# Conductor Plan: Backend Modularization Completion

## Background
Phases 1–3 of the backend modularization are completed (Ownership/inventory, Information architecture, and Backend extraction). The WebSocket terminal and audio modules have been successfully extracted to services, and legacy endpoints are delegated via `get_route()`.

## Current implementation status (audited 2026-08-04)
- [x] Phases 1–3: Backend extraction complete.
- [x] Routes delegated via `get_route()` in `rpi_dashboard/api/routes.py` (106 GET + 3 POST routes).
- [x] POST routes registered: `/report`, `/return`, `/wifi/connect` via `get_post_route()`.
- [x] `handlers.py` decoupled from `webserver.py` (no direct imports except lazy wifi_connect).
- [x] Dead `legacy_webserver_endpoint` and `LEGACY_ROUTE_*` variables removed from routes.py.
- [x] **do_GET cleaned: 565 → 89 lines.** Removed ~476 lines of inline elif handlers that duplicated registry routes.
- [x] Remaining 18 inline větve are utility/deprecated endpoints not in registry: `/`, `/favicon.ico`, `/manifest.json`, `/ws/token`, `/cache/*`, `/pool/*`, `/play`, `/kodi/*`, `/selftest/testaudio`, `/audio/test`, `/system/reboot`.
- [x] webserver.py reduced from 3394 → 2896 lines (-498 lines).
- [x] All 702 tests pass.
- [ ] Phase 4: Production visual redesign (WebUI/TUI) — remains as future work.
- [ ] Phase 6: Full verification gate with `tools/verify-done.sh`.

## What was done today (2026-08-04)
1. Added POST route registry and `get_post_route()` to routes.py.
2. Added `handle_post_report`, `handle_post_return`, `handle_post_wifi_connect` to handlers.py.
3. Updated `do_POST` to use `get_post_route()` for `/wifi/connect`, `/report`, `/return`.
4. Removed `import webserver` from handlers.py `handle_media_preview`.
5. Removed dead code: `legacy_webserver_endpoint`, `LEGACY_ROUTE_*`, `_legacy_route_name` from routes.py.
6. **Rewrote do_GET: removed all 64 inline elif branches that duplicated registry routes.**
7. Removed 2 dead legacy tests, fixed 2 test mocks for new import paths.

## Acceptance Criteria
- [x] Routes delegated via `get_route()` / `get_post_route()`.
- [x] `handlers.py` decoupled from `webserver.py`.
- [x] Dead code removed.
- [x] do_GET reduced from 565 → 89 lines.
- [x] webserver.py reduced from 3394 → 2896 lines.
- [x] All 702 tests pass.
- [ ] Phase 4–6 complete (future work).
