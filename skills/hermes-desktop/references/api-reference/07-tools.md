# tools — 工具包（114 模块）

> **模块**: `tools/`（包，共 114 个模块）
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: 内置工具：代码执行、浏览器、委托、文件、MCP 等。

## tools.__init__

### 模块文档

Tools package namespace.

Keep package import side effects minimal. Importing ``tools`` should not
eagerly import the full tool stack, because several subsystems load tools while
``hermes_cli.config`` is still initializing.

Callers should import concrete submodules directly, for example:

    import tools.web_tools
    from tools import browser_tool

Python will resolve those submodules via the package path without needing them
to be re-exported here.

### 顶层函数

#### def `check_file_requirements()`

File tools only require terminal backend availability.


## tools.ansi_strip

### 模块文档

Strip ANSI escape sequences from subprocess output.

Used by terminal_tool, code_execution_tool, and process_registry to clean
command output before returning it to the model.  This prevents ANSI codes
from entering the model's context — which is the root cause of models
copying escape sequences into file writes.

Covers the full ECMA-48 spec: CSI (including private-mode ``?`` prefix,
colon-separated params, intermediate bytes), OSC (BEL and ST terminators),
DCS/SOS/PM/APC string sequences, nF multi-byte escapes, Fp/Fe/Fs
single-byte escapes, and 8-bit C1 control characters.

### 顶层函数

#### def `strip_ansi(text: str) -> str`

Remove ANSI escape sequences from text.

Returns the input unchanged (fast path) when no ESC or C1 bytes are
present.  Safe to call on any string — clean text passes through
with negligible overhead.

#### def `sanitize_display_text(text: str) -> str`

Sanitize stored/untrusted text before echoing it to a terminal.

Removes ANSI/ECMA-48 escape sequences AND bare control characters,
preserving only newlines and tabs (carriage returns are normalized
to newlines so ``\r``-overwrite spoofing can't hide content).

Use this when re-rendering conversation history or other persisted
text in a terminal UI (e.g. the ``/resume`` recap): a message that
arrived with embedded escapes — pasted content, gateway-origin
text, or model output echoing injected tool results — must not be
able to clear the screen, retitle the window, move the cursor, or
restyle adjacent UI when replayed. Rich's ``Text()`` does NOT
neutralize raw escape bytes, so sanitization has to happen before
display. Mirrors openai/codex#31494 (``sanitize_user_text``).


## tools.approval

### 模块文档

Dangerous command approval -- detection, prompting, and per-session state.

This module is the single source of truth for the dangerous command system:
- Pattern detection (DANGEROUS_PATTERNS, detect_dangerous_command)
- Per-session approval state (thread-safe, keyed by session_key)
- Approval prompting (CLI interactive + gateway async)
- Smart approval via auxiliary LLM (auto-approve low-risk commands)
- Permanent allowlist persistence (config.yaml)

### 顶层函数

#### def `set_hermes_interactive_context(interactive: bool) -> contextvars.Token`

Bind interactive mode for the current context (thread or asyncio task).

Use this instead of mutating ``os.environ["HERMES_INTERACTIVE"]`` from
concurrent executor threads. When unset (default), interactive detection
falls back to the ``HERMES_INTERACTIVE`` env var for legacy callers.

#### def `reset_hermes_interactive_context(token: contextvars.Token) -> None`

Restore the prior value from :func:`set_hermes_interactive_context`.

#### def `set_current_session_key(session_key: str) -> contextvars.Token[str]`

Bind the active approval session key to the current context.

#### def `reset_current_session_key(token: contextvars.Token[str]) -> None`

Restore the prior approval session key context.

#### def `set_current_observability_context(turn_id: str = '', tool_call_id: str = '') -> tuple[contextvars.Token[str], contextvars.Token[str]]`

Bind active tool correlation IDs to approval hooks.

#### def `reset_current_observability_context(tokens: tuple[contextvars.Token[str], contextvars.Token[str]]) -> None`

Restore prior approval hook correlation IDs.

#### def `get_current_session_key(default: str = 'default') -> str`

Return the active session key, preferring context-local state.

Resolution order:
1. approval-specific contextvars (set by gateway before agent.run)
2. session_context contextvars (set by _set_session_env)
3. os.environ fallback (CLI, cron, tests)

#### def `detect_hardline_command(command: str) -> tuple`

Check if a command matches hardline blocklist patterns.

Hardline patterns are NEVER bypassable, even in YOLO mode.

Returns:
    (is_hardline, description) or (False, None)

#### def `detect_dangerous_command(command: str) -> tuple`

Check if a command matches any dangerous patterns.

Returns:
    (is_dangerous, pattern_key, description) or (False, None, None)

#### def `register_gateway_notify(session_key: str, cb) -> None`

Register a per-session callback for sending approval requests to the user.

The callback signature is ``cb(approval_data: dict) -> None`` where
*approval_data* contains ``command``, ``description``, and
``pattern_keys``.  The callback bridges sync→async (runs in the agent
thread, must schedule the actual send on the event loop).

#### def `unregister_gateway_notify(session_key: str) -> None`

Unregister the per-session gateway approval callback.

Signals ALL blocked threads for this session so they don't hang forever
(e.g. when the agent run finishes or is interrupted).

#### def `resolve_gateway_approval(session_key: str, choice: str, resolve_all: bool = False, reason: Optional[str] = None) -> int`

Called by the gateway's /approve or /deny handler to unblock
waiting agent thread(s).

When *resolve_all* is True every pending approval in the session is
resolved at once (``/approve all``).  Otherwise only the oldest one
is resolved (FIFO).

*reason* is an optional free-text explanation attached to an explicit
deny (``/deny <reason>``).  It is relayed back to the agent in the
BLOCKED message so it can adapt instead of only hearing "denied".

Returns the number of approvals resolved (0 means nothing was pending).

#### def `has_blocking_approval(session_key: str) -> bool`

Check if a session has one or more blocking gateway approvals waiting.

#### def `submit_pending(session_key: str, approval: dict)`

Store a pending approval request for a session.

#### def `approve_session(session_key: str, pattern_key: str)`

Approve a pattern for this session only.

#### def `enable_session_yolo(session_key: str) -> None`

Enable YOLO bypass for a single session key.

#### def `disable_session_yolo(session_key: str) -> None`

Disable YOLO bypass for a single session key.

#### def `clear_session(session_key: str) -> None`

Remove all approval and yolo state for a given session.

#### def `is_session_yolo_enabled(session_key: str) -> bool`

Return True when YOLO bypass is enabled for a specific session.

#### def `is_current_session_yolo_enabled() -> bool`

Return True when the active approval session has YOLO bypass enabled.

#### def `is_approved(session_key: str, pattern_key: str) -> bool`

Check if a pattern is approved (session-scoped or permanent).

Accept both the current canonical key and the legacy regex-derived key so
existing command_allowlist entries continue to work after key migrations.

#### def `approve_permanent(pattern_key: str)`

Add a pattern to the permanent allowlist.

#### def `load_permanent(patterns: set)`

Bulk-load permanent allowlist entries from config.

#### def `load_permanent_allowlist() -> set`

Load permanently allowed command patterns from config.

Also syncs them into the approval module so is_approved() works for
patterns added via 'always' in a previous session.

#### def `save_permanent_allowlist(patterns: set)`

Save permanently allowed command patterns to config.

#### def `prompt_dangerous_approval(command: str, description: str, timeout_seconds: int | None = None, allow_permanent: bool = True, approval_callback = None, smart_denied: bool = False) -> str`

Prompt the user to approve a dangerous command (CLI only).

Args:
    allow_permanent: When False, hide the [a]lways option (used when
        tirith warnings are present, since broad permanent allowlisting
        is inappropriate for content-level security findings).
    smart_denied: When True, this is an owner override of a Smart DENY.
        Offer only one-operation approval or denial.
    approval_callback: Optional callback registered by the CLI for
        prompt_toolkit integration. Signature:
        (command, description, *, allow_permanent=True,
        smart_denied=False) -> str. Legacy callback signatures remain
        supported when ``smart_denied`` is false.

Returns: 'once', 'session', 'always', or 'deny'

#### def `is_approval_bypass_active() -> bool`

Return True when the user has opted out of Hermes approval prompts.

Collapses the canonical three-source bypass check used across the codebase
into one place:
  - process-scoped ``--yolo`` / ``HERMES_YOLO_MODE`` (frozen at import time
    so a mid-process skill can't flip it — a prompt-injection escalation
    path; see ``_YOLO_MODE_FROZEN`` above),
  - the session-scoped gateway ``/yolo`` toggle,
  - ``approvals.mode: off`` in config.

This is the pure-bypass sub-expression only. Callers that also honor a
hardline blocklist / permanent allowlist must check those separately.

#### def `check_dangerous_command(command: str, env_type: str, approval_callback = None, has_host_access: bool = False) -> dict`

Check if a command is dangerous and handle approval.

This is the main entry point called by terminal_tool before executing
any command. It orchestrates detection, session checks, and prompting.

Args:
    command: The shell command to check.
    env_type: Terminal backend type ('local', 'ssh', 'docker', etc.).
    approval_callback: Optional CLI callback for interactive prompts.
    has_host_access: True when a Docker sandbox bind-mounts host paths,
        so its commands can reach the host and must not skip approval.

Returns:
    {"approved": True/False, "message": str or None, ...}

#### def `request_tool_approval(tool_name: str, reason: str, rule_key: str = '', approval_callback = None) -> dict`

Escalate an arbitrary tool call to the human-approval gate.

This is the entry point for a plugin ``pre_tool_call`` hook that returns
``{"action": "approve", "message": ...}``: instead of the plugin vetoing
the call (``action: block``) or silently allowing it, it asks the SAME
human gate that Tier-2 dangerous shell patterns use. The LLM cannot skip
or bypass this — the tool call is intercepted before execution.

It reuses the existing approval primitives (session/permanent allowlist,
``prompt_dangerous_approval`` for CLI, ``submit_pending`` for the gateway
callback, ``[o]nce/[s]ession/[a]lways/[d]eny``, timeout fail-closed) so
behavior is identical to a dangerous-command match — only the trigger
(a plugin rule on any tool) differs.

Args:
    tool_name: The tool being gated (e.g. ``"write_file"``, ``"terminal"``).
    reason: Human-facing message from the plugin explaining why approval
        is needed (rendered in the prompt).
    rule_key: Optional stable identifier the plugin can supply to control
        the ``[a]lways`` allowlist grain. When empty, the key is derived
        from ``tool_name`` + a hash of ``reason`` so that DISTINCT reasons
        on the same tool persist independently (answering ``[a]lways`` to
        "write to ~/.ssh" does NOT auto-approve a later "send email" rule
        on the same tool).
    approval_callback: Optional CLI callback for interactive prompts
        (same contract as ``check_dangerous_command``).

Returns:
    ``{"approved": True, "message": None}`` when allowed, or
    ``{"approved": False, "message": <reason>, ...}`` when denied /
    blocked. Shape matches ``check_dangerous_command`` so callers handle
    both paths identically.

Non-interactive contexts: cron jobs honor ``approvals.cron_mode`` (parity
with dangerous commands); any OTHER non-interactive non-gateway context
(a bare script with no ``HERMES_INTERACTIVE``) fails CLOSED — a plugin-
flagged action never runs ungated without a human.

#### def `check_all_command_guards(command: str, env_type: str, approval_callback = None, has_host_access: bool = False) -> dict`

Run all pre-exec security checks and return a single approval decision.

Gathers findings from tirith and dangerous-command detection, then
presents them as a single combined approval request. This prevents
a gateway force=True replay from bypassing one check when only the
other was shown to the user.

``has_host_access`` is True when a Docker sandbox bind-mounts host paths;
such a session is no longer isolated, so it goes through the normal flow
instead of the container fast-path.

#### def `check_execute_code_guard(code: str, env_type: str, has_host_access: bool = False) -> dict`

Approve an execute_code script before its child process is spawned.

execute_code runs arbitrary local Python — the script can call
``subprocess``, ``os.system``, ``ctypes``, or other process/file APIs
directly, none of which pass through ``terminal()`` /
``DANGEROUS_PATTERNS``. In gateway/ask contexts we fail closed by approving
the script as a whole before it runs (#30882). Returns the same dict
contract as ``check_all_command_guards``.

Scope (documented limitation, #30882): in a purely local non-interactive
non-gateway session (no TTY, not gateway, not cron-deny) this returns
approved — matching the existing terminal auto-approve contract. The
hardline floor still blocks catastrophic ``terminal()`` commands the script
issues; running arbitrary code headlessly without any approval surface is
trusted-by-config (set a gateway/ask surface or ``approvals.cron_mode`` to
require approval).

#### def `request_elicitation_consent(message: str, description: str, timeout_seconds: int | None = None, surface: str = 'mcp-elicitation') -> str`

Route an MCP elicitation request to whichever approval surface owns
the active session and return a normalized result.

Gateway sessions (Telegram, Slack, Discord, etc.) go through
``_await_gateway_decision`` so the notify_cb posts a message and the
agent thread blocks until the user responds via the platform UI.
CLI/TUI sessions go through ``prompt_dangerous_approval``.

Always fails closed: missing notify_cb in a gateway session, timeouts,
and exceptions all map to ``"decline"`` so a server treats them as
"user did not approve" rather than retrying or hanging.

Returns one of ``"accept" | "decline" | "cancel"``.


## tools.async_delegation

### 模块文档

Async (background) delegation registry.

Backs ``delegate_task(background=true)``: the parent agent dispatches a
subagent that runs on a module-level daemon executor and returns a handle
immediately, so the user and the model can keep working while the child runs.

When the child finishes, a completion event is pushed onto the SHARED
``process_registry.completion_queue`` with ``type="async_delegation"``. The
CLI (``cli.py`` process_loop) and gateway (``_run_process_watcher`` /
``completion_queue`` drain) already poll that queue while the agent is idle
and forge a fresh user/internal turn from each event. We deliberately reuse
that rail rather than reaching into a running agent loop:

  - completions surface as a NEW turn when the agent is idle, never spliced
    between a tool result and an assistant message. That keeps strict
    message-role alternation legal and the prompt cache intact (hard
    invariant: never mutate past context).
  - we inherit the queue's de-dup, crash-recovery checkpoint, and the
    existing CLI + gateway drain wiring for free — no new drain loops in the
    two largest files in the repo.

The completion payload carries a RICH, self-contained task-source block (the
original goal, the context the parent supplied, toolsets, model, dispatch
time, status, and the full result summary). When the result re-enters the
conversation the parent may be deep in unrelated context and won't remember
why the subagent existed; the block lets it either use the result or
re-dispatch if the world has moved on.

This module owns ONLY the async lifecycle. The actual child build + run is
delegated back to ``delegate_tool._run_single_child`` via an injected
runner, so all the credential leasing, heartbeat, timeout, and result-shaping
logic stays in one place.

### 顶层函数

#### def `recover_abandoned_delegations() -> int`

Classify records whose owning process disappeared as outcome unknown.

#### def `restore_undelivered_completions(target_queue) -> int`

Enqueue durable pending completions as fresh turns after process start.

Every restored event is stamped ``restored=True`` (in-memory only — the
stamp is added after the durable payload is deserialized and is never
persisted). Restored events originate from a *previous* process, so no
consumer in THIS process implicitly owns them: drain paths that run
without an ownership filter (the legacy single-session behavior) must
leave them queued for a consumer that can positively prove ownership,
otherwise a brand-new session adopts a dead session's delegation
results seconds after boot (#64484).

#### def `mark_completion_delivered(delegation_id: str) -> bool`

Atomically acknowledge successful injection of a durable completion.

#### def `claim_completion_delivery(delegation_id: str, claim_id: str) -> bool`

Claim one pending completion across competing consumers/processes.

#### def `claim_event_delivery(evt: Dict[str, Any], consumer: str) -> Optional[str]`

Claim a durable delegation event; non-durable events need no token.

#### def `release_completion_delivery(delegation_id: str, claim_id: str) -> bool`

Release a failed delivery claim so another consumer may retry.

#### def `complete_completion_delivery(delegation_id: str, claim_id: str) -> bool`

Acknowledge acceptance for the consumer holding this claim.

#### def `complete_event_delivery(evt: Dict[str, Any], claim_id: str) -> None`

#### def `release_event_delivery(evt: Dict[str, Any], claim_id: str) -> None`

#### def `get_durable_delegation(delegation_id: str) -> Optional[Dict[str, Any]]`

#### def `active_count() -> int`

Number of async delegations currently running.

#### def `dispatch_async_delegation(goal: str, context: Optional[str], toolsets: Optional[List[str]], role: str, model: Optional[str], session_key: str, parent_session_id: Optional[str] = None, runner: Callable[[], Dict[str, Any]], origin_ui_session_id: str = '', interrupt_fn: Optional[Callable[[], None]] = None, max_async_children: int = _DEFAULT_MAX_ASYNC_CHILDREN) -> Dict[str, Any]`

Spawn ``runner`` on the daemon executor and return a handle immediately.

Parameters
----------
goal, context, toolsets, role, model
    The dispatch-time task spec, captured verbatim for the rich
    completion block.
session_key
    The gateway session_key (from ``tools.approval.get_current_session_key``)
    captured on the parent thread BEFORE dispatch, because the daemon
    worker thread won't carry the contextvar. Used to route the
    completion back to the originating session.
parent_session_id
    The durable ``state.db`` session id of the parent agent that spawned
    the delegation. Carried on the completion event so the gateway can
    pin routing to the spawning session instead of recovering the latest
    ``ended_at IS NULL`` row for the peer tuple (#57498).
runner
    Zero-arg callable that builds + runs the child and returns the same
    result dict ``_run_single_child`` produces. Runs on the worker thread.
interrupt_fn
    Optional callable to signal the child to stop (used on shutdown /
    explicit cancel).
max_async_children
    Concurrency cap. When at capacity the dispatch is REJECTED (the caller
    should fall back to sync or tell the user) rather than queued, so a
    runaway model can't pile up unbounded background work.

Returns
-------
dict
    ``{"status": "dispatched", "delegation_id": ...}`` on success, or
    ``{"status": "rejected", "error": ...}`` when at capacity.

#### def `dispatch_async_delegation_batch(goals: List[str], context: Optional[str], toolsets: Optional[List[str]], role: str, model: Optional[str], session_key: str, parent_session_id: Optional[str] = None, runner: Callable[[], Dict[str, Any]], origin_ui_session_id: str = '', interrupt_fn: Optional[Callable[[], None]] = None, max_async_children: int = _DEFAULT_MAX_ASYNC_CHILDREN, delegation_id: Optional[str] = None) -> Dict[str, Any]`

Dispatch a WHOLE fan-out batch as ONE background unit.

Unlike ``dispatch_async_delegation`` (which backs a single subagent),
``runner`` here runs the entire batch — it builds and joins on every child
in parallel and returns the combined ``{"results": [...],
"total_duration_seconds": N}`` dict that the synchronous path would have
returned. We occupy ONE async slot for the whole batch (the in-batch
parallelism is bounded separately by ``max_concurrent_children``), so a
single ``delegate_task`` fan-out never exhausts the async pool by itself.

When the batch finishes, a SINGLE completion event is pushed onto the
shared ``process_registry.completion_queue`` carrying the full per-task
``results`` list, so the consolidated summaries re-enter the conversation
as one message once every child is done — the chat is never blocked while
they run.

Returns ``{"status": "dispatched", "delegation_id": ...}`` on success or
``{"status": "rejected", "error": ...}`` when the async pool is at
capacity.

#### def `list_async_delegations() -> List[Dict[str, Any]]`

Snapshot of async delegations (running + recently completed).

Safe to call from any thread. Excludes the non-serialisable interrupt_fn.

#### def `interrupt_all(reason: str = 'shutdown') -> int`

Signal every running async delegation to stop. Returns how many.

Used on ``/stop`` and gateway shutdown so a dangling background subagent
can't keep burning tokens with no one listening. The child still emits a
completion event (status='interrupted') via the normal finalize path.

#### def `interrupt_for_session(session_key: str = '', origin_ui_session_id: str = '', parent_session_id: str = '', reason: str = 'session_end') -> int`

Signal running async delegations owned by ONE session to stop.

A delegation's lifecycle is bound to the session that spawned it: when
that session ends, its in-flight background subagents must end with it —
a completed orphan would otherwise sit on the shared completion queue
with no live owner, either leaking into another chat or burning tokens
with no one listening (#55578).

Selectors (any matching field claims the record):
- ``origin_ui_session_id``: the live TUI tab/window that commissioned it.
- ``session_key``: the durable routing key captured at dispatch.
- ``parent_session_id``: the spawning agent's durable session-db id —
  the right selector for gateway chats, whose ``session_key`` (the
  platform conversation key) SURVIVES a ``/new`` reset while the
  session id rotates.

Returns how many were interrupted.


## tools.binary_extensions

### 模块文档

Binary file extensions to skip for text-based operations.

These files can't be meaningfully compared as text and are often large.
Ported from free-code src/constants/files.ts.

### 顶层函数

#### def `has_binary_extension(path: str) -> bool`

Check if a file path has a binary extension. Pure string check, no I/O.


## tools.blueprints

### 模块文档

Blueprints: shareable plain-language automations layered on skills + cron.

A "blueprint" is NOT a new object type. It is an ordinary skill (a SKILL.md the
agent loads) that additionally declares an automation schedule in its
frontmatter:

    metadata:
      hermes:
        blueprint:
          schedule: "0 9 * * *"     # presence of `blueprint:` marks it runnable
          deliver: origin            # optional (default "origin")
          prompt: "..."              # optional task instruction for the run
          no_agent: false            # optional

Because a blueprint is just a skill, it flows through the ENTIRE existing
skills-hub pipeline for free — search, inspect, quarantine, security scan,
install, lock-file provenance, audit log, taps, the centralized index, and
`hermes skills publish` for sharing. No new source type, no new store, no new
transport. This module is the thin bridge between that skill metadata and the
existing cron `create_job()` API:

  * ``parse_blueprint(skill_md_text)``  -> BlueprintSpec | None
  * ``blueprint_spec_for_installed(name)`` -> BlueprintSpec | None
  * ``create_blueprint_job(spec, ...)`` -> the created cron job dict
  * ``export_blueprint(job, body)``      -> a shareable SKILL.md string

The dev guide's "Extend, Don't Duplicate" rule is the whole design: the blueprint
is a skill, the schedule is a cron job, sharing is the existing publish/tap/
index path.

### class BlueprintError

> 继承: `ValueError` ｜ 方法数: 0（公开 0）

Raised when a blueprint block is present but malformed.


### class BlueprintSpec

> 继承: `object` ｜ 方法数: 0（公开 0）

Parsed ``metadata.hermes.blueprint`` automation spec for a skill.


### 顶层函数

#### def `parse_blueprint(skill_md_text: str) -> Optional[BlueprintSpec]`

Extract a BlueprintSpec from a SKILL.md string, or None if not a blueprint.

A skill is a blueprint iff ``metadata.hermes.blueprint`` is a mapping containing
a non-empty ``schedule``. Raises BlueprintError if the block exists but is
structurally invalid (so a typo surfaces instead of silently no-op'ing).

**异常**: `BlueprintError`

#### def `blueprint_spec_for_installed(skill_name: str) -> Optional[BlueprintSpec]`

Locate an installed skill's SKILL.md and parse its blueprint block.

Searches the standard skills tree for ``<skill_name>/SKILL.md``. Returns
None if the skill isn't found or isn't a blueprint.

#### def `blueprint_to_job_spec(spec: BlueprintSpec, name: Optional[str] = None) -> Dict[str, Any]`

Build the ``cron.jobs.create_job`` kwargs dict for a BlueprintSpec.

This is the single source of truth for translating a blueprint into a job.
Both the direct ``create_blueprint_job`` path and the suggestion path
(``register_blueprint_suggestion``) build on it, so a blueprint scheduled now and
a blueprint accepted from a suggestion produce an identical job.

#### def `create_blueprint_job(spec: BlueprintSpec, origin: Optional[Dict[str, Any]] = None, name: Optional[str] = None) -> Dict[str, Any]`

Create the cron job described by a BlueprintSpec via the existing cron API.

The blueprint's skill is loaded before the run (cron ``skills=[name]``); the
optional ``prompt`` becomes the task instruction. Delivery, model, and
toolsets carry through. Returns the created job dict.

#### def `register_blueprint_suggestion(spec: BlueprintSpec) -> Optional[Dict[str, Any]]`

Turn an installed blueprint into a pending Suggested Cron Job.

Blueprints are source ``blueprint`` of the unified suggestion surface: installing
a skill that carries a ``blueprint:`` block does NOT auto-schedule it — it
registers a suggestion the user accepts (or dismisses) like any other.
Returns the suggestion record, or None if it was skipped (already
seen/dismissed, backlog full, etc.).

#### def `export_blueprint(job: Dict[str, Any], body: str, blueprint_name: Optional[str] = None) -> str`

Render a shareable blueprint SKILL.md from an existing cron job dict.

The inverse of ``create_blueprint_job``: take a cron job a user already built
and emit a SKILL.md (with a ``metadata.hermes.blueprint`` block) they can hand
to ``hermes skills publish`` to share. ``body`` is the plain-language
description / instructions that become the SKILL.md body.


## tools.browser_camofox

### 模块文档

Camofox browser backend — local anti-detection browser via REST API.

Camofox-browser is a self-hosted Node.js server wrapping Camoufox (Firefox
fork with C++ fingerprint spoofing).  It exposes a REST API that maps 1:1
to our browser tool interface: accessibility snapshots with element refs,
click/type/scroll by ref, screenshots, etc.

When ``CAMOFOX_URL`` is set (e.g. ``http://localhost:9377``), the browser
tools route through this module instead of the ``agent-browser`` CLI.

Setup::

    # Option 1: npm
    git clone https://github.com/jo-inc/camofox-browser && cd camofox-browser
    npm install && npm start   # downloads Camoufox (~300MB) on first run

    # Option 2: Docker
    docker run -p 9377:9377 -e CAMOFOX_PORT=9377 jo-inc/camofox-browser

Then set ``CAMOFOX_URL=http://localhost:9377`` in ``~/.hermes/.env``.
For Docker Camofox, optionally set ``CAMOFOX_REWRITE_LOOPBACK_URLS=true``
so page URLs like ``http://127.0.0.1:3000`` are opened inside the
container as ``http://host.docker.internal:3000``.

### 顶层函数

#### def `get_camofox_url() -> str`

Return the configured Camofox server URL, or empty string.

#### def `is_camofox_mode() -> bool`

True when Camofox backend is configured and no CDP override is active.

A CDP override takes priority over Camofox so the browser tools operate on
the real CDP browser (and a CDP backend is treated as non-local for SSRF
checks) instead of being silently routed to Camofox. The override may come
from the ``BROWSER_CDP_URL`` env var (set by ``/browser connect``) OR a
persistent ``browser.cdp_url`` in config.yaml — both are honored, matching
``browser_tool._get_cdp_override()``'s precedence. (Previously only the env
var suppressed Camofox, so ``CAMOFOX_URL`` + a config CDP override still
routed navigation through Camofox.)

#### def `check_camofox_available() -> bool`

Verify the Camofox server is reachable.

#### def `get_vnc_url() -> Optional[str]`

Return the VNC URL if the Camofox server exposes one, or None.

#### def `camofox_soft_cleanup(task_id: Optional[str] = None) -> bool`

Release the in-memory session without destroying the server-side context.

When managed persistence is enabled the browser profile (and its cookies)
must survive across agent tasks.  This helper drops only the local tracking
entry and returns ``True``.  When managed persistence is *not* enabled it
does nothing and returns ``False`` so the caller can fall back to
:func:`camofox_close`.

#### def `camofox_navigate(url: str, task_id: Optional[str] = None) -> str`

Navigate to a URL via Camofox.

#### def `camofox_snapshot(full: bool = False, task_id: Optional[str] = None, user_task: Optional[str] = None) -> str`

Get accessibility tree snapshot from Camofox.

#### def `camofox_click(ref: str, task_id: Optional[str] = None) -> str`

Click an element by ref via Camofox.

#### def `camofox_type(ref: str, text: str, task_id: Optional[str] = None) -> str`

Type text into an element by ref via Camofox.

#### def `camofox_scroll(direction: str, task_id: Optional[str] = None) -> str`

Scroll the page via Camofox.

#### def `camofox_back(task_id: Optional[str] = None) -> str`

Navigate back via Camofox.

#### def `camofox_press(key: str, task_id: Optional[str] = None) -> str`

Press a keyboard key via Camofox.

#### def `camofox_close(task_id: Optional[str] = None) -> str`

Close the browser session via Camofox.

#### def `camofox_get_images(task_id: Optional[str] = None) -> str`

Get images on the current page via Camofox.

Extracts image information from the accessibility tree snapshot,
since Camofox does not expose a dedicated /images endpoint.

#### def `camofox_vision(question: str, annotate: bool = False, task_id: Optional[str] = None) -> str`

Take a screenshot and analyze it with vision AI via Camofox.

#### def `camofox_console(clear: bool = False, task_id: Optional[str] = None) -> str`

Get console output — limited support in Camofox.

Camofox does not expose browser console logs via its REST API.
Returns an empty result with a note.


## tools.browser_camofox_state

### 模块文档

Hermes-managed Camofox state helpers.

Provides profile-scoped identity and state directory paths for Camofox
persistent browser profiles.  When managed persistence is enabled, Hermes
sends a deterministic userId derived from the active profile so that
Camofox can map it to the same persistent browser profile directory
across restarts.

### 顶层函数

#### def `get_camofox_state_dir() -> Path`

Return the profile-scoped root directory for Camofox persistence.

#### def `get_camofox_identity(task_id: Optional[str] = None) -> Dict[str, str]`

Return the stable Hermes-managed Camofox identity for this profile.

The user identity is profile-scoped (same Hermes profile = same userId).
The session key is scoped to the logical browser task so newly created
tabs within the same profile reuse the same identity contract.


## tools.browser_cdp_tool

### 模块文档

Raw Chrome DevTools Protocol (CDP) passthrough tool.

Exposes a single tool, ``browser_cdp``, that sends arbitrary CDP commands to
the browser's DevTools WebSocket endpoint.  Works when a CDP URL is
configured — either via ``/browser connect`` (sets ``BROWSER_CDP_URL``) or
``browser.cdp_url`` in ``config.yaml`` — or when a CDP-backed cloud provider
session is active.

This is the escape hatch for browser operations not covered by the main
browser tool surface (``browser_navigate``, ``browser_click``,
``browser_console``, etc.) — handling native dialogs, iframe-scoped
evaluation, cookie/network control, low-level tab management, etc.

Method reference: https://chromedevtools.github.io/devtools-protocol/

### 顶层函数

#### def `browser_cdp(method: str, params: Optional[Dict[str, Any]] = None, target_id: Optional[str] = None, frame_id: Optional[str] = None, timeout: float = 30.0, task_id: Optional[str] = None) -> str`

Send a raw CDP command.  See ``CDP_DOCS_URL`` for method documentation.

Args:
    method: CDP method name, e.g. ``"Target.getTargets"``.
    params: Method-specific parameters; defaults to ``{}``.
    target_id: Optional target/tab ID for page-level methods.  When set,
        we first attach to the target (``flatten=True``) and send
        ``method`` with the resulting ``sessionId``.  Uses a fresh
        stateless CDP connection.
    frame_id: Optional cross-origin (OOPIF) iframe ``frame_id`` from
        ``browser_snapshot.frame_tree.children[]``.  When set (and the
        frame is an OOPIF with a live session tracked by the CDP
        supervisor), routes the call through the supervisor's existing
        WebSocket — which is how you Runtime.evaluate *inside* an
        iframe on backends where per-call fresh CDP connections would
        hit signed-URL expiry (Browserbase) or expensive reattach.
    timeout: Seconds to wait for the call to complete.
    task_id: Task identifier for supervisor lookup.  When ``frame_id``
        is set, this identifies which task's supervisor to use; the
        handler will default to ``"default"`` otherwise.

Returns:
    JSON string ``{"success": True, "method": ..., "result": {...}}`` on
    success, or ``{"error": "..."}`` on failure.


## tools.browser_dialog_tool

### 模块文档

Agent-facing tool: respond to a native JS dialog captured by the CDP supervisor.

This tool is response-only — the agent first reads ``pending_dialogs`` from
``browser_snapshot`` output, then calls ``browser_dialog(action=...)`` to
accept or dismiss.

Gated on the same ``_browser_cdp_check`` as ``browser_cdp`` so it only
appears when a CDP endpoint is reachable (Browserbase with a
``connectUrl``, local Chromium-family browser via ``/browser connect``, or
``browser.cdp_url`` set in config).

See ``website/docs/developer-guide/browser-supervisor.md`` for the full
design.

### 顶层函数

#### def `browser_dialog(action: str, prompt_text: Optional[str] = None, dialog_id: Optional[str] = None, task_id: Optional[str] = None) -> str`

Respond to a pending dialog on the active task's CDP supervisor.


## tools.browser_supervisor

### 模块文档

Persistent CDP supervisor for browser dialog + frame detection.

One ``CDPSupervisor`` runs per Hermes ``task_id`` that has a reachable CDP
endpoint. It holds a single persistent WebSocket to the backend, subscribes
to ``Page`` / ``Runtime`` / ``Target`` events on every attached session
(top-level page and every OOPIF / worker target that auto-attaches), and
surfaces observable state — pending dialogs and frame tree — through a
thread-safe snapshot object that tool handlers consume synchronously.

The supervisor is NOT in the agent's tool schema. Its output reaches the
agent via two channels:

1. ``browser_snapshot`` merges supervisor state into its return payload
   (see ``tools/browser_tool.py``).
2. ``browser_dialog`` tool responds to a pending dialog by calling
   ``respond_to_dialog()`` on the active supervisor.

Design spec: ``website/docs/developer-guide/browser-supervisor.md``.

### class PendingDialog

> 继承: `object` ｜ 方法数: 1（公开 1）

A JS dialog currently open on some frame's session.

#### def `to_dict(self) -> Dict[str, Any]`


### class DialogRecord

> 继承: `object` ｜ 方法数: 1（公开 1）

A historical record of a dialog that was opened and then handled.

Retained in ``recent_dialogs`` for a short window so agents on backends
that auto-dismiss dialogs server-side (Browserbase) can still observe
that a dialog fired, even though they couldn't respond to it.

#### def `to_dict(self) -> Dict[str, Any]`


### class FrameInfo

> 继承: `object` ｜ 方法数: 1（公开 1）

One frame in the page's frame tree.

``is_oopif`` means the frame has its own CDP target (separate process,
reachable via ``cdp_session_id``). Same-origin / srcdoc iframes share
the parent process and have ``is_oopif=False`` + ``cdp_session_id=None``.

#### def `to_dict(self) -> Dict[str, Any]`


### class ConsoleEvent

> 继承: `object` ｜ 方法数: 0（公开 0）

Ring buffer entry for console + exception traffic.


### class SupervisorSnapshot

> 继承: `object` ｜ 方法数: 1（公开 1）

Read-only snapshot of supervisor state.

Frozen dataclass so tool handlers can freely dereference without
worrying about mutation under their feet.

#### def `to_dict(self) -> Dict[str, Any]`

Serialize for inclusion in ``browser_snapshot`` output.


### class CDPSupervisor

> 继承: `object` ｜ 方法数: 29（公开 5）

One supervisor per (task_id, cdp_url) pair.

Lifecycle:
  * ``start()`` — kicked off by ``SupervisorRegistry.get_or_start``; spawns
    a daemon thread running its own asyncio loop, connects the WebSocket,
    attaches to the first page target, enables domains, starts
    auto-attaching to child targets.
  * ``snapshot()`` — sync, thread-safe, called from tool handlers.
  * ``respond_to_dialog(action, ...)`` — sync bridge; schedules a coroutine
    on the supervisor's loop and waits (with timeout) for the CDP ack.
  * ``stop()`` — cancels task, closes WebSocket, joins thread.

All CDP I/O lives on the supervisor's own loop. External callers never
touch the loop directly; they go through the sync API above.

#### def `__init__(task_id: str, cdp_url: str, dialog_policy: str = DEFAULT_DIALOG_POLICY, dialog_timeout_s: float = DEFAULT_DIALOG_TIMEOUT_S) -> None`

**异常**: `ValueError`

#### def `start(self, timeout: float = 15.0) -> None`

Launch the background loop and wait until attachment is complete.

Raises whatever exception attach failed with (connect error, bad
WebSocket URL, CDP domain enable failure, etc.). On success, the
supervisor is fully wired up — pending-dialog events will be captured
as of the moment ``start()`` returns.

**异常**: `TimeoutError`, `RuntimeError`

#### def `stop(self, timeout: float = 5.0) -> None`

Cancel the supervisor task and join the thread.

#### def `snapshot(self) -> SupervisorSnapshot`

Return an immutable snapshot of current state.

#### def `respond_to_dialog(self, action: str, prompt_text: Optional[str] = None, dialog_id: Optional[str] = None, timeout: float = 10.0) -> Dict[str, Any]`

Accept/dismiss a pending dialog. Sync bridge onto the supervisor loop.

Returns ``{"ok": True, "dialog": {...}}`` on success,
``{"ok": False, "error": "..."}`` on a recoverable error (no dialog,
ambiguous dialog_id, supervisor inactive).

#### def `evaluate_runtime(self, expression: str, return_by_value: bool = True, await_promise: bool = True, timeout: float = 10.0) -> Dict[str, Any]`

Evaluate ``expression`` in the page's Runtime context over the live WS.

Reuses the supervisor's already-connected WebSocket — zero subprocess
startup cost vs the agent-browser CLI ``eval`` command (which does
fork+exec+Node-startup+CDP-setup on every call).

Returns a dict shaped like ``{"ok": True, "result": <value>, "result_type": "..."}``
on success, or ``{"ok": False, "error": "..."}`` on failure.

``return_by_value=True`` asks the browser to JSON-serialize the result
before sending it back, matching DevTools-console semantics for
primitive / plain-object expressions. For DOM nodes or non-serializable
objects, the browser returns a description string in ``result_type``.

**异常**: `RuntimeError`


## tools.browser_tool

### 模块文档

Browser Tool Module

This module provides browser automation tools using agent-browser CLI.  It
supports multiple backends — **Browser Use** (cloud, default for Nous
subscribers), **Browserbase** (cloud, direct credentials), and **local
Chromium** — with identical agent-facing behaviour.  The backend is
auto-detected from config and available credentials.

The tool uses agent-browser's accessibility tree (ariaSnapshot) for text-based
page representation, making it ideal for LLM agents without vision capabilities.

Features:
- **Local mode** (default): zero-cost headless Chromium via agent-browser.
  Works on Linux servers without a display.  One-time setup:
  ``agent-browser install`` (downloads Chromium) or
  ``agent-browser install --with-deps`` (also installs system libraries for
  Debian/Ubuntu/Docker).
- **Cloud mode**: Browserbase or Browser Use cloud execution when configured.
- Session isolation per task ID
- Text-based page snapshots using accessibility tree
- Element interaction via ref selectors (@e1, @e2, etc.)
- Task-aware content extraction using LLM summarization
- Automatic cleanup of browser sessions

Environment Variables:
- BROWSERBASE_API_KEY: API key for direct Browserbase cloud mode
- BROWSERBASE_PROJECT_ID: Project ID for direct Browserbase cloud mode
- BROWSER_USE_API_KEY: API key for direct Browser Use cloud mode
- BROWSERBASE_PROXIES: Enable/disable residential proxies (default: "true")
- BROWSERBASE_ADVANCED_STEALTH: Enable advanced stealth mode with custom Chromium,
  requires Scale Plan (default: "false")
- BROWSERBASE_KEEP_ALIVE: Enable keepAlive for session reconnection after disconnects,
  requires paid plan (default: "true")
- BROWSERBASE_SESSION_TIMEOUT: Custom session timeout in seconds (max 21600 = 6h).
  Set to extend beyond project default. Common values: 600 (10min), 1800 (30min) (default: none)

Usage:
    from tools.browser_tool import browser_navigate, browser_snapshot, browser_click

    # Navigate to a page
    result = browser_navigate("https://example.com", task_id="task_123")

    # Get page snapshot
    snapshot = browser_snapshot(task_id="task_123")

    # Click an element
    browser_click("@e5", task_id="task_123")

### 顶层函数

#### def `browser_navigate(url: str, task_id: Optional[str] = None) -> str`

Navigate to a URL in the browser.

Args:
    url: The URL to navigate to
    task_id: Task identifier for session isolation

Returns:
    JSON string with navigation result (includes stealth features info on first nav)

#### def `browser_snapshot(full: bool = False, task_id: Optional[str] = None, user_task: Optional[str] = None) -> str`

Get a text-based snapshot of the current page's accessibility tree.

Args:
    full: If True, return complete snapshot. If False, return compact view.
    task_id: Task identifier for session isolation
    user_task: The user's current task (for task-aware extraction)

Returns:
    JSON string with page snapshot

#### def `browser_click(ref: str, task_id: Optional[str] = None) -> str`

Click on an element.

Args:
    ref: Element reference (e.g., "@e5")
    task_id: Task identifier for session isolation

Returns:
    JSON string with click result

#### def `browser_type(ref: str, text: str, task_id: Optional[str] = None) -> str`

Type text into an input field.

Args:
    ref: Element reference (e.g., "@e3")
    text: Text to type
    task_id: Task identifier for session isolation

Returns:
    JSON string with type result

#### def `browser_scroll(direction: str, task_id: Optional[str] = None) -> str`

Scroll the page.

Args:
    direction: "up" or "down"
    task_id: Task identifier for session isolation

Returns:
    JSON string with scroll result

#### def `browser_back(task_id: Optional[str] = None) -> str`

Navigate back in browser history.

Args:
    task_id: Task identifier for session isolation

Returns:
    JSON string with navigation result

#### def `browser_press(key: str, task_id: Optional[str] = None) -> str`

Press a keyboard key.

Args:
    key: Key to press (e.g., "Enter", "Tab")
    task_id: Task identifier for session isolation

Returns:
    JSON string with key press result

#### def `browser_console(clear: bool = False, expression: Optional[str] = None, task_id: Optional[str] = None) -> str`

Get browser console messages and JavaScript errors, or evaluate JS in the page.

When ``expression`` is provided, evaluates JavaScript in the page context
(like the DevTools console) and returns the result.  Otherwise returns
console output (log/warn/error/info) and uncaught exceptions.

Args:
    clear: If True, clear the message/error buffers after reading
    expression: JavaScript expression to evaluate in the page context
    task_id: Task identifier for session isolation

Returns:
    JSON string with console messages/errors, or eval result

#### def `browser_get_images(task_id: Optional[str] = None) -> str`

Get all images on the current page.

Args:
    task_id: Task identifier for session isolation

Returns:
    JSON string with list of images (src and alt)

#### def `browser_vision(question: str, annotate: bool = False, task_id: Optional[str] = None) -> Union[str, Dict[str, Any]]`

Take a screenshot of the current page for visual inspection.

Captures what's visually displayed in the browser. When the active model
supports native vision, the screenshot is attached directly to the
conversation so the model can inspect it on the next turn; otherwise Hermes
falls back to the auxiliary vision model and returns a text analysis. Useful
for visual content the text-based snapshot may not capture (CAPTCHAs,
verification challenges, images, complex layouts, etc.).

The screenshot is saved persistently and its file path is returned so it
can be shared with users via MEDIA:<path> in the response.

Args:
    question: What you want to know about the page visually
    annotate: If True, overlay numbered [N] labels on interactive elements
    task_id: Task identifier for session isolation

Returns:
    A JSON string with vision analysis results and screenshot_path, or a
    multimodal tool-result envelope carrying the screenshot and metadata.

#### def `cleanup_browser(task_id: Optional[str] = None) -> None`

Clean up browser session(s) for a task.

Called automatically when a task completes or when inactivity timeout is reached.
Closes both the agent-browser/Browserbase session and Camofox sessions.

When ``task_id`` is a bare task identifier (no ``::local`` suffix), reaps
BOTH the cloud/primary session AND any hybrid-routing local sidecar that
may have been spawned for LAN/localhost URLs in the same task.  When
``task_id`` already carries a ``::local`` suffix (called from the inactivity
cleanup loop against a specific session key), reaps only that one.

Args:
    task_id: Task identifier (or explicit session key)

#### def `cleanup_all_browsers() -> None`

Clean up all active browser sessions.

Useful for cleanup on shutdown.

#### def `check_browser_requirements() -> bool`

Check if browser tool requirements are met.

In **local mode** (no cloud provider configured): the ``agent-browser``
CLI must be findable. Chrome/Chromium is required for the default Chrome
engine and for fallback/screenshot paths, but not for Lightpanda-only text
navigation/snapshot workflows.

In **cloud mode** (Browserbase, Browser Use, or Firecrawl): the CLI
and the provider's required credentials must be present. The cloud
provider hosts its own Chromium, so no local browser binary is needed.

Returns:
    True if all requirements are met, False otherwise

#### def `check_browser_vision_requirements() -> bool`

Whether ``browser_vision`` should be advertised to the model.

Requires BOTH a working browser (``check_browser_requirements``) AND a
resolvable vision backend. Without the vision check, the tool stays in
the model's tool list even when no vision provider is configured, then
fails at call time with a cryptic provider-side error like
``unknown variant `image_url`, expected `text``` (issue #31179).


## tools.budget_config

### 模块文档

Configurable budget constants for tool result persistence.

Per-tool resolution: pinned > config overrides > registry > default.

### class BudgetConfig

> 继承: `object` ｜ 方法数: 1（公开 1）

Immutable budget constants for the 3-layer tool result persistence system.

Layer 2 (per-result): resolve_threshold(tool_name) -> threshold in chars.
Layer 3 (per-turn):   turn_budget -> aggregate char budget across all tool
                      results in a single assistant turn.
Preview:              preview_size -> inline snippet size after persistence.

#### def `resolve_threshold(self, tool_name: str) -> int | float`

Resolve the persistence threshold for a tool.

Priority: pinned -> tool_overrides -> registry per-tool -> default.

The registry per-tool value is capped at ``default_result_size`` so a
context-scaled budget (small model) actually constrains tools that
register a large fixed ``max_result_size_chars`` (web/terminal/x_search
all register 100K). For the default budget this is a no-op because both
equal 100K; for a scaled-down budget it prevents a per-tool registry
value from re-inflating the cap past the model's window (#23767).


### 顶层函数

#### def `budget_for_context_window(context_length: int | None) -> BudgetConfig`

Return a BudgetConfig scaled to the active model's context window.

The fixed defaults (100K result / 200K turn chars) are correct for large
(200K+ token) models but blind to small ones: on a 65K-token model a single
tool result persisted at the 100K-char threshold, or a 200K-char turn
budget (~50K tokens), can by itself approach or exceed the whole window and
force an oversized request (#23767).

Scaling keeps large models byte-identical to today (the proportional value
is clamped to the existing defaults as a CAP) while shrinking the budget for
small models proportionally to their window, floored so a usable preview
always survives.


## tools.checkpoint_manager

### 模块文档

Checkpoint Manager — Transparent filesystem snapshots via a single shared
shadow git store.

Creates automatic snapshots of working directories before file-mutating
operations (``write_file``, ``patch``, ``terminal`` with destructive flags),
triggered once per conversation turn.  Provides rollback to any previous
checkpoint.

This is NOT a tool — the LLM never sees it.  It's transparent infrastructure
controlled by the ``checkpoints`` config flag or ``--checkpoints`` CLI flag.

Storage layout (single shared store, git objects deduplicated across projects)
-----------------------------------------------------------------------------

    ~/.hermes/checkpoints/
        store/                          — single bare-ish git repo
            HEAD, config, objects/      — standard git internals (shared)
            refs/hermes/<hash16>        — per-project branch tip
            indexes/<hash16>            — per-project git index
            projects/<hash16>.json      — {workdir, created_at, last_touch}
            info/exclude                — default excludes (shared)
        .last_prune                     — auto-prune idempotency marker
        legacy-<timestamp>/             — archived pre-v2 per-project shadow
                                          repos (auto-migrated on first init)

Why a single store?
-------------------

The pre-v2 design kept a full shadow repo per working directory.  Each one
re-stored most of the project's files under its own ``objects/`` tree, with
zero sharing across worktrees of the same project.  A single user with a
dozen worktrees of the same repo burned ~40 MB each (~500 MB total) storing
the same blobs over and over.  A single shared store lets git's content-
addressable object DB deduplicate across projects and across turns, so adding
a new worktree costs near-zero.

The shadow store uses ``GIT_DIR`` + ``GIT_WORK_TREE`` + ``GIT_INDEX_FILE``
so no git state leaks into the user's project directory.

Auto-maintenance
----------------

Shadow state accumulates over time.  ``prune_checkpoints`` deletes refs whose
recorded working directory no longer exists (orphan) or whose last touch is
older than ``retention_days`` (stale), then runs ``git gc --prune=now`` to
reclaim object storage.  A size-cap pass drops the oldest checkpoints per
project until total store size is under ``max_total_size_mb``.

### class CheckpointManager

> 继承: `object` ｜ 方法数: 12（公开 6）

Manages automatic filesystem checkpoints.

Designed to be owned by AIAgent.  Call ``new_turn()`` at the start of
each conversation turn and ``ensure_checkpoint(dir, reason)`` before
any file-mutating tool call.  The manager deduplicates so at most one
snapshot is taken per directory per turn.

Parameters
----------
enabled : bool
    Master switch (from config / CLI flag).
max_snapshots : int
    Keep at most this many checkpoints per directory.
max_total_size_mb : int
    Hard ceiling on total store size.  Oldest checkpoints per project
    are dropped when the store exceeds this after a commit.
max_file_size_mb : int
    Skip adding any single file larger than this to a checkpoint.
    (Implemented via ``.gitignore`` excludes + a post-stage size check.)

#### def `__init__(enabled: bool = False, max_snapshots: int = 20, max_total_size_mb: int = 500, max_file_size_mb: int = 10)`

#### def `new_turn(self) -> None`

Reset per-turn dedup.  Call at the start of each agent iteration.

#### def `ensure_checkpoint(self, working_dir: str, reason: str = 'auto') -> bool`

Take a checkpoint if enabled and not already done this turn.

Returns True if a checkpoint was taken, False otherwise.
Never raises — all errors are silently logged.

#### def `list_checkpoints(self, working_dir: str) -> List[Dict]`

List available checkpoints for a directory (most recent first).

#### def `diff(self, working_dir: str, commit_hash: str) -> Dict`

Show diff between a checkpoint and the current working tree.

#### def `restore(self, working_dir: str, commit_hash: str, file_path: str = None) -> Dict`

Restore files to a checkpoint state.

#### def `get_working_dir_for_path(self, file_path: str) -> str`

Resolve a file path to its working directory for checkpointing.


### 顶层函数

#### def `format_checkpoint_list(checkpoints: List[Dict], directory: str) -> str`

Format checkpoint list for display to user.

#### def `prune_checkpoints(retention_days: int = 7, delete_orphans: bool = True, checkpoint_base: Optional[Path] = None, max_total_size_mb: int = 0) -> Dict[str, int]`

Delete stale/orphan checkpoints and reclaim store space.

A project entry is deleted when either:

* ``delete_orphans=True`` and its ``workdir`` no longer exists on disk
  (the original project was deleted / moved); OR
* its ``last_touch`` is older than ``retention_days`` days.

Additionally, if ``max_total_size_mb > 0`` and the store exceeds that
after orphan/stale pruning, the oldest commit per remaining project is
dropped until the store is under the cap.

Legacy-archive dirs (``legacy-*``) older than ``retention_days`` are
also deleted.

Returns a dict with counts ``{"scanned", "deleted_orphan",
"deleted_stale", "errors", "bytes_freed"}``.

Never raises — maintenance must never block interactive startup.

#### def `maybe_auto_prune_checkpoints(retention_days: int = 7, min_interval_hours: int = 24, delete_orphans: bool = True, checkpoint_base: Optional[Path] = None, max_total_size_mb: int = 0) -> Dict[str, object]`

Idempotent wrapper around ``prune_checkpoints`` for startup hooks.

Writes ``CHECKPOINT_BASE/.last_prune`` on completion so subsequent
calls within ``min_interval_hours`` short-circuit.

Returns ``{"skipped": bool, "result": prune_checkpoints-dict,
"error": optional str}``.

#### def `store_status(checkpoint_base: Optional[Path] = None) -> Dict`

Return a summary of the shadow store.

``{"base": path, "store_size_bytes": N, "legacy_size_bytes": N,
   "total_size_bytes": N, "project_count": N, "projects": [...],
   "legacy_archives": [...]}``

#### def `clear_all(checkpoint_base: Optional[Path] = None) -> Dict[str, int]`

Nuke the entire checkpoint base (store + legacy).  Irreversible.

Returns ``{"bytes_freed": N, "deleted": bool}``.

#### def `clear_legacy(checkpoint_base: Optional[Path] = None) -> Dict[str, int]`

Delete all ``legacy-*`` archive directories.

Returns ``{"bytes_freed": N, "deleted": count}``.


## tools.clarify_gateway

### 模块文档

Gateway-side clarify primitive (blocking event-based queue).

The ``clarify`` tool needs to ask the user a question and block the agent
thread until they respond.  In CLI mode this is trivial — ``input()`` is
synchronous.  In gateway mode the agent runs on a worker thread while the
event loop handles the user's reply, so we need a thread-safe primitive
that:

  * stores a pending clarify request (with a generated ``clarify_id``),
  * blocks the agent thread on an ``Event``,
  * resolves the wait when the gateway's button-callback or text-intercept
    fires ``resolve_gateway_clarify(clarify_id, response)``,
  * supports timeouts so a user who never responds does NOT hang the agent
    thread forever (which would also pin the gateway's running-agent guard).

State is module-level (same shape as ``tools.approval``) so platform
adapters can call ``resolve_gateway_clarify`` without holding a back-
reference to the ``GatewayRunner`` instance.

Two delivery paths from the adapter:

  1. **Button UI** — adapters override ``send_clarify`` to render inline
     buttons (e.g. Telegram ``InlineKeyboardMarkup``).  The button
     callback resolves with the chosen string.  A final "Other (type
     answer)" button enters text-capture mode for free-form responses.

  2. **Text fallback** — adapters without rich UI render a numbered list.
     The user replies with a number ("2") or with free text; the gateway's
     ``_handle_message`` intercepts the reply and resolves directly.

### 顶层函数

#### def `register(clarify_id: str, session_key: str, question: str, choices: Optional[List[str]]) -> _ClarifyEntry`

Register a pending clarify request and return the entry.

The caller (gateway clarify_callback) will then send the prompt to the
user and block on ``wait_for_response(clarify_id, timeout)``.

#### def `wait_for_response(clarify_id: str, timeout: float) -> Optional[str]`

Block on the entry's event until resolved or timeout fires.

Polls in 1-second slices so the agent's inactivity heartbeat keeps
firing — without this, ``Event.wait(timeout=600)`` blocks the thread
for 10 minutes with zero activity touches and the gateway's inactivity
watchdog kills the agent while the user is still typing.

Returns the resolved response string, or ``None`` on timeout.

#### def `resolve_gateway_clarify(clarify_id: str, response: str) -> bool`

Unblock the agent thread waiting on ``clarify_id``.

Returns True if an entry was found and resolved, False otherwise
(already resolved, expired, or never existed).

#### def `get_pending_for_session(session_key: str, include_choice_prompts: bool = False) -> Optional[_ClarifyEntry]`

Return the oldest pending clarify entry for a session, or None.

By default this only returns entries awaiting free-form text (open-ended
clarifies, or a multi-choice clarify after the user picked ``Other``).
Gateways may pass ``include_choice_prompts=True`` when the user has typed
directly in response to an active multi-choice prompt; in that case the
oldest unresolved clarify is returned so the text can resolve it instead
of being queued as an unrelated follow-up turn.

#### def `resolve_text_response_for_session(session_key: str, response: str) -> bool`

Resolve the oldest pending clarify in ``session_key`` from typed text.

#### def `mark_awaiting_text(clarify_id: str) -> bool`

Flip an entry into text-capture mode (user picked the 'Other' button).

Returns True if the entry exists and was flipped, False otherwise.

#### def `has_pending(session_key: str) -> bool`

Return True when this session has at least one pending clarify entry.

#### def `clear_session(session_key: str) -> int`

Resolve and drop every pending clarify for a session.

Used by session-boundary cleanup (e.g. ``/new``, gateway shutdown,
cached-agent eviction) so blocked agent threads don't hang past the
end of their session.  Returns the number of entries cancelled.

#### def `get_clarify_timeout() -> int`

Read the clarify response timeout (seconds) from config.

Defaults to 3600 (1 hour) — long enough that a user who steps away
(meeting, AFK, slow to read) still finds a live entry when they tap
the button, short enough that a genuinely abandoned prompt eventually
unblocks the agent thread instead of pinning the running-agent guard
forever.  The old 600s default evicted the entry mid-think, so a late
tap landed on a dead entry and the agent hung on ``running: clarify``
(#32762).

Reads ``agent.clarify_timeout`` from config.yaml.

#### def `register_notify(session_key: str, cb: Callable[[_ClarifyEntry], None]) -> None`

Register a per-session notify callback used by ``clarify_callback``.

#### def `unregister_notify(session_key: str) -> None`

Drop the per-session notify callback and cancel any pending clarify entries.

#### def `get_notify(session_key: str) -> Optional[Callable[[_ClarifyEntry], None]]`


## tools.clarify_tool

### 模块文档

Clarify Tool Module - Interactive Clarifying Questions

Allows the agent to present structured multiple-choice questions or open-ended
prompts to the user. In CLI mode, choices are navigable with arrow keys. On
messaging platforms, choices are rendered as a numbered list.

The actual user-interaction logic lives in the platform layer (cli.py for CLI,
gateway/run.py for messaging). This module defines the schema, validation, and
a thin dispatcher that delegates to a platform-provided callback.

### 顶层函数

#### def `clarify_tool(question: str, choices: Optional[List[str]] = None, callback: Optional[Callable] = None) -> str`

Ask the user a question, optionally with multiple-choice options.

Args:
    question: The question text to present.
    choices:  Up to 4 predefined answer choices. When omitted the
              question is purely open-ended.
    callback: Platform-provided function that handles the actual UI
              interaction. Signature: callback(question, choices) -> str.
              Injected by the agent runner (cli.py / gateway).

Returns:
    JSON string with the user's response.

#### def `check_clarify_requirements() -> bool`

Clarify tool has no external requirements -- always available.


## tools.close_terminal_tool

### 模块文档

Close a read-only agent terminal tab in the Hermes desktop GUI.

Each ``terminal(background=true)`` process is mirrored as a read-only tab in the
desktop's terminal pane. This tool lets the agent drop a tab it no longer needs
to show — WITHOUT killing the process (use ``process(action='kill')`` for that).
The output keeps buffering and the user can reopen the tab from the status stack.

It routes through the process registry's ``on_close`` sink, which the desktop
gateway wires to emit a ``terminal.close`` event the renderer handles. Like
``read_terminal`` it is gated on ``HERMES_DESKTOP`` so it never appears outside
the GUI.

### 顶层函数

#### def `close_terminal_tool(process_id: str) -> str`

Ask the desktop GUI to close a background process's read-only tab.

#### def `check_close_terminal_requirements() -> bool`

Desktop GUI only — HERMES_DESKTOP is set on the gateway the app spawns.


## tools.code_execution_tool

### 模块文档

Code Execution Tool -- Programmatic Tool Calling (PTC)

Lets the LLM write a Python script that calls Hermes tools via RPC,
collapsing multi-step tool chains into a single inference turn.

Architecture (two transports):

  **Local backend (UDS):**
  1. Parent generates a `hermes_tools.py` stub module with UDS RPC functions
  2. Parent opens a Unix domain socket and starts an RPC listener thread
  3. Parent spawns a child process that runs the LLM's script
  4. Tool calls travel over the UDS back to the parent for dispatch

  **Remote backends (file-based RPC):**
  1. Parent generates `hermes_tools.py` with file-based RPC stubs
  2. Parent ships both files to the remote environment
  3. Script runs inside the terminal backend (Docker/SSH/Modal/Daytona/etc.)
  4. Tool calls are written as request files; a polling thread on the parent
     reads them via env.execute(), dispatches, and writes response files
  5. The script polls for response files and continues

In both cases, only the script's stdout is returned to the LLM; intermediate
tool results never enter the context window.

Platform: Linux / macOS only (Unix domain sockets for local). Disabled on Windows.
Remote execution additionally requires Python 3 in the terminal backend.

### 顶层函数

#### def `check_sandbox_requirements() -> bool`

Code execution sandbox requires a POSIX OS for Unix domain sockets.

#### def `generate_hermes_tools_module(enabled_tools: List[str], transport: str = 'uds') -> str`

Build the source code for the hermes_tools.py stub module.

Only tools in both SANDBOX_ALLOWED_TOOLS and enabled_tools get stubs.

Args:
    enabled_tools: Tool names enabled in the current session.
    transport: ``"uds"`` for Unix domain socket (local backend) or
               ``"file"`` for file-based RPC (remote backends).

#### def `execute_code(code: str, task_id: Optional[str] = None, enabled_tools: Optional[List[str]] = None) -> str`

Run a Python script in a sandboxed child process with RPC access
to a subset of Hermes tools.

Dispatches to the local (UDS) or remote (file-based RPC) path
depending on the configured terminal backend.

Args:
    code:          Python source code to execute.
    task_id:       Session task ID for tool isolation (terminal env, etc.).
    enabled_tools: Tool names enabled in the current session. The sandbox
                   gets the intersection with SANDBOX_ALLOWED_TOOLS.

Returns:
    JSON string with execution results.

#### def `build_execute_code_schema(enabled_sandbox_tools: set = None, mode: str = None) -> dict`

Build the execute_code schema with description listing only enabled tools.

When tools are disabled via ``hermes tools`` (e.g. web is turned off),
the schema description should NOT mention web_search / web_extract —
otherwise the model thinks they are available and keeps trying to use them.

``mode`` controls the working-directory sentence in the description:
  - ``'strict'``: scripts run in a temp dir (not the session's CWD)
  - ``'project'`` (default): scripts run in the session's CWD with the
    active venv's python
If ``mode`` is None, the current ``code_execution.mode`` config is read.


## tools.computer_use.__init__

### 模块文档

Computer use toolset — universal (any-model) macOS desktop control.

Architecture
------------
This toolset drives macOS apps through cua-driver's background computer-use
primitive (SkyLight private SPIs for focus-without-raise + pid-scoped event
posting). Unlike #4562's pyautogui backend, it does NOT steal the user's
cursor, keyboard focus, or Space — the agent and the user can co-work on the
same machine.

Unlike #4562's Anthropic-native `computer_20251124` tool, the schema here is
a plain OpenAI function-calling schema that every tool-capable model can
drive. Vision models get SOM (set-of-mark) captures — a screenshot with
numbered overlays on every interactable element plus the AX tree — so they
click by element index instead of pixel coordinates. Non-vision models can
drive via the AX tree alone.

Wiring
------
* `tool.py`       — registers the `computer_use` tool via tools.registry.
* `backend.py`    — abstract `ComputerUseBackend`; swappable implementation.
* `cua_backend.py`— default backend; speaks MCP over stdio to `cua-driver`.
* `schema.py`     — shared schema + docstring for the generic `computer_use`
                    tool. Model-agnostic.
* `capture.py`    — screenshot post-processing (PNG coercion, sizing, SOM
                    overlay if the backend did not).

The outer integration points (multimodal tool-result plumbing, screenshot
eviction in the Anthropic adapter, image-aware token estimation, the
COMPUTER_USE_GUIDANCE prompt block, approval hook, and the skill) live
alongside this package. See agent/anthropic_adapter.py and
agent/prompt_builder.py for the salvaged hunks from PR #4562.

## tools.computer_use.backend

### 模块文档

Abstract backend interface for computer use.

Any implementation (cua-driver over MCP, pyautogui, noop, future Linux/Windows)
must return the shape described below. All methods synchronous; async is
handled inside the backend implementation if needed.

### class UIElement

> 继承: `object` ｜ 方法数: 1（公开 1）

One interactable element on the current screen.

#### def `center(self) -> Tuple[int, int]`


### class CaptureResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of a screen capture call.

At least one of png_b64 / elements is populated depending on capture mode:
  * mode="vision" → png_b64 only
  * mode="ax"     → elements only
  * mode="som"    → both (default): PNG already has numbered overlays
                     drawn by the backend, and `elements` holds the
                     matching index → element mapping.


### class ActionResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of any action (click / type / scroll / drag / key / wait).

Beyond the transport-level ``ok`` flag, this carries cua-driver's
structured action verdict so the model can follow the documented
verify → escalate ladder (NousResearch/hermes-agent#67052). ``ok`` stays
tool/transport success only — it is NOT the semantic verdict. Read
``effect`` / ``escalation`` to decide the next rung. All structured
fields are optional and additive: an older driver that omits
``structuredContent`` leaves them ``None`` and behavior is unchanged.


### class ComputerUseBackend

> 继承: `ABC` ｜ 方法数: 14（公开 14）

Lifecycle: `start()` before first use, `stop()` at shutdown.

#### def `start(self) -> None`

#### def `stop(self) -> None`

#### def `is_available(self) -> bool`

Return True if the backend can be used on this host right now.

Used by check_fn gating and by the post-setup wizard.

#### def `capture(self, mode: str = 'som', app: Optional[str] = None, pid: Optional[int] = None, window_id: Optional[int] = None) -> CaptureResult`

#### def `click(self, element: Optional[int] = None, x: Optional[int] = None, y: Optional[int] = None, button: str = 'left', click_count: int = 1, modifiers: Optional[List[str]] = None, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `drag(self, from_element: Optional[int] = None, to_element: Optional[int] = None, from_xy: Optional[Tuple[int, int]] = None, to_xy: Optional[Tuple[int, int]] = None, button: str = 'left', modifiers: Optional[List[str]] = None, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `scroll(self, direction: str, amount: int = 3, element: Optional[int] = None, x: Optional[int] = None, y: Optional[int] = None, modifiers: Optional[List[str]] = None, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `type_text(self, text: str, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `key(self, keys: str, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

Send a key combo, e.g. 'cmd+s', 'ctrl+alt+t', 'return'.

#### def `list_apps(self) -> List[Dict[str, Any]]`

Return running apps with bundle IDs, PIDs, window counts.

#### def `list_windows(self) -> List[Dict[str, Any]]`

Return visible native windows with PID and window identifiers.

Optional compatibility hook: backends that predate window discovery
remain instantiable and simply report no windows.

#### def `focus_app(self, app: str, raise_window: bool = False) -> ActionResult`

Route input to `app` (by name or bundle ID). Default: focus without raise.

#### def `set_value(self, value: str, element: Optional[int] = None) -> ActionResult`

Set a native value on an element (e.g. AXPopUpButton selection).

`element` is the 1-based SOM index returned by a prior capture call.

#### def `wait(self, seconds: float) -> ActionResult`

Default implementation: time.sleep.


## tools.computer_use.cua_backend

### 模块文档

Cua-driver backend (macOS, Windows, Linux).

Speaks MCP over stdio to `cua-driver`. The Python `mcp` SDK is async, so we
run a dedicated asyncio event loop on a background thread and marshal sync
calls through it.

The same `cua-driver call <tool>` surface (click, type_text, hotkey, drag,
scroll, screenshot, launch_app, list_apps, list_windows, get_window_state,
move_cursor, wait) works identically across macOS, Windows, and Linux —
cua-driver's PARITY matrix marks the action tools VERIFIED on macOS and
Windows in the cross-platform Rust port (`cua-driver-rs`).

Linux is the most recent runtime (X11 today, Wayland via XWayland; pure-
Wayland progress tracked upstream). It is enabled in
`check_computer_use_requirements` alongside macOS and Windows. The plumbing
in this file is OS-agnostic; per-host gaps (no DISPLAY, missing AT-SPI,
etc.) surface as specific blocked checks via `hermes computer-use doctor`
rather than failing silently.

Install:
  - **macOS**:
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.sh)"
  - **Windows** (PowerShell):
      irm https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.ps1 | iex

After install, `cua-driver` is on $PATH and supports `cua-driver mcp` (stdio
transport) which is what we invoke.

The macOS path uses private SkyLight SPIs (SLEventPostToPid,
SLPSPostEventRecordTo, _AXObserverAddNotificationAndCheckRemote) that aren't
Apple-public and can break on OS updates. The Windows path in cua-driver-rs
uses stable Win32 APIs (SendInput + UI Automation) — not subject to the
same SPI breakage class.

### class CuaDriverBackend

> 继承: `ComputerUseBackend` ｜ 方法数: 43（公开 34）

Default computer-use backend. Cross-platform via cua-driver MCP.

#### def `__init__() -> None`

#### def `start(self) -> None`

#### def `stop(self) -> None`

#### def `is_available(self) -> bool`

#### def `capture(self, mode: str = 'som', app: Optional[str] = None, pid: Optional[int] = None, window_id: Optional[int] = None) -> CaptureResult`

Capture the frontmost on-screen window or an exact known target.

Maps hermes `capture(mode, app)` → cua-driver `list_windows` +
`get_window_state` (ax/som) or `screenshot` (vision).

#### def `click(self, element: Optional[int] = None, x: Optional[int] = None, y: Optional[int] = None, button: str = 'left', click_count: int = 1, modifiers: Optional[List[str]] = None, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `drag(self, from_element: Optional[int] = None, to_element: Optional[int] = None, from_xy: Optional[Tuple[int, int]] = None, to_xy: Optional[Tuple[int, int]] = None, button: str = 'left', modifiers: Optional[List[str]] = None, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `scroll(self, direction: str, amount: int = 3, element: Optional[int] = None, x: Optional[int] = None, y: Optional[int] = None, modifiers: Optional[List[str]] = None, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `type_text(self, text: str, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `key(self, keys: str, delivery_mode: Optional[str] = None, bring_to_front: bool = False) -> ActionResult`

#### def `set_value(self, value: str, element: Optional[int] = None) -> ActionResult`

Set a value on an element. Handles AXPopUpButton selects natively.

#### def `list_apps(self) -> List[Dict[str, Any]]`

#### def `list_windows(self) -> List[Dict[str, Any]]`

#### def `focus_app(self, app: str, raise_window: bool = False) -> ActionResult`

Target an app for subsequent actions without stealing system focus.

cua-driver background-automation never needs to bring a window to the
front: capture(app=...) already selects the right window via
list_windows. We implement focus_app as a pure window-selector —
enumerate on-screen windows, find the best match for *app*, and store
its pid/window_id so that subsequent click/type calls hit the right
process.

raise_window=True is intentionally ignored: stealing the user's focus
is exactly what this backend is designed to avoid.

#### def `launch_app(self, bundle_id: Optional[str] = None, name: Optional[str] = None, urls: Optional[List[str]] = None, additional_arguments: Optional[List[str]] = None, creates_new_application_instance: bool = False) -> Dict[str, Any]`

Idempotent launch. Returns ``{pid, bundle_id, name, windows[]}``
so callers can skip an extra ``list_windows`` round-trip before
``get_window_state``.

``creates_new_application_instance=True`` forces a new instance
even if the app is already running — use it when concurrent
runs may touch the same app so each session gets its own
isolated window.

**异常**: `ValueError`

#### def `kill_app(self, pid: int) -> ActionResult`

Terminate by pid. Equivalent to ``kill -9`` on POSIX,
``taskkill /F`` on Windows.

#### def `bring_to_front(self, pid: int, window_id: Optional[int] = None) -> ActionResult`

Activate a window so subsequent foreground-dispatched input
lands on it. cua-driver's docstring notes this is the cheaper
path than per-call SetForegroundWindow flashes.

#### def `move_cursor(self, x: int, y: int) -> ActionResult`

Move the agent-cursor *overlay* to a screen point. This is a
visual hint — it does NOT move the real OS pointer (cua-driver
explicitly avoids stealing pointer focus). The overlay glides
smoothly to the target, so consumers use it before a click to
give a visible "where the agent is going" cue.

#### def `get_cursor_position(self) -> Tuple[int, int]`

Return the *real* OS cursor position in screen points
(origin top-left).

#### def `get_screen_size(self) -> Dict[str, Any]`

Return the logical size of the main display in points plus
its backing scale factor. Shape:
``{width, height, backing_scale_factor}``.

#### def `zoom(self, window_id: int, x: float, y: float, w: float, h: float, factor: float = 1.0, format: str = 'jpeg', quality: int = 85) -> Dict[str, Any]`

Return a JPEG / PNG of a sub-region of a window, optionally
scaled. cua-driver supports zoom-to-rect for callers that need
a higher-resolution view of a specific element.

#### def `set_agent_cursor_enabled(self, enabled: bool, cursor_id: Optional[str] = None) -> ActionResult`

Toggle the agent cursor overlay's visibility for this run.

#### def `set_agent_cursor_motion(self, glide_ms: Optional[float] = None, dwell_ms: Optional[float] = None, idle_hide_ms: Optional[float] = None, cursor_id: Optional[str] = None) -> ActionResult`

Tune the overlay's motion timings — glide duration, post-click
dwell, idle-hide delay. Each None means "leave at current value".

#### def `set_agent_cursor_style(self, gradient_colors: Optional[List[str]] = None, bloom_color: Optional[str] = None, image_path: Optional[str] = None, cursor_id: Optional[str] = None) -> ActionResult`

Customise the cursor body. ``gradient_colors`` are CSS hex
strings tip→tail; ``bloom_color`` is the radial halo; an
``image_path`` (.svg/.png/.ico) replaces the silhouette
entirely. Empty values revert to the palette default.

#### def `get_agent_cursor_state(self, cursor_id: Optional[str] = None) -> Dict[str, Any]`

Return ``{x, y, config: {cursor_color, cursor_icon, ...},
enabled}`` for this run's cursor (or the named ``cursor_id``).

#### def `start_recording(self, output_dir: str, record_video: bool = False) -> Dict[str, Any]`

Enable trajectory recording (per-turn screenshots + action
JSON) to ``output_dir``. ``record_video=True`` ALSO captures
the main display to ``<output_dir>/recording.mp4`` (H.264).
Recording ownership is keyed by this run's session id so
concurrent runs don't fight over the recorder.

#### def `stop_recording(self) -> Dict[str, Any]`

Disable recording and finalise the mp4 (if video was on).
Returns the recorder's final state including ``last_video_path``.

#### def `get_recording_state(self) -> Dict[str, Any]`

Return the current recorder state without changing it.
Shape: ``{recording, enabled, output_dir, next_turn,
last_video_path, last_error, owner, video_active}``.

#### def `replay_trajectory(self, trajectory_dir: str, dry_run: bool = False, speed_factor: float = 1.0) -> Dict[str, Any]`

Replay a prior recording's turn stream by re-invoking each
turn's tool call in lexical order. ``dry_run=True`` logs without
actually firing the tools.

#### def `install_ffmpeg(self) -> Dict[str, Any]`

Bootstrap ffmpeg for ``start_recording(record_video=True)``
on Linux / Windows. macOS records natively via ScreenCaptureKit
and doesn't need ffmpeg.

#### def `get_config(self) -> Dict[str, Any]`

Return the current cua-driver runtime config.

#### def `set_config(self, **config) -> ActionResult`

Set cua-driver config keys. Common keys include
``max_image_dimension`` (image-output resizing), recording
flags, etc. Unknown keys are passed through verbatim — cua-driver
validates against its own schema.

#### def `get_accessibility_tree(self) -> Dict[str, Any]`

Return a lightweight snapshot of running regular apps +
on-screen visible windows with bounds, z-order, owner pid.
Roughly the data ``list_windows`` exposes, in one call. Most
callers should prefer ``capture()`` / ``focus_app()`` which
already use this shape internally.

#### def `page(self, pid: int, action: str, **page_args: Any) -> Dict[str, Any]`

Interact with a browser page loaded in a running app (Chrome,
Safari, Edge, ...). cua-driver routes through CDP / Apple Events
/ AX tree depending on the target. ``action`` + ``page_args``
shape depends on the requested operation (e.g. ``action="eval"``
takes ``js: str``); see cua-driver's ``page`` tool description
for the full grammar.

#### def `call_tool(self, name: str, args: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]`

Call any cua-driver MCP tool by name with arbitrary args.
``session`` is injected (preserves the caller's explicit one
via setdefault). For tools the wrapper doesn't already type-
wrap, this is the supported escape hatch — preferred over
reaching for ``self._session.call_tool`` directly because it
keeps the session-id contract consistent with everything else.


### 顶层函数

#### def `cua_driver_child_env(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]`

Return the environment dict for spawning cua-driver.

Starts from ``base_env`` (defaults to ``os.environ``) and, when telemetry
is disabled (the default), injects ``CUA_DRIVER_RS_TELEMETRY_ENABLED=0``.
When the user has opted in, the var is left untouched so cua-driver uses
its own default. Used by every cua-driver spawn site (MCP backend, status,
doctor, install) so the policy is applied consistently.

#### def `cua_driver_binary_available() -> bool`

True if `cua-driver` is on $PATH or HERMES_CUA_DRIVER_CMD resolves.

#### def `cua_driver_update_check(timeout: float = 8.0) -> Optional[Dict[str, Any]]`

Run ``cua-driver check-update --json`` and return its parsed state.

The payload mirrors the ``check_for_update`` MCP tool:
``{current_version, latest_version, update_available, ...}``.

Returns ``None`` (callers should stay quiet) when the result is
indeterminate: the binary is missing, the driver is too old to support
the verb (it predates trycua/cua#1734), the GitHub check failed (an
``error`` field is set), or the output didn't parse. Best-effort; never
raises.

#### def `cua_driver_update_nudge() -> Optional[str]`

One-line "an update is available" message, or ``None`` when up to date,
indeterminate, or the driver is too old to report.

#### def `cua_driver_install_hint() -> str`


## tools.computer_use.doctor

### 模块文档

`hermes computer-use doctor` — thin client for cua-driver's `health_report` MCP tool.

cua-driver owns the health model (#1908 / be761fac on `main`). This module
just drives the stdio JSON-RPC handshake, calls `health_report`, and
renders the structured response. When the driver gets new checks, they
flow through here without code changes on the Hermes side — the only
contract is the stable `schema_version="1"` payload shape.

Exit code conventions:
- 0: overall == "ok"
- 1: overall in ("degraded", "failed")
- 2: driver binary missing / unreachable / protocol error

### 顶层函数

#### def `run_doctor(driver_cmd: Optional[str] = None, include: Sequence[str] = (), skip: Sequence[str] = (), json_output: bool = False, color: Optional[bool] = None) -> int`

Resolve the cua-driver binary, call `health_report`, render the result.

Honors `HERMES_CUA_DRIVER_CMD` via the same `_cua_driver_cmd()` resolver
that `install_cua_driver` + the runtime backend use, so the doctor
diagnoses what your `computer_use` toolset will actually invoke.


## tools.computer_use.permissions

### 模块文档

Cross-platform Computer Use readiness + macOS permission helpers.

cua-driver runs on macOS, Windows, and Linux, but "ready to drive" means
something different on each:

  * macOS — explicit TCC grants (Accessibility + Screen Recording). cua-driver
    reports/requests them via ``permissions status`` / ``permissions grant``.
    The grants attach to cua-driver's OWN identity (``com.trycua.driver`` /
    the installed ``CuaDriver.app``), NOT Hermes — so no Hermes entitlement is
    involved, and ``grant`` launches CuaDriver via LaunchServices so the macOS
    dialog is attributed correctly.
  * Windows — no TCC toggles; the UIAccess worker (``cua-driver-uia.exe``) may
    trip a SmartScreen prompt on first run. Readiness == driver health.
  * Linux — assistive control via the X11/XWayland stack. Readiness == driver
    health.

The universal signal on every platform is ``cua-driver doctor --json`` (binary
integrity + platform support). ``computer_use_status`` folds that together with
the macOS permission detail into one payload for the desktop card, the
``hermes computer-use permissions`` CLI, and ``/api/tools/computer-use/status``.

### 顶层函数

#### def `computer_use_status(driver_cmd: Optional[str] = None) -> Dict[str, Any]`

Unified, OS-aware Computer Use readiness for the desktop card.

``ready`` is the single signal the UI keys off: on macOS it's both TCC
grants; elsewhere it's driver health (no TCC model). ``None`` means
unknown (binary missing / probe failed). ``can_grant`` is macOS-only.

#### def `request_permissions_grant(driver_cmd: Optional[str] = None) -> int`

Run ``cua-driver permissions grant`` (macOS); stream its output.

Launches CuaDriver via LaunchServices so the TCC dialog is attributed to
``com.trycua.driver``, then waits for the grant. Returns the driver's exit
code (0 ok), 2 if the binary is missing, 64 on a non-macOS platform (which
has no TCC permission model to grant).


## tools.computer_use.schema

### 模块文档

Schema for the generic `computer_use` tool.

Model-agnostic. Any tool-calling model can drive this. Vision-capable models
should prefer `capture(mode='som')` then `click(element=N)` — much more
reliable than pixel coordinates. Pixel coordinates remain supported for
models that were trained on them (e.g. Claude's computer-use RL).

### 顶层函数

#### def `get_computer_use_schema() -> Dict[str, Any]`

Return the generic OpenAI function-calling schema.


## tools.computer_use.tool

### 模块文档

Entry point for the `computer_use` tool.

Universal (any-model) desktop control across macOS, Windows, and Linux via
cua-driver's background computer-use primitive. Replaces #4562's
Anthropic-native `computer_20251124` approach — the schema here is standard
OpenAI function-calling so every tool-capable model can drive it.

Linux is the most recent runtime (X11 + Wayland, via cua-driver-rs's
AT-SPI tree path); it is enabled here alongside macOS and Windows. When a
host's display server or accessibility stack isn't reachable, cua-driver's
`health_report` (surfaced by `hermes computer-use doctor`) reports the
exact blocked check rather than the toolset silently failing.

Return contract
---------------
For text-only results (wait, key, list_apps, focus_app, failures, etc.):
  JSON string.

For captures / actions with `capture_after=True`:
  A dict wrapped as the OpenAI-style multi-part tool-message content:

      {
        "_multimodal": True,
        "content": [
            {"type": "text", "text": "<human-readable summary + SOM index>"},
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64,<b64>"}},
        ],
        "text_summary": "<text used for fallback string content>",
      }

  run_agent.py's tool-message builder inspects `_multimodal` and emits a
  list-shaped `content` for OpenAI-compatible providers. The Anthropic
  adapter splices the base64 image into a `tool_result` block (see
  `agent/anthropic_adapter.py`). Every provider that supports multi-part
  tool content gets the image; text-only providers see the summary only.

### 顶层函数

#### def `set_approval_callback(cb) -> None`

Register a callback for computer_use approval prompts (used by CLI).

Matches the terminal_tool._approval_callback pattern. The callback
receives (action, args, summary) and returns one of:
  "approve_once" | "approve_session" | "always_approve" | "deny".

#### def `reset_backend_for_tests() -> None`

Test helper — tear down the cached backend and per-session state.

#### def `handle_computer_use(args: Dict[str, Any], **kwargs) -> Any`

Main entry point — dispatched by tools.registry.

Returns either a JSON string (text-only) or a dict marked `_multimodal`
(image + summary) which run_agent.py wraps into the tool message.

#### def `check_computer_use_requirements() -> bool`

Return True iff computer_use can run on this host.

Conditions: macOS, Windows, or Linux + cua-driver binary installed (or
override via env). cua-driver runs on all three; the Linux path is
headed/X11 today (Wayland via XWayland), pure-Wayland progress tracked
upstream. Linux users see specific blocked checks via
`hermes computer-use doctor` if their session is incomplete (e.g. no
DISPLAY set).

#### def `get_computer_use_schema() -> Dict[str, Any]`


## tools.computer_use.vision_routing

### 模块文档

Vision-routing decisions for ``computer_use`` capture results.

Background
----------
``computer_use(action='capture', mode='som'|'vision')`` returns a
``_multimodal`` envelope containing the captured screenshot. That envelope
is delivered back to the **active session model** as the tool result. When
the active main model has no vision capability (e.g. text-only or
text+code-only models), or when the active provider rejects multimodal
content inside tool-result messages, the screenshot trips a 404 / 400 at
the provider boundary and the agent loop reports a hard tool failure.

Issue #24015 reports this regression for the ``cua-driver`` backend:
configuring ``auxiliary.vision`` (a dedicated vision-capable model) in
``config.yaml`` was silently ignored — the screenshot was still routed at
the *main* model and failed with HTTP 404 ``No endpoints found that
support image input`` even though a perfectly good vision backend was
sitting in config waiting to be used.

This module centralises the small policy decision: should a captured
screenshot be returned as multimodal content (main model handles vision
natively) or pre-analysed via the auxiliary vision pipeline so the main
model only ever sees text?

Behaviour (mirrors ``vision_analyze`` for consistency)
------------------------------------------------------
* If the user explicitly configured ``auxiliary.vision`` (any of
  ``provider``, ``model``, or ``base_url`` non-empty / not ``"auto"``),
  the screenshot is routed through the aux vision pipeline. Users who
  pay for a dedicated vision model usually want it used.
* Otherwise, if the user explicitly declared the active model vision-capable
  via ``model.supports_vision`` / provider model config, return ``False``.
  This is the escape hatch for custom/local OpenAI-compatible VLM routes that
  are absent from models.dev and provider allowlists.
* Otherwise, if the active main model+provider can carry an image inside
  a tool-result message AND the model reports ``supports_vision=True``
  in models.dev metadata, return ``False`` (use the multimodal path).
* In every other case (non-vision main model, provider that does not
  accept multimodal tool results, lookup failure), route through aux
  vision so the main model receives a text description it can act on.

The decision intentionally fails *closed* (i.e. towards aux routing) when
metadata is missing or ambiguous: returning a screenshot to a model that
cannot read it is a hard tool failure, while routing it through aux costs
one extra LLM call and yields a usable description.

### 顶层函数

#### def `should_route_capture_to_aux_vision(provider: str, model: str, cfg: Optional[Dict[str, Any]]) -> bool`

Return True iff the captured screenshot should be pre-analysed via aux vision.

Args:
  provider: active inference provider id (e.g. ``"openrouter"``,
    ``"anthropic"``, ``"openai-codex"``). Lower-case canonical id.
  model:    active main model slug as it would be sent to the provider.
  cfg:      loaded ``config.yaml`` dict (or None).

Returns:
  ``True`` when the caller should hand the screenshot to the aux vision
  pipeline (and surface a text-only tool result). ``False`` when the
  caller should keep the existing multimodal envelope (main model
  handles vision natively).


## tools.computer_use_tool

### 模块文档

Shim for tool discovery. Registers `computer_use` with tools.registry.

The real implementation lives in the `tools/computer_use/` package to keep
the file structure clean. This shim exists because tools.registry auto-imports
`tools/*.py` — we need a top-level module to trigger the registration.

## tools.credential_files

### 模块文档

File passthrough registry for remote terminal backends.

Remote backends (Docker, Modal, SSH) create sandboxes with no host files.
This module ensures that credential files, skill directories, and host-side
cache directories (documents, images, audio, screenshots) are mounted or
synced into those sandboxes so the agent can access them.

**Credentials and skills** — session-scoped registry fed by skill declarations
(``required_credential_files``) and user config (``terminal.credential_files``).

**Cache directories** — gateway-cached uploads, browser screenshots, TTS
audio, and processed images.  Mounted read-only so the remote terminal can
reference files the host side created (e.g. ``unzip`` an uploaded archive).

Remote backends call :func:`get_credential_file_mounts`,
:func:`get_skills_directory_mount` / :func:`iter_skills_files`, and
:func:`get_cache_directory_mounts` / :func:`iter_cache_files` at sandbox
creation time and before each command (for resync on Modal).

### 顶层函数

#### def `register_credential_file(relative_path: str, container_base: str = '/root/.hermes') -> bool`

Register a credential file for mounting into remote sandboxes.

*relative_path* is relative to ``HERMES_HOME`` (e.g. ``google_token.json``).
Returns True if the file exists on the host and was registered.

Security: rejects absolute paths and path traversal sequences (``..``).
The resolved host path must remain inside HERMES_HOME so that a malicious
skill cannot declare ``required_credential_files: ['../../.ssh/id_rsa']``
and exfiltrate sensitive host files into a container sandbox.

Containment alone is not sufficient, because HERMES_HOME is exactly where
the MASTER credential stores live. A skill legitimately needs its own
service token (``google_token.json``); it never needs ``.env`` (every
provider key), ``auth.json`` (all provider tokens and OAuth grants),
``mcp-tokens/`` or the Bitwarden plaintext cache. Those are refused via
the canonical read deny-list (``agent.file_safety.get_read_block_error``)
— the same guard that stops the agent reading them with ``read_file``, so
the mount surface cannot hand a skill what the read surface denies it.

#### def `register_credential_files(entries: list, container_base: str = '/root/.hermes') -> List[str]`

Register multiple credential files from skill frontmatter entries.

Each entry is either a string (relative path) or a dict with a ``path``
key.  Returns the list of relative paths that were NOT found on the host
(i.e. missing files).

#### def `get_credential_file_mounts() -> List[Dict[str, str]]`

Return all credential files that should be mounted into remote sandboxes.

Each item has ``host_path`` and ``container_path`` keys.
Combines skill-registered files and user config.

#### def `get_skills_directory_mount(container_base: str = '/root/.hermes') -> list[Dict[str, str]]`

Return mount info for all skill directories (local + external).

Skills may include ``scripts/``, ``templates/``, and ``references/``
subdirectories that the agent needs to execute inside remote sandboxes.

**Security:** Bind mounts follow symlinks, so a malicious symlink inside
the skills tree could expose arbitrary host files to the container.  When
symlinks are detected, this function creates a sanitized copy (regular
files only) in a temp directory and returns that path instead.  When no
symlinks are present (the common case), the original directory is returned
directly with zero overhead.

Returns a list of dicts with ``host_path`` and ``container_path`` keys.
The local skills dir mounts at ``<container_base>/skills``, external dirs
at ``<container_base>/external_skills/<index>``.

#### def `iter_skills_files(container_base: str = '/root/.hermes') -> List[Dict[str, str]]`

Yield individual (host_path, container_path) entries for skills files.

Includes both the local skills dir and any external dirs configured via
skills.external_dirs.  Skips symlinks entirely.  Preferred for backends
that upload files individually (Daytona, Modal) rather than mounting a
directory.

#### def `get_cache_directory_mounts(container_base: str = '/root/.hermes') -> List[Dict[str, str]]`

Return mount entries for each cache directory that exists on disk.

Used by Docker to create bind mounts.  Each entry has ``host_path`` and
``container_path`` keys.  The host path is resolved via
``get_hermes_dir()`` for backward compatibility with old directory layouts.

#### def `map_cache_path_to_container(host_path: str, container_base: str = '/root/.hermes') -> Optional[str]`

Map a host cache path to its mounted path under *container_base*.

Returns the POSIX container path when *host_path* lives under one of the
auto-mounted cache directories, otherwise ``None``.  Backend-agnostic: the
caller decides which ``container_base`` applies (Docker ``/root/.hermes``,
SSH ``<remote_home>/.hermes``, etc.) and whether translation is wanted.
Always joins with ``posixpath`` because container/remote paths are POSIX
regardless of the host OS.

#### def `from_agent_visible_cache_path(container_path: str, container_base: str = '/root/.hermes') -> str`

Translate a sandbox/container cache path back to its host path.

Inverse of :func:`to_agent_visible_cache_path`. Returns the input unchanged
when the active backend is not Docker, or when the path is not under any
auto-mounted cache directory — the caller then treats a still-container
path as "no host file" and falls back to an in-container read.

#### def `to_agent_visible_cache_path(host_path: str, container_base: str = '/root/.hermes') -> str`

Translate a host cache path to its mounted path inside the sandbox.

Returns the input unchanged if it is not under any auto-mounted cache
directory, or if the active terminal backend does not require path
translation (only Docker for now).

#### def `iter_cache_files(container_base: str = '/root/.hermes') -> List[Dict[str, str]]`

Return individual (host_path, container_path) entries for cache files.

Used by Modal to upload files individually and resync before each command.
Skips symlinks.  The container paths use the new ``cache/<subdir>`` layout.

#### def `clear_credential_files() -> None`

Reset the skill-scoped registry (e.g. on session reset).


## tools.cronjob_tools

### 模块文档

Cron job management tools for Hermes Agent.

Expose a single compressed action-oriented tool to avoid schema/context bloat.
Compatibility wrappers remain for direct Python callers and legacy tests.

### 顶层函数

#### def `cronjob(action: str, job_id: Optional[str] = None, prompt: Optional[str] = None, schedule: Optional[str] = None, name: Optional[str] = None, repeat: Optional[int] = None, deliver: Optional[str] = None, include_disabled: bool = False, skill: Optional[str] = None, skills: Optional[List[str]] = None, model: Optional[str] = None, provider: Optional[str] = None, base_url: Optional[str] = None, reason: Optional[str] = None, script: Optional[str] = None, context_from: Optional[Union[str, List[str]]] = None, enabled_toolsets: Optional[List[str]] = None, workdir: Optional[str] = None, no_agent: Optional[bool] = None, attach_to_session: Optional[bool] = None, task_id: str = None) -> str`

Unified cron job management tool.

#### def `check_cronjob_requirements() -> bool`

Check if cronjob tools can be used.

Available in interactive CLI mode and gateway/messaging platforms.
The cron system is internal (JSON file-based scheduler ticked by the gateway),
so no external crontab executable is required.

Session env vars must hold an explicit truthy string (``1``, ``true``,
``yes``, ``on``) — false-like values (``0``, ``false``, ``no``, ``off``)
leave the tool disabled. Uses the shared ``env_var_enabled`` helper so
every consumer of these flags agrees on the truthy set.


## tools.daemon_pool

### 模块文档

Shared daemon-thread ThreadPoolExecutor.

Stdlib ``ThreadPoolExecutor`` workers are non-daemon AND are registered in
``concurrent.futures.thread._threads_queues``, whose atexit hook
(``_python_exit``) joins every worker unconditionally — even after
``shutdown(wait=False)``.  A single wedged worker (tool blocked on network
I/O, hung provider daemon, stuck subagent) therefore blocks interpreter
exit forever.  This is the root cause of multi-minute CLI exits on long
sessions: every abandoned concurrent-tool batch leaves workers that the
exit hook insists on joining.

``DaemonThreadPoolExecutor`` spawns daemon workers and skips the
``_threads_queues`` registration, so:

  - ``_python_exit`` never joins them, and
  - the interpreter's non-daemon thread join at shutdown skips them.

Semantics are otherwise identical (initializer/initargs, work queue,
idle-thread reuse).  Use it for any pool whose work is best-effort or
independently interruptible and must never hold the process open:
concurrent tool execution, background memory sync, catalog fan-out,
subagent timeout wrappers.  Do NOT use it for work that must complete
before exit (durable writes) — those belong on foreground threads with
explicit bounded joins.

### class DaemonThreadPoolExecutor

> 继承: `ThreadPoolExecutor` ｜ 方法数: 1（公开 0）

ThreadPoolExecutor variant whose workers do not block process exit.


## tools.debug_helpers

### 模块文档

Shared debug session infrastructure for Hermes tools.

Replaces the identical DEBUG_MODE / _log_debug_call / _save_debug_log /
get_debug_session_info boilerplate previously duplicated across web_tools,
vision_tools, and image_generation_tool.

Usage in a tool module:

    from tools.debug_helpers import DebugSession

    _debug = DebugSession("web_tools", env_var="WEB_TOOLS_DEBUG")

    # Log a call (no-op when debug mode is off)
    _debug.log_call("web_search", {"query": q, "results": len(r)})

    # Save the debug log (no-op when debug mode is off)
    _debug.save()

    # Expose debug info to external callers
    def get_debug_session_info():
        return _debug.get_session_info()

### class DebugSession

> 继承: `object` ｜ 方法数: 5（公开 4）

Per-tool debug session that records tool calls to a JSON log file.

Activated by a tool-specific environment variable (e.g. WEB_TOOLS_DEBUG=true).
When disabled, all methods are cheap no-ops.

#### def `__init__(tool_name: str, env_var: str) -> None`

#### property `active(self) -> bool`

#### def `log_call(self, call_name: str, call_data: Dict[str, Any]) -> None`

Append a tool-call entry to the in-memory log.

#### def `save(self) -> None`

Flush the in-memory log to a JSON file in the logs directory.

#### def `get_session_info(self) -> Dict[str, Any]`

Return a summary dict suitable for returning from get_debug_session_info().


## tools.delegate_tool

### 模块文档

Delegate Tool -- Subagent Architecture

Spawns child AIAgent instances with isolated context, inherited toolsets,
and their own terminal sessions. Supports single-task and batch (parallel)
modes. Top-level model calls run in the background; orchestrator children
wait for their own workers so they can synthesize the results.

Each child gets:
  - A fresh conversation (no parent history)
  - Its own task_id (own terminal session, file ops cache)
  - The parent's toolsets, with child-only blocked tools stripped
  - A focused system prompt built from the delegated goal + context

The parent's context only sees the delegation call and the summary result,
never the child's intermediate tool calls or reasoning.

### class DelegateEvent

> 继承: `str`、`enum.Enum` ｜ 方法数: 0（公开 0）

Formal event types emitted during delegation progress.

_build_child_progress_callback normalises incoming legacy strings
(``tool.started``, ``_thinking``, …) to these enum values via
``_LEGACY_EVENT_MAP``.  External consumers (gateway SSE, ACP adapter,
CLI) still receive the legacy strings during the deprecation window.

TASK_SPAWNED / TASK_COMPLETED / TASK_FAILED are reserved for
future orchestrator lifecycle events and are not currently emitted.


### 顶层函数

#### def `set_spawn_paused(paused: bool) -> bool`

Globally block/unblock new delegate_task spawns.

Active children keep running; only NEW calls to delegate_task fail fast
with a "spawning paused" error until unblocked.  Returns the new state.

#### def `is_spawn_paused() -> bool`

#### def `interrupt_subagent(subagent_id: str) -> bool`

Request that a single running subagent stop at its next iteration boundary.

Does not hard-kill the worker thread (Python can't); sets the child's
interrupt flag which propagates to in-flight tools and recurses into
grandchildren via AIAgent.interrupt().  Returns True if a matching
subagent was found.

#### def `list_active_subagents() -> List[Dict[str, Any]]`

Snapshot of the currently running subagent tree.

Each record: {subagent_id, parent_id, depth, goal, model, started_at,
tool_count, status}.  Safe to call from any thread — returns a copy.

#### def `check_delegate_requirements() -> bool`

Delegation has no external requirements -- always available.

#### def `delegate_task(goal: Optional[str] = None, context: Optional[str] = None, tasks: Optional[List[Dict[str, Any]]] = None, max_iterations: Optional[int] = None, role: Optional[str] = None, background: Optional[bool] = None, parent_agent = None) -> str`

Spawn one or more child agents to handle delegated tasks.

Supports two modes:
  - Single: provide goal (+ optional context and role)
  - Batch:  provide tasks array [{goal, context, role}, ...]

The 'role' parameter controls whether a child can further delegate:
'leaf' (default) cannot; 'orchestrator' retains the delegation
toolset and can spawn its own workers, bounded by
delegation.max_spawn_depth.  Per-task role beats the top-level one.

Returns JSON with results array, one entry per task.


## tools.delegation_live_log

### 模块文档

Live, tail-able transcripts for delegated subagents.

Every ``delegate_task`` dispatch creates one append-only, human-readable log
per child under::

    <hermes_home>/cache/delegation/live/<delegation_id>/task-<n>.log

The files are pre-created with a header at dispatch time (so ``tail -f``
attaches immediately) and then stream one line per child event: assistant
text, thinking, tool calls, tool results, and lifecycle markers. The paths
are returned from ``delegate_task`` so the parent agent (or the user) can
watch a child work instead of waiting blind for the consolidated summary.

Placement under ``cache/delegation`` is deliberate: that directory is
mounted read-only into remote terminal backends (Docker/Modal/SSH) via
``credential_files._CACHE_DIRS``, so the logs are readable from any backend.

Design constraints:

* **Never raise into the agent loop.** Every write is wrapped; the first
  failure disables the writer and degrades to a debug log.
* **Survive child crashes.** Files are opened in append mode per write —
  no long-lived handle to lose, every event is flushed when written.
* **Side-channel only.** Nothing here touches message content, so prompt
  caching is unaffected.
* **No config knobs.** Retention is a module constant (7 days), pruned
  opportunistically on each new dispatch.

### class LiveTranscriptWriter

> 继承: `object` ｜ 方法数: 11（公开 10）

Append-only human-readable event log for ONE subagent task.

All methods are best-effort: the first write failure flips ``_ok`` off
and subsequent calls become no-ops (debug-logged). Never raises.

#### def `__init__(delegation_id: str, task_index: int, goal: str, context: Optional[str] = None, root: Optional[Path] = None)`

#### def `event(self, role: str, text: str) -> None`

Append one ``HH:MM:SS role ⟩ text`` line. Flushed per event.

#### def `assistant_text(self, text: str) -> None`

#### def `thinking(self, text: str) -> None`

#### def `tool_start(self, name: str, args_preview: Any = None) -> None`

#### def `tool_result(self, name: str, result: Any = None, duration: Any = None, is_error: bool = False) -> None`

#### def `marker(self, text: str) -> None`

Lifecycle marker: start / final / error / interrupt / budget.

#### def `add_stream_delta(self, delta: str) -> None`

Buffer streamed assistant reply text; flushed as one line.

#### def `flush_stream(self) -> None`

#### def `observe(self, event_type: Any, tool_name: Any = None, preview: Any = None, args: Any = None, **kwargs: Any) -> None`

Map a child tool_progress_callback event onto transcript lines.

Mirrors the shapes emitted by agent/tool_executor.py,
agent/conversation_loop.py, and tools/delegate_tool._run_single_child.
Unknown events are ignored. Never raises (event() swallows I/O).

#### def `finalize(self, entry: Dict[str, Any]) -> None`

Terminal marker from the aggregated result entry.

Adds exit-reason detail the subagent.complete event doesn't carry
(budget exhaustion via exit_reason=max_iterations, errors, etc.).


### 顶层函数

#### def `live_transcript_root() -> Path`

Root directory for live transcripts (profile-safe, never ~/.hermes).

#### def `new_live_delegation_id() -> str`

Same shape as async_delegation's ids so the dir name matches the handle.

#### def `wrap_progress_callback(inner_cb, writer: LiveTranscriptWriter)`

Wrap a child's tool_progress_callback so events also land in the log.

``inner_cb`` may be None (no parent display) — the wrapper still records.
Writer failures never propagate; inner callback behavior is unchanged
(its own exceptions are handled by callers exactly as before).
Preserves the ``_flush`` attribute contract used by _run_single_child.

#### def `create_live_transcripts(task_list: List[Dict[str, Any]], context: Optional[str] = None, delegation_id: Optional[str] = None) -> tuple[Optional[str], List[Optional[LiveTranscriptWriter]], List[str]]`

Create one pre-headered writer per task + a manifest.json.

Returns ``(delegation_id, writers, paths)``. On any top-level failure
returns ``(None, [None]*n, [])`` so delegation proceeds untouched.
Also opportunistically prunes stale live dirs (retention).

#### def `update_manifest_statuses(delegation_id: Optional[str], results: List[Dict[str, Any]]) -> None`

Best-effort per-task status update once the batch has aggregated.

#### def `prune_stale_live_dirs(max_age_days: int = LIVE_RETENTION_DAYS) -> int`

Remove live/<delegation_id> dirs older than the retention window.

Returns how many were removed. Fully best-effort.


## tools.discord_tool

### 模块文档

Discord server introspection and management tool.

Provides the agent with the ability to interact with Discord servers
when running on the Discord gateway. Uses Discord REST API directly
with the bot token — no dependency on the gateway adapter's client.

Only included in the hermes-discord toolset, so it has zero cost
for users on other platforms.

The schema exposed to the model is filtered by two gates:

1. Privileged intents detected from GET /applications/@me at schema
   build time. Actions that require an intent the bot doesn't have
   (search_members / member_info → GUILD_MEMBERS intent) are hidden.
   fetch_messages is kept regardless of MESSAGE_CONTENT intent, but
   its description is annotated when the intent is missing.

2. User config allowlist at ``discord.server_actions``. If the user
   sets a comma-separated list (or YAML list) of action names, only
   those appear in the schema. Empty/unset means all intent-available
   actions are exposed.

Per-guild permissions (MANAGE_ROLES etc.) are NOT pre-checked — Discord
returns a 403 at call time and :func:`_enrich_403` maps it to
actionable guidance the model can relay to the user.

### class DiscordAPIError

> 继承: `Exception` ｜ 方法数: 1（公开 0）

Raised when a Discord API call fails.

#### def `__init__(status: int, body: str)`


### 顶层函数

#### def `get_dynamic_schema_core() -> Optional[Dict[str, Any]]`

#### def `get_dynamic_schema_admin() -> Optional[Dict[str, Any]]`

#### def `get_dynamic_schema() -> Optional[Dict[str, Any]]`

Backward-compat wrapper — returns core schema.

#### def `check_discord_tool_requirements() -> bool`

Tool is available only when a Discord bot token is configured.

#### def `discord_core(action: str, **kwargs) -> str`

Execute a core Discord action (fetch_messages, search_members, create_thread).

#### def `discord_admin_handler(action: str, **kwargs) -> str`

Execute a Discord admin action (server management).


## tools.env_passthrough

### 模块文档

Environment variable passthrough registry.

Skills that declare ``required_environment_variables`` in their frontmatter
need those vars available in sandboxed execution environments (execute_code,
terminal).  By default both sandboxes strip secrets from the child process
environment for security.  This module provides a session-scoped allowlist
so skill-declared vars (and user-configured overrides) pass through.

Two sources feed the allowlist:

1. **Skill declarations** — when a skill is loaded via ``skill_view``, its
   ``required_environment_variables`` are registered here automatically.
2. **User config** — ``terminal.env_passthrough`` in config.yaml lets users
   explicitly allowlist vars for non-skill use cases.

Both ``code_execution_tool.py`` and ``tools/environments/local.py`` consult
:func:`is_env_passthrough` before stripping a variable.

### 顶层函数

#### def `register_env_passthrough(var_names: Iterable[str]) -> None`

Register environment variable names as allowed in sandboxed environments.

Typically called when a skill declares ``required_environment_variables``.

Variables that are Hermes-managed provider credentials (from
``_HERMES_PROVIDER_ENV_BLOCKLIST``) are rejected here to preserve
the ``execute_code`` sandbox's credential-scrubbing guarantee per
GHSA-rhgp-j443-p4rf. A skill that needs to talk to a Hermes-managed
provider should do so via the agent's main-process tools (web_search,
web_extract, etc.) where the credential remains safely in the main
process.

Non-Hermes third-party API keys (TENOR_API_KEY, NOTION_TOKEN, etc.)
pass through normally — they were never in the sandbox scrub list.

#### def `is_env_passthrough(var_name: str) -> bool`

Check whether *var_name* is allowed to pass through to sandboxes.

Returns ``True`` if the variable was registered by a skill or listed in
the user's ``tools.env_passthrough`` config.

#### def `get_all_passthrough() -> frozenset[str]`

Return the union of skill-registered and config-based passthrough vars.

#### def `clear_env_passthrough() -> None`

Reset the skill-scoped allowlist (e.g. on session reset).


## tools.env_probe

### 模块文档

Local-environment toolchain probe for the system prompt.

When the terminal backend is local (the agent's tools run on the same
machine as Hermes itself), we surface a single deterministic line about
Python tooling state so models don't have to discover it by hitting
walls.  Common failure modes this addresses:

* Hermes ships under one Python (e.g. 3.11 in a bundled venv) while the
  user's login shell has a different one (e.g. 3.12 system).  ``pip``
  resolved from PATH may not match ``python3 -m pip``.
* The bundled-venv Python has no pip module installed → ``python3 -m
  pip`` returns ``No module named pip``.
* The system Python is PEP-668 externally-managed → naive
  ``pip install`` fails with ``error: externally-managed-environment``.

The probe is cheap (a handful of subprocess calls, ~50ms total),
cached for the lifetime of the process, and emits **at most one
short line** when something non-default is detected.  When the
environment looks normal (python3+pip both present and matched, no
PEP 668), it emits nothing — no token cost.

Remote terminal backends (docker, modal, ssh, …) are skipped: the
host's Python state is irrelevant when tools run inside a sandbox.
The sandbox has its own existing probe (``_probe_remote_backend``)
in ``agent/prompt_builder.py``.

Toggle via ``agent.environment_probe`` in config.yaml (default True).

### 顶层函数

#### def `get_environment_probe_line(force_refresh: bool = False) -> str`

Return the cached probe line (building it on first call).

Returns "" when the environment is clean — the system prompt
assembler should drop the section in that case rather than
emit an empty heading.

The probe itself always runs in a single background worker thread;
this function waits on its completion event for at most
``_PROBE_WAIT_TIMEOUT`` seconds and then fails open with "".  A
wedged probe subprocess (#67964) therefore can never block
system-prompt construction — at worst the toolchain line is absent
from prompts built while the probe is stuck.

``force_refresh`` is for tests; real callers should never need it.

#### def `warm_environment_probe_async() -> None`

Kick off the probe in a background thread so the first
system-prompt build doesn't pay the ~0.5s of subprocess calls
(python3/pip/PEP-668 version checks) on the time-to-first-token
critical path.

Idempotent and fail-safe.  The prompt-build call to
``get_environment_probe_line`` waits (bounded) on the same worker's
completion event instead of recomputing.  Called from agent init
(all platforms); safe to call from anywhere.


## tools.environments.__init__

### 模块文档

Hermes execution environment backends.

Each backend provides the same interface (BaseEnvironment ABC) for running
shell commands in a specific execution context: local, Docker, SSH,
Singularity, Modal, or Daytona. (Modal additionally has direct and
Nous-managed modes, selected via terminal.modal_mode.)

The terminal_tool.py factory (_create_environment) selects the backend
based on the TERMINAL_ENV configuration.

## tools.environments.base

### 模块文档

Base class for all Hermes execution environment backends.

Unified spawn-per-call model: every command spawns a fresh ``bash -c`` process.
A session snapshot (env vars, functions, aliases) is captured once at init and
re-sourced before each command. CWD persists via in-band stdout markers (remote)
or a temp file (local).

### class ProcessHandle

> 继承: `Protocol` ｜ 方法数: 5（公开 5）

Duck type that every backend's _run_bash() must return.

subprocess.Popen satisfies this natively.  SDK backends (Modal, Daytona)
return _ThreadedProcessHandle which adapts their blocking calls.

#### def `poll(self) -> int | None`

#### def `kill(self) -> None`

#### def `wait(self, timeout: float | None = None) -> int`

#### property `stdout(self) -> IO[str] | None`

#### property `returncode(self) -> int | None`


### class BaseEnvironment

> 继承: `ABC` ｜ 方法数: 18（公开 5）

Common interface and unified execution flow for all Hermes backends.

Subclasses implement ``_run_bash()`` and ``cleanup()``.  The base class
provides ``execute()`` with session snapshot sourcing, CWD tracking,
interrupt handling, and timeout enforcement.

#### def `get_temp_dir(self) -> str`

Return the backend temp directory used for session artifacts.

Most sandboxed backends use ``/tmp`` inside the target environment.
LocalEnvironment overrides this on platforms like Termux where ``/tmp``
may be missing and ``TMPDIR`` is the portable writable location.

#### def `__init__(cwd: str, timeout: int, env: dict = None)`

#### def `cleanup(self)`

Release backend resources (container, instance, connection).

#### def `init_session(self)`

Capture login shell environment into a snapshot file.

Called once after backend construction.  On success, sets
``_snapshot_ready = True`` so subsequent commands source the snapshot
instead of running with ``bash -l``.

**异常**: `RuntimeError`

#### def `execute(self, command: str, cwd: str = '', timeout: int | None = None, stdin_data: str | None = None, rewrite_compound_background: bool = True, bounded_capture: bool = False) -> dict`

Execute a command, return {"output": str, "returncode": int}.

``bounded_capture=True`` caps stdout/stderr retention at
``tool_output.max_bytes`` WHILE the stream is drained (head/tail
window) instead of holding the full output in memory (#64435).
It must only be set by callers whose output is destined for the
model/tool payload (the foreground terminal tool). Internal
full-fidelity consumers — file operations ``cat`` reads that feed
the patch engine, code-execution RPC reads, log reads — MUST leave
it False: truncating those corrupts data, not just display.

#### def `stop(self)`

Alias for cleanup (compat with older callers).


### 顶层函数

#### def `set_activity_callback(cb: Callable[[str], None] | None) -> None`

Register a callback that _wait_for_process fires periodically.

#### def `touch_activity_if_due(state: dict, label: str) -> None`

Fire the activity callback at most once every ``state['interval']`` seconds.

*state* must contain ``last_touch`` (monotonic timestamp) and ``start``
(monotonic timestamp of the operation start).  An optional ``interval``
key overrides the default 10 s cadence.

Swallows all exceptions so callers don't need their own try/except.

#### def `get_sandbox_dir() -> Path`

Return the host-side root for all sandbox storage (Docker workspaces,
Singularity overlays/SIF cache, etc.).

Configurable via TERMINAL_SANDBOX_DIR. Defaults to {HERMES_HOME}/sandboxes/.


## tools.environments.daytona

### 模块文档

Daytona cloud execution environment.

Uses the Daytona Python SDK to run commands in cloud sandboxes.
Supports persistent sandboxes: when enabled, sandboxes are stopped on cleanup
and resumed on next creation, preserving the filesystem across sessions.

### class DaytonaEnvironment

> 继承: `BaseEnvironment` ｜ 方法数: 9（公开 1）

Daytona cloud sandbox execution backend.

Spawn-per-call via _ThreadedProcessHandle wrapping blocking SDK calls.
cancel_fn wired to sandbox.stop() for interrupt support.
Shell timeout wrapper preserved (SDK timeout unreliable).

#### def `__init__(image: str, cwd: str = '/home/daytona', timeout: int = 60, cpu: int = 1, memory: int = 5120, disk: int = 10240, persistent_filesystem: bool = True, task_id: str = 'default')`

**异常**: `ImportError`

#### def `cleanup(self)`


## tools.environments.docker

### 模块文档

Docker execution environment for sandboxed command execution.

Security hardened (cap-drop ALL, no-new-privileges, PID limits),
configurable resource limits (CPU, memory, disk), and optional filesystem
persistence via bind mounts.

### class DockerEnvironment

> 继承: `BaseEnvironment` ｜ 方法数: 11（公开 3）

Hardened Docker container execution with resource limits and persistence.

Security: all capabilities dropped, no privilege escalation, PID limits,
size-limited tmpfs for scratch dirs. The container itself is the security
boundary — the filesystem inside is writable so agents can install packages
(pip, npm, apt) as needed. Writable workspace via tmpfs or bind mounts.

Persistence: when enabled, bind mounts preserve /workspace and /root
across container restarts.

#### def `__init__(image: str, cwd: str = '/root', timeout: int = 60, cpu: float = 0, memory: int = 0, disk: int = 0, persistent_filesystem: bool = False, task_id: str = 'default', volumes: list = None, forward_env: list[str] | None = None, env: dict | None = None, network: bool = True, host_cwd: str = None, auto_mount_cwd: bool = False, run_as_host_user: bool = False, extra_args: list = None, persist_across_processes: bool = True)`

#### def `execute(self, command: str, cwd: str = '', **kwargs) -> dict`

Execute a command, auto-recovering from dead containers.

If the container was removed out-of-band (idle reaper, docker prune,
OOM kill, daemon restart), detect the error and recreate the container
transparently before retrying once.

#### def `cleanup(self, force_remove: bool = False)`

Tear down the container according to persist mode and *force_remove*.

Persist-mode (``persist_across_processes=True``, the default) leaves the
container **running** untouched. The docs promise "ONE long-lived
container shared across sessions" and stopping it on every Hermes exit
breaks that promise:

* Background processes inside the container (``npm run dev``, watchers,
  long-running pytest) get killed every time the user runs ``/quit``.
* Every reuse requires ``docker start`` + waiting for the container to
  come back up, adding 1–2s to the first tool call of the new session.
* The user-visible difference between "ONE long-lived container" and
  "a new container that happens to share state" is exactly this:
  processes survive in the former, die in the latter.

Resource reclamation for the persist-mode case lives in the
``reap_orphan_containers()`` path (see issue #20561 commit 3): if no
Hermes process touches a labeled container for ``2 × lifetime_seconds``
it gets ``docker rm -f``'d at the next Hermes startup. That covers the
SIGKILL / OOM / abandoned-laptop cases without us needing to stop the
container on every graceful exit.

Opt-out mode (``persist_across_processes=False``) still does
``docker stop`` + ``docker rm -f`` on every cleanup, matching the
pre-PR behavior for users who explicitly want per-process isolation.

``force_remove=True`` overrides persist mode and always tears the
container down (``docker stop`` + ``docker rm -f``). This is the
explicit-teardown path for ``/reset``, ``cleanup_vm(task_id)``-driven
resets, or any caller that wants a guaranteed fresh container on next
``DockerEnvironment(task_id=...)``. No current caller passes
``force_remove=True``; the parameter is here so the explicit-teardown
semantics can be wired up later without changing this method's
signature.

Cleanup runs on a daemon thread with bounded ``subprocess.run`` calls
(not the racy ``Popen(... &)`` pattern from before PR #33645). The
atexit hook in ``tools/terminal_tool.py`` waits up to 15s for the
thread to finish before the interpreter exits, so ``docker stop`` /
``docker rm`` actually completes when we do trigger it.

#### def `wait_for_cleanup(self, timeout: float = 30.0) -> bool`

Block up to *timeout* seconds for the cleanup worker thread.

Returns ``True`` if the thread finished (or no thread was started),
``False`` on timeout. The atexit hook in terminal_tool.py calls this
on every active environment so docker stop/rm actually completes
before the Python process exits — without this, ``hermes /quit``
races the interpreter shutdown and leaves stopped containers behind.


### 顶层函数

#### def `reap_orphan_containers(max_age_seconds: int = 600, profile_filter: str | None = None, docker_exe: str | None = None) -> int`

Remove stale hermes-tagged containers left behind by prior processes.

Targets containers that match all of:

* ``label=hermes-agent=1`` (created by this codebase)
* ``status=exited`` (running containers are NEVER reaped — they may
  belong to a sibling Hermes process whose reuse path will pick them
  up; killing them would crash the sibling mid-command)
* (optional) ``label=hermes-profile=<profile_filter>`` (sweep only the
  caller's profile by default; a hermes process in profile A must not
  tear down profile B's containers)
* ``State.FinishedAt`` older than *max_age_seconds* ago (so a sibling
  process that just exited and is about to be replaced doesn't get
  its container yanked out from under it)

Returns the number of containers removed. Best-effort: any failure
(docker daemon unreachable, slow inspect, parse error) is logged at
debug level and the function returns whatever it managed before the
failure. Safe to call repeatedly; idempotent.

Issue #20561 — this is the safety net for SIGKILL / OOM / crashed
terminal exits that bypass the ``atexit`` cleanup hook. Without it,
even with the cleanup-fix in the prior commit, a hard-killed Hermes
process leaves its container behind permanently because there's no
subsequent Hermes process scheduled to reuse that exact (task, profile)
pair.

#### def `find_docker() -> Optional[str]`

Locate the docker (or podman) CLI binary.

Resolution order:
1. ``HERMES_DOCKER_BINARY`` env var — explicit override (e.g. ``/usr/bin/podman``)
2. ``docker`` on PATH via ``shutil.which``
3. ``podman`` on PATH via ``shutil.which``
4. Well-known macOS Docker Desktop install locations

Returns the absolute path, or ``None`` if neither runtime can be found.


## tools.environments.file_sync

### 模块文档

Shared file sync manager for remote execution backends.

Tracks local file changes via mtime+size, detects deletions, and
syncs to remote environments transactionally.  Used by SSH, Modal,
and Daytona.  Docker and Singularity use bind mounts (live host FS
view) and don't need this.

### class FileSyncManager

> 继承: `object` ｜ 方法数: 9（公开 2）

Tracks local file changes and syncs to a remote environment.

Backends instantiate this with transport callbacks (upload, delete)
and a file-source callable.  The manager handles mtime-based change
detection, deletion tracking, rate limiting, and transactional state.

Not used by bind-mount backends (Docker, Singularity) — those get
live host FS views and don't need file sync.

#### def `__init__(get_files_fn: GetFilesFn, upload_fn: UploadFn, delete_fn: DeleteFn, sync_interval: float = _SYNC_INTERVAL_SECONDS, bulk_upload_fn: BulkUploadFn | None = None, bulk_download_fn: BulkDownloadFn | None = None)`

#### def `sync(self, force: bool = False) -> None`

Run a sync cycle: upload changed files, delete removed files.

Rate-limited to once per ``sync_interval`` unless *force* is True
or ``HERMES_FORCE_FILE_SYNC=1`` is set.

Transactional: state only committed if ALL operations succeed.
On failure, state rolls back so the next cycle retries everything.

#### def `sync_back(self, hermes_home: Path | None = None) -> None`

Pull remote changes back to the host filesystem.

Downloads the remote ``.hermes/`` directory as a tar archive,
unpacks it, and applies only files that differ from what was
originally pushed (based on SHA-256 content hashes).

Protected against SIGINT (defers the signal until complete) and
serialized across concurrent gateway sandboxes via file lock.


### 顶层函数

#### def `iter_sync_files(container_base: str = '/root/.hermes') -> list[tuple[str, str]]`

Enumerate all files that should be synced to a remote environment.

Combines credentials, skills, and cache into a single flat list of
(host_path, remote_path) pairs.  Credential paths are remapped from
the hardcoded /root/.hermes to *container_base* because the remote
user's home may differ (e.g. /home/daytona, /home/user).

#### def `quoted_rm_command(remote_paths: list[str]) -> str`

Build a shell ``rm -f`` command for a batch of remote paths.

#### def `quoted_mkdir_command(dirs: list[str]) -> str`

Build a shell ``mkdir -p`` command for a batch of directories.

#### def `unique_parent_dirs(files: list[tuple[str, str]]) -> list[str]`

Extract sorted unique parent directories from (host, remote) pairs.


## tools.environments.local

### 模块文档

Local execution environment — spawn-per-call with session snapshot.

### class LocalEnvironment

> 继承: `BaseEnvironment` ｜ 方法数: 9（公开 2）

Run commands directly on the host machine.

Spawn-per-call: every execute() spawns a fresh bash process.
Session snapshot preserves env vars across calls.
CWD persists via file-based read after each command.

#### def `__init__(cwd: str = '', timeout: int = 60, env: dict = None)`

#### def `get_temp_dir(self) -> str`

Return a shell-safe writable temp dir for local execution.

Termux does not provide /tmp by default, but exposes a POSIX TMPDIR.
Prefer POSIX-style env vars when available, keep using /tmp on regular
Unix systems, and only fall back to tempfile.gettempdir() when it also
resolves to a POSIX path.

Check the environment configured for this backend first so callers can
override the temp root explicitly (for example via terminal.env or a
custom TMPDIR), then fall back to the host process environment.

**Windows:** hardcoded ``/tmp`` is wrong in two ways — native Python
can't open the path, and the Windows default temp (``%TEMP%``) often
contains spaces (``C:\Users\Some Name\AppData\Local\Temp``) that
break unquoted bash interpolations.  Use a dedicated cache dir under
``HERMES_HOME`` instead — single-word path, guaranteed to exist, same
string resolves in both Git Bash and native Python.

#### def `cleanup(self)`

Clean up temp files.


### 顶层函数

#### def `hermes_subprocess_env(inherit_credentials: bool = False) -> dict[str, str]`

Build a sanitized environment dict for a spawned subprocess.

Centralized helper for the **non-terminal** spawn surface (browser,
ACP/CLI executors, computer-use driver, dep-ensure, TUI Node host,
detached gateway).  Use this instead of copying ``os.environ`` directly
so strip-by-default is the uniform policy across every spawn site, with a
single source of truth (``_HERMES_PROVIDER_ENV_BLOCKLIST``).  The terminal
/ execute_code path keeps using :func:`_sanitize_subprocess_env`, which is
skill-aware (``env_passthrough``); this helper is for spawns that have no
skill-passthrough concept.

Two-tier stripping:

* **Tier 1 (always):** ``_ALWAYS_STRIP_KEYS`` — gateway bot tokens, GitHub
  auth, and remote-compute secrets are removed regardless of
  ``inherit_credentials``.  No child Hermes spawns legitimately needs them.
* **Tier 2 (conditional):** the rest of ``_HERMES_PROVIDER_ENV_BLOCKLIST``
  (LLM provider API keys, tool secrets) is removed unless the caller passes
  ``inherit_credentials=True``.

Pass ``inherit_credentials=True`` **only** when the child legitimately
needs LLM provider credentials — a user-blessed ``claude`` / ``codex`` /
``gemini`` CLI executor, or the TUI Node host that makes model calls.  The
flag is grep-able for audit: ``grep -rn 'inherit_credentials=True'`` lists
every spawn site that still receives provider credentials.

Callers that need a *specific* non-provider secret (e.g. the browser worker
needs ``BROWSERBASE_API_KEY`` / ``FIRECRAWL_API_KEY``) should call with
``inherit_credentials=False`` and copy just those keys back from
``os.environ`` into the returned dict.


## tools.environments.managed_modal

### 模块文档

Managed Modal environment backed by tool-gateway.

### class ManagedModalEnvironment

> 继承: `BaseModalExecutionEnvironment` ｜ 方法数: 12（公开 1）

Gateway-owned Modal sandbox with Hermes-compatible execute/cleanup.

#### def `__init__(image: str, cwd: str = '/root', timeout: int = 60, modal_sandbox_kwargs: Optional[Dict[str, Any]] = None, persistent_filesystem: bool = True, task_id: str = 'default')`

**异常**: `ValueError`

#### def `cleanup(self)`


## tools.environments.modal

### 模块文档

Modal cloud execution environment using the native Modal SDK directly.

Uses ``Sandbox.create()`` + ``Sandbox.exec()`` instead of the older runtime
wrapper, while preserving Hermes' persistent snapshot behavior across sessions.

### class ModalEnvironment

> 继承: `BaseEnvironment` ｜ 方法数: 8（公开 1）

Modal cloud execution via native Modal sandboxes.

Spawn-per-call via _ThreadedProcessHandle wrapping async SDK calls.
cancel_fn wired to sandbox.terminate for interrupt support.

#### def `__init__(image: str, cwd: str = '/root', timeout: int = 60, modal_sandbox_kwargs: Optional[dict[str, Any]] = None, persistent_filesystem: bool = True, task_id: str = 'default')`

#### def `cleanup(self)`

Snapshot the filesystem (if persistent) then stop the sandbox.


## tools.environments.modal_utils

### 模块文档

Shared Hermes-side execution flow for Modal transports.

This module deliberately stops at the Hermes boundary:
- command preparation
- cwd/timeout normalization
- stdin/sudo shell wrapping
- common result shape
- interrupt/cancel polling

Direct Modal and managed Modal keep separate transport logic, persistence, and
trust-boundary decisions in their own modules.

### class PreparedModalExec

> 继承: `object` ｜ 方法数: 0（公开 0）

Normalized command data passed to a transport-specific exec runner.


### class ModalExecStart

> 继承: `object` ｜ 方法数: 0（公开 0）

Transport response after starting an exec.


### class BaseModalExecutionEnvironment

> 继承: `BaseEnvironment` ｜ 方法数: 9（公开 1）

Execution flow for the *managed* Modal transport (gateway-owned sandbox).

This deliberately overrides :meth:`BaseEnvironment.execute` because the
tool-gateway handles command preparation, CWD tracking, and env-snapshot
management on the server side.  The base class's ``_wrap_command`` /
``_wait_for_process`` / snapshot machinery does not apply here — the
gateway owns that responsibility.  See ``ManagedModalEnvironment`` for the
concrete subclass.

#### def `execute(self, command: str, cwd: str = '', timeout: int | None = None, stdin_data: str | None = None, rewrite_compound_background: bool = True, bounded_capture: bool = False) -> dict`


### 顶层函数

#### def `wrap_modal_stdin_heredoc(command: str, stdin_data: str) -> str`

Append stdin as a shell heredoc for transports without stdin piping.

#### def `wrap_modal_sudo_pipe(command: str, sudo_stdin: str) -> str`

Feed sudo via a shell pipe for transports without direct stdin piping.


## tools.environments.singularity

### 模块文档

Singularity/Apptainer persistent container environment.

Security-hardened with --containall, --no-home, capability dropping.
Supports configurable resource limits and optional filesystem persistence
via writable overlay directories that survive across sessions.

### class SingularityEnvironment

> 继承: `BaseEnvironment` ｜ 方法数: 4（公开 1）

Hardened Singularity/Apptainer container with resource limits and persistence.

Spawn-per-call: every execute() spawns a fresh ``apptainer exec ... bash -c`` process.
Session snapshot preserves env vars across calls.
CWD persists via in-band stdout markers.

#### def `__init__(image: str, cwd: str = '~', timeout: int = 60, cpu: float = 0, memory: int = 0, disk: int = 0, persistent_filesystem: bool = False, task_id: str = 'default')`

#### def `cleanup(self)`

Stop the instance. If persistent, the overlay dir survives.


## tools.environments.ssh

### 模块文档

SSH remote execution environment with ControlMaster connection persistence.

### class SSHEnvironment

> 继承: `BaseEnvironment` ｜ 方法数: 12（公开 1）

Run commands on a remote machine over SSH.

Spawn-per-call: every execute() spawns a fresh ``ssh ... bash -c`` process.
Session snapshot preserves env vars across calls.
CWD persists via in-band stdout markers.
Uses SSH ControlMaster for connection reuse.

#### def `__init__(host: str, user: str, cwd: str = '~', timeout: int = 60, port: int = 22, key_path: str = '')`

#### def `cleanup(self)`


## tools.fal_common

### 模块文档

Shared FAL.ai SDK plumbing.

Holds the stateless atoms that every FAL-backed tool needs:

* :func:`import_fal_client` — lazy import + ``lazy_deps`` integration so
  ``fal_client`` isn't pulled at cold start (it added ~64 ms per CLI
  invocation when imported eagerly).
* :class:`_ManagedFalSyncClient` — wrapper that drives a Nous-managed
  fal-queue gateway through the standard ``fal_client.SyncClient``
  primitives.
* :func:`_normalize_fal_queue_url_format`, :func:`_extract_http_status`
  — small helpers used by both the managed client wrapper and
  ``_submit_fal_request``.

Stateful pieces (cache globals, ``_managed_fal_client*`` selectors,
``_submit_fal_request``) intentionally stay on
:mod:`tools.image_generation_tool`. That module is the patch target for
existing test suites (``tests/tools/test_image_generation.py``,
``tests/tools/test_managed_media_gateways.py``) and for the
``plugins/image_gen/fal/`` plugin's ``_it`` indirection — moving the
caches here would silently defeat ``monkeypatch.setattr(image_tool,
"_managed_fal_client", None)`` because the lookups would go against
``fal_common``'s namespace instead. See the per-rule walkthrough at
issue #26241 for details.

### 顶层函数

#### def `import_fal_client() -> Any`

Import ``fal_client`` (via ``lazy_deps`` when available) and return
the module reference.

Callers are responsible for caching the result on their own module
global — keeping per-module globals lets tests monkey-patch the
target module's ``fal_client`` attribute and have the patched value
stick for that module's call sites.

Raises :class:`ImportError` if the package is genuinely unavailable.

**异常**: `class`, `ImportError`


## tools.feishu_doc_tool

### 模块文档

Feishu Document Tool -- read document content via Feishu/Lark API.

Provides ``feishu_doc_read`` for reading document content as plain text.
Uses the same lazy-import + BaseRequest pattern as feishu_comment.py.

### 顶层函数

#### def `set_client(client)`

Store a lark client for the current thread (called by feishu_comment).

#### def `get_client()`

Return the lark client for the current thread, or None.


## tools.feishu_drive_tool

### 模块文档

Feishu Drive Tools -- document comment operations via Feishu/Lark API.

Provides tools for listing, replying to, and adding document comments.
Uses the same lazy-import + BaseRequest pattern as feishu_comment.py.
The lark client is injected per-thread by the comment event handler.

### 顶层函数

#### def `set_client(client)`

Store a lark client for the current thread (called by feishu_comment).

#### def `get_client()`

Return the lark client for the current thread, or None.


## tools.file_operations

### 模块文档

File Operations Module

Provides file manipulation capabilities (read, write, patch, search) that work
across all terminal backends (local, docker, ssh, singularity, modal, daytona).

The key insight is that all file operations can be expressed as shell commands,
so we wrap the terminal backend's execute() interface to provide a unified file API.

Usage:
    from tools.file_operations import ShellFileOperations
    from tools.terminal_tool import _active_environments
    
    # Get file operations for a terminal environment
    file_ops = ShellFileOperations(terminal_env)
    
    # Read a file
    result = file_ops.read_file("/path/to/file.py")
    
    # Write a file
    result = file_ops.write_file("/path/to/new.py", "print('hello')")
    
    # Search for content
    result = file_ops.search("TODO", path=".", file_glob="*.py")

### class ReadResult

> 继承: `object` ｜ 方法数: 1（公开 1）

Result from reading a file.

#### def `to_dict(self) -> dict`


### class WriteResult

> 继承: `object` ｜ 方法数: 1（公开 1）

Result from writing a file.

#### def `to_dict(self) -> dict`


### class PatchResult

> 继承: `object` ｜ 方法数: 1（公开 1）

Result from patching a file.

#### def `to_dict(self) -> dict`


### class SearchMatch

> 继承: `object` ｜ 方法数: 0（公开 0）

A single search match.


### class SearchResult

> 继承: `object` ｜ 方法数: 2（公开 1）

Result from searching.

#### def `to_dict(self, densify: bool = False) -> dict`


### class LintResult

> 继承: `object` ｜ 方法数: 1（公开 1）

Result from linting a file.

#### def `to_dict(self) -> dict`


### class ExecuteResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result from executing a shell command.


### class FileOperations

> 继承: `ABC` ｜ 方法数: 9（公开 9）

Abstract interface for file operations across terminal backends.

#### def `read_file(self, path: str, offset: int = 1, limit: int = 500) -> ReadResult`

Read a file with pagination support.

#### def `read_file_raw(self, path: str) -> ReadResult`

Read the complete file content as a plain string.

No pagination, no line-number prefixes, no per-line truncation.
Returns ReadResult with .content = full file text, .error set on
failure. Always reads to EOF regardless of file size.

#### def `write_file(self, path: str, content: str) -> WriteResult`

Write content to a file, creating directories as needed.

#### def `patch_replace(self, path: str, old_string: str, new_string: str, replace_all: bool = False) -> PatchResult`

Replace text in a file using fuzzy matching.

#### def `patch_v4a(self, patch_content: str) -> PatchResult`

Apply a V4A format patch.

#### def `delete_file(self, path: str) -> WriteResult`

Delete a file. Returns WriteResult with .error set on failure.

#### def `delete_path(self, path: str, recursive: bool = False) -> WriteResult`

Cross-platform delete that handles files and (with recursive=True)
directory trees. Default implementation delegates to ``delete_file``
for the non-recursive case; backends with native recursive support
should override.

#### def `move_file(self, src: str, dst: str) -> WriteResult`

Move/rename a file from src to dst. Returns WriteResult with .error set on failure.

#### def `search(self, pattern: str, path: str = '.', target: str = 'content', file_glob: Optional[str] = None, limit: int = 50, offset: int = 0, output_mode: str = 'content', context: int = 0) -> SearchResult`

Search for content or files.


### class ShellFileOperations

> 继承: `FileOperations` ｜ 方法数: 35（公开 9）

File operations implemented via shell commands.

Works with ANY terminal backend that has execute(command, cwd) method.
This includes local, docker, singularity, ssh, modal, and daytona environments.

#### def `__init__(terminal_env, cwd: str = None)`

Initialize file operations with a terminal environment.

Args:
    terminal_env: Any object with execute(command, cwd) method.
                 Returns {"output": str, "returncode": int}
    cwd: Optional explicit fallback cwd when the terminal env has
         no cwd attribute (rare — most backends track cwd live).

Note:
    Every _exec() call prefers the LIVE ``terminal_env.cwd`` over
    ``self.cwd`` so ``cd`` commands run via the terminal tool are
    picked up immediately.  ``self.cwd`` is only used as a fallback
    when the env has no cwd at all — it is NOT the authoritative
    cwd, despite being settable at init time.

    Historical bug (fixed): prior versions of this class used the
    init-time cwd for every _exec() call, which caused relative
    paths passed to patch/read/write to target the wrong directory
    after the user ran ``cd`` in the terminal.  Patches would
    claim success and return a plausible diff but land in the
    original directory, producing apparent silent failures.

#### def `read_file(self, path: str, offset: int = 1, limit: int = 500) -> ReadResult`

Read a file with pagination, binary detection, and line numbers.

Args:
    path: File path (absolute or relative to cwd)
    offset: Line number to start from (1-indexed, default 1)
    limit: Maximum lines to return (default 500, max 2000)

Returns:
    ReadResult with content, metadata, or error info

#### def `read_file_raw(self, path: str) -> ReadResult`

Read the complete file content as a plain string.

No pagination, no line-number prefixes, no per-line truncation.
Uses cat so the full file is returned regardless of size.

#### def `delete_file(self, path: str) -> WriteResult`

Delete a single file.

Cross-platform: runs via ``python -c`` against the terminal env's
Python so it works on Windows shells (``cmd.exe``/PowerShell) that
don't ship ``rm``. Directories are rejected here — use
``delete_path(recursive=True)`` for trees.

#### def `delete_path(self, path: str, recursive: bool = False) -> WriteResult`

Cross-platform delete that handles files and (with recursive=True)
directory trees. Always preferred over emitting ``rm -rf`` /
``Remove-Item -Recurse`` directly so the same tool call works on
every backend (local / docker / ssh / Windows).

#### def `move_file(self, src: str, dst: str) -> WriteResult`

Move a file via mv.

#### def `write_file(self, path: str, content: str) -> WriteResult`

Write content to a file, creating parent directories as needed.

Pipes content through stdin to avoid OS ARG_MAX limits on large
files. The content never appears in the shell command string —
only the file path does.

Before anything touches disk, a fail-closed syntax gate runs
against the CANDIDATE content: if ``path``'s extension is in
``_FAIL_CLOSED_INPROC_EXTS`` (JSON/YAML/TOML — structured data
formats where a parse failure always means corruption) and the
candidate content doesn't parse, the write is refused outright.
No temp file, no rename, nothing on disk changes.

After a write that clears the gate, runs a post-first / pre-lazy
lint check via ``_check_lint_delta()``.  If the new content is
clean, the lint call is O(one parse).  If the new content has
errors the gate didn't already catch (i.e. errors from a linter
outside ``_FAIL_CLOSED_INPROC_EXTS``, such as Python), the
pre-write content is linted too and only errors newly introduced
by this write are surfaced — pre-existing problems are filtered
out so the agent isn't distracted chasing them.

Args:
    path: File path to write
    content: Content to write

Returns:
    WriteResult with bytes written, lint summary, or error.

#### def `patch_replace(self, path: str, old_string: str, new_string: str, replace_all: bool = False) -> PatchResult`

Replace text in a file using fuzzy matching.

Args:
    path: File path to modify
    old_string: Text to find (must be unique unless replace_all=True)
    new_string: Replacement text
    replace_all: If True, replace all occurrences

Returns:
    PatchResult with diff and lint results

#### def `patch_v4a(self, patch_content: str) -> PatchResult`

Apply a V4A format patch.

V4A format:
    *** Begin Patch
    *** Update File: path/to/file.py
    @@ context hint @@
     context line
    -removed line
    +added line
    *** End Patch

Args:
    patch_content: V4A format patch string

Returns:
    PatchResult with changes made

#### def `search(self, pattern: str, path: str = '.', target: str = 'content', file_glob: Optional[str] = None, limit: int = 50, offset: int = 0, output_mode: str = 'content', context: int = 0) -> SearchResult`

Search for content or files.

Args:
    pattern: Regex (for content) or glob pattern (for files)
    path: Directory/file to search (default: cwd)
    target: "content" (grep) or "files" (glob)
    file_glob: File pattern filter for content search (e.g., "*.py")
    limit: Max results (default 50)
    offset: Skip first N results
    output_mode: "content", "files_only", or "count"
    context: Lines of context around matches

Returns:
    SearchResult with matches or file list


### 顶层函数

#### def `normalize_read_pagination(offset: Any = DEFAULT_READ_OFFSET, limit: Any = DEFAULT_READ_LIMIT) -> tuple[int, int]`

Return safe read_file pagination bounds.

Tool schemas declare minimum/maximum values, but not every caller or
provider enforces schemas before dispatch. Clamp here so invalid values
cannot leak into sed ranges like ``0,-1p``.

The upper bound on ``limit`` comes from ``tool_output.max_lines`` in
config.yaml (defaults to the module-level ``MAX_LINES`` constant).

#### def `normalize_search_pagination(offset: Any = DEFAULT_SEARCH_OFFSET, limit: Any = DEFAULT_SEARCH_LIMIT) -> tuple[int, int]`

Return safe search pagination bounds for shell head/tail pipelines.


## tools.file_state

### 模块文档

Cross-agent file state coordination.

Prevents mangled edits when concurrent subagents (same process, same
filesystem) touch the same file. Complements the single-agent path-overlap
check in ``run_agent._should_parallelize_tool_batch`` — this module catches
the case where subagent B writes a file that subagent A already read, so
A's next write would overwrite B's changes with stale content.

Design
------
A process-wide singleton ``FileStateRegistry`` tracks, per resolved path:

  * per-agent read stamps: {task_id: {path: (mtime, read_ts, partial)}}
  * last writer globally: {path: (task_id, write_ts)}
  * per-path ``threading.Lock`` for read→modify→write critical sections

Three public hooks are used by the file tools:

  * ``record_read(task_id, path, *, partial)`` — called by read_file
  * ``note_write(task_id, path)`` — called after write_file / patch
  * ``check_stale(task_id, path)`` — called BEFORE write_file / patch

Plus ``lock_path(path)`` — a context-manager returning a per-path lock to
wrap the whole read→modify→write block. And ``writes_since(task_id,
since_ts, paths)`` for the subagent-completion reminder in delegate_tool.

All methods are no-ops when ``HERMES_DISABLE_FILE_STATE_GUARD=1`` is set.

This module is intentionally separate from ``_read_tracker`` in
``file_tools.py`` — that tracker is per-task and handles consecutive-read
loop detection, which is a different concern.

### class FileStateRegistry

> 继承: `object` ｜ 方法数: 9（公开 7）

Process-wide coordinator for cross-agent file edits.

#### def `__init__() -> None`

#### def `lock_path(self, resolved: str)`

Acquire the per-path lock for a read→modify→write section.

Same process, same filesystem — threads on the same path serialize.
Different paths proceed in parallel.

#### def `record_read(self, task_id: str, resolved: str, partial: bool = False, mtime: Optional[float] = None) -> None`

#### def `note_write(self, task_id: str, resolved: str, mtime: Optional[float] = None) -> None`

Record a successful write.

Updates the global last-writer map AND this agent's own read stamp
(a write is an implicit read — the agent now knows the current
content).

#### def `check_stale(self, task_id: str, resolved: str) -> Optional[str]`

Return a model-facing warning if this write would be stale.

Three staleness classes, in order of severity:

  1. Sibling subagent wrote this file after this agent's last read.
  2. External/unknown change (mtime differs from our last read).
  3. Agent never read the file (write-without-read).

Returns ``None`` when the write is safe.  Does not raise — callers
decide whether to block or warn.

#### def `writes_since(self, exclude_task_id: str, since_ts: float, paths: Iterable[str]) -> Dict[str, List[str]]`

Return ``{writer_task_id: [paths]}`` for writes done after
``since_ts`` by agents OTHER than ``exclude_task_id``.

Used by delegate_task to append a "subagent modified files the
parent previously read" reminder to the delegation result.

#### def `known_reads(self, task_id: str) -> List[str]`

Return the list of resolved paths this agent has read.

#### def `clear(self) -> None`

Reset all state.  Intended for tests only.


### 顶层函数

#### def `get_registry() -> FileStateRegistry`

#### def `record_read(task_id: str, resolved_or_path: str | Path, partial: bool = False) -> None`

#### def `note_write(task_id: str, resolved_or_path: str | Path) -> None`

#### def `check_stale(task_id: str, resolved_or_path: str | Path) -> Optional[str]`

#### def `lock_path(resolved_or_path: str | Path)`

#### def `writes_since(exclude_task_id: str, since_ts: float, paths: Iterable[str | Path]) -> Dict[str, List[str]]`

#### def `known_reads(task_id: str) -> List[str]`


## tools.file_tools

### 模块文档

File Tools Module - LLM agent file manipulation tools.

### 顶层函数

#### def `clear_file_ops_cache(task_id: str = None)`

Clear the file operations cache.

#### def `read_file_tool(path: str, offset: int = 1, limit: int = 500, task_id: str = 'default') -> str`

Read a file with pagination and line numbers.

#### def `reset_file_dedup(task_id: str = None)`

Clear the deduplication cache for file reads.

Called after context compression — the original read content has been
summarised away, so the model needs the full content if it reads the
same file again.  Without this, reads after compression would return
a "file unchanged" stub pointing at content that no longer exists in
context.

Call with a task_id to clear just that task, or without to clear all.

#### def `notify_other_tool_call(task_id: str = 'default')`

Reset consecutive read/search counter for a task.

Called by the tool dispatcher (model_tools.py) whenever a tool OTHER
than read_file / search_files is executed.  This ensures we only warn
or block on *truly consecutive* repeated reads — if the agent does
anything else in between (write, patch, terminal, etc.) the counter
resets and the next read is treated as fresh.

#### def `write_file_tool(path: str, content: str, task_id: str = 'default', cross_profile: bool = False, session_id: str | None = None) -> str`

Write content to a file.

``cross_profile`` opts out of the soft cross-Hermes-profile guard. The
guard fires only on writes that land in another profile's
skills/plugins/cron/memories directory; everything else is unaffected.
Pass ``True`` after explicit user direction — same shape as ``force``
on the terminal tool.

#### def `patch_tool(mode: str = 'replace', path: str = None, old_string: str = None, new_string: str = None, replace_all: bool = False, patch: str = None, task_id: str = 'default', cross_profile: bool = False, session_id: str | None = None) -> str`

Patch a file using replace mode or V4A patch format.

``cross_profile`` opts out of the soft cross-Hermes-profile guard for
targets under another profile's skills/plugins/cron/memories
directory. Same shape as ``write_file``'s flag.

#### def `search_tool(pattern: str, target: str = 'content', path: str = '.', file_glob: str = None, limit: int = 50, offset: int = 0, output_mode: str = 'content', context: int = 0, task_id: str = 'default') -> str`

Search for content or files.


## tools.fuzzy_match

### 模块文档

Fuzzy Matching Module for File Operations

Implements a multi-strategy matching chain to robustly find and replace text,
accommodating variations in whitespace, indentation, and escaping common
in LLM-generated code.

The 9-strategy chain (inspired by OpenCode), tried in order:
1. Exact match - Direct string comparison
2. Line-trimmed - Strip leading/trailing whitespace per line
3. Whitespace normalized - Collapse multiple spaces/tabs to single space
4. Indentation flexible - Ignore indentation differences entirely
5. Escape normalized - Convert \n literals to actual newlines
6. Trimmed boundary - Trim first/last line whitespace only
7. Block anchor - Match first+last lines, use similarity for middle
8. Context-aware - 50% line similarity threshold

Multi-occurrence matching is handled via the replace_all flag.

Usage:
    from tools.fuzzy_match import fuzzy_find_and_replace
    
    new_content, match_count, strategy, error = fuzzy_find_and_replace(
        content="def foo():\n    pass",
        old_string="def foo():",
        new_string="def bar():",
        replace_all=False
    )

### 顶层函数

#### def `fuzzy_find_and_replace(content: str, old_string: str, new_string: str, replace_all: bool = False) -> Tuple[str, int, Optional[str], Optional[str]]`

Find and replace text using a chain of increasingly fuzzy matching strategies.

Args:
    content: The file content to search in
    old_string: The text to find
    new_string: The replacement text
    replace_all: If True, replace all occurrences; if False, require uniqueness

Returns:
    Tuple of (new_content, match_count, strategy_name, error_message)
    - If successful: (modified_content, number_of_replacements, strategy_used, None)
    - If failed: (original_content, 0, None, error_description)

#### def `find_closest_lines(old_string: str, content: str, context_lines: int = 2, max_results: int = 3) -> str`

Find lines in content most similar to old_string for "did you mean?" feedback.

Returns a formatted string showing the closest matching lines with context,
or empty string if no useful match is found.

#### def `format_no_match_hint(error: Optional[str], match_count: int, old_string: str, content: str) -> str`

Return a '\n\nDid you mean...' snippet for plain no-match errors.

Gated so the hint only fires for actual "old_string not found" failures.
Ambiguous-match ("Found N matches"), escape-drift, and identical-strings
errors all have ``match_count == 0`` but a "did you mean?" snippet would
be misleading — those failed for unrelated reasons.

Returns an empty string when there's nothing useful to append.


## tools.homeassistant_tool

### 模块文档

Home Assistant tool for controlling smart home devices via REST API.

Registers four LLM-callable tools:
- ``ha_list_entities`` -- list/filter entities by domain or area
- ``ha_get_state`` -- get detailed state of a single entity
- ``ha_list_services`` -- list available services (actions) per domain
- ``ha_call_service`` -- call a HA service (turn_on, turn_off, set_temperature, etc.)

Authentication uses a Long-Lived Access Token via ``HASS_TOKEN`` env var.
The HA instance URL is read from ``HASS_URL`` (default: http://homeassistant.local:8123).

## tools.hook_output_spill

### 模块文档

Spill oversized hook-injected context to disk with a preview placeholder.

Ported from openai/codex PR #21069 (``Spill large hook outputs from context``).

Background
----------
Both shell hooks (``agent/shell_hooks.py``) and Python plugins
(``pre_llm_call`` hook in ``run_agent.py``) can return ``{"context": "..."}``
which gets concatenated into the current turn's user message on EVERY
subsequent API call. If a hook emits a large blob (e.g. a debug dump, a
full file, or a runaway prompt-engineering script), that blob inflates
every turn of the session and blows out the prompt cache prefix the
moment it's appended.

This mirrors what Codex does for its ``PreToolUse``/``Stop``/feedback
hooks: once the injected text exceeds a configured budget, write the
full content to a per-session directory on disk and replace the in-prompt
payload with a head/tail preview plus the saved path. The model can still
inspect the full content via ``read_file`` or ``terminal`` if it needs to.

Config (``config.yaml``)::

    hooks:
      output_spill:
        enabled: true          # default: true; set false to disable spilling
        max_chars: 10000       # default; context above this is spilled
        preview_head: 500      # chars shown at the start of the preview
        preview_tail: 500      # chars shown at the end of the preview
        directory: null        # default: <HERMES_HOME>/hook_outputs

Design invariants
-----------------
* Behaviour-preserving when ``enabled: false`` or when content is under
  the cap — return the input string unchanged.
* Never raises. Any I/O error (disk full, permission denied, missing
  HERMES_HOME, etc.) falls back to a byte-length truncation with an
  in-prompt notice — the hook context still reaches the model, just
  bounded in size.
* Spill files are grouped by session so a ``/new`` session doesn't grow
  them forever in one directory.

### 顶层函数

#### def `get_spill_config() -> Dict[str, Any]`

Return resolved hook output-spill config. Never raises.

#### def `spill_if_oversized(text: str, session_id: Optional[str] = None, source: str = 'hook', config: Optional[Dict[str, Any]] = None) -> str`

Spill ``text`` to disk if it exceeds the configured cap.

Returns either ``text`` unchanged (when under the cap, disabled, or
empty) or a preview string with a filesystem path pointing at the
full content.

Parameters
----------
text:
    The raw injected-context string from a hook. Non-string inputs
    are coerced with ``str()``.
session_id:
    Used to group spill files by conversation. Falls back to
    ``"no-session"`` if missing.
source:
    Human-readable label used in the preview header (``"hook"``,
    ``"plugin hook"``, ``"shell hook"``, etc.). Free-form.
config:
    Optional override for tests; normally resolved from
    ``config.yaml``.


## tools.image_generation_tool

### 模块文档

Image Generation Tools Module

Provides image generation via FAL.ai. Multiple FAL models are supported and
selectable via ``hermes tools`` → Image Generation; the active model is
persisted to ``image_gen.model`` in ``config.yaml``.

Architecture:
- ``FAL_MODELS`` is a catalog of supported models with per-model metadata
  (size-style family, defaults, ``supports`` whitelist, upscaler flag).
- ``_build_fal_payload()`` translates the agent's unified inputs (prompt +
  aspect_ratio) into the model-specific payload and filters to the
  ``supports`` whitelist so models never receive rejected keys.
- Upscaling via FAL's Clarity Upscaler is gated per-model via the ``upscale``
  flag — on for FLUX 2 Pro (backward-compat), off for all faster/newer models
  where upscaling would either hurt latency or add marginal quality.

Pricing shown in UI strings is as-of the initial commit; we accept drift and
update when it's noticed.

### 顶层函数

#### def `image_generate_tool(prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, num_inference_steps: Optional[int] = None, guidance_scale: Optional[float] = None, num_images: Optional[int] = None, output_format: Optional[str] = None, seed: Optional[int] = None, image_url: Optional[str] = None, reference_image_urls: Optional[list] = None) -> str`

Generate an image from a text prompt, or edit a source image, via FAL.

Routing: when ``image_url`` (or ``reference_image_urls``) is provided AND
the configured model declares an ``edit_endpoint``, the call routes to that
image-to-image / edit endpoint; otherwise it's plain text-to-image.

The agent-facing schema exposes ``prompt``, ``aspect_ratio``, ``image_url``
and ``reference_image_urls``; the remaining kwargs are overrides for direct
Python callers and are filtered per-model via the ``supports`` /
``edit_supports`` whitelist (unsupported overrides are silently dropped so
legacy callers don't break when switching models).

Returns a JSON string with ``{"success": bool, "image": url | None,
"modality": "text" | "image", "error": str, "error_type": str}``.

**异常**: `ValueError`

#### def `check_fal_api_key() -> bool`

True if the FAL.ai API key (direct or managed gateway) is available.

#### def `check_image_generation_requirements() -> bool`

True if FAL or the explicitly configured image backend is available.

#### def `is_krea_model(model_id: Optional[str]) -> bool`

True when ``model_id`` is a native Krea plugin id (``krea-2-*``).


## tools.image_source

### 模块文档

Single resolver for every vision_analyze image source -> bytes + mime.

All source handling (data:/http(s)/file/local/container) funnels through
:func:`resolve_image_source` so size and magic-byte checks are enforced exactly
once.  Returns raw bytes (not a path): the downstream step is base64 -> data URL
(RFC 2397) and provider base64 content blocks.

Security (terminal-backend confinement, GHSA-gpxw-6wxv-w3qq): under a non-local
terminal backend the file tools are confined to the sandbox (SECURITY.md 2.2),
but vision read images host-side. This resolver enforces the same boundary:

  * local backend            -> read any host path (chosen posture, unchanged)
  * non-local backend:
      path in a media cache   -> host-read (the gateway/download caches live on
                                 the host and are bind-mounted into the sandbox)
      path anywhere else      -> read the bytes *inside the sandbox* via exec-read
                                 (the agent can already ``cat`` any container file;
                                 this stays within the sandbox boundary and never
                                 reaches the host's ``/etc/passwd`` / ``~/.ssh``).

So a prompt-injected ``vision_analyze('/etc/passwd')`` under Docker reads the
*container's* file (what every other tool sees), not the host's — no escape —
while container-only images (tmpfs ``/workspace``, root-owned) are still
deliverable. This is the unified delivery + confinement model: the same
mechanism that fixes "vision can't see container files" also closes the escape.

### class ImageResolutionError

> 继承: `Exception` ｜ 方法数: 1（公开 0）

#### def `__init__(message: str, src: str = '', origin: str = '')`


### class UnsupportedScheme

> 继承: `ImageResolutionError` ｜ 方法数: 0（公开 0）


### class SourceUnsafe

> 继承: `ImageResolutionError` ｜ 方法数: 0（公开 0）


### class SourceTooLarge

> 继承: `ImageResolutionError` ｜ 方法数: 0（公开 0）


### class SourceNotFound

> 继承: `ImageResolutionError` ｜ 方法数: 0（公开 0）


### class NotAnImage

> 继承: `ImageResolutionError` ｜ 方法数: 0（公开 0）


### class ResolveContext

> 继承: `object` ｜ 方法数: 0（公开 0）


### class ResolvedImage

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `resolve_image_source(src: str, ctx: ResolveContext) -> ResolvedImage`

**异常**: `SourceNotFound`, `UnsupportedScheme`, `SourceUnsafe`


## tools.interrupt

### 模块文档

Per-thread interrupt signaling for all tools.

Provides thread-scoped interrupt tracking so that interrupting one agent
session does not kill tools running in other sessions.  This is critical
in the gateway where multiple agents run concurrently in the same process.

The agent stores its execution thread ID at the start of run_conversation()
and passes it to set_interrupt()/clear_interrupt().  Tools call
is_interrupted() which checks the CURRENT thread — no argument needed.

Usage in tools:
    from tools.interrupt import is_interrupted
    if is_interrupted():
        return {"output": "[interrupted]", "returncode": 130}

### 顶层函数

#### def `set_interrupt(active: bool, thread_id: int | None = None) -> None`

Set or clear interrupt for a specific thread.

Args:
    active: True to signal interrupt, False to clear it.
    thread_id: Target thread ident.  When None, targets the
               current thread (backward compat for CLI/tests).

#### def `is_interrupted() -> bool`

Check if an interrupt has been requested for the current thread.

Safe to call from any thread — each thread only sees its own
interrupt state.

#### def `clear_current_thread_interrupt() -> None`

Clear any interrupt bit on the CURRENT thread.

Gives a user-approved command a clean interrupt slate immediately before
it spawns its child process, so a stale bit that landed on this thread
during the blocking approval-wait cannot SIGINT the just-approved run
(exit 130 + "[Command interrupted]").  Single-thread ordering on this tid
keeps the DO-NOT-BREAK invariant intact: a *genuine* interrupt arriving
after this call re-sets the bit on the same thread and is still observed by
the executor's poll loop.  Call this directly, never via the
_interrupt_event proxy (its .clear() binds to whatever thread runs it).


## tools.kanban_tools

### 模块文档

Kanban tools — structured tool-call surface for worker + orchestrator agents.

These tools are registered into the model's schema when the agent is
running under the dispatcher (env var ``HERMES_KANBAN_TASK`` set) or when
the active profile explicitly enables the ``kanban`` toolset for
orchestrator work. A normal ``hermes chat`` session still sees **zero**
kanban tools in its schema unless configured.

Why tools instead of just shelling out to ``hermes kanban``?

1. **Backend portability.** A worker whose terminal tool points at Docker
   / Modal / Singularity / SSH would run ``hermes kanban complete …``
   inside the container, where ``hermes`` isn't installed and the DB
   isn't mounted. Tools run in the agent's Python process, so they
   always reach ``~/.hermes/kanban.db`` regardless of terminal backend.

2. **No shell-quoting footguns.** Passing ``--metadata '{"x": [...]}'``
   through shlex+argparse is fragile. Structured tool args skip it.

3. **Better errors.** Tool-call failures return structured JSON the
   model can reason about, not stderr strings it has to parse.

Humans continue to use the CLI (``hermes kanban …``), the dashboard
(``hermes dashboard``), and the slash command (``/kanban …``) — all
three bypass the agent entirely. The tools are for dispatcher-spawned
worker handoffs and for configured orchestrator profiles that route work
through the board.

### 顶层函数

#### def `heartbeat_current_worker_from_env() -> bool`

Best-effort: extend the kanban claim + bump board heartbeat for the
current dispatcher-spawned worker, using identity from env vars.

Returns True if a write was attempted (whether or not it succeeded);
False if the call was skipped (not a kanban worker, rate-limited, or
swallowed exception). The boolean is informational — callers should
not branch on it.

Identity comes from:
  * ``HERMES_KANBAN_TASK`` — task id (required; absence means no-op)
  * ``HERMES_KANBAN_RUN_ID`` — pins the run row so we don't heartbeat
    a stale run that may have already been reclaimed
  * ``HERMES_KANBAN_CLAIM_LOCK`` — claim lock for ``heartbeat_claim``;
    falls back to the default ``_claimer_id()`` for locally-driven
    workers that never went through the dispatcher path

Rate-limited via the module-level ``_auto_heartbeat_last_attempt``
timestamp (monotonic clock); not thread-safe in the strict sense, but
the worst case is one extra DB write per race, which is harmless.


## tools.lazy_deps

### 模块文档

Lazy dependency installer for opt-in Hermes Agent backends.

Many Hermes features (Mistral TTS, ElevenLabs TTS, Honcho memory, Bedrock,
Slack, Matrix, etc.) require Python packages that not every user needs. The
historical approach was to bundle them all under ``pyproject.toml`` extras
(``hermes-agent[all]``) and install them eagerly at setup time. That has
two problems:

1. **Fragility.** When one extra's transitive dependency becomes
   unavailable on PyPI (quarantined for malware, yanked, broken upload),
   the *entire* ``[all]`` resolve fails and fresh installs silently fall
   back to a stripped tier — losing 10+ unrelated extras at once.

2. **Bloat.** A user who only ever talks to one provider pulls hundreds
   of packages they will never import.

The lazy-install pattern fixes both. Backends call :func:`ensure` at the
top of their first-import path. If the deps are missing, ``ensure`` checks
the ``security.allow_lazy_installs`` config flag (default true) and runs
a venv-scoped pip install. If the user has explicitly disabled lazy
installs, ``ensure`` raises :class:`FeatureUnavailable` with a clear
remediation hint pointing at ``hermes tools`` or the manual pip command.

Security model:

* **Venv-scoped by default.** Installs target ``sys.executable`` in the
  active venv. We never touch the system Python.
* **Durable-target mode (immutable images).** When the deployment seals the
  agent's own venv (the Docker image sets ``HERMES_DISABLE_LAZY_INSTALLS=1``
  and makes ``/opt/hermes`` read-only), setting
  ``HERMES_LAZY_INSTALL_TARGET`` redirects lazy installs to a writable
  directory on the durable data volume (e.g. ``/opt/data/lazy-packages``).
  That directory is **appended to the end of ``sys.path``** — never
  prepended, never exported via ``PYTHONPATH`` — so the agent's own
  site-packages wins every name collision. A package installed this way can
  only ADD new importable modules; it can never shadow, downgrade, or break
  a module the core already ships. The worst a bad/incompatible backend
  package can do is fail to import and report itself unavailable — the agent
  core stays healthy. This is the structural guarantee that a lazily
  installed package cannot brick Hermes, which is what made it safe to seal
  the venv in the first place. Compiled-wheel safety across image rebuilds
  is handled by an ABI/Python-version stamp on the target subdir (see
  :func:`_ensure_target_ready`).
* **PyPI by package name only.** Specs may be ``"package>=1.0,<2"`` etc.
  We do NOT support ``--index-url`` overrides, ``git+https://``, file:
  paths, or any other input that could be hijacked by a malicious config.
* **Allowlist.** Only specs that appear in :data:`LAZY_DEPS` can be
  installed via this path. A typo in feature name doesn't get the user
  install-anything semantics.
* **Opt-out.** Setting ``security.allow_lazy_installs: false`` in
  ``config.yaml`` disables runtime installs in BOTH modes. Users in
  restricted networks or strict security postures can pin themselves to
  whatever was installed at setup time.
* **Offline detection.** If the install fails (offline, mirror down,
  PyPI 404 / quarantine), we surface the failure as
  :class:`FeatureUnavailable` with the actual pip stderr — no silent
  retries, no caching of bad state.

Adding a new backend:

1. Add an entry to :data:`LAZY_DEPS` with the package specs.
2. At the top of the backend module's import path, call
   ``ensure("feature.name")`` inside a try/except that converts
   :class:`FeatureUnavailable` to a useful runtime error.

### class FeatureUnavailable

> 继承: `RuntimeError` ｜ 方法数: 2（公开 0）

A lazily-installable feature is missing and cannot be made available.

Either the deps were never installed and the user has disabled lazy
installs, or the install attempt failed.

#### def `__init__(feature: str, missing: tuple[str, ...], reason: str)`


### 顶层函数

#### def `activate_durable_lazy_target() -> None`

Public: wire the durable lazy-install target onto ``sys.path``.

Safe no-op when :data:`_LAZY_TARGET_ENV` is unset or the directory does
not yet exist. Called once early in process startup (before backends
import) so packages installed into the durable store on a previous run
are importable on this run. Never raises.

#### def `feature_specs(feature: str) -> tuple[str, ...]`

Return the registered specs for a feature, or raise KeyError.

**异常**: `KeyError`

#### def `feature_missing(feature: str) -> tuple[str, ...]`

Return the subset of specs for ``feature`` not currently installed.

#### def `ensure(feature: str, prompt: bool = True) -> None`

Make sure all packages for ``feature`` are importable.

If they're missing, attempts to install them in the active venv. Raises
:class:`FeatureUnavailable` if the user has disabled lazy installs or
if the install attempt fails.

``prompt``: when True (default) and stdin is a TTY, asks the user to
confirm before installing. Non-interactive callers (gateway, cron,
batch) get prompt=False and skip the confirmation — config flag is
the gate in that case.

**异常**: `class`, `FeatureUnavailable`

#### def `is_available(feature: str) -> bool`

Return True if the feature's deps are already satisfied.

#### def `feature_install_command(feature: str) -> Optional[str]`

Return the ``pip install`` command a user could run manually, or None.

#### def `active_features() -> list[str]`

Return the list of features the user has ever lazy-installed.

A feature counts as "active" if at least one of its declared packages
is currently installed in the venv (presence check, ignoring version).
Features the user has never enabled stay quiet.

Used by ``hermes update`` to figure out which lazy backends need a
refresh pass when pins move in :data:`LAZY_DEPS`.

#### def `refresh_active_features(prompt: bool = False) -> dict[str, str]`

Re-run ``ensure`` for every feature the user has previously activated.

Returns a ``{feature: status}`` map where status is one of:
    ``"current"``  — pins already satisfied, no install run
    ``"refreshed"`` — pins were stale, reinstall succeeded
    ``"failed: <reason>"`` — install attempt failed; caller decides
                              whether to surface it (we don't raise)
    ``"skipped: <reason>"`` — gated off (config flag, user decline)

Intended for ``hermes update``. Never raises; lazy-install failures
here must not block the rest of the update flow.

#### def `ensure_and_bind(feature: str, importer: Callable[[], dict[str, Any]], target_globals: dict, prompt: bool = False) -> bool`

Ensure a feature is installed, then rebind names into the caller's globals.

Combines :func:`ensure` with a post-install import step that rebinds
module-level names.  This eliminates the error-prone pattern of manually
listing every global that needs updating after lazy-install.

``importer`` is a zero-arg callable that returns a dict of
``{name: value}`` for all symbols the caller needs rebound.  It is called
only after :func:`ensure` succeeds (or if the packages are already
installed).

Returns True on success, False if deps couldn't be installed or imported.

Example usage in a platform adapter::

    def check_slack_requirements() -> bool:
        if SLACK_AVAILABLE:
            return True
        def _import():
            from slack_bolt.async_app import AsyncApp
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
            from slack_sdk.web.async_client import AsyncWebClient
            import aiohttp
            return {
                "AsyncApp": AsyncApp,
                "AsyncSocketModeHandler": AsyncSocketModeHandler,
                "AsyncWebClient": AsyncWebClient,
                "aiohttp": aiohttp,
                "SLACK_AVAILABLE": True,
            }
        return ensure_and_bind("platform.slack", _import, globals(), prompt=False)


## tools.managed_tool_gateway

### 模块文档

Generic managed-tool gateway helpers for Nous-hosted vendor passthroughs.

### class ManagedToolGatewayConfig

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `auth_json_path()`

Return the Hermes auth store path, respecting HERMES_HOME overrides.

#### def `peek_nous_access_token() -> Optional[str]`

Cheap probe for a Nous gateway token without triggering refresh.

Availability scans (`hermes tools`, banner/status paint, provider
`is_available()` checks) must stay off the synchronous OAuth refresh path.
This helper therefore only inspects the explicit env override and the
cached auth-store token, without checking expiry and without making any
network calls. Truthful refresh handling stays in request/session paths
that call :func:`read_nous_access_token`.

#### def `read_nous_access_token() -> Optional[str]`

Read a Nous Subscriber OAuth access token from auth store or env override.

#### def `get_tool_gateway_scheme() -> str`

Return configured shared gateway URL scheme.

**异常**: `ValueError`

#### def `build_vendor_gateway_url(vendor: str) -> str`

Return the gateway origin for a specific vendor.

#### def `resolve_managed_tool_gateway(vendor: str, gateway_builder: Optional[Callable[[str], str]] = None, token_reader: Optional[Callable[[], Optional[str]]] = None) -> Optional[ManagedToolGatewayConfig]`

Resolve shared managed-tool gateway config for a vendor.

#### def `is_managed_tool_gateway_ready(vendor: str, gateway_builder: Optional[Callable[[str], str]] = None, token_reader: Optional[Callable[[], Optional[str]]] = None) -> bool`

Return True when gateway URL and a likely-usable Nous token are present.

Defaults to :func:`peek_nous_access_token` so read-only availability scans
avoid synchronous OAuth refresh. Callers that are about to make a real
gateway request should use :func:`resolve_managed_tool_gateway` (which
still defaults to the refresh-aware :func:`read_nous_access_token`).


## tools.mcp_dashboard_oauth

### 模块文档

Dashboard-mediated callback bridge for MCP OAuth.

The MCP SDK remains responsible for discovery, DCR, PKCE, state validation and
token exchange. This module only moves the two human/browser callbacks from a
loopback listener into the already-authenticated dashboard session.

### class DashboardOAuthFlow

> 继承: `object` ｜ 方法数: 9（公开 9）

#### async def `publish_authorization_url(self, url: str) -> None`

**异常**: `ValueError`, `RuntimeError`

#### async def `wait_for_authorization_url(self, timeout: float = 30.0) -> str`

**异常**: `TimeoutError`, `RuntimeError`

#### def `deliver_callback(self, code: str | None, state: str | None, error: str | None) -> None`

**异常**: `ValueError`

#### async def `wait_for_callback(self, timeout: float = 300.0) -> tuple[str, str | None]`

**异常**: `TimeoutError`, `RuntimeError`

#### def `mark_approved(self) -> None`

**异常**: `RuntimeError`

#### def `mark_error(self, error: str) -> None`

#### def `snapshot(self) -> dict`

#### def `mark_worker_done(self) -> None`

#### property `worker_done(self) -> bool`


### 顶层函数

#### def `dashboard_oauth_flow(flow: DashboardOAuthFlow) -> Iterator[None]`

#### def `get_dashboard_oauth_flow() -> DashboardOAuthFlow | None`


## tools.mcp_oauth

### 模块文档

MCP OAuth 2.1 Client Support

Implements the browser-based OAuth 2.1 authorization code flow with PKCE
for MCP servers that require OAuth authentication instead of static bearer
tokens.

Uses the MCP Python SDK's ``OAuthClientProvider`` (an ``httpx.Auth`` subclass)
which handles discovery, dynamic client registration, PKCE, token exchange,
refresh, and step-up authorization automatically.

This module provides the glue:
    - ``HermesTokenStorage``: persists tokens/client-info to disk so they
      survive across process restarts.
    - Callback server: ephemeral localhost HTTP server to capture the OAuth
      redirect with the authorization code.
    - ``build_oauth_auth()``: entry point called by ``mcp_tool.py`` that wires
      everything together and returns the ``httpx.Auth`` object.

Configuration in config.yaml::

    mcp_servers:
      my_server:
        url: "https://mcp.example.com/mcp"
        auth: oauth
        oauth:                                  # all fields optional
          client_id: "pre-registered-id"        # skip dynamic registration
          client_secret: "secret"               # confidential clients only
          scope: "read write"                   # default: server-provided
          redirect_port: 0                      # 0 = auto-pick free port
          redirect_uri: "https://proxy/callback"  # default: loopback callback
          redirect_host: "localhost"            # loopback hostname (WAF-safe)
          client_name: "My Custom Client"       # default: "Hermes Agent"

### class OAuthNonInteractiveError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when OAuth requires browser interaction in a non-interactive env.


### class HermesTokenStorage

> 继承: `object` ｜ 方法数: 15（公开 11）

Persist OAuth tokens and client registration to JSON files.

File layout::

    HERMES_HOME/mcp-tokens/<server_name>.json         -- tokens
    HERMES_HOME/mcp-tokens/<server_name>.client.json   -- client info
    HERMES_HOME/mcp-tokens/<server_name>.meta.json     -- oauth server metadata

#### def `__init__(server_name: str, hermes_home: str | Path | None = None)`

#### async def `get_tokens(self) -> OAuthToken | None`

#### async def `set_tokens(self, tokens: OAuthToken) -> None`

#### async def `get_client_info(self) -> OAuthClientInformationFull | None`

#### async def `set_client_info(self, client_info: OAuthClientInformationFull) -> None`

#### def `save_oauth_metadata(self, metadata: OAuthMetadata) -> None`

#### def `load_oauth_metadata(self) -> OAuthMetadata | None`

#### def `remove(self) -> None`

Delete all stored OAuth state for this server.

#### def `snapshot(self) -> dict[str, bytes]`

Capture on-disk OAuth state so a failed re-auth can restore it.

Maps filename -> bytes for whichever of the three state files exist.
Feed back to ``restore()`` to undo an intervening ``remove()`` when a
re-authentication attempt fails, so a still-valid token isn't destroyed.

#### def `restore(self, snapshot: dict[str, bytes], only_if_absent: bool = False) -> None`

Revert to a snapshot without overwriting a concurrent successful write.

#### def `poison_client_registration(self) -> bool`

Discard a dead dynamically-registered client so it gets re-created.

Called when the IdP rejects our cached ``client_id`` with
``invalid_client`` on the token endpoint — proof the server-side
registration is gone (IdP redeploy / DB wipe / rebrand). Deleting
``client.json`` makes the MCP SDK's ``async_auth_flow`` take the
``if not client_info`` branch and re-run RFC 7591 dynamic client
registration on the next flow. The stale ``meta.json`` is dropped
too so discovery re-runs against a freshly fetched document.

Tokens are intentionally left in place — the subsequent
re-authorization overwrites them, and keeping them avoids losing a
still-valid refresh token if the re-registration never completes.

A single ``.bak`` copy of the client file is kept for recovery.
Returns True if a client file was present and removed.

#### def `has_cached_tokens(self) -> bool`

Return True if we have tokens on disk (may be expired).


### 顶层函数

#### def `force_interactive_oauth()`

Treat the current execution context as interactive despite no TTY.

For GUI-driven auth (dashboard/desktop REST endpoint): the user IS present
— just not on stdin. Opens the browser + localhost callback flow that the
TTY heuristic would otherwise refuse. Same ContextVar propagation story as
suppress_interactive_oauth() (#35927).

#### def `suppress_interactive_oauth()`

Disable stdin-based OAuth prompts for the current execution context.

Uses a ContextVar so the suppression propagates from a background-discovery
thread onto the coroutine scheduled (via run_coroutine_threadsafe) on the
dedicated MCP event-loop thread — where the OAuth callback actually runs
(#35927). A threading.local would not cross that thread boundary.

#### def `remove_oauth_tokens(server_name: str, hermes_home: str | Path | None = None) -> None`

Delete stored OAuth tokens and client info for a server.

#### def `build_oauth_auth(server_name: str, server_url: str, oauth_config: dict | None = None) -> OAuthClientProvider | None`

Build an ``httpx.Auth``-compatible OAuth handler for an MCP server.

Public API preserved for backwards compatibility. New code should use
:func:`tools.mcp_oauth_manager.get_manager` so OAuth state is shared
across config-time, runtime, and reconnect paths.

Args:
    server_name: Server key in mcp_servers config (used for storage).
    server_url: MCP server endpoint URL.
    oauth_config: Optional dict from the ``oauth:`` block in config.yaml.

Returns:
    An ``OAuthClientProvider`` instance, or None if the MCP SDK lacks
    OAuth support.

**异常**: `OAuthNonInteractiveError`


## tools.mcp_oauth_manager

### 模块文档

Central manager for per-server MCP OAuth state.

One instance shared across the process. Holds per-server OAuth provider
instances and coordinates:

- **Cross-process token reload** via mtime-based disk watch. When an external
  process (e.g. a user cron job) refreshes tokens on disk, the next auth flow
  picks them up without requiring a process restart.
- **401 deduplication** via in-flight futures. When N concurrent tool calls
  all hit 401 with the same access_token, only one recovery attempt fires;
  the rest await the same result.
- **Reconnect signalling** for long-lived MCP sessions. The manager itself
  does not drive reconnection — the `MCPServerTask` in `mcp_tool.py` does —
  but the manager is the single source of truth that decides when reconnect
  is warranted.

Replaces what used to be scattered across eight call sites in `mcp_oauth.py`,
`mcp_tool.py`, and `hermes_cli/mcp_config.py`. This module is the ONLY place
that instantiates the MCP SDK's `OAuthClientProvider` — all other code paths
go through `get_manager()`.

Design reference:

- Claude Code's ``invalidateOAuthCacheIfDiskChanged``
  (``claude-code/src/utils/auth.ts:1320``, CC-1096 / GH#24317). Identical
  external-refresh staleness bug class.
- Codex's ``refresh_oauth_if_needed`` / ``persist_if_needed``
  (``codex-rs/rmcp-client/src/rmcp_client.rs:805``). We lean on the MCP SDK's
  lazy refresh rather than calling refresh before every op, because one
  ``stat()`` per tool call is cheaper than an ``await`` + potential refresh
  round-trip, and the SDK's in-memory expiry path is already correct.

### class MCPOAuthManager

> 继承: `object` ｜ 方法数: 9（公开 6）

Single source of truth for per-server MCP OAuth state.

Thread-safe: the ``_entries`` dict is guarded by ``_entries_lock`` for
get-or-create semantics. Per-entry state is guarded by the entry's own
``asyncio.Lock`` (used from the MCP event loop thread).

#### def `__init__() -> None`

#### def `get_or_build_provider(self, server_name: str, server_url: str, oauth_config: Optional[dict]) -> Optional[Any]`

Return a cached OAuth provider for ``server_name`` or build one.

Idempotent: repeat calls with the same name return the same instance.
If ``server_url`` changes for a given name, the cached entry is
discarded and a fresh provider is built.

Returns None if the MCP SDK's OAuth support is unavailable.

#### def `remove(self, server_name: str, hermes_home: str | Path | None = None) -> _ProviderEntry | None`

Evict the provider from cache AND delete tokens from disk.

Called by ``hermes mcp remove <name>`` and (indirectly) by
``hermes mcp login <name>`` during forced re-auth.

#### def `restore_entry(self, server_name: str, entry: _ProviderEntry | None, hermes_home: str | Path | None = None) -> None`

Restore a provider entry removed for a failed reauthorization.

#### def `evict(self, server_name: str, hermes_home: str | Path | None = None) -> None`

Drop only the in-process provider, preserving persisted OAuth state.

#### async def `invalidate_if_disk_changed(self, server_name: str, hermes_home: str | Path | None = None) -> bool`

If the tokens file on disk has a newer mtime than last-seen, force
the MCP SDK provider to reload its in-memory state.

Returns True if the cache was invalidated (mtime differed). This is
the core fix for the external-refresh workflow: a cron job writes
fresh tokens to disk, and on the next tool call the running MCP
session picks them up without a restart.

#### async def `handle_401(self, server_name: str, failed_access_token: Optional[str] = None) -> bool`

Handle a 401 from a tool call, deduplicated across concurrent callers.

Returns:
    True  if a (possibly new) access token is now available — caller
          should trigger a reconnect and retry the operation.
    False if no recovery path exists — caller should surface a
          ``needs_reauth`` error to the model so it stops hallucinating
          manual refresh attempts.

Thundering-herd protection: if N concurrent tool calls hit 401 with
the same ``failed_access_token``, only one recovery attempt fires.
Others await the same future.


### 顶层函数

#### def `get_manager() -> MCPOAuthManager`

Return the process-wide :class:`MCPOAuthManager` singleton.

#### def `reset_manager_for_tests() -> None`

Test-only helper: drop the singleton so fixtures start clean.


## tools.mcp_stdio_watchdog

### 模块文档

Parent-death watchdog supervisor for stdio MCP subprocesses.

Problem this fixes (#TBD): a stdio MCP server (e.g. ``npx -y mcp-remote
<url>``) is spawned as a direct child of the Hermes process. Hermes's own
teardown path (``MCPServerTask.shutdown()`` / ``_kill_orphaned_mcp_children``
at final exit) reaps it cleanly on a *graceful* exit. But if the spawning
Hermes process dies hard — ``kill -9``, an OS-level crash, a force-quit of
the TUI/desktop app — that teardown code never runs, and the child (plus any
of its own descendants, e.g. mcp-remote's spawned ``node`` process) is
orphaned. macOS has no direct equivalent of Linux's
``prctl(PR_SET_PDEATHSIG)`` to make the kernel auto-kill a child when its
parent dies, so nothing reaps these until the next Hermes startup's opt-in
``_kill_orphaned_mcp_children()`` sweep — which only runs if something calls
it. Repeated ungraceful session restarts can pile up N orphaned processes,
all racing to hold the same upstream SSE session, producing errors like
"Invalid request parameters" / "Received request before initialization was
complete" on the *legitimate* new connection.

Fix: don't spawn the MCP server command directly. Spawn this supervisor
instead, which:
  1. execs the real command as its own child (own process group via
     ``start_new_session``, so it doesn't inherit the supervisor's
     controlling terminal weirdly and so we can killpg it cleanly);
  2. transparently passes stdin/stdout/stderr through — the MCP stdio
     protocol talks directly over those pipes, so the supervisor must be a
     no-op relay, not a bytes-in-the-middle proxy;
  3. runs a background thread that polls the direct POSIX parent identity:
     compare current ``getppid()`` against the parent PID recorded when the
     wrapper was created;
  4. the instant the original parent is gone, terminates the real child's
     process group (SIGTERM, grace period, then SIGKILL) and exits.

This is intentionally a thin, standard-library-only script so it starts fast
and can't itself become a resource leak.

Usage (see ``tools/mcp_tool.py::_run_stdio``)::

    python3 -m tools.mcp_stdio_watchdog \
        --ppid <original_parent_pid> -- <real_command> <arg1> <arg2> ...

### 顶层函数

#### def `main(argv: list[str] | None = None) -> int`


## tools.mcp_tool

### 模块文档

MCP (Model Context Protocol) Client Support

Connects to external MCP servers via stdio, HTTP/StreamableHTTP, or SSE
transport, discovers their tools, and registers them into the hermes-agent
tool registry so the agent can call them like any built-in tool.

Configuration is read from ~/.hermes/config.yaml under the ``mcp_servers`` key.
The ``mcp`` Python package is optional -- if not installed, this module is a
no-op and logs a debug message.

Example config::

    mcp_servers:
      filesystem:
        command: "npx"
        args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        env: {}
        timeout: 120         # per-tool-call timeout in seconds (default: 300)
        connect_timeout: 60  # initial connection timeout (default: 60)
        keepalive_interval: 10  # liveness ping cadence in seconds (default:
                                # 180). Set below the server's session TTL for
                                # servers that GC idle sessions quickly (e.g.
                                # Unreal Engine editor MCP, ~15s). Floored at 5s.
        idle_timeout_seconds: 3600      # optional stdio recycle after idle
        max_lifetime_seconds: 86400     # optional stdio recycle after age
        # The recycle settings may also live under lifecycle: {...}.
        # Use 0 to disable either recycle limit.
      github:
        command: "npx"
        args: ["-y", "@modelcontextprotocol/server-github"]
        env:
          GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_..."
        supports_parallel_tool_calls: true  # tools from this server may run concurrently
      remote_api:
        url: "https://my-mcp-server.example.com/mcp"
        headers:
          Authorization: "Bearer sk-..."
        timeout: 180
        skip_preflight: true  # bypass the content-type probe for a valid
                              # Streamable HTTP endpoint that answers HEAD/GET
                              # with a non-MCP content type but serves real
                              # MCP over POST. Default: false.
      searxng:
        url: "http://localhost:8000/sse"
        transport: sse       # use SSE transport instead of Streamable HTTP
        timeout: 180
        connect_timeout: 10
        command: "npx"
        args: ["-y", "analysis-server"]
        sampling:                    # server-initiated LLM requests
          enabled: true              # default: true
          model: "gemini-3-flash"    # override model (optional)
          max_tokens_cap: 4096       # max tokens per request
          timeout: 30                # LLM call timeout (seconds)
          max_rpm: 10                # max requests per minute
          allowed_models: []         # model whitelist (empty = all)
          max_tool_rounds: 5         # tool loop limit (0 = disable)
          log_level: "info"          # audit verbosity

Features:
    - Stdio transport (command + args) and HTTP/StreamableHTTP transport (url)
    - SSE transport (transport: sse) for MCP servers using the SSE protocol
    - Automatic reconnection with exponential backoff (up to 5 retries)
    - Environment variable filtering for stdio subprocesses (security)
    - Credential stripping in error messages returned to the LLM
    - Configurable per-server timeouts for tool calls and connections
    - Thread-safe architecture with dedicated background event loop
    - Sampling support: MCP servers can request LLM completions via
      sampling/createMessage (text and tool-use responses)
    - Parallel tool call opt-in: per-server ``supports_parallel_tool_calls``
      flag allows concurrent execution of tools from the same server

Architecture:
    A dedicated background event loop (_mcp_loop) runs in a daemon thread.
    Each MCP server runs as a long-lived asyncio Task on this loop, keeping
    its transport context alive. Tool call coroutines are scheduled onto the
    loop via ``run_coroutine_threadsafe()``.

    On shutdown, each server Task is signalled to exit its ``async with``
    block, ensuring the anyio cancel-scope cleanup happens in the *same*
    Task that opened the connection (required by anyio).

Thread safety:
    _servers and _mcp_loop/_mcp_thread are accessed from both the MCP
    background thread and caller threads.  All mutations are protected by
    _lock so the code is safe regardless of GIL presence (e.g. Python 3.13+
    free-threading).

### class InvalidMcpUrlError

> 继承: `ValueError` ｜ 方法数: 0（公开 0）

Raised when a remote MCP server's ``url`` cannot be parsed as http(s)://.

Validated once at startup so we fail fast with a clear message instead of
burning through the reconnect-backoff loop on every attempt.  (Ported from
anomalyco/opencode#25019.)


### class NonMcpEndpointError

> 继承: `ConnectionError` ｜ 方法数: 0（公开 0）

Raised when an HTTP MCP URL serves a non-MCP response.

A genuine MCP Streamable-HTTP endpoint answers with ``application/json``
or ``text/event-stream``.  Anything else on a 2xx response (typically
``text/html`` from a web-app root) means the configured ``url`` points at
the wrong place.  This is non-retryable: every attempt returns the same
page, so the reconnect-backoff loop is skipped and the server is reported
failed immediately with an actionable message.

Subclasses :class:`ConnectionError` so callers that only catch the broad
class still treat it as a connection problem.


### class SamplingHandler

> 继承: `object` ｜ 方法数: 10（公开 1）

Handles sampling/createMessage requests for a single MCP server.

Each MCPServerTask that has sampling enabled creates one SamplingHandler.
The handler is callable and passed directly to ``ClientSession`` as
the ``sampling_callback``.  All state (rate-limit timestamps, metrics,
tool-loop counters) lives on the instance -- no module-level globals.

The callback is async and runs on the MCP background event loop.  The
sync LLM call is offloaded to a thread via ``asyncio.to_thread()`` so
it doesn't block the event loop.

#### def `__init__(server_name: str, config: dict)`

#### def `session_kwargs(self) -> dict`

Return kwargs to pass to ClientSession for sampling support.


### class ElicitationHandler

> 继承: `object` ｜ 方法数: 3（公开 1）

Handles ``elicitation/create`` requests for a single MCP server.

Each ``MCPServerTask`` that has elicitation enabled creates one handler.
The handler is callable and passed directly to ``ClientSession`` as the
``elicitation_callback`` (added in mcp Python SDK 1.11.0).

Elicitation lets a server ask the client to collect structured input from
the user mid-tool-call (e.g. payment authorization, OAuth confirmation).
Form-mode elicitations are routed through Hermes' existing approval
system (``tools.approval.prompt_dangerous_approval``), which surfaces
the prompt on whichever surface the active session uses -- CLI, TUI,
Telegram, Slack, etc. URL-mode elicitations are declined as unsupported.

Failure modes are fail-closed: any timeout, exception, or unexpected
state returns ``decline``/``cancel`` rather than silently accepting.
The server treats this as the user not approving.

#### def `__init__(server_name: str, config: dict, owner: Optional['MCPServerTask'] = None)`

#### def `session_kwargs(self) -> dict`

Return kwargs to pass to ClientSession for elicitation support.


### class MCPServerTask

> 继承: `object` ｜ 方法数: 27（公开 4）

Manages a single MCP server connection in a dedicated asyncio Task.

The entire connection lifecycle (connect, discover, serve, disconnect)
runs inside one asyncio Task so that anyio cancel-scopes created by
the transport client are entered and exited in the same Task context.

Supports both stdio and HTTP/StreamableHTTP transports.

#### def `__init__(name: str)`

#### def `mark_tool_call(self) -> None`

Record that a user-visible MCP operation is starting.

#### async def `run(self, config: dict)`

Long-lived coroutine: connect, discover tools, wait, disconnect.

Includes automatic reconnection with exponential backoff if the
connection drops unexpectedly (unless shutdown was requested).

#### async def `start(self, config: dict)`

Create the background Task and wait until ready (or failed).

**异常**: `self._error`

#### async def `shutdown(self)`

Signal the Task to exit and wait for clean resource teardown.


### 顶层函数

#### def `reconnect_mcp_server(server_name: str) -> bool`

Ask a currently-live MCP server to rebuild after external re-auth.

#### def `sanitize_mcp_name_component(value: str) -> str`

Return an MCP name component safe for tool and prefix generation.

Preserves Hermes's historical behavior of converting hyphens to
underscores, and also replaces any other character outside
``[A-Za-z0-9_]`` with ``_`` so generated tool names are compatible with
provider validation rules.

#### def `mcp_prefixed_tool_name(server_name: str, tool_name: str) -> str`

Build the registry/wire name for an MCP tool.

Produces ``mcp__<sanitizedServer>__<sanitizedTool>``.

#### def `register_mcp_servers(servers: Dict[str, dict]) -> List[str]`

Connect to explicit MCP servers and register their tools.

Idempotent for already-connected server names. Servers with
``enabled: false`` are skipped without disconnecting existing sessions.

Args:
    servers: Mapping of ``{server_name: server_config}``.

Returns:
    List of all currently registered MCP tool names.

#### def `discover_mcp_tools() -> List[str]`

Entry point: load config, connect to MCP servers, register tools.

Called from ``model_tools`` after ``discover_builtin_tools()``. Safe to call even when
the ``mcp`` package is not installed (returns empty list).

Idempotent for already-connected servers. If some servers failed on a
previous call, only the missing ones are retried.

Returns:
    List of all registered MCP tool names.

#### def `is_mcp_tool_parallel_safe(tool_name: str) -> bool`

Check if an MCP tool belongs to a server that supports parallel tool calls.

MCP tool names follow the pattern ``mcp__{server}__{tool}``, but that
string shape is ambiguous when server names contain underscores. Use the
exact server provenance captured at registration time rather than prefix
matching, then check whether that server's config includes
``supports_parallel_tool_calls: true``.

Returns False for non-MCP tools or tools from servers without the flag.

#### def `get_mcp_status() -> List[dict]`

Return status of all configured MCP servers for banner display.

Returns a list of dicts with keys: name, transport, tools, connected,
disabled, and status. Includes connected servers, disabled servers,
in-flight connection attempts, recorded failures, and servers that are
configured but have not been started in this process yet.

#### def `probe_mcp_server_tools() -> Dict[str, List[tuple]]`

Temporarily connect to configured MCP servers and list their tools.

Designed for ``hermes tools`` interactive configuration — connects to each
enabled server, grabs tool names and descriptions, then disconnects.
Does NOT register tools in the Hermes registry.

Returns:
    Dict mapping server name to list of (tool_name, description) tuples.
    Servers that fail to connect are omitted from the result.

#### def `has_registered_mcp_tools() -> bool`

True if any MCP server has actually registered tools into the registry.

Cheap — checks the global MCP-tool→server name map under ``_lock``, no
registry walk.  Used by the per-turn refresh hook so a session with no MCP
tools (the common case, and also a connected-but-zero-tool/prompt-only
server) skips the ``get_tool_definitions`` rebuild entirely.  Checks
registered TOOLS, not connected servers, so a server that registers no tools
doesn't keep the hook firing every turn.

#### def `refresh_agent_mcp_tools(agent, enabled_override = None, disabled_override = None, quiet_mode: bool = True) -> set`

Re-derive an already-built agent's tool snapshot from the live registry.

The agent snapshots ``agent.tools`` once at build time and never re-reads
the registry (see ``run_agent`` / ``agent_init``).  When MCP servers connect
*after* that snapshot — a slow HTTP/OAuth server that misses the bounded
startup wait, or a ``/reload-mcp`` — their tools are invisible until the
snapshot is rebuilt.  This is the single shared rebuild used by every such
caller (the TUI ``reload.mcp`` RPC, the gateway reload, the late-binding
refresh thread, and the per-turn between-turns refresh) so they can't drift
apart again.

The rebuild respects the agent's own ``enabled_toolsets`` /
``disabled_toolsets`` (the same filtering it was built with) and diffs by
tool **name** (not count — a count compare misses an equal-size add/remove
swap).

Crucially it is **additive-preserving**: ``get_tool_definitions`` returns
only the registry-derived tools, but ``agent_init`` appends two further
families directly onto ``agent.tools`` *after* that — external
memory-provider tools (mem0/honcho/…) and context-engine tools
(``lcm_*``).  A naive ``agent.tools = get_tool_definitions(...)`` would
silently DELETE those.  So after rebuilding the registry set we re-run the
same post-build injectors ``agent_init`` used, reconstructing the full
surface.  The new ``(tools, valid_tool_names)`` pair is published together
under ``_agent_tools_lock`` so a concurrent reader never sees a
cross-attribute half-swap.

Returns the set of newly-added tool names (empty when nothing changed), so
callers can decide whether to notify the user / re-emit session info.  The
caller owns the prompt-cache contract: this helper does NOT check turn state,
because each caller has a different policy (``/reload-mcp`` rebuilds after
explicit user consent; the late-binding and between-turns paths only rebuild
at a turn boundary, before that turn's ``tools=`` prefix is assembled).

#### def `shutdown_mcp_servers()`

Close all MCP server connections and stop the background loop.

Each server Task is signalled to exit its ``async with`` block so that
the anyio cancel-scope cleanup happens in the same Task that opened it.
All servers are shut down in parallel via ``asyncio.gather``.


## tools.memory_tool

### 模块文档

Memory Tool Module - Persistent Curated Memory

Provides bounded, file-backed memory that persists across sessions. Two stores:
  - MEMORY.md: agent's personal notes and observations (environment facts, project
    conventions, tool quirks, things learned)
  - USER.md: what the agent knows about the user (preferences, communication style,
    expectations, workflow habits)

Both are injected into the system prompt as a frozen snapshot at session start.
Mid-session writes update files on disk immediately (durable) but do NOT change
the system prompt -- this preserves the prefix cache for the entire session.
The snapshot refreshes on the next session start.

Entry delimiter: § (section sign). Entries can be multiline.
Character limits (not tokens) because char counts are model-independent.

Design:
- Single `memory` tool with action parameter: add, replace, remove
- replace/remove use short unique substring matching (not full text or IDs)
- Behavioral guidance lives in the tool schema description
- Frozen snapshot pattern: system prompt is stable, tool responses show live state

### class MemoryStore

> 继承: `object` ｜ 方法数: 25（公开 8）

Bounded curated memory with file persistence. One instance per AIAgent.

Maintains two parallel states:
  - _system_prompt_snapshot: frozen at load time, used for system prompt injection.
    Never mutated mid-session. Keeps prefix cache stable.
  - memory_entries / user_entries: live state, mutated by tool calls, persisted to disk.
    Tool responses always reflect this live state.

#### def `__init__(memory_char_limit: int = 2200, user_char_limit: int = 1375)`

#### def `reset_consolidation_failures(self) -> None`

Reset the per-turn consolidation-failure counter (call at turn start).

#### def `load_from_disk(self)`

Load entries from MEMORY.md and USER.md, capture system prompt snapshot.

The frozen snapshot is what enters the system prompt. We scan each
entry for injection/promptware patterns at snapshot-build time —
ANY hit replaces the entry text in the snapshot with a placeholder
like ``[BLOCKED: …]``, so a poisoned-on-disk memory file (supply
chain, compromised tool, sister-session write) cannot inject into
the system prompt.

The live ``memory_entries`` / ``user_entries`` lists keep the
original text so the user can still SEE poisoned entries via
see poisoned entries by inspecting the source files directly, and remove them — silently dropping them would hide the attack from the user.

Scanning is deterministic from disk bytes, so the snapshot remains
stable for the entire session (prefix-cache invariant holds).

#### def `save_to_disk(self, target: str)`

Persist entries to the appropriate file. Called after every mutation.

#### def `add(self, target: str, content: str) -> Dict[str, Any]`

Append a new entry. Returns error if it would exceed the char limit.

#### def `replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]`

Find entry containing old_text substring, replace it with new_content.

#### def `remove(self, target: str, old_text: str) -> Dict[str, Any]`

Remove the entry containing old_text substring.

#### def `apply_batch(self, target: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]`

Apply a sequence of add/replace/remove ops to one target atomically.

All operations are validated and applied against the FINAL budget --
intermediate overflow is irrelevant. This lets the model free space
(remove/replace) and add new entries in a SINGLE tool call instead of
the multi-turn consolidate-then-retry dance that re-sends the whole
conversation context several times.

Semantics: all-or-nothing. If any op is malformed, doesn't match, or
the net result would exceed the char limit, NOTHING is written and an
error is returned describing the first failure plus the live state.

#### def `format_for_system_prompt(self, target: str) -> Optional[str]`

Return the frozen snapshot for system prompt injection.

This returns the state captured at load_from_disk() time, NOT the live
state. Mid-session writes do not affect this. This keeps the system
prompt stable across all turns, preserving the prefix cache.

Returns None if the snapshot is empty (no entries at load time).


### 顶层函数

#### def `get_memory_dir() -> Path`

Return the profile-scoped memories directory.

#### def `load_on_disk_store() -> MemoryStore`

Build a fresh on-disk :class:`MemoryStore`, honoring configured char limits.

Use this from any context that has no live agent (the messaging gateway, the
Desktop GUI, the bare CLI ``/memory`` handler) but still needs to read or
apply approved memory writes. Mirrors how the live agent constructs its store
in ``agent/agent_init.py`` — including the user's ``memory.memory_char_limit``
/ ``memory.user_char_limit`` overrides — so an approval applied without a live
agent enforces the SAME caps as one applied with one.

Falls back to the built-in defaults if config can't be loaded, so this can
never raise on a missing/unreadable config.

#### def `memory_tool(action: str = None, target: str = 'memory', content: str = None, old_text: str = None, operations: Optional[List[Dict[str, Any]]] = None, store: Optional[MemoryStore] = None) -> str`

Single entry point for the memory tool. Dispatches to MemoryStore methods.

Two shapes:
  - Single op: action + (content / old_text).
  - Batch:     operations=[{action, content?, old_text?}, ...] applied
               atomically against the final char budget in ONE call.

Returns JSON string with results.

#### def `check_memory_requirements() -> bool`

Memory tool has no external requirements -- always available.

#### def `apply_memory_pending(payload: Dict[str, Any], store: MemoryStore) -> Dict[str, Any]`

Replay a staged memory write directly against the store, bypassing the
write gate. Called by the /memory approve handler.

Returns the store's result dict.


## tools.microsoft_graph_auth

### 模块文档

Microsoft Graph app-only authentication helpers.

### class MicrosoftGraphAuthError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Base class for Microsoft Graph auth failures.


### class MicrosoftGraphConfigError

> 继承: `MicrosoftGraphAuthError` ｜ 方法数: 0（公开 0）

Raised when Graph credentials are missing or invalid.


### class MicrosoftGraphTokenError

> 继承: `MicrosoftGraphAuthError` ｜ 方法数: 0（公开 0）

Raised when token acquisition fails.


### class GraphCredentials

> 继承: `object` ｜ 方法数: 2（公开 2）

Normalized Microsoft Graph app-only credentials.

#### property `token_url(self) -> str`

#### classmethod `from_env(cls, environ: dict[str, str] | None = None, required: bool = True) -> GraphCredentials | None`

**异常**: `MicrosoftGraphConfigError`


### class CachedAccessToken

> 继承: `object` ｜ 方法数: 2（公开 2）

Cached app-only Graph access token.

#### def `is_expired(self, skew_seconds: int = DEFAULT_TOKEN_SKEW_SECONDS) -> bool`

#### property `expires_in_seconds(self) -> int`


### class MicrosoftGraphTokenProvider

> 继承: `object` ｜ 方法数: 6（公开 4）

Acquire and cache Microsoft Graph app-only access tokens.

#### def `__init__(credentials: GraphCredentials, timeout: float = 20.0, skew_seconds: int = DEFAULT_TOKEN_SKEW_SECONDS, transport: httpx.AsyncBaseTransport | None = None) -> None`

#### classmethod `from_env(cls, environ: dict[str, str] | None = None, **kwargs: Any) -> MicrosoftGraphTokenProvider`

#### def `clear_cache(self) -> None`

#### def `inspect_token_health(self) -> dict[str, Any]`

#### async def `get_access_token(self, force_refresh: bool = False) -> str`


## tools.microsoft_graph_client

### 模块文档

Reusable Microsoft Graph REST client helpers.

### class MicrosoftGraphClientError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Base class for Graph client failures.


### class MicrosoftGraphAPIError

> 继承: `MicrosoftGraphClientError` ｜ 方法数: 1（公开 0）

Raised when a Graph API request fails.

#### def `__init__(status_code: int, method: str, url: str, message: str, retry_after_seconds: float | None = None, payload: Any = None) -> None`


### class MicrosoftGraphClient

> 继承: `object` ｜ 方法数: 16（公开 8）

Minimal async Microsoft Graph client with retries and pagination.

#### def `__init__(token_provider: MicrosoftGraphTokenProvider, base_url: str = DEFAULT_GRAPH_BASE_URL, timeout: float = 60.0, max_retries: int = 3, transport: httpx.AsyncBaseTransport | None = None, sleep: Callable[[float], Awaitable[None]] | None = None, user_agent: str = 'Hermes-Agent/graph-client') -> None`

#### classmethod `from_env(cls, **kwargs: Any) -> MicrosoftGraphClient`

#### async def `get_json(self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any`

#### async def `post_json(self, path: str, json_body: Any | None = None, headers: dict[str, str] | None = None) -> Any`

#### async def `patch_json(self, path: str, json_body: Any | None = None, headers: dict[str, str] | None = None) -> Any`

#### async def `delete(self, path: str, headers: dict[str, str] | None = None) -> dict[str, Any]`

#### async def `iterate_pages(self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> AsyncIterator[dict[str, Any]]`

**异常**: `MicrosoftGraphClientError`

#### async def `collect_paginated(self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> list[Any]`

#### async def `download_to_file(self, path: str, destination: str | Path, headers: dict[str, str] | None = None, chunk_size: int = 65536) -> dict[str, Any]`

Download a Graph resource to disk, streaming the response body.

The body is written chunk-by-chunk via ``response.aiter_bytes`` with
the ``httpx.AsyncClient`` kept open for the duration of the iteration,
so recordings and other large artifacts do not need to fit in memory.

**异常**: `MicrosoftGraphClientError`, `api_error`


## tools.neutts_synth

### 模块文档

Standalone NeuTTS synthesis helper.

Called by tts_tool.py via subprocess to keep the TTS model (~500MB)
in a separate process that exits after synthesis — no lingering memory.

Usage:
    python -m tools.neutts_synth --text "Hello" --out output.wav         --ref-audio samples/jo.wav --ref-text samples/jo.txt

Requires: python -m pip install -U neutts[all]
System:   apt install espeak-ng  (or brew install espeak-ng)

### 顶层函数

#### def `main()`


## tools.openrouter_client

### 模块文档

Shared OpenRouter API client for Hermes tools.

Provides a single lazy-initialized AsyncOpenAI client that all tool modules
can share.  Routes through the centralized provider router in
agent/auxiliary_client.py so auth, headers, and API format are handled
consistently.

### 顶层函数

#### def `get_async_client()`

Return a shared async OpenAI-compatible client for OpenRouter.

The client is created lazily on first call and reused thereafter.
Uses the centralized provider router for auth and client construction.
Raises ValueError if OPENROUTER_API_KEY is not set.

**异常**: `ValueError`

#### def `check_api_key() -> bool`

Check whether the OpenRouter API key is present.


## tools.osv_check

### 模块文档

OSV malware check for MCP extension packages.

Before launching an MCP server via npx/uvx, queries the OSV (Open Source
Vulnerabilities) API to check if the package has any known malware advisories
(MAL-* IDs).  Regular CVEs are ignored — only confirmed malware is blocked.

The API is free, public, and maintained by Google.  Typical latency is ~300ms.
Fail-open: network errors allow the package to proceed.

Inspired by Block/goose's extension malware check.

### 顶层函数

#### def `check_package_for_malware(command: str, args: list) -> Optional[str]`

Check if an MCP server package has known malware advisories.

Inspects the *command* (e.g. ``npx``, ``uvx``) and *args* to infer the
package name and ecosystem.  Queries the OSV API for MAL-* advisories.

Returns:
    An error message string if malware is found, or None if clean/unknown.
    Returns None (allow) on network errors or unrecognized commands.


## tools.patch_parser

### 模块文档

V4A Patch Format Parser

Parses the V4A patch format used by codex, cline, and other coding agents.

V4A Format:
    *** Begin Patch
    *** Update File: path/to/file.py
    @@ optional context hint @@
     context line (space prefix)
    -removed line (minus prefix)
    +added line (plus prefix)
    *** Add File: path/to/new.py
    +new file content
    +line 2
    *** Delete File: path/to/old.py
    *** Move File: old/path.py -> new/path.py
    *** End Patch

Usage:
    from tools.patch_parser import parse_v4a_patch, apply_v4a_operations
    
    operations, error = parse_v4a_patch(patch_content)
    if error:
        print(f"Parse error: {error}")
    else:
        result = apply_v4a_operations(operations, file_ops)

### class OperationType

> 继承: `Enum` ｜ 方法数: 0（公开 0）


### class HunkLine

> 继承: `object` ｜ 方法数: 0（公开 0）

A single line in a patch hunk.


### class Hunk

> 继承: `object` ｜ 方法数: 0（公开 0）

A group of changes within a file.


### class PatchOperation

> 继承: `object` ｜ 方法数: 0（公开 0）

A single operation in a V4A patch.


### 顶层函数

#### def `parse_v4a_patch(patch_content: str) -> Tuple[List[PatchOperation], Optional[str]]`

Parse a V4A format patch.

Args:
    patch_content: The patch text in V4A format

Returns:
    Tuple of (operations, error_message)
    - If successful: (list_of_operations, None)
    - If failed: ([], error_description)

#### def `apply_v4a_operations(operations: List[PatchOperation], file_ops: Any) -> PatchResult`

Apply V4A patch operations using a file operations interface.

Uses a two-phase validate-then-apply approach:
- Phase 1: validate all operations against current file contents without
  writing anything. If any validation error is found, return immediately
  with no filesystem changes.
- Phase 2: apply all operations. A failure here (e.g. a race between
  validation and apply) is reported with a note to run ``git diff``.

Args:
    operations: List of PatchOperation from parse_v4a_patch
    file_ops: Object with read_file_raw, write_file methods

Returns:
    PatchResult with results of all operations


## tools.path_security

### 模块文档

Shared path validation helpers for tool implementations.

Extracts the ``resolve() + relative_to()`` and ``..`` traversal check
patterns previously duplicated across skill_manager_tool, skills_tool,
skills_hub, cronjob_tools, and credential_files.

### 顶层函数

#### def `validate_within_dir(path: Path, root: Path) -> Optional[str]`

Ensure *path* resolves to a location within *root*.

Returns an error message string if validation fails, or ``None`` if the
path is safe.  Uses ``Path.resolve()`` to follow symlinks and normalize
``..`` components.

Usage::

    error = validate_within_dir(user_path, allowed_root)
    if error:
        return json.dumps({"error": error})

#### def `has_traversal_component(path_str: str) -> bool`

Return True if *path_str* contains ``..`` traversal components.

Quick check for obvious traversal attempts before doing full resolution.


## tools.process_registry

### 模块文档

Process Registry -- In-memory registry for managed background processes.

Tracks processes spawned via terminal(background=true), providing:
  - Output buffering (rolling 200KB window)
  - Status polling and log retrieval
  - Blocking wait with interrupt support
  - Process killing
  - Crash recovery via JSON checkpoint file
  - Session-scoped tracking for gateway reset protection

Background processes execute THROUGH the environment interface -- nothing
runs on the host machine unless TERMINAL_ENV=local. For Docker, Singularity,
Modal, Daytona, and SSH backends, the command runs inside the sandbox.

Usage:
    from tools.process_registry import process_registry

    # Spawn a background process (called from terminal_tool)
    session = process_registry.spawn(env, "pytest -v", task_id="task_123")

    # Poll for status
    result = process_registry.poll(session.id)

    # Block until done
    result = process_registry.wait(session.id, timeout=300)

    # Kill it
    process_registry.kill(session.id)

### class ProcessSession

> 继承: `object` ｜ 方法数: 0（公开 0）

A tracked background process with output buffering.


### class ProcessRegistry

> 继承: `object` ｜ 方法数: 42（公开 21）

In-memory registry of running and finished background processes.

Thread-safe. Accessed from:
  - Executor threads (terminal_tool, process tool handlers)
  - Gateway asyncio loop (watcher tasks, session reset checks)
  - Cleanup thread (sandbox reaping coordination)

#### def `__init__()`

#### def `spawn_local(self, command: str, cwd: str = None, task_id: str = '', session_key: str = '', env_vars: dict = None, use_pty: bool = False) -> ProcessSession`

Spawn a background process locally.

Only for TERMINAL_ENV=local. Other backends use spawn_via_env().

Args:
    use_pty: If True, use a pseudo-terminal via ptyprocess for interactive
             CLI tools (Codex, Claude Code, Python REPL). Falls back to
             subprocess.Popen if ptyprocess is not installed.

#### def `spawn_via_env(self, env: Any, command: str, cwd: str = None, task_id: str = '', session_key: str = '', timeout: int = 10) -> ProcessSession`

Spawn a background process through a non-local environment backend.

For Docker/Singularity/Modal/Daytona/SSH: runs the command inside the sandbox
using the environment's execute() interface. We wrap the command to
capture the in-sandbox PID and redirect output to a log file inside
the sandbox, then poll the log via subsequent execute() calls.

This is less capable than local spawn (no live stdout pipe, no stdin),
but it ensures the command runs in the correct sandbox context.

#### def `is_completion_consumed(self, session_id: str) -> bool`

Check if a completion notification was already consumed via wait/log.

#### def `is_session_waiting(self, session_id: str) -> bool`

Whether a goal loop parked on this session should still be parked.

Used by the goal-loop wait barrier (``hermes_cli.goals``) to support
waiting on a process's OWN trigger, not just its exit. A session is
"still waiting" when:
  - it is still running, AND
  - if it has ``watch_patterns``, none has matched yet (so a
    long-lived watcher that fires a trigger mid-run — and may never
    exit — unblocks the moment its pattern hits, not on exit).

Returns False (don't wait) when the session has exited, its watch
pattern has already fired, or the session is unknown — so a stale or
already-triggered barrier can never wedge the loop.

#### def `drain_notifications(self, session_key: str = '', owns_event = None, skip_poll_observed: bool = True) -> list[tuple[dict, str]]`

Pop all pending notification events and return formatted pairs.

Returns a list of (raw_event, formatted_text) tuples.
Skips completion events the agent already consumed via wait/log or
observed inline via poll() (see ``_drain_should_skip``). Gateway/TUI
callers pass ``skip_poll_observed=False`` because read-only polling must
not suppress autonomous delivery there.

When a routing filter is supplied, addressed notifications must not be
drained into the wrong session. Async-delegation events always require
conversation payload; ordinary notifications require routing when they
carry ``session_key`` or ``origin_ui_session_id`` metadata. Two filter
modes are supported, strongest first:

- ``owns_event(evt) -> bool``: positive-proof ownership callback.
  When provided, a routed event is consumed ONLY if the callback
  returns True; everything else is re-queued for its owner.
  The TUI passes its compression-chain-aware ownership check here so
  a post-compression session still claims its own pre-compression
  dispatches.
- ``session_key``: plain key equality (CLI and other single-session
  callers). Non-matching addressed events are re-queued.

With neither set, all events are consumed (legacy single-session
behavior, backward compatible). Ownerless ordinary notifications also
retain that legacy behavior even when a filter is provided. When a
filter is provided, ownerless async-delegation events remain
fail-closed and require positive proof.

#### def `get(self, session_id: str) -> Optional[ProcessSession]`

Get a session by ID (running or finished).

#### def `poll(self, session_id: str) -> dict`

Check status and get new output for a background process.

#### def `read_log(self, session_id: str, offset: int = 0, limit: int = 200) -> dict`

Read the full output log with optional pagination by lines.

#### def `wait(self, session_id: str, timeout: int = None) -> dict`

Block until a process exits, timeout, or interrupt.

Args:
    session_id: The process to wait for.
    timeout: Max seconds to block. Falls back to TERMINAL_TIMEOUT config.

Returns:
    dict with status ("exited", "timeout", "interrupted", "not_found")
    and output snapshot.

#### def `kill_process(self, session_id: str, source: str = 'process.kill', consume_output: bool = True) -> dict`

Kill a background process and return its output snapshot.

``consume_output`` is true for explicit tool/RPC kills because their
caller observes the returned output. Bulk cleanup passes false: it
discards each result and therefore must not suppress an autonomous
output-bearing completion notification.

#### def `write_stdin(self, session_id: str, data: str) -> dict`

Send raw data to a running process's stdin (no newline appended).

#### def `submit_stdin(self, session_id: str, data: str = '') -> dict`

Send data + newline to a running process's stdin (like pressing Enter).

#### def `request_close_terminal(self, session_id: str) -> dict`

Ask the desktop GUI to close the read-only terminal tab mirroring this
background process.

This does NOT kill the process — it only drops the view. Output keeps
streaming into the (capped) buffer and the user can reopen the tab from
the status stack. Desktop-only: returns an error if no UI close sink is
wired (e.g. CLI / messaging).

#### def `close_stdin(self, session_id: str) -> dict`

Close a running process's stdin / send EOF without killing the process.

#### def `count_running(self) -> int`

Return the count of currently-running background processes.

Cheap O(1) read of the running dict, suitable for status-bar polling
on every render tick. CPython dict ``len()`` is atomic; callers do not
need to hold ``self._lock``. Reflects ``_running`` only: sessions are
moved to ``_finished`` when their subprocess exits.

#### def `list_sessions(self, task_id: str = None, session_key: str = None) -> list`

List all running and recently-finished processes.

When ``task_id`` is given, processes for that task are included. When
``session_key`` is also given, session-scoped background processes
(``background: true``) registered under that gateway session are
surfaced too, even if they belong to a different task — so the agent
can discover a forgotten preview server that is blocking session
reset (#29177). Such cross-task entries are flagged with
``"session_scoped": true``.

#### def `has_active_processes(self, task_id: str) -> bool`

Check if there are active (running) processes for a task_id.

#### def `has_active_for_session(self, session_key: str, max_active_age: Optional[float] = None) -> bool`

Check if there are active processes for a gateway session key.

When *max_active_age* is set (seconds), processes that started more
than that many seconds ago are **ignored** — they are still running
but are considered stale and must not block session idle / daily
reset.  This prevents a forgotten ``http.server`` (or any long-lived
preview process) from permanently freezing the session lifecycle.

Args:
    session_key: Gateway session key to check.
    max_active_age: If set, ignore processes older than this many
        seconds.  ``None`` retains the legacy behaviour (any running
        process blocks).

#### def `has_any_active(self) -> bool`

Whether ANY background process is still running (across all sessions).

Used by scale-to-zero idle detection (gateway/scale_to_zero): a gateway
with a live background process (terminal background=true) is NOT idle and
must not be suspended, or the process is lost. Refreshes detached
sessions first so a finished-but-unreaped process reads as inactive.

#### def `kill_all(self, task_id: str = None) -> int`

Kill all running processes, optionally filtered by task_id. Returns count killed.

#### def `recover_from_checkpoint(self) -> int`

On gateway startup, probe PIDs from checkpoint file.

Returns the number of processes recovered as detached.


### 顶层函数

#### def `format_uptime_short(seconds: int) -> str`

#### def `format_process_notification(evt: dict) -> str | None`

Format a process notification event into a [IMPORTANT: ...] message.

Handles completion events (notify_on_complete), watch pattern matches,
and watch disabled events from the unified completion_queue.


## tools.project_tools

### 模块文档

Project tools — the agent's INTENTIONAL handle on first-class Projects.

Projects (per-profile ``projects.db``) are the named workspaces the desktop
sidebar groups sessions into. Creating / switching a project is a deliberate act
expressed as explicit tools — never a side effect of a terminal ``cd``.

Exposed only on GUI sessions: the tools live in the `project` toolset (kept off
``_HERMES_CORE_TOOLS``) which the desktop/TUI gateway folds into its resolved
toolsets, so no CLI/messaging/cron schema carries them. The GUI also wires
``set_project_workspace_callback`` so a create/switch re-anchors the live
session's cwd and the sidebar follows the move; the DB write is the durable part.

### 顶层函数

#### def `set_project_workspace_callback(fn: Optional[Callable[[str, str, str], None]]) -> None`

#### def `project_list(task_id: Optional[str] = None) -> str`

#### def `project_create(name: str, path: Optional[str] = None, task_id: Optional[str] = None) -> str`

#### def `project_switch(project: str, task_id: Optional[str] = None) -> str`


## tools.read_extract

### 模块文档

Stdlib document-to-text extraction for ``read_file``.

Supports Jupyter notebooks, DOCX, and XLSX without adding hard dependencies.
Malformed documents raise :class:`ExtractionError`; callers can then fall back to
normal text/binary handling.

### class ExtractionError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Raised when a supported-looking document cannot be rendered as text.


### 顶层函数

#### def `is_extractable_document(path: str) -> bool`

#### def `extract_document_text(path: str) -> str`

**异常**: `ExtractionError`


## tools.read_terminal_tool

### 模块文档

Read the in-app terminal pane in the Hermes desktop GUI.

The embedded terminal's buffer lives in the desktop renderer (xterm.js), so this
tool round-trips through the gateway's blocking-prompt bridge — the same one
`clarify` uses: tui_gateway emits ``terminal.read.request``, the renderer answers
with ``terminal.read.respond``. This module is just schema + a thin dispatcher
over the platform-injected callback.

### 顶层函数

#### def `read_terminal_tool(start_line: Optional[int] = None, count: Optional[int] = None, callback: Optional[Callable] = None) -> str`

Return the in-app terminal's contents (+ line metadata) as a JSON string.

#### def `check_read_terminal_requirements() -> bool`

Desktop GUI only — HERMES_DESKTOP is set on the gateway the app spawns.


## tools.registry

### 模块文档

Central registry for all hermes-agent tools.

Each tool file calls ``registry.register()`` at module level to declare its
schema, handler, toolset membership, and availability check.  ``model_tools.py``
queries the registry instead of maintaining its own parallel data structures.

Import chain (circular-import safe):
    tools/registry.py  (no imports from model_tools or tool files)
           ^
    tools/*.py  (import from tools.registry at module level)
           ^
    model_tools.py  (imports tools.registry + all tool modules)
           ^
    run_agent.py, cli.py, batch_runner.py, etc.

### class ToolEntry

> 继承: `object` ｜ 方法数: 1（公开 0）

Metadata for a single registered tool.

#### def `__init__(name, toolset, schema, handler, check_fn, requires_env, is_async, description, emoji, max_result_size_chars = None, dynamic_schema_overrides = None)`


### class ToolRegistry

> 继承: `object` ｜ 方法数: 29（公开 22）

Singleton registry that collects tool schemas + handlers from tool files.

#### def `__init__()`

#### def `get_entry(self, name: str) -> Optional[ToolEntry]`

Return a registered tool entry by name, or None.

#### def `get_registered_toolset_names(self) -> List[str]`

Return sorted unique toolset names present in the registry.

#### def `get_tool_names_for_toolset(self, toolset: str) -> List[str]`

Return sorted tool names registered under a given toolset.

#### def `register_toolset_alias(self, alias: str, toolset: str) -> None`

Register an explicit alias for a canonical toolset name.

#### def `get_registered_toolset_aliases(self) -> Dict[str, str]`

Return a snapshot of ``{alias: canonical_toolset}`` mappings.

#### def `get_toolset_alias_target(self, alias: str) -> Optional[str]`

Return the canonical toolset name for an alias, or None.

#### def `register_plugin_override_policy(self, module_namespace: str, allowed: bool) -> None`

Bind a plugin module namespace to its operator opt-in for built-in
override. Called once per plugin at load time. Durable: never cleared,
so later (even threaded/delayed) register() calls from that module are
still gated by the same policy.

#### def `register(self, name: str, toolset: str, schema: dict, handler: Callable, check_fn: Callable = None, requires_env: list = None, is_async: bool = False, description: str = '', emoji: str = '', max_result_size_chars: int | float | None = None, dynamic_schema_overrides: Callable = None, override: bool = False)`

Register a tool.  Called at module-import time by each tool file.

``override=True`` is an explicit opt-in for plugins that intend to
replace an existing built-in tool implementation (e.g. swap the
default browser tool for a headed-Chrome CDP backend). Without it,
registrations that would shadow an existing tool from a different
toolset are rejected to prevent accidental overwrites.

**异常**: `PermissionError`

#### def `deregister(self, name: str) -> None`

Remove a tool from the registry.

Also cleans up the toolset check if no other tools remain in the
same toolset.  Used by MCP dynamic tool discovery to nuke-and-repave
when a server sends ``notifications/tools/list_changed``.

Gated by the same operator opt-in policy ``register(override=True)``
enforces. Without this, a plugin could bypass that gate entirely by
deregistering a tool it doesn't own and then calling plain
``register()`` over the now-empty slot — ``register()`` only runs its
override check when an ``existing`` entry is present, so removing it
first skips the check altogether. MCP toolsets (``mcp-*``) are exempt:
dynamic tool discovery legitimately nukes-and-repaves its own tools on
every refresh and has no plugin-override concept.

**异常**: `PermissionError`

#### def `get_definitions(self, tool_names: Set[str], quiet: bool = False) -> List[dict]`

Return OpenAI-format tool schemas for the requested tool names.

Only tools whose ``check_fn()`` returns True (or have no check_fn)
are included. ``check_fn()`` results are cached for ~30 s via
:func:`_check_fn_cached` to amortize repeat probes (check_terminal_
requirements probes modal/docker, browser checks probe playwright,
etc.); TTL chosen so env-var changes (``hermes tools enable foo``)
still take effect in near-real-time without forcing a full cache
flush on every call.

#### def `dispatch(self, name: str, args: dict, **kwargs) -> str | dict`

Execute a tool handler by name.

* Async handlers are bridged automatically via ``_run_async()``.
* Handler results are normalized to a string or supported multimodal
  envelope before leaving the registry.
* All exceptions are caught and returned as ``{"error": "..."}``
  for consistent error format.

#### def `get_max_result_size(self, name: str, default: int | float | None = None) -> int | float`

Return per-tool max result size, or *default* (or global default).

#### def `get_all_tool_names(self) -> List[str]`

Return sorted list of all registered tool names.

#### def `get_schema(self, name: str) -> Optional[dict]`

Return a tool's raw schema dict, bypassing check_fn filtering.

Useful for token estimation and introspection where availability
doesn't matter — only the schema content does.

#### def `get_toolset_for_tool(self, name: str) -> Optional[str]`

Return the toolset a tool belongs to, or None.

#### def `get_emoji(self, name: str, default: str = '⚡') -> str`

Return the emoji for a tool, or *default* if unset.

#### def `get_tool_to_toolset_map(self) -> Dict[str, str]`

Return ``{tool_name: toolset_name}`` for every registered tool.

#### def `is_toolset_available(self, toolset: str) -> bool`

Check if a toolset has at least one exposable tool.

Returns False (rather than crashing) when a per-tool check raises
an unexpected exception (e.g. network error, missing import, bad config).

#### def `check_toolset_requirements(self) -> Dict[str, bool]`

Return ``{toolset: available_bool}`` for every toolset.

#### def `get_available_toolsets(self) -> Dict[str, dict]`

Return toolset metadata for UI display.

#### def `get_toolset_requirements(self) -> Dict[str, dict]`

Build a TOOLSET_REQUIREMENTS-compatible dict for backward compat.

#### def `check_tool_availability(self, quiet: bool = False)`

Return (available_toolsets, unavailable_info) like the old function.


### 顶层函数

#### def `discover_builtin_tools(tools_dir: Optional[Path] = None) -> List[str]`

Import built-in self-registering tool modules and return their module names.

#### def `invalidate_check_fn_cache() -> None`

Drop all cached ``check_fn`` results. Call after config changes that
affect tool availability (e.g. ``hermes tools enable``).

#### def `tool_error(message, **extra) -> str`

Return a JSON error string for tool handlers.

>>> tool_error("file not found")
'{"error": "file not found"}'
>>> tool_error("bad input", success=False)
'{"error": "bad input", "success": false}'

#### def `tool_result(data = None, **kwargs) -> str`

Return a JSON result string for tool handlers.

Accepts a dict positional arg *or* keyword arguments (not both):

>>> tool_result(success=True, count=42)
'{"success": true, "count": 42}'
>>> tool_result({"key": "value"})
'{"key": "value"}'


## tools.schema_sanitizer

### 模块文档

Sanitize tool JSON schemas for broad LLM-backend compatibility.

Some local inference backends (notably llama.cpp's ``json-schema-to-grammar``
converter used to build GBNF tool-call parsers) are strict about what JSON
Schema shapes they accept. Schemas that OpenAI / Anthropic / most cloud
providers silently accept can make llama.cpp fail the entire request with:

    HTTP 400: Unable to generate parser for this template.
    Automatic parser generation failed: JSON schema conversion failed:
    Unrecognized schema: "object"

The failure modes we've seen in the wild:

* ``{"type": "object"}`` with no ``properties`` — rejected as a node the
  grammar generator can't constrain.
* A schema value that is the bare string ``"object"`` instead of a dict
  (malformed MCP server output, e.g. ``additionalProperties: "object"``).
* ``"type": ["string", "null"]`` array types — many converters only accept
  single-string ``type``.
* ``anyOf`` / ``oneOf`` unions whose only purpose is to permit ``null`` for
  optional fields (common Pydantic/MCP shape). Anthropic rejects these at
  the top of ``input_schema``; collapse them to the non-null branch.
* Unconstrained ``additionalProperties`` on objects with empty properties.
* ``default`` (and other annotation keywords) alongside ``$ref`` — strict
  backends (Fireworks-hosted Kimi, JSON Schema draft-07 validators) reject
  sibling keywords at the same level as ``$ref``.  Common MCP/Pydantic shape
  after nullable-union collapse::

      {"$ref": "#/$defs/Foo", "default": null}

This module walks the final tool schema tree (after MCP-level normalization
and any per-tool dynamic rebuilds) and fixes the known-hostile constructs
in-place on a deep copy. It is intentionally conservative: it only modifies
shapes the LLM backend couldn't use anyway.

### 顶层函数

#### def `sanitize_tool_schemas(tools: list[dict]) -> list[dict]`

Return a copy of ``tools`` with each tool's parameter schema sanitized.

Input is an OpenAI-format tool list:
``[{"type": "function", "function": {"name": ..., "parameters": {...}}}]``

The returned list is a deep copy — callers can safely mutate it without
affecting the original registry entries.

#### def `strip_nullable_unions(schema: Any, keep_nullable_hint: bool = True) -> Any`

Collapse ``anyOf`` / ``oneOf`` nullable unions to the non-null branch.

MCP / Pydantic optional fields commonly arrive as::

    {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null}

Anthropic's tool input-schema validator rejects the null branch. Tool
optionality is already represented by the parent object's ``required``
array, so we collapse the union to the single non-null variant.

Metadata (``title``, ``description``, ``default``, ``examples``) on the
outer union node is carried over to the replacement variant.

Args:
    schema: JSON-Schema fragment (dict, list, or scalar).
    keep_nullable_hint: If True, set ``nullable: true`` on the replacement
        to preserve the "this field may be None" signal for downstream
        consumers that care (e.g. runtime argument coercion that maps the
        literal string ``"null"`` to Python ``None``). Anthropic's
        validator accepts ``nullable: true`` but strict producers may
        prefer False.

Returns:
    The schema with nullable unions collapsed. Non-union nodes are
    returned unchanged.

#### def `strip_pattern_and_format(tools: list[dict]) -> tuple[list[dict], int]`

Strip ``pattern`` and ``format`` JSON Schema keywords from tool schemas.

This is a *reactive* sanitizer invoked only when llama.cpp's
``json-schema-to-grammar`` converter has rejected a tool schema with an
HTTP 400 grammar-parse error.  llama.cpp's regex engine supports only a
small subset of ECMAScript regex (literals, ``.``, ``[...]``, ``|``,
``*``, ``+``, ``?``, ``{n,m}``) — it rejects escape classes like ``\d``,
``\w``, ``\s`` and most ``format`` values.  Cloud providers (OpenAI,
Anthropic, OpenRouter, Gemini) accept these keywords fine and rely on
them as prompting hints, so we keep them in the default schema and only
strip on demand.

The strip operates on a sibling of ``type`` (so schema keywords are
removed) — a property literally *named* ``pattern`` (e.g. the first arg
of the built-in ``search_files`` tool) is not affected because property
names live in the ``properties`` dict, not as siblings of ``type``.

Args:
    tools: OpenAI-format tool list, mutated in place for efficiency.
        Callers that need to preserve the original should deep-copy first.

Returns:
    ``(tools, stripped_count)`` — the same list reference plus a count of
    how many ``pattern``/``format`` keywords were removed across all tools.

#### def `strip_slash_enum(tools: list[dict]) -> tuple[list[dict], int]`

Strip ``enum`` keywords whose string values contain a forward slash.

xAI's ``/v1/responses`` and ``/v1/chat/completions`` endpoints compile
tool schemas to a grammar that rejects ``enum`` values containing ``/``
(the request fails with HTTP 400 "Invalid arguments passed to the
model" before any token is emitted). Most commonly hit by MCP-derived
tools whose enum lists HuggingFace model IDs (``Qwen/Qwen3.5-0.8B``,
``openai/gpt-oss-20b``) or owner/name environment IDs. The constraint
is purely a prompting hint; dropping it lets the model still see the
field description and pick a value, without xAI tripping on the slash.

Args:
    tools: OpenAI-format or Responses-format tool list, mutated in
        place. Callers that need to preserve the original should
        deep-copy first.

Returns:
    ``(tools, stripped_count)`` — same list reference plus a count of
    how many ``enum`` keywords were removed.


## tools.send_message_tool

### 模块文档

Send Message Tool -- cross-channel messaging via platform APIs.

Sends a message to a user or channel on any connected messaging platform
(Telegram, Discord, Slack). Supports listing available targets and resolving
human-friendly channel names to IDs. Works in both CLI and gateway contexts.

### 顶层函数

#### def `send_message_tool(args, **kw)`

Handle cross-channel send_message tool calls.


## tools.session_search_tool

### 模块文档

Session Search Tool - Long-Term Conversation Recall

Single-shape tool with three calling modes (inferred from args, no explicit
mode parameter):

  1. DISCOVERY — pass ``query``. Runs FTS5, dedupes hits by session lineage,
     returns top N sessions each with: snippet, ±5 message window around the
     match, plus bookend_start (first 3 user+assistant msgs of session) and
     bookend_end (last 3). Zero LLM cost.

  2. SCROLL — pass ``session_id`` + ``around_message_id``. Returns a window
     of ±window messages centered on the anchor, no FTS5, no bookends. To
     scroll forward / backward, re-anchor on the last / first message id of
     the returned window.

  3. BROWSE — no args. Returns recent sessions chronologically (titles,
     previews, timestamps).

All three modes operate on the SQLite session DB via the FTS5 index and
the get_anchored_view / get_messages_around primitives in hermes_state.
No LLM calls anywhere — every shape returns actual messages from the DB.

History: PR #20238 (JabberELF) seeded a fast/summary dual-mode split; the
toolkit expansion in PR #26419 (yoniebans) added the anchored drill-down,
bookends, and sort. This module merges all of that into a single calling
shape with no mode parameter, no summary LLM path, and explicit scroll
support.

### 顶层函数

#### def `session_search(query: str = '', role_filter: str = None, limit: int = 3, db = None, current_session_id: str = None, session_id: str = None, around_message_id: int = None, window: int = 5, sort: str = None, profile: str = None) -> str`

Single-shape tool. Mode inferred from which args are set.

Discovery: pass ``query``.
Scroll:    pass ``session_id`` + ``around_message_id``.
Read:      pass ``session_id`` (no anchor) — dumps the whole session.
Browse:    pass nothing.

Pass ``profile`` to read another profile's sessions (e.g. resolving an
``@session:<profile>/<id>`` link). Scroll wins over read/discovery when an
anchor is set — the agent has asked for a specific slice.

#### def `check_session_search_requirements() -> bool`

Requires the SQLite state database.


## tools.skill_manager_tool

### 模块文档

Skill Manager Tool -- Agent-Managed Skill Creation & Editing

Allows the agent to create, update, and delete skills, turning successful
approaches into reusable procedural knowledge. New skills are created in
~/.hermes/skills/. Existing skills (bundled, hub-installed, or user-created)
can be modified or deleted wherever they live.

Skills are the agent's procedural memory: they capture *how to do a specific
type of task* based on proven experience. General memory (MEMORY.md, USER.md) is
broad and declarative. Skills are narrow and actionable.

Actions:
  create     -- Create a new skill (SKILL.md + directory structure)
  edit       -- Replace the SKILL.md content of a user skill (full rewrite)
  patch      -- Targeted find-and-replace within SKILL.md or any supporting file
  delete     -- Remove a user skill entirely
  write_file -- Add/overwrite a supporting file (reference, template, script, asset)
  remove_file-- Remove a supporting file from a user skill

Directory layout for user skills:
    ~/.hermes/skills/
    ├── my-skill/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── templates/
    │   ├── scripts/
    │   └── assets/
    └── category-name/
        └── another-skill/
            └── SKILL.md

### 顶层函数

#### def `mark_background_review_skill_read(path: Path) -> None`

Record that the active background-review fork has read a skill file.

The autonomous review fork is allowed to evolve skills, but it must not
patch or rewrite content it has only inferred from the transcript.  The
skill_view tool calls this after returning file content to the model; write
paths below require the corresponding target path to be present when the
current origin is ``background_review``.

#### def `apply_skill_pending(payload: Dict[str, Any]) -> str`

Replay a staged skill write, bypassing the gate. Returns the tool result
JSON string. Called by the /skills approve handler.

#### def `skill_manage(action: str, name: str, content: str = None, category: str = None, file_path: str = None, file_content: str = None, old_string: str = None, new_string: str = None, replace_all: bool = False, absorbed_into: str = None) -> str`

Manage user-created skills. Dispatches to the appropriate action handler.

Returns JSON string with results.


## tools.skill_provenance

### 模块文档

Skill write-origin provenance — ContextVar for distinguishing agent-sediment skill writes from foreground user-directed writes.

The curator only consolidates/prunes skills it autonomously created via the
background self-improvement review fork. Skills a user asks a foreground
agent to write belong to the user and must never be auto-curated.

This module exposes a ContextVar that run_agent.py sets before each tool
loop so tool handlers (e.g. skill_manage create) can check whether they
are executing inside the background-review fork.

The signal piggybacks on AIAgent._memory_write_origin, which is already
set to "background_review" for review-fork instances (see
_spawn_background_review in run_agent.py) and defaults to "assistant_tool"
for normal (foreground) agents.

Usage:
    from tools.skill_provenance import (
        set_current_write_origin,
        reset_current_write_origin,
        get_current_write_origin,
    )

    token = set_current_write_origin("background_review")
    try:
        ...  # tool runs here
    finally:
        reset_current_write_origin(token)

    # inside a tool:
    if get_current_write_origin() == "background_review":
        mark_agent_created(skill_name)

### 顶层函数

#### def `set_current_write_origin(origin: str) -> contextvars.Token[str]`

Bind the active write origin to the current context.

Returns a Token the caller must pass to reset_current_write_origin
in a finally block.

#### def `reset_current_write_origin(token: contextvars.Token[str]) -> None`

Restore the prior write origin context.

#### def `get_current_write_origin() -> str`

Return the active write origin.

Default: "foreground" — any tool call made by a regular (non-review)
agent, from the CLI, the gateway, cron, or a subagent.

"background_review" — the self-improvement review fork; only skills
created under this origin should be marked agent-created for curator
management.

#### def `is_background_review() -> bool`

Convenience: True iff the current write origin is the background
review fork.


## tools.skill_usage

### 模块文档

Skill usage telemetry + provenance tracking for the Curator feature.

Tracks per-skill usage metadata in a sidecar JSON file (~/.hermes/skills/.usage.json)
keyed by skill name. Counters are bumped by the existing skill tools (skill_view,
skill_manage); the curator orchestrator reads the derived activity timestamp to
decide lifecycle transitions.

Design notes:
  - Sidecar, not frontmatter. Keeps operational telemetry out of user-authored
    SKILL.md content and avoids conflict pressure for bundled/hub skills.
  - Atomic writes via tempfile + os.replace (same pattern as .bundled_manifest).
  - All counter bumps are best-effort: failures log at DEBUG and return silently.
    A broken sidecar never breaks the underlying tool call.
  - Provenance filter: curator-managed skills are explicitly marked when
    created through skill_manage. Bundled / hub-installed skills stay
    off-limits, and manually authored skills are not inferred from location.

Lifecycle states:
    active    -> default
    stale     -> unused > stale_after_days (config)
    archived  -> unused > archive_after_days (config); moved to .archive/
    pinned    -> opt-out from auto transitions (boolean flag, orthogonal to state)

### 顶层函数

#### def `is_protected_builtin(skill_name: str) -> bool`

Whether *skill_name* is a load-bearing built-in the curator never touches.

Protected built-ins are exempt from archival and consolidation on every
path: the automatic state-transition walk, the LLM consolidation pass (they
are dropped from the candidate list), and direct ``archive_skill`` calls.

#### def `latest_activity_at(record: Dict[str, Any]) -> Optional[str]`

Return the newest actual activity timestamp for a usage record.

"Activity" means a skill was used, viewed, or patched. Creation time is
intentionally excluded so callers can still distinguish never-active skills;
lifecycle code can fall back to ``created_at`` as its own anchor.

#### def `activity_count(record: Dict[str, Any]) -> int`

Return the total observed activity count across use/view/patch events.

#### def `read_suppressed_names() -> Set[str]`

Built-in skills the curator pruned — the re-seeder must leave archived.

One skill name per line in ``~/.hermes/skills/.curator_suppressed``. This is
what makes pruning a built-in durable: without it, ``hermes update`` would
re-copy the bundled skill on the next sync.

#### def `add_suppressed_name(skill_name: str) -> None`

Record that a built-in skill was pruned, so sync won't restore it.

#### def `remove_suppressed_name(skill_name: str) -> None`

Clear a built-in's suppression entry (e.g. on restore).

#### def `list_agent_created_skill_names() -> List[str]`

Enumerate skills the curator may manage.

Always includes agent-authored skills (those marked in ``.usage.json`` via
``skill_manage(action="create")``). When ``curator.prune_builtins`` is
enabled, bundled built-in skills are ALSO included even though they have no
agent-created usage record — their inactivity clock is anchored on first
sight (see ``apply_automatic_transitions``). Hub-installed skills are never
included; manually authored skills are not inferred from filesystem
location.

#### def `list_archived_skill_names() -> List[str]`

Enumerate skills in ``~/.hermes/skills/.archive/``.

Archive layout is flat (``.archive/<skill>/``) as set by ``archive_skill``,
so the directory name is the skill name. Used by ``hermes curator
list-archived`` to help users pass a name to ``hermes curator restore``.

#### def `is_agent_created(skill_name: str) -> bool`

Whether *skill_name* is neither bundled nor hub-installed.

#### def `is_hub_installed(skill_name: str) -> bool`

Whether *skill_name* was installed via the Skills Hub.

#### def `is_bundled(skill_name: str) -> bool`

Whether *skill_name* was seeded from the bundled repo skills.

#### def `is_curation_eligible(skill_name: str, skill_path: Optional[Path] = None) -> bool`

Whether the curator may track/archive *skill_name*.

Agent-created skills are always eligible. Bundled built-ins become eligible
only when ``curator.prune_builtins`` is enabled. Hub-installed and external
skill-dir skills are NEVER eligible — they have an external upstream owner.
Protected built-ins (``PROTECTED_BUILTIN_SKILLS``) are NEVER eligible
regardless of any flag — they back load-bearing UX and must never be
archived or consolidated.

#### def `load_usage() -> Dict[str, Dict[str, Any]]`

Read the entire .usage.json map. Returns empty dict on missing/corrupt.

#### def `save_usage(data: Dict[str, Dict[str, Any]]) -> None`

Write the usage map atomically. Best-effort — errors are logged, not raised.

#### def `get_record(skill_name: str) -> Dict[str, Any]`

Return the record for *skill_name*, creating a fresh one if missing.

#### def `seed_record_if_missing(skill_name: str) -> None`

Persist a baseline usage record for a curation-eligible skill.

Built-ins carry no usage record until something touches them, which leaves
their inactivity clock with no anchor. Seeding a record here fixes
``created_at`` to the moment the curator first sees the skill, so the
archive/stale clock measures non-use FROM THEN — not from epoch. No-op when
a record already exists or the skill isn't curation-eligible.

#### def `bump_view(skill_name: str) -> None`

Bump view_count and last_viewed_at. Called from skill_view().

Tracks every skill regardless of provenance — built-ins and hub skills
included. Usage telemetry is observability, not a curation signal.

#### def `bump_use(skill_name: str) -> None`

Bump use_count and last_used_at. Called when a skill is actively used
(e.g. loaded into the prompt path or referenced from an assistant turn).

Tracks every skill regardless of provenance.

#### def `bump_patch(skill_name: str) -> None`

Bump patch_count and last_patched_at. Called from skill_manage (patch/edit).

Tracks every skill regardless of provenance.

#### def `mark_agent_created(skill_name: str) -> None`

Opt a skill created by skill_manage into curator management.

Viewing or invoking a manually authored skill may still create telemetry,
but only this explicit marker makes it eligible for automatic curation.

#### def `set_state(skill_name: str, state: str) -> None`

Set lifecycle state. No-op if *state* is invalid or the skill isn't
curator-manageable (hub skills, or built-ins with pruning disabled).

#### def `set_pinned(skill_name: str, pinned: bool) -> None`

#### def `forget(skill_name: str) -> None`

Drop a skill's usage entry entirely. Called when the skill is deleted.

#### def `archive_skill(skill_name: str) -> Tuple[bool, str]`

Move a curator-eligible skill directory to ~/.hermes/skills/.archive/.

Returns (ok, message). Never archives hub-installed skills. Bundled
built-ins are only archivable when ``curator.prune_builtins`` is enabled;
when one is archived, its name is added to the suppression list so the
update-time re-seeder leaves it archived instead of restoring it.

#### def `restore_skill(skill_name: str) -> Tuple[bool, str]`

Move an archived skill back to ~/.hermes/skills/. Restores to the flat
top-level layout; original category nesting is NOT reconstructed.

Refuses to restore under a name that now collides with a hub-installed
skill — that would shadow the upstream version. Also refuses to restore
over a bundled built-in UNLESS ``curator.prune_builtins`` is enabled (in
which case built-ins are curator-managed and restoring is the documented
way to lift a prune). Restoring clears any suppression entry so future
updates may re-seed the built-in again.

#### def `agent_created_report() -> List[Dict[str, Any]]`

Return a list of {name, state, pinned, last_activity_at, ...}
records for every curator-managed skill. Missing usage records are
backfilled with defaults so callers can always index fields.

Each row carries ``_persisted``: True when a real record exists in
``.usage.json``, False when the row is a fresh backfill (e.g. a built-in
seen for the first time). The curator uses this to seed the inactivity
clock instead of treating an unrecorded skill as ancient.

#### def `provenance(skill_name: str) -> str`

Classify a skill's origin: 'hub', 'bundled', or 'agent'.

'agent' covers both agent-authored and local manually-authored skills —
anything not seeded from the bundled repo or installed via the hub.

#### def `usage_report() -> List[Dict[str, Any]]`

Return usage telemetry for EVERY skill on disk, with provenance.

Unlike ``agent_created_report()`` (which is scoped to curator-managed
candidates), this surfaces all skills — bundled built-ins and
hub-installed included — so callers can answer "how often is this skill
used" independent of whether it's ever curated. Rows carry a
``provenance`` field ('agent' | 'bundled' | 'hub') and ``_persisted``
(whether a real ``.usage.json`` record backs the row).


## tools.skills_ast_audit

### 模块文档

AST-level deep audit for skill Python files — opt-in diagnostic, not a security gate.

Per SECURITY.md §2.4, Skills Guard is in-process heuristics ("useful — not
boundaries"). This module is a separate opt-in diagnostic that flags dynamic
import / dynamic attribute access patterns operators may want to eyeball when
reviewing third-party skill code. Every pattern flagged here has legitimate
uses; findings are hints for human review, not verdicts.

CLI: ``hermes skills audit --deep``

### 顶层函数

#### def `ast_scan_path(path: Path) -> List[Finding]`

Scan a single .py file or recursively scan all .py under a directory.

Returns a list of (file, line, pattern_id, description) tuples. Empty for
non-Python paths, missing paths, or paths with no matching patterns.

#### def `format_ast_report(findings: List[Finding], skill_name: str = '') -> str`

Plain-text report (Rich-markup-free) grouped by file.


## tools.skills_guard

### 模块文档

Skills Guard — Security scanner for externally-sourced skills.

Every skill downloaded from a registry passes through this scanner before
installation. It uses regex-based static analysis to detect known-bad patterns
(data exfiltration, prompt injection, destructive commands, persistence, etc.)
and a trust-aware install policy that determines whether a skill is allowed
based on both the scan verdict and the source's trust level.

Trust levels:
  - builtin:   Ships with Hermes. Never scanned, always trusted.
  - trusted:   openai/skills and anthropics/skills only. Caution verdicts allowed.
  - community: Everything else. Any findings = blocked unless --force.

Usage:
    from tools.skills_guard import scan_skill, should_allow_install, format_scan_report

    result = scan_skill(Path("skills/.hub/quarantine/some-skill"), source="community")
    allowed, reason = should_allow_install(result)
    if not allowed:
        print(format_scan_report(result))

### class Finding

> 继承: `object` ｜ 方法数: 0（公开 0）


### class ScanResult

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `scan_file(file_path: Path, rel_path: str = '') -> List[Finding]`

Scan a single file for threat patterns and invisible unicode characters.

Args:
    file_path: Absolute path to the file
    rel_path: Relative path for display (defaults to file_path.name)

Returns:
    List of findings (deduplicated per pattern per line)

#### def `scan_skill(skill_path: Path, source: str = 'community') -> ScanResult`

Scan all files in a skill directory for security threats.

Performs:
1. Structural checks (file count, total size, binary files, symlinks)
2. Regex pattern matching on all text files
3. Invisible unicode character detection

A skill may ship a `.skillignore` (or `.clawhubignore`) file with
gitignore-style patterns. Matching paths are excluded from BOTH the
structural checks and the pattern scan, so development/docs artifacts
that are not part of the installed skill (e.g. `SKILL-original.md`,
`docs/plans/`, `release-notes.md`) don't trip findings. The ignore
file itself is always excluded. Patterns cannot un-ignore the
skill's own `SKILL.md`, which is always scanned.

Args:
    skill_path: Path to the skill directory (must contain SKILL.md)
    source: Source identifier for trust level resolution (e.g. "openai/skills")

Returns:
    ScanResult with verdict, findings, and trust metadata

#### def `full_content_hash(skill_path: Path) -> str`

Full canonical digest used to bind scanner attestations.

#### def `scan_skill_cached(skill_path: Path, source: str = 'community', source_url: str = '', cache_dir: Path | None = None) -> Tuple[ScanResult, dict]`

Return a scan plus attestation, caching only exact current content.

#### def `should_allow_install(result: ScanResult, force: bool = False) -> Tuple[bool, str]`

Determine whether a skill should be installed based on scan result and trust.

Args:
    result: Scan result from scan_skill()
    force: If True, override blocked policy decisions for this scan result

Returns:
    (allowed, reason) tuple

#### def `format_scan_report(result: ScanResult) -> str`

Format a scan result as a human-readable report string.

Returns a compact multi-line report suitable for CLI or chat display.

#### def `content_hash(skill_path: Path) -> str`

Compute a SHA-256 hash of all files in a skill directory for integrity tracking.

File paths (relative to ``skill_path``) are mixed into the hash alongside
file contents so that swapping the contents of two files in a skill
changes the hash. This must stay symmetric with
``tools.skills_hub.bundle_content_hash`` — both functions need to
produce the same digest for the same skill (one operates on disk,
one on an in-memory bundle), so any change to the hash shape MUST
land in both places at once.


## tools.skills_hub

### 模块文档

Skills Hub — Source adapters and hub state management for the Hermes Skills Hub.

This is a library module (not an agent tool). It provides:
  - GitHubAuth: Shared GitHub API authentication (PAT, gh CLI, GitHub App)
  - SkillSource ABC: Interface for all skill registry adapters
  - OptionalSkillSource: Official optional skills shipped with the repo (not activated by default)
  - GitHubSource: Fetch skills from any GitHub repo via the Contents API
  - HubLockFile: Track provenance of installed hub skills
  - Hub state directory management (quarantine, audit log, taps, index cache)

Used by hermes_cli/skills_hub.py for CLI commands and the /skills slash command.

### class SkillMeta

> 继承: `object` ｜ 方法数: 0（公开 0）

Minimal metadata returned by search results.


### class SkillBundle

> 继承: `object` ｜ 方法数: 0（公开 0）

A downloaded skill ready for quarantine/scanning/installation.


### class GitHubAuth

> 继承: `object` ｜ 方法数: 7（公开 3）

GitHub API authentication. Tries methods in priority order:
  1. GITHUB_TOKEN / GH_TOKEN env var (PAT — the default)
  2. `gh auth token` subprocess (if gh CLI is installed)
  3. GitHub App JWT + installation token (if app credentials configured)
  4. Unauthenticated (60 req/hr, public repos only)

#### def `__init__()`

#### def `get_headers(self) -> Dict[str, str]`

Return authorization headers for GitHub API requests.

#### def `is_authenticated(self) -> bool`

#### def `auth_method(self) -> str`

Return which auth method is active: 'pat', 'gh-cli', 'github-app', or 'anonymous'.


### class SkillSource

> 继承: `ABC` ｜ 方法数: 5（公开 5）

Abstract base for all skill registry adapters.

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

Search for skills matching a query string.

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

Download a skill bundle by identifier.

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`

Fetch metadata for a skill without downloading all files.

#### def `source_id(self) -> str`

Unique identifier for this source (e.g. 'github', 'clawhub').

#### def `trust_level_for(self, identifier: str) -> str`

Determine trust level for a skill from this source.


### class GitHubSource

> 继承: `SkillSource` ｜ 方法数: 23（公开 6）

Fetch skills from GitHub repos via the Contents API.

#### def `__init__(auth: GitHubAuth, extra_taps: Optional[List[Dict]] = None)`

#### def `source_id(self) -> str`

#### property `is_rate_limited(self) -> bool`

Whether GitHub API rate limit was hit during operations.

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

Search all taps for skills matching the query.

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

Download a skill from GitHub.
identifier format: "owner/repo/path/to/skill-dir"

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`

Fetch just the SKILL.md metadata for preview.


### class WellKnownSkillSource

> 继承: `SkillSource` ｜ 方法数: 11（公开 5）

Read skills from a domain exposing /.well-known/skills/index.json.

#### def `source_id(self) -> str`

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`


### class UrlSource

> 继承: `SkillSource` ｜ 方法数: 10（公开 5）

Fetch SKILL.md plus explicitly referenced, allowlisted support files.

The identifier IS the URL (e.g. ``https://example.com/path/SKILL.md``).
Bare URLs cannot safely enumerate a repository, so only exact references
below references/templates/scripts/assets are fetched. Other repository
files are never copied.

The skill name is read from the ``name:`` field in the SKILL.md YAML
frontmatter (with a URL-slug fallback). Trust level is always
``community`` and the same security scan runs as for every other source.

#### def `source_id(self) -> str`

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`


### class SkillsShSource

> 继承: `SkillSource` ｜ 方法数: 25（公开 5）

Discover skills via skills.sh and fetch content from the underlying GitHub repo.

#### def `__init__(auth: GitHubAuth)`

#### def `source_id(self) -> str`

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`


### class ClawHubSource

> 继承: `SkillSource` ｜ 方法数: 19（公开 5）

Fetch skills from ClawHub (clawhub.ai) via their HTTP API.
All skills are treated as community trust — ClawHavoc incident showed
their vetting is insufficient (341 malicious skills found Feb 2026).

#### def `source_id(self) -> str`

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`


### class ClaudeMarketplaceSource

> 继承: `SkillSource` ｜ 方法数: 8（公开 6）

Discover skills from Claude Code marketplace repos.
Marketplace repos contain .claude-plugin/marketplace.json with plugin listings.

#### def `__init__(auth: GitHubAuth)`

#### def `source_id(self) -> str`

#### property `is_rate_limited(self) -> bool`

Whether the underlying GitHub API hit a rate limit during the crawl.

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`


### class LobeHubSource

> 继承: `SkillSource` ｜ 方法数: 8（公开 5）

Fetch skills from LobeHub's agent marketplace (14,500+ agents).
LobeHub agents are system prompt templates — we convert them to SKILL.md on fetch.
Data lives in GitHub: lobehub/lobe-chat-agents.

#### def `source_id(self) -> str`

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`


### class BrowseShSource

> 继承: `SkillSource` ｜ 方法数: 9（公开 5）

Discover and install site-specific browser automation skills from browse.sh.

browse.sh (https://browse.sh) is Browserbase's catalog of 200+ SKILL.md files
that describe how to automate specific websites (Airbnb, Amazon, arXiv, etc.).
The catalog lives at ``/api/skills`` and each skill's actual SKILL.md content
is fetched via ``/api/skills/{slug}`` which returns a ``skillMdUrl`` field
pointing at a CDN-hosted blob — the catalog's ``sourceUrl`` field is a GitHub
HTML URL whose underlying repository is not always public, so it cannot be
relied on for content fetch.

#### def `source_id(self) -> str`

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`


### class OptionalSkillSource

> 继承: `SkillSource` ｜ 方法数: 9（公开 5）

Fetch skills from the optional-skills/ directory shipped with the repo.

These skills are official (maintained by Nous Research) but not activated
by default — they don't appear in the system prompt and aren't copied to
~/.hermes/skills/ during setup.  They are discoverable via the Skills Hub
(search / install / inspect) and labelled "official" with "builtin" trust.

#### def `__init__()`

#### def `source_id(self) -> str`

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`


### class HubLockFile

> 继承: `object` ｜ 方法数: 7（公开 6）

Manages skills/.hub/lock.json — tracks provenance of installed hub skills.

#### def `__init__(path: Optional[Path] = None)`

#### def `load(self) -> dict`

#### def `save(self, data: dict) -> None`

#### def `record_install(self, name: str, source: str, identifier: str, trust_level: str, scan_verdict: str, skill_hash: str, install_path: str, files: List[str], metadata: Optional[Dict[str, Any]] = None, scan_provenance: Optional[Dict[str, Any]] = None) -> None`

#### def `record_uninstall(self, name: str) -> None`

#### def `get_installed(self, name: str) -> Optional[dict]`

#### def `list_installed(self) -> List[dict]`


### class TapsManager

> 继承: `object` ｜ 方法数: 6（公开 5）

Manages the taps.json file — custom GitHub repo sources.

#### def `__init__(path: Optional[Path] = None)`

#### def `load(self) -> List[dict]`

#### def `save(self, taps: List[dict]) -> None`

#### def `add(self, repo: str, path: str = 'skills/') -> bool`

Add a tap. Returns False if already exists.

#### def `remove(self, repo: str) -> bool`

Remove a tap by repo name. Returns False if not found.

#### def `list_taps(self) -> List[dict]`


### class HermesIndexSource

> 继承: `SkillSource` ｜ 方法数: 11（公开 6）

Skill source backed by the centralized Hermes Skills Index.

The index is a JSON catalog published to the docs site and rebuilt
daily by CI.  It contains metadata + resolved GitHub paths for every
skill, eliminating the need for users to hit the GitHub API for
search or path discovery.

When the index is unavailable, all methods return empty / None so
downstream sources take over transparently.

#### def `__init__(auth: GitHubAuth)`

#### def `source_id(self) -> str`

#### property `is_available(self) -> bool`

Whether the index is loaded and has skills.

#### def `trust_level_for(self, identifier: str) -> str`

#### def `search(self, query: str, limit: int = 10) -> List[SkillMeta]`

Search the cached index.  Zero API calls.

Matches against name, description, tags, identifier, and the per-tap
``extra.provider`` label (so a query like ``nvidia`` surfaces the
``NVIDIA/skills/...`` entries even though their ``source`` is the bare
``github``).  Results are scored and ranked (exact name > name prefix >
whole-word > substring) rather than returned in raw index order and
truncated at the first ``limit`` hits — that earlier break-at-limit
behaviour returned an arbitrary file-order slice and buried the most
relevant skills.

#### def `fetch(self, identifier: str) -> Optional[SkillBundle]`

Fetch a skill using the resolved path from the index.

If the index has a ``resolved_github_id`` for this skill, we skip
the entire candidate/discovery chain and go directly to GitHub
with the exact path.  This reduces install from ~31 API calls to
just the file content downloads (~5-22 depending on skill size).

#### def `inspect(self, identifier: str) -> Optional[SkillMeta]`

Return metadata from the index.  Zero API calls.


### 顶层函数

#### def `source_url_for_bundle(bundle: SkillBundle) -> str`

Best available human-facing immutable-source provenance URL.

#### def `github_provider_for(repo: str) -> Optional[str]`

Return the provider label for a GitHub tap repo, or None.

``repo`` is ``owner/repo``; matched case-insensitively so ``NVIDIA/skills``
and ``nvidia/skills`` both resolve to ``"NVIDIA"``.

#### def `append_audit_log(action: str, skill_name: str, source: str, trust_level: str, verdict: str, extra: str = '') -> None`

Append a line to the audit log.

#### def `ensure_hub_dirs() -> None`

Create the .hub directory structure if it doesn't exist.

#### def `quarantine_bundle(bundle: SkillBundle) -> Path`

Write a skill bundle to the quarantine directory for scanning.

#### def `install_from_quarantine(quarantine_path: Path, skill_name: str, category: str, bundle: SkillBundle, scan_result: ScanResult, scan_provenance: Optional[Dict[str, Any]] = None) -> Path`

Move a scanned skill from quarantine into the skills directory.

**异常**: `ValueError`

#### def `uninstall_skill(skill_name: str) -> Tuple[bool, str]`

Remove a hub-installed skill. Refuses to remove builtins.

#### def `bundle_content_hash(bundle: SkillBundle) -> str`

Compute a deterministic hash for an in-memory skill bundle.

#### def `check_for_skill_updates(name: Optional[str] = None, lock: Optional[HubLockFile] = None, sources: Optional[List[SkillSource]] = None, auth: Optional[GitHubAuth] = None) -> List[dict]`

Check installed hub skills for upstream changes.

#### def `create_source_router(auth: Optional[GitHubAuth] = None) -> List[SkillSource]`

Create all configured source adapters.
Returns a list of active sources for search/fetch operations.

#### def `parallel_search_sources(sources: List[SkillSource], query: str = '', per_source_limits: Optional[Dict[str, int]] = None, source_filter: str = 'all', overall_timeout: float = 30, on_source_done: Optional[Any] = None) -> Tuple[List[SkillMeta], Dict[str, int], List[str]]`

Search all sources in parallel with per-source timeout.

Returns ``(all_results, source_counts, timed_out_ids)``.

*on_source_done* is an optional callback ``(source_id, count) -> None``
invoked as each source completes — useful for progress indicators.

#### def `unified_search(query: str, sources: List[SkillSource], source_filter: str = 'all', limit: int = 10) -> List[SkillMeta]`

Search all sources (in parallel) and merge results.


## tools.skills_sync

### 模块文档

Skills Sync -- Manifest-based seeding and updating of bundled skills.

Copies bundled skills from the repo's skills/ directory into ~/.hermes/skills/
and uses a manifest to track which skills have been synced and their origin hash.

Manifest format (v2): each line is "skill_name:origin_hash" where origin_hash
is the MD5 of the bundled skill at the time it was last synced to the user dir.
Old v1 manifests (plain names without hashes) are auto-migrated.

Update logic:
  - NEW skills (not in manifest): copied to user dir, origin hash recorded.
  - EXISTING skills (in manifest, present in user dir):
      * If user copy matches origin hash: user hasn't modified it → safe to
        update from bundled if bundled changed. New origin hash recorded.
      * If user copy differs from origin hash: user customized it → SKIP.
  - DELETED by user (in manifest, absent from user dir): respected, not re-added.
  - REMOVED from bundled (in manifest, gone from repo): cleaned from manifest.

The manifest lives at ~/.hermes/skills/.bundled_manifest.

### 顶层函数

#### def `restore_official_optional_skill(name: str, restore: bool = False) -> dict`

Restore one or all official optional skills from repo source.

``restore=False`` only performs exact-match provenance backfill. ``restore=True``
repairs already-mutated/reorganized skills by backing up matching active
copies and copying the official optional source into its canonical path.

#### def `sync_skills(quiet: bool = False) -> dict`

Sync bundled skills into ~/.hermes/skills/ using the manifest.

Returns:
    dict with keys: copied (list), updated (list), skipped (int),
                    user_modified (list), cleaned (list), total_bundled (int)

#### def `reset_bundled_skill(name: str, restore: bool = False) -> dict`

Reset a bundled skill's manifest tracking so future syncs work normally.

When a user edits a bundled skill, subsequent syncs mark it as
``user_modified`` and skip it forever — even if the user later copies
the bundled version back into place, because the manifest still holds
the *old* origin hash. This function breaks that loop.

Args:
    name: The skill name (matches the manifest key / skill frontmatter name).
    restore: If True, also delete the user's copy in SKILLS_DIR and let
             the next sync re-copy the current bundled version. If False
             (default), only clear the manifest entry — the user's
             current copy is preserved but future updates work again.

Returns:
    dict with keys:
      - ok: bool, whether the reset succeeded
      - action: one of "manifest_cleared", "restored", "not_in_manifest",
                "bundled_missing"
      - message: human-readable description
      - synced: dict from sync_skills() if a sync was triggered, else None

#### def `list_user_modified_bundled_skills() -> List[dict]`

Return the bundled skills that ``hermes update`` keeps because the user
edited them locally.

A skill counts as user-modified when its on-disk copy no longer matches the
origin hash recorded in the manifest the last time it was synced — the exact
same test the sync loop uses to decide what to skip. This is the discovery
half of that behavior, so a user can find the names the ``~ N user-modified
(kept)`` notice only counts.

Returns a list (sorted by name) of dicts:
    ``{"name": str, "dest": Path, "bundled_src": Path}``
where ``dest`` is the user's copy and ``bundled_src`` is the current stock
copy (so callers can diff or restore).

#### def `diff_bundled_skill(name: str) -> dict`

Diff a user's copy of a bundled skill against the current stock version.

Lets a user see exactly what diverged before deciding whether to keep their
edits or ``hermes skills reset`` back to upstream.

Returns a dict:
    ``ok`` (bool), ``name`` (str), ``found`` (bool — bundled source exists),
    ``modified`` (bool), ``message`` (str),
    ``diffs``: list of ``{"path": str, "status": str, "diff": str}`` where
    status is one of ``modified`` / ``added`` (only in user copy) /
    ``removed`` (only in bundled) / ``binary``.

#### def `set_bundled_skills_opt_out(enabled: bool) -> dict`

Toggle the .no-bundled-skills opt-out marker for the active profile.

When ``enabled`` is True, writes HERMES_HOME/.no-bundled-skills so the
installer, ``hermes update``, and any direct sync stop seeding bundled
skills. When False, removes the marker so seeding resumes on the next
sync. This is the on-disk-state half of ``hermes skills opt-out`` /
``opt-in``; removal of already-present skills is a separate, explicit
step (see ``remove_pristine_bundled_skills``).

Returns:
    dict with keys: ok (bool), changed (bool), marker (str path),
                    message (str).

#### def `is_bundled_skills_opt_out() -> bool`

Return True if the active profile carries the opt-out marker.

#### def `remove_pristine_bundled_skills(dry_run: bool = False) -> dict`

Delete bundled skills that are present, manifest-tracked, AND unmodified.

Safety is the whole point of this function. A skill on disk is removed
ONLY when all of these hold:
  - it is recorded in the sync manifest (so it is genuinely a bundled
    skill, not a hub-installed or hand-written one), AND
  - it still exists in the bundled source (so we can hash-compare), AND
  - its on-disk copy is byte-identical to the manifest origin hash
    (so the user has not edited it).

Anything user-modified, hub-installed, or locally authored is left
untouched and reported under ``skipped``. The manifest entry for each
removed skill is dropped so a later opt-in re-seed treats it as new.

Args:
    dry_run: When True, compute what would be removed without deleting.

Returns:
    dict with keys: ok (bool), removed (list[str]),
                    skipped (list[dict]) where each dict is
                    {name, reason}, dry_run (bool), message (str).


## tools.skills_tool

### 模块文档

Skills Tool Module

This module provides tools for listing and viewing skill documents.
Skills are organized as directories containing a SKILL.md file (the main instructions)
and optional supporting files like references, templates, and examples.

Inspired by Anthropic's Claude Skills system with progressive disclosure architecture:
- Metadata (name ≤64 chars, description ≤1024 chars) - shown in skills_list
- Full Instructions - loaded via skill_view when needed
- Linked Files (references, templates) - loaded on demand

Directory Structure:
    skills/
    ├── my-skill/
    │   ├── SKILL.md           # Main instructions (required)
    │   ├── references/        # Supporting documentation
    │   │   ├── api.md
    │   │   └── examples.md
    │   ├── templates/         # Templates for output
    │   │   └── template.md
    │   └── assets/            # Supplementary files (agentskills.io standard)
    └── category/              # Category folder for organization
        └── another-skill/
            └── SKILL.md

SKILL.md Format (YAML Frontmatter, agentskills.io compatible):
    ---
    name: skill-name              # Required, max 64 chars
    description: Brief description # Required, max 1024 chars
    version: 1.0.0                # Optional
    license: MIT                  # Optional (agentskills.io)
    platforms: [macos]            # Optional — restrict to specific OS platforms
                                  #   Valid: macos, linux, windows
                                  #   Omit to load on all platforms (default)
    prerequisites:                # Optional — legacy runtime requirements
      env_vars: [API_KEY]         #   Legacy env var names are normalized into
                                  #   required_environment_variables on load.
      commands: [curl, jq]        #   Command checks remain advisory only.
    compatibility: Requires X     # Optional (agentskills.io)
    metadata:                     # Optional, arbitrary key-value (agentskills.io)
      hermes:
        tags: [fine-tuning, llm]
        related_skills: [peft, lora]
    ---

    # Skill Title

    Full instructions and content here...

Available tools:
- skills_list: List skills with metadata (progressive disclosure tier 1)
- skill_view: Load full skill content (progressive disclosure tier 2-3)

Usage:
    from tools.skills_tool import skills_list, skill_view, check_skills_requirements

    # List all skills (returns metadata only - token efficient)
    result = skills_list()

    # View a skill's main content (loads full instructions)
    content = skill_view("axolotl")

    # View a reference file within a skill (loads linked file)
    content = skill_view("axolotl", "references/dataset-formats.md")

### class SkillReadinessStatus

> 继承: `str`、`Enum` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `load_env() -> Dict[str, str]`

Load profile-scoped environment variables from HERMES_HOME/.env.

#### def `set_secret_capture_callback(callback) -> None`

#### def `skill_matches_platform(frontmatter: Dict[str, Any]) -> bool`

Check if a skill is compatible with the current OS platform.

Delegates to ``agent.skill_utils.skill_matches_platform`` — kept here
as a public re-export so existing callers don't need updating.

#### def `skill_matches_environment(frontmatter: Dict[str, Any]) -> bool`

Check if a skill is relevant to the current runtime environment.

Delegates to ``agent.skill_utils.skill_matches_environment`` — kept here
as a public re-export so existing callers don't need updating. This is an
offer-time relevance gate (kanban/docker/s6), NOT a hard-compatibility gate;
explicit skill loads bypass it.

#### def `check_skills_requirements() -> bool`

Skills are always available -- the directory is created on first use if needed.

#### def `skills_list(category: str = None, task_id: str = None) -> str`

List all available skills (progressive disclosure tier 1 - minimal metadata).

Returns only name + description to minimize token usage. Use skill_view() to
load full content, tags, related files, etc.

Args:
    category: Optional category filter (e.g., "mlops")
    task_id: Optional task identifier used to probe the active backend

Returns:
    JSON string with minimal skill info: name, description, category

#### def `skill_view(name: str, file_path: str = None, task_id: str = None, preprocess: bool = True) -> str`

View the content of a skill or a specific file within a skill directory.

Args:
    name: Name or path of the skill (e.g., "axolotl" or "03-fine-tuning/axolotl").
        Qualified names like "plugin:skill" resolve to plugin-provided skills.
    file_path: Optional path to a specific file within the skill (e.g., "references/api.md")
    task_id: Optional task identifier used to probe the active backend
    preprocess: Apply configured SKILL.md template and inline shell rendering
        to main skill content. Internal slash/preload callers disable this
        because they render the skill message themselves.

Returns:
    JSON string with skill content or error message


## tools.slash_confirm

### 模块文档

Generic slash-command confirmation primitive (gateway-side).

Slash commands that have a non-destructive but expensive side effect worth
surfacing to the user (currently only ``/reload-mcp``, which invalidates
the provider prompt cache) route through this module.

Two delivery paths:

  1. Button UI — adapters that override ``send_slash_confirm`` render
     three inline buttons (Approve Once / Always Approve / Cancel).  The
     button callback calls ``resolve(session_key, confirm_id, choice)``.

  2. Text fallback — adapters without button UIs get a plain text prompt.
     Users reply with ``/approve``, ``/always``, or ``/cancel``; the
     gateway's ``_handle_message`` intercepts those replies and calls
     ``resolve()`` directly.

State is stored module-level (like ``tools.approval``) so platform
adapters can resolve callbacks without needing a backreference to the
``GatewayRunner`` instance.  The CLI path (``cli.py``) uses a local
synchronous variant — see ``_prompt_slash_confirm`` there.

### 顶层函数

#### def `register(session_key: str, confirm_id: str, command: str, handler: Callable[[str], Awaitable[Optional[str]]]) -> None`

Register a pending slash-command confirmation.

Overwrites any prior pending confirm for the same ``session_key`` — the
user invoking a new confirmable command supersedes the stale one.

#### def `get_pending(session_key: str) -> Optional[Dict[str, Any]]`

Return the pending confirm dict for a session, or None.

#### def `clear(session_key: str) -> None`

Drop the pending confirm for ``session_key`` without running it.

#### def `clear_if_stale(session_key: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> bool`

Drop the pending confirm if older than ``timeout`` seconds.

Returns True if an entry was dropped.

#### def `resolve(session_key: str, confirm_id: str, choice: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[str]`

Resolve a pending confirm.

``choice`` must be one of ``"once"``, ``"always"``, or ``"cancel"``.
Returns the handler's output string (to be sent as a follow-up
message), or ``None`` if the confirm was stale, already resolved, or
the confirm_id doesn't match.

Safe to call from an asyncio callback (button click) or from the
gateway's message intercept path.

#### def `resolve_sync_compat(loop: asyncio.AbstractEventLoop, session_key: str, confirm_id: str, choice: str) -> Optional[str]`

Synchronous helper: schedule resolve() on a loop and wait for the result.

Used by platform callback paths that run on a different thread than the
event loop (e.g. Discord's button click handler in some configurations).
Prefer the async ``resolve()`` from an async context.


## tools.terminal_tool

### 模块文档

Terminal Tool Module

A terminal tool that executes commands in local, Docker, Modal, SSH,
Singularity, and Daytona environments. Supports local execution,
containerized backends, and cloud sandboxes, including managed Modal mode.

Supported environments:
- "local": Execute directly on the host machine (default, fastest)
- "docker": Execute in Docker containers (isolated, requires Docker)
- "modal": Execute in Modal cloud sandboxes (direct Modal or managed gateway)

Features:
- Multiple execution backends (local, docker, modal)
- Background task support
- VM/container lifecycle management
- Automatic cleanup after inactivity

Cloud sandbox note:
- Persistent filesystems preserve working state across sandbox recreation
- Persistent filesystems do NOT guarantee the same live sandbox or long-running processes survive cleanup, idle reaping, or Hermes exit

Usage:
    from terminal_tool import terminal_tool

    # Execute a simple command
    result = terminal_tool("ls -la")

    # Execute in background
    result = terminal_tool("python server.py", background=True)

### 顶层函数

#### def `set_sudo_password_callback(cb)`

Register a callback for sudo password prompts (used by CLI).

Per-thread scope — ACP sessions that run concurrently in a
ThreadPoolExecutor each have their own callback slot.

#### def `set_approval_callback(cb)`

Register a callback for dangerous command approval prompts.

Per-thread scope — ACP sessions that run concurrently in a
ThreadPoolExecutor each have their own callback slot. See
GHSA-qg5c-hvr5-hjgr.

#### def `record_session_cwd(session_key: Optional[str], cwd: Optional[str]) -> None`

Record *cwd* as the working directory of *session_key*.

Called wherever a session's live cwd becomes known: after a terminal
command completes (the env's post-command tracking has just parsed the
resulting cwd) and when a surface registers a workspace cwd override.
Empty/None session keys collapse to ``"default"`` (single-session CLI).
Non-string / empty cwds are ignored.

#### def `get_session_cwd(session_key: Optional[str]) -> Optional[str]`

Return the recorded working directory for *session_key*, if any.

No fallback chain here on purpose: callers decide what an absent record
means (config default, TERMINAL_CWD seed, process cwd). ``None``/empty
keys read the ``"default"`` record.

#### def `clear_session_cwd(session_key: str) -> None`

Drop a session's cwd record (session teardown).

#### def `register_task_env_overrides(task_id: str, overrides: Dict[str, Any])`

Register environment overrides for a specific task/rollout.

Called by Atropos environments before the agent loop to configure
per-task sandbox settings (e.g., a custom Dockerfile for the Modal image).

Supported override keys:
    - modal_image: str -- Path to Dockerfile or Docker Hub image name
    - docker_image: str -- Docker image name
    - cwd: str -- Working directory inside the sandbox

Args:
    task_id: The rollout's unique task identifier
    overrides: Dict of config keys to override

#### def `clear_task_env_overrides(task_id: str)`

Clear environment overrides for a task after rollout completes.

Called during cleanup to avoid stale entries accumulating.

#### def `resolve_task_overrides(task_id: Optional[str]) -> Dict[str, Any]`

Return the env overrides for *task_id*, raw key first then collapsed.

``register_task_env_overrides`` writes under the *raw* task/session id, but
a CWD-only override collapses (:func:`_resolve_container_task_id`) to the
shared ``"default"`` container so per-session surfaces (ACP/gateway/
dashboard) don't each spin up their own sandbox. Callers that need the
override (terminal command setup, file-tool cwd resolution) must therefore
read the raw id FIRST and only fall back to the collapsed container id, or
the originating session's override is silently dropped. This is the single
source of that lookup so the terminal and file layers can't drift apart.

#### def `get_active_env(task_id: str)`

Return the active BaseEnvironment for *task_id*, or None.

#### def `is_persistent_env(task_id: str) -> bool`

Return True if the active environment for task_id is configured for
cross-turn persistence (``persistent_filesystem=True``).

Used by the agent loop to skip per-turn teardown for backends whose whole
point is to survive between turns (docker with ``container_persistent``,
daytona, modal, etc.). Non-persistent backends (e.g. Morph) still get torn
down at end-of-turn to prevent leakage. The idle reaper
(``_cleanup_inactive_envs``) handles persistent envs once they exceed
``terminal.lifetime_seconds``.

#### def `cleanup_all_environments()`

Clean up ALL active environments. Use with caution.

#### def `cleanup_vm(task_id: str, force_remove: bool = False)`

Manually clean up a specific environment by task_id.

*force_remove* (default False) is forwarded to backends that accept it
— currently only ``DockerEnvironment``. The default of False matches
session-lifecycle semantics: this function is called from
``AIAgent.close()`` (TUI session close, gateway session teardown) and the
per-turn cleanup branch for non-persistent envs, both of which should
honor the user's persist-mode preference. Stopping the container here
would defeat the "ONE long-lived container shared across sessions"
contract — exactly the bug Ben reported when the container was killed
on every TUI session close.

Pass ``force_remove=True`` for actual user-initiated teardown
(e.g. ``/reset``-style flows that haven't been wired yet, or future
"destroy my sandbox" commands).

The idle reaper passes the env through ``env.cleanup()`` directly (not
via this function), so persist-mode idle envs are similarly no-op'd —
only the orphan reaper at next startup reclaims them.

#### def `terminal_tool(command: str, background: bool = False, timeout: Optional[int] = None, task_id: Optional[str] = None, session_id: Optional[str] = None, force: bool = False, workdir: Optional[str] = None, pty: bool = False, notify_on_complete: bool = False, watch_patterns: Optional[List[str]] = None) -> str`

Execute a command in the configured terminal environment.

Args:
    command: The command to execute
    background: Whether to run in background (default: False)
    timeout: Command timeout in seconds (default: from config)
    task_id: Unique identifier for environment isolation (optional)
    session_id: Conversation/session identifier for durable observability
    force: If True, skip dangerous command check (use after user confirms)
    workdir: Working directory for this command (optional, uses session cwd if not set)
    pty: If True, use pseudo-terminal for interactive CLI tools (local backend only)
    notify_on_complete: If True and background=True, you'll be notified exactly once when the process exits. The right choice for almost every long task. MUTUALLY EXCLUSIVE with watch_patterns.
    watch_patterns: List of strings to watch for in background output. HARD rate limit: 1 notification per 15s per process. After 3 strike windows in a row, watch_patterns is disabled and the session is auto-promoted to notify_on_complete. Use ONLY for rare, one-shot mid-process signals on long-lived processes (server readiness, migration-done markers). NEVER use in loops/batch jobs — error patterns there will hit the strike limit and get disabled. MUTUALLY EXCLUSIVE with notify_on_complete — set one, not both.

Returns:
    str: JSON string with output, exit_code, and error fields

Examples:
    # Execute a simple command
    >>> result = terminal_tool(command="ls -la /tmp")

    # Run a background task
    >>> result = terminal_tool(command="python server.py", background=True)

    # With custom timeout
    >>> result = terminal_tool(command="long_task.sh", timeout=300)
    
    # Force run after user confirmation
    # Note: force parameter is internal only, not exposed to model API

#### def `check_terminal_requirements() -> bool`

Check if all requirements for the terminal tool are met.


## tools.thread_context

### 模块文档

Propagate agent-turn context into worker threads that dispatch Hermes tools.

A bare ``threading.Thread`` / ``ThreadPoolExecutor`` worker starts with an
empty ``contextvars.Context`` and no thread-local approval/sudo callbacks.
Tool dispatch inside such a thread therefore silently loses:

  * the approval *session/platform* ContextVars (``tools.approval`` /
    ``gateway.session_context``) — so gateway sessions fall into
    ``check_dangerous_command``'s non-interactive auto-approve branch and
    dangerous commands run without prompting (#33057, #30882);
  * the thread-local CLI approval/sudo callbacks (``tools.terminal_tool``) —
    so ``prompt_dangerous_approval`` cannot reach the user
    (GHSA-qg5c-hvr5-hjgr, #15216).

This helper factors out that capture/install/clear lifecycle so the several
places that fan tool dispatch onto worker threads (``agent.tool_executor`` and
the ``execute_code`` RPC threads) share one audited implementation instead of
divergent copies.

Usage — call :func:`propagate_context_to_thread` **on the parent thread**
(it snapshots the parent's ContextVars and callbacks at call time) and use the
returned callable as the worker's target::

    t = threading.Thread(target=propagate_context_to_thread(loop_fn), args=(...))
    # or
    executor.submit(propagate_context_to_thread(worker_fn), *args)

Approval/sudo callbacks are installed for the worker's lifetime and **always
cleared on exit**, so a recycled thread never holds a stale reference to a
disposed CLI instance.

### 顶层函数

#### def `propagate_context_to_thread(target: Callable) -> Callable`

Wrap *target* for execution on a worker thread with the *current*
thread's ContextVars and approval/sudo callbacks propagated.

Call this on the parent thread; pass the returned callable as the
thread/executor target.  The returned callable forwards its positional
and keyword arguments to *target* and returns its result.

Fail-closed: if callback installation raises, the callbacks are left
unset (``None``).  That is the safe outcome — ``prompt_dangerous_approval``
denies dangerous commands when no callback is registered in an interactive
context, and the gateway approval queue blocks when its notify callback is
absent.


## tools.threat_patterns

### 模块文档

Shared threat-pattern library for context window security scanning.

This module is the single source of truth for prompt-injection / promptware /
exfiltration patterns used across the context-assembly scanners
(``agent/prompt_builder.py``, ``tools/memory_tool.py``) and the tool-result
delimiter system in ``agent/tool_dispatch_helpers.py``.

Pattern philosophy
------------------
Patterns are organized by ATTACK CLASS, not by source file.  Each pattern
is a ``(regex, pattern_id, scope)`` tuple, where ``scope`` controls which
scanners use it:

- ``"all"``  — applied everywhere (classic prompt injection, exfiltration)
- ``"context"`` — applied to context files + memory + tool results
  (promptware / C2 / behavioral hijack; broader detection)
- ``"strict"`` — applied to memory writes + skill installs only
  (aggressive checks acceptable for user-curated content but too noisy
  for tool results)

The split exists because tool results contain web pages, GitHub issues,
and MCP responses — content the user did not author — and we want broad
detection there, but blocking is reserved for paths where the user can
intervene (memory writes, skill installs).

Pattern anchoring
-----------------
New patterns anchor on **C2-specific vocabulary or unambiguous attack
behavior**, NOT on bossy English.  Phrases like "you are obligated to"
or "you must" alone are too common in legitimate instruction-writing
(see AGENTS.md, CLAUDE.md, etc.) to flag.  See the pattern comments for
the rationale on borderline cases.

Multi-word bypass
-----------------
Patterns use bounded ``(?:\w+\s+){0,8}`` filler between key tokens to prevent
attackers from inserting a handful of words (e.g. "ignore all prior
instructions" instead of "ignore all instructions") without allowing unbounded
regex backtracking. This mirrors the fix applied to ``skills_guard.py`` in
commit 4ea29978.

### 顶层函数

#### def `scan_for_threats(content: str, scope: str = 'context') -> List[str]`

Return a list of matched pattern IDs in ``content`` at the given scope.

``scope`` selects which pattern set to apply:

- ``"all"`` (narrow): classic injection + exfil only — minimal false
  positives, suitable for any text.
- ``"context"`` (default): adds promptware / C2 / role-play patterns —
  suitable for context files, memory entries, and tool results.
- ``"strict"`` (broad): adds persistence / SSH backdoor / exfil-URL
  patterns — appropriate for user-mediated writes (memory tool,
  skills install) where false positives can be resolved interactively.

Also checks for invisible unicode characters (returned as
``"invisible_unicode_U+XXXX"`` so the caller can surface the offending
codepoint in a log line).

**异常**: `ValueError`

#### def `first_threat_message(content: str, scope: str = 'strict') -> Optional[str]`

Return a human-readable error string for the first threat found, or None.

Convenience wrapper used by paths that block on the first hit
(memory tool writes, skills install) where the caller just needs a
yes/no + a message.


## tools.tirith_security

### 模块文档

Tirith pre-exec security scanning wrapper.

Runs the tirith binary as a subprocess to scan commands for content-level
threats (homograph URLs, pipe-to-interpreter, terminal injection, etc.).

Exit code is the verdict source of truth:
  0 = allow, 1 = block, 2 = warn

JSON stdout enriches findings/summary but never overrides the verdict.
Operational failures (spawn error, timeout, unknown exit code) respect
the fail_open config setting. Programming errors propagate.

Auto-install: if tirith is not found on PATH or at the configured path,
it is automatically downloaded from GitHub releases to $HERMES_HOME/bin/tirith.
The download always verifies SHA-256 checksums.  When cosign is available on
PATH, provenance verification (GitHub Actions workflow signature) is also
performed.  If cosign is not installed, the download proceeds with SHA-256
verification only — still secure via HTTPS + checksum, just without supply
chain provenance proof.  Installation runs in a background thread so startup
never blocks.

### 顶层函数

#### def `is_platform_supported() -> bool`

True when tirith ships a prebuilt binary for this OS+arch.

Used by callers (CLI banner, etc.) to distinguish "tirith failed to
install" from "tirith was never going to install here" — the latter
is silent because there is nothing the user can do about it.

#### def `ensure_installed(log_failures: bool = True)`

Ensure tirith is available, downloading in background if needed.

Quick PATH/local checks are synchronous; network download runs in a
daemon thread so startup never blocks. Safe to call multiple times.
Returns the resolved path immediately if available, or None.

#### def `check_command_security(command: str) -> dict`

Run tirith security scan on a command.

Exit code determines action (0=allow, 1=block, 2=warn). JSON enriches
findings/summary. Spawn failures and timeouts respect fail_open config.
Programming errors propagate.

Returns:
    {"action": "allow"|"warn"|"block", "findings": [...], "summary": str}


## tools.todo_tool

### 模块文档

Todo Tool Module - Planning & Task Management

Provides an in-memory task list the agent uses to decompose complex tasks,
track progress, and maintain focus across long conversations. The state
lives on the AIAgent instance (one per session) and is re-injected into
the conversation after context compression events.

Design:
- Single `todo` tool: provide `todos` param to write, omit to read
- Every call returns the full current list
- No system prompt mutation, no tool response modification
- Behavioral guidance lives entirely in the tool schema description

### class TodoStore

> 继承: `object` ｜ 方法数: 8（公开 4）

In-memory todo list. One instance per AIAgent (one per session).

Items are ordered -- list position is priority. Each item has:
  - id: unique string identifier (agent-chosen)
  - content: task description
  - status: pending | in_progress | completed | cancelled

#### def `__init__()`

#### def `write(self, todos: List[Dict[str, Any]], merge: bool = False) -> List[Dict[str, str]]`

Write todos. Returns the full current list after writing.

Args:
    todos: list of {id, content, status} dicts
    merge: if False, replace the entire list. If True, update
           existing items by id and append new ones.

#### def `read(self) -> List[Dict[str, str]]`

Return a copy of the current list.

#### def `has_items(self) -> bool`

Check if there are any items in the list.

#### def `format_for_injection(self) -> Optional[str]`

Render the todo list for post-compression injection.

Returns a human-readable string to append to the compressed
message history, or None if the list is empty.


### 顶层函数

#### def `todo_tool(todos: Optional[List[Dict[str, Any]]] = None, merge: bool = False, store: Optional[TodoStore] = None) -> str`

Single entry point for the todo tool. Reads or writes depending on params.

Args:
    todos: if provided, write these items. If None, read current list.
    merge: if True, update by id. If False (default), replace entire list.
    store: the TodoStore instance from the AIAgent.

Returns:
    JSON string with the full current list and summary metadata.

#### def `check_todo_requirements() -> bool`

Todo tool has no external requirements -- always available.


## tools.tool_backend_helpers

### 模块文档

Shared helpers for tool backend selection.

### 顶层函数

#### def `managed_nous_tools_enabled(force_fresh: bool = False) -> bool`

Return True when the user is entitled to the Nous Tool Gateway.

Entitlement is paid Nous Portal service access OR a live free tool pool
(``tool_gateway_entitled``). Per-category coverage (the pool funds image but
not video, etc.) is narrowed by callers via ``tool_gateway_entitled_for``;
this coarse gate only answers "is any managed tool usable at all".

Tool Gateway availability fails closed on unknown/error entitlement.  We
intentionally catch all exceptions and return False — never block startup.
``force_fresh=True`` is for interactive configuration flows that should
reflect a just-purchased subscription, credits, or pool grant immediately.

#### def `nous_tool_gateway_unavailable_message(capability: str = 'the Nous Tool Gateway', force_fresh: bool = False) -> str`

Return account-aware guidance for an unavailable Nous Tool Gateway path.

#### def `normalize_browser_cloud_provider(value: object | None) -> str`

Return a normalized browser provider key.

#### def `coerce_modal_mode(value: object | None) -> str`

Return the requested modal mode when valid, else the default.

#### def `normalize_modal_mode(value: object | None) -> str`

Return a normalized modal execution mode.

#### def `has_direct_modal_credentials() -> bool`

Return True when direct Modal credentials/config are available.

#### def `resolve_modal_backend_state(modal_mode: object | None, has_direct: bool, managed_ready: bool, managed_enabled: bool | None = None) -> Dict[str, Any]`

Resolve direct vs managed Modal backend selection.

Semantics:
- ``direct`` means direct-only
- ``managed`` means managed-only
- ``auto`` prefers managed when available, then falls back to direct

#### def `resolve_openai_audio_api_key() -> str`

Prefer the voice-tools key, but fall back to the normal OpenAI key.

#### def `prefers_gateway(config_section: str) -> bool`

Return True when the user opted into the Tool Gateway for this tool.

Reads ``<section>.use_gateway`` from config.yaml.  Never raises.

#### def `fal_key_is_configured() -> bool`

Return True when FAL_KEY is set to a non-whitespace value.

Consults both ``os.environ`` and ``~/.hermes/.env`` (via
``hermes_cli.config.get_env_value`` when available) so tool-side
checks and CLI setup-time checks agree.  A whitespace-only value
is treated as unset everywhere.


## tools.tool_output_limits

### 模块文档

Configurable tool-output truncation limits.

Ported from anomalyco/opencode PR #23770 (``feat(truncate): allow
configuring tool output truncation limits``).

OpenCode hardcoded ``MAX_LINES = 2000`` and ``MAX_BYTES = 50 * 1024``
as tool-output truncation thresholds. Hermes-agent had the same
hardcoded constants in two places:

* ``tools/terminal_tool.py`` — ``MAX_OUTPUT_CHARS = 50000`` (terminal
  stdout/stderr cap)
* ``tools/file_operations.py`` — ``MAX_LINES = 2000`` /
  ``MAX_LINE_LENGTH = 2000`` (read_file pagination cap + per-line cap)

This module centralises those values behind a single config section
(``tool_output`` in ``config.yaml``) so power users can tune them
without patching the source. The existing hardcoded numbers remain as
defaults, so behaviour is unchanged when the config key is absent.

Example ``config.yaml``::

    tool_output:
      max_bytes: 100000        # terminal output cap (chars)
      max_lines: 5000          # read_file pagination + truncation cap
      max_line_length: 2000    # per-line length cap before '... [truncated]'

The limits reader is defensive: any error (missing config file, invalid
value type, etc.) falls back to the built-in defaults so tools never
fail because of a malformed config.

### 顶层函数

#### def `get_tool_output_limits() -> Dict[str, int]`

Return resolved tool-output limits, reading ``tool_output`` from config.

Keys: ``max_bytes``, ``max_lines``, ``max_line_length``. Missing or
invalid entries fall through to the ``DEFAULT_*`` constants. This
function NEVER raises.

Result is cached for the process lifetime to avoid repeated disk I/O
on every tool call. Call ``_reset_tool_output_limits_cache()`` in
tests that need a fresh read after config changes.

#### def `get_max_bytes() -> int`

Shortcut for terminal-tool callers that only need the byte cap.

#### def `get_max_lines() -> int`

Shortcut for file-ops callers that only need the line cap.

#### def `get_max_line_length() -> int`

Shortcut for file-ops callers that only need the per-line cap.


## tools.tool_result_storage

### 模块文档

Tool result persistence -- preserves large outputs instead of truncating.

Defense against context-window overflow operates at three levels:

1. **Per-tool output cap** (inside each tool): Tools like search_files
   pre-truncate their own output before returning. This is the first line
   of defense and the only one the tool author controls.

2. **Per-result persistence** (maybe_persist_tool_result): After a tool
   returns, if its output exceeds the tool's registered threshold
   (registry.get_max_result_size), the full output is written INTO THE
   SANDBOX temp dir (for example /tmp/hermes-results/{tool_use_id}.txt on
   standard Linux, or $TMPDIR/hermes-results/{tool_use_id}.txt on Termux)
   via env.execute(). The in-context content is replaced with a preview +
   file path reference. The model can read_file to access the full output
   on any backend.

3. **Per-turn aggregate budget** (enforce_turn_budget): After all tool
   results in a single assistant turn are collected, if the total exceeds
   MAX_TURN_BUDGET_CHARS (200K), the largest non-persisted results are
   spilled to disk until the aggregate is under budget. This catches cases
   where many medium-sized results combine to overflow context.

### 顶层函数

#### def `generate_preview(content: str, max_chars: int = DEFAULT_PREVIEW_SIZE_CHARS) -> tuple[str, bool]`

Truncate at last newline within max_chars. Returns (preview, has_more).

#### def `maybe_persist_tool_result(content: str, tool_name: str, tool_use_id: str, env = None, config: BudgetConfig = DEFAULT_BUDGET, threshold: int | float | None = None) -> str`

Layer 2: persist oversized result into the sandbox, return preview + path.

Writes via env.execute() so the file is accessible from any backend
(local, Docker, SSH, Modal, Daytona). Falls back to inline truncation
if write fails or no env is available.

Args:
    content: Raw tool result string.
    tool_name: Name of the tool (used for threshold lookup).
    tool_use_id: Unique ID for this tool call (used as filename).
    env: The active BaseEnvironment instance, or None.
    config: BudgetConfig controlling thresholds and preview size.
    threshold: Explicit override; takes precedence over config resolution.

Returns:
    Original content if small, or <persisted-output> replacement.

#### def `enforce_turn_budget(tool_messages: list[dict], env = None, config: BudgetConfig = DEFAULT_BUDGET) -> list[dict]`

Layer 3: enforce aggregate budget across all tool results in a turn.

If total chars exceed budget, persist the largest non-persisted results
first (via sandbox write) until under budget. Already-persisted results
are skipped.

Mutates the list in-place and returns it.


## tools.tool_search

### 模块文档

Progressive tool disclosure ("tool search") for Hermes Agent.

When enabled, MCP and non-core plugin tools are replaced in the model-visible
tools array by three bridge tools — ``tool_search``, ``tool_describe``,
``tool_call`` — and surfaced on demand. Core Hermes tools never defer.

Design constraints this module is built around (see ``openclaw-tool-search-report``
for the full rationale):

* Core tools defined in ``toolsets._HERMES_CORE_TOOLS`` are *never* deferred.
  Always-load means always-load. No exceptions.
* The threshold gate runs every assembly: when deferrable tools would consume
  less than ``threshold_pct`` of the model's context window (default 10%),
  tool search is a no-op and the tools array passes through unchanged.
* The catalog is stateless across turns and tools-array assemblies. It is
  rebuilt from the current tool-defs list every time. This is the lesson
  from OpenClaw's cron regression (openclaw/openclaw#84141): a session-keyed
  catalog that drifts out of sync with the live tool registry produces
  silent tool dropouts.
* Bridge tools route through ``model_tools.handle_function_call`` exactly
  like a direct call, so guardrails, plugin pre/post hooks, approval flows,
  and tool-result truncation all fire identically.
* Display and trajectory unwrap is implemented here so the user (CLI activity
  feed, gateway, saved trajectories) always sees the underlying tool, not
  the bridge.

### class ToolSearchConfig

> 继承: `object` ｜ 方法数: 1（公开 1）

Resolved, validated tool-search configuration for a single assembly.

#### classmethod `from_raw(cls, raw: Any) -> ToolSearchConfig`

Build a config from a raw dict / bool / None.

Accepts the legacy bool shape (``tools.tool_search: true``) and the
dict shape (``tools.tool_search: {enabled: auto, ...}``). Validates
and clamps every numeric field; unknown values fall back to safe
defaults rather than raising, so a typo in user config does not
break the agent.


### class CatalogEntry

> 继承: `object` ｜ 方法数: 0（公开 0）

One deferrable tool, in a form the bridge tools can search and serve.


### class AssemblyResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Outcome of one assembly. Useful for tests and observability.


### 顶层函数

#### def `load_config() -> ToolSearchConfig`

Load tool-search config from the user config file.

#### def `is_deferrable_tool_name(name: str) -> bool`

Return True if a tool with this name is *eligible* for deferral.

A tool is deferrable iff it is registered with an MCP toolset prefix
OR it is not in ``_HERMES_CORE_TOOLS``. Core tools are never deferred
even when their toolset is technically plugin-provided (this protects
against accidental shadowing).

#### def `classify_tools(tool_defs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]`

Split a tool-defs list into (visible, deferrable).

``visible`` retains every tool that must stay in the model-facing array:
every core tool, plus any tool we can't classify. ``deferrable`` is the
candidate set for catalog entry.

#### def `estimate_tokens_from_schemas(tool_defs: Iterable[Dict[str, Any]]) -> int`

Estimate the token cost of a tool-defs list via the chars/4 rule.

Cheap and stable across providers. The number doesn't need to be exact —
it gates the activate/skip decision, and a typical 200K context with a
10% threshold means the decision flips around 20K tokens of schema.
Order-of-magnitude precision is fine.

#### def `should_activate(config: ToolSearchConfig, deferrable_tokens: int, context_length: Optional[int]) -> bool`

Decide whether tool search should activate for the current assembly.

``"off"`` skips unconditionally. ``"on"`` activates unconditionally
(as long as there is at least one deferrable tool — there's no point
swapping a no-op). ``"auto"`` activates when the deferrable schemas
would consume ``threshold_pct`` of context or more.

#### def `build_catalog(tool_defs: List[Dict[str, Any]]) -> List[CatalogEntry]`

Build the deferred-tool catalog from a tool-defs list.

Caller is expected to pass only the deferrable subset (``classify_tools``
returns it as the second element).

#### def `search_catalog(catalog: List[CatalogEntry], query: str, limit: int = 5) -> List[CatalogEntry]`

Return the top-``limit`` catalog entries for ``query`` by BM25.

Falls back to a stable name-substring match when BM25 yields no hits
above zero. That ensures a query like ``"github"`` against a catalog
where every tool is named ``github_*`` still returns results — BM25
can underperform when query and document share only one token that
appears in every document (zero IDF).

#### def `bridge_tool_schemas(deferred_count: int) -> List[Dict[str, Any]]`

Build the bridge tool schemas to inject in place of deferred tools.

The schemas are intentionally short — every byte added here is a byte
the user pays on every turn. Descriptions are tuned to be unambiguous
about the call sequence the model should follow.

#### def `assemble_tool_defs(tool_defs: List[Dict[str, Any]], context_length: Optional[int] = None, config: Optional[ToolSearchConfig] = None) -> AssemblyResult`

Return the tool-defs list the model should actually see.

When tool search is inactive (off, no deferrable tools, or below
threshold), this is a passthrough. When active, MCP and plugin tools
are stripped from the visible list and replaced with the three bridge
tools. Core tools are *never* deferred regardless of config.

Idempotent: calling with bridge tools already in the input is a no-op
(they classify as non-core/non-deferrable but their names are reserved,
so they are filtered out of the deferrable set).

#### def `is_bridge_tool(name: str) -> bool`

#### def `dispatch_tool_search(args: Dict[str, Any], current_tool_defs: List[Dict[str, Any]], config: Optional[ToolSearchConfig] = None) -> str`

Execute the ``tool_search`` bridge tool. Returns a JSON string.

#### def `dispatch_tool_describe(args: Dict[str, Any], current_tool_defs: List[Dict[str, Any]]) -> str`

Execute the ``tool_describe`` bridge tool. Returns a JSON string.

#### def `scoped_deferrable_names(tool_defs: List[Dict[str, Any]]) -> frozenset[str]`

Return the set of deferrable tool names present in ``tool_defs``.

``tool_defs`` is expected to be the *pre-assembly* tool list for the
current session's toolset scope (i.e. what
``get_tool_definitions(skip_tool_search_assembly=True)`` returns for the
session's enabled/disabled toolsets). The resulting set is the universe of
tools the session may legitimately reach through ``tool_call``. Used as a
scoping gate by both the ``model_tools`` bridge dispatch and the
``tool_executor`` unwrap so a restricted-toolset session can never invoke
an out-of-scope tool via the bridge.

#### def `resolve_underlying_call(args: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any], Optional[str]]`

Parse a ``tool_call`` invocation into (underlying_name, args, error_msg).

Used by:
* the dispatcher in ``model_tools.handle_function_call``,
* the display layer (so the activity feed shows the underlying tool),
* the trajectory recorder.

On parse error, returns ``(None, {}, error_message)``.


## tools.transcription_tools

### 模块文档

Transcription Tools Module

Provides speech-to-text transcription with six providers:

  - **local** (default, free) — faster-whisper running locally, no API key needed.
    Auto-downloads the model (~150 MB for ``base``) on first use.
  - **groq** (free tier) — Groq Whisper API, requires ``GROQ_API_KEY``.
  - **openai** (paid) — OpenAI Whisper API, requires ``VOICE_TOOLS_OPENAI_KEY``.
  - **mistral** — Mistral Voxtral Transcribe API, requires ``MISTRAL_API_KEY``.
  - **xai** — xAI Grok STT API, requires ``XAI_API_KEY``. High accuracy,
    Inverse Text Normalization, diarization, 21 languages.
  - **elevenlabs** — ElevenLabs Scribe API, requires ``ELEVENLABS_API_KEY``.

Used by the messaging gateway to automatically transcribe voice messages
sent by users on Telegram, Discord, WhatsApp, Slack, and Signal.

Supported input formats: mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg, aac

Usage::

    from tools.transcription_tools import transcribe_audio

    result = transcribe_audio("/path/to/audio.ogg")
    if result["success"]:
        print(result["transcript"])

### 顶层函数

#### def `get_env_value(name, default = None)`

Read env values through the live config module.

Tests may monkeypatch and later restore ``hermes_cli.config.get_env_value``
before this module is imported. Resolve the helper at call time so STT does
not keep a stale imported function for the rest of the test process.

#### def `is_stt_enabled(stt_config: Optional[dict] = None) -> bool`

Return whether STT is enabled in config.

#### def `transcribe_audio(file_path: str, model: Optional[str] = None) -> Dict[str, Any]`

Transcribe an audio file using the configured STT provider.

Provider priority:
  1. User config (``stt.provider`` in config.yaml)
  2. Auto-detect: local > Groq > OpenAI > Mistral > xAI > ElevenLabs

Args:
    file_path: Absolute path to the audio file to transcribe.
    model:     Override the model. If None, uses config or provider default.

Returns:
    dict with keys:
      - "success" (bool): Whether transcription succeeded
      - "transcript" (str): The transcribed text (empty on failure)
      - "error" (str, optional): Error message if success is False
      - "provider" (str, optional): Which provider was used


## tools.tts_tool

### 模块文档

Text-to-Speech Tool Module

Built-in TTS providers:
- Edge TTS (default, free, no API key): Microsoft Edge neural voices
- ElevenLabs (premium): High-quality voices, needs ELEVENLABS_API_KEY
- OpenAI TTS: Good quality, needs OPENAI_API_KEY
- MiniMax TTS: High-quality with voice cloning, needs MINIMAX_API_KEY
- Mistral (Voxtral TTS): Multilingual, native Opus, needs MISTRAL_API_KEY
- Google Gemini TTS: Controllable, 30 prebuilt voices, needs GEMINI_API_KEY
- xAI TTS: Grok voices, uses xAI Grok OAuth credentials or XAI_API_KEY
- NeuTTS (local, free, no API key): On-device TTS via neutts
- KittenTTS (local, free, no API key): On-device 25MB model
- Piper (local, free, no API key): OHF-Voice/piper1-gpl neural VITS, 44 languages

Custom command providers:
- Users can declare any number of named providers with ``type: command``
  under ``tts.providers.<name>`` in ``~/.hermes/config.yaml``. Hermes
  writes the input text to a temp file and runs the configured shell
  command, which must produce the audio file at the expected path.
  See the Local Command section of ``website/docs/user-guide/features/tts.md``.

Output formats:
- Opus (.ogg) for Telegram voice bubbles (requires ffmpeg for Edge TTS)
- MP3 (.mp3) for everything else (CLI, Discord, WhatsApp)

Configuration is loaded from ~/.hermes/config.yaml under the 'tts:' key.
The user chooses the provider and voice; the model just sends text.

Usage:
    from tools.tts_tool import text_to_speech_tool, check_tts_requirements

    result = text_to_speech_tool(text="Hello world")

### 顶层函数

#### def `get_env_value(name, default = None)`

Read env values through the live config module.

Tests may monkeypatch and later restore ``hermes_cli.config.get_env_value``
before this module is imported. Resolve the helper at call time so TTS does
not keep a stale imported function for the rest of the test process.

#### def `text_to_speech_tool(text: str, output_path: Optional[str] = None) -> str`

Convert text to speech audio.

Reads provider/voice config from ~/.hermes/config.yaml (tts: section).
The model sends text; the user configures voice and provider.

On messaging platforms, the returned MEDIA:<path> tag is intercepted
by the send pipeline and delivered as a native voice message.
In CLI mode, the file is saved to ~/voice-memos/.

Args:
    text: The text to convert to speech.
    output_path: Optional custom save path. Defaults to ~/voice-memos/<timestamp>.mp3

Returns:
    str: JSON result with success, file_path, and optionally MEDIA tag.

#### def `check_tts_requirements() -> bool`

Return whether the explicitly resolved TTS provider can run.

Availability must mirror :func:`text_to_speech_tool` dispatch. Unrelated
cloud credentials do not make the default Edge backend usable, and an
explicitly selected backend is checked on its own requirements.

#### def `stream_tts_to_speaker(text_queue: queue.Queue, stop_event: threading.Event, tts_done_event: threading.Event, display_callback: Optional[Callable[[str], None]] = None)`

Consume text deltas from *text_queue*, buffer them into sentences,
and stream each sentence through ElevenLabs TTS to the speaker in
real-time.

Protocol:
    * The producer puts ``str`` deltas onto *text_queue*.
    * A ``None`` sentinel signals end-of-text (flush remaining buffer).
    * *stop_event* can be set to abort early (e.g. user interrupt).
    * *tts_done_event* is **set** in the ``finally`` block so callers
      waiting on it (continuous voice mode) know playback is finished.


## tools.url_safety

### 模块文档

URL safety checks — blocks requests to private/internal network addresses.

Prevents SSRF (Server-Side Request Forgery) where a malicious prompt or
skill could trick the agent into fetching internal resources like cloud
metadata endpoints (169.254.169.254), localhost services, or private
network hosts.

The check can be globally disabled via ``security.allow_private_urls: true``
in config.yaml for environments where DNS resolves external domains to
private/benchmark-range IPs (OpenWrt routers, corporate proxies, VPNs
that use 198.18.0.0/15 or 100.64.0.0/10).  Even when disabled, cloud
metadata hostnames (metadata.google.internal, 169.254.169.254) are
**always** blocked — those are never legitimate agent targets.

Limitations (documented, not fixable at pre-flight level):
  - DNS rebinding (TOCTOU): an attacker-controlled DNS server with TTL=0
    can return a public IP for the check, then a private IP for the actual
    connection. Fixing this requires connection-level validation (e.g.
    Python's Champion library or an egress proxy like Stripe's Smokescreen).
  - Redirect-based bypass is mitigated by httpx event hooks that re-validate
    each redirect target in vision_tools, gateway platform adapters, and
    media cache helpers. Web tools use third-party SDKs (Firecrawl/Tavily)
    where redirect handling is on their servers.

### 顶层函数

#### def `normalize_url_for_request(url: str) -> str`

Return an ASCII-safe HTTP URL for Hermes-owned URL tools.

Browsers and HTTP clients expect URIs, but users and models often provide
IRIs such as ``https://wttr.in/Köln``.  Preserve URL syntax and existing
percent escapes while encoding non-ASCII host/path/query/fragment text.
This is intentionally for URL tool inputs only; arbitrary shell commands
must not be rewritten.

#### def `sensitive_query_param_name(url: str) -> Optional[str]`

Return the first sensitive query parameter name in ``url``, if any.

Used before handing URLs to third-party fetch/browser backends. Prefix-based
token redaction catches known credential shapes; this catches opaque magic
links, OAuth codes, signed URL signatures, and custom ``?token=...`` values
that do not have a recognizable vendor prefix.

#### def `has_sensitive_query_params(url: str) -> bool`

Return True when ``url`` carries likely credential-bearing query params.

#### def `is_always_blocked_url(url: str) -> bool`

Return True when the URL targets an always-blocked endpoint.

This is the security floor — cloud metadata IPs / hostnames
(169.254.169.254, metadata.google.internal, ECS task metadata, etc.)
that have no legitimate agent use regardless of backend, routing, or
the ``allow_private_urls`` toggle.  Used by callers that bypass the
full ``is_safe_url`` check for their own reasons (e.g. hybrid cloud
browser routing to a local Chromium sidecar for private URLs) and
still need to enforce the non-negotiable floor before letting the
request proceed.

Returns True (= blocked) on:
  - Hostnames in ``_BLOCKED_HOSTNAMES``
  - IPs / networks in ``_ALWAYS_BLOCKED_IPS`` / ``_ALWAYS_BLOCKED_NETWORKS``
  - URLs whose hostname resolves to any of the above

Returns False (= not in the always-blocked floor) on:
  - Benign public / private / loopback URLs (whether or not they'd
    be blocked by the ordinary SSRF check)
  - DNS-resolution failures for non-sentinel hostnames (these are
    someone else's problem — the caller's ordinary fail-closed path
    will catch them if applicable)
  - Parse errors (caller decides fail-open vs fail-closed)

Intentionally narrower than ``is_safe_url``: only blocks the sentinel
set, not ordinary private addresses.  Callers that want the full
SSRF check should still use ``is_safe_url``.

#### def `is_safe_url(url: str) -> bool`

Return True if the URL target is not a private/internal address.

Resolves the hostname to an IP and checks against private ranges.
Fails closed: DNS errors and unexpected exceptions block the request.

When ``security.allow_private_urls`` is enabled (or the env var
``HERMES_ALLOW_PRIVATE_URLS=true``), private-IP blocking is skipped.
Cloud metadata endpoints (169.254.169.254, metadata.google.internal)
remain blocked regardless — they are never legitimate agent targets.

#### def `async_is_safe_url(url: str) -> bool`

Same rules as :func:`is_safe_url`, but run the DNS work off the event loop.

``socket.getaddrinfo`` can block; call this from async code paths (gateway,
``web_extract_tool``, vision download hooks) instead of ``is_safe_url``.

#### def `redirect_target_from_response(response: Any) -> Optional[str]`

Return the redirect target visible from inside an httpx response hook.

In ``httpx.AsyncClient`` response event hooks, ``response.next_request`` is
frequently ``None`` even for a genuine redirect (it is populated later by
the redirect-following machinery). Relying on ``next_request`` alone means
an SSRF redirect guard silently never fires: a public URL that 302s to
``http://169.254.169.254/`` gets followed anyway. The ``Location`` header,
however, is already present on the response, so resolve the target from it
first (handling relative Locations via ``urljoin``) and only fall back to
``next_request`` when no ``Location`` header is set.


## tools.video_generation_tool

### 模块文档

Video Generation Tool
=====================

Single ``video_generate`` tool that dispatches to a plugin-registered
video generation provider. Mirrors the ``image_generate`` design:

- ``agent/video_gen_provider.py`` defines the :class:`VideoGenProvider` ABC.
- ``agent/video_gen_registry.py`` holds the active providers (populated by
  plugins at import time).
- Each provider lives under ``plugins/video_gen/<name>/``.

The tool itself is intentionally backend-agnostic and ships **no in-tree
provider** — turn on a backend by enabling a plugin (``hermes plugins
enable video_gen/<name>``) and selecting it in ``hermes tools`` → Video
Generation.

Unified surface
---------------
One tool covers the common cases - text-to-video, image-to-video, and
reference-to-video - with a compact schema:

    prompt                   text instruction (required)
    image_url                drives image-to-video
    reference_image_urls     list, up to provider-declared cap
    duration                 seconds (provider clamps)
    aspect_ratio             "16:9" | "9:16" | "1:1" | ...
    resolution               "480p" | "540p" | "720p" | "1080p"
    negative_prompt          optional (Pixverse/Kling style)
    audio                    optional (Veo3/Pixverse pricing tier)
    seed                     optional
    model                    optional, override the active provider's default

Providers ignore parameters they do not support. The tool layer does
**lightweight** validation (type/required-prompt) and lets each provider
do its own clamping inside :meth:`VideoGenProvider.generate` — that keeps
the tool surface stable as new providers ship with different capabilities.

Video edit and video extend are intentionally not exposed here; providers with
those workflows should expose separate tools.

### 顶层函数

#### def `check_video_generation_requirements() -> bool`

Return True when at least one registered provider reports available.

Triggers plugin discovery (idempotent) so user-installed plugins are
visible to the toolset gate.


## tools.vision_tools

### 模块文档

Vision Tools Module

This module provides vision analysis tools that work with image URLs.
Uses the centralized auxiliary vision router, which can select OpenRouter,
Nous, Codex, native Anthropic, or a custom OpenAI-compatible endpoint.

Available tools:
- vision_analyze_tool: Analyze images from URLs with custom prompts

Features:
- Downloads images from URLs and converts to base64 for API compatibility
- Comprehensive image description
- Context-aware analysis based on user queries
- Automatic temporary file cleanup
- Proper error handling and validation
- Debug logging support

Usage:
    from vision_tools import vision_analyze_tool
    import asyncio
    
    # Analyze an image
    result = await vision_analyze_tool(
        image_url="https://example.com/image.jpg",
        user_prompt="What architectural style is this building?"
    )

### 顶层函数

#### def `vision_analyze_tool(image_url: str, user_prompt: str, model: str = None, task_id: Optional[str] = None) -> str`

Analyze an image from a URL or local file path using vision AI.

This tool accepts either an HTTP/HTTPS URL or a local file path. For URLs,
it downloads the image first. In both cases, the image is converted to base64
and processed using Gemini 3 Flash Preview via OpenRouter API.

The user_prompt parameter is expected to be pre-formatted by the calling
function (typically model_tools.py) to include both full description
requests and specific questions.

Args:
    image_url (str): The URL or local file path of the image to analyze.
                     Accepts http://, https:// URLs or absolute/relative file paths.
    user_prompt (str): The pre-formatted prompt for the vision model
    model (str): The vision model to use (default: google/gemini-3-flash-preview)

Returns:
    str: JSON string containing the analysis results with the following structure:
         {
             "success": bool,
             "analysis": str (defaults to error message if None)
         }

Raises:
    Exception: If download fails, analysis fails, or API key is not set
    
Note:
    - For URLs, temporary images are stored under $HERMES_HOME/cache/vision/ and cleaned up
    - For local file paths, the file is used directly and NOT deleted
    - Supports common image formats (JPEG, PNG, GIF, WebP, etc.)

**异常**: `Exception`, `Note`, `ValueError`

#### def `check_vision_requirements() -> bool`

Check if the configured runtime vision path can resolve a client.

Mirrors the fallback chain that ``call_llm(task="vision")`` actually uses
at runtime: first the explicit ``auxiliary.vision.provider`` (if any),
and if that fails, the auto chain (main provider → openrouter → nous).
Without the auto-fallback step the tool would disappear from the model's
tool list whenever the explicit provider name was unresolvable, even
when the auto chain would have served the request (issue #31179).

#### def `video_analyze_tool(video_url: str, user_prompt: str, model: str = None) -> str`

Analyze a video via multimodal LLM. Returns JSON {success, analysis}.

**异常**: `ValueError`, `PermissionError`


## tools.voice_mode

### 模块文档

Voice Mode -- Push-to-talk audio recording and playback for the CLI.

Provides audio capture via sounddevice, WAV encoding via stdlib wave,
STT dispatch via tools.transcription_tools, and TTS playback via
sounddevice or system audio players.

Dependencies (optional):
    pip install sounddevice numpy
    or: pip install hermes-agent[voice]

### class TermuxAudioRecorder

> 继承: `object` ｜ 方法数: 9（公开 7）

Recorder backend that uses Termux:API microphone capture commands.

#### def `__init__() -> None`

#### property `is_recording(self) -> bool`

#### property `elapsed_seconds(self) -> float`

#### property `current_rms(self) -> int`

#### def `start(self, on_silence_stop = None) -> None`

**异常**: `RuntimeError`

#### def `stop(self) -> Optional[str]`

#### def `cancel(self) -> None`

#### def `shutdown(self) -> None`


### class AudioRecorder

> 继承: `object` ｜ 方法数: 11（公开 7）

Thread-safe audio recorder using sounddevice.InputStream.

Usage::

    recorder = AudioRecorder()
    recorder.start(on_silence_stop=my_callback)
    # ... user speaks ...
    wav_path = recorder.stop()   # returns path to WAV file
    # or
    recorder.cancel()            # discard without saving

If ``on_silence_stop`` is provided, recording automatically stops when
the user is silent for ``silence_duration`` seconds and calls the callback.

#### def `__init__() -> None`

#### property `elapsed_seconds(self) -> float`

#### property `current_rms(self) -> int`

Current audio input RMS level (0-32767). Updated each audio chunk.

#### property `is_recording(self) -> bool`

Whether audio recording is currently active.

#### def `start(self, on_silence_stop = None) -> None`

Start capturing audio from the default input device.

The underlying InputStream is created once and kept alive across
recordings.  Subsequent calls simply reset detection state and
toggle frame collection via ``_recording``.

Args:
    on_silence_stop: Optional callback invoked (in a daemon thread) when
        silence is detected after speech. The callback receives no arguments.
        Use this to auto-stop recording and trigger transcription.

Raises ``RuntimeError`` if sounddevice/numpy are not installed
or if a recording is already in progress.

**异常**: `RuntimeError`

#### def `stop(self) -> Optional[str]`

Stop recording and write captured audio to a WAV file.

The underlying stream is kept alive for reuse — only frame
collection is stopped.

Returns:
    Path to the WAV file, or ``None`` if no audio was captured.

#### def `cancel(self) -> None`

Stop recording and discard all captured audio.

The underlying stream is kept alive for reuse.

#### def `shutdown(self) -> None`

Release the audio stream.  Call when voice mode is disabled.


### 顶层函数

#### def `detect_audio_environment() -> dict`

Detect if the current environment supports audio I/O.

Returns dict with 'available' (bool), 'warnings' (list of hard-fail
reasons that block voice mode), and 'notices' (list of informational
messages that do NOT block voice mode).

#### def `play_beep(frequency: int = 880, duration: float = 0.12, count: int = 1) -> None`

Play a short beep tone using numpy + sounddevice.

Args:
    frequency: Tone frequency in Hz (default 880 = A5).
    duration: Duration of each beep in seconds.
    count: Number of beeps to play (with short gap between).

#### def `create_audio_recorder() -> AudioRecorder | TermuxAudioRecorder`

Return the best recorder backend for the current environment.

#### def `is_whisper_hallucination(transcript: str) -> bool`

Check if a transcript is a known Whisper hallucination on silence.

#### def `transcribe_recording(wav_path: str, model: Optional[str] = None) -> Dict[str, Any]`

Transcribe a WAV recording using the existing Whisper pipeline.

Delegates to ``tools.transcription_tools.transcribe_audio()``.
Filters out known Whisper hallucinations on silent audio.

Args:
    wav_path: Path to the WAV file.
    model: Whisper model name (default: from config or ``whisper-1``).

Returns:
    Dict with ``success``, ``transcript``, and optionally ``error``.

#### def `stop_playback() -> None`

Interrupt the currently playing audio (if any).

#### def `play_audio_file(file_path: str) -> bool`

Play an audio file through the default output device.

Strategy:
1. WAV files via ``sounddevice.play()`` when available.
2. System commands: ``afplay`` (macOS), ``ffplay`` (cross-platform),
   ``aplay`` (Linux ALSA).

Playback can be interrupted by calling ``stop_playback()``.

Returns:
    ``True`` if playback succeeded, ``False`` otherwise.

#### def `check_voice_requirements() -> Dict[str, Any]`

Check if all voice mode requirements are met.

Returns:
    Dict with ``available``, ``audio_available``, ``stt_available``,
    ``missing_packages``, and ``details``.

#### def `cleanup_temp_recordings(max_age_seconds: int = 3600) -> int`

Remove old temporary voice recording files.

Args:
    max_age_seconds: Delete files older than this (default: 1 hour).

Returns:
    Number of files deleted.


## tools.web_tools

### 模块文档

Standalone Web Tools Module

This module provides generic web tools that work with multiple backend providers.
Backend is selected during ``hermes tools`` setup (web.backend in config.yaml).
When available, Hermes can route Firecrawl calls through a Nous-hosted tool-gateway
for Nous Subscribers only.

Available tools:
- web_search_tool: Search the web for information
- web_extract_tool: Extract content from specific web pages

Backend compatibility:
- Exa: https://exa.ai (search, extract)
- Firecrawl: https://docs.firecrawl.dev/introduction (search, extract; direct or derived firecrawl-gateway.<domain> for Nous Subscribers)
- Parallel: https://docs.parallel.ai (search, extract)
- Tavily: https://tavily.com (search, extract)

LLM Processing:
- Uses OpenRouter API with Gemini 3 Flash Preview for intelligent content extraction
- Extracts key excerpts and creates markdown summaries to reduce token usage

Debug Mode:
- Set WEB_TOOLS_DEBUG=true to enable detailed logging
- Creates web_tools_debug_UUID.json in ./logs directory
- Captures all tool calls, results, and compression metrics

Usage:
    from web_tools import web_search_tool, web_extract_tool
    
    # Search the web
    results = web_search_tool("Python machine learning libraries", limit=3)
    
    # Extract content from URLs  
    content = web_extract_tool(["https://example.com"], format="markdown")

### 顶层函数

#### def `convert_base64_images_to_links(text: str) -> str`

Replace inline base64 image blobs with labeled markdown links.

base64 image payloads are token bombs (a single inline PNG can be tens of
thousands of characters), so we never send the raw bytes to the model. But
we preserve the fact that an image was there, and its alt text, as an
inspectable placeholder. Real (http/https) markdown image links are left
untouched so the agent can ``web_extract`` / ``vision_analyze`` them.

Transformations:
  ``![alt](data:image/png;base64,AAAA...)``  -> ``[IMAGE: alt](base64 image omitted)``
  ``(data:image/png;base64,AAAA...)``        -> ``[IMAGE]``
  bare ``data:image/...;base64,AAAA...``     -> ``[IMAGE]``

#### def `web_search_tool(query: str, limit: int = 5) -> str`

Search the web for information using available search API backend.

This function provides a generic interface for web search that can work
with multiple backends (Parallel or Firecrawl).

Note: This function returns search result metadata only (URLs, titles, descriptions).
Use web_extract_tool to get full content from specific URLs.

Args:
    query (str): The search query to look up
    limit (int): Maximum number of results to return (default: 5)

Returns:
    str: JSON string containing search results with the following structure:
         {
             "success": bool,
             "data": {
                 "web": [
                     {
                         "title": str,
                         "url": str,
                         "description": str,
                         "position": int
                     },
                     ...
                 ]
             }
         }

Raises:
    Exception: If search fails or API key is not set

**异常**: `Exception`

#### def `web_extract_tool(urls: List[Any], format: str = None, char_limit: Optional[int] = None) -> str`

Extract content from specific web pages using available extraction API backend.

Returns clean page content (markdown/text) with NO LLM summarization. The
extract backends (Firecrawl, Tavily, Exa, Parallel) already return clean,
boilerplate-stripped content, so we return it directly and fast. Pages over
``char_limit`` are head+tail truncated with an explicit footer; the full
text is stored under cache/web and the footer tells the model how to
read_file the omitted middle. Inline base64 images are replaced with
``[IMAGE: alt]`` placeholders (real image URLs are preserved as links).

Args:
    urls (List[Any]): URL strings or search-result objects containing a
        string ``url`` or ``href`` field
    format (str): Desired output format ("markdown" or "html", optional)
    char_limit (Optional[int]): Per-page char budget sent to the model
        (default: web.extract_char_limit or 15000). Larger pages truncate.

Security: URLs are checked for embedded secrets before fetching.

Returns:
    str: JSON string with a ``results`` list; each entry has
         ``url``, ``title``, ``content``, ``error``. ``content`` is the
         (possibly truncated) clean page text.

Raises:
    Exception: If extraction fails or API key is not set

**异常**: `Exception`

#### def `check_web_api_key() -> bool`

Check whether the configured web backend is available.

Used as the ``check_fn`` gate for the ``web_search`` and ``web_extract``
tool registry entries — so a plugin-registered provider that reports
``is_available()`` must light the tools up even when no built-in backend
has credentials (issues #28651, #31873). Resolution funnels through
:func:`_is_backend_available`, which delegates non-legacy names to the
registry.


## tools.website_policy

### 模块文档

Website access policy helpers for URL-capable tools.

This module loads a user-managed website blocklist from ~/.hermes/config.yaml
and optional shared list files. It is intentionally lightweight so web/browser
tools can enforce URL policy without pulling in the heavier CLI config stack.

Policy is cached in memory with a short TTL so config changes take effect
quickly without re-reading the file on every URL check.

### class WebsitePolicyError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Raised when a website policy file is malformed.


### 顶层函数

#### def `load_website_blocklist(config_path: Optional[Path] = None) -> Dict[str, Any]`

Load and return the parsed website blocklist policy.

Results are cached for ``_CACHE_TTL_SECONDS`` to avoid re-reading
config.yaml on every URL check.  Pass an explicit ``config_path``
to bypass the cache (used by tests).

**异常**: `WebsitePolicyError`

#### def `invalidate_cache() -> None`

Force the next ``check_website_access`` call to re-read config.

#### def `check_website_access(url: str, config_path: Optional[Path] = None) -> Optional[Dict[str, str]]`

Check whether a URL is allowed by the website blocklist policy.

Returns ``None`` if access is allowed, or a dict with block metadata
(``host``, ``rule``, ``source``, ``message``) if blocked.

Never raises on policy errors — logs a warning and returns ``None``
(fail-open) so a config typo doesn't break all web tools.  Pass
``config_path`` explicitly (tests) to get strict error propagation.


## tools.write_approval

### 模块文档

Write-approval gate + pending store for memory and skill writes.

Background
----------
The agent writes to two persistent stores that survive across sessions:

  * **memory** — MEMORY.md / USER.md, small (~200 char) declarative entries
  * **skills** — SKILL.md + supporting files, potentially huge (10-100 KB)

Both stores are written from two origins:

  * **foreground** — a normal agent turn (user is present / chatting)
  * **background_review** — the self-improvement review fork that runs after a
    turn and autonomously decides what to save (the source of the
    "wrong assumptions" users complained about)

This module lets the user gate those writes per-subsystem with a boolean
``write_approval``:

  * ``false`` (default) — write freely (the pre-gate behaviour)
  * ``true``            — require approval: do not commit the write; either
    prompt inline (memory, interactive CLI only) or **stage** it to a pending
    store and surface it for the user to approve or reject out-of-band

The size asymmetry between memory and skills is real and unavoidable: a memory
entry can be reviewed inline in a chat bubble; a 100 KB SKILL.md cannot. So
the gate stages BOTH to disk, but review affordances differ by subsystem
(see ``hermes_cli`` slash handlers): memory shows full content, skills show
metadata + a one-line gist + a ``diff`` escape hatch (CLI/dashboard/file).

Staging is mandatory for background-origin writes (a daemon thread cannot
block on an interactive prompt) and for gateway sessions (no inline prompt
channel — review happens via ``/memory pending``). Foreground CLI memory
writes prompt inline via the dangerous-command approval callback; skill
writes always stage (too big to eyeball mid-loop).

Pending records live under ``<HERMES_HOME>/pending/{memory,skills}/<id>.json``
so they survive process restarts and can be reviewed from CLI, gateway, or the
web dashboard.

### class GateDecision

> 继承: `object` ｜ 方法数: 1（公开 0）

Result of evaluating the write gate for a single write attempt.

Exactly one of the boolean flags is True:
  * ``allow``  — proceed with the real write (gate off, or an inline
    approval was granted).
  * ``blocked`` — refuse the write (the user denied an inline approval
    prompt). ``message`` explains why; surface it to the agent.
  * ``stage``  — do not write; the caller should stage the payload via
    ``stage_write`` (gate on, and no inline prompt is available — gateway,
    background review, script, or any skill write). ``message`` is the
    user-facing "staged for approval" note.

#### def `__init__(allow = False, blocked = False, stage = False, message = '')`


### 顶层函数

#### def `write_approval_enabled(subsystem: str) -> bool`

Return whether the approval gate is enabled for ``subsystem``.

Reads ``<subsystem>.write_approval`` from config.yaml. Defaults to
``False`` (gate off — writes flow freely) for any unset / invalid value so
existing installs keep their current behaviour until the user opts in.

#### def `stage_write(subsystem: str, payload: Dict[str, Any], summary: str, origin: str) -> Dict[str, Any]`

Persist a pending write and return a short record describing it.

Args:
    subsystem: ``memory`` or ``skills``.
    payload: the exact kwargs needed to replay the write when approved
        (e.g. ``{"action": "add", "target": "user", "content": "..."}``
        for memory, or the full ``skill_manage`` kwargs for skills).
    summary: a one-line human-readable description shown in pending lists.
        For skills this is the LLM/heuristic gist; for memory it can be the
        entry text itself.
    origin: ``foreground`` or ``background_review`` — recorded for audit.

Returns a dict with ``id`` and metadata. Best-effort: on disk failure it
logs and still returns a record (the write is simply lost, which is the
safe failure for an approval gate — nothing is silently committed).

#### def `list_pending(subsystem: str) -> List[Dict[str, Any]]`

Return all pending records for ``subsystem``, oldest first.

#### def `get_pending(subsystem: str, pending_id: str) -> Optional[Dict[str, Any]]`

Return a single pending record by id, or None.

#### def `discard_pending(subsystem: str, pending_id: str) -> bool`

Delete a pending record. Returns True if it existed.

#### def `pending_count(subsystem: str) -> int`

Cheap count of pending records (for notification badges).

#### def `current_origin() -> str`

Return the active write origin: ``foreground`` or ``background_review``.

Reuses the skill-provenance ContextVar, which the background review fork
already sets (see ``agent.background_review`` /
``AIAgent._spawn_background_review``). Foreground agent turns leave it at
the default ``foreground``.

#### def `is_background() -> bool`

#### def `evaluate_gate(subsystem: str, inline_summary: str = '', inline_detail: str = '') -> GateDecision`

Decide what to do with a pending write for ``subsystem``.

Args:
    subsystem: ``memory`` or ``skills``.
    inline_summary: short description used as the inline approval prompt
        header (memory foreground path only).
    inline_detail: full content shown in the inline prompt (memory entries
        are small; skills never take the inline path).

Decision matrix:
    gate off (default)                    → allow (writes flow freely)
    gate on, memory + interactive CLI     → inline approve/deny prompt
    gate on, memory + gateway/script/bg   → stage
    gate on, skills (any origin)          → stage (too big to review inline)

Note: there is no config-driven "blocked" outcome — the gate only ever
delays a write for approval, never silently refuses it. ``blocked`` is
still produced when the user *actively denies* an inline prompt.

#### def `skill_gist(action: str, name: str, content: str = '', file_path: str = '', old_string: str = '', new_string: str = '') -> str`

Build a one-line human gist for a pending skill write.

Heuristic, no model call — the gist surfaces enough to decide approve/reject
in a chat bubble, while the full diff stays behind /skills diff (CLI/
dashboard/file). For create/edit it pulls the frontmatter ``description:``;
for patch/write_file it describes the size of the change.

#### def `skill_pending_diff(record: Dict[str, Any]) -> str`

Build a full unified diff (or full content) for a staged skill write.

Used by /skills diff <id> on a surface that can render it (CLI pager, web
dashboard, or by opening the pending JSON file). For create this is the new
file content; for edit/patch it is a unified diff against the current
on-disk skill.


## tools.x_search_tool

### 模块文档

X Search tool backed by xAI's built-in ``x_search`` Responses API tool.

Authentication
--------------
The tool registers when **either** xAI credential path is available:

* ``XAI_API_KEY`` is set in ``~/.hermes/.env`` or the process environment
  (paid xAI API key), OR
* The user is signed in via xAI Grok OAuth — SuperGrok subscription —
  i.e. ``hermes auth add xai-oauth`` has been run and the stored refresh
  token still works.

Credential preference at call time matches
:func:`tools.xai_http.resolve_xai_http_credentials`: SuperGrok OAuth first,
direct OAuth resolver second, ``XAI_API_KEY`` last. That helper also
auto-refreshes the OAuth access token when it's within the refresh skew
window, so a ``True`` from :func:`check_x_search_requirements` means the
bearer is fetchable AND non-empty.

Defensive output
----------------
The tool surfaces two additional signals beyond xAI's raw response so callers
can tell a real citation-backed answer from an unsourced one:

* ``from_date`` / ``to_date`` are validated client-side before the HTTP call.
  Malformed (non ``YYYY-MM-DD``), inverted (``from_date > to_date``), and
  pure-future ranges (``from_date`` later than today UTC) fail fast with a
  clear error instead of burning an API call. ``to_date`` in the future is
  still allowed so callers can legitimately request "from yesterday to
  tomorrow".
* Successful responses carry ``degraded`` and ``degraded_reason`` fields.
  ``degraded`` is ``True`` when any narrowing filter (handles or dates) was
  active AND xAI returned no citations in either the top-level ``citations``
  array or the inline ``url_citation`` annotations. In that case the
  ``answer`` came from the model's own knowledge rather than the X index,
  and the caller should treat the result as unsourced.

Salvaged from PR #10786 (originally by @Jaaneek); credential resolution
reworked to honor both auth modes per Teknium's design.

### 顶层函数

#### def `check_x_search_requirements() -> bool`

Return True when xAI credentials are available AND valid.

``resolve_xai_http_credentials`` calls
:func:`hermes_cli.auth.resolve_xai_oauth_runtime_credentials` which
auto-refreshes the OAuth access token if it's expiring; a successful
return therefore implies a usable bearer.

#### def `x_search_tool(query: str, allowed_x_handles: Optional[List[str]] = None, excluded_x_handles: Optional[List[str]] = None, from_date: str = '', to_date: str = '', enable_image_understanding: bool = False, enable_video_understanding: bool = False) -> str`

**异常**: `RuntimeError`


## tools.xai_http

### 模块文档

Shared helpers for direct xAI HTTP integrations.

### 顶层函数

#### def `has_xai_credentials() -> bool`

Cheap probe — return True when xAI credentials are *likely* usable.

Deliberately avoids :func:`resolve_xai_http_credentials` so callers in
hot-paint paths (``hermes tools`` repaint, tool-registration scans,
``WebSearchProvider.is_available()``) don't incur disk locks or — in
the OAuth path — a network token refresh. The ABC contract on
:meth:`agent.web_search_provider.WebSearchProvider.is_available`
explicitly forbids network calls for exactly this reason.

Resolution order, fast-to-slow:

1. ``XAI_API_KEY`` env var (cheapest; covers explicit-key users).
2. ``~/.hermes/auth.json`` has a non-empty ``providers.xai-oauth.tokens.access_token``
   (single file read, no expiry check, no refresh).
3. ``credential_pool.xai-oauth`` has any entry with a non-empty
   ``access_token`` (covers multi-account ``hermes auth add xai-oauth``
   grants that are pool-only / ``manual:device_code``).

Returns False on any exception so a corrupted auth store can't block
other availability scans. Truthful refresh + expiry handling happens
in ``search()`` (or whichever caller actually makes the request).

#### def `get_env_value(name: str, default = None)`

Read ``name`` from ``~/.hermes/.env`` first, then ``os.environ``.

Wraps :func:`hermes_cli.config.get_env_value` so tests can patch
``tools.xai_http.get_env_value`` to inject dotenv-only secrets into the
xAI credential resolver.

#### def `hermes_xai_user_agent() -> str`

Return a stable Hermes-specific User-Agent for xAI HTTP calls.

#### def `read_xai_imagine_storage_config(section_name: str) -> Dict[str, Any]`

Read storage settings for xAI Imagine under image_gen/video_gen config.

Supported config shape:

    image_gen:
      xai:
        storage:
          enabled: true
          public_url: true
          expires_after: null     # omit for permanent public URLs

The same shape is accepted under ``video_gen.xai.storage``. Storage is on
by default so xAI returns permanent public URLs instead of short-lived CDN URLs.

#### def `build_xai_storage_options(section_name: str, filename_prefix: str, extension: str) -> Optional[Dict[str, Any]]`

Return an xAI ``storage_options`` payload, or None when disabled.

#### def `xai_storage_notice_text(section_name: str) -> str`

User-facing notice for first xAI Imagine storage use.

#### def `maybe_mark_xai_storage_notice_seen(section_name: str) -> Optional[str]`

Return the storage notice once per Hermes home, then mark it seen.

#### def `resolve_xai_http_credentials(force_refresh: bool = False, api_key_hint: Optional[str] = None) -> Dict[str, str]`

Resolve bearer credentials for direct xAI HTTP endpoints.

Prefers Hermes-managed xAI OAuth credentials when available, then falls back
to ``XAI_API_KEY`` resolved via ``hermes_cli.config.get_env_value`` so keys
stored in ``~/.hermes/.env`` (the standard Hermes location) are honored —
not just ones already exported into ``os.environ``. This keeps direct xAI
endpoints (images, TTS, STT, etc.) aligned with the main runtime auth model
and preserves the regression contract from PR #17140 / #17163.

Set ``force_refresh=True`` to perform an unconditional OAuth refresh.
Reactive callers should also pass the rejected bearer as ``api_key_hint``
so a freshly loaded multi-account pool refreshes the exact issuing entry,
not whichever entry its strategy would otherwise select first.


## tools.xai_video_tools

### 模块文档

xAI-specific Imagine video edit and extend tools.

## tools.yuanbao_tools

### 模块文档

yuanbao_tools.py - 元宝平台工具集

提供以下工具函数，供 hermes-agent 的 "hermes-yuanbao" toolset 使用：
  - get_group_info        : 查询群基本信息（群名、群主、成员数）
  - query_group_members   : 查询群成员（按名搜索、列举 bot、列举全部）
  - search_sticker        : 按关键词搜索内置贴纸（返回候选列表，含 sticker_id/name/description）
  - send_sticker          : 向当前会话或指定 chat_id 发送贴纸（TIMFaceElem）
  - send_dm               : 发送私聊消息（按昵称查找用户并发送）

对齐 chatbot-web/yuanbao-openclaw-plugin 的 sticker-search/sticker-send 行为：
LLM 应先用 search_sticker 找到合适的 sticker_id（或直接传中文 name），再用 send_sticker
发送。不要在文本中夹杂裸的 Unicode emoji 当作贴纸。

The active adapter singleton lives in ``gateway.platforms.yuanbao`` and is
accessed via ``get_active_adapter()``.

### 顶层函数

#### def `get_group_info(group_code: str) -> dict`

查询群基本信息（群名、群主、成员数）。

#### def `query_group_members(group_code: str, action: str = 'list_all', name: str = '', mention: bool = False) -> dict`

统一的群成员查询工具（对齐 TS query_session_members）。

action:
  - find      : 按昵称模糊搜索
  - list_bots : 列出 bot 和元宝 AI
  - list_all  : 列出全部成员

#### def `search_sticker(query: str = '', limit: int = 10) -> dict`

在内置贴纸表中按关键词模糊搜索，返回 Top-N 候选。

返回每条候选的 sticker_id / name / description / package_id，
供 LLM 选择后传给 send_sticker。空 query 时返回前 N 条。

#### def `send_sticker(sticker: str = '', chat_id: str = '', reply_to: str = '') -> dict`

向 chat_id（缺省取当前会话）发送一张内置贴纸（TIMFaceElem）。

Args:
    sticker:   贴纸名称（如 "六六六"）或 sticker_id（如 "278"）。为空时随机发送一张。
    chat_id:   目标会话；缺省时使用当前会话上下文（HERMES_SESSION_CHAT_ID）。
               格式：``direct:{account_id}`` / ``group:{group_code}`` / 或裸 account_id。
    reply_to:  群聊场景的引用消息 ID（可选）。

Returns: ``{"success": bool, ...}``

#### def `send_dm(group_code: str, name: str, message: str, user_id: str = '', media_files: Optional[List[Tuple[str, bool]]] = None) -> dict`

Send a DM (private chat message) to a group member, with optional media.

Workflow:
  1. If user_id is provided, send directly.
  2. Otherwise, search the group member list by name to resolve user_id.
  3. Send text via adapter.send_dm(), then iterate media_files by extension.

Args:
    group_code: The group where the target user belongs.
    name: Target user's nickname (partial match, case-insensitive).
    message: The message text to send.
    user_id: (Optional) If already known, skip the member lookup.
    media_files: (Optional) List of (file_path, is_voice) tuples to send
                 after the text message.  Images are sent via
                 send_image_file; everything else via send_document.

