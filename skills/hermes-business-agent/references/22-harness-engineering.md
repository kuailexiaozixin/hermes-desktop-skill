# 22 · Agent Harness：hermes-agent 的运行机器、可改边界与改造定档

业务方提的要求越来越多：「每一轮最多让它试三次工具」「压缩之后别把我们的单号丢了」「这条命令必须有人点确认」。
这三句话看起来是三件事，实际上落在同一层——不是模型本身，也不是你写的那些业务工具，而是**把一次对话从输入跑到输出的那层代码**。
业界把这一层叫 **Agent Harness**（字面义"挽具"：套在模型身上、让它能拉动真实工作的那副缰绳和鞍具）。
定档错这一层，代价是具体的：你会把可配置的东西当成交付需求排进工期，或者把只有改源码才做得到的事情当成"加个插件"就答应了。

本篇不是把这句话再论证一遍。它交付五样能直接查的东西：

1. **部件表**（§2）：这一层由哪些部件组成，每个部件在 `hermes-agent==0.19.0` 里是哪份文件、哪个符号；
2. **可改边界三档**（§4）：哪一档改配置、哪一档写插件、哪一档必须改包源码——每条都带源码位置，可自己点开核对；
3. **定档动作**（§6）：一条改造要求进来，按什么顺序做才能既不误判可行、也不轻率动手改核；
4. **检索机制**（§8）：一轮对话里模型凭什么东西找到该用的东西，四条机制各自的判据与失效形态；
5. **多轮编排**（§9）：单轮跑完之后由谁决定要不要再跑一轮，验收面在哪、预算封在哪、状态存在哪。

**位置标识的口径**：本篇引用源码一律给到**文件 + 函数名 / 类名 / 常量名**，不给行号。
行号会随上游每次改动整体漂移，而符号名不会；复核时用 `grep -n "符号名" 文件名` 定位，再读那一处代码。

第 3 样是本篇存在的理由。前文各篇讲的是"怎么把 Agent 用起来"（`01`/`02`/`03`），只有这一篇要回答
"当官方没预留口子时你该怎么办"，而那正是第 ⑤⑥ 步之后项目最容易翻车的位置。

> 先说清楚一件事：下面 §4.3 列出的"改源码才动得了"的四条边界，是本篇的主要价值所在。
> 它们看起来都"应该可以配"——阈值、白名单、审批否决、引擎选择，任何一个 Agent 框架都会给你开关。
> 在 hermes-agent 0.19.0 上，这四个开关里有三个不是你以为的那样：`compression.threshold` 填 0.3 会被抬回 0.75；
> `tool_loop_guardrails` 只能调阈值、不能改"哪些工具算幂等"；审批钩子插件拿到的是观察权不是否决权。
> 每一条都在本机源码上读过具体行，位置附在 §4.3。

---

## 1. 这个词指什么，Hermes 自己怎么用这个词

**白话**：模型只会做一件事——输入一段文本，输出一段文本。要它"把发票审一遍并把结论写进 ERP"，需要有人在外面
准备材料（这一轮该让模型看到什么）、把它的请求翻译成人能执行的动作（工具调用）、拿回结果再喂回去、失败了重来、
危险动作先问人、跑完把过程记下来。这一整套"外面的人"就是 harness。

**边界（四个词不要混）**：模型（权重与推理服务）不在 harness 里；你写的业务工具实现不在 harness 里；
`hermes-agent` 的 `AIAgent` 主循环、上下文装配、工具分发、审批、会话存储、回调，全在 harness 里。
框架（framework）与运行时（runtime）是 harness 的近邻词，区别在于：框架通常指可复用的构件集，运行时指实际执行与调度，
harness 指"为了让这一个模型能干这活而搭的那副架子"——它离业务最近，也最容易因为省事而被跳过。
提示词（prompt）算 harness 的一部分，但它是**软约束**：写在提示词里的"请不要重复调用同一工具"不产生强制，
强制在部件 7（循环护栏）与部件 6（权限与审批闸门）里（编号见 §2 表）。

**Hermes 自己的用法（核对过，别把术语当成它的架构词汇表）**。口径：不区分大小写地匹配字符串 `harness`。
文档侧（`hermes-llms-full.txt`，96,443 行）命中 23 行、词本身 26 次；源码侧（0.19.0 `RECORD` 列出的 793 个 `.py`）
命中 18 个文件、38 行、38 次。源码里 38 行只说三件事：**20 行**指后台 self-improvement review 由外层注入的那一轮
（`hermes_state.py` 独占 14 行，含前缀表 `_REVIEW_HARNESS_PREFIXES`、`_is_background_review_harness_message()`
与剥除函数 `_strip_background_review_harness()`；另 `agent/background_review.py` 3 行、`run_agent.py` 2 行、
`agent/agent_init.py` 1 行）——这类轮次会被从会话数据里剥掉；**10 行**是 "test harness"，指测试替身与夹具，
跟运行时无关（`gateway/platforms/base.py` 2 行等）；**余下 8 行**散在评测跑批
（`tui_gateway/synthetic_turn.py` 的 certify harness，模块 docstring）、`asyncio.run` 壳
（`gateway/platforms/base.py`）、浏览器 `session` 各自的守护壳（`tools/browser_tool.py`）、
看板与网关侧（`tools/kanban_tools.py`、`gateway/run.py` 等）这些位置。文档侧同样全是具体东西：外部驱动壳
（"the same pattern other agent harnesses use for repo-local configuration"）、评测跑批
（"one-shot and eval-harness invocations that run under a hard external ceiling"）、浏览器 `session` 各自的守护壳
（"Each name gets its own harness daemon"）。两侧合起来，"the harness" 这种定指只有 5 处，每次都指着近处那个东西，
**没有一处把 Hermes 整体称作 "the Harness"**。
**结论**：§2 的部件切分是我们外加的分析透镜，不是 Hermes 的官方模块划分；它的作用只有一个——
把"这条业务要求该找谁"定位到具体文件。任何把本节读成"Hermes 文档里的架构分层"的引用都是错的。

---

## 2. 部件表：这一层由哪些部件组成，各自在 0.19.0 的落点

这一层由哪些部件组成，本篇按 12 件切。切分依据是本机逐模块读下来的结果，其中两处必须拆开才说得清——
**上下文装配**与**上下文压缩**在 Hermes 里是两套代码、两条配置路径；**主循环**与**循环护栏**同理（护栏可以整段关掉）。
每行的"本技能归属"列指出该部件的详细口径已经写在哪篇，避免同一事实两处维护。

| # | 部件 | 它替你决定什么（业务白话） | hermes-agent 0.19.0 落点（已核对） | 本技能归属 |
| --- | --- | --- | --- | --- |
| 1 | 主循环 | 一轮对话什么时候停 | `agent/conversation_loop.py` 的 `run_conversation()`；轮次推进条件是该函数内 `while (api_call_count < agent.max_iterations and agent.iteration_budget.remaining > 0)` 一句（迭代上限与迭代预算同时成立才继续，另有 `_budget_grace_call` 宽限一次）；预算对象 `agent/iteration_budget.py` 的 `IterationBudget` | 参数归 `01` §3 |
| 2 | 上下文装配 | 每轮发给模型的原文由哪些块拼成 | `agent/prompt_builder.py`、`agent/system_prompt.py`、`agent/prompt_caching.py`；项目上下文文件白名单 `agent/coding_context.py` 的 `_CONTEXT_FILES`（`AGENTS.md` / `CLAUDE.md` / `.cursorrules`），且只收录该目录下真实存在者（同文件 `context_files=[c for c in _CONTEXT_FILES if (root / c).is_file()]` 一处）；整体开关 `init_agent()` 的 `skip_context_files` 参数（`agent/agent_init.py`） | 五档预算记账表归 `19` §4 |
| 3 | 上下文压缩 | 逼近窗口上限时丢什么、留什么 | `agent/context_compressor.py`：默认阈值 0.50（`hermes_cli/config.py` 的 `DEFAULT_CONFIG["compression"]`）、小窗模型下限 0.75（`_SMALL_CTX_WINDOW_LIMIT` 一带）且**只升不降**（`_effective_threshold_percent()` 用 `max()` 实现）；引擎抽象 `agent/context_engine.py` 的 `ContextEngine` | 引擎职责归 `13` §2.1 |
| 4 | 记忆与状态 | 跨会话留什么、落在哪个文件 | `hermes_state.py`：默认库 `DEFAULT_DB_PATH`（`$HERMES_HOME/state.db`）、`SessionDB` 类、`FTS_SQL` / `FTS_TRIGRAM_SQL` 两张全文检索表的 DDL、运行期能力探测 `_sqlite_supports_fts5()`、损坏修复 `repair_state_db_schema()`；长期记忆 `agent/memory_manager.py`、后端抽象 `agent/memory_provider.py` | 根性描述归 `00` §4；换后端归 `02` §13；检索机制归本篇 §8 |
| 5 | 工具面 | 模型这一轮能看见哪些工具、以什么顺序看见 | `toolsets.py`：`TOOLSETS` 注册表、`resolve_toolset()`、`create_custom_toolset()`，其中 `return sorted(tools)` 保证同一份配置必得同一份工具列表（提示缓存前缀才不会白丢） | 57 集清单唯一归 `03` |
| 6 | 权限与审批闸门 | 哪个动作必须先问人、答案交给谁 | `tools/approval.py`、`tools/write_approval.py`；回调注入点 `tools/terminal_tool.py` 的 `set_approval_callback()`，且回调存在线程本地（`_callback_tls = threading.local()`，见 GHSA-qg5c-hvr5-hjgr 注释）；插件侧边界 `hermes_cli/plugins.py` 的 `VALID_HOOKS` 处 "Observers only: return values are ignored. Plugins cannot veto or …"，以及文档串指向 `tools.approval.request_tool_approval` 的那段 | 闭环设计归 `02` §7.2、`03` §2 |
| 7 | 循环护栏 | 重复失败、重复无进展时是否强制停 | `agent/tool_guardrails.py`：`ToolCallGuardrailConfig` 的阈值字段、`IDEMPOTENT_TOOL_NAMES` 与 `MUTATING_TOOL_NAMES` 两个工具名集合；构造点 `agent/agent_init.py` 内 `agent._tool_guardrails = ToolCallGuardrailController(` 一处 | 幂等/写面语义归 `19` §3 |
| 8 | 执行隔离 | 命令跑在你这台机器上还是别的机器上 | `tools/environments/`（`BaseEnvironment` ABC，另有 local/docker/singularity/modal/managed_modal/daytona/ssh 实现）；选择变量在 `tools/terminal_tool.py` 的 `_get_env_config()` 里 `env_type = os.getenv("TERMINAL_ENV", "local")`，合法值见同文件未知后端的错误提示（local / docker / singularity / modal / daytona / ssh） | Windows 侧实测口径归 `03` §3.4 |
| 9 | 错误恢复 | 一次调用失败之后按什么顺序重来 | `agent/retry_utils.py`、`agent/turn_retry_state.py`；重试次数 `agent.api_max_retries`（`agent/agent_init.py` 内 `_raw_api_retries = _agent_section.get("api_max_retries", 3)`，默认 3），SDK 自带重试被显式关掉（`agent/agent_runtime_helpers.py` 的 `create_openai_client()` 内 `client_kwargs.setdefault("max_retries", 0)`）；凭证池刷新计数每轮清零（`agent/conversation_loop.py` 的 `run_conversation()` 内 `agent._auth_pool_refresh_counts = {}`，注释指向 issue #26080）；文件快照 `tools/checkpoint_manager.py` 的 `CheckpointManager`（默认关闭见 `hermes_cli/config.py` 的 `DEFAULT_CONFIG["checkpoints"]`） | 降级契约归 `21` §5 |
| 10 | 可观测与评估 | 这轮跑得好不好，谁看得见 | 16 个回调参数（`run_agent.py` 的 `AIAgent.__init__` 签名）；23 个生命周期钩子 + 4 类中间件（`hermes_cli/plugins.py` 的 `VALID_HOOKS` / `VALID_MIDDLEWARE`，全清单见 §4.2）；批量评测 `batch_runner.py`（并行跑数据集 + trajectory 落盘 + 工具使用统计）；过程落盘 `hermes_state.py` | 事件词汇归 `01` §4.1；用例资产归 `20` |
| 11 | 技能与知识注入 | 怎么把"这类活该怎么干"喂给它 | 技能目录 `$HERMES_HOME/skills/`（`tools/skills_hub.py` 的 `_skills_dir()`）、仓库内技能随项目根生效；装配 `build_skills_system_prompt()` 与 `agent/skill_utils.py` 的前置过滤；准入检查 `tools/skills_guard.py`、`tools/skills_ast_audit.py` | 结构与生效时机归 `02` §10；索引与触发判据归本篇 §8 |
| 12 | 编排与调度 | 多 Agent 与定时任务怎么跑起来，单轮跑完要不要再跑一轮 | 委托 `tools/delegate_tool.py`、`tools/async_delegation.py`、`tools/delegation_live_log.py`；工作队列 `tools/kanban_tools.py`；定时 `tools/cronjob_tools.py` + `hermes_cli/cron.py` + `cron/scheduler.py`（`tick()`，gateway 每 60 秒调一次）+ `plugins/cron_providers/`；对应钩子 `subagent_start/stop`、`kanban_task_claimed/completed/blocked`；**多轮循环** `hermes_cli/goals.py`（`GoalManager` / `judge_goal()` / `GoalContract`） | 要不要编排的判据归 `21` §4；**继续还是停由谁判、验收面与预算归本篇 §9** |

**读表方式**：拿到一条要求，先在第三列里找它的部件。找到，说明这件事在 harness 里有位置；
**找不到**（例如"每轮硬限 900 秒墙钟"），说明它落在你这一侧（外层调用者的超时），不要去包里找开关。

---

## 3. 最小 harness 与生产 harness：Hermes 已经把哪几块做完了

这一层可以分两档评估：**最小可用四块**（能跑完一轮对话）与**生产必需再加的四道工序**（能拿去交付）。
这个分法在 Hermes 上的用法和别处不同——
**它不是"你要不要补"的清单，而是"你已经有了但没接线"的清单**。逐条对照：

**最小四块（库内已实装，无需你写）**

| 块 | Hermes 实现 | 你仍要做的动作 |
| --- | --- | --- |
| System Prompt（这轮的身份与规矩） | `agent/system_prompt.py` + `agent/prompt_builder.py`；`ephemeral_system_prompt` 参数在真正发请求前整段追加（`agent/conversation_loop.py` 里 `if agent.ephemeral_system_prompt:` 一带） | 决定业务段落在哪一层注入（`19` §4.3 段式），别和 SOUL 混写 |
| Tool Definitions（工具怎么被描述给模型） | `toolsets.py` + `tools/registry.py` 自注册；`resolve_toolset()` 输出排序后列表 | 减法配置（`enabled=None` + `disabled`，R4） |
| Tool Execution（调用真的落地执行） | `agent/tool_executor.py`，含范围强制（越界调用在钩子与护栏之前就被拒，同文件注释 "reject before hooks/guardrails/dispatch" 一处） | 业务工具自己的错误语义（`20` §3） |
| Tool Loop（拿结果再问一轮，直到收敛） | `agent/conversation_loop.py` 的 `run_conversation()`，轮次推进条件在该函数内的 `while` 一句 | 显式设 `max_iterations`，禁止吃默认值 |

**生产四工序（库内有机制，但默认不生效或不完整）**

1. **错误处理**：重试链在库内（§2 部件 9），但**默认只有 3 次 API 重试，没有业务级降级**。四类降级契约要你自己写（`21` §5）。
2. **沙箱**：六个 `TERMINAL_ENV` 后端都在，默认 `local`，即命令直接跑在你的机器上。而且这条选择**走环境变量不走 YAML**——
   详见 §4.3 边界 D，这是本篇最要紧的一条实测结论。
3. **多 Agent 编排**：`delegate_task` 与 Kanban 两套机制在库内（§2 部件 12），但**要不要用是业务判断**，判据归 `21` §4，本篇不重复。
4. **定时任务**：`hermes_cli/cron.py` + `tools/cronjob_tools.py` 是 CLI/网关形态的能力。路线①（进程内）想定时，
   定时器是你自己的进程职责。

一句话结论：**换模型之前先把这四道工序的接线补上**。在 Hermes 上，"换一副 harness 比换两代模型更有效"
这类说法的正确读法是"你已经有 harness 了，缺的是把它接到你的治理面上"，不是"自己再造一副"；
至于它作为效果结论是否成立，本篇不采信，理由见 §5 第三类。

---

## 4. 可改边界三档

三档按**改造后升级时的存活概率**排序：A 档随 `pip install -U` 完好，B 档在扩展面 API 不变时完好，C 档每次升级都要重做。
判档不是偏好问题：升级会不会把改动冲掉，决定你答不答应这个需求、报多少工时。

### 4.1 A 档：配置行就能改的（0.19.0 实测可读）

`config.yaml` 由 `hermes_cli/config.py` 的默认表兜底（每个键都能在默认表里查到形状与默认值，
`grep -n '"compression"' -A20 hermes_cli/config.py` 这类检索比读文档快且不会漂）。本篇只登记"harness 层的主开关键名与读取位置"，
不重述取值语义（各键语义的唯一归属仍是 §2 末列指出的那几篇）：

| 键 | 管哪个部件 | 读取位置 |
| --- | --- | --- |
| `agent.api_max_retries` | 9 | `agent/agent_init.py` 的 `init_agent()` 内 `_raw_api_retries = _agent_section.get("api_max_retries", 3)`（默认 3） |
| `agent.max_turns` | 1 | **仅网关侧读**：`gateway/run.py` 的 `_current_max_iterations()` 取值后作为 `max_iterations=` 传进构造。迭代上限本身是**构造参数**（`agent/agent_init.py` 的 `init_agent()` 签名 `max_iterations: int = 90`，默认 90），YAML 里没有 `agent.max_iterations` 这个键——进程内路线想改它，只能在建 `AIAgent` 时显式传 |
| `compression.*`（`threshold` / `target_ratio` / `protect_last_n` / `protect_first_n` / `hygiene_hard_message_limit`） | 3 | 默认表 `hermes_cli/config.py` 的 `DEFAULT_CONFIG["compression"]`；阈值下限逻辑 `agent/context_compressor.py` 的 `_effective_threshold_percent()` |
| `context.engine` | 3 | `agent/agent_init.py` 的 `init_agent()` 内 `_engine_name = _ctx_cfg.get("engine", "compressor")` 一带（默认值即 `"compressor"`） |
| `tool_loop_guardrails.*` | 7 | `agent/agent_init.py` 内 `ToolCallGuardrailController(` 的构造处（传 `ToolCallGuardrailConfig.from_mapping(...)`）；可写键的形状见 `hermes_cli/config.py` 的 `DEFAULT_CONFIG["tool_loop_guardrails"]` |
| `terminal.*`（`backend` / `cwd` / `timeout` / `env_passthrough` / `home_mode`） | 6 / 8 | 默认表 `hermes_cli/config.py` 的 `DEFAULT_CONFIG["terminal"]`；**但工具实际读 env，见边界 D** |
| `plugins.enabled` | 10 / 11 / 12 | `hermes_cli/plugins.py` 的 `_get_enabled_plugins()` 与 `_discover_and_load_inner()` 内 `enabled = _get_enabled_plugins()` 一处 |
| `checkpoints.*` | 9 | `hermes_cli/config.py` 的 `DEFAULT_CONFIG["checkpoints"]`；构造参数 `run_agent.py` 的 `AIAgent.__init__` 签名（`checkpoints_enabled: bool = False`） |
| `memory.write_approval` / `skills.write_approval` / `display.memory_notifications` | 4 / 11 | 见 `00` §4 自进化循环条目与 `08` |

### 4.2 B 档：官方扩展面（不改包源码）

**这是唯一有兼容承诺的一档。** Hermes 的插件发现有四条来源，写在 `hermes_cli/plugins.py` 的模块 docstring 开头：
打包插件（`<包>/plugins/<name>/`，其中 `memory/` 与 `context_engine/` 两个子目录被排除、走各自的发现路径）、
用户插件（`~/.hermes/plugins/<name>/`，即 `$HERMES_HOME/plugins/`）、项目插件（`./.hermes/plugins/<name>/`，需 `HERMES_ENABLE_PROJECT_PLUGINS` 显式打开）、
pip entry-point 插件（`hermes_agent.plugins` group）。**后加载者按同名覆盖前者**（docstring 原句：
"a user or project plugin with the same name as a bundled plugin replaces it"）——
这一条给了你一个不动 wheel 就能替换打包插件的能力，但它只覆盖插件层，覆盖不到 `agent/`、`tools/` 里的核心模块。

**注意默认值**：除打包的平台插件外，其余插件**默认不加载**（`hermes_cli/plugins.py` 的 `_discover_and_load_inner()` 内注释 `None = opt-in default (nothing enabled)`，
判定逻辑 `:1454-1468`，未启用时提示语是 `run hermes plugins enable <name>`）。
路线① 最常见的第一次失败不是插件写错，是没把它写进 `plugins.enabled`。

`register(ctx)` 能拿到的注册面，0.19.0 共 **18 个 `register_*` 方法**（`hermes_cli/plugins.py` 的 `PluginContext`，机器枚举）：
`register_tool` · `register_hook` · `register_middleware` · `register_context_engine` · `register_platform` ·
`register_skill` · `register_command` · `register_cli_command` · `register_auxiliary_task` · `register_secret_source` ·
`register_web_search_provider` · `register_browser_provider` · `register_image_gen_provider` · `register_video_gen_provider` ·
`register_tts_provider` · `register_transcription_provider` · `register_dashboard_auth_provider` · `register_slack_action_handler`。
业务集成里真正常用的是前四个。**记忆后端不在这 18 个里**：`plugins/memory/` 用自己的发现路径，
插件的 `register(ctx)` 收到的是 `_ProviderCollector`（`plugins/memory/__init__.py` 的 `class _ProviderCollector`，源码注释自称 "Fake plugin context"），
它只接 `register_memory_provider`，`register_tool` / `register_hook` / `register_cli_command` 全是空实现——
**记忆后端插件顺手注册业务工具是无效的**，这一点和 `02` §13 的写法要连着读。
其余是给平台适配器与供应商替换用的，路线① 基本用不到。

**两类拦截面，语义差别很关键**（这是"能不能拦住"的分水岭）：

- **钩子（observer）共 23 个**：`pre_llm_call` · `post_llm_call` · `transform_llm_output` · `pre_api_request` · `post_api_request` ·
  `api_request_error` · `pre_tool_call` · `post_tool_call` · `transform_tool_result` · `pre_verify` · `pre_approval_request` ·
  `post_approval_response` · `pre_gateway_dispatch` · `on_session_start` · `on_session_end` · `on_session_finalize` · `on_session_reset` ·
  `subagent_start` · `subagent_stop` · `kanban_task_claimed` · `kanban_task_completed` · `kanban_task_blocked` · `transform_terminal_output`。
  注册未知名字不报错、只 warn（`register_hook` 仍存下来以便前向兼容）。
- **中间件（behavior-changing）共 4 类**：`llm_request` · `llm_execution` · `tool_request` · `tool_execution`。
  docstring 明说分界：request 类可以改写真正发出去的载荷，execution 类可以包住真实回调；
  工具请求中间件在库内被实际调用于 `agent/tool_executor.py` 的 `execute_tool_calls_concurrent()`（内 `_apply_tool_request_middleware_for_agent(` 调用）
  与 `agent/agent_runtime_helpers.py` 的 `invoke_tool()`（内 `apply_tool_request_middleware(` 调用）。

讨论这一层时还会遇到一套"工程位点"命名：工具网关 / 调用拦截 / 反馈装配 / 上下文状态管理 / 异常处理。
这五个词在 Hermes 上不是五个新名词，逐一对应到 `tool_request`+`tool_execution` 中间件、`pre_tool_call`、
`transform_tool_result`、`context.engine` 插槽、`api_request_error` + 部件 9 的重试链。
**在本机可核对的清单面前，任何位点说法都只是别名**，写方案时给文件名，别给别名。

**已经装好、可直接换的供应商面**：`plugins/memory/` 目录里随 wheel 装了 8 个后端
（byterover / hindsight / holographic / honcho / mem0 / openviking / retaindb / supermemory），加内置默认；
`plugins/` 顶层另有 `context_engine` · `cron_providers` · `model-providers` · `platforms` · `web` · `browser` ·
`image_gen` · `video_gen` · `observability` · `security-guidance` 等插槽目录。
**插槽有货没货要逐个查**：`plugins/context_engine/` 目录里只有 `__init__.py`，即 0.19.0 的 wheel 内没有任何第三方上下文引擎可选——
该机制的第一个抽象方法是 `name`（`agent/context_engine.py` 的 `ContextEngine` 里 `def name(self) -> str:`，docstring 举例 'compressor'、'lcm'），它必须与 `context.engine` 的配置值完全一致才会被认（`agent/agent_init.py` 的 `init_agent()` 内 `if _candidate is not None and _candidate.name == _engine_name:` 一处）。
装第三方引擎（官方文档举的例子是外部仓库 `hermes-lcm`）走插件面，并且**不会自动激活**，必须显式写 `context.engine`。

### 4.3 C 档：改包源码才动得了的硬边界

以下四条在本机读源码确认，全部**没有配置出口**。它们的共同点是"看起来像参数，其实是策略"。
写需求时把这四条当作已知物理限制，不要留成"待调研"。

**A. 新增一种 `api_mode`（接一个上游没有的协议）**
`agent/agent_init.py` 的 `init_agent()` 里有一处内联白名单（`if api_mode in {"chat_completions", "codex_responses", "anthropic_messages", "bedrock_converse", "codex_app_server"}:`），
不在集合内的一律落到同一函数的 `else` 分支 `agent.api_mode = "chat_completions"`。配置传什么都不产生第四、第六种模式。
另有一处整轮接管：`api_mode == "codex_app_server"` 时 `run_conversation` 在进循环之前就 `return agent._run_codex_app_server_turn(...)`
（`agent/conversation_loop.py`，注释 "Default Hermes path is bypassed entirely"），这是目前唯一的"换掉整个 runtime"入口，
且它是上游加的，不是你加的。
（顺带一条已核实的口径问题：同文件 `init_agent()` 的 docstring 在 `api_mode` 参数处只列了前两种取值，与上面那行代码不一致。
本技能 `01` §3 的 api_mode 行以代码为准，`references/api-reference/` 是上游原文的逐字副本、不改。）

**B. 把压缩阈值调到小窗模型的 0.75 以下**
`compression.threshold` 可以填任意小数，但 `agent/context_compressor.py` 的 `_effective_threshold_percent()` 对上下文窗口小于
`_SMALL_CTX_WINDOW_LIMIT`（512K）的模型执行 `return max(threshold_percent, 0.75)`——**只升不降**（源码注释原话 "raise-only"）。
填 0.3 的实际效果是 0.75。
想真正提前压缩，可动的是 `target_ratio`、`protect_first_n`/`protect_last_n`，或者换引擎（§4.2 末）；
而换引擎之后，主机侧阈值连同那条自动抬高的通知一起失效——`agent/agent_init.py` 的 `init_agent()` 内 `agent.context_compressor = _selected_engine` 之后
那段注释明确写了外部引擎 "own compaction policy … never reaches the plugin"（并把 `_compression_threshold_autoraised` 置空，注释挂 issue #44439）。
**这条是"配置项存在但不生效"的典型形态**，第 6 步的证伪动作就是为它准备的。

**C. 改变"哪些工具算幂等 / 哪些算写"**
`agent/tool_guardrails.py` 的 `IDEMPOTENT_TOOL_NAMES` 与 `MUTATING_TOOL_NAMES` 是两个硬编码 `frozenset`（各 16 项）。
数据类 `ToolCallGuardrailConfig` 的字段允许从构造函数传入，但**唯一的构造路径**是 `agent/agent_init.py` 的 `init_agent()` 内
`ToolCallGuardrailController(` 那一处，它调的是 `ToolCallGuardrailConfig.from_mapping(config["tool_loop_guardrails"])`——
而同文件 `from_mapping()` 只逐字段构造八个阈值与开关，**根本不传这两个集合**。也就是说 YAML 里写 `idempotent_tools: [...]` 不会被读到。
后果要说白：你的业务工具默认既不在幂等集也不在写集里，护栏的"幂等无进展"这条判定对它不成立；
能被配置的只有六个阈值和两个开关（`warnings_enabled`、`hard_stop_enabled`，默认后者为 `False`，即**默认只提示不拦**）。

**D. 让 `terminal.backend: docker` 在进程内路线里生效**
这条是安全语义，必须写全。`tools/terminal_tool.py` 的全部终端设置**读 `os.environ` 的 `TERMINAL_*`，不读 YAML**
（`_get_env_config()` 内 `env_type = os.getenv("TERMINAL_ENV", "local")`）。YAML 到 env 的桥由启动器做：CLI、网关、TUI/dashboard 各自在启动时桥一次。
跳过这些路径的进程——源码注释点名了 `hermes serve`、桌面应用内的进程内 agent、cron ticker、ACP——
"used to silently fall back to the local backend even when config.yaml selects `terminal.backend: docker`,
running commands on the host the user intended to sandbox"，注释挂着四个 issue 号（#63141 #54449 #61115 #65696）。
现在的补救是同文件的 `_ensure_terminal_env_bridged()`，它只在 `TERMINAL_ENV` **未设置**时补，
且"Explicit env always wins"。给你的落地口径三句：
① 进程内路线要容器执行，就在你自己的启动代码里显式设 `TERMINAL_ENV=docker`，不要指望 YAML 生效；
② 设了 `TERMINAL_ENV` 之后桥接函数直接返回（同函数内 `if "TERMINAL_ENV" in os.environ or _terminal_config_bridge_attempted:`），你的显式选择永远优先；
③ 后端不可用时它是**记日志返回 False**（同文件 `check_terminal_requirements()`，未知后端的错误提示在同一函数的分支里），
不是抛异常带走界面——所以隔离是否真的生效，必须在验收里单独证。

**关于 `hooks:`（shell 钩子）的一条待验项，如实登记**：`agent/shell_hooks.py` 的 `register_from_config()`
在 0.19.0 包里只有三个调用点——`cli.py`、`gateway/run.py`、`hermes_cli/main.py` 三处的启动准备函数内。
纯库模式没有任何东西调用它，因此**配了 `hooks:` 也不会生效**。这个函数是 public、可在宿主进程里自己调用，
但它有三重前置：先看 `_resolve_effective_accept()`（认 `--accept-hooks` / `HERMES_ACCEPT_HOOKS=1` / `hooks_auto_accept: true`，
`accept_hooks=True` 跳过 TTY 询问）、再过 `_is_allowlisted()`（未获同意就记 warning 并 skip）、
以及最前面的 `HERMES_SAFE_MODE=1` 直接整体跳过（安全模式下一条用户自定义代码都不执行，插件、MCP、钩子全算）。
宿主自调用的端到端效果本技能**未实测**，
按 `07` 的"未实测不宣称"红线，只登记事实与探针，不写结论。探针（在你自己的 venv 里跑，不碰包）：

```python
from agent.shell_hooks import register_from_config
specs = register_from_config({"hooks": [...]}, accept_hooks=True)  # 返回真正接上的 spec 列表；空列表即未生效
```

---

## 5. 另一根分层轴、通道与知识的分工、不写进方案的三类数字

这一层业界说法很多，本篇不逐条引述：凡无法在本机核对的表述，写进本篇就等于让下游拿它当依据。
下面三格只留下三类有影响的东西——分层用哪根轴、通道与知识各管什么、哪些数字不能当判据。取材规则一句话：
**能在源码里翻到位置、或在本机跑出返回值的才写进判据，其余一律不采信。**

**（一）本篇按"代码归属"轴分层。** 判断一个部件在不在 harness 里只看一件事：对应那行代码在不在 `site-packages` 里。
在——属于 harness；不在——它是模型权重与推理服务，或者你写的业务工具。这根轴**逐行可判定**，所以第 ⑥ 步问
"这条要求落在哪一层"永远能回答到一个文件名。另一根常见的轴按**控制回路拓扑**分层（谁观测、谁执行、谁反馈），
把模型本身算进回路当"控制器"、把环境状态当被控对象。两根轴量的是不同东西，不能混进同一张表：拓扑轴的归属取决于
你把哪一层画成被控对象，换个画法结论就跟着变，不可判定。本篇不采用它，但保留它唯一有用的那条提醒——
**部件 7（循环护栏）与部件 10（可观测与评估）合起来才构成反馈回路**，只接其中一个环就闭不上，审第 ⑥ 步时按这条查一遍。

**（二）"通道"与"知识"各管一半，别拿一侧的话回答另一侧的问题。** 一种说法是 harness 只是管道、可沉淀的业务知识
才是护城河；另一种把它当一门独立工程学科。两句各覆盖一半对象：对**交付出去的业务系统**，护城河确实是第 ① 步盘出来的
业务契约与口径（归 `19`），harness 是通道；对**这一期工程的成败与工时**，成本几乎全在通道形状上——§4.3 四条硬边界
没有一条源于"知识不足"，四条全是通道形状造成的。本篇因此只做通道这一侧（在哪、能改到哪一档、怎么证），
知识那一侧一律指向 `19`，两侧不互相代答。

**（三）三类数字不进入判据，也不写进方案。** ① 外部项目的效果性数字：投入人数、历时几个月、合并多少 PR、
省百分之多少时间——本机不具备复现条件。② 跨层比较的说法："换一副 harness 比换两代模型有效""换个框架能提速 N 倍"——
被比较的两侧不同量纲，没有可信分母。③ 工具与厂商自己给的吞吐宣称。
本篇出现的数字只有两种来源：**在源码里数出来的常量与条目数**（可按本篇给的符号名复数一遍），
以及 **§6 动作 2 那条本机可跑的返回值**；
第 ⑦ 步取证也只认这两种。方案里一旦出现第三类数字，按 `07` 的"未实测不宣称"红线退回原处。

---

## 6. 实操：一条改造要求进来，按四步定档

**输入**：业务方或验收表里的一条 harness 级要求（判据：它约束的是"怎么跑"而不是"跑什么"，见 §1 边界）。
**产出**：一行定档结论 + 一个可演示的验证证据 + 需要时的工时改判。
出口判据在动作 4 末尾。**顺序不可换**：跳过动作 2 直接写代码，是本篇 §4.3 那四条硬边界存在的唯一原因。

1. **定位部件**。用 §2 第三列找到这条要求属于哪个部件；找不到就判定它落在外层调用者（例如墙钟超时），
   记为"包外"，后面三步不用再走。
2. **证伪"可插"错觉**（必做，10 分钟内可完成）。三种查法，任一命中即得结论：
   - 查默认表看键是否存在：`grep -n '"你要配的键"' <site-packages>/hermes_cli/config.py`；
   - 查是否真被读：从键名反查读取点，`grep -rn '<键名>' <site-packages>/agent/ <site-packages>/tools/`，
     **读代码里的那一处，不读 docstring**——§4.3-A 与 D 都是 docstring 与实现不一致的位置；
   - 跑起来看效果：设一个小窗口模型跑一次长对话，直接打印实际生效值。压缩阈值的实例（本机可跑，不写文件）：
     ```python
     from agent.context_compressor import ContextCompressor
     f = ContextCompressor._effective_threshold_percent
     f(128_000, 0.30)   # 期望 0.30，实际 0.75 —— 阈值不可下调的证据
     f(600_000, 0.30)   # 大窗口时 0.30 保留
     ```
     静态查到的"只升不降"与这一行调用返回值合起来才算证据（`07` 的取证口径）。
3. **按 A → B → C 顺序选方案**（越靠前升级越安全，与 `02` §9 的"选面顺序"是同一条判据在 harness 层的复述）：
   A 档能表达就写配置行，并按 `19` §7 第 6 张表登记它属于哪个入口；A 档表达不了再看 B 档 18 个 `register_*`，
   并确认该注册面对你的路线**真的会被调用**（§4.2 的 `plugins.enabled` 默认值就是最常见的失效点）；
   两条都不通才允许谈 C 档。
4. **谈 C 档就要交代价**。三条必写：动的是哪个文件哪个函数（§4.3 给了四个候选位置）、
   下次升级怎么重放（fork 分支或 post-install 脚本，各自怎么在 `06` 的打包链里保住）、
   以及**这条改动是否已经作为需求反馈上游**——`02` §15 的红线是"改核只在极端情况、且不鼓励"，
   本篇给的是它的操作版本：能举出 §4.3 里的机制证据说"确实没有出口"，才允许立项改核。
   出口判据：这一步的结论要能被现场演示——一次真实调用返回 §4.3 所说的值，或一条日志证明护栏确实在默认配置下只提示不拦。

**禁止**三件事：把提示词当强制（§1 末，软约束不产生拦截，强制在部件 6/7）；
在路线① 里假定 YAML 生效（§4.3-D 是本篇给这条判据的实测来源）；
把 §5（三）列出的三类不可复现数字写进方案。

---

## 7. 与主线八步的对应

| 主线位置 | 用本篇哪一节 | 解决什么 |
| --- | --- | --- |
| 〔入场检查〕 | §4.3 各条的位置 + §10 复核方法 | 版本升级后确认哪几条硬边界还在原位 |
| 第 ② 步 定形态 | §4.3-D、§3 生产四工序 2 | 选了进程内路线就别提容器隔离，除非打算自己设 env |
| 第 ③ 步 跑通内核 | §3 最小四块、§2 部件 1 | 六条硬性规定背后的循环结构 |
| 第 ③ 步 跑通内核（多轮） | §9.1–§9.4 | 要不要跑多轮、验收面写在哪、预算封在哪、异步任务怎么等 |
| 第 ⑤ 步 赋业务 | §4.1 / §4.2（B 档 18 个注册面）、§2 部件 5 | 业务能力接到哪个面上，接错面就白写 |
| 第 ⑥ 步 立闸门 | §2 部件 6/7、§4.3-C、§4.3-D③ | 强制动作发生在哪一层，默认是拦还是只提示 |
| 第 ⑦ 步 取证 | §6 动作 2、§10 | 每条 harness 级断言的现场演示方法 |
| 第 ⑧ 步 交付 | §6 动作 4 | 若本期有 C 档改动，交付包里必须带重放说明 |

**判据归属**：本篇只交付"部件在哪、能改到哪一档、怎么证"这三件事，
外加跨轮的"继续还是停由谁判、验收面在哪"（§9）。
扩展面选序与改核红线仍以 `02` §9 与 §15 为准；能力行为语义以 `08` 为准；审批闭环设计以 `02` §7.2 为准；
断言与用例设计以 `20` 为准。与本篇重复的表述以那几篇为准，本篇是它们在 harness 层的定位工具。

---

## 8. 检索机制：模型这一轮能"找到"什么，由哪一层决定

部件表回答的是"要求落在哪个部件"，本节回答另一个方向的问题：**一轮对话里，模型凭什么东西找到该用的东西**。
这四件事都在 harness 内，都归你决定，但机制完全不同——一个是延迟加载，一个是关键词全文检索，
一个是外部后端预取，一个是索引常驻、按需取正文。**混成一句"它有检索能力"就没法验收了**，因为四者的失败形态互不相同。

先给结论，再逐条落到符号名。**核心层没有向量检索**：按 0.19.0 `RECORD` 列出的 793 个 `.py` 逐个检索，
`faiss` / `hnsw` / `milvus` / `weaviate` / `pinecone` / `sqlite-vec` 均零命中；
`chroma`、`qdrant`、`cosine` 命中的全部在 `plugins/` 下（图像抠像的 chroma key、mem0 插件的向量库选项等），
核心模块里 `embedding` 的 25 个文件命中也是同形异义（`max_position_embeddings`、Unicode 双向控制符的 "embedding"、
文本嵌入某参数），**没有一处是检索用的向量索引**。所以本节讲的四条都是字面意义上的定位：BM25、SQLite FTS5、目录索引、ripgrep。

**（一）工具面的延迟加载（Tool Search）**。工具定义本身要占提示词，装几百个工具就会挤掉对话。
Hermes 的做法是先把工具拆成两堆（`tools/tool_search.py` 的 `classify_tools()` 与 `is_deferrable_tool_name()`）：
**核心工具永远留在明面上，可延迟的收进目录，由三个"桥接工具"按需调用**。判定规则只有一条：
工具名不在 `toolsets._HERMES_CORE_TOOLS` 里、且能在注册表查到条目，就算可延迟（`mcp-` 前缀的算在内，
但核心工具即使来自插件 toolset 也**不延迟**，源码注释说明这是为了防止意外遮蔽）。本节列的四类检索工具
（`search_files` / `session_search` / `skills_list` / `skill_view`）**全在核心表里，永远不会被延迟**。

**什么时候真的延迟，由一个阈值闸门决定**（`should_activate()`）：默认 `enabled="auto"`、`threshold_pct=10.0`，
即"可延迟工具的 schema 估出的 token 数达到上下文窗口的 10% 才启用"；token 数按 **字符数除以 4** 粗估
（`estimate_tokens_from_schemas()`，源码注释说这只需数量级准确）。拿不到上下文窗口时退回固定 2 万 token 阈值。
注意这三条默认值都可配（`ToolSearchConfig`），但**闸门只管"是否启用"，不管"启用后召回路不对"**。

**启用之后怎么找**：`search_catalog()` 用 BM25 打分，**k1=1.5、b=0.75**（`_bm25_score()` 的默认参数），
是**自己内联实现**的、没引外部检索库（源码注释的理由是目录规模小，工具数通常不到 500）。
可检索文本由 `_entry_search_text()` 拼：**工具名（下划线、点、横线、冒号都拆成词）+ 描述 + 顶层参数名**，
**schema 正文被刻意排除**（docstring 原话 "indexing them adds noise without improving recall in our measurement"）——
所以按参数值或参数说明里的词去搜是搜不到的，能搜的是"这个工具大概干什么"。
BM25 全零分时回落到工具名子串匹配，源码注释说明这解决的是"查询词每篇文档都有、IDF 归零"的情形。
**一个对你的验收有用的判据**：工具描述写得越准，召回路越准；把关键信息只写在参数说明里，这个工具就等于搜不到。

**（二）会话的关键词全文检索（Session Search）**。跨会话找东西靠 SQLite FTS5，不是向量。
`hermes_state.py` 维护两张虚拟表：`messages_fts`（默认分词器）与 `messages_fts_trigram`（`tokenize='trigram'`），
两张表都由 `messages` 表上的触发器维护，索引内容是 **content + tool_name + tool_calls 三列拼接**。
trigram 那张是为中文准备的，源码注释写明默认分词器会把 CJK 拆成单字、导致短语匹配失效，trigram 生成 3 字节重叠序列后
任意文字的子串查询都能原生工作——**中文场景要检索会话，认准这张表**。
能不能用不是看文档而是**运行时探测**：`_sqlite_supports_fts5()` 临时建一张 fts5 探针表再删掉，失败就降级并告警。
查询侧是 `search_messages()`，用 `MATCH` 匹配并用 `snippet()` 回摘命中片段，trigram 表有对应的降级路径。
对外的封装是 `tools/session_search_tool.py`，三种用法：**DISCOVERY**（给 `query`，按会话血缘去重后返回片段 + 前后文 + 首尾）、
**SCROLL**（给 `session_id` 与 `around_message_id`，返回该点上下窗口，继续滚动就锚到窗口首尾消息）、
**BROWSE**（不给参数，按时间列最近会话）。它有两条**排序与过滤**上的设计值得你在评估长期记忆时照抄：
子代理与工具来源的会话默认**不参与**检索（`_HIDDEN_SESSION_SOURCES = ("subagent", "tool")`），
cron 会话**参与但降权**（`_DEMOTED_SESSION_SOURCES = ("cron",)`）——注释里记着原因：定时任务会大量堆积
重复词汇，在纯 BM25 下把用户自己的会话挤出结果，造成"想不起来"（源码注释引用 issue #19434）。
**这解释了一件事**：这类召回盲区不是模型问题，是排序问题。

**（三）记忆的外部后端预取（Memory Provider prefetch）**。`agent/memory_provider.py` 定义 `MemoryProvider(ABC)`，
0.19.0 的契约里与检索相关的有两个方法：`prefetch(query, *, session_id="")` 在**每次 API 调用前**被调用，
返回要注入的文本；`queue_prefetch(query, ...)` 在**每轮结束后**调用，为下一轮准备，
默认是空实现——**这一对"预取下一轮"的设计是否生效，取决于后端有没有实现它**。
调用点在 `agent/turn_context.py`（每次组装轮次时 `prefetch_all()`，注释写明它跑在工具循环之前），
编排在 `agent/memory_manager.py`（`prefetch_all()` / `queue_prefetch_all()`）。
注入时不是把裸文本贴进去，而是 `build_memory_context_block()` 包成 `<memory-context>` 围栏并加一句系统说明，
大意是"以下是召回的记忆上下文，不是新的用户输入，按权威参考数据对待"；
该函数还会 `sanitize_context()` 一遍，若后端已自己包过围栏就剥掉并告警。
**失败形态**：这一层是外部后端，缺凭证或后端不可用时由 provider 自己的 `is_available()` 在初始化时判定，
不是检索不到、而是**整层没有**；所以验收要问的是"这轮有没有 `<memory-context>` 块"，不是"答得准不准"。
**同时注意一个限制**：`MemoryManager` 允许**同时只有一个外部后端**（模块 docstring 明确写了拒绝第二个并告警，理由是防止工具 schema 膨胀与后端冲突）。

**（四）技能是索引常驻、按需取正文**。这一点最容易记反：`build_skills_system_prompt()` 进系统提示的
**是一份压缩索引**（按分类列出技能名与描述），**不是全部 SKILL.md 正文**；正文要靠模型自己调 `skill_view` 取。
索引有两层缓存（进程内 LRU + 磁盘快照 `.skills_prompt_snapshot.json`，按 mtime/size 清单校验）。
**哪些技能会出现在索引里，由条件决定**（`_skill_should_show()`）：frontmatter 里的
`requires_tools` / `requires_toolsets` 不满足就不显示，`fallback_for_tools` / `fallback_for_toolsets` 命中就隐藏
（有主工具时不让兜底技能露出来）；平台维度由 `skill_matches_platform_list()` 过滤。
**所以"技能装了却不生效"要分三层查**：frontmatter 条件是否满足 → 平台过滤是否通过 → 是否被禁用列表挡掉。
**这条对你的交付有直接影响**：技能正文不进提示词，意味着它**不占常驻预算**，
但也意味着**模型得自己决定去读它**——描述写得含糊，技能就永远不会被触发。

**（五）文件与代码检索**。核心工具 `search_files` 优先用 ripgrep，**没有 ripgrep 时回落 Python 实现**。
这一条与本节其余四条不同：它不进任何目录、也不走 BM25，就是普通的文件内容搜索。

**把四条并起来看，可导出一条验收判据**：这四层的检索质量**都由你写下的东西决定**——
工具描述（决定 BM25 召不召回）、会话写入与来源标记（决定 FTS5 排不排得进来）、
外部记忆后端（决定 `<memory-context>` 有没有内容）、技能描述与 frontmatter（决定索引与触发）。
模型换得再强，这四处的写法不变，召回结果就不变。**这一节不构成"要不要上向量库"的建议**，
本篇只给已核实的事实：`hermes-agent==0.19.0` 的核心层不提供向量检索，你要用只能走 `02` §13 的记忆后端插件面自己接。

---

## 9. 多轮编排：单轮跑完之后，由谁决定要不要再跑一轮

前面几节讲的都是**一轮之内**的事：工具怎么给、护栏怎么拦、检索怎么找。
本节讲跨轮的那一层——一轮结束后，**继续还是停，这个判断由谁作出**。
这一层在 `hermes-agent==0.19.0` 里归 `hermes_cli/goals.py`（模块 docstring 自称 "Persistent session goals"），
是本篇唯一一处"谁来当循环体"的落点。

### 9.1 一圈是怎么转的

| 拍 | 谁做 | 落点 |
| --- | --- | --- |
| 目标由人设定 | 人 | `/goal` 命令；文本可含结构化验收契约（见 9.2） |
| 执行一轮 | 主 Agent | 正常对话轮，走 `agent/conversation_loop.py` |
| 判断该不该继续 | **独立的 judge（辅助模型）** | `judge_goal()` |
| 把"继续"喂回同一会话 | 框架 | `CONTINUATION_PROMPT_TEMPLATE` 系列，作为普通 user 消息追加 |
| 状态落到对话之外 | 框架 | `GoalState` 存 `SessionDB` 的 `state_meta` 表，键 `goal:<session_id>` |

**关键的一条设计**（`goals.py` 模块 docstring 写明）：续轮提示**就是一条普通 user 消息**，
不改系统提示、不换工具集——**所以提示词缓存不被打断**。这条决定了多轮循环不会让每轮的提示重建成本线性上涨，
是它能撑住长循环的前提。`GoalManager` 与 CLI、网关两侧是同一套实例（docstring 明说本模块对 `cli.HermesCLI`
与 gateway runner 都没有硬依赖，两边各自接进同一个 `GoalManager`）。

### 9.2 验收面：结构化完成契约

验收标准是整个循环能不能收敛的唯一根据。`goals.py` 把它做成一个可选的结构化对象
`GoalContract`，五个字段（`_CONTRACT_FIELDS`）：

- `outcome`（要达成什么）、`verification`（怎么证明达成了）、`constraints`（不可破坏的约束）、
  `boundaries`（范围边界）、`stop_when`（卡住什么条件下停并上报）。

来源有两条：**手写**——`parse_contract()` 支持行内语法，在 `/goal` 文本里写
`verify: ...` / `constraints: ...` / `stop when: ...`，`_CONTRACT_ALIASES` 给了二十多个别名
（`evidence`、`proof` 归 verification；`must not`、`do not change` 归 constraints；`files`、`scope` 归 boundaries；
`give up when`、`blocked` 归 stop_when）；**自动展开**——`/goal draft` 调 `draft_contract()`，
用一句大白话让辅助模型生成契约，失败时**回落到无契约的自由目标**，不因此卡住设目标。

契约为空时行为与无契约完全一致（`GoalContract.is_empty()`），这是向后兼容的关键。
**契约存在时的效力**由 `judge_goal()` 的 docstring 写明：judge 严格按 `verification` 判 DONE，
且**违反 `constraints` 时拒绝完成**。同一个契约块还会拼进续轮提示
（`CONTINUATION_PROMPT_WITH_CONTRACT_TEMPLATE`），大意是"声称完成前先满足 Verification 并给出具体证据
（命令输出、文件内容、测试结果）"——**同一份契约同时管住执行方与验收方**，这是它比单纯加提示有效的原因。

### 9.3 停止条件：不只是"完成/未完成"

`judge_goal()` 返回的是**四值**元组 `(verdict, reason, parse_failed, wait_directive, transport_failed)`，
不是二值。`verdict` 有 `done` / `continue` / `wait` / `skipped`（judge 调不通时）。

**`wait` 这一态是本节最值得抄的设计**。`JUDGE_SYSTEM_PROMPT` 对它的界定很克制——
只在"下一步动作是等异步工作"而非"该继续干"时才用，且必须给出一个具体载荷：

- `wait_on_session`：给会话 id，进程退出**或** `watch_patterns` 命中即醒，适配长驻 watcher；
- `wait_on_pid`：给 pid，进程退出即醒；
- `wait_for_seconds`：给秒数，作退避用。

提示词里明写了一句反滥用约束：不要因为"还有活没干"就选 WAIT，只在"现在戳它一下纯属空转"时才用。
**这条把"该等"和"该继续"分成两个可判定分支**，而不是让控制器自己去判断该不该等——
这正是控制论里传感器该干的事：返回足够具体的信号，控制器就不必猜。

等待期由 `GoalState` 的四个字段承载（`waiting_on_pid` / `waiting_on_session` / `waiting_until` / `waiting_reason`）。
在等待期里，`evaluate_after_turn()` 直接短路返回 `verdict="waiting"`、
`should_continue=False`，**不消耗轮次、不调 judge**；等进程退出、模式命中或墙钟时间到了才恢复正常判定。
也可由 `/goal wait <pid> [原因]` 手工挂起、`/goal unwait` 解除——手工入口**只接受 pid**，
`wait_on_session` 与 `wait_for_seconds` 两种载荷只能由 judge 给出（`GoalManager` 上有对应方法，
但 CLI 与网关的 `/goal` 分发只暴露了 pid 这一种，见 `hermes_cli/cli_commands_mixin.py` 的 `/goal` 分发段）。
`gather_background_processes()` 取的是 `process_registry` 的实时会话快照，所以 judge 看到的是当下真实在跑的东西。

### 9.4 预算：两层封顶，互不相通

多轮循环至少有两个独立的消耗闸门，**不要混为一谈**：

| 闸门 | 符号 | 默认 | 管什么 |
| --- | --- | --- | --- |
| 轮次预算 | `DEFAULT_MAX_TURNS` | 20 | `/goal` 循环转多少轮 |
| 迭代预算（父） | `IterationBudget`，来自 `max_iterations` | 90 | 主 Agent 工具循环转多少步 |
| 迭代预算（子） | `IterationBudget`，来自 `delegation.max_iterations` | 50 | 每个子代理各自的步数上限 |

后两项由 `agent/iteration_budget.py` 的 `IterationBudget` 类 docstring 写明，`DEFAULT_MAX_TURNS` 是
`hermes_cli/goals.py` 的模块常量。要注意一句容易漏的：
**子代理各有独立预算，父子合计可以超出父的上限**。`execute_code`（程序化工具调用）的迭代会经 `refund()` 退还，
不占预算。

### 9.5 失败方向：fail-open 及其代价

`judge_goal()` 明确 fail-open——judge 调用失败返回 `("continue", ...)`，docstring 写明理由
"A broken judge must not wedge progress; the turn budget is the backstop"（坏掉的 judge 不能把进展卡死，
轮次预算才是最后防线）。配套两道自动刹车：

- `DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES = 3`：judge 连续返回空/非 JSON 达 3 次即自动暂停，并提示去改 `auxiliary.goal_judge` 配置；
- `DEFAULT_MAX_CONSECUTIVE_TRANSPORT_FAILURES = 5`：连续传输失败（401/超时/DNS/连接错误）达 5 次同样自动暂停。

**解析失败与传输失败是分开计数的**，注释写明传输错误是偶发的、不计入前者。
**这整组设计防的是"发散"**（judge 坏了导致循环停不下来、把预算烧光），代价是**它不防"收敛到错误状态"**
——judge 判 done 但实际没做完，循环会带着自信停下。校验这一层不能只靠它（见 `07` 的红线与 `20` 的验收做法）。

### 9.6 judge 用哪个模型：默认是主模型

`DEFAULT_CONFIG["auxiliary"]["goal_judge"]` 的默认值是 `"provider": "auto"`、`"model": ""`。
`draft_contract()` 的 docstring 写明这是 "main-model-first, cache-safe"——同模型可复用父会话的提示缓存。
`judge_goal()` 与 `draft_contract()` 都经 `agent/auxiliary_client.py` 的 `call_llm()`（`task="goal_judge"`），
所以 `auxiliary.goal_judge.*`（provider/model/base_url/timeout/reasoning_effort）都能配。

**所以默认状态下 judge 与执行方是同一个模型**，独立性靠"不同提示 + 独立调用"而非"不同模型"来获得。
`hermes_cli/tips.py` 里给的反面建议是路由到一个便宜快的小模型把循环成本压到最低。
**这是一个真实的取舍，不是疏漏**：省下的是缓存与成本，付出的是执行方与验收方共享同一套偏好。
若你的验收面要求强独立（见 9.7 的判据），必须在 `auxiliary.goal_judge.model` 显式配一个不同模型——默认值不会给你分离。

### 9.7 何时该用多轮，何时该停

本节给的是判据，不是推荐。**先回答一个问题：你要的"完成"，能不能写成一条不需要你盯着就能拒绝坏结果的检查？**
能不能，循环才有验收面；不能，"完成"就只是主观判断，此时多轮循环只会把主观判断重复很多遍。

用与不用的边界，按缺口看：

| 需求 | 0.19.0 现状 | 落点与依据 |
| --- | --- | --- |
| 有界目标、多轮推进、到验收面为止 | 有 | `/goal` + 契约（9.2）+ 轮次预算（9.4） |
| 异步任务未完时不空转 | 有 | `wait` 三种载荷（9.3） |
| 跨会话续跑 | 有 | `state_meta` 落盘，`/resume` 接得上（9.1） |
| 定时/事件触发 | 部分 | `cron/scheduler.py` 的 `tick()` 由 gateway 每 60 秒调一次；它是**独立的定时任务体系**，与 `/goal` 循环不联动 |
| 让循环自己发现"这轮该做什么" | **无** | 循环内容完全由人给的 goal 文本决定；没有"读 CI 失败 / 未关闭 issue"这类信号源 |
| 并行子任务的文件系统级隔离 | **无** | `tools/delegate_tool.py` 给子代理的是独立 `task_id`、独立终端会话、独立文件操作缓存，**不是** git worktree。改动落在共享工作目录时不存在目录级隔离 |

**这张表的用法**：需求落在"有"那几行，用 `/goal` 就够，不必自己造编排；
落在最后两行，说明你要的东西 0.19.0 没有对应实现，**不要靠改 `/goal` 的提示词去凑**——
那是把缺失的部件当提示词问题处理。先按 §6 的四步定档，确认是 B 档（插件）还是 C 档（改核）。

**并行那一行要特别当心**：子代理各有独立 `task_id` 与终端会话，**不等于**写入路径互斥。
多个子代理同时改同一个工作目录时，冲突发生在文件系统层，`task_id` 挡不住。
真要并行改同一仓库，得自己保证目录分离（`hermes_cli/projects_cmd.py` 与 `tui_gateway/project_tree.py`
里的 worktree 相关代码属项目管理与界面，不是子代理隔离面）。

### 9.8 与本篇其余部分的关系

本节不改变 §4 的任何结论，只补一个跨轮视角：

- **单轮内的强制点仍在部件 6/7**（§2 部件表第 6、7 行），续轮是普通 user 消息，不绕过护栏——这一条
  由 `goals.py` docstring 的"不改系统提示、不换工具集"直接保证。
- **检索机制（§8）在多轮里不重跑**：记忆预取在每次 API 调用前触发，续轮同样吃 `<memory-context>`；
  技能索引仍常驻，续轮不需重新 `skill_view` 已读的正文。
- **判据归属**：本节只交付"多轮由谁判定、验收面在哪、预算封在哪、状态存在哪"；
  断言与用例设计归 `20`，护栏与审批闭环归 `02` §7.2。

---

## 10. 版本与核实方法

- 本篇全部结论针对 **`hermes-agent == 0.19.0`**，核对环境是本机已安装的包目录（`site-packages`），
  不是 GitHub 上的最新源码。包版本以 `python -c "import importlib.metadata as m; print(m.version('hermes-agent'))"` 为准。
- **位置标识一律用符号名，不用行号**：文件 + 函数名 / 类名 / 常量名。行号会随上游每次改动整体漂移，符号名不会。
  复核一条结论只需两步：`grep -n "符号名" 文件名` 定位，再读那一处代码。形如 `DEFAULT_CONFIG["compression"]`
  这类下标定位也照此办理（先 grep 常量名，再在该常量块内找子键）。
  §4.3-A（api_mode 白名单）、§4.3-B（阈值只升不降）、§4.3-C（`from_mapping()` 不读工具名集合）、
  §4.3-D（终端设置读 env）四条是下一版本最可能变的位置，升级后优先复查这四条；
  §8 的四条检索机制同样是易变位置，升级后按那一节的符号清单逐条对一遍；
  §9 的多轮编排在下一版本也需重点复查四处——`auxiliary.goal_judge` 的默认 `provider`
  （若上游改成默认用独立小模型，本篇 9.6 的取舍描述要改写）、`GoalContract` 的字段集
  （`_CONTRACT_FIELDS` 增删会让 9.2 的行内语法表失效）、`IterationBudget` 的两个默认值、
  以及 9.7 那张表里标"无"的两行（发现信号源、子代理目录级隔离）——**若上游补上了，这张表要改**。
- §9 里两处"不存在型"结论同样只对被核过的版本成立，建议升级后按同一路径复查：
  `goals.py` 的模块 docstring 明说续轮不改系统提示、不换工具集，这是"续轮不绕过护栏"这条结论的依据；
  子代理隔离那条按 `tools/delegate_tool.py` 的 `DELEGATE_BLOCKED_TOOLS` 与 task_id 机制判定，
  **不要用"grep 不到 git worktree"就下结论**——`hermes_cli/` 与 `tui_gateway/` 里确有 worktree 代码，
  但那是项目管理与界面，不是子代理隔离面，判定依据是"子代理拿到的是 task_id 还是目录"。
- **这条规则有明确边界**，全库扫过一遍确认：`references/`、`docs/`、`SKILL.md` 里的行号引用已全部改掉；
  余下带行号的只落在两处，**都不受本篇口径约束**——
  ① `references/api-reference/` 是 `scripts/gen_api_reference.py` 从上游 docstring 逐字转录的产物，
  里面的 `file.py:1310` 是**上游原话**，改它等于篡改被引材料，要改只能改上游；
  ② `CHANGELOG.md` 是按版本累积的改动记录，条目里的行号记录的是**当时那次核对的位置**，
  随代码演进失效是预期内的，重写它等于伪造历史。两者都不作为现行判据使用。
- 两处**已知上游自身不一致**，本篇按代码而非 docstring 记录：`agent/agent_init.py` 的 `init_agent()` docstring 在
  `api_mode` 参数处少列三种取值；`hermes_state.py` 的全文检索用标准库 `sqlite3`（模块顶部 `import sqlite3`）
  并在运行时探测能力（`_sqlite_supports_fts5()`），
  hermes-agent 自己的 793 个模块里没有一处 `import apsw`（按 `RECORD` 逐文件核实，命中 0；
  本机 site-packages 里另有无关的第三方 `apsw` 包，不构成引用关系）。
  本条同时是 `02` §13 一处归因的更正依据。
- §8 中"核心层无向量检索"这一条同样是**穷举核实**得出的：按 `RECORD` 的 793 个 `.py` 检索
  `faiss` / `hnsw` / `milvus` / `weaviate` / `pinecone` / `sqlite-vec` 全部零命中。升级后这条需要重跑，
  因为它是一条"不存在"型结论，**只对被核过的那个版本成立**。
- 未核实的部分本篇明确说未核实：§4.3 末宿主自调 `register_from_config()` 的端到端行为、
  `TERMINAL_ENV=docker` 在 Windows 上的可用后端组合。这两条按 `07` 红线不给结论，只给探针。
- §9 全节为**静态读码**得出，未实跑一次完整多轮循环。要取现场证据，最省事的一条是：
  设一个带契约的 `/goal`（写明 `verify:` 一行），观察续轮提示是否按契约带出验收面、
  以及 `last_verdict` / `turns_used` 是否按预期推进——这两个值都落在 `state_meta` 表里，可直接读。
