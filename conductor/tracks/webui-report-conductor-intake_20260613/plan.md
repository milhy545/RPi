# Implementation Plan – WebUI Report → Conductor Intake

## Goal
Add a fully functional feedback system to the Dashboard WebUI that captures **bug reports** and **feature requests**, stores them locally, and creates a draft Conductor track for each submission.

## Tasks (ordered)
| # | Description | Owner | Status |
|---|-------------|-------|--------|
| 1 | Extend backend `/report` POST endpoint to accept JSON payload `{type, description, tab, ...}` (already present). | backend | ✅ Done |
| 2 | Add validation schema (type must be `bug` or `feature`; description non‑empty). | backend | ⏳ Pending |
| 3 | Persist reports to `reports/` directory (already in `_save_report`). | backend | ⏳ Pending |
| 4 | Create a background worker script (`tools/process_reports.py`) that scans `reports/` for new files, reads them, and generates a Conductor draft track using `conductor:newTrack` CLI. | backend | ⏳ Pending |
| 5 | Wire the worker to run as a systemd service (`report-processor.service`). | ops | ⏳ Pending |
| 6 | Update WebUI JavaScript to show a modal dialog with two buttons (Report bug / Request feature) and submit via `fetch('/report', {method:'POST', body: JSON.stringify(...)})`. | frontend | ⏳ Pending |
| 7 | Ensure UI shows a toast/notification confirming receipt and that processing may take a moment. | frontend | ⏳ Pending |
| 8 | Add unit test `tests/test_report_endpoint.py` (already exists) to verify file creation. | tests | ✅ Done |
| 9 | Add integration test `tests/integration/test_report_flow.py` that simulates a full POST and checks that a Conductor track appears after the worker runs (mock worker). | tests | ⏳ Pending |
|10 | Update CI to run the new tests (coverage). | CI | ⏳ Pending |
|11 | Document the feature in `README.md` (add a section *User Feedback & Conductor Integration*). | docs | ⏳ Pending |

## Acceptance Criteria
- When a user submits a bug/feature via WebUI, a JSON file appears in `reports/`.
- The background worker creates a new Conductor track under `conductor/tracks/` with a name like `report_<timestamp>_<type>`.
- The track contains a `spec.md` summarizing the user submission and a skeleton `plan.md` with a single task: “Investigate and resolve the report”.
- UI shows success toast and does not block the user.
- All new code is covered by tests and CI passes with ≥ 80 % coverage.
