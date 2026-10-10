# Multimedia klávesový daemon (keys2mpv.py)

## Popis
`keys2mpv.py` je daemon, který přijímá multimediální klávesy z USB klávesnice a přeposílá je přímo na mpv přes IPC socket.

## Jak funguje
1. Naslouchá na `/dev/input/event*` pro stisknuté klávesy
2. Mapuje multimediální klávesy na mpv příkazy
3. Odesílá příkazy přes Unix socket (`/tmp/rpi-mpv.sock`)

## Mapování kláves
| Klávesa | Příkaz mpv |
|---------|-----------|
| Play/Pause | `cycle pause` |
| Stop | `stop` |
| Next | `seek +30` |
| Previous | `seek -30` |
| Volume Up | `add volume 5` |
| Volume Down | `add volume -5` |
| Mute | `cycle mute` |

## Spuštění
```bash
python3 keys2mpv.py &
```

## Závislosti
- mpv musí běžet s aktivním IPC socketem
- USB klávesnice musí být připojena
- Kernel modul `evdev` musí být dostupný
