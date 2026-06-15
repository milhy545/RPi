# Plan: Terminal tab fixes and hardware stats

## Phase 1 — Discovery
- [x] Reproduce cursor and fit issues
- [x] Capture current CPU affinity mask state without interrupting playback
- [x] Identify HDMI audio sink mismatch causing missing HDMI option

## Phase 2 — Design
- [x] Fix xterm sizing/snapshot/cursor handling
- [x] Add CPU mask/status design for mpv, background services, and audio services
- [x] Add safe restart action design for mpv, dashboard, and full RPi

## Phase 3 — Implementation Planning
- [x] Add hardware stats panel for CPU, GPU, RAM, disk, temperatures and frequencies
- [x] Move CPU masks/restart controls from Player Quick to Terminal tab
- [x] Expand WebUI layout width to use browser viewport
- [x] Stage `/system/status` endpoint for CPU mask reporting
- [x] Stage Quick tab CPU mask UI and restart buttons
- [x] Stage HDMI sink constant correction to current PipeWire sink

## Phase 4 — Validation
- [x] Define tests/manual checks before implementation starts
- [x] Confirm no regression to existing playback, audio, devices, and terminal flows
