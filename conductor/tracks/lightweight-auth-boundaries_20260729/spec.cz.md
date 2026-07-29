# Specifikace: Lightweight Auth Boundaries

## Přehled

Zavést řízení přístupu na základě rolí se třemi úrovněmi — Basic, Expert
a Admin — pro RPi-TV Dashboard. Basic zachovává současný zážitek bez
přihlašování pro běžné přehrávání v domácnosti. Expert a Admin přidávají
přihlášení pro správu konfigurace, zařízení a systémových operací.
Veškeré vynucování probíhá na straně serveru; skrytí prvků v UI nikdy
není bezpečnostní hranicí.

## Motivace

Dashboard se v současnosti spoléhá pouze na IP subnet allowlist. Jakékoliv
zařízení v LAN nebo Tailscale rozsahu má plný přístup ke všem endpointům,
včetně destruktivních operací jako restart, odebrání BT zařízení a
přístup k terminálu/PTY. Track unified-ui-ux-refactor vyžaduje konkrétní
implementaci auth předtím, než bude možné zapnout UI gating pro
Basic/Expert/Admin. Existující dashboard-security-cleanup dokončil
tokenovou autentizaci terminálového WebSocket a zpracování přihlašovacích
údajů Wi-Fi, ale nezavedl správu relací ani řízení přístupu podle rolí.

## Funkční požadavky

### Role

| Role | Přihlášení | Přístup |
|------|-----------|---------|
| Basic | Žádné | Čtení stavů; běžné MPV play/pause/stop/seek/volume, mute, domácí návrat, objevování/stav módů |
| Expert | Cookie relace | Směrování, konfigurace, správa zařízení/sítě/audio/CEC |
| Admin | Povýšená cookie relace nebo step-up z Expert | Terminál/PTY, WS credential, systémové logy, restart/reboot systému, budoucí update |

- Admin dědí všechna oprávnění Expert.
- Expert může provést krátkodobý step-up na Admin (5minutové okno).
- Basic routy musí fungovat bez `auth.json` provisioningu.
- Expert/Admin routy vracejí `503 setup_required` pokud není
  nakonfigurováno.

### Route Policy (method/path aware, fail-closed)

**Basic (bez přihlášení):**

- `/mpv/play`, `/mpv/stop`, `/mpv/toggle`, `/mpv/seek`, `/mpv/seekabs`,
  `/mpv/vol`, `/mpv/volume` — běžné ovládání přehrávání.
- `/mpv/status`, `/mpv/memory` — čtení stavu a pozice obnovení.
- `/modes` (GET) — čtení dostupných režimů zobrazení.
- `/audio/state`, `/audio/matrix`, `/audio/mute-state`,
  `/audio/bluetooth-profiles`, `/audio/mute` — čtení stavu a běžný mute.
- `/devices/state`, `/devices`, `/bt/state`, `/bt/scan`, `/bt/controller`,
  `/bt/transfers`, `/bt/files`, `/bt/diagnostics`, `/bt/media`,
  `/bt/pairing`, `/bt/capabilities`, `/bt/phone-role` — čtení stavu
  zařízení.
- `/wifi/status`, `/cec/scan`, `/cec/br/st` — čtení stavu sítě/CEC.
- `/system/stats`, `/system/hw-stats`, `/system/status`,
  `/system/https-info` — čtení stavu systému.
- `/network/info`, `/network/tailscale` — čtení síťových informací.
- `/youtube/cookies/status`, `/media/preview` — čtení diagnostiky.
- `/dlna/scan`, `/dlna/renderer/status` — čtení stavu DLNA.
- `/audio/route/dlna-input/status` — čtení stavu DLNA input route.
- `/return/last`, `/return/config` — čtení stavu návratu.
- `/return` (POST) — spuštění domácího návratu na dashboard.
- `/cache/stats`, `/pool/stats` — čtení statistik cache/poolu.
- `/report` (POST) — odeslání zpětné vazby od kohokoliv v domácnosti.
- Všechny statické assety, WebUI shell, manifest, favicon.

**Expert (přihlášení):**

- Správa obnovení MPV (GET): `/mpv/memory-save`, `/mpv/memory/clear`.
- Audio směrování (dnes GET): `/audio/default-sink`, `/audio/volume`,
  `/audio/volume/global`, `/audio/bt`, `/audio/hdmi`, `/audio/dlna`,
  `/audio/latency`, `/audio/multi-output`, `/audio/matrix/link`,
  `/audio/test`, `/keepalive`.
- Správa audio směrování (dnes GET): `/audio/route/alexa-bt`,
  `/audio/route/alexa-retarget`, `/audio/route/dlna-input/start`,
  `/audio/route/dlna-input/stop`, `/audio/route/dlna-input/mode`,
  `/audio/route/dlna-input/target`.
- Ovládání DLNA rendereru (dnes GET): `/dlna/select`, `/dlna/connect`,
  `/dlna/disconnect`, `/dlna/renderer/start`, `/dlna/renderer/stop`.
- Správa BT (dnes GET): `/bt/pair`, `/bt/trust`, `/bt/connect`,
  `/bt/disconnect`, `/bt/device-action`, `/bt/device-profile`,
  `/bt/device-autoconnect`, `/bt/device-hid`, `/bt/settings`,
  `/bt/adapter-power`, `/bt/discoverable`, `/bt/discovery`,
  `/bt/operation`, `/devices/bt/scan`.
- Správa Wi-Fi: `/wifi/connect` (GET+POST), `/wifi/scan` (GET).
- Ovládání CEC: `/cec/send`, `/cec/key`, `/cec/in`, `/cec/power`,
  `/cec/nav`, `/cec/vol`, `/cec/input`, `/cec/br/start`, `/cec/br/stop`.
- Konfigurace návratu: `/return/config/set`.
- YouTube age check: `/youtube/age-check`.
- Správa cache/poolu: `/cache/clear`, `/pool/clear`.
- Konfigurace integrace: `/ha/config` — minimálně Expert, protože
  budoucí integrační konfigurace může obsahovat auth údaje.

**Admin (povýšené přihlášení):**

- Terminál: `/terminal/connect`, `/terminal/disconnect`.
- WS credential: `/ws/token`.
- Systémové logy: `/system/logs`.
- Restart/reboot systému (dnes GET): `/system/restart-mpv`,
  `/system/restart-dashboard`, `/system/restart-rpi`, `/system/reboot`,
  `/restart/mpv`, `/restart/dashboard`, `/restart/rpi`.
- Destruktivní BT: `/bt/remove`, `/bt/reset`, `/bt/file-send`,
  `/bt/file-cancel`.
- Self-test: `/selftest/testaudio`.

**Výchozí stav fail-closed:** jakákoliv route v chráněném namespace
(`/audio/*`, `/bt/*`, `/wifi/*`, `/cec/*`, `/system/*`, `/terminal/*`,
`/dlna/*`, `/return/*`, `/mpv/*`, `/devices/*`, `/network/*`,
`/restart/*`, `/youtube/*`, `/media/*`, `/cache/*`, `/pool/*`,
`/ha/*`, `/selftest/*`, `/ws/*`, `/keepalive`) která není explicitně
klasifikována, se výchozí nastaví na Admin. Opravdu neregistrované
cesty (např. `/foo/bar`) vracejí 404 — nikdy nedosáhnou auth brány.

**Zastaralé (bez auth, vrací 410):** `/play`, `/kodi/st`, `/kodi/status`.

Každý záznam `ENDPOINT_ROLES` je klíčovaný přesnou dvojicí `(path, method)` a ukládá `RoutePolicy(required_role, mutating: bool)`. Reprezentativní flagy: `/mpv/play` GET Basic/true, `/mpv/status` GET Basic/false, `/return` POST Basic/true, `/report` POST Basic/true, `/system/logs` GET Admin/false a `/system/reboot` GET Admin/true.

### Autentizace

#### Hashování hesel

- Algoritmus: PBKDF2-SHA256 přes `hashlib.pbkdf2_hmac` (stdlib, žádná
  nová závislost).
- Počet iterací: určen benchmarkem hardwaru v době provisioningu.
  Kalibrační funkce spustí více vzorků pro každého kandidáta, vypočítá
  medián doby přihlášení a odhadne optimální počet jehož medián leží
  v 150–300 ms. Poté omezi na bezpečné hranice (100_000–1_000_000),
  ověří že finální multi-sample medián leží v 150–300 ms a selže
  provisioning s akční chybou pokud žádný kandidát nesplňuje cíl.
  Unit testy mockují časy; live RPi evidence zaznamenává medián/p95.
- Salt: 16 bajtů, generován pro každý ukládaný credential.
- Uloženo v `auth.json` jako base64 spolu s počtem iterací.

#### Správa relací

- Token: `secrets.token_bytes(32)` — neprůhledný, náhodný, 32 bajtů.
- Hodnota cookie: hex-encodovaný token (64 znaků), `HttpOnly`,
  `SameSite=Lax`, `Path=/`.
- Atribut `Secure` se nastaví, když je skutečné připojení TLS, včetně loopback TLS, a vynechá se pouze pro povolené loopback HTTP.
- Server-side úložiště: in-memory `dict[sha256(token) → Session]`
  chráněný `threading.Lock`. Na serveru se ukládá pouze SHA-256 digest
  tokenu; samotný token se nikdy nepersituje. Veřejné metody získávají
  lock jednou; privátní `_unlocked` helpery běží pouze pokud volající
  již drží lock. Uložené mutovatelné Session objekty nikdy neunikají:
  token-based metody mutují pod lockem a vracejí immutable snapshoty.
- Objekt relace: `{role, created, last_seen, csrf_token, step_up_expires}`.
- TTL: Expert 8 hodin (sliding window), Admin 30 minut
  (sliding window), step-up 5 minut.
- Ověřování requestu: `bytes.fromhex(cookie)` → `sha256()` → dict
  lookup pod store lockem. Hot path provádí pouze digest výpočet a
  locked dictionary lookup; žádné hashování hesel na requestu.
- Store lock musí být držen pro všechny read a write operace na session
  dict. `AuthStore` používá stejný vzorec `Lock` s non-nested
  získáváním a privátními `_unlocked` helpery pro všechny čtení a
  zápisy konfiguračního souboru. Testy concurrency ověří bezpečné
  chování pod paralelním create/validate/destroy a současným read/write.

#### Step-up flow

1. Uživatel má Expert session cookie.
2. Frontend otevře step-up modal pro Admin akce.
3. `POST /auth/step-up` s `{"password": "<admin-password>"}`,
   existujícím session cookie a hlavičkou `X-CSRF-Token` odpovídající
   csrf_token relace. Vyžaduje HTTPS (loopback vyňat).
4. Server ověří Expert relaci, CSRF token, poté ověří admin hash hesla.
5. Při úspěchu: nastaví `step_up_expires = now + 300s` a
   `effective_role = Admin`.
6. Po 5 minutách se `effective_role` vrátí na Expert.

#### Přihlášení

- `POST /auth/login` s `{"password": "...", "role": "expert|admin"}`.
- Pole `role` je povinné a určuje který credential ověřit. Server nikdy
  tiše nepreferuje jeden hash před druhým; pokud zadané heslo odpovídá
  hashu špatné role, přihlášení selže s 401.
- Vyžaduje HTTPS (loopback vyňat).
- Navíc aplikuje Origin / Fetch Metadata kontroly: odmítá requesty
  s `Sec-Fetch-Site: cross-site` a validuje
  host `Origin` nebo `Referer` vůči `ALLOWED_SUBNETS` pokud přítomno.
- Rate limit: 5 pokusů za minutu na IP.

### Ochrana CSRF

CSRF ochrana je určena route policy, nikoliv pouhou přítomností elevated
session cookie.

**Expert/Admin cookie-authenticated mutace (např. `/bt/pair`,
`/audio/default-sink`, `/wifi/connect`):**

- Mechanismus: synchroniser token + provenience.
  - Server generuje `csrf_token = secrets.token_bytes(16)` při vytvoření
    relace.
  - Token hex je dostupný přes čitelný `rpi_csrf` convenience cookie
    (non-HttpOnly, `SameSite=Strict`, `Path=/`, `Secure` pokud je připojení TLS, vynechaný pouze pro povolené loopback HTTP).
  - Každý cookie-authenticated Expert/Admin state-changing request MUSÍ
    obsahovat hlavičku `X-CSRF-Token` jejíž hodnota odpovídá csrf_token
    relace. Server provádí constant-time srovnání přes
    `hmac.compare_digest`. Pokud je přítomen i `rpi_csrf` cookie,
    hodnota hlavičky se musí rovnat hodnotě cookie.
  - Cross-site requesty jsou odmítnuty (`Sec-Fetch-Site: cross-site`).
    Cross-origin je detekován pouze neplatným hostem `Origin` nebo
    `Referer` neodpovídajícím `ALLOWED_SUBNETS` / `localhost` / `*.local`.
  - Pokud je `Origin` nebo `Referer` přítomen, musí být platný.
  - Pokud jsou `Origin` i `Referer` oba nepřítomni: non-loopback přijímá
    pouze pokud `Sec-Fetch-Site` je `same-origin` nebo `same-site`;
    loopback přijímá chybějící provenience; jinak odmítnuto.
- Bearer-authenticated requesty CSRF přeskakují (žádný browser kontext).

**Basic mutující routy (např. `/mpv/play` GET, `/return` POST):**

- Basic mutace bez relace nemohou používat session CSRF (žádná relace
  neexistuje). Místo toho se aplikuje Fetch Metadata / Origin obrana:
  - Pokud je přítomen header `Sec-Fetch-Site` a má hodnotu `cross-site`,
    request je odmítnut s 403.
  - Pokud je přítomen header `Origin` nebo `Referer`, jeho host musí
    odpovídat `ALLOWED_SUBNETS` nebo být `localhost` / `*.local`.
  - Pokud chybí `Origin` i `Referer`: přijme loopback; non-loopback přijme pouze s `Sec-Fetch-Site: same-origin` nebo `same-site`; jinak request odmítne.
- Tato obrana není dokonalá CSRF bariéra; spoléhá na enforcement Fetch
  Metadata headerů prohlížeči. Snížuje útočný povrch bez blokování
  legitimní automatizace.

### API tokeny (Bearer)

- Uloženy v `auth.json` pod `api_keys`, klíčovány SHA-256 digestem
  raw tokenu. Každý záznam: `{role, label, created}`. Digest je
  klíč mapy; žádný prefix se neukládá.
- Raw token se vypíše přesně jednou při vytvoření (pouze lokální CLI)
  a nikdy se nepersituje.
- Ověření: `sha256(bearer_value)` → dict lookup.

### Provisioning

- Žádný web bootstrap. Žádný tisk tajemství do stderr nebo logů.
- Lokální CLI nástroj: `tools/auth_setup.py` s podpříkazy `expert`,
  `admin`, `api-key`.
- Používá `ssh-askpass` (nebo `$SSH_ASKPASS`) pokud je grafické nebo
  askpass prostředí použitelné (`$DISPLAY` nebo `$SSH_ASKPASS` nastaveno),
  s `getpass.getpass()` jako TTY fallback. Hesla se nikdy nepředávají
  jako argumenty příkazové řádky.
- Konfigurační soubor: `~/.config/rpi-dashboard/auth.json`, zapisován
  atomicky (temp soubor → fsync → rename) s módem `0600`. Adresář
  vytvořen s módem `0700` pokud chybí.
- Před přepsáním existujícího `auth.json` nástroj vytvoří zálohu
  s módem 0600 (např. `auth.json.bak`) ve stejném adresáři.
- Dva oddělené hashované přihlašovací údaje: `expert` a `admin`.
- Role-aware přístup: Expert PŘÍSTUP je považován za provisionovaný
  pokud existuje buď expert nebo admin hash; Admin PŘÍSTUP vyžaduje
  admin hash. `is_role_provisioned(role) -> bool` toto reflektuje
  (Expert true pokud je přítomen kterýkoliv hash, Admin true pouze
  pokud je přítomen admin hash). Lokální CLI nastavuje credentials
  přímo; není autorizován existujícím heslem.
- Pokud `auth.json` neexistuje: Basic routy fungují normálně;
  Expert/Admin routy vracejí `503 setup_required`.

### Požadavek HTTPS

- `POST /auth/login` a `POST /auth/step-up` odmítají non-loopback HTTP
  a přijímají non-loopback HTTPS. Loopback HTTP je povoleno.
- Detekce transportu používá skutečný TLS stav připojení (např.
  TLS-wrapped socket nebo server TLS konfigurace), nikoliv IP heuristiky
  nebo `X-Forwarded-Proto`.
- Atribut `Secure` cookie následuje TLS: nastaví se, když je připojení TLS, včetně loopback TLS, a vynechá se pouze pro povolené loopback HTTP.
- Každý request nesoucí session cookie nebo Bearer credential vyžaduje skutečné TLS, pokud klient není loopback. Externí HTTP se odmítne před validací credentialu; `X-Forwarded-Proto` toto pravidlo nemůže obejít.

### Rate limit přihlášení

- Oddělený thread-safe store, nezávislý na obecném action limiteru.
- 5 pokusů za rolling 60 sekund na client IP.
- Vrací 429 pokud překročeno.
- Každá IP je trackována odděleně; expirace okna resetuje počet.
- Concurrency-safe pod paralelními requesty.
- Úložiště má pevný limit 1024 IP bucketů: pod stejným lockem odstraní vypršelé buckety; před vložením nové IP při plné kapacitě odstraní nejstarší bucket.

### HTTP odpověďové kódy

| Kód | Význam |
|-----|--------|
| 200 | Úspěch |
| 401 | Chybějící nebo vypršelá/neplatná relace (`WWW-Authenticate: Cookie`) |
| 403 | Relace existuje ale role nestačí, nebo selhání CSRF / Fetch Metadata |
| 403 | IP není v allowlist (existující, beze změny) |
| 429 | Rate limited (existující, beze změny) |
| 503 | Expert/Admin požadavek ale `auth.json` není nakonfigurováno |

## Nefunkční požadavky

- Žádné nové pip závislosti. Čistý stdlib (`hashlib`, `hmac`, `secrets`,
  `threading`, `time`, `json`, `os`).
- Ověřování relací neprovádí PBKDF ani filesystem I/O — pouze digest
  výpočet a locked dictionary lookup na request. Na cílovém RPi musí
  1000 přímých validací reportovat medián ≤ 1 ms a p95 ≤ 5 ms.
- Hashování hesel přidává latence pouze při přihlášení; počet iterací
  je kalibrován per-device přes multi-sample benchmark jehož medián
  spadá do cílového rozsahu.
- `AuthStore` může znovu načíst config při startu a při loginu nebo
  Bearer lookup pokud se změní mtime, ale nikdy při běžných
  session-authenticated requestech. Rotace credentialů neruší
  existující in-memory sessiony; restart dashboardu je vyžadován
  pokud je zamýšlena revokace.
- Všechny existující testy procházejí s kompatibilními testy
  aktualizovanými podle potřeby (Basic routy zůstávají bez autentizace).
- Přehrávání v domácnosti nikdy není přerušeno stavem auth.
- Thread safety: `AuthStore` a `SessionStore` používají `threading.Lock`
  s non-nested získáváním a privátními unlocked helpery pro všechny
  sdílené čtení a zápisy. Testy concurrency cvičí paralelní
  create/validate/destroy a současný read/write.

## Omezení

- Existující `ALLOWED_SUBNETS` IP allowlist je zachován beze změny.
- Existující rate limiting je zachován beze změny.
- Existující CORS politika je zachována beze změny.
- Existující terminálový WebSocket token (`WS_AUTH_TOKEN`) je
  zablokován za Admin auth; token samotný není nahrazen.
- Track `dashboard-security-cleanup_20260723` je dokončen a nesmí
  být modifikován.

## Kritéria přijetí

- [ ] `auth.json` chybí: všechny Basic routy vracejí 200; Expert/Admin
  routy vracejí 503 `setup_required`.
- [ ] `auth.json` přítomen pouze s expert heslem: Expert routy vracejí
  200 po přihlášení s `role=expert`; Admin routy vracejí 503 přes
  `is_role_provisioned(ADMIN)` = False; přihlášení s `role=admin`
  vrací 401.
- [ ] `auth.json` přítomen pouze s admin heslem: obě Expert i Admin
  routy jsou přístupné (admin credential splňuje Expert přes hierarchii).
- [ ] Přihlášení s polem `role` odpovídajícím špatnému hashi vrací 401,
  nikdy tiše neudělí přístup.
- [ ] Admin step-up z Expert relace úspěšně funguje a vyprší po
  5 minutách.
- [ ] Ověřování relací: 1000 přímých validací na cílovém RPi reportuje
  medián ≤ 1 ms a p95 ≤ 5 ms; žádný PBKDF ani filesystem I/O.
- [ ] X-CSRF-Token header validace: odmítá cross-site
  Expert/Admin mutace; odmítá chybějící provenience z non-loopback;
  přijímá same-origin s platným Origin/Referer.
- [ ] Logout a step-up vyžadují CSRF (X-CSRF-Token hlavička); requesty
  bez hlavičky jsou odmítnuty.
- [ ] Basic mutující routy odmítají `Sec-Fetch-Site: cross-site`; odmítají chybějící provenienci z non-loopbacku; přijímají chybějící provenienci z loopbacku a non-loopback `same-origin`/`same-site`.
- [ ] Přihlášení a step-up odmítají non-loopback HTTP; přijímají
  non-loopback HTTPS; povolují loopback HTTP.
- [ ] Login rate limiter: 6. pokus do 60 sekund vrací 429; nezávislé
  IP trackovány odděleně; expirace okna resetuje počet; concurrency
  safe; úložiště nikdy nepřekročí 1024 IP bucketů a při plné kapacitě odstraní nejstarší bucket před vložením nové IP.
- [ ] Bearer-authenticated requesty přeskakují CSRF pouze na povoleném transportu: externí TLS a loopback HTTP jsou přijaty; externí HTTP je odmítnuto před validací tokenu.
- [ ] Vytvoření API tokenu vypíše raw hodnotu jednou (pouze lokální
  CLI); následné lookupy používají pouze SHA-256 digest; raw hodnota
  není v `auth.json`.
- [ ] `tools/auth_setup.py` čte hesla přes askpass/getpass, zapisuje
  `auth.json` s módem 0600, vytváří zálohu před přepsáním, nikdy
  nevypisuje hesla.
- [ ] Přihlášení a step-up vyžadují HTTPS; pouze loopback může
  použít HTTP.
- [ ] `AuthStore` a `SessionStore` jsou thread-safe; testy concurrency
  procházejí.
- [ ] Rollback nikdy neodstraňuje ani nepřepisuje skutečný uživatelský
  `auth.json`; testy používají temp cesty; provisioning vytváří zálohu
  před náhradou.
- [ ] Všechny pytest testy procházejí s kompatibilními testy
  aktualizovanými podle potřeby.
- [ ] Plná regrese route inventáře: `/modes` (GET), `/return` (POST),
  `/system/reboot` (GET), `/audio/route/dlna-input/status` (GET Basic),
  `/bt/discovery` (GET Expert) a každá cesta v `api/routes.py` plus
  úspěšný legacy dispatch je klasifikován v `ENDPOINT_ROLES` nebo
  explicitně vyňat. Fail-closed prefixy zahrnují `/mpv/*`, `/devices/*`,
  `/network/*`, `/restart/*`, `/youtube/*`, `/media/*`, `/cache/*`,
  `/pool/*`, `/ha/*`, `/selftest/*`, `/ws/*`, `/keepalive`.
- [ ] `uv run ruff check .` prochází.
- [ ] `git diff --check` čistý.

## Mimo rozsah

- Vystavení na veřejném internetu nebo externí identity providery.
- Per-user účty (model sdíleného hesla domácnosti).
- Frontend role-aware UI rendering (vlastnictví
  `unified-ui-ux-refactor_20260728`).
- Implementace WebSocket PTY transportu (samostatný track).
- Admin API-key creation endpoint (není v aktuálním rozsahu; pouze
  lokální CLI).
