# RPi-TV Dashboard API Reference

## Overview

RESTful API for controlling RPi-TV Dashboard. All endpoints return JSON.

**Base URL**: `http://<RPi-IP>:8080`

## Authentication

No authentication required. IP allowlist enforced (LAN + Tailscale).

## Rate Limiting

- **Limit**: 1 request per second per IP
- **Action endpoints**: Additional rate limiting

## Endpoints

### Audio

#### GET /audio/state
Get current audio state.

**Response**:
```json
{
  "default_sink": "alsa_output.platform-hdmi-audio.0.hdmi-stereo",
  "sinks": [...],
  "sources": [...],
  "devices": {...},
  "routes": {...},
  "latency": {...}
}
```

#### GET /audio/default-sink?name=<sink_name>
Set default audio sink.

**Parameters**:
- `name` (string, required): Sink name

**Response**:
```json
{"ok": true}
```

#### GET /audio/volume?kind=<sink|source>&name=<name>&volume=<0-150>
Set audio volume.

**Parameters**:
- `kind` (string): "sink" or "source"
- `name` (string, required): Device name
- `volume` (int): Volume level (0-150)

**Response**:
```json
{"ok": true, "volume": 100}
```

#### GET /audio/matrix
Get PipeWire audio matrix.

**Response**:
```json
{
  "nodes": {...},
  "links": [...]
}
```

#### GET /audio/matrix/link?out=<node>&in=<node>&state=<0|1>
Link/unlink audio nodes.

**Parameters**:
- `out` (string, required): Output node
- `in` (string, required): Input node
- `state` (string): "1" to link, "0" to unlink

**Response**:
```json
{"ok": true, "out": "linked"}
```

### Player

#### GET /mpv/play?url=<url>&q=<quality>&resume=<0|1>
Start mpv playback.

**Parameters**:
- `url` (string, required): Video URL
- `q` (string): Quality (360p, 480p, 720p, 1080p)
- `resume` (string): "1" to resume from last position

**Response**:
```json
{"ok": true, "pid": 12345}
```

#### GET /mpv/stop
Stop mpv playback.

**Response**:
```json
{"ok": true}
```

#### GET /mpv/status
Get mpv status.

**Response**:
```json
{
  "ok": true,
  "on": true,
  "pos": 120.5,
  "dur": 300.0,
  "paused": false,
  "title": "Video Title",
  "vol": 100,
  "q": "720p"
}
```

#### GET /mpv/seek?position=<seconds>
Seek to position.

**Parameters**:
- `position` (float, required): Position in seconds

**Response**:
```json
{"ok": true}
```

### Devices

#### GET /devices/state
Get devices state.

**Response**:
```json
{
  "bluetooth": {
    "paired": [...],
    "scanned": [...]
  },
  "wifi": {...}
}
```

#### Adapter-aware Bluetooth API

`adapter_id` plus `device_key` is the authoritative device identity. A legacy
`mac` is accepted only when it resolves to exactly one adapter relationship.

| Endpoint | Parameters | Purpose |
| --- | --- | --- |
| `GET /bt/state` | none | Versioned adapters, devices, negotiated capabilities, bounded operations/events, media, OBEX, and settings |
| `GET /bt/discovery` | `action=start|stop`, `adapter_id`, optional `seconds=1..60` | Bounded per-adapter discovery |
| `GET /bt/adapter-power` | `adapter_id`, `powered=0|1` | Power one adapter |
| `GET /bt/discoverable` | `adapter_id`, `discoverable=0|1`, optional `timeout` | Set bounded pair visibility |
| `GET /bt/settings` | optional `auto_connect`, `discoverable_timeout`, `scan_mode` | Persist global policy |
| `GET /bt/device-autoconnect` | `adapter_id`, `device_key`, `enabled=0|1` | Set per-device reconnect opt-out |
| `GET /bt/device-action` | `action=connect|disconnect|trust|untrust|block|unblock|remove|pair`, identity | Run an adapter-scoped action; Pair starts the asynchronous lifecycle |
| `GET /bt/device-profile` | `action=connect|disconnect`, `profile_uuid`, identity | Connect/disconnect an advertised BlueZ profile |
| `GET /bt/operation` | `action=status|cancel`, `operation_id` | Inspect or request cancellation of a bounded backend operation |
| `GET /bt/pairing` | `action=start|status|respond|cancel`, identity or `operation_id`; response may include `accepted` and `value` | Non-blocking confirmation/PIN/passkey pairing lifecycle |
| `GET /bt/media` | `action=play|pause|stop|next|previous|volume`, identity, optional `value=0..127` | Capability-checked AVRCP player/transport action |
| `GET /bt/transfers` | none | OBEX availability, receive-agent state, and bounded transfer history |
| `GET /bt/files` | none | Safe outbound candidates from `~/Downloads` |
| `GET /bt/file-send` | identity, `path` from `/bt/files` | Start adapter-selected Object Push |
| `GET /bt/file-cancel` | `transfer_id` | Cancel an active transfer |
| `GET /bt/device-hid` | identity, `enabled=0|1` | Fail-closed trusted-device HID opt-in boundary |
| `GET /bt/diagnostics` | none | Bounded read-only failure, version, adapter, and resource report |

Legacy `/bt/pair`, `/bt/trust`, `/bt/connect`, `/bt/disconnect`, and
`/bt/remove` routes remain deterministic during migration. `/bt/pair` now
returns a `pairing` lifecycle record rather than blocking an HTTP request while
waiting for a user challenge.

Audio routes used by Bluetooth are `/audio/bluetooth-profiles` for PipeWire card
profile inspection/selection, `/audio/mute-state` for exact sink/source mute,
and `/audio/multi-output` with `action=status|start|sync|stop|reconcile`.

#### GET /wifi/status
Get WiFi status.

**Response**:
```json
{
  "available": true,
  "connected": true,
  "connected_ssid": "MyNetwork",
  "networks": [...]
}
```

#### GET /wifi/scan
Scan WiFi networks.

**Response**:
```json
{
  "ok": true,
  "networks": [
    {"ssid": "Network", "signal": 85, "security": "WPA2"}
  ]
}
```

#### GET /wifi/connect?ssid=<ssid>&password=<password>
Connect to WiFi network.

**Parameters**:
- `ssid` (string, required): Network name
- `password` (string): Network password

**Response**:
```json
{"ok": true, "output": "Connection successful"}
```

### CEC

#### GET /cec/scan
Scan CEC devices.

**Response**:
```json
{"ok": true, "devices": [...]}
```

#### GET /cec/power?action=<on|off>
CEC power control.

**Parameters**:
- `action` (string): "on" or "off"

**Response**:
```json
{"ok": true}
```

#### GET /cec/nav?action=<up|down|left|right|select|back|menu>
CEC navigation.

**Parameters**:
- `action` (string): Navigation action

**Response**:
```json
{"ok": true}
```

### System

#### GET /system/stats
Get system statistics.

**Response**:
```json
{
  "cpu_percent": 45.2,
  "cpu_temp": 52.0,
  "ram": {"used_mb": 512, "total_mb": 1024, "percent": 50},
  "disk": {"total": "32G", "used": "16G", "available": "16G", "percent": "50%"},
  "uptime": "1d 5h 30m"
}
```

#### GET /restart/mpv
Restart mpv player.

**Response**:
```json
{"ok": true, "message": "mpv restarted"}
```

#### GET /restart/dashboard
Restart dashboard service.

**Response**:
```json
{"ok": true, "message": "Dashboard restarting"}
```

#### GET /restart/rpi
Restart Raspberry Pi.

**Response**:
```json
{"ok": true, "message": "Rebooting..."}
```

## Error Responses

All errors return JSON with `ok: false`:

```json
{
  "ok": false,
  "error": "Error message"
}
```

### HTTP Status Codes

- `200`: Success
- `400`: Bad request (missing parameters)
- `403`: Forbidden (IP not allowed)
- `404`: Not found
- `429`: Rate limited
- `500`: Internal server error

## Examples

### Play a video
```bash
curl "http://192.168.0.100:8080/mpv/play?url=https://youtube.com/watch?v=dQw4w9WgXcQ&q=720p"
```

### Get audio state
```bash
curl "http://192.168.0.100:8080/audio/state"
```

### Switch to Bluetooth
```bash
curl "http://192.168.0.100:8080/audio/default-sink?name=bluez_output.00_00_00_00_00_00.a2dp_sink"
```

### Scan WiFi
```bash
curl "http://192.168.0.100:8080/wifi/scan"
```

### Get system stats
```bash
curl "http://192.168.0.100:8080/system/stats"
```
