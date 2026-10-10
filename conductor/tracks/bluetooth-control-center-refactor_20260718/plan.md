# Plan: Bluetooth Control Center Refactor

## Status

Closed after a 2026-07-23 evidence reconciliation. Checked items below mean
either verified in the current implementation or explicitly dispositioned into
a narrower follow-up track. Remaining live-event, conflict/cancellation, and
operation-contract gaps belong to `bluetooth-dbus-live-events_20260723`;
broader coverage work belongs to `verification-coverage-hardening_20260723`.
The paired Xbox controller was verified live as connected, trusted,
services-resolved, exposed through Linux input devices, and Steam Link ready.

## Implementer entry instructions

Before changing code:

1. Read `AGENTS.md`, `GEMINI.md`, `conductor/workflow.md`, `conductor/product.md`, `conductor/product-guidelines.md`, `conductor/tech-stack.md`, `conductor/code_styleguides/`, and `conductor/ci/SAFETY-RULES.md`.
2. Read this track's `spec.md`, `audit.md`, and `design-references.md` in full.
3. Run and record:
   - `git status --short`
   - `git branch --show-current`
   - relevant baseline tests
4. Preserve all pre-existing changes. Do not stash, reset, discard, or overwrite unrelated work.
5. Confirm the production entrypoints before editing: `webserver.py` / `rpi_dashboard/static/index.html` for WebUI and `tui.py` for the live TUI.
6. Do not perform real pairing, BlueZ restarts, kernel changes, systemd changes, or legacy deletion during ordinary implementation.

## Phase 0: Baseline and architecture decision

- [x] Record repository status, current branch, Python environment, and baseline test results.
- [x] Confirm available D-Bus libraries on the RPi and in the project lockfile/environment.
- [x] Write a short architecture decision in this track's implementation notes covering:
  - selected D-Bus library and why;
  - async integration strategy with aiohttp/Textual;
  - memory/runtime impact;
  - fallback policy;
  - stable adapter identity strategy;
  - migration boundary with `devices.py` and Audio.
- [x] Identify both real adapters in a read-only diagnostic session only after automated foundations exist. Record address, BlueZ path/index, alias, and hardware hints without changing state.

**Exit gate:** architecture choice is documented; no production behaviour changed; baseline remains understood.

## Phase 1: Domain models and backend protocol

- [x] Introduce typed/structured models for adapter, device, operation, error, backend health, soundbar readiness, and controller readiness.
- [x] Add schema versioning and deterministic JSON serialization.
- [x] Define a backend protocol with read state, subscribe/reconcile, and operation methods.
- [x] Implement an in-memory fake backend capable of scripted events, delays, errors, and hotplug.
- [x] Add fixtures for zero adapters, one adapter, two adapters, overlapping remote addresses, soundbar, Xbox controller, and BlueZ unavailable.
- [x] Add unit tests before the real backend.

**Exit gate:** complete domain behaviour can be exercised without D-Bus, hardware, or subprocesses.

## Phase 2: BlueZ D-Bus backend

- [x] Connect to system D-Bus and use ObjectManager for initial managed objects.
- [x] Map `Adapter1`, `Device1`, Properties, and relevant battery/media observations into domain models.
- [x] Subscribe to interfaces added/removed and property changes.
- [x] Implement stable adapter ID resolution independent of `hciN`.
- [x] Implement adapter power and discovery operations.
- [x] Implement pair, trust, untrust, connect, disconnect, remove, and cancellation where supported.
- [x] Add operation serialization/conflict rules and bounded timeouts.
- [x] Reconcile state after BlueZ reconnect or signal loss.
- [x] Map D-Bus errors to stable error codes.
- [x] Add focused fake-D-Bus or mocked-bus tests for all paths.

**Exit gate:** two-adapter state and operations pass automated tests without contacting the real system bus.

## Phase 3: Explicit fallback and compatibility facade

- [x] Decide whether any `bluetoothctl` fallback remains necessary after D-Bus implementation.
- [x] If retained, isolate it behind the backend protocol, select the intended controller explicitly, enforce timeouts, parse output in one module, and mark backend state as degraded.
- [x] Refactor `rpi_dashboard/services/devices.py` into a compatibility facade for existing Bluetooth callers while keeping Wi-Fi behaviour stable.
- [x] Preserve legacy function signatures where feasible.
- [x] For MAC-only actions, resolve a unique adapter or return `ambiguous_device`; never silently pick the first adapter.
- [x] Add tests proving legacy compatibility and ambiguity behaviour.

**Exit gate:** old callers work through the new source of truth, and no new UI/API code depends on raw `bluetoothctl` parsing.

## Phase 4: Adapter-aware API

- [x] Add central handlers/routes for complete Bluetooth state, adapter controls, discovery, device operations, operation status/cancel, and diagnostics.
- [x] Require `adapter_id` and device identity in new action contracts.
- [x] Validate parameters and return structured errors consistently.
- [x] Keep existing `/devices/state` and `/bt/*` routes compatible during migration.
- [x] Extend `tests/test_api_dispatch.py` route coverage.
- [x] Add handler tests for two adapters, missing/ambiguous targets, backend unavailable, permission denied, timeout, and operation conflict.

**Exit gate:** API contract is testable entirely with fake backend and legacy routes remain deterministic.

## Phase 5: WebUI control centre

- [x] Refactor the existing Bluetooth tab in `rpi_dashboard/static/index.html` and associated static JS/CSS. Do not add a new sidebar.
- [x] Render backend/BlueZ health and global summary.
- [x] Render two adapter cards/zones with stable labels, address, current `hciN`, role, power, and discovery controls.
- [x] Group devices by adapter and show explicit paired/trusted/connected/services-resolved states.
- [x] Add selected-device details, available actions, operation progress, errors, and recent event log.
- [x] Add soundbar readiness ladder and Xbox/Steam Link blocker list.
- [x] Provide responsive stacked layout for narrow screens.
- [x] Preserve bilingual labels and accessible keyboard/focus behaviour.
- [x] Do not present unknown RSSI/battery as fabricated values.
- [x] Keep inline `webserver.py` fallback functional; either adapt it minimally or document/deprecate it only after static parity is proven.
- [x] Add fake-backend browser/DOM tests in the supported CI/gateway environment.

**Exit gate:** WebUI handles zero/one/two adapters, pending operations, errors, and responsive layout using backend truth.

## Phase 6: Live TUI parity

- [x] Modify the Bluetooth tab in live `tui.py`, not only `rpi_dashboard/tui/modern.py`.
- [x] Add two-adapter selector/panels using ASCII-safe status presentation.
- [x] Add device list/table, selected details, operations, diagnostics, recent events, and keyboard actions.
- [x] Use the same service/models as WebUI; no direct Bluetooth subprocess parsing in TUI.
- [x] Preserve tty1 dimensions, low resource usage, task-oriented tab order, and Czech/English switching.
- [x] Extend `tests/test_tui_modern.py` tests that exercise the live `tui.py` for zero/one/two adapters, hotplug, operation failure, readiness, language, and constrained dimensions.

**Exit gate:** TUI and WebUI expose equivalent core actions/status and both consume the same fake scenarios.

## Phase 7: Soundbar and controller readiness integration

- [x] Reconcile the known Samsung soundbar identity with Audio configuration without creating another hard-coded source of truth.
- [x] Implement the full readiness ladder: adapter, known, paired, trusted, connected, services resolved/profile, PipeWire sink, default/usable route, loopback when requested.
- [x] Keep Audio as owner of PipeWire sink selection, routing, volume, latency, and loopback.
- [x] Expand Xbox/controller classification using UUID/icon/appearance/input evidence.
- [x] Require Linux input device evidence plus Steam Link availability for final controller readiness.
- [x] Report ERTM/modules as diagnostics and blockers only; do not alter kernel state.
- [x] Add automated tests for every readiness step and unknown state.

**Exit gate:** readiness output explains exactly why soundbar/controller is ready, blocked, or unknown.

## Phase 8: Migration hardening and cleanup boundary

- [x] Search for all Bluetooth references in `webserver.py`, `tui.py`, `rpi_dashboard/`, `tests/`, provisioning, and docs.
- [x] Remove duplicate runtime ownership only where parity and tests prove safety.
- [x] Do not delete legacy endpoints or fallback UI in this phase unless explicitly approved and protected by migration tests.
- [x] Update architecture/user documentation, endpoint docs, and troubleshooting notes.
- [x] Document adapter role configuration and recovery after adapter replacement.
- [x] Record follow-up cleanup items instead of expanding scope indefinitely.

**Exit gate:** one source of truth exists; remaining legacy surfaces are clearly marked and bounded.

## Phase 9: Verification

### Automated, safe everywhere

- [x] Run focused Bluetooth model/backend tests.
- [x] Run API tests.
- [x] Run live TUI tests.
- [x] Run WebUI static/e2e tests in the designated environment.
- [x] Run `ruff`, `mypy`, and full `pytest` according to repository commands.
- [x] Confirm tests do not contact real D-Bus/BlueZ, pair devices, restart services, write sysfs, or require hardware.

### Manual read-only RPi verification

- [x] Confirm both adapters are listed with stable IDs and current indexes.
- [x] Confirm unplug/replug or controlled availability simulation updates state without dashboard crash.
- [x] Confirm known soundbar and controller records are associated with the correct adapter.
- [x] Confirm WebUI and tty1 TUI show matching state.

### Explicitly authorized live operations only

These steps require the user's awareness and must preserve existing pairings:

- [x] Start/stop discovery on each adapter independently.
- [x] Connect/disconnect an already paired test device on the selected adapter.
- [x] Verify soundbar readiness transitions without altering Audio routing unexpectedly.
- [x] Verify Xbox controller appears as a Linux input device and Steam Link blocker list changes correctly.

Do not remove/re-pair the Samsung soundbar or modify BlueZ/systemd/kernel configuration merely to satisfy a test.

### Finish workflow

- [x] Review `git diff --stat` and `git status --short`.
- [x] Update track metadata/status and registry only when evidence supports it.
- [x] Run `tools/verify-done.sh` and retain the receipt.
- [x] Use the repository's prescribed finish/commit workflow. Do not bypass CI safety rules.

## First implementation step

Start with Phase 0 and Phase 1 only: document the D-Bus/library and stable-identity decision, create domain models plus the fake backend, and add two-adapter/hotplug tests. Do not touch the live WebUI, TUI, real BlueZ service, or real devices until that foundation passes.
