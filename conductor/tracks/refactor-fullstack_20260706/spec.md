# Specification: Full-Stack Refactoring — Backend Modularization + WebUI Responsive + TUI Modernization

## Overview

Complete refactoring of the RPi-TV Dashboard system to achieve:
1. **Backend modularization** — Break 2906-line monolithic `webserver.py` into clean, testable modules
2. **WebUI responsive design** — Desktop/tablet/mobile support with theme system
3. **TUI modernization** — Update Textual dashboard with modern look, complete Devices/Settings tabs
4. **Integration of open tracks** — mpv Auto-Return on EOF + BT Audio Stutter fix

## Current State Analysis

### Backend (`webserver.py` — 2906 lines)
- Monolithic file with embedded HTML/CSS/JS (1500+ lines of inline frontend)
- All API handlers, audio routing, device management, CEC, player logic mixed together
- Partial handler extraction started (`handlers.py`, `router.py`) but only 3 routes migrated
- Audio matrix functions added but not modularized

### Frontend (WebUI)
- Single-page app with 7 tabs: Player, Apps, CEC, Kodi, Audio, Devices, Terminal
- All CSS/JS inline in `page()` function — no build system, no separation
- i18n support (CZ/EN) implemented but hardcoded in JS object
- No theme system, no responsive breakpoints
- Clipboard requires HTTPS (working)
- PWA manifest exists

### TUI (`tui.py` — 1274 lines)
- Textual-based with 2 tabs: "Ovládání & Telemetrie", "Zařízení & Nastavení"
- SystemStats widget reads from /proc
- Devices tab incomplete — scan/pair UI not functional
- Settings tab missing most controls
- No theme support, basic styling

### Tests
- 12 unit tests (pytest) — mostly API endpoint tests
- 1 E2E test file (Playwright) — 6 test cases
- No integration tests for audio routing, device pairing
- No visual regression tests

## Functional Requirements

### Backend Modularization
- **FR-B1:** Split `webserver.py` into domain modules: `audio.py`, `devices.py`, `cec.py`, `player.py`, `terminal.py`, `wifi.py`, `system.py`
- **FR-B2:** Create `api/` package with route registration and middleware (auth, rate-limit, CORS)
- **FR-B3:** Extract HTML/CSS/JS into `static/` directory with proper file structure
- **FR-B4:** Implement service layer pattern — handlers call services, services call system tools
- **FR-B5:** Add comprehensive docstrings and type hints to all public functions
- **FR-B6:** Maintain backward compatibility — all existing API endpoints must continue working

### WebUI Responsive Design
- **FR-W1:** Implement CSS Grid/Flexbox layout with responsive breakpoints (desktop >1024px, tablet 768-1024px, mobile <768px)
- **FR-W2:** Create theme system with light/dark modes + accent color selection
- **FR-W3:** Store theme preference in localStorage
- **FR-W4:** Ensure all 7 tabs are fully functional on all screen sizes
- **FR-W5:** Audio section: complete mixer visualization, routing controls, DLNA latency slider
- **FR-W6:** Devices section: Bluetooth scan/pair/trust/remove workflow, WiFi connect, role assignment
- **FR-W7:** Collapsible sidebar on mobile, tab bar navigation
- **FR-W8:** Touch-friendly controls (larger tap targets, swipe gestures)

### TUI Modernization
- **FR-T1:** Update Textual theme with modern color scheme and borders
- **FR-T2:** Complete Devices tab — BT scan list, pair/trust buttons, device status
- **FR-T3:** Complete Settings tab — WiFi config, audio defaults, CEC settings, system restart
- **FR-T4:** Add real-time device status polling
- **FR-T5:** Implement keyboard shortcuts for common actions

### Open Track Integration
- **FR-O1:** mpv Auto-Return on EOF — listen for `eof-reached` event, trigger clean shutdown, return to dashboard
- **FR-O2:** BT Audio Stutter Fix — diagnose PipeWire buffer/Wi-Fi interference, optimize A2DP profile
- **FR-O3:** Xbox Controller Pairing — install xpadneo driver, configure bluetoothctl ERTM fix

## Non-Functional Requirements

### Performance
- **NFR-P1:** API response time <100ms for state endpoints
- **NFR-P2:** WebUI initial load <2 seconds on RPi 3B+
- **NFR-P3:** TUI refresh interval ≤2 seconds for system stats
- **NFR-P4:** Memory usage <50MB for webserver process

### Reliability
- **NFR-R1:** All existing tests must pass after refactoring
- **NFR-R2:** No regression in audio routing, player control, or device management
- **NFR-R3:** Graceful degradation when system tools unavailable (pw-dump, pactl, etc.)

### Maintainability
- **NFR-M1:** Each module <500 lines
- **NFR-M2:** Test coverage >80% for new modules
- **NFR-M3:** Type hints on all public functions
- **NFR-M4:** Docstrings on all public functions and classes

### Security
- **NFR-S1:** No secrets in code (API keys, passwords)
- **NFR-S2:** Input validation on all API parameters
- **NFR-S3:** Rate limiting maintained on all endpoints

## Acceptance Criteria

- [ ] `webserver.py` reduced to <300 lines (HTTP server + route dispatch only)
- [ ] All domain logic in separate modules under `rpi_dashboard/` package
- [ ] HTML/CSS/JS in `static/` directory, served as static files
- [ ] All 12 existing unit tests pass
- [ ] New unit tests for each module (>80% coverage)
- [ ] E2E tests expanded to cover all 7 tabs
- [ ] WebUI responsive on desktop, tablet, mobile viewports
- [ ] Theme system with dark/light modes working
- [ ] Audio tab: mixer, routing, DLNA latency all functional
- [ ] Devices tab: BT scan/pair/trust/remove working
- [ ] TUI Devices tab: BT scan list and pair buttons functional
- [ ] TUI Settings tab: WiFi, audio defaults, restart controls working
- [ ] mpv auto-return on EOF working (video ends → return to dashboard)
- [ ] BT audio stutter resolved (5-minute test without drops)
- [ ] Xbox controller pairs and connects via Bluetooth

## Out of Scope

- **Kodi tab removal** — Already tracked separately
- **New hardware support** — No new device drivers beyond xpadneo
- **Cloud integration** — No cloud sync, remote access beyond current Tailscale
- **Mobile app** — WebUI only, no native iOS/Android app
- **Video transcoding** — mpv only, no server-side transcoding

## Dependencies

- PipeWire/PulseAudio (audio routing)
- BlueZ (Bluetooth management)
- NetworkManager (WiFi)
- CEC adapter (HDMI-CEC)
- mpv (video player)
- Textual (TUI framework)
- Playwright (E2E testing)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing API | High | Backward compatibility layer, comprehensive tests |
| Audio regression | High | Test each routing path manually before merge |
| TUI Textual API changes | Medium | Pin Textual version, check changelog |
| RPi 3B+ performance | Medium | Profile memory/CPU, optimize hot paths |
| BT driver compatibility | Medium | Test xpadneo on actual hardware |
