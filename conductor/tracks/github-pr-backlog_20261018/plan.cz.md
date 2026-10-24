# Plán implementace: Vyřešení fronty GitHub PR

## Fáze 1 — Zastavit neprověřenou automatizaci

- [x] Vypnout původní bezpodmínečný auto-merge workflow.
- [x] Vypnout všechny požadavky na auto-merge aktivní v počátečním seznamu PR.
- [x] Přidat podmínku štítku `merge-approved`, při každé události PR znovu ověřit štítek i stav draftu a otestovat zrušení auto-merge.
- [x] Gated workflow znovu zapnout poté, co byla jeho nová verze v `main` a nezůstaly otevřené PR ani zařazené auto-merge požadavky.
- [x] Opravit bránu commitů a receiptů: zakázat amend commity, odmítat runtime artefakty a jasně selhat při chybějícím receipt.
- [x] Přizpůsobit GitHub CI politice lokálních Actions přes přímý Git fetch a lokální skripty; zachovat povinný check `verify-done` a importovat receipt přesných main commitů z metadat úspěšného běhu.
- [x] Po blokaci merge aktivním rulesetem `main` zapnout GitHub CodeQL default setup pro Actions, JavaScript/TypeScript a Python; před sloučením ověřit analýzu přesné revize PR.

## Fáze 2 — Zaznamenat a roztřídit frontu

- [x] Zachytit počáteční seznam otevřených PR a aktuální SHA GitHub `main`.
- [x] Zachovat čtyři lokální commity a vytvořit čistý izolovaný worktree z GitHub `main`.
- [x] Zaznamenat rozhodnutí pro každé původní PR a před uzavřením nebo sloučením jej znovu ověřit.
- [x] Po závěrečné kontrole diffu uzavřít PR #93 a #96 z jiných projektů jako `invalid` s jasným vysvětlením.
- [x] Duplicitní PR označit jako `duplicate` až po ověření a pojmenování nástupce.

## Fáze 3 — Sloučit změny a ověřit kandidáty

- [x] Znovu prověřit PR #85: aktuální diff obsahoval jen zástupné report tracky, runtime soubor režimu a smazání generovaných reportů; PR byl uzavřen jako neplatný, protože nezůstala žádná změna aplikace ani platný report k zachování.
- [x] Sloučit změny přístupnosti včetně přeložených přístupných názvů a ovládání zavření formuláře zpětné vazby.
- [x] Sloučit změny síťových informací v TUI včetně DHCP leases a náhradní hodnoty RPi-service.
- [x] Sloučit službu pro síťové informace do jediné implementace a otestovat adresy, routy, rozhraní i fallback.
- [x] Sloučit TUI helper pro příkazy a procfs detekci procesů; doplnit cílené testy rodičovské PID rodiny, průměru CPU a ukončení kandidátního procesu; vynechat generované reporty a duplicitní testy.
- [x] Prověřit zamčené prostředí projektu a připravit opravené verze zranitelných balíků `multidict`, `pip` a `urllib3`, které pokrývá PR #62.
- [x] Připravit cíleného nástupce pro #62, #111 a #113: vyžadovat opravená minima aiohttp a certifi a pip 26.2.2 ve vývojovém extra; merge i uzavření původních PR podmínit úspěchem nástupce.
- [x] Sloučit otestovaný kandidát změny lockfile a potom uzavřít PR #62, #111 a #113 jako nahrazené; #62 se zavřel při merge a dvě PR s ARIA/závislostmi po úspěšné přesné main CI #117.
- [x] Samostatně prověřit změny stavů služeb, Kodi portu a DLNA: #56 zavřen jako wontfix, protože soubor s invocation stavem systemd není ekvivalent `systemctl is-active`; #58 nahradil procfs lookup a testy v #109; #68 už byl implementován v `main`.
- [x] Odmítnout změny workflow s neplatným YAML, příliš širokými oprávněními, nepřipnutými akcemi třetích stran nebo nevyřešenými připomínkami; #96 byl po kontrole diffu zavřen jako neplatný.

## Fáze 4 — Postupně sloučit

- [x] Aktualizovat každý vybraný PR podle aktuálního `main` a zkontrolovat přesný diff.
- [x] Pro vybrané kandidáty na Milhy-PC spustit požadované `github-safe` kontroly a cílené testy.
- [ ] Po potvrzení aktuální adresy RPi spustit neinvazivní RPi candidate smoke pro změny dotýkající se runtime; živý SSH alias a uložená mapa zařízení si odporují, proto se hardware kandidát zatím nestagoval.
- [x] Počkat na úspěšné povinné kontroly a review, potom sloučit právě jeden PR metodou rebase.
- [x] Po každém sloučení znovu ověřit nebo aktualizovat následujícího kandidáta.
- [x] Nahrazené duplicity uzavřít až po potvrzení sloučení nástupce.

## Fáze 5 — Ověřit a uzavřít track

- [x] Potvrdit stav všech PR z původního seznamu a znovu načíst živý seznam otevřených PR; je prázdný.
- [x] Ověřit GitHub `main`, povinné kontroly, CI receipt, izolovaný worktree a zachování čtyř lokálních commitů.
- [x] Spustit `tools/verify-done.sh` pro aktuální SHA main s importovaným přesným main receiptem a izolovaným worktree. Track ponechat aktivní pouze kvůli samostatnému RPi candidate smoke výše.

## Počáteční inventář PR a plánovaný postup

| PR | Téma | Plán |
|---|---|---|
| #93 | Nesouvisející aplikační/repozitářové soubory | Po poslední kontrole diffu uzavřen jako neplatný. |
| #85 | Velký sync balík, změny aplikace a Conductor reporty | Uzavřen jako neplatný po kontrole aktuálního diffu: zůstaly jen zástupné soubory, runtime stav a smazané generované reporty; nebyl důvod rozdělovat platný kód ani report. |
| #92, #94–#95, #97–#102, #110, #112 | Přístupnost | Uzavřeno se štítkem `duplicate`, poté co byly platné změny sloučeny a otestovány v #106 (`5606ad2d2fb090676101fe9d8f3b2b2802f37867`). |
| #42–#43, #45–#49, #60–#61, #64, #67 | TUI Bluetooth/síť/helpery procesů | Uzavřeno se štítkem `duplicate` po konsolidaci a testech v #105 (`c4384c5deb14cb6812d25650a26a7df201410414`). |
| #54–#55, #65, #71–#73, #78–#91 bez #85 | Backend síťové informace | Uzavřeno se štítkem `duplicate` po konsolidaci a testech v #104 (`857cd80f6fa4673d16482667e712f026679a9251`). |
| #77, #81 | Enumerace procesů na RPi | Implementace je v main; cílené jedinečné regresní testy byly sloučeny v #116 s přesným main receipt. #77 se zavřel při merge #116, #81 je uzavřen jako nahrazený. Mazání reportů převzato nebylo. |
| #56 | Zjišťování stavu služby | Uzavřeno jako wontfix: přítomnost interního souboru systemd není ekvivalentem `systemctl is-active`. |
| #58 | Vyhledání DLNA procesu | Uzavřeno se štítkem `duplicate`; procfs lookup je v `main` a #109 (`32f68c40d6bab7e2c8ffc68f2c3b51040cba8ce4`) sjednotil stav a PID a přidal cílené testy. |
| #62 | Aktualizace závislostí | Uzavřeno jako nahrazené PR #117, které se sloučilo jako `f9b8a2ef7d3a325e6edef8670088730ddeeee2a8` s přesnou main CI a receiptem. |
| #66 | Signalizace MPV procesu | Uzavřeno se štítkem `duplicate` po sloučení bezpečnějšího přesného hledání procesu v #108 (`36a6e50c79424fabb2d0273f3604e93587fc5113`). |
| #68 | Detekce Kodi portu | Uzavřeno se štítkem `duplicate`; aktuální `main` už kontroluje IPv4/IPv6 procfs a ošetřuje prázdné soubory. |
| #96 | PR-agent workflow | Uzavřen jako neplatný: duplicitní `runs-on`, nepřipnutá akce třetí strany, široká oprávnění pro zápis a předání tajného klíče. |
| #111, #113 | ARIA štítky zavírání modálních oken a minima závislostí | Uzavřeno se štítkem `duplicate`; změny UI jsou v #106 a minima závislostí zachoval #117. |
| #114, #115 | Přístupnost Bluetooth topologie | #114 uzavřeno se štítkem `duplicate`; #115 sloučeno jako `d1dd878eebc9f02e88df4a40b319a6215d67eb44`. |

## Záznam změn

- 2026-10-18: Zaznamenán seznam 48 PR, vypnut bezpodmínečný auto-merge a vytvořen izolovaný worktree z GitHub `main` na `4b7caeed68c2378507d81bba7136fe51e5f64faa`.
- 2026-10-18: Implementována brána auto-merge s explicitním štítkem a zahájena oprava lokálního kontraktu commitů/receiptů; testy a CI ještě čekají.
- 2026-10-18: Přidány regresní testy helperu commitů, chybějícího/platného receipt a schválení/zrušení workflow; 21 cílených testů, ShellCheck, shell syntax i parsování YAML prochází. Plné lokální CI ještě čeká.
- 2026-10-18: První plný běh odhalil, že `pip-audit` kontroloval globální balíky hostu. CI nyní před auditem synchronizuje zamčené prostředí projektu. V locku bylo 6 nálezů v balících `multidict 6.7.1`, `pip 26.1.2` a `urllib3 2.7.0`; aktualizováno na `6.9.1`, `26.2.1` a `2.8.0`. `pip-audit` v prostředí projektu nyní hlásí nula známých zranitelností. Opraveny dva testy závislé na Bluetooth adaptéru hostitele a test receipt kontraktu. Plná CI se opakuje.
- 2026-10-18: GitHub API potvrzuje, že repozitář povoluje pouze lokální workflow/akce; dosavadní CI volalo zakázané marketplace akce a končilo před vytvořením jobů. Tyto kroky nahrazeny přímým stažením Git refu a lokálním CI skriptem, povinný check `verify-done` zůstal zachován. Odstraněna závislost na artifact akcích, handoff nově importuje receipt z úspěšného běhu pro přesný `main` commit a chrání lokální adresáře receiptů/reportů před mazáním při synchronizaci.
- 2026-10-18: První vzdálená CI potvrdila správné stažení checkoutu i průchod celé testovací sady, ale odhalila generované reporty ve dvou API integračních testech a předpoklad pojmenované větve ve `verify-done.sh`. Výstup testů byl přesměrován do `tmp_path`; kontrola čistého stromu i receipt zůstala. Kontrola tracking větve se přeskočí pouze u detached CI refu, jehož SHA workflow předem ověřilo.
- 2026-10-18: Nesouvisející PR #93 a #96 byly po kontrole aktuálního diffu uzavřeny se štítkem `invalid` a vysvětlením.
- 2026-10-18: Aktuální review #103 našlo problémy s původem receiptů, kontrolou runtime artefaktů v celém PR diffu, coverage v hosted CI, validací profilů a opakovaným importem receiptů. Opravy jsou lokálně hotové: přesný receipt z main push, selektivní přenos RPi kandidátního receipt, povinné projektové nástroje, výpis reportu při chybě a izolované testovací cesty reportů. Cílená sada prochází (44 testů); nová vzdálená CI a review Kilo ještě čekají před sloučením.
- 2026-10-18: Následné review odhalilo, že detached lokální checkout mohl přeskočit kontrolu push stavu a chyba `git status` mohla být vyhodnocena jako čistý strom. Detached ověření nyní projde jen v GitHub Actions s odpovídajícím `GITHUB_SHA` a `GITHUB_REF`; chyby kontroly stromu a runtime diffu selžou. Cílené testy verifieru a workflow procházejí (22 testů); před sloučením se musí zopakovat plný lokální profil a vzdálené review nad aktualizovaným commitem.
- 2026-10-18: Další hosted CI odhalila, že proměnná PR `VERIFY_BASE_SHA` z runneru pronikla do syntetických testovacích repozitářů verifieru, které nemají tento základní commit. Fixture nyní tuto CI proměnnou čistí, pokud ji test výslovně nenastaví; všech 7 testů verifieru lokálně prochází. Plná lokální CI a nové hosted review ještě čekají.
- 2026-10-18: Kontrola nevyřešených review vláken odhalila dvě zbývající mezery ve verifieru a handoffu: lokální feature větev mohla přijmout PR receipt jako důkaz dokončení a rsync mohl zahrnout nebo smazat nesouvisející soubory receiptů. Lokální ověření nyní vyžaduje původ `main-push`; PR receipt přijímá pouze odpovídající PR běh Actions pro přesné SHA. Handoff zahrne jen přesný RPi kandidátní receipt a ochrání ostatní receipty/reporty před `--delete`; oba případy mají regresní testy. Cílená sada 28 testů verifieru, handoffu a workflow prošla; plná CI a review ještě čekají.
- 2026-10-18: Následné review zjistilo, že `github-safe` nemohl projít gateway Milhy-PC bez hardwarového receipt a že Actions nejprve stahovaly pohyblivý ref a až poté jej porovnávaly s neměnným `GITHUB_SHA`. Gateway nyní vyžaduje E2E/RPi důkazy jen pro `milhy-full`; oba CI workflow stahují a checkoutují přímo SHA události. Regresní test spouští reálnou cestu gateway bez pushnutí a bez hardwarových artefaktů. Plná CI a hosted review ještě čekají.
- 2026-10-18: Cílená sada gateway, workflow, verifieru a handoffu prochází (69 testů) po nastavení projektového `PYTHONPATH`; stále je nutné zopakovat plné `github-safe` a nové hosted review.
- 2026-10-18: CI dispatch gateway pro feature větev používá `workflow_dispatch` a jeho receipt má jiný zdroj než PR nebo main-push. `verify-done.sh` jej nyní přijme jen pro přesné SHA v odpovídající události Actions; lokální dokončení stále vyžaduje původ main-push. Přibyl samostatný regresní test; cílená a plná CI ještě čekají.
- 2026-10-18: Aktivní ruleset GitHub `main` blokoval #103, protože požadovaný nástroj CodeQL nebyl nastaven. Zapnuli jsme GitHub default setup pro Actions, JavaScript/TypeScript a Python bez oslabení pravidel větve; běží úvodní scan a před merge je nutné ověřit analýzu revize PR.

- 2026-10-24: Znovu jsem prověřil uzavřený PR #85 podle aktuálního diffu. Obsahuje pouze zástupné report tracky, runtime soubor režimu a smazání generovaných reportů; nezůstala žádná platná změna aplikace ani uživatelský report k zachování. Doplnil jsem cílené testy procfs guardu pro rodičovské PID, průměr CPU a řádné/nucené ukončení kandidáta, bez převzetí mazání reportů a opakovaných případů.

- 2026-10-24: PR #116 byl sloučen jako c0193130ede0aff820c85ea9608b7e8851ac4630 se stromem 55ba040e8ea67ef1300fc30062d1a7205ed114b3; main push run 40069464037 prošel a vytvořil conductor/ci/receipts/c0193130ede0aff820c85ea9608b7e8851ac4630-20261024-061627-push.json, výsledek VERIFY-DONE: PASS. Nástupce přidal pět cílených regresních testů guardu; #77 se zavřel při merge, #81 byl uzavřen jako nahrazený.
- 2026-10-24: Prověřil jsem závislosti v #62, #111 a #113. Sloučený lock už obsahuje novější aiohttp a certifi, ale deklarovaná minima stále dovolují zranitelné verze; lock má také pip 26.2.1. Cílený nástupce nyní zvyšuje minima na aiohttp>=3.14.4, certifi>=2026.10.19 a pip>=26.2.2 ve vývojovém extra.
- 2026-10-24: PR #117 byl sloučen jako f9b8a2ef7d3a325e6edef8670088730ddeeee2a8 (strom d2b32dce9d93ec614abed7b39c8168136ad5841b). Main push CI run 40070217677 prošel celým github-safe (819 testů, coverage 69,26 %), pip-audit i verify-done; receipt: conductor/ci/receipts/f9b8a2ef7d3a325e6edef8670088730ddeeee2a8-20261024-062804-push.json. Kilo review PR #117 prošel bez nálezů a povinné PR kontroly prošly. Nepovinný `pr-title/grammar` vrátil externí 401 a není součástí povinných kontrol rulesetu. PR #62, #111 a #113 jsou zavřené; duplicity dostaly štítek až po ověření nástupců. Workflow Queue PR Auto-Merge je znovu aktivní po vyprázdnění seznamu otevřených PR. Předchozí main běh #106 odhalil nález pip-audit kvůli starým minimům závislostí; #117 to řeší a audit přesné aktuální main větve prochází. Root checkout zůstal nedotčený se čtyřmi lokálními commity; první mirror kontrola narazila na zastaralý lokální `main`, poté verify-done uspěl proti izolovanému worktree na f9b8a2e. Neinvazivní RPi candidate smoke čeká na potvrzení aktuální mapy hostu.
