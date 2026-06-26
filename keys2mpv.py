#!/usr/bin/env python3
"""
keys2mpv — Multimedia keyboard daemon for RPi.
Reads /dev/input/event2 directly, sends commands to mpv via IPC.
Works independently of TUI/webserver — runs as background service.
"""
import json
import os
import signal
import socket
import struct
import sys

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
    except:
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
    except:
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
    print(f"keys2mpv: Press Ctrl+C or kill to stop")
    
    with open(INPUT_DEV, 'rb') as f:
        while True:
            data = f.read(24)
            if len(data) == 24:
                _, _, ev_type, ev_code, ev_value = struct.unpack('llHHi', data)
                if ev_type == 1 and ev_value == 1:  # Key press (down only)
                    if ev_code in KEYMAP:
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
