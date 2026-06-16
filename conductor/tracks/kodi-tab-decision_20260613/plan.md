# Plan: Evaluate Kodi tab usefulness

## Phase 1 — Discovery
- [x] Validate whether Kodi is installed and useful

## Phase 2 — Design
- [x] Document real use cases or decide removal

## Phase 3 — Implementation Planning
- [x] If kept, add guided example and status diagnostics

## Phase 4 — Validation
- [x] Define tests/manual checks before implementation starts
- [x] Confirm no regression to existing playback, audio, devices, and terminal flows

## Decision
Kodi is not installed and JSON-RPC port 9090 is not listening on this RPi. The tab is kept as a diagnostics-only legacy launcher rather than removed, so layout remains stable and future DLNA/Kodi renderer work has a visible status surface. Normal playback remains Player/mpv.

## Verification Evidence
- Local discovery: no `kodi` / `kodi-standalone` binaries, no listener on TCP 9090.
- Local endpoint: `/kodi/status` returns `decision=keep-diagnostics-only`, `useful=false`.
- Remote host: Milhy-PC.
- Remote Playwright target: `https://rpi-tv/`.
- Artifact: `/tmp/rpi-dashboard-webapp-artifacts/webapp-test-kodi-20260616-154600/kodi-diagnostics.png`.
- Browser result: Kodi tab active, diagnostics show `NOT AVAILABLE`, `keep-diagnostics-only`, `not listening`, no console errors.
