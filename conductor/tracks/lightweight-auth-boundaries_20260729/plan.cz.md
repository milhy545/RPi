# Implementační plán: Lightweight Auth Boundaries

## Předpoklady

- `dashboard-security-cleanup_20260723` je dokončen (tokenová autentizace
  terminálového WebSocket, Wi-Fi přes stdin, Bandit nálezy zdokumentovány).
- Všechny existující pytest testy procházejí před zahájením tohoto tracku.
- `uv run ruff check .` prochází před zahájením tohoto tracku.
- **Globální pravidlo pro rollback:** rollback se dotýká pouze věnovaných
  sledovaných implementačních commitů nebo revidovaných reverzních patchů;
  nikdy neodstraňuje, nepíše přes ani neobnovuje runtime/user `auth.json`.

## Fáze 1: Příprava Conductor tracku

- [x] Úkol: Vytvořit `conductor/tracks/lightweight-auth-boundaries_20260729/`
  s `metadata.json`, `spec.md`, `spec.cz.md`, `plan.md`, `plan.cz.md`.
  Zaregistrovat v `conductor/tracks.md` s otevřeným `[ ]` záznamem a
  explicitní závislostí na `dashboard-security-cleanup_20260723`.
  - **Test:** `cat conductor/tracks.md | grep lightweight-auth-boundaries`
    zobrazí záznam. `python3 -c "import json; json.load(open('conductor/tracks/lightweight-auth-boundaries_20260729/metadata.json'))"` úspěšný.
  - **Evidence:** `git diff --stat` zobrazí pouze změněné conductor soubory.
  - **Rollback:** revertovat commit z fáze 1 přes `git revert` nebo recenzovaný reverse patch; zachovat runtime/user config.

## Fáze 2: Auth jádro (`rpi_dashboard/auth.py`)

- [x] Úkol: Vytvořit `rpi_dashboard/auth.py` s enum `Role`
  (`BASIC = 0`, `EXPERT = 1`, `ADMIN = 2`), operátory porovnání
  a `Role.__ge__` pro kontrolu hierarchie.
  - **Test:** `test_role_hierarchy`: `ADMIN >= EXPERT >= BASIC` je True;
    `BASIC >= EXPERT` je False.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit z fáze 2 který přidal `auth.py`.

- [x] Úkol: Implementovat `calibrate_pbkdf2(target_ms=200, samples=3)`
  který benchmarkuje `hashlib.pbkdf2_hmac("sha256", password_bytes, salt, n)`
  pro každý kandidátní počet iterací v `[100_000, 200_000, 400_000,
  600_000, 800_000, 1_000_000]`. Pro každého kandidáta spustí `samples`
  opakování a vypočítá medián. Odhadne optimální počet jehož medián
  leží v 150–300 ms, omezi na bezpečné hranice (100_000–1_000_000),
  ověří že finální multi-sample medián leží v 150–300 ms a selže
  provisioning s akční chybou pokud žádný kandidát nesplňuje cíl.
  Unit testy mockují časy; live RPi evidence zaznamenává medián/p95.
  - **Test:** `test_calibrate_pbkdf2_returns_positive_int`: výsledek je
    int > 0. `test_calibrate_pbkdf2_target_range`: výsledek je mezi
    100_000 a 1_000_000. `test_calibrate_pbkdf2_verification_step`:
    potvrdí že vrácený počet iterací produkuje medián v cílovém rozsahu
    při benchmarku. `test_calibrate_pbkdf2_fails_when_no_candidate`:
    mockovat časy kde žádný kandidát nedosáhne cíle, ověřit že
    provisioning vyhodí akční chybu.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal `calibrate_pbkdf2`.

- [x] Úkol: Implementovat `hash_password(password: str) -> dict` vracející
  `{password_hash: base64, salt: base64, iterations: int}` a
  `verify_password(password: str, stored: dict) -> bool`.
  - **Test:** `test_hash_and_verify_roundtrip`: hash poté verify úspěch.
    `test_verify_wrong_password_fails`: špatné heslo vrací False.
    `test_stored_dict_contains_required_keys`: výstup obsahuje
    `password_hash`, `salt`, `iterations`.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal `hash_password`/`verify_password`.

- [x] Úkol: Implementovat třídu `AuthStore` s `threading.Lock` chránící
  každé sdílené čtení a zápis (non-nested získávání, privátní `_unlocked`
  helpery volané pouze když volající drží lock):
  - `__init__(path)`: nastaví cestu konfigurace, načte pokud existuje.
  - `load()`: čte `auth.json`, vrací dict nebo prázdný dict.
  - `save(data)`: získá lock, atomický zápis (temp soubor → fsync →
    rename), mód 0600. Adresář vytvořen s módem 0700 pokud chybí.
  - `is_provisioned() -> bool`: True pokud existuje expert nebo admin hash.
  - `is_role_provisioned(role: Role) -> bool`: True pokud má daná role
    uložený hash. Expert je provisionován buď Expert nebo Admin credential;
    Admin pouze Admin credential.
  - `get_expert_hash() -> dict | None`, `get_admin_hash() -> dict | None`.
  - `set_expert(password)`, `set_admin(password)`: hash a uloží pod lockem.
    Před přepsáním existujícího souboru vytvoří zálohu s módem 0600.
  - `api_keys` dict klíčovaný SHA-256 digestem raw tokenu. Každý záznam:
    `{role, label, created}`. Žádný prefix se neukládá.
  - `create_api_key(raw_token, role, label)`: ukládá role+label pod
    digest klíč.
  - `get_api_key_role(raw_token) -> Role | None`: SHA-256 lookup.
  - **Test:** `test_auth_store_is_provisioned_false_when_missing`:
    neexistující cesta vrací False. `test_auth_store_set_and_get_expert`:
    nastavit expert heslo, ověřit is_provisioned a get_expert_hash.
    `test_auth_store_atomic_write_permissions`: mód souboru je 0o600.
    `test_auth_store_backup_on_overwrite`: nastavit expert, nastavit znovu,
    ověřit že `.bak` soubor existuje se stejným hashem.
    `test_is_role_provisioned_expert_by_admin`: pouze admin hash nastaven,
    is_role_provisioned(EXPERT) vrací True.
    `test_is_role_provisioned_admin_requires_admin`: pouze expert hash
    nastaven, is_role_provisioned(ADMIN) vrací False.
    `test_api_key_create_and_lookup`: vytvořit klíč, lookup podle raw
    tokenu vrací správnou roli. `test_api_key_not_stored_plaintext`:
    raw token není v obsahu souboru. `test_api_key_digest_only_key`:
    auth.json api_keys klíče jsou hex digesty, bez pole prefix.
    `test_auth_store_concurrent_reads_writes`: 10 vláken provádějících
    paralelní čtení a zápisy produkuje validní auth.json bez poškození.
  - **Evidence:** výstup pytest ukazuje pass; testovací konfigurace vytvořená v `tmp_path` má mód 0o600.
  - **Rollback:** revertovat commit který přidal `AuthStore`; testovací auth.json žije v tmp_path a automaticky se zahodí.

## Fáze 3: Session Store

- [x] Úkol: Implementovat třídu `SessionStore` s `threading.Lock` pro
  všechny operace na dict (non-nested získávání, privátní unlocked helpery):
  - `create(role: Role) -> tuple[str, SessionSnapshot]`: generuje
    `token = secrets.token_bytes(32)`, počítá `key = sha256(token)`,
    ukládá mutovatelnou `Session` do dict pod Lockem, vrací
    `(token.hex(), SessionSnapshot)` — immutable kopii. Interní
    mutovatelná Session nikdy neuniká.
  - `validate(cookie_hex: str) -> tuple[Role | None, SessionSnapshot | None]`:
    `bytes.fromhex` → `sha256` → dict lookup pod Lockem. Vrací None
    pokud vypršelo. Sliding window: obnovuje `last_seen` pod Lockem.
    Vrací immutable `SessionSnapshot`.
  - `step_up(cookie_hex: str) -> bool`: poté co auth endpoint ověřil admin heslo, pod Lockem znovu ověří, že token označuje živou Expert session, a atomicky nastaví `step_up_expires = now + 300`. `effective_role` odvodí Admin po dobu platnosti tohoto deadline. `SessionStore` neprovádí ověřování hesla ani PBKDF.
  - `effective_role(cookie_hex: str) -> Role`: vyhledá session pod
    digestem pod Lockem, vrací `ADMIN` pokud `step_up_expires`
    nedosaženo, jinak `session.role`.
  - `destroy(cookie_hex: str)`: odebere session z dict pod lockem.
  - `cleanup()`: odebere vypršelé session (voláno periodicky).
  - Konfigurovatelné TTL: `EXPERT_TTL = 28800` (8h),
    `ADMIN_TTL = 1800` (30min), `STEPUP_TTL = 300` (5min).
  - **Test:** `test_session_create_and_validate`: vytvořit Expert session,
    validate vrací Expert roli. `test_session_validate_expired`:
    vytvořit session, posune injektované hodiny přes TTL, validate vrací
    None.
    `test_session_step_up`: poté co endpoint ověřil admin credential, step_up na živé Expert relaci způsobí, že `effective_role` vrací Admin. `test_session_step_up_expiry`: po step-up posunout injektovaný čas za 5 minut, `effective_role` se vrátí na Expert.
    `test_session_destroy`: validate po destroy vrací None.
    `test_session_benchmark_on_rpi`: na cílovém RPi spustit 1000 přímých validací a ověřit medián ≤ 1 ms a p95 ≤ 5 ms; žádný PBKDF ani filesystem I/O.
    `test_session_concurrent_create_validate_destroy`: 20 vláken
    provádějících náhodný create/validate/destroy paralelně dokončí
    bez poškození nebo výjimky. `test_session_expiry_injected_clock`: posunout injektované hodiny za TTL, ověřit že `validate` vrací None; nemutovat vrácený objekt.
  - **Evidence:** výstup pytest ukazuje pass. Benchmark output ukazuje
    medián a p95 hodnoty pro ruční kontrolu.
  - **Rollback:** revertovat commit který přidal `SessionStore`.

## Fáze 4: Route Policy

- [x] Úkol: Implementovat dict `ENDPOINT_ROLES` mapující
  `(path, method)` → `RoutePolicy` s poli `required_role: Role | None`,
  `mutating: bool`. Naplnit dle tabulek rout ze specifikace. Zahrnout
  helper `validate_basic_csrf(path, method, headers, is_loopback: bool) -> bool` který
  vrací True pokud request projde Fetch Metadata / Origin obranou pro Basic routy s `mutating=true`, bez ohledu na HTTP metodu.
  - **Test:** `test_basic_routes_require_no_auth`: `/mpv/play` GET,
    `/mpv/status` GET, `/audio/state` GET mapují na `required_role=None`. `test_route_policy_mutating_flags`: ověří, že `/mpv/play` GET, `/audio/mute` GET, `/return` POST a `/report` POST jsou Basic s `mutating=True`; `/mpv/status` GET je Basic s `mutating=False`; `/system/logs` GET je Admin s `mutating=False`; `/system/reboot` GET je Admin s `mutating=True`.
    `test_mpv_memory_save_requires_expert`: `/mpv/memory-save` GET mapuje
    na `required_role=EXPERT`. `test_mpv_memory_clear_requires_expert`:
    `/mpv/memory/clear` GET mapuje na `required_role=EXPERT`.
    `test_system_logs_requires_admin`: `/system/logs` GET mapuje na
    `required_role=ADMIN`. `test_expert_routes_require_expert`:
    `/audio/default-sink` GET, `/bt/pair` GET, `/wifi/connect` GET+POST
    mapují na `required_role=EXPERT`. `test_admin_routes_require_admin`:
    `/terminal/connect` GET, `/system/restart-rpi` GET, `/system/reboot` GET, `/ws/token` GET
    mapují na `required_role=ADMIN`. `test_unknown_protected_route_defaults_to_admin`:
    `/audio/new-feature` POST mapuje na Admin. `test_unknown_unprotected_route_returns_none`:
    `/foo/bar` GET mapuje na None (404, ne auth). `test_deprecated_routes_return_410`:
    `/play` GET, `/kodi/status` GET mapují na deprecated.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal `ENDPOINT_ROLES`.

- [x] Úkol: Implementovat `classify_request(path, method, session, auth_store)
  -> tuple[Role | None, int | None]` který vrací `(required_role,
  error_code)` kde error_code je 401/403/405/410/503 nebo None. Řeší:
  - Nestav provisionovaný stav (503 pro Expert/Admin).
  - Chybějící session (401 pro Expert/Admin).
  - Nedostatečná role (403).
  - Zastaralé routy (410).
  - Metoda nepovolená pro route (405).
  - Role-aware: Expert route s pouze admin hash provisionovaným vrací
    200 (admin splňuje Expert); Admin route s pouze expert hash vrací
    503 (expert nesplňuje Admin).
  - **Test:** `test_classify_unprovisioned_returns_503`: žádný auth.json,
    Expert route vrací 503. `test_classify_missing_session_401`:
    nakonfigurováno, žádný cookie, Expert route vrací 401.
    `test_classify_wrong_role_403`: Expert session, Admin route vrací
    403. `test_classify_basic_no_session`: Basic route vrací (None, None).
    `test_classify_deprecated_410`: `/play` vrací 410.
    `test_classify_method_not_allowed_405`: `/mpv/status` POST vrací 405.
    `test_classify_admin_hash_satisfies_expert_route`: pouze admin hash
    nastaven, Expert route vrací (EXPERT, None).
    `test_classify_expert_hash_does_not_satisfy_admin_route`: pouze
    expert hash nastaven, Admin route vrací (ADMIN, 503).
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal `classify_request`.

- [x] Úkol: Implementovat `validate_basic_csrf(path, method, headers, is_loopback: bool) -> bool`
  která aplikuje Fetch Metadata / Origin obranu pro Basic routy s `mutating=true`, bez ohledu na HTTP metodu:
  - Pokud je přítomen header `Sec-Fetch-Site` a je `cross-site`, vrací False (403). Cross-origin se detekuje pouze neplatným hostem `Origin` nebo `Referer`.
  - Pokud je přítomen header `Origin` nebo `Referer`, ověří vůči
    `ALLOWED_SUBNETS` nebo `localhost`/`*.local`. Vrací False pokud
    neplatný.
  - Pokud nejsou přítomny `Origin` ani `Referer`, přijme loopback request. Non-loopback request přijme pouze s `Sec-Fetch-Site: same-origin` nebo `same-site`; bez provenance hlaviček jej odmítne.
  - **Test:** `test_basic_csrf_rejects_cross_site_fetch`: request s
    `Sec-Fetch-Site: cross-site` vrací False. `test_basic_csrf_rejects_bad_origin`:
    request s `Origin: https://evil.example` vrací False.
    `test_basic_csrf_accepts_valid_origin`: request s
    `Origin: http://192.168.0.10:8090` vrací True.
    `test_basic_csrf_accepts_no_headers_on_loopback`: request bez Sec-Fetch-Site, bez Origin, bez Referer a s `is_loopback=True` vrací True. `test_basic_csrf_accepts_localhost_referer`: request s `Referer: http://localhost:8090/mpv/play` vrací True. `test_basic_csrf_rejects_missing_provenance_non_loopback`: bez Sec-Fetch-Site, Origin i Referer a s `is_loopback=False` vrací False. `test_basic_csrf_accepts_same_origin_non_loopback`: bez Origin/Referer, `Sec-Fetch-Site: same-origin`, `is_loopback=False` vrací True. `test_basic_csrf_accepts_same_site_non_loopback`: bez Origin/Referer, `Sec-Fetch-Site: same-site`, `is_loopback=False` vrací True.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal `validate_basic_csrf`.

## Fáze 5: Ochrana CSRF (Expert/Admin)

- [x] Úkol: Implementovat CSRF synchroniser-token pomocné funkce pro
  Expert/Admin:
  - `generate_csrf_token() -> bytes`: `secrets.token_bytes(16)`.
  - `validate_csrf(session: SessionSnapshot, x_csrf_header: str | None,
    rpi_csrf_cookie: str | None, origin: str | None, referer: str |
    None, sec_fetch_site: str | None, is_loopback: bool) -> bool`: constant-time porovnání
    hlavičky `X-CSRF-Token` s csrf_token hex relace (`hmac.compare_digest`).
    Pokud je přítomen `rpi_csrf_cookie`, hodnota hlavičky se musí rovnat
    hodnotě cookie. Cross-site `Sec-Fetch-Site` hodnoty jsou odmítnuty.
    Origin/Referer validován vůči `ALLOWED_SUBNETS` nebo `localhost`/`*.local`.
    Pokud chybí Origin i Referer, přijme loopback; non-loopback přijme pouze s `Sec-Fetch-Site: same-origin` nebo `same-site`, jinak jej odmítne.
  - Pole `csrf_token` relace naplněno při vytvoření. `rpi_csrf`
    non-HttpOnly convenience cookie naplněno pro frontend čtení tokenu.
  - **Test:** `test_csrf_valid_header_and_origin_passes`: odpovídající
    X-CSRF-Token hlavička + platný origin vrací True.
    `test_csrf_mismatched_header_fails`: špatná hodnota hlavičky vrací
    False. `test_csrf_bad_origin_fails`: platná hlavička ale neznámý
    origin vrací False. `test_csrf_cross_site_rejected`:
    `Sec-Fetch-Site: cross-site` s platnou hlavičkou vrací False.
    `test_csrf_cross_origin_detected_via_origin`: platná hlavička ale
    křížový původ `Origin` host vrací False.
    `test_csrf_same_origin_accepted`: žádný Origin/Referer,
    `Sec-Fetch-Site: same-origin`, ne-loopback vrací True.
    `test_csrf_same_site_accepted`: žádný Origin/Referer,
    `Sec-Fetch-Site: same-site`, ne-loopback vrací True.
    `test_csrf_missing_provenance_non_loopback_rejected`: žádný Origin,
    žádný Referer, žádný Sec-Fetch-Site, ne-loopback IP vrací False.
    `test_csrf_missing_provenance_loopback_accepted`: stejné hlavičky,
    loopback IP vrací True.
    `test_csrf_header_must_match_cookie_when_present`: X-CSRF-Token
    hlavička se nerovná rpi_csrf cookie vrací False.
    `test_csrf_uses_constant_time_compare`: potvrdí použití
    hmac.compare_digest (žádný timing leak).
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal Expert/Admin CSRF helpery.

## Fáze 5b: Rate limiter přihlášení

- [x] Úkol: Implementovat třídu `LoginAttemptLimiter` s `threading.Lock`:
  - `check_and_record(ip: str) -> bool`: vrací True pokud pokus povolen
    (≤ 5 za rolling 60s), zaznamená časové razítko. Vrací False pokud
    překročeno.
  - Pod stejným Lockem odebere vypršelé buckety; před záznamem dosud neznámé IP, pokud zůstává 1024 bucketů, odstraní nejstarší a teprve potom vloží nový. Úložiště nikdy nepřekročí 1024 IP bucketů.
  - Omezený interní slovník (max 1024 IP adres); concurrent-safe.
  - **Test:** `test_login_limiter_allows_first_five`: 5 pokusů ze stejné
    IP úspěšných (vše vrací True). `test_login_limiter_blocks_sixth`:
    6. pokus do 60s vrací False. `test_login_limiter_independent_ips`:
    různé IP sledovány nezávisle. `test_login_limiter_expiry`: po 60s
    okně počet resetován. `test_login_limiter_concurrent`: 10 vláken
    volajících check_and_record paralelně pro jednu IP, přesně 5 vrací
    True a 5 vrací False. `test_login_limiter_storage_bounded`: zaznamená více než 1024 unikátních IP a ověří, že počet interních bucketů nikdy nepřekročí 1024 a nejstarší bucket je odstraněn.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal `LoginAttemptLimiter`.

## Fáze 6: Provisioning CLI

- [x] Úkol: Vytvořit `tools/auth_setup.py` s podpříkazy `expert`,
  `admin`, `api-key`. Používá `ssh-askpass` / `$SSH_ASKPASS` pokud je
  `$DISPLAY` nebo `$SSH_ASKPASS` nastaveno, s fallback na `getpass.getpass()`.
  Hesla se nikdy nepředávají jako argv.
  - `expert`: vyzve k zadání expert hesla, hashuje s benchmarkovanými
    iteracemi, zapisuje do auth.json (vytvoří zálohu pokud existuje).
  - `admin`: vyzve k zadání admin hesla, stejný postup.
  - `api-key <label> [role]`: generuje `secrets.token_urlsafe(32)`,
    vypíše raw hodnotu jednou přes stdout, ukládá SHA-256 digest
    do auth.json.
  - Všechny zápisy používají `AuthStore.save()` (atomický, mód 0600).
  - **Test:** `test_auth_setup_expert_creates_auth_json`: spustit
    s mockovaným askpass, ověřit existenci auth.json s expert hash.
    `test_auth_setup_backup_created_on_overwrite`: spustit dvakrát,
    ověřit že `.bak` soubor existuje. `test_auth_setup_api_key_prints_once`:
    zachytit stdout, ověřit že raw token se objeví přesně jednou.
    `test_auth_setup_no_plaintext_in_file`: ověřit že řetězec raw tokenu
    není v obsahu auth.json. `test_auth_setup_uses_askpass_when_display_set`:
    mockovat $DISPLAY, ověřit že ssh-askpass je zavolán.
    `test_auth_setup_fallback_to_getpass`: žádný $DISPLAY, žádný
    $SSH_ASKPASS, ověřit že getpass je zavolán.
  - **Evidence:** výstup pytest ukazuje pass. Ruční: spustit
    `python tools/auth_setup.py expert` a ověřit askpass/getpass výzvu.
  - **Rollback:** revertovat commit který přidal `tools/auth_setup.py`; testovací auth.json žije v tmp_path.

## Fáze 7: Integrace middleware

- [x] Úkol: Rozšířit `rpi_dashboard/api/middleware.py` o:
  - `extract_session_cookie(request) -> str | None`: čte cookie
    `rpi_session` z hlaviček requestu.
  - `extract_bearer_role(request, auth_store) -> Role | None`: čte
    hlavičku `Authorization: Bearer`, ověřuje přes `auth_store`.
  - `set_session_cookie(handler, token_hex, max_age, is_tls: bool)`:
    nastaví `Set-Cookie` s HttpOnly, SameSite=Lax, Path=/. atribut
    `Secure` nastaven iff `is_tls`.
  - `set_csrf_cookie(handler, csrf_hex, is_tls: bool)`: nastaví
    non-HttpOnly cookie `rpi_csrf` s `Path=/`, `SameSite=Strict`,
    `Secure` iff `is_tls`.
  - `credential_transport_allowed(is_tls: bool, is_loopback: bool) -> bool`:
    vrací True pokud je endpoint povolen (loopback HTTP povolen,
    externí vyžaduje TLS).
  - `is_https(handler) -> bool`: vrací True pokud připojení používá TLS
    (kontroluje socket nebo server state, nikoliv IP nebo headers).
  - **Test:** `test_extract_session_cookie_parses_header`: mock requestu
    s cookie hlavičkou, ověřit extrakci. `test_extract_bearer_valid`:
    mock requestu s platným Bearer, ověřit vrácenou roli.
    `test_set_session_cookie_secure_for_loopback_tls`: ověřit přítomnost
    Secure flagu při loopback TLS. `test_set_session_cookie_no_secure_for_loopback_http`:
    ověřit absenci Secure flagu pro loopback HTTP.
    `test_set_csrf_cookie_secure_for_loopback_tls`: ověřit přítomnost
    Secure flagu při loopback TLS. `test_set_csrf_cookie_no_secure_for_loopback_http`:
    ověřit absenci Secure flagu pro loopback HTTP.
    `test_is_https_external_tls`: externí TLS připojení vrací True.
    `test_is_https_external_http`: externí HTTP vrací False.
    `test_is_https_loopback_http`: loopback HTTP vrací False (detekce
    TLS reportuje pouze transport).
    `test_credential_transport_allowed_loopback_http`: loopback HTTP
    přijato politikou credential transportu.
    `test_credential_transport_rejects_external_http`: externí HTTP
    odmítnuto.
    `test_is_https_rejects_x_forwarded_proto`: externí HTTP s `X-Forwarded-Proto: https` stále vrací False.
    `test_credential_transport_allowed_external_tls`: externí TLS přijato.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal middleware auth helpery.

## Fáze 8: Webserver auth endpointy a brány

- [x] Úkol: Přidat auth endpointy do `webserver.py`:
  - `POST /auth/login`: přijímá `{"password": "...", "role": "expert|admin"}`,
    ověřuje vůči hashu pro požadovanou roli (nikdy tiše nepreferuje
    druhou), vytváří session, nastavuje cookies, vrací `{ok, role}`.
    Vyžaduje HTTPS (loopback vyňat). Aplikuje Origin / Fetch Metadata
    kontroly. Rate limit: 5/min/IP.
  - `POST /auth/logout`: ničí session, maže cookies. Vyžaduje CSRF
    (X-CSRF-Token hlavička).
  - `GET /auth/whoami`: vrací `{authenticated, role, setup_required}`.
  - `POST /auth/step-up`: přijímá `{"password": "..."}`, ověřuje admin
    hash, povýší Expert session na 5 minut. Vyžaduje HTTPS a CSRF
    (X-CSRF-Token hlavička).
  - **Test:** `test_auth_login_success`: POST s správným expert heslem
    a `role=expert` vrací 200 + session cookie. `test_auth_login_wrong_password`:
    vrací 401. `test_auth_login_wrong_role`: expert heslo s `role=admin`
    vrací 401 (není tiše přijato). `test_auth_login_unprovisioned`:
    vrací 503. `test_auth_login_accepts_external_tls`: login přes externí TLS vrací 200.
    `test_auth_login_rejects_external_http`: plain HTTP z non-loopback
    vrací 403. `test_auth_login_allows_loopback_http`: loopback HTTP
    přijato. `test_auth_login_rejects_spoofed_x_forwarded_proto`: externí HTTP s `X-Forwarded-Proto: https` vrací 403. `test_auth_logout_clears_session`: login poté logout,
    následující Expert request vrací 401. `test_auth_whoami_basic_when_unprovisioned`:
    vrací `{authenticated: false, role: "basic"}`.
    `test_auth_step_up`: Expert session + admin heslo vrací Admin roli
    na 5 minut. `test_auth_step_up_accepts_external_tls`: step-up přes externí TLS vrací 200. `test_auth_step_up_rejects_external_http`: plain HTTP
    step-up z non-loopback vrací 403. `test_auth_step_up_allows_loopback_http`: loopback HTTP step-up vrací 200. `test_auth_step_up_rejects_spoofed_x_forwarded_proto`: externí HTTP step-up s `X-Forwarded-Proto: https` vrací 403.
    `test_auth_logout_requires_csrf`: logout
    bez X-CSRF-Token hlavičky vrací 403. `test_auth_step_up_requires_csrf`:
    step-up bez X-CSRF-Token hlavičky vrací 403.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal auth endpointy.

- [x] Úkol: Přidat auth bránu v `do_GET` a `do_POST` po IP allowlist.
  Logika brány na request:
  1. Extrakce session cookie nebo Bearer token.
  2. Pokud je některý credential přítomen a `credential_transport_allowed()` vrací false, vrátit 403 před validací credentialu; externí HTTP nikdy nesmí nést Cookie ani Bearer credential, loopback HTTP zůstává povoleno.
  3. Zavolat `classify_request()`.
  4. Vrátit 401/403/503 podle potřeby.
  5. Pro Basic routy (None required_role): aplikovat `validate_basic_csrf`, když `RoutePolicy.mutating=True`, bez ohledu na HTTP metodu, poté propustit.
  6. Pro Expert/Admin routy s platnou session: ověřit CSRF (X-CSRF-Token hlavička + Origin/Referer + Sec-Fetch-Site) u requestů, jejichž `RoutePolicy.mutating=True`, bez ohledu na HTTP metodu.
  7. Bearer requesty přeskakují CSRF pouze po úspěšné transportní kontrole.
  - **Test:** `test_all_routes_classified`: každá cesta z `api/routes.py` a legacy dispatch je v `ENDPOINT_ROLES` nebo exempt; explicitně ověří `/audio/route/dlna-input/status` (Basic), `/bt/discovery` (Expert), `/modes` (Basic), `/return` POST (Basic) a `/system/reboot` (Admin).
    `test_gate_allows_basic_without_session`: `/mpv/status` GET
    vrací 200 bez cookie. `test_gate_blocks_expert_without_session`:
    `/audio/default-sink` GET vrací 401 bez cookie. `test_gate_allows_expert_with_session`:
    login poté Expert route vrací 200. `test_gate_blocks_admin_with_expert_session`:
    Expert session + Admin route vrací 403. `test_gate_csrf_rejects_missing_header`:
    Expert session + GET bez X-CSRF-Token hlavičky vrací 403.
    `test_gate_csrf_rejects_cross_site`: Expert session + GET s
    X-CSRF-Token ale `Sec-Fetch-Site: cross-site` vrací 403.
    `test_gate_bearer_skips_csrf`: Bearer token přes externí TLS + GET bez X-CSRF-Token vrací 200. `test_gate_rejects_bearer_on_external_http`: externí HTTP s Bearer vrací 403 před validací tokenu. `test_gate_accepts_bearer_on_loopback_http`: loopback HTTP s platným Bearer uspěje. `test_gate_rejects_session_cookie_on_external_http`: externí HTTP se session cookie vrací 403 před validací session. `test_gate_basic_mutating_rejects_cross_site_fetch`:
    `/mpv/play` GET s `Sec-Fetch-Site: cross-site` vrací 403.
    `test_gate_basic_mutating_accepts_no_fetch_header`: `/mpv/play` GET
    z loopbacku bez Sec-Fetch-Site, Origin ani Referer vrací 200. `test_gate_method_not_allowed`:
    `/mpv/status` POST vrací 405. `test_gate_admin_route_requires_admin_role`:
    Expert session + Admin route vrací 403. `test_gate_deprecated_returns_410`:
    `/play` GET vrací 410.
  - **Evidence:** výstup pytest ukazuje pass.
  - **Rollback:** revertovat commit který přidal auth brány.

## Fáze 9: Regrese route inventáře

- [x] Úkol: Napsat regresní test který čte všechny registrované routy
  z `rpi_dashboard/api/routes.py` a legacy dispatch tabulky
  `webserver.py` a ověřuje že každá route je přítomna v
  `ENDPOINT_ROLES` nebo je explicitně vyňata (statické assety,
  deprecated). Zabraňuje driftu nových rout bez klasifikace.
  - **Test:** `test_all_registered_routes_have_role_classification`:
    importovat route registry a legacy dispatch, sesbírat všechny cesty,
    ověřit že každá je přítomna v ENDPOINT_ROLES nebo v dokumentovaném
    exempt listu. Explicitně ověřit `/modes` (GET Basic), `/return`
    (POST Basic), `/system/reboot` (GET Admin),
    `/audio/route/dlna-input/status` (GET Basic), `/bt/discovery`
    (GET Expert) jsou klasifikovány. Selhat s jasnou zprávou
    obsahující nesklasifikované cesty.
  - **Evidence:** výstup pytest ukazuje pass; jakákoliv nová
    nesklasifikovaná route test shodí.
  - **Rollback:** revertovat commit který přidal regresní test route inventáře.

## Fáze 10: Integrační ověření

- [x] Úkol: Spustit kompletní testovací sadu, ověřit:
  - Všechny existující testy procházejí s kompatibilními testy
    aktualizovanými podle potřeby (Basic routy beze změny).
  - Nové auth testy procházejí.
  - `uv run ruff check .` čistý.
  - `uv run mypy .` čistý (pokud použito).
  - Ruční: spustit server bez auth.json, ověřit že Basic přehrávání
    funguje, Expert/Admin vrací 503.
  - Ruční: spustit `python tools/auth_setup.py expert` a
    `python tools/auth_setup.py admin`, ověřit askpass/getpass výzvu,
    přihlášení, step-up, vypršení session.
  - Ruční: spustit `python tools/auth_setup.py api-key test-label` a
    ověřit že raw token je vypsán jednou, poté použít jako Bearer.
  - **Test:** `uv run python -m pytest -q` — vše prochází.
  - **Evidence:** kompletní výstup pytest, ruff, poznámky z ručního
    ověření.
  - **Rollback:** vrátit implementační commity fází 2–9 v opačném
    pořadí podle globálního pravidla pro rollback (zachovat runtime/user
    auth.json).

## Dokončení

- [x] Úkol: Aktualizovat `metadata.json` status na `"complete"`,
  přidat `completed_at` časové razítko a `implementation_notes`
  sumarizující co bylo dodáno.
- [x] Úkol: Spustit `tools/verify-done.sh` a potvrdit exit code 0
  s platným receipt.
- [x] Úkol: Aktualizovat `conductor/tracks.md` na `[x]`.
