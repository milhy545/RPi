"""Hardware guard and resource protection engine for RPi validation pipeline.

Ensures candidate/test execution on RPi never degrades user playback, gaming,
TUI dashboard, or system performance, and prevents self-deadlock via CPU attribution.
"""

from __future__ import annotations

import os
import time
import subprocess
import logging
from typing import Dict, List, Set, Any, Optional, Callable

logger = logging.getLogger(__name__)


class RPiPipelineError(Exception):
    """Base exception for RPi validation pipeline."""
    pass


class RPiBusyError(RPiPipelineError):
    """Raised when RPi is busy and backoff timeout expires."""
    pass


class RPiPlaybackStartedInterrupt(RPiPipelineError):
    """Raised when user playback starts during candidate/test run."""
    pass


class BrowserForbiddenOnRPiError(RPiPipelineError):
    """Raised if a browser execution is attempted on RPi host."""
    pass


class DirtyCheckoutError(RPiPipelineError):
    """Raised when candidate staging encounters uncommitted dirty files."""
    pass


class SHAMismatchError(RPiPipelineError):
    """Raised when candidate SHA does not match expected SHA."""
    pass


class LockContentionError(RPiPipelineError):
    """Raised when pipeline flock cannot be acquired."""
    pass


class PushForbiddenOnRPiError(RPiPipelineError):
    """Raised if git push is attempted on RPi host."""
    pass


def get_current_pid_family() -> Set[int]:
    """Get current process PID and ancestor PIDs excluding init (PID 1)."""
    pids = {os.getpid()}
    try:
        pid = os.getpid()
        while pid > 1:
            with open(f"/proc/{pid}/stat", "r") as f:
                content = f.read()
            rpar_idx = content.rfind(")")
            if rpar_idx == -1:
                break
            fields = content[rpar_idx + 1:].strip().split()
            ppid = int(fields[1])
            if ppid <= 1 or ppid in pids:
                break
            pids.add(ppid)
            pid = ppid
    except Exception:
        pass
    return pids


def parse_proc_ps_output(ps_output: str) -> List[Dict[str, Any]]:
    """Parse output from `ps -eo pid,ppid,pcpu,comm,args` into process dictionaries."""
    processes: List[Dict[str, Any]] = []
    lines = ps_output.strip().splitlines()
    if not lines:
        return processes
    
    header = lines[0].lower()
    start_line = 1 if "pid" in header else 0

    for line in lines[start_line:]:
        parts = line.strip().split(None, 4)
        if len(parts) < 4:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
            pcpu = float(parts[2])
            comm = parts[3]
            args = parts[4] if len(parts) > 4 else comm
            processes.append({
                "pid": pid,
                "ppid": ppid,
                "pcpu": pcpu,
                "comm": comm,
                "args": args,
            })
        except ValueError:
            continue
    return processes


def is_exact_playback_process(proc: Dict[str, Any]) -> bool:
    """Determine if process is an authoritative playback/gaming process.

    Strictly matches exact executables ('mpv', 'steamlink', 'moonlight').
    Also detects TUI dashboard processes ('tui.py').
    Must NOT match helper scripts like 'keys2mpv.py' or python wrappers.
    """
    comm = proc.get("comm", "").strip()
    args = proc.get("args", "").strip()

    if comm in ("mpv", "steamlink", "moonlight"):
        return True

    first_arg = args.split()[0] if args else ""
    basename = os.path.basename(first_arg)
    if basename in ("mpv", "steamlink", "moonlight"):
        return True

    if comm in ("python", "python3", "python3.12") or "python" in first_arg:
        if "keys2mpv.py" in args:
            return False
        # Check for TUI dashboard process
        if "tui.py" in args or basename == "tui.py":
            return True

    return False


def get_active_mode(mode_file_path: Optional[str] = None) -> Optional[str]:
    """Read active dashboard mode from file if present."""
    paths_to_check = []
    if mode_file_path:
        paths_to_check.append(mode_file_path)
    paths_to_check.extend([
        ".dlnain-mode.json",
        "/tmp/.active_mode",
        "/home/milhy777/rpi-dashboard/.dlnain-mode.json"
    ])
    for path in paths_to_check:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if "mode" in content:
                    import json
                    data = json.loads(content)
                    return data.get("mode")
                return content
            except Exception:
                pass
    return None


class RPiGuard:
    """Hardware guard enforcing RPi resource thresholds and playback non-disruption."""

    def __init__(
        self,
        cpu_threshold_pct: float = 20.0,
        ram_min_free_mb: float = 50.0,
        temp_max_c: float = 75.0,
        proc_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        temp_provider: Optional[Callable[[], float]] = None,
        ram_provider: Optional[Callable[[], float]] = None,
        mode_file_path: Optional[str] = None,
    ):
        self.cpu_threshold_pct = cpu_threshold_pct
        self.ram_min_free_mb = ram_min_free_mb
        self.temp_max_c = temp_max_c
        self.proc_provider = proc_provider
        self.temp_provider = temp_provider
        self.ram_provider = ram_provider
        self.mode_file_path = mode_file_path

    def _get_processes(self) -> List[Dict[str, Any]]:
        if self.proc_provider:
            return self.proc_provider()
        try:
            res = subprocess.run(
                ["ps", "-eo", "pid,ppid,pcpu,comm,args"],
                capture_output=True,
                text=True,
                check=True,
            )
            return parse_proc_ps_output(res.stdout)
        except Exception:
            processes: List[Dict[str, Any]] = []
            return processes

    def _get_ram_free_mb(self) -> float:
        if self.ram_provider:
            return self.ram_provider()
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem_map = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    mem_map[key] = int(val)
            avail_kb = mem_map.get("MemAvailable", mem_map.get("MemFree", 0))
            return avail_kb / 1024.0
        except Exception:
            return 500.0

    def _get_temp_c(self) -> float:
        if self.temp_provider:
            return self.temp_provider()
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    return float(f.read().strip()) / 1000.0
        except Exception:
            pass
        return 45.0

    def _get_sustained_user_cpu_pct(self, exclude_pids: Set[int], sample_count: int = 3, sample_delay: float = 0.5) -> float:
        """Get sustained user CPU percentage by sampling multiple times.

        Takes multiple samples to avoid false positives from brief CPU spikes.
        Returns the average CPU usage across all samples.
        """
        total_cpu = 0.0
        for _ in range(sample_count):
            processes = self._get_processes()
            sample_cpu = 0.0
            for proc in processes:
                pid = proc.get("pid", 0)
                comm = proc.get("comm", "").strip()
                if pid not in exclude_pids and comm not in ("ps", "top", "pgrep", "pi"):
                    sample_cpu += proc.get("pcpu", 0.0)
            total_cpu += sample_cpu
            if _ < sample_count - 1:
                time.sleep(sample_delay)
        return total_cpu / sample_count

    def check_status(self, exclude_pids: Optional[Set[int]] = None, sustained_cpu_samples: int = 1) -> Dict[str, Any]:
        """Check live RPi hardware status and process activity.

        For sustained CPU measurement, takes multiple samples to avoid brief spike
        false positives. Set sustained_cpu_samples > 1 for sustained measurement.
        Default is 1 for backwards compatibility (instantaneous check).
        """
        if exclude_pids is None:
            exclude_pids = get_current_pid_family()

        processes = self._get_processes()
        active_playback = False
        active_mode = get_active_mode(self.mode_file_path)

        # Check for playback processes in the snapshot
        for proc in processes:
            if is_exact_playback_process(proc):
                comm = proc.get("comm", "").strip()
                args = proc.get("args", "").strip()
                if ("tui.py" in args or comm == "tui.py") and active_mode not in ("tui", "mpv", "steamlink", "moonlight", "spotify", "media_player"):
                    continue
                active_playback = True
                break

        # Get sustained CPU measurement (average across multiple samples)
        if sustained_cpu_samples > 1:
            user_cpu_pct = self._get_sustained_user_cpu_pct(exclude_pids, sustained_cpu_samples)
        else:
            # Single sample for backwards compatibility
            user_cpu_pct = 0.0
            for proc in processes:
                pid = proc.get("pid", 0)
                comm = proc.get("comm", "").strip()
                if pid not in exclude_pids and comm not in ("ps", "top", "pgrep", "pi"):
                    user_cpu_pct += proc.get("pcpu", 0.0)

        if active_mode in ("mpv", "steamlink", "moonlight", "spotify", "media_player", "tui"):
            active_playback = True

        ram_free_mb = self._get_ram_free_mb()
        temp_c = self._get_temp_c()

        busy = False
        reasons = []

        if active_playback:
            busy = True
            reasons.append("Active playback/gaming/TUI detected")
        if user_cpu_pct > self.cpu_threshold_pct:
            busy = True
            reasons.append(f"User CPU usage {user_cpu_pct:.1f}% exceeds {self.cpu_threshold_pct}%")
        if ram_free_mb < self.ram_min_free_mb:
            busy = True
            reasons.append(f"Available RAM {ram_free_mb:.1f}MB below {self.ram_min_free_mb}MB limit")
        if temp_c > self.temp_max_c:
            busy = True
            reasons.append(f"CPU temperature {temp_c:.1f}°C exceeds {self.temp_max_c}°C limit")

        return {
            "busy": busy,
            "reasons": reasons,
            "active_playback": active_playback,
            "user_cpu_pct": user_cpu_pct,
            "ram_free_mb": ram_free_mb,
            "temp_c": temp_c,
            "active_mode": active_mode,
        }

    def wait_until_idle(
        self,
        max_wait_seconds: float = 30.0,
        backoff_seconds: float = 2.0,
        exclude_pids: Optional[Set[int]] = None,
        sustained_cpu_samples: int = 1,
    ) -> Dict[str, Any]:
        """Wait up to max_wait_seconds with backoff until system is idle."""
        start = time.time()
        last_status = self.check_status(exclude_pids=exclude_pids, sustained_cpu_samples=sustained_cpu_samples)

        while last_status["busy"]:
            elapsed = time.time() - start
            if elapsed >= max_wait_seconds:
                raise RPiBusyError(
                    f"RPi remained busy after {max_wait_seconds}s timeout: {', '.join(last_status['reasons'])}"
                )
            time.sleep(backoff_seconds)
            last_status = self.check_status(exclude_pids=exclude_pids, sustained_cpu_samples=sustained_cpu_samples)

        return last_status

    def run_protected_command(
        self,
        cmd: List[str],
        cancel_callback: Optional[Callable[[], None]] = None,
        poll_interval: float = 1.0,
        exclude_pids: Optional[Set[int]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Run candidate command while actively monitoring for playback start."""
        if exclude_pids is None:
            exclude_pids = get_current_pid_family()

        status = self.check_status(exclude_pids=exclude_pids)
        if status["busy"]:
            raise RPiBusyError(f"Cannot start candidate execution: {', '.join(status['reasons'])}")

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=cwd)
        exclude_pids.add(proc.pid)

        try:
            while proc.poll() is None:
                current_status = self.check_status(exclude_pids=exclude_pids)
                if current_status["active_playback"]:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    if cancel_callback:
                        cancel_callback()
                    raise RPiPlaybackStartedInterrupt("User playback started during candidate execution; aborted candidate process.")
                time.sleep(poll_interval)

            stdout, stderr = proc.communicate()
            return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)
        except Exception:
            if proc.poll() is None:
                proc.kill()
            raise
