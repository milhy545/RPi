#!/usr/bin/env python3
"""
keys2mpv — Multimedia keyboard daemon for RPi.
Reads /dev/input/event2 directly, sends commands to mpv via IPC.
Also handles global hotkeys like Ctrl+Alt+Backspace to return to dashboard.
Works independently of TUI/webserver — runs as background service.
"""
import json
import os
import signal
import socket
import struct
import sys

from rpi_dashboard.services import return_service

INPUT_DEV = "/dev/input/event2"
SOCKETS = ["/tmp/rpi-mpv.sock", "/tmp/mpv-socket"]

# Keycode → mpv IPC command + label
KEYMAP = {
    164: (["cycle", "pause"],     "⏯  Play/Pause"),
    163: (["seek", "30"],         "⏩  +30s"),
    165: (["seek", "-30"],        "⏪  -30s"),
    114: (["add", "volume", "-5"],"🔉  Vol-5"),    # reversed
    115: (["add", "volume", "5"], "🔊  Vol+5"),    # reversed
    113: (["set", "mute", "yes"], "🔇  Mute"),
}

# Keycodes for modifiers we care about for Ctrl+Alt+Backspace
CTRL_KEYS = {29, 97}          # Left Ctrl (29), Right Ctrl (97)
ALT_KEYS = {56, 100}          # Left Alt (56), Right Alt (100, AltGr)
BACKSPACE_KEY = 14

def find_socket():
    """Find active mpv IPC socket."""
    for s in SOCKETS:
        if os.path.exists(s):
            return s
    return None

def mpv_cmd(cmd_list):
    """Send command to mpv via IPC. Returns True on success."""
    sock = find_socket()
    if not sock:
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock)
        s.settimeout(2)
        s.sendall(json.dumps({"command": cmd_list}).encode() + b"\n")
        resp = s.recv(4096)
        s.close()
        data = json.loads(resp.decode())
        return data.get("error") == "success"
    except (OSError, json.JSONDecodeError):
        return False

def mpv_get(prop):
    """Get property from mpv via IPC."""
    sock = find_socket()
    if not sock:
        return None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock)
        s.settimeout(2)
        s.sendall(json.dumps({"command": ["get_property", prop]}).encode() + b"\n")
        resp = s.recv(4096)
        s.close()
        data = json.loads(resp.decode())
        return data.get("data")
    except (OSError, json.JSONDecodeError):
        return None

def graceful_exit(sig, frame):
    print("\nkeys2mpv: Stopped.")
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_exit)
signal.signal(signal.SIGINT, graceful_exit)

def main():
    if not os.path.exists(INPUT_DEV):
        print(f"keys2mpv: ERROR - {INPUT_DEV} not found")
        sys.exit(1)
    
    print(f"keys2mpv: Listening on {INPUT_DEV}")
    print(f"keys2mpv: Sockets: {SOCKETS}")
    print("keys2mpv: Listening for Ctrl+Alt+Backspace to return to dashboard")
    print("keys2mpv: Press Ctrl+C or kill to stop")
    
    # Track state of modifier keys
    ctrl_pressed = False
    alt_pressed = False
    
    with open(INPUT_DEV, 'rb') as f:
        while True:
            data = f.read(24)
            if len(data) == 24:
                _, _, ev_type, ev_code, ev_value = struct.unpack('llHHi', data)
                if ev_type == 1:  # Key event
                    if ev_code in CTRL_KEYS:
                        ctrl_pressed = (ev_value == 1)  # 1 = press, 0 = release
                    elif ev_code in ALT_KEYS:
                        alt_pressed = (ev_value == 1)
                    elif ev_code == BACKSPACE_KEY and ev_value == 1:  # Backspace pressed
                        if ctrl_pressed and alt_pressed:
                            # Trigger return to dashboard
                            try:
                                return_service.return_to_dashboard(
                                    reason="keyboard_shortcut",
                                    source="ctrl_alt_backspace"
                                )
                                print("keys2mpv: Ctrl+Alt+Backspace -> return to dashboard")
                            except Exception as e:
                                print(f"keys2mpv: Error triggering return: {e}")
                            # Do not send Backspace to mpv
                            continue
                    # If we get here and it's a key press (down) and in KEYMAP, send to mpv
                    if ev_value == 1 and ev_code in KEYMAP:
                        cmd, label = KEYMAP[ev_code]
                        ok = mpv_cmd(cmd)
                        if ok:
                            # Get current status for feedback
                            pos = mpv_get("time-pos")
                            vol = mpv_get("volume")
                            pos_str = f"{int(pos//60)}:{int(pos%60):02d}" if pos else "?"
                            vol_str = f"{int(vol)}%" if vol else "?"
                            print(f"keys2mpv: {label}  pos={pos_str} vol={vol_str}")
                        else:
                            print(f"keys2mpv: {label}  (mpv not running)")

if __name__ == "__main__":
    main()
