# CI pipeline RPi Dashboardu

## 1. Práce na Conductor tracku

Pracuj na pojmenované feature větvi nebo v izolovaném worktree. Před úpravami přečti specifikaci a plán tracku a zachovej nesouvisející práci. Jediným hostem, který smí pushovat nebo slučovat na GitHubu, je Milhy-PC. Produkční checkout na RPi nesmí pushovat na GitHub.

## 2. Vytvoření commitu pomocí `tools/finish-track.sh`

```bash
tools/finish-track.sh "fix(webui): preserve accessible modal labels"
```

Skript vyžaduje zprávu commitu, pojmenovanou větev a čekající změny. Vytvoří zachovaný stash `pre-finish-track-*`, obnoví přesný stav indexu i pracovního stromu, spustí vybraný profil `tools/run-ci.sh`, odmítne runtime artefakty a vytvoří nový commit až po úspěšné CI. Nikdy neupravuje současný commit, nepushuje větev ani nevytváří completion receipt.

Výchozí profil je `rpi-focused` na RPi a `milhy-full` na Milhy-PC. Pro změny, jejichž ověření plně pokrývá CI repozitáře a které nepotřebují připraveného RPi kandidáta ani vzdálené browser testy, lze nastavit `CI_PROFILE=github-safe`. Volba profilu neruší povinné kontroly GitHubu ani závěrečný receipt.

Pokud CI selže, commit nevznikne. Pracovní strom i bezpečnostní snapshot zůstávají k dispozici pro opravu.

## 3. Ověření a sloučení pull requestu

Feature větve pushuj pouze z Milhy-PC. Změny ovlivňující runtime musí před gateway pushem získat požadované důkazy z připraveného RPi kandidáta a vzdáleného E2E. Otevři nebo aktualizuj pull request a počkej na povinné kontroly `verify-done` a review. Slévej vždy jen jeden prověřený PR a používej rebase podle pravidel repozitáře.

Politika GitHub Actions v repozitáři povoluje pouze lokální workflow. CI stahuje testovaný ref pomocí Gitu a spouští skripty repozitáře; nesmí používat marketplace akce.

Automatické sloučení rebase je povolené pouze po přidání štítku `merge-approved` maintainerem. Odebrání štítku nebo změna PR na draft zruší čekající auto-merge.

## 4. Completion receipt pro přesné SHA

GitHub Actions CI vytváří dočasný receipt a report během ověřování každého běhu. Pro dokončení je nutný úspěšný běh `ci.yml` po pushi přesného commitu `main`. `tools/verify-done.sh` ověří současný commit a strom, podle potřeby vytvoří lokální receipt a report z odpovídajícího úspěšného běhu push CI na `main` a zkontroluje pracovní strom i stav gateway. Workflow artefakty nenahrává.

Spusť ověření v čistém checkoutu přesného commitu `main`:

```bash
tools/verify-done.sh
```

Chybějící nebo neplatný receipt znamená neúspěch. Samotný lokální commit nebo zelená kontrola pull requestu není completion receipt pro `main`.

## 5. Směrování podle hostu a ochrana dat

- **RPi:** pro lehké kontroly použij `rpi-focused`; `rpi-candidate` použij pouze s guardem a neinvazivními kandidátními testy. Na RPi nikdy nespouštěj browser automatizaci.
- **Milhy-PC:** pro plné lokální ověření použij `milhy-full`; `github-safe` použij pro změny, jejichž povinné kontroly běží v GitHub Actions a nepotřebují hardware ani vzdálený browser.
- **GitHub:** dodržuj povinné kontroly PR a merge queue; neobcházej ochranu větví.
- **Uživatelská data:** zachovej reporty a rozpracované změny. Do commitu nedávej CI reporty, receipty, cache, tajné údaje, stav přehrávání ani generované E2E výsledky.
- **Bezpečnost kandidáta:** kód kandidáta připrav v izolovaném worktree. Nepřepisuj špinavý produkční checkout, nepoužívej `rsync --delete` nad neznámým stavem a nepřerušuj přehrávání, hraní, TUI, audio, Bluetooth, CEC ani systémové služby.

## 6. Řešení selhání

| Selhání | Commit | Push nebo merge | Požadovaný postup |
|---|---|---|---|
| Selže lokální CI | Nevznikne | Ne | Oprav změnu a znovu spusť vybraný profil. |
| Je staged runtime artefakt | Nevznikne | Ne | Vyřaď ho z commitu, ale nemaž uživatelská data. |
| Selže RPi guard nebo vzdálené E2E | Může existovat na feature větvi | Bez gateway push/merge | Zachovej kandidáta a uveď přesnou selhávající bránu důkazů. |
| Selže povinná kontrola GitHubu nebo review | Může existovat na feature větvi | Bez merge | Vyřeš nález a počkej na nové kontroly. |
| Chybí nebo je neplatný receipt přesného main SHA | Commit na main zůstane | Bez tvrzení o dokončení | Prověř přesný Actions běh; importuj pouze úspěšný push CI pro toto SHA na main. |

## 7. Přehled souborů

- `tools/finish-track.sh` — bezpečnostní snapshot, lokální CI, kontrola artefaktů a commit bez amend.
- `tools/run-ci.sh` — lokální validace podle profilu.
- `tools/ci-agent.sh` — gateway kontroly Milhy-PC a push podmíněný důkazy.
- `tools/trigger-ci-handoff.sh` — handoff z RPi na Milhy-PC a import receiptu pro přesné main SHA.
- `tools/verify-done.sh` — povinná kontrola přesného receipt a pracovního stromu.
- `tools/receipt_lookup.py` a `tools/import_main_receipt.py` — hledání receiptů a import úspěšného běhu přesného main SHA.
- `.github/workflows/ci.yml` — CI pro pull requesty a hlavní větev.
- `.github/workflows/auto-merge.yml` — explicitní auto-merge brána se štítkem `merge-approved`.
- `conductor/ci/SAFETY-RULES.md` — závazná pravidla běhu a důkazů.
