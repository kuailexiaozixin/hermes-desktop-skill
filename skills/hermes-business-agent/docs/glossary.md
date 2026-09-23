# 术语表（glossary）

> 初读技能先看本表，建立词汇；读完回到 `SKILL.md` 的工作流主线；文档反查索引见 `references/00-index.md` §3。

| 术语 | 含义 |
| --- | --- |
| **Hermes Python Library** | `pip install hermes-agent` 后得到的 `run_agent` 等 23 个顶层模块；本技能唯一集成对象 |
| **`AIAgent`** | Library 的核心类（`from run_agent import AIAgent`）；进程内 Agent 对象，非线程安全 |
| **`run_conversation()`** | `AIAgent` 主入口，同步阻塞。返回字典有两套键集不同的形状（正常走完一轮 28 个键 / 提前退出最少只有 4 个键），成败只能判 `completed`，逐项见 `01` §2.1 |
| **`chat()`** | `run_conversation()` 的薄包装，只返回 `result["final_response"]`；因此分不清"成功答复"与"失败说明"，需要判成败的入口不要用它（`01` §2.1 口径 2） |
| **进程内直跑路线** | 5 条平等可选路线之一：在你的 EXE 同一进程内直跑 `AIAgent`（不额外起网关、不开 API Server、不走 `/v1`、单进程单文件 EXE）。五条路线逐节见 `references/02-integration-core.md` §2.1–§2.5，选型判据在其 §2.6 |
| **跨进程路线（gateway / spawn CLI / API Server / `/v1`）** | 除进程内直跑之外的 4 条路线，与它平等可选：Hermes 网关 + HTTP 服务（sidecar）、起 `hermes` 子进程、OpenAI 兼容 API Server、只挂 `/v1` 对话面。适用于网关平台接入、独立 API、外部多语言客户端；逐节位置与选型判据同上 |
| **toolset** | 一组相关工具的集合（如 file/web/memory/terminal）；用 `enabled_toolsets` / `disabled_toolsets` 控制。内核 57 个的全量清单见 `03` §3–§4，减法原则见 `01` §3.2 |
| **skill** | Hermes 原生能力单元：挂在 `$HERMES_HOME/skills/` 下的 `SKILL.md` 加随附脚本，Agent 按需读取（`02` §10）。与"本技能"这份文档不是一回事 |
| **`stream_callback`** | `run_conversation()` / `chat()` 的**方法参数**，逐片文本增量 `(delta: str)`。内核把它临时绑到 `agent._stream_callback`，只在当轮有效 |
| **`stream_delta_callback`** | `AIAgent.__init__` 上的构造器回调，与上一条**同时**收到每个文本增量，但额外会收到 `None` 收尾哨兵——两者不能共用一个不判空的回调函数（`01` §4.3 第 2 条） |
| **构造器回调** | `AIAgent.__init__` 的 16 个 `*_callback`（tool_start/complete/progress、reasoning、thinking、status、notice、clarify、step、event 等）。全量语义在 `01` §3.6.6，常用的 11 个列在 §4 |
| **`event_callback`** | 16 个构造器回调中唯一带 `(str, dict)` 类型注解的通用事件出口。但 0.19.0 内核只经它发 `session:compress` 一个事件名，拿它当界面事件源会收到近乎空的流（`01` §4.1） |
| **`disabled_toolsets`** | 减法禁用 toolset；进程内**必设 `["terminal"]`** |
| **`conversation_history`** | 多轮上下文；把上一轮返回字典里的 `messages` 原样传回即实现多轮（`01` §2.1 口径 3） |
| **`session_id`** | 会话标识。落盘由 `hermes_state` 的 SQLite `SessionDB` 承担（`11` §3），外部句柄经构造参数 `session_db` 传入（`01` §3.6 第 29 项） |
| **`HERMES_HOME`** | Hermes 运行数据（配置/会话/轨迹）根目录。解析顺序：上下文覆盖 → 同名环境变量 → 平台默认；冻结态无人替你钉，须由启动器显式钉到制品目录（`05` §3） |
| **SSE** | Server-Sent Events；FastHTML 路线把队列事件推给前端的线格式（`04` §1）。与 `event_callback` 是两件事，别混为一谈（`01` §4.1） |
| **worker 线程 + 队列** | 本路线统一桥接范式：`run_conversation` 在 worker 线程跑，回调只把事件 `queue.put`，主线程取队列渲染（`02` §3；最小骨架 `02` §6） |
| **`_ThinkingSplitter`** | 示例代码里的辅助类，把推理增量与正文增量分流到界面两个区域。实现只在 `examples/01-hermes-desktop/Agent系统/agent_runtime/_chat.py:375`，参考文档不重述；它存在的必要来自 `01` §4.3 第 4 条 |
| **签名漂移** | 升级 `hermes-agent` 后 `AIAgent` 的参数或默认值与文档记录不一致。用 `scripts/check_api_signature.py` 对照 `scripts/api-baseline.json` 发现（`07` §2） |
| **`hermes` vs `hermes-agent`** | PyPI 上两个**无关**包；正确装 `hermes-agent`，装错 `hermes` 会命令冲突 |
| **三层工具面（按风险）** | 禁止面 / 受控写面 / 只读面，量的是"这个动作能不能做、要不要看着做"（`19` §3） |
| **三层注册范式（按实现）** | 纯 Python 工具注入 / 复用内核工具集 / 把系统功能包成受控工具，量的是"这个工具怎么接进来"（`02` §7.1）。与上一条都叫"三层"，引用时必须带定语 |
| **受控写面** | 会改用户数据的那一层工具。注册的同时就要接审批、幂等键、先读当前状态、执行后回读实际生效值（`19` §3 第 2 步；可复用的内核护栏模块清单见 `02` §7.2） |
| **假绿** | 只测"进程起来了 / HTTP 200"就当成功，而 Agent 实际没干活（库导入失败时网页照样 200）。防法是断言行为证据并跑一次真实 LLM 往返（`09` §6、`17`） |
