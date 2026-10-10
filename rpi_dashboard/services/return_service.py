"""
Return-to-dashboard service.

Provides a single, idempotent action to return from any active mode to the
dashboard, handling graceful shutdown, timeout, and fallback to forceful
termination. Records the reason and source of the last return for telemetry.
Also listens for Xbox B button (BTN_EAST) long press (≥2 seconds) to trigger
a return.
"""

import json
import os
import select
import struct
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List

from rpi_dashboard.services.input_devices import find_all_input_devices_by_name_pattern

# We will import mode_switcher lazily to avoid circular imports
from mode_switcher import ModeSwitcher

# Configuration file path
_CONFIG_PATH = Path("/home/milhy777/rpi-dashboard/conductor/ci/receipts/return_service_config.json")

# Default configuration
_DEFAULT_CONFIG = {
    "keyboard_shortcut_enabled": True,
    "xbox_b_hold_enabled": True,
    "xbox_b_hold_duration_sec": 2.0,
}

# Global state
_last_reason: str = "unknown"
_last_source: str = "unknown"
_last_timestamp: float = 0.0
_lock = threading.Lock()

# Reference to the active mode_switcher (set by the TUI)
_active_mode_switcher: Optional[ModeSwitcher] = None
_ms_lock = threading.Lock()

# Xbox listener control
_xbox_listener_thread: Optional[threading.Thread] = None
_xbox_listener_stop_event = threading.Event()
_listener_started = False

# Configuration (loaded from file)
_config: Dict = {}
_config_lock = threading.Lock()


def _load_config_unlocked() -> Dict:
    """Load configuration from file without acquiring ``_config_lock``.

    Must only be called while ``_config_lock`` is held by the caller.
    """
    global _config
    if _config:
        return _config
    try:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, 'r') as f:
                _config = {**_DEFAULT_CONFIG, **json.load(f)}
        else:
            _config = _DEFAULT_CONFIG.copy()
    except Exception:
        _config = _DEFAULT_CONFIG.copy()
    return _config


def _save_config_unlocked() -> None:
    """Save configuration to file without acquiring ``_config_lock``.

    Must only be called while ``_config_lock`` is held by the caller.
    """
    global _config
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, 'w') as f:
        json.dump(_config, f, indent=2)


def _load_config() -> Dict:
    """Load configuration from file, falling back to defaults.

    Acquires ``_config_lock`` exactly once and returns a defensive copy
    while the lock is still held.
    """
    with _config_lock:
        _load_config_unlocked()
        return {**_config}


def _save_config() -> None:
    """Save configuration to file.

    Acquires ``_config_lock`` exactly once.
    """
    with _config_lock:
        _save_config_unlocked()


def get_config() -> Dict:
    """Get current configuration.

    Returns a defensive copy so callers cannot mutate internal state.
    """
    return _load_config()


def update_config(updates: Dict) -> Dict:
    """Update configuration with new values.

    Acquires ``_config_lock`` exactly once and uses private unlocked helpers
    to avoid nested / re-entrant locking.
    """
    global _config
    with _config_lock:
        _load_config_unlocked()
        for key, value in updates.items():
            if key in _DEFAULT_CONFIG:
                # Type conversion for known keys
                if key.endswith('_enabled'):
                    _config[key] = bool(value)
                elif key.endswith('_duration_sec'):
                    _config[key] = float(value)
                else:
                    _config[key] = value
        _save_config_unlocked()
        return {**_config}


def set_mode_switcher(ms: Optional[ModeSwitcher]) -> None:
    """Set the active mode_switcher instance (called from TUI)."""
    global _active_mode_switcher
    with _ms_lock:
        _active_mode_switcher = ms


def get_mode_switcher() -> Optional[ModeSwitcher]:
    """Get the current mode_switcher instance."""
    with _ms_lock:
        return _active_mode_switcher


def get_last_return() -> dict:
    """Return a dict with the last reason, source, and timestamp."""
    with _lock:
        return {
            "reason": _last_reason,
            "source": _last_source,
            "timestamp": _last_timestamp,
        }


def _record_return(reason: str, source: str) -> None:
    """Record the reason and source for the last return."""
    global _last_reason, _last_source, _last_timestamp
    with _lock:
        _last_reason = reason
        _last_source = source
        _last_timestamp = time.time()


def return_to_dashboard(reason: str, source: str) -> bool:
    """
    Execute a return-to-dashboard sequence.
    Returns True if a return was initiated (i.e., we stopped an active mode),
    False if we were already at the dashboard.
    This function is idempotent.
    """
    # Always record the attempt
    _record_return(reason, source)

    # Get the current mode_switcher
    ms = get_mode_switcher()
    if ms is None:
        # No mode_switcher known; assume we are at the dashboard.
        return False

    # Request the mode_switcher to stop the active process, if any.
    # The method returns True if it actually terminated a process.
    try:
        stopped = ms.request_stop()
    except Exception:
        # If something goes wrong, we assume we did not stop anything.
        stopped = False

    return stopped


def start_xbox_listener() -> None:
    """Start the Xbox B button listener thread if not already running."""
    global _xbox_listener_thread, _listener_started
    with _ms_lock:  # reuse lock for simplicity; could have its own
        if _listener_started:
            return
        _listener_started = True
    _xbox_listener_stop_event.clear()
    _xbox_listener_thread = threading.Thread(
        target=_xbox_listener_loop,
        name="XboxBListener",
        daemon=True,
    )
    _xbox_listener_thread.start()


def stop_xbox_listener() -> None:
    """Stop the Xbox B listener thread (called on shutdown)."""
    global _xbox_listener_thread, _listener_started
    _xbox_listener_stop_event.set()
    if _xbox_listener_thread is not None:
        _xbox_listener_thread.join(timeout=2.0)
        _xbox_listener_thread = None
    _listener_started = False


def _xbox_listener_loop() -> None:
    """Background thread to monitor Xbox B button presses."""
    BTN_EAST = 0x12e  # from linux/input.h
    # Map file descriptor to press timestamp (or None if not pressed)
    press_times: Dict[int, Optional[float]] = {}
    # Map file descriptor to device path for cleanup/reporting
    fd_to_path: Dict[int, str] = {}
    # Rescan interval for hotplug (seconds)
    RESCAN_INTERVAL = 5.0
    last_rescan = 0.0

    def _scan_for_xbox_devices() -> List[str]:
        """Return list of /dev/input/event* paths that appear to be Xbox controllers."""
        return find_all_input_devices_by_name_pattern("xbox")

    def _open_device(path: str) -> Optional[int]:
        """Open device for non-blocking reading, return fd or None."""
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            return fd
        except OSError:
            return None

    # Initial device discovery
    now = time.time()
    if now - last_rescan >= RESCAN_INTERVAL:
        paths = _scan_for_xbox_devices()
        last_rescan = now
        for path in paths:
            if path in fd_to_path.values():
                continue  # already open
            fd = _open_device(path)
            if fd is not None:
                fd_to_path[fd] = path
                press_times[fd] = None  # no press yet

    # Main loop
    while not _xbox_listener_stop_event.is_set():
        # Periodically rescan for new devices
        now = time.time()
        if now - last_rescan >= RESCAN_INTERVAL:
            current_paths = set(fd_to_path.values())
            new_paths = set(_scan_for_xbox_devices())
            # Add new devices
            for path in new_paths - current_paths:
                if path not in fd_to_path.values():
                    fd = _open_device(path)
                    if fd is not None:
                        fd_to_path[fd] = path
                        press_times[fd] = None
            # Note: we don't actively remove disappeared devices; they will cause errors on read.
            last_rescan = now

        # Prepare select list
        if not fd_to_path:
            # No devices, sleep a bit
            time.sleep(0.1)
            continue
        rlist, _, _ = select.select(list(fd_to_path.keys()), [], [], 0.1)
        for fd in rlist:
            device_path: Optional[str] = fd_to_path.get(fd)
            if device_path is None:
                continue
            try:
                data = os.read(fd, 24)  # size of struct input_event
                if len(data) != 24:
                    # Possibly device disconnected
                    raise OSError
                (tv_sec, tv_usec, ev_type, ev_code, ev_value) = struct.unpack('llHHi', data)

                # Check if Xbox B listener is enabled
                config = get_config()
                xbox_enabled = config.get("xbox_b_hold_enabled", True)
                xbox_duration = config.get("xbox_b_hold_duration_sec", 2.0)

                if ev_type == 1 and ev_code == BTN_EAST:  # EV_KEY, BTN_EAST
                    if ev_value == 1:  # key down
                        if press_times.get(fd) is None:
                            press_times[fd] = time.time()
                    elif ev_value == 0:  # key up
                        press_times[fd] = None
            except OSError:
                # Device likely disconnected; close and remove
                try:
                    os.close(fd)
                except OSError:
                    pass
                if fd in fd_to_path:
                    del fd_to_path[fd]
                if fd in press_times:
                    del press_times[fd]
            except Exception:
                # Other errors, ignore to keep thread alive
                pass

        # Check elapsed press durations while key is still held down
        config = get_config()
        xbox_enabled = config.get("xbox_b_hold_enabled", True)
        xbox_duration = config.get("xbox_b_hold_duration_sec", 2.0)

        now_time = time.time()
        for fd, start in list(press_times.items()):
            if start is not None and xbox_enabled:
                if now_time - start >= xbox_duration:
                    press_times[fd] = None  # Reset so it doesn't re-trigger continuously
                    try:
                        return_to_dashboard(
                            reason="xbox_b_long_hold",
                            source="xbox_b"
                        )
                    except Exception:
                        pass
        # Small sleep to prevent busy loop when no events
        time.sleep(0.01)


def request_stop() -> None:
    """
    Backward-compatible alias for return_to_dashboard with default reason/source.
    This function is kept for compatibility with existing code that might
    call a request_stop function.
    """
    return_to_dashboard(reason="request_stop", source="return_service")