# Implementation Plan: Bluetooth Topology Accessible Controls

- [x] Add Czech and English accessible-name keys for the three topology controls.
- [x] Keep their visible glyphs and actions intact.
- [x] Extend the Chromium regression flow to switch languages and check names and glyphs.
- [x] Add focused static coverage for the translation keys and attributes.
- [x] Run focused static tests (`13 passed`) and the Chromium language-switch check with `/usr/bin/chromium`.
- [x] Run `CI_PROFILE=github-safe tools/run-ci.sh --profile github-safe`; all checks passed, including the full pytest suite, Ruff, mypy, Bandit, and pip-audit.
- [ ] Create a PR against the current `main` and wait for required checks and Kilo review.
- [ ] Merge only after the PR is conflict-free, approved, and required checks pass.

## Verification Record

- 2026-10-24: `uv run python -m pytest -q tests/test_static_assets.py` — 13 passed.
- 2026-10-24: `CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium node tests/e2e/a11y_i18n_test.mjs` — passed for Czech and English labels while preserving all three button glyphs.
- 2026-10-24: `CI_PROFILE=github-safe tools/run-ci.sh --profile github-safe` — passed; report `conductor/ci/reports/857cd80-20261024-065020.md`.
