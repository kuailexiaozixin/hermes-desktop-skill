# 16 · `gateway` 包全量模块枚举（Hermes 网关运行时，0.19.0，共 77 个 `.py`）

> 本文件是顶层 `gateway` 包的**完整、逐模块枚举**。经 `hermes-agent==0.19.0` 已装包**逐模块读取 docstring + AST 提取公开 API** 核实；
> 全部 77 个 `.py`（72 个功能模块 + 5 个 `__init__.py`）无一遗漏，含 `platforms.qqbot.*` / `relay.*` 等子包。
>
> **为什么要单独一篇**：`gateway` 是 23 个顶层模块之一，但此前只在 `14-library-infra.md` §1 被当作「一行」交代（`Hermes 网关`），
> 包内 77 个 `.py` 从未逐模块枚举——这是 Library 全貌里**最后一个未展开的包**。本文按 `12-tools-modules.md` / `13-agent-modules.md`
> 的同一格式把它补全，使「Library 全貌收口」真正名符其实。
>
> **适用说明（与 `07` §1、`10` §1 一致）**：本文聚焦「Hermes 网关」路线（5 条平等可选路线之一；其余见 `01`/`10`/`15`），以**进程内直跑路线**为叙述对照（网关 / CLI / API Server / `/v1` 均平等可选，无先后顺序）。
> `gateway` 包是**网关路线**的运行时实现；若选用进程内直跑路线则**不起网关、不 import 其主函数**（`gateway.run` / `gateway.config` 等常驻设施）；
> 但 `api_server` adapter（`15`）与平台适配器（§2）是你理解「网关平台接入 / API Server」形态时必读的。

> **路线平等声明**：调用 Python Library 有 5 条**平等可选**技术路线——进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`——**无先后顺序，按需选用其一**。本文是其中「Hermes 网关」路线的完整模块枚举；其余 4 条路线见 `01-library-api.md`（进程内直跑示例）/ `10-hermes-cli.md`（spawn CLI）/ `15-api-server.md`（API Server·`/v1`）。本文中「进程内直跑」仅作叙述对照，不代表该路线优先或推荐。

## 0. `gateway` 包是什么、为什么单独一篇

- **是什么**：`gateway` 是 Hermes 的**网关运行时顶层包**（`top_level.txt` 23 个顶层模块之一），即「Hermes Gateway——多平台消息集成」的代码实现。
  它常驻运行（`hermes gateway` 由 `hermes_cli.gateway` 子命令拉起），内部起 HTTP 服务（默认 `127.0.0.1:8642`），
  对外暴露 OpenAI 兼容 `/v1` 端点（`platforms/api_server.py`），并通过「内置核心（`gateway/platforms/*`）+ 插件平台（`plugins/platforms/*`）」适配器接入消息平台（双轨，见 §2）。
- **与 10 的边界**：`10-hermes-cli.md` 列的 `hermes_cli.gateway` 是 CLI **启动子命令**；本文列的 `gateway.*` 是**顶层包**（网关运行时本体），二者是「命令入口 vs 实现」的关系。
- **与 15 的边界**：`15-api-server.md` 讲 API Server **如何使用/如何接入**（判据/配置/端点/认证/进程内自建）；本文只负责 `gateway` 包**有哪些模块、各自干什么**这一层，不重复能力语义。
- **与 14 的边界**：`14-library-infra.md` §1 曾把 `gateway` 作为基础设施一行列出并给出「为什么进程内不用」；本文把该包**内部 77 个模块逐一枚举**，两者互补，`14` §1 gateway 行已改为指向本文。

## 1. 全量模块清单（77 个，按子包/顶层分组，不交叉不重合）

> 每行：模块 | 真实用途（取自 0.19.0 docstring）| 代表公开 API（仅列真实存在者）。
> `gateway` 子包 = `platforms`（平台适配器）/ `relay`（实验性中继）/ `builtin_hooks`（内置钩子）；顶层 42 个功能模块。

### 1.1 (top)（42 个）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `authz_mixin` | User-authorization methods for ``GatewayRunner``. | GatewayAuthorizationMixin |
| `cgroup_cleanup` | SIGKILL any process left in this systemd unit's cgroup. | _own_cgroup_path, _read_cgroup_pids, reap_cgroup, main |
| `channel_directory` | Channel directory -- cached map of reachable channels/contacts per platform. | _load_channel_aliases, _apply_channel_aliases, _normalize_channel_query, _channel_target_name |
| `code_skew` | Detect when the gateway is running stale code after a hot ``git pull``. | _fingerprint, record_boot_fingerprint, _short, detect_code_skew |
| `config` | Gateway configuration management. | Platform, HomeChannel, SessionResetPolicy, ChannelOverride |
| `cwd_placeholder` | Resolve gateway ``terminal.cwd`` placeholder values to ``TERMINAL_CWD``. | _truthy_env, resolve_placeholder_terminal_cwd |
| `dead_targets` | Persistent registry of delivery targets that are confirmed unreachable. | DeadTargetRegistry |
| `delivery` | Delivery routing for cron job outputs and agent responses. | DeliveryTarget, DeliveryRouter |
| `delivery_ledger` | Durable delivery-obligation ledger for gateway final responses. | _db_path, _connect, _owner_stamp, _owner_alive |
| `display_config` | Per-platform display/verbosity configuration resolver. | resolve_display_setting, _normalise |
| `drain_control` | External drain-control marker contract (dashboard → gateway). | current_instantiation_epoch, drain_request_path, write_drain_request, clear_drain_request |
| `hooks` | Event Hook System | HookRegistry |
| `kanban_watchers` | Kanban board watcher methods for GatewayRunner. | GatewayKanbanWatchersMixin |
| `memory_monitor` | Periodic process memory usage logging for the gateway. | _get_rss_mb, log_memory_usage, _monitor_loop, start_memory_monitoring |
| `message_timestamps` | Helpers for rendering gateway message timestamps exactly once. | coerce_message_timestamp, format_message_timestamp, strip_leading_message_timestamps, render_user_content_with_timestamp |
| `mirror` | Session mirroring for cross-platform message delivery. | mirror_to_session, _find_session_id, _append_to_sqlite |
| `pairing` | DM Pairing System | PairingStore |
| `platform_registry` | Platform Adapter Registry | PlatformEntry, PlatformRegistry |
| `profile_routing` | Profile-based routing for the gateway with hierarchical matching. | ProfileRoute |
| `readiness` | Bounded, non-destructive readiness probes for authenticated health surfaces. | _check, _probe_state_db, _probe_config, _probe_disk |
| `response_filters` | Gateway response filtering helpers. | _canonical_silence_candidate, _strip_edge_silence_punctuation, _canonical_silence_candidates, is_intentional_silence_response |
| `restart` | Shared gateway restart constants and supervisor detection helpers. | is_gateway_supervisor_process, parse_restart_drain_timeout |
| `restart_loop_guard` | Auto-resume restart-loop breaker (#30719, defense-3). | _state_path, _load_boots, _save_boots, record_restart_interrupted_boot |
| `rich_sent_store` | Local index of text we've sent via ``sendRichMessage`` (Bot API 10.1). | _store_path, _key, record, lookup |
| `run` | Gateway runner - entry point for messaging platform integrations. | MultiplexConfigError, SecondaryPortBindingConfigError, GatewayRunner |
| `runtime_footer` | Gateway runtime-metadata footer. | _home_relative_cwd, _model_short, resolve_footer_config, format_runtime_footer |
| `scale_to_zero` | Scale-to-zero idle detection + dormant-quiesce for the gateway (Phase 0). | scale_to_zero_enabled, parse_idle_timeout_seconds, messaging_is_relay_only_or_absent, _platform_name |
| `session` | Session management for the gateway. | SessionSource, SessionContext, SessionEntry, _SessionFlight |
| `session_context` | Session-scoped context variables for the Hermes gateway. | session_context_engaged, set_current_session_id, set_session_vars, clear_session_vars |
| `shutdown_forensics` | Shutdown forensics — capture context when the gateway receives SIGTERM/SIGINT. | _signal_name, _read_proc_field, _read_proc_cmdline, _proc_summary |
| `shutdown_watchdog` | Out-of-loop shutdown backstop + event-loop liveness heartbeat (#66892). | _process_hermes_home, get_loop_heartbeat_path, get_shutdown_watchdog_dump_path, write_loop_heartbeat |
| `slash_access` | Per-platform slash command access control. | SlashAccessPolicy |
| `slash_commands` | Gateway slash-command handlers for GatewayRunner. | GatewaySlashCommandsMixin |
| `status` | Gateway runtime status helpers. | StormInfo |
| `status_phrases` | Human-friendly generic gateway status phrases. | _clean_phrase_list, _merge_phrase_mapping, _merge_phrase_file, _relative_path_under |
| `sticker_cache` | Sticker description cache for Telegram. | _load_cache, _save_cache, get_cached_description, cache_sticker_description |
| `stream_consumer` | Gateway streaming consumer — bridges sync agent callbacks to async platform delivery. | StreamConsumerConfig, GatewayStreamConsumer |
| `stream_dispatch` | Adapter-driven dispatch of structured stream events to a delivery sink. | GatewayEventDispatcher |
| `stream_events` | Structured streaming events — the agent→gateway delivery contract. | MessageChunk, MessageStop, Commentary, ToolCallChunk |
| `systemd_notify` | Minimal, optional systemd ``sd_notify`` support for the gateway. | SystemdWatchdog |
| `turn_lease` | Per-session turn lease — serializes the [load history → run → flush] region. | TurnLeaseToken, _SessionLease, SessionTurnLeaseRegistry |
| `whatsapp_identity` | Shared helpers for canonicalising WhatsApp sender identity. | normalize_whatsapp_identifier, to_whatsapp_jid, expand_whatsapp_aliases, canonical_whatsapp_identifier |

### 1.2 `gateway.platforms`（18 个）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `gateway.platforms._http_client_limits` | Shared HTTP client factory for long-lived platform adapters. | platform_httpx_limits |
| `gateway.platforms.api_server` | OpenAI-compatible API server platform adapter. | ResponseStore, _IdempotencyCache, APIServerAdapter |
| `gateway.platforms.base` | Base platform adapter interface. | CachedMedia, MessageType, ProcessingOutcome, MessageEvent |
| `gateway.platforms.bluebubbles` | BlueBubbles iMessage platform adapter. | BlueBubblesAdapter |
| `gateway.platforms.helpers` | Shared helper classes for gateway platform adapters. | MessageDeduplicator, TextBatchAggregator, ThreadParticipationTracker |
| `gateway.platforms.msgraph_webhook` | Microsoft Graph webhook adapter for change-notification ingress. | MSGraphWebhookAdapter |
| `gateway.platforms.signal` | Signal messenger platform adapter. | SignalAdapter |
| `gateway.platforms.signal_format` | Shared Signal formatting helpers. | markdown_to_signal |
| `gateway.platforms.signal_rate_limit` | Signal attachment rate-limit scheduler. | SignalRateLimitError, SignalSchedulerError, SignalAttachmentScheduler |
| `gateway.platforms.webhook` | Generic webhook platform adapter. | WebhookAdapter |
| `gateway.platforms.webhook_filters` | Route-local filters and script transforms for the webhook adapter. | WebhookRouteProcessor |
| `gateway.platforms.weixin` | Weixin platform adapter. | ContextTokenStore, TypingTicketCache, WeixinAdapter |
| `gateway.platforms.whatsapp_cloud` | WhatsApp Cloud API adapter — official Meta WhatsApp Business Platform. | WhatsAppCloudAdapter |
| `gateway.platforms.whatsapp_common` | Transport-agnostic WhatsApp behavior shared by the Baileys bridge adapter | WhatsAppBehaviorMixin |
| `gateway.platforms.yuanbao` | Yuanbao platform adapter. | MarkdownProcessor, SignManager, InboundContext, InboundMiddleware |
| `gateway.platforms.yuanbao_media` | yuanbao_media.py — 元宝平台媒体处理模块 | guess_mime_type, is_image, get_image_format, md5_hex |
| `gateway.platforms.yuanbao_proto` | yuanbao_proto.py - Yuanbao WebSocket 协议编解码（纯 Python 实现） | _dbg, next_seq_no, _encode_varint, _decode_varint |
| `gateway.platforms.yuanbao_sticker` | Yuanbao sticker (TIMFaceElem) support. | get_sticker_by_name, get_random_sticker, get_sticker_by_id, _normalize_text |

### 1.3 `gateway.platforms.qqbot`（7 个）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `gateway.platforms.qqbot.adapter` | QQ Bot platform adapter using the Official QQ Bot API (v2). | QQCloseError, QQAdapter |
| `gateway.platforms.qqbot.chunked_upload` | QQ Bot chunked upload flow. | UploadDailyLimitExceededError, UploadFileTooLargeError, _UploadProgress, _PreparePart |
| `gateway.platforms.qqbot.constants` | QQBot package-level constants shared across adapter, onboard, and other modules. | — |
| `gateway.platforms.qqbot.crypto` | AES-256-GCM utilities for QQBot scan-to-configure credential decryption. | generate_bind_key, decrypt_secret |
| `gateway.platforms.qqbot.keyboards` | QQ Bot inline keyboards + approval / update-prompt senders. | KeyboardButtonPermission, KeyboardButtonAction, KeyboardButtonRenderData, KeyboardButton |
| `gateway.platforms.qqbot.onboard` | QQBot scan-to-configure (QR code onboard) module. | BindStatus |
| `gateway.platforms.qqbot.utils` | QQBot shared utilities — User-Agent, HTTP helpers, config coercion. | _get_hermes_version, build_user_agent, get_api_headers, coerce_list |

### 1.4 `gateway.relay`（5 个，EXPERIMENTAL）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `gateway.relay.adapter` | RelayAdapter — one generic gateway adapter fronted by the connector. EXPERIMENTAL. | RelayAdapter |
| `gateway.relay.auth` | Gateway-side relay authentication primitives. EXPERIMENTAL. | _hmac_hex, sign, verify_signature, make_token |
| `gateway.relay.descriptor` | CapabilityDescriptor — the relay handshake payload. EXPERIMENTAL. | CapabilityDescriptor |
| `gateway.relay.transport` | Relay transport protocol — the gateway<->connector wire contract. EXPERIMENTAL. | RelayTransport |
| `gateway.relay.ws_transport` | Production WebSocket RelayTransport — the gateway's live link to the connector. | PassthroughForward, WebSocketRelayTransport |

### 1.5 `gateway.builtin_hooks`（1 个）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `gateway.builtin_hooks` | Built-in gateway hooks that are always registered.（内置钩子，恒注册） | — |

## 2. 平台适配器真面目（双轨：内置核心 + 插件平台）

> **0.19.0 网关平台适配器是「双轨」架构**，不要只看 `gateway/platforms/`（内置核心）。
> **插件平台在 `plugins/platforms/*`**（每个 `adapter.py + plugin.yaml`，`kind: platform`）；`hermes_cli/gateway.py` 明确「Bundled platform plugins auto-load unconditionally」（无条件自动加载），
> 且 `gateway/run.py _create_adapter()` **先查 `platform_registry`（插件优先），再回退内置 legacy if/elif**。
> 官方 `Platform` 枚举（`gateway/config.py`）显式声明 telegram/discord/whatsapp/slack/matrix/mattermost/homeassistant/email/sms/dingtalk/feishu/wecom 等成员，
> 其余插件平台（irc/line/simplex/photon/google_chat/raft/ntfy/teams）经 `_scan_bundled_plugin_platforms()` 扫描 `plugins/platforms/*/plugin.yaml` 动态注册。
> 因此 **Telegram / Slack / 飞书 / 企微 / 钉钉 / Discord / Matrix / SMS / Email 等均为受支持平台**，只是走插件适配器（而非 `gateway/platforms` 内置）。

### 2.1 内置核心平台（`gateway/run.py _create_adapter` legacy 分支，9 个，代码在 `gateway/platforms/*`）

| 平台 | 实现模块 | 备注 |
| --- | --- | --- |
| QQ（Bot API v2） | `gateway/platforms/qqbot/*` | 内置核心 |
| Signal | `gateway/platforms/signal.py` + `signal_format` + `signal_rate_limit` | 内置核心 |
| Webhook | `gateway/platforms/webhook.py` + `webhook_filters` | 内置核心 |
| 微信（个人账号，腾讯 iLink Bot API） | `gateway/platforms/weixin.py` | 内置核心 |
| WhatsApp Cloud API | `gateway/platforms/whatsapp_cloud.py` + `whatsapp_common` + 顶层 `whatsapp_identity` | 内置核心（Meta 官方） |
| 元宝（Yuanbao） | `gateway/platforms/yuanbao.py` + `yuanbao_media`/`yuanbao_proto`/`yuanbao_sticker` | 内置核心（WebSocket） |
| BlueBubbles（iMessage） | `gateway/platforms/bluebubbles.py` | 内置核心 |
| Microsoft Graph webhook | `gateway/platforms/msgraph_webhook.py` | 内置核心 |
| OpenAI 兼容 API Server | `gateway/platforms/api_server.py` | 网关 `/v1` 层（见 `15`） |

### 2.2 插件平台（`plugins/platforms/*`，20 个，`adapter.py + plugin.yaml`，`kind: platform`，无条件自动加载）

| 平台 | 插件目录 | 典型所需凭据 |
| --- | --- | --- |
| Telegram | `plugins/platforms/telegram` | `TELEGRAM_BOT_TOKEN` |
| Slack | `plugins/platforms/slack` | `SLACK_*` |
| Discord | `plugins/platforms/discord` | `DISCORD_*` |
| 飞书 / Lark | `plugins/platforms/feishu` | `FEISHU_*` |
| 企业微信 WeCom | `plugins/platforms/wecom`（含 `wecom_callback`） | `WECOM_*` |
| 钉钉 DingTalk | `plugins/platforms/dingtalk` | `DINGTALK_*` |
| Matrix | `plugins/platforms/matrix` | `MATRIX_*` |
| SMS（Twilio） | `plugins/platforms/sms` | Twilio `SMS_*` |
| Email | `plugins/platforms/email` | SMTP `EMAIL_*` |
| WhatsApp | `plugins/platforms/whatsapp` | `WHATSAPP_*` |
| Google Chat | `plugins/platforms/google_chat` | `GOOGLE_CHAT_*` |
| Home Assistant | `plugins/platforms/homeassistant` | `HOMEASSISTANT_*` |
| IRC | `plugins/platforms/irc` | `IRC_SERVER` 等 |
| LINE | `plugins/platforms/line` | `LINE_*` |
| Mattermost | `plugins/platforms/mattermost` | `MATTERMOST_*` |
| Microsoft Teams | `plugins/platforms/teams` | `TEAMS_*` |
| iMessage（Photon） | `plugins/platforms/photon` | `PHOTON_*` |
| SimpleX Chat | `plugins/platforms/simplex` | `SIMPLEX_*` |
| Raft | `plugins/platforms/raft` | `RAFT_*` |
| ntfy | `plugins/platforms/ntfy` | `NTFY_*` |

### 2.3 结论（对本文档集既有表述的纠偏）
- **`10` §1.2 / `02` §4 / `14` §2.1 称「网关把 Telegram/Slack/QQ/飞书等喂给 Agent」方向正确**——这些平台确实被网关支持；
  精确说，**Telegram/Slack/飞书/企微/钉钉/Discord/Matrix/SMS/Email 走 `plugins/platforms` 插件适配器**，`QQ` 等走 `gateway/platforms` 内置核心。
- 早期稿把 telegram/slack 归为「CLI 侧」、把 feishu/wecom/discord/matrix/sms/email 称为「无实现」——**不准确，已按 0.19.0 源码更正**。
  这些平台在 `plugins/platforms/*/adapter.py` 均有完整实现，并被 `Platform` 枚举 / 插件扫描注册为网关平台。
- 同一平台可能两处都有（如 WhatsApp：内置 `whatsapp_cloud` + 插件 `whatsapp`）——**插件注册优先**（`_create_adapter` 先查 registry）。

## 3. 与本文档集其他篇目关系

| 主题 | 归属文件 | 本文 role |
| --- | --- | --- |
| 网关/CLI/API Server 形态的启动命令入口 | `10-hermes-cli.md` §2.5（`hermes_cli.gateway`） | 命令入口（本文是实现） |
| API Server 如何用 / 端点 / 认证 / 进程内自建 | `15-api-server.md` | 能力语义（本文仅列 `api_server` 模块） |
| 网关为什么进程内不起 / Library 全貌收口 | `14-library-infra.md` §0/§3 | 取舍结论（本文是包内枚举） |
| 能力→模块地图（含 hermes-* 平台归属） | `02-integration-core.md` §4 | 映射（本文 §2 提供 0.19.0 实证） |
| 57 工具集 / 平台工具集行为 | `03-capabilities-and-toolsets.md` | 能力行为（本文不列） |
| `tools` / `agent` 包全量枚举 | `12` / `13` | 不同包（工具实现 / 运行时内核） |
| 红线/门禁 | `07-quality-gates.md` | 权威红线（本文仅引用） |

> 本文只负责「`gateway` 包模块的存在性 / 用途 / 代表 API」这一层；能力行为、工具集、网关形态的取舍结论均指向对应篇目，不重复。

## 4. 全文检索索引（网关 / API Server 视角）

| 你想确认的事 | 看本文哪个小节 |
| --- | --- |
| `gateway` 包一共有哪些模块 / 网关运行时构成 | §1 |
| 0.19.0 网关实际承载哪些平台 | §2 |
| API Server 那层在 gateway 包里是哪个文件 | §1.2（`platforms/api_server.py`，详见 `15`） |
| QQ / Signal / WhatsApp / 元宝 / 微信 的适配器在哪 | §1.2–§1.3 / §2 |
| 实验性中继（relay）是什么 | §1.4 |
| 内置钩子在哪 | §1.5 |
| 网关形态为什么进程内不起 | `14-library-infra.md` §0/§2.1（本文不重复） |
