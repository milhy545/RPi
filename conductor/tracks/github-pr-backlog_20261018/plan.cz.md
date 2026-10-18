# Plán implementace: Vyřešení fronty GitHub PR

## Fáze 1 — Zastavit neprověřenou automatizaci

- [x] Vypnout původní bezpodmínečný auto-merge workflow.
- [x] Vypnout všechny požadavky na auto-merge aktivní v počátečním seznamu PR.
- [x] Přidat podmínku štítku `merge-approved`, cestu pro zrušení po odebrání štítku a cílené testy workflow.
- [ ] Workflow znovu zapnout až po nasazení nové verze na `main`.
- [x] Opravit bránu commitů a receiptů: zakázat amend commity, odmítat runtime artefakty a jasně selhat při chybějícím receipt.
- [x] Přizpůsobit GitHub CI politice lokálních Actions přes přímý Git fetch a lokální skripty; zachovat povinný check `verify-done` a importovat receipt přesných main commitů z metadat úspěšného běhu.

## Fáze 2 — Zaznamenat a roztřídit frontu

- [x] Zachytit počáteční seznam otevřených PR a aktuální SHA GitHub `main`.
- [x] Zachovat čtyři lokální commity a vytvořit čistý izolovaný worktree z GitHub `main`.
- [ ] Zaznamenat rozhodnutí pro každé původní PR a před uzavřením nebo sloučením jej znovu ověřit.
- [ ] Po závěrečné kontrole diffu uzavřít PR z jiných projektů jako `invalid` s jasným vysvětlením.
- [ ] Duplicitní PR označit jako `duplicate` až po uvedení ověřeného nástupce.

## Fáze 3 — Sloučit změny a ověřit kandidáty

- [ ] Rozdělit PR #85 na konkrétní změny kódu a reporty; zachovat platné uživatelské reporty a vynechat runtime artefakty.
- [ ] Sloučit změny přístupnosti včetně přeložených přístupných názvů a ovládání zavření formuláře zpětné vazby.
- [ ] Sloučit změny síťových informací v TUI včetně DHCP leases a náhradní hodnoty `RPi-service`.
- [ ] Sloučit službu pro síťové informace do jediné implementace a otestovat adresy, routy, rozhraní i fallback.
- [ ] Sloučit TUI helper pro příkazy a procfs detekci procesů; nepřidávat generované reporty.
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
| #93 | Nesouvisející aplikační/repozitářové soubory | Po poslední kontrole diffu uzavřít jako neplatné. |
| #85 | Velký sync balík, změny aplikace a Conductor reporty | Rozdělit; prověřit Ruff a review; zachovat platné reporty. |
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
| #96 | PR-agent workflow | Prověřit YAML, připnutí akcí, rozsah tokenu a tajné údaje; použít zabezpečenou náhradu nebo uzavřít jako nahrazené. |

## Záznam změn

- 2026-10-18: Zaznamenán seznam 48 PR, vypnut bezpodmínečný auto-merge a vytvořen izolovaný worktree z GitHub `main` na `4b7caeed68c2378507d81bba7136fe51e5f64faa`.
- 2026-10-18: Implementována brána auto-merge s explicitním štítkem a zahájena oprava lokálního kontraktu commitů/receiptů; testy a CI ještě čekají.
- 2026-10-18: Přidány regresní testy helperu commitů, chybějícího/platného receipt a schválení/zrušení workflow; 21 cílených testů, ShellCheck, shell syntax i parsování YAML prochází. Plné lokální CI ještě čeká.
- 2026-10-18: První plný běh odhalil, že `pip-audit` kontroloval globální balíky hostu. CI nyní před auditem synchronizuje zamčené prostředí projektu. V locku bylo 6 nálezů v balících `multidict 6.7.1`, `pip 26.1.2` a `urllib3 2.7.0`; aktualizováno na `6.9.1`, `26.2.1` a `2.8.0`. `pip-audit` v prostředí projektu nyní hlásí nula známých zranitelností. Opraveny dva testy závislé na Bluetooth adaptéru hostitele a test receipt kontraktu. Plná CI se opakuje.
- 2026-10-18: GitHub API potvrzuje, že repozitář povoluje pouze lokální workflow/akce; dosavadní CI volalo zakázané marketplace akce a končilo před vytvořením jobů. Tyto kroky nahrazeny přímým stažením Git refu a lokálním CI skriptem, povinný check `verify-done` zůstal zachován. Odstraněna závislost na artifact akcích, handoff nově importuje receipt z úspěšného běhu pro přesný `main` commit a chrání lokální adresáře receiptů/reportů před mazáním při synchronizaci.
