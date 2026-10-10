# Baseline Capture — backend-modularization-completion_20260723

## Remote WebUI capture

Captured on Milhy-PC against the live Pi WebUI at `http://100.82.217.17:8080` with Playwright screenshots in:

- `/home/milhy777/Develop/RPi/tests/e2e/artifacts/baselines`

### Captured viewports / states

- `desktop-home.png`
- `desktop-player.png`
- `desktop-audio.png`
- `desktop-bluetooth.png`
- `desktop-devices.png`
- `desktop-terminal.png`
- `tablet-home.png`
- `tablet-player.png`
- `tablet-audio.png`
- `tablet-bluetooth.png`
- `tablet-devices.png`
- `tablet-terminal.png`
- `mobile-home.png`
- `mobile-player.png`
- `mobile-audio.png`
- `mobile-bluetooth.png`
- `mobile-devices.png`
- `mobile-terminal.png`
- `tv-home.png`
- `tv-player.png`
- `tv-audio.png`
- `tv-bluetooth.png`
- `tv-devices.png`
- `tv-terminal.png`

## Remote TUI capture

Captured on Milhy-PC with a pseudo-TTY session:

- `/tmp/rpi-tui-baseline.log`

The log contains the initial Textual render and the idle dashboard state, including the Czech/English header, player tab, and idle metrics.

## Repeatable capture commands

### WebUI screenshots

```bash
cd /home/milhy777/Develop/RPi/tests/e2e
node capture-baselines.mjs
```

### TUI text baseline

```bash
cd /home/milhy777/Develop/RPi
script -q -c "timeout 6s .venv/bin/python tui.py" /tmp/rpi-tui-baseline.log
```
