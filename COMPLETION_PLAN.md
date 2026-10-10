# Plan to Complete backend-modularization-completion_20260723 Track

## Phase 4: Production Visual Redesign (REMAINING)

### WebUI - Remaining Panels to Redesign
- [ ] **Player panel** - Match wireframe: one primary card (URL input, quality, play), status card, quick links
- [ ] **Apps panel** - Match wireframe: clean launch buttons, return hints
- [ ] **Audio panel** - Match wireframe: topology/mixer as primary, controls secondary
- [ ] **Bluetooth panel** - Already has advanced design (Gemini control center), verify parity
- [ ] **Devices panel** - Match wireframe: Wi-Fi/hardware overview, Bluetooth in separate tab
- [ ] **CEC removal from primary nav** - Move to advanced foldout per wireframe
- [ ] **Terminal panel** - Match wireframe: clean connect/disconnect, status
- [ ] **Responsive CSS** - Verify all breakpoints (1024, 768, 480) work for new layout
- [ ] **Accessibility** - ARIA labels, keyboard nav, high contrast

### TUI - Verify & Polish
- [ ] TUI already has correct 8 tabs (Player, Apps, Audio, Bluetooth, Devices, Network, System, Logs)
- [ ] Verify TV-size (2-3m view) layout works
- [ ] Verify constrained-terminal mode works
- [ ] Keyboard/gamepad navigation complete

## Phase 5: Legacy Retirement
- [ ] Verify migration telemetry & compatibility window
- [ ] Remove legacy endpoints in small revertible sets:
  - [ ] `/kodi/*` endpoints (already deprecated with 410)
  - [ ] Legacy inline webserver branches in `webserver.py`
  - [ ] Duplicate audio routing in webserver vs services
- [ ] Update API/client docs with rollback proofs

## Phase 6: Runtime Verification
- [ ] Full test suite: route, service, static, WebUI, TUI, a11y, lint, type, security
- [ ] Verify on RPi: services, ports, endpoints, logs, startup, RAM, CPU
- [ ] Verify remotely on Milhy-PC
- [ ] `tools/verify-done.sh` PASS with receipt

---

## Execution Order
1. Complete WebUI panel redesigns (Player, Apps, Audio, Devices, Terminal, CEC removal)
2. Verify TUI matches wireframes
3. Legacy endpoint removal
4. Full CI verification and receipt