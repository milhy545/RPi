# Product Guidelines: RPi Dumb TV Dashboard

## 1. Design Philosophy

### 1.1 Goat Principle First
Funkčnost má absolutní přednost před estetikou. Každý UI element musí mít jasný účel. Žádné dekorativní prvky, které konzumují RAM nebo CPU cykly.

### 1.2 Terminal-Native Aesthetic
- **Vizuální styl:** Hacker/Matrix estetika — tmavé pozadí, zelený a cyan text, minimální barevná paleta.
- **Fonty:** Výhradně monospace fonty dostupné v terminálu (systémový výchozí).
- **Animace:** Žádné animace. Statické rendery s reaktivní aktualizací dat.
- **Hustota informací:** Maximalizovat informace na obrazovku. Žádné zbytečné mezery nebo padding navíc.

## 2. UX Principles

### 2.1 Zero-Latency Interaction
- Přepnutí módu (Dashboard → SteamLink/MPV/Spotify) musí proběhnout pod 500ms.
- Dashboard se musí plně renderovat do 1 sekundy po spuštění.
- Žádné loading spinnery — buď je akce okamžitá, nebo se zobrazí textový log.

### 2.2 Fail-Safe by Default
- Každý mód musí mít jasný "kill switch" pro návrat do IDLE.
- Pokud externí proces (steamlink, mpv, wpe) crashne, dashboard se automaticky obnoví.
- Žádná akce nesmí vyžadovat SSH přístup pro recovery.

### 2.3 TV-Optimized Layout
- **Minimální čitelná velikost textu:** Optimalizováno pro vzdálenost 2-3 metry od obrazovky.
- **Ovládání:** Primárně klávesnice/gamepad. Myš jako sekundární input.
- **Kontrast:** Vysoký kontrast (WCAG AAA pro text na tmavém pozadí).

### 2.4 Household-Friendly
- Kritické akce (SteamLink, MPV, Spotify) musí být přístupné na max 2 stisky kláves.
- Názvy módů a tlačítek v češtině (primární jazyk UI).
- Network listener na portu 8099 umožní ovládání z mobilu bez interakce s TUI.

## 3. Technical Constraints as Guidelines

### 3.1 Memory Budget
| Komponenta | Max RAM |
|---|---|
| TUI Dashboard (core) | ≤ 20 MB |
| System telemetry polling | ≤ 2 MB |
| Network listener | ≤ 5 MB |
| **Celkový overhead** | **≤ 27 MB** |

### 3.2 Dependency Rules
- **Povoleno:** `textual`, `psutil` (telemetrie), `aiohttp`/`uvicorn` (network listener).
- **Zakázáno:** X11, Wayland compositor (kromě WPE), Electron, web frameworky s heavy runtime.
- **Správa balíčků:** Výhradně `uv`. Žádný pip/pipx.

### 3.3 Process Isolation
- Každý mód běží jako samostatný proces, ne jako součást TUI.
- Dashboard se suspend/resume — nikdy neběží paralelně s aktivním módem.
- Sdílený PID file pro koordinaci mezi dashboardem a módy.

## 4. Branding & Voice

### 4.1 Naming
- **Produkt:** RPi Dumb TV Dashboard (interně "DumbTV")
- **Integrace:** Součást J.A.R.V.I.S. ekosystému

### 4.2 Tone of Voice (Log Messages)
- Stručné, technické, informativní.
- Formát: `[TIMESTAMP] [SUBSYSTEM] Message`
- Bez emoji v produkčních logech (emoji pouze v UI widgetech pro rychlé vizuální rozlišení).

### 4.3 Error Messages
- Vždy uvést: co selhalo, proč, a co dělat dál.
- Příklad: `[ERROR] MPV: Nelze přehrát stream. Důvod: yt-dlp timeout. Akce: Zkontroluj síťové připojení.`
