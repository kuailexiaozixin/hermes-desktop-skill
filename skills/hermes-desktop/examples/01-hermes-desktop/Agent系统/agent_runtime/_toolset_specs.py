"""工具集 Spec 表 —— 工具集元数据的单一事实源（方案 A 重构）。

本模块把原先散落 6 处的按工具集 keyed 数据（TOOLSET_LABELS / TOOLSET_CATEGORIES /
TOOLSET_RUNTIME_HINTS / ENV_REQUIRED / routes.toolsets.TRIAL_FORCE / TRIAL_PROMPTS）
收敛为一张声明式 ``TOOLSET_SPECS`` 表，其余全部由表派生（文件末尾的兼容视图保持
``agent_runtime`` 既有导出名不变，调用方零改动）。

探测（test 报告）同样声明化：
  * ``probe_env``：EnvSpec 序列，通用 env 探测（set / 未设置 + 可选真实值展示）；
  * ``probe_fn``：确实特殊的运行环境探测（CDP 端口文件、沙箱、cua-driver 等），
    返回 ``(checks, extra_detail)``，不再重复写「检查某 env 是否设置」。

TRIAL（试用）规格：``trial_tools`` + ``trial_join`` 由 ``build_trial_force`` 生成
system 级强制指令（与原 26 条模板逐字等价），``trial_prompt`` 为预置最小任务。

行为契约（与重构前逐字段对齐，见 tests/test_toolsets_specs.py 与基线 diff）：
  * discover_toolsets 的 label/category/env/hint/requirements 输出不变；
  * test_toolset 的 checks 列表内容与顺序不变（image_gen 修复 FAL_KEY 遗漏，
    属有意增强——原 ENV_REQUIRED 有 FAL_KEY 而死代码探测分支漏了它）；
  * TRIAL_FORCE / TRIAL_PROMPTS 键值与原字典完全一致。
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


# ============================================================================
# 分类常量（与重构前 TOOLSET_CATEGORIES 值逐字一致）
# ============================================================================
CAT_BROWSER = "🌐 浏览器"
CAT_CODE = "💻 代码"
CAT_DESKTOP = "🖥️ 电脑"
CAT_SEARCH = "🔍 搜索"
CAT_TASK = "📋 任务"
CAT_CONTENT = "🎨 内容"
CAT_SOCIAL = "💬 社交"
CAT_HOME = "🏠 家居"
CAT_MEMORY = "🧠 记忆"
CAT_SCHEDULE = "⏰ 定时"
CAT_FUN = "🎵 娱乐"
CAT_OTHER = "🔧 其他"

CATEGORY_ORDER: List[str] = [
    CAT_BROWSER, CAT_CODE, CAT_DESKTOP, CAT_SEARCH, CAT_TASK,
    CAT_CONTENT, CAT_SOCIAL, CAT_HOME, CAT_MEMORY, CAT_SCHEDULE,
    CAT_FUN, CAT_OTHER,
]


# ============================================================================
# 声明式探测原语
# ============================================================================
@dataclass(frozen=True)
class EnvSpec:
    """一个环境变量的探测声明（test 报告的 checks 行）。"""
    var: str
    ok_text: str = "已设置"
    missing_text: str = "未设置"
    show_value: bool = False  # True 且已设置时直接展示当前值（用于 URL 类）


def E(var: str) -> EnvSpec:
    """简写：常规 env 探测。"""
    return EnvSpec(var)


def inject_agent_env() -> None:
    """把 config.yaml 中 agent.env 注入 os.environ（工具集 check_fn 读环境变量）。"""
    try:
        from hermes_config import get_hermes_home, read_config_yaml
        agent = (read_config_yaml(get_hermes_home()).get("agent", {}) or {})
        for k, v in (agent.get("env") or {}).items():
            os.environ.setdefault(str(k), str(v))
    except Exception:  # noqa: BLE001
        pass


# ── 专用探测函数（确实特殊、无法用 EnvSpec 表达的运行环境探测）──────────────
# 每个函数返回 (checks, extra_detail)；extra_detail 追加进 test 报告 detail。

def _probe_browser_cdp() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    from pathlib import Path as _Path
    edge_exe = _Path("C:/") / "Program Files (x86)" / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    _edge_installed = edge_exe.exists()
    checks.append({"var": "Edge 浏览器", "set": _edge_installed,
                   "value": f"已安装（{edge_exe}）" if _edge_installed else "未安装"})

    cdp_url = os.environ.get("BROWSER_CDP_URL", "")
    # 也检查 config.yaml 中的 browser.cdp_url
    try:
        from hermes_config import get_hermes_home, read_config_yaml
        _cfg = read_config_yaml(get_hermes_home())
        _browser_cfg = _cfg.get("browser", {}) or {}
        _cfg_url = _browser_cfg.get("cdp_url", "")
        if _cfg_url and not cdp_url:
            cdp_url = _cfg_url
    except Exception:
        pass
    if cdp_url:
        checks.append({"var": "BROWSER_CDP_URL", "set": True,
                       "value": cdp_url[:60] + "…" if len(cdp_url) > 60 else cdp_url})
    else:
        checks.append({"var": "BROWSER_CDP_URL", "set": False})

    # 探测 DevToolsActivePort 获取 CDP 端点
    edge_data = _Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"
    dt_port = edge_data / "DevToolsActivePort"
    if dt_port.exists():
        try:
            port_text = dt_port.read_text().strip()
            _lines = port_text.splitlines()
            _port = _lines[0].strip() if _lines else ""
            _path = _lines[1].strip() if len(_lines) > 1 else "/devtools/browser/"
            _ws_url = f"ws://127.0.0.1:{_port}{_path}"
            # 轻量 TCP ping 验证端点是否存活（Edge 的 HTTP 端点始终返回 404）
            try:
                import socket as _sock
                _s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                _s.settimeout(2)
                _result = _s.connect_ex(("127.0.0.1", int(_port)))
                _s.close()
                if _result == 0:
                    checks.append({"var": "DevToolsActivePort", "set": True,
                                   "value": f"端口 {_port} · 运行中（WebSocket: {_ws_url[:50]}…）"})
                else:
                    checks.append({"var": "DevToolsActivePort", "set": False,
                                   "value": f"端口 {_port} · 端口文件存在但端口未监听（可能来自上次会话）"})
            except Exception:
                checks.append({"var": "DevToolsActivePort", "set": False,
                               "value": f"端口 {_port} · 连接失败"})
        except Exception:
            checks.append({"var": "DevToolsActivePort", "set": False, "value": "存在但无法读取"})
    else:
        checks.append({"var": "DevToolsActivePort", "set": False,
                       "value": "不存在（Edge 需以 --remote-debugging-port=9222 启动）"})
    return checks, ""


def _probe_vision() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    try:
        from hermes_config import get_active_model_cfg
        _model = get_active_model_cfg(None)
        _model_name = (_model or {}).get("model", "未知")
        _has_vision = any(k in (_model_name or "").lower() for k in ("vision", "vl", "4v", "omni", "gemini"))
        checks.append({"var": "当前模型", "set": True, "value": _model_name})
        checks.append({"var": "模型支持视觉", "set": _has_vision,
                       "value": "是" if _has_vision else "否（需切换至支持视觉的模型）"})
    except Exception:
        checks.append({"var": "当前模型", "set": False, "value": "读取失败"})
    return checks, ""


def _probe_code_execution() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    checks.append({"var": "Python 版本", "set": True, "value": sys.version.split()[0]})
    checks.append({"var": "操作系统", "set": True, "value": sys.platform})
    try:
        from tools.code_execution_tool import SANDBOX_AVAILABLE
        checks.append({"var": "沙箱就绪", "set": SANDBOX_AVAILABLE,
                       "value": "是" if SANDBOX_AVAILABLE else "否（仅 POSIX 系统支持）"})
    except Exception:
        checks.append({"var": "沙箱就绪", "set": False, "value": "无法检测"})
    return checks, ""


def _probe_computer_use() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    checks.append({"var": "操作系统", "set": True, "value": sys.platform})
    # 确保 config.yaml 中的 HERMES_CUA_DRIVER_CMD 已注入 os.environ
    inject_agent_env()
    # 直接检查 cua-driver 二进制（不依赖 cua_backend 模块级缓存变量）
    _cua_cmd = os.environ.get("HERMES_CUA_DRIVER_CMD", "cua-driver")
    _driver_ok = bool(shutil.which(_cua_cmd))
    extra = ""
    if _driver_ok:
        checks.append({"var": "cua-driver", "set": True, "value": "可用"})
    else:
        checks.append({"var": "cua-driver", "set": False, "value": "未安装"})
        extra = "cua-driver 未安装。点击「一键检测安装」自动安装即可。"
    return checks, extra


def _probe_web() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    # 检查联网后端（真实配置键：web.search_backend > web.backend）
    try:
        from hermes_config import read_config_yaml
        _cfg = read_config_yaml()
        _web = (_cfg.get("web") or {}) or {}
        _backend = (_web.get("search_backend") or _web.get("backend") or "").strip()
        checks.append({"var": "联网后端", "set": bool(_backend), "value": _backend or "未配置（自动探测）"})
    except Exception:
        checks.append({"var": "联网后端", "set": False})
    return checks, ""


def _probe_browser() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    try:
        from tools.browser_tool import check_browser_requirements
        _ok = bool(check_browser_requirements())
        checks.append({"var": "Playwright 浏览器", "set": _ok,
                       "value": "可用" if _ok else "未安装/不可用（需 playwright install）"})
    except Exception as _e:
        checks.append({"var": "Playwright 浏览器", "set": False, "value": "检测异常：%s" % _e})
    return checks, ""


def _probe_skills() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    from pathlib import Path as _P
    try:
        from hermes_config import get_hermes_home
        _skills_dir = _P(get_hermes_home()) / "skills"
        _count = len(list(_skills_dir.glob("*/SKILL.md"))) if _skills_dir.exists() else 0
        checks.append({"var": "技能目录", "set": _skills_dir.exists(),
                       "value": "%s 个技能" % _count if _skills_dir.exists() else "目录不存在"})
    except Exception as _e:
        checks.append({"var": "技能目录", "set": False, "value": "检测异常：%s" % _e})
    return checks, ""


def _probe_ffmpeg() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    _ff = shutil.which("ffmpeg")
    checks.append({"var": "FFmpeg", "set": bool(_ff), "value": _ff or "未安装（需安装 FFmpeg）"})
    return checks, ""


def _probe_cronjob() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    try:
        from tools.registry import registry
        _tools = registry.get_tool_names_for_toolset("cronjob")
        checks.append({"var": "cronjob 工具", "set": len(_tools) > 0, "value": "%d 个工具" % len(_tools)})
    except Exception:
        checks.append({"var": "cronjob 工具", "set": False, "value": "未注册"})
    # 检查 cron 调度线程
    try:
        import cron_scheduler as _cs
        _running = bool(_cs._scheduler_thread and _cs._scheduler_thread.is_alive())
        checks.append({"var": "调度器线程", "set": _running, "value": "运行中" if _running else "未启动"})
    except Exception:
        checks.append({"var": "调度器线程", "set": False})
    return checks, ""


def _probe_kanban() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    from pathlib import Path as _P
    try:
        from hermes_config import get_hermes_home
        _db = _P(get_hermes_home()) / "kanban.db"
        checks.append({"var": "kanban.db", "set": _db.exists(),
                       "value": "存在" if _db.exists() else "未初始化（使用看板工具后自动创建）"})
    except Exception as _e:
        checks.append({"var": "kanban.db", "set": False, "value": "检测异常：%s" % _e})
    return checks, ""


def _probe_session_search() -> Tuple[List[dict], str]:
    checks: List[dict] = []
    from pathlib import Path as _P
    try:
        from hermes_config import get_hermes_home
        _db = _P(get_hermes_home()) / "desktop" / "sessions.db"
        _count = 0
        if _db.exists():
            from sessions import count_conversations
            _count = count_conversations()
        checks.append({"var": "sessions.db", "set": _db.exists(),
                       "value": "%d 条会话" % _count if _db.exists() else "不存在"})
    except Exception:
        checks.append({"var": "sessions.db", "set": False})
    return checks, ""


def _make_registered_probe(toolset_name: str) -> Callable:
    """通用探测：某工具集在 registry 中注册的工具数。"""
    def _probe() -> Tuple[List[dict], str]:
        checks: List[dict] = []
        try:
            from tools.registry import registry
            _tools = registry.get_tool_names_for_toolset(toolset_name)
            checks.append({"var": "%s 工具" % toolset_name, "set": len(_tools) > 0,
                           "value": "%d 个工具" % len(_tools)})
        except Exception:
            checks.append({"var": "%s 工具" % toolset_name, "set": False, "value": "未注册"})
        return checks, ""
    return _probe


# ============================================================================
# Spec 表
# ============================================================================
@dataclass(frozen=True)
class ToolsetSpec:
    """一个工具集的全部元数据（唯一事实源）。"""
    label: str = ""                    # 中文名（空 → 回退 registry 原名）
    purpose: str = ""                  # 一句话用途（通用措辞，不含行业术语）
    category: str = CAT_OTHER          # 分类（CATEGORY_ORDER 之一）
    env: Tuple[str, ...] = ()          # 所需运行时环境变量（任一配置即视为已配置）
    runtime_hint: str = ""             # 未就绪引导（配置弹窗 / 卡片提示）
    trial_tools: Tuple[str, ...] = ()  # 试用强制使用的工具名（生成 TRIAL_FORCE）
    trial_join: str = "或"             # 多工具时的连接词（或 / 和）
    trial_prompt: str = ""             # 试用预置最小任务（空 → 通用兜底句）
    installer: str = ""                # 一键安装分支键（cua/cronjob/kanban/ffmpeg；空=不支持）
    probe_env: Tuple[EnvSpec, ...] = ()           # test 报告的 env 探测项
    probe_fn: Optional[Callable] = None           # 专用探测（返回 checks, extra_detail）


TOOLSET_SPECS: Dict[str, ToolsetSpec] = {
    # ── 🖥️ 电脑 ────────────────────────────────────────────────
    "file": ToolsetSpec(
        label="文件读写", purpose="读写本地文件、浏览目录、进程内执行 Python（纯 Python，无终端）",
        category=CAT_DESKTOP,
        runtime_hint="文件读写自动可用，无需额外配置。纯 Python 实现，无终端依赖。",
        trial_tools=("write_file", "read_file"), trial_join="和",
        trial_prompt="请使用文件工具在工作目录创建一个文件 trial_test.txt（内容 hello），然后读取它并返回内容。",
    ),
    "computer_use": ToolsetSpec(
        label="电脑自动化", purpose="操作本机应用完成重复性工作（需配置）",
        category=CAT_DESKTOP,
        runtime_hint="需要安装桌面自动化驱动（cua-driver），点击「配置」→「一键检测安装」自动完成。"
                     "Windows 已原生支持，Linux 需 X11/XWayland 环境。",
        trial_tools=("computer_use",),
        trial_prompt="请使用电脑自动化工具描述当前桌面状态，并返回结果。",
        installer="cua", probe_fn=_probe_computer_use,
    ),

    # ── 💻 代码 ────────────────────────────────────────────────
    "code_execution": ToolsetSpec(
        label="代码执行", purpose="在沙箱内运行代码做计算、数据处理与验证",
        category=CAT_CODE,
        runtime_hint="需要在 POSIX 兼容系统下运行（Linux/macOS/WSL）。"
                     "Windows 原生支持受限，建议使用 WSL 或 Docker 环境。",
        trial_tools=("run_python", "run_javascript"),
        trial_prompt="请使用代码执行工具运行 Python：print(6*7)，并告诉我输出结果。",
        probe_fn=_probe_code_execution,
    ),
    "terminal": ToolsetSpec(
        label="终端命令", purpose="已按架构禁用（改用进程内 run_python，无需 Git Bash）",
        category=CAT_CODE,
    ),

    # ── 🌐 浏览器 ──────────────────────────────────────────────
    "browser": ToolsetSpec(
        label="浏览器自动化", purpose="自动打开网页、点击填表、抓取页面内容",
        category=CAT_BROWSER,
        runtime_hint=("需要 Chromium 内核浏览器引擎（由 agent-browser CLI 驱动，Playwright 仅作 Chromium "
                      "二进制来源之一，并非运行时引擎）。推荐 `npx agent-browser install --with-deps` 安装；"
                      "本机已装 Edge/Chrome 可零下载启用：设置环境变量 AGENT_BROWSER_EXECUTABLE_PATH "
                      "指向其 exe 路径；也可 `npx playwright install chromium` 作为备选（装到 "
                      "~/.cache/ms-playwright 后会被自动识别）。"),
        trial_tools=("browser",),
        trial_prompt="请使用浏览器工具打开 https://example.com 并返回页面标题。",
        probe_fn=_probe_browser,
    ),
    "browser-cdp": ToolsetSpec(
        label="浏览器(CDP)", purpose="基于 Chrome DevTools 协议的高级网页自动化",
        category=CAT_BROWSER,
        env=("BROWSER_CDP_URL",),
        runtime_hint="需要本地 Edge 浏览器开启远程调试。操作步骤：1. 关闭所有 Edge 窗口；"
                     "2. 运行：msedge.exe --remote-debugging-port=9222；"
                     "3. 在此页面点击「配置」→「自动检测 Edge CDP 端点」。",
        trial_tools=("browser_cdp",),
        trial_prompt="请使用 CDP 浏览器工具打开 https://example.com 并返回页面标题。",
        probe_env=(E("BROWSER_CDP_URL"),),
        probe_fn=_probe_browser_cdp,
    ),

    # ── 🔍 搜索 ────────────────────────────────────────────────
    "web": ToolsetSpec(
        label="联网检索", purpose="检索互联网信息与实时资料（部分后端需 API Key）",
        category=CAT_SEARCH,
        env=("EXA_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY", "PARALLEL_API_KEY",
             "SEARXNG_URL", "BRAVE_SEARCH_API_KEY", "XAI_API_KEY"),
        runtime_hint=("联网检索内置 8 个后端：firecrawl(默认,需 KEY)、searxng(免费,需 SEARXNG_URL)、"
                      "brave-free(免费额度,需 BRAVE_SEARCH_API_KEY)、ddgs(免费无需任何 Key,首次自动安装 SDK)、"
                      "tavily/exa/parallel(需对应 KEY)、xai(需 XAI_API_KEY,手动 opt-in)。"
                      "零配置即可联网：ddgs 无需任何 Key；或自托管 SearXNG 填 SEARXNG_URL。"),
        trial_tools=("web_search", "web_extract"),
        trial_prompt="请使用联网搜索工具搜索「人工智能最新进展」，简要总结 3 条要点。",
        probe_fn=_probe_web,
    ),
    "x_search": ToolsetSpec(
        label="X 检索", purpose="检索 X/Twitter 公开信息（需 XAI_API_KEY）",
        category=CAT_SEARCH,
        env=("XAI_API_KEY",),
        runtime_hint="X/Twitter 检索需要 XAI_API_KEY。在工具集配置页面填写 XAI_API_KEY 环境变量。",
        trial_tools=("x_search",),
        trial_prompt="请使用 X 检索工具搜索「AI」，简要总结结果。",
        probe_env=(EnvSpec("XAI_API_KEY", missing_text="未设置（需配置 XAI_API_KEY）"),),
    ),
    "session_search": ToolsetSpec(
        label="历史检索", purpose="检索过往会话与结论",
        category=CAT_SEARCH,
        runtime_hint="历史检索自动可用，无需额外配置。检索过往会话与结论，数据来自本地会话库（SQLite）。",
        trial_tools=("session_search",),
        trial_prompt="请使用历史检索工具搜索与「测试」相关的会话，并返回结果。",
        probe_fn=_probe_session_search,
    ),

    # ── 📋 任务 ────────────────────────────────────────────────
    "todo": ToolsetSpec(
        label="待办清单", purpose="拆解与跟踪任务清单",
        category=CAT_TASK,
        runtime_hint="待办清单自动可用，无需额外配置。",
        trial_tools=("create_todo", "list_todos"),
        trial_prompt="请使用待办工具创建一条测试待办「试用验证」，再列出待办。",
    ),
    "kanban": ToolsetSpec(
        label="看板", purpose="以看板管理任务状态、阻塞与评论",
        category=CAT_TASK,
        runtime_hint="点击「一键检测安装」自动配置后即可使用。数据存储在 HERMES_HOME/kanban.db 中。",
        trial_tools=("kanban",),
        trial_prompt="请使用看板工具列出所有任务，并返回结果。",
        installer="kanban", probe_fn=_probe_kanban,
    ),
    "project": ToolsetSpec(
        label="项目管理", purpose="管理项目、阶段与产出",
        category=CAT_TASK,
        runtime_hint="项目管理自动可用，无需额外配置。",
        trial_tools=("project",),
        trial_prompt="请使用项目管理工具列出当前可用的项目操作，并返回结果。",
        probe_fn=_make_registered_probe("project"),
    ),
    "delegation": ToolsetSpec(
        label="子任务委派", purpose="把复杂任务拆给子智能体并行处理",
        category=CAT_TASK,
        runtime_hint="子任务委派自动可用，无需额外配置。支持将复杂任务拆解给子智能体并行处理。",
        trial_tools=("delegate_task",),
        trial_prompt="请使用子任务委派工具将「计算 1+1」作为一个子任务执行，并返回结果。",
        probe_fn=_make_registered_probe("delegation"),
    ),

    # ── 🎨 内容 ────────────────────────────────────────────────
    "vision": ToolsetSpec(
        label="图像理解", purpose="识别图片、截图与文档影像中的内容",
        category=CAT_CONTENT,
        env=("OPENAI_API_KEY", "SILICONFLOW_API_KEY"),
        runtime_hint="需要视觉模型 API Key 或本地视觉后端。请在模型配置中确认已设置支持视觉的模型。",
        trial_tools=("vision",),
        trial_prompt="请使用图像理解工具说明它能识别什么（无需实际图片）。",
        probe_env=(E("OPENAI_API_KEY"), E("SILICONFLOW_API_KEY")),
        probe_fn=_probe_vision,
    ),
    "image_gen": ToolsetSpec(
        label="图像生成", purpose="按描述生成图片（需配置）",
        category=CAT_CONTENT,
        env=("FAL_KEY", "OPENAI_API_KEY", "SILICONFLOW_API_KEY", "STABILITY_API_KEY"),
        runtime_hint="需要图像生成 API Key。厂商预设：OpenAI DALL-E / Stability AI / 硅基流动。",
        trial_tools=("generate_image",),
        trial_prompt="请使用图像生成工具生成一张「蓝色小猫」的图片，并说明是否成功。",
        # 探测覆盖全部 env（修复重构前 ENV_REQUIRED 有 FAL_KEY 而死代码探测分支漏掉的不一致）
        probe_env=(E("FAL_KEY"), E("OPENAI_API_KEY"), E("SILICONFLOW_API_KEY"), E("STABILITY_API_KEY")),
    ),
    "video_gen": ToolsetSpec(
        label="视频生成", purpose="按描述生成短视频（需配置）",
        category=CAT_CONTENT,
        env=("RUNWAY_API_KEY", "PIKA_API_KEY"),
        runtime_hint="需要视频生成 API Key。厂商预设：Runway / Pika / 可灵。",
        trial_tools=("generate_video",),
        trial_prompt="请使用视频生成工具生成一段 5 秒的「海浪」视频，并返回结果。",
        probe_env=(E("RUNWAY_API_KEY"), E("PIKA_API_KEY")),
    ),
    "video": ToolsetSpec(
        label="视频处理", purpose="视频剪辑与转码相关处理（需配置）",
        category=CAT_CONTENT,
        runtime_hint="需要 FFmpeg 视频处理引擎。点击「一键检测安装」自动下载安装。",
        trial_tools=("video",),
        trial_prompt="请使用视频处理工具列出当前可用的视频操作，并返回结果。",
        installer="ffmpeg", probe_fn=_probe_ffmpeg,
    ),
    "tts": ToolsetSpec(
        label="语音合成", purpose="把文本转为语音（需配置）",
        category=CAT_CONTENT,
        env=("OPENAI_API_KEY", "VOLC_API_KEY"),
        runtime_hint="需要语音合成 API Key。厂商预设：OpenAI TTS / 火山引擎。",
        trial_tools=("text_to_speech",),
        trial_prompt="请使用语音合成工具将「你好，世界」转为语音，并返回结果。",
        probe_env=(E("OPENAI_API_KEY"), E("VOLC_API_KEY")),
    ),

    # ── 💬 社交 ────────────────────────────────────────────────
    "feishu_doc": ToolsetSpec(
        label="飞书文档", purpose="读写飞书文档（需配置）",
        category=CAT_SOCIAL,
        env=("FEISHU_APP_ID", "FEISHU_APP_SECRET"),
        runtime_hint="需要飞书开放平台 App ID 与 App Secret。在飞书开发者后台创建应用后获取。",
        trial_tools=("feishu_doc",),
        trial_prompt="请使用飞书文档工具列出当前可用的飞书操作，并返回结果。",
        probe_env=(E("FEISHU_APP_ID"), E("FEISHU_APP_SECRET")),
    ),
    "feishu_drive": ToolsetSpec(
        label="飞书云盘", purpose="读写飞书云盘（需配置）",
        category=CAT_SOCIAL,
        env=("FEISHU_APP_ID", "FEISHU_APP_SECRET"),
        runtime_hint="需要飞书开放平台 App ID 与 App Secret。在飞书开发者后台创建应用后获取。",
        trial_tools=("feishu_drive",),
        trial_prompt="请使用飞书云盘工具列出当前可用的飞书云盘操作，并返回结果。",
        probe_env=(E("FEISHU_APP_ID"), E("FEISHU_APP_SECRET")),
    ),
    "discord": ToolsetSpec(
        label="Discord", purpose="Discord 集成（需配置）",
        category=CAT_SOCIAL,
        env=("DISCORD_BOT_TOKEN",),
        runtime_hint="需要 Discord Bot Token。在 Discord Developer Portal 创建 Bot 后获取。",
        trial_tools=("discord",),
        trial_prompt="请使用 Discord 工具列出当前可用的 Discord 操作，并返回结果。",
        probe_env=(E("DISCORD_BOT_TOKEN"),),
    ),
    "discord_admin": ToolsetSpec(
        label="Discord 管理", purpose="Discord 管理（需配置）",
        category=CAT_SOCIAL,
        env=("DISCORD_BOT_TOKEN",),
        runtime_hint="需要 Discord Bot Token 及管理员权限。",
        trial_tools=("discord_admin",),
        trial_prompt="请使用 Discord 管理工具列出当前可用的管理操作，并返回结果。",
        probe_env=(E("DISCORD_BOT_TOKEN"),),
    ),
    "hermes-yuanbao": ToolsetSpec(
        label="元宝", purpose="腾讯元宝集成（需配置）",
        category=CAT_SOCIAL,
        env=("YUANBAO_API_KEY",),
        runtime_hint="需要腾讯元宝 API Key。",
        trial_tools=("hermes_yuanbao",),
        trial_prompt="请使用元宝工具列出当前可用的元宝操作，并返回结果。",
        probe_env=(E("YUANBAO_API_KEY"),),
    ),

    # ── 🏠 家居 / 🎵 娱乐 ──────────────────────────────────────
    "homeassistant": ToolsetSpec(
        label="HomeAssistant", purpose="智能家居集成（需配置）",
        category=CAT_HOME,
        env=("HOMEASSISTANT_TOKEN",),
        runtime_hint="需要 HomeAssistant 长生命周期 Token 和 Base URL。",
        trial_tools=("homeassistant",),
        trial_prompt="请使用 HomeAssistant 工具列出当前可用的智能家居操作，并返回结果。",
        probe_env=(E("HOMEASSISTANT_TOKEN"), EnvSpec("HOMEASSISTANT_URL", show_value=True)),
    ),
    "spotify": ToolsetSpec(
        label="Spotify", purpose="Spotify 音乐控制（需配置）",
        category=CAT_FUN,
        env=("SPOTIFY_ACCESS_TOKEN",),
        runtime_hint="需要 Spotify 账号授权。请先在系统浏览器登录 Spotify 后重试。",
        probe_env=(EnvSpec("SPOTIFY_ACCESS_TOKEN", ok_text="已授权",
                           missing_text="未授权（需登录 Spotify）"),),
    ),

    # ── 🧠 记忆 ────────────────────────────────────────────────
    "memory": ToolsetSpec(
        label="长期记忆", purpose="跨会话记住偏好、约定与事实",
        category=CAT_MEMORY,
        runtime_hint="长期记忆自动可用，无需额外配置。跨会话记住偏好、约定与事实。",
        trial_tools=("read_memory", "write_memory"),
        trial_prompt="请使用记忆工具向 MEMORY.md 追加一条测试条目「试用验证」，再读取确认。",
    ),
    "skills": ToolsetSpec(
        label="技能库", purpose="加载 SKILL.md 形式的专家技能扩展能力",
        category=CAT_MEMORY,
        runtime_hint="技能库自动可用，无需额外配置。加载 SKILL.md 形式的专家技能。",
        trial_tools=("skills",),
        trial_prompt="请使用技能库工具列出当前可用的技能操作，并返回结果。",
        probe_fn=_probe_skills,
    ),
    "clarify": ToolsetSpec(
        label="澄清提问", purpose="信息不足时向用户追问关键细节",
        category=CAT_MEMORY,
        runtime_hint="澄清提问自动可用，无需额外配置。信息不足时向用户追问关键细节。",
        trial_tools=("clarify",),
        trial_prompt="请使用澄清提问工具对「帮我写个程序」这个模糊需求进行追问，列出需要澄清的问题。",
        probe_fn=_make_registered_probe("clarify"),
    ),

    # ── ⏰ 定时 ────────────────────────────────────────────────
    "cronjob": ToolsetSpec(
        label="定时任务", purpose="按 cron / 自然语言周期定时执行任务",
        category=CAT_SCHEDULE,
        runtime_hint="点击「一键检测安装」自动配置后即可使用。启用后任务会在后台线程中按周期自动执行。",
        trial_tools=("cronjob",),
        trial_prompt="请使用定时任务工具列出当前所有定时任务，并返回结果。",
        installer="cronjob", probe_fn=_probe_cronjob,
    ),

    # ── 🔧 其他（无分类登记的回退默认）────────────────────────
    "sogou_weixin": ToolsetSpec(
        label="公众号检索", purpose="通过搜狗微信搜索检索微信公众号文章（免费无需 Key）",
    ),
}


# ============================================================================
# 派生逻辑
# ============================================================================
def get_spec(name: str) -> Optional[ToolsetSpec]:
    return TOOLSET_SPECS.get(name)


def build_trial_force(name: str, spec: Optional[ToolsetSpec] = None) -> str:
    """生成「试用」的 system 级强制指令（与重构前 26 条模板逐字等价）。"""
    if spec is None:
        spec = TOOLSET_SPECS.get(name)
    if spec and spec.trial_tools:
        if len(spec.trial_tools) == 1:
            tools_txt = spec.trial_tools[0]
        else:
            tools_txt = (" %s " % spec.trial_join).join(spec.trial_tools)
        return ("你必须使用 %s 工具集中的 %s 工具来完成以下任务，不要使用其他工具集。"
                % (name, tools_txt))
    return "你必须使用【%s】工具集中的工具来完成以下任务，不要使用其他工具集。" % name


def build_trial_prompt(name: str) -> str:
    """试用的预置最小任务；未登记的工具集走通用兜底句。"""
    spec = TOOLSET_SPECS.get(name)
    if spec and spec.trial_prompt:
        return spec.trial_prompt
    return "请使用与【%s】相关的工具完成一个最小任务，并说明执行结果。" % name


def run_probes(name: str) -> Tuple[List[dict], str]:
    """声明式探测执行器：替代重构前 250 行 if/elif 链。

    返回 (checks, detail)，字段与重构前 ``_runtime_probe`` 完全一致：
      1. 有 runtime_hint 的工具集，detail 首行为「运行环境要求：<hint>」；
      2. probe_env 逐项生成 env 探测行；
      3. probe_fn 追加专用探测与额外 detail。
    """
    spec = TOOLSET_SPECS.get(name)
    checks: List[dict] = []
    detail_parts: List[str] = []
    hint = spec.runtime_hint if spec else ""
    if hint:
        detail_parts.append("运行环境要求：" + hint)
    if spec is None:
        return checks, "\n".join(detail_parts)
    for es in spec.probe_env:
        v = os.environ.get(es.var, "")
        if v:
            value = v if es.show_value else es.ok_text
            checks.append({"var": es.var, "set": True, "value": value})
        else:
            checks.append({"var": es.var, "set": False, "value": es.missing_text})
    if spec.probe_fn is not None:
        try:
            extra_checks, extra_detail = spec.probe_fn()
            checks.extend(extra_checks)
            if extra_detail:
                detail_parts.append(extra_detail)
        except Exception as _e:  # noqa: BLE001
            checks.append({"var": "探测异常", "set": False, "value": str(_e)})
    return checks, "\n".join(detail_parts)


def group_specs_by_category() -> "List[Tuple[str, List[ToolsetSpec]]]":
    """按 CATEGORY_ORDER 分组（前端分组渲染可直接复用）。"""
    groups: Dict[str, List[ToolsetSpec]] = {}
    for spec in TOOLSET_SPECS.values():
        groups.setdefault(spec.category, []).append(spec)
    return [(c, groups[c]) for c in CATEGORY_ORDER if c in groups]


# ============================================================================
# 兼容视图（保持 agent_runtime 既有导出名与形态，调用方零改动）
# ============================================================================
TOOLSET_LABELS: Dict[str, Tuple[str, str]] = {
    n: (s.label, s.purpose) for n, s in TOOLSET_SPECS.items()}
# 与原始 TOOLSET_CATEGORIES 逐键一致：只登记非默认分类；sogou_weixin 等走默认
# 「🔧 其他」的工具集不入表（discover 侧 .get 兜底，行为不变）。前端分组渲染直接用
# spec.category，不经此视图。
TOOLSET_CATEGORIES: Dict[str, str] = {
    n: s.category for n, s in TOOLSET_SPECS.items() if s.category != CAT_OTHER}
TOOLSET_RUNTIME_HINTS: Dict[str, str] = {
    n: s.runtime_hint for n, s in TOOLSET_SPECS.items() if s.runtime_hint}
ENV_REQUIRED: Dict[str, List[str]] = {
    n: list(s.env) for n, s in TOOLSET_SPECS.items() if s.env}
TRIAL_FORCE: Dict[str, str] = {
    n: build_trial_force(n, s) for n, s in TOOLSET_SPECS.items() if s.trial_tools}
TRIAL_PROMPTS: Dict[str, str] = {
    n: s.trial_prompt for n, s in TOOLSET_SPECS.items() if s.trial_prompt}
