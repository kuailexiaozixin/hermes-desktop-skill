---
name: hermes-desktop
description: >-
  在桌面 / Web GUI 应用、业务系统或非 Python 语言宿主中「对接与集成」Hermes AI Agent Python 库的技能。
  定位：**对接集成引擎**——复制 `examples/` 底座 → 快速把 `AIAgent` 接进你的应用 → 门禁收尾，而非从零开发 Agent 框架。
  触发：给应用的 GUI 加一个内嵌 Hermes 智能体、或把 Hermes 接进业务系统时使用；调用 Python Library 有 5 条平等可选路线，按需选一。
  触发词：hermes、hermes-agent、AIAgent、run_agent、给应用加 AI、内嵌 Agent、桌面 AI 对话、业务系统对接智能体、
  GUI 集成 Agent、进程内 agent、在应用里对接 AI、AI 对话面板、工具调用可视化。
  反触发（一般不用）：不涉及对接/集成 hermes 内核的纯脚本调用、仅用 hermes CLI 无需集成、Hermes 官方服务端部署运维。
version: "1.7.30"
author: agent
agent_created: true
platform: multi
when_to_use: >-
  用户要**在自己的桌面 / Web GUI 应用**（FastHTML+pywebview、Tkinter、PyQt/textual、Electron/React/Vue/Koa 等），
  或**其他语言宿主**（.NET/Java/C/C++/Rust 经嵌入 Python 运行时或本地桥接）里嵌一个 Hermes 智能体时触发。
  调用 Python Library 有 5 条**平等可选**的技术路线——进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`——**无先后顺序，按需选择其一**；文档与示例为叙述方便常以进程内直跑作示例，不代表该路线优先或推荐。
  各路线完整落地见对应 reference；路线选型与跨进程路线落地见 references/02-integration-core.md §2 路径 D。
---

# hermes-desktop

> **定位**：本技能是「**对接集成引擎**」——把 Hermes Agent 内核（`AIAgent` 进程内）接进你的桌面 GUI 应用，
> 而非从零做完整应用的开发流程。**核心价值在「对接与集成」**：复制 `examples/` 底座 → 快速进集成 → 一键门禁收尾。
> 因此本技能**前序流程极简、集成流程为主、后序流程复用现成门禁**，不在需求/架构/交付上耗费过多时间。
>
>   **技术栈锁死**：Hermes Python Library（`AIAgent` 进程内）+ 渲染层/宿主（FastHTML/pywebview/Tkinter/PyQt/textual 进程内；**或** Electron/React/Vue/Koa 经 Python 后端 + 本地桥接；**或** .NET/Java/C/C++/Rust 经嵌入 Python 运行时（pythonnet/JPype/libpython/PyO3）或本地桥接）+ PyInstaller。
> **5 条路线平等可选**：调用 Python Library 有 5 条**平等可选**的技术路线——**进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`**——**无先后顺序**，按需选择其一即可。本文档与示例为叙述方便常以进程内直跑作示例，不代表该路线优先或推荐。选路关系到进程拓扑与交付形态（单进程 EXE / sidecar / 独立服务），按需求权衡，无默认；跨进程路线的选型与落地见 references/02-integration-core.md §2 路径 D。
>   - 进程内直跑：在你的 EXE 同一进程内直跑 `AIAgent`，单进程单文件 EXE，无端口/CORS/健康探测；Node 不跑内核（仅作 UI 壳/桥接层，见 `04` §7–§9）；非 Python 宿主通过嵌入 Python 运行时或本地桥接接入。
>   - 跨进程路线（相对进程内直跑）：由对应服务承担端口/鉴权/多客户端，新增「跨进程状态同步 + HTTP 桥接」代价；选型与落地见 references/02-integration-core.md §2 路径 D。
> **一种交付物**：内嵌 Hermes 内核的**单文件桌面 EXE**（跨进程路线亦可打包为带 sidecar 或服务依赖的交付物）。
>
> **本技能边界**：覆盖 **进程内 Library + 桌面 GUI** 与 gateway / API Server / 纯 CLI / 纯 Web 等形态，5 条路线一律按需选用，无主从。

> **能做什么**：
> - 给应用加 AI 对话面板；`AIAgent` 回调做流式输出 / 工具调用可视化 / 思考过程展示；进程内调 Hermes 内置 CLI
> - 把业务工具注册成 toolset 给 Agent 调用；设计 GUI↔内核桥接（callback→queue→SSE/after→前端渲染）
> - 内嵌 Hermes 内核的桌面应用打包成单文件 EXE（PyInstaller）；接入表格/办公能力并让 Agent 安全地改表
> - 强类型结构化输出（`PluginLlm.complete_structured`）/ 多模态输入 / 业务上下文注入
>
>  **权威事实来源**：`hermes-llms-full.txt`（官方全文，HARD-GATE 必读，见 §1 门 1）+ 本地已装 Library 源码（文档滞后以源码为准）；
>  旗舰参考实现 `examples/01-hermes-desktop/`（自包含底座，见 §4 资源与导航）。

---

## §0 上游漂移跟踪（每次使用前先看）

> Hermes 高频发版，API 断言来自 `hermes-agent` 某一确定版本的源码（见 `references/api-baseline.json` 锁定的 `baseline_version`）。**先确认版本是否漂移，再照着写代码。**

- 快速检查：`python scripts/track_upstream.py --quick` + `python scripts/check_api_signature.py`
- 四条跟踪线（发行版 / 文档指纹 / 源码签名 / API 参考）与漂移应对见 [`references/07-quality-gates.md`](references/07-quality-gates.md)

- 库级 API 参考（`references/api-reference/`，ast 静态解析自本机已装源码、按模块拆分：`run_agent`/`toolsets`/`gateway.session`/`mcp_serve`）由 `python scripts/gen_api_reference.py` 一键生成；本地升级 hermes-agent 后运行 `python scripts/track_upstream.py --regenerate-apiref` 自动重生成，并纳入 §0 第四线（API 参考）版本一致性检查。

> ⚠️ **铁律**：有 `REMOVED` / `DEFAULT_CHANGED` 漂移时，**先更新技能再开工**，禁止带病作业。

---

## §1 HARD-GATE：两道必读门（不可跳过）

### 门 1：`hermes-llms-full.txt`（官方文档全文，约 68,000 行）

**做任何 Hermes 相关开发前，必须先检索相关章节。** 它是 Nous Research 官方文档完整导出（用户视角+运维视角）。

> ⚠️ 本技能核心是「Library 怎么被调用与集成」，这部分官方文档覆盖极稀薄（仅 `guides/python-library` 一页，漏全部 15 个构造器回调）。因此：
> - **语义与概念**（toolset / skill / session / HERMES_HOME / 危险命令审批）→ 查 llms-full.txt
> - **Library API 签名与参数** → 查 [`references/01-library-api.md`](references/01-library-api.md)（源码派生），有疑问直接读本地已装源码
> - **文档与源码冲突时，以源码为准**，并在 [`docs/troubleshooting.md`](docs/troubleshooting.md) 记一笔

索引：全局导航见 [`references/00-index.md`](references/00-index.md)（事实基线/阅读顺序/单真相源映射/llms-full 检索地图）。

### 门 2：GUI 框架侧的权威源（按路线二选一）

本技能已内置主流渲染框架的集成范式（Python 原生 A 类 + JS/Node 前端 B 类），无需依赖外部技能：

| 路线 | 必读文件（本技能内自带） | 内容 |
| --- | --- | --- |
| **渲染框架（FastHTML/Tkinter/pywebview/PyQt/textual + Electron/React/Vue/Koa + .NET/Java/C/C++/Rust 宿主）** | [`references/04-rendering-frameworks.md`](references/04-rendering-frameworks.md) | 各框架接入 Hermes Python Library：FastHTML+pywebview（SSE / queue 桥）、Tkinter/PyQt/textual（worker 线程 + 主线程回传）、Electron/React/Vue/Koa（Python 后端 + stdio/命名管道/本地 socket 桥接，不连网关 8642）、.NET/Java/C/C++/Rust（嵌入 Python 运行时或本地桥接，见 §10–§13） |

> 需要框架本身完整 API 时，查阅对应框架官方文档（FastHTML / Tkinter 官方资料，可联网）。

**跳过后果**：Library API 用错参数名（回调不触发、静默无流式）、GUI 组件属性写错、线程模型违规导致偶发崩溃。

---

## §2 这条路线到底是什么

```
┌─ 你的桌面 EXE（单进程）────────────────────────────────┐
│  GUI 层                     Hermes 内核层              │
│  ┌──────────────┐  callback │  AIAgent                │
│  │ FastHTML     │◄─────────┤  (run_agent.py)         │
│  │  + pywebview │  queue   │                          │
│  │     或       │──────────►│  run_conversation()     │
│  │ Tkinter      │  用户输入  └────────┬─────────────────┘
│  └──────────────┘             tools/ toolsets/        │
│                               （进程内直接调用）       │
└──────────────────────────────┬─────────────────────────┘
                               │ 只有这一条出网连接
                               ▼
                    LLM Provider（DeepSeek/OpenRouter/…）
```

**进程内直跑路线与其他路线（以进程内为例说明拓扑差异）**：进程内直跑路线下没有第二个进程、没有 `hermes gateway`、没有 `127.0.0.1:8642`、
没有 `API_SERVER_KEY`、没有 CORS——Agent 就是你进程里的一个 Python 对象。若选用跨进程路线，则这些由对应服务承担（选型与落地见 references/02-integration-core.md §2 路径 D）。

> 上述为**进程内直跑路线**的收益/代价示例（仅作拓扑差异说明，不意味着该路线优先）。5 条路线**平等可选**，按需求权衡；跨进程路线选型与落地见 references/02-integration-core.md §2 路径 D。
> ✅ **进程内直跑收益**：单进程单文件 EXE 双击即用；无端口/CORS/健康探测；回调是 Python 对象零序列化开销。
> ❌ **进程内直跑代价**：无法远程（GUI 与内核须同机同解释器）；无进程隔离（安全靠 `disabled_toolsets` + 自建工具面）；崩溃带走整个 GUI（try/except 包裹 worker）；升级需重新打包；无法多客户端共享内核。

---

## §3 架构约束（集成前必读，共 5 条）

1. **`AIAgent` 不是线程安全的，绝不共享实例。** 内部持有会话历史、工具会话、迭代计数器，**每次对话新建一个**。
2. **`run_conversation()` 是阻塞的同步调用。** 在 GUI 主线程（Tkinter/FastHTML/Electron renderer/PyQt）里直接调 = 冻界面。**必须 worker 线程 + 队列/本地桥接**。
3. **流式不靠返回值，靠回调。** `run_conversation()` 跑完才返回。要实时输出**必须**传 `stream_callback`（文本增量）+ `__init__` 的事件回调（工具/推理）。
4. **`HERMES_HOME` 决定一切运行数据落点，且必须可写。** 冻结态（EXE）下应显式指向 `<exe>/hermes_data`。
5. **不跨进程隔离的路线（如进程内直跑）没有内建安全边界。** 官方 API Server 至少有 key 鉴权；进程内直跑什么都没有。**进程内直跑时强制 `disabled_toolsets=["terminal"]` 起步**，业务能力用自建纯 Python 工具补。（若选用跨进程路线，鉴权边界由对应服务承担；绑非本机地址时 terminal 需沙箱。）

---

## §4 主题路由（Skill Graph · 地图索引）

> 原则：先按「我要做什么」命中下方 **MOC 意图聚类**，再读聚类下的节点文件。每个文件有**唯一主导归属**（见 MOC 总览）；
> 若它同时跨主题，主导聚类之外的交叉用途在「何时进」里标注。**`00-index.md` 是唯一权威索引**（阅读顺序 / 单真相源 / llms-full 检索地图），
> 本 MOC 只做「意图 → 入口文档」的速查，二者分工、不重复维护。

### 🗺 MOC 总览（按任务意图，每文件一个主导聚类）

| 聚类 | 主导节点 | 何时进 |
| --- | --- | --- |
| **A 核心 API 与库结构** | 01-library-api / 10-hermes-cli / 11-library-support / 12-tools-modules / 13-agent-modules / 14-library-infra / 16-gateway-package | 写集成代码、查 `AIAgent` 签名、查模块构成 / 排障 |
| **B GUI 集成与能力** | 04-rendering-frameworks / 03-capabilities-and-toolsets / 08-capability-integration | 接渲染框架、开关 57 工具集 / 审批闭环、接能力层 |
| **C 业务整合与路线选型** | 02-integration-core / 15-api-server / 18-tristructure-architecture | 让 Agent 懂业务、选 5 条调用路线、走 API Server / `/v1`、业务成完整系统时按三系统分离 |
| **D 环境、打包与质量** | 05-install-and-env / 06-packaging / 07-quality-gates / 09-integration-e2e | 建 venv、出单文件 EXE、过门禁、做端到端验证 |

> 交叉提示：`02-integration-core` 同时承载「界面接入」与「路线选型」（进程内三条路径 + §2 路径 D），是 C 的主导、也常被 A/B 引用；
> `01-library-api` 的会话/记忆运行时方法常被 GUI 集成（B）用到——**主导归一处，跨聚类需求仍以各文档正文为准**。

### A 核心 API 与库结构（本技能的心脏）

| 文件 | 内容 | 优先级 |
| --- | --- | --- |
| [`references/01-library-api.md`](references/01-library-api.md) | **`AIAgent` 完整构造参数表（含全部 15 个构造器回调 + `run_conversation`/`chat` 的 `stream_callback` 方法参数）+ 签名 + 返回结构 + 结构化输出与多模态输入（§3.4bis：`request_overrides` 透传 / `ctx.llm.complete_structured` 强类型 / OpenAI 风格多模态消息）**，源码派生并标行号 | **写任何集成代码前必读** |
| [`references/10-hermes-cli.md`](references/10-hermes-cli.md) | **`hermes_cli` 完整参考（顶层 147 模块 / 含嵌套共 205）**：分组清单 + 逐模块用途与代表 API + 可复用模块详解 + llms-full 检索地图 | import 某个 `hermes_cli` 子模块 / 查 CLI 能力时 |
| [`references/11-library-support.md`](references/11-library-support.md) | **`batch_runner` + Hermes 自有支撑单文件模块**（`hermes_constants`/`hermes_state`/`hermes_logging`/`hermes_time`/`hermes_bootstrap`/`model_tools`/`toolsets`/`toolset_distributions`/`utils`/`trajectory_compressor`）：逐模块公开 API | 查 `HERMES_HOME`/会话落盘/原子写/自定义工具集/批量跑 Agent 时 |
| [`references/12-tools-modules.md`](references/12-tools-modules.md) | **`tools` 包全量模块枚举（113 个嵌套子模块）**：逐模块用途 + 代表 API | 查某个 `tools.*` 工具实现模块是否存在/能否进程内用时 |
| [`references/13-agent-modules.md`](references/13-agent-modules.md) | **`agent` 包参考（155 模块全量枚举 + 六项深度主题）**：§1 逐模块用途 + 内核分类 + 代表 API；§2 深度主题（上下文压缩/记忆/用量遥测/模型路由/一次性调用/安全护栏）含类·方法·集成要点 | 查 `agent` 内核构成 / 排障 / 接入某一项 agent 能力时 |
| [`references/14-library-infra.md`](references/14-library-infra.md) | **剩余 Hermes 自有基础设施模块**（`gateway`/`cli`/`cron`/`plugins`/`providers`/`acp_adapter`/`tui_gateway`/`mcp_serve`）：用途 + Library 全貌收口 | 确认 Library 还有哪些进程外设施、为什么不起网关时 |
| [`references/16-gateway-package.md`](references/16-gateway-package.md) | **顶层 `gateway` 包全量模块枚举（77 个 `.py`）**：逐模块用途 + 代表 API + 0.19.0 实际承载的平台清单 | 查网关运行时构成 / 某个 `gateway.*` 模块 / 网关承载哪些平台时 |

### B GUI 集成与能力

| 文件 | 内容 | 何时进 |
| --- | --- | --- |
| [`references/04-rendering-frameworks.md`](references/04-rendering-frameworks.md) | 多框架接入与整合（FastHTML/Tkinter/pywebview/PyQt/textual + Electron/React/Vue/Koa + .NET/Java/C/C++/Rust 宿主，逐一接入范式见 §1–§13；选型速查见 §10） | 选渲染框架 / 接入某框架时 |
| [`references/03-capabilities-and-toolsets.md`](references/03-capabilities-and-toolsets.md) | **57 工具集（33 capability + 24 hermes-*）逐条文档** + 减法原则 / 审批闭环 / 开关配方 | 开/关某能力、排查工具缺失时 |
| [`references/08-capability-integration.md`](references/08-capability-integration.md) | **57 工具集之外的能力层逐条**（Goals/Snapshots/MOA/Projects/Bundles/Security Audit/Blueprints/Batch/Journey/Backup/Profiles/Curator/Routing/Kanban/IM 桥），均经 0.19.0 源码核实 | 接能力层时 |

### C 业务整合与路线选型

| 文件 | 内容 | 何时进 |
| --- | --- | --- |
| [`references/02-integration-core.md`](references/02-integration-core.md) | **业务系统与 Agent 双向整合（界面接入 + 业务赋能，一个整体）**：进程内三条路径 + SSE 桥接 + 能力→模块地图 + CLI 复用 + 最小骨架 + 治理，加上非侵入扩展面（Skill/MCP/Plugin/Memory）与三种加业务工具方式对比；**§12 含 `ctx.llm` 宿主推理（`PluginLlm.complete/complete_structured` 强类型结构化 + 业务上下文注入）**。**源码派生核实（版本见 00-index 事实基线）** | 做集成/流式/复用 CLI 逻辑、给 Agent 接业务工具/记忆/流程、**要强类型结构化输出（§12）**时 |
| [`references/15-api-server.md`](references/15-api-server.md) | **API Server 路线完整手册**（判据/三种实现路径/配置/端点全清单/认证安全/接入示例/进程内自建/检查清单） | 要开 API Server / 接 OpenAI 兼容前端 / 走 `/v1` 时 |
| [`references/18-tristructure-architecture.md`](references/18-tristructure-architecture.md) | **三系统解耦架构（高内聚低耦合的工程级落地）**：业务系统/连接系统/Agent系统 拆分、两层高内聚低耦合（系统间依赖铁律 + 系统内部模块内聚）、底座三步替换法、三系统验证门禁 `verify_tristructure.py` | 业务是完整系统、需独立交付/底座可整体替换/业务与 Agent 必须解耦时（见 §5 ⓪ 架构形态决策） |

### D 环境、打包与质量

| 文件 | 内容 | 何时进 |
| --- | --- | --- |
| [`references/05-install-and-env.md`](references/05-install-and-env.md) | **`pip install hermes-agent` 的坑**、HERMES_HOME（hermes_constants 唯一真相）、环境变量表、依赖 extras | 部署/切换运行环境时 |
| [`references/06-packaging.md`](references/06-packaging.md) | PyInstaller 打包内嵌 Hermes 的完整配方、hidden-import 清单、冻结三坑 | 出 EXE / 交付一键启动入口时 |
| [`references/07-quality-gates.md`](references/07-quality-gates.md) | **反模式红线(12 条) / 门禁脚本 / 运行数据保护 / 工作流**（上游跟踪见 `scripts/`） | 提交/发版前 |
| [`references/09-integration-e2e.md`](references/09-integration-e2e.md) | **集成自测与端到端验证（跑通一个集成）**：Hermes 作为 Agent 的测试特殊性、专项断言清单（含宿主系统原有功能用例）、walkthrough、反模式；**§8 Agent 输出评估（LLM Judge 三段式）/ §9 离线确定性测试（mock 回放）** | 做集成自测 / 端到端验证 / 输出质量评估时 |

### 资源与导航（唯一权威 + 参考实现 + 门禁脚本）

* **唯一权威索引**：**`references/00-index.md`** —— 全局导航（阅读顺序 / 事实基线 / 单真相源映射 / llms-full 检索地图），任何时候先看它。
* **签名参考**：`references/api-reference/`（自动生成，ast 静态解析 0.19.0 源码）——查精确类/方法/参数/返回/异常签名，由 `scripts/gen_api_reference.py` 一键重生成；`scripts/api-baseline.json` 供 `check_api_signature.py` 比对。
* **参考实现（⭐ 对接时优先复制 examples/01）**：
  * [`examples/01-hermes-desktop/`](examples/01-hermes-desktop/) —— **旗舰示例**，自包含进程内 `AIAgent` + FastHTML/pywebview 底座（SSE 流式、工具可视化、自定义 toolset、思考折叠、EXE 打包），刻意不含业务。完整说明见其 `README.md`。
  * [`examples/02-hermes-pywebview-multiagent/`](examples/02-hermes-pywebview-multiagent/) —— **pywebview 多 Agent 变体**（拉取自开源 Felix-Forever/hermes-agent-desktop，MIT）：纯 pywebview 极简（单 `app.py` + `index.html`）+ 多 Agent 编排。说明见其 `skill-note.md`。
  * [`examples/03-nesquena-hermes-webui/`](examples/03-nesquena-hermes-webui/) —— **Web UI 本地适配**（源自开源 nesquena/hermes-webui，17k+ stars）：三栏浏览器/手机 Web 界面，与 CLI 1:1 对等；`server.py` + `api/` 路由包 + `static/` 前端，经 `api/agent_runtime.py` 以 `from run_agent import AIAgent` 驱动核心；Windows 原生 `start-webui.bat` / `start.ps1` 启动（端口 8787）。完整说明见其 `README.md`。
  * [`templates/`](templates/) —— 最小骨架（FastHTML 版 / Tkinter 版各一套）。
* **文档**：`docs/glossary.md`（不知从何下手看全景）、`docs/troubleshooting.md`（排障，问题沉淀首选）、`docs/delivery-checklist.md`（交付验收清单）。
* **门禁脚本**（按需调用，详见各自 `--help`）：

| 脚本 | 用途 |
| --- | --- |
| `quality_check.py` | 一键门禁（6 步）：py_compile + 技能结构 + 离线桥接 + 签名漂移 + 网页回归 + 文档链接 |
| `release_gate.py` | 统一发布门禁（打包/交付前必跑）：6 硬门禁 + 2 CI 建议项（含 version 一致性：SKILL.md `version` 必须等于 CHANGELOG 最新；`--bump-version` 自动同步，杜绝滞后） |
| `check_js_modules.py` | 前端 ES 模块强制校验（条件性硬门禁） |
| `check_endpoints.py` | 前端→后端路由链路校验（捕获运行时 404） |
| `smoke_test_web.py` | 网页无头冒烟（关键 DOM id + `/healthz` 200，无需 Key） |
| `track_upstream.py` | 上游漂移跟踪（四线：PyPI 版本 / 文档指纹 / 源码签名 / API 参考，含内容哈希比对；`--gate` 硬阻塞、`--regenerate-apiref` 重生成） |
| `check_api_signature.py` | 源码签名比对（ast 静态解析，不 import） |
| `probe_library.py` | 探测已装 Library：版本、路径、可导入性 |
| `check_skill_gate.py` | 技能自身结构门禁 |
| `verify_tristructure.py` | 三系统架构验证门禁（可选模式）：业务纯净 / 连接唯一装配点 / 独立入口 / 底座纯净；未启用三系统则 SKIP |
| `ui_window_verify.py`（可选） | FastHTML 路线界面视觉质检（pywebview 原生 DOM 断言 + 截图） |
| `ui_automate.py`（可选） | FastHTML 路线 UI 交互自动化（点击/输入/导航/断言） |

---

## §5 快速对接工作流（本技能主线）

> 本技能**重点是「在已有系统/底座中对接与集成 Hermes」**，因此工作流**轻前序、重对接、简后序**：
> 从「用户给需求」到「进入集成」只需一步合规检查；集成是主体；后序用现成门禁一键收尾，不展开、不重复造流程。
> 详细步骤与脚本用法见 [`references/07-quality-gates.md`](references/07-quality-gates.md) §4，本清单为执行主线。

```
> **⓪ 架构形态决策（开始前先定形态，见 [`references/18-tristructure-architecture.md`](references/18-tristructure-architecture.md) §4 判据）**：
> - **单工程内嵌**（默认）：中小型单一应用，复制 `examples/01` 直接加业务——本流程主体。
> - **三系统分离**：业务是完整系统（需独立交付 / 底座可整体替换 / 业务与 Agent 必须解耦）→ 按 18 号文档把工程拆为 `业务系统/` + `连接系统/` + `Agent系统/`(=01 纯净底座)，装配由连接系统 `fuse_business_into_agent()` 承担。

用户要"在我的应用里加个 AI"（或已有桌面 GUI 应用）
  │
  │
  │   [架构形态决策] 单工程内嵌（默认）→ 本流程；三系统分离 → 见 references/18号文档
  │
  ├─ ⓪ 上游漂移（--quick，不深挖）：track_upstream.py --quick + check_api_signature.py
  │     → 有 REMOVED/DEFAULT_CHANGED 先修技能；无则直接进入对接
  │
  ├─ ① 集成前合规检查（几分钟，判定能否对接，过即进入集成）
  │    GUI 框架/宿主是否为本技能已覆盖的主流框架（FastHTML/pywebview/Tkinter/PyQt/textual + Electron/React/Vue/Koa，
  │    或其他语言宿主 .NET/Java/C/C++/Rust 经嵌入运行时/本地桥接）？
  │    （其他 → 参考 04 §15 通用桥接范式，或评估能否套用 B/C 类「进程内嵌入 / 本地桥接」）
  │    Python ∈ [3.11, 3.14)？
  │    能 from run_agent import AIAgent（跑 scripts/probe_library.py）？
  │    主线程事件循环模型，规划 worker 线程落点？
  │    → 过 → 立即进入 ②（默认路径，已有系统加 Agent）
  │
  ├─ ② 对接底座：复制 examples/01-hermes-desktop（或 templates/）
  │    先跑通「最小可对话 Agent」：一句话进、一句话出、流式可见
  │    ▶ 铁律：先跑通空壳再加业务；不改造底座（复制-适配-加你的业务）
  │
  ├─ ③ 回调桥接：stream_callback（文本）+ action/action_result（工具卡片）+ reasoning（思考）
  │    → queue → SSE/after → 前端渲染（见 references/04-rendering-frameworks.md）
  │
  ├─ ④ 工具面与安全：disabled_toolsets=["terminal"] 起步
  │    → 自建纯 Python 工具注册 toolset → 审批闭环（见 references/03-capabilities-and-toolsets.md §2）
  │    ▶ 表格/办公需求走 03-capabilities-and-toolsets.md §2 审批闭环（办公受控工具面治理模型）
  │
  ├─ ⑤ 验证（每步对接完成即验，防假绿）：
  │    py_compile + 导入 + 离线桥接测试（quality_check.py，无需 API Key）
  │    + 回调触发验证（断言 stream_callback 被调 ≥1 次，本技能独有，不可省）
  │    + 真实 LLM 往返冒烟（含 Key 环境交付前由用户执行）
  │    → FastHTML 路线示例另加：ui_window_verify.py（视觉质检）+ ui_automate.py（交互自动化），均可选
  │
  ├─ ⑥ 一键门禁（打包前必跑）：release_gate.py
  │    （track_upstream --gate + quality_check + check_endpoints + smoke_test_web + check_js_modules，全绿放行）
  │
  └─ ⑦ 打包交付：最小 venv → PyInstaller --onefile → hidden-import 清单 → 冒烟
       → 填 docs/delivery-checklist.md → 说明产物/用法/退出 → 交付确认（含测试证据）
```

> **要点**：链路 7 步，其中 ②③④ 是核心对接（占主要工作量），前序仅 ① 一步合规检查，后序 ⑥⑦ 一键门禁+打包
> 均复用现成脚本，不在前序流程与后序流程上耗费时间。详细版与产出物见
> [`references/07-quality-gates.md`](references/07-quality-gates.md) §4。

---

## §6 必须遵守的铁律（最高优先级）

### 装包与环境

* 🔴 **`pip install hermes` 装的是完全无关的另一个包！** PyPI 上 `hermes`（0.9.1）是 Helmholtz 的科研软件元数据工具，且也提供 `hermes` CLI——装错会命令冲突。**正确的是 `pip install hermes-agent`**。
* **发行包名 ≠ 导入名，无统一命名空间包**：`pip install hermes-agent` 后 23 个顶层模块平铺进 site-packages（`run_agent`、`agent`、`tools`、`toolsets`、`gateway`、`hermes_cli`…）。**导入写 `from run_agent import AIAgent`，不是 `from hermes_agent import ...`**。
* **Python 版本硬约束**：`>=3.11, <3.14`。3.10 及以下、3.14 及以上都装不上。
* **依赖按需装 extras**：`hermes-agent[all]` 极重。按路线按需装 extras：FastHTML+pywebview 路线通常还需 `[web]`；Tkinter/PyQt/textual/Electron 等原生或本地桥接路线用基础包即可（勿带 `[web]`；最小 venv 铁律见 [`references/06-packaging.md`](references/06-packaging.md) §1）。全清单见 [`references/05-install-and-env.md`](references/05-install-and-env.md)。

### 集成编码

* **绝不复用 `AIAgent` 实例**：每次对话新建。共享 = 会话串台 + 计数器错乱。
* **绝不在主线程/事件循环里直接 `run_conversation()`**：必须 worker 线程 + `queue.Queue`。Tkinter/PyQt 侧 `root.after()`/`Signal`；FastHTML 侧用生成器消费队列产出 SSE；Electron/React/Vue 侧经本地桥接把事件推到前端（见 `04` §7–§8）。
* **流式必须传 `stream_callback` 给 `run_conversation()`**，工具/推理事件回调传给 **`AIAgent.__init__`**。两者位置不同：
  ```python
  agent = AIAgent(..., tool_start_callback=cb1, reasoning_callback=cb2)   # 事件 → 构造函数
  agent.run_conversation(user_message=..., stream_callback=cb3)           # 文本增量 → 方法参数
  ```
* **必须 `quiet_mode=True`**：否则 Hermes 的 CLI 输出会污染 stdout / GUI 日志窗。
* **必须显式设 `max_iterations`**：源码默认 **90**（官方文档写 500，不一致）。桌面问答建议 10~30，防跑飞烧钱。
* **必须 `disabled_toolsets=["terminal"]` 起步**：进程内无隔离，放开 terminal = 把 shell 交给模型。**别误写 `enabled_toolsets=["file"]`**——那会把 web/memory/code_execution 等能力全砍掉（功能退化）。
* **回调里禁止做重活、禁止碰 GUI 控件**：回调在 worker 线程执行，只能 `queue.put(...)`，渲染交给主线程。
* **`HERMES_HOME` 冻结态必须显式指向 `<exe>/hermes_data`** 并确保可写。

### 质量与门禁

* **回调触发验证（本技能独有，不可跳过）**：集成后必须跑一次真实对话，断言 `stream_callback` **确实被调用过 ≥1 次**。很多路径静默降级成「一次性出全文」——不验证就发现不了。
* **冒烟测试（结构级，无需 Key）**：`python scripts/smoke_test_web.py` 断言关键 DOM id + `/healthz` 200，捕获「首页渲染崩溃」。
* **界面视觉质检（可选，FastHTML 路线）**：`scripts/ui_window_verify.py` 做 pywebview 原生窗口断言式质检 + `ui_automate.py` 交互自动化；与 `smoke_test_web.py` 互补（后者验"关键节点存在"，前者验"视觉上没问题"）。
* **反复核实（万无一失）**：技能内容（API 签名 / 版本基线 / 路径引用 / 门禁脚本）**任何改动**后，必须重跑 `track_upstream.py` + `check_api_signature.py`（§0）+ `quality_check` + `check_endpoints` + `check_js_modules`（原生 ES 模块前端示例）+ `smoke_test_web` + `release_gate`，任一项硬失败即阻断。

### 打包

* **`--onefile`**，禁 `--onedir`。
* **Hermes hidden-import 必须逐个列**：`run_agent`、`hermes_constants`、`hermes_state`、`agent.*`、`tools.*` 逐个写。**禁止 `--collect-submodules tools`（会 OOM）**。
* **函数内懒加载的模块必须显式 `--hidden-import`**：Hermes 大量使用 `def f(): from agent.xxx import yyy` 的延迟导入，PyInstaller 静态分析抓不到。
* 完整配方见 [`references/06-packaging.md`](references/06-packaging.md)。
* **一键启动脚本必须走规范流程**（见 [`references/06-packaging.md`](references/06-packaging.md) §3/§7）：`启动.bat` 一律 **GBK 编码 + CRLF**（⛔ 禁 UTF-8/`chcp 65001`，否则中文在括号块乱码导致双击闪退）；venv 用全局 `%LOCALAPPDATA%\hermes-desktop\venvs\<name>`（⛔ 禁在 examples 目录内建 .venv）；创建后必须按 §7 **四步验证**（venv/依赖 → 启动 → 端口+健康端点 → 前端/窗口）确认能启动。

---

## §7 反模式与红线

完整 12 条反模式红线（⛔ 路线错误清单）见 [`references/07-quality-gates.md`](references/07-quality-gates.md) §1。

---

## §8 代码与结构原则（仅本技能相关）

* Agent 集成代码独立成模块（如 `agent_runtime.py`），不要塞进路由文件。
* 分层：GUI 层 / 桥接层（callback→queue）/ Agent 构造层 / 工具层，四层不混。
* 工具函数纯 Python 实现，不 shell 调用。
* 单文件过大主动拆分；框架面（Loops / Delegation / Commands）按功能域拆包（共享工具入 `_utils.py` 防循环导入，`__init__.py` 重导出保持向后兼容），适用于「后端逻辑聚合层」膨胀场景。
* **高内聚低耦合（工程组织 + 模块设计两层）**：业务是完整系统时，按 [`references/18-tristructure-architecture.md`](references/18-tristructure-architecture.md) 组织为 `业务系统/` + `连接系统/` + `Agent系统/` 三系统：业务系统纯业务（禁 `import` Agent 模块）、连接系统纯桥接（唯一装配点 `fuse_business_into_agent()`）、Agent系统=上游纯净底座（可整体替换）。
* **同样适用于各系统内部模块**：单一职责、模块分层（路由/服务/桥接/数据不跨层）、共享辅助抽公共模块消除 copy-paste、死代码（未引用模块/函数/import）一律清理（`pyflakes`/`autoflake` 佐证）。
