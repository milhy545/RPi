# `webserver_8099.py`

## Purpose
This is the main HTTP/WebSocket control plane for the dashboard.

- HTTP: `8099`
- Terminal WebSocket: `8098`
- mpv IPC: `/tmp/gfn-mpv.sock`

## High-level routes

### Player / media
- `GET /mpv/play?url=...&q=...`
- `GET /mpv/stop`
- `GET /mpv/status`
- `GET /mpv/toggle`
- `GET /mpv/seek?d=...`
- `GET /mpv/seekabs?pos=...`
- `GET /mpv/vol?d=...`
- `GET /play?url=...` — legacy Kodi launcher
- `GET /kodi/st`

### CEC
- `GET /cec/send?c=...`
- `GET /cec/key?k=...`
- `GET /cec/in?n=...`
- `GET /cec/scan`
- `GET /cec/br/start`
- `GET /cec/br/stop`
- `GET /cec/br/st`

### Audio
- `GET /audio/state`
- `GET /audio/volume?kind=sink|source&name=...&volume=N`
- `GET /audio/mute?kind=sink|source&name=...`
- `GET /audio/default-sink?name=...`
- `GET /audio/latency?key=dlna_output_offset_ms|default_latency_ms&value=N`
- `GET /audio/bt`
- `GET /audio/hdmi`
- `GET /audio/dlna`
- `GET /audio/route/alexa-bt?action=status|start|stop`
- `GET /dlna/select?name=...&location=...&usn=...`
- `GET /dlna/connect`
- `GET /dlna/disconnect`
- `GET /keepalive?action=status|start|stop|stop_all&sink=...`

### Devices / Wi‑Fi / YouTube
- `GET /devices/state`
- `GET /devices/bt/scan?seconds=...`
- `GET /wifi/status`
- `GET /wifi/scan`
- `GET /wifi/connect?ssid=...&password=...`
- `GET /youtube/cookies/status`
- `GET /youtube/age-check?url=...`

### Self-tests
- `GET /selftest/testaudio`

## Function reference

### Media helpers

#### `norm(u)`
Normalizes URLs by collapsing duplicate slashes in the path.

**Example**
Useful before passing a URL to `yt-dlp` or Kodi.

#### `yt_id(u)`
Extracts a YouTube video ID from common YouTube URL formats.

**Example**
```python
yt_id("https://youtu.be/dQw4w9WgXcQ")
```

#### `resolve(url, q=None)`
Resolves a YouTube or direct URL into a playable URL using `yt-dlp` and the local cookie file.

**Example**
- Paste a YouTube link into the WebUI Player tab.
- The dashboard resolves the stream and hands it to mpv.

#### `kodi_rpc(m, p=None, t=3)`
Sends JSON-RPC to a local Kodi instance on `127.0.0.1:9090`.

**Example**
```python
kodi_rpc("Player.GetActivePlayers")
```

#### `mcmd(*a)`
Sends an IPC command to mpv.

**Example**
```python
mcmd("seek", 30, "relative")
```

#### `mget(p)`
Reads a property from mpv via IPC.

#### `mpv_start(url, q=None)`
Resolves a media URL and starts mpv fullscreen using the IPC socket.

**Example**
```bash
curl 'http://127.0.0.1:8099/mpv/play?url=https://youtu.be/dQw4w9WgXcQ&q=360p'
```

#### `mpv_stop()`
Stops mpv and removes the stale IPC socket if needed.

#### `mpv_st()`
Returns current mpv status for the UI.

### CEC helpers

#### `cec_cmd(cmd)`
Executes a CEC control command.

#### `cec_scan()`
Scans attached HDMI-CEC devices.

#### `br_start()`, `br_stop()`, `br_st()`
Manage the remote-to-mpv bridge.

**Example**
- Use `cec('on 0')` from the UI to power on the TV.
- Use the bridge to let the TV remote control playback.

### Audio helpers

#### `_run(cmd, t=5)`
Shared subprocess wrapper with capture and timeout.

#### `_parse_int(value, field)`
Safe integer parser used for audio input validation.

#### `_pactl_lines(kind)`
Reads `pactl list short ...` output and returns structured rows.

#### `_sink_volume(name)` / `_source_volume(name)`
Read device volume percentages.

#### `_loopback_module_id()`
Finds the active PipeWire/PulseAudio loopback module for Alexa → BT routing.

#### `_paired_bt_device(paired_text, mac=...)`
Parses `bluetoothctl devices Paired` output into a structured BT soundbar record.

#### `_classify_sink(name)` / `_classify_source(name)`
Classify audio devices into HDMI, BT, DLNA, USB input/output, remote input, etc.

#### `_load_audio_latency()` / `_save_audio_latency(data)`
Load/store local JSON latency settings.

#### `_sink_name_by_id(...)`
Map sink-input sink IDs back to sink names.

#### `_sink_input_streams(...)`
Return active sink inputs used by the mixer section.

#### `_audio_state_uncached()`
Build the full audio state snapshot from `pactl`, `bluetoothctl`, and latency JSON.

#### `audio_state(force=False)`
Cached wrapper around the uncached state to reduce repeated hardware queries.

**Example**
- The Audio tab refreshes this endpoint repeatedly without spamming the Pi.

#### `audio_set_volume(kind, name, volume)`
Sets sink/source volume with validation and clamping.

**Example**
```bash
curl 'http://127.0.0.1:8099/audio/volume?kind=sink&name=bluez_output...&volume=80'
```

#### `audio_set_default(name)`
Sets the default output sink.

#### `_apply_dlna_delay()` / `_reset_dlna_delay()`
Apply or reset `mpv audio-delay` compensation for DLNA sync.

#### `audio_set_latency(key, value_ms)`
Persist latency settings and apply them when DLNA is active.

#### `_ensure_silent_wav()`
Creates a silent audio file used by keepalive loops.

#### `_keepalive_start(sink_name)` / `_keepalive_stop(sink_name=None)`
Manage background keepalive audio streams so sinks do not suspend.

#### `_keepalive_orphans()` / `_stop_keepalive_orphans()` / `_keepalive_status()`
Find, stop, and report orphaned keepalive processes.

#### `audio_select_dlna_renderer(name, location, usn="")`
Stores the chosen DLNA renderer in local latency settings.

#### `_pa_dlna_running()` / `_start_pa_dlna()` / `_selected_dlna_sink_name()`
Detect and start the DLNA bridge and map it to the correct sink.

#### `audio_connect_dlna()` / `audio_disconnect_dlna()`
Start or stop DLNA output routing.

#### `audio_keepalive(action, sink=None)`
UI/API control for keepalive streams.

#### `audio_route_alexa_bt(action)`
Start/stop Alexa AUX → BT Soundbar loopback.

**Example**
- Use this route when the USB sound card should feed the Samsung soundbar.

### Devices / Wi‑Fi / YouTube helpers

#### `_bt_kind(name)`
Classify BT devices as speakers, Xbox controllers, or unknown.

#### `_bt_paired_devices()`
Return paired Bluetooth devices.

#### `_bt_scanned_devices()`
Return devices seen by a scan that are not yet paired.

#### `devices_state()`
Returns a combined device snapshot for the Devices tab.

#### `bluetooth_scan_devices(seconds=5)`
Runs a temporary Bluetooth scan and returns paired + discovered devices.

#### `_wifi_nmcli_available()`
Checks whether `nmcli` is available.

#### `wifi_status()`
Returns Wi‑Fi interface status using `nmcli` or `iw`.

#### `wifi_scan()`
Lists visible Wi‑Fi networks.

#### `wifi_connect(ssid, password)`
Connects to a Wi‑Fi network with `nmcli`.

#### `youtube_cookie_status()`
Checks whether the local `yt-cookies.txt` file exists and looks healthy.

#### `youtube_age_check(url)`
Combines `resolve()` and cookie status to diagnose age-restricted playback failures.

### UI helpers

#### `selftest_testaudio()`
Safe validation endpoint for the Audio/Player/Devices WebUI.

#### `page()`
Renders the full HTML/JS WebUI.

### HTTP handler

#### `H.log_message(...)`
Silences default HTTP logging.

#### `H.sj(c, o)`
Sends JSON responses.

#### `H.st(c, b, ct="text/html;charset=utf-8")`
Sends text/HTML responses.

#### `H.do_GET()`
Main route dispatcher for the WebUI API.

#### `H.do_POST()`
Legacy `POST /play` handler.

### WebSocket / startup helpers

#### `term_handler(websocket)`
Terminal relay for the `Terminal` tab.

#### `start_ws_server()`
Starts the terminal WebSocket server.

#### `mpv_ipc_socket_live(path=MSOCK)`
Checks whether an existing mpv IPC socket is alive before unlinking it.

#### `cleanup_stale_mpv_socket()`
Deletes dead sockets only; preserves live playback.

## Real usage examples
- Open the Audio tab and move the default sink to HDMI before a TV app.
- Open Devices and pair a Bluetooth speaker, then return to Audio to route sound.
- Open Player, paste a YouTube URL, and use the cookie status if age-restricted playback fails.
- Use `curl` against `/audio/state` for debugging without opening the UI.

## Notes on the Kodi tab
Kodi is intentionally documented here because it is part of the WebUI. It is a legacy launcher, not the main media path.
