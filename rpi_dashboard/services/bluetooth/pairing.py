"""Explicit BlueZ pairing agent with visible, bounded user challenges."""

import asyncio
from typing import Any

from dbus_fast.errors import DBusError
from dbus_fast.service import ServiceInterface, method


AGENT_INTERFACE = "org.bluez.Agent1"
_DBUS_OBJECT_PATH = "o"
_DBUS_STRING = "s"
_DBUS_UINT32 = "u"
_DBUS_UINT16 = "q"
_DBUS_NOTHING = ""


class PairingAgent(ServiceInterface):
    """Authorize only the device in one explicit dashboard pairing session."""

    def __init__(self, timeout: float = 60.0) -> None:
        super().__init__(AGENT_INTERFACE)
        self.timeout = timeout
        self.expected_path: str | None = None
        self.challenge: dict[str, Any] | None = None
        self._response: asyncio.Future[dict[str, Any]] | None = None

    def prepare(self, device_path: str) -> None:
        self.reject_pending("A new pairing request replaced the old request")
        self.expected_path = device_path
        self.challenge = None

    def clear(self) -> None:
        self.reject_pending("Pairing request ended")
        self.expected_path = None
        self.challenge = None

    def respond(self, accepted: bool, value: str | int | None = None) -> bool:
        waiter = self._response
        if waiter is None or waiter.done():
            return False
        waiter.set_result({"accepted": bool(accepted), "value": value})
        return True

    def reject_pending(self, message: str) -> None:
        waiter = self._response
        if waiter is not None and not waiter.done():
            waiter.set_result({"accepted": False, "message": message})

    async def _request(
        self,
        kind: str,
        device: str,
        *,
        passkey: int | None = None,
        service_uuid: str | None = None,
    ) -> dict[str, Any]:
        if not self.expected_path or device != self.expected_path:
            raise DBusError("org.bluez.Error.Rejected", "Device is not the active pairing target")
        loop = asyncio.get_running_loop()
        self._response = loop.create_future()
        self.challenge = {
            "type": kind,
            "device_path": device,
            "passkey": passkey,
            "service_uuid": service_uuid,
            "state": "waiting_for_user",
        }
        try:
            response = await asyncio.wait_for(self._response, timeout=self.timeout)
        except TimeoutError as exc:
            raise DBusError("org.bluez.Error.Rejected", "Pairing confirmation timed out") from exc
        finally:
            self._response = None
        if not response.get("accepted"):
            raise DBusError("org.bluez.Error.Rejected", "Pairing was rejected")
        self.challenge = {**self.challenge, "state": "accepted"}
        return response

    @method()
    def Release(self) -> _DBUS_NOTHING:  # type: ignore[valid-type,return]
        self.clear()

    @method()
    async def RequestPinCode(
        self,
        device: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
    ) -> _DBUS_STRING:  # type: ignore[valid-type]
        response = await self._request("pin_code", device)
        value = str(response.get("value") or "")
        if not value or len(value) > 16:
            raise DBusError("org.bluez.Error.Rejected", "A PIN code is required")
        return value

    @method()
    async def RequestPasskey(
        self,
        device: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
    ) -> _DBUS_UINT32:  # type: ignore[valid-type]
        response = await self._request("passkey", device)
        raw_value = response.get("value")
        try:
            value = int(raw_value) if isinstance(raw_value, str | int) else -1
        except (TypeError, ValueError) as exc:
            raise DBusError("org.bluez.Error.Rejected", "A numeric passkey is required") from exc
        if not 0 <= value <= 999999:
            raise DBusError("org.bluez.Error.Rejected", "Passkey must be between 000000 and 999999")
        return value

    @method()
    def DisplayPinCode(  # type: ignore[return]
        self,
        device: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
        pincode: _DBUS_STRING,  # type: ignore[valid-type]
    ) -> _DBUS_NOTHING:  # type: ignore[valid-type,return]
        self.challenge = {
            "type": "display_pin_code",
            "device_path": device,
            "pin_code": pincode,
            "state": "display",
        }

    @method()
    def DisplayPasskey(  # type: ignore[return]
        self,
        device: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
        passkey: _DBUS_UINT32,  # type: ignore[valid-type]
        entered: _DBUS_UINT16,  # type: ignore[valid-type]
    ) -> _DBUS_NOTHING:  # type: ignore[valid-type,return]
        self.challenge = {
            "type": "display_passkey",
            "device_path": device,
            "passkey": passkey,
            "entered": entered,
            "state": "display",
        }

    @method()
    async def RequestConfirmation(  # type: ignore[return]
        self,
        device: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
        passkey: _DBUS_UINT32,  # type: ignore[valid-type]
    ) -> _DBUS_NOTHING:  # type: ignore[valid-type,return]
        await self._request("confirmation", device, passkey=passkey)

    @method()
    async def RequestAuthorization(  # type: ignore[return]
        self,
        device: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
    ) -> _DBUS_NOTHING:  # type: ignore[valid-type,return]
        await self._request("authorization", device)

    @method()
    async def AuthorizeService(  # type: ignore[return]
        self,
        device: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
        uuid: _DBUS_STRING,  # type: ignore[valid-type]
    ) -> _DBUS_NOTHING:  # type: ignore[valid-type,return]
        await self._request("service", device, service_uuid=uuid)

    @method()
    def Cancel(self) -> _DBUS_NOTHING:  # type: ignore[valid-type,return]
        self.reject_pending("BlueZ cancelled pairing")
