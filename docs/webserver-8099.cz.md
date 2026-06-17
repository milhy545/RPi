# WebUI / API Server (webserver_8099.py)

## Popis
`webserver_8099.py` je hlavní WebUI server běžící na portech **8099** (HTTP) a **8098** (WebSocket terminál).

## Technologie
- Python `http.server.ThreadingHTTPServer`
- WebSocket přes knihovnu `websockets`
- mpv ovládání přes IPC Unix socket
- PulseAudio přes `pactl`
- Bluetooth přes `bluetoothctl`
- Wi-Fi přes `nmcli`
- YouTube přes `yt-dlp`

## Záložky WebUI

### 🎬 Player
- Přehrávání YouTube a přímých URL přes mpv
- Ovládání play/pause/stop/seek/volume
- Rychlé testovací URL (Rick Astley, Gangnam)
- **YouTube Age/Cookies** diagnostika

### 🚀 Apps
- Spouštění: Steam Link, GeForce Now, MPV, Spotify, Amazon Music
- Tlačítko STOP pro návrat do dashboardu

### 📺 CEC
- Ovládání TV přes HDMI-CEC
- Power on/off, Volume, Navigation, Input switching
- Remote→MPV Bridge pro ovládání mpv přes TV ovladač

### 📦 Kodi
- Legacy JSON-RPC launcher pro lokální Kodi na `127.0.0.1:9090`
- Pouze pokud Kodi běží jako renderer

### 🔊 Audio
- Výstupní zařízení (vlevo): HDMI, BT Soundbar, DLNA, USB
- Vstupní zdroje (vpravo): Alexa USB, Remote Mic, DLNA Input
- Mixer — aktivní streamy
- Směrování: Alexa AUX → BT Soundbar (PipeWire loopback)
- DLNA Latency Compensation
- Diagnostika a raw JSON

### 🧩 Zařízení
- **Bluetooth**: Párování, připojení, důvěřování, odebírání
- **Wi‑Fi**: Klient, Access Point, Ad-hoc režimy
- Doporučené role zařízení

### 💻 Terminál
- tmux-backed terminál přes WebSocket
- Připojení/odpojení

## API Routy

### MPV
| Rpopis | Popis |
|--------|-------|
| `GET /mpv/play?url=...&q=...` | Spustí přehrávání |
| `GET /mpv/stop` | Zastaví přehrávání |
| `GET /mpv/toggle` | Play/Pause toggle |
| `GET /mpv/status` | Stav přehrávače |
| `GET /mpv/seek?d=10` | Seek relativní |
| `GET /mpv/seekabs?pos=60` | Seek absolutní |
| `GET /mpv/vol?d=10` | Změna hlasitosti |

### Audio
| Rpopis | Popis |
|--------|-------|
| `GET /audio/state` | Kompletní audio stav |
| `GET /audio/volume?kind=sink&name=...&volume=80` | Nastavení hlasitosti |
| `GET /audio/mute?kind=sink&name=...` | Přepnout ztlumení |
| `GET /audio/default-sink?name=...` | Nastavit výchozí výstup |
| `GET /audio/latency?key=...&value=...` | Nastavit latenci |
| `GET /audio/bt` | Přepnout na Bluetooth |
| `GET /audio/hdmi` | Přepnout na HDMI |
| `GET /audio/dlna` | Přepnout na DLNA |

### DLNA
| Rpopis | Popis |
|--------|-------|
| `GET /dlna/scan` | Skenovat DLNA rendery |
| `GET /dlna/select?name=...&location=...` | Vybrat DLNA cíl |
| `GET /dlna/connect` | Připojit DLNA |
| `GET /dlna/disconnect` | Odpojit DLNA |

### Bluetooth
| Rpopis | Popis |
|--------|-------|
| `GET /bt/scan` | Skenovat BT zařízení |
| `GET /bt/pair?mac=...` | Spárovat zařízení |
| `GET /bt/connect?mac=...` | Připojit zařízení |
| `GET /bt/disconnect?mac=...` | Odpojit zařízení |
| `GET /bt/trust?mac=...` | Důvěřovat zařízení |
| `GET /bt/remove?mac=...` | Odebrat zařízení |

### Wi-Fi
| Rpopis | Popis |
|--------|-------|
| `GET /wifi/status` | Stav Wi-Fi |
| `GET /wifi/scan` | Skenovat sítě |
| `GET /wifi/connect?ssid=...&password=...` | Připojit se k síti |
| `GET /wifi/ap/start?ssid=...&password=...` | Spustit Access Point |
| `GET /wifi/ap/stop` | Zastavit Access Point |
| `GET /wifi/ap/status` | Stav AP |
| `GET /wifi/adhoc/start?ssid=...&channel=...` | Spustit Ad-hoc |
| `GET /wifi/adhoc/stop` | Zastavit Ad-hoc |
| `GET /wifi/adhoc/status` | Stav Ad-hoc |

### YouTube
| Rpopis | Popis |
|--------|-------|
| `GET /youtube/cookies/status` | Stav cookies |
| `GET /youtube/age-check?url=...` | Kontrola věkového omezení |

### Kodi
| Rpopis | Popis |
|--------|-------|
| `GET /play?url=...` | Poslat URL do Kodi |
| `GET /kodi/st` | Stav Kodi přehrávače |

### Systém
| Rpopis | Popis |
|--------|-------|
| `GET /selftest/testaudio` | Selftest audio komponent |
| `GET /devices/state` | Stav zařízení |
| `GET /devices/bt/scan?seconds=6` | Skenovat BT zařízení |
| `GET /system/reboot` | Restart RPi |

## Interní funkce

### Audio správa
- `_pactl_lines(what)` — parsování pactl výstupu
- `audio_state()` — kompletní audio stav pro WebUI
- `audio_set_volume(kind, name, vol)` — nastavení hlasitosti
- `audio_set_default(name)` — nastavení výchozího výstupu
- `audio_route_alexa_bt(action)` — PipeWire loopback pro Alexa→BT

### DLNA
- `_pa_dlna_running()` — kontrola DLNA spojení
- `audio_select_dlna_renderer()` — výběr DLNA cíle
- `audio_connect_dlna()` — připojení DLNA
- `audio_disconnect_dlna()` — odpojení DLNA
- `audio_keepalive(action, sink)` — správa keepalive procesů

### Wi-Fi
- `wifi_status()` — stav připojení
- `wifi_scan()` — skenování sítí
- `wifi_connect(ssid, pw)` — připojení k síti
- `wifi_ap_start(ssid, pw)` — spuštění AP (hostapd + dnsmasq)
- `wifi_ap_stop()` — zastavení AP
- `wifi_ap_status()` — stav AP
- `wifi_adhoc_start(ssid, ch)` — spuštění Ad-hoc (IBSS)
- `wifi_adhoc_stop()` — zastavení Ad-hoc
- `wifi_adhoc_status()` — stav Ad-hoc

### YouTube
- `youtube_cookie_status()` — kontrola cookies
- `youtube_age_check(url)` — ověření věkového omezení

## Spuštění
```bash
python3 webserver_8099.py
# WebUI: http://0.0.0.0:8099
# Terminal WS: ws://0.0.0.0:8098
```
