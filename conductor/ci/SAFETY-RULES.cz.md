# Bezpečnostní pravidla agentů — CI gateway

## ZÁVAZNÁ PRAVIDLA

### Pravidlo 1: Nikdy netvrdit „hotovo“ bez receipt

Agent NESMÍ říct „hotovo“, „done“, „finished“ ani „completed“, dokud `tools/verify-done.sh` neskončí s kódem 0.

```bash
tools/verify-done.sh
# Při návratovém kódu 1 agent NESMÍ tvrdit, že je práce dokončená.
```

### Pravidlo 2: Necommitovat bez úspěšného CI

Lokální bránu commitu vynucuje `tools/finish-track.sh`:

- Zachová bezpečnostní snapshot a před přípravou commitu spustí vybraný CI profil.
- Při neúspěšném CI nebo při staged runtime artefaktech commit nevytvoří.
- Vytvoří nový commit; nikdy neupravuje současný commit.
- Agent nesmí tuto bránu obejít přímým spuštěním `git commit`.
- Skript nepushuje ani nevytváří completion receipt. Push a merge provádí gateway Milhy-PC; důkaz dokončení pro přesný `main` dodává GitHub Actions.

### Pravidlo 3: Nikdy nevynechat receipt

Completion receipt pro přesný push do `main` vytváří pouze úspěšné GitHub Actions CI:

```text
conductor/ci/receipts/{sha}-{timestamp}-github-main.json
```

Bez receipt pro přesné SHA nebo totožný Git strom je pipeline nedokončená a agent nesmí tvrdit, že je hotovo. Shoda podle stromu je povolena proto, že GitHub rebase může změnit metadata commitu. Receipt z kontroly RPi kandidáta je pouze důkaz hardwarové brány a nenahrazuje completion receipt.

Pokud se změnil základní commit a tím i strom, `verify-done.sh` může vytvořit nový lokální receipt pouze z úspěšného GitHub Actions běhu workflow `ci.yml` typu push pro přesné SHA větve `main`. Workflow používá pouze lokální kroky a nenahrává artefakty.

### Pravidlo 4: Nikdy neignorovat chyby

Pokud selže některý z těchto kroků, agent se musí zastavit a oznámit přesnou chybu:

- návratový kód `tools/run-ci.sh` není 0,
- `git commit` selže,
- `rsync` na Milhy-PC selže,
- Milhy-PC CI agent selže,
- selže povinná GitHub Actions kontrola PR nebo `main`,
- `tools/verify-done.sh` neskončí s kódem 0.

### Pravidlo 5: Nikdy necommitovat runtime artefakty

Zakázané soubory v commitu:

- `*.pyc`, `__pycache__/`,
- `.forensics/`,
- `playback-memory.json`, `yt-cookies.txt`,
- `conductor/ci/reports/`, `conductor/ci/receipts/`,
- `.venv/`.

### Pravidlo 6: Z RPi nikdy nepushovat

RPi NESMÍ spouštět `git push`. Veškeré GitHub pushe provádí gateway Milhy-PC.

### Pravidlo 7: Bezpečnostní snapshot před každým commitem

`tools/finish-track.sh` před CI vytvoří zálohu:

```text
pre-finish-track-{timestamp}
```

Když se něco pokazí, lze snapshot obnovit. Skript ho po obnovení změn ponechá v seznamu stashů.

### Pravidlo 8: Výslovné CI profily a směrování podle hostu

- `rpi-focused`: cílené testy a syntaxe pro RPi; bez plné sady pytest a browser testů.
- `milhy-full`: plné pytest, Ruff, mypy, bezpečnostní kontroly a vzdálené browser E2E na Milhy-PC.
- `rpi-candidate`: neinvazivní hardwarová kontrola izolovaného kandidáta na RPi.
- `github-safe`: plné lokální statické a unit kontroly pro změny, jejichž zbývající povinné kontroly provede GitHub Actions; nevyžaduje hardware ani vzdálený browser.

### Pravidlo 9: Neinvazivní hardwarová brána RPi

- Přesné párování procesů `mpv`, `steamlink`, `moonlight` a TUI režimu; vyloučit skripty, které obsahují jen podobný text, například `keys2mpv.py`.
- Pokud trvalé vytížení CPU uživatelem překročí 20 %, kandidátní kontrola čeká. CPU samotného CI runneru se odečítá, aby nevznikl deadlock.
- Pokud během kontroly začne přehrávání, kandidátní procesy se okamžitě ukončí a kontrola se zařadí zpět.
- Browsery (Playwright/Chrome/Firefox) jsou na RPi přísně zakázané.

### Pravidlo 10: Izolovaný worktree kandidáta a vlastnictví flock

- Kód kandidáta se připravuje v izolovaném worktree mimo živý checkout.
- `rsync --delete` je zakázán, pokud je živý checkout nebo cílový worktree špinavý.
- Pipeline používá zámek `flock` (`/tmp/rpi-ci-pipeline.lock`), aby neběžela souběžně.

## OVĚŘOVACÍ POSTUP

```text
Agent připraví změny ve feature větvi
  ↓
tools/finish-track.sh "zpráva commitu"
  ↓
  ├── vytvoří se bezpečnostní snapshot
  ├── proběhne vybraný lokální CI profil
  ├── zkontrolují se runtime artefakty
  └── vytvoří se nový commit (bez amend, push ani completion receipt)
  ↓
Gateway Milhy-PC pushne kandidátní větev až po požadovaných důkazech
  ↓
Proběhnou povinné kontroly a review PR; maintainer sloučí přes ochranu větve
  ↓
GitHub Actions vytvoří receipt/report pro přesné SHA větve main
  ↓
tools/verify-done.sh
  ↓
  ├── receipt odpovídá SHA nebo totožnému stromu?
  ├── stav receipt je done?
  ├── existuje CI report?
  ├── pracovní strom je čistý?
  ├── zrcadlo Milhy-PC odpovídá?
  ├── commit je na origin?
  ├── poslední commit neobsahuje runtime artefakty?
  └── nejsou přítomné zakázané řetězce?
  ↓
KÓD 0 = agent smí tvrdit „hotovo“
KÓD 1 = agent NESMÍ tvrdit „hotovo“
```

## TABULKA SELHÁNÍ

| Selhání | Commit vytvořen? | Push nebo merge? | Postup agenta |
|---|---|---|---|
| Selže lokální CI nebo kontrola artefaktů | Ne | Ne | Opravit změnu a zopakovat CI; bezpečnostní snapshot zachovat. |
| Selže `git commit` | Ne | Ne | Prověřit staged soubory a zachovat pracovní strom. |
| Selže RPi kandidát nebo vzdálené E2E | Může zůstat na feature větvi | Bez push | Uvést přesnou překážku; kandidáta nepushovat. |
| Selže GitHub kontrola PR nebo review | Může zůstat na feature větvi | Bez merge | Opravit nález a počkat na opakované kontroly. |
| Selže CI pro přesné `main` SHA nebo kontrola receipt | Commit na main zůstává | Bez tvrzení o dokončení | Prověřit přesné SHA a Actions artefakt; CI opravit nebo zopakovat. |
| Vše projde a `verify-done.sh` skončí s kódem 0 | Ano | Ano | Agent smí tvrdit, že práce je hotová. |

## ZÁKAZ NEPRAVDIVÝCH TVRZENÍ

Agent NESMÍ:

- tvrdit „CI prošlo“ bez uvedení cesty k reportu,
- tvrdit „commit vytvořen“ bez uvedení SHA,
- tvrdit „hotovo“ bez úspěšného `tools/verify-done.sh`,
- tvrdit „pushnuto na GitHub“ bez odkazu na GitHub Actions běh,
- ignorovat výstup na stderr,
- pokračovat po chybě skriptu s `set -e`,
- použít `|| true` k potlačení chyby v kritické cestě.
