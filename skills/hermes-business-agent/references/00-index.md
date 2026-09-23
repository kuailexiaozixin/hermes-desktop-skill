# 00 · hermes-business-agent 参考文档索引（检索地图 + 全局导航 + 事实基线）

> 本文件是 **hermes-business-agent** 技能的**唯一权威索引**，提供 `hermes-llms-full.txt` 检索地图、全局导航与事实基线。所有结论均经 `hermes-agent==0.19.0`
> 的已安装包**逐条源码内省**核实（见 §4 事实基线），并对照技能内置参考实现
> `examples/01-hermes-desktop` 的实战写法交叉验证。任何与本文不符的描述，以本文 + 源码为准。
>
> **最优先**：本文 §1 即 `hermes-llms-full.txt` 检索地图（完整版，自 `10-hermes-cli.md` §5 移入）——写任何代码前先在此检索确认语义。

---

## 1. `hermes-llms-full.txt` 检索地图（完整版，最优先）

> `hermes-llms-full.txt` 是 Hermes 官方文档全文的内置副本（**当前基线 91,898 行 / 5.0 MB**，md5、体积与下载来源记在
> `references/docs-baseline.json`——那是唯一真相，禁止别处复述行数；`--update-docs` 重拉后只改 sidecar 与本行）。
> 本技能入场检查（SKILL.md〔入场检查〕）
> 要求写代码前先在此检索对应章节确认语义。**文档与源码冲突时一律以源码为准**（本文档集即源码派生版）。

### 1.1 按任务 → 检索关键词

> 最后一列是**适用路线**（① 进程内直跑 / ② Hermes 网关 / ③ spawn CLI / ④ API Server / ⑤ 仅 `/v1`，见 `02` §2.1–§2.5）——
> 五条路线平等，没有"本路线"。单元格只说**哪几条路线用得上**，禁止把它读成推荐。

| 你想做的事 | 在 llms-full.txt 检索的标题 / 关键词 | 适用路线与落点 |
| --- | --- | --- |
| 确认 `AIAgent` 概念 / Library 模式 | `Using Hermes as a Python Library` / `run_conversation()` | ①⑤ 自建（详见 `01`）；②③④ 内核仍同此，只是运行在服务端进程 |
| 模型 / Provider / key 配置 | `Configuration` › `Configure a model` / `base_url` / `api_key` | 全路线；②④ 在服务端配（`15` §3、`06` §9.5），①③⑤ 在宿主进程配（`05` §5） |
| Toolset 启用 / 自定义注册 | `Tools & Toolsets` / `ctx.register_tool` | 全路线；概念看这里，进程内注册落地见 `01`/`03` |
| 工具按需加载 / 渐进披露（MCP 工具多） | `Tool Search` / `tool_search` | 全路线（内核特性）：MCP/插件工具的 agent 级渐进披露，内置核心工具从不延迟；57 工具集减法原则仍归 `03` §1 |
| 子 Agent 委托 / 多 Agent 任务分解 | `Configuration` › `Delegation`（`delegate_task`）/ `Kanban worker lanes` | ①③⑤：`delegation` 在 `03` 基线内可进程内用；Kanban 为跨进程持久工作队列（②④ 形态） |
| 回调触发时机 | `## Callback Surfaces` / `reasoning_callback` | ①③⑤ 直接对接界面；②④ 在服务端进程内同用，客户端侧改看 SSE 事件（`15` §4/§4bis） |
| 多轮会话 / 持久化 | `Sessions` › `Session Storage` / `session_id` | 全路线；②④ 另有会话头与管理端点（`15` §4） |
| MCP toolset 接入 | `MCP Servers` | 全路线；接法与筛选见 `02` §11（`hermes mcp configure` 选只读面） |
| 插件 Plugins | `Plugins` | 全路线（`plugins`/`skills_hub`），随 `HERMES_HOME` 走 |
| 危险命令审批 | `Security` › `Dangerous Command Approval` | ①③⑤ 自建（`03` §2、`02` §7）；②④ 有网关分类器与 `/v1/runs/{id}/approval`（`15` §4bis） |
| HERMES_HOME / 配置落点 | `Configuration` › `Managing Configuration` | 全路线；②④ 每 profile 一棵子树，服务端可重定向（`05` §2、`06` §9.1） |
| CLI / TUI 用法 | `CLI Interface` / `TUI` | ③ 直接驱动；①⑤ 复用辅助逻辑见 `10` §3（禁止进程内 spawn 子进程，R1） |
| **API Server `/v1`** | `API Server` | ④⑤（② 承载）；手册 `15`，服务侧部署 `06` §9 |
| gateway / sidecar | `Gateway` / `Container Architecture` | ②（④ 方式 A 依赖它）；模块枚举 `16` |
| Agent 间通信（A2A 协议） | `A2A (Agent-to-Agent)`（user-guide/messaging/a2a） | 入站（Agent Card / JSON-RPC / SSE）需 ②；出站 `a2a` 工具集不在 0.19.0 基线 57 集表内，用前先核实实装 `TOOLSETS` |
| Managed Mode / Docker 部署 | `Managed Mode` / `Docker` | ②④（跨进程部署，`06` §9.2）；①③⑤ 单机形态无关 |
| 官方 Hermes Desktop（Electron 桌面端） | `apps/desktop/`（README + DESIGN + AGENTS 三篇，随 wheel 装进 site-packages，本地可读）；CLI 子命令 `hermes desktop`（别名 `gui`）记在 `hermes-llms-full.txt` 的 CLI 一览表 | 与本技能正交：它是官方成品通用聊天桌面端，**不含**你的业务工具面与界面定制。要现成品直接 `hermes desktop`，要自建界面走本技能路线；本文档不另立对照表 |
| 消息平台（Telegram/Slack…） | `Integrations` / 各平台 adapter | ② 独有（适配器清单 `16` §2）；①③④⑤ 无此能力，需要就换路线 |

### 1.2 检索技巧

- 文档随版本重排，**不要依赖行号**，用标题/关键词检索。
- 版本漂移重灾区：`Callback Surfaces`、`Tools & Toolsets` 的注册 API、`Configuration` 的 schema。
  每次大版本（如 0.18→0.19）后跑 `scripts/track_upstream.py --update-docs` 重拉并比对 md5。
- **它对「Library 如何被调用与集成」覆盖极薄**：官方只有 `guides/python-library` 一页，`## Callback Surfaces` 一节
  只提到 16 个构造器回调中的 8 个（`tool_progress_callback`、`thinking_callback`、`reasoning_callback`、`clarify_callback`、
  `step_callback`、`stream_delta_callback`、`tool_gen_callback`、`status_callback`）；桌面界面最常挂的 `event_callback`、
  `tool_start_callback`、`tool_complete_callback`、`notice_callback` 等另外 8 个通篇没有。全量清单与参数含义在 `01` §3.6.6，
  本节只登记"官方缺哪几个"这一条事实，供第 ③④ 步挂回调前先核对。
- 文档说「只能 clone」→ 与实测（pip 可装 wheel）冲突时，**以实测为准**，并在 `docs/troubleshooting.md` 记一笔。

### 1.3 跨路线关键词速记（选了哪条路线，这些就是"看错篇目"信号）

同一批关键词在五条路线下的含义正好相反，逐条对照路线编号核对：
`API_SERVER_KEY` · `CORS` · `127.0.0.1:8642` · `hermes gateway` · `/v1/chat/completions` ·
`Dockerfile` · `Managed Mode` · 官方 `apps/desktop` · Telegram/Slack 平台 adapter · A2A 入站（`A2A_HOST`/`A2A_PORT`）。

- **选 ①（进程内直跑）时看到它们** = 走错篇目了：这套是 ②④ 的东西，停下回 `02` §2.1 核对选型，
  禁止在进程内形态里去连 `8642`、配 key、配 CORS（`07` R2/R3）。
- **选 ②④ 时** = 正常，按 `15`（含 `06` §9 服务侧部署）/`16` 走。
- **选 ③ 时** = 只有 spawn CLI 与 `/v1` 无关；要 HTTP 面就改选 ④⑤。
- **选 ⑤ 时** = 端点在自己的进程里，网关侧配置（`API_SERVER_*`）不适用，鉴权与 CORS 自建（`15` §7）。

---

## 2. 本技能定位与「文档 × 适用路线」标注

**定位一句话**：用 `hermes-agent`（`pip install hermes-agent` → `from run_agent import AIAgent`）**把 Agent 接进真实业务流程，
或从零开发 Agent 驱动的业务系统**——
宿主可以是 **FastHTML / Tkinter / pywebview / PyQt / textual（Python 原生）**、**Electron / React·Vue / Koa（JS 前端桥接）**、
**.NET / Java / C / C++ / Rust（其他语言宿主）**（接入方式见 `04-rendering-frameworks.md`），
调用 Library 有 **5 条平等可选**路线（逐条判据/拓扑/代价见 `02-integration-core.md` §2.1–§2.5）：

| 编号 | 路线 | 落地文档 | 交付形态 |
| --- | --- | --- | --- |
| ① | 进程内直跑 | `01`（API）+ `02` §3/§6（桥接与骨架）+ `04`（各框架）+ `06` §1–§8（打包） | 单文件 EXE / 单进程 |
| ② | Hermes 网关 | `16`（77 模块与平台适配器）+ `08` §11/§14/§15 + `06` §9（服务侧部署） | 常驻服务 + 客户端 |
| ③ | spawn CLI | `10`（205 模块清单）+ `06` §9.2（本机 sidecar 形态） | 主程序 + `hermes` 可执行 |
| ④ | API Server | `15` §2 方式 A（配置/端点/认证/`/v1/runs` 审批）+ `06` §9（守护/日志/升级回滚） | 服务端部署 |
| ⑤ | 仅 `/v1` | `15` §2 方式 B + §7（进程内自建薄层） | 单进程带本地端点 |

**各参考文档的适用路线**（读之前先看这行，避免把某路线的约束当通用铁律）：

| 文档 | 适用路线 | 说明 |
| --- | --- | --- |
| `01` `03` `04` `05` `08` `09` `10` `11` `12` `13` `14` `19` `20` `21` | 全（多数以 ① 为叙述示例） | 机制、语义、验证与建模与路线无关；涉及端口/鉴权处会就地标注 |
| `02` | 全（§2 是路线总表） | §3/§6/§8 具体条目按 ①/⑤ 叙述，§2.2–§2.5 给其余路线 |
| `06` | §1–§8 = ①⑤（冻结单文件交付）；§9 = ②③④（常驻服务 / sidecar 部署、守护、日志、滚动升级与回滚、多客户端） | 交付与启动的单一落点，两种形态都在本文 |
| `07` | 全（§1 逐条标了适用路线） | 红线与门禁；未标即全路线通用 |
| `15` | ④⑤ | API Server / `/v1` 手册（服务侧运维归 `06` §9） |
| `16` | ② | 网关包模块枚举 |
| `17` | 全 | 调试纪律（任何 Check/Test 失败后进） |
| `18` | 全（工程形态） | 三系统解耦；与调用路线正交，选 ①~⑤ 任一条都可用 |

> 文中凡以「进程内直跑」举例，**只代表叙述基线，不代表推荐**。`04`/`07` 里「不连 `8642`、不起网关、不 spawn CLI」类约束
> 均是**路线①**的接入约定；选了 ②③④⑤ 时它们本就如此，不算违规（对照 `07` §1 的「适用路线」列）。

> **Hermes 的根性**：官方文档把它描述为一个带 **self-improvement loop** 的 agent——每解决一个新问题就把做法沉淀成技能、
> 把事实写进记忆，再由 `memory.write_approval` 决定这些写入要不要人确认（consent-aware）。这决定了集成姿态：
> 把 Hermes 当**会积累的数字同事**，而非无状态 API 调用。机制基线见 §4，`memory`/`skill_manage` 的 API 见 `01`/`13`，能力语义见 `08`。
> 术语可核对：在 `hermes-llms-full.txt` 里搜 `self-improv` 命中 20 处（如 "the self-improvement loop that creates them"）；
> 官方用的是 self-improvement loop / agent self-improvement，**没有** "self-improving agent" 这一说法，也没有任何宣传语。

---

## 3. 反向索引：SKILL.md 第 N 步 ↔ 该读的文档

> **流程主线只有一处：SKILL.md 的工作流（入场检查 + 八步 + 回路）。** 本文不重排顺序、不再列"建议先读 A 再读 B"的独立流程——
> 那张表会和主线各说一遍、必然漂移。这里只做反向登记：执行到第 N 步时，需要哪些文档、各自解决什么。

| 主线位置（SKILL.md） | 主文档 | 按需补充 | 解决什么 |
| --- | --- | --- | --- |
| 〔入场检查〕漂移 · 语义源 · 环境可跑性 | `07` §2（跟踪四线）· `references/api-reference/` · `hermes-llms-full.txt`（技能根目录）· `05`（安装坑、`HERMES_HOME`、extras） | `01` §1/§3（签名冲突时） | 版本是否漂移；语义/签名各查哪个源；装什么、导入什么、数据落哪、凭证怎么走 |
| ① 定业务（收料 → 目标三句话 → 定入场 → 六问 → 分流 → 配验收并取背书 → 汇编六张表，`19` §7 第 6 张入口表在第 ② 步填） | `19`（全文即本步的七站流水线：§2.1 收料·入场与顺序、§2.2 六问·分流·配验收、§7 汇编）· `docs/glossary.md` | `20` §1–§2（schema 归属与三件套）· `21` §2.1（要采的字段先想好） | 业务结构如何一一对应到面、上下文与断言 |
| ② 定形态（部署入口 · 宿主 · 路线 · 能力入口配置 · 工程形态 · 组织约束与改动进仓的签认约定） | `18`（三系统判据与依赖铁律）· `02` §2.1–§2.5（五条路线逐节）· `04` §14（三问定宿主）· `19` §7 第 6 张（入口表在本步填） | `15`（考虑 ④⑤ 时）· `16`（考虑 ② 时）· `10`（考虑 ③ 时）· `06` §9（选 ②③④ 前先看服务侧要补的守护与回滚） | 四件互相牵制的事按依赖方向逐条确定（部署入口→宿主与路线，能力入口能否只落成配置行→工程形态），含非法组合 |
| ③ 最小可对话内核 | `01`（构造参数全表 + 回调） | `02` §6（骨架）· `examples/01-hermes-desktop`·`templates/` | `AIAgent` 怎么建、六条硬性规定的参数出处 |
| ④ 接界面 | `04`（A/B/C 三类逐一范式） | `01` §4.1（事件词汇）· `02` §3（SSE 桥接） | callback→queue→SSE/after→渲染 的框架化落点 |
| ⑤ 赋业务 | `02` §9–§14（四类扩展面 + §7.1 工具注册）· `19` §3–§5（三层面、分层注入与范围强制）· `20` §4.3–§4.4（用例形状即机检接口，四件同提交的对账段） | `03`（57 工具集逐条）· `08`（能力层逐条）· `10`/`11`/`12`/`13`（模块存在性字典）· `20` §2–§4（结构化输出、校验顺序、建用例）· `21` §4（要不要编排） | 让 Agent 懂业务：面、上下文、结论形状 |
| ⑥ 立闸门 | `03` §2（审批闭环）· `02` §7.2（内核护栏模块清单） | `19` §3/§6（幂等与回读、权限 diff）· `21` §3/§5（配额与四类降级契约）· `02` §7.3（办公受控面） | 能写之后怎么不伤人、确认怎么不退化成形式 |
| ⑦ 取证 | `09`（walkthrough + 断言清单 + Judge + mock 回放）· `07` §2–§3（门禁与自检） | `20` §4/§6（Golden 集与失败归因）· `17`（出口不过时的 Debug 闭环，跨所有步） | Check 与 Test 各自的脚本、断言与存档 |
| ⑧ 交付 | `06`（§1–§8 打包 + 一键启动 + 四步验证；§9 路线②③④ 的服务部署、守护、升级与回滚）· `07` §2（`release_gate`）· `docs/delivery-checklist.md` | `18` §7（三系统门禁）· `15` §10（路线④⑤ 端点检查与服务侧三条验收）· `21` §6（发布基线） | 出得了货、起得来、**在制品上与隔离环境里验过**、升得上、退得回去、**发出去有观察窗**、**窗收口时留一页"本期停在哪里"** |
| 〔回路〕运营回流 | `21` §2/§7（采什么、五步回路） | `20` §4.1/§5（错答回流与用例维护） | 线上错答怎么变成下一条回归用例 |

> **两条依赖前置关系**（跳读会踩坑，故保留）：
> ① 不要跳过 `01` 直接看 `03`——工具集是 `AIAgent` 的 `enabled_toolsets`/`disabled_toolsets` 参数的输入，构造语义在 `01` §3。
> ② 不要跳过 `19` 直接写业务工具——没有六要素盘点，工具面与上下文会各自长成对方不认识的形状，`20` 的用例也无从派生。

---

## 4. 事实基线（唯一真相源，0.19.0 内省核实）

```
包名 / 版本 : hermes-agent == 0.19.0
导入语句     : from run_agent import AIAgent          # 顶层模块，非 hermes.* 子包
CLI 包      : hermes_cli  ( __version__ = "0.19.0" )  # 含 146 个顶层模块（含嵌套共 205，均不含包根 __init__.py，见 10）
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

**自进化学习循环（Hermes 根性，机制基线 0.19.0）**：
- **后台 self-improvement review**：每轮后可能触发，fork 独立 `AIAgent`（独立 prompt cache、不影响主会话），决定写入记忆或创建/改进技能。
- **记忆**：`$HERMES_HOME/memories/`（`MEMORY.md`/`USER.md`），会话开始作为**冻结快照**注入 system prompt（无 `read` 动作，agent 天然看到）；agent 用 `memory` 工具自管理。
- **技能沉淀**：agent 用 `skill_manage`（`create`/`patch`）把成功流程固化为 `$HERMES_HOME/skills/` 技能，按需加载。
- **consent-aware（用户知情同意）**：默认通知（`display.memory_notifications`）；可开写审批门（`memory.write_approval` / `skills.write_approval`），后台写入暂存 `/memory pending` → approve/reject。
- **不可变核心**：托管镜像 `/opt/hermes` 核心不可变，自进化只作用于 `/opt/data` 数据层；核心改动走 PR 发版。
- **并发约束**：勿让两进程指向同一数据目录（记忆/会话不支持并发写）。
- **归属**：`memory`/`skill_manage` 工具 API → `01-library-api` / `13-agent-modules`；能力行为语义 → `08-capability-integration`；GUI 落地（审批闭环 / 记忆可视化）→ `02-integration-core` 与 example01。

> 自进化有真实代价（token、技能目录污染、写审批摩擦），集成时需权衡；`memory_notifications`/`write_approval` 等开关见 `01`/`08`。

**系统架构基线（顶层地图，0.19.0）**：
- **分层主干**：Entry Points（CLI / Gateway / ACP / Batch / API Server / Python Library）→ `AIAgent`（`run_agent.py`）统一内核（Prompt Builder / Provider Resolution / Tool Dispatch）→ Session Storage（SQLite+FTS5）+ Tool Backends（Terminal / Browser / Web / MCP / File / Vision…）。**一条类服务所有入口**，平台差异在入口点不在 agent（platform-agnostic core）。
- **核心循环**（`run_conversation`）：构建系统提示 → 解析 provider → API 调用（chat_completions / codex_responses / anthropic_messages 三模式）→ 有 tool_calls 则分发改派回环 → 收敛 → 响应 → 落盘 SessionDB。
- **工具发现链**：`tools/registry.py`（无依赖）← `tools/*.py`（import 时 `registry.register()`）← `model_tools.py` ← `run_agent`/`cli`/`batch_runner`。**自注册，勿手写清单**；PyInstaller 打包别漏触发点（`06`）。
- **设计原则**：Prompt stability / Observable execution（工具调用经回调可见 = 桌面事件流基础，`01` §4）/ Interruptible / Platform-agnostic core / Loose coupling（注册表 + check_fn 门控）/ Profile isolation（独立 `HERMES_HOME`）。
- **归属**：各包模块清单 → `10`/`12`/`13`/`14`/`16`；能力语义 → `08`；Library 全貌收口 → `14` §3；本文只给系统级分层地图，不重复模块清单。

## 5. 单真相源映射（避免重复与漂移）

| 事实 | 唯一归属文件 | 备注 |
| --- | --- | --- |
| 装包名 / 版本 / 导入路径 | `01-library-api.md` §1 | 改版本先改这里 |
| `AIAgent` 构造参数与回调签名 | `01-library-api.md` §3 | 以源码 `__init__` 为准；**默认值以此处为唯一出处（实测值在 §3.2 全量表）**，SKILL.md 第 ③ 步只保留"必须显式设"这条决策与指针，其余文档一律引用不重述 |
| 「官方文档说 A、源码是 B」的冲突结论与处置 | `docs/troubleshooting.md`（逐条编号，首条 §11 = `max_iterations` 500 vs 90） | 冲突**结论**归本文、实测**值**归 `01`；SKILL.md 〔入场检查〕规定这是唯一沉淀位 |
| 两种入场（接进已有系统 / 从零开发）的盘点顺序 | `19-business-domain-model.md` §2.1 | 建模动作的性质差异归此；SKILL.md 第 ① 步只保留"读出来 vs 定出来"一句结论 |
| SSE 事件词汇（delta/reasoning/action/…） | `01-library-api.md` §4 + `02-integration-core.md` §3 | 旗舰示例 `examples/01-hermes-desktop/Agent系统/agent_runtime/` 复核 |
| 57 工具集清单与逐项说明 | `03-capabilities-and-toolsets.md` | 单一全量表，禁止别处再列 |
| 减法原则（enabled=None=全量 / disabled 做减法） | `01-library-api.md` §3 + `03-*` §1 | 进程内直跑常态 `disabled=["terminal"]` |
| `HERMES_HOME` 与环境变量 | `05-install-and-env.md` | `hermes_constants` 是唯一 API |
| PyInstaller hidden-import 清单 | `06-packaging.md` §2 | 随依赖增删更新 |
| 服务侧部署：守护、日志落点、滚动升级与回滚、多客户端并发 | `06-packaging.md` §9 | 路线②③④ 的交付动作唯一落点；端点/配置/鉴权事实仍归 `15`/`16` |
| 上下文分层与每轮 token 预算（谁维护、占多少） | `19-business-domain-model.md` §4 | 五档记账表（档 × 载体 × 注入通道 × 维护责任 × token 预算）；"系统提示词/SKILLS/WIKI/工具/代码"五个名字是本表两列的取值、禁止另立第二张分层表（声明归 `19` §4.2 末）；§4.1 另有「未核对材料暂存位」，它**不是第三层上下文**（不进通道、不占预算、Agent 读不到）；§4.3 段式含一段项目级前言，其预算归稳定知识档；SKILL.md 第 ①⑤ 步只保留"禁止共用一个预算"的决策与指针 |
| 按场景装配能力：确定性 API vs 概率采样 | `11-library-support.md` §8（解析/自定义工具集，即"配置行 → 面"的落地函数）· §9（禁止 `toolset_distributions` 用于生产分派，实测理由归此） | 「场景 → 面」的表形状归 `19` §7 第 1 张，「入口 → 配置行」归第 6 张 |
| 「几个入口、几套配置」的形态判据与三条代价（统一运行时 + 入口差异配置化） | `SKILL.md` 第 ② 步（判据与前移后的位置）· 表形状 `19` §7 第 6 张 | 逐入口 diff 与配置表单点实现检查归 `19` §6 第 5–6 条；`21` §4 只留"先合后拆"的工具收敛义，禁止在那里复述 |
| 调用链上的身份绑定、凭证生命周期与文件作用域 | `15-api-server.md` §4ter | 逐站实测（key → 会话头 → profile → ContextVar → 工具 kwargs 断在哪）；路线① 的边界登记在 `02` §8，`current_scope()` 做法归 `19` §5 |
| 反模式红线 | `07-quality-gates.md` §1 | 任何新增能力先过此章 |
| 文档内部的组织与行文规则（步内四拍、白话标准、并列的合法边界） | `SKILL.md`「这条主线怎么读」 | 唯一规范出处；`19` 全文是按此重排的样板，各 reference 的正文组织冲突时以该节为准 |
| 能力行为语义（Goals/MOA/…） | `08-capability-integration.md` | 单一行为基线，禁止别处再写能力语义 |
| `hermes_cli` 模块清单（用途与代表 API） | `10-hermes-cli.md` | 全 146 个顶层模块不遗漏、不重复、不交叉 |
| llms-full 检索地图 | `00-index.md` §1（本文） | 完整版自 `10-hermes-cli.md` §5 移入，唯一权威检索索引 |
| 系统架构基线（顶层地图） | `00-index.md` §4（本文） | 分层主干 / 核心数据流 / 设计原则 / 工具发现链；模块清单另见 `10`/`12`/`13`/`14`/`16` |
| `batch_runner` + 支撑模块 API | `11-library-support.md` | `HERMES_HOME`/会话落盘/自定义工具集/原子写单一参考 |
| `tools` 包全量子模块 | `12-tools-modules.md` | 113 个嵌套子模块不遗漏、不重复、不交叉 |
| `agent` 包全量子模块 | `13-agent-modules.md` | 155 个嵌套子模块不遗漏、不重复、不交叉 |
| 基础设施模块（网关/CLI/cron/…） | `14-library-infra.md` | 进程外设施单一说明，避免误 import |
| API Server 路线落地 | `15-api-server.md` | API Server 形态单一真相源（配置/端点/接入/进程内自建），避免与 02/04/10 重复 |
| `gateway` 包全量子模块 | `16-gateway-package.md` | 77 个嵌套子模块不遗漏、不重复、不交叉 |
| 非侵入扩展面（skill/mcp/plugin/memory） | `02-integration-core.md` §9–§14 | 业务对接 Hermes 的唯一扩展面参考（已并入双向整合总章）；改核为最后手段 |
| A2A / Delegation / Tool Search 能力语义 | `hermes-llms-full.txt` 对应章节（本文 §1.1 索引） | 本技能仅索引不重复转录；后续如新增专题 reference，先更新本表归属 |
| 业务六要素 → 工具面/上下文映射、三层面与权限 diff | `19-business-domain-model.md` | 建模层单一真相源；工具清单本体仍归 `03`，装配机制仍归 `02` |
| 「这一格归模型还是归代码」的三问判据（与三层风险面正交的第二根轴） | `19-business-domain-model.md` §3 第 5 步 | 判给代码 ⇒ 禁止注册成工具（裁剪依据同此）；测试轨按它选 ⇒ `20` §4.5；SKILL.md 第 ⑤ 步动作 3 只带三问与结论 |
| `execute_code` / PTC 的实测口径（Windows 可用性、7 工具白名单、审批一次批、上限可配） | `03-capabilities-and-toolsets.md` §3.4 | 两处 docstring 与实现相反的踩坑记在此；轮次与 token 的账归 `21` §6，红线归 `07` R13 |
| 输出契约（schema 设计规则、校验顺序）与 Golden 集（来源/规模/维护/归因） | `20-output-contract-and-golden-set.md` | 用例的**方法与资产规范**归此；`complete_structured` 的 API 签名仍归 `01` §3.4bis / `02` §12 |
| 可观测字段、配额与成本治理、编排机制选择、四类降级契约、发布基线与运营回路 | `21-operations-and-degradation.md` | 运营视角单一真相源；模块签名仍归 `13` §2.3，能力语义归 `08` |
| 5 条调用路线的判据/拓扑/代价对照 | `02-integration-core.md` §2.1–§2.5 | 路线选择单一真相源；各路线**落地细节**仍分别在 `01`/`10`/`15`/`16` |

---

## 6. 交叉引用与行文约定

- 本目录文件以 `NN-` 两位编号开头；跨文件引用写作 `` `03-capabilities-and-toolsets.md` §2 ``
  （反引号包裹文件名 + `§节号`）。
- 锚点用 GitHub 风格：`## 3. 工具集系统` → 链接 `#3-工具集系统`。
- 代码符号用反引号：`AIAgent`、`TOOLSETS`、`get_hermes_home()`。
- 路线红线统一用「禁止」字样标记（见 `07-quality-gates.md`）。
- **正文按流程写，不按清单写**（规范全文见 `SKILL.md`「这条主线怎么读」）：每一节要能读出一句"先做什么、再做什么、
  这一步的产出物喂给谁"，节与节之间是数据依赖而不是并列。顺序若真的不重要（如三类问题的三个权威源），
  就在正文里明说"这是一组任一命中的判据/一个 N 选一的岔路"，禁止让读者自己猜。
- **表格只用来装"产出物本身"**（契约表、预算账本、逐站实测结果）；用来装"该按什么顺序做"的表要改写成编号动作。
  反模式（禁止句）挂在它所属的那一站/那一步旁边，禁止攒到文末清单。
- **白话标准**：先说这件事在业务上是什么，再说它在代码上是什么；术语首次出现跟一句白话解释；
  精确参数名、行号、实测数值只放在本目录，SKILL.md 正文留指针。

---

## 7. 与内置参考实现的关系

`examples/01-hermes-desktop` 是旗舰参考实现，**已是三系统完整形态**（见其 `README.md` 与 `18` 号文档）：
`Agent系统/`（纯净底座，**git submodule**，克隆后需 `git submodule update --init`；进程内 `AIAgent` + FastHTML + pywebview，
其 `agent_runtime` 包（`Agent系统/agent_runtime/`）的构造与 SSE 分发已作为本文档「实战写法」的核验样本，见 01 §3、§4）、
`业务系统/`（纯业务样例：`build_app()` / `mount_rd_routes()` / `get_business_snapshot()`，不 import Agent）、
`连接系统/`（唯一装配点 `fuse_business_into_agent()`，含 `BUSINESS_CONTEXT_HOOK` 注入与降级回退）。
`examples/02-hermes-pywebview-multiagent` 是多智能体 pywebview 壳示例。
`examples/03-nesquena-hermes-webui` 是 Hermes WebUI 本地适配（源自开源 nesquena/hermes-webui）：三栏浏览器/手机 Web 界面（CLI 1:1 对等），经 `api/agent_runtime.py` 以 `from run_agent import AIAgent` 驱动核心，Windows 原生 `start-webui.bat` / `start.ps1` 启动（端口 8787）。
三者代码本身可读，本文档只抽取**与技能通用方法相关**的结论，不绑定任何具体业务领域。
