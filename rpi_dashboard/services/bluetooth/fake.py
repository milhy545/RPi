"""In-memory Bluetooth backend for tests and UI development."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import datetime
from datetime import timezone
from typing import Any

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
from .models import normalize_address

SAMSUNG_SOUNDBAR_MAC = "24:4B:03:92:0B:8C"


class FakeBluetoothBackend:
    """Deterministic adapter-aware backend that never contacts BlueZ."""

    def __init__(
        self,
        *,
        adapters: list[Adapter] | None = None,
        devices: list[Device] | None = None,
        available: bool = True,
        event_limit: int = 50,
    ) -> None:
        self._backend = BackendHealth(
            name="fake",
            degraded=False,
            available=available,
            message="" if available else "BlueZ unavailable in fake scenario",
        )
        self._adapters = {adapter.id: adapter for adapter in adapters or []}
        self._devices = {device.key: device for device in devices or []}
        self._operations: dict[str, Operation] = {}
        self._events: deque[Event] = deque(maxlen=event_limit)
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._counter = 0
        self._scripted_errors: dict[str, BluetoothError] = {}
        self._scripted_delays: dict[str, float] = {}
        self._busy: set[tuple[str | None, str | None]] = set()

    @classmethod
    def empty(cls) -> "FakeBluetoothBackend":
        """Return a fake backend with no adapters."""
        return cls()

    @classmethod
    def one_adapter(cls) -> "FakeBluetoothBackend":
        """Return a fake backend with one powered adapter."""
        return cls(adapters=[fake_adapter(address="AA:BB:CC:00:00:01")])

    @classmethod
    def two_adapters(cls) -> "FakeBluetoothBackend":
        """Return a fake backend with audio and controller adapters."""
        audio = fake_adapter(
            address="AA:BB:CC:00:00:01",
            index=0,
            role="audio",
            alias="Onboard BT",
        )
        controllers = fake_adapter(
            address="AA:BB:CC:00:00:02",
            index=1,
            role="controllers",
            alias="USB BT Adapter",
        )
        return cls(adapters=[audio, controllers])

    @classmethod
    def with_overlapping_remote(cls) -> "FakeBluetoothBackend":
        """Return two adapter records seeing the same remote address."""
        backend = cls.two_adapters()
        adapter_ids = list(backend._adapters)
        backend.add_device(fake_device(adapter_ids[0], "DD:EE:FF:00:00:09"))
        backend.add_device(fake_device(adapter_ids[1], "DD:EE:FF:00:00:09"))
        return backend

    @classmethod
    def with_soundbar_and_controller(cls) -> "FakeBluetoothBackend":
        """Return a two-adapter backend with known soundbar and controller."""
        backend = cls.two_adapters()
        adapters = list(backend._adapters.values())
        backend.add_device(
            fake_device(
                adapters[0].id,
                SAMSUNG_SOUNDBAR_MAC,
                name="[Samsung] Soundbar J-Series",
                uuids=("0000110b-0000-1000-8000-00805f9b34fb",),
                paired=True,
                trusted=True,
                connected=True,
                services_resolved=True,
            )
        )
        backend.add_device(
            fake_device(
                adapters[1].id,
                "E4:17:D8:00:00:42",
                name="Xbox Wireless Controller",
                icon="input-gaming",
                uuids=("00001124-0000-1000-8000-00805f9b34fb",),
                paired=True,
                trusted=True,
                connected=True,
                services_resolved=True,
            )
        )
        return backend

    def script_error(self, operation_type: str, error: BluetoothError) -> None:
        """Force a future operation type to fail with a stable error."""
        self._scripted_errors[operation_type] = error

    def script_delay(self, operation_type: str, seconds: float) -> None:
        """Force a future operation type to wait before completing."""
        self._scripted_delays[operation_type] = seconds

    def add_adapter(self, adapter: Adapter) -> None:
        """Hotplug an adapter into the fake backend."""
        self._adapters[adapter.id] = adapter
        self._record_event("adapter_added", f"Adapter {adapter.id} appeared", adapter.id)

    def remove_adapter(self, adapter_id: str) -> None:
        """Mark an adapter and its devices absent without deleting history."""
        adapter = self._adapters.get(adapter_id)
        if adapter is None:
            return
        self._adapters[adapter_id] = replace(
            adapter,
            present=False,
            powered=False,
            discovering=False,
        )
        for key, device in list(self._devices.items()):
            if device.adapter_id == adapter_id:
                self._devices[key] = replace(device, present=False)
        self._record_event("adapter_removed", f"Adapter {adapter_id} disappeared", adapter_id)

    def add_device(self, device: Device) -> None:
        """Add or update a device relationship."""
        self._devices[device.key] = device
        self._record_event(
            "device_found",
            f"Device {device.address} found",
            device.adapter_id,
            device.key,
        )

    async def state(self) -> BluetoothState:
        """Return the current complete fake state."""
        diagnostics: dict[str, Any] = {
            "bluez": {"available": self._backend.available, "source": "fake"},
            "soundbar": self._soundbar_readiness().to_dict(),
            "controllers": self._controller_readiness().to_dict(),
            "steamlink": self._controller_readiness().steamlink,
        }
        return BluetoothState(
            backend=self._backend,
            adapters=tuple(sorted(self._adapters.values(), key=lambda item: item.id)),
            devices=tuple(sorted(self._devices.values(), key=lambda item: item.key)),
            operations=tuple(sorted(self._operations.values(), key=lambda item: item.id)),
            diagnostics=diagnostics,
            events=tuple(self._events),
            ok=self._backend.available,
        )

    async def events(self) -> AsyncIterator[Event]:
        """Yield events recorded after subscription begins."""
        while True:
            yield await self._queue.get()

    async def reconcile(self) -> BluetoothState:
        """Return current in-memory truth and record a reconciliation event."""
        self._record_event("reconciled", "Fake backend reconciled")
        return await self.state()

    async def set_adapter_power(self, adapter_id: str, powered: bool) -> Operation:
        """Set adapter power in memory."""
        return await self._adapter_operation("set_power", adapter_id, powered=powered)

    async def set_adapter_discoverable(
        self,
        adapter_id: str,
        discoverable: bool,
        timeout: int = 0,
    ) -> Operation:
        """Set adapter discoverability in memory."""
        return await self._adapter_operation(
            "set_discoverable",
            adapter_id,
            discoverable=discoverable,
            timeout=timeout,
        )

    async def start_discovery(self, adapter_id: str) -> Operation:
        """Start discovery on an adapter."""
        return await self._adapter_operation("start_discovery", adapter_id)

    async def stop_discovery(self, adapter_id: str) -> Operation:
        """Stop discovery on an adapter."""
        return await self._adapter_operation("stop_discovery", adapter_id)

    async def pair(self, adapter_id: str, device_key: str) -> Operation:
        """Pair a fake device."""
        return await self._device_operation("pair", adapter_id, device_key)

    async def trust(self, adapter_id: str, device_key: str) -> Operation:
        """Trust a fake device."""
        return await self._device_operation("trust", adapter_id, device_key)

    async def untrust(self, adapter_id: str, device_key: str) -> Operation:
        """Untrust a fake device."""
        return await self._device_operation("untrust", adapter_id, device_key)

    async def connect(self, adapter_id: str, device_key: str) -> Operation:
        """Connect a fake device."""
        return await self._device_operation("connect", adapter_id, device_key)

    async def disconnect(self, adapter_id: str, device_key: str) -> Operation:
        """Disconnect a fake device."""
        return await self._device_operation("disconnect", adapter_id, device_key)

    async def remove(self, adapter_id: str, device_key: str) -> Operation:
        """Mark a fake device absent."""
        return await self._device_operation("remove", adapter_id, device_key)

    async def cancel(self, operation_id: str) -> Operation:
        """Cancel a pending fake operation if it exists."""
        operation = self._operations.get(operation_id)
        if operation is None:
            error = BluetoothError("device_missing", "Operation does not exist")
            return self._record_operation("cancel", state="failed", error=error)
        cancelled = replace(
            operation,
            state="cancelled",
            updated_at=_now(),
            error=BluetoothError("cancelled", "Operation cancelled"),
        )
        self._operations[operation_id] = cancelled
        return cancelled

    async def _adapter_operation(
        self,
        operation_type: str,
        adapter_id: str,
        **kwargs: Any,
    ) -> Operation:
        adapter = self._adapters.get(adapter_id)
        if adapter is None or not adapter.present:
            error = BluetoothError(
                "adapter_missing",
                "Adapter is not present",
                retryable=True,
                adapter_id=adapter_id,
            )
            return self._record_operation(
                operation_type,
                adapter_id=adapter_id,
                state="failed",
                error=error,
            )
        conflict = self._conflict(operation_type, adapter_id, None)
        if conflict is not None:
            return conflict
        started = self._start_operation(operation_type, adapter_id, None)
        scripted = await self._scripted_result(started)
        if scripted is not None:
            return scripted
        if operation_type == "set_power":
            adapter = replace(adapter, powered=bool(kwargs["powered"]))
        elif operation_type == "set_discoverable":
            adapter = replace(adapter, discoverable=bool(kwargs["discoverable"]))
        elif operation_type == "start_discovery":
            adapter = replace(adapter, discovering=True)
        elif operation_type == "stop_discovery":
            adapter = replace(adapter, discovering=False)
        self._adapters[adapter_id] = adapter
        return self._finish_operation(started, {"adapter_id": adapter_id})

    async def _device_operation(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str,
    ) -> Operation:
        adapter = self._adapters.get(adapter_id)
        device = self._devices.get(device_key)
        if adapter is None or not adapter.present:
            error = BluetoothError(
                "adapter_missing",
                "Adapter is not present",
                retryable=True,
                adapter_id=adapter_id,
                device_key=device_key,
            )
            return self._record_operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=error,
            )
        if device is None or device.adapter_id != adapter_id:
            error = BluetoothError(
                "device_missing",
                "Device is not present on selected adapter",
                retryable=True,
                adapter_id=adapter_id,
                device_key=device_key,
            )
            return self._record_operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=error,
            )
        if not adapter.powered and operation_type in {"pair", "connect"}:
            error = BluetoothError(
                "adapter_powered_off",
                "Adapter is powered off",
                retryable=True,
                adapter_id=adapter_id,
                device_key=device_key,
            )
            return self._record_operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=error,
            )
        conflict = self._conflict(operation_type, adapter_id, device_key)
        if conflict is not None:
            return conflict
        started = self._start_operation(operation_type, adapter_id, device_key)
        scripted = await self._scripted_result(started)
        if scripted is not None:
            return scripted
        self._devices[device_key] = _apply_device_operation(device, operation_type)
        return self._finish_operation(started, {"device_key": device_key})

    def _conflict(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str | None,
    ) -> Operation | None:
        target = (adapter_id, device_key)
        if target not in self._busy:
            return None
        error = BluetoothError(
            "operation_busy",
            "Another operation is already active for this target",
            retryable=True,
            adapter_id=adapter_id,
            device_key=device_key,
        )
        return self._record_operation(
            operation_type,
            adapter_id=adapter_id,
            device_key=device_key,
            state="failed",
            error=error,
        )

    def _start_operation(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str | None,
    ) -> Operation:
        target = (adapter_id, device_key)
        self._busy.add(target)
        return self._record_operation(
            operation_type,
            adapter_id=adapter_id,
            device_key=device_key,
            state="pending",
            cancellable=operation_type in {"pair", "start_discovery"},
        )

    async def _scripted_result(self, operation: Operation) -> Operation | None:
        delay = self._scripted_delays.get(operation.type)
        if delay:
            await asyncio.sleep(delay)
        error = self._scripted_errors.pop(operation.type, None)
        if error is None:
            return None
        failed = replace(operation, state="failed", updated_at=_now(), error=error)
        self._operations[operation.id] = failed
        self._busy.discard((operation.adapter_id, operation.device_key))
        self._record_event(
            "operation_failed",
            f"{operation.type} failed: {error.code}",
            operation.adapter_id,
            operation.device_key,
        )
        return failed

    def _finish_operation(
        self,
        operation: Operation,
        result: dict[str, Any],
    ) -> Operation:
        finished = replace(
            operation,
            state="succeeded",
            updated_at=_now(),
            result=result,
        )
        self._operations[operation.id] = finished
        self._busy.discard((operation.adapter_id, operation.device_key))
        self._record_event(
            "operation_succeeded",
            f"{operation.type} succeeded",
            operation.adapter_id,
            operation.device_key,
        )
        return finished

    def _record_operation(
        self,
        operation_type: str,
        *,
        adapter_id: str | None = None,
        device_key: str | None = None,
        state: str,
        cancellable: bool = False,
        error: BluetoothError | None = None,
    ) -> Operation:
        self._counter += 1
        operation = Operation(
            id=f"fake-op-{self._counter}",
            type=operation_type,
            adapter_id=adapter_id,
            device_key=device_key,
            state=state,
            started_at=_now(),
            updated_at=_now(),
            cancellable=cancellable,
            error=error,
        )
        self._operations[operation.id] = operation
        if error is not None:
            self._record_event(
                "operation_failed",
                f"{operation_type} failed: {error.code}",
                adapter_id,
                device_key,
            )
        return operation

    def _record_event(
        self,
        event_type: str,
        message: str,
        adapter_id: str | None = None,
        device_key: str | None = None,
    ) -> None:
        self._counter += 1
        event = Event(
            id=f"fake-event-{self._counter}",
            type=event_type,
            message=message,
            timestamp=_now(),
            adapter_id=adapter_id,
            device_key=device_key,
        )
        self._events.append(event)
        self._queue.put_nowait(event)

    def _soundbar_readiness(self) -> SoundbarReadiness:
        soundbar = next(
            (
                device
                for device in self._devices.values()
                if normalize_address(device.address) == SAMSUNG_SOUNDBAR_MAC
            ),
            None,
        )
        adapter = self._adapters.get(soundbar.adapter_id) if soundbar else None
        steps = (
            ReadinessStep(
                "adapter",
                "Adapter present and powered",
                bool(adapter and adapter.present and adapter.powered),
                "Adapter is usable" if adapter and adapter.powered else "Adapter missing or off",
            ),
            ReadinessStep(
                "known",
                "Soundbar known",
                bool(soundbar and soundbar.present),
                "Soundbar is known" if soundbar else "Soundbar not seen",
            ),
            ReadinessStep(
                "paired",
                "Paired",
                bool(soundbar and soundbar.paired),
                "Paired in BlueZ" if soundbar and soundbar.paired else "Not paired",
            ),
            ReadinessStep(
                "trusted",
                "Trusted",
                bool(soundbar and soundbar.trusted),
                "Trusted in BlueZ" if soundbar and soundbar.trusted else "Not trusted",
            ),
            ReadinessStep(
                "connected",
                "BlueZ connected",
                bool(soundbar and soundbar.connected),
                "Transport connected" if soundbar and soundbar.connected else "Not connected",
            ),
            ReadinessStep(
                "services",
                "Services resolved",
                soundbar.services_resolved if soundbar else False,
                "Profile resolved" if soundbar and soundbar.services_resolved else "Profile unresolved",
            ),
            ReadinessStep(
                "pipewire_sink",
                "PipeWire sink present",
                None,
                "Owned by Audio service, unknown in Bluetooth fake backend",
            ),
            ReadinessStep(
                "route",
                "Audio route/loopback",
                None,
                "Owned by Audio service, unknown in Bluetooth fake backend",
            ),
        )
        ready = all(step.state is True for step in steps[:6])
        return SoundbarReadiness(
            device_key=soundbar.key if soundbar else None,
            ready=ready,
            steps=steps,
        )

    def _controller_readiness(self) -> ControllerReadiness:
        controllers = tuple(
            device.key
            for device in self._devices.values()
            if device.kind in {"gamepad", "xbox_controller"}
        )
        blockers: list[str] = []
        if not controllers:
            blockers.append("No controller devices known")
        blockers.append("Linux input evidence unavailable in fake backend")
        blockers.append("Steam Link availability unavailable in fake backend")
        return ControllerReadiness(
            ready=False,
            controllers=controllers,
            input_devices=(),
            modules={},
            steamlink={"available": None, "path": ""},
            blockers=tuple(blockers),
        )


def fake_adapter(
    *,
    address: str,
    index: int = 0,
    role: str | None = None,
    alias: str = "",
    powered: bool = True,
) -> Adapter:
    """Build a fake adapter with stable id from address."""
    adapter_id = adapter_id_from_address(address)
    return Adapter(
        id=adapter_id,
        bluez_path=f"/org/bluez/hci{index}",
        index=index,
        address=normalize_address(address),
        name=alias or f"hci{index}",
        alias=alias,
        powered=powered,
        discoverable=False,
        pairable=True,
        discovering=False,
        present=True,
        backend="fake",
        role=role,
    )


def fake_device(
    adapter_id: str,
    address: str,
    *,
    name: str = "Test Bluetooth Device",
    icon: str = "",
    uuids: tuple[str, ...] = (),
    paired: bool = False,
    trusted: bool = False,
    connected: bool = False,
    services_resolved: bool | None = None,
) -> Device:
    """Build a fake device scoped to one adapter."""
    key = make_device_key(adapter_id, address)
    kind, evidence, confidence = classify_device(name, icon, uuids)
    return Device(
        key=key,
        adapter_id=adapter_id,
        bluez_path=f"/org/bluez/hci0/dev_{normalize_address(address).replace(':', '_')}",
        address=normalize_address(address),
        name=name,
        alias=name,
        icon=icon,
        uuids=uuids,
        paired=paired,
        bonded=paired,
        trusted=trusted,
        connected=connected,
        services_resolved=services_resolved,
        kind=kind,
        kind_evidence=evidence,
        confidence=confidence,
    )


def _apply_device_operation(device: Device, operation_type: str) -> Device:
    if operation_type == "pair":
        return replace(device, paired=True, bonded=True, present=True, known=True)
    if operation_type == "trust":
        return replace(device, trusted=True)
    if operation_type == "untrust":
        return replace(device, trusted=False)
    if operation_type == "connect":
        return replace(device, connected=True)
    if operation_type == "disconnect":
        return replace(device, connected=False)
    if operation_type == "remove":
        return replace(
            device,
            paired=False,
            bonded=False,
            trusted=False,
            connected=False,
            present=False,
        )
    return device


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
