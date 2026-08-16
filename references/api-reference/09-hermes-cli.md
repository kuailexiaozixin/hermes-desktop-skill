# hermes_cli — 命令行包（206 模块）

> **模块**: `hermes_cli/`（包，共 206 个模块）
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: 命令行/网关/配置/Web 服务等顶层入口。

## hermes_cli.__init__

### 模块文档

Hermes CLI - Unified command-line interface for Hermes Agent.

Provides subcommands for:
- hermes chat          - Interactive chat (same as ./hermes)
- hermes gateway       - Run gateway in foreground
- hermes gateway start - Start gateway service
- hermes gateway stop  - Stop gateway service
- hermes setup         - Interactive setup wizard
- hermes status        - Show status of all components
- hermes cron          - Manage cron jobs

## hermes_cli._parser

### 模块文档

Top-level argparse construction for the hermes CLI.

Lives in its own module so other modules (e.g. ``relaunch.py``) can
introspect the parser to discover which flags exist without running the
``main`` fn.

Only the top-level parser and the ``chat`` subparser live here. Every other
subparser (model, gateway, sessions, …) is built inline in ``main.py``
because its dispatch is tightly coupled to module-level ``cmd_*`` functions.

### 顶层函数

#### def `build_top_level_parser()`

Build the top-level parser, the subparsers action, and the ``chat`` subparser.

Returns ``(parser, subparsers, chat_parser)``. The caller wires
``chat_parser.set_defaults(func=cmd_chat)`` and continues registering
other subparsers via ``subparsers.add_parser(...)``.


## hermes_cli._subprocess_compat

### 模块文档

Windows subprocess compatibility helpers.

Hermes is developed on Linux / macOS and tested natively on Windows too.
Several common subprocess patterns break silently-or-loudly on Windows:

* ``["npm", "install", ...]`` — on Windows ``npm`` is ``npm.cmd``, a batch
  shim.  ``subprocess.Popen(["npm", ...])`` fails with WinError 193
  ("not a valid Win32 application") because CreateProcessW can't run a
  ``.cmd`` file without ``shell=True`` or PATHEXT resolution.

* ``start_new_session=True`` — on POSIX, this maps to ``os.setsid()`` and
  actually detaches the child.  On Windows it's silently ignored; the
  Windows equivalent is ``CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS``
  creationflags, which Python only applies when you pass them explicitly.

* Console-window flashes — every ``subprocess.Popen`` of a ``.exe`` on
  Windows spawns a cmd window briefly unless ``CREATE_NO_WINDOW`` is
  passed.  Cosmetic but jarring for background daemons.

This module centralizes the platform-branching logic so the rest of the
codebase doesn't sprinkle ``if sys.platform == "win32":`` everywhere.

**All helpers are no-ops on non-Windows** — calling them in Linux/macOS
code paths is safe by design.  That's the "do no damage on POSIX"
guarantee.

### 顶层函数

#### def `resolve_node_command(name: str, argv: Sequence[str]) -> list[str]`

Resolve a Node-ecosystem command name to an absolute-path argv.

On Windows, commands like ``npm``, ``npx``, ``yarn``, ``pnpm``,
``playwright``, ``prettier`` ship as ``.cmd`` files (batch shims).
``subprocess.Popen(["npm", "install"])`` fails with WinError 193
because CreateProcessW doesn't execute batch files directly.

``shutil.which(name)`` *does* resolve ``.cmd`` via PATHEXT and returns
the fully-qualified path — which CreateProcessW accepts because the
extension tells Windows to route through ``cmd.exe /c``.

On POSIX ``shutil.which`` also returns a fully-qualified path when
found.  That's a small change from bare-name resolution (the OS does
its own PATH search) but functionally identical and has the side
benefit of making the argv reproducible in logs.

Behavior when the command is not on PATH:
- On Windows: return the bare name — caller can still try with
  ``shell=True`` as a last resort, OR the subsequent Popen will
  raise FileNotFoundError with a readable error we want to surface.
- On POSIX: same.  Bare ``npm`` on a Linux box without npm installed
  fails the same way it did before this function existed.

Args:
    name: The command name to resolve (``npm``, ``npx``, ``node`` …).
    argv: The remaining arguments.  Must NOT include ``name`` itself —
        this function builds the full argv list.

Returns:
    A list suitable for passing to subprocess.Popen/run/call.

#### def `windows_detach_flags() -> int`

Return Win32 creationflags that detach a child from the parent
console and process group.  0 on non-Windows.

Pair with ``start_new_session=False`` (default) when calling
subprocess.Popen — on POSIX use ``start_new_session=True`` instead,
which maps to ``os.setsid()`` in the child.

Rationale:
- ``CREATE_NEW_PROCESS_GROUP`` — child has its own process group so
  Ctrl+C in the parent console doesn't propagate.
- ``DETACHED_PROCESS`` — child has no console at all.  Necessary for
  background daemons (gateway watchers, update respawners) because
  without it, closing the console kills the child.
- ``CREATE_NO_WINDOW`` — suppress the brief cmd flash that would
  otherwise appear when launching a console app.  Redundant with
  DETACHED_PROCESS but explicit for clarity.
- ``CREATE_BREAKAWAY_FROM_JOB`` — escape any job object the parent is
  in.  Electron (Desktop app) and Tauri (bootstrap installer) wrap
  their children in job objects; without breakaway, those children
  die when the parent process exits even if they were spawned with
  DETACHED_PROCESS.  This was the missing flag that made the
  post-update gateway respawn watcher silently die alongside the
  Tauri updater after the Electron Desktop's update flow finished.

If a process is in a job that disallows breakaway (rare —
JOB_OBJECT_LIMIT_BREAKAWAY_OK isn't set), CreateProcess returns
ERROR_ACCESS_DENIED.  Python surfaces that as ``PermissionError``
on the ``subprocess.Popen`` call.  Callers in this codebase already
wrap detached spawns in ``try/except OSError`` and fall back to a
cmd.exe wrapper, so the breakaway-denied case degrades gracefully
rather than crashing.

#### def `windows_detach_flags_without_breakaway() -> int`

Same as :func:`windows_detach_flags` minus ``CREATE_BREAKAWAY_FROM_JOB``.

The docstring on :func:`windows_detach_flags` notes that a process in
a job which disallows breakaway (no ``JOB_OBJECT_LIMIT_BREAKAWAY_OK``)
will see ``ERROR_ACCESS_DENIED`` from CreateProcess, surfacing as
``OSError`` (``PermissionError``) on the ``subprocess.Popen`` call.
Callers that want to recover — by retrying without the breakaway
bit — can pair the two helpers symbolically rather than coding the
``& ~0x01000000`` magic at every site:

.. code-block:: python

    try:
        subprocess.Popen(argv, creationflags=windows_detach_flags(), …)
    except OSError:
        subprocess.Popen(
            argv,
            creationflags=windows_detach_flags_without_breakaway(),
            …,
        )

See ``gateway_windows.py::_spawn_detached`` for the canonical
implementation of this pattern.  Returns 0 on non-Windows.

#### def `windows_hide_flags() -> int`

Return Win32 creationflags that merely hide the child's console
window without detaching the child.  0 on non-Windows.

Use for short-lived console apps spawned as part of a larger
operation (``taskkill``, ``where``, version probes) where we want no
flash but also want to collect stdout/exit code synchronously.

The key difference from :func:`windows_detach_flags`: NO
``DETACHED_PROCESS`` — the child still inherits stdio handles so
``capture_output=True`` works.  ``DETACHED_PROCESS`` would sever
stdio and break stdout capture.

#### def `windows_detach_popen_kwargs() -> dict`

Return a dict of Popen kwargs that detach a child on Windows and
fall back to the POSIX equivalent (``start_new_session=True``) on
Linux/macOS.

Usage pattern:

.. code-block:: python

    subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
        **windows_detach_popen_kwargs(),
    )

This replaces the unsafe-on-Windows pattern:

.. code-block:: python

    subprocess.Popen(..., start_new_session=True)

which silently fails to detach on Windows (the flag is accepted but
has no effect — the child stays attached to the parent's console
and dies when the console closes).


## hermes_cli.active_sessions

### 模块文档

Cross-process active chat session leases.

The session database records persisted conversations.  This module records
currently open chat surfaces, including idle CLI/TUI sessions that have not
written a transcript row yet.

### class ActiveSessionLease

> 继承: `object` ｜ 方法数: 1（公开 1）

#### def `release(self) -> None`


### 顶层函数

#### def `coerce_max_concurrent_sessions(value: Any, key: str = 'max_concurrent_sessions') -> Optional[int]`

Return a positive integer cap, or None when disabled/invalid.

**异常**: `ValueError`

#### def `resolve_max_concurrent_sessions(config: Any) -> Optional[int]`

Resolve top-level max_concurrent_sessions with gateway.* fallback.

#### def `active_session_limit_message(active_count: int, max_sessions: int) -> str`

#### def `try_acquire_active_session(session_id: str, surface: str, config: Any, metadata: Optional[dict[str, Any]] = None) -> tuple[Optional[ActiveSessionLease], Optional[str]]`

Acquire an active-session slot.

Returns ``(lease, None)`` on success.  When the cap is disabled, the lease is
a no-op object so callers can unconditionally call ``release()``.

#### def `release_active_session(lease: ActiveSessionLease) -> None`

#### def `transfer_active_session(lease: ActiveSessionLease, session_id: str, metadata: Optional[dict[str, Any]] = None) -> bool`

Move an existing lease to a new session id without dropping the slot.

#### def `active_session_registry_snapshot() -> list[dict[str, Any]]`

Return the pruned active-session registry for diagnostics/tests.


## hermes_cli.auth

### 模块文档

Multi-provider authentication system for Hermes Agent.

Supports OAuth device code flows (Nous Portal, future: OpenAI Codex) and
traditional API key providers (OpenRouter, custom endpoints). Auth state
is persisted in ~/.hermes/auth.json with cross-process file locking.

Architecture:
- ProviderConfig registry defines known OAuth providers
- Auth store (auth.json) holds per-provider credential state
- resolve_provider() picks the active provider via priority chain
- resolve_*_runtime_credentials() handles token refresh and runtime keys
- logout_command() is the CLI entry point for clearing auth

Nous authentication paths:
- Invoke JWT (preferred): use a scoped access_token directly for inference.

### class ProviderConfig

> 继承: `object` ｜ 方法数: 0（公开 0）

Describes a known inference provider.


### class AuthError

> 继承: `RuntimeError` ｜ 方法数: 1（公开 0）

Structured auth error with UX mapping hints.

#### def `__init__(message: str, provider: str = '', code: Optional[str] = None, relogin_required: bool = False) -> None`


### 顶层函数

#### def `get_anthropic_key() -> str`

Return the first usable Anthropic credential, or ``""``.

Checks both the ``.env`` file and the process environment, preferring
``~/.hermes/.env`` so a deliberate key rotation isn't shadowed by a stale
shell export (matches the api-key resolution path — see #20591).  The
order mirrors the ``PROVIDER_REGISTRY["anthropic"].api_key_env_vars``
tuple:

    ANTHROPIC_API_KEY -> ANTHROPIC_TOKEN -> CLAUDE_CODE_OAUTH_TOKEN

#### def `has_usable_secret(value: Any, min_length: int = 4) -> bool`

Return True when a configured secret looks usable, not empty/placeholder.

#### def `detect_zai_endpoint(api_key: str, timeout: float = 8.0) -> Optional[Dict[str, str]]`

Probe z.ai endpoints to find one that accepts this API key.

Returns {"id": ..., "base_url": ..., "model": ..., "label": ...} for the
first working endpoint, or None if all fail.  For endpoints with multiple
candidate models, tries each in order and returns the first that succeeds.

#### def `is_rate_limited_auth_error(error: Exception) -> bool`

True when an :class:`AuthError` represents upstream rate-limiting / quota
exhaustion rather than missing or invalid credentials.

These failures are transient — re-authenticating cannot resolve them — so
callers should surface a "retry later" notice and prefer a fallback chain
instead of prompting the operator to run ``hermes auth``.

#### def `format_auth_error(error: Exception) -> str`

Map auth failures to concise user-facing guidance.

#### def `mark_provider_active_if_unset(provider_id: str) -> None`

Set ``active_provider`` to *provider_id* only when none is set yet.

Used by ``hermes auth add`` OAuth paths that create credential-pool
entries directly (no singleton ``providers.<id>`` block). Adding the
very first credential for a provider should make it the active provider
so the setup wizard's ``_model_section_has_credentials()`` check (which
consults ``get_active_provider()``) does not report "No inference
provider configured". Subsequent adds for an already-active setup leave
the user's chosen active provider untouched.

#### def `is_known_auth_provider(provider_id: str) -> bool`

#### def `get_auth_provider_display_name(provider_id: str) -> str`

#### def `is_runtime_provider_routable(provider_id: str) -> bool`

Return whether runtime resolution recognizes a provider identity.

This is a capability check, not a credential check. It follows the same
alias/plugin-aware normalization as ``resolve_provider`` while preserving
special runtime identities that intentionally live outside the registry.

#### def `read_credential_pool(provider_id: Optional[str] = None) -> Dict[str, Any]`

Return the persisted credential pool, or one provider slice.

In profile mode, the profile's credential pool is authoritative. If a
provider has no entries in the profile, entries from the global-root
``auth.json`` are used as a read-only fallback — so workers spawned in a
profile can see providers that were only authenticated at global scope.

Profile entries always win: the global fallback only applies per-provider
when the profile has zero entries for that provider. Once the user runs
``hermes auth add <provider>`` inside the profile, profile entries
fully shadow global for that provider on the next read.

Writes always go to the profile (``write_credential_pool`` is unchanged).
See issue #18594 follow-up.

#### def `write_credential_pool(provider_id: str, entries: List[Dict[str, Any]], removed_ids: Optional[Iterable[str]] = None) -> Path`

Persist one provider's credential pool under auth.json.

This is the final disk-boundary guard for borrowed/reference-only
credentials. Callers may pass raw dictionaries, so sanitize here even when
``PooledCredential.to_dict()`` already did the same work upstream.

Re-read the on-disk pool under the same lock and merge entries present on
disk but missing from ``entries``. Those were added by another process after
the caller loaded its in-memory snapshot; without this merge a later
rotation/exhaustion rewrite drops the concurrent credential.

Pass ``removed_ids`` for entries the caller intentionally removed, so the
merge does not resurrect them from the on-disk copy.

#### def `suppress_credential_source(provider_id: str, source: str) -> None`

Mark a credential source as suppressed so it won't be re-seeded.

#### def `is_source_suppressed(provider_id: str, source: str) -> bool`

Check if a credential source has been suppressed by the user.

#### def `unsuppress_credential_source(provider_id: str, source: str) -> bool`

Clear a suppression marker so the source will be re-seeded on the next load.

Returns True if a marker was cleared, False if no marker existed.

#### def `get_provider_auth_state(provider_id: str) -> Optional[Dict[str, Any]]`

Return persisted auth state for a provider, or None.

In profile mode, ``_load_provider_state`` already falls back to the
global-root ``auth.json`` per-provider when the profile has no entry —
so this is now a thin convenience wrapper. Profile state always wins
when present. Writes (``_save_auth_store`` / ``persist_*_credentials``)
are unchanged — they still target the profile only. This mirrors
``read_credential_pool``'s per-provider shadowing semantics so that
``_seed_from_singletons`` can reseed a profile's credential pool from
global-scope provider state (e.g. a globally-authenticated Anthropic
OAuth or Nous device-code session). See issue #18594 follow-up.

#### def `get_active_provider() -> Optional[str]`

Return the currently active provider ID from auth store.

#### def `is_provider_explicitly_configured(provider_id: str) -> bool`

Return True only if the user has explicitly configured this provider.

Checks:
  1. active_provider in auth.json matches
  2. model.provider in config.yaml matches
  3. Provider-specific env vars are set (e.g. ANTHROPIC_API_KEY)

This is used to gate auto-discovery of external credentials (e.g.
Claude Code's ~/.claude/.credentials.json) so they are never used
without the user's explicit choice.  See PR #4210 for the same
pattern applied to the setup wizard gate.

#### def `clear_provider_auth(provider_id: Optional[str] = None) -> bool`

Clear auth state for a provider. Used by `hermes logout`.
If provider_id is None, clears the active provider.
Returns True if something was cleared.

#### def `deactivate_provider() -> None`

Clear active_provider in auth.json without deleting credentials.
Used when the user switches to a non-OAuth provider (OpenRouter, custom)
so auto-resolution doesn't keep picking the OAuth provider.

#### def `resolve_provider(requested: Optional[str] = None, explicit_api_key: Optional[str] = None, explicit_base_url: Optional[str] = None) -> str`

Determine which inference provider to use.

Priority (when requested="auto" or None) — explicit user intent wins over a
stale logged-in OAuth provider (#29285):
1. Explicit CLI api_key/base_url -> "openrouter"
2. config.yaml `model.provider`
3. OPENAI_API_KEY / OPENROUTER_API_KEY env vars -> "openrouter"
4. OpenRouter credential pool
5. Provider-specific API keys (GLM, Kimi, MiniMax, ...) -> that provider
6. auth.json `active_provider` (logged-in OAuth) — last-resort fallback
7. AWS Bedrock credential chain
8. Error (no provider configured)

**异常**: `AuthError`

#### def `resolve_qwen_runtime_credentials(force_refresh: bool = False, refresh_if_expiring: bool = True, refresh_skew_seconds: int = QWEN_ACCESS_TOKEN_REFRESH_SKEW_SECONDS) -> Dict[str, Any]`

**异常**: `AuthError`

#### def `get_qwen_auth_status() -> Dict[str, Any]`

#### def `resolve_spotify_runtime_credentials(force_refresh: bool = False, refresh_if_expiring: bool = True, refresh_skew_seconds: int = SPOTIFY_ACCESS_TOKEN_REFRESH_SKEW_SECONDS) -> Dict[str, Any]`

**异常**: `AuthError`

#### def `get_spotify_auth_status() -> Dict[str, Any]`

#### def `login_spotify_command(args) -> None`

**异常**: `SystemExit`

#### def `refresh_codex_oauth_pure(access_token: str, refresh_token: str, timeout_seconds: float = 20.0) -> Dict[str, Any]`

Refresh Codex OAuth tokens without mutating Hermes auth state.

**异常**: `AuthError`

#### def `resolve_codex_runtime_credentials(force_refresh: bool = False, refresh_if_expiring: bool = True, refresh_skew_seconds: int = CODEX_ACCESS_TOKEN_REFRESH_SKEW_SECONDS) -> Dict[str, Any]`

Resolve runtime credentials from Hermes's own Codex token store.

Falls back to the credential pool when the singleton (``providers.openai-codex.tokens``)
has no usable access_token but the pool (``credential_pool.openai-codex``) does. This
closes the divergence between the chat path (singleton-only via this function) and
the auxiliary path (pool-first via ``_read_codex_access_token``). Without this
fallback, a user whose tokens live only in the pool — for example after a manual
pool seed, a partial re-auth, or pool-only restoration from a backup — gets a bare
HTTP 401 ``Missing Authentication header`` from the wire instead of a usable
credential. See issue #32992.

**异常**: `AuthError`, `read_error`

#### def `refresh_xai_oauth_pure(access_token: str, refresh_token: str, token_endpoint: str = '', timeout_seconds: float = 20.0) -> Dict[str, Any]`

**异常**: `AuthError`

#### def `resolve_xai_oauth_runtime_credentials(force_refresh: bool = False, refresh_if_expiring: bool = True, refresh_skew_seconds: Optional[int] = None) -> Dict[str, Any]`

#### def `fetch_nous_models(inference_base_url: str, api_key: str, timeout_seconds: float = 15.0, verify: bool | str = True) -> List[str]`

Fetch available model IDs from the Nous inference API.

**异常**: `AuthError`

#### def `resolve_nous_access_token(timeout_seconds: float = 15.0, insecure: Optional[bool] = None, ca_bundle: Optional[str] = None, refresh_skew_seconds: int = ACCESS_TOKEN_REFRESH_SKEW_SECONDS) -> str`

Resolve a refresh-aware Nous Portal access token for managed tool gateways.

**异常**: `AuthError`

#### def `refresh_nous_oauth_pure(access_token: str, refresh_token: str, client_id: str, portal_base_url: str, inference_base_url: str, token_type: str = 'Bearer', scope: str = DEFAULT_NOUS_SCOPE, obtained_at: Optional[str] = None, expires_at: Optional[str] = None, agent_key: Optional[str] = None, agent_key_expires_at: Optional[str] = None, timeout_seconds: float = 15.0, insecure: Optional[bool] = None, ca_bundle: Optional[str] = None, force_refresh: bool = False, on_state_update: Optional[Callable[[Dict[str, Any], str], None]] = None) -> Dict[str, Any]`

Refresh Nous OAuth state without mutating auth.json directly.

``on_state_update`` is called after a successful access-token refresh.
Callers that own persistent state can use it to save the newly rotated
refresh token before later validation can fail.

**异常**: `AuthError`

#### def `refresh_nous_oauth_from_state(state: Dict[str, Any], timeout_seconds: float = 15.0, force_refresh: bool = False, on_state_update: Optional[Callable[[Dict[str, Any], str], None]] = None) -> Dict[str, Any]`

Refresh Nous OAuth from a state dict. Thin wrapper around refresh_nous_oauth_pure.

#### def `persist_nous_credentials(creds: Dict[str, Any], label: Optional[str] = None)`

Persist Nous OAuth credentials as the singleton provider state
and ensure the credential pool is in sync.

Nous credentials are read at runtime from two independent locations:

- ``providers.nous``: singleton state read by
  ``resolve_nous_runtime_credentials()`` during 401 recovery and by
  ``_seed_from_singletons()`` during pool load.
- ``credential_pool.nous``: used by the runtime ``pool.select()`` path.

Historically ``hermes auth add nous`` wrote a ``manual:device_code`` pool
entry only, skipping ``providers.nous``. When the runtime credential
expired, the recovery path read the empty singleton state and raised
``AuthError`` silently (``logger.debug`` at INFO level).

This helper writes ``providers.nous`` then calls ``load_pool("nous")`` so
``_seed_from_singletons`` materialises the canonical ``device_code`` pool
entry from the singleton.  Re-running login upserts the same entry in
place; the pool never accumulates duplicate device_code rows.

``label`` is an optional user-chosen display name (from
``hermes auth add nous --label <name>``).  It gets embedded in the
singleton state so that ``_seed_from_singletons`` uses it as the pool
entry's label on every subsequent ``load_pool("nous")`` instead of the
auto-derived token fingerprint.  When ``None``, the auto-derived label
via ``label_from_token`` is used (unchanged default behaviour).

Returns the upserted :class:`PooledCredential` entry (or ``None`` if
seeding somehow produced no match — shouldn't happen).

#### def `resolve_nous_runtime_credentials(timeout_seconds: float = 15.0, insecure: Optional[bool] = None, ca_bundle: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]`

Resolve Nous inference credentials for runtime use.

Ensures access_token is a valid inference-scoped JWT, refreshing it when
needed. Concurrent processes coordinate through the auth store file lock.

Returns dict with: provider, base_url, api_key, key_id, expires_at,
expires_in, source ("invoke_jwt"), and auth_path.

**异常**: `AuthError`

#### def `invalidate_nous_auth_status_cache() -> None`

Clear the get_nous_auth_status() process-level memo.

Call this from any code path that mutates Nous auth state without going
through resolve_nous_runtime_credentials() (e.g. tests). Login/logout
flows touch auth.json, so the mtime check below invalidates them
automatically — explicit invalidation is the belt-and-braces option.

#### def `get_nous_auth_status() -> Dict[str, Any]`

Status snapshot for Nous auth.

Prefer the auth-store provider state, because that is the live source of
truth for refresh operations. When provider state exists, validate it
by resolving runtime credentials so revoked refresh sessions do not show up
as a healthy login. If provider state is absent, fall back to the credential
pool for the just-logged-in / not-yet-promoted case.

The returned snapshot is memoised for ~15s keyed on the auth.json mtime,
so menu/status surfaces that ask repeatedly don't trigger one refresh POST
per call. Login/logout flows write to auth.json and therefore invalidate
the cache automatically; tests can also call
``invalidate_nous_auth_status_cache()`` explicitly.

#### def `get_nous_session_validity() -> str`

Classify the Nous bootstrap session for the dashboard /api/status probe.

Returns one of:
  - ``"valid"``    — a usable Nous credential is present (login healthy).
  - ``"terminal"`` — the Nous session has taken a terminal auth failure
    (invalid_grant / quarantined / relogin required). This is the sole
    signal NAS acts on to re-mint a hosted-agent bootstrap session.
  - ``"unknown"``  — indeterminate (no Nous provider state, or a transient/
    non-terminal error). Never triggers a re-mint.

Determinable with NO working token — it reads local auth-store state only,
which is exactly the condition a dead hosted box is in.

ANTI-FLAP CONTRACT: only a *terminal* failure maps to "terminal". A normal
mid-rotation blip, a transient network error, or a merely-expiring token
must NOT report "terminal" (that would trigger a spurious NAS re-mint on a
healthy box). We key "terminal" on the auth layer's own terminal signal
(`relogin_required`) plus a persisted quarantine marker, never on a bare
"not logged in".

#### def `get_codex_auth_status() -> Dict[str, Any]`

Status snapshot for Codex auth.

Checks the credential pool first (where `hermes auth` stores credentials),
then falls back to the legacy provider state.

#### def `get_xai_oauth_auth_status() -> Dict[str, Any]`

#### def `get_api_key_provider_status(provider_id: str) -> Dict[str, Any]`

Status snapshot for API-key providers (z.ai, Kimi, MiniMax).

#### def `get_external_process_provider_status(provider_id: str) -> Dict[str, Any]`

Status snapshot for providers that run a local subprocess.

#### def `get_auth_status(provider_id: Optional[str] = None) -> Dict[str, Any]`

Generic auth status dispatcher.

#### def `resolve_api_key_provider_credentials(provider_id: str) -> Dict[str, Any]`

Resolve API key and base URL for an API-key provider.

Returns dict with: provider, api_key, base_url, source.

**异常**: `AuthError`

#### def `resolve_external_process_provider_credentials(provider_id: str) -> Dict[str, Any]`

Resolve runtime details for local subprocess-backed providers.

**异常**: `AuthError`

#### def `login_command(args) -> None`

Deprecated: use 'hermes model' or 'hermes setup' instead.

**异常**: `SystemExit`

#### def `build_minimax_oauth_token_provider() -> Callable[[], str]`

Return a zero-arg callable that yields a fresh MiniMax access token.

The Anthropic SDK caches ``api_key`` as a static string at construction
time, so a session that resolves credentials once at startup will keep
sending the same bearer until MiniMax's server returns 401 — typically
~15 minutes in, because MiniMax issues short-lived access tokens.

Returning a *callable* instead of a string lets us hook into the
existing Entra-ID bearer infrastructure in
:mod:`agent.anthropic_adapter`: ``build_anthropic_client`` detects a
callable and routes through ``_build_anthropic_client_with_bearer_hook``,
which mints a fresh ``Authorization`` header on every outbound request.
Each invocation re-reads the persisted state from ``auth.json`` and
calls :func:`_refresh_minimax_oauth_state` — that helper is a no-op
when the token still has more than ``MINIMAX_OAUTH_REFRESH_SKEW_SECONDS``
of life left, so the steady-state cost is one file read + one
timestamp compare per request.

Reading state fresh each time also means a refresh persisted by one
process (CLI, gateway, cron) is immediately visible to every other
process sharing the same ``auth.json``.

**异常**: `AuthError`

#### def `resolve_minimax_oauth_runtime_credentials(min_token_ttl_seconds: int = MINIMAX_OAUTH_REFRESH_SKEW_SECONDS, as_token_provider: bool = False) -> Dict[str, Any]`

Return {provider, api_key, base_url, source} for minimax-oauth.

When ``as_token_provider`` is True, ``api_key`` is a zero-arg callable
that mints a fresh access token per call (proactively refreshing if
the cached token is within ``MINIMAX_OAUTH_REFRESH_SKEW_SECONDS`` of
expiry). This is what the runtime provider path uses so that long
sessions survive MiniMax's short access-token lifetime — see
:func:`build_minimax_oauth_token_provider` for the rationale.

The default (string ``api_key``) preserves the historical contract for
diagnostic call sites like ``hermes status`` that just want to know
whether a valid token exists right now.

**异常**: `AuthError`

#### def `get_minimax_oauth_auth_status() -> Dict[str, Any]`

Return auth status dict for MiniMax OAuth provider.

#### def `nous_token_has_billing_scope() -> bool`

Return True if the currently-held Nous token carries ``billing:manage``.

Reads the persisted ``scope`` string saved at login (``_save_provider_state``
stores ``token_data.get("scope") or scope``). A space-delimited match. Used by
the lazy step-up: if False, the first billing call will 403 ``insufficient_scope``
anyway, but checking up front lets a surface skip a doomed round-trip.

#### def `step_up_nous_billing_scope(open_browser: bool = True, timeout_seconds: float = 15.0, on_verification: Optional[Callable[[str, str], None]] = None) -> bool`

Re-run the device flow requesting ``billing:manage`` and persist the result.

The lazy step-up (plan D-A): triggered when a billing endpoint returns
``403 insufficient_scope``. Runs a fresh device-connect with
``inference:invoke tool:invoke billing:manage`` on the scope. The user must be
an ADMIN/OWNER and tick "Allow terminal billing" in the portal for the minted
token to actually carry the scope; otherwise the server silently downscopes and this
returns False.

Reuses the held credential's portal/inference URLs + client_id so the step-up
targets the same deployment (incl. a preview via ``HERMES_PORTAL_BASE_URL`` set
at the original login). Persists to the auth store + shared store + pool, exactly
like ``_login_nous`` — but WITHOUT the model picker (this is a scope upgrade, not
a fresh login).

Returns True iff the new token carries ``billing:manage``.

#### def `logout_command(args) -> None`

Clear auth state for a provider.

**异常**: `SystemExit`


## hermes_cli.auth_commands

### 模块文档

Credential-pool auth subcommands.

### 顶层函数

#### def `auth_add_command(args) -> None`

**异常**: `SystemExit`

#### def `auth_list_command(args) -> None`

#### def `auth_remove_command(args) -> None`

**异常**: `SystemExit`

#### def `auth_reset_command(args) -> None`

#### def `auth_status_command(args) -> None`

**异常**: `SystemExit`

#### def `auth_logout_command(args) -> None`

#### def `auth_spotify_command(args) -> None`

**异常**: `SystemExit`

#### def `auth_command(args) -> None`


## hermes_cli.azure_detect

### 模块文档

Azure Foundry endpoint auto-detection.

Inspect a Microsoft Foundry / Azure OpenAI endpoint to determine:
  - API transport (OpenAI-style ``chat_completions`` vs
    Anthropic-style ``anthropic_messages``)
  - Available models (best effort — Azure does not expose a deployment
    listing via the inference API key, but Azure OpenAI v1 endpoints
    return the resource's model catalog via ``GET /models``)
  - Context length for each discovered/entered model, via the existing
    :func:`agent.model_metadata.get_model_context_length` resolver.

Rationale:

Azure has no pure-API-key deployment-listing endpoint — per Microsoft,
deployment enumeration requires ARM management-plane auth.  Azure
OpenAI v1 endpoints ``{resource}.openai.azure.com/openai/v1`` do return
a ``/models`` list, but it reflects the resource's *available* models
rather than the user's *deployed* deployment names.  In practice it is
still a useful hint — the user picks a familiar model name and we look
up its context length from the catalog.

Authentication modes:
  - ``api_key`` (default): the wizard passes an ``api_key`` string; the
    probe sends both ``api-key:`` and ``Authorization: Bearer`` headers
    so we hit any Azure deployment regardless of which header it expects.
  - ``entra_id``: the wizard passes a ``token_provider`` callable from
    :mod:`agent.azure_identity_adapter`. The probe mints exactly one
    bearer JWT, sends **only** ``Authorization: Bearer <jwt>`` (never
    ``api-key:``), and never persists the token. This matches Microsoft's
    documented contract for keyless inference.

The detector never crashes on errors (every HTTP call is wrapped in a
broad try/except).  Callers get a :class:`DetectionResult` with whatever
information could be gathered, and fall back to manual entry for the
rest.

### class DetectionResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Everything auto-detection could gather from a base URL + API key.


### 顶层函数

#### def `detect(base_url: str, api_key: Any = '', token_provider: Optional[Callable[[], str]] = None) -> DetectionResult`

Inspect an Azure endpoint and describe its transport + models.

Call this from the wizard before asking the user to pick an API
mode manually.  The caller should treat the returned
:class:`DetectionResult` as *advisory* — if ``api_mode`` is None,
fall back to asking the user.

``api_key`` may be a string (legacy API-key auth — sends both
``api-key:`` and ``Authorization: Bearer``) or a callable returning
a bearer JWT (Entra ID auth — sends ONLY ``Authorization: Bearer``).
``token_provider`` is an alternative explicit name for the callable
form; if both are supplied the callable wins.

#### def `lookup_context_length(model: str, base_url: str, api_key: Any = '', token_provider: Optional[Callable[[], str]] = None) -> Optional[int]`

Thin wrapper around :func:`agent.model_metadata.get_model_context_length`
that returns ``None`` when only the fallback default (128k) would
fire, so the wizard can distinguish "we actually know this" from
"we guessed.

For Entra-ID mode pass a callable as ``api_key`` (or via
``token_provider=``); the wrapped resolver expects a string, so we
mint one bearer JWT here for the single lookup. The resolver itself
only reads catalog metadata over HTTP — no SDK client is built — so
the minted token is consumed for at most one /models probe.


## hermes_cli.backup

### 模块文档

Backup and import commands for hermes CLI.

`hermes backup` creates a zip archive of the entire ~/.hermes/ directory
(excluding the hermes-agent repo and transient files).

`hermes import` restores from a backup zip, overlaying onto the current
HERMES_HOME root.

### 顶层函数

#### def `run_backup(args) -> None`

Create a zip backup of the Hermes home directory.

#### def `run_import(args) -> None`

Restore a Hermes backup from a zip file.

#### def `create_quick_snapshot(label: Optional[str] = None, hermes_home: Optional[Path] = None, keep: Optional[int] = None, max_file_size: Optional[int] = None) -> Optional[str]`

Create a quick state snapshot of critical files.

Copies STATE_FILES to a timestamped directory under state-snapshots/.
Auto-prunes old snapshots beyond the keep limit.

Args:
    max_file_size: When set, individual files larger than this many bytes
        are skipped (with a printed warning) instead of copied. Used by
        the pre-update safety snapshot so a multi-GB ``state.db`` can
        never stall ``hermes update`` or silently eat disk — the small
        pairing/cron/config files the snapshot exists to protect are
        always captured. ``None`` (default) copies everything, which
        preserves manual ``/snapshot`` and ``hermes backup --quick``
        behavior.

Returns:
    Snapshot ID (timestamp-based), or None if no files found.

#### def `list_quick_snapshots(limit: int = 20, hermes_home: Optional[Path] = None) -> List[Dict[str, Any]]`

List existing quick state snapshots, most recent first.

#### def `restore_quick_snapshot(snapshot_id: str, hermes_home: Optional[Path] = None) -> bool`

Restore state from a quick snapshot.

Overwrites current state files with the snapshot's copies.
Returns True if at least one file was restored.

#### def `restore_cron_jobs_if_emptied(snapshot_id: str, hermes_home: Optional[Path] = None) -> Optional[Dict[str, Any]]`

Safety net for silent cron-job loss across ``hermes update``.

Config-version migrations have been observed to leave ``cron/jobs.json``
valid-but-empty after an update, silently dropping every scheduled job
(issue #34600). The desktop scheduler can also overwrite the file with its
own small set of internally-tracked crons, causing partial loss (issue
#52144).

This compares the *current* job count against the pre-update snapshot. If
the live file now has **fewer** jobs than the snapshot, the snapshot copy
of ``cron/jobs.json`` is restored in place.

The check is deliberately conservative — it only ever restores when there
is unambiguous evidence of loss (snapshot had more jobs than live file),
so a user who genuinely deleted jobs during/after the update is never
second-guessed, and an unreadable live file (count ``None``) is left
untouched so real corruption still surfaces.

Args:
    snapshot_id: The pre-update quick-snapshot id (from
        :func:`create_quick_snapshot`).
    hermes_home: Override for the Hermes home directory (tests).

Returns:
    ``None`` when no action was taken (the common, healthy path). On a
    successful restore, a dict ``{"restored": True, "job_count": N,
    "snapshot_id": ...}`` so the caller can warn the user.

#### def `prune_quick_snapshots(keep: int = _QUICK_DEFAULT_KEEP, hermes_home: Optional[Path] = None) -> int`

Manually prune quick snapshots. Returns count deleted.

#### def `run_quick_backup(args) -> None`

CLI entry point for hermes backup --quick.

#### def `create_pre_update_backup(hermes_home: Optional[Path] = None, keep: int = _PRE_UPDATE_DEFAULT_KEEP) -> Optional[Path]`

Create a full zip backup of HERMES_HOME under ``backups/``.

Mirrors :func:`run_backup` (same exclusion rules, same SQLite safe-copy)
but writes to ``<HERMES_HOME>/backups/pre-update-<timestamp>.zip`` and
auto-prunes old pre-update backups.

Returns the path to the created zip, or ``None`` if no files were
found or the backup could not be created.  Never raises — the caller
(``hermes update``) should continue even if the backup fails.

#### def `create_pre_migration_backup(hermes_home: Optional[Path] = None, keep: int = _PRE_MIGRATION_DEFAULT_KEEP) -> Optional[Path]`

Create a full zip backup of HERMES_HOME under ``backups/`` before a
``hermes claw migrate`` apply.

Shares implementation with :func:`create_pre_update_backup` via
``_write_full_zip_backup`` — same exclusions, same SQLite safe-copy,
restorable with ``hermes import <archive>``.  Writes to
``<HERMES_HOME>/backups/pre-migration-<timestamp>.zip`` and auto-prunes
old pre-migration backups.

Returns the path to the created zip, or ``None`` if nothing was found
to back up (fresh install) or the write failed.  Never raises — the
caller decides whether to abort or proceed.


## hermes_cli.banner

### 模块文档

Welcome banner, ASCII art, skills summary, and update check for the CLI.

Pure display functions with no HermesCLI state dependency.

### 顶层函数

#### def `cprint(text: str)`

Print ANSI-colored text through prompt_toolkit's renderer.

#### def `get_available_skills() -> Dict[str, List[str]]`

Return skills grouped by category, filtered by platform and disabled state.

Delegates to ``_find_all_skills()`` from ``tools/skills_tool`` which already
handles platform gating (``platforms:`` frontmatter) and respects the
user's ``skills.disabled`` config list.

#### def `check_via_pypi() -> Optional[int]`

Compare installed version against PyPI latest.

Returns 0 if up-to-date, 1 if behind, None on failure.

#### def `check_for_updates() -> Optional[int]`

Check whether a Hermes update is available.

Two paths: if ``HERMES_REVISION`` is set (nix builds embed it), compare
it to upstream main via ``git ls-remote``. Otherwise look for a local
git checkout and count commits behind ``origin/main``.

Returns the number of commits behind, ``UPDATE_AVAILABLE_NO_COUNT`` (-1)
if behind but the count is unknown, ``0`` if up-to-date, or ``None`` if
the check failed or doesn't apply. Cached for 6 hours.

#### def `get_git_banner_state(repo_dir: Optional[Path] = None) -> Optional[dict]`

Return upstream/local git hashes for the startup banner.

For source installs and dev images this runs ``git rev-parse`` against
the active checkout.  When no checkout is available — the canonical case
is the published Docker image, which excludes ``.git`` from the build
context — we fall back to the baked-in build SHA (see
``hermes_cli/build_info.py``) and return it as a frozen
``upstream == local`` state with ``ahead=0``.  A built image is by
definition pinned to one commit, so "ahead" is always zero and the
banner correctly shows ``· upstream <sha>`` with no carried-commits
annotation.

#### def `get_latest_release_tag(repo_dir: Optional[Path] = None) -> Optional[tuple]`

Return ``(tag, release_url)`` for the latest git tag, or None.

Local-only — runs ``git describe --tags --abbrev=0`` against the
Hermes checkout. Cached per-process. Release URL always points at the
canonical NousResearch/hermes-agent repo (forks don't get a link).

#### def `format_banner_version_label() -> str`

Return the version label shown in the startup banner title.

#### def `prefetch_update_check()`

Kick off update check in a background daemon thread.

#### def `get_update_result(timeout: float = 0.5) -> Optional[int]`

Get result of prefetched check. Returns None if not ready.

#### def `build_welcome_banner(console: Console, model: str, cwd: str, tools: List[dict] = None, enabled_toolsets: List[str] = None, session_id: str = None, get_toolset_for_tool = None, context_length: int = None, provider: str = None)`

Build and print a welcome banner with caduceus on left and info on right.

Args:
    console: Rich Console instance.
    model: Current model name.
    cwd: Current working directory.
    tools: List of tool definitions.
    enabled_toolsets: List of enabled toolset names.
    session_id: Session identifier.
    get_toolset_for_tool: Callable to map tool name -> toolset name.
    context_length: Model's context window size in tokens.
    provider: Active provider id. When ``"moa"``, ``model`` is a MoA
        preset name and the banner renders the aggregator instead of a
        bare model slug.


## hermes_cli.blueprint_cmd

### 模块文档

Shared ``/blueprint`` command logic for CLI, TUI, and gateway.

The conversational counterpart to the dashboard's Automation Blueprints form. Where a
surface has a screen, the user fills a form (dashboard / GUI app) and the API
calls ``fill_blueprint`` -> ``create_job`` directly. Where a surface is just a
chat line, the user picks a blueprint by name and the agent asks for what it
needs — pick a blueprint by name and the agent asks you for what it needs, one
question at a time (the messaging-assistant model: pick a blueprint → it asks you
a couple things → done).

Subcommand shapes:
  /blueprint                      list the catalog
  /blueprint <name>               name-match a blueprint, then SEED THE AGENT to
                                    ask the user for each value conversationally
  /blueprint <name> slot=val …    fill + create the cron job directly
                                    (the deterministic dashboard / docs / power-
                                    user shortcut — no agent turn)

The ``<name>`` form is forgiving: exact key, unique prefix, or fuzzy match all
resolve; an ambiguous query lists the candidates; an unknown one suggests the
closest. When it resolves, the handler returns an ``agent_seed`` — a natural-
language instruction built from the blueprint's typed slots + schedule/prompt
templates — that the calling surface feeds to the agent as a normal user turn
(gateway: rewrite ``event.text`` and fall through, the ``/steer`` pattern; CLI:
a one-shot pending seed the main loop runs). The agent then asks for each slot
and calls the existing ``cronjob`` tool. No new tool, no second job engine.

Parsing is shlex-based so quoted free-text values (``criteria="from my boss"``)
survive.

### class BlueprintCommandResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Outcome of a ``/blueprint`` invocation.

``text`` is always shown to the user. When ``agent_seed`` is set, the
calling surface should ALSO hand that seed to the agent as the user's next
turn (the blueprint was matched and now the agent gathers the slot values
conversationally). When ``agent_seed`` is None the command is fully handled
(catalog listing, direct create, or an error) and nothing is sent to the
agent.


### 顶层函数

#### def `match_blueprint(query: str) -> Tuple[Optional[Any], List[Any]]`

Resolve a free-typed blueprint name to a blueprint.

Returns ``(blueprint, candidates)``:
  * exact key or unique prefix / fuzzy match -> ``(blueprint, [])``
  * ambiguous (2+ plausible) -> ``(None, [candidates…])``
  * no plausible match -> ``(None, [])``

Matching is forgiving because chat-line users type the name (unlike the
dashboard/Discord where it's picked): exact key first, then case-insensitive
prefix on key or title, then a difflib fuzzy pass.

#### def `build_blueprint_seed(blueprint) -> str`

Build the natural-language fill-request the agent will act on.

The agent reads this as a normal user turn, asks the user for each unfilled
slot one at a time, then calls the ``cronjob`` tool with the
cron expression it builds from the blueprint's ``schedule_template`` and the
rendered prompt. Defaults are stated so the agent can offer them.

#### def `handle_blueprint_command(args: str, origin: Optional[Dict[str, Any]] = None, surface: str = 'cli') -> BlueprintCommandResult`

Dispatch a ``/blueprint`` invocation.

Returns a :class:`BlueprintCommandResult`. When ``agent_seed`` is set the
caller must feed it to the agent as the next user turn; otherwise the
command is fully handled and only ``text`` is shown.

``args`` is everything after ``/blueprint``. ``origin`` lets a directly
created job deliver back to the chat it was set up from. ``surface``
(``"cli"`` | ``"gateway"``) picks the right wording for follow-up hints —
``/cron`` only exists on the CLI.


## hermes_cli.browser_connect

### 模块文档

Shared helpers for attaching Hermes to a local Chromium-family CDP port.

### class LaunchAttempt

> 继承: `object` ｜ 方法数: 0（公开 0）

Outcome of one candidate-binary launch attempt.


### class ChromeDebugLaunch

> 继承: `object` ｜ 方法数: 1（公开 1）

Structured result of ``launch_chrome_debug``.

``launched`` mirrors the legacy boolean contract: a launch command was
executed and the browser is ready or still starting (it does NOT
guarantee the CDP port ever opens). ``attempts`` carries per-candidate
diagnostics so callers can explain *why* nothing came up.

#### property `hint(self) -> str | None`

Best user-facing explanation for a failed/soft launch, if any.


### 顶层函数

#### def `get_chrome_debug_candidates(system: str) -> list[str]`

#### def `chrome_debug_data_dir() -> str`

#### def `is_browser_debug_ready(url: str, timeout: float = 1.0) -> bool`

Return True when ``url`` exposes a reachable Chrome DevTools endpoint.

#### def `discover_local_cdp_url(port: int, timeout: float = 1.0) -> str | None`

Return the first loopback URL (IPv4 first, then IPv6) speaking CDP.

Dual-stack discovery: when another application squats the IPv4
loopback on ``port``, a debug browser launched with
``--remote-debugging-port`` may bind only ``[::1]``. Probing both
literals finds it either way. Returns ``None`` when neither
loopback exposes a CDP discovery endpoint.

#### def `local_port_in_use(port: int, timeout: float = 0.5) -> bool`

Return True when either loopback accepts TCP on ``port``.

Callers use this AFTER a failed CDP probe to distinguish "port is
free, we can launch a browser on it" from "another application
(IDE debugger, dev server) is squatting the port and a launch
would fight it".

#### def `find_free_debug_port(preferred: int = DEFAULT_BROWSER_CDP_PORT, attempts: int = 10) -> int`

Return the first port after ``preferred`` bindable on both loopbacks.

Used when ``preferred`` is occupied by a non-CDP application: rather
than launching a browser into a bind conflict, pick a nearby free
port. Falls back to ``preferred + 1`` if nothing binds (the launch
will then fail with a clear browser-side error instead of silently
doing nothing).

#### def `manual_chrome_debug_command(port: int = DEFAULT_BROWSER_CDP_PORT, system: str | None = None) -> str | None`

#### def `launch_chrome_debug(port: int = DEFAULT_BROWSER_CDP_PORT, system: str | None = None) -> ChromeDebugLaunch`

Launch a Chromium-family browser with remote debugging, with diagnostics.

Tries each detected candidate binary in turn. A candidate that exits
before the CDP port opens (crash, singleton forward to an existing
instance, bad profile dir) is logged — with exit code and a stderr tail —
and the next candidate is tried.

#### def `try_launch_chrome_debug(port: int = DEFAULT_BROWSER_CDP_PORT, system: str | None = None) -> bool`


## hermes_cli.build_info

### 模块文档

Baked-in build metadata for Hermes Agent.

Source installs report their git revision live via ``git rev-parse`` (see
``hermes_cli/dump.py`` and ``hermes_cli/banner.py``).  That doesn't work inside
the published Docker image because ``.dockerignore`` excludes ``.git``, so
those callsites fall back to ``"(unknown)"`` / drop the banner suffix entirely.

To make ``hermes dump`` and the startup banner identify the exact commit the
image was built from, the Docker build writes the build-time ``$HERMES_GIT_SHA``
arg into ``<project_root>/.hermes_build_sha``.  This module is the single
read-side helper consumed by both callsites — keeping the lookup in one place
so the file path and missing-file behaviour stay consistent.

Behaviour:

- Returns ``None`` when the file is absent.  Source installs and dev images
  built without the ``HERMES_GIT_SHA`` build-arg fall through to live-git
  resolution in the caller, so non-Docker installs are unaffected.
- Returns ``None`` on any IO / decoding error.  The build-sha is a nice-to-have
  for support triage; nothing in the CLI is allowed to crash because of it.
- Truncates to ``short`` characters (default 8) to match the format used by
  ``git rev-parse --short=8`` throughout the codebase.

### 顶层函数

#### def `get_build_sha(short: int = 8) -> Optional[str]`

Return the baked-in build SHA, truncated to ``short`` chars, or None.

Reads ``<project_root>/.hermes_build_sha`` if present.  The file is
written by the Dockerfile's ``HERMES_GIT_SHA`` build-arg and contains
the full 40-character commit hash on a single line.


## hermes_cli.bundles

### 模块文档

Implementation of the ``hermes bundles`` CLI subcommand.

Mirrors the structure of ``hermes_cli/skills_hub.py`` but for skill
bundles. Bundles are tiny YAML files that name a set of skills to load
together via a single ``/<bundle>`` slash command.

Subcommands:
- list: show all bundles
- show: dump one bundle's contents
- create: build a new bundle from arguments or interactively
- delete: remove a bundle
- reload: re-scan the bundles directory

### 顶层函数

#### def `register_cli(subparser) -> None`

Build the ``hermes bundles`` argparse tree.

Called from ``hermes_cli/main.py`` where it owns the top-level
``bundles`` subparser. Keeping registration here means the bundles
subcommand's argparse tree lives next to its handlers.

#### def `bundles_command(args) -> None`

Dispatch ``hermes bundles <subcommand>`` to the right handler.


## hermes_cli.callbacks

### 模块文档

Interactive prompt callbacks for terminal_tool integration.

These bridge terminal_tool's interactive prompts (clarify, sudo, approval)
into prompt_toolkit's event loop. Each function takes the HermesCLI instance
as its first argument and uses its state (queues, app reference) to coordinate
with the TUI.

### 顶层函数

#### def `clarify_callback(cli, question, choices)`

Prompt for clarifying question through the TUI.

Sets up the interactive selection UI, then blocks until the user
responds. Returns the user's choice or a timeout message.

#### def `prompt_for_secret(cli, var_name: str, prompt: str, metadata = None) -> dict`

Prompt for a secret value through the TUI (e.g. API keys for skills).

Returns a dict with keys: success, stored_as, validated, skipped, message.
The secret is stored in ~/.hermes/.env and never exposed to the model.

#### def `approval_callback(cli, command: str, description: str) -> str`

Prompt for dangerous command approval through the TUI.

Shows a selection UI with choices: once / session / always / deny.
When the command is longer than 70 characters, a "view" option is
included so the user can reveal the full text before deciding.

Uses cli._approval_lock to serialize concurrent requests (e.g. from
parallel delegation subtasks) so each prompt gets its own turn.


## hermes_cli.checkpoints

### 模块文档

`hermes checkpoints` CLI subcommand.

Gives users direct visibility and control over the filesystem checkpoint
store at ``~/.hermes/checkpoints/``.  Actions:

    hermes checkpoints               # same as `status`
    hermes checkpoints status        # total size, project count, breakdown
    hermes checkpoints list          # per-project checkpoint counts + workdir
    hermes checkpoints prune [opts]  # force a sweep (ignores the 24h marker)
    hermes checkpoints clear [-f]    # nuke the entire base (asks first)
    hermes checkpoints clear-legacy  # delete just the legacy-* archives

Examples::

    hermes checkpoints
    hermes checkpoints prune --retention-days 3 --max-size-mb 200
    hermes checkpoints clear -f

None of these require the agent to be running.  Safe to call any time.

### 顶层函数

#### def `cmd_status(args: argparse.Namespace) -> int`

#### def `cmd_list(args: argparse.Namespace) -> int`

#### def `cmd_prune(args: argparse.Namespace) -> int`

#### def `cmd_clear(args: argparse.Namespace) -> int`

#### def `cmd_clear_legacy(args: argparse.Namespace) -> int`

#### def `register_cli(parser: argparse.ArgumentParser) -> None`

Wire subcommands onto the ``hermes checkpoints`` parser.


## hermes_cli.claw

### 模块文档

hermes claw — OpenClaw migration commands.

Usage:
    hermes claw migrate              # Preview then migrate (always shows preview first)
    hermes claw migrate --dry-run    # Preview only, no changes
    hermes claw migrate --yes        # Skip confirmation prompt
    hermes claw migrate --preset full --overwrite --migrate-secrets  # Full run w/ secrets
    hermes claw migrate --no-backup  # Skip pre-migration snapshot
    hermes claw cleanup              # Archive leftover OpenClaw directories
    hermes claw cleanup --dry-run    # Preview what would be archived

### 顶层函数

#### def `claw_command(args)`

Route hermes claw subcommands.


## hermes_cli.cli_agent_setup_mixin

### 模块文档

Agent-construction and session-resume display methods for ``HermesCLI``.

Extracted from ``cli.py`` as part of the god-file decomposition campaign
(``~/.hermes/plans/god-file-decomposition.md``, Phase 4 step 2). This mixin holds
the agent lifecycle/setup cluster: runtime-credential resolution, per-turn agent
config, first-use agent construction, and resumed-session preload + history recap.

Behavior-neutral: every method is lifted verbatim from ``HermesCLI``. ``self.*``
calls resolve unchanged via the MRO. Neutral dependencies are imported at module
top level; ``cli.py``-internal helpers/constants are imported lazily inside each
method (``from cli import ...`` resolves at call time, when ``cli`` is fully
loaded) so this module never imports ``cli`` at import time -> no import cycle.

### class CLIAgentSetupMixin

> 继承: `object` ｜ 方法数: 5（公开 0）

Agent construction + session-resume display methods for ``HermesCLI``.


## hermes_cli.cli_billing_mixin

### 模块文档

Billing and subscription handlers for the interactive CLI (god-file decomposition).

This module hosts the Nous billing/subscription methods lifted out of
``cli.py``'s ``HermesCLI`` class. ``HermesCLI`` inherits
``CLIBillingMixin`` so every ``self.<handler>`` call resolves unchanged
via the MRO — behavior-neutral apart from focused billing fixes.

Import discipline mirrors ``hermes_cli.cli_commands_mixin``:
  * Neutral, non-cyclic dependencies are imported at module top level below.
  * cli.py-internal symbols (the ``_cprint``/``_b``/``_d`` helpers and
    display constants) are imported LAZILY inside each method via
    ``from cli import ...``. The mixin never imports ``cli`` at module load
    time, avoiding the cycle created when ``cli.py`` imports this mixin.

### class CLIBillingMixin

> 继承: `object` ｜ 方法数: 29（公开 0）

Mixin holding interactive-CLI billing and subscription handlers.


## hermes_cli.cli_commands_mixin

### 模块文档

Slash-command handlers for the interactive CLI (god-file decomposition Phase 4).

This module hosts the ``_handle_*_command`` slash-command handlers lifted out of
``cli.py``'s ``HermesCLI`` class. ``HermesCLI`` inherits ``CLICommandsMixin`` so
every ``self.<handler>`` call resolves unchanged via the MRO — behavior-neutral.

Import discipline (mirrors gateway/slash_commands.py, PR #41886):
  * Neutral, non-cyclic deps are imported at module top-level below.
  * cli.py-internal symbols (the ``_cprint``/``_ACCENT``/``save_config_value``…
    module-level helpers and constants) are imported LAZILY inside each handler
    via ``from cli import ...`` — that resolves at call time when ``cli`` is fully
    loaded, so the mixin module never imports ``cli`` at top level (no cycle).

### class CLICommandsMixin

> 继承: `object` ｜ 方法数: 43（公开 0）

Mixin holding the interactive-CLI slash-command handlers.

All methods use only ``self`` state plus the imports above and per-method
lazy ``from cli import ...`` lines, so they compose cleanly onto
``HermesCLI`` via the MRO.


## hermes_cli.cli_output

### 模块文档

Shared CLI output helpers for Hermes CLI modules.

Extracts the identical ``print_info/success/warning/error`` and ``prompt()``
functions previously duplicated across setup.py, tools_config.py,
mcp_config.py, and memory_setup.py.

### 顶层函数

#### def `print_info(text: str) -> None`

Print a dim informational message.

#### def `print_success(text: str) -> None`

Print a green success message with ✓ prefix.

#### def `print_warning(text: str) -> None`

Print a yellow warning message with ⚠ prefix.

#### def `print_error(text: str) -> None`

Print a red error message with ✗ prefix.

#### def `print_header(text: str) -> None`

Print a bold yellow header.

#### def `prompt(question: str, default: str | None = None, password: bool = False) -> str`

Prompt the user for input with optional default and password masking.

Replaces the four independent ``_prompt()`` / ``prompt()`` implementations
in setup.py, tools_config.py, mcp_config.py, and memory_setup.py.

Returns the user's input (stripped), or *default* if the user presses Enter.
Returns empty string on Ctrl-C or EOF.

#### def `prompt_yes_no(question: str, default: bool = True) -> bool`

Prompt for a yes/no answer. Returns bool.


## hermes_cli.clipboard

### 模块文档

Clipboard image extraction for macOS, Windows, Linux, and WSL2.

Provides a single function `save_clipboard_image(dest)` that checks the
system clipboard for image data, saves it to *dest* as PNG, and returns
True on success.  No external Python dependencies — uses only OS-level
CLI tools that ship with the platform (or are commonly installed).

Platform support:
  macOS   — osascript (always available), pngpaste (if installed)
  Windows — PowerShell via WinForms, Get-Clipboard, file-drop fallback
  WSL2    — powershell.exe via WinForms, Get-Clipboard, file-drop fallback
  Linux   — wl-paste (Wayland), xclip (X11)

### 顶层函数

#### def `save_clipboard_image(dest: Path) -> bool`

Extract an image from the system clipboard and save it as PNG.

Returns True if an image was found and saved, False otherwise.

#### def `has_clipboard_image() -> bool`

Quick check: does the clipboard currently contain an image?

Lighter than save_clipboard_image — doesn't extract or write anything.


## hermes_cli.codex_models

### 模块文档

Codex model discovery from API, local cache, and config.

### 顶层函数

#### def `get_codex_model_ids(access_token: Optional[str] = None) -> List[str]`

Return available Codex model IDs, trying API first, then local sources.

Resolution order: API (live, if token provided) > config.toml default >
local cache > hardcoded defaults.


## hermes_cli.codex_runtime_plugin_migration

### 模块文档

Migrate Hermes' MCP server config and Codex's installed curated plugins
to the format Codex expects in ~/.codex/config.toml.

When the user enables the codex_app_server runtime, the codex subprocess
runs its own MCP client and its own plugin runtime (Linear, Atlassian,
Asana, plus per-account ChatGPT apps via app/list). For both of those to
be useful, the user's choices need to be visible to codex too. This
module:

  1. Reads Hermes' YAML and writes equivalent [mcp_servers.<name>]
     entries to ~/.codex/config.toml.
  2. Queries codex's `plugin/list` for the openai-curated marketplace
     and writes [plugins."<name>@<marketplace>"] entries for any plugin
     the user has installed=true on their codex CLI. (This is what
     OpenClaw calls "migrate native codex plugins" — the YouTube-video-
     worthy bit Pash highlighted: Canva, GitHub, Calendar, Gmail
     pre-configured.)
  3. Writes a [permissions] default profile so users on this runtime
     don't get an approval prompt on every write attempt.

What translates (MCP servers):
  Hermes mcp_servers.<n>.command/args/env  → codex stdio transport
  Hermes mcp_servers.<n>.url/headers       → codex streamable_http transport
  Hermes mcp_servers.<n>.timeout           → codex tool_timeout_sec
  Hermes mcp_servers.<n>.connect_timeout   → codex startup_timeout_sec

What does NOT translate (warned + skipped):
  Hermes-specific keys (sampling, etc.) — codex's MCP client has no
  equivalent. Listed in the per-server skipped[] field of the report.

What's NOT migrated (intentional):
  AGENTS.md — codex respects this file natively in its cwd. Hermes' own
  AGENTS.md (project-level) is already in the worktree, so codex picks
  it up without translation. No code needed.

### class MigrationReport

> 继承: `object` ｜ 方法数: 1（公开 1）

Outcome of a migration pass.

#### def `summary(self) -> str`


### 顶层函数

#### def `render_codex_toml_section(servers: dict[str, dict], plugins: Optional[list[dict]] = None, default_permission_profile: Optional[str] = None) -> str`

Render the managed [mcp_servers.<n>] / [plugins.<id>] / [permissions]
block for ~/.codex/config.toml.

Args:
    servers: dict of MCP server name → translated codex inline-table
    plugins: optional list of {name, marketplace, enabled} for native
        Codex plugins to enable. (E.g. the Linear / Atlassian / Asana
        curated plugins, or per-account ChatGPT apps.)
    default_permission_profile: when set, write `[permissions] default`
        so the user doesn't get an approval prompt on every write
        attempt. Common values: "workspace-write", "read-only",
        "full-access".

#### def `migrate(hermes_config: dict, codex_home: Optional[Path] = None, dry_run: bool = False, discover_plugins: bool = True, default_permission_profile: Optional[str] = ':workspace', expose_hermes_tools: bool = True) -> MigrationReport`

Translate Hermes mcp_servers config + Codex curated plugins into
~/.codex/config.toml.

Args:
    hermes_config: full ~/.hermes/config.yaml dict
    codex_home: override CODEX_HOME (defaults to ~/.codex)
    dry_run: skip the actual write; report what would happen
    discover_plugins: when True (default), query `plugin/list` against
        the live codex CLI to migrate any installed curated plugins
        into [plugins."<name>@<marketplace>"] entries. Set False to
        skip the subprocess spawn (for tests or restricted environments).
    default_permission_profile: when set (default ":workspace"), write
        top-level `default_permissions = "<name>"` so users on this
        runtime don't get an approval prompt on every write attempt.
        Built-in codex profile names are ":workspace", ":read-only",
        ":danger-no-sandbox" (note the leading ":"). Also accepts a
        user-defined profile name (no leading ":") that the user has
        configured in their own [permissions.<name>] table. Set None
        to leave permissions unset and let codex use its compiled-in
        default (which is read-only).
    expose_hermes_tools: when True (default), register Hermes' own
        tool surface (web_search, browser_*, delegate_task, vision,
        memory, skills, etc.) as an MCP server in ~/.codex/config.toml
        so the codex subprocess can call back into Hermes for tools
        codex doesn't have built in. Set False to opt out.


## hermes_cli.codex_runtime_switch

### 模块文档

Shared logic for the /codex-runtime slash command.

Toggles `model.openai_runtime` between "auto" (= chat_completions, Hermes'
default) and "codex_app_server" (= hand turns to a codex subprocess).

Both CLI (cli.py) and gateway (gateway/run.py) call into this module so the
behavior stays identical across surfaces.

The actual runtime resolution happens in hermes_cli.runtime_provider's
_maybe_apply_codex_app_server_runtime() helper, which reads the persisted
config value. This module just persists the value and reports the change.

### class CodexRuntimeStatus

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of a /codex-runtime invocation. Callers render this however
suits their surface (CLI uses Rich panels, gateway sends a text message).


### 顶层函数

#### def `parse_args(arg_string: str) -> tuple[Optional[str], list[str]]`

Parse the slash-command argument string. Returns (value, errors).

No args         → return current state (value=None)
'auto' / 'codex_app_server' / 'on' / 'off' → return that value
anything else   → error

#### def `get_current_runtime(config: dict) -> str`

Read the current `model.openai_runtime` value from a config dict.
Returns 'auto' for unset / empty / unrecognized values.

#### def `set_runtime(config: dict, new_value: str) -> str`

Mutate the config dict in place to persist the new runtime value.
Returns the previous value for callers that want to report a delta.

**异常**: `ValueError`

#### def `check_codex_binary_ok() -> tuple[bool, Optional[str]]`

Best-effort verification that codex CLI is installed at acceptable
version. Returns (ok, version_or_message).

#### def `apply(config: dict, new_value: Optional[str], persist_callback = None) -> CodexRuntimeStatus`

Top-level entry point used by both CLI and gateway handlers.

Args:
    config: in-memory config dict (will be mutated when new_value is set)
    new_value: desired runtime; None means "show current state only"
    persist_callback: optional callable taking the mutated config dict
        and persisting it to disk. Skipped when None (used by tests).

Returns: CodexRuntimeStatus describing the outcome.


## hermes_cli.colors

### 模块文档

Shared ANSI color utilities for Hermes CLI modules.

### class Colors

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `should_use_color() -> bool`

Return True when colored output is appropriate.

Respects the NO_COLOR environment variable (https://no-color.org/)
and TERM=dumb, in addition to the existing TTY check.

#### def `color(text: str, *codes) -> str`

Apply color codes to text (only when color output is appropriate).


## hermes_cli.commands

### 模块文档

Slash command definitions and autocomplete for the Hermes CLI.

Central registry for all slash commands. Every consumer -- CLI help, gateway
dispatch, Telegram BotCommands, Slack subcommand mapping, autocomplete --
derives its data from ``COMMAND_REGISTRY``.

To add a command: add a ``CommandDef`` entry to ``COMMAND_REGISTRY``.
To add an alias: set ``aliases=("short",)`` on the existing ``CommandDef``.

### class CommandDef

> 继承: `object` ｜ 方法数: 0（公开 0）

Definition of a single slash command.


### class SlashCommandCompleter

> 继承: `Completer` ｜ 方法数: 20（公开 1）

Autocomplete for built-in slash commands, subcommands, and skill commands.

#### def `__init__(skill_commands_provider: Callable[[], Mapping[str, dict[str, Any]]] | None = None, command_filter: Callable[[str], bool] | None = None, skill_bundles_provider: Callable[[], Mapping[str, dict[str, Any]]] | None = None) -> None`

#### def `get_completions(self, document, complete_event)`


### class SlashCommandAutoSuggest

> 继承: `AutoSuggest` ｜ 方法数: 2（公开 1）

Inline ghost-text suggestions for slash commands and their subcommands.

Shows the rest of a command or subcommand in dim text as you type.
Falls back to history-based suggestions for non-slash input.

#### def `__init__(history_suggest: AutoSuggest | None = None, completer: SlashCommandCompleter | None = None) -> None`

#### def `get_suggestion(self, buffer, document)`


### 顶层函数

#### def `resolve_command(name: str) -> CommandDef | None`

Resolve a command name or alias to its CommandDef.

Accepts names with or without the leading slash.

#### def `is_gateway_known_command(name: str | None) -> bool`

Return True if ``name`` resolves to a gateway-dispatchable slash command.

This covers both built-in commands (``GATEWAY_KNOWN_COMMANDS`` derived
from ``COMMAND_REGISTRY``) and plugin-registered commands, which are
looked up lazily so importing this module never forces plugin
discovery. Gateway code uses this to decide whether to emit
``command:<name>`` hooks — plugin commands get the same lifecycle
events as built-ins.

#### def `should_bypass_active_session(command_name: str | None) -> bool`

Return True for any resolvable slash command.

Rationale: every gateway-registered slash command either has a
specific Level-2 handler in gateway/run.py (/stop, /new, /model,
/approve, etc.) or reaches the running-agent catch-all that returns
a "busy — wait or /stop first" response. In both paths the command
is dispatched, not queued.

Queueing is always wrong for a recognized slash command because the
safety net in gateway.run discards any command text that reaches
the pending queue — which meant a mid-run /model (or /reasoning,
/voice, /insights, /title, /resume, /retry, /undo, /compress,
/usage, /reload-mcp, /sethome, /reset) would silently
interrupt the agent AND get discarded, producing a zero-char
response. See issue #5057 / PRs #6252, #10370, #4665.

ACTIVE_SESSION_BYPASS_COMMANDS remains the subset of commands with
explicit Level-2 handlers; the rest fall through to the catch-all.

#### def `gateway_help_lines() -> list[str]`

Generate gateway help text lines from the registry.

#### def `telegram_bot_commands() -> list[tuple[str, str]]`

Return (command_name, description) pairs for Telegram setMyCommands.

Telegram command names cannot contain hyphens, so they are replaced with
underscores.  Aliases are skipped -- Telegram shows one menu entry per
canonical command.

Built-in commands that require arguments (e.g. /queue, /steer, /background)
are **included** because their handlers return usage text when selected
without a payload, making them discoverable via autocomplete.

Plugin-registered slash commands that require arguments are **excluded**
because plugins may not provide a no-arg usage fallback.

#### def `telegram_menu_max_commands() -> int`

Return configured Telegram BotCommand menu cap with safe bounds.

#### def `telegram_menu_commands(max_commands: int = 100) -> tuple[list[tuple[str, str]], int]`

Return Telegram menu commands capped to the Bot API limit.

Priority order (higher priority = never bumped by overflow):
  1. Core CommandDef commands (always included)
  2. Plugin slash commands (take precedence over skills)
  3. Built-in skill commands (fill remaining slots, alphabetical)

Skills are the only tier that gets trimmed when the cap is hit.
User-installed hub skills are excluded — accessible via /skills.
Skills disabled for the ``"telegram"`` platform (via ``hermes skills
config``) are excluded from the menu entirely.

Returns:
    (menu_commands, hidden_count) where hidden_count is the number of
    commands omitted due to the cap.

#### def `discord_skill_commands(max_slots: int, reserved_names: set[str]) -> tuple[list[tuple[str, str, str]], int]`

Return skill entries for Discord slash command registration.

Same priority and filtering logic as :func:`telegram_menu_commands`
(plugins > skills, hub excluded, per-platform disabled excluded), but
adapted for Discord's constraints:

- Hyphens are allowed in names (no ``-`` → ``_`` sanitization)
- Descriptions capped at 100 chars (Discord's per-field max)

Args:
    max_slots: Available command slots (100 minus existing built-in count).
    reserved_names: Names of already-registered built-in commands.

Returns:
    ``(entries, hidden_count)`` where *entries* is a list of
    ``(discord_name, description, cmd_key)`` triples.  ``cmd_key`` is
    the original ``/skill-name`` key needed for the slash handler callback.

#### def `discord_skill_commands_by_category(reserved_names: set[str]) -> tuple[dict[str, list[tuple[str, str, str]]], list[tuple[str, str, str]], int]`

Return skill entries organized by category for Discord ``/skill`` autocomplete.

Skills whose directory is nested at least 2 levels under a scan root
(e.g. ``creative/ascii-art/SKILL.md``) are grouped by their top-level
category.  Root-level skills (e.g. ``dogfood/SKILL.md``) are returned as
*uncategorized*.

Scan roots include the local ``SKILLS_DIR`` **and** any configured
``skills.external_dirs`` — matching the widened filter applied to the
flat ``discord_skill_commands()`` collector in #18741. Without this
parity, external-dir skills are visible via ``hermes skills list`` and
the agent's ``/skill-name`` dispatch but silently absent from Discord's
``/skill`` autocomplete.

Filtering mirrors :func:`discord_skill_commands`: hub skills excluded,
per-platform disabled excluded, names clamped to 32 chars, descriptions
clamped to 100 chars.

The legacy 25-group × 25-subcommand caps (from the old nested
``/skill <cat> <name>`` layout) are **not** applied — the live caller
(``_register_skill_group`` in ``gateway/platforms/discord.py``, refactored
in PR #11580) flattens these results and feeds them into a single
autocomplete callback, which scales to thousands of entries without any
per-command payload concerns. ``hidden_count`` is retained in the return
tuple for backward compatibility and still reports skills dropped for
other reasons (32-char clamp collision vs a reserved name).

Returns:
    ``(categories, uncategorized, hidden_count)``

    - *categories*: ``{category_name: [(name, description, cmd_key), ...]}``
    - *uncategorized*: ``[(name, description, cmd_key), ...]``
    - *hidden_count*: skills dropped due to name clamp collisions
      against already-registered command names.

#### def `slack_native_slashes() -> list[tuple[str, str, str]]`

Return (slash_name, description, usage_hint) triples for Slack.

Every gateway-available command in ``COMMAND_REGISTRY`` is surfaced as
a standalone Slack slash command (e.g. ``/btw``, ``/stop``, ``/model``),
matching Discord's and Telegram's model where every command is a
first-class slash and not a ``/hermes <verb>`` subcommand.

Both canonical names and aliases are included so users can type any
documented form (e.g. ``/background``, ``/bg``, and ``/btw`` all work).
Plugin-registered slash commands are included too.

Commands whose sanitized name collides with a Slack built-in
(e.g. ``/status``, ``/me``, ``/join``) are silently skipped.  Users
can still reach them via ``/hermes <command>``.

Results are clamped to Slack's 50-command limit with duplicate-name
avoidance. ``/hermes`` is always reserved as the first entry so the
legacy ``/hermes <subcommand>`` form keeps working for anything that
gets dropped by the clamp or for free-form questions.

#### def `slack_app_manifest(request_url: str = 'https://hermes-agent.local/slack/commands') -> dict[str, Any]`

Generate a Slack app manifest with all gateway commands as slashes.

``request_url`` is required by Slack's manifest schema for every slash
command, but in Socket Mode (which we use) Slack ignores it and routes
the command event through the WebSocket. A placeholder URL is fine.

The returned dict is the ``features.slash_commands`` portion only —
callers compose it into a full manifest (or merge into an existing
one). Keeping it narrow avoids coupling us to the rest of the manifest
schema (display_information, oauth_config, settings, etc.) which users
set up once in the Slack UI and rarely change.

#### def `slack_subcommand_map() -> dict[str, str]`

Return subcommand -> /command mapping for Slack /hermes handler.

Maps both canonical names and aliases so /hermes bg do stuff works
the same as /hermes background do stuff.

Plugin-registered slash commands are included so ``/hermes <plugin-cmd>``
routes through the plugin handler.


## hermes_cli.completion

### 模块文档

Shell completion script generation for hermes CLI.

Walks the live argparse parser tree to generate accurate, always-up-to-date
completion scripts — no hardcoded subcommand lists, no extra dependencies.

Supports bash, zsh, and fish.

### 顶层函数

#### def `generate_bash(parser: argparse.ArgumentParser) -> str`

#### def `generate_zsh(parser: argparse.ArgumentParser) -> str`

#### def `generate_fish(parser: argparse.ArgumentParser) -> str`


## hermes_cli.config

### 模块文档

Configuration management for Hermes Agent.

Config files are stored in ~/.hermes/ for easy access:
- ~/.hermes/config.yaml  - All settings (model, toolsets, terminal, etc.)
- ~/.hermes/.env         - API keys and secrets

This module provides:
- hermes config          - Show current configuration
- hermes config edit     - Open config in editor
- hermes config get      - Print a resolved configuration value
- hermes config set      - Set a specific value
- hermes config unset    - Remove a user configuration value
- hermes config wizard   - Re-run setup wizard

### class ConfigIssue

> 继承: `object` ｜ 方法数: 0（公开 0）

A detected config structure problem.


### 顶层函数

#### def `get_managed_system() -> Optional[str]`

Return the package manager owning this install, if any.

#### def `is_managed() -> bool`

Check if Hermes is running in package-manager-managed mode.

Two signals: the HERMES_MANAGED env var (set by the systemd service),
or a .managed marker file in HERMES_HOME (set by the NixOS activation
script, so interactive shells also see it).

#### def `get_managed_update_command() -> Optional[str]`

Return the preferred upgrade command for a managed install.

#### def `detect_install_method(project_root: Optional[Path] = None) -> str`

Detect how Hermes was installed: 'docker', 'nixos', 'homebrew', 'git', or 'pip'.

Resolution order:
1. Code-scoped stamp ``<install tree>/.install_method`` (next to the
   running code) — the authoritative marker.
2. Legacy home-scoped stamp ``$HERMES_HOME/.install_method`` — read for
   backward compatibility, but a ``docker`` value is IGNORED when we are
   not actually running inside a container (see below).
3. HERMES_MANAGED env / .managed marker (NixOS, Homebrew)
4. .git directory presence -> 'git'
5. Fallback -> 'pip'

Why the stamp is code-scoped, not home-scoped (issue: shared ``~/.hermes``)
--------------------------------------------------------------------------
The install method describes *the binary that is running*, but
``$HERMES_HOME`` is a shared DATA directory — the Docker docs deliberately
bind-mount it (``~/.hermes:/opt/data``) so config/sessions/memory persist
and can be shared with a host-side Desktop/CLI install. When a
containerised gateway and a host install share one ``$HERMES_HOME``, a
home-scoped stamp is a single slot describing two different installs:
the container stamps ``docker`` on every boot, the host install then reads
``docker`` and ``hermes update`` refuses to run ("doesn't apply inside the
Docker container") even though the host binary is a perfectly updatable
git/pip install. Scoping the stamp to the install tree gives each install
its own truthful marker.

Self-healing for already-poisoned homes: a legacy ``docker`` value in the
home-scoped stamp is only honoured when we are genuinely in a container.
On a host install that read a contaminating ``docker`` stamp, we fall
through to managed/.git/pip detection instead — so existing shared-home
setups recover without the user touching anything.

Note: running inside a container is NOT treated as "docker" on its own.
The supported installs self-identify via the code-scoped stamp:
  - the curl installer (scripts/install.sh, the README/website install
    command) git-clones the repo and stamps ``git`` next to the code;
  - the published ``nousresearch/hermes-agent`` image bakes a ``docker``
    stamp into ``/opt/hermes`` at build time.
An unsupported manual install dropped into a container (no stamp) falls
through to the ``.git``/pip checks and behaves like any off-path install.
See issue #34397.

#### def `stamp_install_method(method: str, project_root: Optional[Path] = None) -> None`

Write the install method next to the running code (code-scoped stamp).

The stamp lives in the install tree (``<install tree>/.install_method``),
not in ``$HERMES_HOME``, so that two installs sharing one data directory
do not overwrite each other's marker. See ``detect_install_method`` for
the full rationale.

Best-effort: if the install tree is read-only (e.g. the immutable
``/opt/hermes`` in the published image, which instead bakes the stamp at
build time) the write silently no-ops and detection falls back to its
other signals.

#### def `is_uv_tool_install() -> bool`

Return True when the *running* Hermes lives in a ``uv tool`` layout.

``uv tool install hermes-agent`` places the install at
``.../uv/tools/hermes-agent/...`` (default ``~/.local/share/uv/tools``,
or ``$UV_TOOL_DIR/...``). Such installs live outside any virtualenv, so
``uv pip install`` fails with ``No virtual environment found`` and the
update path must use ``uv tool upgrade`` instead.

Detection is intentionally restricted to properties of the running
interpreter (``sys.prefix`` / ``sys.executable``). We deliberately do
NOT consult ``uv tool list``: it would also return True when
``hermes-agent`` happens to be uv-tool-installed on the machine while
the *active* Hermes is a regular pip/venv install, causing
``hermes update`` to upgrade the wrong copy. It would also block on a
subprocess call (~seconds) just to compute a recommendation string.

#### def `recommended_update_command_for_method(method: str) -> str`

Return the update command or guidance for a given install method.

#### def `recommended_update_command() -> str`

Return the best update command for the current installation.

#### def `is_unsupported_install_method(method: str) -> bool`

Whether ``method`` (from ``detect_install_method()``) is deprecated.

#### def `unsupported_install_method_label(method: str) -> str`

Human-readable name for an unsupported install method.

#### def `format_unsupported_install_warning(method: str) -> str`

Plain-text (no markup) deprecation notice for pip/Homebrew installs.

Shared verbatim across the CLI banner, TUI/desktop ``session.info``, and
``hermes update`` / ``hermes update --check`` so the wording — and the
docs link — stays consistent across every surface instead of drifting
into three slightly different warnings.

#### def `format_docker_update_message() -> str`

Return the user-facing message for ``hermes update`` inside Docker.

Centralised so ``cmd_update`` (the apply path) and ``_cmd_update_check``
(the dry-run path) share the same wording.  See ``_DOCKER_UPDATE_MESSAGE``
above for the full rationale.

#### def `format_managed_message(action: str = 'modify this Hermes installation') -> str`

Build a user-facing error for managed installs.

#### def `managed_error(action: str = 'modify configuration')`

Print user-friendly error for managed mode.

#### def `get_container_exec_info() -> Optional[dict]`

Read container mode metadata from HERMES_HOME/.container-mode.

Returns a dict with keys: backend, container_name, exec_user, hermes_bin
or None if container mode is not active, we're already inside the
container, or HERMES_DEV=1 is set.

The .container-mode file is written by the NixOS activation script when
container.enable = true. It tells the host CLI to exec into the container
instead of running locally.

#### def `get_config_path() -> Path`

Get the main config file path.

#### def `get_env_path() -> Path`

Get the .env file path (for API keys).

#### def `get_project_root() -> Path`

Get the project installation directory.

#### def `ensure_hermes_home()`

Ensure ~/.hermes directory structure exists with secure permissions.

In managed mode (NixOS), dirs are created by the activation script with
setgid + group-writable (2770). We skip mkdir and set umask(0o007) so
any files created (e.g. SOUL.md) are group-writable (0660).

Memoized per home path: this runs on EVERY ``load_config()`` (inside the
config lock), and the ~14 mkdir/chmod syscalls per call made repeated
config loads the dominant cost of hot read paths like ``model.options``.
After the first successful pass for a given ``HERMES_HOME`` we only re-run
the full walk if the home directory itself has vanished (a deleted home is
recreated on the next load, as before). Profile switches change
``get_hermes_home()`` and therefore re-run for the new path.

**异常**: `FileNotFoundError`

#### def `get_missing_env_vars(required_only: bool = False) -> List[Dict[str, Any]]`

Check which environment variables are missing.

Returns list of dicts with var info for missing variables.

#### def `clear_model_endpoint_credentials(model_cfg: Dict[str, Any], clear_api_key: bool = True, clear_api_mode: bool = True, clear_base_url: bool = False) -> Dict[str, Any]`

Remove stale inline endpoint credentials from a model config.

``model.api_key`` is valid only for explicit custom endpoint assignments.
Built-in providers resolve credentials from env vars, auth.json, or the
credential pool. When switching away from a custom endpoint, leaving these
fields behind keeps secrets in config.yaml and can contaminate later custom
resolution paths.

#### def `get_missing_config_fields() -> List[Dict[str, Any]]`

Check which config fields are missing or outdated (recursive).

Walks the DEFAULT_CONFIG tree at arbitrary depth and reports any keys
present in defaults but absent from the user's loaded config.

#### def `get_missing_skill_config_vars() -> List[Dict[str, Any]]`

Return skill-declared config vars that are missing or empty in config.yaml.

Scans all enabled skills for ``metadata.hermes.config`` entries, then checks
which ones are absent or empty under ``skills.config.<key>`` in the user's
config.yaml.  Returns a list of dicts suitable for prompting.

#### def `providers_dict_to_custom_providers(providers_dict: Any) -> List[Dict[str, Any]]`

Normalize ``providers`` config entries into the legacy custom-provider shape.

#### def `get_compatible_custom_providers(config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]`

Return a deduplicated custom-provider view across legacy and v12+ config.

``custom_providers`` remains the on-disk legacy format, while ``providers``
is the newer keyed schema.  Runtime and picker flows still need a single
list-shaped view, but we should not materialise that compatibility layer
back into config.yaml because it duplicates entries in UIs.

#### def `get_custom_provider_tls_settings(base_url: str, custom_providers: Optional[List[Dict[str, Any]]] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

Return TLS settings from a matching ``custom_providers`` / ``providers`` entry.

#### def `apply_custom_provider_tls_to_client_kwargs(client_kwargs: Dict[str, Any], base_url: str, custom_providers: Optional[List[Dict[str, Any]]] = None, config: Optional[Dict[str, Any]] = None) -> None`

Attach per-provider TLS knobs to OpenAI client kwargs when matched.

#### def `normalize_extra_headers(extra_headers: Any) -> Dict[str, str]`

Normalize a raw ``extra_headers`` value into a ``dict[str, str]``.

Stringifies keys and values and drops entries whose value is ``None``.
Returns ``{}`` for non-dict or empty inputs. This is the single shared
normalizer for per-provider ``extra_headers`` across config normalization,
runtime resolution, client construction, and live ``/models`` discovery.

SECURITY: header values routinely carry credentials (Cloudflare Access
service tokens, proxy auth, custom bearer schemes). Callers must never
log the returned values.

#### def `get_custom_provider_extra_headers(base_url: str, custom_providers: Optional[List[Dict[str, Any]]] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, str]`

Return ``extra_headers`` from a matching ``providers`` / ``custom_providers`` entry.

Matches the entry whose ``base_url`` equals *base_url* (trailing-slash and
case insensitive, mirroring :func:`get_custom_provider_tls_settings`) and
returns its ``extra_headers`` dict, or ``{}`` when no entry matches or the
entry declares none.

SECURITY: header values routinely carry credentials (Cloudflare Access
service tokens, proxy auth, custom bearer schemes). Callers must never
log the returned values.

#### def `apply_custom_provider_extra_headers_to_client_kwargs(client_kwargs: Dict[str, Any], base_url: str, custom_providers: Optional[List[Dict[str, Any]]] = None, config: Optional[Dict[str, Any]] = None) -> None`

Merge per-provider ``extra_headers`` onto OpenAI client ``default_headers``.

Provider-specific headers win over provider/SDK defaults already present in
``client_kwargs`` — they are the most specific configuration level. No-op
when the base_url matches no ``providers`` / ``custom_providers`` entry or
the entry declares no headers.

SECURITY: values may carry credentials — never log them.

#### def `get_custom_provider_context_length(model: str, base_url: str, custom_providers: Optional[List[Dict[str, Any]]] = None, config: Optional[Dict[str, Any]] = None) -> Optional[int]`

Look up a per-model ``context_length`` override from ``custom_providers``.

Matches any entry whose ``base_url`` equals ``base_url`` (trailing-slash
insensitive) and returns ``custom_providers[i].models.<model>.context_length``
if present and valid.  Returns ``None`` when no override applies.

This is the single source of truth for custom-provider context overrides,
used by:
  * ``AIAgent.__init__`` (startup resolution)
  * ``AIAgent.switch_model`` (mid-session ``/model`` switch)
  * ``hermes_cli.model_switch.resolve_display_context_length`` (``/model`` confirmation display)
  * ``gateway.run._format_session_info`` (``/info`` display)
  * ``agent.model_metadata.get_model_context_length`` (when custom_providers is threaded through)

Before this helper existed, the lookup was duplicated in ``run_agent.py``'s
startup path only; every other path (notably ``/model`` switch) fell back
to the 128K default.  See #15779.

#### def `check_config_version() -> Tuple[int, int]`

Check the raw on-disk config schema version.

``load_config()`` deliberately starts from ``DEFAULT_CONFIG`` and deep-merges
the user's file, which is correct for runtime reads but wrong for deciding
whether the user's persisted schema has been migrated. A config file with no
raw ``_config_version`` must remain visible as legacy instead of inheriting
the latest default version in memory.

Returns (current_version, latest_version).

#### def `validate_config_structure(config: Optional[Dict[str, Any]] = None) -> List['ConfigIssue']`

Validate config.yaml structure and return a list of detected issues.

Catches common YAML formatting mistakes that produce confusing runtime
errors (like "Unknown provider") instead of clear diagnostics.

Can be called with a pre-loaded config dict, or will load from disk.

#### def `print_config_warnings(config: Optional[Dict[str, Any]] = None) -> None`

Print config structure warnings to stderr at startup.

Called early in CLI and gateway init so users see problems before
they hit cryptic "Unknown provider" errors.  Prints nothing if
config is healthy.

#### def `warn_deprecated_cwd_env_vars(config: Optional[Dict[str, Any]] = None) -> None`

Warn if MESSAGING_CWD or TERMINAL_CWD is set in .env instead of config.yaml.

These env vars are deprecated — the canonical setting is terminal.cwd
in config.yaml.  Prints a migration hint to stderr.

#### def `migrate_config(interactive: bool = True, quiet: bool = False) -> Dict[str, Any]`

Migrate config to latest version, prompting for new required fields.

Args:
    interactive: If True, prompt user for missing values
    quiet: If True, suppress output
    
Returns:
    Dict with migration results: {"env_added": [...], "config_added": [...], "warnings": [...]}

#### def `is_provider_enabled(provider_cfg: Optional[Dict[str, Any]]) -> bool`

Return whether a ``providers.<name>`` config block is enabled.

A provider is enabled by default. Only an explicit ``enabled: false`` in
the block hides it from the model picker, ``/models`` listings, the
runtime resolver and the doctor / status output.

Backward-compat: configs without the ``enabled`` key keep working as
before — the default is ``True``.

Pass any non-dict (None, list, string) and you get ``True`` too, so
malformed entries don't disappear silently; they'll still be flagged
by the existing validation paths.

#### def `cfg_get(cfg: Optional[Dict[str, Any]], *keys: str, default: Any = None) -> Any`

Traverse nested dict keys safely, returning ``default`` on any miss.

Canonical helper for the ``cfg.get("X", {}).get("Y", default)`` pattern
that appears 50+ times across the codebase. Handles three common gotchas
in one place:

  1. Missing intermediate keys (returns ``default``, no KeyError).
  2. An intermediate value that's not a dict (e.g. a user wrote a string
     where a section was expected). Returns ``default`` instead of
     AttributeError on ``.get()``.
  3. ``cfg is None`` (callers sometimes pass ``load_config() or None``).

Named ``cfg_get`` rather than ``cfg_path`` to avoid shadowing the
ubiquitous ``cfg_path = _hermes_home / "config.yaml"`` local variable
that appears in gateway/run.py, cron/scheduler.py, main.py, etc.

Explicit ``None`` values are returned as-is (matches ``dict.get(key,
default)`` semantics — ``default`` is only returned when the key is
*absent*, not when it's present but set to ``None``).

Examples:
    >>> cfg_get({"agent": {"reasoning_effort": "high"}}, "agent", "reasoning_effort")
    'high'
    >>> cfg_get({}, "agent", "reasoning_effort", default="medium")
    'medium'
    >>> cfg_get({"agent": "oops_a_string"}, "agent", "reasoning_effort", default="low")
    'low'
    >>> cfg_get(None, "anything", default=42)
    42
    >>> cfg_get({"a": {"b": None}}, "a", "b", default="def")  # explicit None preserved
    >>> cfg_get({"a": {"b": False}}, "a", "b", default=True)  # falsy values preserved
    False

#### def `read_raw_config() -> Dict[str, Any]`

Read ~/.hermes/config.yaml as-is, without merging defaults or migrating.

Returns the raw YAML dict, or ``{}`` if the file doesn't exist or can't
be parsed.  Use this for lightweight config reads where you just need a
single value and don't want the overhead of ``load_config()``'s deep-merge
+ migration pipeline.

Cached on the config file's (mtime_ns, size) — same strategy as
``load_config()``. Returns a deepcopy on every call since some callers
mutate the result before passing to ``save_config()``.

#### def `require_readable_config_before_write(config_path: Optional[Path] = None) -> None`

Refuse to replace an existing config.yaml that cannot be read.

**异常**: `RuntimeError`

#### def `atomic_config_write(config_path: Path, data: Any, **kwargs: Any) -> None`

Fail-closed atomic write for ``config.yaml``.

The single chokepoint every config-update path should use instead of
calling :func:`utils.atomic_yaml_write` directly. It runs
:func:`require_readable_config_before_write` first, so a full-file
replacement can never silently clobber an existing ``config.yaml`` that
degraded to an empty dict on read (permission error, broken mount,
transient I/O). New-file creation still works when the path is absent.

Root cause this guards: ``read_raw_config()`` returns ``{}`` for BOTH an
absent file and an unreadable-but-present file. Callers that read then
overwrite can't tell the two apart, so an unreadable config would be
replaced with only defaults or the single edited section. Routing every
write through this helper enforces the invariant in one place rather than
relying on each of ~15 independent write sites to remember the guard.

``kwargs`` are forwarded verbatim to ``atomic_yaml_write``
(``sort_keys``, ``default_flow_style``, ``extra_content``, ...).

#### def `load_config() -> Dict[str, Any]`

Load configuration from ~/.hermes/config.yaml.

Cached on the config file's (mtime_ns, size). Returns a deepcopy of
the cached value when unchanged, since most call sites mutate the
result (e.g. ``cfg["model"]["default"] = ...`` before ``save_config``).
The cache is keyed on ``str(config_path)`` so profile switches
(which change ``HERMES_HOME`` and therefore ``get_config_path()``)
don't collide.

Read-only callers should use ``load_config_readonly()`` to skip the
defensive deepcopy — that path matters in agent-loop hot spots like
``get_provider_request_timeout`` which is called once per API turn.

#### def `load_config_readonly() -> Dict[str, Any]`

Fast-path variant of ``load_config()`` for callers that ONLY READ.

Returns the cached config dict directly without the defensive deepcopy
that ``load_config()`` applies. **Mutating the returned dict (or any
nested structure) corrupts the in-process cache for every subsequent
caller** — only use this when you are absolutely sure your code path
will not write to the result. If you need to mutate or pass to
``save_config``, call ``load_config()`` instead.

Why this exists: ``load_config()`` cache-hit cost is ~265us per call,
half of which (~135us) is the defensive deepcopy. The agent loop calls
into config reads (timeouts, thresholds, feature flags) ~20-50x per
conversation; skipping deepcopy here removes a measurable allocation
source and the GC pressure that comes with it.

Note: this returns a plain ``dict`` (not ``MappingProxyType``) so
existing ``isinstance(x, dict)`` guards downstream keep working. The
safety guarantee is purely documented, not enforced — be careful.

#### def `write_platform_config_field(platform_key: str, field_key: str, value: Any, raw: bool = False) -> None`

Persist one scalar field under ``platforms.<platform_key>``.

``raw=True`` preserves CLI setup flows that intentionally edit only the
user's raw config file. Dashboard routes use the default loaded-config path
so they retain their existing profile-scoped ``load_config`` behavior.

#### def `terminal_config_env_var_for_key(key: str) -> Optional[str]`

Return the env var mirrored by a ``terminal.*`` config key.

#### def `apply_terminal_config_to_env(env: Optional[Dict[str, str]] = None, config: Optional[Dict[str, Any]] = None, override: Optional[bool] = None) -> Dict[str, str]`

Bridge ``terminal.*`` config into the env vars terminal tools read.

``tools.terminal_tool`` is intentionally environment-driven because it also
runs in child processes (TUI, dashboard PTY, gateway workers).  This helper
gives those child-process launch paths the same config bridge as classic
CLI without importing ``cli.py`` and paying for its startup side effects.

When the user config contains a ``terminal`` section, config.yaml is
authoritative and overrides existing env values.  Otherwise defaults only
backfill missing env vars so exported/.env values keep working.

#### def `save_config(config: Dict[str, Any], strip_defaults: bool = True, preserve_keys: Optional[Set[Tuple[str, ...]]] = None, merge_existing: bool = False)`

Save configuration to ~/.hermes/config.yaml.


Default values from ``DEFAULT_CONFIG`` are not written to disk unless
the user explicitly set them (i.e. the path exists in the raw config
before any normalisation).  This prevents config.yaml from being
contaminated with schema defaults on every save, which makes future
default changes invisible to users.

When ``merge_existing`` is True, the on-disk raw config is deep-merged
under *config* before writing so partial callers (migration steps via
``_persist_migration``) cannot drop unrelated sections the caller omitted.
Full-document replacement callers (dashboard raw YAML editor, callers that
already deep-merge) must leave this False so intentional deletions survive.

#### def `load_env() -> Dict[str, str]`

Load environment variables from ~/.hermes/.env.

Sanitizes lines before parsing so that corrupted files (e.g.
concatenated KEY=VALUE pairs on a single line) are handled
gracefully instead of producing mangled values such as duplicated
bot tokens.  See #8908.

The parsed dict is memoised keyed on the .env file mtime, because
``get_env_value()`` is called dozens-to-hundreds of times per
interactive menu render (`hermes tools`, `hermes setup`, status
panels). Sanitisation is O(lines × known-keys), so re-parsing the
same file on every call was burning ~300ms of CPU per `hermes tools`
menu paint on top of the OAuth-refresh slowness. The mtime check
invalidates the cache when the user edits .env mid-process.

#### def `invalidate_env_cache() -> None`

Clear the load_env() process-level memo.

Writers that mutate .env (set_env_value, save_env, etc.) call this
to guarantee the next load_env() sees their change even on
filesystems with coarse mtime resolution. Reads invalidate naturally
via the mtime/size check.

#### def `sanitize_env_file() -> int`

Read, sanitize, and rewrite ~/.hermes/.env in place.

Returns the number of lines that were fixed (concatenation splits +
placeholder removals).  Returns 0 when no changes are needed.

#### def `save_env_value(key: str, value: str)`

Save or update a value in ~/.hermes/.env.

**异常**: `ValueError`

#### def `remove_env_value(key: str) -> bool`

Remove a key from ~/.hermes/.env and os.environ.

Returns True if the key was found and removed, False otherwise.

**异常**: `ValueError`

#### def `save_anthropic_oauth_token(value: str, save_fn = None)`

Persist an Anthropic OAuth/setup token and clear the API-key slot.

#### def `use_anthropic_claude_code_credentials(save_fn = None)`

Use Claude Code's own credential files instead of persisting env tokens.

#### def `save_anthropic_api_key(value: str, save_fn = None)`

Persist an Anthropic API key and clear the OAuth/setup-token slot.

#### def `save_env_value_secure(key: str, value: str) -> Dict[str, Any]`

#### def `reload_env() -> int`

Re-read ~/.hermes/.env into os.environ. Returns count of vars updated.

Adds/updates vars that changed and removes vars that were deleted from
the .env file (but only vars known to Hermes — OPTIONAL_ENV_VARS and
_EXTRA_ENV_KEYS — to avoid clobbering unrelated environment).

#### def `get_env_value(key: str) -> Optional[str]`

Get a value from ~/.hermes/.env or environment.

#### def `get_env_value_prefer_dotenv(key: str) -> Optional[str]`

Resolve a credential env value, preferring ``~/.hermes/.env`` over ``os.environ``.

Used for Hermes-managed credentials where a deliberate edit to ``.env``
must take precedence over a stale value inherited from the parent shell
(Codex CLI, test scripts, login profile exports). Without this, rotating
a key in ``.env`` mid-session leaves callers serving the stale shell
value and produces persistent 401s.

The ``os.environ`` fallback routes through ``secret_scope.get_secret`` so
that, under an active profile scope (multiplexed gateway turn), this read
is scope-checked rather than leaking another profile's raw ``os.environ``
value — matching the credential-pool seeding path's behaviour.

#### def `redact_key(key: str) -> str`

Redact an API key for display.

Thin wrapper over :func:`agent.redact.mask_secret` — preserves the
"(not set)" placeholder in dim color for the empty case.

#### def `redact_config_value(value: Any, _depth: int = 0) -> Any`

Return a copy of ``value`` with credential-shaped keys masked for display.

Recursively walks dicts/lists and replaces the value of any key in
``_SECRET_CONFIG_KEYS`` (case-insensitive) with a masked form via
:func:`agent.redact.mask_secret`. Non-secret keys and scalar values pass
through unchanged. Use this before ``print``-ing any config sub-tree that
might carry a custom-provider ``api_key`` — ``print`` bypasses the logging
redactor, and opaque tokens (e.g. Cloudflare ``cfut_...``) don't match the
vendor-prefix regexes either, so structural key-name masking is required.

#### def `show_config()`

Display current configuration.

#### def `edit_config()`

Open config file in user's editor.

#### def `set_config_value(key: str, value: str, force: bool = False)`

Set a configuration value.

Args:
    key: Dotted config path (e.g. ``terminal.backend``).
    value: String value (auto-coerced to bool/int/float when matching).
    force: When True, skip the unknown-key warning — useful for scripted
        writes of keys the running version doesn't recognize yet. The CLI
        exposes this via ``hermes config set --force``.

#### def `get_config_value(key: str, as_json: bool = False)`

Print a resolved configuration value.

#### def `unset_config_value(key: str)`

Remove a user-set configuration or .env value.

#### def `config_command(args)`

Handle config subcommands.


## hermes_cli.console_engine

### 模块文档

Safe Hermes Console command engine.

This module backs ``hermes console`` and is intentionally narrower than the
full Hermes CLI. It exposes a curated set of native adapters that can later be
shared by the dashboard console websocket without becoming a raw shell.

### class ConsoleCommandError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

User-facing console command failure.


### class ConsoleResult

> 继承: `object` ｜ 方法数: 0（公开 0）


### class ConsoleCommand

> 继承: `object` ｜ 方法数: 0（公开 0）


### class HermesConsoleEngine

> 继承: `object` ｜ 方法数: 11（公开 3）

Curated line-command executor for Hermes Console.

#### def `__init__(output_limit: int = 20000)`

#### def `execute(self, line: str, confirmed: bool = False) -> ConsoleResult`

**异常**: `ConsoleCommandError`

#### def `help_text(self, subject: str | None = None) -> str`

#### def `register(self, path: Iterable[str], usage: str, summary: str, handler: Callable[['HermesConsoleEngine', list[str]], str], mutating: bool = False, confirmation: str = '') -> None`


### 顶层函数

#### def `run_console_repl(stdin = None, stdout = None, stderr = None, interactive: bool | None = None) -> int`

Run the local ``hermes console`` REPL.


## hermes_cli.container_boot

### 模块文档

Container-boot reconciliation of per-profile gateway s6 services.

Service directories under /run/service/ live on **tmpfs** and are wiped
on every container restart. Profile directories under
``$HERMES_HOME/profiles/<name>/`` live on the persistent VOLUME, and
each one records its gateway's last state in ``gateway_state.json``.
This module bridges the two: on every container boot, walk the
persistent profiles, recreate the s6 service slots, and auto-start
only those whose last recorded state was ``running``.

Wired into the image as /etc/cont-init.d/02-reconcile-profiles by the
Dockerfile (Phase 4 Task 4.0). Runs as root after 01-hermes-setup
(the stage2 hook) has chowned the volume and seeded $HERMES_HOME, but
before s6-rc starts user services.

Without this module, every ``docker restart`` would silently wipe
every per-profile gateway, even though the user's profiles still
exist on disk.

### class ReconcileAction

> 继承: `object` ｜ 方法数: 0（公开 0）

One profile's outcome from a single reconciliation pass.


### 顶层函数

#### def `reconcile_profile_gateways(hermes_home: Path, scandir: Path, dry_run: bool = False, container_argv: Sequence[str] | None = None) -> list[ReconcileAction]`

Recreate s6 service registrations for every persistent profile.

Always registers a ``gateway-default`` slot for the root profile
(the implicit profile that lives at the top of ``$HERMES_HOME``,
not under ``profiles/``). The dispatcher in ``hermes_cli.gateway``
maps an empty profile suffix to ``gateway-default``, so this slot
is what ``hermes gateway start`` (no ``-p``) targets. Without it,
bare ``hermes gateway start`` inside the container would land on
``s6-svc -u /run/service/gateway-default`` → uncaught
``CalledProcessError`` → traceback to the user (PR #30136 review).

The default slot's prior state is read from
``$HERMES_HOME/gateway_state.json`` (sibling to the profile root,
not under ``profiles/``); stale runtime files there are swept the
same way as for named profiles.

Args:
    hermes_home: The container's HERMES_HOME (typically /opt/data).
        Profiles live under ``<hermes_home>/profiles/<name>/``;
        the default profile lives at ``<hermes_home>`` itself.
    scandir: The s6 dynamic scandir (typically /run/service). Service
        directories are created at ``<scandir>/gateway-<profile>/``.
    dry_run: When True, walk and return the action list without
        touching the filesystem. For tests and `--dry-run` debug.
    container_argv: Optional container PID 1 argv override. Production
        reads ``/proc/1/cmdline``; tests inject it directly.

Returns:
    One :class:`ReconcileAction` per profile, in this order:
    ``default`` first, then named profiles in directory order.

#### def `main() -> int`

Entry point invoked from /etc/cont-init.d/02-reconcile-profiles.


## hermes_cli.context_switch_guard

### 模块文档

Warn when an in-session model switch will trigger preflight compression on the next turn.

Addresses part of #23767 ("user-facing guardrail when switching from a
high-context provider to a substantially lower-context provider"). The other
proposed fixes from that issue (hard preflight token guard, metadata cache
invalidation on switch, compression safety invariant, oversized tool-output
handling) are tracked separately.

Mirrors the expensive-model guard pattern: merge into ``ModelSwitchResult.warning_message``
so Herm TUI, CLI, and gateway surfaces that already show switch warnings pick it up.

### 顶层函数

#### def `merge_preflight_compression_warning(result: ModelSwitchResult, agent: Any = None, messages: Optional[List[dict]] = None, custom_providers: list | None = None, config_context_length: int | None = None) -> None`

If the next user message will likely preflight-compress, append a warning.

#### def `enrich_model_switch_warnings_for_gateway(result: ModelSwitchResult, runner: Any, session_key: str, source: Any, custom_providers: list | None = None, load_gateway_config: Callable[[], dict] | None = None) -> None`

Gateway helper: cached agent + session DB messages.


## hermes_cli.copilot_auth

### 模块文档

GitHub Copilot authentication utilities.

Implements the OAuth device code flow used by the Copilot CLI and handles
token validation/exchange for the Copilot API.

Token type support (per GitHub docs):
  gho_          OAuth token           ✓  (default via copilot login)
  github_pat_   Fine-grained PAT      ✓  (needs Copilot Requests permission)
  ghu_          GitHub App token      ✓  (via environment variable)
  ghp_          Classic PAT           ✗  NOT SUPPORTED

Credential search order (matching Copilot CLI behaviour):
  1. COPILOT_GITHUB_TOKEN env var
  2. GH_TOKEN env var
  3. GITHUB_TOKEN env var
  4. gh auth token  CLI fallback

### 顶层函数

#### def `validate_copilot_token(token: str) -> tuple[bool, str]`

Validate that a token is usable with the Copilot API.

Returns (valid, message).

#### def `resolve_copilot_token() -> tuple[str, str]`

Resolve a GitHub token suitable for Copilot API use.

Returns (token, source) where source describes where the token came from.
Raises ValueError if only a classic PAT is available.

**异常**: `ValueError`

#### def `copilot_device_code_login(host: str = 'github.com', timeout_seconds: float = 300) -> Optional[str]`

Run the GitHub OAuth device code flow for Copilot.

Prints instructions for the user, polls for completion, and returns
the OAuth access token on success, or None on failure/cancellation.

This replicates the flow used by opencode and the Copilot CLI.

#### def `exchange_copilot_token(raw_token: str, timeout: float = 10.0) -> tuple[str, float, Optional[str]]`

Exchange a raw GitHub token for a short-lived Copilot API token.

Calls ``GET https://api.github.com/copilot_internal/v2/token`` with
the raw GitHub token and returns ``(api_token, expires_at, base_url)``.

The returned token is a semicolon-separated string (not a standard JWT)
used as ``Authorization: Bearer <token>`` for Copilot API requests.
``base_url`` is the account-specific API host: the authoritative
``endpoints.api`` advertised by the exchange (enterprise/proxied
accounts), falling back to a host derived from the token's ``proxy-ep``
field. Individual accounts have neither, so ``base_url`` is None.

Results are cached in-process and reused until close to expiry.
Raises ``ValueError`` on failure.

**异常**: `ValueError`

#### def `get_copilot_api_token(raw_token: str) -> tuple[str, Optional[str]]`

Exchange a raw GitHub token for a Copilot API token, with fallback.

Convenience wrapper: returns ``(api_token, base_url)`` on success, or
``(raw_token, None)`` if the exchange fails (e.g. network error, unsupported
account type). This preserves existing behaviour for accounts that don't
need exchange while enabling access to internal-only models for those that do.

``base_url`` is the account-specific API endpoint advertised by the
exchange (``endpoints.api``, with a ``proxy-ep`` fallback), or None for
individual accounts.

#### def `copilot_request_headers(is_agent_turn: bool = True, is_vision: bool = False) -> dict[str, str]`

Build the standard headers for Copilot API requests.

Replicates the header set used by opencode and the Copilot CLI.


## hermes_cli.credential_lifecycle

### 模块文档

Unified provider-credential lifecycle across every store Hermes reads.

A provider API key can live in up to THREE stores at once:

    1. ``~/.hermes/.env``                     — the canonical secret store
    2. ``~/.hermes/auth.json`` →
       ``credential_pool.<provider>[*]``      — env-seeded pool entries
       (``source == "env:<VAR>"``) persisted by the pool loader
    3. ``~/.hermes/config.yaml``              — inline mirrors written by the
       custom-endpoint flows (``model.api_key``, ``auxiliary.<task>.api_key``,
       ``custom_providers[*].api_key``)

Historically the desktop/dashboard endpoints (PUT/DELETE ``/api/env``) and the
TUI-gateway RPCs only mutated store 1. That divergence is the root cause of a
whole bug family:

    * #51071 / #59761 — deleting a key removes it from ``.env`` but the stale
      ``credential_pool`` entry (and ``provider_models_cache.json`` row)
      survives, so the provider keeps appearing in the model picker, even
      across restarts (the pool loader is additive-only).
    * #62269 — updating a key rewrites ``.env`` but leaves the OLD key in a
      higher-precedence ``config.yaml`` mirror (``model.api_key`` wins over
      env at client construction), producing persistent 401s with a key the
      UI no longer shows.

This module is the single choke point: every surface that saves or removes a
provider credential should route through :func:`save_provider_env_credential`
/ :func:`remove_provider_env_credential` so all three stores stay consistent.

OAuth preservation contract: removal only prunes credential-pool entries whose
``source`` is exactly ``env:<VAR>``. OAuth/device-code/manual/borrowed entries
(``device_code``, ``manual*``, ``gh_cli``, ``claude_code``, ``oauth``, …) and
the ``providers.<id>`` OAuth token blocks in auth.json are never touched —
deleting an API key must not revoke an OAuth grant for the same provider.

Secrecy contract: no function in this module logs, prints, or returns a
credential value. Results carry key NAMES and config PATHS only.

### 顶层函数

#### def `purge_env_credential_references(env_var: str, clear_models_cache: bool = True) -> Dict[str, Any]`

Remove non-.env references to an env-var credential.

Prunes ``credential_pool`` env-seeded entries and (optionally) the
affected providers' rows in ``provider_models_cache.json`` so the model
picker stops advertising a provider whose key is gone (#59761).

#### def `save_provider_env_credential(env_var: str, value: str) -> Dict[str, Any]`

Save/update a credential in ``.env`` and reconcile every mirror.

After the ``.env`` write, any config.yaml mirror that held the PREVIOUS
value of this var (``model.api_key`` etc.) is updated to the new value so
a stale higher-precedence copy cannot shadow the rotation (#62269).
Suppressed ``env:<VAR>`` pool sources are re-enabled so a deliberate
re-add through the UI behaves like ``hermes auth add``.

#### def `remove_provider_env_credential(env_var: str) -> Dict[str, Any]`

Remove a credential from EVERY store it lives in.

Clears the ``.env`` entry (and process env), prunes env-seeded
``credential_pool`` entries, drops the affected providers' model-cache
rows, and removes any config.yaml mirror holding the same value.
OAuth/device-code/manual credentials are preserved (see module docstring).

``found`` is True when ANY store held the credential — callers that
previously 404'd on ".env miss" should key off this instead so a stale
pool-only entry can still be cleaned up through the same button.


## hermes_cli.cron

### 模块文档

Cron subcommand for hermes CLI.

Handles standalone cron management commands like list, create, edit,
pause/resume/run/remove, status, and tick.

### 顶层函数

#### def `cron_list(show_all: bool = False)`

List all scheduled jobs.

#### def `cron_tick()`

Run due jobs once and exit.

#### def `cron_runs(job_id: Optional[str] = None, limit: int = 20)`

Show indexed durable cron execution history.

#### def `cron_status()`

Show cron execution status.

#### def `cron_create(args)`

#### def `cron_edit(args)`

#### def `cron_command(args)`

Handle cron subcommands.


## hermes_cli.curator

### 模块文档

CLI subcommand: `hermes curator <subcommand>`.

Thin shell around agent/curator.py and tools/skill_usage.py. Renders a status
table, triggers a run, pauses/resumes, and pins/unpins skills.

This module intentionally has no side effects at import time — main.py wires
the argparse subparsers on demand.

### 顶层函数

#### def `register_cli(parent: argparse.ArgumentParser) -> None`

Attach `curator` subcommands to *parent*.

main.py calls this with the ArgumentParser returned by
``subparsers.add_parser("curator", ...)``.

#### def `cli_main(argv = None) -> int`

Standalone entry (also usable by hermes_cli.main fallthrough).


## hermes_cli.curses_ui

### 模块文档

Shared curses-based UI components for Hermes CLI.

Used by `hermes tools` and `hermes skills` for interactive checklists.
Provides a curses multi-select with keyboard navigation, plus a
text-based numbered fallback for terminals without curses support.

### 顶层函数

#### def `flush_stdin() -> None`

Flush any stray bytes from the stdin input buffer.

Must be called after ``curses.wrapper()`` (or any terminal-mode library
like simple_term_menu) returns, **before** the next ``input()`` /
``getpass.getpass()`` call.  ``curses.endwin()`` restores the terminal
but does NOT drain the OS input buffer — leftover escape-sequence bytes
(from arrow keys, terminal mode-switch responses, or rapid keypresses)
remain buffered and silently get consumed by the next ``input()`` call,
corrupting user data (e.g. writing ``^[^[`` into .env files).

On non-TTY stdin (piped, redirected) or Windows, this is a no-op.

#### def `read_menu_key(stdscr) -> str`

Read one keypress and normalize it to a menu action.

Decodes raw arrow-key escape sequences in addition to the translated
``curses.KEY_*`` values.  Even with ``keypad(True)`` (which
``curses.wrapper`` sets), some terminals/terminfo entries deliver cursor
keys as raw CSI/SS3 byte sequences — ``getch()`` then returns ``27`` (ESC)
followed by e.g. ``[`` ``A``.  Treating that leading ``27`` as a cancel is
what made the setup wizard's provider/model pickers bail to the numbered
fallback the moment a user pressed up/down.

Returns one of the ``NAV_*`` constants.  A lone ESC (no continuation byte
within a short window) is the only thing that maps to ``NAV_CANCEL`` via
the escape path; ``q`` also cancels.  Unknown sequences map to
``NAV_NONE`` so the caller simply ignores them rather than misfiring.

#### def `curses_checklist(title: str, items: List[str], selected: Set[int], cancel_returns: Set[int] | None = None, status_fn: Optional[Callable[[Set[int]], str]] = None) -> Set[int]`

Curses multi-select checklist. Returns set of selected indices.

Args:
    title: Header line displayed above the checklist.
    items: Display labels for each row.
    selected: Indices that start checked (pre-selected).
    cancel_returns: Returned on ESC/q. Defaults to the original *selected*.
    status_fn: Optional callback ``f(chosen_indices) -> str`` whose return
        value is rendered on the bottom row of the terminal.  Use this for
        live aggregate info (e.g. estimated token counts).

#### def `curses_radiolist(title: str, items: List[str], selected: int = 0, cancel_returns: int | None = None, description: str | None = None, searchable: bool = False) -> int`

Curses single-select radio list. Returns the selected index.

Args:
    title: Header line displayed above the list.
    items: Display labels for each row.
    selected: Index that starts selected (pre-selected).
    cancel_returns: Returned on ESC/q. Defaults to the original *selected*.
    description: Optional multi-line text shown between the title and
        the item list.  Useful for context that should survive the
        curses screen clear.
    searchable: When true, ``/`` opens a type-to-filter prompt. The
        returned value is always the original item index, not a filtered
        row position.

#### def `curses_single_select(title: str, items: List[str], default_index: int = 0, cancel_label: str = 'Cancel', searchable: bool = False) -> int | None`

Curses single-select menu. Returns selected index or None on cancel.

Works inside prompt_toolkit because curses.wrapper() restores the terminal
safely, unlike simple_term_menu which conflicts with /dev/tty.

When ``searchable`` is true, ``/`` opens a type-to-filter prompt; the
returned value is always the original item index (or None for cancel).


## hermes_cli.dashboard_auth.__init__

### 模块文档

Dashboard authentication provider framework.

The dashboard auth gate engages only when the dashboard binds to a
non-loopback host without ``--insecure``. In that mode, every request must
carry a verified session from one of the registered ``DashboardAuthProvider``
plugins.

The Nous provider lives in ``plugins/dashboard-auth-nous/`` and is the
default. Third parties register their own providers via the plugin hook
``ctx.register_dashboard_auth_provider``.

## hermes_cli.dashboard_auth.audit

### 模块文档

Audit log for dashboard-auth events.

Profile-aware location: ``$HERMES_HOME/logs/dashboard-auth.log``.
Format: one JSON object per line. Token-like fields are stripped before
serialisation to avoid leaking refresh tokens or JWTs to disk.

This module deliberately keeps a minimal dependency surface — no imports
from ``hermes_constants`` or other hermes_cli modules — so it can be
imported safely from middleware code that loads early in the startup
sequence.

### class AuditEvent

> 继承: `enum.Enum` ｜ 方法数: 0（公开 0）

Event types written to dashboard-auth.log.

Values are the literal ``event`` field on the JSON line.


### 顶层函数

#### def `audit_log(event: AuditEvent, **fields: Any) -> None`

Append one event to the audit log.

Token-like fields are dropped. Missing log directory is created.
Write failures are logged at WARNING but never raise — auth must not
fail because the audit logger broke.


## hermes_cli.dashboard_auth.base

### 模块文档

Abstract base + dataclasses + exceptions for dashboard auth providers.

### class Session

> 继承: `object` ｜ 方法数: 0（公开 0）

A verified identity. Returned by ``complete_login`` and ``verify_session``.

All fields are mandatory. Providers that don't have a concept of orgs
should set ``org_id`` to an empty string. ``access_token`` and
``refresh_token`` are opaque to Hermes — provider-specific.


### class TokenPrincipal

> 继承: `object` ｜ 方法数: 0（公开 0）

A verified non-interactive (service-to-service) caller.

The token analog of :class:`Session`. Where a ``Session`` represents an
interactive human identity behind a session cookie, a ``TokenPrincipal``
represents a machine/service caller that authenticated by presenting a
bearer token in the ``Authorization`` request header on a single
request — no login, no cookie, no refresh.

Returned by :meth:`DashboardAuthProvider.verify_token` and attached to
``request.state.token_principal`` by the token-auth middleware seam so a
route handler can see *who* called it.

Fields:
  * ``principal`` — stable identifier for the caller (e.g. the provider
    name, a service account id, or an agent id). Opaque to the seam.
  * ``provider`` — the ``name`` of the provider that verified the token.
  * ``scopes`` — capability strings this principal is authorised for.
    Empty tuple means "unscoped" (the provider vouches for the caller but
    attaches no capability list); a route MAY enforce a required scope.


### class LoginStart

> 继承: `object` ｜ 方法数: 0（公开 0）

First leg of the OAuth round trip.

``redirect_url`` is the URL the browser must navigate to (e.g. the
Portal's ``/oauth/authorize``). ``cookie_payload`` is a dict of cookie
name → serialised value that the auth route will ``Set-Cookie`` on the
response. Used for PKCE state, CSRF nonces, etc. Cookies set here MUST
be HttpOnly + Secure (when over HTTPS) + SameSite=Lax with a TTL ≤ 10
minutes (the login lifetime).


### class ProviderError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

IDP unreachable, network error, or other transient failure.

Middleware translates this to HTTP 503.


### class InvalidCodeError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

The OAuth callback ``code`` / ``state`` failed validation.

Middleware translates this to HTTP 400.


### class InvalidCredentialsError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

A username/password pair was rejected by a password provider.

Raised by :meth:`DashboardAuthProvider.complete_password_login`. The
``/auth/password-login`` route translates this to HTTP 401 with a
deliberately generic detail (never distinguishing "unknown user" from
"wrong password") so the endpoint can't be used as a username oracle.


### class RefreshExpiredError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

This provider rejects the refresh token as dead or invalid.

In a multi-provider deployment this does not prove token ownership, so
middleware may try remaining providers. It clears cookies and forces
re-login only after every reachable provider rejects the token.


### class DashboardAuthProvider

> 继承: `ABC` ｜ 方法数: 7（公开 7）

Protocol every dashboard-auth provider plugin implements.

Lifecycle:
  1. ``start_login`` — user clicks "Log in with X" on the login page.
     Provider returns a redirect URL and any PKCE/CSRF state to stash
     in short-lived cookies.
  2. Browser bounces through the OAuth IDP and lands at /auth/callback.
  3. ``complete_login`` — exchange the code + verifier for a Session.
  4. ``verify_session`` — called on every request to validate the
     access token in the cookie. Returns ``None`` if the token is
     expired or invalid (middleware then triggers refresh or logout).
  5. ``refresh_session`` — called when the access token is near expiry.
     Returns a new Session with rotated tokens.
  6. ``revoke_session`` — called on /auth/logout. Best-effort.

Failure semantics:
  * ``start_login`` may raise ``ProviderError`` if the IDP is
    unreachable.
  * ``complete_login`` raises ``InvalidCodeError`` on bad code/state;
    ``ProviderError`` if the IDP is unreachable.
  * ``verify_session`` returns ``None`` on expiry / unknown token;
    raises ``ProviderError`` if the IDP is unreachable. Middleware
    treats expiry and unreachable differently (expiry → refresh;
    unreachable → 503).
  * ``refresh_session`` raises ``RefreshExpiredError`` when the refresh
    token is invalid for that provider. Middleware tries the remaining
    providers because an opaque foreign token can be indistinguishable
    from an expired one; it forces re-login only after every reachable
    provider rejects the token. Raises ``ProviderError`` on network
    failure; middleware still tries remaining providers, but returns 503
    without clearing cookies if none succeeds and any was unavailable.
  * ``revoke_session`` is best-effort and must not raise.

Subclasses MUST set ``name`` (lowercase identifier, stable forever)
and ``display_name`` (user-facing label on the login page).

Password (non-redirect) providers:
  A provider that authenticates with a username + password instead of
  an OAuth redirect sets ``supports_password = True`` and implements
  ``complete_password_login``. The login page then renders a
  credential form (POSTing to ``/auth/password-login``) instead of a
  "Log in with X" redirect button. Everything downstream of login —
  ``verify_session`` / ``refresh_session`` / ``revoke_session``, the
  session cookies, the WS-ticket mint — is identical to the OAuth
  path, because a password session is just a :class:`Session` with
  provider-minted opaque tokens. The OAuth methods (``start_login`` /
  ``complete_login``) remain abstract; a pure-password provider that
  will never be reached via the redirect flow may implement them as
  stubs that raise ``NotImplementedError``.

#### def `start_login(self, redirect_uri: str) -> LoginStart`

#### def `complete_login(self, code: str, state: str, code_verifier: str, redirect_uri: str) -> Session`

#### def `verify_session(self, access_token: str) -> Optional[Session]`

#### def `refresh_session(self, refresh_token: str) -> Session`

#### def `revoke_session(self, refresh_token: str) -> None`

#### def `complete_password_login(self, username: str, password: str) -> Session`

Verify a username/password pair and mint a :class:`Session`.

Only called when ``supports_password`` is True (the
``/auth/password-login`` route guards on the flag). The default
raises ``NotImplementedError`` so an OAuth-only provider that
forgets to set the flag fails loudly rather than silently
accepting credentials.

The returned ``Session`` carries provider-minted opaque
``access_token`` / ``refresh_token`` exactly like the OAuth path,
so all downstream session handling (cookies, verify, refresh,
ws-tickets, logout) is identical.

Failure semantics:
  * ``InvalidCredentialsError`` — username/password rejected. The
    route surfaces a generic 401 (no user-vs-password
    distinction). Implementations SHOULD spend constant time on
    unknown users (dummy hash verify) to avoid a timing oracle.
  * ``ProviderError`` — the backing credential store is
    unreachable (LDAP/DB down); the route surfaces 503.

**异常**: `NotImplementedError`

#### def `verify_token(self, token: str) -> Optional[TokenPrincipal]`

Verify a non-interactive bearer token; return its principal.

The token analog of ``verify_session``. Only consulted when
``supports_token`` is True. Called by the ``token_auth`` middleware
seam for every request to a token-authable route, in registration
order, until one provider returns a non-None principal.

Contract (mirrors ``verify_session`` stacking semantics):
  * Return a :class:`TokenPrincipal` if this provider recognises and
    accepts the token.
  * Return ``None`` for a token this provider does NOT recognise —
    never raise, so the seam can fall through to the next provider.
    A malformed/expired/wrong token is "not recognised" → ``None``.
  * Raise ``ProviderError`` ONLY for a genuine backing-store outage
    (the provider can neither confirm nor deny). The seam treats this
    like ``verify_session``: remember it, keep trying other providers,
    and surface 503 only if NO provider accepts the token AND at least
    one was unreachable.

Implementations MUST use a constant-time comparison
(``hmac.compare_digest``) when matching a shared secret so the
endpoint isn't a timing oracle.

The default raises ``NotImplementedError`` so a provider that sets
``supports_token`` but forgets to implement this fails loudly rather
than silently accepting every caller.

**异常**: `NotImplementedError`


### 顶层函数

#### def `assert_protocol_compliance(cls: type) -> None`

Raise ``TypeError`` if ``cls`` doesn't fully implement the provider protocol.

Call this in every provider plugin's unit tests::

    def test_protocol_compliance():
        assert_protocol_compliance(MyProvider)

Returns ``None`` on success so callers can assert it explicitly.

**异常**: `TypeError`


## hermes_cli.dashboard_auth.cookies

### 模块文档

Cookie helpers for dashboard auth.

Three cookies in play:
  - hermes_session_at:   the OAuth access token
                         (HttpOnly, lifetime = token TTL, ~15 min)
  - hermes_session_rt:   the OAuth refresh token
                         (HttpOnly, lifetime = 24h, ROTATING + reuse-detected)
                         Nous Portal issues a rotating refresh token for the
                         dashboard auth-code grant (Portal NAS #293 / hermes
                         #37247). ``set_session_cookies`` writes this cookie
                         whenever the provider returns a non-empty
                         ``refresh_token``; the middleware uses it to rotate a
                         fresh access token transparently on AT expiry. A
                         provider that omits the refresh token (empty string)
                         degrades gracefully to access-token-only sessions —
                         the RT cookie is simply not written.
  - hermes_session_pkce: short-lived PKCE state + CSRF nonce + provider
                         hint (HttpOnly, lifetime = 10 minutes)

All three are ``SameSite=Lax`` (browser will send on cross-site GET
top-level navigation, which we need for the IDP redirect back to
``/auth/callback``) and live under the prefix's Path. ``Secure`` is set
ONLY when the dashboard was reached over HTTPS — detected via the
request URL scheme, which honours ``X-Forwarded-Proto`` upstream of
Fly's TLS terminator when uvicorn is configured with
``proxy_headers=True``. Loopback dev traffic is always HTTP so
``Secure`` would lock the cookies out of the browser.

Cookie prefix selection (browser hardening per
https://datatracker.ietf.org/doc/html/draft-west-cookie-prefixes):

  * Loopback HTTP — bare name. ``__Host-`` / ``__Secure-`` require
    ``Secure``, which is incompatible with HTTP.
  * Gated HTTPS, direct deploy (Path=/) — ``__Host-`` prefix. Binds the
    cookie to the exact origin (no Domain attribute) — strongest spec
    guarantee.
  * Gated HTTPS, behind a reverse-proxy prefix (Path=/hermes) —
    ``__Secure-`` prefix. ``__Host-`` is disallowed when Path != "/";
    ``__Secure-`` keeps the Secure-required hardening without the
    Path constraint, and the explicit ``Path=/hermes`` covers
    same-origin app isolation.

The setters and readers BOTH consult the active prefix because the
cookie *name* changes — a reader that looked up the bare name when the
setter wrote ``__Secure-hermes_session_at`` would never find the value.

Refresh-token handling:
   ``set_session_cookies`` accepts ``refresh_token=""`` (provider omitted
   it) and silently skips writing the RT cookie in that case, so a
   refresh-token-less provider degrades to access-token-only sessions.
   ``clear_session_cookies`` always emits a Max-Age=0 deletion for the RT
   cookie on logout / session expiry so a stale cookie from an earlier
   deployment gets cleared. The transparent rotation flow ("expired AT +
   live RT → rotate server-side, else 401 → /login") lives in
   ``middleware._attempt_refresh``.

### 顶层函数

#### def `set_session_provider_cookie(response: Response, provider: str, use_https: bool, prefix: str = '') -> None`

Persist the non-secret provider routing hint for token refresh.

#### def `set_session_cookies(response: Response, access_token: str, refresh_token: str, access_token_expires_in: int, use_https: bool, prefix: str = '', provider: str = '') -> None`

Set the session cookies on the response.

``access_token_expires_in`` is in seconds. Use the provider's reported
TTL for the access token.

``refresh_token`` is written as the RT cookie when non-empty. Nous Portal
issues a 24h rotating refresh token (hermes #37247); a provider that
omits it returns ``Session.refresh_token == ""`` and we simply don't
persist the RT cookie — the session then behaves as access-token-only
until the AT expires. No other branch changes between the two cases.

``prefix`` is the normalised X-Forwarded-Prefix value (e.g. ``/hermes``)
or ``""`` for a direct deploy. It influences both the cookie name
(``__Host-`` vs ``__Secure-`` vs bare) and the ``Path`` attribute.

#### def `clear_session_cookies(response: Response, prefix: str = '') -> None`

Emit Max-Age=0 deletions for both session cookies.

To delete a cookie reliably the deletion's ``Path`` must match the
set path AND the cookie name must match the variant the setter used.
We don't know which variant was originally set (cookie prefix
depends on the request that set it), so we emit deletions for every
plausible variant under the active path.

#### def `set_pkce_cookie(response: Response, payload: str, use_https: bool, prefix: str = '') -> None`

#### def `clear_pkce_cookie(response: Response, prefix: str = '') -> None`

#### def `read_session_cookies(request: Request) -> Tuple[Optional[str], Optional[str]]`

Returns (access_token, refresh_token), either may be None.

#### def `read_session_provider(request: Request) -> Optional[str]`

Return the provider routing hint associated with the session cookies.

#### def `read_pkce_cookie(request: Request) -> Optional[str]`

#### def `set_sso_attempt_cookie(response: Response, use_https: bool, prefix: str = '') -> None`

Set the one-shot auto-SSO loop-guard marker (Phase 1).

Written by the gate the moment it auto-initiates the portal OAuth
redirect on an unauthenticated document load. The value is a constant
(``"1"``) — only its presence matters. Short Max-Age so a stale marker
can't permanently suppress a future silent attempt.

#### def `read_sso_attempt_cookie(request: Request) -> Optional[str]`

Return the auto-SSO marker value if present (any variant), else None.

#### def `clear_sso_attempt_cookie(response: Response, prefix: str = '') -> None`

Emit Max-Age=0 deletions for the auto-SSO marker, every name variant.

Called on a successful callback and whenever the gate falls back to
/login, so the marker never lingers to suppress a later silent attempt.

#### def `detect_https(request: Request) -> bool`

Decide whether to set the ``Secure`` cookie flag.

Reads ``request.url.scheme`` — under uvicorn's ``proxy_headers=True``
(which start_server enables when the gate is active), this honours
``X-Forwarded-Proto`` from Fly's TLS terminator. Loopback traffic is
always HTTP so this returns False there.


## hermes_cli.dashboard_auth.login_page

### 模块文档

Server-rendered /login page.

No React, no JavaScript dependency. Listed providers come from the
registry; clicking a provider sends a GET to
``/auth/login?provider=<name>``.

Visual styling mirrors the Nous Research design system (the
``@nous-research/ui`` package the React dashboard uses): the same
``Collapse`` / ``Rules Compressed`` typeface, amber-on-dark colour
tokens (``#170d02`` / ``#ffac02`` / ``#fff``), uppercase + wide-tracking
brand chrome, and the inset-bevel button shadow. Fonts are served
out of the SPA's ``/fonts/`` directory which the dashboard-auth gate
already allowlists pre-auth (see ``_GATE_PUBLIC_PREFIXES`` in
``middleware.py``), so the page renders without needing the React
bundle loaded.

Test-stable class names: the existing test suite extracts the
``class="provider-btn"`` anchor href to walk the OAuth flow. That
class name MUST NOT change without updating
``tests/hermes_cli/test_dashboard_auth_401_reauth.py``.

### 顶层函数

#### def `render_login_html(next_path: str = '') -> str`

Return the full HTML for ``GET /login``.

``next_path`` — when set, the post-login landing path the user
originally requested. Threaded into each provider button's ``href``
as a ``next=`` query parameter so the OAuth round trip carries it
end-to-end. The caller (``routes.login_page``) is responsible for
validating ``next_path`` against the same-origin rules before we
emit it; we still HTML-escape it as defence in depth.


## hermes_cli.dashboard_auth.middleware

### 模块文档

Auth-gate middleware for the dashboard.

Engaged when ``app.state.auth_required is True``. The gate's job:

  1. Allow a small set of routes through unauthenticated (login page,
     ``/auth/*`` OAuth round trip, ``/api/auth/providers``, static
     assets).
  2. For everything else, demand a valid session cookie and attach the
     verified :class:`Session` to ``request.state.session``.
  3. On HTML routes, redirect missing/invalid cookies to ``/login``.
     On ``/api/*`` routes, return 401 JSON.

The middleware is a no-op when ``auth_required`` is False (loopback
mode); the legacy ``_SESSION_TOKEN`` ``auth_middleware`` handles those
binds.

### 顶层函数

#### def `gated_auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response`

Engaged only when ``app.state.auth_required is True``.

No-op pass-through in loopback mode so the legacy auth_middleware can
handle those binds via ``_SESSION_TOKEN``.


## hermes_cli.dashboard_auth.prefix

### 模块文档

Helpers for X-Forwarded-Prefix support.

Mission-control style deploys reverse-proxy the dashboard at a path
prefix (e.g. ``mission-control.tilos.com/hermes/*`` -> dashboard on
:9119), injecting ``X-Forwarded-Prefix: /hermes`` so the backend can
reconstruct prefixed URLs (Location: headers, OAuth redirect_uri,
cookie Path attributes, SPA asset URLs).

This module is also the home of the ``HERMES_DASHBOARD_PUBLIC_URL`` /
``dashboard.public_url`` resolution — when the operator declares a
complete public URL (scheme + host + optional path prefix), we use
that directly for the OAuth ``redirect_uri`` and skip the
X-Forwarded-Prefix reconstruction. Relief valve for deploys where the
proxy header chain isn't reliable.

The single source of truth for both helpers lives here so the gate
middleware, the OAuth routes, the cookie helpers, and the SPA mount
all agree on validation rules.

### 顶层函数

#### def `normalise_prefix(raw: Optional[str]) -> str`

Normalise an X-Forwarded-Prefix header value.

Returns a string like ``"/hermes"`` (no trailing slash) or ``""``
when no prefix is set / the header is malformed. We deliberately
reject anything containing ``..`` or non-printable bytes so a
hostile proxy can't inject HTML or path-traversal sequences via the
prefix.

#### def `prefix_from_request(request) -> str`

Convenience wrapper that reads the header off a Starlette/FastAPI
Request and normalises it. Returns ``""`` when no prefix.

#### def `resolve_public_url() -> str`

Resolve the operator-declared dashboard public URL.

Precedence (mirrors ``dashboard.oauth.client_id``):

  1. ``HERMES_DASHBOARD_PUBLIC_URL`` env var (when non-empty after
     strip — empty values are treated as unset so a provisioned-but-
     not-populated Fly secret can't shadow a valid config.yaml entry).
  2. ``dashboard.public_url`` in ``config.yaml``.
  3. Empty string — signals "no override, reconstruct from request"
     to the caller.

Each candidate value is run through :func:`_normalise_public_url`.
A malformed env var falls through to the config.yaml entry; a
malformed config entry falls through to ``""``. This means a typo
in one surface doesn't prevent the other from working.


## hermes_cli.dashboard_auth.public_paths

### 模块文档

Shared allowlist of ``/api/*`` paths that bypass dashboard auth.

Two middlewares enforce dashboard auth and previously kept independent
copies of this list:

* ``hermes_cli.web_server.auth_middleware`` — loopback / ``--insecure``
  mode, gates on the ephemeral ``_SESSION_TOKEN``.
* ``hermes_cli.dashboard_auth.middleware.gated_auth_middleware`` —
  non-loopback mode, gates on the OAuth session cookie.

When the lists drifted, ``/api/status`` ended up public under the legacy
gate but 401'd under the OAuth gate. That broke the portal's wildcard
liveness probe (``nous-account-service`` ``fly-provider.ts``
``getInstanceRuntimeStatus``), which fetches ``/api/status`` without a
cookie as its sole signal of "agent dashboard is alive": every healthy
wildcard-subdomain agent surfaced as STARTING/down in the portal UI even
though the dashboard was serving correctly.

Centralising the allowlist here so both middlewares import the same
frozenset prevents the next drift. Keep this list minimal — only truly
non-sensitive, read-only endpoints belong here. As a sanity check, every
entry should be safe to expose to:

  * external uptime probes (Pingdom, Better Stack, NAS),
  * the dashboard SPA before the user has logged in,
  * anyone who happens to ``curl`` the hostname.

If a new endpoint doesn't pass all three tests, it should be gated and
the SPA should bootstrap it after login instead.

## hermes_cli.dashboard_auth.registry

### 模块文档

Module-level registry for DashboardAuthProvider instances.

Plugins call ``register_provider`` via the plugin context hook at startup.
The auth gate middleware iterates ``list_providers()`` and uses
``get_provider`` to dispatch on the session's ``provider`` field.

### 顶层函数

#### def `register_provider(provider: DashboardAuthProvider) -> None`

Register a provider.

Raises:
    TypeError: on protocol violation.
    ValueError: if a provider with the same name is already registered.

**异常**: `TypeError`, `ValueError`

#### def `get_provider(name: str) -> Optional[DashboardAuthProvider]`

Return the registered provider for ``name``, or None if unknown.

#### def `list_providers() -> List[DashboardAuthProvider]`

All registered providers, in registration order.

#### def `list_token_providers() -> List[DashboardAuthProvider]`

Registered providers that support non-interactive token auth.

The subset of ``list_providers()`` whose ``supports_token`` flag is True,
in registration order. The ``token_auth`` middleware seam consults these
(and only these) when a token-authable route is hit, so OAuth/password-only
providers are never asked to ``verify_token``. Returns an empty list when
no token provider is registered — a token-authable route then fails
closed (401), never open.

#### def `list_session_providers() -> List[DashboardAuthProvider]`

Registered providers with supports_session True (interactive cookie
sessions). The login page, /auth/login, and the gate's verify/refresh loops
consult only these. Mirror of list_token_providers.

#### def `clear_providers() -> None`

Test-only: drop all registrations.


## hermes_cli.dashboard_auth.routes

### 模块文档

HTTP routes for the dashboard-auth OAuth round trip.

Mounted at root (no prefix) by ``web_server.py``. The router does not
auto-gate; gating is performed by ``gated_auth_middleware``, which
allowlists everything under ``/auth/*`` and ``/api/auth/providers``.

The routes:

  GET  /login              → server-rendered login page
  GET  /auth/login?provider=N → 302 to IDP, sets PKCE cookie
  GET  /auth/callback?code,state → completes login, sets session cookies
  POST /auth/logout        → clears cookies, best-effort revoke
  GET  /api/auth/providers → list registered providers (login bootstrap)
  GET  /api/auth/me        → current Session as JSON (auth-required)

### 顶层函数

#### def `login_page(request: Request) -> HTMLResponse`

#### def `api_auth_providers() -> Any`

#### def `auth_login(request: Request, provider: str, next: str = '')`

**异常**: `HTTPException`

#### def `auth_callback(request: Request, code: str = '', state: str = '', error: str = '', error_description: str = '')`

**异常**: `HTTPException`

#### def `auth_password_login(request: Request, body: _PasswordLoginBody)`

Authenticate a username/password against a password provider.

Mirrors the cookie-minting tail of ``/auth/callback`` but skips the
PKCE/state/code machinery (those are OAuth-only). On success sets the
session cookies and returns JSON ``{"ok": true, "next": <path>}`` —
the credential form POSTs via fetch and navigates client-side, so a
302 (which fetch follows opaquely) is the wrong shape here.

Failure modes, all deliberately generic so the endpoint can't be used
as a username oracle or a provider-enumeration oracle:
  * unknown provider / provider lacks password support → 404
  * bad credentials → 401 ("Invalid credentials")
  * backing store unreachable → 503
  * too many attempts from this IP → 429

**异常**: `HTTPException`

#### def `auth_logout(request: Request)`

#### def `api_auth_me(request: Request)`

Return the verified session as JSON. Auth-required (gate enforces).

**异常**: `HTTPException`

#### def `api_auth_ws_ticket(request: Request)`

Mint a short-lived single-use ticket for the authenticated session.

Browsers cannot set ``Authorization`` on a WebSocket upgrade, so in
gated mode the SPA POSTs this endpoint to get a ``?ticket=`` value to
append to ``/api/pty``, ``/api/console``, ``/api/ws``, ``/api/pub``, or
``/api/events``.

The ticket has a 30-second TTL and is single-use. Calling this endpoint
multiple times in quick succession (e.g. one ticket per WS) is the
expected pattern.

**异常**: `HTTPException`


## hermes_cli.dashboard_auth.token_auth

### 模块文档

Route-agnostic non-interactive (bearer-token) auth seam for the dashboard.

This is the generic API-token capability (decisions.md Q-C): a reusable seam
that ANY service-to-service / machine-credential provider plugs into, NOT a
drain-specific hook. The drain bearer-secret plugin is merely the first
consumer.

How it fits the existing auth framework:

  * The interactive gate (``gated_auth_middleware``) authenticates a human
    via a session cookie on every non-public route. A service caller has no
    cookie — it presents a bearer token in the ``Authorization`` header on a
    single request. That is what this seam verifies.

  * A route opts in by registering its exact path via
    :func:`register_token_route`. Only registered paths are token-authable;
    everything else is untouched, so this can never accidentally widen the
    auth surface of an existing route.

  * :func:`token_auth_middleware` runs OUTERMOST (installed last in
    ``web_server.py``). For a token route it fully owns the auth decision:
    authenticate via the stacked token providers, attach the verified
    :class:`~hermes_cli.dashboard_auth.base.TokenPrincipal` to
    ``request.state.token_principal`` + set ``request.state.token_authenticated``,
    and pass through; otherwise reject (401 unauthenticated, or 503 when a
    provider's backing store was unreachable). The downstream cookie/session
    gates honour ``token_authenticated`` and skip enforcement, so a
    token-authed service request is never bounced to ``/login``.

  * Fails closed: a token route with no registered token provider, no token,
    or an unrecognised token gets 401 — never an open pass-through.

Provider stacking mirrors ``verify_session``: each ``supports_token`` provider
is consulted in registration order until one returns a principal. A provider
that doesn't recognise the token returns ``None`` and the seam moves on; a
provider whose backing store is unreachable raises ``ProviderError``, which the
seam remembers and surfaces as 503 only if NO provider accepts the token.

### 顶层函数

#### def `register_token_route(path: str) -> None`

Mark ``path`` (exact match) as token-authable.

Idempotent. Call at module import / app setup so the seam knows which
routes to guard. Registering a route does NOT make it public — it makes
it authenticate by token instead of by session cookie.

#### def `is_token_route(path: str) -> bool`

True if ``path`` was registered as token-authable (exact match).

#### def `clear_token_routes() -> None`

Test-only: drop all registered token routes.

#### def `extract_bearer_token(request: Request) -> str`

Return the bearer token from the ``Authorization`` header, or "".

Accepts ``<scheme> <token>`` where scheme is "bearer" (case-insensitive).
Returns an empty string for a missing/malformed header or a non-bearer
scheme — the caller treats "" as "no token presented".

#### def `authenticate_token(request: Request) -> Tuple[Optional[TokenPrincipal], Optional[str]]`

Try every token provider against the request's bearer token.

Returns ``(principal, unreachable_provider_name)``:
  * ``(TokenPrincipal, None)`` — a provider recognised and accepted the token.
  * ``(None, None)`` — no token, or no provider recognised it (reject 401).
  * ``(None, name)`` — no provider accepted it AND at least one provider's
    backing store was unreachable (the caller surfaces 503, not 401, so a
    transient outage doesn't read as "bad credentials").

Never raises: a provider ``ProviderError`` is caught and remembered.

#### def `token_auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response`

Outermost auth seam for token-authable routes.

No-op pass-through for any path not registered via
:func:`register_token_route`. For a registered path, token auth is the
only accepted scheme:

  * valid token  → attach principal + ``token_authenticated`` flag, pass through.
  * unreachable  → 503 (provider backing store down; not "bad credentials").
  * otherwise    → 401 unauthenticated.

Runs before the cookie/session gates (installed last in ``web_server.py``).
The cookie gates honour ``request.state.token_authenticated`` and skip
enforcement, so a token-authed request is never redirected to ``/login``.


## hermes_cli.dashboard_auth.ws_tickets

### 模块文档

WS-upgrade auth credentials for gated mode.

Browsers cannot set ``Authorization`` on a WebSocket upgrade. In loopback
mode the legacy ``?token=<_SESSION_TOKEN>`` query param works because the
token is injected into the SPA bundle. In gated mode there is no injected
token — so this module provides two credential shapes:

1. **Single-use browser tickets** (``mint_ticket`` / ``consume_ticket``).
   The SPA gets a fresh ticket via the authenticated REST endpoint
   ``POST /api/auth/ws-ticket`` and passes it as ``?ticket=`` on the WS
   upgrade. Single-use, TTL = 30 seconds — a leaked ticket is uninteresting.

2. **A process-lifetime internal credential** (``internal_ws_credential`` /
   ``consume_internal_credential``). This authenticates *server-spawned*
   WS clients — specifically the embedded-TUI PTY child, which attaches to
   ``/api/ws`` (JSON-RPC gateway) and ``/api/pub`` (event sidecar) over
   loopback. A single-use 30s ticket is the wrong shape for that link: the
   child reads its attach URL once at startup and **reuses it on every
   reconnect**, and on a slow cold boot the child may not dial within 30s.
   The internal credential is minted once per process, never expires, is
   multi-use, and — critically — is **never injected into any HTML/SPA**:
   it only ever leaves the process via the spawned child's environment, so
   browser-side XSS cannot read it. A leaked internal credential grants no
   more than a single-use ticket already does (the same two internal WS
   endpoints), and the same Origin / host guards still apply downstream.

In-memory; the dashboard is a single process so no distributed coordination
is needed. The module exposes a small functional API rather than a class so
tests can patch ``time.time`` cleanly.

### class TicketInvalid

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Ticket missing, expired, or already consumed.


### 顶层函数

#### def `mint_ticket(user_id: str, provider: str) -> str`

Generate a one-shot ticket bound to this user identity.

The returned token is base64url, 43 bytes of entropy (32-byte random
seed). Stash returns the ``info`` dict to the caller on consume so the
WS handler can carry the identity forward into its session log.

#### def `consume_ticket(ticket: str) -> Dict[str, Any]`

Validate and consume. Raises :class:`TicketInvalid` on missing/expired/used.

Single-use semantics: a successful consume immediately removes the
ticket from the store, so a second call with the same value raises
``TicketInvalid("unknown ticket: …")``.

**异常**: `class`, `TicketInvalid`

#### def `internal_ws_credential() -> str`

Return the process-lifetime internal WS credential, minting it once.

Used by the server to authenticate WS clients it spawns itself (the
embedded-TUI PTY child). The value is stable for the life of the process,
multi-use, and never expires — so a server-spawned child can reconnect
its ``/api/ws`` / ``/api/pub`` sockets indefinitely without re-minting.

The credential is never injected into the SPA HTML or returned over any
REST endpoint; it is only ever passed to a child process via its
environment. See the module docstring for the threat-model rationale.

#### def `consume_internal_credential(value: str) -> Dict[str, Any]`

Validate an internal credential. Raises :class:`TicketInvalid` on mismatch.

Unlike :func:`consume_ticket` this is **not** single-use — the value is
not removed on success, so a server-spawned child can present it on every
(re)connect. Returns the fixed server-internal identity ``info`` dict
(``{user_id, provider}``), mirroring the ``info`` shape ``consume_ticket``
returns, so a caller that wants to record the connecting identity can; the
current ``_ws_auth_ok`` caller validates for the boolean outcome only and
discards the dict.

A constant-time compare against the (lazily-minted) credential avoids
leaking length / prefix information on mismatch. If no internal
credential has been minted yet, any value is rejected.

**异常**: `class`, `Unlike`, `TicketInvalid`


## hermes_cli.dashboard_register

### 模块文档

``hermes dashboard register`` — register a self-hosted dashboard OAuth client.

Automates what a user otherwise does by hand: open the Nous Portal
``/local-dashboards`` page in a browser, click "register", copy the
resulting ``agent:{id}`` OAuth client ID, and paste it into ``~/.hermes/.env``
as ``HERMES_DASHBOARD_OAUTH_CLIENT_ID``.

This command:
  1. Resolves a fresh Nous Portal access token from the existing login
     (``~/.hermes/auth.json``), refreshing it if needed. Fails fast with a
     "run `hermes setup`" hint when the user isn't logged in.
  2. POSTs to ``{portal}/api/oauth/self-hosted-client`` with that bearer
     token, which creates a SELF_HOSTED agent client owned by the caller's
     org and returns the fully-formed ``agent:{id}`` client_id.
  3. Writes ``HERMES_DASHBOARD_OAUTH_CLIENT_ID`` and (if absent)
     ``HERMES_DASHBOARD_PORTAL_URL`` into ``~/.hermes/.env`` idempotently.
  4. Prints a post-register hint explaining that the OAuth gate only engages
     on a non-loopback bind.

The portal endpoint is the NAS half of this feature (POST
/api/oauth/self-hosted-client). The ``agent:`` prefix is applied server-side,
so this client never needs to know the namespace convention.

### 顶层函数

#### def `cmd_dashboard_register(args) -> None`

Register a self-hosted dashboard OAuth client with Nous Portal.


## hermes_cli.debug

### 模块文档

``hermes debug`` debug tools for Hermes Agent.

Currently supports:
    hermes debug share    Upload debug report (system info + logs) to a
                          paste service and print a shareable URL.
                          By default, log content is run through
                          ``agent.redact.redact_sensitive_text`` with
                          ``force=True`` before upload so credentials in
                          ``~/.hermes/logs/*.log`` are not leaked into
                          the public paste service. Pass ``--no-redact``
                          to disable.
                          Pass ``--nous`` to upload instead to Nous-internal
                          storage (AWS S3) via a signed URL minted by the
                          Nous account service: the bundle is private
                          (viewable only by Nous staff / allowlisted mods via
                          a Google-login-gated viewer) and auto-deletes after
                          14 days, rather than going to a public paste.

### class LogSnapshot

> 继承: `object` ｜ 方法数: 0（公开 0）

Single-read snapshot of a log file used by debug-share.


### class DebugShareResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Structured outcome of a ``debug share`` upload.

Returned by :func:`build_debug_share` so non-CLI callers (the dashboard
web server, gateway) can render the uploaded paste URLs as real links
instead of scraping printed text.


### 顶层函数

#### def `delete_paste(url: str) -> bool`

Delete a paste from paste.rs.  Returns True on success.

Only paste.rs supports unauthenticated DELETE.  dpaste.com pastes
expire automatically but cannot be deleted via API.

**异常**: `ValueError`

#### def `upload_to_pastebin(content: str, expiry_days: int = 7) -> str`

Upload *content* to a paste service, trying paste.rs then dpaste.com.

Returns the paste URL on success, raises on total failure.

**异常**: `RuntimeError`

#### def `collect_debug_report(log_lines: int = 200, dump_text: str = '', log_snapshots: Optional[dict[str, LogSnapshot]] = None) -> str`

Build the summary debug report: system dump + log tails.

Parameters
----------
log_lines
    Number of recent lines to include per log file.
dump_text
    Pre-captured dump output.  If empty, ``hermes dump`` is run
    internally.

Returns the report as a plain-text string ready for upload.

#### def `collect_share_bundle(log_lines: int = 200, redact: bool = True) -> dict[str, str]`

Collect the debug report + full logs as a label→text mapping.

Returns ``{"report": ..., "agent.log": ..., "gateway.log": ...,
"desktop.log": ...}`` where each value is the already-redacted (when
``redact`` is True) text that would be uploaded.  Keys for logs that are
absent/empty are simply omitted.

This is the single source of collection + redaction shared by both
destinations: the paste.rs path (:func:`build_debug_share`) and the
Nous-S3 path (``--nous``).  Centralising it guarantees the Nous bundle is
built from the *same* force-redacted snapshots as the public paste path —
redaction is the safety boundary, so the Nous path must never see raw
logs.

The dump header is prepended to each full log (mirroring the historical
paste behaviour) so every file is self-contained, and the redaction
banner is prepended when ``redact`` is True.

#### def `build_nous_bundle(bundle: dict[str, str], redact: bool = True) -> bytes`

Gzip-compress a :func:`collect_share_bundle` mapping into the Nous envelope.

The JSON shape is what the discord-support viewer (Repo 3) parses::

    {"format": "hermes-debug-share/1",
     "redacted": <bool>,
     "created": <iso8601>,
     "files": {"report": ..., "agent.log": ..., ...}}

#### def `build_debug_share(log_lines: int = 200, expiry: int = 7, redact: bool = True) -> DebugShareResult`

Collect the debug report + full logs, upload each, return the URLs.

This is the shared core behind ``hermes debug share`` (CLI) and the
dashboard ``POST /api/ops/debug-share`` endpoint. It performs blocking
network I/O (paste uploads) — callers inside an event loop must run it in
a worker thread.

The summary report upload is required: on failure this raises
``RuntimeError``. Full-log uploads are best-effort; their errors are
collected into ``failures`` rather than raised.

#### def `run_debug_share(args)`

Collect debug report + full logs, upload each, print URLs.

#### def `run_debug_delete(args)`

Delete one or more paste URLs uploaded by /debug.

#### def `run_debug(args)`

Route debug subcommands.


## hermes_cli.default_soul

### 模块文档

Default SOUL.md template seeded into HERMES_HOME on first run.

### 顶层函数

#### def `is_legacy_template_soul(text: str) -> bool`

True if ``text`` is an old empty-template SOUL.md (no user persona).

Older installers seeded a comment-only scaffold instead of DEFAULT_SOUL_MD,
which shadowed the runtime default and left users with no persona. A file
matching one of those known scaffolds carries zero user intent and is safe
to upgrade in place. Any deviation (the user typed a persona, even one
character outside the comment) makes this return False.


## hermes_cli.dep_ensure

### 模块文档

Lazy dependency bootstrapper for non-Python runtime deps.

Detection and prompting live here in Python — not in install.sh — because:
  1. shutil.which() works on every platform; install.sh needs bash.
  2. Detection is instant; spawning bash for a "is node installed?" check is waste.
  3. Python controls the UX (rich prompts, non-interactive fallback, TTY detection).

install.sh is still the *installation* backend because it has 1900 lines of
battle-tested OS detection and package-manager logic (apt/brew/pacman/dnf/
zypper/Termux/…).  Reimplementing that in Python would be huge duplication.

Deps that degrade gracefully (ripgrep → grep fallback, ffmpeg → skip conversion)
don't need ensure_dependency wired in — only hard-fail sites do (TUI needs node,
browser tool needs agent-browser).

### 顶层函数

#### def `ensure_dependency(dep: str, interactive: bool = True) -> bool`

Ensure a non-Python dependency is available. Returns True if available.


## hermes_cli.diagnostics_upload

### 模块文档

Client for uploading ``hermes debug share`` bundles to Nous-internal S3.

This is the opt-in (``--nous``) destination for ``hermes debug share``.
Unlike the public paste.rs path, bundles uploaded here go to a Nous-owned
S3 bucket via a short-lived signed URL minted by the Nous account service
(NAS).  The bucket auto-expires objects after 14 days, and the contents are
only viewable by Nous staff (and allowlisted Discord mods) through a
Google-OAuth-gated viewer.

Flow:

    1. POST {NAS_BASE}/api/diagnostics/upload-url  → {uploadUrl, viewUrl, id, ...}
       (the request body carries ``sizeBytes``; NAS signs it into the presigned
       URL's ``ContentLength``, so the PUT must send exactly that many bytes)
    2. PUT <uploadUrl>  (the gzipped bundle, Content-Type application/gzip)

NAS is stateless — the object's existence in S3 is the only state, so there is
no confirm/callback step.

Uses stdlib ``urllib`` only, matching ``debug.py`` style — no third-party deps.

### 顶层函数

#### def `request_upload_url(content_type: str = 'application/gzip', size_bytes: int | None = None) -> dict`

Ask NAS to mint a presigned PUT URL for a diagnostics bundle.

POSTs a small JSON body to ``{NAS_BASE}/api/diagnostics/upload-url`` and
returns the parsed JSON response, expected to contain at least
``uploadUrl``, ``viewUrl`` and ``id`` (plus optional ``expiresAt`` /
``uploadExpiresInSeconds``).

Raises on non-2xx responses or unparseable JSON.

**异常**: `RuntimeError`

#### def `put_bundle(upload_url: str, data: bytes, content_type: str = 'application/gzip') -> None`

PUT the gzipped *data* bundle to a presigned *upload_url*.

Sets the ``Content-Type`` header (must match what NAS pinned when signing
the URL, otherwise S3 rejects the signature). Raises on non-2xx.

**异常**: `RuntimeError`

#### def `share_to_nous(report_bundle: bytes) -> dict`

Orchestrate the full Nous-S3 upload of a gzipped *report_bundle*.

Two steps: mint a presigned PUT URL (sending the exact ``sizeBytes`` NAS
signs into the URL's ``ContentLength``), then PUT the bundle. NAS is
stateless — the object's existence in S3 is the only state, so there is no
confirm/callback step. Returns the dict from :func:`request_upload_url`
(which carries ``viewUrl`` / ``id`` / expiry metadata) so the caller can
print the viewer link. Raises on any failure of either step.


## hermes_cli.dingtalk_auth

### 模块文档

DingTalk Device Flow authorization.

Implements the same 3-step registration flow as dingtalk-openclaw-connector:
  1. POST /app/registration/init   → get nonce
  2. POST /app/registration/begin  → get device_code + verification_uri_complete
  3. POST /app/registration/poll   → poll until SUCCESS → get client_id + client_secret

The verification_uri_complete is rendered as a QR code in the terminal so the
user can scan it with DingTalk to authorize, yielding AppKey + AppSecret
automatically.

### class RegistrationError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Raised when a DingTalk registration API call fails.


### 顶层函数

#### def `begin_registration() -> dict`

Start a device-flow registration.

Returns a dict with keys:
    device_code, verification_uri_complete, expires_in, interval

**异常**: `RegistrationError`

#### def `poll_registration(device_code: str) -> dict`

Poll the registration status once.

Returns a dict with keys:  status, client_id?, client_secret?, fail_reason?

#### def `wait_for_registration_success(device_code: str, interval: int = 3, expires_in: int = 7200, on_waiting: Optional[callable] = None) -> Tuple[str, str]`

Block until the registration succeeds or times out.

Returns (client_id, client_secret).

**异常**: `RegistrationError`

#### def `render_qr_to_terminal(url: str) -> bool`

Render *url* as a compact QR code in the terminal.

Returns True if the QR code was printed, False if the library is missing.

#### def `dingtalk_qr_auth() -> Optional[Tuple[str, str]]`

Run the interactive QR-code device-flow authorization.

Returns (client_id, client_secret) on success, or None if the user
cancelled or the flow failed.


## hermes_cli.doctor

### 模块文档

Doctor command for hermes CLI.

Diagnoses issues with Hermes Agent setup.

### 顶层函数

#### def `check_ok(text: str, detail: str = '')`

#### def `check_warn(text: str, detail: str = '')`

#### def `check_fail(text: str, detail: str = '')`

#### def `check_info(text: str)`

#### def `collect_deprecated_config_keys(raw_config: dict | None) -> list[tuple[str, str]]`

Return ``(legacy_path, replacement)`` for deprecated keys present in *raw_config*.

Only keys that appear in the on-disk YAML are reported (raw file load, not
merged defaults). Empty containers still count — presence of the legacy
key is the signal that the user should migrate.

#### def `collect_deprecated_env_vars(env_map: dict | None) -> list[tuple[str, str]]`

Return ``(legacy_env, replacement)`` for deprecated vars present in *env_map*.

*env_map* should come from the on-disk ``.env`` (e.g. ``load_env()``), not
``os.environ``, so bridged runtime vars do not trigger false positives.

#### def `report_deprecated_config_and_env(raw_config: dict | None = None, env_map: dict | None = None) -> list[tuple[str, str]]`

Emit non-failing doctor warnings for deprecated config keys and env vars.

Returns the list of ``(legacy, replacement)`` findings that were reported
(empty when nothing deprecated is present). Does not mutate config/env and
does not append to the blocking ``issues`` list.

#### def `check_certificates() -> None`

Verify the certifi CA bundle is loadable.

Surfaces the SSLConfigurationError user-friendly path before they hit
a wall of tracebacks on the first outbound HTTPS call.

#### def `managed_scope_check() -> None`

Report the active managed scope (resolved dir + pinned key counts).

Silent when no managed scope is present. When the managed directory was
resolved from the HERMES_MANAGED_DIR override (rather than the system
default), that is surfaced too — a redirected scope is the documented
foot-gun (see docs/design/managed-scope.md §7) and an operator should see it.

#### def `run_doctor(args)`

Run diagnostic checks.


## hermes_cli.dump

### 模块文档

Dump command for hermes CLI.

Outputs a compact, plain-text summary of the user's Hermes setup
that can be copy-pasted into Discord/GitHub/Telegram for support context.
No ANSI colors, no checkmarks — just data.

### 顶层函数

#### def `run_dump(args)`

Output a compact, copy-pasteable setup summary.


## hermes_cli.env_loader

### 模块文档

Helpers for loading Hermes .env files consistently across entrypoints.

### 顶层函数

#### def `get_secret_source(env_var: str) -> str | None`

Return the label of the secret source that supplied ``env_var``, if any.

Returns ``"bitwarden"`` for keys pulled from Bitwarden Secrets Manager
during the current process's ``load_hermes_dotenv()`` call.  Returns
``None`` for keys that came from ``.env``, the shell environment, or
aren't tracked.  The returned label is metadata only: credential-pool
persistence may store it to explain the origin of a borrowed secret, but
must never treat it as authorization to persist the raw value.

#### def `reset_secret_source_cache() -> None`

Forget which HERMES_HOME paths have already had external secrets applied.

The first call to ``_apply_external_secret_sources(home_path)`` in a
process pulls from Bitwarden (or other configured backend), records the
applied keys in ``_SECRET_SOURCES``, and remembers ``home_path`` so
subsequent calls in the same process are no-ops.  Call this to force the
next call to re-pull — useful for tests, and for long-running processes
that want to refresh after a config change.

#### def `format_secret_source_suffix(env_var: str) -> str`

Return a human-readable suffix like ``" (from Bitwarden)"`` or ``""``.

Use this when printing a detected credential so the user can see where
it came from.  Empty string when the credential came from ``.env`` or
the shell — those are the implicit / "default" cases users already
understand.

#### def `load_hermes_dotenv(hermes_home: str | os.PathLike | None = None, project_env: str | os.PathLike | None = None) -> list[Path]`

Load Hermes environment files with user config taking precedence.

Behavior:
- `~/.hermes/.env` overrides stale shell-exported values when present.
- project `.env` acts as a dev fallback and only fills missing values when
  the user env exists.
- if no user env exists, the project `.env` also overrides stale shell vars.


## hermes_cli.fallback_cmd

### 模块文档

hermes fallback — manage the fallback provider chain.

Fallback providers are tried in order when the primary model fails with
rate-limit, overload, or connection errors. See:
https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers

Subcommands:
  hermes fallback [list]   Show the current fallback chain (default when no subcommand)
  hermes fallback add      Pick provider + model via the same picker as `hermes model`,
                           then append the selection to the chain
  hermes fallback remove   Pick an entry to delete from the chain
  hermes fallback clear    Remove all fallback entries

Storage: ``fallback_providers`` in ``~/.hermes/config.yaml`` (top-level, list of
``{provider, model, base_url?, api_mode?}`` dicts).  The legacy single-dict
``fallback_model`` format is migrated to the new list format on first add.

### 顶层函数

#### def `cmd_fallback_list(args) -> None`

Print the current fallback chain.

#### def `cmd_fallback_add(args) -> None`

Launch the same picker as `hermes model`, then append the selection to the chain.

#### def `cmd_fallback_remove(args) -> None`

Pick an entry from the chain and remove it.

#### def `cmd_fallback_clear(args) -> None`

Remove all fallback entries (with confirmation).

#### def `cmd_fallback(args) -> None`

Top-level dispatcher for ``hermes fallback [subcommand]``.

**异常**: `SystemExit`


## hermes_cli.fallback_config

### 模块文档

Helpers for reading the effective fallback provider chain from config.

### 顶层函数

#### def `resolve_entry_api_key(entry: dict[str, Any] | None) -> str | None`

API key for one fallback entry: inline ``api_key``, else ``key_env``.

Mirrors the custom-provider convention (``key_env`` names the env var
holding the key; ``api_key_env`` accepted as an alias). Returns None when
neither yields a non-empty value, letting ``resolve_runtime_provider``
fall through to the provider's standard credential resolution.

#### def `get_fallback_chain(config: dict[str, Any] | None) -> list[dict[str, Any]]`

Return the effective fallback chain merged across old and new config keys.

``fallback_providers`` remains the primary source of truth and keeps its
order. Legacy ``fallback_model`` entries are appended afterwards unless
they target the same provider/model/base_url route as an earlier entry.
The returned list always contains fresh dict copies.


## hermes_cli.gateway

### 模块文档

Gateway subcommand for hermes CLI.

Handles: hermes gateway [run|start|stop|restart|status|install|uninstall|setup]

### class GatewayRuntimeSnapshot

> 继承: `object` ｜ 方法数: 2（公开 2）

#### property `running(self) -> bool`

#### property `has_process_service_mismatch(self) -> bool`


### class ProfileGatewayProcess

> 继承: `object` ｜ 方法数: 0（公开 0）


### class UserSystemdUnavailableError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when ``systemctl --user`` cannot reach the user D-Bus session.

Typically hit on fresh RHEL/Debian SSH sessions where linger is disabled
and no user@.service is running, so ``/run/user/$UID/bus`` never exists.
Carries a user-facing remediation message in ``args[0]``.


### class SystemScopeRequiresRootError

> 继承: `RuntimeError` ｜ 方法数: 1（公开 0）

Raised when a system-scope gateway operation is attempted as non-root.

System-scope units live in ``/etc/systemd/system/`` and require root for
install / uninstall / start / stop / restart via ``systemctl``. The
previous behavior was ``sys.exit(1)`` which blew past the wizard's
``except Exception`` guards and dumped the user at a bare shell prompt
with no guidance. Raising a typed exception lets callers that can
recover (the setup wizard) print actionable remediation instead, while
``gateway_command`` still exits 1 with the same message for the direct
CLI path.

``args[0]`` carries the user-facing message, ``args[1]`` the action name.
``str(e)`` returns only the message (not the tuple repr) so format
strings like ``f"Failed: {e}"`` render cleanly.


### 顶层函数

#### def `find_gateway_pids(exclude_pids: set | None = None, all_profiles: bool = False) -> list`

Find PIDs of running gateway processes.

Args:
    exclude_pids: PIDs to exclude from the result (e.g. service-managed
        PIDs that should not be killed during a stale-process sweep).
    all_profiles: When ``True``, return gateway PIDs across **all**
        profiles (the pre-7923 global behaviour).  ``hermes update``
        needs this because a code update affects every profile.
        When ``False`` (default), only PIDs belonging to the current
        Hermes profile are returned.

#### def `find_profile_gateway_processes(exclude_pids: set | None = None) -> list[ProfileGatewayProcess]`

Return running gateway PIDs mapped to Hermes profiles via PID files.

#### def `launch_detached_gateway_restart_by_cmdline(old_pid: int, run_argv: list[str]) -> bool`

Relaunch a gateway by replaying its captured command line after exit.

Companion to ``launch_detached_profile_gateway_restart`` for gateways that
have no profile→PID-file mapping (Scheduled-Task / manually-launched
``gateway run`` whose HERMES_HOME or argv doesn't match a known profile).
Uses the identical detached-watcher mechanism; only the respawn argv
differs (the process's own argv instead of a profile-derived one).

#### def `launch_detached_profile_gateway_restart(profile: str, old_pid: int) -> bool`

Relaunch a manually-run profile gateway after its current PID exits.

#### def `get_gateway_runtime_snapshot(system: bool = False) -> GatewayRuntimeSnapshot`

Return a unified view of gateway liveness for the current profile.

#### def `kill_gateway_processes(force: bool = False, exclude_pids: set | None = None, all_profiles: bool = False) -> int`

Kill any running gateway processes. Returns count killed.

Args:
    force: Use the platform's force-kill mechanism instead of graceful terminate.
    exclude_pids: PIDs to skip (e.g. service-managed PIDs that were just
        restarted and should not be killed).
    all_profiles: When ``True``, kill across all profiles.  Passed
        through to :func:`find_gateway_pids`.

#### def `stop_profile_gateway() -> bool`

Stop only the gateway for the current profile (HERMES_HOME-scoped).

Uses the PID file written by start_gateway(), so it only kills the
gateway belonging to this profile — not gateways from other profiles.
Returns True if a process was stopped, False if none was found.

On hosts without a service supervisor (e.g. WSL/no-systemd, where the
manual restart fallback runs the gateway in-process under a ``gateway
restart`` argv), the pidfile/runtime record can be missing or stale while
a live orphan still holds the webhook port. In that case fall back to the
orphan-aware process scan so the replacement reaps the prior instance
instead of stacking a duplicate on the same port (#51325).

#### def `is_linux() -> bool`

#### def `supports_systemd_services() -> bool`

#### def `is_macos() -> bool`

#### def `is_windows() -> bool`

#### def `get_service_name() -> str`

Derive a systemd service name scoped to this HERMES_HOME.

Default ``~/.hermes`` returns ``hermes-gateway`` (backward compatible).
Profile ``~/.hermes/profiles/coder`` returns ``hermes-gateway-coder``.
Any other HERMES_HOME appends a short hash for uniqueness.

#### def `get_systemd_unit_path(system: bool = False) -> Path`

#### def `get_installed_systemd_scopes() -> list[str]`

#### def `has_conflicting_systemd_units() -> bool`

#### def `has_legacy_hermes_units() -> bool`

Return True when any legacy Hermes gateway unit files exist.

#### def `print_legacy_unit_warning() -> None`

Warn about legacy Hermes gateway unit files if any are installed.

Idempotent: prints nothing when no legacy units are detected. Safe to
call from any status/install/setup path.

#### def `remove_legacy_hermes_units(interactive: bool = True, dry_run: bool = False) -> tuple[int, list[Path]]`

Stop, disable, and remove legacy Hermes gateway unit files.

Iterates over whatever ``_find_legacy_hermes_units()`` returns — which is
an explicit allowlist of legacy names (not a glob). Profile units and
unrelated third-party services are never touched.

Args:
    interactive: When True, prompt before removing. When False, remove
        without asking (used when another prompt has already confirmed,
        e.g. from the install flow).
    dry_run: When True, list what would be removed and return.

Returns:
    ``(removed_count, remaining_paths)`` — remaining includes units we
    couldn't remove (typically system-scope when not running as root).

#### def `print_systemd_scope_conflict_warning() -> None`

#### def `prompt_linux_gateway_install_scope() -> str | None`

#### def `install_linux_gateway_from_setup(force: bool = False, enable_on_startup: bool = True) -> tuple[str | None, bool]`

#### def `get_systemd_linger_status() -> tuple[bool | None, str]`

Return systemd linger status for the current user.

Returns:
    (True, "") when linger is enabled.
    (False, "") when linger is disabled.
    (None, detail) when the status could not be determined.

#### def `print_systemd_linger_guidance() -> None`

Print the current linger status and the fix when it is disabled.

#### def `get_launchd_plist_path() -> Path`

Return the launchd plist path, scoped per profile.

Default ``~/.hermes`` → ``ai.hermes.gateway.plist`` (backward compatible).
Profile ``~/.hermes/profiles/coder`` → ``ai.hermes.gateway-coder.plist``.

#### def `get_python_path() -> str`

#### def `generate_systemd_unit(system: bool = False, run_as_user: str | None = None) -> str`

#### def `systemd_unit_is_current(system: bool = False) -> bool`

#### def `refresh_systemd_unit_if_needed(system: bool = False) -> bool`

Rewrite the installed systemd unit when the generated definition has changed.

#### def `systemd_install(force: bool = False, system: bool = False, run_as_user: str | None = None, enable_on_startup: bool = True, non_interactive: bool = False)`

#### def `systemd_uninstall(system: bool = False)`

#### def `systemd_start(system: bool = False)`

#### def `systemd_stop(system: bool = False)`

#### def `systemd_restart(system: bool = False)`

#### def `systemd_status(deep: bool = False, system: bool = False, full: bool = False)`

#### def `get_launchd_label() -> str`

Return the launchd service label, scoped per profile.

#### def `generate_launchd_plist() -> str`

#### def `launchd_plist_is_current() -> bool`

Check if the installed launchd plist matches the currently generated one.

#### def `refresh_launchd_plist_if_needed() -> bool`

Rewrite the installed launchd plist when the generated definition has changed.

Unlike systemd, launchd picks up plist changes on the next ``launchctl kill``/
``launchctl kickstart`` cycle — no daemon-reload is needed. We still bootout/
bootstrap to make launchd re-read the updated plist immediately.

#### def `launchd_install(force: bool = False)`

#### def `launchd_uninstall()`

#### def `launchd_start()`

#### def `launchd_stop()`

#### def `launchd_restart()`

#### def `launchd_status(deep: bool = False)`

#### def `run_gateway(verbose: int = 0, quiet: bool = False, replace: bool = False, force: bool = False)`

Run the gateway in foreground.

Args:
    verbose: Stderr log verbosity count added on top of default WARNING (0=WARNING, 1=INFO, 2+=DEBUG).
    quiet: Suppress all stderr log output.
    replace: If True, kill any existing gateway instance before starting.
             This prevents systemd restart loops when the old process
             hasn't fully exited yet.
    force: Skip the supervised-gateway conflict guard and start even when a
           systemd/launchd service is already supervising this profile.

#### def `gateway_setup()`

Interactive setup for messaging platforms + gateway service.

#### def `gateway_command(args)`

Handle gateway subcommands.


## hermes_cli.gateway_enroll

### 模块文档

``hermes gateway enroll`` — enroll a self-hosted gateway with a relay connector.

The connector⇄gateway channel is authenticated (the gateway may be
customer-managed and internet-exposed). This command is the gateway half of the
zero-touch enrollment in the connector repo's
``docs/connector-gateway-auth-design.md``:

  1. Resolve a fresh Nous Portal access token from the existing login
     (``~/.hermes/auth.json``) — the same path ``hermes dashboard register``
     uses (``resolve_nous_access_token``). This proves *which Nous org (tenant)*
     the caller owns; the connector derives the authoritative tenant from it via
     ``GET /api/oauth/account`` (never from anything the gateway asserts).
  2. POST ``{enrollmentToken, gatewayId}`` to the connector's ``/relay/enroll``
     with that token in the ``Authorization`` header, over TLS.
  3. The connector verifies the enrollment token (signature + single-use +
     tenant match), mints a per-gateway secret, get-or-creates the per-tenant
     delivery key, and returns both ONCE.
  4. Persist ``GATEWAY_RELAY_ID`` / ``GATEWAY_RELAY_SECRET`` /
     ``GATEWAY_RELAY_DELIVERY_KEY`` (+ ``GATEWAY_RELAY_URL`` if supplied) into
     ``~/.hermes/.env``. The per-gateway secret authenticates the WS upgrade;
     the per-tenant delivery key verifies signed inbound deliveries.

Managed/hosted installs do NOT self-enroll: the orchestrator (NAS) mints the
secret directly and stamps it into the container env, so this command refuses to
run under ``is_managed()`` (mirrors ``dashboard register``).

EXPERIMENTAL: the relay auth scheme may change without a deprecation cycle until
≥2 Class-1 platforms validate the contract.

### 顶层函数

#### def `cmd_gateway_enroll(args) -> None`

Enroll this gateway with a relay connector; persist the auth creds to .env.


## hermes_cli.gateway_windows

### 模块文档

Windows gateway service backend (Scheduled Task + Startup-folder fallback).

This mirrors the contract exposed by ``launchd_install`` / ``launchd_start`` /
``launchd_status`` etc. on macOS and ``systemd_install`` / ``systemd_start`` on
Linux. It uses ``schtasks`` under the hood with ``/SC ONLOGON`` and restart-on-
failure XML settings, and falls back to a ``%APPDATA%\...\Startup\<name>.vbs``
dropper when Scheduled Task creation is denied (locked-down corporate boxes).

Design notes
------------
* ``schtasks /Create /SC ONLOGON /RL LIMITED`` means the task runs at the
  CURRENT USER's next logon without any elevation prompt. Manual starts and
  install ``--start-now`` use the direct detached ``pythonw`` launcher instead
  of ``schtasks /Run`` so start/restart behavior is consistent.
* We write a shared ``gateway.cmd`` wrapper plus a console-less ``gateway.vbs``
  launcher. Scheduled Task and Startup-folder persistence both route through
  VBS/wscript; immediate manual starts route through direct ``subprocess`` spawn.
* Status = merge of "is the schtasks entry registered?" + "is the startup
  login item present?" + "is there a gateway process running?" so the status
  command keeps working regardless of which install path was taken.
* Quoting is tricky: schtasks parses ``/TR`` itself and cmd.exe parses the
  generated ``gateway.cmd``. Those are DIFFERENT parsers. We keep two
  separate quote helpers (same pattern OpenClaw uses) and never cross them.
* All of this is Windows-only. ``import`` paths are still safe on POSIX but
  the functions raise if called on non-Windows.

### 顶层函数

#### def `get_task_name() -> str`

Scheduled Task name, scoped per profile.

Default profile: ``Hermes_Gateway``
Named profile X: ``Hermes_Gateway_<X>``

#### def `get_task_script_path() -> Path`

The generated ``gateway.cmd`` wrapper kept beside the VBS launcher.

Lives under ``%LOCALAPPDATA%\hermes\gateway-service\<task_name>.cmd``
(or ``<HERMES_HOME>/gateway-service/<task_name>.cmd`` so per-profile
Hermes installs stay self-contained).

#### def `get_startup_entry_path() -> Path`

#### def `windowless_gateway_restart_spec(run_argv: list[str]) -> tuple[list[str], str, dict[str, str]]`

Rewrite a console-``python.exe`` gateway argv into a windowless one.

The post-update restart paths build their respawn command from
``get_python_path()`` which returns the venv's console ``python.exe``.
On Windows — especially with uv-created venvs — launching that
interpreter (even with ``CREATE_NO_WINDOW``) leaves a persistent
console window: ``venv\Scripts\python.exe`` is a launcher shim that
re-execs the *base* console interpreter, which allocates its own
conhost.  ``CREATE_NO_WINDOW`` cannot suppress that second window.
See ``_resolve_detached_python`` for the gory details.

This mirrors what ``_build_gateway_argv`` / ``_spawn_detached`` do for
a clean start: swap the interpreter for the windowless ``pythonw.exe``
(base interpreter for uv venvs) and return the cwd + env overlay
(VIRTUAL_ENV, PYTHONPATH) the base interpreter needs to resolve the
``hermes_cli`` package without the venv launcher's site config.

Returns ``(new_argv, working_dir, env_overlay)``.  ``new_argv``
preserves every argument after the interpreter (``-m hermes_cli.main
[--profile X] gateway run [--replace]``) verbatim.  On non-Windows, or
if ``run_argv`` doesn't start with a resolvable python, the argv is
returned unchanged with an empty overlay.

#### def `install(force: bool = False, start_now: bool | None = None, start_on_login: bool | None = None, elevated_handoff: bool = False) -> None`

Install the gateway as a Windows Scheduled Task (with Startup fallback).

Idempotent: re-running updates the task to point at the current python/
project paths. ``force`` is accepted for API parity with ``launchd_install``
/ ``systemd_install`` but isn't needed — we always reconcile.

**异常**: `RuntimeError`

#### def `uninstall() -> None`

Remove both the Scheduled Task and the Startup-folder fallback, if present.

#### def `is_task_registered() -> bool`

#### def `is_startup_entry_installed() -> bool`

#### def `is_installed() -> bool`

True when either the schtasks entry or the Startup fallback is present.

#### def `query_task_status() -> dict[str, str]`

Parse ``schtasks /Query /V /FO LIST`` and pull the interesting keys.

#### def `status(deep: bool = False) -> None`

Print a status report for the Windows gateway service.

#### def `start() -> None`

Start the gateway using the canonical detached Windows launch path.

#### def `stop() -> None`

Stop the gateway.

Writes the planned-stop marker first so the gateway can drain
in-flight agents and persist ``resume_pending`` before exit (the
gateway's marker-watcher thread picks this up — Windows asyncio
can't deliver SIGTERM to the loop, so the marker is our only IPC).
Then escalates with bounded Windows process termination against the
known gateway PID(s).

#### def `restart() -> None`

Stop the gateway then start it again.

Waits for the old gateway to be authoritatively gone before relaunching --
otherwise ``start()``'s "already running" guard sees the still-draining old
process and no-ops, and when that process later exits nothing replaces it (a
silent outage). Fails loudly if the process can't be cleared or the relaunch
doesn't produce a running gateway.

**异常**: `RuntimeError`


## hermes_cli.goals

### 模块文档

Persistent session goals — the Ralph loop for Hermes.

A goal is a free-form user objective that stays active across turns. After
each turn completes, a small judge call asks an auxiliary model "is this
goal satisfied by the assistant's last response?". If not, Hermes feeds a
continuation prompt back into the same session and keeps working until the
goal is done, turn budget is exhausted, the user pauses/clears it, or the
user sends a new message (which takes priority and pauses the goal loop).

State is persisted in SessionDB's ``state_meta`` table keyed by
``goal:<session_id>`` so ``/resume`` picks it up.

Design notes / invariants:

- The continuation prompt is just a normal user message appended to the
  session via ``run_conversation``. No system-prompt mutation, no toolset
  swap — prompt caching stays intact.
- Judge failures are fail-OPEN: ``continue``. A broken judge must not wedge
  progress; the turn budget is the backstop.
- When a real user message arrives mid-loop it preempts the continuation
  prompt and also pauses the goal loop for that turn (we still re-judge
  after, so if the user's message happens to complete the goal the judge
  will say ``done``).
- This module has zero hard dependency on ``cli.HermesCLI`` or the gateway
  runner — both wire the same ``GoalManager`` in.

Nothing in this module touches the agent's system prompt or toolset.

### class GoalContract

> 继承: `object` ｜ 方法数: 4（公开 4）

Optional structured completion contract for a goal.

Each field is free-form prose the user (or :func:`draft_contract`)
supplies. Empty fields are omitted everywhere — a goal with no contract
behaves exactly like the original free-form goal. The contract is woven
into both the continuation prompt (so the agent targets the verification
surface and respects constraints) and the judge prompt (so "done" is
decided against evidence, not vibes).

#### def `is_empty(self) -> bool`

#### def `to_dict(self) -> Dict[str, str]`

#### classmethod `from_dict(cls, data: Optional[Dict[str, Any]]) -> GoalContract`

#### def `render_block(self) -> str`

Render non-empty contract fields as a labelled block. Empty
contract → empty string (callers skip the section entirely).


### class GoalState

> 继承: `object` ｜ 方法数: 4（公开 4）

Serializable goal state stored per session.

#### def `to_json(self) -> str`

#### classmethod `from_json(cls, raw: str) -> GoalState`

#### def `has_contract(self) -> bool`

#### def `render_subgoals_block(self) -> str`

Render the subgoals as a numbered ``- N. text`` block. Empty
when no subgoals exist.


### class GoalManager

> 继承: `object` ｜ 方法数: 24（公开 23）

Per-session goal state + continuation decisions.

The CLI and gateway each hold one ``GoalManager`` per live session.

Methods:

- ``set(goal)`` — start a new standing goal.
- ``clear()`` — remove the active goal.
- ``pause()`` / ``resume()`` — explicit user controls.
- ``status()`` — printable one-liner.
- ``evaluate_after_turn(last_response)`` — call the judge, update state,
  and return a decision dict the caller uses to drive the next turn.
- ``next_continuation_prompt()`` — the canonical user-role message to
  feed back into ``run_conversation``.

#### def `__init__(session_id: str, default_max_turns: int = DEFAULT_MAX_TURNS)`

#### property `state(self) -> Optional[GoalState]`

#### def `is_active(self) -> bool`

#### def `has_goal(self) -> bool`

#### def `has_contract(self) -> bool`

#### def `status_line(self) -> str`

#### def `set(self, goal: str, max_turns: Optional[int] = None, contract: Optional[GoalContract] = None) -> GoalState`

**异常**: `ValueError`

#### def `set_contract(self, contract: GoalContract) -> Optional[GoalState]`

Attach or replace the completion contract on the active goal.

Returns the updated state, or None when there is no goal to attach to.

#### def `pause(self, reason: str = 'user-paused') -> Optional[GoalState]`

#### def `resume(self, reset_budget: bool = True) -> Optional[GoalState]`

#### def `clear(self) -> None`

#### def `mark_done(self, reason: str) -> None`

#### def `add_subgoal(self, text: str) -> str`

Append a user-added criterion to the active goal. Requires
``has_goal()``; raises ``RuntimeError`` otherwise.

Returns the cleaned text so the caller can show it back to the user.

**异常**: `RuntimeError`, `ValueError`

#### def `remove_subgoal(self, index_1based: int) -> str`

Remove a subgoal by 1-based index. Returns the removed text.

**异常**: `RuntimeError`, `IndexError`

#### def `clear_subgoals(self) -> int`

Wipe all subgoals. Returns the previous count.

**异常**: `RuntimeError`

#### def `render_subgoals(self) -> str`

Public helper for the /subgoal slash command.

#### def `wait_on(self, pid: int, reason: str = '') -> GoalState`

Park the goal loop on a background process PID.

While the PID is alive, ``evaluate_after_turn`` returns
``should_continue=False`` without burning a turn or calling the
judge — the loop quiesces instead of re-poking the agent into busy
work. The barrier auto-clears when the process exits. Requires an
active goal. For a process with a watch_patterns/notify_on_complete
trigger, prefer ``wait_on_session`` so a mid-run trigger (not just
exit) releases the barrier.

**异常**: `RuntimeError`, `ValueError`

#### def `wait_on_session(self, session_id: str, reason: str = '') -> GoalState`

Park the goal loop on a process_registry session's OWN trigger.

Unlike ``wait_on`` (which releases only on PID exit), this releases
when the session's trigger fires: it exits, OR — if it was started
with ``watch_patterns`` — its pattern matches. This is the right
barrier for a long-lived watcher/server/poller that signals mid-run
and may never exit. Requires an active goal.

**异常**: `RuntimeError`, `ValueError`

#### def `wait_for_seconds(self, seconds: int, reason: str = '') -> GoalState`

Park the goal loop until ``seconds`` from now have elapsed.

Time-based counterpart to ``wait_on`` — for backoff / cooldown waits
where there's no process to track (e.g. the agent is rate-limited).
The barrier auto-clears once the deadline passes. Requires an active
goal.

**异常**: `RuntimeError`, `ValueError`

#### def `stop_waiting(self) -> bool`

Clear any active wait barrier (pid / session / time). Returns True
if one was cleared.

#### def `is_waiting(self) -> bool`

True iff a barrier is set AND not yet satisfied.

Session barrier: active until the process exits or its watch-pattern
trigger fires. Pid barrier: active while the process is alive. Time
barrier: active until the deadline passes. Side effect: a satisfied
barrier is cleared here (lazy auto-clear) so the next evaluation
resumes normal judging.

#### def `evaluate_after_turn(self, last_response: str, user_initiated: bool = True, background_processes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]`

Run the judge and update state. Return a decision dict.

``user_initiated`` distinguishes a real user prompt (True) from a
continuation prompt we fed ourselves (False). Both increment
``turns_used`` because both consume model budget.

``background_processes`` is the live ``process_registry.list_sessions()``
snapshot for this session. It's handed to the judge so it can decide
to WAIT on an in-flight process (CI poller, build, ...) instead of
re-poking the agent — the automatic counterpart to ``/goal wait``.

Decision keys:
  - ``status``: current goal status after update
  - ``should_continue``: bool — caller should fire another turn
  - ``continuation_prompt``: str or None
  - ``verdict``: "done" | "continue" | "wait" | "skipped" | "inactive"
  - ``reason``: str
  - ``message``: user-visible one-liner to print/send

#### def `next_continuation_prompt(self) -> Optional[str]`

#### def `render_contract(self) -> str`

Public helper for the /goal show + /goal draft slash commands.


### 顶层函数

#### def `parse_contract(text: str) -> Tuple[str, GoalContract]`

Split user-typed goal text into a headline + structured contract.

Supports inline ``field: value`` lines so power users can type a full
contract in one shot, e.g.::

    Migrate auth to JWT
    verify: the auth test suite passes
    constraints: keep the public /login response shape unchanged
    boundaries: only touch services/auth and its tests
    stop when: a schema change needs product sign-off

The first non-field line(s) become the goal headline; recognized
``field:`` lines populate the contract. Lines for the same field are
joined. Unrecognized prefixes stay part of the headline, so a plain
free-form goal with an incidental colon (``Fix bug: the parser``)
is NOT mangled — only lines whose prefix matches a known alias are
pulled out. Returns ``(headline, contract)``.

#### def `load_goal(session_id: str) -> Optional[GoalState]`

Load the goal for a session, or None if none exists.

#### def `save_goal(session_id: str, state: GoalState) -> None`

Persist a goal to SessionDB. No-op if DB unavailable.

#### def `clear_goal(session_id: str) -> None`

Mark a goal cleared in the DB (preserved for audit, status=cleared).

#### def `migrate_goal_to_session(old_session_id: str, new_session_id: str, reason: str = '') -> bool`

Carry a persistent /goal from a parent session to its continuation.

Context compression rotates ``session_id`` to a fresh child session,
but ``load_goal`` does a flat ``goal:<session_id>`` lookup with no
parent-lineage walk — so an active goal silently dies at the
compaction boundary (#33618). Copy the goal onto the new session and
archive the old row as ``cleared`` so exactly one active goal row
exists per logical conversation (avoids the "two active goals"
hazard of a pure copy).

Returns True when a goal was migrated, False when there was nothing
to migrate or the DB was unavailable. Best-effort and never raises —
a failure here must not block compression.

#### def `judge_goal(goal: str, last_response: str, timeout: float = DEFAULT_JUDGE_TIMEOUT, subgoals: Optional[List[str]] = None, background_processes: Optional[List[Dict[str, Any]]] = None, contract: Optional[GoalContract] = None) -> Tuple[str, str, bool, Optional[Dict[str, Any]], bool]`

Ask the auxiliary model whether the goal is satisfied.

Returns ``(verdict, reason, parse_failed, wait_directive, transport_failed)`` where verdict
is ``"done"``, ``"continue"``, ``"wait"``, or ``"skipped"`` (when the
judge couldn't be reached). ``wait_directive`` is set only for ``"wait"``
(``{"pid": int}`` or ``{"seconds": int}``); ``None`` otherwise.

``parse_failed`` is True only when the judge call succeeded but its output
was unusable (empty or non-JSON). API/transport errors return False — they
are transient and should fail-open silently.

``transport_failed`` is True only when the judge couldn't reach the API at
all (auth 401, timeout, DNS, connection error).  Repeated transport
failures signal a permanent config problem (e.g. invalid API key).  Callers
use this flag to auto-pause after N consecutive transport failures (see
``DEFAULT_MAX_CONSECUTIVE_TRANSPORT_FAILURES``). Callers use this flag to
auto-pause after N consecutive parse failures (see
``DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES``).

``subgoals`` is an optional list of user-added criteria (from
``/subgoal``) factored into the verdict. ``background_processes`` is the
live ``process_registry.list_sessions()`` snapshot; when the agent is
waiting on one (a CI poller, build, etc.) the judge can return a ``wait``
verdict naming its pid, parking the loop instead of re-poking.
``contract`` is an optional structured completion contract; when present
the judge decides DONE strictly against its Verification criterion and
refuses completion when a Constraint was violated. All three are additive
— a contract, subgoals, and a background-process list can coexist in one
judge prompt; when none are set, behavior is identical to the original
free-form judge.

This is deliberately fail-open: transport errors return ``("continue", ..., ..., None, True)``
— the ``transport_failed=True`` flag lets callers track and auto-pause after
N consecutive transport failures (see
``DEFAULT_MAX_CONSECUTIVE_TRANSPORT_FAILURES``) so a permanently broken
judge doesn't burn the entire turn budget.

#### def `gather_background_processes(task_id: Optional[str] = None) -> List[Dict[str, Any]]`

Return the live background-process snapshot for the goal judge.

Thin, fail-safe wrapper over ``process_registry.list_sessions(task_id)``.
Returns only RUNNING processes (an exited one is nothing to wait on) and
never raises — any import/registry failure yields ``[]`` so the goal loop
degrades to its pre-wait-barrier behavior (judge just won't see processes).
The drivers (CLI + gateway) call this and pass the result into
``GoalManager.evaluate_after_turn(background_processes=...)``.

#### def `draft_contract(objective: str, timeout: float = DEFAULT_JUDGE_TIMEOUT) -> Optional[GoalContract]`

Expand a plain-language objective into a structured completion contract.

Uses the ``goal_judge`` auxiliary task (main-model-first, cache-safe — it
is a side LLM call, not a conversation turn). Returns a populated
:class:`GoalContract` on success, or ``None`` when the auxiliary client is
unavailable or the model's reply can't be parsed. Callers fall back to a
bare free-form goal in that case, so a missing/weak aux model never blocks
setting a goal.

#### def `run_kanban_goal_loop(task_id: str, goal_text: str, run_turn, task_status_fn, block_fn, max_turns: int = DEFAULT_MAX_TURNS, first_response: str = '', log = None) -> Dict[str, Any]`

Drive a kanban worker through a Ralph-style goal loop.

The dispatcher spawns a goal-mode worker exactly like a normal worker
(``hermes -p <profile> chat -q "work kanban task <id>"``). The worker's
first turn has already run by the time this is called; ``first_response``
is that turn's reply. From here we:

1. Check whether the worker already terminated the task (called
   ``kanban_complete`` / ``kanban_block``). If so, stop — nothing to do.
2. Otherwise judge the latest response against ``goal_text`` (the card's
   title + body). ``continue`` → feed a continuation prompt and run
   another turn IN THE SAME SESSION via ``run_turn``. ``done`` but the
   task is still open → one explicit "call kanban_complete" nudge.
3. When the turn budget is exhausted and the worker still hasn't
   terminated the task, ``block_fn`` is invoked so the card lands in a
   sticky ``blocked`` state for human review (NOT a silent exit).

This function performs NO SessionDB persistence — a worker process is
ephemeral, so the turn budget lives in a local counter. It is fully
decoupled from the CLI for testability: callers inject ``run_turn``
(str -> str), ``task_status_fn`` (() -> str|None), and ``block_fn``
(reason: str -> None).

Returns a decision dict: ``{"outcome", "turns_used", "reason"}`` where
outcome is one of ``"completed_by_worker"``, ``"blocked_budget"``,
``"blocked_by_worker"``, or ``"stopped"``.


## hermes_cli.gui_uninstall

### 模块文档

Hermes Desktop (Chat GUI) uninstaller.

The desktop GUI ships in two shapes and this module knows how to find and
remove the artifacts of both, on Linux, macOS, and Windows, WITHOUT touching
the Python agent or the user's config/data:

  1. Source-built GUI (``hermes desktop`` / ``hermes gui``)
     Built inside the agent checkout under ``$HERMES_HOME/hermes-agent/``:
       - ``apps/desktop/dist``      (compiled renderer)
       - ``apps/desktop/release``   (electron-builder unpacked app + installers)
       - ``apps/desktop/node_modules`` and the workspace-root ``node_modules``
         (Electron itself, ~200MB) — only removed on a GUI uninstall because
         the agent does not need them.
       - ``$HERMES_HOME/desktop-build-stamp.json`` (the build freshness stamp)

  2. Packaged distributable (DMG / NSIS / AppImage / deb / rpm)
     Installed by the OS to a standard application location and carrying its
     own bundled Electron + a per-user Electron ``userData`` directory:
       - macOS:   ``/Applications/Hermes.app`` or ``~/Applications/Hermes.app``
       - Windows: ``%LOCALAPPDATA%\Programs\Hermes`` (NSIS per-user)
       - Linux:   ``~/.local/share/applications`` .desktop entry + AppImage

In both shapes the Electron runtime keeps a ``userData`` directory keyed on
the app name ("Hermes"), separate from ``$HERMES_HOME``:
  - macOS:   ``~/Library/Application Support/Hermes``
  - Windows: ``%APPDATA%\Hermes``
  - Linux:   ``$XDG_CONFIG_HOME/Hermes`` (default ``~/.config/Hermes``)

This holds the desktop's own ``connection.json`` / ``updates.json`` and
Chromium cache — pure GUI state, safe to remove on a GUI uninstall.

The functions here are deliberately import-light and side-effect-free at
import time so the Electron main process can shell out to
``hermes uninstall --gui`` (and friends) without paying for the full CLI.

### 顶层函数

#### def `log_info(msg: str)`

#### def `log_success(msg: str)`

#### def `log_warn(msg: str)`

#### def `desktop_userdata_dir() -> Path`

Return the Electron ``userData`` directory for the desktop app.

Mirrors Electron's ``app.getPath('userData')`` for an app named "Hermes"
on each platform. This is GUI-only state (connection.json, updates.json,
Chromium cache) and never holds agent config or sessions.

#### def `source_built_gui_artifacts(hermes_home: Path) -> list[Path]`

GUI build artifacts produced by ``hermes desktop`` inside the checkout.

These are removable on a GUI uninstall without harming the agent: the
Python agent runs from ``hermes-agent/`` source + ``venv/`` and never
needs the Electron build output or node_modules.

#### def `packaged_gui_app_paths() -> list[Path]`

Standard install locations of the packaged desktop distributable.

Returns every candidate for the current OS; the caller filters to those
that actually exist. We never glob system-wide — only the well-known
electron-builder output locations for the "Hermes" product.

#### def `agent_is_installed(hermes_home: Path) -> bool`

Return True when a usable Python agent install exists under HERMES_HOME.

Used by the desktop UI to decide which uninstall options to offer: if the
agent isn't present (a future "lite" GUI-only client), the "remove agent"
options are hidden.

#### def `gui_is_installed(hermes_home: Path) -> bool`

Return True when any desktop GUI artifact exists (built or packaged).

#### def `gui_install_summary(hermes_home: Path | None = None) -> dict`

Structured snapshot of what's installed, for the desktop UI to render.

Returns JSON-serializable primitives so the Electron main process can
forward it to the renderer via IPC (paths as strings, booleans for the
high-level questions the UI gates options on).

#### def `uninstall_gui(hermes_home: Path | None = None, remove_userdata: bool = True) -> list[Path]`

Remove the desktop GUI's artifacts, leaving the agent + user data intact.

Removes:
  - source-built GUI artifacts (dist/release/node_modules/build-stamp)
  - the packaged app bundle / install dir (best-effort; deb/rpm need the
    system package manager and are reported, not force-removed)
  - the Electron ``userData`` directory (unless ``remove_userdata=False``)

Never touches ``hermes-agent/hermes_cli`` (agent source), ``venv/``, or any
config / sessions / .env under ``$HERMES_HOME``.

Returns the list of paths actually removed.


## hermes_cli.hooks

### 模块文档

hermes hooks — inspect and manage shell-script hooks.

Usage::

    hermes hooks list
    hermes hooks test <event> [--for-tool X] [--payload-file F]
    hermes hooks revoke <command>
    hermes hooks doctor

Consent records live under ``~/.hermes/shell-hooks-allowlist.json`` and
hook definitions come from the ``hooks:`` block in ``~/.hermes/config.yaml``
(the same config read by the CLI / gateway at startup).

This module is a thin CLI shell over :mod:`agent.shell_hooks`; every
shared concern (payload serialisation, response parsing, allowlist
format) lives there.

### 顶层函数

#### def `hooks_command(args) -> None`

Entry point for ``hermes hooks`` — dispatches to the requested action.


## hermes_cli.input_sanitize

### 模块文档

Sanitize user prompt text leaked from terminal / paste control sequences.

### 顶层函数

#### def `strip_leaked_bracketed_paste_wrappers(text: str) -> str`

Strip leaked bracketed-paste wrapper markers from user-visible text.

Defensive normalization for cases where terminal/prompt_toolkit parsing
fails and bracketed-paste markers end up in the buffer as literal text.

Canonical wrappers are stripped unconditionally. Degraded visible forms like
``[200~`` / ``[201~`` and ``00~`` / ``01~`` are removed only at boundaries
so embedded literals such as ``literal[200~tag`` stay intact.

#### def `collapse_repeated_input_artifacts(text: str, min_repeats: int = 4) -> str`

Drop a trailing run of the desktop ~[[e corruption signature (#62557).

#### def `sanitize_user_prompt_text(text: str) -> str`

Normalize user-authored prompt text before persistence or model input.


## hermes_cli.inventory

### 模块文档

Provider/model inventory context — shared substrate for the dashboard
``/api/model/options``, the TUI ``model.options``/``model.save_key``
JSON-RPC handlers, and the interactive picker.

Before this module the three call-sites each duplicated:

1. The 17-LOC config-slice that pulls ``model.{default,name,provider,base_url}``,
   ``providers:``, and ``custom_providers:`` out of ``load_config()``;
2. The call into ``list_authenticated_providers`` with the resulting kwargs;
3. (TUI only) a 45-LOC post-pass that merges authenticated rows with
   unconfigured ``CANONICAL_PROVIDERS`` rows and emits ``authenticated``/
   ``auth_type``/``key_env``/``warning`` hints for the picker UI.

Consolidating those three steps into one entry point eliminates two bugs
the duplicates were hiding:

- The dashboard read ``cfg.get("custom_providers")`` directly, missing the
  v12+ keyed ``providers:`` form (which the TUI handled via
  ``get_compatible_custom_providers``).
- The TUI's canonical-merge keyed on ``is_user_defined`` to decide
  ordering. Section 3 of ``list_authenticated_providers`` sets
  ``is_user_defined=True`` even for canonical slugs that appear in the
  ``providers:`` config dict, which silently demoted them to the tail of
  the picker. ``_reorder_canonical`` keys on slug membership instead.

Substrate facts (verified May 2026):
- ``list_authenticated_providers`` already populates each row's
  ``models`` from the curated catalog (same source as the picker). Do
  NOT call ``provider_model_ids()`` per row to "freshen" — that bypasses
  curation and pulls in non-agentic models (Nous /models returns ~400
  IDs including TTS, embeddings, rerankers, image/video generators).

### class ConfigContext

> 继承: `object` ｜ 方法数: 1（公开 1）

Snapshot of the model + provider config every inventory caller
needs. Built once via ``load_picker_context()``; the TUI overlays
live agent state via ``with_overrides()`` before passing through.

#### def `with_overrides(self, current_provider: Optional[str] = None, current_model: Optional[str] = None, current_base_url: Optional[str] = None) -> ConfigContext`

Return a copy with truthy overrides applied.

Truthy-only because the TUI reads agent attributes that may be
empty strings before an agent is spawned — empties must NOT
clobber the disk-config values.


### 顶层函数

#### def `load_picker_context() -> ConfigContext`

Load the disk-config snapshot every consumer needs.

Replaces the inline 17-LOC config-slice that ``web_server.py`` and
``tui_gateway/server.py`` (×2 sites) used to do.

#### def `build_models_payload(ctx: ConfigContext, explicit_only: bool = False, include_unconfigured: bool = False, picker_hints: bool = False, canonical_order: bool = False, pricing: bool = False, capabilities: bool = False, force_fresh_nous_tier: bool = False, refresh: bool = False, probe_custom_providers: bool = True, probe_current_custom_provider: bool = False, max_models: int | None = None) -> dict`

Build the ``{providers, model, provider}`` shape every consumer
needs from a single substrate call.

Flags:
- ``explicit_only``: keep only providers the user explicitly configured
  (current provider, providers from config, or providers backed by
  provider-specific env vars). This hides ambient / auto-seeded
  credentials from desktop chat pickers.
- ``include_unconfigured``: append ``CANONICAL_PROVIDERS`` rows that
  ``list_authenticated_providers`` didn't emit (TUI uses this to show
  the full provider universe in the picker).
- ``picker_hints``: add ``authenticated``/``auth_type``/``key_env``/
  ``warning`` per row (TUI ``ModelPickerDialog`` shape).
- ``canonical_order``: reorder canonical-slug rows to
  ``CANONICAL_PROVIDERS`` declaration order; truly-custom rows go
  last (TUI display order).
- ``pricing``: enrich each row with formatted per-model pricing and,
  for Nous, ``free_tier``/``unavailable_models`` so the GUI picker can
  show $/Mtok columns and gate paid models on free accounts —
  mirroring the ``hermes model`` CLI picker. Adds network calls
  (pricing fetch + Nous tier check); only set for interactive pickers.
- ``capabilities``: add a per-row ``capabilities`` map
  ``{model: {fast, reasoning}}`` so pickers can gate the model-options
  controls (fast toggle / reasoning) to what each model actually
  supports, instead of offering knobs the backend would reject.
- ``force_fresh_nous_tier``: bypass the short Nous free-tier cache when
  selecting Portal-recommended Nous models and applying tier gating. Keep
  this false for UI picker opens; explicit auth/model flows can opt in
  when they need freshly-purchased credits to show up immediately.
- ``refresh``: bust the per-provider model-id disk cache so every row
  re-fetches its live catalog. Set only for an explicit user-triggered
  "refresh models" action; normal picker opens leave it false to stay
  snappy on the 1h cache.
- ``probe_custom_providers``: allow saved custom/provider endpoints to
  run live ``/models`` discovery while building the payload. GUI picker
  opens should leave this false unless the user explicitly refreshes; the
  row can still render its configured model immediately, and slow/offline
  local endpoints no longer block the dialog.
- ``probe_current_custom_provider``: when ``probe_custom_providers`` is
  false, still live-probe the current custom endpoint. This keeps normal
  GUI/TUI picker opens fast while making the active custom provider's model
  list match the classic CLI picker.


## hermes_cli.journey

### 模块文档

``hermes journey`` — what Hermes has learned, on a timeline.

A terminal-native rendition of the desktop Star Map / Memory Graph: a horizontal
timeline bar chart of learned skills and memories over time (oldest at top,
newest at bottom) plus the playable constellation scrubber. Graph assembly,
layout, and the (ported-from-desktop) palette all live in
``agent.learning_graph`` / ``agent.learning_graph_render`` so the CLI, the TUI
``/journey`` overlay, and the desktop panel draw the same data.

### 顶层函数

#### def `register_cli(parent: argparse.ArgumentParser) -> None`

#### def `cmd_journey(args: argparse.Namespace) -> int`


## hermes_cli.kanban

### 模块文档

CLI for the Hermes Kanban board — ``hermes kanban …`` subcommand.

Exposes the full Kanban command surface documented in the design spec
(``docs/hermes-kanban-v1-spec.pdf``).  All DB work is delegated to
``kanban_db``.  This module adds:

  * Argparse subcommand construction (``build_parser``).
  * Argument dispatch (``kanban_command``).
  * Output formatting (plain text + ``--json``).
  * A short shared helper that parses a single slash-style string
    (used by ``/kanban …`` in CLI and gateway) and forwards it to the
    argparse surface.

### 顶层函数

#### def `build_parser(parent_subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser`

Attach the ``kanban`` subcommand tree under an existing subparsers.

Returns the top-level ``kanban`` parser so caller can ``set_defaults``.

#### def `kanban_command(args: argparse.Namespace) -> int`

Entry point from ``hermes kanban …`` argparse dispatch.

Returns a shell-style exit code (0 on success, non-zero on error).

#### def `run_slash(rest: str) -> str`

Execute a ``/kanban …`` string and return captured stdout/stderr.

``rest`` is everything after ``/kanban`` (may be empty).  Used from
both the interactive CLI (``self._handle_kanban_command``) and the
gateway (``_handle_kanban_command``) so formatting is identical.


## hermes_cli.kanban_db

### 模块文档

SQLite-backed Kanban board for multi-profile, multi-project collaboration.

In a fresh install the board lives at ``<root>/kanban.db`` where
``<root>`` is the **shared Hermes root** (the parent of any active
profile). Profiles intentionally collapse onto a shared board: it IS
the cross-profile coordination primitive. A worker spawned with
``hermes -p <profile>`` joins the same board as the dispatcher that
claimed the task. The same applies to ``<root>/kanban/workspaces/`` and
``<root>/kanban/logs/``.

**Multiple boards (projects):** users can create additional boards to
separate unrelated streams of work (e.g. one per project / repo / domain).
Each board is a directory under ``<root>/kanban/boards/<slug>/`` with
its own ``kanban.db``, ``workspaces/``, and ``logs/``. All boards share
the profile's Hermes home but are otherwise isolated: a worker spawned
for a task on board ``atm10-server`` sees only that board's tasks,
cannot enumerate other boards, and its dispatcher ticks don't touch
other boards' DBs.

The first (and for single-project users, only) board is ``default``.
For back-compat its on-disk DB is ``<root>/kanban.db`` (not
``boards/default/kanban.db``), so installs that predate the boards
feature keep working with zero migration. See :func:`kanban_db_path`.

Board resolution order (highest precedence first, all optional):

* ``board=`` argument passed directly to :func:`connect` / :func:`init_db`
  (explicit — used by the CLI ``--board`` flag and the dashboard
  ``?board=...`` query param).
* ``HERMES_KANBAN_BOARD`` env var (used by the dispatcher to pin workers
  to the board their task lives on — workers cannot see other boards).
* ``HERMES_KANBAN_DB`` env var (pins the DB file path directly — legacy
  override still honoured; highest precedence when the file path itself
  is what the caller wants to force).
* ``<root>/kanban/current`` — a one-line text file holding the slug of
  the "currently selected" board. Written by ``hermes kanban boards
  switch <slug>``. When absent, the active board is ``default``.

In standard installs ``<root>`` is ``~/.hermes``. In Docker / custom
deployments where ``HERMES_HOME`` points outside ``~/.hermes`` (e.g.
``/opt/hermes``), ``<root>`` is ``HERMES_HOME``. Legacy env-var
overrides still work:

* ``HERMES_KANBAN_DB`` — pin the database file path directly.
* ``HERMES_KANBAN_WORKSPACES_ROOT`` — pin the workspaces root directly.
* ``HERMES_KANBAN_HOME`` — pin the umbrella root that anchors kanban
  paths. Useful for tests and unusual deployments.

The dispatcher injects ``HERMES_KANBAN_DB``,
``HERMES_KANBAN_WORKSPACES_ROOT``, and ``HERMES_KANBAN_BOARD`` into
worker subprocess env so workers converge on the exact DB the
dispatcher used to claim their task — even under unusual symlink or
Docker layouts.

Schema is intentionally small: tasks, task_links, task_comments,
task_events.  The ``workspace_kind`` field decouples coordination from git
worktrees so that research / ops / digital-twin workloads work alongside
coding workloads.  See ``docs/hermes-kanban-v1-spec.pdf`` for the full
design specification.

Concurrency strategy: WAL mode + ``BEGIN IMMEDIATE`` for write
transactions + compare-and-swap (CAS) updates on ``tasks.status`` and
``tasks.claim_lock``.  SQLite serializes writers via its WAL lock, so at
most one claimer can win any given task.  Losers observe zero affected
rows and move on -- no retry loops, no distributed-lock machinery.
The CAS coordination is **per-board** — each board is a separate DB,
so multi-board installs get the same atomicity guarantees without any
new locking.

### class Task

> 继承: `object` ｜ 方法数: 1（公开 1）

In-memory view of a row from the ``tasks`` table.

#### classmethod `from_row(cls, row: sqlite3.Row) -> Task`


### class Run

> 继承: `object` ｜ 方法数: 1（公开 1）

In-memory view of a ``task_runs`` row.

A run is one attempt to execute a task — created on claim, closed
on complete/block/crash/timeout/spawn_failure/reclaim. Multiple runs
per task when retries happen. Carries the claim machinery, PID,
heartbeat, and the structured handoff summary that downstream workers
read via ``build_worker_context``.

#### classmethod `from_row(cls, row: sqlite3.Row) -> Run`


### class Comment

> 继承: `object` ｜ 方法数: 0（公开 0）


### class Attachment

> 继承: `object` ｜ 方法数: 0（公开 0）

In-memory view of a row from the ``task_attachments`` table.


### class Event

> 继承: `object` ｜ 方法数: 0（公开 0）


### class KanbanDbCorruptError

> 继承: `RuntimeError` ｜ 方法数: 1（公开 0）

Raised when an existing kanban DB file fails integrity checks.

Fail-closed guard against silent recreation of a corrupt board file,
which would otherwise destroy the user's tasks. Carries both the
original path and the timestamped backup we made before refusing.

#### def `__init__(db_path: Path, backup_path: Optional[Path], reason: str)`


### class AttachmentTooLarge

> 继承: `ValueError` ｜ 方法数: 0（公开 0）

Raised when an attachment exceeds the configured size cap.

Subclasses :class:`ValueError` so generic ``except ValueError`` handlers
(e.g. the dashboard's 400 fallback) still catch it, while callers that
want a distinct user-facing message (the tool/CLI 413-equivalent) can
catch it specifically.


### class HallucinatedCardsError

> 继承: `ValueError` ｜ 方法数: 1（公开 0）

Raised by ``complete_task`` when ``created_cards`` contains ids
that don't exist or weren't created by the completing worker.

The phantom list is attached as ``.phantom`` for callers that want
structured access. Kept as ``ValueError`` subclass so existing
tool-error handlers treat it as a recoverable user error.

#### def `__init__(phantom: list[str], completing_task_id: str)`


### class ArtifactPreservationError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when a declared scratch deliverable cannot be preserved.


### class DispatchResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Outcome of a single ``dispatch`` pass.


### 顶层函数

#### def `scoped_current_board(slug: str)`

Temporarily pin the active board for the current context only.

#### def `kanban_home() -> Path`

Return the shared Hermes root that anchors the kanban board.

Resolution order:

1. ``HERMES_KANBAN_HOME`` env var when set and non-empty (explicit
   override for tests and unusual deployments).
2. ``get_default_hermes_root()``, which already returns ``<root>``
   when ``HERMES_HOME`` is ``<root>/profiles/<name>``, and returns
   ``HERMES_HOME`` directly for Docker / custom deployments.

The kanban board is shared across profiles **by design** (see the
module docstring). Resolving the kanban paths through the active
profile's ``HERMES_HOME`` would silently fork the board per profile,
which breaks the dispatcher / worker handoff.

#### def `boards_root() -> Path`

Return ``<root>/kanban/boards`` — the parent of non-default board dirs.

``default`` is intentionally NOT under this directory — its DB lives at
``<root>/kanban.db`` for back-compat with pre-boards installs. This
function returns the directory where *additional* named boards live,
used by :func:`list_boards` to enumerate them.

#### def `current_board_path() -> Path`

Return the path to ``<root>/kanban/current``.

One-line text file written by ``hermes kanban boards switch <slug>``
to persist the user's board selection across CLI invocations. Absent
by default (meaning: active board is ``default``).

#### def `get_current_board() -> str`

Return the active board slug, honouring the resolution chain.

Order (highest precedence first):

1. ``HERMES_KANBAN_BOARD`` env var (set by the dispatcher on worker
   spawn, or manually for ad-hoc overrides).
2. ``<root>/kanban/current`` on disk (set by ``hermes kanban boards
   switch``), but only when that board still exists.
3. ``DEFAULT_BOARD`` (``"default"``).

A malformed or stale slug at any step falls through to the next layer
with a best-effort warning — the dispatcher must never crash because a
user hand-edited a file or removed a board directory.

#### def `set_current_board(slug: str) -> Path`

Persist ``slug`` as the active board. Returns the file written.

Writes ``<root>/kanban/current``. The caller should validate the slug
exists first (via :func:`board_exists`) — this function does not —
so that ``hermes kanban boards switch <typo>`` returns an error
instead of silently pointing at nothing.

**异常**: `ValueError`

#### def `clear_current_board() -> None`

Remove ``<root>/kanban/current`` so the active board reverts to ``default``.

#### def `board_dir(board: Optional[str] = None) -> Path`

Return the on-disk directory for ``board``.

``default`` is ``<root>/kanban/boards/default/`` **for metadata only**
(board.json + workspaces/ + logs/). Its DB file stays at
``<root>/kanban.db`` for back-compat — see :func:`kanban_db_path`.

All other boards live at ``<root>/kanban/boards/<slug>/`` with
everything inside that directory including the ``kanban.db``.

#### def `board_exists(board: Optional[str] = None) -> bool`

Return True if the board has persisted metadata or a DB on disk.

``default`` is considered to always exist — its DB is created
on first :func:`connect` and there's no way for it to be missing
in a configuration where the kanban feature is usable at all.

#### def `kanban_db_path(board: Optional[str] = None) -> Path`

Return the path to the ``kanban.db`` for ``board``.

Resolution (highest precedence first):

1. ``HERMES_KANBAN_DB`` env var — pins the path directly. Honoured for
   back-compat and for the dispatcher→worker handoff (defense in
   depth: dispatcher injects this into worker env so workers are
   immune to any path-resolution disagreement).
2. When ``board`` arg is None, the active board from
   :func:`get_current_board` is used.
3. Board ``default`` → ``<root>/kanban.db`` (back-compat path).
   Other boards → ``<root>/kanban/boards/<slug>/kanban.db``.

#### def `workspaces_root(board: Optional[str] = None) -> Path`

Return the directory under which ``scratch`` workspaces are created.

Anchored per-board so workspaces don't leak between projects.
``HERMES_KANBAN_WORKSPACES_ROOT`` pins the path directly (highest
precedence) — the dispatcher injects this into worker env.

``default`` keeps the legacy path ``<root>/kanban/workspaces/`` so
that existing scratch workspaces from before the boards feature are
preserved. Other boards use ``<root>/kanban/boards/<slug>/workspaces/``.

#### def `attachments_root(board: Optional[str] = None) -> Path`

Return the directory under which task file attachments are stored.

Mirrors :func:`worker_logs_dir` / :func:`workspaces_root`: anchored
per-board so attachments don't leak between projects. Each task gets
its own ``<root>/.../attachments/<task_id>/`` subdirectory.

``HERMES_KANBAN_ATTACHMENTS_ROOT`` pins the path directly (highest
precedence) for tests and unusual deployments.

``default`` uses ``<root>/kanban/attachments/``; other boards use
``<root>/kanban/boards/<slug>/attachments/``.

Workers (which run with full file-tool access) read attached files
by the absolute path surfaced in :func:`build_worker_context`. On the
local terminal backend — the default for kanban — that path resolves
directly. Remote backends (Docker/Modal) need this directory mounted;
see the kanban docs.

#### def `task_attachments_dir(task_id: str, board: Optional[str] = None) -> Path`

Return the per-task attachment directory ``<root>/<task_id>/``.

#### def `worker_logs_dir(board: Optional[str] = None) -> Path`

Return the directory under which per-task worker logs are written.

``default`` keeps the legacy path ``<root>/kanban/logs/``. Other
boards use ``<root>/kanban/boards/<slug>/logs/``. Logs follow the
board — makes ``hermes kanban log`` unambiguous even when multiple
boards have tasks with the same id.

#### def `board_metadata_path(board: Optional[str] = None) -> Path`

Return the path to ``board.json`` for ``board``.

Stores display metadata (display name, description, icon, color,
created_at). The on-disk slug is the canonical identity; this file
is purely for presentation in the CLI / dashboard.

#### def `read_board_metadata(board: Optional[str] = None) -> dict`

Return ``board.json`` contents (or synthesized defaults).

Never raises — a missing / malformed ``board.json`` falls back to a
synthesised entry so the dashboard always has something to render.
Includes the canonical ``slug`` and ``db_path`` so the caller
doesn't need to reconstruct them.

#### def `write_board_metadata(board: Optional[str], name: Optional[str] = None, description: Optional[str] = None, icon: Optional[str] = None, color: Optional[str] = None, archived: Optional[bool] = None, default_workdir: Optional[str] = None) -> dict`

Create / update ``board.json`` for ``board``.

Preserves any existing fields not mentioned in the call. Sets
``created_at`` on first write. Returns the resulting metadata dict.

#### def `create_board(slug: str, name: Optional[str] = None, description: Optional[str] = None, icon: Optional[str] = None, color: Optional[str] = None, default_workdir: Optional[str] = None) -> dict`

Create a new board directory + DB + metadata. Idempotent.

Returns the resulting metadata. Raises :class:`ValueError` for a
malformed slug; returns the existing metadata (not an error) if the
board already exists — matching ``mkdir -p`` semantics.

**异常**: `class`, `ValueError`

#### def `list_boards(include_archived: bool = True) -> list[dict]`

Enumerate all boards that exist on disk.

Always includes ``default`` (even when the ``boards/default/``
metadata dir doesn't exist, because its DB is at the legacy path).
Other boards are discovered by scanning ``boards/`` for subdirectories
that either contain a ``kanban.db`` or a ``board.json``.

Returns a list of metadata dicts, sorted with ``default`` first and
the rest alphabetically.

#### def `remove_board(slug: str, archive: bool = True) -> dict`

Remove or archive a board.

``archive=True`` (default) moves the board's directory to
``<root>/kanban/boards/_archived/<slug>-<timestamp>/`` so the data
is recoverable. ``archive=False`` deletes the directory outright.

The ``default`` board cannot be removed — raises :class:`ValueError`.
Returns a summary dict describing what happened (``{"slug", "action",
"new_path"}``).

**异常**: `class`, `ValueError`

#### def `connect(db_path: Optional[Path] = None, board: Optional[str] = None) -> sqlite3.Connection`

Open (and initialize if needed) the kanban DB.

WAL mode is enabled on every connection; it's a no-op after the first
time but keeps the code robust if the DB file is ever re-created.

The first connection to a given path auto-runs :func:`init_db` so
fresh installs and test harnesses that construct `connect()`
directly don't have to remember a separate init step. Subsequent
connections skip the schema check via a module-level path cache.

Path resolution:

* ``db_path`` explicit → used as-is (legacy callers, tests).
* ``board`` explicit → resolves to that board's DB.
* Neither → :func:`kanban_db_path` resolves via
  ``HERMES_KANBAN_DB`` env → ``HERMES_KANBAN_BOARD`` env →
  ``<root>/kanban/current`` → ``default``.

#### def `connect_closing(db_path: Optional[Path] = None, board: Optional[str] = None)`

Open a kanban DB connection and guarantee it is closed on exit.

Use this instead of ``with kb.connect() as conn:`` — sqlite3's
built-in connection context manager only commits/rollbacks the
transaction; it does NOT close the file descriptor. In long-lived
processes (gateway, dashboard) that route every kanban operation
through ``connect()`` (e.g. ``run_slash`` dispatching ``/kanban …``
commands, ``decompose_task_endpoint`` calling
``kanban_decompose.decompose_task``), the unclosed connections
accumulate as open FDs to ``kanban.db`` and ``kanban.db-wal``. After
enough operations the process hits the kernel FD limit and dies
with ``[Errno 24] Too many open files``.

See #33159 for the production incident.

The ``connect()`` function itself remains unchanged so callers that
intentionally manage the connection lifetime (tests, long-lived
callers) continue to work.

#### def `init_db(db_path: Optional[Path] = None, board: Optional[str] = None) -> Path`

Create the schema if it doesn't exist; return the path used.

Kept as a public entry point so CLI ``hermes kanban init`` and the
daemon have something explicit to call. Unlike :func:`connect`'s
first-time auto-init (which caches by path), ``init_db`` always
re-runs the migration pass. Callers that know the on-disk schema
may have drifted — tests that write legacy event kinds directly,
external tools that upgrade an old DB file — can call this to
force re-migration.

#### def `write_txn(conn: sqlite3.Connection)`

Context manager for an IMMEDIATE write transaction.

Use for any multi-statement write (creating a task + link, claiming a
task + recording an event, etc.).  A claim CAS inside this context is
atomic -- at most one concurrent writer can succeed.

The explicit ROLLBACK on exception is wrapped in try/except so that
a SQLite auto-rollback (which leaves no active transaction) does not
shadow the original exception with a spurious rollback error.

#### def `create_task(conn: sqlite3.Connection, title: str, body: Optional[str] = None, assignee: Optional[str] = None, created_by: Optional[str] = None, workspace_kind: str = 'scratch', workspace_path: Optional[str] = None, branch_name: Optional[str] = None, tenant: Optional[str] = None, priority: int = 0, parents: Iterable[str] = (), triage: bool = False, idempotency_key: Optional[str] = None, max_runtime_seconds: Optional[int] = None, skills: Optional[Iterable[str]] = None, max_retries: Optional[int] = None, goal_mode: bool = False, goal_max_turns: Optional[int] = None, initial_status: str = 'running', session_id: Optional[str] = None, board: Optional[str] = None, project_id: Optional[str] = None) -> str`

Create a new task and optionally link it under parent tasks.

Returns the new task id.  Status is ``ready`` when there are no
parents (or all parents already ``done``), otherwise ``todo``.
If ``triage=True``, status is forced to ``triage`` regardless of
parents — a specifier/triager is expected to promote the task to
``todo`` once the spec is fleshed out.

If ``idempotency_key`` is provided and a non-archived task with the
same key already exists, returns the existing task's id instead of
creating a duplicate. Useful for retried webhooks / automation that
should not double-write.

``max_runtime_seconds`` caps how long a worker may run before the
dispatcher SIGTERMs (then SIGKILLs after a grace window) and
re-queues the task. ``None`` means no cap (default).

``skills`` is an optional list of skill names to force-load into
the worker when dispatched. Stored as JSON; the dispatcher passes
each name to ``hermes --skills ...``. Use this to pin a task to a
specialist skill (e.g. ``skills=["translation"]`` so the worker loads the
translation skill regardless of the profile's default config).

**异常**: `RuntimeError`, `ValueError`

#### def `get_task(conn: sqlite3.Connection, task_id: str) -> Optional[Task]`

#### def `list_tasks(conn: sqlite3.Connection, assignee: Optional[str] = None, status: Optional[str] = None, tenant: Optional[str] = None, session_id: Optional[str] = None, include_archived: bool = False, limit: Optional[int] = None, order_by: Optional[str] = None, workflow_template_id: Optional[str] = None, current_step_key: Optional[str] = None) -> list[Task]`

**异常**: `ValueError`

#### def `assign_task(conn: sqlite3.Connection, task_id: str, profile: Optional[str]) -> bool`

Assign or reassign a task.  Returns True on success.

Refuses to reassign a task that's currently running (claim_lock set).
Reassign after the current run completes if needed.

**异常**: `RuntimeError`

#### def `link_tasks(conn: sqlite3.Connection, parent_id: str, child_id: str) -> None`

**异常**: `ValueError`

#### def `unlink_tasks(conn: sqlite3.Connection, parent_id: str, child_id: str) -> bool`

#### def `parent_ids(conn: sqlite3.Connection, task_id: str) -> list[str]`

#### def `child_ids(conn: sqlite3.Connection, task_id: str) -> list[str]`

#### def `parent_results(conn: sqlite3.Connection, task_id: str) -> list[tuple[str, Optional[str]]]`

Return ``(parent_id, result)`` for every done parent of ``task_id``.

#### def `add_comment(conn: sqlite3.Connection, task_id: str, author: str, body: str) -> int`

**异常**: `ValueError`

#### def `list_comments(conn: sqlite3.Connection, task_id: str) -> list[Comment]`

#### def `store_attachment_bytes(conn: sqlite3.Connection, task_id: str, filename: str, data: bytes, content_type: Optional[str] = None, uploaded_by: Optional[str] = None, board: Optional[str] = None, max_bytes: Optional[int] = None) -> int`

Validate, size-check, persist a blob, and record its metadata row.

This is the single write path shared by the dashboard endpoint, the
agent toolset (``kanban_attach`` / ``kanban_attach_url``), and the CLI
(``hermes kanban attach``) so name-sanitisation, the size cap, and the
collision-resolution all behave identically everywhere.

Steps: enforce ``max_bytes``, sanitise ``filename`` to a safe basename,
write the bytes under :func:`task_attachments_dir` with a
collision-free name, then insert the ``task_attachments`` row via
:func:`add_attachment`. Returns the new attachment id.

Raises :class:`AttachmentTooLarge` when ``data`` exceeds ``max_bytes``,
or :class:`ValueError` for a bad filename / unknown task. On any failure
after the blob is written (e.g. the task disappeared) the orphaned blob
is removed before re-raising.

**异常**: `class`, `or`, `AttachmentTooLarge`

#### def `add_attachment(conn: sqlite3.Connection, task_id: str, filename: str, stored_path: str, content_type: Optional[str] = None, size: int = 0, uploaded_by: Optional[str] = None) -> int`

Record a file attachment for a task. Returns the new attachment id.

The caller is responsible for writing the blob to ``stored_path``
first (under :func:`task_attachments_dir`); this only persists the
metadata row and appends an ``attached`` event.

**异常**: `ValueError`

#### def `list_attachments(conn: sqlite3.Connection, task_id: str) -> list[Attachment]`

#### def `get_attachment(conn: sqlite3.Connection, attachment_id: int) -> Optional[Attachment]`

#### def `delete_attachment(conn: sqlite3.Connection, attachment_id: int) -> Optional[Attachment]`

Delete an attachment row and its on-disk blob. Returns the removed row.

Returns ``None`` when no row matched. The blob is removed best-effort
(a missing file is not an error); the metadata row is the source of
truth for whether an attachment "exists".

#### def `list_events(conn: sqlite3.Connection, task_id: str) -> list[Event]`

#### def `recompute_ready(conn: sqlite3.Connection, failure_limit: int = None) -> int`

Promote ``todo`` tasks to ``ready`` when all parents are ``done`` or ``archived``.

Returns the number of tasks promoted.  Safe to call inside or outside
an existing transaction; it opens its own IMMEDIATE txn.

``blocked`` tasks are also considered for promotion (so a task
blocked purely by a parent dependency unblocks itself when the
parent completes), *except* in two cases:

1. The most recent block event was a worker-initiated
   ``kanban_block`` — those stay blocked until an explicit
   ``kanban_unblock`` (#28712).

2. The task's ``consecutive_failures`` has reached the effective
   failure limit.  This prevents infinite retry loops when a task
   repeatedly exhausts its iteration budget: without this guard the
   counter would reset on every recovery cycle and the circuit
   breaker could never trip (#35072).

The effective failure limit resolves in the same order as the
circuit breaker in ``_record_task_failure`` so the two never
disagree about when a task is permanently blocked:

  1. per-task ``max_retries`` if set
  2. caller-supplied ``failure_limit`` (the dispatcher passes the
     ``kanban.failure_limit`` config value through ``dispatch_once``)
  3. ``DEFAULT_FAILURE_LIMIT``

#### def `claim_task(conn: sqlite3.Connection, task_id: str, ttl_seconds: Optional[int] = None, claimer: Optional[str] = None) -> Optional[Task]`

Atomically transition ``ready -> running``.

Returns the claimed ``Task`` on success, ``None`` if the task was
already claimed (or is not in ``ready`` status).

#### def `claim_review_task(conn: sqlite3.Connection, task_id: str, ttl_seconds: Optional[int] = None, claimer: Optional[str] = None) -> Optional[Task]`

Atomically transition ``review -> running``.

Returns the claimed ``Task`` on success, ``None`` if the task was
already claimed (or is not in ``review`` status).

Unlike ``claim_task`` (which handles ``ready -> running``), this
does NOT check parent dependencies — the task already passed that
gate on its original ``todo -> ready -> running`` transition.

Creates a new run entry so the review agent's lifecycle is tracked
independently from the original worker run.

#### def `heartbeat_claim(conn: sqlite3.Connection, task_id: str, ttl_seconds: Optional[int] = None, claimer: Optional[str] = None) -> bool`

Extend a running claim.  Returns True if we still own it.

Workers that know they'll exceed 15 minutes should call this every
few minutes to keep ownership.

#### def `release_stale_claims(conn: sqlite3.Connection, signal_fn = None) -> int`

Reset any ``running`` task whose claim has expired.

A stale-by-TTL claim whose host-local worker PID is still alive is
*extended* (with a ``claim_extended`` event) instead of being
reclaimed. Reclaiming a live worker mid-flight produces the spawn-
then-immediately-reclaim loop seen on slow models that spend longer
than ``DEFAULT_CLAIM_TTL_SECONDS`` inside a single tool-free LLM
call (#23025): no tool calls means no ``kanban_heartbeat``, even
though the subprocess is healthy.

Backstop (#29747 gap 3): if the worker's PID is still alive but its
``last_heartbeat_at`` is stale by more than
``DEFAULT_CLAIM_HEARTBEAT_MAX_STALE_SECONDS`` (1h), the worker has
been making no observable progress and we reclaim anyway — even if
``_pid_alive`` is still true. This catches the wedged-in-a-logic-loop
case where the process is technically running but accomplishing
nothing. ``_touch_activity`` (run_agent.py) bridges chunk-level
liveness into ``last_heartbeat_at`` via #31752, so any genuinely
active worker keeps its heartbeat fresh as a side effect of normal
API traffic. ``enforce_max_runtime`` and ``detect_crashed_workers``
remain the upper bounds for genuinely wedged or dead workers.

Returns the number of stale claims actually reclaimed (live-pid
extensions don't count). Safe to call often.

#### def `reclaim_task(conn: sqlite3.Connection, task_id: str, reason: Optional[str] = None, signal_fn = None) -> bool`

Operator-driven reclaim: release the claim and reset to ``ready``.

Unlike :func:`release_stale_claims` which only acts on tasks whose
``claim_expires`` has passed, this function reclaims immediately
regardless of TTL. Intended for the dashboard/CLI recovery flow
when an operator wants to abort a running worker without waiting
for the TTL to expire (e.g. after seeing a hallucination warning).

Returns True if a reclaim happened, False if the task isn't in a
reclaimable state (not running, or doesn't exist).

#### def `reassign_task(conn: sqlite3.Connection, task_id: str, profile: Optional[str], reclaim_first: bool = False, reason: Optional[str] = None) -> bool`

Reassign a task, optionally reclaiming a stuck running worker first.

This is the recovery path for "this profile's model is broken, try
a different one". If ``reclaim_first`` is True, any active claim is
released (via :func:`reclaim_task`) before the reassign happens;
otherwise the function refuses to reassign a currently-running task
and returns False (caller can retry with ``reclaim_first=True``).

Returns True if the reassign landed. ``profile`` may be ``None`` to
unassign entirely.

#### def `complete_task(conn: sqlite3.Connection, task_id: str, result: Optional[str] = None, summary: Optional[str] = None, metadata: Optional[dict] = None, created_cards: Optional[Iterable[str]] = None, expected_run_id: Optional[int] = None) -> bool`

Transition ``running|ready -> done`` and record ``result``.

Accepts a task that is merely ``ready`` too, so a manual CLI
completion (``hermes kanban complete <id>``) works without requiring
a claim/start/complete sequence.

``summary`` and ``metadata`` are stored on the closing run (if any)
and surfaced to downstream children via :func:`build_worker_context`.
When ``summary`` is omitted we fall back to ``result`` so single-run
callers do not have to pass both. ``metadata`` is a free-form dict
(e.g. ``{"changed_files": [...], "tests_run": [...]}``) — workers
are encouraged to use it for structured handoff facts.

``created_cards`` is an optional list of task ids the completing
worker claims to have created. Each id is verified against
``tasks.created_by``. If any id is phantom (does not exist or was
not created by this worker's assignee profile), completion is blocked
with a ``HallucinatedCardsError`` and a
``completion_blocked_hallucination`` event is emitted so the rejected
attempt is auditable. When all ids verify, they are recorded on the
``completed`` event payload.

After a successful completion, ``summary`` and ``result`` are scanned
for prose references like ``t_deadbeefcafe`` that do not resolve.
Any suspected phantom references are recorded as a
``suspected_hallucinated_references`` event. This pass is advisory
and never blocks.

**异常**: `HallucinatedCardsError`

#### def `edit_completed_task_result(conn: sqlite3.Connection, task_id: str, result: str, summary: Optional[str] = None, metadata: Optional[dict] = None) -> bool`

Backfill the user-visible result for an already completed task.

#### def `block_task(conn: sqlite3.Connection, task_id: str, reason: Optional[str] = None, kind: Optional[str] = None, expected_run_id: Optional[int] = None) -> bool`

Transition ``running``/``ready`` → ``blocked`` (or route elsewhere).

``kind`` (one of :data:`VALID_BLOCK_KINDS`, or ``None`` for a legacy
un-typed block) drives routing instead of every block landing in one
undifferentiated ``blocked`` bucket:

* ``dependency`` — the task is only waiting on another task. It does NOT
  sit in ``blocked`` (where a cron would keep "unblocking" it); it goes to
  ``todo`` so the existing parent-gating / ``recompute_ready`` machinery
  promotes it automatically once its parents finish. No human, no cron, no
  retry storm. This is Dale's "Type 2 — dependency blocked".

* ``needs_input`` / ``capability`` / ``None`` — "truly blocked" (Dale's
  "Type 1"). Lands in ``blocked`` for a human. BUT: each time such a task
  is re-blocked for the SAME kind after having been unblocked, the
  unblock-loop counter (``block_recurrences``) increments. When it reaches
  :data:`BLOCK_RECURRENCE_LIMIT`, the task is routed to ``triage`` instead
  of ``blocked`` — breaking the cron-unblock ↔ worker-re-block loop and
  forcing a human-in-the-loop triage decision.

* ``transient`` — treated like a generic block for routing, but a worker
  can use it to signal "this might clear on its own"; it still participates
  in the loop breaker so a forever-flaky task eventually escalates.

Returns True on any successful transition (to ``blocked``, ``todo``, or
``triage``), False when the task wasn't in a blockable state.

**异常**: `ValueError`

#### def `promote_task(conn: sqlite3.Connection, task_id: str, actor: str, reason: Optional[str] = None, force: bool = False, dry_run: bool = False) -> tuple[bool, Optional[str]]`

Manually promote a `todo` or `blocked` task to `ready`.

Mirrors the automatic promotion done by ``recompute_ready`` but
drives it from a deliberate operator action with an audit-trail
entry. Refuses to promote if any parent dep is not in a terminal
state (`done`/`archived`) unless ``force=True``. Does NOT change
assignee or claim state. Returns ``(True, None)`` on success and
``(False, reason)`` if refused. ``dry_run=True`` validates the
promotion would succeed without mutating state.

#### def `unblock_task(conn: sqlite3.Connection, task_id: str) -> bool`

Transition ``blocked``/``scheduled`` -> ready or todo.

Defensively closes any stale ``current_run_id`` pointer before flipping
status. In the common path (``block_task`` closed the run already) this
is a no-op. If a future or external write left the pointer dangling,
the leaked run is closed as ``reclaimed`` inside the same txn so the
runs invariant (``current_run_id IS NULL`` ⇔ run row in terminal
state) holds for the rest of this function's lifetime.

#### def `specify_triage_task(conn: sqlite3.Connection, task_id: str, title: Optional[str] = None, body: Optional[str] = None, assignee: Optional[str] = None, author: Optional[str] = None) -> bool`

Flesh out a triage task and promote it to ``todo``.

Atomically updates ``title`` / ``body`` / ``assignee`` (when provided)
and transitions ``status: triage -> todo`` in a single write txn. Returns
False when the task is missing or not in the ``triage`` column — callers
should surface that as "nothing to specify" rather than an error.

``todo`` (not ``ready``) is the correct landing column: ``recompute_ready``
promotes parent-free / parent-done todos to ``ready`` on the next
dispatcher tick, which keeps the normal parent-gating behaviour intact
for specified tasks that happen to have open parents.

``author`` is recorded on an audit comment only when at least one of
``title`` / ``body`` / ``assignee`` actually changed — avoids noisy
comment spam for status-only promotions.

**异常**: `ValueError`

#### def `decompose_triage_task(conn: sqlite3.Connection, task_id: str, root_assignee: Optional[str], children: list[dict], author: Optional[str] = None, auto_promote: bool = True) -> Optional[list[str]]`

Fan a triage task out into child tasks and promote the root to ``todo``.

The root task stays alive and becomes the parent of every child —
when all children reach ``done``, the root promotes to ``ready`` and
its assignee (typically the orchestrator profile) wakes back up to
judge completion or spawn more work.

``children`` is a list of dicts, each shaped like::

    {
        "title": "...",
        "body": "...",                     # optional
        "assignee": "profile-name",        # optional, None -> default fallback
        "parents": [0, 2],                 # indices into this same children list
    }

Returns the list of created child task ids (in input order) on
success. Returns ``None`` when:
  - The root task does not exist
  - The root task is not in ``triage``
  - A cycle would result (caller built a bad graph)

Validation of titles/assignees happens inside the same write_txn as
the inserts so a malformed entry aborts the whole decomposition
cleanly (no orphan children).

**异常**: `ValueError`

#### def `archive_task(conn: sqlite3.Connection, task_id: str) -> bool`

#### def `delete_archived_task(conn: sqlite3.Connection, task_id: str) -> bool`

Permanently remove an already-archived task and its related rows.

Safety guard: only archived tasks can be deleted. Active / blocked / done
tasks must be explicitly archived first so accidental data loss requires a
second deliberate action.

#### def `delete_task(conn: sqlite3.Connection, task_id: str) -> bool`

Hard-delete a task and cascade to all related rows.

Because the schema does not use ``ON DELETE CASCADE`` foreign keys,
we explicitly delete from child tables first, then the task row.
This keeps the operation atomic (single ``write_txn``).

Returns ``True`` if the task existed and was deleted, ``False``
if the task was not found.

#### def `resolve_workspace(task: Task, board: Optional[str] = None) -> Path`

Resolve (and create if needed) the workspace for a task.

- ``scratch``: a fresh dir under ``<board-root>/workspaces/<id>/``,
  where ``<board-root>`` is the active board's root. The path is the
  same for the dispatcher and every profile worker, so handoff is
  path-stable.
- ``dir:<path>``: the path stored in ``workspace_path``.  Created
  if missing.  MUST be absolute — relative paths are rejected to
  prevent confused-deputy traversal where ``../../../tmp/attacker``
  resolves against the dispatcher's CWD instead of a meaningful
  root.  Users who want a kanban-root-relative workspace should
  compute the absolute path themselves.
- ``worktree``: a real linked git worktree. If ``workspace_path`` names
  a repo root, Hermes treats it as an anchor and materializes a linked
  worktree at ``<repo>/.worktrees/<task-id>``. If ``workspace_path`` names
  a concrete target path, Hermes creates/reuses that linked worktree. With
  no ``workspace_path``, Hermes anchors on the board's ``default_workdir``
  and materializes ``<repo>/.worktrees/<task-id>`` per task; if no
  ``default_workdir`` is configured it raises rather than guessing from the
  dispatcher's CWD. When ``branch_name`` is empty, Hermes uses
  ``wt/<task-id>``.

Persist the resolved path back to the task row via ``set_workspace_path``
so subsequent runs reuse the same directory.

**异常**: `ValueError`

#### def `set_workspace_path(conn: sqlite3.Connection, task_id: str, path: Path | str) -> None`

#### def `set_branch_name(conn: sqlite3.Connection, task_id: str, branch_name: str) -> None`

#### def `schedule_task(conn: sqlite3.Connection, task_id: str, reason: Optional[str] = None, expected_run_id: Optional[int] = None) -> bool`

Park a task in ``scheduled`` so it is waiting on time, not human input.

``scheduled`` tasks are intentionally not dispatchable; an external cron,
human action, or automation can later call ``unblock_task`` to re-gate them
to ``ready`` (or ``todo`` if parents are still incomplete).

#### def `reap_worker_zombies() -> list[int]`

Reap all zombie children of this process without blocking.

Returns the list of reaped PIDs. Safe to call when there are no
children (returns []). No-op on Windows.

#### def `heartbeat_worker(conn: sqlite3.Connection, task_id: str, note: Optional[str] = None, expected_run_id: Optional[int] = None) -> bool`

Record a ``heartbeat`` event + touch ``last_heartbeat_at``.

Called by long-running workers as a liveness signal orthogonal to
the PID check. A worker that forks a long-lived child (train loop,
video encode, web crawl) can have its Python still alive while the
actual work process is stuck; periodic heartbeats catch that.

Returns True on success, False if the task is not in a state that
should be heartbeating (not running, or claim expired).

#### def `enforce_max_runtime(conn: sqlite3.Connection, signal_fn = None) -> list[str]`

Terminate workers whose per-task ``max_runtime_seconds`` has elapsed.

Sends SIGTERM, waits a short grace window, then SIGKILL. Emits a
``timed_out`` event and drops the task back to ``ready`` so the next
dispatcher tick re-spawns it — unless the spawn-failure circuit
breaker has already given up, in which case the task stays blocked
where ``_record_spawn_failure`` parked it.

Runs host-local: only tasks claimed by this host are candidates
(same reasoning as ``detect_crashed_workers``). ``signal_fn`` is a
test hook; defaults to ``os.kill`` on POSIX.

#### def `detect_stale_running(conn: sqlite3.Connection, stale_timeout_seconds: int = 0, signal_fn = None) -> list[str]`

Reclaim ``running`` tasks that show no progress (heartbeat) within the
staleness window.

A task is considered stale when BOTH of these hold:

1. It has been running for longer than ``stale_timeout_seconds``
   (measured from the active run's ``started_at``, falling back to
   ``tasks.started_at`` on older runs).
2. Its ``last_heartbeat_at`` is older than
   ``_STALE_HEARTBEAT_GAP_SECONDS`` (or NULL — never sent a heartbeat).

On reclaim the task is reset to ``ready``, the run is closed with
``outcome='stale'``, and the host-local worker (if still running) is
terminated.

Only considers ``status='running'`` tasks. Blocked tasks are never
candidates.  Returns the list of reclaimed task IDs.

``stale_timeout_seconds=0`` disables the check entirely (returns ``[]``
immediately).  ``signal_fn`` is a test hook; defaults to ``os.kill``
on POSIX.

#### def `detect_crashed_workers(conn: sqlite3.Connection) -> list[str]`

Reclaim ``running`` tasks whose worker PID is no longer alive.

Appends a ``crashed`` event and drops the task back to ``ready``.
Different from ``release_stale_claims``: this checks liveness
immediately rather than waiting for the claim TTL.

Only considers tasks claimed by *this host* — PIDs from other hosts
are meaningless here. The host-local check is enough because
``_default_spawn`` always runs the worker on the same host as the
dispatcher (the whole design is single-host).

When the reap registry shows the worker exited cleanly (rc=0) but
the task was still ``running`` in the DB, treat it as a protocol
violation (worker answered conversationally without calling
``kanban_complete`` / ``kanban_block``) and trip the circuit breaker
on the first occurrence — retrying a worker whose CLI keeps
returning 0 without a terminal transition just loops forever.

When the reap registry shows the worker exited with the rate-limit
sentinel (``KANBAN_RATE_LIMIT_EXIT_CODE``), the worker bailed on a
provider quota wall, NOT a task failure. Such tasks are released back
to ``ready`` WITHOUT counting a failure (so a long quota window can't
trip the breaker) and stamped with a quota-blocker error so
``check_respawn_guard`` defers their respawn until the window clears.
The ids are returned via the ``_last_rate_limited`` function attribute
(the public return stays the crashed-only ``list[str]``).

#### def `check_respawn_guard(conn: sqlite3.Connection, task_id: str) -> Optional[str]`

Return a guard reason if ``task_id`` should NOT be re-spawned, else None.

Called per ready task in ``dispatch_once`` before any claim attempt.
Returning a reason defers the spawn this tick; the task stays in
``ready`` and gets another chance on the next dispatcher tick.

Checks in priority order:

``"rate_limit_cooldown"``
    The task's most recent run ended with the ``rate_limited`` outcome
    (a worker bailed on a provider quota wall via the EX_TEMPFAIL
    sentinel) within ``_resolve_rate_limit_cooldown_seconds()``. The
    quota almost certainly hasn't reset yet, so defer the respawn until
    the cooldown elapses — then allow a cheap probe. This is checked
    BEFORE ``blocker_auth`` because the rate-limit requeue stamps a
    quota-flavored ``last_failure_error`` that would otherwise match the
    auth-blocker regex and park the task forever (the rate-limit path
    never increments ``consecutive_failures``, so the breaker can't free
    it). Once the cooldown elapses the task falls through and respawns.

``"blocker_auth"``
    The task's last failure error matches a quota / authentication
    pattern. Retrying immediately is unlikely to help (rate limits
    reset on a timer; auth needs human action), so we defer to the
    next tick. The existing ``consecutive_failures`` counter still
    trips the auto-block circuit breaker after ``failure_limit``
    consecutive failures, so a persistent auth error eventually
    blocks via the normal path — but a transient 429 gets a few
    ticks of recovery first.

``"recent_success"``
    A completed run exists within ``_RESPAWN_GUARD_SUCCESS_WINDOW``
    seconds.  Useful work already succeeded for this task; wait for
    human review rather than immediately re-spawning. Bypassed when an
    explicit re-queue event (status change, promote, unblock, reclaim)
    arrives AFTER that completion — that's a deliberate re-run request.

``"active_pr"``
    A GitHub PR URL appears in a recent task comment (within
    ``_RESPAWN_GUARD_PR_WINDOW`` seconds).  A prior worker already
    opened a PR; re-spawning risks a duplicate PR on the same task.

Stale / dead claim locks are NOT a guard reason — they are handled
by ``release_stale_claims`` and ``detect_crashed_workers`` which
reset the task to ``ready`` only after verifying the lock is
genuinely dead (no live PID on this host).

#### def `has_spawnable_ready(conn: sqlite3.Connection) -> bool`

Return True iff there is at least one ready+assigned+unclaimed task
whose assignee maps to a real Hermes profile.

Used by the gateway- and CLI-embedded dispatchers' health telemetry to
decide whether ``0 spawned`` is a "stuck" condition (real spawnable
work waiting) or a "correctly idle" condition (only control-plane
lanes like ``orion-cc`` / ``orion-research`` waiting on terminals
that pull tasks via ``claim_task`` directly).

Falls back to "any ready+assigned" if ``profile_exists`` is not
importable (e.g. partial install) — preserves the old behavior so
the warning still fires in degraded environments.

#### def `has_spawnable_review(conn: sqlite3.Connection) -> bool`

Return True iff there is at least one review+assigned+unclaimed task
whose assignee maps to a real Hermes profile.

Mirror of :func:`has_spawnable_ready` for the review column —
used by the health telemetry to decide whether the dispatcher
should have spawned a review agent.

#### def `dispatch_once(conn: sqlite3.Connection, spawn_fn = None, ttl_seconds: Optional[int] = None, dry_run: bool = False, max_spawn: Optional[int] = None, max_in_progress: Optional[int] = None, failure_limit: int = DEFAULT_SPAWN_FAILURE_LIMIT, stale_timeout_seconds: int = 0, board: Optional[str] = None, default_assignee: Optional[str] = None, max_in_progress_per_profile: Optional[int] = None) -> DispatchResult`

Run one dispatcher tick under the board's single-writer lock.

Thin wrapper around :func:`_dispatch_once_locked`. It acquires a
non-blocking, board-scoped dispatch lock (issue #35240) so that two
dispatchers pointed at the same ``kanban.db`` — e.g. the service-
managed gateway and a shell-spawned orphan that escaped the service
cgroup — can never run a reclaim/spawn/write tick concurrently and
race on WAL frames. The losing dispatcher returns an empty
``DispatchResult`` with ``skipped_locked=True`` and does no DB writes;
the holder is already making progress on the same board.

The lock is keyed off the board's resolved DB path, so unrelated
boards tick in parallel. See :func:`_dispatch_tick_lock` for the
cross-process / cross-platform mechanics.

#### def `worker_log_rotation_config(kanban_cfg: Optional[dict] = None) -> tuple[int, int]`

Return ``(rotate_bytes, backup_count)`` for worker log rotation.

Defaults preserve the historical behavior: rotate at 2 MiB and keep one
backup generation (``.log.1``). Operators with long-running workers can
raise either value from ``config.yaml`` without changing dispatcher code.

#### def `run_daemon(interval: float = 60.0, max_spawn: Optional[int] = None, failure_limit: int = DEFAULT_SPAWN_FAILURE_LIMIT, stop_event = None, on_tick = None) -> None`

Run the dispatcher in a loop until interrupted.

Calls :func:`dispatch_once` every ``interval`` seconds. Exits cleanly
on SIGINT / SIGTERM so ``hermes kanban daemon`` is systemd-friendly.
``stop_event`` (a :class:`threading.Event`) and ``on_tick`` (a
callable receiving the :class:`DispatchResult`) are test hooks.

#### def `build_worker_context(conn: sqlite3.Connection, task_id: str) -> str`

Return the full text a worker should read to understand its task.

Order:
  1. Task title (mandatory).
  2. Task body (optional opening post, capped at 8 KB).
  3. Prior attempts on THIS task (most recent ``_CTX_MAX_PRIOR_ATTEMPTS``
     shown; older attempts collapsed into a one-line summary).
     Each attempt's ``summary`` / ``error`` / ``metadata`` capped at
     ``_CTX_MAX_FIELD_BYTES`` each.
  4. Structured handoff results of every done parent task. Prefers
     ``run.summary`` / ``run.metadata`` when the parent was executed
     via a run; falls back to ``task.result`` for older data. Same
     per-field cap.
  5. Cross-task role history for the assignee (most recent 5
     completed runs on other tasks).
  6. Comment thread (most recent ``_CTX_MAX_COMMENTS`` shown, older
     collapsed).

All caps exist so worker prompts stay bounded even on pathological
boards (retry-heavy tasks, comment storms). The per-field char cap
prevents a single 1 MB summary from dominating context.

**异常**: `ValueError`

#### def `board_stats(conn: sqlite3.Connection) -> dict`

Per-status + per-assignee counts, plus the oldest ``ready`` age in
seconds (the clearest staleness signal for a router or HUD).

#### def `task_age(task: Task) -> dict`

Return age metrics for a single task. All values are seconds or None.

#### def `add_notify_sub(conn: sqlite3.Connection, task_id: str, platform: str, chat_id: str, thread_id: Optional[str] = None, user_id: Optional[str] = None, notifier_profile: Optional[str] = None) -> None`

Register a gateway source that wants terminal-state notifications
for ``task_id``. Idempotent on (task, platform, chat, thread).

#### def `list_notify_subs(conn: sqlite3.Connection, task_id: Optional[str] = None) -> list[dict]`

#### def `remove_notify_sub(conn: sqlite3.Connection, task_id: str, platform: str, chat_id: str, thread_id: Optional[str] = None) -> bool`

#### def `unseen_events_for_sub(conn: sqlite3.Connection, task_id: str, platform: str, chat_id: str, thread_id: Optional[str] = None, kinds: Optional[Iterable[str]] = None) -> tuple[int, list[Event]]`

Return ``(new_cursor, events)`` for a given subscription.

Only events with ``id > last_event_id`` are returned. The subscription's
cursor is NOT advanced here; call :func:`advance_notify_cursor` after
the gateway has successfully delivered the notifications.

#### def `claim_unseen_events_for_sub(conn: sqlite3.Connection, task_id: str, platform: str, chat_id: str, thread_id: Optional[str] = None, kinds: Optional[Iterable[str]] = None) -> tuple[int, int, list[Event]]`

Atomically claim unseen notification events for one subscription.

Returns ``(old_cursor, new_cursor, events)``. When events are returned,
``kanban_notify_subs.last_event_id`` has already been advanced to
``new_cursor`` inside a ``BEGIN IMMEDIATE`` transaction. That makes the
notifier's read/claim step single-owner across multiple gateway watcher
processes pointed at the same board DB: concurrent watchers serialize on
SQLite's writer lock, and only the first process sees and claims a given
event range.

Callers should send the claimed events, then either leave the cursor at
``new_cursor`` on success or call :func:`rewind_notify_cursor` if delivery
failed before any terminal unsubscribe removed the row.

#### def `advance_notify_cursor(conn: sqlite3.Connection, task_id: str, platform: str, chat_id: str, thread_id: Optional[str] = None, new_cursor: int) -> None`

#### def `rewind_notify_cursor(conn: sqlite3.Connection, task_id: str, platform: str, chat_id: str, thread_id: Optional[str] = None, claimed_cursor: int, old_cursor: int) -> bool`

Undo a notification claim when delivery fails.

The CAS guard only rewinds if no later notifier advanced the row after our
claim. This keeps retry behavior for transient send failures without
clobbering newer progress.

#### def `gc_events(conn: sqlite3.Connection, older_than_seconds: int = 30 * 24 * 3600) -> int`

Delete task_events rows older than ``older_than_seconds`` for tasks
in a terminal state (``done`` or ``archived``). Returns the number of
rows deleted. Running / ready / blocked tasks keep their full event
history.

#### def `gc_worker_logs(older_than_seconds: int = 30 * 24 * 3600, board: Optional[str] = None) -> int`

Delete worker log files older than ``older_than_seconds``. Returns
the number of files removed. Kept separate from ``gc_events`` because
log files live on disk, not in SQLite. Scoped to ``board`` (defaults
to the active board) — per-board isolation means deleting logs from
board A cannot touch board B's logs.

#### def `worker_log_path(task_id: str, board: Optional[str] = None) -> Path`

Return the path to a worker's log file. The file may not exist
(task never spawned, or log already GC'd).

When ``board`` is None, resolves via the active board (env var →
current-board file → default). The dispatcher always passes the
board explicitly to avoid any resolution ambiguity when multiple
boards exist.

#### def `read_worker_log(task_id: str, tail_bytes: Optional[int] = None, board: Optional[str] = None) -> Optional[str]`

Read the worker log for ``task_id``. Returns None if the file
doesn't exist. If ``tail_bytes`` is set, only the last N bytes are
returned (useful for the dashboard drawer which shouldn't page megabytes).

#### def `list_profiles_on_disk() -> list[str]`

Return the set of assignee/profile names discovered on disk.

Includes:
- named profiles under ``<default-root>/profiles/<name>/config.yaml``
- the implicit ``default`` profile when the default Hermes root exists

Reads profile paths directly so this module has no import dependency on
``hermes_cli.profiles`` (which pulls in a large chunk of the CLI startup
path).

#### def `known_assignees(conn: sqlite3.Connection) -> list[dict]`

Return every assignee name known to the board or on disk.

Each entry is ``{"name": str, "on_disk": bool, "counts": {status: n}}``.
A name is included when it's a configured profile on disk OR when
any non-archived task has it as the assignee. Used by:

- ``hermes kanban assignees`` for the terminal.
- The dashboard assignee dropdown (so a fresh profile appears in
  the picker even before it's been given any task).
- Router-profile heuristics ("who's overloaded?") without scanning
  the whole board.

#### def `list_runs(conn: sqlite3.Connection, task_id: str, include_active: bool = True, state_type: Optional[str] = None, state_name: Optional[str] = None) -> list[Run]`

Return all runs for ``task_id`` in start order.

``include_active=True`` (default) includes the currently-running
attempt if any. Set False to return only closed runs (useful for
"how many prior attempts have there been?" checks).

When ``state_type`` and ``state_name`` are set, restrict to rows
where that column equals ``state_name`` (``state_type`` is
``status`` or ``outcome``). Both must be passed together.

**异常**: `ValueError`

#### def `get_run(conn: sqlite3.Connection, run_id: int) -> Optional[Run]`

#### def `latest_run(conn: sqlite3.Connection, task_id: str) -> Optional[Run]`

Return the most recent run regardless of outcome (active or closed).

#### def `latest_summary(conn: sqlite3.Connection, task_id: str) -> Optional[str]`

Return the latest non-null ``task_runs.summary`` for ``task_id``.

The worker writes its handoff to ``task_runs.summary``
via ``complete_task(summary=...)``; ``tasks.result`` is left empty
unless the caller passes ``result=`` explicitly. Dashboards and CLI
"show" views need this value to surface what a worker actually did
— without it, ``tasks.result`` is NULL and the task looks like a
no-op even when the run completed.

Picks the most recent run by ``ended_at`` (falling back to ``id``
for ties or unfinished rows). Returns None if no run has a summary.

#### def `latest_summaries(conn: sqlite3.Connection, task_ids: Iterable[str]) -> dict[str, str]`

Batch-fetch latest non-null summaries for a list of task ids.

Used by the dashboard board endpoint to attach ``latest_summary`` to
every card in a single SQL query, avoiding the N+1 pattern of
calling :func:`latest_summary` per task. Returns a dict mapping
``task_id`` → summary string, omitting tasks with no summary.

Approach: a window function picks the newest non-null-summary row
per ``task_id``; works against SQLite ≥ 3.25 (default on every
supported platform).


## hermes_cli.kanban_decompose

### 模块文档

Kanban decomposer — fan a triage task out into a graph of child tasks.

Invoked by ``hermes kanban decompose [task_id | --all]`` and the
auto-decompose path in the gateway dispatcher loop. Reads the user's
profile roster (with descriptions) and asks the auxiliary LLM to
return a task graph in JSON. Then atomically creates the children,
links them under the root, and flips the root ``triage -> todo``.

The root task stays alive and becomes the parent of every leaf child,
so when the whole graph completes the root wakes back up — its
assignee (the orchestrator profile) gets a chance to judge completion
and add more tasks if the work isn't done yet.

Design notes
------------

* Mirrors the shape of ``hermes_cli/kanban_specify.py``: lazy aux
  client import inside the function, lenient response parse, never
  raises on expected failure modes.

* The system prompt sees the *configured* profile roster — names plus
  descriptions plus the default fallback. Profiles without a
  description are still listed (with a note) so the decomposer can
  match on name as a fallback, but the user has an obvious incentive
  to describe them.

* ``fanout=false`` collapses to the same effect as ``kanban specify``:
  we tighten the body and flip ``triage -> todo`` as a single task,
  no children created. This makes ``decompose`` a strict superset of
  ``specify`` from the user's perspective.

* If the LLM picks an assignee that doesn't exist as a profile, we
  rewrite it to the configured ``default_assignee`` (or the default
  profile if unset). A child task NEVER ends up with ``assignee=None``.

### class DecomposeOutcome

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of decomposing a single triage task.


### 顶层函数

#### def `decompose_task(task_id: str, author: Optional[str] = None, timeout: Optional[int] = None) -> DecomposeOutcome`

Decompose a triage task into a graph of child tasks.

Returns an outcome describing what happened. Never raises for
expected failure modes (task not in triage, no aux client
configured, API error, malformed response, decomposer returned
fanout=true with empty task list) — those surface via ``ok=False``.

#### def `list_triage_ids(tenant: Optional[str] = None) -> list[str]`

Return task ids currently in the triage column.


## hermes_cli.kanban_diagnostics

### 模块文档

Kanban diagnostics — structured, actionable distress signals for tasks.

A ``Diagnostic`` is a machine-readable description of something that's wrong
with a kanban task: a hallucinated card id, a spawn crash-loop, a task
stuck blocked for too long, etc. Each one carries:

* A **kind** (canonical code; UI/tests match on this).
* A **severity** (``warning`` / ``error`` / ``critical``).
* A **title** (one-line human description) and **detail** (longer text).
* A list of **suggested actions** — structured entries the dashboard
  turns into buttons and the CLI turns into hints.

Rules run over (task, recent events, recent runs) and emit diagnostics.
They are stateless and read-only — no DB writes. Callers compute
diagnostics on demand (on ``/board`` load, ``/tasks/:id`` fetch, or
``hermes kanban diagnostics``).

Design goals:

* Fixable-on-the-operator's-side signals only (missing config, phantom
  ids, crash loop). Not "the provider returned 502 once" — that's a
  transient runtime blip, not a diagnostic.
* Recoverable: every diagnostic comes with at least one suggested
  recovery action the operator can actually take from the UI.
* Auto-clearing: when the underlying failure mode resolves (a clean
  ``completed`` event arrives, a spawn succeeds, the task gets
  unblocked), the diagnostic stops firing. The audit event trail stays.

### class DiagnosticAction

> 继承: `object` ｜ 方法数: 1（公开 1）

A single recovery action attached to a diagnostic.

The ``kind`` determines how both the UI and CLI render it:

* ``reclaim`` / ``reassign`` — POST to the matching /tasks/:id/*
  endpoint; dashboard wires into the existing recovery popover.
* ``unblock`` — PATCH status back to ``ready`` (for stuck-blocked
  diagnostics).
* ``cli_hint`` — print/copy a shell command (e.g.
  ``hermes -p <profile> auth``). No HTTP side effect.
* ``open_docs`` — deep-link to the docs URL named in ``payload.url``.
* ``comment`` — nudge the operator to add a comment (for
  stuck-blocked tasks that need human input).

``suggested=True`` marks the action as the recommended first step;
the UI highlights it. Multiple actions can be suggested if they're
equally valid.

#### def `to_dict(self) -> dict`


### class Diagnostic

> 继承: `object` ｜ 方法数: 1（公开 1）

One active distress signal on a task.

#### def `to_dict(self) -> dict`


### 顶层函数

#### def `severity_at_or_above(severity: Optional[str], threshold: Optional[str]) -> bool`

Return True when ``severity`` meets or exceeds ``threshold``.

#### def `triage_aux_status(config: Optional[dict]) -> Optional[dict]`

Inspect raw config and report whether triage paths look configured.

Returns ``None`` when config context is unavailable (suppress diagnostic
to avoid noisy false positives in tests / low-level callers). Otherwise
returns a dict with:

  - ``auto_decompose``: bool — whether the dispatcher auto-runs decompose
  - ``decomposer_explicit``: bool — user-supplied decomposer slot
  - ``specifier_explicit``: bool — user-supplied specifier slot
  - ``main_model_visible``: bool — main model can serve as auto fallback

#### def `config_from_kanban_config(kanban_cfg: Optional[dict]) -> dict`

Build diagnostics config from the runtime ``kanban`` config section.

``kanban.diagnostics.failure_threshold`` remains an explicit override.
Otherwise, derive the repeated-failure threshold from
``kanban.failure_limit`` so CLI/dashboard diagnostics match the
dispatcher's actual circuit-breaker threshold.

#### def `config_from_runtime_config(raw_config: Optional[dict]) -> dict`

Build diagnostics config from the full Hermes runtime config.

Carries through ``kanban``, ``auxiliary``, and ``model`` keys so triage-
aware rules can inspect the active aux-helper and main-model state.
Folds the ``kanban`` block through ``config_from_kanban_config`` so the
repeated-failure threshold derivation still applies.

#### def `compute_task_diagnostics(task, events: list, runs: list, now: Optional[int] = None, config: Optional[dict] = None) -> list[Diagnostic]`

Run every rule against a single task's state and return a
severity-sorted list of active diagnostics.

Sorting: critical first, then error, then warning; ties broken by
most-recent ``last_seen_at``.


## hermes_cli.kanban_specify

### 模块文档

Kanban triage specifier — flesh out a one-liner into a real spec.

Used by ``hermes kanban specify [task_id | --all]``. Takes a task that
lives in the Triage column (a rough idea, typically only a title), calls
the auxiliary LLM to produce:

  * A tightened title (optional — only replaces if the model proposes a
    materially different one)
  * A concrete body: goal, proposed approach, acceptance criteria

and then flips the task ``triage -> todo`` via
``kanban_db.specify_triage_task``. The dispatcher promotes it to
``ready`` on its next tick (or immediately if there are no open parents).

Design notes
------------

* This module intentionally mirrors ``hermes_cli/goals.py`` — same aux
  client pattern, same "empty config => skip, don't crash" tolerance.
  Keeps the surface area tiny and the failure modes predictable.

* The prompt is a short system + user pair. We ask for JSON with
  ``{title, body}``; if parsing fails, we fall back to treating the
  whole response as the body and leave the title untouched. No
  retry loop — one shot, keep cost bounded.

* Structured output / JSON mode is not requested explicitly so the
  specifier works on providers that don't implement it. The parse
  is lenient (tolerates markdown code fences around the JSON).

### class SpecifyOutcome

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of specifying a single triage task.


### 顶层函数

#### def `specify_task(task_id: str, author: Optional[str] = None, timeout: Optional[int] = None) -> SpecifyOutcome`

Specify a single triage task and promote it to ``todo``.

Returns an outcome describing what happened. Never raises for expected
failure modes (task not in triage, no aux client configured, API
error, malformed response) — those surface via ``ok=False`` so the
``--all`` sweep can continue past individual failures.

#### def `list_triage_ids(tenant: Optional[str] = None) -> list[str]`

Return task ids currently in the triage column.

``tenant`` narrows the sweep; ``None`` returns every triage task.


## hermes_cli.kanban_swarm

### 模块文档

Kanban Swarm v1: thin swarm topology helpers on top of Kanban.

This module intentionally does not introduce a second scheduler. It writes a
small task graph into the existing Kanban kernel:

    planning root (completed immediately)
        ├─ parallel specialist workers (ready)
        └─ verifier (todo until all workers done)
             └─ synthesizer (todo until verifier done)

The shared blackboard is also deliberately low-tech: structured JSON comments on
the root task. That keeps all state in existing task_comments/task_events rows,
so the dashboard, notifier, slash command, and dispatcher keep working without a
new service.

### class SwarmWorkerSpec

> 继承: `object` ｜ 方法数: 0（公开 0）

A single parallel worker card in a swarm.


### class SwarmCreated

> 继承: `object` ｜ 方法数: 1（公开 1）

IDs produced by :func:`create_swarm`.

#### def `as_dict(self) -> dict[str, Any]`


### 顶层函数

#### def `create_swarm(conn: sqlite3.Connection, goal: str, workers: Iterable[SwarmWorkerSpec], verifier_assignee: str, synthesizer_assignee: str, root_title: Optional[str] = None, verifier_title: str = 'Verify swarm outputs', synthesizer_title: str = 'Synthesize swarm outputs', tenant: Optional[str] = None, created_by: str = 'swarm-orchestrator', workspace_kind: str = 'scratch', workspace_path: Optional[str] = None, priority: int = 0, idempotency_key: Optional[str] = None) -> SwarmCreated`

Create a durable Kanban swarm graph.

The returned graph is immediately dispatchable: the planning root is marked
``done`` with topology metadata, parallel workers are ``ready``, the verifier
waits for every worker, and the synthesizer waits for the verifier.

**异常**: `ValueError`

#### def `post_blackboard_update(conn: sqlite3.Connection, root_id: str, author: str, key: str, value: Any) -> int`

Append one structured update to the swarm root blackboard.

#### def `latest_blackboard(conn: sqlite3.Connection, root_id: str) -> dict[str, Any]`

Merge structured blackboard comments on a root card.

Later comments replace earlier values for the same key. ``_authors`` records
the author of the winning value for traceability.

#### def `parse_worker_arg(raw: str) -> SwarmWorkerSpec`

Parse CLI ``--worker profile:title[:skill,skill]`` values.

**异常**: `ValueError`


## hermes_cli.logs

### 模块文档

``hermes logs`` — view and filter Hermes log files.

Supports tailing, following, session filtering, level filtering,
component filtering, and relative time ranges.  All log files live
under ``~/.hermes/logs/``.

Usage examples::

    hermes logs                    # last 50 lines of agent.log
    hermes logs -f                 # follow agent.log in real time
    hermes logs errors             # last 50 lines of errors.log
    hermes logs gateway -n 100    # last 100 lines of gateway.log
    hermes logs gui -f            # follow gui.log (dashboard/pty/ws)
    hermes logs desktop -f        # follow desktop.log (Electron app boot/backend)
    hermes logs --level WARNING    # only WARNING+ lines
    hermes logs --session abc123   # filter by session ID substring
    hermes logs --component tools  # only tool-related lines
    hermes logs --since 1h         # lines from the last hour
    hermes logs --since 30m -f     # follow, starting 30 min ago

### 顶层函数

#### def `tail_log(log_name: str = 'agent', num_lines: int = 50, follow: bool = False, level: Optional[str] = None, session: Optional[str] = None, since: Optional[str] = None, component: Optional[str] = None) -> None`

Read and display log lines, optionally following in real time.

Parameters
----------
log_name
    Which log to read: ``"agent"``, ``"errors"``, ``"gateway"``, ``"gui"``.
num_lines
    Number of recent lines to show (before follow starts).
follow
    If True, keep watching for new lines (Ctrl+C to stop).
level
    Minimum log level to show (e.g. ``"WARNING"``).
session
    Session ID substring to filter on.
since
    Relative time string (e.g. ``"1h"``, ``"30m"``).
component
    Component name to filter by (e.g. ``"gateway"``, ``"tools"``).

#### def `list_logs() -> None`

Print available log files with sizes.


## hermes_cli.main

### 模块文档

Hermes CLI - Main entry point.

Usage:
    hermes                     # Interactive chat (default)
    hermes chat                # Interactive chat
    hermes gateway             # Run gateway in foreground
    hermes gateway start       # Start gateway as service
    hermes gateway stop        # Stop gateway service
    hermes gateway status      # Show gateway status
    hermes gateway install     # Install gateway service
    hermes gateway uninstall   # Uninstall gateway service
    hermes setup               # Interactive setup wizard
    hermes logout              # Clear stored authentication
    hermes status              # Show status of all components
    hermes cron                # Manage cron jobs
    hermes cron list           # List cron jobs
    hermes cron status         # Check if cron scheduler is running
    hermes doctor              # Check configuration and dependencies
    hermes honcho setup                    # Configure Honcho AI memory integration
    hermes honcho status                   # Show Honcho config and connection status
    hermes honcho sessions                 # List directory → session name mappings
    hermes honcho map <name>               # Map current directory to a session name
    hermes honcho peer                     # Show peer names and dialectic settings
    hermes honcho peer --user NAME         # Set user peer name
    hermes honcho peer --ai NAME           # Set AI peer name
    hermes honcho peer --reasoning LEVEL   # Set dialectic reasoning level
    hermes honcho mode                     # Show current memory mode
    hermes honcho mode [hybrid|honcho|local]  # Set memory mode
    hermes honcho tokens                   # Show token budget settings
    hermes honcho tokens --context N       # Set session.context() token cap
    hermes honcho tokens --dialectic N     # Set dialectic result char cap
    hermes honcho identity                 # Show AI peer identity representation
    hermes honcho identity <file>          # Seed AI peer identity from a file (SOUL.md etc.)
    hermes honcho migrate                  # Step-by-step migration guide: OpenClaw native → Hermes + Honcho
    hermes version             Show version
    hermes update              Update to latest version
    hermes uninstall           Uninstall Hermes Agent
    hermes acp                 Run as an ACP server for editor integration
    hermes sessions browse     Interactive session picker with search

    hermes claw migrate --dry-run  # Preview migration without changes

### 顶层函数

#### def `cmd_chat(args)`

Run interactive chat CLI.

#### def `cmd_gateway(args)`

Gateway management commands.

#### def `cmd_proxy(args)`

Local OpenAI-compatible proxy to OAuth providers.

**异常**: `SystemExit`

#### def `cmd_whatsapp(args)`

Set up WhatsApp: choose mode, configure, install bridge, pair via QR.

#### def `cmd_whatsapp_cloud(args)`

Set up WhatsApp Business Cloud API (official Meta integration).

Walks the user through the Meta-side credentials (Phone Number ID,
Access Token, App Secret, optional App/WABA IDs) plus webhook
configuration. Includes field-shape validators that catch the most
common setup mistakes (e.g. pasting a phone number into the Phone
Number ID field).

Distinct from ``hermes whatsapp`` (the Baileys bridge wizard) — the
two adapters are complementary, not alternatives. See
``hermes_cli/setup_whatsapp_cloud.py``.

#### def `cmd_setup(args)`

Interactive setup wizard.

#### def `cmd_postinstall(args)`

One-shot bootstrap for pip users: install non-Python deps + run setup.

#### def `cmd_model(args)`

Select default model — starts with provider selection, then model picker.

#### def `select_provider_and_model(args = None)`

Core provider selection + model picking logic.

Shared by ``cmd_model`` (``hermes model``) and the setup wizard
(``setup_model_provider`` in setup.py).  Handles the full flow:
provider picker, credential prompting, model selection, and config
persistence.

#### def `cmd_login(args)`

Authenticate Hermes CLI with a provider.

#### def `cmd_logout(args)`

Clear provider authentication.

#### def `cmd_auth(args)`

Manage pooled credentials.

#### def `cmd_status(args)`

Show status of all components.

#### def `cmd_cron(args)`

Cron job management.

#### def `cmd_webhook(args)`

Webhook subscription management.

#### def `cmd_slack(args)`

Slack integration helpers.

Dispatches ``hermes slack <subcommand>``. Currently supports:
  manifest — print or write a Slack app manifest with every gateway
             command registered as a first-class slash.

#### def `cmd_kanban(args)`

Multi-profile collaboration board.

#### def `cmd_project(args)`

Manage projects (named, multi-folder workspaces).

#### def `cmd_hooks(args)`

Shell-hook inspection and management.

#### def `cmd_doctor(args)`

Check configuration and dependencies.

#### def `cmd_security(args)`

Dispatch `hermes security <subcmd>`.

#### def `cmd_dump(args)`

Dump setup summary for support/debugging.

#### def `cmd_debug(args)`

Debug tools (share report, etc.).

#### def `cmd_config(args)`

Configuration management.

#### def `cmd_backup(args)`

Back up Hermes home directory to a zip file.

#### def `cmd_import(args)`

Restore a Hermes backup from a zip file.

#### def `cmd_version(args)`

Show version.

#### def `cmd_uninstall(args)`

Uninstall Hermes Agent (or just the Chat GUI with --gui).

#### def `cmd_gui(args: argparse.Namespace)`

Build and launch the native Electron desktop GUI.

#### def `cmd_update(args)`

Update Hermes Agent to the latest version.

Thin wrapper around ``_cmd_update_impl``: installs hangup protection,
runs the update, then restores stdio on the way out (even on
``sys.exit`` or unhandled exceptions).

#### def `cmd_profile(args)`

Profile management — create, delete, list, switch, alias.

#### def `cmd_dashboard(args)`

Start the web UI server, or (with --stop/--status) manage running ones.

#### def `cmd_dashboard_register(args)`

Register a self-hosted dashboard OAuth client with Nous Portal.

#### def `cmd_gateway_enroll(args)`

Enroll a self-hosted gateway with a relay connector.

#### def `cmd_completion(args, parser = None)`

Print shell completion script.

#### def `cmd_prompt_size(args)`

Show a byte/char breakdown of the system prompt + tool schemas.

#### def `cmd_logs(args)`

View and filter Hermes log files.

#### def `cmd_console(args)`

Open the safe Hermes command console.

#### def `cmd_memory(args)`

#### def `cmd_acp(args)`

Launch Hermes Agent as an ACP server.

#### def `cmd_tools(args)`

#### def `cmd_insights(args)`

#### def `cmd_skills(args)`

#### def `cmd_pairing(args)`

#### def `cmd_plugins(args)`

#### def `cmd_mcp(args)`

#### def `cmd_claw(args)`

#### def `main()`

Main entry point for hermes CLI.


## hermes_cli.managed_scope

### 模块文档

Managed scope — IT-pushed, user-immutable config & env layer.

A system-level directory (default ``/etc/hermes``, root-owned and not
user-writable) supplies ``config.yaml`` and ``.env`` values that WIN over the
user's ``~/.hermes/config.yaml`` and ``~/.hermes/.env`` on a per-leaf-key basis.

This is DISTINCT from ``hermes_cli.config.is_managed()`` / ``HERMES_MANAGED``,
which is a coarse package-manager write-lock (declarative-distro / formula
installs). That lock blocks all mutation; this layer injects specific immutable
values. The two are independent and may coexist.

v1 enforcement is filesystem permissions only — see
``docs/design/managed-scope.md`` §7. v1 is Linux/POSIX-first; ``get_managed_dir()``
is the single seam for adding macOS / Windows native locations later.

Attribution: do not reference any third-party product by name in this file.

### 顶层函数

#### def `get_managed_dir() -> Optional[Path]`

Resolve the managed-scope directory, or None when no scope is present.

Resolution (highest priority first):
  1. ``$HERMES_MANAGED_DIR`` — deployment/bootstrap path override (IT-only;
     never persisted to any .env). Honored only when set to a non-empty value
     AND the directory exists.
  2. ``/etc/hermes`` — POSIX default, when it exists. Ignored under pytest so
     a real system managed scope can't leak into the test suite.

A non-existent directory at either tier resolves to None (no managed scope),
which is the common case and must be cheap + side-effect-free.

#### def `invalidate_managed_cache() -> None`

Drop cached managed config/env. For tests and post-edit reloads.

#### def `load_managed_config() -> dict`

Parsed managed config.yaml, or {} when absent/malformed (fail-open).

#### def `load_managed_env() -> Dict[str, str]`

Parsed managed .env (KEY=VALUE), or {} when absent (fail-open).

#### def `apply_managed_overlay(config: dict) -> dict`

Overlay administrator-pinned config values on top of an already-built dict.

The single, shared way for any config loader that builds its own dict
(rather than going through hermes_cli.config.load_config) to honor managed
scope. Mirrors hermes_cli.config._load_config_impl's managed merge exactly:

  * expand the managed config's ``${VAR}`` refs against the PROCESS env only
    (never user-config-defined refs), so a user cannot shadow a managed
    literal via a ${VAR} they control;
  * normalize the managed config's root ``model`` key (a bare ``model: x/y``
    string is promoted to ``model.default``) so it can't clobber the dict
    shape callers expect;
  * leaf-level deep-merge managed ON TOP, so managed wins per-leaf while
    sibling keys stay user-controlled.

Fail-open: returns ``config`` unchanged if no managed scope is present or on
any error — managed scope must never break a caller's startup. Mutates and
returns ``config`` (callers pass a dict they own).

#### def `managed_config_keys() -> set`

Dotted leaf keys pinned by the managed config (e.g. {'model.default'}).

#### def `is_key_managed(dotted_key: str) -> bool`

True if the exact dotted config key is pinned by the managed layer.

#### def `is_env_managed(name: str) -> bool`

True if the env var name is pinned by the managed .env layer.


## hermes_cli.managed_uv

### 模块文档

Managed uv — one path, no guessing.

Hermes owns its own uv binary at ``$HERMES_HOME/bin/uv`` (or ``uv.exe`` on
Windows).  Every code path that needs uv resolves it from that single location.
If the binary is missing, ``ensure_uv()`` bootstraps it via the official
standalone installer with ``UV_UNMANAGED_INSTALL`` / ``UV_INSTALL_DIR`` pointed
at ``$HERMES_HOME/bin`` so the installer writes directly there — no PATH
probing, no conda guards, no multi-location resolution chains.

### 顶层函数

#### def `managed_uv_path() -> Path`

Return the path where Hermes keeps *its* uv binary.

``$HERMES_HOME/bin/uv`` on POSIX, ``$HERMES_HOME\bin\uv.exe`` on
Windows.  The directory may not exist yet — callers should use
``ensure_uv()`` to bootstrap it.

#### def `resolve_uv() -> Optional[str]`

Return the managed uv path if it exists, else ``None``.

No side effects — pure lookup.

#### def `ensure_uv()`

Return the managed uv path, installing it first if necessary.

On **POSIX** the result is a :class:`_UvResult` (a ``str`` subclass) that is
both usable directly as the path *and* unpackable as
``(path, fresh_bootstrap)`` for older call sites parked on a 2-tuple
release — see :class:`_UvResult` for the update-boundary rationale.

On **Windows** we deliberately return a plain ``str``/``None`` instead.
``subprocess`` there serializes the argv via ``subprocess.list2cmdline``,
which iterates every entry *as a string* (``for c in arg``). The dependency
installer passes uv straight into the command list (``[uv_bin, "pip", ...]``),
so a ``_UvResult`` — whose ``__iter__`` yields ``(path, fresh_bootstrap)``
rather than characters — would inject the bool into the command line and
crash the install with ``TypeError: sequence item 1: expected str instance,
bool found``. A plain ``str`` matches the historical Windows contract and is
subprocess-safe. (A single value cannot satisfy both 2-target unpacking and
Windows char-iteration: both use the iterator protocol, with contradictory
results.)

On failure the result is falsy — never raises — so callers can fall back to
pip gracefully.

#### def `update_managed_uv() -> Optional[str]`

Run ``uv self update`` on the managed uv binary.

Call this during ``hermes update`` so the managed copy stays current.
Returns the managed path on success, ``None`` if uv isn't available or
the self-update fails (non-fatal — the old version still works).

#### def `rebuild_venv(uv_bin: str, venv_dir: Path, python_version: str = '3.11') -> bool`


## hermes_cli.mcp_catalog

### 模块文档

MCP catalog — curated, Nous-approved MCP servers shipped with the repo.

Mirrors the optional-skills/ pattern: each catalog entry lives under
``optional-mcps/<name>/manifest.yaml`` and ships disabled. Users discover
entries via ``hermes mcp catalog`` or the interactive ``hermes mcp picker``,
and install them with ``hermes mcp install <name>`` (or by toggling in the
picker, which flows them through any required env/OAuth setup).

Catalog policy:
- Entries are added only by merging a PR into hermes-agent. Presence in the
  ``optional-mcps/`` directory = Nous approval. No community tier, no trust
  signals beyond "it's in the catalog".
- Manifests pin transport details (commands, args, refs). Pins follow the
  same supply-chain rules as pyproject dependencies: exact versions for
  package launchers (``uvx pkg==X``, ``npx pkg@X``), full commit SHAs for
  git installs, and the pinned release should be at least 2 weeks old at
  pin time. MCPs are never
  auto-updated; users explicitly re-run ``hermes mcp install <name>`` to
  pull a new manifest version after a repo update.
- Secrets prompted at install time go to ``~/.hermes/.env`` (the
  .env-is-for-secrets rule). Non-secret env vars also go to .env to keep
  one credential store.

See website/docs/user-guide/mcp-catalog.md for user docs.
See references/mcp-catalog.md (this repo's skill) for the manifest schema.

### class EnvVarSpec

> 继承: `object` ｜ 方法数: 0（公开 0）


### class AuthSpec

> 继承: `object` ｜ 方法数: 0（公开 0）


### class TransportSpec

> 继承: `object` ｜ 方法数: 0（公开 0）


### class InstallSpec

> 继承: `object` ｜ 方法数: 0（公开 0）

Optional bootstrap step (git clone + dep install).

Omit for one-shot launchable servers (npx, uvx).


### class ToolsSpec

> 继承: `object` ｜ 方法数: 0（公开 0）

Manifest-side tool-selection hints.

Drives the pre-checked state of the install-time tool checklist, and acts
as the fallback selection when probe fails. See install_entry() flow.


### class CatalogEntry

> 继承: `object` ｜ 方法数: 0（公开 0）


### class CatalogError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Manifest parse/validation failure or install error.


### 顶层函数

#### def `list_catalog() -> List[CatalogEntry]`

Return all valid catalog entries, sorted by name.

Invalid manifests are skipped silently (CI tests catch them at PR time).
Manifests with a future ``manifest_version`` are also skipped, but the
skip is surfaced via :func:`catalog_diagnostics` so the picker / catalog
UIs can tell the user their Hermes is out of date.

#### def `catalog_diagnostics() -> List[tuple]`

Diagnostics from the most recent :func:`list_catalog` call.

Returns a list of ``(entry_name, kind, message)`` tuples where ``kind``
is one of:
  - ``future_manifest`` — manifest_version is newer than this Hermes
    understands. Update Hermes to install this entry.
  - ``invalid`` — manifest is malformed in some other way (caught by
    CI for shipped manifests; user-modified manifests can hit this).

#### def `get_entry(name: str) -> Optional[CatalogEntry]`

Look up a single entry by name. ``official/<name>`` prefix accepted.

#### def `installed_servers() -> Dict[str, dict]`

Return current ``mcp_servers`` block from config.yaml.

#### def `is_installed(name: str) -> bool`

#### def `is_enabled(name: str) -> bool`

#### def `install_entry(entry: CatalogEntry, enable: bool = True) -> None`

Install a catalog entry end-to-end.

Steps:
    1. If ``install.type == git``, clone + run bootstrap commands.
    2. If ``auth.type == api_key``, prompt for env vars, save to .env.
    3. If ``auth.type == oauth`` (remote MCP / case 1), write the
       ``auth: oauth`` marker (MCP client handles browser on first connect
       in the non-pre-authenticated case).
    4. Translate the manifest into an ``mcp_servers.<name>`` block and
       save into config.yaml.
    5. Probe the server, present a curses checklist for tool selection,
       write ``tools.include`` (or no filter, depending on choice).
       If probe fails, fall back to the manifest's
       ``tools.default_enabled`` or all-on.
    6. Print post_install notes.

**异常**: `CatalogError`

#### def `uninstall_entry(name: str, purge_install_dir: bool = True) -> bool`

Remove a catalog-installed MCP from config and (optionally) wipe its
clone directory. Returns True if anything was removed.


## hermes_cli.mcp_config

### 模块文档

MCP Server Management CLI — ``hermes mcp`` subcommand.

Implements ``hermes mcp add/remove/list/test/configure`` for interactive
MCP server lifecycle management (issue #690 Phase 2).

Relies on tools/mcp_tool.py for connection/discovery and keeps
configuration in ~/.hermes/config.yaml under the ``mcp_servers`` key.

### 顶层函数

#### def `cmd_mcp_add(args)`

Add a new MCP server with discovery-first tool selection.

#### def `cmd_mcp_remove(args)`

Remove an MCP server from config.

#### def `cmd_mcp_list(args = None)`

List all configured MCP servers.

#### def `cmd_mcp_test(args)`

Test connection to an MCP server.

#### def `cmd_mcp_login(args)`

Force re-authentication for an OAuth-based MCP server.

Deletes cached tokens (both on disk and in the running process's
MCPOAuthManager cache) and triggers a fresh OAuth flow via the
existing probe path.

Use this when:
  - Tokens are stuck in a bad state (server revoked, refresh token
    consumed by an external process, etc.)
  - You want to re-authenticate to change scopes or account
  - A tool call returned ``needs_reauth: true``

#### def `cmd_mcp_reauth(args)`

Re-authenticate one OAuth MCP server, or all of them sequentially.

``hermes mcp reauth <name>`` re-auths a single server (same as ``login``).
``hermes mcp reauth --all`` discovers every ``auth: oauth`` server in
config and re-auths them ONE AT A TIME.

Serial-by-design: a human can only complete one browser OAuth flow at a
time, so re-authing all servers concurrently would open N tabs at once
and N-1 would time out. This is the self-service fix for the recurring
stale-client ritual in GH#36767 (and avoids the startup popup storm when
several servers go stale at once).

#### def `cmd_mcp_configure(args)`

Reconfigure which tools are enabled for an existing MCP server.

#### def `mcp_command(args)`

Main dispatcher for ``hermes mcp`` subcommands.


## hermes_cli.mcp_picker

### 模块文档

MCP picker — interactive `hermes mcp picker` (also the default `hermes mcp`).

Lists every catalog entry plus any custom MCP servers the user has added via
``hermes mcp add``, lets them pick one, and routes to install / enable /
disable / uninstall / configure-tools flows.

Mirrors the `hermes plugin` picker UX: arrow keys to navigate, ENTER on a row
to act on it. The action depends on current status:

  not installed (catalog)   → install  (clone/bootstrap if needed, prompt for creds)
  installed / disabled      → enable
  installed / enabled       → submenu: configure tools / disable / uninstall / reinstall
  custom (non-catalog)      → submenu: configure tools / enable / disable / remove

The picker loops until the user hits ESC/q so they can manage multiple
entries in one session.

### 顶层函数

#### def `show_catalog() -> None`

`hermes mcp catalog` — print the curated list + custom servers, no interaction.

#### def `run_picker() -> None`

`hermes mcp picker` (and default `hermes mcp`) — interactive selector.

Loops until the user hits ESC/q. After each action the picker re-renders
so the user can manage several entries in one session.

#### def `install_by_name(identifier: str) -> int`

`hermes mcp install <name>` — non-interactive entry-point.

Returns 0 on success, non-zero on failure (so the CLI can propagate
exit codes).


## hermes_cli.mcp_security

### 模块文档

Security checks for user-configured MCP server entries.

MCP stdio transports intentionally support arbitrary local commands so users can
run custom servers. This module does not try to sandbox that capability. It
blocks two high-signal abuse shapes seen in the wild:

1. The exfiltration shape from #45620: a shell interpreter whose inline script
   invokes network egress tooling.
2. The persistence shape from the June 2026 ``hermes-0day`` campaign: a shell
   interpreter whose inline script writes to OS persistence surfaces
   (``~/.ssh/authorized_keys``, ``/etc/ssh``, ``/etc/pam.d``, ``sudoers``,
   crontab, shell rc files). The campaign planted ``command: bash`` MCP entries
   whose payload appended an attacker SSH key to ``authorized_keys``; Hermes
   re-executed them on every cron tick / startup, re-installing the backdoor.

3. A hardcoded indicator-of-compromise (IOC) blocklist for that campaign — the
   attacker's ``hermes-0day`` SSH public key and source IPs. Any entry whose
   command/args/env carry an IOC is refused outright, regardless of shape, so a
   pre-planted ``config.yaml`` cannot spawn it.

These checks run BOTH at save time (``_save_mcp_server`` — dashboard API + CLI)
and at spawn time (``tools.mcp_tool._filter_suspicious_mcp_servers`` — discovery
/ cron / startup), so a hand-edited or pre-planted entry is also caught before
it can execute.

### 顶层函数

#### def `validate_mcp_server_entry(name: str, entry: dict[str, Any]) -> list[str]`

Return security warnings for an MCP server entry.

Empty return means the entry is not suspicious. This is intentionally not a
whitelist: legitimate local MCPs can still use custom commands, Python
scripts, npx, uvx, etc. We block three narrow shapes only:

* a known hermes-0day IOC anywhere in command/args/env (hardcoded blocklist);
* a shell interpreter whose inline script invokes network egress (#45620);
* a shell interpreter whose inline script writes to an OS persistence
  surface (June 2026 hermes-0day SSH/PAM/sudoers/cron shape).

#### def `is_mcp_server_entry_suspicious(name: str, entry: dict[str, Any]) -> bool`


## hermes_cli.mcp_startup

### 模块文档

Shared CLI/TUI-safe helpers for background MCP discovery.

### 顶层函数

#### def `start_background_mcp_discovery(logger, thread_name: str) -> None`

Spawn one shared background MCP discovery thread for this process.

#### def `wait_for_mcp_discovery(timeout: float | None = None) -> None`

Wait for background MCP discovery before the first tool snapshot.

``thread.join(timeout)`` returns the INSTANT discovery completes, so this
only ever blocks for the real connect time of a still-pending server —
users with no MCP servers or fast servers pay ~0s.  The bound (from
``mcp_discovery_timeout`` in config) just caps the wait so a dead server
can't freeze startup; servers that miss it are picked up by the automatic
late-binding refresh.

#### def `mcp_discovery_in_flight() -> bool`

Return True if THIS module's background discovery thread is still running.

Mirrors ``tui_gateway.entry.mcp_discovery_in_flight`` for the surfaces that
start discovery through ``start_background_mcp_discovery`` here (the desktop
app + dashboard WebSocket sidecar via ``tui_gateway/ws.py``, and
``hermes dashboard``).  Those processes populate THIS module's
``_mcp_discovery_thread``, not ``tui_gateway.entry``'s, so the late-refresh
scheduler must consult both to decide whether a slow server's tools are
still pending (see #51587).

#### def `join_mcp_discovery(timeout: float | None = None) -> bool`

Block until THIS module's background discovery finishes, up to ``timeout``.

Returns True if discovery has completed (thread absent or no longer alive),
False if it is still running after the timeout.  Unlike
``wait_for_mcp_discovery`` this accepts an unbounded/long wait and reports
the outcome, for the off-critical-path late-refresh waiter.


## hermes_cli.memory_oauth

### 模块文档

HTTP routes for memory-provider OAuth connect, mounted by ``web_server``.

Kept out of ``web_server.py`` so the memory feature's surface stays in the
memory layer. Dispatch is by convention: a provider's flow lives at
``plugins.memory.<provider>.oauth_flow`` exposing ``start_loopback_flow_background``
and ``get_flow_status``; a provider without that module simply 404s. No provider
is named here.

### 顶层函数

#### def `start_memory_oauth(provider: str, profile: Optional[str] = None)`

Begin a provider's zero-CLI OAuth flow — opens the browser and captures
the grant via the loopback listener. Returns immediately; poll status.

**异常**: `HTTPException`

#### def `memory_oauth_status(provider: str, profile: Optional[str] = None)`

Poll a provider's OAuth flow: idle | pending | connected | error.

**异常**: `HTTPException`


## hermes_cli.memory_setup

### 模块文档

hermes memory setup|status — configure memory provider plugins.

Auto-detects installed memory providers via the plugin system.
Interactive curses-based UI for provider selection, then walks through
the provider's config schema. Writes config to config.yaml + .env.

### 顶层函数

#### def `cmd_setup_provider(provider_name: str) -> None`

Run memory setup for a specific provider, skipping the picker.

#### def `cmd_setup(args) -> None`

Interactive memory provider setup wizard.

#### def `cmd_status(args) -> None`

Show current memory provider config.

#### def `memory_command(args) -> None`

Route memory subcommands.


## hermes_cli.middleware

### 模块文档

Hermes middleware contract helpers.

Observer hooks report what happened. Middleware can change what happens by
rewriting a request or wrapping the actual execution callback. Keep the small
contract helpers here so agent-loop call sites and plugins share one vocabulary.

### class RequestMiddlewareResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of applying request middleware to a mutable payload.


### 顶层函数

#### def `observer_payload(**kwargs: Any) -> Dict[str, Any]`

#### def `middleware_payload(**kwargs: Any) -> Dict[str, Any]`

#### def `apply_llm_request_middleware(request: Dict[str, Any], **context: Any) -> RequestMiddlewareResult`

Apply registered LLM request middleware.

Middleware may return ``{"request": {...}}`` to replace the effective
provider kwargs before Hermes sends them.

#### def `apply_tool_request_middleware(tool_name: str, args: Dict[str, Any], **context: Any) -> RequestMiddlewareResult`

Apply registered tool request middleware.

Middleware may return ``{"args": {...}}`` to replace the effective tool
arguments before hooks, guardrails, approvals, and execution see them.

#### def `apply_api_request_middleware(request: Dict[str, Any], **context: Any) -> RequestMiddlewareResult`

Compatibility wrapper for older ``api_request`` naming.

#### def `run_llm_execution_middleware(request: Dict[str, Any], next_call: Callable[[Dict[str, Any]], Any], **context: Any) -> Any`

Run provider execution through registered LLM execution middleware.

#### def `run_tool_execution_middleware(tool_name: str, args: Dict[str, Any], next_call: Callable[[Dict[str, Any]], Any], **context: Any) -> Any`

Run tool execution through registered tool execution middleware.

#### def `run_api_execution_middleware(request: Dict[str, Any], next_call: Callable[[Dict[str, Any]], Any], **context: Any) -> Any`

Compatibility wrapper for older ``api_execution`` naming.


## hermes_cli.migrate

### 模块文档

CLI handlers for ``hermes migrate ...``.

Currently exposes only ``hermes migrate xai`` — diagnoses and (with --apply)
rewrites references to xAI models retired on May 15, 2026.

### 顶层函数

#### def `cmd_migrate(args: Any) -> int`

Dispatcher for ``hermes migrate <subtype>``.

#### def `cmd_migrate_xai(args: Any) -> int`

Run xAI May-15 model migration in dry-run or apply mode.


## hermes_cli.moa_cmd

### 模块文档

CLI helpers for configuring Mixture of Agents.

### 顶层函数

#### def `cmd_moa(args) -> None`

Manage Mixture of Agents model presets.

**异常**: `SystemExit`


## hermes_cli.moa_config

### 模块文档

Mixture-of-Agents configuration and slash-command helpers.

### 顶层函数

#### def `validate_moa_payload(raw: Any) -> list[str]`

Return the problems ``normalize_moa_config`` would silently paper over.

``normalize_moa_config`` is deliberately tolerant: at *read* time a
hand-edited config must degrade to defaults rather than crash the agent.
That same tolerance at *write* time is a corruption engine — a client that
sends a half-filled slot gets its whole preset silently replaced with the
hardcoded defaults (#64156). API write paths call this first and reject
invalid payloads loudly instead of saving something the user never chose.

Returns a list of human-readable problems; empty means safe to save.

#### def `normalize_moa_config(raw: Any) -> dict[str, Any]`

Return validated MoA config with named presets.

Backward compatible with the first PR shape where ``moa`` itself contained
``reference_models`` and ``aggregator`` directly.

#### def `list_moa_presets(config: Any) -> list[str]`

#### def `resolve_moa_preset(config: Any, name: str | None = None) -> dict[str, Any]`

**异常**: `MoAPresetNotFoundError`

#### def `exact_moa_preset_name(config: Any, text: str) -> str | None`

Return the preset name iff ``text`` exactly matches an *enabled* preset.

Used by the no-explicit-provider switch path (PATH B in
``hermes_cli/model_switch.py``) to recognize a bare ``/model <preset>``
that the user typed without the ``moa:`` prefix. This is an *implicit*
match, so it must honor the per-preset ``enabled`` opt-out: a user who set
``enabled: false`` to disable a preset must not have a plain model switch
whose name happens to collide with that preset key silently pivot the
session onto the MoA virtual provider (issue #55187). Explicit selection
via ``--provider moa`` / the model picker does not go through here, so a
disabled preset is still reachable when the user explicitly asks for it.

#### def `set_active_moa_preset(config: Any, name: str | None) -> dict[str, Any]`

**异常**: `KeyError`

#### def `encode_moa_turn(prompt: str, config: Any = None, preset: str | None = None) -> str`

Encode a /moa one-shot turn for frontends that can only send text.

#### def `decode_moa_turn(message: Any) -> tuple[str, dict[str, Any] | None]`

Decode a hidden /moa one-shot marker.

#### def `build_moa_turn_prompt(user_prompt: str, config: Any = None, preset: str | None = None) -> str`

Build the hidden one-shot payload used by TUI/gateway routing.

#### def `moa_usage() -> str`


## hermes_cli.model_catalog

### 模块文档

Remote model catalog fetcher.

The Hermes docs site hosts a JSON manifest of curated models for providers
we want to update without shipping a release (currently OpenRouter and
Nous Portal). This module fetches, validates, and caches that manifest,
falling back to the in-repo hardcoded lists when the network is unavailable.

Pipeline
--------
1. ``get_catalog()`` — returns a parsed manifest dict.
   - Checks in-process cache (invalidated by TTL).
   - Reads disk cache at ``~/.hermes/cache/model_catalog.json``.
   - Fetches the master URL if disk cache is stale or missing.
   - On any fetch failure, keeps using the stale cache (or empty dict).

2. ``get_curated_openrouter_models()`` / ``get_curated_nous_models()`` —
   thin accessors returning the shapes existing callers expect. Each
   falls back to the in-repo hardcoded list on any lookup failure.

Schema (version 1)
------------------
::

    {
      "version": 1,
      "updated_at": "2026-04-25T22:00:00Z",
      "metadata": {...},                # free-form
      "providers": {
        "openrouter": {
          "metadata": {...},            # free-form
          "models": [
            {"id": "vendor/model", "description": "recommended",
             "metadata": {...}}          # free-form, model-level
          ]
        },
        "nous": {...}
      }
    }

Unknown fields are ignored — extra metadata can be added at either level
without bumping ``version``. ``version`` bumps are reserved for
breaking changes (renaming ``providers``, changing ``models`` shape).

### 顶层函数

#### def `get_catalog(force_refresh: bool = False) -> dict[str, Any]`

Return the parsed model catalog manifest, or an empty dict on failure.

Callers should treat a missing provider/model as "use the in-repo fallback"
— never raise from this function so the CLI keeps working offline.

#### def `get_curated_openrouter_models() -> list[tuple[str, str]] | None`

Return OpenRouter's curated ``[(id, description), ...]`` from the manifest.

Returns ``None`` when the manifest is unavailable, so callers can fall
back to their hardcoded list.

#### def `get_curated_nous_models() -> list[str] | None`

Return Nous Portal's curated list of model ids from the manifest.

Returns ``None`` when the manifest is unavailable.

#### def `get_default_model_from_cache(provider: str) -> str | None`

Return the catalog's labeled default model for ``provider`` — cache only.

The manifest marks exactly one model entry per provider with
``"default": true``; that entry is the model Hermes silently lands on when
the user never picked one. This accessor reads ONLY the in-process copy or
the disk cache — it NEVER triggers a network fetch, so it is safe on hot
resolution paths (agent build, gateway session setup) that must stay
network-free. The cache is kept fresh by the picker/`hermes update` paths;
when no cached manifest exists (fresh install, offline), returns None and
the caller falls back to the in-repo constant.

#### def `seed_cache_from_checkout(project_root: Path | str) -> bool`

Overwrite the disk cache with the catalog shipped in a local checkout.

``hermes update`` pulls the latest repo, so the freshly-pulled
``website/static/api/model-catalog.json`` IS the newest catalog — no
network round-trip needed. Copying it straight over the disk cache keeps
the model picker current even when the remote manifest fetch is bot-gated
or the Portal hiccups.

Reads the shipped manifest, validates it against the schema, and writes it
to ``~/.hermes/cache/model_catalog.json`` via the same atomic writer the
network path uses. Returns ``True`` on success, ``False`` if the file is
missing, malformed, or fails validation (caller should treat a ``False``
as non-fatal — the network fetch path still applies on the next picker
open).

#### def `reset_cache() -> None`

Clear the in-process cache. Used by tests and ``hermes model --refresh``.


## hermes_cli.model_cost_guard

### 模块文档

Expensive-model confirmation helpers for model selection surfaces.

### class ExpensiveModelWarning

> 继承: `object` ｜ 方法数: 0（公开 0）

Confirmation payload for models above Hermes' cost guardrail.


### 顶层函数

#### def `expensive_model_warning(model_name: str, provider: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None, model_info: Optional[ModelInfo] = None) -> Optional[ExpensiveModelWarning]`

Return a warning payload when known pricing exceeds safety thresholds.

The guard only triggers when pricing is known. Callers should use this after
model resolution so aliases and provider-specific model IDs have settled.


## hermes_cli.model_normalize

### 模块文档

Per-provider model name normalization.

Different LLM providers expect model identifiers in different formats:

- **Aggregators** (OpenRouter, Nous, AI Gateway, Kilo Code) need
  ``vendor/model`` slugs like ``anthropic/claude-sonnet-4.6``.
- **Anthropic** native API expects bare names with dots replaced by
  hyphens: ``claude-sonnet-4-6``.
- **Copilot** expects bare names *with* dots preserved:
  ``claude-sonnet-4.6``.
- **OpenCode Zen** preserves dots for GPT/GLM/Gemini/Kimi/MiniMax-style
  model IDs, but Claude still uses hyphenated native names like
  ``claude-sonnet-4-6``.
- **OpenCode Go** preserves dots in model names: ``minimax-m2.7``.
- **DeepSeek** accepts ``deepseek-chat`` (V3), ``deepseek-reasoner``
  (R1-family), and the first-class V-series IDs (``deepseek-v4-pro``,
  ``deepseek-v4-flash``, and any future ``deepseek-v<N>-*``).  Older
  Hermes revisions folded every non-reasoner input into
  ``deepseek-chat``, which on aggregators routes to V3 — so a user
  picking V4 Pro was silently downgraded.
- **Custom** and remaining providers pass the name through as-is.

This module centralises that translation so callers can simply write::

    api_model = normalize_model_for_provider(user_input, provider)

Inspired by Clawdbot's ``normalizeAnthropicModelId`` pattern.

### 顶层函数

#### def `detect_vendor(model_name: str) -> Optional[str]`

Detect the vendor slug from a bare model name.

Uses the first hyphen-delimited token of the model name to look up
the corresponding vendor in ``_VENDOR_PREFIXES``.  Also handles
case-insensitive matching and special patterns.

Args:
    model_name: A model name, optionally already including a
        ``vendor/`` prefix.  If a prefix is present it is used
        directly.

Returns:
    The vendor slug (e.g. ``"anthropic"``, ``"openai"``) or ``None``
    if no vendor can be confidently detected.

Examples::

    >>> detect_vendor("claude-sonnet-4.6")
    'anthropic'
    >>> detect_vendor("gpt-5.4-mini")
    'openai'
    >>> detect_vendor("anthropic/claude-sonnet-4.6")
    'anthropic'
    >>> detect_vendor("my-custom-model")

#### def `normalize_model_for_provider(model_input: str, target_provider: str) -> str`

Translate a model name into the format the target provider's API expects.

This is the primary entry point for model name normalisation.  It
accepts any user-facing model identifier and transforms it for the
specific provider that will receive the API call.

Args:
    model_input: The model name as provided by the user or config.
        Can be bare (``"claude-sonnet-4.6"``), vendor-prefixed
        (``"anthropic/claude-sonnet-4.6"``), or already in native
        format (``"claude-sonnet-4-6"``).
    target_provider: The canonical Hermes provider id, e.g.
        ``"openrouter"``, ``"anthropic"``, ``"copilot"``,
        ``"deepseek"``, ``"custom"``.  Should already be normalised
        via ``hermes_cli.models.normalize_provider()``.

Returns:
    The model identifier string that the target provider's API
    expects.

Raises:
    No exceptions -- always returns a best-effort string.

Examples::

    >>> normalize_model_for_provider("claude-sonnet-4.6", "openrouter")
    'anthropic/claude-sonnet-4.6'

    >>> normalize_model_for_provider("anthropic/claude-sonnet-4.6", "anthropic")
    'claude-sonnet-4-6'

    >>> normalize_model_for_provider("anthropic/claude-sonnet-4.6", "copilot")
    'claude-sonnet-4.6'

    >>> normalize_model_for_provider("openai/gpt-5.4", "copilot")
    'gpt-5.4'

    >>> normalize_model_for_provider("claude-sonnet-4.6", "opencode-zen")
    'claude-sonnet-4-6'

    >>> normalize_model_for_provider("minimax-m2.5-free", "opencode-zen")
    'minimax-m2.5-free'

    >>> normalize_model_for_provider("deepseek-v3", "deepseek")
    'deepseek-chat'

    >>> normalize_model_for_provider("deepseek-r1", "deepseek")
    'deepseek-reasoner'

    >>> normalize_model_for_provider("my-model", "custom")
    'my-model'

    >>> normalize_model_for_provider("claude-sonnet-4.6", "zai")
    'claude-sonnet-4.6'

    >>> normalize_model_for_provider("MiMo-V2.5-Pro", "xiaomi")
    'mimo-v2.5-pro'

**异常**: `Examples`


## hermes_cli.model_setup_flows

### 模块文档

Per-provider model-selection wizard flows for ``hermes setup`` / ``hermes model``.

Extracted from ``hermes_cli/main.py`` as part of the god-file decomposition
campaign (``~/.hermes/plans/god-file-decomposition.md``, Phase 2 — splitting
main.py handler/flow bodies out of the module). These 18 ``_model_flow_*``
functions are the interactive provider-setup branches dispatched by
``select_provider_and_model`` (which stays in main.py).

Behavior-neutral: each function is lifted verbatim. ``select_provider_and_model``
in main.py re-imports them (``from hermes_cli.model_setup_flows import *``-style
explicit import) so existing call sites — and test monkeypatches that target
``hermes_cli.main._model_flow_*`` — keep resolving against main.py's namespace.

main.py-internal helpers the flows call (``_prompt_api_key``, ``_save_custom_provider``,
the reasoning-effort/stepfun/qwen helpers, ``_run_anthropic_oauth_flow``, …) are
imported lazily inside the flows (``from hermes_cli.main import ...`` resolves at
call time, when main.py is fully loaded) so this module never imports
``hermes_cli.main`` at import time -> no import cycle.

### 顶层函数

#### def `bedrock_region_geo_prefix(region_name: str) -> str`

Map an AWS region name to its inference-profile geo prefix ('' = unknown).

#### def `bedrock_model_routable_from_region(model_id: str, region_name: str) -> bool`

True when *model_id* can be invoked from *region_name*'s endpoint.

Bare foundation-model ids and ``global.*`` profiles route from anywhere.
Geo-prefixed inference profiles (``us.*``, ``eu.*``, ...) only route from
endpoints in their own geography. Unknown region shapes hide nothing.


## hermes_cli.model_switch

### 模块文档

Shared model-switching logic for CLI and gateway /model commands.

Both the CLI (cli.py) and gateway (gateway/run.py) /model handlers
share the same core pipeline:

  parse flags -> alias resolution -> provider resolution ->
  credential resolution -> normalize model name ->
  metadata lookup -> build result

This module ties together the foundation layers:

- ``agent.models_dev``            -- models.dev catalog, ModelInfo, ProviderInfo
- ``hermes_cli.providers``        -- canonical provider identity + overlays
- ``hermes_cli.model_normalize``  -- per-provider name formatting

Provider switching uses the ``--provider`` flag exclusively.
No colon-based ``provider:model`` syntax — colons are reserved for
OpenRouter variant suffixes (``:free``, ``:extended``, ``:fast``).

### class ModelIdentity

> 继承: `NamedTuple` ｜ 方法数: 0（公开 0）

Vendor slug and family prefix used for catalog resolution.


### class DirectAlias

> 继承: `NamedTuple` ｜ 方法数: 0（公开 0）

Exact model mapping that bypasses catalog resolution.


### class ModelSwitchResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of a model switch attempt.


### class ModelFlagParseResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Parsed flags for a /model command.


### 顶层函数

#### def `format_model_for_display(model_name: str) -> str`

Return a human-friendly form of *model_name* for CLI status output.

Strips known opaque proxy prefixes (Palantir Foundry's
``ri.language-model-service..language-model.*``) and returns the
trailing slug. Falls through to the original string for everything
else, so real model IDs (``claude-4-7-opus-20260101``,
``gpt-5-4``, ``meta-llama/Llama-3.3-70B-Instruct``) are untouched.

This is a DISPLAY-ONLY helper. Do NOT use the return value for any
wire-side operation — the proxy expects the full opaque ID, and
callers that compare or persist must keep the original.

#### def `is_nous_hermes_non_agentic(model_name: str) -> bool`

Return True if *model_name* is a real Nous Hermes 3/4 chat model.

Used to decide whether to surface the non-agentic warning at startup.
Callers in :mod:`cli.py` and here should go through this single helper
so the two sites don't drift.

#### def `parse_model_flags_detailed(raw_args: str) -> ModelFlagParseResult`

Parse flags from /model command args.

Returns a :class:`ModelFlagParseResult`. ``--once`` is intentionally
parsed here but interpreted by each caller because each frontend has its
own live-session restore hook.

``is_global`` and ``is_session`` are independent flag presences; the
*effective* persistence decision is resolved by
:func:`resolve_persist_behavior` so the config-gated default
(``model.persist_switch_by_default``) is applied in one place.

Examples::

    "sonnet"                         -> ("sonnet", "", False, False, False)
    "sonnet --global"                -> ("sonnet", "", True, False, False)
    "sonnet --session"               -> ("sonnet", "", False, False, True)
    "sonnet --once"                  -> is_once=True
    "sonnet --provider anthropic"    -> ("sonnet", "anthropic", False, False, False)
    "--provider my-ollama"           -> ("", "my-ollama", False, False, False)
    "--refresh"                      -> ("", "", False, True, False)
    "sonnet --provider anthropic --global" -> ("sonnet", "anthropic", True, False, False)

#### def `parse_model_flags(raw_args: str) -> tuple[str, str, bool, bool, bool]`

Parse legacy /model flags and return the historical 5-tuple.

New call sites that care about ``--once`` should use
:func:`parse_model_flags_detailed`.

#### def `resolve_persist_behavior(is_global: bool, is_session: bool, is_once: bool = False, explicit_provider: str = '') -> bool`

Decide whether a ``/model`` switch should persist to ``config.yaml``.

Resolution order:

1. ``--once`` explicitly opts out → ``False`` (next turn only).
2. ``--session`` explicitly opts out → ``False`` (this session only).
3. ``--global`` explicitly opts in → ``True``.
4. ``--provider`` given without an explicit persist flag → ``False``
   (session only).  Provider switches are typically exploratory — the
   user is trying a different backend for this conversation, not
   reconfiguring the default.  ``--global`` can still force persist.
5. Otherwise defer to ``model.persist_switch_by_default`` in
   ``config.yaml`` (defaults to ``False``: a plain ``/model <name>``
   affects only the current session).  Users who want the old
   persist-by-default behavior can set the key to ``true``; a one-off
   ``--global`` always persists.

The config read is defensive: on a fresh install ``model`` may be a
flat string rather than a dict, in which case the built-in default
(``False``) applies.

#### def `resolve_alias(raw_input: str, current_provider: str) -> Optional[tuple[str, str, str]]`

Resolve a short alias against the current provider's catalog.

Looks up *raw_input* in :data:`MODEL_ALIASES`, then searches the
current provider's models.dev catalog for the model whose ID starts
with ``vendor/family`` (or just ``family`` for non-aggregator
providers) and has the **highest version**.

Returns:
    ``(provider, resolved_model_id, alias_name)`` if a match is
    found on the current provider, or ``None`` if the alias doesn't
    exist or no matching model is available.

#### def `get_authenticated_provider_slugs(current_provider: str = '', user_providers: dict = None, custom_providers: list | None = None) -> list[str]`

Return slugs of providers that have credentials.

Uses ``list_authenticated_providers()`` which is backed by the models.dev
in-memory cache (1 hr TTL) — no extra network cost.

#### def `resolve_display_context_length(model: str, provider: str, base_url: str = '', api_key: str = '', model_info: Optional[ModelInfo] = None, custom_providers: list | None = None, config_context_length: int | None = None) -> Optional[int]`

Resolve the context length to show in /model output.

models.dev reports per-vendor context (e.g. gpt-5.5 = 1.05M on openai)
but provider-enforced limits can be lower (e.g. Codex OAuth caps the
same slug at 272k). The authoritative source is
``agent.model_metadata.get_model_context_length`` which already knows
about Codex OAuth, Copilot, Nous, and falls back to models.dev for the
rest.

When ``custom_providers`` is provided, per-model ``context_length``
overrides from ``custom_providers[].models.<id>.context_length`` are
honored — this closes #15779 where ``/model`` switch ignored user-set
overrides.

Prefer the provider-aware value; fall back to ``model_info.context_window``
only if the resolver returns nothing.

#### def `switch_model(raw_input: str, current_provider: str, current_model: str, current_base_url: str = '', current_api_key: str = '', is_global: bool = False, explicit_provider: str = '', user_providers: dict = None, custom_providers: list | None = None) -> ModelSwitchResult`

Core model-switching pipeline shared between CLI and gateway.

Resolution chain:

  If --provider given:
    a. Resolve provider via resolve_provider_full()
    b. Resolve credentials
    c. If model given, resolve alias on target provider or use as-is
    d. If no model, auto-detect from endpoint

  If no --provider:
    a. Try alias resolution on current provider
    b. If alias exists but not on current provider -> fallback
    c. On aggregator, try vendor/model slug conversion
    d. Aggregator catalog search
    e. detect_provider_for_model() as last resort
    f. Resolve credentials
    g. Normalize model name for target provider

  Finally:
    h. Get full model metadata from models.dev
    i. Build result

Args:
    raw_input: The model name (after flag parsing).
    current_provider: The currently active provider.
    current_model: The currently active model name.
    current_base_url: The currently active base URL.
    current_api_key: The currently active API key.
    is_global: Whether to persist the switch.
    explicit_provider: From --provider flag (empty = no explicit provider).
    user_providers: The ``providers:`` dict from config.yaml (for user endpoints).
    custom_providers: The ``custom_providers:`` list from config.yaml.

Returns:
    ModelSwitchResult with all information the caller needs.

#### def `prewarm_picker_cache_async() -> Optional['_threading.Thread']`

Warm the provider-models disk cache in a background daemon thread.

The no-args ``/model`` picker calls ``list_authenticated_providers()``,
which fetches each authenticated provider's live ``/v1/models`` list on a
cold/stale cache. Those fetches are independent HTTP round-trips but run
serially, so the first ``/model`` open in a session (or any open after the
1h cache TTL expires) blocks ~1-2s on the user's critical path.

This pre-warms that exact path off-thread during idle session time: it
runs ``list_authenticated_providers()`` once, which populates
``provider_models_cache.json`` for every authed provider. By the time the
user types ``/model``, the picker hits the warm disk cache and renders in
~100ms.

Fire-and-forget. Process-level Event guard ensures it runs at most once.
Fully exception-isolated — a slow or offline provider can never affect the
session. Returns the spawned thread (for tests) or None if already warmed.

#### def `list_authenticated_providers(current_provider: str = '', current_base_url: str = '', user_providers: dict = None, custom_providers: list | None = None, force_fresh_nous_tier: bool = False, max_models: int | None = None, current_model: str = '', refresh: bool = False, probe_custom_providers: bool = True, probe_current_custom_provider: bool = False, for_picker: bool = False, excluded_providers: list | None = None) -> List[dict]`

Detect which providers have credentials and list their curated models.

Uses the curated model lists from hermes_cli/models.py (OPENROUTER_MODELS,
_PROVIDER_MODELS) — NOT the full models.dev catalog.  These are hand-picked
agentic models that work well as agent backends.

Returns a list of dicts, each with:
  - slug: str — the --provider value to use
  - name: str — display name
  - is_current: bool
  - is_user_defined: bool
  - models: list[str] — curated model IDs (up to max_models)
  - total_models: int — total curated count
  - source: str — "built-in", "models.dev", "user-config"

Only includes providers that have API keys set or are user-defined endpoints.
``force_fresh_nous_tier`` bypasses the short Nous tier cache for explicit
account-sensitive flows. UI picker opens should leave it false so they do
not block on fresh Portal/account checks every time.

``refresh`` busts the per-provider model-id disk cache
(``provider_models_cache.json``) up front so every row re-fetches its
live catalog. Use for an explicit user-triggered "refresh models" action
(e.g. the desktop picker's refresh control); leave false for normal picker
opens so they stay snappy on the 1h cache.

``probe_custom_providers`` controls live ``/models`` discovery for saved
custom OpenAI-compatible endpoints. Keep the default true for CLI parity;
GUI picker opens can pass false to show configured models immediately
without waiting on offline local endpoints.

``probe_current_custom_provider`` is the middle ground for GUI picker
opens: probe only the currently-selected custom endpoint so its model list
matches the active provider without blocking on every saved/offline custom
endpoint.

#### def `list_picker_providers(current_provider: str = '', current_base_url: str = '', user_providers: dict = None, custom_providers: list | None = None, max_models: int | None = None, current_model: str = '', include_moa: bool = False, excluded_providers: list | None = None) -> List[dict]`

Interactive-picker variant of :func:`list_authenticated_providers`.

Post-processes the base list so the ``/model`` picker (Telegram/Discord
inline keyboards) only surfaces models that are actually callable in the
current install:

- OpenRouter's model list is replaced with the output of
  :func:`hermes_cli.models.fetch_openrouter_models`, which filters the
  curated ``OPENROUTER_MODELS`` snapshot against the live OpenRouter
  catalog.  IDs the live catalog no longer carries drop out, so the
  picker never offers a model the user can't call.
- Provider rows whose model list ends up empty are dropped, except
  custom endpoints (``is_user_defined=True`` with an ``api_url``) where
  the user may supply their own model set through config.

All other providers and metadata fields are passed through unchanged.
The typed ``/model <name>`` path is unaffected -- only the interactive
picker payload is narrowed.


## hermes_cli.models

### 模块文档

Canonical model catalogs and lightweight validation helpers.

Add, remove, or reorder entries here — both `hermes setup` and
`hermes` provider-selection will pick up the change automatically.

### class ProviderEntry

> 继承: `NamedTuple` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `is_nous_free_tier(account_info: dict[str, Any]) -> bool`

Return True if the account info indicates a free (unpaid) tier.

Prefer the Portal's explicit ``paid_service_access.allowed`` entitlement
decision.  Legacy payloads fall back to ``subscription.monthly_charge == 0``.
Returns False when both signals are missing or unparseable.

#### def `partition_nous_models_by_tier(model_ids: list[str], pricing: dict[str, dict[str, str]], free_tier: bool) -> tuple[list[str], list[str]]`

Split Nous models into (selectable, unavailable) based on user tier.

For paid-tier users: all models are selectable, none unavailable.

For free-tier users: only free models are selectable; paid models
are returned as unavailable (shown grayed out in the menu).

#### def `union_with_portal_free_recommendations(curated_ids: list[str], pricing: dict[str, dict[str, str]], portal_base_url: str = '', force_refresh: bool = False) -> tuple[list[str], dict[str, dict[str, str]]]`

Augment curated list + pricing with the Portal's ``freeRecommendedModels``.

The Portal's ``/api/nous/recommended-models`` endpoint advertises which
models are free *right now* — independent of what the in-repo
``_PROVIDER_MODELS["nous"]`` list happens to contain or whether the
docs-hosted catalog manifest has been rebuilt since the last release.

For free-tier users this is the source of truth: any model the Portal
flags as free should be selectable, even if the user is running an
older Hermes that doesn't ship that model in its hardcoded curated
list.  This function returns an augmented ``(model_ids, pricing)``
pair where:

* Portal free recommendations missing from ``curated_ids`` are
  appended after the curated list (so the in-repo curated models
  show first and Portal-only picks follow).
* ``pricing`` gets a synthetic ``{"prompt": "0", "completion": "0"}``
  entry for any free recommendation missing from the live pricing
  map, so :func:`partition_nous_models_by_tier` keeps it.

Failures (network, parse, missing field) are silent and degrade to
returning the inputs unchanged.

#### def `union_with_portal_paid_recommendations(curated_ids: list[str], pricing: dict[str, dict[str, str]], portal_base_url: str = '', force_refresh: bool = False) -> tuple[list[str], dict[str, dict[str, str]]]`

Augment curated list with the Portal's ``paidRecommendedModels``.

Mirror of :func:`union_with_portal_free_recommendations` for paid-tier
users. The Portal's ``/api/nous/recommended-models`` endpoint advertises
which paid models are blessed *right now* — independent of what the
in-repo ``_PROVIDER_MODELS["nous"]`` list happens to contain or whether
the docs-hosted catalog manifest has been rebuilt since the last release.

For paid-tier users this lets newly-launched paid models surface in the
picker even if the user is running an older Hermes that doesn't ship
them in its hardcoded curated list. This function returns an augmented
``(model_ids, pricing)`` pair where:

* Portal paid recommendations missing from ``curated_ids`` are
  appended after the curated list (so the in-repo curated models
  show first and Portal-only picks follow).
* ``pricing`` is left untouched — we deliberately do NOT synthesize
  pricing entries for paid models. Live pricing is fetched separately
  via :func:`get_pricing_for_provider`; if the live endpoint hasn't
  published pricing yet, the picker shows a blank price column rather
  than fabricating numbers. (The free helper synthesizes ``$0`` so
  :func:`partition_nous_models_by_tier` keeps free models selectable;
  no equivalent gating applies on the paid side, so synthesis would
  only mislead the user.)

Failures (network, parse, missing field) are silent and degrade to
returning the inputs unchanged — never block the picker on a
Portal-side hiccup.

#### def `check_nous_free_tier(force_fresh: bool = False) -> bool`

Check if the current Nous Portal user is on a free (unpaid) tier.

Results are cached for ``_FREE_TIER_CACHE_TTL`` seconds to avoid
hitting the Portal API on every call.  The cache is short-lived so
that an account upgrade is reflected within a few minutes.

Returns True only when entitlement is known to be free.  Unknown/error
states return False so this compatibility wrapper does not block users.

#### def `fetch_nous_recommended_models(portal_base_url: str = '', timeout: float = 5.0, force_refresh: bool = False) -> dict[str, Any]`

Fetch the Nous Portal's curated recommended-models payload.

Hits ``<portal>/api/nous/recommended-models``. The endpoint is public —
no auth is required. Results are cached per portal URL for
``_NOUS_RECOMMENDED_CACHE_TTL`` seconds in process; pass
``force_refresh=True`` to bypass the in-process cache.

A successful live fetch is also persisted to a per-base disk cache
(``$HERMES_HOME/cache/nous_recommended_cache.json``) as last-known-good.
When the live fetch fails (network, parse, non-2xx) and the in-process
cache is empty, the disk copy is returned instead of ``{}`` — so a
transient Portal hiccup no longer silently drops the free/paid model
recommendations from the picker. Self-heals on the next successful fetch.

Returns the parsed JSON dict, or ``{}`` only when neither the network nor
any cache layer can supply data. Callers must treat missing/null fields
as "no recommendation" and fall back to their own default.

#### def `get_nous_recommended_aux_model(vision: bool = False, free_tier: Optional[bool] = None, portal_base_url: str = '', force_refresh: bool = False) -> Optional[str]`

Return the Portal's recommended model name for an auxiliary task.

Picks the best field from the Portal's recommended-models payload:

* ``vision=True``  → ``paidRecommendedVisionModel``  (paid tier) or
                     ``freeRecommendedVisionModel``  (free tier)
* ``vision=False`` → ``paidRecommendedCompactionModel`` or
                     ``freeRecommendedCompactionModel``

When ``free_tier`` is ``None`` (default) the user's tier is auto-detected
via :func:`check_nous_free_tier`. Pass an explicit bool to bypass the
detection — useful for tests or when the caller already knows the tier.

For paid-tier users we prefer the paid recommendation but gracefully fall
back to the free recommendation if the Portal returned ``null`` for the
paid field (common during the staged rollout of new paid models).

Returns ``None`` when every candidate is missing, null, or the fetch
fails — callers should fall back to their own default (currently
``google/gemini-3-flash-preview``).

#### def `provider_group_for_slug(slug: str) -> str`

Return the group_id a provider slug belongs to, or "" if ungrouped.

#### def `group_providers(slugs)`

Fold a flat ordered slug iterable into picker rows by provider group.

DISPLAY ONLY. Used by every interactive picker (``hermes model``, the
setup wizard, the Telegram ``/model`` keyboard) so grouping is identical
across surfaces.

Each returned row is a dict::

    {"kind": "single", "slug": <slug>}                       # ungrouped, or
                                                              # 1-member group
    {"kind": "group", "group_id": <gid>, "label": <label>,
     "description": <desc>, "members": [<slug>, ...]}        # 2+ members

Rules:
  * A group row appears at the position of its FIRST present member, in
    the input order. Subsequent members fold into that row (and are not
    emitted again).
  * Member order inside a group follows ``PROVIDER_GROUPS`` declaration,
    restricted to the members actually present in ``slugs``.
  * A group reduced to a single present member degrades to a ``single``
    row — no pointless one-item submenu.
  * Slugs not in any group pass through as ``single`` rows, order
    preserved.
  * Duplicate slugs in the input are ignored after first sight.

#### def `get_preferred_silent_default_model(provider: str = 'openrouter') -> str`

Return the silent-default model id — catalog label first, constant second.

Reads the ``"default": true`` label from the cached remote catalog
(never hits the network — safe on hot resolution paths), falling back to
:data:`PREFERRED_SILENT_DEFAULT_MODEL` when no cached manifest exists or
the provider block carries no label.

#### def `pick_silent_default_model(model_ids: list[str], provider: str = 'openrouter') -> str`

Pick the silent default from an available-models list.

Returns the catalog-labeled default (see
:func:`get_preferred_silent_default_model`) when the list carries it,
else the first entry, else "". Used by every surface that must choose a
model on the user's behalf without an interactive picker (GUI onboarding
recommended-default, empty-model runtime fallback).

#### def `get_default_model_for_provider(provider: str) -> str`

Return a cost-safe default model for a provider, or "" if unknown.

Used as a NON-INTERACTIVE fallback when a provider is configured but no
model was ever selected (e.g. ``hermes auth add openai-codex`` without
``hermes model``, or a profile that sets ``provider`` with no ``model``).

For most providers this is the first entry in ``_PROVIDER_MODELS`` — the
same model the ``hermes model`` picker offers first. For metered aggregators
whose curated list is ordered most-capable-first, that entry is also the
most EXPENSIVE one, so silently defaulting to it is a billing footgun.
Those providers (``_SILENT_DEFAULT_PROVIDERS``) resolve through the
catalog-labeled default instead; a missing model must never auto-escalate
to the flagship.

#### def `fetch_openrouter_models(timeout: float = 8.0, force_refresh: bool = False) -> list[tuple[str, str]]`

Return the curated OpenRouter picker list, refreshed from the live catalog when possible.

#### def `model_ids(force_refresh: bool = False) -> list[str]`

Return just the OpenRouter model-id strings.

#### def `get_curated_nous_model_ids() -> list[str]`

Return the curated Nous Portal model-id list.

Prefers the remotely-hosted catalog manifest (published under
``website/static/api/model-catalog.json``); falls back to the in-repo
snapshot in ``_PROVIDER_MODELS["nous"]`` when the manifest is
unreachable. Always returns a list (never None).

#### def `fetch_models_with_pricing(api_key: str | None = None, base_url: str = 'https://openrouter.ai/api', timeout: float = 8.0, force_refresh: bool = False) -> dict[str, dict[str, str]]`

Fetch ``/v1/models`` and return ``{model_id: {prompt, completion}}`` pricing.

Results are cached per *base_url* so repeated calls are free.
Works with any OpenRouter-compatible endpoint (OpenRouter, Nous Portal).

#### def `get_pricing_for_provider(provider: str, force_refresh: bool = False) -> dict[str, dict[str, str]]`

Return live pricing for providers that support it (openrouter, nous, novita).

#### def `list_available_providers() -> list[dict[str, str]]`

Return info about all providers the user could use with ``provider:model``.

Each dict has ``id``, ``label``, and ``aliases``.
Checks which providers have valid credentials configured.

Derives the provider list from :data:`CANONICAL_PROVIDERS` (single
source of truth shared with ``hermes model``, ``/model``, etc.).

#### def `parse_model_input(raw: str, current_provider: str) -> tuple[str, str]`

Parse ``/model`` input into ``(provider, model)``.

Supports ``provider:model`` syntax to switch providers at runtime::

    openrouter:anthropic/claude-sonnet-4.5  →  ("openrouter", "anthropic/claude-sonnet-4.5")
    nous:hermes-3                           →  ("nous", "hermes-3")
    anthropic/claude-sonnet-4.5             →  (current_provider, "anthropic/claude-sonnet-4.5")
    gpt-5.4                                 →  (current_provider, "gpt-5.4")

The colon is only treated as a provider delimiter if the left side is a
recognized provider name or alias.  This avoids misinterpreting model names
that happen to contain colons (e.g. ``anthropic/claude-3.5-sonnet:beta``).

Returns ``(provider, model)`` where *provider* is either the explicit
provider from the input or *current_provider* if none was specified.

#### def `curated_models_for_provider(provider: Optional[str], force_refresh: bool = False) -> list[tuple[str, str]]`

Return ``(model_id, description)`` tuples for a provider's model list.

Tries to fetch the live model list from the provider's API first,
falling back to the static ``_PROVIDER_MODELS`` catalog if the API
is unreachable.

#### def `detect_static_provider_for_model(model_name: str, current_provider: str) -> Optional[tuple[str, str]]`

Auto-detect a provider from static catalogs only.

Returns ``(provider_id, model_name)``. The model name may be remapped
when a static alias or bare provider name resolves to a catalog default.
Returns ``None`` when no confident match is found.

#### def `detect_provider_for_model(model_name: str, current_provider: str) -> Optional[tuple[str, str]]`

Auto-detect the best provider for a model name.

Returns ``(provider_id, model_name)`` — the model name may be remapped
(e.g. bare ``deepseek-chat`` → ``deepseek/deepseek-chat`` for OpenRouter).
Returns ``None`` when no confident match is found.

Priority:
0. Bare provider name → switch to that provider's default model
1. Direct provider static catalog match
2. OpenRouter catalog match

#### def `normalize_provider(provider: Optional[str]) -> str`

Normalize provider aliases to Hermes' canonical provider ids.

Note: ``"auto"`` passes through unchanged — use
``hermes_cli.auth.resolve_provider()`` to resolve it to a concrete
provider based on credentials and environment.

#### def `provider_label(provider: Optional[str]) -> str`

Return a human-friendly label for a provider id or alias.

#### def `model_supports_fast_mode(model_id: Optional[str]) -> bool`

Return whether Hermes should expose the /fast toggle for this model.

#### def `resolve_fast_mode_overrides(model_id: Optional[str]) -> dict[str, Any] | None`

Return request_overrides for fast/priority mode, or None if unsupported.

Returns provider-appropriate overrides:
- OpenAI models: ``{"service_tier": "priority"}`` (Priority Processing)
- Anthropic models: ``{"speed": "fast"}`` (Anthropic Fast Mode beta)

The overrides are injected into the API request kwargs by
``_build_api_kwargs`` in run_agent.py — each API path handles its own
keys (service_tier for OpenAI/Codex, speed for Anthropic Messages).

#### def `provider_model_ids(provider: Optional[str], force_refresh: bool = False) -> list[str]`

Return the best known model catalog for a provider.

Tries live API endpoints for providers that support them (Codex, Nous),
falling back to static lists. For providers in ``_MODELS_DEV_PREFERRED``
(opencode-go/zen, xiaomi, deepseek, smaller inference providers, etc.),
models.dev entries are merged on top of curated so new models released
on the platform appear in ``/model`` without a Hermes release.

#### def `cached_provider_model_ids(provider: Optional[str], force_refresh: bool = False, ttl_seconds: int = _PROVIDER_MODELS_CACHE_TTL) -> list[str]`

Disk-cached wrapper around :func:`provider_model_ids`.

Hits the cache when fresh; otherwise calls the live function and
persists a non-empty result. Always returns a list (never None).

#### def `clear_provider_models_cache(provider: Optional[str] = None) -> None`

Drop a single provider's cache entry, or wipe the whole cache.

``provider=None`` wipes everything; otherwise only that provider's
entry is removed. Used by ``/model --refresh`` and
``hermes model --refresh``.

#### def `copilot_default_headers(is_agent_turn: bool = True) -> dict[str, str]`

Standard headers for Copilot API requests.

Includes Openai-Intent and x-initiator headers that opencode and the
Copilot CLI send on every request.

#### def `fetch_github_model_catalog(api_key: Optional[str] = None, timeout: float = 5.0) -> Optional[list[dict[str, Any]]]`

Fetch the live GitHub Copilot model catalog for this account.

#### def `get_copilot_model_context(model_id: str, api_key: Optional[str] = None) -> Optional[int]`

Look up max_prompt_tokens for a Copilot model from the live /models API.

Results are cached in-process for 1 hour to avoid repeated API calls.
Returns the token limit or None if not found.

#### def `probe_lmstudio_models(api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 5.0) -> Optional[list[str]]`

Probe LM Studio's model listing.

Returns chat-capable model keys on success, including the valid empty-list
case when the server is reachable but has no non-embedding models.
Returns ``None`` on network errors, malformed responses, or empty/invalid
base URLs.

Raises ``AuthError`` on HTTP 401/403 so callers can surface token issues
separately from reachability problems.

#### def `fetch_lmstudio_models(api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 5.0) -> list[str]`

Fetch LM Studio chat-capable model keys from native ``/api/v1/models``.

Returns a list of model keys (e.g. ``publisher/model-name``) with embedding
models filtered out. Returns an empty list on network errors, malformed
responses, or empty/invalid base URLs.

Raises ``AuthError`` on HTTP 401/403 so callers can distinguish a missing
or wrong ``LM_API_KEY`` from an unreachable server — the most common
LM Studio support case once auth-enabled mode is turned on.

#### def `ensure_lmstudio_model_loaded(model: str, base_url: Optional[str], api_key: Optional[str], target_context_length: int, timeout: float = 120.0) -> Optional[int]`

Ensure LM Studio has ``model`` loaded with at least ``target_context_length``.

No-op when an instance is already loaded with sufficient context. Otherwise
POSTs ``/api/v1/models/load`` to (re)load with the target context, capped
at the model's ``max_context_length``. Returns the resolved loaded context
length, or ``None`` when the probe / load failed.

#### def `lmstudio_model_reasoning_options(model: str, base_url: Optional[str], api_key: Optional[str] = None, timeout: float = 5.0) -> list[str]`

Return the reasoning ``allowed_options`` LM Studio publishes for ``model``.

Pulls ``capabilities.reasoning.allowed_options`` from ``/api/v1/models``.
Returns ``[]`` when the model is unknown, the endpoint is unreachable,
or the model does not declare a reasoning capability.

#### def `ollama_model_supports_thinking(model: str, base_url: Optional[str], api_key: Optional[str] = None, timeout: float = 5.0) -> Optional[bool]`

Return True if an Ollama (Cloud or local) model advertises ``thinking``.

Probes the native ``/api/show`` endpoint and checks the ``capabilities``
list, which Ollama populates from the model's metadata (e.g.
``deepseek-v4-pro`` → ``["completion", "tools", "thinking"]`` while
``gemma3:27b`` → ``["completion", "vision"]``). This is the authoritative
capability source — the OpenAI-compat ``/v1/models`` endpoint omits it.

Returns:
    True  — the model declares the ``thinking`` capability.
    False — ``/api/show`` succeeded but the model has no ``thinking`` cap.
    None  — the probe failed (unreachable / non-Ollama / error); the caller
            decides the fallback (we treat None as "don't emit").

#### def `normalize_copilot_model_id(model_id: Optional[str], catalog: Optional[list[dict[str, Any]]] = None, api_key: Optional[str] = None) -> str`

#### def `copilot_model_api_mode(model_id: Optional[str], catalog: Optional[list[dict[str, Any]]] = None, api_key: Optional[str] = None) -> str`

Determine the API mode for a Copilot model.

Uses the model ID pattern (matching opencode's approach) as the
primary signal.  Falls back to the catalog's ``supported_endpoints``
only for models not covered by the pattern check.

#### def `azure_foundry_model_api_mode(model_name: Optional[str]) -> Optional[str]`

Infer Azure Foundry api_mode from a deployment/model name.

Returns ``"codex_responses"`` when the model name matches a family that
only accepts the Responses API on Azure Foundry (GPT-5.x, codex, o1/o3/o4
reasoning models).  Returns ``None`` otherwise — the caller should fall
back to the configured/default api_mode (typically ``chat_completions``)
so GPT-4o, GPT-4 Turbo, Llama, Mistral, etc. keep working.

Intentionally does NOT return ``anthropic_messages``; Anthropic-style
Azure endpoints are disambiguated by URL (``/anthropic`` suffix) in
``runtime_provider._detect_api_mode_for_url`` and by the user setting
``model.api_mode: anthropic_messages`` explicitly.

#### def `normalize_opencode_model_id(provider_id: Optional[str], model_id: Optional[str]) -> str`

Normalize OpenCode config IDs to the bare model slug used in API requests.

#### def `opencode_model_api_mode(provider_id: Optional[str], model_id: Optional[str]) -> str`

Determine the API mode for an OpenCode Zen / Go model.

OpenCode routes different models behind different API surfaces:

- GPT-5 / Codex models on Zen use ``/v1/responses``
- Claude models on Zen use ``/v1/messages``
- MiniMax and Qwen models on Go use ``/v1/messages``
- GLM / Kimi / DeepSeek / MiMo on Go use ``/v1/chat/completions``
- Qwen models on Zen use ``/v1/messages``
- Other Zen models (Gemini, GLM, Kimi, MiniMax, DeepSeek, etc.) use
  ``/v1/chat/completions``

This follows the published OpenCode docs for Zen and Go endpoints
(https://opencode.ai/docs/zen/ and https://opencode.ai/docs/go/).

#### def `normalize_opencode_base_url(provider_id: Optional[str], api_mode: Optional[str], base_url: Optional[str]) -> str`

Normalize an OpenCode Zen / Go base URL for the target API mode.

OpenCode's OpenAI-compatible endpoints live under ``/v1`` (the OpenAI SDK
appends ``/chat/completions`` or ``/responses``), while the Anthropic SDK
appends its own ``/v1/messages`` — so anthropic_messages needs the ``/v1``
suffix stripped.

Crucially this must be SYMMETRIC.  The stripped URL gets persisted to
config (``model.base_url``) by the TUI/desktop and gateway after switching
into an anthropic-routed model (e.g. minimax-m2.7 on Go).  A later switch
to a chat_completions model (glm, deepseek, kimi) then inherited the
stripped URL and POSTed to ``https://opencode.ai/zen/go/chat/completions``
— a 404 (the marketing site).  Re-append ``/v1`` for non-anthropic modes
so previously-stripped URLs heal themselves.

Only opencode.ai-hosted URLs are re-suffixed; custom proxy overrides via
``OPENCODE_*_BASE_URL`` are left alone unless they already carry ``/v1``.

#### def `github_model_reasoning_efforts(model_id: Optional[str], catalog: Optional[list[dict[str, Any]]] = None, api_key: Optional[str] = None) -> list[str]`

Return supported reasoning-effort levels for a Copilot-visible model.

#### def `probe_api_models(api_key: Optional[str], base_url: Optional[str], timeout: float = 5.0, api_mode: Optional[str] = None, request_headers: Optional[dict[str, str]] = None) -> dict[str, Any]`

Probe a ``/models`` endpoint with light URL heuristics.

For ``anthropic_messages`` mode, uses ``x-api-key`` and
``anthropic-version`` headers (Anthropic's native auth) instead of
``Authorization: Bearer``.  The response shape (``data[].id``) is
identical, so the same parser works for both.

#### def `deepinfra_model_ids(tag: str, force_refresh: bool = False) -> list[str]`

Return DeepInfra model ids carrying surface *tag* (``[]`` on failure).

Single source of truth for the per-surface model shims (TTS/STT/vision),
replacing the copy-pasted ``import _fetch_deepinfra_models_by_tag → fetch
→ [item["id"] …]`` wrapper each of them used to carry.

#### def `deepinfra_base_url(section: Optional[dict] = None) -> str`

Resolve the DeepInfra OpenAI-compatible base URL, normalized.

Precedence: config-section ``base_url`` → ``DEEPINFRA_BASE_URL`` env →
default. Always stripped with any trailing slash removed. Single source
of truth for the base-URL chain the TTS/STT/image/video shims each used
to re-code (with subtly divergent normalization).

#### def `fetch_api_models(api_key: Optional[str], base_url: Optional[str], timeout: float = 5.0, api_mode: Optional[str] = None, headers: Optional[dict[str, str]] = None) -> Optional[list[str]]`

Fetch the list of available model IDs from the provider's ``/models`` endpoint.

Returns a list of model ID strings, or ``None`` if the endpoint could not
be reached (network error, timeout, auth failure, etc.).

#### def `fetch_ollama_cloud_models(api_key: Optional[str] = None, base_url: Optional[str] = None, force_refresh: bool = False) -> list[str]`

Fetch Ollama Cloud models by merging live API + models.dev, with disk cache.

Resolution order:
  1. Disk cache (if fresh, < 1 hour, and not force_refresh)
  2. Live ``/v1/models`` endpoint (primary — freshest source)
  3. models.dev registry (secondary — fills gaps for unlisted models)
  4. Merge: live models first, then models.dev additions (deduped)

Returns a list of model IDs (never None — empty list on total failure).

#### def `validate_requested_model(model_name: str, provider: Optional[str], api_key: Optional[str] = None, base_url: Optional[str] = None, api_mode: Optional[str] = None) -> dict[str, Any]`

Validate a ``/model`` value for the active provider.

Performs format checks first, then probes the live API to confirm
the model actually exists.

Returns a dict with:
  - accepted: whether the CLI should switch to the requested model now
  - persist: whether it is safe to save to config
  - recognized: whether it matched a known provider catalog
  - message: optional warning / guidance for the user


## hermes_cli.nous_account

### 模块文档

Normalized Nous Portal account entitlement helpers.

### class NousPortalSubscriptionInfo

> 继承: `object` ｜ 方法数: 0（公开 0）


### class NousPaidServiceAccessInfo

> 继承: `object` ｜ 方法数: 0（公开 0）


### class NousToolAccessInfo

> 继承: `object` ｜ 方法数: 0（公开 0）

Free tool-pool entitlement, decoupled from paid/billing access.

Mirrors the Portal's ``tool_access`` claim/field: ``enabled`` is true when a
positive tool-pool balance is live and not gated off; ``coverage`` maps each
tool category to whether the pool funds it (FAL video is excluded).


### class NousPortalAccountInfo

> 继承: `object` ｜ 方法数: 4（公开 4）

#### property `is_paid(self) -> bool`

#### property `is_free_tier(self) -> bool`

#### property `tool_gateway_entitled(self) -> bool`

Coarse "entitled to any managed tool" gate: paid access OR a live
free tool pool. Use :meth:`tool_gateway_entitled_for` to gate a specific
tool category (the pool does not cover every category).

#### def `tool_gateway_entitled_for(self, category: str) -> bool`

Whether a specific tool category is entitled. Paid users are entitled
everywhere; free tool-pool users only where ``coverage[category]`` is
true (e.g. image but not video).


### 顶层函数

#### def `nous_portal_billing_url(account_info: Optional[NousPortalAccountInfo] = None) -> str`

Return the billing URL for a normalized Nous account snapshot.

#### def `nous_portal_topup_url(account_info: Optional[NousPortalAccountInfo] = None) -> str`

Return the portal top-up URL that auto-opens the top-up modal.

Prefers the org-pinned page ``{base}/orgs/{slug}/billing?topup=open`` (skips
the legacy shim's re-resolution + multi-org disambiguation). Falls back to the
legacy ``{base}/billing?topup=open`` when the account has no ``org_slug`` (the
portal's ``slug`` is nullable; the legacy page forwards the param through to
the org-pinned page). Never builds ``/orgs/None/billing``.

The ``?topup=open`` query is the NAS enabler that lands the user in the
top-up flow rather than just on the billing page.

#### def `format_nous_portal_entitlement_message(account_info: Optional[NousPortalAccountInfo], capability: str = 'this feature', include_refresh_hint: bool = True, coverage_category: Optional[str] = None) -> Optional[str]`

Return user-facing guidance for a missing Nous tool-gateway entitlement.

``None`` means the account is entitled to use the capability — via paid
service access OR a live free tool pool that covers it. The message works
from normalized entitlement fields rather than subscription price alone:
purchased credits without a subscription still count as paid access, while a
paid subscription with exhausted usable credits does not.

``coverage_category`` scopes the check to a single tool category (e.g.
``"fal-video"``). When given, a user who is entitled overall but whose
access does not fund that category gets a neutral billing nudge instead of a
message implying their credits are exhausted. The pool-vs-paid distinction is
never surfaced to the user.

#### def `reset_nous_portal_account_info_cache() -> None`

Clear the short-lived account-info cache used by tests.

#### def `get_nous_portal_account_info(force_fresh: bool = False, min_jwt_ttl_seconds: int = 60) -> NousPortalAccountInfo`

Return normalized Nous Portal account entitlement information.

By default, a valid unexpired OAuth access JWT is used as a low-latency
local account snapshot. ``force_fresh=True`` always calls
``/api/oauth/account`` and bypasses the short-lived cache. JWT claims are
decoded locally for UX gating only; server APIs remain authoritative.


## hermes_cli.nous_auth_keepalive

### 模块文档

Background keepalive for long-lived Nous Portal sessions.

### 顶层函数

#### def `refresh_nous_auth_keepalive_once(min_key_ttl_seconds: int = NOUS_INVOKE_JWT_MIN_TTL_SECONDS, timeout_seconds: Optional[float] = None) -> bool`

Refresh Nous auth once if credentials are configured.

#### def `start_nous_auth_keepalive(interval_seconds: int = NOUS_AUTH_KEEPALIVE_INTERVAL_SECONDS, initial_delay_seconds: int = NOUS_AUTH_KEEPALIVE_INITIAL_DELAY_SECONDS, min_key_ttl_seconds: int = NOUS_INVOKE_JWT_MIN_TTL_SECONDS, timeout_seconds: Optional[float] = None) -> Optional[threading.Thread]`

Start the process-wide Nous auth keepalive thread.

#### def `stop_nous_auth_keepalive(timeout: float = 5.0) -> None`

Stop the keepalive thread. Intended for graceful shutdown/tests.


## hermes_cli.nous_billing

### 模块文档

Nous Portal terminal-billing HTTP client (Phase 2b).

Thin, fail-loud client for the four ``/api/billing/*`` endpoints the terminal
billing screens drive. Companion to ``hermes_cli/nous_account.py`` (which owns
read-only entitlement/balance) — this module owns the *write* side: buy credits,
poll a charge, configure auto-reload.

Design rules:

- **Money is decimal, never float.** The server emits decimal STRINGS
  (``"142.5"`` — not fixed 2dp). We parse with :class:`decimal.Decimal` and never
  round-trip through float.
- **This client raises typed exceptions; it does NOT fail open.** Fail-open is the
  *caller's* job (the ``agent/billing_view.py`` builders) so each surface can
  decide how to degrade. A raw network/HTTP error here surfaces as
  :class:`BillingError` (or a subclass) carrying the parsed server ``error`` code,
  HTTP status, ``portalUrl`` deep-link, and ``retry_after``.
- **Auth** = the OAuth bearer JWT Hermes already holds for inference
  (``get_provider_auth_state("nous")["access_token"]``). No API-key auth on these.
- **Portal base URL** resolves with the same precedence as the device-flow login
  (``auth.py``): ``HERMES_PORTAL_BASE_URL`` → ``NOUS_PORTAL_BASE_URL`` → the
  stored auth-state ``portal_base_url`` → the registry default. This is how the
  E2E run points the client at a preview deployment with zero code change.

### class BillingError

> 继承: `Exception` ｜ 方法数: 1（公开 0）

A billing HTTP call failed.

Carries everything a surface needs to render the right message + affordance:
the server ``error`` code, HTTP ``status``, an optional human ``message``, the
``portalUrl`` deep-link (present on every gate denial), and ``retry_after``
seconds (429/503). ``payload`` is the full parsed JSON body when available.

#### def `__init__(message: str, status: Optional[int] = None, error: Optional[str] = None, portal_url: Optional[str] = None, retry_after: Optional[int] = None, payload: Optional[dict[str, Any]] = None, actor: Optional[str] = None, code: Optional[str] = None, recovery: Optional[str] = None) -> None`


### class BillingScopeRequired

> 继承: `BillingError` ｜ 方法数: 0（公开 0）

``403 insufficient_scope`` — the held token lacks ``billing:manage``.

The lazy step-up trigger: catching this kicks off a fresh device-connect that
requests ``billing:manage`` (and tells the user an ADMIN must tick "Allow
terminal billing"). Also fires mid-session if the scope is stripped on refresh
after the user loses ADMIN.


### class BillingAuthError

> 继承: `BillingError` ｜ 方法数: 0（公开 0）

``401`` — missing/invalid bearer token (not logged in / expired).


### class BillingRemoteSpendingRevoked

> 继承: `BillingError` ｜ 方法数: 0（公开 0）

``403 remote_spending_revoked`` — THIS terminal's spending was revoked.

Distinct from ``insufficient_scope`` (never had the grant) and from
``session_revoked`` (full logout). The terminal stays logged in; only the
money path is cut. ``actor`` is ``"admin"`` or ``"self"`` (absent → treat as
``"self"``); recovery is **reconnect** (re-consent device-auth). The terminal
MUST disable charge/auto-reload immediately, without waiting for the next
token refresh (the current token still claims the scope for ~15 min).


### class BillingSessionRevoked

> 继承: `BillingAuthError` ｜ 方法数: 0（公开 0）

``401 session_revoked`` — the whole session was logged out.

Stronger than a spend-revoke: recovery is **re-login** (full device-auth),
not just reconnect. Subclass of :class:`BillingAuthError` so existing 401
handling still treats it as not-logged-in, but the typed code lets the
surface route to re-login with the right copy.


### class BillingTransient

> 继承: `BillingError` ｜ 方法数: 0（公开 0）

A deterministic non-charge outcome: the request definitely did NOT
reach/complete at Stripe, so it's always safe to retry after backoff —
never the "maybe charged" ambiguity of a real 5xx/timeout. Covers
429 rate limiting, 503 gate-unavailable, Stripe being down, and the
daily upgrade cap — distinct failure modes that share this one
contract property. Catch this (not the old ad-hoc subclass hierarchy)
wherever the intent is "any transient, definitely-not-charged billing
failure, back off and retry/poll".


### class BillingRateLimited

> 继承: `BillingTransient` ｜ 方法数: 0（公开 0）

``429 rate_limited`` or ``503 temporarily_unavailable``.

NOT a payment failure. Carries ``retry_after`` (seconds) — back off and tell
the user "try again in N min"; never auto-retry-spam (the limiter is
5/org/hr + 5/token/hr and easy to dig deeper into). A 503 is the gate backend
failing closed — back off, do NOT treat as revoked.


### class BillingStripeUnavailable

> 继承: `BillingTransient` ｜ 方法数: 0（公开 0）

``503 stripe_unavailable`` — Stripe itself is down.

TRANSIENT: back off and retry using Retry-After; this is NOT the same as
being throttled by our own rate limiter, so surfaces must not render "rate
limited" copy for it — they should read ``.error`` to tell the two apart.
A BillingTransient sibling of BillingRateLimited (not a subclass) — surfaces
must not render "rate limited" copy for it; read ``.error`` to distinguish it.


### class BillingUpgradeCapExceeded

> 继承: `BillingTransient` ｜ 方法数: 0（公开 0）

``429 upgrade_cap_exceeded`` — the org hit its 5-upgrades/day cap.

Distinct from the hourly ``rate_limited`` charge cap (same HTTP status,
different meaning + no useful short-Retry-After backoff). A BillingTransient
sibling of BillingRateLimited (not a subclass) — surfaces must read ``.error``
to distinguish the failure mode.


### 顶层函数

#### def `resolve_portal_base_url(state: Optional[dict[str, Any]] = None) -> str`

Resolve the portal base URL with login-time precedence.

``HERMES_PORTAL_BASE_URL`` → ``NOUS_PORTAL_BASE_URL`` → stored auth-state
``portal_base_url`` → registry default. Trailing slash stripped.

#### def `invalidate_cached_token() -> None`

Bust the 30s token cache so post-step-up replays use the freshly-scoped token.

``_request`` only self-busts the cache on a 401 (an expired/invalid
token), not on a 403 scope denial — so after a step-up grant, the
cache would otherwise still hold the pre-grant unscoped token and
the immediate replay would 403 again. Callers outside this module
(e.g. the CLI's scope step-up flow) call this instead of poking
the private ``_token_cache`` global directly.

#### def `get_billing_state(timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``GET /api/billing/state`` — role-tiered overview (no scope required).

#### def `patch_auto_top_up(enabled: bool, threshold: float | str, top_up_amount: float | str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``PATCH /api/billing/auto-top-up`` — configure auto-reload (scope required).

Body is strict server-side: extra keys (``maxMonthlySpend``, a payment method)
are rejected with 400. Numbers are sent as JSON numbers per the contract.

#### def `post_charge(amount_usd: float | str, idempotency_key: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``POST /api/billing/charge`` — buy credits (scope required).

``Idempotency-Key`` header is MANDATORY (a missing header is a server 400, not
a default): generate a UUID per user-confirmed purchase and reuse it on retry.
Returns ``202 {chargeId}`` — money is NOT confirmed yet; poll with
:func:`get_charge_status`.

**异常**: `BillingError`

#### def `get_charge_status(charge_id: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``GET /api/billing/charge/{id}`` — poll a charge (scope required).

Returns ``{status: "pending"|"settled"|"failed", ...}``. An unknown or foreign
id returns ``{status:"pending"}`` (never 404, never another org's data) — so a
``pending`` that never resolves past the 5-min cap is a *timeout*, not an error.

**异常**: `BillingError`

#### def `get_subscription_state(timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``GET /api/billing/subscription`` — current plan, tiers, usage (no scope).

Returns the raw JSON dict from NAS (WS1 Phase A). Read-only — no
``billing:manage`` scope required. Raises :class:`BillingAuthError`
on 401 and :class:`BillingError` on other non-2xx.

**异常**: `class`

#### def `post_subscription_preview(subscription_type_id: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``POST /api/billing/subscription/preview`` — a chargeless effect quote.

Quotes a change to ``subscription_type_id`` without mutating anything:
``effect`` is ``charge_now`` (an upgrade → ``amountDueNowCents`` is the prorated
upfront charge), ``scheduled`` (a downgrade → ``effectiveAt`` is period end),
``no_op`` (already on the tier), or ``blocked`` (``reason`` says why the commit
would be refused). Also returns the current + target tier and the monthly-credit
delta. ``amountDueNowCents`` is ``None`` when not a charge or when the proration
quote is unavailable. Requires ``billing:manage`` (live Stripe calls + amounts).

#### def `put_subscription_pending_change(subscription_type_id: str | None = None, cancel: bool = False, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``PUT /api/billing/subscription/pending-change`` — set the end-of-period intent.

A subscription has at most one pending disposition. Pass ``cancel=True`` to
schedule a cancellation, or a ``subscription_type_id`` to schedule a downgrade /
same-price change. UPGRADES are rejected here (they charge immediately — use
:func:`post_subscription_upgrade`). Chargeless; requires ``billing:manage``.
Returns ``{rail, changeType, targetTierName, message}`` for a tier change, or
``{rail, cancelAtPeriodEnd, message}`` for a cancellation.

**异常**: `BillingError`

#### def `delete_subscription_pending_change(timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``DELETE /api/billing/subscription/pending-change`` — clear it (resume / undo).

Removes a scheduled downgrade OR cancellation in one call, restoring the live
active tier and recurring renewal. Chargeless, but it re-enables recurring
spend, so it requires ``billing:manage`` and is honored by the org kill-switch.
Returns ``{rail, cancelAtPeriodEnd: false, message}``.

#### def `post_subscription_upgrade(subscription_type_id: str, idempotency_key: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]`

``POST /api/billing/subscription/upgrade`` — immediate paid upgrade.

The SINGLE money route: one Stripe op prorates, charges the card already on the
subscription, and flips the plan. ``Idempotency-Key`` is MANDATORY (a missing
header is a server 400, not a default) — reuse the same key on retry so a replay
cannot double-charge. Returns ``{status:"upgraded"|"already_on_tier", ...}`` on
success, or ``{status:"requires_action"|"payment_failed", reason, recoveryUrl}``
when the charge needs 3DS / was declined and must be finished in the portal at
``recoveryUrl``. Requires ``billing:manage``.

**异常**: `BillingError`


## hermes_cli.nous_subscription

### 模块文档

Helpers for Nous subscription managed-tool capabilities.

### class NousFeatureState

> 继承: `object` ｜ 方法数: 0（公开 0）


### class NousSubscriptionFeatures

> 继承: `object` ｜ 方法数: 8（公开 8）

#### property `web(self) -> NousFeatureState`

#### property `image_gen(self) -> NousFeatureState`

#### property `tts(self) -> NousFeatureState`

#### property `stt(self) -> NousFeatureState`

#### property `browser(self) -> NousFeatureState`

#### property `video_gen(self) -> NousFeatureState`

#### property `modal(self) -> NousFeatureState`

#### def `items(self) -> Iterable[NousFeatureState]`


### 顶层函数

#### def `get_nous_subscription_features(config: Optional[Dict[str, object]] = None, force_fresh: bool = False) -> NousSubscriptionFeatures`

#### def `apply_nous_managed_defaults(config: Dict[str, object], enabled_toolsets: Optional[Iterable[str]] = None, force_fresh: bool = False) -> set[str]`

#### def `get_gateway_eligible_tools(config: Optional[Dict[str, object]] = None, force_fresh: bool = False) -> tuple[list[str], list[str], list[str]]`

Return (unconfigured, has_direct, already_managed) tool key lists.

- unconfigured: tools with no direct credentials (easy switch)
- has_direct: tools where the user has their own API keys
- already_managed: tools already routed through the gateway

All lists are empty when the user is not a paid Nous subscriber or
is not using Nous as their provider.

#### def `apply_gateway_defaults(config: Dict[str, object], tool_keys: list[str]) -> set[str]`

Apply Tool Gateway config for the given tool keys.

Sets ``use_gateway: true`` in each tool's config section so the
runtime prefers the gateway even when direct API keys are present.

Returns the set of tools that were actually changed.

#### def `prompt_enable_tool_gateway(config: Dict[str, object], force_fresh: bool = True) -> set[str]`

If eligible tools exist, prompt the user (per tool) to enable the Tool
Gateway.

"Pool enabled" is the trigger: a user with a live free tool pool (or paid
access) is shown a per-tool checklist of the covered managed backends and
picks which to route through the gateway. The free pool funds web/image/
tts/browser but not video, so the checklist only lists covered tools (the
coverage filter lives in get_gateway_eligible_tools).

Returns the set of tools that were enabled, or empty set if the user
declined or no tools were eligible.

#### def `ensure_nous_portal_access(capability: str = 'the Nous Tool Gateway', coverage_category: Optional[str] = None) -> bool`

Make sure the user is entitled to the Nous Tool Gateway, logging in if
needed.

Used by ``hermes tools`` when a user selects a Nous-managed Tool Gateway
backend (e.g. "Firecrawl (Nous Portal)").  Unlike ``hermes model``'s Nous
login, this:

- does NOT change the inference provider (``model.provider`` is untouched),
- does NOT run model selection, and
- does NOT offer the bulk "enable for all tools" Tool Gateway prompt.

It only performs the Nous Portal device-code OAuth (when the user isn't
already logged in) and refreshes entitlement, so the caller can enable the
single tool the user picked.

Entitlement is satisfied by paid service access OR a live free tool pool.
When ``coverage_category`` is given (e.g. ``"fal"`` for image gen), the pool
must cover that category specifically — so a pool user selecting video
(``"fal-video"``, not pool-funded) is correctly denied.

Returns ``True`` when the account is entitled after the flow, ``False``
otherwise (declined login, login failed, or no entitlement).


## hermes_cli.onepassword_secrets_cli

### 模块文档

CLI handlers for ``hermes secrets onepassword ...``.

Subcommands:
    setup    — verify the op CLI, set account / token env var, enable
    status   — show config + op binary + auth + configured references
    set      — map an env var to an ``op://…`` reference
    remove   — drop a mapping
    sync     — resolve references now and show what would be applied (dry-run)
    disable  — flip ``secrets.onepassword.enabled`` to False

Unlike Bitwarden, the ``op`` binary is NOT auto-installed: 1Password publishes
the CLI through OS package managers and signed installers, so Hermes expects
an already-installed, already-authenticated ``op`` and never downloads one.

### 顶层函数

#### def `register_cli(parent_parser: argparse.ArgumentParser) -> None`

Attach the ``onepassword`` subcommand tree to a parent parser.

#### def `cmd_setup(args: argparse.Namespace) -> int`

#### def `cmd_status(args: argparse.Namespace) -> int`

#### def `cmd_set(args: argparse.Namespace) -> int`

#### def `cmd_remove(args: argparse.Namespace) -> int`

#### def `cmd_sync(args: argparse.Namespace) -> int`

#### def `cmd_disable(args: argparse.Namespace) -> int`


## hermes_cli.oneshot

### 模块文档

Oneshot (-z) mode: send a prompt, get the final content block, exit.

Bypasses cli.py entirely.  No banner, no spinner, no session_id line,
no stderr chatter.  Just the agent's final text to stdout.

Toolsets = explicit --toolsets when provided, otherwise whatever the user has
configured for "cli" in `hermes tools`.
Rules / memory / AGENTS.md / preloaded skills = same as a normal chat turn.
Approvals = auto-bypassed (HERMES_YOLO_MODE=1 is set for the call).
Working directory = the user's CWD (AGENTS.md etc. resolve from there as usual).

Model / provider selection mirrors `hermes chat`:
    - Both optional. If omitted, use the user's configured default.
    - If both given, pair them exactly as given.
    - If only --model given, auto-detect the provider that serves it.
    - If only --provider given, error out (ambiguous — caller must pick a model).

Env var fallbacks (used when the corresponding arg is not passed):
    - HERMES_INFERENCE_MODEL

### 顶层函数

#### def `run_oneshot(prompt: str, model: Optional[str] = None, provider: Optional[str] = None, toolsets: object = None, usage_file: Optional[str] = None) -> int`

Execute a single prompt and print only the final content block.

Args:
    prompt: The user message to send.
    model: Optional model override. Falls back to HERMES_INFERENCE_MODEL
        env var, then config.yaml's model.default / model.model.
    provider: Optional provider override. Falls back to config.yaml's
        model.provider, then "auto".
    toolsets: Optional comma-separated string or iterable of toolsets.
    usage_file: Optional path; when set, a JSON usage report (estimated
        cost, token counts, model, api_calls) is written there after the
        run — even when the run fails — so pipelines can account for
        spend per invocation.

Returns the exit code.  The caller owns process termination.

**异常**: `failure`


## hermes_cli.pairing

### 模块文档

CLI commands for the DM pairing system.

Usage:
    hermes pairing list              # Show all pending + approved users
    hermes pairing approve <platform> <code>  # Approve a pairing code
    hermes pairing revoke <platform> <user_id> # Revoke user access
    hermes pairing clear-pending     # Clear all expired/pending codes

### 顶层函数

#### def `pairing_command(args)`

Handle hermes pairing subcommands.


## hermes_cli.partial_compress

### 模块文档

Boundary-aware partial compression — "summarize up to here".

Inspired by Claude Code's Rewind menu "Summarize up to here" action
(v2.1.139–v2.1.142, Week 20, May 2026):
https://code.claude.com/docs/en/whats-new/2026-w20

Hermes already has ``/compress`` (full-history compaction) and an
automatic token-budget tail-protection heuristic inside
``ContextCompressor``. What was missing is *user-chosen* boundary
control: "fold everything before this point into a summary, but keep
my most recent N exchanges exactly as they are." That is the value of
the Claude Code feature — the user decides the compression boundary
instead of leaving it to the token-budget heuristic.

This module owns the pure, side-effect-free split logic so both the
CLI (``cli.py::_manual_compress``) and the gateway
(``gateway/run.py::_handle_compress_command``) share one
implementation. The slash-command surfaces handle compression of the
*head* via the existing ``_compress_context`` pipeline (preserving all
the session-rotation / lock / memory-notify machinery) and then
re-append the verbatim *tail* returned here.

Design notes / invariants honored:

* **Role alternation.** The compressed head ends with summary/handoff
  content (assistant- or user-role, possibly a trailing todo snapshot).
  The verbatim tail must begin with a ``user`` message so the rejoined
  history keeps the user↔assistant alternation that providers validate.
  :func:`split_history_for_partial_compress` snaps the tail boundary
  backwards to the nearest ``user`` turn so the rejoin is always legal.

* **No silent context mutation.** This is a manual, user-invoked
  action. It rotates the session exactly like ``/compress`` does (via
  the caller), so the prompt-cache reset is explicit and expected, not
  silent.

* **Conservative defaults.** ``keep_last`` counts *exchanges* (a user
  turn plus its following assistant/tool turns), defaulting to 2. The
  split never compresses if doing so would leave nothing in the head.

### 顶层函数

#### def `parse_partial_compress_args(raw_args: str) -> Tuple[bool, int, Optional[str]]`

Parse the argument string after ``/compress``.

Recognizes the boundary-aware forms:

* ``here``            → partial compress, keep ``DEFAULT_KEEP_LAST``
* ``here 4``          → partial compress, keep 4 exchanges
* ``--keep 4``        → partial compress, keep 4 exchanges
* ``up to here``      → alias for ``here`` (matches Claude Code's
                        menu label "Summarize up to here")

Anything else is treated as a focus topic for the existing full
``/compress <focus>`` behavior.

Returns ``(partial, keep_last, focus_topic)``:

* ``partial`` — True when a boundary-aware form was requested.
* ``keep_last`` — exchanges to preserve verbatim (only meaningful
  when ``partial`` is True).
* ``focus_topic`` — focus string for full compression, or None.
  Always None when ``partial`` is True (the two modes are exclusive;
  a focused partial compress is not a documented Claude Code
  behavior and would muddy the UX).

#### def `extract_compress_flags(raw_args: str) -> Tuple[str, bool, bool]`

Strip ``--preview``/``--dry-run``/``--aggressive`` flags from the
argument string after ``/compress`` (or its ``/compact`` alias).

Flags may appear anywhere and coexist with the positional forms
(``here [N]``, ``--keep N``, or a focus topic); the returned
remainder is what :func:`parse_partial_compress_args` should see.

Returns ``(remaining_args, preview, aggressive_requested)``:

* ``preview`` — True when ``--preview`` or ``--dry-run`` was given.
  The caller must report what WOULD be compressed (message counts,
  token estimate, boundary) and make **no changes**.
* ``aggressive_requested`` — True when ``--aggressive`` was given.
  The current surfaces do not implement an LLM-free hard-truncate
  path (it would need its own transcript-persistence branch outside
  the guarded ``_compress_context`` rotation machinery), so callers
  surface a "not supported" note instead of silently treating the
  flag as a focus topic.

#### def `summarize_compress_preview(history: List[Dict[str, Any]], partial: bool, keep_last: int, focus_topic: Optional[str], approx_tokens: int) -> Dict[str, Any]`

Build the ``/compress --preview`` report — pure, no side effects.

Shared by the CLI (``cli.py::_manual_compress``) and the gateway
(``gateway/slash_commands.py::_handle_compress_command``) so both
surfaces report the same numbers the real run would use.

Returns a dict with ``head_count``/``tail_count``/``lines`` where
``lines`` is a ready-to-print list of report strings.

#### def `split_history_for_partial_compress(history: List[Dict[str, Any]], keep_last: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]`

Split ``history`` into ``(head, tail)`` for partial compression.

``head`` is the earlier portion that will be summarized; ``tail`` is
the most recent ``keep_last`` exchanges, preserved verbatim.

An *exchange* is counted by ``user``-role messages: keeping N
exchanges means keeping everything from the Nth-most-recent ``user``
message onward. This guarantees the tail starts on a ``user`` turn,
so when the caller rejoins ``compressed_head + tail`` the
user↔assistant alternation stays valid (the compressed head's
trailing content is followed by a fresh user turn).

Returns ``(head, tail)``. If the split would leave the head empty
(not enough history to compress meaningfully), returns
``(history, [])`` — signaling the caller to fall back to full
compression or report "nothing to do".

#### def `rejoin_compressed_head_and_tail(compressed_head: List[Dict[str, Any]], tail: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Concatenate a compressed head with the verbatim tail, defending
the seam against an illegal user→user / assistant→assistant adjacency.

In normal operation the compressed head ends with the head's own
protected verbatim tail (the ``ContextCompressor`` always preserves a
recent window), which terminates on an ``assistant``/``tool`` turn —
so ``assistant → user`` at the seam is already valid. But the head
compressor's exact output shape is not contractually guaranteed (a
plugin context engine could return something that ends on a ``user``
turn, or a degenerate single-summary message). Rather than trust the
seam, this helper inspects the boundary and, if the last head message
and the first tail message share a ``user``/``assistant`` role, folds
the tail's first message content onto the head's last message so the
rejoined list never violates provider role-alternation rules.

``tool`` messages are left alone — consecutive ``tool`` entries are
the one legal repetition (parallel tool results).


## hermes_cli.pets

### 模块文档

CLI subcommand: ``hermes pets <subcommand>``.

Thin shell around :mod:`agent.pet`.  Browses the public petdex gallery,
installs pets into the profile's ``pets/`` directory, selects the active
mascot (writes ``display.pet.*`` to config.yaml), and runs a doctor check.

No side effects at import time — ``main.py`` wires the argparse subparsers on
demand via :func:`register_cli`.

### 顶层函数

#### def `set_pet_scale(value: float | str) -> tuple[float, str | None]`

Set ``display.pet.scale`` (clamped to bounds). Returns ``(applied, error)``.

The single write path behind ``/pet scale`` and the desktop slider, so every
surface that resolves scale from config picks it up identically. *error* is
set (and nothing written) only when *value* isn't a number.

#### def `toggle_pet_display() -> tuple[bool, str | None, str | None]`

Toggle ``display.pet.enabled``.

Returns ``(enabled, display_name, error_message)``. *error_message* is set
when turning on but nothing is installed to show.

#### def `print_pet_gallery(limit: int = 20) -> None`

Print a slice of the public petdex gallery (CLI/TUI text fallback).

#### def `register_cli(parent: argparse.ArgumentParser) -> None`

Attach ``pets`` subcommands to *parent* (called by main.py).


## hermes_cli.platforms

### 模块文档

Shared platform registry for Hermes Agent.

Single source of truth for platform metadata consumed by both
skills_config (label display) and tools_config (default toolset
resolution).  Import ``PLATFORMS`` from here instead of maintaining
duplicate dicts in each module.

### class PlatformInfo

> 继承: `NamedTuple` ｜ 方法数: 0（公开 0）

Metadata for a single platform entry.


### 顶层函数

#### def `platform_label(key: str, default: str = '') -> str`

Return the display label for a platform key, or *default*.

Checks the static PLATFORMS dict first, then the plugin platform
registry for dynamically registered platforms.

#### def `get_all_platforms() -> OrderedDict[str, PlatformInfo]`

Return PLATFORMS merged with any plugin-registered platforms.

Plugin platforms are appended after builtins.  This is the function
that tools_config and skills_config should use for platform menus.


## hermes_cli.plugins

### 模块文档

Hermes Plugin System
====================

Discovers, loads, and manages plugins from four sources:

1. **Bundled plugins** – ``<repo>/plugins/<name>/`` (shipped with hermes-agent;
   ``memory/`` and ``context_engine/`` subdirs are excluded — they have their
   own discovery paths)
2. **User plugins**   – ``~/.hermes/plugins/<name>/``
3. **Project plugins** – ``./.hermes/plugins/<name>/`` (opt-in via
   ``HERMES_ENABLE_PROJECT_PLUGINS``)
4. **Pip plugins**     – packages that expose the ``hermes_agent.plugins``
   entry-point group.

Later sources override earlier ones on name collision, so a user or project
plugin with the same name as a bundled plugin replaces it.

Each directory plugin must contain a ``plugin.yaml`` manifest **and** an
``__init__.py`` with a ``register(ctx)`` function.

Lifecycle hooks
---------------
Plugins may register callbacks for any of the hooks in ``VALID_HOOKS``.
The agent core calls ``invoke_hook(name, **kwargs)`` at the appropriate
points.

Tool registration
-----------------
``PluginContext.register_tool()`` delegates to ``tools.registry.register()``
so plugin-defined tools appear alongside the built-in tools.

### class PluginToolOverrideError

> 继承: `PermissionError` ｜ 方法数: 0（公开 0）

Raised when a plugin attempts to override a built-in tool without
operator opt-in via ``plugins.entries.<plugin_id>.allow_tool_override``.


### class PluginManifest

> 继承: `object` ｜ 方法数: 0（公开 0）

Parsed representation of a plugin.yaml manifest.


### class LoadedPlugin

> 继承: `object` ｜ 方法数: 0（公开 0）

Runtime state for a single loaded plugin.


### class PluginContext

> 继承: `object` ｜ 方法数: 24（公开 22）

Facade given to plugins so they can register tools and hooks.

#### def `__init__(manifest: PluginManifest, manager: PluginManager)`

#### property `llm(self) -> Any`

Return the plugin's :class:`agent.plugin_llm.PluginLlm` facade.

Lets trusted plugins run host-owned chat or structured completions
against the user's active model and auth without bringing their
own provider keys. Override capability (model, agent id, auth
profile) is fail-closed by default and gated through
``plugins.entries.<plugin_id>.llm.*`` config keys.

See :mod:`agent.plugin_llm` for the full surface.

#### property `profile_name(self) -> str`

Return the active Hermes profile name (e.g. ``"default"``).

Derived from ``HERMES_HOME`` via
:func:`hermes_cli.profiles.get_active_profile_name`, so it works in
every execution context — interactive CLI, gateway, and
kanban-spawned worker sessions alike — without depending on
``_cli_ref`` (which is ``None`` outside an interactive CLI run).

Returns ``"default"`` for the default profile, the profile id when
running under ``~/.hermes/profiles/<name>``, or ``"custom"`` when
``HERMES_HOME`` points somewhere unrecognized.

#### def `register_tool(self, name: str, toolset: str, schema: dict, handler: Callable, check_fn: Callable | None = None, requires_env: list | None = None, is_async: bool = False, description: str = '', emoji: str = '', override: bool = False) -> None`

Register a tool in the global registry **and** track it as plugin-provided.

Pass ``override=True`` to replace an existing built-in tool with the
same name (e.g. swap the default ``browser_navigate`` for a custom
CDP-backed implementation). Without it, attempting to register a name
already claimed by a different toolset is rejected.

``override=True`` against a built-in tool requires the operator to
opt in via ``plugins.entries.<plugin_id>.allow_tool_override: true``
in config.yaml — mirrors the trust gate pattern used for
``ctx.llm`` provider/model overrides (#23194). Without that gate,
any enabled plugin could silently replace a privileged built-in
like ``shell_exec`` or ``write_file`` and exfiltrate everything
the model invokes through it.

**异常**: `PluginToolOverrideError`

#### def `inject_message(self, content: str, role: str = 'user') -> bool`

Inject a message into the active conversation.

If the agent is idle (waiting for user input), this starts a new turn.
If the agent is running, this interrupts and injects the message.

This enables plugins (e.g. remote control viewers, messaging bridges)
to send messages into the conversation from external sources.

Returns True if the message was queued successfully.

#### def `register_cli_command(self, name: str, help: str, setup_fn: Callable, handler_fn: Callable | None = None, description: str = '') -> None`

Register a CLI subcommand (e.g. ``hermes honcho ...``).

The *setup_fn* receives an argparse subparser and should add any
arguments/sub-subparsers.  If *handler_fn* is provided it is set
as the default dispatch function via ``set_defaults(func=...)``.

#### def `register_command(self, name: str, handler: Callable, description: str = '', args_hint: str = '') -> None`

Register a slash command (e.g. ``/lcm``) available in CLI and gateway sessions.

The handler signature is ``fn(raw_args: str) -> str | None``.
It may also be an async callable — the gateway dispatch handles both.

Unlike ``register_cli_command()`` (which creates ``hermes <subcommand>``
terminal commands), this registers in-session slash commands that users
invoke during a conversation.

``args_hint`` is an optional short string (e.g. ``"<file>"`` or
``"dias:7 formato:json"``) used by gateway adapters to surface the
command with an argument field — for example Discord's native slash
command picker. Plugin commands without ``args_hint`` register as
parameterless in Discord and still accept trailing text when invoked
as free-form chat.

Names conflicting with built-in commands are rejected with a warning.

#### def `dispatch_tool(self, tool_name: str, args: dict, **kwargs) -> str`

Dispatch a tool call through the registry, with parent agent context.

This is the public interface for plugin slash commands that need to call
tools like ``delegate_task`` without reaching into framework internals.
The parent agent (if available) is resolved automatically — plugins never
need to access the agent directly.

Args:
    tool_name: Registry name of the tool (e.g. ``"delegate_task"``).
    args: Tool arguments dict (same as what the model would pass).
    **kwargs: Extra keyword args forwarded to the registry dispatch.

Returns:
    JSON string from the tool handler (same format as model tool calls).

#### def `register_context_engine(self, engine) -> None`

Register a context engine to replace the built-in ContextCompressor.

Only one context engine plugin is allowed. If a second plugin tries
to register one, it is rejected with a warning.

The engine must be an instance of ``agent.context_engine.ContextEngine``.

#### def `register_image_gen_provider(self, provider) -> None`

Register an image generation backend.

``provider`` must be an instance of
:class:`agent.image_gen_provider.ImageGenProvider`. The
``provider.name`` attribute is what ``image_gen.provider`` in
``config.yaml`` matches against when routing ``image_generate``
tool calls.

#### def `register_dashboard_auth_provider(self, provider) -> None`

Register a dashboard authentication provider.

``provider`` must be an instance of
:class:`hermes_cli.dashboard_auth.DashboardAuthProvider`. Used by
the dashboard OAuth auth gate, which engages when the dashboard
binds to a non-loopback host without ``--insecure``.

Misbehaving providers (wrong type, duplicate name) are logged at
WARNING and silently ignored — never raised — so a broken plugin
cannot crash the host. Same convention as
``register_image_gen_provider``.

#### def `register_video_gen_provider(self, provider) -> None`

Register a video generation backend.

``provider`` must be an instance of
:class:`agent.video_gen_provider.VideoGenProvider`. The
``provider.name`` attribute is what ``video_gen.provider`` in
``config.yaml`` matches against when routing ``video_generate``
tool calls.

#### def `register_web_search_provider(self, provider) -> None`

Register a web search/extract backend.

``provider`` must be an instance of
:class:`agent.web_search_provider.WebSearchProvider`. The
``provider.name`` attribute is what ``web.search_backend`` /
``web.extract_backend`` / ``web.backend`` in ``config.yaml``
matches against when routing ``web_search`` / ``web_extract``
tool calls.

#### def `register_browser_provider(self, provider) -> None`

Register a cloud browser backend.

``provider`` must be an instance of
:class:`agent.browser_provider.BrowserProvider`. The
``provider.name`` attribute is what ``browser.cloud_provider`` in
``config.yaml`` matches against when routing cloud-mode
``browser_*`` tool calls.

Mirrors :meth:`register_web_search_provider` exactly — same
registration shape, same gating, same logging. The browser
subsystem's dispatcher (:func:`tools.browser_tool._get_cloud_provider`)
consults the registry built up by these calls.

#### def `register_secret_source(self, source) -> None`

Register an external secret-manager backend.

``source`` must be an instance of
:class:`agent.secret_sources.base.SecretSource`.  Registered
sources run during ``load_hermes_dotenv()`` startup — after
``~/.hermes/.env`` loads, before Hermes reads credentials — when
their ``secrets.<source.name>`` config section is enabled.  The
orchestrator (``agent.secret_sources.registry.apply_all``) owns
ordering, mapped-vs-bulk precedence, conflict warnings, and
provenance; the source only fetches.

NOTE ON TIMING: plugin discovery happens later in startup than
the first ``load_hermes_dotenv()`` call, so a plugin-registered
source is not consulted by the initial env load of the process
that discovers it.  It IS consulted by every subsequently
spawned Hermes process (gateway children, cron sessions,
subagents), and immediately after a
``reset_secret_source_cache()`` re-pull.  Plugin sources are
therefore best for supplying credentials to the running fleet;
the bundled sources cover first-process bootstrap.

Contract requirements (rejected with a warning otherwise):
inherit from ``SecretSource``, ``api_version`` matching
``SECRET_SOURCE_API_VERSION``, lowercase unique ``name``,
``shape`` of ``"mapped"`` or ``"bulk"``, unique ``scheme`` (when
set), and a ``fetch()`` that never raises and never prompts.
See the base-module docstring for the full contract.

#### def `register_tts_provider(self, provider) -> None`

Register a text-to-speech backend.

``provider`` must be an instance of
:class:`agent.tts_provider.TTSProvider`. The ``provider.name``
attribute is what ``tts.provider`` in ``config.yaml`` matches
against when routing ``text_to_speech`` tool calls — **but
only when**:

1. ``provider.name`` is NOT a built-in TTS provider name
   (``edge``, ``openai``, ``elevenlabs``, …). Built-ins always
   win — the registry rejects shadowing names with a warning.
2. There is NO ``tts.providers.<name>: type: command`` entry
   with the same name. Command-providers (PR #17843) win on
   name collision because config is more local than plugin
   install.

Coexists with the command-provider registry rather than
replacing it — see issue #30398 for the full design rationale.

#### def `register_transcription_provider(self, provider) -> None`

Register a speech-to-text backend.

``provider`` must be an instance of
:class:`agent.transcription_provider.TranscriptionProvider`.
The ``provider.name`` attribute is what ``stt.provider`` in
``config.yaml`` matches against when routing
:func:`tools.transcription_tools.transcribe_audio` calls —
**but only when**:

1. ``provider.name`` is NOT a built-in STT provider name
   (``local``, ``local_command``, ``groq``, ``openai``,
   ``mistral``, ``xai``). Built-ins always win — the registry
   rejects shadowing names with a warning.
2. There is NO ``stt.providers.<name>: type: command`` entry
   with the same name. Command-providers win on name
   collision because config is more local than plugin install
   — same precedence rule as TTS.

Coexists with the in-tree dispatcher and the STT
command-provider registry rather than replacing them. The 6
built-in STT backends keep their native implementations in
``tools/transcription_tools.py``; this hook is for *new* Python
engines (OpenRouter, SenseAudio, Gemini-STT, custom proprietary
backends).

#### def `register_platform(self, name: str, label: str, adapter_factory: Callable, check_fn: Callable, validate_config: Callable | None = None, required_env: list | None = None, install_hint: str = '', **entry_kwargs: Any) -> None`

Register a gateway platform adapter.

The adapter_factory receives a ``PlatformConfig`` and returns a
``BasePlatformAdapter`` subclass instance.  The gateway calls
``check_fn()`` before instantiation to verify dependencies.

Extra keyword arguments are forwarded to ``PlatformEntry`` (e.g.
``setup_fn``, ``emoji``, ``allowed_users_env``, ``platform_hint``).
Unknown keys raise TypeError from the dataclass constructor.

Example::

    ctx.register_platform(
        name="irc",
        label="IRC",
        adapter_factory=lambda cfg: IRCAdapter(cfg),
        check_fn=lambda: True,
        emoji="💬",
        setup_fn=irc_interactive_setup,
    )

#### def `register_slack_action_handler(self, action_id: Any, callback: Callable) -> None`

Register a Slack Block Kit action handler from a plugin.

Hermes' Slack adapter wires registered handlers into its
``slack_bolt.AsyncApp`` at connect time. The callback is invoked
when a user clicks a button (or interacts with another Block Kit
action element) whose ``action_id`` matches.

Callback signature follows the slack_bolt convention::

    async def handler(ack, body, action) -> None:
        await ack()  # required, within 3 seconds
        ...

Args:
    action_id: Whatever ``slack_bolt.App.action()`` accepts —
        a literal ``action_id`` string, a compiled ``re.Pattern``
        for matching multiple ids, or a constraint dict
        (e.g. ``{"action_id": "...", "block_id": "..."}``).
    callback: Async callable receiving ``(ack, body, action)``.

Raises:
    ValueError: if ``callback`` is not callable, or ``action_id``
        is empty/None.

Example::

    async def _on_approve(ack, body, action):
        await ack()
        # apply some workflow keyed on action["value"]

    ctx.register_slack_action_handler("inbox_sweep_approve", _on_approve)

**异常**: `ValueError`, `Example`

#### def `register_auxiliary_task(self, key: str, display_name: str, description: str, defaults: Optional[Dict[str, Any]] = None) -> None`

Register a plugin-defined auxiliary LLM task.

Auxiliary tasks are LLM-backed side jobs (vision analysis, web extraction,
compression, smart-approval, etc.) that route through ``auxiliary_client.py``.
Each task has its own ``auxiliary.<key>`` config block where users can
pin a provider/model independent of the main chat model.

Plugins use this to declare their own auxiliary tasks without touching
core files. After registration, the task:

  - Appears in the ``hermes model → Configure auxiliary models`` picker
  - Has its provider/model/base_url/api_key bridged from config.yaml to
    ``AUXILIARY_<KEY_UPPER>_*`` env vars at gateway startup
  - Gets default routing fields (provider="auto", model="", etc.) merged
    into loaded configs so ``cfg.get("auxiliary", {}).get(key)`` works

Args:
    key: stable task key (snake_case). Used in config ``auxiliary.<key>``
        and env vars ``AUXILIARY_<KEY_UPPER>_*``. Must not shadow a
        built-in task key (vision, compression, web_extract, approval,
        mcp, title_generation, skills_hub, curator).
    display_name: human-readable name shown in the picker.
    description: short one-line description shown next to the name.
    defaults: optional dict of default routing fields. Recognized keys:
        ``provider`` (default "auto"), ``model`` (default ""),
        ``base_url`` (default ""), ``api_key`` (default ""),
        ``timeout`` (default 60), ``extra_body`` (default {}),
        plus any task-specific extras (e.g. ``download_timeout``).
        Unknown keys are preserved verbatim — the plugin owns the
        schema for its own task.

Raises:
    ValueError: if *key* is empty, contains invalid characters, or
        shadows a built-in auxiliary task key.

Example:
    ctx.register_auxiliary_task(
        key="memory_retain_filter",
        display_name="Memory retain filter",
        description="hindsight pre-retain dedup/extract",
        defaults={"provider": "auto", "timeout": 30},
    )

**异常**: `ValueError`, `Example`

#### def `register_hook(self, hook_name: str, callback: Callable) -> None`

Register a lifecycle hook callback.

Unknown hook names produce a warning but are still stored so
forward-compatible plugins don't break.

#### def `register_middleware(self, kind: str, callback: Callable) -> None`

Register a behavior-changing middleware callback.

Middleware is separate from observer hooks: request middleware may
rewrite the effective payload, and execution middleware may wrap the
real callback. Unknown kinds are stored for forward compatibility but
warned so plugin authors can catch typos.

#### def `register_skill(self, name: str, path: Path, description: str = '') -> None`

Register a read-only skill provided by this plugin.

The skill becomes resolvable as ``'<plugin_name>:<name>'`` via
``skill_view()``.  It does **not** enter the flat
``~/.hermes/skills/`` tree and is **not** listed in the system
prompt's ``<available_skills>`` index — plugin skills are
opt-in explicit loads only.

Raises:
    ValueError: if *name* contains ``':'`` or invalid characters.
    FileNotFoundError: if *path* does not exist.

**异常**: `ValueError`, `FileNotFoundError`


### class PluginManager

> 继承: `object` ｜ 方法数: 21（公开 10）

Central manager that discovers, loads, and invokes plugins.

#### def `__init__() -> None`

#### def `discover_and_load(self, force: bool = False) -> None`

Scan all plugin sources and load each plugin found.

When ``force`` is true, clear cached discovery state first so config
changes or newly-added bundled backends become visible in long-lived
sessions without requiring a full agent restart.

#### def `invoke_hook(self, hook_name: str, **kwargs: Any) -> List[Any]`

Call all registered callbacks for *hook_name*.

Each callback is wrapped in its own try/except so a misbehaving
plugin cannot break the core agent loop.

Returns a list of non-``None`` return values from callbacks.

For ``pre_llm_call``, callbacks may return a dict describing
context to inject into the current turn's user message::

    {"context": "recalled text..."}
    "recalled text..."          # plain string, equivalent

Context is ALWAYS injected into the user message, never the
system prompt.  This preserves the prompt cache prefix — the
system prompt stays identical across turns so cached tokens
are reused.  All injected context is ephemeral — never
persisted to session DB.

#### def `has_hook(self, hook_name: str) -> bool`

Return True when at least one callback is registered for a hook.

#### def `has_middleware(self, kind: str) -> bool`

Return True when at least one callback is registered for middleware.

#### def `invoke_middleware(self, kind: str, **kwargs: Any) -> List[Any]`

Call registered middleware callbacks for *kind*.

Each callback is isolated so one plugin cannot break the base runtime
path. Middleware that wants to change behavior must return the shape
documented by the caller-specific contract.

#### def `get_slack_action_handlers(self) -> List[tuple]`

Return the list of plugin-registered Slack action handlers.

Each entry is a ``(action_id, callback, plugin_name)`` tuple.
Consumed by the Slack adapter at connect time to wire callbacks
into its ``slack_bolt.AsyncApp``.

Plugins register handlers via
:meth:`PluginContext.register_slack_action_handler`.

#### def `list_plugins(self) -> List[Dict[str, Any]]`

Return a list of info dicts for all discovered plugins.

#### def `find_plugin_skill(self, qualified_name: str) -> Optional[Path]`

Return the ``Path`` to a plugin skill's SKILL.md, or ``None``.

#### def `list_plugin_skills(self, plugin_name: str) -> List[str]`

Return sorted bare names of all skills registered by *plugin_name*.

#### def `remove_plugin_skill(self, qualified_name: str) -> None`

Remove a stale registry entry (silently ignores missing keys).


### 顶层函数

#### def `get_bundled_plugins_dir() -> Path`

Locate the bundled ``plugins/`` directory.

Honours ``HERMES_BUNDLED_PLUGINS`` (set by the Nix wrapper / packaged
installs) so read-only store paths are consulted first.  Falls back to
the in-repo path used during development.

#### def `get_plugin_manager() -> PluginManager`

Return (and lazily create) the global PluginManager singleton.

#### def `discover_plugins(force: bool = False) -> None`

Discover and load all plugins.

Default behavior is idempotent. Pass ``force=True`` to rescan plugin
manifests and reload state in the current process.

#### def `invoke_hook(hook_name: str, **kwargs: Any) -> List[Any]`

Invoke a lifecycle hook on all loaded plugins.

Returns a list of non-``None`` return values from plugin callbacks.

#### def `invoke_middleware(kind: str, **kwargs: Any) -> List[Any]`

Invoke registered middleware callbacks.

Returns a list of non-``None`` return values from middleware callbacks.

#### def `has_middleware(kind: str) -> bool`

Return True when middleware callbacks are registered for ``kind``.

#### def `has_hook(hook_name: str) -> bool`

Return True when a hook has registered callbacks.

#### def `set_thread_tool_whitelist(allowed: Optional[Set[str]], deny_msg_fmt: str = "Tool '{tool_name}' denied: not in this thread's tool whitelist") -> None`

#### def `clear_thread_tool_whitelist() -> None`

#### def `get_pre_tool_call_directive(tool_name: str, args: Optional[Dict[str, Any]], task_id: str = '', session_id: str = '', tool_call_id: str = '', turn_id: str = '', api_request_id: str = '', middleware_trace: Optional[List[Dict[str, Any]]] = None) -> tuple[Optional[str], Optional[str]]`

Check ``pre_tool_call`` hooks for a blocking or approval directive.

Backward-compatible public helper: returns ``(directive, message)`` where
``directive`` is ``"block"``, ``"approve"``, or ``None``. Internal callers
that need approve-specific metadata use
:func:`_get_pre_tool_call_directive_details`.

#### def `get_pre_tool_call_block_message(tool_name: str, args: Optional[Dict[str, Any]], task_id: str = '', session_id: str = '', tool_call_id: str = '', turn_id: str = '', api_request_id: str = '', middleware_trace: Optional[List[Dict[str, Any]]] = None) -> Optional[str]`

Back-compat shim: return only a ``block`` message (or ``None``).

Deprecated in favor of :func:`get_pre_tool_call_directive`, which also
surfaces the ``approve`` escalation directive. Kept so any external caller
importing the old name keeps working; ``approve`` directives are invisible
to this shim (it only reports blocks).

#### def `resolve_pre_tool_block(tool_name: str, args: Optional[Dict[str, Any]], task_id: str = '', session_id: str = '', tool_call_id: str = '', turn_id: str = '', api_request_id: str = '', middleware_trace: Optional[List[Dict[str, Any]]] = None) -> Optional[str]`

Resolve the pre_tool_call directive to a final block message (or None).

Single entry point for every tool-dispatch site: fetches the plugin
directive and, for an ``approve`` escalation, invokes the human-approval
gate (:func:`tools.approval.request_tool_approval`). Returns the message
the tool result should carry when the call is blocked, or ``None`` when
the call may proceed.

Centralizing this keeps the security-critical fail-closed logic in ONE
place instead of copy-pasted across the concurrent/sequential/helper
dispatch paths: an ``approve`` directive whose gate errors, denies, or
times out is fail-closed to a block; ``block`` blocks with its message;
anything else proceeds.

#### def `get_pre_verify_continue_message(session_id: str = '', platform: str = '', model: str = '', coding: bool = False, attempt: int = 0, final_response: str = '', changed_paths: Optional[List[str]] = None) -> Optional[str]`

Check user ``pre_verify`` hooks for a directive to keep the agent going.

Fired once per turn when the agent edited code and is about to verify/finish.
A hook keeps the turn going (run a check, defer it, tidy the diff) by
returning::

    {"action": "continue", "message": "<follow-up for the model>"}

The Claude-Code Stop shape ``{"decision": "block", "reason": "..."}`` (block
the stop == keep going) is accepted too. The first directive carrying a
non-empty message wins; any other return lets the turn finish. Mirrors
:func:`get_pre_tool_call_block_message` — the call site stays a one-liner.

``coding`` / ``attempt`` let a hook scope itself (``if not coding`` …) and
self-throttle (``if attempt`` …), the same way a ``pre_tool_call`` hook
scopes on ``tool_name``.

#### def `get_plugin_context_engine()`

Return the plugin-registered context engine, or None.

#### def `get_plugin_command_handler(name: str) -> Optional[Callable]`

Return the handler for a plugin-registered slash command, or ``None``.

#### def `resolve_plugin_command_result(result: Any) -> Any`

Resolve a plugin command return value, awaiting async handlers when needed.

Sync CLI/TUI dispatch sites call plugin handlers from plain functions.
If a handler is async, await it directly when no loop is running; if
we're already inside an active loop, run it in a helper thread with its
own loop so the caller still gets a concrete result synchronously. The
threaded path is bounded by a 30s timeout so a hung async handler cannot
wedge the terminal indefinitely.

**异常**: `TimeoutError`

#### def `get_plugin_commands() -> Dict[str, dict]`

Return the full plugin commands dict (name → {handler, description, plugin}).

Triggers idempotent plugin discovery so callers can use plugin commands
before any explicit discover_plugins() call.

#### def `get_plugin_auxiliary_tasks() -> List[Dict[str, Any]]`

Return all plugin-registered auxiliary tasks as a stable-ordered list.

Each entry is the registration dict from
:meth:`PluginContext.register_auxiliary_task`:
``{key, display_name, description, defaults, plugin}``.

Triggers idempotent plugin discovery so callers can read the registry
before any explicit ``discover_plugins()`` call. Sorted by ``key`` for
deterministic ordering in pickers and tests.

#### def `get_plugin_toolsets() -> List[tuple]`

Return plugin toolsets as ``(key, label, description)`` tuples.

Used by the ``hermes tools`` TUI so plugin-provided toolsets appear
alongside the built-in ones and can be toggled on/off per platform.


## hermes_cli.plugins_cmd

### 模块文档

``hermes plugins`` CLI subcommand — install, update, remove, and list plugins.

Plugins are installed from Git repositories into ``~/.hermes/plugins/``.
Supports full URLs and ``owner/repo`` shorthand (resolves to GitHub).

After install, if the plugin ships an ``after-install.md`` file it is
rendered with Rich Markdown.  Otherwise a default confirmation is shown.

### class PluginOperationError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Recoverable plugin install/update failure (CLI exits; HTTP maps to 4xx).


### 顶层函数

#### def `cmd_install(identifier: str, force: bool = False, enable: Optional[bool] = None) -> None`

Install a plugin from a Git URL or owner/repo shorthand.

After install, prompt "Enable now? [y/N]" unless *enable* is provided
(True = auto-enable without prompting, False = install disabled).

#### def `cmd_update(name: str) -> None`

Update an installed plugin by pulling latest from its git remote.

#### def `cmd_remove(name: str) -> None`

Remove an installed plugin by name.

#### def `ensure_basic_auth_plugin_enabled_in_config(cfg: dict) -> bool`

Re-enable the bundled basic dashboard-auth plugin in *cfg*.

``hermes setup`` / ``hermes plugins disable basic`` can park the plugin
in ``plugins.disabled`` while ``dashboard.basic_auth`` is configured.
The basic provider is a bundled backend that still respects the
deny-list, so password auth silently fails until the block is removed.

Returns True when ``plugins.disabled`` was modified.

#### def `cmd_enable(name: str, allow_tool_override: Optional[bool] = None) -> None`

Add a plugin to the enabled allow-list (and remove it from disabled).

For non-bundled plugins, prompt the operator about granting the
privileged ``allow_tool_override`` capability (replacing built-in tools
like ``shell_exec`` / ``write_file``). ``allow_tool_override`` is a
tri-state: ``True`` grants without prompting, ``False`` declines without
prompting, ``None`` (default) asks interactively. Bundled plugins are
trusted and never prompted.

#### def `cmd_disable(name: str) -> None`

Remove a plugin from the enabled allow-list (and add to disabled).

#### def `cmd_list(args: Any | None = None) -> None`

List all plugins (bundled + user) with enabled/disabled state.

#### def `cmd_toggle() -> None`

Interactive composite UI — general plugins + provider plugin categories.

#### def `dashboard_install_plugin(identifier: str, force: bool, enable: bool) -> dict[str, Any]`

Non-interactive install for the web dashboard. Returns a JSON-serializable dict.

#### def `dashboard_set_agent_plugin_enabled(name: str, enabled: bool) -> dict[str, Any]`

Enable or disable a plugin in ``config.yaml`` (runtime allow/deny lists).

For plugins that provide tools (toolsets), also toggles the toolset in
``platform_toolsets`` so the agent actually sees the tools in sessions.

#### def `dashboard_update_user_plugin(name: str) -> dict[str, Any]`

``git pull`` inside ``~/.hermes/plugins/<name>``.

#### def `dashboard_remove_user_plugin(name: str) -> dict[str, Any]`

Delete a plugin tree under ``~/.hermes/plugins/`` only.

#### def `plugins_command(args) -> None`

Dispatch hermes plugins subcommands.


## hermes_cli.portal_cli

### 模块文档

``hermes portal`` — the human-readable entry point for Nous Portal.

Running ``hermes portal`` with no subcommand performs the one-shot Portal
onboarding: OAuth login, pick a Nous model, switch the inference provider to
Nous, and offer to enable the Tool Gateway. It is the friendly alias for
``hermes auth add nous --type oauth`` (which still works), is identical to
``hermes setup --portal``, and runs the same Nous flow as the first-time quick
setup.

Subcommands:
  (none)   Log in to Nous Portal + set it up (one-shot onboarding).
  login    Explicit alias for the default one-shot onboarding.
  info     Show Portal auth state + which Tool Gateway tools are routed.
  open     Open the Portal subscription page in the user's default browser.
  tools    List Tool Gateway tools and which are active in the current config.

This command is intentionally minimal — it does not duplicate functionality
already in ``hermes auth`` or ``hermes tools``. It's the onboarding + discovery
surface for the Portal subscription itself.

### 顶层函数

#### def `portal_command(args) -> int`

Top-level dispatch for `hermes portal <subcommand>`.

#### def `add_parser(subparsers) -> None`

Register `hermes portal` on the given argparse subparsers object.


## hermes_cli.profile_describer

### 模块文档

Profile describer — auto-generate ``description`` for a profile.

Used by ``hermes profile describe <name> --auto`` and the dashboard's
"auto-generate description" button. Reads the profile's installed
skills, model+provider, name, and optionally a small slice of memory,
then asks the auxiliary LLM to produce a 1-2 sentence description of
what the profile is good at.

Result is written to ``<profile_dir>/profile.yaml`` with
``description_auto: true`` so the dashboard can surface a "review"
badge. User can edit afterward to confirm.

Design notes
------------
- Mirrors the shape of ``hermes_cli/kanban_specify.py``: lazy aux
  client import inside the function, lenient response parse, never
  raises on expected failure modes.
- Reads at most ``MAX_SKILLS_FOR_PROMPT`` skill names to keep the
  prompt bounded. No skill body — names + categories are enough
  signal and avoid blowing context on profiles with 100+ skills.
- Memory is intentionally NOT read here. Memories are personal and
  the orchestrator routes work to a *role* not a *biography*. If we
  find later that memory adds signal we can wire it; for now,
  skills + name + model is plenty.

### class DescribeOutcome

> 继承: `object` ｜ 方法数: 0（公开 0）

Result of describing a single profile.


### 顶层函数

#### def `describe_profile(profile_name: str, overwrite: bool = False, timeout: Optional[int] = None) -> DescribeOutcome`

Auto-generate a description for one profile.

Returns an outcome describing what happened. Never raises for
expected failure modes (profile missing, no aux client configured,
API error, malformed response) — those surface via ``ok=False`` so
a sweep can continue past individual failures.

``overwrite`` controls whether an existing user-authored description
is replaced. By default we refuse to overwrite a description with
``description_auto: false`` to protect curated text. Auto-generated
descriptions (``description_auto: true``) are always replaceable.

#### def `list_describable_profiles(missing_only: bool = True) -> list[str]`

Return profile names that can be described.

``missing_only=True`` (default) returns only profiles without a
description. ``missing_only=False`` returns every profile.


## hermes_cli.profile_distribution

### 模块文档

Profile distributions — shareable, packaged Hermes profiles via git.

A distribution is a Hermes profile published as a git repository (or
installed from a local directory for development). Install with one command
from a git URL, update in place, and keep your local memories / sessions /
credentials untouched.

Where this fits relative to the existing pieces:

* ``hermes profile export/import`` — local backup / restore for a profile
  on your own machine. NOT a distribution format. Stays as-is.
* ``hermes skills install <url>`` — the URL install pattern we're mirroring,
  but at the profile granularity.

Subcommands (all live under ``hermes profile``, not a parallel tree):

    hermes profile install <source> [--name N] [--alias] [--force] [--yes]
    hermes profile update  <name>  [--force-config] [--yes]
    hermes profile info    <name>

``<source>`` is one of:

* A git URL (``github.com/user/repo``, ``https://github.com/...``, ``git@...``,
  ``ssh://``, ``git://``), optionally with ``#<ref>`` to pin a tag / branch /
  commit SHA.
* A local directory that already contains ``distribution.yaml`` — used
  during profile development before the first push.

Manifest format (``distribution.yaml`` at the profile root)::

    name: telemetry
    version: 0.1.0
    description: "Compliance monitoring harness"
    hermes_requires: ">=0.12.0"
    author: "..."
    license: "..."
    env_requires:
      - name: OPENAI_API_KEY
        description: "OpenAI API key"
        required: true
      - name: GRAPHITI_MCP_URL
        description: "Memory graph URL"
        required: false
        default: "http://127.0.0.1:8000/sse"
    distribution_owned:      # optional; sensible defaults apply
      - SOUL.md
      - skills/
      - cron/
      - mcp.json

Update semantics:

* Distribution-owned paths (SOUL.md, mcp.json, skills/, cron/,
  distribution.yaml) are replaced from the new source.
* ``config.yaml`` is distribution-owned but preserved on update unless
  ``--force-config`` is passed (user overrides typically live here).
* User-owned paths (memories/, sessions/, state.db, auth.json, .env,
  logs/, workspace/, home/, plans/, *_cache/, and anything under
  ``local/``) are never touched.

### class DistributionError

> 继承: `Exception` ｜ 方法数: 0（公开 0）

Raised for distribution install/update failures.


### class EnvRequirement

> 继承: `object` ｜ 方法数: 2（公开 2）

#### classmethod `from_dict(cls, data: Any) -> EnvRequirement`

**异常**: `DistributionError`

#### def `to_dict(self) -> Dict[str, Any]`


### class DistributionManifest

> 继承: `object` ｜ 方法数: 3（公开 3）

#### classmethod `from_dict(cls, data: Any) -> DistributionManifest`

**异常**: `DistributionError`

#### def `to_dict(self) -> Dict[str, Any]`

#### def `owned_paths(self) -> List[str]`

Resolve which paths count as distribution-owned.


### class InstallPlan

> 继承: `object` ｜ 方法数: 0（公开 0）

Summary of what an install will do, surfaced for user confirmation.


### 顶层函数

#### def `read_manifest(profile_dir: Path) -> Optional[DistributionManifest]`

Return the manifest for *profile_dir*, or None if it isn't a distribution.

**异常**: `DistributionError`

#### def `write_manifest(profile_dir: Path, manifest: DistributionManifest) -> Path`

#### def `check_hermes_requires(spec: str, current_version: str) -> None`

Raise DistributionError if ``current_version`` does not satisfy ``spec``.

``spec`` accepts a single comparator (``>=0.12.0``, ``==0.12.0``, etc.).
Empty or blank spec is a no-op — no requirement.

**异常**: `DistributionError`

#### def `plan_install(source: str, workdir: Path, override_name: Optional[str] = None) -> InstallPlan`

Stage *source* and produce a plan describing what install would do.

**异常**: `DistributionError`

#### def `install_distribution(source: str, name: Optional[str] = None, force: bool = False, create_alias: bool = False) -> InstallPlan`

Install a distribution from *source* into a new profile.

Returns the resolved :class:`InstallPlan`.  Use :func:`plan_install`
first if you want to preview + prompt the user before calling this.

**异常**: `DistributionError`

#### def `update_distribution(profile_name: str, force_config: bool = False) -> InstallPlan`

Re-pull the distribution for an existing profile and apply updates.

The source is read from the installed profile's ``distribution.yaml``
``source:`` field.  Distribution-owned files are overwritten; user-owned
data (memories, sessions, auth) is never touched.  ``config.yaml`` is
preserved unless ``force_config`` is True.

**异常**: `DistributionError`

#### def `describe_distribution(profile_name: str) -> Dict[str, Any]`

Return a structured view of a profile's distribution metadata.

Returns an empty dict if the profile exists but has no manifest.
Raises DistributionError if the profile itself doesn't exist.

**异常**: `DistributionError`


## hermes_cli.profiles

### 模块文档

Profile management for multiple isolated Hermes instances.

Each profile is a fully independent HERMES_HOME directory with its own
config.yaml, .env, memory, sessions, skills, gateway, cron, and logs.
Profiles live under ``~/.hermes/profiles/<name>/`` by default.

The "default" profile is ``~/.hermes`` itself — backward compatible,
zero migration needed.

Usage::

    hermes profile create coder          # fresh profile + bundled skills
    hermes profile create coder --clone  # also copy config, .env, SOUL.md, skills
    hermes profile create coder --clone-all  # full copy of source profile
    coder chat                           # use via wrapper alias
    hermes -p coder chat                 # or via flag
    hermes profile use coder             # set as sticky default
    hermes profile delete coder          # remove profile + alias + service

### class ProfileInfo

> 继承: `object` ｜ 方法数: 0（公开 0）

Summary information about a profile.


### 顶层函数

#### def `has_bundled_skills_opt_out(profile_dir: Path) -> bool`

Return True if the profile opted out of bundled-skill seeding.

#### def `normalize_profile_name(name: str) -> str`

Return the canonical profile id used on disk and in CLI ``-p`` argv.

Named profiles are stored lowercase under ``profiles/<id>/``. The special
alias ``default`` is matched case-insensitively (``Default`` → ``default``).
Dashboards and tools may pass title-cased display labels; normalize before
validation, assignment, and subprocess spawn (see issue #18498).

**异常**: `ValueError`

#### def `validate_profile_name(name: str) -> None`

Raise ``ValueError`` if *name* is not a valid profile identifier.

Validates the input as-given — strict lowercase match. Callers that accept
mixed-case or title-cased input from users (dashboard UI, CLI args) should
call :func:`normalize_profile_name` first. This separation keeps validate
honest about what the on-disk directory name must look like, while
ingress-point normalization handles UX flexibility (see #18498).

Also rejects names in :data:`_RESERVED_NAMES` (``hermes``, ``test``,
``tmp``, ``root``, ``sudo``) that would create confusing on-disk
collisions (a ``hermes`` profile inside ``~/.hermes/``) or get refused
at alias-creation time anyway. ``default`` is a special pass-through —
it's a valid alias for the built-in root profile.

**异常**: `ValueError`

#### def `validate_alias_name(name: str) -> None`

Raise ``ValueError`` if *name* is not a safe wrapper-alias identifier.

The alias is used verbatim as a filename under :func:`_get_wrapper_dir`
(``~/.local/bin``), so it must be a single safe command name with no path
separators or traversal segments — otherwise a value like ``../../.bashrc``
would escape the wrapper directory and clobber arbitrary user files. We
reuse the profile id regex, which already forbids ``/``, ``.``, and ``..``.

**异常**: `ValueError`

#### def `get_profile_dir(name: str) -> Path`

Resolve a profile name to its HERMES_HOME directory.

#### def `profile_exists(name: str) -> bool`

Check whether a profile directory exists.

#### def `check_alias_collision(name: str) -> Optional[str]`

Return a human-readable collision message, or None if the name is safe.

Checks: alias-name validity, reserved names, hermes subcommands, existing
binaries in PATH.

#### def `create_wrapper_script(name: str, target: Optional[str] = None) -> Optional[Path]`

Create a shell wrapper script at ~/.local/bin/<name>.

The wrapper file is named after ``name`` (the alias). The profile it
activates is ``target`` if given, otherwise ``name`` — this lets a custom
alias name point at a differently-named profile without a post-hoc rewrite.

On Windows, creates a ``.bat`` file instead of a POSIX shell script.
Returns the path to the created wrapper, or None if creation failed.

#### def `remove_wrapper_script(name: str) -> bool`

Remove the wrapper script for a profile. Returns True if removed.

#### def `find_alias_for_profile(profile_name: str) -> Optional[str]`

Return the alias name of the wrapper that activates *profile_name*, or None.

A wrapper created by :func:`create_wrapper_script` is a file named after the
alias whose body invokes ``hermes -p <profile>``. When the alias name equals
the profile name this is trivial, but a custom alias (``hermes profile alias
<profile> --name <custom>``) produces a differently-named file — so the
display side cannot assume ``wrapper == profile`` and must reverse-look-up.

A custom alias (name != profile) is preferred over the profile-named wrapper
so ``profile list``/``show`` surface the command the user actually typed.
Results are sorted for deterministic output when several aliases match.

For listing ALL profiles at once, prefer :func:`build_alias_map` — calling
this per-profile re-reads every wrapper file N times (O(N*M)); on a wrapper
dir like ``~/.local/bin`` that also holds large unrelated binaries (ffmpeg
etc.) that meant multi-second ``list_profiles`` latency and desktop timeouts.

#### def `build_alias_map() -> dict[str, str]`

Single-pass reverse map ``{canonical_profile -> alias_name}``.

Scans the wrapper dir ONCE (vs. :func:`find_alias_for_profile` per profile)
and reads only a small head slice of each candidate wrapper, skipping
binaries. A custom alias (file name != profile) wins over the profile-named
wrapper, matching ``find_alias_for_profile``'s preference; deterministic via
sorted iteration.

#### def `read_profile_meta(profile_dir: Path) -> dict`

Read ``<profile_dir>/profile.yaml`` and return a dict.

Returns ``{"description": "", "description_auto": False}`` when the
file is missing or unreadable. Never raises — a corrupt
profile.yaml on an unrelated profile must not break
``hermes profile list``.

#### def `write_profile_meta(profile_dir: Path, description: Optional[str] = None, description_auto: Optional[bool] = None) -> None`

Update ``<profile_dir>/profile.yaml`` in place.

Only the explicitly passed fields are overwritten; unspecified
fields preserve existing values. Creates the file if missing.
Profile directory itself must exist.

**异常**: `FileNotFoundError`

#### def `list_profiles() -> List[ProfileInfo]`

Return info for all profiles, including the default.

#### def `profiles_to_serve(multiplex: bool) -> List[Tuple[str, Path]]`

Return the ``(profile_name, hermes_home)`` pairs a gateway should serve.

This is the single chokepoint for "which profiles does the inbound gateway
handle" so later multiplexing phases never re-derive the set.

- ``multiplex=False`` (default): returns exactly one entry for the *active*
  profile — byte-for-byte the single-profile behavior the gateway has
  always had. The name is ``"default"`` for the default profile or the
  active named profile's id.
- ``multiplex=True``: returns the default profile plus every valid named
  profile under ``profiles/``, each paired with its own HERMES_HOME.

Intentionally lightweight (a directory scan + name validation only): no
per-profile config reads, gateway-running probes, or skill counts like
:func:`list_profiles`. It runs on gateway startup and must stay cheap.

The returned ``hermes_home`` is the path to pass to
``set_hermes_home_override`` when scoping a turn to that profile.

#### def `create_profile(name: str, clone_from: Optional[str] = None, clone_all: bool = False, clone_config: bool = False, no_alias: bool = False, no_skills: bool = False, description: Optional[str] = None) -> Path`

Create a new profile directory.

Parameters
----------
name:
    Profile identifier (lowercase, alphanumeric, hyphens, underscores).
clone_from:
    Source profile to clone from. If ``None`` and clone_config/clone_all
    is True, defaults to the currently active profile.
clone_all:
    If True, do a full copytree of the source (all state).
clone_config:
    If True, copy config files (config.yaml, .env, SOUL.md), installed
    skills, and selected profile identity files from the source profile.
no_alias:
    If True, skip wrapper script creation.
no_skills:
    If True, create an empty profile with no bundled skills, and write
    a marker file so ``hermes update`` skips re-seeding this profile's
    skills. Mutually exclusive with ``clone_config``/``clone_all`` (those
    explicitly copy skills from the source).

Returns
-------
Path
    The newly created profile directory.

**异常**: `ValueError`, `FileExistsError`, `FileNotFoundError`

#### def `seed_profile_skills(profile_dir: Path, quiet: bool = False) -> Optional[dict]`

Seed bundled skills into a profile via subprocess.

Uses subprocess because sync_skills() caches HERMES_HOME at module level.
Returns the sync result dict, or None on failure.

Profiles that opted out of bundled skills (via ``hermes profile create
--no-skills`` — which writes ``.no-bundled-skills`` to the profile root)
are skipped and get an empty-result dict so callers can report
"opted out" instead of "failed".

#### def `backfill_profile_envs(quiet: bool = False) -> List[str]`

Give every named profile that predates per-profile ``.env`` files one.

Profiles created before the dashboard/CLI started seeding a ``.env``
(PR #44792) have none, so once the Channels/Keys endpoints became
profile-scoped those profiles stopped inheriting the root install's
credentials and showed everything as unconfigured. To avoid breaking
anyone on update, copy the DEFAULT install's ``.env`` into each named
profile that lacks one — that preserves the effective credentials those
profiles were already running with (they previously read the root
``.env`` via the process environment). Users can then diverge per
profile from there.

Falls back to the placeholder header when the default install has no
``.env`` itself. Never overwrites an existing profile ``.env``.

Returns the list of profile names that received a backfilled ``.env``.

#### def `delete_profile(name: str, yes: bool = False) -> Path`

Delete a profile, its wrapper script, and its gateway service.

Stops the gateway if running. Disables systemd/launchd service first
to prevent auto-restart.

Returns the path that was removed.

**异常**: `ValueError`, `FileNotFoundError`, `RuntimeError`

#### def `get_active_profile() -> str`

Read the sticky active profile name.

Returns ``"default"`` if no active_profile file exists or it's empty.

#### def `set_active_profile(name: str) -> None`

Set the sticky active profile.

Writes to ``~/.hermes/active_profile``. Use ``"default"`` to clear.

**异常**: `FileNotFoundError`

#### def `get_active_profile_name() -> str`

Infer the current profile name from HERMES_HOME.

Returns ``"default"`` if HERMES_HOME is not set or points to ``~/.hermes``.
Returns the profile name if HERMES_HOME points into ``~/.hermes/profiles/<name>``.
Returns ``"custom"`` if HERMES_HOME is set to an unrecognized path.

#### def `export_profile(name: str, output_path: str) -> Path`

Export a profile to a tar.gz archive.

Returns the output file path.

**异常**: `FileNotFoundError`

#### def `import_profile(archive_path: str, name: Optional[str] = None) -> Path`

Import a profile from a tar.gz archive.

If *name* is not given, infers it from the archive's top-level directory.
Returns the imported profile directory.

**异常**: `FileNotFoundError`, `ValueError`, `FileExistsError`

#### def `rename_profile(old_name: str, new_name: str) -> Path`

Rename a profile: directory, wrapper script, service, active_profile.

Returns the new profile directory.

**异常**: `ValueError`, `FileNotFoundError`, `FileExistsError`

#### def `resolve_profile_env(profile_name: str) -> str`

Resolve a profile name to a HERMES_HOME path string.

Called early in the CLI entry point, before any hermes modules
are imported, to set the HERMES_HOME environment variable.

**异常**: `FileNotFoundError`


## hermes_cli.projects_cmd

### 模块文档

``hermes project`` CLI — manage first-class, multi-folder Projects.

A Project is a human-named workspace spanning one or more folders, with one
designated primary repo. Projects anchor desktop session grouping and (when
bound to a kanban board) give kanban tasks a deterministic worktree + branch
convention. State lives in the per-profile ``$HERMES_HOME/projects.db`` store
(see :mod:`hermes_cli.projects_db`).

This is a footprint-ladder rung-2 capability: a CLI command + gateway RPC,
with zero model-tool schema cost.

### 顶层函数

#### def `build_parser(parent_subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser`

Attach the ``project`` subcommand tree. Returns the top parser.

#### def `projects_command(args: argparse.Namespace) -> int`

Entry point from ``hermes project …`` argparse dispatch.


## hermes_cli.projects_db

### 模块文档

Per-profile first-class Project store.

A **Project** is a human-named, multi-folder workspace. Unlike the desktop's
old inferred "workspaces" (derived from each session's ``cwd`` + a git probe)
and unlike kanban's self-generated worktrees, a Project is an explicit,
persisted entity the user creates and names. It anchors:

- **Desktop session grouping** — a session belongs to a project when its
  ``cwd`` lives under one of the project's folders (longest-prefix match).
- **Kanban task worktrees** — a task linked to a project creates its worktree
  under the project's primary repo with a deterministic branch name, instead
  of the random ``wt/<task-id>`` fallback.

Scope: **per-profile**, stored at ``$HERMES_HOME/projects.db`` (resolved via
``get_hermes_home()``), mirroring sessions / config / cron. This deliberately
differs from kanban, whose board DB is root-anchored and shared across
profiles. A Project may *bind* a kanban board (``board_slug``) so the two
systems agree on the repo + branch convention without merging their stores.

The schema is intentionally small and additive: column additions go through
:func:`_add_column_if_missing` so opening an old DB is always safe.

### class ProjectFolder

> 继承: `object` ｜ 方法数: 1（公开 1）

#### def `to_dict(self) -> dict`


### class Project

> 继承: `object` ｜ 方法数: 1（公开 1）

#### def `to_dict(self) -> dict`


### 顶层函数

#### def `projects_db_path() -> Path`

The per-profile projects DB path (``$HERMES_HOME/projects.db``).

Profile-aware: ``get_hermes_home()`` already points at the active profile's
home. Tests pass an explicit ``db_path`` to :func:`connect`.

#### def `normalize_slug(slug: Optional[str]) -> Optional[str]`

Lowercase + strip a slug; validate; return ``None`` for empty.

**异常**: `ValueError`

#### def `connect(db_path: Optional[Path] = None) -> sqlite3.Connection`

Open (and initialize if needed) the per-profile projects DB.

WAL with DELETE fallback for network filesystems (shared helper from
``hermes_state``). Schema init is idempotent (``CREATE TABLE IF NOT
EXISTS`` + additive migrations) and cached per-path per-process.

#### def `connect_closing(db_path: Optional[Path] = None)`

Open a projects DB connection and guarantee it is closed on exit.

sqlite3's connection context manager only commits/rollbacks; it does NOT
close the file descriptor. Long-lived processes (gateway, dashboard) route
many project operations through ``connect()``; without closing, FDs to
``projects.db`` accumulate. Mirrors ``kanban_db.connect_closing``.

#### def `create_project(conn: sqlite3.Connection, name: str, slug: Optional[str] = None, folders: Optional[Iterable[str]] = None, primary_path: Optional[str] = None, description: Optional[str] = None, icon: Optional[str] = None, color: Optional[str] = None, board_slug: Optional[str] = None) -> str`

Create a project and return its id.

``folders`` are normalized to absolute paths. If ``primary_path`` is given
it is added to the folder set (if not already present) and marked primary;
otherwise the first folder becomes primary.

**异常**: `ValueError`

#### def `list_projects(conn: sqlite3.Connection, include_archived: bool = False) -> List[Project]`

#### def `get_project(conn: sqlite3.Connection, id_or_slug: str) -> Optional[Project]`

Look up a project by id first, then by slug.

#### def `update_project(conn: sqlite3.Connection, project_id: str, name: Optional[str] = None, description: Optional[str] = None, icon: Optional[str] = None, color: Optional[str] = None, board_slug: Optional[str] = None) -> bool`

Patch top-level project fields. Only provided fields change.

``icon``, ``color``, and ``board_slug`` accept an empty string to clear
(store NULL) — passing ``None`` leaves the field untouched, so callers that
want to clear must send ``""``.

**异常**: `ValueError`

#### def `add_folder(conn: sqlite3.Connection, project_id: str, path: str, label: Optional[str] = None, is_primary: bool = False) -> str`

Add a folder to a project. Returns the normalized path.

When ``is_primary`` is set, the folder becomes the project's primary repo
(the previous primary is demoted, and ``projects.primary_path`` updates).

**异常**: `ValueError`

#### def `remove_folder(conn: sqlite3.Connection, project_id: str, path: str) -> bool`

Remove a folder from a project. Repoints primary if it was primary.

#### def `set_primary(conn: sqlite3.Connection, project_id: str, path: str) -> bool`

#### def `archive_project(conn: sqlite3.Connection, project_id: str) -> bool`

#### def `restore_project(conn: sqlite3.Connection, project_id: str) -> bool`

#### def `delete_project(conn: sqlite3.Connection, project_id: str) -> bool`

Hard-delete a project and its folders (cascade).

#### def `set_active(conn: sqlite3.Connection, project_id: Optional[str]) -> None`

Set (or clear, when ``None``) the active project pointer.

#### def `get_active_id(conn: sqlite3.Connection) -> Optional[str]`

#### def `record_discovered_repos(conn: sqlite3.Connection, repos: Iterable[tuple[str, Optional[str]]], replace: bool = False) -> int`

Persist scanned git repo roots into the cache.

``repos`` is an iterable of ``(root, label)``. Roots are normalized; the
label falls back to the basename. Returns the number of rows written.

When ``replace`` is true, this is the authoritative result of a fresh disk
scan: delete stale rows first so old eval/worktree noise disappears instead
of living forever in the cache.

#### def `list_discovered_repos(conn: sqlite3.Connection) -> List[dict]`

All cached discovered repo roots, most-recently-seen first.

#### def `project_for_path(conn: sqlite3.Connection, path: str, include_archived: bool = False) -> Optional[Project]`

Return the project owning ``path`` (longest-prefix folder match).

A folder owns ``path`` when ``path`` equals the folder or is nested under
it. The most specific (longest) folder wins, so nested projects resolve to
the innermost one.

#### def `branch_name_for(project: Project, task_id: str, title: str = '') -> str`

Deterministic branch name for a project-linked kanban task.

Shape: ``<project-slug>/<task-id>`` (optionally ``-<title-slug>``). Stable
and human-meaningful, replacing the random ``wt/<task-id>`` fallback.


## hermes_cli.prompt_size

### 模块文档

Prompt-size diagnostic: ``hermes prompt-size``.

Reports a byte/char breakdown of the system prompt the agent would build for
a fresh session — system prompt total, the ``<available_skills>`` index,
memory + user profile, and tool-schema JSON. Lets users see where their fixed
prompt budget goes (issue #34667) without parsing a saved session JSON by hand.

The diagnostic builds a real inspection agent (so the numbers match what
actually ships on the wire) but never makes a network call: it passes dummy
credentials so ``AIAgent.__init__`` takes the direct-construction path, then
calls ``build_system_prompt_parts`` / inspects ``agent.tools`` offline.

### 顶层函数

#### def `compute_prompt_breakdown(platform: str = 'cli') -> Dict[str, Any]`

Return a dict of prompt-size measurements for a fresh session.

Keys: ``system_prompt`` (chars/bytes), ``skills_index``, ``memory``,
``user_profile``, ``tools`` (count + json bytes), and ``sections`` (a list
of (label, chars, bytes) for the three prompt tiers).

#### def `render_breakdown(data: Dict[str, Any]) -> str`

Render the breakdown as plain text suitable for a terminal.

#### def `cmd_prompt_size(args: Any) -> None`

Entry point for ``hermes prompt-size``.


## hermes_cli.provider_catalog

### 模块文档

Unified provider catalog — one source of truth for the provider universe.

The provider list shown by ``hermes model`` (CLI/TUI) and the desktop Settings
→ Providers tabs (Accounts + API keys) **must be the same set**.  Historically
they were not: the CLI picker read :data:`hermes_cli.models.CANONICAL_PROVIDERS`
(which auto-extends from ``plugins/model-providers/<name>/``), while the desktop
tabs read separate hand-maintained lists (``_OAUTH_PROVIDER_CATALOG``,
``OPTIONAL_ENV_VARS`` + ``PROVIDER_GROUPS``) that nobody kept in sync.  Every
provider added after those lists were written silently went missing from the
GUI — e.g. GitHub Copilot showing up only under "tools", or ``openai-api`` being
configurable from the CLI but not the desktop app.

This module fixes that at the root: it derives ONE descriptor per provider from
the same universe ``hermes model`` renders (``CANONICAL_PROVIDERS``), joining:

* ``auth_type`` / ``api_key_env_vars`` / ``base_url_env_var`` from
  :data:`hermes_cli.auth.PROVIDER_REGISTRY` (credential truth), and
* ``display_name`` / ``description`` / ``signup_url`` from the provider's
  :class:`providers.base.ProviderProfile` when one exists, falling back to the
  ``CANONICAL_PROVIDERS`` entry's ``label`` / ``tui_desc`` and the
  ``OPTIONAL_ENV_VARS`` signup URL otherwise (many profiles leave these blank,
  and four canonical providers have no profile at all — lmstudio, openai-api,
  tencent-tokenhub, xai-oauth — so the fallbacks are load-bearing).

Each descriptor is tagged with the ``tab`` it belongs on (``keys`` vs
``accounts``) based purely on how the provider authenticates.  The desktop
``/api/env`` and ``/api/providers/oauth`` endpoints derive their MEMBERSHIP from
this catalog; the old hand lists are demoted to presentation/override overlays
(bespoke OAuth flow + status resolvers, richer copy, icons, ordering) and no
longer decide which providers exist.

Parity contract (locked by tests): the union of the two tabs equals the
``CANONICAL_PROVIDERS`` universe, i.e. exactly what ``hermes model`` shows.

### class ProviderDescriptor

> 继承: `object` ｜ 方法数: 0（公开 0）

One provider, as seen by every surface (CLI picker + both GUI tabs).


### 顶层函数

#### def `tab_for_auth_type(auth_type: str) -> str`

Return the desktop tab ("keys"|"accounts") a provider's auth maps to.

#### def `provider_catalog() -> list[ProviderDescriptor]`

Return one descriptor per provider in the ``hermes model`` universe.

Membership is :data:`CANONICAL_PROVIDERS` (the list the CLI/TUI picker
renders, which auto-extends from provider plugins).  Auth + env come from
``PROVIDER_REGISTRY``; display metadata from ``ProviderProfile`` with
canonical/env fallbacks so providers without a profile (or with blank
profile metadata) still resolve sensibly.

#### def `provider_catalog_by_slug() -> dict[str, ProviderDescriptor]`

Convenience: the catalog keyed by slug.


## hermes_cli.providers

### 模块文档

Single source of truth for provider identity in Hermes Agent.

Two data sources, merged at runtime:

1. **models.dev catalog** — 109+ providers with base URLs, env vars, display
   names, and full model metadata (context, cost, capabilities).  This is
   the primary database.

2. **Hermes overlays** — transport type, auth patterns, aggregator flags,
   and additional env vars that models.dev doesn't track.  Small dict,
   maintained here.

3. **User config** (``providers:`` section in config.yaml) — user-defined
   endpoints and overrides.  Merged on top of everything else.

Other modules import from this file.  No parallel registries.

### class HermesOverlay

> 继承: `object` ｜ 方法数: 0（公开 0）

Hermes-specific provider metadata layered on top of models.dev.


### class ProviderDef

> 继承: `object` ｜ 方法数: 0（公开 0）

Complete provider definition — merged from all sources.


### 顶层函数

#### def `normalize_provider(name: str) -> str`

Resolve aliases and normalise casing to a canonical provider id.

Returns the canonical id string.  Does *not* validate that the id
corresponds to a known provider.

#### def `get_provider(name: str) -> Optional[ProviderDef]`

Look up a built-in provider by id or alias.

Resolution order:
  1. Hermes overlays (for providers not in models.dev: nous, openai-codex, etc.)
  2. models.dev catalog + Hermes overlay

User-defined providers from config.yaml (``providers:`` / ``custom_providers:``)
are resolved by :func:`resolve_provider_full`, which layers ``resolve_user_provider``
and ``resolve_custom_provider`` on top of this function. Callers that need
user-config support should use ``resolve_provider_full`` instead.

Returns a fully-resolved ProviderDef or None.

#### def `get_label(provider_id: str) -> str`

Get a human-readable display name for a provider.

#### def `is_aggregator(provider: str) -> bool`

Return True when the provider is a multi-model aggregator.

#### def `is_routing_aggregator(provider: str) -> bool`

Return True only for TRUE routing aggregators (e.g. OpenRouter, named
``custom:*`` proxies) — those that route bare/vendor-slugged model names
to *other* providers' endpoints.

Distinct from :func:`is_aggregator`, which also reports True for
flat-namespace resellers (opencode-go/zen) whose catalog is entirely
first-party. Use this gate when the question is "would selecting this
model silently re-route the call away from the user's intended provider?"
— i.e. the picker dedup. Resellers answer no: their listed models are
their own, so their rows must not be deduped against user proxies.

#### def `host_mandated_api_mode(base_url: str = '') -> Optional[str]`

Return the wire protocol a specific endpoint *requires*, or None.

Some hosts only accept one API mode and reject the others outright:
  - api.openai.com only accepts the Responses API for its (reasoning)
    models when tools + reasoning are in play (chat/completions 400s).
  - api.anthropic.com / ``…/anthropic`` suffixes speak native Messages.
  - Kimi's ``/coding`` endpoint speaks native Messages.
  - AWS Bedrock runtime hosts speak Converse.

These are *mandatory* — a session carrying a stale api_mode (e.g. a
/model switch that kept the previous provider's ``chat_completions``)
must be overridden to the host's required mode, not merely filled in
when empty. Generic / unknown endpoints return None so an explicitly
configured api_mode on them is never clobbered.

#### def `determine_api_mode(provider: str, base_url: str = '') -> str`

Determine the API mode (wire protocol) for a provider/endpoint.

Resolution order:
  1. Host-mandated mode (special endpoints that only accept one protocol).
  2. Known provider → transport → TRANSPORT_TO_API_MODE.
  3. Direct provider checks (bedrock).
  4. Default: 'chat_completions'.

#### def `resolve_user_provider(name: str, user_config: Dict[str, Any]) -> Optional[ProviderDef]`

Resolve a provider from the user's config.yaml ``providers:`` section.

Args:
    name: Provider name as given by the user.
    user_config: The ``providers:`` dict from config.yaml.

Returns:
    ProviderDef if found, else None.

#### def `custom_provider_slug(display_name: str) -> str`

Build a canonical slug for a custom_providers entry.

Matches the convention used by runtime_provider and credential_pool
(``custom:<normalized-name>``).  Centralised here so all call-sites
produce identical slugs.

#### def `resolve_custom_provider(name: str, custom_providers: Optional[List[Dict[str, Any]]]) -> Optional[ProviderDef]`

Resolve a provider from the user's config.yaml ``custom_providers`` list.

#### def `resolve_provider_full(name: str, user_providers: Optional[Dict[str, Any]] = None, custom_providers: Optional[List[Dict[str, Any]]] = None) -> Optional[ProviderDef]`

Full resolution chain: built-in → models.dev → user config.

This is the main entry point for --provider flag resolution.

Args:
    name: Provider name or alias.
    user_providers: The ``providers:`` dict from config.yaml (optional).
    custom_providers: The ``custom_providers:`` list from config.yaml (optional).

Returns:
    ProviderDef if found, else None.


## hermes_cli.proxy.__init__

### 模块文档

Local OpenAI-compatible proxy that forwards to OAuth-authenticated upstreams.

Lets external apps (OpenViking, Karakeep, Open WebUI, ...) ride the user's
already-logged-in provider subscription instead of needing a static API key
copy-pasted into each app's config.

The proxy listens on ``127.0.0.1:<port>``, accepts any bearer (the client's
``Authorization`` header is discarded), and attaches the user's real
upstream credential to the forwarded request. The credential is refreshed
automatically when it approaches expiry.

First-class adapter:
  - ``nous`` — Nous Portal (https://inference-api.nousresearch.com/v1)

Future adapters can plug in by implementing ``UpstreamAdapter``.

## hermes_cli.proxy.adapters.__init__

### 模块文档

Upstream adapter registry for the local proxy server.

Each adapter wraps a provider's OAuth state and exposes a uniform interface
the proxy server can use to forward requests with a freshly-minted bearer
token. See :class:`UpstreamAdapter` for the contract.

### 顶层函数

#### def `get_adapter(name: str) -> UpstreamAdapter`

Instantiate an adapter by provider name.

Raises:
    ValueError: if ``name`` is not a registered adapter.

**异常**: `ValueError`


## hermes_cli.proxy.adapters.base

### 模块文档

Abstract base for proxy upstream adapters.

An :class:`UpstreamAdapter` represents one OAuth-authenticated provider the
local proxy can forward requests to. The adapter is responsible for:

  - locating the user's auth state for that provider
  - refreshing/minting credentials when needed
  - reporting the resolved upstream base URL
  - declaring which request paths it accepts

The proxy server is otherwise provider-agnostic.

### class UpstreamCredential

> 继承: `object` ｜ 方法数: 0（公开 0）

A resolved bearer + base URL ready to forward to.


### class UpstreamAdapter

> 继承: `ABC` ｜ 方法数: 7（公开 7）

Contract for an upstream provider the proxy can forward to.

#### property `name(self) -> str`

Adapter key used on the CLI (e.g. ``"nous"``).

#### property `display_name(self) -> str`

Human-readable provider name for logs and ``proxy status``.

#### property `allowed_paths(self) -> FrozenSet[str]`

Set of relative request paths the upstream accepts.

Paths are relative to the proxy's ``/v1`` mount point. For example,
``"/chat/completions"`` corresponds to a client request to
``http://127.0.0.1:<port>/v1/chat/completions``. Requests to paths
not in this set get a 404 with a helpful error body.

#### def `is_authenticated(self) -> bool`

Return True if the user has usable credentials for this upstream.

Should be cheap — no network calls. Used by ``proxy start`` for a
clear up-front error before binding a port.

#### def `get_credential(self) -> UpstreamCredential`

Return a fresh credential, refreshing or rotating if necessary.

Implementations should:
  - refresh the access token if it's near expiry
  - rotate the upstream bearer key if it's near expiry
  - persist any refreshed state back to disk

Raises:
    RuntimeError: if the user isn't authenticated or the upstream
      refresh fails. The proxy will return 401 to the client.

**异常**: `RuntimeError`

#### def `get_retry_credential(self, failed_credential: UpstreamCredential, status_code: int) -> Optional[UpstreamCredential]`

Return an alternate credential after an upstream auth failure.

The default is no retry. Providers can override this for one-shot
fallback paths after the upstream rejects the first request.

#### def `describe(self) -> str`

One-line status summary for ``proxy status``.


## hermes_cli.proxy.adapters.nous_portal

### 模块文档

Nous Portal upstream adapter.

Reads the user's Nous OAuth state from ``~/.hermes/auth.json`` through the
shared runtime resolver, validates or refreshes the inference JWT, then exposes
the upstream base URL plus bearer for the proxy server to forward to.

### class NousPortalAdapter

> 继承: `UpstreamAdapter` ｜ 方法数: 10（公开 6）

Proxy upstream for the Nous Portal inference API.

#### def `__init__() -> None`

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### property `allowed_paths(self) -> FrozenSet[str]`

#### def `is_authenticated(self) -> bool`

#### def `get_credential(self) -> UpstreamCredential`

#### def `get_retry_credential(self, failed_credential: UpstreamCredential, status_code: int) -> Optional[UpstreamCredential]`


## hermes_cli.proxy.adapters.xai

### 模块文档

xAI Grok OAuth upstream adapter.

### class XAIGrokAdapter

> 继承: `UpstreamAdapter` ｜ 方法数: 9（公开 6）

Proxy upstream for xAI Grok via Hermes-managed OAuth credentials.

#### def `__init__() -> None`

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### property `allowed_paths(self) -> FrozenSet[str]`

#### def `is_authenticated(self) -> bool`

#### def `get_credential(self) -> UpstreamCredential`

**异常**: `RuntimeError`

#### def `get_retry_credential(self, failed_credential: UpstreamCredential, status_code: int) -> Optional[UpstreamCredential]`


## hermes_cli.proxy.cli

### 模块文档

CLI handlers for the ``hermes proxy`` subcommand.

### 顶层函数

#### def `cmd_proxy_start(args: Any) -> int`

Run the proxy server in the foreground.

Returns process exit code (0 on clean shutdown).

#### def `cmd_proxy_status(args: Any) -> int`

Print the status of each configured upstream adapter.

#### def `cmd_proxy_list_providers(args: Any) -> int`

List available proxy upstream providers.

#### def `cmd_proxy(args: Any) -> int`

Dispatch ``hermes proxy <subcommand>``.


## hermes_cli.proxy.server

### 模块文档

HTTP server that forwards OpenAI-compatible requests to a configured upstream.

Listens on ``http://<host>:<port>/v1/<path>`` and forwards each request to
``<upstream-base-url>/<path>`` with the client's ``Authorization`` header
replaced by a freshly-resolved bearer from the configured adapter. The
response is streamed back unmodified, preserving SSE.

The server is intentionally minimal: it does NOT mediate, log, transform,
or rewrite request/response bodies. It's a credential-attaching forwarder.

### 顶层函数

#### def `create_app(adapter: UpstreamAdapter) -> web.Application`

Build the aiohttp application bound to a specific upstream adapter.

**异常**: `RuntimeError`

#### def `run_server(adapter: UpstreamAdapter, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, shutdown_event: Optional[asyncio.Event] = None) -> None`

Run the proxy in the current event loop until shutdown_event is set.

If shutdown_event is None, runs until cancelled (Ctrl+C or SIGTERM).

**异常**: `RuntimeError`


## hermes_cli.psutil_android

### 模块文档

Helpers for the temporary psutil-on-Android compatibility installer.

### class PsutilAndroidInstallError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when the pinned psutil sdist is missing or unsafe.


### 顶层函数

#### def `prepare_patched_psutil_sdist(archive: Path, destination: Path) -> Path`

Safely extract the pinned psutil sdist and patch it for Android.

**异常**: `PsutilAndroidInstallError`


## hermes_cli.pt_input_extras

### 模块文档

Augmentations to prompt_toolkit's input-parsing tables.

Imported once at CLI startup. Each helper installs a small mapping into
prompt_toolkit's `ANSI_SEQUENCES` so byte sequences emitted by modern
keyboard protocols (Kitty / xterm `modifyOtherKeys`) decode to existing
key tuples Hermes already binds.

Kept in a standalone module — separate from `cli.py` — so the registrations
can be unit-tested without importing the whole CLI runtime.

### 顶层函数

#### def `install_shift_enter_alias() -> int`

Map Shift+Enter byte sequences to the (Escape, ControlM) key tuple
that Alt+Enter produces, so the existing Alt+Enter newline handler
fires for terminals that emit a distinct Shift+Enter.

Sequences mapped:
  - "\x1b[13;2u"     — Kitty keyboard protocol / CSI-u, modifier=2 (Shift)
  - "\x1b[27;2;13~"  — xterm modifyOtherKeys=2, modifier=2 (Shift)
  - "\x1b[27;2;13u"  — alternate ordering some emitters use

The CSI-u sequence is not in stock prompt_toolkit. The modifyOtherKeys
variant `\x1b[27;2;13~` IS in stock prompt_toolkit but mapped to plain
`Keys.ControlM` — i.e. Shift+Enter behaves identically to Enter, which
is the very bug this helper exists to fix. We therefore overwrite
those two specific keys (and `\x1b[27;2;13u`) unconditionally; other
`\x1b[27;...;13~` sequences (Ctrl+Enter, Alt+Enter via modifyOtherKeys
variants 5/6/etc.) are left untouched.

Default macOS Terminal and stock Windows Terminal still send the same
byte for Enter and Shift+Enter, so there is no fix for those terminals
at the application layer — the sequences above never reach Hermes.

Returns the number of sequences whose mapping was changed.

#### def `install_ctrl_enter_alias() -> int`

Map Ctrl+Enter byte sequences to the (Escape, ControlM) key tuple
that Alt+Enter produces, so the existing Alt+Enter newline handler
fires for terminals that emit a distinct Ctrl+Enter.

Sequences mapped:
  - "\x1b[13;5u"     — Kitty keyboard protocol / CSI-u, modifier=5 (Ctrl)
  - "\x1b[27;5;13~"  — xterm modifyOtherKeys=2, modifier=5 (Ctrl)
  - "\x1b[27;5;13u"  — alternate ordering some emitters use

Stock prompt_toolkit doesn't map any of these. Without this alias,
Kitty/mintty/xterm-with-modifyOtherKeys users over SSH never get a
Ctrl+Enter newline — the keystroke arrives as a raw CSI sequence that
falls through to the default character-insert handler. See #22379.

Returns the number of sequences whose mapping was changed.

#### def `install_ignored_terminal_sequences() -> int`

Map terminal-emitted noise sequences to ``Keys.Ignore`` so they
are consumed by the VT100 parser before they reach key bindings or
the input buffer.

Currently covers focus reports:
  - ``\x1b[I`` — terminal regained focus (focus in)
  - ``\x1b[O`` — terminal lost focus (focus out)

Ghostty, iTerm2, and some xterm builds can emit these sequences when
the user switches tabs / windows or when a multiplexer toggles focus
tracking upstream. prompt_toolkit does not map these by default, so
its parser falls back to literal key presses (ESC, ``[``, ``I``/``O``)
and inserts ``[I``/``[O`` into the prompt buffer after the ESC byte
is handled.

Registering them as ``Keys.Ignore`` is parser-level — strictly
cleaner than post-hoc regex stripping in the input sanitizer because
the bytes never reach the buffer. ``setdefault`` is used so any user
or downstream registration wins.

Returns the number of sequences whose mapping was changed.


## hermes_cli.pty_bridge

### 模块文档

PTY bridge for `hermes dashboard` chat tab.

Wraps a child process behind a pseudo-terminal so its ANSI output can be
streamed to a browser-side terminal emulator (xterm.js) and typed
keystrokes can be fed back in.  The only caller today is the
``/api/pty`` WebSocket endpoint in ``hermes_cli.web_server``.

Design constraints:

* **POSIX-only.**  This module depends on ``fcntl``, ``termios``, and
  ``ptyprocess``, none of which exist on native Windows Python.  Native
  Windows ConPTY is a different API (Windows 10 build 17763+) and would
  need a separate Windows implementation (``pywinpty``) — that's tracked
  as a future enhancement.  On native Windows, importing this module
  raises :class:`ImportError` and the dashboard's ``/chat`` tab shows a
  WSL-recommended banner instead of crashing.  Every other feature in the
  dashboard (sessions, jobs, metrics, config editor) works natively.
* **Zero Node dependency on the server side.**  We use :mod:`ptyprocess`,
  which is a pure-Python wrapper around the OS calls.  The browser talks
  to the same ``hermes --tui`` binary it would launch from the CLI, so
  every TUI feature (slash popover, model picker, tool rows, markdown,
  skin engine, clarify/sudo/approval prompts) ships automatically.
* **Byte-safe I/O.**  Reads and writes go through the PTY master fd
  directly — we avoid :class:`ptyprocess.PtyProcessUnicode` because
  streaming ANSI is inherently byte-oriented and UTF-8 boundaries may land
  mid-read.

### class PtyUnavailableError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when a PTY cannot be created on this platform.

Today this means native Windows (no ConPTY bindings) or a dev
environment missing the ``ptyprocess`` dependency.  The dashboard
surfaces the message to the user as a chat-tab banner.


### class PtyBridge

> 继承: `object` ｜ 方法数: 11（公开 8）

Thin wrapper around ``ptyprocess.PtyProcess`` for byte streaming.

Not thread-safe.  A single bridge is owned by the WebSocket handler
that spawned it; the reader runs in an executor thread while writes
happen on the event-loop thread.  Both sides are OK because the
kernel PTY is the actual synchronization point — we never call
:mod:`ptyprocess` methods concurrently, we only call ``os.read`` and
``os.write`` on the master fd, which is safe.

#### def `__init__(proc: ptyprocess.PtyProcess)`

#### classmethod `is_available(cls) -> bool`

True if a PTY can be spawned on this platform.

#### classmethod `spawn(cls, argv: Sequence[str], cwd: Optional[str] = None, env: Optional[dict] = None, cols: int = 80, rows: int = 24) -> PtyBridge`

Spawn ``argv`` behind a new PTY and return a bridge.

Raises :class:`PtyUnavailableError` if the platform can't host a
PTY.  Raises :class:`FileNotFoundError` or :class:`OSError` for
ordinary exec failures (missing binary, bad cwd, etc.).

**异常**: `class`, `PtyUnavailableError`

#### property `pid(self) -> int`

#### def `is_alive(self) -> bool`

#### def `read(self, timeout: float = 0.2) -> Optional[bytes]`

Read up to 64 KiB of raw bytes from the PTY master.

Returns:
    * bytes — zero or more bytes of child output
    * empty bytes (``b""``) — no data available within ``timeout``
    * None — child has exited and the master fd is at EOF

Never blocks longer than ``timeout`` seconds.  Safe to call after
:meth:`close`; returns ``None`` in that case.

#### def `write(self, data: bytes) -> None`

Write raw bytes to the PTY master (i.e. the child's stdin).

#### def `resize(self, cols: int, rows: int) -> None`

Forward a terminal resize to the child via ``TIOCSWINSZ``.

Dimensions are clamped to a sane range first.  Some hosts report
garbage window sizes — the motivating case is WSL2, where xterm.js
in the dashboard ``/chat`` tab can pick up ``columns=131072,
rows=1`` from a broken winsize probe.  ``struct winsize`` packs each
field as an unsigned short (max 65535), so an unclamped 131072 would
raise ``struct.error`` (not ``OSError``) and break the resize path,
leaving the TUI laid out for a one-row / absurdly-wide screen —
which is what shows up as blank / disappearing text.

#### def `close(self) -> None`

Terminate the child (SIGTERM → 0.5s grace → SIGKILL) and close fds.

Idempotent.  Reaping the child is important so we don't leak
zombies across the lifetime of the dashboard process.


## hermes_cli.pty_session

### 模块文档

Keep-alive PTY sessions for dashboard terminals.

A PTY process outlives the WebSocket that created it: a single drain task
always reads the PTY into a bounded RingBuffer and forwards to the attached
socket when present. Reconnecting with the same opaque token replays the
buffer and resumes live. See
docs/superpowers/specs/2026-06-20-pty-keepalive-reattach-design.md.

### class RingBuffer

> 继承: `object` ｜ 方法数: 4（公开 3）

Keeps only the most recent ``capacity`` bytes appended to it.

#### def `__init__(capacity: int) -> None`

#### def `append(self, data: bytes) -> None`

#### def `snapshot(self) -> bytes`

#### property `truncated(self) -> bool`


### class PtySession

> 继承: `object` ｜ 方法数: 6（公开 4）

#### def `__init__(key: str, bridge, buffer_cap: int, read_timeout: float) -> None`

#### async def `start(self) -> None`

#### async def `attach(self, ws) -> None`

#### def `detach(self, ws) -> None`

#### async def `close(self) -> None`


### class RegistryFull

> 继承: `Exception` ｜ 方法数: 0（公开 0）


### class PtySessionRegistry

> 继承: `object` ｜ 方法数: 6（公开 4）

#### def `__init__(ttl: float, max_sessions: int, buffer_cap: int, read_timeout: float) -> None`

#### async def `attach_or_spawn(self, key: str, spawn: Callable[[], object]) -> Tuple[PtySession, bool]`

#### def `detach(self, key: str, ws) -> None`

#### async def `reap_idle(self, now: Optional[float] = None) -> None`

#### async def `close_all(self) -> None`


### 顶层函数

#### def `run_reaper(registry: PtySessionRegistry, interval: float = 60.0) -> None`

Periodically reap idle/dead keep-alive sessions. Cancelled on shutdown.


## hermes_cli.relaunch

### 模块文档

Unified self-relaunch for Hermes CLI.

Preserves critical flags (--tui, --dev, --profile, --model, etc.) across
process replacement so that ``hermes sessions browse`` or post-setup relaunch
doesn't silently drop the user's UI mode or other preferences.

Also works when ``hermes`` is not on PATH (e.g. ``nix run`` or ``python -m``).

### 顶层函数

#### def `resolve_hermes_bin() -> Optional[str]`

Find the hermes entry point.

Priority:
  1. ``sys.argv[0]`` if it resolves to a real executable.
  2. ``shutil.which("hermes")`` on PATH.
  3. ``None`` → caller should fall back to ``python -m hermes_cli.main``.

Windows note: ``os.access(path, os.X_OK)`` returns True for ``.py`` and
``.pyc`` files on Windows (the OS treats anything listed in PATHEXT as
executable, and Python files are often registered there).  But
``subprocess.run([script.py, ...])`` can't actually execute a .py
directly — CreateProcessW needs a real .exe, not a script associated
with the Python launcher.  On Windows we therefore skip the argv[0]
fast-path when it points at a .py file and fall through to either
``hermes.exe`` on PATH or the ``sys.executable -m hermes_cli.main``
fallback.

#### def `build_relaunch_argv(extra_args: Sequence[str], preserve_inherited: bool = True, original_argv: Optional[Sequence[str]] = None) -> list[str]`

Construct an argv list for replacing the current process with hermes.

Args:
    extra_args: Arguments to append (e.g. ``["--resume", id]``).
    preserve_inherited: Whether to carry over UI / behaviour flags
        tagged with ``inherit_on_relaunch`` in the parser.
    original_argv: The original argv to scan for flags (defaults to
        ``sys.argv[1:]``).

#### def `relaunch(extra_args: Sequence[str], preserve_inherited: bool = True, original_argv: Optional[Sequence[str]] = None) -> None`

Replace the current process with a fresh hermes invocation.

On POSIX we use ``os.execvp`` which replaces the running process with
the new one in place — same PID, no double-fork.  That's what the
relaunch contract wants: "run hermes again as if the user had typed
the new argv".

Windows has no native exec semantics — ``os.execvp`` on Windows
*emulates* exec by spawning the child and exiting the parent, but
only works when the target is a real Win32 executable.  Our target
is usually ``hermes.exe`` (a Python console-script shim that wraps
``python -m hermes_cli.main``) or a ``.cmd`` batch file, and both
raise ``OSError(8, "Exec format error")`` on Windows' execvp.

The Windows-correct pattern is: spawn the child with ``subprocess.run``
(which routes through ``cmd.exe`` via ``shell=False`` + PATHEXT resolution),
wait for it to exit, then propagate its exit code via ``sys.exit``.
That's functionally equivalent — the user sees "hermes exited, then
new hermes started" — just with two PIDs in play instead of one.


## hermes_cli.runtime_provider

### 模块文档

Shared runtime provider resolution for CLI, gateway, cron, and helpers.

### 顶层函数

#### def `resolve_requested_provider(requested: Optional[str] = None) -> str`

Resolve provider request from explicit arg, config, then env.

#### def `has_named_custom_provider(requested_provider: str) -> bool`

Return True when config defines a custom provider matching the request.

Thin public wrapper around :func:`_get_named_custom_provider` so other
modules (e.g. the cronjob tool) can decide whether a provider name will
actually resolve to a configured ``providers:`` / ``custom_providers:``
entry — without reaching into a private helper or duplicating the scan.

#### def `find_custom_provider_identity(base_url: str) -> Optional[str]`

Map an endpoint URL back to its canonical ``custom:<name>`` menu key.

Returns the ``custom:<normalized-name>`` slug of the first ``providers:``
/ ``custom_providers:`` entry whose base_url matches, or ``None`` when no
entry owns the URL.

Session persistence stores the agent's *resolved* provider, and for every
named custom endpoint that is the literal string ``"custom"`` — the entry
name is lost, and the api_key is deliberately never persisted. The
endpoint URL is the one durable fact that survives the round-trip, so
this reverse lookup lets persist/rebuild paths recover the entry identity
(and with it key_env/api_key/api_mode resolution via
:func:`_get_named_custom_provider`) instead of failing with
``auth_unavailable`` or silently rebuilding with placeholder credentials.

#### def `canonical_custom_identity(base_url: Optional[str] = None, config_provider: Optional[str] = None) -> Optional[str]`

Recover a routable ``custom:<name>`` identity for a bare custom provider.

The bare string ``"custom"`` is the *resolved billing class* shared by
every named ``providers:`` / ``custom_providers:`` entry — it is NOT a
routable provider identity (``resolve_runtime_provider("custom")`` falls
through to the OpenRouter default URL with no api_key, which surfaces to
the user as "No LLM provider configured").

Any code path that persists or restores a session's provider override
must run the resolved provider through this helper so a bare ``"custom"``
is upgraded back to its durable ``custom:<name>`` menu key. Two recovery
sources, in priority order:

1. ``base_url`` — reverse-lookup the entry that owns the endpoint URL
   (the one fact that always survives the persistence round-trip when a
   URL was recorded).
2. ``config_provider`` — the active ``config.model.provider`` (or its
   ``provider``/``HERMES_INFERENCE_PROVIDER`` equivalent). When the agent
   was built without a base_url on the override (the recurring
   Desktop/TUI regression vector), the configured provider is the only
   durable identity left, so fall back to it when it names a real entry.

Returns ``custom:<name>`` when a routable identity is recovered, else
``None`` (caller keeps whatever it had — bare ``"custom"`` only as a last
resort, e.g. a genuine ad-hoc endpoint with no config entry).

#### def `resolve_runtime_provider(requested: Optional[str] = None, explicit_api_key: Optional[str] = None, explicit_base_url: Optional[str] = None, target_model: Optional[str] = None) -> Dict[str, Any]`

Resolve runtime provider credentials for agent execution.

target_model: Optional override for model_cfg.get("default") when
computing provider-specific api_mode (e.g. OpenCode Zen/Go where different
models route through different API surfaces). Callers performing an
explicit mid-session model switch should pass the new model here so
api_mode is derived from the model they are switching TO, not the stale
persisted default. Other callers can leave it None to preserve existing
behavior (api_mode derived from config).

**异常**: `ValueError`, `AuthError`

#### def `format_runtime_provider_error(error: Exception) -> str`


## hermes_cli.secret_prompt

### 模块文档

Secret input prompts with masked typing feedback.

### 顶层函数

#### def `masked_secret_prompt(prompt: str, mask: str = '*') -> str`

Prompt for a secret while showing masked typing feedback.

Falls back to ``getpass.getpass`` when stdin/stdout are not interactive or
when raw terminal handling is unavailable.


## hermes_cli.secrets_cli

### 模块文档

CLI handlers for ``hermes secrets bitwarden ...``.

Subcommands:
    setup    — interactive wizard: install bws, prompt for token + project, test fetch
    status   — show current config + binary version + last fetch outcome
    sync     — run a fetch right now and show what would be applied (dry-run friendly)
    disable  — flip ``secrets.bitwarden.enabled`` to False
    install  — just download the bws binary (no token / project required)

### 顶层函数

#### def `register_cli(parent_parser: argparse.ArgumentParser) -> None`

Attach the ``bitwarden`` subcommand tree to a parent parser.

Called from ``hermes_cli.main`` as part of building the top-level
``hermes secrets`` parser.

#### def `cmd_setup(args: argparse.Namespace) -> int`

#### def `cmd_status(args: argparse.Namespace) -> int`

#### def `cmd_sync(args: argparse.Namespace) -> int`

#### def `cmd_disable(args: argparse.Namespace) -> int`

#### def `cmd_install(args: argparse.Namespace) -> int`


## hermes_cli.security_advisories

### 模块文档

Security advisory checker for Hermes Agent.

Detects known-compromised Python packages installed in the active venv
(supply-chain attacks like the Mini Shai-Hulud worm of May 2026 that
poisoned ``mistralai 2.4.6`` on PyPI) and surfaces remediation guidance to
the user.

Design goals:

- **Cheap.** A single ``importlib.metadata.version()`` call per advisory
  package. Safe to run on every CLI startup.
- **Loud when it matters, silent otherwise.** If no compromised package is
  installed, the user sees nothing.
- **Acknowledgeable.** Once the user has read and acted on an advisory they
  can dismiss it via ``hermes doctor --ack <id>``; the ack is persisted to
  ``config.security.acked_advisories`` and survives restart.
- **Extensible.** Adding a new advisory is one entry in ``ADVISORIES``;
  adding a new compromised version is a one-line edit. No code changes
  needed when the next worm hits.

The check is invoked from three places:

1. ``hermes doctor`` (and ``hermes doctor --ack <id>``)
2. CLI startup banner (one short line, then full guidance via
   ``hermes doctor``)
3. Gateway startup (logged to gateway.log; first interactive message gets
   a one-line operator banner)

This module is intentionally dependency-free beyond the stdlib so it can
run in environments where the rest of Hermes failed to import.

### class Advisory

> 继承: `object` ｜ 方法数: 0（公开 0）

One security advisory entry.

Attributes:
    id: stable identifier used for acks (e.g. ``shai-hulud-2026-05``).
        Lowercase-hyphen, never reused.
    title: one-line headline shown in banners.
    summary: 1-3 sentence description of what was compromised and how.
    url: reference URL (Socket advisory, GitHub advisory, PyPI page).
    compromised: tuple of ``(package_name, frozenset_of_versions)``
        pairs. Empty frozenset means "any version of this package is
        considered suspect" — use sparingly.
    remediation: ordered list of steps the user should take. First step
        should be the uninstall command; subsequent steps the credential
        audit / rotation guidance.
    published: ISO date string for sort order.


### class AdvisoryHit

> 继承: `object` ｜ 方法数: 0（公开 0）

One package-version match against an advisory.


### 顶层函数

#### def `detect_compromised(advisories: Iterable[Advisory] = ADVISORIES) -> list[AdvisoryHit]`

Scan installed packages and return all advisory hits.

A "hit" means an advisory's listed package is installed AND the version
is in the compromised set (or the compromised set is empty, meaning
*any* version is suspect).

#### def `get_acked_ids() -> set[str]`

Return the set of advisory IDs the user has dismissed.

Returns an empty set if config can't be loaded (don't block startup
just because config is broken — the advisory will keep firing until
config is repaired, which is fine).

#### def `ack_advisory(advisory_id: str) -> bool`

Persist an ack for ``advisory_id``. Returns True on success.

Idempotent — acking an already-acked ID is a no-op.

#### def `filter_unacked(hits: list[AdvisoryHit]) -> list[AdvisoryHit]`

Return only hits whose advisories the user has not dismissed.

#### def `short_banner_lines(hits: list[AdvisoryHit]) -> list[str]`

Return 1-3 short lines suitable for a startup banner.

Caller is responsible for color/styling. Always names the worst hit
explicitly so the user knows what's wrong without running doctor.

#### def `full_remediation_text(hit: AdvisoryHit) -> list[str]`

Return a multi-line block describing the advisory + remediation.

#### def `hits_due_for_banner(hits: list[AdvisoryHit], repeat_hours: int = _BANNER_REPEAT_HOURS) -> list[AdvisoryHit]`

Return only hits whose banner is due (not acked, not recently shown).

Side effect: stamps the banner cache for any hit that's about to be
shown. Callers should subsequently render the result.

#### def `render_doctor_section(hits: list[AdvisoryHit]) -> tuple[bool, list[str]]`

Render the security-advisory section for ``hermes doctor``.

Returns ``(has_problems, lines)``. Caller is responsible for printing
with whatever color scheme it uses.

#### def `startup_banner(hits: list[AdvisoryHit]) -> Optional[str]`

Return a printable startup banner, or None if nothing is due.

Updates the banner cache as a side effect (so the next call within
24h returns None for the same hit).

#### def `gateway_log_message(hits: list[AdvisoryHit]) -> Optional[str]`

Return a one-line log message for gateway operators, or None.


## hermes_cli.security_audit

### 模块文档

On-demand supply-chain audit for Hermes Agent installs.

Scans three surfaces a Hermes user actually controls and we can map to
upstream advisories without auth or extra binaries:

1. The Hermes venv (every PyPI dist via ``importlib.metadata``).
2. Python deps declared by user-installed plugins under ``~/.hermes/plugins``
   (``requirements.txt`` + ``pyproject.toml`` best-effort pin extraction).
3. MCP servers wired in ``config.yaml`` whose ``command/args`` look like
   ``npx -y <pkg>@<ver>`` or ``uvx <pkg>==<ver>``.

Vulnerabilities are looked up against OSV.dev (``api.osv.dev/v1/querybatch``
+ ``/v1/vulns/{id}``). Single-shot, on-demand, never daily — see the design
notes in ``references/security-disclosure-triage.md``.

Out of scope on purpose: global pip/npm, editor/browser extensions,
daily background scans, auto-blocking installs.

### class Component

> 继承: `object` ｜ 方法数: 0（公开 0）

A single (name, version, ecosystem) tuple discovered on disk.


### class Vulnerability

> 继承: `object` ｜ 方法数: 0（公开 0）


### class Finding

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `run_audit(skip_venv: bool = False, skip_plugins: bool = False, skip_mcp: bool = False, hermes_home: Optional[Path] = None) -> list[Finding]`

Discover components, query OSV, return findings sorted by severity desc.

#### def `cmd_security_audit(args: argparse.Namespace) -> int`

Implementation of `hermes security audit`.


## hermes_cli.security_audit_startup

### 模块文档

Startup security posture audit (warn-on-load, never blocks).

Surfaces dangerous host / deployment posture at process start so operators
get an at-a-glance "you're exposed" signal. Motivated by the June 2026
MCP-config persistence campaign, where compromised boxes ran as root with an
exposed dashboard / API server and no firewall — and nothing ever told the
operator. These checks are advisory: they emit ``logger.warning`` records
and return human-readable strings; they never raise or block startup.

Checks (each is independent and fail-safe — any internal error is swallowed
and simply yields no finding):

1. Running as root (POSIX uid 0).
2. SSH daemon present with password authentication enabled.
3. Running inside a container with no persistent volume mount over the
   HERMES_HOME data dir (state is ephemeral — lost on container restart).
4. A network-accessible gateway listener (dashboard / API server) with no
   authentication configured.

Cross-platform: the root and SSH checks are POSIX-only and no-op on Windows.
Everything is best-effort and read-only.

### 顶层函数

#### def `run_security_audit(hermes_home: Optional[Path] = None, config: Optional[dict] = None) -> list[str]`

Run all checks and return a list of human-readable warning strings.

Pure: no logging, no side effects. Each check is independently
fail-safe. Used directly by tests; the logging wrapper is
:func:`log_startup_security_warnings`.

#### def `log_startup_security_warnings(hermes_home: Optional[Path] = None, config: Optional[dict] = None, force: bool = False) -> list[str]`

Run the audit once per process and emit each finding via logger.warning.

Returns the findings (also for tests). Never raises. Idempotent unless
``force=True`` (used by tests).


## hermes_cli.send_cmd

### 模块文档

CLI subcommand: ``hermes send`` — pipe text from shell scripts to any
configured messaging platform (Telegram, Discord, Slack, Signal, SMS, etc.).

This is a thin wrapper around ``tools.send_message_tool.send_message_tool``
that exposes its functionality as a standalone CLI entry point so ops
scripts, cron jobs, CI hooks, and monitoring daemons can reuse the gateway's
already-configured credentials without having to reimplement each platform's
REST API client.

Design notes:

* No LLM, no agent loop — the subcommand just resolves arguments, reads the
  message body, calls the shared tool function, and prints/returns the
  result. It is intentionally fast, cheap, and side-effect-only.
* For platforms that send via bot token (Telegram, Discord, Slack, Signal,
  SMS, WhatsApp-CloudAPI, …) no running gateway is required. The tool
  talks directly to each platform's REST endpoint. For platforms that rely
  on a persistent adapter connection (plugin platforms, Matrix in some
  modes, …) a live gateway is needed; the underlying tool surfaces that
  error to the caller.
* Exit codes follow the classic Unix convention:
    0 — delivery (or list) succeeded
    1 — delivery failed at the platform level
    2 — usage / argument / config error (argparse already uses 2)

### 顶层函数

#### def `cmd_send(args: argparse.Namespace) -> None`

Entry point wired into the top-level argparse dispatcher.

#### def `register_send_subparser(subparsers) -> argparse.ArgumentParser`

Create the ``send`` subparser and return it.

Kept as a standalone function so the top-level parser builder can wire
it in next to the other messaging subcommands without cluttering
``_parser.py`` or ``main.py``.


## hermes_cli.service_manager

### 模块文档

Abstract service manager interface.

Wraps the existing systemd (Linux host), launchd (macOS host), Windows
Scheduled Task (native Windows host), and s6 (container) backends behind
a common Protocol. Only the s6 backend supports runtime registration
(for per-profile gateways) — host backends raise NotImplementedError
from those methods, and callers MUST check supports_runtime_registration()
before invoking them.

Host-side call sites (setup wizard, uninstall, status) continue to use
the existing module-level functions in hermes_cli.gateway and
hermes_cli.gateway_windows directly. This protocol is a thin facade
used by new code that needs to be backend-agnostic — specifically the
profile create/delete hooks (Phase 4) and the s6 dispatch path in
``hermes gateway start/stop/restart`` when running inside a container.

### class ServiceManager

> 继承: `Protocol` ｜ 方法数: 8（公开 8）

Abstract interface for init-system-specific service operations.

Lifecycle methods (start / stop / restart / is_running) are
implemented by every backend. Runtime registration
(register_profile_gateway / unregister_profile_gateway /
list_profile_gateways) is implemented only by the s6 backend —
callers MUST check ``supports_runtime_registration()`` before
invoking the registration methods.

#### def `start(self, name: str) -> None`

#### def `stop(self, name: str) -> None`

#### def `restart(self, name: str) -> None`

#### def `is_running(self, name: str) -> bool`

#### def `supports_runtime_registration(self) -> bool`

#### def `register_profile_gateway(self, profile: str, extra_env: dict[str, str] | None = None, start_now: bool = True) -> None`

#### def `unregister_profile_gateway(self, profile: str) -> None`

#### def `list_profile_gateways(self) -> list[str]`


### class SystemdServiceManager

> 继承: `_RegistrationUnsupportedMixin` ｜ 方法数: 4（公开 4）

Thin wrapper around the ``systemd_*`` functions in hermes_cli.gateway.

Existing host call sites continue to use those functions directly;
this wrapper exists for new code that needs to be backend-agnostic
(the Phase 4 profile create/delete hooks).

#### def `start(self, name: str) -> None`

#### def `stop(self, name: str) -> None`

#### def `restart(self, name: str) -> None`

#### def `is_running(self, name: str) -> bool`


### class LaunchdServiceManager

> 继承: `_RegistrationUnsupportedMixin` ｜ 方法数: 4（公开 4）

Thin wrapper around the ``launchd_*`` functions in hermes_cli.gateway.

#### def `start(self, name: str) -> None`

#### def `stop(self, name: str) -> None`

#### def `restart(self, name: str) -> None`

#### def `is_running(self, name: str) -> bool`


### class WindowsServiceManager

> 继承: `_RegistrationUnsupportedMixin` ｜ 方法数: 5（公开 5）

Thin wrapper around ``hermes_cli.gateway_windows`` (Scheduled Task /
Startup-folder fallback).

The native Windows backend uses a Scheduled Task rather than a true
init-system service, but for protocol purposes the lifecycle is the
same: start / stop / restart / is_running. ``install`` accepts a
handful of Windows-specific kwargs (start_now, start_on_login,
elevated_handoff) that are passed straight through — non-Windows
callers should never invoke ``install`` on this wrapper.

#### def `install(self, force: bool = False, start_now: bool | None = None, start_on_login: bool | None = None, elevated_handoff: bool = False) -> None`

#### def `start(self, name: str) -> None`

#### def `stop(self, name: str) -> None`

#### def `restart(self, name: str) -> None`

#### def `is_running(self, name: str) -> bool`


### class S6Error

> 继承: `RuntimeError` ｜ 方法数: 1（公开 0）

Base error for S6ServiceManager lifecycle failures.

Concrete subclasses carry the slot name (and, where useful, the
underlying subprocess output) so the CLI can render an actionable
message instead of leaking a raw ``CalledProcessError`` traceback.

#### def `__init__(message: str, service: str | None = None) -> None`


### class GatewayNotRegisteredError

> 继承: `S6Error` ｜ 方法数: 1（公开 0）

Raised when a lifecycle method targets a slot that doesn't exist.

Most commonly: ``hermes -p typo gateway start`` when no profile
``typo`` exists. Carries the unprefixed profile name (not the
full ``gateway-<profile>`` service-dir name) so callers can phrase
a user-facing message like "no such gateway 'typo'".

#### def `__init__(profile: str) -> None`


### class S6CommandError

> 继承: `S6Error` ｜ 方法数: 1（公开 0）

Raised when an s6 command fails for a reason other than a
missing slot — e.g. permission denied on the supervise control
FIFO, or s6-svc returning a non-zero exit for an unexpected
reason. Carries the stderr from the failing command so callers
can surface it.

#### def `__init__(service: str, action: str, returncode: int, stderr: str) -> None`


### class S6ServiceManager

> 继承: `object` ｜ 方法数: 16（公开 8）

Per-profile gateway supervision via s6-overlay.

Only handles runtime-registered services under
``S6_DYNAMIC_SCANDIR``. Static services (main-hermes, dashboard)
are managed by s6-rc at image-build time and are out of scope.

#### def `__init__(scandir: Path = S6_DYNAMIC_SCANDIR) -> None`

#### def `start(self, name: str) -> None`

Bring up a registered service (``s6-svc -u``).

Raises:
    GatewayNotRegisteredError: no service directory for ``name``.
    S6CommandError: s6-svc exited non-zero for any other reason
        (permission denied on the supervise FIFO, timeout, etc.).

**异常**: `GatewayNotRegisteredError`, `S6CommandError`

#### def `stop(self, name: str) -> None`

Bring down a registered service (``s6-svc -d``).

Writes a planned-stop marker naming the supervised gateway PID
BEFORE sending the down command, so the gateway's shutdown
handler recognises this SIGTERM as an operator-initiated stop
and persists ``gateway_state=stopped`` (respecting the explicit
intent). Without the marker, an intentional ``hermes gateway
stop`` is indistinguishable from the container/s6 SIGTERM sent on
``docker restart``; the latter must NOT persist ``stopped`` or
container_boot refuses to auto-start on the next boot (#42675).
The marker write is best-effort — a failure only means the stop
is treated as signal-initiated, which is the safe fallback.

Raises:
    GatewayNotRegisteredError: no service directory for ``name``.
    S6CommandError: s6-svc exited non-zero for any other reason.

**异常**: `GatewayNotRegisteredError`, `S6CommandError`

#### def `restart(self, name: str) -> None`

Restart a registered service (``s6-svc -t`` = SIGTERM).

Raises:
    GatewayNotRegisteredError: no service directory for ``name``.
    S6CommandError: s6-svc exited non-zero for any other reason.

**异常**: `GatewayNotRegisteredError`, `S6CommandError`

#### def `is_running(self, name: str) -> bool`

True iff ``s6-svstat`` reports the service as up.

#### def `supports_runtime_registration(self) -> bool`

#### def `register_profile_gateway(self, profile: str, extra_env: dict[str, str] | None = None, start_now: bool = True) -> None`

Create the s6 service directory for a profile gateway.

Triggers ``s6-svscanctl -a`` so s6-svscan picks the new directory
up immediately.  When *start_now* is ``True`` (the default) the
service starts immediately; when ``False`` a ``down`` marker file
is written so s6-supervise leaves the service stopped until the
user explicitly runs ``hermes -p <profile> gateway start``.

Raises:
    ValueError: if the profile name is invalid or the service
        directory already exists.
    RuntimeError: if ``s6-svscanctl`` fails.

**异常**: `ValueError`, `RuntimeError`

#### def `unregister_profile_gateway(self, profile: str) -> None`

Stop the profile gateway service and remove its directory.

Idempotent: absent services are a no-op. Best-effort stop +
wait-for-down before removal so the running gateway process
gets a chance to shut down cleanly before its service dir
disappears.

Teardown ordering matters: ``s6-svscanctl -an`` is fired
**before** ``rmtree`` so s6-svscan reaps the supervise child
process (releasing its handle on ``supervise/lock`` and the
regular files inside the supervise dir), giving us a clean
directory to remove. Without the reap-first ordering, the
rmtree races s6-supervise on a set of root-owned files inside
the supervise dir and the dir is left half-removed.

#### def `list_profile_gateways(self) -> list[str]`

Return the profile names of all currently-registered gateway services.

Filters the scandir to entries that match the ``gateway-`` prefix.
Other services (e.g. ``s6-linux-init-shutdownd``) are ignored.


### 顶层函数

#### def `validate_profile_name(name: str) -> None`

Raise ValueError if ``name`` is not usable as a profile name.

Profile names are used as s6 service directory names, so they must
match a conservative subset of filesystem-safe characters. Reject
empty strings, uppercase, paths-traversal sequences, and anything
longer than s6's default ``name_max``.

**异常**: `ValueError`

#### def `detect_service_manager() -> ServiceManagerKind`

Detect which service manager is available in this environment.

Returns:
    "s6" — s6-svscan is PID 1 (s6-overlay image; Docker, Podman, or a
           Fly Firecracker microVM)
    "windows" — native Windows host
    "launchd" — macOS host
    "systemd" — Linux host with a working user/system bus
    "none" — anything else (Termux, sandbox shells, etc.)

This function does NOT replace ``supports_systemd_services()`` —
host call sites continue to use that. It exists for new backend-
agnostic code (profile create/delete hooks, the s6 dispatch path
in ``hermes gateway start/stop/restart``).

#### def `get_service_manager() -> ServiceManager`

Return the ServiceManager instance for the current environment.

Raises:
    RuntimeError: when no supported backend is available.

**异常**: `RuntimeError`


## hermes_cli.session_export

### 模块文档

Shared renderers for session export commands.

The CLI, dashboard, and slash-command surfaces all deal with the same
session-shaped data: a session dict with a ``messages`` list. Keep filtering
and human-readable rendering here so each surface only has to load sessions
and write bytes.

### 顶层函数

#### def `normalize_export_format(fmt: str) -> ExportFormat`

Return the canonical export format name.

**异常**: `ValueError`

#### def `normalize_export_only(only: Optional[str]) -> Optional[ExportOnly]`

Return the canonical export filter name.

**异常**: `ValueError`

#### def `render_sessions_export(sessions: Iterable[Dict[str, Any]], fmt: str = 'jsonl', only: Optional[str] = None) -> str`

Render exported sessions in a stable, reusable format.

``fmt=jsonl`` with no filter intentionally preserves the legacy shape:
one full session object per line. ``only=user-prompts`` switches the unit
of export to one prompt record per line so the output is easy to pipe into
review, memory-ingestion, or prompt-library tooling.

#### def `export_record_count(sessions: Iterable[Dict[str, Any]], only: Optional[str] = None) -> Tuple[int, str]`

Return ``(count, noun)`` for status messages after an export.

#### def `iter_user_prompt_records(sessions: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]`

Yield one normalized record for each user-authored prompt.


## hermes_cli.session_export_html

### 模块文档

HTML Export generator for Hermes sessions.
Generates a standalone, beautiful HTML file with all messages embedded.
Supports single and multi-session exports with a professional sidebar.
No remote dependencies.
Enhanced with UI-UX-PRO-MAX design intelligence.

### 顶层函数

#### def `generate_multi_session_html_export(sessions: List[Dict[str, Any]]) -> str`

#### def `generate_html_export(session_data: Dict[str, Any]) -> str`

Legacy wrapper for single session export.


## hermes_cli.session_export_md

### 模块文档

Markdown/QMD export helpers for Hermes sessions.

This module is intentionally filesystem-only: it formats already-exported
SessionDB dictionaries and writes them to user-selected export directories. It
must not mutate state.db or call delete/prune/archive APIs.

### 顶层函数

#### def `render_session_markdown(session: dict[str, Any], fmt: str = 'md', include_verification: bool = True) -> str`

Render a SessionDB export dictionary as Markdown/QMD text.

**异常**: `ValueError`

#### def `safe_session_filename(session: dict[str, Any], fmt: str = 'md') -> str`

Return a deterministic, path-safe filename for a session export.

**异常**: `ValueError`

#### def `file_sha256(path: Path | str) -> str`

#### def `verify_export_file(path: Path | str, session: dict[str, Any]) -> tuple[bool, str]`

#### def `redact_session_data(session: dict[str, Any]) -> dict[str, Any]`

Return a deep copy of a session export dict with secrets redacted.

Runs every message's content and tool-call arguments through the
force-mode redaction pass (``agent.redact.redact_sensitive_text``), so
API keys, tokens, and credentials that appeared in tool output never
land in plaintext export files. Force mode ignores the user's global
``security.redact_secrets`` preference — an explicit ``--redact`` export
must never emit raw secrets.

#### def `write_session_markdown(session: dict[str, Any], output_dir: Path | str, fmt: str = 'md', force: bool = False) -> Path`

Write a Markdown/QMD export file and return its path.

Raises FileExistsError when the destination exists and force=False.

**异常**: `FileExistsError`

#### def `append_manifest_entry(output_dir: Path | str, session: dict[str, Any], path: Path | str, fmt: str) -> Path`


## hermes_cli.session_filters

### 模块文档

Shared time/filter parsing for `hermes sessions prune` / `archive`.

Turns user-friendly CLI values into the epoch bounds and filter kwargs
consumed by ``SessionDB.prune_sessions`` / ``archive_sessions`` /
``list_prune_candidates``.

Two value shapes are accepted anywhere a point in time is expected:

* Durations (relative to now): ``5h``, ``30m``, ``2d``, ``1w`` — and, for
  backward compatibility with the original ``--older-than N`` flag, a bare
  integer which means **days**.
* Absolute timestamps: ``2026-07-05``, ``2026-07-05 14:30``,
  ``2026-07-05T14:30:00`` (any ISO-8601 form ``datetime.fromisoformat``
  understands; naive values are interpreted in local time).

### 顶层函数

#### def `parse_duration_seconds(value: str) -> Optional[float]`

Parse ``5h`` / ``30m`` / ``2d`` / ``1w`` / ``90`` (bare = days) into
seconds. Returns None when the value doesn't look like a duration.

#### def `parse_point_in_time(value: str, flag: str) -> float`

Parse a CLI time value into an epoch timestamp.

Durations are interpreted as "that long ago" (``5h`` → now − 5 hours).
Absolute ISO timestamps are returned as-is (naive = local time).
Raises ``ValueError`` with a user-facing message on unparseable input.

**异常**: `ValueError`

#### def `format_epoch(ts: Optional[float]) -> str`

Render an epoch timestamp as a short local-time string.

#### def `build_prune_filters(args: Any) -> Dict[str, Any]`

Translate argparse Namespace flags into SessionDB filter kwargs.

Understands: ``--older-than``, ``--newer-than``, ``--before``,
``--after``, ``--source``, ``--title``, ``--end-reason``, ``--cwd``,
``--min-messages``, ``--max-messages``, ``--archived``/``--no-archived``.

``--before``/``--older-than`` both set the upper bound (started_before);
``--after``/``--newer-than`` both set the lower bound (started_after).
When both a duration flag and an absolute flag target the same bound,
the tighter (more restrictive) bound wins.

Raises ``ValueError`` on unparseable values or an empty/inverted window.

**异常**: `ValueError`

#### def `describe_filters(filters: Dict[str, Any]) -> str`

Human-readable summary of active filters for confirmation prompts.


## hermes_cli.session_listing

### 模块文档

Shared session-listing helpers for CLI and gateway slash surfaces.

### 顶层函数

#### def `parse_session_listing_args(raw_args: str) -> tuple[bool, bool, str, str | None]`

Parse `/sessions`-style args into listing flags, a resume target, and a search query.

Returns ``(include_all_sources, include_unnamed, target, search_query)``.
``list``/``ls`` and ``browse`` are display aliases; ``all``/``--all`` widens
source scope; ``full``/``--full`` keeps unnamed sessions in the listing.
``search``/``find`` makes the remaining words a search query —
``search_query`` is ``None`` when search wasn't requested and ``""`` when it
was requested without a query. Flags are only honored before the first
positional word, so titles containing e.g. "all" aren't misparsed. Anything
else is treated as a target so `/sessions <id-or-title>` can delegate to
`/resume`.

#### def `query_session_listing(session_db: Any, source: str | None, current_session_id: str | None = None, include_all_sources: bool = False, include_unnamed: bool = False, search_query: str | None = None, limit: int = 10, exclude_sources: list[str] | None = None) -> list[dict[str, Any]]`

Return session rows for interactive listing surfaces.

This is the shared selection policy behind CLI/gateway session browsing:
source-scoped by default, optionally global, hide unnamed sessions unless
the caller asks for a full listing, and never include the current session.
With ``search_query``, rows are filtered by title/id match (SQL-level, see
``SessionDB.list_sessions_rich``) and ordered by most-recent activity;
unnamed sessions stay visible since an id match may be the only handle.

#### def `format_gateway_session_listing(rows: list[dict[str, Any]], include_source: bool = False, title: str = 'Sessions') -> str`

Render a compact Markdown-ish session list for gateway messengers.


## hermes_cli.session_recap

### 模块文档

Session recap — summarize what's happened in the current session.

Inspired by Claude Code's `/recap` command (v2.1.114, April 2026), which
shows a one-line summary of what happened while a terminal was unfocused
so users juggling multiple sessions can re-orient quickly.

Source: https://code.claude.com/docs/en/whats-new/2026-w17

Differences from Claude Code:
    - Pure local computation from the in-memory conversation history. No
      LLM call, no auxiliary model, no prompt-cache invalidation. A
      recap should be instant and free.
    - Works unchanged on CLI and every gateway platform (Telegram,
      Discord, Slack, …) because both call into the same ``build_recap``
      helper. Claude Code only shows this on the CLI.
    - Tailored to hermes-agent's tool vocabulary (``terminal``, ``patch``,
      ``write_file``, ``delegate_task``, ``browser_*``, ``web_*``) — the
      recap surfaces which classes of work were most active.

### 顶层函数

#### def `build_recap(messages: Sequence[Mapping[str, Any]], session_title: Optional[str] = None, session_id: Optional[str] = None, platform: Optional[str] = None) -> str`

Build a multi-line recap of recent activity.

Inputs:
    messages: the full conversation history as a list of
        chat-completion-style dicts (``role``, ``content``,
        ``tool_calls``, …).
    session_title: optional human title (from SessionDB).
    session_id: optional session id.
    platform: optional hint (``"cli"``, ``"telegram"``, …). Does not
        change behavior today but is accepted for forward compat.

The output is plain text designed to render well in both a terminal
(with 80-col wrapping) and a gateway message bubble.


## hermes_cli.setup

### 模块文档

Interactive setup wizard for Hermes Agent.

Modular wizard with independently-runnable sections:
  1. Model & Provider — choose your AI provider and model
  2. Terminal Backend — where your agent runs commands
  3. Agent Settings — iterations, compression, session reset
  4. Messaging Platforms — connect Telegram, Discord, etc.
  5. Tools — configure TTS, web search, image generation, etc.

Config files are stored in ~/.hermes/ for easy access.

### 顶层函数

#### def `print_header(title: str)`

Print a section header.

#### def `is_interactive_stdin() -> bool`

Return True when stdin looks like a usable interactive TTY.

#### def `print_noninteractive_setup_guidance(reason: str | None = None) -> None`

Print guidance for headless/non-interactive setup flows.

#### def `prompt(question: str, default: str = None, password: bool = False) -> str`

Prompt for input with optional default.

#### def `prompt_choice(question: str, choices: list, default: int = 0, description: str | None = None) -> int`

Prompt for a choice from a list with arrow key navigation.

Escape keeps the current default (skips the question).
Ctrl+C exits the wizard.

#### def `is_noninteractive() -> bool`

True when no human is available to answer a prompt.

The dashboard/desktop spawn CLI actions with ``stdin=DEVNULL`` and
``HERMES_NONINTERACTIVE=1`` (see ``hermes_cli/web_server.py``). In that
context an ``input()`` raises ``EOFError`` immediately, so a prompt that
aborts on EOF kills the spawned action — this is what made the desktop
"restart gateway" fail when the Windows gateway service was not yet
installed (the start path asks "Install it now?" with no one to answer).
Honour the explicit env flag here so callers fall back to their default.

#### def `prompt_yes_no(question: str, default: bool = True) -> bool`

Prompt for yes/no. Ctrl+C exits, empty input returns default.

Non-interactive callers (``HERMES_NONINTERACTIVE=1`` or a closed/redirected
stdin) have no one to answer, so fall back to ``default`` instead of
aborting the whole process.

#### def `prompt_checklist(title: str, items: list, pre_selected: list = None) -> list`

Display a multi-select checklist and return the indices of selected items.

Each item in `items` is a display string. `pre_selected` is a list of
indices that should be checked by default. A "Continue →" option is
appended at the end — the user toggles items with Space and confirms
with Enter on "Continue →".

Falls back to a numbered toggle interface when curses is
unavailable.

Returns:
    List of selected indices (not including the Continue option).

#### def `setup_model_provider(config: dict, quick: bool = False)`

Configure the inference provider and default model.

Delegates to ``cmd_model()`` (the same flow used by ``hermes model``)
for provider selection, credential prompting, and model picking.
This ensures a single code path for all provider setup — any new
provider added to ``hermes model`` is automatically available here.

When *quick* is True, skips credential rotation, vision, and TTS
configuration — used by the streamlined first-time quick setup.

#### def `setup_tts(config: dict)`

Standalone TTS setup (for 'hermes setup tts').

#### def `setup_terminal_backend(config: dict)`

Configure the terminal execution backend.

#### def `setup_agent_settings(config: dict)`

Configure agent behavior: iterations, progress display, compression, session reset.

#### def `setup_gateway(config: dict)`

Configure messaging platform integrations.

#### def `setup_tools(config: dict, first_install: bool = False)`

Configure tools — delegates to the unified tools_command() in tools_config.py.

Both `hermes setup tools` and `hermes tools` use the same flow:
platform selection → toolset toggles → provider/API key configuration.

Args:
    first_install: When True, uses the simplified first-install flow
        (no platform menu, prompts for all unconfigured API keys).

#### def `run_setup_wizard(args)`

Run the interactive setup wizard.

Supports full, quick, and section-specific setup:
  hermes setup           — full or quick (auto-detected)
  hermes setup model     — just model/provider
  hermes setup tts       — just text-to-speech
  hermes setup terminal  — just terminal backend
  hermes setup gateway   — just messaging platforms
  hermes setup tools     — just tool configuration
  hermes setup agent     — just agent settings


## hermes_cli.setup_whatsapp_cloud

### 模块文档

Interactive setup wizard for the WhatsApp Cloud API adapter.

Entry point: ``hermes whatsapp-cloud`` (dispatched from
``cmd_whatsapp_cloud`` in ``hermes_cli/main.py``).

Walks the user through the 6 credentials Meta requires + recipient
allowlist, auto-generates the verify token, and prints exact follow-up
instructions for the parts that can't happen inside the wizard process
(starting cloudflared, starting the gateway, configuring Meta's
webhook dashboard, adding their phone to the recipient list).

Heavy emphasis on field-shape validation to catch the most common
configuration mistakes:

- Putting the actual phone number in ``WHATSAPP_CLOUD_PHONE_NUMBER_ID``
  (the field expects Meta's 15-17 digit internal ID, not a phone number).
  This is the #1 trap — caught us during Phase 3 live testing.
- Pasting tokens with trailing whitespace.
- Pasting an OpenAI / Slack / GitHub key by mistake.
- Confusing App ID with WABA ID with Phone Number ID.

Each prompt has contextual help showing exactly where to find the value
in Meta's App Dashboard, with a one-line description and the field's
expected shape ("starts with EAA", "15-17 digits", "32 hex chars", etc.).

The wizard intentionally does NOT smoke-test the webhook itself — the
Hermes gateway and the cloudflared tunnel both run in separate
processes the user starts AFTER this wizard exits, so any in-wizard
probe would fail by design. Instead the final SETUP COMPLETE block
prints the exact curl command the user can run from a third terminal
to verify the loop end-to-end once everything's running.

### 顶层函数

#### def `run_whatsapp_cloud_setup() -> int`

Interactive wizard for the WhatsApp Cloud API adapter.

Returns 0 on full success, 1 on user abort, 2 on partial completion
(some fields written but the user bailed before finishing).


## hermes_cli.skills_config

### 模块文档

Skills configuration for Hermes Agent.
`hermes skills` enters this module.

Toggle individual skills or categories on/off, globally or per-platform.
Config stored in ~/.hermes/config.yaml under:

  skills:
    disabled: [skill-a, skill-b]          # global disabled list
    platform_disabled:                    # per-platform overrides
      telegram: [skill-c]
      cli: []

### 顶层函数

#### def `get_disabled_skills(config: dict, platform: Optional[str] = None) -> Set[str]`

Return disabled skill names: the global list unioned with the
platform-specific list when a platform is given.

A globally-disabled skill stays disabled on every platform, so the
platform list adds to the global list rather than replacing it. This
mirrors ``agent.skill_utils.get_disabled_skill_names``.

#### def `save_disabled_skills(config: dict, disabled: Set[str], platform: Optional[str] = None)`

Persist disabled skill names to config.

#### def `skills_command(args = None)`

Entry point for `hermes skills`.


## hermes_cli.skills_hub

### 模块文档

Skills Hub CLI — Unified interface for the Hermes Skills Hub.

Powers both:
  - `hermes skills <subcommand>` (CLI argparse entry point)
  - `/skills <subcommand>` (slash command in the interactive chat)

All logic lives in shared do_* functions. The CLI entry point and slash command
handler are thin wrappers that parse args and delegate.

### 顶层函数

#### def `do_search(query: str, source: str = 'all', limit: int = 10, console: Optional[Console] = None, as_json: bool = False) -> None`

Search registries and display results as a Rich table.

When ``as_json=True`` writes a JSON array of result records to stdout
(one object per skill: ``name``, ``identifier``, ``source``,
``trust_level``, ``description``) and skips the table render. This is
the scripting / copy-paste handle: the full identifier is always
intact, even for browse-sh slugs that the table would otherwise wrap.

#### def `do_browse(page: int = 1, page_size: int = 20, source: str = 'all', console: Optional[Console] = None) -> None`

Browse all available skills across registries, paginated.

Official skills are always shown first, regardless of source filter.

#### def `do_install(identifier: str, category: str = '', force: bool = False, console: Optional[Console] = None, skip_confirm: bool = False, invalidate_cache: bool = True, name_override: str = '') -> None`

Fetch, quarantine, scan, confirm, and install a skill.

``name_override`` lets non-interactive callers (slash commands, gateway,
scripts) supply a skill name when the upstream SKILL.md lacks a valid
``name:`` frontmatter field. On interactive TTY surfaces, a missing name
triggers a prompt instead; ``skip_confirm=True`` means "non-interactive"
(so pair it with ``name_override`` when installing from a URL that has
no frontmatter).

#### def `do_inspect(identifier: str, console: Optional[Console] = None) -> None`

Preview a skill's SKILL.md content without installing.

#### def `browse_skills(page: int = 1, page_size: int = 20, source: str = 'all') -> dict`

Paginated hub browse for programmatic callers (e.g. TUI gateway).

Returns ``{"items": [...], "page": int, "total_pages": int, "total": int}``.

#### def `inspect_skill(identifier: str) -> Optional[dict]`

Skill metadata (+ SKILL.md preview) for programmatic callers.

#### def `do_list(source_filter: str = 'all', enabled_only: bool = False, console: Optional[Console] = None) -> None`

List installed skills, distinguishing hub, builtin, and local skills.

Args:
    source_filter: ``all`` | ``hub`` | ``builtin`` | ``local``.
    enabled_only: If True, hide disabled skills from the output.

Enabled/disabled state is resolved against the currently active profile's
config — ``hermes -p <profile> skills list`` reads that profile's
``skills.disabled`` list because ``-p`` swaps ``HERMES_HOME`` at process
start.  No explicit profile flag needed here.

#### def `do_check(name: Optional[str] = None, console: Optional[Console] = None) -> None`

Check hub-installed skills for upstream updates.

#### def `do_update(name: Optional[str] = None, console: Optional[Console] = None) -> None`

Update hub-installed skills with upstream changes.

#### def `do_audit(name: Optional[str] = None, console: Optional[Console] = None, deep: bool = False) -> None`

Re-run security scan on installed hub skills.

When ``deep=True``, also runs an opt-in AST-level diagnostic on Python
files (review aid only — not a security gate; skills_guard.py verdicts
are unchanged).

#### def `do_uninstall(name: str, console: Optional[Console] = None, skip_confirm: bool = False, invalidate_cache: bool = True) -> None`

Remove a hub-installed skill with confirmation.

#### def `do_reset(name: str, restore: bool = False, console: Optional[Console] = None, skip_confirm: bool = False, invalidate_cache: bool = True) -> None`

Reset a bundled skill's manifest tracking (+ optionally restore from bundled).

#### def `do_list_modified(console: Optional[Console] = None, as_json: bool = False) -> None`

List bundled skills the user has edited (which `hermes update` keeps).

#### def `do_diff(name: str, console: Optional[Console] = None) -> None`

Show how the user's copy of a bundled skill differs from the stock version.

#### def `do_opt_out(remove: bool = False, console: Optional[Console] = None, skip_confirm: bool = False, invalidate_cache: bool = True) -> None`

Opt the active profile out of bundled-skill seeding.

Always writes the .no-bundled-skills marker (stop future seeding). With
``remove``, also deletes already-present bundled skills that are pristine
(manifest-tracked AND unmodified); user-edited and non-bundled skills are
never touched.

#### def `do_opt_in(sync: bool = False, console: Optional[Console] = None, invalidate_cache: bool = True) -> None`

Remove the opt-out marker so bundled-skill seeding resumes.

With ``sync``, immediately re-seed bundled skills instead of waiting for
the next ``hermes update``.

#### def `do_repair_official(name: str, restore: bool = False, console: Optional[Console] = None, skip_confirm: bool = False, invalidate_cache: bool = True) -> None`

Backfill or restore official optional skills from repo source.

#### def `do_tap(action: str, repo: str = '', console: Optional[Console] = None) -> None`

Manage taps (custom GitHub repo sources).

#### def `do_publish(skill_path: str, target: str = 'github', repo: str = '', console: Optional[Console] = None) -> None`

Publish a local skill to a registry (GitHub PR or ClawHub submission).

#### def `do_snapshot_export(output_path: str, console: Optional[Console] = None) -> None`

Export current hub skill configuration to a portable JSON file.

#### def `do_snapshot_import(input_path: str, force: bool = False, console: Optional[Console] = None) -> None`

Re-install skills from a snapshot file.

#### def `skills_command(args) -> None`

Router for `hermes skills <subcommand>` — called from hermes_cli/main.py.

#### def `handle_skills_slash(cmd: str, console: Optional[Console] = None) -> None`

Parse and dispatch `/skills <subcommand> [args]` from the chat interface.

Examples:
    /skills search kubernetes
    /skills install openai/skills/skill-creator
    /skills install openai/skills/skill-creator --force
    /skills install https://example.com/path/SKILL.md
    /skills inspect openai/skills/skill-creator
    /skills list
    /skills list --source hub
    /skills check
    /skills update
    /skills audit
    /skills audit my-skill
    /skills audit --deep
    /skills audit my-skill --deep
    /skills uninstall my-skill
    /skills tap list
    /skills tap add owner/repo
    /skills tap remove owner/repo


## hermes_cli.skin_engine

### 模块文档

Hermes CLI skin/theme engine.

A data-driven skin system that lets users customize the CLI's visual appearance.
Skins are defined as YAML files in ~/.hermes/skins/ or as built-in presets.
No code changes are needed to add a new skin.

SKIN YAML SCHEMA
================

All fields are optional. Missing values inherit from the ``default`` skin.

.. code-block:: yaml

    # Required: skin identity
    name: mytheme                         # Unique skin name (lowercase, hyphens ok)
    description: Short description        # Shown in /skin listing

    # Colors: hex values for Rich markup (banner, UI, response box)
    colors:
      banner_border: "#CD7F32"            # Panel border color
      banner_title: "#FFD700"             # Panel title text color
      banner_accent: "#FFBF00"            # Section headers (Available Tools, etc.)
      banner_dim: "#B8860B"               # Dim/muted text (separators, labels)
      banner_text: "#FFF8DC"              # Body text (tool names, skill names)
      ui_accent: "#FFBF00"               # General UI accent
      ui_label: "#DAA520"                # UI labels (warm gold; teal clashed w/ default banner gold)
      ui_ok: "#4caf50"                   # Success indicators
      ui_error: "#ef5350"                # Error indicators
      ui_warn: "#ffa726"                 # Warning indicators
      prompt: "#FFF8DC"                  # Prompt text color
      input_rule: "#CD7F32"              # Input area horizontal rule
      response_border: "#FFD700"         # Response box border (ANSI)
      status_bar_bg: "#1a1a2e"           # Status bar background
      status_bar_text: "#C0C0C0"         # Status bar default text
      status_bar_strong: "#FFD700"       # Status bar highlighted text
      status_bar_dim: "#8B8682"          # Status bar separators/muted text
      status_bar_good: "#8FBC8F"         # Healthy context usage
      status_bar_warn: "#FFD700"         # Warning context usage
      status_bar_bad: "#FF8C00"          # High context usage
      status_bar_critical: "#FF6B6B"     # Critical context usage
      session_label: "#DAA520"           # Session label color
      session_border: "#8B8682"          # Session ID dim color
      status_bar_bg: "#1a1a2e"          # TUI status/usage bar background
      voice_status_bg: "#1a1a2e"        # TUI voice status background
      selection_bg: "#333355"           # TUI mouse-selection highlight background
      completion_menu_bg: "#1a1a2e"      # Completion menu background
      completion_menu_current_bg: "#333355"  # Active completion row background
      completion_menu_meta_bg: "#1a1a2e"     # Completion meta column background
      completion_menu_meta_current_bg: "#333355"  # Active completion meta background

    # Spinner: customize the animated spinner during API calls
    spinner:
      waiting_faces:                      # Faces shown while waiting for API
        - "(⚔)"
        - "(⛨)"
      thinking_faces:                     # Faces shown during reasoning
        - "(⌁)"
        - "(<>)"
      thinking_verbs:                     # Verbs for spinner messages
        - "forging"
        - "plotting"
      wings:                              # Optional left/right spinner decorations
        - ["⟪⚔", "⚔⟫"]                  # Each entry is [left, right] pair
        - ["⟪▲", "▲⟫"]

    # Branding: text strings used throughout the CLI
    branding:
      agent_name: "Hermes Agent"          # Banner title, status display
      welcome: "Welcome message"          # Shown at CLI startup
      goodbye: "Goodbye! ⚕"              # Shown on exit
      response_label: " ⚕ Hermes "       # Response box header label
      prompt_symbol: "❯"                 # Input prompt symbol (bare token; renderers add trailing space)
      help_header: "(^_^)? Commands"      # /help header text

    # Tool prefix: character for tool output lines (default: ┊)
    tool_prefix: "┊"

    # Tool emojis: override the default emoji for any tool (used in spinners & progress)
    tool_emojis:
      terminal: "⚔"           # Override terminal tool emoji
      web_search: "🔮"        # Override web_search tool emoji
      # Any tool not listed here uses its registry default

USAGE
=====

.. code-block:: python

    from hermes_cli.skin_engine import get_active_skin, list_skins, set_active_skin

    skin = get_active_skin()
    print(skin.colors["banner_title"])    # "#FFD700"
    print(skin.get_branding("agent_name"))  # "Hermes Agent"

    set_active_skin("ares")               # Switch to built-in ares skin
    set_active_skin("mytheme")            # Switch to user skin from ~/.hermes/skins/

BUILT-IN SKINS
==============

- ``default`` — Classic Hermes gold/kawaii (the current look)
- ``ares``    — Crimson/bronze war-god theme with custom spinner wings
- ``mono``    — Clean grayscale monochrome
- ``slate``   — Cool blue developer-focused theme
- ``daylight`` — Light background theme with dark text and blue accents
- ``warm-lightmode`` — Warm brown/gold text for light terminal backgrounds

USER SKINS
==========

Drop a YAML file in ``~/.hermes/skins/<name>.yaml`` following the schema above.
Activate with ``/skin <name>`` in the CLI or ``display.skin: <name>`` in config.yaml.

### class SkinConfig

> 继承: `object` ｜ 方法数: 3（公开 3）

Complete skin configuration.

#### def `get_color(self, key: str, fallback: str = '') -> str`

Get a color value with fallback.

#### def `get_spinner_wings(self) -> List[Tuple[str, str]]`

Get spinner wing pairs, or empty list if none.

#### def `get_branding(self, key: str, fallback: str = '') -> str`

Get a branding value with fallback.


### 顶层函数

#### def `list_skins() -> List[Dict[str, str]]`

List all available skins (built-in + user-installed).

Returns list of {"name": ..., "description": ..., "source": "builtin"|"user"}.

#### def `load_skin(name: str) -> SkinConfig`

Load a skin by name. Checks user skins first, then built-in.

#### def `get_active_skin() -> SkinConfig`

Get the currently active skin config (cached).

#### def `set_active_skin(name: str) -> SkinConfig`

Switch the active skin. Returns the new SkinConfig.

#### def `get_active_skin_name() -> str`

Get the name of the currently active skin.

#### def `init_skin_from_config(config: dict) -> None`

Initialize the active skin from CLI config at startup.

Call this once during CLI init with the loaded config dict.

#### def `get_active_prompt_symbol(fallback: str = '❯') -> str`

Return the interactive prompt symbol with a single trailing space.

Skins store ``prompt_symbol`` as a bare token (no spaces). The trailing
space is appended here so callers can drop it straight into a rendered
prompt without hand-rolling whitespace.

#### def `get_active_help_header(fallback: str = '(^_^)? Available Commands') -> str`

Get the /help header from the active skin.

#### def `get_active_goodbye(fallback: str = 'Goodbye! ⚕') -> str`

Get the goodbye line from the active skin.

#### def `get_prompt_toolkit_style_overrides() -> Dict[str, str]`

Return prompt_toolkit style overrides derived from the active skin.

These are layered on top of the CLI's base TUI style so /skin can refresh
the live prompt_toolkit UI immediately without rebuilding the app.


## hermes_cli.slack_cli

### 模块文档

``hermes slack ...`` CLI subcommands.

Today only ``hermes slack manifest`` is implemented — it generates the
Slack app manifest JSON for registering every gateway command as a native
Slack slash (``/btw``, ``/stop``, ``/model``, …) so users get the same
first-class slash UX Discord and Telegram already have.

Typical workflow::

    $ hermes slack manifest > slack-manifest.json
    # or:
    $ hermes slack manifest --write

Then paste the printed JSON into the Slack app config (Features → App
Manifest → Edit) and click Save. Slack diffs the manifest and prompts
for reinstall when scopes/commands change.

### 顶层函数

#### def `slack_manifest_command(args) -> int`

Print or write a Slack app manifest JSON.

Flags (all parsed in ``hermes_cli/main.py``):
  --write [PATH]  Write to file instead of stdout (default path:
                  ``$HERMES_HOME/slack-manifest.json``)
  --name NAME     Override the bot display name (default: "Hermes")
  --description DESC  Override the bot description
  --slashes-only  Emit only the ``features.slash_commands`` array (for
                  merging into an existing manifest manually)
  --no-assistant  Omit Slack AI Assistant mode (assistant_view feature,
                  assistant:write scope, assistant_thread_* events) so
                  DMs render as a flat chat where bare slash commands
                  work inline instead of the Assistant thread pane.
  --agent-view    Use Slack's Agent messaging experience (agent_view,
                  app_home_opened + message.im) instead of the legacy
                  Assistant messaging experience.


## hermes_cli.sqlite_util

### 模块文档

Shared SQLite primitives for the small per-profile / board stores.

The projects and kanban stores open WAL SQLite files with the same two
primitives — an idempotent column-add migration and an IMMEDIATE write
transaction. One definition here keeps the two stores from drifting.

### 顶层函数

#### def `add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> bool`

``ALTER TABLE <table> ADD COLUMN <ddl>``, idempotent across races.

Returns ``True`` when this call added the column. Swallows the
``duplicate column name`` error a concurrent migrator may have run first
(issue #21708). ``column`` is the human-readable name for the call site;
``ddl`` carries the actual definition.

#### def `write_txn(conn: sqlite3.Connection)`

An IMMEDIATE write transaction: at most one concurrent writer wins.

The explicit ROLLBACK is guarded so a SQLite auto-rollback (no active
transaction left under EIO / lock contention / corruption) cannot shadow
the original exception with a spurious rollback error.


## hermes_cli.status

### 模块文档

Status command for hermes CLI.

Shows the status of all Hermes Agent components.

### 顶层函数

#### def `check_mark(ok: bool) -> str`

#### def `redact_key(key: str) -> str`

Redact an API key for display.

Thin wrapper over :func:`agent.redact.mask_secret`. Preserves the
"(not set)" placeholder in dim color to match ``hermes config``'s
output (previously this variant was missing the DIM color —
consolidated via PR that also introduced ``mask_secret``).

#### def `show_status(args)`

Show status of all Hermes Agent components.


## hermes_cli.stdio

### 模块文档

Windows-safe stdio configuration.

On Windows, Python's ``sys.stdout``/``sys.stderr`` default to the console's
active code page (often ``cp1252``, sometimes ``cp437``, occasionally ``cp932``
on Japanese locales, etc.).  Hermes's banners, tool output feed, and slash
command listings all contain Unicode: box-drawing characters (``─┌┐└┘├┤``),
mathematical and geometric symbols (``◆ ◇ ◎ ▣ ⚔ ⚖ →``), and user-supplied
text in any language.  Printing those to a cp1252 console raises
``UnicodeEncodeError: 'charmap' codec can't encode character…`` and kills the
whole CLI before the REPL even opens.

The fix is to force UTF-8 on the Python side and also flip the console's
code page to UTF-8 (65001).  Both matter: Python-level only helps when
Python's stdout is a real TTY; code-page flipping lets subprocesses and
child Python ``print()`` calls agree on encoding.

This module is a no-op on every non-Windows platform, and idempotent.
Entry points (``cli.py`` ``main``, ``hermes_cli/main.py`` CLI dispatch,
``gateway/run.py`` startup) call :func:`configure_windows_stdio` exactly
once early in startup.

Patterns cribbed from Claude Code (``src/utils/platform.ts``), OpenCode
(``packages/opencode/src/pty/index.ts`` env injection), and OpenAI Codex
(``codex-rs/core/src/unified_exec/process_manager.rs``).  None of those
actually flip the console code page — they rely on their runtime (Node or
Rust) writing UTF-16 to the Win32 console API and letting the terminal
sort it out.  Python doesn't get that luxury.

### 顶层函数

#### def `is_windows() -> bool`

Return True iff running on native Windows (not WSL).

#### def `configure_windows_stdio() -> bool`

Force UTF-8 stdio on Windows.  No-op elsewhere.

Idempotent — safe to call multiple times from different entry points.

Returns ``True`` if anything was actually changed, ``False`` on
non-Windows or on a repeat call.

Set ``HERMES_DISABLE_WINDOWS_UTF8=1`` in the environment to opt out
(for diagnosing encoding-related bugs by forcing the old cp1252 path).

Also sets a sensible default ``EDITOR`` on Windows if none is already
set — see :func:`_default_windows_editor`.


## hermes_cli.subcommands.__init__

### 模块文档

CLI subcommand parser builders for ``hermes <subcommand>``.

``hermes_cli/main.py:main()`` historically built the entire argparse tree
inline — 179 ``add_parser`` calls across ~26 subcommand groups, all wedged
into one 3,300-line function. This package breaks that tree apart: each
subcommand group owns a ``build_<group>_parser(subparsers, ...)`` function in
its own module, and ``main()`` calls those builders instead of inlining the
argument definitions.

Handlers (the ``cmd_*`` functions) still live in ``main.py`` for now and are
dependency-injected into the builders so these modules never import ``main``
(which would create a cycle). Shared parser helpers live in
``_shared.py``.

Part of the god-file decomposition plan (Phase 2).

## hermes_cli.subcommands._shared

### 模块文档

Shared parser helpers used across multiple CLI subcommand builders.

These were module-level helpers in ``hermes_cli/main.py``. They are pulled
into a neutral module so both ``main.py`` and every
``hermes_cli/subcommands/<group>.py`` builder can import them without an
import cycle. ``main.py`` re-exports them for backwards compatibility, so
existing references keep working.

### 顶层函数

#### def `add_accept_hooks_flag(parser: argparse.ArgumentParser) -> None`

Attach the ``--accept-hooks`` flag.

Shared across every agent subparser so the flag works regardless of CLI
position.


## hermes_cli.subcommands.acp

### 模块文档

``hermes acp`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_acp_parser(subparsers, cmd_acp: Callable) -> None`

Attach the ``acp`` subcommand to ``subparsers``.


## hermes_cli.subcommands.auth

### 模块文档

``hermes auth`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_auth_parser(subparsers, cmd_auth: Callable) -> None`

Attach the ``auth`` subcommand to ``subparsers``.


## hermes_cli.subcommands.backup

### 模块文档

``hermes backup`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_backup_parser(subparsers, cmd_backup: Callable) -> None`

Attach the ``backup`` subcommand to ``subparsers``.


## hermes_cli.subcommands.claw

### 模块文档

``hermes claw`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_claw_parser(subparsers, cmd_claw: Callable) -> None`

Attach the ``claw`` subcommand to ``subparsers``.


## hermes_cli.subcommands.config

### 模块文档

``hermes config`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_config_parser(subparsers, cmd_config: Callable) -> None`

Attach the ``config`` subcommand to ``subparsers``.


## hermes_cli.subcommands.console

### 模块文档

``hermes console`` subcommand parser.

### 顶层函数

#### def `build_console_parser(subparsers, cmd_console: Callable) -> None`

Attach the safe Hermes Console REPL subcommand.


## hermes_cli.subcommands.cron

### 模块文档

``hermes cron`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` — same arguments, same
``func=cmd_cron`` dispatch. The handler is injected so this module does not
import ``main`` (cycle avoidance).

### 顶层函数

#### def `build_cron_parser(subparsers, cmd_cron: Callable) -> None`

Attach the ``cron`` subcommand (and its sub-actions) to ``subparsers``.


## hermes_cli.subcommands.dashboard

### 模块文档

``hermes dashboard`` / ``hermes serve`` subcommand parsers.

``dashboard`` is the browser web UI; ``serve`` is the same gateway, headless —
what the desktop app and remote backends run. ``serve`` also skips the web UI
build (``headless_backend=True``): pure JSON-RPC/WS clients never load the SPA.
Both share one handler (``cmd_dashboard`` → ``start_server``). Extracted from
``hermes_cli/main.py:main()`` (god-file Phase 2); handler injected to avoid
importing ``main``.

### 顶层函数

#### def `build_dashboard_parser(subparsers, cmd_dashboard: Callable, cmd_dashboard_register: Callable) -> None`

Attach the ``dashboard`` and ``serve`` subcommands.

Both share the same backend (``cmd_dashboard`` → ``start_server``).
``dashboard`` is the browser UI; ``serve`` is the headless backend used by
the desktop app and remote clients. They are independent surfaces — neither
"launches" the other — so the desktop app spawns ``serve``, never
``dashboard``.


## hermes_cli.subcommands.debug

### 模块文档

``hermes debug`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_debug_parser(subparsers, cmd_debug: Callable) -> None`

Attach the ``debug`` subcommand to ``subparsers``.


## hermes_cli.subcommands.doctor

### 模块文档

``hermes doctor`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_doctor_parser(subparsers, cmd_doctor: Callable) -> None`

Attach the ``doctor`` subcommand to ``subparsers``.


## hermes_cli.subcommands.dump

### 模块文档

``hermes dump`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_dump_parser(subparsers, cmd_dump: Callable) -> None`

Attach the ``dump`` subcommand to ``subparsers``.


## hermes_cli.subcommands.gateway

### 模块文档

``hermes gateway`` and ``hermes proxy`` subcommand parsers.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Both parsers are built together because they shared one inline block (the
``gateway`` section also defined ``proxy``). Handlers injected to avoid
importing ``main``.

### 顶层函数

#### def `build_gateway_parser(subparsers, cmd_gateway: Callable, cmd_proxy: Callable, cmd_gateway_enroll: Callable) -> None`

Attach the ``gateway`` and ``proxy`` subcommands to ``subparsers``.


## hermes_cli.subcommands.gui

### 模块文档

``hermes gui`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_gui_parser(subparsers, cmd_gui: Callable) -> None`

Attach the ``gui`` subcommand to ``subparsers``.


## hermes_cli.subcommands.hooks

### 模块文档

``hermes hooks`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_hooks_parser(subparsers, cmd_hooks: Callable) -> None`

Attach the ``hooks`` subcommand to ``subparsers``.


## hermes_cli.subcommands.import_cmd

### 模块文档

``hermes import`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_import_cmd_parser(subparsers, cmd_import: Callable) -> None`

Attach the ``import`` subcommand to ``subparsers``.


## hermes_cli.subcommands.insights

### 模块文档

``hermes insights`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_insights_parser(subparsers, cmd_insights: Callable) -> None`

Attach the ``insights`` subcommand to ``subparsers``.


## hermes_cli.subcommands.login

### 模块文档

``hermes login`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_login_parser(subparsers, cmd_login: Callable) -> None`

Attach the deprecated ``login`` subcommand to ``subparsers``.

``hermes login`` was removed in favor of ``hermes auth`` / ``hermes model``
(the runtime handler in ``hermes_cli/auth.py::login_command`` just prints a
deprecation message and exits).  The subparser is kept registered so that
old scripts/aliases invoking ``hermes login [--flags]`` still receive the
actionable deprecation message rather than an argparse ``invalid choice:
'login'`` error — but:

- The subparser is registered WITHOUT a ``help=`` kwarg so the row is
  omitted from ``hermes --help`` (argparse only lists subcommands that
  have a help string).  This hides a command that no longer works (#24756)
  without the ``help=argparse.SUPPRESS`` ``==SUPPRESS==`` leak that
  argparse emits for a top-level subparser on Python 3.12+.
- ``--provider`` accepts ANY value (no ``choices=``) so that, e.g.,
  ``hermes login --provider anthropic`` reaches the deprecation handler and
  gets pointed at ``hermes model`` instead of crashing in argparse with
  ``invalid choice: 'anthropic'`` before the handler can run.


## hermes_cli.subcommands.logout

### 模块文档

``hermes logout`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_logout_parser(subparsers, cmd_logout: Callable) -> None`

Attach the ``logout`` subcommand to ``subparsers``.


## hermes_cli.subcommands.logs

### 模块文档

``hermes logs`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_logs_parser(subparsers, cmd_logs: Callable) -> None`

Attach the ``logs`` subcommand to ``subparsers``.


## hermes_cli.subcommands.mcp

### 模块文档

``hermes mcp`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_mcp_parser(subparsers, cmd_mcp: Callable) -> None`

Attach the ``mcp`` subcommand to ``subparsers``.


## hermes_cli.subcommands.memory

### 模块文档

``hermes memory`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_memory_parser(subparsers, cmd_memory: Callable) -> None`

Attach the ``memory`` subcommand to ``subparsers``.


## hermes_cli.subcommands.model

### 模块文档

``hermes model`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_model_parser(subparsers, cmd_model: Callable) -> None`

Attach the ``model`` subcommand to ``subparsers``.


## hermes_cli.subcommands.pairing

### 模块文档

``hermes pairing`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_pairing_parser(subparsers, cmd_pairing: Callable) -> None`

Attach the ``pairing`` subcommand to ``subparsers``.


## hermes_cli.subcommands.plugins

### 模块文档

``hermes plugins`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_plugins_parser(subparsers, cmd_plugins: Callable) -> None`

Attach the ``plugins`` subcommand to ``subparsers``.


## hermes_cli.subcommands.postinstall

### 模块文档

``hermes postinstall`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_postinstall_parser(subparsers, cmd_postinstall: Callable) -> None`

Attach the ``postinstall`` subcommand to ``subparsers``.


## hermes_cli.subcommands.profile

### 模块文档

``hermes profile`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_profile_parser(subparsers, cmd_profile: Callable) -> None`

Attach the ``profile`` subcommand to ``subparsers``.


## hermes_cli.subcommands.prompt_size

### 模块文档

``hermes prompt-size`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_prompt_size_parser(subparsers, cmd_prompt_size: Callable) -> None`

Attach the ``prompt-size`` subcommand to ``subparsers``.


## hermes_cli.subcommands.security

### 模块文档

``hermes security`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_security_parser(subparsers, cmd_security: Callable) -> None`

Attach the ``security`` subcommand to ``subparsers``.


## hermes_cli.subcommands.setup

### 模块文档

``hermes setup`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_setup_parser(subparsers, cmd_setup: Callable) -> None`

Attach the ``setup`` subcommand to ``subparsers``.


## hermes_cli.subcommands.skills

### 模块文档

``hermes skills`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_skills_parser(subparsers, cmd_skills: Callable) -> None`

Attach the ``skills`` subcommand to ``subparsers``.


## hermes_cli.subcommands.slack

### 模块文档

``hermes slack`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_slack_parser(subparsers, cmd_slack: Callable) -> None`

Attach the ``slack`` subcommand to ``subparsers``.


## hermes_cli.subcommands.status

### 模块文档

``hermes status`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_status_parser(subparsers, cmd_status: Callable) -> None`

Attach the ``status`` subcommand to ``subparsers``.


## hermes_cli.subcommands.tools

### 模块文档

``hermes tools`` subcommand parser.

Extracted from ``hermes_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_tools_parser(subparsers, cmd_tools: Callable) -> None`

Attach the ``tools`` subcommand to ``subparsers``.


## hermes_cli.subcommands.uninstall

### 模块文档

``hermes uninstall`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_uninstall_parser(subparsers, cmd_uninstall: Callable) -> None`

Attach the ``uninstall`` subcommand to ``subparsers``.


## hermes_cli.subcommands.update

### 模块文档

``hermes update`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_update_parser(subparsers, cmd_update: Callable) -> None`

Attach the ``update`` subcommand to ``subparsers``.


## hermes_cli.subcommands.version

### 模块文档

``hermes version`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_version_parser(subparsers, cmd_version: Callable) -> None`

Attach the ``version`` subcommand to ``subparsers``.


## hermes_cli.subcommands.webhook

### 模块文档

``hermes webhook`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_webhook_parser(subparsers, cmd_webhook: Callable) -> None`

Attach the ``webhook`` subcommand to ``subparsers``.


## hermes_cli.subcommands.whatsapp

### 模块文档

``hermes whatsapp`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.

### 顶层函数

#### def `build_whatsapp_parser(subparsers, cmd_whatsapp: Callable) -> None`

Attach the ``whatsapp`` subcommand to ``subparsers``.


## hermes_cli.suggestions_cmd

### 模块文档

Shared ``/suggestions`` command logic for CLI and gateway.

Both surfaces call ``handle_suggestions_command(args, origin=...)`` and present
the returned text however they present command output. Keeping the logic here
(not in cli.py / gateway/run.py) means the two surfaces can never drift.

Subcommands:
  /suggestions                 list pending suggestions (numbered)
  /suggestions accept <N|id>   create the cron job for that suggestion
  /suggestions dismiss <N|id>  dismiss it (latched, never re-offered)
  /suggestions catalog         seed the curated starter automations as pending
  /suggestions clear           drop accepted records (housekeeping)

### 顶层函数

#### def `handle_suggestions_command(args: str, origin: Optional[Dict[str, Any]] = None, surface: str = 'cli') -> str`

Dispatch a ``/suggestions`` invocation. Returns text to show the user.

``args`` is everything after ``/suggestions`` (already stripped of the
command word). ``origin`` is the platform/chat dict so an accepted job's
"origin" delivery routes back to where the user accepted; when omitted it
is resolved from the session environment. ``surface`` (``"cli"`` |
``"gateway"``) picks the wording for follow-up hints — ``/cron`` only
exists on the CLI.


## hermes_cli.telegram_managed_bot

### 模块文档

Telegram Managed Bot onboarding client.

Uses Telegram's Managed Bots feature to create a user-owned child bot without
manual BotFather token copy-paste. Hermes talks only to the Nous onboarding
service; the raw Telegram token is saved locally after one-time retrieval.

### class TelegramPairing

> 继承: `object` ｜ 方法数: 0（公开 0）

Pairing record returned by the Telegram onboarding service.


### class TelegramBotSetupResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Successful Telegram onboarding result returned by the setup service.


### 顶层函数

#### def `is_valid_telegram_bot_token(token: object) -> bool`

Return True when *token* has Telegram's bot-token shape.

#### def `render_qr_terminal(url: str) -> str`

Render a URL as a QR code string suitable for terminal output.

#### def `print_qr_code(url: str, include_link: bool = True) -> None`

Print a QR code to stdout, with URL fallback if qrcode is missing.

#### def `generate_username_slug(length: int = 16) -> str`

Generate a base32-ish slug for Telegram username correlation.

Sixteen characters from a 32-symbol alphabet gives 80 bits of entropy while
keeping ``hermes_<slug>_bot`` under Telegram's 32-character username limit.

#### def `generate_bot_username(profile_name: Optional[str] = None) -> str`

Generate a secure suggested bot username like ``hermes_<slug>_bot``.

``profile_name`` is accepted for backward compatibility with the original
PoC, but is intentionally not embedded in the username. The username has to
carry enough entropy for backend correlation.

#### def `generate_deep_link(manager_bot: str = DEFAULT_MANAGER_BOT, suggested_username: Optional[str] = None, suggested_name: Optional[str] = None) -> str`

Build a ``t.me/newbot`` deep link for managed bot creation.

#### def `generate_pairing_nonce() -> str`

Generate a legacy-compatible random nonce string.

The new protocol uses service-created ``pairing_id`` + bearer
``poll_token`` instead of a path nonce, but this helper is harmless and
still useful for callers/tests that need a generic random id.

#### def `create_pairing(api_url: str | None = None, bot_name: str = DEFAULT_BOT_NAME, timeout: float = 10.0) -> TelegramPairing | None`

Create a Telegram onboarding pairing.

``POST /v1/telegram/pairings`` returns the deep link, QR payload, public
pairing id, and secret poll token. The token is only used as a bearer
credential while polling.

#### def `poll_pairing_result_once(api_url: str | None, pairing: TelegramPairing, timeout: float = 10.0) -> TelegramBotSetupResult | None`

Poll the onboarding service once. Returns setup metadata when ready.

#### def `poll_pairing_once(api_url: str | None, pairing: TelegramPairing, timeout: float = 10.0) -> str | None`

Poll the onboarding service once. Returns the token when ready.

#### def `poll_for_setup_result(api_url: str | None, pairing: TelegramPairing, timeout: float = DEFAULT_POLL_TIMEOUT, interval: float = POLL_INTERVAL) -> Optional[TelegramBotSetupResult]`

Poll the pairing API until setup metadata is available or timeout.

#### def `poll_for_token(api_url: str | None, pairing: TelegramPairing, timeout: float = DEFAULT_POLL_TIMEOUT, interval: float = POLL_INTERVAL) -> Optional[str]`

Poll the pairing API until the bot token is available or timeout.

#### def `auto_setup_telegram_bot_result(api_url: str | None = None, manager_bot: str = DEFAULT_MANAGER_BOT, profile_name: Optional[str] = None, poll_timeout: float = DEFAULT_POLL_TIMEOUT) -> Optional[TelegramBotSetupResult]`

Run the full automatic Telegram bot creation flow.

#### def `auto_setup_telegram_bot(api_url: str | None = None, manager_bot: str = DEFAULT_MANAGER_BOT, profile_name: Optional[str] = None, poll_timeout: float = DEFAULT_POLL_TIMEOUT) -> Optional[str]`

Run automatic Telegram bot creation and return only the bot token.


## hermes_cli.timeouts

### 顶层函数

#### def `get_provider_request_timeout(provider_id: str, model: str | None = None) -> float | None`

Return a configured provider request timeout in seconds, if any.

#### def `get_provider_stale_timeout(provider_id: str, model: str | None = None) -> float | None`

Return a configured non-stream stale timeout in seconds, if any.


## hermes_cli.tips

### 模块文档

Random tips shown at CLI session start to help users discover features.

### 顶层函数

#### def `get_random_tip(exclude_recent: int = 0) -> str`

Return a random tip string.

Args:
    exclude_recent: not used currently; reserved for future
        deduplication across sessions.


## hermes_cli.tools_config

### 模块文档

Unified tool configuration for Hermes Agent.

`hermes tools` and `hermes setup tools` both enter this module.
Select a platform → toggle toolsets on/off → for newly enabled tools
that need API keys, run through provider-aware configuration.

Saves per-platform tool configuration to ~/.hermes/config.yaml under
the `platform_toolsets` key.

### 顶层函数

#### def `gui_toolset_label(label: str) -> str`

Strip leading emoji/icons from toolset titles for GUI surfaces.

Registry labels use ``<emoji> <title>``; plugin toolsets prefix with ``🔌``.
CLI/TUI keeps the raw ``label`` — only HTTP APIs call this helper.

#### def `install_cua_driver(upgrade: bool = False) -> bool`

Install or refresh the cua-driver binary used by Computer Use.

The upstream installer always pulls the latest release tag, so re-running
it is the canonical way to upgrade. We expose two modes:

* ``upgrade=False`` — original post-setup behaviour: skip if already
  installed, install otherwise. Used by the toolset enable flow where
  we don't want to surprise the user with a network fetch.
* ``upgrade=True`` — always re-run the installer (or call ``cua-driver
  update`` if the binary supports it). Used by ``hermes update`` and
  by ``hermes computer-use install --upgrade``.

Returns True iff cua-driver is installed (or successfully refreshed)
when the function returns. Supported on macOS, Windows, and Linux
(Linux is alpha). Silently returns False on unsupported platforms.

#### def `valid_post_setup_keys() -> Set[str]`

Return the set of post-setup keys declared by any visible provider.

Collected from ``TOOL_CATEGORIES`` plus the plugin-registered web /
image-gen / video-gen / browser providers (which can also carry a
``post_setup``). This is the allowlist the ``hermes tools post-setup``
command and the dashboard post-setup endpoint validate against, so a
caller can't drive ``_run_post_setup`` with an arbitrary key.

#### def `run_post_setup_command(args) -> int`

``hermes tools post-setup <key>`` — non-interactive post-setup runner.

Runs the install/bootstrap hook a provider declares (npm install for
browser/Camofox, pip install for kittentts/piper/ddgs, cua-driver fetch,
etc.). This is the stable, scriptable target the dashboard spawns so the
GUI can drive backend setup without re-implementing the install logic.
Returns a process exit code (0 ok, 2 unknown key).

#### def `enabled_mcp_server_names(config: dict) -> Set[str]`

Names of MCP servers globally enabled in config.yaml.

Shared by the gateway/CLI platform resolver (``_get_platform_tools``) and
the cron per-job toolset resolver (``cron.scheduler``) so every path agrees
on MCP membership. A server is enabled unless its config sets an explicitly
falsey ``enabled`` (per ``_parse_enabled_flag``: false/0/no/off) — a missing
flag or an unrecognized value is treated as enabled.

#### def `web_provider_capabilities(backend: str) -> list`

Return the capabilities (``search`` / ``extract``) a web backend supports.

Consults the plugin registry's provider instance (``supports_search`` /
``supports_extract``) so the Capabilities GUI can offer per-capability
selection (``web.search_backend`` / ``web.extract_backend``) only where it
makes sense — e.g. ddgs and brave-free are search-only. Falls back to both
capabilities when the backend isn't registered (hardcoded setup-flow rows
like the managed Firecrawl entries resolve before plugin discovery in some
test contexts, and firecrawl itself supports both).

#### def `provider_readiness_status(provider: dict, config: dict, features = None, is_active: Optional[bool] = None) -> str`

Compute an honest readiness state for a provider picker row.

Returns one of:

- ``"ready"``       — usable as-is (keys set / entitled / installed).
- ``"needs_keys"``  — declares env vars and at least one is unset.
- ``"needs_auth"``  — needs a sign-in: Nous Portal login/entitlement for
  managed Tool Gateway rows, or xAI Grok OAuth / XAI_API_KEY for
  ``post_setup: "xai_grok"`` rows.
- ``"needs_setup"`` — keyless row whose ``post_setup`` install hook has
  verifiably not run yet (see ``_POST_SETUP_READY``).

Keyless ≠ usable: this is the server-side truth the GUI "Ready" pill
renders from (the old client-side heuristic showed Ready for every
zero-env-var row, including logged-out Nous Subscription rows).

``features`` (a ``NousSubscriptionFeatures``) can be passed to avoid
re-fetching portal state per row. ``is_active`` is the completed-setup
fallback signal for post_setup hooks with no registered installed-check
(selecting a row runs its hook, so the active row has been set up).

#### def `apply_provider_selection(ts_key: str, provider_name: str, config: dict) -> None`

Non-interactively persist a provider selection for a toolset.

Resolves ``provider_name`` within ``ts_key``'s category (matching the
rows the GUI/CLI picker shows via :func:`_visible_providers`) and writes
the corresponding backend/provider config keys. Unlike
:func:`_configure_provider`, this does NOT prompt for API keys, run
post-setup hooks, gate on Nous Portal auth, or run interactive model
pickers — those are handled separately (env endpoints, post-setup
endpoints, the model picker) in the desktop GUI.

Raises ``KeyError`` if the toolset has no category or the provider name
is not found among the visible providers.

**异常**: `KeyError`

#### def `tools_command(args = None, first_install: bool = False, config: dict = None)`

Entry point for `hermes tools` and `hermes setup tools`.

Args:
    first_install: When True (set by the setup wizard on fresh installs),
        skip the platform menu, go straight to the CLI checklist, and
        prompt for API keys on all enabled tools that need them.
    config: Optional config dict to use.  When called from the setup
        wizard, the wizard passes its own dict so that platform_toolsets
        are written into it and survive the wizard's final save_config().

#### def `tools_disable_enable_command(args)`

Enable, disable, or list tools for a platform.

Built-in toolsets use plain names (e.g. ``web``, ``memory``).
MCP tools use ``server:tool`` notation (e.g. ``github:create_issue``).


## hermes_cli.toolset_validation

### 模块文档

Validation for the ``platform_toolsets`` config section.

Pure, side-effect-free helpers so the logic is unit-testable without importing
the tool registry or launching Hermes (mirrors the decoupled-helper pattern used
elsewhere in the CLI).

Motivated by #38798: a config migration silently rewrote the valid toolset name
``hermes-cli`` to the non-existent ``hermes``. ``resolve_toolset('hermes')``
returns an empty list, so every tool silently disappeared with no error, warning,
or log entry — the agent degraded to text-only replies and the cause took
significant debugging to find. Surfacing invalid toolset names (and the
zero-tools end state) loudly turns that silent failure into an actionable one.

### 顶层函数

#### def `validate_platform_toolsets(platform_toolsets: object, is_valid_toolset: Callable[[str], bool]) -> List[str]`

Return human-readable warnings for a ``platform_toolsets`` mapping.

Two failure modes are reported:

1. A toolset name that ``is_valid_toolset`` rejects — usually a corrupted or
   renamed entry. When ``hermes-<platform>`` would have been valid (the exact
   #38798 shape, where ``cli`` held ``hermes`` instead of ``hermes-cli``),
   the warning includes that as a suggestion.
2. The mapping is non-empty but resolves to *zero* valid toolsets, so the
   agent would start with no tools at all.

``is_valid_toolset`` is injected (normally :func:`toolsets.validate_toolset`)
so this function performs no imports or I/O and is testable in isolation.

Args:
    platform_toolsets: The raw ``platform_toolsets`` value from config. Only
        ``dict`` values carry toolset entries; anything else yields no
        warnings (nothing to validate).
    is_valid_toolset: Predicate returning ``True`` for a known toolset name.

Returns:
    A list of warning strings (empty when everything is valid).


## hermes_cli.uninstall

### 模块文档

Hermes Agent Uninstaller.

Provides options for:
- Full uninstall: Remove everything including configs and data
- Keep data: Remove code but keep ~/.hermes/ (configs, sessions, logs)

### 顶层函数

#### def `log_info(msg: str)`

#### def `log_success(msg: str)`

#### def `log_warn(msg: str)`

#### def `get_project_root() -> Path`

Get the project installation directory.

#### def `find_shell_configs() -> list`

Find shell configuration files that might have PATH entries.

#### def `remove_path_from_shell_configs()`

Remove Hermes PATH entries from shell configuration files.

#### def `remove_wrapper_script()`

Remove the hermes wrapper script if it exists.

#### def `remove_node_symlinks(hermes_home: Path) -> list`

Remove the node/npm/npx symlinks the installer placed on PATH.

The POSIX installer (``scripts/install.sh`` / ``scripts/lib/node-bootstrap.sh``)
symlinks node/npm/npx into the same directory as the ``hermes`` command:

- ``/usr/local/bin/`` on root FHS installs (Linux, uid 0)
- ``$PREFIX/bin/`` on Termux
- ``~/.local/bin/`` otherwise (the common non-root case)

We check all candidate directories so that uninstall works regardless of
how the install was done (e.g. a root FHS install that placed links in
``/usr/local/bin``, or an older install that used ``~/.local/bin`` before
the FHS fix).  Only symlinks that resolve into this Hermes home's ``node``
directory are removed — links the user has repointed elsewhere (nvm, fnm,
etc.) are left untouched.

#### def `uninstall_gateway_service()`

Stop and uninstall the gateway service (systemd, launchd, Windows
Scheduled Task / Startup folder) and kill any standalone gateway processes.

Delegates to the gateway module which handles:
- Linux: user + system systemd services (with proper DBUS env setup)
- macOS: launchd plists
- Windows: Scheduled Task + Startup-folder fallback, via ``gateway_windows``
- All platforms: standalone ``hermes gateway run`` processes
- Termux/Android: skips systemd (no systemd on Android), still kills standalone processes

#### def `remove_path_from_windows_registry(hermes_home: Path) -> list[str]`

Strip Hermes-owned entries from User-scope PATH in the registry.

Returns the list of removed path entries.  Operates on HKCU\Environment,
same key the installer wrote to via ``[Environment]::SetEnvironmentVariable``.

#### def `remove_hermes_env_vars_windows() -> list[str]`

Delete HERMES_HOME and HERMES_GIT_BASH_PATH from User-scope env vars.

#### def `remove_portable_tooling_windows(hermes_home: Path) -> list[Path]`

Delete PortableGit and Node installs the Windows installer created under
``%LOCALAPPDATA%\hermes\``.  Only called on full uninstall; they're
isolated from any system Git / Node so they cannot break other tools.

#### def `run_gui_uninstall(args)`

GUI-only uninstall: remove the Chat GUI, leave the agent + data intact.

Mirrors ``hermes uninstall --gui``. Removes the desktop app's built
artifacts, the packaged app bundle (best-effort), and the Electron
userData dir — nothing under ``$HERMES_HOME`` config/sessions/.env, and
never the Python agent or its venv.

#### def `run_uninstall(args)`

Run the uninstall process.

Options:
- Full uninstall: removes code + ~/.hermes/ (configs, data, logs)
- Keep data: removes code but keeps ~/.hermes/ for future reinstall

#### def `main(argv = None) -> int`

Module entrypoint: ``python -m hermes_cli.uninstall --mode <gui|lite|full>``.

Exists so the desktop app can run the uninstall under a Python interpreter
OUTSIDE the venv being deleted. On Windows, ``lite``/``full`` rmtree the
venv that contains the running ``python.exe`` — and a running .exe is
mandatory-locked, so doing that from the venv's own interpreter half-fails.
The desktop launches this with the system Python + ``PYTHONPATH=<agentRoot>``
so ``import hermes_cli`` resolves from source while the venv is torn down.

This module imports only stdlib + ``hermes_constants`` + ``hermes_cli.colors``
(and lazily ``hermes_cli.gui_uninstall``), so it runs fine under a bare
system Python with no site-packages from the venv.


## hermes_cli.urllib_security

### 模块文档

Security policy for credential-bearing stdlib urllib requests.

### class SafeCredentialRedirectHandler

> 继承: `urllib.request.HTTPRedirectHandler` ｜ 方法数: 2（公开 1）

Preserve request headers only while redirects stay on one origin.

#### def `__init__(original_url: str, cross_origin_safe_headers: Iterable[str] = _CROSS_ORIGIN_SAFE_HEADERS) -> None`

#### def `redirect_request(self, req, fp, code, msg, headers, newurl)`


### 顶层函数

#### def `url_origin(url: str) -> tuple[str, str, int | None]`

Return a normalized (scheme, hostname, effective port) origin.

#### def `open_credentialed_url(request: urllib.request.Request, timeout: float, opener_factory: Callable[..., Any] | None = None)`

Open a request without forwarding credentials across origins.

The default preserves an application-installed opener's proxy, TLS,
cookies, custom protocol handlers, and instrumentation while replacing its
redirect handler. ``opener_factory`` is an explicit test seam; security is
never disabled based on global ``urlopen`` identity.


## hermes_cli.voice

### 模块文档

Process-wide voice recording + TTS API for the TUI gateway.

Wraps ``tools.voice_mode`` (recording/transcription) and ``tools.tts_tool``
(text-to-speech) behind idempotent, stateful entry points that the gateway's
``voice.record``, ``voice.toggle``, and ``voice.tts`` JSON-RPC handlers can
call from a dedicated thread. The gateway imports this module lazily so that
missing optional audio deps (sounddevice, faster-whisper, numpy) surface as
an ``ImportError`` at call time, not at startup.

Two usage modes are exposed:

* **Push-to-talk** (``start_recording`` / ``stop_and_transcribe``) — single
  manually-bounded capture used when the caller drives the start/stop pair
  explicitly.
* **Continuous (VAD)** (``start_continuous`` / ``stop_continuous``) — mirrors
  the classic CLI voice mode: recording auto-stops on silence, transcribes,
  hands the result to a callback, and then auto-restarts for the next turn.
  Three consecutive no-speech cycles stop the loop and fire
  ``on_silent_limit`` so the UI can turn the mode off.

### 顶层函数

#### def `voice_record_key_from_config(cfg: Any) -> Any`

Shape-safe ``cfg.voice.record_key`` lookup.

``load_config()`` deep-merges raw YAML and preserves scalar
overrides, so a hand-edited ``voice: true`` / ``voice: cmd+b``
leaves ``cfg["voice"]`` as a bool/str instead of a dict, and the
naive ``.get("voice", {}).get("record_key")`` chain raises
AttributeError before voice can even start (Copilot round-11 on
#19835). Return ``None`` for malformed shapes so call sites can
feed the result straight into the normalizer/formatter and get
the documented default.

#### def `normalize_voice_record_key_for_prompt_toolkit(raw: Any) -> str`

Coerce ``voice.record_key`` into prompt_toolkit's ``c-x`` / ``a-x`` format.

Mirrors the TUI parser contract (``ui-tui/src/lib/platform.ts``)
so one config value binds the same shortcut in both runtimes:

* non-string / empty / typo'd / bare-char / multi-modifier / reserved
  ``ctrl+c|d|l`` → documented default ``c-b``
* single-char keys: ``ctrl+o`` → ``c-o``
* named keys: ``ctrl+space`` → ``c-space`` (aliases collapse:
  ``ctrl+return`` → ``c-enter``)
* ``super`` / ``win`` / ``windows`` → ``c-b`` (TUI-only modifiers —
  prompt_toolkit has no super mod; the CLI binding site is
  expected to warn when this fallback fires so users see the
  cross-runtime split, Copilot round-11 on #19835)

#### def `format_voice_record_key_for_status(raw: Any) -> str`

Render ``voice.record_key`` for ``/voice status`` in CLI-friendly form.

Mirrors the TUI's ``formatVoiceRecordKey``: returns ``Ctrl+B`` /
``Alt+Space`` / ``Ctrl+Enter``. Malformed configs surface as the
documented default so status never advertises a shortcut that
won't bind (Copilot round-10 on #19835).

#### def `start_recording() -> None`

Begin capturing from the default input device (push-to-talk).

Idempotent — calling again while a recording is in progress is a no-op.

#### def `stop_and_transcribe() -> Optional[str]`

Stop the active push-to-talk recording, transcribe, return text.

Returns ``None`` when no recording is active, when the microphone
captured no speech, or when Whisper returned a known hallucination.

#### def `start_continuous(on_transcript: Callable[[str], None], on_status: Optional[Callable[[str], None]] = None, on_silent_limit: Optional[Callable[[], None]] = None, silence_threshold: int = 200, silence_duration: float = 3.0, auto_restart: bool = True) -> bool`

Start a VAD-driven continuous recording loop.

The loop calls ``on_transcript(text)`` each time speech is detected and
transcribed successfully. If ``auto_restart`` is True, it auto-restarts
for the next turn and resets the no-speech counter for that loop. If
``auto_restart`` is False, the first silence-triggered transcription ends
the loop and reports ``"idle"``; no-speech counts are retained across
starts so a push-to-talk caller can still enforce the three-strikes guard.
After ``_CONTINUOUS_NO_SPEECH_LIMIT`` consecutive silent cycles (no speech
picked up at all) the loop stops itself and calls ``on_silent_limit`` so the
UI can reflect "voice off". Returns False if a previous stop is still
transcribing/cleaning up; otherwise returns True. Idempotent — calling while
already active is a successful no-op.

``on_status`` is called with ``"listening"`` / ``"transcribing"`` /
``"idle"`` so the UI can show a live indicator.

#### def `stop_continuous(force_transcribe: bool = False) -> None`

Stop the active continuous loop and release the microphone.

Idempotent — calling while not active is a no-op. If ``force_transcribe`` is
True, the recorder stops synchronously, then transcription/cleanup runs on a
background thread before reporting ``"idle"``. Otherwise the buffer is
discarded.

#### def `is_continuous_active() -> bool`

Whether a continuous voice loop is currently running.

#### def `speak_text(text: str) -> None`

Synthesize ``text`` with the configured TTS provider and play it.

Mirrors cli.py:_voice_speak_response exactly — same markdown strip
pipeline, same 4000-char cap, same explicit mp3 output path, same
MP3-over-OGG playback choice (afplay misbehaves on OGG), same cleanup
of both extensions. Keeping these in sync means a voice-mode TTS
session in the TUI sounds identical to one in the classic CLI.

While playback is in flight the module-level _tts_playing Event is
cleared so the continuous-recording loop knows to wait before
re-arming the mic (otherwise the agent's spoken reply feedback-loops
through the microphone and the agent ends up replying to itself).


## hermes_cli.web_git

### 模块文档

Backend git operations for the desktop coding rail + Codex-style review pane.

The desktop's git affordances (coding-rail status, worktree lanes, review pane,
branch switch) run as Electron-local git on the user's machine. On a *remote*
gateway those would operate on the wrong filesystem, so this module mirrors them
over the dashboard's authenticated REST surface — the same pattern as ``/api/fs``.

Everything shells out to the system ``git`` (and ``gh`` for ship info / PRs).
Reads degrade to ``None`` / empty on a non-repo; mutations raise so the renderer
can surface a toast. Callers pass an already path-hardened ``cwd``.

### 顶层函数

#### def `resolve_rename_path(raw: str) -> str`

``old => new`` (and ``dir/{old => new}/f``) → the NEW path, so a row
addresses the real file for diff/stage.

#### def `repo_status(cwd: str) -> dict | None`

Compact working-tree status for the coding rail. None on a non-repo.

#### def `review_list(cwd: str, scope: str, base_ref: str | None) -> dict`

Changed files for a scope. Mirrors the Electron reviewList shapes.

#### def `review_diff(cwd: str, file_path: str, scope: str, base_ref: str | None, staged: bool) -> str`

#### def `file_diff_vs_head(cwd: str, file_path: str) -> str`

Working-tree-vs-HEAD diff for one file (the preview's diff view). Unlike
review_diff, never all-adds a clean tracked file; only a genuinely untracked one.

#### def `review_stage(cwd: str, file_path: str | None) -> dict`

#### def `review_unstage(cwd: str, file_path: str | None) -> dict`

#### def `review_revert(cwd: str, file_path: str | None) -> dict`

Discard changes back to the committed state (restore tracked, remove untracked).

#### def `review_rev_parse(cwd: str, ref: str | None) -> str | None`

#### def `review_commit(cwd: str, message: str, push: bool) -> dict`

Commit the working tree; stage everything first when nothing is staged.

#### def `review_push(cwd: str) -> dict`

#### def `review_commit_context(cwd: str) -> dict`

Diff of what WILL commit + recent subjects, for drafting a commit message.

#### def `review_ship_info(cwd: str) -> dict`

gh availability/auth + this branch's PR. ghReady false when gh missing/unauthed.

#### def `review_create_pr(cwd: str) -> dict`

Create a PR for the current branch (push first), letting gh fill title/body.

**异常**: `RuntimeError`

#### def `worktree_list(cwd: str) -> list[dict]`

#### def `worktree_add(cwd: str, options: dict) -> dict`

**异常**: `RuntimeError`

#### def `worktree_remove(cwd: str, worktree_path: str, force: bool) -> dict`

#### def `branch_list(cwd: str) -> list[dict]`

#### def `branch_switch(cwd: str, branch: str) -> dict`

**异常**: `RuntimeError`

#### def `base_branch_list(cwd: str) -> list[dict]`

Local heads + remote-tracking refs for the base-branch picker.

The remote default (origin/HEAD) is flagged so the UI can preselect it.


## hermes_cli.web_server

### 模块文档

Hermes Agent — Web UI server.

Provides a FastAPI backend serving the Vite/React frontend and REST API
endpoints for managing configuration, environment variables, and sessions.

Usage:
    python -m hermes_cli.main web          # Start on http://127.0.0.1:9119
    python -m hermes_cli.main web --port 8080

### class ConfigUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class EnvVarUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class EnvVarDelete

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class EnvVarReveal

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MemoryProviderConfigUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MemoryProviderSetupRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class CustomEndpointUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MessagingPlatformUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class TelegramOnboardingStart

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class TelegramOnboardingApply

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class WhatsAppOnboardingStart

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class WhatsAppOnboardingApply

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class AudioTranscriptionRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ManagedFileUpload

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ChatImageUpload

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ManagedDirectoryCreate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ManagedFileDelete

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ModelAssignment

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）

Payload for POST /api/model/set — assign a provider/model to a slot.

scope="main"        → writes model.provider + model.default
scope="auxiliary"   → writes auxiliary.<task>.provider + auxiliary.<task>.model
scope="auxiliary" with task=""  → applied to every auxiliary.* slot
scope="auxiliary" with task="__reset__"  → resets every slot to provider="auto"


### class MoaModelSlot

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MoaPresetPayload

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MoaConfigPayload

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ManagedFilesPolicy

> 继承: `object` ｜ 方法数: 0（公开 0）


### class FsWriteText

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class GitPathBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class GitFileBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class GitCommitBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class GitWorktreeAddBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class GitWorktreeRemoveBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class GitBranchSwitchBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class CuratorPause

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class LearningNodeRef

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class LearningNodeEdit

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class DebugShareRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class TTSSpeakRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class OAuthSubmitBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class BulkDeleteSessions

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SessionImport

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SessionRename

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SessionPrune

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class CronJobCreate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class CronJobUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class AutomationBlueprintInstantiate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MCPServerCreate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MCPServersReplace

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MCPEnabledToggle

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MCPCatalogInstall

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class PairingApprove

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class PairingRevoke

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class WebhookCreate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class WebhookEnabledToggle

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class CredentialPoolAdd

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MemoryProviderSelect

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class MemoryReset

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class BackupRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ImportRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class HookCreate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class HookDelete

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SkillInstallRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SkillUninstallRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SkillsUpdateRequest

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ProfileCreate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ProfileRename

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ProfileSoulUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ProfileActiveUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ProfileDescriptionUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ProfileModelUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ProfileDescribeAuto

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SkillToggle

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SkillCreate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SkillContentUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ToolsetToggle

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ToolsetProviderSelect

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ToolsetModelSelect

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ToolsetEnvUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ToolsetPostSetup

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class TerminalBackendSelect

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class RawConfigUpdate

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ThemeSetBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class FontSetBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `should_require_auth(host: str, allow_public: bool = False) -> bool`

Return True iff the dashboard auth gate must be active.

Truth table:
  host == loopback        → False (no auth — local-only, trusted operator)
  host != loopback        → True  (gate engages — OAuth or password required)

"Loopback" is 127.0.0.1, localhost, ::1. RFC1918 / CGNAT / link-local are
deliberately treated as PUBLIC — a hostile device on the same LAN is exactly
the threat model the gate is designed for.

``allow_public`` (the legacy ``--insecure`` escape hatch) NO LONGER disables
the gate. It is accepted for backward-compat with old launch scripts and
desktop shells but is ignored: a non-loopback bind ALWAYS requires an auth
provider (OAuth or the bundled password provider). This closes the
unauthenticated-public-dashboard hole behind the June 2026 ``hermes-0day``
MCP-persistence campaign, where ``--insecure --host 0.0.0.0`` left the
config/MCP/agent surface open to internet scanners.

#### def `host_header_middleware(request: Request, call_next)`

Reject requests whose Host header doesn't match the bound interface.

Defends against DNS rebinding: a victim browser on a localhost
dashboard is tricked into fetching from an attacker hostname that
TTL-flips to 127.0.0.1. CORS and same-origin checks don't help —
the browser now treats the attacker origin as same-origin with the
dashboard. Host-header validation at the app layer catches it.

See GHSA-ppp5-vxwm-4cf7.

#### def `auth_middleware(request: Request, call_next)`

Require the session token on all /api/ routes except the public list.

#### def `get_media(path: str)`

Return a gateway-local image file as a base64 data URL.

Lets remote clients (the desktop app over the network, or the web dashboard
in a browser) display images the agent wrote to *this* machine's filesystem
— they can't read the gateway's local disk directly.

Auth-gated by the session token like every other /api route. Restricted to
an image-extension allowlist, a size cap, AND the gateway's own media roots
(resolved, symlink-safe) so it can't be used to read arbitrary files.

**异常**: `HTTPException`

#### def `upload_chat_image(payload: ChatImageUpload, profile: Optional[str] = None)`

Persist a browser-provided chat image where the embedded TUI can read it.

The dashboard /chat page runs Hermes inside an xterm.js PTY. Browser
clipboard image bytes are not visible to the server-side clipboard, so the
page uploads them here, then drives the TUI's ``/image <path>`` command
with the returned gateway-visible path. Files land under
``HERMES_HOME/images/`` — the same directory ``clipboard.paste`` /
``image.attach`` already use.

**异常**: `HTTPException`

#### def `list_managed_files(request: Request, path: Optional[str] = None)`

**异常**: `HTTPException`

#### def `read_managed_file(request: Request, path: str)`

**异常**: `HTTPException`

#### def `download_managed_file(request: Request, path: str)`

Stream a managed file as an attachment download.

Remote clients (desktop app, browser dashboard) open agent-written files
that live on *this* gateway's disk, not theirs. Auth-gated like every other
managed-files route — ``auth_middleware`` additionally accepts the session
token as a ``?token=`` query param here so a shell/browser-opened download
(which can't set the session header) still authenticates. See ``/api/pty``
for the same query-token precedent.

**异常**: `HTTPException`

#### def `upload_managed_file(payload: ManagedFileUpload, request: Request)`

**异常**: `HTTPException`

#### def `upload_managed_file_stream(request: Request, file: UploadFile = File(...), path: str = Form(...), overwrite: bool = Form(True))`

**异常**: `HTTPException`

#### def `create_managed_directory(payload: ManagedDirectoryCreate, request: Request)`

**异常**: `HTTPException`

#### def `delete_managed_file(payload: ManagedFileDelete, request: Request)`

**异常**: `HTTPException`

#### def `fs_list(path: str)`

#### def `fs_read_text(path: str)`

**异常**: `HTTPException`

#### def `fs_write_text(payload: FsWriteText)`

Overwrite (or create) a UTF-8 text file for the in-app spot editor.

Mirrors the local Electron ``hermes:fs:writeText`` hardening: the path is
resolved + validated by ``_fs_path``, the parent directory must already
exist (we never build directory trees), only regular files may be replaced,
and the payload is size-capped. The write is staged to a sibling temp file
and ``os.replace``-d into place so a crash mid-write can't truncate the
original. Stale-on-disk detection is the client's job (re-read before save),
so both transports behave identically.

**异常**: `HTTPException`

#### def `fs_read_data_url(path: str)`

**异常**: `HTTPException`

#### def `fs_git_root(path: str)`

#### def `fs_default_cwd()`

#### def `git_status_route(path: str)`

#### def `git_worktrees_route(path: str)`

#### def `git_branches_route(path: str)`

#### def `git_base_branches_route(path: str)`

#### def `git_review_list_route(path: str, scope: str = 'uncommitted', base: Optional[str] = None)`

#### def `git_review_diff_route(path: str, file: str, scope: str = 'uncommitted', base: Optional[str] = None, staged: bool = False)`

#### def `git_file_diff_route(path: str, file: str)`

#### def `git_commit_context_route(path: str)`

#### def `git_rev_parse_route(path: str, ref: Optional[str] = None)`

#### def `git_ship_info_route(path: str)`

#### def `git_stage_route(body: GitFileBody)`

#### def `git_unstage_route(body: GitFileBody)`

#### def `git_revert_route(body: GitFileBody)`

#### def `git_commit_route(body: GitCommitBody)`

#### def `git_push_route(body: GitPathBody)`

#### def `git_create_pr_route(body: GitPathBody)`

#### def `git_worktree_add_route(body: GitWorktreeAddBody)`

#### def `git_worktree_remove_route(body: GitWorktreeRemoveBody)`

#### def `git_branch_switch_route(body: GitBranchSwitchBody)`

#### def `get_status(profile: Optional[str] = None)`

#### def `get_system_stats()`

Host + process system stats for the System page.

OS / Python / host identity from stdlib; CPU / memory / disk / uptime from
psutil when available, with graceful degradation when it isn't.  Read-only
and non-sensitive (no env values, no paths beyond the hermes home root).

#### def `get_curator_status()`

**异常**: `HTTPException`

#### def `set_curator_paused(body: CuratorPause)`

#### def `run_curator()`

Trigger a curator review now (backgrounded; tail via action status).

**异常**: `HTTPException`

#### def `get_learning_graph(profile: Optional[str] = None)`

Learning graph payload for the desktop panel.

Profile-scoped view of learned, non-base skills plus memory chunks, with
graph links derived from skill relations and memory-skill overlap.

**异常**: `HTTPException`

#### def `get_learning_node(id: str, profile: Optional[str] = None)`

Current content of a journey node (skill SKILL.md or memory chunk), for an edit prefill.

**异常**: `HTTPException`

#### def `delete_learning_node(body: LearningNodeRef)`

Delete a journey node — skills are archived (restorable), memories removed.

**异常**: `HTTPException`

#### def `update_learning_node(body: LearningNodeEdit)`

Rewrite a journey node's content (SKILL.md or memory chunk).

**异常**: `HTTPException`

#### def `get_portal_status()`

#### def `run_prompt_size()`

**异常**: `HTTPException`

#### def `run_dump()`

**异常**: `HTTPException`

#### def `run_config_migrate()`

**异常**: `HTTPException`

#### def `run_debug_share_endpoint(body: DebugShareRequest | None = None)`

Upload a redacted debug report + full logs and return the paste URLs.

Unlike the other diagnostics actions (doctor, dump, prompt-size) this is
*synchronous*: the whole point of ``debug share`` is the set of shareable
URLs it produces, so we run the upload in a worker thread and return the
structured ``{urls, failures, redacted, ...}`` payload directly. The
dashboard renders those as real, copyable links instead of scraping a log
tail. Pastes auto-delete after 6 hours (handled inside the share core).

**异常**: `HTTPException`

#### def `restart_gateway(profile: Optional[str] = None)`

Kick off a ``hermes gateway restart`` in the background.

**异常**: `HTTPException`

#### def `gateway_drain(request: Request)`

Begin or cancel an external (NAS-driven) gateway drain.

Authenticated by the non-interactive token-auth seam: the
``dashboard_auth/drain`` plugin registers this exact path as a token route
and verifies the ``Authorization`` bearer secret. If that plugin isn't
active (no ``HERMES_DASHBOARD_DRAIN_SECRET``), the route is NOT a token
route, so on a gated bind the cookie gate handles it (a browser session can
still drive it from the dashboard) and on a loopback bind the legacy
session-token gate applies — either way it is never unauthenticated on a
network-exposed bind.

Body: ``{"action": "drain"}`` (begin) or ``{"action": "cancel"}`` (cancel).
Begin writes the ``.drain_request.json`` marker the gateway's
``_drain_control_watcher`` observes (flip to ``draining`` + refuse new
turns); cancel removes it (revert to ``running`` + re-accept). Idempotent
on both sides. This endpoint only writes/removes the marker — the gateway
process owns the actual state transition (there is no HTTP control channel
into the running gateway; the marker IS the channel, decisions.md Q-B).

The force-override (D6: "unless a user commands it") is NOT here — an
immediate, drain-skipping action maps onto the existing
``POST /api/gateway/restart`` force path, which supersedes a drain.

**异常**: `HTTPException`

#### def `update_hermes()`

Kick off ``hermes update`` in the background.

**异常**: `HTTPException`

#### def `check_hermes_update(force: bool = False)`

Report whether a Hermes update is available, without applying it.

Powers the dashboard's "check before you update" flow: the System page
shows the commit-behind count and asks the user to confirm before
``POST /api/hermes/update`` actually runs ``hermes update``.

Returns:
    install_method: 'git' | 'pip' | 'docker' | 'nixos' | 'homebrew' | ...
    current_version: installed Hermes version string
    behind: commits behind upstream (>=1), 0 if up to date,
            -1 if behind by an unknown count (nix/pypi), or null if the
            check could not run (offline, no remote, etc.)
    update_available: convenience bool (behind is non-zero and not null)
    can_apply: True when the dashboard's update button can apply it
               in place (git/pip); False for docker/nix/homebrew where the
               user must update out-of-band
    update_command: the recommended command for this install method
    message: human-readable guidance for non-applyable methods
    commits: for git/pip installs that are behind, a list of the commits
             the local checkout is behind upstream by — each
             {sha, summary, author, at}. Absent/empty otherwise. The
             desktop's remote update overlay renders this as "what's
             changed". Additive: existing consumers ignore it.

#### def `transcribe_audio_upload(payload: AudioTranscriptionRequest)`

**异常**: `HTTPException`

#### def `get_elevenlabs_voices()`

Return ElevenLabs voices when an API key is configured.

The desktop UI uses this for the ``tts.elevenlabs.voice_id`` dropdown.
Only non-secret voice metadata is returned; the API key stays server-side.

**异常**: `HTTPException`

#### def `speak_text(payload: TTSSpeakRequest)`

Synthesize speech and return audio as base64 data URL.

Used by the desktop voice-conversation mode to play back assistant
responses without exposing the on-disk file path. Reuses the
existing TTS provider chain (Edge / OpenAI / ElevenLabs / etc.)
configured in ``~/.hermes/config.yaml`` under ``tts.``.

**异常**: `HTTPException`

#### def `get_action_status(name: str, lines: int = 200)`

Tail an action log and report whether the process is still running.

**异常**: `HTTPException`

#### def `get_sessions(limit: int = 20, offset: int = 0, min_messages: int = 0, archived: str = 'exclude', order: str = 'created', source: str = None, exclude_sources: str = None, cwd_prefix: str = None, full: bool = False, profile: Optional[str] = None)`

List sessions.

``archived`` controls how soft-archived sessions are treated:
``exclude`` (default) hides them, ``only`` returns just the archived ones
(used by the desktop "Archived sessions" settings panel), and ``include``
returns both.

``order`` controls pagination order: ``created`` (default, by original
start time) or ``recent`` (by latest activity across the compression
chain). ``recent`` keeps a long-running conversation on the first page
after it auto-compresses into a fresh continuation id.

Rows omit ``system_prompt``/``model_config`` (the payload-dominating
fields no list UI reads) unless ``full=1`` is passed.

**异常**: `HTTPException`

#### def `get_profiles_sessions(limit: int = 20, offset: int = 0, min_messages: int = 0, archived: str = 'exclude', order: str = 'recent', profile: str = 'all', source: str = None, exclude_sources: str = None, full: bool = False)`

Unified, read-only session list aggregated across ALL profiles.

Intentionally process-light: this opens each profile's ``state.db`` directly
from disk — it does NOT spawn a dashboard backend per profile. Each returned
session is tagged with its owning ``profile`` so the desktop renders one
browsable list and only spins up a profile's backend when the user actually
interacts (sends a message). A user with a single (default) profile gets the
same rows as ``/api/sessions``, just tagged ``profile="default"``.

Rows omit ``system_prompt``/``model_config`` unless ``full=1`` — same
list projection as ``/api/sessions``.

**异常**: `HTTPException`

#### def `get_profiles_sessions_sidebar(recents_profile: str = 'all', recents_limit: int = 20, recents_exclude: str = None, cron_limit: int = 50, messaging_limit: int = 100, messaging_exclude: str = None)`

Batched sidebar session slices — one profile-DB open per refresh.

The desktop sidebar needs three source-scoped windows per refresh: recents
(local chats, scoped to the active profile), cron sessions (all profiles),
and messaging-platform sessions (all profiles). Served as three separate
``/api/profiles/sessions`` calls they reopened every profile's ``state.db``
three times and re-counted each refresh. This opens each DB once and runs
the three filtered queries together, returning the three windows in one
payload. Read-only and process-light, same row projection and 300s active
heuristic as ``/api/profiles/sessions``.

The caller passes the source taxonomy (``recents_exclude`` /
``messaging_exclude`` CSV, ``source=cron`` is implicit) so this stays
taxonomy-agnostic like the per-slice endpoint. All three slices use
``min_messages=1`` / ``archived=exclude`` / recency order, matching the
desktop's per-slice calls.

#### def `search_sessions(q: str = '', limit: int = 20, profile: Optional[str] = None)`

Search sessions by ID plus full-text message content using FTS5.

Direct session-id matches are surfaced first, then FTS message-content
matches. Results are deduped by compression lineage, not by raw
``session_id``. Auto-compression rotates a conversation onto a fresh
session id (and leaves the old segment's messages in the FTS index), so one
logical chat can own many ``sessions`` rows that all match the same query.
Branches also use ``parent_session_id``, but they are real alternate
conversations; don't collapse branch-specific hits back into the parent.

**异常**: `HTTPException`

#### def `get_memory_provider_config(name: str, surface: Optional[str] = None, profile: Optional[str] = None)`

#### def `setup_memory_provider(name: str, body: MemoryProviderSetupRequest)`

**异常**: `HTTPException`

#### def `update_memory_provider_config(name: str, body: MemoryProviderConfigUpdate, surface: Optional[str] = None, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `get_config(profile: Optional[str] = None)`

#### def `get_defaults()`

#### def `get_schema(profile: Optional[str] = None)`

#### def `get_model_info(profile: Optional[str] = None)`

Return resolved model metadata for the currently configured model.

Calls the same context-length resolution chain the agent uses, so the
frontend can display "Auto-detected: 200K" alongside the override field.
Also returns model capabilities (vision, reasoning, tools) when available.

#### def `get_model_options(profile: Optional[str] = None, refresh: bool = False, include_unconfigured: bool = False, explicit_only: bool = False)`

Return authenticated providers + their curated model lists.

REST equivalent of the ``model.options`` JSON-RPC on tui_gateway, so the
dashboard Models page can render the picker without a live chat session.
The response shape matches ``model.options`` 1:1 so ``ModelPickerDialog``
can share the same types.

``profile`` scopes the picker context (current model/provider, custom
providers from config, per-profile .env auth state) so the Models page
reads the SAME profile /api/model/set writes.

``refresh`` busts the per-provider model-id disk cache so every row
re-fetches its live catalog — used by the picker's explicit "Refresh
Models" control. Normal opens leave it false to stay on the 1h cache.

**异常**: `HTTPException`

#### def `get_recommended_default_model(provider: str = '')`

Return the recommended default model for a freshly-authenticated provider.

Mirrors the model-curation `hermes model` does so GUI onboarding lands on a
sensible default instead of blindly taking the first curated entry. For
Nous this honors the user's free/paid tier: free users get a free model,
paid users get the full curated default. For any other provider it falls
back to the first curated model (same as before).

Response: {"provider": str, "model": str, "free_tier": bool | None}
where free_tier is True/False for Nous and None otherwise. `model` may be
empty if nothing could be resolved (caller degrades gracefully).

#### def `get_auxiliary_models(profile: Optional[str] = None)`

Return current auxiliary task assignments.

Shape:
  {
    "tasks": [
      {"task": "vision", "provider": "auto", "model": "", "base_url": ""},
      ...
    ],
    "main": {"provider": "openrouter", "model": "anthropic/claude-opus-4.7"},
  }

``profile`` scopes the read — without it, the Models page would show
the dashboard profile's auxiliary pins while /api/model/set wrote the
selected profile's (read/write asymmetry).

**异常**: `HTTPException`

#### def `get_moa_models(profile: Optional[str] = None)`

Return the configured Mixture-of-Agents provider/model slots.

**异常**: `HTTPException`

#### def `set_moa_models(body: MoaConfigPayload, profile: Optional[str] = None)`

Persist the Mixture-of-Agents provider/model slots.

**异常**: `HTTPException`

#### def `set_model_assignment(body: ModelAssignment, profile: Optional[str] = None)`

Assign a model to the main slot or an auxiliary task slot.

Writes to ``~/.hermes/config.yaml`` — applies to **new** sessions only.
The currently running chat PTY (if any) is not affected; use the
``/model`` slash command inside a chat to hot-swap that specific session.

**异常**: `HTTPException`

#### def `update_config(body: ConfigUpdate, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `get_env_vars(profile: Optional[str] = None)`

#### def `set_env_var(body: EnvVarUpdate, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `list_custom_endpoints()`

Return configured OpenAI-compatible custom endpoints for Desktop.

**异常**: `HTTPException`

#### def `upsert_custom_endpoint(body: CustomEndpointUpdate)`

Create or update a v12+ ``providers`` custom endpoint entry.

**异常**: `HTTPException`

#### def `activate_custom_endpoint(endpoint_id: str)`

Set a configured custom endpoint as the default model provider.

**异常**: `HTTPException`

#### def `delete_custom_endpoint(endpoint_id: str)`

Remove a configured custom endpoint from ``providers``.

**异常**: `HTTPException`

#### def `validate_custom_endpoint(body: CustomEndpointUpdate)`

Probe a custom endpoint by calling its OpenAI-compatible /models URL.

#### def `validate_provider_credential(body: EnvVarUpdate, request: Request)`

Live-probe a provider credential before it's saved.

Returns {ok, reachable, message}. ok=True means the provider accepted the
key; ok=False + reachable=True means the key is bad (caller should block);
reachable=False means the network probe couldn't run (caller may save with
a warning rather than hard-blocking offline users).

#### def `remove_env_var(body: EnvVarDelete, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `reveal_env_var(body: EnvVarReveal, request: Request, profile: Optional[str] = None)`

Return the real (unredacted) value of a single env var.

Protected by:
- Ephemeral session token (generated per server start, injected into SPA)
- Rate limiting (max 5 reveals per 30s window)
- Audit logging

**异常**: `HTTPException`

#### def `start_whatsapp_onboarding(body: WhatsAppOnboardingStart)`

#### def `get_whatsapp_onboarding_status(pairing_id: str)`

**异常**: `HTTPException`

#### def `apply_whatsapp_onboarding(pairing_id: str, body: WhatsAppOnboardingApply, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `cancel_whatsapp_onboarding(pairing_id: str)`

#### def `start_telegram_onboarding(body: TelegramOnboardingStart)`

**异常**: `HTTPException`

#### def `get_telegram_onboarding_status(pairing_id: str)`

**异常**: `HTTPException`

#### def `apply_telegram_onboarding(pairing_id: str, body: TelegramOnboardingApply, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `cancel_telegram_onboarding(pairing_id: str)`

#### def `get_messaging_platforms(profile: Optional[str] = None)`

#### def `update_messaging_platform(platform_id: str, body: MessagingPlatformUpdate, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `test_messaging_platform(platform_id: str, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `list_oauth_providers(profile: Optional[str] = None)`

Enumerate every OAuth-capable LLM provider with current status.

Response shape (per provider):
    id              stable identifier (used in DELETE path)
    name            human label
    flow            "pkce" | "device_code" | "external"
    cli_command     fallback CLI command for users to run manually
    disconnect_command  shell command that clears an external provider's
                        creds (run in the embedded terminal), else null
    docs_url        external docs/portal link for the "Learn more" link
    status:
      logged_in        bool — currently has usable creds
      source           short slug ("hermes_pkce", "claude_code", ...)
      source_label     human-readable origin (file path, env var name)
      token_preview    last N chars of the token, never the full token
      expires_at       ISO timestamp string or null
      has_refresh_token bool

Membership is derived from the unified provider_catalog() so this stays in
sync with the `hermes model` picker; _OAUTH_OVERRIDES supplies per-provider
flow/status/cli metadata.

#### def `disconnect_oauth_provider(provider_id: str, request: Request, profile: Optional[str] = None)`

Disconnect an OAuth provider. Token-protected (matches /env/reveal).

**异常**: `HTTPException`

#### def `start_oauth_login(provider_id: str, request: Request, profile: Optional[str] = None)`

Initiate an OAuth login flow. Token-protected.

**异常**: `HTTPException`

#### def `submit_oauth_code(provider_id: str, body: OAuthSubmitBody, request: Request, profile: Optional[str] = None)`

Submit the auth code for PKCE flows. Token-protected.

**异常**: `HTTPException`

#### def `poll_oauth_session(provider_id: str, session_id: str, profile: Optional[str] = None)`

Poll a session's status (no auth — read-only state).

Shared by the device-code flows (Nous, OpenAI Codex, MiniMax, xAI).
Each surfaces progress through the same background-worker-updated
``status`` field, so a single poll endpoint serves them all.

**异常**: `HTTPException`

#### def `cancel_oauth_session(session_id: str, request: Request, profile: Optional[str] = None)`

Cancel a pending OAuth session. Token-protected.

#### def `bulk_delete_sessions_endpoint(body: BulkDeleteSessions)`

Delete every session in ``body.ids`` in a single DB transaction.

Backs the dashboard's bulk-select-and-delete flow on the sessions
page. POST (not DELETE) because most HTTP clients refuse to send a
request body on DELETE and a body is the natural shape for a list
of IDs — Starlette accepts both, but POSTing a list keeps proxies,
curl, and the browser ``fetch`` API consistent.

Per-row contract matches :meth:`SessionDB.delete_sessions`:

* Unknown IDs are silently skipped (the response ``deleted`` count
  reflects what really happened, not the input length). This is
  deliberate — UI selection state can race against another tab's
  delete, and we'd rather succeed-on-the-rest than fail-the-whole-
  batch.
* Children of every deleted parent are orphaned, not cascade-
  deleted.
* Active and archived sessions ARE deleted when explicitly
  selected — unlike ``DELETE /api/sessions/empty``, the user
  hand-picked the rows so we trust the selection.
* Like the other session-delete endpoints, this does NOT pass a
  ``sessions_dir`` through; on-disk transcript / request-dump
  cleanup runs at the CLI/agent layer on the next prune pass.

The response carries the actual deleted count, so the dashboard
can surface it in a toast. The IDs that were removed are not
echoed back because the client already knows what it asked to
delete (unknown IDs are silently skipped — see contract above)
and can prune its in-memory list directly from the request.

**异常**: `HTTPException`

#### def `import_sessions_endpoint(request: Request)`

Import one or more sessions exported from the dashboard or CLI.

This is intentionally separate from ``/api/ops/import``: that endpoint
restores a whole Hermes backup archive, while this endpoint is scoped to
session rows/messages and is safe to use from the Sessions page.

**异常**: `HTTPException`

#### def `count_empty_sessions_endpoint(profile: Optional[str] = None)`

Return the number of empty, ended, non-archived sessions.

Drives the dashboard's "Delete empty (N)" button — when N is 0 the
UI hides the affordance so users aren't presented with a button
that does nothing. Cheap, single-COUNT query.

#### def `delete_empty_sessions_endpoint(profile: Optional[str] = None)`

Delete every empty (``message_count == 0``), ended,
non-archived session in a single transaction.

Safety contract mirrors :meth:`SessionDB.delete_empty_sessions`:

* Active sessions are skipped (``ended_at IS NULL``) so a live
  agent isn't yanked mid-handshake.
* Archived sessions are skipped — the user explicitly chose to
  keep those rows.
* Children of deleted parents are orphaned, not cascade-deleted.

Like the single-session ``DELETE /api/sessions/{id}`` endpoint
below, this doesn't pass a ``sessions_dir`` through — the on-disk
transcript / request-dump cleanup is wired at the CLI/agent layer
but the web server historically leaves file cleanup to the next
prune-on-startup pass. Matching that pre-existing trade-off keeps
the two delete endpoints' DB-vs-disk behaviour consistent.

#### def `get_session_stats(profile: Optional[str] = None)`

Session-store statistics for the Sessions page (mirrors `hermes sessions stats`).

Registered before ``/api/sessions/{session_id}`` so the literal ``stats``
path isn't captured as a session id by the parameterized route.

#### def `get_session_detail(session_id: str, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `get_session_latest_descendant(session_id: str, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `get_session_messages(session_id: str, profile: Optional[str] = None, limit: Optional[int] = None, offset: int = 0)`

**异常**: `HTTPException`

#### def `delete_session_endpoint(session_id: str, profile: Optional[str] = None)`

#### def `rename_session_endpoint(session_id: str, body: SessionRename)`

Update a session: rename (or clear its title) and/or archive it.

``title`` renames (empty/null clears the title); ``archived`` soft-hides or
restores the session. Either field may be omitted. ``profile`` targets
another profile's session.

**异常**: `HTTPException`

#### def `export_session_endpoint(session_id: str, profile: Optional[str] = None)`

Export a single session (metadata + messages) as JSON.

**异常**: `HTTPException`

#### def `prune_sessions_endpoint(body: SessionPrune)`

Delete ended sessions matching filters without blocking the event loop.

#### def `get_logs(file: str = 'agent', lines: int = 100, level: Optional[str] = None, component: Optional[str] = None, search: Optional[str] = None)`

**异常**: `HTTPException`

#### def `list_cron_jobs(profile: str = 'all')`

#### def `get_cron_job(job_id: str, profile: Optional[str] = None)`

#### def `list_cron_job_runs(job_id: str, profile: Optional[str] = None, limit: int = 20)`

#### def `create_cron_job(body: CronJobCreate, profile: Optional[str] = None)`

#### def `get_cron_delivery_targets()`

Delivery targets the cron dropdown should offer.

Always includes the implicit ``local`` option. Beyond that, the list is
derived dynamically from the configured gateway platforms via
``cron.scheduler.cron_delivery_targets()`` — no hardcoded platform list. A
configured platform that hasn't set its cron home channel is still returned
with ``home_target_set: false`` so the UI can surface it as "configure a
home channel first" rather than hiding it.

#### def `update_cron_job(job_id: str, body: CronJobUpdate, profile: Optional[str] = None)`

#### def `pause_cron_job(job_id: str, profile: Optional[str] = None)`

#### def `resume_cron_job(job_id: str, profile: Optional[str] = None)`

#### def `trigger_cron_job(job_id: str, profile: Optional[str] = None)`

#### def `delete_cron_job(job_id: str, profile: Optional[str] = None)`

#### def `cron_fire_webhook(request: Request)`

Chronos managed-cron fire webhook (NAS -> agent).

Authenticated by a short-lived NAS-minted JWT (verified by the pluggable
Chronos fire-verifier), NOT the dashboard session cookie — so this path is
in ``PUBLIC_API_PATHS`` to bypass the dashboard auth gate, and the JWT is
the real gate. This is the inbound half of scale-to-zero managed cron: NAS
POSTs here at fire time, the agent verifies, claims the job (store CAS, so
at-most-once across replicas / on a NAS retry), runs it, and re-arms the
next one-shot.

Lives on the dashboard app (not the api_server adapter) because the
dashboard is the agent's always-reachable public HTTP surface on hosted
deployments; the gateway may be idle/scaled down.

Returns 202 immediately and runs the job in the background so a long agent
turn never trips NAS's HTTP timeout.

#### def `list_cron_blueprints()`

Return the blueprint catalog as form schemas for the dashboard gallery.

The ``deliver`` slot's options are rewritten from the user's actually
configured gateway platforms (plus the universal origin/local/all), so the
form never offers a platform that isn't connected.

**异常**: `HTTPException`

#### def `instantiate_blueprint(body: AutomationBlueprintInstantiate, profile: str = 'default')`

Fill a blueprint's slots and create the cron job (form-submit path).

**异常**: `HTTPException`

#### def `list_mcp_servers(profile: Optional[str] = None)`

#### def `add_mcp_server(body: MCPServerCreate, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `replace_mcp_servers(body: MCPServersReplace, profile: Optional[str] = None)`

Replace the entire ``mcp_servers`` map (the GUI mcp.json editor's save).

The generic ``/api/config`` endpoint deep-merges maps, so it can never
delete a server key, drop an ``enabled: false`` flag, or remove a nested
field — edits looked saved but the stale entry survived on disk.  This
endpoint sets the whole map so removals actually persist.  Storage stays
the config.yaml ``mcp_servers`` key the CLI/TUI already read.

**异常**: `HTTPException`

#### def `remove_mcp_server(name: str, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `test_mcp_server(name: str, profile: Optional[str] = None)`

Connect to the server, list its tools, disconnect.  Returns tool list.

**异常**: `HTTPException`

#### def `auth_mcp_server(name: str, request: Request, profile: Optional[str] = None)`

Start MCP OAuth and hand the authorization URL to the dashboard browser.

**异常**: `HTTPException`

#### def `mcp_oauth_flow_status(flow_id: str, request: Request)`

**异常**: `HTTPException`

#### def `mcp_oauth_callback(server_name: str, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None)`

#### def `set_mcp_server_enabled(name: str, body: MCPEnabledToggle, profile: Optional[str] = None)`

Enable or disable an MCP server (takes effect on next session/gateway).

Toggles the ``enabled`` key on the server's config.yaml entry — the same
flag the agent reads at startup.  Disabled servers stay in config so they
can be re-enabled without re-entering their settings.

**异常**: `HTTPException`

#### def `list_mcp_catalog(profile: Optional[str] = None)`

Browse the Nous-approved MCP catalog (the optional-mcps/ manifests).

Each entry reports whether it's already installed and enabled so the UI
can show install / enabled state inline.  This is the same catalog
`hermes mcp catalog` / `hermes mcp install` read.  ``profile`` scopes
the installed/enabled annotations (the catalog itself is repo-shipped
and identical for every profile).

**异常**: `HTTPException`

#### def `install_mcp_catalog_entry(body: MCPCatalogInstall, profile: Optional[str] = None)`

Install a catalog MCP into config.yaml.

For HTTP/stdio entries with required env vars, those are written to .env
via the standard env path so the agent can read them at session start.
Entries that need a git bootstrap (``needs_install``) are installed via
the CLI action path because the clone can take time.

**异常**: `HTTPException`

#### def `list_pairing()`

#### def `approve_pairing(body: PairingApprove)`

**异常**: `HTTPException`

#### def `revoke_pairing(body: PairingRevoke)`

**异常**: `HTTPException`

#### def `clear_pending_pairing()`

#### def `list_webhooks()`

#### def `enable_webhooks()`

**异常**: `HTTPException`

#### def `create_webhook(body: WebhookCreate)`

**异常**: `HTTPException`

#### def `delete_webhook(name: str)`

**异常**: `HTTPException`

#### def `set_webhook_enabled(name: str, body: WebhookEnabledToggle)`

Enable or disable a webhook route.

Disabled routes stay in the subscriptions file (so they can be
re-enabled) but the gateway rejects incoming events with 403.  The
gateway hot-reloads the subscriptions file, so this takes effect on the
next event without a restart.

**异常**: `HTTPException`

#### def `start_gateway(profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `stop_gateway(profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `list_credential_pool()`

#### def `add_credential_pool_entry(body: CredentialPoolAdd)`

**异常**: `HTTPException`

#### def `remove_credential_pool_entry(provider: str, index: int)`

Remove a pool entry.  ``index`` is 1-based (matches the list response).

Removal must be sticky (#55217): ``load_pool()`` re-seeds entries from
their backing source (.env var, OAuth singleton file, custom-provider
config) on every call, so deleting only the pool row silently reverts on
the next dashboard refresh.  We dispatch through the same RemovalStep
registry the CLI ``hermes auth remove`` uses: each source cleans up its
external state and suppresses ``(provider, source)`` so the seeders skip
it.  Manual entries have no registered step — nothing external to clean,
no suppression needed (they aren't re-seeded).

**异常**: `HTTPException`

#### def `get_memory_status()`

#### def `set_memory_provider(body: MemoryProviderSelect)`

#### def `reset_memory(body: MemoryReset)`

**异常**: `HTTPException`

#### def `run_doctor()`

**异常**: `HTTPException`

#### def `run_security_audit()`

**异常**: `HTTPException`

#### def `run_backup(body: BackupRequest)`

**异常**: `HTTPException`

#### def `download_dashboard_backup(archive: str)`

**异常**: `HTTPException`

#### def `run_import(body: ImportRequest)`

**异常**: `HTTPException`

#### def `run_import_upload(file: UploadFile = File(...), force: bool = Form(False))`

**异常**: `HTTPException`

#### def `list_hooks()`

List configured shell hooks from config.yaml with consent + health.

Reports each hook's allowlist (consent) status and whether the script is
currently executable, plus the set of valid hook events so the create
form can offer them.

#### def `create_hook(body: HookCreate)`

Add a shell hook to config.yaml (and optionally approve it).

Shell hooks run arbitrary commands, so this is a privileged action: it
writes to the ``hooks:`` config block and, when ``approve`` is set, records
consent in the allowlist so the hook actually fires.  Takes effect on the
next session / gateway restart.

**异常**: `HTTPException`

#### def `delete_hook(body: HookDelete)`

Remove a hook from config.yaml and revoke its consent allowlist entry.

**异常**: `HTTPException`

#### def `list_checkpoints()`

List the /rollback shadow store checkpoints (read-only).

#### def `prune_checkpoints()`

**异常**: `HTTPException`

#### def `install_skill_hub(body: SkillInstallRequest, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `uninstall_skill_hub(body: SkillUninstallRequest, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `update_skills_hub(body: Optional[SkillsUpdateRequest] = None, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `list_skills_hub_sources(profile: Optional[str] = None)`

List the configured skill-hub sources and installed-skill provenance.

Gives the dashboard something to show BEFORE a search runs — which hubs
are wired up, their trust tier, and a set of featured skills pulled from
the centralized index (zero extra API calls).  Without this the Browse-hub
tab is a blank page with no indication it's even connected to anything.
``profile`` scopes the installed-skill provenance to that profile.

**异常**: `HTTPException`

#### def `search_skills_hub(q: str = '', source: str = 'all', limit: int = 20, profile: Optional[str] = None)`

Search the skill hub across all configured sources.

Network-bound (parallel source search); runs in a thread so the FastAPI
loop isn't blocked.  Returns structured results the UI installs by
identifier via POST /api/skills/hub/install, previews via
/api/skills/hub/preview, and scans via /api/skills/hub/scan.

**异常**: `HTTPException`

#### def `preview_skill_hub(identifier: str = '', profile: Optional[str] = None)`

Fetch a hub skill's SKILL.md content + metadata for in-dashboard reading.

Resolves the identifier across configured sources (same path the CLI
installer uses), then returns the rendered SKILL.md text and the file
manifest WITHOUT installing anything.  This is the 'read the actual skill
before installing' affordance the Browse-hub tab was missing.

Scoped to ``profile`` so a non-default profile with different hub taps
resolves against ITS source router, not the default profile's.

**异常**: `HTTPException`

#### def `scan_skill_hub(identifier: str = '', profile: Optional[str] = None)`

Run the install-time security scan on a hub skill WITHOUT installing it.

Fetches the bundle, quarantines it, and runs the same `scan_skill` /
`should_allow_install` pipeline the CLI installer uses — then cleans up the
quarantine.  Returns the verdict, per-finding detail, trust tier, and the
install-policy decision so the dashboard can show a visual safety result
on demand (the 'scan' button the Browse-hub tab was missing).

Scoped to ``profile`` so the bundle resolves against that profile's hub
source router, matching where an install would pull it from.

**异常**: `HTTPException`

#### def `list_profiles_endpoint()`

#### def `create_profile_endpoint(body: ProfileCreate)`

**异常**: `HTTPException`

#### def `get_active_profile_endpoint()`

Return the sticky active profile and the profile this dashboard
process is currently running as.

``active`` is the sticky default written by ``hermes profile use`` —
the profile new CLI invocations pick up. ``current`` is the profile
the running dashboard/gateway is scoped to (derived from HERMES_HOME).

#### def `set_active_profile_endpoint(body: ProfileActiveUpdate)`

Set the sticky active profile (mirrors ``hermes profile use``).

Note: this does not retarget the already-running dashboard process —
it changes which profile subsequent CLI commands and gateways use.

**异常**: `HTTPException`

#### def `get_profile_setup_command(name: str)`

#### def `open_profile_terminal_endpoint(name: str)`

**异常**: `HTTPException`

#### def `rename_profile_endpoint(name: str, body: ProfileRename)`

**异常**: `HTTPException`

#### def `delete_profile_endpoint(name: str)`

Delete a profile. The dashboard collects the user's confirmation in
its own dialog before this request, so we always pass ``yes=True`` to
skip the CLI's interactive prompt.

**异常**: `HTTPException`

#### def `get_profile_soul(name: str)`

**异常**: `HTTPException`

#### def `update_profile_soul(name: str, body: ProfileSoulUpdate)`

**异常**: `HTTPException`

#### def `update_profile_description_endpoint(name: str, body: ProfileDescriptionUpdate)`

Set or clear a profile's role description (kanban routing signal).

Empty string clears the description. Non-empty stores it as a
user-authored description (``description_auto: false``) so the
auto-describer won't overwrite it on a sweep.

**异常**: `HTTPException`

#### def `update_profile_model_endpoint(name: str, body: ProfileModelUpdate)`

Set the main model (``model.default`` + ``model.provider``) for a
specific profile's config.yaml, without touching the dashboard's own
active profile. Mirrors ``POST /api/model/set`` (main scope) but scoped
to the named profile via the HERMES_HOME override.

**异常**: `HTTPException`

#### def `describe_profile_auto_endpoint(name: str, body: ProfileDescribeAuto)`

Auto-generate a profile's description via the auxiliary LLM
(``auxiliary.profile_describer``). Mirrors ``hermes profile describe
<name> --auto``.

A failed generation (no aux client, LLM error, …) is returned as
``ok: false`` with a reason rather than an HTTP error so the UI can
surface it inline and let the operator fix config and retry.

**异常**: `HTTPException`

#### def `get_skills(profile: Optional[str] = None)`

#### def `toggle_skill(body: SkillToggle, profile: Optional[str] = None)`

#### def `get_skill_content(name: str, profile: Optional[str] = None)`

Return the raw SKILL.md text for a skill, for the dashboard editor.

**异常**: `HTTPException`

#### def `create_skill(body: SkillCreate)`

Create a new custom skill (SKILL.md) from the dashboard editor.

Calls the same validated write path as the agent's ``skill_manage``
tool (frontmatter validation, name/category validation, size limit,
optional security scan) — but bypasses the agent write-approval gate:
a write from the authenticated dashboard IS the user acting directly.

**异常**: `HTTPException`

#### def `update_skill_content(body: SkillContentUpdate)`

Replace the SKILL.md of an existing skill (full rewrite) from the editor.

**异常**: `HTTPException`

#### def `get_toolsets(profile: Optional[str] = None)`

#### def `toggle_toolset(name: str, body: ToolsetToggle, profile: Optional[str] = None)`

Enable/disable a configurable toolset for its configuration platform.

Most toolsets persist to ``platform_toolsets.cli``. Platform-restricted
toolsets instead target their supported platform (for example, Discord's
native toolsets persist to ``platform_toolsets.discord``). The shared
``_save_platform_tools`` helper keeps the GUI and CLI in lockstep. Scoped
to ``body.profile`` when provided. Returns 400 for unknown toolset keys.

**异常**: `HTTPException`

#### def `get_toolset_config(name: str, profile: Optional[str] = None)`

Return the provider matrix + key status for a toolset's config panel.

Surfaces the same provider rows the CLI ``hermes tools`` picker shows
(via ``_visible_providers``), each with its ``env_vars`` annotated with
current ``is_set`` state so the GUI can render provider selection + key
entry. Toolsets without a ``TOOL_CATEGORIES`` entry return an empty
provider list and ``has_category: false``. Returns 400 for unknown keys.

**异常**: `HTTPException`

#### def `get_toolset_models(name: str, provider: Optional[str] = None, profile: Optional[str] = None)`

Return the model catalog for a toolset backend (image/video gen).

The GUI counterpart of the model picker `hermes tools` runs after a
backend is selected — e.g. FAL's multi-model catalog (speed / strengths /
price per model). ``provider`` names a picker row; omitted, the currently
active provider is used. Toolsets without model catalogs return
``has_models: false``.

#### def `select_toolset_model(name: str, body: ToolsetModelSelect, profile: Optional[str] = None)`

Persist a backend model selection (``image_gen.model`` / ``video_gen.model``).

Validates the model against the resolved backend's catalog — the same
write the CLI's post-selection model picker performs. Returns 400 for
toolsets without model catalogs or unknown model ids.

**异常**: `HTTPException`

#### def `select_toolset_provider(name: str, body: ToolsetProviderSelect, profile: Optional[str] = None)`

Persist a provider selection for a toolset (no key prompting).

Delegates to ``apply_provider_selection`` — the shared, non-interactive
core extracted from the CLI configurator — so the GUI and ``hermes tools``
write identical config keys (``web.backend``, ``tts.provider``, etc.).
API keys and post-setup flows are handled by separate endpoints. Returns
400 for unknown toolset or provider names.

For the ``web`` toolset only, an optional ``capability`` ('search' |
'extract') scopes the selection to ``web.search_backend`` /
``web.extract_backend`` — the same per-capability overrides the runtime
dispatchers (``tools.web_tools._get_search_backend`` /
``_get_extract_backend``) resolve first. The provider must actually
support the requested capability (a search-only backend can't be the
extract backend). Omitting ``capability`` keeps the legacy whole-provider
behavior (writes ``web.backend``).

Managed Nous rows (``managed_nous_feature``) additionally report the
Portal entitlement state: the CLI flow gates these selections on
``ensure_nous_portal_access`` (inline login), but the GUI has no inline
prompt, so selecting one while logged out / unentitled used to write the
config keys and then never activate (``_is_provider_active`` requires
``managed_by_nous``). The response now carries an additive
``needs_nous_auth: true`` + ``feature`` so the client can drive the
existing Nous Portal OAuth flow (``POST /api/providers/oauth/nous/start``)
and refetch.

**异常**: `HTTPException`

#### def `save_toolset_env(name: str, body: ToolsetEnvUpdate, profile: Optional[str] = None)`

Persist API keys for a toolset's provider env vars.

Writes each ``key: value`` to ``~/.hermes/.env`` via ``save_env_value`` —
the same store ``hermes tools`` writes when it prompts for keys. Keys are
validated against the env-var allowlist for the toolset's category (the
union of every visible provider's ``env_vars``), so the GUI can't write an
arbitrary env var through this endpoint. A blank value is treated as
"leave unchanged" and skipped. Returns the saved/skipped key lists and the
refreshed ``is_set`` status. Returns 400 for unknown toolset or env keys.

**异常**: `HTTPException`

#### def `run_toolset_post_setup(name: str, body: ToolsetPostSetup, profile: Optional[str] = None)`

Spawn a provider's post-setup install hook as a background action.

Post-setup hooks (npm install for browser/Camofox, pip install for
KittenTTS/Piper/ddgs, cua-driver fetch, etc.) are long-running and
text-output, so this follows the spawn-action pattern: it launches
``hermes tools post-setup <key>`` and the frontend tails the log via
``GET /api/actions/tools-post-setup/status``. The ``key`` is validated
against the declared post-setup allowlist before spawning. Returns 400
for unknown toolset or post-setup key.

``profile`` spawns the hook as ``hermes -p <profile> tools post-setup``.
Most hooks install machine-level artifacts (repo node_modules, shared
pip packages) where the scope is inert, but hooks that read config or
write per-profile state must see the same HERMES_HOME the rest of the
drawer's writes targeted — so the scope is threaded for consistency.

**异常**: `HTTPException`

#### def `get_terminal_backends(profile: Optional[str] = None)`

Terminal execution backend rows with health probes for the picker panel.

Returns ``{active, backends: [{name, label, description, active, status,
detail}]}`` where ``status`` is ``ready`` / ``needs_setup`` /
``unavailable`` and ``detail`` carries setup guidance for non-ready rows.
Probes are fast (<~2s each) and defensive — a probe failure surfaces as a
status, never an error response.

#### def `select_terminal_backend(body: TerminalBackendSelect, profile: Optional[str] = None)`

Persist ``terminal.backend`` in config.yaml.

Validates against the known backend set (the same enum the raw-config
settings row exposes). Selecting a backend that still needs setup is
allowed — the picker shows guidance instead of blocking, matching the CLI.

**异常**: `HTTPException`

#### def `get_computer_use_status(profile: Optional[str] = None)`

Cross-platform Computer Use readiness for the desktop card.

See ``tools.computer_use.permissions.computer_use_status`` for the payload
shape. Read-only and fast (shells ``cua-driver doctor`` + macOS
``permissions status``).

#### def `grant_computer_use_permissions(profile: Optional[str] = None)`

Spawn ``hermes computer-use permissions grant`` as a background action.

macOS-only: ``cua-driver permissions grant`` launches CuaDriver via
LaunchServices so the TCC dialog is attributed to com.trycua.driver, then
waits for approval. The frontend polls ``GET /api/actions/computer-use-
grant/status`` and re-reads ``/status`` once it exits. Windows/Linux have
no TCC toggles to grant, so this returns 400 there.

**异常**: `HTTPException`

#### def `get_config_raw(profile: Optional[str] = None)`

Raw config.yaml text plus its resolved path.

``path`` is resolved inside ``_profile_scope`` so the Config page header
shows the file the switched profile actually reads/writes — /api/status's
``config_path`` is machine-global and always reports the dashboard
process's own profile, which is wrong under the global profile switcher.

#### def `update_config_raw(body: RawConfigUpdate, profile: Optional[str] = None)`

**异常**: `HTTPException`

#### def `get_usage_analytics(days: int = 30, profile: Optional[str] = None)`

#### def `get_models_analytics(days: int = 30, profile: Optional[str] = None)`

Return model analytics without blocking the serving event loop.

#### def `console_ws(ws: WebSocket) -> None`

#### def `pty_ws(ws: WebSocket) -> None`

#### def `gateway_ws(ws: WebSocket) -> None`

#### def `pub_ws(ws: WebSocket) -> None`

#### def `events_ws(ws: WebSocket) -> None`

#### def `mount_spa(application: FastAPI)`

Mount the built SPA. Falls back to index.html for client-side routing.

The session token is injected into index.html via a ``<script>`` tag so
the SPA can authenticate against protected API endpoints without a
separate (unauthenticated) token-dispensing endpoint.

When served behind a path-prefix reverse proxy (e.g.
``mission-control.tilos.com/hermes/*`` -> local Caddy -> :9119), the
proxy injects ``X-Forwarded-Prefix: /hermes`` on every request. We
rewrite the served ``index.html`` so absolute asset URLs (``/assets/...``)
and the SPA's runtime ``__HERMES_BASE_PATH__`` honour that prefix
without rebuilding the bundle.

#### def `get_dashboard_themes()`

Return available themes and the currently active one.

Built-in entries ship name/label/description only (the frontend owns
their full definitions in `web/src/themes/presets.ts`).  User themes
from `~/.hermes/dashboard-themes/*.yaml` ship with their full
normalised definition under `definition`, so the client can apply
them without a stub.

#### def `set_dashboard_theme(body: ThemeSetBody)`

Set the active dashboard theme (persists to config.yaml).

#### def `get_dashboard_font()`

Return the active font override (``"theme"`` = use the theme's font).

#### def `set_dashboard_font(body: FontSetBody)`

Set the dashboard font override (persists to config.yaml).

Accepts any id in the curated catalog, or ``"theme"`` to clear the
override and fall back to the active theme's own font. Unknown ids are
coerced to ``"theme"`` rather than 400'd so a stale client can't wedge
the picker.

#### def `get_dashboard_plugins()`

Return discovered dashboard plugins (excludes user-hidden and non-enabled ones).

#### def `rescan_dashboard_plugins()`

Force re-scan of dashboard plugins.

#### def `get_plugins_hub(request: Request)`

Unified agent plugins + dashboard extension metadata (session protected).

**异常**: `HTTPException`

#### def `post_agent_plugin_install(request: Request, body: _AgentPluginInstallBody)`

**异常**: `HTTPException`

#### def `post_agent_plugin_enable(request: Request, name: str)`

**异常**: `HTTPException`

#### def `post_agent_plugin_disable(request: Request, name: str)`

**异常**: `HTTPException`

#### def `post_agent_plugin_update(request: Request, name: str)`

**异常**: `HTTPException`

#### def `delete_agent_plugin(request: Request, name: str)`

**异常**: `HTTPException`

#### def `put_plugin_providers(request: Request, body: _PluginProvidersPutBody)`

Persist memory provider / context engine selection (writes config.yaml).

#### def `post_plugin_visibility(request: Request, name: str, body: _PluginVisibilityBody)`

Toggle a plugin's sidebar visibility (persists to config.yaml dashboard.hidden_plugins).

#### def `serve_plugin_asset(plugin_name: str, file_path: str)`

Serve static assets from a dashboard plugin directory.

Only serves files from the plugin's ``dashboard/`` subdirectory.
Path traversal is blocked by checking ``resolve().is_relative_to()``.

Restricted to a browser-fetchable suffix allowlist (JS/CSS/JSON/HTML/
SVG/PNG/JPG/WOFF). The dashboard loads plugin JS via ``<script src>``
and CSS via ``<link href>``, neither of which can attach a custom
auth header — so this route stays unauthenticated to keep the SPA
working. But user-installed plugins ship a ``plugin_api.py``
backend module that the browser never fetches; it's only imported
by :func:`_mount_plugin_api_routes` at startup. Without a suffix
allowlist, anyone on the loopback port can curl the ``.py`` source
of a private third-party plugin. Reject everything outside the
browser-asset set.

User plugins must be in plugins.enabled before their assets are
served. (#46435, GHSA-mcfc-hp25-cjv7)

**异常**: `HTTPException`

#### def `start_server(host: str = '127.0.0.1', port: int = 9119, open_browser: bool = True, allow_public: bool = False, initial_profile: str = '', headless: bool = False)`

Start the web UI server.

``initial_profile`` (when set) is appended to the auto-opened browser
URL as ``?profile=<name>`` so the SPA's profile switcher preselects it
— used when a profile alias (``<profile> dashboard``) routes to the
machine dashboard.

``headless`` is the ``serve`` path: the JSON-RPC/WS backend with no UI
build and no SPA mount (mount_spa() honours ``HERMES_SERVE_HEADLESS``), so
the banner announces the bind rather than a browser URL.

**异常**: `SystemExit`


## hermes_cli.webhook

### 模块文档

hermes webhook — manage dynamic webhook subscriptions from the CLI.

Usage:
    hermes webhook subscribe <name> [options]
    hermes webhook list
    hermes webhook remove <name>
    hermes webhook test <name> [--payload '{"key": "value"}']

Subscriptions persist to ~/.hermes/webhook_subscriptions.json and are
hot-reloaded by the webhook adapter without a gateway restart.

### 顶层函数

#### def `webhook_command(args)`

Entry point for 'hermes webhook' subcommand.


## hermes_cli.win_pty_bridge

### 模块文档

Windows ConPTY bridge for the `hermes dashboard` chat tab.

Drop-in counterpart to ``hermes_cli.pty_bridge.PtyBridge`` for native
Windows. Mirrors the exact public surface the ``/api/pty`` WebSocket
handler in ``hermes_cli.web_server`` consumes: ``spawn``, ``read``,
``write``, ``resize``, ``close``, ``is_available``, plus the
``PtyUnavailableError`` type.

Backed by ``pywinpty`` (already a declared win32 dependency in
pyproject.toml) instead of ``ptyprocess``/``fcntl``/``termios``, none of
which exist on native Windows. The read/write/terminate calls here match
the working winpty usage already shipping in ``tools/process_registry.py``.

### class PtyUnavailableError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when a PTY cannot be created on this platform.


### class WinPtyBridge

> 继承: `object` ｜ 方法数: 11（公开 8）

pywinpty-backed bridge with the same interface as ``PtyBridge``.

``web_server`` calls :meth:`read` inside ``run_in_executor``, so a
blocking/polling read here never stalls the event loop. ConPTY exposes
no selectable fd, so we poll with a short sleep instead of ``select``.

#### def `__init__(proc: PtyProcess) -> None`

#### classmethod `is_available(cls) -> bool`

#### classmethod `spawn(cls, argv: Sequence[str], cwd: Optional[str] = None, env: Optional[dict] = None, cols: int = 80, rows: int = 24) -> WinPtyBridge`

**异常**: `PtyUnavailableError`

#### property `pid(self) -> int`

#### def `is_alive(self) -> bool`

#### def `read(self, timeout: float = 0.2) -> Optional[bytes]`

Up to 64 KiB of child output.

Returns bytes, ``b""`` when nothing is available this tick, or
``None`` once the child has exited (EOF).

#### def `write(self, data: bytes) -> None`

#### def `resize(self, cols: int, rows: int) -> None`

#### def `close(self) -> None`


## hermes_cli.write_approval_commands

### 模块文档

Shared handlers for the /memory and /skills write-approval subcommands.

Both the interactive CLI (``cli.py``) and the gateway (``gateway/run.py``) call
into this module so the pending-review UX (list / approve / reject / diff /
mode) lives in one place. Each caller owns only its surface concerns:
formatting the returned text and, for the gateway, persisting config + evicting
the cached agent on a mode change.

Every public handler returns a plain text string suitable for both a terminal
and a chat message. Skill diffs are intentionally NOT inlined here — the
``diff`` handler returns the full diff for the CLI pager, but on a messaging
platform the gateway truncates it and points the user at the dashboard / file.

### 顶层函数

#### def `handle_pending_subcommand(subsystem: str, args: List[str], memory_store = None, set_mode_fn = None) -> Optional[str]`

Dispatch a /memory or /skills subcommand.

Args:
    subsystem: ``memory`` or ``skills``.
    args: tokens after the slash command (e.g. ``["approve", "a1b2"]``).
    memory_store: live MemoryStore for applying approved memory writes
        (CLI passes ``self.agent._memory_store``; gateway applies against a
        freshly loaded store).
    set_mode_fn: optional callable ``(enabled: bool) -> None`` that
        persists the new write_approval boolean to config (gateway provides
        this; CLI uses its own ``save_config_value`` and passes a closure).

Returns a text string to show the user. Returns None when the args are not
a write-approval subcommand (caller falls through to its other handling,
e.g. /skills search).


## hermes_cli.xai_retirement

### 模块文档

Detect xAI models retired on May 15, 2026.

Source: https://docs.x.ai/developers/migration/may-15-retirement

Pure logic: walks a Hermes config dict, returns issues for any reference
to a retired xAI model. No I/O, no CLI dependencies — testable in isolation
and reusable from both `hermes doctor` and a future `hermes migrate xai`.

### class RetirementIssue

> 继承: `object` ｜ 方法数: 0（公开 0）

A reference to a retired xAI model found in a Hermes config.


### class ApplyResult

> 继承: `object` ｜ 方法数: 0（公开 0）

Outcome of an apply_migration call.


### 顶层函数

#### def `find_retired_xai_refs(config: Dict[str, Any]) -> List[RetirementIssue]`

Walk all model slots in a Hermes config and return retirement issues.

Slots scanned:
  - ``principal.model``
  - ``auxiliary.<any>.model`` (introspective — covers future aux slots)
  - ``delegation.model``
  - ``tts.xai.model``
  - ``plugins.image_gen.xai.model``

#### def `format_issue(issue: RetirementIssue) -> str`

One-line human-readable rendering of a retirement issue.

#### def `apply_migration(config_path: Path, issues: List[RetirementIssue], backup: bool = True) -> ApplyResult`

Rewrite ``config_path`` in-place so each issue is resolved.

For every issue, the model name is replaced by ``issue.replacement``. If the
issue has ``reasoning_effort`` set (i.e. the migration is from a
``*-non-reasoning`` variant), a sibling ``reasoning_effort`` key is added
or updated alongside the model.

Uses ``ruamel.yaml`` round-trip mode so comments, key order, indentation,
and type literals (booleans, ints) are preserved.

A backup copy is written to
``<config_path>.bak-pre-migrate-xai-YYYYMMDD-HHMMSS`` before rewriting,
unless ``backup=False``.

**异常**: `FileNotFoundError`

