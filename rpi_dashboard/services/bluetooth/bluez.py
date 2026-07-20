"""BlueZ D-Bus backend for the Bluetooth control center."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any

try:
    from dbus_fast import BusType
    from dbus_fast import Message
    from dbus_fast import MessageType
    from dbus_fast import Variant
    from dbus_fast.aio import MessageBus
except ModuleNotFoundError:
    BusType = None  # type: ignore[assignment,misc]
    Message = None  # type: ignore[assignment,misc]
    MessageBus = None  # type: ignore[assignment,misc]
    MessageType = None  # type: ignore[assignment,misc]
    Variant = Any  # type: ignore[assignment,misc]

from .models import Adapter
from .models import BackendHealth
from .models import BluetoothError
from .models import BluetoothState
from .models import ControllerReadiness
from .models import Device
from .models import Operation
from .models import ReadinessStep
from .models import SoundbarReadiness
from .models import adapter_id_from_address
from .models import classify_device
from .models import make_device_key
from .models import normalize_address
from .protocol import BluetoothBackend

BLUEZ = "org.bluez"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
PROPERTIES = "org.freedesktop.DBus.Properties"
ADAPTER1 = "org.bluez.Adapter1"
DEVICE1 = "org.bluez.Device1"
BATTERY1 = "org.bluez.Battery1"
SAMSUNG_SOUNDBAR_MAC = "24:4B:03:92:0B:8C"


class BlueZDbusBackend:
    """Async BlueZ backend using the system bus and standard interfaces."""

    def __init__(self, fallback: BluetoothBackend | None = None) -> None:
        self.fallback = fallback
        self._bus: MessageBus | None = None
        self._last_state: BluetoothState | None = None
        self._counter = 0

    async def state(self) -> BluetoothState:
        """Return current BlueZ state, or fallback state when unavailable."""
        try:
            return await self._state_from_bluez()
        except Exception as exc:
            if self.fallback is not None:
                return await self.fallback.state()
            return _unavailable_state(exc)

    async def events(self):
        """Signal streaming is reserved for the hotplug integration phase."""
        if False:
            yield None

    async def reconcile(self) -> BluetoothState:
        """Rebuild state from ObjectManager."""
        return await self.state()

    async def set_adapter_power(self, adapter_id: str, powered: bool) -> Operation:
        """Set Adapter1.Powered."""
        target = await self._adapter_target(adapter_id)
        if isinstance(target, BluetoothError):
            return self._operation("set_power", adapter_id=adapter_id, state="failed", error=target)
        if self._adapter_requires_fallback(target):
            return await self._fallback_backend().set_adapter_power(adapter_id, powered)
        path = target.bluez_path
        return await self._call_properties_set(
            "set_power",
            path,
            ADAPTER1,
            "Powered",
            Variant("b", powered),
            adapter_id=adapter_id,
        )

    async def start_discovery(self, adapter_id: str) -> Operation:
        """Start discovery on one adapter."""
        return await self._adapter_method("start_discovery", adapter_id, "StartDiscovery")

    async def stop_discovery(self, adapter_id: str) -> Operation:
        """Stop discovery on one adapter."""
        return await self._adapter_method("stop_discovery", adapter_id, "StopDiscovery")

    async def pair(self, adapter_id: str, device_key: str) -> Operation:
        """Pair a device."""
        return await self._device_method("pair", adapter_id, device_key, "Pair")

    async def trust(self, adapter_id: str, device_key: str) -> Operation:
        """Set Device1.Trusted true."""
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation("trust", adapter_id=adapter_id, device_key=device_key, state="failed", error=target)
        if target.use_fallback:
            return await self._fallback_backend().trust(adapter_id, device_key)
        return await self._call_properties_set(
            "trust",
            target.bluez_path,
            DEVICE1,
            "Trusted",
            Variant("b", True),
            adapter_id=adapter_id,
            device_key=device_key,
        )

    async def untrust(self, adapter_id: str, device_key: str) -> Operation:
        """Set Device1.Trusted false."""
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation("untrust", adapter_id=adapter_id, device_key=device_key, state="failed", error=target)
        if target.use_fallback:
            return await self._fallback_backend().untrust(adapter_id, device_key)
        return await self._call_properties_set(
            "untrust",
            target.bluez_path,
            DEVICE1,
            "Trusted",
            Variant("b", False),
            adapter_id=adapter_id,
            device_key=device_key,
        )

    async def connect(self, adapter_id: str, device_key: str) -> Operation:
        """Connect a device."""
        return await self._device_method("connect", adapter_id, device_key, "Connect")

    async def disconnect(self, adapter_id: str, device_key: str) -> Operation:
        """Disconnect a device."""
        return await self._device_method("disconnect", adapter_id, device_key, "Disconnect")

    async def remove(self, adapter_id: str, device_key: str) -> Operation:
        """Remove a device from its adapter."""
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation("remove", adapter_id=adapter_id, device_key=device_key, state="failed", error=target)
        if target.use_fallback:
            return await self._fallback_backend().remove(adapter_id, device_key)
        return await self._call_method(
            "remove",
            target.adapter_path,
            ADAPTER1,
            "RemoveDevice",
            signature="o",
            body=[target.bluez_path],
            adapter_id=adapter_id,
            device_key=device_key,
        )

    async def cancel(self, operation_id: str) -> Operation:
        """Cancel is only supported for selected BlueZ flows in later phases."""
        error = BluetoothError("unsupported", "D-Bus cancel is not implemented for this operation")
        return self._operation("cancel", state="failed", error=error)

    async def _state_from_bluez(self) -> BluetoothState:
        bus = await self._connect()
        reply = await bus.call(
            Message(
                destination=BLUEZ,
                path="/",
                interface=OBJECT_MANAGER,
                member="GetManagedObjects",
            )
        )
        if reply.message_type is MessageType.ERROR:
            raise RuntimeError(reply.body[0] if reply.body else reply.error_name)
        managed = reply.body[0]
        adapters = _adapters_from_managed(managed)
        devices = _devices_from_managed(managed, adapters)
        state = BluetoothState(
            backend=BackendHealth(name="bluez-dbus", degraded=False, available=True),
            adapters=tuple(adapters),
            devices=tuple(devices),
            diagnostics=_diagnostics(adapters, devices),
        )
        self._last_state = state
        return state

    async def _adapter_method(
        self,
        operation_type: str,
        adapter_id: str,
        member: str,
    ) -> Operation:
        target = await self._adapter_target(adapter_id)
        if isinstance(target, BluetoothError):
            return self._operation(operation_type, adapter_id=adapter_id, state="failed", error=target)
        if self._adapter_requires_fallback(target):
            return await getattr(self._fallback_backend(), operation_type)(adapter_id)
        return await self._call_method(
            operation_type,
            target.bluez_path,
            ADAPTER1,
            member,
            adapter_id=adapter_id,
        )

    async def _device_method(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str,
        member: str,
    ) -> Operation:
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=target,
            )
        if target.use_fallback:
            return await getattr(self._fallback_backend(), operation_type)(adapter_id, device_key)
        return await self._call_method(
            operation_type,
            target.bluez_path,
            DEVICE1,
            member,
            adapter_id=adapter_id,
            device_key=device_key,
        )

    async def _call_properties_set(
        self,
        operation_type: str,
        path: str,
        interface: str,
        prop: str,
        value: Any,
        *,
        adapter_id: str | None = None,
        device_key: str | None = None,
    ) -> Operation:
        return await self._call_method(
            operation_type,
            path,
            PROPERTIES,
            "Set",
            signature="ssv",
            body=[interface, prop, value],
            adapter_id=adapter_id,
            device_key=device_key,
        )

    async def _call_method(
        self,
        operation_type: str,
        path: str,
        interface: str,
        member: str,
        *,
        signature: str | None = None,
        body: list[Any] | None = None,
        adapter_id: str | None = None,
        device_key: str | None = None,
    ) -> Operation:
        try:
            bus = await self._connect()
            reply = await bus.call(
                Message(
                    destination=BLUEZ,
                    path=path,
                    interface=interface,
                    member=member,
                    signature=signature,
                    body=body or [],
                )
            )
            if reply.message_type is MessageType.ERROR:
                error = _dbus_error(reply, adapter_id, device_key)
                return self._operation(
                    operation_type,
                    adapter_id=adapter_id,
                    device_key=device_key,
                    state="failed",
                    error=error,
                )
            return self._operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="succeeded",
                result={"dbus_member": member},
            )
        except Exception as exc:
            error = BluetoothError(
                "backend_unavailable",
                "BlueZ D-Bus operation failed",
                retryable=True,
                adapter_id=adapter_id,
                device_key=device_key,
                detail=str(exc),
            )
            return self._operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=error,
            )

    async def _adapter_target(self, adapter_id: str) -> Adapter | BluetoothError:
        state = await self.state()
        adapter = next(
            (candidate for candidate in state.adapters if candidate.id == adapter_id and candidate.present),
            None,
        )
        if adapter is None:
            return BluetoothError(
                "adapter_missing",
                "Adapter is not present",
                retryable=True,
                adapter_id=adapter_id,
            )
        return adapter

    async def _device_target(
        self,
        adapter_id: str,
        device_key: str,
    ) -> "_DeviceTarget | BluetoothError":
        state = await self.state()
        device = next(
            (
                candidate for candidate in state.devices
                if candidate.key == device_key
                and candidate.adapter_id == adapter_id
                and candidate.present
            ),
            None,
        )
        if device is None:
            return BluetoothError(
                "device_missing",
                "Device is not present on selected adapter",
                retryable=True,
                adapter_id=adapter_id,
                device_key=device_key,
            )
        adapter = next(candidate for candidate in state.adapters if candidate.id == adapter_id)
        return _DeviceTarget(
            bluez_path=device.bluez_path,
            adapter_path=adapter.bluez_path,
            use_fallback=self._adapter_requires_fallback(adapter) or not device.bluez_path.startswith("/org/bluez/"),
        )

    def _adapter_requires_fallback(self, adapter: Adapter) -> bool:
        """Return true when state came from a non-D-Bus fallback adapter."""
        return bool(
            self.fallback is not None
            and (
                adapter.backend != "bluez-dbus"
                or not adapter.bluez_path.startswith("/org/bluez/")
            )
        )

    def _fallback_backend(self) -> BluetoothBackend:
        if self.fallback is None:
            raise RuntimeError("Fallback backend is not configured")
        return self.fallback

    async def _connect(self) -> MessageBus:
        if MessageBus is None or BusType is None:
            raise RuntimeError("dbus-fast is not installed")
        if self._bus is None or not self._bus.connected:
            self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        return self._bus

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
        return Operation(
            id=f"bluez-op-{self._counter}",
            type=operation_type,
            adapter_id=adapter_id,
            device_key=device_key,
            state=state,
            started_at=_now(),
            updated_at=_now(),
            result=result or {},
            error=error,
        )


class _DeviceTarget:
    def __init__(self, *, bluez_path: str, adapter_path: str, use_fallback: bool = False) -> None:
        self.bluez_path = bluez_path
        self.adapter_path = adapter_path
        self.use_fallback = use_fallback


def _adapters_from_managed(managed: dict[str, Any]) -> list[Adapter]:
    adapters = []
    for path, interfaces in managed.items():
        props = interfaces.get(ADAPTER1)
        if not props:
            continue
        address = normalize_address(_variant_value(props.get("Address"), ""))
        adapter_id = adapter_id_from_address(address) if address else f"adapter-{path.rsplit('/', 1)[-1]}"
        adapters.append(
            Adapter(
                id=adapter_id,
                bluez_path=path,
                index=_index_from_path(path),
                address=address,
                address_type=_variant_value(props.get("AddressType"), "public"),
                name=_variant_value(props.get("Name"), ""),
                alias=_variant_value(props.get("Alias"), ""),
                modalias=_variant_value(props.get("Modalias"), ""),
                powered=bool(_variant_value(props.get("Powered"), False)),
                discoverable=bool(_variant_value(props.get("Discoverable"), False)),
                pairable=bool(_variant_value(props.get("Pairable"), False)),
                discovering=bool(_variant_value(props.get("Discovering"), False)),
                present=True,
                backend="bluez-dbus",
            )
        )
    return adapters


def _devices_from_managed(
    managed: dict[str, Any],
    adapters: list[Adapter],
) -> list[Device]:
    by_path = {adapter.bluez_path: adapter for adapter in adapters}
    devices = []
    for path, interfaces in managed.items():
        props = interfaces.get(DEVICE1)
        if not props:
            continue
        adapter_path = _adapter_path_for_device(path)
        adapter = by_path.get(adapter_path)
        if adapter is None:
            continue
        address = normalize_address(_variant_value(props.get("Address"), ""))
        name = _variant_value(props.get("Name"), "") or _variant_value(props.get("Alias"), "")
        icon = _variant_value(props.get("Icon"), "")
        uuids = tuple(_variant_value(props.get("UUIDs"), []) or [])
        kind, evidence, confidence = classify_device(
            name,
            icon,
            uuids,
            _variant_value(props.get("Appearance"), None),
        )
        battery = interfaces.get(BATTERY1, {}).get("Percentage")
        devices.append(
            Device(
                key=make_device_key(adapter.id, address),
                adapter_id=adapter.id,
                bluez_path=path,
                address=address,
                address_type=_variant_value(props.get("AddressType"), "public"),
                name=name,
                alias=_variant_value(props.get("Alias"), name),
                icon=icon,
                appearance=_variant_value(props.get("Appearance"), None),
                uuids=uuids,
                paired=bool(_variant_value(props.get("Paired"), False)),
                trusted=bool(_variant_value(props.get("Trusted"), False)),
                blocked=bool(_variant_value(props.get("Blocked"), False)),
                connected=bool(_variant_value(props.get("Connected"), False)),
                services_resolved=_variant_value(props.get("ServicesResolved"), None),
                rssi=_variant_value(props.get("RSSI"), None),
                tx_power=_variant_value(props.get("TxPower"), None),
                battery_percentage=_variant_value(battery, None),
                kind=kind,
                kind_evidence=evidence,
                confidence=confidence,
            )
        )
    return devices


def _diagnostics(adapters: list[Adapter], devices: list[Device]) -> dict[str, Any]:
    return {
        "bluez": {
            "available": True,
            "backend": "bluez-dbus",
            "adapters": len(adapters),
        },
        "soundbar": _soundbar_readiness(adapters, devices).to_dict(),
        "controllers": _controller_readiness(devices).to_dict(),
        "steamlink": {"available": None, "path": ""},
    }


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
    blockers.append("Linux input evidence unavailable in BlueZ state")
    blockers.append("Steam Link availability unavailable in BlueZ state")
    return ControllerReadiness(
        ready=False,
        controllers=controllers,
        steamlink={"available": None, "path": ""},
        blockers=tuple(blockers),
    )


def _unavailable_state(exc: Exception) -> BluetoothState:
    error = BluetoothError(
        "backend_unavailable",
        "BlueZ D-Bus is unavailable",
        retryable=True,
        detail=str(exc),
    )
    return BluetoothState(
        backend=BackendHealth(name="bluez-dbus", degraded=False, available=False, message=str(exc)),
        diagnostics={
            "bluez": {"available": False, "error": error.to_dict()},
            "soundbar": SoundbarReadiness().to_dict(),
            "controllers": ControllerReadiness(blockers=("BlueZ D-Bus unavailable",)).to_dict(),
            "steamlink": {"available": None, "path": ""},
        },
        ok=False,
    )


def _dbus_error(
    reply: Message,
    adapter_id: str | None,
    device_key: str | None,
) -> BluetoothError:
    name = reply.error_name or ""
    detail = str(reply.body[0]) if reply.body else name
    code = "unsupported"
    if "NotReady" in name:
        code = "adapter_powered_off"
    elif "DoesNotExist" in name or "NotFound" in name:
        code = "device_missing" if device_key else "adapter_missing"
    elif "Authentication" in name:
        code = "authentication_failed"
    elif "Rejected" in name:
        code = "pairing_rejected"
    elif "Failed" in name:
        code = "connection_failed" if device_key else "backend_unavailable"
    return BluetoothError(
        code,
        "BlueZ D-Bus operation failed",
        retryable=code in {"adapter_powered_off", "connection_failed", "backend_unavailable"},
        adapter_id=adapter_id,
        device_key=device_key,
        detail=detail,
    )


def _adapter_path_for_device(path: str) -> str:
    parts = path.split("/dev_", 1)
    return parts[0]


def _index_from_path(path: str) -> int | None:
    suffix = path.rsplit("/hci", 1)[-1].split("/", 1)[0]
    try:
        return int(suffix)
    except ValueError:
        return None


def _variant_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if hasattr(value, "value"):
        return value.value
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
