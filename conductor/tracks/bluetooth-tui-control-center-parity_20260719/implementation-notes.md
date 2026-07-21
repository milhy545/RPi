# Implementation Notes

## Completed Scope

- Ported the saved Gemini WebUI prototype into the production Bluetooth WebUI tab using local static HTML/CSS/JS.
- Preserved the prototype design shape: top navigation, Basic/Expert mode, sidebars, topology canvas, cyan Adapter A/audio side, green Adapter B/IO side, controls, filters, hardware gauges, device detail, quick actions, summary, and responsive desktop/tablet/mobile behavior.
- Added real WebUI actions for scan, pair, trust, connect, disconnect, remove, adapter power, mode/theme/language, filters, topology zoom/reset, export, and planned no-op placeholders where backend support does not exist yet.
- Fixed BlueZ operation routing so fallback state does not cause D-Bus calls against invalid empty object paths.
- Added focused tests for Bluetooth backend fallback delegation and WebUI static shape.
- Added Playwright E2E scripts:
  - `tests/e2e/bt_webui_test.mjs` for deterministic mocked BT WebUI design/click coverage.
  - `tests/e2e/bt_webui_real_rpi_test.mjs` for real Milhy-PC browser testing against the live RPi WebUI.

## Real Hardware Evidence

Live RPi adapters tested:

- `adapter-b827ebe11e89` / `B8:27:EB:E1:1E:89`
- `adapter-001a7dda710a` / `00:1A:7D:DA:71:0A`

Real destructive API test results were saved to:

- `/tmp/bt-real-api-report.json`

The real API test executed against both adapters:

- discovery start
- discovery stop
- power off
- power on
- pair
- trust
- connect
- disconnect
- remove

All reported `ok=true`.

Final live state after testing:

- both adapters powered `true`
- both adapters discovering `false`
- device count `8`

## E2E Evidence

Milhy-PC mocked design/click E2E:

- `TARGET_URL=http://127.0.0.1:18090 node tests/e2e/bt_webui_test.mjs`
- Result: `Bluetooth WebUI E2E passed with 34 mocked BT requests`

Milhy-PC real browser to RPi WebUI:

- `TARGET_URL=http://192.168.0.205:8090 node tests/e2e/bt_webui_real_rpi_test.mjs`
- Result: `REAL_RPI_WEBUI_BT_E2E passed nodes=8 quick=8`

Remote screenshot artifacts on Milhy-PC:

- `bt-real-desktop.png`
- `bt-real-tablet.png`
- `bt-real-mobile.png`
- `bt-real-clicked-all.png`

## Local Verification

- `node --check rpi_dashboard/static/js/app.js`
- `node --check tests/e2e/bt_webui_test.mjs`
- `node --check tests/e2e/bt_webui_real_rpi_test.mjs`
- `uv run python -m pytest tests/test_bluetooth_service_api.py tests/test_static_assets.py -q` -> `13 passed`
- `uv run ruff check` -> `All checks passed`
- `uv run python -m pytest -q` -> `156 passed`

## Notes

- The live backend can still report `bluetoothctl` degraded state when BlueZ D-Bus state temporarily falls back. Operations now remain functional because the BlueZ backend delegates to fallback operations when fallback state is active.
- During one real browser run, the Power Off click completed but no adapter remained off by the time state was checked; the separate destructive API test verified power off/on on both adapters successfully.
