## Background
The `audio-fullstack-refactor_20260725` track addresses a comprehensive refactor of the RPi Dashboard audio subsystem. It tackles the current technical debt by breaking down the 1,033-line `rpi_dashboard/services/audio.py` monolith into a modular package architecture. Additionally, it resolves a synchronization bug between PipeWire and Bluetooth AVRCP volumes, introduces a global master volume API, enhances the WebUI with an Audio Flow Topology canvas, and modernizes the Textual-based TUI with an ASCII flow diagram while keeping diacritic-free Czech strings for TV console compatibility. All 312 existing tests must continue to pass on this memory-constrained (1 GB RAM) environment.

## Phase 1: Backend modularization (split audio.py into package)
- [ ] Task: Create directory `rpi_dashboard/services/audio/` and rename the existing `rpi_dashboard/services/audio.py` to `rpi_dashboard/services/audio/_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/state.py` and move the functions `parse_pactl_output`, `get_sinks`, `get_sources`, `get_active_sink` from `_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/mixer.py` and move `set_sink_volume`, `set_sink_mute`, `toggle_sink_mute` from `_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/matrix.py` and move `parse_pipewire_nodes`, `parse_pipewire_links`, `manage_loopback` from `_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/multi_output.py` and move `enable_multi_output`, `disable_multi_output`, `get_multi_output_state` from `_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/keepalive.py` and move `start_keepalive`, `stop_keepalive`, `is_keepalive_running` from `_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/profiles.py` and move `set_card_profile`, `get_card_profiles` from `_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/latency.py` and move `apply_latency_offset`, `get_latency_offset` from `_legacy_audio.py`.
- [ ] Task: Create `rpi_dashboard/services/audio/__init__.py`. Import and re-export all functions from `state`, `mixer`, `matrix`, `multi_output`, `keepalive`, `profiles`, and `latency` to ensure 100% backward compatibility for existing imports like `from rpi_dashboard.services.audio import get_sinks`.
- [ ] Task: Delete `rpi_dashboard/services/audio/_legacy_audio.py`.
- [ ] Verify: `uv run python -m pytest tests/test_services_audio.py`

## Phase 2: BT volume sync + global master volume API
- [ ] Task: In `rpi_dashboard/services/audio/mixer.py`, modify `set_sink_volume(sink_id, volume)` to check if `sink_id` is a Bluetooth device, and if so, call BlueZ D-Bus AVRCP `org.bluez.MediaTransport1.Volume` to sync the volume.
- [ ] Task: In `rpi_dashboard/services/bt.py`, modify the BT volume setter function to import and call `set_sink_volume` from `rpi_dashboard.services.audio` so PipeWire is updated when AVRCP changes.
- [ ] Task: In `rpi_dashboard/services/audio/mixer.py`, add a new function `set_global_master_volume(percentage: int) -> None` that fetches all active output sinks and scales their volumes proportionally based on the provided percentage.
- [ ] Task: In `rpi_dashboard/api/audio.py`, add a new endpoint `POST /audio/volume/global` that parses a JSON body `{"volume": <int>}` and calls `set_global_master_volume(volume)`.
- [ ] Verify: `uv run python -m pytest tests/test_services_audio.py`

## Phase 3: WebUI Audio topology canvas polish + volume sync UI
- [ ] Task: In `rpi_dashboard/static/index.html`, add `<input type="range" id="master-volume-slider" min="0" max="100">` to the top of the Audio tab header.
- [ ] Task: In `rpi_dashboard/static/app.js`, add an event listener for `#master-volume-slider` that dispatches a `POST` request to `/audio/volume/global` on change.
- [ ] Task: In `rpi_dashboard/static/app.js`, update `renderAudioTopology()` to dynamically read the multi-mixer state and render source/sink nodes on `#audio-flow-canvas`.
- [ ] Task: In `rpi_dashboard/static/app.js`, update `drawAudioTopoLines()` to correctly draw connections from active source nodes to sink nodes.
- [ ] Task: In `rpi_dashboard/static/app.js`, add logic to synchronize the existing BT tab volume slider when the Audio tab slider changes (and vice versa) using DOM state updates.
- [ ] Verify: `uv run ruff check rpi_dashboard/api/audio.py`

## Phase 4: TUI audio modernization with ASCII flow diagram
- [ ] Task: In `rpi_dashboard/tui/tabs/audio.py`, define a new Textual widget class `AudioFlowDiagram(Widget)` that generates an ASCII diagram representation based on `get_multi_output_state()`.
- [ ] Task: In `rpi_dashboard/tui/tabs/audio.py`, replace the basic `#list_audio_sinks` option list with a new layout container holding both `AudioFlowDiagram` and the sink list.
- [ ] Task: In `rpi_dashboard/tui/tabs/audio.py`, add a Textual `Slider` widget for the global master volume control.
- [ ] Task: In `rpi_dashboard/tui/tabs/audio.py`, ensure all new text labels use diacritic-free Czech strings (e.g., "Hlavni hlasitost" instead of "Hlavní hlasitost", "Topologie audia" instead of "Topologie audia").
- [ ] Verify: `uv run python -m pytest tests/`

## Phase 5: Test coverage to 100% on new routing logic
- [ ] Task: In `tests/test_services_audio.py`, add unit tests for `set_global_master_volume` to ensure it proportionally scales multiple sinks correctly.
- [ ] Task: In `tests/test_services_audio.py`, add mock tests verifying that `set_sink_volume` triggers the D-Bus AVRCP call for Bluetooth devices.
- [ ] Task: In `tests/test_testaudio_webui.py`, add assertions to check for the presence of `#master-volume-slider` in the HTML structure.
- [ ] Verify: `uv run python -m pytest tests/test_services_audio.py tests/test_testaudio_webui.py`

## Phase 6: Full verification gate
- [ ] Task: Run the entire test suite to guarantee all 312+ tests pass without regression.
- [ ] Task: Run linting tools on all modified files in `rpi_dashboard/`.
- [ ] Task: Run the track verification script.
- [ ] Verify: `tools/verify-done.sh`

## Acceptance Criteria
- [ ] The `rpi_dashboard/services/audio.py` monolith is completely replaced by the `rpi_dashboard/services/audio/` package.
- [ ] Bluetooth AVRCP volume and PipeWire sink volume are bidirectionally synchronized.
- [ ] Global master volume scales all active output sinks proportionally via `POST /audio/volume/global`.
- [ ] WebUI `#audio-flow-canvas` renders multi-mixer topology and handles master volume slider inputs.
- [ ] TUI renders an ASCII audio flow diagram and uses exclusively diacritic-free Czech strings.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes
