# Priority Track Reconciliation — 29 July 2026

## Scope

Reconcile the registry and metadata state of four priority Conductor tracks
that were incorrectly marked `[x]` (complete) in `tracks.md` at commit
`638caa493fa5f5491f0be0fd5f5c0012920fe69c`. This audit was performed in a
dedicated git worktree on branch `recovery/conductor-reconciliation_20260729`.

## Infrastructure

- **Worktree:** `/home/milhy777/Develop/RPi-recovery-conductor`
- **Branch:** `recovery/conductor-reconciliation_20260729`
- **Base commit:** `638caa493fa5f5491f0be0fd5f5c0012920fe69c`
- **Original checkout:** `/home/milhy777/Develop/RPi` (dirty: `AGENTS.md`,
  `AGENTS.cz.md`, `docs/audits/` — all controller-originated, untouched)
- **Authoritative tools:** `conductor.py status` (exit 0),
  `conductor.py validate` (exit 1, INVALID)

## Receipt Status

No completion receipt exists for HEAD `638caa4` in either checkout. The
original checkout contains 96 receipt files for other SHAs; the worktree
carries only `.gitkeep` because receipts are gitignored runtime artifacts.
Absence of a receipt for `638caa4` means the CI pipeline was never completed
for this commit, confirming it is unverified partial work.

## Priority Track Classifications

### 1. unified-ui-ux-refactor_20260728

| Field | Prior state | Current state |
|---|---|---|
| Registry | `[x]` done | **`[ ]` reopened** |
| Metadata | missing | **`active`** (created) |
| Spec | missing | **created** (spec.md + spec.cz.md) |
| Plan | 0/24 checked, stale paths | **rewritten** (0 checked, 35 plan items + 10 acceptance criteria = 45 total) |

**Evidence:** `theme.css` defines tokens; `main.css` (70 `var(--`) and
`themes.css` (78 `var(--`) consume them. However: Bluetooth duplicate
global surfaces remain; status bar DOM IDs mismatch JS selectors; `updBr()`
throws null-reference every 3 seconds; Terminal tab is blank; TUI parity
not started. Plan rewritten to reflect actual file paths
(`main.css`/`themes.css`/`responsive.css`/`audio.css`, not `style.css`),
correct endpoint (`/system/hw-stats` not `/system/stats`), TUI reading
from shared `rpi_dashboard.services.system` module, Terminal shell with
integration contract (no WebSocket until terminal/auth tracks deliver),
Basic/Expert/Admin boundary requiring server-side auth, Playwright
evidence at four viewports, and TUI verification via Textual `run_test()`
pytest plus manual `/dev/tty1` on RPi. CSS acceptance uses semantic checks (token
categories, no unjustified duplicates, screenshot regression), not
brittle `var(--` count thresholds.

**Plan item counts (after rewrite):**
- Phase 1 (CSS Token Audit): 4 tasks + 1 verify = 5
- Phase 2 (Remove BT Duplicates): 3 tasks + 1 verify = 4
- Phase 3 (Status Bar Telemetry): 3 tasks + 1 verify = 4
- Phase 4 (Console Errors): 2 tasks + 1 verify = 3
- Phase 5 (Terminal Shell): 2 tasks + 1 verify = 3
- Phase 6 (Responsive Verification): 4 tasks + 2 verify = 6
- Phase 7 (TUI Parity): 4 tasks + 1 verify = 5
- Phase 8 (Full Verification): 4 tasks + 1 verify = 5
- **Subtotal (tasks + verify): 35**
- Acceptance Criteria: 10
- **Total unchecked checklist items: 45**

**Action:** Reopened. Files created: `spec.md`, `spec.cz.md`, `metadata.json`.
`plan.md` and `plan.cz.md` rewritten. No tasks checked.

### 2. audio-fullstack-refactor_20260725

| Field | Prior state | Current state |
|---|---|---|
| Registry | `[x]` done | **`[ ]` reopened** |
| Metadata | `active` | `active` (unchanged) |
| Spec | present | present (unchanged) |
| Plan | 0/43 checked | **not modified** (per scope) |

**Evidence:** `rpi_dashboard/services/audio/` exists with only
`__init__.py` containing the full monolithic audio code (~1054 lines).
No sub-modules (`state.py`, `mixer.py`, `matrix.py`, `multi_output.py`,
`keepalive.py`, `profiles.py`, `latency.py`) exist. `set_global_master_volume()`
and BT AVRCP sync are present in `__init__.py`. TUI `AudioFlowDiagram`
not found. Plan checkboxes left untouched per scope restriction.

**Action:** Reopened. Metadata kept as `active`. Plan not modified.

### 3. backend-modularization-completion_20260723

| Field | Prior state | Current state |
|---|---|---|
| Registry | `[x]` done | **`[ ]` reopened** |
| Metadata | `active` | `active` (unchanged) |
| Spec | present | present (unchanged) |
| Plan | 0/33 checked | **not modified** (per scope) |

**Evidence:** `webserver.py` is 3088 lines. API extraction to
`rpi_dashboard/api/` is real (routes.py, handlers.py exist). E2E
test infrastructure present (`tests/e2e/` with 4 Playwright test
files + package.json). Phase 4 visual redesign, Phase 5 legacy
retirement, and Phase 6 runtime verification show no plan completion.
Plan checkboxes left untouched per scope restriction.

**Action:** Reopened. Metadata kept as `active`. Plan not modified.

### 4. verification-coverage-hardening_20260723

| Field | Prior state | Current state |
|---|---|---|
| Registry | `[x]` done | **`[ ]` reopened** |
| Metadata | `planned` | `planned` (unchanged) |
| Spec | present | present (unchanged) |
| Plan | 0/32 checked | **not modified** (per scope) |

**Evidence:** Baseline captured (`baseline_20260727_133715/`).
`baseline_reconciliation.md` and `log-audit.md` exist.
`tests/test_transport_disconnect.py` and `tests/test_shutdown_behavior.py`
do not exist. Phases 2-5 are HW-ONLY. Plan checkboxes left untouched
per scope restriction.

**Action:** Reopened. Metadata kept as `planned`. Plan not modified.

## Deferred Historical Inconsistencies

The following tracks have registry/metadata mismatches but are outside the
scope of this reconciliation. They require separate historical review to
determine supersession, absorption, or independent status:

- `alexa-dlna-audio-routing_20260613` (done/planned)
- `devices-tab-hardening_20260613` (done/planned)
- `dlna-rendering_20260611` (done/planned)
- `playback-resume-memory_20260613` (done/planned)
- `terminal-hw-stats_20260613` (done/planned)
- `webui-report-conductor-intake_20260613` (done/planned)
- `android-share-app_20260613` (done/planned) — specification deliverable
- `milhy-pc-firewall_20260611` (done/implementation)
- `smart-home-integrations_20260613` (done/planned)
- `mpv-eof-runtime-return_20260723` (done/done) — strong implementation
  evidence, verification/bookkeeping incomplete
- `mpv-optimization_20260627` (done/done) — pending review
- `modular_test_ci_config_audio_fix_20260626` (unregistered/pending)
- 6x `report_*` tracks (done/missing metadata)
- `audio-multimixer-webui_20260725` (absorbed into audio-fullstack)

## Files Changed

| File | Action |
|---|---|
| `conductor/tracks.md` | 4 entries changed from `[x]` to `[ ]` |
| `conductor/tracks/unified-ui-ux-refactor_20260728/spec.md` | Created |
| `conductor/tracks/unified-ui-ux-refactor_20260728/spec.cz.md` | Created |
| `conductor/tracks/unified-ui-ux-refactor_20260728/metadata.json` | Created |
| `conductor/tracks/unified-ui-ux-refactor_20260728/plan.md` | Rewritten |
| `conductor/tracks/unified-ui-ux-refactor_20260728/plan.cz.md` | Created |
| `conductor/audit/priority-track-reconciliation_20260729.md` | This file |
| `conductor/audit/priority-track-reconciliation_20260729.cz.md` | Czech translation |

## Verification

- `git diff --check`: clean (no whitespace errors)
- `python3 -m json.tool metadata.json`: valid JSON
- `rg '[\x{4E00}-\x{9FFF}]'` across `.cz.md` files: no matches
- `conductor.py validate`: exit 1 (INVALID) — 8 deferred errors in
  historical tracks; none of the 4 priority tracks appear in errors
- Original checkout status: unchanged (`M AGENTS.md`, `?? AGENTS.cz.md`,
  `?? docs/audits/`)
