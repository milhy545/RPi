"""Adapter-aware bluetoothctl fallback backend.

This backend is intentionally marked degraded. It preserves existing runtime
behaviour while the BlueZ D-Bus backend is built, but it still routes actions
through the shared Bluetooth state contract and selects adapters explicitly.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from collections import deque
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from .fake import SAMSUNG_SOUNDBAR_MAC
from .models import Adapter
from .models import BackendHealth
from .models import BluetoothError
from .models import BluetoothState
from .models import ControllerReadiness
from .models import Device
from .models import Event
from .models import Operation
from .models import ReadinessStep
from .models import SoundbarReadiness
from .models import adapter_id_from_address
from .models import classify_device
from .models import make_device_key
from .models import hide_non_owner_duplicates
from .models import normalize_address


class BluetoothctlBackend:
    """Bluetooth backend backed by bounded `bluetoothctl` subprocess calls."""

    def __init__(self, timeout: int = 8, history_limit: int = 50) -> None:
        self.timeout = timeout
        self._counter = 0
        self._last_state: BluetoothState | None = None
        self._operations: deque[Operation] = deque(maxlen=history_limit)
        self._events: deque[Event] = deque(maxlen=history_limit)

    async def state(self) -> BluetoothState:
        """Read state through bluetoothctl without changing device state."""
        return await asyncio.to_thread(self._state_sync)

    async def events(self):
        """The subprocess fallback does not have a live event stream."""
        if False:
            yield None

    async def reconcile(self) -> BluetoothState:
        """Re-read state from bluetoothctl."""
        return await self.state()

    async def set_adapter_power(self, adapter_id: str, powered: bool) -> Operation:
        """Set adapter power."""
        return await asyncio.to_thread(
            self._adapter_command,
            "set_power",
            adapter_id,
            ["power", "on" if powered else "off"],
        )

    async def set_adapter_discoverable(
        self,
        adapter_id: str,
        discoverable: bool,
        timeout: int = 0,
    ) -> Operation:
        """Set adapter discoverability with an explicit timeout."""
        return await asyncio.to_thread(
            self._adapter_command,
            "set_discoverable",
            adapter_id,
            [
                ["discoverable-timeout", str(max(0, timeout))],
                ["discoverable", "on" if discoverable else "off"],
            ],
        )

    async def start_discovery(self, adapter_id: str) -> Operation:
        """Start discovery on a selected adapter."""
        return await asyncio.to_thread(
            self._adapter_command,
            "start_discovery",
            adapter_id,
            ["scan", "on"],
        )

    async def stop_discovery(self, adapter_id: str) -> Operation:
        """Stop discovery on a selected adapter."""
        return await asyncio.to_thread(
            self._adapter_command,
            "stop_discovery",
            adapter_id,
            ["scan", "off"],
        )

    async def pair(self, adapter_id: str, device_key: str) -> Operation:
        """Pair a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "pair", adapter_id, device_key)

    async def trust(self, adapter_id: str, device_key: str) -> Operation:
        """Trust a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "trust", adapter_id, device_key)

    async def untrust(self, adapter_id: str, device_key: str) -> Operation:
        """Untrust a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "untrust", adapter_id, device_key)

    async def block(self, adapter_id: str, device_key: str) -> Operation:
        """Block a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "block", adapter_id, device_key)

    async def unblock(self, adapter_id: str, device_key: str) -> Operation:
        """Unblock a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "unblock", adapter_id, device_key)

    async def connect(self, adapter_id: str, device_key: str) -> Operation:
        """Connect a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "connect", adapter_id, device_key)

    async def disconnect(self, adapter_id: str, device_key: str) -> Operation:
        """Disconnect a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "disconnect", adapter_id, device_key)

    async def connect_profile(
        self,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
    ) -> Operation:
        """Connect one advertised profile using the selected controller."""
        return await asyncio.to_thread(
            self._device_profile_command,
            "connect_profile",
            adapter_id,
            device_key,
            profile_uuid,
        )

    async def disconnect_profile(
        self,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
    ) -> Operation:
        """Disconnect one advertised profile using the selected controller."""
        return await asyncio.to_thread(
            self._device_profile_command,
            "disconnect_profile",
            adapter_id,
            device_key,
            profile_uuid,
        )

    async def media_control(
        self,
        adapter_id: str,
        device_key: str,
        action: str,
        value: int | None = None,
    ) -> Operation:
        """Report that bluetoothctl cannot expose deterministic AVRCP players."""
        error = BluetoothError(
            "profile_unavailable",
            "AVRCP control requires the BlueZ D-Bus backend",
            adapter_id=adapter_id,
            device_key=device_key,
        )
        return self._operation(
            f"media_{action}",
            adapter_id=adapter_id,
            device_key=device_key,
            state="failed",
            error=error,
        )

    async def remove(self, adapter_id: str, device_key: str) -> Operation:
        """Remove a device using an explicit controller selection."""
        return await asyncio.to_thread(self._device_command, "remove", adapter_id, device_key)

    async def cancel(self, operation_id: str) -> Operation:
        """Cancel is not supported by the subprocess fallback."""
        error = BluetoothError(
            "unsupported",
            "bluetoothctl fallback cannot cancel completed subprocess operations",
        )
        return self._operation("cancel", state="failed", error=error)

    def _state_sync(self) -> BluetoothState:
        try:
            adapters = self._read_adapters()
            devices: list[Device] = []
            for adapter in adapters:
                devices.extend(self._read_devices(adapter))
            devices = hide_non_owner_duplicates(devices)
            state = BluetoothState(
                backend=BackendHealth(
                    name="bluetoothctl",
                    degraded=True,
                    available=True,
                    message="Compatibility fallback active until BlueZ D-Bus backend is enabled",
                ),
                adapters=tuple(adapters),
                devices=tuple(devices),
                operations=tuple(self._operations),
                diagnostics=self._diagnostics(adapters, devices),
                events=tuple(self._events),
            )
            self._last_state = state
            return state
        except Exception as exc:
            error = BluetoothError(
                "backend_unavailable",
                "bluetoothctl state read failed",
                retryable=True,
                detail=str(exc),
            )
            state = BluetoothState(
                backend=BackendHealth(
                    name="bluetoothctl",
                    degraded=True,
                    available=False,
                    message=str(exc),
                ),
                diagnostics={
                    "bluez": {"available": False, "error": error.to_dict()},
                    "soundbar": SoundbarReadiness().to_dict(),
                    "controllers": ControllerReadiness(
                        blockers=("Bluetooth backend unavailable",)
                    ).to_dict(),
                    "steamlink": {"available": None, "path": ""},
                },
                operations=tuple(self._operations),
                events=tuple(self._events),
                ok=False,
            )
            self._last_state = state
            return state

    def _read_adapters(self) -> list[Adapter]:
        listed = self._run([["list"]]).stdout
        adapters = []
        for line in listed.splitlines():
            if not line.startswith("Controller "):
                continue
            parts = line.split(maxsplit=2)
            if len(parts) < 2:
                continue
            address = normalize_address(parts[1])
            name = parts[2] if len(parts) > 2 else ""
            adapter_id = adapter_id_from_address(address)
            show = self._run([["select", address], ["show"]]).stdout
            props = _parse_show(show)
            index = _adapter_index_by_address(address)
            bluez_path = f"/org/bluez/hci{index}" if index is not None else f"bluetoothctl://{address}"
            adapters.append(
                Adapter(
                    id=adapter_id,
                    bluez_path=bluez_path,
                    index=index,
                    address=address,
                    address_type=props.get("address_type", "public"),
                    name=props.get("name", name),
                    alias=props.get("alias", name),
                    modalias=props.get("modalias", ""),
                    powered=props.get("powered", "no") == "yes",
                    discoverable=props.get("discoverable", "no") == "yes",
                    pairable=props.get("pairable", "no") == "yes",
                    discovering=props.get("discovering", "no") == "yes",
                    present=True,
                    backend="bluetoothctl",
                )
            )
        return adapters

    def _read_devices(self, adapter: Adapter) -> list[Device]:
        output = self._run([["select", adapter.address], ["devices"]]).stdout
        devices = []
        for raw in _parse_device_lines(output):
            info = self._run([["select", adapter.address], ["info", raw["address"]]]).stdout
            devices.append(_device_from_info(adapter, raw, info))
        return devices

    def _adapter_command(
        self,
        operation_type: str,
        adapter_id: str,
        command: list[str] | list[list[str]],
    ) -> Operation:
        adapter = self._adapter_by_id(adapter_id)
        if adapter is None:
            error = BluetoothError(
                "adapter_missing",
                "Adapter is not present",
                retryable=True,
                adapter_id=adapter_id,
            )
            return self._operation(operation_type, adapter_id=adapter_id, state="failed", error=error)
        command_lines = command if command and isinstance(command[0], list) else [command]
        result = self._run([["select", adapter.address], *command_lines])
        succeeded = _command_succeeded(result)
        return self._operation(
            operation_type,
            adapter_id=adapter_id,
            state="succeeded" if succeeded else "failed",
            result={"output": _bounded_output(result)},
            error=None if succeeded else _command_error(result, adapter_id),
        )

    def _device_command(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str,
    ) -> Operation:
        adapter = self._adapter_by_id(adapter_id)
        if adapter is None:
            error = BluetoothError(
                "adapter_missing",
                "Adapter is not present",
                retryable=True,
                adapter_id=adapter_id,
                device_key=device_key,
            )
            return self._operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=error,
            )
        mac = _address_from_key(device_key)
        if operation_type == "pair":
            result, succeeded = self._pair_with_agent(adapter, mac)
        else:
            result = self._run([["select", adapter.address], [operation_type, mac]])
            succeeded = _command_succeeded(result)
        return self._operation(
            operation_type,
            adapter_id=adapter_id,
            device_key=device_key,
            state="succeeded" if succeeded else "failed",
            result={"output": _bounded_output(result)},
            error=None if succeeded else _command_error(result, adapter_id, device_key),
        )

    def _device_profile_command(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
    ) -> Operation:
        adapter = self._adapter_by_id(adapter_id)
        if adapter is None:
            return self._operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=BluetoothError(
                    "adapter_missing",
                    "Adapter is not present",
                    retryable=True,
                    adapter_id=adapter_id,
                    device_key=device_key,
                ),
            )
        normalized = profile_uuid.strip().lower()
        device = None
        if self._last_state is not None:
            device = next(
                (
                    item
                    for item in self._last_state.devices
                    if item.adapter_id == adapter_id and item.key == device_key
                ),
                None,
            )
        if device is None or normalized not in {uuid.lower() for uuid in device.uuids}:
            return self._operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=BluetoothError(
                    "profile_unavailable",
                    "Profile is not advertised by this device",
                    adapter_id=adapter_id,
                    device_key=device_key,
                ),
            )
        command = "connect" if operation_type == "connect_profile" else "disconnect"
        result = self._run(
            [["select", adapter.address], [command, _address_from_key(device_key), normalized]]
        )
        succeeded = _command_succeeded(result)
        return self._operation(
            operation_type,
            adapter_id=adapter_id,
            device_key=device_key,
            state="succeeded" if succeeded else "failed",
            result={"profile_uuid": normalized, "output": _bounded_output(result)},
            error=None if succeeded else _command_error(result, adapter_id, device_key),
        )

    def _pair_with_agent(
        self,
        adapter: Adapter,
        mac: str,
    ) -> tuple[subprocess.CompletedProcess[str], bool]:
        """Keep a headless bluetoothctl agent alive until BlueZ settles."""
        process = subprocess.Popen(
            ["bluetoothctl", "--agent", "NoInputNoOutput"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if process.stdin is None:
            process.kill()
            return subprocess.CompletedProcess(
                ["bluetoothctl"],
                1,
                stdout="",
                stderr="bluetoothctl stdin unavailable",
            ), False
        succeeded = False
        try:
            time.sleep(1.0)
            for other in self._pairing_peers(adapter):
                process.stdin.write(f"select {other.address}\npairable off\n")
            process.stdin.write(
                f"select {adapter.address}\n"
                "pairable on\n"
                f"pair {mac}\n"
            )
            process.stdin.flush()
            succeeded = self._wait_for_device_property(adapter, mac, "bonded", "yes")
        except BrokenPipeError:
            succeeded = False
        finally:
            try:
                process.stdin.write("pairable off\nquit\n")
                process.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            output, _ = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
            succeeded = False
        result = subprocess.CompletedProcess(
            ["bluetoothctl", "--agent", "NoInputNoOutput"],
            process.returncode or 0,
            stdout=output,
            stderr="",
        )
        return result, succeeded

    def _pairing_peers(self, selected: Adapter) -> tuple[Adapter, ...]:
        """Return other present adapters that must remain non-pairable."""
        state = self._last_state
        if state is None:
            return ()
        return tuple(
            adapter
            for adapter in state.adapters
            if adapter.present and adapter.address != selected.address
        )

    def _wait_for_device_property(
        self,
        adapter: Adapter,
        mac: str,
        property_name: str,
        expected: str,
    ) -> bool:
        """Wait for BlueZ to settle after an asynchronous bluetoothctl action."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            info = self._run([["select", adapter.address], ["info", mac]]).stdout
            if _parse_show(info).get(property_name) == expected:
                return True
            time.sleep(0.25)
        return False

    def _adapter_by_id(self, adapter_id: str) -> Adapter | None:
        state = self._last_state or self._state_sync()
        return next((adapter for adapter in state.adapters if adapter.id == adapter_id), None)

    def _run(self, commands: list[list[str]]) -> subprocess.CompletedProcess[str]:
        script = "\n".join(" ".join(command) for command in commands) + "\nquit\n"
        return subprocess.run(
            ["bluetoothctl"],
            input=script,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

    def _operation(
        self,
        operation_type: str,
        *,
        adapter_id: str | None = None,
        device_key: str | None = None,
        state: str,
        result: dict[str, Any] | None = None,
        error: BluetoothError | None = None,
    ) -> Operation:
        self._counter += 1
        operation = Operation(
            id=f"bluetoothctl-op-{self._counter}",
            type=operation_type,
            adapter_id=adapter_id,
            device_key=device_key,
            state=state,
            started_at=_now(),
            updated_at=_now(),
            result=result or {},
            error=error,
        )
        self._operations.append(operation)
        self._events.append(
            Event(
                id=f"bluetoothctl-event-{self._counter}",
                type="operation_succeeded" if state == "succeeded" else "operation_failed",
                message=f"{operation_type} {state}",
                timestamp=operation.updated_at,
                adapter_id=adapter_id,
                device_key=device_key,
            )
        )
        return operation

    def _diagnostics(
        self,
        adapters: list[Adapter],
        devices: list[Device],
    ) -> dict[str, Any]:
        return {
            "bluez": {
                "available": True,
                "backend": "bluetoothctl",
                "degraded": True,
            },
            "soundbar": _soundbar_readiness(adapters, devices).to_dict(),
            "controllers": _controller_readiness(devices).to_dict(),
            "steamlink": {"available": None, "path": ""},
        }


def _parse_show(output: str) -> dict[str, str]:
    props = {}
    for line in output.splitlines():
        clean = line.strip()
        if clean.startswith("Controller "):
            continue
        if ":" not in clean:
            continue
        key, value = clean.split(":", 1)
        props[key.strip().lower().replace(" ", "_")] = value.strip()
    for line in output.splitlines():
        clean = line.strip()
        if clean.startswith("/org/bluez/hci"):
            props["bluez_path"] = clean.split()[0]
            break
    return props


def _adapter_index_by_address(address: str) -> int | None:
    """Resolve the current hci index from sysfs without guessing hci0."""
    normalized = normalize_address(address)
    for address_file in sorted(Path("/sys/class/bluetooth").glob("hci*/address")):
        try:
            candidate = normalize_address(address_file.read_text(encoding="utf-8").strip())
        except OSError:
            continue
        if candidate != normalized:
            continue
        name = address_file.parent.name
        if name.startswith("hci") and name[3:].isdigit():
            return int(name[3:])
    return None


def _command_succeeded(result: subprocess.CompletedProcess[str]) -> bool:
    output = f"{result.stdout}\n{result.stderr}".lower()
    failure_markers = ("failed", "not available", "invalid command", "error:")
    return result.returncode == 0 and not any(marker in output for marker in failure_markers)


def _parse_device_lines(output: str) -> list[dict[str, str]]:
    devices = []
    for line in output.splitlines():
        clean = line.strip()
        if not clean.startswith("Device "):
            continue
        parts = clean.split(maxsplit=2)
        if len(parts) >= 2:
            devices.append({
                "address": normalize_address(parts[1]),
                "name": parts[2] if len(parts) > 2 else parts[1],
            })
    return devices


def _device_from_info(adapter: Adapter, raw: dict[str, str], info: str) -> Device:
    props = _parse_show(info)
    address = normalize_address(props.get("device", raw["address"]))
    name = props.get("name", raw.get("name", address))
    icon = props.get("icon", "")
    uuids = tuple(_parse_uuids(info))
    kind, evidence, confidence = classify_device(name, icon, uuids)
    return Device(
        key=make_device_key(adapter.id, address),
        adapter_id=adapter.id,
        bluez_path=props.get("bluez_path", f"{adapter.bluez_path}/dev_{address.replace(':', '_')}"),
        address=address,
        address_type=props.get("address_type", "public"),
        name=name,
        alias=props.get("alias", name),
        icon=icon,
        uuids=uuids,
        paired=props.get("paired", "no") == "yes",
        bonded=_yes_no_unknown(props.get("bonded")),
        trusted=props.get("trusted", "no") == "yes",
        blocked=props.get("blocked", "no") == "yes",
        connected=props.get("connected", "no") == "yes",
        services_resolved=_yes_no_unknown(props.get("services_resolved")),
        rssi=_int_or_none(props.get("rssi")),
        tx_power=_int_or_none(props.get("txpower")),
        battery_percentage=_int_or_none(props.get("battery_percentage")),
        kind=kind,
        kind_evidence=evidence,
        confidence=confidence,
    )


def _parse_uuids(output: str) -> list[str]:
    uuids = []
    for line in output.splitlines():
        clean = line.strip()
        if "(0x" in clean and "-" in clean:
            uuids.append(clean.split()[0])
    return uuids


def _soundbar_readiness(
    adapters: list[Adapter],
    devices: list[Device],
) -> SoundbarReadiness:
    soundbar = next(
        (device for device in devices if normalize_address(device.address) == SAMSUNG_SOUNDBAR_MAC),
        None,
    )
    adapter = next(
        (candidate for candidate in adapters if soundbar and candidate.id == soundbar.adapter_id),
        None,
    )
    steps = (
        ReadinessStep("adapter", "Adapter present and powered", bool(adapter and adapter.powered), "Adapter usable" if adapter and adapter.powered else "Adapter missing or off"),
        ReadinessStep("known", "Soundbar known", bool(soundbar), "Soundbar known" if soundbar else "Soundbar not seen"),
        ReadinessStep("paired", "Paired", bool(soundbar and soundbar.paired), "Paired" if soundbar and soundbar.paired else "Not paired"),
        ReadinessStep("trusted", "Trusted", bool(soundbar and soundbar.trusted), "Trusted" if soundbar and soundbar.trusted else "Not trusted"),
        ReadinessStep("connected", "BlueZ connected", bool(soundbar and soundbar.connected), "Connected" if soundbar and soundbar.connected else "Not connected"),
        ReadinessStep("services", "Services resolved", soundbar.services_resolved if soundbar else False, "Services resolved" if soundbar and soundbar.services_resolved else "Services unresolved"),
        ReadinessStep("pipewire_sink", "PipeWire sink present", None, "Owned by Audio service"),
        ReadinessStep("route", "Audio route/loopback", None, "Owned by Audio service"),
    )
    return SoundbarReadiness(
        device_key=soundbar.key if soundbar else None,
        ready=all(step.state is True for step in steps[:6]),
        steps=steps,
    )


def _controller_readiness(devices: list[Device]) -> ControllerReadiness:
    controllers = tuple(
        device.key for device in devices
        if device.kind in {"gamepad", "xbox_controller"}
    )
    blockers = []
    if not any(device.connected for device in devices if device.key in controllers):
        blockers.append("No connected controller")
    blockers.append("Linux input evidence unavailable in bluetoothctl fallback")
    blockers.append("Steam Link availability unavailable in bluetoothctl fallback")
    return ControllerReadiness(
        ready=False,
        controllers=controllers,
        steamlink={"available": None, "path": ""},
        blockers=tuple(blockers),
    )


def _index_from_path(path: str) -> int | None:
    marker = "/hci"
    if marker not in path:
        return None
    suffix = path.rsplit(marker, 1)[-1].split("/", 1)[0]
    return _int_or_none(suffix)


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _yes_no_unknown(value: str | None) -> bool | None:
    if value == "yes":
        return True
    if value == "no":
        return False
    return None


def _address_from_key(device_key: str) -> str:
    return normalize_address(device_key.rsplit("/", 1)[-1])


def _bounded_output(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stdout + result.stderr).strip()[:500]


def _command_error(
    result: subprocess.CompletedProcess[str],
    adapter_id: str,
    device_key: str | None = None,
) -> BluetoothError:
    return BluetoothError(
        "connection_failed" if device_key else "unsupported",
        "bluetoothctl command failed",
        retryable=True,
        adapter_id=adapter_id,
        device_key=device_key,
        detail=_bounded_output(result),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
