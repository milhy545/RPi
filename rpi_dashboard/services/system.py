"""System service module for RPi-TV Dashboard.

Handles system stats, restart, and hardware monitoring.
"""

import os
import subprocess
from typing import Any, Dict


def _run(cmd, t=5):
    """Run a command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def get_cpu_usage() -> float:
    """Get CPU usage percentage."""
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        if line.startswith("cpu "):
            parts = list(map(int, line.split()[1:8]))
            idle = parts[3] + parts[4]
            total = sum(parts)
            if total > 0:
                return 100.0 * (1.0 - idle / total)
    except Exception:
        pass
    return 0.0


def get_ram_usage() -> Dict[str, float]:
    """Get RAM usage in MB."""
    try:
        mem_total = 0
        mem_available = 0
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_available = int(line.split()[1])
        if mem_total > 0:
            used = mem_total - mem_available
            return {
                "used_mb": used / 1024,
                "total_mb": mem_total / 1024,
                "percent": 100.0 * used / mem_total,
            }
    except Exception:
        pass
    return {"used_mb": 0, "total_mb": 1, "percent": 0}


def get_cpu_temp() -> float:
    """Get CPU temperature in Celsius."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip())
        return temp / 1000.0
    except Exception:
        return 0.0


def get_disk_usage() -> Dict[str, Any]:
    """Get disk usage for root partition."""
    try:
        r = _run(["df", "-h", "/"], t=3)
        lines = r.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                return {
                    "total": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "percent": parts[4],
                }
    except Exception:
        pass
    return {"total": "0", "used": "0", "available": "0", "percent": "0%"}


def get_uptime() -> str:
    """Get system uptime."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    except Exception:
        return "unknown"


def get_system_stats() -> Dict[str, Any]:
    """Get comprehensive system stats."""
    return {
        "cpu_percent": get_cpu_usage(),
        "cpu_temp": get_cpu_temp(),
        "ram": get_ram_usage(),
        "disk": get_disk_usage(),
        "uptime": get_uptime(),
    }


def restart_mpv() -> Dict[str, Any]:
    """Restart mpv player."""
    try:
        _run(["pkill", "-f", "mpv"], t=3)
        return {"ok": True, "message": "mpv restarted"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def restart_dashboard() -> Dict[str, Any]:
    """Restart the dashboard service."""
    try:
        r = _run(["sudo", "systemctl", "restart", "rpi-dashboard"], t=10)
        return {"ok": r.returncode == 0, "message": "Dashboard restarting"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def restart_rpi() -> Dict[str, Any]:
    """Restart the Raspberry Pi."""
    try:
        r = _run(["sudo", "reboot"], t=5)
        return {"ok": True, "message": "Rebooting..."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_network_info() -> Dict[str, Any]:
    """Get network information."""
    try:
        # Get IP addresses
        r = _run(["hostname", "-I"], t=3)
        ips = r.stdout.strip().split()

        # Get default gateway
        r2 = _run(["ip", "route", "show", "default"], t=3)
        gateway = None
        for line in r2.stdout.split("\n"):
            if "default via" in line:
                parts = line.split()
                idx = parts.index("via")
                if idx + 1 < len(parts):
                    gateway = parts[idx + 1]
                break

        return {
            "ips": ips,
            "gateway": gateway,
        }
    except Exception as e:
        return {"ips": [], "gateway": None, "error": str(e)}


def get_tailscale_status() -> Dict[str, Any]:
    """Get Tailscale VPN status."""
    try:
        r = _run(["tailscale", "status"], t=5)
        if r.returncode == 0:
            return {"connected": True, "status": r.stdout.strip()[:500]}
        return {"connected": False}
    except Exception:
        return {"connected": False}


def get_service_status(service: str) -> Dict[str, Any]:
    """Get systemd service status."""
    try:
        r = _run(["systemctl", "is-active", service], t=3)
        return {"active": r.stdout.strip() == "active", "status": r.stdout.strip()}
    except Exception:
        return {"active": False, "status": "unknown"}


def get_hwmon_info() -> Dict[str, Any]:
    """Get hardware monitoring info (temperatures, fan speeds)."""
    temps = {}
    try:
        for zone in os.listdir("/sys/class/thermal/"):
            if zone.startswith("thermal_zone"):
                path = f"/sys/class/thermal/{zone}/temp"
                if os.path.exists(path):
                    with open(path, "r") as f:
                        temp = int(f.read().strip()) / 1000.0
                    temps[zone] = temp
    except Exception:
        pass
    return {"temperatures": temps}
