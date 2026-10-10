# Audit stavu projektu - 28. cervence 2026

## Rozsah a Verdikt

Audit pokryva Git historii, stav Conductoru, architekturu aplikace, automaticke kontroly, security tooling, produkcni RPi runtime a zive chovani WebUI na commitu `638caa4`.

Dashboard je provozuschopny a cast backendove modularizace je realna, repozitar ale **neni dokonceny ani pripraveny k release**. Posledni hromadny commit uzavrel tracky bez splneni jejich vlastnich planu, pridal testovy deadlock a neimplementoval slibovany sjednoceny WebUI refaktor. Produkce servíruje aktualni soubory, takze nezmenene rozhrani neni problem deploye ani browser cache.

| Oblast | Skore | Hodnoceni podle dukazu |
| --- | ---: | --- |
| Runtime a hlavni funkce | 6/10 | Sluzba je aktivni; player, audio, Bluetooth, zarizeni a vetsina API odpovida. |
| Backendova architektura | 5/10 | Extrakce rout a services je realna, ale velke kompatibilitni monolity zustaly. |
| WebUI a responsive UX | 3/10 | Duplicitni navigace/statusy, mrtva telemetrie, prazdny Terminal a opakovane JS chyby. |
| Audio refaktor | 4/10 | Nektera API a routing existuji; planovany split, master UI a TUI prace chybi. |
| Testy a CI | 3/10 | 324 testu projde po vynechani jednoho deadlocku; package coverage je jen 58 %. |
| Bezpecnost a provoz | 4/10 | LAN/Tailscale allow-list existuje, ale ovladaci API nema uzivatelskou autentizaci a jedna zavislost je zranitelna. |
| Conductor governance | 2/10 | Registry odporuje planum, metadata, CI i runtime dukazum. |

## Co se Realne Zmenilo

Commity z 27. cervence prinesly uzitecnou praci: stare audio, player, device, CEC a system routy byly delegovany do `rpi_dashboard/services/` a `rpi_dashboard/api/`; pribyly panely Sit, System a Logy; ovladani navratu do dashboardu dostalo API/UI cast.

Finalni commit `638caa4` zmenil 46 souboru (`+1 174/-517`), velkou cast ale tvori plany, stav tracku a doprovodne soubory. Ve WebUI pridal jen 46 radku theme tokenu, osm HTML radku pro theme/PWA a 24 JS radku telemetrie. Bluetooth sub-header/footer neodstranil a stranku nepredelal. Viditelna Audio topologie pochazi uz z commitu `1792d56` a `61cd086` z 25. cervence.

## Kriticka Zjisteni

1. **Conductor tracky byly uzavreny administrativne, nikoli overenim.** Unified UI track vznikl a byl oznacen jako hotovy ve stejnem commitu, pricemz vsech 24 ukolu zustalo nezaskrtnutych. Audio track ma 43 nezaskrtnutych polozek a metadata stale rikaji `active`. Dalsich osm registry-complete tracku ma 13-33 nesplnenych ukolu. Pro `638caa4` neexistuje platny completion receipt.
2. **Finalni CI nikdy neproslo.** GitHub run `30326330766` byl po 15 minutach zrusen pri pytestu. Lokalni reprodukce ukazuje deadlock v `test_return_config_get_set`: `update_config()` drzi bezny Lock a vola dva helpery, ktere ho zkouseji ziskat znovu. Bez tohoto testu je vysledek `324 passed, 1 deselected` za 33 sekund.
3. **Slibovany WebUI refaktor chybi.** Live desktop i mobile kontrola ukazuje globalni a Bluetooth Basic/Expert/jazykove ovladani zaroven a dve stavove listy nad sebou. `theme.css` se temer nepouziva; CSS stale obsahuje stovky hardcoded barev a pixelovych hodnot.
4. **Globalni status bar se nemuze aktualizovat.** JavaScript hleda `status-cpu`, `status-ram` a `status-temp`, ale DOM ma pouze `sb-cpu` a `sb-ram`. Polling zacne az po rucnim zapnuti live monitoringu v Systemu. Produkce proto zustava na `CPU: --` a `RAM: --`.
5. **Extrahovane WebUI ma prazdny Terminal tab.** `rpi_dashboard/static/index.html` obsahuje tlacitko Terminal, ale nema panel `p-terminal`. Jeho JavaScript navic otevre WebSocket bez nacteni nebo odeslani povinneho tokenu. Embedded fallback HTML ma jinou implementaci, coz potvrzuje drift dvou zdroju UI.
6. **Kazde tri sekundy vznikne JavaScript vyjimka.** `updBr()` zapisuje do odstranenych elementu `brb`/`brs` bez null checku. Live session nasbirala pres 100 konzolovych chyb.

## Architektura, Kvalita a Bezpecnost

Hlavni soubory jsou stale prilis velke: `webserver.py` ma 3 088 radku, `tui.py` 2 674, Bluetooth BlueZ/service moduly 1 337/1 220, audio `__init__.py` 1 054 a `app.js` 915. Audio "split" prevazne prejmenoval stary monolit na package; planovane `state.py`, `mixer.py`, `matrix.py`, `multi_output.py`, `profiles.py` a dalsi moduly neexistuji.

Ruff hlasi unused import v `tests/test_pwa.py`. Mypy hlasi pet chyb v audio, smart-home a TUI kodu. Package coverage je 58 %, zvlaste slabe jsou media (15 %), audio DLNA (17 %), audio routing (20 %), player (35 %) a system (38 %). Live endpoint `/system/status` vraci HTTP 500, zatimco `/system/hw-stats`, `/audio/state`, `/bt/state` a `/ha/config` odpovidaji.

`pip-audit` nachazi CVE-2026-55404 v `yt-dlp 2026.6.9`, opravenou ve `2026.7.4`. Zranitelne shortcut-writing options se zde nepouzivaji, coz snizuje okamzitou dosazitelnost, ale nezbavuje projekt povinnosti upgrade. Bandit nema high-severity nalez, ale hlasi 14 medium a 307 low; medium skupina se tyka hlavne pevnych `/tmp` cest, bindu na vsechna rozhrani a validace URL schemat. `SECURITY.md` je stale neupraveny template s fiktivnimi verzemi. Trackovane backupy a zpracovane runtime reporty zbytecne znecistuji repo.

## Doporucene Poradi Opravy

1. Znovu otevrit kazdy registry-complete track, jehoz plan, metadata, receipt nebo verifikace nesouhlasi; `638caa4` brat jako neoverenou castecni implementaci.
2. Opravit return-service deadlock, vratit plny pytest pass, opravit Ruff/mypy a vyzadovat tyto kontroly v GitHub CI pred dalsi feature praci.
3. Opravit prazdny Terminal a jeho auth flow, chyby `updBr()`, `/system/status` a napojeni globalni telemetrie.
4. Provést unified WebUI track viditelne: odstranit Bluetooth globalni ovladani/footer, zapojit theme tokeny a overit desktop/mobile screenshoty i interakce.
5. Rozdelit audio track na male overitelne faze. Prejmenovani souboru nevydavat za modularizaci; rozdelit odpovednosti a doplnit chybejici master-volume/TUI funkce s testy.
6. Upgradovat `yt-dlp`, nahradit `SECURITY.md`, odstranit trackovane backupy/runtime artefakty a definovat explicitni autentizaci ovladacich endpointu.

## Zaznam Overeni

- Produkcni hashe `index.html`, `app.js`, `main.css` a `theme.css` odpovidaji aktualnimu checkoutu.
- Plny pytest: deadlock v `test_return_config_get_set`; zbytek: `324 passed, 1 deselected`.
- Coverage: 58 %; Ruff: 1 chyba; mypy: 5 chyb; `node --check`: pass.
- Playwright: potvrzeny desktop/mobile duplicity; overeno Audio; Terminal je prazdny; potvrzena opakovana konzolova vyjimka.
- `tools/verify-done.sh`: selhava, protoze `638caa4` nema uspesny exact-main receipt. Worktree navic obsahuje tento audit a aktualizaci contributor guide.
