# Textual Dashboard (tui.py)

## Popis
`tui.py` je hlavní Textual dashboard — TUI rozhraní běžící přímo v terminálu na RPi.

## Třídy
### `Dashboard(App)`
Hlavní aplikace s komponovanými panely.

### `PlayerPanel`
Panel pro přehrávání YouTube/mpv.
- `action_play()` — spustí přehrávání z inputu
- `action_stop()` — zastaví přehrávání
- `action_pause()` — pozastaví/pokračuje

### `AudioPanel`
Panel pro správu zvuku a směrování.
- Výstupy vlevo, vstupy vpravo
- Přepínání mezi BT/HDMI/DLNA
- Kompenzace DLNA zpoždění

### `DevicesPanel`
Panel pro Bluetooth párování a Wi‑Fi správu.

### `TerminalPanel`
Integrovaný terminál s podporou tmux.

## Klávesové zkratky
- `q` — ukončit
- `p` — play/pause
- `s` — stop
- `left/right` — seek ±10s
- `up/down` — volume ±5%

## Spuštění
```bash
python3 main.py
```

## Poznámky
- TUI běží na RPi, ne na TV
- WebUI (port 8099) je primární rozhraní pro ovládání z TV
