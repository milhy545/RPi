# Implementation Plan: Zero-Overhead Mode Switcher Engine

## Phase 0: Architecture & State Machine Foundation
- [x] Task: Decide and document DRM/KMS vs Wayland compositor strategy in `spec.md` (completed — DRM/KMS for MPV, optional wlroots for SteamLink/WPE).
- [x] Task: Implement the `ModeSwitcherState` enum and state machine in a new `mode_switcher.py` module. Enforce states (`IDLE`, `SUSPENDING`, `RUNNING`, `RESUMING`) and transitions.
- [x] Task: Implement the `asyncio.Lock`-based concurrency guard with immediate rejection and log warnings.

## Phase 1: Subprocess Management
- [x] Task: Create a subprocess wrapper that executes shell commands and returns exit codes. Use connected standard descriptors (stdin/stdout/stderr) for direct TTY takeover.
- [x] Task: Redirect inputs and outputs ensuring that external processes can capture console controls. Avoid `subprocess.DEVNULL` for interactive tools.
- [x] Task: Define configurable timeouts for processes. Default is unlimited (0).

## Phase 2: TUI Suspension & Resume
- [x] Task: Implement TUI suspension using Textual's `with self.app.suspend():` context manager. Run the subprocess synchronously inside a thread executor to keep the main asyncio event loop active.
- [x] Task: Validate screen restoration after subprocess exits.
- [x] Task: Add pause/resume mechanism for the background API server. Reject incoming play requests during suspension with `503 Service Unavailable`.

## Phase 3: Log Buffer Persistence
- [x] Task: Implement the `LogBuffer` class to store up to 200 logs in memory.
- [x] Task: Replay the buffer into the Textual `Log` widget on application mount and after subprocess resume.
- [x] Task: Decouple direct widget logging by routing all logging calls through the `LogBuffer` first.

## Phase 4: Signal Handling & Watchdog Timer
- [x] Task: Install a SIGTERM handler on the app. Shut down the subprocess with a 5s grace period before SIGKILL, restore terminal, and exit cleanly.
- [x] Task: Install a SIGINT handler on the app. Terminate the subprocess with identical teardown, restore terminal, and return to IDLE.
- [x] Task: Implement a watchdog timer to kill stuck processes.
- [x] Task: Define timeout constants per mode (e.g. `STEAMLINK_TIMEOUT = 0`, `MPV_TIMEOUT = 0`, `TEST_TIMEOUT = 30`).

## Phase 5: Integration & Validation
- [x] Task: Wire the `ModeSwitcher` into `RPiDashboard.on_button_pressed()` and replace stub logic.
- [x] Task: Route the API play requests through the mode switcher.
- [x] Task: Verify interactive takeover using `nano` (via fallback when `steamlink` is missing).
- [x] Task: Verify crash recovery with non-zero exit codes.
- [x] Task: Verify watchdog timer killing process and restoring terminal.
- [x] Task: Verify concurrency guard rejection.
- [x] Task: Verify signal handlers (SIGTERM and SIGINT).
- [x] Task: Confirm low memory footprint (< 1 MB RAM overhead).

## Completion Notes
- Core mode switcher engine is complete in `mode_switcher.py` / `tui.py`.
- UI parity/app-mode leftovers live in `dashboard-modes-settings-terminal_20260613`.
