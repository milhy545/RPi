"""Backend protocol for Bluetooth control center implementations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from .models import BluetoothState
from .models import Event
from .models import Operation


class BluetoothBackend(Protocol):
    """Adapter-aware Bluetooth backend contract."""

    async def state(self) -> BluetoothState:
        """Return the latest complete Bluetooth state."""

    async def events(self) -> AsyncIterator[Event]:
        """Yield backend events for API/UI subscribers."""

    async def reconcile(self) -> BluetoothState:
        """Refresh state from backend truth after signal loss or hotplug."""

    async def set_adapter_power(self, adapter_id: str, powered: bool) -> Operation:
        """Set adapter power."""

    async def set_adapter_discoverable(
        self,
        adapter_id: str,
        discoverable: bool,
        timeout: int = 0,
    ) -> Operation:
        """Set adapter discoverability and its timeout in seconds."""

    async def start_discovery(self, adapter_id: str) -> Operation:
        """Start discovery on a selected adapter."""

    async def stop_discovery(self, adapter_id: str) -> Operation:
        """Stop discovery on a selected adapter."""

    async def pair(self, adapter_id: str, device_key: str) -> Operation:
        """Pair a device on the selected adapter."""

    async def trust(self, adapter_id: str, device_key: str) -> Operation:
        """Trust a device on the selected adapter."""

    async def untrust(self, adapter_id: str, device_key: str) -> Operation:
        """Remove trust from a device on the selected adapter."""

    async def block(self, adapter_id: str, device_key: str) -> Operation:
        """Block connections from a device."""

    async def unblock(self, adapter_id: str, device_key: str) -> Operation:
        """Allow connections from a previously blocked device."""

    async def connect(self, adapter_id: str, device_key: str) -> Operation:
        """Connect a device on the selected adapter."""

    async def disconnect(self, adapter_id: str, device_key: str) -> Operation:
        """Disconnect a device on the selected adapter."""

    async def connect_profile(
        self,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
    ) -> Operation:
        """Connect one remote-advertised profile."""

    async def disconnect_profile(
        self,
        adapter_id: str,
        device_key: str,
        profile_uuid: str,
    ) -> Operation:
        """Disconnect one remote-advertised profile."""

    async def media_control(
        self,
        adapter_id: str,
        device_key: str,
        action: str,
        value: int | None = None,
    ) -> Operation:
        """Run an advertised AVRCP action or set transport volume."""

    async def remove(self, adapter_id: str, device_key: str) -> Operation:
        """Remove a device from the selected adapter."""

    async def cancel(self, operation_id: str) -> Operation:
        """Cancel an operation where supported."""
