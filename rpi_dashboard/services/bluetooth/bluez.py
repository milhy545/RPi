"""BlueZ D-Bus backend for the Bluetooth control center."""

from __future__ import annotations

import asyncio
from collections import deque
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
from .models import Event
from .models import Operation
from .models import ReadinessStep
from .models import SoundbarReadiness
from .models import adapter_id_from_address
from .models import classify_device
from .models import hide_non_owner_duplicates
from .models import make_device_key
from .models import normalize_address
from .pairing import PairingAgent
from .protocol import BluetoothBackend

BLUEZ = "org.bluez"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
PROPERTIES = "org.freedesktop.DBus.Properties"
DBUS = "org.freedesktop.DBus"
DBUS_PATH = "/org/freedesktop/DBus"
ADAPTER1 = "org.bluez.Adapter1"
DEVICE1 = "org.bluez.Device1"
BATTERY1 = "org.bluez.Battery1"
MEDIA_PLAYER1 = "org.bluez.MediaPlayer1"
MEDIA_TRANSPORT1 = "org.bluez.MediaTransport1"
AGENT_MANAGER1 = "org.bluez.AgentManager1"
PAIRING_AGENT_PATH = "/org/rpidashboard/bluetooth_agent"
SAMSUNG_SOUNDBAR_MAC = "24:4B:03:92:0B:8C"
AUDIO_SOURCE_UUID = "0000110a-0000-1000-8000-00805f9b34fb"
AUDIO_SINK_UUID = "0000110b-0000-1000-8000-00805f9b34fb"


class BlueZDbusBackend:
    """Async BlueZ backend using the system bus and standard interfaces."""

    def __init__(
        self,
        fallback: BluetoothBackend | None = None,
        operation_timeout: float = 15.0,
        history_limit: int = 50,
    ) -> None:
        self.fallback = fallback
        self.operation_timeout = operation_timeout
        self._bus: MessageBus | None = None
        self._bus_loop: asyncio.AbstractEventLoop | None = None
        self._last_state: BluetoothState | None = None
        self._counter = 0
        self._operations: deque[Operation] = deque(maxlen=history_limit)
        self._events: deque[Event] = deque(maxlen=history_limit)
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=history_limit)
        self._subscriptions_bus: MessageBus | None = None
        self._busy_targets: set[tuple[str, str | None]] = set()
        self._pairing_agent = PairingAgent(timeout=60.0)
        self._pairing_agent_bus: MessageBus | None = None

    async def state(self) -> BluetoothState:
        """Return current BlueZ state, or fallback state when unavailable."""
        try:
            return await self._state_from_bluez()
        except Exception as exc:
            if self.fallback is not None:
                return await self.fallback.state()
            return _unavailable_state(exc)

    async def events(self):
        """Yield bounded BlueZ object/property events as they arrive."""
        await self._connect()
        while True:
            yield await self._event_queue.get()

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

    async def set_adapter_discoverable(
        self,
        adapter_id: str,
        discoverable: bool,
        timeout: int = 0,
    ) -> Operation:
        """Set Adapter1 discoverability and timeout."""
        target = await self._adapter_target(adapter_id)
        if isinstance(target, BluetoothError):
            return self._operation(
                "set_discoverable",
                adapter_id=adapter_id,
                state="failed",
                error=target,
            )
        if self._adapter_requires_fallback(target):
            return await self._fallback_backend().set_adapter_discoverable(
                adapter_id,
                discoverable,
                timeout,
            )
        timeout_result = await self._call_properties_set(
            "set_discoverable_timeout",
            target.bluez_path,
            ADAPTER1,
            "DiscoverableTimeout",
            Variant("u", max(0, timeout)),
            adapter_id=adapter_id,
        )
        if timeout_result.state != "succeeded":
            return timeout_result
        return await self._call_properties_set(
            "set_discoverable",
            target.bluez_path,
            ADAPTER1,
            "Discoverable",
            Variant("b", discoverable),
            adapter_id=adapter_id,
        )

    async def start_discovery(self, adapter_id: str) -> Operation:
        """Start discovery on one adapter."""
        return await self._adapter_method("start_discovery", adapter_id, "StartDiscovery")

    async def stop_discovery(self, adapter_id: str) -> Operation:
        """Stop discovery on one adapter."""
        return await self._adapter_method("stop_discovery", adapter_id, "StopDiscovery")

    async def pair(self, adapter_id: str, device_key: str) -> Operation:
        """Pair through a bounded agent that accepts only the explicit target."""
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation(
                "pair",
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=target,
            )
        if target.use_fallback:
            operation = await self._fallback_backend().pair(adapter_id, device_key)
            self._remember_external_operation(operation)
            return operation
        try:
            await self._ensure_pairing_agent()
        except Exception as exc:
            return self._operation(
                "pair",
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=BluetoothError(
                    "backend_unavailable",
                    "BlueZ pairing agent registration failed",
                    retryable=True,
                    adapter_id=adapter_id,
                    device_key=device_key,
                    detail=str(exc),
                ),
            )
        self._pairing_agent.prepare(target.bluez_path)
        try:
            return await self._call_method(
                "pair",
                target.bluez_path,
                DEVICE1,
                "Pair",
                adapter_id=adapter_id,
                device_key=device_key,
            )
        finally:
            self._pairing_agent.clear()

    def pairing_challenge(self) -> dict[str, Any] | None:
        """Return the current visible agent challenge without changing it."""
        challenge = self._pairing_agent.challenge
        if challenge is None:
            return None
        adapter_id, device_key = self._identity_for_path(str(challenge.get("device_path", "")))
        return {**challenge, "adapter_id": adapter_id, "device_key": device_key}

    def respond_pairing(self, accepted: bool, value: str | int | None = None) -> bool:
        """Resolve the current pairing challenge from a deliberate UI action."""
        return self._pairing_agent.respond(accepted, value)

    async def cancel_pairing(self, adapter_id: str, device_key: str) -> Operation:
        """Reject the agent challenge and ask Device1 to cancel pairing."""
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation(
                "cancel_pairing",
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=target,
            )
        self._pairing_agent.reject_pending("Pairing cancelled by user")
        if target.use_fallback:
            return self._operation(
                "cancel_pairing",
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=BluetoothError(
                    "unsupported",
                    "Fallback pairing cancellation is unavailable",
                    adapter_id=adapter_id,
                    device_key=device_key,
                ),
            )
        return await self._call_method(
            "cancel_pairing",
            target.bluez_path,
            DEVICE1,
            "CancelPairing",
            adapter_id=adapter_id,
            device_key=device_key,
        )

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

    async def block(self, adapter_id: str, device_key: str) -> Operation:
        """Set Device1.Blocked true on the selected adapter relationship."""
        return await self._set_device_boolean(
            "block", adapter_id, device_key, "Blocked", True
        )

    async def unblock(self, adapter_id: str, device_key: str) -> Operation:
        """Set Device1.Blocked false on the selected adapter relationship."""
        return await self._set_device_boolean(
            "unblock", adapter_id, device_key, "Blocked", False
        )

    async def connect(self, adapter_id: str, device_key: str) -> Operation:
        """Connect a device, selecting A2DP explicitly for audio endpoints."""
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation(
                "connect",
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=target,
            )
        if target.use_fallback:
            return await self._fallback_backend().connect(adapter_id, device_key)

        profile = _preferred_connect_profile(target.device)
        if profile is not None:
            return await self._call_method(
                "connect",
                target.bluez_path,
                DEVICE1,
                "ConnectProfile",
                signature="s",
                body=[profile],
                adapter_id=adapter_id,
                device_key=device_key,
            )
        return await self._call_method(
            "connect",
            target.bluez_path,
            DEVICE1,
            "Connect",
            adapter_id=adapter_id,
            device_key=device_key,
        )

    async def disconnect(self, adapter_id: str, device_key: str) -> Operation:
        """Disconnect a device."""
        return await self._device_method("disconnect", adapter_id, device_key, "Disconnect")

    async def connect_profile(
        self,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
    ) -> Operation:
        """Connect one profile advertised by the selected device."""
        return await self._device_profile_method(
            "connect_profile",
            adapter_id,
            device_key,
            profile_uuid,
            "ConnectProfile",
        )

    async def disconnect_profile(
        self,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
    ) -> Operation:
        """Disconnect one profile advertised by the selected device."""
        return await self._device_profile_method(
            "disconnect_profile",
            adapter_id,
            device_key,
            profile_uuid,
            "DisconnectProfile",
        )

    async def media_control(
        self,
        adapter_id: str,
        device_key: str,
        action: str,
        value: int | None = None,
    ) -> Operation:
        """Control one BlueZ MediaPlayer1 or its MediaTransport1 volume."""
        target = await self._device_target(adapter_id, device_key)
        if isinstance(target, BluetoothError):
            return self._operation(
                "media_control",
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=target,
            )
        if target.use_fallback:
            return await self._fallback_backend().media_control(
                adapter_id, device_key, action, value
            )
        state = await self.state()
        media = state.diagnostics.get("media") or {}
        if action == "volume":
            transport = next(
                (
                    item
                    for item in media.get("transports", [])
                    if item.get("device_key") == device_key
                ),
                None,
            )
            if transport is None or value is None or not 0 <= value <= 127:
                return self._profile_failure(adapter_id, device_key, "AVRCP transport volume is unavailable")
            return await self._call_properties_set(
                "media_volume",
                transport["path"],
                MEDIA_TRANSPORT1,
                "Volume",
                Variant("q", value),
                adapter_id=adapter_id,
                device_key=device_key,
            )
        members = {
            "play": "Play",
            "pause": "Pause",
            "stop": "Stop",
            "next": "Next",
            "previous": "Previous",
        }
        member = members.get(action)
        player = next(
            (
                item
                for item in media.get("players", [])
                if item.get("device_key") == device_key
            ),
            None,
        )
        if member is None or player is None:
            return self._profile_failure(adapter_id, device_key, "AVRCP media player action is unavailable")
        return await self._call_method(
            f"media_{action}",
            player["path"],
            MEDIA_PLAYER1,
            member,
            adapter_id=adapter_id,
            device_key=device_key,
        )

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
        """Return an explicit result for a known BlueZ operation lifecycle."""
        operation = next((item for item in self._operations if item.id == operation_id), None)
        if operation is None:
            error = BluetoothError("operation_missing", "Bluetooth operation does not exist")
        elif operation.state != "pending" or not operation.cancellable:
            error = BluetoothError(
                "operation_not_cancellable",
                "Bluetooth operation is already complete or is not cancellable",
                adapter_id=operation.adapter_id,
                device_key=operation.device_key,
            )
        else:
            error = BluetoothError(
                "unsupported",
                "This BlueZ operation has no safe cancellation method",
                adapter_id=operation.adapter_id,
                device_key=operation.device_key,
            )
        return self._operation("cancel", state="failed", error=error)

    async def _state_from_bluez(self) -> BluetoothState:
        bus = await self._connect()
        reply = await asyncio.wait_for(
            bus.call(
                Message(
                    destination=BLUEZ,
                    path="/",
                    interface=OBJECT_MANAGER,
                    member="GetManagedObjects",
                )
            ),
            timeout=self.operation_timeout,
        )
        if reply.message_type is MessageType.ERROR:
            raise RuntimeError(reply.body[0] if reply.body else reply.error_name)
        managed = reply.body[0]
        adapters = _adapters_from_managed(managed)
        devices = hide_non_owner_duplicates(_devices_from_managed(managed, adapters))
        diagnostics = _diagnostics(adapters, devices)
        diagnostics["media"] = _media_from_managed(managed, devices)
        state = BluetoothState(
            backend=BackendHealth(name="bluez-dbus", degraded=False, available=True),
            adapters=tuple(adapters),
            devices=tuple(devices),
            operations=tuple(self._operations),
            diagnostics=diagnostics,
            events=tuple(self._events),
        )
        self._last_state = state
        return state

    def _profile_failure(
        self,
        adapter_id: str,
        device_key: str,
        message: str,
    ) -> Operation:
        return self._operation(
            "media_control",
            adapter_id=adapter_id,
            device_key=device_key,
            state="failed",
            error=BluetoothError(
                "profile_unavailable",
                message,
                adapter_id=adapter_id,
                device_key=device_key,
            ),
        )

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

    async def _set_device_boolean(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str,
        prop: str,
        value: bool,
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
            return await getattr(self._fallback_backend(), operation_type)(
                adapter_id, device_key
            )
        return await self._call_properties_set(
            operation_type,
            target.bluez_path,
            DEVICE1,
            prop,
            Variant("b", value),
            adapter_id=adapter_id,
            device_key=device_key,
        )

    async def _device_profile_method(
        self,
        operation_type: str,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
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
        normalized = profile_uuid.strip().lower()
        advertised = {uuid.lower() for uuid in target.device.uuids}
        if not normalized or normalized not in advertised:
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
        if target.use_fallback:
            return await getattr(self._fallback_backend(), operation_type)(
                adapter_id, device_key, normalized
            )
        return await self._call_method(
            operation_type,
            target.bluez_path,
            DEVICE1,
            member,
            signature="s",
            body=[normalized],
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
        target = (
            (adapter_id, device_key)
            if adapter_id is not None and operation_type != "cancel_pairing"
            else None
        )
        if target is not None and target in self._busy_targets:
            return self._operation(
                operation_type,
                adapter_id=adapter_id,
                device_key=device_key,
                state="failed",
                error=BluetoothError(
                    "operation_busy",
                    "Another operation is already active for this target",
                    retryable=True,
                    adapter_id=adapter_id,
                    device_key=device_key,
                ),
            )
        if target is not None:
            self._busy_targets.add(target)
        try:
            bus = await self._connect()
            reply = await asyncio.wait_for(
                bus.call(
                    Message(
                        destination=BLUEZ,
                        path=path,
                        interface=interface,
                        member=member,
                        signature=signature or "",
                        body=body or [],
                    )
                ),
                timeout=self.operation_timeout,
            )
            if reply.message_type is MessageType.ERROR:
                if _idempotent_method_success(operation_type, reply):
                    return self._operation(
                        operation_type,
                        adapter_id=adapter_id,
                        device_key=device_key,
                        state="succeeded",
                        result={"dbus_member": member, "already_in_state": True},
                    )
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
        finally:
            if target is not None:
                self._busy_targets.discard(target)

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
            device=device,
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

    async def _ensure_pairing_agent(self) -> None:
        bus = await self._connect()
        if self._pairing_agent_bus is bus:
            return
        bus.export(PAIRING_AGENT_PATH, self._pairing_agent)
        reply = await asyncio.wait_for(
            bus.call(
                Message(
                    destination=BLUEZ,
                    path="/org/bluez",
                    interface=AGENT_MANAGER1,
                    member="RegisterAgent",
                    signature="os",
                    body=[PAIRING_AGENT_PATH, "KeyboardDisplay"],
                )
            ),
            timeout=self.operation_timeout,
        )
        if reply.message_type is MessageType.ERROR and reply.error_name != "org.bluez.Error.AlreadyExists":
            raise RuntimeError(
                str(reply.body[0]) if reply.body else reply.error_name or "RegisterAgent failed"
            )
        self._pairing_agent_bus = bus

    async def _connect(self) -> MessageBus:
        if MessageBus is None or BusType is None:
            raise RuntimeError("dbus-fast is not installed")
        loop = asyncio.get_running_loop()
        if self._bus is not None and self._bus_loop is not loop:
            self._bus.disconnect()
            self._bus = None
            self._subscriptions_bus = None
            self._pairing_agent_bus = None
        if self._bus is None or not self._bus.connected:
            self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            self._bus_loop = loop
            self._subscriptions_bus = None
            self._pairing_agent_bus = None
        await self._ensure_signal_subscriptions(self._bus)
        return self._bus

    async def _ensure_signal_subscriptions(self, bus: MessageBus) -> None:
        if self._subscriptions_bus is bus:
            return
        bus.add_message_handler(self._handle_bluez_signal)
        rules = (
            "type='signal',sender='org.bluez',interface='org.freedesktop.DBus.ObjectManager'",
            "type='signal',sender='org.bluez',interface='org.freedesktop.DBus.Properties'",
        )
        for rule in rules:
            reply = await bus.call(
                Message(
                    destination=DBUS,
                    path=DBUS_PATH,
                    interface=DBUS,
                    member="AddMatch",
                    signature="s",
                    body=[rule],
                )
            )
            if reply.message_type is MessageType.ERROR:
                raise RuntimeError(
                    str(reply.body[0]) if reply.body else reply.error_name or "AddMatch failed"
                )
        self._subscriptions_bus = bus

    def _handle_bluez_signal(self, message: Message) -> None:
        if message.message_type is not MessageType.SIGNAL:
            return
        event_type = ""
        path = message.path or ""
        changed_interface = ""
        if message.interface == OBJECT_MANAGER and message.member == "InterfacesAdded":
            path = str(message.body[0])
            interfaces = message.body[1]
            if ADAPTER1 in interfaces:
                event_type = "adapter_added"
            elif DEVICE1 in interfaces:
                event_type = "device_added"
        elif message.interface == OBJECT_MANAGER and message.member == "InterfacesRemoved":
            path = str(message.body[0])
            interfaces = message.body[1]
            if ADAPTER1 in interfaces:
                event_type = "adapter_removed"
            elif DEVICE1 in interfaces:
                event_type = "device_removed"
        elif message.interface == PROPERTIES and message.member == "PropertiesChanged":
            changed_interface = str(message.body[0])
            if changed_interface == ADAPTER1:
                event_type = "adapter_changed"
            elif changed_interface in {DEVICE1, BATTERY1}:
                event_type = "device_changed"
        if not event_type:
            return

        adapter_id, device_key = self._identity_for_path(path)
        self._counter += 1
        event = Event(
            id=f"bluez-signal-{self._counter}",
            type=event_type,
            message=f"{event_type}: {path}",
            timestamp=_now(),
            adapter_id=adapter_id,
            device_key=device_key,
            detail={"path": path, "interface": changed_interface} if changed_interface else {"path": path},
        )
        self._events.append(event)
        if self._event_queue.full():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._event_queue.put_nowait(event)

    def _identity_for_path(self, path: str) -> tuple[str | None, str | None]:
        state = self._last_state
        if state is not None:
            device = next((item for item in state.devices if item.bluez_path == path), None)
            if device is not None:
                return device.adapter_id, device.key
            adapter = next((item for item in state.adapters if item.bluez_path == path), None)
            if adapter is not None:
                return adapter.id, None
        adapter_path = _adapter_path_for_device(path)
        if state is not None:
            adapter = next(
                (item for item in state.adapters if item.bluez_path == adapter_path),
                None,
            )
            if adapter is not None:
                return adapter.id, None
        return None, None

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
        self._operations.append(operation)
        self._events.append(
            Event(
                id=f"bluez-event-{self._counter}",
                type="operation_succeeded" if state == "succeeded" else "operation_failed",
                message=f"{operation_type} {state}",
                timestamp=operation.updated_at,
                adapter_id=adapter_id,
                device_key=device_key,
            )
        )
        return operation

    def _remember_external_operation(self, operation: Operation) -> None:
        self._operations.append(operation)
        self._events.append(
            Event(
                id=f"bluez-external-{operation.id}",
                type="operation_succeeded" if operation.state == "succeeded" else "operation_failed",
                message=f"{operation.type} {operation.state}",
                timestamp=operation.updated_at,
                adapter_id=operation.adapter_id,
                device_key=operation.device_key,
            )
        )


class _DeviceTarget:
    def __init__(
        self,
        *,
        bluez_path: str,
        adapter_path: str,
        device: Device,
        use_fallback: bool = False,
    ) -> None:
        self.bluez_path = bluez_path
        self.adapter_path = adapter_path
        self.device = device
        self.use_fallback = use_fallback


def _preferred_connect_profile(device: Device) -> str | None:
    """Select the remote A2DP role for unambiguous audio endpoints."""
    uuids = {uuid.lower() for uuid in device.uuids}
    if device.kind in {"speaker", "headset"} and AUDIO_SINK_UUID in uuids:
        return AUDIO_SINK_UUID
    if device.icon == "phone" and AUDIO_SOURCE_UUID in uuids:
        return AUDIO_SOURCE_UUID
    return None


def _media_from_managed(
    managed: dict[str, Any],
    devices: list[Device],
) -> dict[str, list[dict[str, Any]]]:
    """Map BlueZ AVRCP players/transports to adapter-scoped device identities."""
    players: list[dict[str, Any]] = []
    transports: list[dict[str, Any]] = []
    for path, interfaces in managed.items():
        owner = max(
            (device for device in devices if path.startswith(f"{device.bluez_path}/")),
            key=lambda device: len(device.bluez_path),
            default=None,
        )
        if owner is None:
            continue
        player = interfaces.get(MEDIA_PLAYER1)
        if player:
            track = _variant_value(player.get("Track"), {})
            players.append(
                {
                    "path": path,
                    "adapter_id": owner.adapter_id,
                    "device_key": owner.key,
                    "name": _variant_value(player.get("Name"), ""),
                    "status": _variant_value(player.get("Status"), "unknown"),
                    "position": _variant_value(player.get("Position"), None),
                    "track": {
                        str(key): _variant_value(value, value)
                        for key, value in (track.items() if isinstance(track, dict) else [])
                    },
                }
            )
        transport = interfaces.get(MEDIA_TRANSPORT1)
        if transport:
            transports.append(
                {
                    "path": path,
                    "adapter_id": owner.adapter_id,
                    "device_key": owner.key,
                    "uuid": _variant_value(transport.get("UUID"), ""),
                    "state": _variant_value(transport.get("State"), "unknown"),
                    "codec": _variant_value(transport.get("Codec"), None),
                    "volume": _variant_value(transport.get("Volume"), None),
                    "delay": _variant_value(transport.get("Delay"), None),
                }
            )
    return {"players": players, "transports": transports}


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
                bonded=_variant_value(props.get("Bonded"), None),
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


def _idempotent_method_success(operation_type: str, reply: Message) -> bool:
    name = reply.error_name or ""
    detail = str(reply.body[0]) if reply.body else ""
    if operation_type == "start_discovery":
        return "InProgress" in name or "already in progress" in detail.lower()
    if operation_type == "stop_discovery":
        return (
            "NotReady" in name
            or "not ready" in detail.lower()
            or "no discovery started" in detail.lower()
        )
    if operation_type == "connect":
        return "AlreadyConnected" in name or "already connected" in detail.lower()
    return False


def _adapter_path_for_device(path: str) -> str:
    parts = path.split("/dev_", 1)
    return parts[0]


def _index_from_path(path: str) -> int | None:
    if "/hci" not in path:
        return None
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
