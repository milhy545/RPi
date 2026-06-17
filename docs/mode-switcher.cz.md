# Přepínač módů

## Popis
`mode_switcher.py` spouští a dohlíží na externí aplikace bez narušení stavu dashboardu.

## Třídy
### `ModeSwitcher`
- `launch(mode)` — spustí aplikaci podle názvu módu
- `stop()` — zastaví běžící aplikaci
- `status()` — vrátí stav aktuální aplikace

## Podporované módy
- `steamlink` — Steam Link
- `gfn` — GeForce Now
- `mpv` — MPV přehrávač
- `spotify` — Spotify
- `amazon` — Amazon Music

## Použití
```python
from mode_switcher import ModeSwitcher
ms = ModeSwitcher()
ms.launch('steamlink')
ms.stop()
```

## Architektura
- Aplikace běží přímo na TV připojeném k RPi
- Dashboard se automaticky vrátí po ukončení aplikace
- `Ctrl+C` ukončí většinu aplikací, `Ctrl+Q` ukončí Steam Link
