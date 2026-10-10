# Plan: Alexa and DLNA audio routing

## Phase 1 — Discovery
- [x] Map current PipeWire/DLNA/Alexa capabilities

## Phase 2 — Design
- [x] Design routes and UI states

## Phase 3 — Implementation
- [x] Alexa AUX → BT Soundbar route: already fully implemented (start/stop/status)
- [x] DLNA output: scan/select/connect/disconnect — already implemented
- [x] DLNA latency compensation: already implemented
- [x] Improved `taRoute()` error handling with remediation messages
- [x] Improved `taDlnaConnect()` error handling with remediation messages
- [x] Enhanced DLNA Input card: shows detailed requirements and track dependency
- [x] Route status UI: ON/READY/NOT READY badges with module info

## Phase 4 — Validation
- [x] `py_compile` passes for webserver_8099.py
- [x] Selftest (selftest_testaudio) passes with ok: True
- [x] No regression to existing playback, audio, devices, and terminal flows
- [x] DLNA Input marked as PLANNED pending track 1 (dlna-rendering)
