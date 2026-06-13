# `tui.py`

## Purpose
The main interactive dashboard, built with Textual, used for control, telemetry, settings, and app launching.

## Top-level objects

### `API_PORT`
Environment-driven HTTP API port, default `8090`.

### `SystemStats`
Telemetry widget showing live CPU, RAM, temperature, and IP address.

**Methods**
- `on_mount()` — initialize caches and start periodic updates
- `get_cpu_usage()` — compute CPU usage from `/proc/stat`
- `get_ram_usage()` — compute RAM used/total from `/proc/meminfo`
- `get_cpu_temp()` — read CPU temperature from `/sys/class/thermal/...`
- `get_local_ip()` — resolve the current local LAN IP
- `update_stats()` — render the formatted telemetry line

**Example**
The top dashboard panel shows: CPU %, RAM, temperature, and IP address.

### `ModeStatus`
Shows the current dashboard/app mode.

**Method**
- `render()` — format the current mode string

**Example**
Displays `IDLE (Dashboard)` while no app is active.

### `RPiDashboard`
The main Textual `App`.

**Methods**
- `compose()` — build the UI layout and tabs
- `write_log(message)` — append a message to file and the live log widget
- `replay_log_buffer()` — restore log history after suspension
- `pause_api_server()` — pause incoming API activity while an app is running
- `resume_api_server()` — resume API activity after recovery
- `on_mount()` — initialize runtime state and background tasks
- `run_sys_cmd(...)` — execute a system command safely
- `update_settings_data()` — refresh the settings page state
- `update_network_info()` — refresh network information
- `update_audio_sinks()` — refresh audio sink state
- `update_bluetooth_devices()` — refresh Bluetooth device list
- `update_wifi_hotspot_info()` — refresh hotspot status
- `restart_padlna()` — restart the audio casting bridge
- `scan_bluetooth()` — scan for nearby BT devices
- `disconnect_all_bluetooth()` — disconnect all BT devices
- `on_switch_changed(...)` — handle UI switch toggles
- `on_option_list_option_selected(...)` — handle option list selection
- `set_audio_sink(...)` — change the default sink from the TUI
- `on_unmount()` — cleanup on exit
- `start_api_server()` — start the aiohttp control server
- `api_middleware()` — middleware for API handling
- `add_cors_headers()` — attach CORS headers
- `handle_play(...)` — start playback from a URL
- `handle_status()` — return current dashboard status
- `send_mpv_ipc(...)` — send raw mpv IPC commands
- `handle_player_pause()` — toggle pause
- `handle_player_stop()` — stop playback
- `handle_player_volume()` — change volume
- `handle_player_seek()` — seek relative
- `handle_audio_get_sinks()` — list sinks
- `handle_audio_select_sink()` — select a sink
- `handle_bluetooth_get_devices()` — return BT devices
- `handle_bluetooth_connect()` — connect a BT device
- `handle_wifi_get_networks()` — list Wi‑Fi networks
- `handle_wifi_connect()` — connect to Wi‑Fi
- `handle_system_reboot()` — reboot the system
- `handle_mode_launch()` — launch a predefined app mode
- `handle_mode_stop()` — stop the active mode/app
- `play_media()` — start media playback workflow
- `on_key()` — keyboard shortcuts for playback control
- `run_watchdog_test()` — verify watchdog timeout handling
- `run_crash_test()` — verify crash recovery
- `run_concurrency_test()` — verify concurrent launch rejection
- `_free_ram_mb()` — internal RAM helper
- `launch_mode()` — helper for selected mode launch
- `on_button_pressed()` — handle sidebar/button actions

## Real usage examples
- Start `uv run python tui.py` to open the full dashboard.
- Use the **Audio** controls to pick HDMI vs BT without leaving the TV UI.
- Press keyboard media keys while a video is playing; `on_key()` routes them to mpv.
- Use the test buttons to verify watchdog and crash recovery without touching real media.

## Notes on the settings tab
The settings layout is intentionally broad: audio sink selection, Bluetooth status, Wi‑Fi/hotspot, and Tailscale/network information are grouped so the user can fix connectivity from the same screen.
