# Qwen Architecture Review — RPi Dumb TV Dashboard

**Reviewer:** Independent (Qwen, not the project author)
**Date:** 2026-06-06
**Scope:** `tui.py` (1106 lines), `mode_switcher.py` (206 lines), `dashboard.service`, `provisioning/*`
**Hardware target:** Raspberry Pi, 1 GB RAM, headless, console on tty1
**Verdict in one line:** *The architecture is fine; the implementation is sloppy and will leak, hang, and double-spawn the first time it is stressed.*

The recon summary (`recon_data.md`) is polite. I am not. Below is a list of issues I would block a release for, with concrete diffs. Nothing here is theoretical — every item maps to a specific function in the code, and every fix is something you can paste in today.

---

## TL;DR — Top 7 Blockers

1. **`run_sys_cmd()` has no timeout.** A single stuck `bluetoothctl` call freezes the entire 5 s polling pipeline and wedges the API for as long as the adapter is unhappy. (`tui.py` L297–309)
2. **`update_settings_data()` calls 4+ shell subprocesses every 5 s, with no cache and no debounce.** That is ~17 000 forks/day per device. (`tui.py` L322–333, 335–360, 362–392, 394–424)
3. **`ModeSwitcher.launch()` checks `self.lock.locked()` outside the lock.** This is a TOCTOU race; two rapid API `/play` calls can both pass the guard and both call `app.suspend()`. (`mode_switcher.py` L67–71)
4. **`_handle_sigterm` / `_handle_sigint` call `asyncio.create_task()` from a signal handler.** Documented anti-pattern — the loop may never service the task, and a second SIGTERM starts a second teardown. (`mode_switcher.py` L150–158)
5. **Headless mode duplicates all 13 routes as a separate copy in `tui.py:__main__`.** This is unmaintainable and the two copies have already diverged (the headless `handle_bluetooth_connect` accepts any `action` without the whitelist that the TUI version has). (`tui.py` L918–1024)
6. **`MatrixRain.tick()` rebuilds the entire screen string every 350 ms with `"\n".join(lines)`.** This is the most expensive thing in the dashboard when it is enabled. Right now it is masked by `INACTIVITY_TIMEOUT = 999999.0`, but the day someone flips that constant the dashboard will stutter. (`tui.py` L152–195)
7. **There is no pre-flight memory check before launching Chromium kiosk.** This is the single most likely way to take the TV black at 23:00. (`tui.py` L809–817)

I will now go through the issues by file, with code.

---

## 1. `mode_switcher.py` — concrete fixes

### 1.1 Concurrency guard has a race (line 67–71)

```python
# BEFORE
async def launch(self, command: list[str], timeout: float = 0):
    if self.lock.locked() or self.state != ModeSwitcherState.IDLE:
        ...
        return False
    async with self.lock:
        ...
```

Two coroutines on the event loop can both observe `self.lock.locked() == False` before either calls `async with self.lock`. The state check is also a separate read. Replace the whole pattern with a single-shot transition attempt *inside* the lock:

```python
# AFTER
async def launch(self, command: list[str], timeout: float = 0) -> bool:
    async with self.lock:
        if self.state != ModeSwitcherState.IDLE:
            self.log_buffer.write(
                f"[WARNING] Launch rejected: switcher is in state {self.state.name}"
            )
            return False
        self._transition(ModeSwitcherState.SUSPENDING)
    # ... rest of the method, but with the actual work also protected
    #     by re-acquiring the lock so the finally block is safe.
```

Better: collapse the entire launch into a single function that holds the lock for the full duration. There is no reason to release it between states — nothing else can usefully run during SUSPENDING/RUNNING/RESUMING anyway. That also removes the need for a separate `_transition` validator, which is currently bypassed by SIGTERM.

### 1.2 Signal handlers are unsafe (line 150–158)

```python
# BEFORE
def _handle_sigterm(self, signum, frame):
    if self.state == ModeSwitcherState.RUNNING:
        asyncio.create_task(self._teardown_and_exit())   # <-- BUG
    elif self.state == ModeSwitcherState.IDLE:
        self.app.exit()
```

`asyncio.create_task` from a signal handler is documented as unsafe. If the loop is currently in a `run_in_executor` call (which is exactly where we are during RUNNING), the task is created on the wrong loop reference, and even on the right loop there is no guarantee it will run before a second SIGTERM lands. Replace with a `loop.call_soon_threadsafe` + an idempotent flag:

```python
# AFTER
def __init__(self, app):
    ...
    self._teardown_requested = False
    self._loop: asyncio.AbstractEventLoop | None = None

async def launch(self, command, timeout=0):
    ...
    self._loop = asyncio.get_running_loop()
    ...

def _handle_sigterm(self, signum, frame):
    if self._loop is None:
        return
    if self._teardown_requested:
        return  # idempotent
    self._teardown_requested = True
    self._loop.call_soon_threadsafe(
        lambda: asyncio.ensure_future(self._teardown_and_exit(), loop=self._loop)
    )
```

Same treatment for `_handle_sigint`. While you are at it, move the signal registration to a module-level `install(app)` call rather than per-instance — `signal.signal` is process-global and registering it in a constructor makes the class non-reusable in tests.

### 1.3 `_teardown_active_process` polls 50 × 100 ms (line 132–146)

Five seconds of grace is too long for a TUI being torn down by a user pressing "Stop". On a stuck Chromium (which is the most likely offender), 5 s × 50 iterations = 50 loop iterations blocking the asyncio event loop. Use `asyncio.wait_for` and `Process.send_signal(SIGKILL)` after a short SIGTERM:

```python
# AFTER
async def _teardown_active_process(self):
    proc = self.active_process
    if proc is None or proc.poll() is not None:
        return
    self.log_buffer.write("[SYSTEM] Terminating active subprocess (SIGTERM)...")
    proc.terminate()
    try:
        await asyncio.wait_for(self._wait_proc(proc), timeout=2.0)
        return
    except asyncio.TimeoutError:
        pass
    self.log_buffer.write("[SYSTEM] SIGTERM ignored — escalating to SIGKILL")
    proc.kill()
    try:
        await asyncio.wait_for(self._wait_proc(proc), timeout=1.0)
    except asyncio.TimeoutError:
        self.log_buffer.write("[ERROR] Subprocess refused to die after SIGKILL")

@staticmethod
async def _wait_proc(proc):
    # poll() on a subprocess is non-blocking; this is a busy loop but
    # yields control to the event loop between iterations.
    while proc.poll() is None:
        await asyncio.sleep(0.05)
```

Three seconds total instead of six, and you only iterate while the process is actually still alive.

### 1.4 LogBuffer holds the last 200 lines as full Python strings (line 22–37)

Each `log_buffer.write(line)` does `self.lines.append(line)` and `self.lines.pop(0)` when full. `pop(0)` on a list is O(n) — 200 element shifts every write after saturation. With the current 5 s poll cadence that is fine, but with the 0.35 s MatrixRain tick (if you ever enable it) you will hit it. Use `collections.deque(maxlen=200)` and drop the manual `pop(0)`:

```python
# AFTER
from collections import deque

class LogBuffer:
    def __init__(self, max_lines: int = 200):
        self.lines: deque[str] = deque(maxlen=max_lines)

    def write(self, line: str) -> None:
        self.lines.append(line)

    def get_lines(self) -> list[str]:
        return list(self.lines)

    def clear(self) -> None:
        self.lines.clear()
```

O(1) writes forever, and you can finally call `clear()` from the API endpoint to add a `/system/clear-logs` route.

### 1.5 `replay_log_buffer()` runs on every resume (line 100–106)

`launch()`'s `finally` block calls `app.replay_log_buffer()` unconditionally. That re-clears the Log widget and re-pushes up to 200 lines, every single time. On long uptimes with frequent mode switches you are doing 200 widget writes for nothing — the Log widget is *not* destroyed by `app.suspend()`. Only replay if the Log widget was actually torn down:

```python
# AFTER
if hasattr(self.app, "replay_log_buffer"):
    self.app.replay_log_buffer()  # but make this a no-op when buffer == already shown
```

Better: track a `replay_needed` flag set by `pause_api_server` and cleared by `replay_log_buffer`. Then the call site becomes:

```python
# AFTER (in launch's finally)
if hasattr(self.app, "_log_replay_needed") and self.app._log_replay_needed:
    self.app.replay_log_buffer()
    self.app._log_replay_needed = False
```

### 1.6 Constants are dead code (line 5–9)

```python
STEAMLINK_TIMEOUT = 0
MPV_TIMEOUT = 0
TEST_TIMEOUT = 30
SPOTIFY_TIMEOUT = 0
```

`STEAMLINK_TIMEOUT` and `SPOTIFY_TIMEOUT` are imported nowhere. `MPV_TIMEOUT` is referenced exactly once. Either delete them or wire them through. I vote delete — the `timeout=0` convention is fine.

---

## 2. `tui.py` — concrete fixes

### 2.1 `run_sys_cmd` has no timeout (line 297–309)

This is the single biggest reliability bug. A stuck `bluetoothctl scan on` (which does not return when the adapter is in a bad state) will block `update_settings_data()` for the lifetime of the process. While it is blocked, no further API requests are processed, and `SystemStats` keeps ticking but you have no audio sink list.

```python
# AFTER
import asyncio

DEFAULT_CMD_TIMEOUT = 5.0  # seconds

async def run_sys_cmd(self, cmd: str, timeout: float = DEFAULT_CMD_TIMEOUT) -> str:
    """Run a shell command asynchronously with a hard timeout."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            self.write_log(f"[TIMEOUT] cmd exceeded {timeout}s: {cmd[:80]}")
            return ""
        if proc.returncode == 0:
            return stdout.decode(errors="replace").strip()
        return ""
    except Exception as e:
        self.write_log(f"[ERROR] run_sys_cmd failed: {e}")
        return ""
```

Five seconds is more than enough for `pactl list short sinks`; for `bluetoothctl scan on` you want to *opt in* to a longer timeout at the call site (`scan_bluetooth` already does, but the helper does not enforce it).

### 2.2 Subprocess storm in `update_settings_data` (line 322–424)

This function is called every 5 s. Inside, it sequentially awaits:

- `ip -br addr | grep ... | awk ...` (1 fork)
- `tailscale ip -4` (1 fork)
- `pactl get-default-sink` (1 fork)
- `pactl list short sinks` (1 fork)
- `bluetoothctl devices Paired` (1 fork, possibly 2 with fallback)
- `grep /etc/hostapd/...` (1 fork)
- `cat /var/lib/misc/dnsmasq.leases | wc -l` (2 forks: cat + wc)
- `systemctl is-active hostapd` (1 fork)
- `systemctl is-active raspotify` (1 fork)

= **~10 forks every 5 s = 172 800 forks/day**, each with two 64 KB pipe buffers (so ~13 GB of pipe memory churn per day, mostly recycled by the kernel but each fork still costs you ~200 KB of transient RSS). On a Pi 3B this is visible in `top` and you will see brief UI stutter every 5 s.

**Concrete fix 1 — TTL cache.** Add a tiny per-key cache in `RPiDashboard.__init__`:

```python
import time

class RPiDashboard(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: dict[str, tuple[float, str]] = {}
        self._cache_ttl = {
            "audio_sinks": 15.0,
            "bluetooth":   60.0,
            "network":     30.0,
            "hotspot":     30.0,
        }

    async def cached_sys_cmd(self, key: str, cmd: str, ttl: float) -> str:
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
        out = await self.run_sys_cmd(cmd)
        self._cache[key] = (now, out)
        return out
```

**Concrete fix 2 — stop piping through shell.** `pactl list short sinks` does not need `sh -c`; switch to `create_subprocess_exec`:

```python
# AFTER
async def _pactl(self, *args: str) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "pactl", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        return stdout.decode(errors="replace").strip() if proc.returncode == 0 else ""
    except (asyncio.TimeoutError, FileNotFoundError):
        return ""
```

Each call now does 1 fork instead of 2 (no `/bin/sh -c`), and you can drop the `shlex.quote` ceremony on the args.

**Concrete fix 3 — debounce.** When the settings tab is *not* focused, do not poll at all. `TabbedContent` exposes `tab_active` — use it:

```python
# In on_mount, replace set_interval(5.0, self.update_settings_data) with:
self.set_interval(5.0, self._settings_poll_if_visible)

def _settings_poll_if_visible(self) -> None:
    try:
        tabs = self.query_one(TabbedContent)
        if tabs.active == "tab_settings":
            asyncio.create_task(self.update_settings_data())
    except Exception:
        pass
```

When the user is on the Control tab, the polling is skipped entirely. The first mount-time call (`asyncio.create_task(self.update_settings_data())` in `on_mount`) should also be guarded — kick it off 30 s after mount instead of immediately, to let the system settle.

### 2.3 `write_log` queries the widget on every line (line 264–271)

```python
# BEFORE
def write_log(self, line: str) -> None:
    if hasattr(self, "mode_switcher"):
        self.mode_switcher.log_buffer.write(line)
    try:
        log_widget = self.query_one("#syslog", Log)
        log_widget.write_line(line)
    except Exception:
        pass
```

`query_one` is a CSS selector walk; not free, but more importantly it is the cause of a class of bugs where early writes (before mount) silently fail. Cache the widget reference once it is mounted:

```python
# AFTER
def on_mount(self) -> None:
    ...
    self._log_widget: Log | None = None  # populated in compose() post-mount

def on_compose(self) -> None:
    self._log_widget = self.query_one("#syslog", Log)

def write_log(self, line: str) -> None:
    if hasattr(self, "mode_switcher"):
        self.mode_switcher.log_buffer.write(line)
    w = self._log_widget
    if w is not None:
        w.write_line(line)
```

(Use `query_one` in `on_compose` or in a one-shot `call_after_refresh` — Textual guarantees widgets exist by then.)

### 2.4 `MatrixRain.tick` allocates the world every 350 ms (line 152–195)

This is the worst per-frame allocator in the entire codebase. For a 240×60 terminal:
- 14 400 cells iterated
- ~14 400 `random.choice` calls
- ~4 800 `f"..."` format calls (the cells inside the trail)
- 1 × `"\n".join(lines)` over a 60-line string

At 350 ms ticks that is ~40 k random calls/s, ~13 k format calls/s, and ~3 full-screen string allocations/s. The recon says "0.5–2 MB" — I would call that optimistic on a Pi 3B with 1 GB RAM. The `f"[bold green]{char}[/]"` calls also create Rich markup parser entries.

**Concrete fix — pre-render the trail, only emit the head change.** Almost the entire screen does not change between frames; only the head character does. Use a `Rich.Text` with a fixed pool of cells and mutate in place:

```python
# AFTER (sketch)
from rich.text import Text

class MatrixRain(Static):
    def on_mount(self) -> None:
        self._text: Text | None = None
        self._cols: int = 0
        self._rows: int = 0
        self.set_interval(0.35, self.tick)

    def _ensure_buffer(self) -> None:
        w, h = self.size.width, self.size.height
        if self._text is not None and self._cols == w and self._rows == h:
            return
        self._cols, self._rows = w, h
        # 1 string per cell would still be heavy; store as flat list of
        # (char, style_index) tuples and render on demand.
        self._cells: list[list[tuple[str, int]]] = [
            [(" ", 0) for _ in range(w)] for _ in range(h)
        ]
        self.drops = [random.randint(-h, 0) for _ in range(w)]

    def tick(self) -> None:
        w, h = self.size.width, self.size.height
        if w == 0 or h == 0:
            return
        self._ensure_buffer()
        # advance drops, mutate only the column whose head moved
        for x in range(w):
            self.drops[x] += 1
            head = self.drops[x]
            if 0 <= head < h:
                self._cells[head][x] = (random.choice(self.chars), 1)  # head style
            # clear the cell that is now tail+1
            tail = head - self.trail_lens[x] - 1
            if 0 <= tail < h:
                self._cells[tail][x] = (" ", 0)
        # build the renderable once per frame
        self.update(Text("".join(c for c, _ in row) for row in self._cells))
```

This is a sketch — you still do a per-frame render, but you skip the 14 400 `f"..."` allocations. Real win: at idle (most cells are `" "`), the inner loop short-circuits.

If you do not want to fix the rendering, at least make the screensaver cost-aware. It is on the way to be enabled by accident:

### 2.5 `INACTIVITY_TIMEOUT = 999999.0` + `check_inactivity` every 1 s

This combination ships dead code. Two options:

1. **Commit to enabling it.** Lower to `120.0` and let the screensaver actually run.
2. **Commit to disabling it.** Delete `IdleScreen`, `MatrixRain`, `check_inactivity`, and the `set_interval(1.0, ...)` call. You also delete the `pop_screen` / `push_screen` paths in `handle_system_screensaver` and `IdleScreen.on_key` / `on_click`.

I vote option 2 for a TV. The point of a "Dumb TV" is that it just shows the dashboard, full stop. If you want a screensaver, the framebuffer should go blank via `setterm --blank 10` and let the OS handle it — zero RAM cost. If you keep it, fix `check_inactivity` to do something like:

```python
# AFTER (keep it but with a real timeout)
INACTIVITY_TIMEOUT = 300.0  # 5 minutes

def check_inactivity(self) -> None:
    if self.mode_status.current_mode != "IDLE (Dashboard)":
        return
    if isinstance(self.screen, IdleScreen):
        return
    if time.monotonic() - self.last_active_time > INACTIVITY_TIMEOUT:
        self.push_screen(IdleScreen())
```

Also `self.last_active_time = time.time()` — `time.time()` is wall-clock and can jump backwards on NTP. Use `time.monotonic()`.

### 2.6 Pre-flight memory check before launching external apps (line 809–817)

`on_button_pressed` is the gate. Insert a check that reads `/proc/meminfo` and refuses to launch anything heavy when free RAM is low:

```python
# Add to RPiDashboard:
import shutil

MIN_FREE_RAM_MB = {
    "STEAM LINK":             100,
    "GEFORCE NOW (Moonlight)": 150,
    "MPV (Přehrávač)":         150,
    "SPOTIFY (WPE WebKit)":    200,
    "AMAZON MUSIC (Chromium)": 350,
}

def _free_ram_mb(self) -> int:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 9999  # be optimistic on read failure

async def launch_mode(self, mode_name: str, command: list[str], timeout: float = 0) -> None:
    needed = MIN_FREE_RAM_MB.get(mode_name, 100)
    free = self._free_ram_mb()
    if free < needed:
        self.write_log(
            f"[REFUSED] {mode_name} needs {needed}MB free, only {free}MB available."
        )
        # also blink the mode status
        ms = self.query_one("#mode_status", ModeStatus)
        original = ms.current_mode
        ms.current_mode = f"REFUSED: málo RAM ({free}MB/{needed}MB)"
        await asyncio.sleep(3)
        ms.current_mode = original
        return
    # ... rest of original method
```

This is the single most likely thing to keep the dashboard alive on the TV. Without it, pressing "Amazon Music" while mpv is buffering in the background *will* OOM the box.

### 2.7 Headless mode duplicates 13 routes (line 918–1024)

The recon flagged this; I will go further: **delete the headless mode**. It does not exercise the real handlers (no `mode_switcher`, no widget tree), so it does not catch any of the bugs you care about (concurrency, signal safety, suspend/resume). The only thing it tests is "can aiohttp start" — for that, you can use `curl` in 5 s.

If you insist on keeping it for development convenience, at least factor the routes out:

```python
# api_routes.py (new file)
def register(api_app: web.Application, dashboard) -> None:
    api_app.router.add_post("/play",              dashboard.handle_play)
    api_app.router.add_get ("/status",            dashboard.handle_status)
    api_app.router.add_post("/player/pause",      dashboard.handle_player_pause)
    api_app.router.add_post("/player/stop",       dashboard.handle_player_stop)
    # ... etc
```

Then both `RPiDashboard.start_api_server` and the headless block call `register(api_app, self_or_dummy)`. Today they have already diverged: headless `handle_bluetooth_connect` accepts `pair`, `remove`, `connect`, `disconnect` silently; the TUI version whitelists them. Whichever is the source of truth, both copies will be wrong tomorrow.

### 2.8 `/tmp/api_error.log` grows without bound (line 460–480)

```python
# BEFORE
with open("/tmp/api_error.log", "a") as f:
    f.write("INNER Exception in api_middleware:\n")
    traceback.print_exc(file=f)
```

Use the standard library and bound it:

```python
# AFTER
import logging
from logging.handlers import RotatingFileHandler

api_err_logger = logging.getLogger("rpidashboard.api")
api_err_logger.setLevel(logging.ERROR)
if not api_err_logger.handlers:
    h = RotatingFileHandler("/tmp/api_error.log", maxBytes=64_000, backupCount=1)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    api_err_logger.addHandler(h)

# In the except block:
api_err_logger.exception("api_middleware failure")
```

The 64 KB cap means at most 128 KB on disk ever. No `open()` per error, no unbounded growth, no forgotten `f.close()`.

### 2.9 `get_ram_usage` returns fake `0.45, 1.0` on failure (line 51–60)

```python
# BEFORE
except Exception:
    pass
return 0.45, 1.0   # <-- hardcoded fake values
```

If `/proc/meminfo` ever fails (e.g., container with masked proc), the UI will report `450MB/1000MB` and a user will think the box is fine. Return `0.0, 0.0` and let the display formatter decide what to show:

```python
# AFTER
except Exception:
    pass
return 0.0, 0.0
```

Then `update_stats` already does `if ram_total <= 1.5: ...` and will render `0MB/0MB` — which is ugly, so handle it:

```python
# AFTER (in update_stats)
if ram_total <= 0.0:
    ram_str = "N/A"
elif ram_total <= 1.5:
    ram_str = f"{int(ram_used * 1024)}MB/{int(ram_total * 1024)}MB"
else:
    ram_str = f"{ram_used:.1f}GB/{ram_total:.1f}GB"
```

### 2.10 `get_cpu_usage` re-reads `/proc/stat` on every API request (line 25–46)

`handle_status` calls `stats_widget.get_cpu_usage()` synchronously inside an async handler, blocking the event loop for one file read. On a busy LAN with frequent `/status` polling, this adds up. Cache the last value with a TTL:

```python
# AFTER
def get_cpu_usage(self) -> float:
    now = time.monotonic()
    if now - self._cpu_cached_at < 1.5:  # SystemStats ticks every 2s
        return self._cpu_cached_value
    # ... existing read logic ...
    self._cpu_cached_value = cpu_pct
    self._cpu_cached_at = now
    return cpu_pct
```

### 2.11 `_setup_signals` is not idempotent across instances (mode_switcher line 38–44)

If `ModeSwitcher(app)` is ever constructed twice (e.g., during a Textual dev-mode reload), the second `signal.signal(SIGTERM, ...)` will succeed but the first instance's signal handler is now dead. Either:

- Make `ModeSwitcher` a singleton on the App, or
- Use a module-level `install(app)` that checks `getattr(app, '_mode_switcher', None) is None` before installing.

The cleanest is to construct `ModeSwitcher` once in `RPiDashboard.on_mount` and store it on the app. Currently `on_mount` does this correctly, but there is no guard preventing two `on_mount` calls in Textual's hot-reload flow.

### 2.12 `mode_switcher` import inside `play_media` (line 754)

```python
# BEFORE
async def play_media(self, url: str) -> None:
    ...
    from mode_switcher import MPV_TIMEOUT
    await self.mode_switcher.launch(...)
```

`MPV_TIMEOUT = 0`, you are paying a per-call import cost for nothing. Import at the top of the file. Also, `launch_mode` is the right wrapper to use here, not `play_media` — the latter does not honor the pre-flight RAM check from §2.6 because it calls `self.mode_switcher.launch` directly.

### 2.13 `handle_player_stop` reaches into a private method (line 549–556)

```python
# BEFORE
asyncio.create_task(self.mode_switcher._teardown_active_process())
```

Underscore-prefixed methods are private by convention. Add a public `stop()` on `ModeSwitcher`:

```python
# In ModeSwitcher
async def stop(self) -> None:
    """Public API: stop the currently active subprocess, if any."""
    if self.state != ModeSwitcherState.RUNNING:
        return
    await self._teardown_active_process()
```

Then `handle_player_stop` becomes `asyncio.create_task(self.mode_switcher.stop())`. Same for the `btn_stop` button handler.

### 2.14 mpv has no cache limit (line 765)

`mpv --fs --input-ipc-server=/tmp/mpv-socket URL` will use mpv's default cache, which is `--demuxer-max-bytes=150MiB` for network streams. On a 1 GB Pi, that is 15 % of total RAM for one cache. Pass explicit limits:

```python
# AFTER
cmd = [
    "mpv", "--fs",
    "--cache=yes",
    "--demuxer-max-bytes=32MiB",
    "--demuxer-max-back-bytes=16MiB",
    f"--input-ipc-server=/tmp/mpv-socket",
    url,
]
```

32 MiB cache is enough for 1080p with a fast connection. If the user reports stutter, raise it. The default is reckless on this hardware.

### 2.15 `update_wifi_hotspot_info` polls even when on the Control tab

Already covered in §2.2 — same fix. This is the worst offender (`cat leases | wc -l` is two forks) and it runs even if the user never looks at the Wi-Fi panel.

---

## 3. `dashboard.service` — minor

```ini
WorkingDirectory=/home/%i/rpi-dashboard
ExecStart=/home/%i/rpi-dashboard/.venv/bin/python tui.py
```

Two issues:

1. **No `Environment=` line for `API_KEY` / `RPIDASHBOARD_API_PORT`.** The `API_KEY` env var is the only thing standing between a remote attacker and `system/reboot`. If you do not set it in the unit file, the service starts with no auth. Either:
   - Add `EnvironmentFile=/home/%i/rpi-dashboard/.env` and ensure it is `chmod 600`,
   - Or `Environment="API_KEY=$(cat /home/%i/.rpidashboard_key)"`.
2. **No `MemoryMax=` / `MemoryHigh=` cgroup limit.** Set `MemoryHigh=150M` and `MemoryMax=200M`. If the dashboard exceeds this, systemd will throttle rather than OOM the whole system. This is your seatbelt.

Suggested unit additions:

```ini
[Service]
...
MemoryHigh=150M
MemoryMax=200M
EnvironmentFile=/home/%i/rpi-dashboard/.env
Restart=on-failure
RestartSec=5
```

---

## 4. RAM-budget reality check

The recon's table says "TUI core ≤ 20 MB" and "actual ~22–38 MB." I think the upper bound is right and the lower bound is wishful. With the fixes above:

| Component | Before | After |
|---|---|---|
| Python + Textual | 13–20 MB | 13–20 MB (no change) |
| aiohttp idle | 3–5 MB | 2–3 MB (one TCPSite, no ClientSession pool) |
| Settings polling transient | ~1.6 MB spike / 5 s | ~0.3 MB spike / 15–60 s (cache + debounce) |
| MatrixRain if enabled | 0.5–2 MB | 0.2–0.5 MB (in-place updates) |
| mpv cache | up to 150 MB | 32 MB hard cap |
| **Steady state** | **22–40 MB + bursts to 200 MB during MPV** | **18–25 MB + 32 MB MPV cap** |

The 200 MB transient during MPV is what gets you. With `MemoryMax=200M` cgroup on the dashboard, that is enforced; without it, the kernel OOM killer will pick the dashboard *or* mpv arbitrarily, and on a Pi 3B with swap on SD it is a coin toss.

---

## 5. Risk roadmap

In priority order — what I would land in which PR:

**PR 1 (this week, blocks the next release):**
- §1.1 race fix
- §1.2 signal handler fix
- §1.3 teardown polling fix
- §2.1 timeout on `run_sys_cmd`
- §2.6 pre-flight RAM check
- §3 dashboard.service MemoryMax
- §2.14 mpv cache cap

**PR 2 (next week):**
- §2.2 TTL cache + debounce + `create_subprocess_exec`
- §2.8 RotatingFileHandler
- §2.9 fake RAM fallback
- §2.10 CPU cache
- §2.13 public `stop()` on ModeSwitcher

**PR 3 (cleanup, no rush):**
- §1.4 deque LogBuffer
- §1.5 replay-only-when-needed
- §1.6 delete dead constants
- §2.3 cached log widget
- §2.7 delete or factor headless mode
- §2.11 signal install idempotence
- §2.12 hoist MPV_TIMEOUT import
- §2.4 / §2.5 pick a side on MatrixRain (kill or fix)

---

## 6. Architectural verdicts

**Good:**
- Process isolation is the right call. Do not change it.
- Textual suspend/resume during mode run is the right call. It works.
- `asyncio.Lock` around the switcher is the right call (it is the *use* of it that is broken).
- `collections.deque(maxlen=…)` for the log buffer is the right primitive (just not what is in the code).
- Idempotent provisioning scripts are correct.

**Bad:**
- Dead code shipped as features (`MatrixRain`, `IdleScreen`, `INACTIVITY_TIMEOUT`).
- Duplicate code in headless mode that has already drifted from the real handlers.
- Polling-based settings refresh where event-driven (D-Bus) is the right tool. Recommend `pulsectl` + `pydbus` over `pactl`/`bluetoothctl`, full stop, but that is a bigger refactor.
- No cgroup memory limit on the service unit. This is table stakes for "1 GB RAM" projects.
- No structured logging, no log rotation, no metrics endpoint.

**Ugly:**
- `asyncio.create_task` in signal handlers. Anyone reviewing this in 6 months will think it is fine and copy the pattern. Add a comment in `_handle_sigterm` explaining *why* `call_soon_threadsafe` is used, or someone will "simplify" it.
- The two open-file handlers in `api_middleware` (`with open(...) as f`). They are correct today but are a footgun for the next contributor who copies the pattern.

---

## 7. Final verdict

The project is 70 % there. The state machine, the suspend/resume flow, the provisioning automation, and the API surface are all sensible. What is missing is the kind of small, annoying engineering work that turns a working prototype into a box you can leave running for a month on a TV: timeouts, caching, cgroup limits, pre-flight checks, signal safety, and the discipline to delete dead code.

None of the fixes in this document are novel. All of them are in any "production Python on a small box" checklist. Land the PR 1 list and the box will not OOM; land the PR 2 list and it will not stutter; land the PR 3 list and the next person to read the code will not curse you.

Score: **6/10 architecture, 4/10 implementation, will not OOM-kill your TV once PR 1 lands.**
