# Bluetooth TUI Control Center Parity

## Summary

Implement a focused follow-up route that makes the live Bluetooth tab in `tui.py` match the design intent of `docs/design/rpi-screenshots/RPi-BT-TUI.png` as closely as Textual and the physical TV console allow.

This route is documentation/planning only until explicitly implemented. It must not change production code as part of authoring the route.

## Reference

Primary visual reference:

- `docs/design/rpi-screenshots/RPi-BT-TUI.png`

Primary WebUI reference:

- `docs/design/bluetooth/bt-webui-gemini-prototype.html`

Related reference context:

- `docs/design/rpi-screenshots/RPi-BT_advanced.png`
- `docs/design/rpi-screenshots/RPi-BT_basic.png`
- `docs/design/bluetooth/tui-reference.png`
- `conductor/tracks/bluetooth-control-center-refactor_20260718/spec.md`
- `conductor/tracks/bluetooth-control-center-refactor_20260718/plan.md`

The new TUI target is not the older basic Textual panel. It is a dense, terminal-native control center with a topology map, adapter-specific device tables, diagnostics, recent events, quick actions, and a footer status line.

The new WebUI Bluetooth settings target is the Gemini prototype saved in `docs/design/bluetooth/bt-webui-gemini-prototype.html`. Preserve its visual language as the design source of truth: dark shell, left/right sidebars in Expert mode, cyan Adapter A audio lane, green Adapter B IO/controller lane, interactive topology canvas, compact panels, toggles, filters, hardware gauges, device detail panel, quick actions, and summary cards. Functional integration may be polished and evolved where needed for the real backend, but the visual design should not be casually redesigned during implementation.

## Current Gap

The current live `tui.py` Bluetooth tab has been moved toward a control-center presentation, but it is still structurally different from `RPi-BT-TUI.png`:

- the reference uses a large framed `TOPOLOGY` section spanning the full width;
- Adapter A is explicitly audio-oriented and Adapter B is explicitly IO/controllers-oriented;
- top-row topology branches are visually grouped into categories, not only flat device lists;
- the reference has a legend row directly below topology;
- the lower grid is four columns in the middle row and four columns in the status row;
- quick actions and help are always visible as command references;
- diagnostics and recent events are equal first-class panels;
- the footer summarizes service, totals, OS, CPU, and memory;
- terminal framing, cyan/green/yellow/red color language, and ASCII-safe structure are part of the design.

## Goals

1. Make the live `tui.py` Bluetooth tab visually and structurally match `RPi-BT-TUI.png`.
2. Preserve the current Bluetooth v2 backend/API/service contract.
3. Keep all Bluetooth data sourced from the shared domain state, not direct `bluetoothctl` parsing in TUI.
4. Keep the implementation ASCII-safe for tty1, except where Textual box drawing is already known to render acceptably.
5. Preserve Czech/English language switching for tab labels and existing buttons while allowing the Bluetooth control center itself to use compact technical English labels.
6. Support zero, one, and two adapters without blank panels or crashes.
7. Preserve keyboard/action functionality already present: scan, pair, trust, connect, disconnect, remove, refresh.
8. Add automated tests that inspect live `tui.py`, not only `rpi_dashboard/tui/modern.py`.
9. Verify on the physical tty1 and with remote E2E where browser/WebUI regressions might be affected by shared API changes.

## Non-goals

- Do not redesign WebUI away from `docs/design/bluetooth/bt-webui-gemini-prototype.html`; when WebUI work is performed, treat the prototype as the visual contract.
- Do not change the Bluetooth backend, BlueZ D-Bus implementation, pairing semantics, or adapter identity model unless a small UI data-shaping helper is required.
- Do not introduce real pairing/removal operations in tests.
- Do not replace `tui.py` with `rpi_dashboard/tui/modern.py`.
- Do not restart or reconfigure BlueZ as part of ordinary implementation.
- Do not require the reference's exact decorative glow effects; Textual/tty fidelity matters more than bitmap-perfect styling.
- Do not commit generated screenshots or runtime artifacts unless explicitly approved.

## WebUI Design Contract

This route now also records the intended WebUI Bluetooth settings design. Implementation should port the prototype into the existing WebUI stack rather than shipping the standalone file directly.

Required preservation points:

- global top navigation with Raspberry Pi identity, status legend, Basic/Expert mode switch, language switch, and theme toggle;
- Expert mode left sidebar and right tools sidebar;
- Basic mode that hides sidebars and advanced header while keeping topology, controls, details, and status usable;
- large interactive topology panel with pan, zoom, reset, selectable devices, SVG connection lines, Adapter A/B hex hubs, cyan/green color split, offline dimming, and selected-device highlight;
- service controls for auto-connect, discoverable mode, timeout, and scan mode;
- filter panel for connected, paired, and available devices;
- hardware status panel with Adapter A/B RSSI gauges;
- device detail panel with name, active/offline status, RSSI, MAC address, adapter assignment, disconnect, and move-adapter action;
- right sidebar quick actions and summary cards in Expert mode.

Functional evolution is expected:

- replace static `devices` and `actions` arrays with live state from the Bluetooth backend;
- map every destructive action to existing confirmation/error handling;
- preserve adapter-aware operations rather than MAC-only fallbacks;
- persist user-visible mode/theme/language choices only if this matches existing WebUI conventions;
- degrade gracefully when only one adapter exists, when backend data is partial, or when RSSI/MAC metadata is absent;
- replace Tailwind CDN and dynamic runtime class construction with repository-native CSS/build patterns when integrating into production;
- keep visual regression coverage because small CSS changes can break this design.

Implementation caution: the prototype uses dynamic Tailwind class names such as template-built `dark:text-[...]` and `border-${color}` values. Those will not be reliable in a compiled Tailwind pipeline unless converted to explicit classes, CSS variables, data attributes, or a safelist.

## Required Layout

The Bluetooth tab should be one coherent control center, not a stack of unrelated widgets.

### Header Row

Target content:

- left: Bluetooth glyph/marker and title `RPi Bluetooth Control Center (TUI)`;
- subtitle/secondary text: `Dual Adapter Management`;
- right-aligned command strip:
  - `Auto Connect: ON`
  - `[S] Scan All`
  - `[P] Pair New`
  - `[R] Refresh`
  - `[Q] Quit` or repository-appropriate equivalent.

Implementation notes:

- If Textual tab chrome already provides app title and global footer, keep this header inside the Bluetooth pane so the reference is visible when the tab is selected.
- Use fixed-height header content to avoid vertical shift.
- Keep title and command strip readable at 120x35 and 167x94 style test sizes.

### Topology Frame

The top half should be a framed panel titled `TOPOLOGY`.

Required zones:

1. `AUDIO OUTPUT DEVICES` group on the far left:
   - Speakers / Soundbars
   - Headphones
   - Soundbars
   - signal bars
2. `ADAPTER A` hub:
   - powered state
   - average RSSI
   - Bluetooth symbol or ASCII `BT` hub
   - connected/available count
3. `AUDIO INPUT DEVICES` group between Adapter A and the IO devices:
   - Alexa Echo Dot
   - Smartphone
   - Tibo Sphere 2
   - Microphone
4. `IO DEVICES` group:
   - RGB LED Strip
   - RGB LED Light
   - BLE Sensor
   - Fitness Tracker
5. `ADAPTER B` hub:
   - powered state
   - average RSSI
   - connected/available count
   - visual role label `IO & CONTROLLERS MODE`
6. `CONTROLLERS & IO DEVICES` group on the far right:
   - Keyboard
   - Mouse
   - Game Controller
   - MIDI Controller

The rendered topology must map real data into these groups:

- audio output devices: speaker, soundbar, headphones, A2DP/audio-output UUID/icon/class evidence;
- audio input devices: microphones, phones, echo-style devices, source/input-like devices where evidence exists;
- IO devices: LED, sensor, tracker, generic BLE or unknown low-power devices;
- controllers: gamepad, Xbox controller, keyboard, mouse, MIDI/input devices.

If the live state does not include enough devices for every row, fill remaining rows with stable placeholders styled as unavailable/empty, not fake connected devices. The UI must never invent live RSSI/pairing state.

### Legend Row

Immediately below topology, render a horizontal legend:

- `Strong (> -70 dBm)`
- `Weak (-70 to -85 dBm)`
- `Disconnected (< -85 dBm)`

This can be a Static panel with colored line samples. If Textual color markup makes columns unstable, use labels and fixed spacing instead.

### Middle Grid

Four framed panels across the width:

1. `ADAPTER A DEVICES (AUDIO)`
   - columns: `#`, `Device Name`, `RSSI`, `Status`
   - adapter address footer
2. `ADAPTER B DEVICES (IO & CONTROLLERS)`
   - columns: `#`, `Device Name`, `RSSI`, `Status`
   - adapter address footer
3. `AVAILABLE DEVICES`
   - columns: `Device Name`, `RSSI`, `Adapter`
   - footer: `Press [P] to pair selected device`
4. `QUICK ACTIONS`
   - `[S] Scan All Adapters`
   - `[P] Pair New Device`
   - `[C] Connect to Device`
   - `[D] Disconnect Device`
   - `[R] Refresh Topology`
   - `[X] Remove Paired Device`
   - `[G] Adapter Priority`
   - `[M] More Settings`

The existing `OptionList` can remain for selection/action plumbing, but the visible presentation should follow the reference. If `OptionList` is retained, it should be visually subordinate or integrated into one of these panels rather than dominating the tab.

### Bottom Grid

Four framed panels:

1. `ADAPTER STATUS`
   - Adapter A powered state, connections, available count, average RSSI, TX power when known
   - Adapter B equivalent
2. `DIAGNOSTICS`
   - Bluetooth service state
   - host controllers such as `hci0`, `hci1`
   - discoverable/pairable state
   - uptime
   - kernel
   - BlueZ version
3. `RECENT EVENTS`
   - latest operations/events with timestamps when available
   - errors in red
   - scan completion and adapter connect/disconnect events
4. `HELP`
   - arrow navigation
   - Enter select action
   - Tab switch panel
   - R refresh
   - Q quit or app-specific equivalent

### Footer

The footer should include:

- Bluetooth Service: Running/Degraded/Unavailable
- Total Connected
- Total Paired
- RPI OS: Bookworm (64-bit) when detectable or configured
- CPU %
- Mem %

This footer should be stable and one line where terminal width permits.

## Data Mapping Requirements

The UI must consume state from the existing shared Bluetooth service contract:

- adapters from v2 `adapters`;
- devices from v2 `devices`;
- operations from v2 `operations`;
- events from v2 `events`;
- soundbar/controller readiness from v2 `diagnostics`;
- backend health from v2 `backend`.

Adapter labels:

- Adapter A/B display ordering should be stable for the session.
- Prefer configured roles if available.
- If roles are absent, Adapter A should default to the first powered/present adapter and Adapter B to the second.
- Do not use `hci0`/`hci1` as identity, only as display metadata.

Device grouping:

- Use device `kind`, icon, UUIDs, class/appearance, and name as fallback.
- Keep an `unknown` group but render it deliberately.
- Do not move a device between adapter tables unless the backend relationship changes.

RSSI:

- show exact RSSI when present;
- show `-- dBm` or `unknown` when absent;
- average only known values;
- classify strong/weak/disconnected from actual RSSI or connection state.

Status:

- connected: green
- paired/trusted but disconnected: cyan/yellow depending on connected state
- available/unpaired: yellow
- absent/error: red

## Interaction Requirements

Keyboard actions should be wired to current TUI action methods or added as focused handlers:

- `S`: scan all powered adapters
- `R`: refresh Bluetooth state/topology
- `P`: pair selected available device
- `C`: connect selected device
- `D`: disconnect selected device
- `X`: remove selected paired device, with clear danger semantics
- `G`: adapter priority/role panel if implemented, otherwise disabled with a visible status message
- `M`: more settings if implemented, otherwise disabled with a visible status message

Action execution must remain adapter-aware. If selection does not include `adapter_id` and device key, return a visible error instead of falling back to ambiguous MAC-only action.

## Textual Implementation Guidance

Expected implementation area:

- `tui.py`
- tests in `tests/test_tui_modern.py` or a new focused `tests/test_tui_bluetooth_control_center.py`
- optional helper module only if it reduces complexity, for example `rpi_dashboard/tui/bluetooth_view.py`

Prefer a small set of pure rendering helpers that accept a Bluetooth state dict and return panel text/markup. This makes tests simpler and avoids driving the full Textual app for every formatting case.

Suggested helper responsibilities:

- normalize adapter order and labels;
- classify device into topology group;
- compute RSSI average and counts;
- render fixed-width table rows;
- render event lines;
- render status/footer text;
- expose deterministic output for tests.

Keep UI updates bounded. The Bluetooth tab should not perform heavy blocking subprocess work on every refresh. If OS/version/kernel diagnostics are needed, cache them or gather them in existing periodic update flow.

## Acceptance Criteria

The route is complete when:

1. Selecting the live Bluetooth tab on tty1 visibly resembles `RPi-BT-TUI.png` in structure:
   - header command strip;
   - full-width topology panel;
   - legend row;
   - adapter A/B device tables;
   - available devices panel;
   - quick actions panel;
   - adapter status;
   - diagnostics;
   - recent events;
   - help;
   - footer.
2. The UI works with the current live RPi state: two adapters, BlueZ D-Bus backend, and known paired devices.
3. The UI also renders useful states for zero adapters, one adapter, two adapters, and backend degraded/unavailable.
4. No direct Bluetooth subprocess parsing is added to TUI.
5. Existing pair/connect/trust/disconnect/remove actions still work through adapter-aware service calls.
6. The tab remains readable at the tested Textual sizes and does not collapse other operational tabs.
7. Automated tests pass:
   - focused rendering helper tests;
   - live `tui.py` Textual layout tests;
   - Bluetooth API/service tests if touched;
   - full `pytest`;
   - `ruff`;
   - `mypy`.
8. Manual verification evidence is recorded:
   - `sudo -n cat /dev/vcs1` or equivalent tty capture after switching to Bluetooth tab;
   - live `/bt/state` summary;
   - no service crash after refresh.

## Risks

- Bitmap-perfect reproduction is not realistic in Textual/tty; prioritize structure, grouping, color language, and usability.
- Physical tty rendering may mangle some Unicode glyphs. Prefer ASCII labels such as `BT`, `--`, `|--`, and standard Textual borders.
- Dense panels can overflow at small terminal sizes. Define minimum heights and graceful truncation.
- Current Bluetooth state may not include enough semantic evidence for every category in the mock-up. Use honest placeholders and evidence-backed grouping.
- Avoid making the TUI refresh loop slow by querying OS/kernel/BlueZ diagnostics too often.

## Out of Scope Follow-ups

- WebUI parity with `RPi-BT_advanced.png`.
- Adapter role configuration persistence.
- Full keyboard focus manager for every topology group.
- Live graph animation.
- Real pairing agent UX beyond existing service capabilities.
