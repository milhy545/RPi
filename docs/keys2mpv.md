# `keys2mpv.py`

## Purpose
Background daemon that reads a hardware input device directly and sends multimedia key events to mpv over IPC.

## Hardware behavior
- Input device: `/dev/input/event2`
- mpv sockets tried in order:
  1. `/tmp/gfn-mpv.sock`
  2. `/tmp/mpv-socket`

## Function reference

### `find_socket()`
Returns the first existing mpv IPC socket path, or `None` if mpv is not running.

**Example**
- Pressing a multimedia key while mpv is active uses the live socket automatically.

### `mpv_cmd(cmd_list)`
Sends a command list to mpv via IPC.

**Example**
```python
mpv_cmd(["cycle", "pause"])
```
This toggles pause/play.

### `mpv_get(prop)`
Reads a property from mpv via IPC.

**Example**
```python
print(mpv_get("time-pos"))
```
Useful for showing the current playback position after a key press.

### `graceful_exit(sig, frame)`
Handles SIGTERM/SIGINT and exits cleanly.

### `main()`
Opens the input device and continuously reads key events.

## Key map
- `164` → Play/Pause
- `163` → Next / +30s
- `165` → Previous / -30s
- `114` → Volume down
- `115` → Volume up
- `113` → Mute

## Real usage examples
- Press the hardware Play/Pause button while a video is playing.
- Tap Volume+ on the remote to raise mpv volume without touching the TV UI.
- Use Next/Prev buttons to skip around while the TV dashboard is hidden.
