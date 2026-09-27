# 10 · `hermes_cli` 完整参考（Hermes 内置 CLI 包，0.19.0 顶层 146 个模块文件 + 3 个子包，含嵌套共 205 个 `.py`；口径均不含包根 `__init__.py`）

> 本文件是 `hermes_cli` 包的**完整、权威、逐模块参考**。
> `hermes_cli` 是 `hermes-agent==0.19.0` 自带的**统一 CLI 包**（`__version__="0.19.0"`），
> 也是 Library 的组成部分之一（与 `run_agent`/`tools`/`agent`/`batch_runner` 并列，均为顶层包）。
> 它的子命令包括 `chat` / `gateway` / `setup` / `status` / `cron` / `mcp` / `bundles` / `project` / `kanban` / `backup` / `doctor` / `plugins` / `portal` 等。
>
> 本文经 `hermes-agent==0.19.0` 已装包**逐模块读取 docstring + 用 `ast` 提取顶层公开名**核实（全程静态解析源码，不 `import` 任何 `hermes_cli` 模块，避免 TTY/网络副作用）；
> 全部 149 个顶层条目（146 个模块文件 + `subcommands`/`dashboard_auth`/`proxy` 三个子包，均不含包根 `__init__.py`）无一遗漏，按 13 个主题组编排；其中 8 个模块跨主题，在两组的表里各出现一次，第二处只留「见 2.x」指针与同一份代表 API，不是重复盘点。
> 含嵌套子模块共 205 个 `.py`（同一棵树内全部 `.py`，仅扣除包根 `__init__.py`）。
>
> **与 08 的边界**：`08-capability-integration.md` 讲「能力的行为语义」（Goals/Snapshots/MOA/Projects/Bundles 等
> 在进程内怎么用、有什么实战片段）；本文讲「`hermes_cli` 这个包里**有哪些模块、各自干什么、进程内能不能安全 import**」。
> 两文通过模块名互相交叉引用，但**不重复**能力语义。
>
> **与 02 的边界**：`02-integration-core.md` 讲「进程内三条集成路径与 SSE 桥接」；本文 §3 把「路径 B：复用 `hermes_cli` 逻辑」
> 做成完整的模块级清单，供需要时定位与调用。

---

> **路线平等声明**：调用 Python Library 有 5 条**平等可选**技术路线——进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`——**无先后顺序，按需选用其一**。本文聚焦 `hermes_cli` 包的模块清单：它既包含「进程内直跑路线可 `import` 复用的纯逻辑子模块」，也包含「spawn CLI 路线（起 `hermes` 子进程）才用到」的模块。其余跨进程路线见 `15-api-server.md`（API Server·`/v1`）与 `16-gateway-package.md`（Hermes 网关）。本文中「进程内直跑」仅作叙述对照，不代表该路线优先或推荐。

## 0. 本文定位与适用边界

`hermes_cli` 是 Hermes 的「命令行界面 + 大量内部逻辑」的承载包。它既是给用户敲命令的 CLI，
也内含许多**纯逻辑子模块**（配置读写、定时任务、MOA 预设、能力状态、看板存储等），
这些纯逻辑可以被桌面应用**进程内直接 `import` 复用**，不必起子进程。

但 `hermes_cli` 也包含大量**只在「起网关 / 起 Web Server / 终端交互 / 云端账号」时才需要**的模块，
进程内 Library 路线用不到。本文列出全部模块的**用途与代表 API**，供进程内复用挑选：

> **适用说明（与 `07` §1 一致）**：若选用**进程内直跑**路线，一般**不起 Hermes 网关、不 spawn `hermes` CLI 子进程、不开 API Server、不走 `/v1`**。
> 因此 `hermes_cli` 中凡是「起服务 / 监听端口 / 起子进程 / TTY 交互」的模块，
> 即使 `import` 成功也**一般不在桌面应用里直接调用其主函数**——它们是为网关/CLI/API Server 路线服务的；若选用对应跨进程路线则另作评估（见 `15`/`16`）。

---

## 1. 进程内直跑与跨进程路线的核心概念（必读）

### 1.1 什么叫「进程内」？

**进程（process）** 是操作系统分配资源的最小运行单位；一个正在运行的程序（含它的代码、内存、打开的文件）
就是一个进程。

- **进程内（in-process）**：在你的桌面应用**同一个进程**里，`import` Hermes 的 Library 并直接 `new AIAgent()`，
  Agent 跑在你程序的地址空间里，函数调用就是普通 Python 调用。这是 5 条平等可选路线中的「进程内直跑」路线。
- **跨进程（out-of-process，其余 4 条路线之一）**：你的程序**另外启动一个独立程序/进程**（例如 `hermes` 可执行、`hermes gateway` 服务），
  通过「进程间通信（IPC）」——HTTP、管道、socket——跟它对话。该路线（spawn CLI / Hermes 网关 / API Server·`/v1`）与进程内直跑路线**平等可选**，详见 `15`/`16`。

本技能默认走**进程内**：你的 EXE 里直接包含 `run_agent`/`tools`/`agent`/`hermes_cli`/`batch_runner` 这些包，
单一进程、单一 EXE 文件，Agent 计算发生在你自己的进程内。

### 1.2 什么叫「网关（gateway）」？什么叫「API Server」？

- **网关（gateway）**：Hermes 提供的一个**常驻后台服务进程**（顶层 `gateway` 包，即「Hermes Gateway——
  多平台消息集成」；`hermes_cli.gateway` 是它的 CLI 启动子命令），
  它内部起一个 HTTP 服务，对外暴露 OpenAI 兼容的 `/v1/chat/completions` 等端点
  （实现在 `gateway/platforms/api_server.py`，aiohttp；默认监听 `127.0.0.1:8642`），
  并把 Telegram/Slack/QQ/飞书等**消息平台**的消息「喂」给 Agent（即 `24` 个 `hermes-*` 平台集成靠它激活）。
  它是「一个独立服务 + 多平台接入」的中心节点。
- **API Server**：网关暴露 OpenAI 兼容 HTTP 接口的那一层（`gateway/platforms/api_server.py`，aiohttp；
  每个请求在服务端创建一个 `AIAgent` 执行）。注意：**`hermes_cli.web_server`（FastAPI）是
  Web UI / Dashboard**，不含 `/v1/chat/completions`，与 OpenAI 兼容 API Server 是两回事，勿混淆。
  （API Server 形态的完整落地见 `15-api-server.md`。）

进程内直跑路线**一般不用网关、不开 API Server**——Agent 直接在你的进程里算，前端（pywebview/FastHTML）直接调你的 Python 函数，
不需要一个「中间 HTTP 服务」来转发。若选用网关/API Server 路线（见 `15`/`16`），则由对应服务承担。

### 1.3 什么叫「spawn」？什么叫「子进程」？

- **子进程（child process）**：由当前进程**启动的另一个独立进程**。它有自己的内存空间，和父进程隔离。
- **spawn**：泛指「启动（派生）一个新进程」的动作（来自 Unix `fork`/`spawn`、Windows `CreateProcess`）。

所谓「不 spawn `hermes` 子进程」（进程内直跑路线的常见做法），就是**不要让桌面应用去执行 `hermes chat …`、`hermes gateway …` 这类命令行**，
再读它的 stdout/stderr 或 HTTP 端口来拿结果——那样 Agent 就跑在另一个进程里了。若选用 spawn CLI 路线（见本文 §3），则按需起子进程。

### 1.4 进程内直跑路线的根由（为什么它常作为叙述基线）

| 维度 | 进程内直跑路线 | 网关 / 子进程（跨进程路线） |
| --- | --- | --- |
| **部署形态** | 单个 EXE，双击即跑，零外部依赖 | 需常驻一个后台服务进程，或每次调用拉起 CLI |
| **通信开销** | 函数调用，纳秒~微秒级 | HTTP/管道往返，毫秒级 + 序列化成本 |
| **状态一致性** | Agent 对象、会话、配置同处一进程，内存共享 | 跨进程，状态需序列化/落盘同步，易漂移 |
| **打包体积** | 只打用到的包；PyInstaller hidden-import 可控 | 需把整个 CLI 运行时（TTY/服务/平台适配）全打进去，体积爆炸 |
| **崩溃隔离** | 无（同进程，Agent 崩=应用崩） | 有（子进程崩不影响父进程） |
| **平台集成** | 需自建桥（应用收消息→`run_conversation`） | 网关原生支持 24 个 `hermes-*` 平台 |
| **调试/门禁** | 直接断点、直接断言事件流 | 跨进程日志难追，HTTP 200「假绿」风险高 |

**结论性理由**：本技能面向的典型场景是「**已有一个桌面 GUI 应用，要在其中集成 Hermes 作为 AI 内核**」。
在这种场景里：
1. 应用**本来就有自己的窗口和事件循环**，不需要再起一个 HTTP 服务来「转发对话」——前端直接调 `AIAgent` 即可；
2. 交付物目标是**单文件 EXE**（见 `06-packaging.md`），起网关/起子进程会引入常驻服务、端口占用、生命周期管理，
   与「单 EXE、双击即跑」冲突；
3. 进程内调用能直接拿到 `AIAgent` 的 16 个构造器回调（`01` §4）做流式渲染，比「轮询 HTTP 流」简单且可靠；
4. 避免「HTTP 200 假绿」——Library 导入失败时 Web 仍返回 200（`07` §1 R6），进程内同步调用能在启动时立即暴露。

> **选用网关/子进程/API Server（`/v1`）路线会带来什么？**（详见 `15`/`16`）
> - **好处**：① 天然支持 24 个 `hermes-*` 消息平台（Telegram/Slack/飞书/QQ 等），无需自建桥；
>   ② 跨进程崩溃隔离（Agent 崩不拖垮宿主 GUI）；③ 多个前端/多语言客户端可共享同一个网关端点。
> - **坏处**：① 丧失单 EXE 交付，需常驻服务 + 端口管理；② 引入 HTTP 序列化开销与「假绿」风险；
>   ③ 打包体积与依赖面剧增（整个 CLI 运行时）；④ 状态跨进程同步复杂，调试困难。
> - **何时考虑放开**：当需求明确是「做一个 Hermes 网关/服务器、或要接消息平台机器人、或多客户端共享 Agent」
>   时，可走网关/CLI/API Server（`/v1`）路线——5 条路线平等可选，按需求选用其一（其余路线见 `15`/`16`），无默认或推荐之分。

---

## 2. 完整模块清单（149 个顶层条目，分 13 个主题组）

> 每行：模块 | 一句话真实用途（取自该模块的 docstring）| 代表顶层 API。第三列的每个名字都用 `ast` 解析已装包源码核对过，取的是该模块**自身命名空间**里的公开名：顶层 `def` / `async def` / `class` / 赋值（含带类型标注的赋值）/ `__all__`，以及写在顶层 `if` / `try` / `with` 块里的那些；不含下划线开头的名字，不含该模块 import 进来的第三方符号，也不含推测出来的名字。子包（`subcommands` / `dashboard_auth` / `proxy`）取 `__init__.py` 的再导出；`subcommands/__init__.py` 只有 docstring、无再导出，因此该行的代表 API 写成 `组内文件.py::名()` 形式，按那个文件自身的命名空间核对。

### 2.1 入口与命令分发（Entry & dispatch）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `main` | CLI 主入口（`hermes` 命令的总分发） | `main()` |
| `_parser` | argparse 顶层解析器构造 | `build_top_level_parser()` |
| `commands` | 斜杠命令定义与自动补全 | `COMMAND_REGISTRY` / `CommandDef` / `resolve_command()` |
| `subcommands` | 子命令 argparse 树的分包：每组一个 `build_<组名>_parser()`，由 `main.py` 挂载（40 个文件：39 组 + `_shared.py`） | `subcommands/gateway.py::build_gateway_parser()` / `subcommands/model.py::build_model_parser()` |
| `cli_commands_mixin` | 交互式 CLI 斜杠命令处理器（god-file 分解） | `CLICommandsMixin` |
| `cli_agent_setup_mixin` | `HermesCLI` 的 Agent 构造/会话恢复显示 | `CLIAgentSetupMixin` |
| `completion` | shell 补全脚本生成 | `generate_bash()` / `generate_zsh()` / `generate_fish()` |
| `oneshot` | `-z` 一次性模式（发一句拿结果即退出） | `run_oneshot()` |
| `send_cmd` | `hermes send`（从 shell 脚本管道文本给 Agent） | `cmd_send()` / `register_send_subparser()` |
| `relaunch` | CLI 统一自重启 | `relaunch()` |
| `console_engine` | 安全 Hermes 控制台命令引擎 | `HermesConsoleEngine` |

### 2.2 配置 / 环境 / 平台（Config / env / platform）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `config` | 配置管理（读/写 `config.yaml`） | `load_config()` / `save_config()` |
| `env_loader` | 跨入口统一加载 `.env` | `load_hermes_dotenv()` / `get_secret_source()` |
| `managed_scope` | IT 推送的、用户不可变配置/环境层 | `load_managed_config()` / `apply_managed_overlay()` |
| `managed_uv` | managed uv 单一路径管理 | `ensure_uv()` |
| `platforms` | 共享平台注册表 | `PlatformInfo` / `get_all_platforms()` |
| `build_info` | 构建期烘焙的元数据 | `get_build_sha()` |
| `default_soul` | 首次运行注入的默认 `SOUL.md` 模板 | `DEFAULT_SOUL_MD` |
| `dep_ensure` | 非 Python 运行时依赖的懒引导 | `ensure_dependency()` |
| `timeouts` | 超时常量解析 | `get_provider_request_timeout()` / `get_provider_stale_timeout()` |
| `stdio` | Windows 安全 stdio 配置 | `configure_windows_stdio()` |
| `profiles` | 多 profile 环境隔离（创建/切换/导出/别名/排除技能路径），`HERMES_PROFILE` 决定数据根 | `create_profile()` / `list_profiles()` / `get_active_profile()` |

### 2.3 认证 / 账号 / 凭证（Auth / accounts / secrets）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `auth` | 多 provider 认证系统 | `resolve_provider()` / `get_auth_status()` / `ProviderConfig` |
| `auth_commands` | 凭证池（credential-pool）子命令 | `auth_command()` / `auth_add_command()` |
| `copilot_auth` | GitHub Copilot 认证工具 | `copilot_device_code_login()` / `resolve_copilot_token()` |
| `dingtalk_auth` | 钉钉设备流授权 | `dingtalk_qr_auth()` / `begin_registration()` |
| `nous_account` | Nous Portal 账户权益归一 | `get_nous_portal_account_info()` |
| `nous_auth_keepalive` | Nous 长会话后台保活 | `start_nous_auth_keepalive()` |
| `nous_billing` | Nous 终端计费 HTTP 客户端 | `get_billing_state()` / `post_charge()` |
| `nous_subscription` | Nous 订阅托管工具能力 | `get_nous_subscription_features()` / `get_gateway_eligible_tools()` |
| `onepassword_secrets_cli` | 1Password 密钥 CLI 处理器 | `register_cli()` / `cmd_set()` |
| `secrets_cli` | Bitwarden 密钥 CLI 处理器 | `register_cli()` / `cmd_sync()` |
| `secret_prompt` | 掩码密钥输入 | `masked_secret_prompt()` |
| `memory_oauth` | memory provider OAuth HTTP 路由（被 `web_server` 挂载） | `start_memory_oauth()` / `router` |
| `memory_setup` | `hermes memory setup\|status` | `memory_command()` / `cmd_setup()` |
| `dashboard_register` | 自托管 dashboard OAuth 客户端注册 | `cmd_dashboard_register()` |
| `dashboard_auth` | Dashboard 认证 provider 框架（OAuth/Token 会话、provider 注册与列举） | `DashboardAuthProvider` / `register_provider()` |
| `pairing` | DM pairing 系统 CLI | `pairing_command()` |
| `portal_cli` | Nous Portal 人类可读入口 | `portal_command()` |

### 2.4 供应商 / 模型（Provider / model）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `providers` | provider 身份唯一真相 | `get_provider()` / `is_aggregator()` |
| `provider_catalog` | 统一 provider 目录（单一真相源） | `provider_catalog` / `provider_catalog_by_slug` |
| `models` | 规范模型目录与轻量校验 | `validate_requested_model()` / `ProviderEntry` |
| `model_catalog` | 远程模型目录拉取 | `get_catalog()` |
| `model_cost_guard` | 昂贵模型选择确认 | `expensive_model_warning()` |
| `model_normalize` | 每 provider 模型名归一 | `normalize_model_for_provider()` |
| `model_setup_flows` | 每 provider 选型向导流 | `bedrock_model_routable_from_region()` |
| `model_switch` | CLI/gateway 共享 `/model` 切换逻辑 | `switch_model()` |
| `codex_models` | Codex 模型发现 | `get_codex_model_ids()` |
| `fallback_cmd` | fallback provider 链管理 | `cmd_fallback()` / `cmd_fallback_add()` |
| `fallback_config` | 读取生效 fallback 链 | `get_fallback_chain()` |
| `xai_retirement` | 检测 2026-05-15 退役的 xAI 模型 | `find_retired_xai_refs()` / `apply_migration()` |
| `azure_detect` | Azure Foundry 端点自动检测 | `detect()` |
| `context_switch_guard` | 会话内模型切换触发压缩警告 | `merge_preflight_compression_warning()` |

### 2.5 网关 / Web / API Server（Gateway / web）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `gateway` | 网关子命令 | `gateway_command()` / `run_gateway()` |
| `gateway_windows` | Windows 网关服务后台（计划任务+启动文件夹） | `install()` / `is_installed()` |
| `gateway_enroll` | 自托管网关注册 relay connector | `cmd_gateway_enroll()` |
| `web_server` | Web UI 服务器（FastAPI 后端 + Vite/React 前端 + REST API），本包最大模块（`web_server.py` 19441 行）；**不含** `/v1/chat/completions`（见 §1.2） | `start_server()` / `auth_middleware()` / `app` |
| `webhook` | 动态 webhook 订阅管理 | `webhook_command()` |
| `web_git` | 桌面 coding 轨后端 git 操作 | `repo_status()` / `review_commit()` |
| `proxy` | 本地 OpenAI 兼容代理：把请求转发到 OAuth 鉴权的上游（网关节点用） | `UpstreamAdapter` |
| `container_boot` | 每 profile 网关 s6 服务协调 | `reconcile_profile_gateways()` / `ReconcileAction` |
| `pty_session` | dashboard 终端保活 PTY | `PtySessionRegistry` / `run_reaper()` |
| `win_pty_bridge` | Windows ConPTY 桥（dashboard chat tab） | `WinPtyBridge` / `PtyUnavailableError` |
| `pt_input_extras` | prompt_toolkit 输入解析增强 | `install_shift_enter_alias()` / `install_ignored_terminal_sequences()` |
| `voice` | TUI gateway 语音录制 + TTS API | `start_recording()` / `speak_text()` |

### 2.6 工具 / 工具集配置（Tools / toolset config）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `tools_config` | 统一工具配置：`hermes tools` / `hermes setup tools` 的落点，把各平台勾选的 toolset 写进 `platform_toolsets`，并读 `agent.disabled_toolsets` | `tools_command()` / `CONFIGURABLE_TOOLSETS` / `enabled_mcp_server_names()` |
| `toolset_validation` | `platform_toolsets` 配置段校验 | `validate_platform_toolsets()` |
| `skills_config` | 技能配置 | `get_disabled_skills()` / `skills_command()` |
| `skills_hub` | Hermes 技能中心 CLI | `skills_command()` / `do_install()` |
| `mcp_catalog` | 精选、Nous 审核过的 MCP 服务器目录 | `list_catalog()` / `CatalogEntry` |
| `mcp_config` | `hermes mcp` 子命令 | `mcp_command()` / `cmd_mcp_add()` |
| `mcp_picker` | 交互式 `hermes mcp picker` | `run_picker()` |
| `mcp_security` | 用户配置 MCP server 条目的安全校验 | `validate_mcp_server_entry()` / `is_mcp_server_entry_suspicious()` |
| `mcp_startup` | 后台 MCP 发现的 CLI/TUI 安全 helper | `start_background_mcp_discovery()` |
| `callbacks` | `terminal_tool` 交互式 prompt 回调 | `clarify_callback` / `approval_callback` / `prompt_for_secret` |
| `clipboard` | 剪贴板图片提取（mac/win/linux/wsl2） | `save_clipboard_image()` / `has_clipboard_image()` |
| `browser_connect` | 附加本地 Chromium CDP 端口 helper | `discover_local_cdp_url()` / `try_launch_chrome_debug()` |

### 2.7 能力模块（Capabilities：目标/项目/看板/旅程/策展/MOA/Bundles/Blueprint/会话）

> 这些模块的「能力行为语义」详见 `08-capability-integration.md`；本文只列模块定位与代表 API。
> 行为实战片段在 08（Goals/Snapshots/MOA/Projects/Bundles 含进程内实战子节）。

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `goals` | 持久会话目标（Ralph 循环） | `GoalManager` / `GoalState` / `parse_contract` |
| `projects_cmd` | `hermes project` CLI（一级多文件夹 Project 管理） | `projects_command()` |
| `projects_db` | 每 profile 一级 Project 存储 | `create_project()` / `connect_closing()` / `set_active()` |
| `kanban` | `hermes kanban` 子命令 | `kanban_command()` / `run_slash()` |
| `kanban_db` | SQLite 看板（多 profile/多 project） | `connect()` / `create_task()` / `Task` |
| `kanban_decompose` | 看板分解器（把 triage 任务拆成子任务图） | `decompose_task()` / `DecomposeOutcome` |
| `kanban_diagnostics` | 看板诊断（结构化告警信号） | `compute_task_diagnostics()` / `Diagnostic` |
| `kanban_specify` | 看板 triage 指定器（一句话展开成 spec） | `specify_task()` / `SpecifyOutcome` |
| `kanban_swarm` | 看板 Swarm v1 拓扑 helper | `create_swarm()` / `SwarmWorkerSpec` |
| `journey` | `hermes journey`（Hermes 学到的时间线） | `cmd_journey()` |
| `curator` | `hermes curator` 子命令 | `register_cli()` / `cli_main()` |
| `moa_cmd` | MOA 配置 CLI helper | `cmd_moa()` |
| `moa_config` | MoA 配置 + 斜杠命令 helper | `resolve_moa_preset()` / `set_active_moa_preset()` / `normalize_moa_config()` |
| `bundles` | `hermes bundles` 子命令 | `bundles_command()` / `register_cli()` |
| `blueprint_cmd` | `/blueprint` 共享命令逻辑（CLI/TUI/网关） | `handle_blueprint_command()` |
| `checkpoints` | `hermes checkpoints` CLI 子命令（会话消息级快照） | `register_cli()` / `cmd_list()` |
| `active_sessions` | 跨进程活动会话租约 | `ActiveSessionLease` |
| `session_listing` | CLI/gateway 会话列表 helper | `query_session_listing()` |
| `session_filters` | `hermes sessions prune/archive` 过滤 | `build_prune_filters()` / `describe_filters()` |
| `session_recap` | 会话回顾摘要 | `build_recap()` |
| `session_export` | 会话导出共享渲染器 | `render_sessions_export()` |
| `session_export_html` | 会话 HTML 导出生成器 | `generate_html_export()` |
| `session_export_md` | 会话 Markdown/QMD 导出 helper | `render_session_markdown()` |
| `prompt_size` | prompt 规模诊断（`hermes prompt-size`） | `compute_prompt_breakdown()` / `cmd_prompt_size()` |
| `partial_compress` | 边界感知部分压缩（"总结到此处"） | `split_history_for_partial_compress()` |
| `suggestions_cmd` | `/suggestions` 共享命令逻辑 | `handle_suggestions_command()` |
| `write_approval_commands` | `/memory` `/skills` 写审批子命令 | `handle_pending_subcommand()` |

### 2.8 安全 / 审计（Security / audit）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `security_audit` | 安装包按需供应链审计 | `run_audit()` / `Finding` / `Component` |
| `security_audit_startup` | 启动期安全态势审计（warn-on-load，不阻塞） | `log_startup_security_warnings()` |
| `security_advisories` | 安全公告检查 | `detect_compromised()` / `startup_banner()` |
| `mcp_security` | 用户配置 MCP server 安全校验（见 2.6） | `validate_mcp_server_entry()` |
| `runtime_provider` | CLI/gateway/cron 共享运行时 provider 解析 | `resolve_runtime_provider()` |
| `credential_lifecycle` | 跨所有 store 的统一 provider 凭证生命周期 | `save_provider_env_credential()` / `purge_env_credential_references()` |
| `input_sanitize` | 清洗终端/paste 泄漏到用户 prompt 的控制序列 | `sanitize_user_prompt_text()` |
| `urllib_security` | 携带凭证的 stdlib urllib 请求安全策略 | `open_credentialed_url()` |

### 2.9 安装 / 卸载 / 部署 / 迁移（Install / uninstall / migrate）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `setup` | 交互式安装向导 | `run_setup_wizard()` |
| `setup_whatsapp_cloud` | WhatsApp Cloud 适配向导 | `run_whatsapp_cloud_setup()` |
| `uninstall` | Hermes Agent 卸载器 | `run_uninstall()` |
| `gui_uninstall` | Desktop Chat GUI 卸载器 | `uninstall_gui()` |
| `doctor` | 诊断命令 | `run_doctor()` |
| `migrate` | `hermes migrate` 处理器 | `cmd_migrate()` |
| `codex_runtime_plugin_migration` | MCP/Codex 插件配置迁移 | `migrate()` / `MigrationReport` |
| `codex_runtime_switch` | `/codex-runtime` 共享逻辑 | `get_current_runtime()` / `set_runtime()` |
| `claw` | OpenClaw 迁移命令 | `claw_command()` |
| `inventory` | provider/model 清单上下文（dashboard 共享底座） | `load_picker_context()` / `ConfigContext` |
| `profile_describer` | 自动生成 profile `description` | `describe_profile()` |
| `profile_distribution` | 可分享、git 打包的 profile | `read_manifest()` / `DistributionManifest` |

### 2.10 运行 / 服务 / 调度（Runtime / service / cron / backup）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `service_manager` | 抽象服务管理接口 | `ServiceManager` |
| `cron` | `hermes cron` 子命令 | `cron_command()` / `cron_tick()` |
| `backup` | 备份与导入命令 | `create_quick_snapshot()` / `create_pre_update_backup()` / `restore_cron_jobs_if_emptied()` |
| `logs` | `hermes logs` 查看/过滤 | `tail_log()` / `list_logs()` |
| `status` | `hermes status`：逐项显示 Hermes 各组件状态（密钥在输出里脱敏） | `show_status()` / `redact_key()` / `check_mark()` |
| `debug` | `hermes debug` 工具 | `run_debug()` / `collect_debug_report()` |
| `dump` | dump 命令 | `run_dump()` |
| `diagnostics_upload` | `hermes debug share` 上传 Nous S3 | `share_to_nous()` |
| `tips` | 会话开始随机提示 | `get_random_tip()` |
| `banner` | 欢迎横幅 + 更新检查 | `build_welcome_banner()` |
| `hooks` | `hermes hooks` shell 脚本管理 | `hooks_command()` |
| `middleware` | 中间件契约 helper | `RequestMiddlewareResult` / `VALID_MIDDLEWARE` |
| `pets` | `hermes pets` 子命令 | `register_cli()` / `print_pet_gallery()` |
| `plugins` | Hermes 插件系统 | `PluginManager` / `PluginContext` |
| `plugins_cmd` | `hermes plugins` 子命令 | `plugins_command()` |
| `sqlite_util` | 小型 per-profile/board 存储的 SQLite 原语 | `write_txn()` / `add_column_if_missing()` |

### 2.11 消息平台桥（IM / messaging bridges）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `slack_cli` | `hermes slack` 子命令 | `slack_manifest_command()` |
| `telegram_managed_bot` | Telegram 托管机器人接入 | `auto_setup_telegram_bot()` |
| `pairing` | DM pairing（见 2.3） | `pairing_command()` |
| `webhook` | 动态 webhook（见 2.5） | `webhook_command()` |
| `cli_billing_mixin` | 交互式 CLI 计费/订阅处理器（god-file 分解） | `CLIBillingMixin` |

### 2.12 UI / TUI 渲染（UI / TUI rendering）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `curses_ui` | curses 共享 UI 组件 | `curses_checklist()` / `curses_single_select()` |
| `skin_engine` | CLI 皮肤/主题引擎 | `load_skin()` / `SkinConfig` |
| `colors` | 共享 ANSI 颜色工具 | `color()` / `Colors` |
| `cli_output` | CLI 输出 helper | `print_info()` / `prompt_yes_no()` |
| `voice` | 语音（见 2.5，TUI gateway 用） | `start_recording()` |
| `clipboard` | 剪贴板（见 2.6） | `save_clipboard_image()` |

### 2.13 Windows / 平台特定（Windows / platform-specific）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `_subprocess_compat` | Windows 子进程兼容 helper | `windows_detach_popen_kwargs()` |
| `gateway_windows` | Windows 网关服务（见 2.5） | `install()` |
| `stdio` | Windows 安全 stdio（见 2.2） | `configure_windows_stdio()` |
| `win_pty_bridge` | Windows ConPTY 桥（见 2.5） | `WinPtyBridge` |
| `psutil_android` | psutil Android 兼容临时安装 | `prepare_patched_psutil_sdist()` |
| `pty_bridge` | PTY 桥（依赖 `fcntl`，**仅 Linux 可 import**；Windows 导入即 `ModuleNotFoundError`） | `PtyBridge` |

---

## 3. 进程内可复用模块详解（含最小代码）

进程内桌面集成**最常用**的 `hermes_cli` 复用点（均为纯逻辑，无 TTY/网络副作用）：

### 3.1 配置读写 —— `hermes_cli.config`
```python
from hermes_cli.config import load_config, save_config
cfg = load_config()          # 读 HERMES_HOME/config.yaml
cfg["some_key"] = "v"
save_config(cfg)
```

### 3.2 工具集配置读取 —— `hermes_cli.tools_config`
```python
from hermes_cli.config import load_config
from hermes_cli.tools_config import CONFIGURABLE_TOOLSETS, enabled_mcp_server_names
CONFIGURABLE_TOOLSETS                     # 可在设置面勾选的 toolset 全集（list[tuple]）
enabled_mcp_server_names(load_config())   # config.yaml 里已启用的 MCP server 名
```

### 3.3 定时任务底层逻辑 —— `hermes_cli.cron`
> 注意：`cron_command()` 是 CLI 子命令入口；但其背后的 `cronjob` 工具集逻辑（与 `tools.cronjob_tools` 配合）
> 是进程内可调度的能力。桌面应用若要做「定时触发 Agent」，直接用 `AIAgent` + 自己的调度器，
> 复用 `cron` 模块里的纯函数（`cron_list` / `cron_tick` / `cron_runs`），不要调用 `cron_command()` 起子命令。

### 3.4 MOA 预设解析 —— `hermes_cli.moa_config`
```python
from hermes_cli.config import load_config
from hermes_cli.moa_config import resolve_moa_preset, set_active_moa_preset
spec = resolve_moa_preset(load_config().get("moa") or {}, "balanced")   # 返回该预设的 dict
cfg = set_active_moa_preset(load_config().get("moa") or {}, "balanced")  # 只改内存中的 active_preset，不落盘
```
> MoA 的进程内实战见 `08` §3（经 `run_conversation(moa_config=)` 驱动）。

### 3.5 备份 —— `hermes_cli.backup`
```python
from hermes_cli.backup import create_quick_snapshot, restore_cron_jobs_if_emptied
create_quick_snapshot(label="before-update")   # 落 HERMES_HOME 快照
```

### 3.6 Profile 管理 —— `hermes_cli.profiles`
```python
from hermes_cli.profiles import create_profile, list_profiles
create_profile("work")     # 多环境隔离（per-profile 配置/会话/能力）
```

### 3.7 能力状态内核模块（行为见 `08`）
- `goals` → `GoalManager`（持久会话目标）
- `projects_db` → `create_project` / `connect_closing` / `set_active`（一级多文件夹 Project）
- `bundles` → `bundles_command`（技能捆绑包 CLI 子命令）；扫描与删除的真实实现在 `agent.skill_bundles`（`scan_bundles` / `delete_bundle`），进程内要读捆绑包直接用它
- `moa_config` → MOA 预设（见 3.4）
- `security_audit` / `security_audit_startup` → 供应链审计（启动 warn，不阻塞）
- `backup` → 见 3.5

### 3.8 供应商/模型查询 —— `hermes_cli.providers` / `provider_catalog` / `models`
```python
from hermes_cli.providers import get_provider, is_aggregator, determine_api_mode
from hermes_cli.provider_catalog import provider_catalog
p = get_provider("openrouter")
```

### 3.9 会话导出 —— `session_export_*` / `session_recap` / `prompt_size`
纯渲染/诊断，进程内可调用生成「对话记录 HTML/Markdown」或诊断 prompt 规模。

---

## 4. 进程内复用注意（哪些模块要慎用）

`hermes_cli` 中多数「起服务 / 监听端口 / 起子进程 / TTY 交互 / 云账号 / IM 桥」类模块依赖完整 CLI 运行时
（TTY、凭据流、端口、后台服务）。进程内桌面应**只 import 你确认无副作用的纯函数子模块**（见 §3）；
涉及交互式输入/网络认证/起服务的模块**不要在 GUI 初始化时盲目 import**。

---

## 5. 全文检索索引（`hermes-llms-full.txt` 检索地图）

> **已上移**：完整版检索地图现为 `00-index.md` §1（本技能**最优先**的检索索引，HARD-GATE 写代码前先查）。
> 本文不再重复维护，避免漂移；需要检索时统一到 `00-index.md` §1。

## 6. 与本文档集其他篇目关系（避免交叉）

| 主题 | 归属文件 | 本文 role |
| --- | --- | --- |
| `AIAgent` 构造参数/回调/SSE 词汇 | `01-library-api.md` | 进程内驱动核心（本文不涉及） |
| 路径 A/B/C 与 5 条调用路线 / SSE 桥接 / 最小骨架 | `02-integration-core.md` | 路径 B 的模块级清单见本文 §3（02 §4 只留路线红线并指向本文） |
| 57 工具集逐条 | `03-capabilities-and-toolsets.md` | 工具集行为（本文不列） |
| 多框架接入（FastHTML/Tkinter/…） | `04-rendering-frameworks.md` | 渲染层（本文不列） |
| 安装/环境/HERMES_HOME | `05-install-and-env.md` | 环境（本文 §2.2/§2.9 仅标模块） |
| 打包/hidden-import | `06-packaging.md` | 打包（本文不列） |
| 红线/门禁/工作流 | `07-quality-gates.md` | 红线 R1/R3 的「概念解释」在本文 §1（07 是权威红线列表） |
| 能力行为语义（Goals/MOA/…） | `08-capability-integration.md` | 能力语义（本文 §2.7 仅标模块定位，行为去 08） |
| 集成自测/端到端 | `09-integration-e2e.md` | 测试（本文不列） |

> 任何对 `hermes_cli` 模块的「能力行为」描述若与 `08` 重叠，以 `08` 为准；本文只负责「模块存在性 / 用途 /
> 代表 API」这一层，确保全 149 个顶层条目不遗漏；8 个跨主题模块只在主组列全信息，另一组留指针。
