# Specification: Remove Kodi tab from WebUI

## Overview
Kodi is not planned to return to this RPi. Remove the visible Kodi WebUI surface and stop presenting Kodi as a future/diagnostic option. Normal playback remains Player/mpv.

## Functional Requirements
- Remove the Kodi navigation tab and panel from the WebUI.
- Remove Kodi JavaScript launcher/diagnostic UI functions from the active frontend.
- Replace legacy Kodi HTTP endpoints with explicit `410 Gone` JSON responses so accidental callers get a clear message.
- Preserve Player/mpv playback and all other tabs.
- Update tests to assert Kodi UI is absent.

## Acceptance Criteria
- WebUI has no visible Kodi tab or panel.
- `/kodi/status`, `/kodi/st`, and `/play` return clear deprecation JSON.
- Remote Playwright verifies no Kodi tab is visible and other primary tabs still render.
- CI and `tools/verify-done.sh` pass.
