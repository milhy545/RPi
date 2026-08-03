# Conductor Plan: Audio Full-Stack Refactor

## Background
The `audio-fullstack-refactor_20260725` track addresses a comprehensive refactor of the RPi Dashboard audio subsystem. It tackles the current technical debt by breaking down the 1,033-line `rpi_dashboard/services/audio.py` monolith into a modular package architecture, introduces a global master volume API, enhances the WebUI with an Audio Flow Topology canvas, and modernizes the Textual-based TUI with an ASCII flow diagram while keeping diacritic-free Czech strings for TV console compatibility.

## Current implementation status (audited 2026-08-04)
- [x] Modular `rpi_dashboard/services/audio/` package replaces the former monolith and preserves public imports.
- [x] Global master volume service, API route, WebUI slider, and topology canvas are implemented with automated coverage.
- [x] BT volume sync (AVRCP ↔ PipeWire) → transferred to `bt-dbus-resilience_20260804`.
- [x] AVRCP-focused tests → transferred to `bt-dbus-resilience_20260804`.
- [ ] The Textual TUI provides the planned `AudioFlowDiagram` and master-volume layout.
- [ ] TUI-focused tests and target-RPi verification are recorded.

## Phase 1: Backend modularization — DONE
All tasks completed. See implementation history.

## Phase 2: Global master volume API
- [x] Task: In `rpi_dashboard/services/audio/mixer.py`, add `set_global_master_volume(percentage: int) -> None`.
- [x] Task: In `rpi_dashboard/api/audio.py`, add `POST /audio/volume/global` endpoint.
- [ ] Task: In `rpi_dashboard/static/index.html`, add `<input type="range" id="master-volume-slider" min="0" max="100">` to the Audio tab header.
- [ ] Task: In `rpi_dashboard/static/app.js`, add event listener for `#master-volume-slider` → `POST /audio/volume/global`.

## Phase 3: WebUI Audio topology canvas polish
- [ ] Task: In `rpi_dashboard/static/app.js`, update `renderAudioTopology()` to dynamically read multi-mixer state and render source/sink nodes on `#audio-flow-canvas`.
- [ ] Task: In `rpi_dashboard/static/app.js`, update `drawAudioTopoLines()` to correctly draw connections from active source nodes to sink nodes.
- [ ] Task: In `rpi_dashboard/static/app.js`, add logic to synchronize the BT tab volume slider when the Audio tab slider changes (and vice versa).
- [ ] Verify: `uv run ruff check rpi_dashboard/api/audio.py`

## Phase 4: TUI audio modernization with ASCII flow diagram
- [ ] Task: In `rpi_dashboard/tui/tabs/audio.py`, define `AudioFlowDiagram(Widget)` that generates ASCII diagram from `get_multi_output_state()`.
- [ ] Task: In `rpi_dashboard/tui/tabs/audio.py`, replace `#list_audio_sinks` with layout container holding `AudioFlowDiagram` and sink list.
- [ ] Task: In `rpi_dashboard/tui/tabs/audio.py`, add Textual `Slider` for global master volume control.
- [ ] Task: Ensure all new text labels use diacritic-free Czech strings.
- [ ] Verify: `uv run python -m pytest tests/`

## Phase 5: Test coverage
- [ ] Task: In `tests/test_services_audio.py`, add unit tests for `set_global_master_volume`.
- [ ] Task: In `tests/test_testaudio_webui.py`, add assertions for `#master-volume-slider` presence.
- [ ] Verify: `uv run python -m pytest tests/test_services_audio.py tests/test_testaudio_webui.py`

## Phase 6: Full verification gate
- [ ] Task: Run entire test suite — all 312+ tests must pass.
- [ ] Task: Run linting on all modified files.
- [ ] Task: `tools/verify-done.sh`

## Acceptance Criteria
- [ ] `audio/` package preserves public API contract.
- [ ] Global master volume scales all active output sinks proportionally via `POST /audio/volume/global`.
- [ ] WebUI `#audio-flow-canvas` renders multi-mixer topology and handles master volume slider.
- [ ] TUI renders ASCII audio flow diagram with diacritic-free Czech strings.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes

## Transferred to bt-dbus-resilience_20260804
- BT volume sync (AVRCP ↔ PipeWire) — bidirectional sync between `mixer.py` and `bt.py`
- AVRCP-focused unit tests
