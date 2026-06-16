# Implementation Plan: Player paste button inside URL input

## Phase 1 — Implementation
- [x] Move paste button inside URL input wrapper before quality selector
- [x] Remove duplicate paste icon from i18n/rendering
- [x] Preserve manual overwrite, auto no-overwrite, preview, and 720p default

## Phase 2 — Verification
- [x] Run local syntax/unit checks
- [x] Run remote Playwright visual/DOM verification via webapp-testing
- [x] Run Conductor finish pipeline
- [x] Run `tools/verify-done.sh`

## Verification Evidence
- Remote host: Milhy-PC
- Target URL: `http://192.168.0.205:8099/`
- Artifact: `/tmp/rpi-dashboard-webapp-artifacts/webapp-test-20260616-104550/player-url-row.png`
- DOM checks passed: paste button parent is `.url-wrap`, visually within `#url`, before `#qual`, text is single `📋`, quality is `720p`, no console errors.
