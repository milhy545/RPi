# Utility skripty

## Přehled
Projekt obsahuje několik pomocných skriptů pro správu a diagnostiku.

## Klíčové utility

### `keys2mpv.py`
Daemon pro převod multimediálních kláves na mpv příkazy. Viz [keys2mpv.cz.md](./keys2mpv.cz.md).

### `mode_switcher.py`
Modul pro spouštění a zastavování externích aplikací. Viz [mode-switcher.cz.md](./mode-switcher.cz.md).

### `webserver_8099.py`
WebUI server s kompletním API. Viz [webserver-8099.cz.md](./webserver-8099.cz.md).

## Pomocné příkazy
```bash
# Kontrola mpv socketu
ls -la /tmp/gfn-mpv.sock

# Kontrola audio stavu
pactl info | grep "Default Sink"

# Bluetooth diagnostika
bluetoothctl show

# Wi-Fi diagnostika
nmcli device wifi list
```
