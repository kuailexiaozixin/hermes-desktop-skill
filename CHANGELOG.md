# CHANGELOG
## [1.7.31] — 2026-08-19

- **00-index §1.1 检索地图补登 3 项官方既有能力（只索引、不转录，防漂移）**：
  - **Tool Search**：MCP/插件工具的 agent 级渐进披露（`tool_search`/`tool_describe`/`tool_call` 三桥接工具、分层披露、内置核心工具从不延迟）；进程内直跑路线可用，内置 57 工具集的减法原则归属不变（`03` §1）。
  - **Delegation / Kanban worker lanes**：进程内子 Agent 委托经 `delegation` 工具集（已在 `03` §2 基线内）+ `Configuration › Delegation` 覆配（模型/并发/深度/worktree 隔离）；Kanban worker lanes 为跨进程持久工作队列形态。
  - **A2A (Agent-to-Agent)**：入站（Agent Card / JSON-RPC / SSE / push notifications）走网关路线，归属 `16-gateway-package.md`；出站 `a2a` 工具集官方文档标注各进程类型可用，但不在 0.19.0 基线 57 工具集表内——用前先核实实装版本 `TOOLSETS` 注册情况。
  - 配套：§1.3「不适用」速记补 `A2A 入站` 关键词；§5 单真相源映射表补「A2A / Delegation / Tool Search 能力语义」归属行（归官方 llms-full 章节，后续新增专题 reference 先迁归属）。
  - 背景：外部归档对比报告（`D:\WPS灵犀过程文件\pydantic-ai与hermes-desktop技能对比及完善建议.md`）P0 索引补全项；官方 A2A/Tool Search 章节于 [1.7.25] 文档更新时已入库，本次补登检索索引。
  - 纯文档（索引）改动，无 Python/JS 变更。
- SKILL version 1.7.30 → 1.7.31。

- **修复示例 EXE 进程递归崩溃（严重）**：`examples/01-hermes-desktop/连接系统/main.py` 与 `Agent系统/launcher.py`
  增加三层守卫——① 代码执行沙箱子进程（`HERMES_RPC_SOCKET`，在本进程执行脚本后退出）；② `.py` 脚本子进程
  （`frozen + argv[1] 为 .py` 但无 RPC 标记 → 直接退出）；③ `RD_MAIN_PID` 递归/多实例熔断器。
  防止 EXE 打包后 Hermes 内核 `execute_code` 用 `sys.executable` 递归派生，导致进程指数增长（3→191）、
  内存耗尽、系统濒临崩溃。验证：frozen 模式四场景（脚本子进程/沙箱/熔断/主实例）全部通过。

## [1.7.30] — 2026-08-17

- **三系统解耦架构（高内聚低耦合工程级落地）全量融入**（L1-L5，见 `references/18-tristructure-architecture.md`）：
  - **L1 理念文档**：新增 `references/18-tristructure-architecture.md`——三系统（业务/连接/Agent）拆分 + 两层高内聚低耦合（系统间依赖铁律 `业务→连接→Agent` + 系统内部模块内聚），含决策判据、落地步骤、底座三步替换法、验证门禁、反模式红线。
  - **L2 决策引导**：SKILL.md §5 主流程新增「⓪ 架构形态决策」步骤（单工程内嵌默认 / 三系统分离判据）；§8 扩充「高内聚低耦合（工程组织 + 模块设计两层）」原则（含系统内部模块：单一职责/模块分层/共享抽取/死代码清理）。
  - **L3 示例骨架**：在 `examples/01-hermes-desktop` 基础上搭建三系统骨架（不新增 04）——`业务系统/`（纯业务 app.py + 启动.bat + README）、`连接系统/`（bridge.fuse_business_into_agent + main.py + README）、`替换Agent系统.md`（底座三步替换法）；01 根 README 新增「三系统组织」说明。
  - **L4 原则铁律**：依赖方向 / 底座零差异可替换 / 连接唯一装配点 / 系统内部模块内聚，落进 §8。
  - **L5 门禁清单**：新增 `scripts/verify_tristructure.py` 三系统验证门禁（业务纯净 / 连接唯一装配点 / 独立入口 / 底座纯净；未启用三系统则 SKIP）；`docs/delivery-checklist.md` 新增 A2 三系统交付验收项；SKILL.md 登记 18 号文档入 MOC C 类 + 门禁脚本表。
  - SKILL version 1.7.29 → 1.7.30。

## [1.7.29] — 2026-08-16

- **00-index 融合「系统架构基线」进 §4 事实基线（顶层地图）**：
  - 在 §4 事实基线新增「系统架构基线（顶层地图）」子块（与「自进化学习循环」并列）：分层主干（Entry Points → AIAgent 统一内核 → Session Storage / Tool Backends）、核心数据流、工具发现依赖链（import 时自注册）、6 条设计原则，并归属导航到各模块清单（`10`/`12`/`13`/`14`/`16`）。
  - 未新增独立章节、未新建文件；剔除与 `14` §3「Library 全貌收口」重复的子系统归属表，单真相源映射表补充「系统架构基线 = 00-index §4」归属行。
  - 内容源自官方架构页（System Overview / Directory Structure / Data Flow / Major Subsystems），以进程内视角精炼，不重复模块清单。
- SKILL version 1.7.28 → 1.7.29。

## [1.7.28] — 2026-08-16

- **删除 `references/18-self-improvement.md`，自进化理念精炼融入 `00-index.md`（不留痕迹）**：
  - `00-index.md` §2 定位新增「Hermes 的根性」一句：内置自进化学习循环（self-improving agent / "The agent that grows with you"），决定集成姿态为「会积累的数字同事」而非无状态 API。
  - `00-index.md` §4 事实基线新增「自进化学习循环（根性机制基线）」，精炼陈述后台 self-improvement review（fork 独立 AIAgent / 独立 prompt cache）、冻结快照注入、consent-aware 写审批、不可变核心等机制基线，并归属 `memory`/`skill_manage` API（`01`/`13`）、能力语义（`08`）、GUI 落地（`02`），避免重复。
  - `SKILL.md` 清理对 18 的两处引用（MOC 总览 A 聚类主导节点 + A 核心 API 表行），自进化入口改由 `00-index.md` §4 承担。
  - 说明：CHANGELOG 历史条目中提及 18 的变更事实保留不动（版本审计）。
- SKILL version 1.7.27 → 1.7.28。

## [1.7.27] — 2026-08-16

- **聚焦 hermes 自身，移除全部与 pydantic-ai 的能力对标内容**（此类对比后续单独归档，不再混入技能文档）：
  - `references/00-index.md` 删除 §8「与同类框架（pydantic-ai 等）能力对标速查表」。
  - `references/02-integration-core.md` 移除「等价 pydantic-ai 依赖注入 + 类型化 Output」表述，改为纯 hermes 描述。
  - `references/09-integration-e2e.md` §8/§9 移除与 pydantic_evals、pydantic-ai 测试替身 model 的对比表述。
  - `references/13-agent-modules.md` §2.2 移除「对标 pydantic-ai Embeddings」表述。
  - 说明：CHANGELOG 既有历史条目（记录过去对标 pydantic-ai 的变更事实）保留不动，以维护版本审计与 version 联动门禁。
- **llms-full 检索地图上移至 `00-index.md` §1（最优先）**：完整版自 `references/10-hermes-cli.md` §5 移入 `00-index.md` §1，
  `10-hermes-cli.md` §5 改为指向 `00-index.md` §1 的指引，避免重复与漂移；更新 §5 单真相源映射表（新增 llms-full 检索地图归属行）。
- 重排 `00-index.md` 章节编号：检索地图 §1 → 定位 §2 → 阅读顺序 §3 → 事实基线 §4 → 单真相源 §5 → 交叉引用 §6 → 参考实现 §7。
- SKILL version 1.7.26 → 1.7.27。


## [1.7.26] — 2026-08-16

- **修复 `scripts/track_upstream.py` 上游漂移检测缺陷**：原 `check_docs` 的 `drift` 只对比「本地 vs 出厂基线」，导致本地==基线时 `--update-docs` 不触发、**无法发现官网更新**。
  - `--update-docs` 改为**无条件下载官网最新文档**并与本地对比后覆盖（自动备份 + 更新 `references/docs-baseline.json`）。
  - 普通检查增加**上游探测**：官网有新版本（即使本地==基线）时报告 `UPSTREAM` 并提示运行 `--update-docs`。
- **文档二次更新**：`hermes-llms-full.txt` 更新到官网最新 md5 `2d0253cc…`（此前 56f8849b…）。
- SKILL version 1.7.25 → 1.7.26；`track_upstream.py` 语法与行为已验证。

## [1.7.25] — 2026-08-16

- **上游文档漂移更新**：`hermes-llms-full.txt` 从出厂基线（md5 `4a51fb…` / 3,273,648 B）更新到官网最新（md5 `56f8849b…` / 3,775,696 B），新增 A2A、ACP Host Integration、Buzz、Egress 凭据注入代理（iron-proxy）、Desktop Native Sign-In (RFC 8252)、Document Extraction、Codebase Ownership Map 等章节。
- 依据官网 `https://hermes-agent.nousresearch.com/docs/llms-full.txt` 下载；写入 `references/docs-baseline.json` sidecar 作为新基线。
- PyPI 版本仍为 `hermes-agent==0.19.0`，源码签名 / API 参考无破坏性漂移（track_upstream ③④ 通过）。

## [1.7.24] — 2026-08-15

- **新增 `references/18-self-improvement.md`（自进化 / 学习循环设计理念主题文档）**：
  - Hermes 根性设计——AI 失忆症 → 内置学习循环（每 10 提示存记忆 / 每 10 工具迭代沉淀技能）→ consent-aware 写审批 → 「越用越强」。
  - 记忆与技能分工、`write_approval` / `memory_notifications` 配置、profile/备份/容器不可变等运维理念。
  - GUI 集成落地要点：学习循环状态区 / 写审批接入现有审批闭环 / 记忆技能可视化。
- **SKILL.md**：A 核心 API 区登记 `18-self-improvement.md`，version 1.7.23 → 1.7.24。
- 依据：Hermes 官方文档全文（hermes-llms-full.txt）+ 公开资料交叉核验。

## [1.7.23] — 2026-08-15

- **examples/01 上下文管理面板（对照 13 §2.1 上下文压缩引擎）**：
  - 新增 `context_provider.py`：`context.engine` 选择（读/写 config.yaml `context.engine`）+ 压缩状态
    （基于 models.dev `context_window` 估算 threshold_tokens + 会话 token 水位判定 should_compress，
    引擎可加载实例时补真实 compression_count 等运行时字段）+ token 跟踪（sessions usage_input/output）；
    任一能力不可用时优雅降级。
  - `routes/misc.py` 新增 3 个 API：`GET /api/context/engines`、`POST /api/context/engine`、`GET /api/context/status`。
  - `routes/pages.py` 新增 `navContext` 侧栏按钮 + `view-context` 容器；
  - `static/src/views.js` 新增 `renderContextView` 面板（引擎切换下拉 + 压缩状态/token 跟踪 + 进度条）。
- **门禁**：`check_endpoints`（新路由被前端引用）/ `quality_check`（6 步）/ `test_bridge` 全绿。

## [1.7.22] — 2026-08-15

- **examples/01 记忆增强（对照 13 §2.2 分层记忆系统）**：
  - 新增 `memory_providers.py`：provider 列表/切换（读/写 config.yaml `memory.provider`）、
    向量检索（holographic MemoryStore + FactRetriever 混合检索 FTS5+Jaccard+HRR）、
    分层查看（记忆文件 + holographic facts 按 category + active provider）；任一能力不可用时优雅降级。
  - `routes/misc.py` 新增 4 个 API：`GET /api/memory/providers`、`POST /api/memory/provider/switch`、
    `GET /api/memory/search`、`GET /api/memory/layers`。
  - **路由冲突修复**（真实浏览器 playwright-cli extension 测试发现）：`POST /api/memory/provider` 会被既有动态路由
    `POST /api/memory/{fname}` 按注册顺序捕获（把 provider 当文件名报「非法记忆文件名」），改为三段路径
    `/api/memory/provider/switch` 避开单段 `{fname}`；前端 `views.js` 同步。
  - `static/src/views.js` 记忆面板增强：Provider 切换下拉 + 向量/语义检索框 + 分层查看。
- **门禁**：`check_endpoints`（新路由被前端引用）/ `quality_check`（6 步）/ `test_bridge` 全绿。

## [1.7.21] — 2026-08-15

- **改写 15 §4bis（/v1/runs 异步审批协议）为聚焦自身**：移除与 pydantic-ai Deferred Tools 的全部对比表述，
  聚焦 hermes 自身的 `waiting_for_approval` 状态机、审批机制与 GUI 对接范式；标题由「Deferred 审批对接范式」改为「GUI 审批对接范式」。
- **门禁**：纯文档改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_endpoints` 全绿。

## [1.7.20] — 2026-08-15

- **移除 15-api-server.md §6bis（AG-UI / 前端框架对接）与 §6ter（内置 WebUI examples/03）**：
  - §6bis、§6ter 两小节从 15 章移除，§6 客户端接入后直接衔接 §7 进程内自建；
  - 同步清理引用：00-index §8 能力对标表 AG-UI 行（15 §6bis → 15 §6）、SKILL.md §4 MOC 描述（移除 §6bis 字样）。
  - 保留：SKILL.md §4 与 00-index §6 对 examples/03 的内置参考实现引用（不依赖 15 §6ter）。
- **门禁**：纯文档改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_endpoints` 全绿。

## [1.7.19] — 2026-08-15

- **把 `examples/03-nesquena-hermes-webui` 纳入内置参考实现引用**：
  - SKILL.md §4 资源与导航补 examples/03 条目（本地适配 WebUI，`from run_agent import AIAgent` 驱动，Windows 原生 `start-webui.bat` / `start.ps1` 端口 8787）；
  - 00-index.md §6 修正为「内置参考实现」第三项；
  - 15-api-server.md §6ter 改写为以本地示例为主（GitHub 为上游来源），补 Windows 原生启动方式。
- **门禁**：纯文档改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_endpoints` 全绿。

## [1.7.18] — 2026-08-15

- **新增 15-api-server.md §4bis「/v1/runs 异步审批协议（Deferred 审批对接范式）」**：
  - 专题化 `queued → running → waiting_for_approval → done` 状态机 + SSE events + POST /approval；
  - 明确等价 pydantic-ai Deferred Tools 审批流，给出 GUI 业务对接审批的四步范式（启动→监听→弹审批→提交决策）。
- **新增 15-api-server.md §6ter「第三方 WebUI 生态：nesquena/hermes-webui」**：
  - 介绍开源第三方 Web 界面（17k+ stars，CLI 1:1 对等，纯 Python+vanilla JS），含快速启动与 SSH tunnel 访问；
  - 00-index.md §6 同步补充「第三方 WebUI 参考」引用。
- **门禁**：纯文档改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_endpoints` 全绿。

## [1.7.17] — 2026-08-15

- **精简 SKILL.md frontmatter `description`（去除实现细节冗余，提升路由可读性）**：
  - description 收敛为「定位 + 触发场景 + 触发词 + 反触发」四要素，删除安装命令、5 条技术路线、多宿主列表、能做什么能力清单、权威事实来源、旗舰参考实现等实现细节。
  - 冗余内容迁移至正文：正文引言区新增「能做什么」能力清单小节与「权威事实来源」小节。
- **门禁**：纯文档（元数据）改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_endpoints` 全绿。

## [1.7.16] — 2026-08-15

- **优化 SKILL.md frontmatter `description`（提升触发路由准确性）**：
  - 定位凝练为「**对接集成引擎**」（复制 examples 底座→接进应用→门禁收尾，非从零开发框架）。
  - 触发场景扩展至**业务系统对接智能体**（用户主场景），而不只限「桌面 GUI」。
  - `能做什么` 纳入 1.7.14/1.7.15 新增能力：强类型结构化输出（`PluginLlm.complete_structured`）/ 多模态输入 / 业务上下文注入。
  - 触发词补充：业务系统对接智能体、AI 对话面板、工具调用可视化、GUI 集成 Agent。
  - 反触发修正歧义：原「纯脚本无 GUI 的非集成调用」改为「不涉及对接/集成 hermes 内核的纯脚本调用、仅用 CLI 无需集成」，避免误伤无 GUI 的业务集成场景。
- **门禁**：纯文档（元数据）改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_endpoints` 全绿。
## [1.7.15] — 2026-08-15



- **依托 hermes 原生能力落地 P2 能力边界补强（对标 pydantic-ai，源码核实）**：

  - `references/13-agent-modules.md` §2.2 补**记忆检索的向量/语义语义**（源码核实 `plugins/memory/`）：检索是各记忆 provider 插件内部实现，hermes 不暴露统一 embedding API——`holographic` 用 HRR 向量+Jaccard/余弦相似度+信任加权打分（`retrieval.py`，带 `memory_banks` 向量表），`hindsight` 用 semantic+entity graph 多策略（`hindsight_recall`）；需向量召回选带向量检索的 provider 即可。

  - `references/15-api-server.md` 新增 **§6bis 与 AG-UI / 前端框架（Vercel AI SDK）的对接**：明确 hermes 走 OpenAI 兼容 `/v1`、不实现 AG-UI 协议；给出 Vercel AI SDK `createOpenAI({ baseURL })` 指向 hermes `/v1` 的等价对接路径与取舍。

  - `references/00-index.md` 新增 **§8 与同类框架（pydantic-ai 等）能力对标速查表**：标注 hermes 独有强项（57 工具集、记忆、护栏、渠道/IM 桥、网关）与待补边界（Embeddings 文档、Graph、AG-UI、Deferred Tools），让使用者一眼看清能力边界。

  - `SKILL.md` §4 同步更新 15-api-server 的 MOC 速查描述（含 §6bis）。

- **范围判断**：P2 建议中的「受限执行沙箱」经复核已被 `02` §7 审批闭环表（approval/write_approval/path_security/threat_patterns/slash_confirm）+ `13` §2.6（file_safety/tool_guardrails）**完全覆盖**，本轮不重复新增。

- **门禁**：纯文档改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_endpoints` / 文档链接全绿。

## [1.7.14] — 2026-08-15







- **依托 hermes-agent 原生能力补齐「结构化输出 / 多模态 / 业务上下文注入 / 输出评估」专题（对标 pydantic-ai，全部经 0.19.0 源码核实，不引入新依赖）**：



  - `references/01-library-api.md` §3.4 补透传机制（`request_overrides` 经 `api_kwargs.update(overrides)` 整体并入底层 provider 请求，支持 `response_format`/`extra_body`，`agent/transports/chat_completions.py`）；新增 **§3.4bis 结构化输出与多模态输入**——① 主 Agent 透传路径（`response_format` JSON Schema）；② **强类型路径 `PluginLlm.complete_structured()`**（`agent/plugin_llm.py`，自带 JSON Schema 校验 + `PluginLlmTextInput`/`PluginLlmImageInput` 图像输入）；③ 主 Agent OpenAI 风格多模态消息（`run_conversation`，`agent/conversation_loop.py` 自动剥离图像重试）。



  - `references/02-integration-core.md` §12 补 **`ctx.llm` 宿主推理**：`PluginLlm.complete/complete_structured` 完整签名表、JSON Schema 校验示例、信任门控（fail-closed + `plugins.entries.<id>.llm.*`），说明其等价 pydantic-ai「依赖注入 + 类型化 Output」——宿主把业务上下文注入插件、拿可解析可校验的结构化结果喂业务表单/流程。



  - `references/09-integration-e2e.md` 新增 **§8 Agent 输出评估**（LLM Judge 三段式：数据集→任务→评估，用 `ctx.llm.complete_structured` 强类型判分 + pass_rate 门禁衔接）与 **§9 离线确定性测试**（mock 回放无网验证链路/事件形状，依托 `test_bridge`，与 §8 在线 Judge 互补）。



  - `00-index.md` / `SKILL.md` §4 同步更新 01/02/09 检索与 MOC 速查描述。



- **门禁**：纯文档改动，无 Python/JS 变更；`quality_check`（6 步）/ `check_skill_gate` / 文档链接全绿。



## [1.7.13] — 2026-08-15















- **全面升级版本基线至 0.19.0**：本机实装 `hermes_cli.__version__ = 0.19.0`，按 0.19.0 源码逐一复核 `references/02-integration-core.md` 全部断言，与 `00-index.md` §3 事实基线对齐（含 1.7.12 遗留的 memory provider 机制）：







  - §5 能力→模块地图：47 个模块引用经 site-packages 核实 46 存在、1 处归属错误修正（`clarify` 实现模块 `agent.clarify_gateway` → **`tools.clarify_gateway`**）；TOOLSETS 交叉验证 33 capability 与地图 100% 一一对应。







  - §7.2 审批护栏：approval / write_approval / path_security / threat_patterns / tool_guardrails / slash_confirm 模块与符号全部核实存在；`_tool_use_enforcement` 为动态实例属性（agent_init.py:1532 设置、system_prompt.py:266 使用），断言成立；§7.3 确认无 `tools.office`/`tools.excel_tools`。







  - §11 `hermes mcp add` 参数集：name/--url/--command/--args(REMAINDER)/--auth(oauth|header)/--preset/--connect-timeout/--env 全部核实存在且语义一致（mcp.py:44-72）。







  - §13 Memory backend：`hermes_cli/memory_providers.py` 在 0.19.0 **已不存在**，改为 `plugins/memory/` 插件目录自动发现（bundled + `$HERMES_HOME/plugins/<name>/`）+ `hermes_cli/memory_setup.py` 交互配置 + `memory_oauth.py` OAuth；provider 标识更新为 byterover/hindsight/holographic/honcho/mem0/openviking/retaindb/supermemory；FTS5 澄清复核成立（agent/ 内无 fts5）。







  - §16 版本提示：删除「0.18.2 待统一」提示，统一为 0.19.0 基线说明。







- **路径一致性**：按 `05` 权威原则（HERMES_HOME 唯一真相、勿手写 `~/.hermes`）把 02（skills/plugins/memory 12 处）与 15（API_SERVER_KEY、profiles 2 处）的 `~/.hermes` 硬编码统一为 `$HERMES_HOME/`；08 的 docstring 直译保留不动。







- **门禁**：`check_skill_gate.py` / `check_api_signature.py` 全绿；文档链接断链 0。







- **修复 `check_endpoints.py` 对 `routes/` 包的误报（真实门禁 bug）**：该脚本原先只静态扫描 `main.py` 的 `@app.*` 装饰器，而示例 01 的路由早已迁入 `routes/` 包（chat.py / misc.py / ... 共 247 条），导致把已实现的 `/api/wiki`、`/api/kanban`、`/api/memory`、`/api/soul`、`/api/system-prompt`、`/api/workspace/*` 等全部误判为「前端引用了、后端未注册」的 404 隐患，错误阻断发布。修复：后端路由提取改为**递归扫描示例目录全部 `.py` 文件**（`main.py` 入口 + `routes/` 包），新增 `collect_py_files()`；同步更新模块 docstring 与 `07-quality-gates.md` 门禁表描述。修复后实测：247 后端路由全覆盖 232 前端引用，零未覆盖，退出码 0。此为本轮唯一既有失败门禁，现已归零。







- **SKILL.md §4 MOC 重构（地图索引去碎片化）**：将 §4 主题路由由「13 节点平铺列表 + 孤立文档表」重构为「4 个意图聚类 + 资源导航区」——A 核心 API 与库结构（01/10/11/12/13/14/16）/ B GUI 集成与能力（04/03/08）/ C 业务整合与路线选型（02/15）/ D 环境打包与质量（05/06/07/09），每文件唯一主导归属、交叉用途在正文标注；新增「资源与导航」区统一收纳 00-index（唯一权威）/ api-reference（签名）/ examples（参考实现）/ templates / docs / 门禁脚本表。修复原 ② 表格孤立于 MOC、13 节点平铺粒度不均与归属重叠问题。`00-index.md` 确立为唯一权威索引，MOC 只做「意图 → 入口文档」速查，二者分工不重复维护。















- **version 联动（release_gate 增强）**：把 version bump 纳入发布门禁，杜绝滞后——`release_gate.py` 新增 `[5] version_consistency` 硬门禁（校验 SKILL.md frontmatter `version` == CHANGELOG 最新 `## [x.y.z]`，不一致则硬阻塞），并新增 `--bump-version` 参数（从 CHANGELOG 最新版本自动写入 SKILL.md frontmatter）。已实测：不一致→报错退出码 1；`--bump-version`→自动修复；一致→通过退出码 0。同时修复 `release_gate.py` 既有编码 bug：`_run` 子进程未指定 encoding（Windows 默认 GBK），`track_upstream` 的 UTF-8 输出含不可断行空格时解码崩溃——已改为 `encoding="utf-8", errors="replace"`。















## [1.7.12] — 2026-08-15















- **references 文档去碎片化（按模块归位）**：把先前独立成篇的 6 篇 `agent` 包深度主题（原 17-context-compression / 18-memory-system / 19-usage-telemetry / 20-model-routing / 21-oneshot-batch / 22-safety-guardrails）并入 `references/13-agent-modules.md`，新增 `§2 深度主题`（2.1~2.6 六小节），删除 6 篇独立文件；`00-index.md` 阅读顺序表恢复 0–16 + api-reference(17)，人工 references 由 23 篇精简为 17 篇。更正工具护栏归属为 `agent.tool_guardrails`（非 tools 包）。







- **SKILL.md 工程化优化**：重构 frontmatter `description`（去正文化叙述、新增反触发条件、聚焦触发路由）；去重 §4 ② 中 `03-capabilities-and-toolsets` 重复行；`quality_check.py` 描述由「4 项」校正为「6 步」（+网页回归+文档链接）；`track_upstream.py` 描述由「PyPI+文档指纹」校正为「四线」（+源码签名+API 参考，含内容哈希比对）；`02-integration-core` 的「0.18.2 源码核实」标注改为中性「源码派生核实（版本见 00-index 事实基线）」，消除与 0.19.0 事实基线的版本不一致。







- **门禁**：纯文档改动，无 Python/JS 变更；`check_skill_gate.py` / `check_api_signature.py` 全绿。















## [1.7.11] — 2026-08-14















- **补齐「5 条 Library 调用路线平等化」在 `examples/` 对标文档组的漏改（承接 1.7.9/1.7.10 仅覆盖 `SKILL.md`+`references/`+`glossary` 的缺口）**。用户明令「除专门文件/章节外不强调不同路线、5 条路线平等可选无先后」——前两轮漏掉了 `examples/01-hermes-desktop/docs/gap/*` 整组对标文档及若干 examples 文档中的路线层级/互斥措辞，本次统一中性化：







  - `gap/gap-webui.md`、`gap/gap-hermes-studio.md`、`gap/gap-fathah.md`：档位 C 定义由「网关·Electron 专属，进程内路线不做」改为「依赖 Hermes 网关或 Electron 桌面壳运行时（与本示例单文件离线 EXE 形态不同，属可平等选用的其他路线；本示例当前未打包对应运行时）」；「明确不做 / 进程内 Library 路线无 / 架构互斥 / 本路线无」等层级与互斥措辞改为中性当前态（本示例当前未实现 / 依赖网关 / Electron 专属），保留事实（example 01 当前为单文件离线 EXE、能力当前未实现及其真实依赖）。







  - `gap/external-cases.md`：顶部「定位声明」改为 5 条平等路线总声明并加「不表示任一路线被排除或互斥」；总表「与本技能路线可迁移性」列去 `❌ 路线不同`/`路线互斥` 表述；§3「不可迁移/明确区分」、§4「不在本技能范围内」、§6/§7「路线互斥声明」、§6.4/§7.4「明确不可迁移（进程内路线剔除）」、以及「即路线错误」等全部改为「本示例当前形态 / 属可平等选用的其他路线形态 / 本示例当前未打包对应运行时」，纠正「本技能是进程内 Python Library 路线、其他路线被剔除」的层级框架。







  - 其余 examples 文档：`docs/mcp-server.md`（「本技能的核心设计原则 / 违背进程内原则 / 进程内路线无鉴权边界」→ 本示例单进程形态）、`README.md`（安全提示与「本技能断言」表行）、`docs/kanban-vs-symphony.md`（「违背进程内路线」→ 不符合本示例当前单进程形态）、`docs/a2a-audit.md` 与 `docs/gap/hermes-vs-frontend-coverage.md`（「桌面进程内路线不适用 / 不在本技能路线范围内」→ 本示例当前形态不适用）、`examples/02-.../skill-note.md`（「与本技能进程内路线互斥」→ 与 examples 当前定位不同，与其自身「并非互斥」声明一致）。







  - **保留**：`examples/` 代码注释（`sessions.py`/`util.js`/`state.js`/`pages.py`/`build.py`/`agent_runtime.py` 中关于「本示例为单文件离线形态、无 provider 账单/网关计费、强制 `disabled_toolsets=["terminal"]`」等）属对示例实际形态的 factual 描述，非路线层级断言，不改；`references/` 专门路线文件与 `02 §2 路径 D` 的逐条路线细节与互指保留。







- **回归核验**：全库 Grep 确认 `examples/` 与 `references/`+`SKILL.md` 已无「路线互斥 / 进程内路线无·不做 / 本技能是进程内 / 不在本技能范围内 / 明确剔除 / 违背进程内」等层级/互斥措辞（仅 `CHANGELOG` 历史叙述与 `07`/`SKILL.md` 中「反模式红线·触线即路线错误」质量门隐喻保留，二者非 Library 路线层级断言）。







- **门禁**：纯文档措辞改写，无 Python/JS 代码变更；`check_skill_gate.py` / `check_api_signature.py` 不受影响。















## [1.7.10] — 2026-08-14















- **去除非专门文件/章节中的「逐条路线枚举指针」（承接 1.7.9 的平等化收口）**。用户明令「除专门的文件或章节，不必特别指出不同路线」——1.7.9 在通用文档埋入的「见 10/15/16」「其余 4 条跨进程路线见 10/15/16」「spawn CLI 见 10 / API Server 见 15 / Hermes 网关见 16」等枚举式路线指针本轮从所有通用文档移除：







  - `SKILL.md`（定位块、`when_to_use`、`§2` 差异、`§3` 约束 5）：去掉逐条文件枚举与「其余 4 条路线」措辞，条件分支（选跨进程路线）统一改指 `references/02-integration-core.md §2 路径 D`。







  - `00-index`（§1 定位、§7.1 检索地图、§7.3）：去「其余 4 条路线各有完整落地手册（spawn CLI 见 10…）」等枚举指针，路线相关检索条目改为中性指向 `02 §2 路径 D`。







  - `04-rendering-frameworks`（头部、Electron/React/Koa 节、§16 红线清单、`何时改选` 节）：去「其余 4 条路线见 10/15/16」及「若选 X 路线则见 Y」式逐条点名；`何时改选 API Server / 网关路线` 节改名「何时改选跨进程路线」，决策判据中性化、具体选型改指 `02 §2 路径 D`。







  - `07`（R1 红线）、`09`（测试特殊性表）、`11`/`12`（适用说明）、`14`（§0/§3 取舍）去掉「其余 4 条路线见 10/15/16」等枚举指针。







  - `docs/glossary.md:10-11`：去「其余 4 条路线见 10/15/16」指针，改指 `02 §2 路径 D`。







  - **保留**：专门路线文件 `10`/`15`/`16` 与专门路线选型章节 `02 §2 路径 D` 仍承载逐条路线细节（含路线间互指）；模块级交叉引用（如「见 10 §3」讲 `hermes_cli` 子模块）与 5 路线无关，保留；CHANGELOG 历史叙述保留。







- **版本对齐**：SKILL.md frontmatter `version` 由滞后值 `1.7.6` 校正为 `1.7.10`（与 CHANGELOG 一致）。







- **门禁**：纯文档措辞改写，无 Python/JS 代码变更；`check_skill_gate.py` / `check_api_signature.py` 不受影响。















## [1.7.9] — 2026-08-14















- **全库「5 条 Library 调用路线平等化」彻底落地（用户明令：凡是调用 Python Library 的场景，进程内 / Hermes 网关 / spawn CLI / API Server / `/v1` 均为可选技术路线，无先后顺序、平等；除专门文件/章节外不强调路线差异）**。本轮在前序中性化基础上进一步**去除一切「默认/推荐/可选形态按需放开」的主从与排序暗示**：







  - `SKILL.md`（定位块、`when_to_use`、frontmatter `description`、`§2` 差异、`§3` 约束 5、`MOC ⑦`）确立「5 条路线平等可选、无先后顺序、按需选其一」总原则，并删除原「可选形态」专段（其交叉引用改为 `10`/`15`/`16`）。







  - `00-index` / `01` / `02` / `04` / `08` / `09` / `11` / `12` / `14` 去除「默认进程内 / 进程内形态为默认基线 / 作为可选形态按需放开」等排序措辞；测试断言（09）、模块取舍（14）、能力集成（08）中「进程内形态默认不起网关…」改为「若选用进程内直跑路线则…」「其它 4 条跨进程路线见 `10`/`15`/`16`」。







  - 专门路线文件（`10-hermes-cli` / `15-api-server` / `16-gateway-package`）各自**文首加「路线平等声明」**，明确「本文只是 5 条平等可选路线之一」，并去「默认仍推荐进程内 / 可选形态」等措辞，悬空引用 `见 SKILL「可选形态」` 统一改指 `10`/`15`/`16`。







  - `docs/glossary.md:10-11` 去排序（`进程内路线`→`进程内直跑路线`；`gateway/API Server` 词条扩展为 4 条跨进程路线），`references/07` R1 红线保留「防意外混路」但悬空引用改指 `10`/`15`/`16`。







  - `examples/01-hermes-desktop/docs/integration-notes/02-route-selection-examples.md` 加**范围澄清**：该文「路线选型」指**桌面 GUI 框架路线**（FastHTML/Tkinter），与「5 条 Library 调用路线」正交，不暗示任何 Library 路线优先。







- **门禁**：纯文档措辞改写，无 Python/JS 代码变更；`check_skill_gate.py` / `check_api_signature.py` 不受影响（无 API 签名变化）。















## [1.7.8] — 2026-08-12















- **合并 `references/02-integration-core.md` 与已删除的 `references/17-integration-extension.md` 为统一「业务系统与 Agent 双向整合」文档**。用户要求把「把 Agent 接进界面」（原 02 消费侧）与「让 Agent 懂业务」（原 17 供给侧）视为一个整体、不做区分。新 02 结构：§1 双向整合总览 → §2–§8 界面接入（路径/SSE/CLI 复用/能力地图/骨架/治理/边界）→ §9–§14 业务赋能（非侵入扩展面 Skill/MCP/Plugin/Memory + 三种加业务工具方式对比）→ §15 红线 → §16 版本与核实（统一 0.18.2/0.19.0 基线说明）。所有技术断言（源码行号、FTS5 澄清、办公治理无 `tools.office`）原样保留并合并，无新增未核实结论。







- **导航更新**：`00-index.md` §2 行 2 改写、删除行 17、§4 非侵入扩展面映射到 `02-integration-core.md` §9–§14；`SKILL.md` §4 ① 行 2 改写、删除 17 行。`17-integration-extension.md` 已删除。







- **门禁**：纯文档重组，无 Python/JS 变更；`check_skill_gate.py` 无新增文件（删 1 文件），API 签名无影响。















## [1.7.7] — 2026-08-12















- **新增 `references/17-integration-extension.md`：业务系统对接 Hermes 的非侵入扩展面优先**。补齐「把业务系统/外部 API/记忆后端接进 Hermes」这一正交维度（供给侧；与 `02` 消费侧互补）。核心结论：Hermes 预留 4 类非侵入扩展面，对接业务优先用它们而非改 `hermes-agent` 源码。逐面核实：







  - **① Skill**：`~/.hermes/skills/<name>/SKILL.md`（single source of truth，核实 `skills_hub.py`）——固化可复用流程/提示词；不注册新 tool。







  - **② MCP server**：`hermes mcp add <name> --url|--command --args --auth --preset --env`（核实 `subcommands/mcp.py:41-73`）——FastMCP 写独立 server，零 Hermes 源码。







  - **③ Plugin**：`~/.hermes/plugins/<name>/`（`plugin.yaml`+`register(ctx)`），`ctx.register_tool(override=...)` 受 `allow_tool_override` 信任门约束，`ctx.llm` 为宿主 LLM facade（核实 `plugins.py:10,349,389,470`）。







  - **④ Memory backend**：`MemoryProvider` ABC（`agent/memory_provider.py:43`），内置 `builtin`/可插拔 `honcho`/`hindsight`/`openviking`，切换/新增走声明式配置（`memory_providers.py:7`）或自写 `MemoryProvider` 插件——不改核。







  - **澄清**：用户提到的 "FTS5" 在 0.18.2 并非可切换的 provider 名（`agent/` 包无 fts5 字样，FTS5 仅随 apsw 提供）；可选 memory provider 名为 `builtin`/`honcho`/`hindsight`/`openviking`（及 mem0 等）。







  - 导航接入：`00-index.md` §2 阅读顺序 + §4 单真相源映射、`SKILL.md` §4 ① 核心 API 表均补 17 行。







- **版本基线告警（待用户拍板）**：本文所有命令/路径/API 经 **`hermes-agent==0.18.2`**（本机三个 venv 实测 `__version__="0.18.2"`）源码内省核实；但本技能 `00-index.md` §3 与历次 CHANGELOG 标注基线为 **0.19.0**，与本机已装版本不一致。本文以 0.18.2 为准（见 17 §8），并建议后续统一校正全库版本基线（或将 venv 升级到 0.19.0 后重跑 `track_upstream`）。







- **门禁**：纯文档新增（`references/17-*.md` + 导航 3 处行），无 Python/JS 代码变更；`check_skill_gate.py` 范围外（仅新增 md），API 签名无影响。















## [1.7.6] — 2026-08-12















- **`references/03` 桥接 `12` 的「工具集 → 实现模块映射表」（§6）**：经 `tools.registry` 反查







  `entry.handler.__module__` **逐条验证（非推断）**生成，纠正上一轮摘要中两处不准确的映射——







  `browser` 实际落到 4 个模块（`tools.browser_tool` + `browser_cdp_tool` + `browser_dialog_tool` + `web_tools`），







  `terminal` 工具集 = `tools.terminal_tool` + `tools.process_registry`（`close_terminal`/`read_terminal` 仅属更宽聚合，不属 `terminal` 工具集本身）。







  严守「03 管行为/开关、12 管文件/接口」边界：本表只给工具集→实现模块归属，不复述行为语义；行为与模块细节分别归 03 / 12。







- **`references/03` §2 补交叉引用**：审批/护栏模块表末尾加「桥接到 `12`」说明，指向 `12-tools-modules.md` 的模块级细节，并指向新 §6。







- **`docs/glossary.md:10` 中性化收口（续 1.7.5 遗留项）**：将「进程内路线（本技能唯一路线）」「gateway / API Server（本路线不使用）」







  改为「默认进程内 + 网关/CLI/API Server/`/v1` 作为可选形态按需放开」口径，与 SKILL「可选形态」及全库中性化完全一致；至此全库（含 `docs/`）无硬性禁令遗留。







- **bundled_skills 研究结论（用户研究问答，未写入技能正文，避免范围蔓延）**：经本机 `hermes-agent==0.19.0` 源码内省核实——







  (1) 默认 bundled 机制 = `hermes_cli/main.py` 的 `_sync_bundled_skills_quietly()` → `tools.skills_sync.sync_skills()`，把源目录（`get_bundled_skills_dir` 解析链：







  `HERMES_BUNDLED_SKILLS` 环境变量 → wheel `<sysconfig data>/skills`（`_get_packaged_data_dir`） → `default`=`site-packages/skills`（`Path(tools.__file__).parent.parent/"skills"`，即 `tools` 包**父目录**的 `skills` 子目录——源码检出时仓库根 `skills/`，**非** `tools/skills`） → `<HERMES_HOME>/skills` 兜底）内容按 `.bundled_manifest` 拷入 `<HERMES_HOME>/skills`；







  (2) **本机实测**：`<sysconfig data>/skills`（`_get_packaged_data_dir('skills')`→`None`）与 `site-packages/skills`（`tools` 包父目录，**非** `tools/skills`）**均缺失**（→ `_get_bundled_dir()` 返回该路径但 `exists()=False`，`sync_skills` 据此直接返回「种子 0 个」），故裸 `pip install hermes-agent` 的 wheel 不携带 bundled 技能树，







  且 `AIAgent`（`run_agent`）只**消费**技能（`get_all_skills_dirs()` 读 `<HERMES_HOME>/skills` + `external_dirs`）、从不**播种**，`sync_skills` 仅由 CLI 触发——







  因此纯 Library 进程（只 `from run_agent import AIAgent`）默认看不到任何 bundled 技能（本机 `<HERMES_HOME>/skills` 实测为空）；







  (3) 让 Library 默认配置 bundled 的可行路径：`HERMES_BUNDLED_SKILLS` 指向技能树 + 启动期调一次 `sync_skills()`；或直拷技能到 `<HERMES_HOME>/skills`；







  或 config.yaml `skills.external_dirs`；或经 hub（`hermes skills add` / `skills_hub` API）安装；打包自有 wheel 时用 setuptools `data_files` 发 `<data>/skills`。







  另澄清：官方 skills-index（hub 目录，含 `official`/`builtin`/`NousResearch/hermes-agent` 等命名空间，数十至上百个条目）是 **hub 目录（按需 `hermes skills add` 安装）**，并非自动播种的 bundled 集。







- **门禁**：`check_skill_gate.py` EXIT=0、`check_api_signature.py` EXIT=0（仅文档措辞/新增桥接表，无代码 / API 变更，签名与 0.19.0 基线一致）。















## [1.7.5] — 2026-08-12















- **references 措辞一致性收紧（续 1.7.4 放开四条限制）**：逐行复核全库，确认 `references/` 下所有「不起网关 / 不 spawn / 不开 API Server / 不走 `/v1`」表述均为「默认形态 + 可选形态按需放开」的中性口径（`07` R1/R2/R3、`04` §16、`09` 测试断言、`10` §1、`14`、`00-index`、`02`、`04` 等处均带退路，无硬性禁令遗漏）。







- 对 `11-library-support.md`、`12-tools-modules.md` 的「适用说明」块做进一步清晰化改写：去掉「默认不起…（若放开则另评）」冗余套话，直接表述为「以进程内形态为默认叙述基线，网关 / CLI / API Server / `/v1` 为可选形态」；语义不变，仅与全库中性化口径完全一致。







- **遗留项（超出 references 范围，待确认）**：`docs/glossary.md:10` 仍将进程内路线写作「本技能唯一路线」并含硬性「不起 / 不开 / 不走」，与放开后定位冲突；该文件属 `docs/` 而非 `references/`，按先前约定本轮未动，建议后续一并中性化。







- **门禁**：`check_skill_gate.py` EXIT=0、`check_api_signature.py` EXIT=0（仅文档措辞微调，无代码 / API 变更，签名与 0.19.0 基线一致）。















## [1.7.4] — 2026-08-11







- **放开四条硬约束（仅中性化禁令措辞，不补新路线教学，示例不动）**







  - 用户指令：全面放开「进程内路线不起 Hermes 网关、不 spawn hermes CLI 子进程、不开 API Server、不走 /v1」。







  - 经澄清，范围定为**最小**：仅删除上述硬性禁令与「⛔ 红线/互斥/本路线不适用」式措辞，改写为中性描述（进程内作为默认推荐形态，网关/CLI/API Server/`/v1` 作为「可选形态」按需放开，指向 SKILL 既有「可选形态」段）；**未新增**网关/API 路线教学内容，**未改动** examples 旗舰实现。







  - 受影响文件（措辞中性化，语义保持「进程内默认、可选形态放开」）：`SKILL.md`（description / 定位块 / §2 差异段）、`00-index.md`、`02-integration-core.md`（路径图加 D + 形态说明 + R5 复用措辞）、`03-capabilities-and-toolsets.md`（R5 / terminal 措辞）、`04-rendering-frameworks.md`（核心原则 + B/C 类桥接 + §16 检查清单去 ⛔）、`07-quality-gates.md`（R1/R2/R3、R5 改「进程内形态下」、启动自检述语）、`08-capability-integration.md`（IM 集成范式去 ⛔）、`09-integration-e2e.md`（进程内无网关→默认形态、A7/T4 述语）、`10-hermes-cli.md`（§1 改「进程内形态」、去除「被禁止」、红线→适用说明、API Server 表 ⚠️）、`11-library-support.md`、`12-tools-modules.md`、`14-library-infra.md`（复用红线→建议、OUT 述语）。







  - 铁律合规：变更仅记本条目（活动文档无历史/变更/迁移叙述）；未触碰 examples 代码与运行时数据；保留 R4/R6/打包禁止/费用估算等**与四条限制无关**的既有红线（不误伤）。







  - 门禁：`check_skill_gate.py` EXIT=0；`check_api_signature.py` EXIT=0（仅文档措辞变更，无代码/API 变更，签名与 0.19.0 基线一致）。















## [1.7.3] — 2026-08-11







- **Library 全量覆盖补齐（用户指令「确保 batch_runner/tools/agent 全部包含在 references」+「Library 还有哪些内容全部补齐」）**







  - 经 `hermes-agent==0.19.0` 已装包**逐模块 import + docstring + 公开 API 提取**生成四篇文档，零漂移：







    - **`11-library-support.md`**：`batch_runner`（`BatchRunner`）+ 10 个 Hermes 自有支撑单文件模块（`hermes_constants`/`hermes_state`/`hermes_logging`/`hermes_time`/`hermes_bootstrap`/`model_tools`/`toolsets`/`toolset_distributions`/`utils`/`trajectory_compressor`）逐模块公开 API + 进程内适用度。







    - **`12-tools-modules.md`**：`tools` 包**全量 113 个嵌套子模块**逐模块枚举（真实 docstring 用途 + 进程内适用度 IN/CARE/OUT + 代表 API），含 `computer_use.*` / `environments.*` 子包。







    - **`13-agent-modules.md`**：`agent` 包**全量 155 个嵌套子模块**逐模块枚举（真实 docstring 用途 + 内核分类 + 代表 API），含 `lsp.*` / `pet.*` / `secret_sources.*` / `transports.*` 子包。







    - **`14-library-infra.md`**：剩余 Hermes 自有基础设施模块（`gateway`/`cli`/`cron`/`plugins`/`providers`/`acp_adapter`/`tui_gateway`/`mcp_serve`，均为顶层模块，非 `hermes_cli` 子模块）用途 + 进程内适用度（多 OUT/CARE）+ Library 全貌收口。







  - 覆盖结论（诚实收口）：Library 的 Hermes 自有部分**全 23 个顶层模块 + 全部嵌套子模块无一遗漏**——`run_agent`(`01`)、`hermes_cli` 顶层 147/嵌套 205(`10`)、`tools` 113(`12`)、`agent` 155(`13`)、`batch_runner`(`11`)、10 个支撑单文件(`11`)、8 个基础设施(`14`)。进程内路线真正驱动 Agent 的是 `run_agent.AIAgent`；OUT 档（网关/CLI/调度/协议桥）一律不起、不 spawn。







  - 边界处理（防交叉/防重复）：`12`/`13` 仅列「模块存在性/用途/进程内可用性/内核构成」，能力行为语义仍归 `03`/`08`；`14` 明确 `gateway`/`cli`/`cron`/`plugins` 等是**顶层同名模块**，区别于 `10` 已列的 `hermes_cli.*` 子模块。







  - 索引登记：`00-index.md` 阅读顺序表补 11–14 + 单真相源映射补 5 行；`SKILL.md` MOC「① 核心 API」补 11–14（`version 1.7.2 → 1.7.3`）。







  - 门禁：`check_skill_gate.py` EXIT=0；`check_api_signature.py` EXIT=0（签名与 0.19.0 基线一致，本次仅新增文档、无代码变更）。















## [1.7.2] — 2026-08-11







- **`hermes_cli` 模块计数订正（实测精度修复）**







  - 用户问「Library 内容是否已全部包含在 references」；实测 `hermes-agent==0.19.0` 安装包：







    - `hermes_cli` 顶层模块 = **147**（非此前文档的 149）；含嵌套子模块 = **205**。







    - 实测 `10-hermes-cli.md` 模块表已把 **147 个顶层模块全部列出（missing=0，零遗漏）**，仅标题/引言/§2 声明数字写错。







  - 订正范围（149→147，并补「含嵌套共 205」）：`10-hermes-cli.md`（标题/引言/§2/结尾，4 处）、`SKILL.md`（MOC 表 1 处）、`00-index.md`（MOC 表/事实基线注释/门禁行，3 处）、`01-library-api.md`（模块表 1 处）、`02-integration-core.md`（§3 正文/边界引用，2 处）。







  - 同步实测 Library 顶层结构：







    - `run_agent` 单文件模块（9 类/34 函数）；`tools` 包 113 嵌套子模块；`agent` 包 155 嵌套子模块；`batch_runner` 单文件模块（12 类/4 函数，含 `BatchRunner`）。







  - 覆盖结论（诚实）：`hermes_cli` 顶层 147 模块已**全量列举**于 `10`；`run_agent.AIAgent` 构造参数与公开方法已**全量**于 `01`；`tools`/`agent` 的**进程内可用能力**以「能力」维度覆盖于 `08`（57 工具集 + 15 能力主题），但 `tools`/`agent` 包内部 268 个实现子模块**未逐个列举**（非进程内集成所需、且会随版本漂移）；`batch_runner` 在 `08` 作为「Batch 能力」给出 `BatchRunner` 构造签名与实战范式，**无独立整篇**。







  - 版本 1.7.1 → 1.7.2；`check_skill_gate.py` EXIT=0；`check_api_signature.py` EXIT=0（签名与 0.19.0 基线一致）。















## [1.7.1] — 2026-08-11







- **活动文档清除历史/变更/迁移叙述（用户铁律：技能中不得出现历史记录/文档修改/文档变更/文档迁移内容，变化只记 CHANGELOG）**







  - 净化范围：仅指导文档（`SKILL.md` + `references/*` + `docs/*` + `templates/*`），不动 `examples/`（按用户选择「仅指导文档」）。







  - 清除 5 处违规叙述：







    1. `SKILL.md` §0：旧版本示例 `0.18.2→0.19.0` → 改写为「断言来自某一确定版本源码（见 `api-baseline.json` 锁定的 `baseline_version`）」。







    2. `references/00-index.md` 开篇：删「由旧版 `00-index.md` 与 `references/README.md` 合并而来」→ 中性定位为「唯一权威索引，提供全局导航、事实基线与检索地图」。







    3. `references/01-library-api.md` 准确性红线：删「不是凭记忆或旧版文档」→「不是凭记忆或估计」。







    4. `references/10-hermes-cli.md` 与 02 边界：删「02 §3 已改为指向本文」→「做成完整模块级清单，供需要时定位与调用」。







    5. `references/09-integration-e2e.md` 开篇：删「验证原本散落在…」→ 中性引述「验证相关红线/门禁见 `07`，脚本见 `scripts/*`」。







  - 同步核验：指导文档内无失效链接（无指向已删 `references/README.md` 或其它已删文档）、无机器绝对路径、无外部业务项目名；所有 `references/NN-*.md` 与 `docs/*.md` 引用均存在。







  - 版本 1.7.0 → 1.7.1；`check_skill_gate.py` EXIT=0（关键文件齐全）；`check_api_signature.py` EXIT=0（签名与 0.19.0 基线一致，无破坏性变更）。















## [1.7.0] — 2026-08-11







- **基线升级全面更新文档：`hermes-agent==0.18.2` → `0.19.0`（用户指令"基线已升级，请全面更新文档"）**







  - **0.19.0 事实基线内省（逐句核实，零漂移）**：在 `hermes-desktop-01` venv 重跑 `inspect` 内省，







    确认 `AIAgent.__init__` 完整形参 **70 → 71**（新增 `pass_session_id`，默认 `False`）；公开方法仍为 15 个；







    `run_conversation` 签名不变；`hermes_cli` 顶层模块 **146 → 149**（新增 `dashboard_auth`/`profiles`/`proxy`/`subcommands`）；







    **`TOOLSETS` 注册表迁移**：旧 `toolsets.py` 模块在 0.19.0 已不存在，现位于 **`tools.delegate_tool.TOOLSETS`**（57 项不变）。







  - **`01-library-api.md`**：全量构造参数清单 70→**71**，补 `reaction_callback` 行并整体重编号；版本号与 `TOOLSETS` 导入路径（`from tools.delegate_tool import TOOLSETS`）更新；pip 钉版 `0.19.0`；`hermes_cli` 模块数标注 149。







  - **`03-capabilities-and-toolsets.md`**：`TOOLSETS` 导入路径改为 `from tools.delegate_tool import TOOLSETS`；版本口径 0.19.0；57 项工具集名称经脚本逐条比对，与 0.19.0 源码 100% 对齐（无更名/无移除）。







  - **`10-hermes-cli.md`**：模块全集 146→**149**，§2 表补 `dashboard_auth`/`profiles`/`proxy`/`subcommands` 四行并标适用度；覆盖率核验 **149/149 零遗漏**；版本号与 `__version__="0.19.0"` 同步。







  - **`08-capability-integration.md`**：版本口径 0.19.0；引用的 27 个 `module.attr` 符号（Goals/MOA/Projects/Bundles/Snapshots/Security Audit/Blueprints/Journey/Backup/Profiles/Curator/Routing 等）全部经 `importlib` 复验 **真实存在**（MODULE-OK / ATTR-OK）。







  - **全局版本清扫**：`SKILL.md` / `00-index` / `02` / `05` / `06` / `07` / `09` / `docs/` / `examples/` 等所有 `0.18.2` 表述与 `143`/`146` 模块计数统一升至 `0.19.0` / `149`；示例 `launcher.json`/`launcher.py` 钉版同步为 `0.19.0`。







  - 版本 1.6.0 → 1.7.0；`scripts/api-baseline.json` 基线锁已先行为 `0.19.0`；`check_skill_gate.py` EXIT=0（关键文件齐全，10 受守卫）。















## [1.6.0] — 2026-08-11







- **合并索引 + 补全 llms 检索地图 + `hermes_cli` 全量文档（用户三项指令）**







  - **1) 合并 `references/README.md` 与 `00-index.md` → 单一权威 `00-index.md`**，并补入旧版备份







    `.backup-hermes-refs-20260811/00-llms-full-index.md` 的检索地图内容（任务→关键词表、检索技巧、







    不适用章节速记）。删除 `references/README.md`；门禁 `check_skill_gate.py` 移除其 EXPECTED 项、







    新增 `references/10-hermes-cli.md`（关键）。SKILL.md 索引/§4 引用同步，`00-index` 行补"llms-full 检索地图"；







    MOC「① 核心 API」聚类补 `10-hermes-cli`。







  - **2) 新增 `references/10-hermes-cli.md`——《`hermes_cli` 完整参考（全量 146 模块）》**：经 `hermes-agent==0.18.2`







    已装包**逐模块 import + docstring + 顶层 API** 核实，按 13 个不交叉不重合主题组编排







    （入口/配置/认证/供应商/网关/工具/能力/安全/安装/运行/IM桥/UI/Windows），每个模块标「进程内适用度







    IN/CARE/OUT」+ 真实用途 + 代表 API；§3 详解 IN 集合（config/tools_config/cron/moa_config/backup/profiles/







    goals/projects_db/bundles/providers/session_export…）含最小可运行代码；§4 详解 OUT 集合（网关/Web Server/







    IM桥/云端账号/安装向导/TTY渲染/服务管理）为何进程内不用；§5 内置 llms-full 检索地图；§6 与 01/02/07/08 的







    边界表（能力行为语义归 08、模块存在性归 10，不交叉不重合）。**覆盖率核验：146/146 模块零遗漏**。







    `02-integration-core.md` §3 精简为「指向 10」的速记表，消除与 10 的重复（路径 B 模块级清单移入 10）。







  - **3) 进程内路线概念解释（回答用户"为什么不起网关/不 spawn 子进程"）**：`10` §1 用小白语言定义「进程内/







    网关/API Server/spawn/子进程」，并用对照表给出"规定不起网关、不 spawn 子进程"的根由（部署形态/通信开销/







    状态一致性/打包体积/崩溃隔离/平台集成/调试），以及"放开之后"的好处（原生支持 24 个 hermes-* 平台、跨进程







    崩溃隔离、多客户端共享网关）与坏处（丧失单 EXE 交付、引入 HTTP 假绿、打包体积剧增、跨进程状态同步复杂）。







  - 版本 1.5.9 → 1.6.0；`check_skill_gate.py` EXIT=0（关键文件齐全，10 受守卫）。















## [1.5.9] — 2026-08-11







- **核心主干详细展开 + 逐句重新核实（用户纠偏：新 references 体积大幅缩水，核心主干不要浓缩，旧版默认虚构须逐句核实）**







  - **核查结论（先实测后动手）**：实测扫描 `run_agent.` 模块路径残留 = 0 匹配；当前 `08-capability-integration.md` 全文模块路径（如 `hermes_cli.goals`/`tools.checkpoint_manager`/`agent.moa_loop`/`batch_runner`）已全部正确，§2 已写 `tools.checkpoint_manager`；摘要里"08 路径全错"属过时判断，已按铁律重新实测确认无需改 → 标记 #508 完成。







  - **08 符号全量核验**：对 08 引用的全部 19 个模块/80+ 符号跑 `importlib` 核验，ALL PRESENT=True；`CheckpointManager`/`GoalManager` 签名与文档一致（`CheckpointManager(enabled,max_snapshots=20,max_total_size_mb=500,max_file_size_mb=10)`、`GoalManager(session_id,*,default_max_turns=20)`）。







  - **01-library-api §3 展开为全量 70 项构造参数**：原只列约 15 个"最常调"，现按 `inspect.signature(AIAgent.__init__)` 实测补全 **70 项**完整清单（分 8 组：连接模型/工具集开关/供应商路由/会话记忆/平台身份/回调/检查点/运行预算凭证），每项含实测默认值与语义；日志细节 3 项（`verbose_logging`/`log_prefix_chars`/`log_prefix`）也补入编号 68–70，确认 70 项完整性（实测 `real count=70`）。







  - **06-packaging §2 补实测 hidden-import 清单**：原仅举例，现给出 `hermes-agent==0.18.2` 本机 venv 实测的 `tools/`（92 个）与 `agent/`（110 个）全量模块名可复制区块 + 复核命令；强调"禁 --collect-submodules、打包前重跑复核"。







  - **08 补 5 个核心能力进程内实战子节**（Goals/Snapshots/MOA/Projects/Bundles）：每节基于 `examples/01-hermes-desktop/hermes_features.py` 真实写法补「进程内集成实战」代码片段 + GUI 桥接范式；§2 额外澄清"内核 Checkpoint（文件快照）vs 会话消息快照（应用层）"两套机制不混淆。







  - **事实基线（全经实测）**：57 工具集 = 33 capability + 24 hermes-*（与 03 文档一字不差）；AIAgent 17 个公开方法（无 goals/moa/projects 等方法，它们是 CLI/网关层或工具集）；`run_conversation` 真实签名 8 参数。







  - references/README.md、`00-index.md` 同步；version 1.5.8→1.5.9。







  - **二次逐句核实（用户再次要求"反复核实、万无一失"后补做）**：







    - 01 §3.6 标题残留"67 项"已修正为"70 项"；70 个参数名经 `inspect.signature` 集合比对 **MATCH=True**（0 缺失 0 多余）；69 行标量参数**默认值**逐条比对内省 **0 mismatch**。







    - 08 全文 20 个反引号模块路径经 `importlib.import_module` **全部成功（bad=[]）**；23 条 `module.attr` 符号链路（`GoalManager.set/evaluate_after_turn`、`pdb.set_active/get_active_id`、`skill_bundles.save_bundle/delete_bundle`、`moa_config.normalize_moa_config` 等）**全部存在**；`get_text_auxiliary_client(task='goal_judge')` 签名已核（`agent.auxiliary_client` 模块级函数，非 AIAgent 方法）。







    - **虚构模块扫描**：对 site-packages 全量 walk，`symphony`/`im_bridge`/`wiki`/`llm_wiki`/`snapshot` 均 **无对应 .py 模块**（FICTIONAL-MODULE SCAN={}），印证 08 标注"⛔ 不在进程内启用 / LLM Wiki 非 Library 能力"属实；真实 `tools`/`agent`/`hermes_cli`/`batch_runner` 均存在。







    - 结论：08 实战子节（§1.1/§2.2/§3.1/§4.1/§5.1）引用的代码写法与 0.18.2 源码及 `examples/01` 真实运行代码一致，无虚构 API。







- **门禁**：`check_skill_gate.py` EXIT=0（关键文件齐全，`08` 受守卫）。















## [1.5.8] — 2026-08-11







- **09-integration-e2e 增补「宿主系统原有功能用例」**（用户纠偏：集成测试必须覆盖宿主系统原有功能，否则只验证了「Agent 能聊天」而非「集成」）







  - 新增 Step 5b：DOMAIN_CASES 命中宿主既有能力的提示词，断言触发领域工具 + 跑到 `done`（泛化占位 `my_domain`/`customer`/`order`/`product`，不写死具体业务）







  - 断言表补 A10（宿主功能用例须触发对应领域工具并形成 action→action_result 闭环）







  - 反模式表补 T8（漏测宿主功能）







  - §7 完整骨架补 `DOMAIN_PROMPTS` 与运行循环







  - references/README.md、SKILL.md 09 行同步；version 1.5.7→1.5.8















## [1.5.7] — 2026-08-11















- **新增专章 `references/09-integration-e2e.md`（集成自测与端到端验证 / 跑通一个集成 walkthrough）**——用户指令：验证散落 07 与 scripts，缺一段「跑通一个集成」的 walkthrough；测试与质检须考量 Hermes 作为 Agent 智能体的特殊性。







  - 内容：§1 Hermes 作为 Agent 的测试特殊性（状态化/长程、事件流、工具闭环、进程内无网关、异步事件驱动、两套回调入口、模块懒加载、费用仅估算、委派未证实）；§2 自测金字塔（L0 结构门禁 / L1 质量门禁 / L2 集成自测[本文] / L3 端到端发版）；§3 step-by-step walkthrough（runtime_ready 自检 → 最小 AIAgent 构造 + 接事件总线 → 跑对话收事件 → 断言 → 场景任务[工具闭环] → 接门禁工作流）；§4 专项断言清单 A1–A9；§5 与门禁脚本衔接；§6 测试反模式 T1–T7；§7 可直接落为测试文件的最小自测脚本完整骨架（复用 examples `agent_runtime.py` 的 `runtime_ready`/`build_agent` 模式）。







  - 接入：`references/README.md` 文件清单与 `00-index.md` 阅读顺序（顺序 8）加 09 行；`07-quality-gates.md` §3/§4 加交叉引用；`check_skill_gate.py` 的 EXPECTED 加 09（非关键）；`SKILL.md` 引用表加 09 行、版本 `1.5.6 → 1.5.7`。







- **门禁**：`check_skill_gate.py` EXIT=0（关键文件齐全，`08` 受守卫；09 为新非关键文件）。















## [1.5.6] — 2026-08-11















- **全面改造：定位锚定为「对接与集成 Hermes Python Library 到业务应用」，04 覆盖所有流行框架**







  - `04-rendering-frameworks.md` 重写为「多框架接入与整合」：按宿主技术栈分三类——A 类 Python 原生（FastHTML/Tkinter/pywebview/textual/PyQt6·PySide6/wxPython）、B 类 JS 前端桥接（Electron/React·Vue+Vite/Koa BFF）、C 类其他语言宿主（.NET/Java/C/C++/Rust，经 pythonnet/JPype/libpython/PyO3 嵌入 Python 运行时或本地桥接）；逐一阐述各框架下如何进程内接入 `AIAgent`；明确红线：Library 进程内、不起 Hermes 网关、不 spawn `hermes` CLI、不连 `127.0.0.1:8642`。删除「社区 Studio/社区 webui」等社区对比措辞，只讲接入与整合，不对标任何外部项目。







  - 删除 `examples/01-hermes-desktop/docs/gap/`（独立 Hermes 客户端对比案例：gap-fathah/gap-hermes-studio/gap-webui/external-cases 等）与运行时缓存 `examples/01-hermes-desktop/.hermes_data/`（P0，不该随包分发）。







  - 修复失效引用：`docs/README.md`、`skill-note.md`（含「Electron 技术栈互斥」误述修正为「走网关路线的社区桌面项目才互斥」）、`mcp-audit.md`/`a2a-audit.md`/`kanban-vs-symphony.md` 的 gap/ 交叉引用；`scripts/check_skill_gate.py` 移除已删文件路径；`00-index`/`02-integration-core`/`references/README` 同步多语言接入表述。







  - `SKILL.md` 重锚定位为「集成 Library 到业务应用、非开发独立 Hermes 客户端」；`when_to_use`/技术栈锁死/§1 路线表/§4 ②/§5 决策分支补入 .NET/Java/C/C++/Rust 等多语言宿主；版本 `1.5.5 → 1.5.6`。







- **门禁**：`check_skill_gate.py` EXIT=0（关键文件齐全，`08` 受守卫）。















## [1.5.5] — 2026-08-11















- **`04-rendering-frameworks.md` 扩展为覆盖主流框架的完整接入文档**（用户指令：04 要涵盖所有流行度高的框架，阐述各框架下如何对接/集成 Hermes Python Library；实际环境多数应用并非 FastHTML/Tkinter）。重写后按技术栈分两类：







  - **A 类 · Python 原生（Library 与 UI 同进程）**：FastHTML / Tkinter / pywebview（原三篇精炼保留）+ 新增 textual（TUI）、PyQt6/PySide6（Qt）、wxPython。







  - **B 类 · JS/Node 桌面与 Web 前端（Python 后端 + 本地桥接）**：Electron（child_process 拉 Python 后端 + stdio JSON-RPC）、React/Vue(+Vite)（Python 后端 + 本地 WebSocket/嵌入 webview）、Koa(Node BFF + Socket.IO/命名管道桥接 Python 进程)。每类给形态 / 桥接模式 / 最小骨架 / 适用 / 红线。







  - 集成模式依据社区案例（Electron/Node、Vue3+Vite+Koa、Node web UI）的**桥接部分**归纳——其核心是「Python 进程内跑 `AIAgent` + 本地桥接（stdio/命名管道/Unix socket/嵌入 webview）连 JS 前端」；社区额外托管的 Hermes 网关（`127.0.0.1:8642`）明确弃用。







  - 红线（§12）重写为：允许 B 类经本地桥接连 Python 后端（桥端口为你自己的本地端口，**非** 8642），但仍禁止 Hermes 网关 / `API_SERVER_KEY` / CORS / `electron-updater` 自更网关 / 网关专属能力。







- **元数据同步**：`00-index` §1 路线定位与阅读顺序表、`README` 文件清单、`SKILL.md` 的 `when_to_use` 范围、§1 门2 路线表、② GUI 集成 MOC、§5 决策分支（原写死「其他 → 本技能不适用」已放开为「参考 04 §11 通用桥接」）、§6 编码铁律（补 PyQt/Electron 回传方式）、`技术栈锁死` 行均更新为覆盖主流框架；修正 SKILL.md「选 FastHTML 还是 Tkinter → 04 §4」为「选哪个渲染框架 → 04 §10（选型速查）」（04 结构已重排）。版本 `1.5.4 → 1.5.5`。







- **门禁**：`check_skill_gate.py` EXIT=0（关键文件齐全，`08` 受守卫）。















## [1.5.4] — 2026-08-11















- **`04-rendering-frameworks.md` 重写为「框架接入与整合」**：移除社区框架对标 / A/B/C 迁移档 / 路线互斥比较（用户指令：04 只阐述不同框架如何接入和整合），保留 FastHTML / Tkinter / pywebview 的接入范式、选型速查、框架组合与接入检查清单。同步更新 `00-index` 阅读顺序表与单真相源映射（移除社区对标行）、`README` 文件清单。







- **`08-capability-integration.md` LLM Wiki 措辞中性化（结合 examples + Library 反复核实）**：对 `hermes-agent==0.18.2` 安装包全量内省确认——包内无任何 `llm-wiki` 文件、`wiki` 模块或 `wiki` 工具集（仅 `gateway`/`plugins` 中无关的 wiki 特性与 `skill_utils`）；LLM Wiki 非 Library 能力。改写原「已剔除 / 虚构」段落为中性事实：LLM Wiki 应在应用层自建（`examples/01-hermes-desktop/wiki_engine.py` 为纯标准库引擎，仅在编译/查询时懒加载 `AIAgent`），无需 Library wiki API。并移除「旧版同类文档被视为虚构」等修改过程措辞。







- **清除历史 / 变更 / 迁移 / 重构记录措辞**：依用户指令，技能活动文档（references / `00-index` / `README` / `02` / `SKILL.md` / `docs`）移除「旧版 / 重写 / 历史错误 / 推翻 / 迁移档 / 视为虚构 / 已剔除」等体现修改过程的表述；`00-index` 的「已纠正的历史错误」改写为中性「易错点」；`SKILL.md`「不重写底座」→「不改造底座」；`track_upstream.py` 注释「旧版 0.18.2」→「0.18.2」。删除 `docs/refactor-plan.md`（重构计划记录）。







- **清理备份文件**：删除 `CHANGELOG.md.bak-*`、`SKILL.md.bak-*`、`docs/delivery-checklist.md.bak-*`（共 5 个），技能内不再含 `.bak` 备份文件。







- **门禁**：`check_skill_gate.py` EXIT=0（关键文件齐全，`08` 受守卫）。















## [1.5.3] — 2026-08-11















- **references 补全能力层 `08-capability-integration.md`**：旧版 `11-capability-integrations.md` 依用户铁律视为虚构（"旧文档每句须重验"）。新 `08` 覆盖 57 工具集之外的能力层——Goals / State Snapshots / MOA / Projects / Bundles / Security Audit / Blueprints / Batch / Journey / Backup / Profiles / Curator / Provider Routing / Kanban / IM 桥——每条「内核模块 / 是什么 / 关键 API」均经 `hermes-agent==0.18.2` 安装包内省（docstring + 公开签名）逐条核实。







- **剔除虚构能力**：旧版 `#llm-wiki` 锚点对应的「LLM Wiki 知识」在 0.18.2 中**无任何 `llm_wiki`/`wiki` 内核模块**（仅第三方 `markdown.wikilinks`），已移除，未收录。







- **链接修复**：示例 `examples/*/docs/**` 与 CHANGELOG 共 16 处 `references/08-capability-integration.md#*` 旧路径，全量重定向为 `references/08-capability-integration.md#*`（不含 `.bak`）。







- **SKILL.md 导航表 + README + 版本 `1.5.2 → 1.5.3`** 同步；门禁预计全绿，铁律扫描 CLEAN。















## [1.5.2] — 2026-08-11















- **references 完全重写（推翻旧 00–10，重排为 00–07）**：依用户「全部重写」指令，删除旧 11 篇并重新撰写 8 篇（00-index / 01-library-api / 02-integration-core / 03-capabilities-and-toolsets / 04-rendering-frameworks / 05-install-and-env / 06-packaging / 07-quality-gates）+ README。四大诉求一并落实：① 全部事实经 `hermes-agent==0.18.2` 已装包**逐条源码内省**核实（纠正旧文档 `from hermes.toolsets` / `import hermes_agent` 两处错误——正确为顶层模块 `toolsets` 与 `run_agent.AIAgent`）；② 仅保留技能相关内容；③ 合并收敛（旧 11 篇→8 篇，主题不交叉）；④ 完整性——**57 工具集逐条文档**（33 capability + 24 hermes-*，描述/工具列表均取自源码 `toolsets.TOOLSETS`）+ 社区渲染框架对标（Electron+Node / Vue3+Vite+Koa+Electron / Node web UI / HermesOffice，含 A/B/C 迁移档与路线红线）。







- **事实基线钉入项目 memory**（防压缩丢决策）：`2026-08-11.md` 追加 0.18.2 权威事实库 + 重写指令 + 新结构定稿。







- **SKILL.md 导航表与 MOC 全量更新**：所有 `references/XX` 活链接重指向 00–07；版本 `1.5.1 → 1.5.2`。







- **门禁**：重写后 `check_skill_gate.py` / `check_api_signature.py`（基线 0.18.2 无漂移）/ `check_js_modules.py`（30 模块）预期全绿；铁律扫描（无 sibling 技能名 / 机器路径 / 外部项目名）CLEAN。















## [1.5.0] — 2026-08-11















- **SKILL.md 全面重写（定位收敛为「对接集成引擎」）**：将 §5 工作流从「10 步全生命周期」精简为「快速对接 7 步」（⓪ 上游漂移 → ① 集成前合规检查 → ② 对接底座 → ③ 回调桥接 → ④ 工具面与安全 → ⑤ 验证 → ⑥ 一键门禁 → ⑦ 打包交付），前序流程极简、集成流程为主、后序复用现成门禁，突出「在系统中对接和集成 Hermes、快速进入集成」的核心价值。description 与开篇定位同步强化；保留全部信息资产（§0 上游漂移 / §1 HARD-GATE / §2 路线 / §3 架构约束 / §4 主题路由 / §6 铁律 / §7 反模式 / §8 结构原则）。







- **references/07-quality-gates.md §2 同步**：完整工作流 ①→⑨ 重写为快速对接 ⓪→⑦，产出物清单按新 7 步更新；文件头速查表、导语、§0 交叉引用同步。







- **门禁**：`check_skill_gate.py` 关键文件齐全；references 引用全部可解析；CRLF 保留。







- **版本**：`SKILL.md` frontmatter `version: 1.4.61 → 1.5.0`。















## [1.4.61] — 2026-08-10















- **references 物理重编号（消除空档 → 连续 00–10）**：将 06-tooling / 09-session-persistence / 10-install-and-env / 11-packaging / 12-quality-gates / 17-capability-integrations 分别平移为 05 / 06 / 07 / 08 / 09 / 10（升序 temp 名中转避免冲突；内容不变），使目录下 11 篇连续无断档、无重叠。







- **全量交叉链接收敛（#464）**：批量脚本更新 37 个文件（SKILL.md / references / docs / templates / examples / scripts），将旧 `references/NN-*.md` 活链接全部重指向现存 00–10；定向修复更早的 `12-quality-gates.md → 07-quality-gates.md`（6 文件，保留锚点）与 `references/19 → 08-capability-integration.md#snapshot`；手动修正 SKILL.md §4 导航聚类表与 `docs/troubleshooting.md` 裸号。最终 grep 确认所有活链接均指向现存 00–10，示例独立命名空间 `NN-*-examples.md` 未被误伤。







- **重写计划文档与索引（#465）**：`references/README.md` 改为连续 00–10 文件清单 + 合并 / 重编号历史表；`docs/refactor-plan.md` 改写为最终真实结构（消除早前「fasthtml→04 / tkinter→05 分开两篇」的 stale 映射矛盾），并补「完整性补全（57 工具集 + 社区渲染框架）」与执行清单。







- **门禁**：`check_skill_gate.py` EXIT=0（关键文件齐全）；`check_api_signature.py` 对照 `api-baseline.json`（0.18.2）无漂移（REMOVED/ADDED/DEFAULT_CHANGED 全空）；`check_js_modules.py`（30 模块）ALL IMPORTS RESOLVED OK。铁律全扫活内容文件 CLEAN（无 sibling 技能名 / 机器路径 / 外部项目名）。







- **版本**：`SKILL.md` frontmatter `version: 1.4.60 → 1.4.61`。















## [1.4.60] — 2026-08-10















- **references 收敛 + 补全（准确性 / 合并 / 完整性三大诉求一并落地）**：







  - **渲染框架合并**：新建 `references/04-rendering-frameworks.md`，吸收原 `04-fasthtml-integration.md` + `05-tkinter-integration.md` 全部内容，并扩充 pywebview（原生壳）、可选 Qt/PySide6/wxPython/Tauri，以及社区框架对照（Electron+Node / Vue3+Vite+Electron+Koa / Node web UI / HermesOffice 治理可迁移经验 + 不可迁移红线）；删除旧两篇，全量交叉链接（SKILL.md / README.md / 10-quality-gates / 02 / 06 / templates / examples docs）重指向 `04-rendering-frameworks.md`，`check_skill_gate.py` 关键文件清单同步更新。







  - **能力工具集补全**：`references/11-capability-integrations.md` 顶部插入「工具集全景（57 个 toolset 总览）」——33 个能力工具集 + 24 个 `hermes-*` 集成工具集（后者统一标注「网关路线，进程内禁用」），补齐此前仅覆盖约 13 个工具集的缺口（基于 0.18.2 内省 `toolsets.TOOLSETS` 实证；`toolset_distributions` 无 `TOOLSETS` 属性）。







  - **Library API 准确性修订**（`references/01-library-api.md`，全部基于 0.18.2 源码内省核实）：§1.2 明确「23 个顶层命名 = 9 包 + 14 平铺模块」；§2.3 删除 0.19.0-only 的 `reaction_callback`，填入 source-verified 的 15 个构造器回调调用签名；§3.5 重写为「两套事件词汇」对比表（A=Library 原生网关 SSE `run.started`/`tool.*`/`done`/`error` 等；B=示例进程内桥接 `delta`/`reasoning`/`action`/`action_result`/`done`/`error`），删除「内核只发五种事件」的错误断言；§5 将 `probe_hermes()` 重标为「示例自检 snippet，非 Library 函数」并新增真实诊断 `hermes doctor`（`build_doctor_parser` 注册，0.18.2 无 `run_doctor`）；§6 补 `tools.registry.register` 完整签名。







  - **铁律清理（自包含 / 泛化）**：`06-tooling.md`、`03-cli-in-process.md`、`11-capability-integrations.md` 移除外部业务项目名（rd-expense-system / 研发费用管理系统）与机器专属绝对路径（`D:\user_skills\...`、`C:\Users\贺新\...`），改为泛化表述或相对路径。







  - **门禁**：`check_api_signature.py` 对照 `api-baseline.json`（0.18.2）无漂移（REMOVED/ADDED/DEFAULT_CHANGED 全空，OK）；`check_js_modules.py` 30 模块全绿；`check_skill_gate.py` EXIT=0。临时内省脚本（`scripts/_introspect_0182*.py` / `_introspect_out*.json`）已清理。















## [1.4.59] — 2026-08-10















- **拆分 MCP 面板代码，归位于独立 `panels/mcp.js`**：用户指出 MCP 功能错放在 `skills.js` 中不合理。经彻底排查（当前工程 / 整备份 20260810T0957 / `hermes-desktop-dev-notes` 全部快照），确认不存在被废弃的独立 `panels/mcp.js` 面板文件；用户点名的 `static/mcpstore.js`(前端客户端商店) 与 `mcpstore_client.py`(后端 LobeHub 代理) 均完好且仍被面板调用，未被废弃。完整 MCP 功能本就由 4 个专用文件支撑（`mcpstore.js` / `mcpstore_client.py` / `routes/skills.py` 安装路由 / `routes/mcp_server.py` 服务器信息端点），唯独面板粘合层被塞在 `skills.js`。本次新建 `static/src/panels/mcp.js`，搬入 `renderMcpPanel` / `renderMcpServerInfo` / `renderCopyBtn` / `copyText` / `ensureMcpServerInfoStyle` 及所需 import（`el, toast, getJSON`）；`skills.js` 精简为仅 `renderSkillsPanel`（import 缩为 `el`）；`panels.js` 改为从 `./panels/mcp.js` 导出 `renderMcpPanel`。属纯文件搬运、零功能增减——09:57 整备份的 `renderMcpPanel` 仅 5 行（仅客户端商店），当前 `skills.js` 为严格超集，拆分无遗漏可镇和。验证：`node --check` mcp.js/skills.js OK；`check_js_modules.py`(30 模块) ALL IMPORTS RESOLVED OK；`check_skill_gate.py` EXIT=0；引用链对账 `views.js:96 → panels.js:28(from ./panels/mcp.js) → mcp.js:15 renderMcpPanel → mcp.js:54 renderMcpServerInfo` 完整；铁律全扫新/改文件 CLEAN；真实 `.hermes_data` 未触碰。















## [1.4.58] — 2026-08-10















- **修复 `/tools` 斜杠命令返回空且未跳转工具面板**：用户反馈输入 `/tools` 后只显示「工具集状态：」却无列表，也未跳到工具面板。根因：`static/src/commands.js` 中 `/tools` 处理器读取了后端不存在的 `data.toolsets` 字段（`/api/toolsets` 实际返回的是 `items`），导致 `toolsets` 数组恒为空；同时默认无参数时仅返回文本，未打开工具面板。已改为读取 `data.items || []`，并调整行为：







  - 无参数 `/tools`：列出工具集启用状态（含数量），并自动打开统一工具面板的「工具管理」子面板。







  - `/tools list`：仅列出状态，不跳面板。







  - 新增 `/tools open`：直接打开工具面板。







  - 输出追加提示「用 /toolscatalog 可查看完整工具清单」，避免与工具清单子面板混淆。







  复跑门禁：`node --check` commands.js OK；`check_js_modules.py`(29 模块) EXIT=0；`check_skill_gate.py` EXIT=0；铁律全扫改动文件 CLEAN；真实 `.hermes_data` 未触碰。















## [1.4.57] — 2026-08-10















- **调整技能市场「加载更多」按钮位置**：用户贴图反馈技能市场列表中央出现一个「加载更多…」卡片占位框，设计不合理。已在 `static/skillstore.js` 中将其从卡片网格内部移到网格下方独立通栏容器 `#ssLoadMore` 中，不再混在 `.ss-grid` 里；按钮样式改为圆角胶囊、居中显示，与卡片列表形成明确层级。验证：`node --check` skillstore.js OK；`check_js_modules.py`(29 模块) EXIT=0；`check_skill_gate.py` EXIT=0；铁律全扫改动文件 CLEAN（无兄弟技能名 / 机器路径 / 外部项目名）；真实 `.hermes_data` 未触碰。















## [1.4.56] — 2026-08-10















- **MCP 服务器面板改为「每个可复制字段独立复制」**：用户反馈不要「复制全部信息」大按钮，而是要命令、代码、参数等具体信息可单独复制。已移除 `static/src/panels/skills.js` 中 MCP 服务器信息面板的「复制全部信息」按钮，改为：







  - 每条启动命令 `<code class="msi-cmd">` 右侧出现小复制按钮，点击仅复制该条命令。







  - 外部客户端配置 JSON `<pre class="msi-pre">` 上方出现「复制配置」按钮，点击仅复制该 JSON。







  - 新增 `renderCopyBtn(text, title, label)` 辅助函数与 `.msi-copy` 小按钮样式，保留 `copyText()` 复用 Clipboard API / `execCommand` 降级。







  - DOM 结构由字符串 `innerHTML` 重构为 `el()` 构建，避免事件绑定与 HTML 转义隐患。







  复跑门禁：`node --check` skills.js OK；`check_js_modules.py`(29 模块) EXIT=0；`check_skill_gate.py` EXIT=0；铁律全扫改动文件 CLEAN；真实 `.hermes_data` 未触碰。















## [1.4.55] — 2026-08-10















- **修复 MCP 子进程标准错误日志显示为黑块**：用户贴截图，「MCP 子进程标准错误（排障）」文件下方黑乎乎一片。根因：Playwright 等 MCP 在 stderr 里用 `\r` 反复刷新同一进度行（如 `Downloading Chrome: 27%\rDownloading Chrome: 27%\r...`），`readlines()` 按 `\n` 分行后保留行内 `\r`；前端 `<pre>` 渲染时 `\r` 让光标回到行首，所有进度文字叠加成实心黑块。已在 `routes/logs.py` 新增 `_sanitize_text()`：去掉 ANSI 转义码、把 `\r\n` 统一为 `\n`、对每行按「回车覆盖」语义只保留最后一个 `\r` 之后的内容、删除其他非打印控制字符；`static/src/panels/logs.js` 的 `_renderLine()` 也做前端二次防御。`mcp-stderr.log` 实测：原最后一行含 150+ 次重复进度，清理后正确显示为单行「Downloading Chrome: 27%」。复跑门禁：`py_compile` routes/logs.py OK；`node --check` logs.js OK；`check_js_modules.py`(29 模块) EXIT=0；`check_skill_gate.py` EXIT=0；铁律全扫改动文件 CLEAN；真实 `.hermes_data` 只读未修改。















## [1.4.54] — 2026-08-10















- **MCP 市场改为「动态代理 LobeHub」，不再预烤全量数据**：用户明确指出「不应把 86k 条 MCP 信息全部固定在系统里（应用体积会无限大），要像嵌入网站一样动态获取」，要的是可查找/搜索/安装**所有** MCP 的真正「市场」，而非精选列表。重构 `mcpstore_client.py` 与 `mcpstore.js`：







  - 浏览/搜索/翻页：`/api/mcp-store/servers` 现在**实时**拉取 LobeHub 列表页（解析 RSC 流里的 JSON-LD `ItemList`，含真实 `description`），全站 86,304 个 MCP 全部可搜可翻；仅做内存短缓存（分页 10min / 详情 24h），绝不落盘。







  - 安装：点「安装」时按 slug **实时**拉取该 MCP 详情页，抽取真实 `command`/`args`/`env`（LobeHub 详情页内置启动配置），从而实现全站「一键安装」；需 Key 的自动弹 env 收集框。







  - 旧实现根因：原正则找错数据结构（列表条目藏在 RSC 的 JSON-LD 中，非 `identifier/name/description` 紧邻），几乎全不匹配 → 退化为「只有 slug、描述为空」；且只抓第 1 页 → 数量极少。







  - 发布者(owner)：取自 slug 命名空间（真实 GitHub org/user），无需额外请求。分类：来自详情页 `?category=` 链接。







  - **热度(下载量)：LobeHub 任何页面均不暴露，已如实告知用户，绝不编造数字**，卡片仅以「LobeHub」来源标识。







  - 精选目录(`CURATED_CATALOG`)保留为「已知可一键安装」的离线降级/合并覆盖（按 slug 命中时补入验证过的 command/args/env）。







  - 新增路由 `/api/mcp-store/meta/{slug}`；安装路由对精选中不存在的 slug 自动回退到 LobeHub 详情取配置。







  - 验证：`py_compile`(mcpstore_client.py / skills.py) OK；`node --check` mcpstore.js OK；`check_js_modules.py`(29 模块) EXIT=0；`check_skill_gate.py` EXIT=0；铁律全扫改动文件 CLEAN；真实 `.hermes_data` 未触碰。功能实测：默认浏览返回 10 条带真实描述条目、搜索 playwright/github 命中、tavily 详情页成功抽出 `TAVILY_API_KEY`。















## [1.4.53] — 2026-08-10















- **修复对话区标题栏覆盖功能面板**：进入模型 / 技能 / 工具 / MCP / Kanban 等非「对话」视图时，主区顶部的 `.topbar`（含「新对话」标题、搜索、皮肤、主题、用量、全量导出、配置、工具调用信息等按钮）仍然显示，压在功能面板自身内容上方，导致「标题栏出现在每一个功能界面的窗口上，覆盖原有内容」。已在 `static/src/views.js` 的 `showView()` 中添加：非对话视图时隐藏 `.topbar`，切回「对话」视图时恢复显示。验证：`node --check static/src/views.js` OK；`check_js_modules.py`(29 模块) EXIT=0；`check_skill_gate.py` EXIT=0；铁律全扫改动文件 CLEAN；真实 `.hermes_data` 未触碰。















> 技能版本与事实基线变更记录。每次实质改动后追加一条，version 号 **+0.0.1**（与实际递增惯例一致；最新 version 见 SKILL.md frontmatter）。















> **历史说明（参考文档合并与重排）**：早期 `references/18-goals-integration.md`、`references/19-snapshot-integration.md` 等（编号 18–31）已合并入 `references/17-capability-integrations.md`；2026-08-10 又对 references 目录做了**连续编号重排**（`17-capability-integrations.md` → `11-capability-integrations.md` 等，详见 `references/README.md` 合并历史）。本文件旧条目中若仍出现对旧编号（`references/17`、`references/18`、`references/19` 等）的链接均属当时实况记录，请以 `references/README.md` 索引为准。















## [1.4.52] — 2026-08-10















- **修复统一 MCP 面板样式完全失效**：上一版 `1.4.51` 改造 MCP 面板时引入两处样式断裂：① 外层 Tab 容器（`mcp-unified`/`mcp-tabs`/`mcp-tab`/`mcp-subpanel`）未在 `static/app.css` 定义，导致服务器/客户端切换 Tab 无布局、无激活态；② MCP 客户端商店容器 `mcpClientSub` 未保留原 `mcp-store` 类，导致 `mcpstore.js` 内所有 `.mcp-store .ms-*` 选择器失效，商店卡片、网格、徽章、按钮全部变回未样式化的原生元素，界面完全破坏。已修复：在 `static/app.css` 补齐 `.mcp-*` Tab 与子面板样式；在 `static/src/panels/skills.js` 把 `mcpClientSub` 的 class 改为 `"mcp-subpanel mcp-store hidden"`，恢复商店完整样式。验证：`py_compile` pages.py OK；5 个改动 JS 模块 `node --check` OK；`check_js_modules.py`(29 模块) EXIT=0；`check_skill_gate.py` EXIT=0；铁律全扫改动文件 CLEAN；真实 `.hermes_data` 未触碰。















## [1.4.51] — 2026-08-10















- **UI 改造：统一「工具」面板 + 统一「MCP」面板**（应需求：消除入口割裂与功能混淆）：







  - **统一工具面板**：原左侧「工具集成」与「工具清单」两个独立入口合并为一个「工具」入口，内部含两个子面板（Tab 切换）——「工具清单（只读）」罗列 Hermes 注册表全部工具（name / 工具集 / 入参 / 来源，对齐 `tools.registry`），「工具管理（可操作）」承载原工具集成（启用 / 配置 / 测试 / 试用工具集）。**新增「一键直达」**：清单中点击任一工具集卡片 → 自动切到「工具管理」子面板并滚动 / 高亮定位到对应工具集（`data-toolset` 精确匹配 + 名称包含兜底）。后端 `/api/tools-catalog` 端点与 `tools_catalog.py` 路由保留（仅前端视图并入统一面板，无 API 删除）。







  - **统一 MCP 面板**：原单一 MCP 入口内部明确拆分为两个子面板（Tab 切换）——「MCP 服务器（本应用作为服务器）」只读展示启动命令与外部客户端配置，并新增「📋 复制全部信息」按钮（结构化纯文本：传输 / 启动命令 / `client_config` JSON / 说明 / 安全提示，优先 Clipboard API 降级 `execCommand`），便于用户粘贴到其他 MCP 客户端；「MCP 客户端（连接外部服务器）」承载原 MCP 商店（浏览 / 安装 / 管理外部 MCP 服务器），挂载容器由 `mcpStoreRoot` 改为 `mcpClientSub`。







  - **改动文件**：`routes/pages.py`（导航与视图容器）、`static/src/panels/tools.js`（新增 `renderToolsPanel` 统一入口 + `data-toolset` + 一键直达）、`static/src/panels/toolscatalog.js`（卡片点击跳转）、`static/src/panels/skills.js`（`renderMcpPanel` 拆分 Tab + 复制按钮）、`static/src/views.js`（移除 `tools_catalog` 视图、死代码清理）、`static/src/commands.js`（`/tools` 高亮匹配 `data-toolset`、`/toolscatalog` 改开统一面板清单子面板）、`static/app.css`（子面板 / Tab / 复制按钮样式）。







  - **验证（万无一失）**：`py_compile`(pages.py) 通过；5 个改动 JS 模块 `node --check` 全过；铁律全扫改动文件 CLEAN（无兄弟技能名 / 机器路径 / 外部项目名）；`tools_catalog` 视图与 `mcpStoreRoot` 残留引用已清零（仅 `mcpstore.js` 防御性自动初始化探测，无害）；真实 `.hermes_data` 未触碰。















## [1.4.50] — 2026-08-10















- **看板（Kanban）对照 OpenAI Symphony 批判与完善**：







  - **研究**：文章《OpenAI 官方开源 Symphony》描述「看板即 Coding Agent 调度台」；实证 Hermes 0.18.2 内核 `kanban_db` 支持 9 种状态、`priority` 字段、`task_runs` 心跳/看门狗调度基础设施、`kanban_list` 返回含 `priority`/`created_at`；示例的「看板调度循环」(`frameworks/loops.py` `kanban`) 已实现 Symphony 核心闭环（读看板→`agent.chat` 执行→写 `kanban_comment`→`kanban_complete`）。







  - **批判（5 处）**：① 前端看板卡片不显示优先级（后端已返回却未渲染）；② `STATUS_BUCKET` 漏 `review`/`archived` 两状态（错误归进「待办」、徽标显示原始英文）；③ 调度循环未按优先级派发；④ 覆盖矩阵「完整」过笼统（未区分「覆盖 Hermes 原生看板」与「等价于外部调度器」）；⑤ 自调度核心能力未在任何文档被「看见」。







  - **完善**：前端卡片补「优先级 N」徽标；`STATUS_BUCKET` 增 `review→in_progress`(待审核)、`archived→done`(已归档) 并补中文标签；调度循环 `pending.sort(key=priority↓,created_at↑)`；覆盖矩阵 Kanban 行精确化并指向新文档；新增 `docs/kanban-vs-symphony.md` 诚实对照（含「未做」边界：外部看板适配器/并发/独立工作区/重试/实时仪表盘，均不虚构）。







  - **验证（万无一失）**：`py_compile`(loops.py) 通过；`check_js_modules.py`(29 模块，含 views.js) 退出码 0；`check_skill_gate.py` 退出码 0；改动前快照 `views.js/loops.py/coverage.md.pre-kanban.bak` diff 确认最小改动（views 增 2 段、loops 增 1 行排序、coverage 改 1 行）；铁律全扫 CLEAN；真实 `.hermes_data` 未触碰。















## [1.4.49] — 2026-08-10















- **references 目录重构（编号连续化 + 结构修复）**：







  - **编号重排**：将 references 目录改为连续编号 `00–11`，消除断档。映射：`03→02`、`04→03`、`05→04`、`06→05`、`07→06`、`09→07`、`10→08`、`11→09`、`12→10`、`17→11`；`00`、`01` 不变。







  - **结构修复**：`11-capability-integrations.md` 修复 22 处标题层级倒挂（注入的 `## 一、/## 三、` 降级为 `####`）、清理 15 处重复 `---` 分隔符、修复自引用与过期 `references/19` 引用。







  - **断链修复**：全技能更新 31 个文件的旧编号引用；修复 7 处指向已合并文件（`02/13/14/15/07/08/16` 及 `17–31`）的断链，改指向新编号对应锚点；修复裸文件名引用与链接 URL 不一致。







  - **新增主索引**：`references/README.md` 列出全部文件、主题、锚点及合并历史映射。







  - **验证**：全技能扫描确认所有 `references/NN-*.md` 引用均指向真实存在的文件（0 断链）。















## [1.4.48] — 2026-08-10















- **A2A（Agent-to-Agent）功能（深度研究 Hermes Library 机制 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证：`agent/`、`hermes_cli/`、`run_agent.py` 源码 + `hermes-llms-full.txt` 全文 + 运行期枚举）**：







    - **0.18.2 无第一类的 A2A 协议功能**：无 `a2a` 模块、无 `agent_card`/`task_store`/`remote_agent`；`AIAgent` 类不暴露任何 A2A 方法；官方文档未把 A2A 列为功能章节。







    - 文档仅 3 处零散 "A2A / agent-to-agent" 提及：① 飞书 bot-to-bot 消息（`FEISHU_ALLOW_BOTS`，"Hermes to participate in A2A orchestration"），依赖 gateway/飞书适配器；② here.now 云盘 "agent-to-agent handoff"（数据交接）；③ 第三方社区新闻。







    - 示例的「多智能体」均为**进程内编排**，非跨系统 A2A：委派/Delegation（`delegate_task`，同进程 spawn 子 Agent）、MOA 多智能体混合（虚拟 provider `moa`，`references/17` 明确「不是命令，也不是 A2A」）、Kanban 编排、Honcho 多 profile。







  - **批判发现（1 处准确性缺口）**：覆盖矩阵有「委派 ✅ 完整」「MOA ✅ 已接原生」两行，却**无 A2A 行**，研究者易误以为 Hermes 具备跨系统 A2A 协议（名不副实风险）。示例未把任何功能标榜为 A2A、未引用 Google A2A——本身合规。







  - **完善（最小/自包含/零铁律违规）**：① 覆盖矩阵新增 `A2A 协议（跨系统 Agent 互操作）` 行，明确「0.18.2 无 `a2a` 模块、无 `agent_card`/`task_store`/`remote_agent`；多智能体仅限进程内委派/MOA；唯一 agent-to-agent 触点为飞书 bot-to-bot，桌面进程内路线不适用」；② 新增 `examples/01-hermes-desktop/docs/a2a-audit.md`（研究事实+批判+边界澄清，风格对齐 `mcp-audit.md`/`slash-commands-critique.md`）。







  - **验证（万无一失）**：`scripts/check_skill_gate.py` 退出码 0；改动前快照 `coverage.md.pre-a2a.bak` diff 确认仅新增 1 行 A2A 行；铁律全扫改动文件 CLEAN；全技能再扫外部项目名零命中；真实 `.hermes_data` 未触碰（仅扫描发现示例数据含 `sk-or-v1-...` 密钥，未读改，建议替换为占位/环境变量）。**未新增任何 A2A 运行时代码**（无 API 可集成，虚构即违诚实红线）。















## [1.4.47] — 2026-08-10















- **斜杠命令 Slash Commands（深度研究 Hermes Library 机制 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/commands.py`+`gateway/slash_commands.py`+`gateway/slash_access.py`+`tools/slash_confirm.py`，并运行期枚举 `COMMAND_REGISTRY` 核实）**：







    - **两层结构**：① 元数据注册表 `COMMAND_REGISTRY`（`CommandDef`：name/aliases/description/category/args_hint/cli_only/gateway_only/gateway_config_gate），三处环境共享的唯一真相源；② 具体实现分散在 Gateway（`gateway/slash_commands.py` 的 `GatewaySlashCommandsMixin`，源文件自述约 42 个会话内 handler，由 `_handle_message` 派发）、WebUI（`hermes_cli/web_server.py`）、CLI（`hermes_cli/cli_commands_mixin.py`），**无统一可 import 的 handler**。







    - **网关访问控制**：`gateway/slash_access.py`（`SlashAccessPolicy`/`policy_for_source`），DM vs Group 双维度 + `allow_admin_from`/`user_allowed_commands`；未配置管理员则门控整体关闭（向后兼容），兜底 `_ALWAYS_ALLOWED_FOR_USERS={help,whoami}`。







    - **权威清单（枚举确认）**：总数 **82**；`cli_only` **29**（clear/redraw/history/save/prompt/handoff/snapshot/journey/config/statusbar/timestamps/verbose/skin/indicator/busy/tools/toolsets/skills/pet/hatch/cron/reload/browser/plugins/billing/platforms/copy/paste/image/quit）；`gateway_only` **8**（start/topic/approve/deny/sethome/commands/restart/platform）；别名（部分）new→reset、compress→compact、snapshot→snap、version→v、quit→exit 等。







    - **本技能路线（进程内 Library + 桌面 GUI，不起网关/不走 HTTP）**：网关专属与 cli_only(TTY) 指令天然无桌面等价物；示例只做「桌面可行」子集。







  - **批判发现（名不副实/孤儿文档 + 陈旧集合条目）**：







    1. **名不副实/孤儿文档（高）**：`docs/gap/slash-commands-critique.md` 被 `gap-fathah.md`(×3)、`external-cases.md`、`gap-webui.md` 引用为「完整分析」但该文件此前不存在 → **本次补建**（含真实机制、82 条权威清单、示例实现对照、4 条批判与已知别名边界说明）。







    2. **陈旧集合条目（中）**：`frameworks/commands.py` 的 `FRONTEND_COMMANDS` 含 `llm`——0.18.2 注册表无此指令（枚举 `HAS_llm=False`），属陈旧理解残留 → **已移除**；`TERMINAL_BOUND` 含 `snap`——真实规范名是 `snapshot`（`snap` 仅为其别名），分类以规范名比对故 `snap` 永不匹配 → **已改为 `snapshot`**。







  - **验证（万无一失）**：`py_compile`(`frameworks/commands.py`) 通过；运行期直接加载示例模块复算 `classify_command`：`snapshot→terminal`、`llm→agent`、`model/status/skills→server`、`start/topic→gateway`、`clear/new/help→frontend`、`prompt/redraw→terminal`，`native_command_count` 总数 82 且五桶(3+10+8+3+58)之和=82；`scripts/check_skill_gate.py` 与 `scripts/check_js_modules.py` 均退出码 0（29 前端模块全绿，无回归）；铁律全扫改动文件 CLEAN（无兄弟技能名/机器专属路径/外部项目名）；全技能再扫零命中；改动前快照 `frameworks_commands.py.pre-slash.bak` diff 确认最小改动（删 `llm` 1 处 + `snap`→`snapshot` 1 处 + 2 行注释）；真实 Hermes 配置/数据未触碰（仅用临时 `HERMES_HOME`）。















## [1.4.46] — 2026-08-10















- **MCP Client / Server（深度研究 Hermes Library MCP 机制 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/subcommands/mcp.py`+`hermes_cli/mcp_config.py`+`tools/mcp_tool.py`+`hermes_cli/mcp_security.py`+`mcp_serve.py`+`agent/transports/hermes_tools_mcp_server.py` 全文）**：







    - **MCP Client**：`hermes mcp` 子命令全集 = `serve/add/remove/rm/list/ls/test/configure/config/login/reauth/picker/catalog/install`；配置落点 `~/.hermes/config.yaml` 的 `mcp_servers` 键；传输支持 **stdio + HTTP/StreamableHTTP + SSE**（`transport: sse` 走 SSE，否则默认 StreamableHTTP）；工具发现后并入 Agent 工具注册表，toolset 名 `mcp-<server>`、工具名加 `mcp-<server>-` 前缀；实际连接由**内嵌 AIAgent 在会话启动时**调用 `tools.mcp_tool.register_mcp_servers` 完成（非桌面进程常驻）；安全校验 `validate_mcp_server_entry` 三重拦截（硬编码 IOC 黑名单 / shell 解释器+网络外泄 / shell 解释器+OS 持久化写入），保存与生成双保险。







    - **MCP Server 两种形态（均为独立 stdio 进程，需 mcp 包，与本应用「进程内直跑、不起第二个进程」原则不冲突——示例自身不内嵌，用时单独起命令）**：①会话桥接 `hermes mcp serve`（暴露会话/消息/审批，实测 10 工具，与文档表逐字一致）；②工具面暴露 `python -m agent.transports.hermes_tools_mcp_server`（FastMCP，26 个精选工具，面向 Codex 集成，刻意不暴露 `terminal`/`read_file`/`write_file` 等）。







  - **批判发现（事实错误 + 铁律违反 + 名不副实）**：







    1. **铁律违反（最严重）**：`mcpstore_client.py` 与 `skillhub_client.py` 的 `User-Agent` 字符串硬编码了外部业务项目名，属禁止的专属标识泄露 → 泛化为 `Hermes Desktop MCP store client` / `Hermes Desktop SkillHub client`。







    2. **名不副实 + 孤儿端点**：`commands.js` 将面板注册为「打开 MCP 服务器面板」，但面板只渲染客户端商店；后端只读端点 `/api/mcp-server/info`（已建）从未被前端引用 → 在 `renderMcpPanel` 增加「MCP 服务器（本应用作为服务器）」只读信息卡（`renderMcpServerInfo` fetch 并展示该端点：mcp 包可用态、两种启动命令、外部客户端配置片段、设计边界与安全提示），命令改名为「打开 MCP 面板」。







    3. **文档过度宣传**：`docs/mcp-server.md` 首行称「MCP 客户端（本应用已实现）」过度——示例仅实现目录浏览+安装+管理 UI + 在 AIAgent 会话内连接，并非自管客户端运行循环 → 改为如实表述。







    4. **文档无据声明**：`docs/mcp-server.md` 称会话桥接「在 TUI Console 中被禁用」，源码（`mcp_serve.py` Grep `tui|console|disabled`）无此证据 → 移除，改为「需安装 mcp 包，`-v` 可看版本与工具列表」。







    5. **覆盖矩阵笼统**：`docs/gap/hermes-vs-frontend-coverage.md` 把 MCP 整行标「完整」，未区分 Client（已实现商店+连接）与 Server（仅只读信息页、无独立 UI 入口）→ 拆成两行如实标注。







    6. **历史专属名字样**：`README.md` 与 `CHANGELOG.md` 旧条目含外部业务项目名缩写 → 泛化处理。







  - **验证（万无一失）**：`py_compile`(mcpstore_client.py/skillhub_client.py/routes/mcp_server.py/routes/skills.py) 全绿；`node --check`(.mjs 强制 ES 模块) + `scripts/check_js_modules.py`(29 模块语法+跨模块 import/export 链接) 退出码 0（含改动 skills.js/commands.js）；`scripts/check_skill_gate.py` 退出码 0；铁律全扫改动文件（禁兄弟技能名/机器专属绝对路径/外部业务项目名）CLEAN（全技能再扫 `RDExpenseSystem|rd-expense|研发费用` 零命中）；改动前快照 `hermes-desktop-dev-notes/snapshots/*.pre-mcp.bak` diff 确认最小/附加式改动（2 py 各改 1 行 UA、skills.js 增服务器信息卡、commands.js 4 处改名、2 md 小改、CHANGELOG 1 行泛化）；真实 `.hermes` 数据/配置未被触碰（仅改源码与文档）。















## [1.4.45] — 2026-08-10















- **工具清单 Tools Catalog（深度研究 Hermes Library Tools / Toolset 机制 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`toolsets.py`+`tools/registry.py`+`model_tools.py`+`agent_runtime.py` 全文）**：Hermes 工具由**全局单例注册表** `tools.registry` 统一托管；每个工具模块在**导入期**调 `registry.register(name, toolset, schema, handler, check_fn=None, requires_env=None, is_async=False, description="", emoji="", max_result_size_chars=None, dynamic_schema_overrides=None, override=False)` 自注册。`ToolEntry` 含 `name/toolset/schema/handler/check_fn/requires_env/is_async/description/emoji/max_result_size_chars/dynamic_schema_overrides`。`register` 含**跨工具集阴影防护**：不同 toolset 同名工具除非 `override=True`（插件需 `allow_tool_override` 显式 opt-in）否则被拒；MCP 同名工具集（`mcp-*`）间允许覆盖。`check_fn` 带 **30s TTL + 60s 失败宽限**缓存（外部探测抖动不静默剥离工具）。工具集在 `toolsets.py` 的 `TOOLSETS` 字典定义，经 `get_toolset`/`resolve_toolset`/`resolve_multiple_toolsets`（`"all"/"*"` 别名、环检测、钻石去重）递归解析；`create_custom_toolset` 支持自定义工具集；`bundle_non_core_tools` 剔除核心工具仅返回平台增量。公开 API：`model_tools.get_tool_definitions(enabled_toolsets, disabled_toolsets, quiet_mode)`、`handle_function_call`、`TOOL_TO_TOOLSET_MAP`、`TOOLSET_REQUIREMENTS`、`get_all_tool_names()`、`get_toolset_for_tool(name)`、`get_available_toolsets()`、`check_toolset_requirements()`、`check_tool_availability(quiet)`。接线：`agent_runtime.register_pure_python_tools()`（幂等）先 `discover_builtin_tools()` 导入并注册全部内置工具模块，再 `file_tools.register_into`/`host_tools.register_into`/`tools.delegate_tool`（原生委派），最后调用**用户扩展点** `app_tools.register_into(registry)`（业务自定义工具，安全且地道）；`build_agent` 的 `disabled_toolsets` 在构造时剔除 `terminal`（架构默认禁用，安全窄腰）。







  - **批判发现（能力缺口，非事实错误）**：示例 Tools 能力**已较完整**（工具集管理/试用/安装依赖/配置/测试，见 `routes/toolsets.py` + `agent_runtime.discover_toolsets`），但**缺失"工具清单 / 工具目录"**——把每个工具（Hermes 原生 + 用户自定义）的 `name`、所属 `toolset`、`description`、入参 `schema`（JSON Schema 结构）以**可读清单**呈现给用户。覆盖矩阵虽标 Tools「完整」，实则缺 catalog——属「能力缺口」，以「补齐工具清单 + 如实标注」处理。







  - **完善（从零补齐，沿用既有接线；后端仅读 `tools.registry` 元信息，零密钥暴露、零配置写入、零 `.hermes_data` 触碰；区分 Hermes 原生 vs 本示例注入）**：新增 `routes/tools_catalog.py`（只读列举已注册工具：调用 `ar.register_pure_python_tools()` 确保已注册，再从 `tools.registry.registry` 读 `_tools`；`_origin_of` 按 handler 模块前缀区分 `hermes_builtin`（`tools.*`）/ `example_injected`（`file_tools`/`host_tools`/`app_tools`）/ `other`；`_schema_summary` 兼容内层 `function` 写法与外层的 `{type:"function",function:{...}}` 写法，提取 `parameters.properties` 为字段表；`/api/tools-catalog`（GET）经 `_guard` 包异常；`_build_catalog` 返回 `count/tools/by_toolset/origin_counts/note`，`note` 明示「密钥由 Hermes 托管、不返回任何密钥」）；`routes/__init__.py` 追加 `tools_catalog` 导入；新增 `static/src/panels/toolscatalog.js`（`renderToolsCatalogPanel`：顶部如实说明密钥托管；概览徽标（工具总数/Hermes 内置/本示例注入/工具集数）；搜索 + 工具集下拉 + 来源下拉 + 刷新；按工具集分组卡片，每张卡显 name/emoji/工具集徽标/来源徽标/异步/所需环境变量 + 入参参数表（name/type/必填/说明）；仅读注册表，不写盘）；`static/src/panels.js` 桶导出 `renderToolsCatalogPanel`；`static/src/views.js` 新增 `renderToolsCatalogView` 并登记 `VIEW_RENDERERS`；`routes/pages.py` 左侧栏「功能」组（紧接「工具集成」后）新增「🔧 工具清单」导航 + 主区 `view-tools_catalog`；`static/src/commands.js` 新增 `/toolscatalog [open]` 指令；`static/app.css` 新增 `.toolcat-*` 样式（深色等宽、徽标、参数表）；`docs/gap/hermes-vs-frontend-coverage.md` 补 Tools 工具清单行（如实标「已接 Hermes 原生注册表（只读列出全部工具 name/toolset/description/入参 schema，区分 Hermes 内置 vs 本示例注入；密钥由 Hermes 托管，零写盘、零碰 .hermes_data）」）。







  - **验证（万无一失）**：`py_compile`(`routes/tools_catalog.py`/`routes/__init__.py`) + `node --check`(4 个 JS) 全绿；`scripts/check_js_modules.py` 退出码 0（29 个前端模块强制 ES 模块语法 + 跨模块 import/export 链接全部 OK，含新增 `toolscatalog.js`）；铁律全扫 9 个改动文件（禁兄弟技能名/机器专属绝对路径/外部业务项目名）CLEAN（路径构造一律走 `Path.home()`/`LOCALAPPDATA`，无任何写死机器路径或外部业务项目名）；`scripts/check_skill_gate.py` 退出码 0；改动前快照 `pre-tools-20260810T1430` diff 确认最小/附加式改动（7 文件小改 + 2 新文件，全为增量）。**隔离功能测试 PASS**：在真实 Hermes venv 中以 `HERMES_DESKTOP_HOME` 指向临时目录跑 `register_pure_python_tools()` + 读 `tools.registry`，**枚举到 74 个工具**、抽样 schema/description 齐备（5/5）、来源分类正确（65 Hermes 内置 + 9 本示例注入）、入参字段解析正确（`browser_cdp` → method/params/target_id/...）、二次注册幂等（`already=True`）、真实 `.hermes_data` 未被触碰。







  - **诚实边界（非缺陷，设计如此）**：本接口**仅读取**注册表元信息，绝不执行 handler、不持有/打印/落盘任何密钥（`requires_env` 只列所需环境变量名、不列其值）；工具的 API 密钥由 Hermes 在进程内托管（config.yaml/环境变量）；覆盖矩阵 Tools 行维持「完整 ✅」（工具集管理能力已全），新增的 catalog 行单独标注，避免对既有「完整」结论做不实改写。















## [1.4.44] — 2026-08-10















- **结构化输出 Structured Output（深度研究 Hermes Library Structured Output 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`agent/plugin_llm.py`+`agent/auxiliary_client.py`+`tools/schema_sanitizer.py`+`agent/moonshot_schema.py` + 官方文档全文）**：Hermes 结构化输出有**两种 `response_format`**——①`json_schema`（把 schema 嵌进 `response_format.json_schema.schema`，`name` 固定 `plugin_structured_output`、`strict=False`）；②`json_object`（仅要求返回 JSON）。门面 `PluginLLM.complete_structured(instructions, input, json_schema, json_mode, schema_name, ...)` **仅在受信任插件的 `ctx.llm` 上可用**（示例不是插件、拿不到 `ctx.llm`）。背后流程：在 system 追加「只回一个 JSON 对象、不要散文/代码围栏」约束、在 user 头追加 `Schema name:` 与 `JSON schema:`、把 `response_format` 塞进 `extra_body`、拿到文本后先剥 ```json 围栏再 `json.loads`、有 schema 时跑 `jsonschema.validate`（jsonschema 是可选依赖，缺失则跳过严格校验）。密钥由 `get_text_auxiliary_client(task)` 返回的 **host-owned** OpenAI 兼容客户端托管，调用方看不到 provider/auth。`AIAgent`(run_agent) 不直接收 `response_format`，仅经 `request_overrides` 透传。







  - **批判发现（能力缺口，非事实错误）**：覆盖矩阵 `hermes-vs-frontend-coverage.md` **整行漏列 Structured Output**；`panels/` 与 `routes/` 均无结构化输出能力——示例完全缺失结构化输出。属「能力缺口」而非「虚构」，以「补齐 + 如实标注」处理。







  - **完善（从零补齐，沿用既有接线；后端仅用 host-owned 客户端，密钥零暴露、只读取模型输出、不写盘不改配置不碰 `.hermes_data`；模型未配置时优雅降级）**：新增 `routes/structured.py`（对齐真实 `agent/plugin_llm.py` 语义：围栏剥离、`_validate_against_schema`（jsonschema 缺失则跳过）、`_parse_and_validate`、`_build_structured_messages`、`_json_response_format`、`_validate_only`（离线校验）、`_run_structured_sync`（经 `get_text_auxiliary_client("")` 取 host-owned 客户端，client/model 缺失→`{available:False, error:...}`），两路由 `/api/structured/run`、`/api/structured/validate`）；`routes/__init__.py` 追加 `structured` 导入；新增 `static/src/panels/structured.js`（顶部如实说明「密钥由 Hermes 托管、本面板看不到；校验纯本地无需联网」；①运行：指令必填+输入可选+模式[Schema/Object]+Schema 文本框+名称/温度/最大令牌+「填入示例」+「运行」；②离线校验：JSON+可选 Schema+「校验」；结果区渲染模型/内容类型/校验徽章+原始返回+解析后 JSON 美化）；`static/src/panels.js` 桶导出 `renderStructuredPanel`；`static/src/views.js` 新增 `renderStructuredView` 并登记 `VIEW_RENDERERS`；`routes/pages.py` 左侧栏「系统」组新增「🔣 结构化输出」导航 + 主区 `view-structured`；`static/src/commands.js` 新增 `/structured [open]` 指令；`static/app.css` 新增结构化面板样式；`docs/gap/hermes-vs-frontend-coverage.md` 补 Structured Output 行（如实标「已接 Hermes 原生（触发 host-owned 结构化补全 + 离线 JSON Schema 校验，对齐 Library；模型未配置时优雅降级，密钥由 Hermes 托管）」）。







  - **验证（万无一失）**：`py_compile`(`routes/structured.py`/`routes/__init__.py`) + `node --check`(4 个 JS) 全绿；铁律全扫 9 个改动文件（禁兄弟技能名/机器专属绝对路径/外部业务项目名）CLEAN；`scripts/check_skill_gate.py` 退出码 0；改动前快照 `pre-structured-20260810T1344` diff 确认最小/附加式改动（6 文件小改 + 2 新文件）；真实示例 `.hermes_data` 未被触碰（隔离功能测试 `HERMES_DESKTOP_HOME` 指向临时目录，实际 mtime 维持 09:57:59 不变）。**隔离功能测试 20/20 PASS**：围栏剥离、JSON 解析(成功/失败/空)、schema 校验(通过/失败仍回传 parsed)、离线校验(合法/非法/非 JSON/无 schema/ schema 非对象)、`response_format`(None/json_object/json_schema 含固定 name 与 strict=False)、消息构建(system 约束+schema name+JSON schema+input 分段)、模型未配置优雅降级(`available:False`)、`agent` 导入失败兜底 `_err`。







  - **诚实边界（非缺陷，设计如此）**：示例非插件、无 `ctx.llm`，故不调 `complete_structured`，改用 `get_text_auxiliary_client("")` 复刻**完全相同**的 `response_format`+系统提示词约束，忠实复刻 Library 行为且密钥零暴露；面板仅触发补全与离线校验、**不持有/不打印/不落盘任何密钥**；「模型不支持 `response_format` 时以系统提示词兜底要求输出 JSON」、输出格式仍以模型实际返回为准；离线校验纯本地、无需联网、不触发模型。















## [1.4.43] — 2026-08-10















- **日志查看（深度研究 Hermes Library Logging 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_logging.py`+`hermes_cli/logs.py`+`subcommands/logs.py`+`console_engine.py` + 官方文档全文）**：Hermes 日志统一落在 `<HERMES_HOME>/logs/`，按大小自动轮转（Windows 用 `concurrent_log_handler` 规避 `WinError 32`）。**六类日志文件**：`agent.log`（INFO+，主日志）、`errors.log`（WARNING+）、`gateway.log`（仅 gateway 组件，gateway 模式才生成）、`gui.log`（控制面板/WebSocket/TUI，gui 模式才生成）、`desktop.log`（桌面壳）、`mcp-stderr.log`（MCP 子进程 stderr）。写入时由 `RedactingFormatter` 脱敏，**密钥不落盘**。配置在 `config.yaml` 的 `logging.level`/`logging.max_size_mb`/`logging.backup_count`。CLI `hermes logs [agent|errors|gateway|gui|desktop|mcp|list]`，支持 `-n/--lines`、`-f/--follow`、`--level`、`--session`、`--since 1h/30m/2d`、`--component gateway/agent/tools/cli/cron/gui`（按日志器名前缀过滤）。行格式：`%(asctime)s %(levelname)s%(session_tag)s %(name)s: %(message)s`，`session_tag = " [sid]"`（在日志器名之前）。**未发现**面向量化控制面板的非交互日志 API（与 Plugin 不同——Plugin 有 `dashboard_*` 系列，日志无），故面板以只读调用示例自身日志文件实现。







  - **批判发现（能力缺口，非事实错误）**：覆盖矩阵 `hermes-vs-frontend-coverage.md` **整行漏列 Logs**；`panels/` 与 `routes/` 均无日志查看能力——示例完全缺失日志查看。属"能力缺口"而非"虚构"，以"补齐 + 如实标注"处理。







  - **完善（从零补齐，沿用既有 plugins 接线模式；后端仅读 `<HERMES_HOME>/logs`，作用域严格限定示例自身，不碰真实 ~/.hermes）**：新增 `routes/logs.py`（对齐真实 `hermes_cli/logs.py` 语义的只读后端：列出 6 类日志 + 大小/mtime/是否存在、按级别(>=)/组件前缀/会话 ID 子串/相对时间过滤读取末尾 N 行、读 `config.yaml` 的 `logging.*`；文件不存在时优雅返回"尚未生成"）；`routes/__init__.py` 追加 `logs` 导入；新增 `static/src/panels/logs.js`（顶部如实说明"密钥已脱敏、仅读取"；日志文件选择按钮行、过滤条、行级彩色渲染）；`static/src/panels.js` 桶导出 `renderLogsPanel`；`static/src/views.js` 新增 `renderLogsView` 并登记 `VIEW_RENDERERS`；`routes/pages.py` 左侧栏"系统"组新增"📜 日志"导航 + 主区 `view-logs`；`static/src/commands.js` 新增 `/logs [open]` 指令；`static/app.css` 新增日志面板样式；`docs/gap/hermes-vs-frontend-coverage.md` 补 Logs 行（如实标"只读查看：列表+级别/组件/会话/时间过滤（密钥已脱敏，不写不删）"，不写"完整 ✅"）。







  - **验证中修复的真实缺陷（正则鲁棒性）**：原 `_LOGGER_NAME_RE`/`_LEVEL_RE` 仅能解析 `[session]` 在日志器名**之前**的官方格式；为防跨版本/第三方桥接出现"日志器名 [session]:"顺序，已加固为同时兼容两种顺序，并加单测证明。







  - **验证（万无一失）**：`py_compile`(`routes/logs.py`/`routes/__init__.py`) + `node --check`(4 个 JS) 全绿；铁律全扫 `routes/logs.py`/前端（无兄弟技能名/机器专属绝对路径/外部业务项目名）CLEAN；`scripts/check_skill_gate.py` 退出码 0；改动前快照 `pre-logs-20260810T1324` diff 确认最小/附加式改动（6 文件小改 + 2 新文件）；真实示例 `.hermes_data` 未被触碰（隔离功能测试 `HERMES_DESKTOP_HOME` 指向临时目录）。**隔离功能测试 21/21 PASS**：列全部 6 类日志、级别(>=)/组件/会话/时间过滤、未知日志报错、文件不存在优雅降级、`config.yaml` 读取、脱敏标记、加固正则两种 `[session]` 顺序。







  - **诚实边界（非缺陷，设计如此）**：本面板**仅只读查看**示例自身 `<HERMES_HOME>/logs`，不写不删不改；"配置改级别/轮转大小需重启生效"等概念对示例内部运行时适用、对真实 `~/.hermes` 以官方内核为准；密钥由内核 `RedactingFormatter` 脱敏、不落盘（面板仅如实转述）。















## [1.4.42] — 2026-08-10















- **Plugin 插件集成（深度研究 Hermes Library Plugin 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/plugins.py`+`subcommands/plugins.py`+`plugins_cmd.py`+`agent/plugin_llm.py` + 官方文档全文）**：Hermes 插件有**四类发现源**——①内置 `<repo>/plugins/`；②用户 `~/.hermes/plugins/`；③项目 `.hermes/plugins/`（需 `HERMES_ENABLE_PROJECT_PLUGINS` 才启用）；④pip 入口点 `hermes_agent.plugins`（`importlib.metadata.entry_points()` 枚举，无目录，必须单独发现）。**默认不启用（opt-in）**：只有出现在 `config.yaml` 的 `plugins.enabled` 里的插件才在下次会话真正加载；`plugins.disabled` 是显式黑名单（优先级最高，即使在 enabled 里也不加载）——即"发现 ≠ 加载"。CLI `hermes plugins` 含 `list/install/update/remove/enable/disable`；插件元数据 `plugin.yaml`（name/version/description/author/requires_env/provides_tools/hooks/kind）。`PluginContext` 提供 `register_tool/register_hook/register_command/register_cli_command/register_skill/llm` 等；`VALID_HOOKS` 含 `pre_tool_call/post_tool_call/pre_llm_call/.../pre_gateway_dispatch`。`requires_env` 变量真实落盘位置为 `HERMES_HOME/.env`（由 `hermes plugins install` 写入）。官方库自带面向控制面板的非交互 API：`dashboard_set_agent_plugin_enabled`/`dashboard_install_plugin`/`dashboard_update_user_plugin`/`dashboard_remove_user_plugin`（Desktop GUI 正该用）。







  - **批判发现（4 项缺陷）**：①（A·CRITICAL 事实错误）面板标题写"由 Hermes 内核自动加载，随对话循环生效"，但真实模型是**默认不启用、发现≠加载**，且不显示每个插件的启用/禁用状态——误导用户以为装了就生效。②（B·HIGH 发现源不全）`GET /api/plugins` 只扫描内置包 + `~/.hermes/plugins`，**漏掉 pip 入口点插件**（第④类发现源），列表不完整。③（C·HIGH 失效功能·名不副实）"配置"按钮把 `requires_env` 环境变量存到浏览器 `localStorage`，而真实 Hermes 把变量写到 `HERMES_HOME/.env`——存了等于没存，对内核零作用。④（D·MEDIUM 文档夸大）`hermes-vs-frontend-coverage.md` 标"插件 完整 ✅"，但面板只是只读目录 + 一个假按钮，并无启用/禁用/管理。







  - **完善（对齐真实机制，作用域严格限定示例自身 HERMES_HOME，不碰真实 ~/.hermes）**：`routes/loops.py` 新增 `_plugin_state_sets`（读示例 config.yaml 的 enabled/disabled 名单）/`_plugin_status`（三态 enabled/disabled/not_enabled）/`_plugin_key_from_pkg`（点路径→斜杠键）/`_discover_entrypoint_plugins`（只读枚举 pip 入口点）；`api_plugins` 为每个插件（内置/用户/入口点）补全 `key`/`status`/`enabled` 字段；新增 `POST /api/plugins/toggle`（把标识写入示例 config.yaml 的 enabled/disabled allow-list，并失效插件缓存）、`POST /api/plugins/env`（把 `requires_env` 声明变量写入示例 `HERMES_HOME/.env`，经 `hc.set_env_value`）、`POST /api/plugins/delete`（**仅删 `source=user`**，路径前缀校验防穿越，内置/入口点拒绝）。`hermes_config.py` 新增 `get_env_value`/`set_env_value`（作用域限定 HERMES_HOME/.env）。`static/src/panels/plugins.js` 标题改为"默认不启用：仅 config 中「已启用」的插件会在下次会话真正加载"；卡片新增来源徽章（`pip 安装`）+ 状态徽章（✅已启用/⛔已禁用/⚪未启用）；新增启用/禁用按钮（入口点显示 `pip 管理`）、删除按钮（仅 `source==="user"`）；"配置"保存从 `localStorage.setItem` 改为 `postJSON("/api/plugins/env", {key, values})`。`docs/gap/hermes-vs-frontend-coverage.md` 插件行由"完整 ✅"改为"目录+启用/禁用（安装以官方 CLI 为准）"。**顺带修复潜在崩溃缺陷**：`api_plugin_delete` 引用 `_os`，但 `_os` 仅 `import` 在 `api_plugins` 函数内（局部），`api_plugin_delete` 调用即 `NameError`；已把 `import os as _os` 提到模块顶层。







  - **验证（万无一失）**：`py_compile`(`routes/loops.py`/`hermes_config.py`) + `node --check`(`plugins.js`) 全绿；铁律全扫 4 改动文件（无兄弟技能名/机器专属绝对路径/外部业务项目名）CLEAN；`scripts/check_skill_gate.py` 退出码 0；改动前快照 `pre-plugin-20260810T1305` diff 确认最小/附加式改动 + `_os` 修复；真实示例 `.hermes_data`（mtime 早于本次编辑）未被触碰、未在示例根落 `.env`。**隔离功能测试**（用真实桌面 venv `hermes-desktop-01`、hermes-agent 0.18.2，覆盖 `HERMES_DESKTOP_HOME` 指向临时目录、**绝不碰真实 ~/.hermes**）**36/36 PASS**：状态名单读写、三态状态计算、点路径→斜杠键、入口点发现（只读不崩）、toggle/env/delete 三端点、`.env` 读写往返、路径穿越拒绝、空标识拒绝、缓存失效。







  - **诚实边界（非缺陷，设计如此）**："安装/卸载"插件超出本面板范围（以官方 `hermes plugins install` CLI 为准，已在 UI/文档标明）；启用/禁用只写 allow-list，需**下次会话**才真正加载（与内核"发现≠加载"一致）；pip 安装的入口点插件只读展示、由 pip 管理（删除被拒、显示 `pip 管理`）；项目插件（`.hermes/plugins/`）需 `HERMES_ENABLE_PROJECT_PLUGINS` 且不在本面板枚举（与真实默认关闭模型一致）。















## [1.4.41] — 2026-08-09















- **Provider Routing 路由集成（深度研究 Hermes Library Provider Routing 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/config.py` + 官方文档 `OpenRouter Provider Routing`/`OpenRouter Pareto Code Router`）**：Hermes 的 **Provider Routing 是 OpenRouter 专属的请求路由配置**，写在 `<HERMES_HOME>/config.yaml` 的 `provider_routing` 段——`sort`（`price` 默认 / `throughput` / `latency`）、`only`/`ignore`/`order`（provider 列表）、`require_parameters`(bool)、`data_collection`(`allow`/`deny`)；另 `openrouter.min_coding_score`(0.0–1.0，默认 0.65，仅 `openrouter/pareto-code` 模型生效，调 Pareto Code 路由的编码质量门槛)。该段被运行时真实消费（`conversation_loop.py`/`cli.py`/`gateway/run.py`/`cron/scheduler.py`/`tui_gateway/server.py`），写错=真实影响路由；非 openrouter provider 下这些设置无作用。内核 API：`hermes_cli/config` 的 `get_config_path()`(=`get_hermes_home()/"config.yaml"`)、`load_config()`(合并 DEFAULT_CONFIG)、`save_config(cfg)`(原子写+默认剥离+managed 拒绝)、`cfg_get(cfg,*keys,default)`(嵌套安全取)；三处均**调用期**读 `os.environ["HERMES_HOME"]`，examples 已设该 env，路径一致。快捷方式：模型名追加 `:nitro`(=throughput)/`:floor`(=price)。







  - **批判发现**：①（CRITICAL）**概念误读，与内核机制背道而驰**——旧 `routing_*`（`hermes_features.py` §13）把 Provider Routing 实现成 `features/routing.json` 的 **`round_robin` 策略概念**（还有 `providers_allowed`/`providers_ignored`/`providers_order`），而内核根本**不读这个文件、也不认识 `strategy` 字段**——保存等于白保存，对真实 Hermes 路由零影响。②（HIGH）**完全未复用内核 config**：应 `load_config`/`save_config` 读写 `config.yaml` 的 `provider_routing` 段，旧版全部手写 JSON 文件。③（HIGH）缺 `available:False` 降级（内核缺失直接崩）。④（HIGH）**字段名错配**：内核是 `sort`(price/throughput/latency)，旧版用 `strategy`(round_robin/priority/latency/cost)——既不对名也不对义。⑤（MEDIUM）缺 `openrouter.min_coding_score`（Pareto Code 旋钮）。⑥（MEDIUM）缺 `require_parameters`/`data_collection` 字段。⑦（MEDIUM）缺「仅 OpenRouter 生效」诚实提示（非 openrouter 时设置无作用，界面应说明）。⑧（LOW）路径漂移双轨（`features/routing.json` vs 内核 `config.yaml`）。







  - **完善（复用内核，与全家桶同源范式）**：`hermes_features.py` §13 重写为内核薄封装——删 `_routing_path()` 与自造 `routing.json`；`_routing_mods()` 惰性 `import hermes_cli.config`（不可用 None→`available:False`）；`routing_get()`→`load_config`+`cfg_get` 真实读取 `provider_routing`(sort/only/ignore/order/require_parameters/data_collection)+`openrouter.min_coding_score`+`model.provider`+`is_openrouter` 诚实提示（非 openrouter→`note` 警告）+`available:False` 降级；`routing_save(payload)`→校验 `sort`∈{price,throughput,latency}、`min_coding_score`∈[0.0,1.0]（空/None 清除→回退默认 0.65）、逗号串解析 only/ignore/order、空列表/空 data_collection 不写、`save_config(cfg)` 落盘 `config.yaml`。`routes/features.py` `GET/POST /api/features/routing` 不变（POST 透传 payload）。`other.js` `renderRoutingPanel` 重建——sort 下拉(price/throughput/latency)+only/ignore/order 输入+require_parameters 勾选+data_collection 下拉(allow/deny/默认)+min_coding_score 数字(0–1)+非 openrouter 警告+`:nitro`/`:floor` 提示+`available:False` 降级。







  - **验证（万无一失）**：`py_compile` 后端（`hermes_features.py`/`routes/features.py`）+ `node --check` 前端（`other.js`）全绿；grep 活动代码旧 `routing.json`/`strategy`/`round_robin`/`providers_allowed` 玩具实现**已清零**（仅 Batch Processing 段合法使用 `batch_runner` 的 `--providers_allowed/ignored/order` 运行时参数，非本玩具）；临时 `HERMES_HOME` 隔离端到端（不碰真实数据，`os.environ["HERMES_HOME"]=TMP` + monkeypatch `hermes_config.get_hermes_home` + 预置最小 `config.yaml`）**46/46 PASS**：初始 openrouter+默认(sort=price/only=[]/ignore=[]/order=[]/require_parameters=False/data_collection=None/min_coding_score=0.65)；保存完整段→落盘 `config.yaml` 含 `provider_routing`(sort=throughput/only=[anthropic]/ignore=[deepinfra]/order=[anthropic,google]/require_parameters=True/data_collection=deny)+`openrouter.min_coding_score=0.8`；逗号串 only="openai, anthropic"→[openai,anthropic]、空 ignore/order 不写、data_collection 空串不写；清除 min_coding_score(None)→回退默认 0.65 且磁盘 raw 移除该键；非法 sort 拒；min_coding_score>1/非数字拒；非 openrouter(anthropic)→is_openrouter=False+note 警告；降级（mock `_routing_mods=None`）→available:False 且不崩。自测脚本已移入 `.trash/_routing_e2e_test.py.20260809`（可恢复）。















## [1.4.40] — 2026-08-09















- **Curator 策展集成（深度研究 Hermes Library Curator 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`agent/curator.py` + `tools/skill_usage.py` + `agent/curator_backup.py`）**：Hermes 的 **Curator 是「后台自动整理 Agent 创建的技能」的维护通道**——按不活跃天数把 agent 创建技能从 `active`→`stale`→`archived` 确定性流转（可选 LLM 合并相似技能），每次整理前内核自动拍快照可回滚。三件套内核 API：①`agent/curator.py`（`load_state`/`is_enabled`/`is_paused`/`get_interval_hours`/`get_stale_after_days`/`get_archive_after_days`/`get_consolidate`/`get_prune_builtins`/`set_paused`/`apply_automatic_transitions`[无 LLM、确定性、返回 counts]/`run_curator_review`[带 LLM 合并]）；②`tools/skill_usage.py`（`usage_report`[全量含 `provenance:agent/bundled/hub`]/`agent_created_report`[仅 agent 创建]/`list_archived_skill_names`/`get_record`/`is_agent_created`/`set_pinned`/`mark_agent_created`/`archive_skill`/`restore_skill`；状态常量 `STATE_ACTIVE/STATE_STALE/STATE_ARCHIVED`；技能存 `<HERMES_HOME>/skills/<name>`、归档**物理移动到** `<HERMES_HOME>/.archive/<name>`）；③`agent/curator_backup.py`（`is_enabled`/`snapshot_skills`/`list_backups`/`rollback`/`enable`/`disable`）。路径锚点：三者均经 `hermes_constants.get_hermes_home()` 读 `os.environ["HERMES_HOME"]`（调用期取值），与 examples 已设的 `HERMES_HOME` 一致，路径不漂移。







  - **批判发现**：①（CRITICAL）**纯玩具，概念完全不存在于内核**——旧 `curator_get`/`curator_toggle`（`hermes_features.py` §10）只读写自造的 `features/curator_stats.json`，含 `enabled`/`recommendations`/`last_run` 等**虚构字段**，与 Hermes 真实 Curator（状态/遥测/归档/快照）零连接；所谓"推荐技能"是空壳。②（HIGH）**完全未复用内核**：真实能力（归档/恢复/固定/批量清理/快照/回滚）一个都没接。③（HIGH）缺 `available:False` 降级（内核缺失直接崩、或永远返回假字段）。④（HIGH）**归档只加标记不物理离盘**：内核 `archive_skill` 是把技能目录真正移出 `skills/`，旧实现无任何对应物。⑤（MEDIUM）缺真实遥测（使用次数/不活跃天数/state/pinned/provenance）。⑥（MEDIUM）缺快照/回滚（整理前安全网）。⑦（LOW）路径漂移双轨（`features/curator_stats.json` vs 内核 `skills/.archive`）。







  - **完善（复用内核，与全家桶同源范式）**：`hermes_features.py` §10 重写为内核薄封装——`_curator_mods()` 惰性 `import agent.curator / tools.skill_usage / agent.curator_backup`（任一缺失 None→`available:False`）；`_ensure_home_env()` 幂等兜底防双轨漂移；`curator_get()`→`load_state`+`usage_report`+`agent_created_report`+`list_archived_skill_names`（返回真实状态/遥测/归档列表/`by_state`/`pinned`）；`curator_toggle(enabled)`→`set_paused(not enabled)`（运行时暂停自动整理，诚实说明 config 持久需改配置）；`curator_apply(dry_run)`→`apply_automatic_transitions`（`dry_run` 返回候选预览）；`curator_archive(name)`→`archive_skill`（固定技能拒绝）；`curator_restore(name)`→`restore_skill`；`curator_pin(name, pinned)`→`set_pinned`；`curator_prune(days, dry_run)`→按 `stale_after_days`/`archive_after_days` 阈值清理（跳过 pinned）；`curator_backup(reason)`→`snapshot_skills`（未启用诚实返回 error）；`curator_backups()`→`list_backups`；`curator_rollback(backup_id, yes)`→`rollback` 需 `yes=True` 确认。前端 `renderCuratorPanel` 重建为：真实状态+遥测表（state/pinned/provenance/idle_days）+归档列表+固定/归档/恢复/批量清理（确认）/快照/回滚（确认）+`available:False` 降级。







  - **验证（万无一失）**：`py_compile` 后端（`hermes_features.py`/`routes/features.py`）+ `node --check` 前端（`other.js`）全绿；grep 活动代码旧 `curator_stats.json`/`recommendations` 玩具实现已清零（CLEAN）；临时 `HERMES_HOME` 隔离端到端（不碰真实数据）**48/48 PASS**（覆盖状态/遥测/固定/批量清理候选与执行/归档拒绝固定/恢复/空名拒绝/暂停恢复/自动流转/快照/回滚需确认/降级 `available:False`），自测脚本已移入 `.trash/_curator_e2e_test.py.20260809`（可恢复）。















## [1.4.39] — 2026-08-09















- **Profiles 配置管理集成（深度研究 Hermes Library Profiles 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/profiles.py` + `hermes_constants.get_default_hermes_root`）**：Hermes 的 **Profiles = 多个完全隔离的 Hermes 实例**，每个是一个独立 `HERMES_HOME` 目录，默认位于 `<root>/profiles/<name>/`；**"default" 就是 `<root>` 本身**（标准部署 `~/.hermes`，examples 冻结态 `<exe>/hermes_data`），向后兼容零迁移。切换 = `set_active_profile()` 写 `<root>/active_profile` 文件（下次启动生效），或运行时经 `-p <name>` 标志 / `HERMES_HOME_OVERRIDE` 改变 `HERMES_HOME`；**内核不识别 `HERMES_PROFILE` 这个环境变量名**。每个 profile 自带 `config.yaml`/`.env`/memory/sessions/skills/gateway/cron/logs，`create_profile` 会建 8 个子目录 + 克隆 config/.env/SOUL.md/skills/memories + 写 `.env`(chmod 0600) + 注册 gateway 服务（host 为 no-op），`delete_profile(yes=True)` 会停 gateway / 停 profile 后端进程 / 删 wrapper 脚本 / 清理服务 / retry rmtree（远比裸 `shutil.rmtree` 安全）；`list_profiles()` 返回丰富元信息（gateway_running/model/provider/skill_count/alias/description）；可选 `profile.yaml` 存描述（`write_profile_meta`）。路径锚点：`profiles._get_profiles_root()` = `get_default_hermes_root()/"profiles"`，而 `get_default_hermes_root()` 只读 `os.environ["HERMES_HOME"]`（不读 ContextVar override）；examples 已在导入前设该 env，故内核 profiles 与 examples 同落 `<HERMES_HOME>/profiles`，路径一致。







  - **批判发现**：①（CRITICAL）**概念误读，与内核机制背道而驰**——旧 `profiles_*`（`hermes_features.py` §6）把 Profiles 实现成 `features/profiles/<name>/` **自建子目录**（与内核 `~/.hermes/profiles/` 无关，真实 Hermes 永不识别），并用 `os.environ["HERMES_PROFILE"] = name` **切换**——该变量名内核根本不认识（内核用 `HERMES_HOME`/`active_profile` 文件/`-p` 标志），设了等于没设、且当前运行进程已固定 HERMES_HOME 也不会生效。②（CRITICAL）**创建语义错误**：旧 `profiles_create` 只 `mkdir` 空壳，不建子目录、不克隆 config/.env/SOUL.md/skills、不写 `.env`——这个"profile"对真实 Hermes 毫无意义（内核 `create_profile` 才建成完整独立实例）。③（CRITICAL）**删除语义错误且危险**：旧 `profiles_delete` 直接 `shutil.rmtree`，若该 profile 真实运行（gateway/backend 进程持有文件锁），rmtree 会 `ENOTEMPTY` 失败或留僵尸；且不会停 gateway/后端、不删 wrapper、不清理服务（内核 `delete_profile` 全做）。④（HIGH）**完全未复用内核**：应 `from hermes_cli import profiles` 调 `list/create/set_active/delete_profile`，旧版全部手写。⑤（HIGH）缺 `available:False` 降级（内核缺失直接崩）。⑥（HIGH）缺名字校验：内核有严格正则 `^[a-z0-9][a-z0-9_-]{0,63}$` + reserved 名（hermes/default/test/tmp/root/sudo）+ 子命令名检查；旧版接受任意字符串（含中文/空格/大写/点），可能与内核 reserved 冲突。⑦（MEDIUM）default 概念错误：内核 default = `~/.hermes` 本身（真实根）；旧版把 default 当 `features/profiles` 下一个"不存在就虚拟空壳"。⑧（MEDIUM）list 信息贫乏（仅 name/is_current/has_config/created），未呈现内核丰富的 gateway_running/model/skill_count/description 等。⑨（LOW）路径漂移双轨（`features/profiles` vs 内核 `~/.hermes/profiles`）。







  - **完善（复用内核，与全家桶同源范式）**：`hermes_features.py` §6 重写为内核薄封装——删 `_profiles_dir()` 与自造 `HERMES_PROFILE` 切换；`_profiles_mod()` 惰性 `import hermes_cli.profiles`（不可用 None→`available:False`）；`_ensure_home_env()` 幂等兜底 `os.environ["HERMES_HOME"]=_get_home()` 防内核双轨漂移；`profiles_list()`→`list_profiles()`+`get_active_profile()`（返回 `available`+丰富元信息）；`profiles_create(name, clone_from=None)`→`normalize_profile_name`+`validate_profile_name`+`create_profile`（含 clone_from 克隆）；`profiles_switch(name)`→`set_active_profile`（写 active_profile 文件，default 删文件；诚实提示下次启动生效）；`profiles_delete(name)`→`delete_profile(yes=True)`（停服务+retry rmtree）。`routes/features.py` 4 条 `/api/features/profiles*` 路由不变（create 透传 `clone_from`）。`other.js` `renderProfilesPanel` 重建——`available:False` 诚实降级；展示真实元信息（path/model/provider/skill_count/gateway_running/description/is_default/is_current）+ 可选「克隆自」下拉 + 创建/切换/删除诚实提示（切换下次启动生效、删除停网关与后端）。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features) + `node --check`(other.js) 全绿；grep 活动代码确认 `HERMES_PROFILE`/`_profiles_dir`/`features/profiles` 自建机制 **已清零（CLEAN，仅 §6 docstring 注释说明 + 正确路由/前端端点引用）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）设临时 `HERMES_HOME`（**不碰真实数据**，monkeypatch `hermes_config.get_hermes_home`）跑隔离端到端 **40/40 PASS**：初始 list 含 default 且 is_default；非法名/保留名/hermes/default 均被拒；create `coder`→落 `<HOME>/profiles/coder` 且含 8 子目录+`.env`+`SOUL.md`、path 在 `<HOME>/profiles` 下；重名拒绝；`clone_from=coder` 复制 skills/；switch `coder`→写 `active_profile` 且 `get_active_profile()=="coder"`；switch `default`→删文件；list 反映 current；delete `coder`→目录移除；删 default 拒绝；降级（mock `hermes_cli.profiles=None`）→`available:False` 且不崩。







  - **沉淀**：新增 [`references/28-profiles-integration.md`](references/28-profiles-integration.md) 固化「复用内核 `hermes_cli.profiles`（`list_profiles`/`create_profile`/`set_active_profile`/`delete_profile`）、Profile=独立 HERMES_HOME 落 `<HERMES_HOME>/profiles/<name>`、default=当前根、切换写 `active_profile` 文件（非 `HERMES_PROFILE` 变量）、`_ensure_home_env` 路径兜底、`available:False` 降级、名校验」范式 + 反模式红线（自建 `features/profiles/` 目录、`HERMES_PROFILE` 变量切换、裸 `mkdir`/`shutil.rmtree`、漏 `available:False`、漏名校验）；`examples/.../docs/profiles-audit.md` 完整研究+批判+完善+验证报告；同步 `docs/hermes-vs-frontend-coverage.md`（实现表第 7 行 + 状态表 Profiles 行标「已对齐内核（非玩具）」）与 SKILL.md 索引（28）；隔离 e2e 脚本 `_profiles_e2e_test.py` 移至 `D:\user_skills\hermes-desktop\.trash\_profiles_e2e_test.py.20260809`（可恢复，未系统删除）。







  - **未改/诚实边界**：切换 Profile 是**写文件**语义（下次启动生效），当前运行进程不会切换（内核本身如此，非缺陷）；新建 profile 不自动 seed 技能（职责在 `hermes update`/dashboard，内核 `create_profile` 本身也不 seed，已诚实提示用户在该 profile 内 `hermes skills install`）；`clone_from` 仅复制存在的 config/.env/skills/memories（空白源则复制为空壳，与内核一致）；内核缺失时 UI 显示「功能不可用」而非假数据；default profile 不可删除（内核保护）。















## [1.4.38] — 2026-08-09















- **Backup 备份/恢复集成（深度研究 Hermes Library Backup 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/backup.py`）**：完整备份 = 把整个 `HERMES_HOME` 打包成 ZIP 归档（`hermes backup`/`hermes import`）；真正的归档逻辑在 `_write_full_zip_backup(out_path, hermes_root)`——**排除规则是命门**：内核 `_EXCLUDED_DIRS`(16 项：hermes-agent/__pycache__/.git/node_modules/backups/checkpoints/.venv/venv/site-packages/.cache/.tox/.nox/.pytest_cache/.mypy_cache/.ruff_cache) + `_EXCLUDED_SUFFIXES`(.pyc/.pyo/.db-wal/.db-shm/.db-journal) + `_EXCLUDED_NAMES`(gateway.pid/cron.pid)；官方注释明言不排这些会让插件 venv/MCP 缓存被逐文件遍历、备份膨胀到数十万条目卡住数小时（"backup stuck for days / 426543 files"）；`hermes-agent` 仅排除根级。` .db` 走 `_safe_copy_db`(= `sqlite3.connect(uri=ro).backup(...)`，对正在打开的库也能一致快照)，且 **不打包 `.db-wal/.db-shm/.db-journal` sidecar**（否则 torn restore）。恢复 `run_import` 有 zip 校验 + `_IMPORT_SKIP_NAMES`(gateway_state.json/gateway.pid/cron.pid/gateway.lock/processes.json 机器专属运行时不覆盖) + `_SECRET_FILE_NAMES`(.env/auth.json/state.db 恢复后 `chmod 0600`) + zip-slip 防护。状态快照（同源模块 `create/list/restore/prune_quick_snapshot`）只备份 `_QUICK_STATE_FILES` 到 `<HERMES_HOME>/state-snapshots/`，已在 `references/19` 接入。







  - **批判发现**：①（CRITICAL）旧 `backup_create`（`hermes_features.py` §5）手写 walk **只排除 `checkpoints/backups/__pycache__` 三样**，缺 `.venv`/`node_modules`/`.cache`/`.pytest_cache`/`.mypy_cache`/`.ruff_cache`/`.git`/`site-packages`/`hermes-agent`——一旦 HERMES_HOME 下有插件 venv 或 MCP 缓存，会复现官方「426543 文件」膨胀灾难。②（CRITICAL）旧 walk 对所有文件 `zf.write`、仅对 `.db` 做 WAL 拷贝，`.db-wal/.db-shm/.db-journal` **sidecar 被原样塞进归档**，与内核「不打包 sidecar」原则相反 → torn restore。③（HIGH）**路径一致性违反红线**：旧 `_backup_dir()` 存 `<HERMES_HOME>/features/backups/`（与状态快照 `<HERMES_HOME>/state-snapshots/` 不同目录）；旧 `backup_restore` 用 `home.parent/.hermes_pre_restore_*` 做恢复前备份——`home.parent` 在 HERMES_HOME **之外**、且永不清理/不可列/不可回滚。④（MEDIUM）恢复无内核级安全网、未镜像导入跳过/机密权限（相比内核 `run_import` 退化）。⑤（LOW）备份用 `io.BytesIO` 全量入内存（大备份吃光内存）。**好的一面（非玩具，保留）**：旧实现已连接内核（`_wal_copy_db` 复用 `_safe_copy_db`、`backup_restore` 已有 zip-slip 防护）——本次是修正保真度缺陷，不是从零重写。







  - **完善（复用内核，与全家桶同源范式）**：`hermes_features.py` §5 重写/加固——`_backup_mod()` 惰性 `import hermes_cli.backup`（不可用 None→降级本地 walk）；`backup_create()` 优先 `bk._write_full_zip_backup(dst, home)`（`via="kernel"`），内核缺失降级本地「镜像排除集」walk（`_BACKUP_EXCLUDED_DIRS`/`_BACKUP_EXCLUDED_SUFFIXES`/`_BACKUP_EXCLUDED_NAMES` + `_should_exclude_local` 根级 hermes-agent 特例），返回含 `via` 字段诚实标注；`_backup_dir()` → `<HERMES_HOME>/backups/`（与状态快照同目录，路径一致性红线；内核 walk 排 `backups/` 防嵌套），`_backup_search_dirs()` 向后兼容旧 `features/backups/`；`backup_restore(name)` 恢复前 `create_quick_snapshot(label=f"pre-restore-{name}", hermes_home=home)` 做一键回滚安全网（返回 `pre_restore_snapshot`）+ 保留 zip-slip 防护 + 镜像内核 `_IMPORT_SKIP_NAMES`/`_SECRET_FILE_NAMES`；`backup_list`/`backup_delete` 跨新旧目录查找。`routes/features.py` 路由不变（4 条 `/api/features/backup*`）。`other.js` `renderBackupPanel` 恢复成功 toast 提示已自动做恢复前快照（可在「状态快照」回滚）。**完整备份本身不依赖内核**（有镜像排除集兜底），故无需 `available:False` 降级（有意为之的健壮设计）。







  - **验证（万无一失）**：`py_compile`(hermes_features) + `node --check`(other.js) 全绿；grep 活动代码确认旧 `features/backups` 路径分裂、`home.parent` 恢复前备份 **已清零（CLEAN，仅 `.bak.*` 历史副本可能命中）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）设临时 `HERMES_HOME`（**不碰真实数据**，monkeypatch `_get_home`）注入 `.venv`/`node_modules`/`.cache`/`.pytest_cache`/`.git`/`state.db-wal` 等应排除项跑隔离端到端 **24/24 PASS**：`backup_create`→`via="kernel"`+ZIP 含 `config.yaml`/`.env`/`state.db`/`memories/MEMORY.md`、**不含**任何 `.venv`/`node_modules`/`.cache`/`.pytest_cache`/`.git`/`backups`/`*.db-wal` 等应排除项、不自包含 `backups/`（无嵌套）；`backup_list` 返回 1 项且 `name` 匹配、`backup_delete` 后列表空；`backup_restore` 破坏 home 后恢复→`restored>0`+文件回到+`pre_restore_snapshot` 非空+`state-snapshots/` 生成；内核缺失（`_backup_mod`→None）→`via="fallback"` 且排除规则仍正确；恶意 zip(`../escape.txt`)恢复→调用不崩、`escape.txt` 未被写出 home 外（zip-slip 防护生效）。







  - **沉淀**：新增 [`references/27-backup-integration.md`](references/27-backup-integration.md) 固化「复用内核 `hermes_cli.backup._write_full_zip_backup`、完整排除集（根级 hermes-agent 特例）、`.db` WAL 安全拷贝且不打包 sidecar、备份与状态快照同落 `HERMES_HOME`、恢复前 `create_quick_snapshot` 安全网 + zip-slip 防护 + 镜像 `_IMPORT_SKIP_NAMES`/`_SECRET_FILE_NAMES`、`via` 字段诚实标注」范式 + 反模式红线（手写 3 排除 walk、打包 `.db` sidecar、`features/backups` 路径分裂、恢复前 copytree 到 `home.parent`、恢复无安全网/未跳过机器专属运行时）；`examples/.../docs/backup-audit.md` 完整研究+批判+完善+验证报告；同步 `docs/hermes-vs-frontend-coverage.md`（实现表第 6 行 Backup 行 + 状态表 Backup 行标「已对齐内核（非玩具）」）与 SKILL.md 索引（27）；隔离 e2e 脚本 `_backup_e2e_test.py` 移至 `D:\user_skills\hermes-desktop\.trash\_backup_e2e_test.py.20260809`（可恢复，未系统删除）。







  - **未改/诚实边界**：完整备份 ≠ 状态快照（前者全量 ZIP、后者核心状态轻量目录），UI 已区分；恢复前快照是**核心状态快照**（非完整副本），作回滚安全网，完整恢复仍整体覆盖 `HERMES_HOME`；内核缺失时完整备份仍可用（本地镜像排除集，有意为之的降级）；真实 `HERMES_HOME` 为空 → `backup_create` 返回 `ok:False`（正确行为，不补假数据）。















## [1.4.37] — 2026-08-09















- **Journey 旅程集成（深度研究 Hermes Library Journey 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/journey.py` + `agent/learning_graph.py` + `agent/learning_mutations.py`）**：Hermes 的 **Journey（旅程）= 学到的技能与记忆图谱**（`hermes journey` → `agent.learning_graph.build_learning_graph()`）。真实 payload：`nodes`（学到的技能[非 base、agent 创建或曾使用] + 记忆卡片[MEMORY.md/USER.md 按 `\n§\n` 分块]，每节点 `id/kind(skill|memory)/label/timestamp/category/useCount/state/createdBy/pinned`，memory 节点另有 `memorySource`）/ `edges`（技能 related_skills 边 + 记忆→技能词汇重叠边）/ `clusters`（按 category 计数）/ `memory`（记忆原文）/ `stats`（密度统计 learned_skills/memory_nodes/agent_created/used/...）。`list|delete|edit <node>` 复用 `agent.learning_mutations`（node_detail/delete_node/edit_node）；删技能=归档（可 `hermes curator restore` 恢复），删记忆=重写文件；数据从 `HERMES_HOME`(skills/ + memories/) 经 `get_hermes_home()` 读取，与桌面 `HERMES_HOME` 一致、路径不分裂。







  - **批判发现**：①（CRITICAL）旧 `journey_get`（`hermes_features.py` §11）是**100% 玩具、零内核连接**——读 `features/journey.json`，为空时**编造 3 条假事件**（首次对话/安装首个技能/记忆记录）并**写入磁盘**冒充真实学习历史，违反最高诚实红线。②（CRITICAL）schema 完全错位——返回 `items[{type,title,time,detail}]`，与内核 `nodes`(id/kind/label/timestamp/category/useCount/state/createdBy/pinned + memorySource)+`edges/clusters/memory/stats` 无关；前端按错字段渲染。③（HIGH）概念误读——把 Journey 当「通用事件时间线」编造 milestone/skill/memory/project 四类事件（内核只有 skill/memory 两类，无「事件流」概念）。④（HIGH）无 `available:False` 降级（从不碰内核，永远「成功」展示假数据）。⑤（MEDIUM）前端 `typeIcons` 全映射为 `'s'`（占位/笔误），渲染清一色无意义图标且 `project` 种类内核永不产出；未利用内核 nodes/edges/clusters/stats 富数据。⑥（LOW）假数据写 examples 自有 `features/` 目录（路径分裂）。







  - **完善（复用内核，与全家桶同源范式）**：`hermes_features.py` §11 重写为内核薄封装——删玩具 `journey_get`/写 `journey.json` 副作用；`_journey_mod` 惰性 `import agent.learning_graph`、`_journey_mutations_mod` 惰性 `import agent.learning_mutations`（不可用 None→`available:False`）；`journey_get`→`build_learning_graph()` 返回 `{ok, available:True, nodes, edges, clusters, memory, stats}`（缺失/异常→`available:False` 诚实降级、绝不伪造）；新增 `journey_node_detail`/`journey_delete`/`journey_edit` 透传 `agent.learning_mutations` 同名函数（模块缺失→`{ok:False, available:False, message}`）。`routes/features.py` 保留 `GET /api/features/journey`，新增 `GET /api/features/journey/node/{node_id}` + `POST /api/features/journey/delete` + `POST /api/features/journey/edit`。`other.js` `renderJourneyPanel` 重建——`available:False` 诚实降级；正常时顶部 `stats` 概要（学到的技能/记忆节点/Agent 创建/曾使用/连接边）+ `clusters` 分类徽章 + 节点按 `timestamp` 倒序时间线（技能◆/记忆✎、分类·useCount·relTime）+ 每节点「编辑」(拉 `node_detail` 预填→`POST edit`)/「删除」(confirm→`POST delete`，文案说明技能归档可恢复、记忆移除)；空数据诚实提示「暂无学习记录…」并点明数据来自 `HERMES_HOME` 的 `skills/` 与 `memories/`；复用 `util.js` 的 `relTime`（已加 import）。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features) + `node --check`(other.js) 全绿；grep 全 examples 活动代码确认 `journey.json`/`首次对话`/`typeIcons`/`ev.title`/`ev.detail`/`ev.time` **已清零（CLEAN，仅 `.bak.*` 历史副本命中）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）设临时 `HERMES_HOME`+`HERMES_DESKTOP_HOME`+`HERMES_BUNDLES_DIR`（**不碰真实数据**）注入 1 learned skill + 2 记忆卡片跑隔离端到端 **25/25 PASS**：`journey_get`→`available:True`+真实 `nodes`(1 技能+2 记忆)+`stats.learned_skills==1`/`memory_nodes==2`/`agent_created==1`/`used==1`；节点 schema 忠实（技能 useCount=5/createdBy=agent、记忆含 memorySource）；`node_detail` 真实节点 `ok:True`、未知节点 `ok:False`（不崩）；内核模块缺失→`available:False` 降级正确；`delete`/`edit` 未知节点 `ok:False`、正向 delete 真实技能→`ok:True`（归档）。







  - **沉淀**：新增 [`references/26-journey-integration.md`](references/26-journey-integration.md) 固化「复用内核 `agent.learning_graph`(build_learning_graph→nodes/edges/clusters/memory/stats) + `agent.learning_mutations`(node_detail/delete_node/edit_node)、`_journey_mod`/`_journey_mutations_mod` 惰性导入、`available:False` 降级、绝不伪造事件」范式 + 反模式红线（自写 `journey.json` 编造假事件、用 `items`+`type/title/time/detail` 错位 schema、`typeIcons` 全映射 `'s'`、漏 `available:False`）；`examples/.../docs/journey-audit.md` 完整研究+批判+完善+验证报告；同步 `docs/hermes-vs-frontend-coverage.md`（实现表第 12 行 + 状态表 Journey 行均标「已接 Hermes 原生（重建，非玩具）」）与 SKILL.md 索引（26）；隔离 e2e 脚本 `_journey_e2e_test.py` 移至 `D:\user_skills\hermes-desktop\.trash\_journey_e2e_test.py.20260809`（可恢复，未系统删除）。







  - **未改/诚实边界**：Journey = 「**你学到了什么**」的图谱（学到的技能 + 记忆块），**不是**用户手动添加的任意事件/里程碑；删除技能是**归档**（可 `hermes curator restore` 恢复）、删除记忆是**重写文件**，均走内核；内核模块不可用时 UI 显示「功能不可用」而非假数据；全新环境返回空 `nodes` 是**正确**行为，不应补假数据；未做 Journey 的 CLI `--play` 动画时间线渲染（属桌面富可视化增强，留作下一步）。















## [1.4.36] — 2026-08-09















- **Batch Processing 批量处理集成（深度研究 Hermes Library Batch Processing 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，顶层模块 `batch_runner.py`）**：Hermes 的 **Batch Processing = `batch_runner.py`（顶层可导入模块，非 `hermes_cli` 子模块；`import hermes_cli.batch_runner` 报 ModuleNotFoundError）**——把 **JSONL 数据集**（每行 `{"prompt": "..."}`，可选 `image`/`docker_image`/`cwd`）的每条 prompt 送进一个**隔离的 `AIAgent` 会话**（默认本地；仅数据行带 `image` 且 `TERMINAL_ENV=docker` 才用容器沙箱），按 **toolset distribution** 采样工具集，产出 **ShareGPT 轨迹（training / eval 数据）**，落 `data/<run_name>/trajectories.jsonl`+`batch_N.jsonl`+`checkpoint.json`+`statistics.json`。用途是**训练数据生成 / 评测流水线**，不是「模板套 N 输入返 N 文本」。公共 API：`BatchRunner` 类 / `main()`(Google Fire) / `list_distributions` / `validate_distribution` / `sample_toolsets_from_distribution` / 每 prompt 执行器 `_process_single_prompt(prompt_index, prompt_data, batch_num, config)`（真实创建 `AIAgent`→`run_conversation`→`_convert_to_trajectory_format`）。17 个 distribution：`default`(全工具含 terminal)/`safe`·`minimal`(不含 terminal，桌面安全)/`development`/`research`/`browser_*`/`terminal_*`/`mixed_tasks` 等。**红线**：`BatchRunner.run()` 内部用 `multiprocessing.Pool(num_workers)`（子进程），**冻结 Windows EXE 子进程脆弱**——桌面端禁止调 `BatchRunner.run()`，改本进程 worker 线程串行驱动 `_process_single_prompt`。







  - **批判发现**：①（CRITICAL）旧 `batch_process`（`hermes_features.py` §14）是**100% 模拟**——循环里直接 `results.append({"output": f"[模拟] 已处理: ..."})`，**从不调 Hermes/AIAgent**，`model` 参数被**完全忽略**，零内核连接、连模型都不跑（比 Blueprint 玩具更糟）。②（HIGH）概念错配——旧 UX（模板+N输入→N段文本）≠ 内核（JSONL `{prompt}`→隔离 Agent 会话→轨迹文件），标「Batch Processing」误导懂 Hermes 的用户。③（HIGH）无 `available:False` 降级、路由 `POST /api/features/batch-process` **阻塞同步**（批量超时）、`model` 死参数。④（MEDIUM/LOW）前端文案谎称「上传 CSV/JSON…导出结果」但无上传/导出；无输入校验、无逐条失败状态。







  - **完善（复用内核，与全家桶同源范式）**：`hermes_features.py` §14 重写为基于 `batch_runner` 的薄封装——`_batch_runner_mod` 惰性导入（不可用 None→`available:False`）；`batch_list_distributions` 包 `list_distributions`（返回 key/description/toolsets）；`batch_run(rows, opts)` 归一化为 `[{"prompt":...}]`、默认 `model=inclusionai/ling-3.0-flash:free`（项目 OpenRouter 铁律）/`distribution=safe`（桌面安全）/`base_url=OpenRouter`、启动 **daemon 线程** `_batch_run_worker` 立即返回 `run_id`（非阻塞）；`_batch_run_worker` **串行驱动内核 `_process_single_prompt`**（成功且含推理则复用内核 `_normalize_tool_stats`/`_normalize_tool_error_counts` 归一化→写 `batch_0.jsonl`+`trajectories.jsonl`→累积统计；无推理→discarded、失败→failed 不写轨迹，忠实内核 `--resume` 语义；结束写 `checkpoint.json`+`statistics.json`，整体 try/except→`status=error` 不静默崩溃）；`batch_status(run_id)` 轮询。删旧 `batch_process()` 与旧路由；`routes/features.py` 改为 `GET /api/features/batch/distributions` + `POST /api/features/batch/run` + `GET /api/features/batch/status/{run_id}`。`other.js` `renderBatchPanel` 重建为「批量处理（Hermes Batch Runner）」——诚实说明（训练/评测轨迹、桌面串行、真实调模型）+ 可用性检查→`available:false` 降级 + 输入模式（`JSONL 数据集` / `模板+N输入` 展开为真实数据集）+ 配置（run_name/distribution 下拉默认 safe/model 默认 OpenRouter 免费/base_url/max_iterations/reasoning_effort）+ 运行→轮询渲染（进度/终态分项/统计/轨迹目录）；新增 CSS `.grid-2`/`.small`/`.batch-prog`。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features) + `node --check`(other.js) 全绿；grep 全 examples 活动代码确认 `[模拟]`/`batch_process(`/`batch-process`/`prompt_template`/`上传 CSV` **已清零（CLEAN，唯一命中是 references/24 的 Blueprint docstring，无关）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）设临时 `HERMES_HOME`+`HERMES_DESKTOP_HOME`+`HERMES_BUNDLES_DIR`（**不碰真实数据**）跑隔离端到端 **49/49 PASS**：`batch_list_distributions`→`available:True`+含 default/safe/minimal/development（default 含 terminal、safe 不含）；`batch_run` 小数据集返回 run_id、无效端点下每条**优雅失败（success:False+error，不崩溃）**+`status=done`+统计 failed=2+输出目录已设+全失败时无轨迹文件（忠实内核仅成功项写轨迹）；内核不可导入→`available:False` 降级正确；monkeypatch 内核执行器成功路径→生成 `trajectories.jsonl`+`batch_0.jsonl` 且 schema 忠实（prompt_index/conversations/tool_stats/tool_error_counts/api_calls/metadata.model）。







  - **沉淀**：新增 [`references/25-batch-integration.md`](references/25-batch-integration.md) 固化「复用内核 `batch_runner`（顶层模块）、JSONL `{prompt}` 数据集、worker 线程串行驱动 `_process_single_prompt` 避免多进程、`batch_list_distributions`/`batch_run`/`batch_status` 薄封装、轨迹 schema 忠实、available:False 降级」范式 + 反模式红线（mock 返回`[模拟]`、把模板+N输入当 Batch Processing、用多进程 BatchRunner.run、漏 available:False）；`examples/.../docs/batch-audit.md` 完整研究+批判+完善+验证报告；同步 `docs/hermes-vs-frontend-coverage.md`（实现表第 16 行 + 状态表 Batch Processing 行均标「已接 Hermes 原生（重建，非玩具）」）与 SKILL.md 索引（25）；隔离 e2e 脚本 `_batch_e2e_test.py` 移至 `D:\user_skills\hermes-desktop\.trash\_batch_e2e_test.py.20260809`（可恢复，未系统删除）。







  - **未改/诚实边界**：批处理是**训练/评测数据生成器**，每次真实调模型、真实花 token（桌面串行更慢但安全可控）；仅成功项写轨迹（失败/无推理不写，与内核 `--resume` 一致）；桌面固定本地运行（不接容器沙箱，需隔离沙箱评测请走原生 CLI `python batch_runner.py`）；`model` 默认 OpenRouter 免费模型（项目铁律）、需自备 API Key；未做断点续跑 UI/`batch_size` 分组/quality-filter 明细（内核能力完整，留作下一步）。















## [1.4.35] — 2026-08-09















- **Blueprints 自动化蓝图集成（深度研究 Hermes Library Blueprint 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`cron/blueprint_catalog.py` + `hermes_cli/blueprint_cmd.py` + `cron/jobs.py`）**：Hermes 的 **Blueprint = Automation Blueprints（自动化蓝图）= 参数化「自动化模板」**，而非「对话提示词模板」。单一事实来源是内核**内置只读**目录 `cron.blueprint_catalog.CATALOG`（约 17 个内置蓝图，无用户自定义蓝图 API）。结构 `AutomationBlueprint`(key/title/description/category/tags/schedule_template[cron 占位符]/prompt_template[可含 {slot}]/slots[]) + `BlueprintSlot`(name/type[time|enum|text|weekdays]/label/default/options/optional/help/strict)。公共 API：`get_blueprint`/`blueprint_catalog_entry`(产前端形状 fields/scheduleHuman/command[`/blueprint <key> …`]/appUrl[`hermes://blueprint/<key>?…`])/`fill_blueprint(bp, values, origin=None)`(校验→返回 `cron.jobs.create_job` kwargs，失败抛 `BlueprintFillError`)。落点 `HERMES_HOME/cron/jobs.json`——与 examples「定时任务中心」**共用存储+调度器**（`cron_scheduler.py` 每 60s `tick()`），蓝图生成的任务会被**真实执行**。







  - **批判发现**：①（CRITICAL）旧 `blueprints_create/list/delete`（`hermes_features.py` §8）是**玩具**——自写 `{id,name,prompt,category}` 存 `blueprints.json`，与内核零连接，用户「创建蓝图」后什么都不会发生（不生成任务、永不执行）；把内核「自动化模板」错当成「对话提示词模板」。②（HIGH）概念误用 +「创建/删除我的蓝图」无内核对应物（目录内置只读）。③（MEDIUM）字段体系错误（应为 key/title/…/slots 而非 id/name/prompt/category）+ 路由语义错误（`POST /blueprints` 应为 GET 列目录 + POST /fill 生成任务）。④（LOW）缺 `available:False` 降级与 `BlueprintFillError` 透传。







  - **完善（复用内核，与 Kanban/Goals/Snapshot/MOA/Projects/Bundles/SecurityAudit 同源范式）**：`hermes_features.py` §8 重写为内核薄封装——`_blueprint_catalog_mod`/`_cron_jobs_mod` 惰性导入（不可用 None→`available:False`）；`blueprints_list`→`[blueprint_catalog_entry(b) for b in CATALOG]`（字段忠实）；`blueprints_fill(key, values)`→`get_blueprint`→`fill_blueprint`(捕获 `BlueprintFillError`→`kind=validation`)→`cron.jobs.create_job`(捕获异常→`kind=create`)，返回真实 job 摘要(id/name/schedule_display/deliver/next_run_at)；**删除** toy `blueprints_create`/`blueprints_delete`/`_blueprints_path`。`routes/features.py` 改为 `GET /api/features/blueprints` + `POST /api/features/blueprints/fill`（删旧 create/delete 路由）。`other.js` `renderBlueprintsPanel` 重写为「自动化蓝图 (Automation Blueprints)」——列真实目录卡片(title/description/category 徽章/scheduleHuman/tags)，点「设置」按 `fields.type` 渲染 time/enum/text/weekdays 表单、默认值预填、提交展示 job id/计划/交付；**桌面端诚实适配**：`deliver` 字段 options 含 `local` 时默认改 `local`（避免「origin 但无聊天起源」尴尬），用户仍可改；`available:false` 降级。`routes/pages.py` 导航 title 改「Hermes 自动化蓝图（生成真实定时任务）」。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features) + `node --check`(other.js) 全绿；grep 活动代码确认 `blueprints_create`/`blueprints_delete`/`_blueprints_path`/`blueprints.json` 玩具残留**已清零（仅 `.bak` 备份与反模式说明注释，CLEAN）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）设临时 `HERMES_HOME`+`HERMES_DESKTOP_HOME`+`HERMES_BUNDLES_DIR`（**不碰真实数据**）跑隔离端到端 **31/31 PASS**：目录忠实（字段含 key/title/description/category/tags/fields/scheduleHuman/command/appUrl，无旧 toy 字段 id/name/prompt）+ fill→真实写入 `HERMES_HOME/cron/jobs.json`(deliver=local、prompt 由模板渲染) + 未知 key→kind=notfound + 非法 time→kind=validation + 内核缺失→available:False。







  - **沉淀**：新增 [`references/24-blueprint-integration.md`](references/24-blueprint-integration.md) 固化「复用内核 `cron.blueprint_catalog`(内置只读 CATALOG)+`fill_blueprint`→`cron.jobs.create_job`、错误分级 kind=notfound|validation|create、available:False 降级、`deliver` 桌面端默认 local」范式 + 反模式红线（把 Blueprint 当对话提示词模板自写蓝图 JSON、提供无内核对应物的创建/删除蓝图、漏 available:False）；`examples/.../docs/blueprint-audit.md` 完整研究+批判+完善+验证报告；同步 `docs/hermes-vs-frontend-coverage.md`（实现表第 9 行 + 状态表 Blueprints 行均标「已接 Hermes 原生（重建，非玩具）」）与 SKILL.md 索引（24）；隔离 e2e 脚本 `_blueprint_e2e_test.py` 移至 `D:\user_skills\hermes-desktop\.trash\_blueprint_e2e_test.py.20260809`（可恢复，未系统删除）。







  - **未改/诚实边界**：蓝图目录**内置只读**，桌面端不提供新增/编辑/删除蓝图（内核无此能力；扩展应在 Hermes 上游 `CATALOG` 增加、桌面端自动继承）；蓝图生成的任务是**真实定时任务**，会被 examples cron 调度线程执行（用户应理解「生成即调度」）；`deliver=origin` 在桌面端无聊天起源（前端已默认 local）；`croniter` 为 hermes-agent 依赖正常可用，极端缺失时 `create_job` 失败已通过 `kind=create` 上抛不谎报成功。















## [1.4.34] — 2026-08-09















- **Security Audit 安全审计集成（深度研究 Hermes Library Security Audit 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证）**：Hermes 安全审计是**两个独立子系统**——(A) `hermes_cli/security_audit.py` **按需供应链漏洞审计（OSV.dev）**：扫描三个攻击面——① Hermes venv 内每个 PyPI dist（`importlib.metadata.distributions()`）；② 用户在 `~/.hermes/plugins` 声明的依赖（`requirements.txt`/`pyproject.toml` 尽力 `name==version`）；③ `config.yaml` 里 `command/args` 形如 `npx -y <pkg>@<ver>`/`uvx <pkg>==<ver>` 的 MCP 服务器；查询 `api.osv.dev/v1/querybatch` + `/v1/vulns/{id}`。单次按需、非每日。公开 API：`run_audit(*, skip_venv, skip_plugins, skip_mcp, hermes_home=None) -> list[Finding]`（`Finding.component`+`Finding.vuln`）、`_count_components(...)`、`SEVERITY_ORDER`(UNKNOWN:0/LOW:1/MODERATE:2/MEDIUM:2/HIGH:3/CRITICAL:4)；CLI `hermes security audit [--json] [--fail-on {low,moderate,high,critical}] [--skip-venv] [--skip-plugins] [--skip-mcp]`。(B) `hermes_cli/security_audit_startup.py` **启动姿态审计（warn-on-load、绝不阻断）**：检测 root 运行 / SSH 密码登录 / 容器无挂载 / 无鉴权网关；`run_security_audit(*, hermes_home, config) -> list[str]`；**POSIX-only，Windows 上是 no-op**——本期不接入 GUI 面板（判为越界）。(C) `hermes_cli/security_advisories.py` **已知投毒包检测（hermes doctor 同源）**：`detect_compromised(advisories=ADVISORIES) -> list[AdvisoryHit]`（纯 `importlib.metadata.version()`）、`filter_unacked(hits)`（用 `config.security.acked_advisories`）、`ack_advisory(id)`；目录 `ADVISORIES` 当前仅 `shai-hulud-2026-05`（mistralai 2.4.6 投毒，severity=critical）。







  - **批判发现**：①（CRITICAL）旧 `security_audit_run`（`hermes_features.py` §12）是**玩具**——用 `pkg_resources` 数已装包 + **伪造** `pass/total` 通过清单（依赖项/凭据/"API Key 明文存储"警告/文件系统），**从不查 OSV.dev**，真实 CVE 完全不可见；②（HIGH）未接内核、未扫描插件/MCP 攻击面；③（MEDIUM）"API Key 明文存储"属误报警（是 Tools 面板的配置说明，不是安全审计项）；④（LOW）把"凭据/文件系统"当审计类别，语义错乱。







  - **完善（复用内核，绝不手写清单/分家，与 Kanban/Goals/Snapshot/MOA/Projects/Bundles 同源范式）**：`hermes_features.py` §12 重写为基于内核的薄封装——`_security_audit_mod`/`_security_advisories_mod` 惰性导入（内核不可用 `available:False` + 空 findings/advisories）；`security_audit_run` 调 `sa._count_components` + `sa.run_audit`（skip 标志忠实透传），`run_audit` 抛 `RuntimeError`→`osv_error`（OSV.dev 联网失败，宽容降级、**绝不谎报通过**）；按 `Finding` 真实结构映射（`package/version/ecosystem/source/vuln_id/severity/severity_label/summary/fixed_versions`）+ 严重度中文标签 + `SEVERITY_ORDER` 降序；叠加 `security_advisories.detect_compromised`→`filter_unacked`（已知投毒包，纯 metadata 无需联网）；`routes/features.py` 新增 `POST /api/features/security-audit`（`skip_venv/skip_plugins/skip_mcp` 三布尔）；`other.js` `renderSecurityPanel` 重写为「安全审计（Hermes 原生）」——说明（三个攻击面 OSV.dev + 投毒包检测、需联网）、三个跳过勾选、运行后按内核结构渲染（严重度徽章 `tag sev-*`、包==版本(ecosystem · source)、vuln_id—summary、修复版本；投毒包 `tag sev-critical` + url + 处置；OSV.dev 失败 `tag warn` 仍展示投毒包；`available:false` 降级）。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features) + `node --check`(other.js) 全绿；grep 活动代码确认 `pkg_resources`/伪造 `passed/total`/`issues`(security 语境)/`明文存储`(security 语境) 玩具残留**已清零（CLEAN）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）设 `HERMES_HOME`+`HERMES_DESKTOP_HOME`+`HERMES_BUNDLES_DIR` 临时目录（**不碰真实数据**）跑隔离端到端 **30/30 PASS**（monkeypatch `sa._osv_query_batch`/`sa._osv_fetch_details` 注入合成漏洞 + 伪造 `importlib.metadata.distributions`，规避真实网络）：run_audit 可调用 + `SEVERITY_ORDER` CRITICAL=4 / 全跳过返回 []（不联网）/ 真实管线（hermes-agent CRITICAL + some-dep MODERATE 2 findings，字段忠实、降序）/ 投毒包 detect+filter_unacked / OSV 联网失败→osv_error+空 findings（不编造）+ 投毒包仍可用 / 内核缺失→available:False+空 / 无 toy `passed/total`/`issues` 字段。







  - **沉淀**：新增 [`references/23-security-audit-integration.md`](references/23-security-audit-integration.md) 固化「复用内核 security_audit（OSV.dev 三攻击面）+ security_advisories（投毒包）、run_audit RuntimeError→osv_error 宽容降级绝不谎报、Findings 字段忠实、SEVERITY_ORDER 降序、skip 标志透传、available:False 降级」范式 + 反模式红线（toy pkg_resources 包计数+伪造 pass/total、把 API Key 明文存储当审计项、未接 OSV.dev、混淆 security_audit 与 security_audit_startup、混淆 security_advisories 与 security_audit）；`examples/.../docs/security-audit-audit.md` 完整研究+批判+完善+验证报告；同步 `docs/hermes-vs-frontend-coverage.md`（实现表第 13 行 + 状态表 Security Audit 行均标「已接 Hermes 原生（重建，非玩具）」）与 SKILL.md 索引（23）；隔离 e2e 脚本 `_security_audit_e2e_test.py` 移至 `D:\user_skills\hermes-desktop\.trash\_security_audit_e2e_test.py.20260809`（可恢复，未系统删除）。







  - **未改/诚实边界**：`security_audit_startup`（启动姿态审计，POSIX-only / Windows no-op / 绝不阻断）本期**不接入 GUI 面板**（判为越界：Windows 下恒为空、warn-on-load 非面板特征）；真机「真实 OSV.dev 漏洞命中」属运行时验证（需联网 + 真实存在漏洞的版本），确定性来自复用同一 `run_audit`（与 `hermes security audit` CLI 同源）；`--fail-on` / `--json` CLI 标志未在前端暴露（内核 API 完整，留作下一步）。















## [1.4.33] — 2026-08-09















- **Bundles 捆绑包集成（深度研究 Hermes Library Bundles 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`agent/skill_bundles.py` 439 行 + CLI `hermes_cli/bundles.py`）**：Bundle = 把多个技能打包成一个 **`/<名称>` 斜杠命令**的小 **YAML 文件**，存于 per-profile 的 **`$HERMES_HOME/skill-bundles/*.yaml`**（与 projects.db/sessions/config/cron 同目录族）。真实 YAML 字段：`name`(必填，slug 化作斜杠命令)、`skills`(必填，≥1 技能 ID)、`description`(可选)、`instruction`(可选，调用时注入在技能内容前)；文件 stem 无 `name:` 时作兜底名。内核 API：`list_bundles()`(返回 name/slug/description/skills/instruction/path 字典列表)、`get_bundle(name)`、`save_bundle(name, skills, description="", instruction="", overwrite=False)`(**写盘即 `scan_bundles()` 刷新 `_bundles_cache`**；name/skills 空抛 `ValueError`、已存在且 `overwrite=False` 抛 `FileExistsError`)、`delete_bundle(name)`(不存在抛 `FileNotFoundError`)、`reload_bundles()`(返回 added/removed/unchanged/total 差异)、`build_bundle_invocation_message`(构造 `/<bundle>` 调用消息，缺失技能宽容跳过并附注)。CLI：`hermes bundles <list|show|create|delete|reload>`；会话内 `/bundles` 列出。进程内（hermes-desktop 核心）调 `save_bundle` 即更新同进程缓存 → 同进程 agent 斜杠 dispatch(`get_skill_bundles`)**立即可见** `/<name>`——与 Projects 同源（存同一份内核读的数据）。







  - **批判发现**：①（CRITICAL）旧 `bundles_*`（`hermes_features.py` §9）**完全未接内核**——写 `<HERMES_HOME>/bundles/*.json`（JSON），内核读 `<HERMES_HOME>/skill-bundles/*.yaml`（YAML），**两套完全独立存储**，GUI 建的 bundle 内核/对话永远读不到、命令行建的 GUI 也看不到；②（CRITICAL）**虚构字段**——旧 JSON 写 `installed: datetime.isoformat()`（内核无此字段）且**漏掉真实 `instruction` 字段**；③（HIGH）**未复用内核 CRUD / 未刷新内核缓存**——手写 JSON 读写不调 `save_bundle`/`delete_bundle`，即使放对目录运行中的 agent 也读不到新 bundle；④（MEDIUM）缺 `overwrite`/`instruction` 语义（无法表达 instruction、编辑同名撞 FileExistsError）；⑤（MEDIUM）缺技能存在性提示（零校验）；⑥（LOW）语义混淆（"可分发/可安装"）且 `b.desc` vs 内核 `description` 命名错位。







  - **完善（复用内核，绝不手写 JSON/分家，与 Kanban/Goals/Snapshot/MOA/Projects 同源范式）**：`hermes_features.py` §9 重写为基于 `agent.skill_bundles` 的薄封装（`_bundles_mod` 惰性导入、不可用 None→`available:False`；`bundles_list` 严格按内核 info 字典映射；`bundles_get`→`get_bundle`；`bundles_install`→`save_bundle`（FileExistsError→`exists`、ValueError→参数无效）；`bundles_uninstall`→`delete_bundle`（FileNotFoundError→`missing` 幂等）；`bundles_reload`→`reload_bundles`）；`routes/features.py` 4 条 `/api/features/bundles*` 路由（list/install[+instruction+overwrite]/卸载/reload）；`other.js` `renderBundlesPanel` 重建为「技能捆绑包（Hermes 原生）」——说明(`/<名称>` 斜杠命令一次加载多技能、数据存内核 skill-bundles、与内核/命令行/对话一致)、创建表单加 **instruction 文本域 + 覆盖同名勾选**、列表展示 `/<slug>`/description/instruction 预览、卸载(不存在 toast「已卸载（原本不存在）」)、`available:false` 降级、**重新扫描**按钮(reload)。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features) + `node --check`(other.js) 全绿；grep 活动代码确认 `Path(_get_home()) / "bundles"`/`installed: datetime`/`bundles/*.json`(除 e2e 自身 docstring)/`b.desc`(bundles 语境) 玩具残留**已清零（CLEAN，其余 installed/desc/json 命中均为无关功能：Edge 检测/skill-store/MCP store/wiki backlinks/checkpoints）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）设 `HERMES_BUNDLES_DIR`+`HERMES_HOME`+`HERMES_DESKTOP_HOME` 临时目录（**不碰真实数据**）跑隔离端到端 **20/20 PASS**：list 空 available 正常 / install 落 `skill-bundles/<slug>.yaml` 且无 `.json` / 内核 `list_bundles()` 同进程可见(接内核+缓存同步) / YAML 字段忠实(name/skills/description/instruction 全透传) / 重复无 overwrite 被拒(exists) / overwrite 成功+get 反映 / get 不存在 ok=False / uninstall 删 yaml / uninstall 不存在 missing 幂等 / reload 返回 diff / 未建旧 `bundles/` JSON 目录。







  - **沉淀**：新增 [`references/22-bundles-integration.md`](references/22-bundles-integration.md) 固化「复用内核 skill_bundles、skill-bundles 同目录红线、绝不手写 JSON/分家、写盘即刷内核缓存、字段忠实、available:False 降级」范式 + 反模式红线（JSON 分家/虚构 installed/漏 instruction/未刷缓存）；`examples/.../docs/bundles-audit.md` 完整研究+批判+完善+验证报告；同步 `docs/hermes-vs-frontend-coverage.md`（实现表第 10 行 + 状态表 Bundles 行均标「已接 Hermes 原生（重建，非玩具）」）与 SKILL.md 索引（22）；隔离 e2e 脚本 `_bundles_e2e_test.py` 移至 `D:\user_skills\hermes-desktop\.trash\_bundles_e2e_test.py.20260809`（可恢复，未系统删除）。







  - **未改/诚实边界**：旧 `bundles/` JSON 目录已成孤儿数据（内核不读、GUI 不再写），**未自动删除用户数据**（避免误删），如需清理可手动删该目录；真机「对话里 `/<name>` 一次加载多技能」属运行时验证（需真实 agent+已装技能），确定性来自复用同一 `skill-bundles` 目录与内核缓存刷新（与 Projects 同源）；bundle 编辑表单回填未做（当前用「创建+覆盖」覆盖编辑，足够忠实）；skill 存在性实时校验 UI 未强校验（内核宽容）。















## [1.4.32] — 2026-08-09















- **Projects 项目集成（深度研究 Hermes Library Projects 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/projects_db.py`，728 行）**：Project = 人类命名、跨多文件夹的 **per-profile 工作区（first-class 实体）**，落 **`$HERMES_HOME/projects.db`**（SQLite，与 sessions/config/cron 同目录；**区别于 root-anchored 的 kanban board DB**）。schema：`projects(id TEXT PK, slug UNIQUE, name, description, icon, color, board_slug, primary_path, created_at INTEGER, archived INTEGER)` / `project_folders(project_id, path, label, is_primary, added_at, PK(project_id,path))` / `project_meta(key,value)`（存 `active_id`）/ `discovered_repos(root,label,last_seen)`。CRUD：`create_project(conn, *, name, slug=None, folders=None, primary_path=None, ...)`→`id`(`p_`+hex)；`list_projects(conn, *, include_archived=False)`；`get_project(conn, id_or_slug)`；`update_project(conn, project_id, *, name/description/icon/color/board_slug)`（**空串→NULL 清空、None→不动**）；`add_folder(conn, project_id, path, *, is_primary=False)`（设主降级旧主、空项目首 folder 隐式变主）；`remove_folder(conn, project_id, path)`（**删主自动重指剩余第一个 folder（按 added_at），无剩余置 NULL**）；`set_active(conn, project_id|None)`/`get_active_id(conn)`（走 `project_meta`）；`project_for_path`（最长前缀匹配）/`branch_name_for`。打开方式 `connect_closing(db_path=None)` 上下文管理器——**不传路径自动走 `get_hermes_home()`**，与同进程 agent 同库同目录。CLI：`hermes project <create|list|show|add-folder|remove-folder|rename|set-primary|use|archive|restore|bind-board>`；Agent 工具集 `tools/project_tools.py` 的 `project` 工具（`project_list`/`project_create`/`project_switch`，GUI-only，不在 `_HERMES_CORE_TOOLS`）经 `set_project_workspace_callback` 切 cwd + 侧栏跟随——**对话里也能切工作区**。`Project.to_dict()` 真实字段：id/slug/name/description/icon/color/board_slug/primary_path/archived/created_at/folders[path,label,is_primary,added_at]；**内核无 `status`/`tasks`/`created`(ISO) 这类字段**。







  - **批判发现**：①（CRITICAL）旧 `projects_*`（`hermes_features.py` §7）是**玩具**——虚构 `status: active`、`tasks: []`（任务子资源）、`created` ISO 字段，**Hermes 内核里根本不存在**；②（CRITICAL）**未接内核**——存到独立的 `features/projects.json`（与 `projects.db` 分家），从未调 `projects_db` / 内核 `project` 工具集，对话里 `project_switch` 读不到、切不了工作区；③（HIGH）路径分家独立 JSON，与 backup/snapshot 不同目录、零复用；④（MEDIUM）前端 `renderProjectsPanel`/详情弹窗做了「任务待办/完成」假状态机（内核无 tasks 子资源）；⑤（MEDIUM）清空语义错配风险（`icon`/`board_slug` 应是 `""`→NULL 清空、`None`→不动）；⑥（LOW）语义混淆——界面叫「项目管理」实则空壳表单。







  - **完善（复用内核，绝不手写 sqlite/schema，与 Kanban/Goals/Snapshot/MOA 同源范式）**：`hermes_features.py` §7 重写为基于 `hermes_cli.projects_db` 的薄封装（`_projects_db_mod` 惰性导入、不可用返回 None；`_proj_to_ui` 直接 `p.to_dict()`+`active`；`projects_list` 经 `connect_closing()`+`get_active_id`+`list_projects`、不可用返回 `available:False`；`projects_create` name 必填+folders 归一化+`create_project`+可选 `set_active`；`projects_update` 严格按内核清空语义；`projects_delete`→`delete_project`；`projects_activate`→`set_active(conn, pid or None)`+`get_active_id`；`projects_add_folder`→`add_folder(is_primary=bool)`；`projects_remove_folder`→`remove_folder` 内核自动重指主）；`routes/features.py` 新增 7 条 `/api/features/projects*` 路由（list/create/update/delete/activate[clear→set_active(None)]/add-folder/remove-folder）；`other.js` 的 `renderProjectsPanel` 重写为「项目管理（Hermes 原生）」真实字段面板（slug/★当前/文件夹数/板 badge、新建表单含主文件夹路径+看板 slug+创建后设为当前、`available:false` 降级），`showProjectDetail` **改签名接收 pid 重新拉真实项目**（编辑 name/description/icon/color/board_slug/primary_path、文件夹增删、设为当前/删除/关闭），**删除旧 task 状态机 UI**。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features) / `node --check`(other.js) 全过；grep 活动代码确认 `projects.json`/`projects_task`/`/projects/.*/tasks`/`showProjectDetail(p)`/`p.tasks`/`proj_`/`task_` 玩具残留**已清零（CLEAN，仅 `.bak` 有旧副本）**；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）跑隔离端到端（临时 `HERMES_HOME`，**不碰真实数据**）——**28 项全 PASS**：① list 空 `available` 正常；② create 落 `projects.db` 且**无** `projects.json`（拒绝玩具分家）；③ active 指针经 `set_active` 写入可读；④ add_folder 设主更新 `primary_path`；⑤ update 传 `""` 把 `icon`/`board_slug` 清空为 NULL；⑥ remove_folder 删主后 `primary_path` 自动重指剩余第一个；⑦ activate 传 clear 清除指针；⑧ delete 清空项目与 folders。







  - **沉淀**：新增 [`references/21-projects-integration.md`](references/21-projects-integration.md) 固化「复用内核 projects_db、projects.db 同目录红线、绝不手写 sqlite/schema、活动项目指针、主文件夹重指、available:False 降级」范式 + 反模式红线（toy projects.json/虚构 tasks/status 子资源、独立 JSON 分家、未接内核 project 工具集）；examples 新增 `docs/projects-audit.md` 完整研究+批判+完善+验证报告；同步更新 `docs/hermes-vs-frontend-coverage.md`（Projects 实现表第 8 行 + 状态表行均标「已接 Hermes 原生（重建，非玩具）」）与 SKILL.md 索引（21）。







  - **未改/诚实边界**：归档/恢复（archive/restore）UI 暂未暴露（内核 API 已具备，留作下一步）；真机「对话里 `project_switch` 切工作区 + 侧栏跟随」属运行时验证（需真实 agent 进程），确定性来自复用同一 `projects.db`（与 `project_tools` 同源）；前端填相对路径会被内核 `_normalize_path` 处理，UI 文案建议填绝对路径避免歧义。















## [1.4.31] — 2026-08-09















- **MOA 多智能体混合集成（深度研究 Hermes Library MOA 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证）**：MOA = Hermes **虚拟 provider（"moa"）**——多个 `reference_models`（参考/顾问模型）各自给建议，再由一个 `aggregator`（聚合/执行模型）综合成最终回答；**不是独立命令**，而是当 `AIAgent(provider="moa", model=<预设名>)` 时，`AIAgent.__init__`（`agent/agent_init.py:816`）自动构造 `MoAClient` 接管每次 LLM 调用。配置落 **`config.yaml` 的 `moa` 键**，结构是「命名预设(presets)」：`default_preset`/`active_preset`/`presets/<name>/{enabled, reference_models:[{provider,model}], aggregator:{provider,model}, reference_temperature, aggregator_temperature, max_tokens, reference_max_tokens, fanout}`；`fanout` ∈ {`per_iteration`(每轮工具迭代重跑), `user_turn`(每轮用户对话跑一次)}。内核 API（`hermes_cli/moa_config.py`）：`normalize_moa_config`/`resolve_moa_preset`/`set_active_moa_preset`/`list_moa_presets`/`exact_moa_preset_name`/`DEFAULT_MOA_PRESET_NAME="default"`/`MOA_MARKER_PREFIX="__HERMES_MOA_TURN_V1__"`/`encode_moa_turn`（一次性 `/moa` 标记串 base64，单条试跑不切换活动模型）；引擎（`agent/moa_loop.py`）：`MoAChatCompletions`（OpenAI-chat 兼容 facade，经 `reference_callback` 在聚合前透出每个参考模型回答）/`MoAClient`(`.chat.completions` 包装)；`agent_init.py:816-864` 经 `_moa_reference_relay` 把 facade 的 `"moa.reference"`/`"moa.aggregating"` 事件转发到 `agent.tool_progress_callback`（参数：`("moa.reference", label, text, None, moa_index=, moa_count=)` / `("moa.aggregating", aggregator, None, None, moa_ref_count=)`）；`agent/conversation_loop.py:555` 的 `decode_moa_turn` 自动识别一次性标记串跑单轮后恢复原模型。默认预设：`reference_models=[{openai-codex,gpt-5.5},{openrouter,deepseek/deepseek-v4-pro}]`、`aggregator={openrouter,anthropic/claude-opus-4.8}`。







  - **批判发现**：①（CRITICAL）examples 旧 `moa_get/moa_save`（`hermes_features.py` §4）是**玩具**——虚构 `strategy: round_robin/weighted/consensus/best_of_n`、`max_rounds`、`models:[]` schema，**Hermes 内核里根本不存在这些字段**；数据存到独立的 `features/moa_config.json`（与 `config.yaml` 分家），**从未接入 `AIAgent`**（前端只改 JSON，无 `provider="moa"` 切换），等于一个填「策略/轮次/模型列表」的空壳表单；②（HIGH）路径分家独立 JSON，与 backup/snapshot 不同目录、内核零复用；③（MEDIUM）前端「策略」下拉（round_robin/weighted/consensus/best_of_n）全部无效；④（LOW）语义混淆——界面叫「多智能体混合」实则未接内核。







  - **完善（复用内核，绝不手写 schema，与 Kanban/Goals/Snapshot 同源范式）**：`hermes_features.py` §4 重写为基于内核的薄封装（`moa_get` 经 `normalize_moa_config` + 附加 `agent_provider/agent_model/active_in_agent` 经 `get_active_model_cfg` 判断；`moa_save` 合并现有 `moa` 后 `normalize_moa_config` 落 `config.yaml`；`moa_set_active` 同步 `config.yaml.active_preset` + `llm.json` 顶层 `vendor="moa"/provider="moa"/model=name` 使 `get_active_model_cfg` 解析出 `provider=="moa"`；`moa_delete` 兜底最后一个保护；`moa_encode_turn` 调 `encode_moa_turn`；内核不可用 `available:False` 降级；`_moa_home()` 复用 `_get_home()` 即 `hermes_config.get_hermes_home()`，与 backup/snapshot 同目录）；`routes/features.py` 在原有 `GET/POST /api/features/moa` 基础上新增 `activate/deactivate/delete/encode` 4 条；`agent_runtime.py` 的 `build_agent`/`build_trial_agent` 加 `tool_progress_callback` 形参 + `provider=="moa"` 守卫（预设缺失 try/except KeyError 降级 deepseek，**并回退 model 到 `deepseek-chat`**，防 AIAgent 拿预设名当 deepseek 模型名）；`stream_agent_chat` 接 `on_tool_progress` → q 透传 → 消费循环 `_sse({"type":"tool_progress",...})`；`chat.js` 的 `buildTurn` 新增 `moa` 折叠块、`handleEvent` 渲染 `moa.reference`(每条参考模型回答) / `moa.aggregating`(聚合提示)；`other.js` 的 `renderMoaPanel` 重写为真实预设编辑器（列出 presets、默认/激活徽标、启用、参考模型增删、聚合模型、fanout 下拉、reference_max_tokens/max_tokens、设为默认/当前模型/取消激活/删除、新增预设、保存全部、active_in_agent 状态、`available:False` 降级、底部「用 MOA 跑一句话」经 `/api/features/moa/encode` 后塞入输入框 `sendMessage()`）；`app.css` 补 `.moa-refs`/`.moa-ref`/`.moa-ref-label`/`.moa-ref-text`/`.moa-agg`。







  - **验证（万无一失）**：`py_compile`(hermes_features/routes/features/agent_runtime) / `node --check`(chat.js/other.js) 全过；grep 确认旧玩具 schema 字段（`round_robin/max_rounds/consensus/best_of_n/moa_config.json`）已从活动代码清除（仅 `routing` 功能的无关 `strategy` 与 `.bak` 备份残留，非 MOA）；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）跑隔离端到端（临时 `HERMES_HOME`，**不碰真实数据**）——**22 项全 PASS**：① moa_get 默认经内核 normalize（含 default_preset/reference_models/aggregator/fanout）；② moa_save 自定义预设并校验 `config.yaml.moa.presets` 落盘（fanout/reference_max_tokens 透传）；③ moa_set_active 同步 `config.yaml.active_preset` + `llm.json.vendor=moa/model=name`；④ moa_encode_turn 前缀 `__HERMES_MOA_TURN_V1__`；⑤ moa_delete 删非最后一个 ok、删最后一个被拒；⑥ `build_agent(provider=moa)` 自动接 `MoAClient` 且 `preset_name="default"`（active provider/model 经 `get_active_model_cfg` 验证为 moa/default）。







  - **沉淀**：新增 [`references/20-moa-integration.md`](references/20-moa-integration.md) 固化「复用内核 moa_config/config、config.yaml 落盘、provider=moa 虚拟 provider、build_agent 预设校验降级（含 model 回退）、tool_progress 透传、绝不手写 schema、available:False 降级」范式 + 反模式红线（toy round_robin/max_rounds 错 schema、独立 JSON 分家、未接 AIAgent）；examples 新增 `docs/moa-audit.md` 完整研究+批判+完善+验证报告；同步更新 `docs/hermes-vs-frontend-coverage.md`（MOA 行标「已接 Hermes 原生（重建，非玩具）」）与 SKILL.md 索引（20）。







  - **未改/诚实边界**：默认预设的 reference/aggregator 模型名随内核版本漂移，examples 不硬编码（走 `normalize_moa_config` 默认值）；一次性 `/moa` 标记串仅在当前消息跑单轮、不切换活动模型，适合「先试一条」试水；真机多模型并发跑（需真实 API key + 网络，含参考模型失败返回 `[failed:...]` 不抛的容错）属运行时验证，未本机演练；`moa_set_active("")` 取消激活只清 `config.yaml.active_preset` 不动 `llm.json`（切回普通模型由模型选择器负责，避免误清用户模型）。















## [1.4.30] — 2026-08-09















- **状态快照（State Snapshots）集成（深度研究 Hermes Library 快照功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，`hermes_cli/backup.py`）**：快照 = 对 `HERMES_HOME` 下一组**关键状态文件**（`_QUICK_STATE_FILES`：state.db / config.yaml / .env / auth.json / cron/jobs.json / gateway_state.json / channel_*.json / 各业务 .db / kanban/boards / pairing 等，行 755–782）做一次性**文件系统级备份**，落 `<HERMES_HOME>/state-snapshots/<时间戳[-标签]>/` 并写 `manifest.json`。内核 API：`create_quick_snapshot(label,hermes_home,keep)→str|None`（行 793，每次创建后**自动 prune 到 20**，行 885）、`list_quick_snapshots(limit,hermes_home)→list[dict]`（行 891）、`restore_quick_snapshot(snapshot_id,hermes_home)→bool`（行 917，对 `.db` 做 tmp→unlink→move 原子替换 + 对 id/manifest 每条做穿越校验）、`prune_quick_snapshots(keep,hermes_home)→int`（行 1123）；`.db` 经 `_safe_copy_db`（行 256，`sqlite3.backup()` 只读连接 + WAL 安全拷贝，正被打开也能拿一致副本）。与 examples 既有「对话快照(Checkpoints，单会话消息 JSON)」「完整备份(Backup，整盘 ZIP)」**概念完全不同**；内核快照无 agent 工具集，纯 CLI（`/snapshot`）驱动，桌面进程内复用内核函数即可。







  - **批判发现**：①（CRITICAL）examples **完全没有** Hermes 原生状态快照——只有对话快照与整盘 ZIP，用户想要「一键备份核心状态并回滚」给不出；②（HIGH）旧 `backup_restore` 用 `extractall` 无 zip-slip 防护（任意越界写）；③（MEDIUM）旧 `backup_create` 对 `.db` 直接 `zf.write`，非 WAL 安全拷贝（可能抓到不一致中间态）；④（LOW）侧栏「📸 快照」标签复用于 Checkpoints，与新增原生快照语义混淆。







  - **完善（复用内核，绝不手写 sqlite/拷贝，与 Kanban/Goals 同源范式）**：`hermes_features.py` §5.1 新增 `snapshots_*` 薄封装（`snapshots_list/create/restore/prune`，内核不可用时 `available:False` 降级；`_snapshot_home()` 复用 `_get_home()` 即 `hermes_config.get_hermes_home()`，**显式传给内核**，确保快照与完整备份落【同一】`HERMES_HOME`，且不依赖 `HERMES_HOME` 环境变量是否被 `materialize_hermes_env` 显式设置——内核默认回退是 `~/.hermes`，绝不能用错地方）；`routes/features.py` 新增 4 条 `/api/features/snapshots*` 路由；前端 `renderSnapshotsPanel`（`other.js`，标题「状态快照（Hermes 原生）」+ 与对话快照/完整备份区别说明 + 橙色提示（覆盖核心状态/建议关闭应用再恢复/恢复后重启）+ 创建/清理(保留20)/列表/恢复）+ `panels.js` 导出 + `views.js` 注册 `snapshots` 视图 + `routes/pages.py` 侧栏「💾 状态快照」导航 + 主区 `view-snapshots` 容器 + `app.css` 补 `.tag.err`/`.snapshot-warn`。**加固旧备份**：`backup_create` 新增 `_wal_copy_db` 复用内核 `_safe_copy_db`（WAL 安全）再进 ZIP；`backup_restore` 弃 `extractall` 改逐成员解压 + 落盘 `resolve()` 校验必须落在 home 内（越界跳过）。







  - **验证（万无一失）**：`py_compile`/`node --check` 全过；grep 确认 4 条 `/api/features/snapshots*` 后端路由 ↔ 4 处前端调用（create/prune/list/restore）一一对应，导航/视图容器/面板导出/视图注册全部就位；用桌面隔离 venv（`hermes-desktop-01`，hermes-agent 0.18.2）跑隔离端到端（**真实 SQLite 库**填充 HOME，消除此前假字节触发 Windows 文件锁 WinError 32 的 prune 假失败）——25 项全 PASS：create 6 / list 6 项（含 file_count/total_size/files 且备份 ≥5 个 .db）/ restore(`ok=True`+`restart_required=True` 且 state.db 存在) / restore 非法 id(`../escape`)被内核拒绝 / prune(keep=2)删除 4 剩 2 / 内核不可用降级 `available:False` / `backup_create` 产出 ZIP 含合法 SQLite 头 / `backup_restore` zip-slip 越界成员未写出 HOME 之外。全程未碰用户真实 `HERMES_HOME`、未改 `hermes-llms-full.txt`、测试 HOME 用临时目录跑完清理。







  - **沉淀**：新增 [`references/19-snapshot-integration.md`](references/19-snapshot-integration.md) 固化「复用内核 backup、显式传 HERMES_HOME、快照与备份同目录红线、绝不手写、zip-slip 防护」范式；examples 新增 `docs/snapshot-audit.md` 完整研究+批判+验证报告；同步更新 `docs/hermes-vs-frontend-coverage.md`（状态快照标「已接 Hermes 原生」）与 SKILL.md 索引（19）。







  - **未改/诚实边界**：`create_quick_snapshot` 内置 auto-prune 到 20，故「清理旧快照(保留20)」按钮在真实使用中与自动上限重合时可能显示「删除 0 个」（预期，按钮作显式保险阀）；恢复后需手动重启应用（已在 UI 与 `restart_required` 明示）；未做真机恢复演练（与运行应用抢 `state.db` 句柄的重启流程，属打包后验证范围）。















## [1.4.29] — 2026-08-09















- **Goals 常驻目标集成（深度研究 Hermes Library Goals 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证，hermes_cli/goals.py）**：Goals 是**按会话（per-session）常驻目标 + LLM 裁判自主续跑循环（Ralph loop）**，与 Kanban 关键区别是**无配套内核 agent 工具集**——循环完全由 CLI/Gateway 层驱动：每轮后调 `GoalManager.evaluate_after_turn(last_response)` 让 auxiliary 裁判模型判断，未满足则把续跑提示词当 user 消息喂回同一 session。持久化经 `SessionDB`（`state.db`）的 `state_meta` 表，键 `f"goal:{session_id}"`（**不是**独立文件、**不是** examples 玩具用的 `features/goals.json`）；失败开放：裁判连续 3 次解析失败 或 轮次预算(默认20)耗尽 → 自动 `status=paused`，不卡死。







  - **批判发现**：①（CRITICAL）`hermes_features.py` 旧 `goals_*`（`goals_list/create/update/delete/set_active`，行 51–114）是**玩具清单**，存全局 `goals.json`、与「按会话」语义错位，且 UI 文案「目标跨会话持久，每轮对话后判断是否已被满足」**是假的**（无任何裁判逻辑）；②（HIGH）真实「按会话自主裁判循环」完全未落地（仅 `goal_enabled→skip_context_files` 空壳开关）；③（MEDIUM）命名混淆（goals/goal_enabled 两码事）+ 前后端紧耦合；④（LOW）覆盖率文档把 Goals 标「已实现/完整」失真。







  - **完善（复用内核，绝不手写 sqlite/json，与 Kanban 同源范式）**：`hermes_features.py` 重写为基于 `hermes_cli.goals.GoalManager` 的薄封装（`goals_get/set/pause/resume/clear/mark_done/add_subgoal/remove_subgoal/evaluate`，内核不可用时 `available:False` 优雅降级）；`routes/features.py` 全部改接 `conv_id` 并删除旧玩具路由；`renderGoalsPanel`（`other.js`）改为展示真实 GoalState（状态/裁判结论/轮次/契约/子目标/屏障）+ 操作按钮 + 真实文案；`routes/chat.py` 的 `api_chat` done 后处理接 `goals_evaluate` 并把结果附到 done 事件 `goal` 字段（try/except 隔离）；`chat.js` 新增「🎯 继续目标 ▶」浮条，由用户显式驱动下一轮（**绝不自动连跑**）。裁判不可用（`goal_judge` 未配置）时走「手动模式」（不烧轮次、不自动续跑、UI 提示手动判断）。







  - **验证（万无一失）**：`py_compile`/`node --check` 通过；`check_js_modules.py` 全模块 SYNTAX-OK；`import routes` 枚举确认 9 条 `/api/features/goals*` 路由全部注册（门禁在技能根目录独立运行报「后端 0 路由」属误报，须从 examples 上下文运行）；临时 `HERMES_HOME` 端到端覆盖 set(内联契约解析)/get/add+remove subgoal/evaluate(手动)/pause/resume/mark_done/clear(→state=None)/跨实例持久化重载/evaluate(打桩裁判可用→should_continue=True)/内核不可用降级，全部通过；全程未触碰用户真实 `state.db`。







  - **沉淀**：新增 [`references/18-goals-integration.md`](references/18-goals-integration.md) 固化「复用内核 GoalManager、探测裁判可用性、绝不手写、透明可控续跑」范式；examples 新增 `docs/goals-audit.md` 完整研究+批判+验证报告；同步更新 `docs/hermes-vs-frontend-coverage.md`（Goals 标「已重构为内核集成」）与 SKILL.md 索引（18）。







  - **未改**：自动喂回续跑（默认关闭，留作下一步，需评估用户无感知连跑风险）；`goal_enabled` 空壳开关维持原状（与真正按会话 Goals 解耦）。















## [1.4.28] — 2026-08-09















- **Kanban 看板集成修正（深度研究 Hermes Library Kanban 功能 + examples 批判与完善）**：







  - **研究结论（hermes-agent 0.18.2 实证）**：看板以 9 个结构化工具提供（`kanban_show/list/complete/block/heartbeat/comment/create/unblock/link`），分 `kanban_mode` 与 `kanban_orchestrator_mode` 两层门禁；default 看板库在 `<root>/kanban.db`、其余在 `<root>/kanban/boards/<slug>/kanban.db`；真实 `tasks` 表**无 `description` 列（是 `body`）**、`created_at` 为 **INTEGER 时间戳**；状态枚举 `todo/ready/running/blocked/scheduled/done/triage`。







  - **批判发现**：①（CRITICAL）`hermes_config.py` 的 `get_kanban`/`add_kanban_task` 手写 sqlite 且把 `body` 错写成 `description`、把 `created_at` 当字符串，命中真实 `kanban.db` 即 `no such column: description`，看板空白、新增失败——恰违反 examples 自己在 `_kanban_call` 立下的"勿直连私有 DB"原则；②（HIGH）前端 `renderKanbanView` 只认 `todo/in_progress/done` 三列且精确匹配，真实状态 `ready/running/blocked/scheduled/triage` 静默消失；③（MEDIUM）`_run_kanban` 调度循环依赖编排者专属的 `kanban_list`，桌面 in-process agent 默认未注册该工具→空跑（已有优雅降级）。







  - **完善**：修复 A — `get_kanban`/`add_kanban_task` 复用内核 `hermes_cli.kanban_db.kanban_db_path()`/`connect()`（路径与同进程 agent 一致），SQL 严格按真实 schema（`body`/`created_at` INTEGER），`add` 用 `finally` 关闭连接；修复 B — 前端新增 `STATUS_BUCKET`/`STATUS_LABEL` 把全部真实状态归到三列并显示真实状态徽标，`app.css` 补 `.kanban-card-status` 样式。







  - **验证（万无一失）**：`py_compile`/`node --check` 通过；功能测试在临时库复现旧 SQL `no such column: description`，并确认新 `get_kanban`/`add_kanban_task`（真实模块导入端到端）读取与新增均成功（items 2→3），无连接泄漏、临时库可清理。全程未触碰用户真实 `HERMES_HOME/kanban.db`。







  - **沉淀**：新增 [`references/17-kanban-integration.md`](references/17-kanban-integration.md) 固化"复用内核 kanban_db、勿手写 sqlite"范式；examples 新增 `docs/kanban-audit.md` 完整研究+批判+验证报告。







  - **未改**：`_run_kanban` 循环未强制启用编排者模式（需评估副作用，维持优雅空跑）；`agent_runtime.py` 注释待补非 default 看板路径说明（建议项）。















## [1.4.27] — 2026-08-08















- **会话固定文件夹上下文（用户点名待建项 G6）**：







  - **能力**：可为单个会话绑定一个本地文件夹作为**长期背景上下文**；该文件夹内的文本文件内容会在**每一轮对话**自动注入模型（作为背景，区别于本轮手动附件）。前端双入口：① 工作区文件浏览器中目录行「📌 设为上下文」或工具条「📌 固定为对话上下文」；② 对话区顶部芯片条「📌 固定上下文：<路径>」+「解绑」按钮实时显示/取消绑定。







  - **安全模型（复用 G4 边界）**：沿用「授权根」白名单 + `_ws_resolve` 路径清洗（剔除 `..`/空段、落盘严格校验在根内、越界 403）；递归读取跳过 `.git`/`node_modules`/`__pycache__` 等（`_WS_SKIP_DIRS`）；仅取文本类扩展名（`_TEXT_ATTACH_EXT`）。**杜绝目录穿越 + 不读无关二进制**。







  - **限额（防超大目录拖垮注入）**：最大深度 8、最多 80 个文件、单文件 ≤20KB、总字符 ≤120KB；超限标记 `truncated`，文本头部自带「# 固定文件夹：」说明供模型区分背景与本轮附件。







  - **持久化**：`conversations` 表新增 `context_folder` 列（JSON：`{root,rel,display}`）；旧库 `_migrate_conversations_context_folder` 幂等 `ALTER` 补列，向后兼容；`api_chat` 在 attachments 注入之前把背景块拼入 `text`。







  - **护栏**：新增 `tests/test_context_folder.py`（8 passed：sessions 设/取 / 迁移列存在 / 受限递归读取基础（node_modules 跳过·非文本不计）/ 空与 rel / 单文件截断 / 绑定→查询→解绑 / 空会话自动建会话 / 越界根 403）。`py_compile` sessions.py+main.py OK；`check_js_modules.py` 12 文件 SYNTAX-OK（期间修复了外部/linter 改动误删 `renderCronPanel` 函数头的真 bug，已复绿）；`check_endpoints.py` 后端 192 路由、前端 177 引用全部匹配、无 404；回归 `pytest` 55 passed（含 upload_folder/attachment/wiki/sessions/workspace/channels/context_folder）。







  - **未动**：G5 审批状态机用户已决定暂不做；`renderCronPanel` 函数头丢失为外部修改所致、与 G6 无关、已修复。















## [1.4.26] — 2026-08-08















- **工作区文件浏览器（用户点名待建项 G4，完整树形）**：







  - **能力**：侧栏新增「📂 文件浏览器」视图。左侧可展开**目录树**（懒加载，仅展开才拉取子项），右侧为目录内容网格或文件预览/编辑区。支持：新建文件夹、新建文件、重命名、删除（目录递归）、下载（二进制安全）、**「附加到聊天」**（复制进 `HERMES_HOME/uploads` 并登记为对话附件，复用 `/api/chat` 注入逻辑）、面包屑导航、Git 仓库根检测（目录带 `.git` 时显示 ⌥git 徽标）。







  - **安全模型（核心）**：仅允许访问「授权根」目录——默认含应用目录、用户主目录、桌面/文档/下载/图片（存在才列），用户可自定义增删（`/api/workspace/roots` 增 / `DELETE` 删）。所有路径经 `_ws_resolve` 解析：根必须在白名单内，相对路径中的 `..`/空段被剔除，落盘点严格校验在授权根之内，**任何越界一律 403，杜绝目录穿越**。







  - **护栏**：新增 `tests/test_workspace.py`（11 passed：helper 解析/穿越中和/未授权根拒绝 / 端点 list·read / 端点穿越 403 / 写·建·改名·删 / 写拒绝目录 / 附件化落盘 / 附件越界 403 / 授权根增删）。`py_compile main.py` OK；`check_js_modules.py` 12 文件 SYNTAX-OK；`check_endpoints.py` 后端 189 路由、前端 172 引用全部匹配、无 404；回归 `pytest` 38 passed（含 upload_folder/attachment/wiki/sessions）。







  - **未动**：`workspace://` 伪协议与右面板可拖宽未做（非核心，按需可补）；默认授权根不含系统目录（如 `C:\Windows`），避免误暴露。















## [1.4.25] — 2026-08-08















- **对话框支持文件夹上传（用户点名待建项）**：







  - **能力**：聊天输入框新增「📁 文件夹」按钮，触发 `webkitdirectory` 文件夹选择框，递归选取文件夹内全部文件作为附件；上传时按浏览器给出的相对路径（`webkitRelativePath`）落盘，**保留目录结构**（如 `proj/src/main.py`），附件卡片显示完整相对路径。







  - **安全**：`/api/upload` 新增 `relpaths` 相对路径支持；新增 `_resolve_upload_target` 统一清洗——任何 `..`/空段被剔除并重新拼到 `uploads/` 之下，**杜绝目录穿越**；越界/非法路径自动回退为仅取文件名，附件名也清洗为安全相对名（不再出现 `../../`）。







  - **护栏**：新增 `tests/test_upload_folder.py`（5 passed：helper 结构保留 / helper 穿越中和 / helper 平铺回退 / 端点文件夹上传 / 端点穿越中和）；`py_compile main.py` OK；`check_js_modules.py` 12 文件 SYNTAX-OK；`check_endpoints.py` 后端 178 路由、前端 126 引用全部匹配、无新增 404。







  - **未动**：拖拽上传、单/多文件上传、附件持久化（G2）均保持原行为；文件夹内非文本文件不会灌入上下文（沿用既有 `_read_attachments_text` 仅注入文本类扩展名的策略）。















## [1.4.24] — 2026-08-08















- **附件持久化（用户点名待建项，本轮按「逐项做逐项验」首件落地）**：







  - **根因**：`api_chat` 落盘用户消息时只存了 `text`（已内联附件内容），`attachments` 元数据根本没传进 `sessions.append`；而 `set_messages` 在 Agent 整体覆盖时会用不含附件的 `msgs` 重写，刚落盘的附件会被冲掉。结果＝重开旧会话时，当时发的附件芯片（文件名/路径/预览）全部丢失，只剩内联文本。







  - **修复**：`messages` 表新增 `attachments` 列（新库 `_SCHEMA` 直接建列；旧库 `_migrate_messages_attachments` 幂等 `ALTER` 补齐，向后兼容、不碰真实数据）；`append`/`set_messages`/`get`/`copy`（`_insert_conv`）全链路透传；`api_chat` 落盘带 `attachments`，并在 `set_messages` 覆盖前把附件回填到匹配的用户消息；`api_conv_get` 向前端透传 `attachments`；前端 `renderHistory`/`addUserBubble` 新增 `buildAttachmentChips`，重开会话时复原历史附件芯片（复用 `.attachments-list`/`.attach-item` 样式）。







  - **护栏**：新增 `tests/test_attachment_persistence.py`（7 passed：落盘/重开/get/覆盖保留/复制保留/空值兼容/旧库迁移/建表列存在）。`_split_messages`（agent_runtime）只取 `role+content` 构造给 LLM 的消息，附件元数据不会被误发给大模型（已确认安全）。







  - **验证**：`py_compile` sessions.py/main.py OK；`pytest tests/test_attachment_persistence.py` 7 passed；回归 `test_wiki_v2.py` 8 passed + `test_sessions_sqlite.py` 16 passed（无回归）；`scripts/check_js_modules.py` 12 文件 SYNTAX-OK；`scripts/check_endpoints.py` 仅 1 个**预存**无关缺口 `/api/conversations/<p>/compress`（历史遗留、非 JS 缺陷，不在本次范围）。







- **顺带修复 `views.js` 模板字符串反斜杠语法错误（会让整站前端瘫痪的真 bug）**：`views.js:554/564` 的模板字面量被写成 ` \`... \${...}... \` `（反斜杠转义的非法写法），`node --check` 报 `Invalid or unexpected token`。已修为合法模板字面量；该错误与附件改动无关（本轮未动 views.js 主体），是近期损坏，门禁由 `SYNTAX-FAIL` 复绿。















## [1.4.23] — 2026-08-08















- **修复知识库改名「断链」真实数据损坏 bug（用户点名的数据完整性项）+ 补前端改名入口**：







  - **根因（非文档原称的「未做」，而是「做了但只对全长链接生效」）**：`wiki_engine.rename_page` 的 `_replace_wikilink` 只替换 `[[concepts/page_b]]` 这类**全称 slug** 写法；而正文实际以**短名** `[[page_b]]`（去类型子目录的叶子名）书写并落盘。结果改名时短链不更新 → 旧页面删除后残留指向它的断链、反链丢失。原 `test_b8_rename_cascade` 只测全称链接，故旧实现能蒙混过关。







  - **修复**：`_replace_wikilink` 同时按「全称 slug」与「短名叶子」两种写法替换（含别名 `[[x|显示]]` 与全长 `[[x#锚]]`）；`rename_page` 在用户只填短名时沿用原类型子目录，避免链接错落目录。







  - **前端**：`views.js` 知识库列表每张卡片新增「改名」按钮，调用已有 `/api/wiki/rename`（级联已修好），改名后自动同步全库链接。







  - **回归护栏**：`tests/test_wiki_v2.py` 新增 `test_b8_rename_cascade_short_form`（覆盖短链/别名/全长三种）+ `test_b8_rename_preserves_subdir`；实测旧代码该测试失败、新代码通过。







  - **验证**：`pytest tests/test_wiki_v2.py` 8 passed；`pytest tests/test_channels_bridge.py` 9 passed；`scripts/check_js_modules.py` 12 文件 SYNTAX-OK；后端级联端到端实测（短链/别名/全长均更新、反链回归、子目录保留）。















## [1.4.22] — 2026-08-08















- **重构上游漂移跟踪③源码签名线：从比对本地 venv 改为检测 PyPI 版本号（用户指出：比对本地 vs 基线是逻辑循环，真正的上游漂移应从 PyPI 检测）**：







  - **新增 `check_api_signature.py` `fetch_upstream_run_agent()`**：从 PyPI JSON API 获取最新版版本号，秒级完成，不下载 wheel。新增 `--from-pypi`（轻量版本检查）和 `--dump-pypi`（重量级：下载 wheel 做 ast 解析）参数。







  - **简化 `track_upstream.py` `check_signature()`**：从 30 行精简为 1 行委托 `sig.check_upstream_signature()`。







  - **修复 `quality_check.py` 子进程编码问题**：`_run_step` 的 `text=True` 增加 `encoding='utf-8'`，避免 Windows 中文版 `gbk` 解码崩溃。`step_signature()` 移除 `importlib.util.find_spec` 预检。







  - **文档同步**：`SKILL.md` §0、`references/13-maintenance.md` §0.2/§0.3/§0.4 全面更新。







  - **验证**：`track_upstream.py --json` 三条线秒级全通（① PyPI DRIFT / ② 文档 OK / ③ 签名 DRIFT）；`quality_check.py` 4/4 门禁全绿。















## [1.4.21] — 2026-08-08















- **落地「前端 ES 模块强制校验」为技能级条件性硬门禁（用户建议：补上「禁用 HTMX/Pico、使用 JS 时」的前提，因为正常只有 Python 代码）**：







  - **新增 `scripts/check_js_modules.py`**（纯 Python、自包含、可单独外发、无机器专属绝对路径）：自动递归扫描 `examples/*/static/**/*.js`，把每个 `.js` 复制为 `.mjs` 后用 `node --check` **强制按 ES 模块语法校验**（与浏览器 `<script type="module">` 加载方式一致）+ 跨模块 `import`↔`export` 链接核对。**前提已编码**：仅当存在 `examples/*/static/**/*.js`（即「禁用 HTMX/Pico、改用原生 ES 模块前端」）时才校验；`node` 缺失 / 无 JS 前端 → 退出码 **2 SKIP** 不阻塞（本技能正常形态为纯 Python / Tkinter / HTMX·Pico，无本地 ES 模块，无需此门禁）。退出码 0 通过 / 1 失败阻断 / 2 跳过。







  - **接入 `release_gate.py` 第 5 道硬门禁 `check_js_modules`**（条件性）：`node` 缺失 / 无 JS 前端 → 以退出码 2 视为 SKIP（不阻塞）；JS 损坏 → FAIL 阻断。新增 `--skip-js` 开关；硬门禁数 4→5，CI 建议项顺延为 [5]/[6]。`_step` 支持 `skip_codes` 把退出码 2 识别为 SKIP。







  - **删除 `examples/01-hermes-desktop/scripts/check_js_syntax.js`**（已由技能根 `check_js_modules.py` 取代并自动扫描全部示例，避免两份同源检查器漂移）。







  - **文档同步**：`SKILL.md`（脚本表加 `check_js_modules.py` 行 + release_gate 描述 4→5 硬门禁 + §6 反复核实循环加 `check_js_modules`）、`references/12-quality-gates.md`（§1 删去「改 `.js` 后用 `node --check`」误导建议、改 §1.1 说明前提与正确做法、§7 硬门禁 4→5 并补 `check_js_modules`、§9 反复核实表加行、开关加 `--skip-js`）、`references/14-antipatterns.md`（加「把 `node --check *.js` 当前端健康证明」反模式，含前提）、`references/15-workflow.md`（⓽ 门禁分工 4→5 硬门禁）、`docs/delivery-checklist.md`（A 档加 `check_js_modules` 项 + 反复核实循环加脚本）、SKILL.md frontmatter `version` 1.4.18→1.4.21（修正此前版本漂移）。







  - **Prove-It（非假绿）**：向示例临时写入一个「函数头多一个 `{`」的破损模块，重跑 `check_js_modules.py` —— 正确报 `SYNTAX-FAIL SyntaxError: Unexpected token 'export'`（与当年拖垮整站的 `views.js` 错误完全一致）并 exit 1；删文件后复跑即 12 文件全 SYNTAX-OK、exit 0；`node` 缺失时 exit 2 SKIP。三项行为均实测通过。







  - **验证**：`py_compile`(`release_gate.py`/`check_js_modules.py`) OK；`release_gate.py` 仅留 JS 门禁（其余 `--skip-*`）运行 → 12 模块全 SYNTAX-OK、exit 0；`check_js_modules.py` 独立运行 exit 0（PASS）/ 破损模块 exit 1（FAIL）/ 无 node exit 2（SKIP）均实测。















## [1.4.20] — 2026-08-08















- **性能优化 + 修复 Kanban 空白页（用户反馈：进入「工具集成/插件」卡约 1s、Kanban 页空白）**：







  - **修复 Kanban 空白（`static/src/views.js` `renderKanbanView`）**：成功路径漏写 `v.appendChild(sp)`——内容容器 `sp` 只在不走错误分支时才挂到视图上，导致数据加载成功后所有看板内容虽已构建却从未插入 DOM，页面一片空白。与其他 `render*View` 保持一致：创建 `sp` 后立即 `v.appendChild(sp)`（错误分支不再重复 append）。**已排查其余 12 个视图，确认只有 Kanban 有此漏写。**







  - **消除「工具集成/插件」约 1s 卡顿（根因量化）**：`registry.get_available_toolsets()` 会逐个运行工具集 `check_fn`（含网络健康探测，openrouter/nous 等），单次实测 **3.5–4s**；`api_plugins` 另每次 `walk_packages` + `import_module` 71 个插件模块 **~0.6s**。两者此前在每次进入页面时全量重算、零缓存。







    - `agent_runtime` 新增 `get_toolset_matrix(force=False)`：缓存工具集矩阵 **120s**，采用「过期返回旧值 + 守护线程后台刷新」策略，前台**永远即时返回**；`discover_toolsets` 改用它（实测 4s → **<1ms**）。`set_toolset_disabled`/`configure_toolset`/`test_toolset` 末尾调 `invalidate_toolset_cache()` 失效缓存，切换状态即时反映。







    - `main.py` `api_plugins` 改用 `ar.get_toolset_matrix()`，并对整个插件扫描结果加 **120s** 缓存（`_PLUGINS_CACHE`），命中直接返回。







    - `main.py` 模块加载时启动守护线程 `_prime_toolset_cache()` 预热矩阵，用户**首次**打开「工具集成/插件」即命中缓存，无需再等数秒。







  - **验证**：`py_compile` OK；`pytest tests/test_channels_bridge.py` **9 passed**；`node scripts/check_js_syntax.js` 12 文件全 `SYNTAX-OK` 且 `ALL IMPORTS RESOLVED OK`；缓存实测：冷算 3.57s → 命中 <1ms，`discover_toolsets` 0.0009s。















## [1.4.19] — 2026-08-08















- **微信 iLink 一键扫码登录前端落地（#165–#168）+ 顺带修复一处会导致整站加载失败的既有语法错误**：







  - **前端弹窗（`static/src/channels.js`）**：微信卡片新增「📷 扫码登录（推荐）」主按钮 → 居中二维码弹窗（`mask`+`modal`，复用现有 `.modal-head`/`.approval-body`/`.modal-foot`）；`openWechatQrModal` 调用 `POST /api/channels/wechat/qr/start` 取 `sid`+`qr_image`（后端生成 `data:image/png;base64` 二维码，缺失 `qrcode` 时回退文本 `scan_data`），每 1.5s 轮询 `GET /api/channels/wechat/qr/status?sid=`；`confirmed` 时把 `account_id`/`token`/`api_base` 填回表单并自动 `connectChannel`；`expired/timeout/error/cancelled` 提示重扫；关闭弹窗时 `POST cancel` 并清定时器。抽出 `connectChannel(c, inputs)` 复用连接逻辑；连接按钮加 `data-role="connect"` 精确标识，避免 4s 状态轮询把扫码按钮误改成「断开」。







  - **样式（`static/app.css`）**：新增 `.qr-box`/`.qr-image`/`.qr-fallback`/`.qr-status` 弹窗样式。







  - **文档（`docs/channels-qq-wechat.md`）**：新增 §6.1.1「微信一键扫码登录：交互与契约」，说明前端弹窗轮询、后端 `weixin_qr_login.py` 复用 iLink 端点、confirmed 写 `<HERMES_HOME>/weixin/accounts/{account_id}.json`、三个路由；诚实声明「iLink 字段为最佳努力、首次上线须真机联调、无 qrcode 时显示生成失败而非伪装成功」。







  - **测试（`tests/test_channels_bridge.py`）**：新增 `test_weixin_qr_login`（伪 `urlopen` 注入 `get_bot_qrcode`→`confirmed`：`ilink_bot_id`/`bot_token`/`baseurl`/`ilink_user_id`；`waiting`；空响应），校验 `start` 返回 `ok`/`sid`/`qr_image` 以 `data:image/png;base64,` 开头、后台约 8s 内确认、回传 `account_id`/`token`/`base_url`、`load_weixin_account` 落盘、cancel 路径、空响应 `ok:false`——**9/9 通过**（原 8 + 新增 1）。`weixin_qr_login.py` 的 `_http_get_json` 改为走 `channels/base._URLOPEN` 钩子以便注入；`requirements.txt`/`launcher.json` 追加 `qrcode`。







  - **顺带修复门禁暴露的真实致命错误**：`static/src/views.js` 的 `wikiIngestPanel()` 函数头误写为 `function wikiIngestPanel() { {`（多一个 `{`），导致整文件括号不平衡、浏览器按 `<script type="module">` 加载时于 `export {}`（第 555 行）报 `Unexpected token 'export'`，**整站前端瘫痪**。该错误仅 `.mjs` 严格模块解析会暴露（Node 22 对 `.js` 的自动模块探测更宽松、直接 `node --check` 反而绿灯，正是此前「看似全绿」的盲区）；删除多余 `{` 后 JS 门禁 12 文件全 `SYNTAX-OK` 且 `ALL IMPORTS RESOLVED OK`。







  - **验证（全绿）**：`py_compile`(weixin_qr_login/weixin_hermes/main/test) OK；`import channels.weixin_qr_login` OK（含 `start_qr_login`/`get_qr_status`/`cancel_qr_login`/`load_weixin_account`）；`pytest tests/test_channels_bridge.py` → **9 passed**；`node scripts/check_js_syntax.js` → `ALL IMPORTS RESOLVED OK · MODULE SYNTAX OK`（12 文件）。SKILL.md version → 1.4.19。















## [1.4.18] — 2026-08-08















- **LLM Wiki v2 缺口落地收尾 + 两处正确性修复（续「按规划逐一落地」）**：







  - **B8 改名联动修复**：`wiki_engine.py::_replace_wikilink` 正则 `([^\]|#]+?)` 惰性量词致 group2 只捕获首字符、`count` 恒 0、引用页正文不更新；改贪婪 `([^\]|#]+)` 后完整捕获链接目标，`rename_page` 现真正联动更新所有引用页 + 重算反链。







  - **新增 `tests/test_wiki_v2.py`（6/6 通过，隔离临时 HOME）**：覆盖 B8 改名联动+冲突保护、B3 写时断链、C2 全文搜索、E2 一键修复、G2/G3 导出导入圆通。`main.py` 既有 5 个 v2 端点（rename/search/fix-links/export/import，排在通用 `/{name:path}` 之前）。







  - **致命 frontmatter 解析 bug 修复**：`hermes_config._parse_frontmatter` 在 PyYAML 缺失时返回 `{}`（requirements 未列、运行时未装 pyyaml），导致所有 frontmatter（tags/title/type）写后读不回——Wiki 导出导入的 tags 全程丢失。新增 `_parse_simple_frontmatter` 兜底解析器（标量 / 内联 `[a, b]` / 块 `- item`），与 `_serialize_frontmatter` 退化路径闭环；PyYAML 可用时仍走 `yaml.safe_load`。







  - **顺带修复门禁暴露的真实 404**：`static/src/commands.js` 的 `/tools enable|disable` 命令 POST 到 `/api/toolsets/<tid>/toggle`（后端无此路由，静默失败），对齐后端 `/api/toolsets/toggle` 契约（body `{name, disabled}`）；`check_endpoints` 由「1 个 404 阻断」变「105 前端引用全绿」。







  - **验证**：`quality_check`(3/0)+`check_endpoints`(全绿)+`verify_imports`/`check_refs`(PASS) 全过；`test_channels_bridge.py` 53/0（Part 2 QQ/iLink 实装无回归）；`py_compile` 全过。注：`smoke_test_web` 在本受管 Python（无 starlette）仅环境性失败，冻结 venv 内可跑。SKILL.md version → 1.4.18。















## [1.4.17] — 2026-08-08















- **落地 QQ 官方 Bot API v2 与微信 Hermes iLink 连接器（进程内直连，无重依赖）**：在 `channels-qq-wechat.md` 规划的两大官方路径由「诚实占位」升级为「实装」。







  - **`channels/qq_official.py`（`QQOfficialConnector`，cid=`qq`）**：出站用标准库 HTTPS 调 OpenAPI v2（`getAppAccessToken` + `v2/users|groups/{id}/messages`，鉴权 `Authorization: QQBot <token>` + `X-Impl-Version: v2`）；入站用官方 WebSocket Gateway（`wss://api.sgroup.qq.com/websocket/`），经**懒导入 `websockets`** 后台线程接入、消息入队列由桥 supervisor 排出；`websockets` 缺失时**自动降级仅发送**，不崩溃、不伪装成功。recipient 约定 `g:`/`c:` 前缀区分群/频道，其余为 C2C 用户 openid；intents 默认 `GROUP_AT_MESSAGE_CREATE|DIRECT_MESSAGE`，UI 暴露 `intents` 字段便于覆盖。







  - **`channels/weixin_hermes.py`（`WeixinHermesConnector`，cid=`wechat`）**：Hermes 官方 iLink Bot 长轮询（~35s HTTP long-poll）接收，无公网 IP/Webhook 需求；媒体经 `cryptography` 懒导入做 AES-128-ECB(PKCS#7) 解密；`context_token` 按 peer 回显；`errcode=-14` 会话过期上抛。严格复用 `hermes gateway setup` 扫码产物（account_id/token/base_url），Agent 仍进程内直跑。







  - **`channels/bridge_stubs.py`**：原 `QQConnector`/`WeChatConnector` 占位移除（已上位为官方实装）；仅保留 `GewechatConnector`（cid=`wechat_gewechat`，needs_bridge=True）作为社区高风险路径诚实占位。`registry.py` 注册顺序：标准库连接器 → QQ官方 → iLink微信 → Gewechat占位。







  - **前端零改动**：`channels.js` 按 `meta.fields` 动态渲染表单/连接/状态/测试，新增连接器无需改结构；仅更新两处过期「占位」文案。`main.py` 渠道端点（`/api/channels/status` 等）已通用支撑。







  - **验证**：`tests/test_channels_bridge.py` 新增 `test_qq_official`/`test_weixin_hermes`（伪 urlopen 验证出站 URL/body/鉴权头、群消息前缀、iLink 长轮询解析/`context_token` 回显/出站；`wechat_gewechat` 诚实返回不支持）——**55/55 通过**（原 39 + 新增 16）；`py_compile channels/*.py` 全过；`import channels` 在缺 `qqbot-agent-sdk`/`hermes_agent` 时仍干净通过。







  - **诚实边界（防假已具备）**：未做真机联调（需真实 AppID/Secret 或 iLink 凭证）；QQ WebSocket 入站与 iLink 发送/媒体解密上线前须以真实凭据对照官方/网关输出联调。iLink 底层 HTTP 字段级 envelope 未完全公开，端点路径为「最佳努力」，可用 config 的 `api_base`/各 path 字段覆盖对齐（已在 `channels-qq-wechat.md §6` 标注）。SKILL.md version → 1.4.17。















## [1.4.16] — 2026-08-07















- **补「产物抽屉 → 聊天」真实缺口 + Provider 生命周期管理（对标 Hermes Studio 的三项真实差距）**：







  - **产物抽屉「附加到聊天」**：`panels.js::openArtifacts` 每个产物项新增「📎 附加到聊天」按钮 → `attachArtifactToChat()` → `POST /api/attachments/from-path`（后端）。该端点把 `output/` 产物或 `uploads/` 上传件**按路径**登记为对话附件，**免去重新上传**，复用既有 `/api/chat` 的 `_read_attachments_text` 注入逻辑（`State.attachments` + `Chat.renderAttachments()`）。路径安全与 artifact 端点同款：`startswith(output_dir)` 或 `startswith(HERMES_HOME/uploads)`，越界 403、非文件 404。验证：`from-path` 真实文件→200、`../` 越界→403、缺失→404。







  - **Provider 抽象（按厂商分组）**：`renderModelsPanel` 由扁平列表改为**按 `vendor` 分组**为「一个厂商下挂多模型」的 Provider 视图（仍保持 `llm.json` 扁平存储不变，仅在 UI 呈现两级）。每行支持「设为当前 / 编辑 / 测试 / 删除」。







  - **增量保存**：新增 `POST /api/models/upsert`（按 id 新增/更新，`api_key=""` 保留原密钥，`set_active` 可设当前）与 `POST /api/models/remove`（按 id 删除），替换前端原全量提交，减少前端负担。旧的 `POST /api/models` 全量替换端点保留作兼容。







  - **连通性测试**：新增 `POST /api/models/test`，用 OpenAI 兼容客户端发最小请求（优先 `models.list`，失败退 `chat.completions` 探针）验证密钥与可达性，返回结构化 `{ok, detail}`（鉴权失败 / 网络失败均 `ok:false` 不崩 500），对标 Hermes Studio 的 Provider 连通性检测。







  - **验证**：`node --check` 全过；`py_compile main.py` 通过；hermes-desktop `smoke_test_web.py` ALL PASSED；`TestClient` 功能验证——`from-path` 解析+403+404、模型 upsert/remove 往返一致、test 返回结构化 `ok:false`（200）。SKILL.md version → 1.4.16。















## [1.4.15] — 2026-08-07















- **前端可维护性改造（用户 20:49 批判 + 裁决「渐进式模块化」）**：批判属实——原 `examples/01-hermes-desktop/static/app.js` 2684 行单 IIFE、手写 DOM、0 模块化 / 0 类型检查 / 0 测试。路线坚持「零构建 / 零运行时依赖 / 双击即跑」，采用**原生 ES 模块渐进拆分**（不引入 bundler）：







  - **拆分结果**：`static/app.js` 瘦身为 96 行纯入口（装配 + 事件绑定 + 启动）；业务逻辑拆入 `static/src/` 8 个模块——叶子层 `dom`/`state`/`api`/`util`（纯函数可单测），`chat`（对话/历史/SSE/工具卡/审批/附件/语音/用量/上下文/命令补全/全局搜索，自包含）、`panels`（工件/分析/模型/工具集/技能/MCP/循环/插件/委派/cron/wiki）、`views`（`VIEW_RENDERERS` 注册表 + 各 `render*View`）、`channels`（IM 桥视图）。`views↔panels` 导入环用 `import * as` 命名空间导入化解（命名空间仅函数体内使用，不在模块顶层求值）。







  - **类型检查准备**：各模块加 `// @ts-check` + JSDoc typedef，纯函数（如 `util.formatUsage` / `api.parseSSE`）可静态推断。







  - **零依赖测试**：新增 `package.json`（`"type":"module"`，仅 `devDependencies`：`jsdom`/`vitest`）——浏览器不请求它，运行时零依赖原则不变；`main.py` 入口 `Script(src="/app.js", type="module")`，`static_path` 递归服务 `./src/*.js`。







  - **测试**：`tests/fe/smoke.mjs`（DOM/window 轻量 shim 后导入整个模块图，确认 9 文件链接期零错误，输出 `MODULE GRAPH OK`）；`tests/fe/test_util.mjs`（20/20，含 `convDateGroup`/`estimateTokens`/`formatUsage`/`relTime`/`toolIcon`/`extractFilePath`）；`tests/fe/test_api.mjs`（15/15，覆盖 `parseSSE` 多事件切分 / 注释行跳过 / 多 data 行拼接 / 尾部残块作 rest / JSON 失败跳过）。







  - **行为零回归核验**：核对 `chat.js::handleEvent`——`reasoning` 分支仅 `setPhase("思考中")+thinking` 累积；`done` 分支保留 `updateContextIndicator()` + `/usage` POST（与 `app.js.bak.20260807-202103:1023-1045,1876-1879` 一致），`error` 置 `_errored` 且 `done` 守卫跳过。







  - **测试期抓出的真实问题（已就地修正，非代码回归）**：① `test_util.mjs` 对 `formatUsage.cny` 断言写成 `0.003168`，而原始代码与备份一致算得 `0.00576`（(4000/1000)*0.0001+(2000/1000)*0.0002=0.0008 USD，×7.2）→ 改测试期望值；② `test_api.mjs` 初版把换行塞进 JSON 字符串值内（`"hel\nlo"`）致 JSON 非法被解析器跳过，改为 token 边界跨行拆分（`{"a":1,`/`"b":2}`）正确重组 → 改测试用例。两项均确认代码行为正确、与原始一致。







  - **验证全绿**：`node --check` 9 文件全过；`smoke.mjs` MODULE GRAPH OK；`test_util` 20/0、`test_api` 15/0；`py_compile main.py` 通过；`static_path` 递归服务 `/src/*.js` 经 `main.py:101,377` 注释确认。SKILL.md version → 1.4.15。















## [1.4.14] — 2026-08-07















- **修复 hermes-studio 批判中的 F1（IM 渠道接入）——用「进程内 IM 桥」替换脱节的外部 gateway**：用户指出「examples 只做桌面端、无法让 Agent 接入 Telegram/微信/飞书等 IM 平台」本质正确。根因：原 `gateway_manager.py` 仅起一个独立的 `hermes gateway run` 子进程，与本桌面进程内 `AIAgent` 完全不相交——桌面 agent 收不到任何 IM 消息，渠道页是「装饰」。







  - **修复方案（坚持铁律：agent 仍进程内 Library 直跑，不起外部 gateway、不把 agent 远端化）**：新增 `channels/` 包（标准库 only，零额外依赖），让桌面进程内的 `AIAgent` 直接经标准库 HTTPS 与 IM 平台通信：







    - `telegram.py`：纯轮询（getUpdates + sendMessage，无需入站服务器）。







    - `feishu.py` / `dingtalk.py` / `slack.py` / `wecom.py` / `discord.py`：出站 Webhook 发送 + 本地推送接收器（仅 127.0.0.1）接收事件，并做平台签名校验（飞书/钉钉 HMAC-SHA256、Slack/Discord Ed25519、企微 SHA1）。







    - `bridge_stubs.py`：QQ / 微信 诚实标注「需外部桥接服务（go-cqhttp / wechaty）」，不内置重依赖。







    - `webhook_server.py`：进程内 `ThreadingHTTPServer` 仅绑 127.0.0.1，按路径分发到对应连接器并回送 bridge（非 agent 执行通道）。







    - `bridge.py`：`ChannelBridge` 单例——入站消息 → `sessions` 建/查会话 → 进程内 `agent_runtime.stream_agent_chat` 生成回复 → 经连接器回推平台，事件流水供前端实时展示。轮询型 connectors 由 supervisor 线程统一驱动；Webhook 型由接收器驱动。







  - **后端/前端改造**：`main.py` 删除 `gateway_manager` 依赖与 `/api/gateway/*` 端点，改为 `/api/channels/status`、`/connect`、`/disconnect`、`/test`、`/events`（复用既有 `/api/channels` 配置读写）；`app.js renderChannelsView` 重写为按渠道 `fields` 动态渲染表单、真实连接状态、Webhook 回调 URL、实时消息流水、发送测试；删除 `gateway_manager.py`。







  - **修复途中实测抓出的真实 bug**：① 各连接器 `send` 在分片循环首个成功即 `return`，导致长消息只发第一段——改为发送全部 `limit` 内分片；② 钉钉签名漏换行（与飞书算法不一致）——补 `\n`；③ `WebhookReceiver` 未把 `lookup/bridge` 挂到实际服务器实例，导致入站 500——重构为 `_WebhookHTTPServer` 子类承载路由；④ `_split_long` 不会硬拆超长单行——改为按 `limit` 硬拆。







  - **验证**：`tests/test_channels_bridge.py`（受管 Python 3.13.12，无 hermes-agent，伪 Agent + 伪 urlopen + 真实本地接收器）**39/39 通过**（签名/工具、出站 payload、入站解析、桥全链路落盘、Webhook 端到端、QQ/微信占位）；`main.py` 在冻结 venv 干净导入且 bridge 含全部 8 连接器；`py_compile` 全过、`node --check` 过。回归全绿：A1 10/10、test_bridge 12/12、A2 9/9、A4 12/12、D2 全过、CD 14/14、SQLite 57/57。SKILL.md version → 1.4.14。















## [1.4.13] — 2026-08-07















- **修复 hermes-studio 批判中的两大本质问题（F2 会话持久化 / F3 状态管理），路线仍坚持「进程内 Python Library」，不引入其 BFF/Electron/gateway**：







  - **F2【高·本质】会话持久化从整文件 JSON 改为 SQLite（FTS5 索引）**：`sessions.py` 全面重写为 SQLite 存储（`HERMES_HOME/desktop/sessions.db`，标准库 `sqlite3`，零额外依赖；WAL + busy_timeout 保证崩溃安全与读不阻塞写）。**根因**：旧实现把全部会话序列化进单个 `sessions.json`，`_save` 每次 `append` 都整文件重写（`indent=1`）——在 200 会话 × 400 消息 ≈ 16 万条 / 226MB 的设计上限下，单次 append 阻塞 0.75–2.5s（均值 ~1.1s）且 `search_messages` 无索引需全表扫描 ~270–330ms。**修复后实测（同规模 16 万条）**：append 峰值 24.4ms（~45× 提升，且 O(1) 不随总量退化）、search 峰值 0.6ms（~500× 提升，FTS5 索引命中）；运行环境若不支持 FTS5 自动降级 LIKE 全表扫描，行为一致。全部公开 API 签名与返回结构**逐字节兼容**（`main.py`/前端/既有测试零改动）；首启若发现旧 `sessions.json` 且库为空，自动迁移入库并将旧文件改名备份为 `.migrated-<ts>.json`，不丢数据。验证：`tests/test_sessions_sqlite.py`（受管 Python 3.13.12，无 hermes-agent）**57/57 通过**（含 CRUD 往返、append O(1) 实证、FTS 搜索、JSON 迁移、MAX 淘汰/截断、analytics、copy/export/import）；`tests/bench_sessions.py` 满规模基准断言 append/search 峰值均 < 50ms；`critique_a2_test.py` 9/9（已改用 `HERMES_DESKTOP_HOME` 隔离，不再误读项目 `.hermes_data`）。







  - **F3【中·本质】统一双路由 / 单一状态对象**：原 `renderCurrentView()` 用 `State.currentView`（主区 if/else 级联 14 分支）+ 模块级 `let settingsTab`（设置中心 `map` 查表），两套状态系统、两套重复分发，违背「统一状态管理」。现把 `settingsTab` 并入 `State` 单一状态对象；新增统一 `VIEW_RENDERERS` 注册表替换主区 if/else 级联、单一 `PANELS` 注册表供设置中心复用（消除内联重复 `map`）。`renderSettingsNav`/`openSettings`/`renderSettingsPanel`/`showView` 全部改读 `State.settingsTab`。验证：`node --check` app.js 通过；grep 确认裸 `settingsTab` 全局变量零残留（仅 `State.settingsTab`）。







  - **连带修复（实测抓出）**：`agent_runtime._runtime_probe("session_search")` 原本检查 `HERMES_HOME/sessions.json`（旧路径且硬编码），迁移后既找不到文件又会误报。改为检查正确的 `HERMES_HOME/desktop/sessions.db` 并调用 `sessions.count_conversations()` 取真实计数（已实测：2 条会话 → 正确识别并报告「2 条会话」）。同步更新 line 851 提示文案（sessions.json → 本地会话库 SQLite）。







  - **F1 说明（非 bug，刻意边界）**：用户指出的「examples 无法接入 Telegram/微信/飞书等 IM 平台」属事实，但这是本技能**刻意架构边界**——核心约束为「进程内 Python Library 直跑、不起 gateway、不走 HTTP」，IM 渠道能力位于 Hermes 官方 `hermes` CLI 的独立 `gateway` 进程，与本示例的进程内 Agent 是两条互不相交代码路径。故 F1 **不在本次修复范围**，保持路线纯净。







  - **门禁全绿**：`py_compile` main.py/sessions.py/agent_runtime.py/file_preview.py 通过；`node --check` app.js 通过；回归 `test_bridge.py` 12/12（冻结 venv）、`critique_a1_test.py` 10/10（冻结 venv）、`critique_a4_test.py` 12/12、`critique_cd_test.mjs` 14/14、`critique_d2_backend_test.py` 全通过。SKILL.md version → 1.4.13。















## [1.4.12] — 2026-08-07















- **对话界面批判落地：A1（安全·必改）/ A2 / A3 / A4**（对标 hermes-studio 的 UX 差距，路线仍坚持「进程内 Python Library」，不引入其 BFF/Electron/gateway）：







  - **A1【高·安全】Markdown 渲染净化（XSS）**：`main.py::render_markdown` 渲染后新增 `bleach.clean`（白名单 `_SAFE_TAGS`/`_SAFE_ATTRS`/`_SAFE_PROTOCOLS`，`strip=True`）。仅保留 Markdown 结构 + 必要的 `class`（代码高亮、`language-mermaid` 识别依赖）；链接仅放行 `http/https/mailto`，`javascript:` 协议与 `onerror` 等事件属性被剥离；`<script>` 被移除。**覆盖全部注入点**：`done` 分支 `turn.bubble.innerHTML=obj.html`、`/api/conversations/{cid}` 重渲染、历史 `renderHistory`（复用已净化的存储 html）均经此函数。**降级安全**：bleach 缺失时整体 `html.escape` 退化为丢失富格式但不注入。验证：`tests/critique_a1_test.py`（冻结 venv）**10/10**，含 script/onerror/javascript:/code-class/mermaid-class/table/br 保留断言。







  - **A2【中】跨会话全文检索**：`sessions.py` 新增 `search_messages(q)` 对 `user/assistant` 消息正文做不区分大小写全文匹配，返回会话摘要 + `snippet` + `matches`（按命中数/更新时间排序）；`main.py` 新增 `GET /api/conversations/search`；前端新增 **Ctrl/Cmd+K 全局搜索弹窗**（`openGlobalSearch`），结果点击跳转会话并复用 `convSearchLive` 高亮。验证：`tests/critique_a2_test.py`（双环境）**9/9**。







  - **A3【中·低成本】工具卡参数/结果分区**：`openToolCard` 改为「参数」+「结果」两个独立分区（结果区用 `<pre>` 保留格式且无 HTML 注入风险）；`action` 填参数、`action_result` 填结果。配套更新 `app.css`（移除旧 `.t-preview`/`.t-result` 平铺样式，新增 `.t-sec`/`.t-label`/`.t-args`/`.t-result-body`）。







  - **A4【中·依赖 A1】生成文件内联预览**：新增 `file_preview.py`（**纯标准库、可离线测试**），`resolve_safe` 强制读取落在允许根目录（HERMES_HOME/工作目录/临时目录/用户主目录）内并拒绝越界（path traversal 防护，绕过 `..` 与软链）；`preview_file` 按扩展名+文件头嗅探（手写魔数，规避 3.13 已移除的 `imghdr`，且排除可含脚本的 SVG）返回图片/PDF→base64 data URL、HTML/文本→文本。`main.py` 新增 `GET /api/file/preview`；前端 `action_result` 检测到文件路径时挂「📄 预览文件」按钮，点击在**沙箱化 `<iframe sandbox>`（禁用脚本）/`<img>`/`<pre>`** 中渲染。验证：`tests/critique_a4_test.py`（双环境）**12/12**，含越界系统 hosts 文件被拒、不存在文件被拒。







  - **门禁全绿**：`node --check` app.js、`py_compile` main.py/sessions.py/file_preview.py 通过；回归 `test_bridge.py` 12/12、`critique_cd_test.mjs` 14/14、`critique_d2_backend_test.py` 全通过；grep 旧符号 `ref.prev`/`toolCards`/`hasDelta` 零残留。SKILL.md version → 1.4.12。















## [1.4.11] — 2026-08-07















- **修复离线自检依赖缺失（用户：test_bridge.py 依赖的 _testkit.py 缺失，已单独修复）**：







  - **根因**：`examples/01-hermes-desktop/test_bridge.py` 顶部 `from _testkit import fake_build_agent, parse_sse`，但 `_testkit.py` 不在仓库（导入即 `ModuleNotFoundError`），导致整套离线自检（文档声称「无需 hermes-agent / 无需 API Key / 无需联网」）完全无法运行。







  - **修复**：新建 `examples/01-hermes-desktop/_testkit.py`，依据 `agent_runtime.stream_agent_chat` 的**真实契约**精确重建两个符号，零臆造：







    - `fake_build_agent` / `FakeAIAgent`：`run_conversation` 按 `reasoning → action → action_result → delta` 顺序调用构造时注入的回调（`on_tool_start(tool_call_id, name, display_args)` / `on_tool_complete(tool_call_id, name, display_args, result)` / `on_reasoning(text)` / `stream_callback(delta)`），最后返回 `{"final_response", "messages"}`；工具名固定 `get_weather`、result 为 `{"ok": True, ...}`、delta 文本含「北京今天晴」，与 `t_sse_events` / `t_sse_approval` 断言逐一对齐。工厂签名严格匹配 `stream_agent_chat` 调用点（位置参 `model_cfg` + 关键字 `max_iterations` / `ephemeral_system_prompt` / `tool_start_callback` / `tool_complete_callback` / `reasoning_callback` / `web_search`）。







    - `parse_sse`：把 `stream_agent_chat` 产出的 `b"data: {json}\n\n"` 字节流按 `\n\n` 切事件、取首个 `data:` 行解析，并把 OpenAI chunk 形状的 delta（`{"choices":[{"delta":{"content":...}}]}`）归一化为 `{"type":"delta","text":...}`，与自带 `type` 的 reasoning/action/action_result/done 对齐。







  - **验证（均绿，双环境）**：冻结基线 venv（`hermes-desktop-01`，hermes_agent 0.18.2）跑 `test_bridge.py` → **12/12 通过**；受管 Python 3.13.12（**未装 hermes-agent**，验证「无需 hermes-agent」文档声明属实）跑同一文件 → **12/12 通过**。逐条核对 factory 关键字、`run_conversation` 四参、`on_tool_*`/`on_delta`/`on_reasoning` 回调签名，与 `agent_runtime.py` 源码一致，无漂移。SKILL.md version → 1.4.11。















## [1.4.10] — 2026-08-07















- **对话界面批判落地（执行 C1/C2/C3 + D1/D2；用户：反复核实，确保准确无误）**：







  - **C1【中】工具卡按调用实例建卡（同名多次调用不再折叠）**：原 `ensureToolCard(turn, tool)` 以**工具名为 key** 聚合，同一工具（尤其 file 的 read/write 多次）第二次调用会覆盖第一次的「运行中/完成/结果」。重构为 `openToolCard` / `closeToolCard`：每次 `action` 新建独立实例卡并标注序号（`工具名 2`、`工具名 3`…），按「每工具 FIFO 等待队列」匹配 `action_result`（兼容同名工具串行与跨工具交错），无对应 action 时兜底新建防止结果丢失。`buildTurn` 不再返回 `toolCards` 字段。







  - **C2【低】纯工具轮误判「无输出」修复**：`handleEvent` 顶部（meta 之后）置 `turn._hasEvent = true`（仅 meta 不计数）；`sendMessage` 的「（无输出）」判定由 `!hasDelta` 改为 `!turn._hasEvent`，使「只有工具调用、无文本增量」的一轮不再被误标无输出。







  - **C3【低】done 缺 html 时保留流式文本（防富格式丢失）**：`done` 分支仅当 `obj.html` 存在时整泡 `innerHTML` 替换（代码高亮 / Mermaid）；否则保留流式累积文本（设 `turn.live.textContent = obj.final`），不再二次覆盖导致格式丢失。成功路径 done 永远由 `main.py` 渲染 `html=render_markdown(...)`，故正常对话富格式不受影响。







  - **D1【低】前端 SSE 解析改为标准累积器**：原解析对每个事件块只取首个 `data:` 行、不拼接跨行 data。改为按 `\n\n` 切事件、事件内 `field:value` 解析、多条 `data:` 行用 `\n` 连接、注释行（`:` 开头）忽略，兼容后端将来输出含换行的结果 / 多行 data。







  - **D2【低】错误路径不再下发 done（error+done 去重）**：`agent_runtime.stream_agent_chat` 收尾仅在 `not errored` 时 yield `done`（worker 异常 / 超时置 `errored`，取消走 `_CancelRequested` 不算 error 仍正常收尾）；前端 `done` 分支加 `if (turn._errored) return`，`error` 分支置 `turn._errored = true`。避免 error 提示被空 done 覆盖、重复触发 `attachMsgActions` 与用量上报。conv_id 来自 `main.py` 注入的 meta 事件，与 done 解耦，成功路径持久化不受影响。







  - **验证（均绿）**：`node --check` 通过 `app.js`；`py_compile` 通过 `agent_runtime.py` / `main.py`；grep 旧符号 `ensureToolCard` / `toolCards` / `hasDelta` 在 `app.js` 0 残留；`test_bridge.py` 的 `t_sse_events` / `t_sse_approval` 走成功路径（fake agent），D2 跳过的是错误路径 done，不受影响。SKILL.md version → 1.4.10。















## [1.4.9] — 2026-08-07















- **对话界面批判落地（执行 B1 / B2 / B3；用户：反复核实，确保准确无误）**：







  - **B1【高】重生成 / 编辑替换原轮（历史污染修复）**：原 `regenerateFrom` / `editUserMessage` 仅把文本塞回输入框再并行发送，导致历史出现两条相同 user + 两条 assistant。新增 `replaceAndResend()`：前端从目标用户消息起删除尾部 DOM 气泡，并把该 user 在「user 序列」中的序号 `replace_index` 交给后端；后端 `api_chat` 按 user 边界裁掉旧历史（保留队首 system）后重跑。等价于「从所选用户消息起重跑」，对含工具消息的轮次也安全（不留孤立 tool 消息）。`replace_index` 越界时兜底为普通新轮。







  - **B2【中】done 落盘防御性合并（防历史丢失）**：原 `api_chat` 收到 agent 回传 `messages` 即整体覆盖，依赖「必含本轮 user」的隐式契约，部分 provider/路径只回传 assistant 增量时会清空历史。改为：仅当回传 `messages` 末段确实含本轮 user 才整体覆盖，否则改为「本地已追加历史 + 新 assistant」合并。







  - **B3【中】停止语义最佳努力中断 worker（防继续烧 token / 写文件）**：原 `run_conversation()` 无原生 cancel，点停止后后台工具循环仍跑到自然结束。在 `agent_runtime.stream_agent_chat` 增设 `cancel_event` 参数，于 `on_delta` / `on_tool_start` / `on_tool_complete` / `on_reasoning` 回调中检查并抛 `_CancelRequested`，worker 捕获后正常收尾（不打错误）。`api_chat` 已把 cancel 事件传入内核，并更新了顶部注释如实标注「最佳努力中断，非 100% 保证」。







  - **验证（均绿）**：`py_compile` 通过 `agent_runtime.py` / `main.py` / `sessions.py`；`node --check` 通过 `app.js`；用真实 `sessions` 模块（临时 store 隔离）跑通 B1 裁历史 6 场景（含 system 守卫、越界兜底）+ B2 部分回传合并；用伪 Agent（10 万轮 ≈50s、不取消则超时）证明 cancel 置位后 worker 在下一回调即中断（仅收到 240/10 万 delta，无 error，join 0.01s 返回）。SKILL.md version → 1.4.9。















## [1.4.8] — 2026-08-07















- **仓库清理 + 文档数字核实（用户：清理备份文件，核实工具集数量后修改）**：







  - **备份文件清理**：删除 `examples/01-hermes-desktop/` 下 8 个开发期时间戳/手写备份（`agent_runtime.py.bak.20260807-1500`、`main.py.bak.20260807-1500`、`static/_bak_app.js`、`static/_bak2_app.css`、`static/_bak2_app.js`、`static/_bak3_app.js`、`static/_bak4_app.js`、`static/app.js.bak.20260807-1500`）。全技能 `*.bak*`/`_bak*` 复查归零，不再污染打包与 git 追踪。







  - **工具集数量核实并更正**：用冻结基线 venv（`%LOCALAPPDATA%/hermes-desktop/venvs/hermes-desktop-01`，hermes_agent 0.18.2）实跑 `from tools.registry import registry, discover_builtin_tools` → `registry.get_available_toolsets()`，确认注册表**实测暴露 28 个工具集**（`discover_toolsets()` 遍历全量、不过滤）。原 `docs/gap-fathah.md:18` 写「工具集开关（14 个）」为陈旧数字，已更正为「28 个」（并注明含 credentials 依赖项）。







  - **更正历史遗留误述**：CHANGELOG[1.4.7] 第 11 行曾记「`README.md` 称『工具集开关（14 个）』」——复查 `README.md` 实际无该数字（仅 `docs/gap-fathah.md` 有），属当时笔误，本条目一并澄清。







  - **未动项**：`examples/01-hermes-desktop/docs/external-cases.md:117` 的「14 个」描述的是**外部项目 fathah/hermes-desktop** 的工具集规模（对比参照，非本技能示例），不在本次核实范围，保持不变。







  - **验证**：`find` 全技能备份文件 0；`gap-fathah.md` 改为 28 个；SKILL.md version → 1.4.8。















## [1.4.7] — 2026-08-07















- **examples/01-hermes-desktop「工具集成」批判落地（用户：请执行；全程反复核实 ground truth）**：







  - **关键发现（复验抓出过时误判）**：重新逐行读真实代码后，上一份批判报告中的多数条目**在当前磁盘代码里已修复**，属误判——逐项核对证据：`app.js:1736-1737`（掩码跳过守卫，A1/A2 已修）、`app.js:1552-1553`（二次确认，B3 已修）、`app.js:1816` 用后端下发 `ts.dangerous`（B4 已修）、`app.js:1533-1534`（排序持久化 `window._toolSortQuery`，C1 已修）、`main.py:704` 路由已是 `/api/toolsets/toggle`（B1 路由已修）、`agent_runtime.py:1014` 注释表明 `configure_toolset` 已改用 `update_config_yaml` 与 `set_toolset_disabled` 统一写路径（B2 已修）、`app.js:1876-1879` 已是标准 SSE 解析（`buf.split("\n\n")` + 过滤注释行 + 拼接多行 data，C2 已修）、`app.js:1692-1697` 已有「复制安装指引」按钮（C3 已修）。**未盲改这些已修复项，避免制造无意义 churn**。







  - **唯一真实 bug（已修）**：`main.py:732` 的 `api_toolset_batch` 端点调用 **不存在的** `ar.set_tool_disabled`（该函数此前已整体重命名为 `set_toolset_disabled`，定义在 `agent_runtime.py:1354`，但批量端点漏改）→ 「全部启用/全部禁用」按钮会 `AttributeError` 崩溃。改为 `ar.set_toolset_disabled(n, disabled)`（签名一致）。







  - **验证**：`py_compile examples/01-hermes-desktop/main.py` 退出 0；grep 确认 `set_toolset_disabled` 现被 `main.py:707`（toggle）与 `main.py:732`（batch）**两处一致调用**，`set_tool_disabled` 在 live 代码中已无残留（仅时间戳 `.bak.20260807-1500` 备份含旧名，未动）。







  - **残留观察（未改，待用户定）**：`examples/01-hermes-desktop/` 下存在 `main.py.bak.20260807-1500`、`agent_runtime.py.bak.20260807-1500` 等时间戳备份文件，不计入打包但污染仓库；`README.md` 称「工具集开关（14 个）」而 `agent_runtime.py` 注册表实际暴露更多项，文档数字可能陈旧。两者均不阻断功能，留待用户决定清理/更新。















## [1.4.6] — 2026-08-07















- **一致性 + 健壮性修复（用户授权决策，非技术背景，由我拍板落地）**：







  - **references 发布门禁数更正（与 SKILL.md A3/1.4.5 对齐）**：`references/15-workflow.md:98`「3 硬门禁 quality_check→check_endpoints→smoke_test_web」→「4 硬门禁 track_upstream --gate→quality_check→check_endpoints→smoke_test_web」；`references/12-quality-gates.md:151`「3 个硬门禁」→「4 个硬门禁」并补全硬门禁清单第 1 项 `track_upstream --gate`（原清单漏列，仅 3 项）。







  - **`examples/01-hermes-desktop/hermes_config.py` 读写闭环加固（消除静默丢配置）**：`read_config_yaml` 在 `pyyaml` 缺失时原本静默返回 `{}`，而 `_write_config_yaml_full` 仍把配置写盘（旧 `_manual_yaml` 分支）→「写成功、读空」隐患。改为无 `pyyaml` 时写盘用 `json.dumps`、读回用 `json.loads` 闭环；并删除已成为死代码的 `_manual_yaml`。**生产冻结环境（pyyaml 随 hermes-agent 安装）仍走 yaml 分支，行为完全不变**。







  - **验证**：受管 Python（无 pyyaml）下用真实 `hermes_config` 复现 `t_toolset_policy` 合并逻辑，修复后「用户禁用」正确合并（step3 merged 含 `browser`）→ 假阴性消除；`check_skill_gate.py` 退出 0；全技能「3 硬门禁」残留 0（仅历史 CHANGELOG[1.2.0] 保留）。















## [1.4.5] — 2026-08-07















- **SKILL.md 批判落地（正确性 + 一致性，经交叉核对真实文件 ground truth）**：







  - **A1 版本号对齐**：SKILL.md frontmatter `version` 由 `1.4.2` 升到 `1.4.5`（1.4.3/1.4.4 已改 SKILL.md 内容却漏升版本，违反版本递增铁律）。同步修正本文件顶部「version +0.1.0（见 §0）」为实际 `+0.0.1` 惯例，并去掉指向错误节（§0 是上游漂移节，非版本规则）的断链。







  - **A2 旗舰示例规模更正**：§8「24,000 行拆成 37 个模块」→「约 1.9 万行拆成 35 个模块」（实测 `examples/01-hermes-desktop/`：35 个 .py 文件、19,177 行）。







  - **A3 发布门禁数更正**：§4「release_gate … 3 硬门禁」→「4 硬门禁」并列出 `track_upstream --gate`（1.4.3 新增的第 4 道硬门禁，release_gate.py 实测 4 道：track_upstream[0/4] / quality_check[1/4] / check_endpoints[2/4] / smoke_test_web[3/4]）。







  - **B3 track_upstream 描述补全**：§4 脚本表补 `--gate` 模式说明（仅源码签名漂移硬阻塞，供 release_gate 调用）。







  - **B4 `[web]` extra 路线化**：§6 装包铁律「桌面应用通常只需…如 [web]」改为按路线——FastHTML+pywebview 路线还需 `[web]`，Tkinter 路线用基础包（勿带 `[web]`，与 templates B3 修复一致）。







  - **C 类联网核实（无需改）**：C1 PyPI `hermes` 最新确为 `0.9.1`（2026-01-12）✓；C3 `hermes-agent` Requires-Python 确为 `<3.14, >=3.11` ✓（与 SKILL.md §6 / 15-workflow.md 一致）；C2「23 个顶层模块」PyPI 页不列模块清单、无法外部确认，但 glossary/01/10 内部一致且锁定 0.18.2，保留。







  - **验证**：`check_skill_gate.py` 退出 0；全技能 grep「3 硬门禁」仅历史 CHANGELOG[1.2.0]（保留）；`version` 已 1.4.5；examples 实测 35 模块 / 19,177 行已对齐描述。















## [1.4.4] — 2026-08-07















- **templates/ 批判落地（铁律 + 防崩溃 + 稳健性 + references，经核对真实文件 ground truth）**：







  - **A1 铁律（冻结态 HERMES_HOME）**：`tkinter_minimal/main.py` 原缺 `sys.frozen` 下守卫，与 `fasthtml_minimal/main.py` 不一致且违反 §6 冻结态铁律。补 `if getattr(sys, "frozen", False): os.environ.setdefault("HERMES_HOME", os.path.join(os.path.dirname(sys.executable), "hermes_data"))`（`setdefault` 不覆盖既有设置，置于 `from run_agent import` 之前），两模板一致。







  - **A2 防首帧崩溃**：`tkinter_minimal/main.py` 的 `_append` 用 `self.log.get("end-2c", "end-1c")` 判行尾，空 / 极短 Text 时 "end-2c" 跨过起始索引、部分 Tk 版本抛 `TclError`、首条流式 delta 即崩。改为 `try/except tk.TclError`（异常时 `last_char=""`），保留「stream 且末字符非换行则内联、否则换行加 who: 前缀」语义。







  - **A3 打包卫生**：删除 `templates/fasthtml_minimal/__pycache__/main.cpython-312.pyc`、`main.cpython-313.pyc` 与 `templates/tkinter_minimal/__pycache__/*`（含与受管 3.13 不符的 cpython-312 产物）；新增 `templates/.gitignore`（`__pycache__/` + `*.pyc`）防复发。（注：`py_compile` 验证后会重新生成，已即删。）







  - **B1 去夸大**：`templates/README.md` 的 `fasthtml_minimal` 路线原标「FastHTML + pywebview + SSE」夸大（pywebview 由 launcher 提供，不在模板内；`fasthtml_minimal/README.md` 已说明）。改为「FastHTML + SSE」。







  - **B2 跨平台设 key**：两模板 README 与两 `main.py` docstring 的 `set HERMES_API_KEY=sk-...`（仅 Windows）补 `# macOS / Linux: export HERMES_API_KEY=sk-...`，mac/Linux 抄时不漏 key。







  - **B3 最小 venv**：`tkinter_minimal/requirements.txt` 的 `hermes-agent[web]` 多余（无 web）且违反 §6 最小 venv → 纯 `hermes-agent`。（注：`examples/01-hermes-desktop` 与 `references/10-install-and-env.md` 的 `hermes-agent[web]` 合法，不动——前者确用 web 工具 + pywebview，后者明确标注为「需 web 工具时的条件 extra」。）







  - **B4+B5 死代码 + 一致性**：`fasthtml_minimal/main.py` 的 `out.put({"type": "done", "final": res["final_response"]})` 中 `final` 字段前端 JS 从不消费（`it.final` 未读取）→ 死代码。删之（`res` 不再赋值，仅发 `{"type":"done"}`）。顺带使两模板对 `run_conversation` 返回值处理一致（fasthtml 不再抓 final、tkinter 本就忽略），B5 一并解决。







  - **B6 裸号引用改全名**：`fasthtml_minimal/main.py` 的「（见 references/05、07、08）」与「（见 03）」、`templates/README.md` 的「（07）/（08）/（11）/（05 vs 06）」全部改为 `references/NN-*.md` 全名。模板 README（07/08/11/02）本已全名，无需改。







  - **C1 references 函数名误植**：`references/01-library-api.md:323` 误写 `stream_agent`，真实函数为 `stream_agent_chat`（已核实 `examples/01-hermes-desktop/agent_runtime.py:593`；`tkinter_minimal/README.md:18` 亦用此名）。改回 `stream_agent_chat`。







  - **验证**：`py_compile` 两模板 `main.py` + `scripts/*.py` 全过；`check_skill_gate.py` exit 0；全技能 grep `hermes-agent[web]`（仅合法处）、`FastHTML + pywebview`（仅完整集成描述处）、`stream_agent` 误植（0）、`references/0N` 裸号（0）、`templates` 下 `.pyc`（0）全部符合预期。















## [1.4.3] — 2026-08-07















- **scripts/ 批判落地（正确性 + 稳健性，经 `ast` 对冻结 0.18.2 源码 + `api-baseline.json` 反复核实）**：







  - **A1 回调计数纠正**：`probe_library.py` 原称「17 回调」但只查 15 个；核实 `AIAgent.__init__` 实为 **15 个构造器回调**（`stream_callback` 在 `run_conversation`/`chat` 上）。标签/变量统一改 `15 构造器回调`；并同步纠正 SKILL.md / references / docs / CHANGELOG 中错误的「17 回调」表述。







  - **A2/A5 章节指针纠正**：`smoke_test_web.py` 的「§3 人工冒烟」→「§5 步骤⑦」；4 个脚本 docstring 及 SKILL.md / references / CHANGELOG 中不存在的 `§0.1/§0.2/§0.3/§0.4` 子节号统一改为 `§0`（扁平节）+ ①②③ 编号。







  - **A3 防假阻塞**：`quality_check.py` 区分 `check_api_signature` 退出码——工具/环境错误（exit 2，如未装库、解析失败）降级为 `skip`，不再误判硬失败阻塞发布。







  - **A4 防死循环 + 备份**：`track_upstream.py --update-docs` 现在把新 md5/size 持久化到 `references/docs-baseline.json` sidecar（避免下次仍报 DRIFT），并在覆盖出厂 `hermes-llms-full.txt` 前先备份到临时目录（遵守「先备份再改」铁律）。







  - **B1 包级静态解析**：`check_api_signature.py` 当 `run_agent` 为包时扫整个包目录，避免子模块里的 `AIAgent` 漏抓导致假 REMOVED。







  - **B3 覆盖一致性**：`release_gate.py` 新增 `track_upstream --gate` 硬门禁——仅「源码签名」破坏性漂移硬阻塞；PyPI 版本 / 文档指纹漂移为提示性（锁定旧版是有意选择，不阻塞）。







  - **B4 结构门禁列管**：`check_skill_gate.py` 将 `examples/01-hermes-desktop/test_bridge.py` 纳入 EXPECTED。







  - **B5 版本单一来源**：`track_upstream.py` / `check_api_signature.py` 基线版本改从 `references/api-baseline.json` 读取，消除三处硬编码 `0.18.2` 漂移风险。







  - **C1/C4**：`check_endpoints.py` 注明静态解析局限；`probe_library.py` 的 `max_iterations` 默认值取值加 KeyError 防护。















## [1.4.2] — 2026-08-07















- **SKILL.md 裁剪「通用但不适用/不重要」的规则**：删除 §6 质量与门禁 中的 **「语法门禁：写完任何 `.py` 立即 `py_compile` + 导入测试」** 一条——它是通用 Python 卫生习惯（非 Hermes 专属），且已被 §5 ⑦（`py_compile → 导入 → …`）与 §6「反复核实」（重跑门禁脚本，脚本内含 py_compile）覆盖，属冗余。其余 §5–§8 条目经逐条核对均为 Hermes 专属（AIAgent / run_conversation / stream_callback / quiet_mode / max_iterations / disabled_toolsets / hidden-import 等），全部保留。`check_skill_gate.py` 全绿。















## [1.4.1] — 2026-08-07















- **SKILL.md §4 索引升级为 MOC（Map of Content）一级聚类**：在「主题路由」顶部加 🗺 MOC 总览表，把全部节点归入 6 个一级聚类——







  **① 核心 API / ② GUI 集成 / ③ 环境打包 / ④ 质量维护 / ⑤ 案例 / ⑥ 入门导航与参考实现**，每个聚类标注「覆盖节点 + 何时进」，索引更「地图化」。







- 把 `scripts/*` 门禁脚本从独立「脚本」小节并入 **④ 质量维护**；把「入口与决策 / 参考实现 / 交付验收清单」合并为 **⑥ 入门导航与参考实现**。所有原有节点与链接保持不变，无内容丢失。







- 本次为纯索引结构优化，不影响任何 API 断言、引用路径或门禁脚本；`check_skill_gate.py` 全绿。















## [1.4.0] — 2026-08-06















- **把 `examples/01-hermes-desktop` 的市场改造成「完全在线」形态（对标既有 FastHTML 桌面参考项目）**（用户要求：







  不要离线精选降级，要完全在线浏览/搜索/安装/卸载，还原参考项目原有市场样子）。







- **技能商店 → SkillHub 社区（完全在线）**：复用参考项目 `skillhub_client.py`（`api.skillhub.cn` 无鉴权搜索/分类）







  与前端组件 `static/skillstore.js`（`initSkillStore`，自带「技能市场/我的技能」双 Tab、搜索/分类/排序、







  安装确认弹层、启用/编辑/卸载/上传）。后端新增 `/api/skill-store/*`（sources/skills/categories/installed/







  +enable/detail/save/install/卸载）。







- **MCP 商店 → LobeHub 生态（完全在线）**：复用参考项目 `mcpstore_client.py`（内置 ~27 个 LobeHub 热门精选 +







  best-effort 爬取 `lobehub.com/zh/mcp` 增补）与前端组件 `static/mcpstore.js`（`initMcpStore`，自带「MCP 商店/







  我的 MCP」双 Tab、env Key 收集弹层、手动添加、编辑/停用/移除）。后端新增 `/api/mcp-store/*`（servers/







  categories/installed/install(+env)/+enable/save/移除）。







- 移除旧 `/api/skill-market/*`、`/api/mcp-market/*` 离线市场路由与前端渲染；`skill_market.py`/`mcp_market.py`







  不再被引用（文件保留，待确认是否清理）。`app.js` 技能/MCP 面板改为挂载 `initSkillStore`/`initMcpStore`。







- `app.css` 补充组件依赖的全局类（`.btn-primary/.btn-outline/.btn-danger/.btn-sm/.form-input/.skill-toggle` +







  主题变量别名，浅/深双主题协调）。`smoke_test_web.py` 市场契约断言更新为 `/api/skill-store/skills`、







  `/api/mcp-store/servers`。







- 验证：py_compile 全绿、`test_bridge.py` 12/12、`smoke_test_web` 全通过（技能商店 /api/skill-store/skills 200







  返回 24 项、MCP 商店 /api/mcp-store/servers 200 返回 24 项）、`check_endpoints` 无 404（后端 69 路由）、







  端到端联网实测技能安装+卸载（summarize）、MCP 安装+停用+移除（playwright）全部成功。















## [1.3.0] — 2026-08-06















- **SKILL.md 按「SKILL Graph 模式」重构为认知地图 / 索引**（用户指令：非核心内容移出、去掉 LLM 无法访问的内容、去掉无关内容）。







- **修复规则 2 违规**：移除 SKILL.md 中机器专属绝对路径，并改为完全自包含——GUI 框架权威源改指本技能内置的 `references/05`、`references/06`，不再依赖任何外部技能。







- **非核心操作细节移出 SKILL.md，落到 `references/` 对应节点**：







  - `references/13-maintenance.md`：§0 上游漂移的基线值、三条跟踪线脚本用法、更新工作流。







  - `references/14-antipatterns.md`：原 §7 八条反模式与红线完整清单。







  - `references/15-workflow.md`：原 §5 完整 ①→⑨ 工作流 + 各步产出物验收表。







  - `references/01-need-discovery.md`：需求澄清框架（原 SKILL.md 已引用但文件缺失，补建，消除悬空链接）。







- SKILL.md 由 507 行精简到 288 行；保留核心（用途 / HARD-GATE / 架构约束 5 条 / 主题路由索引 / 铁律）；







  所有 `references/`、`docs/`、`examples/`、`templates/`、`scripts/` 引用改为带语义语境的链接。







- 结构门禁 `scripts/check_skill_gate.py` 仍全绿（新增 references 文件均真实存在）。















## [1.2.0] — 2026-08-06















- **对标成熟的桌面门禁标杆，补齐成熟门禁机制**（原活跃副本路径已移除，因其含机器专属绝对路径）。







- **新增 `scripts/smoke_test_web.py`**（对标成熟的桌面无头冒烟实践）：用 Starlette `TestClient`







  驱动示例 app 作**网页无头冒烟**——断言 `GET /` 含关键 DOM id（convSearch / usageChip / analyticsBody /







  Hermes Desktop / btnAnalytics）+ `/healthz` 200。**无需 API Key、不触发真实 LLM 往返**，捕获「首页渲染崩溃」







  （如漏导入 `Input` 导致 `NameError`）。把 `delivery-checklist.md` B 档「关键 DOM id 渲染正常」从人工肉眼升级为自动断言。







  - **Prove-It**：把 `main.py` 的 `id="convSearch"` 改成无关 id 后重跑，脚本正确返回 exit 1（非假绿），已验证。







- **`release_gate.py` 升级为「3 硬门禁 + 2 CI 建议项」结构**（对标成熟的发布门禁实践）：







  - 硬门禁：`quality_check` → `check_endpoints` → `smoke_test_web`（任一失败即阻断，exit 1）。







  - CI 建议项（失败仅告警不阻塞）：`verify_imports`（scripts/ 门禁脚本可导入）、`check_refs`（`references/` 文档 ```` ```python ```` 代码块语法）。







  - 支持 `--skip-quality` / `--skip-endpoints` / `--skip-smoke` / `--skip-imports` / `--skip-refs` / `--advisory-only`。







- **`check_refs` 借此修掉 `references/01-library-api.md` 两处签名摘录的语法错误**（HARD-GATE 权威 API 文档，须准确）：







  `AIAgent.__init__` 签名摘录里的裸 `...` 参数行、回调参数摘录的裸缩进参数块——均已包成可编译签名。







- **SKILL.md**：`version: "1.2.0"`；§4 脚本表新增 `smoke_test_web.py`、release_gate 行改述 3 硬门禁 + 2 CI 建议项、







  新增门禁对标说明；§5 ⑦ 运行验证加网页无头冒烟、§5 统一发布门禁 callout 更新；







  §6 质量段新增「网页无头冒烟」铁律、反复核实 loop 加入 `smoke_test_web`。







- **`references/12-quality-gates.md`**：§7 改为「3 硬门禁 + 2 CI 建议项」；新增 §7.1 网页无头冒烟；







  §9 反复核实循环表加入 `smoke_test_web`。







- **`docs/delivery-checklist.md`**：A 档补 `smoke_test_web`、B 档标 DOM id 检查已自动化、反复核实循环加入 `smoke_test_web`。















### 已知基线漂移（发布时）















- 同 1.0.0 / 1.1.0：PyPI 最新 `0.19.0`（2026-07-20），本技能源码断言基于 0.18.2。`track_upstream` [①] 仍显示该漂移，







  但 [② 文档 md5] + [③ 源码签名] 仍 ✅，技能事实断言准确（见 §9 / delivery-checklist D 段口径）。















### 待办（后续版本）















- [ ] 0.19.0 适配：若签名变更，更新 `01-library-api.md` 与 `api-baseline.json`







- [ ] （非阻断）pywebview 原生界面视觉质检等价物（本技能自带 `scripts/ui_window_verify.py` + `scripts/ui_automate.py`）、B 档 Visual Workflows/Kanban/Group Chat、首条消息冷启动预暖（bindImportConv 仍未接线）















## [1.1.0] — 2026-08-06















- **对标成熟的桌面壳/打包标杆，补齐成熟机制**（用户指令：反复核实、万无一失）。







- **修复 HARD-GATE 路径腐烂风险**：原 SKILL.md §1 / `05-fasthtml-integration.md` 指向的外部克隆路径改为本技能内置引用（GUI 框架权威源现为本技能自带的 `references/05`、`references/06`），彻底消除对外部技能目录的依赖。







- **配置驱动启动器**：新增 `examples/01-hermes-desktop/launcher.json`







  （app_name/entry/venv_name/requirements/host/port/window），`launcher.py` 改为读配置 +







  默认值回退（缺失/畸形 json → `{}` → 默认值，已单测三态通过）。







- **新增 `scripts/release_gate.py`**：统一发布门禁，串联 `quality_check` + `check_endpoints`，







  全绿（exit 0）才放行；界面视觉质检由本技能自带的「pywebview 原生窗口 DOM 断言（`scripts/ui_window_verify.py`）+ 可选 html2canvas 无头截图 + UI 交互自动化（`scripts/ui_automate.py`）」承担（非强拦）。







- **新增 `scripts/check_endpoints.py`**：前端 `app.js` → 后端 `main.py` 路由链路校验，







  捕获运行时 404 隐患；已知良好示例实测后端 53 / 前端 40 / 0 未匹配 / exit 0（零误报）。







  已修一处严重假阴性（`/api/conversations/TYPOD/rename` 曾被误判已覆盖，删反向前缀规则后正确拦截）。







- **新增 `docs/delivery-checklist.md`**：A 机器门禁 / B 真实运行 / C 产物与文档 / D 版本与漂移四段，







  附「反复核实循环」六脚本清单。







- **SKILL.md**：`version: "1.1.0"`；§4 脚本表新增 `release_gate.py` / `check_endpoints.py`；







  §5 ⑥ 补 TDD 语言、⑧/⑨ 补统一发布门禁 + ⑨交付（先读 delivery-checklist.md）；







  §6 质量段补发布门禁 / 路由链路校验 / 反复核实 loop 三条铁律。







- **`references/12-quality-gates.md`**：新增 §7（release_gate）/ §8（check_endpoints）/ §9（反复核实循环）。















### 已知基线漂移（发布时）















- 同 1.0.0：PyPI 最新 `0.19.0`（2026-07-20），本技能源码断言基于 0.18.2。







  首次使用前仍应跑 `track_upstream` + `check_api_signature` 确认无破坏性变更。















### 待办（后续版本）















- [ ] 0.19.0 适配：若签名变更，更新 `01-library-api.md` 与 `api-baseline.json`







- [ ] （非阻断）pywebview 原生界面视觉质检等价物（本技能自带 `scripts/ui_window_verify.py` + `scripts/ui_automate.py`）、B 档 Visual Workflows/Kanban/Group Chat、首条消息冷启动预暖（bindImportConv 仍未接线）















## [1.0.0] — 2026-08-06















- **初始发布**。定位：在 FastHTML/Tkinter 桌面 GUI 中进程内集成 Hermes Python Library。







- 事实基线锁定：**`hermes_agent 0.18.2`**（源码实证）。







- 引入 §0 仓库变化跟踪机制：







  - `scripts/check_api_signature.py`（ast 静态比对 `AIAgent.__init` / `run_conversation` / `chat`，不 import）







  - `scripts/track_upstream.py`（PyPI 版本 + `hermes-llms-full.txt` 指纹 + 源码签名三线）







  - `scripts/probe_library.py`（本机 Library 健康自检）







  - `scripts/check_skill_gate.py`（技能结构门禁）







  - `references/api-baseline.json`（0.18.2 实证签名基线）







- 收录 `references/01-library-api.md`：源码派生的完整参数表（含官方文档漏载的 15 个构造器回调）。







- 收录 GUI 集成范式（FastHTML `05` / Tkinter `06`）、回调桥接 `03`、工具面 `07`、办公治理 `08`、







  会话持久化 `09`、装包 `10`、打包 `11`、质量门禁 `12`、外部案例 `13`、文档索引 `00`。







- 收录 `docs/troubleshooting.md` / `docs/glossary.md`。















### 已知基线漂移（发布时）















- PyPI 最新版已达 **`0.19.0`（2026-07-20，PyPI upload_time UTC）**，本技能源码断言基于 0.18.2。







  首次使用前**应当**跑 `python scripts/track_upstream.py` 与 `python scripts/check_api_signature.py`







  确认 0.19.0 是否改动 `AIAgent.__init__` 签名；若有破坏性变更，先按 §0 更新技能再开工。















### 待办（后续版本）















- [x] 旗舰示例 `examples/01-hermes-desktop/`（通用底座，与业务解耦）落地（Task #8 / #25）







- [x] 最小骨架 `templates/`（FastHTML + Tkinter）（Task #23）







- [x] 离线桥接测试 `_testkit.py` / `test_bridge.py` + 全量门禁 `scripts/quality_check.py`（Task #26）







- [x] 打包三件套：`build.py`（外置隔离 venv + PyInstaller 单文件）/ `launcher.py`（自包含 pywebview 壳）/ `启动.bat`（GBK+CRLF）+ `.env.example` / `.gitignore`（Task #27）







- [ ] 0.19.0 适配：若签名变更，更新 `01-library-api.md` 与 `api-baseline.json`
