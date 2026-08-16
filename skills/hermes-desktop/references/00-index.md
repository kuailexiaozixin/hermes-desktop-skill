# 00 · hermes-desktop 参考文档索引（检索地图 + 全局导航 + 事实基线）

> 本文件是 **hermes-desktop** 技能的**唯一权威索引**，提供 `hermes-llms-full.txt` 检索地图、全局导航与事实基线。所有结论均经 `hermes-agent==0.19.0`
> 的已安装包**逐条源码内省**核实（见 §4 事实基线），并对照技能内置参考实现
> `examples/01-hermes-desktop` 的实战写法交叉验证。任何与本文不符的描述，以本文 + 源码为准。
>
> **最优先**：本文 §1 即 `hermes-llms-full.txt` 检索地图（完整版，自 `10-hermes-cli.md` §5 移入）——写任何代码前先在此检索确认语义。

---

## 1. `hermes-llms-full.txt` 检索地图（完整版，最优先）

> `hermes-llms-full.txt` 是 Hermes 官方文档全文（约 68,000 行）的内置副本，本技能 HARD-GATE（SKILL.md §1 门1）
> 要求写代码前先在此检索对应章节确认语义。**文档与源码冲突时一律以源码为准**（本文档集即源码派生版）。

### 1.1 按任务 → 检索关键词

| 你想做的事 | 在 llms-full.txt 检索的标题 / 关键词 | 本路线相关度 |
| --- | --- | --- |
| 确认 `AIAgent` 概念 / 进程内 Library 模式 | `Using Hermes as a Python Library` / `run_conversation()` | ✅ 核心（详见 `01`） |
| 模型 / Provider / key 配置 | `Configuration` › `Configure a model` / `base_url` / `api_key` | ✅ |
| Toolset 启用 / 自定义注册 | `Tools & Toolsets` / `ctx.register_tool` | ✅ 概念看这里，进程内注册落地见 `01`/`03` |
| 回调触发时机 | `## Callback Surfaces` / `reasoning_callback` | ✅ 时机看这里，实证签名看 `01` |
| 多轮会话 / 持久化 | `Sessions` › `Session Storage` / `session_id` | ✅ |
| MCP toolset 接入 | `MCP Servers` | ⚠️ 可用，进程内接法以源码为准（见 `06` §6） |
| 插件 Plugins | `Plugins` | ⚠️ 可用（`plugins`/`skills_hub`） |
| 危险命令审批 | `Security` › `Dangerous Command Approval` | ✅ 思路借鉴，进程内需自建（见 `07` §4 / `02` §7） |
| HERMES_HOME / 配置落点 | `Configuration` › `Managing Configuration` | ✅ |
| CLI / TUI 用法 | `CLI Interface` / `TUI` | ⚠️ 进程内调 CLI 逻辑见 `10-hermes-cli.md` §3 |
| **API Server `/v1`** | `API Server` | ⚠️ 进程内直跑路线不适用（选 API Server 路线则按需，见 `15-api-server.md`） |
| gateway / sidecar | `Gateway` / `Container Architecture` | ❌ 进程内直跑路线不适用（选网关路线则按需，见 `16-gateway-package.md`） |
| Managed Mode / Docker 部署 | `Managed Mode` / `Docker` | ❌ 进程内直跑路线不适用（属跨进程部署，按需求选对应路线，见 `15-api-server.md`/`16-gateway-package.md`） |
| 官方 Desktop（Electron） | `apps/desktop`（仓库内，不在文档） | ❌ 路线定位不同（差异见 `04-rendering-frameworks.md` §16） |
| 消息平台（Telegram/Slack…） | `Integrations` / 各平台 adapter | ❌ 进程内直跑路线需改选网关路线才激活（见 `02` §5；选网关路线则按需，见 `16-gateway-package.md`） |

### 1.2 检索技巧

- 文档随版本重排，**不要依赖行号**，用标题/关键词检索。
- 版本漂移重灾区：`Callback Surfaces`、`Tools & Toolsets` 的注册 API、`Configuration` 的 schema。
  每次大版本（如 0.18→0.19）后跑 `scripts/track_upstream.py --update-docs` 重拉并比对 md5。
- 文档说「只能 clone」→ 与实测（pip 可装 wheel）冲突时，**以实测为准**，并在 `docs/troubleshooting.md` 记一笔。

### 1.3 本路线「不适用」章节速记

遇到以下关键词，提醒自己：**这是进程内直跑路线下的不适用项**；若确定选网关 / API Server / `/v1` 路线（见 `15-api-server.md`/`16-gateway-package.md`）则按需启用——选进程内直跑路线时请停下核对：
`API_SERVER_KEY` · `CORS` · `127.0.0.1:8642` · `hermes gateway` · `/v1/chat/completions` ·
`Dockerfile` · `Managed Mode` · 官方 `apps/desktop` · Telegram/Slack 平台 adapter。

---

## 2. 本技能定位（一句话）

在 **FastHTML / Tkinter / pywebview / PyQt / textual（Python 原生）以及 Electron / React·Vue / Koa（JS 前端桥接）、
.NET / Java / C / C++ / Rust（其他语言宿主）** 等各类应用框架中，
**进程内直跑 Hermes 的 Python Library**（`pip install hermes-agent` → `from run_agent import AIAgent`）；
调用 Python Library 有 5 条**平等可选**路线——进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`——**无先后顺序**，按需选择其一。本文档与示例常以进程内直跑为叙述基线，不代表该路线优先或推荐；跨进程路线的选型与落地见 references/02-integration-core.md §2 路径 D。
各类框架的接入方式详见 `04-rendering-frameworks.md`（多框架接入与整合）。

---

## 3. 阅读顺序（建议）

| 顺序 | 文件 | 解决什么问题 | 何时读 |
| --- | --- | --- | --- |
| 0 | **00-index**（本文件） | 全局导航、事实基线、单真相源映射、llms-full 检索地图 | 任何时候 |
| 1 | **01-library-api** | Library 怎么装、怎么导入、`AIAgent` 怎么构造（**全量 70 个构造参数逐项**）、回调与流式、会话/环境、**结构化输出与多模态输入（§3.4bis：`request_overrides` 透传 / `ctx.llm.complete_structured` 强类型 / OpenAI 风格多模态消息）** | 写集成代码前必读 |
| 2 | **02-integration-core** | 业务系统与 Agent 双向整合（界面接入 + 业务赋能，一个整体）：进程内三条路径/SSE/能力→模块地图/CLI 复用/最小骨架/治理，加上非侵入扩展面（Skill/MCP/Plugin/Memory）与三种加业务工具方式对比；**§12 含 `ctx.llm` 宿主推理（`PluginLlm.complete/complete_structured` 强类型结构化 + 业务上下文注入，等价依赖注入+类型化输出）** | 设计桌面壳/Web UI、给 Agent 接业务工具/记忆/流程、要强类型结构化输出时 |
| 3 | **03-capabilities-and-toolsets** | 57 个工具集**逐条**文档 + 减法原则 + 审批闭环 | 要开/关某项能力、排查工具缺失时 |
| 4 | **04-rendering-frameworks** | Python 原生 + JS 前端桥接 + 其他语言宿主（.NET/Java/C/C++/Rust）的接入与整合 | 选渲染层/宿主时 |
| 5 | **05-install-and-env** | 安装、venv、`HERMES_HOME` 唯一真相、配置路径 | 部署/切换运行环境时 |
| 6 | **06-packaging** | PyInstaller 打包 hidden-import、冻结三坑、版本互斥 venv，以及**一键启动脚本**（bat/venv/四步验证） | 出 EXE / 交付一键启动入口时 |
| 7 | **07-quality-gates** | 反模式红线、门禁脚本、运行数据保护、自检、工作流 | 提交/发版前 |
| 8 | **08-capability-integration** | 能力层（工具集之外）逐条行为语义：Goals/Snapshots/MOA/Projects/Bundles/Security Audit/Blueprints/Batch/Journey/Backup/Profiles/Curator/Routing/Kanban/IM 桥，均经 0.19.0 源码核实；**Goals/Snapshots/MOA/Projects/Bundles 含进程内实战子节** | 接能力层时 |
| 9 | **09-integration-e2e** | 集成自测与端到端验证（跑通一个集成）、Hermes 作为 Agent 的测试特殊性断言；**§8 Agent 输出评估（LLM Judge 三段式，依托 `ctx.llm.complete_structured`）/ §9 离线确定性测试（mock 回放无网验证）** | 做集成自测 / 端到端验证 / 输出质量评估时 |
| 10 | **10-hermes-cli** | **`hermes_cli` 完整参考（顶层 147 模块 / 含嵌套共 205）**：分组清单 + 逐模块用途与代表 API + 可复用模块详解（llms-full 检索地图已上移至本文 §1） | 要 import 某个 `hermes_cli` 子模块 / 查 CLI 能力时 |
| 11 | **11-library-support** | **`batch_runner` + Hermes 自有支撑单文件模块**（`hermes_constants`/`hermes_state`/`hermes_logging`/`hermes_time`/`hermes_bootstrap`/`model_tools`/`toolsets`/`toolset_distributions`/`utils`/`trajectory_compressor`）：逐模块公开 API | 查 `HERMES_HOME`/会话落盘/原子写/自定义工具集/批量跑 Agent 时 |
| 12 | **12-tools-modules** | **`tools` 包全量模块枚举（113 个嵌套子模块）**：逐模块用途 + 代表 API | 查某个 `tools.*` 工具实现模块是否存在/能否进程内用时 |
| 13 | **13-agent-modules** | **`agent` 包参考（155 模块全量枚举 + 六项深度主题）**：§1 逐模块用途 + 内核分类 + 代表 API；§2 深度主题（2.1 上下文压缩 / 2.2 记忆 / 2.3 用量遥测 / 2.4 模型路由 / 2.5 一次性调用 / 2.6 安全护栏）含类·方法·集成要点 | 查 `agent` 运行时内核构成 / 排障定位 / 接入某一项 agent 能力时 |
| 14 | **14-library-infra** | **剩余 Hermes 自有基础设施模块**（`gateway`/`cli`/`cron`/`plugins`/`providers`/`acp_adapter`/`tui_gateway`/`mcp_serve`）：用途 + Library 全貌收口 | 确认 Library 还有哪些进程外设施（网关 / CLI / API Server 等）及其用途时 |
| 15 | **15-api-server** | **API Server 路线完整手册**（判据/三种实现路径/配置/端点全清单/认证安全/接入示例/进程内自建/检查清单） | 要开 API Server / 接 OpenAI 兼容前端 / 走 `/v1` 时 |
| 16 | **16-gateway-package** | **顶层 `gateway` 包全量模块枚举（77 个 `.py`）**：逐模块用途 + 代表 API + 0.19.0 实际承载的平台清单 | 查网关运行时构成 / 某个 `gateway.*` 模块 / 网关承载哪些平台时 |
| 17 | **api-reference/**（自动生成） | **库级 API 参考**（按模块拆分，ast 静态解析自 0.19.0 源码、未 import）：`01-run-agent`（AIAgent 240 方法）/`02-toolsets`/`03-gateway-session`/`04-mcp-serve`，含类、方法、参数（类型注解+默认值）、返回类型、异常 | 需要精确的类/方法/参数/返回/异常签名时（由 `scripts/gen_api_reference.py` 一键重新生成） |

> 不要跳读 01 直接看 03：工具集是 `AIAgent` 的 `enabled_toolsets` / `disabled_toolsets`
> 参数的输入，构造语义见 01 §3。

---

## 4. 事实基线（唯一真相源，0.19.0 内省核实）

```
包名 / 版本 : hermes-agent == 0.19.0
导入语句     : from run_agent import AIAgent          # 顶层模块，非 hermes.* 子包
CLI 包      : hermes_cli  ( __version__ = "0.19.0" )  # 含 147 个顶层模块（含嵌套共 205，见 10）
工具集注册表 : from toolsets import TOOLSETS          # 顶层模块 toolsets，非 hermes.toolsets
工具集总数   : 57  =  33 个 capability  +  24 个 hermes-* 集成
工具集结构   : 每项 = { "description": str, "tools": list[str], "includes": list[str] }
环境 API     : hermes_constants.get_hermes_home() / set_hermes_home_override(path) / ...
```

**易错点（务必注意）**：
- 顶层模块是 `toolsets`（`from toolsets import TOOLSETS`），不是 `hermes.toolsets`——0.19.0 不存在 `hermes` 包。
- 正确包名是 `hermes-agent`（连字符），导入符号是 `run_agent.AIAgent`；`import hermes_agent` 会报 `No module named`。
- `AIAgent.__init__` 是 `Forwarder`，真实构造逻辑在 `agent.agent_init.init_agent`（`__init__` 的 docstring 已指明）。
- `hermes_cli` 是 Library 自带的统一 CLI 包（与 `run_agent`/`tools`/`agent`/`batch_runner` 并列，均为顶层包），
  但**不是进程内驱动 Agent 的核心入口**——进程内驱动对话的是 `AIAgent`；`hermes_cli` 在桌面集成里的正确用法是
  「辅助逻辑复用」（见 `10-hermes-cli.md` §3），正如 `02` §3 所讲。它和 `AIAgent` 是并列的 Library 组成部分，不是从属关系。

---

## 5. 单真相源映射（避免重复与漂移）

| 事实 | 唯一归属文件 | 备注 |
| --- | --- | --- |
| 装包名 / 版本 / 导入路径 | `01-library-api.md` §1 | 改版本先改这里 |
| `AIAgent` 构造参数与回调签名 | `01-library-api.md` §3 | 以源码 `__init__` 为准 |
| SSE 事件词汇（delta/reasoning/action/…） | `01-library-api.md` §4 + `02-integration-core.md` §3 | 旗舰示例 `agent_runtime.py` 复核 |
| 57 工具集清单与逐项说明 | `03-capabilities-and-toolsets.md` | 单一全量表，禁止别处再列 |
| 减法原则（enabled=None=全量 / disabled 做减法） | `01-library-api.md` §3 + `03-*` §1 | 进程内直跑常态 `disabled=["terminal"]` |
| `HERMES_HOME` 与环境变量 | `05-install-and-env.md` | `hermes_constants` 是唯一 API |
| PyInstaller hidden-import 清单 | `06-packaging.md` §2 | 随依赖增删更新 |
| 反模式红线 | `07-quality-gates.md` §1 | 任何新增能力先过此章 |
| 能力行为语义（Goals/MOA/…） | `08-capability-integration.md` | 单一行为基线，禁止别处再写能力语义 |
| `hermes_cli` 模块清单（用途与代表 API） | `10-hermes-cli.md` | 全 147 个顶层模块不遗漏、不重复、不交叉 |
| llms-full 检索地图 | `00-index.md` §1（本文） | 完整版自 `10-hermes-cli.md` §5 移入，唯一权威检索索引 |
| `batch_runner` + 支撑模块 API | `11-library-support.md` | `HERMES_HOME`/会话落盘/自定义工具集/原子写单一参考 |
| `tools` 包全量子模块 | `12-tools-modules.md` | 113 个嵌套子模块不遗漏、不重复、不交叉 |
| `agent` 包全量子模块 | `13-agent-modules.md` | 155 个嵌套子模块不遗漏、不重复、不交叉 |
| 基础设施模块（网关/CLI/cron/…） | `14-library-infra.md` | 进程外设施单一说明，避免误 import |
| API Server 路线落地 | `15-api-server.md` | API Server 形态单一真相源（配置/端点/接入/进程内自建），避免与 02/04/10 重复 |
| `gateway` 包全量子模块 | `16-gateway-package.md` | 77 个嵌套子模块不遗漏、不重复、不交叉 |
| 非侵入扩展面（skill/mcp/plugin/memory） | `02-integration-core.md` §9–§14 | 业务对接 Hermes 的唯一扩展面参考（已并入双向整合总章）；改核为最后手段 |

---

## 6. 交叉引用约定

- 本目录文件以 `NN-` 两位编号开头；跨文件引用写作 `` `03-capabilities-and-toolsets.md` §2 ``
  （反引号包裹文件名 + `§节号`）。
- 锚点用 GitHub 风格：`## 3. 工具集系统` → 链接 `#3-工具集系统`。
- 代码符号用反引号：`AIAgent`、`TOOLSETS`、`get_hermes_home()`。
- 路线红线统一用 ⛔ 标记（见 `07-quality-gates.md`）。

---

## 7. 与内置参考实现的关系

`examples/01-hermes-desktop` 是**自包含**的进程内 `AIAgent` + FastHTML + pywebview 旗舰示例，
其 `agent_runtime.py` 的构造与 SSE 分发已作为本文档「实战写法」的核验样本（见 01 §3、§4）。
`examples/02-hermes-pywebview-multiagent` 是多智能体 pywebview 壳示例。
`examples/03-nesquena-hermes-webui` 是 Hermes WebUI 本地适配（源自开源 nesquena/hermes-webui）：三栏浏览器/手机 Web 界面（CLI 1:1 对等），经 `api/agent_runtime.py` 以 `from run_agent import AIAgent` 驱动核心，Windows 原生 `start-webui.bat` / `start.ps1` 启动（端口 8787）。
三者代码本身可读，本文档只抽取**与技能通用方法相关**的结论，不绑定任何具体业务领域。
