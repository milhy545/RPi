"""CEC service module for RPi-TV Dashboard.

Handles HDMI-CEC commands for TV control.
"""

import subprocess
import sys
from typing import Any, Dict, Optional


def cec_cmd(cmd: str, timeout: float = 5) -> Dict[str, Any]:
    """Send a CEC command."""
    try:
        proc = subprocess.Popen(
            ["cec-client", "-d", "1", "-s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, _stderr = proc.communicate(input=cmd + "\n", timeout=timeout)
        return {"ok": proc.returncode == 0, "output": stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cec_scan() -> Dict[str, Any]:
    """Scan CEC bus for devices."""
    try:
        r = subprocess.run(["cec-ctl", "-d", "/dev/cec0", "-S"], capture_output=True, text=True, timeout=5)
        return {"ok": True, "devices": r.stdout.strip().splitlines() if r.stdout.strip() else [], "output": r.stdout.strip()[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cec_send(cmd: str, timeout: float = 5) -> Dict[str, Any]:
    """Send a raw CEC command."""
    return cec_cmd(cmd, timeout)


def cec_key(key: str, timeout: float = 5) -> Dict[str, Any]:
    """Send a CEC key command."""
    return cec_cmd(f"user-control pressed '{key}'", timeout)


def cec_input(input_num: str, timeout: float = 5) -> Dict[str, Any]:
    """Switch to a CEC input."""
    _ = input_num
    return cec_cmd("active-source phys-addr=1.0.0.0", timeout)


_CEC_BRIDGE: Optional[subprocess.Popen[Any]] = None


def cec_bridge_start() -> Dict[str, Any]:
    """Start the legacy CEC-to-mpv bridge."""
    global _CEC_BRIDGE
    cec_bridge_stop()
    script = r'''
import json, os, select, socket, subprocess, sys, time
MP = "/tmp/rpi-mpv.sock"
SOCKET_RECV_SIZE = 4096

def mc(cmd):
    if not os.path.exists(MP):
        return
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(MP)
        s.settimeout(1)
        s.sendall((json.dumps({"command": ["parse-command", cmd]}) + "\n").encode())
        s.recv(SOCKET_RECV_SIZE)
        s.close()
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)

M = {"play": "cycle pause", "pause": "cycle pause", "stop": "stop", "backward": "seek -10", "forward": "seek 10", "rewind": "seek -60", "fast_forward": "seek 60", "left": "seek -10", "right": "seek 10", "select": "cycle pause", "exit": "stop", "menu": "cycle pause", "volume_up": "add volume 5", "volume_down": "add volume -5", "mute": "cycle mute"}
while True:
    p = subprocess.Popen(["cec-client", "-s", "-d", "1", "-p", "0"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        while True:
            r, _, _ = select.select([p.stdout], [], [], 3.0)
            if r:
                line = p.stdout.readline()
                if not line:
                    break
                lowered = line.lower()
                for k, cmd in M.items():
                    if k in lowered:
                        mc(cmd)
                        break
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        p.wait(timeout=2)
    except Exception:
        p.kill()
    time.sleep(2)
'''
    _CEC_BRIDGE = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"ok": True, "pid": _CEC_BRIDGE.pid}


def cec_bridge_stop() -> Dict[str, Any]:
    """Stop the legacy CEC-to-mpv bridge."""
    global _CEC_BRIDGE
    proc = _CEC_BRIDGE
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
    _CEC_BRIDGE = None
    return {"ok": True}


def cec_bridge_status() -> Dict[str, Any]:
    """Return the bridge status."""
    proc = _CEC_BRIDGE
    return {"on": bool(proc and proc.poll() is None), "pid": proc.pid if proc else None}


def cec_power_on() -> Dict[str, Any]:
    """Turn on TV via CEC."""
    return cec_cmd("on 0")


def cec_power_off() -> Dict[str, Any]:
    """Turn off TV via CEC."""
    return cec_cmd("standby 0")


def cec_volume_up() -> Dict[str, Any]:
    """Increase volume via CEC."""
    return cec_cmd("volup")


def cec_volume_down() -> Dict[str, Any]:
    """Decrease volume via CEC."""
    return cec_cmd("voldown")


def cec_mute() -> Dict[str, Any]:
    """Toggle mute via CEC."""
    return cec_cmd("mute")


def cec_up() -> Dict[str, Any]:
    """Navigate up via CEC."""
    return cec_cmd("up")


def cec_down() -> Dict[str, Any]:
    """Navigate down via CEC."""
    return cec_cmd("down")


def cec_left() -> Dict[str, Any]:
    """Navigate left via CEC."""
    return cec_cmd("left")


def cec_right() -> Dict[str, Any]:
    """Navigate right via CEC."""
    return cec_cmd("right")


def cec_select() -> Dict[str, Any]:
    """Select/OK via CEC."""
    return cec_cmd("select")


def cec_back() -> Dict[str, Any]:
    """Go back via CEC."""
    return cec_cmd("back")


def cec_menu() -> Dict[str, Any]:
    """Open menu via CEC."""
    return cec_cmd("menu")


def cec_input_hdmi1() -> Dict[str, Any]:
    """Switch to HDMI 1."""
    return cec_cmd("input 1")


def cec_input_hdmi2() -> Dict[str, Any]:
    """Switch to HDMI 2."""
    return cec_cmd("input 2")


def cec_input_hdmi3() -> Dict[str, Any]:
    """Switch to HDMI 3."""
    return cec_cmd("input 3")


def cec_active_source() -> Dict[str, Any]:
    """Set RPi as active source."""
    return cec_cmd("active_source")


def cec_physical_address() -> Optional[str]:
    """Get physical address of the TV."""
    try:
        proc = subprocess.Popen(
            ["cec-client", "-d", "1", "-s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="tx 0f 82 10 00\n", timeout=3)
        # Parse response
        for line in stdout.split("\n"):
            if "physical address" in line.lower():
                return line.split(":")[-1].strip()
        return None
    except Exception:
        return None
