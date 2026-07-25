# Implementation Plan: Multi-Output Audio Distribution for BT Source & MPV

## Phase 1: Core Audio Service Extension (`rpi_dashboard/services/audio.py`)
- [x] Task: Generalize output sink discovery to include HDMI and non-BlueZ sinks
  - [x] Modify `_bluetooth_output_sinks()` -> `_available_output_sinks()` to include HDMI stereo (`alsa_output.platform-3f902000.hdmi.hdmi-stereo`) alongside `bluez_output.*`
  - [x] Update `audio_multi_output()` validation logic to allow mixed sink types (HDMI + BT speakers)
  - [x] Adjust loopback creation parameters (`latency_msec=50`) for BT input sources (`bluez_input.*`) for stutter-free buffering
  - [x] Run focused unit test `pytest tests/test_services_audio.py`

## Phase 2: MPV Player Integration (`webserver.py` & `rpi_dashboard/services/player.py`)
- [x] Task: Remove hardcoded HDMI reset from `mpv_start()` in `webserver.py`
  - [x] Ensure `mpv_start()` respects the current PipeWire default sink instead of forcing `alsa_output.platform-3f902000.hdmi.hdmi-stereo`
  - [x] Ensure HDMI card profile is active without forcing single-sink fallback when multi-output is active
  - [x] Run focused unit tests `pytest tests/test_api_dispatch.py` and `pytest tests/test_static_assets.py`

## Phase 3: Anti-Stutter & Performance Hardening
- [x] Task: Audit and set PipeWire buffer parameters
  - [x] Set PipeWire quantum baseline to 1024 for audio stability on RPi 3B+
  - [x] Verify CPU Core 3 pinning for `pipewire` and `wireplumber` services
  - [x] Verify CPU Cores 1-2 pinning for `mpv` process

## Phase 4: System Verification & Integration
- [x] Task: Verify unit tests & RPi CI requirements
  - [x] Run full test suite: `pytest`
  - [x] Run RPi CI verification script: `./tools/verify-done.sh`

## Completion
- [x] Acceptance criteria verified
- [x] Required project completion gate passed (`./tools/verify-done.sh`)
