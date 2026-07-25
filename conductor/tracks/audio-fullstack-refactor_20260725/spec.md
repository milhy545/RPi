# Track Specification: Audio Full-Stack Refactor

## Overview
Refactor the RPi Dashboard audio domain across backend, WebUI, and TUI:
1. **Backend Modularization**: Split monolihtic `audio.py` (1,136 lines) into structured `rpi_dashboard/services/audio/` package.
2. **WebUI Scaffold Transformation**: Global WebUI shell transformation (Basic horizontal menu vs Expert vertical left sidebar) with status bar, theme/i18n, and integrated Bluetooth/Audio tabs.
3. **Audio WebUI Redesign**: Interactive Audio Flow Topology canvas (Basic click & click, Expert drag & drop), priority node placement for MPV and game streams.
4. **Audio TUI Modernization**: Modern ASCII audio topology flow view in `tui.py`.

## Acceptance Criteria
- All 270+ existing unit and API tests pass without regression.
- `audio/` package preserves public API contract seamlessly.
- WebUI mode switcher toggles global Basic (horizontal tabs) and Expert (vertical sidebar) layouts.
- `tools/verify-done.sh` passes with valid CI receipt.
