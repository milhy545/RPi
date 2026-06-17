# Implementation Plan: HTTP fallback with HTTPS clipboard banner

## Phase 1 — UI
- [x] Add security banner markup and styles
- [x] Add JavaScript to choose HTTP fallback vs HTTPS secure state
- [x] Add bilingual strings for banner text/buttons

## Phase 2 — Verification
- [x] Update WebUI tests
- [x] Verify HTTP and HTTPS states with remote Playwright
- [x] Run finish pipeline
- [x] Run `tools/verify-done.sh`

## Verification Evidence
- System hostname changed from `rpi` to `rpi-tv`; `/etc/hosts` updated to `127.0.1.1 rpi-tv rpi`.
- Tailscale hostname set to `rpi-tv`; MagicDNS verified as `rpi-tv.tailb42db0.ts.net`.
- Remote host: Milhy-PC.
- Remote Playwright target URLs: `http://rpi-tv/`, `https://rpi-tv/`, `https://rpi-tv.local/`, `https://rpi-tv.tailb42db0.ts.net/`.
- Artifact: `/tmp/rpi-dashboard-webapp-artifacts/webapp-test-banner-rpi-tv-20260616-134810/`.
- HTTP result: no redirect, fallback banner shown, `Open HTTPS` link points to `https://rpi-tv/`, secure context false.
- HTTPS result: secure banner shown, secure context true, Clipboard API present, quality `720p`, no console errors.
