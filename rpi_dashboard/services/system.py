"""System service module for RPi-TV Dashboard.

Handles system stats, restart, and hardware monitoring.
"""

import json
import os
import math
import shutil
import socket
import subprocess
import time
import fcntl
import struct
import sys
import array
import contextlib
from typing import Any, Dict, List, Optional, Tuple

from config import HTTP_PORT, HTTPS_PORT, HTTPS_PORT_ALT, PORT


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


def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0"
    size_name = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 1)
    if s.is_integer():
        return f"{int(s)}{size_name[i]}"
    return f"{s:.1f}{size_name[i]}"


def get_disk_usage() -> Dict[str, Any]:
    """Get disk usage for root partition."""
    try:
        # Bolt Performance Optimization:
        # Replaced expensive subprocess shell call (`df -h`) with native
        # Python shutil.disk_usage to avoid process creation overhead.
        usage = shutil.disk_usage("/")
        total_b = usage.total
        used_b = usage.used
        avail_b = usage.free
        percent = math.ceil((used_b / total_b) * 100) if total_b > 0 else 0
        return {
            "total": _format_size(total_b),
            "used": _format_size(used_b),
            "available": _format_size(avail_b),
            "percent": f"{percent}%",
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


def _cpu_sample() -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    with open("/proc/stat") as f:
        for line in f:
            if line.startswith("cpu") and line[3:4].isdigit():
                parts = [int(x) for x in line.split()[1:]]
                idle = parts[3] + parts[4]
                total = sum(parts)
                out.append((total, idle))
    return out


def _meminfo() -> Dict[str, int]:
    mem: Dict[str, int] = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":", 1)
            mem[key] = int(value.split()[0])
    return mem


def _cpu_freqs_cached() -> List[Optional[int]]:
    freq: List[Optional[int]] = []
    for i in range(4):
        try:
            with open(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq") as f:
                freq.append(int(f.read().strip()) // 1000)
        except Exception:
            freq.append(None)
    return freq


def _vcgencmd_core_mhz() -> Optional[int]:
    try:
        raw = subprocess.check_output(["vcgencmd", "measure_clock", "core"], text=True, timeout=2).strip()
        return int(raw.split("=")[-1]) // 1000000
    except Exception:
        return None


def dashboard_hostnames_and_ips() -> Tuple[List[str], List[str]]:
    names = {"rpi-tv", "rpi-tv.local", "localhost"}
    ips = {"127.0.0.1"}
    try:
        hn = socket.gethostname().strip()
        if hn:
            names.add(hn)
            names.add(f"{hn}.local")
    except Exception:
        pass
    try:
        for ip in subprocess.check_output(["hostname", "-I"], text=True, timeout=2).split():
            if ip:
                ips.add(ip)
    except Exception:
        pass
    try:
        for flag in ("-4", "-6"):
            r = subprocess.run(["tailscale", "ip", flag], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                for ip in r.stdout.split():
                    ips.add(ip)
    except Exception:
        pass
    try:
        r = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            d = json.loads(r.stdout or "{}")
            dns = (d.get("Self") or {}).get("DNSName") or ""
            if dns:
                names.add(dns.rstrip("."))
                names.add(dns.split(".")[0])
    except Exception:
        pass
    return sorted(names), sorted(ips)


def get_system_stats() -> Dict[str, Any]:
    """Get comprehensive system stats."""
    return {
        "cpu_percent": get_cpu_usage(),
        "cpu_temp": get_cpu_temp(),
        "ram": get_ram_usage(),
        "disk": get_disk_usage(),
        "uptime": get_uptime(),
    }


def _unit_main_pid(unit: str, user: bool = False) -> str:
    """Return the MainPID for *unit*, or ``""`` on any failure.

    Uses ``_run`` (``subprocess.run``) for consistency with the rest of the
    module.  Catches command failures, timeouts, and missing binaries so that
    a single absent unit never tears down the whole status response.
    """
    cmd = ["systemctl"]
    if user:
        cmd.append("--user")
    cmd += ["show", unit, "-p", "MainPID", "--value"]
    try:
        r = _run(cmd, t=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _taskset_mask(pid: str) -> str:
    if not pid or pid == "0":
        return "N/A"
    try:
        # ⚡ Bolt Optimization: Use native Python to read CPU affinity
        # Replaced expensive `subprocess.check_output(["taskset", ...])` with
        # native file I/O to avoid process creation overhead on Raspberry Pi.
        # This makes the `/system/status` API much faster.
        with open(f"/proc/{pid}/status", "r") as f:
            for line in f:
                if line.startswith("Cpus_allowed:"):
                    return line.split(":")[1].strip()
        return "N/A"
    except Exception:
        return "N/A"


def _mask_to_cores(mask: str) -> str:
    try:
        mask_val = int(mask, 16)
        cores = [str(i) for i in range(4) if mask_val & (1 << i)]
        return ",".join(cores) if cores else "none"
    except Exception:
        return "?"


def _get_pid_by_name(name: str) -> str:
    """Find process ID by name natively to avoid expensive subprocess calls."""
    try:
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    with open(f"/proc/{pid}/comm", "r") as f:
                        if f.read().strip() == name:
                            return pid
                except (IOError, OSError):
                    pass
    except OSError:
        pass
    return ""


def get_system_status() -> Dict[str, Any]:
    """Return CPU affinity/status info used by the legacy WebUI."""
    # ⚡ Bolt Optimization: Use native Python procfs reading instead of `pgrep`
    # Replaced expensive `subprocess.check_output(["pgrep", "-x", "mpv"])` with
    # native file I/O to avoid process creation overhead on Raspberry Pi.
    # This makes the API faster and reduces system load.
    mpv_pid = _get_pid_by_name("mpv")
    dash_pid = _unit_main_pid("dashboard@milhy777")
    keys_pid = _unit_main_pid("keys2mpv")
    ws_pid = _unit_main_pid("webserver")
    pw_pid = _unit_main_pid("pipewire", user=True)
    wp_pid = _unit_main_pid("wireplumber", user=True)
    mpv_mask = _taskset_mask(mpv_pid)
    dash_mask = _taskset_mask(dash_pid)
    keys_mask = _taskset_mask(keys_pid)
    ws_mask = _taskset_mask(ws_pid)
    pw_mask = _taskset_mask(pw_pid)
    wp_mask = _taskset_mask(wp_pid)
    return {
        "mpv": {"pid": mpv_pid, "mask": mpv_mask, "cores": _mask_to_cores(mpv_mask)},
        "dashboard": {"pid": dash_pid, "mask": dash_mask, "cores": "0" if dash_mask == "1" else dash_mask},
        "keys2mpv": {"pid": keys_pid, "mask": keys_mask, "cores": "0" if keys_mask == "1" else keys_mask},
        "webserver": {"pid": ws_pid, "mask": ws_mask, "cores": "0" if ws_mask == "1" else ws_mask},
        "pipewire": {"pid": pw_pid, "mask": pw_mask, "cores": "3" if pw_mask == "8" else pw_mask},
        "wireplumber": {"pid": wp_pid, "mask": wp_mask, "cores": "3" if wp_mask == "8" else wp_mask},
        "summary": {
            "core0_background": ["dashboard", "keys2mpv", "webserver"],
            "core1_2_media": ["mpv"],
            "core3_audio": ["pipewire", "wireplumber"],
        },
    }


def get_hw_stats() -> Dict[str, Any]:
    """Get richer hardware stats used by the WebUI terminal tab."""
    cpu: List[float] = []
    try:
        samples_a = _cpu_sample()
        time.sleep(0.35)
        samples_b = _cpu_sample()
        for (t0, i0), (t1, i1) in zip(samples_a, samples_b):
            dt = t1 - t0
            di = i1 - i0
            cpu.append(round(100 * (dt - di) / dt, 1) if dt > 0 else 0.0)
    except Exception:
        cpu = []
    mem = _meminfo()
    total_mb = mem.get("MemTotal", 0) // 1024
    avail_mb = mem.get("MemAvailable", 0) // 1024
    used_mb = max(0, total_mb - avail_mb)
    st = os.statvfs("/")
    total_gb = round(st.f_blocks * st.f_frsize / 1024 / 1024 / 1024, 1)
    free_gb = round(st.f_bfree * st.f_frsize / 1024 / 1024 / 1024, 1)
    avail_gb = round(st.f_bavail * st.f_frsize / 1024 / 1024 / 1024, 1)
    used_gb = round(total_gb - free_gb, 1)
    temp_c = None
    for tp in ("/sys/class/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone1/temp"):
        try:
            with open(tp) as f:
                temp_c = round(int(f.read().strip()) / 1000, 1)
                break
        except Exception:
            pass
    freq = _cpu_freqs_cached()
    gpu = {"core_mhz": _vcgencmd_core_mhz(), "temp_c": temp_c}
    with open("/proc/uptime") as f:
        up = int(float(f.read().split()[0]))
    h = up // 3600
    m = (up % 3600) // 60
    s = up % 60
    return {
        "cpu": cpu,
        "loadavg": list(os.getloadavg()),
        "temp_c": temp_c,
        "freq_mhz": freq,
        "gpu": gpu,
        "ram": {"used_mb": used_mb, "total_mb": total_mb, "percent": round(100 * used_mb / total_mb, 1) if total_mb else 0},
        "disk": {"used_gb": used_gb, "total_gb": total_gb, "free_gb": free_gb, "avail_gb": avail_gb, "percent": round(100 * used_gb / total_gb, 1) if total_gb else 0},
        "uptime": f"{h}h {m}m {s}s",
    }


def get_https_info() -> Dict[str, Any]:
    """Return HTTPS and friendly port metadata."""
    names, ips = dashboard_hostnames_and_ips()
    host = names[0] if names else "rpi-tv"
    return {
        "ok": True,
        "http_port": PORT,
        "https_port": HTTPS_PORT,
        "friendly_http_port": HTTP_PORT,
        "friendly_https_port": HTTPS_PORT_ALT,
        "cert_exists": os.path.exists(os.path.expanduser("~/.config/rpi-dashboard/https/webui.crt")),
        "https_url": f"https://{host}:{HTTPS_PORT}/",
        "friendly_https_url": f"https://{host}/",
        "friendly_http_url": f"http://{host}/",
        "names": names,
        "ips": ips,
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
        # ⚡ Bolt Optimization: Use native Python to get network info
        # Replaced expensive subprocess shell calls (`hostname -I` and `ip route show default`)
        # with native socket ioctls and file I/O to avoid process creation overhead on Raspberry Pi.
        ips = []
        is_64bits = sys.maxsize > 2**32
        struct_size = 40 if is_64bits else 32
        pack_format = 'iP' if is_64bits else 'iI'
        names = array.array('B', b'\0' * 4096)

        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
            outbytes = struct.unpack(pack_format, fcntl.ioctl(
                s.fileno(),
                0x8912,  # SIOCGIFCONF
                struct.pack(pack_format, 4096, names.buffer_info()[0])
            ))[0]
            namestr = names.tobytes()
            for i in range(0, outbytes, struct_size):
                ip = socket.inet_ntoa(namestr[i+20:i+24])
                if ip != "127.0.0.1":
                    ips.append(ip)

        # Get default gateway natively
        gateway = None
        with open("/proc/net/route", "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3 and parts[1] == "00000000":
                    gw_hex = parts[2]
                    if gw_hex != "00000000":
                        gateway = socket.inet_ntoa(struct.pack("<L", int(gw_hex, 16)))
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


def get_service_logs(service: str, lines: int = 100) -> Dict[str, Any]:
    """Get systemd journal logs for a service."""
    try:
        cmd = ["journalctl", "-u", service, "-n", str(lines), "--no-pager", "--output=cat"]
        if not service:
            cmd = ["journalctl", "-n", str(lines), "--no-pager", "--output=cat"]
        r = _run(cmd, t=10)
        return {"logs": r.stdout, "error": r.stderr if r.returncode != 0 else None}
    except Exception as e:
        return {"logs": "", "error": str(e)}
