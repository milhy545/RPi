# Implementation Plan: Full-Stack Refactoring

## Overview

7-phase refactoring plan: Backend → Frontend → TUI → Integration → Testing → Open Tracks → Polish.

Each phase has clear deliverables, verification steps, and rollback points.

---

## Phase 1: Backend Foundation — Package Structure & Service Layer

**Goal:** Create `rpi_dashboard/` package with domain modules, establish service layer pattern.

### Tasks

- [ ] **1.1 Create package structure**
    ```
    rpi_dashboard/
    ├── __init__.py
    ├── api/
    │   ├── __init__.py
    │   ├── routes.py          # Route registry
    │   ├── middleware.py       # Auth, rate-limit, CORS
    │   └── handlers.py        # Request handlers
    ├── services/
    │   ├── __init__.py
    │   ├── audio.py           # Audio routing, mixer, DLNA
    │   ├── player.py          # mpv control, playback
    │   ├── devices.py         # BT, WiFi, device management
    │   ├── cec.py             # HDMI-CEC commands
    │   ├── terminal.py        # WebSocket terminal
    │   └── system.py          # HW stats, restart, system info
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py         # Dataclasses for API responses
    └── static/
        ├── index.html         # Main WebUI page
        ├── css/
        │   ├── main.css       # Core styles
        │   ├── themes.css     # Theme variables
        │   └── responsive.css # Media queries
        ├── js/
        │   ├── app.js         # Main app logic
        │   ├── api.js         # API client
        │   ├── i18n.js        # Translations
        │   ├── player.js      # Player tab
        │   ├── audio.js       # Audio tab
        │   ├── devices.js     # Devices tab
        │   ├── cec.js         # CEC tab
        │   └── terminal.js    # Terminal tab
        └── manifest.json      # PWA manifest
    ```

- [ ] **1.2 Extract `services/audio.py`**
    - Move from `webserver.py`: `audio_state()`, `get_audio_matrix()`, `audio_matrix_link()`, `audio_set_volume()`, `audio_set_default()`, all `_sink_*`, `_source_*`, `_loopback_*` helpers
    - Create `AudioService` class with clean interface
    - Add type hints and docstrings
    - Unit tests: `tests/test_services_audio.py`

- [ ] **1.3 Extract `services/player.py`**
    - Move: `mpv_start()`, `mpv_stop()`, `mpv_status()`, `mpv_seek()`, `mpv_volume()`, mpv IPC helpers
    - Create `PlayerService` class
    - Unit tests: `tests/test_services_player.py`

- [ ] **1.4 Extract `services/devices.py`**
    - Move: `devices_state()`, `bluetooth_scan_devices()`, `_bt_paired_devices()`, `_bt_scanned_devices()`, `wifi_status()`, `wifi_scan()`, `wifi_connect()`
    - Create `DeviceService` class
    - Unit tests: `tests/test_services_devices.py`

- [ ] **1.5 Extract `services/cec.py`**
    - Move: CEC scan, power, navigation, volume, input switching functions
    - Create `CECService` class
    - Unit tests: `tests/test_services_cec.py`

- [ ] **1.6 Extract `services/terminal.py`**
    - Move: WebSocket terminal handler, tmux integration
    - Create `TerminalService` class
    - Unit tests: `tests/test_services_terminal.py`

- [ ] **1.7 Extract `services/system.py`**
    - Move: System stats, restart functions, HW monitoring
    - Create `SystemService` class
    - Unit tests: `tests/test_services_system.py`

- [ ] **1.8 Create `api/routes.py`**
    - Route registry with decorators
    - Migrate all endpoints from `webserver.py` do_GET/do_POST
    - Backward compatibility: old paths map to new handlers

- [ ] **1.9 Create `api/middleware.py`**
    - Rate limiting (existing logic extracted)
    - CORS headers
    - IP subnet validation
    - Request logging

- [ ] **1.10 Phase 1 Verification**
    - [ ] All 12 existing tests pass
    - [ ] New service tests pass (>80% coverage)
    - [ ] `python -m rpi_dashboard` starts server
    - [ ] All API endpoints respond correctly
    - [ ] Run `tools/verify-done.sh`

---

## Phase 2: Static File Extraction — WebUI Separation

**Goal:** Extract all HTML/CSS/JS from `webserver.py` into proper static files.

### Tasks

- [ ] **2.1 Extract HTML template**
    - Move `page()` function output to `static/index.html`
    - Template variables become data attributes or JS config
    - Keep i18n object in `static/js/i18n.js`

- [ ] **2.2 Extract CSS**
    - Move inline `<style>` to `static/css/main.css`
    - Create `static/css/themes.css` with CSS custom properties
    - Create `static/css/responsive.css` with media queries

- [ ] **2.3 Extract JavaScript**
    - Move inline `<script>` to modular JS files
    - `static/js/app.js` — Main app, tab switching, utilities
    - `static/js/api.js` — Fetch wrapper, error handling
    - `static/js/player.js` — Player tab logic
    - `static/js/audio.js` — Audio tab logic
    - `static/js/devices.js` — Devices tab logic
    - `static/js/cec.js` — CEC tab logic
    - `static/js/terminal.js` — Terminal WebSocket

- [ ] **2.4 Update `webserver.py` static file serving**
    - Serve `static/` directory
    - Set proper MIME types
    - Cache headers for assets

- [ ] **2.5 Phase 2 Verification**
    - [ ] WebUI loads from static files
    - [ ] All tabs functional
    - [ ] No console errors
    - [ ] Visual regression: screenshots match baseline
    - [ ] Run `tools/verify-done.sh`

---

## Phase 3: WebUI Responsive Design & Themes

**Goal:** Make WebUI fully responsive with theme system.

### Tasks

- [ ] **3.1 Implement CSS Grid layout**
    - Desktop: sidebar + main content
    - Tablet: collapsible sidebar
    - Mobile: bottom tab bar

- [ ] **3.2 Create theme system**
    - CSS custom properties for colors
    - Dark theme (default, current)
    - Light theme
    - Accent color picker (blue, green, purple, orange)

- [ ] **3.3 Theme persistence**
    - Save to localStorage
    - Load on page init
    - System preference detection (prefers-color-scheme)

- [ ] **3.4 Responsive breakpoints**
    - `>1024px`: Desktop layout
    - `768-1024px`: Tablet layout
    - `<768px`: Mobile layout

- [ ] **3.5 Touch-friendly controls**
    - Minimum 44px tap targets
    - Swipe gestures for tabs
    - Pull-to-refresh

- [ ] **3.6 Audio tab responsive**
    - Mixer visualization scales properly
    - Routing controls stack on mobile
    - DLNA latency slider full-width on mobile

- [ ] **3.7 Devices tab responsive**
    - BT scan list scrollable
    - Pair/trust buttons accessible
    - WiFi connect form usable on mobile

- [ ] **3.8 Phase 3 Verification**
    - [ ] Desktop (1920x1080): all tabs perfect
    - [ ] Tablet (768x1024): sidebar collapsible, all functional
    - [ ] Mobile (375x667): tab bar, all functional
    - [ ] Theme switch works, persists
    - [ ] Run `tools/verify-done.sh`

---

## Phase 4: TUI Modernization

**Goal:** Update TUI with modern look, complete Devices/Settings tabs.

### Tasks

- [ ] **4.1 Update TUI theme**
    - Modern color scheme (dark background, accent colors)
    - Better borders and spacing
    - Status indicators with icons

- [ ] **4.2 Complete Devices tab**
    - BT scan list with device names/types
    - Pair/Trust/Remove buttons per device
    - Connection status indicators
    - WiFi network list and connect form

- [ ] **4.3 Complete Settings tab**
    - Audio default sink selector
    - CEC power/bridge toggles
    - System restart buttons (mpv, dashboard, RPi)
    - Language switcher (CZ/EN)

- [ ] **4.4 Add keyboard shortcuts**
    - `r` — Refresh stats
    - `d` — Switch to Devices tab
    - `s` — Switch to Settings tab
    - `q` — Quit
    - `1-4` — Switch tabs

- [ ] **4.5 Real-time device polling**
    - BT device status updates every 5s
    - WiFi connection status
    - Audio sink changes

- [ ] **4.6 Phase 4 Verification**
    - [ ] TUI starts and displays correctly
    - [ ] Devices tab: BT scan shows devices
    - [ ] Devices tab: Pair button works
    - [ ] Settings tab: All controls functional
    - [ ] Keyboard shortcuts work
    - [ ] Run `tools/verify-done.sh`

---

## Phase 5: Comprehensive Testing

**Goal:** Achieve >80% coverage, expand E2E tests.

### Tasks

- [ ] **5.1 Unit tests for all services**
    - `tests/test_services_audio.py` — 15+ test cases
    - `tests/test_services_player.py` — 10+ test cases
    - `tests/test_services_devices.py` — 10+ test cases
    - `tests/test_services_cec.py` — 8+ test cases
    - `tests/test_services_terminal.py` — 5+ test cases
    - `tests/test_services_system.py` — 8+ test cases

- [ ] **5.2 API integration tests**
    - `tests/test_api_routes.py` — All endpoints
    - `tests/test_api_middleware.py` — Rate limit, CORS, auth

- [ ] **5.3 Expand E2E tests**
    - `tests/e2e/webui_tabs.mjs` — Tab navigation
    - `tests/e2e/webui_audio.mjs` — Audio controls
    - `tests/e2e/webui_devices.mjs` — Device pairing
    - `tests/e2e/webui_player.mjs` — Player controls
    - `tests/e2e/webui_responsive.mjs` — Viewport tests
    - `tests/e2e/webui_themes.mjs` — Theme switching

- [ ] **5.4 Visual regression tests**
    - Baseline screenshots for each tab
    - Compare after changes
    - Alert on unexpected differences

- [ ] **5.5 Performance tests**
    - API response time benchmarks
    - Memory usage tracking
    - Load test with concurrent requests

- [ ] **5.6 Phase 5 Verification**
    - [ ] `pytest --cov=rpi_dashboard --cov-report=html` shows >80%
    - [ ] All E2E tests pass
    - [ ] No regressions in existing functionality
    - [ ] Run `tools/verify-done.sh`

---

## Phase 6: Open Track Integration

**Goal:** Implement mpv Auto-Return, BT Stutter Fix, Xbox Controller.

### Tasks

- [ ] **6.1 mpv Auto-Return on EOF**
    - Listen for `eof-reached` event in mpv IPC
    - Trigger clean shutdown sequence
    - Return TUI to dashboard mode
    - Update WebUI player status
    - Unit tests: `tests/test_player_eof.py`

- [ ] **6.2 BT Audio Stutter Diagnosis**
    - Log PipeWire buffer stats
    - Check Wi-Fi/BT frequency overlap
    - Test different A2DP buffer sizes
    - Document findings in `conductor/tracks/refactor-fullstack_20260706/bt-stutter-report.md`

- [ ] **6.3 BT Audio Stutter Fix**
    - Optimize PipeWire quantum/buffer settings
    - Implement adaptive buffer sizing
    - Add user-configurable latency slider
    - Unit tests: `tests/test_audio_bt_buffer.py`

- [ ] **6.4 Xbox Controller Pairing**
    - Install xpadneo driver: `sudo apt install xpadneo-dkms`
    - Configure bluetoothctl ERTM fix
    - Add device type detection in WebUI
    - Test input events with `evtest`
    - Unit tests: `tests/test_devices_xbox.py`

- [ ] **6.5 Phase 6 Verification**
    - [ ] mpv: Play video to end → auto-returns to dashboard
    - [ ] BT audio: 5-minute test, no stuttering
    - [ ] Xbox: Pairs, connects, input works
    - [ ] Run `tools/verify-done.sh`

---

## Phase 7: Polish & Documentation

**Goal:** Final cleanup, documentation, performance optimization.

### Tasks

- [ ] **7.1 Code cleanup**
    - Remove dead code from old `webserver.py`
    - Consolidate duplicate functions
    - Final type hint pass
    - Run `ruff check` and `mypy` — fix all warnings

- [ ] **7.2 Documentation**
    - Update `README.md` with new structure
    - Add `docs/API.md` — endpoint reference
    - Add `docs/ARCHITECTURE.md` — module diagrams
    - Add `docs/DEVELOPMENT.md` — setup, testing, contributing

- [ ] **7.3 Performance optimization**
    - Profile hot paths with `cProfile`
    - Optimize audio state caching
    - Lazy-load static assets
    - Compress JS/CSS (if build system added)

- [ ] **7.4 Security audit**
    - Run `bandit` on all Python code
    - Review input validation
    - Check for hardcoded secrets
    - Verify rate limiting

- [ ] **7.5 Final testing**
    - Full regression suite
    - Manual testing on actual RPi 3B+
    - Test on mobile device (Android/iOS)
    - Test with real BT speakers
    - Test with real CEC adapter

- [ ] **7.6 Phase 7 Verification**
    - [ ] `ruff check` — 0 warnings
    - [ ] `mypy` — 0 errors
    - [ ] `bandit` — 0 high-severity issues
    - [ ] All tests pass
    - [ ] Manual testing checklist complete
    - [ ] Run `tools/verify-done.sh`
    - [ ] Create receipt in `conductor/ci/receipts/`

---

## Rollback Plan

Each phase has a git tag for rollback:
```bash
git tag refactor-phase-1-complete
git tag refactor-phase-2-complete
# etc.
```

If a phase fails verification:
1. Revert to last good tag
2. Analyze failure
3. Fix and re-run phase

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Backend Foundation | 3-4 hours | None |
| Phase 2: Static Extraction | 2-3 hours | Phase 1 |
| Phase 3: Responsive Design | 3-4 hours | Phase 2 |
| Phase 4: TUI Modernization | 2-3 hours | Phase 1 |
| Phase 5: Testing | 2-3 hours | Phases 1-4 |
| Phase 6: Open Tracks | 2-3 hours | Phase 1 |
| Phase 7: Polish | 1-2 hours | All phases |
| **Total** | **15-22 hours** | |

---

## Success Criteria

- [ ] `webserver.py` <300 lines (down from 2906)
- [ ] Each service module <500 lines
- [ ] Test coverage >80%
- [ ] All 7 WebUI tabs fully functional
- [ ] Responsive on desktop/tablet/mobile
- [ ] Theme system with dark/light modes
- [ ] TUI Devices tab functional
- [ ] TUI Settings tab functional
- [ ] mpv auto-return on EOF working
- [ ] BT audio no stuttering
- [ ] Xbox controller pairs and works
- [ ] No regressions in existing functionality
- [ ] Documentation complete
