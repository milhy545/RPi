# Plán implementace: Vyřešení fronty GitHub PR

## Fáze 1 — Zastavit neprověřenou automatizaci

- [x] Vypnout původní bezpodmínečný auto-merge workflow.
- [x] Vypnout všechny požadavky na auto-merge aktivní v počátečním seznamu PR.
- [x] Přidat podmínku štítku `merge-approved`, při každé události PR znovu ověřit štítek i stav draftu a otestovat zrušení auto-merge.
- [ ] Workflow znovu zapnout až po nasazení nové verze na `main`.
- [x] Opravit bránu commitů a receiptů: zakázat amend commity, odmítat runtime artefakty a jasně selhat při chybějícím receipt.
- [x] Přizpůsobit GitHub CI politice lokálních Actions přes přímý Git fetch a lokální skripty; zachovat povinný check `verify-done` a importovat receipt přesných main commitů z metadat úspěšného běhu.
- [x] Po blokaci merge aktivním rulesetem `main` zapnout GitHub CodeQL default setup pro Actions, JavaScript/TypeScript a Python; před sloučením ověřit analýzu přesné revize PR.

## Fáze 2 — Zaznamenat a roztřídit frontu

- [x] Zachytit počáteční seznam otevřených PR a aktuální SHA GitHub `main`.
- [x] Zachovat čtyři lokální commity a vytvořit čistý izolovaný worktree z GitHub `main`.
- [ ] Zaznamenat rozhodnutí pro každé původní PR a před uzavřením nebo sloučením jej znovu ověřit.
- [x] Po závěrečné kontrole diffu uzavřít PR #93 a #96 z jiných projektů jako `invalid` s jasným vysvětlením.
- [ ] Duplicitní PR označit jako `duplicate` až po uvedení ověřeného nástupce.

## Fáze 3 — Sloučit změny a ověřit kandidáty

- [x] Znovu prověřit PR #85: aktuální diff obsahoval jen zástupné report tracky, runtime soubor režimu a smazání generovaných reportů; PR byl uzavřen jako neplatný, protože nezůstala žádná změna aplikace ani platný report k zachování.
- [ ] Sloučit změny přístupnosti včetně přeložených přístupných názvů a ovládání zavření formuláře zpětné vazby.
- [ ] Sloučit změny síťových informací v TUI včetně DHCP leases a náhradní hodnoty `RPi-service`.
- [ ] Sloučit službu pro síťové informace do jediné implementace a otestovat adresy, routy, rozhraní i fallback.
- [x] Sloučit TUI helper pro příkazy a procfs detekci procesů; doplnit cílené testy rodičovské PID rodiny, průměru CPU a ukončení kandidátního procesu; vynechat generované reporty a duplicitní testy.
- [x] Prověřit zamčené prostředí projektu a připravit opravené verze zranitelných balíků `multidict`, `pip` a `urllib3`, které pokrývá PR #62.
- [ ] Sloučit otestovaný kandidát změny lockfile a potom uzavřít PR #62 jako nahrazený tímto kandidátem.
- [ ] Samostatně prověřit změny procesů, stavů služeb, kontroly Kodi portu, DLNA a závislostí.
- [ ] Odmítnout změny workflow s neplatným YAML, příliš širokými oprávněními, nepřipnutými akcemi třetích stran nebo nevyřešenými připomínkami.

## Fáze 4 — Postupně sloučit

- [ ] Aktualizovat každý vybraný PR podle aktuálního `main` a zkontrolovat přesný diff.
- [ ] Na Milhy-PC spustit povinné kontroly a testy kandidáta; při změně runtime chování provést bezpečnou kontrolu na RPi.
- [ ] Počkat na úspěšné povinné kontroly a review, potom sloučit právě jeden PR metodou rebase.
- [ ] Po každém sloučení znovu ověřit nebo aktualizovat následujícího kandidáta.
- [ ] Nahrazené duplicity uzavřít až po potvrzení sloučení nástupce.

## Fáze 5 — Ověřit a uzavřít track

- [ ] Potvrdit stav všech PR z původního seznamu a znovu načíst živý seznam otevřených PR.
- [ ] Ověřit GitHub `main`, povinné kontroly, CI receipt, lokální worktree a zachování čtyř lokálních commitů.
- [ ] Spustit `tools/verify-done.sh`; při chybějícím důkazu ponechat track aktivní a nahlásit přesný blokátor.

## Počáteční inventář PR a plánovaný postup

| PR | Téma | Plán |
|---|---|---|
| #93 | Nesouvisející aplikační/repozitářové soubory | Po poslední kontrole diffu uzavřen jako neplatný. |
| #85 | Velký sync balík, změny aplikace a Conductor reporty | Uzavřen jako neplatný po kontrole aktuálního diffu: zůstaly jen zástupné soubory, runtime stav a smazané generované reporty; nebyl důvod rozdělovat platný kód ani report. |
| #92, #94–#95, #97–#102 | Přístupnost | Sloučit do přeloženého a otestovaného nástupce včetně aktivní feedback šablony. |
| #42–#43 | Vykreslování Bluetooth událostí v TUI | Zachovat platná DHCP/Wi-Fi data a neprázdný fallback služby. |
| #45–#46, #48–#49 | Síťové informace v TUI | Zachovat masku podsítě, nastavení a Tailscale do jednoho testovaného nástupce. |
| #47, #60–#61, #64, #67 | Helper příkazů v TUI | Vybrat bezpečnou variantu, otestovat argumenty a timeouty a vynechat reporty. |
| #54–#55, #65, #71–#73, #78–#91 bez #85 | Backend síťové informace | Sloučit přes service API, zachovat kompatibilitu a otestovat fallback. |
| #77, #81 | Enumerace procesů na RPi | Zachovat přesné procfs porovnání a testy; nemažte reporty. |
| #56 | Zjišťování stavu služby | Uzavřít, pokud se neprokáže ekvivalence `systemctl is-active`. |
| #58 | Vyhledání DLNA procesu | Zkontrolovat a otestovat procfs chování. |
| #62 | Aktualizace závislosti | Zachovat upgrade pipu v opraveném lockfile; jako nahrazené uzavřít až po sloučení nástupce. |
| #66 | Signalizace MPV procesu | Ověřit přesné nalezení procesu a bezpečný cíl signálu. |
| #68 | Detekce Kodi portu | Ověřit IPv4/IPv6 procfs parsing a místo volání. |
| #96 | PR-agent workflow | Uzavřen jako neplatný: duplicitní `runs-on`, nepřipnutá akce třetí strany, široká oprávnění pro zápis a předání tajného klíče. |

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

- 2026-10-24: Znovu jsem prověřil uzavřený PR #85 podle aktuálního diffu. Obsahuje pouze zástupné report tracky, runtime soubor režimu a smazání generovaných reportů; nezůstala žádná platná změna aplikace ani uživatelský report k zachování. Doplnil jsem cílené testy procfs guardu pro rodičovské PID, průměr CPU a graceful/nucené ukončení kandidáta, bez převzetí mazání reportů a opakovaných případů.
