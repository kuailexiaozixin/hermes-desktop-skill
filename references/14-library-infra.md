# 14 · 剩余 Hermes 自有基础设施模块参考（网关 / CLI / cron / 插件 / 供应商 / 传输适配，0.19.0）

> 本文件覆盖 Library 中**其余 Hermes 自有模块**——它们多数属于「网关 / Web Server / CLI 交互 / 云端账号 / 消息平台桥 / 调度」这类**进程外设施**，
> 在「桌面 GUI 进程内直跑 `AIAgent`」路线下**一般不应 import 或调用主函数**。把它们单列一篇，是为了**诚实交代 Library 还有哪些东西、以及为什么不用**，
> 避免你以为「Library 只剩前面那些」或误把网关模块 import 进桌面应用。
>
> 全部条目经 `hermes-agent==0.19.0` 顶层模块名单（`top_level.txt`）核实；公开 API 经 `importlib` 内省提取（部分模块因依赖重、import 即拉起 TTY/服务，未强制 import，其 API 以 `top_level.txt` + 已知结构描述）。
> 与 `10-hermes-cli.md` 的边界：`hermes_cli.*` 已在 `10` 全量列举（含 `gateway`/`web_server`/`cron`/`plugins` 等作为 `hermes_cli` 子模块）；
> 本文列的 `gateway`/`cli`/`cron`/`plugins`/`providers`/`acp_adapter`/`tui_gateway`/`mcp_serve` 是**顶层同名模块**（非 `hermes_cli` 子模块），二者是两回事，请勿混淆。

---

## 0. 这些模块为何多属「进程外设施」

进程内直跑路线的核心约束（见 `07` §1、`10` §1）：若选用**进程内直跑**路线，一般**不起网关、不 spawn 子进程、不开 API Server**（跨进程路线的设施按对应手册按需启用，选型与落地见 references/02-integration-core.md §2 路径 D）。

下表模块几乎全部是「为网关/CLI/TTY/云端/IM 平台服务」的。它们的**存在**是 Library 的一部分，但它们的**主函数**是给另一条路线（网关/子进程）用的。
桌面应用若 import 并调用其主函数，会引入端口占用、TTY 依赖、后台服务、跨进程状态等——与「单 EXE 双击即跑」冲突。

> **复用建议**：只 import 你确认**无副作用的纯函数子模块**（如 `providers` 的 `register_provider`/`list_providers`，属纯注册表）；
> 涉及「起服务 / 监听端口 / TTY 交互 / 网络认证」的主函数**不要在 GUI 初始化时盲目 import**。

---

## 1. 顶层基础设施模块清单（按用途分组）

| 模块（顶层） | 用途（0.19.0） | 代表 API | 说明 |
| --- | --- | --- | --- |
| `gateway` | Hermes 网关——多平台消息集成常驻服务（顶层包，77 个 `.py`） | （import 即拉起网关依赖；主函数 `gateway.main` 起服务） | 起 HTTP 服务、监听端口、做平台接入。**本路线不用**（详见 `10` §2.5 同名 `hermes_cli.gateway`；**包内 77 个模块已全量枚举见 `16-gateway-package.md`**） |
| `cli` | Hermes Agent CLI——交互式终端界面 | `ChatConsole` / `HermesCLI` / `main` | TTY 交互界面，给终端用；GUI 桌面自己画界面，不套用 |
| `cron` | Cron 定时任务调度系统 | （import 即拉起调度依赖） | `hermes cron` 子命令；**底层 cronjob 工具逻辑**在 `tools.cronjob_tools`（进程内可用，见 `12`），本模块主函数不用 |
| `plugins` | Hermes 插件系统 | （插件发现/加载体系） | 插件**机制**可了解（`10` §2.10 也列 `hermes_cli.plugins`）；进程内若用插件，经 `AIAgent` 的工具集/技能体系接入，不要直接 import 此模块起插件加载器 |
| `providers` | Provider（LLM 厂商）模块注册表 | `register_provider()` / `list_providers()` / `get_provider_profile()` | 纯函数注册表，**进程内可安全 import**；模型/厂商查询也见 `10` §2.4（`hermes_cli.providers`） |
| `acp_adapter` | ACP（Agent Communication Protocol）适配器 | `entry:main`（`hermes-acp` 命令入口） | 协议适配/桥接，给网关/外部协议用；进程内直跑时不需要 |
| `tui_gateway` | TUI 网关（终端图形界面网关） | （TUI 渲染 + 网关） | 终端图形 + 网关；GUI 桌面不用 |
| `mcp_serve` | Hermes MCP Server——把消息对话暴露为 MCP 工具 | `create_mcp_server()` / `run_mcp_server()` / `EventBridge` / `QueueEvent` | 起一个 MCP 服务端对外暴露对话；进程内若要「调用 MCP 工具」用 `tools.mcp_tool`（见 `12`），不是起这个 server |

> 注：`top_level.txt` 顶层模块共 23 个（见 `00-index.md` §3 事实基线思路），其中 `run_agent`/`tools`/`agent`/`hermes_cli`/`batch_runner` 及 `11` 覆盖的支撑模块已在 `01`/`10`/`12`/`13`/`11` 详述；
> 本文覆盖剩余 8 个顶层基础设施模块。其余第三方依赖（PIL/fastapi/pydantic 等）不计为 Hermes 自有。

---

## 2. 各模块定位详解（为什么不用 / 什么情况下可用）

### 2.1 `gateway` —— 多平台消息集成常驻服务

- **是什么**：Hermes 提供的常驻后台服务进程，内部起 HTTP 服务（典型监听 `127.0.0.1:8642`），对外暴露 OpenAI 兼容的 `/v1/chat/completions`，
  并把消息平台的消息「喂」给 Agent。**0.19.0 网关平台适配器为「双轨」**：内置核心（`gateway/platforms/*`：QQ/Signal/Webhook/微信/WhatsApp Cloud/元宝/BlueBubbles/MSGraph/API Server）+ 插件平台（`plugins/platforms/*`：Telegram/Slack/Discord/飞书/企微/钉钉/Matrix/SMS/Email/Teams 等 20 个，`kind: platform` 无条件自动加载，registry 优先）。完整平台清单见 `16-gateway-package.md` §2。
- **为什么进程内不用**：起服务、监听端口、做多平台接入——本路线用 `AIAgent` 进程内直跑 + 自建前端桥接，不需要。
- **误用后果**：引入端口占用、常驻进程、跨进程状态同步，与「单 EXE 双击即跑」互斥。
- **如需接消息平台**：应用自己收消息 → `run_conversation`（见 `02` §5），而非起网关。

### 2.2 `cli` —— 交互式终端界面

- **是什么**：`HermesCLI` / `ChatConsole`，给终端用户用的交互式聊天界面（含表格对齐、markdown 重排、用量估算等辅助函数）。
- **为什么不用**：GUI 桌面自己画窗口和渲染层；`cli` 的 TTY 渲染在桌面应用里无意义。
- **可借鉴**：`cli` 里 `estimate_usage_cost` / `realign_markdown_tables` 等纯函数逻辑若需复用，可参考其实现自行移植（不要直接 import TTY 类）。

### 2.3 `cron` —— 定时任务调度

- **是什么**：`hermes cron` 子命令的调度系统。
- **底层可用部分**：真正干活的 `cronjob` 工具逻辑在 `tools.cronjob_tools`（`12` 已列，进程内可用）——它让 Agent「定时触发任务」。
- **本模块主函数不用**：桌面应用若要做「定时触发 Agent」，直接用 `AIAgent` + 自己的调度器（如 `threading.Timer` / `schedule` 库），复用 `cronjob_tools` 做配置解析，不要调用 `cron` 起子命令。

### 2.4 `plugins` —— 插件系统

- **是什么**：Hermes 插件发现/加载体系。
- **进程内怎么用**：插件**机制**可了解；但进程内启用某项能力，优先走 `AIAgent` 的**工具集 / 技能**体系（见 `03` / `08`），不要直接 import 此模块起「插件加载器」。
- 插件生态的 CLI 侧也见 `10` §2.10（`hermes_cli.plugins` / `plugins_cmd`）。

### 2.5 `providers` —— LLM 厂商注册表

- **是什么**：Provider 模块注册表（集中登记各 LLM 厂商的接入模块）。
- **进程内可用**：`register_provider()` / `list_providers()` / `get_provider_profile()` 是纯函数，**进程内可安全 import**。
- 更常用的厂商/模型查询入口在 `10` §2.4（`hermes_cli.providers` / `provider_catalog` / `models`）；本文 `providers` 是底层注册表。

### 2.6 `acp_adapter` —— ACP 协议适配器

- **是什么**：`hermes-acp` 命令入口（`entry:main`），实现 Agent Communication Protocol 适配，用于网关/外部协议桥接。
- **为什么不用**：进程内直跑时不走 ACP 桥；你的前端直接调 `AIAgent`，不需要协议适配层。

### 2.7 `tui_gateway` —— TUI 网关

- **是什么**：终端图形界面（TUI）+ 网关组合。
- **为什么不用**：GUI 桌面不用 TUI，也不起网关。

### 2.8 `mcp_serve` —— 把对话暴露为 MCP 工具

- **是什么**：起一个 MCP Server（`create_mcp_server` / `run_mcp_server`），把 Hermes 的消息对话作为 MCP 工具对外暴露（供其他 MCP 客户端调用）。
- **进程内不用**：本路线是「桌面应用内部用 `AIAgent`」，不是「把对话当 MCP 服务供别人调」。
- **若要在进程内调用外部 MCP 工具**：用 `tools.mcp_tool`（`12` 已列 `discover_mcp_tools` / `register_mcp_servers` 等），而非起这个 server。

---

## 3. 本路线「Library 全貌」收口（诚实覆盖结论）

经 `top_level.txt`（23 个顶层模块）+ 包内枚举，Library 全家福如下，已**全部覆盖**于本技能 references：

| 类别 | 顶层模块 | 覆盖文件 |
| --- | --- | --- |
| 进程内驱动核心 | `run_agent` | `01-library-api.md` |
| 工具实现包 | `tools`（113 嵌套子模块） | `12-tools-modules.md` |
| 运行时内核 | `agent`（155 嵌套子模块） | `13-agent-modules.md` |
| 统一 CLI 包 | `hermes_cli`（147 顶层 / 205 含嵌套） | `10-hermes-cli.md` |
| 批量运行器 | `batch_runner` | `11-library-support.md` §1 |
| 支撑单文件模块 | `hermes_constants` / `hermes_state` / `hermes_logging` / `hermes_time` / `hermes_bootstrap` / `model_tools` / `toolsets` / `toolset_distributions` / `utils` / `trajectory_compressor` | `11-library-support.md` §2–§11 |
| 网关运行时顶层包 | `gateway`（77 个 `.py`） | **`16-gateway-package.md`** |
| 进程外基础设施 | `cli` / `cron` / `plugins` / `providers` / `acp_adapter` / `tui_gateway` / `mcp_serve` | **本文件 `14`** |
| 第三方依赖 | PIL / fastapi / pydantic / …（不计为 Hermes 自有） | 不收录 |

> 至此，Library 的 Hermes 自有部分**无一遗漏**：`batch_runner` / `tools` / `agent` 已全量逐模块列举（`11`/`12`/`13`），
> 其余自有模块（支撑 + 基础设施）也已补齐（`11`/`14`）。进程内直跑时真正驱动 Agent 的是 `run_agent.AIAgent`，
> 其余模块按「进程内直跑」取舍：网关/CLI/调度/协议桥等进程外设施，进程内直跑时一般不起、不 spawn（改选跨进程路线则按需启用，选型见 references/02-integration-core.md §2 路径 D）。

---

## 4. 与本文档集其他篇目关系（避免交叉）

| 主题 | 归属文件 | 本文 role |
| --- | --- | --- |
| 进程内驱动核心 | `01-library-api.md` | 对外接口（本文不涉及） |
| `hermes_cli` 模块清单（含其 `gateway`/`cron`/`plugins` 子模块） | `10-hermes-cli.md` | 不同包（CLI 子模块 vs 顶层同名模块） |
| `tools` / `agent` 全量枚举 | `12` / `13` | 工具/内核实现（本文不列） |
| 支撑模块 | `11-library-support.md` | 进程内可复用支撑（本文仅列进程外设施） |
| 能力行为（Goals/MOA/…） | `08-capability-integration.md` | 能力语义（本文不列） |
| 红线/门禁 | `07-quality-gates.md` | 权威红线（本文仅引用） |

> 本文只负责「剩余基础设施模块的存在性 / 用途 / 为什么不用」这一层，
> 能力行为、工具集、内核构成均指向对应篇目，不重复。

---

## 5. 全文检索索引（桌面集成视角）

| 你想确认的事 | 看本文哪个小节 |
| --- | --- |
| Library 还有哪些东西、为什么不用网关 | §0 / §1 / §3 |
| 网关是什么、为什么进程内不起 | §2.1 |
| 定时任务底层逻辑在哪（可用） | §2.3（→ `12` `tools.cronjob_tools`） |
| 插件机制怎么了解 | §2.4 |
| LLM 厂商注册表（可 import） | §2.5 |
| MCP：调用外部工具 vs 起 server 的区别 | §2.8（调用用 `12` `tools.mcp_tool`） |
| Library 全貌收口 / 覆盖结论 | §3 |
| `gateway` 包内有哪些模块 / 网关承载哪些平台 | `16-gateway-package.md` |
