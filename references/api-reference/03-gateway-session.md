# gateway.session — 会话数据模型

> **模块**: `gateway/session.py`
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: Hermes Gateway 的会话存储与上下文模型。

## 模块文档

Session management for the gateway.

Handles:
- Session context tracking (where messages come from)
- Session storage (conversations persisted to disk)
- Reset policy evaluation (when to start fresh)
- Dynamic system prompt injection (agent knows its context)

### 模块文档

Session management for the gateway.

Handles:
- Session context tracking (where messages come from)
- Session storage (conversations persisted to disk)
- Reset policy evaluation (when to start fresh)
- Dynamic system prompt injection (agent knows its context)

### class SessionSource

> 继承: `object` ｜ 方法数: 4（公开 3）

Describes where a message originated from.

This information is used to:
1. Route responses back to the right place
2. Inject context into the system prompt
3. Track origin for cron job delivery

#### property `description(self) -> str`

Human-readable description of the source.

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> SessionSource`


### class SessionContext

> 继承: `object` ｜ 方法数: 1（公开 1）

Full context for a session, used for dynamic system prompt injection.

The agent receives this information to understand:
- Where messages are coming from
- What platforms are available
- Where it can deliver scheduled task outputs

#### def `to_dict(self) -> Dict[str, Any]`


### class SessionEntry

> 继承: `object` ｜ 方法数: 2（公开 2）

Entry in the session store.

Maps a session key to its current session ID and metadata.

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> SessionEntry`

**异常**: `ValueError`


### class AsyncSessionStore

> 继承: `object` ｜ 方法数: 2（公开 0）

Async boundary for the synchronous, thread-safe SessionStore.

#### def `__init__(store: SessionStore) -> None`


### class SessionStore

> 继承: `object` ｜ 方法数: 52（公开 22）

Manages session storage and retrieval.

Uses SQLite (via SessionDB) for session metadata and message transcripts.
Falls back to legacy JSONL files if SQLite is unavailable.

#### def `__init__(sessions_dir: Path, config: GatewayConfig, has_active_processes_fn = None)`

#### def `set_expiry_finalized(self, entry: SessionEntry, clear_model_override: bool = True) -> None`

Mark a session entry expiry-finalized in memory, sessions.json, AND state.db.

Single write-path for the expiry watcher (#9006): keeps the durable
state.db flag in sync with the JSON routing index so the flag
survives sessions.json pruning/loss.

``clear_model_override=False`` preserves the give-up path's original
behavior (flag only, no override drop).

#### def `is_session_finalizable(self, entry: SessionEntry) -> bool`

Return True if the expiry watcher will *ever* finalize this session.

The expiry watcher (``GatewayRunner._session_expiry_watcher``) only
tears an agent down — and only then fires ``on_session_end`` — for
sessions whose reset policy eventually expires. A ``mode == "none"``
session never expires (``_is_session_expired`` returns ``False``
forever), so the watcher will never finalize it.

This distinction matters for the agent-cache idle sweep: deferring
idle eviction to "let the watcher finalize it later" is only correct
when the watcher WILL run for this session. For a ``mode == "none"``
session, deferring pins the cached agent in memory for the gateway's
entire lifetime with no finalization ever coming — the exact leak the
idle sweep exists to relieve. Callers use this predicate to decide
whether the session store owns the eviction boundary (finalizable) or
the idle sweep must still reap the agent itself (not finalizable).

Public wrapper so callers don't reach into policy internals. Errors
resolving the policy are treated as "not finalizable" (safe: the idle
sweep falls back to reaping the agent rather than pinning it).

#### def `has_any_sessions(self) -> bool`

Check if any sessions have ever been created (across all platforms).

Uses the SQLite database as the source of truth because it preserves
historical session records (ended sessions still count).  The in-memory
``_entries`` dict replaces entries on reset, so ``len(_entries)`` would
stay at 1 for single-platform users — which is the bug this fixes.

The current session is already in the DB by the time this is called
(get_or_create_session runs first), so we check ``> 1``.

#### def `get_or_create_session(self, source: SessionSource, force_new: bool = False) -> SessionEntry`

Single-flight session lookup/create per routing key.

Calls for different keys remain concurrent. Overlapping calls for the
same key share the owner's result, including concurrent ``force_new``
deliveries, so only one routing transition and SQLite row is created.

**异常**: `slot.error`

#### def `update_session(self, session_key: str, last_prompt_tokens: int = None) -> None`

Update lightweight session metadata after an interaction.

#### def `set_model_override(self, session_key: str, override: Optional[Dict[str, Any]]) -> None`

Persist (or clear) the session-scoped /model override.

Only non-secret keys (model/provider/base_url — see
``sanitize_model_override``) are written; ``api_key``/``api_mode``
are re-resolved at rehydration time via the normal runtime provider
resolution.  Pass ``None`` (or a dict with no persistable values)
to clear the persisted override, e.g. on /new.

#### def `get_model_override(self, session_key: str) -> Optional[Dict[str, str]]`

Return the persisted /model override for *session_key*, if any.

#### def `suspend_session(self, session_key: str) -> bool`

Mark a session as suspended so it auto-resets on next access.

Used by ``/stop`` to prevent stuck sessions from being resumed
after a gateway restart (#7536).  Returns True if the session
existed and was marked.

#### def `mark_resume_pending(self, session_key: str, reason: str = 'restart_timeout') -> bool`

Mark a session as resumable after a restart interruption.

Unlike ``suspend_session()``, this preserves the existing
``session_id`` and the transcript.  The next call to
``get_or_create_session()`` for this key returns the same entry
so the user auto-resumes on the same conversation lane.

Returns True if the session existed and was marked.

#### def `clear_resume_pending(self, session_key: str) -> bool`

Clear the resume-pending flag after a successful resumed turn.

Called from the gateway after ``run_conversation()`` returns a
final response for a session that had ``resume_pending=True``,
signalling that recovery succeeded.

Returns True if a flag was cleared.

#### def `prune_old_entries(self, max_age_days: int) -> int`

Drop SessionEntry records older than max_age_days.

Pruning is based on ``updated_at`` (last activity), not ``created_at``.
A session that's been active within the window is kept regardless of
how old it is.  Entries marked ``suspended`` are kept — the user
explicitly paused them for later resume.  Entries held by an active
process (via has_active_processes_fn) are also kept so long-running
background work isn't orphaned.

Pruning is functionally identical to a natural reset-policy expiry:
the transcript in SQLite stays, but the session_key → session_id
mapping is dropped and the user starts a fresh session on return.

``max_age_days <= 0`` disables pruning; returns 0 immediately.
Returns the number of entries removed.

#### def `suspend_recently_active(self, max_age_seconds: int = 120) -> int`

Mark recently-active sessions as resumable after an unexpected exit.

Called on gateway startup after a crash or fast restart to preserve
in-flight sessions instead of destroying their conversation history
(#7536).  Only marks sessions updated within *max_age_seconds* to
avoid touching long-idle sessions.  Sets ``resume_pending=True`` so
the next incoming message on the same session_key auto-resumes from
the existing transcript.

Entries already flagged ``resume_pending=True`` are skipped.  Entries
explicitly ``suspended=True`` (from /stop or stuck-loop escalation)
are also skipped.  Terminal escalation for genuinely stuck sessions
is still handled by the existing ``.restart_failure_counts`` counter
(threshold 3), which runs after this method and sets ``suspended=True``.

Returns the number of sessions marked resumable.

#### def `reset_session(self, session_key: str, display_name: Optional[str] = None) -> Optional[SessionEntry]`

Force reset a session, creating a new session ID.

#### def `switch_session(self, session_key: str, target_session_id: str) -> Optional[SessionEntry]`

Switch a session key to point at an existing session ID.

Used by ``/resume`` to restore a previously-named session.
Ends the current session in SQLite (like reset), but instead of
generating a fresh session ID, re-uses ``target_session_id`` so the
old transcript is loaded on the next message. If the target session was
previously ended, re-open it so gateway resume semantics match the CLI.

#### def `list_sessions(self, active_minutes: Optional[int] = None) -> List[SessionEntry]`

List all sessions, optionally filtered by activity.

#### def `lookup_by_session_id(self, session_id: str) -> Optional[SessionEntry]`

Return the active session entry for a persisted session ID, if any.

#### def `peek_session_id(self, session_key: str) -> Optional[str]`

Return the persisted session_id currently bound to a session key.

Public, lock-held accessor for the key→session_id mapping. Callers that
need to resolve the session row for a source (e.g. the webhook
delivery-close path) should use this rather than reaching into the
private ``_entries`` dict without holding ``self._lock``. Returns None
when the key is unknown or has no session_id yet.

#### def `append_to_transcript(self, session_id: str, message: Dict[str, Any], skip_db: bool = False) -> None`

Append a message to a session's transcript (SQLite).

Args:
    skip_db: When True, skip the SQLite write. Used when the agent
             already persisted messages to SQLite via its own
             _flush_messages_to_session_db(), preventing the
             duplicate-write bug (#860).

#### def `has_platform_message_id(self, session_id: str, platform_message_id: str) -> bool`

Check if a message with the given platform_message_id is persisted.

Thin wrapper over SessionDB.has_platform_message_id(). Returns False
when no DB is available (in-memory sessions). Used by the gateway's
transient-failure dedupe guard (#47237).

#### def `rewrite_transcript(self, session_id: str, messages: List[Dict[str, Any]]) -> bool`

Replace the entire transcript for a session with new messages.

Used by /retry, /undo, and /compress to persist modified conversation
history. state.db is the canonical store.

Returns ``True`` when the write lands (or there is no DB to write to)
and ``False`` when the canonical write fails. Most callers can ignore
the result, but callers that would otherwise commit a destructive state
change on top of a failed write — e.g. /compress repointing the live
session onto a fresh session_id — must check it so they can surface an
error instead of silently dropping the conversation.

#### def `load_transcript(self, session_id: str) -> List[Dict[str, Any]]`

Load all messages from a session's transcript.

state.db is the canonical store. The legacy JSONL fallback was removed
in spec 002 — pre-DB sessions on existing disks have already been
migrated (their DB row holds the full message history).

#### def `rewind_session(self, session_id: str, n: int = 1) -> Optional[Dict[str, Any]]`

Back up ``n`` user turns via soft-delete, keeping rows for audit.

Unlike :meth:`rewrite_transcript` (a hard replace used by /retry),
this flips the truncated rows to ``active=0`` in state.db so they
survive for audit and stay hidden from re-prompts and search. Mirrors
the CLI/TUI ``/undo [N]`` behavior via ``SessionDB.rewind_to_message``.

Returns a dict ``{"rewound_count", "turns_undone", "target_text"}`` on
success, or ``None`` if there's no DB or no user message to back up to.
``n`` clamps to the oldest user turn when it exceeds the turn count.


### 顶层函数

#### def `auto_continue_freshness_window() -> float`

Return the configured auto-continue freshness window in seconds.

Single source of truth for both the resume scheduler (``gateway/run.py``)
and the routing-time zombie gate in ``get_or_create_session``.  Reads
``HERMES_AUTO_CONTINUE_FRESHNESS`` (bridged from ``config.yaml``
``agent.gateway_auto_continue_freshness`` at gateway startup) and falls
back to the module default when unset or malformed.  A non-positive value
disables the freshness gate (restores the pre-fix "always fresh" behaviour
for users who want to opt out).

#### def `neutralize_untrusted_inline_text(value: Any, max_chars: int = _MAX_PROMPT_METADATA_CHARS) -> str`

Collapse untrusted text to a single inert line, unquoted.

Sibling of :func:`_format_untrusted_prompt_value` for call sites that must
preserve the surrounding format (e.g. an inline ``[Name] message turn``
prefix) instead of a standalone ``**Label:** "value"`` line — JSON-quoting
would visibly change a well-behaved value's rendering there.

Embedded newlines are the injection vector both helpers guard against:
they let an untrusted display name masquerade as a new markdown section
(a fake heading, an "## Override" block) inside content the model reads
every turn. Collapsing them to a single space keeps a normal value
byte-identical while making a hostile one visually inert.

#### def `build_session_context_prompt(context: SessionContext, redact_pii: bool = False) -> str`

Build the dynamic system prompt section that tells the agent about its context.

This is injected into the system prompt so the agent knows:
- Where messages are coming from
- What platforms are connected
- Where it can deliver scheduled task outputs

When *redact_pii* is True **and** the source platform is in
``_PII_SAFE_PLATFORMS``, phone numbers are stripped and user/chat IDs
are replaced with deterministic hashes before being sent to the LLM.
Platforms like Discord are excluded because mentions need real IDs.
Routing still uses the original values (they stay in SessionSource).

#### def `sanitize_model_override(override: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]`

Return a copy of *override* containing only persistable, non-secret keys.

Returns ``None`` when the input is empty/not a dict or no persistable
values remain, so callers can store the result directly on
``SessionEntry.model_override``.

#### def `is_shared_multi_user_session(source: SessionSource, group_sessions_per_user: bool = True, thread_sessions_per_user: bool = False) -> bool`

Return True when a non-DM session is shared across participants.

Mirrors the isolation rules in :func:`build_session_key`:
  - DMs are never shared.
  - Threads are shared unless ``thread_sessions_per_user`` is True.
  - Non-thread group/channel sessions are shared unless
    ``group_sessions_per_user`` is True (default: True = isolated).

#### def `build_session_key(source: SessionSource, group_sessions_per_user: bool = True, thread_sessions_per_user: bool = False, profile: Optional[str] = None) -> str`

Build a deterministic session key from a message source.

This is the single source of truth for session key construction.

``profile`` selects the key namespace (see :func:`_session_key_namespace`).
It defaults to ``None`` ⇒ the legacy ``agent:main`` namespace, so callers
that don't multiplex produce byte-identical keys to before. Only the
multiplexing gateway passes a non-default profile.

DM rules:
  - DMs include chat_id when present, so each private conversation is isolated.
  - thread_id further differentiates threaded DMs within the same DM chat.
  - Without chat_id, thread_id is used as a best-effort fallback.
  - Without thread_id or chat_id, DMs share a single session.

Group/channel rules:
  - chat_id identifies the parent group/channel.
  - user_id/user_id_alt isolates participants within that parent chat when available when
    ``group_sessions_per_user`` is enabled.
  - thread_id differentiates threads within that parent chat.  When
    ``thread_sessions_per_user`` is False (default), threads are *shared* across all
    participants — user_id is NOT appended, so every user in the thread
    shares a single session.  This is the expected UX for threaded
    conversations (Telegram forum topics, Discord threads, Slack threads).
  - Without participant identifiers, or when isolation is disabled, messages fall back to one
    shared session per chat.
  - Without identifiers, messages fall back to one session per platform/chat_type.

#### def `build_session_context(source: SessionSource, config: GatewayConfig, session_entry: Optional[SessionEntry] = None) -> SessionContext`

Build a full session context from a source and config.

This is used to inject context into the agent's system prompt.

