# Audio Multi-Mixer and WebUI Plan

## Phase 1: Core Audio Engine Rewrite
- [x] **Task 1**: Identify cause of BT dropouts (codec/bitrate mismatch or idle suspension) and fix in `audio.py` or PipeWire config.
- [x] **Task 2**: Implement the Multi-Mixer architecture (e.g., using `module-combine-sink` or PipeWire node graphs) in `audio.py` to allow any source to any sink mapping with latency compensation.
- [x] **Task 3**: Refactor `/home/milhy777/rpi-dashboard/backend/webserver.py` to expose the new audio routing API.
- [ ] **Task 4**: Rewrite `test_services_audio.py` to reach 100% test coverage on the new routing logic.

## Phase 2: WebUI - Premium Design & Functional UI
- [x] **Task 5**: Design the core layout for the new Audio tab, ensuring premium aesthetics.
- [x] **Task 6**: Implement Basic Mode (horizontal menu, click-to-route UI).
- [x] **Task 7**: Implement Expert Mode (vertical menu, Drag & Drop schematic topology routing).
- [x] **Task 8**: Connect WebUI frontend to the new backend API, ensuring state is synced without heavy polling.

## Phase 3: Integration & Finalization
- [ ] **Task 9**: Update TUI (`tui.py`) to align with the new audio API.
- [ ] **Task 10**: E2E testing of the full stack (UI -> Backend -> PipeWire -> Hardware outputs).
- [ ] **Task 11**: Monitor system resource usage (RAM/CPU) to guarantee RPi stability.
