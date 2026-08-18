from __future__ import annotations

import json
import os
import queue
import re
import threading
from typing import Any, Callable, Iterator
import file_tools
import host_tools




def _render_html(text: str) -> str:
    """把助手文本渲染成 HTML（与 main.render_markdown 同扩展，避免循环导入 main）。"""
    try:
        import markdown as _md
        return _md.markdown(text or "", extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
                            output_format="html")
    except Exception:
        import html as _h
        return "<pre>%s</pre>" % _h.escape(text or "")

MAX_TOOL_OUTPUT = file_tools.MAX_TOOL_OUTPUT

_REGISTERED = False
_REGISTER_LOCK = threading.Lock()


class _CancelRequested(Exception):
    """由 cancel_event 在回调中触发，用于最佳努力地尽早中断 run_conversation。

    Hermes 的 run_conversation() 没有原生 cancel；我们把一个 threading.Event 传入
    流式内核，在 on_delta / on_tool_* / on_reasoning 回调里检查它，置位即抛出本异常，
    让 worker 线程尽快退出（避免长时间工具循环继续烧 token / 写文件）。
    """


# ============================================================================
# 0) 工具集策略：单一事实源
# ============================================================================
# Library 模式下始终禁用的工具集（terminal = spawn-per-call shell，需要 Git Bash /
# PortableGit）。build_agent 与 discover_toolsets 都引用它，保证「设置中心显示的启用
# 状态」与「Agent 实际启用的工具集」永远一致。
DISABLED_TOOLSETS: list[str] = ["terminal"]

# 4 个自动化工具集：默认启用、无感调用。
# 用户可在「工具与集成中心」显式禁用其中任意一个；禁用选择会写入 config.yaml 的
# agent.disabled_toolsets 并持久化，重启或重新注册（例如打开工具面板）时不会被覆盖。
AUTOMATION_TOOLSETS: tuple[str, ...] = (
    "browser",         # 浏览器自动化
    "browser-cdp",     # 浏览器（CDP）
    "computer_use",    # 电脑自动化
    "code_execution",  # 代码执行
)

# 危险工具集：试用时会实际写入数据，需前端二次确认
DANGEROUS_TOOLSETS: frozenset[str] = frozenset({
    "file", "memory", "todo", "kanban", "cronjob",
})


def ensure_automation_defaults() -> dict:
    """启动时归一化工具集禁用名单（幂等，默认不写回 config.yaml）。

    关键修正（#Bug1）：4 个自动化工具集（browser / browser-cdp / computer_use /
    code_execution）默认启用，但**用户可以显式禁用**，且禁用选择必须持久化。
    因此本函数**不再**从 ``agent.disabled_toolsets`` / ``agent.disabled_tools`` 中
    强行剔除这些工具集——旧版本这样做，会导致用户在设置中心关闭某个自动化工具集后，
    在下次启动 / 重新注册（打开工具面板即触发 ``discover_toolsets`` →
    ``register_pure_python_tools``）时被静默还原，开关形同虚设。

    terminal 始终禁用由 ``_resolve_disabled_toolsets`` 在构造时统一叠加，无需在此处理。
    本函数现在只做幂等校验：确认 config.yaml 可正常读取，不修改任何用户配置。
    """
    try:
        from hermes_config import get_hermes_home, read_config_yaml
        home = get_hermes_home()
        read_config_yaml(home)  # 触发读取以暴露配置损坏（fail-fast，不写回）
        return {"ok": True, "changed": False}
    except Exception as e:  # noqa: BLE001
        print("[ensure_automation_defaults] warn:", e)
        return {"ok": False, "error": str(e)}


# ============================================================================
# 1) 注册：内置工具发现 + 纯 Python 覆盖 + 宿主工具 + 原生委派 + 业务扩展点
# ============================================================================
def register_pure_python_tools() -> dict:
    """把内置工具集 + 纯 Python 文件工具（覆盖）+ 宿主工具注册进 Hermes registry。幂等。

    关键点（与网关启动等价）：必须先调用 ``discover_builtin_tools()`` 把全部内置工具
    模块（browser / computer_use / cron / code_execution / memory / web / mcp …）导入
    并注册到全局 registry，否则 AIAgent 构造时 ``get_tool_definitions`` 只能看到已注册
    的工具——本进程若不主动发现，就只剩本模块 override 的 ``file`` 工具，浏览器 / 电脑
    自动化 / cron / 代码执行等能力将全部丢失（功能退化）。
    terminal 工具集由 build_agent 的 ``disabled_toolsets`` 在构造时剔除。
    """
    global _REGISTERED
    with _REGISTER_LOCK:
        if _REGISTERED:
            return {"ok": True, "already": True}
        from tools.registry import registry, discover_builtin_tools

        # 等价网关启动：导入并注册全部内置工具模块（仅注册；check_fn 在取 schema 时才跑）
        discover_builtin_tools()

        # 冻结(onefile)兜底：discover_builtin_tools 内部用 tools_path.glob("*.py") 枚举
        # 工具模块，但 PyInstaller 只把 tools 包打进 .pyc，冻结态 glob 找不到任何 .py，
        # 于是绝大多数内置工具集（web / memory / skills / code_execution / kanban …）
        # 不会被注册——既让设置中心「工具集」面板只显示几个，也使 EXE 内 Agent 实际无法
        # 使用这些工具。改用 pkgutil.iter_modules(tools.__path__) 枚举已冻结进二进制、
        # 可被 import 的模块名并逐一导入（各模块导入时即 self-register）。
        try:
            import pkgutil as _pkgutil
            import importlib as _importlib
            import tools as _tools_pkg
            _seen: set[str] = set()
            for _mi in _pkgutil.iter_modules(_tools_pkg.__path__):
                _mn = "tools." + _mi.name
                if _mn in ("tools.registry", "tools.mcp_tool"):
                    continue
                _seen.add(_mn)
                try:
                    _importlib.import_module(_mn)
                except Exception:
                    pass
            # 安全网：极少数冻结环境下 __path__ 不可枚举时，显式尝试关键工具模块
            if len(_seen) < 8:
                for _name in ("web", "memory", "skills", "code_execution", "kanban",
                              "computer_use", "cronjob", "todo", "project", "vision",
                              "image_gen", "video_gen", "session_search", "clarify",
                              "delegation", "browser", "browser_cdp", "x_search",
                              "feishu_doc", "feishu_drive", "discord", "discord_admin",
                              "homeassistant", "hermes_yuanbao", "tts", "video"):
                    try:
                        _importlib.import_module("tools." + _name)
                    except Exception:
                        pass
        except Exception:
            pass

        registered: list[str] = []
        # 纯 Python 文件工具（覆盖内置 file 工具集，零 subprocess）+ run_python
        registered += file_tools.register_into(registry)
        # 宿主能力：预览用户 ASGI 应用 / 停止预览 / 运行时装库
        registered += host_tools.register_into(registry)

        # 子智能体委派：使用 Hermes **原生** tools.delegate_tool（导入即触发模块级
        # registry.register，带完整原生 schema：goal/context/tasks/role/background +
        # 动态限额描述；toolset=delegation）。模型自主调用路径由
        # AIAgent._dispatch_delegate_task(parent_agent=self) 接管；深度限制由原生
        # delegation.max_spawn_depth（默认 1=扁平）执行；配置统一读 config.yaml
        # delegation.*（与设置中心「委派」面板同源，见 frameworks.get_delegation_config）。
        try:
            import tools.delegate_tool  # noqa: F401
            registered.append("delegate_task")
        except Exception as e:  # noqa: BLE001
            print("[register_pure_python_tools] native delegation import warn:", e)

        # 业务扩展点：把本示例复制到自己的项目后，在 app_tools/ 里实现
        # `register_into(registry) -> list[str]`，这里会自动调用（不存在则跳过）。
        try:
            import app_tools
            hook = getattr(app_tools, "register_into", None)
            if callable(hook):
                registered += list(hook(registry) or [])
        except Exception as e:  # noqa: BLE001
            print("[register_pure_python_tools] app_tools warn:", e)

        # 归一化工具集禁用名单（不再覆盖用户显式禁用的自动化工具集，见 ensure_automation_defaults）
        try:
            ensure_automation_defaults()
        except Exception as e:  # noqa: BLE001
            print("[register_pure_python_tools] ensure_automation_defaults warn:", e)

        _REGISTERED = True
        return {"ok": True, "registered": registered}


# ============================================================================
# 2) AIAgent 工厂
# ============================================================================
def _resolve_provider(vendor: str) -> str:
    """厂商键 → Hermes provider 名（36 家厂商预设见 hermes_config.VENDOR_PRESETS）。"""
    try:
        from hermes_config import VENDOR_PRESETS
    except Exception:
        VENDOR_PRESETS = {}
    return (VENDOR_PRESETS.get(vendor, {}) or {}).get("provider", vendor)


def _resolve_disabled_toolsets(web_search: bool) -> list[str]:
    """terminal 始终禁用；合并用户手动禁用的工具集；未开启联网时再把 web + browser 一并禁用。

    web_search=True（默认）不额外禁用，保留 web/browser 供 Agent 联网检索与自动化。
    用户手动开关（工具集成界面）通过 config.yaml 的 agent.disabled_toolsets 持久化，
    在此合并进真正传给 build_agent 的 disabled_toolsets，保证「设置中心显示的启用
    状态」与「Agent 实际生效状态」一致。
    """
    from hermes_config import get_hermes_home, read_config_yaml
    disabled = list(DISABLED_TOOLSETS)
    try:
        agent_cfg = (read_config_yaml(get_hermes_home()).get("agent", {}) or {})
        disabled.extend(agent_cfg.get("disabled_toolsets", []) or [])
    except Exception:  # noqa: BLE001
        pass
    if not web_search:
        disabled.extend(["web", "browser"])
    return list(dict.fromkeys(disabled))


# 通用系统提示词（**无任何业务措辞**）：说明本环境的工具边界，避免模型幻想 shell。
SYSTEM_PROMPT = """你是运行在一个 **Hermes 桌面应用**内的智能体，进程内直接执行工具。

环境边界（务必遵守）：
1. **没有终端 / shell**。`bash`、`cmd`、`ls`、`dir`、`rm` 等命令都不存在。
   - 浏览目录 → `list_dir`
   - 读文件 → `read_file`；写文件 → `write_file`；改文件 → `patch`
   - 搜索 → `search_files`
   - 任何脚本化操作（复制/移动/删除/解压/数据处理/HTTP 请求）→ `run_python`
     （进程内执行 Python，变量与 import 跨调用保留）
2. 相对路径一律相对**项目根目录**解析；绝对路径原样遵从。
   - **常规产物 / 导出**写到 `output/` 下；但「修改本应用自身的功能或界面」时，
     直接编辑对应的**源码文件**，不要另写一份到 output/。
3. 生成的 Web 应用（FastHTML/ASGI）可用 `preview_asgi_app(dir=...)` 在宿主内起本地预览；
   缺第三方库时用 `install_library(pkg=..., dir=...)` 安装后直接预览；`stop_preview` 关闭。
4. 复杂任务可用 `delegate_task` 拆给子智能体并行处理；跨会话事实用记忆工具沉淀。

本应用的代码结构（修改自身功能前必须先读对应文件，严禁凭空编造不存在的组件）：
- 前端是**原生 ES 模块 + FastHTML 服务端渲染**，**不是 React / Vue**。
- 页面骨架（侧栏、顶栏、对话区、各抽屉）由 `routes/pages.py` 用 FastHTML 组件渲染。
- 前端交互逻辑在 `static/src/*.js`（`chat.js` 对话 / `app.js` 装配 / `views.js` 各视图 /
  `panels/*.js` 各面板）；样式在 `static/app.css`。
- 后端接口在 `routes/*.py`（`chat.py` 对话、`features.py`、`loops.py`、`misc.py` …）。

修改本应用自身功能 / 界面时的硬性要求（杜绝「只给代码片段或教程、声称完成却没改文件」）：
- **直接动手改文件**：先 `read_file` 读目标文件 → 用 `patch` / `write_file` **真实修改** →
  再用 `read_file` **回读确认**改动已落盘。绝不要只输出代码块或教程来代替实际修改。
- **前端改动优先走静态文件**：界面 / 交互类需求优先改 `static/src/*.js` 与 `static/app.css`
  （浏览器刷新即生效；你改完后应用会**自动重载**，用户立刻能看到变化）。
- **服务端改动需重启**：改 `routes/*.py` 后必须重启进程才生效；你**无法自行重启**，
  改完请明确告知用户「需要重启应用」，由用户重启——不要假装已经生效。
- **先定位再改**：用 `search_files`（关键词如「产物」「convList」「sidebar」「btnArtifacts」）
  或 `list_dir` 找到真正相关的文件与元素 id，再动手，避免改到不存在的组件。

行为准则：**先做后说**。能用工具拿到的事实不要猜测，不要只描述计划而不调用工具；
完成后用简洁中文说明做了什么、改了哪些文件、用户是否需要重启应用。
"""
