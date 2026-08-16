# gateway — 网关包（77 模块）

> **模块**: `gateway/`（包，共 77 个模块）
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: 网关：会话、运行、平台注册、流分发、投递、配置等。

## gateway.__init__

### 模块文档

Hermes Gateway - Multi-platform messaging integration.

This module provides a unified gateway for connecting the Hermes agent
to various messaging platforms (Telegram, Discord, WhatsApp, Weixin, and more) with:
- Session management (persistent conversations with reset policies)
- Dynamic context injection (agent knows where messages come from)
- Delivery routing (cron job outputs to appropriate channels)
- Platform-specific toolsets (different capabilities per platform)

## gateway.authz_mixin

### 模块文档

User-authorization methods for ``GatewayRunner``.

Extracted from ``gateway/run.py`` as part of the god-file decomposition campaign
(``~/.hermes/plans/god-file-decomposition.md``, Phase 3 mechanical mixin lifts).
This mixin holds the inbound-message authorization cluster: whether a user/chat
is allowed to talk to the agent, the per-adapter DM policy, and the
unauthorized-DM behavior.

Behavior-neutral: every method is lifted verbatim from ``GatewayRunner``.
``self.*`` calls resolve unchanged via the MRO. Neutral dependencies import at
module top; the module-level ``logger`` is imported lazily inside the one method
that uses it (``from gateway.run import logger`` resolves at call time, when
``gateway.run`` is fully loaded) so this module never imports ``gateway.run`` at
import time -> no import cycle. The lazy import preserves the exact logger name
(``"gateway.run"``) so log records are unchanged.

### class GatewayAuthorizationMixin

> 继承: `object` ｜ 方法数: 10（公开 0）

User/chat authorization methods for ``GatewayRunner``.


## gateway.builtin_hooks.__init__

### 模块文档

Built-in gateway hooks that are always registered.

## gateway.cgroup_cleanup

### 模块文档

SIGKILL any process left in this systemd unit's cgroup.

Runs as ``ExecStopPost=`` so it only fires after the gateway's main process
has exited. The gateway already reaps its own tool subprocesses on a clean
shutdown; this is the safety net for long-lived helpers it doesn't track
(``adb``, platform bridges, etc.) that would otherwise be orphaned in the
cgroup and block ``Restart=always`` — issue #37454.

We deliberately iterate ``cgroup.procs`` and send per-PID SIGKILLs instead
of writing ``1`` to ``cgroup.kill``: the original failure mode in #37454
was the kernel returning ``EINVAL`` on the cgroup-wide kill, while per-PID
signal delivery uses a separate code path that still works.

### 顶层函数

#### def `reap_cgroup(cgroup_path: str | None = None) -> int`

SIGKILL every PID in the cgroup other than the caller. Returns the count killed.

#### def `main() -> int`


## gateway.channel_directory

### 模块文档

Channel directory -- cached map of reachable channels/contacts per platform.

Built on gateway startup, refreshed periodically (every 5 min), and saved to
~/.hermes/channel_directory.json.  The send_message tool reads this file for
action="list" and for resolving human-friendly channel names to numeric IDs.

### 顶层函数

#### def `build_channel_directory(adapters: Dict[Any, Any]) -> Dict[str, Any]`

Build a channel directory from connected platform adapters and session data.

Returns the directory dict and writes it to DIRECTORY_PATH.

#### def `load_directory() -> Dict[str, Any]`

Load the cached channel directory from disk.

#### def `lookup_channel_type(platform_name: str, chat_id: str) -> Optional[str]`

Return the channel ``type`` string (e.g. ``"channel"``, ``"forum"``) for *chat_id*, or *None* if unknown.

#### def `resolve_channel_name(platform_name: str, name: str) -> Optional[str]`

Resolve a human-friendly channel name to a numeric ID.

Matching strategy (case-insensitive, first match wins):
- Discord: "bot-home", "#bot-home", "GuildName/bot-home"
- Telegram: display name or group name
- Slack: "engineering", "#engineering"

#### def `format_directory_for_display() -> str`

Format the channel directory as a human-readable list for the model.


## gateway.code_skew

### 模块文档

Detect when the gateway is running stale code after a hot ``git pull``.

The gateway is a single long-lived process; its ``sys.modules`` is frozen at
boot. If the checkout is updated underneath it (a manual ``git pull``, or the
window before ``hermes update``'s graceful restart fires), a first-time lazy
import on a new code path can resolve a freshly-pulled consumer module against a
stale cached dependency -> ImportError (see
``tests/test_stale_utils_module_import.py`` for the exact failure).

We snapshot the checkout revision at gateway startup and compare on demand, so
risky callers (e.g. ``/model`` switching) can refuse with a clear "restart the
gateway" message instead of crashing on a cryptic import error.

If the revision can't be read (non-git install, IO error), the boot snapshot
stays ``None`` and skew detection no-ops — it never produces a false positive.

### 顶层函数

#### def `record_boot_fingerprint() -> None`

Snapshot the checkout revision at gateway startup (idempotent).

#### def `detect_code_skew() -> tuple[str, str] | None`

Return ``(boot_rev, disk_rev)`` short labels if the checkout drifted
since boot, else ``None``.


## gateway.config

### 模块文档

Gateway configuration management.

Handles loading and validating configuration for:
- Connected platforms (Telegram, Discord, WhatsApp, Weixin, and more)
- Home channels for each platform
- Session reset policies
- Delivery preferences

### class Platform

> 继承: `Enum` ｜ 方法数: 2（公开 0）

Supported messaging platforms.

Built-in platforms have explicit members.  Plugin platforms use dynamic
members created on-demand by ``_missing_()`` so that
``Platform("irc")`` works without modifying this enum.  Dynamic members
are cached in ``_value2member_map_`` for identity-stable comparisons.


### class HomeChannel

> 继承: `object` ｜ 方法数: 2（公开 2）

Default destination for a platform.

When a cron job specifies deliver="telegram" without a specific chat ID,
messages are sent to this home channel. Thread-aware platforms may also
store a thread/topic ID so the bare platform target routes to the exact
conversation where /sethome was run.

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> HomeChannel`


### class SessionResetPolicy

> 继承: `object` ｜ 方法数: 2（公开 2）

Controls when sessions reset (lose context).

Modes:
- "daily": Reset at a specific hour each day
- "idle": Reset after N minutes of inactivity
- "both": Whichever triggers first (daily boundary OR idle timeout)
- "none": Never auto-reset (context managed only by compression)

Default is "none" — sessions never auto-reset unless the user opts in
via the `session_reset` section in config.yaml (or gateway.json
overrides). Changed July 2026 from "both" (24h idle + daily 4am), which
surprised users who expected their conversations to persist.

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> SessionResetPolicy`


### class ChannelOverride

> 继承: `object` ｜ 方法数: 2（公开 2）

Per-channel override for model, provider, and system prompt.

Used in config under platforms.<name>.channel_overrides[channel_id].
Enables different channels (e.g. Discord #daily vs #dev) to use different
models and personas without running separate gateway instances.

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> ChannelOverride`


### class PlatformConfig

> 继承: `object` ｜ 方法数: 2（公开 2）

Configuration for a single messaging platform.

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> PlatformConfig`


### class StreamingConfig

> 继承: `object` ｜ 方法数: 2（公开 2）

Configuration for real-time token streaming to messaging platforms.

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> StreamingConfig`


### class GatewayConfig

> 继承: `object` ｜ 方法数: 9（公开 7）

Main gateway configuration.

Manages all platform connections, session policies, and delivery settings.

#### def `get_connected_platforms(self) -> List[Platform]`

Return list of platforms that are enabled and configured.

Sorted by platform value so the rendered "Connected Platforms" list
(and the home-channel blocks derived from it) is byte-stable across
gateway restarts and mid-process platform registration — dict
insertion order is not a stable contract and a reorder busts the
prompt cache without any semantic change.

#### def `get_home_channel(self, platform: Platform) -> Optional[HomeChannel]`

Get the home channel for a platform.

#### def `get_reset_policy(self, platform: Optional[Platform] = None, session_type: Optional[str] = None) -> SessionResetPolicy`

Get the appropriate reset policy for a session.

Priority: platform override > type override > default

#### def `to_dict(self) -> Dict[str, Any]`

#### classmethod `from_dict(cls, data: Dict[str, Any]) -> GatewayConfig`

#### def `get_unauthorized_dm_behavior(self, platform: Optional[Platform] = None) -> str`

Return the effective unauthorized-DM behavior for a platform.

Email is inbox-shaped, not chat-shaped, so it defaults to ``"ignore"``
unless ``platforms.email.unauthorized_dm_behavior`` explicitly opts
into pairing. A global default does not opt email into pairing.

#### def `get_notice_delivery(self, platform: Optional[Platform] = None) -> str`

Return the effective notice-delivery mode for a platform.


### 顶层函数

#### def `coerce_systemd_watchdog_seconds(value: Any, key: str = 'gateway.systemd_watchdog_seconds') -> int`

Return a bounded positive watchdog interval or zero when disabled.

Runtime and service generation share this normalization so a value can
never enable ``Type=notify`` while disabling application heartbeats.

#### def `platform_binds_port(platform_value: str, extra: Optional[dict] = None) -> bool`

Return True when *platform_value* actually binds a port for *extra* config.

Mode-conditional platforms (Feishu) only bind in their listener mode;
everything else in ``PORT_BINDING_PLATFORM_VALUES`` always binds.

#### def `load_gateway_config() -> GatewayConfig`

Load gateway configuration from multiple sources.

Priority (highest to lowest):
1. Environment variables
2. ~/.hermes/config.yaml (primary user-facing config)
3. ~/.hermes/gateway.json (legacy — provides defaults under config.yaml)
4. Built-in defaults


## gateway.cwd_placeholder

### 模块文档

Resolve gateway ``terminal.cwd`` placeholder values to ``TERMINAL_CWD``.

When ``terminal.cwd`` is unset or a placeholder (``.``, ``auto``, ``cwd``),
the gateway must not blindly map host ``Path.home()`` into container backends.
Docker with workspace mounting still needs an explicit host path signal
(``MESSAGING_CWD`` or an absolute config path) for ``terminal_tool`` to map
``/host/project`` → ``/workspace``.

### 顶层函数

#### def `resolve_placeholder_terminal_cwd(configured_cwd: str, terminal_backend: str, messaging_cwd: str | None, docker_mount_cwd_to_workspace: bool, home_fallback: str) -> str | None`

Return the ``TERMINAL_CWD`` value to set, or ``None`` to leave it unset.

Cases:
  - **local** + placeholder → ``MESSAGING_CWD`` or ``home_fallback``
  - **docker** + placeholder + mount on + host ``MESSAGING_CWD`` → host path
    (for ``terminal_tool`` ``/workspace`` mapping)
  - **docker** + placeholder + mount off → ``None`` (sandbox default)
  - other non-local backends + placeholder → ``None``


## gateway.dead_targets

### 模块文档

Persistent registry of delivery targets that are confirmed unreachable.

When a messaging platform reports that a target chat is permanently gone — a
deleted group (``Forbidden: the group chat was deleted``), a bot kicked/blocked,
or a deactivated user — re-sending to it on every cron tick or every fan-out
delivery wastes a send attempt against the platform's flood-control envelope and
spams the logs.  This registry lets the delivery layer short-circuit a target it
has already proven dead, while staying self-healing: any successful send to that
target clears the flag, so a user who re-adds the bot (or restores the chat)
recovers automatically with no manual cleanup.

Scope is deliberately narrow.  Only *whole-chat* deaths are recorded — the
``forbidden`` and chat-level ``not_found`` (``chat not found``) error kinds.
Thread/topic-level ``not_found`` is NOT recorded here: the adapters already
self-heal that by retrying without ``reply_to`` (see the Telegram adapter's
reply-target-deleted path), and a deleted topic does not mean the parent chat is
dead.

The store is a small JSON file under the active profile's HERMES_HOME so each
profile keeps its own dead set.  Reads/writes are best-effort: a corrupt or
unwritable file degrades to an in-memory-only registry rather than raising on
the delivery path.

### class DeadTargetRegistry

> 继承: `object` ｜ 方法数: 8（公开 5）

Thread-safe, persistent set of confirmed-dead delivery targets.

Keyed on ``platform:chat_id``.  Stores the reason and a timestamp for
observability.  Self-healing: :meth:`clear` (called on a successful send)
removes the flag.

#### def `__init__(path: Optional[Path] = None) -> None`

#### staticmethod `is_dead_error_kind(error_kind: Optional[str]) -> bool`

Return True when ``error_kind`` denotes a permanent whole-chat death.

#### def `is_dead(self, platform: str, chat_id: Optional[str]) -> bool`

#### def `mark_dead(self, platform: str, chat_id: Optional[str], reason: str = '') -> bool`

Record a target as confirmed-dead.  Returns True if newly added.

#### def `clear(self, platform: str, chat_id: Optional[str]) -> bool`

Remove a target's dead flag (self-healing).  Returns True if it was set.

#### def `all_dead(self) -> Dict[str, Dict[str, object]]`

Snapshot of the current dead set (for diagnostics / `hermes` CLI).


## gateway.delivery

### 模块文档

Delivery routing for cron job outputs and agent responses.

Routes messages to the appropriate destination based on:
- Explicit targets (e.g., "telegram:123456789")
- Platform home channels (e.g., "telegram" → home channel)
- Origin (back to where the job was created)
- Local (always saved to files)

### class DeliveryTarget

> 继承: `object` ｜ 方法数: 2（公开 2）

A single delivery target.

Represents where a message should be sent:
- "origin" → back to source
- "local" → save to local files
- "telegram" → Telegram home channel
- "telegram:123456" → specific Telegram chat

#### classmethod `parse(cls, target: str, origin: Optional[SessionSource] = None) -> DeliveryTarget`

Parse a delivery target string.

Formats:
- "origin" → back to source
- "local" → local files only
- "telegram" → Telegram home channel
- "telegram:123456" → specific Telegram chat

#### def `to_string(self) -> str`

Convert back to string format.


### class DeliveryRouter

> 继承: `object` ｜ 方法数: 6（公开 1）

Routes messages to appropriate destinations.

Handles the logic of resolving delivery targets and dispatching
messages to the right platform adapters.

#### def `__init__(config: GatewayConfig, adapters: Dict[Platform, Any] = None, dead_targets: Optional[DeadTargetRegistry] = None)`

Initialize the delivery router.

Args:
    config: Gateway configuration
    adapters: Dict mapping platforms to their adapter instances
    dead_targets: Optional shared registry of confirmed-unreachable
        targets.  When omitted, a profile-local registry is created.

#### async def `deliver(self, content: str, targets: List[DeliveryTarget], job_id: Optional[str] = None, job_name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

Deliver content to all specified targets.

Args:
    content: The message/output to deliver
    targets: List of delivery targets
    job_id: Optional job ID (for cron jobs)
    job_name: Optional job name
    metadata: Additional metadata to include

Returns:
    Dict with delivery results per target


### 顶层函数

#### def `looks_like_telegram_private_chat_id(chat_id: Optional[str]) -> bool`

True when ``chat_id`` is a positive int — Telegram's private-chat shape.

Telegram private chats use positive chat IDs; groups/channels/supergroups
use negative IDs. This is the single source of truth for that heuristic,
reused by the handoff seed path in ``gateway/run.py`` so handoff-created
DM topics key the same way as inbound DM-topic messages.


## gateway.delivery_ledger

### 模块文档

Durable delivery-obligation ledger for gateway final responses.

A final agent response that was generated but not yet confirmed-delivered
to the messaging platform is the one artifact the gateway can lose without
a trace: the turn already burned its tokens, the text exists only in a
Python local, and a crash / planned restart between finalize and platform
ACK drops it silently (#58818, #41696, #63695).

This module records a small durable row per outbound final response in the
shared ``state.db`` (same file and conventions as
``tools.async_delegation`` — WAL, owner pid + process-start-time liveness,
bounded retention). The gateway writes three checkpoints around the send:

    record_obligation()   state='pending'     before any send attempt
    mark_attempting()     state='attempting'  immediately before the await
    mark_delivered() /    state='delivered'   only on SendResult.success
    mark_failed()         state='failed'      on a definitive rejection

On startup, ``sweep_recoverable()`` claims rows whose owning process is
dead and hands them to the gateway for redelivery. Crash semantics are
explicit about ambiguity (the contract review of the earlier
delivery-outbox attempt, #61790, closed it for silently resending
ambiguous sends):

- ``pending``     — the send never started: redeliver plainly, no dup risk.
- ``attempting``  — crashed mid-await: the platform MAY already have the
  message. Redelivered WITH a visible recovered-reply marker so the
  contract is honest at-least-once, never a silent duplicate.
- ``failed``      — definitively rejected once; the restart is a natural
  retry boundary. Also carries the marker.
- ``delivered``   — nothing to do; retention prunes.

Poison rows cannot spin: attempts are capped, stale rows expire, and both
transition to ``abandoned`` (kept briefly for inspection, then pruned).

Everything here is best-effort by design: ledger failures must never block
or delay an actual send. Callers wrap every call in try/except.

### 顶层函数

#### def `compute_obligation_id(session_key: str, message_ref: str, content: str) -> str`

Stable id: same turn + same content re-records idempotently, while
distinct threads/topics on the same chat can never collide (the
session_key carries platform, chat and thread; ``message_ref`` is the
triggering inbound message id, distinguishing turns in one session).

#### def `record_obligation(obligation_id: str, session_key: str, platform: str, chat_id: str, thread_id: Optional[str], content: str) -> None`

Record a final response as owed to the platform (state='pending').

#### def `mark_attempting(obligation_id: str) -> None`

#### def `mark_delivered(obligation_id: str) -> None`

#### def `mark_failed(obligation_id: str, error: str = '') -> None`

#### def `sweep_recoverable(now: Optional[float] = None, deliverable_platforms: Optional[set] = None) -> List[Dict[str, Any]]`

Claim undelivered rows owned by dead processes; return them for
redelivery.

Claiming atomically re-stamps the owner to THIS process and increments
``attempts``, so a second gateway racing the same sweep cannot
double-claim (the UPDATE is guarded on the previous owner stamp).
Rows over the attempts cap or older than the stale cutoff transition to
'abandoned' instead of being returned.

``deliverable_platforms`` (platform value strings) restricts claiming to
platforms the caller can actually send on this boot.  ``attempts`` is the
redelivery budget, so it must only be spent on a real send: a platform
that failed to connect would otherwise burn one attempt per boot and hit
the cap having never been sent once.  Rows for absent platforms are left
untouched for a later boot; the stale cutoff still bounds them.

#### def `ledger_enabled(config: Optional[Dict[str, Any]] = None) -> bool`

Read the ``gateway.delivery_ledger`` config gate (default on).

#### def `debug_rows(limit: int = 20) -> str`

Human-readable dump for ad-hoc inspection (sqlite3-free path).


## gateway.display_config

### 模块文档

Per-platform display/verbosity configuration resolver.

Provides ``resolve_display_setting()`` — the single entry-point for reading
display settings with platform-specific overrides and sensible defaults.

Resolution order (first non-None wins):
    1. ``display.platforms.<platform>.<key>``  — explicit per-platform user override
    2. ``display.<key>``                       — global user setting
    3. ``_PLATFORM_DEFAULTS[<platform>][<key>]``  — built-in sensible default
    4. ``_GLOBAL_DEFAULTS[<key>]``              — built-in global default

Exception: ``display.streaming`` is CLI-only.  Gateway streaming follows the
top-level ``streaming`` config unless ``display.platforms.<platform>.streaming``
sets an explicit per-platform override.

Backward compatibility: ``display.tool_progress_overrides`` is still read as a
fallback for ``tool_progress`` when no ``display.platforms`` entry exists.  A
config migration (version bump) automatically moves the old format into the new
``display.platforms`` structure.

### 顶层函数

#### def `resolve_display_setting(user_config: dict, platform_key: str, setting: str, fallback: Any = None) -> Any`

Resolve a display setting with per-platform override support.

Parameters
----------
user_config : dict
    The full parsed config.yaml dict.
platform_key : str
    Platform config key (e.g. ``"telegram"``, ``"slack"``).  Use
    ``_platform_config_key(source.platform)`` from gateway/run.py.
setting : str
    Display setting name (e.g. ``"tool_progress"``, ``"show_reasoning"``).
fallback : Any
    Fallback value when the setting isn't found anywhere.

Returns
-------
The resolved value, or *fallback* if nothing is configured.


## gateway.drain_control

### 模块文档

External drain-control marker contract (dashboard → gateway).

Task 2.2 of the safe-shutdown plan (decisions.md Q-B, option A): the dashboard
has no way to call into a running gateway — there is no HTTP control channel
into the gateway process (guardrails: "there is NO external control channel
into a running gateway"). Restart/drain is driven only by the gateway reacting
to its own inputs: slash commands, process signals, and file markers it writes
itself (``.restart_notify.json``).

So the begin/cancel-drain dashboard endpoint communicates with the running
gateway the same way: it writes (or removes) a marker file, and a gateway
background watcher reacts to it. This module owns that marker contract so both
sides — the dashboard endpoint (writer) and the gateway watcher (reader) —
share one definition and can never disagree.

Contract (presence-based, mirroring ``.restart_notify.json``):

  * begin-drain  → write ``{HERMES_HOME}/.drain_request.json`` with
    ``{"action": "drain", "requested_at": <iso>, "principal": <str>,
    "epoch": <instantiation-epoch>, "suppress_notification": <bool>}``.
  * cancel-drain → remove the marker.
  * The gateway watcher treats **presence of a marker stamped with the current
    instantiation epoch** as "external drain active": flip
    ``gateway_state -> "draining"`` and stop accepting new turns. Absence (or a
    marker from a *prior* instantiation) means "not draining" (revert to
    ``running`` if we had flipped it).

Why the epoch (NS-570). ``HERMES_HOME`` is a **durable** store — on Hermes
Cloud it is a persistent Fly volume (``/opt/data``). A begin-drain marker
written there *survives a machine restart*. But the disruptive lifecycle
actions a drain protects (auto-update / image migrate / env edit / profile
change) all **restart the machine**, which is exactly the signal that the drain
is over. Without the epoch, a freshly-restarted gateway re-reads the orphaned
marker on boot and parks itself right back in ``draining`` forever (NS-570: an
auto-updated instance refused every turn for ~52 min). Stamping the marker with
an identity of *this* container/VM instantiation, and ignoring a marker whose
epoch doesn't match, makes "a deliberate restart clears the drain" true by
construction — while a marker written during the *current* instantiation (the
live drain) still matches, and an s6 respawn of just the gateway (PID 1 / init
unchanged) still honours an in-flight drain.

Reading the marker never raises: a malformed/half-written file reads as
"present but contentless", which the watcher still treats as drain-active
(fail-safe toward quiescing — a corrupt begin marker must not be ignored). The
epoch check is deliberately **lenient**: it ignores a marker only on a
*definite* epoch mismatch. A marker with no epoch (legacy/corrupt/contentless),
or an environment where the epoch cannot be computed (non-Linux, no ``/proc``),
both degrade to the original presence-only behaviour — never fail-closed.

### 顶层函数

#### def `current_instantiation_epoch() -> str`

Identity of THIS container / VM instantiation.

Stable for the life of the PID-1 init process — so an s6 respawn of just
the gateway keeps the same epoch and an in-flight drain is honoured — but
changes when the machine/container is recreated (a fresh PID 1 → a fresh
epoch). Composed from two ``/proc`` facts:

  * the kernel **boot id** (``/proc/sys/kernel/random/boot_id``) — changes
    on a VM / microVM reboot (e.g. a Fly Firecracker machine restart);
  * **PID 1's start time** (field 22 of ``/proc/1/stat``) — changes on a
    plain ``docker restart`` (the host kernel, hence boot_id, is unchanged,
    but ``/init`` is a brand-new process).

Together they discriminate every restart mode that matters:

  | event                          | boot_id | pid1 start | epoch  | marker |
  |--------------------------------|---------|------------|--------|--------|
  | Fly microVM reboot (auto-upd.) | changes | changes    | NEW    | reject |
  | plain ``docker restart``       | same    | changes    | NEW    | reject |
  | s6 respawn of the gateway only | same    | same       | SAME   | honour |
  | host ``hermes gateway restart``| same    | same(init) | SAME   | honour |

The last row is intentional: a host install has no durable-volume drain
bug, and honouring a drain across a deliberate process restart is the
intended reversible behaviour (D4a) — PID 1 there is the long-lived init
(systemd/launchd), so the epoch is stable.

Returns ``""`` when neither identity source is readable (non-Linux, no
``/proc``). An empty epoch disables the staleness check downstream,
degrading to the released presence-only behaviour — never fail-closed.
Memoised: the epoch is constant for the life of the process.

#### def `drain_request_path(home: Optional[Path] = None) -> Path`

Absolute path to the drain-request marker, respecting HERMES_HOME.

#### def `write_drain_request(principal: str = 'drain-control', suppress_notification: bool = False, home: Optional[Path] = None) -> dict[str, Any]`

Write the begin-drain marker. Returns the payload written.

Atomic write so the gateway watcher never reads a half-written file.
Idempotent: re-writing while a drain is already in progress just refreshes
``requested_at`` (harmless — the watcher keys off presence, not content).

Stamps the marker with :func:`current_instantiation_epoch` so a marker that
later survives a machine restart on the durable HERMES_HOME volume can be
recognised as stale and ignored (NS-570).

``suppress_notification`` is a generic "be quiet on the shutdown that ends
this drain" flag. When the drain culminates in a process exit (e.g. NAS
recreates the machine for an auto-update image migration), the gateway's
shutdown path reads it via :func:`drain_notification_suppressed` and skips
the *home-channel* "gateway shutting down" broadcast — the operator-flavoured
ping that would otherwise fire on every routine auto-update, potentially
dozens of times a day. It NEVER suppresses the per-active-session interrupt
ping. The gateway stays agnostic about *why* the drain is quiet; the policy
of which drain causes set the flag lives entirely in the caller (NAS). The
field defaults False so legacy/operator drains behave exactly as before.

#### def `clear_drain_request(home: Optional[Path] = None) -> bool`

Remove the drain marker (cancel-drain). Returns True if one existed.

Best-effort: a missing file is not an error (cancel is idempotent).

#### def `drain_requested(home: Optional[Path] = None) -> bool`

True iff a begin-drain marker for THIS instantiation is present.

A marker whose ``epoch`` does not match the current instantiation epoch is
treated as absent: it survived a container/VM restart (HERMES_HOME is a
durable Fly volume on Hermes Cloud) and the lifecycle action that triggered
the drain has already completed — honouring it would wedge the
freshly-restarted gateway in ``draining`` (NS-570). The staleness check is
lenient (see :func:`_marker_epoch_is_stale`): a legacy/corrupt marker with
no epoch, or an environment without ``/proc``, still reads as drain-active.

#### def `drain_notification_suppressed(home: Optional[Path] = None) -> bool`

True iff an ACTIVE drain marker asks to suppress the shutdown broadcast.

"Active" means exactly what :func:`drain_requested` means — a marker present
AND stamped with the current instantiation epoch. A stale (other-epoch)
marker that survived a machine restart on the durable HERMES_HOME volume is
ignored here just as it is for drain state (NS-570): we must never let an
orphaned marker's flag silence a *fresh* gateway's legitimate shutdown
broadcast.

Only honours the flag when it is explicitly truthy in the marker body. A
legacy marker without the field, a corrupt/contentless ``{}`` body, or an
absent marker all read as "not suppressed" (False) — fail toward the louder,
more-visible behaviour, consistent with :func:`read_drain_request`'s
never-raise contract. The gateway's shutdown path uses this to skip ONLY the
home-channel broadcast; the per-active-session interrupt ping is unaffected.

#### def `read_drain_request(home: Optional[Path] = None) -> Optional[dict[str, Any]]`

Return the marker payload, or ``None`` if absent.

A present-but-unparseable marker returns ``{}`` (truthy-presence preserved
via :func:`drain_requested`; callers that need the body get an empty dict
rather than an exception). Never raises.


## gateway.hooks

### 模块文档

Event Hook System

A lightweight event-driven system that fires handlers at key lifecycle points.
Hooks are discovered from ~/.hermes/hooks/ directories, each containing:
  - HOOK.yaml  (metadata: name, description, events list)
  - handler.py (Python handler with async def handle(event_type, context))

Events:
  - gateway:startup     -- Gateway process starts
  - session:start       -- New session created (first message of a new session)
  - session:end         -- Session ends (user ran /new or /reset)
  - session:reset       -- Session reset completed (new session entry created)
  - agent:start         -- Agent begins processing a message
  - agent:step          -- Each turn in the tool-calling loop
  - agent:end           -- Agent finishes processing
  - command:*           -- Any slash command executed (wildcard match)

Errors in hooks are caught and logged but never block the main pipeline.

Context dict passed to ``agent:start`` / ``agent:end`` handlers:
  platform     -- source platform name (e.g. "telegram", "matrix", "slack")
  user_id      -- platform user id of the sender
  chat_id      -- platform chat id (group/DM identifier)
  thread_id    -- Telegram forum-topic id / thread root id (string; empty
                  when not in a thread / topic)
  chat_type    -- "dm" | "group" | "forum" (empty if unknown)
  session_id   -- Hermes session id
  message      -- inbound message text (truncated to 500 chars)

``agent:end`` adds:
  response     -- agent response text (truncated to 500 chars)

Handlers posting a follow-up into the same Telegram forum-topic should
include ``message_thread_id=int(thread_id)`` when ``chat_type == "forum"``
and ``thread_id`` is non-empty.

### class HookRegistry

> 继承: `object` ｜ 方法数: 7（公开 4）

Discovers, loads, and fires event hooks.

Usage:
    registry = HookRegistry()
    registry.discover_and_load()
    await registry.emit("agent:start", {"platform": "telegram", ...})

#### def `__init__()`

#### property `loaded_hooks(self) -> List[dict]`

Return metadata about all loaded hooks.

#### def `discover_and_load(self) -> None`

Scan the hooks directory for hook directories and load their handlers.

Also registers built-in hooks that are always active.

Each hook directory must contain:
  - HOOK.yaml with at least 'name' and 'events' keys
  - handler.py with a top-level 'handle' function (sync or async)

#### async def `emit(self, event_type: str, context: Optional[Dict[str, Any]] = None) -> None`

Fire all handlers registered for an event, discarding return values.

Supports wildcard matching: handlers registered for "command:*" will
fire for any "command:..." event. Handlers registered for a base type
like "agent" won't fire for "agent:start" -- only exact matches and
explicit wildcards.

Args:
    event_type: The event identifier (e.g. "agent:start").
    context:    Optional dict with event-specific data.

#### async def `emit_collect(self, event_type: str, context: Optional[Dict[str, Any]] = None) -> List[Any]`

Fire handlers and return their non-None return values in order.

Like :meth:`emit` but captures each handler's return value. Used for
decision-style hooks (e.g. ``command:<name>`` policies that want to
allow/deny/rewrite the command before normal dispatch).

Exceptions from individual handlers are logged but do not abort the
remaining handlers.


## gateway.kanban_watchers

### 模块文档

Kanban board watcher methods for GatewayRunner.

Extracted verbatim from ``gateway/run.py`` (god-file decomposition Phase 3).
These are the background-loop methods that subscribe to kanban boards, deliver
notifications/artifacts, and drive the multi-agent dispatcher. They use only
``self`` state, so they live on a mixin that ``GatewayRunner`` inherits — the
``self._kanban_*`` call sites resolve identically via the MRO, making this a
behavior-neutral move that lifts ~1,000 LOC out of run.py.

### class GatewayKanbanWatchersMixin

> 继承: `object` ｜ 方法数: 6（公开 0）

Kanban watcher / notifier / dispatcher loops for GatewayRunner.


## gateway.memory_monitor

### 模块文档

Periodic process memory usage logging for the gateway.

Ported from cline/cline#10343 (src/standalone/memory-monitor.ts).

The gateway is a long-lived process that accumulates memory as it caches
agent instances, session transcripts, tool schemas, memory providers, MCP
connections, etc.  A slow leak in any of those subsystems is invisible
in a single log line — you only see it by watching RSS climb over hours.

This module emits a single structured ``[MEMORY] ...`` line every N
minutes (default 5) so maintainers investigating a suspected leak can
grep ``agent.log`` / ``gateway.log`` for a time series of RSS + Python
GC stats.  The timer runs in a background thread and shuts down cleanly
with the gateway.

Design notes (parity with the Cline port):
  * Grep-friendly single-line format beginning ``[MEMORY]``.
  * Final snapshot logged on shutdown so "last RSS before exit" is
    always in the log.
  * Baseline snapshot logged immediately on start.
  * Daemon thread — never blocks process exit.
  * Uses ``resource`` (stdlib, Linux/macOS) first and falls back to
    ``psutil`` when ``resource`` isn't available (Windows).  Both are
    optional; when neither works we emit a single WARNING and disable
    the monitor rather than crashing the gateway.

Config: ``logging.memory_monitor`` in ``config.yaml`` — see
``hermes_cli/config.py`` for the defaults block.

### 顶层函数

#### def `log_memory_usage(prefix: str = '') -> None`

Log current memory usage in a grep-friendly ``[MEMORY] ...`` line.

Safe to call on-demand from any thread at important lifecycle
moments (after shutdown, after context compression, etc.).

Parameters
----------
prefix
    Optional extra tag inserted after ``[MEMORY]`` — e.g.
    ``"baseline"``, ``"shutdown"``.

#### def `start_memory_monitoring(interval_seconds: float = 300.0) -> bool`

Start periodic memory usage logging in a daemon thread.

Logs immediately to capture a baseline, then every ``interval_seconds``.
Safe to call multiple times — subsequent calls are no-ops while the
first monitor is still running.

Parameters
----------
interval_seconds
    How often to log.  Default 300s (5 minutes), matching the
    upstream cline/cline implementation.

Returns
-------
bool
    True if a fresh monitor thread was started, False if one was
    already running or if memory introspection isn't available.

#### def `stop_memory_monitoring(timeout: float = 2.0) -> None`

Stop the monitor thread and log a final snapshot.

Safe to call even if ``start_memory_monitoring()`` was never called.

#### def `is_running() -> bool`

True if the background monitor thread is alive.


## gateway.message_timestamps

### 模块文档

Helpers for rendering gateway message timestamps exactly once.

Gateway messages need timestamps in the LLM context for temporal awareness, but
persisted message content should stay clean so replay does not accumulate
``[timestamp] [timestamp] ...`` prefixes across turns.

### 顶层函数

#### def `coerce_message_timestamp(ts_value: Any, tz = None) -> Optional[float]`

Coerce a timestamp-like value to Unix epoch seconds.

Accepts Unix epoch numbers, datetime objects, ISO strings, and the gateway's
bracketed human-readable timestamp format. Returns ``None`` when the value
cannot be interpreted.

#### def `format_message_timestamp(ts_value: Any, tz = None) -> str`

Format a timestamp value as ``[Tue 2026-04-28 13:40:53 CEST]``.

#### def `strip_leading_message_timestamps(content: str, tz = None) -> Tuple[str, Optional[float]]`

Strip one or more leading gateway timestamp prefixes from ``content``.

Returns ``(clean_content, embedded_epoch)``.  If multiple timestamp prefixes
are present, the timestamp closest to the actual message text wins.  That
preserves the original platform-send time for legacy contaminated rows like
``[processing time] [platform time] [sender] message``.

#### def `render_user_content_with_timestamp(content: str, ts_value: Any = None, tz = None) -> str`

Render a user message for LLM context with exactly one timestamp prefix.

Existing leading timestamp prefixes are removed first.  If such a prefix was
present, its parsed time wins over ``ts_value``; otherwise ``ts_value`` is
formatted and prepended.  If no timestamp is available, the cleaned content is
returned unchanged.


## gateway.mirror

### 模块文档

Session mirroring for cross-platform message delivery.

When a message is sent to a platform (via send_message or cron delivery),
this module appends a "delivery-mirror" record to the target session's
transcript so the receiving-side agent has context about what was sent.

Standalone -- works from CLI, cron, and gateway contexts without needing
the full SessionStore machinery.

### 顶层函数

#### def `mirror_to_session(platform: str, chat_id: str, message_text: str, source_label: str = 'cli', thread_id: Optional[str] = None, user_id: Optional[str] = None, role: str = 'assistant') -> bool`

Append a delivery-mirror message to the target session's transcript.

Finds the gateway session that matches the given platform + chat_id,
then writes a mirror entry to both the JSONL transcript and SQLite DB.

``role`` defaults to ``"assistant"`` — correct for the interactive
``send_message`` mirror, where the mirrored text is the agent's own
outgoing reply (a genuine assistant turn). Callers mirroring text that is
NOT the agent speaking — e.g. a cron brief delivered out-of-band — must
pass ``role="user"``: the ``mirror``/``mirror_source`` metadata is dropped
at the SQLite boundary (only role+content persist), so on replay an
assistant-role mirror is indistinguishable from a real assistant turn and
produces ``assistant → assistant`` pairs that break strict-alternation
providers (issue #2221). A user-role mirror collapses safely via
``repair_message_sequence``'s consecutive-user merge on every provider.

Returns True if mirrored successfully, False if no matching session or error.
All errors are caught -- this is never fatal.


## gateway.pairing

### 模块文档

DM Pairing System

Code-based approval flow for authorizing new users on messaging platforms.
Instead of static allowlists with user IDs, unknown users receive a one-time
pairing code that the bot owner approves via the CLI.

Security features (based on OWASP + NIST SP 800-63-4 guidance):
  - 8-char codes from 32-char unambiguous alphabet (no 0/O/1/I)
  - Cryptographic randomness via secrets.choice()
  - 1-hour code expiry
  - Max 3 pending codes per platform
  - Rate limiting: 1 request per user per 10 minutes
  - Lockout after 5 failed approval attempts (1 hour)
  - File permissions: chmod 0600 on all data files
  - Codes are never logged to stdout

Storage: ~/.hermes/pairing/

### class PairingStore

> 继承: `object` ｜ 方法数: 25（公开 8）

Manages pairing codes and approved user lists.

Data files per platform:
  - {platform}-pending.json   : pending pairing requests
  - {platform}-approved.json  : approved (paired) users
  - _rate_limits.json         : rate limit tracking

When constructed with ``profile="<name>"``, storage lives under
``<HERMES_HOME>/profiles/<name>/pairing/`` (per-profile, used by
multiplexing gateways so each profile has its own whitelist).
Without a profile, storage is the global ``<HERMES_HOME>/pairing/``
directory (backward-compat for the ``hermes pairing`` CLI).

#### def `__init__(profile: Optional[str] = None)`

#### property `profile(self) -> Optional[str]`

Profile name this store is scoped to, or None for the global store.

#### def `is_approved(self, platform: str, user_id: str) -> bool`

Check if a user is approved (paired) on a platform.

#### def `list_approved(self, platform: str = None) -> list`

List approved users, optionally filtered by platform.

#### def `revoke(self, platform: str, user_id: str) -> bool`

Remove a user from the approved list. Returns True if found.

#### def `generate_code(self, platform: str, user_id: str, user_name: str = '') -> Optional[str]`

Generate a pairing code for a new user.

Returns the code string, or None if:
  - User is rate-limited (too recent request)
  - Max pending codes reached for this platform
  - User/platform is in lockout due to failed attempts

The code is NOT stored in plaintext.  Only a salted SHA-256 hash is
persisted so that reading the pending file does not reveal codes.

#### def `approve_code(self, platform: str, code: str) -> Optional[dict]`

Approve a pairing code. Adds the user to the approved list.

Returns ``{user_id, user_name}`` on success, ``None`` if the code is
invalid/expired OR the platform is currently locked out after
``MAX_FAILED_ATTEMPTS`` failed approvals (#10195). Callers can
disambiguate with ``_is_locked_out(platform)``.

Verification: the user-provided code is hashed with each stored
entry's salt and compared to the stored hash using constant-time
comparison. Pre-hash entries (legacy plaintext-key format from
pre-upgrade pending.json files) are silently ignored — they get
pruned at TTL by ``_cleanup_expired``.

#### def `list_pending(self, platform: str = None) -> list`

List pending pairing requests, optionally filtered by platform.

Codes are stored hashed — the ``code`` field is replaced with the
first 8 hex characters of the hash so admins can distinguish entries
without revealing the original code. Legacy plaintext-key entries
(pre-hash format) are shown with a "legacy" placeholder so admins
can see them age out without crashing on a missing ``hash`` field.

#### def `clear_pending(self, platform: str = None) -> int`

Clear all pending requests. Returns count removed.


## gateway.platform_registry

### 模块文档

Platform Adapter Registry

Allows platform adapters (built-in and plugin) to self-register so the gateway
can discover and instantiate them without hardcoded if/elif chains.

Built-in adapters continue to use the existing if/elif in _create_adapter()
for now.  Plugin adapters register here via PluginContext.register_platform()
and are looked up first -- if nothing is found the gateway falls through to
the legacy code path.

Usage (plugin side):

    from gateway.platform_registry import platform_registry, PlatformEntry

    platform_registry.register(PlatformEntry(
        name="irc",
        label="IRC",
        adapter_factory=lambda cfg: IRCAdapter(cfg),
        check_fn=check_requirements,
        validate_config=lambda cfg: bool(cfg.extra.get("server")),
        required_env=["IRC_SERVER"],
        install_hint="pip install irc",
    ))

Usage (gateway side):

    adapter = platform_registry.create_adapter("irc", platform_config)

### class PlatformEntry

> 继承: `object` ｜ 方法数: 0（公开 0）

Metadata and factory for a single platform adapter.


### class PlatformRegistry

> 继承: `object` ｜ 方法数: 11（公开 8）

Central registry of platform adapters.

Thread-safe for reads (dict lookups are atomic under GIL).
Writes happen at startup during sequential discovery.

#### def `__init__() -> None`

#### def `register_deferred(self, name: str, loader: Callable[[], None]) -> None`

Register a lazy loader for a platform that hasn't been imported yet.

*loader* is a zero-arg callable that imports the owning plugin module,
which is expected to call :meth:`register` with the real entry for
*name*.  The loader runs at most once, the first time *name* is looked
up (or when the full entry list is materialized).  A real entry that is
registered directly (e.g. a built-in) takes precedence -- the deferred
loader is then dropped.

#### def `register(self, entry: PlatformEntry) -> None`

Register a platform adapter entry.

If an entry with the same name exists, it is replaced (last writer
wins -- this lets plugins override built-in adapters if desired).

#### def `unregister(self, name: str) -> bool`

Remove a platform entry.  Returns True if it existed.

#### def `get(self, name: str) -> Optional[PlatformEntry]`

Look up a platform entry by name.

#### def `all_entries(self) -> list[PlatformEntry]`

Return all registered platform entries.

#### def `plugin_entries(self) -> list[PlatformEntry]`

Return only plugin-registered platform entries.

#### def `is_registered(self, name: str) -> bool`

#### def `create_adapter(self, name: str, config: Any) -> Optional[Any]`

Create an adapter instance for the given platform name.

Returns None if:
- No entry registered for *name*
- check_fn() returns False (missing deps)
- validate_config() returns False (misconfigured)
- The factory raises an exception


## gateway.platforms.__init__

### 模块文档

Platform adapters for messaging integrations.

Each adapter handles:
- Receiving messages from a platform
- Sending messages/responses back
- Platform-specific authentication
- Message formatting and media handling

## gateway.platforms._http_client_limits

### 模块文档

Shared HTTP client factory for long-lived platform adapters.

Gateway messaging platforms (QQ Bot, Feishu, WeCom, DingTalk, Signal,
BlueBubbles, WeCom-callback) keep a persistent ``httpx.AsyncClient``
alive for the adapter's lifetime.  That amortises TLS/connection setup
across many API calls, but it also means the process's file-descriptor
pressure is sensitive to how aggressively the pool recycles idle keep-
alive connections.

httpx's default ``keepalive_expiry`` is 5 seconds.  On macOS behind
Cloudflare Warp (and other transparent proxies), peer-initiated FIN can
sit in ``CLOSE_WAIT`` longer than that before the local socket actually
drains — which, multiplied across 7 long-lived adapters plus the LLM
client and MCP clients, walks straight into the default 256 fd limit.
See #18451.

``platform_httpx_limits()`` returns a tighter ``httpx.Limits`` the
adapter factories use instead of the httpx default.  The values chosen:

* ``max_keepalive_connections=10`` — plenty for any single adapter;
  platform APIs rarely parallelise beyond this.
* ``keepalive_expiry=2.0`` — close idle sockets aggressively so a
  proxy's lingering CLOSE_WAIT window can't starve the process.

Override via ``HERMES_GATEWAY_HTTPX_KEEPALIVE_EXPIRY`` /
``HERMES_GATEWAY_HTTPX_MAX_KEEPALIVE`` env vars when tuning under load.

### 顶层函数

#### def `platform_httpx_limits() -> httpx.Limits | None`

Return ``httpx.Limits`` tuned for persistent platform-adapter clients.

Returns ``None`` when httpx isn't importable, so callers can fall
back to httpx's built-in default without a hard dependency on this
helper being reachable.


## gateway.platforms.api_server

### 模块文档

OpenAI-compatible API server platform adapter.

Exposes an HTTP server with endpoints:
- POST /v1/chat/completions        — OpenAI Chat Completions format (stateless; opt-in session continuity via X-Hermes-Session-Id header; opt-in long-term memory scoping via X-Hermes-Session-Key header)
- POST /v1/responses               — OpenAI Responses API format (stateful via previous_response_id; X-Hermes-Session-Key supported)
- GET  /v1/responses/{response_id} — Retrieve a stored response
- DELETE /v1/responses/{response_id} — Delete a stored response
- GET  /v1/models                  — lists hermes-agent and any configured model_routes aliases
- GET  /v1/capabilities            — machine-readable API capabilities for external UIs
- GET  /api/sessions               — list client-visible Hermes sessions
- POST /api/sessions               — create an empty Hermes session
- GET/PATCH/DELETE /api/sessions/{session_id} — read/update/delete a session
- GET  /api/sessions/{session_id}/messages — read session message history
- POST /api/sessions/{session_id}/fork — branch a session using SessionDB lineage
- POST /api/sessions/{session_id}/chat[/stream] — chat with a persisted session
- POST /v1/runs                    — start a run, returns run_id immediately (202)
- GET  /v1/runs/{run_id}           — retrieve current run status
- GET  /v1/runs/{run_id}/events    — SSE stream of structured lifecycle events
- POST /v1/runs/{run_id}/approval — resolve a pending run approval
- POST /v1/runs/{run_id}/stop       — interrupt a running agent
- GET  /health                     — health check
- GET  /health/detailed            — rich status for cross-container dashboard probing

Any OpenAI-compatible frontend (Open WebUI, LobeChat, LibreChat,
AnythingLLM, NextChat, ChatBox, etc.) can connect to hermes-agent
through this adapter by pointing at http://localhost:8642/v1 and
authenticating with API_SERVER_KEY.

When ``gateway.multiplex_profiles`` is on, the default profile owns this
listener and secondary profiles are reached via a URL prefix — same contract
as the webhook adapter:

    GET  /p/<profile>/v1/models
    POST /p/<profile>/v1/chat/completions
    ...

Requires:
- aiohttp (already available in the gateway)

### class ResponseStore

> 继承: `object` ｜ 方法数: 9（公开 6）

SQLite-backed LRU store for Responses API state.

Each stored response includes the full internal conversation history
(with tool calls and results) so it can be reconstructed on subsequent
requests via previous_response_id.

Persists across gateway restarts.  Falls back to in-memory SQLite
if the on-disk path is unavailable.

#### def `__init__(max_size: int = MAX_STORED_RESPONSES, db_path: str = None)`

#### def `get(self, response_id: str) -> Optional[Dict[str, Any]]`

Retrieve a stored response by ID (updates access time for LRU).

#### def `put(self, response_id: str, data: Dict[str, Any]) -> None`

Store a response, evicting the oldest if at capacity.

#### def `delete(self, response_id: str) -> bool`

Remove a response from the store. Returns True if found and deleted.

#### def `get_conversation(self, name: str) -> Optional[str]`

Get the latest response_id for a conversation name.

#### def `set_conversation(self, name: str, response_id: str) -> None`

Map a conversation name to its latest response_id.

#### def `close(self) -> None`

Close the database connection.


### class APIServerAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 90（公开 5）

OpenAI-compatible HTTP API server adapter.

Runs an aiohttp web server that accepts OpenAI-format requests
and routes them through hermes-agent's AIAgent.

#### def `__init__(config: PlatformConfig)`

#### def `active_agent_work_count(self) -> int`

Return all live agent work owned by this API adapter.

``/v1/runs`` registers an asyncio task before it constructs and stores
its agent, so ``_active_run_agents`` has a real queued-before-agent gap.
Reuse the task-based accounting used by the concurrent-run limit: it
covers that gap and excludes completed tasks retained until cleanup.

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Start the aiohttp web server.

#### async def `disconnect(self) -> None`

Stop the aiohttp web server and release all owned resources.

Closes the ResponseStore SQLite connection in addition to stopping
the aiohttp web server. Without this, every adapter instance leaks
2 file descriptors (the database file and its WAL sidecar) — the
reconnect loop in ``gateway.run`` constructs a fresh adapter on
every retry, so 2 fds/retry × 300s backoff cap ≈ 12 fds/hour, which
exhausts the default 2560 fd limit after ~12h of failed reconnects
and turns the whole gateway into a zombie
(OSError: [Errno 24] Too many open files, #37011).

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Not used — HTTP request/response cycle handles delivery directly.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return basic info about the API server.


### 顶层函数

#### def `check_api_server_requirements() -> bool`

Check if API server dependencies are available.


## gateway.platforms.base

### 模块文档

Base platform adapter interface.

All platform adapters (Telegram, Discord, WhatsApp, Weixin, and more) inherit from this
and implement the required methods.

### class CachedMedia

> 继承: `object` ｜ 方法数: 1（公开 1）

Result of caching one attachment's bytes.

#### def `context_note(self) -> str`

One-line transcript annotation pointing the agent at the file.


### class MessageType

> 继承: `Enum` ｜ 方法数: 0（公开 0）

Types of incoming messages.


### class ProcessingOutcome

> 继承: `Enum` ｜ 方法数: 0（公开 0）

Result classification for message-processing lifecycle hooks.


### class MessageEvent

> 继承: `object` ｜ 方法数: 3（公开 3）

Incoming message from a platform.

Normalized representation that all adapters produce.

#### def `is_command(self) -> bool`

Check if this is a command message (e.g., /new, /reset).

#### def `get_command(self) -> Optional[str]`

Extract command name if this is a command message.

#### def `get_command_args(self) -> str`

Get the arguments after a command.


### class TextDebounceState

> 继承: `object` ｜ 方法数: 0（公开 0）


### class SendResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of sending a message.


### class EphemeralReply

> 继承: `str` ｜ 方法数: 2（公开 1）

System-notice reply that auto-deletes after a TTL.

Slash-command handlers in ``gateway/run.py`` can return this wrapper
instead of a plain string to request that the reply message be deleted
after ``ttl_seconds`` on platforms that support ``delete_message``.

Subclassing ``str`` keeps the wrapper transparent to anything that
treats handler return values as text (existing tests use ``in`` /
``startswith`` / equality; the ``_process_message_background`` pipeline
extracts attachments from the string content).  ``isinstance(r,
EphemeralReply)`` still distinguishes ephemeral replies from plain
strings so the send path can schedule deletion.

Platforms that don't override :meth:`BasePlatformAdapter.delete_message`
silently ignore the TTL — the message is sent normally and left in
place.  When ``ttl_seconds`` is ``None``, the pipeline uses the
configured ``display.ephemeral_system_ttl`` default.  A default of ``0``
disables auto-deletion globally, preserving prior behavior.

#### property `text(self) -> str`

Return the underlying text.

Provided for call sites that want an explicit string conversion,
though ``str(reply)`` and using ``reply`` directly where a string
is expected both work identically.


### class BasePlatformAdapter

> 继承: `ABC` ｜ 方法数: 108（公开 65）

Base class for platform adapters.

Subclasses implement platform-specific logic for:
- Connecting and authenticating
- Receiving messages
- Sending messages/responses
- Handling media

#### def `set_status_text(self, chat_id: str, text: Optional[str]) -> None`

Set or clear (``None``) the live working-state phrase for a chat.

Cheap, in-memory only: the next typing refresh renders the new text.
No-op storage on adapters that never read ``_status_text``.

#### def `__init__(config: PlatformConfig, platform: Platform)`

#### property `message_len_fn(self) -> Callable[[str], int]`

Return the length function for measuring message size on this platform.

Override in adapters whose platform counts characters differently from
Python ``len`` (e.g. Telegram counts UTF-16 code units).

#### property `enforces_own_access_policy(self) -> bool`

Whether this adapter gates inbound access before dispatch.

Some adapters (WeCom, Weixin, Yuanbao, QQBot, WhatsApp) implement a
documented config-driven access surface — ``dm_policy`` / ``group_policy`` /
``allow_from`` / ``group_allow_from`` in ``PlatformConfig.extra`` — and
enforce it at intake: a message is dropped inside the adapter and never
reaches the gateway unless it already passed that policy.

The gateway's env-based allowlist check runs *after* the adapter. When
no env allowlist is configured, the gateway consults this flag so it can
honor a config-only ``dm_policy: allowlist`` / ``allow_from`` (which the
adapter already enforced) instead of double-denying it. Crucially, the
flag alone is NOT "already authorized": these adapters default
``dm_policy`` / ``group_policy`` to ``"open"``, which forwards every
sender, so the gateway trusts the adapter only when its effective policy
for the chat type is an actual ``"allowlist"`` restriction — never for
``"open"`` (that would be the network-exposed fail-open SECURITY.md §2.6
forbids). Open access still requires an explicit
``{PLATFORM}_ALLOW_ALL_USERS`` / ``GATEWAY_ALLOW_ALL_USERS`` opt-in.

Adapters that own their access policy override this to return ``True``.
Adapters that delegate access control to the gateway leave it ``False``
(the default).

#### property `authorization_is_upstream(self) -> bool`

Whether inbound on this adapter was already authorized UPSTREAM.

Distinct from ``enforces_own_access_policy``: that flag describes an
adapter that enforces a LOCAL, config-driven access surface
(``dm_policy: allowlist`` / ``allow_from``) the gateway can mirror. This
flag describes an adapter whose authorization is performed by a TRUSTED
UPSTREAM over an authenticated transport — there is no local policy to
consult, and the env allowlist (``{PLATFORM}_ALLOWED_USERS``) does not
apply because the sender identity isn't a platform account the operator
configures here.

The relay adapter is the sole user: it fronts the Team Gateway
connector over a per-instance-authenticated WebSocket, and the connector
performs owner-only author-binding resolution BEFORE delivering — a
message only reaches this gateway because the connector resolved it to
THIS instance's bound user (``user_instance_binding``). The author id is
read off the event the connector observed, never gateway-asserted. So an
inbound relay event carries an authorization decision already made by a
trusted, authenticated upstream; default-denying it (no env allowlist ⇒
deny) is incorrect.

This is NOT a fail-open: it is authorization DELEGATED to a trusted
upstream that authenticated the transport (the relay WS secret) and
enforced owner-only binding, as opposed to authorization being ABSENT.
It only takes effect for an adapter that explicitly overrides this to
``True``; every network-exposed direct adapter leaves it ``False`` and
the env-allowlist default-deny continues to apply unchanged.

#### def `supports_draft_streaming(self, chat_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool`

Whether this adapter supports native streaming-draft updates.

Telegram Bot API 9.5 introduced ``sendMessageDraft``, which renders an
animated streaming preview as the bot calls it repeatedly with the
same ``draft_id`` and growing text.  Adapters that implement
``send_draft`` should return True here for the chat types where the
platform supports it (Telegram restricts drafts to private DMs).

Default implementation returns False.  Stream consumers fall back to
the edit-based path (``send`` + ``edit_message``) when this returns
False or when ``send_draft`` raises.

#### def `prefers_fresh_final_streaming(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool`

Whether the stream consumer should finalize a streamed reply by
sending a *fresh* final message (and deleting the preview) instead of
final-editing the preview.

Some adapters can send richer final messages than their current edit
implementation supports. Telegram is the motivating case: Hermes sends
final replies through ``sendRichMessage`` but still finalizes streamed
previews through its existing MarkdownV2 edit path until Bot API 10.1's
``rich_message`` edit parameter is wired directly. Such adapters
override this to ask the consumer to re-deliver the completed answer as
a new rich message and best-effort delete the stale preview, so the
final rendering matches the rich send path.

Default implementation returns False — legacy platforms keep the
edit-in-place finalization path.

#### def `streaming_overflow_limit(self) -> Optional[int]`

Max single-message length (in this adapter's ``message_len_fn``
units) the stream consumer may accumulate before it splits, when the
adapter can deliver a larger message than its legacy per-message limit.

Telegram Bot API 10.1 Rich Messages accept up to 32,768 chars in a
single ``sendRichMessage`` / ``sendRichMessageDraft``, far above the
4,096 MarkdownV2 limit.  Adapters with such a richer send/draft path
override this so the consumer doesn't fragment a reply that fits one
rich message; the live edit preview is still bound by the platform's
edit limit, but the finalized reply (and DM draft preview) is delivered
whole.

Return ``None`` (default) to use ``MAX_MESSAGE_LENGTH``.

#### async def `send_draft(self, chat_id: str, draft_id: int, content: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send or update an animated streaming-draft preview.

Reuse the same ``draft_id`` (any non-zero int) across consecutive
calls within a single response so the platform animates the preview
rather than re-creating it.  Different responses must use different
``draft_id`` values within the same chat to avoid animating over a
prior bubble.

Drafts have no message_id and cannot be edited, replied to, or
deleted via normal message APIs.  When the response finishes, the
caller delivers the final answer as a regular ``send`` and the
draft preview clears naturally on the client.

Default implementation raises NotImplementedError; adapters that
also return True from :meth:`supports_draft_streaming` must override.

**异常**: `NotImplementedError`

#### def `render_message_event(self, event: Any, sink: Any) -> None`

Render a MessageChunk / MessageStop / Commentary onto the sink.

Default: map onto the stream consumer's existing primitives, preserving
today's behavior 1:1.  ``sink`` is a GatewayStreamConsumer.

#### def `format_tool_event(self, event: Any, mode: str = 'all', preview_max_len: int = 40) -> Optional[str]`

Return the rendered chrome for a ToolCallChunk, or None to eat it.

Reproduces the gateway's historical tool-progress formatting: an emoji
for the tool, the tool name, and a short argument preview (or the full
args dict in ``verbose`` mode).  Adapters that cannot render tool chrome
(no message editing, plain-text only) should override to return None so
the event is dropped rather than spamming separate bubbles.

``mode`` is the resolved tool-progress mode ("all" / "new" / "verbose");
``preview_max_len`` mirrors the ``tool_preview_length`` config (0 means
"no cap" in verbose mode).

#### property `has_fatal_error(self) -> bool`

#### property `fatal_error_message(self) -> Optional[str]`

#### property `fatal_error_code(self) -> Optional[str]`

#### property `fatal_error_retryable(self) -> bool`

#### def `set_fatal_error_handler(self, handler: Callable[['BasePlatformAdapter'], Awaitable[None] | None]) -> None`

#### property `name(self) -> str`

Human-readable name for this adapter.

#### property `is_connected(self) -> bool`

Check if adapter is currently connected.

#### def `set_message_handler(self, handler: MessageHandler) -> None`

Set the handler for incoming messages.

The handler receives a MessageEvent and should return
an optional response string.

#### def `set_topic_recovery_fn(self, fn: Optional[Callable[[Any], Optional[str]]]) -> None`

Install a thread_id-recovery hook (Telegram DM topic mode).

The hook is called with ``event.source`` before session keying;
a non-None return value replaces ``source.thread_id``. Pass
``None`` to clear the hook.

#### def `set_busy_session_handler(self, handler: Optional[Callable[[MessageEvent, str], Awaitable[bool]]]) -> None`

Set an optional handler for messages arriving during active sessions.

#### def `set_authorization_check(self, callback: Optional[Callable[[str, Optional[str], Optional[str]], bool]]) -> None`

Register a platform-bound authorization check.

The callback signature is ``(user_id, chat_type, chat_id) -> bool``.
It is used by adapters that pull external context (e.g. Slack thread
replies via ``conversations.replies``) to flag messages from senders
that are not on the configured allowlist, so the LLM can treat them
as unverified background reference rather than authoritative input.

#### def `set_session_store(self, session_store: Any) -> None`

Set the session store for checking active sessions.

Used by adapters that need to check if a thread/conversation
has an active session before processing messages (e.g., Slack
thread replies without explicit mentions).

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to the platform and start receiving messages.

Args:
    is_reconnect: False on a cold first boot (the gateway is
        starting this platform for the first time); True when the
        reconnect watcher is re-establishing a platform that was
        previously running and dropped after an outage. Adapters
        that buffer a server-side update queue (e.g. Telegram's Bot
        API) should preserve that queue when ``is_reconnect`` is
        True so messages sent during the outage are delivered rather
        than silently discarded. Adapters with no such queue may
        ignore the flag.

Returns True if connection was successful.

#### async def `disconnect(self) -> None`

Disconnect from the platform.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a message to a chat.

Args:
    chat_id: The chat/channel ID to send to
    content: Message content (may be markdown)
    reply_to: Optional message ID to reply to
    metadata: Additional platform-specific options

Returns:
    SendResult with success status and message ID

#### async def `create_handoff_thread(self, parent_chat_id: str, name: str) -> Optional[str]`

Create a fresh thread under ``parent_chat_id`` for a session handoff.

Used by the gateway's handoff watcher when transferring a CLI
session to a thread-capable platform — the new thread isolates the
handed-off conversation from any pre-existing chat in the home
channel and gives users a clean per-handoff scrollback.

Returns the new thread/topic id (as a string) on success, or
``None`` if the platform doesn't support threading or the
attempt failed (permissions, topics-mode off, etc.). When ``None``
is returned the watcher falls back to using ``parent_chat_id``
directly.

Default implementation returns ``None`` — adapters that support
threads override this. See:
  - Telegram: forum topics in groups, DM topics with bot API 9.4+
  - Discord:  text-channel threads (1440-min auto-archive)
  - Slack:    seed-message thread anchoring

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False) -> SendResult`

Edit a previously sent message. Optional — platforms that don't
support editing return success=False and callers fall back to
sending a new message.

``finalize`` signals that this is the last edit in a streaming
sequence.  Most platforms (Telegram, Slack, Discord, Matrix,
etc.) treat it as a no-op because their edit APIs have no notion
of message lifecycle state — an edit is an edit.  Platforms that
render streaming updates with a distinct "in progress" state and
require explicit closure (e.g. rich card / AI assistant surfaces
such as DingTalk AI Cards) use it to finalize the message and
transition the UI out of the streaming indicator — those should
also set ``REQUIRES_EDIT_FINALIZE = True`` so callers route a
final edit through even when content is unchanged.  Callers
should set ``finalize=True`` on the final edit of a streamed
response (typically when ``got_done`` fires in the stream
consumer) and leave it ``False`` on intermediate edits.

#### async def `delete_message(self, chat_id: str, message_id: str) -> bool`

Delete a previously sent message.  Optional — platforms that don't
support deletion return ``False`` and callers fall back to leaving
the message in place.

Used by the stream consumer's fresh-final cleanup path (see
openclaw/openclaw#72038) to remove long-lived preview messages
after sending the completed reply as a fresh message so the
platform's visible timestamp reflects completion time.

Returns ``True`` on successful deletion, ``False`` otherwise.
Subclasses should override for platforms with a deletion API
(e.g. Telegram ``deleteMessage``).

#### async def `send_slash_confirm(self, chat_id: str, title: str, message: str, session_key: str, confirm_id: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a three-option slash-command confirmation prompt.

Used by the gateway's generic slash-confirm primitive (see
``GatewayRunner._request_slash_confirm``) for commands that have a
non-destructive but expensive side effect the user should explicitly
acknowledge — the current caller is ``/reload-mcp``, which
invalidates the provider prompt cache.

Platforms with inline-button support (Telegram, Discord, Slack,
Matrix, Feishu) should override this to render three buttons:
Approve Once / Always Approve / Cancel.  Button callbacks MUST be
routed back through the gateway by calling
``GatewayRunner._resolve_slash_confirm(confirm_id, choice)`` where
``choice`` is ``"once"`` / ``"always"`` / ``"cancel"``.

Platforms without button UIs leave this as the default and fall
through to the gateway's text fallback (which sends ``message`` as
plain text and intercepts the next ``/approve`` / ``/always`` /
``/cancel`` reply).

``confirm_id`` is a short string generated by the gateway; the
adapter stores it alongside any platform-specific state needed to
route the callback (e.g. Telegram's ``_approval_state`` dict).

#### async def `send_clarify(self, chat_id: str, question: str, choices: Optional[list], clarify_id: str, session_key: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a clarify prompt to the user.

Two render modes:

  * **Multiple choice** (``choices`` is a non-empty list) — adapters
    that override this should render inline buttons (one per choice
    plus a final "Other" / free-text option).  Button callbacks
    MUST resolve via
    ``tools.clarify_gateway.resolve_gateway_clarify(clarify_id, response)``
    with the chosen string.  Picking the "Other" button calls
    ``mark_awaiting_text(clarify_id)`` so the next message in the
    session is captured as the response.

  * **Open-ended** (``choices`` is None or empty) — render the
    question as a plain text message; the next user message in the
    session is captured by the gateway's text-intercept and
    resolves the clarify automatically (see
    ``GatewayRunner._maybe_intercept_clarify_text``).

The default implementation falls back to a numbered text list,
which works on every platform — the user replies with a number
("2") or with the literal choice text, and the gateway intercepts
and resolves.  For the text fallback path, the default calls
``mark_awaiting_text()`` so that the gateway text-intercept
(:meth:`GatewayRunner._maybe_intercept_clarify_text`) catches the
user's reply instead of timing out.
Adapters with native button UIs (Telegram, Discord) SHOULD
override this for a richer UX.

#### async def `send_private_notice(self, chat_id: str, user_id: Optional[str], content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a notice privately when the platform supports it.

The default implementation falls back to a normal send so callers can
use one code path across platforms.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Send a typing indicator.

Override in subclasses if the platform supports it.
metadata: optional dict with platform-specific context (e.g. thread_id for Slack).

#### async def `stop_typing(self, chat_id: str) -> None`

Stop a persistent typing indicator (if the platform uses one).

Override in subclasses that start background typing loops.
Default is a no-op for platforms with one-shot typing indicators.

#### async def `send_multiple_images(self, chat_id: str, images: List[Tuple[str, str]], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send a batch of images.

Accepts ``http(s)://``, ``file://`` URIs in the first tuple
element.

Default implementation sends each item individually,
routing animated GIFs through ``send_animation`` and local
files through ``send_image_file``.

Override in subclasses to bundle into a single native API call
(e.g. Signal's multi-attachment RPC)

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an image natively via the platform API.

Override in subclasses to send images as proper attachments
instead of plain-text URLs. Default falls back to sending the
URL as a text message.

#### async def `send_animation(self, chat_id: str, animation_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an animated GIF natively via the platform API.

Override in subclasses to send GIFs as proper animations
(e.g., Telegram send_animation) so they auto-play inline.
Default falls back to send_image.

#### staticmethod `extract_images(content: str) -> Tuple[List[Tuple[str, str]], str]`

Extract image URLs from markdown and HTML image tags in a response.

Finds patterns like:
- ![alt text](https://example.com/image.png)
- <img src="https://example.com/image.png">
- <img src="https://example.com/image.png"></img>

Args:
    content: The response text to scan.

Returns:
    Tuple of (list of (url, alt_text) pairs, cleaned content with image tags removed).

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send an audio file as a native voice message via the platform API.

Override in subclasses to send audio as voice bubbles (Telegram)
or file attachments (Discord). Default falls back to a friendly
notice — never echo the local audio_path into chat, since it is a
host filesystem path that would leak the Hermes home layout.

#### def `prepare_tts_text(self, text: str) -> str`

Prepare text for TTS. Override to filter tool output, code, etc.

Default strips markdown formatting and truncates to 4000 chars.

#### async def `play_tts(self, chat_id: str, audio_path: str, **kwargs) -> SendResult`

Play auto-TTS audio for voice replies.

Override in subclasses for invisible playback (e.g. Web UI).
Default falls back to send_voice (shows audio player).

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a video natively via the platform API.

Override in subclasses to send videos as inline playable media.
Default falls back to a friendly notice — never echo the local
video_path into chat, since it is a host filesystem path that
would leak the Hermes home layout.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a document/file natively via the platform API.

Override in subclasses to send files as downloadable attachments.
Default falls back to a friendly notice — never echo the local
file_path into chat, since it is a host filesystem path that
would leak the Hermes home layout.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a local image file natively via the platform API.

Unlike send_image() which takes a URL, this takes a local file path.
Override in subclasses for native photo attachments. Default falls
back to a friendly notice — never echo the local image_path into
chat, since it is a host filesystem path that would leak the
Hermes home layout.

#### staticmethod `validate_media_delivery_path(path: str) -> Optional[str]`

Return a resolved path if it is safe for native attachment upload.

#### staticmethod `filter_media_delivery_paths(media_files) -> List[Tuple[str, bool]]`

Drop unsafe MEDIA paths and normalize accepted paths.

#### staticmethod `filter_local_delivery_paths(file_paths) -> List[str]`

Drop unsafe bare local file paths and normalize accepted paths.

#### staticmethod `extract_media(content: str) -> Tuple[List[Tuple[str, bool]], str]`

Extract MEDIA:<path> tags and [[audio_as_voice]] directives from response text.

The TTS tool returns responses like:
    [[audio_as_voice]]
    MEDIA:/path/to/audio.ogg

Skills that produce large/lossless images (e.g. info-graph, where a
rendered JPG is 1-2 MB but Telegram's sendPhoto recompresses to
~200 KB at 1280px) can use ``[[as_document]]`` to request unmodified
delivery via sendDocument instead of sendPhoto/sendMediaGroup. The
directive is detected at the dispatch sites (which have access to the
original response); this method just strips it so it never leaks into
user-visible text. Per-file granularity is intentionally not exposed —
when an agent emits ``[[as_document]]`` once, every image path in the
same response is delivered as a document, mirroring the all-or-nothing
scope of ``[[audio_as_voice]]``.

Args:
    content: The response text to scan.

Returns:
    Tuple of (list of (path, is_voice) pairs, cleaned content with tags removed).

#### staticmethod `strip_media_directives_for_display(text: str) -> str`

Strip MEDIA: directives from streamed/display text.

Known-extension tags are removed unconditionally (same as
``MEDIA_TAG_CLEANUP_RE``). Extension-less tags are removed only when
``validate_media_delivery_path`` accepts the path so undeliverable
paths stay visible for debugging.

#### staticmethod `extract_local_files(content: str) -> Tuple[List[str], str]`

Detect bare local file paths in response text for native delivery.

Matches absolute paths (/...) and tilde paths (~/) ending in common
image, video, audio, or document extensions.  Validates each
candidate with ``os.path.isfile()`` to avoid false positives from
URLs or non-existent paths.

The extension list is broader than just images/video so the agent
can produce arbitrary artifacts (charts, PDFs, spreadsheets, code
archives, CSVs) and have them ship to the user as native uploads
without needing an explicit ``MEDIA:`` tag.  Image / video
extensions still embed inline where the platform supports it;
document extensions route through ``send_document``.  The dispatch
partition lives in ``gateway/run.py``.

Paths inside fenced code blocks (``` ... ```) and inline code
(`...`) are ignored so that code samples are never mutilated.

Returns:
    Tuple of (list of expanded file paths, cleaned text with the
    raw path strings removed).

#### def `pause_typing_for_chat(self, chat_id: str) -> None`

Pause typing indicator for a chat (e.g. during approval waits).

Thread-safe (CPython GIL) — can be called from the sync agent thread
while ``_keep_typing`` runs on the async event loop.

#### def `resume_typing_for_chat(self, chat_id: str) -> None`

Resume typing indicator for a chat after approval resolves.

#### async def `interrupt_session_activity(self, session_key: str, chat_id: str, metadata = None) -> None`

Signal the active session loop to stop and clear typing immediately.

#### def `register_post_delivery_callback(self, session_key: str, callback: Callable, generation: int | None = None) -> None`

Register a deferred callback to fire after the main response.

``generation`` lets callers tie the callback to a specific gateway run
generation so stale runs cannot clear callbacks owned by a fresher run.

If a callback for the same ``session_key`` (and generation, when set)
is already registered, the new callback is chained — both fire, in
registration order, with per-callback exception isolation. This lets
independent features (background-review release + temporary-bubble
cleanup) coexist without clobbering each other. Stale-generation
callers never overwrite a fresher generation's slot.

#### def `pop_post_delivery_callback(self, session_key: str, generation: int | None = None) -> Callable | None`

Pop a deferred callback, optionally requiring generation ownership.

#### async def `on_processing_start(self, event: MessageEvent) -> None`

Hook called when background processing begins.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Hook called when background processing completes.

#### async def `cancel_session_processing(self, session_key: str, release_guard: bool = True, discard_pending: bool = True) -> None`

Cancel in-flight processing for a single session.

``release_guard=False`` keeps the adapter-level session guard in place
so reset-like commands can finish atomically before follow-up messages
are allowed to start a fresh background task.

Bounded by a 5s timeout so a wedged finally block in the cancelled
task (typing-task cleanup, on_processing_complete hook, etc.) can't
stall the calling dispatch coroutine — particularly under pytest-
asyncio where the event loop's cancellation-propagation semantics
differ subtly from a bare ``asyncio.run`` harness.

#### async def `handle_message(self, event: MessageEvent) -> None`

Process an incoming message.

This method returns quickly by spawning background tasks.
This allows new messages to be processed even while an agent is running,
enabling interruption support.

#### async def `cancel_background_tasks(self) -> None`

Cancel any in-flight background message-processing tasks.

Used during gateway shutdown/replacement so active sessions from the old
process do not keep running after adapters are being torn down.

Each cancelled task is awaited with a 5s bound so a wedged finally
(typing-task cleanup, on_processing_complete hook) can't stall the
whole shutdown path.  Stragglers are released from our tracking and
allowed to finish unwinding on their own.

#### def `has_pending_interrupt(self, session_key: str) -> bool`

Check if there's a pending interrupt for a session.

#### def `get_pending_message(self, session_key: str) -> Optional[MessageEvent]`

Get and clear any pending message for a session.

#### def `build_source(self, chat_id: str, chat_name: Optional[str] = None, chat_type: str = 'dm', user_id: Optional[str] = None, user_name: Optional[str] = None, thread_id: Optional[str] = None, chat_topic: Optional[str] = None, user_id_alt: Optional[str] = None, chat_id_alt: Optional[str] = None, is_bot: bool = False, scope_id: Optional[str] = None, guild_id: Optional[str] = None, parent_chat_id: Optional[str] = None, message_id: Optional[str] = None, role_authorized: bool = False, auto_thread_created: bool = False, auto_thread_initial_name: Optional[str] = None) -> SessionSource`

Helper to build a SessionSource for this platform.

When ``gateway.profile_routes`` is configured, the routing engine
resolves the matching profile from guild/chat/thread and stamps it on
``source.profile``. Downstream code (``_resolve_profile_home_for_source``
in run.py) reads that field to enter ``_profile_runtime_scope`` for
per-profile HERMES_HOME isolation.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Get information about a chat/channel.

Returns dict with at least:
- name: Chat name
- type: "dm", "group", "channel"

#### def `format_message(self, content: str) -> str`

Format a message for this platform.

Override in subclasses to handle platform-specific formatting
(e.g., Telegram MarkdownV2, Discord markdown).

Default implementation returns content as-is.

#### staticmethod `truncate_message(content: str, max_length: int = 4096, len_fn: Optional['Callable[[str], int]'] = None) -> List[str]`

Split a long message into chunks, preserving code block boundaries.

When a split falls inside a triple-backtick code block, the fence is
closed at the end of the current chunk and reopened (with the original
language tag) at the start of the next chunk.  Multi-chunk responses
receive indicators like ``(1/3)``.

Args:
    content: The full message content
    max_length: Maximum length per chunk (platform-specific)
    len_fn: Optional length function for measuring string length.
             Defaults to ``len`` (Unicode code-points).  Pass
             ``utf16_len`` for platforms that measure message
             length in UTF-16 code units (e.g. Telegram).

Returns:
    List of message chunks


### 顶层函数

#### def `should_send_media_as_audio(platform, ext: str, is_voice: bool = False) -> bool`

Return True when a media file should use the platform's audio sender.

Other platforms: every recognized audio extension routes through the
audio sender.

Telegram: the Bot API only accepts MP3/M4A for sendAudio and
Opus/OGG for sendVoice. Opus/OGG is only routed as audio when the
caller flagged ``is_voice=True`` (so we don't turn a regular audio
attachment into a voice bubble just because the file happens to be
Opus). Everything else falls through to document delivery by
returning ``False``.

#### def `utf16_len(s: str) -> int`

Count UTF-16 code units in *s*.

Telegram's message-length limit (4 096) is measured in UTF-16 code units,
**not** Unicode code-points.  Characters outside the Basic Multilingual
Plane (emoji like 😀, CJK Extension B, musical symbols, …) are encoded as
surrogate pairs and therefore consume **two** UTF-16 code units each, even
though Python's ``len()`` counts them as one.

Ported from nearai/ironclaw#2304 which discovered the same discrepancy in
Rust's ``chars().count()``.

#### def `is_network_accessible(host: str) -> bool`

Return True if *host* would expose the server beyond loopback.

Loopback addresses (127.0.0.1, ::1, IPv4-mapped ::ffff:127.0.0.1)
are local-only.  Unspecified addresses (0.0.0.0, ::) bind all
interfaces.  Hostnames are resolved; DNS failure fails closed.

#### def `should_bypass_proxy(target_hosts: str | list[str] | tuple[str, ...] | set[str] | None) -> bool`

Return True when NO_PROXY/no_proxy matches at least one target host.

Supports exact hosts, domain suffixes, wildcard suffixes, IP literals,
CIDR ranges, optional host:port entries, and ``*``.

#### def `resolve_proxy_url(platform_env_var: str | None = None, target_hosts: str | list[str] | tuple[str, ...] | set[str] | None = None) -> str | None`

Return a proxy URL from env vars, or macOS system proxy.

Check order:
  0. *platform_env_var* (e.g. ``DISCORD_PROXY``) — highest priority
  1. HTTPS_PROXY / HTTP_PROXY / ALL_PROXY (and lowercase variants)
  2. macOS system proxy via ``scutil --proxy`` (auto-detect)

Returns *None* if no proxy is found, or if NO_PROXY/no_proxy matches one
of ``target_hosts``.

#### def `proxy_kwargs_for_bot(proxy_url: str | None) -> dict`

Build kwargs for ``commands.Bot()`` / ``discord.Client()`` with proxy.

Returns:
  - SOCKS URL  → ``{"connector": ProxyConnector(..., rdns=True)}``
  - HTTP URL   → ``{"proxy": url}``
  - *None*     → ``{}``

``rdns=True`` forces remote DNS resolution through the proxy — required
by many SOCKS implementations (Shadowrocket, Clash) and essential for
bypassing DNS pollution behind the GFW.

#### def `proxy_kwargs_for_aiohttp(proxy_url: str | None) -> tuple[dict, dict]`

Build kwargs for standalone ``aiohttp.ClientSession`` with proxy.

Returns ``(session_kwargs, request_kwargs)`` where:
  - With aiohttp-socks → ``({"connector": ProxyConnector(...)}, {})``
    for *all* proxy schemes (SOCKS **and** HTTP/HTTPS).
  - HTTP without aiohttp-socks → ``({}, {"proxy": url})``.
  - None → ``({}, {})``.

Prefer the connector path: it works transparently with libraries
(like mautrix) that call ``session.request()`` without forwarding
per-request ``proxy=`` kwargs.

Usage::

    sess_kw, req_kw = proxy_kwargs_for_aiohttp(proxy_url)
    async with aiohttp.ClientSession(**sess_kw) as session:
        async with session.get(url, **req_kw) as resp:
            ...

#### def `is_host_excluded_by_no_proxy(hostname: str, no_proxy_value: str | None = None) -> bool`

Return True when ``hostname`` matches a ``NO_PROXY`` entry.

Supports comma- or whitespace-separated entries with optional leading dots
and ``*.`` wildcards, which match both the apex domain and subdomains.

#### def `safe_url_for_log(url: str, max_len: int = 80) -> str`

Return a URL string safe for logs (no query/fragment/userinfo).

#### def `get_inbound_media_max_bytes() -> int`

Return the max inbound image/audio/video bytes allowed in memory.

Reads ``gateway.max_inbound_media_bytes`` from config.yaml. ``0`` (or a
negative / unparseable value) disables the cap. Non-fatal if config is
unreadable — falls back to the default.

#### def `validate_inbound_media_size(size: int, media_type: str = 'media', max_bytes: Optional[int] = None) -> None`

Raise ``ValueError`` if an inbound media payload exceeds the cap.

A ``max_bytes`` of ``0`` (or the configured cap resolving to ``0``)
disables the check entirely. Passing ``max_bytes`` lets callers resolve
the limit once and reuse it across an incremental read.

**异常**: `ValueError`

#### def `get_image_cache_dir() -> Path`

Return the image cache directory, creating it if it doesn't exist.

#### def `cache_image_from_bytes(data: bytes, ext: str = '.jpg') -> str`

Save raw image bytes to the cache and return the absolute file path.

Args:
    data: Raw image bytes.
    ext:  File extension including the dot (e.g. ".jpg", ".png").

Returns:
    Absolute path to the cached image file as a string.

Raises:
    ValueError: If *data* does not look like a valid image (e.g. an HTML
        error page returned by the upstream server).

**异常**: `ValueError`

#### def `cache_image_from_url(url: str, ext: str = '.jpg', retries: int = 2) -> str`

Download an image from a URL and save it to the local cache.

Retries on transient failures (timeouts, 429, 5xx) with exponential
backoff so a single slow CDN response doesn't lose the media.

Args:
    url: The HTTP/HTTPS URL to download from.
    ext: File extension including the dot (e.g. ".jpg", ".png").
    retries: Number of retry attempts on transient failures.

Returns:
    Absolute path to the cached image file as a string.

Raises:
    ValueError: If the URL targets a private/internal network (SSRF protection).

**异常**: `ValueError`

#### def `cleanup_image_cache(max_age_hours: int = 24) -> int`

Delete cached images older than *max_age_hours*.

Returns the number of files removed.

#### def `get_audio_cache_dir() -> Path`

Return the audio cache directory, creating it if it doesn't exist.

#### def `cache_audio_from_bytes(data: bytes, ext: str = '.ogg') -> str`

Save raw audio bytes to the cache and return the absolute file path.

Args:
    data: Raw audio bytes.
    ext:  File extension including the dot (e.g. ".ogg", ".mp3").

Returns:
    Absolute path to the cached audio file as a string.

#### def `cache_audio_from_url(url: str, ext: str = '.ogg', retries: int = 2) -> str`

Download an audio file from a URL and save it to the local cache.

Retries on transient failures (timeouts, 429, 5xx) with exponential
backoff so a single slow CDN response doesn't lose the media.

Args:
    url: The HTTP/HTTPS URL to download from.
    ext: File extension including the dot (e.g. ".ogg", ".mp3").
    retries: Number of retry attempts on transient failures.

Returns:
    Absolute path to the cached audio file as a string.

Raises:
    ValueError: If the URL targets a private/internal network (SSRF protection).

**异常**: `ValueError`

#### def `get_video_cache_dir() -> Path`

Return the video cache directory, creating it if it doesn't exist.

#### def `cache_video_from_bytes(data: bytes, ext: str = '.mp4') -> str`

Save raw video bytes to the cache and return the absolute file path.

#### def `validate_media_delivery_path(path: str) -> Optional[str]`

Return a safe absolute file path for native media delivery, else None.

Default mode (single-user / private gateway): accept any existing regular
file that isn't under the credential / system-path denylist
(``_MEDIA_DELIVERY_DENIED_PREFIXES`` + ``~/.ssh``, ``~/.aws``, etc.).
This matches the symmetry of inbound delivery — Telegram/Discord/Slack
will hand the agent any file the user uploads, and the agent can hand
back any file that isn't a credential.

Strict mode (opt-in via ``gateway.strict`` in ``config.yaml`` or
``HERMES_MEDIA_DELIVERY_STRICT=1``): the file MUST live under a
Hermes-managed cache, under an operator-allowlisted root
(``HERMES_MEDIA_ALLOW_DIRS``), or be freshly produced inside the
configured recency window. Suitable for public-facing bots where
prompt injection from one user shouldn't be able to exfiltrate the
host's secrets to that same user.

Symlinks are resolved before any containment / denylist check.

#### def `get_document_cache_dir() -> Path`

Return the document cache directory, creating it if it doesn't exist.

#### def `cache_document_from_bytes(data: bytes, filename: str) -> str`

Save raw document bytes to the cache and return the absolute file path.

The cached filename preserves the original human-readable name with a
unique prefix: ``doc_{uuid12}_{original_filename}``.

Args:
    data: Raw document bytes.
    filename: Original filename (e.g. "report.pdf").

Returns:
    Absolute path to the cached document file as a string.

Raises:
    ValueError: If the sanitized path escapes the cache directory.

**异常**: `ValueError`

#### def `cleanup_document_cache(max_age_hours: int = 24) -> int`

Delete cached documents older than *max_age_hours*.

Returns the number of files removed.

#### def `cache_media_bytes(data: bytes, filename: str = '', mime_type: str = '', default_kind: Optional[str] = None) -> Optional[CachedMedia]`

Classify and cache raw attachment bytes; return a CachedMedia or None.

``default_kind`` ("image"/"video"/"audio"/"document") biases classification
when the extension/MIME are ambiguous — e.g. a Telegram native photo whose
file has no usable name. Any non-image/video/audio file is cached as a
document and surfaced to the agent (arbitrary types get
``application/octet-stream``); only images that fail validation
(``cache_image_from_bytes`` raises ValueError) return None.

#### def `coerce_plaintext_gateway_command(event: MessageEvent) -> None`

Rewrite a tiny set of DM plaintext admin phrases into slash commands.

This keeps high-impact operational phrases like ``restart gateway`` out of
the LLM/tool path, where they can trigger a self-restart from inside the
currently running agent and leave the gateway stuck in ``draining`` while it
waits for that same agent to finish.

Scope is intentionally narrow: DM text messages only, exact restart-style
phrases only. Group chats keep natural-language semantics.

#### def `classify_send_error(exc: Optional[BaseException], error_text: str = '') -> str`

Map a send exception / error string to a :data:`SEND_ERROR_KINDS` value.

Platform-neutral: matches on the lowercased text of ``exc`` (and/or the
explicit ``error_text``) against the substrings the major messaging APIs
use.  Conservative — anything unrecognized returns ``"unknown"`` so callers
never mistake an unclassified failure for a benign one.

#### def `is_chat_level_not_found(exc: Optional[BaseException] = None, error_text: str = '') -> bool`

Whether a ``not_found`` failure means the *whole chat* is gone.

:func:`classify_send_error` collapses chat-level and thread/topic/message-level
not_found into the single ``"not_found"`` kind.  Only the chat-level case (the
chat/user/group no longer exists) should mark a delivery target dead; a deleted
forum topic or an edited-away message leaves the parent chat reachable.  When
both a chat-level and a sub-chat marker are present, the sub-chat reading wins
(conservative: never kill a chat that may still be reachable).

Argument order mirrors :func:`classify_send_error` (``exc`` first) and both
share :func:`_error_blob`, so the two classifiers cannot disagree on the same
failure.

#### def `merge_pending_message_event(pending_messages: Dict[str, MessageEvent], session_key: str, event: MessageEvent, merge_text: bool = False) -> None`

Store or merge a pending event for a session.

Photo bursts/albums often arrive as multiple near-simultaneous PHOTO
events. Merge those into the existing queued event so the next turn sees
the whole burst.

When ``merge_text`` is enabled, rapid follow-up TEXT events are appended
instead of replacing the pending turn. This is used for Telegram bursty
follow-ups so a multi-part user thought is not silently truncated to only
the last queued fragment.

#### def `resolve_channel_prompt(config_extra: dict, channel_id: str, parent_id: str | None = None) -> str | None`

Resolve a per-channel ephemeral prompt from platform config.

Looks up ``channel_prompts`` in the adapter's ``config.extra`` dict.
Prefers an exact match on *channel_id*; falls back to *parent_id*
(useful for forum threads / child channels inheriting a parent prompt).

Returns the prompt string, or None if no match is found.  Blank/whitespace-
only prompts are treated as absent.

#### def `resolve_channel_skills(config_extra: dict, channel_id: str, parent_id: str | None = None) -> list[str] | None`

Resolve auto-loaded skill(s) for a channel/thread from platform config.

Looks up ``channel_skill_bindings`` in the adapter's ``config.extra`` dict.

Config format::

    channel_skill_bindings:
      - id: "C0123"          # Slack channel ID or Discord channel/forum ID
        skills: ["skill-a", "skill-b"]
      - id: "D0ABCDE"
        skill: "solo-skill"  # single string also accepted

Prefers an exact match on *channel_id*; falls back to *parent_id*
(useful for forum threads / Slack threads inheriting the parent channel's
binding).

Returns a deduplicated list of skill names (order preserved), or None if
no match is found.


## gateway.platforms.bluebubbles

### 模块文档

BlueBubbles iMessage platform adapter.

Uses the local BlueBubbles macOS server for outbound REST sends and inbound
webhooks.  Supports text messaging, media attachments (images, voice, video,
documents), tapback reactions, typing indicators, and read receipts.

Architecture based on PR #5869 (benjaminsehl) with inbound attachment
downloading from PR #4588 (YuhangLin).

### class BlueBubblesAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 35（公开 15）

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### staticmethod `truncate_message(content: str, max_length: int = MAX_TEXT_LENGTH) -> List[str]`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_animation(self, chat_id: str, animation_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

#### async def `stop_typing(self, chat_id: str) -> None`

#### async def `mark_read(self, chat_id: str) -> bool`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### def `format_message(self, content: str) -> str`


### 顶层函数

#### def `check_bluebubbles_requirements() -> bool`


## gateway.platforms.helpers

### 模块文档

Shared helper classes for gateway platform adapters.

Extracts common patterns that were duplicated across 5-7 adapters:
message deduplication, text batch aggregation, markdown stripping,
and thread participation tracking.

### class MessageDeduplicator

> 继承: `object` ｜ 方法数: 5（公开 4）

TTL-based message deduplication cache.

Replaces the identical ``_seen_messages`` / ``_is_duplicate()`` pattern
previously duplicated in discord, slack, dingtalk, wecom, weixin,
mattermost, and feishu adapters.

Usage::

    self._dedup = MessageDeduplicator()

    # In message handler:
    if self._dedup.is_duplicate(msg_id):
        return

#### def `__init__(max_size: int = 2000, ttl_seconds: float = 300)`

#### def `is_duplicate(self, msg_id: str) -> bool`

Return True if *msg_id* was already seen within the TTL window.

#### def `contains(self, msg_id: str) -> bool`

Return whether *msg_id* is live in the cache without inserting it.

#### def `discard(self, msg_id: str) -> None`

Release a claimed message ID after cancelled/failed handoff.

#### def `clear(self)`

Clear all tracked messages.


### class TextBatchAggregator

> 继承: `object` ｜ 方法数: 5（公开 3）

Aggregates rapid-fire text events into single messages.

Replaces the ``_enqueue_text_event`` / ``_flush_text_batch`` pattern
previously duplicated in telegram, discord, matrix, wecom, and feishu.

Usage::

    self._text_batcher = TextBatchAggregator(
        handler=self._message_handler,
        batch_delay=0.6,
        split_threshold=1900,
    )

    # In message dispatch:
    if msg_type == MessageType.TEXT and self._text_batcher.is_enabled():
        self._text_batcher.enqueue(event, session_key)
        return

#### def `__init__(handler, batch_delay: float = 0.6, split_delay: float = 2.0, split_threshold: int = 4000)`

#### def `is_enabled(self) -> bool`

Return True if batching is active (delay > 0).

#### def `enqueue(self, event: MessageEvent, key: str) -> None`

Add *event* to the pending batch for *key*.

#### def `cancel_all(self) -> None`

Cancel all pending flush tasks.


### class ThreadParticipationTracker

> 继承: `object` ｜ 方法数: 7（公开 2）

Persistent tracking of threads the bot has participated in.

Replaces the identical ``_load/_save_participated_threads`` +
``_mark_thread_participated`` pattern previously duplicated in
discord.py and matrix.py.

Usage::

    self._threads = ThreadParticipationTracker("discord")

    # Check membership:
    if thread_id in self._threads:
        ...

    # Mark participation:
    self._threads.mark(thread_id)

#### def `__init__(platform_name: str, max_tracked: int = 500)`

#### def `mark(self, thread_id: str) -> None`

Mark *thread_id* as participated and persist.

#### def `clear(self) -> None`


### 顶层函数

#### def `strip_markdown(text: str) -> str`

Strip markdown formatting for plain-text platforms (SMS, iMessage, etc.).

Replaces the identical ``_strip_markdown()`` functions previously
duplicated in sms.py, bluebubbles.py, and feishu.py.

#### def `redact_phone(phone: str) -> str`

Redact a phone number for logging, preserving country code and last 4.

Replaces the identical ``_redact_phone()`` functions in signal.py,
sms.py, and bluebubbles.py.

#### def `is_table_row(line: str) -> bool`

Return True if *line* could plausibly be a table data row.

#### def `split_markdown_table_row(line: str) -> list[str]`

Split a GFM table row into stripped cell values.

#### def `convert_table_to_bullets(text: str) -> str`

Rewrite GFM pipe tables into bold-heading + bullet groups.

Tables inside fenced code blocks are left alone.


## gateway.platforms.msgraph_webhook

### 模块文档

Microsoft Graph webhook adapter for change-notification ingress.

### class MSGraphWebhookAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 24（公开 5）

Receive Microsoft Graph change notifications and surface them internally.

#### def `__init__(config: PlatformConfig)`

#### def `set_notification_scheduler(self, scheduler: Optional[NotificationScheduler]) -> None`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`


### 顶层函数

#### def `check_msgraph_webhook_requirements() -> bool`

Return whether required webhook dependencies are available.


## gateway.platforms.qqbot.__init__

### 模块文档

QQBot platform package.

Re-exports the main adapter symbols from ``adapter.py`` (the original
``qqbot.py``) so that **all existing import paths remain unchanged**::

    from gateway.platforms.qqbot import QQAdapter          # works
    from gateway.platforms.qqbot import check_qq_requirements  # works

New modules:
    - ``constants`` — shared constants (API URLs, timeouts, message types)
    - ``utils`` — User-Agent builder, config helpers
    - ``crypto`` — AES-256-GCM key generation and decryption
    - ``onboard`` — QR-code scan-to-configure flow

## gateway.platforms.qqbot.adapter

### 模块文档

QQ Bot platform adapter using the Official QQ Bot API (v2).

Connects to the QQ Bot WebSocket Gateway for inbound events and uses the
REST API (``api.sgroup.qq.com``) for outbound messages and media uploads.

Configuration in config.yaml:
    platforms:
      qq:
        enabled: true
        extra:
          app_id: "your-app-id"            # or QQ_APP_ID env var
          client_secret: "your-secret"     # or QQ_CLIENT_SECRET env var
          markdown_support: true           # enable QQ markdown (msg_type 2)
          dm_policy: "pairing"             # open | allowlist | disabled | pairing
          allow_from: ["openid_1"]
          group_policy: "pairing"          # open | allowlist | disabled | pairing
          group_allow_from: ["group_openid_1"]
          stt:                             # Voice-to-text config (optional)
            provider: "zai"                # zai (GLM-ASR), openai (Whisper), etc.
            baseUrl: "https://open.bigmodel.cn/api/coding/paas/v4"
            apiKey: "your-stt-api-key"     # or set QQ_STT_API_KEY env var
            model: "glm-asr"               # glm-asr, whisper-1, etc.

    Voice transcription priority:
      1. QQ's built-in ``asr_refer_text`` (Tencent ASR — free, always tried first)
      2. Configured STT provider via ``stt`` config or ``QQ_STT_*`` env vars

Reference: https://bot.q.qq.com/wiki/develop/api-v2/

### class QQCloseError

> 继承: `Exception` ｜ 方法数: 1（公开 0）

Raised when QQ WebSocket closes with a specific code.

Carries the close code and reason for proper handling in the reconnect loop.

#### def `__init__(code, reason = '')`


### class QQAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 88（公开 20）

QQ Bot adapter backed by the official QQ Bot WebSocket Gateway + REST API.

#### property `is_connected(self) -> bool`

Return True only when the QQ WebSocket transport is usable.

#### def `__init__(config: PlatformConfig)`

#### property `name(self) -> str`

#### property `enforces_own_access_policy(self) -> bool`

QQBot gates DM/group access at intake via dm_policy/group_policy.

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Authenticate, obtain gateway URL, and open the WebSocket.

Args:
    is_reconnect: False on a cold first boot; True when the
        reconnect watcher is re-establishing this platform after
        an outage. QQBot has no server-side update queue so this
        flag is accepted for interface conformance only.

#### async def `disconnect(self) -> None`

Close all connections and stop listeners.

#### async def `handle_message(self, event: MessageEvent) -> None`

Cache the last message ID per chat, then delegate to base.

#### def `set_interaction_callback(self, callback: Optional[Callable[[InteractionEvent], Awaitable[None]]]) -> None`

Register (or clear) the interaction callback.

Invoked once per ``INTERACTION_CREATE`` event *after* the adapter has
ACKed the interaction. The callback is responsible for routing the
button click to the right subsystem (approval resolver, update-prompt
resolver, etc.) based on the ``button_data`` payload.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a text or markdown message to a QQ user or group.

Applies format_message(), splits long messages via truncate_message(),
and retries transient failures with exponential backoff.

#### async def `send_with_keyboard(self, chat_id: str, content: str, keyboard: InlineKeyboard, reply_to: Optional[str] = None) -> SendResult`

Send a single text message with an inline keyboard attached.

Unlike :meth:`send`, this does NOT split long content into chunks —
a keyboard message has exactly one interactive surface, and splitting
would orphan the buttons from the first chunk. Callers should keep
approval/update-prompt bodies short.

Guild (channel) chats don't support inline keyboards; returns a
non-retryable failure for those.

#### async def `send_approval_request(self, chat_id: str, req: ApprovalRequest, reply_to: Optional[str] = None) -> SendResult`

Send a 3-button approval request (``allow-once / allow-always / deny``).

The rendered text comes from :func:`build_approval_text`; callers can
override by passing a custom :class:`ApprovalRequest`.

Users click the button → ``INTERACTION_CREATE`` fires → the adapter's
registered :meth:`set_interaction_callback` handler decodes
``button_data`` via :func:`parse_approval_button_data`.

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[Dict[str, Any]] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Send a button-based exec-approval prompt for a dangerous command.

Called by ``gateway/run.py``'s ``_approval_notify_sync`` when the
agent is blocked waiting for approval. Button clicks resolve via
:func:`tools.approval.resolve_gateway_approval` — dispatched by the
adapter's interaction callback (:meth:`_default_interaction_dispatch`).

#### async def `send_update_prompt(self, chat_id: str, prompt: str, default: str = '', session_key: str = '', metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a Yes/No update-confirmation prompt with inline buttons.

Matches the cross-adapter contract used by
``gateway/run.py``'s ``hermes update --gateway`` watcher. Button
clicks surface as ``INTERACTION_CREATE`` with
``button_data = 'update_prompt:y'`` or ``'update_prompt:n'``;
the adapter's interaction callback writes the answer to
``~/.hermes/.update_response`` so the detached update process
can read it.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an image natively via QQ Bot API upload.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a local image file natively.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a voice message natively.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a video natively.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a file/document natively.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Send an input notify to a C2C user (only supported for C2C).

Debounced to one request per ~50s (the API sets a 60s indicator).
The QQ API requires the originating message ID — retrieved from
``_last_msg_id`` which is populated by ``_on_message``.

#### def `format_message(self, content: str) -> str`

Format message for QQ.

When markdown_support is enabled, content is sent as-is (QQ renders it).
When disabled, strip markdown via shared helper (same as BlueBubbles/SMS).

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return chat info based on chat type heuristics.


### 顶层函数

#### def `check_qq_requirements() -> bool`

Check if QQ runtime dependencies are available.


## gateway.platforms.qqbot.chunked_upload

### 模块文档

QQ Bot chunked upload flow.

The QQ v2 API caps inline base64 uploads (``file_data`` / ``url``) at ~10 MB.
For files between 10 MB and ~100 MB we have to use the three-step chunked
upload flow::

    1. POST /v2/{users|groups}/{id}/upload_prepare
       → returns upload_id, block_size, and an array of pre-signed COS part URLs.
    2. For each part:
         PUT the part bytes to its pre-signed COS URL,
         then POST /v2/{users|groups}/{id}/upload_part_finish to acknowledge.
    3. POST /v2/{users|groups}/{id}/files with {"upload_id": ...}
       → returns the ``file_info`` token the caller uses in a RichMedia
       message.

Error-code semantics (from the QQ Bot v2 API spec):

- ``40093001`` — ``upload_part_finish`` retryable. Retry until the server-provided
  ``retry_timeout`` elapses (or a local cap).
- ``40093002`` — daily cumulative upload quota exceeded. Not retryable; surface
  as :class:`UploadDailyLimitExceededError` so the caller can build a
  user-friendly reply.

Exceptions:

- :class:`UploadDailyLimitExceededError` — daily quota hit (non-retryable).
- :class:`UploadFileTooLargeError` — file exceeds the platform per-file limit.
- :class:`RuntimeError` — generic upload failure (network, part PUT, complete).

Ported from WideLee's qqbot-agent-sdk v1.2.2 (``media_loader.py::ChunkedUploader``)
so the heavy-upload path stays in-tree. Authorship preserved via Co-authored-by.

### class UploadDailyLimitExceededError

> 继承: `Exception` ｜ 方法数: 2（公开 1）

Raised when ``upload_prepare`` returns biz_code 40093002.

The daily cumulative upload quota for this bot has been reached. Callers
should surface :attr:`file_name` + :attr:`file_size_human` so the model
can compose a helpful reply.

#### def `__init__(file_name: str, file_size: int, message: str = '') -> None`

#### property `file_size_human(self) -> str`


### class UploadFileTooLargeError

> 继承: `Exception` ｜ 方法数: 3（公开 2）

Raised when a file exceeds the platform per-file size limit.

#### def `__init__(file_name: str, file_size: int, limit_bytes: int = 0, message: str = '') -> None`

#### property `file_size_human(self) -> str`

#### property `limit_human(self) -> str`


### class ChunkedUploader

> 继承: `object` ｜ 方法数: 7（公开 1）

Run the prepare → PUT parts → complete sequence.

:param api_request: Bound ``_api_request(method, path, body=..., timeout=...)``
    coroutine from the adapter. Must raise ``RuntimeError`` with the biz_code
    embedded in the message on API errors.
:param http_put: Coroutine ``(url, data, headers, timeout) -> response`` for
    COS part uploads. Typically wraps ``httpx.AsyncClient.put``.
:param log_tag: Log prefix.

#### def `__init__(api_request: ApiRequestFn, http_put: Callable[..., Awaitable[Any]], log_tag: str = 'QQBot') -> None`

#### async def `upload(self, chat_type: str, target_id: str, file_path: str, file_type: int, file_name: str) -> Dict[str, Any]`

Run the full chunked upload and return the ``complete_upload`` response.

:param chat_type: ``'c2c'`` or ``'group'``.
:param target_id: User or group openid.
:param file_path: Absolute path to a local file.
:param file_type: ``MEDIA_TYPE_*`` constant.
:param file_name: Original filename (for upload_prepare).
:returns: The raw response dict from ``complete_upload`` — contains
    ``file_info`` that the caller uses in a RichMedia message body.
:raises UploadDailyLimitExceededError: On biz_code 40093002.
:raises UploadFileTooLargeError: When the file exceeds the platform limit.
:raises RuntimeError: On other API or I/O failures.

**异常**: `UploadDailyLimitExceededError`, `UploadFileTooLargeError`, `RuntimeError`, `ValueError`


### 顶层函数

#### def `format_size(size_bytes: int) -> str`

Return a human-readable file size string (e.g. ``'12.3 MB'``).


## gateway.platforms.qqbot.constants

### 模块文档

QQBot package-level constants shared across adapter, onboard, and other modules.

## gateway.platforms.qqbot.crypto

### 模块文档

AES-256-GCM utilities for QQBot scan-to-configure credential decryption.

### 顶层函数

#### def `generate_bind_key() -> str`

Generate a 256-bit random AES key and return it as base64.

The key is passed to ``create_bind_task`` so the server can encrypt
the bot's *client_secret* before returning it.  Only this CLI holds
the key, ensuring the secret never travels in plaintext.

#### def `decrypt_secret(encrypted_base64: str, key_base64: str) -> str`

Decrypt a base64-encoded AES-256-GCM ciphertext.

Ciphertext layout (after base64-decoding)::

    IV (12 bytes) ‖ ciphertext (N bytes) ‖ AuthTag (16 bytes)

Args:
    encrypted_base64: The ``bot_encrypt_secret`` value from
        ``poll_bind_result``.
    key_base64: The base64 AES key generated by
        :func:`generate_bind_key`.

Returns:
    The decrypted *client_secret* as a UTF-8 string.


## gateway.platforms.qqbot.keyboards

### 模块文档

QQ Bot inline keyboards + approval / update-prompt senders.

QQ Bot v2 supports attaching inline keyboards to outbound messages. When a
user clicks a button, the platform dispatches an ``INTERACTION_CREATE``
gateway event containing the button's ``data`` payload. The bot must ACK the
interaction promptly via ``PUT /interactions/{id}`` or the user sees an
error indicator on the button.

This module provides:

- :class:`InlineKeyboard` + button dataclasses — serialized into the
  ``keyboard`` field of the outbound message body.
- :func:`build_approval_keyboard` — 3-button ✅ once / ⭐ always / ❌ deny
  keyboard for tool-approval flows.
- :func:`build_update_prompt_keyboard` — Yes/No keyboard for update confirms.
- :func:`parse_approval_button_data` / :func:`parse_update_prompt_button_data`
  — decode the ``button_data`` payload from ``INTERACTION_CREATE``.
- :class:`ApprovalRequest` + :class:`ApprovalSender` — high-level helper that
  builds an approval message with keyboard and posts it to a c2c / group chat.

``button_data`` formats::

    approve:<session_key>:<decision>      # decision = allow-once|allow-always|deny
    update_prompt:<answer>                # answer = y|n

Ported from WideLee's qqbot-agent-sdk v1.2.2 (``approval.py`` + ``dto.py``
keyboard types). Authorship preserved via Co-authored-by.

### class KeyboardButtonPermission

> 继承: `object` ｜ 方法数: 1（公开 1）

Button permission metadata. ``type=2`` means all users can click.

#### def `to_dict(self) -> Dict[str, Any]`


### class KeyboardButtonAction

> 继承: `object` ｜ 方法数: 1（公开 1）

What happens when the button is clicked.

:param type: ``1`` (Callback — triggers ``INTERACTION_CREATE``) or
    ``2`` (Link — opens a URL).
:param data: Payload delivered in ``data.resolved.button_data`` when
    ``type=1``.
:param permission: :class:`KeyboardButtonPermission`.
:param click_limit: Max clicks per user (``1`` = single-use).

#### def `to_dict(self) -> Dict[str, Any]`


### class KeyboardButtonRenderData

> 继承: `object` ｜ 方法数: 1（公开 1）

Visual rendering of a button.

:param label: Pre-click label.
:param visited_label: Post-click label (button stays greyed in place).
:param style: ``0`` = grey, ``1`` = blue.

#### def `to_dict(self) -> Dict[str, Any]`


### class KeyboardButton

> 继承: `object` ｜ 方法数: 1（公开 1）

One button in a keyboard.

:param group_id: Buttons sharing a ``group_id`` are mutually exclusive —
    clicking one greys the rest.

#### def `to_dict(self) -> Dict[str, Any]`


### class KeyboardRow

> 继承: `object` ｜ 方法数: 1（公开 1）

#### def `to_dict(self) -> Dict[str, Any]`


### class KeyboardContent

> 继承: `object` ｜ 方法数: 1（公开 1）

#### def `to_dict(self) -> Dict[str, Any]`


### class InlineKeyboard

> 继承: `object` ｜ 方法数: 1（公开 1）

Top-level keyboard payload — goes into ``MessageToCreate.keyboard``.

#### def `to_dict(self) -> Dict[str, Any]`


### class ApprovalRequest

> 继承: `object` ｜ 方法数: 0（公开 0）

Structured approval-request display data.

:param session_key: Routes the decision back to the waiting caller.
:param title: Short title at the top.
:param description: Optional longer description.
:param command_preview: Command text (exec approvals).
:param cwd: Working directory (exec approvals).
:param tool_name: Tool name (plugin approvals).
:param severity: ``'critical' | 'info' | ''``.
:param timeout_sec: Seconds until the approval expires.


### class ApprovalSender

> 继承: `object` ｜ 方法数: 2（公开 1）

Send an approval-request message with an inline keyboard.

Decoupled from the adapter via callables so it can be unit-tested in
isolation. Pass the adapter's ``_send_message_with_keyboard`` helper
(or any equivalent) as ``post_message``.

#### def `__init__(post_c2c: PostMessageFn, post_group: PostMessageFn, log_tag: str = 'QQBot') -> None`

#### async def `send(self, chat_type: str, chat_id: str, req: ApprovalRequest, msg_id: Optional[str] = None) -> bool`

Send an approval message to *chat_id*.

:param chat_type: ``'c2c'`` or ``'group'``.
:param chat_id: User openid or group openid.
:param req: :class:`ApprovalRequest`.
:param msg_id: Reply-to message id (required for passive messages).
:returns: ``True`` on success, ``False`` on failure.


### class InteractionEvent

> 继承: `object` ｜ 方法数: 1（公开 1）

Parsed ``INTERACTION_CREATE`` event payload.

See https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/interface-framework/event-emit.html

#### property `operator_openid(self) -> str`

Best available operator openid (group → member; c2c → user).


### 顶层函数

#### def `parse_approval_button_data(button_data: str) -> Optional[tuple[str, str]]`

Parse approval ``button_data`` into ``(session_key, decision)``.

:param button_data: Raw ``data.resolved.button_data`` from
    ``INTERACTION_CREATE``.
:returns: ``(session_key, decision)`` or ``None`` if not an approval button.

#### def `parse_update_prompt_button_data(button_data: str) -> Optional[str]`

Parse update-prompt ``button_data`` into ``'y'`` or ``'n'``.

#### def `build_approval_keyboard(session_key: str, allow_permanent: bool = True) -> InlineKeyboard`

Build the approval keyboard, hiding persistent scope when unavailable.

Layout: ``[✅ 允许一次] [⭐ 始终允许] [❌ 拒绝]`` — all three share
``group_id='approval'`` so clicking one greys out the rest.

:param session_key: Embedded into ``button_data`` so the decision
    routes back to the right pending approval.

#### def `build_update_prompt_keyboard() -> InlineKeyboard`

Build a Yes/No keyboard for update confirmation prompts.

#### def `build_approval_text(req: ApprovalRequest) -> str`

Render an :class:`ApprovalRequest` into the message body (markdown).

#### def `parse_interaction_event(raw: Dict[str, Any]) -> InteractionEvent`

Parse a raw ``INTERACTION_CREATE`` dispatch payload (``d``).


## gateway.platforms.qqbot.onboard

### 模块文档

QQBot scan-to-configure (QR code onboard) module.

Mirrors the Feishu onboarding pattern: synchronous HTTP + a single public
entry-point ``qr_register()`` that handles the full flow (create task →
display QR code → poll → decrypt credentials).

Calls the ``q.qq.com`` ``create_bind_task`` / ``poll_bind_result`` APIs to
generate a QR-code URL and poll for scan completion.  On success the caller
receives the bot's *app_id*, *client_secret* (decrypted locally), and the
scanner's *user_openid* — enough to fully configure the QQBot gateway.

Reference: https://bot.q.qq.com/wiki/develop/api-v2/

### class BindStatus

> 继承: `IntEnum` ｜ 方法数: 0（公开 0）

Status codes returned by ``_poll_bind_result``.


### 顶层函数

#### def `build_connect_url(task_id: str) -> str`

Build the QR-code target URL for a given *task_id*.

#### def `qr_register(timeout_seconds: int = 600) -> Optional[dict]`

Run the QQBot scan-to-configure QR registration flow.

Mirrors ``feishu.qr_register()``: handles create → display → poll →
decrypt in one call.  Unexpected errors propagate to the caller.

:returns:
    ``{"app_id": ..., "client_secret": ..., "user_openid": ...}`` on
    success, or ``None`` on failure / expiry / cancellation.


## gateway.platforms.qqbot.utils

### 模块文档

QQBot shared utilities — User-Agent, HTTP helpers, config coercion.

### 顶层函数

#### def `build_user_agent() -> str`

Build a descriptive User-Agent string.

Format::

    QQBotAdapter/<qqbot_version> (Python/<py_version>; <os>; Hermes/<hermes_version>)

Example::

    QQBotAdapter/1.0.0 (Python/3.11.15; darwin; Hermes/0.9.0)

#### def `get_api_headers() -> Dict[str, str]`

Return standard HTTP headers for QQBot API requests.

Includes ``Content-Type``, ``Accept``, and a dynamic ``User-Agent``.
``q.qq.com`` requires ``Accept: application/json`` — without it,
the server returns a JavaScript anti-bot challenge page.

#### def `coerce_list(value: Any) -> List[str]`

Coerce config values into a trimmed string list.

Accepts comma-separated strings, lists, tuples, sets, or single values.


## gateway.platforms.signal

### 模块文档

Signal messenger platform adapter.

Connects to a signal-cli daemon running in HTTP mode.
Inbound messages arrive via SSE (Server-Sent Events) streaming.
Outbound messages and actions use JSON-RPC 2.0 over HTTP.

Based on PR #268 by ibhagwan, rebuilt with bug fixes.

Requires:
  - signal-cli installed and running: signal-cli daemon --http 127.0.0.1:8080
  - SIGNAL_HTTP_URL and SIGNAL_ACCOUNT environment variables set

### class SignalAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 39（公开 17）

Signal messenger adapter using signal-cli HTTP daemon.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to signal-cli daemon and start SSE listener.

#### async def `disconnect(self) -> None`

Stop SSE listener and clean up.

#### def `format_message(self, content: str) -> str`

Strip markdown for plain-text fallback (used by base class).

The actual rich formatting happens in send() via _markdown_to_signal().

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a text message with native Signal formatting.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Send a typing indicator.

base.py's ``_keep_typing`` refresh loop calls this every ~2s while
the agent is processing. If signal-cli returns NETWORK_FAILURE for
this recipient (offline, unroutable, group membership lost, etc.)
the unmitigated behaviour is: a WARNING log every 2 seconds for as
long as the agent keeps running. Instead we:

- silence the WARNING after the first consecutive failure (subsequent
  attempts log at DEBUG) so transport issues are still visible once
  but don't flood the log,
- skip the RPC entirely during an exponential cooldown window once
  three consecutive failures have happened, so we stop hammering
  signal-cli with requests it can't deliver.

A successful sendTyping clears the counters.

#### async def `send_multiple_images(self, chat_id: str, images: List[Tuple[str, str]], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send a batch of images via chunked Signal RPC calls.

Per-image alt texts are dropped — Signal's send RPC only carries
one shared message body. Bad images (download failure, missing
file, oversize) are skipped with a warning so one bad URL
doesn't lose the rest of the batch. ``human_delay`` is ignored:
the rate-limit scheduler handles inter-batch pacing.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, **kwargs) -> SendResult`

Send an image. Supports http(s):// and file:// URLs.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, filename: Optional[str] = None, **kwargs) -> SendResult`

Send a document/file attachment.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a local image file as a native Signal attachment.

Called by the gateway media delivery flow when MEDIA: tags containing
image paths are extracted from agent responses.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send an audio file as a Signal attachment.

Signal does not distinguish voice messages from file attachments at
the API level, so this routes through the same RPC send path.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a video file as a Signal attachment.

#### async def `stop_typing(self, chat_id: str) -> None`

Public interface for stopping typing — called by base adapter's
_keep_typing finally block to clean up platform-level typing tasks.

#### async def `send_reaction(self, chat_id: str, emoji: str, target_author: str, target_timestamp: int) -> bool`

Send a reaction emoji to a specific message via signal-cli RPC.

Args:
    chat_id: The chat (phone number or "group:<id>")
    emoji: Reaction emoji string (e.g. "👀", "✅")
    target_author: Phone number / UUID of the message author
    target_timestamp: Signal timestamp (ms) of the message to react to

#### async def `remove_reaction(self, chat_id: str, target_author: str, target_timestamp: int) -> bool`

Remove a reaction by sending an empty-string emoji.

#### async def `on_processing_start(self, event: MessageEvent) -> None`

React with 👀 when processing begins.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Swap the 👀 reaction for ✅ (success) or ❌ (failure).

On CANCELLED we leave the 👀 in place — no terminal outcome means
the reaction should keep reflecting "in progress" (matches Telegram).

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Get information about a chat/contact.


### 顶层函数

#### def `check_signal_requirements() -> bool`

Check if Signal runtime dependencies are available.

#### def `validate_signal_config(config: PlatformConfig) -> bool`

Check if Signal has enough config to connect.


## gateway.platforms.signal_format

### 模块文档

Shared Signal formatting helpers.

Keep markdown → Signal native formatting conversion in one place so both the
live Signal adapter and standalone send paths emit the same bodyRanges.

### 顶层函数

#### def `markdown_to_signal(text: str) -> tuple[str, list[str]]`

Convert markdown to plain text + Signal textStyles list.

Signal doesn't render markdown. Instead it uses ``bodyRanges`` (exposed by
signal-cli as ``textStyle`` / ``textStyles`` params) with the format
``start:length:STYLE``.

Positions are measured in UTF-16 code units because that's what the Signal
protocol uses.

Supported styles: BOLD, ITALIC, STRIKETHROUGH, MONOSPACE.


## gateway.platforms.signal_rate_limit

### 模块文档

Signal attachment rate-limit scheduler.

Process-wide token-bucket simulator that mirrors the per-account
attachment rate limit signal-cli/Signal-Server enforce. Producers
(``SignalAdapter.send_multiple_images`` and the ``send_message`` tool's
Signal path) call ``acquire(n)`` before an attachment send; on a 429
they call ``feedback(retry_after, n)`` so the model recalibrates from
the server's authoritative hint.

The scheduler serializes concurrent calls through an ``asyncio.Lock``,
giving FIFO fairness across agent sessions sharing one signal-cli
daemon.

### class SignalRateLimitError

> 继承: `Exception` ｜ 方法数: 1（公开 0）

Raised by ``SignalAdapter._rpc`` for rate-limit responses when the
caller has opted in via ``raise_on_rate_limit=True``.

Carries the server-supplied per-token Retry-After (in seconds) on
signal-cli ≥ v0.14.3
``retry_after`` is None when the version doesn't expose it.

#### def `__init__(message: str, retry_after: Optional[float] = None) -> None`


### class SignalSchedulerError

> 继承: `Exception` ｜ 方法数: 0（公开 0）


### class SignalAttachmentScheduler

> 继承: `object` ｜ 方法数: 7（公开 5）

Process-wide token-bucket simulator for Signal attachment sends.

The bucket holds up to ``capacity`` tokens (default 50, matching
Signal's server-side rate-limit bucket size). Each attachment consumes one
token. Tokens refill at ``refill_rate`` tokens/second, calibrated
from the per-token Retry-After hint we get from the server when a
429 fires. Until we've observed one, we use the documented default
(1 token / 4 seconds).

Concurrent ``acquire(n)`` calls serialize through an
``asyncio.Lock`` — natural FIFO across agent sessions hitting the
same daemon.

#### def `__init__(capacity: float = float(SIGNAL_RATE_LIMIT_BUCKET_CAPACITY), default_retry_after: float = float(SIGNAL_RATE_LIMIT_DEFAULT_RETRY_AFTER)) -> None`

#### def `estimate_wait(self, n: int) -> float`

Best-effort estimate of the seconds until ``n`` tokens would
be available. Used to decide whether to emit a user-facing
pacing notice *before* committing to an ``acquire`` that may
block silently. Lock-free; small races vs. concurrent acquires
are benign for an informational notice.

#### async def `acquire(self, n: int) -> float`

Block until at least ``n`` tokens are available, return the
seconds slept.

Does **not** deduct tokens — the bucket is a read-only model of
server-side capacity.  Call ``report_rpc_duration()`` after the
RPC to synchronise the model with the server timeline.

Not perfect in case lots of coroutines try to acquire for big
uploads (``report_rpc_duration`` will take a long time to get hit)
but this is just a simulation. Signal server is ground truth and
will raise rate-limit exceptions triggering requeues.

The lock is released during ``asyncio.sleep`` so other callers
can interleave.  A retry loop re-checks after each sleep in
case the deadline was pessimistic.

**异常**: `SignalSchedulerError`

#### async def `report_rpc_duration(self, rpc_duration: float, n_attachments: int) -> None`

Record an attachment-send RPC that just completed.

Deducts ``n_attachments`` tokens without crediting refill during
the upload window. Signal's server checks the bucket at RPC start
and does *not* refill during request processing — refill resumes
after the response. Crediting upload-time refill causes cumulative
drift that eventually triggers 429s.

Advances ``last_refill`` so the next ``acquire`` / ``_refill``
starts counting from this point.

#### def `feedback(self, retry_after: Optional[float], n_attempted: int) -> None`

Apply server feedback after a 429.

``retry_after`` is the per-*token* refill window the server
reports (None when signal-cli is older than v0.14.3 and didn't
surface it).

When present we calibrate ``refill_rate`` from it:
the server is authoritative.

#### def `state(self) -> dict`

Return current scheduler state for diagnostic logging (read-only).

Does not advance ``last_refill`` — safe to call from logging paths
without perturbing the bucket.


### 顶层函数

#### def `get_scheduler() -> SignalAttachmentScheduler`

Return the process-wide scheduler, creating it on first access.


## gateway.platforms.webhook

### 模块文档

Generic webhook platform adapter.

Runs an aiohttp HTTP server that receives webhook POSTs from external
services (GitHub, GitLab, JIRA, Stripe, etc.), validates HMAC signatures,
transforms payloads into agent prompts, and routes responses back to the
source or to another configured platform.

Configuration lives in config.yaml under platforms.webhook.extra.routes.
Each route defines:
  - events: which event types to accept (header-based filtering)
  - secret: HMAC secret for signature validation (REQUIRED)
  - prompt: template string formatted with the webhook payload
  - skills: optional list of skills to load for the agent
  - deliver: where to send the response (github_comment, telegram, etc.)
  - deliver_extra: additional delivery config (repo, pr_number, chat_id)
  - deliver_only: if true, skip the agent — the rendered prompt IS the
    message that gets delivered.  Use for external push notifications
    (Supabase, monitoring alerts, inter-agent pings) where zero LLM cost
    and sub-second delivery matter more than agent reasoning.

Security:
  - HMAC secret is required per route (validated at startup)
  - Rate limiting per route (fixed-window, configurable)
  - Idempotency cache prevents duplicate agent runs on webhook retries
  - Body size limits checked before reading payload
  - Generic HMAC supports a V2 signature (X-Webhook-Signature-V2) that
    binds a timestamp into the signed data for replay protection; the
    legacy body-only V1 (X-Webhook-Signature) is deprecated but still
    accepted with a warning, since it has no replay protection
  - Set secret to "INSECURE_NO_AUTH" to skip validation (testing only)

### class WebhookAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 22（公开 5）

Generic webhook receiver that triggers agent runs from HTTP POSTs.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

**异常**: `ValueError`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Deliver the agent's response to the configured destination.

chat_id is ``webhook:{route}:{delivery_id}``.  The delivery info
stored during webhook receipt is read with ``.get()`` (not popped)
so that interim status messages emitted before the final response
— fallback-model notifications, context-pressure warnings, etc. —
do not consume the entry and silently downgrade the final response
to the ``log`` deliver type.  TTL cleanup happens on POST.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### async def `on_processing_complete(self, event: MessageEvent, outcome: Any) -> None`

Close the per-delivery webhook session once its run finishes.

A webhook delivery is one-shot: the ``delivery_id`` is baked into the
session key, so the session will never receive a second turn.  Mirror
the cron completion path (``cron/scheduler.py`` →
``end_session(..., "cron_complete")``) by marking the session ended
when the run completes.  Without this, webhook sessions keep
``ended_at`` NULL forever; ``SessionDB.prune_sessions`` only reaps
rows with ``ended_at`` set, so unclosed webhook sessions accumulate
unbounded and drive state.db bloat (the ghost-session leak).

This hook is the one seam that runs at the TRUE end of the run:
``BasePlatformAdapter._process_message_background`` fires it after the
message handler returns, on the success, failure, and cancellation
paths alike — so error runs are reaped too.  (``handle_message`` is
fire-and-forget; wrapping IT closes before the run even starts.)
``end_session()`` is first-reason-wins and no-ops on an already-ended
row, so this never clobbers a ``compression``/``agent_close`` reason.


### 顶层函数

#### def `check_webhook_requirements() -> bool`

Check if webhook adapter dependencies are available.


## gateway.platforms.webhook_filters

### 模块文档

Route-local filters and script transforms for the webhook adapter.

### class WebhookRouteProcessor

> 继承: `object` ｜ 方法数: 5（公开 4）

Evaluate declarative filters and optional script transforms.

#### def `__init__(script_timeout_seconds: int = DEFAULT_SCRIPT_TIMEOUT_SECONDS) -> None`

#### def `resolve_filter_field(self, field: Any, payload: dict, event_type: str, headers: Any) -> Any`

Resolve a dotted filter field against payload/event/headers context.

#### def `filter_matches(self, spec: Any, payload: dict, event_type: str, headers: Any) -> bool`

Evaluate one declarative webhook filter spec.

#### def `route_filters_match(self, route_config: dict, payload: dict, event_type: str, headers: Any) -> bool`

#### def `run_route_script(self, script_value: Any, payload: dict) -> tuple[bool, Optional[dict]]`

Run a route script and return (should_continue, transformed_payload).


## gateway.platforms.weixin

### 模块文档

Weixin platform adapter.

Connects Hermes Agent to WeChat personal accounts via Tencent's iLink Bot API.

Design notes:
- Long-poll ``getupdates`` drives inbound delivery.
- Every outbound reply must echo the latest ``context_token`` for the peer.
- Media files move through an AES-128-ECB encrypted CDN protocol.
- QR login is exposed as a helper for the gateway setup wizard.

### class ContextTokenStore

> 继承: `object` ｜ 方法数: 7（公开 3）

Disk-backed ``context_token`` cache keyed by account + peer.

#### def `__init__(hermes_home: str)`

#### def `restore(self, account_id: str) -> None`

#### def `get(self, account_id: str, user_id: str) -> Optional[str]`

#### def `set(self, account_id: str, user_id: str, token: str) -> None`


### class TypingTicketCache

> 继承: `object` ｜ 方法数: 3（公开 2）

Short-lived typing ticket cache from ``getconfig``.

#### def `__init__(ttl_seconds: float = 600.0)`

#### def `get(self, user_id: str) -> Optional[str]`

#### def `set(self, user_id: str, ticket: str) -> None`


### class WeixinAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 43（公开 13）

Native Hermes adapter for Weixin personal accounts.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### property `enforces_own_access_policy(self) -> bool`

Weixin gates DM/group access at intake via dm_policy/group_policy.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_typing(self, chat_id: str, metadata: Optional[Dict[str, Any]] = None) -> None`

#### async def `stop_typing(self, chat_id: str) -> None`

#### async def `send_image(self, chat_id: str, image_url: str, caption: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### def `format_message(self, content: Optional[str]) -> str`


### 顶层函数

#### def `check_weixin_requirements() -> bool`

Return True when runtime dependencies for Weixin are available.

#### def `save_weixin_account(hermes_home: str, account_id: str, token: str, base_url: str, user_id: str = '') -> None`

Persist account credentials for later reuse.

#### def `load_weixin_account(hermes_home: str, account_id: str) -> Optional[Dict[str, Any]]`

Load persisted account credentials.

#### def `qr_login(hermes_home: str, bot_type: str = '3', timeout_seconds: int = 480) -> Optional[Dict[str, str]]`

Run the interactive iLink QR login flow.

Returns a credential dict on success, or ``None`` if login fails or times out.

**异常**: `RuntimeError`

#### def `send_weixin_direct(extra: Dict[str, Any], token: Optional[str], chat_id: str, message: str, media_files: Optional[List[Tuple[str, bool]]] = None) -> Dict[str, Any]`

One-shot send helper for ``send_message`` and cron delivery.

This bypasses the long-poll adapter lifecycle and uses the raw API directly.


## gateway.platforms.whatsapp_cloud

### 模块文档

WhatsApp Cloud API adapter — official Meta WhatsApp Business Platform.

This adapter is a *complement* to ``whatsapp.py`` (the Baileys bridge), not
a replacement. The two are independent:

- ``whatsapp.py``      — unofficial Baileys bridge, personal accounts, no
                         public URL needed, account-ban risk.
- ``whatsapp_cloud.py`` (this file) — official Meta Cloud API, Business
                         account required, public webhook URL required,
                         token-based auth.

Both share gating / mention / formatting behavior via ``WhatsAppBehaviorMixin``.

Phase scope (this file evolves across phases):
- Phase 2 — outbound text via Graph API + webhook server with verify-token
            handshake.
- Phase 3 — X-Hub-Signature-256 HMAC verification (raw body, constant-time)
            + wamid replay protection + dispatch via handle_message. Phase 3
            adapter is end-to-end usable for text DMs.
- Phase 4 — media upload + send (image/video/audio/document), inbound
            media download via the Graph media endpoint, voice-note opus
            conversion via ffmpeg with graceful MP3 fallback when ffmpeg
            isn't on PATH. Document text injection for readable types.
- Phase 5 — 24-hour conversation window + template fallback.

Required env vars to enable the adapter:
- WHATSAPP_CLOUD_PHONE_NUMBER_ID  (the Graph URL path component)
- WHATSAPP_CLOUD_ACCESS_TOKEN     (System User permanent token)

Optional / Phase-3+:
- WHATSAPP_CLOUD_APP_ID
- WHATSAPP_CLOUD_APP_SECRET       (HMAC key for X-Hub-Signature-256)
- WHATSAPP_CLOUD_WABA_ID          (analytics / future use)
- WHATSAPP_CLOUD_VERIFY_TOKEN     (hub.verify_token shared secret)
- WHATSAPP_CLOUD_WEBHOOK_HOST     (default 0.0.0.0)
- WHATSAPP_CLOUD_WEBHOOK_PORT     (default 8090)
- WHATSAPP_CLOUD_WEBHOOK_PATH     (default /whatsapp/webhook)
- WHATSAPP_CLOUD_API_VERSION      (default v20.0)

### class WhatsAppCloudAdapter

> 继承: `WhatsAppBehaviorMixin`、`BasePlatformAdapter` ｜ 方法数: 40（公开 13）

WhatsApp Business Cloud API adapter.

Outbound: HTTPS POST to ``graph.facebook.com/<api_version>/<phone_id>/messages``.
Inbound: aiohttp server accepting Meta's webhook payloads.

The mixin must come first in the bases list so its ``format_message``
overrides ``BasePlatformAdapter.format_message`` (the base provides a
generic implementation that does not convert markdown to WhatsApp
syntax). The Baileys adapter does the same.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a text message via Graph API.

``chat_id`` is the recipient's WhatsApp ID (``wa_id``) — typically
their phone number with country code, no plus sign.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Mark the latest inbound message as read AND show a typing
indicator in the user's chat UI.

Best-effort: any error (no inbound wamid yet, network failure,
stale token, message older than 30 days) is swallowed silently
so the agent's main reply path isn't blocked by UX polish.

#### async def `send_clarify(self, chat_id: str, question: str, choices: Optional[list], clarify_id: str, session_key: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Render a clarify prompt as native WhatsApp interactive buttons.

- 1–3 choices → ``interactive.type=button`` (inline pill buttons).
- 4+ choices → ``interactive.type=list`` (tap-to-open sheet with
  up to 10 rows). Telegram's "Other (type answer)" escape hatch
  is appended as the final row, picking it flips the entry into
  text-capture mode handled by the gateway's text intercept.
- 0 choices (open-ended) → plain text question; the next message
  in the session is captured by the gateway and resolves clarify.

The button ``id`` field carries ``cl:<clarify_id>:<idx>`` (or
``:other``); inbound webhook parsing dispatches on the prefix.

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[Dict[str, Any]] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Render a dangerous-command approval prompt with native buttons.

Two quick-reply buttons (Approve / Deny). Tapping resolves the
waiting agent via ``tools.approval.resolve_gateway_approval`` —
same mechanism as the text ``/approve`` flow. The agent thread
is blocked until the user taps or types a response.

#### async def `send_slash_confirm(self, chat_id: str, title: str, message: str, session_key: str, confirm_id: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Render a 3-button slash-command confirmation prompt.

Mirrors Telegram's send_slash_confirm: Approve Once / Always /
Cancel. The confirm_id is supplied by the caller (slash command
handler) — we just store the session_key mapping for the inbound
resolver to look up.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send an image by public URL. Prefers Meta's ``link`` mode.

``**kwargs`` absorbs platform-agnostic args the base class passes
(e.g. ``metadata``) that the Cloud API doesn't have a use for.
Mirrors send_image_file / send_video / send_voice / send_document.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a local image file via two-step upload + id.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a video. Local path → upload; HTTPS URL → link mode.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send an audio file as a WhatsApp voice message.

WhatsApp renders ``audio/ogg; codecs=opus`` as the green
voice-note bubble; other audio types (MP3, AAC, etc.) appear as
a generic audio attachment. Hermes TTS produces MP3, so we try
ffmpeg conversion to opus first and fall back to sending the
MP3 as-is when ffmpeg is unavailable.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a document attachment with optional filename + caption.


### 顶层函数

#### def `check_whatsapp_cloud_requirements() -> bool`

Return whether transport dependencies are available.

aiohttp is needed for the webhook server (inbound). httpx is needed
for Graph API calls (outbound). Both ship with hermes-agent's default
dependency set, so this should always be True in normal installs.


## gateway.platforms.whatsapp_common

### 模块文档

Transport-agnostic WhatsApp behavior shared by the Baileys bridge adapter
and the official WhatsApp Cloud API adapter.

The mixin provides:
- Allow-list / DM / group gating
- Mention detection (explicit @-mentions + configurable regex patterns)
- Quoted-reply-to-bot detection
- Broadcast / Channel / Newsletter filtering
- WhatsApp-flavored markdown conversion
- Outgoing chunk length budgeting

It is the *behavior layer*. Transport-specific concerns (subprocess management,
HTTP webhooks, Graph API calls, media upload protocols) live in each adapter.

Mixin contract — the adapter must set these on ``self`` before any of the
mixin's methods are called (typically in ``__init__``):

    self.config        # gateway.config.PlatformConfig
    self.name          # str — adapter name (used in log lines)
    self._dm_policy             # str: "open" | "allowlist" | "disabled"
    self._allow_from            # set[str]
    self._group_policy          # str: "open" | "allowlist" | "disabled"
    self._group_allow_from      # set[str]
    self._mention_patterns      # list[re.Pattern]
    self._reply_prefix          # Optional[str]

Class attributes ``MAX_MESSAGE_LENGTH`` and ``DEFAULT_REPLY_PREFIX`` are
defined on the mixin and may be overridden per-adapter if needed.

### class WhatsAppBehaviorMixin

> 继承: `object` ｜ 方法数: 22（公开 2）

Shared behavior for all WhatsApp adapters (Baileys + Cloud API).

See module docstring for the attribute contract the host adapter must
satisfy. This mixin owns no state of its own — every value it touches
is either a class attribute or set by the adapter's ``__init__``.

#### property `enforces_own_access_policy(self) -> bool`

WhatsApp gates DM/group access at intake via dm_policy/group_policy.

#### def `format_message(self, content: str) -> str`

Convert standard markdown to WhatsApp-compatible formatting.

WhatsApp supports: *bold*, _italic_, ~strikethrough~, ```code```,
and monospaced `inline`. Standard markdown uses different syntax
for bold/italic/strikethrough, so we convert here.

Code blocks (``` fenced) and inline code (`) are protected from
conversion via placeholder substitution.


### 顶层函数

#### def `resolve_whatsapp_bridge_dir() -> Path`

Resolve the WhatsApp bridge directory, mirroring to HERMES_HOME if needed.

When the install tree is read-only (e.g., Docker /opt/hermes), this function
mirrors the bridge source to a writable HERMES_HOME location and returns that
path. This ensures npm install works in Docker environments.

Returns the resolved bridge directory path.


## gateway.platforms.yuanbao

### 模块文档

Yuanbao platform adapter.

Connects to the Yuanbao WebSocket gateway, handles authentication (AUTH_BIND),
heartbeat, reconnection, message receive (T05) and send (T06).

Configuration in config.yaml (or via env vars):
    platforms:
      yuanbao:
        extra:
          app_id: "..."              # or YUANBAO_APP_ID
          app_secret: "..."          # or YUANBAO_APP_SECRET
          bot_id: "..."              # or YUANBAO_BOT_ID  (optional, returned by sign-token)
          ws_url: "wss://..."        # or YUANBAO_WS_URL
          api_domain: "https://..."  # or YUANBAO_API_DOMAIN

### class MarkdownProcessor

> 继承: `object` ｜ 方法数: 12（公开 12）

Encapsulates all Markdown-related utilities for the Yuanbao platform.

Provides static methods for:
- Fence detection and streaming merge
- Table row detection and sanitization
- Paragraph-boundary splitting
- Atomic-block extraction and chunk splitting
- Outer markdown fence stripping
- Markdown hint prompt generation

#### staticmethod `has_unclosed_fence(text: str) -> bool`

Detect whether the text has unclosed code block fences.

Scan line by line, toggling in/out state when encountering a line starting with ```.
An odd number of toggles indicates an unclosed fence.

Args:
    text: Markdown text to check

Returns:
    Returns True if the text ends with an unclosed fence, otherwise False

#### staticmethod `ends_with_table_row(text: str) -> bool`

Detect whether the text ends with a table row (last non-empty line starts and ends with |).

Args:
    text: Text to check

Returns:
    Returns True if the last non-empty line is a table row

#### staticmethod `split_at_paragraph_boundary(text: str, max_chars: int, len_fn: Optional[Callable[[str], int]] = None) -> tuple[str, str]`

Find the nearest paragraph boundary split point within max_chars, return (head, tail).

Split priority:
1. Blank line (paragraph boundary)
2. Newline after period/question mark/exclamation mark (Chinese and English)
3. Last newline
4. Force split at max_chars

Args:
    text: Text to split
    max_chars: Maximum character count limit
    len_fn: Optional custom length function (e.g. UTF-16 length); defaults to built-in len

Returns:
    (head, tail) tuple, head is the front part, tail is the back part, satisfying head + tail == text

#### staticmethod `is_fence_atom(text: str) -> bool`

Determine whether an atomic block is a code block (starts with ```).

#### staticmethod `is_table_atom(text: str) -> bool`

Determine whether an atomic block is a table (first line starts with |).

#### staticmethod `split_into_atoms(text: str) -> list[str]`

Split text into a list of "atomic blocks", each being an indivisible logical unit:

- Code block (fence): from opening ``` to closing ``` (including fence lines)
- Table: consecutive |...| lines forming a whole segment
- Normal paragraph: plain text segments separated by blank lines

Blank lines serve as separators and are not included in any atomic block.

Args:
    text: Markdown text to split

Returns:
    List of atomic block strings (all non-empty)

#### classmethod `chunk_markdown_text(cls, text: str, max_chars: int = 4000, len_fn: Optional[Callable[[str], int]] = None) -> list[str]`

Split Markdown text into multiple chunks by max_chars.

Guarantees:
- Each chunk <= max_chars characters (unless a single code block/table itself exceeds the limit)
- Code blocks (```...```) are not split in the middle
- Table rows are not split in the middle (tables output as atomic blocks)
- Split at paragraph boundaries (blank lines, after periods, etc.)
- Small trailing/leading chunks are merged with neighbours when possible

Args:
    text: Markdown text to split
    max_chars: Max characters per chunk, default 4000
    len_fn: Optional custom length function (e.g. UTF-16 length); defaults to built-in len

Returns:
    List of text chunks after splitting (non-empty)

#### classmethod `infer_block_separator(cls, prev_chunk: str, next_chunk: str) -> str`

Infer the separator to use between two split chunks.

Rules (aligned with TS markdown-stream.ts):
- Previous chunk ends with code fence or next chunk starts with fence → single newline '\n'
- Previous chunk ends with table row and next chunk starts with table row → single newline '\n' (continued table)
- Otherwise → double newline '\n\n' (paragraph separator)

Args:
    prev_chunk: Previous chunk
    next_chunk: Next chunk

Returns:
    '\n' or '\n\n'

#### classmethod `merge_block_streaming_fences(cls, chunks: list[str]) -> list[str]`

Stream-aware fence-conscious chunk merging.

When streaming output produces multiple chunks truncated in the middle of a fence,
attempt to merge adjacent chunks to complete the fence.

Rules:
- If chunk i has an unclosed fence and chunk i+1 starts with ```,
    merge i+1 into i (until the fence is closed or no more chunks).
- Use infer_block_separator to infer the separator during merging.

Args:
    chunks: Original chunk list

Returns:
    Merged chunk list (length <= original length)

#### staticmethod `strip_outer_markdown_fence(text: str) -> str`

Strip outer Markdown fence.

When AI reply is entirely wrapped in ```markdown\n...\n```, remove the outer fence,
keeping the content. Only strip when the first line is ```markdown (case-insensitive) and the last line is ```.

Args:
    text: Text to process

Returns:
    Text with outer fence stripped (returns original if no match)

#### staticmethod `sanitize_markdown_table(text: str) -> str`

Table output sanitization.

Handle common formatting issues in AI-generated Markdown tables:
1. Remove extra whitespace before/after table rows
2. Ensure separator rows (|---|---|) are correctly formatted
3. Remove empty table rows

Args:
    text: Markdown text containing tables

Returns:
    Sanitized text

#### staticmethod `markdown_hint_system_prompt() -> str`

Markdown rendering hint (appended to system prompt).

Tell AI that Yuanbao platform supports Markdown rendering, including:
- Code blocks (```lang)
- Tables (| col | col |)
- Bold/italic


### class SignManager

> 继承: `object` ｜ 方法数: 9（公开 9）

Encapsulates all sign-token related logic for the Yuanbao platform.

Manages token acquisition, caching, signature computation, and
automatic retry.  All state (cache, locks) is kept as class-level
attributes so that a single shared client serves the whole process.

#### classmethod `get_refresh_lock(cls, app_key: str) -> asyncio.Lock`

Return (creating if needed) the per-app_key refresh lock.

Must only be called from within a running event loop (async context).

#### staticmethod `compute_signature(nonce: str, timestamp: str, app_key: str, app_secret: str) -> str`

Compute HMAC-SHA256 signature (aligned with TypeScript original).

plain     = nonce + timestamp + app_key + app_secret
signature = HMAC-SHA256(key=app_secret, msg=plain).hexdigest()

#### staticmethod `build_timestamp() -> str`

Build Beijing-time ISO-8601 timestamp (no milliseconds).

Format: 2006-01-02T15:04:05+08:00

#### classmethod `is_cache_valid(cls, entry: dict[str, Any]) -> bool`

Determine whether the cache entry is valid (not expired with margin).

#### classmethod `clear_locks(cls) -> None`

Clear all per-app_key refresh locks (called on disconnect).

#### classmethod `purge_expired(cls) -> int`

Remove all expired entries from the token cache.

Returns the number of entries purged.  Called lazily from
``get_token()`` so that stale app_key entries don't accumulate
indefinitely in long-running processes.

#### async def `fetch(cls, app_key: str, app_secret: str, api_domain: str, route_env: str = '') -> dict[str, Any]`

Send sign-ticket HTTP request with auto-retry (up to MAX_RETRIES times).

**异常**: `RuntimeError`, `ValueError`

#### async def `get_token(cls, app_key: str, app_secret: str, api_domain: str, route_env: str = '') -> dict[str, Any]`

Get WS auth token (with cache).

Return directly on cache hit without re-requesting; treat as expiring
60 seconds before actual expiry, triggering refresh.

#### async def `force_refresh(cls, app_key: str, app_secret: str, api_domain: str, route_env: str = '') -> dict[str, Any]`

Force refresh token (clear cache and re-sign).


### class InboundContext

> 继承: `object` ｜ 方法数: 0（公开 0）

Mutable context flowing through the inbound middleware pipeline.

Each middleware reads/writes fields on this context.  The pipeline
engine passes it to every middleware in registration order.


### class InboundMiddleware

> 继承: `ABC` ｜ 方法数: 3（公开 1）

Abstract base class for all inbound pipeline middlewares.

Subclasses must:
  - Set ``name`` as a class-level attribute (used for pipeline registration
    and dynamic insertion/removal).
  - Implement ``async handle(ctx, next_fn)`` containing the middleware logic.

Convention:
  - Call ``await next_fn()`` to pass control to the next middleware.
  - Return without calling ``next_fn`` to **stop** the pipeline.

#### async def `handle(self, ctx: InboundContext, next_fn: Callable) -> None`

Process *ctx* and optionally call *next_fn* to continue the pipeline.


### class InboundPipeline

> 继承: `object` ｜ 方法数: 8（公开 6）

Onion-model middleware pipeline engine for inbound message processing.

Inspired by OpenClaw's MessagePipeline (extensions/yuanbao/src/business/
pipeline/engine.ts).  Supports named middlewares, conditional guards
(``when``), and ``use_before`` / ``use_after`` / ``remove`` for dynamic
composition.

Accepts both ``InboundMiddleware`` instances (OOP style) and plain
``async def(ctx, next_fn)`` callables (functional style) for flexibility.

#### def `__init__() -> None`

#### def `use(self, name_or_mw, handler = None, when = None) -> InboundPipeline`

Append a middleware to the end of the pipeline.

Accepts either:
  - ``pipeline.use(SomeMiddleware())``  — OOP style
  - ``pipeline.use("name", some_fn)``   — functional style

#### def `use_before(self, target: str, name_or_mw, handler = None, when = None) -> InboundPipeline`

Insert a middleware before *target* (by name).  Appends if not found.

#### def `use_after(self, target: str, name_or_mw, handler = None, when = None) -> InboundPipeline`

Insert a middleware after *target* (by name).  Appends if not found.

#### def `remove(self, name: str) -> InboundPipeline`

Remove a middleware by name.

#### property `middleware_names(self) -> list`

Return ordered list of registered middleware names (for testing).

#### async def `execute(self, ctx: InboundContext) -> None`

Run all middlewares in order.  Each middleware receives ``(ctx, next_fn)``.


### class DecodeMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 4（公开 3）

Decode raw inbound frames from JSON or Protobuf into ctx.push.

Encapsulates JSON push parsing (aligned with TS decodeFromContent)
and Protobuf decoding via ``decode_inbound_push``.

#### staticmethod `convert_json_msg_body(raw_body: list) -> list`

Normalize raw JSON msg_body array to [{"msg_type": str, "msg_content": dict}].

Compatible with both PascalCase (MsgType/MsgContent) and
snake_case (msg_type/msg_content) naming.

#### staticmethod `parse_json_push(raw_json: dict) -> dict | None`

Convert JSON-format push to a dict with the same structure as
``decode_inbound_push``.

Supports standard callback format (callback_command + from_account +
msg_body) and legacy format fields (GroupId, MsgSeq, MsgKey, MsgBody,
etc.).

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class ExtractFieldsMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 1（公开 1）

Extract common fields from ctx.push into ctx attributes.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class DedupMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 1（公开 1）

Inbound message deduplication.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class RecallGuardMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 7（公开 1）

Intercept Group.CallbackAfterRecallMsg / C2C.CallbackAfterMsgWithDraw.

Branch A: message in transcript (observed, not yet consumed) → redact content
Branch B: message not in transcript → append system note
Branch C: message currently being processed → silent interrupt + delayed redact

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class SkipSelfMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 2（公开 1）

Filter out bot's own messages.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class ChatRoutingMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 1（公开 1）

Determine chat_id, chat_type, chat_name from push fields.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class AccessPolicy

> 继承: `object` ｜ 方法数: 7（公开 5）

Platform-level DM / Group access control policy.

Encapsulates the allow/deny logic so that both inbound middleware
and outbound ``send_dm`` can share the same rules without reaching
into adapter internals.

#### def `__init__(dm_policy: str, dm_allow_from: list[str], group_policy: str, group_allow_from: list[str]) -> None`

#### def `is_dm_allowed(self, sender_id: str) -> bool`

Strict DM authorization — pairing does not imply access.

#### def `is_dm_intake_allowed(self, sender_id: str) -> bool`

Whether a DM may reach gateway intake (pairing handshake path).

#### def `is_group_allowed(self, group_code: str) -> bool`

Platform-level group chat inbound filter (open / allowlist / disabled).

#### property `dm_policy(self) -> str`

#### property `group_policy(self) -> str`


### class AccessGuardMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 1（公开 1）

Platform-level DM/Group access control filter.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class AutoSetHomeMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 1（公开 1）

Auto-designate the first inbound conversation as Yuanbao home channel.

Triggers when no home channel is configured, or when an existing group-chat
home is superseded by the first DM (direct > group upgrade).
Silent: writes config.yaml and env, no user-facing message.

Runs after :class:`BuildSourceMiddleware` and :class:`GroupAtGuardMiddleware`
so unaddressed group traffic is dropped before home-channel persistence.
Only senders that pass strict authorization (allowlist / explicit open
opt-in / pairing-store approval) may claim ``YUANBAO_HOME_CHANNEL``.
Intake-only pairing forwards must not claim ``YUANBAO_HOME_CHANNEL``.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class ExtractContentMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 9（公开 1）

Extract raw text and media refs from msg_body.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class PlaceholderFilterMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 2（公开 2）

Skip pure placeholder messages (e.g. '[image]' with no media).

#### classmethod `is_skippable_placeholder(cls, text: str, media_count: int = 0) -> bool`

Detect whether the message is a pure placeholder (should be skipped).

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class OwnerCommandMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 3（公开 1）

Detect bot-owner slash commands in group chat.

Identifies in-group allowlisted slash commands and determines sender identity.
Owner commands skip @Bot detection; non-owner attempts are rejected.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class BuildSourceMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 1（公开 1）

Build SessionSource from context fields.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class GroupAtGuardMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 5（公开 1）

In group chat, observe non-@bot messages; only reply on @Bot.

Owner commands skip @Bot detection (owner doesn't need to @Bot).

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class GroupAttributionMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 1（公开 1）

Tag group @bot messages with [nickname|user_id] attribution and channel_prompt.

For group messages that pass the @bot guard (i.e. the bot is mentioned),
this middleware:
  - Builds a per-turn channel_prompt so the model knows its identity and
    the attribution scheme.
  - Rewrites ctx.raw_text to ``[nickname|user_id]\n<content>`` to match
    the observed-history format.
  - Suppresses the runner's default ``[user_name]`` shared-thread prefix
    by clearing ``source.user_name``.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class YuanbaoMessageType

> 继承: `Enum` ｜ 方法数: 0（公开 0）

Yuanbao-local message subtypes; coerced back to :class:`MessageType`
before leaving the adapter (see :class:`DispatchMiddleware`).


### class ClassifyMessageTypeMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 2（公开 1）

Determine MessageType from text content and msg_body elements.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class QuoteContextMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 3（公开 1）

Extract quote/reply context from cloud_custom_data.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class ForwardedRecordsParseMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 5（公开 2）

Deep-parse WeChat forwarded chat records (elem_type 1009) for dispatch.

Activates when a full ``ForwardMsgData`` dict is available on the current
turn, carried by the current message (``ctx.forwarded_records``).
Resolves media to ``[kind|ybres:RID]``
placeholders, appends downloadable refs to ``ctx.media_refs`` (for
:class:`MediaResolveMiddleware`), and rewrites ``ctx.raw_text``.

Group @bot turns *without* a forward on the current message rely on the
eagerly-rendered summaries that :class:`GroupAtGuardMiddleware` writes to
the transcript at observe time — there is no run-time summary fallback
here.

On any failure the middleware leaves ``ctx.raw_text`` untouched
(graceful degradation, design §2.8).

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`

#### classmethod `build_forward_text(cls, forward_data: dict, ctx: InboundContext, is_dispatch: bool) -> str`

Render ``ForwardMsgData`` into forward text.

Body lines are ``发送人：正文`` with full ``[kind|ybres:RID]`` media
markers preserved. When ``is_dispatch`` is true, refs are appended to
``ctx.media_refs`` for downstream resolution and a ``用户附言：
{ctx.raw_text}`` footer is added; observed callers skip both since
no later middleware runs.


### class MediaResolveMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 13（公开 1）

Resolve inbound media references to downloadable URLs.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class PatchAnchorsMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 2（公开 1）

Replace ``[kind|ybres:RID]`` anchors in ``ctx.raw_text`` with local paths.

Runs after :class:`MediaResolveMiddleware` so that ``ctx.media_urls`` /
``ctx.media_types`` are already populated with downloaded resources
(own media + quote media or group-observed media).  The transcript
written downstream then records usable local paths for the model
instead of opaque ``ybres:`` references.

Only resolved media (paths starting with ``/``) are substituted; any
anchor without a corresponding local resource is left untouched.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class DispatchMiddleware

> 继承: `InboundMiddleware` ｜ 方法数: 2（公开 1）

Build MessageEvent and dispatch to AI handler.

#### async def `handle(self, ctx: InboundContext, next_fn) -> None`


### class InboundPipelineBuilder

> 继承: `object` ｜ 方法数: 1（公开 1）

Factory for building InboundPipeline instances.

Separates pipeline assembly (business knowledge) from the pipeline engine
(InboundPipeline) so the engine stays generic and reusable.

#### classmethod `build(cls) -> InboundPipeline`

Build the default inbound message processing pipeline.


### class ConnectionManager

> 继承: `object` ｜ 方法数: 20（公开 8）

Manages the WebSocket connection lifecycle for YuanbaoAdapter.

Responsibilities:
  - Opening and closing the WebSocket
  - AUTH_BIND handshake
  - Heartbeat (ping/pong) loop
  - Receive loop (frame dispatch)
  - Reconnect with exponential backoff

#### def `__init__(adapter: YuanbaoAdapter) -> None`

#### property `ws(self)`

#### property `connect_id(self) -> Optional[str]`

#### property `reconnect_attempts(self) -> int`

#### property `is_connected(self) -> bool`

#### async def `open(self) -> bool`

Open WebSocket connection: sign-token → WS connect → AUTH_BIND → start loops.

Returns True on success, False on failure.

#### async def `close(self) -> None`

Cancel background tasks, fail pending futures, and close the WebSocket.

#### async def `send_biz_request(self, encoded_conn_msg: bytes, req_id: str, timeout: float = DEFAULT_SEND_TIMEOUT) -> dict`

Send a business-layer request and wait for the response.

1. Register a Future in pending_acks[req_id]
2. Send encoded_conn_msg (bytes) to WS
3. asyncio.wait_for(future, timeout)
4. Clean up pending_acks on timeout/exception

**异常**: `RuntimeError`

#### def `schedule_reconnect(self) -> None`

Schedule a reconnect only if running and not already reconnecting.


### class MediaSendHandler

> 继承: `ABC` ｜ 方法数: 4（公开 4）

Abstract base class for media send strategies.

Subclasses implement:
  - acquire_file(): how to obtain file bytes (download URL / read local)
  - build_msg_body(): how to build TIMxxxElem from upload result

The shared flow (check ws → cancel notifier → validate → COS upload
→ lock → dispatch) is handled by the base handle() template method.

#### async def `acquire_file(self, adapter: YuanbaoAdapter, **kwargs: Any) -> Tuple[bytes, str, str]`

Return (file_bytes, filename, content_type).

Raises:
    ValueError: when file cannot be acquired (not found, empty, etc.)

**异常**: `ValueError`

#### def `build_msg_body(self, upload_result: dict, **kwargs: Any) -> list`

Build platform-specific MsgBody list from COS upload result.

#### def `needs_cos_upload(self) -> bool`

Override to return False for non-COS media (e.g. sticker).

#### async def `handle(self, adapter: YuanbaoAdapter, chat_id: str, reply_to: Optional[str] = None, caption: Optional[str] = None, **kwargs: Any) -> SendResult`

Template method: shared media send flow.


### class ImageUrlHandler

> 继承: `MediaSendHandler` ｜ 方法数: 2（公开 2）

Strategy: send image from a URL (download → COS → TIMImageElem).

#### async def `acquire_file(self, adapter, **kwargs)`

#### def `build_msg_body(self, upload_result, **kwargs)`


### class ImageFileHandler

> 继承: `MediaSendHandler` ｜ 方法数: 2（公开 2）

Strategy: send image from a local file path (read → COS → TIMImageElem).

#### async def `acquire_file(self, adapter, **kwargs)`

**异常**: `ValueError`

#### def `build_msg_body(self, upload_result, **kwargs)`


### class FileUrlHandler

> 继承: `MediaSendHandler` ｜ 方法数: 2（公开 2）

Strategy: send file from a URL (download → COS → TIMFileElem).

#### async def `acquire_file(self, adapter, **kwargs)`

#### def `build_msg_body(self, upload_result, **kwargs)`


### class DocumentHandler

> 继承: `MediaSendHandler` ｜ 方法数: 2（公开 2）

Strategy: send local file/document (read → COS → TIMFileElem).

#### async def `acquire_file(self, adapter, **kwargs)`

**异常**: `ValueError`

#### def `build_msg_body(self, upload_result, **kwargs)`


### class StickerHandler

> 继承: `MediaSendHandler` ｜ 方法数: 3（公开 3）

Strategy: send sticker/emoji (TIMFaceElem, no COS upload needed).

#### def `needs_cos_upload(self) -> bool`

#### async def `acquire_file(self, adapter, **kwargs)`

#### def `build_msg_body(self, upload_result, **kwargs)`

**异常**: `ValueError`


### class GroupQueryService

> 继承: `object` ｜ 方法数: 5（公开 4）

Encapsulates all group query operations (both low-level WS calls and
higher-level AI-tool-facing wrappers).

Responsibilities:
  - Low-level WS encode/decode for group info and member list queries
  - Chat-id parsing, error wrapping and result filtering for AI tools
  - Member cache population on the adapter

#### def `__init__(adapter: YuanbaoAdapter) -> None`

#### async def `query_group_info_raw(self, group_code: str) -> Optional[dict]`

Query group info via WS (group name, owner, member count, etc.).

Returns:
    Decoded dict or None on failure.

#### async def `get_group_member_list_raw(self, group_code: str, offset: int = 0, limit: int = 200) -> Optional[dict]`

Query group member list via WS.

Returns:
    Decoded dict or None on failure.  Also populates adapter._member_cache.

#### async def `query_group_info(self, chat_id: str) -> dict`

AI tool: Query current group info.

No parameters needed (group_code extracted from session context).
Returns group name, owner, member count, etc.

#### async def `query_session_members(self, chat_id: str, action: str = 'list_all', name: Optional[str] = None) -> dict`

AI tool: Query group member list.

Args:
    chat_id: Chat ID (extracted from session context)
    action: 'find' (search by name) | 'list_bots' (list bots) | 'list_all' (list all)
    name: Search keyword when action='find'

Returns:
    {"members": [...], "total": int, "mentionHint": str}


### class HeartbeatManager

> 继承: `object` ｜ 方法数: 6（公开 4）

Manages reply heartbeat (RUNNING / FINISH) lifecycle.

Responsibilities:
  - Periodic RUNNING heartbeat sender (every 2s)
  - Auto-FINISH after 30s inactivity
  - Explicit stop with optional FINISH signal

#### def `__init__(adapter: YuanbaoAdapter) -> None`

#### async def `send_heartbeat_once(self, chat_id: str, heartbeat_val: int) -> None`

Send a single heartbeat (RUNNING or FINISH), best effort.

#### async def `start(self, chat_id: str) -> None`

Start or renew the Reply Heartbeat periodic sender (RUNNING, every 2s).

#### async def `stop(self, chat_id: str, send_finish: bool = True) -> None`

Stop Reply Heartbeat and optionally send FINISH.

#### async def `close(self) -> None`

Cancel all reply heartbeat tasks.


### class SlowResponseNotifier

> 继承: `object` ｜ 方法数: 5（公开 3）

Manages delayed 'please wait' notifications for slow agent responses.

Starts a timer per chat_id; if the agent hasn't replied within
SLOW_RESPONSE_TIMEOUT_S seconds, sends a courtesy message.

#### def `__init__(adapter: YuanbaoAdapter, sender: MessageSender) -> None`

#### async def `start(self, chat_id: str) -> None`

Start a delayed task that notifies the user when the agent is slow.

#### def `cancel(self, chat_id: str) -> None`

Cancel the pending slow-response notifier for *chat_id*, if any.

#### async def `close(self) -> None`

Cancel all slow-response tasks.


### class MessageSender

> 继承: `object` ｜ 方法数: 18（公开 15）

Core message sending dispatcher for YuanbaoAdapter.

Responsibilities:
  - Per-chat-id lock management (serial send ordering)
  - Text chunk sending with retry
  - C2C / Group message encoding and dispatch
  - Media send helpers (image, file, sticker, document)
  - Direct send helper (text + media, used by send_message tool)

#### def `__init__(adapter: YuanbaoAdapter) -> None`

#### def `register_handler(self, name: str, handler: MediaSendHandler) -> None`

Register (or replace) a named media send handler.

#### def `get_chat_lock(self, chat_id: str) -> asyncio.Lock`

Return (or create) a per-chat-id lock with safe LRU eviction.

#### async def `send_text(self, chat_id: str, content: str, reply_to: Optional[str] = None, group_code: str = '') -> SendResult`

Send text message with auto-chunking and per-chat-id ordering guarantee.

#### async def `send_media(self, chat_id: str, handler_name: str, reply_to: Optional[str] = None, caption: Optional[str] = None, **kwargs: Any) -> SendResult`

Dispatch media send to the named handler strategy.

#### async def `send_direct(self, chat_id: str, message: str, media_files: Optional[List[Tuple[str, bool]]] = None) -> Dict[str, Any]`

Send text + media via Yuanbao (used by the ``send_message`` tool).

Unlike Weixin which creates a fresh adapter per call, Yuanbao reuses
the running gateway adapter (persistent WebSocket).  Logic mirrors
send_weixin_direct: send text first, then iterate media_files by
extension.

#### async def `dispatch_msg_body(self, chat_id: str, msg_body: list, reply_to: Optional[str] = None, group_code: str = '') -> SendResult`

Lock + dispatch an arbitrary MsgBody to C2C or group.

#### async def `send_text_chunk(self, chat_id: str, text: str, reply_to: Optional[str] = None, retry: int = 3, group_code: str = '') -> SendResult`

Send a single text chunk with retry (exponential backoff: 1s, 2s, 4s).

#### async def `send_c2c_message(self, to_account: str, text: str, group_code: str = '') -> dict`

Send C2C text message, return {success: bool, msg_key: str}.

#### async def `send_group_message(self, group_code: str, text: str, reply_to: Optional[str] = None) -> dict`

Send group text message, auto-converting @nickname to TIMCustomElem.

#### async def `send_c2c_msg_body(self, to_account: str, msg_body: list, group_code: str = '') -> dict`

Send C2C message with arbitrary MsgBody.

#### async def `send_group_msg_body(self, group_code: str, msg_body: list, reply_to: Optional[str] = None) -> dict`

Send group message with arbitrary MsgBody.

#### staticmethod `validate_media(file_bytes: Optional[bytes], filename: str, max_size_mb: int = 20) -> Optional[str]`

Media pre-validation: check file validity before sending/uploading.

Returns:
    Error description (str) if validation fails, otherwise None.

#### staticmethod `truncate_message(content: str, max_length: int = 4000, len_fn: Optional[Callable[[str], int]] = None) -> List[str]`

Split a long message into chunks with table-awareness.

Delegates core splitting to ``MarkdownProcessor.chunk_markdown_text``
and strips page indicators like ``(1/3)`` from the output.

Falls back to ``BasePlatformAdapter.truncate_message`` for non-table
content and for overall text that fits in a single chunk.

#### staticmethod `strip_cron_wrapper(content: str) -> str`

Strip scheduler cron header/footer wrapper for cleaner Yuanbao output.

#### async def `close(self) -> None`

Release chat locks (no-op for now; placeholder for future cleanup).


### class OutboundManager

> 继承: `object` ｜ 方法数: 14（公开 10）

Outbound coordinator that orchestrates sending, heartbeat and slow-response.

Composes:
  - MessageSender   — core text/media sending
  - HeartbeatManager — reply heartbeat (RUNNING / FINISH) lifecycle
  - SlowResponseNotifier — delayed 'please wait' notifications

YuanbaoAdapter holds a single ``_outbound: OutboundManager`` and delegates
all outbound operations through it.

#### def `__init__(adapter: YuanbaoAdapter) -> None`

#### async def `send_text(self, chat_id: str, content: str, reply_to: Optional[str] = None, group_code: str = '') -> SendResult`

Send text message with auto-chunking.

#### async def `send_media(self, chat_id: str, handler_name: str, **kwargs: Any) -> SendResult`

Dispatch media send to the named handler strategy.

#### async def `send_direct(self, chat_id: str, message: str, media_files: Optional[List[Tuple[str, bool]]] = None) -> Dict[str, Any]`

Send text + media (used by send_message tool).

#### async def `start_typing(self, chat_id: str) -> None`

Start reply heartbeat (RUNNING).

#### async def `stop_typing(self, chat_id: str, send_finish: bool = False) -> None`

Stop reply heartbeat.

#### async def `start_slow_notifier(self, chat_id: str) -> None`

Start slow-response notifier.

#### def `cancel_slow_notifier(self, chat_id: str) -> None`

Cancel slow-response notifier.

#### def `get_chat_lock(self, chat_id: str) -> asyncio.Lock`

Proxy to MessageSender.get_chat_lock for backward compatibility.

#### staticmethod `validate_media(file_bytes: Optional[bytes], filename: str, max_size_mb: int = 20) -> Optional[str]`

Proxy to MessageSender.validate_media.

#### async def `close(self) -> None`

Shut down all sub-managers.


### class YuanbaoAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 23（公开 18）

Yuanbao AI Bot adapter backed by a persistent WebSocket connection.

#### classmethod `get_active(cls) -> Optional['YuanbaoAdapter']`

Return the currently connected YuanbaoAdapter, or None.

#### classmethod `set_active(cls, adapter: Optional['YuanbaoAdapter']) -> None`

Register (or clear) the active adapter instance.

#### def `__init__(config: PlatformConfig, **kwargs: Any) -> None`

#### property `enforces_own_access_policy(self) -> bool`

Yuanbao gates DM/group access at intake via dm_policy/group_policy.

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to Yuanbao WS gateway and authenticate.

Delegates to ConnectionManager.open().

#### async def `disconnect(self) -> None`

Cancel background tasks and close the WebSocket connection.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, group_code: str = '') -> SendResult`

Send text message with auto-chunking. Delegates to OutboundManager.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return basic chat metadata derived from the chat_id prefix.

chat_id conventions:
  "group:<group_code>"  → group chat
  "direct:<account>"   → C2C / direct message (default)

TODO (T06): fetch real chat name/member-count from Yuanbao API.

#### async def `send_typing(self, chat_id: str, metadata: Optional[dict] = None) -> None`

Send "typing" status heartbeat (RUNNING). Delegates to OutboundManager.

#### async def `stop_typing(self, chat_id: str) -> None`

Stop the RUNNING heartbeat loop without sending FINISH immediately.

FINISH is sent by send() after actual message delivery to ensure correct ordering:
RUNNING... -> message arrives -> FINISH.

#### async def `query_group_info(self, group_code: str) -> Optional[dict]`

Query group info (delegates to GroupQueryService).

#### async def `get_group_member_list(self, group_code: str, offset: int = 0, limit: int = 200) -> Optional[dict]`

Query group member list (delegates to GroupQueryService).

#### async def `send_dm(self, user_id: str, text: str, group_code: str = '') -> SendResult`

Actively send C2C private chat message.

Args:
    user_id: Target user ID
    text: Message text (limit 10000 characters)
    group_code: Source group code (for group-originated DM context)

Returns:
    SendResult

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[dict] = None, **kwargs: Any) -> SendResult`

Send image message (URL). Delegates to OutboundManager via ImageUrlHandler.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[dict] = None, **kwargs: Any) -> SendResult`

Send local image file. Delegates to OutboundManager via ImageFileHandler.

#### async def `send_file(self, chat_id: str, file_url: str, filename: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[dict] = None, **kwargs: Any) -> SendResult`

Send file message (URL). Delegates to OutboundManager via FileUrlHandler.

#### async def `send_sticker(self, chat_id: str, sticker_name: Optional[str] = None, face_index: Optional[int] = None, reply_to: Optional[str] = None, **kwargs: Any) -> SendResult`

Send sticker/emoji. Delegates to OutboundManager via StickerHandler.

#### async def `send_document(self, chat_id: str, file_path: str, filename: Optional[str] = None, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[dict] = None, **kwargs: Any) -> SendResult`

Send local file (document). Delegates to OutboundManager via DocumentHandler.

#### def `get_status(self) -> dict`

Return a snapshot of the current connection status.


### 顶层函数

#### def `get_active_adapter() -> Optional['YuanbaoAdapter']`

Delegate to ``YuanbaoAdapter.get_active()``.

#### def `send_yuanbao_direct(adapter: YuanbaoAdapter, chat_id: str, message: str, media_files: Optional[List[Tuple[str, bool]]] = None) -> Dict[str, Any]`

Delegate to ``OutboundManager.send_direct``.


## gateway.platforms.yuanbao_media

### 模块文档

yuanbao_media.py — 元宝平台媒体处理模块

提供 COS 上传、文件下载、TIM 媒体消息构建等功能。
移植自 TypeScript 版 media.ts（yuanbao-openclaw-plugin），
使用 httpx 替代 cos-nodejs-sdk-v5，避免引入额外 SDK 依赖。

COS 上传流程：
  1. 调用 genUploadInfo 获取临时凭证（tmpSecretId/tmpSecretKey/sessionToken）
  2. 用临时凭证通过 HMAC-SHA1 签名构建 Authorization 头
  3. HTTP PUT 上传到 COS

TIM 消息体构建：
  - buildImageMsgBody() → TIMImageElem
  - buildFileMsgBody()  → TIMFileElem

### 顶层函数

#### def `guess_mime_type(filename: str) -> str`

根据文件扩展名猜测 MIME 类型。

#### def `is_image(filename: str, mime_type: str = '') -> bool`

判断是否为图片类型。

#### def `get_image_format(mime_type: str) -> int`

获取 TIM 图片格式编号。

#### def `md5_hex(data: bytes) -> str`

计算 MD5 十六进制摘要。

#### def `generate_file_id() -> str`

生成随机文件 ID（32 位 hex）。

#### def `parse_image_size(data: bytes) -> Optional[dict[str, int]]`

解析图片宽高（支持 JPEG/PNG/GIF/WebP），无需第三方依赖。
返回 {"width": w, "height": h} 或 None（无法识别）。

#### def `download_url(url: str, max_size_mb: int = DEFAULT_MAX_SIZE_MB) -> tuple[bytes, str]`

下载 URL 内容，返回 (bytes, content_type)。

Args:
    url:          HTTP(S) URL
    max_size_mb:  最大允许大小（MB），超过则抛出异常

Returns:
    (data_bytes, content_type_string)

Raises:
    ValueError:  内容超过大小限制
    httpx.HTTPError: 网络/HTTP 错误

**异常**: `ValueError`, `httpx.HTTPError`

#### def `get_cos_credentials(app_key: str, api_domain: str, token: str, filename: str = 'file', file_id: Optional[str] = None, bot_id: str = '', route_env: str = '') -> dict`

调用 genUploadInfo 接口获取 COS 临时密钥及上传配置。

Args:
    app_key:        应用 Key（用于 X-ID 头）
    api_domain:     API 域名（如 https://bot.yuanbao.tencent.com）
    token:          当前有效的签票 token（X-Token 头）
    filename:       待上传的文件名（含扩展名）
    file_id:        客户端生成的唯一文件 ID（不传则自动生成）
    bot_id:         Bot 账号 ID（用于 X-ID 头）

Returns:
    COS 上传配置 dict，包含以下字段：
        bucketName         (str)  — COS Bucket 名称
        region             (str)  — COS 地域
        location           (str)  — 上传 Key（对象路径）
        encryptTmpSecretId (str)  — 临时 SecretId
        encryptTmpSecretKey(str)  — 临时 SecretKey
        encryptToken       (str)  — SessionToken
        startTime          (int)  — 凭证起始时间戳（Unix）
        expiredTime        (int)  — 凭证过期时间戳（Unix）
        resourceUrl        (str)  — 上传后的公网访问 URL
        resourceID         (str)  — 资源 ID（可选）

Raises:
    RuntimeError: 接口返回非 0 code 或字段缺失

**异常**: `RuntimeError`

#### def `upload_to_cos(file_bytes: bytes, filename: str, content_type: str, credentials: dict, bucket: str, region: str) -> dict`

通过 httpx PUT 请求将文件上传到 COS。
使用临时凭证（tmpSecretId/tmpSecretKey/sessionToken）构建 HMAC-SHA1 签名。

Args:
    file_bytes:   文件二进制内容
    filename:     文件名（用于辅助计算 MIME、UUID）
    content_type: MIME 类型（如 "image/jpeg"）
    credentials:  get_cos_credentials() 返回的 dict，包含：
                    encryptTmpSecretId  → tmpSecretId
                    encryptTmpSecretKey → tmpSecretKey
                    encryptToken        → sessionToken
                    location            → COS key（对象路径）
                    resourceUrl         → 上传后公网 URL
                    startTime           → 凭证起始时间（Unix）
                    expiredTime         → 凭证过期时间（Unix）
    bucket:       COS Bucket 名称（如 chatbot-1234567890）
    region:       COS 地域（如 ap-guangzhou）

Returns:
    上传结果 dict，包含：
        url       (str)           — COS 公网访问 URL
        uuid      (str)           — 文件内容 MD5
        size      (int)           — 文件大小（字节）
        width     (int, optional) — 图片宽度（仅图片）
        height    (int, optional) — 图片高度（仅图片）

Raises:
    httpx.HTTPStatusError: COS 返回非 2xx 状态
    RuntimeError:          credentials 字段缺失

**异常**: `httpx.HTTPStatusError`, `RuntimeError`

#### def `build_image_msg_body(url: str, uuid: Optional[str] = None, filename: Optional[str] = None, size: int = 0, width: int = 0, height: int = 0, mime_type: str = '') -> list[dict]`

构建腾讯 IM TIMImageElem 消息体。
参考：https://cloud.tencent.com/document/product/269/2720

Args:
    url:       图片公网访问 URL（COS resourceUrl）
    uuid:      文件 UUID（MD5 或其他唯一标识）
    filename:  文件名（uuid 为空时作为备用）
    size:      文件大小（字节）
    width:     图片宽度（像素）
    height:    图片高度（像素）
    mime_type: MIME 类型（用于确定 image_format）

Returns:
    TIMImageElem 消息体列表（适合直接放入 msg_body）

#### def `build_file_msg_body(url: str, filename: str, uuid: Optional[str] = None, size: int = 0) -> list[dict]`

构建腾讯 IM TIMFileElem 消息体。
参考：https://cloud.tencent.com/document/product/269/2720

Args:
    url:      文件公网访问 URL（COS resourceUrl）
    filename: 文件名（含扩展名）
    uuid:     文件 UUID（MD5 或其他唯一标识，不传则使用 filename）
    size:     文件大小（字节）

Returns:
    TIMFileElem 消息体列表（适合直接放入 msg_body）


## gateway.platforms.yuanbao_proto

### 模块文档

yuanbao_proto.py - Yuanbao WebSocket 协议编解码（纯 Python 实现）

协议层级：
  WebSocket frame
    └── ConnMsg (protobuf: trpc.yuanbao.conn_common.ConnMsg)
          ├── head: Head  (cmd_type, cmd, seq_no, msg_id, module, ...)
          └── data: bytes  (业务 payload，标准 protobuf)
                └── InboundMessagePush / SendC2CMessageReq / SendGroupMessageReq / ...
                      (trpc.yuanbao.yuanbao_conn.yuanbao_openclaw_proxy.*)

注意：conn 层（ConnMsg）本身是标准 protobuf，不是自定义二进制格式。
     conn.proto 注释里的自定义格式（magic+head_len+body_len）仅用于 quic/tcp，
     WebSocket 直接传 ConnMsg protobuf bytes（无粘包问题，每个 ws frame = 一条消息）。

实现方式：手写 varint / protobuf wire-format 编解码，不依赖第三方 protobuf 库。

### 顶层函数

#### def `next_seq_no() -> int`

生成递增序列号（线程安全，溢出时归零）

#### def `encode_conn_msg(msg_type: int, seq_no: int, data: bytes) -> bytes`

编码 ConnMsg（简化接口，对应任务要求的签名）。

Args:
    msg_type: cmd_type（CMD_TYPE 枚举值）
    seq_no:   序列号
    data:     内层 payload bytes（业务 protobuf）

Returns:
    ConnMsg 编码后的 bytes

#### def `decode_conn_msg(data: bytes) -> dict`

解码 ConnMsg，返回 {msg_type, seq_no, data, head}。

Returns:
    {
      "msg_type": int,      # cmd_type
      "seq_no":   int,
      "data":     bytes,    # 内层 payload
      "head":     dict,     # 完整 head 字段
    }

#### def `encode_conn_msg_full(cmd_type: int, cmd: str, seq_no: int, msg_id: str, module: str, data: bytes, need_ack: bool = False) -> bytes`

编码完整的 ConnMsg（含 cmd/msg_id/module 等 head 字段）。
比 encode_conn_msg 提供更多 head 控制。

#### def `encode_biz_msg(service: str, method: str, req_id: str, body: bytes) -> bytes`

将业务 payload 包装为 ConnMsg bytes。

Args:
    service: 模块名（head.module），如 "yuanbao_openclaw_proxy"
    method:  命令字（head.cmd），如 "send_c2c_message"
    req_id:  消息 ID（head.msg_id）
    body:    已编码的业务 protobuf bytes

Returns:
    ConnMsg bytes（可直接发送到 WebSocket）

#### def `decode_biz_msg(data: bytes) -> dict`

解码 ConnMsg bytes，返回业务层信息。

Returns:
    {
      "service":     str,    # head.module
      "method":      str,    # head.cmd
      "req_id":      str,    # head.msg_id
      "body":        bytes,  # 内层 biz payload
      "is_response": bool,   # cmd_type == 1 (Response)
      "head":        dict,   # 完整 head
    }

#### def `decode_inbound_push(data: bytes) -> Optional[dict]`

解析入站消息推送的 biz payload（InboundMessagePush proto bytes）。

Args:
    data: ConnMsg.data 字段的 bytes（即 biz payload）

Returns:
    {
      "from_account":  str,
      "to_account":    str (可选),
      "group_code":    str (可选，群消息才有),
      "group_id":      str (可选),
      "group_name":    str (可选),
      "msg_key":       str,
      "msg_id":        str,
      "msg_seq":       int,
      "msg_random":    int,
      "msg_time":      int,
      "sender_nickname": str,
      "msg_body":      [{"msg_type": str, "msg_content": dict}, ...],
      "callback_command": str,
      "cloud_custom_data": str,
      "bot_owner_id":  str,
      "claw_msg_type": int,
      "private_from_group_code": str,
      "trace_id":      str,
      "recall_msg_seq_list": [{"msg_seq": int, "msg_id": str}, ...] 或 None,
    }
    或 None（解析失败）

#### def `decode_forward_msg_data(data: bytes) -> Optional[dict]`

Parse ForwardMsgData protobuf bytes (the base64-decoded ext_map value).

Args:
    data: ForwardMsgData protobuf bytes, after base64 decoding.

Returns:
    A dict matching the structure consumed by
    ``ForwardedRecordsParseMiddleware.build_forward_text``
    (``sub_type`` / ``nick_name`` / ``msg`` list); ``None`` on parse failure.

#### def `encode_forward_msg_data(data: dict) -> bytes`

Encode ForwardMsgData protobuf bytes (inverse of ``decode_forward_msg_data``).

Mainly used to build mock / test data; production code never needs to encode this.

#### def `encode_send_c2c_message(to_account: str, msg_body: list, from_account: str, msg_id: str = '', msg_random: int = 0, msg_seq: Optional[int] = None, group_code: str = '', trace_id: str = '') -> bytes`

Encode a C2C send-message request and return the full ConnMsg bytes
(ready to be sent over WebSocket).

Args:
    to_account:   recipient account
    msg_body:     list of message-body elements; each item is
                  {"msg_type": str, "msg_content": dict}.
                  Example: [{"msg_type": "TIMTextElem", "msg_content": {"text": "hello"}}]
    from_account: sender account (the bot account)
    msg_id:       unique message ID (req_id is used when empty)
    msg_random:   random number for de-duplication
    msg_seq:      message sequence number (optional)
    group_code:   filled in for the "private chat originating from a group" case
    trace_id:     trace ID for request tracing

Returns:
    ConnMsg bytes

#### def `encode_send_group_message(group_code: str, msg_body: list, from_account: str, msg_id: str = '', to_account: str = '', random: str = '', msg_seq: Optional[int] = None, ref_msg_id: str = '', trace_id: str = '') -> bytes`

Encode a group send-message request and return the full ConnMsg bytes
(ready to be sent over WebSocket).

Args:
    group_code:   group ID
    msg_body:     list of message-body elements
    from_account: sender account (the bot account)
    msg_id:       unique message ID
    to_account:   targeted recipient (usually empty)
    random:       random string for de-duplication
    msg_seq:      message sequence number
    ref_msg_id:   ID of the referenced (quoted) message
    trace_id:     trace ID for request tracing

Returns:
    ConnMsg bytes

#### def `encode_auth_bind(biz_id: str, uid: str, source: str, token: str, msg_id: str, app_version: str = '', operation_system: str = '', bot_version: str = '', route_env: str = '') -> bytes`

构造 auth-bind 请求 ConnMsg bytes。

AuthBindReq fields:
  1: biz_id (string)
  2: auth_info (message AuthInfo: uid=1, source=2, token=3)
  3: device_info (message DeviceInfo: app_version=1, app_operation_system=2, instance_id=10, bot_version=24)
  5: env_name (string)

#### def `encode_ping(msg_id: str) -> bytes`

构造 ping 请求 ConnMsg bytes（PingReq 为空消息）

#### def `encode_push_ack(original_head: dict) -> bytes`

构造 push ACK 回包

#### def `encode_send_private_heartbeat(from_account: str, to_account: str, heartbeat: int = WS_HEARTBEAT_RUNNING) -> bytes`

编码 SendPrivateHeartbeatReq，返回完整 ConnMsg bytes。

SendPrivateHeartbeatReq fields:
  1: from_account (string)
  2: to_account   (string)
  3: heartbeat    (varint: RUNNING=1, FINISH=2)

#### def `encode_send_group_heartbeat(from_account: str, group_code: str, heartbeat: int = WS_HEARTBEAT_RUNNING, send_time: int = 0) -> bytes`

编码 SendGroupHeartbeatReq，返回完整 ConnMsg bytes。

SendGroupHeartbeatReq fields:
  1: from_account (string)
  2: to_account   (string)  — 群场景留空
  3: group_code   (string)
  4: send_time    (int64, ms timestamp)
  5: heartbeat    (varint: RUNNING=1, FINISH=2)

#### def `encode_query_group_info(group_code: str) -> bytes`

编码 QueryGroupInfoReq，返回完整 ConnMsg bytes。

QueryGroupInfoReq fields:
  1: group_code (string)

#### def `decode_query_group_info_rsp(data: bytes) -> Optional[dict]`

解码 QueryGroupInfoRsp biz payload。

Proto 结构（对齐 TS biz-codec / member.ts queryGroupInfo）：

  message QueryGroupInfoRsp {
    int32  code       = 1;
    string message    = 2;
    GroupInfo group_info = 3;   // 嵌套 message
  }

  message GroupInfo {
    string group_name            = 1;
    string group_owner_user_id   = 2;
    string group_owner_nickname  = 3;
    uint32 group_size            = 4;
  }

Returns:
    解码后的 dict，或 None（解析失败）

#### def `encode_get_group_member_list(group_code: str, offset: int = 0, limit: int = 200) -> bytes`

编码 GetGroupMemberListReq，返回完整 ConnMsg bytes。

GetGroupMemberListReq fields:
  1: group_code (string)
  2: offset     (uint32)
  3: limit      (uint32)

#### def `decode_get_group_member_list_rsp(data: bytes) -> Optional[dict]`

解码 GetGroupMemberListRsp biz payload。

GetGroupMemberListRsp fields:
  1: code         (int32)
  2: message      (string)
  3: members      (repeated message MemberInfo)
  4: next_offset  (uint32)
  5: is_complete  (bool/varint)

MemberInfo fields:
  1: user_id      (string)
  2: nickname     (string)
  3: role         (uint32)  — 0=member, 1=admin, 2=owner
  4: join_time    (uint32)
  5: name_card    (string)  — 群昵称

Returns:
    {
      "code": int,
      "message": str,
      "members": [{"user_id": str, "nickname": str, "role": int, ...}, ...],
      "next_offset": int,
      "is_complete": bool,
    }
    或 None（解析失败）


## gateway.platforms.yuanbao_sticker

### 模块文档

Yuanbao sticker (TIMFaceElem) support.

Ported from yuanbao-openclaw-plugin/src/sticker/.

TIMFaceElem wire format:
    {
        "msg_type": "TIMFaceElem",
        "msg_content": {
            "index": 0,          # always 0 per Yuanbao convention
            "data": "<json>",    # serialised sticker metadata
        }
    }

The `data` field carries a JSON string with the sticker's metadata so the
receiver can look up the correct asset in the emoji pack.

### 顶层函数

#### def `get_sticker_by_name(name: str) -> Optional[dict]`

按名称查找贴纸，支持模糊匹配。

匹配优先级：
  1. 完全相等（name）
  2. name 包含查询词（前缀/子串）
  3. description 包含查询词（同义词搜索）
  4. 通用模糊评分（与 sticker-search 同算法），命中即返回得分最高的一条

返回 sticker dict，找不到返回 None。

#### def `get_random_sticker(category: str = None) -> dict`

随机返回一个贴纸。

若指定 category，则在 description 中含有该关键词的贴纸里随机选取；
category 为 None 时从全表随机。

#### def `get_sticker_by_id(sticker_id: str) -> Optional[dict]`

按 sticker_id 精确查找贴纸。

#### def `search_stickers(query: str, limit: int = 10) -> list[dict]`

在内置贴纸表中按模糊匹配排序返回前 N 条结果。

评分综合 name/description 字段的子串、字符多重集覆盖、bigram Jaccard、子序列比例。
name 权重略高于 description（×0.88）。空 query 时按字典顺序返回前 N 条。

#### def `build_face_msg_body(face_index: int, face_type: int = 1, data: Optional[str] = None) -> list`

构造 TIMFaceElem 消息体。

Yuanbao 约定：
  - index 固定传 0（服务端通过 data 字段识别具体表情）
  - data 为 JSON 字符串，包含 sticker_id / package_id 等字段

Args:
    face_index: 保留字段，暂时不影响 wire format（Yuanbao 固定 index=0）。
                当 face_index > 0 时视为旧版 QQ 表情 ID，直接放入 index。
    face_type:  保留字段（兼容旧接口，当前未使用）。
    data:       已序列化的 JSON 字符串；为 None 时仅传 index。

Returns:
    符合 Yuanbao TIM 协议的 msg_body list，如::

        [{"msg_type": "TIMFaceElem", "msg_content": {"index": 0, "data": "..."}}]

#### def `build_sticker_msg_body(sticker: dict) -> list`

从 STICKER_MAP 中的 sticker dict 直接构造 TIMFaceElem 消息体。

这是 send_sticker() 的内部辅助，确保 data 字段与原始 JS 插件一致。


## gateway.profile_routing

### 模块文档

Profile-based routing for the gateway with hierarchical matching.

Allows a single Hermes instance to route specific Discord guilds/channels/threads
to different profiles — each with their own model, tools, memory, and persona.

Matching priority (most specific first):
  1. platform + chat_id + thread_id (exact thread)  — specificity 14
  2. platform + chat_id (channel route)             — specificity 6
  3. platform + guild_id (guild/server route)       — specificity 2
  4. No match                                       → default profile

Parent-chain matching:
For Discord threads and forum posts, ``parent_chat_id`` carries the
direct parent (the channel for a thread, the forum channel for a post).
Routes keyed on a channel match both direct messages and messages in
any thread/post whose parent is that channel.

Configuration (config.yaml):

    gateway:
      profile_routes:
        - name: server-default
          platform: discord
          guild_id: "YOUR_GUILD_ID"
          profile: server-profile

        - name: special-channel
          platform: discord
          guild_id: "YOUR_GUILD_ID"
          chat_id: "YOUR_CHANNEL_ID"
          profile: channel-profile

        - name: thread-route
          platform: discord
          chat_id: "YOUR_CHANNEL_ID"
          thread_id: "YOUR_THREAD_ID"
          profile: thread-profile

### class ProfileRoute

> 继承: `object` ｜ 方法数: 2（公开 2）

A single routing rule that maps a platform scope to a profile.

#### property `specificity(self) -> int`

Higher value = more specific match.

#### def `matches(self, platform: str, guild_id: Optional[str] = None, chat_id: Optional[str] = None, thread_id: Optional[str] = None, parent_chat_id: Optional[str] = None) -> bool`

Return True if this route matches the given source fields.

All configured discriminators are matched conjunctively (AND): every
discriminator that the route declares must hold. ``chat_id`` supports
hierarchical matching for Discord forums/threads:
- Direct channel match: chat_id == route.chat_id
- Thread in channel: parent_chat_id == route.chat_id
A route declaring both ``guild_id`` and ``chat_id`` requires both to
match (a chat match alone does not satisfy a guild constraint).


### 顶层函数

#### def `parse_profile_routes(raw: Optional[List[Dict[str, Any]]]) -> List[ProfileRoute]`

Parse profile_routes from config.yaml into ProfileRoute objects.

Returns routes sorted by specificity (most specific first).

#### def `match_profile_route(routes: List[ProfileRoute], platform: str, guild_id: Optional[str] = None, chat_id: Optional[str] = None, thread_id: Optional[str] = None, parent_chat_id: Optional[str] = None) -> Optional[ProfileRoute]`

Return the best-matching route, or None for no match.


## gateway.readiness

### 模块文档

Bounded, non-destructive readiness probes for authenticated health surfaces.

### 顶层函数

#### def `collect_runtime_readiness(configured_model: str, runtime_status: dict[str, Any] | None, active_api_runs: int = 0, process_completion_queue_depth: int = 0, active_delegations: int = 0) -> dict[str, Any]`

Return bounded readiness diagnostics without mutating runtime state.

The detailed health endpoint is authenticated. Even there, probes expose
status and counts only: never config values, credentials, paths, commands,
queue payloads, or exception messages.


## gateway.relay.__init__

### 模块文档

Relay/connector support package for the Hermes gateway.

EXPERIMENTAL. This package implements the gateway side of the "Gateway Gateway"
relay design: a generic ``RelayAdapter`` plus the wire-serializable
``CapabilityDescriptor`` the connector hands it at handshake time, and the
production ``WebSocketRelayTransport`` that dials the connector. The public API
(module names, descriptor field set, transport protocol) MAY CHANGE without a
deprecation cycle until at least two real Class-1 platforms (Discord + Telegram)
have shaken out the schema.

See ``docs/relay-connector-contract.md`` for the formal cross-repo interface.

Activation is driven by configuration, not a separate feature flag: the relay
platform is registered when a connector relay URL is configured
(``GATEWAY_RELAY_URL`` env or ``gateway.relay_url`` in config.yaml). Deployments
that don't set it are unaffected — exactly the same shape as ``gateway.proxy_url``.

### 顶层函数

#### def `relay_url() -> Optional[str]`

The connector relay endpoint URL, or None when relay is not configured.

Checks ``GATEWAY_RELAY_URL`` (convenient for Docker) first, then
``gateway.relay_url`` in config.yaml. A non-empty value activates the relay
platform; absence means a normal direct/single-tenant gateway.

#### def `relay_platform_identities() -> list[tuple[str, str]]`

The (platform, bot_id) pairs this gateway fronts over the relay (Phase 1.5).

Shape A (multi-platform-per-agent, D-Q1.5c — CUT OVER, no scalar fallback):
one gateway fronts a SET of platforms on one WS connection. The set is the
env-stamped deploy config:

  - ``GATEWAY_RELAY_PLATFORMS`` — comma-sep list (e.g. ``discord,telegram``).
  - ``GATEWAY_RELAY_BOT_IDS`` — JSON keyed map
    ``{"discord": {"botId": "..."}, "telegram": {"botId": "...", "username": "..."}}``.

Returns the ordered list of ``(platform, bot_id)`` pairs (the FIRST is the
default the handshake/descriptor falls back to). The connector accepts N
hellos accumulating into its advertised set; outbound frames discriminate
per-frame on the platform (gateway-gateway D-Q1.5b.1). A platform present in
the list but absent from the ids map resolves with an empty bot_id (the
connector rejects an unprovisioned platform with a structured failure).

Defaults to ``[("relay", "")]`` when nothing is configured (the generic
single-plane fallback for a connector that didn't stamp a platform set).

#### def `relay_bot_username(platform: str) -> Optional[str]`

The bot's deep-link username/handle for a platform (e.g. Telegram's
``@handle`` for ``t.me/<handle>``), read from the per-platform entry in
``GATEWAY_RELAY_BOT_IDS``. None when absent (most platforms don't need one).

#### def `relay_platform_identity() -> tuple[str, str]`

The PRIMARY (platform, bot_id) — the first identity in the configured set.

Kept for call sites that need a single representative identity (the default
descriptor platform, the policy projection's primary). The full set is
``relay_platform_identities()``. Defaults to ``("relay", "")``.

#### def `relay_connection_auth() -> tuple[Optional[str], Optional[str]]`

The (gateway_id, upgrade_secret) this gateway authenticates the WS upgrade with.

Both come from enrollment (``hermes gateway enroll`` writes them to
``~/.hermes/.env``): ``GATEWAY_RELAY_ID`` identifies the enrolled instance,
``GATEWAY_RELAY_SECRET`` is the per-gateway signing secret. Either absent ->
``(None, None)`` and the transport dials unauthenticated (dev/test, or a
connector that doesn't enforce auth). Checks env first (Docker), then
``gateway.relay_id`` / ``gateway.relay_secret`` in config.yaml.

#### def `relay_endpoint() -> Optional[str]`

The gateway's own PUBLIC inbound URL, asserted to the connector at provision.

The connector delivers signed inbound POSTs to this URL and stores it on the
tenant's route rows. It is gateway-asserted (the connector scopes it to the
verified tenant, so a dishonest gateway can only misdirect its OWN inbound).
The *source* of the value differs by deployment but the code path is uniform:
a self-hosted operator sets ``GATEWAY_RELAY_ENDPOINT`` (mirrors how they set
``HERMES_DASHBOARD_PUBLIC_URL``); a hosted/NAS container has the same var
stamped in (NAS knows the public URL only in that case). Absent -> the
gateway provisions outbound-only (no inbound routes written).

Env first (Docker), then ``gateway.relay_endpoint`` in config.yaml.

#### def `relay_route_keys() -> list[str]`

Discriminators (scope_ids / chat_ids / paths) this gateway's tenant owns.

Gateway-provided config, paired with ``relay_endpoint()``: the connector
writes one route row per (routeKey -> tenant, endpoint), so route keys only
take effect alongside an endpoint. Empty -> outbound-only provisioning (the
connector accepts an empty set and writes no route rows).

``GATEWAY_RELAY_ROUTE_KEYS`` is comma-separated; config.yaml
``gateway.relay_route_keys`` may be a list or a comma string.

#### def `relay_instance_id() -> Optional[str]`

Stable per-instance id this gateway forwards at provision (Phase 6 Unit α).

Binds the connector's ``gatewayId -> instanceId`` so the connector can route
inbound per-instance (not tenant-broadcast) once Phase 6 delivery lands. The
value is the NAS ``AgentInstance.id`` for a managed agent (NAS stamps
``GATEWAY_RELAY_INSTANCE_ID`` into the container env, beside
``GATEWAY_RELAY_URL``); a self-hosted operator may set it explicitly. It is
gateway-asserted but safely scoped: the org/tenant stays token-verified, so a
dishonest gateway can only bind ITS OWN tenant's instance — the same posture
as ``relay_endpoint()``. Absent -> the connector stores null and per-instance
routing simply has no binding for this connection yet (back-compat).

Env first (Docker/NAS), then ``gateway.relay_instance_id`` in config.yaml.

#### def `relay_wake_url() -> Optional[str]`

The gateway's WAKE URL, forwarded at provision (Phase 5 §5.2 wake PRIMITIVE).

A poke target the connector issues a payload-free GET to when a buffered-only
(going-idle) destination for this instance receives its first buffered event,
so a suspended gateway wakes, reconnects its relay WS, and drains its
delivery-leg backlog. The value's *source* differs by deployment but the code
path is uniform: a managed/NAS container has ``GATEWAY_RELAY_WAKE_URL`` stamped
in (NAS knows the Fly autostart / dashboard hostname); a self-hosted operator
sets it explicitly (or passes ``--wake-url`` to ``hermes gateway enroll``).

Gateway-asserted but safely scoped: the org/tenant stays token-verified, so a
dishonest gateway can only register a wake target for ITS OWN instance — the
same posture as ``relay_instance_id()`` / the retired ``relay_endpoint()``.
Absent -> the connector stores null and simply can't wake this instance
(buffering still works; the gateway drains whenever it next reconnects).

Env first (Docker/NAS), then ``gateway.relay_wake_url`` in config.yaml.

#### def `relay_relevance_policy(platform: Optional[str] = None) -> Optional[dict]`

Project a fronted platform's RELEVANCE config into the connector's generic vocabulary.

The connector's relevance gate (Phase 6 Unit ζ) reasons over a
platform-agnostic policy — ``requireAddress`` / ``freeResponseScopes`` /
``allowOtherBots`` — NOT over Discord/Telegram words. This is the gateway
side of that contract: it reads the agent's existing relevance knobs and
emits the generic shape the connector stores per-instance (Phase 1.5: the
connector keys the policy by ``(tenant, platform, instanceId)``, so each
fronted platform gets its own row — pass its name here).

Mapping (the connector vocabulary ← the gateway's existing config):
  - ``requireAddress``     ← the platform's ``require_mention`` (the agent
    only engages a non-owner message that @mentions it / replies to it).
  - ``freeResponseScopes`` ← the platform's ``free_response_channels`` (the
    channel/scope ids where ``require_mention`` is waived — same scope
    vocabulary the connector's δ scope grants + ε floor use).
  - ``allowOtherBots``     ← ``{PLATFORM}_ALLOW_BOTS`` in {"mentions","all"}
    (whether bot-authored messages are admitted; default off).

Read from the relay platform's config block (the platform the connector
fronts, e.g. ``discord:``), falling back to the bridged top-level keys, then
the ``{PLATFORM}_*`` env. ``platform`` defaults to the PRIMARY fronted
platform (back-compat). Returns the generic dict, or None when relay isn't
configured or the platform exposes no relevance knobs (⇒ the connector's
quiet default already matches, so there's nothing to declare).

#### def `self_provision_relay() -> bool`

Boot-time relay self-provision: mint relay creds in-process, no human, no disk.

Fires when relay is configured (``relay_url()`` set) and NO per-gateway secret
is already present, AND the agent can resolve its own Nous access token. In
that case the runtime resolves the agent's own Nous access token (the same
``resolve_nous_access_token()`` the enroll CLI / dashboard register use),
POSTs ``/relay/provision`` asserting its own endpoint + route keys, and sets
``GATEWAY_RELAY_ID`` / ``GATEWAY_RELAY_SECRET`` / ``GATEWAY_RELAY_DELIVERY_KEY``
into ``os.environ`` so the subsequent ``register_relay_adapter()`` picks them
up. The creds live ONLY in process memory — never written to ``~/.hermes/.env``.

The trigger is deliberately NOT ``is_managed()``: that means
"package-manager/NixOS-managed" and is False on a NAS-hosted Fly agent (which
sets neither ``HERMES_MANAGED`` nor a ``.managed`` marker), so gating on it
blocked the exact hosted case this is for. The real signal is "you pointed me
at a connector and didn't pin a secret" — which is both NAS-independent and
self-guarding:

  - A NAS-hosted agent: has ``GATEWAY_RELAY_URL``, no pinned secret, and a
    bootstrapped NAS token -> self-provisions.
  - A self-hosted operator who ran ``hermes gateway enroll``: has a PINNED
    ``GATEWAY_RELAY_SECRET`` -> skipped (the secret-present guard below).
  - A self-hosted box with a relay URL but no NAS identity:
    ``resolve_nous_access_token()`` fails -> graceful no-op.

Stateless: process-env creds don't survive a restart, so a hosted container
re-provisions every boot; the connector's rotation window covers a still-
connected prior instance. An explicitly-pinned ``GATEWAY_RELAY_SECRET`` (env
or config) is RESPECTED — self-provision skips so an operator pin isn't
stomped.

Returns True if it provisioned, False otherwise. NEVER raises: a provision
failure logs and returns False so the gateway still boots (and
``register_relay_adapter`` will simply dial unauthenticated / be rejected,
rather than the whole gateway crashing).

#### def `send_relay_policy() -> bool`

Declare this gateway's relevance policy to the connector (Phase 6 Unit ζ).

Runs at boot AFTER the per-gateway secret is resolved (self-provisioned or
pinned), projecting the agent's relevance config into the generic vocabulary
(``relay_relevance_policy``) and POSTing it to ``/relay/policy`` with the
gateway's own upgrade token. The connector stores it per-instance and the
relevance gate enforces it on delivery — so the SAME mention-gating /
free-response / allow-bots behavior the agent applies directly also governs
relay delivery, and excluded traffic never wakes a scaled-to-zero agent.

Self-healing: the agent is the source of truth and re-declares every boot
(mirrors the ``routeKeys`` upsert at provision). Idempotent — a full replace.

NEVER raises and NEVER blocks boot: relevance is an optimization layered on
the δ/ε authorization gate (which already protects isolation), so a failed
declaration just means the connector keeps the prior/quiet policy. Returns
True iff the connector accepted the policy (HTTP 200).

#### def `register_relay_adapter(force: bool = False, url: Optional[str] = None) -> bool`

Register the generic ``relay`` platform via the platform registry.

Registers when a relay URL is configured (or ``force=True`` for tests, which
builds a transport-less adapter — the unit-test posture). Returns True if
registration happened. Additive: uses the same registry path as plugin
adapters, so no core dispatch changes are needed.

When a URL is present the factory builds a live ``WebSocketRelayTransport``;
the ``RelayAdapter`` negotiates the real ``CapabilityDescriptor`` at
``connect()`` time via ``transport.handshake()``.


## gateway.relay.adapter

### 模块文档

RelayAdapter — one generic gateway adapter fronted by the connector. EXPERIMENTAL.

A single ``BasePlatformAdapter`` subclass that, at handshake, receives a
``CapabilityDescriptor`` from the connector telling it which platform it is
fronting and which capabilities to advertise to the ``GatewayStreamConsumer``.
It implements the four abstract methods (``connect`` / ``disconnect`` / ``send``
/ ``get_chat_info``) plus the capability surface (``MAX_MESSAGE_LENGTH``,
``message_len_fn``, ``supports_draft_streaming``) by delegating wire I/O to an
injected transport and reading capabilities off the descriptor.

There is NO per-platform gateway code: the connector is the only side that knows
"this chat_id maps to a Discord channel, send it via the Discord websocket."
The gateway sees an ordinary ``MessageEvent`` in and calls ``adapter.send`` out.

EXPERIMENTAL: the transport protocol and descriptor schema may change without a
deprecation cycle until >=2 Class-1 platforms validate them.

### class RelayAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 20（公开 10）

Generic relay adapter advertising a connector-negotiated capability profile.

#### def `__init__(config: PlatformConfig, descriptor: CapabilityDescriptor, transport: Optional[RelayTransport] = None) -> None`

#### property `authorization_is_upstream(self) -> bool`

Relay authorization is enforced by the connector, not locally.

The connector authenticates this gateway's WS (per-instance secret) and
performs owner-only author-binding resolution before delivering, so any
inbound relay event was already authorized as THIS instance's bound user
(``user_instance_binding``, keyed on the connector-observed author id).
The instance therefore must not default-deny relay users for lack of a
local ``RELAY_ALLOWED_USERS`` env allowlist. See
``BasePlatformAdapter.authorization_is_upstream``.

#### property `message_len_fn(self) -> Callable[[str], int]`

#### def `supports_draft_streaming(self, chat_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

**异常**: `RuntimeError`

#### async def `on_interrupt(self, session_key: str, chat_id: str) -> None`

Bridge a connector-delivered /stop into the adapter's interrupt path.

The connector forwards a mid-turn interrupt down the socket owned by
the gateway instance running ``session_key``; this routes it to the
existing per-session interrupt mechanism (sets the
``_active_sessions[session_key]`` Event and clears typing), cancelling
the right turn without touching sibling sessions.

#### async def `disconnect(self) -> None`

#### async def `go_dormant(self) -> bool`

Quiesce the relay for a scale-to-zero suspend (D12 / Phase 0).

Unlike ``disconnect()`` (terminal teardown for shutdown/restart), this
keeps the adapter's reconnect path armed so the gateway re-dials and
drains its buffered backlog when the machine wakes. Delegates to the
transport's ``go_dormant()`` when available; a transport without it (the
stub) is a no-op that returns False, so callers degrade safely.

NOTE: deliberately does NOT stop the revocation monitor — going dormant
is not a teardown; the monitor stays live so a real opt-out/revocation
during dormancy is still surfaced on wake.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### async def `send_follow_up(self, session_key: str, kind: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send via a shared-identity capability bound to a session (A2 outbound).

The gateway never holds the credential: it names the session it is
already in plus the capability ``kind``, and the connector resolves the
real value from its vault and egresses (enforcing the tenant match). Used
e.g. to post a Discord interaction follow-up as the shared bot without
the token ever reaching the gateway. See RelayTransport.send_follow_up.


## gateway.relay.auth

### 模块文档

Gateway-side relay authentication primitives. EXPERIMENTAL.

The connector⇄gateway channel is authenticated because a gateway may be
customer-managed and internet-exposed (see the connector repo
``docs/connector-gateway-auth-design.md``). This module is the **gateway half**
of two HMAC schemes whose wire bytes must match the connector's TypeScript
exactly:

1. **WS upgrade auth** (gateway → connector): the gateway presents
   ``Authorization: Bearer <token>`` on the ``/relay`` WebSocket upgrade, where
   ``token = make_upgrade_token(gateway_id, secret)``. Mirrors the connector's
   ``relayAuthToken.ts`` ``makeToken`` (``src/core/relayAuthToken.ts``):
   ``base64url(f"{payload}:{exp}:{sig}")`` with
   ``sig = HMAC_SHA256(f"{payload}:{exp}", secret).hexdigest()`` and
   ``payload == gateway_id``.

2. **Inbound delivery signature** (connector → gateway): the connector signs
   each inbound POST with the per-tenant *delivery key*, carried as
   ``x-relay-timestamp`` + ``x-relay-signature`` headers; the gateway verifies
   before accepting the event. Mirrors the connector's ``deliverySigning.ts``:
   ``sig = HMAC_SHA256(f"{ts}.{body_json}", key).hexdigest()`` over the EXACT
   request body bytes, with a replay-window skew check.

Both schemes use a **multi-secret verify list** (primary first, then a secondary
during a rotation window), exactly like ``api/src/handlers/stats_oauth.ts`` — so
a secret rotation doesn't invalidate outstanding tokens.

EXPERIMENTAL: may change without a deprecation cycle until ≥2 Class-1 platforms
validate the relay contract.

### 顶层函数

#### def `sign(payload: str, secret: str) -> str`

HMAC-SHA256 hex digest — the connector's ``sign`` (relayAuthToken.ts).

#### def `verify_signature(payload: str, sig_hex: str, secrets: Sequence[str]) -> bool`

Constant-time check that ``sig_hex`` is a valid HMAC of ``payload`` under
ANY of ``secrets`` (rotation window). Length-mismatched candidates are
skipped without a timing leak. Mirrors ``verifySignature``.

#### def `make_token(payload: str, secret: str, ttl_seconds: int = 0) -> str`

Build a signed, optionally-expiring token — the connector's ``makeToken``.

``base64url(f"{payload}:{exp}:{sig}")`` where ``exp`` is a unix-seconds
expiry (0 = never) and ``sig = HMAC_SHA256(f"{payload}:{exp}", secret)``.
base64url is unpadded to match Node's ``Buffer.toString("base64url")``.

#### def `make_upgrade_token(gateway_id: str, secret: str, ttl_seconds: int = _DEFAULT_UPGRADE_TTL_SECONDS) -> str`

The WS-upgrade bearer token a gateway sends: ``payload = gateway_id``.

The connector peeks ``gateway_id`` (the payload head) to index its secret
verify list, then verifies the signature against that gateway's stored
secret(s). Mirrors the connector's ``makeUpgradeToken``.

#### def `verify_token(token: str, secrets: Sequence[str]) -> Optional[str]`

Verify a token built by ``make_token``; return the payload or None.

Splits from the right so a payload may itself contain colons (mirrors the
connector's ``verifyToken``). Rejects an expired token and any signature
that doesn't match a secret in the verify list.

#### def `verify_delivery_signature(body_json: str, timestamp: Optional[str], signature: Optional[str], verify_keys: Sequence[str], max_skew_seconds: int = _DEFAULT_MAX_SKEW_SECONDS, now: Optional[int] = None) -> bool`

Verify a connector→gateway inbound delivery signature.

``body_json`` MUST be the exact request body bytes decoded as UTF-8 — the
connector signs over the literal serialized body, so the gateway verifies
over the literal received body (no re-serialization). Checks the timestamp
is within ``max_skew_seconds`` of now and the HMAC matches any key in the
rotation verify list. Mirrors the connector's ``verifyDeliverySignature``.


## gateway.relay.descriptor

### 模块文档

CapabilityDescriptor — the relay handshake payload. EXPERIMENTAL.

The connector hands a ``CapabilityDescriptor`` to the gateway's ``RelayAdapter``
at handshake time; it tells the adapter which platform it is fronting and which
capabilities to advertise to the ``GatewayStreamConsumer`` (char limit,
draft-streaming, edit/threading support, markdown dialect, length unit). It is
the linchpin of the generalization: one gateway adapter serves Discord,
Telegram, Matrix, Signal, ... without per-platform branching.

EXPERIMENTAL: this schema MAY CHANGE without a deprecation cycle until at least
two real Class-1 platforms have validated it. Evolution during the experimental
phase is additive-only, gated by ``contract_version`` (see
docs/relay-connector-contract.md).

Field origins (most are a wire-serializable projection of ``PlatformEntry`` plus
the per-instance capability methods on ``BasePlatformAdapter``):

- ``max_message_length`` -> ``PlatformEntry.max_message_length`` / adapter
  ``MAX_MESSAGE_LENGTH`` attribute (read by stream_consumer).
- ``len_unit``           -> selects which ``message_len_fn`` the adapter installs
  ("chars" = builtin len; "utf16" = Telegram-style UTF-16 code-unit counting).
- ``supports_draft_streaming`` -> adapter ``supports_draft_streaming()`` probe.
- ``supports_edit``      -> whether edit-based streaming is possible (Discord/
  Telegram yes; Signal/SMS no -> consumer degrades to one-message-per-segment).
- ``supports_threads``   -> ``create_handoff_thread`` capability flag.
- ``markdown_dialect``   -> presentation hint (e.g. "markdown_v2", "discord").
- ``emoji`` / ``platform_hint`` / ``pii_safe`` -> ``PlatformEntry`` fields of the
  same name.

### class CapabilityDescriptor

> 继承: `object` ｜ 方法数: 3（公开 3）

Immutable capability descriptor negotiated at relay handshake.

Frozen so a descriptor cannot be mutated after handshake — the adapter
advertises a fixed capability profile for the life of the connection.

#### def `to_json(self) -> str`

Serialize to a compact, stable JSON string for the handshake frame.

#### classmethod `from_json(cls, data: str) -> CapabilityDescriptor`

Deserialize from a handshake JSON string.

Unknown keys are ignored (forward-compat: a newer connector may send
fields this gateway does not know yet); missing optional keys fall back
to dataclass defaults.

#### classmethod `from_platform_entry(cls, entry, len_unit: str = 'chars', supports_draft_streaming: bool = False, supports_edit: bool = True, supports_threads: bool = False, markdown_dialect: str = 'plain') -> CapabilityDescriptor`

Project a ``gateway.platform_registry.PlatformEntry`` into a descriptor.

Demonstrates the descriptor is a *subset/projection* of what
``PlatformEntry`` already encodes, not a parallel concept: ``label``,
``max_message_length``, ``emoji``, ``platform_hint``, ``pii_safe`` and
the platform name come straight off the entry. The runtime capability
bits that ``PlatformEntry`` does NOT encode (length unit, draft/edit/
thread/markdown behavior) are supplied by the caller — in production
the connector fills these from the live adapter's capability methods.

``max_message_length`` of 0 on a ``PlatformEntry`` means "no limit";
we map that to the stream_consumer default of 4096 so the descriptor
always carries a concrete chunking bound.


## gateway.relay.transport

### 模块文档

Relay transport protocol — the gateway<->connector wire contract. EXPERIMENTAL.

The ``RelayAdapter`` (gateway side) delegates all wire I/O to a ``RelayTransport``.
The gateway dials OUT to the connector, so a production transport is a WebSocket
client; in tests it is an in-memory stub (``tests/gateway/relay/stub_connector.py``).

This module defines the protocol surface only — no concrete transport. The
contract has four concerns:

  1. Lifecycle: ``connect`` / ``disconnect``.
  2. Handshake: ``handshake`` returns the ``CapabilityDescriptor`` the connector
     advertises for the platform this adapter fronts.
  3. Inbound: ``set_inbound_handler`` registers a callback the transport invokes
     with each normalized ``MessageEvent`` the connector delivers.
  4. Outbound: ``send_outbound`` carries send/edit/typing actions back to the
     connector; ``get_chat_info`` proxies a chat-info lookup; ``send_interrupt``
     routes a mid-turn /stop down the socket that owns the session_key.

EXPERIMENTAL: may change without a deprecation cycle until >=2 Class-1 platforms
validate it. See docs/relay-connector-contract.md.

### class RelayTransport

> 继承: `Protocol` ｜ 方法数: 10（公开 10）

Full gateway<->connector transport contract.

#### async def `connect(self) -> bool`

Open the connection to the connector; return True on success.

#### async def `disconnect(self) -> None`

Close the connection.

#### async def `handshake(self) -> CapabilityDescriptor`

Return the capability descriptor the connector advertises.

#### def `set_inbound_handler(self, handler: InboundHandler) -> None`

Register the callback invoked with each inbound MessageEvent.

#### def `set_passthrough_handler(self, handler: PassthroughHandler) -> None`

Register the callback invoked with each forwarded passthrough request.

Phase 5 §5.1: the passthrough plane (Discord interactions, Twilio, …)
answers the provider's edge ACK at the connector, then forwards the real
request to the gateway over this same outbound socket (a hosted gateway
has no public inbound port). The transport invokes ``handler(forward,
buffer_id)`` for each ``passthrough_forward`` frame. Optional on a
transport (an in-memory stub may not implement it).

#### async def `send_outbound(self, action: Dict[str, Any], platform: Optional[str] = None) -> Dict[str, Any]`

Carry an outbound action (send/edit/typing) to the connector.

Returns a result dict; for ``op == "send"`` it carries
``success`` and optionally ``message_id`` / ``error``.

``platform`` (Phase 1.5) tags WHICH fronted platform this reply targets,
carried on the OutboundFrame envelope so a gateway fronting N platforms
egresses each reply through the right sender (the transport resolves the
matching advertised botId). Omitted ⇒ the connector falls back to the
session's default platform (single-platform deploys unchanged).

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Proxy a chat-info lookup to the connector.

#### async def `send_interrupt(self, session_key: str, reason: Optional[str] = None) -> None`

Route a mid-turn /stop to the connector for ``session_key``.

The connector forwards it down the socket owned by the gateway
instance running that session (the /stop routing invariant). On the
gateway side this is the OUTBOUND direction; the actual task
cancellation happens when the connector echoes an interrupt inbound
(handled in Task 1.4).

#### async def `go_idle(self, timeout_s: float = 10.0) -> bool`

Ask the connector to flip this instance to buffered-only (Phase 5 §5.3).

Sends ``going_idle`` and awaits the connector's ``going_idle_ack`` — the
connector-authoritative confirmation that live delivery stopped and inbound
now buffers durably for replay on reconnect (Q-5.3c). Returns True on ack,
False on timeout / not-connected (the caller proceeds to close regardless;
without §5.3 wiring there is simply no buffering). Optional on a transport
(an in-memory stub may not implement it). Emitted as part of the gateway's
EXISTING drain transition — not a new idle path.

#### async def `send_follow_up(self, action: Dict[str, Any], platform: Optional[str] = None) -> Dict[str, Any]`

Act on a shared-identity capability bound to a session (A2 outbound).

Some platforms hand the connector a credential that acts on the SHARED
bot identity (e.g. a Discord interaction follow-up token, valid ~15min).
Under A2 that credential NEVER reaches the gateway — the connector
stripped it at the edge and bound it in its capability vault keyed by
the session. To use it, the gateway issues a SEMANTIC action against the
session it is already in; it never names or holds a token.

The action dict carries:
  ``op``          == ``"follow_up"``
  ``session_key`` the session whose bound capability to wield
  ``kind``        the capability kind (e.g. ``"discord.interaction_token"``)
  ``content``     the message content to send via that capability
  ``metadata?``   optional extras

The connector resolves the real capability (``resolveOutboundCapability``
on its side), enforces the tenant match (tenant B can never wield tenant
A's capability), and egresses. Returns ``{success, message_id?, error?}``;
``success`` is False when the capability is absent/expired or the tenant
doesn't match — the gateway then has nothing to retry with (by design: a
leaked gateway holds zero capability material).


## gateway.relay.ws_transport

### 模块文档

Production WebSocket RelayTransport — the gateway's live link to the connector.

The gateway dials OUT to the connector's relay endpoint over a WebSocket and
speaks the newline-delimited JSON frame protocol defined in the connector repo
(``gateway-gateway`` ``src/relay/protocol.ts``) and mirrored in
``docs/relay-connector-contract.md``:

  gateway -> connector : hello, outbound, interrupt
  connector -> gateway : descriptor, inbound, outbound_result, interrupt_inbound

Frames:
  hello            {type, platform, botId}
  descriptor       {type, descriptor}                       (handshake reply)
  inbound          {type, event, bufferId?}                 (a normalized MessageEvent)
  outbound         {type, requestId, action}                (send/edit/typing/follow_up)
  outbound_result  {type, requestId, result}
  interrupt        {type, session_key, reason?}             (gateway egresses /stop)
  interrupt_inbound{type, session_key, chat_id}             (connector -> owning gateway)

This is the concrete transport behind the ``RelayTransport`` Protocol; the
``RelayAdapter`` delegates all wire I/O to it. Outbound calls block on a
per-request future keyed by ``requestId`` until the matching ``outbound_result``
arrives. A background reader task pumps inbound frames to the registered handler
and resolves pending outbound futures.

EXPERIMENTAL: the frame schema may change without a deprecation cycle until at
least two Class-1 platforms validate it.

### class PassthroughForward

> 继承: `object` ｜ 方法数: 0（公开 0）

A connector-forwarded passthrough-plane request (Phase 5 §5.1).

The connector answered the provider's latency-critical ACK at its edge, then
forwarded the real (already-sanitized) request to this gateway over the WS.
``body`` is the exact decoded bytes the connector forwarded (the wire carries
it base64-encoded for byte parity). ``headers`` preserve arrival order.


### class WebSocketRelayTransport

> 继承: `object` ｜ 方法数: 24（公开 13）

RelayTransport over a WebSocket connection the gateway dials to the connector.

#### def `__init__(url: str, platform: str, bot_id: str, identities: Optional[list[tuple[str, str]]] = None, connect_timeout_s: float = _HANDSHAKE_TIMEOUT_S, outbound_timeout_s: float = _OUTBOUND_TIMEOUT_S, gateway_id: Optional[str] = None, upgrade_secret: Optional[str] = None, reconnect: bool = False, reconnect_backoff_s: float = 1.0, reconnect_max_backoff_s: float = 30.0) -> None`

**异常**: `RuntimeError`

#### async def `connect(self) -> bool`

#### async def `disconnect(self) -> None`

#### async def `handshake(self) -> CapabilityDescriptor`

**异常**: `RuntimeError`

#### property `auth_revoked(self) -> bool`

True once the connector closed the socket with 4401 AFTER a prior
successful handshake — i.e. the per-gateway secret was revoked (the
operator opted this instance out of the relay). Terminal: the transport
stops reconnecting, and the adapter surfaces a clean "disabled" state.

#### def `set_inbound_handler(self, handler: InboundHandler) -> None`

#### async def `send_outbound(self, action: Dict[str, Any], platform: Optional[str] = None) -> Dict[str, Any]`

#### async def `send_follow_up(self, action: Dict[str, Any], platform: Optional[str] = None) -> Dict[str, Any]`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### async def `send_interrupt(self, session_key: str, reason: Optional[str] = None) -> None`

#### async def `go_idle(self, timeout_s: float = 10.0) -> bool`

Ask the connector to flip this instance's destination to buffered-only.

Sends ``going_idle`` and awaits the connector's ``going_idle_ack`` — the
connector-AUTHORITATIVE confirmation that live delivery has stopped and
subsequent inbound buffers durably (Q-5.3c). Returns True on ack, False on
timeout / not-connected (the caller proceeds to close anyway — at worst a
live event races a closing socket exactly as before §5.3, no regression).

The gateway stays serving (the read loop keeps handling inbound) until the
ack, so an event landing in the flip window is delivered live, not lost.

#### async def `go_dormant(self, timeout_s: float = 10.0) -> bool`

Quiesce this transport for a scale-to-zero suspend (D12 / Phase 0).

Distinct from BOTH ``disconnect()`` and an unexpected close (F14):
  - ``disconnect()`` sets ``_closing=True`` and CANCELS the reconnect
    supervisor — terminal, "shutting down for good." A machine suspended
    after that never re-dials on wake, so its buffered backlog strands.
  - An unexpected close re-dials IMMEDIATELY (fast backoff) — the socket
    never stays down, so the platform proxy never sees the connection go
    away and never suspends the machine.

``go_dormant()`` is the third mode the suspend behaviour needs:
  1. ``go_idle()`` → the connector flips this instance to buffered-only
     and acks (so inbound that arrives while we sleep buffers durably and
     replays on the next handshake).
  2. Close the socket so the platform proxy sees load drop to zero (the
     precondition for Fly ``autostop:"suspend"``) — but WITHOUT setting
     ``_closing``. The reader's normal end-of-socket fall-through still
     arms the reconnect supervisor, so the wake path stays live; the
     ``_dormant`` flag just makes that supervisor poll on the dormant
     cadence rather than fight the suspend window.

On resume (process unfrozen) the supervisor's pending wait completes, the
re-dial succeeds, and the connector drains the buffered backlog on the new
handshake. Returns the ``go_idle`` ack result (True on ack); the dormancy
close happens regardless (a missed ack at worst races one live event onto
a closing socket, exactly as §5.3 already tolerates).

No-op-safe: a transport that never connected (``_ws is None``) just
returns False without closing.

#### def `set_interrupt_inbound_handler(self, handler: Any) -> None`

Register the callback for connector->gateway interrupt_inbound frames.

#### def `set_passthrough_handler(self, handler: Any) -> None`

Register the callback for connector->gateway passthrough_forward frames.

Mirrors set_interrupt_inbound_handler: the runner/adapter wires this so a
forwarded passthrough request (Phase 5 §5.1) reaches the adapter over the
same outbound WS the gateway already holds. ``handler(forward, buffer_id)``.


## gateway.response_filters

### 模块文档

Gateway response filtering helpers.

These helpers operate at the gateway boundary: they decide whether a completed
agent turn should be delivered to the chat, not what should be persisted in the
conversation history.

### 顶层函数

#### def `is_intentional_silence_response(response: Any) -> bool`

Return True only when ``response`` is exactly a silence marker.

Substantive prose that merely mentions ``NO_REPLY`` or ``[SILENT]`` must be
delivered normally.  A blank response is also not silence; blank output is
handled by the empty-response failure path.

#### def `is_intentional_silence_agent_result(agent_result: dict | None, response: Any) -> bool`

Silence markers suppress delivery only for successful agent turns.

#### def `is_partial_silence_marker(text: Any) -> bool`

Return True while ``text`` could still resolve to a silence marker.

The streaming path accumulates the reply delta-by-delta and must decide,
before the whole response is known, whether to show what it has so far.
A buffer whose canonical form is a non-empty *prefix* of a silence marker
(e.g. ``"NO"`` on the way to ``"NO_REPLY"``, or an exact marker that has
not yet been terminated by stream-end) is held back so a raw marker is
never edited onto the screen and then belatedly retracted.

Anything that has already diverged from every marker (ordinary prose) —
and anything longer than the marker cap — returns False so normal
streaming resumes immediately.  This is the streaming counterpart to
:func:`is_intentional_silence_response`, sharing the same marker set and
canonicalization so the two never drift.


## gateway.restart

### 模块文档

Shared gateway restart constants and supervisor detection helpers.

### 顶层函数

#### def `is_gateway_supervisor_process(environ: Mapping[str, str] | None = None) -> bool`

Return whether this gateway process is owned by a supervisor.

#### def `parse_restart_drain_timeout(raw: object) -> float`

Parse a configured drain timeout, falling back to the shared default.


## gateway.restart_loop_guard

### 模块文档

Auto-resume restart-loop breaker (#30719, defense-3).

Defenses 1 and 2 (the ``_HERMES_GATEWAY`` guard on ``hermes gateway
stop|restart`` + ``terminal_tool``, and the cron-creation lifecycle
filter) stop the agent from scheduling its own restart via the cron and
CLI paths.  They do NOT cover every SIGTERM source: an agent running a
raw ``terminal("launchctl kickstart -k gui/<uid>/ai.hermes.gateway")``,
an external monitor with a bad trigger, or any other repeated crash can
still drive the supervisor (launchd ``KeepAlive`` / systemd ``Restart=``)
into a tight respawn loop.  On each boot the gateway auto-resumes the
restart-interrupted session, whose next turn re-runs the offending
logic — SIGTERM every ~10 seconds until manually broken.

This module is the last-resort circuit breaker: it records a timestamp
each time the gateway boots with restart-interrupted sessions pending,
keeps a rolling window of recent boots persisted across processes (each
boot is a fresh process, so in-memory state is useless), and reports the
loop as "tripped" once too many such boots happen inside a short window.
When tripped, the caller SKIPS auto-resume for that boot — the gateway
still starts and serves real inbound messages, it just stops replaying
the session that keeps killing it, which breaks the cycle and puts a
human back in the loop.

State lives in ``<HERMES_HOME>/gateway/restart_loop.json`` so it is
profile-scoped and survives process death.  It is intentionally tiny and
best-effort: any read/write failure fails OPEN (no false trip) because a
broken breaker must never wedge a healthy gateway.

### 顶层函数

#### def `record_restart_interrupted_boot(window_seconds: int = DEFAULT_WINDOW_SECONDS, now: Optional[float] = None) -> List[float]`

Record that the gateway just booted with restart-interrupted sessions.

Prunes boots older than ``window_seconds`` and appends the current time.
Returns the pruned+appended list (most recent last).  Best-effort — a
persistence failure returns the in-memory list without raising.

#### def `is_restart_loop_tripped(max_restarts: int = DEFAULT_MAX_RESTARTS, window_seconds: int = DEFAULT_WINDOW_SECONDS, now: Optional[float] = None) -> bool`

Return True if the gateway has restarted ``>= max_restarts`` times with
restart-interrupted sessions inside the last ``window_seconds``.

Reads the persisted boot log written by
``record_restart_interrupted_boot`` and counts boots within the window.
Fails OPEN (returns False) on any error — a broken breaker must never
wedge a healthy gateway.

#### def `clear() -> None`

Remove the persisted boot log (used on clean shutdown / by tests).

#### def `check_and_record(max_restarts: int = DEFAULT_MAX_RESTARTS, window_seconds: int = DEFAULT_WINDOW_SECONDS, now: Optional[float] = None) -> bool`

Record this restart-interrupted boot and report whether the loop is now
tripped.

This is the single entry point the gateway calls: it appends the current
boot, then checks whether the (now-updated) window has reached the
threshold.  Returns True when auto-resume should be SKIPPED to break the
loop.


## gateway.rich_sent_store

### 模块文档

Local index of text we've sent via ``sendRichMessage`` (Bot API 10.1).

Telegram does NOT echo a rich message's content back in ``reply_to_message``
when a user replies to it (verified: ``.text``/``.caption`` empty,
``.api_kwargs`` None). So replies to the launchd briefings / any rich send
arrive with no quotable text and the agent is blind to what was referenced.

Fix: remember ``message_id -> text`` at send time, look it up by
``reply_to_id`` on inbound. This module is the single source of truth for that
index.

Best-effort and dependency-free: every operation swallows errors and degrades
to a no-op / ``None`` so it can never break a send or an inbound message.

### 顶层函数

#### def `record(chat_id, message_id, text: Optional[str]) -> None`

Persist ``text`` for ``(chat_id, message_id)``. No-op on any failure.

#### def `lookup(chat_id, message_id) -> Optional[str]`

Return stored text for ``(chat_id, message_id)`` or ``None``.


## gateway.run

### 模块文档

Gateway runner - entry point for messaging platform integrations.

This module provides:
- start_gateway(): Start all configured platform adapters
- GatewayRunner: Main class managing the gateway lifecycle

Usage:
    # Start the gateway
    python -m gateway.run
    
    # Or from CLI
    python cli.py --gateway

### class MultiplexConfigError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

A profile multiplexer config is invalid.

Distinct from a transient adapter-connect failure: a config error means the
operator must fix config.yaml. Fatal configuration errors propagate to the
startup guard instead of being treated as retryable adapter noise.


### class SecondaryPortBindingConfigError

> 继承: `MultiplexConfigError` ｜ 方法数: 0（公开 0）

A secondary profile conflicts with the multiplexer's shared listener.


### class GatewayRunner

> 继承: `GatewayAuthorizationMixin`、`GatewayKanbanWatchersMixin`、`GatewaySlashCommandsMixin` ｜ 方法数: 261（公开 9）

Main gateway controller.

Manages the lifecycle of all platform adapters and routes
messages to/from the agent.

#### def `__init__(config: Optional[GatewayConfig] = None)`

#### property `should_exit_cleanly(self) -> bool`

#### property `should_exit_with_failure(self) -> bool`

#### property `exit_reason(self) -> Optional[str]`

#### property `exit_code(self) -> Optional[int]`

#### def `request_restart(self, detached: bool = False, via_service: bool = False) -> bool`

#### async def `start(self) -> bool`

Start the gateway and all configured platform adapters.

Returns True if at least one adapter connected successfully.

#### async def `stop(self, restart: bool = False, detached_restart: bool = False, service_restart: bool = False) -> None`

Stop the gateway and disconnect all adapters.

#### async def `wait_for_shutdown(self) -> None`

Wait for shutdown signal.

#### property `async_session_store(self) -> AsyncSessionStore`

Return the single async facade for this runner's SessionStore.


### 顶层函数

#### def `render_notice_line(notice) -> str`

Render an AgentNotice to a single plaintext line for messaging platforms.

Messaging has no persistent status bar (unlike the TUI), so a notice is a
one-shot standalone push. The notice policy already bakes the level glyph
(⚠ / • / ✕ / ✓) into the text, and the TUI + CLI REPL render that text
verbatim — so we emit it as-is here too. Prepending a per-level glyph would
DOUBLE it ("⚠ ⚠ Credits 90% used", "⛔ ✕ Credit access paused"). Plaintext
only — no markdown — so it renders uniformly across Telegram/Discord/Slack/
SMS without per-platform escaping. Fail-soft: a malformed/empty notice
degrades to "" rather than raising on the agent's callback path.

#### def `build_resume_recovery_note(reason: Optional[str], message: str = '', interactive: bool = True) -> str`

Build the resume-pending recovery system note for an interrupted turn.

``reason`` is the session's ``resume_reason`` (``restart_timeout``,
``shutdown_timeout``, or anything else → generic interruption phrasing).
``message`` is the user's NEW message text; empty means this is the
startup auto-resume turn synthesized by
``_schedule_resume_pending_sessions`` with no human message attached.

``interactive`` selects the empty-message guidance: on interactive
platforms a human is present, so "report the restore and ask what next"
is right.  On non-interactive event platforms (webhook, API server —
adapters with ``interactive_resume = False``) nobody can answer; the
resumed turn must instead complete the interrupted work, or the task is
silently abandoned behind a "restored" acknowledgement that goes
nowhere (#57056).

#### def `load_gateway_config_for_runner() -> GatewayConfig`

Load gateway config for the process-level GatewayRunner.

When ``gateway.multiplex_profiles`` is off, this is identical to
``load_gateway_config()`` (legacy single-profile path).

When multiplexing is on, reload under the default/active profile's
``_profile_runtime_scope`` so platform tokens in that profile's ``.env``
resolve through the secret scope — the same path secondary profiles use
in ``_start_one_profile_adapters``. Without this, primary startup calls
``load_gateway_config()`` unscoped: ``_getenv`` falls through to
``os.environ``, which often has no ``TELEGRAM_BOT_TOKEN`` once the token
lives only under ``profiles/<name>/.env`` (#64674).

Single-profile gateways never set ``multiplex_profiles``, so they keep the
unscoped load and are unaffected.

#### def `start_gateway(config: Optional[GatewayConfig] = None, replace: bool = False, verbosity: Optional[int] = 0) -> bool`

Start the gateway and run until interrupted.

This is the main entry point for running the gateway.
Returns True if the gateway ran successfully, False if it failed to start.
A False return causes a non-zero exit code so systemd can auto-restart.

Args:
    config: Optional gateway configuration override.
    replace: If True, kill any existing gateway instance before starting.
             Useful for systemd services to avoid restart-loop deadlocks
             when the previous process hasn't fully exited yet.

**异常**: `SystemExit`

#### def `main()`

CLI entry point for the gateway.


## gateway.runtime_footer

### 模块文档

Gateway runtime-metadata footer.

Renders a compact footer showing runtime state (model, context %, cwd) and
appends it to the FINAL message of an agent turn when enabled.  Off by default
to keep replies minimal.

Config (``~/.hermes/config.yaml``)::

    display:
      runtime_footer:
        enabled: true                       # off by default
        fields: [model, context_pct, cwd]   # order shown; drop any to hide

Per-platform overrides live under ``display.platforms.<platform>.runtime_footer``.
Users can toggle the global setting with ``/footer on|off`` from both the CLI
and any gateway platform.

The footer is appended to the final response text in ``gateway/run.py`` right
before returning the response to the adapter send path — so it only lands on
the final message a user sees, not on tool-progress updates or streaming
partials.  When streaming is on and the final text has already been delivered
piecemeal, the footer is sent as a separate trailing message via
``send_trailing_footer()``.

### 顶层函数

#### def `resolve_footer_config(user_config: dict[str, Any] | None, platform_key: str | None = None) -> dict[str, Any]`

Resolve effective runtime-footer config for *platform_key*.

Merge order (later wins):
    1. Built-in defaults (enabled=False)
    2. ``display.runtime_footer``
    3. ``display.platforms.<platform_key>.runtime_footer``

#### def `format_runtime_footer(model: Optional[str], context_tokens: int, context_length: Optional[int], cwd: Optional[str] = None, fields: Iterable[str] = _DEFAULT_FIELDS) -> str`

Render the footer line, or return "" if no fields have data.

Fields are skipped silently when their underlying data is missing — a
partially-populated footer is better than a line with ``?%`` or empty slots.

#### def `build_footer_line(user_config: dict[str, Any] | None, platform_key: str | None, model: Optional[str], context_tokens: int, context_length: Optional[int], cwd: Optional[str] = None) -> str`

Top-level entry point used by gateway/run.py.

Returns the footer text (empty string when disabled or no data).  Callers
append this to the final response themselves, preserving a single blank
line of separation.


## gateway.scale_to_zero

### 模块文档

Scale-to-zero idle detection + dormant-quiesce for the gateway (Phase 0).

This is the gateway-side BEHAVIOUR layer that consumes the relay scale-to-zero
PRIMITIVES (gateway-gateway Phase 5: the buffered-flip, the durable per-instance
buffer, the wakeUrl poke, the reconnect supervisor). It owns the *decision* to go
idle and drives the relay transport's ``go_dormant()`` (D12) — it does NOT itself
suspend the machine. On Fly, the now-traffic-idle machine is suspended by
``autostop:"suspend"`` and woken by autostart-on-wakeUrl (decisions.md Q3=C′).

Design constraints (decisions.md):
  - Per-instance enable is gated SOLELY by the NAS "Labs" toggle, carried to the
    gateway as the ``HERMES_SCALE_TO_ZERO`` env stamp (D11/Q8=A). NOT a user
    config key; ``scale_to_zero.idle_timeout_minutes`` IS config.yaml (D2).
  - Arm only when messaging is relay-only or absent (D1/F6) AND a wakeUrl is
    registered (§3.4(1)) AND the flag is set.
  - Idle = no in-flight agent turn AND no inbound for N min AND no live
    background work (D2/D3/F7).
  - The quiesce uses ``go_dormant()`` (socket closed + supervisor preserved),
    NEVER the stop/restart drain or ``disconnect()`` (F12/F14). The process stays
    alive; Fly freezes+resumes it.
  - ``mark_resume_pending`` is deliberately NOT called here (D13 — suspend
    preserves RAM; revive only if we move to autostop:"stop" or see kills).

The pure helpers (``parse_idle_timeout_seconds``, ``scale_to_zero_enabled``,
``messaging_is_relay_only_or_absent``, ``is_idle``, ``should_arm``) take plain
inputs so they unit-test without a live gateway.

### 顶层函数

#### def `scale_to_zero_enabled(environ: Optional[dict] = None) -> bool`

Whether the per-instance Labs toggle is on (the HERMES_SCALE_TO_ZERO stamp).

D11/Q8=A: this env flag is the SOLE per-instance enable signal reaching the
gateway. Absent/blank/falsey -> disabled (fail-safe default off).

#### def `parse_idle_timeout_seconds(cfg_value: Any, default_minutes: int = DEFAULT_IDLE_TIMEOUT_MINUTES) -> float`

Coerce ``scale_to_zero.idle_timeout_minutes`` (config.yaml, D2) to seconds.

Degrades to the default on any non-numeric / non-positive value (never raises,
never returns <= 0 — a zero/negative timeout would make the gateway go dormant
instantly, which is never the intent).

#### def `messaging_is_relay_only_or_absent(platforms: Iterable[Any]) -> bool`

True iff the only connected messaging platform is RELAY, or there is none
(a Chronos-only / no-platform agent) — the F6/D1 structural precondition.

A directly-connected platform (Discord/Telegram/Slack/...) holds a live
socket and cannot scale to zero, so its presence disarms the feature. We
compare by the platform's ``.value``/name to avoid importing the enum here
(keeps this module import-light and unit-testable).

#### def `should_arm(enabled: bool, relay_only_or_absent: bool, wake_url: Optional[str]) -> bool`

Whether to start the idle watcher at all (D1/D11/§3.4(1)).

ALL must hold: the Labs flag is on, messaging is relay-only/absent, and a
wakeUrl is registered (a suspended instance with no reachable wake target is
a black hole — §3.4(1)). Any unmet -> the watcher never starts (no idle
timer, no dormancy), so a non-opted instance behaves exactly as today.

#### def `is_idle(running_agent_count: int, seconds_since_last_inbound: float, idle_timeout_seconds: float, has_live_background_work: bool) -> bool`

The idle predicate (D2/D3/F7). Pure — composes the three conjuncts.

Idle iff: no in-flight agent turn, no inbound within the timeout window, and
no live background work (backgrounded delegate_task / kanban / bg terminal).
Any active work keeps the gateway awake — suspending mid-flight would lose it.


## gateway.session

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


## gateway.session_context

### 模块文档

Session-scoped context variables for the Hermes gateway.

Replaces the previous ``os.environ``-based session state
(``HERMES_SESSION_PLATFORM``, ``HERMES_SESSION_CHAT_ID``, etc.) with
Python's ``contextvars.ContextVar``.

**Why this matters**

The gateway processes messages concurrently via ``asyncio``.  When two
messages arrive at the same time the old code did:

    os.environ["HERMES_SESSION_THREAD_ID"] = str(context.source.thread_id)

Because ``os.environ`` is *process-global*, Message A's value was
silently overwritten by Message B before Message A's agent finished
running.  Background-task notifications and tool calls therefore routed
to the wrong thread.

``contextvars.ContextVar`` values are *task-local*: each ``asyncio``
task (and any ``run_in_executor`` thread it spawns) gets its own copy,
so concurrent messages never interfere.

**Backward compatibility**

The public helper ``get_session_env(name, default="")`` mirrors the old
``os.getenv("HERMES_SESSION_*", ...)`` calls.  Existing tool code only
needs to replace the import + call site:

    # before
    import os
    platform = os.getenv("HERMES_SESSION_PLATFORM", "")

    # after
    from gateway.session_context import get_session_env
    platform = get_session_env("HERMES_SESSION_PLATFORM", "")

### 顶层函数

#### def `session_context_engaged() -> bool`

True if any session has been bound via set_session_vars in this process.

See the ``_session_context_engaged`` comment for the leak-policy rationale.

#### def `set_current_session_id(session_id: str) -> None`

Synchronize ``HERMES_SESSION_ID`` across ContextVar and ``os.environ``.

Long-lived single-process entrypoints like the CLI can rotate sessions via
``/new``, ``/resume``, ``/branch``, or compression splits without
reconstructing the entire agent. Tools still consult
``get_session_env("HERMES_SESSION_ID")`` with an ``os.environ`` fallback,
so both storage paths must move together when the active session changes.

#### def `set_session_vars(platform: str = '', source: str = '', chat_id: str = '', chat_name: str = '', thread_id: str = '', user_id: str = '', user_name: str = '', session_key: str = '', session_id: str = '', message_id: str = '', profile: str = '', cwd: str = '', async_delivery: bool = True, ui_session_id: str = '') -> list`

Set all session context variables and return reset tokens.

Call ``clear_session_vars(tokens)`` in a ``finally`` block when the handler
exits. Note ``clear_session_vars`` resets every var to ``""`` (to suppress
the ``os.environ`` fallback) rather than restoring prior values — these
helpers are not nestable/stack-safe, and the returned tokens are accepted
only for API compatibility.

``cwd`` pins the logical working directory for this context.

``async_delivery`` declares whether this session's channel can route a
background completion back to the agent after the turn ends (see
``_SESSION_ASYNC_DELIVERY`` / ``async_delivery_supported``). Stateless
request/response adapters (the API server) pass ``False``.

#### def `clear_session_vars(tokens: list) -> None`

Mark session context variables as explicitly cleared.

Sets all variables to ``""`` so that ``get_session_env`` returns an empty
string instead of falling back to (potentially stale) ``os.environ``
values.  The *tokens* argument is accepted for API compatibility with
callers that saved the return value of ``set_session_vars``, but the
actual clearing uses ``var.set("")`` rather than ``var.reset(token)``
to ensure the "explicitly cleared" state is distinguishable from
"never set" (which holds the ``_UNSET`` sentinel).

#### def `reset_session_vars() -> None`

Reset every session context variable to ``_UNSET`` for THIS context.

Distinct from :func:`clear_session_vars`, which sets the vars to ``""``
("explicitly cleared" — suppresses the os.environ fallback and is used when
a handler *finishes*).  This helper restores the ``_UNSET`` sentinel
("never bound in this context"), which is what a freshly-spawned task should
look like *before* it binds its own session.

🔴 Why this exists — the cross-session ContextVar inheritance leak.
Each gateway message is processed in its own ``asyncio`` task, created via
``create_task`` (which snapshots the *current* context with
``copy_context``).  When message B's task is spawned from a context where a
concurrent message A had already called :func:`set_session_vars`, B inherits
A's **set** ContextVars.  Until B calls its own ``set_session_vars`` there is
a window where any subprocess B spawns (e.g. a tool shelling out) reads
*A's* ``HERMES_SESSION_*`` identity via the subprocess-env bridge.  The
bridge's ``_UNSET``-strip guard cannot help: the vars are not ``_UNSET``,
they are set-to-A.  Calling ``reset_session_vars`` at the top of the
per-message handler drops the inherited identity so the window strips safe
(no session) instead of leaking the foreign one; the handler then binds its
own via ``set_session_vars`` a few steps later.  See
tests/tools/test_local_env_session_leak.py and
tests/gateway/test_session_context_inheritance.py.

Note ``_SESSION_ASYNC_DELIVERY`` lives outside ``_VAR_MAP`` (it is a bool
capability flag read via :func:`async_delivery_supported`, not a string
``HERMES_SESSION_*`` env var read via :func:`get_session_env`), so it is
reset explicitly below. Without it, a task spawned from a context where a
sibling adapter bound ``async_delivery=False`` (the stateless API server)
inherits that ``False`` through the pre-bind window, and
``async_delivery_supported`` wrongly reports the new turn's channel as
unable to route a background completion until ``set_session_vars`` runs.

#### def `get_session_env(name: str, default: str = '') -> str`

Read a session context variable by its legacy ``HERMES_SESSION_*`` name.

Drop-in replacement for ``os.getenv("HERMES_SESSION_*", default)``.

Resolution order:
1. Context variable (set by the gateway for concurrency-safe access).
   If the variable was explicitly set (even to ``""``) via
   ``set_session_vars`` or ``clear_session_vars``, that value is
   returned — **no fallback to os.environ**.
2. ``os.environ`` (only when the context variable was never set in
   this context — i.e. CLI, cron scheduler, and test processes that
   don't use ``set_session_vars`` at all).
3. *default*

#### def `declare_stateless_channel() -> None`

Declare that this session cannot receive an async background completion.

Binds only the delivery capability, leaving every other session var unset.
Use this instead of ``set_session_vars(async_delivery=False)`` on a pure
single-process runner: ``set_session_vars`` also latches
``_session_context_engaged`` (see above), which switches the subprocess
env bridge from "os.environ fallback" to "ContextVar-authoritative, strip on
_UNSET" in ``tools/environments/local.py``. A one-shot CLI that never engages
the session-context system must not flip that latch as a side effect of
declaring a capability.

Callers that already build a full session context (cron's ``run_job``) get
the same state by passing ``async_delivery=False`` to ``set_session_vars``.

A session that cannot take a late completion makes ``delegate_task`` fall
through to its existing inline/synchronous path, so subagent results are
returned within the turn instead of being dispatched to a channel that will
never deliver them.

See NousResearch/hermes-agent#53027 and #63142.

#### def `async_delivery_supported() -> bool`

Whether the current session can deliver a background completion later.

Returns ``False`` when the active session was bound by a stateless channel:
an adapter that cannot route a notification back after the turn ends (the
API server), or a one-shot runner that exits after its final response
(``hermes -z``, cron — see :func:`declare_stateless_channel`). The real
gateway platforms, the interactive CLI, and any path that never bound the
contextvar return ``True``.

Tools that promise async delivery (``terminal`` notify_on_complete /
watch_patterns, ``delegate_task`` background=True) consult this before
registering a watcher / dispatching a detached child, so they can refuse a
promise the channel can't keep instead of silently no-op'ing.


## gateway.shutdown_forensics

### 模块文档

Shutdown forensics — capture context when the gateway receives SIGTERM/SIGINT.

The gateway's ``shutdown_signal_handler`` runs synchronously inside the
asyncio event loop.  We can't safely block it for long, but we DO want a
durable record of who/what triggered the shutdown so that "the gateway
keeps dying" incidents can be diagnosed after the fact.

This module exposes :func:`snapshot_shutdown_context`, a fast (<10ms),
non-blocking probe that returns a structured dict the signal handler can
log immediately, plus :func:`spawn_async_diagnostic`, a fire-and-forget
``ps`` walk that runs as a detached subprocess so it can't block teardown
even if /proc is wedged.

Anything that needs to wait (e.g. shelling out to ``ps aux``) belongs in
the async helper, never in the synchronous probe.

### 顶层函数

#### def `snapshot_shutdown_context(received_signal: Any = None) -> Dict[str, Any]`

Fast (<10ms) snapshot of who/what is asking us to shut down.

Captures:

* The signal number/name (so SIGINT vs SIGTERM is visible)
* Our own PID/ppid + parent process info from /proc (Linux)
* Whether systemd is our parent (``ppid==1`` or ``INVOCATION_ID`` set)
* Whether takeover/planned-stop markers exist (consumed lazily by the caller)
* /proc/self limits + load average (1-min)
* Wall-clock and monotonic timestamps for cross-correlating later phases

Pure stdlib, never raises, never blocks on subprocesses.

#### def `spawn_async_diagnostic(log_path: Path, signal_name: str, timeout_seconds: float = 5.0) -> Optional[int]`

Fire-and-forget ``ps``-style snapshot written to ``log_path``.

Runs as a detached subprocess so it can't block the asyncio event loop
or compete with platform teardown.  The subprocess uses its own
``timeout`` so a wedged ``ps`` still self-cleans within
``timeout_seconds``.

Returns the subprocess PID on success, ``None`` on failure.  Never
raises.

We deliberately avoid ``subprocess.run(["ps", "aux"])`` from inside the
signal handler (the pre-existing pattern): on a busy host with hundreds
of processes, ``ps aux`` can take >2s to walk /proc, during which the
asyncio loop is frozen and adapter teardown can't begin.

#### def `format_context_for_log(ctx: Dict[str, Any]) -> str`

Render a shutdown context dict as a single, scannable log line.

#### def `context_as_json(ctx: Dict[str, Any]) -> str`

JSON-serialise a context dict for structured ingestion.  Never raises.

#### def `check_systemd_timing_alignment(drain_timeout: float) -> Optional[Dict[str, Any]]`

At startup, sanity-check that systemd's TimeoutStopSec >= drain_timeout.

When the gateway is run under a stale systemd unit file (e.g. the user
upgraded hermes-agent but never re-ran ``hermes setup`` to regenerate
the unit), ``TimeoutStopSec`` can be smaller than the configured
``restart_drain_timeout``.  Result: SIGTERM arrives, the drain starts,
and systemd SIGKILLs the cgroup mid-drain — looks like a phantom kill
in the journal because the journal only logs ``code=killed status=9``.

Returns ``None`` when the alignment is fine OR we can't determine it
(not running under systemd, ``systemctl`` unavailable, etc.).  Returns
a dict with ``timeout_stop_sec`` + ``drain_timeout`` + ``mismatch``
bool when we have data to report.

Best-effort.  Never raises.


## gateway.shutdown_watchdog

### 模块文档

Out-of-loop shutdown backstop + event-loop liveness heartbeat (#66892).

When the asyncio loop freezes mid-drain, every asyncio-based recovery path is
structurally unable to fire: the drain deadline, status rewrites, and forensics
all need the same loop that is stuck. launchd/systemd KeepAlive only restarts a
*dead* process, so a wedged-but-alive gateway sits as a zombie until manual
SIGKILL.

This module provides:

1. A plain OS-thread shutdown watchdog armed at ``stop()``. If shutdown has not
   completed within ``restart_drain_timeout + grace``, it dumps all-thread
   stacks via ``faulthandler`` plus a metadata snapshot, then ``os._exit`` so
   the service manager can revive the process.
2. An event-loop heartbeat file at ``<HERMES_HOME>/state/gateway.heartbeat`` so
   external supervision can distinguish "process alive" from "loop frozen"
   (``gateway_state.json`` alone can't — it only rewrites on transitions/turns).

### 顶层函数

#### def `get_loop_heartbeat_path(home: Optional[Path] = None) -> Path`

Return ``<HERMES_HOME>/state/gateway.heartbeat``.

#### def `get_shutdown_watchdog_dump_path(home: Optional[Path] = None) -> Path`

Return the faulthandler / metadata dump path for a fired watchdog.

#### def `write_loop_heartbeat(pid: Optional[int] = None, start_time: Optional[float] = None, home: Optional[Path] = None, extra: Optional[Dict[str, Any]] = None) -> Path`

Atomically rewrite the loop-liveness heartbeat file.

``start_time`` is the gateway process start (``time.time()`` epoch seconds)
so supervisors can detect PID reuse. Best-effort — never raises.

#### def `resolve_shutdown_watchdog_delay(drain_timeout: float, grace_s: float = DEFAULT_SHUTDOWN_WATCHDOG_GRACE_S) -> float`

Return the wall-clock leash for the shutdown watchdog thread.

#### def `arm_shutdown_watchdog(delay_s: float, done_event: Optional[threading.Event] = None, snapshot_fn: Optional[Callable[[], Dict[str, Any]]] = None, exit_code: int = 1, dump_path: Optional[Path] = None, name: str = 'gateway-shutdown-watchdog') -> threading.Event`

Arm a daemon-thread hard-exit backstop for a wedged shutdown path.

If ``done_event`` is set before ``delay_s`` elapses, the thread exits
quietly (normal / progressing shutdown completed). Otherwise it dumps
diagnostics and calls ``os._exit(exit_code)``.

Never raises. Returns the ``done_event`` (creating one when omitted) so
the caller can disarm on successful completion.

#### def `loop_heartbeat_forever(interval_s: float = DEFAULT_HEARTBEAT_INTERVAL_S, start_time: Optional[float] = None, home: Optional[Path] = None, should_continue: Optional[Callable[[], bool]] = None) -> None`

Rewrite the loop heartbeat file on a cadence until cancelled / gated off.

Runs as an asyncio task on the gateway loop — if the loop freezes, this
task stops and the file mtime/updated_at goes stale for external monitors.


## gateway.slash_access

### 模块文档

Per-platform slash command access control.

This module sits beside the existing per-platform allowlist (``allow_from``)
and adds a second axis: of the users who are *allowed to talk to the
gateway*, which ones can run *which slash commands*.

Two lists per platform scope (DM vs group, mirroring ``allow_from`` vs
``group_allow_from``):

  - ``allow_admin_from``      — user IDs that get every registered slash
                                command (built-in + plugin-registered).
  - ``user_allowed_commands`` — slash command names non-admin users may
                                run. Empty / unset → non-admins get no
                                slash commands.

Backward compatibility:

  If ``allow_admin_from`` is not set for a scope, slash command gating
  is disabled entirely for that scope. Every allowed user can run every
  slash command, exactly like before. This means existing installs are
  unaffected until an operator opts in by listing at least one admin.

The gate is applied at the slash command dispatch site in
``gateway/run.py`` so it covers BOTH built-in and plugin-registered
commands via the live registry. Gating slash commands does not affect
plain chat — non-admin users can still talk to the agent normally,
they just can't trigger commands outside ``user_allowed_commands``.

Authored as a slimmed-down salvage of PR #4443's permission tiers
(co-authored by @ReqX). The full tier system, audit log, usage
tracking, rate limiting, and tool filtering from that PR are not
included here — only the slash-command access split.

### class SlashAccessPolicy

> 继承: `object` ｜ 方法数: 2（公开 2）

Resolved access policy for a single (platform, scope) pair.

``scope`` is ``"dm"`` for direct messages and ``"group"`` for groups,
channels, threads, and any other multi-user context. The mapping from
SessionSource.chat_type → scope happens in ``policy_for_source``.

#### def `is_admin(self, user_id: Optional[str]) -> bool`

#### def `can_run(self, user_id: Optional[str], canonical_cmd: str) -> bool`


### 顶层函数

#### def `policy_from_extra(extra: dict, scope: str) -> SlashAccessPolicy`

Build a policy from a platform's ``extra`` dict for one scope.

DM scope falls back to group scope keys ONLY for ``user_allowed_commands``
when the DM scope didn't specify its own. This keeps the common case
(operator wants the same command set DM and group) ergonomic without
forcing duplication. Admin lists are NOT cross-scope: an admin in
DMs is not implicitly an admin in a group.

#### def `policy_for_source(gateway_config: Any, source: Any) -> SlashAccessPolicy`

Resolve the access policy for a SessionSource.

Returns a "disabled" policy (gating off, allow everything) when:
  - gateway_config is None
  - the platform has no PlatformConfig
  - the platform's PlatformConfig has no admin list set for the scope

Callers should treat the returned policy as authoritative for slash
command gating only. It does not gate plain chat messages.


## gateway.slash_commands

### 模块文档

Gateway slash-command handlers for GatewayRunner.

Extracted from ``gateway/run.py`` (god-file decomposition Phase 3b). These are
the in-session slash commands (/model, /reset, /usage, /compress, ...) the
gateway dispatches from ``_handle_message``. There are 42 of them (~3,200 LOC);
lifting them into a mixin that ``GatewayRunner`` inherits keeps every
``self._handle_*_command`` dispatch + test reference working via the MRO, while
removing the bulk from run.py.

Module-level run.py helpers a handler needs (``_hermes_home``,
``_load_gateway_config``, ``_resolve_gateway_model``, etc.) are imported lazily
inside the handler body — a deferred ``from gateway.run import ...`` resolves at
call time (run.py fully loaded by then), avoiding an import cycle.

### class GatewaySlashCommandsMixin

> 继承: `object` ｜ 方法数: 59（公开 0）

In-session slash-command handlers for GatewayRunner.


## gateway.status

### 模块文档

Gateway runtime status helpers.

Provides PID-file based detection of whether the gateway daemon is running,
used by send_message's check_fn to gate availability in the CLI.

The PID file lives at ``{HERMES_HOME}/gateway.pid``.  HERMES_HOME defaults to
``~/.hermes`` but can be overridden via the environment variable.  This means
separate HERMES_HOME directories naturally get separate PID files — a property
that will be useful when we add named profiles (multiple agents running
concurrently under distinct configurations).

### class StormInfo

> 继承: `NamedTuple` ｜ 方法数: 0（公开 0）

Result of a respawn-storm check: how many starts, over what window, and
the backoff the caller should sleep to break the storm.


### 顶层函数

#### def `record_start_and_check_storm(max_starts: int = 5, window_s: float = 120.0, backoff_cap_s: float = 300.0) -> Optional[StormInfo]`

Record this gateway start and report whether a respawn storm is underway.

Appends the current UTC timestamp to the starts-log, prunes entries older
than ``window_s``, and ring-buffers the file so it can't grow unbounded.
Returns a :class:`StormInfo` when more than ``max_starts`` starts landed in
the window (with an exponential backoff capped at ``backoff_cap_s``), else
``None``.

Best-effort: any bookkeeping failure is logged and swallowed so a broken
ledger can never crash gateway startup.

#### def `terminate_pid(pid: int, force: bool = False) -> None`

Terminate a PID with platform-appropriate force semantics.

POSIX uses SIGTERM/SIGKILL. Windows uses taskkill /T /F for true force-kill
because os.kill(..., SIGTERM) is not equivalent to a tree-killing hard stop.

**异常**: `OSError`

#### def `get_process_start_time(pid: int) -> Optional[int]`

Public wrapper for retrieving a process start time when available.

#### def `looks_like_gateway_command_line(command: str | None) -> bool`

Return True only for a real ``gateway run`` process command line.

#### def `looks_like_gateway_runtime_command_line(command: str | None) -> bool`

Return True for command lines that can host the gateway runtime.

``gateway restart`` is normally a management command, not the gateway
runtime. On hosts without a service manager, though, the manual restart
fallback executes ``run_gateway()`` in that same process, so its argv stays
as ``gateway restart`` while it owns the webhook port and writes runtime
state. Keep the public ``looks_like_gateway_command_line()`` strict, and
use this broader matcher only when validating Hermes-owned runtime records
or no-supervisor cleanup scans.

#### def `acquire_gateway_runtime_lock() -> bool`

Claim the cross-process runtime lock for the gateway.

Unlike the PID file, the lock is owned by the live process itself. If the
process dies abruptly, the OS releases the lock automatically.

#### def `release_gateway_runtime_lock() -> None`

Release the gateway runtime lock when owned by this process.

#### def `is_gateway_runtime_lock_active(lock_path: Optional[Path] = None) -> bool`

Return True when some process currently owns the gateway runtime lock.

#### def `write_pid_file() -> None`

Write the current process PID and metadata to the gateway PID file.

Uses atomic O_CREAT | O_EXCL creation so that concurrent --replace
invocations race: exactly one process wins and the rest get
FileExistsError.

#### def `write_runtime_status(gateway_state: Any = _UNSET, exit_reason: Any = _UNSET, restart_requested: Any = _UNSET, active_agents: Any = _UNSET, platform: Any = _UNSET, platform_state: Any = _UNSET, error_code: Any = _UNSET, error_message: Any = _UNSET, served_profiles: Any = _UNSET) -> None`

Persist gateway runtime health information for diagnostics/status.

#### def `read_runtime_status(path: Optional[Path] = None) -> Optional[dict[str, Any]]`

Read the persisted gateway runtime health/status information.

``path`` is optional so callers that need to inspect a *different*
profile's state file (e.g. the dashboard enumerating every profile)
can do so without mutating ``HERMES_HOME`` in-process.  Defaults to
the active profile's ``gateway_state.json``.

#### def `parse_active_agents(raw: Any) -> int`

Coerce a persisted ``active_agents`` value to a clamped non-negative int.

The shared coercion for the in-flight gateway-turn count. Used on the WRITE
side (``write_runtime_status``) and by both HTTP read surfaces
(``/api/status`` and ``/health/detailed``) so the count is clamped to a
single contract — never negative, never raising on a manually-edited or
otherwise non-numeric value (degrades to ``0``).

#### def `derive_gateway_busy(gateway_running: bool, gateway_state: Any, active_agents: Any) -> bool`

Whether the gateway is actively processing in-flight turns.

The contract NAS gates lifecycle actions on.  Busy iff the gateway is live
(``gateway_running``), in the ``running`` state, AND at least one agent is
mid-turn (``active_agents > 0``).  Degrades to ``False`` whenever liveness
is unknown, the state is anything but ``running``, or the count is
absent/unparseable — i.e. a down or file-absent gateway reads "not busy",
never a spurious "busy".

NOTE: liveness keys off ``gateway_running`` (a live PID / health probe),
NEVER ``updated_at`` — a healthy idle gateway never advances that timestamp.

#### def `derive_gateway_drainable(gateway_running: bool, gateway_state: Any) -> bool`

Whether the gateway can accept a begin-drain request right now.

True iff the gateway is live and in the ``running`` state — i.e. not already
draining/stopping/stopped and not in a failed-start state.  This is
independent of ``active_agents``: an idle running gateway is drainable (the
drain just completes immediately).  Degrades to ``False`` for a down or
non-running gateway.

#### def `get_runtime_status_running_pid(runtime: Optional[dict[str, Any]] = None, expected_home: Optional[Path] = None) -> Optional[int]`

Return a live gateway PID from the runtime status record, if valid.

``get_running_pid()`` is the primary liveness source because it verifies the
runtime lock and PID file.  Launch-service managers can still leave us with
a live process and a fresh ``gateway_state.json`` but no ``gateway.pid``; use
this as a conservative fallback by checking both the persisted state and the
OS process identity.

``expected_home`` scopes the OS-identity check to a specific profile's
HERMES_HOME.  Pass it when validating *another* profile's state file (the
dashboard enumerating every profile): a stale record whose PID the OS has
recycled onto a different profile's live gateway must not be reported
running for the dead profile.  Omit it (the default) for the active
profile, where any live gateway command line is acceptable.

#### def `remove_pid_file() -> None`

Remove the gateway PID file, but only if it belongs to this process.

During --replace handoffs, the old process's atexit handler can fire AFTER
the new process has written its own PID file.  Blindly removing the file
would delete the new process's record, leaving the gateway running with no
PID file (invisible to ``get_running_pid()``).

#### def `acquire_scoped_lock(scope: str, identity: str, metadata: Optional[dict[str, Any]] = None) -> tuple[bool, Optional[dict[str, Any]]]`

Acquire a machine-local lock keyed by scope + identity.

Used to prevent multiple local gateways from using the same external identity
at once (e.g. the same Telegram bot token across different HERMES_HOME dirs).

#### def `release_scoped_lock(scope: str, identity: str) -> None`

Release a previously-acquired scope lock when owned by this process.

#### def `release_all_scoped_locks(owner_pid: Optional[int] = None, owner_start_time: Optional[int] = None) -> int`

Remove scoped lock files in the lock directory.

Called during --replace to clean up stale locks left by stopped/killed
gateway processes that did not release their locks gracefully. When an
``owner_pid`` is provided, only lock records belonging to that gateway
process are removed. ``owner_start_time`` further narrows the match to
protect against PID reuse.

When no owner is provided, preserves the legacy behavior and removes every
scoped lock file in the directory.

Returns the number of lock files removed.

#### def `write_takeover_marker(target_pid: int) -> bool`

Record that ``target_pid`` is being replaced by the current process.

Captures the target's ``start_time`` so that PID reuse after the
target exits cannot later match the marker. Also records the
replacer's PID and a UTC timestamp for TTL-based staleness checks.

Returns True on successful write, False on any failure. The caller
should proceed with the SIGTERM even if the write fails (the marker
is a best-effort signal, not a correctness requirement).

#### def `consume_takeover_marker_for_self() -> bool`

Check & unlink the takeover marker if it names the current process.

Returns True only when a valid (non-stale) marker names this PID +
start_time. A returning True indicates the current SIGTERM is a
planned --replace takeover; the caller should exit 0 instead of
signalling ``_signal_initiated_shutdown``.

Always unlinks the marker on match (and on detected staleness) so
subsequent unrelated signals don't re-trigger.

#### def `clear_takeover_marker() -> None`

Remove the takeover marker unconditionally. Safe to call repeatedly.

#### def `write_planned_stop_marker(target_pid: int) -> bool`

Record that ``target_pid`` is being stopped intentionally.

The gateway exits non-zero for unexpected SIGTERM so service managers can
revive it. Service stop commands send the same SIGTERM, so the CLI writes
this short-lived marker first to let the target process exit cleanly.

#### def `consume_planned_stop_marker_for_self() -> bool`

Return True when the current process is being intentionally stopped.

#### def `planned_stop_marker_targets_self() -> bool`

Return True only when a live planned-stop marker names the current process.

This is a **non-destructive** probe used by the watcher thread
(``gateway/run.py:_run_planned_stop_watcher``) to decide whether to
trigger shutdown. Unlike :func:`consume_planned_stop_marker_for_self`,
it never unlinks a marker that matches us — the shutdown handler does
the authoritative consume on its own thread.

It *does* clean up markers that can never apply to this process:
malformed markers and markers older than the TTL are unlinked so a
stale file left behind by a previous gateway instance cannot wedge
the new one. Markers naming a different PID/start_time are left in
place (they may still be consumed legitimately by the process they
name) but report False here.

Returns False (without raising) on any read/parse error.

#### def `clear_planned_stop_marker() -> None`

Remove the planned-stop marker unconditionally.

#### def `get_running_pid(pid_path: Optional[Path] = None, cleanup_stale: bool = True) -> Optional[int]`

Return the PID of a running gateway instance, or ``None``.

Checks the PID file and verifies the process is actually alive.
Cleans up stale PID files automatically.

#### def `get_running_pid_cached(pid_path: Optional[Path] = None, cleanup_stale: bool = True, ttl_seconds: float = _GATEWAY_RUNNING_PID_CACHE_TTL_SECONDS) -> Optional[int]`

Cached read-side wrapper for dashboard/status polling.

``get_running_pid()`` probes the runtime lock by briefly opening and locking
``gateway.lock``. That is the right authoritative check for control paths,
but high-frequency read-only HTTP polling can call it hundreds of times per
minute. Cache for a short window and invalidate on PID/lock/runtime-status
file changes so status endpoints do not churn file descriptors while still
noticing gateway start/stop transitions quickly.

#### def `is_gateway_running(pid_path: Optional[Path] = None, cleanup_stale: bool = True) -> bool`

Check if the gateway daemon is currently running.


## gateway.status_phrases

### 模块文档

Human-friendly generic gateway status phrases.

These helpers deliberately avoid relaying raw model scratch text.  They turn
Hermes' long-running gateway status surface into short status lines suitable
for chat surfaces.

Built-in defaults live in ``gateway/assets/status_phrases.yaml``. Users can add
portable, profile-relative phrase catalogs under ``HERMES_HOME`` either by using
conventional paths::

    ~/.hermes/status_phrases.yaml
    ~/.hermes/status_phrases/*.yaml

or by pointing config at a relative file/directory::

    display:
      status_phrases:
        path: status_phrases/whatsapp.yaml  # relative to HERMES_HOME
        mode: append                        # append (default) or replace

Absolute paths and ``..`` escapes are ignored on purpose so config stays
profile-portable and does not accidentally read arbitrary files.

Only configured phrase strings are used; raw tool args, commands, previews, and
reasoning text are never interpolated into the returned phrase.

### 顶层函数

#### def `resolve_status_phrase_catalog(user_config: Mapping[str, Any] | None, platform_key: str | None = None) -> dict[str, list[str]]`

Resolve built-in + user-configured generic status phrases.

Resolution order mirrors gateway display settings: built-ins, conventional
profile-relative user files, global ``display.status_phrases`` (or legacy
alias ``generic_status_phrases``), then
``display.platforms.<platform>.status_phrases``.

#### def `classify_status_context(kind: str, tool_name: str | None = None, preview: str | None = None, args: Any = None) -> str`

Classify an internal gateway event into a Hermes UI-surface bucket.

#### def `choose_status_phrase(kind: str, tool_name: str | None = None, preview: str | None = None, args: Any = None, recent: MutableSequence[str] | None = None, rng: Any = None, catalog: Mapping[str, list[str]] | None = None) -> str`

Pick a short generic status phrase, avoiding recent repeats.

``preview`` and ``args`` are accepted for callback compatibility, but their
raw contents are never embedded in the returned phrase.


## gateway.sticker_cache

### 模块文档

Sticker description cache for Telegram.

When users send stickers, we describe them via the vision tool and cache
the descriptions keyed by file_unique_id so we don't re-analyze the same
sticker image on every send. Descriptions are concise (1-2 sentences).

Cache location: ~/.hermes/sticker_cache.json

### 顶层函数

#### def `get_cached_description(file_unique_id: str) -> Optional[dict]`

Look up a cached sticker description.

Returns:
    dict with keys {description, emoji, set_name, cached_at} or None.

#### def `cache_sticker_description(file_unique_id: str, description: str, emoji: str = '', set_name: str = '') -> None`

Store a sticker description in the cache.

Args:
    file_unique_id: Telegram's stable sticker identifier.
    description:    Vision-generated description text.
    emoji:          Associated emoji (e.g. "😀").
    set_name:       Sticker set name if available.

#### def `build_sticker_injection(description: str, emoji: str = '', set_name: str = '') -> str`

Build the warm-style injection text for a sticker description.

Returns a string like:
  [The user sent a sticker 😀 from "MyPack"~ It shows: "A cat waving" (=^.w.^=)]

#### def `build_animated_sticker_injection(emoji: str = '') -> str`

Build injection text for animated/video stickers we can't analyze.


## gateway.stream_consumer

### 模块文档

Gateway streaming consumer — bridges sync agent callbacks to async platform delivery.

The agent fires stream_delta_callback(text) synchronously from its worker thread.
GatewayStreamConsumer:
  1. Receives deltas via on_delta() (thread-safe, sync)
  2. Queues them to an asyncio task via queue.Queue
  3. The async run() task buffers, rate-limits, and progressively edits
     a single message on the target platform

Design: Uses the edit transport (send initial message, then editMessageText).
This is universally supported across Telegram, Discord, and Slack.

Credit: jobless0x (#774, #1312), OutThisLife (#798), clicksingh (#697).

### class StreamConsumerConfig

> 继承: `object` ｜ 方法数: 0（公开 0）

Runtime config for a single stream consumer instance.


### class GatewayStreamConsumer

> 继承: `object` ｜ 方法数: 42（公开 10）

Async consumer that progressively edits a platform message with streamed tokens.

Usage::

    consumer = GatewayStreamConsumer(adapter, chat_id, config, metadata=metadata)
    # Pass consumer.on_delta as stream_delta_callback to AIAgent
    agent = AIAgent(..., stream_delta_callback=consumer.on_delta)
    # Start the consumer as an asyncio task
    task = asyncio.create_task(consumer.run())
    # ... run agent in thread pool ...
    consumer.finish()  # signal completion
    await task         # wait for final edit

#### def `__init__(adapter: Any, chat_id: str, config: Optional[StreamConsumerConfig] = None, metadata: Optional[dict] = None, on_new_message: Optional[callable] = None, on_before_finalize: Optional[Callable[[], Any]] = None, initial_reply_to_id: Optional[str] = None, run_still_current: Optional[Callable[[], bool]] = None)`

#### property `already_sent(self) -> bool`

True if at least one message was sent or edited during the run.

#### property `final_response_sent(self) -> bool`

True when the stream consumer delivered the final assistant reply.

#### property `message_id(self) -> str | None`

The Discord/chat message ID of the last-sent or edited message.

#### property `final_content_delivered(self) -> bool`

True when the final response content reached the user, even if
the subsequent cosmetic edit (cursor removal) failed.

#### def `has_delivered_text(self, text: str) -> bool`

Return True if *text* was already delivered as visible chat content.

#### def `on_segment_break(self) -> None`

Finalize the current stream segment and start a fresh message.

#### def `on_commentary(self, text: str) -> None`

Queue a completed interim assistant commentary message.

#### def `on_delta(self, text: str) -> None`

Thread-safe callback — called from the agent's worker thread.

When *text* is ``None``, signals a tool boundary: the current message
is finalized and subsequent text will be sent as a new message so it
appears below any tool-progress messages the gateway sent in between.

#### def `finish(self) -> None`

Signal that the stream is complete.

#### async def `run(self) -> None`

Async task that drains the queue and edits the platform message.


## gateway.stream_dispatch

### 模块文档

Adapter-driven dispatch of structured stream events to a delivery sink.

``GatewayEventDispatcher`` is the seam Tobi asked for: the agent emits typed
events (gateway/stream_events.py), and the *adapter* decides how each one is
delivered.  The dispatcher holds an adapter + the stream consumer (sink) + the
resolved per-channel presentation settings (tool-progress mode, preview length)
and routes each event through the adapter's render hooks.

Message/commentary/segment events flow into the consumer (native draft on
Telegram DMs, edit-in-place elsewhere).  Tool events are formatted by the
adapter — which may return None to *eat* the event on platforms that can't
render tool chrome — and the rendered line is enqueued onto the same tool
progress queue the gateway already drains, so the two no longer race through
independent code paths.

This module deliberately has no platform knowledge and no asyncio: it is a thin
synchronous router callable from the agent's worker thread, exactly like the
callbacks it replaces.

### class GatewayEventDispatcher

> 继承: `object` ｜ 方法数: 3（公开 1）

Route typed stream events through an adapter onto a delivery sink.

Parameters
----------
adapter:
    The platform adapter.  Provides ``render_message_event`` and
    ``format_tool_event`` (BasePlatformAdapter defaults reproduce today's
    behavior; adapters may override for native rendering).
sink:
    The GatewayStreamConsumer for assistant-text delivery.  May be None
    when streaming is disabled, in which case message events are dropped
    (the final response still goes out via the normal send path).
enqueue_tool_line:
    Callback that places a rendered tool-progress line onto the gateway's
    progress queue (the same queue ``send_progress_messages`` drains).  May
    be None when tool progress is disabled for this channel.
tool_mode:
    Resolved tool-progress mode for this channel ("all" / "new" / "verbose"
    / "off").
preview_max_len:
    Resolved ``tool_preview_length`` (0 = no cap in verbose mode).
on_long_tool / on_notice:
    Optional hooks for LongToolHint / GatewayNotice events, letting the
    gateway own the "should I surface this here?" decision.

#### def `__init__(adapter: Any, sink: Any = None, enqueue_tool_line: Optional[Callable[[Any], None]] = None, tool_mode: str = 'all', preview_max_len: int = 40, on_long_tool: Optional[Callable[[LongToolHint], None]] = None, on_notice: Optional[Callable[[GatewayNotice], None]] = None) -> None`

#### def `dispatch(self, event: StreamEvent) -> None`

Route a single event.  Never raises into the agent's worker thread.


## gateway.stream_events

### 模块文档

Structured streaming events — the agent→gateway delivery contract.

Historically the agent drove gateway delivery through a fan of loosely-typed
callbacks (``stream_delta_callback(text)``, ``tool_progress_callback(event_type,
tool_name, preview, args)``, ``interim_assistant_callback(text)`` …) and each
gateway callback decided *both* what to render and how to send it.  That
coupling is why tool-progress bubbles and the streaming draft raced each other
on Telegram, and why tool-call formatting lived agent-side even though only the
gateway knows what a given platform can render.

This module defines a small, typed event vocabulary that names *what happened*
without prescribing *how it is delivered*.  The gateway's stream consumer
(``GatewayStreamConsumer``) is the single sink; the platform adapter decides how
to render each event (Telegram can stream a MarkdownV2 ```bash``` block as a
native draft; iMessage has no rich formatting and may collapse or drop tool
chrome).  Separation of concerns: smart agent emits structured data, smart
gateway decides delivery.

These are intentionally plain frozen dataclasses — no behavior, no platform
knowledge, no I/O.  They are cheap to construct on the agent's worker thread and
safe to hand across the thread/async boundary into the consumer queue.

Design constraints (see hermes-agent-dev skill — message-flow + cache
invariants):
  * Events describe *transport*, never *context*.  Nothing here is persisted to
    conversation history; what the gateway chooses to "eat" (e.g. tool chrome on
    a platform that can't render it) must never diverge from the bytes stored in
    the agent's message history.  History is owned by the agent; these events are
    a presentation-layer stream only.
  * Backward compatible by construction.  The gateway adapts its existing
    callbacks into these events at the boundary; adapters that don't opt into
    event-native rendering get identical behavior via the base-class default.

### class MessageChunk

> 继承: `object` ｜ 方法数: 0（公开 0）

A delta of streamed assistant text.

``text`` is the incremental content as it arrives from the model.  The
consumer accumulates chunks and progressively renders them (native draft on
Telegram DMs, edit-in-place elsewhere).  Reasoning/think-block content is
filtered upstream and never arrives as a MessageChunk.


### class MessageStop

> 继承: `object` ｜ 方法数: 0（公开 0）

The current assistant message segment is complete.

Emitted when a contiguous run of assistant text ends — either the whole
response finished, or a tool boundary interrupts the text so the next
segment should render as a fresh message *below* any tool chrome.

``final`` is True only for the terminal stop of the whole turn; an
intermediate stop (text → tool call → more text) carries ``final=False`` so
the consumer finalizes the current bubble and prepares a new segment without
treating the turn as done.


### class Commentary

> 继承: `object` ｜ 方法数: 0（公开 0）

A complete interim assistant message emitted between tool iterations.

Example: the model says "I'll inspect the repo first." before issuing a tool
call.  Unlike a MessageChunk this is already-complete text (not a delta); the
consumer renders it as its own message so it reads as a distinct beat.


### class ToolCallChunk

> 继承: `object` ｜ 方法数: 0（公开 0）

A tool invocation has started (or its in-progress state changed).

Carries the raw facts about the call — name, a short argument ``preview``,
and the full ``args`` dict — and lets the *gateway* decide presentation
(emoji, truncation, verbose vs compact, or eat it entirely on platforms that
don't show tool chrome).  Previously the agent's gateway callback baked the
emoji + preview formatting in; that decision now belongs to the adapter.


### class ToolCallFinished

> 继承: `object` ｜ 方法数: 0（公开 0）

A tool invocation completed.

``duration`` is wall-clock seconds.  ``ok`` reflects whether the tool
returned without raising.  The gateway uses this to clear/settle a progress
bubble and to drive one-time onboarding hints (e.g. suggest /verbose after a
long tool run).  No tool *output* travels here — output is the agent's
concern and is persisted to history, not streamed as presentation.


### class LongToolHint

> 继承: `object` ｜ 方法数: 0（公开 0）

One-shot onboarding nudge when a tool runs longer than the threshold.

The gateway gates this on platform capability (the /verbose command must be
usable) and on the user not having seen the hint before.  Modeled as an
event so the *gateway* owns the "should I surface this here?" decision rather
than the agent.


### class GatewayNotice

> 继承: `object` ｜ 方法数: 0（公开 0）

A gateway-originated control message (restart, online, long-run notice).

``kind`` is a stable string the adapter can switch on
(``"restart"`` / ``"online"`` / ``"long_run"`` / …).  ``text`` is the
human-readable default the base class renders when an adapter has no
platform-specific treatment.


## gateway.systemd_notify

### 模块文档

Minimal, optional systemd ``sd_notify`` support for the gateway.

### class SystemdWatchdog

> 继承: `object` ｜ 方法数: 10（公开 7）

Feed systemd while the asyncio event loop continues to make progress.

#### def `__init__(config_enabled: bool = True, lag_tolerance_seconds: Optional[float] = None) -> None`

#### property `enabled(self) -> bool`

#### property `unhealthy(self) -> bool`

#### property `task(self) -> Optional[asyncio.Task[None]]`

#### def `start(self) -> bool`

Start the loop-progress sampler when systemd watchdog is enabled.

#### def `ready(self, status: str = 'Gateway running') -> bool`

Tell systemd that startup completed and the gateway is ready.

#### def `record_tick(self, scheduled_at: float, now: float) -> bool`

Feed systemd only when the event loop woke within its lag budget.

#### async def `stop(self) -> None`

Stop feeding systemd and emit ``STOPPING=1`` at most once.


### 顶层函数

#### def `notify(message: str) -> bool`

Send one nonblocking sd_notify datagram when systemd configured it.

Notification failures are deliberately non-fatal: a missing socket or an
older platform must never prevent the gateway from starting.

#### def `watchdog_interval_seconds() -> Optional[float]`

Return systemd's configured watchdog interval in seconds.


## gateway.turn_lease

### 模块文档

Per-session turn lease — serializes the [load history → run → flush] region.

Why this exists (#64934): the gateway's busy guards are keyed by ROUTING KEY
(``_active_sessions`` in the adapter, ``_running_agents`` in the runner), but
the durable transcript is owned by SESSION_ID — and ``switch_session()`` makes
the key→id mapping many-to-one (``/resume`` of a named session from a second
chat/topic, CLI-continuity rebinding, async-delegation completion pinning,
Telegram topic-binding tip-walks). Two routing keys mapped to one session_id
run concurrent turns on two different agent objects, so no per-key guard ever
sees the collision. The two turns then interleave their flushes on one
transcript: rows persist in completion order instead of arrival order, the
identity-marker dedup over shared history dicts can swallow a row outright,
and the second turn runs on a history base that never saw the first turn's
exchange — leaving a permanent ``user;user`` alternation wedge that
``repair_message_sequence`` re-repairs on every request forever.

The lease closes that route by serializing per RESOLVED session_id: it is
acquired after session resolution is final (post ``switch_session``/tip-walk),
immediately before the transcript load, and released in the dispatch layer's
``finally`` on every exit path. Same-key messages never reach the acquisition
point while a turn runs (both routing-key guards hold them), so the lock is
uncontended everywhere except the alias-key route — where the second turn now
waits for the first turn's flush and logs one WARNING naming the session and
both routing keys (pairing with the cross-agent tripwire in
``agent/agent_runtime_helpers.note_turn_start``).

Safety properties:

- **Generation-scoped, identity-checked release.** A token records its owner
  (routing key, run generation) and release only frees the lease when that
  exact token is the current holder — a stale unwind can never release a
  newer turn's lease (the #28686 ownership lesson applied). Release is
  idempotent.
- **Fail-open on timeout.** A stuck holder degrades to today's unserialized
  behavior with a loud ERROR after the configured wait — never a wedged
  session. A degraded token holds nothing and releases nothing.
- **Bounded registry.** The per-session lease map is size-capped; eviction
  only ever removes idle (unheld, uncontended) entries, never a live lease.

Known limits (deliberate, flagged on #64934):

- A CLI process sharing the session via CLI-continuity is outside any
  in-process lock — that pair needs a DB-level lease (separate design).
- Mid-turn compression rotation leaves a small alias window: the tip-walk can
  resolve a fresh child id while the parent-holding turn is still in flight.
  The mid-turn binding-sync sites are the right place to alias the lease in a
  follow-up.

### class TurnLeaseToken

> 继承: `object` ｜ 方法数: 2（公开 0）

Handle returned by :meth:`SessionTurnLeaseRegistry.acquire`.

``degraded`` means the acquire timed out and the turn is proceeding
UNSERIALIZED (fail-open); such a token holds nothing and its release is a
no-op. ``released`` makes release idempotent.

#### def `__init__(session_id: str, owner_key: str, generation: int, degraded: bool = False) -> None`


### class SessionTurnLeaseRegistry

> 继承: `object` ｜ 方法数: 7（公开 3）

Asyncio lease per resolved session_id serializing transcript turns.

Process-local and single-event-loop by design — the same visibility scope
as the routing-key guards it extends. All methods must be called from the
gateway's event loop.

#### def `__init__(max_entries: int = DEFAULT_MAX_LEASES) -> None`

#### async def `acquire(self, session_id: str, owner_key: str, generation: int, timeout: Optional[float] = None) -> Optional[TurnLeaseToken]`

Acquire the turn lease for ``session_id``, waiting if held.

Returns a :class:`TurnLeaseToken` — degraded when the wait timed out
(fail-open: caller proceeds unserialized). Returns ``None`` for a
falsy ``session_id``.

#### def `rebind(self, token: Optional[TurnLeaseToken], new_session_id: str) -> bool`

Alias a HELD lease onto ``new_session_id`` after mid-turn rotation.

Compression can rotate the durable session_id while a turn is in
flight (session-hygiene pre-compression, in-agent compression). The
turn's flush then targets the NEW id — so the serialization boundary
must follow it, or an alias routing key resolving the new id (e.g. a
topic tip-walk landing on the fresh child) could start a concurrent
turn the lease never sees. This closes the rotation-alias window
flagged on #64934.

Mechanism: the SAME ``_SessionLease`` object is registered under the
new id (the old mapping stays until it goes idle and is evicted), so
acquirers on either id serialize against one lock — no lock state is
moved, no asyncio internals are touched. Only the current holder can
rebind (identity-checked like release), and the token follows to the
new id so release frees the shared object.

Edge: if the new id already has a live lease of its own (another
turn is running on the target session), the two serialization
domains cannot be merged mid-wait — log loudly and keep the token on
the old id. Fail-open, never deadlock: a holder cannot wait mid-turn.

#### def `release(self, token: Optional[TurnLeaseToken]) -> bool`

Release ``token``'s lease. Idempotent; ownership-checked.

Returns True only when this exact token was the current holder and
the lock was freed. A degraded token, a re-release, or a stale token
whose slot has since been granted to a newer turn are all safe
no-ops — a stale unwind can never release a newer turn's lease.


## gateway.whatsapp_identity

### 模块文档

Shared helpers for canonicalising WhatsApp sender identity.

WhatsApp's bridge can surface the same human under two different JID shapes
within a single conversation:

- LID form: ``999999999999999@lid``
- Phone form: ``15551234567@s.whatsapp.net``

Both the authorisation path (:mod:`gateway.run`) and the session-key path
(:mod:`gateway.session`) need to collapse these aliases to a single stable
identity. This module is the single source of truth for that resolution so
the two paths can never drift apart.

Public helpers:

- :func:`normalize_whatsapp_identifier` — strip JID/LID/device/plus syntax
  down to the bare numeric identifier.
- :func:`canonical_whatsapp_identifier` — walk the bridge's
  ``lid-mapping-*.json`` files and return a stable canonical identity
  across phone/LID variants.
- :func:`expand_whatsapp_aliases` — return the full alias set for an
  identifier. Used by authorisation code that needs to match any known
  form of a sender against an allow-list.

Plugins that need per-sender behaviour on WhatsApp (role-based routing,
per-contact authorisation, policy gating in a gateway hook) should use
``canonical_whatsapp_identifier`` so their bookkeeping lines up with
Hermes' own session keys.

### 顶层函数

#### def `normalize_whatsapp_identifier(value: str) -> str`

Strip WhatsApp JID/LID syntax down to its stable numeric identifier.

Accepts any of the identifier shapes the WhatsApp bridge may emit:
``"60123456789@s.whatsapp.net"``, ``"60123456789:47@s.whatsapp.net"``,
``"60123456789@lid"``, or a bare ``"+601****6789"`` / ``"60123456789"``.
Returns just the numeric identifier (``"60123456789"``) suitable for
equality comparisons.

Useful for plugins that want to match sender IDs against
user-supplied config (phone numbers in ``config.yaml``) without
worrying about which variant the bridge happens to deliver.

#### def `to_whatsapp_jid(value: str) -> str`

Normalize an *outbound* WhatsApp target to a bridge-safe JID.

Baileys' ``jidDecode`` crashes on a bare phone number — it expects a
fully-qualified JID such as ``50766715226@s.whatsapp.net``. This helper
is the inverse of :func:`normalize_whatsapp_identifier`: instead of
stripping a JID down to its numeric core for comparison, it *builds* the
JID a send must use.

Behaviour:

- ``"+50766715226"`` / ``"50766715226"`` → ``"50766715226@s.whatsapp.net"``
- ``"50766715226@s.whatsapp.net"`` → unchanged
- ``"group-id@g.us"`` / ``"130631430344750@lid"`` → unchanged
- ``"user:device@s.whatsapp.net"`` style colon-before-``@`` → ``@`` form
- anything that isn't a recognizable bare phone → returned unchanged so
  the bridge can surface a meaningful error rather than us mangling it.

Returns ``""`` for an empty/whitespace input.

#### def `expand_whatsapp_aliases(identifier: str) -> Set[str]`

Resolve WhatsApp phone/LID aliases via bridge session mapping files.

Returns the set of all identifiers transitively reachable through the
bridge's ``$HERMES_HOME/whatsapp/session/lid-mapping-*.json`` files,
starting from ``identifier``. The result always includes the
normalized input itself, so callers can safely ``in`` check against
the return value without a separate fallback branch.

Returns an empty set if ``identifier`` normalizes to empty.

#### def `canonical_whatsapp_identifier(identifier: str) -> str`

Return a stable WhatsApp sender identity across phone-JID/LID variants.

WhatsApp may surface the same person under either a phone-format JID
(``60123456789@s.whatsapp.net``) or a LID (``1234567890@lid``). This
applies to a DM ``chat_id`` *and* to the ``participant_id`` of a
member inside a group chat — both represent a user identity, and the
bridge may flip between the two for the same human.

This helper reads the bridge's ``whatsapp/session/lid-mapping-*.json``
files, walks the mapping transitively, and picks the shortest
(numeric-preferred) alias as the canonical identity.
:func:`gateway.session.build_session_key` uses this for both WhatsApp
DM chat_ids and WhatsApp group participant_ids, so callers get the
same session-key identity Hermes itself uses.

Plugins that need per-sender behaviour (role-based routing,
authorisation, per-contact policy) should use this so their
bookkeeping lines up with Hermes' session bookkeeping even when
the bridge reshuffles aliases.

Returns an empty string if ``identifier`` normalizes to empty. If no
mapping files exist yet (fresh bridge install), returns the
normalized input unchanged.

