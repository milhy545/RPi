# Implementation Notes: Bluetooth Control Center Refactor

## Phase 0 Baseline

Recorded locally on `2026-07-18`:

- Branch: `implement/bluetooth-control-center-phase1`
- Pre-existing worktree change preserved: `AGENTS.md`
- Production entrypoints confirmed from audit/code: `webserver.py`,
  `rpi_dashboard/static/index.html`, and live `tui.py`
- Python environment check through `uv run python` initially found no installed
  D-Bus Python package: `dbus_fast`, `dbus_next`, `pydbus`, and `dbus` were
  absent. `dbus-fast==5.0.22` was then added through `uv`.
- No real BlueZ, pairing, systemd, kernel, or hardware operation was performed.

## Architecture Decision

Phase 1 does not add a runtime dependency. It introduces a pure Python domain
package plus an in-memory backend so API, WebUI, TUI, and future BlueZ code can
converge on one state contract without touching the system bus.

For Phase 2, the selected library is `dbus-fast`. Reasoning: it is small,
async-capable, compatible with Python 3.12, and fits the existing
`aiohttp`/Textual event-loop architecture better than synchronous subprocess
parsing. If the real RPi environment rejects that dependency, the backend
protocol keeps the implementation replaceable and the explicit `bluetoothctl`
fallback remains available.

Async integration strategy:

- Backend methods are async and return typed state/operation records.
- UI/API callers can poll state first; event subscription is represented by a
  bounded fake event stream for later WebSocket or polling integration.
- Ordinary tests use only the fake backend and must not contact real D-Bus.

Memory/runtime policy:

- Domain models are lightweight dataclasses.
- Fake backend keeps bounded event history only.
- No persistent polling loop or hardware watcher is started in Phase 1.

Fallback policy:

- `bluetoothctl` remains only in the existing legacy service for now.
- New code depends on the backend protocol, not raw command parsing.
- A future fallback must be explicit, adapter-aware, timeout-bound, tested, and
  reported as degraded.

Stable adapter identity strategy:

- Prefer the adapter public address for stable application identity.
- Treat `hciN` and BlueZ object path as current runtime diagnostics only.
- Device keys are scoped as `<adapter-id>/<remote-address>` so the same remote
  MAC seen by two adapters is not merged.
- Future hardware hints can supplement identity where public address is absent.

Migration boundary:

- `rpi_dashboard/services/devices.py` remains unchanged in Phase 1.
- Audio remains owner of PipeWire sinks, default route, volume, latency, and
  loopback. Bluetooth readiness reports transport/profile evidence and marks
  Audio-owned steps as unknown unless Audio supplies evidence later.

## Phase 1 Foundation

Added `rpi_dashboard/services/bluetooth/` with:

- typed models for adapters, devices, operations, errors, backend health,
  readiness steps, soundbar readiness, controller readiness, events, and full
  Bluetooth state;
- deterministic `schema_version = 2` serialization;
- an adapter-aware backend protocol;
- an in-memory fake backend with zero/one/two adapter scenarios, overlapping
  remote-address fixtures, hotplug marking, scripted delays/errors, operation
  records, bounded events, and readiness diagnostics.

Focused tests live in `tests/test_bluetooth_domain.py`.

## Phase 2-7 Implementation Summary

Implemented after the Phase 1 foundation:

- Added `dbus-fast>=5.0.22` to the `uv` project dependencies.
- Added `BlueZDbusBackend`, which reads BlueZ state through
  `ObjectManager.GetManagedObjects` and maps `Adapter1`, `Device1`, and
  `Battery1` data into the shared domain state.
- Added adapter-aware D-Bus operations for power, discovery, pair, trust,
  untrust, connect, disconnect, and remove-device.
- Kept `BluetoothctlBackend` as an explicit degraded compatibility fallback
  that selects the intended controller before actions.
- Added service facade routes:
  - `/bt/state`
  - `/bt/discovery`
  - `/bt/adapter-power`
  - `/bt/device-action`
- Routed legacy `/bt/pair`, `/bt/trust`, `/bt/connect`, `/bt/disconnect`, and
  `/bt/remove` through the new resolver. MAC-only actions now reject
  multi-adapter ambiguity instead of silently choosing a default adapter.
- Embedded v2 Bluetooth state into `/devices/state` while preserving legacy
  `devices`, `paired`, `scanned`, and `controller` fields.
- Migrated the static WebUI Bluetooth tab to render backend health, adapter
  zones, adapter-scoped devices, soundbar readiness, controller readiness, and
  recent operations/events from `/bt/state`.
- Migrated the live `tui.py` Bluetooth tab to show adapter summary,
  adapter-scoped device rows, soundbar ladder, controller blockers, and recent
  Bluetooth operations/events while preserving legacy labels/tests.
- Composed Audio-owned evidence into the soundbar readiness ladder at the
  service facade boundary. Bluetooth still does not own PipeWire route,
  default-sink, volume, latency, or loopback mutation.

## Verification Evidence

Safe local verification performed:

- `uv run python -m pytest tests/test_bluetooth_domain.py`
- `uv run python -m pytest tests/test_bluetooth_service_api.py`
- `uv run python -m pytest tests/test_bluetooth_bluez.py`
- `uv run python -m pytest tests/test_tui_modern.py`
- `node --check rpi_dashboard/static/js/app.js`
- `uv run ruff check`
- `uv run mypy .`
- `uv run python -m pytest` -> `153 passed`

Read-only live RPi smoke:

- `handle_bt_state({})` returned `ok=True`
- backend: `bluez-dbus`, `degraded=False`
- adapters: `2`
- devices: `4`
- observed adapter IDs:
  - `adapter-b827ebe11e89` at `/org/bluez/hci0`
  - `adapter-001a7dda710a` at `/org/bluez/hci1`

No pairing, removal, BlueZ restart, systemd change, kernel/sysfs write, or real
device mutation was performed during this implementation pass.

## 2026-07-21 Hardening Update

The production implementation was hardened against multi-adapter and live-RPi
failures found by GitHub review and destructive E2E testing:

- The synchronous service facade now owns one persistent asyncio loop, so a
  cached D-Bus connection is never reused from a closed `asyncio.run()` loop.
- D-Bus calls have bounded timeouts, bounded operation/event history, safe
  no-argument signatures, and idempotent discovery start/stop handling.
- Pairing keeps a `bluetoothctl --agent NoInputNoOutput` process alive until
  BlueZ reports `Bonded: yes`. Device state now exposes `bonded` separately
  from the transient `paired` property.
- The degraded fallback serializes complete bluetoothctl command lines,
  resolves real `hciN` indexes through sysfs, preserves operation history, and
  detects textual failures even when bluetoothctl exits with status zero.
- Added real `/bt/discoverable` and `/bt/settings` handlers. Auto Connect,
  discoverability timeout, and scan mode are persisted in
  `~/.config/rpi-dashboard/bluetooth.json`.
- Legacy `/bt/pair`, `/bt/trust`, `/bt/connect`, `/bt/disconnect`, and
  `/bt/remove` now use the adapter-aware resolver instead of bypassing it.
- The TUI-hosted WebUI proxies the complete legacy endpoint surface and its
  Bluetooth panel is scrollable at constrained tty dimensions.
- The Gemini-derived Bluetooth WebUI design is retained while controls now
  reflect backend truth, destructive actions require confirmation, unsupported
  controls are disabled, and desktop/tablet/mobile geometry is asserted by
  Playwright. Filter checkboxes share a fixed aligned column and topology nodes
  are auto-fitted inside the canvas.

Live RPi findings and recovery:

- The host had both standard `wireplumber.service` and the obsolete
  `wireplumber-bluetooth.service` claiming BlueZ media profiles. The duplicate
  user service was disabled; standard WirePlumber now creates the Bluetooth
  PipeWire sinks.
- The Samsung soundbar was removed/re-paired with explicit authorization. It
  finished as paired, bonded, trusted, connected, services-resolved, and
  exposed `bluez_output.24_4B_03_92_0B_8C.1` in PipeWire.
- Both adapters finished powered on and not discovering. Auto Connect was
  restored with a 120-second discoverability timeout and balanced scan mode.
- Tibo Sphere 2 was removed during destructive testing and requires its
  physical pairing mode before it can be bonded again.

Verification evidence:

- Full RPi CI: PASS (`tools/run-ci.sh`).
- Focused Bluetooth suite: 40 tests passed.
- Milhy-PC mocked browser E2E: PASS, 44 Bluetooth requests.
- Milhy-PC browser against live RPi: PASS, 4 real nodes and 8 quick actions;
  every supported settings, scan, power, pair, trust, connect, disconnect, and
  remove response was required to return `ok: true`.
- The first Milhy-PC gateway retry correctly rejected a preview server holding
  the production API test port `18090`. The preview process was stopped and the
  port was verified free before rerunning the complete gateway.
