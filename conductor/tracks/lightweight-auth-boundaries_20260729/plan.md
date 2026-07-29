# Implementation Plan: Lightweight Auth Boundaries

## Prerequisites

- `dashboard-security-cleanup_20260723` is complete (terminal WS token
  auth, Wi-Fi stdin, Bandit findings documented).
- All existing pytest tests pass before this track begins.
- `uv run ruff check .` passes before this track begins.
- **Global rollback invariant:** rollback touches only dedicated tracked
  implementation commits or reviewed reverse patches; it never deletes,
  overwrites, or restores runtime/user `auth.json`.

## Phase 1: Conductor Track Setup

- [x] Task: Create `conductor/tracks/lightweight-auth-boundaries_20260729/`
  with `metadata.json`, `spec.md`, `spec.cz.md`, `plan.md`, `plan.cz.md`.
  Register in `conductor/tracks.md` with open `[ ]` entry and explicit
  dependency on `dashboard-security-cleanup_20260723`.
  - **Test:** `cat conductor/tracks.md | grep lightweight-auth-boundaries`
    shows the entry. `python3 -c "import json; json.load(open('conductor/tracks/lightweight-auth-boundaries_20260729/metadata.json'))"` succeeds.
  - **Evidence:** `git diff --stat` shows only conductor files changed.
  - **Rollback:** revert the Phase 1 commit via `git revert` or reviewed reverse patch; preserve any runtime/user config.

## Phase 2: Auth Core (`rpi_dashboard/auth.py`)

- [x] Task: Create `rpi_dashboard/auth.py` with `Role` enum
  (`BASIC = 0`, `EXPERT = 1`, `ADMIN = 2`), comparison operators,
  and `Role.__ge__` for hierarchy checks.
  - **Test:** `test_role_hierarchy`: `ADMIN >= EXPERT >= BASIC` is True;
    `BASIC >= EXPERT` is False.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the Phase 2 commit that added `auth.py`.

- [x] Task: Implement `calibrate_pbkdf2(target_ms=200, samples=3)` that
  benchmarks `hashlib.pbkdf2_hmac("sha256", password_bytes, salt, n)`
  for each candidate iteration count in `[100_000, 200_000, 400_000,
  600_000, 800_000, 1_000_000]`. For each candidate, run `samples`
  trials and compute the median. Estimate the optimal count whose
  median lands within 150–300 ms, clamp to safe bounds (100_000–
  1_000_000), verify the final multi-sample median lies within
  150–300 ms, and fail provisioning with an actionable error if no
  candidate satisfies the target. Unit tests mock timings; live RPi
  evidence records median/p95.
  - **Test:** `test_calibrate_pbkdf2_returns_positive_int`: result is
    an int > 0. `test_calibrate_pbkdf2_target_range`: result is between
    100_000 and 1_000_000. `test_calibrate_pbkdf2_verification_step`:
    confirm the returned iteration count produces a median within the
    target range when benchmarked. `test_calibrate_pbkdf2_fails_when_no_candidate`:
    mock timings where no candidate reaches target, verify provisioning
    raises actionable error.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added `calibrate_pbkdf2`.

- [x] Task: Implement `hash_password(password: str) -> dict` returning
  `{password_hash: base64, salt: base64, iterations: int}` and
  `verify_password(password: str, stored: dict) -> bool`.
  - **Test:** `test_hash_and_verify_roundtrip`: hash then verify
    succeeds. `test_verify_wrong_password_fails`: wrong password returns
    False. `test_stored_dict_contains_required_keys`: output has
    `password_hash`, `salt`, `iterations`.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added `hash_password`/`verify_password`.

- [x] Task: Implement `AuthStore` class with `threading.Lock` protecting
  every shared read and write (non-nested acquisition, private `_unlocked`
  helpers called only while caller holds the lock):
  - `__init__(path)`: sets config path, loads if exists.
  - `load()`: reads `auth.json`, returns dict or empty dict.
  - `save(data)`: acquires lock, atomic write (temp file → fsync →
    rename), mode 0600. Directory created with mode 0700 if missing.
  - `is_provisioned() -> bool`: True if expert or admin hash exists.
  - `is_role_provisioned(role: Role) -> bool`: True if the given role
    has a stored hash. Expert is provisioned by either Expert or Admin
    credential; Admin only by Admin credential.
  - `get_expert_hash() -> dict | None`, `get_admin_hash() -> dict | None`.
  - `set_expert(password)`, `set_admin(password)`: hash and store under
    lock. Before overwriting an existing file, create a mode-0600 backup.
  - `api_keys` dict keyed by SHA-256 digest of raw token. Each record:
    `{role, label, created}`. No prefix stored.
  - `create_api_key(raw_token, role, label)`: stores role+label under
    digest key.
  - `get_api_key_role(raw_token) -> Role | None`: SHA-256 lookup.
  - **Test:** `test_auth_store_is_provisioned_false_when_missing`:
    nonexistent path returns False. `test_auth_store_set_and_get_expert`:
    set expert password, verify is_provisioned and get_expert_hash.
    `test_auth_store_atomic_write_permissions`: file mode is 0o600.
    `test_auth_store_backup_on_overwrite`: set expert, set again, verify
    `.bak` file exists with same hash. `test_is_role_provisioned_expert_by_admin`:
    only admin hash set, is_role_provisioned(EXPERT) returns True.
    `test_is_role_provisioned_admin_requires_admin`: only expert hash
    set, is_role_provisioned(ADMIN) returns False. `test_api_key_create_and_lookup`:
    create key, lookup by raw token returns correct role.
    `test_api_key_not_stored_plaintext`: raw token not in file contents.
    `test_api_key_digest_only_key`: auth.json api_keys keys are
    hex digests, no prefix field. `test_auth_store_concurrent_reads_writes`:
    10 threads performing parallel reads and writes produce valid
    auth.json without corruption.
  - **Evidence:** pytest output shows pass; test-created config in tmp_path has mode 0o600.
  - **Rollback:** revert the commit that added `AuthStore`; any test-created auth.json lives in tmp_path and is discarded automatically.

## Phase 3: Session Store

- [ ] Task: Implement `SessionStore` class with `threading.Lock` for all
  dict operations (non-nested acquisition, private unlocked helpers):
  - `create(role: Role) -> tuple[str, SessionSnapshot]`: generates
    `token = secrets.token_bytes(32)`, computes `key = sha256(token)`,
    stores mutable `Session` in dict under Lock, returns
    `(token.hex(), SessionSnapshot)` — an immutable copy. Internal
    mutable Session never escapes.
  - `validate(cookie_hex: str) -> tuple[Role | None, SessionSnapshot | None]`:
    `bytes.fromhex` → `sha256` → dict lookup under Lock. Returns None
    if expired. Sliding window: refreshes `last_seen` under Lock.
    Returns immutable `SessionSnapshot`.
  - `step_up(cookie_hex: str) -> bool`: after the auth endpoint has verified the admin password, revalidates under Lock that the token names a live Expert session, then atomically sets `step_up_expires = now + 300`. `effective_role` derives Admin while that deadline remains valid. `SessionStore` performs no password verification or PBKDF.
  - `effective_role(cookie_hex: str) -> Role`: looks up session by
    digest under Lock, returns `ADMIN` if `step_up_expires` not reached,
    else `session.role`.
  - `destroy(cookie_hex: str)`: removes session from dict under lock.
  - `cleanup()`: removes expired sessions (called periodically).
  - Configurable TTLs: `EXPERT_TTL = 28800` (8h),
    `ADMIN_TTL = 1800` (30min), `STEPUP_TTL = 300` (5min).
  - **Test:** `test_session_create_and_validate`: create Expert session,
    validate returns Expert role. `test_session_validate_expired`:
    create session, advance injected clock past TTL, validate returns
    None.
    `test_session_step_up`: after the endpoint has verified an admin credential, step_up on a live Expert session makes effective_role return Admin. `test_session_step_up_expiry`:
    step_up, advance time past 5min, effective_role reverts to Expert.
    `test_session_destroy`: validate after destroy returns None.
    `test_session_benchmark_on_rpi`: run 1000 direct validations on
    target RPi, assert median ≤ 1 ms and p95 ≤ 5 ms; no PBKDF or
    filesystem I/O.
    `test_session_concurrent_create_validate_destroy`: 20 threads
    performing random create/validate/destroy in parallel complete
    without corruption or exception.
    `test_session_expiry_injected_clock`: advance injected clock past
    TTL, verify validate returns None; do not mutate returned object.
  - **Evidence:** pytest output shows pass. Benchmark output shows
    median and p95 values for manual review.
  - **Rollback:** revert the commit that added `SessionStore`.

## Phase 4: Route Policy

- [ ] Task: Implement `ENDPOINT_ROLES` dict mapping `(path, method)` →
  `RoutePolicy` with fields `required_role: Role | None`,
  `mutating: bool`. Populate per the spec route tables. Include a
  `validate_basic_csrf(path, method, headers, is_loopback: bool) -> bool` helper that
  returns True if the request passes the Fetch Metadata / Origin defence
  for Basic routes with mutating=true, regardless of HTTP verb.
  - **Test:** `test_basic_routes_require_no_auth`: `/mpv/play` GET,
    `/mpv/status` GET, `/audio/state` GET map to `required_role=None`. `test_route_policy_mutating_flags`: assert `/mpv/play` GET, `/audio/mute` GET, `/return` POST, and `/report` POST are Basic with `mutating=True`; `/mpv/status` GET is Basic with `mutating=False`; `/system/logs` GET is Admin with `mutating=False`; `/system/reboot` GET is Admin with `mutating=True`.
    `test_mpv_memory_save_requires_expert`: `/mpv/memory-save` GET maps
    to `required_role=EXPERT`. `test_mpv_memory_clear_requires_expert`:
    `/mpv/memory/clear` GET maps to `required_role=EXPERT`.
    `test_system_logs_requires_admin`: `/system/logs` GET maps to
    `required_role=ADMIN`. `test_expert_routes_require_expert`:
    `/audio/default-sink` GET, `/bt/pair` GET, `/wifi/connect` GET+POST
    map to `required_role=EXPERT`. `test_admin_routes_require_admin`:
    `/terminal/connect` GET, `/system/restart-rpi` GET,
    `/system/reboot` GET, `/ws/token` GET
    map to `required_role=ADMIN`. `test_unknown_protected_route_defaults_to_admin`:
    `/audio/new-feature` POST maps to Admin. `test_unknown_unprotected_route_returns_none`:
    `/foo/bar` GET maps to None (404, not auth). `test_deprecated_routes_return_410`:
    `/play` GET, `/kodi/status` GET map to deprecated.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added `ENDPOINT_ROLES`.

- [ ] Task: Implement `classify_request(path, method, session, auth_store)
  -> tuple[Role | None, int | None]` that returns `(required_role,
  error_code)` where error_code is 401/403/405/410/503 or None. Handles:
  - Unprovisioned state (503 for Expert/Admin).
  - Missing session (401 for Expert/Admin).
  - Insufficient role (403).
  - Deprecated routes (410).
  - Method not allowed for route (405).
  - Role-aware: Expert route with only admin hash provisioned returns
    200 (admin satisfies Expert); Admin route with only expert hash
    returns 503 (expert does not satisfy Admin).
  - **Test:** `test_classify_unprovisioned_returns_503`: no auth.json,
    Expert route returns 503. `test_classify_missing_session_401`:
    provisioned, no cookie, Expert route returns 401.
    `test_classify_wrong_role_403`: Expert session, Admin route returns
    403. `test_classify_basic_no_session`: Basic route returns (None, None).
    `test_classify_deprecated_410`: `/play` returns 410.
    `test_classify_method_not_allowed_405`: `/mpv/status` POST returns
    405. `test_classify_admin_hash_satisfies_expert_route`: only admin
    hash set, Expert route returns (EXPERT, None).
    `test_classify_expert_hash_does_not_satisfy_admin_route`: only
    expert hash set, Admin route returns (ADMIN, 503).
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added `classify_request`.

- [ ] Task: Implement `validate_basic_csrf(path, method, headers, is_loopback: bool) -> bool`
  that applies Fetch Metadata / Origin defence for Basic routes with mutating=true, regardless of HTTP verb:
  - If `Sec-Fetch-Site` header is present and is `cross-site`, return False (403).
  - If `Origin` or `Referer` header is present, validate against
    `ALLOWED_SUBNETS` or `localhost`/`*.local`. Return False if invalid.
  - If neither header is present, return True if `is_loopback` is True,
    else return True only if `Sec-Fetch-Site` is `same-origin` or `same-site`,
    otherwise return False (accept non-browser automation under subnet
    allowlist only for loopback or same-origin/site).
  - **Test:** `test_basic_csrf_rejects_cross_site_fetch`: request with
    `Sec-Fetch-Site: cross-site` returns False. `test_basic_csrf_rejects_bad_origin`:
    request with `Origin: https://evil.example` returns False.
    `test_basic_csrf_accepts_valid_origin`: request with
    `Origin: http://192.168.0.10:8090` returns True.
    `test_basic_csrf_accepts_no_headers_on_loopback`: request with no Sec-Fetch-Site,
    no Origin, no Referer, and `is_loopback=True` returns True. `test_basic_csrf_accepts_localhost_referer`:
    request with `Referer: http://localhost:8090/mpv/play` returns True. `test_basic_csrf_rejects_missing_provenance_non_loopback`: no Sec-Fetch-Site, Origin, or Referer with `is_loopback=False` returns False. `test_basic_csrf_accepts_same_origin_non_loopback`: no Origin/Referer, `Sec-Fetch-Site: same-origin`, `is_loopback=False` returns True. `test_basic_csrf_accepts_same_site_non_loopback`: no Origin/Referer, `Sec-Fetch-Site: same-site`, `is_loopback=False` returns True.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added `validate_basic_csrf`.

## Phase 5: CSRF Protection (Expert/Admin)

- [ ] Task: Implement Expert/Admin CSRF synchroniser-token helpers:
  - `generate_csrf_token() -> bytes`: `secrets.token_bytes(16)`.
  - `validate_csrf(session: SessionSnapshot, x_csrf_header: str | None,
    rpi_csrf_cookie: str | None, origin: str | None, referer: str |
    None, sec_fetch_site: str | None, is_loopback: bool) -> bool`: constant-time compare
    of `X-CSRF-Token` header with session's csrf_token hex
    (`hmac.compare_digest`). If `rpi_csrf_cookie` is present, header
    value must equal cookie value. Cross-site `Sec-Fetch-Site` values
    are rejected. Origin/Referer validated against `ALLOWED_SUBNETS` or
    `localhost`/`*.local`. When both Origin and Referer are absent, accept loopback; accept non-loopback only when `Sec-Fetch-Site` is `same-origin` or `same-site`; otherwise reject.
  - Session's `csrf_token` field populated at creation. `rpi_csrf`
    non-HttpOnly convenience cookie populated for frontend reads.
  - **Test:** `test_csrf_valid_header_and_origin_passes`: matching
    X-CSRF-Token header + valid origin returns True.
    `test_csrf_mismatched_header_fails`: wrong header value returns False.
    `test_csrf_bad_origin_fails`: valid header but unknown Origin host
    returns False. `test_csrf_cross_site_rejected`: `Sec-Fetch-Site:
    cross-site` with valid header returns False.
    `test_csrf_cross_origin_detected_via_origin`: valid header but
    cross-origin `Origin` host returns False.
    `test_csrf_same_origin_accepted`: no Origin/Referer,
    `Sec-Fetch-Site: same-origin`, non-loopback returns True.
    `test_csrf_same_site_accepted`: no Origin/Referer,
    `Sec-Fetch-Site: same-site`, non-loopback returns True.
    `test_csrf_missing_provenance_non_loopback_rejected`: no Origin,
    no Referer, no Sec-Fetch-Site, non-loopback IP returns False.
    `test_csrf_missing_provenance_loopback_accepted`: same headers,
    loopback IP returns True.
    `test_csrf_header_must_match_cookie_when_present`: X-CSRF-Token
    header differs from rpi_csrf cookie returns False.
    `test_csrf_uses_constant_time_compare`: confirm hmac.compare_digest
    is used (no timing leak).
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added Expert/Admin CSRF helpers.

## Phase 5b: Login Rate Limiter

- [ ] Task: Implement `LoginAttemptLimiter` class with `threading.Lock`:
  - `check_and_record(ip: str) -> bool`: returns True if attempt allowed
    (≤ 5 in rolling 60s), records timestamp. Returns False if exceeded.
  - Under the same Lock, remove expired buckets; before recording a previously unseen IP, if 1024 buckets remain, evict the oldest, then insert. Storage must never exceed 1024 IP buckets.
  - Bounded internal dict (max 1024 IP buckets); concurrent-safe.
  - **Test:** `test_login_limiter_allows_first_five`: 5 attempts from same
    IP succeed (all return True). `test_login_limiter_blocks_sixth`:
    6th attempt within 60s returns False. `test_login_limiter_independent_ips`:
    different IPs tracked separately. `test_login_limiter_expiry`: after
    60s window, count resets. `test_login_limiter_concurrent`: 10 threads
    calling check_and_record in parallel for one IP, exactly 5 return
    True and 5 return False. `test_login_limiter_storage_bounded`: record more than 1024 unique IPs and assert the internal bucket count never exceeds 1024 and the oldest bucket is evicted.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added `LoginAttemptLimiter`.

## Phase 6: Provisioning CLI

- [ ] Task: Create `tools/auth_setup.py` with subcommands `expert`,
  `admin`, `api-key`. Uses `ssh-askpass` / `$SSH_ASKPASS` when
  `$DISPLAY` or `$SSH_ASKPASS` is set, falls back to `getpass.getpass()`.
  Passwords are never passed as argv.
  - `expert`: prompts for expert password, hashes with benchmarked
    iterations, writes to auth.json (creates backup first if exists).
  - `admin`: prompts for admin password, same flow.
  - `api-key <label> [role]`: generates `secrets.token_urlsafe(32)`,
    prints raw value once via stdout, stores SHA-256 digest in auth.json.
  - All writes use `AuthStore.save()` (atomic, mode 0600).
  - **Test:** `test_auth_setup_expert_creates_auth_json`: run with
    mocked askpass, verify auth.json exists with expert hash.
    `test_auth_setup_backup_created_on_overwrite`: run twice, verify
    `.bak` file exists. `test_auth_setup_api_key_prints_once`: capture
    stdout, verify raw token appears exactly once. `test_auth_setup_no_plaintext_in_file`:
    verify raw token string not in auth.json contents.
    `test_auth_setup_uses_askpass_when_display_set`: mock $DISPLAY, verify
    ssh-askpass is invoked. `test_auth_setup_fallback_to_getpass`: no
    $DISPLAY, no $SSH_ASKPASS, verify getpass is invoked.
  - **Evidence:** pytest output shows pass. Manual: run
    `python tools/auth_setup.py expert` and verify askpass/getpass prompt.
  - **Rollback:** revert the commit that added `tools/auth_setup.py`; test auth.json lives in tmp_path.

## Phase 7: Middleware Integration

- [ ] Task: Extend `rpi_dashboard/api/middleware.py` with:
  - `extract_session_cookie(request) -> str | None`: reads `rpi_session`
    cookie from request headers.
  - `extract_bearer_role(request, auth_store) -> Role | None`: reads
    `Authorization: Bearer` header, validates via `auth_store`.
  - `set_session_cookie(handler, token_hex, max_age, is_tls: bool)`:
    sets `Set-Cookie` with HttpOnly, SameSite=Lax, Path=/. `Secure`
    attribute set iff `is_tls`.
  - `set_csrf_cookie(handler, csrf_hex, is_tls: bool)`: sets `rpi_csrf`
    non-HttpOnly cookie with `Path=/`, `SameSite=Strict`, `Secure` iff
    `is_tls`.
  - `credential_transport_allowed(is_tls: bool, is_loopback: bool) -> bool`:
    returns True if credential endpoint is permitted (loopback HTTP
    allowed, external requires TLS).
  - `is_https(handler) -> bool`: returns True if the connection uses TLS
    (checks socket or server state, not IP or headers).
  - **Test:** `test_extract_session_cookie_parses_header`: mock request
    with cookie header, verify extraction. `test_extract_bearer_valid`:
    mock request with valid Bearer, verify role returned.
    `test_set_session_cookie_secure_for_loopback_tls`: verify Secure flag present
    for loopback TLS. `test_set_session_cookie_no_secure_for_loopback_http`:
    verify Secure flag absent for loopback HTTP.
    `test_set_csrf_cookie_secure_for_loopback_tls`: verify Secure flag present
    for loopback TLS. `test_set_csrf_cookie_no_secure_for_loopback_http`: verify
    Secure flag absent for loopback HTTP.
    `test_is_https_external_tls`: external TLS connection returns True.
    `test_is_https_external_http`: external HTTP returns False.
    `test_is_https_loopback_http`: loopback HTTP returns False (TLS
    detection reports transport only).
    `test_credential_transport_allowed_loopback_http`: loopback HTTP
    accepted by credential transport policy.
    `test_credential_transport_rejects_external_http`: external HTTP
    rejected.
    `test_is_https_rejects_x_forwarded_proto`: external HTTP with `X-Forwarded-Proto: https` still returns False.
    `test_credential_transport_allowed_external_tls`: external TLS
    accepted.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added middleware auth helpers.

## Phase 8: Webserver Auth Endpoints and Gates

- [ ] Task: Add auth endpoints to `webserver.py`:
  - `POST /auth/login`: accepts `{"password": "...", "role": "expert|admin"}`,
    verifies against the hash for the requested role only (never silently
    prefers the other), creates session, sets cookies, returns `{ok, role}`.
    Requires HTTPS (loopback exempt). Applies Origin / Fetch Metadata
    checks. Rate limit: 5/min/IP.
  - `POST /auth/logout`: destroys session, clears cookies. Requires
    CSRF (X-CSRF-Token header).
  - `GET /auth/whoami`: returns `{authenticated, role, setup_required}`.
  - `POST /auth/step-up`: accepts `{"password": "..."}`, verifies admin
    hash, elevates Expert session for 5 minutes. Requires HTTPS and
    CSRF (X-CSRF-Token header).
  - **Test:** `test_auth_login_success`: POST with correct expert
    password and `role=expert` returns 200 + session cookie.
    `test_auth_login_wrong_password`: returns 401.
    `test_auth_login_wrong_role`: expert password with `role=admin`
    returns 401 (not silently accepted).
    `test_auth_login_unprovisioned`: returns 503. `test_auth_login_accepts_external_tls`: login over external TLS returns 200.
    `test_auth_login_rejects_external_http`: plain HTTP from non-loopback
    returns 403. `test_auth_login_allows_loopback_http`: loopback
    HTTP accepted. `test_auth_login_rejects_spoofed_x_forwarded_proto`: external HTTP with `X-Forwarded-Proto: https` returns 403. `test_auth_logout_clears_session`: login then logout,
    subsequent Expert request returns 401.
    `test_auth_whoami_basic_when_unprovisioned`: returns
    `{authenticated: false, role: "basic"}`.
    `test_auth_step_up`: Expert session + admin password returns Admin
    role for 5 minutes. `test_auth_step_up_accepts_external_tls`: step-up over external TLS returns 200. `test_auth_step_up_rejects_external_http`: plain HTTP
    step-up from non-loopback returns 403. `test_auth_step_up_allows_loopback_http`: loopback HTTP step-up returns 200. `test_auth_step_up_rejects_spoofed_x_forwarded_proto`: external HTTP step-up with `X-Forwarded-Proto: https` returns 403.
    `test_auth_logout_requires_csrf`: logout without X-CSRF-Token header
    returns 403. `test_auth_step_up_requires_csrf`: step-up without
    X-CSRF-Token header returns 403.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added auth endpoints.

- [ ] Task: Add auth gate in `do_GET` and `do_POST` after IP allowlist.
  Gate logic per request:
  1. Extract session cookie or Bearer token.
  2. If either credential is present and `credential_transport_allowed()` is false, return 403 before credential validation; external HTTP must never carry Cookie or Bearer credentials, while loopback HTTP remains allowed.
  3. Call `classify_request()`.
  4. Return 401/403/503 as appropriate.
  5. For Basic routes (None required_role): apply `validate_basic_csrf` when `RoutePolicy.mutating=True`, regardless of HTTP verb, then pass through.
  6. For Expert/Admin routes with valid session: check CSRF (X-CSRF-Token header + Origin/Referer + Sec-Fetch-Site) on requests whose `RoutePolicy.mutating=True`, regardless of HTTP verb.
  7. Bearer requests skip CSRF only after the transport check passes.
  - **Test:** `test_all_routes_classified`: every path from `api/routes.py`
    and legacy dispatch is in `ENDPOINT_ROLES` or exempt. Explicitly
    assert `/audio/route/dlna-input/status` (Basic), `/bt/discovery`
    (Expert), `/modes` (Basic), `/return` POST (Basic),
    `/system/reboot` (Admin).
    `test_gate_allows_basic_without_session`: `/mpv/status` GET
    returns 200 without cookie. `test_gate_blocks_expert_without_session`:
    `/audio/default-sink` GET returns 401 without cookie.
    `test_gate_allows_expert_with_session`: login then access Expert
    route returns 200. `test_gate_blocks_admin_with_expert_session`:
    Expert session + Admin route returns 403.
    `test_gate_csrf_rejects_missing_header`: Expert session + GET
    without X-CSRF-Token header returns 403.
    `test_gate_csrf_rejects_cross_site`: Expert session + GET with
    X-CSRF-Token but `Sec-Fetch-Site: cross-site` returns 403.
    `test_gate_bearer_skips_csrf`: Bearer token over external TLS + GET without X-CSRF-Token returns 200. `test_gate_rejects_bearer_on_external_http`: external HTTP with Bearer returns 403 before token validation. `test_gate_accepts_bearer_on_loopback_http`: loopback HTTP with valid Bearer succeeds. `test_gate_rejects_session_cookie_on_external_http`: external HTTP with a session cookie returns 403 before session validation.
    `test_gate_basic_mutating_rejects_cross_site_fetch`: `/mpv/play` GET
    with `Sec-Fetch-Site: cross-site` returns 403.
    `test_gate_basic_mutating_accepts_no_fetch_header`: `/mpv/play` GET
    from loopback with no Sec-Fetch-Site, Origin, or Referer returns 200. `test_gate_method_not_allowed`:
    `/mpv/status` POST returns 405.
    `test_gate_admin_route_requires_admin_role`: Expert session + Admin
    route returns 403. `test_gate_deprecated_returns_410`: `/play` GET
    returns 410.
  - **Evidence:** pytest output shows pass.
  - **Rollback:** revert the commit that added auth gates.

## Phase 9: Route Inventory Regression

- [ ] Task: Write a regression test that reads all registered routes
  from `rpi_dashboard/api/routes.py` and the legacy dispatch table in
  `webserver.py`, and asserts that every route appears in
  `ENDPOINT_ROLES` or is explicitly exempted (static assets, deprecated).
  This prevents new routes from drifting unclassified.
  - **Test:** `test_all_registered_routes_have_role_classification`:
    import the route registry and legacy dispatch, collect all paths,
    verify each is present in ENDPOINT_ROLES or in a documented exempt
    list. Explicitly assert `/modes` (GET Basic), `/return` (POST Basic),
    `/system/reboot` (GET Admin), `/audio/route/dlna-input/status`
    (GET Basic), `/bt/discovery` (GET Expert) are classified. Fail
    with a clear message listing any unclassified paths.
  - **Evidence:** pytest output shows pass; any new unclassified route
    fails the test.
  - **Rollback:** revert the commit that added the route inventory regression test.

## Phase 10: Integration Verification

- [ ] Task: Run full test suite, verify:
  - All existing tests pass with compatibility tests updated where
    necessary (Basic routes unchanged).
  - New auth tests pass.
  - `uv run ruff check .` clean.
  - `uv run mypy .` clean (if applicable).
  - Manual: start server without auth.json, verify Basic playback works,
    Expert/Admin return 503.
  - Manual: run `python tools/auth_setup.py expert` and
    `python tools/auth_setup.py admin`, verify askpass/getpass prompt,
    login works, step-up works, session expires.
  - Manual: run `python tools/auth_setup.py api-key test-label` and
    verify raw token printed once, then use it as Bearer.
  - **Test:** `uv run python -m pytest -q` — all pass.
  - **Evidence:** Full pytest output, ruff output, manual verification
    notes.
  - **Rollback:** revert the Phase 2–9 implementation commits in reverse
    order under the global rollback invariant (preserve runtime/user
    auth.json).

## Completion

- [ ] Task: Update `metadata.json` status to `"complete"`, add
  `completed_at` timestamp and `implementation_notes` summarising what
  was delivered.
- [ ] Task: Run `tools/verify-done.sh` and confirm exit code 0 with
  valid receipt.
- [ ] Task: Update `conductor/tracks.md` to mark `[x]`.
