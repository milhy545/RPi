# Spec: Audio Replacement, Devices Route, and YouTube Age Diagnostics

## Goal
Promote the hardened audio prototype into the primary WebUI Audio tab, add a Devices tab for pairing/connectivity, and add safe YouTube cookie/age-verification diagnostics.

## Requirements
- Replace the old stable Audio tab with the improved audio panel after tests pass.
- Preserve the approved Audio layout: output sinks left, input sources right.
- Add debounced volume sliders to avoid excessive `pactl` calls on Raspberry Pi 3.
- Cache `/audio/state` briefly with a lock to reduce repeated `pactl`/Bluetooth pressure.
- Keep safe and mutating audio tests separated.
- Add a WebUI Devices tab for Bluetooth pairing/connect/trust/remove and Wi-Fi scan/status/connect.
- Devices tab must support speakers and Xbox controllers at pairing level; detailed speaker routing remains in Audio.
- Add YouTube cookie status and age-check endpoints without exposing cookie values.
- Document/clarify the Kodi tab purpose.

## Acceptance Criteria
- Python syntax checks pass.
- Extracted WebUI JavaScript passes `node --check`.
- Safe WebUI E2E test passes.
- Live `/selftest/testaudio` returns `ok: true`.
- `/audio/state` supports concurrent smoke requests.
- New endpoints return JSON safely: `/devices/state`, `/wifi/status`, `/youtube/cookies/status`.
- Old separate Test Audio tab is removed from navigation; improved Audio tab remains.
