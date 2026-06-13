# `mode_switcher.py`

## Purpose
Launches foreground applications from the dashboard while preserving the TUI state, protecting against concurrency, and restoring the UI afterward.

## Core concepts
- **IDLE**: dashboard is active
- **SUSPENDING**: dashboard is about to hand control to another app
- **RUNNING**: external app is active
- **RESUMING**: external app exited; dashboard is being restored

## Class / function reference

### `ModeSwitcherState`
Enum for the switcher state machine.

### `InvalidTransition`
Raised when a state change would break the allowed lifecycle.

### `LogBuffer`
In-memory ring buffer that keeps the latest log lines across suspend/resume cycles.

**Methods**
- `__init__(max_lines=200)` — configure the buffer size
- `write(line)` — append a line and trim old entries
- `get_lines()` — return a copy of the stored lines
- `clear()` — empty the buffer

**Example**
The dashboard writes launch/exit events into `LogBuffer` so they survive app suspension.

### `ModeSwitcher`
Main supervisor for launching and recovering external applications.

#### `__init__(app)`
Initializes the switcher for a Textual `App` instance.

#### `_setup_signals()`
Registers SIGTERM/SIGINT handlers.

#### `_transition(new_state)`
Validates and performs a state transition.

**Example**
`IDLE -> SUSPENDING -> RUNNING -> RESUMING -> IDLE`

#### `launch(command, timeout=0)`
Launches an external process, suspends the TUI, optionally arms a watchdog, and restores the dashboard on exit.

**Example**
```python
await mode_switcher.launch(["mpv", "https://example.com/video.mp4"])
```

#### `_teardown_active_process()`
Attempts graceful termination, then kills the process if needed.

#### `_handle_sigterm()`
Handles Ctrl+C/termination behavior.

#### `_handle_sigint()`
Handles interrupt behavior while an app is running.

#### `_teardown_and_exit()`
Stops the process, waits for state recovery, then exits the dashboard.

#### `_teardown_only()`
Stops the active process without exiting the dashboard.

#### `_start_watchdog(timeout)`
Starts the timeout watchdog.

#### `_cancel_watchdog()`
Cancels the watchdog after normal exit.

#### `_watchdog_timer(timeout)`
Sleeps until timeout expires, then tears down the process.

## Real usage examples
- Launch Steam Link from the sidebar and return automatically when it exits.
- Run a test command with a watchdog timeout to verify crash recovery.
- Use the state machine logs to debug app launch failures.
