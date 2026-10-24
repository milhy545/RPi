# Implementační plán: Přístupné ovládání Bluetooth topologie

- [x] Přidat české a anglické překlady přístupných názvů tří ovládacích prvků topologie.
- [x] Zachovat jejich viditelné znaky a akce.
- [x] Rozšířit regresní běh Chromia o přepnutí jazyka a kontrolu názvů i znaků.
- [x] Přidat cílené statické pokrytí překladových klíčů a atributů.
- [x] Spustit cílené statické testy (`13 passed`) a kontrolu přepínání jazyka v Chromiu `/usr/bin/chromium`.
- [x] Spustit `CI_PROFILE=github-safe tools/run-ci.sh --profile github-safe`; prošly všechny kontroly včetně úplné sady pytest, Ruffu, mypy, Banditu a pip-auditu.
- [ ] Vytvořit PR proti aktuálnímu `main` a počkat na povinné kontroly a Kilo review.
- [ ] Sloučit až po odstranění konfliktů a úspěchu povinných kontrol i review.

## Záznam ověření

- 2026-10-24: `uv run python -m pytest -q tests/test_static_assets.py` — 13 testů úspěšně.
- 2026-10-24: `CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium node tests/e2e/a11y_i18n_test.mjs` — čeština i angličtina prošly a všechny tři znaky tlačítek zůstaly zachované.
- 2026-10-24: `CI_PROFILE=github-safe tools/run-ci.sh --profile github-safe` — úspěšně; report `conductor/ci/reports/857cd80-20261024-065020.md`.
