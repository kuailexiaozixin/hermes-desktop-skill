# 03 · 能力与工具集（57 项逐条文档）

> 本文是 **57 个工具集的单一全量参考**，经 `hermes-agent==0.19.0` 的 `tools.delegate_tool.TOOLSETS`
> **逐条内省**核实（描述原文取自源码 `description` 字段，工具列表取自 `tools` 字段）。
> 任何「某能力有什么工具」以本文为准；别处不再重复列全表。

---

## 1. 工具集系统

- 注册表：`from tools.delegate_tool import TOOLSETS`（顶层模块，非 `hermes.toolsets`；0.19.0 起 `TOOLSETS` 已自
  旧的 `toolsets` 模块迁至 `tools.delegate_tool`）。
- 结构：每项 = `{ "description": str, "tools": list[str], "includes": list[str] }`。
- 总数 **57** = **33 个 capability** + **24 个 `hermes-*` 集成**。
- 指令口径（减法原则，见 `01` §3.2）：`enabled_toolsets=None` 启用全部；用
  `disabled_toolsets` 做减法。进程内桌面常态 `disabled=["terminal"]`。
- 派生命名：`coding` / `hermes-acp` / `hermes-api-server` / `hermes-cli` / `hermes-cron` 是
  **聚合型**工具集（组合多个基础工具）；`safe` / `debugging` 用 `includes` 复用基础集；
  `hermes-gateway` 用 `includes` 并集所有平台。

---

## 2. 审批闭环（进程内形态必须自建）

**R5**：网关的「危险命令审批分类器」（`approvals.mode`）在进程内形态**无触发源**
（因为 `terminal` 被禁用，且没有网关事件流）。因此**审批/护栏必须由应用层工具实现**：

| 模块 | 作用 |
| --- | --- |
| `tools.approval` / `tools.write_approval` | 写类操作的审批拦截 |
| `tools.slash_confirm` | 斜杠命令二次确认 |
| `agent.tool_guardrails` | 工具护栏（`ToolGuardrailDecision`） |
| `agent.tool_executor` / `agent.tool_dispatch_helpers` | 工具派发与前置检查 |
| `tools.path_security` / `tools.threat_patterns` / `tools.tirith_security` | 路径/威胁/安全扫描 |

> 桌面应用若要暴露「文件写/命令执行」类能力，必须在自建工具层加审批，而不是依赖网关。

> **桥接到 `12`**：上表各审批/护栏模块的**文件级细节**（模块路径、公开 API、进程内可用性）一律见 `12-tools-modules.md`
> （搜 `tools.approval` / `tools.write_approval` / `tools.slash_confirm` / `agent.tool_guardrails` / `agent.tool_executor` /
> `tools.path_security` / `tools.threat_patterns` / `tools.tirith_security`）。「工具集 → 实现模块」的完整映射见 §6。
> 本文只讲**行为语义与开关**，模块实现不在此复述。

---

## 3. 33 个 capability 工具集（逐条）

> 模板：名称 · 工具数 · 描述（源码原文）· 关键工具 · 备注。

### 3.1 联网与检索
- **web** (2) — Web research and content extraction tools · `web_search`, `web_extract`
- **search** (1) — Web search only (no content extraction/scraping) · `web_search`
- **x_search** (1) — Search X (Twitter) posts/threads via xAI built-in x_search Responses tool; 需 xAI 凭证（SuperGrok OAuth 或 `XAI_API_KEY`），默认关，在 `hermes tools` → X Search 开启 · `x_search`
- **vision** (1) — Image analysis and vision tools · `vision_analyze`
- **video** (1) — Video analysis and understanding tools（opt-in，不在默认集）· `video_analyze`

### 3.2 生成
- **image_gen** (1) — Creative generation tools (images) · `image_generate`
- **video_gen** (3) — Video generation；单 `video_generate` 覆盖文生视频/图生视频/参考生视频，供应商特定 edit/extend 可能另成工具；经 `hermes tools` → Video Generation 配置 · `video_generate`, `xai_video_edit`, `xai_video_extend`

### 3.3 桌面控制
- **computer_use** (1) — 后台桌面控制 via cua-driver（mac/Win/Linux）：截图、鼠标、键盘、滚动、拖拽；**不抢占用户光标/键盘焦点**；任意支持工具的模型可用 · `computer_use`
- **terminal** (2) — Terminal/command execution and process management · `terminal`, `process`
  ⚠️ 进程内形态默认禁用（R5）；若启用须自建审批。

### 3.4 知识 / 技能 / 文件
- **skills** (3) — Access, create, edit, manage skill documents · `skills_list`, `skill_view`, `skill_manage`
- **file** (4) — 文件操作：read/write/patch（模糊匹配）/search（内容+文件）· `read_file`, `write_file`, `patch`, `search_files`
- **memory** (1) — Persistent memory across sessions（个人笔记 + 用户画像）· `memory`
- **todo** (1) — Task planning and tracking for multi-step work · `todo`
- **session_search** (1) — Search and recall past conversations with summarization · `session_search`
- **project** (3) — Desktop Projects：创建/切换命名工作区（仅 GUI 会话）· `project_list`, `project_create`, `project_switch`
- **clarify** (1) — Ask the user clarifying questions（多选或开放）· `clarify`
- **code_execution** (1) — Run Python scripts that call tools programmatically（减少 LLM 往返）· `execute_code`
- **delegation** (1) — Spawn subagents with isolated context for complex subtasks · `delegate_task`
  ⚠️ 委派事件的 SSE 透传未实测（R6）。

### 3.5 上下文引擎 / 浏览器 / 定时
- **context_engine** (0) — Runtime tools exposed by the active context engine（运行时由上下文引擎暴露，无静态工具）· —
- **browser** (13) — 浏览器自动化：navigate/click/type/scroll/iframes/hold-click + web search 找 URL ·
  `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_scroll`,
  `browser_back`, `browser_press`, `browser_get_images`, `browser_vision`, `browser_console`,
  `browser_cdp`, `browser_dialog`, `web_search`（依赖 Node，见 `05` §4）
- **cronjob** (1) — Cronjob 管理：创建/列出/更新/暂停/恢复/删除/触发定时任务 · `cronjob`

### 3.6 多智能体 / 物联网 / 媒体
- **homeassistant** (4) — Home Assistant 智能家居控制与监控 · `ha_list_entities`, `ha_get_state`, `ha_list_services`, `ha_call_service`
- **kanban** (9) — Kanban 多智能体协调；仅当 Agent 被 kanban dispatcher 拉起时激活（`HERMES_KANBAN_TASK` 环境变量）；dispatcher 默认在网关内运行（见 `kanban.dispatch_in_gateway`）·
  `kanban_show`, `kanban_list`, `kanban_complete`, `kanban_block`, `kanban_heartbeat`,
  `kanban_comment`, `kanban_create`, `kanban_link`, `kanban_unblock`
- **spotify** (7) — 原生 Spotify 播放/搜索/播放列表/专辑/媒体库 · `spotify_playback`, `spotify_devices`, `spotify_queue`, `spotify_search`, `spotify_playlists`, `spotify_albums`, `spotify_library`
- **tts** (1) — Text-to-speech：Edge TTS（免费）/ ElevenLabs / OpenAI / xAI · `text_to_speech`

### 3.7 消息平台（capability 级）
- **discord** (1) — Discord 读取与参与：拉消息/搜成员/建线程 · `discord`
- **discord_admin** (1) — Discord 服务器管理：列频道/角色、置顶、分配角色 · `discord_admin`
- **yuanbao** (5) — 元宝平台：群信息/成员查询/私聊/贴纸 · `yb_query_group_info`, `yb_query_group_members`, `yb_send_dm`, `yb_search_sticker`, `yb_send_sticker`
- **feishu_doc** (1) — 读取飞书/Lark 文档内容 · `feishu_doc_read`
- **feishu_drive** (4) — 飞书/Lark 文档评论：列出/回复/添加 · `feishu_drive_list_comments`, `feishu_drive_list_comment_replies`, `feishu_drive_reply_comment`, `feishu_drive_add_comment`

### 3.8 聚合 / 安全型
- **debugging** (2) — Debugging and troubleshooting toolkit · `terminal`, `process`；`includes`: `web`, `file`
- **safe** (0) — Safe toolkit without terminal access；`includes`: `web`, `vision`, `image_gen`
- **coding** (32) — 编码向聚合：files/terminal/search/web docs/skills/todo/delegate/vision/browser ·
  含 `read_file`,`write_file`,`patch`,`search_files`,`vision_analyze`,`skills_*`,`browser_*`,
  `todo`,`memory`,`session_search`,`clarify`,`execute_code`,`delegate_task`,`web_search`,`web_extract`,`terminal`,`process`,`read_terminal`,`close_terminal`
> 注：`hermes-acp`(29) / `hermes-api-server`(35) 是**聚合型 `hermes-*` 集成**（属 24 个 `hermes-*` 而非 33 个 capability），
> 工具组为 `coding` 的变体，见 §4.1。

---

## 4. 24 个 `hermes-*` 集成（逐条）

> 这些**消息平台绑定在进程内形态下默认不启用**（无网关，见 `02` §5）；若放开为网关形态则按网关路线激活。下表给出事实与工具构成，
> 供「应用自收平台消息 → 调 `AIAgent`」的进程内桥接参考。

### 4.1 复合/元工具集（4 个）
- **hermes-cli** (49) — Full interactive CLI toolset：全部默认工具 + cronjob 管理 ·
  基础 49 工具 = `web/file/browser/vision/skills/tts/todo/memory/session_search/clarify/
  execute_code/delegate/cronjob/ha_*/kanban/computer_use` + `terminal/process/read_terminal/close_terminal`
- **hermes-cron** (49) — Default cron toolset：与 hermes-cli 同核心工具，受 `hermes tools` 门控
- **hermes-api-server** (35) — 见 §3.8（OpenAI 兼容 HTTP 用，无交互 UI 工具）
- **hermes-acp** (29) — 见 §3.8（编辑器集成）

### 4.2 消息平台（20 个，均 49 工具，基础同 hermes-cli，差异在后）
| 工具集 | 差异（在 49 基础工具上额外/特有） | 说明 |
| --- | --- | --- |
| `hermes-telegram` | — | 个人使用全权限（terminal 有安全检查） |
| `hermes-whatsapp` | — | 类似 Telegram（个人消息，更可信） |
| `hermes-slack` | — | 工作区使用全权限（terminal 有安全检查） |
| `hermes-signal` | — | 加密消息平台全权限 |
| `hermes-bluebubbles` | — | Apple iMessage via 本地 BlueBubbles server |
| `hermes-homeassistant` | — | 智能家居事件监控与控制 |
| `hermes-email` | — | 经邮件交互（IMAP/SMTP） |
| `hermes-mattermost` | — | 自托管团队消息全权限 |
| `hermes-matrix` | — | 去中心化加密消息全权限 |
| `hermes-dingtalk` | — | 企业消息平台全权限 |
| `hermes-weixin` | — | 个人微信 via iLink 全权限 |
| `hermes-qqbot` | — | QQ 消息 via Official Bot API v2 |
| `hermes-wecom` | — | 企业微信消息全权限 |
| `hermes-wecom-callback` | — | 企业自建应用消息全权限 |
| `hermes-sms` | — | 经 SMS 交互（Twilio） |
| `hermes-discord` (51) | + `discord`, `discord_admin` | Discord bot（terminal 经危险命令审批） |
| `hermes-feishu` (54) | + `feishu_doc_read`, `feishu_drive_*` | 飞书/Lark 企业消息 |
| `hermes-yuanbao` (54) | + `yb_*` | 元宝消息平台 |
| `hermes-webhook` (4) | `web_search`,`web_extract`,`vision_analyze`,`clarify` | 接收/处理外部 webhook 事件 |
| `hermes-gateway` (0) | `includes` 并集全部 19 个平台（telegram/discord/whatsapp/slack/signal/bluebubbles/homeassistant/email/sms/mattermost/matrix/dingtalk/feishu/wecom/wecom-callback/weixin/qqbot/webhook/yuanbao） | 网关工具集，仅网关路线用 |

---

## 5. 常见开关配方（进程内桌面）

| 需求 | `enabled_toolsets` | `disabled_toolsets` |
| --- | --- | --- |
| 全功能桌面（推荐起点） | `None` | `["terminal"]` |
| 离线模式 | `None` | `["terminal","web","browser"]` |
| 纯编码助手 | `None` | `["terminal"]`（再用 `coding` 集思路） |
| 安全无终端 | `None` | `["terminal"]`（或参考 `safe` 集思路） |

> 任何配方都**不要**把 `enabled_toolsets` 写成 `["file"]` 之类（R4）——那会砍掉联网/记忆/浏览器。

---

## 6. 工具集 → 实现模块映射（桥接 `12-tools-modules.md`）

> 本表是 **03（行为/开关）与 12（模块文件/接口）的唯一桥接**：给出每个工具集的**主要实现模块**，
> 不复述行为语义。模块路径、公开 API、进程内可用性以 `12` 为准（逐模块经 0.19.0 源码内省核实）。
> 映射经 `tools.registry` 反查 `entry.handler.__module__` 得到（已逐条验证，非推断）。

### 6.1 有专属实现模块的工具集（capability 级）

| 工具集 | 主要实现模块 | 备注 |
| --- | --- | --- |
| `web` | `tools.web_tools` | |
| `search` | `tools.web_tools` | `web` 的子集 |
| `x_search` | `tools.x_search_tool` | 需 xAI 凭证 |
| `vision` | `tools.vision_tools` | |
| `video` | `tools.vision_tools` | 与 `vision` 同模块 |
| `image_gen` | `tools.image_generation_tool` | |
| `video_gen` | `tools.video_generation_tool`, `tools.xai_video_tools` | |
| `computer_use` | `tools.computer_use_tool` | |
| `terminal` | `tools.terminal_tool`, `tools.process_registry` | |
| `skills` | `tools.skills_tool`, `tools.skill_manager_tool` | |
| `file` | `tools.file_tools` | |
| `memory` | `tools.memory_tool` | |
| `todo` | `tools.todo_tool` | |
| `session_search` | `tools.session_search_tool` | |
| `project` | `tools.project_tools` | |
| `clarify` | `tools.clarify_tool` | |
| `code_execution` | `tools.code_execution_tool` | |
| `delegation` | `tools.delegate_tool` | |
| `browser` | `tools.browser_tool` | 含 `browser_cdp_tool` / `browser_dialog_tool` / `web_tools` 子工具 |
| `cronjob` | `tools.cronjob_tools` | |
| `homeassistant` | `tools.homeassistant_tool` | |
| `kanban` | `tools.kanban_tools` | |
| `spotify` | `plugins.spotify.tools` | 插件包，非 `tools` |
| `tts` | `tools.tts_tool` | |
| `discord` | `tools.discord_tool` | |
| `discord_admin` | `tools.discord_tool` | 与 `discord` 同模块 |
| `yuanbao` | `tools.yuanbao_tools` | |
| `feishu_doc` | `tools.feishu_doc_tool` | |
| `feishu_drive` | `tools.feishu_drive_tool` | |

### 6.2 聚合 / 运行时型（无专属模块，模块 = 所包含能力并集）

| 工具集 | 类型 | 说明 |
| --- | --- | --- |
| `coding` / `safe` / `debugging` | 聚合 | 模块为其 `includes`/组合能力的并集（见 §3.8） |
| `context_engine` | 运行时 | 由上下文引擎运行时暴露，无静态实现模块 |
| `hermes-cli` / `hermes-cron` / `hermes-api-server` / `hermes-acp` | 聚合变体 | `coding`/`cli` 的核心集变体（见 §4.1） |
| `hermes-*` 消息平台（20 个） | 聚合变体 | 49/54 工具变体，模块为 `hermes-cli` 并集 + 平台特有（见 §4.2） |

> 聚合型工具集本身没有单一实现模块；其工具分散在 §6.1 列出的各 capability 模块中。
> 需要「某个具体工具落在哪个文件」时，先在本表 §6.1 按工具集定位模块，再到 `12` 查该模块的公开 API。
