#!/usr/bin/env python3
"""
24-hour soak test for RPi Dashboard verification.

Captures resource usage, log events, and system health metrics
continuously for the specified duration.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence


class SoakTest:
    def __init__(self, duration_hours: float = 24, interval_seconds: int = 60):
        self.duration_hours = duration_hours
        self.interval = interval_seconds
        self.project_root = Path("/home/milhy777/rpi-dashboard")
        self.output_dir = self.project_root / "conductor" / "ci" / "soak"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.start_time = time.time()
        self.end_time = self.start_time + (duration_hours * 3600)
        self.samples: List[Dict[str, Any]] = []

    def run_command(self, cmd: Sequence[str]) -> tuple[int, str, str]:
        """Run command and return (exit_code, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd, cwd=self.project_root,
                capture_output=True, text=True, timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def capture_snapshot(self) -> Dict[str, Any]:
        """Capture a single snapshot of system state."""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": time.time() - self.start_time
        }

        # System info
        rc, out, _ = self.run_command(["uname", "-a"])
        if rc == 0:
            snapshot["kernel"] = out

        # Uptime
        rc, out, _ = self.run_command(["cat", "/proc/uptime"])
        if rc == 0:
            snapshot["uptime_seconds"] = float(out.split()[0])

        # Memory
        lines: list[str] = []
        rc, out, _ = self.run_command(["free", "-b"])
        if rc == 0:
            lines = out.strip().split('\n')
            if len(lines) >= 2:
                mem = lines[1].split()
                snapshot["memory"] = {
                    "total": int(mem[1]),
                    "used": int(mem[2]),
                    "free": int(mem[3]),
                    "available": int(mem[6]) if len(mem) > 6 else int(mem[3])
                }

        # Swap
        if len(lines) >= 3:
            swap = lines[2].split()
            snapshot["swap"] = {
                "total": int(swap[1]),
                "used": int(swap[2]),
                "free": int(swap[3])
            }

        # CPU per core
        rc, out, _ = self.run_command(["mpstat", "-P", "ALL", "1", "1"])
        if rc == 0:
            snapshot["cpu"] = out

        # Load average
        rc, out, _ = self.run_command(["cat", "/proc/loadavg"])
        if rc == 0:
            snapshot["loadavg"] = out.strip()

        # Temperature
        rc, out, _ = self.run_command(["vcgencmd", "measure_temp"])
        if rc == 0:
            snapshot["temperature_c"] = float(out.replace("temp=", "").replace("'C", ""))

        # Disk
        rc, out, _ = self.run_command(["df", "-h", "/"])
        if rc == 0:
            snapshot["disk"] = out.strip()

        # Process count
        rc, out, _ = self.run_command(["ps", "-e", "--no-headers"])
        if rc == 0:
            snapshot["process_count"] = len(out.splitlines())

        # Project services
        for svc in ["dashboard@milhy777", "mpv@milhy777", "report-processor", "tmux-restore"]:
            rc, out, _ = self.run_command(["systemctl", "is-active", svc])
            snapshot[f"service_{svc.replace('@', '_').replace('-', '_')}"] = out if rc == 0 else "inactive"

        # Audio (PipeWire)
        rc, out, _ = self.run_command(["pactl", "info"])
        if rc == 0:
            snapshot["pipewire"] = "\n".join(
                line for line in out.splitlines()
                if line.startswith(("Server Name:", "Default Sink:", "Default Source:"))
            )

        # Bluetooth
        rc, out, _ = self.run_command(["bluetoothctl", "show"])
        if rc == 0:
            snapshot["bluetooth"] = "\n".join(
                line for line in out.splitlines()
                if line.strip().startswith(("Powered:", "Discoverable:", "Pairable:"))
            )

        # Network
        rc, out, _ = self.run_command(["ip", "-brief", "addr", "show"])
        if rc == 0:
            snapshot["network"] = out.strip()

        # Journal errors (last interval)
        rc, out, _ = self.run_command(
            ["journalctl", "--since", "1 minute ago", "-p", "err", "--no-pager", "-n", "20"]
        )
        if rc == 0 and out:
            snapshot["journal_errors"] = out.strip()

        return snapshot

    def run(self):
        """Run the soak test."""
        print(f"Starting {self.duration_hours}h soak test")
        print(f"Interval: {self.interval}s")
        print(f"Output: {self.output_dir}")
        print(f"End time: {datetime.fromtimestamp(self.end_time).isoformat()}")

        sample_count = 0
        while time.time() < self.end_time:
            sample_start = time.time()
            snapshot = self.capture_snapshot()
            self.samples.append(snapshot)
            sample_count += 1

            # Print progress
            elapsed = time.time() - self.start_time
            remaining = self.end_time - time.time()
            print(f"[{datetime.now().isoformat()}] Sample #{sample_count} | "
                  f"Elapsed: {elapsed/3600:.2f}h | Remaining: {remaining/3600:.2f}h | "
                  f"Mem: {snapshot.get('memory', {}).get('used', 0)/1e9:.1f}GB | "
                  f"Temp: {snapshot.get('temperature_c', 0):.1f}°C | "
                  f"Load: {snapshot.get('loadavg', '?')}")

            # Save intermediate every 10 samples
            if sample_count % 10 == 0:
                self.save_results()

            # Sleep until next interval
            elapsed_sample = time.time() - sample_start
            sleep_time = max(0, self.interval - elapsed_sample)
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Final save
        self.save_results()
        print(f"\nSoak test complete. {sample_count} samples collected.")
        print(f"Results saved to: {self.output_dir}")

    def save_results(self):
        """Save results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"soak_{timestamp}.json"

        results = {
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
            "duration_hours": self.duration_hours,
            "interval_seconds": self.interval,
            "sample_count": len(self.samples),
            "samples": self.samples
        }

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        # Also save latest as "latest.json"
        latest_file = self.output_dir / "latest.json"
        with open(latest_file, 'w') as f:
            json.dump(results, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="RPi Dashboard 24h Soak Test")
    parser.add_argument("--duration", type=float, default=24,
                        help="Duration in hours (default: 24)")
    parser.add_argument("--interval", type=int, default=60,
                        help="Sampling interval in seconds (default: 60)")
    parser.add_argument("--output-dir", type=Path,
                        help="Output directory (default: conductor/ci/soak)")

    args = parser.parse_args()

    test = SoakTest(duration_hours=args.duration, interval_seconds=args.interval)
    if args.output_dir:
        test.output_dir = args.output_dir
        test.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        test.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Saving partial results...")
        test.save_results()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        test.save_results()
        sys.exit(1)


if __name__ == "__main__":
    main()
