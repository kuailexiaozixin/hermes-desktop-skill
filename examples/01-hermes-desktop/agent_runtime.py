"""agent_runtime.py — Hermes Desktop 通用底座的**集成内核**（Library 进程内模式）

这是一个标准、通用的 Hermes Desktop 底座内核：只提供「进程内集成 Hermes Python
Library」的完整桥接能力，**不绑定任何业务**。未来项目复制本目录，在 `app_tools/`
里加自己的业务工具即可（`app_tools.register_into(registry)` 会被自动调用）。

架构（全部来自 hermes_agent 0.19.0 源码实证，见 references/01-library-api.md）：
  * `from run_agent import AIAgent` 在**当前进程内**跑 Agent —— 无网关、无 Node、无 HTTP 代理。
  * `disabled_toolsets=["terminal"]` 彻底禁用 spawn-per-call 的终端工具，从而**不需要
    Git Bash / PortableGit**；文件与脚本能力改由纯 Python 工具承担（file_tools.py）。
  * `registry.register(..., toolset="file", override=True)` 用纯 Python handler 覆盖内置
    read_file/write_file/patch/search_files，并新增 list_dir / run_python（零 subprocess）。
  * `host_tools.py` 提供宿主内预览（preview_asgi_app / stop_preview）与运行时装库
    （install_library，进程内 pip.main --target <root>/.deps）。
  * AIAgent 非线程安全 → 每轮对话新建；run_conversation() 同步阻塞 → worker 线程 +
    queue.Queue 桥接成 SSE 字节流。
  * 文本增量走 run_conversation(stream_callback=...)（**方法参数**）；
    工具/推理事件走 AIAgent(__init__) 的**构造器回调**。

底座契约（可被未来项目复用）：
  * `stream_agent_chat(..., agent_factory=build_agent)` —— agent_factory 可注入，
    离线测试用 FakeAIAgent 替换真实 AIAgent（见 tests/test_channels_bridge.py）。
  * `run_agent` / `tools.*` 全部**懒导入**：未安装 hermes-agent 时本模块仍可 import
    （结构门禁 / CI / 离线测试都能跑）。
"""
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


def _build_request_overrides(model_cfg: dict) -> "dict | None":
    """把逐模型采样/格式参数归一成 AIAgent 的 ``request_overrides``。

    Hermes Library 的 ``AIAgent`` 只认透传字典 ``request_overrides``（见
    ``scripts/api-baseline.json:54``），不直接接收 ``temperature`` / ``top_p`` /
    ``stop`` / ``response_format``。本函数负责转换：

    - ``temperature`` / ``top_p`` / ``top_logprobs`` → 原样透传（OpenAI 兼容 provider 通用）；
    - ``stop_sequences``（逗号分隔字符串）→ ``stop``（列表）；
    - ``response_format``（``"json_object"``）→ ``{"type": "json_object"}``。

    仅当确有参数时返回 dict，否则返回 ``None``（不覆盖 AIAgent 默认行为）。
    """
    ro: dict = {}
    for f in ("temperature", "top_p"):
        v = model_cfg.get(f)
        if v not in (None, ""):
            try:
                ro[f] = float(v)
            except (TypeError, ValueError):
                pass
    if model_cfg.get("top_logprobs") not in (None, ""):
        try:
            ro["top_logprobs"] = int(model_cfg["top_logprobs"])
        except (TypeError, ValueError):
            pass
    s = model_cfg.get("stop_sequences")
    if s not in (None, ""):
        ro["stop"] = [x.strip() for x in str(s).split(",") if x.strip()]
    rf = model_cfg.get("response_format")
    if rf not in (None, ""):
        ro["response_format"] = {"type": str(rf)}
    return ro or None


def build_agent(model_cfg: dict, *,
                max_iterations: int | None = None,
                ephemeral_system_prompt: str | None = None,
                tool_start_callback: Callable | None = None,
                tool_complete_callback: Callable | None = None,
                reasoning_callback: Callable | None = None,
                tool_progress_callback: Callable | None = None,
                enabled_toolsets: list[str] | None = None,
                web_search: bool = True) -> Any:
    """根据模型配置构造进程内 AIAgent（terminal 已禁用）。

    web_search=True（默认）保留 web + browser 工具集，使 Agent 可联网检索；
    web_search=False 时禁用（离线模式，避免无意义的联网工具调用）。
    """
    register_pure_python_tools()
    from run_agent import AIAgent

    # 循环面板开关：记忆循环（Memory Loop）与目标循环（Goal 上下文）。默认关闭 →
    # skip_memory=True / skip_context_files=True；用户在「🔁 循环」面板开启后新会话生效。
    # ② 默认开启 Hermes 持久记忆（纯本地、零依赖、配置即开）
    _memory_on = True
    _goal_on = False
    try:
        from frameworks import get_loop_flags
        _flags = get_loop_flags()
        _memory_on = bool(_flags.get("memory_enabled"))
        _goal_on = bool(_flags.get("goal_enabled"))
    except Exception as _e:  # noqa: BLE001
        print("[build_agent] loop flags warn:", _e)
        # 兜底：从 config.yaml 的 [memory] 段读取
        try:
            from hermes_config import read_config_yaml
            _mem_cfg = (read_config_yaml().get("memory", {}) or {})
            _memory_on = bool(_mem_cfg.get("memory_enabled", True))
        except Exception:
            _memory_on = True  # Hermes 默认即开启

    # 需求3：Soul 人格开关 + 自定义系统提示词（从 config.yaml 读取，会话生效）
    _custom_sp = ""
    _soul_on = False
    try:
        from hermes_config import read_config_yaml
        _acfg = read_config_yaml().get("agent") or {}
        _custom_sp = (_acfg.get("system_prompt") or "").strip()
        _soul_on = bool(_acfg.get("soul_enabled"))
    except Exception:
        pass

    vendor = model_cfg.get("vendor") or "deepseek"
    provider = _resolve_provider(vendor)
    # MOA 虚拟 provider：构造前校验预设存在，缺失则降级到默认厂商，
    # 避免 AIAgent.__init__ 在 agent_init.py:816 分支解析 MoAClient 时抛 KeyError 使对话崩溃。
    _moa_failed = False
    if provider == "moa":
        try:
            from hermes_cli.config import load_config
            from hermes_cli.moa_config import resolve_moa_preset
            _preset = model_cfg.get("model") or "default"
            resolve_moa_preset(load_config().get("moa") or {}, _preset)  # KeyError → 预设不存在
        except KeyError:
            print(f"[build_agent] MoA 预设 '{model_cfg.get('model')}' 缺失，降级到 deepseek")
            vendor = "deepseek"
            provider = _resolve_provider(vendor)
            _moa_failed = True
        except Exception:
            pass
    # MoA 降级到 deepseek 后，model 字段仍可能是预设名（如 "default"），对 deepseek 无效 → 回退默认模型
    _model = "deepseek-chat" if _moa_failed else (model_cfg.get("model") or "deepseek-chat")
    kwargs: dict[str, Any] = dict(
        provider=provider,
        model=_model,
        # enabled_toolsets=None → Hermes 默认「全部工具集」（browser/computer_use/cron/
        # code_execution/memory/web/mcp…），与网关启动等价；只用 disabled 做减法剔除
        # terminal。**绝不硬编码 ["file"]**，否则上述能力会被全部砍掉（功能退化）。
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=_resolve_disabled_toolsets(web_search),
        quiet_mode=True,
        save_trajectories=False,
        skip_memory=not _memory_on,
        skip_context_files=not _goal_on,
        load_soul_identity=_soul_on,
    )
    if model_cfg.get("api_key"):
        kwargs["api_key"] = model_cfg["api_key"]
    if model_cfg.get("base_url"):
        kwargs["base_url"] = model_cfg["base_url"]
    if model_cfg.get("max_tokens"):
        try:
            kwargs["max_tokens"] = int(model_cfg["max_tokens"])
        except (TypeError, ValueError):
            pass
    rc = model_cfg.get("reasoning_config")
    if rc and isinstance(rc, dict):
        kwargs["reasoning_config"] = rc
    # 逐模型采样/格式参数：经 request_overrides 透传给底层 provider 请求
    # （AIAgent 不直接接收 temperature/top_p/stop/response_format，见 api-baseline.json:54）。
    _ro = _build_request_overrides(model_cfg)
    if _ro:
        kwargs["request_overrides"] = _ro
    if max_iterations:
        kwargs["max_iterations"] = int(max_iterations)
    if ephemeral_system_prompt:
        kwargs["ephemeral_system_prompt"] = ephemeral_system_prompt
    elif _custom_sp:
        kwargs["ephemeral_system_prompt"] = _custom_sp
    if tool_start_callback:
        kwargs["tool_start_callback"] = tool_start_callback
    if tool_complete_callback:
        kwargs["tool_complete_callback"] = tool_complete_callback
    if reasoning_callback:
        kwargs["reasoning_callback"] = reasoning_callback
    if tool_progress_callback:
        kwargs["tool_progress_callback"] = tool_progress_callback
    agent = AIAgent(**kwargs)

    # ── 强制「工具调用护栏」对所有模型生效 ────────────────────────────────
    # Hermes 默认仅对硬编码名单 TOOL_USE_ENFORCEMENT_MODELS 内的模型注入
    # TOOL_USE_ENFORCEMENT_GUIDANCE（"真正调用工具、别只描述"，属 stable_parts 权重最高
    # 段）。免费/小模型多不在名单 → 表现为「只反问、只描述、不动手」。系统提示按请求构建
    # （system_prompt.build_system_prompt_parts 每轮读 agent._tool_use_enforcement），
    # 故在进程内 agent 上直接置 True 即可让护栏对当前所有模型生效。
    try:
        agent._tool_use_enforcement = True
    except Exception as _e:  # noqa: BLE001
        print("[build_agent] force tool_use_enforcement warn:", _e)

    # 单工具级禁用（工具集级禁用见 DISABLED_TOOLSETS）。config.yaml 的
    # agent.disabled_tools 列出需关闭的单个工具名；剔除后 agent.tools（OpenAI 格式）
    # 与 agent.valid_tool_names 同步收缩，对话循环据此不再把该工具交给模型。
    try:
        from hermes_config import get_hermes_home, read_config_yaml
        home = get_hermes_home()
        disabled_tools = set(
            (read_config_yaml(home).get("agent", {}) or {}).get("disabled_tools", []) or []
        )
        if disabled_tools:
            agent.tools = [
                t for t in (agent.tools or [])
                if (t.get("function", {}) or {}).get("name") not in disabled_tools
            ]
            if getattr(agent, "valid_tool_names", None):
                agent.valid_tool_names = {
                    n for n in agent.valid_tool_names if n not in disabled_tools
                }
    except Exception as _e:  # noqa: BLE001
        print("[build_agent] disabled_tools filter warn:", _e)

    return agent


def build_trial_agent(toolset_name: str, model_cfg: dict, *,
                      max_iterations: int | None = None,
                      ephemeral_system_prompt: str | None = None,
                      tool_start_callback: Callable | None = None,
                      tool_complete_callback: Callable | None = None,
                      reasoning_callback: Callable | None = None,
                      web_search: bool = True) -> Any:
    """试用专用 Agent 工厂：强制启用目标工具集，确保 trial 时模型能调用该工具。"""
    register_pure_python_tools()
    from run_agent import AIAgent
    from tools.registry import invalidate_check_fn_cache
    invalidate_check_fn_cache()

    vendor = model_cfg.get("vendor") or "deepseek"
    provider = _resolve_provider(vendor)
    # MOA 虚拟 provider：构造前校验预设存在，缺失则降级到默认厂商，
    # 避免 AIAgent.__init__ 在 agent_init.py:816 分支解析 MoAClient 时抛 KeyError 使对话崩溃。
    _moa_failed = False
    if provider == "moa":
        try:
            from hermes_cli.config import load_config
            from hermes_cli.moa_config import resolve_moa_preset
            _preset = model_cfg.get("model") or "default"
            resolve_moa_preset(load_config().get("moa") or {}, _preset)  # KeyError → 预设不存在
        except KeyError:
            print(f"[build_agent] MoA 预设 '{model_cfg.get('model')}' 缺失，降级到 deepseek")
            vendor = "deepseek"
            provider = _resolve_provider(vendor)
            _moa_failed = True
        except Exception:
            pass
    # MoA 降级到 deepseek 后，model 字段仍可能是预设名（如 "default"），对 deepseek 无效 → 回退默认模型
    _model = "deepseek-chat" if _moa_failed else (model_cfg.get("model") or "deepseek-chat")
    kwargs: dict[str, Any] = dict(
        provider=provider,
        model=_model,
        enabled_toolsets=[toolset_name],
        disabled_toolsets=["terminal"],
        quiet_mode=True,
        save_trajectories=False,
        skip_memory=True,
        skip_context_files=True,
        load_soul_identity=False,
    )
    if model_cfg.get("api_key"):
        kwargs["api_key"] = model_cfg["api_key"]
    if model_cfg.get("base_url"):
        kwargs["base_url"] = model_cfg["base_url"]
    if max_iterations:
        kwargs["max_iterations"] = int(max_iterations)
    if ephemeral_system_prompt:
        kwargs["ephemeral_system_prompt"] = ephemeral_system_prompt
    if tool_start_callback:
        kwargs["tool_start_callback"] = tool_start_callback
    if tool_complete_callback:
        kwargs["tool_complete_callback"] = tool_complete_callback
    if reasoning_callback:
        kwargs["reasoning_callback"] = reasoning_callback

    agent = AIAgent(**kwargs)
    try:
        agent._tool_use_enforcement = True
    except Exception:
        pass
    return agent


# ============================================================================
# 3) 消息拆分 + SSE 编码
# ============================================================================
def _split_messages(messages: list[dict]) -> tuple[str, list[dict], Any]:
    """把 OpenAI messages 拆成 (system_message, conversation_history, user_message)。"""
    system_parts: list[str] = []
    convo: list[dict] = []
    last_user_content: Any = ""
    last_user_idx = -1
    for i, m in enumerate(messages or []):
        if m.get("role") == "user":
            last_user_idx = i
    for i, m in enumerate(messages or []):
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            continue
        if i == last_user_idx:
            last_user_content = content
            continue
        convo.append({"role": role, "content": content})
    system_message = "\n\n".join(p for p in system_parts if p)
    return system_message, convo, last_user_content


def _sse(obj: dict) -> bytes:
    return ("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8")


def _delta_chunk(text: str) -> bytes:
    return _sse({"choices": [{"index": 0, "delta": {"content": text},
                              "finish_reason": None}]})


def _preview(v: Any, n: int = 160) -> str:
    try:
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    except Exception:
        s = str(v)
    return s[:n]


def _parse_tool_result(result: Any) -> dict:
    """把工具返回的字符串/对象解析为 dict，供前端展示 ok/stdout/url/error 等。"""
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        try:
            return json.loads(result)
        except Exception:
            return {"ok": True, "raw": result}
    return {"ok": True, "raw": str(result)}


# ============================================================================
# 4) 思考分流：把 <thinking>…</thinking> 从正文里剥出来走 reasoning 通道
# ============================================================================
class _ThinkingSplitter:
    """增量流中把 ``<thinking>…</thinking>``（及 ``<think:6124c78e>…</think:6124c78e>``）
    包裹的推理文本分流到 reasoning 通道，其余作为 delta 透传给前端。

    免费/非推理模型不会触发原生 ``reasoning_callback``，但深度思考模式下被系统提示引导
    用 ``<thinking>`` 标签显式推理。标签常因分块而截断，这里用「后缀保留」策略缓冲可能
    未闭合的标签片段，待闭合或流结束再 flush，避免把半截标签渲染给用户。
    """

    _OPEN = ("<thinking>", "<think:6124c78e>")
    _CLOSE = ("</thinking>", "</think:6124c78e>")

    def __init__(self, emit_reasoning, emit_delta):
        self._emit_reasoning = emit_reasoning
        self._emit_delta = emit_delta
        self._in_think = False
        self._out = ""   # 待发的 delta 累积
        self._rea = ""   # 待发的 reasoning 累积
        self._tail = ""  # 跨块边界的开/闭标签前缀残留

    @staticmethod
    def _earliest(s: str, tags, start: int):
        best_idx = -1
        best_tag = None
        for tag in tags:
            idx = s.find(tag, start)
            if idx != -1 and (best_idx == -1 or idx < best_idx):
                best_idx = idx
                best_tag = tag
        return best_idx, best_tag

    @staticmethod
    def _partial_len(s: str, tags) -> int:
        """s 末尾可能是某个 tag 的前缀的最大长度（不含完整 tag）。"""
        best = 0
        for tag in tags:
            for k in range(1, len(tag)):
                if s.endswith(tag[:k]):
                    best = max(best, k)
        return best

    def feed(self, chunk: str):
        data = self._tail + chunk
        self._tail = ""
        i = 0
        n = len(data)
        while i < n:
            if self._in_think:
                ci, ctag = self._earliest(data, self._CLOSE, i)
                if ci == -1:
                    keep = self._partial_len(data[i:], self._CLOSE)
                    self._rea += data[i:n - keep]
                    self._tail = data[n - keep:]
                    i = n
                else:
                    self._rea += data[i:ci]
                    self._flush_rea()
                    self._in_think = False
                    i = ci + len(ctag)
            else:
                oi, otag = self._earliest(data, self._OPEN, i)
                if oi == -1:
                    keep = self._partial_len(data[i:], self._OPEN)
                    self._out += data[i:n - keep]
                    self._tail = data[n - keep:]
                    i = n
                else:
                    self._out += data[i:oi]
                    self._flush_out()
                    self._in_think = True
                    i = oi + len(otag)

    def _flush_out(self):
        if self._out:
            self._emit_delta(self._out)
            self._out = ""

    def _flush_rea(self):
        if self._rea:
            self._emit_reasoning(self._rea)
            self._rea = ""

    def finish(self):
        if self._tail:
            if self._in_think:
                self._rea += self._tail
            else:
                self._out += self._tail
            self._tail = ""
        self._flush_out()
        self._flush_rea()


# ============================================================================
# 5) 一轮对话：worker 线程 + 队列 → SSE 字节流
# ============================================================================
# 推理强度档位（升序）：用于 deep_think 开关把 effort 提到「至少 high」、
# 但不降级用户已设的更高档位。来源：hermes-llms-full.txt Reasoning Effort 章节。
_EFFORT_ORDER = ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]


def _merge_deep_think_effort(current, target: str = "high") -> dict:
    """deep_think 开启时，返回合并推理强度的 ``reasoning_config``。

    - current 已含 effort 且档位 ≥ target：保留用户更强的设定（绝不降级）；
    - 否则把 effort 提到 target（默认 ``"high"``）；
    - 保留 current 中的其它键（如部分 provider 需要的其它推理参数）。

    返回 dict 形状 ``{"effort": "<level>"}``，与批量运行（``hermes_features.batch_run``）
    及逐模型「推理强度」下拉框（``hermes_config.reasoning_effort_to_config``）约定一致。
    """
    base = current if isinstance(current, dict) else {}
    rc = dict(base)
    cur = str(rc.get("effort", "")).strip().lower()
    if cur not in _EFFORT_ORDER or _EFFORT_ORDER.index(cur) < _EFFORT_ORDER.index(target):
        rc["effort"] = target
    return rc


def stream_agent_chat(messages: list[dict], model_cfg: dict, *,
                      max_iterations: int | None = None,
                      approval_check: Callable[[str], "str | None"] | None = None,
                      deep_think: bool = False,
                      web_search: bool = True,
                      agent_factory: Callable | None = None,
                      timeout: float | None = None,
                      cancel_event: "threading.Event | None" = None,
                      ) -> Iterator[bytes]:
    """进程内运行 AIAgent 并产出 SSE 字节流（前端 EventSource 直接消费）。

    事件契约（前端按 type 分发；文本增量沿用 OpenAI chunk 形状）：
        {"choices":[{"delta":{"content": "..."}}]}            文本增量
        {"type":"reasoning","text":str}                        思考过程（可折叠）
        {"type":"action","tool":str,"preview":str}             工具开始
        {"type":"action_result","tool":str,"preview":str,"result":dict}
        {"error":{"message":str}}                              异常

    * ``approval_check(assistant_text) -> cmd|None``：可选，用于在结束时补发
      ``[APPROVAL_REQUIRED: cmd]`` 标记（自定义审批闭环）。
    * ``deep_think=True`` 时：把推理强度（``reasoning_config.effort``）提到「至少 high」
      （不降级用户已设的更高档位），并用 ``_ThinkingSplitter`` 把 ``<thinking>`` 段分流到 reasoning。
    * ``agent_factory``：默认 build_agent；离线测试注入 FakeAIAgent 工厂（tests/test_channels_bridge.py 中的 FakeAIAgent）。
    """
    factory = agent_factory or build_agent

    def _check_cancel():
        # 最佳努力中断：cancel 事件置位即抛出，让 worker 尽快退出（见 B3）。
        if cancel_event is not None and cancel_event.is_set():
            raise _CancelRequested()

    q: "queue.Queue[tuple]" = queue.Queue()
    SENTINEL = ("__end__",)
    splitter = None
    if deep_think:
        splitter = _ThinkingSplitter(
            emit_reasoning=lambda t: q.put(("reasoning", t)),
            emit_delta=lambda t: q.put(("delta", t)),
        )

    def on_tool_start(tool_call_id, name, display_args):  # noqa: ANN001
        _check_cancel()
        q.put(("action", name, _preview(display_args)))

    def on_tool_complete(tool_call_id, name, display_args, result):  # noqa: ANN001
        _check_cancel()
        # 同时发短 preview（日志标题）与解析后的 result（前端判定成功 / 展示 stdout / url）
        q.put(("action_result", name, _preview(result), _parse_tool_result(result)))

    def on_delta(delta):  # noqa: ANN001
        _check_cancel()
        if not delta:
            return
        if splitter is not None:
            splitter.feed(delta)
        else:
            q.put(("delta", delta))

    def on_reasoning(text):  # noqa: ANN001
        _check_cancel()
        if text:
            q.put(("reasoning", text))

    def on_tool_progress(name, *args, **kwargs):  # noqa: ANN001
        # MoA 参考模型事件（agent_init._moa_reference_relay 转发）：
        # name="moa.reference"(label,text,None,moa_index=,moa_count=) /
        #       "moa.aggregating"(aggregator,None,None,moa_ref_count=)
        _check_cancel()
        q.put(("tool_progress", name, args, kwargs))

    system_message, convo, user_content = _split_messages(messages)
    # run_conversation 的 user_message 仅接受 str（见 references/01-library-api.md:263-277）；
    # 图片等多模态内容不在此处构造 content block，而是由 routes/chat.py 经 vision_analyze
    # 工具交给模型查看（视觉模型返回原生像素、纯文本模型降级为辅助视觉模型描述）。
    # 因此 user_message 始终为字符串：取最后一条 user 消息的文本即可。
    user_message = user_content if isinstance(user_content, str) else ""

    # 硬超时：如果 timeout>0，启动一个守护线程在超时后向队列注入错误
    _timeout_timer: threading.Timer | None = None
    if timeout and timeout > 0:
        def _timeout_killer():
            q.put(("error", "执行超时（%.0fs），已自动终止" % timeout))
            q.put(SENTINEL)
        _timeout_timer = threading.Timer(timeout, _timeout_killer)
        _timeout_timer.daemon = True
        _timeout_timer.start()

    def worker():
        # 清空本线程编辑记录，确保静态/服务端文件改动只归因到本轮对话
        try:
            file_tools.reset_edited_files()
        except Exception:
            pass
        try:
            # 记录父模型配置，供对话中可能触发的子智能体委派继承凭据
            try:
                from frameworks import set_parent_model_cfg
                set_parent_model_cfg(model_cfg)
            except Exception:
                pass
            # 深度思考开关：在模型自带推理强度基础上，把 effort 提到「至少 high」
            # （不降级用户已设的更高档位）。仅作用于本轮 factory 调用，不改动传入的
            # model_cfg，避免影响并行 / 后续会话。
            effective_cfg = dict(model_cfg)
            if deep_think:
                effective_cfg["reasoning_config"] = _merge_deep_think_effort(
                    effective_cfg.get("reasoning_config"), target="high")
            agent = factory(
                effective_cfg, max_iterations=max_iterations,
                ephemeral_system_prompt=system_message or None,
                tool_start_callback=on_tool_start,
                tool_complete_callback=on_tool_complete,
                reasoning_callback=on_reasoning,
                tool_progress_callback=on_tool_progress,
                web_search=web_search,
            )
            # 记录当前父 agent（原生 delegate_task registry 兜底路径需要 parent_agent
            # 上下文；模型正常路径由 AIAgent._dispatch_delegate_task 自带 self）
            try:
                from frameworks import set_parent_agent
                set_parent_agent(agent)
            except Exception:
                pass
            result = agent.run_conversation(
                user_message=user_message,
                system_message=system_message or None,
                conversation_history=convo or None,
                stream_callback=on_delta,
            )
            final = ""
            messages_out = None
            if isinstance(result, dict):
                final = result.get("final_response") or ""
                messages_out = result.get("messages")
            if splitter is not None:
                splitter.finish()
            # 回传本轮被 Agent 改动的文件路径，使前端能把「AI 改了文件」真正呈现给用户
            # （静态文件自动重载、服务端文件提示重启），破除「声称成功但界面无变化」。
            _edited = []
            try:
                _edited = file_tools.get_edited_files()
            except Exception:
                pass
            q.put(("final", final, messages_out, _edited))
        except _CancelRequested:
            pass  # 用户已点停止：最佳努力中断，不打错误、正常收尾
        except Exception as e:  # noqa: BLE001
            q.put(("error", f"{type(e).__name__}: {e}"))
        finally:
            # 取消超时定时器（如果未超时则取消，已超时则无副作用）
            if _timeout_timer:
                _timeout_timer.cancel()
            q.put(SENTINEL)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    assistant_text = ""
    streamed_any = False
    final_text = ""
    final_messages = None
    changed_files = []
    errored = False
    while True:
        item = q.get()
        if item == SENTINEL:
            break
        kind = item[0]
        if kind == "delta":
            assistant_text += item[1]
            streamed_any = True
            yield _delta_chunk(item[1])
        elif kind == "reasoning":
            yield _sse({"type": "reasoning", "text": item[1]})
        elif kind == "action":
            yield _sse({"type": "action", "tool": item[1], "preview": item[2]})
        elif kind == "action_result":
            yield _sse({"type": "action_result", "tool": item[1],
                        "preview": item[2], "result": item[3]})
        elif kind == "tool_progress":
            # MoA 参考模型事件透传给前端（chat.js 渲染为「🔄 MOA 参考模型」折叠块）
            yield _sse({"type": "tool_progress", "name": item[1],
                        "args": item[2], "kwargs": item[3]})
        elif kind == "final":
            final_text = item[1] or ""
            final_messages = item[2]
            if len(item) > 3:
                changed_files = item[3] or []
        elif kind == "error":
            yield _sse({"error": {"message": item[1]}})
            errored = True

    # 若未产生任何增量但有最终文本（部分模型/路径不走 stream_callback），补发一次
    if not streamed_any and final_text:
        assistant_text = final_text
        yield _delta_chunk(final_text)

    # 自定义审批标记兜底
    if approval_check:
        try:
            cmd = approval_check(assistant_text)
        except Exception:
            cmd = None
        if cmd:
            yield _delta_chunk(f"\n\n[APPROVAL_REQUIRED: {cmd}]")

    # 收尾事件：把完整文本与消息历史交给前端持久化（多轮上下文契约）
    # html = 服务端渲染的 Markdown（含 language-mermaid 类），供前端做 Mermaid / 代码复制后处理
    # D2：错误路径（worker 异常 / 超时）不再下发 done，避免前端 error 提示被空 done 覆盖、
    #     重复触发 attachMsgActions 与用量上报；错误已由上方 error 事件呈现。
    if not errored:
        yield _sse({"type": "done", "final": assistant_text or final_text,
                    "html": _render_html(assistant_text or final_text),
                    "messages": final_messages,
                    "changed_files": changed_files})


# ============================================================================
# 6) 启动自检（替代网关 /health：进程内路线不起 HTTP 服务也能量健康）
# ============================================================================
def runtime_ready() -> dict:
    """确认 Library 可导入、关键回调面在位。未安装时优雅返回 importable:False。"""
    import inspect

    info: dict[str, Any] = {
        "importable": False, "version": None, "callbacks_ok": False,
        "tools_registered": False, "error": None,
    }
    try:
        import importlib.metadata as md
        info["version"] = md.version("hermes-agent")
        from run_agent import AIAgent

        info["importable"] = True
        params = inspect.signature(AIAgent.__init__).parameters
        rcp = inspect.signature(AIAgent.run_conversation).parameters
        info["callbacks_ok"] = (
            "tool_start_callback" in params
            and "tool_complete_callback" in params
            and "reasoning_callback" in params
            and "event_callback" in params
            and "stream_callback" in rcp
        )
        try:
            reg = register_pure_python_tools()
            info["tools_registered"] = bool(reg.get("ok"))
        except Exception as e2:  # noqa: BLE001
            info["error"] = f"{type(e2).__name__}: {e2}"
    except Exception as e:  # noqa: BLE001
        info["error"] = f"{type(e).__name__}: {e}"
    return info


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
