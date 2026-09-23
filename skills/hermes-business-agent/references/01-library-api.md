# 01 · Hermes Python Library API（构造器 / 回调 / 流式 / 会话 / 工具）

> 经 `hermes-agent==0.19.0` 源码内省核实。本文是 Library 接入的**权威参考**；
> 任何「装包事实 / 导入路径 / 构造参数」以本文为准。

---

## 1. 安装与导入（已核实）

```bash
# 正确包名是连字符 hermes-agent。fastapi / uvicorn / python-multipart / jinja2 本就是核心依赖，
# [web] 只把 fastapi / uvicorn / python-multipart 三项加 starlette 钉成精确版本（jinja2 是核心依赖，不在 [web] 里）；FastHTML 不在任何 extra 里，
# 须由应用自己声明 `python-fasthtml`（旗舰示例 requirements.txt 即如此）
pip install "hermes-agent[web]==0.19.0"
```

```python
# 正确：顶层模块 run_agent
from run_agent import AIAgent

# 错误（0.19.0 实测不存在）：
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
| `hermes_cli/` | 统一 CLI 包（顶层 146 个模块、含嵌套共 205，两个口径都不含包根 `__init__.py`；子命令 chat/gateway/setup/status/cron/desktop，全量见 `10`） |

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

- `chat(message, stream_callback=None) -> str`：单轮，返回最终文本。实现就是 `run_conversation()` 后取
  `result["final_response"]`（`run_agent.py:6407-6420`），因此**它无法区分成功答复与失败说明**——见 §2.1 口径 2。
- `run_conversation(user_message, system_message=None, conversation_history=None, task_id=None,
  stream_callback=None, persist_user_message=None, persist_user_timestamp=None, moa_config=None) -> dict`：
  多轮接管与结构化取数的入口，返回形状见 §2.1。`persist_*` 是"只改落盘、不改发给模型的那一份"：
  `persist_user_message` 指定持久化/返回历史里用的用户消息内容（API 侧可用合成文本，但不许它泄进转录），
  `persist_user_timestamp` 把平台事件时间作为消息元数据保留，而不是嵌进正文。

### 2.1 `run_conversation()` 返回的字典（0.19.0 源码实测）

**同一函数有两套键集不同的字典**，这是调用方最容易踩的一条，所以逐项列全。

**A · 正常走完一轮**——由 `agent/turn_finalizer.py:516-549` 组装，28 个固定键 + 4 个条件键：

| 组 | 键 | 含义 |
| --- | --- | --- |
| 结论与转录 | `final_response` | 最终文本；被中断时是中断说明文字 |
| | `last_reasoning` | 本轮最近一条 assistant 消息的推理段；遇到 `user` 角色即停，不回溯到上一轮（`turn_finalizer.py:507-513`） |
| | `messages` | 本轮完整转录，可直接作为下一轮的 `conversation_history` |
| | `api_calls` | 本轮实际发出的模型请求次数 |
| 终态标志 | `completed` / `failed` / `interrupted` | 三个布尔标志，含义见下方口径 1、2 |
| | `partial` | 只在"因工具调用非法而停"时为 `True`（`turn_finalizer.py:524`） |
| | `turn_exit_reason` | 本轮结束原因（字符串），用于日志与失败归因 |
| | `response_transformed` / `response_previewed` | 响应是否被改写 / 是否已被预览过 |
| 本轮身份 | `model` / `provider` / `base_url` / `session_id` / `service_tier` | 实际生效的模型与端点；`service_tier` 取自 `request_overrides.extra_body` |
| 计量 | `input_tokens` `output_tokens` `prompt_tokens` `completion_tokens` `total_tokens` `reasoning_tokens` `cache_read_tokens` `cache_write_tokens` `last_prompt_tokens` `estimated_cost_usd` `cost_status` `cost_source` | **会话累计值**（源码取的是 `agent.session_*`，不是一轮的增量）。要单轮或单任务的用量，必须在调用前后各读一次再相减——`21` §6 第 2 条按任务统计 token 就依赖这个差值。`last_prompt_tokens` 来自上下文压缩器，用于判断下次请求的上下文规模 |
| 条件键 | `guardrail` | 仅当工具护栏决定停机时出现，值为 `ToolGuardrailDecision.to_metadata()`（`turn_finalizer.py:550-551`） |
| | `cleanup_errors` | 仅当轨迹/会话/资源清理抛错时出现——响应照样返回，但不要把它当干净一轮（`:555`） |
| | `pending_steer` | 末轮之后才到达的 `/steer`，交回调用方作为下一轮用户输入，避免静默丢失（`:560`） |
| | `interrupt_message` | 仅当 `interrupted` 且中断自带说明文字时出现（`:566`） |

**B · 提前退出**——`agent/conversation_loop.py` 共 24 处 return，每处都是**小字典**：
跨全部 24 处都存在的键只有 `final_response`、`messages`、`api_calls`、`completed` 四个；
`error` 21/24、`failed` 14/24（两处中断返回只带 `interrupted: True` 而不带 `failed`），
个别处额外带 `failure_reason`——分类后的失败原因（如 `rate_limit` / `billing`），用途是让调用方区分
「配额墙，不是任务错」与真实失败。**上表 A 的计量键与身份键一律不出现。**

**调用口径（三条）**

1. 读任何计量键之前先判 `completed is True`；为假则改读 `error`，不要回落到默认值 0——那会把失败记成"零成本成功"。
2. 判成败不许只看 `final_response` 非空、也不许只看 `failed`：前者在失败时是错误散文，后者可能根本缺席。
   唯一稳定的是 `completed`。`chat()` 直接返回 `final_response`，所以把失败文本当正常答复交给界面；
   需要区分成败的入口（写面、计费、重试）必须走 `run_conversation()`。
3. 多轮接管只依赖 `messages`：把它原样作为下一轮的 `conversation_history` 传回即可，不必自己拼转录。


---

## 3. 构造参数（全量 71 项，源自 `AIAgent.__init__` 实测签名）

`AIAgent.__init__` 经 `hermes-agent==0.19.0` 内省，**完整参数共 71 个**（`self` 不计）。
§3.1–§3.5 是「桌面集成最常调」的分组速查；**§3.6 是 71 项全量权威清单**，逐项给出默认值与语义。
凡标注「见源码」者为参数名直译，精确语义以 `AIAgent.__init__` 签名 + docstring 为准（已写入
`scripts/api-baseline.json`）。

> **准确性红线**：下列默认值**全部来自本机 venv 的 `inspect.signature(AIAgent.__init__)` 实测**，
> 不是凭记忆或估计。更换 `hermes-agent` 版本后须重跑内省，不要照抄既有数值。

### 3.1 模型与供应商
| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `provider` / `model` | — | 供应商与模型名；`moa` 是虚拟 provider（落地见 `08` §3 MOA） |
| `base_url` / `api_key` | `None` | 自定义端点/密钥；不传走默认凭证源 |
| `api_mode` | `None` | `chat` / `responses` 等底层模式 |
| `max_iterations` | `90` | 单轮最大工具循环次数（与官方文档不一致的说明见 §3.6 第 11 行） |
| `tool_delay` | `1.0` | 工具调用间节流（秒） |
| `reasoning_config` | `None` | 推理参数（供应商相关） |
| `max_tokens` | `None` | 响应上限 |
| `providers_allowed` / `providers_ignored` / `providers_order` | `None` | 供应商白/黑名单与优先级 |

### 3.2 工具集：减法原则（最重要）
| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `enabled_toolsets` | `None` | **`None` = 启用全部工具集**（browser/computer_use/cron/code_execution/memory/web/mcp…），与网关启动等价 |
| `disabled_toolsets` | `None` | 在「全量」基础上**做减法剔除**；进程内直跑常用 `["terminal"]` |

> **减法原则**：永远用 `disabled_toolsets` 做减法，**不要硬编码 `enabled_toolsets=["file"]` 之类**——
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
> 其余保持默认即可。这里全列出来是为了「万无一失」——避免你误以为 §3.1–§3.5 那几张「最常调」表就是全部参数，
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
| 11 | `max_iterations` | `90` | 单轮最大工具循环次数（防止无限循环）。**注意：官方文档写 500，与源码不符**——本行是这一冲突的唯一出处（另见 `docs/troubleshooting.md` §11）；集成时**必须显式设**，禁止依赖默认值 |
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

## 4. 回调与流式（16 个构造器回调）

`AIAgent.__init__` 接受 16 个 `*_callback` 构造参数（全量语义见 §3.6.6），全部可选，互不依赖。下表是常用的 11 个：

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

### 4.1 `event_callback(event_name, payload)` 与 SSE 线格式（两件事，别混为一谈）

`event_callback` 是 16 个 `*_callback` 里唯一带 `(str, dict)` 形状注解的回调
（`Optional[Callable[[str, dict], NoneType]]`；`reaction_callback` 只带 `(str)`，其余注解为裸 `callable`），
设计意图是"事件名 + 载荷"的统一出口。**但 0.19.0 内核只经它发一个事件名**：`session:compress`
（发出点 `agent/conversation_compression.py:1433`、`agent/codex_runtime.py:250`；
`grep -rn 'event_callback("' site-packages/agent` 全量命中仅此两处）。
禁止把对话增量、工具卡片当成 `event_callback` 发出来的东西——按那种假设写的监听器一轮也收不到。

界面要的是**每个回调各占一路、由应用汇成一条流**。旗舰示例 `Agent系统/agent_runtime/_chat.py` 的汇流逐路可回指源码：

| SSE `type`（`_sse({"type": ...})` 的 `type`） | payload 关键字段 | 来源（示例内行号：注册 → 入队） |
| --- | --- | --- |
| `delta` | `text` | `stream_callback` :642 → :570 |
| `reasoning` | `text` | `reasoning_callback` :627 → :575 |
| `action` | `tool`, `preview` | `tool_start_callback` :625 → :548 |
| `context_hint` | `tool`, `hint` | 工具开始路径内一并产出 :557 |
| `action_result` | `tool`, `preview`, `result` | `tool_complete_callback` :626 → :561 |
| `tool_progress` | `name`, `args`, `kwargs` | `tool_progress_callback` :628 → :582 |
| `done` | `final`, `html`, `messages`, `changed_files` | worker 收尾 :658 → :733 |
| `error` | `message` | worker 超时 :595 / 异常 :662 |

两条不变量：错误路径**不再**下发 `done`（避免覆盖已渲染内容）；示例本身**没有**监听 `event_callback`，
压缩事件要接得自己加——这也是把它与上面八类分开记的实际好处。

> **未证实项（准确性红线）**：上述词汇**没有 delegation（委派）事件**。
> `event_callback` 是否透传子代理委派事件**未经实测**——实现委派卡片前必须先实测，
> 否则按「静默不显示」处理，不得在文档中宣称已支持。

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
        # 把 ("delta", text) 映射为前端事件 …… 见 02 §3
```

### 4.3 回调的五条触发规则（决定"为什么一次也没进"）

`17` 要求测试断言行为证据，而下面四条会让回调安静地不触发或触发形状不符预期，先按规则设计再接线：

1. **工具调用轮不流文本**。流式路径只对"纯文本终答"发增量，工具调用轮抑制文本回调
   （`agent/chat_completion_helpers.py:2243-2245`）；且进入工具执行前会先冲刷一次显示回调
   （`agent/conversation_loop.py:5050-5058`）。所以一次带工具往返回界面上"半天没字"是正常形状，
   进度提示要靠 `tool_start_callback` 而不是靠 delta 计数。
2. **`None` 是收尾哨兵，且只发给构造器那一路**。`stream_delta_callback` 会被显式传入 `None` 表示一段流结束
   （`conversation_loop.py:5057`、`:5081`）；方法参数 `stream_callback`（内核存为 `agent._stream_callback`，
   逐轮绑定 `agent/turn_context.py:363`、轮末置 `None` `agent/turn_finalizer.py:573`）**明确不收 `None`**
   （`conversation_loop.py:5053-5054` 注释）。因此做 `buf += delta` 的回调必须对 `None` 短路，
   两路不能共用一个不做判空的函数。文本增量本身两路同发（`run_agent.py:5205-5212`）；空串不会触发（`:5202-5203`）。
3. **回调里抛异常没有任何信号**。三处触发点全是 `except Exception: pass`
   （`run_agent.py:4867-4872`、`:5205-5212`，`chat_completion_helpers.py:2837-2841`），
   抛异常那一次的文本还不计入内核的已流式记录。症状是"界面少了一段字"而非报错，
   所以回调体只做一件事——把事件塞进队列（§4.2），渲染与拼字符串留在主线程。
4. **`reasoning_callback` 的触发形状随是否接了流式回调而变**：注册了 `stream_delta_callback` 或本轮传了
   `stream_callback` 时按推理**增量**多次触发；两者都没注册时才在轮末把整段推理一次性发出
   （`chat_completion_helpers.py:1267-1279` + `run_agent.py:5216-5229`）。同时接 reasoning 与 delta 的界面
   必须按"多段碎片"处理——旗舰示例为此写了分流类（`docs/glossary.md` 的 `_ThinkingSplitter` 行给出其源码位置）。
5. **流式可能被整会话关掉，且没有任何回调通知你**。`agent._disable_streaming` 只在三处被置 `True`，
   置上之后该实例本次进程内**后续每一轮都不再走流式**：Bedrock 的 IAM 拒了
   `InvokeModelWithResponseStream`（`agent/chat_completion_helpers.py:2330-2331`）、供应商号称流式却返回
   完整响应对象而非迭代器（`:2703-2710`）、流式请求抛出不支持类错误（`:3522-3523`）。三处的通知方式是
   `_safe_print` 一行告警或 `logger.info`，**既无回调也不导出可读属性**——窗口化 EXE 没有控制台，那行告警看不见。
   于是症状是"delta 一次都没来过"而不是报错。另有一条更窄的旁路：`platform == "cron"` 且
   `api_mode == "chat_completions"` 且 `provider != "moa"` 时直接委派非流式入口（`:2260-2261`，
   判据 `should_use_direct_api_call` 在 `:435-447`，注释记明是为 #62151 的嵌套线程池死锁绕行），
   常驻服务里跑 Hermes cron 会命中。因此：接了 delta 的界面必须容忍"全程零 delta"（超时后退回整段渲染），
   进度反馈改依赖 `tool_start_callback` / `step_callback`；配置项 `display.streaming` 是 CLI 专用
   （`cli.py:3827` 取默认 `false`、`gateway/display_config.py:12` 注明 CLI-only），进程内没有等价开关。


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

> **费用估算红线**：进程内直跑路线无网关计费，`get_credits_*` 返回的是**估算值**，
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

> 冻结（打包 EXE）后 `HERMES_HOME` 落在哪儿，取决于**启动器有没有钉根**：库对 `sys.frozen` 无感知，
> 不钉就退回平台默认根（Windows 是 `%LOCALAPPDATA%\hermes`）。钉根写法与两条真实约束见 `05` §3、`06` §4。

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
