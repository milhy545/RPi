# TUI Operational Dashboard Design

## Context

The live TV dashboard is `tui.py`, started by `dashboard@milhy777.service` on `tty1`. The file currently mixes Textual layout, widget event handling, API routes, mode switching, system commands, and runtime logging. `rpi_dashboard/tui/modern.py` is a prototype only; it is not the production entrypoint and does not yet cover real TV behavior.

The settings tab layout bug was fixed on 2026-07-07 and is covered by `tests/test_tui_modern.py::test_legacy_tui_settings_tab_has_usable_height`. The next step is not a visual repaint of the current 2x2 grid. The goal is a professional, TV-first operational dashboard that is readable from couch distance, safe to operate, and still light enough for a 1 GB Raspberry Pi.

## Product Direction

Use a task-oriented dashboard with clear tabs:

- `Player` for URL playback, playback controls, quality, and status.
- `Apps` for Steam Link, GeForce Now, Spotify, Amazon Music, MPV, and Stop & Return.
- `Audio` for HDMI/BT/DLNA output selection, latency, volume, loopback, and pa-dlna status.
- `Devices` for Bluetooth scan, pair, trust, connect, disconnect, remove, and device roles.
- `Network` for LAN, Tailscale, Wi-Fi scan/connect, rescue hotspot, and Raspotify status.
- `System` for safe restart actions, resource status, and service health.
- `Logs` for recent operational events and error detail.

The top bar should always show the current mode, CPU, RAM, temperature, IP/API status, and clock. It should avoid decorative graphics and favor readable operational state.

## Visual Principles

Use short human labels first and technical identifiers second. For example, show `TV HDMI` or `Samsung Soundbar` as the primary label, with sink IDs and MAC addresses in muted text. Use compact status badges such as `ACTIVE`, `PAIRED`, `CONNECTED`, `IDLE`, `ERROR`, and `SCANNING`.

Use ASCII-safe labels on `tty1` unless the service terminal/font is explicitly changed and verified. The current `TERM=linux` output corrupts many emoji and Czech diacritics, so the production TUI should not depend on emoji for meaning.

Buttons should be grouped by object and risk. Destructive actions such as reboot, remove device, and stop active mode need confirmation or a clearly reversible flow. Empty, loading, timeout, and error states must be visible in every data panel.

## Architecture

Keep `tui.py` as the production entrypoint during the migration, but split internal responsibilities into smaller widgets and adapters:

- `rpi_dashboard/tui/app.py` or equivalent: production Textual app shell.
- `rpi_dashboard/tui/widgets/`: top bar, status cards, action rows, device lists, log panel.
- `rpi_dashboard/tui/screens/`: Player, Apps, Audio, Devices, Network, System, Logs.
- `rpi_dashboard/tui/adapters.py`: async wrappers around existing service functions and safe command execution.

Where possible, use existing `rpi_dashboard/services/*` instead of duplicating logic in Textual handlers. Keep the existing API and mode switching behavior stable while the UI layer is extracted.

## Implementation Strategy

Work incrementally on the live path. Do not replace `tui.py` with `modern.py` in one step. First introduce reusable visual components and migrate one workflow at a time, starting with `Audio` and `Devices`, because those are the highest-value settings areas and the current refactor target.

Each migrated tab must have a Textual test for layout, empty/error state, and at least one representative action with mocked system commands. Runtime verification on the TV should include service status, framebuffer/TTY inspection, and manual interaction checks. Browser-heavy checks are out of scope on the RPi; use Milhy-PC only for visual companion or browser workflows.

## Open Decisions

Before implementation, decide whether the production TUI should keep Czech labels, switch to English labels, or provide a lightweight language mode. Also decide whether `rpi_dashboard/tui/modern.py` should be deleted after useful ideas are merged, or retained as a prototype until the new production modules exist.
