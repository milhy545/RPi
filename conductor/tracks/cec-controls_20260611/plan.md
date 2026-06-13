# Implementation Plan: CEC Controls

## Phase 1: Core CEC Commands
- [x] Task: Implement cec-ctl wrapper in webserver_8099.py
  - Power On: `--image-view-on` (fixed from `--text-view-on`)
  - Power Off: `--standby`
  - Navigation: `--user-control-pressed` with key mapping
  - Volume: `--user-control-pressed` with volume-up/down/mute
  - Input: `--active-source phys-addr=1.0.0.0`

## Phase 2: WebUI Integration
- [x] Task: Add CEC tab to webUI with buttons for all commands
- [x] Task: Implement JavaScript handlers (cec(), cecKey(), cecIn(), cecScan())

## Phase 3: Bridge Daemon
- [x] Task: Implement cec-client bridge in webserver
  - Spawn `cec-client -s -d 1 -p 0` as subprocess
  - Map TV remote keys to mpv IPC commands
  - Auto-restart on crash (while True loop with 2s delay)

## Phase 4: WebUI Bridge Controls
- [x] Task: Add Bridge Start/Stop button with status indicator
- [x] Task: Add bridge status polling

## Phase 5: Validation
- [x] Test all CEC commands via webUI
- [x] Test bridge: TV remote controls mpv playback
- [x] Test bridge auto-restart after crash
- [x] Conductor - User Manual Verification 'cec-controls'