# Provozní příručky

## Spuštění WebUI
```bash
cd rpi-dashboard
python3 webserver_8099.py &
```
WebUI dostupný na `http://0.0.0.0:8099`

## Spuštění terminálu (WebSocket)
Terminál běží automaticky s WebUI na portu 8098.

## Spuštění TUI dashboardu
```bash
python3 main.py
```

## Zastavení služeb
```bash
# Zastavit WebUI
kill $(pgrep -f webserver_8099.py)

# Zastavit keys2mpv
kill $(pgrep -f keys2mpv.py)
```

## Restart mpv
```bash
# mpv se spouští přes WebUI nebo TUI
# Ruční restart:
pkill mpv
# Pak spusť přes WebUI
```

## Diagnostika
```bash
# Stav audio
pactl list short sinks
pactl list short sources

# Stav Bluetooth
bluetoothctl devices
bluetoothctl devices Paired

# Stav sítě
nmcli device status
nmcli connection show

# Stav WebUI
curl http://localhost:8099/mpv/status
curl http://localhost:8099/audio/state
```

## Logy
```bash
# WebUI logy
tail -f /tmp/rpi_webserver.log

# Systémové logy
journalctl -u rpi-dashboard
```
