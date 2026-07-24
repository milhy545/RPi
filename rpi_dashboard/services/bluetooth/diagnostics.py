"""Bounded Bluetooth/audio failure classification and resource diagnostics."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FailureRule:
    id: str
    pattern: re.Pattern[str]
    layer: str
    diagnosis: str
    mitigation: str
    verification: str


FAILURE_RULES = (
    FailureRule(
        "hci_command_timeout",
        re.compile(r"(command|opcode).*?(tx )?timeout|tx timeout", re.I),
        "controller/firmware",
        "The controller did not complete an HCI command in time.",
        "Stop duplicate discovery, keep retries bounded per adapter, and inspect USB power/firmware before any reset.",
        "Run independent discovery on hci0 and hci1 and confirm no timeout recurs while the other adapter remains usable.",
    ),
    FailureRule(
        "hci_frame_reassembly",
        re.compile(r"frame reassembly|unexpected continuation|malformed.*frame", re.I),
        "controller/transport",
        "The kernel rejected or lost part of an HCI transport frame.",
        "Correlate with the owning adapter, USB errors, and concurrent scan load; do not restart both adapters together.",
        "Repeat the triggering scan/connection with bounded btmon capture and verify the counter remains stable.",
    ),
    FailureRule(
        "security_unavailable",
        re.compile(r"security requested but not available|security.*not available", re.I),
        "link security",
        "The requested encrypted/authenticated link was unavailable on that controller relationship.",
        "Use the bonded owning adapter, explicit pairing agent, and reject cross-adapter discovery shadows.",
        "Reconnect the paired device through its stored adapter and confirm encryption/services resolve.",
    ),
    FailureRule(
        "a2dp_profile_busy",
        re.compile(r"a2dp.*(busy|resource busy)|device or resource busy", re.I),
        "BlueZ/PipeWire profile",
        "Another endpoint or profile transition already owns the A2DP transport.",
        "Serialize device operations, select the advertised role explicitly, and wait for the old transport to release.",
        "Switch A2DP roles repeatedly and confirm one transport plus a structured operation_busy response.",
    ),
    FailureRule(
        "hfp_connection_refused",
        re.compile(r"(hfp|hsp|hands.?free).*connection refused|connection refused.*(hfp|hsp)", re.I),
        "remote headset profile",
        "The peer did not accept the requested HFP/HSP role or telephony backend was missing.",
        "Expose the failure as profile_unavailable and require compatible HF/AG roles plus the WirePlumber telephony backend.",
        "Negotiate the headset profile with a compatible endpoint and verify both PipeWire sink and source nodes.",
    ),
    FailureRule(
        "xbox_hid_gatt",
        re.compile(r"(xbox|hogp|gatt).*(report|battery|notification).*(fail|error)|report map.*(fail|error)", re.I),
        "HID/GATT",
        "A controller HID report or GATT notification could not be initialized.",
        "Keep controller input diagnostics separate from Bluetooth connected state and retry only the failed service.",
        "Confirm a Linux input event device, stable battery telemetry, and no duplicate controller relationship.",
    ),
    FailureRule(
        "xbox_rumble_initialization",
        re.compile(r"(xbox|xpad|rumble).*(init|initializ|timeout|16 second)", re.I),
        "controller driver",
        "Controller force-feedback initialization was slow or timed out.",
        "Do not block dashboard readiness on rumble; measure driver initialization and keep input usable independently.",
        "Reconnect the controller and time input availability separately from force-feedback availability.",
    ),
    FailureRule(
        "pipewire_xrun",
        re.compile(r"\bxrun\b|underrun|overrun", re.I),
        "PipeWire scheduling/buffer",
        "An audio graph missed its real-time processing deadline.",
        "Record route, codec, quantum, CPU load, and adapter before changing buffers; tune only the failing route.",
        "Run the same audio route under measured load and compare bounded xrun counts and latency.",
    ),
)


def analyze_log_text(text: str, sample_limit: int = 3) -> list[dict[str, Any]]:
    """Classify known failure lines without retaining an unbounded journal."""
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    results = []
    for rule in FAILURE_RULES:
        matches = [line for line in lines if rule.pattern.search(line)]
        if not matches:
            continue
        results.append(
            {
                "id": rule.id,
                "count": len(matches),
                "layer": rule.layer,
                "diagnosis": rule.diagnosis,
                "mitigation": rule.mitigation,
                "verification": rule.verification,
                "samples": matches[-sample_limit:],
            }
        )
    return results


def collect_diagnostics() -> dict[str, Any]:
    """Collect bounded read-only versions, logs, adapter counters, and process cost."""
    log_parts = []
    log_errors = []
    for command in (
        ["journalctl", "-b", "--no-pager", "-n", "2000", "-u", "bluetooth.service"],
        ["journalctl", "-b", "-k", "--no-pager", "-n", "2000"],
        ["journalctl", "--user", "-b", "--no-pager", "-n", "1000", "-u", "wireplumber.service"],
    ):
        result = _run(command, timeout=8)
        if result.returncode == 0:
            log_parts.append(result.stdout)
        else:
            log_errors.append((result.stderr or result.stdout).strip())
    return {
        "ok": True,
        "versions": {
            "bluez": _version(["bluetoothd", "-v"]),
            "pipewire": _version(["pipewire", "--version"]),
            "wireplumber": _version(["wireplumber", "--version"]),
        },
        "failure_classes": analyze_log_text("\n".join(log_parts)),
        "log_errors": [error for error in log_errors if error][:4],
        "adapters": _adapter_statistics(),
        "resources": _resource_snapshot(),
        "bounded": {
            "bluetooth_log_lines": 2000,
            "kernel_log_lines": 2000,
            "wireplumber_log_lines": 1000,
            "failure_samples_per_class": 3,
        },
    }


def _run(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr=str(exc))


def _version(command: list[str]) -> str | None:
    result = _run(command, timeout=3)
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0 or not output:
        return None
    lines = output.splitlines()
    return next((line for line in lines if re.search(r"\d+\.\d+", line)), lines[0])


def _adapter_statistics() -> list[dict[str, Any]]:
    rows = []
    for adapter in sorted(Path("/sys/class/bluetooth").glob("hci*")):
        statistics = {}
        for path in sorted((adapter / "statistics").glob("*")):
            try:
                statistics[path.name] = int(path.read_text().strip())
            except (OSError, ValueError):
                continue
        rows.append({"name": adapter.name, "statistics": statistics})
    return rows


def _resource_snapshot() -> dict[str, Any]:
    status: dict[str, str] = {}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                if key in {"VmRSS", "VmSize", "Threads"}:
                    status[key] = value.strip()
    except OSError:
        pass
    load = os.getloadavg()
    return {
        "process_rss": status.get("VmRSS"),
        "process_virtual": status.get("VmSize"),
        "threads": status.get("Threads"),
        "load_average": [round(value, 2) for value in load],
        "cpu_count": os.cpu_count(),
    }
