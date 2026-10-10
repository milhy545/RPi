# Implementační plán: Bezpečná validační pipeline pro RPi / Milhy-PC / Jules

## Úkoly a Milníky

- [x] **Fáze 1: Nastavení Conductor Tracku**
  - Vytvořit metadata tracku, specifikaci a implementační plán.
  - Zaregistrovat track v `conductor/tracks.md`.

- [x] **Fáze 2: Implementace RPi Guardu a Engine Pipeline**
  - Implementovat modul `rpi_dashboard.ci.rpi_guard` s přesnou detekcí procesů, atribucí vlastního CPU, bránou zdrojů, frontováním/backoffem a detekcí přehrávání uprostřed běhu.
  - Implementovat `rpi_dashboard.ci.staging` pro izolovaný staging kandidáta, odmítnutí nečistého checkoutu a rollback.
  - Implementovat `rpi_dashboard.ci.evidence` pro vlastnictví zámku `flock`, agregaci důkazů a atomickou validaci účtenek.

- [x] **Fáze 3: Integrace profilů a skriptů**
  - [x] Aktualizovat `tools/run-ci.sh` pro implementaci explicitních profilů (`rpi-focused`, `milhy-full`, `rpi-candidate`, `github-safe`) a opravu pytest driftu.
  - [x] Aktualizovat výchozí profil `tools/ci-agent.sh` na `milhy-full`.
  - [x] Přidat E2E/evidence brány v `ci-agent.sh` vyžadující SHA-vázaný E2E manifest a přesnou-SHA RPi účtenku před push.
  - [x] Opravit `prepare_candidate` na hlasité selhání při nečistém worktree (odstraněn tichý git-stash).
  - [x] Aktualizovat `tools/finish-track.sh` pro použití profilu `milhy-full`.
  - [x] Opravit obcházení tvrdých bran: zachovat surový exit status Playwrightu, vyžadovat TARGET_URL, selhat milhy-full při chybějícím Playwrightu.
  - [x] Vyřešit CI_PROFILE jednorázově přes RESOLVED_CI_PROFILE pro zamezení unbound var pod set -u.
  - [ ] **ČEKÁ**: Živý E2E/HW/receipt rollout důkaz musí existovat před označením za dokončené.

- [x] **Fáze 4: Šablona RPi Core Rules & Idempotentní Instalátor**
  - Přidat `.agents/core-rules/SKILL.rpi.template.md` s hardwarovými limity a vloženými pravidly pipeline pro CodeX skill systém.
  - Vytvořit `tools/install-rpi-core-rules.sh` s razítkovanou zálohou, řešením symlinků, validací hranic (`.agents/skills` a `.codex/skills`), atomickou instalací a rollbackem při selhání.
  - Cílí na `~/.agents/skills/core-rules/SKILL.md` nebo `~/.codex/skills/core-rules/SKILL.md`.

- [x] **Fáze 5: Sjednocení Dokumentace**
  - Aktualizovat `AGENTS.md` (britská angličtina) a `AGENTS.cz.md` (čeština).
  - Aktualizovat `conductor/ci/SAFETY-RULES.md`, `conductor/workflow.md` a vytvořit odpovídající `conductor/workflow.cz.md`.

- [x] **Fáze 6: Komplexní Sada Testů a Verifikace**
  - [x] Vytvořit `tests/test_rpi_safe_ci_pipeline.py` testující směrování hostitele/profilu, přesnou detekci procesů, atribuci CPU, frontování, abort přehrávání uprostřed běhu, odmítnutí nečistoty, nesoulad SHA, souběh zámků, rollback a zákazy push/browseru na RPi.
  - [x] Přidat deterministické testy dokazující, že push je nemožný při absenci/zastaralosti E2E nebo přesné-SHA RPi účtenky.
  - [x] Přidat testy dokazující, že nečistý stav zůstává nedotčen bez stashingu.
  - [x] Přidat testy ignoračního chování .gitignore a podpory NO_PUSH režimu.
  - [ ] **ČEKÁ**: Živý E2E/HW/receipt rollout důkaz musí existovat před označením za dokončené.
  - Spustit kontroly shell syntaktiky, pytest suite, Ruff, mypy, Conductor validaci a `git diff --check`.
