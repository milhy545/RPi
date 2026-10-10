# Specification: Audio Tab Refactoring Prototype

## Goal
Refine the `🧪 Test Audio` WebUI tab into a safer, clearer audio control panel before replacing the stable `Audio` tab.

## Requirements
- Keep the original `Audio` tab untouched until user approval.
- Show real PipeWire device state for HDMI, BT Soundbar, and USB input.
- Make BT Soundbar pairing/connection state visible.
- Do not encourage starting Alexa → BT loopback when the BT sink is missing.
- Keep route actions explicit and safe.
- Validate with local API checks and syntax checks before restart.

## Acceptance Criteria
- [ ] `/audio/state` returns structured device state.
- [ ] `🧪 Test Audio` shows paired BT Soundbar status.
- [ ] `🧪 Test Audio` offers Connect only when BT is paired but sink missing.
- [ ] Alexa → BT route card warns when BT sink is missing.
- [ ] Existing `Audio` tab remains available.
- [ ] Python syntax check passes.
- [ ] Webserver restart is done only if mpv is not running.
