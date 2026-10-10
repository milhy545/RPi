# Specification: Zero-Overhead Mode Switcher Engine

## Goal
Implement a generic, clean backend engine that allows the dashboard TUI to suspend itself (releasing the terminal screen and standard inputs), spawn a full-screen hardware-accelerated subprocess (such as SteamLink or MPV), and resume the TUI dashboard's state upon subprocess completion.

## Requirements
1. **TUI State Management:** Use Textual's native `with self.suspend():` context manager to release terminal control, clear the screen, and restore it upon subprocess completion. The suspend block must run the subprocess synchronously (via `subprocess.run()` or thread executor) to avoid async/event-loop conflicts inside the suspended context.
2. **Subprocess Management:** Spawn external commands dynamically with standard input/output redirection to ensure full-screen console mode takeover. Subprocesses must receive connected stdin/stdout/stderr (not `DEVNULL`) so interactive apps (e.g. `nano`, `htop`) function correctly.
3. **Restoration Mechanism:** Clean redraw of the TUI application layout post-subprocess exit. A persistent log buffer (in-memory `list[str]`) preserves syslog history across suspend/resume cycles, since Textual's `Log` widget does not survive terminal suspension.
4. **Error & Crash Recovery:** Dashboard must automatically restore itself if the launched app crashes (non-zero exit code) or gets stuck (watchdog timer escalation).
5. **Low RAM Overhead:** Keep the core switcher engine logic simple without spawning heavy monitoring daemons. The mode-switcher state machine and log buffer must add less than 1 MB of RAM overhead.
6. **Concurrency Guard:** Only one subprocess may be active at any time. A second launch request while a subprocess is running must be rejected with a log message. An `asyncio.Lock` or equivalent state flag enforces mutual exclusion.
7. **Signal Handling:** The engine must install handlers for SIGTERM and SIGINT. On receipt of SIGTERM (e.g. systemd stop), the active subprocess is killed (SIGTERM → 5 s grace → SIGKILL), the TUI is resumed, and the app exits cleanly. SIGINT triggers the same subprocess teardown but does not exit the dashboard.
8. **Network Listener Pause:** The background aiohttp API server (port 8099) must be paused or its requests rejected while a subprocess is active, preventing play requests from arriving during suspension and attempting to manipulate suspended widgets.

## State Machine

The mode-switcher operates as an explicit finite state machine:

```
          launch()              subprocess started
 IDLE ──────────────► SUSPENDING ──────────────────► RUNNING
  ▲                      │                              │
  │                      │ (reject)                     │ subprocess exit / crash / timeout
  │                      ▼                              ▼
  │                   IDLE                        RESUMING
  │                                              │
  └──────────────────────────────────────────────┘
                           restored
```

| State | Description |
|---|---|
| `IDLE` | Dashboard active, accepting input, API server running. |
| `SUSPENDING` | TUI suspending, terminal released, subprocess spawning. New launch requests rejected. |
| `RUNNING` | Subprocess owns the terminal. API requests rejected. Watchdog timer armed. |
| `RESUMING` | Subprocess exited. Terminal restored, log buffer replayed, API server resumed. Transitions to `IDLE`. |

## Architecture Decision: Display Backend

Full-screen hardware-accelerated subprocesses (MPV, SteamLink, WPE WebKit) require access to a display output. On RPi OS Lite (headless, no desktop environment), the following options exist:

| Option | Pros | Cons |
|---|---|---|
| **DRM/KMS direct** (`--vo=gpu --gpu-context=drm`) | Zero compositor overhead, lowest RAM | Not all apps support it (SteamLink, WPE need Wayland/X11) |
| **Minimal Wayland compositor** (sway/wlroots) | Universal app compatibility, < 30 MB RAM | Adds a dependency, slight overhead |
| **X11 (Xorg)** | Broadest compatibility | ~50 MB RAM, heavier than Wayland |

**Decision:** Use **DRM/KMS direct rendering** for MPV (which supports it natively). For apps requiring a compositor (SteamLink, WPE WebKit), provision a **minimal Wayland compositor** (wlroots-based) as an optional dependency. The mode-switcher engine itself is display-backend-agnostic — it spawns whatever command is configured and manages its lifecycle.

## Non-Goals
- Integration of specific app launchers (these are handled in their own tracks).
- Graphics rendering configurations (handled in device provisioning).
- Wayland/X11 compositor lifecycle management (handled in automated-provisioning track).

## Acceptance Criteria
- [ ] Textual application can successfully suspend using a custom controller or built-in context.
- [ ] Subprocess (e.g. `nano`, `htop`, or a TTY-attached test script) takes over stdout/stderr and is interactive.
- [ ] On exit, the dashboard screen is successfully redrawn with the original layout and log history intact.
- [ ] The app auto-restores if the subprocess is killed (SIGTERM/SIGKILL) or exits with non-zero code.
- [ ] The watchdog timer kills a stuck subprocess after the configured timeout and restores the dashboard.
- [ ] A second launch attempt while a subprocess is active is rejected with a log message.
- [ ] The aiohttp API server does not deliver play requests to the TUI while a subprocess is running.
- [ ] Receiving SIGTERM during an active subprocess triggers clean teardown and dashboard restoration.
