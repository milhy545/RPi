# Specification: Lightweight Auth Boundaries

## Overview

Introduce role-based access control with three tiers — Basic, Expert, and
Admin — to the RPi-TV Dashboard. Basic preserves the current no-login
household experience for everyday playback. Expert and Admin add step-up
authentication for configuration, device management, and system operations.
All enforcement is server-side; UI element hiding is never the security
boundary.

## Motivation

The dashboard currently relies solely on a subnet IP allowlist. Any device
on the LAN or Tailscale range has full access to every endpoint, including
destructive operations such as reboot, BT device removal, and terminal/PTY
access. The unified-ui-ux-refactor track requires a concrete auth
implementation before Basic/Expert/Admin UI gating can be enabled. The
existing dashboard-security-cleanup track completed terminal WebSocket
token auth and Wi-Fi credential handling but did not introduce session
management or role enforcement.

## Functional Requirements

### Roles

| Role | Login | Access |
|------|-------|--------|
| Basic | None | Read states; everyday MPV play/pause/stop/seek/volume, mute, household return, mode discovery/status |
| Expert | Step-up cookie session | Routing, config, device/network/audio/CEC management |
| Admin | Elevated cookie session or step-up from Expert | Terminal/PTY, WS credential, system logs, system restart/reboot, future system update |

- Admin inherits all Expert permissions.
- Expert may perform a short-lived step-up to Admin (5-minute window).
- Basic routes must work when `auth.json` has not been provisioned.
- Expert/Admin routes return `503 setup_required` when unprovisioned.

### Route Policy (method/path aware, fail-closed)

**Basic (no login):**

- `/mpv/play`, `/mpv/stop`, `/mpv/toggle`, `/mpv/seek`, `/mpv/seekabs`,
  `/mpv/vol`, `/mpv/volume` — everyday playback control.
- `/mpv/status`, `/mpv/memory` — read state and resume position.
- `/modes` (GET) — read available display modes.
- `/audio/state`, `/audio/matrix`, `/audio/mute-state`,
  `/audio/bluetooth-profiles`, `/audio/mute` — read state and normal mute.
- `/devices/state`, `/devices`, `/bt/state`, `/bt/scan`, `/bt/controller`,
  `/bt/transfers`, `/bt/files`, `/bt/diagnostics`, `/bt/media`,
  `/bt/pairing`, `/bt/capabilities`, `/bt/phone-role` — read device state.
- `/wifi/status`, `/cec/scan`, `/cec/br/st` — read network/CEC state.
- `/system/stats`, `/system/hw-stats`, `/system/status`,
  `/system/https-info` — read system state.
- `/network/info`, `/network/tailscale` — read network info.
- `/youtube/cookies/status`, `/media/preview` — read diagnostics.
- `/dlna/scan`, `/dlna/renderer/status` — read DLNA state.
- `/audio/route/dlna-input/status` — read DLNA input route status.
- `/return/last`, `/return/config` — read return state.
- `/return` (POST) — trigger household return-to-dashboard.
- `/cache/stats`, `/pool/stats` — read cache/pool stats.
- `/report` (POST) — submit feedback from any household member.
- All static assets, WebUI shell, manifest, favicon.

**Expert (login):**

- MPV resume management (GET): `/mpv/memory-save`, `/mpv/memory/clear`.
- Audio routing (GET today): `/audio/default-sink`, `/audio/volume`,
  `/audio/volume/global`, `/audio/bt`, `/audio/hdmi`, `/audio/dlna`,
  `/audio/latency`, `/audio/multi-output`, `/audio/matrix/link`,
  `/audio/test`, `/keepalive`.
- Audio route management (GET today): `/audio/route/alexa-bt`,
  `/audio/route/alexa-retarget`, `/audio/route/dlna-input/start`,
  `/audio/route/dlna-input/stop`, `/audio/route/dlna-input/mode`,
  `/audio/route/dlna-input/target`.
- DLNA renderer control (GET today): `/dlna/select`, `/dlna/connect`,
  `/dlna/disconnect`, `/dlna/renderer/start`, `/dlna/renderer/stop`.
- BT management (GET today): `/bt/pair`, `/bt/trust`, `/bt/connect`,
  `/bt/disconnect`, `/bt/device-action`, `/bt/device-profile`,
  `/bt/device-autoconnect`, `/bt/device-hid`, `/bt/settings`,
  `/bt/adapter-power`, `/bt/discoverable`, `/bt/discovery`,
  `/bt/operation`, `/devices/bt/scan`.
- Wi-Fi management: `/wifi/connect` (GET+POST), `/wifi/scan` (GET).
- CEC control: `/cec/send`, `/cec/key`, `/cec/in`, `/cec/power`,
  `/cec/nav`, `/cec/vol`, `/cec/input`, `/cec/br/start`, `/cec/br/stop`.
- Return config: `/return/config/set`.
- YouTube age check: `/youtube/age-check`.
- Cache/pool management: `/cache/clear`, `/pool/clear`.
- Integration config: `/ha/config` — minimum Expert because future
  integration config may contain auth credentials.

**Admin (elevated login):**

- Terminal: `/terminal/connect`, `/terminal/disconnect`.
- WS credential: `/ws/token`.
- System logs: `/system/logs`.
- System restart/reboot (GET today): `/system/restart-mpv`,
  `/system/restart-dashboard`, `/system/restart-rpi`, `/system/reboot`,
  `/restart/mpv`, `/restart/dashboard`, `/restart/rpi`.
- BT destructive: `/bt/remove`, `/bt/reset`, `/bt/file-send`,
  `/bt/file-cancel`.
- Self-test: `/selftest/testaudio`.

**Fail-closed default:** any route in a protected namespace
(`/audio/*`, `/bt/*`, `/wifi/*`, `/cec/*`, `/system/*`, `/terminal/*`,
`/dlna/*`, `/return/*`, `/mpv/*`, `/devices/*`, `/network/*`,
`/restart/*`, `/youtube/*`, `/media/*`, `/cache/*`, `/pool/*`,
`/ha/*`, `/selftest/*`, `/ws/*`, `/keepalive`) not explicitly
classified defaults to Admin. Genuinely unregistered paths (e.g.,
`/foo/bar`) return 404 — they never reach the auth gate.

**Deprecated (no auth, return 410):** `/play`, `/kodi/st`, `/kodi/status`.

Every `ENDPOINT_ROLES` entry is keyed by exact `(path, method)` and stores `RoutePolicy(required_role, mutating: bool)`. Representative flags: `/mpv/play` GET Basic/true, `/mpv/status` GET Basic/false, `/return` POST Basic/true, `/report` POST Basic/true, `/system/logs` GET Admin/false, and `/system/reboot` GET Admin/true.

### Authentication

#### Password hashing

- Algorithm: PBKDF2-SHA256 via `hashlib.pbkdf2_hmac` (stdlib, no new
  dependency).
- Iteration count: determined by hardware benchmark at provisioning time.
  The calibration function runs multiple samples per candidate iteration
  count, computes the median login time for each, and estimates the
  optimal count whose median lands within 150–300 ms. It then clamps
  to safe bounds (100_000–1_000_000), verifies the final multi-sample
  median of the selected count lies within 150–300 ms, and fails
  provisioning with an actionable error if no candidate satisfies the
  target. Unit tests mock timings; live RPi evidence records median/p95.
- Salt: 16 bytes, generated per credential.
- Stored in `auth.json` as base64 alongside the iteration count.

#### Session management

- Token: `secrets.token_bytes(32)` — opaque, random, 32 bytes.
- Cookie value: hex-encoded token (64 characters), `HttpOnly`,
  `SameSite=Lax`, `Path=/`.
- Secure attribute set when the actual connection is TLS, including loopback TLS, and omitted only for permitted loopback HTTP.
- Server-side store: in-memory `dict[sha256(token) → Session]` protected
  by `threading.Lock`. Only the SHA-256 digest of the token is stored;
  the raw token is never persisted server-side. The lock is acquired
  non-nested; public methods acquire Lock once and private `_unlocked`
  helpers may run only while the caller holds it.
- Session object: `{role, created, last_seen, csrf_token, step_up_expires}`.
- TTLs: Expert 8 hours (sliding window), Admin 30 minutes
  (sliding window), step-up 5 minutes.
- Request validation: `bytes.fromhex(cookie)` → `sha256()` → dict lookup
  under the store lock. The hot path performs only a digest computation
  and a locked dictionary lookup; no password hashing occurs per request.
- The store lock must be held for all read and write operations on the
  session dict. `AuthStore` uses the same `Lock` pattern with non-nested
  acquisition and private `_unlocked` helpers for all config file reads
  and writes. Concurrency tests verify safe behaviour under parallel
  create/validate/destroy and concurrent read/write.

#### Step-up flow

1. User has an Expert session cookie.
2. Frontend opens step-up modal for Admin actions.
3. `POST /auth/step-up` with `{"password": "<admin-password>"}`,
   existing session cookie, and `X-CSRF-Token` header matching the
   session's csrf_token. Requires HTTPS (loopback exempt).
4. Server verifies Expert session, CSRF token, then verifies admin
   password hash.
5. On success: sets `step_up_expires = now + 300s` and
   `effective_role = Admin`.
6. After 5 minutes, `effective_role` reverts to Expert.

#### Login

- `POST /auth/login` with `{"password": "...", "role": "expert|admin"}`.
- The `role` field is required and specifies which credential to verify.
  The server never silently prefers one hash over another; if the
  submitted password matches the wrong role's hash, login fails with 401.
- Requires HTTPS (loopback exempt).
- Additionally applies Origin / Fetch Metadata checks: rejects requests with `Sec-Fetch-Site: cross-site`; cross-origin is detected solely by an invalid `Origin` or `Referer` host not matching `ALLOWED_SUBNETS` / `localhost` / `*.local`; validates `Origin` or `Referer` host against `ALLOWED_SUBNETS` when present.
- Rate limit: 5 attempts per minute per IP.

### CSRF Protection

CSRF protection is determined by route policy, not merely by the presence
of an elevated session cookie.

**Expert/Admin cookie-authenticated mutations (e.g., `/bt/pair`,
`/audio/default-sink`, `/wifi/connect`):**

- Mechanism: synchroniser token + provenance.
  - Server generates `csrf_token = secrets.token_bytes(16)` at session
    creation.
  - The token hex is available via a readable `rpi_csrf` convenience
    cookie (non-HttpOnly, `SameSite=Strict`, `Path=/`, `Secure` if the connection is TLS, omitted only for permitted loopback HTTP).
  - Every cookie-authenticated Expert/Admin state-changing request MUST
    include an `X-CSRF-Token` header whose value matches the session's
    `csrf_token`. Server performs constant-time comparison via
    `hmac.compare_digest`. If a `rpi_csrf` cookie is also present, the
    header value must equal the cookie value.
  - Cross-site requests are rejected (`Sec-Fetch-Site: cross-site`).
    Cross-origin is detected solely by an invalid `Origin` or `Referer`
    host not matching `ALLOWED_SUBNETS` / `localhost` / `*.local`.
  - When `Origin` or `Referer` is present, it must be valid.
  - When `Origin` and `Referer` are both absent: non-loopback accepts
    only when `Sec-Fetch-Site` is `same-origin` or `same-site`; loopback
    accepts missing provenance; otherwise rejected.
- Bearer-authenticated requests bypass CSRF (no browser context).

**Basic mutating routes (e.g., `/mpv/play` GET, `/return` POST):**
- Basic mutations without a session cannot use session CSRF (no session exists). Instead, a Fetch Metadata / Origin defence is applied for all Basic routes where RoutePolicy.mutating=true, regardless of HTTP method:
  - If `Sec-Fetch-Site` header is present and equals `cross-site`, the request is rejected with 403.
  - If `Origin` or `Referer` header is present, its host must match `ALLOWED_SUBNETS` or be `localhost`/`*.local`.
  - When `Origin` and `Referer` are both absent: accept loopback; accept non-loopback only when `Sec-Fetch-Site` is `same-origin` or `same-site`; otherwise reject.
- This defence is not a perfect CSRF barrier; it relies on browser enforcement of Fetch Metadata headers. It reduces the attack surface without blocking legitimate automation.
### API Tokens (Bearer)

- Stored in `auth.json` under `api_keys`, keyed by SHA-256 digest
  of the raw token. Each record: `{role, label, created}`. The digest
  is the map key; no prefix field is stored.
- Raw token is printed exactly once at creation (local CLI only) and
  never persisted.
- Validation: `sha256(bearer_value)` → dict lookup.

### Provisioning

- No web bootstrap. No secret printing to stderr or logs.
- Local CLI tool: `tools/auth_setup.py` with subcommands `expert`,
  `admin`, `api-key`.
- Uses `ssh-askpass` (or `$SSH_ASKPASS`) when a graphical or askpass
  environment is usable (`$DISPLAY` or `$SSH_ASKPASS` set), with
  `getpass.getpass()` as TTY fallback. Passwords are never passed as
  command-line arguments.
- Config file: `~/.config/rpi-dashboard/auth.json`, written atomically
  (temp file → fsync → rename) with mode `0600`. Directory created
  with mode `0700` if missing.
- Before overwriting an existing `auth.json`, the provisioning tool
  creates a mode-0600 backup copy (e.g., `auth.json.bak`) in the same
  directory.
- Two separate hashed credentials: `expert` and `admin`.
- Role-aware access: Expert ACCESS is considered provisioned when
  either an expert or admin hash exists; Admin ACCESS requires an admin
  hash. `is_role_provisioned(role) -> bool` reflects this (Expert true
  if either hash present, Admin true only if admin hash present). The
  local CLI sets credentials directly; it is not authorised by an
  existing password.
- When `auth.json` does not exist: Basic routes work normally;
  Expert/Admin routes return `503 setup_required`.

### HTTPS Requirement

- `POST /auth/login` and `POST /auth/step-up` reject non-loopback HTTP
  and accept non-loopback HTTPS. Loopback HTTP is allowed.
- Transport detection uses the actual TLS state of the connection (e.g.,
  TLS-wrapped socket or server TLS configuration), not client IP
  heuristics or `X-Forwarded-Proto`.
- The `Secure` cookie attribute follows TLS: set when the connection is TLS (including loopback TLS), omitted only for permitted loopback HTTP.
- Any request carrying a session cookie or Bearer credential requires actual TLS unless its client is loopback. External HTTP is rejected before credential validation; `X-Forwarded-Proto` cannot override this.

### Login Rate Limiting

- Separate thread-safe store, independent of the general action limiter.
- 5 attempts per rolling 60 seconds per client IP.
- Returns 429 when exceeded.
- Each IP is tracked independently; window expiry resets the count.
- Concurrency-safe under parallel requests.
- Storage is hard-bounded to 1024 IP buckets: remove expired buckets under the same lock; before inserting a new IP at capacity, evict the oldest bucket.

### HTTP Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | No session or expired/invalid session (`WWW-Authenticate: Cookie`) |
| 403 | Session exists but role insufficient, or CSRF / Fetch Metadata failure |
| 403 | IP not in allowlist (existing, unchanged) |
| 429 | Rate limited (existing, unchanged) |
| 503 | Expert/Admin requested but `auth.json` not provisioned |

## Non-Functional Requirements

- No new pip dependencies. Pure stdlib (`hashlib`, `hmac`, `secrets`,
  `threading`, `time`, `json`, `os`).
- Session validation performs no PBKDF or filesystem I/O — only a
  digest computation and a locked dictionary lookup per request. On
  the target RPi, 1000 direct validations must report median ≤ 1 ms
  and p95 ≤ 5 ms.
- Password hashing adds latency at login only; the iteration count is
  calibrated per-device via a multi-sample benchmark whose median falls
  within the target range.
- `AuthStore` may reload config at startup and on login or Bearer lookup
  when mtime changes, but never on ordinary session-authenticated
  requests. Credential rotation does not revoke existing in-memory
  sessions; a dashboard restart is required when revocation is intended.
- All existing tests pass with compatibility tests updated where
  necessary (Basic routes remain unauthenticated).
- Household playback is never interrupted by auth state.
- Thread safety: `AuthStore` and `SessionStore` use `threading.Lock`
  with non-nested acquisition and private unlocked helpers for all
  shared reads and writes. Concurrency tests exercise parallel
  create/validate/destroy and concurrent read/write.

## Constraints

- Existing `ALLOWED_SUBNETS` IP allowlist is preserved unchanged.
- Existing rate limiting is preserved unchanged.
- Existing CORS policy is preserved unchanged.
- Existing terminal WebSocket token (`WS_AUTH_TOKEN`) is gated behind
  Admin auth; the token itself is not replaced.
- The `dashboard-security-cleanup_20260723` track is complete and must
  not be modified.

## Acceptance Criteria

- [ ] `auth.json` absent: all Basic routes return 200; Expert/Admin
  routes return 503 `setup_required`.
- [ ] `auth.json` present with expert password only: Expert routes
  return 200 after login with `role=expert`; Admin routes return 503
  via `is_role_provisioned(ADMIN)` = False; login with `role=admin`
  returns 401.
- [ ] `auth.json` present with admin password only: both Expert and
  Admin routes are accessible (admin credential satisfies Expert via
  hierarchy).
- [ ] Login with `role` field matching wrong hash returns 401, never
  silently grants access.
- [ ] Admin step-up from Expert session succeeds and expires after
  5 minutes.
- [ ] Session validation: 1000 direct validations on target RPi report
  median ≤ 1 ms and p95 ≤ 5 ms; no PBKDF or filesystem I/O.
- [ ] X-CSRF-Token header validation: rejects cross-site
  Expert/Admin mutations; rejects missing provenance from non-loopback;
  accepts same-origin with valid Origin/Referer.
- [ ] Logout and step-up require CSRF (X-CSRF-Token header); requests
  without the header are rejected.
- [ ] Basic mutating routes reject `Sec-Fetch-Site: cross-site`; reject missing provenance from non-loopback; accept missing provenance from loopback and accept non-loopback `same-origin`/`same-site`.
- [ ] Login and step-up reject non-loopback HTTP; accept non-loopback
  HTTPS; allow loopback HTTP.
- [ ] Login rate limiter: 6th attempt within 60 seconds returns 429;
  independent IPs tracked separately; window expiry resets count;
  concurrent access safe; storage never exceeds 1024 IP buckets and evicts the oldest bucket before inserting a new IP at capacity.
- [ ] Bearer-authenticated requests bypass CSRF only on permitted transport: external TLS and loopback HTTP are accepted; external HTTP is rejected before token validation.
- [ ] API token creation prints raw value once (local CLI only);
  subsequent lookups use only the SHA-256 digest; raw value not in
  `auth.json`.
- [ ] `tools/auth_setup.py` reads passwords via askpass/getpass, writes
  `auth.json` with mode 0600, creates backup before overwrite, never
  prints passwords.
- [ ] Login and step-up require HTTPS; loopback alone may use HTTP.
- [ ] `AuthStore` and `SessionStore` are thread-safe; concurrency tests
  pass.
- [ ] Rollback never removes or overwrites a real user `auth.json`;
  tests use temp paths; provisioning creates backup before replacement.
- [ ] All pytest tests pass with compatibility tests updated where
  necessary.
- [ ] Full route-inventory regression: `/modes` (GET), `/return` (POST),
  `/system/reboot` (GET), `/audio/route/dlna-input/status` (GET Basic),
  `/bt/discovery` (GET Expert), and every path in `api/routes.py` plus
  successful legacy dispatch is classified in `ENDPOINT_ROLES` or
  explicitly exempt. Fail-closed prefixes include `/mpv/*`, `/devices/*`,
  `/network/*`, `/restart/*`, `/youtube/*`, `/media/*`, `/cache/*`,
  `/pool/*`, `/ha/*`, `/selftest/*`, `/ws/*`, `/keepalive`.
- [ ] `uv run ruff check .` passes.
- [ ] `git diff --check` clean.

## Out of Scope

- Public internet exposure or external identity providers.
- Per-user accounts (single household password model).
- Frontend role-aware UI rendering (owned by
  `unified-ui-ux-refactor_20260728`).
- WebSocket PTY transport implementation (separate track).
- Admin API-key creation endpoint (not in current scope; local CLI only).
