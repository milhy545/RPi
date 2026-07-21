# Plan: Bluetooth Control Center Refactor

## Status

Planned. No production implementation is part of the track-authoring commit.

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

- [ ] Record repository status, current branch, Python environment, and baseline test results.
- [ ] Confirm available D-Bus libraries on the RPi and in the project lockfile/environment.
- [ ] Write a short architecture decision in this track's implementation notes covering:
  - selected D-Bus library and why;
  - async integration strategy with aiohttp/Textual;
  - memory/runtime impact;
  - fallback policy;
  - stable adapter identity strategy;
  - migration boundary with `devices.py` and Audio.
- [ ] Identify both real adapters in a read-only diagnostic session only after automated foundations exist. Record address, BlueZ path/index, alias, and hardware hints without changing state.

**Exit gate:** architecture choice is documented; no production behaviour changed; baseline remains understood.

## Phase 1: Domain models and backend protocol

- [ ] Introduce typed/structured models for adapter, device, operation, error, backend health, soundbar readiness, and controller readiness.
- [ ] Add schema versioning and deterministic JSON serialization.
- [ ] Define a backend protocol with read state, subscribe/reconcile, and operation methods.
- [ ] Implement an in-memory fake backend capable of scripted events, delays, errors, and hotplug.
- [ ] Add fixtures for zero adapters, one adapter, two adapters, overlapping remote addresses, soundbar, Xbox controller, and BlueZ unavailable.
- [ ] Add unit tests before the real backend.

**Exit gate:** complete domain behaviour can be exercised without D-Bus, hardware, or subprocesses.

## Phase 2: BlueZ D-Bus backend

- [ ] Connect to system D-Bus and use ObjectManager for initial managed objects.
- [ ] Map `Adapter1`, `Device1`, Properties, and relevant battery/media observations into domain models.
- [ ] Subscribe to interfaces added/removed and property changes.
- [ ] Implement stable adapter ID resolution independent of `hciN`.
- [ ] Implement adapter power and discovery operations.
- [ ] Implement pair, trust, untrust, connect, disconnect, remove, and cancellation where supported.
- [ ] Add operation serialization/conflict rules and bounded timeouts.
- [ ] Reconcile state after BlueZ reconnect or signal loss.
- [ ] Map D-Bus errors to stable error codes.
- [ ] Add focused fake-D-Bus or mocked-bus tests for all paths.

**Exit gate:** two-adapter state and operations pass automated tests without contacting the real system bus.

## Phase 3: Explicit fallback and compatibility facade

- [ ] Decide whether any `bluetoothctl` fallback remains necessary after D-Bus implementation.
- [ ] If retained, isolate it behind the backend protocol, select the intended controller explicitly, enforce timeouts, parse output in one module, and mark backend state as degraded.
- [ ] Refactor `rpi_dashboard/services/devices.py` into a compatibility facade for existing Bluetooth callers while keeping Wi-Fi behaviour stable.
- [ ] Preserve legacy function signatures where feasible.
- [ ] For MAC-only actions, resolve a unique adapter or return `ambiguous_device`; never silently pick the first adapter.
- [ ] Add tests proving legacy compatibility and ambiguity behaviour.

**Exit gate:** old callers work through the new source of truth, and no new UI/API code depends on raw `bluetoothctl` parsing.

## Phase 4: Adapter-aware API

- [ ] Add central handlers/routes for complete Bluetooth state, adapter controls, discovery, device operations, operation status/cancel, and diagnostics.
- [ ] Require `adapter_id` and device identity in new action contracts.
- [ ] Validate parameters and return structured errors consistently.
- [ ] Keep existing `/devices/state` and `/bt/*` routes compatible during migration.
- [ ] Extend `tests/test_api_dispatch.py` route coverage.
- [ ] Add handler tests for two adapters, missing/ambiguous targets, backend unavailable, permission denied, timeout, and operation conflict.

**Exit gate:** API contract is testable entirely with fake backend and legacy routes remain deterministic.

## Phase 5: WebUI control centre

- [ ] Refactor the existing Bluetooth tab in `rpi_dashboard/static/index.html` and associated static JS/CSS. Do not add a new sidebar.
- [ ] Render backend/BlueZ health and global summary.
- [ ] Render two adapter cards/zones with stable labels, address, current `hciN`, role, power, and discovery controls.
- [ ] Group devices by adapter and show explicit paired/trusted/connected/services-resolved states.
- [ ] Add selected-device details, available actions, operation progress, errors, and recent event log.
- [ ] Add soundbar readiness ladder and Xbox/Steam Link blocker list.
- [ ] Provide responsive stacked layout for narrow screens.
- [ ] Preserve bilingual labels and accessible keyboard/focus behaviour.
- [ ] Do not present unknown RSSI/battery as fabricated values.
- [ ] Keep inline `webserver.py` fallback functional; either adapt it minimally or document/deprecate it only after static parity is proven.
- [ ] Add fake-backend browser/DOM tests in the supported CI/gateway environment.

**Exit gate:** WebUI handles zero/one/two adapters, pending operations, errors, and responsive layout using backend truth.

## Phase 6: Live TUI parity

- [ ] Modify the Bluetooth tab in live `tui.py`, not only `rpi_dashboard/tui/modern.py`.
- [ ] Add two-adapter selector/panels using ASCII-safe status presentation.
- [ ] Add device list/table, selected details, operations, diagnostics, recent events, and keyboard actions.
- [ ] Use the same service/models as WebUI; no direct Bluetooth subprocess parsing in TUI.
- [ ] Preserve tty1 dimensions, low resource usage, task-oriented tab order, and Czech/English switching.
- [ ] Extend `tests/test_tui_modern.py` tests that exercise the live `tui.py` for zero/one/two adapters, hotplug, operation failure, readiness, language, and constrained dimensions.

**Exit gate:** TUI and WebUI expose equivalent core actions/status and both consume the same fake scenarios.

## Phase 7: Soundbar and controller readiness integration

- [ ] Reconcile the known Samsung soundbar identity with Audio configuration without creating another hard-coded source of truth.
- [ ] Implement the full readiness ladder: adapter, known, paired, trusted, connected, services resolved/profile, PipeWire sink, default/usable route, loopback when requested.
- [ ] Keep Audio as owner of PipeWire sink selection, routing, volume, latency, and loopback.
- [ ] Expand Xbox/controller classification using UUID/icon/appearance/input evidence.
- [ ] Require Linux input device evidence plus Steam Link availability for final controller readiness.
- [ ] Report ERTM/modules as diagnostics and blockers only; do not alter kernel state.
- [ ] Add automated tests for every readiness step and unknown state.

**Exit gate:** readiness output explains exactly why soundbar/controller is ready, blocked, or unknown.

## Phase 8: Migration hardening and cleanup boundary

- [ ] Search for all Bluetooth references in `webserver.py`, `tui.py`, `rpi_dashboard/`, `tests/`, provisioning, and docs.
- [ ] Remove duplicate runtime ownership only where parity and tests prove safety.
- [ ] Do not delete legacy endpoints or fallback UI in this phase unless explicitly approved and protected by migration tests.
- [ ] Update architecture/user documentation, endpoint docs, and troubleshooting notes.
- [ ] Document adapter role configuration and recovery after adapter replacement.
- [ ] Record follow-up cleanup items instead of expanding scope indefinitely.

**Exit gate:** one source of truth exists; remaining legacy surfaces are clearly marked and bounded.

## Phase 9: Verification

### Automated, safe everywhere

- [ ] Run focused Bluetooth model/backend tests.
- [ ] Run API tests.
- [ ] Run live TUI tests.
- [ ] Run WebUI static/e2e tests in the designated environment.
- [ ] Run `ruff`, `mypy`, and full `pytest` according to repository commands.
- [ ] Confirm tests do not contact real D-Bus/BlueZ, pair devices, restart services, write sysfs, or require hardware.

### Manual read-only RPi verification

- [ ] Confirm both adapters are listed with stable IDs and current indexes.
- [ ] Confirm unplug/replug or controlled availability simulation updates state without dashboard crash.
- [ ] Confirm known soundbar and controller records are associated with the correct adapter.
- [ ] Confirm WebUI and tty1 TUI show matching state.

### Explicitly authorized live operations only

These steps require the user's awareness and must preserve existing pairings:

- [ ] Start/stop discovery on each adapter independently.
- [ ] Connect/disconnect an already paired test device on the selected adapter.
- [ ] Verify soundbar readiness transitions without altering Audio routing unexpectedly.
- [ ] Verify Xbox controller appears as a Linux input device and Steam Link blocker list changes correctly.

Do not remove/re-pair the Samsung soundbar or modify BlueZ/systemd/kernel configuration merely to satisfy a test.

### Finish workflow

- [ ] Review `git diff --stat` and `git status --short`.
- [ ] Update track metadata/status and registry only when evidence supports it.
- [ ] Run `tools/verify-done.sh` and retain the receipt.
- [ ] Use the repository's prescribed finish/commit workflow. Do not bypass CI safety rules.

## First implementation step

Start with Phase 0 and Phase 1 only: document the D-Bus/library and stable-identity decision, create domain models plus the fake backend, and add two-adapter/hotplug tests. Do not touch the live WebUI, TUI, real BlueZ service, or real devices until that foundation passes.