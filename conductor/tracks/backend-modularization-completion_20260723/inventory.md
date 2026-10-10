# Legacy Surface Inventory — backend-modularization-completion_20260723

## Current runtime owners

- `webserver.py` — production HTTP/HTTPS/WebSocket server; still owns the bulk of request dispatch and several legacy inline route branches.
- `tui.py` — production Textual dashboard; also contains a separate `--headless` aiohttp API copy.
- `rpi_dashboard/api/routes.py` + `rpi_dashboard/api/handlers.py` + `rpi_dashboard/services/*` — modular service path already in place for many endpoints.
- `rpi_dashboard/tui/modern.py` — prototype surface only; not the production TUI.

## Visible production surfaces

- WebUI: `rpi_dashboard/static/index.html` served by `webserver.py`.
- Live TUI: `tui.py`.
- Terminal WebSocket: `WS_PORT` in `webserver.py`.
- Headless test server: `tui.py --headless` (kept for automated tests, not the production dashboard).

## Legacy / compatibility routes still present

`rpi_dashboard/api/routes.py` no longer exposes active `legacy_webserver_endpoint` registrations for the migrated route set. The helper still exists for future retirement batches and telemetry, but the current registry points the migrated paths directly at API handlers.

### Still owned inline by `webserver.py`

`webserver.py` still contains direct `if/elif` branches for the migrated behaviors as compatibility fallbacks. Registry-first dispatch now routes the active API surface through the service/API layer, so these inline branches are now bypassed for normal requests.

### Duplicate headless API surface in `tui.py --headless`

The headless test server currently re-declares its own aiohttp routes instead of reusing the shared API registry:

- `/`
- `/index.html`
- `/manifest.json`
- `/favicon.ico`
- `/play`
- `/status`
- `/player/pause`
- `/player/stop`
- `/player/volume`
- `/player/seek`
- `/audio/sinks`
- `/audio/sinks/select`
- `/bluetooth/devices`
- `/bluetooth/connect`
- `/wifi/networks`
- `/wifi/connect`
- `/system/reboot`
- `/system/screensaver`
- `/mode/launch`
- `/mode/stop`

## In-repository consumers

- `rpi_dashboard/static/js/app.js` — browser UI actions.
- `tests/test_api_dispatch.py` — route registry coverage and legacy route characterization.
- `tests/test_production_api.py` — headless API smoke checks.
- `tests/test_webserver.py` — URL helpers and server behavior.
- `tests/e2e/*.mjs` — browser automation against the WebUI.
- `README.md`, `AGENTS.md`, `conductor/*` — operator-facing startup and workflow references.

## Initial migration notes

- Modern handlers already exist for many Bluetooth, audio, MPV, device, CEC, and system behaviors.
- The remaining work is to move runtime ownership out of `webserver.py`/`tui.py` branches into explicit service/API boundaries, then retire compatibility branches in small sets.
- `python -m rpi_dashboard` should resolve to the supported production server entrypoint, not the prototype TUI.
