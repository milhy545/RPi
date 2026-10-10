# Implementation Plan: Remove Kodi tab from WebUI

## Phase 1 — UI removal
- [x] Remove Kodi tab button and panel markup
- [x] Remove active Kodi JS functions/initializers

## Phase 2 — Backend deprecation
- [x] Return explicit deprecation JSON for legacy Kodi routes
- [x] Preserve non-Kodi playback routes

## Phase 3 — Verification
- [x] Update tests
- [x] Run local checks
- [x] Run remote Playwright verification
- [x] Run finish pipeline and verify-done

## Verification Evidence
- Local WebUI test passes and asserts Kodi tab/panel absent.
- Remote host: Milhy-PC.
- Remote target: `https://rpi-tv/`.
- Artifact: `/tmp/rpi-dashboard-webapp-artifacts/webapp-test-remove-kodi-20260616-183918/no-kodi-tabs.png`.
- Browser result: visible tabs are Player, Apps, CEC, Audio, Devices, Terminal; no Kodi tab/panel; `/kodi/status` returns `410 Gone` with `deprecated=true`; no unexpected console errors.
