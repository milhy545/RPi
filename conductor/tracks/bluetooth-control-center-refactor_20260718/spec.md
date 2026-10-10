# Bluetooth Control Center Refactor

## Summary

Refactor Bluetooth management into one shared backend and one shared state model used by the live WebUI and the live Textual TUI. The result must correctly represent and control two physical Bluetooth adapters, survive adapter index changes and hotplug events, preserve the existing Samsung soundbar audio workflow, and provide useful Xbox controller / Steam Link readiness diagnostics.

This track defines implementation work only. Creating this track must not change production Bluetooth behaviour.

## Problem statement

The current implementation in `rpi_dashboard/services/devices.py` is based on repeated `bluetoothctl` subprocess calls. It merges paired and scanned devices by MAC address, infers device type mainly from names, and performs pair/trust/connect/disconnect/remove operations without selecting an adapter. That effectively assumes one global adapter and one global device namespace.

The current API exposes `/devices/state`, `/bt/scan`, `/bt/controller`, `/bt/pair`, `/bt/trust`, `/bt/connect`, `/bt/disconnect`, and `/bt/remove`. Actions identify only the remote device MAC. There is no adapter identity, no `untrust`, no explicit power/discoverable control, no operation lifecycle, no hotplug model, and no structured error contract.

The live TUI is `tui.py`, started by `dashboard@milhy777.service`. `rpi_dashboard/tui/modern.py` is a prototype and is not the production entrypoint. The WebUI primarily serves `rpi_dashboard/static/index.html`; large inline HTML/JS in `webserver.py` remains a fallback and migration liability. Bluetooth UI exists in both surfaces but is still a flat device list rather than a two-adapter control centre.

The Samsung soundbar workflow is split across Bluetooth and audio code. The live legacy constants in `webserver.py` identify `[Samsung] Soundbar J-Series`, MAC `24:4B:03:92:0B:8C`, and sink `bluez_output.24_4B_03_92_0B_8C.1`, while `rpi_dashboard/services/audio.py` still contains placeholder Bluetooth constants. Bluetooth connection state, BlueZ service resolution, PipeWire sink availability, default routing, and loopback readiness must not be collapsed into one misleading boolean.

## Goals

1. Provide one shared Bluetooth domain service used by API, WebUI, and live TUI.
2. Model at least two physical adapters simultaneously.
3. Give each adapter a stable identity that does not depend only on `hci0` / `hci1` numbering.
4. Prefer direct BlueZ D-Bus interfaces and signals over parsing interactive CLI output.
5. Support adapter listing, power, discovery, pair, trust, untrust, connect, disconnect, remove, cancel, refresh, and diagnostics.
6. Handle adapter and device hotplug without requiring a dashboard restart.
7. Expose a deterministic, testable state and error contract.
8. Preserve compatibility for existing consumers while migrating them to an adapter-aware API.
9. Redesign the existing Bluetooth tab in WebUI and TUI. Do not add another sidebar or duplicate top-level navigation.
10. Preserve the existing audio routing domain boundary: Bluetooth establishes device transport; Audio owns sinks, default route, loopback, and latency.
11. Provide soundbar readiness and Xbox/Steam Link readiness as composed diagnostics.
12. Provide a fake backend so ordinary CI never requires real Bluetooth hardware or a running BlueZ daemon.

## Non-goals and hard prohibitions

- Do not pair, remove, trust, untrust, connect, or disconnect real devices while implementing ordinary unit tests.
- Do not restart, stop, reconfigure, or replace `bluetooth.service` / BlueZ as part of ordinary implementation or CI.
- Do not install kernel modules, DKMS packages, firmware, or modify boot/kernel settings in this track.
- Do not modify systemd units unless a later explicit, separately reviewed requirement proves it necessary.
- Do not delete legacy endpoints or the inline WebUI fallback until parity, migration, and deprecation evidence exist.
- Do not move PipeWire routing, loopback creation, volume, latency, or default-sink ownership into the Bluetooth service.
- Do not assume adapter index, USB bus path, or remote device MAC alone is sufficient identity in all circumstances.
- Do not treat visual mock-up animations, glowing lines, signal waves, or decorative toggles as required functionality.
- Do not replace the live `tui.py` with `rpi_dashboard/tui/modern.py` in this track.

## Required architecture

### Backend boundary

Create a focused Bluetooth domain package or service, for example `rpi_dashboard/services/bluetooth/`, rather than extending the mixed Wi-Fi/Bluetooth file indefinitely. Exact module names may follow repository conventions, but responsibilities must be separated:

- backend protocol/interface
- BlueZ D-Bus implementation
- fake/in-memory implementation
- optional `bluetoothctl` fallback adapter
- domain models and serialization
- operation orchestration and timeout handling
- diagnostics/readiness aggregation

`rpi_dashboard/services/devices.py` may remain as a compatibility facade during migration, but must not remain the source of truth for new Bluetooth behaviour.

### BlueZ integration

Prefer the system bus and standard BlueZ interfaces:

- `org.freedesktop.DBus.ObjectManager`
- `org.freedesktop.DBus.Properties`
- `org.bluez.Adapter1`
- `org.bluez.Device1`
- `org.bluez.AgentManager1` / `org.bluez.Agent1` when pairing interaction is required
- relevant media/profile properties only for observation, not audio routing ownership

Use managed objects for initial state and D-Bus signals for incremental updates. A polling fallback may exist only as a bounded recovery mechanism.

Before adding a Python dependency, inspect the installed RPi environment and existing project constraints. Prefer a small maintained async-capable D-Bus library compatible with Python 3.12. Document the choice and memory/runtime impact. Do not add a large framework merely to wrap a few methods.

`bluetoothctl` may remain as a fallback only when:

- D-Bus access is unavailable or a required BlueZ behaviour cannot be implemented reliably through the selected library;
- the fallback explicitly selects the intended controller/adapter;
- command execution is bounded by timeouts;
- output parsing is isolated and tested;
- the API reports that a degraded fallback backend is active.

### Stable adapter identity

Every adapter must expose:

- `id`: stable application identity
- `bluez_path`: current object path such as `/org/bluez/hci0`
- `index`: current kernel/BlueZ index for display only
- `address` and `address_type`
- `name`, `alias`, `modalias` when available
- `powered`, `discoverable`, `pairable`, `discovering`
- `present`, `backend`, and health/error state
- optional hardware hints such as USB path/vendor/product when obtainable without privilege escalation

Identity resolution priority should be documented and tested. Prefer adapter public address when stable and available, then persistent hardware characteristics. Never use only `hciN` as the persistent key. When an adapter reappears under a different index, the UI and stored role assignment must follow the stable identity.

Support optional user-facing roles such as `primary`, `audio`, `controllers`, or custom label. Roles are configuration, not identity.

### Device identity and adapter relationship

Every remote device record must include:

- stable device key scoped to adapter, for example `<adapter-id>/<remote-address>`
- `adapter_id` and current BlueZ object path
- address and address type
- name, alias, icon, class/appearance, UUIDs when available
- paired, trusted, blocked, connected, services resolved
- RSSI / TxPower when available, with `null` for unknown rather than invented percentages
- battery percentage only when BlueZ exposes a battery interface
- derived role/kind with evidence and confidence
- first seen, last seen, and present/known status where practical

Do not merge the same remote address seen by different adapters into one record. Do not classify solely by device name when UUID, appearance, icon, input interfaces, or audio profiles provide stronger evidence.

### Shared state contract

Define versioned JSON-serializable models. A representative top-level state is:

```json
{
  "ok": true,
  "schema_version": 2,
  "backend": {"name": "bluez-dbus", "degraded": false},
  "adapters": [],
  "devices": [],
  "operations": [],
  "diagnostics": {
    "bluez": {},
    "soundbar": {},
    "controllers": {},
    "steamlink": {}
  }
}
```

Use explicit enums/strings for operation and health states. Errors must include a stable code, human-readable message, retryability, adapter/device context, and safe technical detail. Expected codes include at least:

- `backend_unavailable`
- `permission_denied`
- `adapter_missing`
- `adapter_powered_off`
- `device_missing`
- `operation_busy`
- `pairing_rejected`
- `authentication_failed`
- `connection_failed`
- `profile_unavailable`
- `timeout`
- `cancelled`
- `unsupported`

### Operations

Bluetooth operations must be adapter-aware and asynchronous from the UI perspective. Each operation should expose an ID, type, target, start/update timestamps, state, result/error, and cancellation capability where BlueZ supports cancellation.

Required operations:

- set adapter power
- start/stop discovery
- pair
- trust / untrust
- connect / disconnect
- remove
- cancel pairing/discovery where supported
- refresh/reconcile state

Prevent conflicting operations on the same adapter/device and surface the conflict instead of silently racing subprocesses.

### Hotplug and reconciliation

Handle `InterfacesAdded`, `InterfacesRemoved`, and property changes. On BlueZ reconnect or signal loss, rebuild state from ObjectManager and preserve user role assignments by stable adapter identity. Mark missing adapters/devices as absent before pruning them according to a documented retention rule.

The dashboard must not crash if:

- no adapter is present;
- only one of the expected two adapters is present;
- an adapter disappears during discovery or pairing;
- BlueZ is temporarily unavailable;
- D-Bus permission is denied;
- a device disappears between selection and action.

## API requirements

Introduce adapter-aware routes or handlers while keeping old routes operational during migration. Exact paths may follow the central route registry, but the contract must cover:

- complete Bluetooth state
- adapter detail/control
- discovery start/stop
- device action with `adapter_id` plus device key/address
- operation status/cancel
- diagnostics

Existing routes that accept only `mac` must either:

1. resolve uniquely and delegate to the new service, or
2. return a deterministic ambiguity error when the device exists on multiple adapters.

Do not silently choose the first adapter.

Update route registry tests and handler validation. Query parameters must be validated centrally. Maintain useful compatibility fields for current WebUI/TUI until both surfaces migrate.

## WebUI requirements

Refactor the existing top-level Bluetooth tab. Do not create another sidebar.

The desktop layout should present:

1. Header with backend/BlueZ health, refresh, diagnostics, and global summary.
2. Two adapter cards/zones, each showing stable label, address, current `hciN`, powered/discovering state, role, and controls.
3. Device cards grouped or visually connected to the adapter that owns the relationship.
4. Selected-device detail with evidence-backed capabilities, exact state, available actions, latest operation, and error text.
5. Soundbar readiness block and controller/Steam Link readiness block.
6. Compact recent-event/operation log useful for diagnosis.

Responsive behaviour:

- wide screens: two adapter zones side by side with a central or lower detail panel;
- narrow/mobile screens: stacked adapter sections, no horizontal dependency on decorative connection lines;
- keyboard focus and accessible labels for every action;
- colour is never the only state indicator;
- no mandatory animation;
- preserve Czech/English translation conventions.

Actions must refresh from backend truth. Optimistic UI is permitted only when clearly marked pending and reconciled after operation completion.

## TUI requirements

Modify the live `tui.py` Bluetooth tab and its tests. Preserve Textual operation on tty1 and the repository's low-resource/ASCII-friendly conventions.

The TUI must expose the same domain state and actions as WebUI using a compact topology:

- adapter selector or two clearly separated adapter panels;
- device table/list with adapter, role, signal if known, and explicit paired/trusted/connected/services status;
- selected-device details;
- operation status and recent events;
- soundbar and Xbox/Steam Link readiness;
- documented keyboard actions for refresh, discovery, pair, trust/untrust, connect/disconnect, remove, cancel, and diagnostics.

Use ASCII-safe text in critical status areas. Do not depend on Unicode diagrams rendering correctly on tty1.

## Soundbar readiness contract

Keep Bluetooth and Audio responsibilities distinct. Compose a readiness ladder for the known Samsung device:

1. adapter present and powered
2. device known/discovered
3. paired
4. trusted
5. BlueZ connected
6. services resolved / expected audio UUID or profile visible
7. PipeWire Bluetooth sink present
8. sink usable and optionally default
9. configured loopback/route active when requested

Each step must have `true`, `false`, or `unknown` plus a reason. Do not call the soundbar `ready` merely because `Connected: yes` appears.

Reconcile the placeholder constants in `rpi_dashboard/services/audio.py` with the live configuration without duplicating another hard-coded source of truth. Preserve the known MAC `24:4B:03:92:0B:8C` through configuration or an existing central constant during migration.

## Xbox controller and Steam Link readiness

Extend the existing controller diagnostics rather than replacing them with name matching. Readiness should report:

- controller devices and their adapter relationship
- pairing, trust, connection, services-resolved state
- BlueZ HID/input profile evidence
- matching Linux input device evidence
- relevant module presence (`hid_xpadneo`/`xpadneo`, `xpad`, `uhid`, `hid_microsoft`)
- ERTM state as diagnostic, not an automatic instruction to alter the kernel
- Steam Link executable availability
- actionable blocker list

`ready` must require enough evidence that a connected controller is exposed as an input device and Steam Link is available. Unknown evidence must not be treated as success.

## Visual references

The source concepts are attached to the ChatGPT project/conversation `RPi-TV`. Codex should use connected ChatGPT project/file context when available. Internal attachment references are listed in `design-references.md`.

The images are inspiration, not pixel-perfect specifications. Binding concepts are:

- two visible physical adapter zones;
- devices clearly associated with their adapter;
- control-centre rather than flat settings-list hierarchy;
- explicit adapter and device status;
- prominent diagnostics/readiness;
- parity between graphical WebUI and terminal TUI;
- dark dashboard visual language compatible with the existing application.

Non-binding concepts are decorative neon glows, animated radio waves, arbitrary percentages, imaginary topology, and switches not backed by real state.

## Migration and compatibility

1. Add domain models/backend behind tests.
2. Add compatibility facade from current `devices.py` functions.
3. Add adapter-aware API alongside legacy routes.
4. Migrate static WebUI Bluetooth tab.
5. Migrate live `tui.py` Bluetooth tab.
6. Reconcile soundbar readiness with Audio service.
7. Mark inline `webserver.py` Bluetooth UI and old handlers as legacy only after parity is proven.
8. Remove legacy code only in a later explicit cleanup step or follow-up track.

No flag day rewrite. At every phase, the dashboard must remain importable and existing routes must fail safely.

## Testing requirements

### Unit tests

Use fake D-Bus objects/backend fixtures. Cover at least:

- stable adapter identity across `hci` index changes
- two adapters with overlapping remote addresses
- adapter add/remove and BlueZ restart reconciliation
- property updates and device state transitions
- discovery start/stop/cancel and timeout
- pair rejection, authentication failure, permission denial, missing adapter/device
- trust/untrust/connect/disconnect/remove operations
- operation conflicts and cancellation
- device capability classification from UUID/icon/appearance evidence
- nullable RSSI and battery handling
- soundbar readiness ladder
- controller/input/Steam Link readiness blockers
- legacy MAC-only route unique resolution and ambiguity error
- serialization/schema compatibility

### API tests

Extend `tests/test_api_dispatch.py` and focused handler tests for new routes, validation, status codes/response bodies, compatibility behaviour, and backend failures.

### TUI tests

Extend tests around the live `tui.py`, not only the unused prototype. Use fake state with zero, one, and two adapters; adapter disappearance; operation pending/failure; soundbar readiness; controller readiness; Czech/English labels; and constrained tty dimensions.

### WebUI tests

Add DOM/unit or e2e coverage using the fake backend for two adapters, responsive stacking, action dispatch, pending/error state, diagnostics, and accessibility labels. Browser tests run in the designated CI/gateway environment, not as an assumption on the 1 GB RPi.

### CI safety

Ordinary CI must not:

- access a real system D-Bus/BlueZ daemon;
- require Bluetooth hardware;
- pair or manipulate real devices;
- restart BlueZ or dashboard services;
- write kernel/sysfs parameters;
- depend on the Samsung soundbar being present.

Live hardware verification is a separate manual phase after automated checks. It must list exact commands and observations before execution and preserve existing pairings.

## Acceptance criteria

- One shared Bluetooth backend/model drives API, static WebUI, and live TUI.
- Two adapters are represented and individually controllable.
- Stable adapter IDs survive index renumbering in tests.
- Every device is scoped to an adapter and actions require or safely resolve adapter identity.
- D-Bus is the normal backend; any CLI fallback is explicit, adapter-aware, bounded, and reported as degraded.
- Hotplug and temporary BlueZ loss do not crash the dashboard.
- WebUI and TUI expose equivalent core operations and diagnostics.
- Existing legacy routes remain compatible or return deterministic ambiguity errors.
- Soundbar readiness distinguishes Bluetooth transport from PipeWire/audio-route readiness.
- Xbox/Steam Link readiness includes Linux input evidence and actionable blockers.
- Fake backend tests cover success, failure, timeout, hotplug, and two-adapter scenarios.
- No ordinary CI test touches real Bluetooth devices or restarts BlueZ.
- Focused tests, full `ruff`, `mypy`, and `pytest` pass according to repository workflow.
- Completion is claimed only after `tools/verify-done.sh` produces an acceptable receipt and the repository's finish workflow is followed.