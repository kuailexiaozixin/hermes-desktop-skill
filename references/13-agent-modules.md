# 13 · `agent` 包参考（Hermes 运行时内核，0.19.0：全量模块枚举 + 六项深度主题）

> 本文件是 `agent` 包的**完整、逐模块枚举**。经 `hermes-agent==0.19.0` 已装包**逐模块 import + 读取 docstring + 提取公开 API** 核实；
> 全部 155 个嵌套子模块无一遗漏（含 `lsp.*` / `pet.*` / `secret_sources.*` / `transports.*` 等子包）。
>
> **「agent 包」是什么**：`agent` 是 Hermes 的**运行时内核**——对话循环、各 LLM 厂商适配（OpenAI/Anthropic/Bedrock/Gemini/Codex/Vertex）、
> 上下文压缩、记忆、凭证池、计费、传输层等都在这里。你的桌面应用通过 `run_agent.AIAgent`（见 `01`）间接驱动它，
> **一般不直接 import `agent.*`**（那是 AIAgent 的内部实现）。本文的价值是「让你知道内核由哪些模块构成、出了问题时去哪查」，
> 而不是让你逐文件 import。
>
> **与 01 的边界**：`01-library-api.md` 讲「`AIAgent` 的公开构造参数 / 15 个回调 / SSE 词汇」这一**对外接口**；
> 本文讲「`agent` 包内部有哪些模块、各自干什么」。接口用 `01`，内部构成查本文。
>
> **与 08 的边界**：`08-capability-integration.md` 讲「Goals/Snapshots/MOA/Projects 等能力在进程内怎么用」；
> 本文仅列 `agent` 包模块定位，能力实战去 `08`。

## 0. 模块分类图例（针对 `agent` 包）

| 标记 | 含义 |
| --- | --- |
| **内核·运行时** | 对话循环/适配器/压缩/记忆/凭证等核心运行时，由 `AIAgent` 内部驱动 |
| **内核·传输** | LLM 厂商传输层（`transports.*`：OpenAI/Anthropic/Bedrock/Codex/Hermes MCP Server 等） |
| **内核·LSP** | 语言服务器协议支持（`lsp.*`） |
| **内核·Pet** | 桌面宠物渲染/生成（`pet.*`） |
| **内核·密钥** | 密钥来源抽象（`secret_sources.*`） |

> ⛔ 红线（与 `07`/`10` 一致）：桌面应用**不要直接 import `agent.*` 内部模块**去复刻对话循环；
> 一律走 `run_agent.AIAgent` 的公开接口（见 `01`）。本文仅供「结构认知 + 排障定位」，不构成 import 指引。

## 1. 全量模块清单（155 个，按子包/顶层分组，不交叉不重合）

> 每行：模块 | 真实用途（取自 0.19.0 docstring）| 分类 | 代表公开 API（仅列真实存在者）。

### 1.1 (top)（120 个）

| 模块 | 用途 | 分类 | 代表 API |
| --- | --- | --- | --- |
| `agent.account_usage` | (无 docstring) | 内核·运行时 | AccountUsageSnapshot, AccountUsageWindow, CodexResetRedeemResult, CreditsView, build_credits_view, build_nous_credits_snapshot |
| `agent.agent_init` | Implementation of :meth:`AIAgent.__init__` — extracted as a module function. | 内核·运行时 | init_agent |
| `agent.agent_runtime_helpers` | Assorted AIAgent runtime helpers — moved out of run_agent.py for clarity. | 内核·运行时 | agent_runtime_owns_post_tool_hook, anthropic_prompt_cache_policy, apply_pending_steer_to_tool_results, cleanup_dead_connections, convert_to_trajectory_format, copy_reasoning_content_for_api |
| `agent.anthropic_adapter` | Anthropic Messages API adapter for Hermes Agent. | 内核·运行时 | build_anthropic_bedrock_client, build_anthropic_client, build_anthropic_kwargs, convert_messages_to_anthropic, convert_tools_to_anthropic, create_anthropic_message |
| `agent.async_utils` | Async/sync bridging helpers. | 内核·运行时 | consume_detached_task_result, safe_schedule_threadsafe |
| `agent.aux_accounting` | Ambient session-accounting context for auxiliary LLM calls. | 内核·运行时 | get_accounting_context, record_aux_usage, reset_accounting_context, set_accounting_context |
| `agent.auxiliary_client` | Shared auxiliary client router for side tasks. | 内核·运行时 | AnthropicAuxiliaryClient, AsyncAnthropicAuxiliaryClient, AsyncBedrockAuxiliaryClient, AsyncCodexAuxiliaryClient, BedrockAuxiliaryClient, CodexAuxiliaryClient |
| `agent.azure_identity_adapter` | Microsoft Entra ID adapter for Microsoft Foundry. | 内核·运行时 | EntraIdentityConfig, build_bearer_http_client, build_token_provider, describe_active_credential, has_azure_identity_credentials, has_azure_identity_installed |
| `agent.background_review` | Background memory/skill review — fork the agent to evaluate the turn. | 内核·运行时 | build_memory_write_metadata, spawn_background_review_thread, summarize_background_review_actions |
| `agent.bedrock_adapter` | AWS Bedrock Converse API adapter for Hermes Agent. | 内核·运行时 | bedrock_model_ids_or_none, build_converse_kwargs, call_converse, call_converse_stream, classify_bedrock_error, convert_messages_to_converse |
| `agent.billing_usage` | Shared dollar-denominated usage model for the billing/subscription surfaces. | 内核·运行时 | UsageBar, UsageModel, build_usage_model, format_renews, usage_model_from_account |
| `agent.billing_view` | Surface-agnostic core for the Phase 2b terminal-billing screens. | 内核·运行时 | AmountValidation, AutoReload, AutoReloadCard, BillingState, CardInfo, MonthlyCap |
| `agent.bounded_response` | Bounded reads of HTTP error response bodies. | 内核·运行时 | read_error_body_or_default, read_streaming_error_body |
| `agent.browser_provider` | Browser Provider ABC ==================== | 内核·运行时 | BrowserProvider |
| `agent.browser_registry` | Browser Provider Registry ========================= | 内核·运行时 | get_provider, list_providers, register_provider |
| `agent.chat_completion_helpers` | Helper functions for the chat-completions code path. | 内核·运行时 | build_api_kwargs, build_assistant_message, cleanup_task_resources, direct_api_call, estimate_request_context_tokens, handle_max_iterations |
| `agent.codex_responses_adapter` | Codex Responses API adapter. | 内核·运行时 | — |
| `agent.codex_runtime` | Codex API runtime — App Server and Responses-API streaming paths. | 内核·运行时 | make_codex_app_server_event_bridge, run_codex_app_server_turn, run_codex_create_stream_fallback, run_codex_stream |
| `agent.coding_context` | Coding-context awareness — base Hermes, every interactive surface. | 内核·运行时 | ContextProfile, ProjectFacts, RuntimeMode, build_coding_workspace_block, coding_compact_skill_categories, coding_selection |
| `agent.context_breakdown` | Live session context-window breakdown for UI surfaces. | 内核·运行时 | compute_session_context_breakdown |
| `agent.context_compressor` | Automatic context window compression for long conversations. | 内核·运行时 | ContextCompressor |
| `agent.context_engine` | Abstract base class for pluggable context engines. | 内核·运行时 | ContextEngine, sanitize_memory_context |
| `agent.context_references` | (无 docstring) | 内核·运行时 | ContextReference, ContextReferenceResult, parse_context_references, preprocess_context_references, preprocess_context_references_async |
| `agent.conversation_compression` | Context compression — extract the AIAgent methods that drive summarisation. | 内核·运行时 | check_compression_model_feasibility, compress_context, conversation_history_after_compression, replay_compression_warning, try_shrink_image_parts_in_messages |
| `agent.conversation_loop` | The agent conversation loop — extracted from ``run_agent.AIAgent``. | 内核·运行时 | run_conversation |
| `agent.copilot_acp_client` | OpenAI-compatible shim that forwards Hermes requests to `copilot --acp`. | 内核·运行时 | CopilotACPClient |
| `agent.credential_persistence` | Credential-pool disk-boundary sanitization helpers. | 内核·运行时 | is_borrowed_credential_source, sanitize_borrowed_credential_payload |
| `agent.credential_pool` | Persistent multi-credential pool for same-provider failover. | 内核·运行时 | CredentialPool, PooledCredential, credential_pool_matches_provider, get_custom_provider_pool_key, get_pool_strategy, label_from_token |
| `agent.credential_sources` | Unified removal contract for every credential source Hermes reads from. | 内核·运行时 | RemovalResult, RemovalStep, find_removal_step, register |
| `agent.credits_tracker` | Credits tracking for Nous inference API responses. | 内核·运行时 | AgentNotice, CreditsState, dev_fixture_credits_state, evaluate_credits_notices, is_free_tier_model, parse_credits_headers |
| `agent.curator` | Curator — background skill maintenance orchestrator. | 内核·运行时 | apply_automatic_transitions, get_archive_after_days, get_consolidate, get_interval_hours, get_min_idle_hours, get_prune_builtins |
| `agent.curator_backup` | Curator snapshot + rollback. | 内核·运行时 | format_size, get_keep, is_enabled, list_backups, rollback, snapshot_skills |
| `agent.display` | CLI presentation -- spinner, kawaii faces, tool preview formatting. | 内核·运行时 | KawaiiSpinner, LocalEditSnapshot, build_status_phrase, build_tool_label, build_tool_preview, capture_local_edit_snapshot |
| `agent.error_classifier` | API error classification for smart failover and recovery. | 内核·运行时 | ClassifiedError, FailoverReason, classify_api_error |
| `agent.errors` | (无 docstring) | 内核·运行时 | EmptyStreamError, MoAPresetNotFoundError, SSLConfigurationError |
| `agent.file_safety` | Shared file safety rules used by both tools and ACP shims. | 内核·运行时 | build_write_denied_paths, build_write_denied_prefixes, classify_container_mirror_target, classify_cross_profile_target, classify_sandbox_mirror_target, get_container_mirror_warning |
| `agent.gemini_native_adapter` | OpenAI-compatible facade over Google AI Studio's native Gemini API. | 内核·运行时 | AsyncGeminiNativeClient, GeminiAPIError, GeminiNativeClient, bare_gemini_model_id, build_gemini_request, gemini_http_error |
| `agent.gemini_schema` | Helpers for translating OpenAI-style tool schemas to Gemini's schema subset. | 内核·运行时 | sanitize_gemini_schema, sanitize_gemini_tool_parameters |
| `agent.i18n` | Lightweight internationalization (i18n) for Hermes static user-facing messages. | 内核·运行时 | get_language, reset_language_cache, t |
| `agent.image_gen_provider` | Image Generation Provider ABC ============================= | 内核·运行时 | ImageGenProvider, error_response, normalize_reference_images, resolve_aspect_ratio, save_b64_image, save_url_image |
| `agent.image_gen_registry` | Image Generation Provider Registry ================================== | 内核·运行时 | get_active_provider, get_provider, list_providers, register_provider |
| `agent.image_routing` | Routing helpers for inbound user-attached images. | 内核·运行时 | build_native_content_parts, decide_image_input_mode, extract_image_refs |
| `agent.insights` | Session Insights Engine for Hermes Agent. | 内核·运行时 | InsightsEngine |
| `agent.iteration_budget` | Per-agent iteration budget — thread-safe consume/refund counter. | 内核·运行时 | IterationBudget |
| `agent.jiter_preload` | Best-effort early import for the OpenAI SDK's native streaming parser. | 内核·运行时 | preload_jiter_native_extension |
| `agent.kanban_stop` | Turn-end guard for kanban workers. | 内核·运行时 | build_kanban_stop_nudge, kanban_stop_nudge_enabled, session_called_kanban_terminal |
| `agent.learn_prompt` | ``/learn`` — build the standards-guided prompt that turns whatever the user described into a reusable skill. | 内核·运行时 | build_learn_prompt |
| `agent.learning_graph` | Assemble the "learning made visible" graph for desktop. | 内核·运行时 | SkillNode, build_edges, build_learning_graph, build_skill_nodes, density_stats |
| `agent.learning_graph_render` | Terminal renderer for the learning timeline (learned skills + memories). | 内核·运行时 | axis_labels, build_legend, build_summary, category_color_map, category_legend, compute_recency |
| `agent.learning_mutations` | User-initiated edit/delete for journey nodes (learned skills + memories). | 内核·运行时 | delete_node, edit_node, node_detail, parse_node_kind |
| `agent.lmstudio_reasoning` | LM Studio reasoning-effort resolution shared by the chat-completions transport and run_agent's iteration-limit summary path. | 内核·运行时 | resolve_lmstudio_effort |
| `agent.lsp` | Language Server Protocol (LSP) integration for Hermes Agent. | 内核·LSP | get_service, shutdown_service |
| `agent.manual_compression_feedback` | User-facing summaries for manual compression commands. | 内核·运行时 | summarize_manual_compression |
| `agent.markdown_tables` | CJK/wide-character-aware re-alignment of model-emitted markdown tables. | 内核·运行时 | is_table_divider, looks_like_table_row, realign_markdown_tables, split_table_row |
| `agent.memory_manager` | MemoryManager — orchestrates memory providers for the agent. | 内核·运行时 | MemoryManager, StreamingContextScrubber, build_memory_context_block, inject_memory_provider_tools, memory_provider_tools_enabled, normalize_tool_schema |
| `agent.memory_provider` | Abstract base class for pluggable memory providers. | 内核·运行时 | MemoryProvider |
| `agent.message_content` | (无 docstring) | 内核·运行时 | flatten_message_text |
| `agent.message_sanitization` | Message and tool-payload sanitization helpers. | 内核·运行时 | close_interrupted_tool_sequence |
| `agent.moa_loop` | Mixture-of-Agents runtime helpers for /moa turns. | 内核·运行时 | MoAChatCompletions, MoAClient, aggregate_moa_context |
| `agent.moa_trace` | Full MoA turn trace persistence (opt-in via config ``moa.save_traces``). | 内核·运行时 | save_moa_turn |
| `agent.model_metadata` | Model metadata, context lengths, and token estimation utilities. | 内核·运行时 | detect_local_server_type, estimate_messages_tokens_rough, estimate_request_tokens_rough, estimate_tokens_rough, fetch_endpoint_model_metadata, fetch_model_metadata |
| `agent.models_dev` | Models.dev registry integration — primary database for providers and models. | 内核·运行时 | ModelCapabilities, ModelInfo, ProviderInfo, fetch_models_dev, get_model_capabilities, get_model_info |
| `agent.moonshot_schema` | Helpers for translating OpenAI-style tool schemas to Moonshot's schema subset. | 内核·运行时 | is_moonshot_model, sanitize_moonshot_tool_parameters, sanitize_moonshot_tools |
| `agent.nous_rate_guard` | Cross-session rate limit guard for Nous Portal. | 内核·运行时 | clear_nous_rate_limit, format_remaining, is_genuine_nous_rate_limit, nous_rate_limit_remaining, record_nous_rate_limit |
| `agent.onboarding` | Contextual first-touch onboarding hints. | 内核·运行时 | busy_input_hint_cli, busy_input_hint_gateway, detect_openclaw_residue, is_seen, mark_seen, openclaw_residue_hint_cli |
| `agent.oneshot` | Shared one-off LLM requests for non-conversational helpers. | 内核·运行时 | render_template, run_oneshot |
| `agent.pet` | Petdex pet engine — shared core for the CLI, TUI, and desktop surfaces. | 内核·Pet | — |
| `agent.plugin_llm` | Plugin LLM facade — host-owned LLM access for trusted plugins. ============================================================== | 内核·运行时 | PluginLlm, PluginLlmCompleteResult, PluginLlmImageInput, PluginLlmStructuredResult, PluginLlmTextInput, PluginLlmTrustError |
| `agent.portal_tags` | Centralized Nous Portal request tags. | 内核·运行时 | conversation_tag, get_conversation_context, hermes_client_tag, nous_portal_tags, reset_conversation_context, set_conversation_context |
| `agent.process_bootstrap` | Process-level bootstrap helpers for ``run_agent``. | 内核·运行时 | build_keepalive_http_client |
| `agent.prompt_builder` | System prompt assembly -- identity, platform hints, skills index, context files. | 内核·运行时 | build_context_files_prompt, build_environment_hints, build_nous_subscription_prompt, build_skills_system_prompt, clear_skills_system_prompt_cache, computer_use_guidance |
| `agent.prompt_caching` | Anthropic prompt caching strategy. | 内核·运行时 | apply_anthropic_cache_control |
| `agent.rate_limit_tracker` | Rate limit tracking for inference API responses. | 内核·运行时 | RateLimitBucket, RateLimitState, format_rate_limit_compact, format_rate_limit_display, parse_rate_limit_headers |
| `agent.reactions` | Token-free detection of user *reactions* to the agent. | 内核·运行时 | detect_reaction |
| `agent.reasoning_timeouts` | Per-reasoning-model stale-timeout floor for known reasoning models. | 内核·运行时 | get_reasoning_stale_timeout_floor |
| `agent.redact` | Regex-based secret redaction for logs and tool output. | 内核·运行时 | RedactingFormatter, is_env_dump_command, mask_secret, redact_cdp_url, redact_sensitive_text, redact_terminal_output |
| `agent.replay_cleanup` | Replay-history sanitization shared across resume code paths. | 内核·运行时 | is_dangerous_confirmation, is_interrupted_tool_result, sanitize_replay_history, strip_dangling_tool_call_tail, strip_interrupted_tool_tails, strip_stale_dangerous_confirmations |
| `agent.retry_utils` | Retry utilities — jittered backoff for decorrelated retries. | 内核·运行时 | adaptive_rate_limit_backoff, is_zai_coding_overload_error, jittered_backoff, zai_coding_overload_retry_ceiling |
| `agent.runtime_cwd` | Single source of truth for the agent working directory. | 内核·运行时 | clear_session_cwd, resolve_agent_cwd, resolve_context_cwd, set_session_cwd |
| `agent.secret_scope` | Profile-scoped credential resolution for multi-profile gateway multiplexing. | 内核·运行时 | UnscopedSecretError, build_profile_secret_scope, current_secret_scope, get_secret, is_multiplex_active, load_env_file |
| `agent.secret_sources` | External secret source integrations. | 内核·密钥 | — |
| `agent.shell_hooks` | Shell-script hooks bridge. | 内核·运行时 | ShellHookSpec, allowlist_entry_for, allowlist_path, iter_configured_hooks, load_allowlist, register_from_config |
| `agent.skill_bundles` | Skill bundles — aliases that load multiple skills under one slash command. | 内核·运行时 | build_bundle_invocation_message, bundle_path_for, delete_bundle, get_bundle, get_skill_bundles, list_bundles |
| `agent.skill_commands` | Shared slash command helpers for skills. | 内核·运行时 | build_preloaded_skills_prompt, build_skill_invocation_message, build_stacked_skill_invocation_message, extract_user_instruction_from_skill_message, get_skill_commands, reload_skills |
| `agent.skill_preprocessing` | Shared SKILL.md preprocessing helpers. | 内核·运行时 | expand_inline_shell, load_skills_config, preprocess_skill_content, run_inline_shell, substitute_template_vars |
| `agent.skill_utils` | Lightweight skill metadata utilities shared by prompt_builder and skills_tool. | 内核·运行时 | discover_all_skill_config_vars, extract_skill_conditions, extract_skill_config_vars, extract_skill_description, get_all_skills_dirs, get_disabled_skill_names |
| `agent.ssl_guard` | Preventive SSL CA certificate checks for Hermes Agent. | 内核·运行时 | verify_ca_bundle, verify_ca_bundle_with_fallback |
| `agent.ssl_verify` | TLS verify resolution for httpx/OpenAI provider clients. | 内核·运行时 | resolve_httpx_verify |
| `agent.stream_diag` | Stream diagnostics — per-attempt counters, exception chains, retry logging. | 内核·运行时 | emit_stream_drop, flatten_exception_chain, log_stream_retry, stream_diag_capture_response, stream_diag_init |
| `agent.stream_single_writer` | Best-effort accessors for the single-writer stream fence (#65991). | 内核·运行时 | claim_stream_writer, stream_writer_is_current |
| `agent.subdirectory_hints` | Progressive subdirectory hint discovery. | 内核·运行时 | SubdirectoryHintTracker |
| `agent.subscription_view` | Surface-agnostic core for the ``/subscription`` TUI screen. | 内核·运行时 | CurrentSubscription, SubscriptionChangePreview, SubscriptionState, SubscriptionTier, build_subscription_state, dev_fixture_subscription_state |
| `agent.system_prompt` | System-prompt assembly for :class:`AIAgent`. | 内核·运行时 | build_system_prompt, build_system_prompt_parts, format_tools_for_system_message, invalidate_system_prompt |
| `agent.think_scrubber` | Stateful scrubber for reasoning/thinking blocks in streamed assistant text. | 内核·运行时 | StreamingThinkScrubber |
| `agent.thinking_timeout_guidance` | Thinking-timeout detection and user-facing guidance for reasoning models. | 内核·运行时 | build_thinking_timeout_guidance, is_thinking_timeout |
| `agent.thread_scoped_output` | Thread-scoped stdout/stderr silencing for background worker threads. | 内核·运行时 | thread_scoped_silence |
| `agent.title_generator` | Auto-generate short session titles from the first user/assistant exchange. | 内核·运行时 | auto_title_session, generate_title, maybe_auto_title |
| `agent.tool_dispatch_helpers` | Tool-dispatch helpers — parallelism gating, multimodal envelopes, mutation tracking. | 内核·运行时 | make_tool_result_message |
| `agent.tool_executor` | Tool-call execution — sequential and concurrent dispatch. | 内核·运行时 | execute_tool_calls_concurrent, execute_tool_calls_segmented, execute_tool_calls_sequential |
| `agent.tool_guardrails` | Pure tool-call loop guardrail primitives. | 内核·运行时 | ToolCallGuardrailConfig, ToolCallGuardrailController, ToolCallSignature, ToolGuardrailDecision, append_toolguard_guidance, canonical_tool_args |
| `agent.tool_result_classification` | Shared helpers for classifying tool result payloads. | 内核·运行时 | file_mutation_result_landed, tool_may_have_side_effect |
| `agent.trace_upload` | Upload a Hermes session transcript to Hugging Face as an agent trace. | 内核·运行时 | TraceRedactionError, build_trace_jsonl, load_session_messages, upload_session_trace |
| `agent.trajectory` | Trajectory saving utilities and static helpers. | 内核·运行时 | convert_scratchpad_to_think, has_incomplete_scratchpad, save_trajectory |
| `agent.transcription_provider` | Transcription Provider ABC ========================== | 内核·运行时 | TranscriptionProvider |
| `agent.transcription_registry` | Transcription Provider Registry ================================ | 内核·运行时 | get_provider, list_providers, register_provider |
| `agent.transports` | Transport layer types and registry for provider response normalization. | 内核·传输 | get_transport, register_transport |
| `agent.tts_provider` | Text-to-Speech Provider ABC ============================ | 内核·运行时 | TTSProvider, resolve_output_format |
| `agent.tts_registry` | TTS Provider Registry ===================== | 内核·运行时 | get_provider, list_providers, register_provider |
| `agent.turn_context` | Per-turn setup for ``run_conversation`` (the turn prologue). | 内核·运行时 | TurnContext, append_notes_to_multimodal_content, build_turn_context, compose_user_api_content, consume_gateway_turn_context_notes, drop_stale_api_content |
| `agent.turn_finalizer` | Post-loop turn finalization for ``run_conversation``. | 内核·运行时 | finalize_turn |
| `agent.turn_retry_state` | Per-attempt recovery bookkeeping for the conversation turn loop. | 内核·运行时 | TurnRetryState |
| `agent.usage_pricing` | (无 docstring) | 内核·运行时 | BillingRoute, CanonicalUsage, CostResult, PricingEntry, estimate_usage_cost, format_duration_compact |
| `agent.verification_evidence` | Coding verification evidence ledger. | 内核·运行时 | VerificationEvidence, classify_verification_command, mark_workspace_edited, record_terminal_result, verification_status |
| `agent.verification_stop` | Turn-end verification guard for coding edits. | 内核·运行时 | build_verify_on_stop_nudge, verify_on_stop_enabled |
| `agent.verify_hooks` | Verification-loop helpers for the ``pre_verify`` round-end gate. | 内核·运行时 | coding_verify_guidance, max_verify_nudges |
| `agent.vertex_adapter` | Vertex AI (Google Cloud) adapter for Hermes Agent. | 内核·运行时 | build_vertex_base_url, get_vertex_config, get_vertex_credentials, has_vertex_credentials |
| `agent.video_gen_provider` | Video Generation Provider ABC ============================= | 内核·运行时 | OpenAICompatibleVideoGenProvider, VideoGenProvider, error_response, save_b64_video, save_bytes_video, save_url_video |
| `agent.video_gen_registry` | Video Generation Provider Registry ================================== | 内核·运行时 | get_active_provider, get_provider, list_providers, register_provider |
| `agent.web_search_provider` | Web Search Provider ABC ======================= | 内核·运行时 | WebSearchProvider, get_provider_env |
| `agent.web_search_registry` | Web Search Provider Registry ============================ | 内核·运行时 | get_active_extract_provider, get_active_search_provider, get_provider, list_providers, register_provider |

### 1.2 agent.lsp.*（10 个）

| 模块 | 用途 | 分类 | 代表 API |
| --- | --- | --- | --- |
| `agent.lsp.cli` | ``hermes lsp`` CLI subcommand. | 内核·LSP | register_subparser, run_lsp_command |
| `agent.lsp.client` | Async LSP client over stdin/stdout. | 内核·LSP | LSPClient, file_uri, uri_to_path |
| `agent.lsp.eventlog` | Structured logging with steady-state silence for the LSP layer. | 内核·LSP | log_active, log_clean, log_diagnostics, log_disabled, log_no_project_root, log_no_server_configured |
| `agent.lsp.install` | Auto-installation of LSP server binaries. | 内核·LSP | detect_status, hermes_lsp_bin_dir, try_install |
| `agent.lsp.manager` | Service-level orchestration for LSP clients. | 内核·LSP | LSPService |
| `agent.lsp.protocol` | Minimal LSP JSON-RPC 2.0 framer over async streams. | 内核·LSP | LSPProtocolError, LSPRequestError, classify_message, encode_message, make_error_response, make_notification |
| `agent.lsp.range_shift` | Diff-aware line-shift map for cross-edit LSP delta filtering. | 内核·LSP | build_line_shift, shift_baseline, shift_diagnostic_range |
| `agent.lsp.reporter` | Format LSP diagnostics for inclusion in tool output. | 内核·LSP | format_diagnostic, report_for_file, truncate |
| `agent.lsp.servers` | Server registry — per-language LSP server definitions. | 内核·LSP | ServerContext, ServerDef, SpawnSpec, find_server_for_file, hermes_lsp_session_dir, language_id_for |
| `agent.lsp.workspace` | Workspace and project-root resolution for LSP. | 内核·LSP | clear_cache, find_git_worktree, is_inside_workspace, nearest_root, normalize_path, resolve_workspace_for_file |

### 1.3 agent.pet.*（10 个）

| 模块 | 用途 | 分类 | 代表 API |
| --- | --- | --- | --- |
| `agent.pet.constants` | Pet sprite geometry + animation-state taxonomy. | 内核·Pet | PetState, clamp_scale, cols_for_scale, resolve_cols, state_aliases_for, state_row_index |
| `agent.pet.generate` | Pet generation — base-draft → hatch pipeline. | 内核·Pet | — |
| `agent.pet.generate.atlas` | Deterministic spritesheet assembly — generated row strips → Hermes atlas. | 内核·Pet | atlas_to_webp_bytes, compose_atlas, extract_strip_frames, mirror_frames, normalize_cells, remove_background |
| `agent.pet.generate.imagegen` | Thin image-generation layer for pet sprites. | 内核·Pet | GenerationError, SpriteProvider, generate, list_sprite_providers, resolve_provider |
| `agent.pet.generate.orchestrate` | Pet generation orchestration — the base-draft → hatch flow. | 内核·Pet | HatchResult, generate_base_drafts, hatch_pet |
| `agent.pet.generate.prompts` | Prompt builders for pet generation. | 内核·Pet | build_base_prompt, build_row_prompt, style_hint |
| `agent.pet.manifest` | Fetch the public petdex manifest. | 内核·Pet | ManifestEntry, ManifestError, clear_cache, fetch_manifest, find_entry, prefetch |
| `agent.pet.render` | Decode a pet spritesheet and encode frames for a terminal. | 内核·Pet | PetRenderer, build_renderer, detect_terminal_graphics, kitty_color_hex, kitty_image_id, kitty_placeholder_rows |
| `agent.pet.state` | Map agent activity → a :class:`PetState`. | 内核·Pet | derive_pet_state, todos_all_done |
| `agent.pet.store` | On-disk pet store — install / list / resolve pets. | 内核·Pet | InstalledPet, PetStoreError, export_pet, install_pet, installed_pets, load_pet |

### 1.4 agent.secret_sources.*（5 个）

| 模块 | 用途 | 分类 | 代表 API |
| --- | --- | --- | --- |
| `agent.secret_sources._cache` | Shared substrate for external secret-source backends. | 内核·密钥 | CachedFetch, DiskCache, resolve_cache_home |
| `agent.secret_sources.base` | Secret-source contract: the ABC every secret backend implements. | 内核·密钥 | ErrorKind, FetchResult, SecretSource, is_valid_env_name, run_secret_cli, scrub_ansi |
| `agent.secret_sources.bitwarden` | Bitwarden Secrets Manager (`bws` CLI) integration. | 内核·密钥 | BitwardenSource, apply_bitwarden_secrets, fetch_bitwarden_secrets, find_bws, install_bws |
| `agent.secret_sources.onepassword` | 1Password (`op` CLI) secret source. | 内核·密钥 | OnePasswordSource, apply_onepassword_secrets, fetch_onepassword_secrets, find_op |
| `agent.secret_sources.registry` | Secret-source registry + apply orchestrator. | 内核·密钥 | AppliedVar, ApplyReport, SourceReport, apply_all, get_source, list_sources |

### 1.5 agent.transports.*（10 个）

| 模块 | 用途 | 分类 | 代表 API |
| --- | --- | --- | --- |
| `agent.transports.anthropic` | Anthropic Messages API transport. | 内核·传输 | AnthropicTransport |
| `agent.transports.base` | Abstract base for provider transports. | 内核·传输 | ProviderTransport |
| `agent.transports.bedrock` | AWS Bedrock Converse API transport. | 内核·传输 | BedrockTransport |
| `agent.transports.chat_completions` | OpenAI Chat Completions transport. | 内核·传输 | ChatCompletionsTransport |
| `agent.transports.codex` | OpenAI Responses API (Codex) transport. | 内核·传输 | ResponsesApiTransport |
| `agent.transports.codex_app_server` | Codex app-server JSON-RPC client. | 内核·传输 | CodexAppServerClient, CodexAppServerError, check_codex_binary, parse_codex_version |
| `agent.transports.codex_app_server_session` | Session adapter for codex app-server runtime. | 内核·传输 | CodexAppServerSession, TurnResult |
| `agent.transports.codex_event_projector` | Projects codex app-server events into Hermes' messages list. | 内核·传输 | CodexEventProjector, ProjectionResult |
| `agent.transports.hermes_tools_mcp_server` | Hermes-tools-as-MCP server for the codex_app_server runtime. | 内核·传输 | main |
| `agent.transports.types` | Shared types for normalized provider responses. | 内核·传输 | NormalizedResponse, ToolCall, Usage, build_tool_call, map_finish_reason |

## 2. 深度主题：`agent` 包六项核心能力

> 本节把 `agent` 包中六项**可独立配置 / 扩展**的核心能力做深度解析（类 / 方法表、集成要点），与 §1 逐模块枚举互补——§1 看「有哪些模块」，本节看「某个能力怎么接入 / 配置」。
> 完整签名一律见 `api-reference/05-agent.md` 对应小节（与各子节内指引一致）。

### 2.1 上下文压缩引擎（context_engine / context_compressor）


> **Hermes 原生能力**：长对话接近模型 token 上限时自动压缩上下文，避免截断与成本膨胀。
> **完整签名**：见 `api-reference/05-agent.md` 的 `agent.context_engine` / `agent.context_compressor` / `agent.conversation_compression`。

#### 定位

Context engine 决定「接近模型 token 上限时如何管理对话上下文」。内置 **`ContextCompressor`** 是默认实现；第三方引擎（如 LCM）可通过插件系统或放入 `plugins/context_engine/<name>/` 目录替换。

选择是**配置驱动**的：`config.yaml` 的 `context.engine`，默认 `"compressor"`（内置）。同一时刻**只有一个引擎生效**。

引擎职责：
- 决定何时触发压缩（`should_compress`）
- 执行压缩（摘要、DAG 构建等，`compress`）
- 可选向 agent 暴露工具（如 `lcm_grep`）
- 从 API 响应跟踪 token 用量（`update_from_response`）

#### 可插拔引擎抽象：`ContextEngine`（agent.context_engine）

第三方引擎需实现的抽象基类：

| 方法 | 作用 |
|------|------|
| `name(self) -> str` | 引擎名 |
| `update_from_response(self, usage)` | 从 API 响应更新 token 用量 |
| `should_compress(self, prompt_tokens=None) -> bool` | 是否触发压缩 |
| `compress(self, messages, current_tokens=None, focus_topic=None, force=False, memory_context='') -> List` | 执行压缩，返回压缩后消息 |
| `should_compress_preflight / should_defer_preflight_to_real_usage / has_content_to_compress` | 预检钩子 |
| `on_session_start / on_session_end / on_session_reset` | 会话生命周期钩子 |

#### 默认实现：`ContextCompressor`（agent.context_compressor）

自包含的自动压缩器，用辅助（廉价/快速）模型**总结中间轮，保护头尾上下文**。

- 构造参数（节选）：`ContextCompressor(model, threshold_percent=0.5, protect_first_n=3, protect_last_n=20, summary_target_ratio=0.2, quiet_mode=False, summary_model_override=None, abort_on_summary_failure=False, ...)`
- 关键方法：`should_compress`、`compress`、`update_model`、`record_completed_compaction(used_fallback=False)`、`get_active_compression_failure_cooldown(refresh=False)`、`bind_session_state`、`on_session_start/end/reset`
- 改进要点：结构化摘要模板（Resolved/Pending 问题跟踪）、过滤安全的摘要 preamble、**压缩失败冷却**（避免反复失败重试）。

#### 驱动方法：`agent.conversation_compression`

提取驱动摘要的 `AIAgent` 方法，核心是：
- `check_compression_model_feasibility` — **启动探针**：校验配置的辅助压缩模型。当辅助模型上下文窗口装不下主模型压缩阈值时告警，可能时自动降低会话阈值；必要时硬阻止。

#### 集成要点

- 用 `config.yaml` 的 `context.engine` 选择引擎（默认 `compressor`）。
- 写第三方引擎：实现 `ContextEngine`，放入 `plugins/context_engine/<name>/` 或经插件系统注册。
- 调优压缩：`threshold_percent`（触发阈值占比）、`protect_first_n`/`protect_last_n`（头尾保护轮数）、`summary_target_ratio`（摘要目标占比）。
- 依赖本技能 `api-reference/05-agent.md` 对应小节获取全部方法签名。

### 2.2 分层记忆系统（memory_provider / memory_manager）


> **Hermes 原生能力**：跨会话持久回忆，通过可插拔 memory provider 提供。
> **完整签名**：见 `api-reference/05-agent.md` 的 `agent.memory_provider` / `agent.memory_manager`。

#### 定位

Memory provider 给 agent **跨会话的持久回忆**。`MemoryManager` 是 `run_agent.py` 中的**单一集成点**，把散落的 per-backend 代码统一为「一个 manager 委托给已注册 provider」。

**关键约束**：只允许**一个外部 provider**（防止工具 schema 膨胀与冲突的记忆后端）。外部 provider（Honcho、Hindsight、Mem0 等）经 `MemoryManager` 注册与管理。

#### 可插拔记忆提供者：`MemoryProvider`（agent.memory_provider）

抽象基类，外部记忆后端实现：

| 方法 | 作用 |
|------|------|
| `name(self) -> str` | 提供者名 |
| `is_available(self) -> bool` | 是否可用 |
| `initialize(self, session_id, **kwargs)` | 会话初始化 |
| `system_prompt_block(self) -> str` | 注入系统提示的记忆块 |
| `prefetch(self, query, session_id='') -> str` | 预取相关记忆 |
| `queue_prefetch(self, query, session_id='')` | 异步预取 |
| `sync_turn(self, user_content, assistant_content, session_id='', messages=None)` | 每轮同步 |
| `get_tool_schemas(self) -> List` | 暴露给 agent 的工具 schema |
| `handle_tool_call(self, tool_name, args, **kwargs) -> str` | 处理记忆工具调用 |
| `shutdown(self)` | 关闭 |

#### 记忆编排：`MemoryManager`（agent.memory_manager）

协调 memory provider 的单一入口，替换散落的 per-backend 代码：
- `add_provider(self, provider)` — 注册 provider（**第二个外部 provider 会被拒绝并告警**）
- `providers(self) -> List[MemoryProvider]` / `get_provider(self, name)`
- `build_system_prompt(self) -> str` — 汇总各 provider 的系统提示块
- `prefetch_all(self, query, session_id='') -> str` / `queue_prefetch_all(...)`
- `sync_all(self, user_content, assistant_content, session_id='', messages=None)` — 每轮同步到全部 provider
- `flush_pending(self, timeout=None) -> bool` — 刷新待同步
- `get_all_tool_schemas(self) -> List` — 汇总工具 schema

辅助：`StreamingContextScrubber`（`__init__/reset/feed(text)->str/flush->str`，流式上下文擦除）。

#### 集成要点

- 记忆是**单一外部 provider** 约束：同一时刻只注册一个外部记忆后端，避免工具 schema 冲突。
- 接入外部后端（Honcho/Mem0/Hindsight）：实现 `MemoryProvider`，经 `MemoryManager.add_provider` 注册。
- 由 `MemoryManager` 统一构建系统提示、预取、每轮同步、工具 schema，不直接散调 provider。
- **记忆检索的向量/语义语义（对标 pydantic-ai Embeddings，源码核实 `plugins/memory/`）**：检索能力是**各记忆 provider 插件内部实现**，hermes 不暴露统一 embedding API。内置插件示例——`holographic`（`plugins/memory/holographic/retrieval.py`）用 **HRR 向量 + Jaccard/余弦相似度 + 信任加权打分** 做混合检索（带 `memory_banks` 向量表）；`hindsight`（云端）用 **semantic + entity graph** 多策略搜索（`hindsight_recall`）。要获得向量/语义召回，选带向量检索的 provider 即可，无需自建嵌入管线。
- 依赖本技能 `api-reference/05-agent.md` 的 `agent.memory_provider` / `agent.memory_manager` 获取完整签名。

### 2.3 用量 / 遥测 / 追踪（usage · telemetry · trace）


> **Hermes 原生能力**：用量核算、成本估算、学分跟踪、会话轨迹上传。
> **完整签名**：见 `api-reference/05-agent.md` 对应小节。

#### 账号用量：`agent.account_usage`

提供账号/学分用量视图（CLI 面板与接口）。

| 类/函数 | 作用 |
|--------|------|
| `AccountUsageSnapshot`（`.available`） | 账号用量快照 |
| `AccountUsageWindow` / `CreditsView` | 用量/学分视图模型 |
| `build_nous_credits_snapshot(account_info)` | 构建 Nous 学分快照 |
| `nous_credits_lines(markdown=False, timeout=10.0)` | 学分文本行（供显示） |
| `build_credits_view(markdown=False)` | 构建学分视图 |
| `redeem_codex_reset_credit(base_url, api_key, force=False)` | 兑换 Codex 重置学分（返回 `CodexResetRedeemResult.redeemed`） |
| `render_account_usage_lines(snapshot, markdown=False)` | 渲染用量行 |

#### 用量计价与成本估算：`agent.usage_pricing`

统一口径的 token 用量与成本计算。

| 类/函数 | 作用 |
|--------|------|
| `CanonicalUsage`（`.prompt_tokens` / `.total_tokens`） | 规范化用量 |
| `BillingRoute` / `PricingEntry` | 计费路由 / 单价条目 |
| `CostResult` | 成本计算结果 |
| `normalize_usage(response_usage, provider, api_mode)` | 把各 provider 原始用量规范化 |
| `estimate_usage_cost(model_name, usage, provider, base_url, api_key)` | 估算成本 |
| `has_known_pricing(model_name, provider, base_url, api_key)` | 是否有已知单价 |
| `resolve_billing_route(model_name, provider, base_url)` / `get_pricing_entry(...)` | 路由与单价解析 |
| `format_duration_compact(seconds)` | 时长格式化 |

#### 会话轨迹上传：`agent.trace_upload`

把 Hermes 会话转录上传到 Hugging Face 作为 agent trace。Hermes 会话存于自身 SQLite（`hermes_state.SessionDB`），此模块重建会话并导出为 **Claude Code JSONL** 形状（三种格式之一）。

| 函数 | 作用 |
|------|------|
| `load_session_messages(session_id, db_path=None)` | 从 SQLite 读会话消息 |
| `build_trace_jsonl(messages, session_id, model, cwd, redact=True) -> str` | 构建 JSONL（可脱敏 `redact`） |
| `upload_session_trace(session_id, model='', cwd='', redact=True, private=True, dataset_name=DEFAULT, token=None) -> str` | 上传轨迹，返回 URL |

> 异常：`TraceRedactionError`（脱敏失败）。

#### 学分跟踪：`agent.credits_tracker`

跟踪 Nous 推理 API 响应的学分（解析 `x-nous-credits-*` 响应头）。

| 类/函数 | 作用 |
|--------|------|
| `CreditsState`（`.has_data` / `.age_seconds` / `.depleted` / `.used_fraction`） | 校验后的学分状态 |
| `parse_credits_headers(headers, provider='') -> Optional[CreditsState]` | 解析响应头 |
| `evaluate_credits_notices(state, latch, model_is_free)` | 生成学分耗尽/订阅上限提示（`AgentNotice`） |
| `seed_credits_at_session_start(agent) -> bool` | 会话启动播种学分 |
| `is_free_tier_model(model, base_url)` | 是否免费层模型 |

#### 集成要点

- 成本核算走 `usage_pricing` 统一口径（`normalize_usage` → `estimate_usage_cost`），不直接读各 provider 原始用量。
- 学分/账号用量视图用 `account_usage` 的 `nous_credits_lines`/`build_credits_view` 渲染。
- 轨迹上传用 `trace_upload.upload_session_trace`，`redact=True` 默认脱敏、`private=True` 默认私有。
- 依赖本技能 `api-reference/05-agent.md` 对应小节获取全部签名。

### 2.4 模型 / 模态路由（image_routing · model_metadata · web_search_provider）


> **Hermes 原生能力**：多模态输入路由、模型元数据与 token 估算、可插拔搜索后端。
> **完整签名**：见 `api-reference/05-agent.md` 对应小节。

#### 图像/多模态路由：`agent.image_routing`

处理**用户附加图片**的入站路由，两种模式：
- **native（原生）**：把图片作为 OpenAI 风格的 `image_url` content part 挂到用户轮。各 provider 适配器（Anthropic / Gemini / Bedrock / Codex / OpenAI chat.completions）已负责把这一形状翻译成各自格式。
- （另一模式为 fallback/描述式，用于不支持原生图像的模型）

集成要点：桌面端接用户上传图片时，按 native 模式附加 `image_url` content part，交给 `run_conversation` 即可跨 provider 路由。

#### 模型元数据与 token 估算：`agent.model_metadata`

模型上下文长度、token 估算的纯工具函数（**无 AIAgent 依赖**）。被 `ContextCompressor` 与 `run_agent.py` 用于**预检**上下文是否放得下。依赖 `agent/models_dev.py`（models.dev 注册表）。

集成要点：需在调用模型前做上下文预检（如 `ContextCompressor` 的 `check_compression_model_feasibility`），用此模块获取上下文长度与估算 token，避免超限。

#### 可插拔搜索后端：`WebSearchProvider`（agent.web_search_provider）

web search 与内容提取的**可插拔后端接口**。Provider 经 `PluginContext.register_web_search_provider()` 注册；活动 provider 由 `web.search`（`web.search_provider`）配置选择。

| 方法 | 作用 |
|------|------|
| `name(self) -> str` / `display_name(self) -> str` | 名称 |
| `is_available(self) -> bool` | 可用性 |
| `supports_search(self) / supports_extract(self)` | 能力声明 |
| `search(self, query, limit=5) -> Dict` | 搜索 |
| `extract(self, url) -> Dict`（如有） | 内容提取 |

集成要点：接入新搜索后端（Tavily/Serper 等）实现 `WebSearchProvider`，经插件系统注册，用 `web.search_provider` 选择；不要硬编码搜索供应商（与 08 的 provider_catalog 反模式红线同理）。

#### 依赖

- `api-reference/05-agent.md` 的 `agent.image_routing` / `agent.model_metadata` / `agent.web_search_provider` 获取全部签名。
- 模型目录统一来自 `models.dev`（见 `08-capability-integration.md` Provider Routing）。

### 2.5 一次性调用（oneshot）


> **Hermes 原生能力**：非对话场景的单次、无状态模型调用。
> **完整签名**：见 `api-reference/05-agent.md` 的 `agent.oneshot`。

#### 定位

"one-shot" 是**单次、无状态的模型调用**，运行在**任何对话之外**：不触碰会话历史、**不破坏 prompt caching**，返回纯文本。UI 表面（标题生成、摘要等）用它做轻量推理。

#### 核心 API（顶层函数）

| 函数 | 作用 |
|------|------|
| `render_template(name, variables=None) -> Tuple[str, str]` | 渲染命名模板，返回 (prompt, ...) |
| `run_oneshot(instructions='', user_input='', template=None, variables=None, task='title_generation', max_tokens=1024, temperature=0.3, timeout=60.0, main_runtime=None) -> str` | 执行一次无状态模型调用，返回纯文本 |

#### 集成要点

- 用 `run_oneshot` 做标题生成、摘要、分类等**非对话**辅助推理，避免走完整会话（省 token、不破坏缓存）。
- `task` 参数预置典型用途（默认 `title_generation`）；`instructions`/`user_input`/`template` 定制提示。
- 与对话式 `AIAgent.run_conversation` 区分：oneshot 无状态、无历史、无工具上下文。
- 依赖本技能 `api-reference/05-agent.md` 的 `agent.oneshot` 获取完整签名。

> 说明：Hermes 的"批处理"概念体现在会话/任务调度（`hermes_cli` 的 cron、`gateway` 的 `run`）与多 Agent 编排（`delegate`/MoA，见 `08-capability-integration.md`），oneshot 是其轻量单次调用形式。

### 2.6 安全护栏 / 提示缓存 / 密钥作用域（safety · caching · secrets）


> **Hermes 原生能力**：工具文件安全、提示缓存、多 profile 密钥作用域。
> **完整签名**：见 `api-reference/05-agent.md` / `07-tools.md` 对应小节。

#### 文件安全：`agent.file_safety`

**共享文件安全规则**，同时被 tools 与 ACP shims 使用。统一约束工具对文件系统的读写边界（允许/拒绝路径、危险操作拦截），避免各工具各自实现导致不一致。

集成要点：新增文件类工具时复用 `file_safety` 的规则做路径/操作校验，与 ACP 行为保持一致。

#### 工具护栏：`agent.tool_guardrails`（agent 包）

工具调用的护栏/校验层，与文件安全互补（见 `13-agent-modules.md` §1 的 `agent.tool_guardrails` 条目）。集成要点：在自定义 toolset 中接入护栏，防止危险工具参数/路径。

#### 提示缓存：`agent.prompt_caching`

Anthropic 提示缓存策略，**单一布局 `system_and_3`**：4 个 `cache_control` 断点——system prompt + 最近 3 条非 system 消息，同一 TTL（5m 或 1h）。在单个多轮会话内把输入 token 成本**降低约 75%**。

集成要点：使用 Anthropic 模型的多轮会话自动受益；通过缓存断点布局控制缓存命中，减少输入 token 成本。oneshot（见 §2.5）不破坏缓存即为此考虑。

#### 密钥作用域：`agent.secret_scope`

**profile 作用域凭证解析**，服务于多 profile 网关复用。多路复用网关一个进程服务多个 profile，每个 profile 有自己的 `.env`（provider key、平台 token），**不能合并**，必须按 profile 隔离。

| 类/函数 | 作用 |
|--------|------|
| `UnscopedSecretError` | 未设置作用域时访问密钥的异常 |
| `set_multiplex_active(active)` / `is_multiplex_active()` | 多路复用开关 |
| `set_secret_scope(secrets) -> Token` / `reset_secret_scope(token)` | 进入/退出 profile 密钥作用域 |
| `current_secret_scope()` | 当前作用域 |
| `get_secret(name, default=None)` | 在当前作用域取密钥 |

集成要点：多 profile 网关下，读取 provider key/平台 token 必须经 `secret_scope`（设置/恢复作用域），禁止跨 profile 合并密钥。异常：`UnscopedSecretError`。

#### 依赖

- `api-reference/05-agent.md` 的 `agent.file_safety` / `agent.prompt_caching` / `agent.secret_scope`；`07-tools.md` 的 `tools.tool_guardrails`。
- 密钥安全边界见本技能《操作边界与删除安全规则》理念（密钥不得入记忆/日志）。

## 3. 与本文档集其他篇目关系

| 主题 | 归属文件 | 本文 role |
| --- | --- | --- |
| `AIAgent` 公开接口 / 回调 / SSE | `01-library-api.md` | 对外接口（本文不涉及） |
| 对话循环 / `run_conversation` | `01`（`conversation_loop` 提取于此） | 驱动核心（本文仅列模块） |
| 能力行为（Goals/MOA/…） | `08-capability-integration.md` | 能力语义（本文仅列模块定位） |
| 红线/门禁 | `07-quality-gates.md` | 权威红线（本文仅引用） |

> `agent` 包的任何「能力行为」描述若与 `08` 重叠，以 `08` 为准；本文只负责「模块存在性 / 用途 / 内核构成」这一层。