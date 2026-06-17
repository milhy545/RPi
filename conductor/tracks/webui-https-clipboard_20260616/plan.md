# Implementation Plan: HTTPS WebUI for clipboard support

## Phase 1 — Setup
- [x] Add HTTPS configuration constants and certificate paths
- [x] Add self-signed certificate generation helper

## Phase 2 — Server
- [x] Start HTTPS server alongside existing HTTP server
- [x] Preserve terminal WebSocket and existing HTTP behavior

## Phase 3 — Verification
- [x] Add/update tests for HTTPS markers
- [x] Verify HTTP and HTTPS locally
- [x] Verify HTTPS Player UI and clipboard API via remote Playwright
- [x] Run finish pipeline and verify-done

## Verification Evidence
- Local HTTP: `http://127.0.0.1:8099/` OK.
- Local HTTPS: `https://127.0.0.1:8443/system/https-info` OK with self-signed cert.
- Remote Playwright host: Milhy-PC.
- Remote target: `https://192.168.0.205:8443/` with `ignoreHTTPSErrors`.
- Artifact: `/tmp/rpi-dashboard-webapp-artifacts/webapp-test-https-20260616-130908/https-player-url-row.png`.
- Browser result: `protocol=https:`, `secureContext=true`, `clipboardApi=true`, paste button inside URL input, quality `720p`, no console errors.
