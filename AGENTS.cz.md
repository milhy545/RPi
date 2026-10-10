# Pravidla repozitáře

## Provozní kontext

Tento repozitář obsahuje RPi-TV Dashboard. Produkční checkout je `/home/milhy777/rpi-dashboard` na hostu `RPi`; vývojové zrcadlo a GitHub gateway jsou v `/home/milhy777/Develop/RPi` na `Milhy-PC`. Před změnou runtime ověř Git root i host. Zachovej uživatelská data, preferuj vratné změny a chování ověř na dotčeném hostu.

## Struktura projektu

- `webserver.py` je kompatibilní vstupní bod WebUI/API; HTTP routing je v `rpi_dashboard/api/`.
- `rpi_dashboard/services/` obsahuje audio, Bluetooth, player, devices, CEC, terminal, smart-home a systémovou logiku.
- `rpi_dashboard/static/` obsahuje HTML, CSS, JavaScript, manifest a service worker WebUI.
- `tui.py` je produkční Textual dashboard. `rpi_dashboard/tui/modern.py` zůstává neprodukční prototyp.
- `tests/` obsahuje pytest testy; `tests/e2e/` obsahuje Playwright hardware smoke flow.
- `provisioning/` a `systemd/` obsahují deployment soubory. `conductor/` je zamýšlený záznam produktu a tracků; dokončení ověř proti plánu, CI a receiptu.

Neupravuj cache, reporty, receipts, logy ani runtime soubory, pokud na ně úkol výslovně necílí.

## Vývojové a testovací příkazy

- `uv sync --extra dev` nainstaluje runtime i vývojové Python závislosti.
- `uv run python tui.py` spustí TUI; `uv run python webserver.py` spustí WebUI/API.
- `uv run python -m pytest -q` spustí Python testy.
- `uv run ruff check .` a `uv run mypy .` spustí lint a typovou kontrolu.
- `cd tests/e2e && npm install` nainstaluje Playwright. Hardware E2E spouštěj z Milhy-PC pomocí `TARGET_URL=http://192.168.0.205:8080 npm test`.
- `tools/run-ci.sh` spustí repozitářové CI kontroly. `tools/verify-done.sh` je povinný před tvrzením o dokončení.

## Styl kódu a testování

Používej Python 3.12, čtyřmezerové odsazení, type hints na veřejných API, `snake_case` pro Python a `kebab-case` pro shell skripty. Service logiku nedávej do HTTP handlerů. Kód a primární dokumentaci piš v UK English a udržuj odpovídající dokumentaci `*.cz.md`.

Přidávej zaměřené `test_<behaviour>.py` testy poblíž měněného chování. Hardwarové příkazy jako `pactl`, `bluetoothctl`, `nmcli`, `cec-client` a `mpv` mockuj, pokud výslovně neprovádíš live validaci na RPi. Změny WebUI vyžadují Playwright nebo ekvivalentní browser důkaz; změny služeb vyžadují ověření logů, procesů, portů a API/UI.

## Commity, pull requesty a bezpečnost agentů

Používej krátké rozkazovací Conventional Commit subjecty, například `fix(webui): remove duplicate status bar`. Pull request musí popsat záměr, dotčené moduly, verifikaci, související track nebo issue, screenshoty UI změn a dopad na hardware.

Před úpravami spusť `git status --short` a zachovej nesouvisející změny. Dodržuj `conductor/ci/SAFETY-RULES.md`: pro commity používej `tools/finish-track.sh`, nikdy nepushuj přímo z RPi a při selhání `tools/verify-done.sh` uveď přesný blokátor.

## Bezpečná validační pipeline a směrování hostů

- **Jediná gateway pro push**: Milhy-PC je jediná gateway pro `git push` a merge na GitHub. RPi host NIKDY nesmí provádět `git push`.
- **Explicitness profilů**:
  - `rpi-focused`: Rychlé unit a syntax kontroly pro RPi (bez těžkého pytestu a prohlížečů).
  - `milhy-full`: Plný pytest, Ruff, mypy, bezpečnostní sken a vzdálený Playwright E2E.
  - `rpi-candidate`: Bezpečný HW smoke na izolovaném kandidátním worktree na RPi.
  - `github-safe`: Finální CI gateway validace na Milhy-PC před push na GitHub.
- **Ochrana přehrávání a uživatele**: Kontroly na RPi NIKDY nesmí přerušit aktivní přehrávání (`mpv`), hraní (`steamlink`/`moonlight`), TUI režimy, audio, Bluetooth, CEC ani služby. Pokud během validace kandidáta začne přehrávání, procesy kandidáta se ihned ukončí a úkol se zařadí zpět do fronty.
- **Izolace kandidáta**: Kód kandidáta se sestavuje v izolovaných adresářích (`/home/milhy777/rpi-dashboard-candidate-<sha>`). Nikdy nepřeplánovávat ani neprovádět `rsync --delete` přes špinavý živý checkout.
- **Vazba na přesný receipt**: Agent NESMÍ tvrdit dokončení bez atomického receiptu (`conductor/ci/receipts/{sha}-{timestamp}.json`) vázaného na přesný commit SHA nebo tree hash.
