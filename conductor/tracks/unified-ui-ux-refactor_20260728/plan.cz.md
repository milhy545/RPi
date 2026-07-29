# Implementační plán: Unified UI/UX Refactor a Theme Engine

## Pozadí

WebUI RPi Dashboard obsahuje duplicitní navigační prvky, duplicitní stavové
panely, mrtvou telemetrii a hardkódované vizuální hodnoty. Zdravotní audit
projektu (2026-07-28) potvrdil: globální prvky vlastněné sekcí Bluetooth
(sub-header/sub-footer) zůstávají viditelné vedle app-level headeru/
navigace; tokeny `theme.css` existují, ale integrace závisí na
`main.css`/`themes.css`; ID prvků stavového panelu neodpovídají JS
selektorům (`sb-cpu` vs `status-cpu`); `updBr()` vyhazuje null-reference
každé 3 sekundy; a Terminal tab je prázdný. TUI (`tui.py`) má taby a
přepínač CZ/EN, ale zatím neodpovídá struktuře WebUI.

## Fáze 1: Audit a integrace CSS tokenů

- [ ] Úkol: Ověřit, že tokeny `:root` v `rpi_dashboard/static/css/theme.css`
  pokrývají všechny požadované kategorie tokenů: paleta barev, škála
  spacingu, typografie, poloměry rámečků a tokeny stavů komponent.
  Mezery zdokumentovat v
  `conductor/tracks/unified-ui-ux-refactor_20260728/token-gap-report.md`
  a `token-gap-report.cz.md`.
- [ ] Úkol: Zajistit, že media queries v `responsive.css` používají CSS
  proměnné místo hardkódovaných pixelových hodnot tam, kde je to vhodné.
- [ ] Úkol: Ověřit, že `audio.css` neuvádí duplicitní barvy kolidující
  s tokeny `theme.css`.
- [ ] Úkol: Zauditovat `main.css` a `themes.css` ohledně hardkódovaných
  hodnot palety, které duplikují definici tokenu bez odůvodnění; nahradit
  nebo zdokumentovat každý případ.
- [ ] Ověření: Zachycení Playwright screenshot baseline před změnami;
  sémantické srovnání po změnách prokazuje žádnou vizuální regresi.

## Fáze 2: Odstranění duplicitních globálních ploch sekce Bluetooth

- [ ] Úkol: Identifikovat a odstranit globální prvky vlastněné sekcí
  Bluetooth (sub-header, sub-footer, sekundární jazyková lišta,
  sekundární stavový panel) z `rpi_dashboard/static/index.html`.
  Ponechat jedinečné app-level prvky.
- [ ] Úkol: Odstranit nebo refaktorovat odpovídající funkce v `app.js`,
  které plní duplicitní BT globální prvky (`btSetMode`, BT přepínač
  jazyka, BT stavové indikátory duplikující stavový panel aplikace).
- [ ] Úkol: Ověřit, že Bluetooth tab zachovává své lokální ovládače
  (scan, pair, connect) a ztrácí pouze globální duplicity.
- [ ] Ověření: Vizuální kontrola na 1920x1080 potvrzuje jeden header,
  jednu navigační lištu, jeden ovládač jazyka a jeden stavový panel.

## Fáze 3: Oprava napojení telemetrie stavového panelu

- [ ] Úkol: Opravit nesoulad DOM ID: buď přejmenovat `sb-cpu`/`sb-ram`
  v `index.html` na `status-cpu`/`status-ram` nebo aktualizovat selektory
  v `app.js` tak, aby odpovídaly skutečným DOM ID. Přidat prvek
  `status-temp` pokud chybí.
- [ ] Úkol: Zajistit, že pravidelné načítání `/system/hw-stats` začíná
  automaticky při načtení stránky (není podmíněno ruční aktivací System
  tabu). `/system/status` zůstává samostatným endpointem pro přiřazení
  procesů/jader.
- [ ] Úkol: Zobrazovat `--` pro CPU, RAM a teplotu, pokud je backend
  endpoint nedostupný nebo vrací chybu.
- [ ] Ověření: Načtení stránky; stavový panel zobrazuje živé hodnoty
  do 2 sekund.

## Fáze 4: Oprava chyb v konzoli

- [ ] Úkol: Opravit null-reference v `updBr()` přidáním null stráží
  před zápisem do prvků `brb`/`brs`, nebo funkci odstranit, pokud
  prvky po fázi 2 neexistují.
- [ ] Úkol: Zauditovat `app.js` dalším null-reference rizikům na
  odstraněných prvcích; přidat stráže nebo odstranit mrtvý kód.
- [ ] Ověření: Otevřít konzoli; nula chyb během 30-sekundového
  nečinné relace na kartě Player.

## Fáze 5: Shell Terminal tabu

- [ ] Úkol: Přidat neprázdný Terminal panel shell do `index.html`, který
  zobrazuje uzamčený/stupňový stav a integrační smlouvu (očekávaný
  WebSocket transport, požadavek na autentizaci).
- [ ] Úkol: Panel nesmí otevírat WebSocket spojení, dokud terminal/auth
  tracky nedodají PTY transport a Admin autorizaci. Jasné vymezení:
  UI track vlastní shell a smlouvu; terminal track vlastní transport;
  auth track vlastní řízení přístupu.
- [ ] Ověření: Terminal tab zobrazuje viditelný, neprázdný panel s textem
  integrační smlouvy.

## Fáze 6: Ověření responzivního layoutu

- [ ] Úkol: Ověřit layout WebUI na 390x844 (mobil iPhone 14 Pro):
  navigace se správně sbalí, dotykové cílové plochy >= 44px, obsah
  je čitelný bez horizontálního skrolování.
- [ ] Úkol: Ověřit na 768x1024 (iPad): dvou-sloupcový layout tam,
  kde je to vhodné, žádné překrývající se prvky.
- [ ] Úkol: Ověřit na 1366x768 (notebook): plný layout se vejde bez
  přetékání, všechny taby dostupné.
- [ ] Úkol: Ověřit na 1920x1080 (desktop): kompletní layout s dostatečnými
  mezerami, žádné roztažené nebo stlačené prvky.
- [ ] Úkol: Zachytit Playwright screenshots na každém rozlišení a uložit
  do `conductor/tracks/unified-ui-ux-refactor_20260728/evidence/`.
- [ ] Ověření: Všechny 4 screenshots zachyceny; žádné viditelné porušení
  layoutu.

## Fáze 7: Parita TUI

- [ ] Úkol: Ověřit strukturu tabů v `tui.py`: Player, Audio, Bluetooth,
  Devices, Network, Terminal, System.
- [ ] Úkol: Ověřit, že stavový panel TUI čte CPU/RAM/teplotu přes
  sdílený Python modul `rpi_dashboard.services.system` (přímé čtení
  z `/proc` a `/sys`), nikoli přes HTTP self-call do WebUI API.
- [ ] Úkol: Ověřit, že přepínač CZ/EN v TUI kopíruje výchozí nastavení
  WebUI (`cz`) a že české řetězce v TUI vynechávají diakritiku pro
  kompatibilitu s TV tty.
- [ ] Úkol: Použít barevné tokeny z `theme.css` palety v Textual CSS,
  kde framework umožňuje (hranice, aktivní stavy, barvy textu).
- [ ] Ověření: Zaměřené Textual `run_test()` pytest pokrytí pro
  produkční `tui.py` projde; manuální ověření na `/dev/tty1` na RPi
  potvrdí správné zobrazení tabů a stavového panelu. Prototyp
  `modern.py` se nepoužívá jako referenční test.

## Fáze 8: Plná branka ověření

- [ ] Úkol: Spustit `uv run python -m pytest -q` — všechny testy projdou.
- [ ] Úkol: Spustit `uv run ruff check .` — žádné lint chyby.
- [ ] Úkol: Zachytit Playwright důkazy pro všechna 4 rozlišení.
- [ ] Úkol: Spustit `tools/verify-done.sh` a potvrdit exit code 0.
- [ ] Ověření: CI receipt zapsán pro SHA commitu.

## Kritéria přijetí

- [ ] Jednotný app header, jedna navigační lišta, jeden ovládač jazyka/
  tématu, jeden globální stavový panel — žádné globální prvky vlastněné
  sekcí Bluetooth duplikující app-level plochy.
- [ ] Stavový panel zobrazuje živé CPU/RAM/teplotu z `/system/hw-stats`.
- [ ] Nula chyb v konzoli během čisté 30sekundové relace.
- [ ] Terminal tab zobrazuje neprázdný shell s integrační smlouvou;
  žádný WebSocket otevřen, dokud jej terminal/auth tracky nedodají.
- [ ] Responzivní layout ověřen na 390x844, 768x1024, 1366x768, 1920x1080.
- [ ] Playwright screenshots zachyceny pro všechna 4 rozlišení.
- [ ] Struktura tabů TUI, stavový panel a přepínač CZ/EN odpovídají WebUI.
- [ ] Všechny existující testy projdou: `uv run python -m pytest -q`.
- [ ] Lint projde: `uv run ruff check .`.
- [ ] `tools/verify-done.sh` projde s platným CI potvrzením.
