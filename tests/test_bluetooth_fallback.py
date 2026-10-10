"""Regression tests for the adapter-aware bluetoothctl fallback."""

import io
import subprocess

import pytest

from rpi_dashboard.services.bluetooth import fallback
from rpi_dashboard.services.bluetooth.fallback import BluetoothctlBackend


def completed(stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["bluetoothctl"], 0, stdout=stdout, stderr="")


def test_bluetoothctl_serializes_command_arguments_on_one_line(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    backend = BluetoothctlBackend()

    backend._run([["select", "AA:BB:CC:DD:EE:FF"], ["info", "11:22:33:44:55:66"]])

    assert captured["input"] == (
        "select AA:BB:CC:DD:EE:FF\n"
        "info 11:22:33:44:55:66\n"
        "quit\n"
    )


def test_pairing_enables_a_headless_bluez_agent(monkeypatch):
    backend = BluetoothctlBackend()
    adapter = fallback.Adapter(
        id="adapter-aabbcc000001",
        bluez_path="/org/bluez/hci0",
        index=0,
        address="AA:BB:CC:00:00:01",
        present=True,
        powered=True,
    )
    monkeypatch.setattr(backend, "_adapter_by_id", lambda adapter_id: adapter)
    captured = {}

    def fake_pair(target_adapter, mac):
        captured["adapter"] = target_adapter
        captured["mac"] = mac
        return completed("Pairing successful"), True

    monkeypatch.setattr(backend, "_pair_with_agent", fake_pair)

    operation = backend._device_command(
        "pair",
        adapter.id,
        f"{adapter.id}/11:22:33:44:55:66",
    )

    assert operation.state == "succeeded"
    assert captured == {"adapter": adapter, "mac": "11:22:33:44:55:66"}


def test_pairing_waits_for_bluez_to_report_paired(monkeypatch):
    backend = BluetoothctlBackend(timeout=1)
    adapter = fallback.Adapter(
        id="adapter-aabbcc000001",
        bluez_path="/org/bluez/hci0",
        index=0,
        address="AA:BB:CC:00:00:01",
        present=True,
        powered=True,
    )
    monkeypatch.setattr(backend, "_adapter_by_id", lambda adapter_id: adapter)
    monkeypatch.setattr(
        backend,
        "_pair_with_agent",
        lambda target_adapter, mac: (
            completed("Agent registered\nPairing successful"),
            True,
        ),
    )

    operation = backend._device_command(
        "pair",
        adapter.id,
        f"{adapter.id}/11:22:33:44:55:66",
    )

    assert operation.state == "succeeded"


def test_pairing_bounds_pairability_to_selected_adapter(monkeypatch):
    """Pairing opens and closes bondability around one explicit controller."""
    backend = BluetoothctlBackend(timeout=1)
    adapter = fallback.Adapter(
        id="adapter-aabbcc000001",
        bluez_path="/org/bluez/hci0",
        index=0,
        address="AA:BB:CC:00:00:01",
        present=True,
        powered=True,
    )

    class PairProcess:
        def __init__(self):
            self.stdin = io.StringIO()
            self.returncode = 0
            self.killed = False

        def communicate(self, timeout=None):
            return "Agent registered\nPairing successful\n", None

        def kill(self):
            self.killed = True

    process = PairProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(fallback.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(backend, "_wait_for_device_property", lambda *args: True)

    result, succeeded = backend._pair_with_agent(adapter, "11:22:33:44:55:66")

    assert succeeded is True
    assert result.returncode == 0
    assert process.stdin.getvalue().splitlines() == [
        "select AA:BB:CC:00:00:01",
        "pairable on",
        "pair 11:22:33:44:55:66",
        "pairable off",
        "quit",
    ]


def test_pairing_closes_pairability_after_failure(monkeypatch):
    """A failed bond attempt must not leave the adapter pairable."""
    backend = BluetoothctlBackend(timeout=1)
    adapter = fallback.Adapter(
        id="adapter-aabbcc000001",
        bluez_path="/org/bluez/hci0",
        index=0,
        address="AA:BB:CC:00:00:01",
        present=True,
        powered=True,
    )

    class PairProcess:
        def __init__(self):
            self.stdin = io.StringIO()
            self.returncode = 0

        def communicate(self, timeout=None):
            return "Agent registered\nFailed to pair\n", None

        def kill(self):
            return None

    process = PairProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(fallback.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(backend, "_wait_for_device_property", lambda *args: False)

    _result, succeeded = backend._pair_with_agent(adapter, "11:22:33:44:55:66")

    assert succeeded is False
    assert "pairable off\nquit\n" in process.stdin.getvalue()


def test_pairing_keeps_other_adapter_closed(monkeypatch):
    """A global BlueZ agent must not expose the non-selected controller."""
    backend = BluetoothctlBackend(timeout=1)
    selected = fallback.Adapter(
        id="adapter-aabbcc000001",
        bluez_path="/org/bluez/hci0",
        index=0,
        address="AA:BB:CC:00:00:01",
        present=True,
        powered=True,
    )
    other = fallback.Adapter(
        id="adapter-aabbcc000002",
        bluez_path="/org/bluez/hci1",
        index=1,
        address="AA:BB:CC:00:00:02",
        present=True,
        powered=True,
    )

    class PairProcess:
        def __init__(self):
            self.stdin = io.StringIO()
            self.returncode = 0

        def communicate(self, timeout=None):
            return "Agent registered\nPairing successful\n", None

        def kill(self):
            return None

    process = PairProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(fallback.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(backend, "_pairing_peers", lambda _selected: (other,))
    monkeypatch.setattr(backend, "_wait_for_device_property", lambda *args: True)

    _result, succeeded = backend._pair_with_agent(selected, "11:22:33:44:55:66")

    assert succeeded is True
    commands = process.stdin.getvalue().splitlines()
    assert commands[:5] == [
        "select AA:BB:CC:00:00:02",
        "pairable off",
        "select AA:BB:CC:00:00:01",
        "pairable on",
        "pair 11:22:33:44:55:66",
    ]


def test_fallback_preserves_distinct_sysfs_adapter_indices(monkeypatch):
    backend = BluetoothctlBackend()
    addresses = ["AA:BB:CC:00:00:01", "AA:BB:CC:00:00:02"]

    def fake_backend_run(commands):
        if commands == [["list"]]:
            return completed("\n".join(f"Controller {address} Adapter" for address in addresses))
        return completed("Powered: yes\nDiscoverable: no\nPairable: yes\n")

    monkeypatch.setattr(backend, "_run", fake_backend_run)
    monkeypatch.setattr(
        fallback,
        "_adapter_index_by_address",
        lambda address: addresses.index(address) + 3,
    )

    adapters = backend._read_adapters()

    assert [adapter.index for adapter in adapters] == [3, 4]
    assert [adapter.bluez_path for adapter in adapters] == [
        "/org/bluez/hci3",
        "/org/bluez/hci4",
    ]


def test_fallback_device_state_exposes_persistent_bond():
    adapter = fallback.Adapter(
        id="adapter-aabbcc000001",
        bluez_path="/org/bluez/hci0",
        index=0,
        address="AA:BB:CC:00:00:01",
    )

    device = fallback._device_from_info(
        adapter,
        {"address": "11:22:33:44:55:66", "name": "Speaker"},
        "Device 11:22:33:44:55:66\nPaired: yes\nBonded: yes\n",
    )

    assert device.paired is True
    assert device.bonded is True


@pytest.mark.asyncio
async def test_fallback_state_retains_completed_operations(monkeypatch):
    backend = BluetoothctlBackend()
    monkeypatch.setattr(backend, "_read_adapters", lambda: [])
    backend._operation("test", state="succeeded")

    state = await backend.state()

    assert state.operations[-1].type == "test"
    assert state.events[-1].type == "operation_succeeded"
