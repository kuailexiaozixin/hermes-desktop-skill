# 术语表（glossary）

> 初读技能先看本表，建立词汇；读完回到 `SKILL.md §4` 的主题路由。

| 术语 | 含义 |
| --- | --- |
| **Hermes Python Library** | `pip install hermes-agent` 后得到的 `run_agent` 等 23 个顶层模块；本技能唯一集成对象 |
| **`AIAgent`** | Library 的核心类（`from run_agent import AIAgent`）；进程内 Agent 对象，非线程安全 |
| **`run_conversation()`** | `AIAgent` 主入口，同步阻塞，返回 `{final_response, messages}`；流式靠 `stream_callback` |
| **进程内直跑路线** | 5 条平等可选路线之一：在你的 EXE 同一进程内直跑 `AIAgent`（不额外起网关、不开 API Server、不走 `/v1`、单进程单文件 EXE）。其余跨进程路线无先后顺序，按需选用，选型见 references/02-integration-core.md §2 路径 D |
| **跨进程路线（gateway / spawn CLI / API Server / `/v1`）** | 调用 Python Library 的其余 4 条跨进程路线（与进程内直跑平等可选）：Hermes 网关 + HTTP 服务（sidecar）、起 `hermes` 子进程、OpenAI 兼容 API Server 等；当需求是网关平台接入 / 独立 API / 外部多客户端 / 多语言客户端时按需选用，选型见 references/02-integration-core.md §2 路径 D |
| **toolset** | 一组相关工具的集合（如 file/web/memory/terminal）；用 `enabled_/disabled_toolsets` 控制 |
| **skill** | Hermes 原生能力单元（区别于 WorkBuddy 的「技能」） |
| **`stream_callback`** | `run_conversation()` 的**方法参数**，文本增量回调 `(delta:str)`——流式的关键 |
| **事件回调** | `AIAgent.__init__` 的 15 个构造器回调（tool_start/complete、reasoning、event…），工具/推理事件 |
| **`event_callback`** | 15 个构造器回调中唯一带完整类型注解的通用事件总线 `(event_name:str, payload:dict)` |
| **`disabled_toolsets`** | 减法禁用 toolset；进程内**必设 `["terminal"]`** |
| **`conversation_history`** | 多轮上下文；把上轮 `result["messages"]` 传回实现多轮 |
| **`session_id`** | 会话标识；配合 SQLite 做持久化（`09`） |
| **`HERMES_HOME`** | Hermes 运行数据（配置/会话/轨迹）根目录；冻结态须指向 `<exe>/hermes_data` |
| **SSE** | Server-Sent Events；FastHTML 路线把队列事件推给前端的机制（`05`） |
| **worker 线程 + 队列** | 本路线统一桥接范式：`run_conversation` 在 worker 跑，回调 `queue.put`，主线程渲染（`03`） |
| **`_ThinkingSplitter`** | 旗舰示例里把推理段与正式回复分流的辅助类（`03` §3.2） |
| **apistar 漂移** | 版本升级导致 `AIAgent` 签名/默认值变化；用 `check_api_signature.py` 比对（`§0`） |
| **`hermes` vs `hermes-agent`** | PyPI 上两个**无关**包；正确装 `hermes-agent`，装错 `hermes` 会冲突 |
| **两/三层工具面** | Layer1 内置 toolset（减 terminal）+ Layer2 自建纯 Python 业务工具（`07`） |
| **受控 DSL 提议** | 改用户数据时用白名单操作 + 预览 + 事务 + 撤销，而非直写（`08`） |
| **假绿** | 只测 HTTP 200 就以为成功——Library 导入失败时 Web 仍 200；须真实 LLM 往返（`12`） |
