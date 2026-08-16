# 01 · Hermes Python Library API（构造器 / 回调 / 流式 / 会话 / 工具）

> 经 `hermes-agent==0.19.0` 源码内省核实。本文是 Library 接入的**权威参考**；
> 任何「装包事实 / 导入路径 / 构造参数」以本文为准。

---

## 1. 安装与导入（已核实）

```bash
# 正确包名是连字符 hermes-agent；[web] 额外拉取 FastHTML/uvicorn 等 Web 依赖
pip install "hermes-agent[web]==0.19.0"
```

```python
# ✅ 正确：顶层模块 run_agent
from run_agent import AIAgent

# ❌ 错误（0.19.0 实测不存在）：
from hermes.toolsets import TOOLSETS      # ModuleNotFoundError: hermes
import hermes_agent                        # ModuleNotFoundError: hermes_agent
```

**已安装包在 site-packages 根层的模块**（均顶层，无 `hermes` 包）：

| 模块 | 作用 |
| --- | --- |
| `run_agent.py` (~270 KB) | `AIAgent` 类本体（构造转发到 `agent.agent_init.init_agent`） |
| `hermes_constants.py` | 路径/环境常量：`HERMES_HOME`、`get_config_path`、`get_skills_dir` 等 |
| `hermes_state.py` | 会话/状态持久化 |
| `hermes_logging.py` / `hermes_time.py` / `hermes_bootstrap.py` | 日志 / 时间 / 引导 |
| `tools/delegate_tool.py` | `TOOLSETS` 注册表（57 项，见 `03` §1；`from tools.delegate_tool import TOOLSETS`） |
| `tools/` | 各工具实现（`file_tools`、`browser_tool`、`terminal_tool` …） |
| `agent/` | 运行时（`agent_init`、`tool_executor`、`context_engine`、`moa_loop` …） |
| `hermes_cli/` | 统一 CLI 包（147 个顶层模块，含嵌套共 205；子命令 chat/gateway/setup/status/cron，全量见 `10`） |

---

## 2. 最小可用示例（进程内）

```python
from run_agent import AIAgent

agent = AIAgent(
    provider="deepseek",          # 或 openai / anthropic / openrouter / moonshot / qwen ...
    model="deepseek-chat",
    api_key="<KEY>",              # 也可用 HERMES_API_KEY 等环境变量，不传则走默认凭证源
    disabled_toolsets=["terminal"],   # 进程内直跑常用：禁用 spawn-per-call 的终端
    quiet_mode=True,
)
reply = agent.chat("用一句话解释什么是进程内 Agent。")
print(reply)
agent.close()
```

- `chat(message, stream_callback=None) -> str`：单轮，返回最终文本。
- `run_conversation(user_message, system_message=None, conversation_history=None,
  task_id=None, stream_callback=None, moa_config=None) -> dict`：返回含最终消息与历史的字典，
  适合多轮接管。

---

## 3. 构造参数（全量 71 项，源自 `AIAgent.__init__` 实测签名）

`AIAgent.__init__` 经 `hermes-agent==0.19.0` 内省，**完整参数共 71 个**（`self` 不计）。
§3.1–§3.5 是「桌面集成最常调」的分组速查；**§3.6 是 71 项全量权威清单**，逐项给出默认值与语义。
凡标注「见源码」者为参数名直译，精确语义以 `AIAgent.__init__` 签名 + docstring 为准（已写入
`scripts/api-baseline.json`）。

> ⚠️ **准确性红线**：下列默认值**全部来自本机 venv 的 `inspect.signature(AIAgent.__init__)` 实测**，
> 不是凭记忆或估计。更换 `hermes-agent` 版本后须重跑内省，不要照抄既有数值。

### 3.1 模型与供应商
| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `provider` / `model` | — | 供应商与模型名；`moa` 是虚拟 provider（见 03 §4 MOA） |
| `base_url` / `api_key` | `None` | 自定义端点/密钥；不传走默认凭证源 |
| `api_mode` | `None` | `chat` / `responses` 等底层模式 |
| `max_iterations` | `90` | 单轮最大工具循环次数 |
| `tool_delay` | `1.0` | 工具调用间节流（秒） |
| `reasoning_config` | `{}` | 推理参数（供应商相关） |
| `max_tokens` | `None` | 响应上限 |
| `providers_allowed` / `providers_ignored` / `providers_order` | `None` | 供应商白/黑名单与优先级 |

### 3.2 工具集：减法原则（最重要）
| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `enabled_toolsets` | `None` | **`None` = 启用全部工具集**（browser/computer_use/cron/code_execution/memory/web/mcp…），与网关启动等价 |
| `disabled_toolsets` | `None` | 在「全量」基础上**做减法剔除**；进程内直跑常用 `["terminal"]` |

> ⚠️ **减法原则**：永远用 `disabled_toolsets` 做减法，**不要硬编码 `enabled_toolsets=["file"]` 之类**——
> 那会把 browser/记忆/联网等能力全部砍掉，导致功能退化。旗舰示例 `build_agent()`
> 即 `enabled_toolsets=None` + `disabled_toolsets=_resolve_disabled_toolsets(web_search)`。
> 若 `web_search=False`（离线模式），再额外剔除 `web` + `browser`。

### 3.3 会话与记忆
| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `session_id` | `None` | 会话标识；相同 id 复用历史 |
| `session_db` | `None` | 外部会话存储句柄 |
| `parent_session_id` | `None` | 子会话归属 |
| `skip_memory` | `False` | `True` 关闭跨会话持久记忆 |
| `skip_context_files` | `False` | `True` 关闭上下文文件注入 |
| `load_soul_identity` | `False` | `True` 加载 `SOUL.md` 人格 |
| `ephemeral_system_prompt` | `None` | 临时系统提示词（覆盖默认） |

### 3.4 采样/格式透传通道
> `AIAgent` **不直接接收** `temperature` / `top_p` / `stop` / `response_format`。
> 这些必须通过 **`request_overrides: dict`** 透传到底层 provider 请求
> （旗舰示例 `_build_request_overrides()` 已证实；api-baseline 亦记录此约束）。

```python
agent = AIAgent(
    provider="openai", model="gpt-4o",
    request_overrides={"temperature": 0.3, "top_p": 0.9,
                       "stop": ["\n\n"], "response_format": {"type": "json_object"}},
)
```

> **透传机制（源码核实 `agent/transports/chat_completions.py`）**：`request_overrides` 在 `build_api_kwargs`
> 中经 `api_kwargs.update(overrides)` **整体并入**底层 provider 请求参数（各 API 路径自行消费 `service_tier` /
> `speed` / `extra_body` / `response_format` 等键），故它是**自由键字典**——除采样参数外，`response_format`
> / `extra_body` 也会原样透传给 OpenAI 兼容端点。自定义 provider 的 `extra_body` 可经
> `_custom_provider_request_overrides`（`runtime_provider.py:917`）透传。

### 3.4bis 结构化输出与多模态输入（两类原生路径）

**结构化输出——主 Agent 的透传路径（JSON Schema）**：依赖 provider 对 `response_format` 的支持
（OpenAI 兼容端点多支持）：

```python
agent = AIAgent(
    provider="openai", model="gpt-4o",
    request_overrides={
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "extract", "strict": True,
                             "schema": {"type": "object", "properties": {...}}},
        }
    },
)
```

**结构化输出——强类型路径（推荐，原生 JSON Schema 校验）**：`PluginLlm.complete_structured()`
（`agent/plugin_llm.py`）跑「有界强类型结构化补全」，自带 JSON Schema 校验（需 `jsonschema` 包，缺装时
JSON 模式仍可用但跳过 schema 强制）与**图像输入**。通过插件 `ctx.llm` 暴露（详见 `02` §12），最贴合
「宿主侧要稳定拿到可解析、可校验的结构化结果」的场景（如把 Agent 输出喂给表单/表格/业务流程）：

```python
# 在插件 register(ctx) 内：
from agent.plugin_llm import PluginLlmTextInput, PluginLlmImageInput
res = ctx.llm.complete_structured(
    instructions="从这段话提取订单：订单号、金额、收货地址，返回 JSON。",
    input=[PluginLlmTextInput(text="订单号 A-1001，金额 88 元，寄到北京。")],
    json_schema={
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "amount": {"type": "number"},
            "address": {"type": "string"},
        },
        "required": ["order_id", "amount", "address"],
    },
)
order = res.parsed   # 已通过 JSON Schema 校验的 dict
```

**多模态输入——主 Agent（OpenAI 风格消息）**：`run_conversation(user_message: Any)` 接受 OpenAI 风格的
`content` 列表（含 `image_url` / base64 图像）。`agent/conversation_loop.py` 处理多模态内容列表；当模型
不支持视觉时，hermes 会**自动剥离图像并以纯文本重试**（`conversation_loop.py:2631` 一带）：

```python
result = agent.run_conversation([
    {"type": "text", "text": "这张图里有什么？"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
])
```

> **分工建议**：要「对话内看图/听音」→ 主 Agent 多模态消息或 `vision`/`video` 工具集（`03` §3.1）；
> 要「插件内稳定拿到强类型结构化 JSON」→ `ctx.llm.complete_structured()`。

### 3.5 检查点（checkpoints）
| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `checkpoints_enabled` | `False` | 开启对话快照 |
| `checkpoint_max_snapshots` | `20` | 最大快照数 |
| `checkpoint_max_total_size_mb` | `500` | 快照总容量上限 |
| `checkpoint_max_file_size_mb` | `10` | 单文件上限 |

---

### 3.6 全量构造参数清单（71 项，实测默认值）

> 下表是 `AIAgent.__init__` 的**完整参数权威清单**（不含 `self`）。分组与 §3.1–§3.5 对应，
> 每项默认值均经 `inspect.signature` 实测；语义为参数名直译 + 与源码/示例交叉验证的结论。
> 参数很多，但**桌面集成真正需要显式传的只有一小撮**（见 §3.1–§3.5 的「最常调」表），
> 其余保持默认即可。这里全列出来是为了「万无一失」——避免你误以为构造器只有 15 个参数，
> 也方便排查某个能力该由哪个参数控制。

#### 3.6.1 连接与模型（Connection & Model）
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 1 | `provider` | `None` | 供应商名（`deepseek`/`openai`/`anthropic`/`openrouter`/`moonshot`/`qwen`/`moa`…） |
| 2 | `model` | `""`（空串） | 模型名；空串时由 provider 选默认 |
| 3 | `base_url` | `None` | 自定义 API 端点；`None` 走 provider 默认 |
| 4 | `api_key` | `None` | 密钥；`None` 走默认凭证源（环境变量/凭据池） |
| 5 | `api_mode` | `None` | 底层模式（`chat`/`responses` 等）；`None` 由 provider 决定 |
| 6 | `acp_command` | `None` | ACP（Agent Client Protocol）命令入口；进程内直跑路线一般不用 |
| 7 | `acp_args` | `None` | ACP 命令参数 |
| 8 | `command` | `None` | 内置 CLI 命令名（如 `chat`/`gateway`）；进程内直跑路线不用 |
| 9 | `args` | `None` | 内置 CLI 命令参数 |
| 10 | `fallback_model` | `None` | 主模型失败时的回退模型 |
| 11 | `max_iterations` | `90` | 单轮最大工具循环次数（防止无限循环） |
| 12 | `tool_delay` | `1.0` | 工具调用之间的节流（秒） |
| 13 | `max_tokens` | `None` | 响应 token 上限；`None` 由 provider 决定 |
| 14 | `reasoning_config` | `None` | 推理参数（供应商相关，如 reasoning effort） |
| 15 | `service_tier` | `None` | 服务层级（如 OpenAI `priority`） |
| 16 | `request_overrides` | `None` | **采样/格式透传字典**（温度/top_p/stop/response_format 等经此透传，见 §3.4） |
| 17 | `prefill_messages` | `None` | 预填消息（assistant prefill，部分 provider 支持） |

#### 3.6.2 工具集开关（Toolset Switches）— 最可能动的两个
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 18 | `enabled_toolsets` | `None` | `None`＝启用全部；传列表则**只**启用这些（减法原则见 §3.2，勿硬编码） |
| 19 | `disabled_toolsets` | `None` | 在全量基础上**剔除**；进程内直跑常用 `["terminal"]` |
| 20 | `tool_progress_mode` | `"all"` | 工具进度回调的粒度（`all`/`none` 等） |

#### 3.6.3 供应商路由（Provider Routing）
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 21 | `providers_allowed` | `None` | 供应商白名单（仅允许这些） |
| 22 | `providers_ignored` | `None` | 供应商黑名单（排除这些） |
| 23 | `providers_order` | `None` | 供应商优先级顺序 |
| 24 | `provider_sort` | `None` | 供应商排序策略 |
| 25 | `provider_require_parameters` | `False` | 是否要求供应商带齐参数才能用 |
| 26 | `provider_data_collection` | `None` | 供应商数据收集偏好 |
| 27 | `openrouter_min_coding_score` | `None` | OpenRouter 路由的最低 coding 评分门槛 |

#### 3.6.4 会话与记忆（Session & Memory）
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 28 | `session_id` | `None` | 会话标识；相同 id 复用历史（持久化核心，见 `09`） |
| 29 | `session_db` | `None` | 外部会话存储句柄（接 SQLite 等） |
| 30 | `parent_session_id` | `None` | 子会话归属父会话 |
| 31 | `skip_memory` | `False` | `True` 关闭跨会话持久记忆 |
| 32 | `skip_context_files` | `False` | `True` 关闭上下文文件自动注入 |
| 33 | `load_soul_identity` | `False` | `True` 加载 `SOUL.md` 人格 |
| 34 | `pass_session_id` | `False` | 是否把 session_id 透传给下游/平台 |
| 35 | `ephemeral_system_prompt` | `None` | 临时系统提示词（覆盖默认，不退化为持久） |

#### 3.6.5 平台 / 身份（Platform & Identity）— 网关/平台态常用，进程内直跑一般留空
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 36 | `platform` | `None` | 平台标识（如 `discord`/`feishu`/`web`）；进程内桌面自定 |
| 37 | `user_id` | `None` | 用户 id |
| 38 | `user_id_alt` | `None` | 备用用户 id |
| 39 | `user_name` | `None` | 用户名 |
| 40 | `chat_id` | `None` | 会话/聊天 id（平台维度） |
| 41 | `chat_name` | `None` | 会话/聊天名 |
| 42 | `chat_type` | `None` | 会话类型（群/私聊等） |
| 43 | `thread_id` | `None` | 线程 id |
| 44 | `gateway_session_key` | `None` | 网关会话键（网关态用） |

#### 3.6.6 回调（Callbacks）— 桥接 GUI/Web 的核心（见 §4）
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 45 | `stream_delta_callback` | `None` | 增量文本回调（逐字渲染） |
| 46 | `reasoning_callback` | `None` | 推理片段回调（思考折叠区） |
| 47 | `thinking_callback` | `None` | thinking 回调（与 `reasoning_callback` 互补） |
| 48 | `reaction_callback` | `None` | 反应/反馈事件回调（对助手消息的「表情/表态」等反应事件） |
| 49 | `tool_start_callback` | `None` | 工具开始回调（卡片「运行中」） |
| 50 | `tool_complete_callback` | `None` | 工具结束回调（卡片「完成」） |
| 51 | `tool_progress_callback` | `None` | 工具进度回调（MoA 参考模型等） |
| 52 | `tool_gen_callback` | `None` | 工具生成回调 |
| 53 | `step_callback` | `None` | 每步回调（步骤指示） |
| 54 | `clarify_callback` | `None` | 需追问时的回调（弹选择/问答） |
| 55 | `read_terminal_callback` | `None` | 读终端输出回调（terminal 工具集启用时） |
| 56 | `interim_assistant_callback` | `None` | 临时 assistant 消息回调 |
| 57 | `status_callback` | `None` | 状态条回调 |
| 58 | `notice_callback` | `None` | 提示回调（带 key） |
| 59 | `notice_clear_callback` | `None` | 清除提示回调（带 key） |
| 60 | `event_callback` | `None` | **统一事件总线**（`(event_name, payload)`，`01` §4.1 词汇） |

#### 3.6.7 检查点（Checkpoints）
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 61 | `checkpoints_enabled` | `False` | 开启对话快照（经 `tools.checkpoint_manager`，见 `08` §2） |
| 62 | `checkpoint_max_snapshots` | `20` | 最大快照数 |
| 63 | `checkpoint_max_total_size_mb` | `500` | 快照总容量上限 |
| 64 | `checkpoint_max_file_size_mb` | `10` | 单文件上限 |

#### 3.6.8 运行/预算/凭证（Runtime / Budget / Credentials）
| # | 参数 | 默认 | 语义（直译/实测） |
| --- | --- | --- | --- |
| 65 | `iteration_budget` | `None` | 迭代预算（更细粒度的循环上限控制） |
| 66 | `credential_pool` | `None` | 凭证池（多账号/多 key 轮换） |
| 67 | `save_trajectories` | `False` | 是否落盘轨迹（`BatchRunner`/调试用） |
| 68 | `quiet_mode` | `False` | 静默模式（减少控制台噪声，桌面集成推荐 `True`） |
| 69 | `verbose_logging` | `False` | 详细日志开关（调试用，默认关） |
| 70 | `log_prefix_chars` | `100` | 日志前缀字符数（截断长前缀） |
| 71 | `log_prefix` | `""` | 日志前缀串（多实例区分时用） |

> 上述 68–71 属日志细节，桌面集成一般保持默认；但它们**仍计入 `AIAgent.__init__` 的完整形参**，
> 本表已覆盖全部 **71 个**形参（经 `inspect.signature` 实测，与源码零漂移）。

---

## 4. 回调与流式（15+ 构造器回调）

`AIAgent.__init__` 接受一组命名回调，全部可选。最常用：

| 回调 | 触发时机 | 典型用途 |
| --- | --- | --- |
| `stream_delta_callback(text)` | 每片增量文本 | 前端逐字渲染 |
| `reasoning_callback(text)` | 推理片段 | 「思考」折叠区 |
| `tool_start_callback(name,**kw)` | 工具开始 | 工具卡片「运行中」 |
| `tool_complete_callback(name,**kw)` | 工具结束 | 工具卡片「完成」 |
| `tool_progress_callback(name,args,kwargs)` | 工具进度 | MoA 参考模型等进度 |
| `step_callback(...)` | 每步 | 步骤指示 |
| `event_callback(event_name: str, payload: dict)` | **统一事件总线** | 见下 |
| `clarify_callback(...)` | 需追问 | 弹选择/问答 |
| `status_callback(msg)` / `notice_callback(key,msg)` / `notice_clear_callback(key)` | 状态/提示 | 状态条 |

### 4.1 `event_callback(event_name, payload)` 与 SSE 词汇

`event_callback` 是唯一带完整类型注解的回调，是**把内核事件桥接进 GUI/Web 的统一入口**。
旗舰示例 `agent_runtime.py` 将 worker 队列事件映射为 SSE 流，已核实的**事件词汇**为：

| `event_name`（即 `_sse({"type": ...})` 的 `type`） | payload 关键字段 | 含义 |
| --- | --- | --- |
| `delta` | `text` | 增量正文（也走 `_delta_chunk`） |
| `reasoning` | `text` | 推理/思考片段 |
| `action` | `tool`, `preview` | 工具调用开始 |
| `action_result` | `tool`, `preview`, `result` | 工具结果 |
| `tool_progress` | `name`, `args`, `kwargs` | 工具进度（MoA 参考模型等） |
| `done` | `final`, `html`, `messages`, `changed_files` | 收尾：完整文本/渲染 HTML/消息历史/改动文件 |
| `error` | `message` | 错误（错误路径**不再**下发 `done`，避免覆盖） |

> ⛔ **未证实项（准确性红线）**：上述词汇**没有 delegation（委派）事件**。
> `event_callback` 是否透传子代理委派事件**未经实测**——实现委派卡片前必须先实测，
> 否则以「静默不显示」兜底，不得在文档宣称已支持。

### 4.2 推荐桥接模式（来自旗舰示例）

```python
import queue, threading

def build_stream(agent, user_msg):
    q = queue.Queue()
    SENTINEL = object()
    def worker():
        try:
            agent.run_conversation(user_msg, stream_callback=lambda t: q.put(("delta", t)))
        finally:
            q.put(SENTINEL)
    threading.Thread(target=worker, daemon=True).start()
    while True:                       # 生成器产出 SSE 块
        item = q.get()
        if item is SENTINEL: break
        # 把 ("delta", text) 映射为前端事件 …… 见 02 §2
```

---

## 5. 会话与记忆的运行时方法

| 方法 | 说明 |
| --- | --- |
| `chat(msg)` / `run_conversation(msg, ...)` | 对话（见 §2） |
| `reset_session_state(previous_messages=None, old_session_id=None, carry_over_context=False)` | 重置会话（保留/不保留上下文） |
| `commit_memory_session(messages=None)` | 显式落盘记忆 |
| `shutdown_memory_provider(messages=None)` | 关闭记忆 provider |
| `interrupt(message=None)` / `clear_interrupt()` | 中断/清除中断 |
| `steer(text) -> bool` | 运行中注入引导指令 |
| `switch_model(new_model, new_provider, api_key="", base_url="", api_mode="")` | 运行中换模型 |
| `release_clients()` / `close()` | 释放底层 HTTP 客户端 / 整体关闭 |
| `get_activity_summary()` | 活动摘要 |
| `get_credits_spent_micros()` / `get_credits_state()` / `get_rate_limit_state()` | 用量/额度（估算，非真实账单） |

> ⚠️ **费用估算红线**：进程内直跑路线无网关计费，`get_credits_*` 返回的是**估算值**，
> 不得宣称「真实账单成本」。

---

## 6. 环境与 `HERMES_HOME`（详见 `05-install-and-env.md`）

环境根目录由 `hermes_constants` 统一管理，是**唯一真相源**：

```python
import hermes_constants as hc
hc.get_hermes_home()                 # -> Path，数据根（会话/记忆/技能/配置）
hc.get_config_path()                 # -> Path，config.yaml 位置
hc.get_skills_dir()                  # -> Path，用户技能目录
hc.get_optional_mcps_dir()           # -> Path，可选 MCP 目录
hc.set_hermes_home_override(path)    # 运行时覆盖（返回 contextvars.Token）
hc.reset_hermes_home_override(token) # 还原
```

> 冻结（打包 EXE）后 `HERMES_HOME` **恒为 `<exe>/hermes_data`**，不可重定向——见 `05` §3、`06` §4。

---

## 7. 自定义纯 Python 工具（扩展点）

桌面应用常需把自有工具（文件预览、宿主命令、业务动作）注入 Agent。旗舰示例的模式：

```python
from run_agent import AIAgent
register_pure_python_tools()         # 注册自有工具（示例：file_tools/host_tools/app_tools）
agent = AIAgent(...)                  # 工具已在其工具集中可见
```

- `register_pure_python_tools()`：把应用层工具登记进运行时（示例自有函数，非 Library 内置）。
- 进程内直跑路线**没有网关的「危险命令审批分类器」**（`approvals.mode: smart|manual|off` 无触发源），
  因此审批/护栏必须由**自建工具层**实现（见 `03` §2 审批闭环）。
