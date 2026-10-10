# Audit: Current Bluetooth Implementation

Audit date: 2026-07-18

Repository baseline inspected: `milhy545/RPi`, `main` at `4132bfacbdac7a4a027e29db2071a3db7e6fdb57`.

This audit was performed through the GitHub connector. It cannot see uncommitted files in the live RPi working tree. The implementer must therefore run `git status --short` and `git branch --show-current` locally before changing anything.

## Repository and runtime entrypoints

- Development/live repository documented as `~/rpi-dashboard`.
- `provisioning/dashboard.service` starts `.venv/bin/python tui.py` on tty1.
- `provisioning/webserver.service` starts `.venv/bin/python webserver.py` with session D-Bus and PipeWire/Pulse environment.
- `main.py` is not the dashboard entrypoint; it only prints a placeholder greeting.
- `rpi_dashboard/tui/modern.py` is a prototype. Production TUI work must target `tui.py`.
- `webserver.py` serves `rpi_dashboard/static/index.html` first and retains a large inline fallback implementation.

## Repository rules relevant to this track

- `AGENTS.md` identifies `webserver.py`, `rpi_dashboard/api/`, `rpi_dashboard/services/`, `rpi_dashboard/static/`, and `tui.py` as the active architecture/migration surfaces.
- Tests mock system tools such as `bluetoothctl`, `pactl`, and `nmcli`.
- `tools/verify-done.sh` and the repository finish workflow are mandatory before claiming completion.
- CI safety rules prohibit casual direct pushes from the RPi and unsupported completion claims.
- Product guidance prioritizes low resource usage, terminal-native operation, no mandatory animations, and the Goat Principle: functionality and reliability over decorative purity.

## Current Bluetooth service

Primary file: `rpi_dashboard/services/devices.py`.

### State acquisition

- `devices_state()` combines Bluetooth and Wi-Fi into one service response.
- Bluetooth devices are obtained using:
  - `bluetoothctl devices Paired`
  - `bluetoothctl devices Scanned`
  - `bluetoothctl info <mac>` for each record
- Parsed records expose:
  - `mac`
  - `name`
  - `kind`
  - legacy `type`
  - `paired`
  - `connected`
  - `trusted`
- Paired and scanned records are merged globally by remote MAC.
- There is no adapter model, adapter path, adapter address, or adapter parameter.
- The same remote address visible through two adapters would be collapsed.

### Classification

- `_bt_device_type()` and `_bt_device_kind()` classify mostly by substrings in the display name.
- Xbox recognition checks words such as `xbox`, `wireless controller`, `controller`, and `gamepad`.
- Audio recognition checks names such as `speaker`, `soundbar`, `headphone`, `earbuds`, and `audio`.
- UUIDs, BlueZ icon, appearance, class, HID profile, media profile, and Linux input evidence are not used for primary device classification.

### Operations

Available wrappers:

- `bluetooth_scan_devices(seconds)`
- `bluetooth_pair(mac)`
- `bluetooth_trust(mac)`
- `bluetooth_connect(mac)`
- `bluetooth_disconnect(mac)`
- `bluetooth_remove(mac)`

Missing or implicit:

- no adapter selection
- no adapter list/detail
- no power control
- no explicit discovery start/stop state contract
- no untrust
- no operation ID/progress/cancel model
- no conflict serialization
- no structured error codes
- no hotplug/event subscription
- no D-Bus implementation

`bluetooth_scan_devices()` invokes `bluetoothctl scan on`, blocks with `time.sleep`, then invokes `scan off`. The duration is clamped to 2–12 seconds. A request handler/thread is therefore occupied during scanning.

All action wrappers return short combined stdout/stderr or broad exception strings. They do not prove that the intended adapter was used.

### Controller readiness

`bluetooth_controller_status()` observes:

- connected devices classified as gamepad/Xbox
- loaded modules from `/proc/modules`:
  - `hid_xpadneo` / `xpadneo`
  - `xpad`
  - `uhid`
  - `hid_microsoft`
- ERTM value from `/sys/module/bluetooth/parameters/disable_ertm`
- names in `/proc/bus/input/devices`
- `steamlink` command availability via `shutil.which`

Current `ready` is essentially connected-controller plus Steam Link executable. It does not require services resolved or matching Linux input evidence.

## Current API

Files:

- `rpi_dashboard/api/handlers.py`
- `rpi_dashboard/api/routes.py`

Registered Bluetooth routes:

- `/devices/state`
- `/bt/scan`
- `/bt/controller`
- `/bt/pair`
- `/bt/trust`
- `/bt/connect`
- `/bt/disconnect`
- `/bt/remove`

The legacy `/devices/bt/scan` route remains marked as implemented in `webserver.py`.

Handlers accept only `mac` for device operations. No adapter identity is accepted or validated. Handler validation is minimal and error response shape is not standardized.

`tests/test_api_dispatch.py` checks that WebUI endpoint names exist in the central route registry, including all current Bluetooth routes, but does not establish a multi-adapter contract.

## Current WebUI

Primary static surface: `rpi_dashboard/static/index.html` plus static scripts/styles.

Observed characteristics:

- Bluetooth already has a dedicated top-level tab.
- The project does not need another sidebar or another top-level Bluetooth navigation item.
- Current Bluetooth content is a flat management panel with refresh/scan, device list/actions, and controller readiness.
- Static WebUI and the inline `webserver.py` fallback create duplicate Bluetooth frontend/migration surfaces.
- Existing actions call `/bt/*` routes.
- Current presentation does not represent two physical adapters or show adapter-to-device ownership.

Implementation must search all inline and static Bluetooth functions before editing so that the active surface and fallback remain understood.

## Current live TUI

Primary file: `tui.py`.

Observed characteristics:

- A dedicated `tab_bluetooth` exists in the task-oriented tab set.
- Bluetooth uses the shared `devices_service` functions rather than having a fully separate parser.
- The UI is based on a flat `OptionList` and action buttons for scan, pair, trust, connect, disconnect, and remove.
- Device actions are keyed by remote MAC only.
- Controller readiness displays connection/module/ERTM/input/Steam Link hints.
- There is no adapter selector, adapter role, topology, operation progress model, or hotplug state.
- `tests/test_tui_modern.py` includes tests for the live `tui.py` despite the filename. It verifies the Bluetooth tab and sample connected/paired status rows.
- The TUI must remain usable at constrained tty dimensions and should keep critical status ASCII-safe.

Additional architectural debt: parts of `tui.py` still import or call `webserver` functions for audio-related state. Bluetooth work must not expand that coupling.

## Soundbar and audio boundary

Known production device:

- name: `[Samsung] Soundbar J-Series`
- MAC: `24:4B:03:92:0B:8C`
- historical sink: `bluez_output.24_4B_03_92_0B_8C.1`

Relevant current state:

- `webserver.py` contains live soundbar constants and audio routes/actions.
- `rpi_dashboard/services/audio.py` contains placeholder Bluetooth soundbar constants, creating inconsistency during the ongoing extraction/refactor.
- `conductor/tracks/bt-audio-loopback_20260611/plan.md` documents the actual soundbar, PipeWire sink, USB input loopback, and prior persistence work.
- Audio routing, default sink, loopback, latency, and volume are an Audio-domain responsibility.
- Bluetooth should expose transport/profile readiness and allow Audio to compose sink/route readiness.

The new design must distinguish:

1. adapter present/powered
2. device known
3. paired
4. trusted
5. connected in BlueZ
6. services/profile resolved
7. PipeWire sink present
8. sink usable/default
9. requested route/loopback active

## Existing related Conductor tracks

### `bluetooth-xbox-controller_20260709`

Status in registry: open/in progress.

Already defines:

- shared Bluetooth backend contract
- dedicated WebUI and TUI surfaces
- normalized device fields
- Xbox/Steam Link diagnostics

Much of its basic surface has already appeared in current code. The new track supersedes and extends its remaining work by adding two physical adapters, stable identity, D-Bus/event architecture, hotplug, operation lifecycle, richer diagnostics, and controlled migration. Do not duplicate already working tab separation merely to check a box.

### `devices-connections`

Previously introduced device management, Bluetooth pairing, and remote routes. Treat as historical baseline, not target architecture.

### `bt-audio-loopback_20260611`

Documents the real Samsung soundbar and Audio loopback. Preserve its operational assumptions unless current read-only diagnostics prove they changed.

### `refactor-fullstack_20260706`

Introduced modular service/API/static frontend direction and broader TUI modernization. This Bluetooth track should align with that direction but must use the actual live entrypoints instead of assuming extraction is complete.

### Audio/UI related completed tracks

Relevant history includes `audio-tab-refactor`, `audio-routing-mixer-v2`, `audio-devices-age-routes`, `devices-tab-hardening`, and `dashboard-modes-settings-terminal`. Inspect their plans only when changing the corresponding shared surfaces.

## Current automated coverage

`tests/test_services_devices.py` covers portions of:

- name-based kind/type classification
- normalized device output
- pair/trust wrappers
- controller readiness

`tests/test_api_dispatch.py` covers central route registration/delegation.

`tests/test_tui_modern.py` covers the live TUI tab layout and sample Bluetooth status rows.

Major missing coverage:

- two adapters
- stable adapter identity across index changes
- D-Bus managed objects/signals
- hotplug and BlueZ reconnect
- permission errors and structured error codes
- untrust/cancel/power/discovery lifecycle
- operation concurrency/timeouts
- overlapping remote addresses by adapter
- UUID/profile-based classification
- battery/RSSI unknown semantics
- soundbar readiness ladder
- Linux input evidence required for controller readiness
- WebUI responsive two-adapter behaviour
- API ambiguity handling

## Principal risks

1. **Wrong adapter selection:** current MAC-only `bluetoothctl` actions can target whichever controller BlueZ/CLI considers default.
2. **Identity drift:** `hci0` and `hci1` can change after boot or USB hotplug.
3. **Global device merge:** remote MAC records are not scoped to adapter.
4. **Blocking scan:** current scan sleeps inside the service call.
5. **Frontend duplication:** static assets and inline `webserver.py` fallback can diverge.
6. **Audio regression:** treating BlueZ connected state as full soundbar readiness may break or misreport PipeWire routing.
7. **Prototype confusion:** editing `rpi_dashboard/tui/modern.py` alone would not change the production tty1 dashboard.
8. **False confidence from name matching:** controller/audio classification lacks profile evidence.
9. **Unsafe tests:** direct system bus, BlueZ restart, pairing, or sysfs writes would make CI nondeterministic and potentially destructive.
10. **Over-refactor:** removing compatibility paths before WebUI/TUI parity could strand the live dashboard.

## Open implementation questions

These are decisions to resolve in Phase 0, not invitations to block the track indefinitely:

- Which small Python D-Bus library is already installed or best fits Python 3.12, aiohttp, and Textual?
- What stable hardware information is available for both adapters on the real RPi without privilege escalation?
- Should adapter roles be stored in an existing settings mechanism or a new minimal Bluetooth config file?
- How should event streaming reach WebUI: bounded polling first, existing WebSocket infrastructure, or another repository-consistent mechanism?
- What retention window should apply to absent scanned devices?
- Which existing Audio service/config location should become the single source of truth for the Samsung identity?
- Does the real Xbox controller expose `Battery1`, specific HID UUIDs, and reliable input names on this image?

Choose conservative defaults, document them, and keep interfaces replaceable.