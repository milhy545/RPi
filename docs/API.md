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

#### GET /bt/scan?seconds=<5>
Scan Bluetooth devices.

**Parameters**:
- `seconds` (int): Scan duration

**Response**:
```json
{
  "ok": true,
  "devices": [
    {"mac": "00:00:00:00:00:00", "name": "Device", "type": "audio_output"}
  ]
}
```

#### GET /bt/pair?mac=<mac_address>
Pair with Bluetooth device.

**Parameters**:
- `mac` (string, required): Device MAC address

**Response**:
```json
{"ok": true, "output": "Pairing successful"}
```

#### GET /bt/trust?mac=<mac_address>
Trust Bluetooth device.

**Parameters**:
- `mac` (string, required): Device MAC address

**Response**:
```json
{"ok": true, "output": "Trust successful"}
```

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
