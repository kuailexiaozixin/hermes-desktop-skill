from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path

from ._models import ensure_default_web_search_backend, write_model_routes
from ._paths import _lock, get_hermes_home, read_config_yaml, update_config_yaml
from ._skills import ensure_default_skills



# ============================================================================
# ============================================================================
# 7) Cron 定时任务 —— 桥接 Hermes 原生 cron 模块（cron.jobs / cron.scheduler）
# ============================================================================
# 存储与调度完全复用 Hermes 核心：schedule 支持自然语言（"2h" / "every 1d at 09:00"
# / cron 表达式）；调度由后台线程每 60s 调用 cron.scheduler.tick() 驱动
# （见 cron_scheduler.start_scheduler），到期任务由 Hermes 原生执行器运行。
# jobs 持久化在 HERMES_HOME/cron/jobs.json（与 Hermes 生态完全一致）。

def _map_job_view(job: dict) -> dict:
    """原生 job → 前端友好视图（兼容既有面板字段）。"""
    if not job:
        return {}
    enabled = bool(job.get("enabled", True))
    state = job.get("state") or ("active" if enabled else "paused")
    paused = (not enabled) or state == "paused"
    return {
        "id": job.get("id"),
        "name": job.get("name"),
        "prompt": job.get("prompt"),
        "schedule": job.get("schedule_display")
                   or (job.get("schedule") or {}).get("display") or "",
        "status": "paused" if paused else "active",
        "enabled": enabled,
        "next_run_at": job.get("next_run_at"),
        "last_run_at": job.get("last_run_at"),
        "last_status": job.get("last_status"),
        "last_error": job.get("last_error"),
        "deliver": job.get("deliver"),
        "kind": (job.get("schedule") or {}).get("kind"),
    }

def list_jobs(home: Path | None = None) -> list[dict]:
    from cron import jobs as _cj
    try:
        # include_disabled=True：让已暂停(paused/disabled)任务也在面板可见，便于重新启用
        return [_map_job_view(j) for j in _cj.list_jobs(include_disabled=True)]
    except Exception:
        return []

def add_job(prompt: str, schedule: str, home: Path | None = None,
            name: str | None = None, job_type: str | None = None) -> dict:
    from cron import jobs as _cj
    prompt = (prompt or "").strip()
    schedule = (schedule or "").strip()
    if not prompt or not schedule:
        return {"ok": False, "error": "prompt 与 schedule 均不能为空"}
    try:
        job = _cj.create_job(prompt, schedule, name=(name or None))
        return {"ok": True, "job": _map_job_view(job)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

def update_job(job_id: str, home: Path | None = None, name: str | None = None,
               prompt: str | None = None, schedule: str | None = None,
               job_type: str | None = None) -> dict:
    from cron import jobs as _cj
    up: dict = {}
    if name and name.strip():
        up["name"] = name.strip()
    if prompt and prompt.strip():
        up["prompt"] = prompt.strip()
    if schedule and schedule.strip():
        up["schedule"] = schedule.strip()
    if not up:
        return {"ok": False, "error": "无有效更新字段"}
    try:
        job = _cj.update_job(job_id, up)
        return {"ok": True, "job": _map_job_view(job)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

def delete_job(job_id: str, home: Path | None = None) -> dict:
    from cron import jobs as _cj
    try:
        return {"ok": bool(_cj.remove_job(job_id))}
    except Exception:
        return {"ok": False}

def set_job_status(job_id: str, status: str, home: Path | None = None) -> dict:
    from cron import jobs as _cj
    if status in ("active", "resume", "enable", "enabled"):
        try:
            _cj.resume_job(job_id)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}
    try:
        _cj.pause_job(job_id)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

def materialize_hermes_env(home: Path | None = None) -> Path:
    """把 Library 模式运行所需的环境「落地」（幂等，可重复调用）：

    1) 设置 HERMES_HOME 环境变量（AIAgent 据此定位 skills / config.yaml / memories）；
    2) 接通原生 bundled 插件目录（冻结态 _MEIPASS/plugins，开发态 site-packages/plugins）；
    3) 播种默认技能；
    4) 默认联网搜索：ensure_default_web_search_backend 写入零配置免费的 ddgs 后端（无需任何 Key/URL，首次自动安装 SDK）；已显式配置的用户设置不覆盖；
    5) 记录已配置模型路由（中性记录）。
    """
    home = home or get_hermes_home()
    with _lock:
        os.environ["HERMES_HOME"] = str(home)
        _export_bundled_plugins_env()
        ensure_default_skills(home)
        ensure_default_web_search_backend(home)
        try:
            write_model_routes(home)
        except Exception:
            pass
    return home


def _export_bundled_plugins_env() -> str | None:
    """把原生 bundled 插件目录导出到 HERMES_BUNDLED_PLUGINS。

    hermes_cli.plugins.get_bundled_plugins_dir() 优先读该环境变量；设了它，
    Hermes 自带的插件才能在冻结态（_MEIPASS/plugins）被内核发现。
    """
    try:
        if getattr(sys, "frozen", False):
            cand = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "plugins"
        else:
            import plugins as _p  # hermes-agent 顶层 plugins 包
            cand = Path(_p.__file__).resolve().parent
        if cand.exists():
            os.environ["HERMES_BUNDLED_PLUGINS"] = str(cand)
            return str(cand)
    except Exception:
        pass
    return None

# ============================================================================
# 需求3：补功能屏数据层（Soul / 记忆 / 系统提示词 / LLM Wiki / 远程渠道 / Kanban）
# 均为 HERMES_HOME 下的文件或配置 CRUD，遵循薄路由原则供 main.py 调用。
# ============================================================================
import time as _time  # noqa: E402

# ── Soul 人格 ─────────────────────────────────────────────────────────────
def get_soul(home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    p = h / "SOUL.md"
    content = p.read_text(encoding="utf-8") if p.exists() else ""
    cfg = read_config_yaml(h)
    enabled = bool((cfg.get("agent") or {}).get("soul_enabled", False))
    return {"ok": True, "enabled": enabled, "content": content, "path": str(p)}

def save_soul(content: str, enabled: bool, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    (h / "SOUL.md").write_text(content or "", encoding="utf-8")
    # 统一走 update_config_yaml 深合并写入（与 toolset/agent_runtime 同一路径），
    # 避免各 save_* 重复 read→改 agent 子 dict→全量写回 的模板，降低误改共享配置风险。
    update_config_yaml(h, {"agent": {"soul_enabled": bool(enabled)}})
    return {"ok": True, "enabled": bool(enabled)}

# ── 记忆管理（MEMORY.md / USER.md，§ 分节） ─────────────────────────────
MEMORY_FILES = ["MEMORY.md", "USER.md"]

def list_memory(home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    d = h / "memories"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for name in MEMORY_FILES:
        p = d / name
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        entries = [e.strip() for e in text.split("\n§\n") if e.strip()]
        out.append({"name": name, "text": text, "entries": entries,
                    "count": len(entries)})
    return {"ok": True, "files": out}

def save_memory(name: str, text: str, home: Path | None = None) -> dict:
    if name not in MEMORY_FILES:
        return {"ok": False, "error": "非法记忆文件名"}
    h = home or get_hermes_home()
    d = h / "memories"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text or "", encoding="utf-8")
    return {"ok": True, "name": name}

# ── 系统提示词 ───────────────────────────────────────────────────────────
def get_system_prompt(home: Path | None = None) -> dict:
    try:
        from agent_runtime import SYSTEM_PROMPT as default
    except Exception:
        default = ""
    cfg = read_config_yaml(home)
    custom = (cfg.get("agent") or {}).get("system_prompt") or ""
    return {"ok": True, "default": default, "custom": custom}

def save_system_prompt(custom: str, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    update_config_yaml(h, {"agent": {"system_prompt": (custom or "").strip()}})
    return {"ok": True}

# ── LLM Wiki（HERMES_HOME/wiki/，参照 Karpathy 范式、与 Hermes 内置 research/llm-wiki 同范式；本实现为自研，不加载官方 bundled skill） ──
# 重逻辑在 wiki_engine.py（目录/反链/ingest/query/lint/graph）；此处为兼容薄封装。
def _wiki_slug(name: str) -> str:
    s = (name or "").replace("..", "").strip("/")
    if s.lower().endswith(".md"):
        s = s[:-3]
    return s


def list_wiki(home: Path | None = None) -> dict:
    from wiki_engine import list_pages
    return {"ok": True, "items": list_pages(home)}


def get_wiki(name: str, home: Path | None = None) -> dict | None:
    from wiki_engine import get_page
    return get_page(home, _wiki_slug(name))


def save_wiki(name: str, title: str, category: str, tags: list, text: str,
              home: Path | None = None, type_: str = "summary",
              sources: list | None = None, confidence: str = "") -> dict:
    from wiki_engine import save_page
    slug = _wiki_slug(name) if name else None
    return save_page(home, slug=slug, title=title, type_=type_,
                     tags=tags, sources=sources, confidence=confidence,
                     category=category, text=text)


def delete_wiki(name: str, home: Path | None = None) -> dict:
    from wiki_engine import delete_page
    return delete_page(home, _wiki_slug(name))

# ── 远程渠道（Gateway Messaging：微信/QQ/飞书/钉钉/企微/Telegram/Discord/Slack） ──
CHANNELS = [
    {"id": "telegram", "label": "Telegram", "icon": "✈", "desc": "Telegram Bot（Hermes 官方网关支持）"},
    {"id": "discord", "label": "Discord", "icon": "🎮", "desc": "Discord Bot"},
    {"id": "slack", "label": "Slack", "icon": "💬", "desc": "Slack App"},
    {"id": "wechat", "label": "微信", "icon": "💚", "desc": "个人微信（需接入桥接服务）"},
    {"id": "qywx", "label": "企业微信", "icon": "🏢", "desc": "企业微信应用机器人"},
    {"id": "feishu", "label": "飞书", "icon": "🪶", "desc": "飞书机器人"},
    {"id": "dingtalk", "label": "钉钉", "icon": "🔔", "desc": "钉钉机器人"},
    {"id": "qq", "label": "QQ", "icon": "🐧", "desc": "QQ 机器人"},
]

def get_channels(home: Path | None = None) -> dict:
    cfg = read_config_yaml(home)
    cc = (cfg.get("agent") or {}).get("channels") or {}
    out = []
    for c in CHANNELS:
        conf = cc.get(c["id"]) or {}
        out.append({
            **c,
            "enabled": bool(conf.get("enabled")),
            "configured": bool(conf.get("token") or conf.get("webhook")
                               or conf.get("app_id") or conf.get("secret")),
            "config": conf,
        })
    return {"ok": True, "channels": out}

def save_channel(cid: str, config: dict, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    # 深合并进 agent.channels（保留其它渠道），与上面 save_* 同一写入路径。
    update_config_yaml(h, {"agent": {"channels": {cid: config or {}}}})
    return {"ok": True, "id": cid}

# ── Kanban 看板（复用内核 hermes_cli.kanban_db；路径与 schema 与内核完全一致） ──
# 看板数据结构由 Hermes 内核掌握。早期版本曾手写 sqlite、把真实表的 body 列错写成
# description、把 INTEGER 的 created_at 当字符串——一旦命中内核真实创建的 kanban.db
# 就报 "no such column: description"，看板空白、新增失败，且上游 schema 变更会静默损坏。
# 因此这里只复用内核的 kanban_db_path()/connect() 取路径与连接，SQL 严格按真实
# schema（tasks 表列：id/title/body/status/priority/created_at …）书写。路径解析尊重
# HERMES_KANBAN_DB / HERMES_KANBAN_BOARD / HERMES_KANBAN_HOME 与 get_default_hermes_root
# （即桌面冻结的 HERMES_HOME），与同进程内 Agent 写入同一看板。
# home 参数保留以兼容旧调用签名，但实际路径由内核 kanban_db_path() 决定。
def get_kanban(home: Path | None = None) -> dict:
    import sqlite3
    cols = ["todo", "in_progress", "done"]
    try:
        from hermes_cli import kanban_db as kb
    except Exception:
        return {"ok": True, "exists": False, "items": [], "columns": cols,
                "error": "内核 kanban_db 不可用"}
    path = kb.kanban_db_path()
    if not path.exists():
        return {"ok": True, "exists": False, "db": str(path),
                "columns": cols, "items": []}
    items = []
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, title, body, status, priority, created_at "
            "FROM tasks ORDER BY priority DESC, created_at DESC").fetchall()
        for r in rows:
            ca = r["created_at"]
            items.append({
                "id": r["id"], "title": r["title"] or "",
                "status": (r["status"] or "todo"),
                "priority": r["priority"] or 0,
                "description": r["body"] or "",
                "created_at": (_time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(ca))
                              if isinstance(ca, (int, float)) else (ca or "")),
            })
        conn.close()
    except Exception as e:
        return {"ok": True, "exists": True, "db": str(path),
                "columns": cols, "items": [], "error": str(e)}
    return {"ok": True, "exists": True, "db": str(path), "columns": cols,
            "items": items}


def add_kanban_task(title: str, description: str = "", home: Path | None = None) -> dict:
    title = (title or "").strip()
    if not title:
        return {"ok": False, "error": "任务标题不能为空"}
    import uuid
    try:
        from hermes_cli import kanban_db as kb
    except Exception as e:
        return {"ok": False, "error": f"内核 kanban_db 不可用：{e}"}
    conn = None
    try:
        conn = kb.connect()   # 初始化真实 schema（含 WAL）；库不存在则创建
        conn.execute(
            "INSERT INTO tasks (id, title, body, status, priority, created_at) "
            "VALUES (?,?,?,?,0,?)",
            (str(uuid.uuid4()), title, description or "", "todo", int(_time.time())))
        conn.commit()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if conn is not None:
            try: conn.close()
            except Exception: pass
    return {"ok": True}
