"""routes/logs.py — Hermes 日志查看（只读）

对齐真实 Hermes 的日志体系（实探 hermes_logging.py + hermes_cli/logs.py）：

- 日志文件统一落在 <HERMES_HOME>/logs/ 下，本示例沿用示例自身的
  HERMES_HOME（冻结态 = <exe>/hermes_data，开发态 = .hermes_data），
  绝不触碰用户真正的 ~/.hermes。
- 已知日志文件（名称 → 文件名 / 中文说明）：
    agent    agent.log     主日志（INFO+，全部活动）
    errors   errors.log    错误与警告（WARNING+，快速排障）
    gateway  gateway.log   网关事件（仅 gateway 组件，gateway 模式才生成）
    gui      gui.log       控制面板 / WebSocket / TUI（gui 模式才生成）
    desktop  desktop.log   桌面应用启动与后端（桌面壳才生成）
    mcp      mcp-stderr.log MCP 子进程标准错误（排障用）
- 文件按大小自动轮转（agent 约 5MB、errors 2MB、gui 10MB，各保留若干备份）。
- 日志写入时已用 RedactingFormatter 脱敏，密钥不会落盘。
- 过滤语义与 `hermes logs` 一致：按级别（>=）、会话 ID 子串、相对时间
  （--since 1h/30m/2d）、组件前缀（gateway/agent/tools/cli/cron/gui）。

本模块**只读取**日志，不写、不删、不改任何日志文件。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

from routes import _err, _ok, _guard, app, hc, Path  # noqa: F401  (Path 供类型标注)

# ── 已知日志文件（对齐 hermes_cli/logs.py 的 LOG_FILES）─────────────────
# name → (文件名, 中文说明, 生成条件说明)
LOG_FILES = {
    "agent":   ("agent.log",      "主日志（INFO+，全部活动）",            "Agent 运行即生成"),
    "errors":  ("errors.log",     "错误与警告（WARNING+）",              "出现告警/错误即生成"),
    "gateway": ("gateway.log",    "网关事件（仅网关组件）",              "gateway 模式才生成"),
    "gui":     ("gui.log",        "控制面板 / WebSocket / TUI",          "gui 模式才生成"),
    "desktop": ("desktop.log",    "桌面应用启动与后端",                  "桌面壳才生成"),
    "mcp":     ("mcp-stderr.log", "MCP 子进程标准错误（排障）",          "使用 MCP 工具才生成"),
}

# 组件前缀（对齐 hermes_logging.COMPONENT_PREFIXES，用于 --component 过滤）
COMPONENT_PREFIXES = {
    "gateway": ("gateway", "hermes_plugins", "plugins.platforms"),
    "agent":   ("agent", "run_agent", "model_tools", "batch_runner"),
    "tools":   ("tools",),
    "cli":     ("hermes_cli", "cli"),
    "cron":    ("cron",),
    "gui":     ("hermes_cli.web_server", "hermes_cli.pty_bridge", "tui_gateway", "uvicorn"),
}

# ANSI 转义序列（颜色/清屏/光标控制）与破坏性控制字符
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][0-9;]*\x07|\x1b\[[?][0-9;]*[A-Za-z]")
# 除 \n \t 以外的 C0 控制字符与 DEL（避免日志面板显示异常 / 黑块）
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")

# 日志行时间戳正则：匹配行首 "2026-04-05 22:35:00,123" 或 "...22:35:00"
_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})")

# 级别提取：匹配 " INFO " / " WARNING " 等。
# 实探真实 Hermes（hermes_logging._LOG_FORMAT = "%(asctime)s %(levelname)s
# %(session_tag)s %(name)s: %(message)s"，session_tag = " [sid]"）：级别后紧跟
# 空格或 "[session]"。这里用先行断言，允许级别后接空格或 "[",更稳健。
_LEVEL_RE = re.compile(r"\s(DEBUG|INFO|WARNING|ERROR|CRITICAL)(?=[\s\[])")

# 日志器名提取：级别之后、可选 [session]（可在名前或名后）、冒号前的非空白词。
# 兼容两种真实写法：
#   "INFO [sid] agent: ..."   （Hermes 官方格式）
#   "INFO agent [sid]: ..."   （个别版本 / 第三方桥接可能如此）
_LOGGER_NAME_RE = re.compile(
    r"\s(?:DEBUG|INFO|WARNING|ERROR|CRITICAL)(?=[\s\[])"
    r"(?:\s+\[.*?\])?"      # 名前的可选 [session]
    r"\s+([^:]+?)"          # 日志器名（到第一个冒号为止）
    r"(?:\s+\[.*?\])?"      # 名后的可选 [session]
    r":"
)

# 级别顺序（用于 >= 过滤）
_LEVEL_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}


# ── 解析工具 ────────────────────────────────────────────────────────────
def _sanitize_text(text: str) -> str:
    """把原始 stderr / 日志文本清理为可安全显示在 HTML 中的字符串。

    处理要点：
      1. 去掉 ANSI 转义码（颜色、清屏、光标移动等）。
      2. 处理 \r：对每一行，\r 表示"回车覆盖同一行"，只保留最后一个 \r 之后的内容。
         这样 Playwright 的进度条 `27%\r27%\r...` 只会显示最终状态。
      3. 删除其他非打印控制字符（0x00-0x08、0x0b-0x0c、0x0e-0x1f、0x7f）。
      4. 统一把 \r\n / \r 替换为 \n。
    """
    if not isinstance(text, str):
        text = str(text)
    # 1) 去掉 ANSI
    text = _ANSI_RE.sub("", text)
    # 2) 把 \r\n 先统一为 \n，再处理裸 \r
    text = text.replace("\r\n", "\n")
    # 3) 对每行里的 \r 做"回车覆盖"语义：取最后一个 \r 之后的内容
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        if "\r" in line:
            line = line.rsplit("\r", 1)[-1]
        # 4) 删除破坏性控制字符
        line = _CONTROL_RE.sub("", line)
        cleaned.append(line)
    return "\n".join(cleaned)


def _parse_since(since_str: str) -> Optional[datetime]:
    """把 '1h' / '30m' / '2d' / '90s' 解析为时间下限；无法解析返回 None。"""
    since_str = (since_str or "").strip().lower()
    m = re.match(r"^(\d+)\s*([smhd])$", since_str)
    if not m:
        return None
    value = int(m.group(1))
    delta = {"s": timedelta(seconds=value),
             "m": timedelta(minutes=value),
             "h": timedelta(hours=value),
             "d": timedelta(days=value)}[m.group(2)]
    return datetime.now() - delta


def _parse_line_timestamp(line: str) -> Optional[datetime]:
    m = _TS_RE.match(line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _extract_level(line: str) -> Optional[str]:
    m = _LEVEL_RE.search(line)
    return m.group(1) if m else None


def _extract_logger_name(line: str) -> Optional[str]:
    m = _LOGGER_NAME_RE.search(line)
    return m.group(1) if m else None


def _line_matches_component(line: str, prefixes: Sequence[str]) -> bool:
    name = _extract_logger_name(line)
    if name is None:
        return False
    return name.startswith(tuple(prefixes))


def _matches_filters(line: str, *, min_level=None, session_filter=None,
                     since=None, component_prefixes=None) -> bool:
    if since is not None:
        ts = _parse_line_timestamp(line)
        if ts is not None and ts < since:
            return False
    if min_level is not None:
        level = _extract_level(line)
        if level is not None and _LEVEL_ORDER.get(level, 0) < _LEVEL_ORDER.get(min_level, 0):
            return False
    if session_filter is not None:
        if session_filter not in line:
            return False
    if component_prefixes is not None:
        if not _line_matches_component(line, component_prefixes):
            return False
    return True


# ── 文件读取（对齐 hermes_cli.logs._read_last_n_lines / _read_tail）────────
def _read_last_n_lines(path: Path, n: int) -> list:
    """高效读文件末尾 N 行：小文件整读，大文件从尾部分块读。"""
    try:
        size = path.stat().st_size
    except OSError:
        return []
    if size == 0:
        return []
    if size <= 1_048_576:  # 1MB 以内：整读，简单正确
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            sanitized = _sanitize_text(raw)
            return sanitized.splitlines(keepends=True)[-n:] or []
        except Exception:
            return []
    # 大文件：从尾部按块读
    try:
        with open(path, "rb") as f:
            chunk_size = 8192
            lines: list = []
            pos = size
            while pos > 0 and len(lines) <= n + 1:
                read_size = min(chunk_size, pos)
                pos -= read_size
                f.seek(pos)
                chunk = f.read(read_size)
                chunk_lines = chunk.split(b"\n")
                if lines:
                    lines[0] = chunk_lines[-1] + lines[0]
                    lines = chunk_lines[:-1] + lines
                else:
                    lines = chunk_lines
                chunk_size = min(chunk_size * 2, 65536)
            decoded = []
            for raw in lines:
                if not raw.strip():
                    continue
                try:
                    text = raw.decode("utf-8", errors="replace") + "\n"
                except Exception:
                    text = raw.decode("latin-1", errors="replace") + "\n"
                decoded.append(_sanitize_text(text))
            return decoded[-n:]
    except Exception:
        return []


def _read_tail(path: Path, num_lines: int, *, min_level=None,
               session_filter=None, since=None, component_prefixes=None) -> list:
    has_filters = any(x is not None for x in (min_level, session_filter, since, component_prefixes))
    if has_filters:
        raw = _read_last_n_lines(path, max(num_lines * 20, 2000))
        filtered = [l for l in raw if _matches_filters(
            l, min_level=min_level, session_filter=session_filter,
            since=since, component_prefixes=component_prefixes)]
        return filtered[-num_lines:]
    return _read_last_n_lines(path, num_lines)


# ── 业务函数（供 _guard 包装）────────────────────────────────────────────
def _list_logs() -> dict:
    home = hc.get_hermes_home()
    log_dir = home / "logs"
    items = []
    for name, (filename, label, cond) in LOG_FILES.items():
        p = log_dir / filename
        exists = p.is_file()
        size = p.stat().st_size if exists else 0
        mtime = p.stat().st_mtime if exists else None
        items.append({
            "name": name, "filename": filename, "label": label,
            "condition": cond, "exists": exists,
            "size": size, "mtime": mtime,
        })
    return _ok(logs=items, home=str(log_dir),
               note="日志文件在 Hermes 运行时才会生成；若某项显示不存在，请先进行一次对话或相关操作。")


def _view_log(name: str, *, lines: int = 200, level: str = "",
              component: str = "", session: str = "", since: str = "") -> dict:
    if name not in LOG_FILES:
        return _err(f"未知日志：{name!r}。可用：{', '.join(sorted(LOG_FILES))}")
    filename = LOG_FILES[name][0]
    home = hc.get_hermes_home()
    path = home / "logs" / filename
    if not path.is_file():
        return _ok(name=name, filename=filename, exists=False, lines=[],
                  count=0, level=level or None, component=component or None,
                  session=session or None, since=since or None,
                  note="该日志文件尚不存在。日志在 Hermes 运行时才会生成。")

    # 解析过滤参数（与 `hermes logs` 对齐；非法值宽容降级）
    min_level = None
    if level:
        lv = level.upper()
        min_level = lv if lv in _LEVEL_ORDER else None
    component_prefixes = None
    if component:
        cl = component.lower()
        component_prefixes = COMPONENT_PREFIXES.get(cl)
    since_dt = _parse_since(since) if since else None
    session_filter = session.strip() if session else None

    try:
        raw_lines = _read_tail(path, max(int(lines), 1) if lines else 200,
                               min_level=min_level, session_filter=session_filter,
                               since=since_dt, component_prefixes=component_prefixes)
    except PermissionError:
        return _err(f"无权限读取：{path}")
    except Exception as e:  # noqa: BLE001
        return _err(f"读取失败：{type(e).__name__}: {e}")

    # 去掉每行结尾换行，前端统一渲染
    out = [l.rstrip("\r\n") for l in raw_lines]
    return _ok(name=name, filename=filename, exists=True, lines=out,
               count=len(out), level=min_level, component=component or None,
               session=session_filter, since=since or None,
               redacted=True,
               note="日志写入时已脱敏，密钥不会落盘。")


def _logging_config() -> dict:
    """读取 config.yaml 的 logging.*（级别 / 单文件上限 MB / 备份数）。"""
    cfg = hc.read_config_yaml() or {}
    lc = cfg.get("logging") if isinstance(cfg, dict) else None
    if not isinstance(lc, dict):
        lc = {}
    return _ok(
        level=lc.get("level"),
        max_size_mb=lc.get("max_size_mb"),
        backup_count=lc.get("backup_count"),
        defaults={"level": "INFO", "max_size_mb": 5, "backup_count": 3},
        note="修改 config.yaml 的 logging 段后需重启应用生效。",
    )


# ── 路由 ────────────────────────────────────────────────────────────────
@app.get("/api/logs")
def api_logs_list():
    """列出 <HERMES_HOME>/logs/ 下已知日志文件（大小 / 修改时间 / 是否存在）。"""
    return _guard(_list_logs)


@app.get("/api/logs/config")
def api_logs_config():
    """当前日志配置（级别 / 轮转大小 / 备份数）。"""
    return _guard(_logging_config)


@app.get("/api/logs/{name}")
def api_logs_view(name: str, lines: int = 200, level: str = "",
                  component: str = "", session: str = "", since: str = ""):
    """读取某日志文件的末尾若干行，支持按级别 / 组件 / 会话 / 时间过滤。

    仅读取，不写不删。
    """
    return _guard(lambda: _view_log(
        name, lines=lines, level=level, component=component,
        session=session, since=since))
