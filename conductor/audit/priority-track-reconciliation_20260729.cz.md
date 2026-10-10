# Rekoncilace prioritních Conductor tracků — 29. července 2026

## Rozsah

Sjednotit stav registru a metadat čtyř prioritních Conductor tracků,
které byly nesprávně označeny `[x]` (dokončeno) v `tracks.md` v commitu
`638caa493fa5f5491f0be0fd5f5c0012920fe69c`. Tento audit byl proveden
v dedikovaném git worktree na větvi
`recovery/conductor-reconciliation_20260729`.

## Infrastruktura

- **Worktree:** `/home/milhy777/Develop/RPi-recovery-conductor`
- **Větev:** `recovery/conductor-reconciliation_20260729`
- **Základní commit:** `638caa493fa5f5491f0be0fd5f5c0012920fe69c`
- **Původní checkout:** `/home/milhy777/Develop/RPi` (dirty: `AGENTS.md`,
  `AGENTS.cz.md`, `docs/audits/` — vše patří kontrolorovi a zůstalo nedotčené)
- **Autoritativní nástroje:** `conductor.py status` (exit 0),
  `conductor.py validate` (exit 1, INVALID)

## Stav receiptů

Pro HEAD `638caa4` neexistuje žádný completion receipt v žádném checkoutu.
Původní checkout obsahuje 96 receipt souborů pro jiné SHA; worktree nese
pouze `.gitkeep`, protože receipty jsou lokální runtime artefakty
ignorované Gitem. Absence receiptu pro `638caa4` potvrzuje, že CI
pipeline nikdy neprošla pro tento commit a že se jedná o neverifikovanou
částečnou práci.

## Klasifikace prioritních tracků

### 1. unified-ui-ux-refactor_20260728

| Pole | Předchozí stav | Aktuální stav |
|---|---|---|
| Registry | `[x]` done | **`[ ]` znovuotevřeno** |
| Metadata | chybějící | **`active`** (vytvořeno) |
| Spec | chybějící | **vytvořeno** (spec.md + spec.cz.md) |
| Plan | 0/24 splněno, zastaralé cesty | **přepsáno** (0 splněno, 35 položek plánu + 10 kritérií přijetí = 45 celkem) |

**Důkaz:** `theme.css` definuje tokeny; `main.css` (70 `var(--`) a
`themes.css` (78 `var(--`) je spotřebovávají. Nicméně: duplicitní
globální prvky vlastněné sekcí Bluetooth zůstávají; ID prvků stavového
panelu neodpovídají JS selektorům; `updBr()` vyhazuje null-reference
každé 3 sekundy; Terminal tab je prázdný; parity TUI nezahájena. Plan
přepsán tak, aby odpovídal skutečným cestám (`main.css`/`themes.css`/
`responsive.css`/`audio.css`, ne `style.css`), správnému endpointu
(`/system/hw-stats` nikoli `/system/stats`), čtení TUI ze sdíleného
Python modulu `rpi_dashboard.services.system`, shellu Terminalu s integrační
smlouvou (žádný WebSocket, dokud jej terminal/auth tracky nedodají), hranici
Basic/Expert/Admin vyžadující server-side auth a Playwright důkazům na 4
rozlišeních. CSS kritéria používají sémantické kontroly (kategorie
tokenů, žádné neodůvodněné duplicity, screenshot regrese), nikoli
křehké `var(--` počty.

**Počty položek plánu (po přepsání):**
- Fáze 1 (Audit CSS tokenů): 4 úkoly + 1 ověření = 5
- Fáze 2 (Odstranění BT duplicit): 3 úkoly + 1 ověření = 4
- Fáze 3 (Telemetrie stavového panelu): 3 úkoly + 1 ověření = 4
- Fáze 4 (Chyby v konzoli): 2 úkoly + 1 ověření = 3
- Fáze 5 (Shell Terminalu): 2 úkoly + 1 ověření = 3
- Fáze 6 (Responzivní ověření): 4 úkoly + 2 ověření = 6
- Fáze 7 (Parita TUI): 4 úkoly + 1 ověření = 5
- Fáze 8 (Plná branka): 4 úkoly + 1 ověření = 5
- **Mezisoučet (úkoly + ověření): 35**
- Kritéria přijetí: 10
- **Celkem nezaškrtnutých checklist položek: 45**

**Akce:** Znovuotevřeno. Soubory vytvořeny: `spec.md`, `spec.cz.md`,
`metadata.json`. `plan.md` a `plan.cz.md` přepsány. Žádné úkoly
nebyly splněny.

### 2. audio-fullstack-refactor_20260725

| Pole | Předchozí stav | Aktuální stav |
|---|---|---|
| Registry | `[x]` done | **`[ ]` znovuotevřeno** |
| Metadata | `active` | `active` (bez změny) |
| Spec | přítomný | přítomný (bez změny) |
| Plán | 0/43 splněno | **beze změny** (mimo rozsah úprav) |

**Důkaz:** `rpi_dashboard/services/audio/` existuje pouze s `__init__.py`
obsahujícím plný monolitický audio kód (~1054 řádků). Žádné pod-moduly
(`state.py`, `mixer.py`, `matrix.py`, `multi_output.py`, `keepalive.py`,
`profiles.py`, `latency.py`) neexistují. `set_global_master_volume()` a
BT AVRCP sync jsou přítomné v `__init__.py`. TUI `AudioFlowDiagram`
nenalezen. Zaškrtávací pole plánu zůstala nedotčená podle omezení rozsahu.

**Akce:** Znovuotevřeno. Metadata ponecháno jako `active`. Plan neměněn.

### 3. backend-modularization-completion_20260723

| Pole | Předchozí stav | Aktuální stav |
|---|---|---|
| Registry | `[x]` done | **`[ ]` znovuotevřeno** |
| Metadata | `active` | `active` (bez změny) |
| Spec | přítomný | přítomný (bez změny) |
| Plán | 0/33 splněno | **beze změny** (mimo rozsah úprav) |

**Důkaz:** `webserver.py` má 3088 řádků. Extrakce API do
`rpi_dashboard/api/` je reálná (routes.py, handlers.py existují).
E2E testová infrastruktura přítomná (`tests/e2e/` se 4 Playwright
testovými soubory + package.json). Fáze 4 vizuální redesign, fáze 5
odebrání legacy a fáze 6 runtime ověření vykazují nulové splnění plánu.
Zaškrtávací pole plánu zůstala nedotčená podle omezení rozsahu.

**Akce:** Znovuotevřeno. Metadata ponecháno jako `active`. Plan neměněn.

### 4. verification-coverage-hardening_20260723

| Pole | Předchozí stav | Aktuální stav |
|---|---|---|
| Registry | `[x]` done | **`[ ]` znovuotevřeno** |
| Metadata | `planned` | `planned` (bez změny) |
| Spec | přítomný | přítomný (bez změny) |
| Plán | 0/32 splněno | **beze změny** (mimo rozsah úprav) |

**Důkaz:** Zachycena základní data (`baseline_20260727_133715/`).
`baseline_reconciliation.md` a `log-audit.md` existují.
`tests/test_transport_disconnect.py` a `tests/test_shutdown_behavior.py`
neexistují. Fáze 2–5 jsou pouze pro hardware. Zaškrtávací pole plánu zůstala
nedotčené podle omezení rozsahu.

**Akce:** Znovuotevřeno. Metadata ponecháno jako `planned`. Plan neměněn.

## Odložené historické nesrovnalosti

Následující tracky mají registry/metadata nesrovnalosti, ale jsou mimo
rozsah tohoto sjednocení. Vyžadují samostatnou historickou revizi
k určení následnictví, absorpce nebo nezávislého stavu:

- `alexa-dlna-audio-routing_20260613` (done/planned)
- `devices-tab-hardening_20260613` (done/planned)
- `dlna-rendering_20260611` (done/planned)
- `playback-resume-memory_20260613` (done/planned)
- `terminal-hw-stats_20260613` (done/planned)
- `webui-report-conductor-intake_20260613` (done/planned)
- `android-share-app_20260613` (done/planned) — výstup specifikace
- `milhy-pc-firewall_20260611` (done/implementation)
- `smart-home-integrations_20260613` (done/planned)
- `mpv-eof-runtime-return_20260723` (done/done) — silné implementační
  důkazy, ověření a evidence jsou neúplné
- `mpv-optimization_20260627` (done/done) — čeká na revizi
- `modular_test_ci_config_audio_fix_20260626` (unregistered/pending)
- 6× track `report_*` (done/chybějící metadata)
- `audio-multimixer-webui_20260725` (absorbováno do audio-fullstack)

## Změněné soubory

| Soubor | Akce |
|---|---|
| `conductor/tracks.md` | 4 položky změněny z `[x]` na `[ ]` |
| `conductor/tracks/unified-ui-ux-refactor_20260728/spec.md` | Vytvořeno |
| `conductor/tracks/unified-ui-ux-refactor_20260728/spec.cz.md` | Vytvořeno |
| `conductor/tracks/unified-ui-ux-refactor_20260728/metadata.json` | Vytvořeno |
| `conductor/tracks/unified-ui-ux-refactor_20260728/plan.md` | Přepsáno |
| `conductor/tracks/unified-ui-ux-refactor_20260728/plan.cz.md` | Vytvořeno |
| `conductor/audit/priority-track-reconciliation_20260729.md` | Tento soubor |
| `conductor/audit/priority-track-reconciliation_20260729.cz.md` | Český překlad |

## Ověření

- `git diff --check`: čistý (žádné whitespace chyby)
- `python3 -m json.tool metadata.json`: validní JSON
- `rg '[\x{4E00}-\x{9FFF}]'` přes `.cz.md` soubory: žádné shody
- `conductor.py validate`: exit 1 (INVALID) — 8 odložených chyb
  u historických tracků; žádný ze čtyř prioritních tracků se
  nevyskytuje v chybách
- Stav původního checkoutu: nedotčený (`M AGENTS.md`, `?? AGENTS.cz.md`,
  `?? docs/audits/`)
