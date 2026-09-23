# agent — Agent 内核包（156 模块）

> **模块**: `agent/`（包，共 156 个模块）
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: Agent 内核：对话循环、适配器、工具执行、记忆、模型注册等。

## agent.__init__

### 模块文档

Agent internals -- extracted modules from run_agent.py.

These modules contain pure utility functions and self-contained classes
that were previously embedded in the 3,600-line run_agent.py. Extracting
them makes run_agent.py focused on the AIAgent orchestrator class.

## agent.account_usage

### class AccountUsageWindow

> 继承: `object` ｜ 方法数: 0（公开 0）


### class AccountUsageSnapshot

> 继承: `object` ｜ 方法数: 1（公开 1）

#### property `available(self) -> bool`


### class CreditsView

> 继承: `object` ｜ 方法数: 0（公开 0）

Surface-agnostic data for the ``/topup`` balance view.

One portal fetch, one parse — consumed identically by the CLI panel, the
gateway button, and any other money surface. Fail-open: when not logged in
or the portal is unreachable, ``logged_in`` is False / ``topup_url`` is None
and callers degrade gracefully.


### class CodexResetRedeemResult

> 继承: `object` ｜ 方法数: 1（公开 1）

Outcome of a `/usage reset` attempt against the Codex backend.

#### property `redeemed(self) -> bool`


### 顶层函数

#### def `render_account_usage_lines(snapshot: Optional[AccountUsageSnapshot], markdown: bool = False) -> list[str]`

#### def `build_nous_credits_snapshot(account_info) -> Optional[AccountUsageSnapshot]`

Map a NousPortalAccountInfo into an AccountUsageSnapshot for /usage.

Shows dollar magnitudes (subscription / top-up / total) + renewal date + a
portal CTA. When the portal supplies a subscription denominator
(``monthly_credits``), also emits a subscription-usage window so the renderer
shows a real ``% used`` gauge; when it's absent (older portals) the view
gracefully degrades to magnitudes-only. Returns None when there's no usable
account info to show (fail-open: caller just shows nothing).

#### def `nous_credits_lines(markdown: bool = False, timeout: float = 10.0) -> list[str]`

Return rendered Nous-credits /usage lines, or [] when there's nothing to show.

Account-independent of any live agent: gated on "a Nous account is logged in"
(a cheap local auth-state check), then a wall-clock-bounded portal fetch. Shared
by the CLI ``_show_usage`` and the TUI ``session.usage`` RPC so both surfaces show
the same block regardless of session API-call count or resume state. Fail-open:
any auth/portal hiccup or timeout returns [] (the caller shows nothing).

Dev override: when HERMES_DEV_CREDITS_FIXTURE selects a fixture state, /usage
renders from that fixture instead of the real portal (so the block + gauge are
testable without a live account). Throwaway scaffolding.

#### def `build_credits_view(markdown: bool = False, timeout: float = 10.0) -> CreditsView`

Build the /topup balance view: balance block + identity line + top-up URL.

Reuses the same account fetch + snapshot + URL builder as the /usage credits
block, so the numbers always match. The balance block is the rendered
snapshot MINUS its trailing top-up/command-hint lines (the /topup surface
supplies its own affordance). Fail-open → ``CreditsView(logged_in=False)``.

#### def `redeem_codex_reset_credit(base_url: Optional[str] = None, api_key: Optional[str] = None, force: bool = False) -> CodexResetRedeemResult`

Redeem one banked Codex rate-limit reset credit (`/usage reset`).

Flow (mirrors the Codex CLI's reset-credits picker, codex-rs
``backend-client``):

1. ``GET .../usage`` — read the current windows + banked credit count.
2. Guard: zero banked credits → refuse. No window fully used and not
   ``force`` → refuse with a warning (a banked reset restores the WHOLE
   5h + weekly allowance; burning it early wastes it). The backend has
   the same protection (``nothing_to_reset`` doesn't consume the
   credit), but failing fast client-side gives a clearer message.
3. ``POST .../rate-limit-reset-credits/consume`` with a fresh UUID
   idempotency key (``redeem_request_id``). No ``credit_id`` — the
   backend picks the next available credit, exactly like the CLI's
   default "Full reset" option.

Never raises: every failure mode returns a ``CodexResetRedeemResult``
with a user-renderable message.

#### def `fetch_account_usage(provider: Optional[str], base_url: Optional[str] = None, api_key: Optional[str] = None) -> Optional[AccountUsageSnapshot]`


## agent.agent_init

### 模块文档

Implementation of :meth:`AIAgent.__init__` — extracted as a module function.

``AIAgent.__init__`` is one of the longest methods in the codebase (60+
parameters, ~1,400 lines of attribute initialization, provider
auto-detection, credential resolution, context-engine bootstrap, etc.).
Keeping it in ``run_agent.py`` bloats that file with code that's mostly
"setup state, then forget".

After this extraction the body lives here as ``init_agent(agent, ...)``
and :meth:`AIAgent.__init__` is a thin wrapper that calls
``init_agent(self, ...)``.  All imports the body needs at module-load
time are listed below; the body also performs many lazy imports inside
its own scope that come along unchanged.

Symbols that tests patch on ``run_agent.*`` (``OpenAI``, ``cleanup_vm``,
etc.) are resolved through :func:`_ra` so the patch contract is
preserved.

### 顶层函数

#### def `init_agent(agent, base_url: str = None, api_key: str = None, provider: str = None, api_mode: str = None, acp_command: str = None, acp_args: list[str] | None = None, command: str = None, args: list[str] | None = None, model: str = '', max_iterations: int = 90, tool_delay: float = 1.0, enabled_toolsets: List[str] = None, disabled_toolsets: List[str] = None, save_trajectories: bool = False, verbose_logging: bool = False, quiet_mode: bool = False, tool_progress_mode: str = 'all', ephemeral_system_prompt: str = None, log_prefix_chars: int = 100, log_prefix: str = '', providers_allowed: List[str] = None, providers_ignored: List[str] = None, providers_order: List[str] = None, provider_sort: str = None, provider_require_parameters: bool = False, provider_data_collection: str = None, openrouter_min_coding_score: Optional[float] = None, session_id: str = None, tool_progress_callback: callable = None, tool_start_callback: callable = None, tool_complete_callback: callable = None, thinking_callback: callable = None, reasoning_callback: callable = None, clarify_callback: callable = None, read_terminal_callback: callable = None, step_callback: callable = None, stream_delta_callback: callable = None, interim_assistant_callback: callable = None, tool_gen_callback: callable = None, status_callback: callable = None, notice_callback: callable = None, notice_clear_callback: callable = None, event_callback: Optional[Callable[[str, dict], None]] = None, reaction_callback: Optional[Callable[[str], None]] = None, max_tokens: int = None, reasoning_config: Dict[str, Any] = None, service_tier: str = None, request_overrides: Dict[str, Any] = None, prefill_messages: List[Dict[str, Any]] = None, platform: str = None, user_id: str = None, user_id_alt: str = None, user_name: str = None, chat_id: str = None, chat_name: str = None, chat_type: str = None, thread_id: str = None, gateway_session_key: str = None, skip_context_files: bool = False, load_soul_identity: bool = False, skip_memory: bool = False, session_db = None, parent_session_id: str = None, iteration_budget: IterationBudget = None, fallback_model: Dict[str, Any] = None, credential_pool = None, checkpoints_enabled: bool = False, checkpoint_max_snapshots: int = 20, checkpoint_max_total_size_mb: int = 500, checkpoint_max_file_size_mb: int = 10, pass_session_id: bool = False)`

Initialize the AI Agent.

Args:
    base_url (str): Base URL for the model API (optional)
    api_key (str): API key for authentication (optional, uses env var if not provided)
    provider (str): Provider identifier (optional; used for telemetry/routing hints)
    api_mode (str): API mode override: "chat_completions" or "codex_responses"
    model (str): Model name to use (default: "anthropic/claude-opus-4.6")
    max_iterations (int): Maximum number of tool calling iterations (default: 90)
    tool_delay (float): Delay between tool calls in seconds (default: 1.0)
    enabled_toolsets (List[str]): Only enable tools from these toolsets (optional)
    disabled_toolsets (List[str]): Disable tools from these toolsets (optional)
    save_trajectories (bool): Whether to save conversation trajectories to JSONL files (default: False)
    verbose_logging (bool): Enable verbose logging for debugging (default: False)
    quiet_mode (bool): Suppress progress output for clean CLI experience (default: False)
    ephemeral_system_prompt (str): System prompt used during agent execution but NOT saved to trajectories (optional)
    log_prefix_chars (int): Number of characters to show in log previews for tool calls/responses (default: 100)
    log_prefix (str): Prefix to add to all log messages for identification in parallel processing (default: "")
    providers_allowed (List[str]): OpenRouter providers to allow (optional)
    providers_ignored (List[str]): OpenRouter providers to ignore (optional)
    providers_order (List[str]): OpenRouter providers to try in order (optional)
    provider_sort (str): Sort providers by price/throughput/latency (optional)
    openrouter_min_coding_score (float): Coding-score floor (0.0-1.0) for the
        openrouter/pareto-code router. Only applied when model == "openrouter/pareto-code".
        None or empty = let OpenRouter pick the strongest available coder.
    session_id (str): Pre-generated session ID for logging (optional, auto-generated if not provided)
    tool_progress_callback (callable): Callback function(tool_name, args_preview) for progress notifications
    clarify_callback (callable): Callback function(question, choices) -> str for interactive user questions.
        Provided by the platform layer (CLI or gateway). If None, the clarify tool returns an error.
    max_tokens (int): Maximum tokens for model responses (optional, uses model default if not set)
    reasoning_config (Dict): OpenRouter reasoning configuration override (e.g. {"effort": "none"} to disable thinking).
        If None, defaults to {"enabled": True, "effort": "medium"} for OpenRouter. Set to disable/customize reasoning.
    prefill_messages (List[Dict]): Messages to prepend to conversation history as prefilled context.
        Useful for injecting a few-shot example or priming the model's response style.
        Example: [{"role": "user", "content": "Hi!"}, {"role": "assistant", "content": "Hello!"}]
        NOTE: Anthropic Sonnet 4.6+ and Opus 4.6+ reject a conversation that ends on an
        assistant-role message (400 error).  For those models use structured outputs or
        output_config.format instead of a trailing-assistant prefill.
    platform (str): The interface platform the user is on (e.g. "cli", "telegram", "discord", "whatsapp").
        Used to inject platform-specific formatting hints into the system prompt.
    skip_context_files (bool): If True, skip auto-injection of project context files
        (SOUL.md, .hermes.md, AGENTS.md, CLAUDE.md, .cursorrules) from the cwd / HERMES_HOME
        into the system prompt. Use this for batch processing and data generation to avoid
        polluting trajectories with user-specific persona or project instructions.
    load_soul_identity (bool): If True, still use ~/.hermes/SOUL.md as the primary
        identity even when skip_context_files=True. Project context files from the cwd
        remain skipped.

**异常**: `ValueError`, `RuntimeError`


## agent.agent_runtime_helpers

### 模块文档

Assorted AIAgent runtime helpers — moved out of run_agent.py for clarity.

Each function takes the parent ``AIAgent`` as its first argument
(``agent``) except for the static helpers (``sanitize_tool_call_arguments``,
``drop_thinking_only_and_merge_users``) which are stateless.  AIAgent
keeps thin forwarders for backward compatibility.

Methods covered:
* ``convert_to_trajectory_format`` — internal -> trajectory-file format
* ``sanitize_tool_call_arguments`` — repair corrupted JSON in tool_calls
* ``repair_message_sequence`` — enforce alternation invariants
* ``strip_think_blocks`` — remove inline reasoning from stored content
* ``recover_with_credential_pool`` — rotate pool entries on 429
* ``try_recover_primary_transport`` — re-create OpenAI client after rate-limit
* ``drop_thinking_only_and_merge_users`` — Anthropic-style cleanup
* ``restore_primary_runtime`` — un-do fallback activation
* ``extract_reasoning`` — pull reasoning fields out of API responses
* ``dump_api_request_debug`` — write request body for post-mortem
* ``anthropic_prompt_cache_policy`` — compute cache_control breakpoints
* ``create_openai_client`` — build the per-agent OpenAI SDK client

### 顶层函数

#### def `agent_runtime_owns_post_tool_hook(agent: Any, function_name: str) -> bool`

Return True when an agent-level tool path emits its own post hook.

#### def `convert_to_trajectory_format(agent, messages: List[Dict[str, Any]], user_query: str, completed: bool) -> List[Dict[str, Any]]`

Convert internal message format to trajectory format for saving.

Args:
    messages (List[Dict]): Internal message history
    user_query (str): Original user query
    completed (bool): Whether the conversation completed successfully
    
Returns:
    List[Dict]: Messages in trajectory format

#### def `sanitize_tool_call_arguments(messages: list, logger = None, session_id: str = None) -> int`

Repair corrupted assistant tool-call argument JSON in-place.

#### def `note_turn_start(agent, turn_id: str)`

Tripwire: detect a turn starting while a previous turn of the same
agent — or of the same underlying *session* on a different agent object —
has not completed its turn-end persist.

Two turns interleaving on one session corrupt the durable transcript:
their flushes race (user rows can persist out of arrival order), a row
can be swallowed by the identity-marker dedup over shared history dicts,
and the second turn runs on a history base that never saw the first
turn's exchange. This helper does NOT prevent any of that — it names the
occurrence, with both turn ids, so the dispatch route that let the
second turn through the busy guard can be identified from logs.

Returns the previous in-flight turn_id when an overlap is detected,
else None. Takes ownership of the in-flight slot either way, so a turn
that crashed before its persist produces at most one warning.

#### def `note_turn_persisted(agent)`

Clear the in-flight marker at turn-end persist (see note_turn_start).

Called from the single persist funnel; unconditional by design — when two
turns genuinely overlap, the first persist clears the second turn's slot
and the tripwire under-reports instead of double-reporting. A diagnostic
must never be noisier than the defect it hunts.

#### def `repair_message_sequence(agent, messages: List[Dict]) -> int`

Collapse malformed role-alternation left in the live history.

Providers (OpenAI, OpenRouter, Anthropic) expect strict alternation:
after the system message, user/tool alternates with assistant, with
no two consecutive user messages and no tool-result that doesn't
follow an assistant-with-tool_calls. Violations cause silent empty
responses on most providers, which triggers the empty-retry loop.

This runs right before the API call as a defensive belt — by the
time it fires, the scaffolding strip should already have prevented
most shapes, but external callers (gateway multi-queue replay,
session resume, cron, explicit conversation_history passed in by
host code) can feed in already-broken histories.

Repairs applied:
  0. Consecutive ``assistant`` messages with no intervening
     ``tool``/``user`` turn — merged into a single assistant turn
     (union of ``tool_calls``, concatenated ``content``). Strict
     OpenAI-compatible providers (DeepSeek v4, Moonshot/Kimi) reject
     a history where an ``assistant`` message carrying ``tool_calls``
     is immediately followed by another ``assistant`` message instead
     of its ``tool`` results — HTTP 400 "An assistant message with
     'tool_calls' must be followed by tool messages…". The split
     shape is produced by recovery/continuation paths that append an
     interim assistant turn (thinking-prefill, codex
     incomplete-continuation) or by host-fed / legacy-persisted /
     resumed histories. Refs #29148, #49147.
  1. Stray ``tool`` messages whose ``tool_call_id`` doesn't match
     any preceding assistant tool_call — dropped.
  2. Consecutive ``user`` messages — merged with newline separator
     so no user input is lost.

Deliberately does NOT rewind orphan ``assistant(tool_calls)+tool``
pairs that precede a user message — that pattern IS valid when the
previous turn completed normally and the user jumped in to redirect
before the model got a continuation turn (the ongoing dialog
pattern). The empty-response scaffolding stripper handles the
genuinely-broken variant via its flag-gated rewind.

Returns the number of repairs made (for logging/telemetry).

#### def `repair_message_sequence_with_cursor(agent, messages: List[Dict]) -> int`

Run :func:`repair_message_sequence` and keep the SessionDB flush
cursor consistent with the compacted list (#44837).

``repair_message_sequence`` merges/drops messages in place, shrinking
the list. ``_last_flushed_db_idx`` (the DB-write cursor) indexes into
that list, so after compaction it can point past the new end — the
turn-end flush would then skip the assistant/tool chain entirely — or
past unflushed messages shifted to lower indexes.

Repair preserves object identity for surviving messages, so counting
the survivors from the previously-flushed prefix gives the exact new
cursor even when messages are dropped/merged at indexes *before* the
cursor — a plain ``min()`` clamp would silently skip that many
unflushed rows. Falls back to the clamp when no prefix snapshot is
available.

Returns the number of repairs made (same as ``repair_message_sequence``).

#### def `strip_think_blocks(agent, content: str) -> str`

Remove reasoning/thinking blocks from content, returning only visible text.

Handles four cases:
  1. Closed tag pairs (`` <think>… ``) — the common path when
     the provider emits complete reasoning blocks.
  2. Unterminated open tag at a block boundary (start of text or
     after a newline) — e.g. MiniMax M2.7 / NIM endpoints where the
     closing tag is dropped.  Everything from the open tag to end
     of string is stripped.  The block-boundary check mirrors
     ``gateway/stream_consumer.py``'s filter so models that mention
     `` <think>`` in prose aren't over-stripped.
  3. Stray orphan open/close tags that slip through.
  4. Tag variants: `` <think>``, ``<thinking>``, ``<reasoning>``,
     ``<REASONING_SCRATCHPAD>``, ``<thought>`` (Gemma 4), all
     case-insensitive.

Additionally strips standalone tool-call XML blocks that some open
models (notably Gemma variants on OpenRouter) emit inside assistant
content instead of via the structured ``tool_calls`` field:
  * ``<tool_call>…</tool_call>``
  * ``<tool_calls>…</tool_calls>``
  * ``<tool_result>…</tool_result>``
  * ``<function_call>…</function_call>``
  * ``<function_calls>…</function_calls>``
  * ``<function name="…">…</function>`` (Gemma style)
Ported from openclaw/openclaw#67318. The ``<function>`` variant is
boundary-gated (only strips when the tag sits at start-of-line or
after punctuation and carries a ``name="..."`` attribute) so prose
mentions like "Use <function> in JavaScript" are preserved.

#### def `recover_with_credential_pool(agent, status_code: Optional[int], has_retried_429: bool, classified_reason: Optional[FailoverReason] = None, error_context: Optional[Dict[str, Any]] = None) -> tuple[bool, bool]`

Attempt credential recovery via pool rotation.

Returns (recovered, has_retried_429).
On rate limits: first occurrence retries same credential (sets flag True).
                second consecutive failure rotates to next credential.
On billing exhaustion: immediately rotates.
On auth failures: attempts token refresh before rotating.

`classified_reason` lets the recovery path honor the structured error
classifier instead of relying only on raw HTTP codes. This matters for
providers that surface billing/rate-limit/auth conditions under a
different status code, such as Anthropic returning HTTP 400 for
"out of extra usage".

#### def `try_recover_primary_transport(agent, api_error: Exception, retry_count: int, max_retries: int) -> bool`

Attempt one extra primary-provider recovery cycle for transient transport failures.

After ``max_retries`` exhaust, rebuild the primary client (clearing
stale connection pools) and give it one more attempt before falling
back.  This is most useful for direct endpoints (custom, Z.AI,
Anthropic, OpenAI, local models) where a TCP-level hiccup does not
mean the provider is down.

Skipped for proxy/aggregator providers (OpenRouter, Nous) which
already manage connection pools and retries server-side — if our
retries through them are exhausted, one more rebuilt client won't help.

#### def `drop_thinking_only_and_merge_users(messages: List[Dict[str, Any]], drop_codex_reasoning_items: bool = True) -> List[Dict[str, Any]]`

Drop thinking-only assistant turns; merge any adjacent user messages left behind.

Runs on the per-call ``api_messages`` copy only. The stored
conversation history (``agent.messages``) is never mutated, so the
user still sees the thinking block in the CLI/gateway transcript and
session persistence keeps the full trace. Only the wire copy sent to
the provider is cleaned.

Why drop-and-merge rather than inject stub text:
- Fabricating ``"."`` / ``"(continued)"`` text lies in the history
  and makes future turns see model output the model didn't emit.
- Dropping the turn preserves honesty; merging adjacent user messages
  preserves the provider's role-alternation invariant.
- This is the pattern used by Claude Code's ``normalizeMessagesForAPI``
  (filterOrphanedThinkingOnlyMessages + mergeAdjacentUserMessages).

#### def `restore_primary_runtime(agent) -> bool`

Restore the primary runtime at the start of a new turn.

In long-lived CLI sessions a single AIAgent instance spans multiple
turns.  Without restoration, one transient failure pins the session
to the fallback provider for every subsequent turn.  Calling this at
the top of ``run_conversation()`` makes fallback turn-scoped.

The gateway caches agents across messages (``_agent_cache`` in
``gateway/run.py``), so this restoration IS needed there too.

#### def `extract_reasoning(agent, assistant_message) -> Optional[str]`

Extract reasoning/thinking content from an assistant message.

OpenRouter and various providers can return reasoning in multiple formats:
1. message.reasoning - Direct reasoning field (DeepSeek, Qwen, etc.)
2. message.reasoning_content - Alternative field (Moonshot AI, Novita, etc.)
3. message.reasoning_details - Array of {type, summary, ...} objects (OpenRouter unified)

Args:
    assistant_message: The assistant message object from the API response
    
Returns:
    Combined reasoning text, or None if no reasoning found

#### def `dump_api_request_debug(agent, api_kwargs: Dict[str, Any], reason: str, error: Optional[Exception] = None) -> Optional[Path]`

Dump a debug-friendly HTTP request record for the active inference API.

Captures the request body from api_kwargs (excluding transport-only keys
like timeout). Intended for debugging provider-side 4xx failures where
retries are not useful.

#### def `anthropic_prompt_cache_policy(agent, provider: Optional[str] = None, base_url: Optional[str] = None, api_mode: Optional[str] = None, model: Optional[str] = None) -> tuple[bool, bool]`

Decide whether to apply Anthropic prompt caching and which layout to use.

Returns ``(should_cache, use_native_layout)``:
  * ``should_cache`` — inject ``cache_control`` breakpoints for this
    request (applies to OpenRouter Claude, native Anthropic, and
    third-party gateways that speak the native Anthropic protocol).
  * ``use_native_layout`` — place markers on the *inner* content
    blocks (native Anthropic accepts and requires this layout);
    when False markers go on the message envelope (OpenRouter and
    OpenAI-wire proxies expect the looser layout).

Third-party providers using the native Anthropic transport
(``api_mode == 'anthropic_messages'`` + Claude-named model) get
caching with the native layout so they benefit from the same
cost reduction as direct Anthropic callers, provided their
gateway implements the Anthropic cache_control contract
(MiniMax, Zhipu GLM, LiteLLM's Anthropic proxy mode all do).

Qwen / Alibaba-family models on OpenCode, OpenCode Go, and direct
Alibaba (DashScope) also honour Anthropic-style ``cache_control``
markers on OpenAI-wire chat completions. Upstream pi-mono #3392 /
pi #3393 documented this for opencode-go Qwen. Without markers
these providers serve zero cache hits, re-billing the full prompt
on every turn.

#### def `create_openai_client(agent, client_kwargs: dict, reason: str, shared: bool) -> Any`

#### def `switch_model(agent, new_model, new_provider, api_key = '', base_url = '', api_mode = '')`

Switch the model/provider in-place for a live agent.

Called by the /model command handlers (CLI and gateway) after
``model_switch.switch_model()`` has resolved credentials and
validated the model.  This method performs the actual runtime
swap: rebuilding clients, updating caching flags, and refreshing
the context compressor.

The implementation mirrors ``_try_activate_fallback()`` for the
client-swap logic but also updates ``_primary_runtime`` so the
change persists across turns (unlike fallback which is
turn-scoped).

**异常**: `ValueError`

#### def `invoke_tool(agent, function_name: str, function_args: dict, effective_task_id: str, tool_call_id: Optional[str] = None, messages: list = None, pre_tool_block_checked: bool = False, skip_tool_request_middleware: bool = False, tool_request_middleware_trace: Optional[List[Dict[str, Any]]] = None) -> str`

Invoke a single tool and return the result string. No display logic.

Handles both agent-level tools (todo, memory, etc.) and registry-dispatched
tools. Used by the concurrent execution path; the sequential path retains
its own inline invocation for backward-compatible display handling.

#### def `repair_tool_call(agent, tool_name: str) -> str | None`

Attempt to repair a mismatched tool name before aborting.

Models sometimes emit variants of a tool name that differ only
in casing, separators, or class-like suffixes. Normalize
aggressively before falling back to fuzzy match:

1. Lowercase direct match.
2. Lowercase + hyphens/spaces -> underscores.
3. CamelCase -> snake_case (TodoTool -> todo_tool).
4. Strip trailing ``_tool`` / ``-tool`` / ``tool`` suffix that
   Claude-style models sometimes tack on (TodoTool_tool ->
   TodoTool -> Todo -> todo). Applied twice so double-tacked
   suffixes like ``TodoTool_tool`` reduce all the way.
5. Fuzzy match (difflib, cutoff=0.7).

See #14784 for the original reports (TodoTool_tool, Patch_tool,
BrowserClick_tool were all returning "Unknown tool" before).

Returns the repaired name if found in valid_tool_names, else None.

#### def `sanitize_api_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Fix orphaned tool_call / tool_result pairs before every LLM call.

Runs unconditionally — not gated on whether the context compressor
is present — so orphans from session loading or manual message
manipulation are always caught.

#### def `looks_like_codex_intermediate_ack(agent, user_message: Any, assistant_content: str, messages: List[Dict[str, Any]], require_workspace: bool = True) -> bool`

Detect a planning/ack message that should continue instead of ending the turn.

``require_workspace`` (default True) keeps the original codex-coding scope:
the ack must reference a filesystem/repo workspace. The conversation loop
passes ``require_workspace=False`` when the user has explicitly opted into
intent-ack continuation for all api_modes (``agent.intent_ack_continuation``
is ``true`` or a model-list), so general autonomous workflows ("I'll run a
health check on the server", "I'll start the deployment") — which carry a
future-ack and an action verb but no filesystem reference — are caught too.
The future-ack + short-content + no-prior-tools + action-verb requirements
always apply, which is what keeps conversational "I'll help you brainstorm"
replies from tripping it.

#### def `intent_ack_continuation_mode(agent) -> str`

Classify the resolved intent-ack continuation mode for this turn.

Returns one of:
  * ``"off"``        — never continue.
  * ``"codex_only"`` — historical scope: continue only on the
    ``codex_responses`` api_mode, and only for codebase/workspace acks
    (``require_workspace=True``).
  * ``"all"``        — user opted in for every api_mode; continue on any
    future-ack + action verb (``require_workspace=False``).

Mirrors the four-mode shape of ``agent.tool_use_enforcement``: ``"auto"``
(default) → codex_only; ``True``/"true"/"always"/"yes"/"on" → all;
``False``/"false"/"never"/"no"/"off" → off; ``list`` → all when a substring
matches the active model name, else off.

#### def `intent_ack_continuation_enabled(agent) -> bool`

Whether intent-ack continuation should fire at all for this turn.

The ``codex_ack_continuations < 2`` per-turn cap and the
``looks_like_codex_intermediate_ack`` detector are applied by the caller;
this only decides the on/off gate. Callers that also need to know whether
the workspace requirement applies should use ``intent_ack_continuation_mode``
directly (``"codex_only"`` ⇒ require_workspace=True, ``"all"`` ⇒ False).

#### def `copy_reasoning_content_for_api(agent, source_msg: dict, api_msg: dict) -> None`

Copy provider-facing reasoning fields onto an API replay message.

#### def `reapply_reasoning_echo_for_provider(agent, api_messages: list) -> int`

Re-pad (or strip) assistant turns' reasoning_content for the active provider.

``api_messages`` is built once, before the retry loop, while the *primary*
provider is active.  A mid-conversation fallback can then switch providers,
so the reasoning fields baked into ``api_messages`` are shaped for the
*prior* provider and must be reconciled against the *current* one:

* Switching TO a require-side provider (DeepSeek / Kimi / MiMo thinking
  mode): assistant turns built when the prior provider did NOT need the
  echo-back go out without ``reasoning_content`` and the new provider
  rejects them with HTTP 400 ("The reasoning_content in the thinking mode
  must be passed back").  Re-apply the pad.

* Switching TO a strict provider that rejects the field (Mistral,
  Cerebras, Groq, SambaNova, …): assistant turns built under a reasoning
  primary carry a ``reasoning_content`` pad (often a single space ``" "``),
  and the strict provider rejects it with HTTP 400/422 ("Extra inputs are
  not permitted").  Strip the field.  This is the exact cross-provider
  fallback bug from #45655 — a DeepSeek primary pads history with ``" "``,
  the request falls back to Mistral, and Mistral 422s on the stale pad.

Calling this immediately before building the request kwargs reconciles the
fields against the *current* provider.  It is idempotent and safe to call
every iteration; it covers every fallback path.

Returns the number of assistant turns whose reasoning_content was added or
removed.

#### def `cleanup_dead_connections(agent) -> bool`

Detect and clean up dead TCP connections on the primary client.

Inspects the httpx connection pool for sockets in unhealthy states
(CLOSE-WAIT, errors).  If any are found, force-closes all sockets
and rebuilds the primary client from scratch.

Returns True if dead connections were found and cleaned up.

#### def `extract_api_error_context(error: Exception) -> Dict[str, Any]`

Extract structured rate-limit details from provider errors.

#### def `apply_pending_steer_to_tool_results(agent, messages: list, num_tool_msgs: int) -> None`

Append any pending /steer text to the last tool result in this turn.

Called at the end of a tool-call batch, before the next API call.
The steer is appended to the last ``role:"tool"`` message's content
with a clear marker so the model understands it came from the user
and NOT from the tool itself. Role alternation is preserved —
nothing new is inserted, we only modify existing content.

Args:
    messages: The running messages list.
    num_tool_msgs: Number of tool results appended in this batch;
        used to locate the tail slice safely.

#### def `force_close_tcp_sockets(client: Any) -> int`

Abort in-flight TCP I/O by shutting down sockets WITHOUT closing FDs.

When a provider drops a connection mid-stream — or the user issues an
interrupt — we want to unblock httpx's reader/writer immediately rather
than waiting for the kernel's per-connection timeout. ``shutdown(SHUT_RDWR)``
achieves that: it sends FIN, breaks any pending ``recv``/``send`` with EOF
or ``EPIPE``, but does NOT release the file descriptor.

Historically this helper also called ``socket.close()`` so the FD got
released immediately, but that's unsafe when (as is the case for both the
interrupt-abort path and stale-call kill path) the helper runs on a
different thread than the one driving the request:

  * The Python ``socket.socket`` we close here is the SAME object held by
    httpx's pool, so closing it via Python sets its ``_fd`` to -1 and
    future operations on that Python object fail safely.
  * BUT the SSL wrapper (``ssl.SSLSocket``'s underlying OpenSSL ``BIO``)
    caches the raw integer FD. Once ``os.close(fd)`` runs, the kernel may
    immediately recycle that integer to the next ``open()`` call — e.g.
    the kanban dispatcher opening ``kanban.db``.
  * The owning worker thread then unwinds httpx, the SSL layer flushes a
    pending TLS record, and the encrypted bytes get written into the
    wrong file (issue #29507: 24-byte TLS application-data record
    clobbering SQLite header bytes 5..28).

The fix is to let the owning thread own the close. ``shutdown()`` from any
thread is FD-safe; ``close()`` is not. The httpx connection's own close
path — which runs from the worker thread when it unwinds — will release
the FD via the same ``socket.socket`` object, and because Python's socket
close atomically swaps ``_fd`` to -1 *before* issuing ``os.close``, there
is no FD-aliasing window when only one thread closes.

Returns the number of sockets shut down. (Field kept as
``tcp_force_closed=N`` in the log line for backwards-compatible parsing.)


## agent.anthropic_adapter

### 模块文档

Anthropic Messages API adapter for Hermes Agent.

Translates between Hermes's internal OpenAI-style message format and
Anthropic's Messages API. Follows the same pattern as the codex_responses
adapter — all provider-specific logic is isolated here.

Auth supports:
  - Regular API keys (sk-ant-api*) → x-api-key header
  - OAuth setup-tokens (sk-ant-oat*) → Bearer auth + beta header
  - Claude Code credentials (~/.claude.json or ~/.claude/.credentials.json) → Bearer auth

### 顶层函数

#### def `build_anthropic_client(api_key, base_url: str = None, timeout: float = None, drop_context_1m_beta: bool = False)`

Create an Anthropic client, auto-detecting setup-tokens vs API keys.

``api_key`` accepts either:

* a static ``str`` — the historical contract for all key-based and
  OAuth flows.
* a ``Callable[[], str]`` — an Entra ID bearer token provider from
  :mod:`agent.azure_identity_adapter`. The Anthropic SDK itself
  requires a static string, so when given a callable we construct
  a custom ``httpx.Client`` with a request event hook that mints a
  fresh JWT per outbound request and rewrites the ``Authorization``
  header. The SDK never sees the callable directly.

If *timeout* is provided it overrides the default 900s read timeout.  The
connect timeout stays at 10s.  Callers pass this from the per-provider /
per-model ``request_timeout_seconds`` config so Anthropic-native and
Anthropic-compatible providers respect the same knob as OpenAI-wire
providers.

``drop_context_1m_beta=True`` strips ``context-1m-2025-08-07`` from the
client-level ``anthropic-beta`` header. Used by the reactive OAuth retry
path in ``run_agent.py`` when a subscription rejects the beta; leave at
its default on fresh clients so 1M-capable subscriptions keep the
capability.

Returns an anthropic.Anthropic instance.

**异常**: `ImportError`

#### def `build_anthropic_bedrock_client(region: str)`

Create an AnthropicBedrock client for Bedrock Claude models.

Uses the Anthropic SDK's native Bedrock adapter, which provides full
Claude feature parity: prompt caching, thinking budgets, adaptive
thinking, fast mode — features not available via the Converse API.

Attaches the common Anthropic beta headers as client-level defaults so
that Bedrock-hosted Claude models get the same enhanced features as
native Anthropic. The ``context-1m-2025-08-07`` beta in particular
unlocks the 1M context window for Opus 4.6/4.7 on Bedrock — without
it, Bedrock caps these models at 200K even though the Anthropic API
serves them with 1M natively.

Auth uses the boto3 default credential chain (IAM roles, SSO, env vars).

**异常**: `ImportError`

#### def `read_claude_code_credentials() -> Optional[Dict[str, Any]]`

Read refreshable Claude Code OAuth credentials.

Reads from two possible sources and reconciles them:
  1. macOS Keychain (Darwin only) — "Claude Code-credentials" entry
  2. ~/.claude/.credentials.json file

Selection rules when both are present:
  - If exactly one is non-expired, prefer that one. (Handles the case
    where Claude Code refreshes one source but not the other — observed
    in the wild on Claude Code 2.1.x.)
  - Otherwise, prefer the source with the later ``expiresAt`` so that
    any subsequent refresh uses the most recent ``refreshToken``.

This intentionally excludes ~/.claude.json primaryApiKey. Opencode's
subscription flow is OAuth/setup-token based with refreshable credentials,
and native direct Anthropic provider usage should follow that path rather
than auto-detecting Claude's first-party managed key.

Returns dict with {accessToken, refreshToken?, expiresAt?, source} or None.

#### def `is_claude_code_token_valid(creds: Dict[str, Any]) -> bool`

Check if Claude Code credentials have a non-expired access token.

#### def `refresh_anthropic_oauth_pure(refresh_token: str, use_json: bool = False) -> Dict[str, Any]`

Refresh an Anthropic OAuth token without mutating local credential files.

**异常**: `ValueError`, `last_error`

#### def `resolve_anthropic_token() -> Optional[str]`

Resolve an Anthropic token from all available sources.

Priority:
  1. ANTHROPIC_TOKEN env var (OAuth/setup token saved by Hermes)
  2. CLAUDE_CODE_OAUTH_TOKEN env var
  3. Claude Code credentials (~/.claude.json or ~/.claude/.credentials.json)
     — with automatic refresh if expired and a refresh token is available
  4. Anthropic credential_pool OAuth entry (~/.hermes/auth.json)
  5. ANTHROPIC_API_KEY env var (regular API key, or legacy fallback)

Returns the token string or None.

#### def `run_oauth_setup_token() -> Optional[str]`

Run 'claude setup-token' interactively and return the resulting token.

Checks multiple sources after the subprocess completes:
  1. Claude Code credential files (may be written by the subprocess)
  2. CLAUDE_CODE_OAUTH_TOKEN / ANTHROPIC_TOKEN env vars

Returns the token string, or None if no credentials were obtained.
Raises FileNotFoundError if the 'claude' CLI is not installed.

**异常**: `FileNotFoundError`

#### def `run_hermes_oauth_login_pure() -> Optional[Dict[str, Any]]`

Run Hermes-native OAuth PKCE flow and return credential state.

#### def `read_hermes_oauth_credentials() -> Optional[Dict[str, Any]]`

Read Hermes-managed OAuth credentials from ~/.hermes/.anthropic_oauth.json.

#### def `normalize_model_name(model: str, preserve_dots: bool = False) -> str`

Normalize a model name for the Anthropic API.

- Strips 'anthropic/' prefix (OpenRouter format, case-insensitive)
- Converts dots to hyphens in version numbers (OpenRouter uses dots,
  Anthropic uses hyphens: claude-opus-4.6 → claude-opus-4-6), unless
  preserve_dots is True (e.g. for Alibaba/DashScope: qwen3.5-plus).
- Preserves Bedrock model IDs (``anthropic.claude-opus-4-7``) and
  regional inference profiles (``us.anthropic.claude-*``) whose dots
  are namespace separators, not version separators.

#### def `convert_tools_to_anthropic(tools: List[Dict]) -> List[Dict]`

Convert OpenAI tool definitions to Anthropic format.

#### def `convert_messages_to_anthropic(messages: List[Dict], base_url: str | None = None, model: str | None = None) -> Tuple[Optional[Any], List[Dict]]`

Convert OpenAI-format messages to Anthropic format.

Returns (system_prompt, anthropic_messages).
System messages are extracted since Anthropic takes them as a separate param.
system_prompt is a string or list of content blocks (when cache_control present).

When *base_url* is provided and points to a third-party Anthropic-compatible
endpoint, all thinking block signatures are stripped.  Signatures are
Anthropic-proprietary — third-party endpoints cannot validate them and will
reject them with HTTP 400 "Invalid signature in thinking block".

When *model* is provided and matches the Kimi / Moonshot family (or
*base_url* is a Kimi / Moonshot host), unsigned thinking blocks
synthesised from ``reasoning_content`` are preserved on replayed
assistant tool-call messages — Kimi requires the field to exist, even
if empty.

#### def `build_anthropic_kwargs(model: str, messages: List[Dict], tools: Optional[List[Dict]], max_tokens: Optional[int], reasoning_config: Optional[Dict[str, Any]], tool_choice: Optional[str] = None, is_oauth: bool = False, preserve_dots: bool = False, context_length: Optional[int] = None, base_url: str | None = None, fast_mode: bool = False, drop_context_1m_beta: bool = False) -> Dict[str, Any]`

Build kwargs for anthropic.messages.create().

Naming note — two distinct concepts, easily confused:
  max_tokens     = OUTPUT token cap for a single response.
                   Anthropic's API calls this "max_tokens" but it only
                   limits the *output*.  Anthropic's own native SDK
                   renamed it "max_output_tokens" for clarity.
  context_length = TOTAL context window (input tokens + output tokens).
                   The API enforces: input_tokens + max_tokens ≤ context_length.
                   Stored on the ContextCompressor; reduced on overflow errors.

When *max_tokens* is None the model's native output ceiling is used
(e.g. 128K for Opus 4.6, 64K for Sonnet 4.6).

When *context_length* is provided and the model's native output ceiling
exceeds it (e.g. a local endpoint with an 8K window), the output cap is
clamped to context_length − 1.  This only kicks in for unusually small
context windows; for full-size models the native output cap is always
smaller than the context window so no clamping happens.
NOTE: this clamping does not account for prompt size — if the prompt is
large, Anthropic may still reject the request.  The caller must detect
"max_tokens too large given prompt" errors and retry with a smaller cap
(see parse_available_output_tokens_from_error + _ephemeral_max_output_tokens).

When *is_oauth* is True, applies Claude Code compatibility transforms:
system prompt prefix, tool name prefixing, and prompt sanitization.

When *preserve_dots* is True, model name dots are not converted to hyphens
(for Alibaba/DashScope anthropic-compatible endpoints: qwen3.5-plus).

When *base_url* points to a third-party Anthropic-compatible endpoint,
thinking block signatures are stripped (they are Anthropic-proprietary).

When *fast_mode* is True, adds ``extra_body["speed"] = "fast"`` and the
fast-mode beta header for ~2.5x faster output throughput on Opus 4.6.
Currently only supported on native Anthropic endpoints (not third-party
compatible ones).

#### def `sanitize_anthropic_kwargs(api_kwargs: Any, log_prefix: str = '') -> Any`

Drop Responses-API-only keys before an Anthropic Messages SDK call.

Defensive boundary guard for #31673: under rare api_mode-flip races
(e.g. a concurrent auxiliary call mutating a shared agent between the
kwargs build and the stream dispatch), a Responses-shaped payload
carrying ``instructions=`` can reach ``messages.stream()`` /
``messages.create()``. The Anthropic SDK rejects it with a
non-retryable ``TypeError`` that nukes the whole turn and propagates
the entire fallback chain.

Mutates ``api_kwargs`` in place and returns it. When a foreign key is
present we log a WARNING so the underlying race stays visible in the
wild instead of being silently papered over.

#### def `create_anthropic_message(client: Any, api_kwargs: dict, log_prefix: str = '', prefer_stream: bool = True) -> Any`

Create an Anthropic message, aggregating via stream when available.

Some Anthropic-compatible gateways are SSE-only: they ignore non-streaming
requests and return ``text/event-stream`` even for ``messages.create()``.
The SDK can surface that as raw text, so callers that expect a Message then
crash on ``.content``.  Prefer ``messages.stream().get_final_message()`` to
match the main turn path, falling back to ``create()`` only for providers
that explicitly do not support streaming, such as restricted Bedrock roles.


## agent.async_utils

### 模块文档

Async/sync bridging helpers.

The codebase has ~30 sites that schedule a coroutine onto an event loop from a
worker thread via :func:`asyncio.run_coroutine_threadsafe`.  That function can
raise :class:`RuntimeError` (e.g. the loop was closed during a shutdown race),
and when it does the coroutine object is never awaited and never closed —
which triggers a ``"coroutine '<name>' was never awaited"`` RuntimeWarning and
leaks the coroutine's frame until GC.

:func:`safe_schedule_threadsafe` wraps the call, closes the coroutine on
scheduling failure, and returns ``None`` (instead of a half-formed future) so
callers can branch cleanly:

    fut = safe_schedule_threadsafe(coro, loop)
    if fut is None:
        return  # or fallback behavior
    fut.result(timeout=5)

The helper deliberately does NOT also handle ``future.result()`` failures —
that is a separate concern.  Once the loop has accepted the coroutine, its
lifecycle belongs to the loop, not the scheduling thread.

### 顶层函数

#### def `safe_schedule_threadsafe(coro: Coroutine[Any, Any, Any], loop: Optional[asyncio.AbstractEventLoop], logger: Optional[logging.Logger] = None, log_message: str = 'Failed to schedule coroutine on loop', log_level: int = logging.DEBUG) -> Optional[Future]`

Schedule ``coro`` on ``loop`` from a sync context, leak-safe.

Returns the :class:`concurrent.futures.Future` on success, or ``None`` if
the loop is missing or :func:`asyncio.run_coroutine_threadsafe` raised
(e.g. the loop was closed during a shutdown race).  In all failure paths
the coroutine is :meth:`close`-d so it does not trigger
``"coroutine was never awaited"`` warnings or leak its frame.

Callers retain full control over what to do with the returned future
(call ``.result(timeout=...)``, attach ``add_done_callback``, ignore it
fire-and-forget, etc.).

#### def `consume_detached_task_result(task: asyncio.Future[Any]) -> None`

Retrieve a detached task's result without surfacing cancellation.

Used as an ``add_done_callback`` on tasks that were cancelled and
detached (e.g. an adapter close path that swallows ``CancelledError``
past its teardown deadline). Observing ``task.exception()`` prevents
"exception was never retrieved" noise on the event loop; cancellation
and any terminal error are deliberately swallowed — the task's owner
already gave up on it.


## agent.aux_accounting

### 模块文档

Ambient session-accounting context for auxiliary LLM calls.

Auxiliary calls (vision, compression, title generation, web_extract,
session_search, ...) funnel through ``agent.auxiliary_client`` which has no
session handle — so their token usage was historically discarded, leaving
dashboard analytics blind to aux model spend (issue #23270).

Instead of threading ``session_db``/``session_id`` parameters through every
aux call site, the agent loop publishes them here (mirroring the Nous Portal
conversation context in ``agent.portal_tags``) and the auxiliary client
records usage at its single response-validation chokepoint.

ContextVar semantics give us the right isolation for free:

* concurrent agents in one process (gateway sessions, delegate subagents)
  never see each other's accounting context;
* worker threads spawned via ``tools.thread_context.propagate_context_to_thread``
  (MoA fan-out, background review) inherit the parent turn's context;
* asyncio tasks inherit the context of the code that created them.

MoA reference/aggregator slots are explicitly EXCLUDED from recording:
``agent/conversation_loop.py`` already folds MoA advisor usage and cost into
the main loop's ``update_token_counts`` delta, so recording them here would
double-count (see ``_EXCLUDED_TASKS``).

### 顶层函数

#### def `set_accounting_context(session_db: Any, session_id: Optional[str])`

Publish the active session's accounting handles for aux usage recording.

Called by the agent loop at turn entry. Returns the ContextVar token so
callers can ``reset_accounting_context(token)`` on turn exit. Publishing
``None`` handles (no DB / no session id) clears the context.

#### def `reset_accounting_context(token) -> None`

Restore the previous accounting context (pair with ``set_...``).

#### def `get_accounting_context() -> Optional[tuple]`

Return ``(session_db, session_id)`` for the active turn, or ``None``.

#### def `record_aux_usage(response: Any, task: Optional[str], provider: Optional[str] = None, base_url: Optional[str] = None) -> None`

Record an auxiliary response's token usage against the ambient session.

Called from the auxiliary client's response-validation chokepoint. Strictly
best-effort: any failure is swallowed (accounting must never break an aux
call). No-ops when:

* no accounting context is published (call is outside any agent turn),
* the task is main-loop-accounted (MoA slots — see ``_EXCLUDED_TASKS``),
* the response carries no usage object.

The model is read from ``response.model`` (accurate even after the aux
client's provider-fallback chains); *provider*/*base_url* reflect the
originally-resolved route and are best-effort.


## agent.auxiliary_client

### 模块文档

Shared auxiliary client router for side tasks.

Provides a single resolution chain so every consumer (context compression,
session search, web extraction, vision analysis, browser vision) picks up
the best available backend without duplicating fallback logic.

Resolution order for text tasks (auto mode):
  1. User's main provider + main model (used regardless of provider type —
     aggregators, direct API-key providers, native Anthropic, Codex, etc.)
  2. OpenRouter  (OPENROUTER_API_KEY)
  3. Nous Portal (~/.hermes/auth.json active provider)
  4. Custom endpoint (config.yaml model.base_url + OPENAI_API_KEY)
  5. Native Anthropic
  6. Direct API-key providers (z.ai/GLM, Kimi/Moonshot, MiniMax, MiniMax-CN)
  7. None

Resolution order for vision/multimodal tasks (auto mode):
  1. Selected main provider, if it is one of the supported vision backends below
  2. OpenRouter
  3. Nous Portal
  4. Native Anthropic
  5. Custom endpoint (for local vision models: Qwen-VL, LLaVA, Pixtral, etc.)
  6. None

Codex OAuth (ChatGPT-account auth) is intentionally NOT in either
fallback chain: OpenAI gates this endpoint behind an undocumented,
shifting model allow-list, so "just try Codex with a hardcoded model"
rots on its own.  Codex is used only when the user's main provider *is*
openai-codex (Step 1 above) or when a caller explicitly requests it with
a model (auxiliary.<task>.provider + auxiliary.<task>.model).

Per-task overrides are configured in config.yaml under the ``auxiliary:`` section
(e.g. ``auxiliary.vision.provider``, ``auxiliary.compression.model``).
Default "auto" follows the chains above.

Payment / credit exhaustion fallback:
  When a resolved provider returns HTTP 402 or a credit-related error,
  call_llm() automatically retries with the next available provider in the
  auto-detection chain.  This handles the common case where a user depletes
  their OpenRouter balance but has Codex OAuth or another provider available.

### class CodexAuxiliaryClient

> 继承: `object` ｜ 方法数: 2（公开 1）

OpenAI-client-compatible wrapper that routes through Codex Responses API.

Consumers can call client.chat.completions.create(**kwargs) as normal.
Also exposes .api_key and .base_url for introspection by async wrappers.

#### def `__init__(real_client: OpenAI, model: str)`

#### def `close(self)`


### class AsyncCodexAuxiliaryClient

> 继承: `object` ｜ 方法数: 1（公开 0）

Async-compatible wrapper matching AsyncOpenAI.chat.completions.create().

#### def `__init__(sync_wrapper: CodexAuxiliaryClient)`


### class AnthropicAuxiliaryClient

> 继承: `object` ｜ 方法数: 2（公开 1）

OpenAI-client-compatible wrapper over a native Anthropic client.

#### def `__init__(real_client: Any, model: str, api_key: str, base_url: str, is_oauth: bool = False)`

#### def `close(self)`


### class AsyncAnthropicAuxiliaryClient

> 继承: `object` ｜ 方法数: 1（公开 0）

#### def `__init__(sync_wrapper: AnthropicAuxiliaryClient)`


### class BedrockAuxiliaryClient

> 继承: `object` ｜ 方法数: 2（公开 1）

OpenAI-client-compatible wrapper over AWS Bedrock Converse API.

#### def `__init__(region: str, model: str)`

#### def `close(self)`


### class AsyncBedrockAuxiliaryClient

> 继承: `object` ｜ 方法数: 1（公开 0）

#### def `__init__(sync_wrapper: BedrockAuxiliaryClient)`


### 顶层函数

#### def `aux_interrupt_protection(active: bool = True)`

Mark the current thread's auxiliary LLM call as interrupt-protected.

Used by atomic aux tasks (compression) so a mid-flight gateway interrupt
doesn't abort the call and trigger a degraded fallback. Re-entrant-safe:
restores the previous value on exit.

#### def `build_or_headers(or_config: dict | None = None) -> dict`

Build OpenRouter headers, optionally including response-cache headers.

Precedence for response cache: env var > config.yaml > default (enabled).

Environment variables:
    ``HERMES_OPENROUTER_CACHE`` — truthy (``1``/``true``/``yes``/``on``)
        enables caching; ``0``/``false``/``no``/``off`` disables.
        Overrides ``openrouter.response_cache`` in config.yaml.
    ``HERMES_OPENROUTER_CACHE_TTL`` — integer seconds (1-86400).
        Overrides ``openrouter.response_cache_ttl`` in config.yaml.

*or_config* is the ``openrouter`` section from config.yaml.  When *None*,
falls back to reading config from disk via ``load_config()``.

#### def `build_nvidia_nim_headers(base_url: str | None) -> dict`

Return NVIDIA NIM cloud attribution headers for build.nvidia.com traffic.

#### def `set_runtime_main(provider: str, model: str, base_url: str = '', api_key: Any = '', api_mode: str = '', auth_mode: str = '') -> contextvars.Token`

Record the current context's live main runtime for auxiliary routing.

Context-local state prevents concurrent gateway sessions from overwriting
one another while retaining compatibility mirrors for legacy readers.

#### def `reset_runtime_main(token: contextvars.Token) -> None`

Restore the runtime binding that preceded one scoped turn.

#### def `scoped_runtime_main(main_runtime: Optional[Dict[str, Any]])`

Temporarily bind an explicit runtime without touching legacy mirrors.

#### def `clear_runtime_main() -> None`

Clear the runtime override in the current context.

#### def `resolve_provider_client(provider: str, model: str = None, async_mode: bool = False, raw_codex: bool = False, explicit_base_url: str = None, explicit_api_key: str = None, api_mode: str = None, main_runtime: Optional[Dict[str, Any]] = None, is_vision: bool = False, task: Optional[str] = None) -> Tuple[Optional[Any], Optional[str]]`

Central router: given a provider name and optional model, return a
configured client with the correct auth, base URL, and API format.

The returned client always exposes ``.chat.completions.create()`` — for
Codex/Responses API providers, an adapter handles the translation
transparently.

Args:
    provider: Provider identifier.  One of:
        "openrouter", "nous", "openai-codex" (or "codex"),
        "zai", "kimi-coding", "minimax", "minimax-cn",
        "custom" (OPENAI_BASE_URL + OPENAI_API_KEY),
        "auto" (full auto-detection chain).
    model: Model slug override.  If None, uses the provider's default
           auxiliary model.
    async_mode: If True, return an async-compatible client.
    raw_codex: If True, return a raw OpenAI client for Codex providers
        instead of wrapping in CodexAuxiliaryClient.  Use this when
        the caller needs direct access to responses.stream() (e.g.,
        the main agent loop).
    explicit_base_url: Optional direct OpenAI-compatible endpoint.
    explicit_api_key: Optional API key paired with explicit_base_url.
    api_mode: API mode override.  One of "chat_completions",
        "codex_responses", or None (auto-detect).  When set to
        "codex_responses", the client is wrapped in
        CodexAuxiliaryClient to route through the Responses API.

Returns:
    (client, resolved_model) or (None, None) if auth is unavailable.

#### def `get_text_auxiliary_client(task: str = '', main_runtime: Optional[Dict[str, Any]] = None) -> Tuple[Optional[OpenAI], Optional[str]]`

Return (client, default_model_slug) for text-only auxiliary tasks.

Args:
    task: Optional task name ("compression", "web_extract") to check
          for a task-specific provider override.

Callers may override the returned model via config.yaml
(e.g. auxiliary.compression.model, auxiliary.web_extract.model).

#### def `get_async_text_auxiliary_client(task: str = '', main_runtime: Optional[Dict[str, Any]] = None)`

Return (async_client, model_slug) for async consumers.

For standard providers returns (AsyncOpenAI, model). For Codex returns
(AsyncCodexAuxiliaryClient, model) which wraps the Responses API.
Returns (None, None) when no provider is available.

#### def `get_available_vision_backends() -> List[str]`

Return the currently available vision backends in auto-selection order.

Order: active provider → OpenRouter → Nous → stop.  This is the single
source of truth for setup, tool gating, and runtime auto-routing of
vision tasks.

#### def `resolve_vision_provider_client(provider: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None, async_mode: bool = False, main_runtime: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Optional[Any], Optional[str]]`

Resolve the client actually used for vision tasks.

Direct endpoint overrides take precedence over provider selection. Explicit
provider overrides still use the generic provider router for non-standard
backends, so users can intentionally force experimental providers. Auto mode
stays conservative and only tries vision backends known to work today.

#### def `get_auxiliary_extra_body() -> dict`

Return extra_body kwargs for auxiliary API calls.

Includes Nous Portal product tags when the auxiliary client is backed
by Nous Portal. Returns empty dict otherwise.

#### def `auxiliary_max_tokens_param(value: int, model: Optional[str] = None) -> dict`

Return the correct max tokens kwarg for the auxiliary client's provider.

OpenRouter and local models use 'max_tokens'. Direct OpenAI with newer
models (gpt-4o, gpt-4.1, gpt-5+, o-series) requires 'max_completion_tokens'.
The Codex adapter translates max_tokens internally, so we use max_tokens
for it as well. Pass ``model`` so third-party OpenAI-compatible endpoints
fronting the newer families are also recognised — URL-only detection
misses the case where a custom base URL serves e.g. ``gpt-5.4``.

#### def `neuter_async_httpx_del() -> None`

Monkey-patch ``AsyncHttpxClientWrapper.__del__`` to be a no-op.

The OpenAI SDK's ``AsyncHttpxClientWrapper.__del__`` schedules
``self.aclose()`` via ``asyncio.get_running_loop().create_task()``.
When an ``AsyncOpenAI`` client is garbage-collected while
prompt_toolkit's event loop is running (the common CLI idle state),
the ``aclose()`` task runs on prompt_toolkit's loop but the
underlying TCP transport is bound to a *different* loop (the worker
thread's loop that the client was originally created on).  If that
loop is closed or its thread is dead, the transport's
``self._loop.call_soon()`` raises ``RuntimeError("Event loop is
closed")``, which prompt_toolkit surfaces as "Unhandled exception
in event loop ... Press ENTER to continue...".

Neutering ``__del__`` is safe because:
- Cached clients are explicitly cleaned via ``_force_close_async_httpx``
  on stale-loop detection and ``shutdown_cached_clients`` on exit.
- Uncached clients' TCP connections are cleaned up by the OS when the
  process exits.
- The OpenAI SDK itself marks this as a TODO (``# TODO(someday):
  support non asyncio runtimes here``).

Call this once at CLI startup, before any ``AsyncOpenAI`` clients are
created.

#### def `shutdown_cached_clients() -> None`

Close all cached clients (sync and async) to prevent event-loop errors.

Call this during CLI shutdown, *before* the event loop is closed, to
avoid ``AsyncHttpxClientWrapper.__del__`` raising on a dead loop.

#### def `cleanup_stale_async_clients() -> None`

Force-close cached async clients whose event loop is closed.

Call this after each agent turn to proactively clean up stale clients
before GC can trigger ``AsyncHttpxClientWrapper.__del__`` on them.
This is defense-in-depth — the primary fix is ``neuter_async_httpx_del``
which disables ``__del__`` entirely.

#### def `call_llm(task: str = None, provider: str = None, model: str = None, base_url: str = None, api_key: str = None, main_runtime: Optional[Dict[str, Any]] = None, messages: list, temperature: Optional[float] = None, max_tokens: int = None, tools: list = None, timeout: float = None, extra_body: dict = None, reasoning_config: Optional[dict] = None, api_mode: str = None, stream: bool = False, stream_options: dict = None) -> Any`

Centralized synchronous LLM call.

Resolves provider + model (from task config, explicit args, or auto-detect),
handles auth, request formatting, and model-specific arg adjustments.

Args:
    task: Auxiliary task name ("compression", "vision", "web_extract",
          "session_search", "skills_hub", "mcp", "title_generation").
          Reads provider:model from config/env. Ignored if provider is set.
    provider: Explicit provider override.
    model: Explicit model override.
    api_mode: Explicit API mode override (e.g. "codex_responses",
          "anthropic_messages"). Takes precedence over task config.
    messages: Chat messages list.
    temperature: Sampling temperature (None = provider default).
    max_tokens: Max output tokens (handles max_tokens vs max_completion_tokens).
    tools: Tool definitions (for function calling).
    timeout: Request timeout in seconds (None = read from auxiliary.{task}.timeout config).
    extra_body: Additional request body fields.
    reasoning_config: Optional Hermes reasoning config for direct model calls
          such as MoA reference/aggregator slots.
    stream: When True, return the raw SDK streaming iterator instead of a
        validated complete response. The caller is responsible for consuming
        chunks (and for any fallback). Used by the MoA aggregator so its
        output can stream to the user.
    stream_options: Passed through to the request when stream is True
        (e.g. {"include_usage": True}).

Returns:
    Response object with .choices[0].message.content, OR — when stream=True —
    the raw streaming iterator from client.chat.completions.create().

Raises:
    RuntimeError: If no provider is configured.

**异常**: `RuntimeError`, `_last_transient`

#### def `extract_content_or_reasoning(response) -> str`

Extract content from an LLM response, falling back to reasoning fields.

Mirrors the main agent loop's behavior when a reasoning model (DeepSeek-R1,
Qwen-QwQ, etc.) returns ``content=None`` with reasoning in structured fields.

Resolution order:
  1. ``message.content`` — strip inline think/reasoning blocks, check for
     remaining non-whitespace text.
  2. ``message.reasoning`` / ``message.reasoning_content`` — direct
     structured reasoning fields (DeepSeek, Moonshot, NovitaAI, etc.).
  3. ``message.reasoning_details`` — OpenRouter unified array format.

Returns the best available text, or ``""`` if nothing found.

#### def `async_call_llm(task: str = None, provider: str = None, model: str = None, base_url: str = None, api_key: str = None, main_runtime: Optional[Dict[str, Any]] = None, messages: list, temperature: Optional[float] = None, max_tokens: int = None, tools: list = None, timeout: float = None, extra_body: dict = None, reasoning_config: Optional[dict] = None) -> Any`

Centralized asynchronous LLM call.

Same as call_llm() but async. See call_llm() for full documentation.

**异常**: `RuntimeError`


## agent.azure_identity_adapter

### 模块文档

Microsoft Entra ID adapter for Microsoft Foundry.

Provides keyless authentication for Microsoft Foundry deployments using the
`azure-identity` SDK's `DefaultAzureCredential` chain (env service principal
→ workload identity → managed identity → VS Code → Azure CLI → azd →
PowerShell → broker).

Architecture mirrors `agent/bedrock_adapter.py`:

* Lazy import. `azure-identity` is only loaded when ``model.auth_mode =
  entra_id`` is selected. Users who stick with `AZURE_FOUNDRY_API_KEY`
  never pay the import cost.
* SDK-callable contract. The public entry point ``build_token_provider``
  returns a zero-arg callable produced by ``get_bearer_token_provider`` —
  this is exactly the value Microsoft's documented sample plugs into
  ``OpenAI(api_key=token_provider, base_url=...)``. The OpenAI SDK calls
  it before every request, so token refresh is transparent.
* Three explicit consumer-side helpers (display / cache / http-bearer)
  rather than one generic "materialize" function — splitting them by
  purpose prevents accidental token-minting in logging paths or token
  leakage into cache keys / dashboard JSON.
* No persisted JWT. ``azure-identity`` caches in-process and (where
  available) in the OS keychain or ``~/.IdentityService``. Hermes does
  not duplicate that storage in ``auth.json``.

Reference: https://learn.microsoft.com/azure/ai-foundry/foundry-models/how-to/configure-entra-id

Requires: ``azure-identity`` (optional dependency — only needed when
``model.auth_mode = entra_id``).

### class EntraIdentityConfig

> 继承: `object` ｜ 方法数: 3（公开 2）

Serializable Entra ID config.

Captures the Hermes-managed Entra knobs we need outside Azure SDK
environment configuration. Everything else
(tenant ID, service principal secret, federated token file, sovereign
cloud authority, etc.) flows through azure-identity's standard
``AZURE_*`` env vars — see the Bedrock pattern in
``hermes_cli/runtime_provider.py:1310-1377`` for the analogous
"let the SDK read env" approach.

``scope`` is Microsoft's documented Foundry inference audience. Almost
everyone uses the default; sovereign-cloud / non-standard tenants can
override via ``model.entra.scope``. Identity selection (user-assigned
managed identity, workload identity, service principal, tenant, authority)
stays in the standard Azure SDK env vars such as ``AZURE_CLIENT_ID``.

``exclude_interactive_browser`` is kept as an internal constructor knob
so probes stay non-interactive by default. It is not written by the setup
wizard.

The dataclass is frozen so it's hashable for ``functools.lru_cache``
keying, and serializable across multiprocessing boundaries (workers
rebuild the credential inside their own process).

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Optional[Dict[str, Any]], default_scope: Optional[str] = None) -> EntraIdentityConfig`


### 顶层函数

#### def `has_azure_identity_installed() -> bool`

Return True if `azure-identity` can be imported right now.

Cheap check — does not walk the credential chain.

#### def `reset_credential_cache() -> None`

Clear the cached ``DefaultAzureCredential``. Used by tests and
profile switches.

Defensive against tests that ``monkeypatch.setattr`` over
``build_credential`` with a plain (non-lru-cached) function — those
won't expose ``cache_clear()`` until pytest reverts the patch.

#### def `build_credential(config: EntraIdentityConfig) -> Any`

Return the cached ``DefaultAzureCredential`` for ``config``.

Hermes processes use exactly one Entra config at a time (the
``model.entra.*`` block in config.yaml drives every aux task,
subagent, and credential probe in the session). ``maxsize=1`` is
intentional: it reflects the actual usage pattern and keeps the
cache trivially small.

``EntraIdentityConfig`` is a frozen dataclass, so it's hashable and
safe as an LRU-cache key. ``functools.lru_cache`` is thread-safe in
CPython.

If two distinct configs are ever passed (tests do this; production
rarely), the LRU eviction handles it correctly — each call still
returns a credential matching its config; only one is cached at a
time. Use :func:`reset_credential_cache` to clear (e.g. in tests).

#### def `build_token_provider(scope: Optional[str] = None, config: Optional[EntraIdentityConfig] = None, base_url: Optional[str] = None, exclude_interactive_browser: bool = True) -> Callable[[], str]`

Return a zero-arg callable that mints a fresh Entra bearer JWT.

The returned callable is exactly what Microsoft's documented Foundry
sample expects::

    from openai import OpenAI
    client = OpenAI(
        base_url="https://my-resource.openai.azure.com/openai/v1/",
        api_key=build_token_provider(),
    )

Scope resolution order:
  1. ``config.scope`` when a config object is supplied
  2. explicit ``scope`` kwarg
  3. ``SCOPE_AI_AZURE_DEFAULT`` (Microsoft's documented Foundry scope)

``base_url`` is unused today and kept for back-compat. Tenant /
service-principal / sovereign-cloud configuration flows through
``azure-identity``'s standard ``AZURE_*`` environment variables —
see :func:`_build_default_credential` for the rationale.

NOT serializable across process boundaries. For multiprocessing
workers, serialize the ``EntraIdentityConfig`` and rebuild the
provider inside the worker.

#### def `has_azure_identity_credentials(scope: Optional[str] = None, config: Optional[EntraIdentityConfig] = None, timeout_seconds: float = 10.0, allow_install: bool = True, **overrides: Any) -> bool`

Best-effort probe: can `DefaultAzureCredential` mint a token now?

Runs ``credential.get_token(scope)`` under a thread-based timeout so
a slow token service can't hang the caller. Returns False on any
error — never raises. Use for ``hermes doctor`` /
``hermes auth status`` / wizard preflight.

``allow_install``: when True (default) and ``azure-identity`` is not
importable, the adapter triggers the standard lazy-install path
(subject to ``security.allow_lazy_installs``) before probing. Set
False to make this strictly an "is installed?" check — used on hot
paths like CLI startup where we never want pip to run.

NOT used by ``is_provider_configured()`` — that path is structural
only (no token mint), so CLI startup doesn't pay this latency.

#### def `describe_active_credential(config: Optional[EntraIdentityConfig] = None, scope: Optional[str] = None, timeout_seconds: float = 10.0, allow_install: bool = True, **overrides: Any) -> Dict[str, Any]`

Return diagnostic info about the active credential chain.

Best-effort: runs ``get_token()`` and inspects what came back.
Designed for ``hermes doctor`` and the wizard preflight — never
raises, returns ``{"ok": False, "error": ...}`` on failure.

``allow_install``: when True (default) and ``azure-identity`` is not
importable, the adapter triggers the standard lazy-install path
(subject to ``security.allow_lazy_installs``) before probing. The
install failure is surfaced as the diagnostic error when it fails.
Set False for hot CLI paths that should never trigger pip.

``azure-identity`` doesn't expose the winning inner credential as
a public field, so we report a coarse picture (env vars present,
token expiry, claims-derived tenant) rather than the credential
class name. Users wanting the precise class can run with
``AZURE_LOG_LEVEL=DEBUG``.

#### def `is_token_provider(value: Any) -> bool`

Return True when ``value`` is a callable Entra token provider.

Used at the seams where a consumer must decide between
string-API-key semantics and bearer-callable semantics.

#### def `materialize_bearer_for_http(value: Any) -> str`

Return a fresh Bearer JWT for a manual HTTP request.

Only call this at sites that must construct an ``Authorization``
header outside the OpenAI SDK (e.g. ``hermes_cli/azure_detect.py``).
Calls the callable exactly once and returns the resulting token.

**Anthropic SDK integration:** the Anthropic Python SDK does not
accept a ``Callable[[], str]`` for ``auth_token``. Instead,
:func:`build_bearer_http_client` returns an ``httpx.Client`` whose
request event hook calls this function and rewrites the
``Authorization`` header per request — and that client is passed to
the Anthropic SDK via ``http_client=...``. See
:func:`agent.anthropic_adapter.build_anthropic_client` for the
consumer.

Raises ``ValueError`` if ``value`` is not a callable token provider
or non-empty string.

**异常**: `ValueError`

#### def `build_bearer_http_client(token_provider: Callable[[], str], **httpx_kwargs: Any) -> Any`

Return an ``httpx.Client`` that mints a fresh Entra bearer JWT
per outbound request.

The Anthropic SDK (≤ 0.86.0 at the time of writing) stores
``api_key`` / ``auth_token`` as static strings and computes the
``Authorization`` header at construction time. To get per-request
token refresh (the Microsoft-recommended Foundry pattern for
callable bearer providers), we install an httpx ``request`` event
hook on a custom client and pass that client to the SDK via
``http_client=...``. The hook:

  1. Calls :func:`materialize_bearer_for_http` to mint a fresh JWT
     (azure-identity caches internally — this is cheap when the
     cached token is still valid).
  2. Strips any pre-set ``Authorization`` / ``api-key`` /
     ``x-api-key`` headers the SDK may have added (avoids
     conflicting auth values).
  3. Sets ``Authorization: Bearer <fresh-jwt>``.

``token_provider`` must be a zero-arg callable returning a string —
typically the result of :func:`build_token_provider`.

``httpx_kwargs`` are forwarded verbatim to ``httpx.Client(...)`` so
callers can attach a ``timeout``, ``transport``, ``proxy``, etc.

Raises ``ImportError`` if ``httpx`` is not installed (it is a
transitive dependency of both ``openai`` and ``anthropic`` SDKs, so
in practice always available when this helper is reached).

**异常**: `ValueError`, `ImportError`


## agent.background_review

### 模块文档

Background memory/skill review — fork the agent to evaluate the turn.

After every turn, ``AIAgent.run_conversation`` may call
:func:`spawn_background_review` to fire off a daemon thread that replays
the conversation snapshot in a forked :class:`AIAgent` and asks itself
"should any skill/memory be saved or updated?".  Writes go straight to
the memory + skill stores.  Main conversation and prompt cache are never
touched.

The fork inherits the parent's live runtime (provider, model, base_url,
credentials, cached system prompt) so it hits the same prefix cache and
uses the same auth.  It runs with a tool whitelist limited to memory and
skill management tools; everything else is denied at runtime.

See the ``hermes-agent-dev`` skill (``references/self-improvement-loop.md``)
for invariants and PR review criteria.

### 顶层函数

#### def `summarize_background_review_actions(review_messages: List[Dict], prior_snapshot: List[Dict], notification_mode: str = 'on') -> List[str]`

Build the human-facing action summary for a background review pass.

Walks the review agent's session messages and collects successful memory
and skill-management actions to surface to the user. Tool messages already
present in ``prior_snapshot`` are skipped so stale inherited results are
not re-surfaced as fresh background work (issue #14944).

``notification_mode`` controls display detail:
- ``off``: return no actions.
- ``on``: generic "Memory updated"/tool messages.
- ``verbose``: include compact content previews from tool-call arguments.

#### def `build_memory_write_metadata(agent: Any, write_origin: Optional[str] = None, execution_context: Optional[str] = None, task_id: Optional[str] = None, tool_call_id: Optional[str] = None) -> Dict[str, Any]`

Build provenance metadata for external memory-provider mirrors.

#### def `spawn_background_review_thread(agent: Any, messages_snapshot: List[Dict], review_memory: bool = False, review_skills: bool = False)`

Build the review thread target and prompt for a background review.

Returns a ``(target, prompt)`` tuple.  The caller (``AIAgent._spawn_background_review``)
owns the actual ``threading.Thread`` construction so test-level patches
of ``run_agent.threading.Thread`` keep working.


## agent.bedrock_adapter

### 模块文档

AWS Bedrock Converse API adapter for Hermes Agent.

Provides native integration with Amazon Bedrock using the Converse API,
bypassing the OpenAI-compatible endpoint in favor of direct AWS SDK calls.
This enables full access to the Bedrock ecosystem:

  - **Native Converse API**: Unified interface for all Bedrock models
    (Claude, Nova, Llama, Mistral, etc.) with streaming support.
  - **AWS credential chain**: IAM roles, SSO profiles, environment variables,
    instance metadata — zero API key management for AWS-native environments.
  - **Dynamic model discovery**: Auto-discovers available foundation models
    and cross-region inference profiles via the Bedrock control plane.
  - **Guardrails support**: Optional Bedrock Guardrails configuration for
    content filtering and safety policies.
  - **Inference profiles**: Supports cross-region inference profiles
    (us.anthropic.claude-*, global.anthropic.claude-*) for better capacity
    and automatic failover.

Architecture follows the same pattern as ``anthropic_adapter.py``:
  - All Bedrock-specific logic is isolated in this module.
  - Messages/tools are converted between OpenAI format and Converse format.
  - Responses are normalized back to OpenAI-compatible objects for the agent loop.

Reference: OpenClaw's ``extensions/amazon-bedrock/`` plugin, which implements
the same Converse API integration in TypeScript via ``@aws-sdk/client-bedrock``.

Requires: ``boto3`` (optional dependency — only needed when using the Bedrock provider).

### 顶层函数

#### def `reset_client_cache()`

Clear cached boto3 clients. Used in tests and profile switches.

#### def `invalidate_runtime_client(region: str) -> bool`

Evict the cached ``bedrock-runtime`` client for a single region.

Per-region counterpart to :func:`reset_client_cache`. Used by the converse
call wrappers to discard clients whose underlying HTTP connection has
gone stale, so the next call allocates a fresh client (with a fresh
connection pool) instead of reusing a dead socket.

Returns True if a cached entry was evicted, False if the region was not
cached.

#### def `is_stale_connection_error(exc: BaseException) -> bool`

Return True if ``exc`` indicates a dead/stale Bedrock HTTP connection.

Matches:
  * ``botocore.exceptions.ConnectionError`` and subclasses
    (``ConnectionClosedError``, ``EndpointConnectionError``,
    ``ReadTimeoutError``, ``ConnectTimeoutError``).
  * ``urllib3.exceptions.ProtocolError`` / ``NewConnectionError`` /
    ``ConnectionError`` (best-effort import — urllib3 is a transitive
    dependency of botocore so it is always available in practice).
  * Bare ``AssertionError`` raised from a frame inside urllib3, botocore,
    or boto3. These are internal-invariant failures (typically triggered
    by corrupted connection-pool state after a dropped socket) and are
    recoverable by swapping the client.

Non-library ``AssertionError``s (from application code or tests) are
intentionally not matched — only library-internal asserts signal stale
connection state.

#### def `is_streaming_access_denied_error(exc: BaseException) -> bool`

Return True when AWS denied the ``bedrock:InvokeModelWithResponseStream`` action.

IAM policies scoped to ``bedrock:InvokeModel`` only (a common least-privilege
setup) reject ``converse_stream()`` with an ``AccessDeniedException`` whose
message names the streaming action, e.g.::

    User: arn:aws:iam::123456789012:user/x is not authorized to perform:
    bedrock:InvokeModelWithResponseStream on resource: ...

This is permanent for the session — retrying the stream can never succeed —
so callers should flip to the non-streaming ``converse()`` path (which maps
to ``bedrock:InvokeModel``) instead of burning retries.

Detection is deliberately message-based: boto3 surfaces this as a
``ClientError`` with ``Error.Code == "AccessDeniedException"``, and the
AnthropicBedrock SDK wraps the same AWS response in its own exception
types, but both preserve the action name in the message.

#### def `resolve_aws_auth_env_var(env: Optional[Dict[str, str]] = None) -> Optional[str]`

Return the name of the AWS auth source that is active, or None.

Checks environment variables first, then falls back to boto3's credential
chain for implicit sources (EC2 IMDS, ECS task role, etc.).

This mirrors OpenClaw's ``resolveAwsSdkEnvVarName()`` — used to detect
whether the user has any AWS credentials configured without actually
attempting to authenticate.

#### def `has_aws_credentials(env: Optional[Dict[str, str]] = None) -> bool`

Return True if any AWS credential source is detected.

Checks environment variables first (fast, no I/O), then falls back to
boto3's credential chain which covers EC2 instance roles, ECS task roles,
Lambda execution roles, and other IMDS-based sources that don't set
environment variables.

This two-tier approach mirrors the pattern from OpenClaw PR #62673:
cloud environments (EC2, ECS, Lambda) provide credentials via instance
metadata, not environment variables. The env-var check is a fast path
for local development; the boto3 fallback covers all cloud deployments.

#### def `resolve_bedrock_region(env: Optional[Dict[str, str]] = None) -> str`

Resolve the AWS region for Bedrock API calls.

Priority:
  1. AWS_REGION env var
  2. AWS_DEFAULT_REGION env var
  3. boto3/botocore configured region (from ~/.aws/config or SSO profile)
  4. us-east-1 (hard fallback)

The boto3 fallback is critical for EU/AP users who configure their region
in ~/.aws/config via a named profile rather than env vars — without it,
live model discovery would always return us.* profile IDs regardless of
the user's actual region.

#### def `bedrock_model_ids_or_none() -> Optional[List[str]]`

Live-discover Bedrock model IDs for the active region.

Returns a list of model ID strings if discovery succeeds and yields
at least one model, or ``None`` on failure / empty result.  Callers
should fall back to the static curated list when ``None`` is returned.

This helper consolidates the discover → extract-ids → fallback
pattern that was previously duplicated across ``provider_model_ids``,
``list_authenticated_providers`` section 2, and section 3.

#### def `is_anthropic_bedrock_model(model_id: str) -> bool`

Return True if the model is an Anthropic Claude model on Bedrock.

These models should use the AnthropicBedrock SDK path for full feature
parity (prompt caching, thinking budgets, adaptive thinking).
Non-Claude models use the Converse API path.

Matches:
  - ``anthropic.claude-*`` (foundation model IDs)
  - ``us.anthropic.claude-*`` (US inference profiles)
  - ``global.anthropic.claude-*`` (global inference profiles)
  - ``eu.anthropic.claude-*`` (EU inference profiles)

#### def `convert_tools_to_converse(tools: List[Dict]) -> List[Dict]`

Convert OpenAI-format tool definitions to Bedrock Converse ``toolConfig``.

OpenAI format::

    {"type": "function", "function": {"name": "...", "description": "...",
     "parameters": {"type": "object", "properties": {...}}}}

Converse format::

    {"toolSpec": {"name": "...", "description": "...",
     "inputSchema": {"json": {"type": "object", "properties": {...}}}}}

#### def `convert_messages_to_converse(messages: List[Dict]) -> Tuple[Optional[List[Dict]], List[Dict]]`

Convert OpenAI-format messages to Bedrock Converse format.

Returns ``(system_prompt, converse_messages)`` where:
  - ``system_prompt`` is a list of system content blocks (or None)
  - ``converse_messages`` is the conversation in Converse format

Handles:
  - System messages → extracted as system prompt
  - User messages → ``{"role": "user", "content": [...]}``
  - Assistant messages → ``{"role": "assistant", "content": [...]}``
  - Tool calls → ``{"toolUse": {"toolUseId": ..., "name": ..., "input": ...}}``
  - Tool results → ``{"toolResult": {"toolUseId": ..., "content": [...]}}``

Converse requires strict user/assistant alternation. Consecutive messages
with the same role are merged into a single message.

#### def `normalize_converse_response(response: Dict) -> SimpleNamespace`

Convert a Bedrock Converse API response to an OpenAI-compatible object.

The agent loop in ``run_agent.py`` expects responses shaped like
``openai.ChatCompletion`` — this function bridges the gap.

Returns a SimpleNamespace with:
  - ``.choices[0].message.content`` — text response
  - ``.choices[0].message.tool_calls`` — tool call list (if any)
  - ``.choices[0].finish_reason`` — stop/tool_calls/length
  - ``.usage`` — token usage stats

#### def `normalize_converse_stream_events(event_stream) -> SimpleNamespace`

Consume a Bedrock ConverseStream event stream and build an OpenAI-compatible response.

Processes the stream events in order:
  - ``messageStart`` — role info
  - ``contentBlockStart`` — new text or toolUse block
  - ``contentBlockDelta`` — incremental text or toolUse input
  - ``contentBlockStop`` — block complete
  - ``messageStop`` — stop reason
  - ``metadata`` — usage stats

Returns the same shape as ``normalize_converse_response()``.

#### def `stream_converse_with_callbacks(event_stream, on_text_delta = None, on_tool_start = None, on_reasoning_delta = None, on_interrupt_check = None, on_event = None) -> SimpleNamespace`

Process a Bedrock ConverseStream event stream with real-time callbacks.

This is the core streaming function that powers both the CLI's live token
display and the gateway's progressive message updates.

Args:
    event_stream: The boto3 ``converse_stream()`` response containing a
        ``stream`` key with an iterable of events.
    on_text_delta: Called with each text chunk as it arrives. Only fires
        when no tool_use blocks have been seen (same semantics as the
        Anthropic and chat_completions streaming paths).
    on_tool_start: Called with the tool name when a toolUse block begins.
        Lets the TUI show a spinner while tool arguments are generated.
    on_reasoning_delta: Called with reasoning/thinking text chunks.
        Bedrock surfaces thinking via ``reasoning`` content block deltas
        on supported models (Claude 4.6+).
    on_interrupt_check: Called on each event. Should return True if the
        agent has been interrupted and streaming should stop.
    on_event: Called once at the top of the loop body for EVERY yielded
        Bedrock event (text/tool-input/reasoning/metadata deltas alike),
        before any branching. Provides a wire-level liveness signal so an
        external watchdog can distinguish "still receiving events" from
        "stream wedged with no data". Errors raised by the callback are
        swallowed so a liveness hook can never abort the stream.

Returns:
    An OpenAI-compatible SimpleNamespace response, identical in shape to
    ``normalize_converse_response()``.

#### def `build_converse_kwargs(model: str, messages: List[Dict], tools: Optional[List[Dict]] = None, max_tokens: int = 4096, temperature: Optional[float] = None, top_p: Optional[float] = None, stop_sequences: Optional[List[str]] = None, guardrail_config: Optional[Dict] = None) -> Dict[str, Any]`

Build kwargs for ``bedrock-runtime.converse()`` or ``converse_stream()``.

Converts OpenAI-format inputs to Converse API parameters.

#### def `call_converse(region: str, model: str, messages: List[Dict], tools: Optional[List[Dict]] = None, max_tokens: int = 4096, temperature: Optional[float] = None, top_p: Optional[float] = None, stop_sequences: Optional[List[str]] = None, guardrail_config: Optional[Dict] = None) -> SimpleNamespace`

Call Bedrock Converse API (non-streaming) and return an OpenAI-compatible response.

This is the primary entry point for the agent loop when using the Bedrock provider.

#### def `call_converse_stream(region: str, model: str, messages: List[Dict], tools: Optional[List[Dict]] = None, max_tokens: int = 4096, temperature: Optional[float] = None, top_p: Optional[float] = None, stop_sequences: Optional[List[str]] = None, guardrail_config: Optional[Dict] = None) -> SimpleNamespace`

Call Bedrock ConverseStream API and return an OpenAI-compatible response.

Consumes the full stream and returns the assembled response. For true
streaming with delta callbacks, use ``iter_converse_stream()`` instead.

#### def `reset_discovery_cache()`

Clear the model discovery cache. Used in tests.

#### def `discover_bedrock_models(region: str, provider_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]`

Discover available Bedrock foundation models and inference profiles.

Returns a list of model info dicts with keys:
  - ``id``: Model ID (e.g. "anthropic.claude-sonnet-4-6-20250514-v1:0")
  - ``name``: Human-readable name
  - ``provider``: Model provider (e.g. "Anthropic", "Amazon", "Meta")
  - ``input_modalities``: List of input types (e.g. ["TEXT", "IMAGE"])
  - ``output_modalities``: List of output types
  - ``streaming``: Whether streaming is supported

Caches results for 1 hour per region to avoid repeated API calls.

Mirrors OpenClaw's ``discoverBedrockModels()`` in
``extensions/amazon-bedrock/discovery.ts``.

#### def `is_context_overflow_error(error_message: str) -> bool`

Return True if the error indicates the input context was too large.

When this returns True, the agent should compress context and retry
rather than treating it as a fatal error.

#### def `classify_bedrock_error(error_message: str) -> str`

Classify a Bedrock error for retry/failover decisions.

Returns:
  - ``"context_overflow"`` — input too long, compress and retry
  - ``"rate_limit"`` — throttled, backoff and retry
  - ``"overloaded"`` — model temporarily unavailable, retry with delay
  - ``"unknown"`` — unclassified error

#### def `probe_bedrock_context_length(model_id: str, region: str) -> Optional[int]`

Discover a Bedrock model's real context window by provoking a length error.

Bedrock does not expose the context window via any metadata API
(``get-foundation-model`` omits it, ``Converse`` metrics omit it,
``CountTokens`` is unsupported on several models).  The only authoritative
source is the ``ValidationException`` raised when a prompt exceeds the
window:

    "The model returned the following errors: prompt is too long:
     1300032 tokens > 1000000 maximum"

Length validation happens *before* inference, so an oversized request is
rejected immediately and cheaply — no tokens are generated and no input is
actually processed.  We pad a request just past each tier in
``_BEDROCK_PROBE_TIERS`` and parse the reported ``maximum``.  Tiers exist
because (a) a *wildly* oversized payload makes Bedrock fail with an opaque
InternalServerException instead of a clean length error, and (b) stepping
up discovers larger windows without over-padding smaller ones.

Returns the detected window, or ``None`` if the probe could not run
(missing credentials, network error, or no parseable limit) so the caller
can fall back to the static table.

#### def `get_bedrock_context_length(model_id: str, region: str = '', probe: bool = True) -> int`

Resolve the context window for a Bedrock model.

Resolution order:
  1. Live probe against Bedrock (authoritative; cached by the caller).
  2. Static fallback table (longest-substring match).
  3. Conservative default.

The static table is intentionally a *fallback*, not the primary source:
AWS ships new model versions (opus-4-7, opus-4-8, ...) faster than the
table can track, and a stale entry silently caps the window (e.g. a
1M-token Opus pinned to 200K via an ``opus-4`` substring match).  The
probe asks Bedrock directly so every model — current or future — gets its
real window with no table maintenance.

``probe=False`` (or an empty ``region``) skips the network call and uses
the static table only — used by pure-offline/display code paths.


## agent.billing_usage

### 模块文档

Shared dollar-denominated usage model for the billing/subscription surfaces.

The single source of truth behind the ``/usage`` and ``/subscription`` usage
bars (TUI + CLI). User feedback (Jun 2026): the terminal surfaces show
**dollars**, never "credits", and every usage bar must make the monthly
subscription allowance and separately-purchased top-up dollars distinctly
visible.

Data source: the NAS account-info fetch (``NousPortalAccountInfo``), whose
``paid_service_access_info`` carries the three dollar magnitudes we render
(despite the legacy ``*_credits`` field names, these are USD floats):

  - ``subscription_credits_remaining``  -> plan dollars left this month
  - ``purchased_credits_remaining``     -> top-up dollars left (rolls over)
  - ``total_usable_credits``            -> total spendable

plus ``subscription.monthly_credits`` (the plan's monthly $ allowance, the
denominator for the "% used" plan bar) and ``current_period_end`` (renewal).

Design: two SEPARATE bars (decided with the user) rather than one crammed
three-segment bar — at terminal widths three same-glyph density segments are
unreadable. The plan bar is "spent vs allowance this month" (carries % used);
the top-up bar is "money you bought, doesn't expire". Each gets full
resolution and a single fill glyph, so the bar is never ambiguous and never
relies on color.

Fail-open everywhere: any missing/non-finite field degrades to fewer bars or a
magnitudes-only view; a logged-out / unreachable portal yields
``available=False`` and the surface shows nothing.

### class UsageBar

> 继承: `object` ｜ 方法数: 2（公开 2）

One full-resolution bar: ``spent`` of ``total``, plus a remaining figure.

``kind`` is ``"plan"`` (monthly allowance, shows % used) or ``"topup"``
(purchased dollars, no denominator — ``spent`` is 0 and ``total`` ==
``remaining`` so it renders as a full bar of available balance).

#### property `pct_used(self) -> Optional[int]`

#### property `fill_fraction(self) -> float`

Fraction of the bar that should read as 'remaining' (filled).


### class UsageModel

> 继承: `object` ｜ 方法数: 1（公开 1）

Surface-agnostic dollar usage model shared by /usage and /subscription.

``status`` classifies the account for copy selection:
  - ``"free"``     : no paid access / no subscription (free models only)
  - ``"low"``      : paid, but total spendable < $5 (ALERT)
  - ``"healthy"``  : paid, total spendable >= $5
  - ``"depleted"`` : paid access lost (balance exhausted)

#### property `has_topup(self) -> bool`


### 顶层函数

#### def `format_renews(value: Optional[str]) -> Optional[str]`

Format an ISO date/timestamp as a human date, e.g. ``Jul 24, 2026``.

Accepts ``2026-07-24``, ``2026-07-24T11:05:01.000Z``, etc. Returns the raw
string unchanged if it can't be parsed (never raises), and ``None`` for
empty input.

#### def `usage_model_from_account(account_info: Any) -> UsageModel`

Build a :class:`UsageModel` from a ``NousPortalAccountInfo``. Fail-open.

Returns ``UsageModel(available=False)`` when there's no usable account info
(logged out, no entitlement block). Never raises.

#### def `build_usage_model(timeout: float = 10.0) -> UsageModel`

Fetch account-info and build the shared usage model. Fail-open.

Dev override: ``HERMES_DEV_CREDITS_FIXTURE`` short-circuits to a fixture so
every usage state is testable without a live account (mirrors the existing
``/usage`` credits-block fixture path).


## agent.billing_view

### 模块文档

Surface-agnostic core for the Phase 2b terminal-billing screens.

One fetch/parse per concern, consumed identically by the CLI handler
(``cli.py::_show_billing``), the TUI JSON-RPC methods
(``tui_gateway/server.py``), and any other surface. Mirrors the proven
``agent/account_usage.py::build_credits_view`` pattern: parse the server payload
into a frozen dataclass; **fail open** — when not logged in or the portal is
unreachable, return a struct with ``logged_in=False`` and let the surface degrade
gracefully (never crash).

Money discipline: the server emits decimal STRINGS (``"142.5"``, not fixed 2dp).
We keep them as :class:`decimal.Decimal` end-to-end and only format for display.

### class CardInfo

> 继承: `object` ｜ 方法数: 3（公开 3）

#### property `masked(self) -> str`

#### property `provenance(self) -> Optional[str]`

Human label for why this card was picked, or None (unknown rung /
server too old to say).

#### property `display(self) -> str`

The one-line card display: ``Visa ····4242 — the card on your
subscription`` (or just the masked card when provenance is unknown).


### class MonthlyCap

> 继承: `object` ｜ 方法数: 0（公开 0）


### class AutoReloadCard

> 继承: `object` ｜ 方法数: 0（公开 0）


### class AutoReload

> 继承: `object` ｜ 方法数: 0（公开 0）


### class BillingState

> 继承: `object` ｜ 方法数: 3（公开 3）

Parsed ``GET /api/billing/state`` — the overview screen's data.

Fail-open: ``logged_in=False`` (and empty fields) when not logged in or the
portal is unreachable.

#### property `is_admin(self) -> bool`

Deprecated/display only — a legacy OWNER/ADMIN check.

NOT a capability check; use :attr:`can_change_plan` for gating billing
plan-change actions.

#### property `can_change_plan(self) -> bool`

Server capability when supplied; otherwise the legacy role fallback.

#### property `can_charge(self) -> bool`

True when the UI should offer charge/auto-reload actions.

Uses the server-granted plan-change capability (``can_change_plan``,
which itself falls back to the legacy OWNER/ADMIN role check when the
server omits ``canChangePlan``) AND the per-org kill-switch. This lets
the server grant charge capability to non-OWNER/ADMIN roles (e.g.
FINANCE_ADMIN) via ``canChangePlan``, instead of hard-coding the
deprecated 3-role admin check. (The server still enforces; this is
just for graying out actions the user can't take.)


### class AmountValidation

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `parse_money(value: Any) -> Optional[Decimal]`

Parse a server money value (decimal string) into :class:`Decimal`.

Returns None for missing/invalid input. Never raises. Accepts str/int (and,
defensively, float — though the server always sends strings).

#### def `format_money(value: Optional[Decimal]) -> str`

Format a Decimal as ``$X`` / ``$X.YY`` for display.

Whole dollars show no decimals; any fractional amount shows exactly 2dp:
``Decimal("142.5")`` → ``"$142.50"``, ``Decimal("100")`` → ``"$100"``,
``Decimal("0.01")`` → ``"$0.01"``.

#### def `billing_state_from_payload(payload: dict[str, Any], portal_url: Optional[str] = None) -> BillingState`

Map a raw ``/api/billing/state`` JSON dict into :class:`BillingState`.

#### def `build_billing_state(timeout: float = 15.0) -> BillingState`

Fetch + parse ``/api/billing/state``. Fail-open.

Returns ``BillingState(logged_in=False)`` when not logged in. On a portal/HTTP
failure, returns ``logged_in=False`` with ``error`` set so the surface can show
a clear message rather than crashing.

Dev override: ``HERMES_DEV_BILLING_FIXTURE`` short-circuits to a fixture so the
card-on-file / admin / scope states are testable offline (mirrors
``HERMES_DEV_CREDITS_FIXTURE`` for the usage model).

#### def `new_idempotency_key() -> str`

Fresh UUID for a user-confirmed purchase (reuse on retry of the SAME buy).

The ``Idempotency-Key`` header is mandatory on ``POST /charge``; generate one
per confirmed purchase and reuse it across retries so a double-submit collapses
to a single charge. Never reuse a key across different amounts (the server
returns 409 idempotency_conflict).

#### def `validate_charge_amount(raw: str, min_usd: Optional[Decimal], max_usd: Optional[Decimal]) -> AmountValidation`

Validate a custom charge amount against bounds + 2dp (multipleOf 0.01).

Mirrors the server's accept/reject so the UI can give instant feedback rather
than round-tripping a sure-to-fail charge. The server is still authoritative.


## agent.bounded_response

### 模块文档

Bounded reads of HTTP error response bodies.

When a provider returns a non-OK status on a *streaming* request, Hermes reads
the response body to build a useful diagnostic error. A bare ``response.read()``
on a streaming httpx response is unbounded in two dangerous ways:

1. A server can declare (or stream) an arbitrarily large body, so the read can
   balloon memory.
2. A server can open the body and then stall forever (no ``Content-Length``,
   no further bytes), so the read hangs the agent indefinitely.

Both are realistic against a misbehaving proxy, a hijacked endpoint, or a
provider having a bad day. The diagnostic body is only ever shown to the user
truncated to a few hundred characters, so reading megabytes — or blocking
forever — buys nothing.

``read_streaming_error_body`` bounds the read to a byte cap and enforces a
hard wall-clock deadline, returning the decoded text snippet. Callers pass the
returned text into their existing error builders instead of touching
``response.text`` (which would be unbounded / would raise after a partial
stream read).

A subtlety the implementation must respect: ``httpx``'s ``iter_bytes()`` blocks
*inside* the C/socket read while waiting for the next chunk. A wall-clock check
placed only between yielded chunks cannot interrupt a server that opens the
body and then stalls mid-chunk — control never returns to Python until httpx's
own (often 30s+) read timeout fires. To guarantee a bounded stop regardless of
socket behavior, the read runs on a daemon worker thread and the caller waits
on it with a hard deadline; on timeout we close the response (which unblocks /
cancels the read) and return whatever partial bytes were collected.

Ported and adapted from openclaw/openclaw#95108 ("bound Anthropic error
streams"), generalized to cover Hermes's three streaming error-body sites
(native Gemini, Gemini Cloud Code, Antigravity Cloud Code).

### 顶层函数

#### def `read_streaming_error_body(response: httpx.Response, max_bytes: int = DEFAULT_ERROR_BODY_MAX_BYTES, timeout_s: float = DEFAULT_ERROR_BODY_TIMEOUT_S) -> str`

Read a non-OK streaming response body with a byte cap and a hard deadline.

Returns the decoded body text (UTF-8, errors replaced), truncated to
``max_bytes``. Never raises: any transport error, stall, or oversize
condition is swallowed and the best-effort partial text (or an empty
string) is returned, because this runs on the error path and must not
mask the original HTTP failure with a read error.

The byte cap protects against huge bodies; the wall-clock deadline (enforced
via a worker thread so it can interrupt a socket read that stalls mid-chunk)
protects against bodies that open and then hang.

#### def `read_error_body_or_default(response: httpx.Response, max_bytes: int = DEFAULT_ERROR_BODY_MAX_BYTES, timeout_s: float = DEFAULT_ERROR_BODY_TIMEOUT_S) -> Optional[str]`

Like ``read_streaming_error_body`` but returns ``None`` on empty body.

Convenience for callers that distinguish "no body" from "empty string".


## agent.browser_provider

### 模块文档

Browser Provider ABC
====================

Defines the pluggable-backend interface for cloud browser providers
(Browserbase, Browser Use, Firecrawl, …). Providers register instances via
:meth:`PluginContext.register_browser_provider`; the active one (selected via
``browser.cloud_provider`` in ``config.yaml``) services every cloud-mode
``browser_*`` tool call.

Providers live in ``<repo>/plugins/browser/<name>/`` (built-in, auto-loaded as
``kind: backend``) or ``~/.hermes/plugins/browser/<name>/`` (user, opt-in via
``plugins.enabled``).

This ABC mirrors :class:`agent.web_search_provider.WebSearchProvider` (PR
#25182) — same shape, same registration flow, same picker integration. The
legacy in-tree ``tools.browser_providers.base.CloudBrowserProvider`` ABC was
deleted in PR #25214 (this work) along with the per-vendor inline modules in
``tools/browser_providers/``; the lifecycle contract documented below is
preserved bit-for-bit so the tool wrapper (:mod:`tools.browser_tool`) does
not have to translate.

Session metadata contract (preserved from the legacy ``CloudBrowserProvider``)::

    {
        "session_name": str,        # unique name for agent-browser --session
        "bb_session_id": str,       # provider session ID (for close/cleanup)
        "cdp_url": str,             # CDP websocket URL
        "features": dict,           # feature flags that were enabled
        "external_call_id": str,    # optional, managed-gateway billing key
    }

``bb_session_id`` is a legacy key name kept verbatim for backward compat with
:mod:`tools.browser_tool` — it holds the provider's session ID regardless of
which provider is in use.

### class BrowserProvider

> 继承: `abc.ABC` ｜ 方法数: 9（公开 9）

Abstract base class for a cloud browser backend.

Subclasses must implement :meth:`name`, :meth:`is_available`, and the
three lifecycle methods: :meth:`create_session`, :meth:`close_session`,
:meth:`emergency_cleanup`.

The lifecycle shape preserves the legacy ``CloudBrowserProvider`` contract
bit-for-bit so the dispatcher in :mod:`tools.browser_tool` is a pure
registry lookup — no per-provider conditionals, no shape translation.

#### property `name(self) -> str`

Stable short identifier used in the ``browser.cloud_provider``
config key.

Lowercase, hyphens permitted to preserve existing user-visible names.
Examples: ``browserbase``, ``browser-use``, ``firecrawl``.

#### property `display_name(self) -> str`

Human-readable label shown in ``hermes tools``. Defaults to ``name``.

#### def `is_available(self) -> bool`

Return True when this provider can service calls.

Typically a cheap check (env var present, managed-gateway token
readable, optional Python dep importable). Must NOT make network
calls — this runs at tool-registration time and on every
``hermes tools`` paint.

Mirrors the legacy ``CloudBrowserProvider.is_configured()`` method;
renamed for parity with :class:`agent.web_search_provider.WebSearchProvider`.

#### def `create_session(self, task_id: str) -> Dict[str, object]`

Create a cloud browser session and return session metadata.

Must return a dict with at least::

    {
        "session_name": str,    # unique name for agent-browser --session
        "bb_session_id": str,   # provider session ID (for close/cleanup)
        "cdp_url": str,         # CDP websocket URL
        "features": dict,       # feature flags that were enabled
    }

``bb_session_id`` is a legacy key name kept for backward compat with
the rest of :mod:`tools.browser_tool` — it holds the provider's
session ID regardless of which provider is in use.

May raise ``ValueError`` (missing credentials) or ``RuntimeError``
(network / API failure); the dispatcher surfaces these to the user.

#### def `close_session(self, session_id: str) -> bool`

Release / terminate a cloud session by its provider session ID.

Returns True on success, False on failure. Should not raise — log and
return False on any exception so the dispatcher's cleanup loop keeps
moving across sessions.

#### def `emergency_cleanup(self, session_id: str) -> None`

Best-effort session teardown during process exit.

Called from atexit / signal handlers. Must tolerate missing
credentials, network errors, etc. — log and move on. Must not raise.

#### def `get_setup_schema(self) -> Dict[str, Any]`

Return provider metadata for the ``hermes tools`` picker.

Used by :mod:`hermes_cli.tools_config` to inject this provider as a
row in the Browser Automation picker. Shape mirrors the existing
hardcoded entries in ``TOOL_CATEGORIES["browser"]``::

    {
        "name": "Browserbase",
        "badge": "paid",
        "tag": "Cloud browser with stealth and proxies",
        "env_vars": [
            {"key": "BROWSERBASE_API_KEY",
             "prompt": "Browserbase API key",
             "url": "https://browserbase.com"},
        ],
        "post_setup": "agent_browser",
    }

Default: minimal entry derived from :attr:`display_name`. Override to
expose API key prompts, badges, managed-Nous gating, and the
``post_setup`` install hook.

#### def `is_configured(self) -> bool`

Backward-compat alias for :meth:`is_available`.

#### def `provider_name(self) -> str`

Backward-compat alias returning :attr:`display_name`.


## agent.browser_registry

### 模块文档

Browser Provider Registry
=========================

Central map of registered cloud browser providers. Populated by plugins at
import-time via :meth:`PluginContext.register_browser_provider`; consumed by
:func:`tools.browser_tool._get_cloud_provider` to route each cloud-mode
``browser_*`` tool call to the active backend.

Active selection
----------------
The active provider is chosen by configuration with this precedence:

1. ``browser.cloud_provider`` in ``config.yaml`` (explicit override).
2. Legacy preference order — ``browser-use`` → ``browserbase`` — filtered by
   availability. Matches the historic auto-detect order in
   :func:`tools.browser_tool._get_cloud_provider` (Browser Use checked first
   because it covers both the managed Nous gateway and direct API key path;
   Browserbase as the older direct-credentials fallback). ``firecrawl`` is
   intentionally NOT in the legacy walk — users only get Firecrawl as a
   cloud browser when they explicitly set ``browser.cloud_provider:
   firecrawl``, matching pre-migration behaviour where Firecrawl was never
   auto-selected.
3. Otherwise ``None`` — the dispatcher falls back to local browser mode.

The explicit-config branch (rule 1) intentionally ignores ``is_available()``
so the dispatcher surfaces a typed "X_API_KEY is not set" error to the user
instead of silently switching backends. Matches the legacy
:func:`tools.browser_tool._get_cloud_provider` behaviour for configured names.

Note: there is no "capability" split here (unlike the web subsystem, which
has search/extract/crawl). Every browser provider implements the full
:class:`agent.browser_provider.BrowserProvider` lifecycle; the registry's
job is purely selection, not capability routing.

### 顶层函数

#### def `register_provider(provider: BrowserProvider) -> None`

Register a cloud browser provider.

Re-registration (same ``name``) overwrites the previous entry and logs
a debug message — makes hot-reload scenarios (tests, dev loops) behave
predictably.

**异常**: `TypeError`, `ValueError`

#### def `list_providers() -> List[BrowserProvider]`

Return all registered providers, sorted by name.

#### def `get_provider(name: str) -> Optional[BrowserProvider]`

Return the provider registered under *name*, or None.


## agent.chat_completion_helpers

### 模块文档

Helper functions for the chat-completions code path.

Extracted from :class:`AIAgent` for cleanliness — bodies of the
non-streaming API call, request kwargs builder, assistant-message
materializer, provider-fallback activator, max-iterations handler,
and per-turn resource cleanup.

Each function takes the parent ``AIAgent`` as its first argument
(``agent``).  :class:`AIAgent` keeps thin forwarder methods so call
sites unchanged.  Symbols that tests patch on ``run_agent`` (e.g.
``cleanup_vm`` / ``cleanup_browser`` in
``test_zombie_process_cleanup.py``) are resolved through
:func:`_ra` so the patch contract is preserved.

### 顶层函数

#### def `estimate_request_context_tokens(api_payload: Any) -> int`

Estimate context/load tokens from an API payload, dict or messages list.

The stale-call detectors historically assumed a Chat Completions request:
they pulled ``api_kwargs["messages"]`` and ran a cheap char/4 estimate.
Codex / Responses API requests carry the conversational payload in
``input`` (with additional load in ``instructions`` and ``tools``), so the
legacy estimator reported ~0 tokens for every Codex turn and the
context-tier scaling never fired.

This helper handles both shapes:
  - bare list -> treat as Chat Completions ``messages``
  - dict with ``messages`` -> Chat Completions (+ ``tools`` if present)
  - dict with ``input`` -> Responses API (+ ``instructions``/``tools``)
  - any other dict -> fall back to summing string values

#### def `openai_codex_stale_timeout_floor(est_tokens: int) -> float`

Minimum wall-clock stale timeout for openai-codex by estimated context.

Gateway/Telegram sessions routinely ship ~15–25k tokens of tools +
instructions before the first user message. Subscription-backed Codex can
legitimately spend several minutes in backend admission/prefill at that
size; the generic 90s non-stream stale default aborts healthy calls. The
floor engages above 10k estimated tokens so those gateway-scale payloads
are covered; smaller requests keep the generic default.

#### def `should_use_direct_api_call(agent) -> bool`

Whether a cron OpenAI-wire request should skip the interrupt worker.

Issue #62151 is specific to OpenRouter's chat-completions path inside the
gateway cron thread stack. Keep native/Codex/Bedrock/MoA transports on their
established workers: their cancellation and client ownership differ, and
the report provides no evidence that those paths share the pre-HTTP wedge.

#### def `direct_api_call(agent, api_kwargs: dict)`

Run a non-streaming LLM call inline on the conversation thread.

Used when ``should_use_direct_api_call`` is True. Skips the interrupt worker
(whose only job is interactive-interrupt responsiveness, which this context
does not have) so the nested-pool deadlock (#62151) cannot occur. Because the
request runs in-flight normally, the per-request OpenAI client's own httpx
timeout (provider ``request_timeout_seconds`` / ``HERMES_API_TIMEOUT``) bounds
a genuinely hung provider — the same bound interactive calls already rely on.

**异常**: `InterruptedError`

#### def `interruptible_api_call(agent, api_kwargs: dict)`

Run the API call in a background thread so the main conversation loop
can detect interrupts without waiting for the full HTTP round-trip.

Each worker thread gets its own OpenAI client instance. Interrupts only
close that worker-local client, so retries and other requests never
inherit a closed transport.

Includes a stale-call detector: if no response arrives within the
configured timeout, the connection is killed and an error raised so
the main retry loop can try again with backoff / credential rotation /
provider fallback.

**异常**: `InterruptedError`

#### def `build_api_kwargs(agent, api_messages: list) -> dict`

Build the keyword arguments dict for the active API mode.

#### def `build_assistant_message(agent, assistant_message, finish_reason: str) -> dict`

Build a normalized assistant message dict from an API response message.

Handles reasoning extraction, reasoning_details, and optional tool_calls
so both the tool-call path and the final-response path share one builder.

#### def `rewrite_prompt_model_identity(agent, model: str, provider: str) -> None`

Point the cached system prompt's ``Model:``/``Provider:`` lines at
the active runtime after a provider switch.

The system prompt is session-stable and replayed verbatim for prefix-cache
warmth, but after a failover the new backend's cache is cold anyway —
while a stale identity line makes the agent misreport which model it is
when asked.  Rewrite the lines in place WITHOUT persisting to the session
DB: the stored row keeps the primary's labels, so when the primary is
restored the prompt is byte-identical to the stored copy again and its
prefix cache still matches.

Only the LAST occurrence of each line is touched — the identity lines
live in the volatile tail of the prompt, and earlier matches could be
user content (memory snapshots, context files).

#### def `try_activate_fallback(agent, reason: FailoverReason | None = None) -> bool`

Switch to the next fallback model/provider in the chain.

Called when the current model is failing after retries.  Swaps the
OpenAI client, model slug, and provider in-place so the retry loop
can continue with the new backend.  Advances through the chain on
each call; returns False when exhausted.

Uses the centralized provider router (resolve_provider_client) for
auth resolution and client construction — no duplicated provider→key
mappings.

#### def `handle_max_iterations(agent, messages: list, api_call_count: int) -> str`

Request a summary when max iterations are reached. Returns the final response text.

#### def `cleanup_task_resources(agent, task_id: str) -> None`

Clean up VM and browser resources for a given task.

Skips ``cleanup_vm`` when the active terminal environment is marked
persistent (``persistent_filesystem=True``) so that long-lived sandbox
containers survive between turns. The idle reaper in
``terminal_tool._cleanup_inactive_envs`` still tears them down once
``terminal.lifetime_seconds`` is exceeded. Non-persistent backends are
torn down per-turn as before to prevent resource leakage (the original
intent of this hook for the Morph backend, see commit fbd3a2fd).

Skips ``cleanup_browser`` in headed mode so the browser window stays
visible between turns. The inactivity reaper in
``browser_tool._cleanup_inactive_browser_sessions`` still handles
idle sessions.

#### def `interruptible_streaming_api_call(agent, api_kwargs: dict, on_first_delta = None)`

Streaming variant of _interruptible_api_call for real-time token delivery.

Handles all three api_modes:
- chat_completions: stream=True on OpenAI-compatible endpoints
- anthropic_messages: client.messages.stream() via Anthropic SDK
- codex_responses: delegates to _run_codex_stream (already streaming)

Fires stream_delta_callback and _stream_callback for each text token.
Tool-call turns suppress the callback — only text-only final responses
stream to the consumer.  Returns a SimpleNamespace that mimics the
non-streaming response shape so the rest of the agent loop is unchanged.

Falls back to _interruptible_api_call on provider errors indicating
streaming is not supported.

**异常**: `InterruptedError`, `_httpx.RemoteProtocolError`, `EmptyStreamError`


## agent.codex_responses_adapter

### 模块文档

Codex Responses API adapter.

Pure format-conversion and normalization logic for the OpenAI Responses API
(used by OpenAI Codex, xAI, GitHub Models, and other Responses-compatible endpoints).

Extracted from run_agent.py to isolate Responses API-specific logic from the
core agent loop. All functions are stateless — they operate on the data passed
in and return transformed results.

## agent.codex_runtime

### 模块文档

Codex API runtime — App Server and Responses-API streaming paths.

Extracted from :class:`AIAgent` to keep the agent loop file focused.
Each function takes the parent ``AIAgent`` as its first argument
(``agent``).  AIAgent keeps thin forwarder methods for backward
compatibility.

* ``run_codex_app_server_turn`` — drives one turn through the
  ``codex_app_server`` subprocess client (used when a Codex CLI install
  is the active provider).
* ``run_codex_stream`` — streams a Codex Responses API call (the
  ``codex_responses`` api_mode).
* ``run_codex_create_stream_fallback`` — recovery path when the
  Responses ``stream=True`` initial create fails.

### 顶层函数

#### def `make_codex_app_server_event_bridge(agent) -> Callable[[dict], None]`

Build an ``on_event`` callback that wires codex app-server JSON-RPC
notifications into Hermes' gateway UI callbacks.

Returns a single-argument callable suitable for
``CodexAppServerSession(on_event=...)``.

Translation map:
  * ``item/started`` for tool-shaped items → ``tool_progress_callback(
    "tool.started", name, preview, args)``
  * ``item/completed`` for tool-shaped items → ``tool_progress_callback(
    "tool.completed", name, None, None, duration=..., is_error=...,
    result=...)``
  * ``item/agentMessage/delta`` → ``_fire_stream_delta(text)`` so chat
    adapters can render the assistant's reply as it streams.
  * ``item/reasoning/delta`` → ``_fire_reasoning_delta(text)``
  * ``item/completed`` for ``agentMessage`` →
    ``_emit_interim_assistant_message({"role": "assistant",
    "content": text})``. The gateway's ``already_streamed`` check
    dedupes against any text the stream-delta callback already
    rendered for the same message.

All callback invocations are guarded — a buggy display callback must
not tear down the codex turn loop. Errors are logged at DEBUG so the
notification stream keeps flowing regardless.

#### def `run_codex_app_server_turn(agent, user_message: str, original_user_message: Any, messages: List[Dict[str, Any]], effective_task_id: str, should_review_memory: bool = False) -> Dict[str, Any]`

Codex app-server runtime path. Hands the entire turn to a `codex
app-server` subprocess and projects its events back into Hermes'
messages list so memory/skill review keep working.

Called from run_conversation() when agent.api_mode == "codex_app_server".
Returns the same dict shape as the chat_completions path.

#### def `run_codex_stream(agent, api_kwargs: dict, client: Any = None, on_first_delta = None)`

Execute one streaming Responses API request and return the final response.

Uses ``responses.create(stream=True)`` (low-level raw event iteration)
rather than the high-level ``responses.stream(...)`` helper.  This makes
us structurally immune to backend drift in the ``response.completed``
payload shape — we never let the SDK reconstruct a typed object from
the terminal event's ``output`` field.

**异常**: `InterruptedError`

#### def `run_codex_create_stream_fallback(agent, api_kwargs: dict, client: Any = None)`

Backward-compatible alias for the unified event-driven path.

Historically this was the fallback when the SDK's high-level
``responses.stream(...)`` helper raised on shape drift.  The primary
path now does exactly what the fallback did, so this just forwards.
Kept as a public symbol because tests and a small number of call sites
still reference it by name.


## agent.coding_context

### 模块文档

Coding-context awareness — base Hermes, every interactive surface.

When the user runs Hermes inside a code workspace (CLI, TUI, desktop app, or an
editor over ACP), Hermes shifts into a **coding posture**. This module is the
single place that decides whether we're in that posture and what it implies,
so the rest of the codebase never re-derives "are we coding?" on its own.

Architecture — one seam, many consumers
----------------------------------------
The posture is modelled as a frozen :class:`RuntimeMode` selected from a small
:class:`ContextProfile` registry (today: ``coding`` and ``general``). A profile
is *data* — it declares the toolset to collapse to, the operating brief to
inject, and hints for other domains (model routing, memory, subagents). Every
domain reads the same resolved object instead of probing git/config itself:

  * **System prompt** — ``RuntimeMode.system_blocks()`` → the operating brief +
    a live git/workspace snapshot (``agent/system_prompt.py``).
  * **Toolset** — ``RuntimeMode.toolset_selection()`` → the ``coding`` toolset
    plus the user's enabled MCP servers (``cli.py`` / ``tui_gateway``). Only
    under the opt-in ``focus`` mode: the default posture is prompt-only and
    never touches the user's configured toolsets (toolsets like messaging /
    smart-home / music are off-by-default anyway, and someone who explicitly
    enabled image-gen or Spotify shouldn't lose it for being in a git repo).
  * **Delegation** — subagents inherit the parent's toolset and run through the
    same prompt builder, so the coding posture propagates to children for free.
  * **Model / memory / compression** — declared on the profile
    (``model_hint``, ``memory_policy``) as the extension seam; consumers read
    ``mode.profile`` rather than re-deciding.

Cache safety
------------
The mode is resolved **once** and is immutable. The workspace snapshot is built
once at prompt-build time and baked into the *stable* system-prompt tier — never
re-probed per turn (that would shatter the prompt cache). Branch and dirty state
drift mid-session, so the brief tells the model to re-check with ``git`` before
acting on the snapshot. A ``/coding`` flip therefore only takes effect next
session (deferred), the same contract as ``/skills install`` vs ``--now``.

Activation (config ``agent.coding_context``):

  * ``auto`` (default) — posture (brief + snapshot) on an interactive coding
    surface sitting in a code workspace (git repo or recognised project root).
    Prompt-only; toolsets and the skill index untouched.
  * ``focus`` — like ``auto``, but additionally collapses the toolset to the
    ``coding`` set + enabled MCP servers and demotes non-coding skill
    categories to names-only in the prompt's skill index (no skill is ever
    hidden). Explicit opt-in for a lean schema.
  * ``on`` — force the posture anywhere (incl. non-workspaces). Prompt-only.
  * ``off`` — disable entirely.

### class ContextProfile

> 继承: `object` ｜ 方法数: 0（公开 0）

A named operating posture. Pure data — consumers read these fields.

``toolset``      — collapse to this toolset (+ enabled MCP) when no explicit
                   selection is pinned; ``None`` keeps the platform default.
``guidance``     — operating brief injected into the stable system prompt;
                   ``""`` injects nothing.
``model_hint``   — routing preference key for smart model routing
                   (extension seam; not yet consumed by the router).
``memory_policy``— memory namespace/weighting hint (extension seam).
``compact_skill_categories`` — skill categories DEMOTED to names-only in
                   the system-prompt skill index under the opt-in ``focus``
                   mode. Never hidden: every skill name stays visible
                   (so memory-anchored recall keeps working) — only the
                   descriptions are dropped to cut index noise. Deny-list
                   semantics so unknown/custom categories keep full
                   entries.


### class RuntimeMode

> 继承: `object` ｜ 方法数: 5（公开 5）

The resolved operating posture for a session. Immutable by construction.

Built once via :func:`resolve_runtime_mode` and consumed by every domain
that cares about the coding/general distinction. Never mutate or re-resolve
mid-session — that would break the prompt cache.

#### property `kind(self) -> str`

#### property `is_coding(self) -> bool`

#### def `toolset_selection(self, config: Optional[dict[str, Any]] = None) -> Optional[list[str]]`

Toolset list for this posture, or ``None`` to keep the platform default.

Non-``None`` only under the opt-in ``focus`` mode. The default posture
is prompt-only: most strippable toolsets are off-by-default anyway, and
a user who explicitly enabled one (image-gen for frontend/game assets,
messaging for build notifications, …) keeps it while coding.

Callers apply this only when the user hasn't pinned an explicit
selection (``--toolsets``, ``HERMES_TUI_TOOLSETS``, …); they never
override a pin. Returns the profile's toolset plus enabled MCP servers.

#### def `system_blocks(self) -> list[str]`

Stable system-prompt blocks for this posture (brief + workspace).

The operating brief carries a model-family edit-format nudge appended
to it (one cached string, not a separate block) so the model is steered
toward the `patch` mode it handles best — see ``_edit_format_line``.

#### def `compact_skill_categories(self) -> frozenset[str]`

Skill categories to demote to names-only in the prompt's skill index.

Gated on the opt-in ``focus`` mode, like the toolset collapse: the
default posture leaves the skill index untouched. Users who didn't ask
for a lean prompt keep full entries for every category — index changes
under ``auto`` proved too surprising in practice, even names-only ones
(a demoted description is information the model no longer weighs when
deciding what to load).

Demoted — never hidden — even under ``focus``. An earlier revision
fully pruned these categories from the index, which caused silent
capability loss in a real workflow: agent-created skills are the
model's accumulated project memory (server-ops runbooks, learned
pitfalls, …), and models do not reliably reach for ``skills_list`` to
rediscover what the index stopped showing them. Names-only keeps every
skill loadable on recall while still cutting the description noise.


### class ProjectFacts

> 继承: `object` ｜ 方法数: 0（公开 0）

Structured project facts — the model's verify loop, detected once.

The same data that feeds the workspace snapshot, exposed structurally so
non-prompt consumers (e.g. the desktop verify UI) read it instead of
re-detecting and drifting from the prompt.


### 顶层函数

#### def `get_profile(name: str) -> ContextProfile`

Return a registered profile, falling back to ``general``.

#### def `resolve_runtime_mode(platform: Optional[str] = None, cwd: Optional[str | Path] = None, config: Optional[dict[str, Any]] = None, model: Optional[str] = None) -> RuntimeMode`

Resolve the operating posture once. Cheap — a handful of ``stat`` calls.

This is the single entry point every domain should call. The returned
object is immutable and safe to cache for the session. Detection itself is
intentionally *not* memoized (see ``_detect_profile_name``) so a long-lived
process can't pin a stale posture; callers resolve once per session and
hold the result. ``model`` is recorded only to steer edit-format guidance;
it never affects detection.

#### def `is_coding_context(platform: Optional[str] = None, cwd: Optional[str | Path] = None, config: Optional[dict[str, Any]] = None) -> bool`

Whether Hermes should operate in its coding posture right now.

#### def `coding_selection(platform: Optional[str] = None, cwd: Optional[str | Path] = None, config: Optional[dict[str, Any]] = None) -> Optional[list[str]]`

Toolset selection for the coding posture.

``None`` unless the user opted into ``focus`` mode AND the posture is
active — the default coding posture never overrides configured toolsets.

#### def `coding_system_blocks(platform: Optional[str] = None, cwd: Optional[str | Path] = None, config: Optional[dict[str, Any]] = None, model: Optional[str] = None) -> list[str]`

Stable system-prompt blocks for the current posture (empty when general).

``model`` steers the brief's edit-format nudge toward the model's family.

#### def `coding_compact_skill_categories(platform: Optional[str] = None, cwd: Optional[str | Path] = None, config: Optional[dict[str, Any]] = None) -> frozenset[str]`

Skill categories the active posture demotes to names-only in the index.

Empty outside the coding posture and outside the opt-in ``focus`` mode —
the default posture never touches the skill index. Under ``focus``,
demoted — never hidden: every skill name stays in the index and remains
loadable via ``skill_view`` / ``skills_list``; only descriptions are
dropped.

#### def `detect_project_facts(root: Path) -> ProjectFacts`

Detect manifests, package manager(s), verify commands, and context files.

Cheap: stat calls plus reads of a couple of small files. The single source
of truth for both the prompt snapshot (:func:`_project_facts`) and the
gateway's ``project.facts`` — so the UI never re-sniffs verify commands.

#### def `project_facts_for(cwd: Optional[str | Path] = None) -> Optional[dict[str, Any]]`

Structured project facts for ``cwd`` — ``None`` outside a workspace.

Same detection the system-prompt snapshot uses (git root, else marker root),
exposed for non-prompt consumers (the desktop verify UI) so they never
re-derive "are we coding?" or duplicate the verify-command sniffing.

#### def `build_coding_workspace_block(cwd: Optional[str | Path] = None) -> str`

Workspace snapshot for the system prompt (empty outside a workspace).

Git state (branch/status/commits) when the cwd is in a repo, plus detected
project facts (manifest, package manager, verify commands, context files)
— so marker-only (non-git) projects still get a snapshot.


## agent.context_breakdown

### 模块文档

Live session context-window breakdown for UI surfaces.

Estimates how the next provider request is composed: system prompt tiers,
tool schemas, and conversation history. Uses the same rough char/4 heuristic
as ``agent.model_metadata.estimate_request_tokens_rough`` so numbers align
with compression thresholds — not exact tokenizer counts.

### 顶层函数

#### def `compute_session_context_breakdown(agent: Any, messages: Optional[List[dict]] = None) -> Dict[str, Any]`

Return a Cursor-style context usage breakdown for one live agent.


## agent.context_compressor

### 模块文档

Automatic context window compression for long conversations.

Self-contained class with its own OpenAI client for summarization.
Uses auxiliary model (cheap/fast) to summarize middle turns while
protecting head and tail context.

Improvements over v2:
  - Structured summary template with Resolved/Pending question tracking
  - Filter-safe summarizer preamble that treats prior turns as source material
  - Historical (reference-only) section headings replace "Next Steps"/"Remaining Work" to avoid reading as active instructions
  - Clear separator when summary merges into tail message
  - Iterative summary updates (preserves info across multiple compactions)
  - Token-budget tail protection instead of fixed message count
  - Tool output pruning before LLM summarization (cheap pre-pass)
  - Scaled summary budget (proportional to compressed content)
  - Richer tool call/result detail in summarizer input

### class ContextCompressor

> 继承: `ContextEngine` ｜ 方法数: 50（公开 13）

Default context engine — compresses conversation context via lossy summarization.

Algorithm:
  1. Prune old tool results (cheap, no LLM call)
  2. Protect head messages (system prompt + first exchange)
  3. Protect tail messages by token budget (most recent ~20K tokens)
  4. Summarize middle turns with structured LLM prompt
  5. On subsequent compactions, iteratively update the previous summary

#### property `name(self) -> str`

#### def `on_session_reset(self) -> None`

Reset all per-session state for /new or /reset.

#### def `on_session_end(self, session_id: str, messages: List[Dict[str, Any]]) -> None`

Clear all per-session compaction state at a real session boundary.

Session end (CLI exit, gateway expiry, session-id rotation) goes
through this method rather than ``on_session_reset()`` (/new, /reset).
The original fix (#38788) only cleared ``_previous_summary``, but the
same cross-session contamination risk applies to every per-session
variable that ``on_session_reset()`` clears: stale
``_ineffective_compression_count`` can suppress compression in a
subsequent live session; ``_summary_failure_cooldown_until`` can block
summary generation; ``_last_compress_aborted`` can make callers think
compression is still aborted; ``_last_aux_model_failure_*`` can surface
stale error warnings; ``_last_summary_dropped_count`` /
``_last_summary_fallback_used`` can produce misleading user warnings.

``compress()`` already guards ``_previous_summary`` leakage at the
point of use; this is defense-in-depth that resets the full per-session
surface the moment the owning session ends.

#### def `bind_session_state(self, session_db: Any = None, session_id: str = '') -> None`

Bind the current session row so durable cooldowns can round-trip.

#### def `on_session_start(self, session_id: str, **kwargs) -> None`

Bind session-scoped compression state for a new or resumed session.

#### def `record_completed_compaction(self, used_fallback: bool = False) -> None`

Record one completed boundary and its summary quality.

#### def `get_active_compression_failure_cooldown(self, refresh: bool = False) -> Optional[Dict[str, Any]]`

Return the live compression-failure cooldown for the bound session.

#### def `update_model(self, model: str, context_length: int, base_url: str = '', api_key: Any = '', provider: str = '', api_mode: str = '', max_tokens: int | None = None) -> None`

Update model info after a model switch or fallback activation.

#### def `__init__(model: str, threshold_percent: float = 0.5, protect_first_n: int = 3, protect_last_n: int = 20, summary_target_ratio: float = 0.2, quiet_mode: bool = False, summary_model_override: str = None, base_url: str = '', api_key: str = '', config_context_length: int | None = None, provider: str = '', api_mode: str = '', abort_on_summary_failure: bool = False, max_tokens: int | None = None)`

#### def `update_from_response(self, usage: Dict[str, Any])`

Update tracked token usage from API response.

#### def `should_defer_preflight_to_real_usage(self, rough_tokens: int) -> bool`

Return True when a high rough preflight estimate is known-noisy.

``estimate_request_tokens_rough(..., tools=...)`` intentionally
overestimates schema-heavy requests so Hermes compresses before a
provider rejects the payload. After a successful compressed API call,
though, provider ``prompt_tokens`` are a better signal than repeating
compaction from the same rough schema overhead. Defer only while the
rough estimate has grown modestly since a request the provider proved
fit under the threshold.

#### def `should_compress(self, prompt_tokens: int = None) -> bool`

Check if context exceeds the compression threshold.

Includes anti-thrashing protection: if the last two compressions
each saved less than 10%, skip compression to avoid infinite loops
where each pass removes only 1-2 messages.

#### def `has_content_to_compress(self, messages: List[Dict[str, Any]]) -> bool`

Return True if there is a non-empty middle region to compact.

Overrides the ABC default so the gateway ``/compress`` guard can
skip the LLM call when the transcript is still entirely inside
the protected head/tail.

#### def `compress(self, messages: List[Dict[str, Any]], current_tokens: Optional[int] = None, focus_topic: Optional[str] = None, force: bool = False, memory_context: str = '') -> List[Dict[str, Any]]`

Compress conversation messages by summarizing middle turns.

Algorithm:
  1. Prune old tool results (cheap pre-pass, no LLM call)
  2. Protect head messages (system prompt + first exchange)
  3. Find tail boundary by token budget (~20K tokens of recent context)
  4. Summarize middle turns with structured LLM prompt
  5. On re-compression, iteratively update the previous summary

After compression, orphaned tool_call / tool_result pairs are cleaned
up so the API never receives mismatched IDs.

Args:
    focus_topic: Optional focus string for guided compression.  When
        provided, the summariser will prioritise preserving information
        related to this topic and be more aggressive about compressing
        everything else.  Inspired by Claude Code's ``/compact``.
    force: If True, clear any active summary-failure cooldown before
        running so a manual ``/compress`` can retry immediately after
        an auto-compression abort.  Auto-compress callers pass False.
    memory_context: Optional provider-supplied context to preserve in
        the summary prompt. Whitespace-only values are ignored.


## agent.context_engine

### 模块文档

Abstract base class for pluggable context engines.

A context engine controls how conversation context is managed when
approaching the model's token limit. The built-in ContextCompressor
is the default implementation. Third-party engines (e.g. LCM) can
replace it via the plugin system or by being placed in the
``plugins/context_engine/<name>/`` directory.

Selection is config-driven: ``context.engine`` in config.yaml.
Default is ``"compressor"`` (the built-in). Only one engine is active.

The engine is responsible for:
  - Deciding when compaction should fire
  - Performing compaction (summarization, DAG construction, etc.)
  - Optionally exposing tools the agent can call (e.g. lcm_grep)
  - Tracking token usage from API responses

Lifecycle:
  1. Engine is instantiated and registered (plugin register() or default)
  2. on_session_start() called when a conversation begins
  3. update_from_response() called after each API response with usage data
  4. should_compress() checked after each turn
  5. compress() called when should_compress() returns True
  6. on_session_end() called at real session boundaries (CLI exit, /reset,
     gateway session expiry) — NOT per-turn

### class ContextEngine

> 继承: `ABC` ｜ 方法数: 14（公开 14）

Base class all context engines must implement.

#### property `name(self) -> str`

Short identifier (e.g. 'compressor', 'lcm').

#### def `update_from_response(self, usage: Dict[str, Any]) -> None`

Update tracked token usage from an API response.

Called after every LLM call with a normalized usage dict. The legacy
keys ``prompt_tokens``, ``completion_tokens``, and ``total_tokens``
are always present. Newer hosts also include canonical buckets:
``input_tokens``, ``output_tokens``, ``cache_read_tokens``,
``cache_write_tokens``, and ``reasoning_tokens``. Engines should
treat those fields as optional for compatibility with older hosts.

#### def `should_compress(self, prompt_tokens: int = None) -> bool`

Return True if compaction should fire this turn.

#### def `compress(self, messages: List[Dict[str, Any]], current_tokens: Optional[int] = None, focus_topic: Optional[str] = None, force: bool = False, memory_context: str = '') -> List[Dict[str, Any]]`

Compact the message list and return the new message list.

This is the main entry point. The engine receives the full message
list and returns a (possibly shorter) list that fits within the
context budget. The implementation is free to summarize, build a
DAG, or do anything else — as long as the returned list is a valid
OpenAI-format message sequence.

Args:
    focus_topic: Optional topic string from manual ``/compress <focus>``.
        Engines that support guided compression should prioritise
        preserving information related to this topic.  Engines that
        don't support it may simply ignore this argument.
    force: Whether a user-requested compression should bypass an
        engine-owned cooldown. Engines without cooldowns may ignore it.
    memory_context: Text returned by memory providers immediately before
        compaction. Summarizing engines should include non-empty text in
        their handoff prompt. Older engines may omit this parameter; the
        host filters unsupported optional arguments by signature.

#### def `should_compress_preflight(self, messages: List[Dict[str, Any]]) -> bool`

Quick rough check before the API call (no real token count yet).

Default returns False (skip pre-flight). Override if your engine
can do a cheap estimate.

#### def `should_defer_preflight_to_real_usage(self, rough_tokens: int) -> bool`

Return True when preflight should trust recent real usage instead.

Built-in compression uses this to avoid re-compacting from known-noisy
rough estimates after a compressed request has already fit. Third-party
engines can ignore it safely.

#### def `has_content_to_compress(self, messages: List[Dict[str, Any]]) -> bool`

Quick check: is there anything in ``messages`` that can be compacted?

Used by the gateway ``/compress`` command as a preflight guard —
returning False lets the gateway report "nothing to compress yet"
without making an LLM call.

Default returns True (always attempt).  Engines with a cheap way
to introspect their own head/tail boundaries should override this
to return False when the transcript is still entirely protected.

#### def `on_session_start(self, session_id: str, **kwargs) -> None`

Called when a new conversation session begins.

Use this to load persisted state (DAG, store) for the session.
kwargs may include hermes_home, platform, model, etc.

#### def `on_session_end(self, session_id: str, messages: List[Dict[str, Any]]) -> None`

Called at real session boundaries (CLI exit, /reset, gateway expiry).

Use this to flush state, close DB connections, etc.
NOT called per-turn — only when the session truly ends.

#### def `on_session_reset(self) -> None`

Called on /new or /reset. Reset per-session state.

Default resets compression_count and token tracking.

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

Return tool schemas this engine provides to the agent.

Default returns empty list (no tools). LCM would return schemas
for lcm_grep, lcm_describe, lcm_expand here.

#### def `handle_tool_call(self, name: str, args: Dict[str, Any], **kwargs) -> str`

Handle a tool call from the agent.

Only called for tool names returned by get_tool_schemas().
Must return a JSON string.

kwargs may include:
  messages: the current in-memory message list (for live ingestion)

#### def `get_status(self) -> Dict[str, Any]`

Return status dict for display/logging.

Default returns the standard fields run_agent.py expects.

#### def `update_model(self, model: str, context_length: int, base_url: str = '', api_key: str = '', provider: str = '', api_mode: str = '') -> None`

Called when the user switches models or on fallback activation.

Default updates context_length and recalculates threshold_tokens
from threshold_percent. Override if your engine needs more
(e.g. recalculate DAG budgets, switch summary models).


### 顶层函数

#### def `sanitize_memory_context(memory_context: str) -> str`

Prepare provider context for a context-engine/LLM egress boundary.


## agent.context_references

### class ContextReference

> 继承: `object` ｜ 方法数: 0（公开 0）


### class ContextReferenceResult

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `parse_context_references(message: str) -> list[ContextReference]`

#### def `preprocess_context_references(message: str, cwd: str | Path, context_length: int, url_fetcher: Callable[[str], str | Awaitable[str]] | None = None, allowed_root: str | Path | None = None) -> ContextReferenceResult`

#### def `preprocess_context_references_async(message: str, cwd: str | Path, context_length: int, url_fetcher: Callable[[str], str | Awaitable[str]] | None = None, allowed_root: str | Path | None = None) -> ContextReferenceResult`


## agent.conversation_compression

### 模块文档

Context compression — extract the AIAgent methods that drive summarisation.

Three concerns live here:

* :func:`check_compression_model_feasibility` — startup probe of the
  configured auxiliary compression model.  Warns when the aux context
  window can't fit the main model's compression threshold; auto-lowers
  the session threshold when possible; hard-rejects auxes below
  ``MINIMUM_CONTEXT_LENGTH``.

* :func:`replay_compression_warning` — re-emit a stored warning through
  the gateway ``status_callback`` once it's wired up (the callback is
  set after :class:`AIAgent` construction).

* :func:`compress_context` — the actual compression call.  Runs the
  configured compressor, splits the SQLite session, rotates the
  session_id, notifies plugin context engines / memory providers, and
  returns the compressed message list and active system prompt.

* :func:`try_shrink_image_parts_in_messages` — image-too-large recovery
  helper that re-encodes ``data:image/...;base64,...`` parts at a smaller
  size so retries can fit under provider ceilings (Anthropic's 5 MB).

``run_agent`` keeps thin wrappers for each so existing call sites
(``self._compress_context(...)``) keep working.  Tests that exercise
these paths see no behavioural change.

### 顶层函数

#### def `check_compression_model_feasibility(agent: Any) -> None`

Warn at session start if the auxiliary compression model's context
window is smaller than the main model's compression threshold.

When the auxiliary model cannot fit the content that needs summarising,
compression will either fail outright (the LLM call errors) or produce
a severely truncated summary.

Called during ``AIAgent.__init__`` so CLI users see the warning
immediately (via ``_vprint``).  The gateway sets ``status_callback``
*after* construction, so :func:`replay_compression_warning` re-sends
the stored warning through the callback on the first
``run_conversation()`` call.

**异常**: `ValueError`

#### def `replay_compression_warning(agent: Any) -> None`

Re-send the compression warning through ``status_callback``.

During ``__init__`` the gateway's ``status_callback`` is not yet
wired, so ``_emit_status`` only reaches ``_vprint`` (CLI).  This
method is called once at the start of the first
``run_conversation()`` — by then the gateway has set the callback,
so every platform (Telegram, Discord, Slack, etc.) receives the
warning.

#### def `conversation_history_after_compression(agent: Any, messages: list) -> Optional[list]`

Return the correct flush baseline after a compression boundary.

Legacy compression rotates to a fresh child session. That child has not
seen the compacted transcript through the normal same-turn flush path yet,
so callers must clear ``conversation_history`` to ``None`` and let the next
persistence call write the whole compacted list.

In-place compaction is different: ``archive_and_compact()`` has already
soft-archived the previous active rows and inserted ``messages`` as the new
active live transcript under the same session id. If the same agent turn
continues with ``conversation_history=None``, the identity-based flush path
treats those already-persisted compacted dicts as new and appends them a
second time, doubling the active context and retriggering compression.

A shallow copy is intentional: it captures the current compacted dict
identities as history while allowing later same-turn appends to remain new.

#### def `compress_context(agent: Any, messages: list, system_message: str, approx_tokens: Optional[int] = None, task_id: str = 'default', focus_topic: Optional[str] = None, force: bool = False) -> Tuple[list, str]`

Compress conversation context and split the session in SQLite.

Args:
    agent: The owning :class:`AIAgent`.
    messages: Current message history (will be summarised).
    system_message: Current system prompt; used when compression needs a
        rebuilt cached prompt.
    approx_tokens: Pre-compression token estimate, logged for ops.
    task_id: Tool task scope (used for clearing file-read dedup state).
    focus_topic: Optional focus string for guided compression — the
        summariser will prioritise preserving information related to
        this topic.  Inspired by Claude Code's ``/compact <focus>``.
    force: If True, bypass any active summary-failure cooldown.  Set
        by the manual ``/compress`` slash command so users can retry
        immediately after an auto-compress abort.  Auto-compress
        callers use the default ``False``.

Returns:
    ``(compressed_messages, new_system_prompt)`` tuple.  When
    compression aborts (aux LLM failed to produce a usable summary),
    returns the original messages unchanged and the existing system
    prompt — the session is NOT rotated.  Callers should detect the
    no-op via ``len(returned) == len(input)`` and stop the retry loop.

#### def `try_shrink_image_parts_in_messages(api_messages: list, max_dimension: int = 8000) -> bool`

Re-encode all native image parts at a smaller size to recover from
image-too-large errors (Anthropic 5 MB, unknown other providers).

Mutates ``api_messages`` in place. Returns True if any image part was
actually replaced, False if there were no image parts to shrink or
Pillow couldn't help (caller should surface the original error).

Strategy: look for ``image_url`` / ``input_image`` parts carrying a
``data:image/...;base64,...`` payload, plus Anthropic-native
``{"type": "image", "source": {"type": "base64", ...}}`` blocks.
For each one whose encoded size exceeds 4 MB (a safe target that slides
under Anthropic's 5 MB ceiling with header overhead) or whose longest side
exceeds ``max_dimension``, write the base64 to a tempfile, call
``vision_tools._resize_image_for_vision`` to produce a smaller data
URL, and substitute it in place.

Non-data-URL images (http/https URLs) are not touched — the provider
fetches those itself and the size limit is different.


## agent.conversation_loop

### 模块文档

The agent conversation loop — extracted from ``run_agent.AIAgent``.

This is the biggest single chunk pulled out of ``run_agent.py``: the
roughly 3,900-line :func:`run_conversation` body that drives one user
turn through the agent (model call, tool dispatch, retries, fallbacks,
compression, post-turn hooks, background memory/skill review nudges).

The function takes the parent ``AIAgent`` instance as its first
argument (``agent``) and accesses its state via attribute lookup.
``_ra().AIAgent.run_conversation`` is now a thin forwarder.

Symbols that production code or tests patch on ``run_agent`` directly
(``handle_function_call``, ``_set_interrupt``, ``OpenAI``, ...) are
resolved through :func:`_ra` so those patches keep working.

### 顶层函数

#### def `run_conversation(agent, user_message: Any, system_message: str = None, conversation_history: List[Dict[str, Any]] = None, task_id: str = None, stream_callback: Optional[callable] = None, persist_user_message: Optional[Any] = None, persist_user_timestamp: Optional[float] = None, moa_config: Optional[dict[str, Any]] = None) -> Dict[str, Any]`

Run a complete conversation with tool calling until completion.

Args:
    user_message (str): The user's message/question
    system_message (str): Custom system message (optional, overrides ephemeral_system_prompt if provided)
    conversation_history (List[Dict]): Previous conversation messages (optional)
    task_id (str): Unique identifier for this task to isolate VMs between concurrent tasks (optional, auto-generated if not provided)
    stream_callback: Optional callback invoked with each text delta during streaming.
        Used by the TTS pipeline to start audio generation before the full response.
        When None (default), API calls use the standard non-streaming path.
    persist_user_message: Optional clean user message to store in
        transcripts/history when user_message contains API-only
        synthetic prefixes.
    persist_user_timestamp: Optional platform event timestamp to store
        as metadata on that persisted user message.
            or queuing follow-up prefetch work.

Returns:
    Dict: Complete conversation result with final response and message history


## agent.copilot_acp_client

### 模块文档

OpenAI-compatible shim that forwards Hermes requests to `copilot --acp`.

This adapter lets Hermes treat the GitHub Copilot ACP server as a chat-style
backend. Each request starts a short-lived ACP session, sends the formatted
conversation as a single prompt, collects text chunks, and converts the result
back into the minimal shape Hermes expects from an OpenAI client.

### class CopilotACPClient

> 继承: `object` ｜ 方法数: 5（公开 1）

Minimal OpenAI-client-compatible facade for Copilot ACP.

#### def `__init__(api_key: str | None = None, base_url: str | None = None, default_headers: dict[str, str] | None = None, acp_command: str | None = None, acp_args: list[str] | None = None, acp_cwd: str | None = None, command: str | None = None, args: list[str] | None = None, **_: Any)`

#### def `close(self) -> None`


## agent.credential_persistence

### 模块文档

Credential-pool disk-boundary sanitization helpers.

These helpers define which credential-pool entries are references to borrowed
runtime secrets and strip raw values before those entries are written to
``auth.json``.  They intentionally have no dependency on ``hermes_cli.auth`` so
both the pool model and the final auth-store write boundary can share the same
policy without import cycles.

### 顶层函数

#### def `is_borrowed_credential_source(source: Any, provider_id: Any = None) -> bool`

Return True when ``source`` points at a borrowed/reference-only secret.

#### def `sanitize_borrowed_credential_payload(payload: Mapping[str, Any], provider_id: Any = None) -> Dict[str, Any]`

Return a disk-safe credential-pool payload.

Owned sources (manual entries and Hermes-owned OAuth/device-code state)
pass through unchanged.  Borrowed/reference-only sources keep labels,
source refs, status/cooldown metadata, counters, and a non-reversible
fingerprint, but raw secret value fields are removed.


## agent.credential_pool

### 模块文档

Persistent multi-credential pool for same-provider failover.

### class PooledCredential

> 继承: `object` ｜ 方法数: 6（公开 4）

#### classmethod `from_dict(cls, provider: str, payload: Dict[str, Any]) -> PooledCredential`

#### def `to_dict(self) -> Dict[str, Any]`

#### property `runtime_api_key(self) -> str`

#### property `runtime_base_url(self) -> Optional[str]`


### class CredentialPool

> 继承: `object` ｜ 方法数: 34（公开 15）

#### def `__init__(provider: str, entries: List[PooledCredential])`

#### def `has_credentials(self) -> bool`

#### def `has_available(self) -> bool`

True if at least one entry is not currently in exhaustion cooldown.

#### def `entries(self) -> List[PooledCredential]`

#### def `current(self) -> Optional[PooledCredential]`

#### def `select(self) -> Optional[PooledCredential]`

#### def `peek(self) -> Optional[PooledCredential]`

#### def `mark_exhausted_and_rotate(self, status_code: Optional[int], error_context: Optional[Dict[str, Any]] = None, api_key_hint: Optional[str] = None) -> Optional[PooledCredential]`

#### def `acquire_lease(self, credential_id: Optional[str] = None) -> Optional[str]`

Acquire a soft lease on a credential.

If a specific credential_id is provided, lease that entry directly.
Otherwise prefer the least-leased available credential, using priority as
a stable tie-breaker. When every credential is already at the soft cap,
still return the least-leased one instead of blocking.

#### def `release_lease(self, credential_id: str) -> None`

Release a previously acquired credential lease.

#### def `try_refresh_current(self) -> Optional[PooledCredential]`

#### def `try_refresh_matching(self, api_key_hint: Optional[str] = None) -> Optional[PooledCredential]`

Force-refresh the entry that supplied ``api_key_hint``.

Direct provider integrations may reload the pool after a request has
already failed, so they cannot rely on ``current_id`` identifying the
issuing credential. With no hint, select an entry without first doing
the normal proactive refresh; the forced refresh below must consume a
rotating refresh token exactly once.

#### def `reset_statuses(self) -> int`

#### def `remove_index(self, index: int) -> Optional[PooledCredential]`

#### def `resolve_target(self, target: Any) -> Tuple[Optional[int], Optional[PooledCredential], Optional[str]]`

#### def `add_entry(self, entry: PooledCredential) -> PooledCredential`


### 顶层函数

#### def `label_from_token(token: str, fallback: str) -> str`

#### def `get_custom_provider_pool_key(base_url: Optional[str], provider_name: Optional[str] = None) -> Optional[str]`

Look up the custom_providers list in config.yaml and return 'custom:<name>' for a matching base_url.

When provider_name is given, prefer matching by name first (solving the case where
multiple custom providers share the same base_url but have different API keys).
Falls back to base_url matching when no name match is found.

Returns None if no match is found.

#### def `list_custom_pool_providers() -> List[str]`

Return all 'custom:*' pool keys that have entries in auth.json.

#### def `get_pool_strategy(provider: str) -> str`

Return the configured selection strategy for a provider.

#### def `credential_pool_matches_provider(pool_or_provider: Any, provider: Optional[str], base_url: Optional[str] = None) -> bool`

Return whether a pool belongs to the requested runtime provider.

Named custom endpoints intentionally use two identities: the live agent is
``custom`` while its pool is keyed ``custom:<name>``. Accept that pair only
when the runtime base URL resolves to the exact same custom pool key.
Empty string identities fail closed. Legacy pool adapters without a
``provider`` attribute remain compatible; production pools are scoped.

#### def `load_pool(provider: str) -> CredentialPool`


## agent.credential_sources

### 模块文档

Unified removal contract for every credential source Hermes reads from.

Hermes seeds its credential pool from many places:

    env:<VAR>     — os.environ / ~/.hermes/.env
    claude_code   — ~/.claude/.credentials.json
    hermes_pkce   — ~/.hermes/.anthropic_oauth.json
    device_code   — auth.json providers.<provider> (nous, openai-codex, ...)
    qwen-cli      — ~/.qwen/oauth_creds.json
    gh_cli        — gh auth token
    config:<name> — custom_providers config entry
    model_config  — model.api_key when model.provider == "custom"
    manual        — user ran `hermes auth add`

Each source has its own reader inside ``agent.credential_pool._seed_from_*``
(which keep their existing shape — we haven't restructured them).  What we
unify here is **removal**:

    ``hermes auth remove <provider> <N>`` must make the pool entry stay gone.

Before this module, every source had an ad-hoc removal branch in
``auth_remove_command``, and several sources had no branch at all — so
``auth remove`` silently reverted on the next ``load_pool()`` call for
qwen-cli, nous device_code (partial), hermes_pkce, copilot gh_cli, and
custom-config sources.

Now every source registers a ``RemovalStep`` that does exactly three things
in the same shape:

    1. Clean up whatever externally-readable state the source reads from
       (.env line, auth.json block, OAuth file, etc.)
    2. Suppress the ``(provider, source_id)`` in auth.json so the
       corresponding ``_seed_from_*`` branch skips the upsert on re-load
    3. Return ``RemovalResult`` describing what was cleaned and any
       diagnostic hints the user should see (shell-exported env vars,
       external credential files we deliberately don't delete, etc.)

Adding a new credential source is:
    - wire up a reader branch in ``_seed_from_*`` (existing pattern)
    - gate that reader behind ``is_source_suppressed(provider, source_id)``
    - register a ``RemovalStep`` here

No more per-source if/elif chain in ``auth_remove_command``.

### class RemovalResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Outcome of removing a credential source.

Attributes:
    cleaned: Short strings describing external state that was actually
        mutated (``"Cleared XAI_API_KEY from .env"``,
        ``"Cleared openai-codex OAuth tokens from auth store"``).
        Printed as plain lines to the user.
    hints: Diagnostic lines ABOUT state the user may need to clean up
        themselves or is deliberately left intact (shell-exported env
        var, Claude Code credential file we don't delete, etc.).
        Printed as plain lines to the user.  Always non-destructive.
    suppress: Whether to call ``suppress_credential_source`` after
        cleanup so future ``load_pool`` calls skip this source.
        Default True — almost every source needs this to stay sticky.
        The only legitimate False is ``manual`` entries, which aren't
        seeded from anywhere external.


### class RemovalStep

> 继承: `object` ｜ 方法数: 1（公开 1）

How to remove one specific credential source cleanly.

Attributes:
    provider: Provider pool key (``"xai"``, ``"anthropic"``, ``"nous"``, ...).
        Special value ``"*"`` means "matches any provider" — used for
        sources like ``manual`` that aren't provider-specific.
    source_id: Source identifier as it appears in
        ``PooledCredential.source``.  May be a literal (``"claude_code"``)
        or a prefix pattern matched via ``match_fn``.
    match_fn: Optional predicate overriding literal ``source_id``
        matching.  Gets the removed entry's source string.  Used for
        ``env:*`` (any env-seeded key), ``config:*`` (any custom
        pool), and ``manual:*`` (any manual-source variant).
    remove_fn: ``(provider, removed_entry) -> RemovalResult``.  Does the
        actual cleanup and returns what happened for the user.
    description: One-line human-readable description for docs / tests.

#### def `matches(self, provider: str, source: str) -> bool`


### 顶层函数

#### def `register(step: RemovalStep) -> RemovalStep`

#### def `find_removal_step(provider: str, source: str) -> Optional[RemovalStep]`

Return the first matching RemovalStep, or None if unregistered.

Unregistered sources fall through to the default remove path in
``auth_remove_command``: the pool entry is already gone (that happens
before dispatch), no external cleanup, no suppression.  This is the
correct behaviour for ``manual`` entries — they were only ever stored
in the pool, nothing external to clean up.


## agent.credits_tracker

### 模块文档

Credits tracking for Nous inference API responses.

Parses x-nous-credits-* (and optional x-nous-tool-pool-*) headers from
inference responses into a validated CreditsState dataclass.  Provides
depletion detection (paid_access), subscription-cap used_fraction, and
warn-once schema-version gating.  This is the hardened parser used by all
live consumers (run_agent, tui_gateway) — not a dev-only shim.

Header schema (x-nous-credits-* family):
    x-nous-credits-version                    contract/schema version
    x-nous-credits-remaining-micros           total remaining balance (micros)
    x-nous-credits-remaining-usd              same, formatted USD string
    x-nous-credits-subscription-micros        subscription balance (SIGNED; may be negative/debt)
    x-nous-credits-subscription-usd           same, formatted USD string
    x-nous-credits-subscription-limit-micros  subscription cap (PAIRED/optional)
    x-nous-credits-subscription-limit-usd     same, formatted USD string (PAIRED/optional)
    x-nous-credits-rollover-micros            rolled-over balance (micros)
    x-nous-credits-purchased-micros           purchased balance (micros)
    x-nous-credits-purchased-usd              same, formatted USD string
    x-nous-credits-denominator-kind           "subscription_cap" | "none"
    x-nous-credits-paid-access                "true" | "false" (STRING!)
    x-nous-credits-disabled-reason            reason string (header omitted when null)
    x-nous-credits-as-of-ms                   server-side timestamp (ms epoch)

Tool-pool headers use a SEPARATE prefix:
    x-nous-tool-pool-micros                   tool-pool balance (micros)
    x-nous-tool-pool-gated-off                "true" | "false" (STRING!)

Money is handled as micros ints only; *_usd values are preserved verbatim as
the raw strings the server sent (never re-parsed to float).

### class CreditsState

> 继承: `object` ｜ 方法数: 4（公开 4）

Full credits state parsed from x-nous-credits-* response headers.

#### property `has_data(self) -> bool`

#### property `age_seconds(self) -> float`

#### property `depleted(self) -> bool`

True when the account has lost paid access.

Keyed off ``paid_access == False`` ONLY — never ``remaining_micros == 0``,
which would give a false positive whenever the balance is zero but access
is still live (e.g. subscription renewal pending).

#### property `used_fraction(self) -> Optional[float]`

Fraction of the subscription cap consumed, in [0.0, 1.0].

Computable only when ``subscription_limit_micros`` is a truthy (non-zero,
non-None) int.  Guarded on the LIMIT FIELD, not ``denominator_kind`` —
the limit field is the real denominator; ``denominator_kind`` is metadata.
Returns None when there is no computable denominator (no limit, or limit==0).


### class AgentNotice

> 继承: `object` ｜ 方法数: 0（公开 0）

A structured, driver-agnostic out-of-band notice.

The agent fires these via ``AIAgent.notice_callback`` (and clears them via
``notice_clear_callback``); each driver renders it its own way — the TUI as a
status-bar override, the CLI as a console line, etc. v1 credits notices are all
``kind="sticky"``; ``kind``/``ttl_ms`` are kept fully expressive so a future
config/slash-command can switch them to TTL without touching the policy (a
single default seam — see L4).


### 顶层函数

#### def `is_free_tier_model(model: str, base_url: str = '') -> bool`

Return True when *model* is a Nous free-tier model, using ONLY local data.

Two signals, both zero-network:

1. The ``:free`` suffix — the canonical Nous free SKU marker (e.g.
   ``nvidia/nemotron-3-ultra:free``). Free by construction on the API side
   (spend is forced to 0 for ``:free`` ids).
2. A peek into the in-process pricing cache in ``hermes_cli.models``
   (populated when the model picker fetched ``/v1/models`` pricing for
   *base_url*). PEEK ONLY — a cache miss never triggers a fetch. This is
   CLI/TUI-session best-effort: gateway sessions never run the picker's
   pricing fetch, so suppression there rests entirely on the ``:free``
   suffix (which all Nous free SKUs carry).

Fail-open to False (the depleted notice still shows) on any error: wrongly
showing the warning is recoverable noise; wrongly hiding it on a paid model
would mask a real billing block.

#### def `evaluate_credits_notices(state: CreditsState, latch: dict, model_is_free: bool = False) -> tuple[list[AgentNotice], list[str]]`

Reconcile credits notices against the latch. Mutates ``latch`` IN PLACE.

latch = {"active": set[str], "seen_below_90": bool, "usage_band": Optional[int]}.

``model_is_free``: True when the session's active model is a Nous free-tier
model (see :func:`is_free_tier_model`). Suppresses the ``credits.depleted``
notice — a depleted account on a free model can keep inferencing, so the
error banner is noise (and confuses free-tier users who never had credits).
Suppression does NOT emit the "restored" success notice; that fires only on
a genuine ``paid_access`` flip back to True.

Returns ``(to_show: list[AgentNotice], to_clear: list[str])``.
Caller emits to_clear FIRST, then to_show.

Pure function — no I/O, no agent/run_agent imports.

#### def `parse_credits_headers(headers: Mapping[str, str], provider: str = '') -> Optional[CreditsState]`

Parse x-nous-credits-* (and x-nous-tool-pool-*) headers into a CreditsState.

Returns None (miss) on ANY of:
- No ``x-nous-credits-version`` header present.
- Version != 1 (> 1 also emits a one-time logger.warning).
- Any ``*_micros`` field is non-integer, or negative for a non-subscription field.
- Any ``*_usd`` field doesn't match ``^-?\d+\.\d{2}$``.
- ``denominator_kind`` is not in {"subscription_cap", "none"}.
- ``paid_access`` / ``tool_pool_gated_off`` is not exactly "true"/"false".
- ``as_of_ms`` is not a valid integer.
- Any unexpected exception.

Fail-open on the subscription_limit pair: a half-pair (only -micros or only
-usd present) is treated as both-absent; the overall parse STILL SUCCEEDS
but with subscription_limit_micros/usd both None.

#### def `dev_fixture_credits_state() -> Optional[CreditsState]`

Return a fixture CreditsState for HERMES_DEV_CREDITS_FIXTURE, or None.

The env value is a state name, OR a path to a file whose contents are a state
name (re-read each call → flip states live without a restart). Unknown name /
"clear" / "none" / unset → None (normal behaviour). Throwaway test scaffolding.

Hard prod-leak guard: a fixture applies ONLY when the dev flag HERMES_DEV_CREDITS
is also on, so a stray HERMES_DEV_CREDITS_FIXTURE (leaked into a shell profile, a
container env, a launch plist, …) can never surface fabricated balances/notices
on a real account.

#### def `seed_credits_at_session_start(agent) -> bool`

Hydrate agent._credits_state from /api/oauth/account (or a dev fixture) and
fire the notice policy, so depletion / usage-band warnings show at session OPEN.

Shared by (a) the TUI/desktop agent build (fires at "ready", before any message)
and (b) the first-turn conversation setup (fallback for plain CLI / when the
build path didn't seed). Idempotent: a second call is a no-op once a seed or a
real header has already populated _credits_state.

Returns True if it seeded this call, False otherwise (not nous / already seeded /
fail-open error). Never raises — credits must never block session startup.


## agent.curator

### 模块文档

Curator — background skill maintenance orchestrator.

The curator is an auxiliary-model task that periodically reviews agent-created
skills and maintains the collection. It runs inactivity-triggered (no cron
daemon): when the agent is idle and the last curator run was longer than
``interval_hours`` ago, ``maybe_run_curator()`` spawns a forked AIAgent to do
the review.

Responsibilities:
  - Auto-transition lifecycle states based on derived skill activity timestamps
  - Spawn a background review agent that can pin / archive / consolidate /
    patch agent-created skills via skill_manage
  - Persist curator state (last_run_at, paused, etc.) in .curator_state

Strict invariants:
  - Only touches agent-created skills (see tools/skill_usage.is_agent_created)
  - Never auto-deletes — only archives. Archive is recoverable.
  - Pinned skills bypass all auto-transitions
  - Uses the auxiliary client; never touches the main session's prompt cache

### 顶层函数

#### def `load_state() -> Dict[str, Any]`

#### def `save_state(data: Dict[str, Any]) -> None`

#### def `set_paused(paused: bool) -> None`

#### def `is_paused() -> bool`

#### def `is_enabled() -> bool`

Default ON when no config says otherwise.

#### def `get_interval_hours() -> int`

#### def `get_min_idle_hours() -> float`

#### def `get_stale_after_days() -> int`

#### def `get_archive_after_days() -> int`

#### def `get_prune_builtins() -> bool`

Whether the curator may prune (archive) bundled built-in skills too.

ON by default. When on, built-ins become curation candidates and are
archived after the same inactivity period as agent-created skills, with a
suppression list keeping them archived across `hermes update` re-seeds.
Hub-installed skills are never pruned regardless of this flag.

#### def `get_consolidate() -> bool`

Whether the curator runs its LLM consolidation (umbrella-building) pass.

OFF by default. When off, a curator run does ONLY the deterministic
inactivity prune (mark stale / archive long-unused skills) and skips the
forked aux-model review entirely — no consolidation, no umbrella-building,
no aux-model cost. Set ``curator.consolidate: true`` to opt back into the
LLM pass that merges overlapping skills into class-level umbrellas.

The explicit ``hermes curator run --consolidate`` flag overrides this for
a single invocation regardless of the config value.

#### def `should_run_now(now: Optional[datetime] = None) -> bool`

Return True if the curator should run immediately.

Gates:
  - curator.enabled == True
  - not paused
  - last_run_at present AND older than interval_hours

First-run behavior: when there is no ``last_run_at`` (fresh install, or
install that predates the curator), we DO NOT run immediately. The
curator is designed to run after at least ``interval_hours`` (7 days by
default) of skill activity, not on the first background tick after
``hermes update``. On first observation we seed ``last_run_at`` to "now"
and defer the first real pass by one full interval. Users who want to
run it sooner can always invoke ``hermes curator run`` (with or without
``--dry-run``) explicitly — that path bypasses this gate.

The idle check (min_idle_hours) is applied at the call site where we know
whether an agent is actively running — here we only enforce the static
gates.

#### def `apply_automatic_transitions(now: Optional[datetime] = None) -> Dict[str, int]`

Walk every curator-managed skill and move active/stale/archived based on
the latest real activity timestamp. Pinned skills are never touched.

Built-ins (eligible only when ``curator.prune_builtins`` is on) are seeded
with a baseline record the first time they're seen so their inactivity
clock starts NOW rather than at epoch — a long-unused built-in is therefore
archived only after a fresh ``archive_after_days`` of non-use, not on the
first pass after the flag flips on.

Returns a counter dict describing what changed.

#### def `run_curator_review(on_summary: Optional[Callable[[str], None]] = None, synchronous: bool = False, dry_run: bool = False, consolidate: Optional[bool] = None) -> Dict[str, Any]`

Execute a single curator review pass.

Steps:
  1. Apply automatic state transitions (pure, no LLM).
  2. If consolidation is enabled AND there are agent-created skills, spawn
     a forked AIAgent that runs the LLM review prompt against the current
     candidate list.
  3. Update .curator_state with last_run_at and a one-line summary.
  4. Invoke *on_summary* with a user-visible description.

If *synchronous* is True, the LLM review runs in the calling thread; the
default is to spawn a daemon thread so the caller returns immediately.

*consolidate* gates the LLM umbrella-building pass. ``None`` (the default)
reads ``curator.consolidate`` from config (OFF by default). Passing
``True``/``False`` overrides the config for this invocation — used by the
``hermes curator run --consolidate`` flag. When consolidation is off, only
the deterministic inactivity prune runs and the forked aux-model review is
skipped entirely (no aux-model cost).

If *dry_run* is True, the automatic stale/archive transitions are SKIPPED
and the LLM review pass is instructed to produce a report only — no
skill_manage mutations, no terminal archive moves. The REPORT.md still
gets written and ``state.last_report_path`` still records it so users
can read what the curator WOULD have done. A dry-run also honors
*consolidate*: when consolidation is off, the preview only reports the
deterministic prune candidates.

#### def `maybe_run_curator(idle_for_seconds: Optional[float] = None, on_summary: Optional[Callable[[str], None]] = None) -> Optional[Dict[str, Any]]`

Best-effort: run a curator pass if all gates pass. Returns the result
dict if a pass was started, else None. Never raises.


## agent.curator_backup

### 模块文档

Curator snapshot + rollback.

A pre-run snapshot of ``~/.hermes/skills/`` (excluding ``.curator_backups/``
itself) is taken before any mutating curator pass. Snapshots are tar.gz
files under ``~/.hermes/skills/.curator_backups/<utc-iso>/`` with a
companion ``manifest.json`` describing the snapshot (reason, time, size,
counted skill files). Rollback picks a snapshot, moves the current
``skills/`` tree aside into another snapshot so even the rollback itself
is undoable, then extracts the chosen snapshot into place.

The snapshot does NOT include:
  - ``.curator_backups/`` (would recurse)
  - ``.hub/`` (hub-installed skills — managed by the hub, not us)

It DOES include:
  - all SKILL.md files + their directories (``scripts/``, ``references/``,
    ``templates/``, ``assets/``)
  - ``.usage.json`` (usage telemetry — needed to rehydrate state cleanly)
  - ``.archive/`` (so rollback restores previously-archived skills too)
  - ``.curator_state`` (so rolling back also restores the last-run-at
    pointer — otherwise the curator would immediately re-fire on the next
    tick)
  - ``.bundled_manifest`` (so protection markers stay consistent)
  - ``.curator_suppressed`` (so rollback restores the set of pruned built-ins
    the re-seeder must leave archived)

Alongside the skills tarball, each snapshot also captures a copy of
``~/.hermes/cron/jobs.json`` as ``cron-jobs.json`` when it exists. Cron
jobs reference skills by name in their ``skills``/``skill`` fields; the
curator's consolidation pass rewrites those in place via
``cron.jobs.rewrite_skill_refs()``. Without capturing the pre-run state,
rolling back the skills tree would leave cron jobs pointing at the
umbrella skills even though the narrow skills they were originally
configured with have been restored. We store the whole jobs.json for
fidelity but rollback only touches the ``skills``/``skill`` fields — the
rest (schedule, next_run_at, enabled, prompt, etc.) is live state and
we leave it alone.

### 顶层函数

#### def `is_enabled() -> bool`

Default ON — the whole point of the backup is safety by default.

#### def `get_keep() -> int`

#### def `snapshot_skills(reason: str = 'manual', protect_ids: Optional[Set[str]] = None) -> Optional[Path]`

Create a tar.gz snapshot of ``~/.hermes/skills/`` and prune old ones.

Returns the snapshot directory path, or ``None`` if the snapshot was
skipped (backup disabled, skills dir missing, or an IO error occurred —
in which case we log at debug and return None so the curator never
aborts a pass because of a backup failure).

``protect_ids`` is forwarded to the prune step so callers can guarantee
specific snapshot ids survive even when they fall outside the keep
window (rollback passes the id it is about to restore from).

#### def `list_backups() -> List[Dict[str, Any]]`

Return all restorable snapshots, newest first. Only entries with a
real ``skills.tar.gz`` tarball are listed — transient
``.rollback-staging-*`` directories created mid-rollback are
implementation detail and not shown.

#### def `rollback(backup_id: Optional[str] = None) -> Tuple[bool, str, Optional[Path]]`

Restore ``~/.hermes/skills/`` from a snapshot.

Strategy:
  1. Resolve the target snapshot (explicit id or newest regular).
  2. Take a safety snapshot of the CURRENT skills tree under
     ``.curator_backups/pre-rollback-<ts>/`` so the rollback itself is
     undoable.
  3. Move all current top-level entries (except ``.curator_backups``
     and ``.hub``) into a tempdir.
  4. Extract the chosen snapshot into ``~/.hermes/skills/``.
  5. On failure during 4, move the tempdir contents back (best-effort)
     and return failure.

Returns ``(ok, message, snapshot_path)``.

**异常**: `tarfile.TarError`

#### def `format_size(n: int) -> str`

#### def `summarize_backups() -> str`


## agent.display

### 模块文档

CLI presentation -- spinner, kawaii faces, tool preview formatting.

Pure display functions and classes with no AIAgent dependency.
Used by AIAgent._execute_tool_calls for CLI feedback.

### class LocalEditSnapshot

> 继承: `object` ｜ 方法数: 0（公开 0）

Pre-tool filesystem snapshot used to render diffs locally after writes.


### class KawaiiSpinner

> 继承: `object` ｜ 方法数: 14（公开 7）

Animated spinner with kawaii faces for CLI feedback during tool execution.

#### classmethod `get_waiting_faces(cls) -> list`

Return waiting faces from the active skin, falling back to KAWAII_WAITING.

#### classmethod `get_thinking_faces(cls) -> list`

Return thinking faces from the active skin, falling back to KAWAII_THINKING.

#### classmethod `get_thinking_verbs(cls) -> list`

Return thinking verbs from the active skin, falling back to THINKING_VERBS.

#### def `__init__(message: str = '', spinner_type: str = 'dots', print_fn = None)`

#### def `start(self)`

#### def `update_text(self, new_message: str)`

#### def `print_above(self, text: str)`

Print a line above the spinner without disrupting animation.

Clears the current spinner line, prints the text, and lets the
next animation tick redraw the spinner on the line below.
Thread-safe: uses the captured stdout reference (self._out).
Works inside redirect_stdout(devnull) because _write bypasses
sys.stdout and writes to the stdout captured at spinner creation.

#### def `stop(self, final_message: str = None)`


### 顶层函数

#### def `set_tool_preview_max_len(n: int) -> None`

Set the global max length for tool call previews. 0 = no limit.

#### def `get_tool_preview_max_len() -> int`

Return the configured max preview length (0 = unlimited).

#### def `get_skin_tool_prefix() -> str`

Get tool output prefix character from active skin.

#### def `get_tool_emoji(tool_name: str, default: str = '⚡') -> str`

Get the display emoji for a tool.

Resolution order:
1. Active skin's ``tool_emojis`` overrides (if a skin is loaded)
2. Tool registry's per-tool ``emoji`` field
3. *default* fallback

#### def `summarize_shell_command(command: str) -> str`

Compact shell wrapper/plumbing for display while preserving raw command elsewhere.

#### def `redact_browser_typed_text_for_display(value: Any, typed_text: Any) -> Any`

Apply secret redaction to browser_type text in display-facing payloads.

Backends sometimes echo the attempted input in error strings or fallback
metadata.  When the raw typed value contains a recognizable secret (API
key, token, JWT, etc.) the redacted form differs from the raw value, so we
replace every occurrence of the raw value with its redacted form before a
browser_type result reaches logs, callbacks, the model, or chat history.

Normal typed text (search queries, addresses, form fields) matches no
secret pattern, so it passes through unchanged and stays readable.

Redaction is forced here regardless of the global ``security.redact_secrets``
preference: a typed credential leaking into chat history is a security
boundary, not mere log hygiene.

#### def `redact_tool_args_for_display(tool_name: str, args: dict | None) -> dict | None`

Return a copy of tool args safe for logs/progress UI.

For ``browser_type`` the ``text`` argument is run through the same
secret-pattern redactor used for logs.  Recognizable credentials (API
keys, tokens) are masked before the value reaches tool progress
notifications; normal typed text is left intact for debuggability.

#### def `build_tool_preview(tool_name: str, args: dict, max_len: int | None = None) -> str | None`

Build a short preview of a tool call's primary argument for display.

*max_len* controls truncation.  ``None`` (default) defers to the global
``_tool_preview_max_len`` set via config; ``0`` means unlimited.

#### def `set_friendly_tool_labels(enabled: bool) -> None`

Toggle friendly human-phrased tool labels (display.friendly_tool_labels).

#### def `get_friendly_tool_labels() -> bool`

Return whether friendly tool labels are enabled.

#### def `get_tool_verb(tool_name: str) -> str | None`

Return the friendly verb for a built-in tool, or None.

Returns None when friendly labels are disabled or the tool has no curated
verb (custom/plugin/MCP tools).  Callers that already hold a computed
argument preview can compose ``f"{verb} {preview}"`` themselves; use
:func:`tool_verb_connector` to pick the right joiner.

#### def `tool_verb_connector(tool_name: str) -> str`

Return the connector between a verb and its preview (" for " or " ").

#### def `verb_drops_preview(tool_name: str) -> bool`

Whether the verb should render alone, without the argument preview.

#### def `build_status_phrase(tool_name: str, args: dict | None, max_len: int = 49) -> str | None`

Build a short present-tense status phrase for platform status surfaces.

Used by text-rendering "typing" indicators (Slack's
``assistant.threads.setStatus`` line) to show what the agent is doing
right now: ``is running scripts/run_tests.sh…`` instead of a static
``is thinking...``.  The phrase is phrased to follow the bot's display
name ("Hermes is running …"), so it starts lowercase with "is".

Pass ``args=None`` for a verb-only phrase (``is running…``) — used when
``display.live_status`` is ``verb`` to keep argument previews out of
shared channels.

Returns None for the ``_thinking`` pseudo-tool and when friendly labels
are disabled (callers fall back to their static default).  ``max_len``
caps the total phrase length; Slack truncates its status line around 50
characters, so the default stays just under that.

#### def `build_tool_label(tool_name: str, args: dict, max_len: int | None = None) -> str | None`

Build a human-phrased status label for a tool call.

For built-in tools with a known verb (``web_search`` -> "Searching the
web for ..."), returns the verb optionally followed by the argument
preview.  For everything else (custom/plugin/MCP tools, or when friendly
labels are disabled) returns the raw preview, so callers can use this as a
drop-in replacement for :func:`build_tool_preview`.

#### def `capture_local_edit_snapshot(tool_name: str, function_args: dict | None) -> LocalEditSnapshot | None`

Capture before-state for local write previews.

#### def `extract_edit_diff(tool_name: str, result: str | None, function_args: dict | None = None, snapshot: LocalEditSnapshot | None = None) -> str | None`

Extract a unified diff from a file-edit tool result.

#### def `render_edit_diff_with_delta(tool_name: str, result: str | None, function_args: dict | None = None, snapshot: LocalEditSnapshot | None = None, print_fn = None) -> bool`

Render an edit diff inline without taking over the terminal UI.

#### def `get_cute_tool_message(tool_name: str, args: dict, duration: float, result: str | None = None) -> str`

Render a completion label without letting cosmetic failures escape.


## agent.error_classifier

### 模块文档

API error classification for smart failover and recovery.

Provides a structured taxonomy of API errors and a priority-ordered
classification pipeline that determines the correct recovery action
(retry, rotate credential, fallback to another provider, compress
context, or abort).

Replaces scattered inline string-matching with a centralized classifier
that the main retry loop in run_agent.py consults for every API failure.

### class FailoverReason

> 继承: `enum.Enum` ｜ 方法数: 0（公开 0）

Why an API call failed — determines recovery strategy.


### class ClassifiedError

> 继承: `object` ｜ 方法数: 1（公开 1）

Structured classification of an API error with recovery hints.

#### property `is_auth(self) -> bool`


### 顶层函数

#### def `classify_api_error(error: Exception, provider: str = '', model: str = '', approx_tokens: int = 0, context_length: int = 200000, num_messages: int = 0) -> ClassifiedError`

Classify an API error into a structured recovery recommendation.

Priority-ordered pipeline:
  1. Special-case provider-specific patterns (thinking sigs, tier gates)
  2. HTTP status code + message-aware refinement
  3. Error code classification (from body)
  4. Message pattern matching (billing vs rate_limit vs context vs auth)
  5. SSL/TLS transient alert patterns → retry as timeout
  6. Server disconnect + large session → context overflow
  7. Transport error heuristics
  8. Fallback: unknown (retryable with backoff)

Args:
    error: The exception from the API call.
    provider: Current provider name (e.g. "openrouter", "anthropic").
    model: Current model slug.
    approx_tokens: Approximate token count of the current context.
    context_length: Maximum context length for the current model.

Returns:
    ClassifiedError with reason and recovery action hints.


## agent.errors

### class SSLConfigurationError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Raised when SSL/TLS certificate bundle configuration fails.


### class EmptyStreamError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when a provider closes a stream without yielding a response.


### class MoAPresetNotFoundError

> 继承: `ValueError` ｜ 方法数: 0（公开 0）

Raised when a persisted MoA preset no longer exists in config.


## agent.file_safety

### 模块文档

Shared file safety rules used by both tools and ACP shims.

### 顶层函数

#### def `build_write_denied_paths(home: str) -> set[str]`

Return exact sensitive paths that must never be written.

#### def `build_write_denied_prefixes(home: str) -> list[str]`

Return sensitive directory prefixes that must never be written.

#### def `get_safe_write_roots() -> set[str]`

Return resolved HERMES_WRITE_SAFE_ROOT paths. Supports multiple directories
separated by ``os.pathsep`` (``:`` on Unix, ``;`` on Windows).
E.g., ``/opt/data:/var/www/html`` on Unix, ``C:\data;D:\www`` on Windows.

#### def `is_write_denied(path: str) -> bool`

Return True if path is blocked by the write denylist or safe root.

#### def `get_write_denied_error(path: str, verb: str = 'Write') -> Optional[str]`

Return a user/model-facing error when writes to ``path`` are blocked.

#### def `get_read_block_error(path: str) -> Optional[str]`

Return an error message when a read targets a denied Hermes path.

Three categories are blocked:

  * Internal Hermes cache files under ``HERMES_HOME/skills/.hub`` —
    readable metadata that an attacker could use as a prompt-injection
    carrier.
  * Credential / secret stores under HERMES_HOME and the global Hermes
    root: ``auth.json``, ``auth.lock``, ``.anthropic_oauth.json``,
    ``.env``, ``webhook_subscriptions.json``, ``auth/google_oauth.json``,
    and anything under ``mcp-tokens/``. These hold plaintext provider keys,
    OAuth tokens, and HMAC secrets that the agent never needs to read
    directly — provider tools / gateway adapters consume them through
    internal channels.
  * Project-local environment files anywhere on disk: ``.env``,
    ``.env.local``, ``.env.development``, ``.env.production``,
    ``.env.test``, ``.env.staging``, ``.envrc``. These routinely hold
    API keys, database passwords, and other credentials for the user's
    own projects. The agent helping debug a project shouldn't normally
    need to read these — ``.env.example`` is the documented-shape
    substitute.

**This is NOT a security boundary.** The terminal tool runs as the
same OS user with shell access; the agent can still ``cat auth.json``
or ``cat ~/.hermes/.env`` and exfiltrate the file. The read-deny exists
as defense-in-depth that:

  * Returns a clear error to models that respect tool denials, which
    empirically prompts most modern models to stop rather than reach
    for the shell.
  * Surfaces a visible audit trail when something tries to read
    credentials — easier to spot in logs than a generic ``cat``.

Treat any user-visible framing around this as "may help" rather than
"stops attackers." A determined model or malicious instruction can
always shell out.

Callers that resolve relative paths against a non-process cwd
(e.g. ``TERMINAL_CWD`` in ``tools/file_tools.py``) MUST pre-resolve
and pass the absolute path string.  This function's own ``resolve()``
is anchored at the Python process cwd, so a relative input like
``"auth.json"`` would otherwise miss the denylist when the task's
terminal cwd differs from the process cwd.

#### def `raise_if_read_blocked(path: str) -> None`

Raise ``ValueError`` if ``path`` is a denied Hermes read (see
:func:`get_read_block_error`), else return.

Shared chokepoint for provider input-loading sites that read a local
file the model/tool supplied (e.g. image-gen ``image_url`` /
``reference_image_urls`` paths). Centralizes the guard so every provider
enforces the same read boundary with identical semantics instead of each
open-coding the try/except block (#57698).

Best-effort by design: if ``agent.file_safety`` machinery is somehow
unavailable at the call site the guard no-ops rather than breaking local
image loading — consistent with the defense-in-depth (not security
boundary) framing of the denylist itself. The blocking ``ValueError`` from
a real hit still propagates; only unexpected internal errors are swallowed.

**异常**: `ValueError`

#### def `classify_cross_profile_target(path: str) -> Optional[dict]`

Classify a write target as cross-profile if it lands in another
profile's scoped area (skills/plugins/cron/memories).

Returns ``None`` when the target is outside Hermes scope, or is inside
the ACTIVE profile, or doesn't hit a profile-scoped area. Otherwise
returns a dict with:

  * ``active_profile``: name of the profile the agent is running as
  * ``target_profile``: name of the profile the path belongs to
  * ``area``: which scoped area (``"skills"``, ``"plugins"``, etc.)
  * ``target_path``: the resolved path string

The caller decides what to do with the result — surface a warning to
the model, prompt the user, or (with explicit consent /
``cross_profile=True``) proceed anyway.

#### def `get_cross_profile_warning(path: str) -> Optional[str]`

Return a model-facing warning string when ``path`` is cross-profile.

Returns ``None`` when the write is in-scope (same profile) or outside
Hermes entirely. Caller is expected to surface the warning to the
agent as a tool-result error, NOT to silently allow the write — the
agent must either get explicit user direction to proceed, or pass
``cross_profile=True`` to its write tool.

This is defense-in-depth: the terminal tool runs as the same OS user
and can write any of these paths without going through this guard.
Treat the guard as a confusion-reducer, not a security boundary.

#### def `classify_sandbox_mirror_target(path: str) -> Optional[dict]`

Classify a write target as a sandbox-mirror of authoritative Hermes state.

Returns ``None`` when the path does not match the sandbox-mirror shape.
Otherwise returns a dict with:

  * ``target_path``: the resolved path string
  * ``mirror_root``: the ``…/sandboxes/<backend>/<task>/home/.hermes``
    prefix (so callers can show users which sandbox owns the mirror)
  * ``inner_path``: the portion under the mirror's ``.hermes`` (what the
    agent likely meant to address on the host)

Detection is path-shape-only — does not require any Hermes resolver to
succeed, so it works correctly even when called from contexts where
HERMES_HOME resolution would be ambiguous.

#### def `get_sandbox_mirror_warning(path: str) -> Optional[str]`

Return a model-facing warning when ``path`` lands in a sandbox mirror.

Returns ``None`` when the path is not a sandbox-mirror target. Caller
is expected to surface the warning to the agent as a tool-result
error. The bypass kwarg (``cross_profile=True``) is shared with the
cross-profile guard: both are soft "I know what I'm doing" overrides
a user can authorise.

Defense-in-depth, NOT a security boundary: the terminal tool runs as
the same OS user and can write the mirror path directly. The guard
exists to surface the misclassification before the silent-success +
divergent-copy footgun in #32049 fires.

#### def `classify_container_mirror_target(path: str, mirror_prefix: str | None = None) -> Optional[dict]`

Classify a write target as a container-side sandbox mirror.

``mirror_prefix`` must be supplied by the caller after it has established
that file tools are executing in a container whose home is a sandbox
mirror. Returns ``None`` when no such context is active or the path is not
under the mirror prefix. Otherwise returns:

  * ``target_path``: resolved path string
  * ``mirror_root``: the declared container mirror prefix
  * ``inner_path``: portion under the mirror root (what the agent
    likely meant to address in the host HERMES_HOME)

#### def `get_container_mirror_warning(path: str, mirror_prefix: str | None = None) -> Optional[str]`

Return a model-facing warning when *path* lands in the container's
sandbox mirror of authoritative Hermes state.

The caller supplies ``mirror_prefix`` only when the current file-tool
backend is known to execute inside a Docker sandbox. Same contract as
``get_cross_profile_warning``: soft guard, returns ``None`` for
non-mirror paths, caller surfaces as a tool-result error. Bypass via
``cross_profile=True`` after explicit user direction.


## agent.gemini_native_adapter

### 模块文档

OpenAI-compatible facade over Google AI Studio's native Gemini API.

Hermes keeps ``api_mode='chat_completions'`` for the ``gemini`` provider so the
main agent loop can keep using its existing OpenAI-shaped message flow.
This adapter is the transport shim that converts those OpenAI-style
``messages[]`` / ``tools[]`` requests into Gemini's native
``models/{model}:generateContent`` schema and converts the responses back.

Why this exists
---------------
Google's OpenAI-compatible endpoint has been brittle for Hermes's multi-turn
agent/tool loop (auth churn, tool-call replay quirks, thought-signature
requirements).  The native Gemini API is the canonical path and avoids the
OpenAI-compat layer entirely.

### class GeminiAPIError

> 继承: `Exception` ｜ 方法数: 1（公开 0）

Error shape compatible with Hermes retry/error classification.

#### def `__init__(message: str, code: str = 'gemini_api_error', status_code: Optional[int] = None, response: Optional[httpx.Response] = None, retry_after: Optional[float] = None, details: Optional[Dict[str, Any]] = None) -> None`


### class GeminiNativeClient

> 继承: `object` ｜ 方法数: 8（公开 1）

Minimal OpenAI-SDK-compatible facade over Gemini's native REST API.

#### def `__init__(api_key: str, base_url: Optional[str] = None, default_headers: Optional[Dict[str, str]] = None, timeout: Any = None, http_client: Optional[httpx.Client] = None, **_: Any) -> None`

**异常**: `RuntimeError`

#### def `close(self) -> None`


### class AsyncGeminiNativeClient

> 继承: `object` ｜ 方法数: 3（公开 1）

Async wrapper used by auxiliary_client for native Gemini calls.

#### def `__init__(sync_client: GeminiNativeClient)`

#### async def `close(self) -> None`


### 顶层函数

#### def `bare_gemini_model_id(model: str) -> str`

Strip Gemini's own provider prefix from an aggregator-style model id.

#### def `is_native_gemini_base_url(base_url: str) -> bool`

Return True when the endpoint speaks Gemini's native REST API.

#### def `probe_gemini_tier(api_key: str, base_url: str = DEFAULT_GEMINI_BASE_URL, model: str = 'gemini-2.5-flash', timeout: float = 10.0) -> str`

Probe a Google AI Studio API key and return its tier.

Returns one of:

- ``"free"``    -- key is on the free tier (unusable with Hermes)
- ``"paid"``    -- key is on a paid tier
- ``"unknown"`` -- probe failed; callers should proceed without blocking.

#### def `is_free_tier_quota_error(error_message: str) -> bool`

Return True when a Gemini 429 message indicates free-tier exhaustion.

#### def `build_gemini_request(messages: List[Dict[str, Any]], tools: Any = None, tool_choice: Any = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, top_p: Optional[float] = None, stop: Any = None, thinking_config: Any = None) -> Dict[str, Any]`

#### def `translate_gemini_response(resp: Dict[str, Any], model: str) -> SimpleNamespace`

#### def `translate_stream_event(event: Dict[str, Any], model: str, tool_call_indices: Dict[str, Dict[str, Any]]) -> List[_GeminiStreamChunk]`

#### def `gemini_http_error(response: httpx.Response, body_text: Optional[str] = None) -> GeminiAPIError`


## agent.gemini_schema

### 模块文档

Helpers for translating OpenAI-style tool schemas to Gemini's schema subset.

### 顶层函数

#### def `sanitize_gemini_schema(schema: Any) -> Dict[str, Any]`

Return a Gemini-compatible copy of a tool parameter schema.

Hermes tool schemas are OpenAI-flavored JSON Schema and may contain keys
such as ``$schema`` or ``additionalProperties`` that Google's Gemini
``Schema`` object rejects.  This helper preserves the documented Gemini
subset and recursively sanitizes nested ``properties`` / ``items`` /
``anyOf`` definitions.

#### def `sanitize_gemini_tool_parameters(parameters: Any) -> Dict[str, Any]`

Normalize tool parameters to a valid Gemini object schema.


## agent.i18n

### 模块文档

Lightweight internationalization (i18n) for Hermes static user-facing messages.

Scope (thin slice, by design): only the highest-impact static strings shown
to the user by Hermes itself -- approval prompts, a handful of gateway slash
command replies, restart-drain notices.  Agent-generated output, log lines,
error tracebacks, tool outputs, and slash-command descriptions all stay in
English.

Catalog files live under ``locales/<lang>.yaml`` at the repo root.  Each
catalog is a flat dict keyed by dotted paths (e.g. ``approval.choose`` or
``gateway.approval_expired``).  Missing keys fall back to English; if English
is missing too, the key path itself is returned so a broken catalog never
crashes the agent.

Usage::

    from agent.i18n import t
    print(t("approval.choose_long"))                       # current lang
    print(t("gateway.draining", count=3))                  # {count} formatted
    print(t("approval.choose_long", lang="zh"))            # explicit override

Language resolution order:
    1. Explicit ``lang=`` argument passed to :func:`t`
    2. ``HERMES_LANGUAGE`` environment variable (for tests / quick override)
    3. ``display.language`` from config.yaml
    4. ``"en"`` (baseline)

Supported languages: en, zh, ja, de, es, fr, tr, uk.  Unknown values fall back to en.

### 顶层函数

#### def `reset_language_cache() -> None`

Invalidate cached language resolution and catalogs.

Call after :func:`hermes_cli.config.save_config` if a running process
needs to pick up a changed ``display.language`` without restart.

#### def `get_language() -> str`

Resolve the active language using env > config > default order.

#### def `t(key: str, lang: str | None = None, **format_kwargs: Any) -> str`

Translate a dotted key to the active language.

Parameters
----------
key
    Dotted path into the catalog, e.g. ``"approval.choose_long"``.
lang
    Explicit language override.  Takes precedence over env + config.
**format_kwargs
    ``str.format`` substitution arguments (``t("gateway.drain", count=3)``
    expects a catalog entry with a ``{count}`` placeholder).

Returns
-------
The translated string, or the English fallback if the key is missing in
the target language, or the bare key if English is also missing.


## agent.image_gen_provider

### 模块文档

Image Generation Provider ABC
=============================

Defines the pluggable-backend interface for image generation. Providers register
instances via ``PluginContext.register_image_gen_provider()``; the active one
(selected via ``image_gen.provider`` in ``config.yaml``) services every
``image_generate`` tool call.

Providers live in ``<repo>/plugins/image_gen/<name>/`` (built-in, auto-loaded
as ``kind: backend``) or ``~/.hermes/plugins/image_gen/<name>/`` (user, opt-in
via ``plugins.enabled``).

Unified surface
---------------
One tool — ``image_generate`` — covers **text-to-image** and
**image-to-image / image editing**. The router is the presence of
``image_url`` (and/or ``reference_image_urls``): if any source image is
provided, the provider routes to its image-to-image / edit endpoint; if
omitted, the provider routes to text-to-image. Users pick one **model**
(e.g. nano-banana-pro, gpt-image-2, grok-imagine-image); the provider
handles which underlying endpoint to hit. This mirrors the ``video_gen``
provider design (``agent/video_gen_provider.py``) so the two surfaces
stay learnable together.

Response shape
--------------
All providers return a dict that :func:`success_response` / :func:`error_response`
produce. The tool wrapper JSON-serializes it. Keys:

    success        bool
    image          str | None       URL or absolute file path
    model          str              provider-specific model identifier
    prompt         str              echoed prompt
    aspect_ratio   str              "landscape" | "square" | "portrait"
    modality       str              "text" | "image" (which mode was used)
    provider       str              provider name (for diagnostics)
    error          str              only when success=False
    error_type     str              only when success=False

### class ImageGenProvider

> 继承: `abc.ABC` ｜ 方法数: 8（公开 8）

Abstract base class for an image generation backend.

Subclasses must implement :meth:`generate`. Everything else has sane
defaults — override only what your provider needs.

#### property `name(self) -> str`

Stable short identifier used in ``image_gen.provider`` config.

Lowercase, no spaces. Examples: ``fal``, ``openai``, ``replicate``.

#### property `display_name(self) -> str`

Human-readable label shown in ``hermes tools``. Defaults to ``name.title()``.

#### def `is_available(self) -> bool`

Return True when this provider can service calls.

Typically checks for a required API key. Default: True
(providers with no external dependencies are always available).

#### def `list_models(self) -> List[Dict[str, Any]]`

Return catalog entries for ``hermes tools`` model picker.

Each entry::

    {
        "id": "gpt-image-1.5",               # required
        "display": "GPT Image 1.5",          # optional; defaults to id
        "speed": "~10s",                     # optional
        "strengths": "...",                  # optional
        "price": "$...",                     # optional
    }

Default: empty list (provider has no user-selectable models).

#### def `get_setup_schema(self) -> Dict[str, Any]`

Return provider metadata for the ``hermes tools`` picker.

Used by ``tools_config.py`` to inject this provider as a row in
the Image Generation provider list. Shape::

    {
        "name": "OpenAI",                     # picker label
        "badge": "paid",                      # optional short tag
        "tag": "One-line description...",     # optional subtitle
        "env_vars": [                         # keys to prompt for
            {"key": "OPENAI_API_KEY",
             "prompt": "OpenAI API key",
             "url": "https://platform.openai.com/api-keys"},
        ],
    }

Default: minimal entry derived from ``display_name``. Override to
expose API key prompts and custom badges.

#### def `default_model(self) -> Optional[str]`

Return the default model id, or None if not applicable.

#### def `capabilities(self) -> Dict[str, Any]`

Return what this provider supports.

Returned dict (all keys optional)::

    {
        "modalities": ["text", "image"],   # which inputs the backend accepts
        "max_reference_images": 9,          # cap for reference_image_urls
    }

``modalities`` declares whether the active backend/model supports
text-to-image (``"text"``), image-to-image / editing (``"image"``),
or both. The tool layer surfaces this in the dynamic schema so the
model knows when ``image_url`` is honored. Used by ``hermes tools``
for the picker too. Default: text-only (backward compatible — a
provider that doesn't override this advertises text-to-image only).

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]`

Generate an image from a text prompt, or edit/transform a source image.

Routing: if ``image_url`` (or any ``reference_image_urls``) is
provided, the provider should route to its image-to-image / edit
endpoint; otherwise text-to-image. ``image_url`` is the primary
source image to edit; ``reference_image_urls`` are additional
style/composition references (provider clamps to its declared
``max_reference_images``).

Implementations should return the dict from :func:`success_response`
or :func:`error_response`. ``kwargs`` may contain forward-compat
parameters future versions of the schema will expose —
implementations MUST ignore unknown keys (no TypeError).


### 顶层函数

#### def `resolve_aspect_ratio(value: Optional[str]) -> str`

Clamp an aspect_ratio value to the valid set, defaulting to landscape.

Invalid values are coerced rather than rejected so the tool surface is
forgiving of agent mistakes.

#### def `normalize_reference_images(value: Any) -> Optional[List[str]]`

Coerce a reference-image argument into a clean list of URL/path strings.

Accepts a single string or a list; strips blanks and whitespace. Returns
``None`` when nothing usable remains so providers can treat "no refs" as a
single sentinel.

#### def `save_b64_image(b64_data: str, prefix: str = 'image', extension: str = 'png') -> Path`

Decode base64 image data and write it under ``$HERMES_HOME/cache/images/``.

Returns the absolute :class:`Path` to the saved file.

Filename format: ``<prefix>_<YYYYMMDD_HHMMSS>_<short-uuid>.<ext>``.

#### def `save_url_image(url: str, prefix: str = 'image', timeout: float = 60.0, max_bytes: int = 25 * 1024 * 1024) -> Path`

Download an image URL and write it under ``$HERMES_HOME/cache/images/``.

Used by providers (xAI, fallback OpenAI) whose API returns an *ephemeral*
URL instead of inline base64 — those URLs frequently expire before a
downstream consumer (Telegram ``send_photo``, browser fetch) can resolve
them, so we materialise the bytes locally at tool-completion time.
Mirrors :func:`save_b64_image`'s shape so providers can swap in one line.

Returns the absolute :class:`Path` to the saved file.  Raises on any
network / HTTP / oversize / non-image-content-type error so callers can
fall back to returning the bare URL with a clear error message.

**异常**: `ValueError`

#### def `success_response(image: str, model: str, prompt: str, aspect_ratio: str, provider: str, modality: str = 'text', extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

Build a uniform success response dict.

``image`` may be an HTTP URL or an absolute filesystem path (for b64
providers like OpenAI). ``modality`` is ``"text"`` (text-to-image) or
``"image"`` (image-to-image / editing) — indicates which endpoint was
actually hit, useful for diagnostics. Callers that need to pass through
additional backend-specific fields can supply ``extra``.

#### def `error_response(error: str, error_type: str = 'provider_error', provider: str = '', model: str = '', prompt: str = '', aspect_ratio: str = DEFAULT_ASPECT_RATIO) -> Dict[str, Any]`

Build a uniform error response dict.


## agent.image_gen_registry

### 模块文档

Image Generation Provider Registry
==================================

Central map of registered providers. Populated by plugins at import-time via
``PluginContext.register_image_gen_provider()``; consumed by the
``image_generate`` tool to dispatch each call to the active backend.

Active selection
----------------
The active provider is chosen by ``image_gen.provider`` in ``config.yaml``.
If unset, :func:`get_active_provider` applies fallback logic:

1. If exactly one provider is registered, use it.
2. Otherwise if a provider named ``fal`` is registered, use it (legacy
   default — matches pre-plugin behavior).
3. Otherwise return ``None`` (the tool surfaces a helpful error pointing
   the user at ``hermes tools``).

### 顶层函数

#### def `register_provider(provider: ImageGenProvider) -> None`

Register an image generation provider.

Re-registration (same ``name``) overwrites the previous entry and logs
a debug message — this makes hot-reload scenarios (tests, dev loops)
behave predictably.

**异常**: `TypeError`, `ValueError`

#### def `list_providers() -> List[ImageGenProvider]`

Return all registered providers, sorted by name.

#### def `get_provider(name: str) -> Optional[ImageGenProvider]`

Return the provider registered under *name*, or None.

#### def `get_active_provider() -> Optional[ImageGenProvider]`

Resolve the currently-active provider.

Reads ``image_gen.provider`` from config.yaml; falls back per the
module docstring.

**Availability semantics** (mirrors :mod:`agent.web_search_registry`):

- When ``image_gen.provider`` is explicitly set, the configured
  provider is returned even if :meth:`ImageGenProvider.is_available`
  reports False — the dispatcher surfaces a precise "X_API_KEY is not
  set" error rather than silently switching backends.
- When ``image_gen.provider`` is unset, the fallback path (single-
  provider shortcut and the FAL legacy preference) is filtered by
  ``is_available()`` so we don't pick a provider the user has no
  credentials for.


## agent.image_routing

### 模块文档

Routing helpers for inbound user-attached images.

Two modes:

  native  — attach images as OpenAI-style ``image_url`` content parts on the
            user turn. Provider adapters (Anthropic, Gemini, Bedrock, Codex,
            OpenAI chat.completions) already translate these into their
            vendor-specific multimodal formats.

  text    — run ``vision_analyze`` on each image up-front and prepend the
            description to the user's text. The model never sees the pixels;
            it only sees a lossy text summary. This is the pre-existing
            behaviour and still the right choice for non-vision models.

The decision is made once per message turn by :func:`decide_image_input_mode`.
It reads ``agent.image_input_mode`` from config.yaml (``auto`` | ``native``
| ``text``, default ``auto``) and the active model's capability metadata.

In ``auto`` mode:
  - If the active model reports ``supports_vision=True`` (via config
    override or models.dev metadata), we attach natively — vision-capable
    main models should always see the original pixels, even when an
    auxiliary vision backend is configured. That auxiliary backend then
    acts as a *fallback* for sessions whose main model can't take images.
  - Otherwise, if the user has explicitly configured ``auxiliary.vision``
    (provider/model/base_url not ``auto``/empty), we route through the
    text pipeline so the auxiliary vision backend can describe the image
    for the text-only main model.
  - Otherwise (non-vision model, no explicit override), we fall back to
    text via the default vision_analyze flow.

This keeps ``vision_analyze`` surfaced as a tool in every session — skills
and agent flows that chain it (browser screenshots, deeper inspection of
URL-referenced images, style-gating loops) keep working. The routing only
affects *how user-attached images on the current turn* are presented to the
main model.

### 顶层函数

#### def `extract_image_refs(text: str) -> Tuple[List[str], List[str]]`

Scan free-form text for image references the model should see.

Returns ``(local_paths, urls)``:

  * ``local_paths`` — absolute (``/``) or home-relative (``~/``) paths
    whose suffix is an image extension AND whose expanded form exists
    on disk as a file. Order-preserving, deduplicated.
  * ``urls`` — ``http(s)://…`` URLs whose path ends in an image
    extension (a ``?query`` is allowed after the extension).
    Order-preserving, deduplicated.

Matches inside fenced code blocks (``` ``` ```) and inline backticks
(`` `…` ``) are skipped so that snippets pasted into a task body for
reference aren't mistaken for live attachments. This mirrors the
behaviour of ``gateway.platforms.base.BaseAdapter.extract_local_files``.

Local paths are validated against the filesystem; URLs are not
(the provider fetches them at request time).

#### def `decide_image_input_mode(provider: str, model: str, cfg: Optional[Dict[str, Any]]) -> str`

Return ``"native"`` or ``"text"`` for the given turn.

Args:
  provider: active inference provider ID (e.g. ``"anthropic"``, ``"openrouter"``).
  model:    active model slug as it would be sent to the provider.
  cfg:      loaded config.yaml dict, or None. When None, behaves as auto.

#### def `build_native_content_parts(user_text: str, image_paths: List[str], image_urls: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], List[str]]`

Build an OpenAI-style ``content`` list for a user turn.

Shape:
  [{"type": "text", "text": "...\n\n[Image attached at: /local/path]"},
   {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
   {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
   ...]

Local paths are read from disk and embedded as base64 ``data:`` URLs.
Remote URLs (``http(s)://``) are passed through verbatim — the provider
fetches them server-side. The model still sees the pixels either way.

For each successfully attached image, a hint is appended to the text
part:

  * local path → ``[Image attached at: <path>]``
  * URL        → ``[Image attached: <url>]``

The hint gives the model a string handle so MCP/skill tools that take
an image path or URL argument can be invoked on the same image without
an extra round-trip. This parallels the text-mode hint produced by
``Runner._enrich_message_with_vision`` (``vision_analyze using image_url:
<path>``) so behaviour is consistent across both image input modes.

Images are attached at their native size. If a provider rejects the
request because an image is too large (e.g. Anthropic's 5 MB per-image
ceiling), the agent's retry loop transparently shrinks and retries
once — see ``run_agent._try_shrink_image_parts_in_messages``.

Returns (content_parts, skipped). Skipped entries are local paths
that couldn't be read from disk; URLs are never skipped (they're
not validated here).


## agent.insights

### 模块文档

Session Insights Engine for Hermes Agent.

Analyzes historical session data from the SQLite state database to produce
comprehensive usage insights — token consumption, cost estimates, tool usage
patterns, activity trends, model/platform breakdowns, and session metrics.

Inspired by Claude Code's /insights command, adapted for Hermes Agent's
multi-platform architecture with additional cost estimation and platform
breakdown capabilities.

Usage:
    from agent.insights import InsightsEngine
    engine = InsightsEngine(db)
    report = engine.generate(days=30)
    print(engine.format_terminal(report))

### class InsightsEngine

> 继承: `object` ｜ 方法数: 16（公开 3）

Analyzes session history and produces usage insights.

Works directly with a SessionDB instance (or raw sqlite3 connection)
to query session and message data.

#### def `__init__(db)`

Initialize with a SessionDB instance.

Args:
    db: A SessionDB instance (from hermes_state.py)

#### def `generate(self, days: int = 30, source: str = None) -> Dict[str, Any]`

Generate a complete insights report.

Args:
    days: Number of days to look back (default: 30)
    source: Optional filter by source platform

Returns:
    Dict with all computed insights

#### def `format_terminal(self, report: Dict) -> str`

Format the insights report for terminal display (CLI).

#### def `format_gateway(self, report: Dict) -> str`

Format the insights report for gateway/messaging (shorter).


## agent.iteration_budget

### 模块文档

Per-agent iteration budget — thread-safe consume/refund counter.

Extracted from ``run_agent.py``.  Each ``AIAgent`` instance (parent or
subagent) holds an :class:`IterationBudget`; the parent's cap comes from
``max_iterations`` (default 90), each subagent's cap comes from
``delegation.max_iterations`` (default 50).

``run_agent`` re-exports ``IterationBudget`` so existing
``from run_agent import IterationBudget`` imports keep working unchanged.

### class IterationBudget

> 继承: `object` ｜ 方法数: 5（公开 4）

Thread-safe iteration counter for an agent.

Each agent (parent or subagent) gets its own ``IterationBudget``.
The parent's budget is capped at ``max_iterations`` (default 90).
Each subagent gets an independent budget capped at
``delegation.max_iterations`` (default 50) — this means total
iterations across parent + subagents can exceed the parent's cap.
Users control the per-subagent limit via ``delegation.max_iterations``
in config.yaml.

``execute_code`` (programmatic tool calling) iterations are refunded via
:meth:`refund` so they don't eat into the budget.

#### def `__init__(max_total: int)`

#### def `consume(self) -> bool`

Try to consume one iteration.  Returns True if allowed.

#### def `refund(self) -> None`

Give back one iteration (e.g. for execute_code turns).

#### property `used(self) -> int`

#### property `remaining(self) -> int`


## agent.jiter_preload

### 模块文档

Best-effort early import for the OpenAI SDK's native streaming parser.

The OpenAI SDK imports ``jiter`` while constructing streaming chat-completion
responses.  On some Windows installs the native extension can be imported
directly from the Hermes venv, but the first import fails when it happens later
inside the threaded streaming request path.  Loading it once during agent
package import avoids that import-order failure while preserving the normal
SDK error path for genuinely missing or broken installs.

### 顶层函数

#### def `preload_jiter_native_extension() -> bool`

Import jiter's native extension early if it is available.


## agent.kanban_stop

### 模块文档

Turn-end guard for kanban workers.

Kanban workers must end with ``kanban_complete`` or ``kanban_block``. Models
(especially GLM / Qwen families) sometimes narrate the next step
("Let me write the report now") and stop with ``finish_reason=stop`` and no
tool calls. Hermes treats that as a clean exit → ``rc=0`` → dispatcher
``protocol_violation``.

This module is policy-only: when a kanban worker tries to finish without a
terminal board tool, return a bounded synthetic nudge so the conversation
loop continues instead of exiting.

### 顶层函数

#### def `kanban_stop_nudge_enabled() -> bool`

Return whether the kanban stop-guard is active for this process.

On when ``HERMES_KANBAN_TASK`` is set (dispatcher-spawned worker), unless
``HERMES_KANBAN_STOP_NUDGE`` explicitly disables it.

#### def `session_called_kanban_terminal(messages: Iterable[dict] | None) -> bool`

True if this conversation already invoked a terminal kanban tool.

#### def `build_kanban_stop_nudge(messages: Iterable[dict] | None = None, attempts: int = 0, max_attempts: int = _DEFAULT_MAX_ATTEMPTS, task_id: Optional[str] = None) -> Optional[str]`

Return a synthetic follow-up when a kanban worker exits without a terminal tool.

Returns ``None`` when the guard should not fire (not a kanban worker,
already completed/blocked, or nudge budget exhausted).


## agent.learn_prompt

### 模块文档

``/learn`` — build the standards-guided prompt that turns whatever the user
described into a reusable skill.

``/learn`` is open-ended. The user can point it at anything they can describe:
a directory of code, an API doc URL, a workflow they just walked the agent
through in this conversation, or pasted notes. This module builds ONE prompt
that instructs the live agent to:

  1. Gather the sources the user named, using the tools it already has
     (``read_file`` / ``search_files`` for dirs, ``web_extract`` for URLs, the
     current conversation for "what I just did", the user's text for pasted
     material).
  2. Author a single ``SKILL.md`` via ``skill_manage`` that follows the Hermes
     skill-authoring standards (description <=60 chars, the modern section
     order, Hermes-tool framing, no invented commands).

There is no separate distillation engine and no model-tool footprint: the
agent does the work with its existing toolset, so this works identically on
local, Docker, and remote terminal backends. Every surface (CLI ``/learn``,
gateway ``/learn``, the dashboard "Learn a skill" panel) calls
:func:`build_learn_prompt` and feeds the result to the agent as a normal turn.

### 顶层函数

#### def `build_learn_prompt(user_request: str) -> str`

Build the agent prompt for an open-ended ``/learn`` request.

Args:
    user_request: the free-text the user gave after ``/learn`` — a
        description of the workflow, paths, URLs, or "what I just did".

Returns:
    A complete instruction the agent runs as a normal turn. The agent
    gathers the described sources with its existing tools and authors the
    skill via ``skill_manage``.


## agent.learning_graph

### 模块文档

Assemble the "learning made visible" graph for desktop.

This graph is intentionally scoped to what a user actually learns over time:
- non-base, learned/profile skills (agent-created or used),
- memory chunks from ``MEMORY.md`` / ``USER.md`` as first-class nodes.

Skill links come from declared ``related_skills``. Memory-to-skill links are
derived from lexical overlap so the graph can answer "which learned skills are
connected to the things I remember?".

Run as a module to print edge-density stats against real data:

    python -m agent.learning_graph

### class SkillNode

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `build_skill_nodes(skill_roots: list[tuple[str, Path]]) -> dict[str, SkillNode]`

#### def `build_edges(nodes: dict[str, SkillNode]) -> list[tuple[str, str]]`

Undirected related_skills edges where BOTH endpoints exist (deduped).

#### def `density_stats(nodes: dict[str, SkillNode], edges: list[tuple[str, str]]) -> dict[str, Any]`

#### def `build_learning_graph() -> dict[str, Any]`

Full payload for the desktop learning panel.

Focus on what is profile-learned and actionable:
- skills that are NOT base-installed and show real learning signal
  (agent-created or used),
- memory chunks as first-class graph nodes connected to those learned skills.


## agent.learning_graph_render

### 模块文档

Terminal renderer for the learning timeline (learned skills + memories).

The desktop app (``apps/desktop/src/app/starmap``) paints a GPU radial
constellation; a terminal can't, so this is a *rendition* of the same data as a
timeline bar chart — date rows, proportional skill/memory bars colored by the
day's dominant category, and a cumulative trajectory sparkline — plus per-slice
bucket metadata the TUI walks as a tree. The age gradient and complementary
memory ink are ported from the desktop source, not guessed.

Grids are emitted as style runs — ``[text, style, alpha, hex?]`` — so each
consumer maps the semantic style + brightness onto its own palette; the
optional 4th element overrides the base color (category heatmap). Pure,
stdlib-only.

### 顶层函数

#### def `recency_ink(rec: float) -> float`

Port of geometry.ts ``recencyInk`` — smoothstep age → ink alpha.

#### def `format_date(ts: Optional[float]) -> str`

#### def `compute_recency(nodes: list[dict[str, Any]]) -> dict[str, Any]`

Port of time-axis.ts ``computeRecency`` (id → recency ratio, timed flag).

#### def `hex_to_rgb(s: str) -> tuple[int, int, int]`

#### def `rgb_to_hex(c: tuple) -> str`

#### def `mix_rgb(a: tuple, b: tuple, t: float) -> tuple[int, int, int]`

#### def `derive_palette(primary_hex: str, dark: bool = True) -> dict[str, str]`

Port of color.ts ``computePalette`` (the bits a terminal needs).

#### def `category_color_map(payload: dict[str, Any]) -> dict[str, str]`

Deterministic, evenly-spread hue per skill category (theme-independent).

#### def `category_legend(payload: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]`

#### def `render_graph(payload: dict[str, Any], cols: int = 80, rows: int = 16, reveal: float = 1.0) -> dict[str, Any]`

Render one timeline frame at ``reveal`` (0→1).

Date rows with proportional skill/memory bars colored by the day's dominant
category, numbered markers tied to label rows, and a cumulative trajectory
sparkline underneath.

#### def `build_legend(payload: dict[str, Any]) -> list[dict[str, Any]]`

#### def `axis_labels(payload: dict[str, Any]) -> dict[str, str]`

#### def `build_summary(payload: dict[str, Any]) -> list[str]`

#### def `render_frames(payload: dict[str, Any], cols: int = 80, rows: int = 16, frames: int = 48) -> dict[str, Any]`

Pre-render a full play-through (reveal 0→1) plus static legend/summary.


## agent.learning_mutations

### 模块文档

User-initiated edit/delete for journey nodes (learned skills + memories).

The journey graph (``agent.learning_graph``) gives every node a stable id:

- **skills** → the skill name (e.g. ``"debugging-hermes-desktop"``)
- **memories** → ``memory:<source>:<index>`` where ``source`` is ``memory``
  (``MEMORY.md``) or ``profile`` (``USER.md``) and ``index`` is the node's
  position in the combined card list (``MEMORY.md`` cards first, then
  ``USER.md``).

This module maps a node id back to its on-disk home and performs the mutation,
shared by the CLI (``hermes journey delete|edit``), the TUI ``/journey`` overlay
(gateway RPCs), and the desktop GUI (REST). Deleting a skill *archives* it
(recoverable via ``hermes curator restore``); deleting a memory rewrites its
file. Pure stdlib + existing skill/memory helpers.

### 顶层函数

#### def `parse_node_kind(node_id: str) -> str`

#### def `node_detail(node_id: str) -> dict[str, Any]`

Current content for an edit prefill. ``content`` is the full SKILL.md
(skills) or the raw memory chunk (memories).

#### def `delete_node(node_id: str) -> dict[str, Any]`

#### def `edit_node(node_id: str, content: str) -> dict[str, Any]`


## agent.lmstudio_reasoning

### 模块文档

LM Studio reasoning-effort resolution shared by the chat-completions
transport and run_agent's iteration-limit summary path.

LM Studio publishes per-model ``capabilities.reasoning.allowed_options`` (e.g.
``["off","on"]`` for toggle-style models, ``["off","minimal","low"]`` for
graduated models). We map the user's ``reasoning_config`` onto LM Studio's
OpenAI-compatible vocabulary, then clamp against the model's allowed set so
the server doesn't 400 on an unsupported effort.

### 顶层函数

#### def `resolve_lmstudio_effort(reasoning_config: Optional[dict], allowed_options: Optional[List[str]]) -> Optional[str]`

Return the ``reasoning_effort`` string to send to LM Studio, or ``None``.

``None`` means "omit the field": the user picked a level the model can't
honor, so let LM Studio fall back to the model's declared default rather
than silently substituting a different effort. When ``allowed_options`` is
falsy (probe failed), skip clamping and send the resolved effort anyway.


## agent.lsp.__init__

### 模块文档

Language Server Protocol (LSP) integration for Hermes Agent.

Hermes runs full language servers (pyright, gopls, rust-analyzer,
typescript-language-server, etc.) as subprocesses and pipes their
``textDocument/publishDiagnostics`` output into the post-write lint
delta filter used by ``write_file`` and ``patch``.

LSP is **gated on git workspace detection** — if the agent's cwd is
inside a git repository, LSP runs against that workspace; otherwise the
file_operations layer falls back to its existing in-process syntax
checks.  This keeps users on user-home cwd's (e.g. Telegram gateway
chats) from spawning daemons they don't need.

Public API:

    from agent.lsp import get_service

    svc = get_service()
    if svc and svc.enabled_for(path):
        await svc.touch_file(path)
        diags = svc.diagnostics_for(path)

The bulk of the wiring is internal — most callers only need the layer
in :func:`tools.file_operations.FileOperations._check_lint_delta`,
which is already wired (see that module).

Architecture is documented in ``website/docs/user-guide/features/lsp.md``.

### 顶层函数

#### def `get_service() -> Optional[LSPService]`

Return the process-wide LSP service singleton, or None when disabled.

The service is created lazily on first call.  ``None`` is returned
when LSP is disabled in config, when no workspace can be detected,
or when the platform doesn't support subprocess-based LSP servers.

On first creation, registers an :mod:`atexit` handler that tears
down spawned language servers on Python exit so a long-running
CLI or gateway session doesn't leak pyright/gopls/etc. processes
when it terminates.

#### def `shutdown_service() -> None`

Tear down the LSP service if one was started.

Safe to call multiple times; safe to call when no service was created.


## agent.lsp.cli

### 模块文档

``hermes lsp`` CLI subcommand.

Subcommands:

- ``status`` — show service state, configured servers, install status.
- ``install <server_id>`` — eagerly install one server's binary.
- ``install-all`` — try to install every server with a known recipe.
- ``restart`` — tear down running clients so the next edit re-spawns.
- ``which <server_id>`` — print the resolved binary path for one server.
- ``list`` — print the registry of supported servers.

The handlers are kept here (rather than in
``hermes_cli/main.py``) so the LSP module ships self-contained.

### 顶层函数

#### def `register_subparser(subparsers: argparse._SubParsersAction) -> None`

Wire the ``hermes lsp`` subcommand tree into the main argparse.

#### def `run_lsp_command(args: argparse.Namespace) -> int`

Top-level dispatcher for ``hermes lsp <subcommand>``.


## agent.lsp.client

### 模块文档

Async LSP client over stdin/stdout.

One :class:`LSPClient` corresponds to one ``(language_server, workspace_root)``
pair — exactly what OpenCode keys clients on, and the same shape Claude
Code uses.  The client owns a child process, drives the JSON-RPC
exchange, and exposes:

- :meth:`open_file` / :meth:`change_file` — text document sync
- :meth:`wait_for_diagnostics` — block until the server emits fresh
  diagnostics for a specific file (or a timeout fires)
- :meth:`diagnostics_for` — read the current per-file diagnostic store
- :meth:`shutdown` — graceful close + SIGTERM/SIGKILL fallback

The class is designed for async use from a single asyncio event loop.
The :class:`agent.lsp.manager.LSPService` runs an event loop in a
background thread so the synchronous file_operations layer can call
into it via :func:`agent.lsp.manager.LSPService.touch_file`.

Implementation notes:

- All per-document state lives in one :class:`_DocState` keyed by
  absolute path.  Freshness is tracked with **document versions**,
  not timestamps: every didChange bumps ``version``, and each stored
  push/pull result is tagged with the version it describes.  A
  result is fresh iff its tag >= the version being waited on, so a
  didChange implicitly invalidates everything older — no clearing,
  no clock comparisons, no race windows.  This is what prevents
  "ghost diagnostics": a slow server's leftovers from the previous
  edit can never masquerade as a verdict on the current content.

- Whole-document sync.  Even when the server advertises incremental
  sync, we send a single ``contentChanges`` entry replacing the
  entire document.  Pretending to be incremental while sending a
  full replacement is well-tolerated by every major server and saves
  range bookkeeping.  See OpenCode's ``client.ts:584-659`` for the
  same trick.

- The "touch-file dance": every ``open_file`` call also fires a
  ``workspace/didChangeWatchedFiles`` notification (CREATED on the
  first open, CHANGED thereafter).  Some servers (clangd, eslint)
  only re-scan when this notification fires, even though the LSP spec
  doesn't strictly require it.

- ``ContentModified`` (-32801) errors get retried with exponential
  backoff up to 3 times.  This matches Claude Code's
  ``LSPServerInstance.sendRequest``.

### class LSPClient

> 继承: `object` ｜ 方法数: 33（公开 8）

Async LSP client tied to one server process and one workspace root.

Lifecycle:

    c = LSPClient(server_id, workspace_root, command, args, init_options)
    await c.start()       # spawn + initialize
    ver = await c.open_file("/path/to/foo.py")
    await c.wait_for_diagnostics("/path/to/foo.py", ver)
    diags = c.diagnostics_for("/path/to/foo.py")
    await c.shutdown()

#### def `__init__(server_id: str, workspace_root: str, command: List[str], env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None, initialization_options: Optional[Dict[str, Any]] = None, seed_diagnostics_on_first_push: bool = False) -> None`

#### property `is_running(self) -> bool`

#### property `state(self) -> str`

#### async def `start(self) -> None`

Spawn the server and complete the initialize handshake.

Raises any exception encountered during spawn/init.  On failure
the process is killed and the client is left in state
``"error"`` — re-call ``start()`` to retry.

#### async def `shutdown(self) -> None`

Best-effort graceful shutdown.

Sends ``shutdown`` + ``exit``, then SIGTERMs/SIGKILLs the
process if it doesn't exit cleanly.  Idempotent.

#### async def `open_file(self, path: str, language_id: str = 'plaintext') -> int`

Send didOpen (first time) or didChange (subsequent) for ``path``.

Returns the new document version number that the agent's
``wait_for_diagnostics`` should match against.

**异常**: `LSPProtocolError`

#### async def `save_file(self, path: str) -> None`

Send didSave for ``path``.  Some linters re-scan only on save.

#### async def `wait_for_diagnostics(self, path: str, version: int, mode: str = 'document', timeout: Optional[float] = None) -> bool`

Wait for the server to publish diagnostics for ``path`` at ``version``.

``mode`` is ``"document"`` (5s budget, document pulls) or
``"full"`` (10s budget, also workspace pulls).  ``timeout``
overrides the mode's default budget when provided — this is
how the user's ``lsp.wait_timeout`` config reaches the wait
loop (slow servers like tsserver on big projects need more
than the 5s default).

Returns ``True`` when *fresh* diagnostics arrived (a push at
or after our didChange, or a pull answered after it) and
``False`` on timeout.  Callers must treat ``False`` as "no
data", NOT as "no errors" — the diagnostic stores may still
hold stale entries from the previous edit at that point.
Best-effort — never throws if the server doesn't support pull
diagnostics; we still get the push side.

#### def `diagnostics_for(self, path: str, fresh_only: bool = False) -> List[Dict[str, Any]]`

Return current merged + deduped diagnostics for one file.

Diagnostics from push and pull stores are concatenated and
deduplicated by ``(severity, code, message, range)`` content
key.  Empty list if the server hasn't published anything.

With ``fresh_only=True``, a store only contributes when its
version tag has caught up to the document's current version —
stale leftovers from the previous edit cycle are excluded.
This is what report paths should use: after an edit, "stale
errors" and "no errors" must not be conflated.


### 顶层函数

#### def `file_uri(path: str) -> str`

Return ``file://`` URI for an absolute filesystem path.

Mirrors Node's ``pathToFileURL`` — handles spaces, unicode, and
Windows drive letters (``C:\foo`` → ``file:///C:/foo``).

#### def `uri_to_path(uri: str) -> str`

Inverse of :func:`file_uri`.


## agent.lsp.eventlog

### 模块文档

Structured logging with steady-state silence for the LSP layer.

The LSP layer fires on every write_file/patch.  In a busy session
that's hundreds of events.  We want users to be able to ``rg`` the
log for "did LSP fire on that edit?" without drowning in noise.

The level model:

- ``DEBUG`` for steady-state events that have no novel signal:
  ``clean``, ``feature off``, ``extension not mapped``, ``no project
  root for already-announced file``, ``server unavailable for
  already-announced binary``.  These never reach ``agent.log`` at the
  default INFO threshold.

- ``INFO`` for state transitions worth surfacing exactly once per
  session: ``active for <root>`` the first time a (server_id,
  workspace_root) client starts, ``no project root for <path>``
  the first time we see that file.  Plus every diagnostic event
  (those are inherently rare and per-edit, exactly what users grep
  for).

- ``WARNING`` for action-required failures: ``server unavailable``
  (binary not on PATH) the first time per (server_id, binary),
  ``no server configured`` once per language.  Per-call WARNING for
  timeouts and unexpected bridge exceptions.

The dedup is in-process module-level sets.  Each set grows at most by
the number of distinct (server_id, root) and (server_id, binary)
pairs touched in one Python process — bytes of memory in even an
aggressive monorepo session.  Bounded LRU was rejected: evicting an
entry would risk re-firing the WARNING/INFO line we explicitly want
to suppress.

Grep recipe::

    tail -f ~/.hermes/logs/agent.log | rg 'lsp\['

### 顶层函数

#### def `log_clean(server_id: str, file_path: str) -> None`

No diagnostics emitted for *file_path*.  DEBUG (silent at default).

#### def `log_disabled(server_id: str, file_path: str, reason: str) -> None`

LSP intentionally skipped for this file (feature off, ext unmapped,
backend not local, etc.).  DEBUG.

#### def `log_active(server_id: str, workspace_root: str) -> None`

A new LSP client started for (server_id, workspace_root).

INFO once per (server_id, workspace_root); DEBUG thereafter.
Lets users verify "is LSP actually running?" with a single grep.

#### def `log_diagnostics(server_id: str, file_path: str, count: int) -> None`

Diagnostics arrived for a file.  INFO every time — these are the
failure signals users actually want to grep for, and they are
inherently rare per edit.

#### def `log_no_project_root(server_id: str, file_path: str) -> None`

File had no recognised project marker.  INFO once per file,
DEBUG thereafter.

#### def `log_server_unavailable(server_id: str, binary_or_pkg: str) -> None`

The server binary couldn't be resolved.  WARNING once per
(server_id, binary), DEBUG thereafter so a hundred subsequent
.py edits don't spam the log.

#### def `log_no_server_configured(server_id: str) -> None`

No spawn recipe for this language.  WARNING once.

#### def `log_timeout(server_id: str, file_path: str, kind: str = 'diagnostics') -> None`

A request to the server timed out.  WARNING every time — these are
inherently novel events worth surfacing on each occurrence.

#### def `log_server_error(server_id: str, file_path: str, exc: BaseException) -> None`

An unexpected exception bubbled out of the LSP layer.  WARNING.

#### def `log_spawn_failed(server_id: str, workspace_root: str, exc: BaseException) -> None`

The LSP server failed to spawn or initialize.  WARNING.

#### def `reset_announce_caches() -> None`

Test-only: clear the dedup caches.  Production code never calls this.


## agent.lsp.install

### 模块文档

Auto-installation of LSP server binaries.

Tries to install missing servers using whatever package manager is
appropriate.  All installs go to a Hermes-owned bin staging dir,
``<HERMES_HOME>/lsp/bin/``, so we don't pollute the user's global
toolchain.

Strategies:

- ``auto`` — attempt to install with the best available package
  manager.  This is the default.
- ``manual`` — never install; if a binary is missing, the server is
  silently skipped and the user is told about it via ``hermes lsp
  status``.
- ``off`` — same as ``manual`` for now (kept distinct so we can
  evolve behavior later, e.g. logging differently).

The actual installs happen synchronously the first time a server is
needed and concurrent calls to :func:`try_install` for the same
package are deduplicated via a per-package lock.

Failure modes are non-fatal: every install path is wrapped in
try/except and returns ``None`` on failure.  The tool layer then
falls back to its in-process syntax checker, exactly as if the user
hadn't enabled LSP at all.

### 顶层函数

#### def `hermes_lsp_bin_dir() -> Path`

Return the Hermes-owned bin staging dir for LSP servers.

#### def `try_install(pkg: str, strategy: str = 'auto') -> Optional[str]`

Try to install ``pkg`` and return the binary path if successful.

``strategy`` is ``"auto"``, ``"manual"``, or ``"off"``.  In
``manual``/``off`` mode, this function only probes for an
existing binary and returns ``None`` if not found.

The install is cached per-package — a second call returns the
same path (or ``None``) without reinstalling.  Concurrent calls
are serialized.

#### def `detect_status(pkg: str) -> str`

Return ``installed``, ``missing``, or ``manual-only`` for a package.

Used by the ``hermes lsp status`` CLI to give users a quick
overview of what's available without spawning anything.


## agent.lsp.manager

### 模块文档

Service-level orchestration for LSP clients.

The :class:`LSPService` is the bridge between the synchronous
file_operations layer and the async :class:`agent.lsp.client.LSPClient`.

Design choices:

- A **single asyncio event loop** runs in a background thread.  All
  client work happens on that loop.  Synchronous callers from
  ``tools/file_operations.py`` use :meth:`get_diagnostics_sync` to
  open + wait + drain in one blocking call.

- One client per ``(server_id, workspace_root)`` key.  Lazy spawn:
  the first request for a key spawns the client; subsequent requests
  re-use it.

- A **broken-set** records ``(server_id, workspace_root)`` pairs that
  failed to spawn or initialize.  These are never retried for the
  life of the service.  Mirrors OpenCode's design.

- A **delta baseline** map keeps "diagnostics-as-of-the-last-snapshot"
  per file.  ``snapshot_baseline()`` is called BEFORE a write; the
  next ``get_diagnostics_sync()`` returns only diagnostics that
  weren't in the baseline.  This is the lift from Claude Code's
  ``beforeFileEdited`` / ``getNewDiagnostics`` pattern, except wired
  to the local LSP layer instead of MCP IDE RPC.

The service is **off by default** — call :meth:`is_active` to check
whether it's actually doing anything.  When LSP is disabled in
config, when no git workspace can be detected, when all configured
servers are missing binaries and auto-install is off, ``is_active``
returns False and the file_operations layer falls through to the
in-process syntax check.

### class LSPService

> 继承: `object` ｜ 方法数: 14（公开 7）

The process-wide LSP service.

Created once via :meth:`create_from_config`; the
:func:`agent.lsp.get_service` accessor manages the singleton.
Most callers should use that accessor rather than constructing
:class:`LSPService` directly.

#### def `__init__(enabled: bool, wait_mode: str, wait_timeout: float, install_strategy: str, binary_overrides: Optional[Dict[str, List[str]]] = None, env_overrides: Optional[Dict[str, Dict[str, str]]] = None, init_overrides: Optional[Dict[str, Dict[str, Any]]] = None, disabled_servers: Optional[List[str]] = None, idle_timeout: float = DEFAULT_IDLE_TIMEOUT) -> None`

#### classmethod `create_from_config(cls) -> Optional['LSPService']`

Build a service from ``hermes_cli.config`` settings.

Returns ``None`` if the config can't be loaded.  The service
itself returns ``is_active()`` False when LSP is disabled.

#### def `is_active(self) -> bool`

Return True iff this service should be consulted at all.

#### def `enabled_for(self, file_path: str) -> bool`

Return True iff LSP should run for this specific file.

Gates on workspace detection (file or cwd inside a git worktree),
on whether any registered server matches the extension, and
on whether the (server_id, workspace_root) pair is in the
broken-set from a previous spawn failure.

Files in already-broken pairs return False so the file_operations
layer skips the LSP path entirely — no spawn attempts, no
timeout cost — until the service is restarted (``hermes lsp
restart``) or the process exits.

#### def `snapshot_baseline(self, file_path: str) -> None`

Snapshot current diagnostics for ``file_path`` as the delta baseline.

Called BEFORE a write so the next ``get_diagnostics_sync()``
can filter out pre-existing errors.  Best-effort — failures
are silently swallowed so a flaky server can't break a write.

Outer timeouts (e.g. server hangs during initialize) mark the
(server_id, workspace_root) pair as broken so subsequent edits
skip it instantly instead of re-paying the timeout cost.

#### def `get_diagnostics_sync(self, file_path: str, delta: bool = True, timeout: Optional[float] = None, line_shift: Optional[Callable[[int], Optional[int]]] = None) -> List[Dict[str, Any]]`

Synchronously open ``file_path`` in the right server, wait for
diagnostics, return them.

If ``delta`` is True (default), the result is filtered against
any baseline previously captured via :meth:`snapshot_baseline`.
Diagnostics present in the baseline are removed so the caller
only sees errors introduced by the current edit.

When ``line_shift`` is provided, baseline diagnostics are
remapped through it before the set-difference.  This handles
the case where the edit deleted or inserted lines, causing
pre-existing diagnostics below the edit point to surface at
different line numbers in the post-edit snapshot — without
the shift, they'd all look "introduced by this edit".  Pass
a callable built by
:func:`agent.lsp.range_shift.build_line_shift` (pre_text,
post_text).  Omit when pre/post content isn't available;
the unshifted comparison still catches diagnostics that
didn't move.

Returns an empty list when LSP is disabled, when no workspace
can be detected, when no server matches, or when the server
can't be spawned.  Never raises.

#### def `shutdown(self) -> None`

Tear down all clients and stop the background loop.

#### def `get_status(self) -> Dict[str, Any]`

Return a snapshot of the service for the CLI status command.


## agent.lsp.protocol

### 模块文档

Minimal LSP JSON-RPC 2.0 framer over async streams.

LSP wire format:

    Content-Length: <bytes>\r\n
    \r\n
    <utf-8 JSON body>

The body is a JSON-RPC 2.0 envelope: request, response, or notification.

This module replaces what ``vscode-jsonrpc/node`` would do in a
TypeScript implementation.  We keep it deliberately small — just the
framer + envelope helpers — so :class:`agent.lsp.client.LSPClient` can
focus on protocol semantics.

### class LSPProtocolError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Raised when the wire protocol is violated.

Distinct from :class:`LSPRequestError` which represents a server
returning a JSON-RPC error response — that's protocol-conformant.
This exception means the framing or envelope itself is broken.


### class LSPRequestError

> 继承: `Exception` ｜ 方法数: 1（公开 0）

Raised when an LSP request returns an error response.

Carries the JSON-RPC ``code``, ``message``, and optional ``data``.

#### def `__init__(code: int, message: str, data: Any = None) -> None`


### 顶层函数

#### def `encode_message(obj: dict) -> bytes`

Encode a JSON-RPC envelope as a Content-Length framed byte string.

The body is encoded as compact UTF-8 JSON (no spaces between
separators) — matches what ``vscode-jsonrpc`` emits and keeps the
Content-Length count exact.

#### def `read_message(reader: asyncio.StreamReader) -> Optional[dict]`

Read one Content-Length framed JSON-RPC message from the stream.

Returns ``None`` on clean EOF (server closed stdout cleanly between
messages — typical shutdown).  Raises :class:`LSPProtocolError` on
malformed framing.

The reader is advanced to just past the JSON body on success.

**异常**: `class`, `LSPProtocolError`

#### def `make_request(req_id: int, method: str, params: Any) -> dict`

Build a JSON-RPC 2.0 request envelope.

#### def `make_notification(method: str, params: Any) -> dict`

Build a JSON-RPC 2.0 notification envelope (no ``id``).

#### def `make_response(req_id: Any, result: Any) -> dict`

Build a JSON-RPC 2.0 success response envelope.

#### def `make_error_response(req_id: Any, code: int, message: str, data: Any = None) -> dict`

Build a JSON-RPC 2.0 error response envelope.

#### def `classify_message(msg: dict) -> Tuple[str, Any]`

Return ``(kind, key)`` where kind is one of ``request``,
``response``, ``notification``, ``invalid``.

The key is the request id for request/response, the method name
for notifications, and ``None`` for invalid messages.


## agent.lsp.range_shift

### 模块文档

Diff-aware line-shift map for cross-edit LSP delta filtering.

When an edit deletes or inserts lines in the middle of a file, every
diagnostic below the edit point shifts to a new line number.  The
LSPService delta filter subtracts the pre-edit baseline from the
post-edit diagnostics keyed on ``(severity, code, source, message,
range)`` — without an adjustment, the shifted-but-otherwise-identical
diagnostics look brand-new and the agent gets flooded with noise.

The fix used here is the same trick git's blame and unified diff use:
build a piecewise-linear map from pre-edit line numbers to post-edit
line numbers, then apply that map to baseline diagnostics before the
set-difference.  Diagnostics whose pre-edit line is in a region the
edit deleted return ``None`` and are dropped from the baseline (they
genuinely no longer apply).

Trade-off vs. dropping range from the key entirely (the previous
fix): preserves the "new instance of an identical error at a
different line" signal — if the model introduces a second instance
of the same error class at a different location, that one will be
surfaced as new instead of swallowed by content-only dedup.

The map is derived from ``difflib.SequenceMatcher.get_opcodes()`` and
exposed as a single callable so callers don't have to reason about
diff regions.

### 顶层函数

#### def `build_line_shift(pre_text: str, post_text: str) -> Callable[[int], Optional[int]]`

Build a function mapping pre-edit line numbers to post-edit line numbers.

Lines are 0-indexed to match the LSP wire format
(``range.start.line`` is 0-indexed).

The returned callable takes a pre-edit 0-indexed line number and
returns the corresponding post-edit 0-indexed line number, or
``None`` if that line was deleted by the edit (no post-edit
counterpart exists).

Cost: one ``SequenceMatcher.get_opcodes()`` call up front; the
returned closure is O(log n) per call (binary search over opcode
regions).  Cheap enough to call once per write/patch and apply to
every baseline diagnostic.

#### def `shift_diagnostic_range(diag: Dict[str, Any], shift: Callable[[int], Optional[int]]) -> Optional[Dict[str, Any]]`

Return a copy of ``diag`` with its line range remapped through ``shift``.

Returns ``None`` if the diagnostic's start line maps to ``None``
(the line was deleted by the edit) — caller drops it from the
baseline since the diagnostic no longer applies.

Both ``start.line`` and ``end.line`` are remapped independently;
when only the end maps to ``None`` (rare, multi-line diagnostic
straddling the edit boundary) we collapse to a single-line range
at the shifted start to keep the diagnostic in the baseline.

The original ``diag`` is not mutated.

#### def `shift_baseline(baseline: List[Dict[str, Any]], shift: Callable[[int], Optional[int]]) -> List[Dict[str, Any]]`

Apply ``shift`` to every diagnostic in ``baseline``, dropping deleted entries.


## agent.lsp.reporter

### 模块文档

Format LSP diagnostics for inclusion in tool output.

The model sees a compact, severity-filtered, line-bounded summary of
diagnostics introduced by the latest edit.  Format matches what
OpenCode's ``lsp/diagnostic.ts`` and Claude Code's
``formatDiagnosticsSummary`` produce — ``<diagnostics>`` blocks with
1-indexed line/column, capped at ``MAX_PER_FILE`` errors.

### 顶层函数

#### def `format_diagnostic(d: Dict[str, Any]) -> str`

One-line representation of a single diagnostic.

``message``, ``code``, and ``source`` are sanitized before
interpolation — see ``_sanitize_field``.

#### def `report_for_file(file_path: str, diagnostics: List[Dict[str, Any]], severities: frozenset = DEFAULT_SEVERITIES, max_per_file: int = MAX_PER_FILE) -> str`

Build a ``<diagnostics file=...>`` block for one file.

Returns an empty string when no diagnostics pass the severity
filter, so callers can do ``if block:`` to skip empty cases.

#### def `truncate(s: str, limit: int = MAX_TOTAL_CHARS) -> str`

Hard-cap a formatted summary string.


## agent.lsp.servers

### 模块文档

Server registry — per-language LSP server definitions.

Each :class:`ServerDef` knows how to:

- match a file by extension (or basename for extensionless files like
  ``Dockerfile``),
- resolve a project root from a file path (often via
  :func:`agent.lsp.workspace.nearest_root`),
- assemble the spawn command (binary, args, env, cwd),
- compute LSP ``initializationOptions``.

Auto-installation is a separate concern handled by
:mod:`agent.lsp.install`.  This module describes WHAT to spawn; the
install module makes the binary appear on PATH if it isn't there.

The full set of servers ships with the package, but most are only
*invoked* when the user actually edits a file in that language.  This
keeps cold-start fast — we don't probe binaries until needed.

### class SpawnSpec

> 继承: `object` ｜ 方法数: 0（公开 0）

The result of resolving a server for a file.

Returned by :meth:`ServerDef.resolve` when a server is applicable
to a file.  ``None`` is returned instead when the server should
be skipped (binary missing and auto-install disabled, project
marker not found, exclude marker hit, etc.).


### class ServerDef

> 继承: `object` ｜ 方法数: 1（公开 1）

Definition of one language server.

The :func:`resolve_root` callable receives the absolute file path
plus the workspace root (git worktree) and returns either the
project-specific root for this server (e.g. the directory
containing ``pyproject.toml``) or ``None`` to skip.

The :func:`build_spawn` callable receives the resolved root and
returns a :class:`SpawnSpec` (or ``None`` if the binary can't be
found and auto-install isn't configured).

#### def `matches(self, file_path: str) -> bool`

Return True iff this server handles ``file_path``.


### class ServerContext

> 继承: `object` ｜ 方法数: 0（公开 0）

Context passed into :meth:`ServerDef.build_spawn`.

Carries the user's auto-install policy, any user-overridden
binary paths, and helpers the spawn builder needs.  All fields
are optional; defaults yield "auto-install allowed, no overrides".


### 顶层函数

#### def `hermes_lsp_session_dir() -> str`

Return (and create) the dir for PSES session/log scratch files.

#### def `find_server_for_file(file_path: str) -> Optional[ServerDef]`

Return the registry entry that handles ``file_path``, or None.

#### def `language_id_for(path: str) -> str`

Return the LSP languageId to send in didOpen for ``path``.


## agent.lsp.workspace

### 模块文档

Workspace and project-root resolution for LSP.

Two concerns live here:

1. **Workspace gate** — the upper-level "is this directory a project?"
   check.  Hermes only runs LSP when the cwd (or the file being edited)
   sits inside a git worktree.  Files outside any git root never
   trigger LSP, even if a server is configured.  This keeps Telegram
   gateway users on user-home cwd's from spawning daemons.

2. **NearestRoot** — the per-server project-root walk.  Each language
   server cares about a different marker (``pyproject.toml`` for
   Python, ``Cargo.toml`` for Rust, ``go.mod`` for Go, etc.) and
   wants the directory containing that marker.  ``nearest_root()``
   walks up from a starting path looking for any of a list of marker
   files, optionally bailing if an exclude marker shows up first.

### 顶层函数

#### def `normalize_path(path: str) -> str`

Normalize a path for use as a stable map key.

Resolves ``~``, makes absolute, and collapses ``.``/``..``.  We do
NOT resolve symlinks here — symlink stability matters for some
LSP servers (rust-analyzer cares about Cargo workspace identity)
and we want the canonical path the user typed when possible.

#### def `find_git_worktree(start: str) -> Optional[str]`

Walk up from ``start`` looking for a ``.git`` entry (file or dir).

Returns the directory containing ``.git``, or ``None`` if no git
root is found before hitting the filesystem root.

A ``.git`` *file* (not directory) means we're inside a git
worktree set up via ``git worktree add`` — both forms count.

#### def `is_inside_workspace(path: str, workspace_root: str) -> bool`

Return True iff ``path`` is inside (or equal to) ``workspace_root``.

Uses absolute paths but does not resolve symlinks — a file accessed
via a symlink that points outside the workspace still counts as
outside.  This is the conservative interpretation; matches LSP
behaviour where servers reject didOpen for unrelated files.

#### def `nearest_root(start: str, markers: Iterable[str], excludes: Optional[Iterable[str]] = None, ceiling: Optional[str] = None) -> Optional[str]`

Walk up from ``start`` looking for any of the given marker files.

Returns the **directory containing** the first matched marker, or
``None`` if no marker is found before hitting ``ceiling`` (or the
filesystem root if no ceiling).

If ``excludes`` is provided and an exclude marker matches *first*
in the upward walk, returns ``None`` — the server is gated off
for that file.  Mirrors OpenCode's NearestRoot exclude semantics
(e.g. typescript skips deno projects when ``deno.json`` is found
before ``package.json``).

#### def `resolve_workspace_for_file(file_path: str, cwd: Optional[str] = None) -> Tuple[Optional[str], bool]`

Resolve the workspace root for a file.

Returns ``(workspace_root, gated_in)`` where ``gated_in`` is True
iff LSP should run for this file at all.  Currently the gate is
"file is inside a git worktree found by walking up from cwd OR
from the file itself".

The cwd path takes precedence — if the agent was launched in a
git project, that worktree is the workspace, and any edit inside
it (regardless of where the file lives) is in-scope.  If the cwd
isn't in a git worktree, we try the file's own location as a
fallback.

Returns ``(None, False)`` when neither path is in a git worktree.

#### def `clear_cache() -> None`

Clear the workspace-resolution cache.

Called on service shutdown so a subsequent re-init doesn't pick
up stale results from a previous session.


## agent.manual_compression_feedback

### 模块文档

User-facing summaries for manual compression commands.

### 顶层函数

#### def `summarize_manual_compression(before_messages: Sequence[dict[str, Any]], after_messages: Sequence[dict[str, Any]], before_tokens: int, after_tokens: int, compression_state: Any = None) -> dict[str, Any]`

Return consistent user-facing feedback for manual compression.


## agent.markdown_tables

### 模块文档

CJK/wide-character-aware re-alignment of model-emitted markdown tables.

Models pad markdown tables assuming each character occupies one terminal
cell. CJK glyphs and most emoji render as two cells, so the model's
spacing collapses into drift the moment a table reaches a real terminal —
header pipes line up, every body row drifts right by N cells per CJK
char.

This module rebuilds row padding using ``wcwidth.wcswidth`` (display
columns), preserving the table's pipes and dashes so it still reads as a
plain-text table in ``strip`` / unrendered display modes. Standard Rich
markdown rendering already aligns CJK correctly inside a wide enough
panel; this helper is for the paths that print the model's text more or
less verbatim.

The helper is deliberately conservative:

* Only contiguous ``| ... |`` blocks with a divider line are rewritten.
* Anything that does not look like a table is passed through unchanged.
* Single-line / mid-stream fragments are left alone — callers buffer
  table rows and flush them once the block is complete.

There is a small, intentional caveat: ``wcwidth`` returns ``-1`` for some
emoji-with-variation-selector sequences (e.g. ``⚠️``); we clamp those to
0 so they do not corrupt the column width math. The 1-cell drift on
those specific glyphs is preferable to silently widening every table
that contains one.

### 顶层函数

#### def `split_table_row(row: str) -> List[str]`

Split ``| a | b | c |`` into ``["a", "b", "c"]`` with trims.

#### def `is_table_divider(row: str) -> bool`

True when ``row`` is a markdown table separator line.

#### def `looks_like_table_row(row: str) -> bool`

True when ``row`` could plausibly be a markdown table row.

Used by streaming callers to decide whether to buffer an in-flight
line. We are intentionally permissive here — the realigner itself
only rewrites blocks that are accompanied by a divider, so a false
positive here at most delays the print of one line.

#### def `realign_markdown_tables(text: str, available_width: int | None = None) -> str`

Rewrite every ``| ... |`` + divider block with wcwidth-aware padding.

Lines that are not part of a recognised table are returned verbatim,
so this is safe to apply to arbitrary assistant prose.

If ``available_width`` is given (terminal cells available for the
rendered table), tables wider than that are rendered as vertical
key-value pairs instead of a horizontal pipe-bordered grid.  This
avoids the terminal soft-wrapping mid-cell, which destroys column
alignment visually even when the bytes are perfectly padded.


## agent.memory_manager

### 模块文档

MemoryManager — orchestrates memory providers for the agent.

Single integration point in run_agent.py. Replaces scattered per-backend
code with one manager that delegates to registered providers.

Only ONE external plugin provider is allowed at a time — attempting to
register a second external provider is rejected with a warning.  This
prevents tool schema bloat and conflicting memory backends.

Usage in run_agent.py:
    self._memory_manager = MemoryManager()
    # Only ONE of these:
    self._memory_manager.add_provider(plugin_provider)

    # System prompt
    prompt_parts.append(self._memory_manager.build_system_prompt())

    # Pre-turn
    context = self._memory_manager.prefetch_all(user_message)

    # Post-turn
    self._memory_manager.sync_all(user_msg, assistant_response)
    self._memory_manager.queue_prefetch_all(user_msg)

### class StreamingContextScrubber

> 继承: `object` ｜ 方法数: 11（公开 3）

Stateful scrubber for streaming text that may contain split memory-context spans.

The one-shot ``sanitize_context`` regex cannot survive chunk boundaries:
a ``<memory-context>`` opened in one delta and closed in a later delta
leaks its payload to the UI because the non-greedy block regex needs
both tags in one string.  This scrubber runs a small state machine
across deltas, holding back partial-tag tails and discarding
everything inside a span (including the system-note line).

Usage::

    scrubber = StreamingContextScrubber()
    for delta in stream:
        visible = scrubber.feed(delta)
        if visible:
            emit(visible)
    trailing = scrubber.flush()  # at end of stream
    if trailing:
        emit(trailing)

The scrubber is re-entrant per agent instance.  Callers building new
top-level responses (new turn) should create a fresh scrubber or call
``reset()``.

#### def `__init__() -> None`

#### def `reset(self) -> None`

#### def `feed(self, text: str) -> str`

Return the visible portion of ``text`` after scrubbing.

Any trailing fragment that could be the start of an open/close tag
is held back in the internal buffer and surfaced on the next
``feed()`` call or discarded/emitted by ``flush()``.

#### def `flush(self) -> str`

Emit any held-back buffer at end-of-stream.

If we're still inside an unterminated span the remaining content is
discarded (safer: leaking partial memory context is worse than a
truncated answer).  Otherwise the held-back partial-tag tail is
emitted verbatim (it turned out not to be a real tag).


### class MemoryManager

> 继承: `object` ｜ 方法数: 33（公开 23）

Orchestrates the built-in provider plus at most one external provider.

The builtin provider is always first. Only one non-builtin (external)
provider is allowed.  Failures in one provider never block the other.

#### def `__init__(external_prefetch_timeout: Optional[float] = None) -> None`

**异常**: `ValueError`

#### def `add_provider(self, provider: MemoryProvider) -> None`

Register a memory provider.

Built-in provider (name ``"builtin"``) is always accepted.
Only **one** external (non-builtin) provider is allowed — a second
attempt is rejected with a warning.

#### property `providers(self) -> List[MemoryProvider]`

All registered providers in order.

#### def `get_provider(self, name: str) -> Optional[MemoryProvider]`

Get a provider by name, or None if not registered.

#### def `build_system_prompt(self) -> str`

Collect system prompt blocks from all providers.

Returns combined text, or empty string if no providers contribute.
Each non-empty block is labeled with the provider name.

#### def `prefetch_all(self, query: str, session_id: str = '') -> str`

Collect prefetch context from all providers.

Returns merged context text labeled by provider. Empty providers
are skipped. Failures in one provider don't block others.

#### def `queue_prefetch_all(self, query: str, session_id: str = '') -> None`

Queue background prefetch on all providers for the next turn.

Provider work is dispatched to a background worker so a slow or
wedged provider can never block the caller. See ``sync_all`` for
the full rationale (agent stuck "running" minutes after a turn).

#### def `sync_all(self, user_content: str, assistant_content: str, session_id: str = '', messages: Optional[List[Dict[str, Any]]] = None) -> None`

Sync a completed turn to all providers.

Runs on a background worker thread, NOT inline on the
turn-completion path. A provider's ``sync_turn`` may make a
blocking network/daemon call (a misconfigured Hindsight daemon
was observed blocking ~298s before failing); doing that inline
held ``run_conversation`` open long after the user saw their
response, so every interface (CLI, TUI, gateway) kept the agent
marked "running" for minutes and any follow-up message triggered
an aggressive interrupt. Dispatching off-thread means a slow or
broken provider can never stall the turn — the sync simply
completes (or fails, logged) in the background.

Writes are serialized through a single worker so turn N lands
before turn N+1; provider implementations don't need their own
ordering guarantees.

#### def `flush_pending(self, timeout: Optional[float] = None) -> bool`

Block until queued sync/prefetch work has drained.

Single-worker executor means submitting a sentinel and waiting on
it guarantees every previously-submitted task has run. Returns
True if the barrier completed within ``timeout`` (or no executor
exists), False on timeout. Used at real session boundaries and by
tests that need to assert provider state deterministically.

#### def `get_all_tool_schemas(self) -> List[Dict[str, Any]]`

Collect tool schemas from all providers.

Reserved core tool names (``clarify``, ``delegate_task``, etc.) are
skipped — they are rejected from the routing table in
:meth:`add_provider`, so the manager must not advertise a schema it
will never route. Built-ins always win (#40466).

#### def `get_all_tool_names(self) -> set`

Return set of all tool names across all providers.

#### def `has_tool(self, tool_name: str) -> bool`

Check if any provider handles this tool.

#### def `handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str`

Route a tool call to the correct provider.

Returns JSON string result. Raises ValueError if no provider
handles the tool.

#### def `on_turn_start(self, turn_number: int, message: str, **kwargs) -> None`

Notify all providers of a new turn.

kwargs may include: remaining_tokens, model, platform, tool_count.

#### def `on_session_end(self, messages: List[Dict[str, Any]]) -> None`

Notify all providers of session end.

#### def `commit_session_boundary_async(self, messages: List[Dict[str, Any]], new_session_id: str, parent_session_id: str = '', reason: str = 'new_session') -> None`

Queue old-session extraction + provider rebinding as ONE serialized task.

Session rotation (/new) must deliver ``on_session_end`` (end-of-session
extraction — an LLM-bound call that can take seconds) strictly BEFORE
``on_session_switch`` (which rebinds provider-internal ``_session_id`` /
turn buffers to the new session). Running extraction inline blocked the
/new command for the whole LLM round-trip (#16454); running it on an
ad-hoc thread raced the inline switch — providers key off internal
state, so a late ``on_session_end`` ran against post-switch bindings
(transcript misattributed to the new session id, double-ingest of the
old turn buffer, new-session buffers cleared).

Submitting BOTH hooks as one task on the manager's single background
worker gives both properties at a single chokepoint: the caller returns
immediately, and the worker's FIFO order serializes end→switch against
every other provider write (per-turn ``sync_all``, prefetches), which
already share the same worker. If the executor is unavailable,
``_submit_background`` degrades to inline execution — the pre-#16454
synchronous behavior, slow but correct.

#### def `on_session_switch(self, new_session_id: str, parent_session_id: str = '', reset: bool = False, rewound: bool = False, **kwargs) -> None`

Notify all providers that the agent's session_id has rotated.

Fires on ``/resume``, ``/branch``, ``/reset``, ``/new``, and
context compression — any path that reassigns
``AIAgent.session_id`` without tearing the provider down.

Providers keep running; they only need to refresh cached
per-session state so subsequent writes land in the correct
session's record. See ``MemoryProvider.on_session_switch`` for
the full contract.

``rewound=True`` signals that session_id is unchanged but the
transcript was truncated; providers caching per-turn document
state should invalidate.

#### def `on_pre_compress(self, messages: List[Dict[str, Any]]) -> str`

Notify all providers before context compression.

Returns combined text from providers to include in the compression
summary prompt. Empty string if no provider contributes.

#### def `on_memory_write(self, action: str, target: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Notify external providers when the built-in memory tool writes.

Skips the builtin provider itself (it's the source of the write).

#### def `notify_memory_tool_write(self, tool_result: Any, tool_args: Dict[str, Any], build_metadata: Optional[Callable[[], Dict[str, Any]]] = None) -> None`

Mirror a built-in memory tool call to external providers.

This is the single entry point the agent loop calls after running the
built-in ``memory`` tool. All the decisions about *whether* and *what*
to mirror live here, behind the manager interface — the loop only hands
over the raw tool result and args:

* gate on a committed (non-staged, successful) write,
* expand the single-op and batched (``operations``) shapes,
* keep only mutating actions (add/replace/remove),
* build per-op provenance metadata and forward ``old_text``.

``build_metadata`` is an optional agent-side callable (the loop knows
session/task/tool-call provenance the manager does not) invoked once per
mirrored op.

#### def `on_delegation(self, task: str, result: str, child_session_id: str = '', **kwargs) -> None`

Notify all providers that a subagent completed.

#### def `shutdown_all(self) -> None`

Shut down all providers (reverse order for clean teardown).

Drains the background sync/prefetch executor first (bounded by
``_SYNC_DRAIN_TIMEOUT_S``) so a turn's final sync has a chance to
land before providers are torn down. The worker threads are
daemon, so anything still wedged past the drain window dies with
the interpreter rather than blocking exit.

#### property `shutdown_drain_state(self) -> Dict[str, Any]`

Snapshot of the most recent bounded shutdown drain outcome.

#### def `initialize_all(self, session_id: str, **kwargs) -> None`

Initialize all providers.

Automatically injects ``hermes_home`` into *kwargs* so that every
provider can resolve profile-scoped storage paths without importing
``get_hermes_home()`` themselves.


### 顶层函数

#### def `normalize_tool_schema(schema: Any) -> Optional[Dict[str, Any]]`

Return a function-tool dict with a resolvable top-level ``name``.

Context engines and memory providers expose tool schemas via
``get_tool_schemas()``. The expected shape is a bare function schema
(``{"name": ..., "description": ..., "parameters": ...}``) which callers
wrap as ``{"type": "function", "function": schema}``.

Some providers instead return an entry that is *already* in OpenAI tool
form (``{"type": "function", "function": {"name": ...}}``). Wrapping that
a second time produces ``{"type": "function", "function": {"type":
"function", "function": {...}}}`` whose ``function`` has no top-level
``name``. Strict providers (e.g. DeepSeek) reject the *entire* request
with ``tools[N].function: missing field name`` (HTTP 400), so one bad
schema disables the whole toolset and breaks every turn (#47707).

This helper normalizes both shapes to the bare function schema and
returns ``None`` for anything without a resolvable name, so callers can
skip-with-warning rather than appending a nameless tool.

#### def `memory_provider_tools_enabled(enabled_toolsets: Optional[List[str]]) -> bool`

Return whether external memory-provider tools should be exposed.

#### def `inject_memory_provider_tools(agent: Any) -> int`

Append external memory-provider tool schemas to an agent tool surface.

#### def `sanitize_context(text: str) -> str`

Strip fence tags, injected context blocks, and system notes from provider output.

#### def `build_memory_context_block(raw_context: str) -> str`

Wrap prefetched memory in a fenced block with system note.


## agent.memory_provider

### 模块文档

Abstract base class for pluggable memory providers.

Memory providers give the agent persistent recall across sessions.
The MemoryManager enforces a one-external-provider limit to prevent
tool schema bloat and conflicting memory backends.

External providers (Honcho, Hindsight, Mem0, etc.) are registered
and managed via MemoryManager. Only one external provider runs at a
time.

Registration:
  Plugins ship in plugins/memory/<name>/ and are activated via
  the memory.provider config key.

Lifecycle (called by MemoryManager, wired in run_agent.py):
  initialize()          — connect, create resources, warm up
  system_prompt_block()  — static text for the system prompt
  prefetch(query)        — background recall before each turn
  sync_turn(user, asst)  — async write after each turn
  get_tool_schemas()     — tool schemas to expose to the model
  handle_tool_call()     — dispatch a tool call
  shutdown()             — clean exit

Optional hooks (override to opt in):
  on_turn_start(turn, message, **kwargs) — per-turn tick with runtime context
  on_session_end(messages)               — end-of-session extraction
  on_session_switch(new_session_id, **kwargs) — mid-process session_id rotation
  on_pre_compress(messages) -> str       — extract before context compression
  on_memory_write(action, target, content, metadata=None) — mirror built-in memory writes
  on_delegation(task, result, **kwargs)  — parent-side observation of subagent work
  backup_paths() -> list[str]            — extra on-disk paths to include in `hermes backup`

### class MemoryProvider

> 继承: `ABC` ｜ 方法数: 19（公开 19）

Abstract base class for memory providers.

#### property `name(self) -> str`

Short identifier for this provider (e.g. 'builtin', 'honcho', 'hindsight').

#### def `is_available(self) -> bool`

Return True if this provider is configured, has credentials, and is ready.

Called during agent init to decide whether to activate the provider.
Should not make network calls — just check config and installed deps.

#### def `initialize(self, session_id: str, **kwargs) -> None`

Initialize for a session.

Called once at agent startup. May create resources (banks, tables),
establish connections, start background threads, etc.

kwargs always include:
  - hermes_home (str): The active HERMES_HOME directory path. Use this
    for profile-scoped storage instead of hardcoding ``~/.hermes``.
  - platform (str): "cli", "telegram", "discord", "cron", etc.

kwargs may also include:
  - agent_context (str): "primary", "subagent", "cron", or "flush".
    Providers should skip writes for non-primary contexts (cron system
    prompts would corrupt user representations).
  - agent_identity (str): Profile name (e.g. "coder"). Use for
    per-profile provider identity scoping.
  - agent_workspace (str): Shared workspace name (e.g. "hermes").
  - parent_session_id (str): For subagents, the parent's session_id.
  - user_id (str): Platform user identifier (gateway sessions).
  - user_id_alt (str): Optional alternate stable platform user identifier.

#### def `system_prompt_block(self) -> str`

Return text to include in the system prompt.

Called during system prompt assembly. Return empty string to skip.
This is for STATIC provider info (instructions, status). Prefetched
recall context is injected separately via prefetch().

#### def `prefetch(self, query: str, session_id: str = '') -> str`

Recall relevant context for the upcoming turn.

Called before each API call. Return formatted text to inject as
context, or empty string if nothing relevant. Implementations
should be fast — use background threads for the actual recall
and return cached results here.

session_id is provided for providers serving concurrent sessions
(gateway group chats, cached agents). Providers that don't need
per-session scoping can ignore it.

#### def `queue_prefetch(self, query: str, session_id: str = '') -> None`

Queue a background recall for the NEXT turn.

Called after each turn completes. The result will be consumed
by prefetch() on the next turn. Default is no-op — providers
that do background prefetching should override this.

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '', messages: Optional[List[Dict[str, Any]]] = None) -> None`

Persist a completed turn to the backend.

Called after each turn. Should be non-blocking — queue for
background processing if the backend has latency.

``messages`` is the OpenAI-style conversation message list as of the
completed turn, including any assistant tool calls and tool results.
Providers that do not need raw turn context can ignore it.

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

Return tool schemas this provider exposes.

Each schema follows the OpenAI function calling format:
{"name": "...", "description": "...", "parameters": {...}}

Return empty list if this provider has no tools (context-only).

#### def `handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str`

Handle a tool call for one of this provider's tools.

Must return a JSON string (the tool result).
Only called for tool names returned by get_tool_schemas().

**异常**: `NotImplementedError`

#### def `shutdown(self) -> None`

Clean shutdown — flush queues, close connections.

#### def `on_turn_start(self, turn_number: int, message: str, **kwargs) -> None`

Called at the start of each turn with the user message.

Use for turn-counting, scope management, periodic maintenance.

kwargs may include: remaining_tokens, model, platform, tool_count.
Providers use what they need; extras are ignored.

#### def `on_session_end(self, messages: List[Dict[str, Any]]) -> None`

Called when a session ends (explicit exit or timeout).

Use for end-of-session fact extraction, summarization, etc.
messages is the full conversation history.

NOT called after every turn — only at actual session boundaries
(CLI exit, /reset, gateway session expiry).

#### def `on_session_switch(self, new_session_id: str, parent_session_id: str = '', reset: bool = False, rewound: bool = False, **kwargs) -> None`

Called when the agent switches session_id mid-process.

Fires on ``/resume``, ``/branch``, ``/reset``, ``/new`` (CLI), the
gateway equivalents, and context compression — any path that
reassigns ``AIAgent.session_id`` without tearing the provider down.

Providers that cache per-session state in ``initialize()``
(``_session_id``, ``_document_id``, accumulated turn buffers,
counters) should update or reset that state here so subsequent
writes land in the correct session's record.

Parameters
----------
new_session_id:
    The session_id the agent just switched to.
parent_session_id:
    The previous session_id, if meaningful — set for ``/branch``
    (fork lineage), context compression (continuation lineage),
    and ``/resume`` (the session we're leaving). Empty string
    when no lineage applies.
reset:
    ``True`` when this is a genuinely new conversation, not a
    resumption of an existing one. Fired by ``/reset`` / ``/new``.
    Providers should flush accumulated per-session buffers
    (``_session_turns``, ``_turn_counter``, etc.) when this is
    set. ``False`` for ``/resume`` / ``/branch`` / compression
    where the logical conversation continues under the new id.
rewound:
    ``True`` if session_id is unchanged but the transcript was
    truncated; providers caching per-turn document state should
    invalidate.

Default is no-op for backward compatibility.

#### def `on_pre_compress(self, messages: List[Dict[str, Any]]) -> str`

Called before context compression discards old messages.

Use to extract insights from messages about to be compressed.
messages is the list that will be summarized/discarded.

Return text to include in the compression summary prompt so the
compressor preserves provider-extracted insights. Return empty
string for no contribution (backwards-compatible default).

#### def `on_delegation(self, task: str, result: str, child_session_id: str = '', **kwargs) -> None`

Called on the PARENT agent when a subagent completes.

The parent's memory provider gets the task+result pair as an
observation of what was delegated and what came back. The subagent
itself has no provider session (skip_memory=True).

task: the delegation prompt
result: the subagent's final response
child_session_id: the subagent's session_id

#### def `get_config_schema(self) -> List[Dict[str, Any]]`

Return config fields this provider needs for setup.

Used by 'hermes memory setup' to walk the user through configuration.
Each field is a dict with:
  key:         config key name (e.g. 'api_key', 'mode')
  description: human-readable description
  secret:      True if this should go to .env (default: False)
  required:    True if required (default: False)
  default:     default value (optional)
  choices:     list of valid values (optional)
  url:         URL where user can get this credential (optional)
  env_var:     explicit env var name for secrets (default: auto-generated)

Return empty list if no config needed (e.g. local-only providers).

#### def `save_config(self, values: Dict[str, Any], hermes_home: str) -> None`

Write non-secret config to the provider's native location.

Called by 'hermes memory setup' after collecting user inputs.
``values`` contains only non-secret fields (secrets go to .env).
``hermes_home`` is the active HERMES_HOME directory path.

Providers with native config files (JSON, YAML) should override
this to write to their expected location. Providers that use only
env vars can leave the default (no-op).

All new memory provider plugins MUST implement either:
- save_config() for native config file formats, OR
- use only env vars (in which case get_config_schema() fields
  should all have ``env_var`` set and this method stays no-op).

#### def `on_memory_write(self, action: str, target: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Called when the built-in memory tool writes an entry.

action: 'add', 'replace', or 'remove'
target: 'memory' or 'user'
content: the entry content
metadata: structured provenance for the write, when available. Common
  keys include ``write_origin``, ``execution_context``, ``session_id``,
  ``parent_session_id``, ``platform``, and ``tool_name``.

Use to mirror built-in memory writes to your backend.

#### def `backup_paths(self) -> List[str]`

Return extra on-disk paths this provider stores OUTSIDE HERMES_HOME.

``hermes backup`` only walks HERMES_HOME, so any provider state kept
under ``~/.honcho``, ``~/.hindsight``, ``~/.openviking``, etc. is lost
across a backup/import cycle unless it's declared here.

Return a list of absolute path strings (files or directories). The
backup command resolves each, captures the ones that exist and live
under the user's home directory into a reserved ``_external/`` subtree
of the archive, and ``hermes import`` restores them to their original
locations. Paths outside the home directory are skipped for safety.

MUST be callable without ``initialize()`` and without network — resolve
from config/env only. Default returns an empty list (nothing external).


## agent.message_content

### 顶层函数

#### def `flatten_message_text(content: Any, sep: str = '\n') -> str`

Return the visible text from common chat/Responses message content shapes.


## agent.message_sanitization

### 模块文档

Message and tool-payload sanitization helpers.

Pure functions extracted from ``run_agent.py`` so the AIAgent module can
stay focused on the conversation loop.  These walk OpenAI-format message
lists and structured payloads, repairing or stripping problematic
characters that would otherwise crash ``json.dumps`` inside the OpenAI
SDK or be rejected by upstream APIs.

All helpers are stateless and side-effect-free except for in-place
mutation of their input (where documented).  Backward-compatible
re-exports from ``run_agent`` remain in place so existing imports
``from run_agent import _sanitize_surrogates`` keep working.

### 顶层函数

#### def `close_interrupted_tool_sequence(messages: list, final_response: Any = None) -> bool`

Append a synthetic assistant turn when an interrupted tail is a tool result.

A turn cut short by ``/stop`` can leave the transcript ending on a raw
``tool`` message (a tool finished, or its execution was cancelled, but the
model never streamed a closing assistant turn). Persisting that tail means
the next user message lands as ``… tool → user`` — a role-alternation
violation that strict providers (Gemini, Claude) react to by hallucinating
a continuation of the user's message and ignoring prior context, which
reads to the user as "lost context" (#48879).

``finalize_turn`` closes this on the happy interrupt path, but the
retry/backoff/error interrupt aborts in ``conversation_loop`` ``return``
early and never reach it — this shared helper closes the sequence on all of
them. ``final_response`` is usually empty on an interrupt, so an explicit
placeholder is used rather than an empty-content assistant turn.

Mutates ``messages`` in place. Returns True if a closing turn was appended.


## agent.moa_loop

### 模块文档

Mixture-of-Agents runtime helpers for /moa turns.

The slash command is deliberately not a model tool. It marks one user turn as
MoA-enabled; the normal Hermes agent loop still owns tool calling and turn
termination, while this module gathers reference-model context before each model
iteration.

### class MoAChatCompletions

> 继承: `object` ｜ 方法数: 5（公开 3）

OpenAI-chat-compatible facade where the aggregator is the acting model.

#### def `__init__(preset_name: str, reference_callback: Any = None)`

#### def `consume_reference_usage(self) -> tuple[Any, Any]`

Pop pending reference-fan-out usage + cost, resetting both to empty.

Returns ``(CanonicalUsage, cost_usd_or_None)`` for the most recent
``create()`` and clears the pending values, so a subsequent read (e.g.
a streaming retry re-entering accounting) cannot double-count. Usage is
always a ``CanonicalUsage`` (zeroed if none); cost is a summed-dollars
float or ``None`` when no advisor could be priced.

#### def `consume_and_save_trace(self, session_id: Any = None, aggregator_output_fallback: Any = None) -> None`

Flush the pending full-turn trace to disk, if one is pending.

No-op when tracing is off (``save_moa_turn`` checks the config), when
there is no pending trace (a cache-HIT iteration ran no references), or
when the aggregator input was never recorded. Clears the pending trace
so a repeat consume cannot double-write. Best-effort — never raises.

``aggregator_output_fallback`` is the aggregator's resolved acting text
as the caller already holds it in memory (the streamed assistant text).
On the streaming path the aggregator's output could not be captured
inline at ``create()`` time (the raw token stream was handed to the live
consumer), so ``pending["aggregator_output"]`` is None; we fold the
caller's resolved text in here so the trace is self-contained in BOTH
streaming and non-streaming modes. Non-streaming already has the inline
output and ignores the fallback.

#### def `create(self, **api_kwargs: Any) -> Any`

**异常**: `RuntimeError`


### class MoAClient

> 继承: `object` ｜ 方法数: 4（公开 3）

#### def `__init__(preset_name: str, reference_callback: Any = None)`

#### def `consume_reference_usage(self) -> Any`

Pop the pending reference-fan-out usage from the completions facade.

Lets session accounting fold the MoA advisor tokens into the turn's
usage without reaching into ``.chat.completions`` internals.

#### property `last_aggregator_slot(self) -> Any`

Resolved aggregator slot ({provider, model, ...}) from the most
recent create(), or None. Read by session cost accounting to price the
aggregator's acting turn at its real model instead of the virtual
preset name.

#### def `consume_and_save_trace(self, session_id: Any = None, aggregator_output_fallback: Any = None) -> None`

Flush the pending full-turn MoA trace via the completions facade.

No-op unless ``moa.save_traces`` is enabled and a turn is pending.
``aggregator_output_fallback`` supplies the resolved acting text so the
streaming path's trace is self-contained (see the facade docstring).


### 顶层函数

#### def `aggregate_moa_context(user_prompt: str, api_messages: list[dict[str, Any]], reference_models: list[dict[str, str]], aggregator: dict[str, str], temperature: float | None = None, aggregator_temperature: float | None = None, max_tokens: int | None = None) -> str`

Run configured reference models and synthesize their advice.

Failures are returned as model-specific notes instead of aborting the normal
agent loop; the main model can still act with partial context.

``max_tokens`` is ``None`` by default: MoA does not cap reference or
aggregator output, so each model uses its own maximum. ``call_llm`` omits
the parameter entirely when it is ``None`` (see its docstring), which also
sidesteps providers that reject ``max_tokens`` outright. A hardcoded cap
here previously truncated long aggregator syntheses.

``temperature`` / ``aggregator_temperature`` are ``None`` by default:
like max_tokens, ``call_llm`` omits temperature when None so the
provider default applies — matching single-model agent behavior. Presets
may still pin explicit values.


## agent.moa_trace

### 模块文档

Full MoA turn trace persistence (opt-in via config ``moa.save_traces``).

When enabled, every Mixture-of-Agents turn that actually runs the reference
fan-out (a cache MISS in ``MoAChatCompletions.create``) appends one JSON line
to ``<hermes_home>/moa-traces/<session_id>.jsonl``. The record is the TRUE
FULL turn — the exact messages array each reference model received (system
prompt + advisory view, not the truncated display preview), each reference's
full output, and the exact messages array the aggregator received (including
the injected reference-context guidance block) plus its output when available
— so a run can be audited end-to-end offline: what every model saw, what every
model said, and what it cost.

This is a side-channel trace. It is NOT the conversation ``messages`` table and
never enters message history or replay — MoA references are advisory side-calls
with their own system prompt, not conversation turns, so persisting them as
message rows would corrupt role alternation / replay. Traces live in their own
files, keyed by session id, and are safe to delete.

Cost model note: gated OFF by default. When off, the only overhead is the
``_traces_enabled()`` config read (cheap) — no file I/O, no serialization.

### 顶层函数

#### def `save_moa_turn(session_id: Optional[str], preset_name: str, reference_outputs: list[tuple[str, str, Any]], aggregator_label: str, aggregator_model: Optional[str], aggregator_provider: Optional[str], aggregator_temperature: Any, aggregator_input_messages: Any, aggregator_output: Optional[str], aggregator_streamed: bool) -> None`

Append one full MoA turn record to the session's trace JSONL, if enabled.

Best-effort: any failure is logged at debug and swallowed — tracing must
never break a live turn. Called once per turn on a reference cache MISS.

``aggregator_output`` is the aggregator's synthesized text. On the
non-streaming path (eval / quiet-mode / subagents) it was captured inline
at call time. On the streaming path it is captured after the fact from the
caller's resolved assistant text (``aggregator_output_fallback`` in
``consume_and_save_trace``) so the trace is self-contained either way; if
that resolved text was unavailable, it falls back to None and the record
points at the session store via ``output_location``.


## agent.model_metadata

### 模块文档

Model metadata, context lengths, and token estimation utilities.

Pure utility functions with no AIAgent dependency. Used by ContextCompressor
and run_agent.py for pre-flight context checks.

### 顶层函数

#### def `grok_supports_reasoning_effort(model: str) -> bool`

Return True when an xAI Grok model accepts ``reasoning.effort``.

Allowlist by substring (matches both bare ``grok-3-mini`` and
aggregator-prefixed ``x-ai/grok-3-mini``). Conservative by design:
if a future Grok model isn't listed, we send no effort dial rather
than 400.

#### def `is_local_endpoint(base_url: str) -> bool`

Return True if base_url points to a local machine.

Recognises loopback (``localhost``, ``127.0.0.0/8``, ``::1``),
container-internal DNS names (``host.docker.internal`` et al.),
RFC-1918 private ranges (``10/8``, ``172.16/12``, ``192.168/16``),
link-local, and Tailscale CGNAT (``100.64.0.0/10``). Tailscale CGNAT
is included so remote-but-trusted Ollama boxes reached over a
Tailscale mesh get the same timeout auto-bumps as localhost Ollama.

#### def `detect_local_server_type(base_url: str, api_key: str = '') -> Optional[str]`

Detect which local server is running at base_url by probing known endpoints.

Returns one of: "ollama", "lm-studio", "vllm", "llamacpp", or None.

The result is cached for the lifetime of the process so that repeated
calls (e.g. every 5-minute metadata refresh) never re-run the waterfall
and never spray 404s at endpoints the server does not expose.

#### def `fetch_model_metadata(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]`

Fetch model metadata from OpenRouter (cached for 1 hour).

#### def `fetch_endpoint_model_metadata(base_url: str, api_key: str = '', force_refresh: bool = False) -> Dict[str, Dict[str, Any]]`

Fetch model metadata from an OpenAI-compatible ``/models`` endpoint.

This is used for explicit custom endpoints where hardcoded global model-name
defaults are unreliable. Results are cached in memory per base URL.

#### def `save_context_length(model: str, base_url: str, length: int) -> None`

Persist a discovered context length for a model+provider combo.

Cache key is ``model@base_url`` so the same model name served from
different providers can have different limits.

#### def `get_cached_context_length(model: str, base_url: str) -> Optional[int]`

Look up a previously discovered context length for model+provider.

#### def `get_next_probe_tier(current_length: int) -> Optional[int]`

Return the next lower probe tier, or None if already at minimum.

#### def `parse_context_limit_from_error(error_msg: str) -> Optional[int]`

Try to extract the actual context limit from an API error message.

Many providers include the limit in their error text, e.g.:
  - "maximum context length is 32768 tokens"
  - "context_length_exceeded: 131072"
  - "Maximum context size 32768 exceeded"
  - "model's max context length is 65536"

#### def `get_context_length_from_provider_error(error_msg: str, current_context_length: int) -> Optional[int]`

Return a provider-reported lower context limit, if one is present.

Context-overflow recovery must not invent a new model window size.  Some
providers only say that the input exceeds the context window without
reporting the actual maximum.  In that case callers should keep the
configured context length and try compression only, rather than stepping
down through guessed probe tiers (1M → 256K → 128K → ...).

#### def `parse_available_output_tokens_from_error(error_msg: str) -> Optional[int]`

Detect an "output cap too large" error and return how many output tokens are available.

Background — two distinct context errors exist:
  1. "Prompt too long"  — the INPUT itself exceeds the context window.
       Fix: compress history, and only reduce context_length if the
       provider explicitly reports the actual lower limit.
  2. "max_tokens too large" — input is fine, but input + requested_output > window.
       Fix: reduce max_tokens (the output cap) for this call.
       Do NOT touch context_length — the window hasn't shrunk.

Anthropic's API returns errors like:
  "max_tokens: 32768 > context_window: 200000 - input_tokens: 190000 = available_tokens: 10000"

Returns the number of output tokens that would fit (e.g. 10000 above), or None if
the error does not look like a max_tokens-too-large error.

#### def `is_output_cap_error(error_msg: str) -> bool`

Return True if a 400 is about the OUTPUT cap (max_tokens) being too large.

This is the broader sibling of :func:`parse_available_output_tokens_from_error`:
that function only returns a number when it can extract the available output
budget from a *known* provider phrasing.  This one answers the cheaper
yes/no question — "is this an output-cap error at all?" — across providers
whose exact wording we may not yet parse a number from.

Why this matters: an output-cap 400 is deterministic (every retry with the
same ``max_tokens`` gets the identical rejection).  If such an error is
misclassified as a context-overflow it gets routed into the compression
loop, the compressor re-issues the call with the same oversized
``max_tokens``, the provider rejects it identically, and the session
death-loops until "cannot compress further" (issue #55546, DashScope/Qwen:
"Range of max_tokens should be [1, 65536]").  Compression cannot help an
output-cap error — the input already fits.

The signal: the error talks about ``max_tokens`` (or its aliases) as a
cap/range/limit, and does NOT talk about the INPUT/prompt/context window
being too long.  When both are present we defer to the context-overflow
path (a real input overflow can also mention max_tokens).

#### def `query_ollama_num_ctx(model: str, base_url: str, api_key: str = '') -> Optional[int]`

Query an Ollama server for the model's context length.

Returns the model's maximum context from GGUF metadata via ``/api/show``,
or the explicit ``num_ctx`` from the Modelfile if set.  Returns None if
the server is unreachable or not Ollama.

This is the value that should be passed as ``num_ctx`` in Ollama chat
requests to override the default 2048.

#### def `query_ollama_supports_vision(model: str, base_url: str, api_key: str = '') -> Optional[bool]`

Return True/False when Ollama ``/api/show`` reports vision support.

Uses the ``capabilities`` field on Ollama 0.6.0+ and falls back to
``model_info.*.vision.block_count`` on older servers. Returns None when
the server is unreachable, not Ollama, or the model is unknown.

#### def `get_model_context_length(model: str, base_url: str = '', api_key: str = '', config_context_length: int | None = None, provider: str = '', custom_providers: list | None = None) -> int`

Get the context length for a model.

Resolution order:
0. Explicit config override (model.context_length or custom_providers per-model)
0c. Endpoint-scoped metadata for models validated on one multiplexed endpoint
1. Persistent cache (previously discovered via probing).  Nous URLs
   bypass the cache here so step 5b can always reconcile against
   the authoritative portal /v1/models response.
1b. AWS Bedrock static table (must precede custom-endpoint probe)
2. Active endpoint metadata (/models for explicit custom endpoints)
3. Local server query (for local endpoints)
4. Anthropic /v1/models API (API-key users only, not OAuth)
5. Provider-aware lookups (before generic OpenRouter cache):
   a. Copilot live /models API
   b. Nous: live /v1/models probe first (authoritative), then OR
      cache fallback with suffix/version normalisation.  Only
      portal-derived values are persisted to disk.
   c. Codex OAuth /models probe
   d. GMI /models endpoint
   e. Ollama native /api/show probe (any base_url, provider-agnostic)
   f. models.dev registry lookup (with :cloud/-cloud suffix fallback)
6. OpenRouter live API metadata (Kimi-family 32k guard)
7. Local server query (before hardcoded defaults for local endpoints)
8. Hardcoded defaults (broad family patterns, longest-key-first)
9. Default fallback (256K)

#### def `get_model_context_length_async(model: str, base_url: str = '', api_key: str = '', config_context_length: int | None = None, provider: str = '', custom_providers: list | None = None) -> int`

Async variant of get_model_context_length.

Offloads the entire synchronous resolution chain (which contains
blocking HTTP calls via ``requests``) to a background thread so it
does not freeze the asyncio event loop and cause Discord heartbeat
timeouts.

Shares all logic with the sync version — no code duplication.

#### def `estimate_tokens_rough(text: str) -> int`

Rough token estimate (~4 chars/token) for pre-flight checks.

Uses ceiling division so short texts (1-3 chars) never estimate as
0 tokens, which would cause the compressor and pre-flight checks to
systematically undercount when many short tool results are present.

#### def `estimate_messages_tokens_rough(messages: List[Dict[str, Any]]) -> int`

Rough token estimate for a message list (pre-flight only).

Image parts (base64 PNG/JPEG) are counted as a flat ~1500 tokens per
image — the Anthropic pricing model — instead of counting raw base64
character length. Without this, a single ~1MB screenshot would be
estimated at ~250K tokens and trigger premature context compression.

#### def `estimate_request_tokens_rough(messages: List[Dict[str, Any]], system_prompt: str = '', tools: Optional[List[Dict[str, Any]]] = None) -> int`

Rough token estimate for a full chat-completions request.

Includes the major payload buckets Hermes sends to providers:
system prompt, conversation messages, and tool schemas.  With 50+
tools enabled, schemas alone can add 20-30K tokens — a significant
blind spot when only counting messages. Image content is counted
at a flat per-image cost (see estimate_messages_tokens_rough).


## agent.models_dev

### 模块文档

Models.dev registry integration — primary database for providers and models.

Fetches from https://models.dev/api.json — a community-maintained database
of 4000+ models across 109+ providers.  Provides:

- **Provider metadata**: name, base URL, env vars, documentation link
- **Model metadata**: context window, max output, cost/M tokens, capabilities
  (reasoning, tools, vision, PDF, audio), modalities, knowledge cutoff,
  open-weights flag, family grouping, deprecation status

Data resolution order (like TypeScript OpenCode):
  1. Bundled snapshot (ships with the package — offline-first)
  2. Disk cache (~/.hermes/models_dev_cache.json)
  3. Network fetch (https://models.dev/api.json)
  4. Background refresh every 60 minutes

Other modules should import the dataclasses and query functions from here
rather than parsing the raw JSON themselves.

### class ModelInfo

> 继承: `object` ｜ 方法数: 6（公开 6）

Full metadata for a single model from models.dev.

#### def `has_cost_data(self) -> bool`

#### def `supports_vision(self) -> bool`

#### def `supports_pdf(self) -> bool`

#### def `supports_audio_input(self) -> bool`

#### def `format_cost(self) -> str`

Human-readable cost string, e.g. '$3.00/M in, $15.00/M out'.

#### def `format_capabilities(self) -> str`

Human-readable capabilities, e.g. 'reasoning, tools, vision, PDF'.


### class ProviderInfo

> 继承: `object` ｜ 方法数: 0（公开 0）

Full metadata for a provider from models.dev.


### class ModelCapabilities

> 继承: `object` ｜ 方法数: 0（公开 0）

Structured capability metadata for a model from models.dev.


### 顶层函数

#### def `fetch_models_dev(force_refresh: bool = False) -> Dict[str, Any]`

Fetch models.dev registry. Cache hierarchy: in-mem → disk → network.

Returns the full registry dict keyed by provider ID, or empty dict on failure.

Cache hierarchy (when ``force_refresh=False``):
  1. In-memory cache, populated and < TTL old → return immediately.
  2. **Disk cache file < TTL old by mtime → load, populate in-mem, return.**
     No network call. Saves ~500 ms per cold-start agent construction;
     ``models.dev`` only changes when providers add new models, so a
     1 hour staleness window is acceptable (same TTL as in-mem cache).
  3. Network fetch → on success, save to disk + in-mem and return.
  4. Network fails → fall back to ANY available disk cache (even stale)
     with a short 5 min in-mem grace period before retrying network.

When ``force_refresh=True`` (used by ``hermes config refresh``, the
"refresh model catalog" code path), stages 1 and 2 are skipped. The
function always hits the network and only falls back to disk if the
network call fails.

#### def `lookup_models_dev_context(provider: str, model: str) -> Optional[int]`

Look up context_length for a provider+model combo in models.dev.

Returns the context window in tokens, or None if not found.
Handles case-insensitive matching and filters out context=0 entries.

#### def `get_model_capabilities(provider: str, model: str) -> Optional[ModelCapabilities]`

Look up full capability metadata from models.dev cache.

Uses the existing fetch_models_dev() and PROVIDER_TO_MODELS_DEV mapping.
Returns None if model not found.

Extracts from model entry fields:
  - reasoning  (bool)  → supports_reasoning
  - tool_call  (bool)  → supports_tools
  - attachment (bool)  → supports_vision
  - limit.context (int) → context_window
  - limit.output  (int) → max_output_tokens
  - family     (str)   → model_family

#### def `list_provider_models(provider: str) -> List[str]`

Return all model IDs for a provider from models.dev.

Returns an empty list if the provider is unknown or has no data.

#### def `list_agentic_models(provider: str) -> List[str]`

Return model IDs suitable for agentic use from models.dev.

Filters for tool_call=True and excludes noise (TTS, embedding,
dated preview snapshots, live/streaming, image-only models).
Returns an empty list on any failure.

#### def `get_provider_info(provider_id: str) -> Optional[ProviderInfo]`

Get full provider metadata from models.dev.

Accepts either a Hermes provider ID (e.g. "kilocode") or a models.dev
ID (e.g. "kilo").  Returns None if the provider is not in the catalog.

#### def `get_model_info(provider_id: str, model_id: str) -> Optional[ModelInfo]`

Get full model metadata from models.dev.

Accepts Hermes or models.dev provider ID.  Tries exact match then
case-insensitive fallback.  Returns None if not found.


## agent.moonshot_schema

### 模块文档

Helpers for translating OpenAI-style tool schemas to Moonshot's schema subset.

Moonshot (Kimi) accepts a stricter subset of JSON Schema than standard OpenAI
tool calling.  Requests that violate it fail with HTTP 400:

    tools.function.parameters is not a valid moonshot flavored json schema,
    details: <...>

Known rejection modes documented at
https://forum.moonshot.ai/t/tool-calling-specification-violation-on-moonshot-api/102
and MoonshotAI/kimi-cli#1595:

1. Every property schema must carry a ``type``.  Standard JSON Schema allows
   type to be omitted (the value is then unconstrained); Moonshot refuses.
2. When ``anyOf`` is used, ``type`` must be on the ``anyOf`` children, not
   the parent.  Presence of both causes "type should be defined in anyOf
   items instead of the parent schema".
3. Every object schema must carry a ``required`` array, even an empty one.
   Standard JSON Schema allows omitting it; Moonshot 400s with
   "required must be an array".

The ``#/definitions/...`` → ``#/$defs/...`` rewrite for draft-07 refs is
handled separately in ``tools/mcp_tool._normalize_mcp_input_schema`` so it
applies at MCP registration time for all providers.

### 顶层函数

#### def `sanitize_moonshot_tool_parameters(parameters: Any) -> Dict[str, Any]`

Normalize tool parameters to a Moonshot-compatible object schema.

Returns a deep-copied schema with the two flavored-JSON-Schema repairs
applied.  Input is not mutated.

#### def `sanitize_moonshot_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Apply ``sanitize_moonshot_tool_parameters`` to every tool's parameters.

#### def `is_moonshot_model(model: str | None) -> bool`

True for any Kimi / Moonshot model slug, regardless of aggregator prefix.

Matches bare names (``kimi-k2.6``, ``moonshotai/Kimi-K2.6``) and aggregator-
prefixed slugs (``nous/moonshotai/kimi-k2.6``, ``openrouter/moonshotai/...``).
Detection by model name covers Nous / OpenRouter / other aggregators that
route to Moonshot's inference, where the base URL is the aggregator's, not
``api.moonshot.ai``.


## agent.nous_rate_guard

### 模块文档

Cross-session rate limit guard for Nous Portal.

Writes rate limit state to a shared file so all sessions (CLI, gateway,
cron, auxiliary) can check whether Nous Portal is currently rate-limited
before making requests.  Prevents retry amplification when RPH is tapped.

Each 429 from Nous triggers up to 9 API calls per conversation turn
(3 SDK retries x 3 Hermes retries), and every one of those calls counts
against RPH.  By recording the rate limit state on first 429 and checking
it before subsequent attempts, we eliminate the amplification effect.

### 顶层函数

#### def `record_nous_rate_limit(headers: Optional[Mapping[str, str]] = None, error_context: Optional[dict[str, Any]] = None, default_cooldown: float = 300.0) -> None`

Record that Nous Portal is rate-limited.

Parses the reset time from response headers or error context.
Falls back to ``default_cooldown`` (5 minutes) if no reset info
is available.  Writes to a shared file that all sessions can read.

Args:
    headers: HTTP response headers from the 429 error.
    error_context: Structured error context from _extract_api_error_context().
    default_cooldown: Fallback cooldown in seconds when no header data.

#### def `nous_rate_limit_remaining() -> Optional[float]`

Check if Nous Portal is currently rate-limited.

Returns:
    Seconds remaining until reset, or None if not rate-limited.

#### def `clear_nous_rate_limit() -> None`

Clear the rate limit state (e.g., after a successful Nous request).

#### def `format_remaining(seconds: float) -> str`

Format seconds remaining into human-readable duration.

#### def `is_genuine_nous_rate_limit(headers: Optional[Mapping[str, str]] = None, last_known_state: Optional[Any] = None) -> bool`

Decide whether a 429 from Nous Portal is a real account rate limit.

Nous Portal multiplexes multiple upstream providers (DeepSeek, Kimi,
MiMo, Hermes, ...) behind one endpoint.  A 429 can mean either:

  (a) The caller's own RPM / RPH / TPM / TPH bucket on Nous is
      exhausted — a genuine rate limit that will last until the
      bucket resets.
  (b) The upstream provider is out of capacity for a specific model
      — transient, clears in seconds, and has nothing to do with
      the caller's quota on Nous.

Tripping the cross-session breaker on (b) blocks ALL Nous requests
(and all models, since Nous is one provider key) for minutes even
though the caller's account is healthy and a different model would
have worked.  That's the bug users hit when DeepSeek V4 Pro 429s
trigger a breaker that then blocks Kimi 2.6 and MiMo V2.5 Pro.

We tell the two apart by looking at:

  1. The 429 response's own ``x-ratelimit-*`` headers.  Nous emits
     the full suite on every response including 429s.  An exhausted
     bucket (``remaining == 0`` with a reset window >= 60s) is
     proof of (a).
  2. The last-known-good rate-limit state captured by
     ``_capture_rate_limits()`` on the previous successful
     response.  If any bucket there was already near-exhausted with
     a substantial reset window, the current 429 is almost
     certainly (a) continuing from that condition.

If neither signal fires, we treat the 429 as (b): fail the single
request, let the retry loop or model-switch proceed, and do NOT
write the cross-session breaker file.

Returns True when the evidence points at (a).


## agent.onboarding

### 模块文档

Contextual first-touch onboarding hints.

Instead of blocking first-run questionnaires, show a one-time hint the *first*
time a user hits a behavior fork — message-while-running, first long-running
tool, etc.  Each hint is shown once per install (tracked in ``config.yaml`` under
``onboarding.seen.<flag>``) and then never again.

Keep this module tiny and dependency-free so both the CLI and gateway can import
it without pulling in heavy modules.

### 顶层函数

#### def `busy_input_hint_gateway(mode: str) -> str`

Hint shown the first time a user messages while the agent is busy.

``mode`` is the effective busy_input_mode that was just applied, so the
message matches reality ("I just interrupted…" vs "I just queued…").

#### def `busy_input_hint_cli(mode: str) -> str`

CLI version of the busy-input hint (plain text, no markdown).

#### def `tool_progress_hint_gateway() -> str`

#### def `tool_progress_hint_cli() -> str`

#### def `openclaw_residue_hint_cli() -> str`

Banner shown the first time Hermes starts and finds ``~/.openclaw/``.

Points users at ``hermes claw migrate`` (non-destructive port of config,
memory, and skills) first. ``hermes claw cleanup`` is mentioned as the
follow-up step for users who have already migrated and want to archive
the old directory — with a warning that archiving breaks OpenClaw.

#### def `detect_openclaw_residue(home: Optional[Path] = None) -> bool`

Return True if an OpenClaw workspace directory is present in ``$HOME``.

Pure filesystem check — no side effects. ``home`` override exists for tests.

#### def `profile_build_mode(config: Mapping[str, Any]) -> str`

Resolve the onboarding profile-build mode from config.

Returns one of:
  ``"ask"``  — on first contact, OFFER to build a profile (default).
  ``"off"``  — never offer; the first-message note stays a plain intro.

Read from ``config.onboarding.profile_build``. Unknown / missing values
fall back to ``"ask"`` so the default experience offers the flow. Any
network/account lookups inside the flow are separately consented to in
conversation — this setting only governs whether the offer is made.

#### def `profile_build_directive() -> str`

System-note directive appended to the very first message ever.

Instructs the agent to run a short, opt-in, consent-gated profile-build
flow and persist confirmed facts to the user-profile memory store
(``memory`` tool, ``target="user"``). Phrased so the agent ASKS before any
lookup and never silently reads connected accounts — directly addressing
the privacy concern that reading email/accounts unprompted feels invasive.

#### def `is_seen(config: Mapping[str, Any], flag: str) -> bool`

Return True if the user has already been shown this first-touch hint.

#### def `mark_seen(config_path: Path, flag: str) -> bool`

Persist ``onboarding.seen.<flag> = True`` to ``config_path``.

Uses the atomic YAML writer so a concurrent process can't observe a
partially-written file.  Returns True on success, False on any error
(including the config file being absent — onboarding is best-effort).


## agent.oneshot

### 模块文档

Shared one-off LLM requests for non-conversational helpers.

A "one-shot" is a single, stateless model call that runs *outside* any
conversation: it never touches a session's history, never breaks prompt
caching, and returns plain text. UI surfaces use it for small generative
chores — a commit message from a diff, a rename suggestion, a summary —
where spinning up an agent turn would be wrong (it would pollute the thread)
and hand-rolling an LLM call at every call site would be worse.

Two ways to call it:

  * ``run_oneshot(instructions=..., user_input=...)`` — caller supplies the
    full prompt.
  * ``run_oneshot(template="commit_message", variables={...})`` — caller
    names a registered template and passes its variables; the template owns
    the prompt engineering so it stays consistent across CLI/TUI/desktop.

Model selection rides the same auxiliary plumbing as title generation
(:func:`agent.auxiliary_client.call_llm`): pass ``main_runtime`` to inherit
the live session's provider/model, otherwise the configured ``task`` (default
``title_generation``) resolves a cheap/fast backend.

### 顶层函数

#### def `render_template(name: str, variables: Optional[Dict[str, Any]] = None) -> Tuple[str, str]`

Resolve a registered template into (instructions, user_input).

Raises KeyError if the template name is unknown so callers fail loudly
instead of silently sending an empty prompt.

**异常**: `KeyError`

#### def `run_oneshot(instructions: str = '', user_input: str = '', template: Optional[str] = None, variables: Optional[Dict[str, Any]] = None, task: str = 'title_generation', max_tokens: int = 1024, temperature: Optional[float] = 0.3, timeout: float = 60.0, main_runtime: Optional[Dict[str, Any]] = None) -> str`

Run a single stateless LLM request and return its text.

Provide either a registered ``template`` (+ ``variables``) or an explicit
``instructions`` / ``user_input`` pair. Returns the model's text answer,
stripped of surrounding whitespace and any wrapping code fence.

Raises RuntimeError when no LLM provider is configured (surfaced from
:func:`call_llm`) and KeyError for an unknown template name.

**异常**: `ValueError`


## agent.pet.__init__

### 模块文档

Petdex pet engine — shared core for the CLI, TUI, and desktop surfaces.

Petdex (https://github.com/crafter-station/petdex) is a public gallery of
animated sprite "pets" for coding agents.  Each pet is a ``pet.json`` plus a
``spritesheet.{webp,png}`` of 192×208 px cells. Current Codex/petdex sheets use
an 8-column × 9-row atlas; older Hermes/petdex sheets used an 8-row atlas.
Hermes infers the row taxonomy from the sheet and maps agent activity onto
idle/run/review/failed/wave/jump.

This package is the **single source of truth** for the feature so the base
CLI (Python) and TUI (Ink, via ``tui_gateway``) never duplicate the hard
parts:

- :mod:`agent.pet.constants` — frame geometry + the :class:`PetState` enum.
- :mod:`agent.pet.state`     — map agent activity → a :class:`PetState`.
- :mod:`agent.pet.manifest`  — fetch the public petdex manifest.
- :mod:`agent.pet.store`     — install / list / resolve pets on disk
                               (profile-aware via ``get_hermes_home()``).
- :mod:`agent.pet.render`    — decode a spritesheet and encode frames for a
                               terminal (kitty / iTerm2 / sixel graphics
                               protocols, with a Unicode half-block
                               fallback).

Rendering in the Electron desktop is necessarily TypeScript (canvas), but it
reuses the same on-disk store and the same state semantics.

The whole feature is a *display* concern: it adds no model tool, mutates no
system prompt or toolset, and therefore has zero effect on prompt caching.

## agent.pet.constants

### 模块文档

Pet sprite geometry + animation-state taxonomy.

These values are the common petdex/Codex pet geometry. The real ``pet.json``
usually only carries ``id``/``displayName``/``description``/``spritesheetPath``;
row taxonomy is inferred from the atlas shape so Hermes can render both legacy
8-row sheets and current 9-row Codex sheets.

### class PetState

> 继承: `str`、`Enum` ｜ 方法数: 0（公开 0）

Animation state a pet can be shown in.

These are Hermes' activity state names. They are not always identical to the
source atlas row names: Codex-format pets use rows like ``jumping`` /
``running`` while the UI keeps the shorter ``jump`` / ``run`` names.


### 顶层函数

#### def `clamp_scale(scale: float) -> float`

Clamp *scale* to ``[MIN_SCALE, MAX_SCALE]`` (the single validation point).

#### def `cols_for_scale(scale: float) -> int`

Half-block width implied by *scale*, clamped to the legibility floor.

Above the floor it tracks the kitty cell box (``scaled_px // 8``) so the two
renderers converge at larger sizes; below it the floor keeps the sprite
readable rather than letting it devolve into a blob.

#### def `resolve_cols(scale: float, unicode_cols: int = 0) -> int`

Resolve terminal width: explicit *unicode_cols* override, else from *scale*.

#### def `state_aliases_for(state: PetState | str) -> tuple[str, ...]`

Return accepted row-name aliases for *state* (always non-empty).

#### def `state_rows_for_grid(row_count: int | None) -> list[str]`

Return the row taxonomy for a spritesheet with *row_count* rows.

#### def `state_row_index(state: PetState | str, row_count: int | None = None) -> int`

Return the spritesheet row index for *state* (clamped, never raises).


## agent.pet.generate.__init__

### 模块文档

Pet generation — base-draft → hatch pipeline.

Public surface used by the gateway RPCs, the CLI ``hermes pets generate``
command, and tests:

- :func:`generate_base_drafts` / :func:`hatch_pet` — the two-step flow.
- :class:`HatchResult`, :class:`GenerationError`.
- :mod:`atlas` — deterministic frame extraction + atlas composition/validation.

Image generation is delegated to the active reference-capable
:class:`~agent.image_gen_provider.ImageGenProvider` (OpenAI gpt-image-2 or Krea);
atlas assembly is fully deterministic so it's testable without any API calls.

## agent.pet.generate.atlas

### 模块文档

Deterministic spritesheet assembly — generated row strips → Hermes atlas.

Image-generation models are good at *drawing* a row of poses but bad at exact
grid geometry, so the model never owns the atlas layout: it produces one loose
horizontal strip per state, and these deterministic ops slice that strip into
clean, centered, transparent ``192x208`` cells and pack them into the sheet our
renderer reads.

The atlas follows the **petdex/Codex standard**: 8 columns x 9 rows of
``192x208`` cells (``1536x1872``), with the row order + per-row frame counts
from OpenAI's ``hatch-pet`` skill. Our renderer (:mod:`agent.pet.render`) keys
frames as ``rows = states, cols = frames`` via
:data:`agent.pet.constants.CODEX_STATE_ROWS`, and a pet built here is a valid
``petdex submit`` spritesheet. Rows shorter than 8 columns leave the trailing
cells fully transparent.

Note ``running`` is the *working* state (in-place processing), NOT locomotion —
``running-right`` / ``running-left`` are the actual directional walk cycles.

The frame-segmentation, fit-to-cell, and transparency-residue logic is adapted
from OpenAI's ``hatch-pet`` skill (openai/skills, Apache-2.0).

### 顶层函数

#### def `remove_background(image, chroma_key: tuple[int, int, int] | None = None, threshold: float = 90.0)`

Return *image* (RGBA) with its flat background keyed out to transparent.

If the strip already has a transparent background we leave it alone; else we
key out *chroma_key* (or the dominant corner color when not given) via a
**border flood-fill**: only background-coloured pixels *connected to an edge*
are removed. A global color match (the old approach) punched holes in the pet
wherever an interior highlight happened to match the backdrop — e.g. a pug's
light belly against a near-white background — which then showed through as the
window behind. Flood-fill keeps those interior pixels because they aren't
reachable from the border without crossing the (non-background) pet.

#### def `extract_strip_frames(strip, frame_count: int, chroma_key: tuple[int, int, int] | None = None, method: str = 'auto', fit: bool = True) -> list`

Turn one generated row strip into *frame_count* frames.

The background is keyed out, then strict extraction treats the requested
frame count as the source of truth: slice known equal slots, isolate the real
subject in each slot, and require empty padding on X and Y. Empty chroma
gutters are only a lenient salvage fallback.

Each frame is cropped at full cell height so tall ears / halos are never
clipped; detached effects and neighbour slivers are dropped per slot. When a
pose does not have required space around it, ``components`` raises and
``auto`` falls back to best-effort slicing.

*fit* (default) fits+centers each frame into a 192x208 cell — the standalone
contract for callers that don't normalize. Hatching passes ``fit=False`` to
keep raw, coordinate-aligned columns for :func:`normalize_cells`, which lays
one shared scale + baseline across the whole pet (no slide, no size pulse).

**异常**: `ValueError`

#### def `normalize_cells(frames_by_state: dict[str, list], pad: int = _NORMALIZE_PAD) -> dict[str, list]`

Register every frame into a 192x208 cell — the deterministic anti-jitter math.

A per-frame "crop→scale→center" pipeline jitters because a moving limb/cape
shifts the bbox (or even the centroid) and a per-frame scale pulses the size.
The rigorous fix, matching image-registration practice (phase correlation)
and AI-sprite pipelines (perfectpixel-studio / sprite-gen):

1. **Cross-correlate** each frame's column profile against the per-state
   *median* profile to find the integer shift that locks the **body** in
   place — robust to limbs/cape because the body dominates the profile.
2. **Union-crop** through one shared state window, then scale every state by a
   single global factor keyed to its median pose height, so the character is
   the same on-screen size in every row while a jump's lift still fits.

#### def `single_frame(image, fit: bool = True)`

One frame from a standalone image (e.g. the base look).

Used as an idle fallback so a pet always renders even if the idle row
generation failed. *fit* yields a finished 192x208 cell; ``fit=False`` yields
the raw keyed sprite for :func:`normalize_cells` to place with the rest.

#### def `mirror_frames(frames: list) -> list`

Horizontally flip each frame *in place* (RGBA-safe).

Used to derive ``running-left`` from an approved ``running-right`` row. The
flip is per-frame so the leftward loop preserves the rightward loop's frame
order and timing — this is NOT a whole-strip reverse (which would play the
animation backwards), matching the petdex/Codex mirror rule.

#### def `compose_atlas(frames_by_state: dict[str, list])`

Pack per-state frame lists into the Hermes atlas (RGBA, residue-cleared).

Missing/short states leave their trailing cells transparent; extra frames
beyond a state's spec are dropped.

#### def `atlas_to_webp_bytes(atlas) -> bytes`

Encode an atlas image to lossless WebP bytes (the on-disk pet format).

#### def `validate_atlas(atlas) -> dict`

Check geometry, per-cell occupancy, and transparency invariants.

Returns ``{ok, width, height, errors, warnings, filled_states}``. Errors are
blockers (wrong size, empty used cell, opaque/dirty transparency); warnings
are soft (a whole state row blank — generation likely dropped a row).


## agent.pet.generate.imagegen

### 模块文档

Thin image-generation layer for pet sprites.

Wraps the active :class:`~agent.image_gen_provider.ImageGenProvider` with the
two things sprite generation needs that the agent-facing ``image_generate`` tool
doesn't expose: **N variants** (loop) and **reference-image grounding** (so each
animation row stays the same character as the chosen base).

Reference grounding only works on providers that support it — currently OpenAI
``gpt-image-2`` (image edits) and Krea (style references). We resolve to one of
those and surface a clear, actionable error otherwise rather than silently
producing an ungrounded, drifting pet.

### class GenerationError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised on any image-generation failure (no provider, API error, IO).


### class SpriteProvider

> 继承: `object` ｜ 方法数: 0（公开 0）

Resolved provider plus whether it can take reference images.


### 顶层函数

#### def `resolve_provider(require_references: bool = True, prefer: str | None = None) -> SpriteProvider`

Pick the image provider to use for sprite work.

Preference: an explicit *prefer* choice (the desktop pet-gen picker) when it's
reference-capable and configured, then the configured/active provider when
it's reference-capable, else the first available reference-capable provider.
With *require_references* off we fall back to any available provider (used for
prompt-only base drafts).

**异常**: `GenerationError`

#### def `list_sprite_providers() -> list[dict]`

The reference-capable providers available to pick for pet generation.

Returns ``[{name, label, default}]`` for every ref-capable provider the user
actually has credentials for, in preference order, marking the one
:func:`resolve_provider` would choose with no explicit preference. Empty when
none is configured (the picker hides itself). Best-effort: discovery hiccups
yield an empty list.

#### def `generate(prompt: str, n: int = 1, reference_images: list[Path] | None = None, provider: SpriteProvider | None = None, prefix: str = 'pet_gen', aspect_ratio: str = 'square') -> list[Path]`

Generate *n* sprite images and return their local paths.

*reference_images* grounds the output on a base image (required for rows).
*aspect_ratio* picks the canvas: ``"square"`` for single-character base
drafts, ``"landscape"`` for multi-frame row strips (the wider 1536px canvas
gives every frame real horizontal room so winged poses don't have to be
shrunk to avoid touching their neighbors).
We *ask* for a transparent background, but fall back to an opaque generation
(cleaned up downstream by the chroma-key pass) on models that reject the
flag. Raises :class:`GenerationError` if nothing usable comes back.

**异常**: `class`, `GenerationError`


## agent.pet.generate.orchestrate

### 模块文档

Pet generation orchestration — the base-draft → hatch flow.

Two steps, mirroring the UX across every surface:

1. :func:`generate_base_drafts` — a handful of prompt-only "what should this pet
   look like" variants. Cheap; the user picks one (or retries for a fresh set).
2. :func:`hatch_pet` — takes the chosen base and generates one grounded row
   strip per Hermes state, slices each into frames, composes the atlas, validates
   it, and writes the pet into the store.

Splitting it this way bounds cost (4 cheap base calls per round; the ~6 row
calls happen once, on the pet you actually keep) and gives each UI a natural
preview/loading point.

### class HatchResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Outcome of a successful :func:`hatch_pet`.


### 顶层函数

#### def `generate_base_drafts(concept: str, n: int = 4, style: str = 'auto', reference_images: list[Path] | None = None, provider: SpriteProvider | None = None, on_draft: Callable[[int, Path], None] | None = None, is_cancelled: Callable[[], bool] | None = None) -> list[Path]`

Generate *n* candidate base looks for *concept*; returns image paths.

Each draft is hardened to a transparent cutout (see :func:`_harden_transparency`).
Drafts are generated concurrently and *on_draft(index, path)* fires as each
one finishes (not at the end) so callers can stream previews to the UI
instead of leaving it blank until the whole batch is done.

*is_cancelled*, when supplied, is polled cooperatively: a draft that hasn't
started yet is skipped, and once it trips we stop staging/streaming further
drafts and cancel any queued work (already-in-flight provider calls can't be
hard-killed, but their results are dropped).

**异常**: `GenerationError`

#### def `hatch_pet(base_image: str | Path, slug: str, display_name: str = '', description: str = '', concept: str = '', style: str = 'auto', on_progress: ProgressFn | None = None, provider: SpriteProvider | None = None, is_cancelled: Callable[[], bool] | None = None) -> HatchResult`

Turn an approved base image into a full, installed Hermes pet.

Generates a grounded row strip per state, extracts frames, composes +
validates the atlas, and registers it. The idle row falls back to the base
look so the pet always renders. Raises :class:`GenerationError` on failure.

*is_cancelled*, when supplied, is polled cooperatively: rows that haven't
started are skipped, queued rows are cancelled, and once every row is done we
abort (raising :class:`GenerationError`) before composing/saving so a stopped
hatch never writes a half-built pet.

**异常**: `class`, `GenerationError`


## agent.pet.generate.prompts

### 模块文档

Prompt builders for pet generation.

Two prompt shapes: a *base* prompt (prompt-only, produces the canonical look the
user picks between) and per-*state* *row* prompts (grounded on the chosen base,
produce one horizontal strip of N poses). Prompts stay concise and
sprite-production oriented; the identity lock and "one transparent row" framing
matter more than flowery description.

We generate the full petdex/Codex nine-state set (see
:data:`agent.pet.generate.atlas.ROW_SPECS`) so a hatched pet is a valid
``petdex submit`` spritesheet.

### 顶层函数

#### def `style_hint(style: str | None) -> str`

#### def `build_base_prompt(concept: str, style: str | None = 'auto', variation: str = '') -> str`

The base look: a single, clean, centered full-body mascot.

*variation* differentiates one draft from the next (see :data:`BASE_VARIATIONS`).

#### def `build_row_prompt(state: str, frame_count: int, concept: str, style: str | None = 'auto') -> str`

A row strip: *frame_count* poses of the SAME character, left→right.

The attached base image is the identity source of truth; the prompt locks
species, palette, face, and props to it.


## agent.pet.manifest

### 模块文档

Fetch the public petdex manifest.

``https://petdex.dev/api/manifest`` 307-redirects to a JSON document on R2:

    {
      "generatedAt": "...",
      "total": 2926,
      "pets": [
        {"slug": "boba", "displayName": "Boba", "kind": "creature",
         "submittedBy": "railly",
         "spritesheetUrl": "https://assets.petdex.dev/.../spritesheet.webp",
         "petJsonUrl": "https://assets.petdex.dev/.../pet.json",
         "zipUrl": "https://assets.petdex.dev/.../boba.zip"},
        ...
      ]
    }

Read-only and unauthenticated; no credentials involved.

### class ManifestEntry

> 继承: `object` ｜ 方法数: 1（公开 1）

A single pet's row in the manifest.

#### classmethod `from_dict(cls, data: dict) -> ManifestEntry`


### class ManifestError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when the manifest can't be fetched or parsed.


### 顶层函数

#### def `clear_cache() -> None`

Drop the cached manifest (forces the next fetch to hit the network).

#### def `prefetch(timeout: float = _DEFAULT_TIMEOUT) -> None`

Warm the manifest cache in a daemon thread — idempotent, never blocks.

The desktop picker calls this when it loads the (instant) local-only gallery
so the full petdex catalog is usually cached by the time it's requested,
without ever holding up the user's own pets on a network round-trip.

#### def `fetch_manifest(timeout: float = _DEFAULT_TIMEOUT, force: bool = False) -> list[ManifestEntry]`

Return every approved pet from the public manifest.

Cached in-process for ``_MANIFEST_TTL`` seconds (pass ``force=True`` to
bypass). Follows the 307 redirect to R2.  Raises :class:`ManifestError` on
any network/parse failure so callers can surface a clean message.

**异常**: `class`, `ManifestError`

#### def `find_entry(slug: str, timeout: float = _DEFAULT_TIMEOUT) -> ManifestEntry | None`

Return the manifest entry for *slug*, or ``None`` if not listed.


## agent.pet.render

### 模块文档

Decode a pet spritesheet and encode frames for a terminal.

Shared by the base CLI (writes the escape bytes to its own stdout) and the
TUI (``tui_gateway`` ships the encoded bytes to Ink, which writes them) so the
decode + capability-detection + protocol-encoding logic exists exactly once.

Supported output modes, in fidelity order:

- ``kitty``   — the kitty graphics protocol (kitty, Ghostty, WezTerm).
- ``iterm``   — iTerm2 inline images (iTerm2, WezTerm).
- ``sixel``   — DEC sixel (xterm -ti vt340, foot, mlterm, WezTerm, …).
- ``unicode`` — 24-bit half-block downscale; works in any truecolor terminal.

Frame decoding requires Pillow (a core Hermes dependency).  If Pillow or the
spritesheet is unavailable the renderer degrades to ``unicode`` text or an
empty string rather than raising.

### class PetRenderer

> 继承: `object` ｜ 方法数: 8（公开 5）

Holds a pet's spritesheet and yields encoded frames per (state, index).

Construct once per pet, then call :meth:`frame` on an animation timer.
Cheap to call repeatedly — decoded frames are cached.

#### def `__init__(spritesheet: str | Path, mode: str = 'unicode', scale: float = DEFAULT_SCALE, unicode_cols: int = 20, frame_w: int = FRAME_W, frame_h: int = FRAME_H, frames_per_state: int = FRAMES_PER_STATE) -> None`

#### property `available(self) -> bool`

#### def `frame_count(self, state: PetState | str) -> int`

#### def `cells(self, state: PetState | str, index: int, cols: int | None = None) -> list[list[Cell]]`

Return one frame as a half-block cell grid (framework-neutral).

Used by the TUI, which renders the grid with native Ink color props
instead of raw ANSI.  Returns ``[]`` when no frame is available.

#### def `kitty_payload(self, state: PetState | str, image_id: int) -> dict | None`

Build the kitty Unicode-placeholder payload for one state.

Returns ``{cols, rows, placeholder, frames}`` where ``frames`` is a
list of transmit escapes (one per animation frame, all reusing
``image_id``) and ``placeholder`` is the static text grid Ink paints.
Placement geometry is derived from the scaled frame pixels (via
:meth:`_cell_box`), not ``unicode_cols`` — kitty upscales to fill
``c``×``r`` cells. ``None`` when no frame is available.

#### def `frame(self, state: PetState | str, index: int) -> str`

Return the encoded escape string for one frame, or ``""``.

``index`` is taken modulo the available frame count so callers can pass
a free-running counter.


### 顶层函数

#### def `detect_terminal_graphics() -> str`

Best-effort detection of the richest graphics protocol available.

Env-based (non-blocking — we never issue a DA1/terminal query that could
hang a pipe).  Returns one of ``kitty`` / ``iterm`` / ``sixel`` /
``unicode``.  Conservative: unknown terminals get ``unicode``, which works
anywhere with truecolor.

#### def `resolve_mode(configured: str | None, stream = None) -> str`

Resolve the effective render mode from config + the environment.

``configured`` is ``display.pet.render_mode`` (``auto`` → detect).  Returns
``off`` when not attached to a TTY (no point emitting graphics into a pipe
or logfile).

#### def `state_frame_counts(sheet_path: str | Path, frame_w: int = FRAME_W, frame_h: int = FRAME_H, frames_per_state: int = FRAMES_PER_STATE) -> dict[str, int]`

Map each driven :class:`PetState` → its real (padding-trimmed) frame count.

The single source of truth for "how many frames does this state actually
have?".  The CLI/TUI consume the trimmed frame lists directly; the gateway
ships this map to the desktop canvas, which steps its own loop.

#### def `kitty_image_id(slug: str) -> int`

Stable per-pet image id in ``[1, 0x7FFF]``.

The id is encoded in the placeholder's 24-bit foreground color, so it must
be non-zero and fit comfortably under ``0xFFFFFF``. A small CRC keeps it
deterministic per slug (so re-renders reuse the same terminal-side image)
while making collisions between two different pets unlikely.

#### def `kitty_color_hex(image_id: int) -> str`

Hex foreground color (``#rrggbb``) that encodes *image_id* for kitty.

#### def `kitty_placeholder_rows(cols: int, rows: int) -> list[str]`

Build the placeholder text grid for an *rows*×*cols* image.

Each line is one row of the grid: the first cell carries the row diacritic
(column defaults to 0), and the remaining ``cols-1`` bare placeholders let
the terminal auto-increment the column. The foreground color (the image id)
is applied by the caller / Ink, not embedded here.

#### def `build_renderer(spritesheet: str | Path, configured_mode: str | None = None, scale: float = DEFAULT_SCALE, unicode_cols: int = 20, stream = None) -> PetRenderer`

Convenience factory: resolve the mode from config+env, then construct.


## agent.pet.state

### 模块文档

Map agent activity → a :class:`PetState`.

This is the one place the "what is the agent doing right now?" → "which
animation row?" decision lives.  Each surface feeds it the signals it already
tracks:

- CLI    — ``KawaiiSpinner`` waiting/thinking state + tool outcomes.
- TUI    — gateway ``tool.start/complete`` + ``message.delta/complete`` events.
- Desktop — the ``$busy``/``$awaitingResponse``/tool-event nanostores
            (re-implemented in TS, but mirroring this priority order).

Keeping the priority order here (and documenting it) lets the TypeScript
mirror stay faithful without a second design.

### 顶层函数

#### def `todos_all_done(todos: Iterable[Any] | None) -> bool`

True iff there's ≥1 todo and every one is completed/cancelled.

The "celebrate" beat (``JUMP``) fires when a plan finishes; this mirrors
the TUI's ``isTodoDone`` so the trigger is defined once across surfaces.
Accepts dicts (``{"status": ...}``) or objects with a ``status`` attr.

#### def `derive_pet_state(busy: bool = False, awaiting_input: bool = False, error: bool = False, celebrate: bool = False, just_completed: bool = False, tool_running: bool = False, reasoning: bool = False) -> PetState`

Resolve the animation state from coarse activity signals.

Priority (highest first) — only one row can show at a time, so the most
salient signal wins:

1. ``error``          → ``FAILED``  (a tool/turn just failed)
2. ``celebrate``      → ``JUMP``    (explicit success beat, e.g. todos done)
3. ``just_completed`` → ``WAVE``    (turn finished cleanly / greeting)
4. ``awaiting_input`` → ``WAITING`` (blocked on the user — a clarify/approval
   prompt is open; this outranks the in-flight signals below because the turn
   is paused on *you*, even though a tool is technically mid-call)
5. ``tool_running``   → ``RUN``     (a tool is executing)
6. ``reasoning``      → ``REVIEW``  (model is thinking / reading)
7. ``busy``           → ``RUN``     (turn in flight, unspecified work)
8. otherwise          → ``IDLE``


## agent.pet.store

### 模块文档

On-disk pet store — install / list / resolve pets.

Pets live under ``get_hermes_home()/pets/<slug>/`` so every profile gets its
own set (we deliberately do **not** reuse petdex's ``~/.codex/pets`` default —
that's owned by the petdex npm CLI and isn't profile-aware).  Each installed
pet directory holds:

    pets/<slug>/
        pet.json            # {id, displayName, description, spritesheetPath}
        spritesheet.webp    # (or .png)

The active pet is resolved from the caller-supplied ``display.pet.slug`` config
value (falling back to the first installed pet), so this module stays free of
the config loader.

### class PetStoreError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised on install/IO failures.


### class InstalledPet

> 继承: `object` ｜ 方法数: 2（公开 2）

A pet present on disk.

#### property `exists(self) -> bool`

#### property `generated(self) -> bool`


### 顶层函数

#### def `pets_dir() -> Path`

Return the profile-scoped pets directory (created on demand).

#### def `load_pet(slug: str) -> InstalledPet | None`

Return the :class:`InstalledPet` for *slug*, or ``None`` if absent.

#### def `installed_pets() -> list[InstalledPet]`

Return every installed pet (dirs containing a usable spritesheet).

#### def `resolve_active_pet(configured_slug: str | None = None) -> InstalledPet | None`

Resolve which pet to display.

Precedence: the configured slug (``display.pet.slug``) if it's installed,
otherwise the first installed pet alphabetically, otherwise ``None``.

#### def `install_pet(slug: str, force: bool = False, timeout: float = _DOWNLOAD_TIMEOUT) -> InstalledPet`

Download *slug* from the manifest into the pets directory.

Idempotent: a fully-installed pet is returned as-is unless *force*.  Raises
:class:`PetStoreError` / :class:`~agent.pet.manifest.ManifestError` on
failure.

**异常**: `class`, `PetStoreError`

#### def `slugify(name: str) -> str`

Lowercase, hyphenate, and strip a display name into a filesystem slug.

#### def `unique_slug(name: str) -> str`

A :func:`slugify` result that doesn't collide with an existing pet dir.

#### def `register_local_pet(spritesheet, slug: str, display_name: str = '', description: str = '') -> InstalledPet`

Write a locally-generated pet into the store and return it.

*spritesheet* may be a PIL image, raw WebP/PNG bytes, or a path. The pet
appears in :func:`installed_pets` immediately, and because :func:`install_pet`
returns an already-on-disk pet before consulting the manifest, it can be
adopted (``pet.select`` / ``/pet <slug>``) without a manifest entry.

**异常**: `PetStoreError`

#### def `export_pet(slug: str) -> tuple[str, bytes]`

Zip an installed pet's folder (pet.json + spritesheet) → (filename, bytes).

Dotfiles (cached thumbs, backups) are skipped so the archive is a clean,
re-importable pet package. Raises :class:`PetStoreError` if not installed.

**异常**: `class`, `PetStoreError`

#### def `thumbnail_png(slug: str, source_url: str = '', timeout: float = 30.0) -> bytes | None`

Return a small idle-frame PNG for *slug*, cached on disk.

Crops the top-left (idle, frame 0) cell of the spritesheet and downsamples
it to a thumbnail. Source preference: an installed spritesheet on disk, else
*source_url* — but only when it points at petdex (so the gateway never
fetches an arbitrary client-supplied URL). Returns ``None`` when there's no
usable source or Pillow/network fails; callers render a placeholder.

Doing this server-side sidesteps the renderer's CSP / R2 hotlink limits that
break a direct ``<img src=cdn>`` and lets the result ride the authenticated
gateway as a same-origin data URL.

#### def `remove_pet(slug: str) -> bool`

Delete an installed pet directory.  Returns True if anything was removed.

#### def `rename_pet(slug: str, display_name: str) -> str | None`

Rename a pet's ``displayName`` AND realign its slug/dir to match.

Generated pets are hatched under a provisional, prompt-derived slug; when
the user names the pet on the reveal screen we make that name the real
identity so lists/subtitles show what they typed, not the prompt. The dir is
renamed to ``slugify(name)`` (and the cached thumbnail moved alongside it)
whenever that yields a free, different slug — otherwise the slug is left as
is. Returns the resulting slug on success, or ``None`` on failure.


## agent.plugin_llm

### 模块文档

Plugin LLM facade — host-owned LLM access for trusted plugins.
==============================================================

Plugins built on Hermes Agent often need to make their own LLM calls
out-of-band — a hook that rewrites a tool error before the user sees
it, a gateway adapter that translates inbound text, a slash command
that summarises a paste, a scheduled job that scores yesterday's
activity into a single line on a status board.

Today the only stable plugin surfaces extend an existing Hermes
subsystem: ``register_tool``, ``register_platform``,
``register_memory_provider``, etc. None of those help when the
plugin's job is to make its own model call. This module is the
supported lane for that case.

The plugin gets ``ctx.llm`` exposed on its
:class:`~hermes_cli.plugins.PluginContext`:

* ``complete(messages, ...)`` — chat completion against the user's
  active model + auth.
* ``complete_structured(instructions=..., input=[...], json_schema=...)``
  — bounded structured inference with optional image inputs, JSON
  schema validation, and parsed JSON output.
* async siblings ``acomplete()`` / ``acomplete_structured()`` for
  plugins running on asyncio loops (gateway adapters, hooks).

Provider/model/agent_id/profile are explicit keyword arguments — no
embedded slugs, no shorthands. This mirrors Hermes' main config
shape (``model.provider`` + ``model.model``) so plugin authors who
already understand the host config don't have to learn anything new.

The host owns provider routing, auth resolution, timeouts, and
fallback. The plugin never sees raw OAuth tokens or API keys. All
override knobs (``provider=``, ``model=``, ``agent_id=``,
``profile=``) are gated behind explicit per-plugin trust flags in
``config.yaml``::

    plugins:
      entries:
        my-plugin:
          llm:
            allow_provider_override: true
            allow_model_override: true
            allowed_providers: [openrouter, anthropic]   # optional
            allowed_models:    [openai/gpt-4o-mini]       # optional
            allow_agent_id_override: false
            allow_profile_override: false

Untrusted plugins still get the default surface — they just can't
steer provider, model, agent, or auth-profile selection. The trust
gate is fail-closed: a missing config block means "no overrides,"
not "anything goes."

Backed by :func:`agent.auxiliary_client.call_llm`, which already
handles every provider, fallback chain, and per-task override Hermes
supports.

### class PluginLlmTextInput

> 继承: `object` ｜ 方法数: 0（公开 0）

Text block in a structured input list.


### class PluginLlmImageInput

> 继承: `object` ｜ 方法数: 0（公开 0）

Image block in a structured input list.

Either ``data`` (raw bytes) or ``url`` (http(s) or data: URL) must be
provided. ``mime_type`` defaults to ``image/png`` when ``data`` is
used and is required for non-PNG bytes to render correctly across
providers.


### class PluginLlmUsage

> 继承: `object` ｜ 方法数: 0（公开 0）

Token + cost usage for a completion. All fields optional — providers
differ on what they return. ``cost_usd`` is the host's best estimate.


### class PluginLlmCompleteResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of :meth:`PluginLlm.complete`.


### class PluginLlmStructuredResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of :meth:`PluginLlm.complete_structured`.

``parsed`` is set only when ``json_mode=True`` or ``json_schema`` is
provided AND the response was valid JSON. ``content_type`` is
``"json"`` in that case, ``"text"`` otherwise (e.g. the model
refused or the response wasn't requested as JSON).


### class PluginLlmTrustError

> 继承: `PermissionError` ｜ 方法数: 0（公开 0）

Raised when a plugin attempts an LLM override without trust.


### class PluginLlm

> 继承: `object` ｜ 方法数: 8（公开 4）

Host-owned LLM access for one trusted plugin.

Instances are constructed by :class:`hermes_cli.plugins.PluginContext`
and exposed as ``ctx.llm``. Plugins should not instantiate this
directly — the constructor binds plugin identity for trust-gate
enforcement.

#### def `__init__(plugin_id: str, policy_loader: Optional[Callable[[str], _TrustPolicy]] = None, sync_caller: Optional[Callable[..., Any]] = None, async_caller: Optional[Callable[..., Awaitable[Any]]] = None) -> None`

#### def `complete(self, messages: List[Dict[str, Any]], provider: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, timeout: Optional[float] = None, agent_id: Optional[str] = None, profile: Optional[str] = None, purpose: Optional[str] = None) -> PluginLlmCompleteResult`

Run a host-owned chat completion against the user's active model.

``messages`` is the standard OpenAI shape. ``provider``,
``model``, ``agent_id``, and ``profile`` follow the same
explicit shape as the host's main config (``model.provider``
+ ``model.model``). Each is independently gated by
``plugins.entries.<id>.llm.allow_*_override`` (see module
docstring).

#### def `complete_structured(self, instructions: str, input: Sequence[PluginLlmInput], json_schema: Optional[Any] = None, json_mode: bool = False, schema_name: Optional[str] = None, system_prompt: Optional[str] = None, provider: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, timeout: Optional[float] = None, agent_id: Optional[str] = None, profile: Optional[str] = None, purpose: Optional[str] = None) -> PluginLlmStructuredResult`

Run a bounded host-owned structured completion.

``input`` accepts text and image blocks (see
:class:`PluginLlmTextInput` / :class:`PluginLlmImageInput`). When
``json_mode=True`` or ``json_schema`` is provided, the response
is parsed and (if a schema is given) validated; the parsed value
is returned in :attr:`PluginLlmStructuredResult.parsed`.

Validation requires the optional ``jsonschema`` package. When it
isn't installed, JSON mode still works but schema enforcement is
skipped with a debug log.

**异常**: `ValueError`

#### async def `acomplete(self, messages: List[Dict[str, Any]], provider: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, timeout: Optional[float] = None, agent_id: Optional[str] = None, profile: Optional[str] = None, purpose: Optional[str] = None) -> PluginLlmCompleteResult`

Async sibling of :meth:`complete`.

#### async def `acomplete_structured(self, instructions: str, input: Sequence[PluginLlmInput], json_schema: Optional[Any] = None, json_mode: bool = False, schema_name: Optional[str] = None, system_prompt: Optional[str] = None, provider: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, timeout: Optional[float] = None, agent_id: Optional[str] = None, profile: Optional[str] = None, purpose: Optional[str] = None) -> PluginLlmStructuredResult`

Async sibling of :meth:`complete_structured`.

**异常**: `ValueError`


### 顶层函数

#### def `make_plugin_llm_for_test(plugin_id: str, policy: _TrustPolicy, sync_caller: Optional[Callable[..., Any]] = None, async_caller: Optional[Callable[..., Awaitable[Any]]] = None) -> PluginLlm`

Construct a :class:`PluginLlm` with an injected policy and caller.

Used by unit tests that don't want to round-trip through config.yaml
or hit a real provider. Not part of the public plugin API.


## agent.portal_tags

### 模块文档

Centralized Nous Portal request tags.

Every Hermes request that hits the Nous Portal — main agent loop, auxiliary
client (compression / titles / vision / web_extract / session_search / etc.),
and any future code path — must carry the same product-attribution tags so
Nous can attribute usage to Hermes Agent and bucket it by client release.

Tag shape (sent in OpenAI-compatible ``extra_body['tags']``):

    [
        "product=hermes-agent",
        "client=hermes-client-v<__version__>",
    ]

The version is sourced live from ``hermes_cli.__version__`` so it auto-aligns
to whatever release is installed; the release script
(``scripts/release.py``) regex-bumps that single string, and every Portal
request picks up the new tag on the next process start.

Why one helper instead of inlining the literal at each site:
* Four call sites (main loop profile, aux client, run_agent compression
  fallback, web_tools fallback) used to drift apart — see PR #24194 which
  only got the aux site, leaving the main loop sending a different tag set.
* Tests should assert the same tag list everywhere; centralizing makes that
  assertion a one-liner against this module.

Do NOT pre-compute these as module-level constants in the consumers. The
version can change at runtime (editable installs, hot-reload tooling), and
``hermes_cli.__version__`` is the canonical source of truth.

### 顶层函数

#### def `set_conversation_context(conversation_id: Optional[str])`

Publish the active conversation id for ambient Portal tagging.

Called by the agent loop at turn entry with the conversation's stable
id (the session-lineage ROOT id, so the tag survives context-compression
session rotation). Pass ``None`` to clear. Returns the ContextVar token
so callers can ``reset_conversation_context(token)`` on turn exit.

#### def `reset_conversation_context(token) -> None`

Restore the previous conversation context (pair with ``set_...``).

#### def `get_conversation_context() -> Optional[str]`

Return the ambient conversation id, or ``None`` when unset.

#### def `hermes_client_tag() -> str`

Return the ``client=...`` tag for Nous Portal requests.

Format: ``client=hermes-client-v<MAJOR>.<MINOR>.<PATCH>``.

#### def `conversation_tag(session_id: str) -> str`

Return the ``conversation=...`` tag for a Hermes session/conversation.

Format: ``conversation=<session_id>``. ``session_id`` is the canonical
Hermes conversation identifier (``AIAgent.session_id``) — the same value
used for ``~/.hermes/sessions/`` storage, session logs, and lineage.

Unlike the product/client tags this is high-cardinality (one value per
conversation), so it is only appended when a session id is actually
available — never as part of the always-on base tag set.

#### def `nous_portal_tags(session_id: str | None = None) -> List[str]`

Return the canonical list of Nous Portal product tags.

Always returns a fresh list so callers can mutate it freely
(e.g. ``merged_extra.setdefault("tags", []).extend(nous_portal_tags())``).

When ``session_id`` is provided, a ``conversation=<session_id>`` tag is
appended so Portal usage can be attributed to a specific Hermes
conversation. When it is omitted, the ambient conversation context
(``set_conversation_context``, published by the agent loop at turn
entry) is used instead — this is how auxiliary calls (compression,
titles, vision, MoA slots, ...) inherit the conversation tag without
per-call-site plumbing. Callers outside any conversation (e.g. the
auxiliary client's import-time base tags) get the canonical two-tag set.


## agent.process_bootstrap

### 模块文档

Process-level bootstrap helpers for ``run_agent``.

Three concerns, all tied to ``AIAgent`` boot-time / runtime IO setup:

1. **Lazy OpenAI SDK import** — ``_load_openai_cls`` + ``_OpenAIProxy``
   defer the 240ms-ish ``from openai import OpenAI`` cost until first use,
   while preserving ``isinstance(client, OpenAI)`` checks and
   ``patch("run_agent.OpenAI", ...)`` test patterns.

2. **Crash-resistant stdio** — ``_SafeWriter`` wraps stdout/stderr so
   ``OSError: Input/output error`` from broken pipes (systemd, Docker,
   thread teardown races) cannot crash the agent.  ``_install_safe_stdio``
   applies the wrapper.

3. **HTTP proxy resolution** — ``_get_proxy_from_env`` reads
   ``HTTPS_PROXY`` / ``HTTP_PROXY`` / ``ALL_PROXY``;
   ``_get_proxy_for_base_url`` respects ``NO_PROXY`` for the given base URL.

``run_agent`` re-exports every name so existing
``from run_agent import _get_proxy_from_env`` imports keep working
unchanged.

### 顶层函数

#### def `build_keepalive_http_client(base_url: str = '', async_mode: bool = False, verify: Any = True) -> Optional[Any]`

Build an httpx client for OpenAI SDK calls with env-only proxy policy.

Uses explicit ``HTTPS_PROXY`` / ``NO_PROXY`` env vars via
``_get_proxy_for_base_url``. Plain no-proxy mounts disable httpx's default
``trust_env`` proxy path, so macOS system proxy settings from
``urllib.request.getproxies()`` (which omit the ExceptionsList) are not
applied. Mirrors ``AIAgent._build_keepalive_http_client``.

Connection lifecycle is managed at the HTTP pool layer
(``keepalive_expiry=20.0`` reaps idle connections before reverse proxies'
typical 30-60 s timeouts) instead of the former custom
``socket_options`` transport, which broke streaming behind reverse
proxies (#54049, #12952) and stalled TLS handshakes by stripping
``TCP_NODELAY``.

``verify`` is forwarded to httpx so auxiliary-client calls (compression,
vision, web_extract, title generation, etc.) honor the same per-provider
``ssl_ca_cert`` / ``ssl_verify`` and ``HERMES_CA_BUNDLE`` settings the main
client uses. It is passed on the client AND on the plain no-proxy mounts
(a mounted transport owns the SSL context for its scheme).


## agent.prompt_builder

### 模块文档

System prompt assembly -- identity, platform hints, skills index, context files.

All functions are stateless. AIAgent._build_system_prompt() calls these to
assemble pieces, then combines them with memory and ephemeral prompts.

### 顶层函数

#### def `computer_use_guidance(platform_name: Optional[str] = None) -> str`

Return platform-aware computer-use guidance for the system prompt.

``platform_name`` is an ``sys.platform``-style string ("darwin",
"win32", "linux"); defaults to the running host's platform.

#### def `format_steer_marker(steer_text: str) -> str`

Wrap a mid-turn steer for appending to a tool result (see module note).

#### def `build_environment_hints() -> str`

Return environment-specific guidance for the system prompt.

Always emits a factual block describing the execution environment:
- For **local** terminal backends: the host OS, user home, current
  working directory (plus a Windows-only note about hostname != user
  and a Windows-only note that `terminal` shells out to bash, not
  PowerShell).
- For **remote / sandbox** terminal backends (docker, singularity,
  modal, daytona, ssh): host info is **suppressed**
  because the agent's tools can't touch the host — only the backend
  matters. A live probe inside the backend reports its OS, user, $HOME,
  and cwd. Falls back to a static summary if the probe fails.

The WSL environment hint is appended unchanged when running under WSL.

#### def `drain_truncation_warnings() -> list`

Return and clear any truncation warnings accumulated in this context.

#### def `clear_skills_system_prompt_cache(clear_snapshot: bool = False) -> None`

Drop the in-process skills prompt cache (and optionally the disk snapshot).

#### def `build_skills_system_prompt(available_tools: set[str] | None = None, available_toolsets: set[str] | None = None, compact_categories: frozenset[str] | None = None) -> str`

Build a compact skill index for the system prompt.

Two-layer cache:
  1. In-process LRU dict keyed by (skills_dir, tools, toolsets, hidden)
  2. Disk snapshot (``.skills_prompt_snapshot.json``) validated by
     mtime/size manifest — survives process restarts

Falls back to a full filesystem scan when both layers miss.

External skill directories (``skills.external_dirs`` in config.yaml) are
scanned alongside the local ``~/.hermes/skills/`` directory.  External dirs
are read-only — they appear in the index but new skills are always created
in the local dir.  Local skills take precedence when names collide.

``compact_categories`` (e.g. from the coding posture — see
agent/coding_context.py) demotes whole categories to a names-only line in
the rendered index. Nothing is ever hidden: every skill name stays
visible and loadable via ``skill_view`` / ``skills_list``; only the
descriptions are dropped, and a footer note explains the demotion.

#### def `build_nous_subscription_prompt(valid_tool_names: set[str] | None = None) -> str`

Build a compact Nous subscription capability block for the system prompt.

#### def `load_soul_md(context_length: Optional[int] = None) -> Optional[str]`

Load SOUL.md from HERMES_HOME and return its content, or None.

Used as the agent identity (slot #1 in the system prompt).  When this
returns content, ``build_context_files_prompt`` should be called with
``skip_soul=True`` so SOUL.md isn't injected twice.

#### def `build_context_files_prompt(cwd: Optional[str] = None, skip_soul: bool = False, context_length: Optional[int] = None, allow_install_tree_fallback: bool = False) -> str`

Discover and load context files for the system prompt.

Priority (first found wins — only ONE project context type is loaded):
  1. .hermes.md / HERMES.md  (walk to git root)
  2. AGENTS.md / agents.md   (cwd only)
  3. CLAUDE.md / claude.md   (cwd only)
  4. .cursorrules / .cursor/rules/*.mdc  (cwd only)

SOUL.md from HERMES_HOME is independent and always included when present.

Each context source is capped before injection. The cap defaults to the
model's context window (scaled — see ``_dynamic_context_file_max_chars``)
when *context_length* is provided, falling back to 20,000 chars otherwise.
An explicit ``context_file_max_chars`` in config.yaml always wins.

When *skip_soul* is True, SOUL.md is not included here (it was already
loaded via ``load_soul_md()`` for the identity slot).


## agent.prompt_caching

### 模块文档

Anthropic prompt caching strategy.

Single layout: ``system_and_3``. 4 cache_control breakpoints — system
prompt + last 3 non-system messages, all at the same TTL (5m or 1h).
Reduces input token costs by ~75% on multi-turn conversations within a
single session.

Pure functions -- no class state, no AIAgent dependency.

### 顶层函数

#### def `apply_anthropic_cache_control(api_messages: List[Dict[str, Any]], cache_ttl: str = '5m', native_anthropic: bool = False) -> List[Dict[str, Any]]`

Apply system_and_3 caching strategy to messages for Anthropic models.

Places up to 4 cache_control breakpoints: system prompt + last 3 non-system
messages, all at the same TTL.

Returns:
    Deep copy of messages with cache_control breakpoints injected.


## agent.rate_limit_tracker

### 模块文档

Rate limit tracking for inference API responses.

Captures x-ratelimit-* headers from provider responses and provides
formatted display for the /usage slash command.  Currently supports
the Nous Portal header format (also used by OpenRouter and OpenAI-compatible
APIs that follow the same convention).

Header schema (12 headers total):
    x-ratelimit-limit-requests          RPM cap
    x-ratelimit-limit-requests-1h       RPH cap
    x-ratelimit-limit-tokens            TPM cap
    x-ratelimit-limit-tokens-1h         TPH cap
    x-ratelimit-remaining-requests      requests left in minute window
    x-ratelimit-remaining-requests-1h   requests left in hour window
    x-ratelimit-remaining-tokens        tokens left in minute window
    x-ratelimit-remaining-tokens-1h     tokens left in hour window
    x-ratelimit-reset-requests          seconds until minute request window resets
    x-ratelimit-reset-requests-1h       seconds until hour request window resets
    x-ratelimit-reset-tokens            seconds until minute token window resets
    x-ratelimit-reset-tokens-1h         seconds until hour token window resets

### class RateLimitBucket

> 继承: `object` ｜ 方法数: 3（公开 3）

One rate-limit window (e.g. requests per minute).

#### property `used(self) -> int`

#### property `usage_pct(self) -> float`

#### property `remaining_seconds_now(self) -> float`

Estimated seconds remaining until reset, adjusted for elapsed time.


### class RateLimitState

> 继承: `object` ｜ 方法数: 2（公开 2）

Full rate-limit state parsed from response headers.

#### property `has_data(self) -> bool`

#### property `age_seconds(self) -> float`


### 顶层函数

#### def `parse_rate_limit_headers(headers: Mapping[str, str], provider: str = '') -> Optional[RateLimitState]`

Parse x-ratelimit-* headers into a RateLimitState.

Returns None if no rate limit headers are present.

#### def `format_rate_limit_display(state: RateLimitState) -> str`

Format rate limit state for terminal/chat display.

#### def `format_rate_limit_compact(state: RateLimitState) -> str`

One-line compact summary for status bars / gateway messages.


## agent.reactions

### 模块文档

Token-free detection of user *reactions* to the agent.

Currently the only reaction is ``vibe`` — an expression of affection or
gratitude toward the agent (``ily``, ``<3``, ``love you``, ``good bot``, a heart
emoji, …). Detection is a curated regex/lexicon: **no model call, no tokens**.

This is the single source of truth shared by every surface — the CLI pet, the
TUI heart, and the desktop floating hearts all react off the same signal,
delivered via ``AIAgent.reaction_callback`` (wired per interactive host).

Generalized on purpose: :func:`detect_reaction` returns a reaction *kind*
string, so new kinds (other emoji reactions, etc.) can be added here without
touching any caller. We match affection specifically — not general positive
sentiment — so "this is great" does NOT fire, but "good bot" / "❤️" do.

### 顶层函数

#### def `detect_reaction(text: str | None) -> str | None`

Return the reaction kind for *text* (currently :data:`VIBE`), or ``None``.

Pure, token-free, and safe to call on every user turn.


## agent.reasoning_timeouts

### 模块文档

Per-reasoning-model stale-timeout floor for known reasoning models.

Reasoning models (those that emit extended thinking blocks before their
first content token) routinely exceed Hermes's default chat-model
stale detectors:

* Stream stale detector:   ``HERMES_STREAM_STALE_TIMEOUT``     default 180s
                           ``agent/chat_completion_helpers.py:2544``
* Non-stream stale detector: ``HERMES_API_CALL_STALE_TIMEOUT``  default 90s
                           ``run_agent.py:1140``

For NVIDIA Nemotron 3 Ultra on the hosted NIM gateway the empirical
upstream idle kill is ~120s (first-party reproduction at
NVIDIA/NemoClaw#4846 — TTFB ~31s, stream dies at 120s). The same
failure mode exists on OpenAI o1/o3, Anthropic Opus 4.x thinking,
DeepSeek R1, Qwen QwQ, xAI Grok reasoning — every cloud reasoning
model hits upstream-proxies / load-balancers with idle timeouts
shorter than the model's thinking phase. Result: the stale detector
kills the connection mid-think, surfacing as
``BrokenPipeError``/``RemoteProtocolError`` on the next read.

This module provides a floor that the existing stale-detector scaling
blocks consult via :func:`get_reasoning_stale_timeout_floor` and
apply as ``max(default, floor)``. It is a FLOOR:

* Never overrides explicit user config (``providers.<id>.models.<model>.stale_timeout_seconds``
  or ``request_timeout_seconds`` already wins — this code never runs
  in that branch).
* Never lowers an existing threshold.
* Has zero effect on non-reasoning models — they are not in the
  allowlist and the resolver returns ``None``.

Matching uses start-anchored regex on the slug-only component of
the model name (after stripping any aggregator prefix like
``openai/``, ``x-ai/``, ``anthropic/``).  The right-anchor matches
end-of-string or a ``-``/``.``/``_`` slug separator, so ``qwen3-235b``
matches the ``qwen3`` family entry (a future model slug would be
``qwen3-235b-instruct`` and would also match) but ``some-other-qwen3``
does NOT match ``qwen3`` (the ``-qwen3`` is not at start of slug).

The ``o1`` case is the most delicate: a model named
``llama-4-70b-o1-preview`` is a hypothetical community derivative that
should NOT trigger the reasoning-model floor for the user (the user
chose a non-OpenAI model, not a reasoning model).  The start-of-slug
anchor naturally excludes this — the matched ``o1-preview`` is at
position 11 of the slug, not at position 0.  The previous substring-
with-trailing-hyphen design would have over-matched here, which is
why start-of-slug anchoring is the right shape.

Fixes #52217.

### 顶层函数

#### def `get_reasoning_stale_timeout_floor(model: object) -> Optional[float]`

Return the stale-timeout floor (seconds) for a known reasoning model.

Returns ``None`` when the model is not in the allowlist or the
argument is empty / not a string.  Matching uses
word-boundary-anchored regex on the lowercased model name, so
``openai/o3-mini`` matches the ``o3-mini`` slug but
``olmo-1`` does NOT match ``o1`` (the ``o1`` substring is not
at a word boundary inside ``olmo-1``).

Aggregator prefixes (``openai/``, ``x-ai/``, ``anthropic/`` etc.)
are preserved through matching — the ``/`` is itself a word
boundary, so ``openai/o3-mini`` matches ``o3-mini`` because the
``/`` before ``o3-mini`` satisfies the left-anchor alternation.

This is a FLOOR — callers must apply it as ``max(default, floor)``
and only when no explicit user-configured per-model
``stale_timeout_seconds`` exists.

>>> get_reasoning_stale_timeout_floor("nvidia/nemotron-3-ultra-550b-a55b")
600.0
>>> get_reasoning_stale_timeout_floor("openai/o3-mini")
300.0
>>> get_reasoning_stale_timeout_floor("deepseek/deepseek-r1")
600.0
>>> get_reasoning_stale_timeout_floor("deepseek/deepseek-v4-flash")
600.0
>>> get_reasoning_stale_timeout_floor("deepseek/deepseek-v4-pro")
600.0
>>> get_reasoning_stale_timeout_floor("qwen/qwen3-235b-a22b-thinking")
180.0
>>> get_reasoning_stale_timeout_floor("x-ai/grok-4-fast-reasoning")
300.0
>>> get_reasoning_stale_timeout_floor("anthropic/claude-opus-4-6")
240.0
>>> get_reasoning_stale_timeout_floor("gpt-4o") is None
True
>>> get_reasoning_stale_timeout_floor("olmo-1") is None
True
>>> get_reasoning_stale_timeout_floor(None) is None
True


## agent.redact

### 模块文档

Regex-based secret redaction for logs and tool output.

Applies pattern matching to mask API keys, tokens, and credentials
before they reach log files, verbose output, or gateway logs.

Short tokens (< 18 chars) are fully masked. Longer tokens preserve
the first 6 and last 4 characters for debuggability.

### class RedactingFormatter

> 继承: `logging.Formatter` ｜ 方法数: 2（公开 1）

Log formatter that redacts secrets from all log messages.

#### def `__init__(fmt = None, datefmt = None, style = '%', **kwargs)`

#### def `format(self, record: logging.LogRecord) -> str`


### 顶层函数

#### def `mask_secret(value: str, head: int = 4, tail: int = 4, floor: int = 12, placeholder: str = '***', empty: str = '') -> str`

Mask a secret for display, preserving ``head`` and ``tail`` characters.

Canonical helper for display-time redaction across Hermes — used by
``hermes config``, ``hermes status``, ``hermes dump``, and anywhere
a secret needs to be shown truncated for debuggability while still
keeping the bulk hidden.

Args:
    value:       The secret to mask. ``None``/empty returns ``empty``.
    head:        Leading characters to preserve. Default 4.
    tail:        Trailing characters to preserve. Default 4.
    floor:       Values shorter than ``head + tail + floor_margin`` are
                 fully masked (returns ``placeholder``). Default 12 —
                 matches the existing config/status/dump convention.
    placeholder: Value returned for too-short inputs. Default ``"***"``.
    empty:       Value returned when ``value`` is falsy (None, ""). The
                 caller can override this to e.g. ``color("(not set)",
                 Colors.DIM)`` for user-facing display.

Examples:
    >>> mask_secret("sk-proj-abcdef1234567890")
    'sk-p...7890'
    >>> mask_secret("short")                         # fully masked
    '***'
    >>> mask_secret("")                              # empty default
    ''
    >>> mask_secret("", empty="(not set)")           # empty override
    '(not set)'
    >>> mask_secret("long-token", head=6, tail=4, floor=18)
    '***'

#### def `redact_cdp_url(value: object) -> str`

Mask secrets in a CDP/browser endpoint URL before it is logged.

The global ``redact_sensitive_text`` deliberately passes web-URL query
params and ``user:pass@`` userinfo through unmasked (OAuth callbacks,
magic-link / pre-signed URLs the agent is meant to follow -- see the
web-URL note above). CDP discovery endpoints are NOT such a workflow:
their query-string tokens and userinfo passwords are pure credentials
that must never reach the logs. So for CDP URLs we opt INTO the two URL
redactors that the global pass leaves off.

This is the single source of truth for redacting a CDP URL that is passed
*directly* to a log or error message. Callers that instead need to redact an
exception whose text embeds the URL (e.g. a ``websockets`` connect error)
should route that through their own error-text helper, which delegates here
-- see ``tools.browser_supervisor._redact_cdp_error_text``.

#### def `redact_sensitive_text(text: str, force: bool = False, code_file: bool = False, file_read: bool = False, redact_url_credentials: bool = False) -> str`

Apply all redaction patterns to a block of text.

Safe to call on any string -- non-matching text passes through unchanged.
Enabled by default. Disable via security.redact_secrets: false in config.yaml.
Set force=True for safety boundaries that must never return raw secrets
regardless of the user's global logging redaction preference.

Set redact_url_credentials=True at non-navigation egress boundaries to
additionally redact credential-named query parameters and ``user:pass@``
URL userinfo. The default remains False because actionable OAuth callback,
magic-link, and pre-signed URLs must survive ordinary tool flows unchanged.

Set code_file=True to skip the ENV-assignment and JSON-field regex
patterns when the text is known to be source code (e.g. MAX_TOKENS=***
constants, "apiKey": "test" fixtures). Prefix patterns, auth headers,
private keys, DB connstrings, JWTs, and URL secrets are still redacted.

Set file_read=True for file *content* returned to the agent (read_file /
search_files / cat). Secrets are STILL redacted — they are never exposed —
but prefix-matched credentials are replaced with a non-reusable sentinel
(``«redacted:ghp_…»``) instead of a head/tail-preserving mask
(``ghp_S1...Pn2T``). The old mask looked like a real-but-truncated key, so
an agent reading it from config.yaml and writing it back silently corrupted
the stored credential into a dead 13-char value → 401 (issue #35519). The
sentinel is syntactically invalid as a token, so it can't be mistaken for a
usable key or written back as one. Implies code_file=True (config/data
files shouldn't trigger the source-code ENV/JSON false-positive paths).

Performance: each regex pattern is gated behind a cheap substring
pre-check (e.g. ``"=" in text`` for ENV assignments, ``"://" in text``
for URLs, ``"eyJ" in text`` for JWTs). On a typical hermes log line
(no secrets) this drops the 13-pattern scan from ~5.6us to ~1.8us per
record (-68%). The pre-checks are conservative — false positives
still run the full regex, which then doesn't match. False negatives
are impossible because every regex requires the gated substring to
match.

#### def `is_env_dump_command(command: str | None) -> bool`

Return True if ``command`` dumps environment variables to stdout.

Detects ``env`` / ``printenv`` / ``set`` / ``export`` / ``declare`` as the
first token of any segment in a pipeline or sequence (``;`` / ``&&`` /
``||`` / ``|``). Conservative: a parse failure or anything unrecognized
returns False (callers then fall back to the safer code_file=True path,
which still masks prefix-shaped keys).

#### def `redact_terminal_output(output: str, command: str | None = None, force: bool = False) -> str`

Redact secrets from terminal/process stdout.

Single redaction policy for ALL terminal-output surfaces — foreground
``terminal`` results AND background ``process(action=poll/log/wait)``
output — so they can't diverge. Picks ``code_file`` based on whether
``command`` is an environment dump:

- env-dump command (``env``/``printenv``/``set``/``export``/``declare``)
  → ``code_file=False`` so the ENV-assignment pass masks opaque tokens.
- anything else (or unknown command) → ``code_file=True`` to avoid
  false positives on source/config dumps.

``force=True`` bypasses the global ``security.redact_secrets`` preference
for safety boundaries that must never emit raw credentials.


## agent.replay_cleanup

### 模块文档

Replay-history sanitization shared across resume code paths.

When a session's last turn dies mid-tool-loop — the process is killed by a
restart/shutdown command, a stale-timeout fires, or an interrupt lands before
the tool result is written — the persisted transcript can end with a dangling
``assistant(tool_calls)`` (no matching ``tool`` answer) or an interrupted
``assistant→tool`` block.  On resume the model sees that broken tail and
re-issues the unanswered call, producing an endless "thinking"/reboot loop
(#49201, #29086).

These pure helpers strip those tails before the history is replayed to the
model.  They were originally local to ``gateway/run.py`` (which fixed the
messaging-gateway path) and are extracted here so every resume surface — the
messaging gateway AND the TUI/WebUI gateway — shares the same cleanup instead
of the WebUI path silently skipping it.

### 顶层函数

#### def `is_interrupted_tool_result(content: Any) -> bool`

Return True if a tool result indicates the tool was interrupted.

#### def `strip_interrupted_tool_tails(agent_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Strip interrupted assistant→tool sequences from replay history.

Older interrupted gateway turns can be followed by a queued real user
message, so the interrupted assistant/tool block is not necessarily the
final tail by the time we rebuild replay history.  Remove any contiguous
assistant(tool_calls) + tool-result block that contains an interrupted tool
result, while preserving successful tool-call sequences intact.

#### def `strip_dangling_tool_call_tail(agent_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Strip a trailing ``assistant(tool_calls)`` block left with NO answers.

When a tool call itself kills the gateway process (``docker restart``,
``systemctl restart``, ``kill``, ``hermes gateway restart``), the process
is terminated by SIGKILL *mid-call* — before the tool result is ever
written and before the orderly shutdown rewind
(``_drop_trailing_empty_response_scaffolding``) can run.  The last thing
persisted is the ``assistant`` message that issued the ``tool_calls``,
with zero matching ``tool`` rows.

On resume the model sees an unanswered tool call at the tail and naturally
re-issues it — which restarts the gateway again, producing the infinite
reboot loop in #49201.  ``strip_interrupted_tool_tails`` does not catch
this because there is no tool result to inspect for an interrupt marker.

This strips that dangling tail at the source so there is nothing for the
model to re-execute.  It only acts when the tail is an
``assistant(tool_calls)`` whose calls have NO corresponding ``tool``
results — a completed assistant→tool pair (any tool answers present) is
left untouched so genuine mid-progress tool loops still resume.

#### def `sanitize_replay_history(agent_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Apply both replay-tail strippers in the canonical order.

Convenience entry point for resume code paths: removes interrupted
assistant→tool blocks anywhere in the history, then removes a dangling
unanswered ``assistant(tool_calls)`` tail.  Returns the same list object
when there is nothing to strip.

#### def `is_dangerous_confirmation(content: Any) -> bool`

Return True if a user-message text matches a known dangerous confirmation.

Used by ``strip_stale_dangerous_confirmations`` to decide which
transcript rows to expire. Substring + case-insensitive so that
``"Please confirm forced restart, the host is critical"`` still matches.

#### def `strip_stale_dangerous_confirmations(agent_history: List[Dict[str, Any]], now: float, expiry_seconds: float = _DANGEROUS_CONFIRMATION_EXPIRY_SECONDS) -> List[Dict[str, Any]]`

Expire stale dangerous-confirmation text in user messages (#59607).

When a high-risk side effect (e.g. host restart via ``shutdown.exe``)
runs, the user's plain-text confirmation phrase is persisted in the
conversation transcript.  If the host restart killed the gateway
process before the assistant's tool result was written, the
transcript tail ends on the assistant's text response — and the
dangerous confirmation text remains in the user role.

On the next inbound message — possibly a casual "are you there?" from
the user minutes later — the LLM sees the stale confirmation and may
interpret the new turn as a fresh re-confirmation, re-executing the
destructive action.  This is the failure mode reported in #59607.

Expired confirmations are REDACTED IN PLACE, not removed: deleting a
user message from the incident tail (``user(confirm) →
assistant("OK, restarting")``) would leave two consecutive assistant
messages, violating the strict role-alternation invariant providers
enforce.  The message survives with its role intact; only the trigger
text is replaced by a sentinel that tells the model the confirmation
has expired.

Messages without a timestamp are left untouched (backward
compatibility: legacy transcripts and in-memory test scaffolding have
no timestamps).  User messages that contain dangerous confirmation
text but are within the expiry window are also left untouched — they
represent a fresh confirmation that has not yet been acted on.

Complements 75ed07ace (which strips the *assistant* side of the
broken tail) by handling the *user* side: a stale plain-text
confirmation that the assistant has not yet responded to in a way
the resume logic recognises.


## agent.retry_utils

### 模块文档

Retry utilities — jittered backoff for decorrelated retries.

Replaces fixed exponential backoff with jittered delays to prevent
thundering-herd retry spikes when multiple sessions hit the same
rate-limited provider concurrently.

### 顶层函数

#### def `jittered_backoff(attempt: int, base_delay: float = 5.0, max_delay: float = 120.0, jitter_ratio: float = 0.5) -> float`

Compute a jittered exponential backoff delay.

Args:
    attempt: 1-based retry attempt number.
    base_delay: Base delay in seconds for attempt 1.
    max_delay: Maximum delay cap in seconds.
    jitter_ratio: Fraction of computed delay to use as random jitter
        range.  0.5 means jitter is uniform in [0, 0.5 * delay].

Returns:
    Delay in seconds: min(base * 2^(attempt-1), max_delay) + jitter.

The jitter decorrelates concurrent retries so multiple sessions
hitting the same provider don't all retry at the same instant.

#### def `is_zai_coding_overload_error(base_url: str | None, model: str | None, error: Any) -> bool`

Return True for Z.AI Coding Plan transient overload 429s.

The coding-plan endpoint reports overload as HTTP 429 with body code 1305
and message "The service may be temporarily overloaded...". Treat only
that narrow shape specially so ordinary quota/billing 429s still fail fast
through the existing classifier.

#### def `adaptive_rate_limit_backoff(attempt: int, base_url: str | None, model: str | None, error: Any, default_wait: float, short_attempts: int = _ZAI_CODING_OVERLOAD_SHORT_ATTEMPTS) -> tuple[float, str | None]`

Provider-aware rate-limit backoff.

For most providers this returns ``default_wait`` unchanged. For Z.AI
Coding Plan GLM-5.2 overloads, keep the first ``short_attempts`` retries on
the normal short exponential schedule, then switch to progressively longer
waits (30s → 60s → 90s → 120s, capped) plus light jitter.

``attempt`` is 1-based, matching the retry loop's logged attempt number.
Returns ``(wait_seconds, reason_label)`` where ``reason_label`` is suitable
for status/log decoration when a provider-specific policy fired.

#### def `zai_coding_overload_retry_ceiling(short_attempts: int = _ZAI_CODING_OVERLOAD_SHORT_ATTEMPTS) -> int`

Retry-loop ceiling needed for the full Z.AI overload backoff schedule.

The adaptive policy runs ``short_attempts`` short retries, then walks the
long-backoff table one entry per subsequent attempt. The retry loop gives
up as soon as ``retry_count >= ceiling`` — and that check runs *before* the
attempt's backoff is computed — so the ceiling must sit one past the final
long-backoff entry for every long tier to actually execute.

With the default ``api_max_retries`` (3) equal to ``short_attempts`` (3),
the loop always gave up before reaching the long tier, leaving the whole
long-backoff schedule as dead code. Callers extend the ceiling to this
value for Z.AI Coding overload 429s so the 30/60/90/120s waits run.


## agent.runtime_cwd

### 模块文档

Single source of truth for the agent working directory.

`TERMINAL_CWD` is the runtime carrier for the configured working directory
(design #19214/#19242: `terminal.cwd` is bridged once to `TERMINAL_CWD` at
gateway/cron startup). The local-CLI backend deliberately leaves it unset and
relies on the launch dir. Reading it in one place keeps the system prompt, the
tool surfaces, and context-file discovery agreeing on where the agent lives.

Multi-session gateways can pin a logical cwd via the `_SESSION_CWD`
contextvar; CLI/cron fall through to `TERMINAL_CWD`/launch cwd.

### 顶层函数

#### def `set_session_cwd(cwd: str | None) -> Token`

Pin the logical cwd for the current context.

#### def `clear_session_cwd() -> None`

#### def `resolve_agent_cwd() -> Path`

#### def `resolve_context_cwd() -> Path | None`


## agent.secret_scope

### 模块文档

Profile-scoped credential resolution for multi-profile gateway multiplexing.

The multiplexing gateway serves many profiles from one process. Each profile
has its own ``.env`` with its own provider keys and platform tokens, so we
**cannot** union them into the process-global ``os.environ`` (that would leak
profile A's keys to profile B's turns, and to every subprocess spawned with
``env=dict(os.environ)``).

This module provides a fail-closed, context-local secret scope:

- ``set_secret_scope(mapping)`` installs the active profile's secrets for the
  current task (a contextvar, so it propagates into the agent's worker thread
  via ``copy_context()`` exactly like the HERMES_HOME override).
- ``get_secret(name)`` reads from that scope. When multiplexing is **active**
  and no scope is set, it RAISES rather than silently falling back to
  ``os.environ`` — an un-migrated or newly-added call site fails loud at that
  exact line instead of leaking another profile's value. When multiplexing is
  **off** (the default), it transparently reads ``os.environ`` so the
  single-profile gateway and every non-gateway caller behave exactly as before.

Design rationale lives in ``docs/design/multiplexing-gateway.md`` (Workstream A).

### class UnscopedSecretError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when a secret is read in multiplex mode with no scope installed.

This is the fail-closed signal: it means a credential read reached
``get_secret`` without a profile scope active, which in a multiplexer would
otherwise leak whichever profile's value happened to be in ``os.environ``.
The fix is to wrap the call path in ``set_secret_scope(...)`` (the per-turn
/ per-adapter profile scope), not to widen the allowlist.


### 顶层函数

#### def `set_multiplex_active(active: bool) -> None`

Mark whether the process is running as a profile multiplexer.

Called once at gateway startup. When True, ``get_secret`` fails closed on
an unscoped read instead of falling back to ``os.environ``.

#### def `is_multiplex_active() -> bool`

Return whether the process is running as a profile multiplexer.

#### def `set_secret_scope(secrets: Optional[Mapping[str, str]]) -> Token`

Install the active profile's secret mapping for the current context.

Returns a token for ``reset_secret_scope``. Pass ``None`` to clear.

#### def `reset_secret_scope(token: Token) -> None`

Restore the previous secret scope.

#### def `current_secret_scope() -> Optional[Mapping[str, str]]`

Return the active secret mapping, or None when no scope is installed.

#### def `get_secret(name: str, default: Optional[str] = None) -> Optional[str]`

Resolve a credential by env-var name, honoring the active profile scope.

Resolution order:

1. Genuinely-global vars (``_is_global_env``) always read ``os.environ`` —
   they are deployment settings, not profile secrets.
2. When a secret scope is installed (multiplexed turn), read from it; an
   absent key returns ``default``. The scope is authoritative — we do NOT
   fall through to ``os.environ``, because in a multiplexer ``os.environ``
   may hold another profile's value.
3. No scope installed:
   - multiplex INACTIVE (default deployment): read ``os.environ`` —
     identical to the legacy ``os.getenv`` behavior every caller had before.
   - multiplex ACTIVE: FAIL CLOSED. Raise ``UnscopedSecretError`` so the
     missing scope is caught loudly instead of leaking a cross-profile value.

**异常**: `UnscopedSecretError`

#### def `load_env_file(env_path: Path) -> Dict[str, str]`

Parse a ``.env`` file into a plain dict WITHOUT touching ``os.environ``.

Used to load a profile's secrets into an isolated mapping for
``set_secret_scope``. Mirrors python-dotenv's basic parsing (KEY=VALUE,
``export`` prefix, ``#`` comments, optional matching quotes) but never
mutates the process environment — that isolation is the whole point.

#### def `build_profile_secret_scope(hermes_home: Path) -> Dict[str, str]`

Build a profile's secret mapping from its ``<home>/.env``.

Returns a fresh dict (safe to install via ``set_secret_scope``). Genuinely
global vars are intentionally NOT copied in — ``get_secret`` reads those
from ``os.environ`` directly, so the scope holds only profile secrets.


## agent.secret_sources.__init__

### 模块文档

External secret source integrations.

A secret source is anything that can supply environment-variable-shaped
credentials at process startup, _after_ ~/.hermes/.env has loaded.

The contract every source implements is
:class:`agent.secret_sources.base.SecretSource`; the orchestrator that
runs the enabled sources (ordering, mapped-beats-bulk precedence,
first-claim-wins conflicts, ``override_existing`` semantics, provenance)
is :func:`agent.secret_sources.registry.apply_all`.  Multiple sources
can be enabled at once — see the registry module docstring for the
precedence ladder.  The atomic-write / 0600 / TTL disk-cache substrate
is shared across backends in ``agent.secret_sources._cache`` so the
security-sensitive bits live in exactly one place.

Currently bundled:

  - ``bitwarden`` — Bitwarden Secrets Manager (`bws` CLI).  See
    ``agent.secret_sources.bitwarden`` for the integration and
    ``hermes_cli.secrets_cli`` for the user-facing setup wizard.
  - ``onepassword`` — 1Password ``op://`` secret references (`op` CLI).
    See ``agent.secret_sources.onepassword`` for the integration and
    ``hermes_cli.onepassword_secrets_cli`` for the user-facing commands.

The bundled set is deliberately closed (policy mirrors memory
providers): new third-party secret managers ship as standalone plugin
repos that subclass ``SecretSource`` and register through
``PluginContext.register_secret_source()`` — they are NOT added to this
package.  A generic ``command`` source is a possible future exception;
OS keystores (Keychain/DPAPI/libsecret) are under discussion.

## agent.secret_sources._cache

### 模块文档

Shared substrate for external secret-source backends.

Every backend (Bitwarden, 1Password, …) needs the same handful of
security-sensitive primitives:

  * a uniform result object (:class:`FetchResult`),
  * environment-variable name validation (:func:`is_valid_env_name`),
  * a two-layer fetch cache whose disk half writes atomically with ``0600``
    permissions and honours a TTL (:class:`DiskCache`, :class:`CachedFetch`).

These used to live inline inside ``bitwarden.py``.  Pulling them here means
the atomic-write / ``0600`` / TTL logic is audited and fixed in exactly one
place instead of drifting across copy-pasted per-backend modules — each
backend supplies only its own cache-key shape and a serializer for it.

Nothing in this module ever raises out to the caller's hot path: the disk
layer is strictly best-effort (a miss just triggers a refetch), because a
cache problem must never block Hermes startup.

### class CachedFetch

> 继承: `object` ｜ 方法数: 1（公开 1）

A set of fetched secret values plus when they were fetched.

#### def `is_fresh(self, ttl_seconds: float) -> bool`


### class DiskCache

> 继承: `Generic[K]` ｜ 方法数: 5（公开 4）

Best-effort, profile-aware on-disk cache for fetched secret values.

One JSON object per backend lives at ``<hermes_home>/cache/<basename>``::

    {"key": "<serialized cache key>", "secrets": {...}, "fetched_at": 1.0}

The file holds only secret *values* keyed by the serialized cache key —
never raw auth material.  Backends are responsible for fingerprinting
tokens/sessions *before* they reach ``key_serializer`` so the token can't
land in the key.

Writes are atomic (``mkstemp`` → ``chmod 0600`` → ``os.replace``) and the
containing ``cache/`` directory is forced to ``0700`` — ``mkdir``'s mode is
umask-subject, so the chmod is the reliable form.  Both ``read`` and
``write`` short-circuit when ``ttl_seconds <= 0``, so setting the TTL to
zero disables *both* cache layers symmetrically: a user opting out never
gets secret values written to disk at all.

#### def `__init__(basename: str, key_serializer: Callable[[K], str]) -> None`

#### def `path(self, home_path: Optional[Path] = None) -> Path`

#### def `read(self, key: K, ttl_seconds: float, home_path: Optional[Path] = None) -> Optional[CachedFetch]`

Return a fresh cached entry for ``key``, or None.

Best-effort: any I/O or parse error, a key mismatch, or a stale entry
all return None so the caller re-fetches.

#### def `write(self, key: K, entry: CachedFetch, ttl_seconds: float, home_path: Optional[Path] = None) -> None`

Persist ``entry`` for ``key`` atomically at mode ``0600``.

No-op when ``ttl_seconds <= 0`` (so caching is genuinely off) or on any
I/O error — the next invocation just re-fetches.

#### def `clear(self, home_path: Optional[Path] = None) -> None`

Delete the on-disk cache file if present (idempotent).


### 顶层函数

#### def `resolve_cache_home(home_path: Optional[Path] = None) -> Path`

Resolve the Hermes home used for cache paths.

``home_path`` is whatever ``load_hermes_dotenv()`` already resolved;
falling back to ``$HERMES_HOME`` / ``~/.hermes`` keeps direct callers
(and tests that don't thread a home through) working.


## agent.secret_sources.base

### 模块文档

Secret-source contract: the ABC every secret backend implements.

A *secret source* resolves credentials from an external secret manager
(Bitwarden Secrets Manager, 1Password, an OS keystore, a user script, ...)
into environment-variable-shaped values at process startup, AFTER
``~/.hermes/.env`` has loaded and BEFORE the rest of Hermes reads
``os.environ``.

Scope of the contract (deliberate, please do not widen):

* **Read-only.**  Sources resolve refs → values.  There is no write-back
  ("save this key to your vault"), no arbitrary secret objects, and no
  mid-session secret API.  If a future need for rotation/refresh appears
  it will arrive as a versioned optional hook — do not bolt it on.
* **Startup-time, synchronous.**  ``fetch()`` is called once per process
  (per HERMES_HOME) by the orchestrator in
  :mod:`agent.secret_sources.registry`, which enforces a wall-clock
  timeout around it.  Sources must not spawn background refreshers.
* **Never raises, never prompts.**  ``fetch()`` returns a
  :class:`FetchResult` — errors go in ``result.error`` with a
  machine-readable :class:`ErrorKind`.  Interactive auth belongs in the
  source's CLI ``setup`` flow, never on the startup path (non-TTY
  gateway/cron startup must never block on stdin).
* **Sources fetch; the orchestrator applies.**  A source returns the
  name→value mapping it *would* contribute.  Precedence (mapped-beats-bulk,
  first-wins, ``override_existing``, protected vars), conflict warnings,
  provenance tracking, and the actual ``os.environ`` writes are owned by
  the orchestrator so no backend can get them wrong.

Versioning: ``SECRET_SOURCE_API_VERSION`` gates plugin compatibility.
New *optional* hooks with default implementations do not bump it;
required-signature changes do, and the registry skips (with a warning)
sources built against a different major version instead of crashing
startup.

### class ErrorKind

> 继承: `str`、`Enum` ｜ 方法数: 0（公开 0）

Machine-readable failure taxonomy for :class:`FetchResult.error`.

A fixed vocabulary keeps startup warnings and ``hermes secrets status``
uniform across backends, and lets the orchestrator implement
kind-dependent policy (e.g. a future stale-cache fallback on
``NETWORK``/``TIMEOUT`` but not on ``AUTH_FAILED``) exactly once.


### class FetchResult

> 继承: `object` ｜ 方法数: 1（公开 1）

Outcome of one source's fetch.

``secrets`` holds what the source *would* contribute; whether each
var is actually applied is the orchestrator's decision.  ``applied``
and ``skipped`` exist for backward compatibility with the original
Bitwarden fetch-and-apply entry point and are left empty by
conforming ``fetch()`` implementations.

#### property `ok(self) -> bool`


### class SecretSource

> 继承: `ABC` ｜ 方法数: 6（公开 6）

One external secret backend.

Subclasses set the class attributes and implement :meth:`fetch`.
Everything else has a sensible default.

Attributes:
    name: Config-section key under ``secrets:`` in config.yaml.
        Lowercase ``[a-z0-9_]+``.  Also the provenance label stored
        for every var this source supplies.
    label: Human-readable name used in startup messages and
        ``hermes secrets status`` (e.g. ``"Bitwarden Secrets Manager"``).
    shape: ``"mapped"`` when the user explicitly binds env-var names
        to refs (1Password ``env:`` map, command source) or
        ``"bulk"`` when the backend injects whole projects/folders
        of secrets implicitly (Bitwarden BSM).  The orchestrator
        gives mapped sources precedence over bulk sources: an
        explicit binding is stronger intent than a project dump.
    scheme: Optional URI scheme this source owns for secret
        references (``"op"`` for ``op://...``).  Must be unique
        across registered sources — refs may eventually appear
        outside the ``secrets:`` block (e.g. credential-pool
        ``api_key`` fields), so scheme collisions are rejected at
        registration time to keep that future possible.
    api_version: Contract version this source was built against.

#### def `fetch(self, cfg: dict, home_path: Path) -> FetchResult`

Resolve this source's secrets. MUST NOT raise or prompt.

``cfg`` is the source's raw config section (``secrets.<name>``)
from config.yaml — treat every field defensively, the section
may be malformed.  ``home_path`` is the resolved HERMES_HOME.

#### def `is_enabled(self, cfg: dict) -> bool`

Whether the user turned this source on.

#### def `override_existing(self, cfg: dict) -> bool`

May this source overwrite vars that .env / the shell already set?

This NEVER extends to vars claimed by another secret source in the
same startup pass — cross-source overrides are a config error the
orchestrator warns about, not a knob.

#### def `protected_env_vars(self, cfg: dict) -> FrozenSet[str]`

Env vars the orchestrator must never let ANY source overwrite.

Typically the source's own bootstrap-auth var (e.g.
``BWS_ACCESS_TOKEN``) so a vault that contains its own access
token can't clobber the credential used to reach it.

#### def `fetch_timeout_seconds(self, cfg: dict) -> float`

Wall-clock budget the orchestrator enforces around fetch().

#### def `config_schema(self) -> dict`

Optional description of this source's config keys.

Shape: ``{key: {"description": str, "default": Any}}``.  Used by
setup surfaces to render config without hardcoding per-source
knowledge.  Purely informational.


### 顶层函数

#### def `is_valid_env_name(name: str) -> bool`

True when ``name`` is a legal environment-variable name.

#### def `scrub_ansi(text: str) -> str`

Strip ANSI escape sequences (whole CSI/OSC sequences, not just ESC).

#### def `run_secret_cli(argv: Sequence[str], allow_env: Sequence[str] = (), extra_env: Optional[Dict[str, str]] = None, timeout: float = DEFAULT_CLI_TIMEOUT_SECONDS) -> subprocess.CompletedProcess`

Run a secret-manager helper CLI with a minimal, allowlisted env.

Security posture shared by every subprocess-driven backend:

* argv list only — never ``shell=True``.  Callers pass user-supplied
  reference strings AFTER a ``--`` option terminator in their argv.
* The child gets ``PATH``/``HOME``/locale basics plus only the env
  vars named in ``allow_env`` (auth/session vars) and ``extra_env``
  — never a copy of the full post-dotenv ``os.environ``, which by
  this point holds every credential Hermes knows about.
* ``NO_COLOR=1`` is set and stderr/stdout are ANSI-scrubbed so
  helper diagnostics can't smuggle escape sequences into Hermes
  output.
* stdin is ``/dev/null`` so a helper that decides to prompt fails
  fast instead of hanging startup.

Raises ``RuntimeError`` on spawn failure or timeout (message safe to
surface); returns the completed process otherwise — callers own
returncode interpretation.

**异常**: `RuntimeError`


## agent.secret_sources.bitwarden

### 模块文档

Bitwarden Secrets Manager (`bws` CLI) integration.

Hermes pulls API keys from Bitwarden Secrets Manager at process startup
so they don't have to live in plaintext in ``~/.hermes/.env``.

Design summary
--------------

* The ``bws`` binary is auto-installed into ``<hermes_home>/bin/bws`` on
  first use.  Hermes pins one version (``_BWS_VERSION``) and downloads
  the matching asset from the official GitHub Releases page, verifying
  the SHA-256 against the release's published checksum file.
* The access token is stored in ``~/.hermes/.env`` as
  ``BWS_ACCESS_TOKEN`` (or whatever name the user picked in
  ``secrets.bitwarden.access_token_env``).  This is the one
  bootstrap secret — every other provider key can live in Bitwarden.
* Pulling secrets is a single ``bws secret list <project_id>
  --output json`` call.  We cache the result in-process for
  ``cache_ttl_seconds`` so back-to-back ``hermes`` invocations don't
  hammer the API.
* Failures NEVER block Hermes startup.  Missing binary, no network,
  expired token, etc. all emit a one-line warning and continue with
  whatever credentials ``.env`` already had.

The module is intentionally subprocess-driven rather than going through
the ``bitwarden-sdk-secrets`` Python package: one cross-platform binary
is easier to lazy-install than a wheels-with-Rust-extension dependency.

### class BitwardenSource

> 继承: `SecretSource` ｜ 方法数: 4（公开 4）

Bitwarden Secrets Manager as a registered secret source.

Thin adapter over the module's fetch machinery.  ``fetch()`` only
*fetches* — precedence, override semantics, conflict warnings, and
the ``os.environ`` writes are the orchestrator's job
(see ``agent.secret_sources.registry.apply_all``).

Bitwarden is a **bulk** source: it injects every secret in the
configured BSM project, so explicit per-var bindings from mapped
sources (e.g. the 1Password ``env:`` map) outrank it.

#### def `override_existing(self, cfg: dict) -> bool`

#### def `protected_env_vars(self, cfg: dict)`

#### def `config_schema(self) -> dict`

#### def `fetch(self, cfg: dict, home_path: Path) -> FetchResult`


### 顶层函数

#### def `find_bws(install_if_missing: bool = False) -> Optional[Path]`

Return a path to a usable ``bws`` binary, or None.

Resolution order:
  1. ``<hermes_home>/bin/bws``  (our managed copy — preferred)
  2. ``shutil.which("bws")``    (system PATH)

When ``install_if_missing`` is True and neither resolves, this calls
:func:`install_bws` to download and verify the pinned version.

#### def `install_bws(force: bool = False) -> Path`

Download, verify, and install the pinned ``bws`` binary.

Returns the path to the installed executable.  Raises on any
failure (network, checksum, extraction) — callers in the auto-install
path catch these; the user-facing ``hermes secrets bitwarden setup``
surface lets them propagate so the wizard can show a clear error.

**异常**: `RuntimeError`

#### def `fetch_bitwarden_secrets(access_token: str, project_id: str, binary: Optional[Path] = None, cache_ttl_seconds: float = 300, use_cache: bool = True, server_url: str = '', home_path: Optional[Path] = None) -> Tuple[Dict[str, str], List[str]]`

Pull the secrets for ``project_id`` from Bitwarden Secrets Manager.

Returns ``(secrets_dict, warnings_list)``.

Set ``server_url`` to point at a non-default Bitwarden region or a
self-hosted instance — e.g. ``https://vault.bitwarden.eu`` for EU
Cloud accounts.  When empty, ``bws`` uses its built-in default
(``https://vault.bitwarden.com``, US Cloud).  This is plumbed into
the subprocess as ``BWS_SERVER_URL``.

Caching is a two-layer LRU: an in-process dict (for hot-reload paths
inside one process) and a disk-persisted JSON file under
``<hermes_home>/cache/bws_cache.json`` (for back-to-back CLI invocations).
Both share the same TTL.  Pass ``home_path`` so disk cache lookups find
the right directory in tests / non-standard installs; otherwise we fall
back to ``$HERMES_HOME`` / ``~/.hermes``.

Raises :class:`RuntimeError` for fatal conditions (missing binary,
auth failure, unparseable output).  Callers in the env_loader path
catch this and emit a single warning; callers in the user-facing
setup wizard let it propagate.

**异常**: `class`, `RuntimeError`

#### def `apply_bitwarden_secrets(enabled: bool, access_token_env: str = 'BWS_ACCESS_TOKEN', project_id: str = '', override_existing: bool = False, cache_ttl_seconds: float = 300, auto_install: bool = True, server_url: str = '', home_path: Optional[Path] = None) -> FetchResult`

Pull secrets from BSM and set them on ``os.environ``.

This is the function ``load_hermes_dotenv()`` calls after the .env
files have loaded.  It is intentionally defensive — any failure
returns a :class:`FetchResult` with ``error`` set; it never raises.

``server_url`` selects the Bitwarden region or self-hosted endpoint
(e.g. ``https://vault.bitwarden.eu`` for EU Cloud).  Empty string
means use ``bws``'s default (US Cloud).

Parameters mirror the ``secrets.bitwarden.*`` config keys so the
caller can just splat the dict in.


## agent.secret_sources.onepassword

### 模块文档

1Password (`op` CLI) secret source.

Resolve provider credentials from 1Password ``op://vault/item/field``
references at process startup so they don't have to live in plaintext in
``~/.hermes/.env``.

Design summary
--------------

* Users map environment-variable names to official 1Password secret
  references in ``secrets.onepassword.env``::

      secrets:
        onepassword:
          enabled: true
          env:
            OPENAI_API_KEY: "op://Private/OpenAI/api key"
            ANTHROPIC_API_KEY: "op://Private/Anthropic/credential"

* After ``.env`` loads, each reference is resolved with a single
  ``op read -- <reference>`` call and injected into ``os.environ`` (the
  same point in startup as the Bitwarden source).
* Authentication is whatever the user's ``op`` CLI already uses — a
  service-account token (``OP_SERVICE_ACCOUNT_TOKEN``) for headless boxes,
  or a desktop/interactive session (``OP_SESSION_*``).  Hermes never
  authenticates on the user's behalf; it shells out to an already-trusted,
  already-authenticated CLI.
* Failures NEVER block startup.  A missing ``op`` binary, expired auth, a
  bad reference, or a permission error each surface a one-line warning and
  Hermes continues with whatever credentials ``.env`` already had.

The atomic-write / ``0600`` / TTL cache mechanics are shared with the other
backends via :mod:`agent.secret_sources._cache` — successful, complete pulls
are cached in-process and on disk under ``<hermes_home>/cache/op_cache.json``
so back-to-back short-lived ``hermes`` invocations don't re-shell ``op`` for
every reference.  The disk file holds only resolved secret *values*; auth
material is fingerprinted, never stored.

### class OnePasswordSource

> 继承: `SecretSource` ｜ 方法数: 4（公开 4）

1Password as a registered secret source.

Thin adapter over the module's fetch machinery.  ``fetch()`` only
*fetches* — precedence, override semantics, conflict warnings, and
the ``os.environ`` writes are the orchestrator's job
(see ``agent.secret_sources.registry.apply_all``).

1Password is a **mapped** source: the user explicitly binds each env
var to an ``op://`` reference under ``secrets.onepassword.env``, so
its claims outrank bulk sources (e.g. a Bitwarden project dump) on
contested vars.

#### def `override_existing(self, cfg: dict) -> bool`

#### def `protected_env_vars(self, cfg: dict)`

#### def `config_schema(self) -> dict`

#### def `fetch(self, cfg: dict, home_path: Path) -> FetchResult`


### 顶层函数

#### def `find_op(binary_path: str = '') -> Optional[Path]`

Resolve a usable ``op`` binary, or None.

When ``binary_path`` is set it is used verbatim and PATH is NOT consulted
— pinning an absolute path is a way to avoid trusting whatever ``op`` shows
up first on ``PATH``.  A pinned-but-missing path returns None (the caller
surfaces a clear error) rather than silently falling back.

#### def `fetch_onepassword_secrets(references: Dict[str, str], account: str = '', token_env: str = _DEFAULT_TOKEN_ENV, binary: Optional[Path] = None, binary_path: str = '', use_cache: bool = True, cache_ttl_seconds: float = 300, home_path: Optional[Path] = None) -> Tuple[Dict[str, str], List[str]]`

Resolve ``references`` (name → ``op://…``) to ``(secrets, warnings)``.

Raises :class:`RuntimeError` only when no ``op`` binary is available — a
fatal "can't fetch anything" condition.  Per-reference failures (expired
auth, bad reference, empty value) are collected as warnings and the
reference is dropped, so one bad entry never sinks the rest.

Only a complete, error-free pull is cached, so a transient auth failure
isn't frozen in for the whole TTL window.

**异常**: `class`, `RuntimeError`

#### def `apply_onepassword_secrets(enabled: bool, env: Optional[Dict[str, str]] = None, account: str = '', service_account_token_env: str = _DEFAULT_TOKEN_ENV, binary_path: str = '', override_existing: bool = True, cache_ttl_seconds: float = 300, home_path: Optional[Path] = None) -> FetchResult`

Resolve configured ``op://`` references and set them on ``os.environ``.

Called by ``load_hermes_dotenv()`` after the .env files have loaded.
Intentionally defensive — any failure returns a :class:`FetchResult` with
``error`` set (or surfaces warnings); it never raises.

Parameters mirror the ``secrets.onepassword.*`` config keys so the caller
can splat the dict in.  References that are already satisfied by the
current environment (when ``override_existing`` is false) are skipped
*before* fetching, so ``op`` is never invoked for a value that would be
discarded.


## agent.secret_sources.registry

### 模块文档

Secret-source registry + apply orchestrator.

This module owns everything that must be uniform across secret backends
so no individual source can get it wrong:

* registration (name/scheme uniqueness, API-version gating)
* per-source wall-clock timeout enforcement around ``fetch()``
* precedence: mapped sources beat bulk sources; within a shape,
  ``secrets.sources`` order (or registration order) decides; first
  claim wins — later sources never silently clobber an earlier one
* ``override_existing`` semantics (may beat .env/shell, never another
  secret source, never a protected var)
* cross-source conflict warnings (shadowed claims are always surfaced)
* provenance: which source supplied every applied var

The single entry point for startup is :func:`apply_all`, called from
``hermes_cli.env_loader._apply_external_secret_sources()``.

Plugins register additional sources via
``PluginContext.register_secret_source()`` which lands in
:func:`register_source`.  In-tree sources are registered lazily by
:func:`_ensure_builtin_sources` — the set of bundled sources is
deliberately closed (Bitwarden, and 1Password once it lands); new
third-party backends ship as standalone plugin repos implementing
:class:`agent.secret_sources.base.SecretSource`.

### class AppliedVar

> 继承: `object` ｜ 方法数: 0（公开 0）

Provenance record for one env var the orchestrator set.


### class SourceReport

> 继承: `object` ｜ 方法数: 0（公开 0）

One source's outcome within an :class:`ApplyReport`.


### class ApplyReport

> 继承: `object` ｜ 方法数: 1（公开 1）

Merged outcome of one orchestrated apply pass.

#### property `applied_any(self) -> bool`


### 顶层函数

#### def `register_source(source: SecretSource, replace: bool = False) -> bool`

Register a secret source.  Returns True on success.

Rejections are logged, never raised — a bad plugin must not take
down startup.  ``replace`` allows tests / user plugins to override
a bundled source of the same name (last-writer-wins like model
providers), but scheme collisions across *different* names are
always rejected.

#### def `get_source(name: str) -> Optional[SecretSource]`

#### def `list_sources() -> List[SecretSource]`

#### def `apply_all(secrets_cfg: dict, home_path: Path, environ: Optional[Dict[str, str]] = None) -> ApplyReport`

Fetch from every enabled source and apply the merged result to env.

``environ`` defaults to ``os.environ``; injectable for tests.

Precedence per env var (most-specific intent wins):

1. Pre-existing env (.env / shell) — unless the winning source has
   ``override_existing: true``.
2. Mapped sources, in configured order.
3. Bulk sources, in configured order.

First claim wins.  A later source that also carries the var gets a
``skipped_claimed`` entry and a conflict warning — never a silent
clobber, and ``override_existing`` never applies across sources.


## agent.shell_hooks

### 模块文档

Shell-script hooks bridge.

Reads the ``hooks:`` block from ``cli-config.yaml``, prompts the user for
consent on first use of each ``(event, command)`` pair, and registers
callbacks on the existing plugin hook manager so every existing
``invoke_hook()`` site dispatches to the configured shell scripts — with
zero changes to call sites.

Design notes
------------
* Python plugins and shell hooks compose naturally: both flow through
  :func:`hermes_cli.plugins.invoke_hook` and its aggregators.  Python
  plugins are registered first (via ``discover_and_load()``) so their
  block decisions win ties over shell-hook blocks.
* Subprocess execution uses ``shlex.split(os.path.expanduser(command))``
  with ``shell=False`` — no shell injection footguns.  Users that need
  pipes/redirection wrap their logic in a script.
* First-use consent is gated by the allowlist under
  ``~/.hermes/shell-hooks-allowlist.json``.  Non-TTY callers must pass
  ``accept_hooks=True`` (resolved from ``--accept-hooks``,
  ``HERMES_ACCEPT_HOOKS``, or ``hooks_auto_accept: true`` in config)
  for registration to succeed without a prompt.
* Registration is idempotent — safe to invoke from both the CLI entry
  point (``hermes_cli/main.py``) and the gateway entry point
  (``gateway/run.py``).

Wire protocol
-------------
**stdin** (JSON, piped to the script)::

    {
        "hook_event_name": "pre_tool_call",
        "tool_name":       "terminal",
        "tool_input":      {"command": "rm -rf /"},
        "session_id":      "sess_abc123",
        "cwd":             "/home/user/project",
        "extra":           {...}   # event-specific kwargs
    }

**stdout** (JSON, optional — anything else is ignored)::

    # Block a pre_tool_call (either shape accepted; normalised internally):
    {"decision": "block", "reason":  "Forbidden command"}   # Claude-Code-style
    {"action":   "block", "message": "Forbidden command"}   # Hermes-canonical

    # Inject context for pre_llm_call:
    {"context": "Today is Friday"}

    # Silent no-op:
    <empty or any non-matching JSON object>

Per-event ``extra`` keys
~~~~~~~~~~~~~~~~~~~~~~~~

The ``extra`` object contains every kwarg that is **not** one of the
top-level payload keys (``tool_name``, ``args``, ``session_id``,
``parent_session_id``).  The tables below list the ``extra`` keys
emitted by each built-in hook site.

``post_tool_call`` (emitted from ``model_tools.py``)::

    result          – tool return value (serialised string)
    status          – "ok" | "error" | "blocked"
    error_type      – error category (e.g. "ValueError"), or None
    error_message   – human-readable error text, or None
    duration_ms     – wall-clock time in milliseconds
    task_id         – current task id (empty string if none)
    tool_call_id    – provider tool-call id
    turn_id         – current turn id
    api_request_id  – current API request id
    middleware_trace – list of dicts from tool middleware chain

``pre_tool_call`` (emitted from ``model_tools.py``)::

    task_id         – current task id (empty string if none)
    tool_call_id    – provider tool-call id
    turn_id         – current turn id
    api_request_id  – current API request id
    middleware_trace – list of dicts from tool middleware chain

``on_session_start`` (emitted from ``agent/conversation_loop.py``)::

    model           – model name (e.g. "claude-sonnet-4-20250514")
    platform        – platform identifier (e.g. "cli", "whatsapp")

``on_session_end`` (emitted from ``agent/turn_finalizer.py``)::

    task_id         – current task id
    turn_id         – current turn id
    completed       – bool, True when the turn produced a final response
    interrupted     – bool, True when the user interrupted
    model           – model name
    platform        – platform identifier

``subagent_stop`` (emitted from ``tools/delegate_tool.py``)::

    parent_turn_id  – parent agent's current turn id
    child_session_id – child (subagent) session id
    child_role      – role string of the child agent
    child_summary   – summary of the child's work
    child_status    – exit status string (e.g. "success", "error")
    duration_ms     – wall-clock time of the child run in milliseconds

### class ShellHookSpec

> 继承: `object` ｜ 方法数: 2（公开 1）

Parsed and validated representation of a single ``hooks:`` entry.

#### def `matches_tool(self, tool_name: Optional[str]) -> bool`


### 顶层函数

#### def `register_from_config(cfg: Optional[Dict[str, Any]], accept_hooks: bool = False) -> List[ShellHookSpec]`

Register every configured shell hook on the plugin manager.

``cfg`` is the full parsed config dict (``hermes_cli.config.load_config``
output).  The ``hooks:`` key is read out of it.  Missing, empty, or
non-dict ``hooks`` is treated as zero configured hooks.

``accept_hooks=True`` skips the TTY consent prompt — the caller is
promising that the user has opted in via a flag, env var, or config
setting.  ``HERMES_ACCEPT_HOOKS=1`` and ``hooks_auto_accept: true`` are
also honored inside this function so either CLI or gateway call sites
pick them up.

Returns the list of :class:`ShellHookSpec` entries that ended up wired
up on the plugin manager.  Skipped entries (unknown events, malformed,
not allowlisted, already registered) are logged but not returned.

#### def `iter_configured_hooks(cfg: Optional[Dict[str, Any]]) -> List[ShellHookSpec]`

Return the parsed ``ShellHookSpec`` entries from config without
registering anything.  Used by ``hermes hooks list`` and ``doctor``.

#### def `reset_for_tests() -> None`

Clear the idempotence set.  Test-only helper.

#### def `allowlist_path() -> Path`

Path to the per-user shell-hook allowlist file.

#### def `load_allowlist() -> Dict[str, Any]`

Return the parsed allowlist, or an empty skeleton if absent.

#### def `save_allowlist(data: Dict[str, Any]) -> None`

Atomically persist the allowlist via per-process ``mkstemp`` +
``os.replace``.  Cross-process read-modify-write races are handled
by :func:`_locked_update_approvals` (``fcntl.flock``).  On OSError
the failure is logged; the in-process hook still registers but
the approval won't survive across runs.

#### def `revoke(command: str) -> int`

Remove every allowlist entry matching ``command``.

Returns the number of entries removed.  Does not unregister any
callbacks that are already live on the plugin manager in the current
process — restart the CLI / gateway to drop them.

#### def `allowlist_entry_for(event: str, command: str) -> Optional[Dict[str, Any]]`

Return the allowlist record for this pair, if any.

#### def `script_mtime_iso(command: str) -> Optional[str]`

ISO-8601 mtime of the resolved script path, or ``None`` if the
script is missing.

#### def `script_is_executable(command: str) -> bool`

Return ``True`` iff ``command`` is runnable as configured.

For a bare invocation (``/path/hook.sh``) the script itself must be
executable.  For interpreter-prefixed commands (``python3
/path/hook.py``, ``/usr/bin/env bash hook.sh``) the script just has
to be readable — the interpreter doesn't care about the ``X_OK``
bit.  Mirrors what ``_spawn`` would actually do at runtime.

#### def `run_once(spec: ShellHookSpec, kwargs: Dict[str, Any]) -> Dict[str, Any]`

Fire a single shell-hook invocation with a synthetic payload.
Used by ``hermes hooks test`` and ``hermes hooks doctor``.

``kwargs`` is the same dict that :func:`hermes_cli.plugins.invoke_hook`
would pass at runtime.  It is routed through :func:`_serialize_payload`
so the synthetic stdin exactly matches what a real hook firing would
produce — otherwise scripts tested via ``hermes hooks test`` could
diverge silently from production behaviour.

Returns the :func:`_spawn` diagnostic dict plus a ``parsed`` field
holding the canonical Hermes-wire-shape response.


## agent.skill_bundles

### 模块文档

Skill bundles — aliases that load multiple skills under one slash command.

A skill bundle is a small YAML file that names a set of skills to load
together. Invoking ``/<bundle-name>`` from the CLI or gateway loads every
referenced skill's full content into a single user message, the same way
``/<skill-name>`` does — but for N skills at once.

Storage
-------
Bundles live in ``~/.hermes/skill-bundles/*.yaml`` (and the equivalent
profile-aware directory under ``HERMES_HOME``). Each file looks like::

    name: backend-dev
    description: Backend feature work — code review, testing, PR workflow.
    skills:
      - github-code-review
      - test-driven-development
      - github-pr-workflow
    instruction: |
      Optional extra guidance to inject above the skill bodies.

The file's stem is treated as a fallback name when ``name:`` is absent, so
dropping a YAML into the directory is enough to register a new bundle.

Conflict resolution
-------------------
If a bundle and a skill share the same slash name, the bundle wins. The
slash command dispatch checks bundles first, then falls back to skills.
This is the intended behavior — a user who names a bundle ``research``
explicitly wants ``/research`` to mean their bundle, not whatever skill
happens to share the slug.

Public API
----------
- :func:`get_skill_bundles` — return ``{"/slug": bundle_info}``
- :func:`resolve_bundle_command_key` — map a user-typed command to its slug
- :func:`build_bundle_invocation_message` — produce the full user message
- :func:`reload_bundles` — re-scan disk and return a diff
- :func:`list_bundles` — return rich info for display (``hermes bundles``)
- :func:`save_bundle` / :func:`delete_bundle` — file-level operations

### 顶层函数

#### def `scan_bundles() -> Dict[str, Dict[str, Any]]`

Scan the bundles directory and rebuild the cache.

Returns the same mapping as :func:`get_skill_bundles` — ``"/slug"`` →
bundle info dict. Later bundles with a duplicate slug are skipped with
a warning (first wins, alphabetical order).

#### def `get_skill_bundles() -> Dict[str, Dict[str, Any]]`

Return the current bundle mapping, rescanning when disk changed.

Cheap to call repeatedly: only rescans when the bundles directory or
any bundle file's mtime is newer than the cached snapshot.

#### def `resolve_bundle_command_key(command: str) -> Optional[str]`

Resolve a user-typed command to its canonical bundle slash key.

Hyphens and underscores are treated interchangeably to mirror the
skill-command behavior (Telegram converts hyphens to underscores in
bot command names).

#### def `reload_bundles() -> Dict[str, Any]`

Re-scan the bundles directory and return a diff.

Mirrors :func:`agent.skill_commands.reload_skills` so callers can use
the same display logic. Returns a dict with ``added``, ``removed``,
``unchanged``, and ``total`` keys.

#### def `list_bundles() -> List[Dict[str, Any]]`

Return a sorted list of bundle info dicts for display.

#### def `build_bundle_invocation_message(cmd_key: str, user_instruction: str = '', task_id: str | None = None, platform: str | None = None) -> Optional[Tuple[str, List[str], List[str]]]`

Build the user message content for a bundle slash command invocation.

Returns ``(message, loaded_skill_names, missing_skill_names)`` or
``None`` if the bundle wasn't found.

A bundle that references skills the user doesn't have installed still
loads — the agent gets a note about which ones were skipped. This is
the same forgiving stance ``build_preloaded_skills_prompt`` uses for
``-s`` CLI preloading.

Disabled skills are also skipped: bundles load members via
``_load_skill_payload`` directly, bypassing the scan-time disabled
filter in ``get_skill_commands()``, so the disabled list must be
re-applied here.  ``platform`` scopes the check to a specific
platform's ``skills.platform_disabled`` config (gateway dispatch
passes it explicitly because the gateway handles multiple platforms
in one process); when *None*, the platform resolves from session env
vars and the global disabled list still applies.  Mirrors the
stacked-skill gate in gateway dispatch (#58888).

#### def `bundle_path_for(name: str) -> Path`

Return the canonical filesystem path for a bundle name.

**异常**: `ValueError`

#### def `save_bundle(name: str, skills: List[str], description: str = '', instruction: str = '', overwrite: bool = False) -> Path`

Write a bundle to disk and invalidate the cache.

Raises ``FileExistsError`` if the target exists and ``overwrite`` is
False. Raises ``ValueError`` if the inputs are unusable.

**异常**: `ValueError`, `FileExistsError`

#### def `delete_bundle(name: str) -> Path`

Delete a bundle by name. Returns the deleted path.

Raises ``FileNotFoundError`` if the bundle doesn't exist.

**异常**: `FileNotFoundError`

#### def `get_bundle(name: str) -> Optional[Dict[str, Any]]`

Look up a bundle by name (slug-normalized).


## agent.skill_commands

### 模块文档

Shared slash command helpers for skills.

Shared between CLI (cli.py) and gateway (gateway/run.py) so both surfaces
can invoke skills via /skill-name commands.

### 顶层函数

#### def `extract_user_instruction_from_skill_message(content: Any) -> Optional[str]`

Recover the user's instruction from a slash-skill-expanded turn.

Returns:
    - The original string unchanged when it is NOT skill scaffolding
      (a normal user message passes straight through).
    - The extracted user instruction when the scaffolding carried one.
    - ``None`` when the content is skill scaffolding with no user
      instruction (i.e. a bare ``/skill`` invocation). Callers that feed
      memory providers should skip the turn in that case — there is no
      user content worth storing.

#### def `scan_skill_commands() -> Dict[str, Dict[str, Any]]`

Scan ~/.hermes/skills/ and return a mapping of /command -> skill info.

Returns:
    Dict mapping "/skill-name" to {name, description, skill_md_path, skill_dir}.

#### def `get_skill_commands() -> Dict[str, Dict[str, Any]]`

Return the current skill commands mapping (scan first if empty).

Rescans when the active platform scope changes (e.g. a gateway
process serving Telegram and Discord concurrently) so each platform
sees its own ``skills.platform_disabled`` view (#14536).

#### def `reload_skills() -> Dict[str, Any]`

Re-scan the skills directory and return a diff of what changed.

Rescans ``~/.hermes/skills/`` and any ``skills.external_dirs`` so the
slash-command map (``agent.skill_commands._skill_commands``) reflects
skills added or removed on disk.

This does NOT invalidate the skills system-prompt cache. Skills are
called by name via ``/skill-name``, ``skills_list``, or ``skill_view``
— they don't need to be in the system prompt for the model to use them.
Keeping the prompt cache intact preserves prefix caching across the
reload, so a user invoking ``/reload-skills`` pays no cache-reset cost.

Returns:
    Dict with keys::

        {
          "added":      [{"name": str, "description": str}, ...],
          "removed":    [{"name": str, "description": str}, ...],
          "unchanged":  [skill names present before and after],
          "total":      total skill count after rescan,
          "commands":   total /slash-skill count after rescan,
        }

    ``description`` is the skill's full SKILL.md frontmatter
    ``description:`` field — the same string the system prompt renders
    as ``    - name: description`` for pre-existing skills.

#### def `resolve_skill_command_key(command: str) -> Optional[str]`

Resolve a user-typed /command to its canonical skill_cmds key.

Skills are always stored with hyphens — ``scan_skill_commands`` normalizes
spaces and underscores to hyphens when building the key. Hyphens and
underscores are treated interchangeably in user input: this matches
``_check_unavailable_skill`` and accommodates Telegram bot-command names
(which disallow hyphens, so ``/claude-code`` is registered as
``/claude_code`` and comes back in the underscored form).

Returns the matching ``/slug`` key from ``get_skill_commands()`` or
``None`` if no match.

#### def `build_skill_invocation_message(cmd_key: str, user_instruction: str = '', task_id: str | None = None, runtime_note: str = '') -> Optional[str]`

Build the user message content for a skill slash command invocation.

Args:
    cmd_key: The command key including leading slash (e.g., "/gif-search").
    user_instruction: Optional text the user typed after the command.

Returns:
    The formatted message string, or None if the skill wasn't found.

#### def `split_stacked_skill_commands(rest: str) -> tuple[list[str], str]`

Consume additional leading ``/skill`` tokens from *rest*.

*rest* is the text that follows the FIRST matched skill command (the
caller has already resolved that one). Leading whitespace-delimited
tokens that start with ``/`` and resolve to installed skill commands are
consumed, up to ``_MAX_STACKED_SKILLS`` total leading skills (i.e. at
most ``_MAX_STACKED_SKILLS - 1`` extra keys here). Parsing stops at the
first token that is not a resolvable skill command — that token and
everything after it become the user instruction.

Returns:
    ``(extra_cmd_keys, remaining_instruction)`` where ``extra_cmd_keys``
    are canonical ``/slug`` keys from :func:`get_skill_commands`.

#### def `build_stacked_skill_invocation_message(cmd_keys: list[str], user_instruction: str = '', task_id: str | None = None) -> Optional[tuple[str, list[str], list[str]]]`

Build the user message for a stacked multi-skill slash invocation.

Args:
    cmd_keys: Canonical ``/slug`` keys, in the order the user typed them.
    user_instruction: Text remaining after the leading skill commands.

Returns:
    ``(message, loaded_skill_names, missing_skill_names)`` or ``None``
    when no skill could be loaded at all.

#### def `build_preloaded_skills_prompt(skill_identifiers: list[str], task_id: str | None = None) -> tuple[str, list[str], list[str]]`

Load one or more skills for session-wide CLI/TUI preloading.

Returns (prompt_text, loaded_skill_names, missing_identifiers).

Disabled skills are treated the same as missing ones: this loads via a
raw identifier straight into ``_load_skill_payload``, bypassing
``get_skill_commands()``'s scan-time disabled filter — mirrors the
bundle-invocation gate (#59156). Without this, ``hermes -s <skill>`` or
a deployment's ``HERMES_TUI_SKILLS`` env var could force-load a skill an
operator disabled via ``skills.disabled``/``skills.platform_disabled``.


## agent.skill_preprocessing

### 模块文档

Shared SKILL.md preprocessing helpers.

### 顶层函数

#### def `load_skills_config() -> dict`

Load the ``skills`` section of config.yaml (best-effort).

#### def `substitute_template_vars(content: str, skill_dir: Path | None, session_id: str | None) -> str`

Replace ${HERMES_SKILL_DIR} / ${HERMES_SESSION_ID} in skill content.

Only substitutes tokens for which a concrete value is available --
unresolved tokens are left in place so the author can spot them.

#### def `run_inline_shell(command: str, cwd: Path | None, timeout: int) -> str`

Execute a single inline-shell snippet and return its stdout (trimmed).

Failures return a short ``[inline-shell error: ...]`` marker instead of
raising, so one bad snippet can't wreck the whole skill message.

#### def `expand_inline_shell(content: str, skill_dir: Path | None, timeout: int) -> str`

Replace every !`cmd` snippet in ``content`` with its stdout.

Runs each snippet with the skill directory as CWD so relative paths in
the snippet work the way the author expects.

#### def `preprocess_skill_content(content: str, skill_dir: Path | None, session_id: str | None = None, skills_cfg: dict | None = None) -> str`

Apply configured SKILL.md template and inline-shell preprocessing.


## agent.skill_utils

### 模块文档

Lightweight skill metadata utilities shared by prompt_builder and skills_tool.

This module intentionally avoids importing the tool registry, CLI config, or any
heavy dependency chain.  It is safe to import at module level without triggering
tool registration or provider resolution.

### 顶层函数

#### def `is_excluded_skill_path(path) -> bool`

True if *path* should be skipped by active skill scanners.

Use this on every ``SKILL.md`` path produced by direct ``rglob`` scans to
prune dependency, virtualenv, VCS, cache, and progressive-disclosure
support-package paths. Centralising the check here keeps every
skill-scanning site in sync with the shared exclusion set.

Accepts a Path or string.

#### def `is_skill_support_path(path) -> bool`

True if *path* is under a support dir of an actual skill root.

``references/``, ``templates/``, ``assets/``, and ``scripts/`` are
progressive-disclosure support areas when they sit directly inside a skill
directory containing ``SKILL.md``. They are not active discovery roots for
standalone skills. A preserved package such as
``some-skill/references/old-skill-package/SKILL.md`` is documentation data
unless the caller explicitly loads it via ``file_path``.

Legitimate categories or skill names such as ``skills/scripts/foo`` remain
discoverable because their ``scripts`` component is not directly under a
directory that contains ``SKILL.md``.

#### def `yaml_load(content: str)`

Parse YAML with lazy import and CSafeLoader preference.

#### def `parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]`

Parse YAML frontmatter from a markdown string.

Uses yaml with CSafeLoader for full YAML support (nested metadata, lists)
with a fallback to simple key:value splitting for robustness.

A single leading UTF-8 BOM (U+FEFF) is stripped before parsing. Windows
GUI editors (Notepad, PowerShell ``>``) prepend one when saving a SKILL.md
as UTF-8, and ``read_text(encoding="utf-8")`` preserves it (only
``utf-8-sig`` strips it). Left in place, the BOM defeats the ``---`` fence
check below and the whole frontmatter is silently discarded — name,
description, ``platforms`` gating, env-var setup, and conditional
activation all vanish. See CONTRIBUTING.md "File encoding".

Returns:
    (frontmatter_dict, remaining_body)

#### def `skill_matches_platform_list(platforms: Any) -> bool`

Return True when *platforms* is compatible with the current OS.

#### def `skill_matches_platform(frontmatter: Dict[str, Any]) -> bool`

Return True when the skill is compatible with the current OS.

Skills declare platform requirements via a top-level ``platforms`` list
in their YAML frontmatter::

    platforms: [macos]          # macOS only
    platforms: [macos, linux]   # macOS and Linux

If the field is absent or empty the skill is compatible with **all**
platforms (backward-compatible default).

Termux note: on Termux/Android, ``sys.platform`` is ``"linux"`` on
older Pythons but became ``"android"`` on Python 3.13+. Termux is a
Linux userland riding on the Android kernel, so skills tagged
``linux`` are treated as compatible in Termux regardless of which
``sys.platform`` value Python reports. Individual Linux commands
inside a skill may still misbehave (no systemd, BusyBox utils, no
apt/dnf, etc.) but that is on the skill, not on platform gating.

#### def `skill_matches_environment(frontmatter: Dict[str, Any]) -> bool`

Return True when the skill is relevant to the current runtime environment.

Skills may declare an ``environments`` list in their YAML frontmatter::

    environments: [kanban]        # only relevant when kanban is active
    environments: [s6]            # only relevant inside the s6 Docker image
    environments: [docker]        # only relevant inside any container

If the field is absent or empty the skill is relevant in **all**
environments (backward-compatible default).

This is an OFFER-time filter: it controls whether a skill shows up in the
skills index / autocomplete / slash-command list. It is intentionally NOT
enforced by ``skill_view`` or ``--skills`` preloading — an explicit load is
explicit consent, and load-bearing force-loads (e.g. a dispatcher pinning
a task to a specialist skill via ``--skills``) must always succeed
regardless of how the offer surfaces filter the skill.

A skill matches when ANY of its declared environments is currently active
(OR semantics, mirroring ``platforms``). Unknown env tags fail open.

#### def `get_disabled_skill_names(platform: str | None = None) -> Set[str]`

Read disabled skill names from config.yaml.

Args:
    platform: Explicit platform name (e.g. ``"telegram"``).  When
        *None*, resolves from ``HERMES_PLATFORM`` or
        ``HERMES_SESSION_PLATFORM`` env vars.  Returns the global
        disabled list, unioned with the platform-specific list when a
        platform is resolved (a globally-disabled skill stays disabled
        on every platform).

Reads the config file directly (no CLI config imports) to stay
lightweight.

#### def `get_external_skills_dirs() -> List[Path]`

Read ``skills.external_dirs`` from config.yaml and return validated paths.

Each entry is expanded (``~`` and ``${VAR}``) and resolved to an absolute
path.  Only directories that actually exist are returned.  Duplicates and
paths that resolve to the local ``~/.hermes/skills/`` are silently skipped.

Cached in-process, keyed on ``config.yaml`` mtime — the function is
called once per skill during banner / tool-registry scans, and YAML
parsing a non-trivial config dominates ``hermes`` cold-start time
when the cache is absent.

#### def `get_all_skills_dirs() -> List[Path]`

Return all skill directories: local ``~/.hermes/skills/`` first, then external.

The local dir is always first (and always included even if it doesn't exist
yet — callers handle that).  External dirs follow in config order.

#### def `normalize_skill_lookup_name(identifier: str) -> str`

Normalize a skill identifier to a ``skill_view()``-safe relative path.

Slash commands and cron jobs may store absolute paths to skills that live
under ``~/.hermes/skills/`` (including via symlinks) or configured
``skills.external_dirs``. ``skill_view()`` rejects absolute names for
security, so callers must translate trusted absolute paths to their
relative form first.

#### def `is_external_skill_path(path) -> bool`

Return True when ``path`` lives under a configured external skills dir.

``skills.external_dirs`` are externally owned: Hermes can discover and view
their skills, and foreground user-directed tool calls may still edit them,
but autonomous lifecycle maintenance must treat them as read-only. This
helper centralizes the ownership boundary so curator/reporting/tool paths do
not each need to re-interpret the config.

#### def `extract_skill_conditions(frontmatter: Dict[str, Any]) -> Dict[str, List]`

Extract conditional activation fields from parsed frontmatter.

#### def `extract_skill_config_vars(frontmatter: Dict[str, Any]) -> List[Dict[str, Any]]`

Extract config variable declarations from parsed frontmatter.

Skills declare config.yaml settings they need via::

    metadata:
      hermes:
        config:
          - key: wiki.path
            description: Path to the LLM Wiki knowledge base directory
            default: "~/wiki"
            prompt: Wiki directory path

Returns a list of dicts with keys: ``key``, ``description``, ``default``,
``prompt``.  Invalid or incomplete entries are silently skipped.

#### def `discover_all_skill_config_vars() -> List[Dict[str, Any]]`

Scan all enabled skills and collect their config variable declarations.

Walks every skills directory, parses each SKILL.md frontmatter, and returns
a deduplicated list of config var dicts.  Each dict also includes a
``skill`` key with the skill name for attribution.

Disabled and platform-incompatible skills are excluded.

#### def `resolve_skill_config_values(config_vars: List[Dict[str, Any]]) -> Dict[str, Any]`

Resolve current values for skill config vars from config.yaml.

Skill config is stored under ``skills.config.<key>`` in config.yaml.
Returns a dict mapping **logical** keys (as declared by skills) to their
current values (or the declared default if the key isn't set).
Path values are expanded via ``os.path.expanduser``.

#### def `extract_skill_description(frontmatter: Dict[str, Any]) -> str`

Extract a truncated description from parsed frontmatter.

#### def `iter_skill_index_files(skills_dir: Path, filename: str)`

Walk skills_dir yielding sorted paths matching *filename*.

Excludes Hermes metadata, VCS, virtualenv/dependency, cache, and skill
support directories. Support directories (references/templates/assets/
scripts) can contain arbitrary markdown and even archived package
``SKILL.md`` files, but they are progressive-disclosure data loaded through
``skill_view(..., file_path=...)`` rather than active skill roots.

#### def `parse_qualified_name(name: str) -> Tuple[Optional[str], str]`

Split ``'namespace:skill-name'`` into ``(namespace, bare_name)``.

Returns ``(None, name)`` when there is no ``':'``.

#### def `is_valid_namespace(candidate: Optional[str]) -> bool`

Check whether *candidate* is a valid namespace (``[a-zA-Z0-9_-]+``).


## agent.ssl_guard

### 模块文档

Preventive SSL CA certificate checks for Hermes Agent.

This module catches broken CA bundle paths before OpenAI/httpx turns them into
opaque ``FileNotFoundError: [Errno 2] No such file or directory`` failures.

### 顶层函数

#### def `verify_ca_bundle() -> None`

Verify configured and bundled CA certificates are present and loadable.

Raises:
    SSLConfigurationError: If an explicit CA-bundle environment variable
        points at a bad path, or if certifi's bundled ``cacert.pem`` is
        missing/corrupt.

**异常**: `SSLConfigurationError`, `_ssl_err`

#### def `verify_ca_bundle_with_fallback() -> None`

Backward-compatible wrapper for older call sites.

The old PR name mentioned a platform fallback, but allowing startup with a
broken certifi bundle still leaves httpx/OpenAI and requests call sites
failing later. Keep the wrapper name but enforce the same check.


## agent.ssl_verify

### 模块文档

TLS verify resolution for httpx/OpenAI provider clients.

### 顶层函数

#### def `resolve_httpx_verify(ca_bundle: Optional[str] = None, ssl_verify: Any = None, base_url: str = '') -> bool | ssl.SSLContext`

Resolve httpx ``verify`` for provider HTTP clients.

Priority:
1. ``ssl_verify: false`` — disable verification (local dev only)
2. explicit ``ca_bundle`` (per-provider ``ssl_ca_cert`` config field)
3. ``HERMES_CA_BUNDLE``, ``SSL_CERT_FILE``, ``REQUESTS_CA_BUNDLE``,
   ``CURL_CA_BUNDLE`` env vars
4. ``True`` (httpx/certifi default)

``base_url`` is used only for the insecure-mode warning message.


## agent.stream_diag

### 模块文档

Stream diagnostics — per-attempt counters, exception chains, retry logging.

When a streaming chat-completions request dies mid-response, we want to
know why: which Cloudflare edge served the request, which OpenRouter
downstream provider answered, how many bytes/chunks we got before the
drop, the HTTP status, the underlying httpx error class.  These helpers
collect that info and emit it both to ``agent.log`` (full detail) and to
the user-facing status line (compact).

All helpers are extracted from :class:`AIAgent` for cleanliness.
``run_agent`` keeps thin forwarder methods so existing call sites and
tests that patch ``run_agent.<helper>`` keep working.

### 顶层函数

#### def `stream_diag_init() -> Dict[str, Any]`

Return a fresh per-attempt diagnostic dict.

Mutated in-place by the streaming functions and read from the retry
block when a stream dies.  Lives on ``request_client_holder`` so it
survives across the closure boundary.

#### def `stream_diag_capture_response(agent: Any, diag: Dict[str, Any], http_response: Any) -> None`

Snapshot interesting headers + HTTP status from the live stream.

Called once at stream open (before iterating chunks) so the metadata
survives even if the stream dies before any chunk arrives.  Failures
are swallowed — diag is best-effort.

#### def `flatten_exception_chain(error: BaseException) -> str`

Return a compact ``Outer(msg) <- Inner(msg) <- ...`` rendering.

OpenAI SDK wraps httpx errors as ``APIConnectionError`` /
``APIError`` and only the wrapper's class is visible at the catch
site — but the underlying ``RemoteProtocolError`` /
``ConnectError`` / ``ReadError`` is what tells us WHY the stream
died.  Walks ``__cause__`` then ``__context__`` (deduped, max 4
deep) to surface the chain in one line.

#### def `log_stream_retry(agent: Any, kind: str, error: BaseException, attempt: int, max_attempts: int, mid_tool_call: bool, diag: Optional[Dict[str, Any]] = None) -> None`

Record a transient stream-drop and retry to ``agent.log``.

Always logs a structured WARNING so users have a breadcrumb regardless
of UI verbosity.  Subagents in particular benefit because their
retries no longer spam the parent's terminal — but the file log keeps
full detail (provider, error class, attempt, base_url, subagent_id).

When *diag* is provided (the per-attempt stream-diagnostic dict from
:func:`stream_diag_init`), the WARNING also captures upstream headers
(cf-ray, x-openrouter-provider, x-openrouter-id), HTTP status, bytes
streamed before the drop, and elapsed time on the dying attempt.
These are the breadcrumbs needed to answer "is one CF edge / one
downstream provider responsible, or is it random across runs?"

#### def `emit_stream_drop(agent: Any, error: BaseException, attempt: int, max_attempts: int, mid_tool_call: bool, diag: Optional[Dict[str, Any]] = None) -> None`

Emit a single user-visible line for a stream drop+retry.

Both top-level agents and subagents announce drops in the UI — the
parent prefixes subagent lines with ``[subagent-N]`` via ``log_prefix``
so they're easy to attribute.  All cases also write a structured
WARNING to ``agent.log`` via :func:`log_stream_retry` with the full
diagnostic detail (subagent_id, provider, base_url, error_type,
cf-ray, x-openrouter-provider, bytes/chunks, elapsed) for post-hoc
analysis.

The user-visible status line is intentionally compact: provider,
error class, attempt N/M, plus ``after Xs`` when the stream dropped
mid-flight.  Full diagnostic detail goes to ``agent.log`` only —
``hermes logs --level WARNING | grep "Stream drop"`` to inspect.


## agent.stream_single_writer

### 模块文档

Best-effort accessors for the single-writer stream fence (#65991).

The fence itself lives on ``AIAgent`` (``_claim_stream_writer`` /
``_stream_writer_is_current`` in ``run_agent.py``), but the streaming code paths
that use it live in *other* modules — ``chat_completion_helpers`` (chat /
anthropic / bedrock) and ``codex_runtime`` (codex responses). Calling the fence
directly as ``agent._claim_stream_writer()`` from those modules makes them
hard-depend on the method being present on whatever object is passed in as
``agent``.

That coupling is a latent crash: a partially-updated checkout (the streaming
helper module newer than ``run_agent``), a hot-reloaded gateway, a duck-typed
agent, or a test double without the method turns an *additive* safety net into a
fatal ``AttributeError`` that aborts the whole turn. A cron job died exactly
this way with ``'AIAgent' object has no attribute '_claim_stream_writer'``.

The fence is only ever allowed to drop a *provably* superseded stream — never
the sole legitimate writer. So when the guard is unavailable (or raises), the
correct degradation is "no fence": keep streaming. These helpers make the
claim/check best-effort to guarantee that.

### 顶层函数

#### def `claim_stream_writer(agent: Any) -> int`

Claim the delta sink for the calling stream attempt, best-effort.

Returns the agent's monotonic writer token when the fence is available, or
``0`` when the agent doesn't expose it (or the claim raised). A ``0`` token
pairs with :func:`stream_writer_is_current` always returning ``True``, so a
guard-less agent is simply never fenced instead of crashing the turn.

#### def `stream_writer_is_current(agent: Any, token: int) -> bool`

True when ``token`` is still the active writer, best-effort.

A falsy token (from a claim that no-oped) or an agent without the fence
means we cannot prove supersession, so the stream is treated as current and
never fenced. This preserves the single-writer invariant's one-way promise:
only a demonstrably stale writer is ever stopped.


## agent.subdirectory_hints

### 模块文档

Progressive subdirectory hint discovery.

As the agent navigates into subdirectories via tool calls (read_file, terminal,
search_files, etc.), this module discovers and loads project context files
(AGENTS.md, CLAUDE.md, .cursorrules) from those directories.  Discovered hints
are appended to the tool result so the model gets relevant context at the moment
it starts working in a new area of the codebase.

This complements the startup context loading in ``prompt_builder.py`` which only
loads from the CWD.  Subdirectory hints are discovered lazily and injected into
the conversation without modifying the system prompt (preserving prompt caching).

Inspired by Block/goose's SubdirectoryHintTracker.

### class SubdirectoryHintTracker

> 继承: `object` ｜ 方法数: 7（公开 1）

Track which directories the agent visits and load hints on first access.

Usage::

    tracker = SubdirectoryHintTracker(working_dir="/path/to/project")

    # After each tool call:
    hints = tracker.check_tool_call("read_file", {"path": "backend/src/main.py"})
    if hints:
        tool_result += hints  # append to the tool result string

#### def `__init__(working_dir: Optional[str] = None)`

#### def `check_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Optional[str]`

Check tool call arguments for new directories and load any hint files.

Returns formatted hint text to append to the tool result, or None.


## agent.subscription_view

### 模块文档

Surface-agnostic core for the ``/subscription`` TUI screen.

Companion to :mod:`agent.billing_view` — same fail-open philosophy: when not
logged in or the portal is unreachable, return a struct with ``logged_in=False``
and let the surface degrade gracefully (never crash). Money is decimal end-to-end
(server emits decimal strings); we only format for display.

The TUI ``SubscriptionOverlay`` drives the plan change in-terminal (V3): it
previews the effect, then schedules a downgrade / cancellation / resume
(chargeless) or applies an upgrade (charges the card on the subscription). The
portal deep-link (built locally from ``portal_url`` + ``org_id``) remains the
fallback for an upgrade that needs 3DS / was declined.

WS1 dependency: ``GET /api/billing/subscription`` is a NAS endpoint (WS1 Phase A).
Until it ships, the fail-open contract handles 404s — the builder returns
``logged_in=False`` and the surface degrades gracefully.

### class CurrentSubscription

> 继承: `object` ｜ 方法数: 0（公开 0）

The user's active subscription. ``None`` (not this object) = no plan.

When present, ``tier_id`` / ``tier_name`` / ``monthly_credits`` /
``cycle_ends_at`` are always set (NAS guarantees a present ``current`` is a
fully-populated plan). Only ``credits_remaining`` and the cancel/downgrade
fields are optional.


### class SubscriptionTier

> 继承: `object` ｜ 方法数: 0（公开 0）

A selectable plan in the catalog — one row of the in-terminal tier picker.

Mirrors NAS's ``SubscriptionTierOption``. ``is_current`` marks the active plan
(shown but not selectable); ``is_enabled=False`` is a grandfathered tier the
user is on but that can no longer be selected. ``tier_order`` sorts the picker
and drives the upgrade-vs-downgrade direction hint.


### class SubscriptionChangePreview

> 继承: `object` ｜ 方法数: 0（公开 0）

Parsed ``POST /api/billing/subscription/preview`` — what a change would do.

``effect`` is the disposition the commit would take:
  - ``charge_now`` → an upgrade; ``amount_due_now_cents`` is the prorated charge.
  - ``scheduled``  → a downgrade / same-price change at ``effective_at`` (period end).
  - ``no_op``      → already on the target tier.
  - ``blocked``    → the commit would be refused; ``reason`` says why.


### class SubscriptionState

> 继承: `object` ｜ 方法数: 2（公开 2）

Parsed ``GET /api/billing/subscription`` — the overview screen's data.

Fail-open: ``logged_in=False`` (and empty fields) when not logged in or the
portal is unreachable.

#### property `is_admin(self) -> bool`

Deprecated/display only — a legacy OWNER/ADMIN check.

NOT a capability check; use :attr:`can_change_plan` for gating billing
plan-change actions.

#### property `can_change_plan(self) -> bool`

Server capability when supplied; otherwise the legacy role fallback.


### 顶层函数

#### def `subscription_change_preview_from_payload(payload: dict[str, Any]) -> SubscriptionChangePreview`

Map a raw ``/subscription/preview`` JSON dict into :class:`SubscriptionChangePreview`.

#### def `subscription_state_from_payload(payload: dict[str, Any], portal_url: Optional[str] = None) -> SubscriptionState`

Map a raw ``/api/billing/subscription`` JSON dict into :class:`SubscriptionState`.

#### def `build_subscription_state(timeout: float = 15.0) -> SubscriptionState`

Fetch + parse ``GET /api/billing/subscription``. Fail-open.

Returns ``SubscriptionState(logged_in=False)`` when not logged in. On a
portal/HTTP failure, returns ``logged_in=False`` with ``error`` set so the
surface can show a clear message rather than crashing.

Dev override: when ``HERMES_DEV_SUBSCRIPTION_FIXTURE`` names a fixture state,
``/subscription`` renders from that fixture instead of the real portal — so
every plan/cancel/downgrade/team/not-admin state is testable on both
the CLI and TUI without a live account. Throwaway scaffolding; see
:func:`dev_fixture_subscription_state`.

#### def `subscription_manage_url(state: SubscriptionState) -> Optional[str]`

Build ``{portal_origin}/manage-subscription?org_id=<id>`` from a state.

Mirrors the TUI's ``buildManageUrl`` (``subscription.ts``): the deep-link
target is NAS's OWN ``/manage-subscription`` page (NOT the Stripe Billing
Portal — decided Jun 23), which routes upgrade→Checkout / downgrade→scheduled
internally. ``org_id`` pins the page to the right account in multi-org
situations. Returns ``None`` when no portal URL is resolvable.

#### def `dev_fixture_subscription_state() -> Optional[SubscriptionState]`

Return a fixture :class:`SubscriptionState` for ``HERMES_DEV_SUBSCRIPTION_FIXTURE``.

Lets every CLI/TUI subscription state be exercised without a live portal:

    free | mid | top | not-admin | downgrade | cancel | team |
    logged-out

Returns ``None`` when the env var is unset/empty (the real portal path runs).
Throwaway scaffolding — mirrors ``HERMES_DEV_CREDITS_FIXTURE``.


## agent.system_prompt

### 模块文档

System-prompt assembly for :class:`AIAgent`.

The agent's system prompt is built once per session and reused across all
turns — only context compression triggers a rebuild.  This keeps the
upstream prefix cache warm.  See ``hermes-agent-dev``'s
``references/system-prompt-invariant.md`` for the invariants and
``references/self-improvement-loop.md`` for how the background-review
fork inherits the cached prompt verbatim.

Three tiers are joined with ``\n\n``:

* ``stable``   — identity (SOUL.md or DEFAULT_AGENT_IDENTITY), tool
  guidance, computer-use guidance, nous subscription block, tool-use
  enforcement guidance + per-model operational guidance, skills prompt,
  alibaba model-name workaround, environment hints, platform hints.
* ``context``  — caller-supplied ``system_message`` plus context files
  (AGENTS.md / .cursorrules / etc.) discovered under ``TERMINAL_CWD``.
* ``volatile`` — memory snapshot, USER.md profile, external memory
  provider block, timestamp/session/model/provider line.

Pure helpers that read the agent's state.  AIAgent keeps thin forwarders.

### 顶层函数

#### def `build_system_prompt_parts(agent: Any, system_message: Optional[str] = None) -> Dict[str, str]`

Assemble the system prompt as three ordered parts.

Returns a dict with three keys:
  * ``stable``   — identity, tool guidance, skills prompt,
    environment hints, platform hints, model-family operational
    guidance.
  * ``context``  — context files (AGENTS.md, .cursorrules, etc.)
    and caller-supplied system_message.
  * ``volatile`` — memory snapshot, user profile, external
    memory provider block, timestamp line.

Joined into a single string by :func:`build_system_prompt` and
cached on ``agent._cached_system_prompt`` for the lifetime of the
AIAgent.  Hermes never re-renders parts of this string mid-
session — that's the only way to keep upstream prompt caches
warm across turns.

#### def `build_system_prompt(agent: Any, system_message: Optional[str] = None) -> str`

Assemble the full system prompt from all layers.

Called once per session (cached on ``agent._cached_system_prompt``) and
only rebuilt after context compression events. This ensures the system
prompt is stable across all turns in a session, maximizing prefix cache
hits.

Layers are ordered cache-friendly: stable identity/guidance first,
then session-stable context files, then per-call volatile content
(memory, USER profile, timestamp).  The whole string is treated as
one cached block — Hermes never rebuilds or reinjects parts of it
mid-session, which is the only way to keep upstream prompt caches
warm across turns.

#### def `invalidate_system_prompt(agent: Any) -> None`

Invalidate the cached system prompt, forcing a rebuild on the next turn.

Called after context compression events. Also reloads memory from disk
so the rebuilt prompt captures any writes from this session.

#### def `format_tools_for_system_message(agent: Any) -> str`

Format tool definitions for the system message in the trajectory format.

Returns:
    str: JSON string representation of tool definitions


## agent.think_scrubber

### 模块文档

Stateful scrubber for reasoning/thinking blocks in streamed assistant text.

``run_agent._strip_think_blocks`` is regex-based and correct for a complete
string, but when it runs *per-delta* in ``_fire_stream_delta`` it destroys
the state that downstream consumers (CLI ``_stream_delta``, gateway
``GatewayStreamConsumer._filter_and_accumulate``) rely on.

Concretely, when MiniMax-M2.7 streams

    delta1 = "<think>"
    delta2 = "Let me check their config"
    delta3 = "</think>"

the per-delta regex erases delta1 entirely (case 2: unterminated-open at
boundary matches ``^<think>...``), so the downstream state machine never
sees the open tag, treats delta2 as regular content, and leaks reasoning
to the user.  Consumers that don't run their own state machine (ACP,
api_server, TTS) never had any defence at all — they just emitted
whatever survived the upstream regex.

This module centralises the tag-suppression state machine at the
upstream layer so every stream_delta_callback sees text that has
already had reasoning blocks removed.  Partial tags at delta
boundaries are held back until the next delta resolves them, and
end-of-stream flushing surfaces any held-back prose that turned out
not to be a real tag.

Usage::

    scrubber = StreamingThinkScrubber()
    for delta in stream:
        visible = scrubber.feed(delta)
        if visible:
            emit(visible)
    tail = scrubber.flush()  # at end of stream
    if tail:
        emit(tail)

The scrubber is re-entrant per agent instance.  Call ``reset()`` at
the top of each new turn so a hung block from an interrupted prior
stream cannot taint the next turn's output.

Tag variants handled (case-insensitive):
  ``<think>``, ``<thinking>``, ``<reasoning>``, ``<thought>``,
  ``<REASONING_SCRATCHPAD>``.

Block-boundary rule for opens: an opening tag is only treated as a
reasoning-block opener when it appears at the start of the stream,
after a newline (optionally followed by whitespace), or when only
whitespace has been emitted on the current line.  This prevents prose
that *mentions* the tag name (e.g. ``"use <think> tags here"``) from
being incorrectly suppressed.  Closed pairs (``<think>X</think>``) are
always suppressed regardless of boundary; a closed pair is an
intentional, bounded construct.

### class StreamingThinkScrubber

> 继承: `object` ｜ 方法数: 10（公开 3）

Stateful scrubber for streaming reasoning/thinking blocks.

State machine:
  - ``_in_block``: True while inside an opened block, waiting for
    a close tag.  All text inside is discarded.
  - ``_buf``: held-back partial-tag tail.  Emitted / discarded on
    the next ``feed()`` call or by ``flush()``.
  - ``_last_emitted_ended_newline``: True iff the most recent
    emission to the consumer ended with ``\n``, or nothing has
    been emitted yet (start-of-stream counts as a boundary).  Used
    to decide whether an open tag at buffer position 0 is at a
    block boundary.

#### def `__init__() -> None`

#### def `reset(self) -> None`

Reset all state.  Call at the top of every new turn.

#### def `feed(self, text: str) -> str`

Feed one delta; return the scrubbed visible portion.

May return an empty string when the entire delta is reasoning
content or is being held back pending resolution of a partial
tag at the boundary.

#### def `flush(self) -> str`

End-of-stream flush.

If still inside an unterminated block, held-back content is
discarded — leaking partial reasoning is worse than a
truncated answer.  Otherwise the held-back partial-tag tail is
emitted verbatim (it turned out not to be a real tag prefix).

Always treats the next ``feed()`` as a fresh stream boundary.
Intra-turn retries (thinking-only prefill, empty-response
retry) flush then stream again without calling ``reset()``;
leaving ``_last_emitted_ended_newline`` False made a new
stream's opening ``<think>`` look mid-line and leak into the
visible reply.


## agent.thinking_timeout_guidance

### 模块文档

Thinking-timeout detection and user-facing guidance for reasoning models.

When a known reasoning model (NVIDIA Nemotron 3 Ultra, OpenAI o1/o3,
Anthropic Opus 4.x thinking, DeepSeek R1, Qwen QwQ, xAI Grok reasoning)
hits a transport-layer error before the first content token arrives, the
upstream proxy has almost certainly idle-killed a long thinking stream —
not a true context overflow or a configuration error.  The user needs
distinct guidance for this case:

    "The model's thinking phase exceeded the upstream proxy's idle
     timeout before the first content token arrived.  This is a known
     issue with reasoning models behind cloud gateways (NVIDIA NIM,
     OpenAI, Anthropic, DeepSeek).  Workarounds in priority order:
     1. Set `providers.<provider>.models.<model>.stale_timeout_seconds: 900`
        in `~/.hermes/config.yaml` to extend the per-call timeout...
     2. Lower `reasoning_budget` or set `reasoning_effort: medium`...
     3. Use a smaller / faster reasoning model..."

The existing `_is_stream_drop` guidance at
``agent/conversation_loop.py:3464-3486`` fires for large-file-write
stream drops ("try execute_code with Python's open() for large files")
which is the WRONG advice for the thinking-timeout case.  This module
provides the detection and the message as standalone helpers so the
detection logic is unit-testable without driving the full retry loop,
and the message text can be regression-tested for spelling and accuracy.

Part 2 of Fixes #52310.

### 顶层函数

#### def `is_thinking_timeout(classified: object, model: str, error_msg: str) -> bool`

Return True when a reasoning model's thinking phase hit a transport kill.

Args:
    classified: a :class:`agent.error_classifier.ClassifiedError` instance
        (duck-typed here to avoid an import cycle in unit tests).
    model: the model slug at failure time (e.g.
        ``"nvidia/nemotron-3-ultra-550b-a55b"``).
    error_msg: lowercased string representation of the underlying
        exception (typically ``str(api_error).lower()``).

Returns True when ALL conditions hold:
    1. ``classified.reason == FailoverReason.timeout`` (the classifier
       override at ``agent/error_classifier.py:720-738`` ensures this
       is the case for reasoning models even on large sessions).
    2. ``api_error`` has no ``.status_code`` attribute set (transport
       disconnect, not an HTTP error).
    3. ``model`` is in the reasoning-model allowlist (reuses
       ``agent.reasoning_timeouts.get_reasoning_stale_timeout_floor``).
    4. ``error_msg`` contains one of the transport-kill substrings.

Non-reasoning models always return False.  Non-transport errors
(billing / rate_limit / auth / context_overflow / format_error)
always return False.  HTTP-status errors always return False.

#### def `build_thinking_timeout_guidance(provider: str, model: str, model_label: Optional[str] = None) -> str`

Return the user-facing guidance string appended to ``_final_response``.

Args:
    provider: provider slug (e.g. ``"nvidia"``, ``"openai"``).
    model: bare model slug the user would put in their config
        (e.g. ``"nemotron-3-ultra-550b-a55b"`` if the user uses
        NVIDIA direct, or the full ``"nvidia/nemotron-3-ultra-550b-a55b"``
        if they go through an aggregator).  Used verbatim in the
        config snippet so the user can copy-paste.
    model_label: optional short label for the model name in the
        prose (e.g. ``"Nemotron 3 Ultra"``).  Falls back to the
        slug if not provided.


## agent.thread_scoped_output

### 模块文档

Thread-scoped stdout/stderr silencing for background worker threads.

``contextlib.redirect_stdout``/``redirect_stderr`` reassign the *process-global*
``sys.stdout``/``sys.stderr``.  When a daemon worker thread (e.g. the background
memory/skill review) wraps its whole body in those context managers, every other
thread in the process — including a gateway's asyncio event-loop thread driving a
Telegram long-poll — sees ``sys.stdout``/``sys.stderr`` pointing at ``devnull``
for the full duration.  Any bare ``print`` / ``sys.stderr.write`` from those other
threads is silently lost during that window (see issue #55769 / #55925).

This module installs a thin proxy as ``sys.stdout``/``sys.stderr`` that routes
writes per-thread: threads registered as "silenced" go to a sink; every other
thread passes through to the *original* stream.  The proxy is installed once,
idempotently, and is never uninstalled (uninstalling would race other threads
mid-write), so the only observable effect for unregistered threads is one extra
attribute lookup per write.

### 顶层函数

#### def `thread_scoped_silence() -> Iterator[None]`

Silence ``stdout``/``stderr`` for the *current thread only*.

Other threads keep writing to the real streams.  Use this around a worker
thread's body instead of ``contextlib.redirect_stdout(devnull)`` when the
process is multi-threaded and another thread must keep its console output.


## agent.title_generator

### 模块文档

Auto-generate short session titles from the first user/assistant exchange.

Runs asynchronously after the first response is delivered so it never
adds latency to the user-facing reply.

### 顶层函数

#### def `generate_title(user_message: str, assistant_response: str, timeout: Optional[float] = None, failure_callback: Optional[FailureCallback] = None, main_runtime: dict = None, runtime_validator: Optional[RuntimeValidator] = None) -> Optional[str]`

Generate a session title from the first exchange.

Uses the main runtime's model when available, falling back to the
auxiliary LLM client (cheapest/fastest available model).
Returns the title string or None on failure.

``failure_callback`` is invoked with ``(task, exception)`` when the
auxiliary call raises — the caller typically wires this to
``AIAgent._emit_auxiliary_failure`` so the user sees a warning instead
of silently accumulating untitled sessions.

``runtime_validator`` is called right before the LLM request. If it
returns False (e.g. the user's model was switched since the background
thread captured its runtime snapshot), the call is skipped silently —
no request is sent, so a stale title request can't reload a model the
runtime already unloaded (#19027).

#### def `auto_title_session(session_db, session_id: str, user_message: str, assistant_response: str, failure_callback: Optional[FailureCallback] = None, main_runtime: dict = None, title_callback: Optional[TitleCallback] = None, runtime_validator: Optional[RuntimeValidator] = None) -> None`

Generate and set a session title if one doesn't already exist.

Called in a background thread after the first exchange completes.
Silently skips if:
- session_db is None
- session already has a title (user-set or previously auto-generated)
- title generation fails
- runtime_validator returns False (model was switched)

Never lets an exception escape: this is a daemon-thread target, and an
escaping exception would spray a raw traceback into the user's terminal
via the default threading excepthook. The canonical trigger is the
post-``hermes update`` stale-module window, where this function's lazy
imports read NEW source from disk while already-cached modules
(``agent.portal_tags`` etc.) are still the OLD version — the resulting
ImportError repeats on every auto-title attempt until the long-running
process restarts.

#### def `maybe_auto_title(session_db, session_id: str, user_message: str, assistant_response: str, conversation_history: list, failure_callback: Optional[FailureCallback] = None, main_runtime: dict = None, title_callback: Optional[TitleCallback] = None, runtime_validator: Optional[RuntimeValidator] = None) -> None`

Fire-and-forget title generation after the first exchange.

Only generates a title when:
- This appears to be the first user→assistant exchange
- No title is already set


## agent.tool_dispatch_helpers

### 模块文档

Tool-dispatch helpers — parallelism gating, multimodal envelopes, mutation tracking.

Pure module-level utilities extracted from ``run_agent.py``:

* ``_is_destructive_command`` — terminal-command heuristic used to gate
  parallel batch dispatch.
* ``_should_parallelize_tool_batch`` / ``_extract_parallel_scope_path`` /
  ``_paths_overlap`` — the rules engine deciding when a multi-tool batch
  can run concurrently.
* ``_is_multimodal_tool_result`` / ``_multimodal_text_summary`` /
  ``_append_subdir_hint_to_multimodal`` — envelope helpers for the
  ``{"_multimodal": True, "content": [...], "text_summary": ...}`` dict
  shape returned by tools like ``computer_use``.
* ``_extract_file_mutation_targets`` / ``_extract_landed_file_mutation_paths`` /
  ``_extract_error_preview`` —
  per-turn file-mutation verifier inputs.
* ``_trajectory_normalize_msg`` — strip image blobs from a message for
  trajectory saving.

All helpers are stateless.  ``run_agent`` re-exports each name so existing
``from run_agent import ...`` imports in tests and other modules keep
working unchanged.

### 顶层函数

#### def `make_tool_result_message(name: str, content: Any, tool_call_id: str, effect_disposition: str | None = None) -> dict`

Build a tool-result message dict with both the OpenAI-format ``name``
field (required by the wire format and provider adapters) and the internal
``tool_name`` field (written to the session DB messages table).

Content from high-risk tools (``web_extract``, ``web_search``, ``browser_*``,
``mcp_*``) gets wrapped in semantic delimiters telling the model the content
is untrusted data, not instructions.  This is the architectural defense
against indirect prompt injection from poisoned web pages, GitHub issues,
and MCP responses — it changes how the model interprets the content rather
than relying on regex pattern matching catching every payload.

Wrapping applies to plain string content and to multimodal content
lists (``[{"type": "text", "text": "..."}, {"type": "image_url", ...}]``):
each text-type part is wrapped individually using the same rules as plain
string content (short text passes through unchanged; longer text is
neutralized and framed). Non-text parts (e.g. image_url) are preserved.
The outer list itself is rebuilt rather than returned by identity, so
callers should compare by value, not by ``is``.


## agent.tool_executor

### 模块文档

Tool-call execution — sequential and concurrent dispatch.

Both AIAgent methods (``_execute_tool_calls_sequential`` and
``_execute_tool_calls_concurrent``) live here as module-level
functions that take the parent ``AIAgent`` as their first argument.

``run_agent`` keeps thin wrappers so existing call sites work; tests
that patch ``run_agent._set_interrupt`` are honored because the
extracted functions reach back through the ``run_agent`` module via
``_ra()`` for that symbol.

### 顶层函数

#### def `execute_tool_calls_concurrent(agent, assistant_message, messages: list, effective_task_id: str, api_call_count: int = 0, finalize: bool = True) -> None`

Execute multiple tool calls concurrently using a thread pool.

Results are collected in the original tool-call order and appended to
messages so the API sees them in the expected sequence.

``finalize=False`` skips the end-of-batch aggregate budget enforcement
and /steer injection — used when this call is one segment of a larger
mixed batch and the segmented dispatcher owns the turn-end work.

#### def `execute_tool_calls_sequential(agent, assistant_message, messages: list, effective_task_id: str, api_call_count: int = 0, finalize: bool = True) -> None`

Execute tool calls sequentially (original behavior). Used for single calls or interactive tools.

``finalize=False`` skips the end-of-batch aggregate budget enforcement
and /steer injection — used when this call is one segment of a larger
mixed batch and the segmented dispatcher owns the turn-end work.

#### def `execute_tool_calls_segmented(agent, assistant_message, messages: list, effective_task_id: str, api_call_count: int = 0, segments = None) -> None`

Execute a mixed tool-call batch as ordered parallel/sequential segments.

``segments`` is the ``(kind, calls)`` plan from
``_plan_tool_batch_segments``: maximal contiguous runs of parallel-safe
calls execute on the concurrent path, barrier calls on the sequential
path, strictly in the model's original call order. Because segments are
contiguous, every tool result is still appended one-per-call in emission
order and no call ever starts before an earlier barrier finishes —
identical ordering and side-effect boundaries to fully-sequential
execution, with I/O parallelism recovered inside the safe runs.

Turn-end work (aggregate budget enforcement + /steer injection) is done
once here for the WHOLE batch; the per-segment executor calls run with
``finalize=False`` so a multi-segment turn cannot multiply the budget or
truncate a steer marker.

Interrupt semantics: each segment executor already checks
``agent._interrupt_requested`` up front and appends a cancelled/skipped
result per call, so an interrupt during segment *k* drains segments
*k+1..n* without executing them while preserving one result per
tool_call_id.


## agent.tool_guardrails

### 模块文档

Pure tool-call loop guardrail primitives.

The controller in this module is intentionally side-effect free: it tracks
per-turn tool-call observations and returns decisions. Runtime code owns whether
those decisions become warning guidance, synthetic tool results, or controlled
turn halts.

### class ToolCallGuardrailConfig

> 继承: `object` ｜ 方法数: 1（公开 1）

Thresholds for per-turn tool-call loop detection.

Warnings are enabled by default and never prevent tool execution. Hard stops
are explicit opt-in so interactive CLI/TUI sessions get a gentle nudge unless
the user enables circuit-breaker behavior in config.yaml.

#### classmethod `from_mapping(cls, data: Mapping[str, Any] | None) -> ToolCallGuardrailConfig`

Build config from the `tool_loop_guardrails` config.yaml section.


### class ToolCallSignature

> 继承: `object` ｜ 方法数: 2（公开 2）

Stable, non-reversible identity for a tool name plus canonical args.

#### classmethod `from_call(cls, tool_name: str, args: Mapping[str, Any] | None) -> ToolCallSignature`

#### def `to_metadata(self) -> dict[str, str]`

Return public metadata without raw argument values.


### class ToolGuardrailDecision

> 继承: `object` ｜ 方法数: 3（公开 3）

Decision returned by the tool-call guardrail controller.

#### property `allows_execution(self) -> bool`

#### property `should_halt(self) -> bool`

#### def `to_metadata(self) -> dict[str, Any]`


### class ToolCallGuardrailController

> 继承: `object` ｜ 方法数: 6（公开 4）

Per-turn controller for repeated failed/non-progressing tool calls.

#### def `__init__(config: ToolCallGuardrailConfig | None = None)`

#### def `reset_for_turn(self) -> None`

#### property `halt_decision(self) -> ToolGuardrailDecision | None`

#### def `before_call(self, tool_name: str, args: Mapping[str, Any] | None) -> ToolGuardrailDecision`

#### def `after_call(self, tool_name: str, args: Mapping[str, Any] | None, result: str | None, failed: bool | None = None) -> ToolGuardrailDecision`


### 顶层函数

#### def `canonical_tool_args(args: Mapping[str, Any]) -> str`

Return sorted compact JSON for parsed tool arguments.

**异常**: `TypeError`

#### def `classify_tool_failure(tool_name: str, result: str | None) -> tuple[bool, str]`

Safety-fallback classifier used only when callers don't pass ``failed``.

Mirrors ``agent.display._detect_tool_failure`` exactly so the guardrail
never disagrees with the CLI's user-visible ``[error]`` tag. Production
callers in ``run_agent.py`` always pass an explicit ``failed=`` derived
from ``_detect_tool_failure``; this function exists so standalone callers
(tests, tooling) still get consistent behavior.

#### def `toolguard_synthetic_result(decision: ToolGuardrailDecision) -> str`

Build a synthetic role=tool content string for a blocked tool call.

#### def `append_toolguard_guidance(result: str, decision: ToolGuardrailDecision) -> str`

Append runtime guidance to the current tool result content.


## agent.tool_result_classification

### 模块文档

Shared helpers for classifying tool result payloads.

### 顶层函数

#### def `tool_may_have_side_effect(tool_name: str) -> bool`

#### def `file_mutation_result_landed(tool_name: str, result: Any) -> bool`

Return True when a file mutation result proves the write landed.


## agent.trace_upload

### 模块文档

Upload a Hermes session transcript to Hugging Face as an agent trace.

Hermes stores sessions in its own SQLite store (``hermes_state.SessionDB``),
so we reconstruct the conversation and emit it in the **Claude Code JSONL**
shape — one of the three formats the Hugging Face Agent Trace Viewer
auto-detects (Claude Code / Codex / Pi). No dataset-side preprocessing is
needed; the Hub tags the dataset ``agent-traces`` and opens it in the viewer.

Docs: https://huggingface.co/docs/hub/agent-traces

Design notes
------------
* **Zero LLM turn.** This is a deterministic export — it never spends a
  model call. The ``hermes trace upload`` subcommand calls
  :func:`upload_session_trace` directly.
* **Private by default.** Traces can contain prompts, tool output, local
  paths, and secrets. The dataset is created private and every text body
  is passed through Hermes' secret redactor (``force=True``) unless the
  caller explicitly opts out with ``redact=False``.
* **Never raises.** Returns a user-facing status string so command
  handlers can echo it straight back to the user. Programmatic callers
  that need the URL can use :func:`build_trace_jsonl` + :func:`_do_upload`
  directly.

### class TraceRedactionError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when a trace cannot be safely redacted before upload.


### 顶层函数

#### def `build_trace_jsonl(messages: List[Dict[str, Any]], session_id: str, model: str = '', cwd: str = '', redact: bool = True) -> str`

Render Hermes conversation messages as Claude Code JSONL text.

Each non-system message becomes one JSONL line in the Claude Code
transcript shape the HF Agent Trace Viewer auto-detects:

* ``user`` / ``tool`` -> ``{"type": "user", "message": {...}}``
* ``assistant``       -> ``{"type": "assistant", "message": {...}}``
  with ``content`` blocks (text + ``tool_use``).

Tool results are emitted as user turns carrying a ``tool_result``
block keyed by ``tool_call_id`` — the same way Claude Code records
them. Turns are linked via ``uuid`` / ``parentUuid``.

#### def `load_session_messages(session_id: str, db_path = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]`

Load a session's conversation + metadata from the SQLite store.

Returns ``(messages, meta)``. ``meta`` is ``{}`` when the session row is
missing (messages may still be present for a live, untitled session).

#### def `upload_session_trace(session_id: str, model: str = '', cwd: str = '', redact: bool = True, private: bool = True, dataset_name: str = DEFAULT_DATASET_NAME, db_path = None, token: Optional[str] = None) -> str`

Top-level entry point used by the CLI/gateway/subcommand.

Loads the session, converts it to Claude Code JSONL, and uploads it to
the user's private ``{user}/hermes-traces`` dataset. Returns a
user-facing status string and never raises.


## agent.trajectory

### 模块文档

Trajectory saving utilities and static helpers.

_convert_to_trajectory_format stays as an AIAgent method (batch_runner.py
calls agent._convert_to_trajectory_format). Only the static helpers and
the file-write logic live here.

### 顶层函数

#### def `convert_scratchpad_to_think(content: str) -> str`

Convert <REASONING_SCRATCHPAD> tags to <think> tags.

#### def `has_incomplete_scratchpad(content: str) -> bool`

Check if content has an opening <REASONING_SCRATCHPAD> without a closing tag.

#### def `save_trajectory(trajectory: List[Dict[str, Any]], model: str, completed: bool, filename: str = None)`

Append a trajectory entry to a JSONL file.

Args:
    trajectory: The ShareGPT-format conversation list.
    model: Model name for metadata.
    completed: Whether the conversation completed successfully.
    filename: Override output filename. Defaults to trajectory_samples.jsonl
              or failed_trajectories.jsonl based on ``completed``.


## agent.transcription_provider

### 模块文档

Transcription Provider ABC
==========================

Defines the pluggable-backend interface for speech-to-text. Providers
register instances via
:meth:`PluginContext.register_transcription_provider`; the active one
(selected via ``stt.provider`` in ``config.yaml``) services every
:func:`tools.transcription_tools.transcribe_audio` call **when the
configured name is neither a built-in (``local``, ``local_command``,
``groq``, ``openai``, ``mistral``, ``xai``) nor disabled**.

Two coexisting STT extension surfaces — in resolution order:

1. **Built-in providers** (``BUILTIN_STT_PROVIDERS`` in
   :mod:`tools.transcription_tools`) — native Python implementations
   for the 6 backends shipped today (faster-whisper, local_command,
   Groq, OpenAI, Mistral, xAI). **Always win** — plugins cannot
   shadow them. The single-env-var shell escape hatch
   ``HERMES_LOCAL_STT_COMMAND`` is preserved via the built-in
   ``local_command`` path.
2. **Plugin-registered providers** (this ABC). For new STT backends —
   OpenRouter, SenseAudio, Gemini-STT, custom proprietary engines —
   that need a Python implementation without modifying
   ``tools/transcription_tools.py``.

Built-ins-always-win is enforced at registration time
(:func:`agent.transcription_registry.register_provider` rejects names
in ``BUILTIN_STT_PROVIDERS`` with a warning) AND at dispatch time
(:func:`tools.transcription_tools._dispatch_to_plugin_provider`
re-checks defensively).

Providers live in ``<repo>/plugins/transcription/<name>/`` (built-in
plugins, none shipped today) or
``~/.hermes/plugins/transcription/<name>/`` (user-installed).

Response contract
-----------------
:meth:`TranscriptionProvider.transcribe` returns a dict with keys::

    success      bool
    transcript   str       transcribed text (empty when success=False)
    provider     str       provider name (for diagnostics)
    error        str       only when success=False

### class TranscriptionProvider

> 继承: `abc.ABC` ｜ 方法数: 7（公开 7）

Abstract base class for a speech-to-text backend.

Subclasses must implement :attr:`name` and :meth:`transcribe`.
Everything else has sane defaults — override only what your provider
needs.

#### property `name(self) -> str`

Stable short identifier used in ``stt.provider`` config.

Lowercase, no spaces. Examples: ``openrouter``, ``sensaudio``,
``gemini``, ``deepgram``. Names that collide with a built-in STT
provider (``local``, ``local_command``, ``groq``, ``openai``,
``mistral``, ``xai``) are rejected at registration time.

#### property `display_name(self) -> str`

Human-readable label shown in ``hermes tools``.

Defaults to ``name.title()``.

#### def `is_available(self) -> bool`

Return True when this provider can service calls.

Typically checks for a required API key + that the SDK is
importable. Default: True (providers with no external
dependencies are always available).

Must NOT raise — used by the picker and ``hermes setup`` for
availability displays and should fail gracefully.

#### def `list_models(self) -> List[Dict[str, Any]]`

Return model catalog entries.

Each entry::

    {
        "id": "whisper-large-v3-turbo",  # required
        "display": "Whisper Large v3 Turbo",   # optional
        "languages": ["en", "es", "fr"],        # optional
        "max_audio_seconds": 1500,              # optional
    }

Default: empty list (provider has a single fixed model or
doesn't expose model selection).

#### def `default_model(self) -> Optional[str]`

Return the default model id, or None if not applicable.

#### def `get_setup_schema(self) -> Dict[str, Any]`

Return provider metadata for the ``hermes tools`` picker.

Used by ``tools_config.py`` to inject this provider as a row in
the Speech-to-Text provider list. Shape::

    {
        "name": "OpenRouter STT",              # picker label
        "badge": "paid",                       # optional short tag
        "tag": "Whisper via OpenRouter API",   # optional subtitle
        "env_vars": [                          # keys to prompt for
            {"key": "OPENROUTER_API_KEY",
             "prompt": "OpenRouter API key",
             "url": "https://openrouter.ai/keys"},
        ],
    }

Default: minimal entry derived from ``display_name`` with no
env vars. Override to expose API key prompts and custom badges.

#### def `transcribe(self, file_path: str, model: Optional[str] = None, language: Optional[str] = None, **extra: Any) -> Dict[str, Any]`

Transcribe the audio file at ``file_path``.

Returns a dict with the standard envelope::

    {
        "success": True,
        "transcript": "the transcribed text",
        "provider": "<this provider's name>",
    }

or on failure::

    {
        "success": False,
        "transcript": "",
        "error": "human-readable error message",
        "provider": "<this provider's name>",
    }

Implementations should NOT raise — convert exceptions to the
error envelope so the dispatcher can deliver a consistent shape
to the gateway/CLI caller.

Args:
    file_path: Absolute path to the audio file. The dispatcher
        has already validated existence + size before calling.
    model: Model identifier from :meth:`list_models`, or None
        to use :meth:`default_model`.
    language: Optional BCP-47 language hint (e.g. ``"en"``,
        ``"ja"``) — providers without language hints should
        ignore this argument.
    **extra: Forward-compat parameters future schema versions
        may expose. Implementations should ignore unknown keys.


## agent.transcription_registry

### 模块文档

Transcription Provider Registry
================================

Central map of registered STT providers. Populated by plugins at
import-time via :meth:`PluginContext.register_transcription_provider`;
consumed by :mod:`tools.transcription_tools` to dispatch
:func:`transcribe_audio` calls to the active plugin backend **when**
the configured ``stt.provider`` name is not a built-in.

Built-ins-always-win
--------------------
Plugin names that collide with a built-in STT provider (``local``,
``local_command``, ``groq``, ``openai``, ``mistral``, ``xai``) are
rejected at registration with a warning. This invariant is also
re-checked at dispatch time in
:func:`tools.transcription_tools._dispatch_to_plugin_provider`.

### 顶层函数

#### def `register_provider(provider: TranscriptionProvider) -> None`

Register a transcription provider.

Rejects:

- Non-:class:`TranscriptionProvider` instances (raises :class:`TypeError`).
- Empty/whitespace ``.name`` (raises :class:`ValueError`).
- Names colliding with a built-in (logs a warning, silently
  ignores — built-ins-always-win invariant).

Re-registration (same ``name``) overwrites the previous entry and
logs a debug message — makes hot-reload scenarios (tests, dev
loops) behave predictably.

**异常**: `class`, `TypeError`, `ValueError`

#### def `list_providers() -> List[TranscriptionProvider]`

Return all registered providers, sorted by name.

#### def `get_provider(name: str) -> Optional[TranscriptionProvider]`

Return the provider registered under *name*, or None.

Name matching is case-insensitive and whitespace-tolerant — mirrors
how ``tools.transcription_tools._get_provider`` normalizes the
configured ``stt.provider`` value.


## agent.transports.__init__

### 模块文档

Transport layer types and registry for provider response normalization.

Usage:
    from agent.transports import get_transport
    transport = get_transport("anthropic_messages")
    result = transport.normalize_response(raw_response)

### 顶层函数

#### def `register_transport(api_mode: str, transport_cls: type) -> None`

Register a transport class for an api_mode string.

#### def `get_transport(api_mode: str)`

Get a transport instance for the given api_mode.

Returns None if no transport is registered for this api_mode.
This allows gradual migration — call sites can check for None
and fall back to the legacy code path.


## agent.transports.anthropic

### 模块文档

Anthropic Messages API transport.

Delegates to the existing adapter functions in agent/anthropic_adapter.py.
This transport owns format conversion and normalization — NOT client lifecycle.

### class AnthropicTransport

> 继承: `ProviderTransport` ｜ 方法数: 8（公开 8）

Transport for api_mode='anthropic_messages'.

Wraps the existing functions in anthropic_adapter.py behind the
ProviderTransport ABC.  Each method delegates — no logic is duplicated.

#### property `api_mode(self) -> str`

#### def `convert_messages(self, messages: List[Dict[str, Any]], **kwargs) -> Any`

Convert OpenAI messages to Anthropic (system, messages) tuple.

kwargs:
    base_url: Optional[str] — affects thinking signature handling.

#### def `convert_tools(self, tools: List[Dict[str, Any]]) -> Any`

Convert OpenAI tool schemas to Anthropic input_schema format.

#### def `build_kwargs(self, model: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, **params) -> Dict[str, Any]`

Build Anthropic messages.create() kwargs.

Calls convert_messages and convert_tools internally.

params (all optional):
    max_tokens: int
    reasoning_config: dict | None
    tool_choice: str | None
    is_oauth: bool
    preserve_dots: bool
    context_length: int | None
    base_url: str | None
    fast_mode: bool
    drop_context_1m_beta: bool

#### def `normalize_response(self, response: Any, **kwargs) -> NormalizedResponse`

Normalize Anthropic response to NormalizedResponse.

Parses content blocks (text, thinking, tool_use), maps stop_reason
to OpenAI finish_reason, and collects reasoning_details in provider_data.

#### def `validate_response(self, response: Any) -> bool`

Check Anthropic response structure is valid.

An empty content list is legitimate for terminal stop reasons that
carry no text payload:

- ``end_turn`` — the model's canonical "nothing more to add" after a
  tool turn that already delivered the user-facing text.
- ``refusal`` — the model declined to respond (Claude 4.5+). The
  Messages API returns an empty ``content`` list with this stop
  reason. Treating it as invalid sends a deterministic refusal into
  the invalid-response retry loop, which reproduces the refusal on
  every attempt and surfaces a misleading "rate limited / invalid
  response" error instead of the refusal. ``normalize_response`` maps
  ``refusal`` → ``content_filter`` so the agent loop's refusal handler
  can surface it.

Treating either as invalid falsely retries a completed response.

#### def `extract_cache_stats(self, response: Any) -> Optional[Dict[str, int]]`

Extract Anthropic cache_read and cache_creation token counts.

#### def `map_finish_reason(self, raw_reason: str) -> str`

Map Anthropic stop_reason to OpenAI finish_reason.


## agent.transports.base

### 模块文档

Abstract base for provider transports.

A transport owns the data path for one api_mode:
  convert_messages → convert_tools → build_kwargs → normalize_response

It does NOT own: client construction, streaming, credential refresh,
prompt caching, interrupt handling, or retry logic.  Those stay on AIAgent.

### class ProviderTransport

> 继承: `ABC` ｜ 方法数: 8（公开 8）

Base class for provider-specific format conversion and normalization.

#### property `api_mode(self) -> str`

The api_mode string this transport handles (e.g. 'anthropic_messages').

#### def `convert_messages(self, messages: List[Dict[str, Any]], **kwargs) -> Any`

Convert OpenAI-format messages to provider-native format.

Returns provider-specific structure (e.g. (system, messages) for Anthropic,
or the messages list unchanged for chat_completions).

#### def `convert_tools(self, tools: List[Dict[str, Any]]) -> Any`

Convert OpenAI-format tool definitions to provider-native format.

Returns provider-specific tool list (e.g. Anthropic input_schema format).

#### def `build_kwargs(self, model: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, **params) -> Dict[str, Any]`

Build the complete API call kwargs dict.

This is the primary entry point — it typically calls convert_messages()
and convert_tools() internally, then adds model-specific config.

Returns a dict ready to be passed to the provider's SDK client.

#### def `normalize_response(self, response: Any, **kwargs) -> NormalizedResponse`

Normalize a raw provider response to the shared NormalizedResponse type.

This is the only method that returns a transport-layer type.

#### def `validate_response(self, response: Any) -> bool`

Optional: check if the raw response is structurally valid.

Returns True if valid, False if the response should be treated as invalid.
Default implementation always returns True.

#### def `extract_cache_stats(self, response: Any) -> Optional[Dict[str, int]]`

Optional: extract provider-specific cache hit/creation stats.

Returns dict with 'cached_tokens' and 'creation_tokens', or None.
Default returns None.

#### def `map_finish_reason(self, raw_reason: str) -> str`

Optional: map provider-specific stop reason to OpenAI equivalent.

Default returns the raw reason unchanged.  Override for providers
with different stop reason vocabularies.


## agent.transports.bedrock

### 模块文档

AWS Bedrock Converse API transport.

Delegates to the existing adapter functions in agent/bedrock_adapter.py.
Bedrock uses its own boto3 client (not the OpenAI SDK), so the transport
owns format conversion and normalization, while client construction and
boto3 calls stay on AIAgent.

### class BedrockTransport

> 继承: `ProviderTransport` ｜ 方法数: 7（公开 7）

Transport for api_mode='bedrock_converse'.

#### property `api_mode(self) -> str`

#### def `convert_messages(self, messages: List[Dict[str, Any]], **kwargs) -> Any`

Convert OpenAI messages to Bedrock Converse format.

#### def `convert_tools(self, tools: List[Dict[str, Any]]) -> Any`

Convert OpenAI tool schemas to Bedrock Converse toolConfig.

#### def `build_kwargs(self, model: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, **params) -> Dict[str, Any]`

Build Bedrock converse() kwargs.

Calls convert_messages and convert_tools internally.

params:
    max_tokens: int — output token limit (default 4096)
    temperature: float | None
    guardrail_config: dict | None — Bedrock guardrails
    region: str — AWS region (default 'us-east-1')

#### def `normalize_response(self, response: Any, **kwargs) -> NormalizedResponse`

Normalize Bedrock response to NormalizedResponse.

Handles two shapes:
1. Raw boto3 dict (from direct converse() calls)
2. Already-normalized SimpleNamespace with .choices (from dispatch site)

#### def `validate_response(self, response: Any) -> bool`

Check Bedrock response structure.

After normalize_converse_response, the response has OpenAI-compatible
.choices — same check as chat_completions.

#### def `map_finish_reason(self, raw_reason: str) -> str`

Map Bedrock stop reason to OpenAI finish_reason.

The adapter already does this mapping inside normalize_converse_response,
so this is only used for direct access to raw responses.


## agent.transports.chat_completions

### 模块文档

OpenAI Chat Completions transport.

Handles the default api_mode ('chat_completions') used by ~16 OpenAI-compatible
providers (OpenRouter, Nous, NVIDIA, Qwen, Ollama, DeepSeek, xAI, Kimi, etc.).

Messages and tools are already in OpenAI format — convert_messages and
convert_tools are near-identity.  The complexity lives in build_kwargs
which has provider-specific conditionals for max_tokens defaults,
reasoning configuration, temperature handling, and extra_body assembly.

### class ChatCompletionsTransport

> 继承: `ProviderTransport` ｜ 方法数: 8（公开 7）

Transport for api_mode='chat_completions'.

The default path for OpenAI-compatible providers.

#### property `api_mode(self) -> str`

#### def `convert_messages(self, messages: list[dict[str, Any]], **kwargs) -> list[dict[str, Any]]`

Messages are already in OpenAI format — strip internal fields
that strict chat-completions providers reject with HTTP 400/422
(or, in the case of some OpenAI-compatible gateways, 5xx):

- Codex Responses API fields: ``codex_reasoning_items`` /
  ``codex_message_items`` on the message, ``call_id`` /
  ``response_item_id`` on ``tool_calls`` entries.
- ``extra_content`` on ``tool_calls`` (Gemini thought_signature) —
  stripped unless the outgoing ``model`` is itself Gemini-family.
  Gemini 3 thinking models attach it for replay, but strict providers
  (Fireworks, Mistral) reject any payload containing it with
  ``Extra inputs are not permitted, field: 'messages[N].tool_calls[M].extra_content'``.
  It must be kept for Gemini targets (replay required) and dropped for
  everyone else, including non-Gemini models that inherited stale
  Gemini ``extra_content`` earlier in a mixed-provider session.
- ``tool_name`` on tool-result messages — written by
  ``make_tool_result_message()`` for the SQLite FTS index, but not
  part of the Chat Completions schema. Strict providers (Fireworks,
  Moonshot/Kimi) reject any payload containing it with
  ``Extra inputs are not permitted, field: 'messages[N].tool_name'``.
  Permissive providers (OpenRouter, MiniMax) silently ignore the
  field, which masked the bug for months.
- Hermes-internal scaffolding markers — any top-level message key
  starting with ``_`` (e.g. ``_empty_recovery_synthetic``,
  ``_empty_terminal_sentinel``, ``_thinking_prefill``). These are
  bookkeeping flags the agent loop attaches to messages so the
  persistence layer can later strip its own scaffolding; they must
  never reach the wire. Permissive providers (real OpenAI,
  Anthropic) silently drop unknown message keys, but strict
  gateways (e.g. opencode-go, codex.nekos.me) reject with
  ``Extra inputs are not permitted, field: 'messages[N]._empty_recovery_synthetic'``,
  which then poisons every subsequent request in the session.

#### def `convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]`

Tools are already in OpenAI format — identity.

#### def `build_kwargs(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, **params) -> dict[str, Any]`

Build chat.completions.create() kwargs.

params (all optional):
    timeout: float — API call timeout
    max_tokens: int | None — user-configured max tokens
    ephemeral_max_output_tokens: int | None — one-shot override
    max_tokens_param_fn: callable — returns {max_tokens: N} or {max_completion_tokens: N}
    reasoning_config: dict | None
    request_overrides: dict | None
    session_id: str | None
    model_lower: str — lowercase model name for pattern matching
    # Provider profile path (all per-provider quirks live in providers/)
    provider_profile: ProviderProfile | None — when present, delegates to
        _build_kwargs_from_profile(); all flag params below are bypassed.
    # Legacy-path flags — only used when provider_profile is None
    # (i.e. custom / unregistered providers). Known providers all go
    # through provider_profile.
    is_openrouter: bool
    is_nous: bool
    is_qwen_portal: bool
    is_github_models: bool
    is_nvidia_nim: bool
    is_kimi: bool
    is_tokenhub: bool
    is_lmstudio: bool
    is_custom_provider: bool
    ollama_num_ctx: int | None
    # Provider routing
    provider_preferences: dict | None
    # Qwen-specific
    qwen_prepare_fn: callable | None — runs AFTER codex sanitization
    qwen_prepare_inplace_fn: callable | None — in-place variant for deepcopied lists
    qwen_session_metadata: dict | None
    # Temperature
    fixed_temperature: Any — from _fixed_temperature_for_model()
    omit_temperature: bool
    # Reasoning
    supports_reasoning: bool
    github_reasoning_extra: dict | None
    lmstudio_reasoning_options: list[str] | None  # raw allowed_options from /api/v1/models
    # Claude on OpenRouter/Nous max output
    anthropic_max_output: int | None
    extra_body_additions: dict | None

#### def `normalize_response(self, response: Any, **kwargs) -> NormalizedResponse`

Normalize OpenAI ChatCompletion to NormalizedResponse.

For chat_completions, this is near-identity — the response is already
in OpenAI format.  extra_content on tool_calls (Gemini thought_signature)
is preserved via ToolCall.provider_data.  reasoning_details (OpenRouter
unified format) and reasoning_content (DeepSeek/Moonshot) are also
preserved for downstream replay.

#### def `validate_response(self, response: Any) -> bool`

Check that response has valid choices.

#### def `extract_cache_stats(self, response: Any) -> dict[str, int] | None`

Extract cache stats from prompt_tokens_details (OpenRouter/OpenAI)
or DeepSeek's native top-level prompt_cache_hit_tokens field.


## agent.transports.codex

### 模块文档

OpenAI Responses API (Codex) transport.

Delegates to the existing adapter functions in agent/codex_responses_adapter.py.
This transport owns format conversion and normalization — NOT client lifecycle,
streaming, or the _run_codex_stream() call path.

### class ResponsesApiTransport

> 继承: `ProviderTransport` ｜ 方法数: 9（公开 8）

Transport for api_mode='codex_responses'.

Wraps the functions extracted into codex_responses_adapter.py (PR 1).

#### property `api_mode(self) -> str`

#### def `convert_messages(self, messages: List[Dict[str, Any]], **kwargs) -> Any`

Convert OpenAI chat messages to Responses API input items.

#### def `convert_tools(self, tools: List[Dict[str, Any]]) -> Any`

Convert OpenAI tool schemas to Responses API function definitions.

#### def `build_kwargs(self, model: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, **params) -> Dict[str, Any]`

Build Responses API kwargs.

Calls convert_messages and convert_tools internally.

params:
    instructions: str — system prompt (extracted from messages[0] if not given)
    reasoning_config: dict | None — {effort, enabled}
    session_id: str | None — transcript/session id; drives the xAI
        x-grok-conv-id header and the Codex cache-scope headers, and is
        the fallback prompt_cache_key when there is no static prefix to
        content-address
    max_tokens: int | None — max_output_tokens
    timeout: float | None — per-request timeout forwarded to the SDK
    request_overrides: dict | None — extra kwargs merged in
    provider: str | None — provider name for backend-specific logic
    base_url: str | None — endpoint URL
    base_url_hostname: str | None — hostname for backend detection
    is_github_responses: bool — Copilot/GitHub models backend
    is_codex_backend: bool — chatgpt.com/backend-api/codex
    is_xai_responses: bool — xAI/Grok backend
    github_reasoning_extra: dict | None — Copilot reasoning params

#### def `normalize_response(self, response: Any, **kwargs) -> NormalizedResponse`

Normalize Codex Responses API response to NormalizedResponse.

#### def `validate_response(self, response: Any) -> bool`

Check Codex Responses API response has valid output structure.

Returns True only if response.output is a non-empty list. Also treats
terminal content-filter incomplete responses as valid: the Responses API
may return status=incomplete with incomplete_details.reason='content_filter'
and no output items. That is a provider refusal signal, not a malformed
response, and must reach normalization so the agent loop can use the
content-policy / fallback path instead of invalid-response retries.

Does NOT check output_text fallback — the caller handles that with
diagnostic logging for stream backfill recovery.

#### def `preflight_kwargs(self, api_kwargs: Any, allow_stream: bool = False, is_github_responses: bool = False) -> dict`

Validate and sanitize Codex API kwargs before the call.

Normalizes input items, strips unsupported fields, validates structure.

#### def `map_finish_reason(self, raw_reason: str) -> str`

Map Codex response.status to OpenAI finish_reason.

Codex uses response.status ('completed', 'incomplete') +
response.incomplete_details.reason for granular mapping.
This method handles the simple status string; the caller
should check incomplete_details separately for 'max_output_tokens'.


## agent.transports.codex_app_server

### 模块文档

Codex app-server JSON-RPC client.

Speaks the protocol documented in codex-rs/app-server/README.md (codex 0.125+).
Transport is newline-delimited JSON-RPC 2.0 over stdio: spawn `codex app-server`,
do an `initialize` handshake, then drive `thread/start` + `turn/start` and
consume streaming `item/*` notifications until `turn/completed`.

This module is the wire-level speaker only. Higher-level concerns (event
projection into Hermes' display, approval bridging, transcript projection into
AIAgent.messages, plugin migration) live in sibling modules.

Status: optional opt-in runtime gated behind `model.openai_runtime ==
"codex_app_server"`. Hermes' default tool dispatch is unchanged when this
runtime is not selected.

### class CodexAppServerError

> 继承: `RuntimeError` ｜ 方法数: 1（公开 0）

Raised on JSON-RPC errors from the app-server.


### class CodexAppServerClient

> 继承: `object` ｜ 方法数: 18（公开 10）

Minimal JSON-RPC 2.0 client for `codex app-server` over stdio.

Threading model:
  - Spawning thread (caller) drives request/response pairs synchronously.
  - One reader thread parses stdout, dispatches replies to the right
    pending future, and routes notifications + server-initiated requests
    to bounded queues that the caller drains on their own cadence.
  - One reader thread captures stderr for diagnostics; codex emits
    tracing logs there at RUST_LOG-controlled levels.

Intentionally NOT async. AIAgent.run_conversation() is synchronous and
runs on the main thread; layering asyncio just to drive a stdio child
creates surprising interrupt semantics. We use blocking queues with
timeouts and rely on `turn/interrupt` for cancellation.

#### def `__init__(codex_bin: str = 'codex', codex_home: Optional[str] = None, extra_args: Optional[list[str]] = None, env: Optional[dict[str, str]] = None) -> None`

#### def `initialize(self, client_name: str = 'hermes', client_title: str = 'Hermes Agent', client_version: str = '0.1', capabilities: Optional[dict] = None, timeout: float = 10.0) -> dict`

Send `initialize` + `initialized` handshake. Returns the server's
InitializeResponse (userAgent, codexHome, platformFamily, platformOs).

**异常**: `RuntimeError`

#### def `close(self, timeout: float = 3.0) -> None`

Close stdin and wait for the subprocess to exit, escalating to kill.

#### def `request(self, method: str, params: Optional[dict] = None, timeout: float = 30.0) -> dict`

Send a JSON-RPC request and block on the response. Returns `result`,
raises CodexAppServerError on `error`.

**异常**: `CodexAppServerError`, `TimeoutError`

#### def `notify(self, method: str, params: Optional[dict] = None) -> None`

Send a JSON-RPC notification (no id, no response expected).

#### def `respond(self, request_id: Any, result: dict) -> None`

Reply to a server-initiated request (e.g. approval prompts).

#### def `respond_error(self, request_id: Any, code: int, message: str, data: Optional[Any] = None) -> None`

Reply to a server-initiated request with an error.

#### def `take_notification(self, timeout: float = 0.0) -> Optional[dict]`

Pop the next streaming notification, or return None on timeout.

timeout=0.0 means non-blocking. Use small positive timeouts inside the
AIAgent turn loop to interleave reads with interrupt checks.

#### def `take_server_request(self, timeout: float = 0.0) -> Optional[dict]`

Pop the next server-initiated request (e.g. exec/applyPatch approval).

#### def `stderr_tail(self, n: int = 20) -> list[str]`

Return last n lines of codex's stderr (for error reports).

#### def `is_alive(self) -> bool`


### 顶层函数

#### def `parse_codex_version(output: str) -> Optional[tuple[int, int, int]]`

Parse `codex --version` output. Returns (major, minor, patch) or None.

#### def `check_codex_binary(codex_bin: str = 'codex', min_version: tuple[int, int, int] = MIN_CODEX_VERSION) -> tuple[bool, str]`

Verify codex CLI is installed and meets minimum version.

Returns (ok, message). Used by setup wizard and runtime startup.


## agent.transports.codex_app_server_session

### 模块文档

Session adapter for codex app-server runtime.

Owns one Codex thread per Hermes session. Drives `turn/start`, consumes
streaming notifications via CodexEventProjector, handles server-initiated
approval requests (apply_patch, exec command), translates cancellation,
and returns a clean turn result that AIAgent.run_conversation() can splice
into its `messages` list.

Lifecycle:
    session = CodexAppServerSession(cwd="/home/x/proj")
    session.ensure_started()                              # spawns + handshake + thread/start
    result = session.run_turn(user_input="hello")         # blocks until turn/completed
    # result.final_text          → assistant text returned to caller
    # result.projected_messages  → list of {role, content, ...} for messages list
    # result.tool_iterations     → how many tool-shaped items completed (skill nudge counter)
    # result.interrupted         → True if Ctrl+C / interrupt_requested fired mid-turn
    session.close()                                       # tears down subprocess

Threading model: the adapter is single-threaded from the caller's perspective.
The underlying CodexAppServerClient owns its own reader threads but exposes
blocking-with-timeout queues that this adapter polls in a loop, so the run_turn
call is synchronous and behaves like AIAgent's existing chat_completions loop.

### class TurnResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of one user→assistant→tool turn through the codex app-server.


### class CodexAppServerSession

> 继承: `object` ｜ 方法数: 15（公开 5）

One Codex thread per Hermes session, lifetime owned by AIAgent.

Not thread-safe — one caller drives it at a time, matching how AIAgent's
run_conversation() loop is structured today. The codex client itself can
handle interleaved reads/writes via its own threads, but the adapter's
state (projector, thread_id, turn counter) is owned by the caller thread.

#### def `__init__(cwd: Optional[str] = None, codex_bin: str = 'codex', codex_home: Optional[str] = None, permission_profile: Optional[str] = None, approval_callback: Optional[Callable[..., str]] = None, on_event: Optional[Callable[[dict], None]] = None, request_routing: Optional[_ServerRequestRouting] = None, client_factory: Optional[Callable[..., CodexAppServerClient]] = None) -> None`

#### def `ensure_started(self) -> str`

Spawn the subprocess, do the initialize handshake, and start a
thread. Returns the codex thread id. Idempotent — repeated calls
return the same thread id.

**异常**: `CodexAppServerError`

#### def `close(self) -> None`

#### def `request_interrupt(self) -> None`

Idempotent: signal the active turn loop to issue turn/interrupt
and unwind. Called by AIAgent's _interrupt_requested path.

#### def `run_turn(self, user_input: Any, turn_timeout: float = 600.0, notification_poll_timeout: float = 0.25, post_tool_quiet_timeout: float = 90.0) -> TurnResult`

Send a user message and block until turn/completed, while
forwarding server-initiated approval requests and projecting items
into Hermes' messages shape.

post_tool_quiet_timeout: if codex emits a tool completion and then
goes quiet for this many seconds without emitting another item or
`turn/completed`, fast-fail and mark the session for retirement.
Mirrors openclaw beta.8's post-tool completion watchdog (#81697)
so a wedged codex doesn't burn the full turn deadline.

#### def `compact_thread(self, turn_timeout: float = 600.0, notification_poll_timeout: float = 0.25) -> TurnResult`

Trigger Codex-native history compaction for the current thread.

`thread/compact/start` returns immediately; the actual compaction
progress streams through the same turn/item notifications as a normal
turn. We wait for the matching `turn/completed` so callers can treat a
successful return as a completed compaction boundary.


## agent.transports.codex_event_projector

### 模块文档

Projects codex app-server events into Hermes' messages list.

The translator that lets Hermes' memory/skill review keep working under the
Codex runtime: it converts Codex `item/*` notifications into the standard
OpenAI-shaped `{role, content, tool_calls, tool_call_id}` entries that
`agent/curator.py` already knows how to read.

Codex emits items with a discriminator field `type`:
  - userMessage         → {role: "user", content}
  - agentMessage        → {role: "assistant", content}
  - reasoning           → stashed in the assistant's "reasoning" field
  - commandExecution    → assistant tool_call(name="exec") + tool result
  - fileChange          → assistant tool_call(name="apply_patch") + tool result
  - mcpToolCall         → assistant tool_call(name=f"mcp.{server}.{tool}") + tool result
  - dynamicToolCall     → assistant tool_call(name=tool) + tool result
  - plan/hookPrompt/collabAgentToolCall → recorded as opaque assistant notes

Each item maps to AT MOST one assistant entry + one tool entry, preserving
Hermes' message-alternation invariants (system → user → assistant → user/tool
→ assistant → ...). Multiple Codex tool calls within one Codex turn produce
multiple consecutive (assistant, tool) pairs, which is the same shape Hermes
already produces for parallel tool calls.

Counters tracked alongside projection:
  - tool_iterations: ticks once per completed tool-shaped item. Used by
    AIAgent._iters_since_skill (skill nudge gate, default threshold 10).

### class ProjectionResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Output of projecting one Codex item.

`messages` is a list because some Codex items produce two messages
(assistant tool_call + tool result). Empty list = item ignored (e.g. a
streaming `outputDelta` that doesn't materialize into messages until the
`item/completed` event).


### class CodexEventProjector

> 继承: `object` ｜ 方法数: 9（公开 1）

Stateful projector consuming Codex notifications in arrival order.

Owns the in-progress reasoning content (codex emits reasoning as separate
items but Hermes stashes it on the next assistant message).

#### def `__init__() -> None`

#### def `project(self, notification: dict) -> ProjectionResult`

Project a single notification. Idempotent for non-completion events;
only `item/completed` and `turn/completed` materialize messages.


## agent.transports.hermes_tools_mcp_server

### 模块文档

Hermes-tools-as-MCP server for the codex_app_server runtime.

When the user runs `openai/*` turns through the codex app-server, codex
owns the loop and builds its own tool list. By default, that means
Hermes' richer tool surface — web search, browser automation,
delegate_task subagents, vision analysis, persistent memory, skills,
cross-session search, image generation, TTS — is unreachable.

This module exposes a curated subset of those Hermes tools to the
spawned codex subprocess via stdio MCP. Codex registers it as a normal
MCP server (per `~/.codex/config.toml [mcp_servers.hermes-tools]`) and
the user gets full Hermes capability inside a Codex turn.

Scope (what we expose):
  - web_search, web_extract              — Firecrawl, no codex equivalent
  - browser_navigate / _click / _type /  — Camofox/Browserbase automation
    _snapshot / _scroll / _back / _press /
    _get_images / _console / _vision
  - vision_analyze                       — image inspection by vision model
  - image_generate                       — image generation
  - skill_view, skills_list              — Hermes' skill library
  - text_to_speech                       — TTS
  - kanban_* (complete/block/comment/    — kanban worker + orchestrator
    heartbeat/show/list/create/            handoff (stateless: read env var,
    unblock/link)                          write ~/.hermes/kanban.db)

What we DO NOT expose:
  - terminal / shell                     — codex's own shell tool
  - read_file / write_file / patch       — codex's apply_patch + shell
  - search_files / process               — codex's shell
  - clarify                              — codex's own UX
  - delegate_task / memory /             — `_AGENT_LOOP_TOOLS` in Hermes
    session_search / todo                  (model_tools.py). They require
                                           the running AIAgent context to
                                           dispatch (mid-loop state), so a
                                           stateless MCP callback can't
                                           drive them. See the inline
                                           comment on EXPOSED_TOOLS below.

Run with: python -m agent.transports.hermes_tools_mcp_server
Spawned by: CodexAppServerSession.ensure_started() when the runtime is
            active and config opts in.

### 顶层函数

#### def `main(argv: Optional[list[str]] = None) -> int`

Entry point for `python -m agent.transports.hermes_tools_mcp_server`.


## agent.transports.types

### 模块文档

Shared types for normalized provider responses.

These dataclasses define the canonical shape that all provider adapters
normalize responses to.  The shared surface is intentionally minimal —
only fields that every downstream consumer reads are top-level.
Protocol-specific state goes in ``provider_data`` dicts (response-level
and per-tool-call) so that protocol-aware code paths can access it
without polluting the shared type.

### class ToolCall

> 继承: `object` ｜ 方法数: 5（公开 5）

A normalized tool call from any provider.

``id`` is the protocol's canonical identifier — what gets used in
``tool_call_id`` / ``tool_use_id`` when constructing tool result
messages.  May be ``None`` when the provider omits it; the agent
fills it via ``_deterministic_call_id()`` before storing in history.

``provider_data`` carries per-tool-call protocol metadata that only
protocol-aware code reads:

* Codex: ``{"call_id": "call_XXX", "response_item_id": "fc_XXX"}``
* Gemini: ``{"extra_content": {"google": {"thought_signature": "..."}}}``
* Others: ``None``

#### property `type(self) -> str`

#### property `function(self) -> ToolCall`

Return self so tc.function.name / tc.function.arguments work.

#### property `call_id(self) -> str | None`

Codex call_id from provider_data, accessed via getattr by _build_assistant_message.

#### property `response_item_id(self) -> str | None`

Codex response_item_id from provider_data.

#### property `extra_content(self) -> dict[str, Any] | None`

Gemini extra_content (thought_signature) from provider_data.

Gemini 3 thinking models attach ``extra_content`` with a
``thought_signature`` to each tool call.  This signature must be
replayed on subsequent API calls — without it the API rejects the
request with HTTP 400.  The chat_completions transport stores this
in ``provider_data["extra_content"]``; this property exposes it so
``_build_assistant_message`` can ``getattr(tc, "extra_content")``
uniformly.


### class Usage

> 继承: `object` ｜ 方法数: 0（公开 0）

Token usage from an API response.


### class NormalizedResponse

> 继承: `object` ｜ 方法数: 5（公开 5）

Normalized API response from any provider.

Shared fields are truly cross-provider — every caller can rely on
them without branching on api_mode.  Protocol-specific state goes in
``provider_data`` so that only protocol-aware code paths read it.

Response-level ``provider_data`` examples:

* Anthropic: ``{"reasoning_details": [...]}``
* Codex: ``{"codex_reasoning_items": [...], "codex_message_items": [...]}``
* Others: ``None``

#### property `reasoning_content(self) -> str | None`

#### property `reasoning_details(self)`

#### property `anthropic_content_blocks(self)`

Verbatim, order-preserving Anthropic content blocks for a turn.

Present only when an Anthropic turn interleaves signed thinking with
tool_use — the one shape the parallel reasoning_details + tool_calls
lists reconstruct in the wrong order, invalidating thinking-block
signatures on replay. See agent/transports/anthropic.py.

#### property `codex_reasoning_items(self)`

#### property `codex_message_items(self)`


### 顶层函数

#### def `build_tool_call(id: str | None, name: str, arguments: Any, **provider_fields: Any) -> ToolCall`

Build a ``ToolCall``, auto-serialising *arguments* if it's a dict.

Any extra keyword arguments are collected into ``provider_data``.

#### def `map_finish_reason(reason: str | None, mapping: dict[str, str]) -> str`

Translate a provider-specific stop reason to the normalised set.

Falls back to ``"stop"`` for unknown or ``None`` reasons.


## agent.tts_provider

### 模块文档

Text-to-Speech Provider ABC
============================

Defines the pluggable-backend interface for text-to-speech synthesis.
Providers register instances via
``PluginContext.register_tts_provider()``; the active one (selected via
``tts.provider`` in ``config.yaml``) services every ``text_to_speech``
tool call **only when the configured name is neither a built-in nor a
command-type provider declared under ``tts.providers.<name>``**.

Three coexisting TTS extension surfaces — in resolution order:

1. **Built-in providers** (``BUILTIN_TTS_PROVIDERS`` in
   :mod:`tools.tts_tool`) — native Python implementations (edge, openai,
   elevenlabs, …). **Always win** — plugins cannot shadow them.
2. **Command-type providers** declared under ``tts.providers.<name>:
   type: command`` (PR #17843, commit ``2facea7f7``). Wire any local
   CLI into Hermes with shell-template placeholders. **Wins over a
   same-name plugin** — config is more local than plugin install.
3. **Plugin-registered providers** (this ABC). For backends that need a
   Python SDK, streaming bytes, OAuth refresh, or voice-listing APIs
   the shell-template grammar can't reasonably express.

Built-ins-always-win is enforced at registration time
(:func:`agent.tts_registry.register_provider` rejects names in
``BUILTIN_TTS_PROVIDERS`` with a warning) AND at dispatch time
(:func:`tools.tts_tool._dispatch_to_plugin_provider` re-checks
defensively). The dispatcher also rejects plugin dispatch when a same-
name command provider is configured.

Providers live in ``<repo>/plugins/tts/<name>/`` (built-in plugins, no
shipped today) or ``~/.hermes/plugins/tts/<name>/`` (user-installed).
None ship in-tree as of issue #30398 — the hook is additive
infrastructure waiting for a real consumer (Cartesia, Fish Audio, …).

Response contract
-----------------
:meth:`TTSProvider.synthesize` writes the audio bytes to ``output_path``
and returns the path as a string. Implementations should raise on
failure — the dispatcher converts exceptions into the standard
``{success: False, error: …}`` JSON envelope the rest of Hermes
expects.

### class TTSProvider

> 继承: `abc.ABC` ｜ 方法数: 11（公开 11）

Abstract base class for a text-to-speech backend.

Subclasses must implement :attr:`name` and :meth:`synthesize`.
Everything else has sane defaults — override only what your provider
needs.

#### property `name(self) -> str`

Stable short identifier used in ``tts.provider`` config.

Lowercase, no spaces. Examples: ``cartesia``, ``fishaudio``,
``deepgram``. Names that collide with a built-in TTS provider
(``edge``, ``openai``, ``elevenlabs``, ``minimax``, ``gemini``,
``mistral``, ``xai``, ``piper``, ``kittentts``, ``neutts``) are
rejected at registration time.

#### property `display_name(self) -> str`

Human-readable label shown in ``hermes tools``.

Defaults to ``name.title()`` (e.g. ``Cartesia`` for ``cartesia``).

#### def `is_available(self) -> bool`

Return True when this provider can service calls.

Typically checks for a required API key + that the SDK is
importable. Default: True (providers with no external
dependencies are always available).

Must NOT raise — used by the picker and ``hermes setup`` for
availability displays and should fail gracefully.

#### def `list_voices(self) -> List[Dict[str, Any]]`

Return voice catalog entries.

Each entry::

    {
        "id": "voice-abc-123",                # required
        "display": "Aria — neutral female",    # optional; defaults to id
        "language": "en-US",                   # optional
        "gender": "female",                    # optional
        "preview_url": "https://...mp3",       # optional
    }

Default: empty list (provider has no enumerable voices or
doesn't surface them via API).

#### def `list_models(self) -> List[Dict[str, Any]]`

Return model catalog entries.

Each entry::

    {
        "id": "sonic-2",                       # required
        "display": "Sonic 2",                  # optional
        "languages": ["en", "es", "fr"],       # optional
        "max_text_length": 5000,               # optional
    }

Default: empty list (provider has a single fixed model or
doesn't expose model selection).

#### def `get_setup_schema(self) -> Dict[str, Any]`

Return provider metadata for the ``hermes tools`` picker.

Used by ``tools_config.py`` to inject this provider as a row in
the Text-to-Speech provider list. Shape::

    {
        "name": "Cartesia",                    # picker label
        "badge": "paid",                       # optional short tag
        "tag": "Ultra-low-latency streaming",  # optional subtitle
        "env_vars": [                          # keys to prompt for
            {"key": "CARTESIA_API_KEY",
             "prompt": "Cartesia API key",
             "url": "https://play.cartesia.ai/console"},
        ],
    }

Default: minimal entry derived from ``display_name`` with no
env vars. Override to expose API key prompts and custom badges.

#### def `default_model(self) -> Optional[str]`

Return the default model id, or None if not applicable.

#### def `default_voice(self) -> Optional[str]`

Return the default voice id, or None if not applicable.

#### def `synthesize(self, text: str, output_path: str, voice: Optional[str] = None, model: Optional[str] = None, speed: Optional[float] = None, format: str = DEFAULT_OUTPUT_FORMAT, **extra: Any) -> str`

Synthesize ``text`` and write audio bytes to ``output_path``.

Returns the absolute path to the written file as a string
(typically just echoes ``output_path``). Raises on failure —
the dispatcher converts exceptions to the standard
``{success: False, error: ...}`` JSON envelope.

Args:
    text: The text to synthesize. Already truncated to the
        provider's max length by the dispatcher.
    output_path: Absolute path where the audio file should be
        written. Parent directory is guaranteed to exist.
    voice: Voice identifier from :meth:`list_voices`, or None
        to use :meth:`default_voice`.
    model: Model identifier from :meth:`list_models`, or None
        to use :meth:`default_model`.
    speed: Optional speech-rate multiplier (1.0 = normal).
        Providers that don't support speed control should
        ignore this argument.
    format: Output audio format. Implementations should match
        the requested format when possible; if unsupported,
        pick the closest equivalent and ensure ``output_path``
        ends with the correct extension.
    **extra: Forward-compat parameters future schema versions
        may expose. Implementations should ignore unknown keys.

**异常**: `Args`, `text`, `output_path`, `voice`, `model`, `speed`, `format`

#### def `stream(self, text: str, voice: Optional[str] = None, model: Optional[str] = None, format: str = 'opus', **extra: Any) -> Iterator[bytes]`

Stream synthesized audio bytes.

Optional. Providers that don't support streaming raise
:class:`NotImplementedError` (the default) and the dispatcher
falls back to :meth:`synthesize` + read-whole-file.

Args mirror :meth:`synthesize`. Default ``format`` is ``opus``
because the primary streaming use case is voice-bubble
delivery (Telegram et al.) which requires Opus.

**异常**: `NotImplementedError`

#### property `voice_compatible(self) -> bool`

Whether output is suitable for voice-bubble delivery.

Mirrors the ``tts.providers.<name>.voice_compatible`` field
from PR #17843. When True, the gateway's voice-message
delivery pipeline runs ffmpeg conversion to Opus if needed.
When False, output is delivered as a regular audio attachment.

Default: False (safe — providers opt in explicitly).


### 顶层函数

#### def `resolve_output_format(value: Optional[str]) -> str`

Clamp an output_format value to the valid set.

Invalid values are coerced to :data:`DEFAULT_OUTPUT_FORMAT` rather
than rejected so the tool surface is forgiving of agent mistakes.


## agent.tts_registry

### 模块文档

TTS Provider Registry
=====================

Central map of registered TTS providers. Populated by plugins at
import-time via :meth:`PluginContext.register_tts_provider`; consumed
by :mod:`tools.tts_tool` to dispatch ``text_to_speech`` tool calls to
the active plugin backend **when** the configured ``tts.provider``
name is neither a built-in nor a command-type provider.

Built-ins-always-win
--------------------
Plugin names that collide with a built-in TTS provider (``edge``,
``openai``, ``elevenlabs``, ``minimax``, ``gemini``, ``mistral``,
``xai``, ``piper``, ``kittentts``, ``neutts``) are rejected at
registration with a warning. This invariant is also re-checked at
dispatch time in :func:`tools.tts_tool._dispatch_to_plugin_provider`.

Command-providers-win-over-plugins
----------------------------------
This registry doesn't enforce the command-vs-plugin precedence — that
lives in the dispatcher, which checks for a same-name
``tts.providers.<name>: type: command`` entry before consulting the
registry. The rationale is locality: a name declared in the user's
``config.yaml`` is more specific to their setup than a plugin that
happens to be installed.

### 顶层函数

#### def `register_provider(provider: TTSProvider) -> None`

Register a TTS provider.

Rejects:

- Non-:class:`TTSProvider` instances (raises :class:`TypeError`).
- Empty/whitespace ``.name`` (raises :class:`ValueError`).
- Names colliding with a built-in (logs a warning, silently
  ignores — built-ins-always-win invariant).

Re-registration (same ``name``) overwrites the previous entry and
logs a debug message — makes hot-reload scenarios (tests, dev
loops) behave predictably.

**异常**: `class`, `TypeError`, `ValueError`

#### def `list_providers() -> List[TTSProvider]`

Return all registered providers, sorted by name.

#### def `get_provider(name: str) -> Optional[TTSProvider]`

Return the provider registered under *name*, or None.

Name matching is case-insensitive and whitespace-tolerant — mirrors
how ``tools.tts_tool._get_provider`` normalizes the configured
``tts.provider`` value.


## agent.turn_context

### 模块文档

Per-turn setup for ``run_conversation`` (the turn prologue).

``run_conversation`` opened with ~470 lines of straight-line setup before the
tool-calling loop ever started: stdio guarding, runtime-main wiring, retry-counter
resets, user-message sanitization, todo/nudge-counter hydration, system-prompt
restore-or-build, session-row creation (before compression, whose DB writes
reference the row), preflight context compression, the ``pre_llm_call`` plugin
hook, external-memory prefetch, and crash-resilience persistence (last, so the
user row is written once with its final ``api_content`` sidecar).

All of that is *prologue* — it runs once per turn, has no back-references into the
loop, and produces a fixed set of values the loop then consumes. ``TurnContext``
captures those produced values; ``build_turn_context`` performs the setup work and
returns one. ``run_conversation`` is left to unpack the context and run the loop,
shrinking the orchestrator by the full prologue.

The builder still mutates ``agent`` heavily (counters, thread id, cached prompt,
session DB) exactly as the inline code did — those side effects are the point. The
``TurnContext`` it returns carries only the *locals* the loop reads back.

Behavior is identical to the original inline prologue; this is a pure
move-and-name refactor with no semantic change.

### class TurnContext

> 继承: `object` ｜ 方法数: 0（公开 0）

Values produced by the turn prologue and consumed by the turn loop.


### 顶层函数

#### def `compose_user_api_content(content: Any, ext_prefetch_cache: str, plugin_user_context: str) -> Optional[str]`

Compose the API-bound content of the current turn's user message.

Sources: memory-manager prefetch + ``pre_llm_call`` plugin context with
target="user_message" (the default). Both are appended to the *API copy*
of the user message only — the stored content stays clean.

This is the single source of that composition. The prologue stamps the
result onto the live message as ``api_content`` (persisted alongside the
clean content) and the ``api_messages`` build in ``conversation_loop``
sends the same helper's output, so the persisted sidecar can never drift
from the bytes on the wire — which is the whole prompt-cache invariant:
what turn N sends must be what turn N+1 replays.

Returns ``None`` when nothing is injected (multimodal/non-string content,
or no ephemeral context), meaning the message is sent as-is.

#### def `substitute_api_content(api_msg: Dict[str, Any]) -> Optional[str]`

Pop the ``api_content`` sidecar and substitute it into ``content``.

Used at every API-bound message-build site (the ``api_messages`` build in
``conversation_loop``, the max-iterations summary in
``chat_completion_helpers``, the chat-completions transport). The sidecar
carries the exact bytes previously sent to the API for this message when
they differ from the clean stored content; substituting it here keeps the
provider prompt-cache prefix byte-stable across turns.

Returns the popped sidecar string (for callers that need the value for
current-turn composition logic) or ``None`` when absent.

#### def `drop_stale_api_content(msg: Dict[str, Any]) -> None`

Drop the ``api_content`` sidecar from a message whose content was rewritten.

Called from every content-rewrite path (historical image strip,
merge-summary-into-tail, consecutive-user repair merge, stale-confirmation
redaction). Replaying the pre-rewrite sidecar would resend exactly what
the rewrite removed, so it must be dropped — the cost is one cache
boundary miss, never wrong content.

#### def `extract_api_content_sidecar(msg: Mapping[str, Any]) -> Optional[str]`

Extract the ``api_content`` sidecar from a message dict for persistence.

Shared by the gateway/branch forwarding sites that copy the sidecar into a
new row. Returns the string sidecar or ``None`` when absent/non-string.

#### def `consume_gateway_turn_context_notes(agent: Any) -> str`

Pop the gateway's per-turn must-deliver notes off the agent (one-shot).

The gateway relocates volatile per-turn facts OUT of the ephemeral system
prompt (auto-reset notes, the first-contact intro, voice-channel changes)
and delivers them on the current user message via the api_content sidecar
instead, so the composed system prompt stays byte-stable turn-over-turn.
It stages the rendered notes on ``agent._gateway_turn_context_notes``
right before ``run_conversation``; this consumes them so a cached agent
can never replay a stale note on a later turn.

#### def `append_notes_to_multimodal_content(content: Any, notes: str) -> bool`

Deliver must-deliver notes on a multimodal (list) user message.

``compose_user_api_content`` returns ``None`` for non-string content, so
sidecar-borne facts would silently drop on image/attachment turns.  For
gateway must-deliver notes we instead append a text part to the content
list in place — the part becomes durable message content (persisted and
replayed as-is), which keeps the wire and the transcript byte-identical.

Returns ``True`` when a part was appended.

#### def `reanchor_current_turn_user_idx(messages: List[Any], user_message: Any) -> int`

Locate this turn's user message after compaction rebuilt ``messages``.

Compression replaces list entries with fresh copies (and may append a
todo-snapshot user message or a restored user turn AFTER the surviving
copy of the current turn's message), so a pre-compression index is
meaningless. Prefer the LAST user message whose content exactly matches
this turn's text — the surviving copy in the common case — so the
injection stamp and the #48677 persist override can't land on a
todo-snapshot or historical row. Fall back to the last user message when
no exact match survives (merge-summary-into-tail rewrites the content but
the trackers still need a live anchor). Returns -1 when the list has no
user message at all.

#### def `build_turn_context(agent, user_message: Any, system_message: Optional[str], conversation_history: Optional[List[Dict[str, Any]]], task_id: Optional[str], stream_callback, persist_user_message: Optional[Any], persist_user_timestamp: Optional[float] = None, restore_or_build_system_prompt, install_safe_stdio, sanitize_surrogates, summarize_user_message_for_log, set_session_context, set_current_write_origin, ra, moa_active: bool = False) -> TurnContext`

Run the once-per-turn setup and return the loop's input context.

The callables/helpers the original prologue referenced from the
``conversation_loop`` module are passed in explicitly to keep this module
free of an import cycle with ``agent.conversation_loop``.


## agent.turn_finalizer

### 模块文档

Post-loop turn finalization for ``run_conversation``.

Extracted from ``agent/conversation_loop.py`` as part of the god-file
decomposition campaign (``~/.hermes/plans/god-file-decomposition.md``, Phase 1
step 4 — the post-loop ``TurnFinalizer`` seam). ``run_conversation``'s tail
(everything after the main tool-calling ``while`` loop) is lifted here verbatim:
budget-exhaustion summary, trajectory save, session persist, turn diagnostics,
response transforms, result-dict assembly, steer drain, and the memory/skill
review trigger.

Behavior-neutral: the body is moved unchanged. All ``agent.*`` side effects fire
exactly as before; only the post-loop *locals* are passed in as keyword args, and
the assembled ``result`` dict is returned to ``run_conversation`` which returns it
to the caller. The function is synchronous with a single return — mirroring the
region it replaces (no awaits, no early returns).

Module ``logger`` is imported lazily inside the body (``from
agent.conversation_loop import logger``) so this module never imports
``agent.conversation_loop`` at import time -> no import cycle, and the log records
keep the exact logger name (``"agent.conversation_loop"``).

### 顶层函数

#### def `finalize_turn(agent, final_response, api_call_count, interrupted, failed, messages, conversation_history, effective_task_id, turn_id, user_message, original_user_message, _should_review_memory, _turn_exit_reason, _pending_verification_response = None, _pending_verification_response_previewed = False)`

Run the post-loop finalization and return the turn ``result`` dict.

Lifted verbatim from ``run_conversation`` (the region after the main agent
loop). See module docstring.


## agent.turn_retry_state

### 模块文档

Per-attempt recovery bookkeeping for the conversation turn loop.

The inner retry loop in ``run_conversation`` (``while retry_count <
max_retries``) makes several distinct recovery attempts on a single model API
call: a credential-pool 429 retry, a per-provider OAuth refresh (codex,
anthropic, nous, copilot), a long-context compression restart, a length-
continuation restart, and a handful of format-recovery branches (thinking-
signature stripping, multimodal-tool-content stripping, llama.cpp grammar
fallback, image shrink, invalid-encrypted-content, 1M-beta header).

Each of those branches is guarded by a one-shot boolean so it fires at most
once per attempt. They used to be ~16 bare ``*_attempted`` / ``has_retried_*``
/ ``restart_with_*`` locals declared inline before the loop and threaded
through its 2,400-line body. ``TurnRetryState`` collapses them into one object
the loop mutates in place (``state.codex_auth_retry_attempted = True``), giving
the recovery bookkeeping a single named, testable home.

Loop-control variables (``retry_count``, ``max_retries``,
``max_compression_attempts``) intentionally stay as plain locals — they are the
``while`` mechanics, not recovery bookkeeping, and putting them on the object
would add indirection without clarifying anything.

This module is dependency-free so it can be unit-tested in isolation and
imported by the turn loop without an import cycle.

### class TurnRetryState

> 继承: `object` ｜ 方法数: 1（公开 0）

One-shot recovery guards + restart signals for a single API-call attempt.

A fresh instance is created for each iteration of the outer turn loop
(once per ``api_call_count``). Each guard fires its recovery branch at most
once; the ``restart_with_*`` signals are read by the loop after the attempt
to decide whether to rebuild the request and retry.


## agent.usage_pricing

### class CanonicalUsage

> 继承: `object` ｜ 方法数: 3（公开 2）

#### property `prompt_tokens(self) -> int`

#### property `total_tokens(self) -> int`


### class BillingRoute

> 继承: `object` ｜ 方法数: 0（公开 0）


### class PricingEntry

> 继承: `object` ｜ 方法数: 0（公开 0）


### class CostResult

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `resolve_billing_route(model_name: str, provider: Optional[str] = None, base_url: Optional[str] = None) -> BillingRoute`

#### def `get_pricing_entry(model_name: str, provider: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None) -> Optional[PricingEntry]`

#### def `normalize_usage(response_usage: Any, provider: Optional[str] = None, api_mode: Optional[str] = None) -> CanonicalUsage`

Normalize raw API response usage into canonical token buckets.

Handles three API shapes:
- Anthropic: input_tokens/output_tokens/cache_read_input_tokens/cache_creation_input_tokens
- Codex Responses: input_tokens includes cache tokens; input_tokens_details.cached_tokens separates them
- OpenAI Chat Completions: prompt_tokens includes cache tokens; prompt_tokens_details.cached_tokens separates them

In both Codex and OpenAI modes, input_tokens is derived by subtracting cache
tokens from the total — the API contract is that input/prompt totals include
cached tokens and the details object breaks them out.

#### def `estimate_usage_cost(model_name: str, usage: CanonicalUsage, provider: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None) -> CostResult`

#### def `has_known_pricing(model_name: str, provider: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None) -> bool`

Check whether we have pricing data for this model+route.

Uses direct lookup instead of routing through the full estimation
pipeline — avoids creating dummy usage objects just to check status.

#### def `format_duration_compact(seconds: float) -> str`

#### def `format_token_count_compact(value: int) -> str`


## agent.verification_evidence

### 模块文档

Coding verification evidence ledger.

This module records what the agent actually proved while working in a code
workspace. It is deliberately passive: it never decides to run a suite, never
blocks completion, and never upgrades targeted checks into "repo green".

### class VerificationEvidence

> 继承: `object` ｜ 方法数: 0（公开 0）

A classified command result worth recording.


### 顶层函数

#### def `classify_verification_command(command: str, cwd: str | Path | None = None, session_id: str | None = None, exit_code: int = 0, output: str = '') -> Optional[VerificationEvidence]`

Classify a terminal command as verification evidence, if applicable.

#### def `record_terminal_result(command: str, cwd: str | Path | None, session_id: str | None, exit_code: int, output: str = '') -> Optional[dict[str, Any]]`

Record a foreground terminal result when it is verification evidence.

**异常**: `RuntimeError`

#### def `mark_workspace_edited(session_id: str | None, cwd: str | Path | None, paths: list[str] | tuple[str, ...] | None = None) -> Optional[dict[str, Any]]`

Mark verification evidence stale after a successful file edit.

#### def `verification_status(session_id: str | None, cwd: str | Path | None) -> dict[str, Any]`

Return the best known verification state for a session/workspace.


## agent.verification_stop

### 模块文档

Turn-end verification guard for coding edits.

This module is intentionally policy-only. It never runs checks itself; it turns
the passive verification ledger into a bounded follow-up when the model tries to
finish immediately after editing code without fresh evidence.

### 顶层函数

#### def `verify_on_stop_enabled(config: dict[str, Any] | None = None) -> bool`

Return whether edit -> verify-before-finish behavior is enabled.

Precedence: an explicit ``HERMES_VERIFY_ON_STOP`` env var wins, then an
explicit ``agent.verify_on_stop`` config value. The config default is
``"auto"`` (see ``DEFAULT_CONFIG``) — surface-aware: ON for interactive
coding surfaces (CLI, TUI, desktop) and programmatic callers, OFF for
conversational messaging surfaces (Telegram, Discord, etc.) where the
verification narrative would reach a human as chat noise. An explicit
bool forces the behavior in either direction. A missing or unrecognized
value falls back to the surface-aware ``"auto"`` default.

#### def `build_verify_on_stop_nudge(session_id: str | None, changed_paths: Iterable[str], attempts: int = 0, max_attempts: int = 2) -> str | None`

Return a synthetic follow-up when edited code lacks fresh verification.


## agent.verify_hooks

### 模块文档

Verification-loop helpers for the ``pre_verify`` round-end gate.

When the agent has edited code and is about to verify/finish, the loop fires the
``pre_verify`` hook (user directives resolved by
:func:`hermes_cli.plugins.get_pre_verify_continue_message`). A directive keeps
the agent going one more turn — run a check, defer it, tidy the diff — instead of
stopping immediately.

The shipped coding guidance lives on the evidence-based verification-stop nudge
(``agent/verification_stop.py``), not as a second default stop gate. That keeps
the default token cost tied to the existing "missing verification evidence"
decision while preserving ``pre_verify`` for user/plugin policy.

### 顶层函数

#### def `max_verify_nudges(config: Optional[dict[str, Any]] = None) -> int`

Bound on consecutive ``pre_verify`` continue directives per turn (>= 0).

#### def `coding_verify_guidance(config: Optional[dict[str, Any]] = None) -> Optional[str]`

Return the optional guidance appended to verification-stop nudges.


## agent.vertex_adapter

### 模块文档

Vertex AI (Google Cloud) adapter for Hermes Agent.

Provides authentication and configuration for Vertex AI's OpenAI-compatible
endpoint. This allows Hermes to use Gemini models via Google Cloud with
enterprise-grade rate limits and quotas.

Requires: pip install google-auth

Environment variables honored (all optional):
  GOOGLE_APPLICATION_CREDENTIALS — path to a service account JSON file (secret).
  VERTEX_CREDENTIALS_PATH        — alias, takes precedence if set (secret).
  VERTEX_PROJECT_ID              — override the project_id embedded in creds.
  VERTEX_REGION                  — override default region ("global" unless set).

Non-secret routing settings (project_id, region) also live in config.yaml
under the ``vertex:`` section; env vars take precedence over config.yaml.

### 顶层函数

#### def `get_vertex_credentials(credentials_path: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]`

Return a (fresh access_token, project_id) pair or (None, None) on failure.

Caches the underlying Credentials object and refreshes it when within
5 minutes of expiry, so repeated calls don't thrash the token endpoint.

#### def `build_vertex_base_url(project_id: str, region: str = DEFAULT_REGION) -> str`

Build the OpenAI-compatible base URL for Vertex AI.

The `global` location uses a bare `aiplatform.googleapis.com` hostname,
while regional locations use `{region}-aiplatform.googleapis.com`.
Gemini 3.x preview models are only served via the global endpoint at
the time of writing.

#### def `get_vertex_config(credentials_path: Optional[str] = None, region: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]`

Resolve (access_token, base_url) for Vertex AI, or (None, None) on failure.

#### def `has_vertex_credentials() -> bool`

Fast check for whether Vertex credentials appear configured.

No network calls and no google-auth import — safe for provider
auto-detection and setup-status display. True when either a service
account JSON path is resolvable, or an explicit project ID is configured
(env or config.yaml, implying ADC is intended).


## agent.video_gen_provider

### 模块文档

Video Generation Provider ABC
=============================

Defines the pluggable-backend interface for video generation. Providers register
instances via ``PluginContext.register_video_gen_provider()``; the active one
(selected via ``video_gen.provider`` in ``config.yaml``) services every
``video_generate`` tool call.

Providers live in ``<repo>/plugins/video_gen/<name>/`` (built-in, auto-loaded
as ``kind: backend``) or ``~/.hermes/plugins/video_gen/<name>/`` (user, opt-in
via ``plugins.enabled``).

Mirrors the ``image_gen`` provider design (``agent/image_gen_provider.py``) so
the two surfaces stay learnable together.

Unified surface
---------------
One tool — ``video_generate`` — covers **text-to-video** and **image-to-video**.
The router is the presence of ``image_url``: if it's set, the provider routes
to its image-to-video endpoint; if it's omitted, the provider routes to
text-to-video. Users pick one **model family** (e.g. Pixverse v6, Veo 3.1,
Kling O3 Standard); the provider handles which underlying FAL/xAI endpoint
to hit.

Video edit and video extend are intentionally NOT exposed in this surface —
the inconsistency across backends is too large for one unified tool. If
those use cases warrant attention later they can ship as separate tools.

Response shape
--------------
All providers return a dict built by :func:`success_response` /
:func:`error_response`. Keys:

    success         bool
    video           str | None      URL or absolute file path
    model           str             provider-specific model identifier
    prompt          str             echoed prompt
    modality        str             "text" | "image" (which mode was used)
    aspect_ratio    str             provider-native (e.g. "16:9") or ""
    duration        int             seconds (0 if not applicable)
    provider        str             provider name (for diagnostics)
    error           str             only when success=False
    error_type      str             only when success=False

### class VideoGenProvider

> 继承: `abc.ABC` ｜ 方法数: 8（公开 8）

Abstract base class for a video generation backend.

Subclasses must implement :meth:`generate`. Everything else has sane
defaults — override only what your provider needs.

#### property `name(self) -> str`

Stable short identifier used in ``video_gen.provider`` config.

Lowercase, no spaces. Examples: ``xai``, ``fal``, ``google``.

#### property `display_name(self) -> str`

Human-readable label shown in ``hermes tools``. Defaults to ``name.title()``.

#### def `is_available(self) -> bool`

Return True when this provider can service calls.

Typically checks for a required API key and optional-dependency
import. Default: True.

#### def `list_models(self) -> List[Dict[str, Any]]`

Return catalog entries for ``hermes tools`` model picker.

Each entry represents a **model family** that supports text-to-video
and/or image-to-video routing internally::

    {
        "id": "veo-3.1",                       # required
        "display": "Veo 3.1",                  # optional; defaults to id
        "speed": "~60s",                       # optional
        "strengths": "...",                    # optional
        "price": "$0.20/s",                    # optional
        "modalities": ["text", "image"],       # optional, advisory
    }

Default: empty list (provider has no user-selectable models).

#### def `get_setup_schema(self) -> Dict[str, Any]`

Return provider metadata for the ``hermes tools`` picker.

#### def `default_model(self) -> Optional[str]`

Return the default model id, or None if not applicable.

#### def `capabilities(self) -> Dict[str, Any]`

Return what this provider supports.

Returned dict (all keys optional)::

    {
        "modalities": ["text", "image"],      # which inputs the backend accepts
        "aspect_ratios": ["16:9", "9:16", ...],
        "resolutions": ["720p", "1080p"],
        "max_duration": 15,                   # seconds
        "min_duration": 1,
        "supports_audio": True,
        "supports_negative_prompt": True,
        "max_reference_images": 7,
    }

Used by the tool layer for soft validation and by ``hermes tools``
for the picker. Default: text-only.

#### def `generate(self, prompt: str, model: Optional[str] = None, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, duration: Optional[int] = None, aspect_ratio: str = DEFAULT_ASPECT_RATIO, resolution: str = DEFAULT_RESOLUTION, negative_prompt: Optional[str] = None, audio: Optional[bool] = None, seed: Optional[int] = None, **kwargs: Any) -> Dict[str, Any]`

Generate a video from a prompt (text-to-video) or animate an image
(image-to-video).

Routing: if ``image_url`` is provided, the provider should route to
its image-to-video endpoint; otherwise text-to-video. The plugin
is responsible for picking the right underlying endpoint within
the user's chosen model family.

Implementations should return the dict from :func:`success_response`
or :func:`error_response`. ``kwargs`` may contain forward-compat
parameters future versions of the schema will expose —
implementations MUST ignore unknown keys (no TypeError).


### class OpenAICompatibleVideoGenProvider

> 继承: `VideoGenProvider` ｜ 方法数: 5（公开 2）

Generic text/image-to-video over the OpenAI ``client.videos`` API.

DeepInfra, OpenAI/Sora, and OpenRouter all expose the same
``POST /videos`` async-job shape (``create`` → poll → ``download_content``),
so the SDK call lives here once. A concrete backend only needs to declare
its identity and credentials::

    class FooVideoGenProvider(OpenAICompatibleVideoGenProvider):
        name = "foo"
        _env_key = "FOO_API_KEY"
        _default_base_url = "https://api.foo.com/v1/openai"
        def list_models(self):
            return [...]   # entries with an "id" key; default_model() uses [0]

``image_url`` routes to image-to-video; its absence routes to text-to-video.
Provider-specific fields (``image_url``/``negative_prompt``/``seed``) ride
in ``extra_body`` so they pass through the SDK unchanged.

#### def `is_available(self) -> bool`

#### def `generate(self, prompt: str, model: Optional[str] = None, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, duration: Optional[int] = None, aspect_ratio: str = DEFAULT_ASPECT_RATIO, resolution: str = DEFAULT_RESOLUTION, negative_prompt: Optional[str] = None, audio: Optional[bool] = None, seed: Optional[int] = None, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `save_b64_video(b64_data: str, prefix: str = 'video', extension: str = 'mp4') -> Path`

Decode base64 video data and write under ``$HERMES_HOME/cache/videos/``.

Returns the absolute :class:`Path` to the saved file.

Filename format: ``<prefix>_<YYYYMMDD_HHMMSS>_<short-uuid>.<ext>``.

#### def `save_bytes_video(raw: bytes, prefix: str = 'video', extension: str = 'mp4') -> Path`

Write raw video bytes (e.g. an HTTP download body) to the cache.

#### def `save_url_video(url: str, prefix: str = 'video', timeout: float = 180.0, max_bytes: int = 200 * 1024 * 1024) -> Path`

Download a video URL and write it under ``$HERMES_HOME/cache/videos/``.

The video twin of :func:`agent.image_gen_provider.save_url_image`: several
backends (DeepInfra, FAL) return an *ephemeral* delivery URL that expires
before a downstream consumer can fetch it, so we materialise the bytes
locally at tool-completion time. Streams with a size cap.

Raises on any network / HTTP / oversize error so callers can fall back to
returning the bare URL.

**异常**: `ValueError`

#### def `success_response(video: str, model: str, prompt: str, modality: str = 'text', aspect_ratio: str = '', duration: int = 0, provider: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

Build a uniform success response dict.

``video`` may be an HTTP URL or an absolute filesystem path.
``modality`` is ``"text"`` (text-to-video) or ``"image"`` (image-to-video) —
indicates which endpoint was actually hit, useful for diagnostics.

#### def `error_response(error: str, error_type: str = 'provider_error', provider: str = '', model: str = '', prompt: str = '', aspect_ratio: str = '') -> Dict[str, Any]`

Build a uniform error response dict.


## agent.video_gen_registry

### 模块文档

Video Generation Provider Registry
==================================

Central map of registered providers. Populated by plugins at import-time via
``PluginContext.register_video_gen_provider()``; consumed by the
``video_generate`` tool to dispatch each call to the active backend.

Active selection
----------------
The active provider is chosen by ``video_gen.provider`` in ``config.yaml``.
If unset, :func:`get_active_provider` applies fallback logic:

1. If exactly one *available* provider is registered, use it.
2. Otherwise return ``None`` (the tool surfaces a helpful error pointing
   the user at ``hermes tools``).

Mirrors ``agent/image_gen_registry.py`` so the two surfaces behave the
same: the unconfigured fallback is filtered by ``is_available()`` so a box
that has credentials for only one backend (e.g. DeepInfra, while the
``fal``/``xai`` plugins also register unconditionally) auto-selects it
instead of returning ``None``.

### 顶层函数

#### def `register_provider(provider: VideoGenProvider) -> None`

Register a video generation provider.

Re-registration (same ``name``) overwrites the previous entry and logs
a debug message — this makes hot-reload scenarios (tests, dev loops)
behave predictably.

**异常**: `TypeError`, `ValueError`

#### def `list_providers() -> List[VideoGenProvider]`

Return all registered providers, sorted by name.

#### def `get_provider(name: str) -> Optional[VideoGenProvider]`

Return the provider registered under *name*, or None.

#### def `get_active_provider() -> Optional[VideoGenProvider]`

Resolve the currently-active provider.

Reads ``video_gen.provider`` from config.yaml; falls back per the
module docstring.


## agent.web_search_provider

### 模块文档

Web Search Provider ABC
=======================

Defines the pluggable-backend interface for web search and content extraction.
Providers register instances via ``PluginContext.register_web_search_provider()``;
the active one (selected via ``web.search_backend`` / ``web.extract_backend`` /
``web.backend`` in ``config.yaml``) services every ``web_search`` /
``web_extract`` tool call.

Providers live in ``<repo>/plugins/web/<name>/`` (built-in, auto-loaded as
``kind: backend``) or ``~/.hermes/plugins/web/<name>/`` (user, opt-in via
``plugins.enabled``).

This ABC is the SINGLE plugin-facing surface for web providers — every
provider in the tree (brave-free, ddgs, searxng, exa, parallel, tavily,
firecrawl) implements it. The legacy in-tree ``tools.web_providers.base``
ABCs were deleted in PR #25182 along with the per-vendor inline helpers
in ``tools/web_tools.py``; the response-shape contract documented below
is preserved bit-for-bit so the tool wrapper does not have to translate.

Response shape (preserved from the legacy contract):

Search results::

    {
        "success": True,
        "data": {
            "web": [
                {"title": str, "url": str, "description": str, "position": int},
                ...
            ]
        }
    }

Extract results::

    {
        "success": True,
        "data": [
            {"url": str, "title": str, "content": str,
             "raw_content": str, "metadata": dict},
            ...
        ]
    }

On failure (either capability)::

    {"success": False, "error": str}

### class WebSearchProvider

> 继承: `abc.ABC` ｜ 方法数: 8（公开 8）

Abstract base class for a web search/extract backend.

Subclasses must implement :meth:`is_available` and at least one of
:meth:`search` / :meth:`extract`. The :meth:`supports_search` /
:meth:`supports_extract` capability flags let the registry route each
tool call to the right provider, and let multi-capability providers
(Firecrawl, Tavily, Exa, …) advertise multiple capabilities from a
single class.

#### property `name(self) -> str`

Stable short identifier used in ``web.search_backend`` /
``web.extract_backend`` / ``web.backend`` config keys.

Lowercase, no spaces; hyphens permitted to preserve existing
user-visible names. Examples: ``brave-free``, ``ddgs``,
``searxng``, ``firecrawl``.

#### property `display_name(self) -> str`

Human-readable label shown in ``hermes tools``. Defaults to ``name``.

#### def `is_available(self) -> bool`

Return True when this provider can service calls.

Typically a cheap check (env var present, optional Python dep
importable, instance URL set). Must NOT make network calls — this
runs at tool-registration time and on every ``hermes tools`` paint.

#### def `supports_search(self) -> bool`

Return True if this provider implements :meth:`search`.

#### def `supports_extract(self) -> bool`

Return True if this provider implements :meth:`extract`.

Both sync and async :meth:`extract` implementations are valid — the
dispatcher detects coroutine functions via
:func:`inspect.iscoroutinefunction` and awaits as needed. Sync
implementations that perform blocking I/O (HTTP, SDK calls) should
ideally wrap in :func:`asyncio.to_thread` at the call site; small
providers can keep their sync shape and let the dispatcher handle
threading.

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a web search.

Override when :meth:`supports_search` returns True. The default
raises NotImplementedError; callers should gate on
:meth:`supports_search` before calling.

**异常**: `NotImplementedError`

#### def `extract(self, urls: List[str], **kwargs: Any) -> Any`

Extract content from one or more URLs.

Override when :meth:`supports_extract` returns True. The default
raises NotImplementedError; callers should gate on
:meth:`supports_extract` before calling.

Return shape: a list of result dicts matching what the legacy
:func:`tools.web_tools.web_extract_tool` post-processing pipeline
expects::

    [
        {
            "url": str,
            "title": str,
            "content": str,
            "raw_content": str,
            "metadata": dict,           # optional
            "error": str,               # optional, only on per-URL failure
        },
        ...
    ]

Implementations MAY be ``async def`` — the dispatcher detects
coroutines via :func:`inspect.iscoroutinefunction` and awaits.

``kwargs`` may carry forward-compat fields (``format``, ``include_raw``,
``max_chars``) — implementations should ignore unknown keys.

**异常**: `expects`, `NotImplementedError`

#### def `get_setup_schema(self) -> Dict[str, Any]`

Return provider metadata for the ``hermes tools`` picker.

Used by ``hermes_cli/tools_config.py`` to inject this provider as a
row in the Web Search / Web Extract picker. Shape::

    {
        "name": "Brave Search (Free)",
        "badge": "free",
        "tag": "No paid tier needed — uses Brave's free API.",
        "env_vars": [
            {"key": "BRAVE_SEARCH_API_KEY",
             "prompt": "Brave Search API key",
             "url": "https://brave.com/search/api/"},
        ],
    }

Default: minimal entry derived from ``display_name``. Override to
expose API key prompts, badges, and instance URL fields.


### 顶层函数

#### def `get_provider_env(name: str) -> str`

Config-aware env lookup for web providers.

Resolves *name* via :func:`hermes_cli.config.get_env_value` (checks
``os.environ`` first, then ``~/.hermes/.env``) so credentials set
through Hermes' config layer are visible even when they were never
exported into the process environment — gateway sessions, delegate
children, and subprocess agent runs (issue #40190). Falls back to a
bare ``os.getenv`` when the config module is unavailable (stripped
installs, early import contexts).

Returns the stripped value, or ``""`` when unset.


## agent.web_search_registry

### 模块文档

Web Search Provider Registry
============================

Central map of registered web providers. Populated by plugins at import-time
via :meth:`PluginContext.register_web_search_provider`; consumed by the
``web_search`` and ``web_extract`` tool wrappers in :mod:`tools.web_tools` to
dispatch each call to the active backend.

Active selection
----------------
The active provider is chosen by configuration with this precedence:

1. ``web.search_backend`` / ``web.extract_backend``
   (per-capability override).
2. ``web.backend`` (shared fallback).
3. If exactly one capability-eligible provider is registered AND available,
   use it.
4. Legacy preference order — ``firecrawl`` → ``parallel`` → ``tavily`` →
   ``exa`` → ``searxng`` → ``brave-free`` → ``ddgs`` — filtered by
   availability. Matches the historic ``tools.web_tools._get_backend()``
   candidate order so installs that never set a config key keep landing
   on the same provider they did before the plugin migration.
5. Otherwise ``None`` — the tool surfaces a helpful error pointing at
   ``hermes tools``.

The capability filter (``supports_search`` / ``supports_extract``) is
applied at every step so a search-only provider (``brave-free``)
configured as ``web.extract_backend`` correctly falls through to an
extract-capable backend.

### 顶层函数

#### def `register_provider(provider: WebSearchProvider) -> None`

Register a web search/extract provider.

Re-registration (same ``name``) overwrites the previous entry and logs
a debug message — makes hot-reload scenarios (tests, dev loops) behave
predictably.

**异常**: `TypeError`, `ValueError`

#### def `list_providers() -> List[WebSearchProvider]`

Return all registered providers, sorted by name.

#### def `get_provider(name: str) -> Optional[WebSearchProvider]`

Return the provider registered under *name*, or None.

#### def `get_active_search_provider() -> Optional[WebSearchProvider]`

Resolve the currently-active web search provider.

Reads ``web.search_backend`` (preferred) or ``web.backend`` (shared
fallback) from config.yaml; falls back per the module docstring.

#### def `get_active_extract_provider() -> Optional[WebSearchProvider]`

Resolve the currently-active web extract provider.

Reads ``web.extract_backend`` (preferred) or ``web.backend`` (shared
fallback) from config.yaml; falls back per the module docstring.

