# AGENTS.md – Raspberry Pi Dashboard

## Commands
- `uv sync` – install dependencies.
- `uv run python main.py` – CLI entry prints “Hello from rpi!”.
- `uv run python tui.py` – start Textual UI (API on port 8090, can be changed via `RPIDASHBOARD_API_PORT`).
- `uv run python test_dashboard.py` – run UI test suite (uses `RPIDASHBOARD_TEST_COMMAND` for test command, default `sleep 999`).
- `python webserver_8099.py` – headless API server on port 8099 (use `--headless` with `tui.py` for same effect).
- `bash chroot-mount.sh` / `bash chroot-umount.sh` – mount/unmount ignored `rootfs/` chroot.

## Environment
- `RPIDASHBOARD_API_PORT` – overrides UI API port (default 8090). Must be set before launching `tui.py`.
- `API_KEY` – if set, API requires `X-API-Key` header.
- `RPIDASHBOARD_TEST_COMMAND` – command used by `test_dashboard.py` (default `sleep 999`).

## UI Elements (IDs)
- Buttons: `btn_steamlink`, `btn_gfn`, `btn_mpv`, `btn_spotify`, `btn_amazon`, `btn_stop`, `btn_restart_padlna`, `btn_scan_bluetooth`, `btn_disconnect_bluetooth`.
- Widgets: `#mode_status` (current mode), `#syslog` (log widget, also writes to `/home/milhy777/dashboard.log`).

## ModeSwitcher
- States: `IDLE`, `SUSPENDING`, `RUNNING`, `RESUMING`.
- Concurrency guard: launches rejected unless state is `IDLE`.
- Watchdog: `ModeSwitcher.launch(command, timeout)` aborts after `timeout` seconds (default none) and logs a warning.
- SIGINT/SIGTERM: graceful termination of subprocess and state reset to `IDLE`.

## RAM Guard (TUI)
- `MIN_FREE_RAM_MB` per mode (e.g., `STEAM LINK`: 100 MB, `MPV`: 150 MB, `SPOTIFY`: 200 MB, `AMAZON MUSIC`: 350 MB). Launch aborted if insufficient RAM.

## Fallbacks
- Missing binaries (`steamlink`, `cage`, `mpv`, `cog`, `moonlight-qt`) cause UI to fall back to `nano` or `top` and log a warning.

## Logging
- UI logs to `/home/milhy777/dashboard.log` and to the `#syslog` widget.
- `ModeSwitcher` keeps a `LogBuffer` of recent log lines for replay after UI suspension.

## API
- Endpoints: `/play`, `/status`, `/player/pause`, `/player/stop`, `/player/volume`, `/player/seek`, `/audio/sinks`, `/audio/select`, `/bluetooth/devices`, `/bluetooth/connect`, `/wifi/networks`, `/wifi/connect`, `/system/reboot`, `/mode/launch`, `/mode/stop`.
- All responses include `Access-Control-Allow-Origin: *`.
- API runs on `0.0.0.0:<API_PORT>` (default 8090) or 8099 in headless mode.

## Chroot
- `rootfs/` is ignored by Git; do not commit it.
- `chroot-mount.sh` mounts `$ROOTFS_DIR` to `rootfs/`; `chroot-umount.sh` must be run before leaving workspace.

## Test Harness
- `test_dashboard.py` sets `RPIDASHBOARD_TEST_COMMAND` and uses `RPiDashboard.run_test()` for UI automation.
- Press `w` → watchdog test (`sleep 999` with 5 s timeout), `c` → crash test (`false`), `g` → concurrency guard test (two concurrent launches).

## Misc
- Project uses Python 3.12, `uv` for package management, `Textual` for UI, `aiohttp` for API server.
- Code follows 4‑space indentation, `snake_case` for functions/variables, `PascalCase` for classes, `ALL_CAPS_WITH_UNDERSCORES` for constants.
