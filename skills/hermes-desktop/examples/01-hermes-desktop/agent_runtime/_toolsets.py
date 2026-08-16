from __future__ import annotations

import json
import os
import queue
import re
import threading
from typing import Any, Callable, Iterator
import file_tools
import host_tools

from ._tools import DANGEROUS_TOOLSETS, DISABLED_TOOLSETS, register_pure_python_tools



# ============================================================================
# 7) 工具集能力矩阵（设置中心「工具与集成」面板数据源）
# ============================================================================
# 友好中文名 + 一句话用途（**通用措辞，不含任何行业术语**）。未列出的工具集回退原名。
# 运行环境提示映射：对无 env 依赖但依赖运行环境的工具集，给出具体引导
TOOLSET_RUNTIME_HINTS: dict[str, str] = {
    "browser": ("需要 Chromium 内核浏览器引擎（由 agent-browser CLI 驱动，Playwright 仅作 Chromium "
                 "二进制来源之一，并非运行时引擎）。推荐 `npx agent-browser install --with-deps` 安装；"
                 "本机已装 Edge/Chrome 可零下载启用：设置环境变量 AGENT_BROWSER_EXECUTABLE_PATH "
                 "指向其 exe 路径；也可 `npx playwright install chromium` 作为备选（装到 "
                 "~/.cache/ms-playwright 后会被自动识别）。"),
    "code_execution": ("需要在 POSIX 兼容系统下运行（Linux/macOS/WSL）。"
                        "Windows 原生支持受限，建议使用 WSL 或 Docker 环境。"),
    "cronjob": ("点击「一键检测安装」自动配置后即可使用。"
                 "启用后任务会在后台线程中按周期自动执行。"),
    "browser-cdp": ("需要本地 Edge 浏览器开启远程调试。操作步骤：1. 关闭所有 Edge 窗口；"
                    "2. 运行：msedge.exe --remote-debugging-port=9222；"
                    "3. 在此页面点击「配置」→「自动检测 Edge CDP 端点」。"),
    "delegation": ("子任务委派自动可用，无需额外配置。"
                    "支持将复杂任务拆解给子智能体并行处理。"),
    "kanban": ("点击「一键检测安装」自动配置后即可使用。"
                "数据存储在 HERMES_HOME/kanban.db 中。"),
    "session_search": ("历史检索自动可用，无需额外配置。"
                        "检索过往会话与结论，数据来自本地会话库（SQLite）。"),
    "todo": ("待办清单自动可用，无需额外配置。"),
    "project": ("项目管理自动可用，无需额外配置。"),
    "clarify": ("澄清提问自动可用，无需额外配置。"
                 "信息不足时向用户追问关键细节。"),
    "memory": ("长期记忆自动可用，无需额外配置。"
                "跨会话记住偏好、约定与事实。"),
    "file": ("文件读写自动可用，无需额外配置。"
              "纯 Python 实现，无终端依赖。"),
    "skills": ("技能库自动可用，无需额外配置。"
                "加载 SKILL.md 形式的专家技能。"),
    "web": ("联网检索内置 8 个后端：firecrawl(默认,需 KEY)、searxng(免费,需 SEARXNG_URL)、"
             "brave-free(免费额度,需 BRAVE_SEARCH_API_KEY)、ddgs(免费无需任何 Key,首次自动安装 SDK)、"
             "tavily/exa/parallel(需对应 KEY)、xai(需 XAI_API_KEY,手动 opt-in)。"
             "零配置即可联网：ddgs 无需任何 Key；或自托管 SearXNG 填 SEARXNG_URL。"),
    "x_search": ("X/Twitter 检索需要 XAI_API_KEY。"
                  "在工具集配置页面填写 XAI_API_KEY 环境变量。"),
    "computer_use": ("需要安装桌面自动化驱动（cua-driver），点击「配置」→「一键检测安装」自动完成。"
                     "Windows 已原生支持，Linux 需 X11/XWayland 环境。"),
    "vision": ("需要视觉模型 API Key 或本地视觉后端。"
                "请在模型配置中确认已设置支持视觉的模型。"),
    "image_gen": ("需要图像生成 API Key。"
                   "厂商预设：OpenAI DALL-E / Stability AI / 硅基流动。"),
    "video_gen": ("需要视频生成 API Key。"
                   "厂商预设：Runway / Pika / 可灵。"),
    "video": ("需要 FFmpeg 视频处理引擎。点击「一键检测安装」自动下载安装。"),
    "tts": ("需要语音合成 API Key。厂商预设：OpenAI TTS / 火山引擎。"),
    "spotify": ("需要 Spotify 账号授权。请先在系统浏览器登录 Spotify 后重试。"),
    "feishu_doc": ("需要飞书开放平台 App ID 与 App Secret。"
                    "在飞书开发者后台创建应用后获取。"),
    "feishu_drive": ("需要飞书开放平台 App ID 与 App Secret。"
                      "在飞书开发者后台创建应用后获取。"),
    "discord": ("需要 Discord Bot Token。"
                 "在 Discord Developer Portal 创建 Bot 后获取。"),
    "discord_admin": ("需要 Discord Bot Token 及管理员权限。"),
    "homeassistant": ("需要 HomeAssistant 长生命周期 Token 和 Base URL。"),
    "hermes-yuanbao": ("需要腾讯元宝 API Key。"),
}

# 最后测试结果缓存（模块级，进程内持久化，不落盘）
_last_test_results: dict[str, dict] = {}


TOOLSET_LABELS: dict[str, tuple[str, str]] = {
    "file": ("文件读写", "读写本地文件、浏览目录、进程内执行 Python（纯 Python，无终端）"),
    "code_execution": ("代码执行", "在沙箱内运行代码做计算、数据处理与验证"),
    "memory": ("长期记忆", "跨会话记住偏好、约定与事实"),
    "skills": ("技能库", "加载 SKILL.md 形式的专家技能扩展能力"),
    "browser": ("浏览器自动化", "自动打开网页、点击填表、抓取页面内容"),
    "browser-cdp": ("浏览器(CDP)", "基于 Chrome DevTools 协议的高级网页自动化"),
    "web": ("联网检索", "检索互联网信息与实时资料（部分后端需 API Key）"),
    "x_search": ("X 检索", "检索 X/Twitter 公开信息（需 XAI_API_KEY）"),
    "session_search": ("历史检索", "检索过往会话与结论"),
    "sogou_weixin": ("公众号检索", "通过搜狗微信搜索检索微信公众号文章（免费无需 Key）"),
    "vision": ("图像理解", "识别图片、截图与文档影像中的内容"),
    "image_gen": ("图像生成", "按描述生成图片（需配置）"),
    "video_gen": ("视频生成", "按描述生成短视频（需配置）"),
    "video": ("视频处理", "视频剪辑与转码相关处理（需配置）"),
    "tts": ("语音合成", "把文本转为语音（需配置）"),
    "computer_use": ("电脑自动化", "操作本机应用完成重复性工作（需配置）"),
    "cronjob": ("定时任务", "按 cron / 自然语言周期定时执行任务"),
    "todo": ("待办清单", "拆解与跟踪任务清单"),
    "kanban": ("看板", "以看板管理任务状态、阻塞与评论"),
    "project": ("项目管理", "管理项目、阶段与产出"),
    "delegation": ("子任务委派", "把复杂任务拆给子智能体并行处理"),
    "clarify": ("澄清提问", "信息不足时向用户追问关键细节"),
    "feishu_doc": ("飞书文档", "读写飞书文档（需配置）"),
    "feishu_drive": ("飞书云盘", "读写飞书云盘（需配置）"),
    "discord": ("Discord", "Discord 集成（需配置）"),
    "discord_admin": ("Discord 管理", "Discord 管理（需配置）"),
    "homeassistant": ("HomeAssistant", "智能家居集成（需配置）"),
    "hermes-yuanbao": ("元宝", "腾讯元宝集成（需配置）"),
    "terminal": ("终端命令", "已按架构禁用（改用进程内 run_python，无需 Git Bash）"),
    "spotify": ("Spotify", "Spotify 音乐控制（需配置）"),
}


# 工具集分类：解决功能重复问题，让用户清楚每个工具属于哪一类
TOOLSET_CATEGORIES: dict[str, str] = {
    # 浏览器自动化（browser vs browser-cdp 都是浏览器，但 browser-cdp 是高级版）
    "browser": "🌐 浏览器",
    "browser-cdp": "🌐 浏览器",
    # 代码执行
    "code_execution": "💻 代码",
    "terminal": "💻 代码",
    # 电脑操作
    "computer_use": "🖥️ 电脑",
    "file": "🖥️ 电脑",
    # 搜索检索
    "web": "🔍 搜索",
    "x_search": "🔍 搜索",
    "session_search": "🔍 搜索",
    # 任务管理（todo vs kanban vs project 都是任务管理，但侧重点不同）
    "todo": "📋 任务",
    "kanban": "📋 任务",
    "project": "📋 任务",
    "delegation": "📋 任务",
    # 内容生成
    "image_gen": "🎨 内容",
    "video_gen": "🎨 内容",
    "video": "🎨 内容",
    "tts": "🎨 内容",
    "vision": "🎨 内容",
    # 社交平台
    "discord": "💬 社交",
    "discord_admin": "💬 社交",
    "feishu_doc": "💬 社交",
    "feishu_drive": "💬 社交",
    "hermes-yuanbao": "💬 社交",
    # 智能家居
    "homeassistant": "🏠 家居",
    # 其他
    "memory": "🧠 记忆",
    "skills": "🧠 记忆",
    "clarify": "🧠 记忆",
    "cronjob": "⏰ 定时",
    "spotify": "🎵 娱乐",
}

# 工具集所需运行时环境变量（模块级，供前端显示和查询用）
ENV_REQUIRED: dict[str, list[str]] = {
    "browser-cdp": ["BROWSER_CDP_URL"],
    "image_gen": ["FAL_KEY", "OPENAI_API_KEY", "SILICONFLOW_API_KEY", "STABILITY_API_KEY"],
    "video_gen": ["RUNWAY_API_KEY", "PIKA_API_KEY"],
    "tts": ["OPENAI_API_KEY", "VOLC_API_KEY"],
    "x_search": ["XAI_API_KEY"],
    "spotify": ["SPOTIFY_ACCESS_TOKEN"],
    "homeassistant": ["HOMEASSISTANT_TOKEN"],
    "hermes-yuanbao": ["YUANBAO_API_KEY"],
    "discord": ["DISCORD_BOT_TOKEN"],
    "discord_admin": ["DISCORD_BOT_TOKEN"],
    "feishu_doc": ["FEISHU_APP_ID", "FEISHU_APP_SECRET"],
    "feishu_drive": ["FEISHU_APP_ID", "FEISHU_APP_SECRET"],
    "web": ["EXA_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY", "PARALLEL_API_KEY", "SEARXNG_URL", "BRAVE_SEARCH_API_KEY", "XAI_API_KEY"],
    "vision": ["OPENAI_API_KEY", "SILICONFLOW_API_KEY"],
}


# ── 工具集发现缓存 ───────────────────────────────────────────────
# registry.get_available_toolsets() 会逐个运行工具集 check_fn（含网络健康探测），
# 单次约 4s；若不缓存，每次进入「工具集成」都会卡数秒。这里缓存矩阵，并以
# 「过期返回旧值 + 后台刷新」策略保证前台永远即时返回；toolset 切换/配置/测试后
# 调 invalidate_toolset_cache() 强制下次同步刷新。
_TOOLSET_MATRIX_CACHE = {"ts": 0.0, "data": None, "computing": False}
_TOOLSET_CACHE_TTL = 120.0  # 秒

def _compute_toolset_matrix() -> dict:
    global _TOOLSET_MATRIX_CACHE
    import time as _t
    register_pure_python_tools()  # 必须先注册纯 Python 工具，否则矩阵为空
    from tools.registry import registry
    data = registry.get_available_toolsets() or {}
    _TOOLSET_MATRIX_CACHE["data"] = data
    _TOOLSET_MATRIX_CACHE["ts"] = _t.time()
    _TOOLSET_MATRIX_CACHE["computing"] = False
    return data

def get_toolset_matrix(force: bool = False) -> dict:
    """返回工具集能力矩阵（带缓存）。force=True 时同步重算（用于状态变更后）。"""
    global _TOOLSET_MATRIX_CACHE
    import time as _t, threading
    cached = _TOOLSET_MATRIX_CACHE["data"]
    if force or cached is None:
        return _compute_toolset_matrix()
    if (_t.time() - _TOOLSET_MATRIX_CACHE["ts"]) >= _TOOLSET_CACHE_TTL and not _TOOLSET_MATRIX_CACHE["computing"]:
        # 已过期：后台刷新，前台立即返回旧值（避免用户每次进入都等网络探测）
        _TOOLSET_MATRIX_CACHE["computing"] = True
        threading.Thread(target=_compute_toolset_matrix, daemon=True).start()
    return cached

def invalidate_toolset_cache() -> None:
    """toolset 状态变更（禁用/启用/配置/测试）后失效缓存，下次进入重新探测。"""
    global _TOOLSET_MATRIX_CACHE
    _TOOLSET_MATRIX_CACHE["data"] = None
    _TOOLSET_MATRIX_CACHE["computing"] = False

def discover_toolsets() -> list[dict]:
    """进程内枚举工具集能力矩阵，替代网关的 /v1/toolsets。

    每项返回：
      name / label / purpose            工具集名、中文名、一句话用途
      available / configured            依赖与凭证是否齐备（check_fn 通过）
      enabled                           用户启用意图（非架构禁用且未被用户手动禁用），与 available 独立
      disabled                          当前是否处于禁用态（架构禁用 或 用户手动禁用）
      arch_disabled                     是否被架构显式禁用（terminal，不可由用户切换）
      tools: [{name, disabled}]         该工具集下的工具（含单工具级禁用初始态）
      requirements                      缺失的环境变量/依赖（available=False 时的提示）
    """
    register_pure_python_tools()
    from tools.registry import registry
    from hermes_config import get_hermes_home, read_config_yaml

    _tool_env()
    home = get_hermes_home()
    agent_cfg = (read_config_yaml(home).get("agent", {}) or {})
    disabled_tools = set(agent_cfg.get("disabled_tools", []) or [])
    user_disabled_ts = set(agent_cfg.get("disabled_toolsets", []) or [])
    arch_set = set(DISABLED_TOOLSETS)
    cfg_env = dict(agent_cfg.get("env") or {})
    matrix = get_toolset_matrix() or {}
    out: list[dict] = []
    for name in sorted(matrix.keys()):
        info = matrix.get(name) or {}
        available = bool(info.get("available"))
        # 运行时环境检查：模块可加载(available) ≠ 运行配置就绪
        # 对有已知 env 要求的工具集，检查至少一个所需环境变量已设置
        _env_required = ENV_REQUIRED.get(name, [])
        _env_set = [v for v in _env_required if os.environ.get(v) or cfg_env.get(v)]
        env_configured = len(_env_required) == 0 or len(_env_set) > 0
        arch_disabled = name in arch_set
        user_dis = name in user_disabled_ts
        is_disabled = arch_disabled or user_dis
        label, purpose = TOOLSET_LABELS.get(
            name, (name, info.get("description") or "")
        )
        req = list(info.get("requirements") or [])
        # 合并运行时环境变量到 requirements，使前端"配置"弹窗显示输入框
        if _env_required:
            for v in _env_required:
                if v not in req:
                    req.append(v)
        # 诊断未配置原因：有缺失 env 则列出；否则查运行时环境提示
        reason = ""
        if not available:
            missing = [v for v in req if not os.environ.get(v)]
            if missing:
                reason = "缺少配置：" + ", ".join(missing)
            else:
                hint = TOOLSET_RUNTIME_HINTS.get(name)
                if hint:
                    reason = hint
                else:
                    reason = "依赖运行环境/专用服务未就绪，点「测试」查看详情"
        elif not env_configured:
            missing_env = [v for v in _env_required if not (os.environ.get(v) or cfg_env.get(v))]
            reason = "缺少运行时配置：" + ", ".join(missing_env[:5])
            if len(missing_env) > 5:
                reason += " 等" + str(len(missing_env)) + "个"
        else:
            # 可用且已配置
            pass
        tool_names = list(info.get("tools") or [])
        tools_out = [{"name": tn, "disabled": tn in disabled_tools} for tn in tool_names]
        # 附加运行时环境提示（模块可加载但缺运行时配置时也显示）
        runtime_hint = TOOLSET_RUNTIME_HINTS.get(name, "") if (not available) or (available and not env_configured) else ""
        # 上次测试结果（模块级缓存，带5分钟TTL #8）
        _last_test = _last_test_results.get(name)
        last_test = None
        if _last_test:
            import time as _t
            if _t.time() - (_last_test.get("ts") or 0) < 300:  # 5分钟TTL
                last_test = _last_test

        out.append({
            "name": name, "label": label, "purpose": purpose,
            "available": available, "configured": env_configured,
            "enabled": (not arch_disabled) and (not user_dis), "disabled": is_disabled,
            "arch_disabled": arch_disabled,
            "tools": tools_out,
            "requirements": req,
            "reason": reason,
            "runtime_hint": runtime_hint,
            "last_test": last_test,
            "configured_env": _env_set,
            "category": TOOLSET_CATEGORIES.get(name, "🔧 其他"),
            "dangerous": name in DANGEROUS_TOOLSETS,
        })
    return out


def _tool_env() -> None:
    """把 config.yaml 中 agent.env 注入 os.environ（工具集 check_fn 读环境变量）。"""
    try:
        from hermes_config import get_hermes_home, read_config_yaml
        agent = (read_config_yaml(get_hermes_home()).get("agent", {}) or {})
        for k, v in (agent.get("env") or {}).items():
            os.environ.setdefault(str(k), str(v))
    except Exception:  # noqa: BLE001
        pass


def configure_toolset(name: str, values: dict) -> dict:
    """保存工具集依赖配置（API Key 等）到 config.yaml 的 agent.env，并即时生效。

    传空字符串的值会从配置中移除。保存后失效 check_fn 缓存，available 实时重查。
    """
    from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml
    from tools.registry import invalidate_check_fn_cache
    home = get_hermes_home()
    cfg = read_config_yaml(home)
    agent = cfg.get("agent") or {}
    env = dict(agent.get("env") or {})
    changed = False
    removed: list[str] = []
    for k, v in (values or {}).items():
        k = str(k).strip()
        if not k:
            continue
        v = str(v or "").strip()
        if v:
            if env.get(k) != v:
                env[k] = v
                changed = True
        else:
            if k in env:
                del env[k]
                removed.append(k)
                changed = True
    if changed:
        agent["env"] = env
        # 统一用 update_config_yaml（深合并），与 set_toolset_disabled 保持同一条写入路径
        from hermes_config import update_config_yaml
        full = read_config_yaml(home)
        full.setdefault("agent", {})
        if env:
            full["agent"]["env"] = env
        else:
            full["agent"].pop("env", None)
        update_config_yaml(home, full)
        # 同步环境变量：新增/更新注入，移除项从 os.environ 清理（仅本次移除的）
        for k, v in env.items():
            os.environ[k] = str(v)
        for k in removed:
            os.environ.pop(k, None)
        invalidate_check_fn_cache()
    invalidate_toolset_cache()
    return {"ok": True, "name": name, "env": env}


def _runtime_probe(name: str) -> tuple[list[dict], str]:
    """对依赖运行环境（无 env）的工具集做特定环境探测，返回 (checks, detail)。"""
    checks: list[dict] = []
    detail_parts: list[str] = []
    hint = TOOLSET_RUNTIME_HINTS.get(name, "")
    if hint:
        detail_parts.append("运行环境要求：" + hint)

    if name == "browser-cdp":
        # 探测 Edge 浏览器和 CDP 端点
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
            checks.append({"var": "BROWSER_CDP_URL", "set": True, "value": cdp_url[:60] + "…" if len(cdp_url) > 60 else cdp_url})
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
                # 用 WebSocket 轻量 ping 验证端点是否存活（Edge 的 HTTP 端点始终返回 404）
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
    elif name == "vision":
        # 检查当前模型是否支持 vision
        try:
            from hermes_config import get_active_model_cfg
            _model = get_active_model_cfg(None)
            _model_name = (_model or {}).get("model", "未知")
            _has_vision = any(k in (_model_name or "").lower() for k in ("vision", "vl", "4v", "omni", "gemini"))
            checks.append({"var": "当前模型", "set": True, "value": _model_name})
            checks.append({"var": "模型支持视觉", "set": _has_vision, "value": "是" if _has_vision else "否（需切换至支持视觉的模型）"})
        except Exception:
            checks.append({"var": "当前模型", "set": False, "value": "读取失败"})
    elif name == "code_execution":
        # 检查 Python 沙箱
        import sys as _sys
        checks.append({"var": "Python 版本", "set": True, "value": _sys.version.split()[0]})
        checks.append({"var": "操作系统", "set": True, "value": _sys.platform})
        try:
            from tools.code_execution_tool import SANDBOX_AVAILABLE
            checks.append({"var": "沙箱就绪", "set": SANDBOX_AVAILABLE, "value": "是" if SANDBOX_AVAILABLE else "否（仅 POSIX 系统支持）"})
        except Exception:
            checks.append({"var": "沙箱就绪", "set": False, "value": "无法检测"})
    elif name == "computer_use":
        import sys as _sys, shutil as _shutil
        checks.append({"var": "操作系统", "set": True, "value": _sys.platform})
        # 确保 config.yaml 中的 HERMES_CUA_DRIVER_CMD 已注入 os.environ
        _tool_env()
        # 直接检查 cua-driver 二进制（不依赖 cua_backend 模块级缓存变量）
        _cua_cmd = os.environ.get("HERMES_CUA_DRIVER_CMD", "cua-driver")
        _driver_ok = bool(_shutil.which(_cua_cmd))
        if _driver_ok:
            checks.append({"var": "cua-driver", "set": True, "value": "可用"})
        else:
            checks.append({"var": "cua-driver", "set": False, "value": "未安装"})
            detail_parts.append("cua-driver 未安装。点击「一键检测安装」自动安装即可。")
    elif name == "web":
        # 检查联网后端（真实配置键：web.search_backend > web.backend）
        try:
            from hermes_config import read_config_yaml
            _cfg = read_config_yaml()
            _web = (_cfg.get("web") or {}) or {}
            _backend = (_web.get("search_backend") or _web.get("backend") or "").strip()
            checks.append({"var": "联网后端", "set": bool(_backend), "value": _backend or "未配置（自动探测）"})
        except Exception:
            checks.append({"var": "联网后端", "set": False})
    elif name == "browser":
        # 检查 Playwright 浏览器可用性
        try:
            from tools.browser_tool import check_browser_requirements
            _ok = bool(check_browser_requirements())
            checks.append({"var": "Playwright 浏览器", "set": _ok, "value": "可用" if _ok else "未安装/不可用（需 playwright install）"})
        except Exception as _e:
            checks.append({"var": "Playwright 浏览器", "set": False, "value": "检测异常：%s" % _e})
    elif name in ("image_gen", "video_gen", "tts"):
        # 检查对应 API Key 是否存在
        _key_map = {"image_gen": ["OPENAI_API_KEY", "SILICONFLOW_API_KEY", "STABILITY_API_KEY"],
                    "video_gen": ["RUNWAY_API_KEY", "PIKA_API_KEY"],
                    "tts": ["OPENAI_API_KEY", "VOLC_API_KEY"]}
        for _k in _key_map.get(name, []):
            _v = os.environ.get(_k, "")
            checks.append({"var": _k, "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name in ("discord", "discord_admin"):
        _v = os.environ.get("DISCORD_BOT_TOKEN", "")
        checks.append({"var": "DISCORD_BOT_TOKEN", "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name in ("feishu_doc", "feishu_drive"):
        _id = os.environ.get("FEISHU_APP_ID", "")
        _secret = os.environ.get("FEISHU_APP_SECRET", "")
        checks.append({"var": "FEISHU_APP_ID", "set": bool(_id), "value": "已设置" if _id else "未设置"})
        checks.append({"var": "FEISHU_APP_SECRET", "set": bool(_secret), "value": "已设置" if _secret else "未设置"})
    elif name == "homeassistant":
        _token = os.environ.get("HOMEASSISTANT_TOKEN", "")
        _url = os.environ.get("HOMEASSISTANT_URL", "")
        checks.append({"var": "HOMEASSISTANT_TOKEN", "set": bool(_token), "value": "已设置" if _token else "未设置"})
        checks.append({"var": "HOMEASSISTANT_URL", "set": bool(_url), "value": _url or "未设置"})
    elif name == "hermes-yuanbao":
        _v = os.environ.get("YUANBAO_API_KEY", "")
        checks.append({"var": "YUANBAO_API_KEY", "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name == "skills":
        # 检查技能目录
        from pathlib import Path as _P
        try:
            from hermes_config import get_hermes_home
            _skills_dir = _P(get_hermes_home()) / "skills"
            _count = len(list(_skills_dir.glob("*/SKILL.md"))) if _skills_dir.exists() else 0
            checks.append({"var": "技能目录", "set": _skills_dir.exists(), "value": "%s 个技能" % _count if _skills_dir.exists() else "目录不存在"})
        except Exception as _e:
            checks.append({"var": "技能目录", "set": False, "value": "检测异常：%s" % _e})
    elif name == "video":
        # 检查 FFmpeg 可用性
        import shutil as _sh
        _ff = _sh.which("ffmpeg")
        checks.append({"var": "FFmpeg", "set": bool(_ff), "value": _ff or "未安装（需安装 FFmpeg）"})
    elif name == "clarify":
        # 检查 clarify 工具是否注册
        try:
            from tools.registry import registry
            _tools = registry.get_tool_names_for_toolset("clarify")
            checks.append({"var": "clarify 工具", "set": len(_tools) > 0, "value": "%d 个工具" % len(_tools)})
        except Exception:
            checks.append({"var": "clarify 工具", "set": False, "value": "未注册"})
    elif name == "project":
        try:
            from tools.registry import registry
            _tools = registry.get_tool_names_for_toolset("project")
            checks.append({"var": "project 工具", "set": len(_tools) > 0, "value": "%d 个工具" % len(_tools)})
        except Exception:
            checks.append({"var": "project 工具", "set": False, "value": "未注册"})
    elif name == "cronjob":
        # 检查 cron 调度器是否运行
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
    elif name == "delegation":
        try:
            from tools.registry import registry
            _tools = registry.get_tool_names_for_toolset("delegation")
            checks.append({"var": "delegation 工具", "set": len(_tools) > 0, "value": "%d 个工具" % len(_tools)})
        except Exception:
            checks.append({"var": "delegation 工具", "set": False, "value": "未注册"})
    elif name == "kanban":
        from pathlib import Path as _P
        try:
            from hermes_config import get_hermes_home
            _db = _P(get_hermes_home()) / "kanban.db"
            checks.append({"var": "kanban.db", "set": _db.exists(), "value": "存在" if _db.exists() else "未初始化（使用看板工具后自动创建）"})
        except Exception as _e:
            checks.append({"var": "kanban.db", "set": False, "value": "检测异常：%s" % _e})
    elif name == "session_search":
        from pathlib import Path as _P
        try:
            from hermes_config import get_hermes_home
            _db = _P(get_hermes_home()) / "desktop" / "sessions.db"
            _count = 0
            if _db.exists():
                from sessions import count_conversations
                _count = count_conversations()
            checks.append({"var": "sessions.db", "set": _db.exists(), "value": "%d 条会话" % _count if _db.exists() else "不存在"})
        except Exception:
            checks.append({"var": "sessions.db", "set": False})
    elif name == "x_search":
        _v = os.environ.get("XAI_API_KEY", "")
        checks.append({"var": "XAI_API_KEY", "set": bool(_v), "value": "已设置" if _v else "未设置（需配置 XAI_API_KEY）"})
    elif name == "image_gen":
        for _k in ["FAL_KEY", "OPENAI_API_KEY", "SILICONFLOW_API_KEY", "STABILITY_API_KEY"]:
            _v = os.environ.get(_k, "")
            checks.append({"var": _k, "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name == "video_gen":
        for _k in ["RUNWAY_API_KEY", "PIKA_API_KEY"]:
            _v = os.environ.get(_k, "")
            checks.append({"var": _k, "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name == "tts":
        for _k in ["OPENAI_API_KEY", "VOLC_API_KEY"]:
            _v = os.environ.get(_k, "")
            checks.append({"var": _k, "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name == "discord":
        _v = os.environ.get("DISCORD_BOT_TOKEN", "")
        checks.append({"var": "DISCORD_BOT_TOKEN", "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name == "discord_admin":
        _v = os.environ.get("DISCORD_BOT_TOKEN", "")
        checks.append({"var": "DISCORD_BOT_TOKEN", "set": bool(_v), "value": "已设置" if _v else "未设置"})
    elif name == "feishu_doc":
        _id = os.environ.get("FEISHU_APP_ID", "")
        _secret = os.environ.get("FEISHU_APP_SECRET", "")
        checks.append({"var": "FEISHU_APP_ID", "set": bool(_id), "value": "已设置" if _id else "未设置"})
        checks.append({"var": "FEISHU_APP_SECRET", "set": bool(_secret), "value": "已设置" if _secret else "未设置"})
    elif name == "feishu_drive":
        _id = os.environ.get("FEISHU_APP_ID", "")
        _secret = os.environ.get("FEISHU_APP_SECRET", "")
        checks.append({"var": "FEISHU_APP_ID", "set": bool(_id), "value": "已设置" if _id else "未设置"})
        checks.append({"var": "FEISHU_APP_SECRET", "set": bool(_secret), "value": "已设置" if _secret else "未设置"})
    elif name == "video":
        import shutil as _shutil_v
        _ff = _shutil_v.which("ffmpeg")
        if _ff:
            checks.append({"var": "FFmpeg", "set": True, "value": f"已安装（{_ff}）"})
        else:
            checks.append({"var": "FFmpeg", "set": False, "value": "未安装（点击「一键检测安装」自动下载）"})
    elif name == "spotify":
        _token = os.environ.get("SPOTIFY_ACCESS_TOKEN", "")
        checks.append({"var": "Spotify 授权", "set": bool(_token), "value": "已授权" if _token else "未授权（需登录 Spotify）"})

    detail = "\n".join(detail_parts) if detail_parts else ""
    return checks, detail


def test_toolset(name: str) -> dict:
    """配置诊断级测试：逐项检查依赖，返回详细报告（每项是否设置 + check_fn 结果 + 运行时探测）。

    结果缓存到 _last_test_results 供 discover_toolsets 的 last_test 字段使用。
    """
    _tool_env()  # 确保 config.yaml 中的 env 已注入 os.environ
    from tools.registry import registry
    check = None
    env_vars: list[str] = []
    try:
        reqs = registry.get_toolset_requirements()
        info = reqs.get(name, {}) or {}
        check = info.get("check_fn")
        env_vars = list(info.get("env_vars") or [])
    except Exception:  # noqa: BLE001
        pass
    checks = [{"var": v, "set": bool(os.environ.get(v))} for v in env_vars]
    missing = [v for v in env_vars if not os.environ.get(v)]

    # 运行时探测（针对无 env 的工具集）
    runtime_checks, runtime_detail = _runtime_probe(name)

    avail = False
    reason = ""
    detail = ""
    if missing:
        reason = "缺少配置：" + ", ".join(missing)
        detail = "以下环境变量未设置，导致依赖判定不满足：\n" + "\n".join(
            "  - %s：未设置" % v for v in missing)
    elif check is not None:
        # 尝试获取 check_fn 的更多诊断信息
        check_fn_detail = ""
        try:
            # 先尝试用标准方式调用
            avail = bool(check())
        except Exception as e:  # noqa: BLE001
            import traceback as _tb
            reason = "依赖检测异常：%s" % e
            detail = "check_fn 抛出异常：%s\n%s" % (e, _tb.format_exc())
            avail = False
        else:
            if not avail:
                reason = "环境校验未通过"
                detail_parts = ["环境变量已齐备，但环境校验（check_fn）未通过。"]
                if runtime_detail:
                    detail_parts.append(runtime_detail)
                # 尝试获取更具体的失败原因：对已知工具集添加额外探测
                try:
                    # 再次调用 check_fn 但捕获其 stderr 输出（很多 check_fn 内部有 print/log）
                    import io as _io
                    import sys as _sys
                    _stderr_capture = _io.StringIO()
                    _old_stderr = _sys.stderr
                    _sys.stderr = _stderr_capture
                    try:
                        check()
                    except Exception:
                        pass
                    finally:
                        _sys.stderr = _old_stderr
                    _captured = _stderr_capture.getvalue().strip()
                    if _captured:
                        check_fn_detail = _captured[:500]
                except Exception:
                    pass
                if check_fn_detail:
                    detail_parts.append("check_fn 内部诊断：" + check_fn_detail)
                detail_parts.append("点击「试用」实际调用可看到真实错误信息。")
                detail = "\n".join(detail_parts)
            else:
                detail = "所有依赖检查通过，工具集可用。"
                if runtime_detail:
                    detail += "\n" + runtime_detail
    else:
        avail = True
        detail = "无环境变量依赖，工具集可用。"
        if runtime_detail:
            detail += "\n" + runtime_detail

    # 合并常规检查与运行时探测
    all_checks = checks + runtime_checks

    result = {"ok": True, "name": name, "available": avail,
              "missing": missing, "reason": reason, "detail": detail,
              "checks": all_checks}
    # 缓存测试结果（模块级，进程内持久化）
    _last_test_results[name] = {
        "available": avail,
        "reason": reason,
        "detail": detail[:200],
        "checks": all_checks,
        "ts": __import__("time").time(),
    }
    invalidate_toolset_cache()
    return result


_TOOLSET_CFG_LOCK = threading.Lock()

def set_toolset_disabled(toolset_name: str, disabled: bool) -> dict:
    """工具集级开关：写 config.yaml 的 agent.disabled_toolsets（设置中心开关用）。

    与 discover_toolsets / _resolve_disabled_toolsets 保持一致：这里持久化的是
    **工具集名**，真正决定 Agent 生效状态的是合并架构禁用后的 disabled_toolsets。
    使用线程锁防止高频切换导致的 race condition（#15）。
    """
    from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml

    with _TOOLSET_CFG_LOCK:
        home = get_hermes_home()
        cfg = read_config_yaml(home)
        agent = cfg.get("agent") or {}
        cur = list(agent.get("disabled_toolsets") or [])
        if disabled and toolset_name not in cur:
            cur.append(toolset_name)
        elif not disabled and toolset_name in cur:
            cur = [t for t in cur if t != toolset_name]
        agent["disabled_toolsets"] = cur
        update_config_yaml(home, {"agent": agent})
    invalidate_toolset_cache()
    return {"ok": True, "tool": toolset_name, "disabled": disabled,
            "disabled_toolsets": cur}


# ============================================================================
# 8) 审批命令执行（纯 Python 进程内删除，无 shell / 无 Git Bash）
# ============================================================================
def execute_approved_command(cmd: str, timeout: int = 120) -> dict:
    """审批弹窗「批准执行」与 HTTP 桥接共用的命令执行器。

    Library 模式已禁用 terminal 工具集，本环境**不支持任何 shell 命令执行**。因此这里
    不 shell out，而是识别删除类命令（rm -rf / rmdir / del / remove / delete + 路径）后，
    用纯 Python（pathlib / shutil）在进程内安全删除——跨平台、零 shell 依赖，天然规避
    Windows 下 `rm` 不存在 / 缺 Git Bash 导致执行失败的问题。

    命令字符串来自本系统自己生成的 [APPROVAL_REQUIRED] 标记、且经用户在弹窗中显式确认，
    属于已授权行为。仅支持文件/目录删除；其余命令一律拒绝（符合无终端架构）。

    `timeout` 保留以兼容 pywebview 调用约定（纯 Python 删除为同步、瞬时操作）。
    """
    import re as _re
    import shutil as _shutil
    from pathlib import Path as _Path

    raw = (cmd or "").strip()
    if not raw:
        return {"ok": False, "error": "命令为空", "command": cmd}

    if not _re.search(
        r"(?:^|[\s(])(?:rm\s+-[rf]+|rmdir|del|rm|remove|delete)\b", raw, _re.I
    ):
        return {"ok": False, "command": cmd,
                "error": "本环境不支持 shell 命令执行；仅支持文件/目录删除操作。"}

    candidates: list[str] = []
    for grp in _re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', raw):
        candidates.append(grp[0] or grp[1] or grp[2])
    _skip = {"rm", "-rf", "-r", "-f", "rmdir", "/s", "/q", "del",
             "remove", "delete", "/c", "/k"}
    targets = [c for c in candidates
               if c.lower() not in _skip and not c.startswith("-")]
    if not targets:
        return {"ok": False, "error": "未能从命令中解析出待删除路径", "command": cmd}

    results: list[str] = []
    overall_ok = True
    for t in targets:
        p = _Path(t).expanduser()
        if not p.exists():
            results.append(f"{t}：不存在（跳过）")
            continue
        try:
            if p.is_dir():
                _shutil.rmtree(p, ignore_errors=False)
            else:
                p.unlink()
            results.append(f"{t}：已删除")
        except Exception as _e:  # noqa: BLE001
            overall_ok = False
            results.append(f"{t}：删除失败 - {_e}")

    return {"ok": overall_ok, "rc": 0 if overall_ok else 1,
            "stdout": "\n".join(results), "stderr": "", "command": cmd}


# 审批闭环：Agent 在回答里写 [APPROVAL_REQUIRED: cmd] 即触发前端弹窗。
# A1 优化：正则模块级编译一次，流式热路径每条 chunk 调用本函数时不再重复编译。
_APPROVAL_RE = re.compile(r"\[APPROVAL_REQUIRED:\s*(.+?)\]")


def extract_approval(text: str) -> "str | None":
    """从助手文本里提取待审批命令（供 main.py 渲染审批弹窗）。

    正则已在模块级编译一次（A1 优化）：流式热路径每条 chunk 调用本函数时
    仅做一次 O(text) 匹配，不再重复编译同一正则。
    """
    m = re.search(_APPROVAL_RE, text or "")
    return m.group(1).strip() if m else None
