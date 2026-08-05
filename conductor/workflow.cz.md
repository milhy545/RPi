# Workflow: RPi Dumb TV Dashboard

## 0. Směrování repozitáře a role hostů

- Veškerá práce na RPi Dashboard používá kořenový adresář tohoto Git repozitáře.
- `<repository>/conductor` je jediný kanonický stav Conductoru.
- **Milhy-PC**: Vývojová stanice, jediná gateway pro `git push` a merge na GitHub, spouštěč plného pytestu, bezpečnostního auditu a Playwright E2E.
- **RPi**: Cílový hardwarový host (RPi 3B, 731 MB RAM). Spouští lehký profil `rpi-focused`, HW smoke testy kandidáta a strážce přehrávání. RPi NIKDY neprovádí `git push`.
- **Jules / Cloud**: Prostředí cloudového agenta. Kód kandidáta je revidován na Milhy-PC před HW validací. VM testy nikdy neslouží jako hardwarový důkaz.

## 1. Bezpečná vícehostitelská validační pipeline

### 1.1 Průběh pipeline dle původu
- **RPi-Origin**: Cílený debug + `rpi-focused` HW kontroly na RPi → handoff synchronizace na Milhy-PC → Milhy-PC `milhy-full` pytest, Ruff, mypy, bezpečnost a vzdálené E2E → opakovaná RPi validace při změně kódu → Milhy-PC merge.
- **Milhy-PC-Origin**: Izolovaný worktree → `milhy-full` kontroly → příprava kandidáta mimo živý RPi checkout → vzdálené Playwright E2E proti kandidátovi → automatický bezpečný RPi `rpi-candidate` HW smoke → Milhy-PC merge.
- **Jules/Cloud-Origin**: Branch/PR → izolovaná Milhy-PC revize & plné kontroly → nasazení kandidáta na RPi → E2E + safe HW validace → Milhy-PC merge.

### 1.2 Profilování příkazů
- `rpi-focused`: Rychlé unit & syntax kontroly pro RPi (bez těžkého pytestu a prohlížečů).
- `milhy-full`: Plný pytest, Ruff, mypy, bezpečnostní sken (ShellCheck, Gitleaks, Bandit, pip-audit), vzdálené Playwright E2E.
- `rpi-candidate`: Bezpečný HW smoke na izolovaném kandidátním worktree na RPi.
- `github-safe`: Finální CI gateway validace na Milhy-PC před push na GitHub.

### 1.3 Automatizovaný RPi strážce (Hardware Guard)
- **Přesné párování procesů**: Kontroluje spuštěné binárky (`mpv`, `steamlink`, `moonlight`, TUI režimy). Vylučuje pomocné skripty jako `keys2mpv.py`.
- **Atribuce zdrojů a fronta**: Uživatelské CPU >20%, nízká volná RAM (<50 MB) nebo teplota (>75°C) zařadí úkol do fronty. Vlastní CPU z CI runneru se odečítá, aby nedošlo k self-deadlocku.
- **Ochrana přehrávání**: Kontroly kandidáta na RPi NIKDY nesmí rušit aktivní přehrávání, hraní, TUI režimy, audio, Bluetooth, CEC ani služby. Pokud během běhu začne přehrávání, proces kandidáta se okamžitě ukončí a zařadí zpět.
- **Limity RPi**: RPi běží sériově s `flock`. Prohlížeče (Playwright/Chrome/Firefox) jsou na RPi přísně zakázány.

## 2. Správa větví a commitů

- **Větve**: `main` (stabilní/produkční), `feat/*` nebo `fix/*` vývojové větve.
- **Formát commitů**: Conventional Commits (`type(scope): message`).
- **Bezpečnostní brány**: `tools/finish-track.sh` vytvoří zálohu `pre-finish-track-{timestamp}`, spustí CI, commitne, synchronizuje zrcadlo a vygeneruje receipt. `tools/verify-done.sh` ověří receipt a přesnou SHA vazbu před tvrzením o dokončení.
