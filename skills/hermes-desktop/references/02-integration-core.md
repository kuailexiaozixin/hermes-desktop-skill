# 02 · 业务系统与 Agent 双向整合（界面接入 + 业务赋能，一个整体）

> 本文讲「业务系统如何与 Agent 智能体整合为一个整体」。
>
> 整合是**双向的、不可分割的两条线**，围绕同一个 `AIAgent` 汇合（进程内直跑时同进程，跨进程路线时由服务承载）：
> - **把 Agent 接进界面（上篇）**：让桌面 / Web 界面能对话、能流式、能把内核事件渲染出来。
> - **让 Agent 懂业务（下篇）**：把你的业务工具、数据、流程、记忆接进 Hermes，让 Agent 能真正办你的业务。
>
> 两者不是「两块」，而是「一面」——没有界面的 Agent 用不起来，不懂业务的 Agent 只是空壳。
> 本技能一律把它们当作**一个整体**来设计：扩展面优先、改核为最后手段。
>
> **与其它参考的分工（避免重复）**：`03` = 工具集（能力→工具）单一全量参考；`10` = `hermes_cli` 147 模块清单；
> `01` = Library API；`04` = 渲染框架桥接；`08` = 能力层语义；`07` = 红线；`12`/`13` = 模块枚举。
> 本文是「业务 ↔ Agent」整合的**唯一总入口**，不与上述任何一篇重复。

---

## 1. 双向整合总览（一个整体）

```
                业务系统  ◄──────────┐       ┌──────────►  桌面 / Web 界面
                    │               │       │                  │
               业务工具 / 数据 / 流程 / 记忆   │   对话窗口 / 流式渲染 / SSE   │
                    │               │       │                  │
                    └──────┬────────┴───────┴────────┬──────┘
                           │                         │
                           ▼                         ▼
                    ┌──────────────────────────────────────┐
                    │        AIAgent（run_agent）               │  ← 两条线在此汇合
                    │   驱动内核：既给界面流式，又调业务工具      │
                    └──────────────────────────────────────┘
```

- **上篇（界面接入）**回答：怎么把 `AIAgent` 接进你的 GUI、做流式 / SSE。
- **下篇（业务赋能）**回答：怎么给 `AIAgent` 喂业务工具 / 记忆 / 流程，让它「懂你业务」。
- 两条线都围绕同一个 `AIAgent` 实例；凡是扩展面能覆盖的，不碰 `hermes-agent` 源码。

---

## 2. 把 Agent 接进界面：进程内集成路径

```
路径 A:  GUI ──直接──> AIAgent（run_agent）        ← 进程内直跑：GUI 与内核同进程
路径 B:  GUI ──import──> hermes_cli.<子模块>        ← 进程内复用 CLI 逻辑，不 spawn 子进程
路径 C（UI）:  GUI(FastHTML/pywebview) ──SSE──> AIAgent   ← 进程内 Web/原生 UI 桥接，见 §3
路径 D:  GUI ──HTTP/stdio──> Hermes 网关 / spawn CLI / API Server（`/v1`）  ← 跨进程路线，与进程内直跑平等可选
```

> **路线说明（5 条平等可选）**：调用 Python Library 有 5 条**平等可选**技术路线——进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`——**无先后顺序**，按需选择其一。进程内直跑把 `AIAgent` 跑在你的 EXE 同一进程；其余 4 条（网关 / CLI / API Server / `/v1`）由对应服务或子进程承担，代价是新增「跨进程状态同步 + HTTP 桥接」。官方 Desktop 与走 Hermes 网关的 Electron 端即属网关形态。各跨进程路线的完整落地见 `10`/`15`/`16`。
>
> **路径 D（跨进程路线）何时选用 / 怎么选 / 代价多大**：
> - **何时**：①需要接消息平台（Telegram/Slack/QQ…）或 cron 多投递目标；②需要把 Agent 暴露成独立 OpenAI 兼容服务，供 Open WebUI / 其它语言 / curl / CI 调用；③需要多客户端 / 远程 / 多用户 profile 隔离；④需要走标准 `/v1`（`/v1/chat/completions`、`/v1/responses`、`/v1/runs` 等）。纯桌面单机 GUI 且无需对外被调时，跨进程路线并非必需，但**是否选用由你按需求决定，不强制**。
> - **怎么选**：三选一（由轻到重）——①连已运行的 Hermes 网关（`127.0.0.1:8642` 的 `/v1`）；②spawn `hermes` CLI 子进程走 stdio/HTTP；③开 `API_SERVER_ENABLED=true` + `hermes gateway` 起独立 API Server（最全，含 runs/jobs/sessions 管理端点）。
> - **代价**：新增**跨进程状态同步 + HTTP 桥接**（进程内直跑无此开销）；单进程/单 EXE 交付丧失，需常驻服务 + 端口 + Bearer 认证 + CORS；API Server 本质是 agent runtime，工具在服务端执行，密钥泄露=终端命令执行风险。
> - **完整落地**：API Server 路线配置/端点/接入/进程内自建/检查清单见 `15-api-server.md`；spawn CLI 见 `10`；Hermes 网关见 `16`。

---

## 3. 路径 C：Web/原生 UI 的 SSE 桥接（worker + queue）

旗舰示例 `agent_runtime.py` 的已核实模式：把 `AIAgent.run_conversation(stream_callback=...)`
放进后台线程，经 `queue.Queue` 把内核事件转成 SSE 流推给前端。

```
前端 ──HTTP POST /chat──> FastAPI/路由
                           │
                           ├─ worker 线程: agent.run_conversation(msg, stream_callback=push_delta)
                           │       push_delta(text) ──> q.put(("delta", text))
                           │       (其余事件同样 q.put)
                           │
                           └─ 生成器: while True: item=q.get()
                                   ("delta",t)      -> _delta_chunk(t)
                                   ("reasoning",t)  -> SSE {type:reasoning,text}
                                   ("action",tool,p)-> SSE {type:action,tool,preview}
                                   ("action_result",tool,p,r) -> SSE {type:action_result,...}
                                   ("tool_progress",name,a,k) -> SSE {type:tool_progress,...}
                                   ("final",text,msgs,files)  -> SSE {type:done,final,html,messages,changed_files}
                                   ("error",msg)    -> SSE {error:{message}}  （错误路径不再发 done）
```

**事件词汇唯一来源**：`01` §4.1 表（delta/reasoning/action/action_result/tool_progress/done/error）。
**无 delegation 事件**——委派卡片未实测前静默不显示（R6，见 `07`）。
若需在 UI 呈现子代理委派卡：先实测 `event_callback` 在 `delegate_task` 时会透传哪些事件（`01` §4.1），
再据实测结果自行订阅并渲染；在未实测前，**不要宣称已支持委派卡片**（`07` R6）。

前端渲染范式（可借鉴 `hermes-webui` 的「工具卡片 + 推理折叠 + 代码复制 + Mermaid」，见 `04` §1）：
把 `action`/`action_result` 渲染为工具卡片，`reasoning` 渲染为折叠思考区，`done.html` 做
Mermaid/代码复制后处理。

---

## 4. 复用 `hermes_cli` 逻辑（不 spawn 子进程）

`hermes_cli` 是统一 CLI 包（含 **147 个顶层模块**，含嵌套共 205），子命令
`chat` / `gateway` / `setup` / `status` / `cron` / `mcp` / `bundles` / `project` / `kanban` /
`backup` / `doctor` / `plugins` / `portal` 等。进程内路线**不调用 `hermes` 可执行**，但若需要
某条 CLI 的纯逻辑（如配置读写、MOA 预设解析、定时任务底层、能力状态内核），**直接 import 对应
子模块**即可，无需子进程。

> ⚠️ **详细的分组清单、逐模块用途与代表 API、可复用模块最小代码的完整说明，全部移入 [`10-hermes-cli.md`](10-hermes-cli.md)**（顶层 147 模块，不交叉不重合）。
> 本节只保留路线红线，具体复用点对 10 查阅，避免两文重复。

**复用建议（与 `07` §1 R1/R3 一致）**：`hermes_cli` 多数「起服务 / 监听端口 / TTY 交互 / 网络认证」类模块依赖完整 CLI 运行时
（TTY、凭据流、端口、后台服务）。**只 import 你确认无副作用的纯函数子模块**（见 10 §3）；
涉及交互式输入/网络认证/起服务的模块**不要在 GUI 初始化时盲目 import**。

最常用复用点速记（完整版见 `10` §3）：

| 复用目标 | 模块（`hermes_cli.*`） |
| --- | --- |
| 配置读写 | `hermes_cli.config`（`load_config`/`save_config`） |
| 工具集开关持久化 | `hermes_cli.tools_config` |
| MOA 预设解析 | `hermes_cli.moa_config`（`resolve_moa_preset`/`set_active_moa_preset`） |
| 备份快照 | `hermes_cli.backup`（`create_quick_snapshot`） |
| Profile 管理 | `hermes_cli.profiles` |
| 能力内核（Goals/Projects/Bundles/Security） | `hermes_cli.goals` / `projects_db` / `bundles` / `security_audit` |
| 供应商/模型查询 | `hermes_cli.providers` / `provider_catalog` / `models` |

---

## 5. 能力 → 模块地图（实现位置，源码内省核实）

`TOOLSETS` 每项工具映射到 `tools/` 或 `agent/` 的具体实现模块。下表覆盖 33 个 capability
工具集（24 个 `hermes-*` 集成见 §5.5 注）。改某能力前先定位其模块。

| 工具集 | 实现模块（site-packages 内） |
| --- | --- |
| `web` / `search` | `tools.web_tools` |
| `x_search` | `tools.x_search_tool` |
| `vision` | `tools.vision_tools` |
| `video` | `tools.vision_tools`（`video_analyze`） |
| `image_gen` | `tools.image_generation_tool` |
| `video_gen` | `tools.video_generation_tool` + `tools.xai_video_tools` |
| `computer_use` | `tools.computer_use_tool` + `tools.computer_use/`（cua-driver） |
| `terminal` | `tools.terminal_tool` + `tools.read_terminal_tool` + `tools.close_terminal_tool` + `tools.process_registry` |
| `skills` | `tools.skills_tool` + `tools.skill_manager_tool` + `tools.skills_guard` + `tools.skills_hub` + `tools.skills_sync` |
| `browser` | `tools.browser_tool` + `tools.browser_cdp_tool` + `tools.browser_dialog_tool` + `tools.browser_camofox` + `tools.browser_supervisor` |
| `cronjob` | `tools.cronjob_tools` |
| `file` | `tools.file_tools` + `tools.file_operations` + `tools.file_state` + `tools.patch_parser` |
| `tts` | `tools.tts_tool` + `tools.neutts_synth` |
| `todo` | `tools.todo_tool` |
| `memory` | `tools.memory_tool` + `agent.memory_manager` + `agent.memory_provider` |
| `context_engine` | `agent.context_engine` |
| `session_search` | `tools.session_search_tool` |
| `project` | `tools.project_tools` |
| `clarify` | `tools.clarify_tool` + `tools.clarify_gateway` |
| `code_execution` | `tools.code_execution_tool` |
| `delegation` | `tools.delegate_tool` + `tools.async_delegation` |
| `homeassistant` | `tools.homeassistant_tool` |
| `kanban` | `tools.kanban_tools` |
| `discord` / `discord_admin` | `tools.discord_tool` |
| `yuanbao` | `tools.yuanbao_tools` |
| `feishu_doc` | `tools.feishu_doc_tool` |
| `feishu_drive` | `tools.feishu_drive_tool` |
| `spotify` | 集成式（bundled）— 不在 `tools/` 顶层模块列表，按需查 `tools/` |
| `debugging` | 聚合：`terminal`+`process` + 包含 `web`+`file` |
| `safe` | 聚合：包含 `web`+`vision`+`image_gen`（无 terminal） |
| `coding` | 聚合 32 工具（files/terminal/search/web/vision/skills/browser/todo/delegate…） |

> 注：`hermes-acp`(29) / `hermes-api-server`(35) 是**编辑器 / OpenAI 兼容 HTTP 的聚合型 `hermes-*` 集成**
> （属 24 个 `hermes-*` 而非 33 个 capability），工具组为 `coding` 变体，见 §5.5 与 `03` §4.1。

### §5.5 关于 24 个 `hermes-*` 集成

这 24 项（`hermes-telegram` … `hermes-gateway`）是**消息平台绑定**，实现位于
`gateway/platforms/*`（如 `gateway/platforms/qqbot`）与 `hermes_cli/*_cli` / `*_auth`。
它们在**网关路线**下才激活（由网关把平台消息喂给 Agent）。

> 进程内形态下通常不启用这 24 项（无网关、无 `127.0.0.1:8642`）；若放开为网关形态，则可按网关路线激活。
> 若桌面应用确实需要接某个平台，应改为「应用自己收平台消息 → 调 `AIAgent.run_conversation`」
> 的进程内桥接，而不是拉起 `hermes-*` 集成。其中 `hermes-gateway` 是「所有平台工具集的
> 并集」（`includes` 列出 19 个平台），`hermes-cli` / `hermes-cron` 是「全量默认工具集」（49 工具，
> 含 terminal——进程内桌面若复用需自行禁用 terminal，见 R5）。

---

## 6. 进程内路线的最小骨架

```python
# launcher / app 启动时
import queue, threading
from run_agent import AIAgent
# （可选）注册应用自有业务工具：register_pure_python_tools()

def stream(user_msg, on_event):
    q = queue.Queue(); SENTINEL = object()
    def worker():
        try:
            AIAgent(
                provider=..., model=..., disabled_toolsets=["terminal"], quiet_mode=True,
                event_callback=lambda name, payload: q.put(("event", name, payload)),
            ).run_conversation(user_msg, stream_callback=lambda t: q.put(("delta", t)))
        finally:
            q.put(SENTINEL)
    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = q.get()
        if item is SENTINEL: break
        on_event(item)          # 转 SSE / 更新 GUI
```

> 完整可运行骨架见 `examples/01-hermes-desktop/agent_runtime.py`（已作为本文档实战样本核验）。
>
> **工程要点（骨架之外必须补齐）**：
> ① `provider` / `model` 是占位符，应从配置解析后传入（构造范式见 `01` §3，勿硬编码）；
> ② `disabled_toolsets` 按业务最小面减法收敛（`01` §3.2），危险工具（terminal 等）需配合 §7 审批护栏；
> ③ 需支持超时/取消/并发：给 worker 线程挂 `threading.Event` 取消标志，`run_conversation` 侧按需中断；
> ④ 异常与清理：worker 内用 try/except 捕获，`finally` 发 SENTINEL 确保 UI 线程不被阻塞；
> ⑤ 单进程并发多用独立 `AIAgent` 实例 + 各自 queue（多 Agent 布局见 `04` §15）。

---

## 7. 工具化与治理（审批 / 办公）

桌面应用要把"宿主能力 + 业务动作 + 办公文档操作"安全地交给 Agent，必须自建工具层与护栏。
进程内路线**没有网关的审批分类器**（`approvals.mode` 无触发源），护栏须由应用层实现（见 `03` §2）。

### 7.1 业务工具注册（三层范式，已核实）

1. **纯 Python 工具集注入**：用 `register_pure_python_tools()` 把应用层函数登记进运行时
   （机制见 `01` §7）——这是"宿主专属动作"（文件预览、宿主命令、业务 API）的接入点。
2. **复用内核工具集**：通过 `enabled_toolsets` / `disabled_toolsets` 开关内核 57 工具集
   （减法原则见 `01` §3.2、`03` §1）——无需改造代码，直接开关。
3. **系统功能包成工具（危险操作包裹）**：把"文件写 / 命令执行 / 路径操作"等系统功能包成
   受控工具，复用内核护栏模块：`agent.tool_guardrails`（`ToolGuardrailDecision` /
   `ToolCallGuardrailController` / `MUTATING_TOOL_NAMES`）、`tools.approval`
   （`DANGEROUS_PATTERNS` / `HARDLINE_PATTERNS` / `approve_permanent` / `approve_session`）、
   `tools.write_approval`（`GateDecision`）、`tools.slash_confirm`（斜杠二次确认）。内核在
   `agent/agent_init.py` 与 `agent/system_prompt.py` 中以 `_tool_use_enforcement`
   落实"工具使用强制约束"，自建工具应复用同一强制语义，不要另起一套。

> 这三类注册点，正是下篇「让 Agent 懂业务」里进程内自定义 toolset 那一格（见 §14）的落地位置。

### 7.2 审批闭环（进程内必须自建）

凡暴露"写类 / 执行类"能力，必须在自建工具层加审批，而非依赖网关（模块以 `03` §2 为准）：

| 风险面 | 内核护栏模块（已核实存在） | 用途 |
| --- | --- | --- |
| 危险命令 | `tools.approval`（`DANGEROUS_PATTERNS` / `HARDLINE_PATTERNS`） | 命令/脚本危险模式拦截 |
| 文件写 | `tools.write_approval`（`GateDecision`） | 写操作门禁 |
| 路径越权 | `tools.path_security`（`validate_within_dir` / `has_traversal_component`） | 防目录穿越 |
| 隐藏威胁 | `tools.threat_patterns`（`first_threat_message` / `INVISIBLE_CHARS`） | 不可见字符/注入扫描 |
| 工具调用 | `agent.tool_guardrails`（`ToolGuardrailDecision`） + `agent.tool_executor` | 调用前决策与预算 |
| 斜杠命令 | `tools.slash_confirm` | 二次确认 |

### 7.3 办公 / 表格文档的受控工具面

⚠️ **事实**：`hermes-agent` **无独立的 `tools.office` / `tools.excel_tools` 模块**
（已核实 `ModuleNotFoundError`；版本基线见 §16）。办公 / 表格 / Word / PDF 操作经 `file` 工具集
（`tools.file_tools`）+ `feishu_doc` / `feishu_drive` 工具集完成。因此"办公文档治理" =
把上述文件写操作套用 §7.2 同一套受控工具面（审批 + `path_security` + `threat_patterns`），
**不要假设存在独立的 office 工具集**。

> 反模式：❌ 不要照抄网关的 `approvals.mode: smart|manual|off` 配置——进程内形态无触发源；
> ❌ 不要假设有 `tools.office` 模块；❌ 不要跳过 `path_security` 直接落盘用户文档。

---

## 8. 进程内路线边界清单（能做什么 / 不能做什么）

> 供快速判断「某项能力在进程内形态下能不能做」。条目均经源码/文档核实，
> 与 `03` §1 红线、`07` 反模式对齐。**原则上：进程内能做则自建，不能做则要么自建、要么放开为网关形态**。

### 8.1 进程内可以做的（直接可用）

| 能力 | 方式 | 依据 |
| --- | --- | --- |
| 单轮/多轮对话 + 流式 | `AIAgent.run_conversation(stream_callback=...)` | `01` §3/§4 |
| 全部内核工具集 | `enabled_toolsets` / `disabled_toolsets` 开关（减法收敛） | `01` §3.2、`03` |
| 注册自有业务工具 | `register_pure_python_tools()` | `01` §7、§7.1 |
| 复用 `hermes_cli` 纯逻辑模块 | `import hermes_cli.<x>`（配置读写/MOA/备份/profile 等） | §4、`10` |
| 会话落盘 / 记忆 / 技能 | 内核 `session_search` / `memory` / `skills` 工具集 | `03` |
| SSE 桥接多框架 UI | worker+queue（FastHTML/Tkinter/pywebview/Qt…） | §3、`04` |
| 审批 / 安全护栏 | 自建工具层（`approval`/`write_approval`/`path_security`/`threat_patterns`/`tool_guardrails`） | §7.2 |
| 定时任务（单机） | 复用 `tools.cronjob_tools` 底层，自建调度循环 | `10` §2.10 |

### 8.2 进程内不能做 / 受限（需网关或自建）

| 能力 | 为什么 | 出路 |
| --- | --- | --- |
| 消息平台接入（Telegram/Slack/QQ/Discord…） | 平台消息由网关喂给 Agent（`gateway/platforms/*`） | ①应用自收消息→`run_conversation` 进程内桥；②放开为网关形态 |
| cron 多投递目标 / 后台异步投递 | outbound 投递走网关 notifier，进程内无持久通道 | 自建投递（邮件/文件/自定目标） |
| SSH / Docker / Modal 远程 terminal 后端 | 远程后端是网关/CLI 能力 | 自建远程执行层，或放开 |
| 网关审批分类器（`approvals.mode: smart/manual/off`） | 进程内无触发源 | 应用层自建审批（§7.2） |
| 真实账单成本（`get_credits_*`） | 进程内为**估算**（无网关计费） | 接受估算值，勿宣称真实 |
| Webhook / 多平台 IM adapter / 网关专属模块 | 属网关 `hermes-*` 24 项集成 | 进程内形态不启用（§5.5） |
| 对外 OpenAI 兼容 `/v1` 服务、多客户端/远程/多用户 | 属 API Server 形态 | 放开路径 D（§2）或进程内自建 `/v1` 薄层 |
| 子代理委派卡（delegation 事件） | `event_callback` 透传委派未实测 | 先实测再宣称（`07` R6、§3） |

> **一句话判据**：凡是「需要常驻服务 / 平台消息入口 / 远程后端 / 外部多客户端」的，进程内形态默认做不了；
> 属单机 GUI、进程内直调、自建护栏范围的，进程内都能做。

---

## 9. 让 Agent 懂业务：非侵入扩展面优先（总原则 + 决策）

界面接好了，下一步是让 Agent 真正「懂你的业务」——能调用你的业务工具、读你的业务数据、走你的业务流程。
Hermes 预留了 **4 类非侵入扩展面**，对接业务时优先用它们，**而不是改 `hermes-agent` 包源码**。

1. **Skill** —— `SKILL.md` + 脚本，挂进 `$HERMES_HOME/skills/`（提示词 / 可复用流程）
2. **MCP server** —— 用 FastMCP 等写一个独立 MCP server，经 `hermes mcp add` 接进（外部系统 / 跨语言工具）
3. **Plugin** —— `$HERMES_HOME/plugins/` 里的插件，用 `ctx.register_tool` / `ctx.llm` 等（新工具 / 钩子 / 替换内置 backend）
4. **Memory backend** —— 换长期记忆后端，走配置 / `MemoryProvider` 注册（不写核）

**为什么优先非侵入**：改 `hermes-agent` 源码 = 升级即丢失、无法 `pip` 同步、审计与回滚困难。扩展面是 Hermes 官方设计的接入口，随版本演进被兼容保证。本技能一贯铁律（SKILL §3.5）：进程内形态无安全边界，起步 `disabled_toolsets=["terminal"]`，业务能力用**自建工具面**补全——这里的"自建工具面"正是上述扩展面（外加 §7 的进程内自定义 toolset）。

### 决策速查

| 你的需求 | 优先扩展面 | 说明 |
| --- | --- | --- |
| 固化一段可复用业务流程 / 领域知识 / 提示词 | **① Skill** | 不注册新 tool，只增强系统提示与可用脚本 |
| 接一个外部系统 / 业务 API（可能跨语言） | **② MCP server** | 独立进程，零 Hermes 源码 |
| 注册**新工具**给 Agent 调用 / 生命周期钩子 / 替换内置 backend / 用宿主 LLM | **③ Plugin** | `$HERMES_HOME/plugins/` + `ctx.*` |
| 换长期记忆后端（个性化 / 跨会话建模） | **④ Memory backend** | 配置切换或自写 `MemoryProvider` |
| 业务与 GUI 紧耦合、同进程最省事 | 进程内自定义 toolset（`01`/`03`） | 见 §14 对比 |

---

## 10. 扩展面① Skill：`SKILL.md` + 脚本挂 `$HERMES_HOME/skills/`

**路径（核实 `skills_hub.py:181,248`）**：`$HERMES_HOME/skills/<name>/SKILL.md` 是单一真相源（single source of truth）。

**结构**：
```
$HERMES_HOME/skills/<name>/
├── SKILL.md              # YAML frontmatter(name, description) + 正文指令
├── references/           # 可选：被 SKILL.md 引用的支撑文档
├── scripts/              # 可选：Python / shell 脚本
├── templates/            # 可选
└── assets/               # 可选
```

**安装（两种方式，均无需改核）**：
- 从 Hub / Git 安装（带安全扫描）：`hermes skills install <owner/repo/skills/name>`
- 直接放目录：把目录放进 `$HERMES_HOME/skills/` 即生效，**无需注册、无需重启**（llms-full.txt:33537 "Drop it in and it's live"）

**自动注册**：每个已装 skill 自动成为 slash 命令（名字即命令，llms-full.txt:2430）。

**适用**：把一段可复用业务流程、领域知识、提示词固化下来，让 Agent 在该类任务上自动加载。

**限制（重要）**：**Skill 本身不注册新的 tool**——它增强系统提示词与可用脚本，让 Agent"更懂怎么做"，但不新增可被调用的函数。需要 Agent 调用你**新写的业务函数**，用扩展面②或③。

---

## 11. 扩展面② MCP server：FastMCP 经 `hermes mcp add` 接入（零 Hermes 源码）

**命令（核实 `subcommands/mcp.py:41-73`，源码内省参数）**：
```bash
# HTTP / SSE 形态的 MCP server
hermes mcp add <name> --url https://mcp.example.com/mcp [--auth oauth|header]

# Stdio 形态的 MCP server（FastMCP / 任意 MCP SDK 写的独立进程）
hermes mcp add <name> --command npx --args -y my-biz-mcp@latest [--env KEY=VALUE ...]
hermes mcp add <name> --command python --args -m my_biz_mcp   # 也可 python

# 已知预设（仅填传输默认值，其余参数仍可被同一命令行覆盖）
hermes mcp add my-codex --preset codex
```
参数清单：`name`(配置键) · `--url` · `--command` · `--args`(REMAINDER，须放最后) · `--auth` · `--preset` · `--connect-timeout` · `--env`(KEY=VALUE)。

**含义**：把**一个外部 MCP server** 接进 Hermes；连上后这些 server 暴露的工具经内置 `mcp` toolset 提供给 Agent。

**写法**：用 [FastMCP](https://github.com/jlowin/fastmcp)（或任意 MCP SDK）写一个 stdio server 进程。Hermes 侧只多一条配置，**不改 `hermes-agent` 一行源码**。

**适用**：把任意外部系统 / 业务 API 包成工具；server 可用 Python / TypeScript / Go 等任意语言（跨语言对接）。

**工具面约束**：接好后用 `hermes mcp configure <name>`（或 `config.yaml`）做工具筛选，对外暴露只读面时选 `select` 模式，避免给 Agent 过多写权限。

---

## 12. 扩展面③ Plugin：`$HERMES_HOME/plugins/`，`tool_override` / `ctx.llm`

**路径（核实 `plugins.py:10,1348`）**：
- 用户插件：`$HERMES_HOME/plugins/<name>/`
- 项目插件：`./.hermes/plugins/<name>/`（需 `HERMES_ENABLE_PROJECT_PLUGINS=1`）
- pip 插件：暴露 `hermes_agent.plugins` entry-point group 的包

**结构**：
```
$HERMES_HOME/plugins/<name>/
├── plugin.yaml        # manifest: name, kind, description, (requires_env ...)
└── __init__.py        # def register(ctx): ...
```

**能力（`ctx` = `PluginContext`，核实 `plugins.py`）**：
| API | 作用 |
| --- | --- |
| `ctx.register_tool(name=, toolset=, schema=, handler=, override=False)` | 注册一个 Agent 可调用的工具（核实 `plugins.py:389`） |
| `ctx.register_hook(name, cb)` / `ctx.register_middleware(kind, cb)` | 生命周期钩子 / 中间件 |
| `ctx.register_memory_provider(p)`（memory 插件专用 ctx） | 注册内存后端——经 `plugins/memory/<name>/` 插件目录发现并调用（见 §13）；注意主 `PluginContext` 无此方法 |
| `ctx.llm` | 宿主托管的 LLM facade（`PluginLlm`，核实 `plugins.py:349`）——可信插件用它跑 host-owned 补全 / 结构化输出 |

**`ctx.llm` 宿主推理 —— 等价「依赖注入 + 强类型结构化输出」（原生能力，`agent/plugin_llm.py`）**：
插件用宿主已配置的模型/鉴权跑推理，**不必自带 provider key**；provider/model/agent_id/profile 覆写默认
**fail-closed**，经 `plugins.entries.<id>.llm.*` 信任键逐个放行。两类方法：

| API（`PluginLlm`） | 作用 |
| --- | --- |
| `complete(messages, *, provider=, model=, temperature=, max_tokens=, timeout=, agent_id=, profile=, purpose=)` | 宿主托管的普通 chat 补全（OpenAI 消息形状），返回 `PluginLlmCompleteResult(text/usage/audit)` |
| `complete_structured(*, instructions=, input=[...], json_schema=, json_mode=False, schema_name=, system_prompt=, provider=, model=, temperature=, max_tokens=, timeout=, agent_id=, profile=, purpose=)` | **有界强类型结构化补全**：`input` 接受文本+图像块（`PluginLlmTextInput`/`PluginLlmImageInput`），传 `json_schema`/`json_mode=True` 时响应被解析并在给 schema 时**校验**；返回 `PluginLlmStructuredResult.parsed`（校验后的 dict）+ `acomplete`/`acomplete_structured` 异步兄弟 |

```python
# 插件 register(ctx) 内：把「业务对象 → Agent 可消费的结构化结论」一条链路做通
from agent.plugin_llm import PluginLlmTextInput
order = ctx.llm.complete_structured(
    instructions="提取订单关键字段并返回 JSON。",
    input=[PluginLlmTextInput(text="#1001 88元 北京")],
    json_schema={
        "type": "object",
        "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}},
        "required": ["order_id", "amount"],
    },
).parsed   # 已通过 schema 校验
```

> **与业务系统双向整合的关系（§1/§2）**：宿主把业务上下文（当前订单/用户/会话）注入插件，用 `complete_structured` 拿到**可解析、可校验**
> 的结构化结果再喂给 Agent 工具或业务流程；schema 校验依赖可选 `jsonschema` 包（缺装时 JSON 模式仍可用）。
> 这是进程内桌面「Agent 输出落业务表单/表格」的最稳路径。

**`tool_override` 信任门（核实 `plugins.py:389,417,470`）**：`override=True` 覆盖内置工具（如 `shell_exec`/`write_file`）时，需用户在 `config.yaml` 显式设
```yaml
plugins:
  entries:
    <plugin_id>:
      allow_tool_override: true
```
否则抛 `PluginToolOverrideError`。这是防第三方插件悄悄替换特权内置工具的信任闸门——**不要图省事全局放开**。

**适用**：要注册新工具 / 钩子 / 替换内置 backend / 用宿主 LLM 做插件内推理。

---

## 13. 扩展面④ Memory backend：内置可插拔，换后端走配置 / `MemoryProvider` 注册

**抽象（核实 `agent/memory_provider.py:43`）**：`class MemoryProvider(ABC)` —— 任何记忆后端的契约（`name` / 写入 / 读取 / 同步生命周期）。

**可识别的 provider 标识（核实 `memory_provider.py:49,303`，0.19.0）**：`builtin`（默认内置）；经 `plugins/memory/` 插件目录提供的 bundled provider 有 `honcho` / `hindsight` / `mem0` / `openviking` / `byterover` / `holographic` / `retaindb` / `supermemory`（契约 docstring 与备份逻辑点名 `~/.honcho`、`~/.hindsight`、`~/.openviking` 等）。

**切换 / 新增 provider = 插件发现 + 配置驱动（核实 `plugins/memory/`，0.19.0）**：memory provider 由 **`plugins/memory/<name>/` 插件目录自动发现**（bundled 随包 + 用户 `$HERMES_HOME/plugins/<name>/`），每子目录含 `__init__.py` 实现 `MemoryProvider` 子类；**同一时刻仅一个 provider 生效**，由 config.yaml `memory.provider` 选择。交互式配置见 `hermes_cli/memory_setup.py`（自动发现 / 装依赖 / 走 schema），OAuth 见 `hermes_cli/memory_oauth.py`。

**自写后端 = 子类 `MemoryProvider`（核实 llms-full.txt:45900-46014,46854）**：
```python
# $HERMES_HOME/plugins/<name>/__init__.py
from agent.memory_provider import MemoryProvider
class MyMemoryProvider(MemoryProvider):
    @property
    def name(self) -> str: return "my-backend"
    # ... 实现读写/同步抽象方法 ...
def register(ctx):
    ctx.register_memory_provider(MyMemoryProvider())
```
—— 你写的是**插件代码**，**不改 `hermes-agent` 核心**。

**⚠️ 关于 "FTS5" 的澄清（针对源码内省）**：FTS5 是 SQLite 的全文检索引擎，随 `apsw` 在 wheel 内提供；但在已装版本的 `agent` 记忆层并未直接引用 FTS5（`agent/` 包内无 fts5 字样）。把 "FTS5" 当成一个可切换的 provider **名**不成立——它更接近内置 SQLite 存储的实现细节。换后端的正确动作是：选 `builtin` 或某个已声明的 provider（配置切换），或自写 `MemoryProvider`（插件）。若你看到文档把 FTS5 列为 provider，那大概率来自更高版本的文档，请以本机已装版本为准。

**进程内注意**：冻结态 `HERMES_HOME` 必须显式指向 `<exe>/hermes_data` 且可写（见 `05-install-and-env.md`）；provider 状态默认落 `<hermes_home>/<provider>/`。

---

## 14. 三种「给 Agent 加业务工具」方式对比（与进程内集成的关系）

你照 §2 用 `AIAgent` 进程内驱动内核；同时通过扩展面给 Agent 喂业务能力。三种"给 Agent 加业务工具"的对比：

| 方式 | 业务代码位置 | 生效范围 | 何时选 |
| --- | --- | --- | --- |
| 进程内自定义 toolset（`01`/`03` / §7.1） | **你的**应用进程内（`ctx.register_tool` / `create_custom_toolset`） | 仅当前桌面应用 | 业务与 GUI 紧耦合、选进程内直跑时同进程最省事 |
| MCP server（②） | **独立进程 / 独立语言** | 该 HERMES_HOME 下所有 Hermes 实例 | 业务是独立服务 / 需跨语言 / 想进程隔离 |
| Plugin（③） | `$HERMES_HOME/plugins/` | 该 HERMES_HOME 下所有 Hermes 实例 | 想跨实例复用，且还需钩子 / backend 替换 / 宿主 LLM |

三者不互斥：例如桌面应用用进程内自定义 toolset 接核心业务，同时用 `hermes mcp add` 接一个独立的第三方服务，再用一个 Plugin 做跨实例的工具增强。

---

## 15. 红线（非侵入 vs 改核；进程内护栏铁律）

- 进程内形态无安全边界：起步 `disabled_toolsets=["terminal"]`，业务能力用自建工具面（SKILL §3.5）。
- 改 `hermes-agent` 包源码只在极端情况：上游确实缺该能力、且扩展面做不到、并已向上游反馈——本技能**不鼓励**。
- 凡扩展面能覆盖的，不碰核；扩展面覆盖不了的，优先在**你的应用层**用进程内 `AIAgent` + 自定义 toolset 解决（仍不改 Hermes 源）。
- 其他铁律不变：绝不复用 `AIAgent` 实例、绝不在主线程 / 事件循环里直接 `run_conversation()`（见 SKILL §3 / §6）。
- 审批护栏必须自建（§7.2）：进程内无网关审批分类器，写类 / 执行类能力必须经 `approval`/`write_approval`/`path_security`/`threat_patterns`/`tool_guardrails` 这一套。

---

## 16. 版本与核实

- 本文命令 / 路径 / API 均经 **`hermes-agent 0.19.0` 源码内省核实**（依据 `hermes_cli/skills_hub.py`、`hermes_cli/subcommands/mcp.py`、`hermes_cli/plugins.py`、`hermes_cli/memory_setup.py`、`plugins/memory/`、`agent/memory_provider.py` 等）。
- **2026-08-15 基线统一为 0.19.0**：此前本文以 0.18.2 实测为准的断言已按 0.19.0 复核更新——§5 模块归属（含 clarify 改指 `tools.clarify_gateway`）、§7.2 审批护栏、§11 `mcp add` 参数集、§13 memory provider 插件机制；与 `00-index.md` §3 事实基线一致。

