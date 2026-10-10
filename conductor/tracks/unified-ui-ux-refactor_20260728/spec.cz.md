# Specifikace: Unified UI/UX Refactor a Theme Engine

## Přehled

Dodat jednotný aplikační shell pro WebUI RPi Dashboard a dosáhnout
smysluplné vizuální parity s produkčním TUI. Aktuální WebUI obsahuje
duplicitní navigační prvky, duplicitní stavové panely, mrtvou telemetrii
a hardkódované vizuální hodnoty, které brání responzivnímu chování.
Tento track zavede architekturu CSS proměnných, odstraní duplicitu,
zprovozní živou telemetrii a ověří výsledek na cílových rozlišeních.

## Motivace

Zdravotní audit projektu (2026-07-28) potvrdil: duplicitní globální prvky
vlastněné sekcí Bluetooth a stavové panely zůstávají viditelné; tokeny
`theme.css` existují, ale nejsou plně integrované; ID prvků stavového
panelu neodpovídají JS selektorům (`sb-cpu`/`sb-ram` vs
`status-cpu`/`status-ram`); Terminal tab je prázdný; a opakující se
chyba `updBr()` nastává každé 3 sekundy. Žádný z 24 plánovaných
úkolů nebylo dokončeno. Track byl označen `[x]` v registru bez
platného CI potvrzení a bez ověření.

## Rozsah

### V rozsahu

- Jednotný aplikační shell: jeden header, jedna navigační lišta, jeden
  ovládač jazyka/tématu, jeden globální stavový panel.
- Odstranit globální prvky vlastněné sekcí Bluetooth, které duplikují
  app-level plochy (sub-header, sub-footer, sekundární jazyková lišta,
  sekundární stavový panel).
- Hranice Basic/Expert/Admin: UI zobrazuje ovládací prvky, jejichž
  viditelnost je určena server-side autorizací. Režimy Expert a Admin
  musí vyžadovat autentizované serverové schopnosti (např. session token
  nebo elevovanou roli) předtím, než UI zpřístupní rozšířené ovládače.
  Skrytí UI prvků nikdy není bezpečnostní hranicí; skutečná implementace
  autorizace je závislostí vlastněnou auth/security trackem a musí být
  dodána před zpřístupněním Expert/Admin ovládacích prvků.
- Architektura CSS proměnných s reálnými aktuálními cestami:
  `rpi_dashboard/static/css/theme.css` (definice), spotřebovávané
  `main.css`, `themes.css` a `responsive.css`.
- Živá telemetrie stavového panelu: opravit nesoulad DOM ID, navázat
  pravidelné načítání `/system/hw-stats` na správné prvky, zobrazovat
  `--` pokud je backend nedostupný. `/system/status` zůstává samostatným
  endpointem pro přiřazení procesů/jader a nepoužívá se pro stavový
  panel.
- Ověření responzivity na 4 rozlišeních: 390x844 (mobil), 768x1024
  (tablet), 1366x768 (notebook), 1920x1080 (desktop).
- Nula chyb v konzoli při čistém načtení.
- Důkaz screenshots z Playwright pro každé rozlišení.
- Parita TUI s produkčním `tui.py` (ne prototypem `modern.py`):
  konzistentní struktura tabů, stavový panel čtoucí CPU/RAM/teplotu
  přes sdílený Python modul `rpi_dashboard.services.system` (přímé
  čtení z `/proc` a `/sys`, nikoli HTTP self-call), přepínač CZ/EN a
  barevně shodné téma. Ověření TUI: zaměřené Textual `run_test()`
  pytest pokrytí pro produkční `tui.py` a manuální důkaz na `/dev/tty1`
  na RPi. Prototyp `modern.py` se nepoužívá jako referenční test.
- Shell Terminal tabu: neprázdný Terminal panel s uzamčenými/stupňovými
  stavy a integrační smlouvou definující očekávaný WebSocket transport
  a požadavky na autentizaci. Za plný PTY transport a autorizaci administrátora
  odpovídají terminal/auth tracky; obojí musí být dodáno před zpřístupněním
  terminálu.

### Mimo rozsah

- Adopce frontend frameworku (React, Vue, Svelte atd.).
- Build služba, bundler nebo Vercel nasazení.
- Změny backend API (pokryto trackem backend-modularization).
- Audio topologie canvas nebo multi-mixer UI (pokryto trackem
  audio-fullstack).
- Bezpečnostní zpevnění control endpointů (pokryto bezpečnostním
  trackem).
- Implementace WebSocket PTY transportu (pokryto terminal trackem).
- Implementace autentizace/autorizace (pokryto auth/security trackem).

## Kritéria přijetí

1. `theme.css` definuje `:root` CSS vlastnosti pro všechny požadované
   kategorie tokenů: paleta barev, škála spacingu, typografie, poloměry
   rámečků a tokeny stavů komponent (hover, active, disabled).
2. `main.css` a `themes.css` spotřebovávají tokeny z `theme.css`. Žádné
   hardkódované hodnoty palety nezůstávají, pokud duplikují definici
   tokenu bez odůvodnění. Sémantický regresní důkaz zachycen přes
   Playwright screenshots, nikoli křehkými `var(--` počty.
3. Globální prvky vlastněné sekcí Bluetooth, které duplikují app-level
   plochy (sub-header, sub-footer, sekundární jazyková lišta, sekundární
   stavový panel), jsou odstraněny z `index.html` a `app.js`.
4. Jeden globální stavový panel zobrazuje CPU, RAM a teplotu pomocí
   správných DOM ID odpovídajících `app.js` selektorům.
5. Stavový panel zobrazuje živé hodnoty z `/system/hw-stats` v intervalu
   pravidelného načítání; zobrazuje `--` pokud je endpoint nedostupný.
6. Chyba null-reference v `updBr()` je opravena; nula chyb v konzoli
   během 30sekundové čisté relace.
7. Terminal tab zobrazuje neprázdný panel shell s uzamčenými/stupňovými
   stavy. Panel zobrazuje integrační smlouvu (očekávaný transport,
   požadavek na autentizaci), ale neotevírá WebSocket dokud terminal/auth
   tracky nedodají PTY transport a Admin autorizaci.
8. Responzivní layout ověřen Playwright screenshots na 390x844, 768x1024,
   1366x768 a 1920x1080.
9. Produkční `tui.py` zobrazuje shodnou strukturu tabů, stavový panel
   čtoucí z `rpi_dashboard.services.system`, přepínač CZ/EN a barevně
   shodné téma.
10. Všechny existující testy projdou: `uv run python -m pytest -q`.
11. Lint projde: `uv run ruff check .`.
12. `tools/verify-done.sh` projde s platným CI potvrzením.

## Nefunkční požadavky

- Žádný frontend build krok nebo runtime závislost mimo statické soubory.
- Architektura CSS proměnných musí podporovat budoucí přepínání světlý/
  tmavé téma přes selektor `[data-theme]`.
- Pravidelné načítání stavového panelu nesmí překročit jeden požadavek
  za sekundu kvůli ochraně 1 GB RPi paměťového rozpočtu.
- TUI musí nadále vynechávat českou diakritiku kvůli omezení TV konzole/tty
  bufferu.

## Požadované důkazy

- Playwright screenshots pro každou velikost rozlišení.
- Zachycení logu konzole prokazující nulový počet chyb.
- Textual `run_test()` pytest pokrytí pro `tui.py`.
- Manuální důkaz na `/dev/tty1` na RPi.
- `git diff --stat` všech změněných souborů.
- `tools/verify-done.sh` exit code 0 s receipt SHA.
