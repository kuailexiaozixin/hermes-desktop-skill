# 12 · `tools` 包全量模块枚举（Hermes 工具系统，0.19.0，共 113 个嵌套子模块）

> 本文件是 `tools` 包的**完整、逐模块枚举**。经 `hermes-agent==0.19.0` 已装包**逐模块 import + 读取 docstring + 提取公开 API** 核实；
> 全部 113 个嵌套子模块无一遗漏（含 `computer_use.*` / `environments.*` 等子包）。
>
> **「工具（tools）」是什么**：`tools` 是 Hermes Agent 在**进程内**真正调用的工具实现集合。
> 当你的桌面应用 `new AIAgent()` 跑起来时，Agent 需要「读文件 / 跑命令 / 查网页 / 调 MCP」等能力，
> 背后就是 `tools` 里的这些模块。它们**本来就是进程内被加载的**，不是网关/子进程路线专有。
>
> **与 03 的边界**：`03-capabilities-and-toolsets.md` 讲「57 个工具集（toolset）的行为语义与启用方式」；
> 本文讲「`tools` 包里**有哪些模块文件、各自干什么、进程内能不能直接用**」。两文通过模块名互相交叉引用，不重复能力语义。
>
> **与 10 的边界**：`10-hermes-cli.md` 列的 `hermes_cli.*` 是 CLI 包；本文列的 `tools.*` 是工具实现包，二者不同。

> **适用说明（与 `07` §1、`10` §1 一致）**：本文档以**进程内直跑路线**为叙述示例；`tools` 中依赖外部网关 / 网络 / 凭证 / 云端的模块，即使 `import` 成功，也需结合所选路线判断是否适合直接调用。
> `tools` 里依赖外部网关/网络/凭证/云端的模块，即使 `import` 成功也不应在进程内桌面应用里盲目调用其主函数。

## 1. 全量模块清单（113 个，按子包/顶层分组，不交叉不重合）

> 每行：模块 | 真实用途（取自 0.19.0 docstring）| 代表公开 API（仅列真实存在者）。

### 1.1 (top)（96 个）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `tools.ansi_strip` | Strip ANSI escape sequences from subprocess output. | sanitize_display_text, strip_ansi |
| `tools.approval` | Dangerous command approval -- detection, prompting, and per-session state. | approve_permanent, approve_session, check_all_command_guards, check_dangerous_command, check_execute_code_guard, clear_session |
| `tools.async_delegation` | Async (background) delegation registry. | active_count, claim_completion_delivery, claim_event_delivery, complete_completion_delivery, complete_event_delivery, dispatch_async_delegation |
| `tools.binary_extensions` | Binary file extensions to skip for text-based operations. | has_binary_extension |
| `tools.blueprints` | Blueprints: shareable plain-language automations layered on skills + cron. | BlueprintError, BlueprintSpec, blueprint_spec_for_installed, blueprint_to_job_spec, create_blueprint_job, export_blueprint |
| `tools.browser_camofox` | Camofox browser backend — local anti-detection browser via REST API. | camofox_back, camofox_click, camofox_close, camofox_console, camofox_get_images, camofox_navigate |
| `tools.browser_camofox_state` | Hermes-managed Camofox state helpers. | get_camofox_identity, get_camofox_state_dir |
| `tools.browser_cdp_tool` | Raw Chrome DevTools Protocol (CDP) passthrough tool. | browser_cdp |
| `tools.browser_dialog_tool` | Agent-facing tool: respond to a native JS dialog captured by the CDP supervisor. | browser_dialog |
| `tools.browser_supervisor` | Persistent CDP supervisor for browser dialog + frame detection. | CDPSupervisor, ConsoleEvent, DialogRecord, FrameInfo, PendingDialog, SupervisorSnapshot |
| `tools.browser_tool` | Browser Tool Module | browser_back, browser_click, browser_console, browser_get_images, browser_navigate, browser_press |
| `tools.budget_config` | Configurable budget constants for tool result persistence. | BudgetConfig, budget_for_context_window |
| `tools.checkpoint_manager` | Checkpoint Manager — Transparent filesystem snapshots via a single shared shadow git store. | CheckpointManager, clear_all, clear_legacy, format_checkpoint_list, maybe_auto_prune_checkpoints, prune_checkpoints |
| `tools.clarify_gateway` | Gateway-side clarify primitive (blocking event-based queue). | clear_session, get_clarify_timeout, get_notify, get_pending_for_session, has_pending, mark_awaiting_text |
| `tools.clarify_tool` | Clarify Tool Module - Interactive Clarifying Questions | check_clarify_requirements, clarify_tool |
| `tools.close_terminal_tool` | Close a read-only agent terminal tab in the Hermes desktop GUI. | check_close_terminal_requirements, close_terminal_tool |
| `tools.code_execution_tool` | Code Execution Tool -- Programmatic Tool Calling (PTC) | build_execute_code_schema, check_sandbox_requirements, execute_code, generate_hermes_tools_module |
| `tools.computer_use` | Computer use toolset — universal (any-model) macOS desktop control. | — |
| `tools.computer_use_tool` | Shim for tool discovery. Registers `computer_use` with tools.registry. | — |
| `tools.credential_files` | File passthrough registry for remote terminal backends. | clear_credential_files, from_agent_visible_cache_path, get_cache_directory_mounts, get_credential_file_mounts, get_skills_directory_mount, iter_cache_files |
| `tools.cronjob_tools` | Cron job management tools for Hermes Agent. | check_cronjob_requirements, cronjob |
| `tools.daemon_pool` | Shared daemon-thread ThreadPoolExecutor. | DaemonThreadPoolExecutor |
| `tools.debug_helpers` | Shared debug session infrastructure for Hermes tools. | DebugSession |
| `tools.delegate_tool` | Delegate Tool -- Subagent Architecture | DelegateEvent, check_delegate_requirements, delegate_task, interrupt_subagent, is_spawn_paused, list_active_subagents |
| `tools.delegation_live_log` | Live, tail-able transcripts for delegated subagents. | LiveTranscriptWriter, create_live_transcripts, live_transcript_root, new_live_delegation_id, prune_stale_live_dirs, update_manifest_statuses |
| `tools.discord_tool` | Discord server introspection and management tool. | DiscordAPIError, check_discord_tool_requirements, discord_admin_handler, discord_core, get_dynamic_schema, get_dynamic_schema_admin |
| `tools.env_passthrough` | Environment variable passthrough registry. | clear_env_passthrough, get_all_passthrough, is_env_passthrough, register_env_passthrough |
| `tools.env_probe` | Local-environment toolchain probe for the system prompt. | get_environment_probe_line, warm_environment_probe_async |
| `tools.environments` | Hermes execution environment backends. | — |
| `tools.fal_common` | Shared FAL.ai SDK plumbing. | import_fal_client |
| `tools.feishu_doc_tool` | Feishu Document Tool -- read document content via Feishu/Lark API. | get_client, set_client |
| `tools.feishu_drive_tool` | Feishu Drive Tools -- document comment operations via Feishu/Lark API. | get_client, set_client |
| `tools.file_operations` | File Operations Module | ExecuteResult, FileOperations, LintResult, PatchResult, ReadResult, SearchMatch |
| `tools.file_state` | Cross-agent file state coordination. | FileStateRegistry, check_stale, get_registry, known_reads, lock_path, note_write |
| `tools.file_tools` | File Tools Module - LLM agent file manipulation tools. | clear_file_ops_cache, notify_other_tool_call, patch_tool, read_file_tool, reset_file_dedup, search_tool |
| `tools.fuzzy_match` | Fuzzy Matching Module for File Operations | find_closest_lines, format_no_match_hint, fuzzy_find_and_replace |
| `tools.homeassistant_tool` | Home Assistant tool for controlling smart home devices via REST API. | — |
| `tools.hook_output_spill` | Spill oversized hook-injected context to disk with a preview placeholder. | get_spill_config, spill_if_oversized |
| `tools.image_generation_tool` | Image Generation Tools Module | check_fal_api_key, check_image_generation_requirements, image_generate_tool, is_krea_model |
| `tools.image_source` | Single resolver for every vision_analyze image source -> bytes + mime. | ImageResolutionError, NotAnImage, ResolveContext, ResolvedImage, SourceNotFound, SourceTooLarge |
| `tools.interrupt` | Per-thread interrupt signaling for all tools. | clear_current_thread_interrupt, is_interrupted, set_interrupt |
| `tools.kanban_tools` | Kanban tools — structured tool-call surface for worker + orchestrator agents. | heartbeat_current_worker_from_env |
| `tools.lazy_deps` | Lazy dependency installer for opt-in Hermes Agent backends. | FeatureUnavailable, activate_durable_lazy_target, active_features, ensure, ensure_and_bind, feature_install_command |
| `tools.managed_tool_gateway` | Generic managed-tool gateway helpers for Nous-hosted vendor passthroughs. | ManagedToolGatewayConfig, auth_json_path, build_vendor_gateway_url, get_tool_gateway_scheme, is_managed_tool_gateway_ready, peek_nous_access_token |
| `tools.mcp_dashboard_oauth` | Dashboard-mediated callback bridge for MCP OAuth. | DashboardOAuthFlow, dashboard_oauth_flow, get_dashboard_oauth_flow |
| `tools.mcp_oauth` | MCP OAuth 2.1 Client Support | HermesTokenStorage, OAuthNonInteractiveError, build_oauth_auth, force_interactive_oauth, remove_oauth_tokens, suppress_interactive_oauth |
| `tools.mcp_oauth_manager` | Central manager for per-server MCP OAuth state. | MCPOAuthManager, get_manager, reset_manager_for_tests |
| `tools.mcp_stdio_watchdog` | Parent-death watchdog supervisor for stdio MCP subprocesses. | main |
| `tools.mcp_tool` | MCP (Model Context Protocol) Client Support | ElicitationHandler, InvalidMcpUrlError, MCPServerTask, NonMcpEndpointError, SamplingHandler, discover_mcp_tools |
| `tools.memory_tool` | Memory Tool Module - Persistent Curated Memory | MemoryStore, apply_memory_pending, check_memory_requirements, get_memory_dir, load_on_disk_store, memory_tool |
| `tools.microsoft_graph_auth` | Microsoft Graph app-only authentication helpers. | CachedAccessToken, GraphCredentials, MicrosoftGraphAuthError, MicrosoftGraphConfigError, MicrosoftGraphTokenError, MicrosoftGraphTokenProvider |
| `tools.microsoft_graph_client` | Reusable Microsoft Graph REST client helpers. | MicrosoftGraphAPIError, MicrosoftGraphClient, MicrosoftGraphClientError |
| `tools.neutts_synth` | Standalone NeuTTS synthesis helper. | main |
| `tools.openrouter_client` | Shared OpenRouter API client for Hermes tools. | check_api_key, get_async_client |
| `tools.osv_check` | OSV malware check for MCP extension packages. | check_package_for_malware |
| `tools.patch_parser` | V4A Patch Format Parser | Hunk, HunkLine, OperationType, PatchOperation, apply_v4a_operations, parse_v4a_patch |
| `tools.path_security` | Shared path validation helpers for tool implementations. | has_traversal_component, validate_within_dir |
| `tools.process_registry` | Process Registry -- In-memory registry for managed background processes. | ProcessRegistry, ProcessSession, format_process_notification, format_uptime_short |
| `tools.project_tools` | Project tools — the agent's INTENTIONAL handle on first-class Projects. | project_create, project_list, project_switch, set_project_workspace_callback |
| `tools.read_extract` | Stdlib document-to-text extraction for ``read_file``. | ExtractionError, extract_document_text, is_extractable_document |
| `tools.read_terminal_tool` | Read the in-app terminal pane in the Hermes desktop GUI. | check_read_terminal_requirements, read_terminal_tool |
| `tools.registry` | Central registry for all hermes-agent tools. | ToolEntry, ToolRegistry, discover_builtin_tools, invalidate_check_fn_cache, tool_error, tool_result |
| `tools.schema_sanitizer` | Sanitize tool JSON schemas for broad LLM-backend compatibility. | sanitize_tool_schemas, strip_nullable_unions, strip_pattern_and_format, strip_slash_enum |
| `tools.send_message_tool` | Send Message Tool -- cross-channel messaging via platform APIs. | send_message_tool |
| `tools.session_search_tool` | Session Search Tool - Long-Term Conversation Recall | check_session_search_requirements, session_search |
| `tools.skill_manager_tool` | Skill Manager Tool -- Agent-Managed Skill Creation & Editing | apply_skill_pending, mark_background_review_skill_read, skill_manage |
| `tools.skill_provenance` | Skill write-origin provenance — ContextVar for distinguishing agent-sediment skill writes from foreground user-directed writes. | get_current_write_origin, is_background_review, reset_current_write_origin, set_current_write_origin |
| `tools.skill_usage` | Skill usage telemetry + provenance tracking for the Curator feature. | activity_count, add_suppressed_name, agent_created_report, archive_skill, bump_patch, bump_use |
| `tools.skills_ast_audit` | AST-level deep audit for skill Python files — opt-in diagnostic, not a security gate. | ast_scan_path, format_ast_report |
| `tools.skills_guard` | Skills Guard — Security scanner for externally-sourced skills. | Finding, ScanResult, content_hash, format_scan_report, full_content_hash, scan_file |
| `tools.skills_hub` | Skills Hub — Source adapters and hub state management for the Hermes Skills Hub. | BrowseShSource, ClaudeMarketplaceSource, ClawHubSource, GitHubAuth, GitHubSource, HermesIndexSource |
| `tools.skills_sync` | Skills Sync -- Manifest-based seeding and updating of bundled skills. | diff_bundled_skill, is_bundled_skills_opt_out, list_user_modified_bundled_skills, remove_pristine_bundled_skills, reset_bundled_skill, restore_official_optional_skill |
| `tools.skills_tool` | Skills Tool Module | SkillReadinessStatus, check_skills_requirements, load_env, set_secret_capture_callback, skill_matches_environment, skill_matches_platform |
| `tools.slash_confirm` | Generic slash-command confirmation primitive (gateway-side). | clear, clear_if_stale, get_pending, register, resolve, resolve_sync_compat |
| `tools.terminal_tool` | Terminal Tool Module | check_terminal_requirements, cleanup_all_environments, cleanup_vm, clear_session_cwd, clear_task_env_overrides, get_active_env |
| `tools.thread_context` | Propagate agent-turn context into worker threads that dispatch Hermes tools. | propagate_context_to_thread |
| `tools.threat_patterns` | Shared threat-pattern library for context window security scanning. | first_threat_message, scan_for_threats |
| `tools.tirith_security` | Tirith pre-exec security scanning wrapper. | check_command_security, ensure_installed, is_platform_supported |
| `tools.todo_tool` | Todo Tool Module - Planning & Task Management | TodoStore, check_todo_requirements, todo_tool |
| `tools.tool_backend_helpers` | Shared helpers for tool backend selection. | coerce_modal_mode, fal_key_is_configured, has_direct_modal_credentials, managed_nous_tools_enabled, normalize_browser_cloud_provider, normalize_modal_mode |
| `tools.tool_output_limits` | Configurable tool-output truncation limits. | get_max_bytes, get_max_line_length, get_max_lines, get_tool_output_limits |
| `tools.tool_result_storage` | Tool result persistence -- preserves large outputs instead of truncating. | enforce_turn_budget, generate_preview, maybe_persist_tool_result |
| `tools.tool_search` | Progressive tool disclosure ("tool search") for Hermes Agent. | AssemblyResult, CatalogEntry, ToolSearchConfig, assemble_tool_defs, bridge_tool_schemas, build_catalog |
| `tools.transcription_tools` | Transcription Tools Module | get_env_value, is_stt_enabled, transcribe_audio |
| `tools.tts_tool` | Text-to-Speech Tool Module | check_tts_requirements, get_env_value, stream_tts_to_speaker, text_to_speech_tool |
| `tools.url_safety` | URL safety checks — blocks requests to private/internal network addresses. | async_is_safe_url, has_sensitive_query_params, is_always_blocked_url, is_safe_url, normalize_url_for_request, redirect_target_from_response |
| `tools.video_generation_tool` | Video Generation Tool ===================== | check_video_generation_requirements |
| `tools.vision_tools` | Vision Tools Module | check_vision_requirements, video_analyze_tool, vision_analyze_tool |
| `tools.voice_mode` | Voice Mode -- Push-to-talk audio recording and playback for the CLI. | AudioRecorder, TermuxAudioRecorder, check_voice_requirements, cleanup_temp_recordings, create_audio_recorder, detect_audio_environment |
| `tools.web_tools` | Standalone Web Tools Module | check_web_api_key, convert_base64_images_to_links, web_extract_tool, web_search_tool |
| `tools.website_policy` | Website access policy helpers for URL-capable tools. | WebsitePolicyError, check_website_access, invalidate_cache, load_website_blocklist |
| `tools.write_approval` | Write-approval gate + pending store for memory and skill writes. | GateDecision, current_origin, discard_pending, evaluate_gate, get_pending, is_background |
| `tools.x_search_tool` | X Search tool backed by xAI's built-in ``x_search`` Responses API tool. | check_x_search_requirements, x_search_tool |
| `tools.xai_http` | Shared helpers for direct xAI HTTP integrations. | build_xai_storage_options, get_env_value, has_xai_credentials, hermes_xai_user_agent, maybe_mark_xai_storage_notice_seen, read_xai_imagine_storage_config |
| `tools.xai_video_tools` | xAI-specific Imagine video edit and extend tools. | — |
| `tools.yuanbao_tools` | yuanbao_tools.py - 元宝平台工具集 | get_group_info, query_group_members, search_sticker, send_dm, send_sticker |

### 1.2 tools.computer_use.*（7 个）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `tools.computer_use.backend` | Abstract backend interface for computer use. | ActionResult, CaptureResult, ComputerUseBackend, UIElement |
| `tools.computer_use.cua_backend` | Cua-driver backend (macOS, Windows, Linux). | CuaDriverBackend, cua_driver_binary_available, cua_driver_child_env, cua_driver_install_hint, cua_driver_update_check, cua_driver_update_nudge |
| `tools.computer_use.doctor` | `hermes computer-use doctor` — thin client for cua-driver's `health_report` MCP tool. | run_doctor |
| `tools.computer_use.permissions` | Cross-platform Computer Use readiness + macOS permission helpers. | computer_use_status, request_permissions_grant |
| `tools.computer_use.schema` | Schema for the generic `computer_use` tool. | get_computer_use_schema |
| `tools.computer_use.tool` | Entry point for the `computer_use` tool. | check_computer_use_requirements, get_computer_use_schema, handle_computer_use, reset_backend_for_tests, set_approval_callback |
| `tools.computer_use.vision_routing` | Vision-routing decisions for ``computer_use`` capture results. | should_route_capture_to_aux_vision |

### 1.3 tools.environments.*（10 个）

| 模块 | 用途 | 代表 API |
| --- | --- | --- |
| `tools.environments.base` | Base class for all Hermes execution environment backends. | BaseEnvironment, ProcessHandle, get_sandbox_dir, set_activity_callback, touch_activity_if_due |
| `tools.environments.daytona` | Daytona cloud execution environment. | DaytonaEnvironment |
| `tools.environments.docker` | Docker execution environment for sandboxed command execution. | DockerEnvironment, find_docker, reap_orphan_containers |
| `tools.environments.file_sync` | Shared file sync manager for remote execution backends. | FileSyncManager, iter_sync_files, quoted_mkdir_command, quoted_rm_command, unique_parent_dirs |
| `tools.environments.local` | Local execution environment — spawn-per-call with session snapshot. | LocalEnvironment, hermes_subprocess_env |
| `tools.environments.managed_modal` | Managed Modal environment backed by tool-gateway. | ManagedModalEnvironment |
| `tools.environments.modal` | Modal cloud execution environment using the native Modal SDK directly. | ModalEnvironment |
| `tools.environments.modal_utils` | Shared Hermes-side execution flow for Modal transports. | BaseModalExecutionEnvironment, ModalExecStart, PreparedModalExec, wrap_modal_stdin_heredoc, wrap_modal_sudo_pipe |
| `tools.environments.singularity` | Singularity/Apptainer persistent container environment. | SingularityEnvironment |
| `tools.environments.ssh` | SSH remote execution environment with ControlMaster connection persistence. | SSHEnvironment |

## 2. 与本文档集其他篇目关系

| 主题 | 归属文件 | 本文 role |
| --- | --- | --- |
| 工具集（toolset）行为语义 / 57 工具集逐条 | `03-capabilities-and-toolsets.md` | 能力行为（本文不列） |
| 工具注册表 / 自定义注册 | `01-library-api.md`（`tools.registry` 用法） | 注册机制（本文仅列模块） |
| 进程内三条集成路径 / SSE 桥接 | `02-integration-core.md` | 驱动核心（本文不涉及） |
| `hermes_cli` 模块清单 | `10-hermes-cli.md` | 不同包（CLI vs 工具实现） |
| 红线/门禁 | `07-quality-gates.md` | 权威红线（本文仅引用） |

> 任何对工具「能力行为」的描述若与 `03` 重叠，以 `03` 为准；本文只负责「模块存在性 / 用途 / 代表 API」这一层。