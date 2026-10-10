# Specifikace tracku: Bezpečná validační pipeline pro RPi / Milhy-PC / Jules

## Kontext a Cíle
Tento track definuje a implementuje bezpečnou, izolovanou multi-host validační pipeline pro RPi-TV Dashboard napříč Raspberry Pi (RPi 3B), Milhy-PC (vývojová pracovní stanice a výhradní push brána na GitHub) a Jules/cloud prostředími.

## Závazné požadavky a pravidla pipeline

1. **Vazba na Bránu a SHA**:
   - Milhy-PC je jediná push a merge brána na GitHub. RPi nikdy neprovádí `git push`.
   - Přesný SHA commit a Git tree hash vážou veškerý důkazní materiál (evidence). Jakákoli následná změna kódu zneplatní předchozí validační účtenky (receipts).

2. **Workflows pipeline podle původu**:
   - **Původ na RPi**: Cílený debug a bezpečné HW kontroly na RPi → předání na Milhy-PC → plný pytest, testy stability backendu, Ruff, mypy, bezpečnostní nástroje a vzdálené browser E2E na Milhy-PC → opakovaná validace na RPi pokud se změnil kód → merge na Milhy-PC.
   - **Původ na Milhy-PC**: Izolovaný worktree → kompletní kontroly → příprava přesného candidate SHA mimo živý checkout na RPi → Playwright/E2E z Milhy-PC proti kandidátovi → automatický bezpečný RPi HW smoke test → merge na Milhy-PC.
   - **Jules/cloud**: Větve/PR → izolovaný přezkum na Milhy-PC & kompletní kontroly → přesný kandidát staged na RPi → E2E + bezpečná HW validace → merge na Milhy-PC. Testy ve VM nikdy neslouží jako hardwarový důkaz.

3. **Automatizovaný RPi Hardware Guard**:
   - **Přesná detekce procesů a režimů**: Kontroluje běžící spustitelné soubory (`mpv`, `steamlink`, `moonlight`, TUI režim). Striktně vylučuje podřetězce (např. `keys2mpv.py` nesmí být nikdy chybě identifikován jako `mpv`).
   - **Využití zdrojů & CPU atribuce**: Trvalé zatížení CPU uživatelem >20 % spouští stav `busy`. Vlastní CPU z runneru CI / PIDs testů je explicitně atribováno a vyloučeno, aby se zabránilo uvíznutí (deadlock). Diagnostic nástroje (`ps`, `top`, `pgrep`, `pi`) jsou z uživatelského zatížení vyloučeny.
   - **Brány zdrojů**: Hranice RAM (<50 MB volné), teplota CPU (>75 °C) a aktivní zámky.
   - **Frontování a Backoff**: Odložení spuštění s omezeným exponenciálním backoffem při vytížení.
   - **Ochrana bez přerušení**: Nikdy nezabíjet, nesignalizovat, nerestartovat ani nedegradovat aktivní přehrávání, hraní, TUI, audio, Bluetooth, CEC nebo služby. Pokud přehrávání začne uprostřed běhu, kandidátní/testovací procesy se ihned ukončí a zařadí zpět do fronty.
   - **Limity hostitele RPi**: Kontroly na RPi běží sériově s `flock`, s nízkou prioritou a časovým limitem. Prohlížeče na RPi nikdy neběží.

4. **Staging kandidáta & Izolace worktree**:
   - Kandidátní kód je připraven v izolovaném worktree/adresáři (`/home/milhy777/rpi-dashboard-candidate-<sha>`).
   - Odmítnout synchronizaci/staging, pokud živý checkout nebo cílový adresář obsahuje necommitted změny (`rsync --delete` zakázáno nad nečistým checkoutem).
   - Kontroly stavu a čistý rollback při selhání.

5. **Explicitní profily spuštění**:
   - `rpi-focused`: Cílený debug a bezpečné unit/smoke kontroly pro RPi (bez těžkého pytestu a testů prohlížeče).
   - `milhy-full`: Plná sada pytest, stabilita backendu, Ruff, mypy, bezpečnostní scany (ShellCheck, Gitleaks, Bandit, pip-audit), vzdálené Playwright E2E.
   - `rpi-candidate`: Bezpečný HW smoke na staged candidate worktree na RPi.
   - `github-safe`: Finální kontrola CI brány na Milhy-PC před push na GitHub.

6. **Správa RPi Core Rules v repozitáři**:
   - Šablona repozitáře `.agents/core-rules/SKILL.rpi.template.md` spravovaná v gitu.
   - Idempotentní instalátor `tools/install-rpi-core-rules.sh` s časovými zálohami, validací cíle (podporuje `.agents/skills` i `.codex/skills`) a kontrolou symlinků.
   - Zachovává pravidla nízké RAM na RPi 3B a vkládá pravidla pro směrování hostitele, ochranu přehrávání, push pouze z Milhy-PC a účtenky.

7. **Kontrakt o důkazním materiálu a účtenkách**:
   - Důkazní materiál pipeline strukturován s hostitelem, SHA/tree, profilem, časovým razítkem, zprávami, bránou RPi, E2E artefakty, URL akcí a cestou k účtence.
   - Vyžaduje souborové zamykání `flock` k zamezení souběhu.
