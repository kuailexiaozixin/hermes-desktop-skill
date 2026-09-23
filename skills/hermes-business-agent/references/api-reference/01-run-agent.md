# run_agent — AIAgent 主类与入口

> **模块**: `run_agent.py`
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: Hermes Agent 核心运行类 AIAgent 与模块入口 main()。

## 模块文档

AI Agent Runner with Tool Calling

This module provides a clean, standalone agent that can execute AI models
with tool calling capabilities. It handles the conversation loop, tool execution,
and response management.

Features:
- Automatic tool calling loop until completion
- Configurable model parameters
- Error handling and recovery
- Message history management
- Support for multiple model providers

Usage:
    from run_agent import AIAgent
    
    agent = AIAgent(base_url="http://localhost:30000/v1", model="claude-opus-4-20250514")
    response = agent.run_conversation("Tell me about the latest Python updates")

### 模块文档

AI Agent Runner with Tool Calling

This module provides a clean, standalone agent that can execute AI models
with tool calling capabilities. It handles the conversation loop, tool execution,
and response management.

Features:
- Automatic tool calling loop until completion
- Configurable model parameters
- Error handling and recovery
- Message history management
- Support for multiple model providers

Usage:
    from run_agent import AIAgent
    
    agent = AIAgent(base_url="http://localhost:30000/v1", model="claude-opus-4-20250514")
    response = agent.run_conversation("Tell me about the latest Python updates")

### class AIAgent

> 继承: `object` ｜ 方法数: 239（公开 18）

AI Agent with tool calling capabilities.

This class manages the conversation flow, tool execution, and response handling
for AI models that support function calling.

#### property `base_url(self) -> str`

#### property `base_url(self, value: str) -> None`

#### def `__init__(base_url: str = None, api_key: str = None, provider: str = None, api_mode: str = None, acp_command: str = None, acp_args: list[str] | None = None, command: str = None, args: list[str] | None = None, model: str = '', max_iterations: int = 90, tool_delay: float = 1.0, enabled_toolsets: List[str] = None, disabled_toolsets: List[str] = None, save_trajectories: bool = False, verbose_logging: bool = False, quiet_mode: bool = False, tool_progress_mode: str = 'all', ephemeral_system_prompt: str = None, log_prefix_chars: int = 100, log_prefix: str = '', providers_allowed: List[str] = None, providers_ignored: List[str] = None, providers_order: List[str] = None, provider_sort: str = None, provider_require_parameters: bool = False, provider_data_collection: str = None, openrouter_min_coding_score: Optional[float] = None, session_id: str = None, tool_progress_callback: callable = None, tool_start_callback: callable = None, tool_complete_callback: callable = None, thinking_callback: callable = None, reasoning_callback: callable = None, clarify_callback: callable = None, read_terminal_callback: callable = None, step_callback: callable = None, stream_delta_callback: callable = None, interim_assistant_callback: callable = None, tool_gen_callback: callable = None, status_callback: callable = None, notice_callback: callable = None, notice_clear_callback: callable = None, event_callback: Optional[Callable[[str, dict], None]] = None, reaction_callback: Optional[Callable[[str], None]] = None, max_tokens: int = None, reasoning_config: Dict[str, Any] = None, service_tier: str = None, request_overrides: Dict[str, Any] = None, prefill_messages: List[Dict[str, Any]] = None, platform: str = None, user_id: str = None, user_id_alt: str = None, user_name: str = None, chat_id: str = None, chat_name: str = None, chat_type: str = None, thread_id: str = None, gateway_session_key: str = None, skip_context_files: bool = False, load_soul_identity: bool = False, skip_memory: bool = False, session_db = None, parent_session_id: str = None, iteration_budget: IterationBudget = None, fallback_model: Dict[str, Any] = None, credential_pool = None, checkpoints_enabled: bool = False, checkpoint_max_snapshots: int = 20, checkpoint_max_total_size_mb: int = 500, checkpoint_max_file_size_mb: int = 10, pass_session_id: bool = False)`

Forwarder — see ``agent.agent_init.init_agent``.

#### def `reset_session_state(self, previous_messages: Optional[list] = None, old_session_id: Optional[str] = None, carry_over_context: bool = False)`

Reset all session-scoped token counters to 0 for a fresh session.

This method encapsulates the reset logic for all session-level metrics
including:
- Token usage counters (input, output, total, prompt, completion)
- Cache read/write tokens
- API call count
- Reasoning tokens
- Estimated cost tracking
- Context compressor internal counters

The method safely handles optional attributes (e.g., context compressor)
using ``hasattr`` checks.

When ``previous_messages`` / ``old_session_id`` / ``carry_over_context``
are provided, the active context engine is notified through the
full transition lifecycle (``_transition_context_engine_session``)
instead of a bare reset. Default callers pass nothing and keep the
existing reset-only behavior.

#### def `switch_model(self, new_model, new_provider, api_key = '', base_url = '', api_mode = '')`

Forwarder — see ``agent.agent_runtime_helpers.switch_model``.

#### def `interrupt(self, message: str = None) -> None`

Request the agent to interrupt its current tool-calling loop.

Call this from another thread (e.g., input handler, message receiver)
to gracefully stop the agent and process a new message.

Also signals long-running tool executions (e.g. terminal commands)
to terminate early, so the agent can respond immediately.

Args:
    message: Optional new message that triggered the interrupt.
             If provided, the agent will include this in its response context.

Example (CLI):
    # In a separate input thread:
    if user_typed_something:
        agent.interrupt(user_input)

Example (Messaging):
    # When new message arrives for active session:
    if session_has_running_agent:
        running_agent.interrupt(new_message.text)

#### def `clear_interrupt(self) -> None`

Clear any pending interrupt request and the per-thread tool interrupt signal.

#### def `steer(self, text: str) -> bool`

Inject a user message into the next tool result without interrupting.

Unlike interrupt(), this does NOT stop the current tool call. The
text is stashed and the agent loop appends it to the LAST tool
result's content once the current tool batch finishes. The model
sees the steer as part of the tool output on its next iteration.

Thread-safe: callable from gateway/CLI/TUI threads. Multiple calls
before the drain point concatenate with newlines.

Args:
    text: The user text to inject. Empty strings are ignored.

Returns:
    True if the steer was accepted, False if the text was empty.

#### def `get_rate_limit_state(self)`

Return the last captured RateLimitState, or None.

#### def `get_credits_state(self)`

Return the last captured CreditsState, or None.

#### def `get_credits_spent_micros(self)`

Session-cumulative micros spent = first_seen_remaining - current_remaining. None if no data.

#### def `get_activity_summary(self) -> dict`

Return a snapshot of the agent's current activity for diagnostics.

Called by the gateway timeout handler to report what the agent was doing
when it was killed, and by the periodic "still working" notifications.

#### def `shutdown_memory_provider(self, messages: list = None) -> None`

Shut down the memory provider and context engine — call at actual session boundaries.

This calls on_session_end() then shutdown_all() on the memory
manager, and on_session_end() on the context engine.
NOT called per-turn — only at CLI exit, /reset, gateway
session expiry, etc.

#### def `commit_memory_session(self, messages: list = None) -> None`

Trigger end-of-session extraction without tearing providers down.
Called when session_id rotates (e.g. /new, context compression);
providers keep their state and continue running under the old
session_id — they just flush pending extraction now.

#### def `release_clients(self) -> None`

Release LLM client resources WITHOUT tearing down session tool state.

Used by the gateway when evicting this agent from _agent_cache for
memory-management reasons (LRU cap or idle TTL) — the session may
resume at any time with a freshly-built AIAgent that reuses the
same task_id / session_id, so we must NOT kill:
  - process_registry entries for task_id (user's bg shells)
  - terminal sandbox for task_id (cwd, env, shell state)
  - browser daemon for task_id (open tabs, cookies)
  - memory provider (has its own lifecycle; keeps running)

We DO close:
  - OpenAI/httpx client pool (big chunk of held memory + sockets;
    the rebuilt agent gets a fresh client anyway)
  - Active child subagents (per-turn artefacts; safe to drop)

Safe to call multiple times.  Distinct from close() — which is the
hard teardown for actual session boundaries (/new, /reset, session
expiry).

#### def `close(self) -> None`

Release all resources held by this agent instance.

Cleans up subprocess resources that would otherwise become orphans:
- Background processes tracked in ProcessRegistry
- Terminal sandbox environments
- Browser daemon sessions
- Active child agents (subagent delegation)
- OpenAI/httpx client connections

Safe to call multiple times (idempotent).  Each cleanup step is
independently guarded so a failure in one does not prevent the rest.

#### property `is_interrupted(self) -> bool`

Check if an interrupt has been requested.

#### def `run_conversation(self, user_message: Any, system_message: str = None, conversation_history: List[Dict[str, Any]] = None, task_id: str = None, stream_callback: Optional[callable] = None, persist_user_message: Optional[Any] = None, persist_user_timestamp: Optional[float] = None, moa_config: Optional[dict[str, Any]] = None) -> Dict[str, Any]`

Forwarder — see ``agent.conversation_loop.run_conversation``.

#### def `chat(self, message: str, stream_callback: Optional[callable] = None) -> str`

Simple chat interface that returns just the final response.

Args:
    message (str): User message
    stream_callback: Optional callback invoked with each text delta during streaming.

Returns:
    str: Final assistant response


### 顶层函数

#### def `main(query: str = None, model: str = '', api_key: str = None, base_url: str = '', max_turns: int = 10, enabled_toolsets: str = None, disabled_toolsets: str = None, list_tools: bool = False, save_trajectories: bool = False, save_sample: bool = False, verbose: bool = False, log_prefix_chars: int = 20)`

Main function for running the agent directly.

Args:
    query (str): Natural language query for the agent. Defaults to Python 3.13 example.
    model (str): Model name to use (OpenRouter format: provider/model). Defaults to anthropic/claude-sonnet-4.6.
    api_key (str): API key for authentication. Uses OPENROUTER_API_KEY env var if not provided.
    base_url (str): Base URL for the model API. Defaults to https://openrouter.ai/api/v1
    max_turns (int): Maximum number of API call iterations. Defaults to 10.
    enabled_toolsets (str): Comma-separated list of toolsets to enable. Supports predefined
                          toolsets (e.g., "research", "development", "safe").
                          Multiple toolsets can be combined: "web,vision"
    disabled_toolsets (str): Comma-separated list of toolsets to disable (e.g., "terminal")
    list_tools (bool): Just list available tools and exit
    save_trajectories (bool): Save conversation trajectories to JSONL files (appends to trajectory_samples.jsonl). Defaults to False.
    save_sample (bool): Save a single trajectory sample to a UUID-named JSONL file for inspection. Defaults to False.
    verbose (bool): Enable verbose logging for debugging. Defaults to False.
    log_prefix_chars (int): Number of characters to show in log previews for tool calls/responses. Defaults to 20.

Toolset Examples:
    - "research": Web search, extract, crawl + vision tools

