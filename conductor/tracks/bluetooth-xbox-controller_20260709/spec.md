# Bluetooth Pairing and Xbox Controller Support

## Problem

Bluetooth pairing is split between WebUI API handlers and direct TUI `bluetoothctl`
commands. This makes behavior inconsistent and hides gamepad-specific readiness
checks needed for Xbox controllers and Steam Link.

## Goals

- Add a top-level Bluetooth surface in both WebUI and TUI.
- Use one shared backend contract for scan, pair, trust, connect, disconnect,
  remove, status, and controller readiness.
- Keep WebUI and TUI wording, roles, status badges, and action order aligned.
- Detect audio devices, generic input devices, gamepads, and Xbox controllers.
- Make Xbox controller setup observable before launching Steam Link.

## Non-Goals

- Do not run browser-based Playwright locally on the 1 GB Raspberry Pi.
- Do not install DKMS/kernel packages or change boot/kernel config without an
  explicit verification step and user awareness.
- Do not move audio routing into Bluetooth; Bluetooth pairs devices, Audio routes
  sinks and streams.

## Acceptance Criteria

- WebUI has a dedicated Bluetooth tab/section reachable from the main menu.
- TUI has a dedicated Bluetooth tab with the same core workflow and labels.
- `/devices/state` and Bluetooth scan results expose normalized devices with
  `mac`, `name`, `kind`, `paired`, `connected`, and `trusted`.
- Pairing actions return useful success/error text and refresh visible state.
- Xbox controllers are classified as `xbox_controller`.
- A controller readiness block reports ERTM status, driver/module hints, connected
  Xbox devices, and Steam Link availability.
- Tests cover normalization, action wrappers, API dispatch, and the new UI hooks.
- Live validation includes service restart, TUI smoke on `tty1`, and non-browser
  WebUI endpoint checks.
