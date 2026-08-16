# plugins — 插件包（187 模块）

> **模块**: `plugins/`（包，共 187 个模块）
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: 内置插件：技能、工作流、看板、学习、多 Agent 等。

## plugins.__init__


## plugins.browser.browser_use.__init__

### 模块文档

Browser Use cloud browser plugin — bundled, auto-loaded.

Mirrors the ``plugins/web/<vendor>/`` layout: ``provider.py`` holds the
provider class; ``__init__.py::register`` instantiates and registers it.

### 顶层函数

#### def `register(ctx) -> None`

Register the Browser Use provider with the plugin context.


## plugins.browser.browser_use.provider

### 模块文档

Browser Use cloud browser provider — plugin form.

Subclasses :class:`agent.browser_provider.BrowserProvider` (the plugin-facing
ABC introduced in PR #25214). The legacy in-tree module
``tools.browser_providers.browser_use`` was removed in the same PR; this file
is now the canonical implementation.

Browser Use is the only browser backend with dual auth: a direct
``BROWSER_USE_API_KEY`` for self-billed users, or the managed Nous tool
gateway (which Hermes uses to bill Browser Use sessions to a Nous
subscription). The dispatch order — direct API key first, managed gateway
second — preserves the pre-migration behaviour in
``tools.browser_providers.browser_use.BrowserUseProvider._get_config_or_none``.

Config keys this provider responds to::

    browser:
      cloud_provider: "browser-use"   # explicit selection
    tool_gateway:
      browser: "gateway"              # optional: prefer managed gateway
                                      #   even when BROWSER_USE_API_KEY is set

Auth env vars (one of)::

    BROWSER_USE_API_KEY=...           # https://browser-use.com
    # OR a managed Nous gateway entry (configured via 'hermes setup')

### class BrowserUseBrowserProvider

> 继承: `BrowserProvider` ｜ 方法数: 10（公开 7）

Browser Use (https://browser-use.com) cloud browser backend.

Dual auth: prefers a direct BROWSER_USE_API_KEY when set, falling back
to the managed Nous tool gateway when ``tool_gateway.browser`` config
routes through it. Setting ``tool_gateway.browser: gateway`` flips the
order so managed billing wins even when BROWSER_USE_API_KEY is present.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `create_session(self, task_id: str) -> Dict[str, object]`

**异常**: `RuntimeError`

#### def `close_session(self, session_id: str) -> bool`

#### def `emergency_cleanup(self, session_id: str) -> None`

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.browser.browserbase.__init__

### 模块文档

Browserbase cloud browser plugin — bundled, auto-loaded.

Mirrors the ``plugins/web/<vendor>/`` and ``plugins/image_gen/openai/``
layout: ``provider.py`` holds the provider class; ``__init__.py::register``
instantiates and registers it via the plugin context.

### 顶层函数

#### def `register(ctx) -> None`

Register the Browserbase provider with the plugin context.


## plugins.browser.browserbase.provider

### 模块文档

Browserbase cloud browser provider — plugin form.

Subclasses :class:`agent.browser_provider.BrowserProvider` (the plugin-facing
ABC introduced in PR #25214). The legacy in-tree module
``tools.browser_providers.browserbase`` was removed in the same PR; this file
is now the canonical implementation.

Browserbase requires direct ``BROWSERBASE_API_KEY`` and ``BROWSERBASE_PROJECT_ID``
credentials. Managed Nous gateway support has been removed — the Nous
subscription now routes through Browser Use instead (see
``plugins/browser/browser_use/``).

Config keys this provider responds to::

    browser:
      cloud_provider: "browserbase"

Auth env vars::

    BROWSERBASE_API_KEY=...       # https://browserbase.com
    BROWSERBASE_PROJECT_ID=...

Optional feature knobs::

    BROWSERBASE_BASE_URL=...      # default https://api.browserbase.com
    BROWSERBASE_PROXIES=true      # default true
    BROWSERBASE_ADVANCED_STEALTH=false
    BROWSERBASE_KEEP_ALIVE=true   # default true
    BROWSERBASE_SESSION_TIMEOUT=... (seconds, integer, max 21600 = 6h)

### class BrowserbaseBrowserProvider

> 继承: `BrowserProvider` ｜ 方法数: 9（公开 7）

Browserbase (https://browserbase.com) cloud browser backend.

Direct credentials only — managed-Nous-gateway support lives on the
Browser Use provider now.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `create_session(self, task_id: str) -> Dict[str, object]`

**异常**: `RuntimeError`

#### def `close_session(self, session_id: str) -> bool`

#### def `emergency_cleanup(self, session_id: str) -> None`

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.browser.firecrawl.__init__

### 模块文档

Firecrawl cloud browser plugin — bundled, auto-loaded.

Distinct from ``plugins/web/firecrawl/`` (the web search/extract/crawl
plugin); both share the FIRECRAWL_API_KEY but speak to different endpoints
(``/v2/browser`` here vs ``/v2/search`` / ``/v2/scrape`` / ``/v2/crawl``
over there).

### 顶层函数

#### def `register(ctx) -> None`

Register the Firecrawl cloud-browser provider with the plugin context.


## plugins.browser.firecrawl.provider

### 模块文档

Firecrawl cloud browser provider — plugin form.

Subclasses :class:`agent.browser_provider.BrowserProvider` (the plugin-facing
ABC introduced in PR #25214). The legacy in-tree module
``tools.browser_providers.firecrawl`` was removed in the same PR; this file
is now the canonical implementation.

This is the cloud-browser path — distinct from the firecrawl WEB plugin at
``plugins/web/firecrawl/`` which handles search/extract/crawl on
``/v2/search`` / ``/v2/scrape`` / ``/v2/crawl``. The two plugins share the
``FIRECRAWL_API_KEY`` env var but talk to different endpoints (this one
hits ``/v2/browser``).

Config keys this provider responds to::

    browser:
      cloud_provider: "firecrawl"   # explicit selection only — not in the
                                    # legacy auto-detect walk

Auth env vars::

    FIRECRAWL_API_KEY=...           # https://firecrawl.dev
    FIRECRAWL_API_URL=...           # optional override (default https://api.firecrawl.dev)
    FIRECRAWL_BROWSER_TTL=...       # optional, default 300 seconds

### class FirecrawlBrowserProvider

> 继承: `BrowserProvider` ｜ 方法数: 9（公开 7）

Firecrawl (https://firecrawl.dev) cloud browser backend.

Cloud-browser path only — search/extract/crawl live in the separate
``plugins/web/firecrawl/`` plugin.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `create_session(self, task_id: str) -> Dict[str, object]`

**异常**: `RuntimeError`

#### def `close_session(self, session_id: str) -> bool`

#### def `emergency_cleanup(self, session_id: str) -> None`

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.context_engine.__init__

### 模块文档

Context engine plugin discovery.

Scans ``plugins/context_engine/<name>/`` directories for context engine
plugins.  Each subdirectory must contain ``__init__.py`` with a class
implementing the ContextEngine ABC.

Context engines are separate from the general plugin system — they live
in the repo and are always available without user installation.  Only ONE
can be active at a time, selected via ``context.engine`` in config.yaml.
The default engine is ``"compressor"`` (the built-in ContextCompressor).

Usage:
    from plugins.context_engine import discover_context_engines, load_context_engine

    available = discover_context_engines()   # [(name, desc, available), ...]
    engine = load_context_engine("lcm")      # ContextEngine instance

### 顶层函数

#### def `discover_context_engines() -> List[Tuple[str, str, bool]]`

Scan plugins/context_engine/ for available engines.

Returns list of (name, description, is_available) tuples.
Does NOT import the engines — just reads plugin.yaml for metadata
and does a lightweight availability check.

#### def `load_context_engine(name: str) -> Optional['ContextEngine']`

Load and return a ContextEngine instance by name.

Returns None if the engine is not found or fails to load.


## plugins.cron_providers.__init__

### 模块文档

Cron scheduler provider plugin discovery.

Scans two directories for cron scheduler provider plugins:

1. Bundled providers: ``plugins/cron_providers/<name>/`` (shipped with hermes-agent)
2. User-installed providers: ``$HERMES_HOME/plugins/<name>/``

Each subdirectory must contain ``__init__.py`` with a class implementing the
``CronScheduler`` ABC (``cron/scheduler_provider.py``). On name collisions,
bundled providers take precedence.

This is a near-verbatim clone of ``plugins/memory/__init__.py`` — the same
discovery/loader machinery, retargeted at ``CronScheduler``. The built-in
``InProcessCronScheduler`` is NOT discovered here: it is core (lives in
``cron/scheduler_provider.py``) so the fallback can never be accidentally
removed. Only NON-default providers (e.g. "chronos") live under this directory.

Only ONE provider can be active at a time, selected via ``cron.provider`` in
config.yaml (empty = built-in). See ``cron.scheduler_provider.resolve_cron_scheduler``.

Usage:
    from plugins.cron_providers import discover_cron_schedulers, load_cron_scheduler

    available = discover_cron_schedulers()   # [(name, desc, available), ...]
    provider = load_cron_scheduler("chronos")  # CronScheduler instance

### 顶层函数

#### def `find_provider_dir(name: str) -> Optional[Path]`

Resolve a provider name to its directory.

Checks bundled first, then user-installed.

#### def `discover_cron_schedulers() -> List[Tuple[str, str, bool]]`

Scan bundled and user-installed directories for available providers.

Returns list of (name, description, is_available) tuples. May be empty —
the built-in is core, not discovered here, so a fresh checkout with no
bundled non-default provider returns []. Bundled providers take precedence
on name collisions.

#### def `load_cron_scheduler(name: str) -> Optional['CronScheduler']`

Load and return a CronScheduler instance by name.

Checks both bundled (``plugins/cron_providers/<name>/``) and user-installed
(``$HERMES_HOME/plugins/<name>/``) directories. Bundled takes precedence
on name collisions.

Returns None if the provider is not found or fails to load.


## plugins.cron_providers.chronos.__init__

### 模块文档

Chronos — NAS-mediated managed cron provider (scale-to-zero).

Chronos (the Greek god of time, alongside Hermes) is the first non-default
``CronScheduler``. It lets a hosted gateway scale to zero while idle and still
fire cron jobs: instead of a 60s in-process ticker, it asks NAS to arm exactly
one external one-shot per job at that job's real next-fire time. NAS calls the
agent back at fire time over an authenticated webhook (``/api/cron/fire``); the
agent runs the job via the shared ``run_one_job`` body and re-arms the next
one-shot.

The external scheduler NAS uses is an internal NAS implementation detail —
Chronos names no vendor, holds no scheduler credentials, and speaks only to
NAS's ``agent-cron`` endpoints with the agent's existing Nous token.

Design constraints (see the plan's DQ-1):
  - start() arms all enabled jobs and RETURNS; it never blocks and never spawns
    a periodic wake. Between fires the machine is truly at zero.
  - reconcile runs only on a warm process (start / on_jobs_changed / piggybacked
    on a fire), never as a periodic wake of a sleeping machine.

Inert unless ``cron.provider: chronos``. ``resolve_cron_scheduler`` falls back
to the built-in if Chronos is unavailable, so cron never loses its trigger.

Wire contract: ``docs/chronos-managed-cron-contract.md``.

### class ChronosCronScheduler

> 继承: `CronScheduler` ｜ 方法数: 14（公开 7）

NAS-mediated external cron provider.

#### def `__init__() -> None`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

Config presence only — NO network.

Chronos needs a portal base URL, the agent's own publicly-reachable
callback URL (for NAS→agent fires), and a usable Nous token (the agent
is logged into the portal). If any is missing, resolve_cron_scheduler
falls back to the built-in ticker.

#### def `start(self, stop_event, adapters = None, loop = None, interval = 60)`

Arm all enabled jobs via NAS, then RETURN immediately.

Does NOT block and does NOT spawn a 60s wake (DQ-1) — that is the whole
point of scale-to-zero. The machine wakes only on a NAS→agent fire.

#### def `stop(self) -> None`

#### def `on_jobs_changed(self) -> None`

A job was created/updated/removed/paused/resumed — reconcile the NAS
registry so the affected one-shot is (re-)armed or cancelled.

#### def `reconcile(self) -> None`

Converge the NAS-armed one-shots toward jobs.json (desired state):
arm missing / re-arm changed-time, cancel orphaned.

#### def `fire_due(self, job_id: str, adapters: Any = None, loop: Any = None) -> bool`

Run the due job (claim + run_one_job via the ABC default), then
re-arm the NEXT one-shot through NAS.

Re-arm happens AFTER the run so next_run_at reflects the completed fire.
If the job is gone (one-shot completed / repeat-N exhausted), get_job
returns None → nothing to re-arm (the schedule naturally stops).


### 顶层函数

#### def `register(ctx) -> None`

Plugin entrypoint — register the Chronos provider with the loader.

Mirrors the memory-plugin shape; plugins/cron_providers discovery calls this and
collects the provider via register_cron_scheduler.


## plugins.cron_providers.chronos._nas_client

### 模块文档

Thin HTTP client for the agent → NAS ``agent-cron`` endpoints (Chronos).

The Chronos provider speaks ONLY to NAS — it names no scheduler vendor and
holds no scheduler credentials. NAS owns the external scheduler (an internal
implementation detail) and that scheduler's account; the agent just asks NAS to
"arm a one-shot at time T" / "cancel" / "list", authenticated with the agent's
existing Nous Portal access token (the same token it already uses to call the
portal — no new secret).

Wire contract: ``docs/chronos-managed-cron-contract.md``.

### class NasCronClientError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when a NAS agent-cron call fails (non-2xx or transport error).


### class NasCronClient

> 继承: `object` ｜ 方法数: 8（公开 3）

Minimal client for the agent→NAS provision/cancel/list endpoints.

Uses the agent's refresh-aware Nous access token for auth. No scheduler
vendor, no scheduler creds — NAS hides all of that behind these three calls.

#### def `__init__(portal_url: str, timeout_seconds: float = 15.0) -> None`

#### def `provision(self, job_id: str, fire_at: str, agent_callback_url: str, dedup_key: str) -> Dict[str, Any]`

Ask NAS to arm a one-shot for ``job_id`` at ``fire_at`` (ISO 8601).

``dedup_key`` (``{job_id}:{fire_at}``) makes re-arming the same fire
idempotent NAS-side. Returns the NAS response (e.g. ``{schedule_id}``).

#### def `cancel(self, job_id: str) -> Dict[str, Any]`

Ask NAS to cancel any armed one-shot for ``job_id``.

#### def `list_armed(self) -> List[Dict[str, Any]]`

List the one-shots NAS currently has armed for this agent.

Returns a list of ``{job_id, fire_at, schedule_id}``. Best-effort: used
by reconcile to find orphaned arms on a cold process; on error the
caller falls back to idempotent re-arm of all desired jobs.


## plugins.cron_providers.chronos.verify

### 模块文档

Inbound cron-fire token verification for Chronos (Phase 4E.1).

When NAS relays an external scheduler fire to the agent, it POSTs
``/api/cron/fire`` with a short-lived NAS-minted JWT. This module verifies that
JWT before any job runs — the security boundary for remotely-triggered job
execution.

We verify a NAS-minted JWT (the trust path the agent already has) rather than
let an external scheduler call the agent directly: the scheduler signs with
NAS's keys, which the agent doesn't (and shouldn't) hold. See the plan's DQ-4.

The verifier is pluggable (``get_fire_verifier``) so the escape-hatch mode
(direct per-job cron-key) can swap in later with no handler change.

Crypto is delegated to PyJWT (already a declared dependency) — we do NOT
hand-roll JWT verification.

### 顶层函数

#### def `verify_nas_fire_token(token: str, expected_audience: str, jwks_or_key: Optional[str] = None, issuer: Optional[str] = None, leeway_seconds: int = 30) -> Optional[Dict[str, Any]]`

Verify a NAS-minted cron-fire JWT. Return decoded claims, or None.

Checks (all must pass):
  - signature against the NAS JWKS (``jwks_or_key`` is a JWKS URL) — RS256
    family; symmetric secrets are rejected (NAS signs asymmetrically).
  - ``aud`` == ``expected_audience`` (this agent: ``agent:{instance_id}``).
  - ``exp`` / ``nbf`` within ``leeway_seconds``.
  - ``iss`` == ``issuer`` when an issuer is configured.
  - ``purpose`` == ``"cron_fire"`` — so a general agent JWT can't be
    replayed against the fire endpoint.

Returns None (never raises) on any failure, so the handler can answer 401
without leaking which check failed.

#### def `get_fire_verifier() -> Callable[..., Optional[Dict[str, Any]]]`

Return the active inbound-fire verifier.

Default = the NAS-JWT verifier. The DQ-4 escape hatch (direct per-job
cron-key) would return a cron-key verifier here instead, selected by config
— so the webhook handler never changes when the auth mode is swapped.


## plugins.dashboard_auth.basic.__init__

### 模块文档

BasicAuthProvider — username/password dashboard auth (no OAuth IDP).

A self-hosted "just put a password on my dashboard" provider. It plugs
into the same ``DashboardAuthProvider`` framework as the Nous OAuth
provider, but authenticates with a username + password instead of an
OAuth redirect: it sets ``supports_password = True`` and implements
``complete_password_login``. The login page renders a credential form for
it; everything downstream of login (session cookies, verify, refresh,
ws-tickets, logout) is identical to the OAuth path because a password
session is just a :class:`Session` with provider-minted opaque tokens.

This provider has **no external IDP and no database**. Credentials are
configured up front; sessions are stateless HMAC-signed tokens this
provider mints and verifies itself. That keeps it zero-infrastructure —
appropriate for a single-box self-hosted dashboard.

Configuration surfaces (env wins over config.yaml when set non-empty),
mirroring the Nous provider's precedence convention:

  ``config.yaml`` — canonical surface::

      dashboard:
        basic_auth:
          username: admin               # required
          # Provide EITHER a precomputed scrypt hash (preferred — no
          # plaintext at rest) ...
          password_hash: "scrypt$..."   # see hash_password()
          # ... OR a plaintext password (hashed in-memory at load).
          password: "s3cret"
          secret: "<32+ random bytes, base64 or hex>"  # optional; token-signing key
          session_ttl_seconds: 43200    # optional; access-token lifetime (default 12h)

  Environment overrides::

      HERMES_DASHBOARD_BASIC_AUTH_USERNAME
      HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH   # preferred
      HERMES_DASHBOARD_BASIC_AUTH_PASSWORD        # plaintext fallback
      HERMES_DASHBOARD_BASIC_AUTH_SECRET
      HERMES_DASHBOARD_BASIC_AUTH_TTL_SECONDS

If ``secret`` is not configured, a random per-process secret is generated
at startup. That's fine for a single-process dashboard, but means all
sessions are invalidated on restart and sessions don't survive across
multiple worker processes — set an explicit ``secret`` for stable
multi-worker / restart-surviving sessions.

Password hashing uses stdlib :func:`hashlib.scrypt` (memory-hard, no
third-party dependency). ``complete_password_login`` runs a constant-time
comparison and always performs a hash even for an unknown username, so
the endpoint is not a username-enumeration timing oracle.

Skip reasons:
  Like the Nous provider, this exposes a module-level ``LAST_SKIP_REASON``
  the gate's fail-closed branch can surface when the plugin loads but
  declines to register (no username/password configured).

### class BasicAuthProvider

> 继承: `DashboardAuthProvider` ｜ 方法数: 9（公开 6）

Username/password provider with stateless HMAC-signed sessions.

#### def `__init__(username: str, password_hash: str, secret: bytes, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None`

**异常**: `ValueError`

#### def `start_login(self, redirect_uri: str) -> LoginStart`

**异常**: `NotImplementedError`

#### def `complete_login(self, code: str, state: str, code_verifier: str, redirect_uri: str) -> Session`

**异常**: `NotImplementedError`

#### def `complete_password_login(self, username: str, password: str) -> Session`

**异常**: `InvalidCredentialsError`

#### def `verify_session(self, access_token: str) -> Optional[Session]`

#### def `refresh_session(self, refresh_token: str) -> Session`

**异常**: `RefreshExpiredError`

#### def `revoke_session(self, refresh_token: str) -> None`


### 顶层函数

#### def `hash_password(password: str) -> str`

Return a ``scrypt$n$r$p$<salt_b64>$<dk_b64>`` hash string.

Use this to precompute ``password_hash`` for config.yaml so plaintext
never sits at rest. Exposed as a module function so operators can run
``python -c "from plugins.dashboard_auth.basic import hash_password;
print(hash_password('pw'))"``.

#### def `register(ctx) -> None`

Plugin entry — registers BasicAuthProvider when credentials exist.

Loopback / ``--insecure`` operators and anyone using the OAuth
provider leave ``dashboard.basic_auth`` unset, so this plugin is a
no-op for them. When username + (password or password_hash) are
configured, it registers a password provider that the login page
renders as a credential form.


## plugins.dashboard_auth.drain.__init__

### 模块文档

DrainSecretProvider — shared-bearer-secret auth for the drain-control endpoint.

Task 2.0b of the safe-shutdown plan, and the FIRST consumer of the generic
non-interactive token-auth capability added in Task 2.0a
(``supports_token`` / ``verify_token`` on the ``DashboardAuthProvider`` ABC +
the route-agnostic ``token_auth`` middleware seam).

What it is
----------
A service-to-service auth provider. ``nous-account-service`` (NAS) provisions a
**per-agent unique** shared secret into each deployed agent's environment; this
provider verifies an inbound ``Authorization`` bearer token against that secret
with a constant-time compare and, on a match, vouches for the caller as the
``drain-control`` principal. It is NOT an interactive identity provider — there
is no login, cookie, session, or refresh. It implements ONLY the token
capability (``supports_token = True`` + ``verify_token``); the five interactive
ABC methods raise ``NotImplementedError``.

Why a plugin (not an ad-hoc header check on the drain route)
------------------------------------------------------------
Decisions.md Q-A: the drain credential MUST be a real auth plugin in the
dashboard auth framework, not a bolt-on. Q-C: the framework widening that
hosts it is generic (Task 2.0a) and this plugin is merely its first consumer.

Security properties (decisions.md Q-A)
--------------------------------------
* **Per-agent unique secret** — each agent gets a distinct secret; a leak's
  blast radius is one agent.
* **Entropy gate at registration** — a weak/short/low-entropy secret fails
  CLOSED at load (the plugin declines to register and records a skip reason);
  it is never silently accepted. Bar: >= 256 bits of entropy / >= 43
  url-safe-base64 chars, and the value must not be obviously structured
  (all-one-character, too few distinct characters).
* **Constant-time compare** — ``hmac.compare_digest`` on the request path, so
  the endpoint is not a timing oracle.

Configuration
-------------
The secret is a CREDENTIAL, so it is carried via an env var (the ``.env``-is-
for-secrets-only rule), provisioned by NAS at deploy time (Phase 3):

    HERMES_DASHBOARD_DRAIN_SECRET   # the per-agent shared secret (>=43 url-safe-b64 chars)

Behavioural knobs live in config.yaml (canonical surface):

    dashboard:
      drain_auth:
        scope: drain            # capability label attached to the principal
        min_secret_chars: 43    # entropy bar (optional; default 43 ~= 256 bits)

When ``HERMES_DASHBOARD_DRAIN_SECRET`` is unset, the plugin is a no-op (records
a skip reason) — agents that don't want NAS-driven drain just don't set it.

### class DrainSecretProvider

> 继承: `DashboardAuthProvider` ｜ 方法数: 7（公开 6）

Non-interactive shared-bearer-secret provider for drain control.

#### def `__init__(secret: str, scope: str = 'drain') -> None`

**异常**: `ValueError`

#### def `verify_token(self, token: str) -> Optional[TokenPrincipal]`

Constant-time compare against the per-agent shared secret.

Returns a ``drain-control`` principal on an exact match, else ``None``
(the generic seam falls through / fails closed). Uses
``hmac.compare_digest`` so a wrong token can't be recovered by timing.

#### def `start_login(self, redirect_uri: str) -> LoginStart`

**异常**: `NotImplementedError`

#### def `complete_login(self, code: str, state: str, code_verifier: str, redirect_uri: str) -> Session`

**异常**: `NotImplementedError`

#### def `verify_session(self, access_token: str) -> Optional[Session]`

#### def `refresh_session(self, refresh_token: str) -> Session`

**异常**: `NotImplementedError`

#### def `revoke_session(self, refresh_token: str) -> None`


### 顶层函数

#### def `assess_secret_strength(secret: str, min_chars: int = _DEFAULT_MIN_SECRET_CHARS) -> Optional[str]`

Return a rejection reason if ``secret`` is too weak, else ``None``.

Fail-closed entropy gate (decisions.md Q-A). Checks, in order:
  * length >= ``min_chars`` (default 43 url-safe-b64 chars ~= 256 bits),
  * at least ``_MIN_DISTINCT_CHARS`` distinct characters,
  * Shannon entropy >= ``_MIN_SHANNON_BITS`` bits.

A ``None`` return means the secret passes. Any string return is a
human-readable reason the caller logs + records as the skip reason.

#### def `register(ctx) -> None`

Plugin entry — registers DrainSecretProvider when a strong secret is set.

No-op (records a skip reason) when ``HERMES_DASHBOARD_DRAIN_SECRET`` is
unset or fails the entropy gate. On success, also registers the
begin/cancel-drain route as token-authable via the generic seam.


## plugins.dashboard_auth.nous.__init__

### 模块文档

NousDashboardAuthProvider — Nous Portal OAuth (authorization-code + PKCE).

Implements ``nous-account-service/docs/agent-dashboard-oauth-contract.md``
(PR #180). The plugin auto-loads (bundled, kind=backend) but only registers
its provider when a client_id is configured — either via ``config.yaml`` or
via the Portal-injected env var — so loopback / ``--insecure`` operators
are unaffected.

Configuration surfaces (env wins over config.yaml when set non-empty):

  ``config.yaml`` — canonical surface::

      dashboard:
        oauth:
          client_id: agent:{agent_instance_id}   # required
          portal_url: https://portal.example     # optional

  Environment overrides — used by Fly.io's platform-secret injection so
  per-deploy values don't need to bake into ``config.yaml``:

      HERMES_DASHBOARD_OAUTH_CLIENT_ID  — shape ``agent:{agent_instance_id}``
      HERMES_DASHBOARD_PORTAL_URL       — defaults to
                                          ``https://portal.nousresearch.com``
                                          (production Portal). Override only
                                          for staging (``portal.rewbs.uk``)
                                          or a custom deployment.

Empty env var values are treated as unset so a provisioned-but-not-populated
Fly secret can't shadow a valid config.yaml entry.

Key contract points encoded here:

  - client_id is per-instance (``agent:{instance_id}``); the suffix is also
    cross-checked against the token's ``agent_instance_id`` claim as
    defense-in-depth.
  - scope is ``agent_dashboard:access`` only (no OIDC scopes).
  - tokens are RS256 JWTs verified against ``/.well-known/jwks.json``;
    JWKS is cached for 5 minutes.
  - the dashboard auth-code grant issues a 24h rotating refresh token
    (Portal NAS PR #293). ``refresh_session`` posts ``grant_type=refresh_token``
    to rotate the access token; ``complete_login`` and ``refresh_session``
    both populate ``Session.refresh_token`` with the (rotating) value the
    middleware persists back to the HttpOnly cookie. On a dead/expired/
    reuse-detected refresh token Portal returns 400 → ``RefreshExpiredError``
    → middleware redirects to ``/auth/login``.
  - audience claim is the bare ``client_id`` (no ``hermes-cli:`` prefix).
  - tolerant ``oauth_contract_version`` check: missing → warn + proceed;
    present and ``!= 1`` → refuse.

The cookie payload returned by ``start_login`` stashes the PKCE
``code_verifier`` and the OAuth ``state`` parameter for the
``/auth/callback`` handler to retrieve. The auth-route layer is the owner
of cookie names; this provider just hands back ``{"code_verifier": …,
"state": …}`` and the route serializes those into the ``hermes_session_pkce``
cookie.

Refresh-token rotation: Portal rotates the refresh token on every
successful refresh and runs reuse-detection (replaying a rotated token
outside Portal's 60s grace revokes the whole session). The host
middleware therefore MUST persist the rotated ``Session.refresh_token``
back to the cookie on every refresh.

Skip reasons:
  The plugin exposes a module-level ``LAST_SKIP_REASON`` that the gate's
  fail-closed branch reads to surface a useful operator error message
  ("Set HERMES_DASHBOARD_OAUTH_CLIENT_ID …") instead of the bare "no
  providers registered" the gate would otherwise emit.

### class NousDashboardAuthProvider

> 继承: `DashboardAuthProvider` ｜ 方法数: 14（公开 5）

Nous Portal OAuth via authorization-code + PKCE (S256).

#### def `__init__(client_id: str, portal_url: str) -> None`

**异常**: `ValueError`

#### def `start_login(self, redirect_uri: str) -> LoginStart`

#### def `complete_login(self, code: str, state: str, code_verifier: str, redirect_uri: str) -> Session`

**异常**: `ProviderError`

#### def `refresh_session(self, refresh_token: str) -> Session`

Rotate the access token using the refresh token.

Posts ``grant_type=refresh_token`` to Portal's token endpoint. The
refresh token is sent in the ``X-Refresh-Token`` header (not the body)
so it never lands in Portal's request-body access logs — mirroring the
device-flow CLI convention; Portal reconciles header vs. body and
rejects conflicts.

Portal rotates the refresh token on every successful refresh, so the
returned ``Session.refresh_token`` is a NEW value the caller MUST
persist (replacing the old cookie). Failing to persist it means the
next refresh replays a rotated token and — outside Portal's 60s grace
— trips reuse-detection and revokes the whole session.

Raises ``RefreshExpiredError`` on a 400 (expired / revoked / reuse-
detected), so the middleware clears cookies and forces re-login.
Raises ``ProviderError`` if Portal is unreachable.

**异常**: `RefreshExpiredError`, `ProviderError`

#### def `verify_session(self, access_token: str) -> Optional[Session]`

#### def `revoke_session(self, refresh_token: str) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry — called by the plugin loader at startup.

Registers ``NousDashboardAuthProvider`` only when a client_id is
configured (either via ``HERMES_DASHBOARD_OAUTH_CLIENT_ID`` env var
or via ``dashboard.oauth.client_id`` in ``config.yaml``). The env
var wins when set non-empty — Fly.io's platform-secret injection
pushes the per-deploy value through this path.

When skipping, writes a short human-readable reason to the module-
level :data:`LAST_SKIP_REASON` so the dashboard's fail-closed branch
can surface "Set HERMES_DASHBOARD_OAUTH_CLIENT_ID …" instead of the
bare "no providers registered" the gate would otherwise emit. The
reason mentions BOTH configuration surfaces so operators don't
guess wrong about which one to populate.

Operator-owned dashboards (loopback / ``--insecure``) leave both
surfaces unset, so this plugin is a no-op for them. The gate-
engagement layer (``hermes_cli.web_server.should_require_auth`` +
the fail-closed check in ``start_server``) handles the "public bind
with zero providers" case independently.


## plugins.dashboard_auth.self_hosted.__init__

### 模块文档

SelfHostedOIDCProvider — generic self-hosted OpenID Connect dashboard auth.

A standards-compliant OpenID Connect Relying Party for the ``hermes dashboard``
OAuth gate. Unlike the bundled ``nous`` provider (which encodes Nous Portal's
bespoke contract — ``agent:{instance_id}`` client ids, a custom access-token
JWT, the ``x-nous-refresh-token`` header, an ``oauth_contract_version`` claim),
this provider speaks **plain OIDC** so it works against any conformant
self-hosted identity provider:

    Authentik · Keycloak · Zitadel · Authelia · Auth0 · Okta · Google · …

It is a pure drop-in plugin: it implements the five
:class:`~hermes_cli.dashboard_auth.DashboardAuthProvider` methods and touches
nothing in core auth/runtime/login. The HTTP round trip, cookies, CSRF
``state`` check and ``redirect_uri`` reconstruction are all owned by
``hermes_cli/dashboard_auth/routes.py``; this provider only:

  1. discovers the IDP's endpoints from ``{issuer}/.well-known/openid-configuration``,
  2. builds the ``/authorize`` URL with PKCE (S256),
  3. exchanges the authorization code for tokens at the discovered
     ``token_endpoint``,
  4. verifies the **ID token** (RS256/ES256) against the discovered
     ``jwks_uri`` with ``iss`` / ``aud`` pinned to the configured issuer /
     client id, and maps standard OIDC claims (``sub``, ``email``, ``name``)
     onto a :class:`~hermes_cli.dashboard_auth.Session`.

Why the ID token (not the access token)? OIDC guarantees the ID token is a
signed JWT carrying identity claims — that is its entire purpose. The access
token's format is opaque to the client per the spec; many IDPs issue random
opaque strings the client cannot verify locally. Verifying the ID token is the
only choice that is universally correct across self-hosted IDPs. (The ``nous``
provider verifies its *access* token because Nous Portal mints a custom JWT
access token with the dashboard claims baked in — a non-OIDC shortcut.)

Both **public** (PKCE-only) and **confidential** (PKCE + ``client_secret``)
clients are supported. A self-hoster who registers a public client configures
no secret and the token-endpoint calls authenticate with PKCE alone (the
default). A self-hoster whose IDP defaults the client to *confidential*
(Authentik and Keycloak commonly do) sets ``client_secret`` and the provider
additionally authenticates the client at the token endpoint, choosing
``client_secret_basic`` (HTTP Basic header) or ``client_secret_post`` (secret
in the form body) from the IDP's advertised
``token_endpoint_auth_methods_supported``. PKCE is sent in **both** modes —
the secret is client authentication layered on top, never a replacement for
PKCE (OAuth 2.1 / RFC 9700 keep PKCE mandatory regardless).

Configuration surfaces (env wins over config.yaml when set non-empty, so a
provisioned-but-not-populated secret can't shadow a valid config.yaml entry —
same precedence convention as the ``nous`` plugin)::

    # config.yaml — canonical surface
    dashboard:
      oauth:
        provider: self-hosted
        self_hosted:
          issuer: https://auth.example.com/application/o/hermes/   # required
          client_id: hermes-dashboard                              # required
          scopes: "openid profile email"                           # optional
          # client_secret: set ONLY for a confidential client. It is a
          # credential — prefer the env var / ~/.hermes/.env over config.yaml.

    # Environment overrides (Docker/Fly secret injection)
    HERMES_DASHBOARD_OIDC_ISSUER
    HERMES_DASHBOARD_OIDC_CLIENT_ID
    HERMES_DASHBOARD_OIDC_SCOPES        # optional; defaults to "openid profile email"
    HERMES_DASHBOARD_OIDC_CLIENT_SECRET # optional; set for a confidential client
                                        # (the .env file is the canonical home —
                                        # it's a secret, not a behavioural setting)

Skip reasons: when the plugin loads but can't register (missing issuer /
client_id), it writes a human-readable reason to the module-level
:data:`LAST_SKIP_REASON` so the gate's fail-closed branch can surface a useful
operator error instead of the bare "no providers registered".

### class SelfHostedOIDCProvider

> 继承: `DashboardAuthProvider` ｜ 方法数: 16（公开 5）

Generic self-hosted OpenID Connect provider (authorization-code + PKCE).

#### def `__init__(issuer: str, client_id: str, scopes: str = _DEFAULT_SCOPES, client_secret: str = '') -> None`

**异常**: `ValueError`

#### def `start_login(self, redirect_uri: str) -> LoginStart`

#### def `complete_login(self, code: str, state: str, code_verifier: str, redirect_uri: str) -> Session`

#### def `refresh_session(self, refresh_token: str) -> Session`

**异常**: `RefreshExpiredError`

#### def `verify_session(self, access_token: str) -> Optional[Session]`

#### def `revoke_session(self, refresh_token: str) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry — called by the plugin loader at startup.

Registers :class:`SelfHostedOIDCProvider` only when both an issuer and a
client_id are configured (via ``HERMES_DASHBOARD_OIDC_*`` env vars or the
``dashboard.oauth.self_hosted`` block in config.yaml). Operator-owned
loopback / ``--insecure`` dashboards leave these unset, so the plugin is a
no-op for them.

On skip, writes a reason to :data:`LAST_SKIP_REASON` that names BOTH
configuration surfaces so operators don't guess wrong about which to set.


## plugins.disk-cleanup.__init__

### 模块文档

disk-cleanup plugin — auto-cleanup of ephemeral Hermes session files.

Wires three behaviours:

1. ``post_tool_call`` hook — inspects ``write_file`` and ``terminal``
   tool results for newly-created paths matching test/temp patterns
   under ``HERMES_HOME`` and tracks them silently.  Zero agent
   compliance required.

2. ``on_session_end`` hook — when any test files were auto-tracked
   during the just-finished turn, runs :func:`disk_cleanup.quick` and
   logs a single line to ``$HERMES_HOME/disk-cleanup/cleanup.log``.

3. ``/disk-cleanup`` slash command — manual ``status``, ``dry-run``,
   ``quick``, ``deep``, ``track``, ``forget``.

Replaces PR #12212's skill-plus-script design: the agent no longer
needs to remember to run commands.

### 顶层函数

#### def `register(ctx) -> None`


## plugins.disk-cleanup.disk_cleanup

### 模块文档

disk_cleanup — ephemeral file cleanup for Hermes Agent.

Library module wrapping the deterministic cleanup rules written by
@LVT382009 in PR #12212. The plugin ``__init__.py`` wires these
functions into ``post_tool_call`` and ``on_session_end`` hooks so
tracking and cleanup happen automatically — the agent never needs to
call a tool or remember a skill.

Rules:
  - test files    → delete immediately at task end (age >= 0)
  - temp files    → delete after 7 days
  - cron-output   → delete after 14 days
  - empty dirs    → always delete (under HERMES_HOME)
  - research      → keep 10 newest, prompt for older (deep only)
  - chrome-profile→ prompt after 14 days (deep only)
  - >500 MB files → prompt always (deep only)

Scope: strictly HERMES_HOME and /tmp/hermes-*
Never touches: ~/.hermes/logs/ or any system directory.

### 顶层函数

#### def `get_state_dir() -> Path`

State dir — separate from ``$HERMES_HOME/logs/``.

#### def `get_tracked_file() -> Path`

#### def `get_log_file() -> Path`

Audit log — intentionally NOT under ``$HERMES_HOME/logs/``.

#### def `is_safe_path(path: Path) -> bool`

Accept only paths under HERMES_HOME or ``/tmp/hermes-*``.

Rejects Windows mounts (``/mnt/c`` etc.) and any system directory.

#### def `load_tracked() -> List[Dict[str, Any]]`

Load tracked.json.  Restores from ``.bak`` on corruption.

#### def `save_tracked(tracked: List[Dict[str, Any]]) -> None`

Atomic write: ``.tmp`` → backup old → rename.

#### def `fmt_size(n: float) -> str`

#### def `track(path_str: str, category: str, silent: bool = False) -> bool`

Register a file for tracking. Returns True if newly tracked.

#### def `forget(path_str: str) -> int`

Remove a path from tracking without deleting the file.

#### def `dry_run() -> Tuple[List[Dict], List[Dict]]`

Return (auto_delete_list, needs_prompt_list) without touching files.

#### def `quick() -> Dict[str, Any]`

Safe deterministic cleanup — no prompts.

Returns: ``{"deleted": N, "empty_dirs": N, "freed": bytes,
           "errors": [str, ...]}``.

#### def `deep(confirm: Optional[callable] = None) -> Dict[str, Any]`

Deep cleanup.

Runs :func:`quick` first, then asks the *confirm* callable for each
risky item (research > 30d beyond 10 newest, chrome-profile > 14d,
any file > 500 MB).  *confirm(item)* must return True to delete.

Returns: ``{"quick": {...}, "deep_deleted": N, "deep_freed": bytes}``.

#### def `status() -> Dict[str, Any]`

Return per-category breakdown and top 10 largest tracked files.

#### def `format_status(s: Dict[str, Any]) -> str`

Human-readable status string (for slash command output).

#### def `guess_category(path: Path) -> Optional[str]`

Return a category label for *path*, or None if we shouldn't track it.

Used by the ``post_tool_call`` hook to auto-track ephemeral files.


## plugins.google_meet.__init__

### 模块文档

google_meet plugin — let the agent join a Meet call, transcribe it, follow up.

v1: transcribe-only. Spawns a headless Chromium via Playwright, joins the Meet
URL, enables live captions, scrapes them into a transcript file. The agent then
has the transcript in its workspace and can do whatever followup work it needs
using its regular tools.

v2 (not in this PR): realtime duplex audio so the agent can speak in the
meeting, via OpenAI Realtime / Gemini Live + BlackHole / PulseAudio null-sink.
``meet_say`` exists as a stub today so the tool surface is stable.

Explicit-by-design: only joins ``https://meet.google.com/`` URLs explicitly
passed in. No calendar scanning, no auto-dial, no consent announcement.

### 顶层函数

#### def `register(ctx) -> None`

Register tools, CLI, and lifecycle hooks.

Called once by the plugin loader when the plugin is enabled via
``plugins.enabled`` in config.yaml.


## plugins.google_meet.audio_bridge

### 模块文档

Virtual audio bridge for feeding generated speech into Chrome's mic.

v2 module. Provisions a platform-specific virtual audio device so the
Meet bot's Chromium instance can be pointed at an input source we
control. The OpenAI Realtime client writes PCM bytes into this device;
Chrome reads them as if they were coming from a microphone.

Linux (primary): uses pactl (PulseAudio) to create a null-sink plus a
virtual source whose master is the null-sink's monitor. Callers set
PULSE_SOURCE=<source_name> in Chrome's env and pass the fake-mic flag.

macOS: requires BlackHole 2ch to be installed. This module only
verifies its presence and returns the device name; routing OS default
input is left to the user (or a future switchaudio-osx integration) to
avoid surprising the user's system audio state.

Windows: not supported in v2.

### class AudioBridge

> 继承: `object` ｜ 方法数: 8（公开 4）

Manages a virtual audio device for Chrome fake-mic input.

Call ``setup()`` once before launching the Meet bot and
``teardown()`` when the session ends. ``teardown()`` is idempotent.

#### def `__init__(name_prefix: str = 'hermes_meet') -> None`

#### property `device_name(self) -> str`

**异常**: `RuntimeError`

#### property `write_target(self) -> str`

**异常**: `RuntimeError`

#### def `setup(self) -> dict`

Provision the virtual audio device.

Returns a dict describing the device. Raises RuntimeError on
unsupported platforms or when required system tools are missing.

**异常**: `RuntimeError`

#### def `teardown(self) -> None`

Release the virtual audio device. Idempotent.


### 顶层函数

#### def `chrome_fake_audio_flags(bridge_info: dict) -> list[str]`

Return Chrome flags for using the fake audio input.

The PulseAudio source is selected via the ``PULSE_SOURCE`` env var,
which callers must set in Chrome's environment before launch:

    env["PULSE_SOURCE"] = bridge_info["device_name"]

On macOS the caller must ensure the system default audio input is
set to the returned BlackHole device (we do not flip that switch).

**异常**: `RuntimeError`


## plugins.google_meet.cli

### 模块文档

CLI commands for the google_meet plugin.

Wires ``hermes meet <subcommand>``:
  setup       — preflight playwright, chromium, auth file, print fixes
  auth        — open a browser to sign into Google, save storage state
  join <url>  — join a Meet URL synchronously (also callable from the agent)
  status      — print current bot state
  transcript  — print the transcript
  stop        — leave the current meeting

### 顶层函数

#### def `register_cli(subparser: argparse.ArgumentParser) -> None`

Build the ``hermes meet`` argparse tree.

Called by :func:`_register_cli_commands` at plugin load time.

#### def `meet_command(args: argparse.Namespace) -> int`


## plugins.google_meet.meet_bot

### 模块文档

Headless Google Meet bot — Playwright + live-caption scraping.

Runs as a standalone subprocess spawned by ``process_manager.py``. Reads config
from env vars, writes status + transcript to files under
``$HERMES_HOME/workspace/meetings/<meeting-id>/``. The main hermes process
reads those files via the ``meet_*`` tools — no IPC beyond filesystem.

The scraping strategy mirrors OpenUtter (sumansid/openutter): we don't parse
WebRTC audio, we enable Google Meet's built-in live captions and observe the
captions container in the DOM via a MutationObserver. This is lossy and
English-biased but it is:

* deterministic (no API keys, no STT billing),
* works behind Meet's normal login / admission,
* survives Meet UI rewrites fairly well because the caption container has a
  stable ARIA role.

Run standalone for debugging::

    HERMES_MEET_URL=https://meet.google.com/abc-defg-hij \
    HERMES_MEET_OUT_DIR=/tmp/meet-debug \
    HERMES_MEET_HEADED=1 \
    python -m plugins.google_meet.meet_bot

No meet.google.com URL → exits non-zero. Any URL that doesn't start with
``https://meet.google.com/`` is rejected (explicit-by-design).

### 顶层函数

#### def `run_bot() -> int`


## plugins.google_meet.node.__init__

### 模块文档

Remote 'node host' primitive for the google_meet plugin.

Lets the Meet bot (Playwright + Chrome) run on a different machine than
the hermes-agent gateway. The gateway speaks a small JSON-over-WebSocket
RPC protocol to the remote node; the node wraps the existing
``plugins.google_meet.process_manager`` API.

Topology
--------
    gateway (Linux)  ── ws://mac.local:18789 ──▶  node server (Mac)
                                                  └─ process_manager
                                                     └─ meet_bot (Playwright)

Why: Google sign-in + Chrome profile live on the user's laptop. Running
the bot there reuses that profile without shipping credentials to the
server.

Public surface
--------------
    NodeClient     — gateway-side RPC client (short-lived sync WS per call)
    NodeServer     — long-running server that hosts the bot
    NodeRegistry   — local JSON registry of approved nodes (name → url+token)
    protocol       — message envelope helpers (make_request, encode, decode, ...)

## plugins.google_meet.node.cli

### 模块文档

`hermes meet node ...` subcommand tree.

Wired into the existing ``hermes meet`` parser by the plugin's top-level
CLI. This module only defines the subparsers and their dispatch — it
does not mutate the existing cli.py.

### 顶层函数

#### def `register_cli(subparser: argparse.ArgumentParser) -> None`

Add ``run / list / approve / remove / status / ping`` subparsers.

*subparser* is the ``hermes meet node`` argparse object — typically
the result of ``meet_parser.add_parser('node', ...)``.

#### def `node_command(args: argparse.Namespace) -> int`

Dispatch for ``hermes meet node ...``.

Returns a process exit code. Side-effects print to stdout/stderr.


## plugins.google_meet.node.client

### 模块文档

Gateway-side RPC client for a remote meet node.

Each call opens a short-lived synchronous WebSocket to the node, sends
exactly one request, reads exactly one response, and closes. This keeps
the client trivial to use from non-async tool handlers and avoids
maintaining persistent connection state across agent turns.

The ``websockets`` package is an optional dep — we import it lazily so
plugin load doesn't require it.

### class NodeClient

> 继承: `object` ｜ 方法数: 8（公开 6）

Thin synchronous WS client matching the server's request surface.

#### def `__init__(url: str, token: str, timeout: float = 10.0) -> None`

**异常**: `ValueError`

#### def `start_bot(self, url: str, guest_name: str = 'Hermes Agent', duration: Optional[str] = None, headed: bool = False, mode: str = 'transcribe') -> Dict[str, Any]`

#### def `stop(self) -> Dict[str, Any]`

#### def `status(self) -> Dict[str, Any]`

#### def `transcript(self, last: Optional[int] = None) -> Dict[str, Any]`

#### def `say(self, text: str) -> Dict[str, Any]`

#### def `ping(self) -> Dict[str, Any]`


## plugins.google_meet.node.protocol

### 模块文档

Wire protocol for gateway ↔ node RPC.

Everything is a JSON object with the same envelope shape:

    Request:   {"type": <str>, "id": <str>, "token": <str>, "payload": <dict>}
    Response:  {"type": "<req-type>_res", "id": <req-id>, "payload": <dict>}
    Error:     {"type": "error", "id": <req-id>, "error": <str>}

Requests must carry the shared bearer token (set up via
``hermes meet node approve`` on the gateway and read off disk on the
server). Mismatched tokens are rejected before dispatch.

### 顶层函数

#### def `make_request(type: str, token: str, payload: Dict[str, Any], req_id: str | None = None) -> Dict[str, Any]`

Construct a request envelope.

``req_id`` is auto-generated (uuid4 hex) when not supplied so callers
can correlate async responses.

**异常**: `ValueError`

#### def `make_response(req_id: str, payload: Dict[str, Any]) -> Dict[str, Any]`

Build a success response. The caller supplies the *request* type;
we suffix it with ``_res`` so clients can assert they got the right
reply.

For simplicity we don't require the type here — clients usually just
key off ``id``. But we still emit a generic ``*_res`` envelope.

**异常**: `ValueError`

#### def `make_error(req_id: str, error: str) -> Dict[str, Any]`

#### def `encode(msg: Dict[str, Any]) -> str`

Serialize a message envelope to a JSON string.

#### def `decode(raw: str) -> Dict[str, Any]`

Parse a JSON envelope, raising ValueError on anything malformed.

Minimal type validation: must be an object, must contain ``type`` and
``id``. Heavier validation (token match, payload shape) happens in
:func:`validate_request` on the server side.

**异常**: `ValueError`

#### def `validate_request(msg: Dict[str, Any], expected_token: str) -> Tuple[bool, str]`

Check a decoded request against the server's shared token.

Returns ``(True, "")`` when the envelope is acceptable or
``(False, <reason>)`` otherwise. Reason strings are safe to surface
back to the client in an error envelope.


## plugins.google_meet.node.registry

### 模块文档

Local JSON registry of approved remote meet nodes.

Lives at ``$HERMES_HOME/workspace/meetings/nodes.json``. The gateway
consults it to resolve a ``chrome_node`` name to a ``(url, token)`` pair
before opening a WebSocket to the remote bot host.

Schema
------
    {
      "nodes": {
        "<name>": {
          "url":   "ws://host:port",
          "token": "...",
          "added_at": <epoch_float>
        }
      }
    }

### class NodeRegistry

> 继承: `object` ｜ 方法数: 8（公开 5）

Simple file-backed registry. Not concurrent-safe across processes
— single writer assumed (the gateway CLI).

#### def `__init__(path: Optional[Path] = None) -> None`

#### def `get(self, name: str) -> Optional[Dict[str, Any]]`

#### def `add(self, name: str, url: str, token: str) -> None`

**异常**: `ValueError`

#### def `remove(self, name: str) -> bool`

#### def `list_all(self) -> List[Dict[str, Any]]`

#### def `resolve(self, chrome_node: Optional[str]) -> Optional[Dict[str, Any]]`

Resolve a node name to its entry.

If ``chrome_node`` is provided, return that named node (or None).
If ``chrome_node`` is None, return the sole registered node when
exactly one is registered; otherwise return None (ambiguous or
empty).


## plugins.google_meet.node.server

### 模块文档

Remote node server.

Runs on the machine that will host the Meet bot (typically the user's
Mac laptop with a signed-in Chrome). Exposes a WebSocket endpoint that
accepts signed RPC requests and dispatches them to the existing
``plugins.google_meet.process_manager`` module.

Launched by ``hermes meet node run``.

Token handling
--------------
On first boot we mint 32 hex chars of entropy and persist them at
``$HERMES_HOME/workspace/meetings/node_token.json``. Subsequent boots
reuse the same token so previously-approved gateways don't need to be
re-paired. The operator copies this token out-of-band to the gateway
via ``hermes meet node approve <name> <url> <token>``.

Dependencies
------------
``websockets`` is an optional dep. We import it lazily inside
:meth:`serve` so installing the plugin doesn't require it unless you
actually host a node.

### class NodeServer

> 继承: `object` ｜ 方法数: 5（公开 3）

WebSocket server that executes meet bot RPCs locally.

#### def `__init__(host: str = '127.0.0.1', port: int = 18789, token_path: Optional[Path] = None, display_name: str = 'hermes-meet-node') -> None`

#### def `ensure_token(self) -> str`

Return the persisted shared secret, generating one on first use.

#### def `get_token(self) -> str`

Alias for :meth:`ensure_token`; does not mutate on subsequent calls.

#### async def `serve(self) -> None`

Run the WebSocket server until cancelled.

Blocks forever. Callers typically wrap this in ``asyncio.run``.

**异常**: `RuntimeError`


## plugins.google_meet.process_manager

### 模块文档

Subprocess lifecycle manager for the google_meet bot.

Single active meeting at a time. Stores the running pid + out_dir in a
session-scoped state file under ``$HERMES_HOME/workspace/meetings/.active.json``
so tool calls across turns can find the bot, and ``on_session_end`` can clean
it up.

The bot runs as a detached subprocess — we don't hold file descriptors open,
so the parent agent loop can't block on it. We communicate via files only.

### 顶层函数

#### def `start(url: str, out_dir: Optional[Path] = None, headed: bool = False, auth_state: Optional[str] = None, guest_name: str = 'Hermes Agent', duration: Optional[str] = None, session_id: Optional[str] = None, mode: str = 'transcribe', realtime_model: Optional[str] = None, realtime_voice: Optional[str] = None, realtime_instructions: Optional[str] = None, realtime_api_key: Optional[str] = None) -> Dict[str, Any]`

Spawn the meet_bot subprocess for *url*.

If a bot is already running for this hermes install, leave it first —
we enforce single-active-meeting semantics.

Returns a dict summarizing the started bot.

#### def `status() -> Dict[str, Any]`

Return the current meeting state, or ``{"ok": False, "reason": ...}``.

#### def `transcript(last: Optional[int] = None) -> Dict[str, Any]`

Read the current transcript file. Returns ok=False if none exists.

#### def `enqueue_say(text: str) -> Dict[str, Any]`

Append a ``say`` request to the active bot's JSONL queue.

Returns ``{"ok": False, "reason": ...}`` when no meeting is active or
the active bot is in transcribe-only mode. Otherwise writes a line to
``<out_dir>/say_queue.jsonl`` that the bot's realtime speaker thread
will consume.

#### def `stop(reason: str = 'requested') -> Dict[str, Any]`

Signal the active bot to leave cleanly, then clear the active pointer.

Sends SIGTERM and waits up to 10s for the bot to exit. Falls back to
SIGKILL if the bot doesn't respond.


## plugins.google_meet.realtime.__init__

### 模块文档

Realtime speech subpackage for the google_meet plugin (v2).

Provides a thin OpenAI Realtime API client and a file-queue speaker
wrapper so the Meet bot can play synthesized speech through the
virtual audio bridge.

## plugins.google_meet.realtime.openai_client

### 模块文档

OpenAI Realtime API WebSocket client + file-queue speaker.

This module is the "output" side of the v2 voice bridge: it takes text,
sends it to the OpenAI Realtime API, receives audio deltas back, and
appends the PCM bytes to a file. A separate consumer (the audio
bridge) streams that file into Chrome's fake microphone.

Designed for simplicity: a single synchronous WebSocket connection per
speaker, per session. The ``websockets`` package is imported lazily so
that importing this module never fails just because the optional dep
is missing.

### class RealtimeSession

> 继承: `object` ｜ 方法数: 7（公开 4）

Minimal sync client for the OpenAI Realtime WebSocket API.

Usage:
    sess = RealtimeSession(api_key=..., audio_sink_path=Path("out.pcm"))
    sess.connect()
    sess.speak("Hello team.")
    sess.close()

Thread safety: ``speak`` and ``cancel_response`` may be called from
different threads; a lock serializes WebSocket writes.

#### def `__init__(api_key: str, model: str = 'gpt-realtime', voice: str = 'alloy', instructions: str = '', audio_sink_path: Optional[Path] = None, sample_rate: int = 24000) -> None`

#### def `connect(self) -> None`

Open WS and send session.update with voice+instructions.

#### def `close(self) -> None`

#### def `speak(self, text: str, timeout: float = 30.0) -> dict`

Send ``text`` and accumulate the audio response.

Audio deltas are base64-decoded and appended to
``audio_sink_path`` (opened 'ab' and closed per call, so a
separate streaming reader can consume whatever is there).

**异常**: `RuntimeError`, `TimeoutError`

#### def `cancel_response(self) -> bool`

Interrupt the in-flight response (barge-in).

Sends ``response.cancel`` on the current WebSocket so the model
stops generating audio immediately. Safe to call at any time;
returns True if a cancel was actually sent, False when there's
nothing to cancel or the socket isn't open.


### class RealtimeSpeaker

> 继承: `object` ｜ 方法数: 5（公开 1）

File-based JSONL queue wrapper around :class:`RealtimeSession`.

Each line in ``queue_path`` is a JSON object of the form
``{"id": "<uuid>", "text": "..."}``. Processed lines are appended
to ``processed_path`` (if set) and then removed from the queue;
if ``processed_path`` is ``None``, processed lines are simply
dropped.

#### def `__init__(session: RealtimeSession, queue_path: Path, processed_path: Optional[Path] = None) -> None`

#### def `run_until_stopped(self, stop_fn: Callable[[], bool], poll_interval: float = 0.5) -> None`


## plugins.google_meet.tools

### 模块文档

Agent-facing tools for the google_meet plugin.

Tools:
  meet_join        — join a Google Meet URL (spawns Playwright bot locally
                     OR on a remote node host via node=<name>)
  meet_status      — report bot liveness + transcript progress
  meet_transcript  — read the current transcript (optional last-N)
  meet_leave       — signal the bot to leave cleanly
  meet_say         — (v2) speak text through the realtime audio bridge.
                     Requires the active meeting to have been joined with
                     mode='realtime'.

### 顶层函数

#### def `check_meet_requirements() -> bool`

Return True when the plugin can actually run LOCALLY.

Gates on:
  * Python ``playwright`` package importable
  * the plugin being on a supported platform (Linux or macOS)

Note: remote-node operation (``node=<name>``) only needs the
``websockets`` dep on the gateway side — Chromium lives on the node.
But the plugin-level gate keeps the v1 semantics; individual tool
handlers relax the requirement when a node is addressed.

#### def `handle_meet_join(args: Dict[str, Any], **_kw) -> str`

#### def `handle_meet_status(args: Dict[str, Any], **_kw) -> str`

#### def `handle_meet_transcript(args: Dict[str, Any], **_kw) -> str`

#### def `handle_meet_leave(args: Dict[str, Any], **_kw) -> str`

#### def `handle_meet_say(args: Dict[str, Any], **_kw) -> str`


## plugins.hermes-achievements.dashboard.plugin_api

### 模块文档

Hermes Achievements dashboard plugin backend.

Mounted at /api/plugins/hermes-achievements/ by Hermes dashboard.

### 顶层函数

#### def `tiers(values: List[int]) -> List[Dict[str, Any]]`

#### def `req(metric: str, gte: int) -> Dict[str, Any]`

#### def `state_path() -> Path`

#### def `snapshot_path() -> Path`

#### def `checkpoint_path() -> Path`

#### def `load_state() -> Dict[str, Any]`

#### def `save_state(state: Dict[str, Any]) -> None`

#### def `load_snapshot() -> Optional[Dict[str, Any]]`

#### def `save_snapshot(data: Dict[str, Any]) -> None`

#### def `load_checkpoint() -> Dict[str, Any]`

#### def `save_checkpoint(data: Dict[str, Any]) -> None`

#### def `session_fingerprint(meta: Dict[str, Any]) -> Dict[str, Any]`

#### def `model_provider(model_name: str) -> Optional[str]`

#### def `is_local_model_name(model_name: str) -> bool`

#### def `analyze_messages(session_id: str, title: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]`

#### def `evaluate_tiered(definition: Dict[str, Any], aggregate: Dict[str, Any]) -> Dict[str, Any]`

#### def `evaluate_requirements(definition: Dict[str, Any], aggregate: Dict[str, Any]) -> Dict[str, Any]`

#### def `evaluate_boolean(definition: Dict[str, Any], aggregate: Dict[str, Any]) -> Dict[str, Any]`

#### def `metric_label(metric: str) -> str`

#### def `criteria_for(definition: Dict[str, Any]) -> str`

#### def `display_achievement(item: Dict[str, Any]) -> Dict[str, Any]`

#### def `scan_sessions(limit: Optional[int] = None, progress_callback: Optional[Any] = None, progress_every: int = 250) -> Dict[str, Any]`

Scan Hermes sessions and build per-session achievement stats.

``limit=None`` (the default) scans the ENTIRE session history. Prior
versions capped this at 200, which silently reduced achievement totals
to ~2% of history on long-running installs and made lifetime badges
unreachable. SQLite's ``LIMIT -1`` means "unlimited"; we map ``None``
and non-positive values to ``-1`` so callers get the full catalog.

Warm scans stay cheap: the checkpoint cache stores per-session stats
keyed by ``(started_at, last_active)`` and only re-analyzes sessions
whose fingerprint changed. Cold scans on large histories (thousands
of sessions) take tens of seconds to several minutes; ``evaluate_all``
runs them on a background thread so the dashboard UI never blocks on
the first request.

``progress_callback(partial_sessions, scanned_so_far, total)`` — when
provided, fires every ``progress_every`` sessions with the sessions
analyzed so far and progress counters. Background scans use this to
publish intermediate snapshots so a long cold scan surfaces badges
incrementally on each dashboard refresh instead of going all-at-once
at the end.

#### def `aggregate_stats(sessions: List[Dict[str, Any]]) -> Dict[str, Any]`

#### def `evaluate_definition(definition: Dict[str, Any], aggregate: Dict[str, Any]) -> Dict[str, Any]`

#### def `evidence_for(definition: Dict[str, Any], sessions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]`

#### def `compute_all(progress_callback: Optional[Any] = None, progress_every: int = 250) -> Dict[str, Any]`

#### def `evaluate_all(force: bool = False) -> Dict[str, Any]`

Return the current achievements payload.

Behavior matrix:

* Fresh in-memory cache → return it instantly.
* Stale on-disk snapshot → load it, kick a background rescan, return
  the stale data (UI decorates it with ``is_stale=True``).
* No snapshot yet (first-ever run) → kick a background scan, return
  an empty-but-valid "pending" payload so the UI can render a spinner
  without blocking.
* ``force=True`` (manual /rescan) → run synchronously, block the
  caller, replace the cache.

Warm scans stay cheap (the checkpoint cache reuses per-session stats).
Cold scans on 8000+ session databases take minutes; the background
thread prevents that from ever blocking the dashboard request path.

#### def `achievements()`

#### def `scan_status()`

#### def `recent_unlocks()`

#### def `session_badges(session_id: str)`

#### def `rescan()`

#### def `reset_state()`


## plugins.hermes-achievements.tests.test_achievement_engine

### class AchievementEngineTests

> 继承: `unittest.TestCase` ｜ 方法数: 11（公开 11）

#### def `test_tool_call_stats_detect_tool_names_and_errors(self)`

#### def `test_tiered_achievement_reaches_highest_matching_tier(self)`

#### def `test_tiered_achievement_can_be_discovered_without_unlocking(self)`

#### def `test_secret_achievement_stays_hidden_without_progress(self)`

#### def `test_multi_condition_unlock_requires_all_requirements(self)`

#### def `test_catalog_has_60_plus_unique_achievements(self)`

#### def `test_model_provider_metrics_are_aggregated(self)`

#### def `test_removed_noisy_achievements_are_not_in_catalog(self)`

#### def `test_open_weights_pilgrim_counts_only_local_model_metadata(self)`

#### def `test_config_surgeon_ignores_generic_config_mentions(self)`

#### def `test_dashboard_card_hover_does_not_move_click_target(self)`


## plugins.image_gen.deepinfra.__init__

### 模块文档

DeepInfra image generation backend.

Exposes DeepInfra's image-gen catalog (FLUX, Qwen-Image-Edit, …) through
the OpenAI-compatible ``/v1/openai/images/generations`` endpoint as an
:class:`ImageGenProvider` implementation.

**Fully dynamic model discovery.** Unlike the other image-gen plugins in
this tree (which ship a hardcoded ``_MODELS`` dict), DeepInfra publishes
a single tagged catalog at
``https://api.deepinfra.com/v1/openai/models?filter=true&sort_by=hermes``
where each entry's ``metadata.tags`` declares its surface (``image-gen``
here). ``list_models()`` filters that catalog via
:func:`hermes_cli.models._fetch_deepinfra_models_by_tag` so newly added
models show up in ``hermes tools`` automatically. No model ids are
hardcoded in this file — if a model is retired upstream, it disappears
from hermes the next time the catalog is fetched, no patch required.

Model selection (first hit wins):

1. ``DEEPINFRA_IMAGE_MODEL`` env var
2. ``image_gen.deepinfra.model`` in ``config.yaml``
3. First model from the live catalog

When all three are absent (catalog unreachable, nothing configured),
``generate()`` returns an :func:`error_response` rather than guessing.

### class DeepInfraImageGenProvider

> 继承: `ImageGenProvider` ｜ 方法数: 8（公开 8）

DeepInfra ``images.generations`` backend.

Catalog is discovered live from the DeepInfra ``/models`` endpoint
filtered by the ``image-gen`` surface tag.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `capabilities(self) -> Dict[str, Any]`

DeepInfra's OpenAI-compatible generation surface is text-only.

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry point — wire ``DeepInfraImageGenProvider`` into the registry.


## plugins.image_gen.fal.__init__

### 模块文档

FAL.ai image generation backend.

Wraps the 18-model FAL catalog (FLUX 2, Z-Image, Nano Banana, GPT
Image 1.5, Recraft, Imagen 4, Qwen, Ideogram, …) as an
:class:`ImageGenProvider` implementation.

The heavy lifting — model catalog, payload construction, request
submission, managed-Nous-gateway selection, Clarity Upscaler chaining
— lives in :mod:`tools.image_generation_tool`. This plugin reaches into
that module via call-time indirection (``import tools.image_generation_tool as _it``)
so:

* the existing test suite (``tests/tools/test_image_generation.py``,
  ``tests/tools/test_managed_media_gateways.py``) keeps patching
  ``image_tool._submit_fal_request`` / ``image_tool.fal_client`` /
  ``image_tool._managed_fal_client`` without modification, and
* there's exactly one canonical FAL code path on disk — the plugin is a
  registration adapter, not a parallel implementation.

See issue #26241 for the migration plan and the
``plugin-extraction-test-patch-compatibility.md`` rules this follows.

### class FalImageGenProvider

> 继承: `ImageGenProvider` ｜ 方法数: 8（公开 8）

FAL.ai image generation backend.

Delegates to ``tools.image_generation_tool.image_generate_tool`` so
the in-tree FAL implementation (model catalog, payload builder,
managed-gateway selection, Clarity Upscaler chaining) is the single
source of truth. Everything is resolved at call time via the
``_it`` indirection so tests can monkey-patch the legacy module.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]`

Generate or edit an image via the legacy FAL pipeline.

Forwards prompt + aspect_ratio + image_url/reference_image_urls (and
any forward-compat extras the schema supports) into
:func:`tools.image_generation_tool.image_generate_tool`, then reshapes
its JSON-string response into the provider-ABC dict format consumed by
``_dispatch_to_plugin_provider``.


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry point — wire ``FalImageGenProvider`` into the registry.


## plugins.image_gen.krea.__init__

### 模块文档

Krea image generation backend.

Exposes Krea's `Krea 2` foundation image model family — Krea 2 Medium and
Krea 2 Large — as an :class:`ImageGenProvider` implementation.

Krea's API is asynchronous: the generate endpoint returns a ``job_id``
that you poll at ``GET /jobs/{job_id}``. This provider hides that
roundtrip behind the synchronous ``generate()`` contract: submit, poll
every 2s with light backoff, materialise the result URL to local cache,
return the success/error dict like every other backend.

Selection precedence (first hit wins):

1. ``KREA_IMAGE_MODEL`` env var (escape hatch for scripts / tests)
2. ``image_gen.krea.model`` in ``config.yaml``
3. ``image_gen.model`` in ``config.yaml`` (when it's one of our IDs)
4. :data:`DEFAULT_MODEL` — ``krea-2-medium`` (Krea's "start here" recommendation)

Docs: https://docs.krea.ai/developers/krea-2/overview
API:  https://docs.krea.ai/api-reference/krea/krea-2-large

### class KreaImageGenProvider

> 继承: `ImageGenProvider` ｜ 方法数: 8（公开 8）

Krea ``Krea 2`` foundation image model backend (Medium + Large).

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry point — wire ``KreaImageGenProvider`` into the registry.


## plugins.image_gen.openai-codex.__init__

### 模块文档

OpenAI image generation backend — ChatGPT/Codex OAuth variant.

Identical model catalog and tier semantics to the ``openai`` image-gen plugin
(``gpt-image-2`` at low/medium/high quality), but routes the request through
the Codex Responses API ``image_generation`` tool instead of the
``images.generate`` REST endpoint. This lets users who are already
authenticated with Codex/ChatGPT generate images without configuring a
separate ``OPENAI_API_KEY``.

Selection precedence for the tier (first hit wins):

1. ``OPENAI_IMAGE_MODEL`` env var (escape hatch for scripts / tests)
2. ``image_gen.openai-codex.model`` in ``config.yaml``
3. ``image_gen.model`` in ``config.yaml`` (when it's one of our tier IDs)
4. :data:`DEFAULT_MODEL` — ``gpt-image-2-medium``

Output is saved as PNG under ``$HERMES_HOME/cache/images/``. Source images for
image-to-image/editing are sent as Responses ``input_image`` content parts.

### class CodexImageGenerationUnsupportedError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

The active Codex account cannot use the hosted image tool.


### class OpenAICodexImageGenProvider

> 继承: `ImageGenProvider` ｜ 方法数: 8（公开 8）

gpt-image-2 routed through ChatGPT/Codex OAuth instead of an API key.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry point — register the Codex-backed image-gen provider.


## plugins.image_gen.openai.__init__

### 模块文档

OpenAI image generation backend.

Exposes OpenAI's ``gpt-image-2`` model at three quality tiers as an
:class:`ImageGenProvider` implementation. The tiers are implemented as
three virtual model IDs so the ``hermes tools`` model picker and the
``image_gen.model`` config key behave like any other multi-model backend:

    gpt-image-2-low     ~15s   fastest, good for iteration
    gpt-image-2-medium  ~40s   default — balanced
    gpt-image-2-high    ~2min  slowest, highest fidelity

All three hit the same underlying API model (``gpt-image-2``) with a
different ``quality`` parameter. Output is base64 JSON → saved under
``$HERMES_HOME/cache/images/``.

Selection precedence (first hit wins):

1. ``OPENAI_IMAGE_MODEL`` env var (escape hatch for scripts / tests)
2. ``image_gen.openai.model`` in ``config.yaml``
3. ``image_gen.model`` in ``config.yaml`` (when it's one of our tier IDs)
4. :data:`DEFAULT_MODEL` — ``gpt-image-2-medium``

### class OpenAIImageGenProvider

> 继承: `ImageGenProvider` ｜ 方法数: 8（公开 8）

OpenAI ``images.generate`` / ``images.edit`` backend — gpt-image-2.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry point — wire ``OpenAIImageGenProvider`` into the registry.


## plugins.image_gen.openrouter.__init__

### 模块文档

OpenRouter-compatible image generation backend (OpenRouter + Nous Portal).

Both OpenRouter and the Nous Portal inference endpoint speak the same
OpenAI-style ``/chat/completions`` image-generation protocol: send
``modalities: ["image", "text"]`` with an image-output model (e.g.
``google/gemini-3-pro-image``), pass reference images as ``image_url``
content parts for grounding, and read the generated images back from
``choices[0].message.images[].image_url.url`` (a ``data:image/...;base64`` URI).

Nous Portal proxies OpenRouter, so one implementation services both — we only
swap the resolved ``(base_url, api_key)``. Credentials are resolved through the
agent's existing :func:`~hermes_cli.runtime_provider.resolve_runtime_provider`,
which already understands OpenRouter's key pool and the Nous OAuth device-code
token, so this plugin never reinvents auth.

Reference grounding is the reason pet sprite generation cares about this
backend: each animation row must stay the same character as the chosen base
frame, which only works on models that accept image input. Gemini Flash Image
("nano-banana") does, so both providers advertise image-to-image support.

### class OpenRouterCompatImageProvider

> 继承: `ImageGenProvider` ｜ 方法数: 12（公开 8）

Image generation over an OpenRouter-compatible chat-completions endpoint.

Instantiated once per backend (OpenRouter, Nous Portal). The two differ only
in which runtime provider supplies ``(base_url, api_key)`` and in the config
namespace used for the model override.

#### def `__init__(provider_name: str, display_name: str, runtime_name: str, config_key: str, model_env_var: str, setup_schema: Dict[str, Any]) -> None`

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `register(ctx: Any) -> None`

Register the OpenRouter + Nous Portal image gen providers.


## plugins.image_gen.xai.__init__

### 模块文档

xAI image generation backend.

Exposes xAI's ``grok-imagine-image`` model as an
:class:`ImageGenProvider` implementation.

Features:
- Text-to-image generation
- Multiple aspect ratios (1:1, 16:9, 9:16, etc.)
- Multiple resolutions (1K, 2K)
- Base64 output saved to cache

Selection precedence (first hit wins):
1. ``XAI_IMAGE_MODEL`` env var
2. ``image_gen.xai.model`` in ``config.yaml``
3. :data:`DEFAULT_MODEL`

### class XAIImageGenProvider

> 继承: `ImageGenProvider` ｜ 方法数: 7（公开 7）

xAI ``grok-imagine-image`` backend.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, **kwargs: Any) -> Dict[str, Any]`

Generate an image (text-to-image) or edit a source image (image-to-image).

Routing: when ``image_url`` is provided, POST to ``/v1/images/edits``
with the source image; otherwise POST to ``/v1/images/generations``.
Per xAI docs, editing uses the ``grok-imagine-image-quality`` model and
a JSON body (the OpenAI SDK's multipart ``images.edit()`` is NOT
supported by xAI).


### 顶层函数

#### def `register(ctx: Any) -> None`

Register this provider with the image gen registry.


## plugins.kanban.dashboard.plugin_api

### 模块文档

Kanban dashboard plugin — backend API routes.

Mounted at /api/plugins/kanban/ by the dashboard plugin system.

This layer is intentionally thin: every handler is a small wrapper around
``hermes_cli.kanban_db`` or a direct SQL query. Writes use the same code
paths the CLI and gateway ``/kanban`` command use, so the three surfaces
cannot drift.

Live updates arrive via the ``/events`` WebSocket, which tails the
append-only ``task_events`` table on a short poll interval (WAL mode lets
reads run alongside the dispatcher's IMMEDIATE write transactions).

Security note
-------------
Plugin HTTP routes go through the dashboard's session-token auth middleware
(``web_server.auth_middleware``) just like core API routes — every
``/api/plugins/...`` request must present the session bearer token (or the
session cookie set when you load the dashboard HTML). The token is the
random per-process ``_SESSION_TOKEN`` printed at startup; the dashboard's
own pages inject it via ``window.__HERMES_SESSION_TOKEN__`` so logged-in
browsers don't have to handle it manually.

For the ``/events`` WebSocket we still require the session token as a
``?token=`` query parameter (browsers cannot set the ``Authorization``
header on an upgrade request), matching the established pattern used by
the in-browser PTY bridge in ``hermes_cli/web_server.py``.

This means ``hermes dashboard --host 0.0.0.0`` is safe to run on a LAN:
plugin routes are no longer an unauthenticated exception. The auth still
isn't multi-user — anyone who can read the printed URL+token gets full
dashboard access — but they can't ride along just because they can reach
the port.

### class CreateTaskBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class UpdateTaskBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class CommentBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class LinkBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class BulkTaskBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class TerminateRunBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class ReclaimBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class SpecifyBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）

Optional author override. Nothing else is configurable from the
dashboard — model + prompt come from ``auxiliary.triage_specifier``
in config.yaml, same as the CLI.


### class ReassignBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class CreateBoardBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class RenameBoardBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class DescribeBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class DescribeAutoBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class DecomposeBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### class OrchestrationSettingsBody

> 继承: `BaseModel` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `get_board(tenant: Optional[str] = Query(None, description='Filter to a single tenant'), include_archived: bool = Query(False), board: Optional[str] = Query(None, description='Kanban board slug (omit for current)'), workflow_template_id: Optional[str] = Query(None, description='Restrict to tasks using this workflow template id'), current_step_key: Optional[str] = Query(None, description='Restrict to tasks at this workflow step key'))`

Return the full board grouped by status column.

``_conn()`` auto-initializes ``kanban.db`` on first call so a fresh
install doesn't surface a "failed to load" error on the plugin tab.

``board`` selects which board to read from. Omitting it falls
through to the active board (``HERMES_KANBAN_BOARD`` env → on-disk
``current`` pointer → ``default``).

#### def `get_task(task_id: str, board: Optional[str] = Query(None), run_state_type: Optional[str] = Query(None, description="With run_state_name: filter runs by column 'status' or 'outcome'"), run_state_name: Optional[str] = Query(None, description='With run_state_type: exact value for that run column'))`

**异常**: `HTTPException`

#### def `create_task(payload: CreateTaskBody, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `list_task_attachments(task_id: str, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `upload_task_attachment(task_id: str, file: UploadFile = File(...), board: Optional[str] = Query(None), uploaded_by: Optional[str] = Form(None))`

Store an uploaded file for a task and record its metadata.

The blob lands under ``attachments_root(board)/<task_id>/`` with a
sanitised, collision-resolved name. The worker reads it via the
absolute path surfaced in ``build_worker_context``.

**异常**: `HTTPException`

#### def `download_attachment(attachment_id: int, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `remove_attachment(attachment_id: int, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `update_task(task_id: str, payload: UpdateTaskBody, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `delete_task(task_id: str, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `add_comment(task_id: str, payload: CommentBody, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `add_link(payload: LinkBody, board: Optional[str] = Query(None))`

**异常**: `HTTPException`

#### def `delete_link(parent_id: str = Query(...), child_id: str = Query(...), board: Optional[str] = Query(None))`

#### def `bulk_update(payload: BulkTaskBody, board: Optional[str] = Query(None))`

Apply the same patch to every id in ``payload.ids``.

This is an *independent* iteration — per-task failures don't abort
siblings. Returns per-id outcome so the UI can surface partials.

**异常**: `HTTPException`

#### def `list_diagnostics(board: Optional[str] = Query(None, description='Kanban board slug (omit for current)'), severity: Optional[str] = Query(None, description='Filter by severity: warning|error|critical'))`

Return ``[{task_id, task_title, task_status, task_assignee,
diagnostics: [...]}, ...]`` for every task on the board with at
least one active diagnostic.

Severity-filterable so the UI can render "just the critical ones"
or the CLI can grep. Useful for the board-header attention strip
AND for ``hermes kanban diagnostics`` which shells to this
endpoint when the dashboard's running, or invokes the engine
directly when it isn't.

#### def `list_active_workers(board: Optional[str] = Query(None, description='Kanban board slug (omit for current)'))`

Return every currently-running worker on the board.

A worker is a ``task_runs`` row whose ``ended_at`` is NULL and whose
``worker_pid`` is non-NULL, belonging to a task with ``status='running'``.

Returns ``{workers: [...], count: N, checked_at: <epoch>}``.  Each
worker entry carries enough context for the dashboard to link back to
its task without a second round-trip.

#### def `get_run_endpoint(run_id: int, board: Optional[str] = Query(None, description='Kanban board slug (omit for current)'))`

Direct lookup of a ``task_runs`` row by its integer id.

Returns ``{run: {...}}`` using the same serialisation as the
per-task run history embedded in ``GET /tasks/{task_id}``.
404 when no such run exists.

**异常**: `HTTPException`

#### def `inspect_run_endpoint(run_id: int, board: Optional[str] = Query(None, description='Kanban board slug (omit for current)'))`

Live PID stats for a run's worker process via psutil.

If the run has already ended, or has no recorded ``worker_pid``,
returns ``{alive: false}`` with a human-readable ``reason``.

When the process is live, returns CPU, memory, thread count, fd count,
status, create_time, and cmdline.  ``access_denied`` is set when the
OS refuses inspection rather than raising a 500.

psutil availability: if psutil is not installed the endpoint still
works but ``alive`` is always returned as ``false`` with
``reason="psutil not available"``.

**异常**: `HTTPException`

#### def `terminate_run_endpoint(run_id: int, payload: TerminateRunBody, board: Optional[str] = Query(None, description='Kanban board slug (omit for current)'))`

Terminate the worker process backing an in-flight run.

Resolves ``run_id`` to its parent ``task_id`` and routes through
:func:`kanban_db.reclaim_task` so the SIGTERM->SIGKILL flow,
run-outcome bookkeeping, and event-log append all match what the
existing ``POST /tasks/{task_id}/reclaim`` endpoint does.

Responses:
  * 200 ``{"ok": true, "run_id": ..., "task_id": ...}`` on success.
  * 404 when ``run_id`` is unknown.
  * 409 when the run has already ended, or the task is no longer in
    a claimable state.

Closes the gap left by PR #28432, which shipped the read-only
sibling endpoints (``/workers/active``, ``/runs/{run_id}``,
``/runs/{run_id}/inspect``) but no termination control surface.

**异常**: `HTTPException`

#### def `reclaim_task_endpoint(task_id: str, payload: ReclaimBody, board: Optional[str] = Query(None))`

Release an active worker claim on a running task.

Used by the dashboard recovery popover when an operator wants to
abort a stuck worker (e.g. one that keeps hallucinating card ids)
without waiting for the claim TTL. Maps 1:1 to
``hermes kanban reclaim <task_id> --reason ...``.

**异常**: `HTTPException`

#### def `specify_task_endpoint(task_id: str, payload: SpecifyBody, board: Optional[str] = Query(None))`

Flesh out a triage-column task via the auxiliary LLM and promote
it to ``todo``. Maps 1:1 to ``hermes kanban specify <task_id>``.

Returns the outcome shape used by the CLI: ``{ok, task_id, reason,
new_title}``. A non-OK outcome is NOT an HTTP error — the UI renders
the reason inline (e.g. "no auxiliary client configured") so the
operator knows what to fix, and retries without a page reload.

This endpoint runs in FastAPI's threadpool (sync ``def``) because
the underlying LLM call can take tens of seconds to minutes on
reasoning models, which would block the event loop if we used
``async def`` without an explicit ``run_in_executor``.

#### def `reassign_task_endpoint(task_id: str, payload: ReassignBody, board: Optional[str] = Query(None))`

Reassign a task to a different profile, optionally reclaiming first.

Used by the dashboard recovery popover when an operator wants to
retry a task with a different worker profile (e.g. switch to a
smarter model after the assigned profile keeps hallucinating).
Maps 1:1 to ``hermes kanban reassign <task_id> <profile> [--reclaim]``.

**异常**: `HTTPException`

#### def `get_config()`

Return kanban dashboard preferences from ~/.hermes/config.yaml.

Reads the ``dashboard.kanban`` section if present; defaults otherwise.
Used by the UI to pre-select tenant filters, toggle markdown rendering,
or set column-width preferences without a round-trip per page load.

#### def `get_home_channels(task_id: Optional[str] = Query(None), board: Optional[str] = Query(None))`

List every platform with a home channel, plus whether *task_id*
(if given) is currently subscribed to that home.

When ``task_id`` is omitted, every entry's ``subscribed`` is ``false``
— useful for the "no task selected" state of the UI.

#### def `subscribe_home(task_id: str, platform: str, board: Optional[str] = Query(None))`

Subscribe *task_id* to notifications routed to *platform*'s home channel.

Idempotent — re-subscribing is a no-op at the DB layer. 404 if the
platform has no home channel configured. 404 if the task doesn't exist.

**异常**: `HTTPException`

#### def `unsubscribe_home(task_id: str, platform: str, board: Optional[str] = Query(None))`

Remove any notify subscription on *task_id* that matches *platform*'s home.

**异常**: `HTTPException`

#### def `get_stats(board: Optional[str] = Query(None))`

Per-status + per-assignee counts + oldest-ready age.

Designed for the dashboard HUD and for router profiles that need to
answer "is this specialist overloaded?" without scanning the whole
board themselves.

#### def `get_assignees(board: Optional[str] = Query(None))`

Known profiles + per-profile task counts.

Returns the union of ``~/.hermes/profiles/*`` on disk and every
distinct assignee currently used on the board. The dashboard uses
this to populate its assignee dropdown so a freshly-created profile
appears in the picker before it's been given any task.

#### def `get_task_log(task_id: str, tail: Optional[int] = Query(None, ge=1, le=2000000), board: Optional[str] = Query(None))`

Return the worker's stdout/stderr log.

``tail`` caps the response size (bytes) so the dashboard drawer
doesn't paginate megabytes into the browser. Returns 404 if the task
has never spawned. The on-disk log is rotated at 2 MiB per
``_rotate_worker_log`` — a single ``.log.1`` is kept, no further
generations, so disk usage per task is bounded at ~4 MiB.

**异常**: `HTTPException`

#### def `dispatch(dry_run: bool = Query(False), max_n: int = Query(8, alias='max'), board: Optional[str] = Query(None))`

#### def `list_boards(include_archived: bool = Query(False))`

Return every board on disk with task counts and the active slug.

#### def `create_board_endpoint(payload: CreateBoardBody)`

Create a new board. Idempotent — ``slug`` collision returns existing.

**异常**: `HTTPException`

#### def `rename_board(slug: str, payload: RenameBoardBody)`

Update a board's display metadata + default project directory (slug is immutable — create a new one to rename the directory).

**异常**: `HTTPException`

#### def `delete_board(slug: str, delete: bool = Query(False, description='Hard-delete instead of archive'))`

Archive (default) or hard-delete a board.

**异常**: `HTTPException`

#### def `switch_board(slug: str)`

Persist ``slug`` as the active board for subsequent CLI / slash calls.

Dashboard users pick boards via a client-side ``localStorage`` — this
endpoint is for ``/kanban boards switch`` parity so gateway slash
commands and the CLI share the same current-board pointer.

**异常**: `HTTPException`

#### def `list_profile_roster()`

Return every installed profile with its description.

Consumed by the dashboard's settings panel (orchestrator picker)
and the profile-description editing UI. Profiles without a
description still appear here — they're routable on name alone,
just less precisely.

**异常**: `HTTPException`

#### def `update_profile_description(profile_name: str, payload: DescribeBody)`

Set or clear the description of a profile.

Empty string clears the description; non-empty stores it as a
user-authored description (``description_auto: false``) so the
auto-describer won't overwrite it on a sweep without
``--overwrite``.

**异常**: `HTTPException`

#### def `auto_describe_profile(profile_name: str, payload: DescribeAutoBody)`

Generate a description for the named profile via the auxiliary
LLM (``auxiliary.profile_describer``). Persists with
``description_auto: true`` so the dashboard can surface a "review"
badge.

Maps 1:1 to ``hermes profile describe <name> --auto``. Non-OK
outcomes are NOT HTTP errors — the UI renders the reason inline
(e.g. "no auxiliary client configured") so the operator can fix
config and retry without a page reload.

**异常**: `HTTPException`

#### def `decompose_task_endpoint(task_id: str, payload: DecomposeBody, board: Optional[str] = Query(None))`

Fan a triage-column task out into a graph of child tasks via the
auxiliary LLM, routed to specialist profiles by description. Maps
1:1 to ``hermes kanban decompose <task_id>``.

Returns the outcome shape used by the CLI: ``{ok, task_id, reason,
fanout, child_ids, new_title}``. A non-OK outcome is NOT an HTTP
error — the UI renders the reason inline.

Runs in FastAPI's threadpool (sync ``def``) because the LLM call
can take minutes on reasoning models.

#### def `get_orchestration_settings()`

Return the current kanban orchestration knobs from config.yaml
plus the resolved effective values (filling in fallbacks).

#### def `set_orchestration_settings(payload: OrchestrationSettingsBody)`

Update the kanban orchestration knobs in ~/.hermes/config.yaml.

Each field is optional — only fields explicitly passed are
written. ``orchestrator_profile`` / ``default_assignee`` accept
empty strings to clear the override and fall back to the default
profile.

**异常**: `HTTPException`

#### def `stream_events(ws: WebSocket)`


## plugins.memory.__init__

### 模块文档

Memory provider plugin discovery.

Scans two directories for memory provider plugins:

1. Bundled providers: ``plugins/memory/<name>/`` (shipped with hermes-agent)
2. User-installed providers: ``$HERMES_HOME/plugins/<name>/``

Each subdirectory must contain ``__init__.py`` with a class implementing
the MemoryProvider ABC.  On name collisions, bundled providers take
precedence.

Only ONE provider can be active at a time, selected via
``memory.provider`` in config.yaml.

Usage:
    from plugins.memory import discover_memory_providers, load_memory_provider

    available = discover_memory_providers()   # [(name, desc, available), ...]
    provider = load_memory_provider("mnemosyne")  # MemoryProvider instance

### 顶层函数

#### def `find_provider_dir(name: str) -> Optional[Path]`

Resolve a provider name to its directory.

Checks bundled first, then user-installed.

#### def `list_memory_provider_names() -> List[str]`

Cheap name-only listing of discoverable memory providers.

Unlike :func:`discover_memory_providers`, this does NOT import provider
modules or run availability checks — it's a directory scan only, safe to
call at module-import time (e.g. when building the dashboard config
schema).

#### def `discover_memory_providers() -> List[Tuple[str, str, bool]]`

Scan bundled and user-installed directories for available providers.

Returns list of (name, description, is_available) tuples.
Bundled providers take precedence on name collisions.

#### def `load_memory_provider(name: str) -> Optional['MemoryProvider']`

Load and return a MemoryProvider instance by name.

Checks both bundled (``plugins/memory/<name>/``) and user-installed
(``$HERMES_HOME/plugins/<name>/``) directories.  Bundled takes
precedence on name collisions.

Returns None if the provider is not found or fails to load.

#### def `discover_plugin_cli_commands() -> List[dict]`

Return CLI commands for the **active** memory plugin only.

Only one memory provider can be active at a time (set via
``memory.provider`` in config.yaml).  This function reads that
value and only loads CLI registration for the matching plugin.
If no provider is active, no commands are registered.

Looks for a ``register_cli(subparser)`` function in the active
plugin's ``cli.py``.  Returns a list of at most one dict with
keys: ``name``, ``help``, ``description``, ``setup_fn``,
``handler_fn``.

This is a lightweight scan — it only imports ``cli.py``, not the
full plugin module.  Safe to call during argparse setup before
any provider is loaded.


## plugins.memory.byterover.__init__

### 模块文档

ByteRover memory plugin — MemoryProvider interface.

Persistent memory via the ByteRover CLI (``brv``). Organizes knowledge into
a hierarchical context tree with tiered retrieval (fuzzy text → LLM-driven
search). Local-first with optional cloud sync.

Original PR #3499 by hieuntg81, adapted to MemoryProvider ABC.

Requires: ``brv`` CLI installed (npm install -g byterover-cli or
curl -fsSL https://byterover.dev/install.sh | sh).

Config via environment variables (profile-scoped via each profile's .env):
  BRV_API_KEY   — ByteRover API key (for cloud features, optional for local)

Config via config.yaml:
  memory:
    byterover:
      auto_extract: false  # disable automatic brv curate hooks

Working directory: $HERMES_HOME/byterover/ (profile-scoped context tree)

### class ByteRoverMemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 17（公开 13）

ByteRover persistent memory via the brv CLI.

#### def `__init__(config: Optional[Dict[str, Any]] = None)`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

Check if brv CLI is installed. No network calls.

#### def `get_config_schema(self)`

#### def `initialize(self, session_id: str, **kwargs) -> None`

#### def `system_prompt_block(self) -> str`

#### def `prefetch(self, query: str, session_id: str = '') -> str`

Run brv query synchronously before the agent's first LLM call.

Blocks until the query completes (up to _QUERY_TIMEOUT seconds), ensuring
the result is available as context before the model is called.

#### def `queue_prefetch(self, query: str, session_id: str = '') -> None`

No-op: prefetch() now runs synchronously at turn start.

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '') -> None`

Curate the conversation turn in background (non-blocking).

#### def `on_memory_write(self, action: str, target: str, content: str) -> None`

Mirror built-in memory writes to ByteRover.

#### def `on_pre_compress(self, messages: List[Dict[str, Any]]) -> str`

Extract insights before context compression discards turns.

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

#### def `handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str`

#### def `shutdown(self) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Register ByteRover as a memory provider plugin.


## plugins.memory.config_schema

### 模块文档

Declarative configuration schema for memory provider plugins.

Each memory provider plugin *declares* its configurable surface in a
``config_schema.py`` next to its ``__init__.py`` — the fields, their types,
which values are secrets, and (for selects) the allowed options. A single
generic renderer in the desktop UI and a single generic ``GET/PUT
/api/memory/providers/{name}/config`` endpoint pair drive the whole
experience, so adding a provider config surface is pure declaration with no
bespoke UI components.

Schema files are loaded by path (like the provider plugins themselves), never
via package import: plugin ``__init__.py`` files pull in the agent runtime,
which must not load into the web server. A ``config_schema.py`` may only
import from this module.

This module is intentionally pure data: it imports nothing from the
config/env layer. ``web_server`` owns the generic read/write logic that
interprets these declarations, dispatching on ``ProviderConfigSchema.storage``
to the matching backend.

### class ProviderFieldOption

> 继承: `object` ｜ 方法数: 0（公开 0）

A single choice for a ``select`` field.


### class ProviderField

> 继承: `object` ｜ 方法数: 2（公开 2）

One configurable field on a memory provider.

A field is stored in exactly one place, decided by ``kind``:

* non-secret kinds — persisted to the provider's config via its storage
  backend under ``key``.
* ``secret`` — persisted to the env store under ``env_key`` and never read
  back out over the API (only an ``is_set`` flag is surfaced).

``aliases`` and ``env_fallbacks`` let a field read legacy values written by
earlier CLI/env setup without re-introducing per-provider code. ``inline``
marks the curated subset shown in the compact panel; the rest surface only
in the full-config modal. ``group`` buckets fields within that modal.

#### property `is_secret(self) -> bool`

#### def `allowed_values(self) -> set[str]`


### class ProviderConfigSchema

> 继承: `object` ｜ 方法数: 1（公开 1）

A provider plugin's declared config surface.

#### def `inline_fields(self) -> tuple[ProviderField, ...]`


### 顶层函数

#### def `get_provider_config_schema(name: str) -> ProviderConfigSchema | None`

Return the ``CONFIG_SCHEMA`` declared by the provider plugin ``name``.

Providers without a ``config_schema.py`` (e.g. ``builtin``) return ``None``
and simply render no config panel. The cache keys on the resolved schema
file, not the name: user-installed plugins are per-profile, so one
profile's lookup must never answer for another's.


## plugins.memory.hindsight.__init__

### 模块文档

Hindsight memory plugin — MemoryProvider interface.

Long-term memory with knowledge graph, entity resolution, and multi-strategy
retrieval. Supports cloud (API key) and local modes.

Configurable request timeout via HINDSIGHT_TIMEOUT env var or config.json.
Configurable embedded daemon idle timeout via HINDSIGHT_IDLE_TIMEOUT env var
or config.json idle_timeout.

Original PR #1811 by benfrank241, adapted to MemoryProvider ABC.

Config via environment variables:
  HINDSIGHT_API_KEY                — API key for Hindsight Cloud
  HINDSIGHT_BANK_ID                — memory bank identifier (default: hermes)
  HINDSIGHT_BUDGET                 — recall budget: low/mid/high (default: mid)
  HINDSIGHT_API_URL                — API endpoint
  HINDSIGHT_MODE                   — cloud or local (default: cloud)
  HINDSIGHT_TIMEOUT                — API request timeout in seconds (default: 120)
  HINDSIGHT_IDLE_TIMEOUT           — embedded daemon idle timeout seconds; 0 disables shutdown (default: 300)
  HINDSIGHT_EMBED_PORT_HEALTH_GRACE_TIMEOUT — seconds to wait for a slow embedded daemon /health before treating it as stale (default: 30; set via config.json port_health_grace_timeout)
  HINDSIGHT_RETAIN_TAGS            — comma-separated tags attached to retained memories
  HINDSIGHT_RETAIN_OBSERVATION_SCOPES — observation scoping for retained memories: per_tag/combined/all_combinations, or a JSON list of tag-lists for custom scopes
  HINDSIGHT_RETAIN_SOURCE          — metadata source value attached to retained memories
  HINDSIGHT_RETAIN_USER_PREFIX     — label used before user turns in retained transcripts
  HINDSIGHT_RETAIN_ASSISTANT_PREFIX — label used before assistant turns in retained transcripts

Or via $HERMES_HOME/hindsight/config.json (profile-scoped), falling back to
~/.hindsight/config.json (legacy, shared) for backward compatibility.

### class HindsightMemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 29（公开 15）

Hindsight long-term memory with knowledge graph and multi-strategy retrieval.

#### def `backup_paths(self) -> List[str]`

Hindsight's legacy shared config and embedded-mode profile env
files live under ~/.hindsight (see _load_config / line ~509).

#### def `__init__()`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

#### def `save_config(self, values, hermes_home)`

Write config to $HERMES_HOME/hindsight/config.json.

#### def `post_setup(self, hermes_home: str, config: dict) -> None`

Custom setup wizard — installs only the deps needed for the selected mode.

#### def `get_config_schema(self)`

#### def `initialize(self, session_id: str, **kwargs) -> None`

#### def `system_prompt_block(self) -> str`

#### def `prefetch(self, query: str, session_id: str = '') -> str`

#### def `queue_prefetch(self, query: str, session_id: str = '') -> None`

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '') -> None`

Enqueue a retain for the current turn. Non-blocking.

The actual aretain_batch runs on a single long-lived writer thread
that drains an in-memory queue. Once shutdown() has been called,
further sync_turn() calls are dropped — this prevents post-exit
retains from reaching aiohttp after interpreter shutdown begins.

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

#### def `handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str`

#### def `on_session_switch(self, new_session_id: str, parent_session_id: str = '', reset: bool = False, **kwargs) -> None`

Refresh cached per-session state when the agent rotates session_id.

Fires on /resume, /branch, /reset, /new, and context compression.
Without this hook, initialize()-cached state (``_session_id``,
``_document_id``, ``_session_turns``, ``_turn_counter``) would keep
pointing at the previous session and writes would land in the wrong
document. See hermes-agent#6672.

Always update ``_session_id`` so metadata and tags on subsequent
retains reflect the active session. Always mint a fresh
``_document_id`` so the new session's retain doesn't overwrite the
old session's document on vectorize-io/hindsight#1303. Always clear
the accumulated batch buffers (``_session_turns``, ``_turn_counter``,
``_turn_index``) — even for /resume and /branch, the new session's
batching must start from zero so an in-flight retain doesn't flush
under the wrong ``_document_id``.

Before clearing, flush any buffered turns under the *old*
``_document_id``. Users who set ``retain_every_n_turns > 1`` would
otherwise silently lose whatever's in ``_session_turns`` at the
moment of switch — the same data-loss class as the shutdown race,
just at a different lifecycle event.

Also wait for any in-flight prefetch from the old session and drop
its cached result; otherwise the new session's first ``prefetch()``
could read stale recall text from before the switch.

``parent_session_id`` is recorded for lineage tags on future retains.
``reset`` is accepted but not needed for Hindsight's state model —
buffer clearing is correct for every session switch, not only /reset.

#### def `shutdown(self) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Register Hindsight as a memory provider plugin.


## plugins.memory.hindsight.config_schema

### 模块文档

Hindsight's declared config surface — rendered by the generic desktop panel.

## plugins.memory.holographic.__init__

### 模块文档

hermes-memory-store — holographic memory plugin using MemoryProvider interface.

Registers as a MemoryProvider plugin, giving the agent structured fact storage
with entity resolution, trust scoring, and HRR-based compositional retrieval.

Original plugin by dusterbloom (PR #2351), adapted to the MemoryProvider ABC.

Config in $HERMES_HOME/config.yaml (profile-scoped):
  plugins:
    hermes-memory-store:
      db_path: $HERMES_HOME/memory_store.db   # omit to use the default
      auto_extract: false
      default_trust: 0.5
      min_trust_threshold: 0.3
      temporal_decay_half_life: 0

### class HolographicMemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 17（公开 13）

Holographic memory with structured facts, entity resolution, and HRR retrieval.

#### def `__init__(config: dict | None = None)`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

#### def `save_config(self, values, hermes_home)`

Write config to config.yaml under plugins.hermes-memory-store.

#### def `get_config_schema(self)`

#### def `initialize(self, session_id: str, **kwargs) -> None`

#### def `system_prompt_block(self) -> str`

#### def `prefetch(self, query: str, session_id: str = '') -> str`

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '') -> None`

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

#### def `handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str`

#### def `on_session_end(self, messages: List[Dict[str, Any]]) -> None`

#### def `on_memory_write(self, action: str, target: str, content: str) -> None`

Mirror built-in memory writes as facts.

#### def `shutdown(self) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Register the holographic memory provider with the plugin system.


## plugins.memory.holographic.holographic

### 模块文档

Holographic Reduced Representations (HRR) with phase encoding.

HRRs are a vector symbolic architecture for encoding compositional structure
into fixed-width distributed representations. This module uses *phase vectors*:
each concept is a vector of angles in [0, 2π). The algebraic operations are:

  bind   — circular convolution (phase addition)  — associates two concepts
  unbind — circular correlation (phase subtraction) — retrieves a bound value
  bundle — superposition (circular mean)           — merges multiple concepts

Phase encoding is numerically stable, avoids the magnitude collapse of
traditional complex-number HRRs, and maps cleanly to cosine similarity.

Atoms are generated deterministically from SHA-256 so representations are
identical across processes, machines, and language versions.

References:
  Plate (1995) — Holographic Reduced Representations
  Gayler (2004) — Vector Symbolic Architectures answer Jackendoff's challenges

### 顶层函数

#### def `encode_atom(word: str, dim: int = 1024) -> np.ndarray`

Deterministic phase vector via SHA-256 counter blocks.

Uses hashlib (not numpy RNG) for cross-platform reproducibility.

Algorithm:
- Generate enough SHA-256 blocks by hashing f"{word}:{i}" for i=0,1,2,...
- Concatenate digests, interpret as uint16 values via struct.unpack
- Scale to [0, 2π): phases = values * (2π / 65536)
- Truncate to dim elements
- Returns np.float64 array of shape (dim,)

#### def `bind(a: np.ndarray, b: np.ndarray) -> np.ndarray`

Circular convolution = element-wise phase addition.

Binding associates two concepts into a single composite vector.
The result is dissimilar to both inputs (quasi-orthogonal).

#### def `unbind(memory: np.ndarray, key: np.ndarray) -> np.ndarray`

Circular correlation = element-wise phase subtraction.

Unbinding retrieves the value associated with a key from a memory vector.
unbind(bind(a, b), a) ≈ b  (up to superposition noise)

#### def `bundle(*vectors: np.ndarray) -> np.ndarray`

Superposition via circular mean of complex exponentials.

Bundling merges multiple vectors into one that is similar to each input.
The result can hold O(sqrt(dim)) items before similarity degrades.

#### def `similarity(a: np.ndarray, b: np.ndarray) -> float`

Phase cosine similarity. Range [-1, 1].

Returns 1.0 for identical vectors, near 0.0 for random (unrelated) vectors,
and -1.0 for perfectly anti-correlated vectors.

#### def `encode_text(text: str, dim: int = 1024) -> np.ndarray`

Bag-of-words: bundle of atom vectors for each token.

Tokenizes by lowercasing, splitting on whitespace, and stripping
leading/trailing punctuation from each token.

Returns bundle of all token atom vectors.
If text is empty or produces no tokens, returns encode_atom("__hrr_empty__", dim).

#### def `encode_fact(content: str, entities: list[str], dim: int = 1024) -> np.ndarray`

Structured encoding: content bound to ROLE_CONTENT, each entity bound to ROLE_ENTITY, all bundled.

Role vectors are reserved atoms: "__hrr_role_content__", "__hrr_role_entity__"

Components:
1. bind(encode_text(content, dim), encode_atom("__hrr_role_content__", dim))
2. For each entity: bind(encode_atom(entity.lower(), dim), encode_atom("__hrr_role_entity__", dim))
3. bundle all components together

This enables algebraic extraction:
    unbind(fact, bind(entity, ROLE_ENTITY)) ≈ content_vector

#### def `phases_to_bytes(phases: np.ndarray) -> bytes`

Serialize phase vector to bytes. float64 tobytes — 8 KB at dim=1024.

#### def `bytes_to_phases(data: bytes) -> np.ndarray`

Deserialize bytes back to phase vector. Inverse of phases_to_bytes.

The .copy() call is required because frombuffer returns a read-only view
backed by the bytes object; callers expect a mutable array.

#### def `snr_estimate(dim: int, n_items: int) -> float`

Signal-to-noise ratio estimate for holographic storage.

SNR = sqrt(dim / n_items) when n_items > 0, else inf.

The SNR falls below 2.0 when n_items > dim / 4, meaning retrieval
errors become likely. Logs a warning when this threshold is crossed.


## plugins.memory.holographic.retrieval

### 模块文档

Hybrid keyword/BM25 retrieval for the memory store.

Ported from KIK memory_agent.py — combines FTS5 full-text search with
Jaccard similarity reranking and trust-weighted scoring.

### class FactRetriever

> 继承: `object` ｜ 方法数: 12（公开 5）

Multi-strategy fact retrieval with trust-weighted scoring.

#### def `__init__(store: MemoryStore, temporal_decay_half_life: int = 0, fts_weight: float = 0.4, jaccard_weight: float = 0.3, hrr_weight: float = 0.3, hrr_dim: int = 1024)`

#### def `search(self, query: str, category: str | None = None, min_trust: float = 0.3, limit: int = 10) -> list[dict]`

Hybrid search: FTS5 candidates → Jaccard rerank → trust weighting.

Pipeline:
1. FTS5 search: Get limit*3 candidates from SQLite full-text search
2. Jaccard boost: Token overlap between query and fact content
3. Trust weighting: final_score = relevance * trust_score
4. Temporal decay (optional): decay = 0.5^(age_days / half_life)

Returns list of dicts with fact data + 'score' field, sorted by score desc.

#### def `probe(self, entity: str, category: str | None = None, limit: int = 10) -> list[dict]`

Compositional entity query using HRR algebra.

Unbinds entity from memory bank to extract associated content.
This is NOT keyword search — it uses algebraic structure to find facts
where the entity plays a structural role.

Falls back to FTS5 search if numpy unavailable.

#### def `related(self, entity: str, category: str | None = None, limit: int = 10) -> list[dict]`

Discover facts that share structural connections with an entity.

Unlike probe (which finds facts *about* an entity), related finds
facts that are connected through shared context — e.g., other entities
mentioned alongside this one, or content that overlaps structurally.

Falls back to FTS5 search if numpy unavailable.

#### def `reason(self, entities: list[str], category: str | None = None, limit: int = 10) -> list[dict]`

Multi-entity compositional query — vector-space JOIN.

Given multiple entities, algebraically intersects their structural
connections to find facts related to ALL of them simultaneously.
This is compositional reasoning that no embedding DB can do.

Example: reason(["peppi", "backend"]) finds facts where peppi AND
backend both play structural roles — without keyword matching.

Falls back to FTS5 search if numpy unavailable.

#### def `contradict(self, category: str | None = None, threshold: float = 0.3, limit: int = 10) -> list[dict]`

Find potentially contradictory facts via entity overlap + content divergence.

Two facts contradict when they share entities (same subject) but have
low content-vector similarity (different claims). This is automated
memory hygiene — no other memory system does this.

Returns pairs of facts with a contradiction score.
Falls back to empty list if numpy unavailable.


## plugins.memory.holographic.store

### 模块文档

SQLite-backed fact store with entity resolution and trust scoring.
Single-user Hermes memory store plugin.

### class MemoryStore

> 继承: `object` ｜ 方法数: 18（公开 8）

SQLite-backed fact store with entity resolution and trust scoring.

#### def `__init__(db_path: str | Path | None = None, default_trust: float = 0.5, hrr_dim: int = 1024) -> None`

#### def `add_fact(self, content: str, category: str = 'general', tags: str = '') -> int`

Insert a fact and return its fact_id.

Deduplicates by content (UNIQUE constraint). On duplicate, returns
the existing fact_id without modifying the row. Extracts entities from
the content and links them to the fact.

**异常**: `ValueError`

#### def `search_facts(self, query: str, category: str | None = None, min_trust: float = 0.3, limit: int = 10) -> list[dict]`

Full-text search over facts using FTS5.

Returns a list of fact dicts ordered by FTS5 rank, then trust_score
descending. Also increments retrieval_count for matched facts.

#### def `update_fact(self, fact_id: int, content: str | None = None, trust_delta: float | None = None, tags: str | None = None, category: str | None = None) -> bool`

Partially update a fact. Trust is clamped to [0, 1].

Returns True if the row existed, False otherwise.

#### def `remove_fact(self, fact_id: int) -> bool`

Delete a fact and its entity links. Returns True if the row existed.

#### def `list_facts(self, category: str | None = None, min_trust: float = 0.0, limit: int = 50) -> list[dict]`

Browse facts ordered by trust_score descending.

Optionally filter by category and minimum trust score.

#### def `record_feedback(self, fact_id: int, helpful: bool) -> dict`

Record user feedback and adjust trust asymmetrically.

helpful=True  -> trust += 0.05, helpful_count += 1
helpful=False -> trust -= 0.10

Returns a dict with fact_id, old_trust, new_trust, helpful_count.
Raises KeyError if fact_id does not exist.

**异常**: `KeyError`

#### def `rebuild_all_vectors(self, dim: int | None = None) -> int`

Recompute all HRR vectors + banks from text. For recovery/migration.

Returns the number of facts processed.

#### def `close(self) -> None`

Release this instance's reference to the shared connection.

The underlying connection is closed only when the last MemoryStore
referencing the same database is closed, so closing one instance can
never break sibling instances that still hold it. Idempotent.


## plugins.memory.honcho.__init__

### 模块文档

Honcho memory plugin — MemoryProvider for Honcho AI-native memory.

Provides cross-session user modeling with dialectic Q&A, semantic search,
peer cards, and persistent conclusions via the Honcho SDK. Honcho provides AI-native cross-session user
modeling with dialectic Q&A, semantic search, peer cards, and conclusions.

Five tools (profile, search, reasoning, context, conclude) are exposed
through the MemoryProvider interface.

Config: Uses the existing Honcho config chain:
  1. $HERMES_HOME/honcho.json (profile-scoped)
  2. ~/.honcho/config.json (legacy global)
  3. Environment variables

### class HonchoMemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 37（公开 18）

Honcho AI-native memory with dialectic Q&A and persistent user modeling.

#### def `backup_paths(self) -> List[str]`

Honcho keeps its peer/session config under ~/.honcho when no
profile-local honcho.json exists (see client.resolve_config_path).

#### def `__init__(query_rewriter: Optional[Callable[[str], str]] = None)`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

Check if Honcho is configured. No network calls.

#### def `save_config(self, values, hermes_home)`

Write config to $HERMES_HOME/honcho.json (Honcho SDK native format).

#### def `get_config_schema(self)`

#### def `post_setup(self, hermes_home: str, config: dict) -> None`

Run the full Honcho setup wizard after provider selection.

#### def `initialize(self, session_id: str, **kwargs) -> None`

Initialize Honcho session manager.

Handles cron guards, recall configuration, session resolution,
memory migration, and optional dialectic prewarming.

#### def `system_prompt_block(self) -> str`

Return system prompt text, adapted by recall_mode.

Returns only the mode header and tool instructions — static text
that doesn't change between turns (prompt-cache friendly).
Live context (representation, card) is injected via prefetch().

#### def `prefetch(self, query: str, session_id: str = '') -> str`

Return base context (representation + card) plus dialectic supplement.

Assembles two layers:
1. Base context from peer.context() — cached, refreshed on context_cadence
2. Dialectic supplement — cached, refreshed on dialectic_cadence

Returns empty in tools-only mode and respects the configured injection
frequency and context budget.

#### def `queue_prefetch(self, query: str, session_id: str = '') -> None`

Fire background prefetch threads for the upcoming turn.

Context and dialectic refreshes have independent cadence controls.

#### def `liveness_snapshot(self) -> dict`

In-process snapshot of dialectic liveness state for diagnostics.

Returns current turn, last successful dialectic turn, pending-result
fire turn, empty streak, effective cadence, and thread status.

#### def `on_turn_start(self, turn_number: int, message: str, **kwargs) -> None`

Track turn count for cadence and injection_frequency logic.

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '') -> None`

Record the conversation turn in Honcho (non-blocking).

Messages exceeding the Honcho API limit (default 25k chars) are
split into multiple messages with continuation markers.

#### def `on_memory_write(self, action: str, target: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Mirror built-in user profile writes as Honcho conclusions.

``metadata`` is accepted for compatibility with the write-origin
work landed in main (commit 6a957a74); it's not yet threaded into
the Honcho conclusion payload.  Left as a follow-up so this PR
stays focused on the 7-PR consolidation and its review follow-ups.

#### def `on_session_end(self, messages: List[Dict[str, Any]]) -> None`

Flush all pending messages to Honcho on session end.

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

Return tool schemas, respecting recall_mode.

Context-only mode exposes no Honcho tools.

#### def `handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str`

Handle a Honcho tool call, with lazy session init for tools-only mode.

#### def `shutdown(self) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Register Honcho as a memory provider plugin.


## plugins.memory.honcho.cli

### 模块文档

CLI commands for Honcho integration management.

Handles: hermes honcho setup | status | sessions | map | peer

### 顶层函数

#### def `clone_honcho_for_profile(profile_name: str) -> bool`

Auto-clone Honcho config for a new profile from the default host block.

Called during profile creation. If Honcho is configured on the default
host, creates a new host block for the profile with inherited settings
and auto-derived workspace/aiPeer.

Returns True if a host block was created, False if Honcho isn't configured.

#### def `cmd_enable(args) -> None`

Enable Honcho for the active profile.

#### def `cmd_disable(args) -> None`

Disable Honcho for the active profile.

#### def `cmd_sync(args) -> None`

Sync Honcho config to all existing profiles.

Scans all Hermes profiles and creates host blocks for any that don't
have one yet. Inherits settings from the default host block.

#### def `sync_honcho_profiles_quiet() -> int`

Sync Honcho host blocks for all profiles. Returns count of newly created blocks.

Called from `hermes update` -- no output, no exceptions.

#### def `cmd_setup(args) -> None`

Interactive Honcho setup wizard.

#### def `cmd_status(args) -> None`

Show current Honcho config and connection status.

#### def `cmd_peers(args) -> None`

Show peer identities across all profiles.

#### def `cmd_sessions(args) -> None`

List known directory → session name mappings.

#### def `cmd_map(args) -> None`

Map current directory to a Honcho session name.

#### def `cmd_peer(args) -> None`

Show or update peer names and dialectic reasoning level.

#### def `cmd_mode(args) -> None`

Show or set the recall mode.

#### def `cmd_strategy(args) -> None`

Show or set the session strategy.

#### def `cmd_tokens(args) -> None`

Show or set token budget settings.

#### def `cmd_identity(args) -> None`

Seed AI peer identity or show both peer representations.

#### def `cmd_migrate(args) -> None`

Step-by-step migration guide: OpenClaw native memory → Hermes + Honcho.

#### def `honcho_command(args) -> None`

Route honcho subcommands.

#### def `register_cli(subparser) -> None`

Build the ``hermes honcho`` argparse subcommand tree.

Called by the plugin CLI registration system during argparse setup.
The *subparser* is the parser for ``hermes honcho``.


## plugins.memory.honcho.client

### 模块文档

Honcho client initialization and configuration.

Resolution order for config file:
  1. $HERMES_HOME/honcho.json  (instance-local, enables isolated Hermes instances)
  2. ~/.honcho/config.json     (global, shared across all Honcho-enabled apps)
  3. Environment variables     (HONCHO_API_KEY, HONCHO_ENVIRONMENT)

Resolution order for host-specific settings:
  1. Explicit host block fields (always win)
  2. Flat/global fields from config root
  3. Defaults (host name as workspace/peer)

### class HonchoClientConfig

> 继承: `object` ｜ 方法数: 5（公开 3）

Configuration for Honcho client, resolved for a specific host.

#### classmethod `from_env(cls, workspace_id: str = 'hermes', host: str | None = None) -> HonchoClientConfig`

Create config from environment variables (fallback).

#### classmethod `from_global_config(cls, host: str | None = None, config_path: Path | None = None) -> HonchoClientConfig`

Create config from the resolved Honcho config path.

Resolution: $HERMES_HOME/honcho.json -> ~/.honcho/config.json -> env vars.
When host is None, derives it from the active Hermes profile.

#### def `resolve_session_name(self, cwd: str | None = None, session_title: str | None = None, session_id: str | None = None, gateway_session_key: str | None = None) -> str | None`

Resolve Honcho session name.

Resolution order:
  1. Gateway session key (stable per-chat identifier from gateway platforms)
  2. per-session strategy — Hermes session_id ({timestamp}_{hex}); authoritative,
     so a generated title never remaps a live conversation
  3. Manual directory override from sessions map
  4. Hermes session title (from /title command; non-per-session)
  5. per-repo strategy — git repo root directory name
  6. per-directory strategy — directory basename
  7. global strategy — workspace name


### 顶层函数

#### def `profile_host_key(profile: str | None) -> str`

Return the safe Honcho host key for a Hermes profile.

#### def `resolve_active_host() -> str`

Derive the Honcho host key from the active Hermes profile.

Resolution order:
  1. HERMES_HONCHO_HOST env var (explicit override)
  2. Active profile name via profiles system -> ``hermes_<profile>``
  3. defaultHost from the active config, but only for the default profile
  4. Fallback: ``"hermes"`` (default profile)

#### def `resolve_global_config_path() -> Path`

Return the shared Honcho config path for the current HOME.

#### def `resolve_config_path() -> Path`

Return the active Honcho config path.

Resolution order:
  1. $HERMES_HOME/honcho.json      (profile-local, if it exists)
  2. ~/.hermes/honcho.json          (default profile — shared host blocks live here)
  3. ~/.honcho/config.json          (global, cross-app interop)

Returns the global path if none exist (for first-time setup writes).

#### def `get_honcho_client(config: HonchoClientConfig | None = None) -> Honcho`

Get or create the Honcho client singleton.

When no config is provided, attempts to load ~/.honcho/config.json
first, falling back to environment variables.

Thread-safe: the client is built exactly once even under concurrent
first calls (double-checked locking via ``SingletonSlot``), so racing
threads can't each construct a client and leak the loser's connection.

**异常**: `ValueError`, `ImportError`

#### def `reset_honcho_client() -> None`

Reset the Honcho client singleton (useful for testing).


## plugins.memory.honcho.config_schema

### 模块文档

Honcho's declared config surface — rendered by the generic desktop panel.

## plugins.memory.honcho.oauth

### 模块文档

OAuth credential storage and refresh for the Honcho memory provider.

An access token authenticates exactly like a scoped API key, so it is stored
as the host's ``apiKey``; this module exchanges the refresh token before
expiry to keep it live.

Refresh tokens rotate with single-use reuse detection: a replayed stale token
revokes the whole grant. So every refresh must persist the rotated token
atomically and be serialized — and a failed refresh never raises into the
agent (stale token stays; the fail-open path absorbs the eventual 401).

### class OAuthCredential

> 继承: `object` ｜ 方法数: 3（公开 3）

An OAuth grant as stored in a honcho.json host block.

``access_token`` mirrors the host's ``apiKey``; the remaining fields live in
the host's ``oauth`` sub-block. ``expires_at`` is absolute epoch seconds.

#### classmethod `from_host_block(cls, block: dict[str, Any]) -> OAuthCredential | None`

Build a credential from a honcho.json host block, or None if incomplete.

#### def `oauth_block(self) -> dict[str, Any]`

The ``oauth`` sub-block to persist (the access token lives in apiKey).

#### def `is_expired(self, now: float, skew: float = _REFRESH_SKEW_SECONDS) -> bool`

True when the access token is within ``skew`` seconds of expiry.


### 顶层函数

#### def `is_oauth_access_token(value: str | None) -> bool`

True when ``value`` is an OAuth access token (vs a static API key).

#### def `ensure_fresh_token(path: Path, host: str, raw: dict[str, Any] | None = None, now: float | None = None) -> tuple[str | None, bool]`

Return ``(access_token, refreshed)`` for ``host``, refreshing if near expiry.

Returns ``(None, False)`` when the host has no OAuth credential (e.g. a plain
API key) so callers leave the existing token untouched. Refresh failures are
swallowed: the current (possibly stale) token is returned with
``refreshed=False`` and the fail-open path handles any resulting 401.

#### def `install_grant(path: Path, host: str, grant: dict[str, Any], client_id: str, token_endpoint: str, apply_config: bool = True, now: float | None = None) -> OAuthCredential`

Apply a fresh OAuth grant to ``path`` for ``host``.

Deep-merges the grant's ``config`` (the manifest default_config) into the
file root — preserving other hosts and root keys — then writes the host's
``apiKey`` and ``oauth`` block. ``grant`` is an OAuthTokenResponse dict
(access_token, refresh_token, expires_in, scope, config).
``apply_config=False`` skips the config merge and stores tokens only.

**异常**: `ValueError`

#### def `apply_token_to_client(client: Any, token: str) -> bool`

Rotate the live Honcho client's Bearer in place. Returns success.

The SDK builds its auth header per request from the HTTP client's
``api_key``, so mutating it rotates every holder of the singleton without a
rebuild. Guarded: an SDK shape change degrades to False and the caller can
fall back to resetting the client.


## plugins.memory.honcho.oauth_flow

### 模块文档

Browser sign-in flow for the Honcho memory provider — no CLI step.

``begin_authorization`` / ``complete_authorization`` are the transport-agnostic
core: the code can arrive via the loopback listener here or a future
``hermes://`` handler. Endpoints are env-overridable with local-dev defaults
because ``/authorize`` (dashboard) and ``/oauth/token`` (API) live on
different origins.

### class OAuthEndpoints

> 继承: `object` ｜ 方法数: 0（公开 0）

Resolved authorization-server URLs and client identity.


### class FlowStatus

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `resolve_endpoints(environment: str | None = None, base_url: str | None = None) -> OAuthEndpoints`

Resolve OAuth endpoints, zero-config by default.

Keys off the host's honcho ``environment`` (production → cloud, local →
localhost); a self-hosted ``base_url`` derives the token endpoint from the
API host. Env vars override every field for unusual deployments.

#### def `begin_authorization(endpoints: OAuthEndpoints, redirect_uri: str = LOOPBACK_REDIRECT_URI, source: str | None = None, config_path: str | None = None, now: float | None = None) -> tuple[str, str]`

Start an authorization: return ``(authorize_url, state)`` and stash PKCE.

``source`` tags the authorize link with the initiating surface
(``hermes-desktop`` / ``hermes-cli``) so the consent side can attribute
connects and vary behavior per surface. ``config_path`` is a home-relative
*display* string for the consent screen (never the absolute path); callers
pass the actual write path separately to ``complete_authorization``.

#### def `complete_authorization(endpoints: OAuthEndpoints, code: str, state: str, config_path: Path | None = None, host: str | None = None, apply_config: bool = True, now: float | None = None) -> oauth.OAuthCredential`

Exchange ``code`` for a grant and persist it. Raises on bad state/exchange.

``apply_config=False`` stores the tokens only, skipping the grant's config
block — the CLI path, where settings stay wizard-owned.

**异常**: `ValueError`

#### def `capture_loopback_code(server: HTTPServer, captured: dict[str, str], timeout: float = 300.0) -> tuple[str, str]`

Serve a single ``/callback`` GET on ``server`` and return ``(code, state)``.

Replies with a close-this-tab page, then stops. Raises ``TimeoutError`` if no
callback arrives within ``timeout``.

**异常**: `ValueError`, `TimeoutError`

#### def `authorize_via_loopback(config_path: Path | None = None, host: str | None = None, source: str | None = None, apply_config: bool = True, open_url: Callable[[str], None] | None = None, timeout: float = 300.0) -> oauth.OAuthCredential`

Drive the full loopback flow: open browser → capture code → exchange → persist.

``open_url`` defaults to the system browser; tests inject a driver that
follows the authorize redirect into the loopback callback. It always
receives the authorize URL, so a CLI caller can also print it for
browserless environments.

**异常**: `ValueError`

#### def `get_flow_status() -> dict[str, object]`

#### def `start_loopback_flow_background(config_path: Path | None = None, host: str | None = None, source: str = 'hermes-desktop', timeout: float = 300.0) -> dict[str, str]`

Launch the loopback flow in a daemon thread; returns the initial status.

Idempotent while a flow is pending — a second call is a no-op so a
double-clicked button can't open two browser tabs / bind :8765 twice.


## plugins.memory.honcho.session

### 模块文档

Honcho-based session management for conversation history.

### class HonchoSession

> 继承: `object` ｜ 方法数: 3（公开 3）

A conversation session backed by Honcho.

Provides a local message cache that syncs to Honcho's
AI-native memory system for user modeling.

#### def `add_message(self, role: str, content: str, **kwargs: Any) -> None`

Add a message to the local cache.

#### def `get_history(self, max_messages: int = 50) -> list[dict[str, Any]]`

Get message history for LLM context.

#### def `clear(self) -> None`

Clear all messages in the session.


### class HonchoSessionManager

> 继承: `object` ｜ 方法数: 43（公开 24）

Manages conversation sessions using Honcho.

Runs alongside hermes' existing SQLite state and file-based memory,
adding persistent cross-session user modeling via Honcho's AI-native memory.

#### def `__init__(honcho: Honcho | None = None, context_tokens: int | None = None, config: Any | None = None, runtime_user_peer_name: str | None = None, runtime_user_peer_name_alt: str | None = None)`

Initialize the session manager.

Args:
    honcho: Optional Honcho client. If not provided, uses the singleton.
    context_tokens: Max tokens for context() calls (None = Honcho default).
    config: HonchoClientConfig from global config (provides peer_name, ai_peer,
            write_frequency, observation, etc.).
    runtime_user_peer_name: Gateway user identity for per-user memory scoping.
    runtime_user_peer_name_alt: Optional stable alternate gateway identity.

#### property `honcho(self) -> Honcho`

Get the Honcho client, refreshing a near-expiry OAuth token in place.

Routes every access through ``get_honcho_client`` (which returns the same
cached singleton) so a long session can't outlive its 1h access token.

#### def `get_or_create(self, key: str) -> HonchoSession`

Get an existing session or create a new one.

Args:
    key: Session key (usually channel:chat_id).

Returns:
    The session.

#### def `save(self, session: HonchoSession) -> None`

Save messages to Honcho, respecting write_frequency.

write_frequency modes:
  "async"   — enqueue for background thread (zero blocking, zero token cost)
  "turn"    — flush synchronously every turn
  "session" — defer until flush_session() is called explicitly
  N (int)   — flush every N turns

#### def `flush_all(self) -> None`

Flush all pending unsynced messages for all cached sessions.

Called at session end for "session" write_frequency, or to force
a sync before process exit regardless of mode.

#### def `shutdown(self) -> None`

Gracefully shut down the async writer thread.

#### def `delete(self, key: str) -> bool`

Delete a session from local cache.

#### def `new_session(self, key: str) -> HonchoSession`

Create a new session, preserving the old one for user modeling.

Creates a fresh session with a new ID while keeping the old
session's data in Honcho for continued user modeling.

#### def `dialectic_query(self, session_key: str, query: str, reasoning_level: str | None = None, peer: str = 'user', apply_injection_cap: bool = True) -> str`

Query Honcho's dialectic endpoint about a peer.

Runs an LLM on Honcho's backend against the target peer's full
representation. Higher latency than context() — callers run this in
a background thread (see HonchoMemoryProvider) to avoid blocking.

Args:
    session_key: The session key to query against.
    query: Natural language question.
    reasoning_level: Override the configured default (dialecticReasoningLevel).
                     Only honored when dialecticDynamic is true.
                     If None or dialecticDynamic is false, uses the configured default.
    peer: Which peer to query — "user" (default) or "ai".
    apply_injection_cap: Clip automatic injections to
        ``dialecticMaxChars``. Explicit ``honcho_reasoning`` calls pass
        False because Honcho already bounds their output.

Returns:
    Honcho's synthesized answer, or empty string on failure.

#### def `prefetch_context(self, session_key: str, user_message: str | None = None) -> None`

Fire get_prefetch_context in a background thread, caching the result.

Non-blocking. Consumed next turn via pop_context_result(). This avoids
a synchronous HTTP round-trip blocking every response.

#### def `set_context_result(self, session_key: str, result: dict[str, str]) -> None`

Store a prefetched context result in a thread-safe way.

#### def `pop_context_result(self, session_key: str) -> dict[str, str]`

Return and clear the cached context result for this session.

Returns empty dict if no result is ready yet (first turn).

#### def `get_prefetch_context(self, session_key: str, user_message: str | None = None) -> dict[str, str]`

Pre-fetch user and AI peer context from Honcho.

Fetches peer_representation and peer_card for both peers, plus the
session summary when available. When user_message is provided, it is
passed as search_query to the peer context call so Honcho returns
conclusions relevant to the session topic rather than the full
observation dump.

Args:
    session_key: The session key to get context for.
    user_message: Optional first user message used as search_query for
                  topic-relevant context retrieval.

Returns:
    Dictionary with 'representation', 'card', 'ai_representation',
    'ai_card', and optionally 'summary' keys.

#### def `migrate_local_history(self, session_key: str, messages: list[dict[str, Any]]) -> bool`

Upload local session history to Honcho as a file.

Used when Honcho activates mid-conversation to preserve prior context.

Args:
    session_key: The session key (e.g., "telegram:123456").
    messages: Local messages (dicts with role, content, timestamp).

Returns:
    True if upload succeeded, False otherwise.

#### def `migrate_memory_files(self, session_key: str, memory_dir: str) -> bool`

Upload MEMORY.md and USER.md to Honcho as files.

Used when Honcho activates on an instance that already has locally
consolidated memory. Backwards compatible -- skips if files don't exist.

Args:
    session_key: The session key to associate files with.
    memory_dir: Path to the memories directory (~/.hermes/memories/).

Returns:
    True if at least one file was uploaded, False otherwise.

#### def `get_session_context(self, session_key: str, peer: str = 'user') -> dict[str, Any]`

Fetch full session context from Honcho including summary.

Uses the session-level context() API which returns summary,
peer_representation, peer_card, and messages.

#### def `get_peer_card(self, session_key: str, peer: str = 'user') -> list[str]`

Fetch a peer card — a curated list of key facts.

Fast, no LLM reasoning. Returns raw structured facts Honcho has
inferred about the target peer (name, role, preferences, patterns).
Empty list if unavailable.

#### def `search_context(self, session_key: str, query: str, max_tokens: int = 800, peer: str = 'user') -> str`

Search raw messages across every session visible from the target
peer's perspective. Results include all authors and require no LLM
synthesis.

Args:
    session_key: Session whose workspace/peer scope to search within.
    query: Search query (hybrid semantic + full-text).
    max_tokens: Approximate budget for returned content. Snippets are
        accumulated until this budget (≈4 chars/token) is exhausted.
    peer: Peer alias or explicit peer ID whose sessions to search.

Returns:
    Ranked message excerpts as a formatted string, or empty string
    if none found.

#### def `create_conclusion(self, session_key: str, content: str, peer: str = 'user') -> bool`

Write a conclusion about a target peer back to Honcho.

Conclusions are facts a peer observes about another peer or itself —
preferences, corrections, clarifications, and project context.
They feed into the target peer's card and representation.

Args:
    session_key: Session to associate the conclusion with.
    content: The conclusion text.
    peer: Peer alias or explicit peer ID. "user" is the default alias.

Returns:
    True on success, False on failure.

#### def `delete_conclusion(self, session_key: str, conclusion_id: str, peer: str = 'user') -> bool`

Delete a conclusion by ID. Use only for PII removal.

Args:
    session_key: Session key for peer resolution.
    conclusion_id: The conclusion ID to delete.
    peer: Peer alias or explicit peer ID.

Returns:
    True on success, False on failure.

#### def `list_conclusions(self, session_key: str, query: str | None = None, peer: str = 'user', limit: int = 20) -> list[dict]`

List or semantically search conclusions with their server IDs.

Args:
    session_key: Session key for peer resolution.
    query: Optional semantic search query. Omit to list recent conclusions.
    peer: Peer alias or explicit peer ID.
    limit: Max conclusions to return.

Returns:
    List of {"id": ..., "content": ...} dicts, or [] on failure/no session.

#### def `set_peer_card(self, session_key: str, card: list[str], peer: str = 'user') -> list[str] | None`

Update a peer's card.

Args:
    session_key: Session key for peer resolution.
    card: New peer card as list of fact strings.
    peer: Peer alias or explicit peer ID.

Returns:
    Updated card on success, None on failure.

#### def `seed_ai_identity(self, session_key: str, content: str, source: str = 'manual') -> bool`

Seed the AI peer's Honcho representation from text content.

Useful for priming AI identity from SOUL.md, exported chats, or
any structured description. The content is sent as an assistant
peer message so Honcho's reasoning model can incorporate it.

Args:
    session_key: The session key to associate with.
    content: The identity/persona content to seed.
    source: Metadata tag for the source (e.g. "soul_md", "export").

Returns:
    True on success, False on failure.

#### def `get_ai_representation(self, session_key: str) -> dict[str, str]`

Fetch the AI peer's current Honcho representation.

Returns:
    Dict with 'representation' and 'card' keys, empty strings if unavailable.

#### def `list_sessions(self) -> list[dict[str, Any]]`

List all cached sessions.


## plugins.memory.mem0.__init__

### 模块文档

Mem0 memory plugin — MemoryProvider interface.

Server-side LLM fact extraction, semantic search, and automatic deduplication
via the Mem0 Platform API (cloud) or OSS (self-hosted) via Memory.

Original PR #2933 by kartik-mem0, adapted to MemoryProvider ABC.

Configuration
-------------
Secret (lives in $HERMES_HOME/.env or the environment):
  MEM0_API_KEY       — Mem0 Platform API key (required for platform mode)
  MEM0_HOST          — Base URL of a self-hosted Mem0 server. When set, the
                       plugin talks to that server directly over HTTP
                       (X-API-Key auth) instead of the cloud API.

Behavioral settings (live in $HERMES_HOME/mem0.json, set via `hermes memory
setup`):
  mode               — Backend mode: "platform" (default) or "oss"
  host               — Self-hosted Mem0 server URL (alt: MEM0_HOST env var).
                       When set, routes to the self-hosted HTTP backend.
  user_id            — Canonical user identifier. When set, it is applied
                       uniformly across every gateway (CLI, Telegram, Slack,
                       Discord, …) so the same human gets one merged memory
                       store. When unset, the gateway-native id (e.g. Telegram
                       numeric id, Discord snowflake) is used instead.
  agent_id           — Agent identifier (default: hermes)

The matching MEM0_MODE / MEM0_USER_ID / MEM0_AGENT_ID environment variables are
still read as a backward-compatible fallback, but mem0.json is the canonical
home for these non-secret settings.

### class Mem0MemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 24（公开 13）

Mem0 memory with server-side extraction and semantic search.

Supports Platform API (cloud) and OSS (self-hosted) modes via MEM0_MODE.

#### def `__init__()`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

#### def `save_config(self, values, hermes_home)`

Write config to $HERMES_HOME/mem0.json.

#### def `get_config_schema(self)`

#### def `post_setup(self, hermes_home: str, config: dict) -> None`

#### def `initialize(self, session_id: str, **kwargs) -> None`

#### def `system_prompt_block(self) -> str`

#### def `on_turn_start(self, turn_number: int, message: str, **kwargs) -> None`

#### def `prefetch(self, query: str, session_id: str = '') -> str`

Recall memories for the CURRENT question with a short hot-path wait.

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '') -> None`

Send the turn to Mem0 for server-side fact extraction (non-blocking).

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

#### def `handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str`

#### def `shutdown(self) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Register Mem0 as a memory provider plugin.


## plugins.memory.mem0._backend

### 模块文档

Backend abstraction for Mem0 Platform and OSS modes.

### class Mem0Backend

> 继承: `ABC` ｜ 方法数: 5（公开 5）

Unified interface over Platform (MemoryClient) and OSS (Memory) backends.

#### def `search(self, query: str, filters: dict, top_k: int = 10, rerank: bool = False) -> list[dict]`

#### def `add(self, messages: list, user_id: str, agent_id: str, infer: bool = False, metadata: dict | None = None) -> dict`

#### def `update(self, memory_id: str, text: str) -> dict`

#### def `delete(self, memory_id: str) -> dict`

#### def `close(self) -> None`


### class PlatformBackend

> 继承: `Mem0Backend` ｜ 方法数: 5（公开 4）

Wraps mem0.MemoryClient for Mem0 Platform (cloud API).

#### def `__init__(api_key: str)`

#### def `search(self, query: str, filters: dict, top_k: int = 10, rerank: bool = False) -> list[dict]`

#### def `add(self, messages: list, user_id: str, agent_id: str, infer: bool = False, metadata: dict | None = None) -> dict`

#### def `update(self, memory_id: str, text: str) -> dict`

#### def `delete(self, memory_id: str) -> dict`


### class SelfHostedBackend

> 继承: `Mem0Backend` ｜ 方法数: 7（公开 5）

Direct HTTP backend for a self-hosted Mem0 server (the FastAPI ``server/``).

mem0.MemoryClient can't be reused for self-hosted: it is hardwired to the
cloud API — ``Authorization: Token`` auth and a ``GET /v1/ping/`` validation
call in ``__init__`` that the self-hosted server does not expose (it would
404 before any real request). This client talks to that server directly,
using its actual contract: ``X-API-Key`` auth and the ``/memories`` /
``/search`` routes.

#### def `__init__(api_key: str, host: str, transport = None)`

#### def `search(self, query: str, filters: dict, top_k: int = 10, rerank: bool = False) -> list[dict]`

#### def `add(self, messages: list, user_id: str, agent_id: str, infer: bool = False, metadata: dict | None = None) -> dict`

#### def `update(self, memory_id: str, text: str) -> dict`

#### def `delete(self, memory_id: str) -> dict`

#### def `close(self) -> None`


### class OSSBackend

> 继承: `Mem0Backend` ｜ 方法数: 7（公开 5）

Wraps mem0.Memory for self-hosted (OSS) mode.

#### def `__init__(oss_config: dict)`

#### def `search(self, query: str, filters: dict, top_k: int = 10, rerank: bool = False) -> list[dict]`

#### def `add(self, messages: list, user_id: str, agent_id: str, infer: bool = False, metadata: dict | None = None) -> dict`

#### def `update(self, memory_id: str, text: str) -> dict`

#### def `delete(self, memory_id: str) -> dict`

#### def `close(self)`


## plugins.memory.mem0._oss_providers

### 模块文档

OSS provider definitions for LLM, embedder, and vector store.

### 顶层函数

#### def `validate_oss_config(oss_config: dict) -> list[str]`

Validate an OSS config dict. Returns list of error strings (empty = valid).


## plugins.memory.mem0._setup

### 模块文档

Setup wizard for Mem0 plugin — interactive and flag-based modes.

### 顶层函数

#### def `has_oss_flags() -> bool`

Check if OSS-related flags are present in sys.argv.

#### def `parse_flags(argv: list[str] | None = None) -> dict[str, str]`

Parse CLI flags from argv. Returns dict of flag values.

#### def `build_oss_config(flags: dict[str, str]) -> tuple[dict, dict[str, str]]`

Build OSS config dict + env_writes from parsed flags.

Returns (oss_config, env_writes) where oss_config goes into mem0.json
and env_writes maps env var names to secret values for .env.

#### def `post_setup(hermes_home: str, config: dict) -> None`

Entry point called by hermes memory setup framework.

Routes on --mode (platform / selfhosted / oss); with no flag it shows an
interactive picker with all three modes. Platform keeps the framework's
original schema-based onboarding; selfhosted points at an existing Mem0
server; oss builds a local SDK config.


## plugins.memory.openviking.__init__

### 模块文档

OpenViking memory plugin — full bidirectional MemoryProvider interface.

Context database by Volcengine (ByteDance) that organizes agent knowledge
into a filesystem hierarchy (viking:// URIs) with tiered context loading,
automatic memory extraction, and session management.

Original PR #3369 by Mibayy, rewritten to use the full OpenViking session
lifecycle instead of read-only search endpoints.

Config via environment variables (profile-scoped via each profile's .env)
or a linked OpenViking CLI config:
  OPENVIKING_ENDPOINT  — Server URL (default: http://127.0.0.1:1933)
  OPENVIKING_API_KEY   — API key (required for authenticated servers)
  OPENVIKING_ACCOUNT   — Tenant account for local/trusted mode (default: default)
  OPENVIKING_USER      — Tenant user for local/trusted mode (default: default)
  OPENVIKING_AGENT     — Hermes peer ID in OpenViking (default: hermes)

Capabilities:
  - Automatic memory extraction on session commit (6 categories)
  - Tiered context: L0 (~100 tokens), L1 (~2k), L2 (full)
  - Semantic search with hierarchical directory retrieval
  - Filesystem-style browsing via viking:// URIs
  - Resource ingestion (URLs, docs, code)

### class OpenVikingMemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 71（公开 17）

Full bidirectional memory via OpenViking context database.

#### def `backup_paths(self) -> List[str]`

OpenViking's ovcli config lives at ~/.openviking/ovcli.conf by
default (or OPENVIKING_CLI_CONFIG_FILE). Capture the resolved file so
endpoint/api-key survive a backup/import cycle.

#### def `__init__()`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

Check if OpenViking endpoint is configured. No network calls.

#### def `get_config_schema(self)`

#### def `get_status_config(self, provider_config: dict) -> dict`

#### def `post_setup(self, hermes_home: str, config: dict) -> None`

Custom setup that can reuse OpenViking's shared CLI config.

#### def `initialize(self, session_id: str, **kwargs) -> None`

#### def `system_prompt_block(self) -> str`

#### def `prefetch(self, query: str, session_id: str = '') -> str`

Return recall context for this query/session.

#### def `queue_prefetch(self, query: str, session_id: str = '') -> None`

OpenViking recall is current-query only; post-turn warming is unused.

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '', messages: Optional[List[Dict[str, Any]]] = None) -> None`

Record the conversation turn in OpenViking's session (non-blocking).

#### def `on_session_end(self, messages: List[Dict[str, Any]]) -> None`

Commit the session to trigger memory extraction.

OpenViking automatically extracts 6 categories of memories:
profile, preferences, entities, events, cases, and patterns.

#### def `on_session_switch(self, new_session_id: str, parent_session_id: str = '', reset: bool = False, **kwargs) -> None`

Commit the old session and rotate cached state to the new session_id.

Fires on /resume, /branch, /reset, /new, and context compression.
Without this hook, ``_session_id`` stays stuck at the value
``initialize()`` cached, so subsequent ``sync_turn()`` writes land in
the already-closed old session and ``on_session_end()`` tries to
commit it a second time. The new session never accumulates messages,
and memory extraction never fires for it. See hermes-agent#28296.

Flushes any in-flight sync under the old session_id, commits the old
session if it has pending turns (same extraction semantics as
``on_session_end``), then rotates ``_session_id`` and resets
``_turn_count``.

#### def `on_memory_write(self, action: str, target: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Mirror successful built-in memory additions to OpenViking.

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

#### def `handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str`

#### def `shutdown(self) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Register OpenViking as a memory provider plugin.


## plugins.memory.query_rewrite

### 模块文档

Rewrite the latest user message into a clean memory-retrieval query.

Provider-agnostic: any memory provider can pass ``rewrite_memory_query``
as its query rewriter. Model/timeout are configured under
``auxiliary.memory_query_rewrite`` in config.yaml.

### 顶层函数

#### def `rewrite_memory_query(user_message: str) -> str`

Return a retrieval-only question, or ``""`` to preserve old behavior.


## plugins.memory.retaindb.__init__

### 模块文档

RetainDB memory plugin — MemoryProvider interface.

Cross-session memory via RetainDB cloud API.

Features:
- Correct API routes for all operations
- Durable SQLite write-behind queue (crash-safe, async ingest)
- Semantic search + user profile retrieval
- Context query with deduplication overlay
- Dialectic synthesis (LLM-powered user understanding, prefetched each turn)
- Agent self-model (persona + instructions from SOUL.md, prefetched each turn)
- Shared file store tools (upload, list, read, ingest, delete)
- Explicit memory tools (profile, search, context, remember, forget)

Config (env vars or hermes config.yaml under retaindb:):
  RETAINDB_API_KEY     — API key (required)
  RETAINDB_BASE_URL    — API endpoint (default: https://api.retaindb.com)
  RETAINDB_PROJECT     — Project identifier (optional — defaults to "default")

### class RetainDBMemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 19（公开 12）

RetainDB cloud memory — durable queue, semantic search, dialectic synthesis, shared files.

#### def `__init__()`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

#### def `get_config_schema(self) -> List[Dict[str, Any]]`

#### def `initialize(self, session_id: str, **kwargs) -> None`

#### def `system_prompt_block(self) -> str`

#### def `queue_prefetch(self, query: str, session_id: str = '') -> None`

Fire context + dialectic + agent model prefetches in background.

#### def `prefetch(self, query: str, session_id: str = '') -> str`

Consume prefetched results and return them as a context block.

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '') -> None`

Queue turn for async ingest. Returns immediately.

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

#### def `handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str`

#### def `on_memory_write(self, action: str, target: str, content: str) -> None`

Mirror built-in memory writes to RetainDB.

#### def `shutdown(self) -> None`


### 顶层函数

#### def `register(ctx) -> None`

Register RetainDB as a memory provider plugin.


## plugins.memory.supermemory.__init__

### 模块文档

Supermemory memory plugin using the MemoryProvider interface.

Provides semantic long-term memory with profile recall, semantic search,
explicit memory tools, cleaned turn capture, and session-end conversation ingest.

### class SupermemoryMemoryProvider

> 继承: `MemoryProvider` ｜ 方法数: 23（公开 17）

#### def `__init__()`

#### property `name(self) -> str`

#### def `is_available(self) -> bool`

#### def `get_config_schema(self)`

#### def `save_config(self, values, hermes_home)`

#### def `get_status_config(self, provider_config: dict) -> dict`

#### def `post_setup(self, hermes_home: str, config: dict) -> None`

#### def `initialize(self, session_id: str, **kwargs) -> None`

#### def `on_turn_start(self, turn_number: int, message: str, **kwargs) -> None`

#### def `system_prompt_block(self) -> str`

#### def `prefetch(self, query: str, session_id: str = '') -> str`

#### def `sync_turn(self, user_content: str, assistant_content: str, session_id: str = '') -> None`

#### def `on_session_end(self, messages: List[Dict[str, Any]]) -> None`

#### def `on_session_switch(self, new_session_id: str, parent_session_id: str = '', reset: bool = False, **kwargs) -> None`

Flush any buffered turns from the old session as one document, then reset for the new session.

#### def `on_memory_write(self, action: str, target: str, content: str) -> None`

#### def `shutdown(self) -> None`

#### def `get_tool_schemas(self) -> List[Dict[str, Any]]`

#### def `handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str`


### 顶层函数

#### def `register(ctx)`


## plugins.model-providers.alibaba-coding-plan.__init__

### 模块文档

Alibaba Cloud Coding Plan provider profile.

Separate from the standard `alibaba` profile because it hits a different
endpoint (coding-intl.dashscope.aliyuncs.com) with a dedicated API key tier.

## plugins.model-providers.alibaba.__init__

### 模块文档

Alibaba Cloud DashScope provider profile.

## plugins.model-providers.anthropic.__init__

### 模块文档

Native Anthropic provider profile.

### class AnthropicProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

Native Anthropic — uses x-api-key header, not Bearer.

#### def `fetch_models(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None`

Anthropic uses x-api-key header and anthropic-version.


## plugins.model-providers.arcee.__init__

### 模块文档

Arcee AI provider profile.

## plugins.model-providers.azure-foundry.__init__

### 模块文档

Microsoft Foundry provider profile.

Azure Foundry exposes an OpenAI-compatible endpoint; users supply their own
base URL at setup since endpoints are per-resource.

## plugins.model-providers.bedrock.__init__

### 模块文档

AWS Bedrock provider profile.

### class BedrockProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

AWS Bedrock — no REST /v1/models endpoint; uses AWS SDK.

#### def `fetch_models(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None`

Bedrock model listing requires AWS SDK, not a REST call.


## plugins.model-providers.copilot-acp.__init__

### 模块文档

GitHub Copilot ACP provider profile.

copilot-acp uses an external ACP subprocess — NOT the standard
transport. api_mode="copilot_acp" is handled separately in run_agent.py.
The profile captures auth + endpoint metadata for registry migration.

### class CopilotACPProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

GitHub Copilot ACP — external process, no REST models endpoint.

#### def `fetch_models(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None`

Model listing is handled by the ACP subprocess.


## plugins.model-providers.copilot.__init__

### 模块文档

Copilot / GitHub Models provider profile.

Copilot uses per-model api_mode routing:
  - GPT-5+ / Codex models → codex_responses
  - Claude models → anthropic_messages
  - Everything else → chat_completions (this profile covers that subset)

Key quirks for the chat_completions subset:
  - Editor attribution headers (via copilot_default_headers())
  - GitHub Models reasoning extra_body (model-catalog gated)

### class CopilotProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

GitHub Copilot / GitHub Models — editor headers + reasoning.

#### def `build_api_kwargs_extras(self, model: str | None = None, reasoning_config: dict | None = None, supports_reasoning: bool = False, **ctx) -> tuple[dict[str, Any], dict[str, Any]]`


## plugins.model-providers.custom.__init__

### 模块文档

Custom / Ollama (local) provider profile.

Covers any endpoint registered as provider="custom", including local
Ollama instances and OpenAI-compatible reasoning endpoints (GLM-5.2 on
Volcengine ARK, vLLM, llama.cpp). Key quirks:
  - ollama_num_ctx → extra_body.options.num_ctx (local context window)
  - reasoning_config disabled → top-level reasoning_effort="none"
    (Ollama /v1/chat/completions ignores think=False — ollama#14820)
    + extra_body.think = False for /api/chat and proxies
  - reasoning_config enabled + effort → top-level reasoning_effort
    (the native OpenAI-compatible format GLM/ARK expect; unset omits it
    so the endpoint's server default applies)

### class CustomProfile

> 继承: `ProviderProfile` ｜ 方法数: 2（公开 2）

Custom/Ollama local provider — think=false and num_ctx support.

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, ollama_num_ctx: int | None = None, **ctx: Any) -> tuple[dict[str, Any], dict[str, Any]]`

#### def `fetch_models(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None`

Custom/Ollama: base_url is user-configured; fetch if set.


## plugins.model-providers.deepinfra.__init__

### 模块文档

DeepInfra provider profile.

DeepInfra is an OpenAI-compatible inference gateway that hosts 100+ open
models (Step, GLM, Kimi, DeepSeek, MiniMax, Nemotron, Mistral, Qwen, …) as
well as image-gen / TTS / STT / embedding endpoints. The chat surface is
wired in through this profile; non-chat surfaces are wired in through
their respective plugin subsystems (``plugins/image_gen/deepinfra`` and
the TTS/STT dispatchers in ``tools/``).

## plugins.model-providers.deepseek.__init__

### 模块文档

DeepSeek provider profile.

DeepSeek's V4 family (and the legacy ``deepseek-reasoner``) defaults to
thinking-mode ON when ``extra_body.thinking`` is unset.  The API then returns
``reasoning_content`` and starts enforcing the contract that subsequent turns
echo it back; combined with how Hermes replays history this lands on the
notorious HTTP 400 ``reasoning_content must be passed back`` error after the
first tool call (#15700, #17212, #17825).

This profile overrides :meth:`build_api_kwargs_extras` to mirror the Kimi /
Moonshot wire shape that DeepSeek's OpenAI-compat endpoint expects:

    {"reasoning_effort": "<low|medium|high|max>",
     "extra_body": {"thinking": {"type": "enabled" | "disabled"}}}

Non-thinking models (only ``deepseek-chat`` today, which is V3) are left as
no-ops so we don't perturb the V3 wire format.

### class DeepSeekProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

DeepSeek — extra_body.thinking + top-level reasoning_effort.

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, model: str | None = None, **context) -> tuple[dict[str, Any], dict[str, Any]]`


## plugins.model-providers.fireworks.__init__

### 模块文档

Fireworks AI provider profile.

Fireworks AI serves fast, production-grade inference for open and proprietary
models through an OpenAI-compatible chat-completions endpoint.

Address models directly by their catalog ID, e.g.
``accounts/fireworks/models/kimi-k2p6`` or ``accounts/fireworks/models/glm-5p2``.
Model IDs here track the canonical Fireworks catalog (fw-ai/fireconnect
``setup-cli``).

## plugins.model-providers.gemini.__init__

### 模块文档

Google Gemini provider profiles.

gemini:            Google AI Studio (API key) — uses GeminiNativeClient

Reports api_mode="chat_completions" but uses a custom native client
that bypasses the standard OpenAI transport. The profile captures auth
and endpoint metadata for auth.py / runtime_provider.py migration, and
carries the thinking_config translation hook so the transport's profile
path produces the same extra_body shape the legacy flag path did.

### class GeminiProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

Gemini — translate reasoning_config to thinking_config in extra_body.

#### def `build_extra_body(self, session_id: str | None = None, **context: Any) -> dict[str, Any]`

Emit extra_body.thinking_config (native) or extra_body.extra_body.google.thinking_config
(OpenAI-compat /openai subpath), mirroring the legacy path's behavior.


## plugins.model-providers.gmi.__init__

### 模块文档

GMI Cloud provider profile.

## plugins.model-providers.huggingface.__init__

### 模块文档

Hugging Face provider profile.

## plugins.model-providers.kilocode.__init__

### 模块文档

Kilo Code provider profile.

## plugins.model-providers.kimi-coding.__init__

### 模块文档

Kimi / Moonshot provider profiles.

Kimi has dual endpoints:
  - sk-kimi-* keys → api.kimi.com/coding (Anthropic Messages API)
  - legacy keys → api.moonshot.ai/v1 (OpenAI chat completions)

This module covers the chat_completions path (/v1 endpoint).

### class KimiProfile

> 继承: `ProviderProfile` ｜ 方法数: 2（公开 2）

Kimi/Moonshot — temperature omitted, thinking xor reasoning_effort.

#### def `fetch_models(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None`

Use Kimi Code's OpenAI-compatible surface for model discovery.

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, **context) -> tuple[dict[str, Any], dict[str, Any]]`

Kimi reasoning controls.

Moonshot's wire shape treats ``extra_body.thinking`` (a binary toggle)
and a top-level ``reasoning_effort`` as mutually exclusive — sending
both is at best redundant and risks "cannot specify both 'thinking' and
'reasoning_effort'" (HTTP 400). This mirrors the kimi-k2 handling on the
opencode-go relay: send effort when one is requested, otherwise fall
back to ``extra_body.thinking`` — never both.


## plugins.model-providers.minimax.__init__

### 模块文档

MiniMax provider profiles (international + China).

The default API-key routes use anthropic_messages because their base URLs end
with /anthropic. Users can opt MiniMax-M3 into the OpenAI-compatible endpoint
with base_url=https://api.minimax.io/v1; that route needs MiniMax-specific
reasoning controls in extra_body.

### class MiniMaxProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

MiniMax — M3 OpenAI-compatible reasoning controls.

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, model: str | None = None, base_url: str | None = None, **context: Any) -> tuple[dict[str, Any], dict[str, Any]]`

Emit M3 reasoning controls for api.minimax.io/v1.

MiniMax-M3's OpenAI-compatible endpoint keeps thinking inline unless
``reasoning_split`` is sent, so always request the split format on that
route. ``thinking`` controls the M3 mode; Hermes' effort levels are not
a MiniMax depth knob here, so they only select adaptive vs disabled.


## plugins.model-providers.nous.__init__

### 模块文档

Nous Portal provider profile.

### class NousProfile

> 继承: `ProviderProfile` ｜ 方法数: 2（公开 2）

Nous Portal — product tags, reasoning with Nous-specific omission.

#### def `build_extra_body(self, session_id: str | None = None, **context) -> dict[str, Any]`

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, supports_reasoning: bool = False, **context) -> tuple[dict[str, Any], dict[str, Any]]`

Nous: passes full reasoning_config, but OMITS when disabled.


## plugins.model-providers.novita.__init__

### 模块文档

NovitaAI provider profile.

## plugins.model-providers.nvidia.__init__

### 模块文档

NVIDIA NIM provider profile.

## plugins.model-providers.ollama-cloud.__init__

### 模块文档

Ollama Cloud provider profile.

Ollama Cloud's OpenAI-compatible ``/v1/chat/completions`` endpoint
supports top-level ``reasoning_effort`` with values ``none``, ``low``,
``medium``, ``high``, and ``max`` (the last being undocumented but
empirically confirmed for DeepSeek V4 — ``max`` produces ~2.5× more
thinking tokens than ``high``).

This profile maps Hermes's ``xhigh`` → ``max`` to unlock DeepSeek V4's
"Max thinking" tier through Ollama Cloud.  ``low`` / ``medium`` / ``high``
pass through unchanged.

When reasoning is explicitly disabled (``enabled: false`` or
``effort: "none"``), ``reasoning_effort`` is omitted entirely so the
model runs in non-thinking mode.

### class OllamaCloudProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

Ollama Cloud — maps xhigh→max via top-level reasoning_effort.

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, supports_reasoning: bool = False, **ctx: Any) -> tuple[dict[str, Any], dict[str, Any]]`

Emit top-level ``reasoning_effort`` for Ollama Cloud thinking models.

Gated on ``supports_reasoning``, which the transport resolves from the
model's native ``/api/show`` ``capabilities`` (``thinking``). Models
without the thinking capability (e.g. ``gemma3``, ``qwen3-coder``) get
no ``reasoning_effort`` at all — emitting it there is a no-op the API
ignores, and gating avoids sending a meaningless field.


## plugins.model-providers.openai-codex.__init__

### 模块文档

OpenAI Codex (Responses API) provider profile.

## plugins.model-providers.opencode-zen.__init__

### 模块文档

OpenCode provider profiles (Zen + Go).

Both use per-model api_mode routing:
  - OpenCode Zen: Claude → anthropic_messages, GPT-5/Codex → codex_responses,
    everything else → chat_completions (this profile)
  - OpenCode Go: MiniMax → anthropic_messages, GLM/Kimi → chat_completions
    (this profile)

### class OpenCodeGoProfile

> 继承: `ProviderProfile` ｜ 方法数: 2（公开 2）

OpenCode Go - model-specific reasoning controls.

#### def `get_max_tokens(self, model: str | None) -> int | None`

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, model: str | None = None, **context) -> tuple[dict[str, Any], dict[str, Any]]`


## plugins.model-providers.openrouter.__init__

### 模块文档

OpenRouter provider profile.

### class OpenRouterProfile

> 继承: `ProviderProfile` ｜ 方法数: 3（公开 3）

OpenRouter aggregator — provider preferences, reasoning config passthrough.

#### def `fetch_models(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None`

Fetch from public OpenRouter catalog — no auth required.

Note: Tool-call capability filtering is applied by hermes_cli/models.py
via fetch_openrouter_models() → _openrouter_model_supports_tools(), not
here. The picker early-returns via the dedicated openrouter path before
reaching this method, so filtering here would be unreachable.

#### def `build_extra_body(self, session_id: str | None = None, **context: Any) -> dict[str, Any]`

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, supports_reasoning: bool = False, model: str | None = None, session_id: str | None = None, **context: Any) -> tuple[dict[str, Any], dict[str, Any]]`

OpenRouter passes the full reasoning_config dict as extra_body.reasoning.

For xAI Grok models routed through OpenRouter, attach the
``x-grok-conv-id`` header so that xAI's prompt cache stays pinned to
the same backend server across turns.


## plugins.model-providers.qwen-oauth.__init__

### 模块文档

Qwen Portal provider profile.

### class QwenProfile

> 继承: `ProviderProfile` ｜ 方法数: 4（公开 3）

Qwen Portal — message normalization, vl_high_resolution, metadata top-level.

#### def `prepare_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]`

Normalize content to list-of-dicts format.

Inject cache_control on system message.

Matches the behavior of run_agent.py:_qwen_prepare_chat_messages().

#### def `build_extra_body(self, session_id: str | None = None, **context) -> dict[str, Any]`

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, qwen_session_metadata: dict | None = None, **context) -> tuple[dict[str, Any], dict[str, Any]]`

Qwen metadata goes to top-level api_kwargs, not extra_body.


## plugins.model-providers.stepfun.__init__

### 模块文档

StepFun provider profile.

## plugins.model-providers.upstage.__init__

### 模块文档

Upstage Solar provider profile.

### class UpstageProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

Upstage Solar — top-level ``reasoning_effort`` control.

Solar Pro/Open expose reasoning through a top-level ``reasoning_effort``
field (``minimal`` | ``low`` | ``medium`` | ``high``), mirroring OpenAI's
shape. Unlike DeepSeek/Kimi it does NOT require echoing ``reasoning_content``
back on later turns, so only the request field needs wiring. We emit at most
``low`` | ``medium`` | ``high`` — the explicit values both Solar Pro 2 and
Pro 3 accept.

Default-on: Solar's own server default is ``minimal`` (off), but for an
agentic workload we default reasoning ON (``_DEFAULT_REASONING_EFFORT``)
when the user hasn't picked an effort. The user can still set any level or
turn it off with ``/reasoning none``.

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, model: str | None = None, **context) -> tuple[dict[str, Any], dict[str, Any]]`


## plugins.model-providers.vertex.__init__

### 模块文档

Google Vertex AI provider profile.

vertex: Gemini models via Google Cloud's OpenAI-compatible endpoint.

Auth is OAuth2 — short-lived access tokens minted from a service-account JSON
or Application Default Credentials (ADC), NOT a static API key. Token
resolution and refresh live in ``agent/vertex_adapter.py``; runtime_provider.py
calls it to obtain a fresh ``(token, base_url)`` pair, then hands the token to
the standard OpenAI client as ``api_key``. Because the wire format is the
OpenAI-compatible chat/completions surface, no message translation is needed —
the only Gemini-specific concern is the ``thinking_config`` reasoning hook,
which is emitted here exactly as the ``gemini`` provider does for its
OpenAI-compat subpath (``extra_body.google.thinking_config``).

``auth_type="vertex"`` marks this as an OAuth-token provider (resolved
specially, like bedrock's ``aws_sdk``) so it is never treated as an
api_key provider that would mistake a credentials-file path for a key.

### class VertexProfile

> 继承: `ProviderProfile` ｜ 方法数: 2（公开 2）

Vertex AI — reuse Gemini's thinking_config translation for extra_body.

#### def `build_extra_body(self, session_id: str | None = None, **context: Any) -> dict[str, Any]`

Emit ``extra_body.google.thinking_config`` for the OpenAI-compat
Vertex surface, mirroring the ``gemini`` provider's behavior.

#### def `fetch_models(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None`

Vertex's OpenAI-compat endpoint has no ``/models`` listing route;
model discovery is not available. The setup wizard ships a curated list.


## plugins.model-providers.xai.__init__

### 模块文档

xAI (Grok) provider profile.

## plugins.model-providers.xiaomi.__init__

### 模块文档

Xiaomi MiMo provider profile.

## plugins.model-providers.zai.__init__

### 模块文档

ZAI / GLM provider profile.

Z.AI's GLM-4.5-and-later chat models default to thinking-mode ON when the
request omits ``thinking``.  Hermes' ``reasoning_config = {"enabled": False}``
was previously a silent no-op on this route — the base profile emits nothing,
so users who turned thinking off (desktop toggle, ``/reasoning none``,
``reasoning_effort: none``/``false`` in config.yaml) kept burning thinking
tokens on every turn.

:meth:`ZaiProfile.build_api_kwargs_extras` translates the Hermes reasoning
config into the wire shape Z.AI's OpenAI-compat endpoint expects:

    {"extra_body": {"thinking": {"type": "enabled" | "disabled"}}}

When no reasoning preference is set (``reasoning_config is None``) the field
is omitted so the server default applies, matching prior behavior.  GLM
models before 4.5 (e.g. ``glm-4-9b``) don't accept ``thinking`` and are left
untouched.

GLM-5.2 additionally exposes a native ``reasoning_effort`` knob with exactly
two enabled levels — ``high`` and ``max`` — on the OpenAI-compatible endpoint
(per Z.AI / BigModel docs).  Hermes' richer effort scale is collapsed onto
those two so the user's effort preference actually reaches the model instead
of being silently dropped.

### class ZaiProfile

> 继承: `ProviderProfile` ｜ 方法数: 1（公开 1）

Z.AI / GLM — extra_body.thinking on/off + GLM-5.2 reasoning_effort.

#### def `build_api_kwargs_extras(self, reasoning_config: dict | None = None, model: str | None = None, **context) -> tuple[dict[str, Any], dict[str, Any]]`


## plugins.observability.langfuse.__init__

### 模块文档

langfuse — Hermes plugin for Langfuse observability.

Traces Hermes conversations, LLM calls, and tool usage to Langfuse.

Activation is handled by the Hermes plugin system — standalone plugins only
load when listed in ``plugins.enabled`` (via ``hermes plugins enable
observability/langfuse`` or ``hermes tools → Langfuse Observability``). At
runtime the plugin also requires the ``langfuse`` SDK and credentials; if
either is missing the hooks are inert.

Required env vars (set via ``hermes tools`` or ~/.hermes/.env):
  HERMES_LANGFUSE_PUBLIC_KEY  - Langfuse project public key (pk-lf-...)
  HERMES_LANGFUSE_SECRET_KEY  - Langfuse project secret key (sk-lf-...)
  HERMES_LANGFUSE_BASE_URL    - Langfuse server URL (default: https://cloud.langfuse.com)

Optional env vars:
  HERMES_LANGFUSE_ENV         - environment tag (e.g. "production", "local")
  HERMES_LANGFUSE_RELEASE     - release/version tag
  HERMES_LANGFUSE_SAMPLE_RATE - sampling rate 0.0–1.0 (default: 1.0)
  HERMES_LANGFUSE_MAX_CHARS   - max chars per field (default: 12000)
  HERMES_LANGFUSE_DEBUG       - set to "true" for verbose logging

### class TraceState

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `on_pre_llm_call(task_id: str = '', session_id: str = '', platform: str = '', model: str = '', provider: str = '', base_url: str = '', api_mode: str = '', api_call_count: int = 0, messages: Any = None, turn_type: str = 'user', conversation_history: Any = None, user_message: Any = None, turn_id: str = '', api_request_id: str = '', **_: Any) -> None`

#### def `on_pre_llm_request(task_id: str = '', session_id: str = '', platform: str = '', model: str = '', provider: str = '', base_url: str = '', api_mode: str = '', api_call_count: int = 0, request_messages: Any = None, messages: Any = None, turn_type: str = 'user', message_count: int = 0, tool_count: int = 0, approx_input_tokens: int = 0, request_char_count: int = 0, max_tokens: Any = None, conversation_history: Any = None, user_message: Any = None, turn_id: str = '', api_request_id: str = '', **_: Any) -> None`

#### def `on_post_llm_call(task_id: str = '', session_id: str = '', provider: str = '', base_url: str = '', api_mode: str = '', model: str = '', api_call_count: int = 0, assistant_message: Any = None, response: Any = None, api_duration: float = 0.0, finish_reason: str = '', usage: Any = None, assistant_content_chars: int = 0, assistant_tool_call_count: int = 0, assistant_response: Any = None, turn_id: str = '', api_request_id: str = '', **_: Any) -> None`

#### def `on_pre_tool_call(tool_name: str = '', args: Any = None, task_id: str = '', session_id: str = '', tool_call_id: str = '', turn_id: str = '', api_request_id: str = '', **_: Any) -> None`

#### def `on_post_tool_call(tool_name: str = '', args: Any = None, result: Any = None, task_id: str = '', session_id: str = '', tool_call_id: str = '', turn_id: str = '', api_request_id: str = '', **_: Any) -> None`

#### def `register(ctx) -> None`


## plugins.observability.nemo_relay.__init__

### 模块文档

nemo_relay — optional Hermes plugin for NeMo Relay observability.

### 顶层函数

#### def `register(ctx) -> None`

#### def `on_session_start(**kwargs: Any) -> None`

#### def `on_session_end(**kwargs: Any) -> None`

#### def `on_session_finalize(**kwargs: Any) -> None`

#### def `on_session_reset(**kwargs: Any) -> None`

#### def `on_pre_llm_call(**kwargs: Any) -> None`

#### def `on_post_llm_call(**kwargs: Any) -> None`

#### def `on_pre_api_request(**kwargs: Any) -> None`

#### def `on_post_api_request(**kwargs: Any) -> None`

#### def `on_api_request_error(**kwargs: Any) -> None`

#### def `on_pre_tool_call(**kwargs: Any) -> None`

#### def `on_post_tool_call(**kwargs: Any) -> None`

#### def `on_pre_approval_request(**kwargs: Any) -> None`

#### def `on_post_approval_response(**kwargs: Any) -> None`

#### def `on_subagent_start(**kwargs: Any) -> None`

#### def `on_subagent_stop(**kwargs: Any) -> None`

#### def `on_llm_execution_middleware(**kwargs: Any) -> Any`

#### def `on_tool_execution_middleware(**kwargs: Any) -> Any`

#### def `reset_for_tests() -> None`


## plugins.platforms.dingtalk.__init__


## plugins.platforms.dingtalk.adapter

### 模块文档

DingTalk platform adapter using Stream Mode.

Uses dingtalk-stream SDK (>=0.20) for real-time message reception without webhooks.
Responses are sent via DingTalk's session webhook (markdown format).
Supports: text, images, audio, video, rich text, files, and group @mentions.

Requires:
    pip install "dingtalk-stream>=0.20" httpx
    DINGTALK_CLIENT_ID and DINGTALK_CLIENT_SECRET env vars

Configuration in config.yaml:
    platforms:
      dingtalk:
        enabled: true
        # Optional group-chat gating (mirrors Slack/Telegram/Discord):
        require_mention: true            # or DINGTALK_REQUIRE_MENTION env var
        # free_response_chats:           # conversations that skip require_mention
        #   - cidABC==
        # mention_patterns:              # regex wake-words (e.g. Chinese bot names)
        #   - "^小马"
        # allowed_users:                 # staff_id or sender_id list; "*" = any
        #   - "manager1234"
        extra:
          client_id: "your-app-key"      # or DINGTALK_CLIENT_ID env var
          client_secret: "your-secret"   # or DINGTALK_CLIENT_SECRET env var

### class DingTalkAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 36（公开 11）

DingTalk chatbot adapter using Stream Mode.

The dingtalk-stream SDK maintains a long-lived WebSocket connection.
Incoming messages arrive via a ChatbotHandler callback. Replies are
sent via the incoming message's session_webhook URL using httpx.

Features:
- Text messages (plain + rich text)
- Images, audio, video, files (via download codes)
- Group chat @mention detection
- Session webhook caching with expiry tracking
- Markdown formatted replies

#### property `SUPPORTS_MESSAGE_EDITING(self) -> bool`

Edits only meaningful when AI Cards are configured.

The gateway gates streaming cursor + edit behaviour on this flag,
so we must reflect the actual adapter capability at runtime.

#### property `REQUIRES_EDIT_FINALIZE(self) -> bool`

AI Card lifecycle requires an explicit ``finalize=True`` edit
to close the streaming indicator, even when the final content is
identical to the last streamed update.  Enabled only when cards
are configured — webhook-only DingTalk doesn't need it.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to DingTalk via Stream Mode.

#### async def `disconnect(self) -> None`

Disconnect from DingTalk.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a markdown reply via DingTalk session webhook.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

DingTalk does not support typing indicators.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an image via DingTalk markdown.

DingTalk's session webhook only supports text/markdown payloads, not
native image/file attachments. For remote image URLs, render the image
inline with markdown so the user still sees the image. Local files need
OpenAPI media upload and are handled separately.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

DingTalk webhook replies cannot send local image files directly.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

DingTalk webhook replies cannot send local file attachments directly.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return basic info about a DingTalk conversation.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False) -> SendResult`

Edit an AI Card by streaming updated content.

``message_id`` is the out_track_id returned by the initial ``send()``
call that created this card.  Callers (stream_consumer, tool
progress) track their own ids independently so two parallel flows
on the same chat_id don't interfere.


### 顶层函数

#### def `check_dingtalk_requirements() -> bool`

Check if DingTalk dependencies are available and configured.

Lazy-installs dingtalk-stream via ``tools.lazy_deps.ensure("platform.dingtalk")``
on first call if not present.

#### def `interactive_setup() -> None`

Configure DingTalk — QR scan (recommended) or manual credential entry.

Replaces hermes_cli/setup.py-era _setup_dingtalk + the static
_PLATFORMS["dingtalk"] dict in hermes_cli/gateway.py. CLI helpers are
lazy-imported so the plugin's module-load surface stays minimal.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.discord.__init__


## plugins.platforms.discord.adapter

### class VoiceReceiver

> 继承: `object` ｜ 方法数: 11（公开 7）

Captures and decodes voice audio from a Discord voice channel.

Attaches to a VoiceClient's socket listener, decrypts RTP packets
(NaCl transport + DAVE E2EE), decodes Opus to PCM, and buffers
per-user audio.  A polling loop detects silence and delivers
completed utterances via a callback.

#### def `__init__(voice_client, allowed_user_ids: set = None)`

#### def `start(self)`

Start listening for voice packets.

#### def `stop(self)`

Stop listening and clean up.

#### def `pause(self)`

#### def `resume(self)`

#### def `map_ssrc(self, ssrc: int, user_id: int)`

#### def `check_silence(self) -> list`

Return list of (user_id, pcm_bytes) for completed utterances.

#### staticmethod `pcm_to_wav(pcm_data: bytes, output_path: str, src_rate: int = 48000, src_channels: int = 2)`

Convert raw PCM to 16kHz mono WAV via ffmpeg.


### class DiscordAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 170（公开 37）

Discord bot adapter.

Handles:
- Receiving messages from servers and DMs
- Sending responses with Discord markdown
- Thread support
- Native slash commands (/ask, /reset, /status, /stop)
- Button-based exec approvals
- Auto-threading for long conversations
- Reaction-based feedback

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to Discord and start receiving events.

#### async def `cancel_background_tasks(self) -> None`

Cancel background tasks, but first flush any pending text-batch sends.

The base-class implementation only cancels tasks in self._background_tasks.
Discord keeps its own _pending_text_batch_tasks dict for the message-merge
logic, and those tasks are NOT in _background_tasks. On shutdown/restart
this caused a race where in-flight response deliveries were cancelled before
Discord had a chance to actually send them, resulting in silent dropped
messages visible to the user as tool-log-only replies with no text.

Fix: await all pending text-batch tasks before delegating to the base
cancel. The flush deadline is clamped below the gateway's per-adapter
disconnect budget (``HERMES_GATEWAY_ADAPTER_DISCONNECT_TIMEOUT``, default
5s) so the gateway's outer ``wait_for`` can't hard-cancel us mid-flush —
we cancel our own stragglers cleanly inside the budget instead.

#### async def `disconnect(self) -> None`

Disconnect from Discord.

#### async def `on_processing_start(self, event: MessageEvent) -> None`

Add an in-progress reaction and record durable handling state.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Swap the in-progress reaction for final reaction and durable state.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a message to a Discord channel or thread.

When metadata contains a thread_id, the message is sent to that
thread instead of the parent channel identified by chat_id.

Forum channels (type 15) reject direct messages — a thread post is
created automatically.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Edit a previously sent Discord message.

Discord caps single-message text at 2,000 chars.  Edits that grow
past this limit must NOT be silently truncated (the stream consumer
would believe the full reply was delivered and stop) and must NOT
return failure (the consumer would re-send and create a duplicate).

Mid-stream (``finalize=False``) we keep editing the original message
with a truncated preview — splitting mid-stream would move the edit
target to a continuation and the next accumulated-token tick would
re-split, looping forever (the Telegram #48648 lesson).  The complete
text is delivered when ``finalize=True`` via ``_edit_overflow_split``.

#### async def `send_multiple_images(self, chat_id: str, images: List[Tuple[str, str]], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send a batch of images as a single Discord message with multiple attachments.

Discord permits up to 10 file attachments per message. Batches are
chunked accordingly. URL images are downloaded into memory and
uploaded as inline attachments (same pattern as ``send_image`` so
they render inline, not as bare links). Local files are opened
directly. On per-chunk failure the remaining images in that chunk
fall back to the base per-image loop.

#### async def `play_tts(self, chat_id: str, audio_path: str, **kwargs) -> SendResult`

Play auto-TTS audio.

When the bot is in a voice channel for this chat's guild, play
directly in the VC instead of sending as a file attachment.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send audio as a Discord file attachment.

#### async def `play_ack_in_voice(self, guild_id: int, phrase: Optional[str] = None) -> bool`

Speak a short acknowledgement over the ambient bed.

Called from the gateway's tool-progress hook on the first tool call of
a turn, so the user hears "let me look into that" before the bot goes
quiet to work.  No-op unless the mixer is installed and acks enabled.

#### def `voice_mixer_active(self, guild_id: int) -> bool`

True when a continuous mixer is installed for this guild.

#### async def `join_voice_channel(self, channel) -> bool`

Join a Discord voice channel. Returns True on success.

#### async def `leave_voice_channel(self, guild_id: int) -> None`

Disconnect from the voice channel in a guild.

#### async def `play_in_voice_channel(self, guild_id: int, audio_path: str) -> bool`

Play an audio file in the connected voice channel.

When the continuous mixer is installed for this guild, the clip is
decoded to PCM and layered over the ambient bed (ducking it) so the
reply can overlap the idle "thinking" loop seamlessly.  Otherwise we
fall back to the legacy one-shot FFmpegPCMAudio path.

#### async def `get_user_voice_channel(self, guild_id: int, user_id: str)`

Return the voice channel the user is currently in, or None.

#### def `is_in_voice_channel(self, guild_id: int) -> bool`

Check if the bot is connected to a voice channel in this guild.

#### def `get_voice_channel_info(self, guild_id: int) -> Optional[Dict[str, Any]]`

Return voice channel awareness info for the given guild.

Returns None if the bot is not in a voice channel.  Otherwise
returns a dict with channel name, member list, count, and
currently-speaking user IDs (from SSRC mapping).

#### def `get_voice_channel_context(self, guild_id: int) -> str`

Return a human-readable voice channel context string.

Suitable for injection into the system/ephemeral prompt so the
agent is always aware of voice channel state.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a local image file natively as a Discord file attachment.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an image natively as a Discord file attachment.

#### async def `send_animation(self, chat_id: str, animation_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an animated GIF natively as a Discord file attachment.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a local video file natively as a Discord attachment.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an arbitrary file natively as a Discord attachment.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Start a persistent typing indicator for a channel.

Discord's TYPING_START gateway event is unreliable in DMs for bots.
Instead, start a background loop that hits the typing endpoint every
12 seconds (typing indicator lasts ~10s).  The loop is cancelled when
stop_typing() is called (after the response is sent).

Rate-limit handling: if a 429 is encountered, the loop logs a
warning, sleeps for the ``retry_after`` duration (or a sensible
default), and continues — it does NOT die on a single rate-limit
hit.  Only CancelledError (from stop_typing) stops the loop.

#### async def `stop_typing(self, chat_id: str) -> None`

Stop the persistent typing indicator for a channel.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Get information about a Discord channel.

#### def `format_message(self, content: str) -> str`

Format message for Discord.

Converts GFM markdown tables to bullet-list groups since Discord
does not render pipe tables natively.

#### def `refresh_skill_group(self) -> tuple[int, int]`

Rescan skills and update the live ``/skill`` autocomplete state.

Invoked by :meth:`gateway.run.GatewayOrchestrator._handle_reload_skills_command`
after :func:`agent.skill_commands.reload_skills` has refreshed
the in-process skill-command registry. Without this call, the
``/skill`` autocomplete dropdown keeps showing the list captured
at process start — new skills stay invisible and deleted skills
return an "Unknown skill" error when clicked.

Because autocomplete options are fetched dynamically by Discord,
we only need to mutate the entries/lookup attributes read by the
callbacks — no ``tree.sync()`` is required.

Returns ``(new_count, hidden_count)``.

#### async def `rename_thread(self, thread_id: str, name: str, only_if_current_name: Optional[str] = None) -> bool`

Best-effort Discord thread rename.

``only_if_current_name`` prevents overwriting human-renamed or
pre-existing threads.  This is intentionally a no-op on mismatch.

#### async def `create_handoff_thread(self, parent_chat_id: str, name: str) -> Optional[str]`

Create a Discord thread under a text channel for a handoff.

Falls back to a seed-message + ``message.create_thread`` path if
``parent.create_thread`` is rejected (some channel types or
permission setups). Returns the new thread id as a string, or
``None`` on failure or when the parent isn't a text channel
(DMs, voice channels, threads themselves can't host threads).

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[dict] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Send a button-based exec approval prompt for a dangerous command.

The buttons call ``resolve_gateway_approval()`` to unblock the waiting
agent thread — this replaces the text-based ``/approve`` flow on Discord.

#### async def `send_slash_confirm(self, chat_id: str, title: str, message: str, session_key: str, confirm_id: str, metadata: Optional[dict] = None) -> SendResult`

Send a three-button slash-command confirmation prompt.

#### async def `send_clarify(self, chat_id: str, question: str, choices: Optional[list], clarify_id: str, session_key: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Render a clarify prompt with one Discord button per choice.

Multi-choice mode (``choices`` non-empty): renders a button per option
plus a final "✏️ Other (type answer)" button. Picking "Other" flips
the clarify entry into text-capture mode so the next user message in
the session becomes the response. Numeric clicks resolve immediately
via ``resolve_gateway_clarify(clarify_id, choice_text)``.

Open-ended mode (``choices`` empty/None): renders the question as
plain embed text — no buttons. The gateway's text-intercept captures
the next message in this session and resolves the clarify.

Choice normalisation: ``choices`` may contain bare strings OR dicts
(LLMs sometimes emit ``[{"description": "..."}]`` instead of bare
strings, which would otherwise render as raw Python repr on the
button label). Dict choices are unwrapped against the canonical
LLM tool-call keys ``label``, ``description``, ``text``, ``title``
in that order. Dicts with none of those keys are dropped.

#### async def `send_update_prompt(self, chat_id: str, prompt: str, default: str = '', session_key: str = '', metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an interactive button-based update prompt (Yes / No).

Used by the gateway ``/update`` watcher when ``hermes update --gateway``
needs user input (stash restore, config migration).

#### async def `send_model_picker(self, chat_id: str, providers: list, current_model: str, current_provider: str, session_key: str, on_model_selected, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an interactive select-menu model picker.

Two-step drill-down: provider dropdown → model dropdown.
Uses Discord embeds + Select menus via ``ModelPickerView``.

#### async def `send_choice_picker(self, chat_id: str, title: str, choices: list, session_key: str, on_choice_selected, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a flat select-menu choice picker (one selection → one value).

Generic single-level companion to ``send_model_picker`` used by
`/reasoning`, `/fast`, and any future finite-choice command. Each
choice dict: ``{"value": str, "label": str, "is_current": bool}``.


### 顶层函数

#### def `check_discord_requirements() -> bool`

Check if Discord dependencies are available.

Lazy-installs discord.py via ``tools.lazy_deps.ensure("platform.discord")``
on first call if not present. After successful install, re-binds module
globals so ``DISCORD_AVAILABLE`` becomes True.

#### def `interactive_setup() -> None`

Guide the user through Discord bot setup.

Mirrors Teams' ``interactive_setup`` shape: lazy-imports CLI helpers so
the plugin's import surface stays small, prompts for the bot token,
captures an allowlist, and offers to set a home channel.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.discord.recovery

### 模块文档

Durable state for Discord reconnect message recovery.

### class DiscordRecoveryStore

> 继承: `object` ｜ 方法数: 4（公开 2）

Small profile-scoped SQLite ledger for completed Discord messages.

#### def `__init__(hermes_home: Path | None = None) -> None`

#### def `path(self) -> Path`

#### def `call(self, fn: Callable[[sqlite3.Connection], Any], default: Any = None) -> Any`


## plugins.platforms.discord.voice_mixer

### class MixerChild

> 继承: `object` ｜ 方法数: 3（公开 2）

A single audio stream feeding into :class:`VoiceMixer`.

Wraps raw 48 kHz / stereo / s16le PCM bytes.  ``read_frame`` hands back one
20 ms frame at a time, optionally looping, with a per-child gain applied.

#### def `__init__(name: str, pcm: bytes, loop: bool = False, gain: float = 1.0, is_speech: bool = False, fade_in_ms: int = 0)`

#### property `finished(self) -> bool`

#### def `read_frame(self) -> Optional[np.ndarray]`

Return the next 20 ms frame as an int16 ndarray, or None if done.


### class VoiceMixer

> 继承: `object` ｜ 方法数: 10（公开 7）

A continuous ``discord.AudioSource`` that mixes N child streams.

Use :meth:`set_ambient` to install/replace the looping idle bed and
:meth:`play_speech` to layer a one-shot clip over it (ducking the ambient
while it plays).  Both are safe to call from the asyncio loop thread while
discord.py drains :meth:`read` from its sender thread.

#### def `is_opus(self) -> bool`

#### def `__init__(ambient_gain: float = 0.18, duck_gain: float = 0.06, speech_gain: float = 1.0, duck_release_ms: int = 400)`

#### def `set_ambient(self, pcm: Optional[bytes], gain: Optional[float] = None) -> None`

Install (or clear, with ``pcm=None``) the looping ambient bed.

#### def `play_speech(self, pcm: bytes, gain: Optional[float] = None, fade_in_ms: int = 40) -> None`

Layer a one-shot speech clip over the ambient bed (ducks ambient).

#### property `speech_active(self) -> bool`

#### def `stop_speech(self) -> None`

Drop any in-flight speech immediately and release the duck.

#### def `read(self) -> bytes`

Return one 20 ms mixed PCM frame (always FRAME_SIZE bytes).

Returning a non-empty frame keeps discord.py's player alive; we never
return b"" because that would stop the single underlying stream and we
want the mixer to run continuously for the lifetime of the connection.

#### def `cleanup(self) -> None`


### 顶层函数

#### def `decode_to_pcm(path: str, timeout: float = 30.0) -> Optional[bytes]`

Decode any audio file to 48 kHz / stereo / s16le PCM via ffmpeg.

Returns the raw PCM bytes, or None on failure.  ffmpeg is already a hard
requirement of the voice path (see ``VoiceReceiver.pcm_to_wav``).

#### def `synth_ambient_pcm(seconds: float = 4.0) -> bytes`

Synthesise a subtle looping ambient bed (no asset file required).

A soft, slowly-pulsing low pad: two detuned sine partials with a gentle
tremolo, plus a touch of filtered noise.  Designed to loop seamlessly
(whole number of cycles, zero-crossing endpoints) and sit quietly under
speech.  Mono content duplicated to stereo.


## plugins.platforms.email.__init__


## plugins.platforms.email.adapter

### 模块文档

Email platform adapter for the Hermes gateway.

Allows users to interact with Hermes by sending emails.
Uses IMAP to receive and SMTP to send messages.

Environment variables:
    EMAIL_IMAP_HOST     — IMAP server host (e.g., imap.gmail.com)
    EMAIL_IMAP_PORT     — IMAP server port (default: 993)
    EMAIL_SMTP_HOST     — SMTP server host (e.g., smtp.gmail.com)
    EMAIL_SMTP_PORT     — SMTP server port (default: 587)
    EMAIL_ADDRESS       — Email address for the agent
    EMAIL_PASSWORD      — Email password or app-specific password
    EMAIL_POLL_INTERVAL — Seconds between mailbox checks (default: 15)
    EMAIL_ALLOWED_USERS — Comma-separated list of allowed sender addresses

### class EmailAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 21（公开 8）

Email gateway adapter using IMAP (receive) and SMTP (send).

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to the IMAP server and start polling for new messages.

#### async def `disconnect(self) -> None`

Stop polling and disconnect.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an email reply to the given address.

#### async def `send_typing(self, chat_id: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Email has no typing indicator — no-op.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an image URL as part of an email body.

``metadata`` is accepted to honor the base-class contract; the
email body send doesn't use it.

#### async def `send_multiple_images(self, chat_id: str, images: List[Tuple[str, str]], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send a batch of images as a single email with multiple MIME attachments.

Local files are attached directly. URL images have their URL
appended to the body (email adapter does not download remote
images). No hard cap — email clients handle dozens of
attachments fine, subject to SMTP message size limits.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a file as an email attachment.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return basic info about the email chat.


### 顶层函数

#### def `check_email_requirements() -> bool`

Check if email platform settings are available and non-blank.

Treats blank/whitespace-only values as missing so an abandoned setup that
left empty ``EMAIL_*`` keys in ``.env`` does not enable the platform (#40715).

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.feishu.__init__


## plugins.platforms.feishu.adapter

### 模块文档

Feishu/Lark platform adapter.

Supports:
- WebSocket long connection and Webhook transport
- Direct-message and group @mention-gated text receive/send
- Inbound image/file/audio/media caching
- Gateway allowlist integration via FEISHU_ALLOWED_USERS
- Persistent dedup state across restarts
- Per-chat serial message processing (matches openclaw createChatQueue)
- Processing status reactions: Typing while working, removed on success,
  swapped for CrossMark on failure
- Reaction events routed as synthetic text events (matches openclaw)
- Interactive card button-click events routed as synthetic COMMAND events
- Webhook anomaly tracking (matches openclaw createWebhookAnomalyTracker)
- Verification token validation as second auth layer (matches openclaw)

Feishu identity model
---------------------
Feishu uses three user-ID tiers (official docs:
https://open.feishu.cn/document/home/user-identity-introduction/introduction):

  open_id  (ou_xxx)  — **App-scoped**.  The same person gets a different
                        open_id under each Feishu app.  Always available in
                        event payloads without extra permissions.
  user_id  (u_xxx)   — **Tenant-scoped**.  Stable within a company but
                        requires the ``contact:user.employee_id:readonly``
                        scope.  May not be present.
  union_id (on_xxx)  — **Developer-scoped**.  Same across all apps owned by
                        one developer/ISV.  Best cross-app stable ID.

For bots specifically:

  app_id              — The application's canonical credential identifier.
  bot open_id         — Returned by ``/bot/v3/info``.  This is the bot's own
                        open_id *within its app context* and is what Feishu
                        puts in ``mentions[].id.open_id`` when someone
                        @-mentions the bot.  Used for mention gating only.

In single-bot mode (what Hermes currently supports), open_id works as a
de-facto unique user identifier since there is only one app context.

Session-key participant isolation prefers ``union_id`` (via user_id_alt)
over ``open_id`` (via user_id) so that sessions stay stable if the same
user is seen through different apps in the future.

### class FeishuPostMediaRef

> 继承: `object` ｜ 方法数: 0（公开 0）


### class FeishuMentionRef

> 继承: `object` ｜ 方法数: 0（公开 0）


### class FeishuPostParseResult

> 继承: `object` ｜ 方法数: 0（公开 0）


### class FeishuNormalizedMessage

> 继承: `object` ｜ 方法数: 0（公开 0）


### class FeishuAdapterSettings

> 继承: `object` ｜ 方法数: 0（公开 0）


### class FeishuGroupRule

> 继承: `object` ｜ 方法数: 0（公开 0）

Per-group policy rule for controlling which users may interact with the bot.


### class FeishuBatchState

> 继承: `object` ｜ 方法数: 0（公开 0）


### class FeishuAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 154（公开 17）

Feishu/Lark bot adapter.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to Feishu/Lark.

#### async def `disconnect(self) -> None`

Disconnect from Feishu/Lark.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a Feishu message.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False) -> SendResult`

Edit a previously sent Feishu text/post message.

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[Dict[str, Any]] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Send an interactive card with approval buttons.

The buttons carry ``hermes_action`` in their value dict so that
``_handle_card_action_event`` can intercept them and call
``resolve_gateway_approval()`` to unblock the waiting agent thread.

#### async def `send_update_prompt(self, chat_id: str, prompt: str, default: str = '', session_key: str = '', metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an interactive update prompt with Yes/No buttons.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send audio to Feishu as a file attachment plus optional caption.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a document/file attachment to Feishu.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a video file to Feishu.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a local image file to Feishu.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Feishu bot API does not expose a typing indicator.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Download a remote image then send it through the native Feishu image flow.

#### async def `send_animation(self, chat_id: str, animation_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Feishu has no native GIF bubble; degrade to a downloadable file.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return real chat metadata from Feishu when available.

#### def `format_message(self, content: str) -> str`

Feishu text messages are plain text by default.

#### async def `on_processing_start(self, event: MessageEvent) -> None`

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`


### 顶层函数

#### def `parse_feishu_post_payload(payload: Any, mentions_map: Optional[Dict[str, FeishuMentionRef]] = None) -> FeishuPostParseResult`

#### def `normalize_feishu_message(message_type: str, raw_content: str, mentions: Optional[Sequence[Any]] = None, bot: _FeishuBotIdentity = _FeishuBotIdentity()) -> FeishuNormalizedMessage`

#### def `check_feishu_requirements() -> bool`

Check if Feishu/Lark dependencies are available.

Lazy-installs lark-oapi via ``tools.lazy_deps.ensure("platform.feishu")``
on first call if not present. Rebinds all module-level globals on success.

#### def `probe_bot(app_id: str, app_secret: str, domain: str) -> Optional[dict]`

Verify bot connectivity via /open-apis/bot/v3/info.

Uses lark_oapi SDK when available, falls back to raw HTTP otherwise.
Returns {"bot_name": ..., "bot_open_id": ...} on success, None on failure.

Note: ``bot_open_id`` here is the bot's app-scoped open_id — the same ID
that Feishu puts in @mention payloads.  It is NOT the app_id.

#### def `qr_register(initial_domain: str = 'feishu', timeout_seconds: int = 600) -> Optional[dict]`

Run the Feishu / Lark scan-to-create QR registration flow.

Returns on success::

    {
        "app_id": str,
        "app_secret": str,
        "domain": "feishu" | "lark",
        "open_id": str | None,
        "bot_name": str | None,
        "bot_open_id": str | None,
    }

Returns None on expected failures (network, auth denied, timeout).
Unexpected errors (bugs, protocol regressions) propagate to the caller.

#### def `interactive_setup() -> None`

Interactive setup for Feishu / Lark — scan-to-create or manual creds.

Replaces the central _setup_feishu in hermes_cli/gateway.py and the static
_PLATFORMS["feishu"] dict. CLI helpers are lazy-imported.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.feishu.feishu_comment

### 模块文档

Feishu/Lark drive document comment handling.

Processes ``drive.notice.comment_add_v1`` events and interacts with the
Drive v2 comment reaction API.  Kept in a separate module so that the
main ``feishu.py`` adapter does not grow further and comment-related
logic can evolve independently.

Flow:
  1. Parse event -> extract file_token, comment_id, reply_id, etc.
  2. Add OK reaction
  3. Parallel fetch: doc meta + comment details (batch_query)
  4. Branch on is_whole:
       Whole -> list whole comments timeline
       Local -> list comment thread replies
  5. Build prompt (local or whole)
  6. Create AIAgent with feishu_doc + feishu_drive tools -> agent generates reply
  7. Route reply:
       Whole -> add_whole_comment
       Local -> reply_to_comment (fallback to add_whole_comment on 1069302)

### 顶层函数

#### def `parse_drive_comment_event(data: Any) -> Optional[Dict[str, Any]]`

Extract structured fields from a ``drive.notice.comment_add_v1`` payload.

*data* may be a ``CustomizedEvent`` (WebSocket) whose ``.event`` is a dict,
or a ``SimpleNamespace`` (Webhook) built from the full JSON body.

Returns a flat dict with the relevant fields, or ``None`` when the
payload is malformed.

#### def `add_comment_reaction(client: Any, file_token: str, file_type: str, reply_id: str, reaction_type: str = 'OK') -> bool`

Add an emoji reaction to a document comment reply.

Uses the Drive v2 ``update_reaction`` endpoint::

    POST /open-apis/drive/v2/files/{file_token}/comments/reaction?file_type=...

Returns ``True`` on success, ``False`` on failure (errors are logged).

#### def `delete_comment_reaction(client: Any, file_token: str, file_type: str, reply_id: str, reaction_type: str = 'OK') -> bool`

Remove an emoji reaction from a document comment reply.

Best-effort — errors are logged but not raised.

#### def `query_document_meta(client: Any, file_token: str, file_type: str) -> Dict[str, Any]`

Fetch document title and URL via batch_query meta API.

Returns ``{"title": "...", "url": "...", "doc_type": "..."}`` or empty dict.

#### def `batch_query_comment(client: Any, file_token: str, file_type: str, comment_id: str) -> Dict[str, Any]`

Fetch comment details via batch_query comment API.

Retries up to 6 times on failure (handles eventual consistency).

Returns the comment dict with fields like ``is_whole``, ``quote``,
``reply_list``, etc.  Empty dict on failure.

#### def `list_whole_comments(client: Any, file_token: str, file_type: str) -> List[Dict[str, Any]]`

List all whole-document comments (paginated, up to 500).

#### def `list_comment_replies(client: Any, file_token: str, file_type: str, comment_id: str, expect_reply_id: str = '') -> List[Dict[str, Any]]`

List all replies in a comment thread (paginated, up to 500).

If *expect_reply_id* is set and not found in the first fetch,
retries up to 6 times (handles eventual consistency).

#### def `reply_to_comment(client: Any, file_token: str, file_type: str, comment_id: str, text: str) -> Tuple[bool, int]`

Post a reply to a local comment thread.

Returns ``(success, code)``.

#### def `add_whole_comment(client: Any, file_token: str, file_type: str, text: str) -> bool`

Add a new whole-document comment.

Returns ``True`` on success.

#### def `deliver_comment_reply(client: Any, file_token: str, file_type: str, comment_id: str, text: str, is_whole: bool) -> bool`

Route agent reply to the correct API, chunking long text.

- Whole comment -> add_whole_comment
- Local comment -> reply_to_comment, fallback to add_whole_comment on 1069302

#### def `build_local_comment_prompt(doc_title: str, doc_url: str, file_token: str, file_type: str, comment_id: str, quote_text: str, root_comment_text: str, target_reply_text: str, timeline: List[Tuple[str, str, bool]], self_open_id: str, target_index: int = -1, referenced_docs: str = '') -> str`

Build the prompt for a local (quoted-text) comment.

#### def `build_whole_comment_prompt(doc_title: str, doc_url: str, file_token: str, file_type: str, comment_text: str, timeline: List[Tuple[str, str, bool]], self_open_id: str, current_index: int = -1, nearest_self_index: int = -1, referenced_docs: str = '') -> str`

Build the prompt for a whole-document comment.

#### def `handle_drive_comment_event(client: Any, data: Any, self_open_id: str = '') -> None`

Full orchestration for a drive comment event.

1. Parse event + filter (self-reply, notice_type)
2. Add OK reaction
3. Fetch doc meta + comment details in parallel
4. Branch on is_whole: build timeline
5. Build prompt, run agent
6. Deliver reply


## plugins.platforms.feishu.feishu_comment_rules

### 模块文档

Feishu document comment access-control rules.

3-tier rule resolution: exact doc > wildcard "*" > top-level > code defaults.
Each field (enabled/policy/allow_from) falls back independently.
Config: ~/.hermes/feishu_comment_rules.json (mtime-cached, hot-reload).
Pairing store: ~/.hermes/feishu_comment_pairing.json.

### class CommentDocumentRule

> 继承: `object` ｜ 方法数: 0（公开 0）

Per-document rule.  ``None`` means 'inherit from lower tier'.


### class CommentsConfig

> 继承: `object` ｜ 方法数: 0（公开 0）

Top-level comment access config.


### class ResolvedCommentRule

> 继承: `object` ｜ 方法数: 0（公开 0）

Fully resolved rule after field-by-field fallback.


### 顶层函数

#### def `load_config() -> CommentsConfig`

Load comment rules from disk (mtime-cached).

#### def `has_wiki_keys(cfg: CommentsConfig) -> bool`

Check if any document rule key starts with 'wiki:'.

#### def `resolve_rule(cfg: CommentsConfig, file_type: str, file_token: str, wiki_token: str = '') -> ResolvedCommentRule`

Resolve effective rule: exact doc → wiki key → wildcard → top-level → defaults.

#### def `pairing_add(user_open_id: str) -> bool`

Add a user to the pairing-approved list. Returns True if newly added.

#### def `pairing_remove(user_open_id: str) -> bool`

Remove a user from the pairing-approved list. Returns True if removed.

#### def `pairing_list() -> Dict[str, Any]`

Return the approved dict  {user_open_id: {approved_at: ...}}.

#### def `is_user_allowed(rule: ResolvedCommentRule, user_open_id: str) -> bool`

Check if user passes the resolved rule's policy gate.


## plugins.platforms.feishu.feishu_meeting_invite

### 模块文档

Feishu/Lark meeting-invitation event handling.

Processes ``vc.bot.meeting_invited_v1`` events by converting them into a
synthetic gateway ``MessageEvent``.  Unlike document comments, the response
should go back to the inviter through the normal Hermes gateway pipeline, so
this module does not instantiate an agent directly.

### class MeetingInviteUser

> 继承: `object` ｜ 方法数: 0（公开 0）


### class MeetingInviteMeeting

> 继承: `object` ｜ 方法数: 0（公开 0）


### class MeetingInvitedPayload

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `parse_meeting_invited_event(data: Any) -> Optional[MeetingInvitedPayload]`

#### def `build_meeting_invite_prompt(payload: MeetingInvitedPayload) -> str`

#### def `handle_meeting_invited_event(adapter: Any, data: Any) -> None`

Convert a vc.bot.meeting_invited_v1 event into a gateway MessageEvent.


## plugins.platforms.google_chat.__init__


## plugins.platforms.google_chat.adapter

### 模块文档

Google Chat platform adapter.

Uses authenticated HTTP callbacks or Google Cloud Pub/Sub for inbound
events and the Google Chat REST API for outbound messages. Pub/Sub remains
available for no-public-URL deployments.

Concurrency model
-----------------
The Pub/Sub SubscriberClient invokes its message callback in a background
thread (managed by the client's internal executor). The adapter's
``handle_message`` coroutine must run on the asyncio event loop, so the
callback uses ``asyncio.run_coroutine_threadsafe`` with
``add_done_callback`` (never ``.result()`` — that would block the callback
thread and saturate the Pub/Sub executor under load).

All outbound Chat REST calls go through ``asyncio.to_thread`` because the
googleapiclient is synchronous. This keeps the event loop responsive.

Pub/Sub delivery diagram::

    Pub/Sub stream   ->  callback thread        ->  asyncio loop
    (streaming_pull)     (_on_pubsub_message)       (handle_message)
         |                       |                        |
         |   at-least-once       |  parse + dedup         |  agent work
         |   delivery            |  _submit_on_loop       |  send() response
         |                       |  message.ack()         |
         v                       v                        v

Event type routing
------------------
Inbound envelope carries ``type`` in [MESSAGE, ADDED_TO_SPACE, REMOVED_FROM_SPACE,
CARD_CLICKED]. Only MESSAGE dispatches to the agent. ADDED_TO_SPACE caches the
bot's resource name (belt-and-suspenders on top of eager resolution in connect()).
CARD_CLICKED is ACK'd only in v1 (follow-up PR implements interactivity).

### class GoogleChatAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 50（公开 20）

Google Chat bot adapter using Pub/Sub pull + Chat REST API.

Required environment (see gateway/config.py Google Chat block):
  GOOGLE_CHAT_PROJECT_ID           (or GOOGLE_CLOUD_PROJECT fallback)
  GOOGLE_CHAT_SUBSCRIPTION_NAME    (or GOOGLE_CHAT_SUBSCRIPTION fallback)
  GOOGLE_CHAT_SERVICE_ACCOUNT_JSON (or GOOGLE_APPLICATION_CREDENTIALS)

Optional:
  GOOGLE_CHAT_ALLOWED_USERS, GOOGLE_CHAT_ALLOW_ALL_USERS
  GOOGLE_CHAT_HOME_CHANNEL
  GOOGLE_CHAT_MAX_MESSAGES (FlowControl, default 1)
  GOOGLE_CHAT_MAX_BYTES    (FlowControl, default 16_777_216 = 16 MiB)

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Validate config, authenticate, start Pub/Sub pull, resolve bot id.

#### async def `disconnect(self) -> None`

Clean shutdown: stop accepting new messages, wait in-flight, close clients.

#### async def `dispatch_http_event(self, envelope: Dict[str, Any]) -> Dict[str, Any]`

#### def `verify_http_event_request(self, auth_header: str) -> Tuple[bool, str]`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a text message.

Signature matches ``BasePlatformAdapter.send``: ``content`` is the
message body, ``reply_to`` is an optional message_id (the inbound
message to thread under), and ``metadata`` may carry ``thread_id``
(the resolved Google Chat ``spaces/X/threads/Y`` resource name).

If a typing card is tracked for this chat, transform it in-place via
``messages.patch`` — NO delete+create. Google Chat shows a tombstone
("Message deleted by its author") on delete, which is visual noise.
Patch rewrites the text of the existing message seamlessly.

Also pauses the base class's ``_keep_typing`` loop for this chat so
it can't post a racing typing card between the patch and the reply.

If ``content`` exceeds MAX_MESSAGE_LENGTH, the first chunk patches
the typing card (if any), subsequent chunks are new messages.

#### async def `send_card(self, chat_id: str, card: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_clarify(self, chat_id: str, question: str, choices: Optional[list], clarify_id: str, session_key: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False) -> SendResult`

Edit a previously sent message via ``messages.patch``.

Required for the gateway tool-progress + token-streaming pipeline:
``GatewayStreamConsumer`` and ``send_progress_messages`` both gate
on this method being overridden (see gateway/run.py:10199 and
gateway/stream_consumer.py). Without it, Google Chat shows no
tool activity (no "🔍 web_search…", no progressive token edits).

``message_id`` is the Google Chat resource name
``spaces/X/messages/Y``. ``finalize`` is unused here — Google
Chat's patch API has no streaming lifecycle state, so the same
patch closes the stream and any prior edit.

404 (message gone) and 403 (perms revoked) are reported as
non-success; the gateway falls back to ``send()`` for the next
edit cycle.

#### async def `delete_message(self, chat_id: str, message_id: str) -> bool`

Delete a message — used sparingly (deletion creates a tombstone).

The base contract returns False on unsupported. We do support it,
but most internal code should prefer ``edit_message`` to avoid the
"Message deleted by its author" tombstone. Provided so the
gateway's stream-consumer fallback paths (e.g. removing an aborted
partial preview) work correctly when explicit deletion is the
right call.

#### classmethod `format_message(cls, content: str) -> str`

Convert standard Markdown to Google Chat's formatting dialect.

Google Chat renders a small subset: ``*bold*``, ``_italic_``,
``~strikethrough~``, fenced/inline code. Standard Markdown
constructs (``**bold**``, ``# headers``, ``[text](url)``) do
not render and need conversion before they reach Chat.

Code blocks (fenced AND inline) are protected from transformation
via placeholder substitution so backticks-wrapped content with
literal asterisks or brackets stays intact. Invisible Unicode
codepoints that render as tofu in Chat's restricted font stack
are stripped at the end. Empty/None input passes through.

Pattern lifted from PR #14965.

#### async def `send_typing(self, chat_id: str, metadata: Any = None) -> None`

Post a visible 'Hermes is thinking…' marker message.

NOT ephemeral (Google Chat has no ephemeral text messages outside
slash command responses). ``send()`` PATCHes this marker in-place
with the real response (no deletion tombstone). The typing card is
either patched by ``send()`` (success) or by
``on_processing_complete`` (failure / cancellation).

IMPORTANT — must place the typing card in the user's thread:
``messages.patch`` cannot change a message's ``thread`` (it's
immutable on update). If we create the typing card at top-level
and the user is replying inside thread T, send() will patch the
top-level card in place — leaving the bot's whole response
stranded outside the user's thread. We resolve the thread the
same way send() does.

IMPORTANT — cancellation safety:
``base.py``'s ``_keep_typing`` calls this through
``asyncio.wait_for(send_typing, timeout=1.5)``. When the
create-API call takes longer than 1.5s, ``wait_for`` cancels
``send_typing`` mid-flight — but the underlying ``asyncio.to_thread``
keeps running and creates a card in Chat that we have NO way to
track (the storage line never runs). Next ``_keep_typing`` tick
sees an empty slot and creates a SECOND card. Result: one orphan
"Hermes is thinking…" stuck in chat forever, plus one card that
gets patched into the reply.

Fix: reserve the slot with an in-flight ``Event``, run the
create in a background task, and ``await asyncio.shield`` it.
Cancellation of THIS coroutine no longer cancels the create —
the task runs to completion and the msg_id lands in the slot
regardless.

#### async def `stop_typing(self, chat_id: str) -> None`

Stop the typing indicator — NO-OP when a live card is tracked.

Google Chat has no separate typing API: the "Hermes is thinking…"
marker is a real message that ``send()`` patches in-place with the
agent's reply. Deleting the marker creates a "Message deleted by
its author" tombstone, which is visual noise.

Upstream code (gateway/run.py and gateway/platforms/base.py) calls
``stop_typing`` at three moments per turn — typically BEFORE
``send()`` runs (so deleting the slot would leave ``send()``
nothing to patch, forcing it to create a fresh message and leaving
the original card as a tombstone). To fix this without modifying
upstream contracts, ``stop_typing`` here is intentionally a NO-OP
when the slot holds a real ``message_name``: the card is left in
place so ``send()`` can patch it.

Three cases:
  * Slot empty → nothing to do.
  * Slot holds SENTINEL → ``send()`` already patched the card;
    pop the sentinel so the next turn starts clean.
  * Slot holds a real ``message_name`` → leave it for ``send()``
    to consume. NO-OP.

Stranded cards on error / cancellation paths (where ``send()``
never runs) are reaped by ``on_processing_complete`` — see that
hook for the patch-to-final-state cleanup.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Reap typing card(s) after the message-handling cycle ends.

SUCCESS: ``send()`` set the SENTINEL after patching. Pop it.

FAILURE / CANCELLED: ``send()`` may not have run, leaving a real
``message_name`` in the slot. Patching the card to a final state
(``"(interrupted)"``) avoids the tombstone that ``messages.delete``
would create. If ``send()`` did run (e.g. base.py error-send branch
patched it), the slot holds the SENTINEL — pop and exit.

Orphan cards: when a background ``send_typing`` task creates a
card AFTER ``send()`` already populated the slot (race window
when the API call takes longer than _keep_typing's wait_for
timeout), the orphan id is stashed in ``self._orphan_typing_messages``.
Patch each orphan with an empty-ish marker so the user doesn't
see "Hermes is thinking…" stuck forever.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an inline image via attachment URL (no upload).

If a typing card is tracked for this chat, patch it in-place with
the image (caption + URL) — same anti-tombstone pattern used by
``send()``. Otherwise create a new message.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs: Any) -> SendResult`

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs: Any) -> SendResult`

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs: Any) -> SendResult`

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs: Any) -> SendResult`

#### async def `send_animation(self, chat_id: str, animation_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Google Chat has no native animation type; fall back to send_image.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return {name, type, chat_id} for a space.


### 顶层函数

#### def `check_google_chat_requirements() -> bool`

Check if Google Chat optional dependencies are installed.

Triggers the lazy import of the google-cloud + googleapiclient stack
on first call. Subsequent calls hit the cached result. This is the
canonical "are the deps available" probe used by the plugin registry
and the adapter's own startup gate.

#### def `card_spec_to_cards_v2(card_spec: Dict[str, Any]) -> Dict[str, Any]`

**异常**: `ValueError`

#### def `interactive_setup() -> None`

Walk the user through Google Chat configuration via ``hermes setup``.

The setup wizard at ``hermes_cli/gateway.py`` calls this for plugin
platforms instead of using the in-tree ``_PLATFORMS`` data block. The
flow mirrors the in-tree built-ins: print the GCP setup instructions,
prompt for env vars, persist them to ``~/.hermes/.env`` so the next
gateway restart picks them up.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system at startup.

Registers the Google Chat adapter under the ``google_chat`` name.
The gateway's ``_create_adapter`` consults the platform registry
BEFORE its built-in if/elif chain, so this registration is what
drives adapter creation at runtime.


## plugins.platforms.google_chat.oauth

### 模块文档

User OAuth helper for the Google Chat gateway adapter.

Google Chat's ``media.upload`` REST endpoint hard-rejects service-account
authentication:

    "This method doesn't support app authentication with a service
     account. Authenticate with a user account."

(See https://developers.google.com/workspace/chat/api/reference/rest/v1/media/upload
and https://developers.google.com/chat/api/guides/auth/users.)

For the bot to deliver native file attachments — the same drag-and-drop
file widget the user gets when they upload manually — each user must
grant the bot the ``chat.messages.create`` scope ONCE in their own DM.
The bot stores per-user refresh tokens and calls ``media.upload`` plus
the subsequent ``messages.create`` *as the requesting user* whenever a
file needs sending.

This module is BOTH a CLI tool (driven by the agent via slash commands or
terminal commands) AND a library imported by ``google_chat.py``:

    Library functions (called from the adapter at runtime):
        load_user_credentials(email=None) -> Credentials | None
        refresh_or_none(creds, email=None) -> Credentials | None
        build_user_chat_service(creds) -> chat_v1.Resource
        list_authorized_emails() -> List[str]

    CLI commands (driven by the agent through the /setup-files slash
    command, modeled on skills/productivity/google-workspace/scripts/setup.py):
        --check                          Exit 0 if auth is valid, else 1
        --client-secret /path/to.json    Persist OAuth client credentials
        --auth-url                       Print the OAuth URL for the user
        --auth-code CODE                 Exchange auth code for token
        --revoke                         Revoke and delete stored token
        --install-deps                   Install Python dependencies
        --email EMAIL                    Scope CLI ops to a specific user
                                         (defaults to legacy single-user
                                         mode when omitted)

The flow mirrors the existing google-workspace skill exactly so anyone
familiar with that flow can read this without surprises.

Token storage layout
--------------------
- Per-user tokens (keyed by sender email):
    ``${HERMES_HOME}/google_chat_user_tokens/<sanitized_email>.json``
- Legacy single-user token (fallback, untouched for backward compat):
    ``${HERMES_HOME}/google_chat_user_token.json``
- Per-user pending OAuth state during /setup-files start → exchange:
    ``${HERMES_HOME}/google_chat_user_oauth_pending/<sanitized_email>.json``
- Legacy pending state:
    ``${HERMES_HOME}/google_chat_user_oauth_pending.json``
- OAuth client secret (profile-scoped — each profile registers its own):
    ``${HERMES_HOME}/google_chat_user_client_secret.json``

### 顶层函数

#### def `load_user_credentials(email: Optional[str] = None) -> Optional[Any]`

Load + validate persisted user OAuth credentials.

``email`` selects the per-user token file; ``None`` falls back to the
legacy single-user path (left in place for installs that ran the
pre-multi-user flow). Returns a ``google.oauth2.credentials.Credentials``
instance ready for use, or ``None`` if no token is stored, the token
is corrupt, or refresh fails. Adapter callers should treat ``None``
as "user has not run /setup-files yet" and surface the setup-instructions
fallback to the user.

Does NOT raise on the no-token case — that's expected.

#### def `refresh_or_none(creds: Any, email: Optional[str] = None) -> Optional[Any]`

Refresh ``creds`` if expired. Returns the credentials or ``None``.

Used by the adapter just before calling media.upload to ensure the
token is current. Returns ``None`` if refresh fails — caller falls
back to the text-notice path. ``email`` controls where the refreshed
token is written back; ``None`` keeps the legacy single-file path.

#### def `build_user_chat_service(creds: Any) -> Any`

Build a Google Chat API client authenticated as the user.

Used for media.upload + the subsequent messages.create that
references the attachmentDataRef. The bot's separate SA-authed
client (``self._chat_api`` in the adapter) is for everything else.

#### def `list_authorized_emails() -> List[str]`

Return the set of user emails that have stored per-user tokens.

Lists files in the per-user tokens dir; does NOT include the legacy
single-user token (its owner is unknown). Sanitized filenames lose
the ``+suffix`` part of plus-addressed emails — accept that and use
this list only for admin display, not for trust decisions.

#### def `install_deps() -> bool`

**异常**: `RuntimeError`

#### def `check_auth(email: Optional[str] = None) -> bool`

Print status; return True if creds are usable.

Per-user when ``email`` given, legacy single-user when omitted.

#### def `store_client_secret(path: str) -> None`

Validate and copy the user's OAuth client_secret.json into HERMES_HOME.

#### def `get_auth_url(email: Optional[str] = None) -> None`

Print the OAuth URL for the user to visit. Persists PKCE state.

``email`` namespaces the pending state so two users can be mid-flow
in parallel without trampling each other's PKCE verifier.

#### def `exchange_auth_code(code: str, email: Optional[str] = None) -> None`

Exchange an auth code (or pasted redirect URL) for a refresh token.

``email`` selects the destination token path. ``None`` writes to the
legacy single-user path (kept for the existing CLI entrypoint and for
pre-multi-user installs).

#### def `revoke(email: Optional[str] = None) -> None`

Revoke the stored token with Google and delete it locally.

Per-user when ``email`` given, legacy single-user when omitted.

#### def `main() -> None`


## plugins.platforms.homeassistant.__init__


## plugins.platforms.homeassistant.adapter

### 模块文档

Home Assistant platform adapter.

Connects to the HA WebSocket API for real-time event monitoring.
State-change events are converted to MessageEvent objects and forwarded
to the agent for processing.  Outbound messages are delivered as HA
persistent notifications.

Requires:
- aiohttp (already in messaging extras)
- HASS_TOKEN env var (Long-Lived Access Token)
- HASS_URL env var (default: http://homeassistant.local:8123)

### class HomeAssistantAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 13（公开 5）

Home Assistant WebSocket adapter.

Subscribes to ``state_changed`` events and forwards them as
MessageEvent objects.  Supports domain/entity filtering and
per-entity cooldowns to avoid event floods.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to HA WebSocket API and subscribe to events.

#### async def `disconnect(self) -> None`

Disconnect from Home Assistant.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a notification via HA REST API (persistent_notification.create).

Uses the REST API instead of WebSocket to avoid a race condition
with the event listener loop that reads from the same WS connection.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

No typing indicator for Home Assistant.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return basic info about the HA event channel.


### 顶层函数

#### def `check_ha_requirements() -> bool`

Check if Home Assistant runtime dependencies are available.

#### def `validate_ha_config(config: PlatformConfig) -> bool`

Return True when Home Assistant has enough credential config to connect.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.irc.__init__


## plugins.platforms.irc.adapter

### 模块文档

IRC Platform Adapter for Hermes Agent.

A plugin-based gateway adapter that connects to an IRC server and relays
messages to/from the Hermes agent.  Zero external dependencies — uses
Python's stdlib asyncio for the IRC protocol.

Configuration in config.yaml::

    gateway:
      platforms:
        irc:
          enabled: true
          extra:
            server: irc.libera.chat
            port: 6697
            nickname: hermes-bot
            channel: "#hermes"
            use_tls: true
            server_password: ""       # optional server password
            nickserv_password: ""     # optional NickServ identification
            allowed_users: []         # empty = allow all, or list of nicks
            max_message_length: 450   # IRC line limit (safe default)

Or via environment variables (overrides config.yaml):
    IRC_SERVER, IRC_PORT, IRC_NICKNAME, IRC_CHANNEL, IRC_USE_TLS,
    IRC_SERVER_PASSWORD, IRC_NICKSERV_PASSWORD

### class IRCAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 13（公开 6）

Async IRC adapter implementing the BasePlatformAdapter interface.

This class is instantiated by the adapter_factory passed to
register_platform().

#### def `__init__(config, **kwargs)`

#### property `name(self) -> str`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to the IRC server, register, and join the channel.

#### async def `disconnect(self) -> None`

Quit and close the connection.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None)`

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

IRC has no typing indicator — no-op.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`


### 顶层函数

#### def `check_requirements() -> bool`

Check if IRC is configured.

Only requires the server and channel — no external pip packages needed.

#### def `validate_config(config) -> bool`

Validate that the platform config has enough info to connect.

#### def `interactive_setup() -> None`

Interactive `hermes gateway setup` flow for the IRC platform.

Lazy-imports ``hermes_cli.setup`` helpers so the plugin stays importable
in non-CLI contexts (gateway runtime, tests).

#### def `is_connected(config) -> bool`

Check whether IRC is configured (env or config.yaml).

#### def `register(ctx)`

Plugin entry point: called by the Hermes plugin system.


## plugins.platforms.line.__init__


## plugins.platforms.line.adapter

### 模块文档

LINE Messaging API platform adapter for Hermes Agent.

A bundled platform plugin that runs an aiohttp webhook server, accepts LINE
webhook events (signature-verified), and relays messages to/from the agent
via the standard ``BasePlatformAdapter`` interface.

Design highlights
-----------------

**Reply token preferred, Push fallback.** LINE's reply token is single-use
and expires roughly 60 seconds after the inbound event. We try Reply first
(it's free) and fall back to the metered Push API when the token is absent,
expired, or rejected by the API.

**Slow-LLM postback button (optional).** When the LLM is still running past
``slow_response_threshold`` seconds (default 45, leaving 15s margin on the
60s reply-token TTL), we burn the original reply token to send a Template
Buttons bubble — the user taps it later to receive the cached answer via a
*fresh* reply token (also free). State machine: PENDING → READY → DELIVERED,
with ERROR for cancelled runs. Set the threshold to 0 to disable the
button and always Push-fallback instead.

**Three-allowlist gating.** Separate allowlists for users (U-prefixed),
groups (C-prefixed), and rooms (R-prefixed). ``LINE_ALLOW_ALL_USERS=true``
is a dev-only escape hatch.

**Media via public HTTPS.** LINE's Messaging API does *not* accept
binary uploads — images, audio, and video must be reachable HTTPS URLs.
We register registered tempfiles under ``/line/media/<token>/<filename>``
served by the same aiohttp app, with an allowed-roots traversal guard.
``LINE_PUBLIC_URL`` (e.g. ``https://my-tunnel.example.com``) overrides
the host:port construction so URLs are reachable when bind is 0.0.0.0
or behind a reverse proxy.

**5-message batching.** LINE accepts at most 5 message objects per
Reply/Push call; longer responses are smart-chunked at 4500 chars
(LINE per-bubble limit is 5000) and batched.

Synthesis credits
-----------------

This file is a synthesis of seven open community PRs adding LINE support
to Hermes Agent. It deliberately ports the *strongest* idea from each into
a single plugin-form module that requires zero core edits:

* PR #18153 (leepoweii)   — Template Buttons postback cache state machine,
  Markdown URL preservation, system-message bypass.
* PR #8398  (yuga-hashimoto) — media URL serving with traversal guard,
  send_voice / send_video, ``LINE_PUBLIC_URL`` env, macOS ``/tmp`` root.
* PR #16832 (jethac)      — config wiring style, voice/image tests.
* PR #21023 (perng)       — plugin-form skeleton (the only one already
  modeled on ``ADDING_A_PLATFORM.md``), reply→push fallback at 50s TTL,
  loading-animation indicator, source dispatcher.
* PR #14942 (soichiyo)    — Cloudflare-tunnel operating model (docs only).
* PR #14988 (David-0x221Eight) — text-first scope discipline.
* PR #6676  (liyoungc)    — Push-only mode (used as the ``threshold=0``
  fallback path here).

### class State

> 继承: `enum.Enum` ｜ 方法数: 0（公开 0）


### class RequestCache

> 继承: `object` ｜ 方法数: 8（公开 7）

In-memory cache for slow-LLM postback retrieval.

PRs #18153 originally combined two TTLs — one for PENDING (24h) and
a shorter one for READY/DELIVERED/ERROR (1h). We keep the same model
here.

#### def `__init__(ttl_seconds: int = 3600, pending_ttl_seconds: int = 86400) -> None`

#### def `register_pending(self, chat_id: str) -> str`

#### def `get(self, request_id: str) -> Optional[_CacheEntry]`

#### def `set_ready(self, request_id: str, payload: Any) -> None`

#### def `set_error(self, request_id: str, message: str) -> None`

#### def `mark_delivered(self, request_id: str) -> None`

#### def `find_pending_for_chat(self, chat_id: str) -> Optional[str]`

#### def `prune(self) -> int`


### class LineAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 24（公开 10）

LINE Messaging API gateway adapter.

#### def `__init__(config, **kwargs)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Trigger LINE's loading-animation indicator (DM only).

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Best-effort chat info derived from the chat_id prefix.

LINE's chat-info APIs are limited and per-source-type — instead of
chasing them we infer from the well-known ID prefixes:
``U`` = user (1:1), ``C`` = group, ``R`` = room. The agent only
needs ``name`` + ``type`` from this method.

#### def `format_message(self, content: str) -> str`

Strip Markdown that LINE can't render. URLs are preserved.

#### async def `interrupt_session_activity(self, session_key: str, chat_id: str) -> None`

Resolve any orphan PENDING postback so the button doesn't loop.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_voice(self, chat_id: str, audio_path: str, duration_ms: int = 1000, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_video(self, chat_id: str, video_path: str, preview_path: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`


### 顶层函数

#### def `strip_markdown_preserving_urls(text: str) -> str`

Strip Markdown that LINE can't render, but keep URLs usable.

LINE's text bubble has zero Markdown support — bold, italics, code
fences, headings, and bullet markers all render as literal characters.
URLs *are* auto-linked by the client, but only when they appear bare
(not inside ``[label](url)`` syntax). This converts ``[label](url)``
to ``label (url)`` so the URL remains tappable, then strips the rest.

Source: PR #18153 (leepoweii) — adapted to keep code-block content
visible (LINE users frequently want command snippets to land as
plain text, not be eaten by the fence).

#### def `split_for_line(text: str, max_chars: int = LINE_SAFE_BUBBLE_CHARS) -> List[str]`

Split ``text`` into LINE-sized bubbles, preferring paragraph/line breaks.

Returns at most ``LINE_MAX_MESSAGES_PER_CALL`` chunks; longer text is
truncated with an ellipsis on the final chunk to keep the response
deliverable in a single Reply/Push call.

#### def `verify_line_signature(body: bytes, signature: str, channel_secret: str) -> bool`

Verify a LINE webhook's ``X-Line-Signature`` header.

LINE signs the *raw* request body with HMAC-SHA256 keyed by the
channel secret, then base64-encodes the digest. Constant-time
comparison defends against timing oracles.

#### def `build_postback_button_message(text: str, button_label: str, request_id: str) -> Dict[str, Any]`

Template Buttons message — the slow-LLM postback bubble.

From PR #18153 (leepoweii). Template Buttons stay tappable from chat
history, unlike Quick Reply chips which are dismissed the moment any
new message arrives in the chat.

LINE limits: ``text`` ≤ 160 chars, ``altText`` ≤ 400 chars.

#### def `check_requirements() -> bool`

Plugin gate: require credentials AND aiohttp at runtime.

#### def `validate_config(config) -> bool`

#### def `is_connected(config) -> bool`

Surface in ``hermes status`` even before the adapter is instantiated.

#### def `interactive_setup() -> None`

Minimal stdin wizard for ``hermes setup line``.

Mirrors the irc/teams style: prompts for the two required vars, plus
one optional public URL. Writes to ``~/.hermes/.env`` via ``hermes_cli.config``.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system at startup.


## plugins.platforms.matrix.__init__


## plugins.platforms.matrix.adapter

### 模块文档

Matrix gateway adapter.

Connects to any Matrix homeserver (self-hosted or matrix.org) via the
mautrix Python SDK.  Supports optional end-to-end encryption (E2EE)
when installed with ``pip install "mautrix[encryption]"``.

Environment variables:
    MATRIX_HOMESERVER           Homeserver URL (e.g. https://matrix.example.org)
    MATRIX_ACCESS_TOKEN         Access token (preferred auth method)
    MATRIX_USER_ID              Full user ID (@bot:server) — required for password login
    MATRIX_PASSWORD             Password (alternative to access token)
    MATRIX_ENCRYPTION           Set "true" to enable E2EE
    MATRIX_E2EE_MODE            off | optional | required. Overrides MATRIX_ENCRYPTION
                                when set. Legacy MATRIX_ENCRYPTION=true maps to required.
    MATRIX_DEVICE_ID            Stable device ID for E2EE persistence across restarts
    MATRIX_PROXY                HTTP(S) or SOCKS proxy URL for Matrix traffic
    MATRIX_ALLOWED_USERS    Comma-separated Matrix user IDs (@user:server)
    MATRIX_ALLOWED_ROOMS    Comma-separated Matrix room IDs allowed to trigger turns
    MATRIX_HOME_ROOM        Room ID for cron/notification delivery
    MATRIX_REACTIONS        Set "false" to disable processing lifecycle reactions
                            (eyes/checkmark/cross). Default: true
    MATRIX_REQUIRE_MENTION      Require @mention in rooms (default: true)
    MATRIX_FREE_RESPONSE_ROOMS  Comma-separated room IDs exempt from mention requirement
                                (alias of matrix.free_response_rooms)
    MATRIX_ALLOWED_ROOMS    Comma-separated room IDs; if set, bot ONLY responds
                            in these rooms (whitelist, DMs exempt; alias of
                            matrix.allowed_rooms)
    MATRIX_IGNORE_USER_PATTERNS Comma-separated regular expressions for appservice /
                                bridge ghost user IDs to ignore
    MATRIX_PROCESS_NOTICES      Set "true" to process inbound m.notice events
                                (default: false)
    MATRIX_ALLOW_ROOM_MENTIONS  Allow outbound @room mentions to notify whole rooms
                                (default: false)
    MATRIX_TOOLS_ALLOW_REDACTION
                              Allow Matrix redaction tool execution (default: false)
    MATRIX_TOOLS_ALLOW_INVITES Allow Matrix invite tool execution (default: false)
    MATRIX_TOOLS_ALLOW_ROOM_CREATE
                              Allow Matrix room creation tool execution (default: false)
    MATRIX_AUTO_THREAD          Auto-create threads for room messages (default: true)
    MATRIX_DM_AUTO_THREAD       Auto-create threads for DM messages (default: false)
    MATRIX_RECOVERY_KEY         Recovery key for cross-signing verification after device key rotation
    MATRIX_DM_MENTION_THREADS   Create a thread when bot is @mentioned in a DM (default: false)
    MATRIX_ALLOW_PUBLIC_ROOMS   Allow Matrix tools to create public rooms (default: false)
    MATRIX_MAX_MESSAGE_LENGTH   Outbound message chunk size in characters (default: 16000)
    MATRIX_APPROVAL_REQUIRE_SENDER
                              Require reaction controls to come from the original requester
                              when requester metadata is available (default: true)
    MATRIX_APPROVAL_TIMEOUT_SECONDS
                              Reaction approval/model-picker timeout (default: 300)

### class MatrixRoomIdentity

> 继承: `object` ｜ 方法数: 0（公开 0）

Resolved Matrix room identity for routing and prompt context.


### class MatrixAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 92（公开 26）

Gateway adapter for Matrix (any homeserver).

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to the Matrix homeserver and start syncing.

#### async def `disconnect(self) -> None`

Disconnect from Matrix.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a message to a Matrix room.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return room name and type (dm/group).

#### def `get_diagnostics(self) -> Dict[str, Any]`

Return redacted Matrix readiness/status diagnostics.

#### async def `send_typing(self, chat_id: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Send a typing indicator.

#### async def `stop_typing(self, chat_id: str) -> None`

Clear the typing indicator.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False) -> SendResult`

Edit an existing message (via m.replace).

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Download an image URL and upload it to Matrix.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload a local image file to Matrix.

#### async def `send_multiple_images(self, chat_id: str, images: list[tuple[str, str]], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send multiple Matrix images as one ordered logical batch.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload a local file as a document.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload an audio file as a voice message (MSC3245 native voice).

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload a video file.

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[dict] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Send a reaction-based exec approval prompt for Matrix.

#### async def `send_model_picker(self, chat_id: str, providers: list, current_model: str, current_provider: str, session_key: str, on_model_selected, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a Matrix reaction-based model picker.

#### async def `send_choice_picker(self, chat_id: str, title: str, choices: list, session_key: str, on_choice_selected, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a Matrix reaction-based choice picker (/reasoning, /fast).

Generic single-level companion to ``send_model_picker``. Each choice
dict: ``{"value": str, "label": str, "is_current": bool}``.

#### def `format_message(self, content: str) -> str`

Pass-through — Matrix supports standard Markdown natively.

#### async def `on_processing_start(self, event: MessageEvent) -> None`

Add eyes reaction when the agent starts processing a message.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Replace eyes with checkmark (success) or cross (failure).

#### async def `send_read_receipt(self, room_id: str, event_id: str) -> bool`

Send a read receipt (m.read) for an event.

#### async def `redact_message(self, room_id: str, event_id: str, reason: str = '') -> bool`

Redact (delete) a message or event from a room.

#### async def `create_room(self, name: str = '', topic: str = '', invite: Optional[list] = None, is_direct: bool = False, preset: str = 'private_chat') -> Optional[str]`

Create a new Matrix room.

#### async def `invite_user(self, room_id: str, user_id: str) -> bool`

Invite a user to a room.

#### async def `fetch_history(self, room_id: str, limit: int = 20, from_token: str = '') -> list[dict[str, Any]]`

Fetch recent Matrix room history using the live client.

#### async def `set_presence(self, state: str = 'online', status_msg: str = '') -> bool`

Set the bot's presence status.


### 顶层函数

#### def `get_matrix_capabilities() -> Dict[str, str]`

Return Matrix gateway capabilities for docs and release checks.

#### def `check_matrix_requirements() -> bool`

Return True if the Matrix adapter can be used.

Lazy-installs the full ``platform.matrix`` feature group via
``tools.lazy_deps.ensure_and_bind`` whenever any of the declared
packages (mautrix, Markdown, aiosqlite, asyncpg, aiohttp-socks) is
missing — not just mautrix itself.  Previously this short-circuited on
``import mautrix``, which left the other four packages uninstalled
forever and broke E2EE connect with ``No module named 'asyncpg'``
(#31116).  Rebinds module-level type globals on success.

#### def `interactive_setup() -> None`

Configure Matrix credentials. Replaces hermes_cli/setup.py::_setup_matrix
and the static _PLATFORMS["matrix"] dict. CLI helpers are lazy-imported.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.mattermost.__init__


## plugins.platforms.mattermost.adapter

### 模块文档

Mattermost gateway adapter.

Connects to a self-hosted (or cloud) Mattermost instance via its REST API
(v4) and WebSocket for real-time events.  No external Mattermost library
required — uses aiohttp which is already a Hermes dependency.

Environment variables:
    MATTERMOST_URL              Server URL (e.g. https://mm.example.com)
    MATTERMOST_TOKEN            Bot token or personal-access token
    MATTERMOST_ALLOWED_USERS    Comma-separated user IDs
    MATTERMOST_HOME_CHANNEL     Channel ID for cron/notification delivery

### class MattermostAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 28（公开 13）

Gateway adapter for Mattermost (self-hosted or cloud).

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to Mattermost and start the WebSocket listener.

#### async def `disconnect(self) -> None`

Disconnect from Mattermost.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a message (or multiple chunks) to a channel.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return channel name and type.

#### async def `send_typing(self, chat_id: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Send a typing indicator.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False) -> SendResult`

Edit an existing post.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Download an image and upload it as a file attachment.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload a local image file.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload a local file as a document.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload an audio file.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Upload a video file.

#### def `format_message(self, content: str) -> str`

Mattermost uses standard Markdown — mostly pass through.

Strip image markdown into plain links (files are uploaded separately).

#### async def `send_multiple_images(self, chat_id: str, images: List[Tuple[str, str]], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send a batch of images as a single Mattermost post with multiple attachments.

Mattermost supports up to 5 ``file_ids`` per post. Each image is
uploaded individually (Mattermost's file API is one-at-a-time),
then a single post is created referencing all uploaded file_ids
at once. Batches larger than 5 are chunked. Falls back to the
base per-image loop on total failure.


### 顶层函数

#### def `check_mattermost_requirements() -> bool`

Return True if the Mattermost adapter runtime dependency is available.

#### def `validate_mattermost_config(config: PlatformConfig) -> bool`

Return True when Mattermost has enough config to connect.

#### def `interactive_setup() -> None`

Guide the user through Mattermost bot setup.

Mirrors Discord/Teams' ``interactive_setup`` shape: lazy-imports CLI
helpers so the plugin's import surface stays small, prompts for the
server URL + bot token, captures an allowlist, and offers to set a
home channel.  Replaces the central
``hermes_cli/setup.py::_setup_mattermost`` function this migration
removes.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.ntfy.__init__


## plugins.platforms.ntfy.adapter

### 模块文档

ntfy platform adapter (Hermes plugin).

Subscribes to a topic on ntfy.sh or any self-hosted ntfy server via
HTTP streaming (``/json`` endpoint with ``poll=false``) and publishes
replies via HTTP POST. No external SDK — only httpx, which is already
a Hermes dependency.

This adapter ships as a Hermes platform plugin under
``plugins/platforms/ntfy/``. The Hermes plugin loader scans the
directory at startup, calls :func:`register`, and the platform becomes
available to ``gateway/run.py`` and ``tools/send_message_tool`` through
the registry — no edits to core files required.

Configuration in config.yaml::

    platforms:
      ntfy:
        enabled: true
        extra:
          server: "https://ntfy.sh"       # or self-hosted URL
          topic: "hermes-in"              # subscribe topic (incoming)
          publish_topic: "hermes-out"     # optional — defaults to topic
          token: "..."                    # optional Bearer / Basic auth token
          markdown: true                  # optional — enable markdown (default: false)

Environment variables (all read at adapter construct time, env wins over
config.yaml ``extra``):

    NTFY_TOPIC                 Topic to subscribe to (required)
    NTFY_SERVER_URL            Server URL (default: https://ntfy.sh)
    NTFY_TOKEN                 Bearer token or 'user:pass' for Basic auth
    NTFY_PUBLISH_TOPIC         Reply topic (defaults to NTFY_TOPIC)
    NTFY_MARKDOWN              "true"/"1"/"yes" enables X-Markdown header
    NTFY_ALLOWED_USERS         Allowlist (treated by gateway as user IDs;
                               on ntfy these are topic names)
    NTFY_ALLOW_ALL_USERS       Allow any topic — dev only
    NTFY_HOME_CHANNEL          Default topic for cron / notification delivery
    NTFY_HOME_CHANNEL_NAME     Human label for the home channel

Identity model: ntfy has no native authenticated user identity. The
``title`` field is publisher-controlled and is NOT used for
authorization. Each topic is treated as a single trusted channel —
``user_id`` is fixed to the topic name. Use a private topic protected
by a read token for any real trust boundary.

### class NtfyAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 11（公开 5）

ntfy adapter.

Subscribes to a topic via HTTP streaming (``/json`` endpoint) and
publishes replies via HTTP POST. No external SDK — only httpx.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to ntfy by starting the streaming subscription task.

#### async def `disconnect(self) -> None`

Disconnect from ntfy.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Publish a message to the configured publish topic.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

ntfy does not support typing indicators.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return basic info about an ntfy topic.


### 顶层函数

#### def `check_requirements() -> bool`

Check whether the ntfy adapter is installable and minimally configured.

Reads ``NTFY_TOPIC`` directly to avoid the cost of a full
``load_gateway_config()`` (which also writes to ``os.environ``) on
every pre-flight check.

#### def `validate_config(config) -> bool`

Validate that the configured ntfy platform has a topic set.

#### def `is_connected(config) -> bool`

Check whether ntfy is configured (env or config.yaml).

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system at startup.


## plugins.platforms.photon.__init__

### 模块文档

Photon Spectrum (iMessage) platform plugin entry point.

## plugins.platforms.photon.adapter

### 模块文档

Photon Spectrum (iMessage) platform adapter for Hermes Agent.

Both directions of traffic flow through a small supervised Node sidecar
(see ``sidecar/index.mjs``) that runs the ``spectrum-ts`` SDK — the SDK is
TypeScript-only and there is no public HTTP message API, so a sidecar is
unavoidable.

Inbound:
    The SDK's ``app.messages`` is a long-lived **gRPC** stream. The sidecar
    serializes each message to a normalized JSON event and streams it to this
    adapter over a loopback ``GET /inbound`` (NDJSON). A background task here
    consumes that stream, dedupes on ``messageId``, and dispatches a
    ``MessageEvent`` to the gateway via ``BasePlatformAdapter.handle_message``.
    No webhook, no public URL, no signing secret.

Outbound:
    ``send`` / ``send_typing`` are loopback POSTs to the sidecar's control
    endpoints, authenticated with a shared bearer token.  Outbound media
    (images, voice notes, video, documents) goes through spectrum-ts'
    ``attachment()`` / ``voice()`` content builders via the sidecar's
    ``/send-attachment`` endpoint.

### class PhotonAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 44（公开 17）

Bidirectional bridge to Photon Spectrum via the Node spectrum-ts sidecar.

Inbound: consume the sidecar's ``/inbound`` gRPC stream.
Outbound: loopback POSTs to the sidecar's control channel.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_animation(self, chat_id: str, animation_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

#### async def `stop_typing(self, chat_id: str) -> None`

#### async def `add_reaction(self, chat_id: str, emoji: str, message_id: Optional[str] = None) -> Dict[str, Any]`

Tapback ``emoji`` onto a message in ``chat_id``.

Without ``message_id``, targets the chat's most recent inbound
message (typically the one the agent is responding to). iMessage
maps ❤️👍👎😂‼️❓ to native tapbacks; anything else uses Apple's
custom-emoji reaction.

#### async def `remove_reaction(self, chat_id: str, message_id: Optional[str] = None) -> Dict[str, Any]`

Retract our tapback from a message (best-effort).

#### async def `on_processing_start(self, event: MessageEvent) -> None`

Tapback 👀 on the triggering message while the agent works.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Swap the 👀 progress tapback for a 👍/👎 result.

Remove-then-add rather than a bare replace: deterministic whether the
platform replaces a sender's previous tapback or stacks them, and it
keeps the sidecar's reaction-handle slot coherent.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return whatever we know about a Spectrum space id.

Photon's ``space.id`` is opaque; the inbound event also carries the
DM/group type, but here we only have the id, so infer conservatively.

#### def `format_message(self, content: str) -> str`


### 顶层函数

#### def `check_requirements() -> bool`

Return True when both Python deps and the Node sidecar are available.

#### def `validate_config(cfg: PlatformConfig) -> bool`

#### def `is_connected(cfg: PlatformConfig) -> bool`

#### def `register(ctx) -> None`

Called by the Hermes plugin loader at startup.


## plugins.platforms.photon.auth

### 模块文档

Photon Dashboard API client + device-code login flow.

This module is pure Python — it intentionally does not depend on
``spectrum-ts``.  Every management-plane operation (login, find/create
project, rotate the project secret, register a user, list the assigned
iMessage line) talks to Photon's **Dashboard API** on a single host,
exactly like the official Photon CLI (``photon-hq/cli``):

    Dashboard API   https://app.photon.codes/api/...
                    OAuth 2.0 device flow, Bearer access token

A Photon project has a single identifier: the dashboard ``id`` *is* the
Spectrum Cloud project id. They used to diverge (a separate
``spectrumProjectId`` field), but the dashboard unified them — every
project is created with matching ids and the pre-existing diverged rows
were backfilled so ``project.id == spectrumProjectId`` everywhere
(dashboard ENG-1582). Spectrum is always enabled and provisioned at
create-time, so there is no enable/toggle step anymore.

The ``spectrum-ts`` SDK (run by the Node sidecar) authenticates to Spectrum
Cloud with ``(id, projectSecret)`` — the same ``id`` used in Dashboard API
paths — which we persist as ``PHOTON_PROJECT_ID`` for the runtime.

Credential storage mirrors every other Hermes channel:

    * runtime SDK creds  -> ``~/.hermes/.env``  (``PHOTON_PROJECT_ID`` =
      project id, ``PHOTON_PROJECT_SECRET``) via ``save_env_value``
    * management metadata -> ``~/.hermes/auth.json`` under
      ``credential_pool.photon`` (device token),
      ``credential_pool.photon_project`` (dashboard id, spectrum id, name), and
      ``credential_pool.photon_user`` (operator number + assigned text line)

Reference: https://github.com/photon-hq/cli and
https://photon.codes/docs/api-reference/device-login/request-device-+-user-code

### class PhotonDashboardAuthError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Raised when Photon rejects a device-flow token for the dashboard API.


### class DeviceCode

> 继承: `object` ｜ 方法数: 0（公开 0）


### 顶层函数

#### def `load_photon_token() -> Optional[str]`

Return the device-flow bearer token stored by ``login()`` or ``None``.

#### def `store_photon_token(token: str) -> None`

Persist a dashboard bearer token under ``credential_pool.photon``.

#### def `load_project_credentials() -> Tuple[Optional[str], Optional[str]]`

Return the runtime SDK creds ``(spectrum_project_id, project_secret)``.

Precedence: process env (``~/.hermes/.env`` is loaded into the gateway's
environment at startup) wins, then ``auth.json`` for offline / status
use.  This is the pair the Node sidecar feeds to ``spectrum-ts``; the id
is the unified project id (dashboard id == spectrumProjectId).

#### def `load_dashboard_project_id() -> Optional[str]`

Return the project id used for management API calls.

Post-unification the dashboard id and the Spectrum id are the same value,
so we prefer the stored ``spectrum_project_id``: for pre-backfill installs
the old ``dashboard_project_id`` is the diverged id that the unification
rewrote (it now 404s), while the Spectrum id always matches the live row.
Falls back to the legacy keys for older records.

#### def `store_project_credentials(spectrum_project_id: str, project_secret: str, dashboard_project_id: Optional[str] = None, name: Optional[str] = None) -> None`

Persist project credentials to both .env (runtime) and auth.json (mgmt).

The runtime SDK creds land in ``~/.hermes/.env`` via the same
``save_env_value`` helper every other channel uses, so the gateway picks
them up from the environment with zero adapter changes.  A copy of the
non-secret ids (plus the secret, for offline ``status``) is written to
``auth.json`` so management commands work even when ``.env`` hasn't been
loaded into the current process.

#### def `store_user_numbers(phone_number: Optional[str] = None, assigned_phone_number: Optional[str] = None, user_id: Optional[str] = None, dashboard_project_id: Optional[str] = None) -> None`

Persist non-secret Photon user numbers for offline ``status`` output.

#### def `request_device_code(client_id: str = DEFAULT_CLIENT_ID, scope: Optional[str] = DEFAULT_SCOPE) -> DeviceCode`

POST ``/api/auth/device/code`` and return the device + user codes.

**异常**: `RuntimeError`

#### def `poll_for_token(code: DeviceCode, client_id: str = DEFAULT_CLIENT_ID, timeout: Optional[int] = None, interval: Optional[int] = None, on_pending: Optional[Callable[[], None]] = None) -> str`

Poll ``/api/auth/device/token`` until the user approves.

Mirrors the official CLI's polling loop: sleep first, then poll;
``authorization_pending`` keeps the interval, ``slow_down`` adds 5s,
HTTP 429 adds 10s, and ``access_denied`` / ``expired_token`` abort.

The bearer token comes from the response body's top-level
``access_token`` (better-auth device-grant shape), with
``session.access_token`` and the ``set-auth-token`` header kept as
fallbacks for API drift.

**异常**: `TimeoutError`, `RuntimeError`

#### def `validate_photon_token(token: str) -> Dict[str, Any]`

Verify a device-flow token is usable for dashboard project APIs.

The device flow can return a token that authenticates the Better Auth
session lookup but is rejected by the project APIs.  Validate against
``/api/auth/get-session`` and ``/api/projects/`` so we fail loudly at
login instead of saving a token that 404s/401s downstream.

**异常**: `PhotonDashboardAuthError`

#### def `login_device_flow(client_id: str = DEFAULT_CLIENT_ID, open_browser: bool = True, on_user_code: Optional[Callable[['DeviceCode'], None]] = None) -> str`

Run the full device-code login flow and persist the token.

Returns the bearer token.  ``on_user_code`` receives the
:class:`DeviceCode` so callers can print it + optionally open a browser.

#### def `get_session(token: str) -> Dict[str, Any]`

GET ``/api/auth/get-session`` — confirm the token + fetch the user.

**异常**: `RuntimeError`

#### def `list_projects(token: str) -> List[Dict[str, Any]]`

GET ``/api/projects`` — return the caller's projects.

**异常**: `RuntimeError`

#### def `find_project_by_name(token: str, name: str) -> Optional[Dict[str, Any]]`

Return the first project whose name matches (case-insensitive).

#### def `create_project(token: str, name: str = DEFAULT_PROJECT_NAME, location: str = 'United States') -> Dict[str, Any]`

POST ``/api/projects`` and return ``{success, id}``.

Spectrum is always provisioned at create-time, so the request body no
longer carries a ``spectrum`` flag (the field was dropped from the API).

**异常**: `RuntimeError`

#### def `regenerate_project_secret(token: str, project_id: str) -> str`

POST ``/api/projects/{id}/regenerate-secret`` → the new project secret.

This is the only way to read a project secret (the dashboard shows it
exactly once), so callers should persist the returned value immediately.

**异常**: `RuntimeError`

#### def `list_users(project_id: str, project_secret: str) -> List[Dict[str, Any]]`

GET Spectrum Cloud ``/projects/{id}/users/`` → ``SpectrumUser[]``.

**异常**: `RuntimeError`

#### def `find_user_by_phone(project_id: str, project_secret: str, phone_number: str) -> Optional[Dict[str, Any]]`

Return an existing Spectrum user with the given phone number, or None.

#### def `create_user(project_id: str, project_secret: str, phone_number: str, first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None, send_invite: bool = False) -> Dict[str, Any]`

POST Spectrum Cloud ``/projects/{id}/users/`` and return the user.

**异常**: `RuntimeError`, `ValueError`

#### def `register_user_if_absent(project_id: str, project_secret: str, phone_number: str, first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None) -> Tuple[Dict[str, Any], bool]`

Idempotently register a Spectrum user.

Returns ``(user, created)`` — ``created`` is False when a user with the
same phone number already exists (the official CLI does no dedup, so we
add it here to make ``setup`` safely re-runnable).

#### def `user_assigned_line(user: Optional[Dict[str, Any]]) -> Optional[str]`

Return the iMessage number a Spectrum user is assigned to text on.

This is the user's ``assignedPhoneNumber`` (the dashboard's "TEXTS ON"
column) — i.e. the number to text to reach the agent, as opposed to the
user's own ``phoneNumber``. On shared-number plans there is no dedicated
entry in ``/lines``, so this per-user field is the source of truth.
Returns ``None`` when unset (e.g. a freshly created, not-yet-assigned user).

#### def `load_user_numbers() -> Tuple[Optional[str], Optional[str]]`

Return ``(operator_phone_number, assigned_phone_number)`` for status.

#### def `refresh_user_numbers(project_id: str, project_secret: str) -> Tuple[Optional[str], Optional[str]]`

Refresh cached user numbers from Photon without provisioning anything.

#### def `list_lines(token: str, project_id: str) -> List[Dict[str, Any]]`

GET ``/api/projects/{id}/lines`` → ``[{id, platform, phoneNumber, status}]``.

**异常**: `RuntimeError`

#### def `add_line(token: str, project_id: str, platform: str = 'imessage') -> Dict[str, Any]`

POST ``/api/projects/{id}/lines`` to provision a new line.

**异常**: `RuntimeError`

#### def `get_imessage_line(token: str, project_id: str, create_if_missing: bool = True) -> Optional[Dict[str, Any]]`

Return the project's iMessage line (the number to text the agent).

If none exists and ``create_if_missing`` is set, provision one.  Returns
``None`` if there is no line and provisioning failed.

#### def `print_credential_summary(emit: Any = print) -> None`

Pretty-print the credential status table via the *emit* callback.

Every secret-bearing read is reduced to a display literal inside this
function (``"✓ stored"`` / ``"✗ missing"`` / a non-secret id); the
callback only ever receives the assembled banner string, so no tainted
value escapes into the caller's scope.

#### def `credential_summary() -> Dict[str, str]`

Return a fully pre-formatted credential status dict (no raw secrets).


## plugins.platforms.photon.cli

### 模块文档

``hermes photon ...`` CLI subcommands — registered by the plugin via
``ctx.register_cli_command()``.

Subcommands:

    setup              full first-time setup (device login + project + user + sidecar)
    status             show login + project + sidecar dep state
    install-sidecar    npm install inside plugins/platforms/photon/sidecar/
    telemetry          show or toggle Spectrum SDK telemetry (on/off)

The device-code login runs automatically as the first step of ``setup``;
there is no standalone ``login`` verb (matching how every other Hermes
gateway channel onboards through a single setup surface).

Photon uses the spectrum-ts gRPC stream for inbound — there is no webhook
to register, so there are no webhook subcommands.

### 顶层函数

#### def `register_cli(parser: argparse.ArgumentParser) -> None`

Wire up `hermes photon ...` subcommands.

#### def `dispatch(args: argparse.Namespace) -> int`

#### def `gateway_setup() -> None`

Run Photon first-time setup from the `hermes gateway setup` wizard.


## plugins.platforms.raft.__init__


## plugins.platforms.raft.adapter

### 模块文档

Raft channel platform adapter.

Starts a local wake endpoint, spawns ``raft agent bridge`` as a child process,
and injects content-free wake hints into Hermes' normal gateway session pipeline.
Token and port are auto-generated when not provided via env/config.
The bridge remains responsible for Raft message cursors and body materialization;
the agent uses the Raft CLI according to the Raft manual.

### class ActivityQueue

> 继承: `object` ｜ 方法数: 4（公开 3）

Bounded at-most-once queue for Raft external activity telemetry.

#### def `__init__(cap: int = DEFAULT_ACTIVITY_QUEUE_CAP)`

#### def `push(self, event: Dict[str, Any]) -> None`

#### def `drain(self, max_events: int = 200) -> Dict[str, Any]`

#### property `size(self) -> int`


### class RaftAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 17（公开 7）

Local HTTP endpoint for Raft channel bridge delivery.

#### def `__init__(config: PlatformConfig)`

#### property `runtime_session(self) -> str`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### async def `handle_message(self, event: MessageEvent) -> None`

Accept Raft wake hints without interrupting an active Hermes turn.

#### def `report_activity(self, event: Dict[str, Any]) -> None`


### 顶层函数

#### def `check_raft_requirements() -> bool`

Check if Raft channel dependencies are available.

Intentionally silent on failure — this is a passive probe registered as
the platform's ``check_fn``. It is called on every
``load_gateway_config()`` (message handling, display lookups, agent
turns), so logging here floods the logs for every user without the
``raft`` CLI installed. The caller (``gateway/platform_registry.py``
``create_adapter()``) emits its own warning when requirements are not met
and an adapter is actually requested. This matches the convention used by
other platform adapters (e.g. ``teams/adapter.py``).

#### def `interactive_setup() -> None`

Interactive ``hermes gateway setup`` flow for the Raft platform.

Lazy-imports CLI helpers so the plugin stays importable in gateway runtime
and test contexts. The flow persists ``RAFT_PROFILE`` to the Hermes env
file so the Raft adapter auto-enables after a gateway restart.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.simplex.__init__


## plugins.platforms.simplex.adapter

### 模块文档

SimpleX Chat platform adapter (Hermes plugin).

Connects to a simplex-chat daemon running in WebSocket mode.
Inbound messages arrive via a persistent WebSocket connection.
Outbound messages use the same WebSocket with JSON commands.

This adapter ships as a Hermes platform plugin under
``plugins/platforms/simplex/``. The Hermes plugin loader scans the
directory at startup, calls ``register(ctx)``, and the platform
becomes available to ``gateway/run.py`` and ``tools/send_message_tool``
through the registry — no edits to core files are required.

SimpleX chat daemon setup:
    simplex-chat -p 5225          # start daemon on port 5225
    # or via Docker:
    # docker run -p 5225:5225 simplexchat/simplex-chat-cli -p 5225

Required environment variables:
    SIMPLEX_WS_URL             WebSocket URL of the daemon
                               (default: ws://127.0.0.1:5225)

Optional environment variables:
    SIMPLEX_ALLOWED_USERS      Comma-separated allowlist. Each entry may be
                               either a numeric contactId (stable across
                               renames; visible via `/contacts` in the CLI)
                               or a contact display name (what the SimpleX
                               UI shows). Both forms are accepted.
    SIMPLEX_ALLOW_ALL_USERS    Set 'true' to allow all contacts
    SIMPLEX_AUTO_ACCEPT        Set 'false' to disable contact-request auto-accept
                               (default: 'true')
    SIMPLEX_GROUP_ALLOWED      Comma-separated group IDs to monitor, or '*'
                               for any group. Omit to disable groups entirely.
    SIMPLEX_HOME_CHANNEL       Default contact/group ID for cron delivery
    SIMPLEX_HOME_CHANNEL_NAME  Human label for the home channel
    HERMES_SIMPLEX_TEXT_BATCH_DELAY
                               Quiet-period seconds (default: 0.8) used to
                               concatenate rapid-fire inbound text messages
                               into a single MessageEvent — same pattern as
                               Telegram's text batching.

The ``websockets`` Python package is imported lazily — the plugin is
discoverable and ``hermes setup`` can describe it even when websockets is
not installed. ``check_requirements()`` returns False until the package
is present, so the gateway will not attempt to instantiate the adapter.

### class SimplexAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 23（公开 10）

SimpleX Chat adapter using the simplex-chat daemon WebSocket API.

Instantiated by the ``adapter_factory`` passed to
``ctx.register_platform()`` in :func:`register`.

#### def `__init__(config: PlatformConfig, **kwargs)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to the simplex-chat daemon and start the WebSocket listener.

#### async def `disconnect(self) -> None`

Stop WebSocket listener and clean up.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a text message.

If *content* contains ``MEDIA:<path>`` tags (embedded by TTS / audio
tools to signal file attachments), they are stripped from the text
body and sent as native voice notes or documents.

Groups use the structured ``/_send #<id> json [...]`` form
because the bracket chat-command syntax (``#[<id>] text``) is
parsed by the daemon as a display-name lookup, which silently
drops when the group's display name isn't the literal ID. DMs
use the simple ``@<id> text`` form which has always worked in
production.

The call is fire-and-forget at the WebSocket level: the daemon
doesn't always return a corrId reply for chat commands, and
waiting for one would serialise all outbound traffic behind a
30-second timeout.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, **kwargs) -> SendResult`

Send an image. Supports ``file://`` URLs and ``http(s)://`` URLs.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a local image file via SimpleX.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a video file via SimpleX (as a file attachment).

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, filename: Optional[str] = None, **kwargs) -> SendResult`

Send a document/file attachment.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, duration: int = 0, **kwargs) -> SendResult`

Send an audio file as a SimpleX voice note (plays inline).

SimpleX distinguishes a generic file attachment (``type: "file"``)
from an inline voice note (``type: "voice"``). ``/f`` would deliver
a downloadable file; the structured ``/_send`` form with
``msgContent.type == "voice"`` produces the voice-note player.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

SimpleX has no typing-indicator API — no-op.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return basic chat info.


### 顶层函数

#### def `check_requirements() -> bool`

Plugin gate: require SIMPLEX_WS_URL AND the websockets package.

Returning False keeps the platform out of ``get_connected_platforms()``
so the gateway never instantiates the adapter when the dependency is
missing or no daemon URL is configured.

#### def `validate_config(config) -> bool`

Validate that the platform config has enough info to connect.

#### def `is_connected(config) -> bool`

Check whether SimpleX is configured (env or config.yaml).

#### def `interactive_setup() -> None`

Minimal stdin wizard for ``hermes setup gateway`` → SimpleX.

Prompts for the WebSocket URL and the optional allowlist / groups /
auto-accept / home channel. Writes to ``~/.hermes/.env`` via
``hermes_cli.config``.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system at startup.


## plugins.platforms.slack.__init__


## plugins.platforms.slack.adapter

### 模块文档

Slack platform adapter.

Uses slack-bolt (Python) with Socket Mode for:
- Receiving messages from channels and DMs
- Sending responses back
- Handling slash commands
- Thread support

### class SlackAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 89（公开 20）

Slack bot adapter using Socket Mode.

Requires two tokens:
  - SLACK_BOT_TOKEN (xoxb-...) for API calls
  - SLACK_APP_TOKEN (xapp-...) for Socket Mode connection

Features:
  - DMs and channel messages (mention-gated in channels)
  - Thread support
  - File/image/audio attachments
  - Slash commands (/hermes)
  - Typing indicators (not natively supported by Slack bots)

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to Slack via Socket Mode.

#### async def `create_handoff_thread(self, parent_chat_id: str, name: str) -> Optional[str]`

Create a Slack thread anchor for a session handoff.

Slack threads are anchored to a parent message (``thread_ts``), not
a channel-level construct. So we post a seed message into the home
channel and return its ``ts`` — the watcher uses that as the
``thread_id`` for subsequent sends.

Returns the seed message ts as a string, or ``None`` on failure.

#### async def `disconnect(self) -> None`

Disconnect from Slack.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a message to a Slack channel or DM.

#### async def `send_private_notice(self, chat_id: str, user_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a Slack ephemeral message visible only to one user.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Edit a previously sent Slack message.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Show a typing/status indicator using assistant.threads.setStatus.

Displays "is thinking..." next to the bot name in a thread, or the
platform's ``typing_status_text`` config value when set.
Requires the assistant:write or chat:write scope.
Auto-clears when the bot sends a reply to the thread.

#### async def `stop_typing(self, chat_id: str, metadata = None) -> None`

Clear the assistant thread status indicator.

#### async def `send_multiple_images(self, chat_id: str, images: List[Tuple[str, str]], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send a batch of images as a single Slack message with multiple file uploads.

Uses ``files_upload_v2`` with its ``file_uploads`` parameter so all
images show up attached to one ``initial_comment`` message instead
of N separate messages. Falls back to the base per-image loop on
any failure.

The batch limit is 10 file uploads per call (Slack server-side cap).

#### def `format_message(self, content: str) -> str`

Convert standard markdown to Slack mrkdwn format.

Protected regions (code blocks, inline code) are extracted first so
their contents are never modified.  Standard markdown constructs
(headers, bold, italic, links) are translated to mrkdwn syntax.

#### async def `on_processing_start(self, event: MessageEvent) -> None`

Add an in-progress reaction when message processing begins.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Swap the in-progress reaction for a final success/failure reaction.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a local image file to Slack by uploading it.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an image to Slack by uploading the URL as a file.

**异常**: `ValueError`

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send an audio file to Slack.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a video file to Slack.

**异常**: `last_exc`

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a document/file attachment to Slack.

**异常**: `last_exc`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Get information about a Slack channel.

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[Dict[str, Any]] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Send a Block Kit approval prompt with interactive buttons.

The buttons call ``resolve_gateway_approval()`` to unblock the waiting
agent thread — same mechanism as the text ``/approve`` flow.

#### async def `send_slash_confirm(self, chat_id: str, title: str, message: str, session_key: str, confirm_id: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a Block Kit three-option slash-command confirmation prompt.


### 顶层函数

#### def `check_slack_requirements() -> bool`

Check if Slack dependencies are available.

Lazy-installs slack-bolt/slack-sdk via ``tools.lazy_deps.ensure("platform.slack")``
on first call if not present. Rebinds all module-level globals on success.

#### def `interactive_setup() -> None`

Guide the user through Slack bot setup.

Mirrors Discord's ``interactive_setup`` shape: lazy-imports CLI helpers so
the plugin's import surface stays small, generates and writes the Slack app
manifest, prompts for the bot + app tokens, captures an allowlist, and
offers to set a home channel. Replaces ``hermes_cli/setup.py::_setup_slack``.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.slack.block_kit

### 模块文档

Render agent markdown into Slack Block Kit blocks.

Opt-in (``slack.extra.rich_blocks: true``) alternative to the flat mrkdwn
``text`` payload produced by :meth:`SlackAdapter.format_message`.  Block Kit
gives us real structural primitives — section headers, dividers, and true
*nested* lists via ``rich_text`` — that plain mrkdwn can only approximate.

Design constraints (why this module is deliberately conservative):

* **Markdown pipe-tables render as native ``table`` blocks** — real grid
  cells with per-column alignment and inline-formatted ``rich_text`` content.
  A table that exceeds Slack's limits (100 rows / 20 cols / 10k aggregate
  cell chars) or won't parse falls back to aligned monospace
  ``rich_text_preformatted`` so a large table never breaks the message.
* **Slack caps a message at 50 blocks** and a ``section``/text object at 3000
  characters.  :func:`render_blocks` enforces both and, if the content simply
  cannot be expressed within them, returns ``None`` so the caller falls back
  to the plain-text path.  A rich render is a nice-to-have; it must never lose
  a message.
* **Every blocks payload MUST ship a ``text`` fallback.**  Slack uses it for
  notifications, screen readers, and old clients.  This module only builds the
  ``blocks`` list; the adapter pairs it with the existing mrkdwn string.

The renderer never raises: any unexpected input degrades to ``None`` (caller
uses plain text).  It is a pure function of its input — no Slack client, no
adapter state — so it is trivially unit-testable.

### 顶层函数

#### def `render_blocks(markdown: str, mrkdwn_fn = None) -> Optional[List[Block]]`

Convert agent markdown to a Slack Block Kit ``blocks`` list.

Args:
    markdown: The agent's response text (standard markdown).
    mrkdwn_fn: Optional callable converting a markdown paragraph to Slack
        mrkdwn for ``section`` blocks (the adapter passes
        ``format_message``).  When ``None``, the raw paragraph text is used.

Returns:
    A list of Block Kit block dicts, or ``None`` when the content is empty,
    exceeds Slack's structural limits, or hits an unexpected shape — the
    caller then falls back to the flat ``text`` payload.  Never raises.


## plugins.platforms.sms.__init__


## plugins.platforms.sms.adapter

### 模块文档

SMS (Twilio) platform adapter.

Connects to the Twilio REST API for outbound SMS and runs an aiohttp
webhook server to receive inbound messages.

Shares credentials with the optional telephony skill — same env vars:
  - TWILIO_ACCOUNT_SID
  - TWILIO_AUTH_TOKEN
  - TWILIO_PHONE_NUMBER  (E.164 from-number, e.g. +15551234567)

Gateway-specific env vars:
  - SMS_WEBHOOK_PORT     (default 8080)
  - SMS_WEBHOOK_HOST     (default 127.0.0.1)
  - SMS_WEBHOOK_URL      (public URL for Twilio signature validation — required)
  - SMS_INSECURE_NO_SIGNATURE  (true to disable signature validation — dev only)
  - SMS_ALLOWED_USERS    (comma-separated E.164 phone numbers)
  - SMS_ALLOW_ALL_USERS  (true/false)
  - SMS_HOME_CHANNEL     (phone number for cron delivery)

### class SmsAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 11（公开 5）

Twilio SMS <-> Hermes gateway adapter.

Each inbound phone number gets its own Hermes session (multi-tenant).
Replies are always sent from the configured TWILIO_PHONE_NUMBER.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

#### def `format_message(self, content: str) -> str`

Strip markdown — SMS renders it as literal characters.


### 顶层函数

#### def `check_sms_requirements() -> bool`

Check if SMS adapter dependencies are available.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.teams.__init__


## plugins.platforms.teams.adapter

### 模块文档

Microsoft Teams platform adapter for Hermes Agent.

Uses the microsoft-teams-apps SDK for authentication and activity processing.
Runs an aiohttp webhook server to receive messages from Teams.
Proactive messaging (send, typing) uses the SDK's App.send() method.

Requires:
    pip install microsoft-teams-apps aiohttp
    TEAMS_CLIENT_ID, TEAMS_CLIENT_SECRET, and TEAMS_TENANT_ID env vars

Configuration in config.yaml:
    platforms:
      teams:
        enabled: true
        extra:
          client_id: "your-client-id"      # or TEAMS_CLIENT_ID env var
          client_secret: "your-secret"      # or TEAMS_CLIENT_SECRET env var
          tenant_id: "your-tenant-id"       # or TEAMS_TENANT_ID env var
          port: 3978                        # or TEAMS_PORT env var

### class TeamsSummaryWriter

> 继承: `object` ｜ 方法数: 11（公开 1）

Pipeline-facing Teams outbound delivery surface.

This stays inside the existing Teams platform plugin so the meeting-pipeline
PR can reuse one Teams integration surface instead of introducing a second
adapter elsewhere in the gateway core.

#### def `__init__(platform_config: PlatformConfig | None = None, graph_client: Any | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None`

#### async def `write_summary(self, payload: Any, config: dict[str, Any] | None, existing_record: Optional[dict[str, Any]] = None) -> dict[str, Any]`

**异常**: `ValueError`


### class TeamsAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 17（公开 11）

Microsoft Teams adapter using the microsoft-teams-apps SDK.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[Dict[str, Any]] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Send an Adaptive Card approval prompt with Allow/Deny buttons.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_typing(self, chat_id: str, metadata: Optional[Dict[str, Any]] = None) -> None`

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

#### async def `get_chat_info(self, chat_id: str) -> dict`


### 顶层函数

#### def `check_requirements() -> bool`

Return True when all Teams dependencies and credentials are present.

#### def `validate_config(config) -> bool`

Return True when the config has the minimum required credentials.

#### def `is_connected(config) -> bool`

Check whether Teams is configured (env or config.yaml).

#### def `check_teams_requirements() -> bool`

Ensure the Teams SDK is importable, lazy-installing it on first use.

Lazy-installs ``microsoft-teams-apps`` via
``tools.lazy_deps.ensure("platform.teams")`` if not present, then rebinds
all module-level SDK globals on success. Returns True once the SDK (and
aiohttp) are importable, False if they couldn't be installed/imported.

#### def `interactive_setup() -> None`

Guide the user through Teams setup using the Teams CLI.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.telegram.__init__


## plugins.platforms.telegram.adapter

### 模块文档

Telegram platform adapter.

Uses python-telegram-bot library for:
- Receiving messages from users/groups
- Sending responses back
- Handling media and commands

### class TelegramAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 184（公开 32）

Telegram bot adapter.

Handles:
- Receiving messages from users and groups
- Sending responses with Telegram markdown
- Forum topics (thread_id support)
- Media messages

#### property `message_len_fn(self)`

Telegram measures message length in UTF-16 code units.

#### def `__init__(config: PlatformConfig)`

#### def `prefers_fresh_final_streaming(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool`

Whether to replace a streamed preview with a fresh rich final.

Disabled for Telegram. The fresh-final path briefly shows two copies of
the final answer, then deletes the streaming preview after the rich send
succeeds — it looks like duplicate delivery at the end of every streamed
turn (the reason #46206 reverted it).  Rich finalize is instead handled
by editing the existing preview in place via Bot API 10.1's
``editMessageText`` ``rich_message`` parameter (see
:meth:`_try_edit_rich`), so no fresh re-send / delete is needed.

#### def `streaming_overflow_limit(self) -> Optional[int]`

Allow the stream consumer to accumulate up to the rich-message cap
before splitting, so a reply that fits one ``sendRichMessage`` /
``sendRichMessageDraft`` isn't fragmented at the 4,096 MarkdownV2 limit.

Gated on the same rich capability as the send path (minus the
content-length check — raising that cap is the whole point): rich not
latched off and the bot exposes an async ``do_api_request``.  Returns
``None`` (→ legacy 4,096 limit) when rich isn't available, so non-rich
streams split exactly as before.

#### async def `create_handoff_thread(self, parent_chat_id: str, name: str) -> Optional[str]`

Create a forum topic for a session handoff.

Works for DM topics (Bot API 9.4+, requires user to enable Topics
in their chat with the bot) and forum supergroups. Returns the
``message_thread_id`` as a string, or ``None`` on failure.

#### async def `ensure_dm_topic(self, chat_id: str, topic_name: str, force_create: bool = False) -> Optional[str]`

Return a private DM topic thread id, creating and persisting it if needed.

#### async def `rename_dm_topic(self, chat_id: int, thread_id: int, name: str) -> None`

Rename a forum topic in a private (DM) chat.

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to Telegram via polling or webhook.

By default, uses long polling (outbound connection to Telegram).
If ``TELEGRAM_WEBHOOK_URL`` is set, starts an HTTP webhook server
instead.  Webhook mode is useful for cloud deployments (Fly.io,
Railway) where inbound HTTP can wake a suspended machine.

``is_reconnect`` distinguishes a cold first boot (False — drop any
stale Bot API queue) from a watcher reconnect after a prolonged
outage (True — preserve the updates Telegram queued while the bot
was offline, otherwise every message sent during the outage is
silently lost). The in-process network-error ladder and the
409-conflict handler already pass ``drop_pending_updates=False``
for the same reason; bootstrap follows suit on the reconnect path.

Env vars for webhook mode::

    TELEGRAM_WEBHOOK_URL    Public HTTPS URL (e.g. https://app.fly.dev/telegram)
    TELEGRAM_WEBHOOK_PORT   Local listen port (default 8443)
    TELEGRAM_WEBHOOK_SECRET Secret token for update verification

**异常**: `RuntimeError`, `OSError`

#### async def `disconnect(self) -> None`

Stop polling/webhook, cancel pending delayed deliveries, and disconnect.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a message to a Telegram chat.

#### async def `send_or_update_status(self, chat_id: str, status_key: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a status message, or edit the previous one with the same key.

Issue #30045: progress/status callbacks (context-pressure, lifecycle,
compression, etc.) used to append a fresh bubble on every call. With
this method, the first call sends and the message id is remembered;
subsequent calls with the same (chat_id, status_key) edit that same
message in place. If the edit fails (message deleted, too old, etc.)
we drop the cached id and send fresh.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Edit a previously sent Telegram message.

Telegram caps single-message text at 4096 UTF-16 codeunits.  Streaming
replies that grow past this limit must NOT be silently truncated and
must NOT return failure (the consumer would re-send and create a
duplicate).  Instead this method split-and-delivers: edit the
existing message with the first chunk and send the rest as
continuation messages, returning the final chunk's id so subsequent
edits target the most recent visible message.

#### async def `delete_message(self, chat_id: str, message_id: str) -> bool`

Delete a previously sent Telegram message.

Used by the stream consumer's fresh-final cleanup path (ported
from openclaw/openclaw#72038) to remove long-lived preview
messages after sending the completed reply as a fresh message.
Telegram's Bot API ``deleteMessage`` works for bot-posted
messages in the last 48 hours.  Failures are non-fatal — the
caller leaves the preview in place and logs at debug level.

#### def `supports_draft_streaming(self, chat_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool`

Telegram supports sendMessageDraft for private chats only.

Bot API 9.5 (March 2026) opened ``sendMessageDraft`` to all bots
unconditionally for private (DM) chats.  Groups, supergroups, and
channels still rely on the edit-based path.

We additionally require ``self._bot`` to expose ``send_message_draft``
(added to python-telegram-bot in 22.6); older PTB installs gracefully
fall back to the edit path even on DMs.

#### async def `send_draft(self, chat_id: str, draft_id: int, content: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Stream a partial message via Telegram's native draft API.

Uses ``sendRichMessageDraft`` (Bot API 10.1) with the raw markdown when
rich messages are enabled and supported, otherwise the plain-text
``sendMessageDraft``. The Bot API animates the preview when the same
``draft_id`` is reused across consecutive calls in the same chat.  When
the response finishes, the caller sends the final text via the normal
``send`` path; the draft preview clears naturally on the client
(Telegram has no Bot API to "promote" a draft to a real message — the
final ``sendMessage``/``sendRichMessage`` is what the user receives in
their history).

#### async def `send_update_prompt(self, chat_id: str, prompt: str, default: str = '', session_key: str = '', metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an inline-keyboard update prompt (Yes / No buttons).

Used by the gateway ``/update`` watcher when ``hermes update --gateway``
needs user input (stash restore, config migration).

#### async def `send_exec_approval(self, chat_id: str, command: str, session_key: str, description: str = 'dangerous command', metadata: Optional[Dict[str, Any]] = None, allow_permanent: bool = True, smart_denied: bool = False) -> SendResult`

Send an inline-keyboard approval prompt with interactive buttons.

The buttons call ``resolve_gateway_approval()`` to unblock the waiting
agent thread — same mechanism as the text ``/approve`` flow.

#### async def `send_slash_confirm(self, chat_id: str, title: str, message: str, session_key: str, confirm_id: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Render a three-button slash-command confirmation prompt.

#### async def `send_clarify(self, chat_id: str, question: str, choices: Optional[list], clarify_id: str, session_key: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Render a clarify prompt with one inline button per choice.

Multi-choice mode (``choices`` non-empty): renders one button per
option plus a final "✏️ Other (type answer)" button.  Picking the
"Other" button flips the entry into text-capture mode so the next
message becomes the response.

Open-ended mode (``choices`` empty): renders the question as plain
text — no buttons.  The next message in the session is captured by
the gateway's text-intercept and resolves the clarify.

#### async def `send_model_picker(self, chat_id: str, providers: list, current_model: str, current_provider: str, session_key: str, on_model_selected, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an interactive inline-keyboard model picker.

Two-step drill-down: provider selection → model selection.
Edits the same message in-place as the user navigates.

#### async def `send_choice_picker(self, chat_id: str, title: str, choices: list, session_key: str, on_choice_selected, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a flat inline-keyboard choice picker (one tap → one value).

Generic single-level companion to ``send_model_picker`` used by
`/reasoning`, `/fast`, and any future finite-choice command. Each
choice dict: ``{"value": str, "label": str, "is_current": bool}``.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send audio as a native Telegram voice message or audio file.

#### async def `send_multiple_images(self, chat_id: str, images: List[tuple], metadata: Optional[Dict[str, Any]] = None, human_delay: float = 0.0) -> None`

Send a batch of images natively via Telegram's media group API.

Telegram's ``send_media_group`` bundles up to 10 photos/videos into
a single album. Larger batches are chunked. Animated GIFs cannot
go into a media group (they require ``send_animation``), so they
are peeled off and sent individually via the base default path.

URL-based photos go into the group directly; local files are
opened as byte streams. On failure the whole batch falls back to
the base adapter's per-image loop.

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a local image file natively as a Telegram photo.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a document/file natively as a Telegram file attachment.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> SendResult`

Send a video natively as a Telegram video message.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an image natively as a Telegram photo.

Tries URL-based send first (fast, works for <5MB images).
Falls back to downloading and uploading as file (supports up to 10MB).

#### async def `send_animation(self, chat_id: str, animation_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send an animated GIF natively as a Telegram animation (auto-plays inline).

#### async def `send_typing(self, chat_id: str, metadata: Optional[Dict[str, Any]] = None) -> None`

Send typing indicator.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Get information about a Telegram chat.

#### def `format_message(self, content: str) -> str`

Convert standard markdown to Telegram MarkdownV2 format.

Protected regions (code blocks, inline code) are extracted first so
their contents are never modified.  Standard markdown constructs
(headers, bold, italic, links) are translated to MarkdownV2 syntax,
and all remaining special characters are escaped.

#### async def `on_processing_start(self, event: MessageEvent) -> None`

Add an in-progress reaction when message processing begins.

#### async def `on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None`

Swap the in-progress reaction for a final success/failure reaction.

Unlike Discord (additive reactions), Telegram's set_message_reaction
replaces all existing reactions in one call — no remove step needed.

On CANCELLED outcomes (e.g. the user runs ``/stop``, or a session is
interrupted mid-flight), we explicitly clear the 👀 in-progress
reaction so it doesn't linger on the user's message indefinitely.
Without this clear, the only way to remove the 👀 was to wait for
another agent run to swap it to 👍/👎 — which never happens if the
cancellation was the last activity in the chat.


### 顶层函数

#### def `check_telegram_requirements() -> bool`

Check if Telegram dependencies are available.

If python-telegram-bot is missing, attempts to lazy-install it via
``tools.lazy_deps.ensure("platform.telegram")``. After a successful
install, re-imports the SDK and flips ``TELEGRAM_AVAILABLE`` to True
so the adapter's class-level type aliases get rebound.

#### def `interactive_setup() -> None`

Configure Telegram bot credentials and allowlist.

Delegates to the existing CLI setup helpers (managed-bot QR onboarding,
token validation, allowlist capture) via lazy import so the full wizard
behavior is preserved without duplicating ~150 lines. Replaces the
_PLATFORMS["telegram"] static dict dispatch in hermes_cli/gateway.py.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.platforms.telegram.telegram_ids

### 模块文档

Helpers for Telegram Bot API chat identifiers.

Telegram's Bot API accepts a ``chat_id`` in two forms: a numeric ID (an int,
e.g. ``123456789`` for a DM or ``-1001234567890`` for a channel/supergroup) or
an ``@username`` string for public channels and groups. Hermes historically
coerced every ``chat_id`` with ``int()``, which crashes on the username form
(``ValueError: invalid literal for int()``). Normalizing here lets numeric IDs
pass through as ints while usernames pass through unchanged — both are valid
values for the Bot API.

### 顶层函数

#### def `normalize_telegram_chat_id(chat_id: Any) -> Union[int, str]`

Return a Bot API-compatible chat_id.

Numeric values (incl. negative channel IDs) are returned as ``int``; any
non-numeric value (e.g. an ``@username``) is returned as a stripped string.
Telegram's Bot API accepts both, so this never raises on a username the way
a bare ``int(chat_id)`` would.

#### def `telegram_chat_id_key(chat_id: Any) -> str`

Stable string key for a chat_id (for dict keys / persisted state).

#### def `looks_like_telegram_username(chat_id: Any) -> bool`

True when the value is an ``@username``-format Telegram chat identifier.

#### def `parse_telegram_username_target(target_ref: Any) -> Union[str, None]`

Return the value when it is an ``@username`` target, else ``None``.


## plugins.platforms.telegram.telegram_network

### 模块文档

Telegram-specific network helpers.

Provides a hostname-preserving fallback transport for networks where
api.telegram.org resolves to an endpoint that is unreachable from the current
host. The transport keeps the logical request host and TLS SNI as
api.telegram.org while retrying the TCP connection against one or more fallback
IPv4 addresses.

### class TelegramFallbackTransport

> 继承: `httpx.AsyncBaseTransport` ｜ 方法数: 3（公开 2）

Retry Telegram Bot API requests via fallback IPs while preserving TLS/SNI.

Requests continue to target https://api.telegram.org/... logically, but on
connect failures the underlying TCP connection is retried against a known
reachable IP. This is effectively the programmatic equivalent of
``curl --resolve api.telegram.org:443:<ip>``.

#### def `__init__(fallback_ips: Iterable[str], **transport_kwargs)`

#### async def `handle_async_request(self, request: httpx.Request) -> httpx.Response`

**异常**: `last_error`, `RuntimeError`

#### async def `aclose(self) -> None`


### 顶层函数

#### def `parse_fallback_ip_env(value: str | None) -> list[str]`

#### def `discover_fallback_ips() -> list[str]`

Auto-discover Telegram API IPs via DNS-over-HTTPS.

Resolves api.telegram.org through Google and Cloudflare DoH and returns all
unique A records.  IPs that match the local system resolver are kept rather
than excluded: in many networks the system-DNS IP is the most reliable path
to api.telegram.org and a transient primary-path failure should be retried
against the same address via the IP-rewrite path before the seed list is
consulted (#14520).  Falls back to a hardcoded seed list only when DoH
yields no usable answers.


## plugins.platforms.wecom.__init__


## plugins.platforms.wecom.adapter

### 模块文档

WeCom (Enterprise WeChat) platform adapter.

Uses the WeCom AI Bot WebSocket gateway for inbound and outbound messages.
The adapter focuses on the core gateway path:

- authenticate via ``aibot_subscribe``
- receive inbound ``aibot_msg_callback`` events
- send outbound markdown messages via ``aibot_send_msg``
- upload outbound media via ``aibot_upload_media_*`` and send native attachments
- best-effort download of inbound image/file attachments for agent context

Configuration in config.yaml:
    platforms:
      wecom:
        enabled: true
        extra:
          bot_id: "your-bot-id"          # or WECOM_BOT_ID env var
          secret: "your-secret"          # or WECOM_SECRET env var
          websocket_url: "wss://openws.work.weixin.qq.com"
          dm_policy: "pairing"           # open | allowlist | disabled | pairing
          allow_from: ["user_id_1"]
          group_policy: "pairing"        # open | allowlist | disabled | pairing
          group_allow_from: ["group_id_1"]
          groups:
            group_id_1:
              allow_from: ["user_id_1"]

### class WeComAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 64（公开 11）

WeCom AI Bot adapter backed by a persistent WebSocket connection.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Connect to the WeCom AI Bot gateway.

#### async def `disconnect(self) -> None`

Disconnect from WeCom.

#### property `enforces_own_access_policy(self) -> bool`

WeCom gates DM/group access at intake via dm_policy/group_policy.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send markdown to a WeCom chat via proactive ``aibot_send_msg``.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

WeCom does not expose typing indicators in this adapter.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Return minimal chat info.


### 顶层函数

#### def `check_wecom_requirements() -> bool`

Check if WeCom runtime dependencies are available.

#### def `qr_scan_for_bot_info(timeout_seconds: int = _QR_POLL_TIMEOUT) -> Optional[Dict[str, str]]`

Run the WeCom QR scan flow to obtain bot_id and secret.

Fetches a QR code from WeCom, renders it in the terminal, and polls
until the user scans it or the timeout expires.

Returns ``{"bot_id": ..., "secret": ...}`` on success, ``None`` on
failure or timeout.

Note: the ``work.weixin.qq.com/ai/qc/{generate,query_result}`` endpoints
used here are not part of WeCom's public developer API — they back the
admin-console web UI's bot-creation flow and may change without notice.
The same pattern is used by the feishu/dingtalk QR setup wizards.

#### def `interactive_setup() -> None`

Interactive setup for WeCom — QR scan or manual credential input.

Replaces hermes_cli/gateway.py::_setup_wecom and the static
_PLATFORMS["wecom"] dict. CLI helpers are lazy-imported.

#### def `register(ctx) -> None`

Plugin entry point — registers both WeCom platforms.


## plugins.platforms.wecom.callback_adapter

### 模块文档

WeCom callback-mode adapter for self-built enterprise applications.

Unlike the bot/websocket adapter in ``wecom.py``, this handles the standard
WeCom callback flow: WeCom POSTs encrypted XML to an HTTP endpoint, the
adapter decrypts it, queues the message for the agent, and immediately
acknowledges.  The agent's reply is delivered later via the proactive
``message/send`` API using an access-token.

Supports multiple self-built apps under one gateway instance, scoped by
``corp_id:user_id`` to avoid cross-corp collisions.

### class WecomCallbackAdapter

> 继承: `BasePlatformAdapter` ｜ 方法数: 19（公开 4）

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

#### async def `disconnect(self) -> None`

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`


### 顶层函数

#### def `check_wecom_callback_requirements() -> bool`


## plugins.platforms.wecom.wecom_crypto

### 模块文档

WeCom BizMsgCrypt-compatible AES-CBC encryption for callback mode.

Implements the same wire format as Tencent's official ``WXBizMsgCrypt``
SDK so that WeCom can verify, encrypt, and decrypt callback payloads.

### class WeComCryptoError

> 继承: `Exception` ｜ 方法数: 0（公开 0）


### class SignatureError

> 继承: `WeComCryptoError` ｜ 方法数: 0（公开 0）


### class DecryptError

> 继承: `WeComCryptoError` ｜ 方法数: 0（公开 0）


### class EncryptError

> 继承: `WeComCryptoError` ｜ 方法数: 0（公开 0）


### class PKCS7Encoder

> 继承: `object` ｜ 方法数: 2（公开 2）

#### classmethod `encode(cls, text: bytes) -> bytes`

#### classmethod `decode(cls, decrypted: bytes) -> bytes`

**异常**: `DecryptError`


### class WXBizMsgCrypt

> 继承: `object` ｜ 方法数: 6（公开 3）

Minimal WeCom callback crypto helper compatible with BizMsgCrypt semantics.

#### def `__init__(token: str, encoding_aes_key: str, receive_id: str)`

**异常**: `ValueError`

#### def `verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str`

#### def `decrypt(self, msg_signature: str, timestamp: str, nonce: str, encrypt: str) -> bytes`

**异常**: `SignatureError`, `DecryptError`

#### def `encrypt(self, plaintext: str, nonce: Optional[str] = None, timestamp: Optional[str] = None) -> str`


## plugins.platforms.whatsapp.__init__


## plugins.platforms.whatsapp.adapter

### 模块文档

WhatsApp platform adapter.

WhatsApp integration is more complex than Telegram/Discord because:
- No official bot API for personal accounts
- Business API requires Meta Business verification
- Most solutions use web-based automation

This adapter supports multiple backends:
1. WhatsApp Business API (requires Meta verification)
2. whatsapp-web.js (via Node.js subprocess) - for personal accounts
3. Baileys (via Node.js subprocess) - alternative for personal accounts

For simplicity, we'll implement a generic interface that can work
with different backends via a bridge pattern.

### class WhatsAppAdapter

> 继承: `WhatsAppBehaviorMixin`、`BasePlatformAdapter` ｜ 方法数: 24（公开 14）

WhatsApp adapter.

This implementation uses a simple HTTP bridge pattern where:
1. A Node.js process runs the WhatsApp Web client
2. Messages are forwarded via HTTP/IPC to this Python adapter
3. Responses are sent back through the bridge

The actual Node.js bridge implementation can vary:
- whatsapp-web.js based
- Baileys based
- Business API based

Configuration:
- bridge_script: Path to the Node.js bridge script
- bridge_port: Port for HTTP communication (default: 3000)
- session_path: Path to store WhatsApp session data
- dm_policy: "open" | "allowlist" | "disabled" | "pairing" — how DMs are handled (default: "pairing")
- allow_from: List of sender IDs allowed in DMs (when dm_policy="allowlist")
- group_policy: "open" | "allowlist" | "disabled" | "pairing" — which groups are processed (default: "pairing")
- group_allow_from: List of group JIDs allowed (when group_policy="allowlist")

Behavior (gating, mention parsing, markdown conversion, chunking) is
provided by ``WhatsAppBehaviorMixin`` so the Cloud API adapter can
share it. Only transport-specific code lives here.

#### def `__init__(config: PlatformConfig)`

#### async def `connect(self, is_reconnect: bool = False) -> bool`

Start the WhatsApp bridge.

This launches the Node.js bridge process and waits for it to be ready.

#### async def `disconnect(self) -> None`

Stop the WhatsApp bridge and clean up any orphaned processes.

#### async def `send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a message via the WhatsApp bridge.

Formats markdown for WhatsApp, splits long messages into chunks
that preserve code block boundaries, and sends each chunk sequentially.

#### async def `edit_message(self, chat_id: str, message_id: str, content: str, finalize: bool = False) -> SendResult`

Edit a previously sent message via the WhatsApp bridge.

#### async def `send_poll(self, chat_id: str, question: str, options: list[str], selectable_count: int = 1) -> SendResult`

Send a native WhatsApp poll via the Baileys bridge.

This is a low-level transport primitive only. Gateway approval UX must
remain gateway-owned and add text fallback plus explicit confirmation
semantics before approval prompts are ever mapped onto polls.

#### async def `send_clarify(self, chat_id: str, question: str, choices: Optional[list], clarify_id: str, session_key: str, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Render multiple-choice clarify as a native WhatsApp poll.

The gateway registers the pending clarify before calling this method.
When Baileys later emits a poll_update with the selected option as
message text, the normal clarify text-intercept resolves the pending
question and the blocked agent continues. Open-ended clarifies use the
text fallback so the user's next typed message is captured.

#### async def `send_location(self, chat_id: str, latitude: float, longitude: float, name: Optional[str] = None, address: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Send a native WhatsApp location pin via the Baileys bridge.

#### async def `send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult`

Download image URL to cache, send natively via bridge.

``metadata`` is accepted to honor the base-class contract — the
batch sender ``send_multiple_images`` passes it through to every
send path. The bridge media call doesn't use it, matching the
sibling overrides (send_video / send_voice / send_document).

#### async def `send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a local image file natively via bridge.

#### async def `send_video(self, chat_id: str, video_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a video natively via bridge — plays inline in WhatsApp.

#### async def `send_voice(self, chat_id: str, audio_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send an audio file as a WhatsApp voice message via bridge.

#### async def `send_document(self, chat_id: str, file_path: str, caption: Optional[str] = None, file_name: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult`

Send a document/file as a downloadable attachment via bridge.

#### async def `send_typing(self, chat_id: str, metadata = None) -> None`

Send typing indicator via bridge.

#### async def `get_chat_info(self, chat_id: str) -> Dict[str, Any]`

Get information about a WhatsApp chat.


### 顶层函数

#### def `check_whatsapp_requirements() -> bool`

Check if WhatsApp dependencies are available.

WhatsApp requires a Node.js bridge for most implementations.

#### def `interactive_setup() -> None`

Guide the user through WhatsApp setup.

Replaces the central _setup_whatsapp in hermes_cli/gateway.py and the
static _PLATFORMS["whatsapp"] dict. CLI helpers are lazy-imported so the
plugin's module-load surface stays minimal.

#### def `register(ctx) -> None`

Plugin entry point — called by the Hermes plugin system.


## plugins.plugin_utils

### 模块文档

Shared concurrency helpers for plugin authors.

The most common plugin footgun is the lazy process-wide singleton:

    _client = None

    def get_client():
        global _client
        if _client is not None:
            return _client
        _client = ExpensiveClient(...)   # <-- TOCTOU: two threads both run this
        return _client

When two threads call ``get_client()`` before the singleton is set, both pass
the ``is not None`` guard, both run the expensive initialization, and the
second write clobbers the first — leaking whatever resource the first client
opened (connections, file handles, background threads).

Multi-threaded agent sessions share one process (delegated tool calls,
background workers, the self-improvement fork), so this race is reachable in
practice. Rather than make every plugin author remember to hand-roll
double-checked locking, this module gives them two thread-safe primitives:

* :func:`lazy_singleton` — decorator for the zero-arg accessor case.
* :class:`SingletonSlot` — manual slot for accessors that build different
  instances depending on a config/key argument.

Both are import-light (stdlib ``threading`` only) so any plugin can import
them without dragging in heavyweight host modules.

### class SingletonSlot

> 继承: `Generic[T]` ｜ 方法数: 4（公开 3）

Thread-safe lazy slot for accessors that take a build argument.

Use this when the cached instance depends on a config/key passed to the
accessor (so a bare zero-arg :func:`lazy_singleton` doesn't fit). The slot
caches the first successfully-built instance and ignores the argument on
subsequent calls — matching the established "first config wins" singleton
semantics most plugins already rely on.

Example::

    _slot: SingletonSlot[Honcho] = SingletonSlot()

    def get_honcho_client(config=None):
        return _slot.get(lambda: Honcho(**resolve(config)))

    def reset_honcho_client():
        _slot.reset()

The factory runs at most once even under concurrent first calls. If the
factory raises, nothing is cached and the next call retries.

#### def `__init__() -> None`

#### def `get(self, factory: Callable[[], T]) -> T`

#### def `peek(self) -> Optional[T]`

Return the cached instance without building it (None if unset).

#### def `reset(self) -> None`

Drop the cached instance so the next ``get()`` rebuilds it.


### 顶层函数

#### def `lazy_singleton(factory: Callable[[], T]) -> Callable[[], T]`

Wrap a zero-argument factory into a thread-safe lazy singleton accessor.

The wrapped callable returns the same instance on every call; the factory
runs exactly once even under concurrent first calls, using double-checked
locking. A ``.reset()`` attribute is attached for tests/teardown.

Example::

    @lazy_singleton
    def get_client():
        return ExpensiveClient(load_config())

    client = get_client()   # built once, safe across threads
    get_client.reset()      # drop the instance (next call rebuilds)

Note: if the factory raises, no instance is cached and the next call
retries (the lock is released either way).


## plugins.security-guidance.__init__

### 模块文档

security-guidance plugin — fast pattern-matched security warnings on file writes.

Wires one behaviour:

* ``transform_tool_result`` hook — scans the *content being written* by
  ``write_file`` / ``patch`` / ``skill_manage`` (write/patch modes) for known
  dangerous code patterns (eval(, pickle.load, yaml.load, os.system,
  subprocess(shell=True), dangerouslySetInnerHTML, verify=False, ECB,
  XXE-prone XML parsers, GitHub Actions ``${{ github.event.* }}`` injection,
  torch.load without ``weights_only=True``, ...). When any pattern matches,
  the plugin appends a ``⚠️ Security warning`` block to the JSON tool-result
  string. The file is still written; the model sees the warning in the next
  turn's tool message and can self-correct.

Why not block? Patterns have a non-trivial false-positive rate (``eval(`` in
a tokenizer, ``yaml.load`` already wrapped in ``yaml.SafeLoader``, ECB inside
a test fixture). Blocking would force every false positive into an approval
prompt or an interrupted workflow. Warning is the right severity for layer
1 — the agent reads the warning and either fixes the code or briefly
documents why the construct is safe.

For block-mode (refuse the write entirely), set
``SECURITY_GUIDANCE_BLOCK=1``. This trades convenience for strictness and
is intended for shared dev environments where unsafe-by-default patterns
are policy violations.

Pattern data lives in ``patterns.py``, forked verbatim from Anthropic's
``claude-plugins-official`` under Apache-2.0. See ``LICENSE`` and ``NOTICE``
in this directory.

### 顶层函数

#### def `register(ctx) -> None`


## plugins.security-guidance.patterns

### 模块文档

Regex-based security pattern definitions for the security-guidance plugin.

Pure data + one pure helper. No env-var reads, no I/O — kept side-effect-free
so it can be imported in isolation.

Forked verbatim from Anthropic's claude-plugins-official repository
(plugins/security-guidance/hooks/patterns.py) under the Apache License 2.0:

    https://github.com/anthropics/claude-plugins-official

  Copyright (c) Anthropic, PBC. and the security-guidance contributors
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

Modifications by NousResearch for the Hermes Agent plugin port:
  - none to the pattern data itself; this file is byte-for-byte the upstream
    patterns.py at commit 0bde168 (2026-05-26). Hermes-side wiring lives in
    __init__.py.

### class RuleId

> 继承: `IntEnum` ｜ 方法数: 0（公开 0）

Stable numeric IDs for SECURITY_PATTERNS rules, emitted via the PostToolUse
metrics field so telemetry can attribute pattern-warning events to
specific checks. The metrics schema only allows bool|number values (no
strings), so rule names can't be sent directly.

Values are frozen: do not renumber existing entries. Append new ones.


### 顶层函数

#### def `rule_names_to_mask(rule_names)`

Pack a set of rule names into a bitmask. Bit N set means RuleId(N) matched.
User-defined patterns (rule_name starting with "user:") have no static
RuleId and are excluded from the mask.


## plugins.spotify.__init__

### 模块文档

Spotify integration plugin — bundled, auto-loaded.

Registers 7 tools (playback, devices, queue, search, playlists, albums,
library) into the ``spotify`` toolset. Each tool's handler is gated by
``_check_spotify_available()`` — when the user has not run ``hermes auth
spotify``, the tools remain registered (so they appear in ``hermes
tools``) but the runtime check prevents dispatch.

Why a plugin instead of a top-level ``tools/`` file?

- ``plugins/`` is where third-party service integrations live (see
  ``plugins/image_gen/`` for the backend-provider pattern, ``plugins/
  disk-cleanup/`` for the standalone pattern). ``tools/`` is reserved
  for foundational capabilities (terminal, read_file, web_search, etc.).
- Mirroring the image_gen plugin layout (``plugins/<category>/<backend>/``
  for categories, flat ``plugins/<name>/`` for standalones) makes new
  service integrations a pattern contributors can copy.
- Bundled + ``kind: backend`` auto-loads on startup just like image_gen
  backends — no user opt-in needed, no ``plugins.enabled`` config.

The Spotify auth flow (``hermes auth spotify``), CLI plumbing, and docs
are unchanged. This move is purely structural.

### 顶层函数

#### def `register(ctx) -> None`

Register all Spotify tools. Called once by the plugin loader.


## plugins.spotify.client

### 模块文档

Thin Spotify Web API helper used by Hermes native tools.

### class SpotifyError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Base Spotify tool error.


### class SpotifyAuthRequiredError

> 继承: `SpotifyError` ｜ 方法数: 0（公开 0）

Raised when the user needs to authenticate with Spotify first.


### class SpotifyAPIError

> 继承: `SpotifyError` ｜ 方法数: 1（公开 0）

Structured Spotify API failure.

#### def `__init__(message: str, status_code: Optional[int] = None, response_body: Optional[str] = None) -> None`


### class SpotifyClient

> 继承: `object` ｜ 方法数: 36（公开 32）

#### def `__init__() -> None`

#### property `base_url(self) -> str`

#### def `request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None, allow_retry_on_401: bool = True, empty_response: Optional[Dict[str, Any]] = None) -> Any`

#### def `get_devices(self) -> Any`

#### def `transfer_playback(self, device_id: str, play: bool = False) -> Any`

#### def `get_playback_state(self, market: Optional[str] = None) -> Any`

#### def `get_currently_playing(self, market: Optional[str] = None) -> Any`

#### def `start_playback(self, device_id: Optional[str] = None, context_uri: Optional[str] = None, uris: Optional[list[str]] = None, offset: Optional[Dict[str, Any]] = None, position_ms: Optional[int] = None) -> Any`

#### def `pause_playback(self, device_id: Optional[str] = None) -> Any`

#### def `skip_next(self, device_id: Optional[str] = None) -> Any`

#### def `skip_previous(self, device_id: Optional[str] = None) -> Any`

#### def `seek(self, position_ms: int, device_id: Optional[str] = None) -> Any`

#### def `set_repeat(self, state: str, device_id: Optional[str] = None) -> Any`

#### def `set_shuffle(self, state: bool, device_id: Optional[str] = None) -> Any`

#### def `set_volume(self, volume_percent: int, device_id: Optional[str] = None) -> Any`

#### def `get_queue(self) -> Any`

#### def `add_to_queue(self, uri: str, device_id: Optional[str] = None) -> Any`

#### def `search(self, query: str, search_types: list[str], limit: int = 10, offset: int = 0, market: Optional[str] = None, include_external: Optional[str] = None) -> Any`

#### def `get_my_playlists(self, limit: int = 20, offset: int = 0) -> Any`

#### def `get_playlist(self, playlist_id: str, market: Optional[str] = None) -> Any`

#### def `create_playlist(self, name: str, public: bool = False, collaborative: bool = False, description: Optional[str] = None) -> Any`

#### def `add_playlist_items(self, playlist_id: str, uris: list[str], position: Optional[int] = None) -> Any`

#### def `remove_playlist_items(self, playlist_id: str, uris: list[str], snapshot_id: Optional[str] = None) -> Any`

#### def `update_playlist_details(self, playlist_id: str, name: Optional[str] = None, public: Optional[bool] = None, collaborative: Optional[bool] = None, description: Optional[str] = None) -> Any`

#### def `get_album(self, album_id: str, market: Optional[str] = None) -> Any`

#### def `get_album_tracks(self, album_id: str, limit: int = 20, offset: int = 0, market: Optional[str] = None) -> Any`

#### def `get_saved_tracks(self, limit: int = 20, offset: int = 0, market: Optional[str] = None) -> Any`

#### def `save_library_items(self, uris: list[str]) -> Any`

#### def `library_contains(self, uris: list[str]) -> Any`

#### def `get_saved_albums(self, limit: int = 20, offset: int = 0, market: Optional[str] = None) -> Any`

#### def `remove_saved_tracks(self, track_ids: list[str]) -> Any`

#### def `remove_saved_albums(self, album_ids: list[str]) -> Any`

#### def `get_recently_played(self, limit: int = 20, after: Optional[int] = None, before: Optional[int] = None) -> Any`


### 顶层函数

#### def `normalize_spotify_id(value: str, expected_type: Optional[str] = None) -> str`

**异常**: `SpotifyError`

#### def `normalize_spotify_uri(value: str, expected_type: Optional[str] = None) -> str`

**异常**: `SpotifyError`

#### def `normalize_spotify_uris(values: Iterable[str], expected_type: Optional[str] = None) -> list[str]`

**异常**: `SpotifyError`

#### def `compact_json(data: Any) -> str`


## plugins.spotify.tools

### 模块文档

Native Spotify tools for Hermes (registered via plugins/spotify).

## plugins.teams_pipeline.__init__

### 模块文档

Teams meeting pipeline plugin.

Registers only operator-facing CLI surfaces. The agent should invoke these via
the terminal tool; no model tools are added by this plugin.

### 顶层函数

#### def `register(ctx) -> None`


## plugins.teams_pipeline.cli

### 模块文档

CLI commands for the Teams meeting pipeline plugin.

### 顶层函数

#### def `register_cli(subparser: argparse.ArgumentParser) -> None`

#### def `teams_pipeline_command(args: argparse.Namespace) -> int`


## plugins.teams_pipeline.meetings

### 模块文档

Graph-backed Teams meeting helpers for the plugin runtime.

### class TeamsMeetingError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Base class for Teams meeting pipeline failures.


### class TeamsMeetingNotFoundError

> 继承: `TeamsMeetingError` ｜ 方法数: 0（公开 0）

Raised when the meeting cannot be resolved from Graph.


### class TeamsMeetingArtifactNotFoundError

> 继承: `TeamsMeetingError` ｜ 方法数: 0（公开 0）

Raised when a transcript or recording cannot be found.


### class TeamsMeetingPermissionError

> 继承: `TeamsMeetingError` ｜ 方法数: 0（公开 0）

Raised when Graph access is denied for the requested resource.


### 顶层函数

#### def `resolve_meeting_reference(client: MicrosoftGraphClient, meeting_id: str | None = None, join_web_url: str | None = None, tenant_id: str | None = None) -> TeamsMeetingRef`

**异常**: `ValueError`, `TeamsMeetingNotFoundError`, `_wrap_graph_error`

#### def `list_transcript_artifacts(client: MicrosoftGraphClient, meeting_ref: TeamsMeetingRef) -> list[MeetingArtifact]`

**异常**: `_wrap_graph_error`

#### def `select_preferred_transcript(candidates: list[MeetingArtifact]) -> MeetingArtifact | None`

#### def `download_transcript_text(client: MicrosoftGraphClient, meeting_ref: TeamsMeetingRef, transcript: MeetingArtifact, encoding: str = 'utf-8') -> str`

**异常**: `TeamsMeetingArtifactNotFoundError`, `_wrap_graph_error`

#### def `fetch_preferred_transcript_text(client: MicrosoftGraphClient, meeting_ref: TeamsMeetingRef) -> tuple[MeetingArtifact | None, str | None]`

#### def `list_recording_artifacts(client: MicrosoftGraphClient, meeting_ref: TeamsMeetingRef) -> list[MeetingArtifact]`

**异常**: `_wrap_graph_error`

#### def `download_recording_artifact(client: MicrosoftGraphClient, meeting_ref: TeamsMeetingRef, recording: MeetingArtifact, destination: str | Path) -> dict[str, Any]`

**异常**: `_wrap_graph_error`

#### def `fetch_call_record_artifact(client: MicrosoftGraphClient, call_record_id: str, allow_permission_errors: bool = True) -> MeetingArtifact | None`

**异常**: `_wrap_graph_error`

#### def `enrich_meeting_with_call_record(client: MicrosoftGraphClient, meeting_ref: TeamsMeetingRef, call_record_id: str | None = None, allow_permission_errors: bool = True) -> MeetingArtifact | None`


## plugins.teams_pipeline.models

### 模块文档

Normalized models for the Teams meeting pipeline plugin.

### class GraphSubscription

> 继承: `object` ｜ 方法数: 3（公开 2）

#### classmethod `from_dict(cls, payload: dict[str, Any]) -> GraphSubscription`

#### def `to_dict(self) -> dict[str, Any]`


### class TeamsMeetingRef

> 继承: `object` ｜ 方法数: 3（公开 2）

#### classmethod `from_dict(cls, payload: dict[str, Any]) -> TeamsMeetingRef`

#### def `to_dict(self) -> dict[str, Any]`


### class MeetingArtifact

> 继承: `object` ｜ 方法数: 3（公开 2）

#### classmethod `from_dict(cls, payload: dict[str, Any]) -> MeetingArtifact`

#### def `to_dict(self) -> dict[str, Any]`


### class TeamsMeetingSummaryPayload

> 继承: `object` ｜ 方法数: 3（公开 2）

#### classmethod `from_dict(cls, payload: dict[str, Any]) -> TeamsMeetingSummaryPayload`

#### def `to_dict(self) -> dict[str, Any]`


### class TeamsMeetingPipelineJob

> 继承: `object` ｜ 方法数: 3（公开 2）

#### classmethod `from_dict(cls, payload: dict[str, Any]) -> TeamsMeetingPipelineJob`

#### def `to_dict(self) -> dict[str, Any]`


## plugins.teams_pipeline.pipeline

### 模块文档

Pipeline orchestration for Microsoft Teams meeting summaries.

### class TeamsPipelineError

> 继承: `RuntimeError` ｜ 方法数: 0（公开 0）

Base class for Teams meeting pipeline failures.


### class TeamsPipelineRetryableError

> 继承: `TeamsPipelineError` ｜ 方法数: 0（公开 0）

Raised when the pipeline should be retried later.


### class TeamsPipelineSinkError

> 继承: `TeamsPipelineError` ｜ 方法数: 0（公开 0）

Raised when an output sink fails.


### class TeamsPipelineArtifactNotFoundError

> 继承: `TeamsPipelineRetryableError` ｜ 方法数: 0（公开 0）

Raised when meeting artifacts are not yet available.


### class TeamsPipelineConfig

> 继承: `object` ｜ 方法数: 1（公开 1）

#### classmethod `from_dict(cls, payload: Optional[dict[str, Any]]) -> TeamsPipelineConfig`


### class NotionWriter

> 继承: `object` ｜ 方法数: 4（公开 1）

#### def `__init__(api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None`

#### async def `write_summary(self, payload: TeamsMeetingSummaryPayload, config: dict[str, Any], existing_record: Optional[dict[str, Any]] = None) -> dict[str, Any]`

**异常**: `TeamsPipelineSinkError`


### class LinearWriter

> 继承: `object` ｜ 方法数: 2（公开 1）

#### def `__init__(api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None`

#### async def `write_summary(self, payload: TeamsMeetingSummaryPayload, config: dict[str, Any], existing_record: Optional[dict[str, Any]] = None) -> dict[str, Any]`

**异常**: `TeamsPipelineSinkError`


### class TeamsMeetingPipeline

> 继承: `object` ｜ 方法数: 11（公开 3）

Transcript-first Teams meeting pipeline with durable lifecycle state.

#### def `__init__(graph_client: Any, store: TeamsPipelineStore, config: TeamsPipelineConfig | dict[str, Any] | None = None, transcribe_fn: TranscribeFn = transcribe_audio, summarize_fn: Optional[SummarizeFn] = None, notion_writer: Optional[NotionWriter] = None, linear_writer: Optional[LinearWriter] = None, teams_sender: Optional[SinkFn] = None) -> None`

#### def `create_job_from_notification(self, notification: dict[str, Any]) -> TeamsMeetingPipelineJob`

#### async def `run_notification(self, notification: dict[str, Any]) -> TeamsMeetingPipelineJob`

#### async def `run_job(self, job_or_id: TeamsMeetingPipelineJob | str) -> TeamsMeetingPipelineJob`

**异常**: `TeamsPipelineError`, `TeamsPipelineRetryableError`, `TeamsPipelineArtifactNotFoundError`


## plugins.teams_pipeline.runtime

### 模块文档

Gateway runtime wiring for the Teams meeting pipeline plugin.

### 顶层函数

#### def `build_pipeline_runtime_config(gateway_config: Any) -> dict[str, Any]`

Build pipeline config from gateway platform config.

Pipeline-specific knobs live under ``teams.extra.meeting_pipeline`` while
Teams delivery continues to source its target details from the existing
Teams platform config.

#### def `build_pipeline_runtime(gateway: Any) -> TeamsMeetingPipeline`

#### def `bind_gateway_runtime(gateway: Any) -> bool`

Attach the Teams pipeline runtime to the msgraph webhook adapter.


## plugins.teams_pipeline.store

### 模块文档

Durable local state for the Teams pipeline plugin.

### class TeamsPipelineStore

> 继承: `object` ｜ 方法数: 18（公开 15）

JSON-backed durable store for Teams pipeline state.

#### def `__init__(path: str | Path)`

#### def `list_subscriptions(self) -> Dict[str, Dict[str, Any]]`

#### def `get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]`

#### def `upsert_subscription(self, subscription_id: str, payload: Dict[str, Any]) -> Dict[str, Any]`

#### def `delete_subscription(self, subscription_id: str) -> bool`

#### classmethod `build_notification_receipt_key(cls, notification: Dict[str, Any]) -> str`

#### def `has_notification_receipt(self, receipt_key: str) -> bool`

#### def `record_notification_receipt(self, receipt_key: str, payload: Optional[Dict[str, Any]] = None, received_at: Optional[str] = None) -> bool`

#### def `record_event_timestamp(self, event_key: str, timestamp: Optional[str] = None) -> str`

#### def `get_event_timestamp(self, event_key: str) -> Optional[str]`

#### def `stats(self) -> Dict[str, int]`

#### def `upsert_job(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]`

#### def `get_job(self, job_id: str) -> Optional[Dict[str, Any]]`

#### def `list_jobs(self) -> Dict[str, Dict[str, Any]]`

#### def `upsert_sink_record(self, sink_key: str, payload: Dict[str, Any]) -> Dict[str, Any]`

#### def `get_sink_record(self, sink_key: str) -> Optional[Dict[str, Any]]`


### 顶层函数

#### def `resolve_teams_pipeline_store_path(path: str | Path | None = None) -> Path`


## plugins.teams_pipeline.subscriptions

### 模块文档

Microsoft Graph subscription helpers for the Teams pipeline plugin.

### 顶层函数

#### def `build_graph_client() -> MicrosoftGraphClient`

#### def `resolve_store_path(path: str | None) -> str`

#### def `build_store(path: str | None = None) -> TeamsPipelineStore`

#### def `sync_graph_subscription_record(store: TeamsPipelineStore, subscription_payload: dict[str, Any], status: str | None = None, renewed: bool = False) -> dict[str, Any]`

#### def `expected_client_state(raw: str | None = None) -> str | None`

#### def `is_managed_subscription(store: TeamsPipelineStore, subscription_payload: dict[str, Any], expected_client_state_value: str | None) -> bool`

#### def `maintain_graph_subscriptions(client: MicrosoftGraphClient, store: TeamsPipelineStore, renew_within_hours: int = 24, extend_hours: int = 24, dry_run: bool = False, client_state: str | None = None) -> dict[str, Any]`


## plugins.video_gen.deepinfra.__init__

### 模块文档

DeepInfra video generation backend.

DeepInfra serves video over the OpenAI-compatible ``/v1/openai/videos``
endpoint (async job: ``create`` → poll → ``download_content``), so all the
SDK plumbing lives in
:class:`agent.video_gen_provider.OpenAICompatibleVideoGenProvider`. This
plugin only declares DeepInfra's identity, credentials, and live model
discovery — no hardcoded model ids, so retired models drop out of hermes the
next time the catalog is fetched without a patch.

Mirrors ``plugins/image_gen/deepinfra`` (which does the same for
``/v1/openai/images/generations``).

### class DeepInfraVideoGenProvider

> 继承: `OpenAICompatibleVideoGenProvider` ｜ 方法数: 4（公开 4）

Text-to-video and image-to-video via DeepInfra's OpenAI-compatible API.

#### property `display_name(self) -> str`

#### def `list_models(self) -> List[Dict[str, Any]]`

Return ``video-gen``-tagged DeepInfra models from the live catalog.

Empty list when the catalog is unreachable — the picker then shows no
options rather than routing to a possibly-retired model.

#### def `capabilities(self) -> Dict[str, Any]`

#### def `get_setup_schema(self) -> Dict[str, Any]`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry point — wire ``DeepInfraVideoGenProvider`` into the registry.


## plugins.video_gen.fal.__init__

### 模块文档

FAL.ai video generation backend.

User-facing surface: pick a **model family** (e.g. "Pixverse v6",
"Veo 3.1", "Seedance 2.0", "Kling v3 4K", "LTX 2.3", "Happy Horse").
The plugin auto-routes to the family's text-to-video endpoint when
called without ``image_url``, and to its image-to-video endpoint when
``image_url`` is provided. The agent never sees the routing — it just
calls ``video_generate(prompt=..., image_url=...)``.

Model families (each with t2v + i2v endpoints):

  Cheap tier:
    ltx-2.3       fal-ai/ltx-2.3-22b/text-to-video               /  fal-ai/ltx-2.3-22b/image-to-video
    pixverse-v6   fal-ai/pixverse/v6/text-to-video               /  fal-ai/pixverse/v6/image-to-video

  Premium tier:
    veo3.1        fal-ai/veo3.1                                  /  fal-ai/veo3.1/image-to-video
    seedance-2.0  bytedance/seedance-2.0/text-to-video           /  bytedance/seedance-2.0/image-to-video
    kling-v3-4k   fal-ai/kling-video/v3/4k/text-to-video         /  fal-ai/kling-video/v3/4k/image-to-video
    happy-horse   alibaba/happy-horse/text-to-video              /  alibaba/happy-horse/image-to-video

Selection precedence for the active family:
    1. ``model=`` arg from the tool call
    2. ``FAL_VIDEO_MODEL`` env var
    3. ``video_gen.fal.model`` in ``config.yaml``
    4. ``video_gen.model`` in ``config.yaml`` (when it's one of our family IDs)
    5. ``DEFAULT_MODEL``

Authentication via ``FAL_KEY`` or the managed Nous gateway. Output is an
HTTPS URL from FAL's CDN; the gateway downloads and delivers it.

### class FALVideoGenProvider

> 继承: `VideoGenProvider` ｜ 方法数: 8（公开 8）

FAL.ai multi-family video generation backend.

Routes between text-to-video and image-to-video endpoints automatically
based on whether ``image_url`` was provided.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, model: Optional[str] = None, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, duration: Optional[int] = None, aspect_ratio: str = '16:9', resolution: str = '720p', negative_prompt: Optional[str] = None, audio: Optional[bool] = None, seed: Optional[int] = None, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `register(ctx) -> None`

Plugin entry point — wire ``FALVideoGenProvider`` into the registry.


## plugins.video_gen.xai.__init__

### 模块文档

xAI Grok-Imagine video generation backend.

Surface: text-to-video, image-to-video, and reference-to-video through the
unified video provider. xAI edit/extend are exposed through separate tools.

Originally salvaged from PR #10600 by @Jaaneek; reshaped into the
:class:`VideoGenProvider` plugin interface and trimmed to the
generate-only surface.

Authentication: xAI Grok OAuth tokens (preferred — billed against the
user's SuperGrok or X Premium+ subscription) or ``XAI_API_KEY``. Both routes are
resolved through ``tools.xai_http.resolve_xai_http_credentials`` so a
single login covers chat + TTS + image gen + video gen + transcription.
When xAI storage is enabled, the primary ``video`` / ``public_url`` fields are the
stored files-cdn HTTPS link. Pass that public MP4 URL as ``video_url`` for
edit/extend; it is sent to xAI as ``video.url``.

### class XAIVideoGenProvider

> 继承: `VideoGenProvider` ｜ 方法数: 8（公开 8）

xAI Grok Imagine video backend.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

#### def `list_models(self) -> List[Dict[str, Any]]`

#### def `default_model(self) -> Optional[str]`

#### def `get_setup_schema(self) -> Dict[str, Any]`

#### def `capabilities(self) -> Dict[str, Any]`

#### def `generate(self, prompt: str, model: Optional[str] = None, image_url: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, duration: Optional[int] = None, aspect_ratio: str = DEFAULT_ASPECT_RATIO, resolution: str = DEFAULT_RESOLUTION, negative_prompt: Optional[str] = None, audio: Optional[bool] = None, seed: Optional[int] = None, **kwargs: Any) -> Dict[str, Any]`


### 顶层函数

#### def `has_xai_video_credentials() -> bool`

#### def `run_xai_video_generation(prompt: str, model: Optional[str], explicit_model: bool, image_url: Optional[str], reference_image_urls: Optional[List[str]], duration: Optional[int], aspect_ratio: str, resolution: str) -> Dict[str, Any]`

#### def `run_xai_video_edit(prompt: str, video_url: str, model: Optional[str] = None) -> Dict[str, Any]`

#### def `run_xai_video_extend(prompt: str, video_url: str, duration: Optional[int] = None, model: Optional[str] = None) -> Dict[str, Any]`

#### def `register(ctx) -> None`

Plugin entry point — wire ``XAIVideoGenProvider`` into the registry.


## plugins.web.__init__


## plugins.web.brave_free.__init__

### 模块文档

Brave Search (free tier) plugin — bundled, auto-loaded.

Mirrors the ``plugins/image_gen/openai/`` layout: ``provider.py`` holds the
provider class, ``__init__.py::register(ctx)`` registers an instance.

### 顶层函数

#### def `register(ctx) -> None`

Register the Brave-free provider with the plugin context.


## plugins.web.brave_free.provider

### 模块文档

Brave Search (free tier) — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider` (the
plugin-facing ABC). The legacy in-tree module
``tools.web_providers.brave_free`` was removed in the same commit that
moved this code under ``plugins/``; this file is now the canonical
implementation.

Config keys this provider responds to::

    web:
      search_backend: "brave-free"     # explicit per-capability
      backend: "brave-free"            # shared fallback

Auth env var::

    BRAVE_SEARCH_API_KEY=...    # https://brave.com/search/api/ (free tier)

### class BraveFreeWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 7（公开 7）

Search-only Brave provider using the free-tier Data-for-Search API.

Free tier is 2,000 queries/month (1 qps). No content-extraction capability —
users pair this with Firecrawl/Tavily/Exa for ``web_extract``.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Return True when ``BRAVE_SEARCH_API_KEY`` is set to a non-empty value.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a search against the Brave Search API.

Returns ``{"success": True, "data": {"web": [{"title", "url", "description", "position"}]}}``
on success, or ``{"success": False, "error": str}`` on failure.

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.web.ddgs.__init__

### 模块文档

DuckDuckGo search plugin — bundled, auto-loaded.

Backed by the community ``ddgs`` Python package which scrapes DDG's HTML
results page. No API key required, but the package itself must be installed
(it's an optional dep — gated via :meth:`is_available`).

### 顶层函数

#### def `register(ctx) -> None`

Register the DDGS provider with the plugin context.


## plugins.web.ddgs.provider

### 模块文档

DuckDuckGo search — plugin form (via the ``ddgs`` package).

Subclasses the plugin-facing :class:`agent.web_search_provider.WebSearchProvider`.
The legacy in-tree module ``tools.web_providers.ddgs`` was removed in the
same commit that moved this code under ``plugins/``; this file is now the
canonical implementation.

The ``ddgs`` package is an optional dependency. ``is_available()`` reflects
whether the package is importable; the plugin still registers either way so
``hermes tools`` can prompt the user to install it.

### class DDGSWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 7（公开 7）

DuckDuckGo HTML-scrape search provider.

No API key needed. Rate limits are enforced server-side by DuckDuckGo;
the provider surfaces ``DuckDuckGoSearchException`` and other ddgs errors
as ``{"success": False, "error": ...}`` rather than raising.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Return True when the ``ddgs`` package is importable.

Probes the import once; cheap because Python caches the import. Must
NOT perform network I/O — runs at tool-registration time and on every
``hermes tools`` paint.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a DuckDuckGo search and return normalized results.

The synchronous ``ddgs`` call is run in a worker thread with a hard
wall-clock timeout (``_SEARCH_TIMEOUT_SECS``) so a hung search cannot
block the shared agent loop indefinitely (#36776).

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.web.exa.__init__

### 模块文档

Exa web search + extract plugin — bundled, auto-loaded.

Backed by the official Exa SDK (``exa-py``). Both search and extract are
sync; the dispatcher in :mod:`tools.web_tools` handles the wrap when the
caller is async.

### 顶层函数

#### def `register(ctx) -> None`

Register the Exa provider with the plugin context.


## plugins.web.exa.provider

### 模块文档

Exa web search + content extraction — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider`. Uses the
official Exa SDK (``exa-py``) which is lazy-loaded via
:func:`tools.lazy_deps.ensure` so that cold-start CLI users don't pay the
SDK import cost when Exa isn't configured.

Config keys this provider responds to::

    web:
      search_backend: "exa"      # explicit per-capability
      extract_backend: "exa"     # explicit per-capability
      backend: "exa"             # shared fallback for both

Env var::

    EXA_API_KEY=...    # https://exa.ai (paid tier; free trial available)

The previous in-tree implementation lived at
``tools.web_tools._exa_search`` / ``_exa_extract``; this file is the
canonical replacement. Behavior is bit-for-bit identical aside from the
ABC method-name change.

### class ExaWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 8（公开 8）

Exa search + extract provider.

Both methods are sync — Exa's SDK is sync-only. The web_extract_tool
dispatcher wraps sync extracts via ``asyncio.to_thread`` when it
needs to keep the event loop responsive.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Return True when ``EXA_API_KEY`` is set to a non-empty value.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute an Exa search.

Returns ``{"success": True, "data": {"web": [{...}, ...]}}`` on
success, ``{"success": False, "error": str}`` on failure (incl.
missing API key and SDK install errors).

#### def `extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]`

Extract content from one or more URLs via Exa.

Returns a list of result dicts shaped for the legacy LLM
post-processing pipeline. On per-URL or whole-batch failure,
results carry an ``error`` field rather than raising.

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.web.firecrawl.__init__

### 模块文档

Firecrawl web search + extract plugin — bundled, auto-loaded.

Largest single plugin in this PR. Captures everything the previous
inline implementation in tools/web_tools.py did:

  - Lazy import of the firecrawl SDK (~200ms cold-start cost) via a
    callable proxy that defers the actual import to first use.
  - Dual client paths: direct (FIRECRAWL_API_KEY / FIRECRAWL_API_URL)
    OR Nous-hosted tool-gateway routing for subscribers, with
    web.use_gateway as the tie-breaker.
  - Per-URL scrape loop with 60s timeout, SSRF re-check after redirect,
    website-policy gating, and format-aware content selection.
  - Robust response shape normalization across SDK / direct API /
    gateway variants (search returns differ by transport).

The plugin re-exports ``Firecrawl`` (the lazy proxy) and
``check_firecrawl_api_key`` for backward-compatibility with tests and
external code that imports those names from ``tools.web_tools``.

### 顶层函数

#### def `register(ctx) -> None`

Register the Firecrawl provider with the plugin context.


## plugins.web.firecrawl.provider

### 模块文档

Firecrawl web search + extract — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider`. This is
the largest provider migrated in this PR; it captures the full inline
firecrawl implementation that previously lived in tools/web_tools.py:

  - :data:`Firecrawl` lazy proxy that defers the ~200ms SDK import to
    first use (re-exported by tools.web_tools for backward compat with
    existing tests that mock that name).
  - :func:`_get_firecrawl_client` with direct + managed-gateway dual
    mode, controlled by ``web.use_gateway`` config when both are
    configured.
  - :func:`check_firecrawl_api_key` re-exported (tests + tools_config
    setup hint depend on this name living in tools.web_tools).
  - :func:`_extract_web_search_results` / :func:`_extract_scrape_payload`
    response-shape normalizers that handle SDK / direct API / gateway
    response variants.
  - Per-URL extract loop with 60s timeout, redirect-aware SSRF re-check,
    website-policy gating, and format-aware content selection.

Async note: the underlying SDK is sync. ``extract()`` is declared
``async def`` because it performs per-URL I/O that benefits from
running in an executor; the implementation wraps each scrape in
:func:`asyncio.to_thread` with :func:`asyncio.wait_for(timeout=60)` to
guard against hung fetches.

Config keys this provider responds to::

    web:
      search_backend: "firecrawl"     # explicit per-capability
      extract_backend: "firecrawl"    # explicit per-capability
      backend: "firecrawl"            # shared fallback (default)
      use_gateway: false              # prefer managed gateway when both
                                      # direct + gateway credentials exist

Env vars::

    FIRECRAWL_API_KEY=...            # direct cloud auth
    FIRECRAWL_API_URL=...            # self-hosted Firecrawl
    FIRECRAWL_GATEWAY_URL=...        # Nous tool-gateway (subscribers)
    TOOL_GATEWAY_DOMAIN=...          # alternate gateway env
    TOOL_GATEWAY_SCHEME=...
    TOOL_GATEWAY_USER_TOKEN=...

### class FirecrawlWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 8（公开 8）

Firecrawl search + extract provider with dual auth paths.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Return True when direct Firecrawl OR managed-gateway path is configured.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a Firecrawl search.

Sync; matches the legacy ``_get_firecrawl_client().search(...)``
call directly. Normalizes the response across SDK/direct/gateway
shapes via :func:`_extract_web_search_results`.

Pre-flight errors (``ValueError`` from configuration check,
``ImportError`` from missing SDK) propagate to the dispatcher's
top-level handler, which wraps them as ``tool_error(...)`` —
matching the legacy ``{"error": "Error searching web: ..."}``
envelope. Only in-flight errors are caught and surfaced as
``{"success": False, "error": ...}``.

#### async def `extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]`

Extract content from one or more URLs via Firecrawl.

Async; each URL is scraped in a background thread with a 60s
timeout. After scraping, the final URL (post-redirect) is
re-checked against website-access policy.

Accepted kwargs (others ignored for forward compat):
  - ``format``: ``"markdown"`` or ``"html"``; default is both
    (request both, return markdown when available).

Returns the legacy per-URL list-of-results shape. Per-URL failures
(timeout, SSRF block, scrape error, policy block) become items
with an ``error`` field rather than raising.

#### def `get_setup_schema(self) -> Dict[str, Any]`


### 顶层函数

#### def `check_firecrawl_api_key() -> bool`

Return True when Firecrawl backend (direct or gateway) is usable.

Re-exported by :mod:`tools.web_tools` for backward compatibility with
existing tests and the ``hermes tools`` setup flow.


## plugins.web.parallel.__init__

### 模块文档

Parallel.ai web search + extract plugin — bundled, auto-loaded.

First plugin in this repo to expose an async :meth:`extract` — Parallel's
SDK is async-native (``AsyncParallel.beta.extract``). The web_extract_tool
dispatcher detects coroutines via :func:`inspect.iscoroutinefunction` and
awaits.

### 顶层函数

#### def `register(ctx) -> None`

Register the Parallel provider with the plugin context.


## plugins.web.parallel.provider

### 模块文档

Parallel.ai web search + content extraction — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider`. Uses two
distinct Parallel SDK clients:

- ``Parallel`` (sync)        — for :meth:`search`
- ``AsyncParallel`` (async)  — for :meth:`extract`

This is the first plugin to exercise the **async-extract** code path in
the ABC: :meth:`extract` is declared ``async def``, and the dispatcher
in :func:`tools.web_tools.web_extract_tool` detects coroutines via
:func:`inspect.iscoroutinefunction` and awaits.

Config keys this provider responds to::

    web:
      search_backend: "parallel"      # explicit per-capability
      extract_backend: "parallel"     # explicit per-capability
      backend: "parallel"             # shared fallback
      # Optional: search mode (default "agentic"; also "fast" or "one-shot")
      # via the PARALLEL_SEARCH_MODE env var.

Env vars::

    PARALLEL_API_KEY=...             # https://parallel.ai (required)
    PARALLEL_SEARCH_MODE=agentic     # optional: agentic|fast|one-shot

### class ParallelWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 8（公开 8）

Parallel.ai search + async extract provider.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Return True when ``PARALLEL_API_KEY`` is set to a non-empty value.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a Parallel search (sync).

Uses the ``beta.search`` endpoint with the configured mode
(``PARALLEL_SEARCH_MODE`` env var, default "agentic"). Limit is
capped at 20 server-side.

#### async def `extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]`

Extract content from one or more URLs via the async SDK.

Returns the legacy list-of-results shape that
:func:`tools.web_tools.web_extract_tool` expects: one entry per
successful URL plus one entry per failed URL with an ``error``
field. Errors are not raised — they're returned as per-URL items.

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.web.searxng.__init__

### 模块文档

SearXNG search plugin — bundled, auto-loaded.

Backed by a user-hosted SearXNG instance (URL configured via ``SEARXNG_URL``).
Search-only — pair with an extract provider (firecrawl/tavily/exa) for
``web_extract`` calls.

### 顶层函数

#### def `register(ctx) -> None`

Register the SearXNG provider with the plugin context.


## plugins.web.searxng.provider

### 模块文档

SearXNG search — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider`. Same JSON
API call (``/search?format=json``), same result normalization. The legacy
in-tree module ``tools.web_providers.searxng`` was removed in the same
commit that moved this code under ``plugins/``; this file is now the
canonical implementation.

Search-only — SearXNG aggregates results from upstream engines but does not
fetch/extract arbitrary URLs. ``supports_extract()`` returns False.

Config keys this provider responds to::

    web:
      search_backend: "searxng"     # explicit per-capability
      backend: "searxng"            # shared fallback

Env var::

    SEARXNG_URL=http://localhost:8080

### class SearXNGWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 7（公开 7）

Search via a user-hosted SearXNG instance.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Return True when ``SEARXNG_URL`` is set.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a search against the configured SearXNG instance.

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.web.tavily.__init__

### 模块文档

Tavily web search + extract plugin — bundled, auto-loaded.

### 顶层函数

#### def `register(ctx) -> None`

Register the Tavily provider with the plugin context.


## plugins.web.tavily.provider

### 模块文档

Tavily web search + content extraction — plugin form.

Subclasses :class:`agent.web_search_provider.WebSearchProvider`. Two
capabilities advertised:

- ``supports_search()``  -> True (Tavily ``/search``)
- ``supports_extract()`` -> True (Tavily ``/extract``)

Both are sync — the underlying call is ``httpx.post(...)``.

Config keys this provider responds to::

    web:
      search_backend: "tavily"     # explicit per-capability
      extract_backend: "tavily"    # explicit per-capability
      backend: "tavily"            # shared fallback for both

Env vars::

    TAVILY_API_KEY=...           # https://app.tavily.com/home (required)
    TAVILY_BASE_URL=...          # optional override of https://api.tavily.com

### class TavilyWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 8（公开 8）

Tavily search + extract provider.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Return True when ``TAVILY_API_KEY`` is set to a non-empty value.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a Tavily search.

#### def `extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]`

Extract content from one or more URLs via Tavily.

Sync — the underlying call is httpx.post(...). Returns the legacy
list-of-results shape; per-URL failures become items with ``error``.

#### def `get_setup_schema(self) -> Dict[str, Any]`


## plugins.web.xai.__init__

### 模块文档

xAI web search plugin — bundled, auto-loaded.

Mirrors the ``plugins/web/brave_free/`` layout: ``provider.py`` holds the
provider class, ``__init__.py::register(ctx)`` registers an instance.

### 顶层函数

#### def `register(ctx) -> None`

Register the xAI Web Search provider with the plugin context.


## plugins.web.xai.provider

### 模块文档

xAI Web Search — plugin form.

Routes ``web_search`` tool calls through xAI's agentic Web Search tool
(server-side ``web_search`` on the Responses API). Grok runs the actual
searching and page-browsing server-side; we ask it to return the top
results as structured JSON so we can hand back the same
``{title, url, description, position}`` rows every other Hermes web
provider produces.

Reference: https://docs.x.ai/developers/tools/web-search

Config keys this provider responds to::

    web:
      search_backend: "xai"           # explicit per-capability
      backend: "xai"                  # shared fallback

Optional knobs (under ``web.xai`` in ``config.yaml``)::

    web:
      xai:
        model: "grok-build-0.1"       # reasoning model required by web_search
        allowed_domains: ["x.ai"]     # max 5 — mutually exclusive with excluded_domains
        excluded_domains: ["bad.com"] # max 5 — mutually exclusive with allowed_domains
        timeout: 90                   # seconds (default 90)

Auth: reuses :func:`tools.xai_http.resolve_xai_http_credentials`, which
prefers Hermes-managed xAI Grok OAuth (via ``hermes auth``) and falls back
to ``XAI_API_KEY`` (resolved through ``~/.hermes/.env``, then
``os.environ``).

### class XAIWebSearchProvider

> 继承: `WebSearchProvider` ｜ 方法数: 12（公开 7）

Search-only provider backed by xAI's agentic Web Search tool.

Sends a structured prompt to Grok with ``tools=[{"type": "web_search"}]``
enabled and asks it to return the top *limit* results as JSON. Falls
back to the Responses API ``citations`` list if Grok ignores the JSON
schema instruction (rare for grok-4.3 but cheap insurance).

No extract capability — pair with Firecrawl / Tavily / Exa for
``web_extract`` if you need page content.

Trust model
-----------
Unlike index-backed providers (Brave / Tavily / Exa) which return
verbatim search-engine results, this backend is an LLM in a trench
coat: Grok decides which URLs to surface, generates the titles and
descriptions itself, and is influenced by the *content of the query*.
A maliciously crafted query (e.g. injected via untrusted upstream
input the agent picked up) can in principle steer Grok into emitting
attacker-chosen URLs. Callers that pipe untrusted text directly into
``web_search`` should treat returned URLs the same way they would
treat any model-generated link — validate before fetching.

#### property `name(self) -> str`

#### property `display_name(self) -> str`

#### def `is_available(self) -> bool`

Cheap availability probe — env var OR auth-store has OAuth tokens.

Delegates to :func:`tools.xai_http.has_xai_credentials`, which is
deliberately *not* the same as :func:`resolve_xai_http_credentials`:
it never triggers OAuth token refresh or acquires the auth-store
lock. The ABC contract requires this method to be safe to call on
every ``hermes tools`` repaint and at tool-registration time.
Token freshness / refresh is handled inside :meth:`search`.

#### def `supports_search(self) -> bool`

#### def `supports_extract(self) -> bool`

#### def `search(self, query: str, limit: int = 5) -> Dict[str, Any]`

Execute a Grok-backed web search.

Returns ``{"success": True, "data": {"web": [{title, url, description, position}, ...]}}``
on success, ``{"success": False, "error": str}`` on failure.

#### def `get_setup_schema(self) -> Dict[str, Any]`

