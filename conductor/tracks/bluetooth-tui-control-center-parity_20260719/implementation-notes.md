# Implementation Notes

## TUI Control Center Parity

- Added `rpi_dashboard/tui/bluetooth_console.py`, a pure renderer for stable Adapter A/B slots, device classification, topology, legend, device tables, quick actions, status, diagnostics, events, help, footer, and compact fallback output.
- Rebuilt the live `tui.py` Bluetooth tab as the reference-shaped full-width topology plus four-column middle and bottom grids.
- Added full `170x48` and compact `85x24` layouts. The full layout uses six fixed 27-character topology zones and does not overlap or scroll.
- Preserved adapter-aware pair, trust, connect, disconnect, remove, scan, and refresh plumbing. `G` and `M` produce explicit visible no-op notices as allowed by the route.
- Added an optional `RPIDASHBOARD_INITIAL_TAB` runtime setting for deterministic tty verification while preserving `tab_player` as the default.
- Added an explicit SIGTERM handler and systemd stop timeout so dashboard restarts exit cleanly instead of hanging.
- Configured tty1 to use `Lat2-Terminus16`, increasing the physical console from `85x24` to `170x48` on the 1360x768 framebuffer.
- Normalized device labels to ASCII and replaced markup-sensitive square brackets in live names, for example `[Samsung]` becomes `(Samsung)`.
- Addressed Codex PR review by prioritizing headset/headphone output evidence over generic `phone` input matching.
- Added a visible `>` target marker, Up/Down target navigation, default/preserved device-key selection, and a matching footer target so full-layout actions never depend on an unreachable hidden selector.
- Reserved the compact layout's final two rows for shortcuts and limited its device summary to two rows; the 85x24 screenshot now shows every advertised action through `[M] Settings`.
- Restored a reachable Trust action with the visible `[T] Trust` command in full and compact layouts and adapter-aware keyboard dispatch.
- Added `fonts-terminus` to fresh-host APT provisioning so the required `Lat2-Terminus16` service precondition is installed before `setfont` runs.

## TUI Verification Evidence

- Focused checks: `uv run ruff check rpi_dashboard/tui/bluetooth_console.py tui.py tests/test_bluetooth_tui_console.py` passed.
- Focused tests: `uv run pytest -q tests/test_bluetooth_tui_console.py tests/test_tui_modern.py -x` reported `20 passed`.
- Full local gateway: `tools/run-ci.sh` reported `191 passed` and wrote `conductor/ci/reports/8c771ff-20260722-001605.md`.
- The new tests cover zero, one, and two adapters; deterministic classification; ASCII-safe output; 170x48 and 85x24 layouts; panel geometry; and `S/P/C/D/X/R/G/M` key behavior with destructive operations mocked.
- A Textual SVG was rasterized and inspected on Milhy-PC at 170x48.
- Physical tty1 capture `/tmp/bluetooth-tui-tty1-final.png` was inspected at 1360x768 and contains the complete reference structure without overlap.
- `/dev/vcs1` confirmed the header, topology, legend, four middle panels, four bottom panels, and one-line footer.
- Live state during tty verification: backend `bluez-dbus`, degraded `false`, 2 adapters, 3 devices.
- `dashboard@milhy777.service` restarted in 2 seconds with `Result=success`; tty1 remained `170x48` and the service/API remained active.
- Post-review physical `/dev/vcs1` verification confirmed the audio-output classification, visible target marker, matching footer target, and `170x48` dimensions.
- Generated screenshots remain runtime artifacts and are not committed.

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

## Final Review Corrections

- Empty A/B adapter placeholders no longer claim the same legacy device when fallback records have no `adapter_id`; unknown devices remain visible only in topology and Available Devices.
- Compact `G`/`M` notices replace the reserved spacer row, keeping the supported `85x24` view at its fixed nine-row height.
- User-configurable adapter aliases are escaped before Rich markup rendering.
- Focused review regression suite: `23 passed` across the Bluetooth console and modern TUI tests, including live Textual geometry at `170x48` and `85x24`.
- Legacy fallback records without a v2 device key now derive a stable selection key from MAC, so navigation, the visible marker, footer target, and actions remain aligned.
- Full mode now starts at its measured `170x38` minimum; widths through 169 columns use the compact renderer.
- Every Bluetooth console panel now follows the live CZ/EN setting and re-renders from the current snapshot on language changes; Czech tty copy is deliberately ASCII-only.
- Adapter aliases use the same ASCII-safe terminal normalization as device labels in addition to Rich markup escaping.
