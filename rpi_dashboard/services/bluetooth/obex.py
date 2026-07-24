"""Bounded BlueZ OBEX Object Push client and receive authorization agent."""

import asyncio
import os
import re
import shutil
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from dbus_fast import BusType, Message, MessageType, Variant
    from dbus_fast.aio import MessageBus
    from dbus_fast.service import ServiceInterface, method
except ImportError:  # pragma: no cover - production dependency is locked
    BusType = None  # type: ignore[assignment,misc]
    Message = None  # type: ignore[assignment,misc]
    MessageType = None  # type: ignore[assignment,misc]
    Variant = Any  # type: ignore[assignment,misc]
    MessageBus = None  # type: ignore[assignment,misc]
    ServiceInterface = object  # type: ignore[assignment,misc]
    method = None  # type: ignore[assignment]


OBEX = "org.bluez.obex"
OBEX_ROOT = "/org/bluez/obex"
OBEX_CLIENT = "org.bluez.obex.Client1"
OBEX_AGENT_MANAGER = "org.bluez.obex.AgentManager1"
OBEX_AGENT = "org.bluez.obex.Agent1"
OBEX_OBJECT_PUSH = "org.bluez.obex.ObjectPush1"
OBEX_TRANSFER = "org.bluez.obex.Transfer1"
OBEX_SESSION = "org.bluez.obex.Session1"
PROPERTIES = "org.freedesktop.DBus.Properties"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
BLUEZ = "org.bluez"
DEFAULT_MAX_BYTES = 512 * 1024 * 1024
MIN_FREE_RESERVE = 16 * 1024 * 1024
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._()\- ]+")
_DBUS_OBJECT_PATH = "o"
_DBUS_STRING = "s"
_DBUS_NOTHING = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def downloads_directory() -> Path:
    """Return the only permitted inbound completion directory."""
    configured = os.environ.get("RPI_BLUETOOTH_DOWNLOAD_DIR")
    return Path(configured).expanduser() if configured else Path.home() / "Downloads"


def max_transfer_bytes() -> int:
    """Return the bounded inbound/outbound transfer size limit."""
    raw = os.environ.get("RPI_BLUETOOTH_MAX_TRANSFER_BYTES", str(DEFAULT_MAX_BYTES))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_BYTES


def sanitize_filename(value: str) -> str:
    """Reduce an untrusted remote filename to one safe local basename."""
    raw = str(value or "").replace("\\", "/")
    name = raw.rsplit("/", 1)[-1].replace("\x00", "").strip()
    name = "".join(character for character in name if ord(character) >= 32)
    name = _SAFE_NAME.sub("_", name).strip(" .")
    if not name or name in {".", ".."}:
        name = "bluetooth-file"
    stem, suffix = os.path.splitext(name)
    suffix = suffix[:24]
    return f"{stem[: max(1, 180 - len(suffix))]}{suffix}"


def collision_safe_path(directory: Path, filename: str) -> Path:
    """Choose a non-existing path under directory without following input paths."""
    directory = directory.resolve()
    safe = sanitize_filename(filename)
    candidate = directory / safe
    stem, suffix = candidate.stem, candidate.suffix
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem} ({counter}){suffix}"
        counter += 1
    if candidate.parent.resolve() != directory:
        raise ValueError("destination escaped Downloads")
    return candidate


def validate_size_and_space(directory: Path, size: int) -> None:
    """Reject oversized transfers or transfers that would exhaust storage."""
    if size < 0 or size > max_transfer_bytes():
        raise ValueError("transfer size exceeds configured limit")
    directory.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(directory).free < size + MIN_FREE_RESERVE:
        raise ValueError("insufficient free space for Bluetooth transfer")


@dataclass(frozen=True)
class ObexTransfer:
    """Public bounded transfer state used by API, WebUI, and TUI."""

    id: str
    direction: str
    address: str
    source_adapter: str | None
    name: str
    size: int
    status: str = "queued"
    transferred: int = 0
    path: str | None = None
    remote_path: str | None = None
    session_path: str | None = None
    error: str | None = None
    started_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.__dict__.items()
            if value is not None
        }


class ObexError(RuntimeError):
    """Stable OBEX service error with an API code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class BlueZObexManager:
    """Use the BlueZ session-bus OBEX API with bounded transfer history."""

    def __init__(self, history_limit: int = 50, timeout: float = 15.0) -> None:
        self.history_limit = history_limit
        self.timeout = timeout
        self._bus: Any | None = None
        self._system_bus: Any | None = None
        self._transfers: dict[str, ObexTransfer] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._remote_to_local: dict[str, str] = {}
        self._lock = threading.Lock()
        self._agent: Any | None = None
        self._agent_registered = False
        self._available = False
        self._last_error: str | None = None

    async def state(self) -> dict[str, Any]:
        available = False
        try:
            await self._connect()
            available = True
            self._last_error = None
        except Exception as exc:
            self._last_error = str(exc)
        with self._lock:
            transfers = [item.to_dict() for item in self._transfers.values()]
        return {
            "ok": available,
            "backend": "bluez-obex-dbus",
            "available": available,
            "receive_agent": self._agent_registered,
            "download_directory": str(downloads_directory()),
            "max_transfer_bytes": max_transfer_bytes(),
            "transfers": transfers,
            "error": self._last_error,
        }

    def snapshot(self) -> dict[str, Any]:
        """Return current OBEX status without opening a bus or changing state."""
        with self._lock:
            transfers = [item.to_dict() for item in self._transfers.values()]
        return {
            "ok": self._available,
            "backend": "bluez-obex-dbus",
            "available": self._available,
            "receive_agent": self._agent_registered,
            "download_directory": str(downloads_directory()),
            "max_transfer_bytes": max_transfer_bytes(),
            "transfers": transfers,
            "error": self._last_error,
        }

    async def start_receive_agent(self) -> dict[str, Any]:
        """Register one Object Push authorization agent on the session bus."""
        if method is None:
            raise ObexError("backend_unavailable", "dbus-fast is not installed")
        bus = await self._connect()
        if self._agent_registered:
            return {"ok": True, "already_registered": True}
        agent_path = "/org/rpidashboard/obex_agent"
        self._agent = _ReceiveAgent(self)
        bus.export(agent_path, self._agent)
        await self._call(
            OBEX_ROOT,
            OBEX_AGENT_MANAGER,
            "RegisterAgent",
            signature="o",
            body=[agent_path],
        )
        self._agent_registered = True
        return {"ok": True, "agent_path": agent_path}

    async def start_send(
        self,
        address: str,
        file_path: str,
        source_adapter: str | None,
    ) -> ObexTransfer:
        """Create one OPP session and return immediately after SendFile starts."""
        path = Path(file_path).expanduser().resolve()
        if not path.is_file() or path.is_symlink():
            raise ObexError("file_missing", "Outbound file must be a regular non-symlink file")
        size = path.stat().st_size
        if size > max_transfer_bytes():
            raise ObexError("size_limit", "Outbound file exceeds configured transfer limit")
        transfer_id = uuid4().hex
        record = ObexTransfer(
            id=transfer_id,
            direction="outbound",
            address=address.upper(),
            source_adapter=source_adapter,
            name=path.name,
            size=size,
            status="starting",
            path=str(path),
        )
        self._remember(record)
        options = {"Target": Variant("s", "opp")}
        if source_adapter:
            options["Source"] = Variant("s", source_adapter.upper())
        try:
            session_reply = await self._call(
                OBEX_ROOT,
                OBEX_CLIENT,
                "CreateSession",
                signature="sa{sv}",
                body=[address.upper(), options],
            )
            session_path = str(session_reply.body[0])
            send_reply = await self._call(
                session_path,
                OBEX_OBJECT_PUSH,
                "SendFile",
                signature="s",
                body=[str(path)],
            )
            remote_path = str(send_reply.body[0])
        except Exception as exc:
            failed = replace(record, status="failed", error=str(exc), updated_at=_now())
            self._remember(failed)
            raise ObexError("connection_failed", str(exc)) from exc
        active = replace(
            record,
            status="active",
            remote_path=remote_path,
            session_path=session_path,
            updated_at=_now(),
        )
        self._remember(active)
        self._remote_to_local[remote_path] = transfer_id
        self._tasks[transfer_id] = asyncio.create_task(self._monitor(transfer_id))
        return active

    async def cancel(self, transfer_id: str) -> ObexTransfer:
        record = self._get(transfer_id)
        if record is None:
            raise ObexError("transfer_missing", "Bluetooth transfer does not exist")
        if record.status not in {"queued", "starting", "active"}:
            return record
        if record.remote_path:
            await self._call(record.remote_path, OBEX_TRANSFER, "Cancel")
        task = self._tasks.pop(transfer_id, None)
        if task is not None:
            task.cancel()
        cancelled = replace(record, status="cancelled", updated_at=_now())
        self._remember(cancelled)
        await self._remove_session(record.session_path)
        return cancelled

    async def authorize_incoming(self, remote_path: str) -> str:
        """Authorize only a paired/trusted owner and return a private staging path."""
        props = await self._get_all(remote_path, OBEX_TRANSFER)
        session_path = str(_value(props.get("Session"), ""))
        session = await self._get_all(session_path, OBEX_SESSION)
        address = str(_value(session.get("Destination"), "")).upper()
        source = str(_value(session.get("Source"), "")).upper() or None
        name = sanitize_filename(str(_value(props.get("Name"), "bluetooth-file")))
        size = int(_value(props.get("Size"), 0) or 0)
        if not await self._trusted_owner(source, address):
            raise ObexError("permission_denied", "Incoming Object Push sender is not paired and trusted")
        directory = downloads_directory()
        validate_size_and_space(directory, size)
        transfer_id = uuid4().hex
        staging = directory.resolve() / f".rpi-bt-{transfer_id}.part"
        record = ObexTransfer(
            id=transfer_id,
            direction="inbound",
            address=address,
            source_adapter=source,
            name=name,
            size=size,
            status="active",
            path=str(staging),
            remote_path=remote_path,
            session_path=session_path,
        )
        self._remember(record)
        self._remote_to_local[remote_path] = transfer_id
        self._tasks[transfer_id] = asyncio.create_task(self._monitor(transfer_id))
        return str(staging)

    async def _monitor(self, transfer_id: str) -> None:
        try:
            while True:
                record = self._get(transfer_id)
                if record is None or not record.remote_path:
                    return
                props = await self._get_all(record.remote_path, OBEX_TRANSFER)
                status = str(_value(props.get("Status"), "active")).lower()
                transferred = int(_value(props.get("Transferred"), 0) or 0)
                updated = replace(record, status=status, transferred=transferred, updated_at=_now())
                self._remember(updated)
                if status in {"complete", "error", "cancelled"}:
                    if status == "complete" and updated.direction == "inbound":
                        updated = self._finalize_incoming(updated)
                    self._remember(updated)
                    await self._remove_session(updated.session_path)
                    return
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            record = self._get(transfer_id)
            if record is not None:
                self._remember(replace(record, status="failed", error=str(exc), updated_at=_now()))

    def _finalize_incoming(self, record: ObexTransfer) -> ObexTransfer:
        staging = Path(record.path or "")
        directory = downloads_directory().resolve()
        if not staging.is_file() or staging.parent.resolve() != directory:
            return replace(record, status="failed", error="OBEX staging file is missing", updated_at=_now())
        actual_size = staging.stat().st_size
        if actual_size > max_transfer_bytes() or (record.size and actual_size > record.size):
            staging.unlink(missing_ok=True)
            return replace(record, status="failed", error="received file exceeded authorized size", updated_at=_now())
        destination = collision_safe_path(directory, record.name)
        os.replace(staging, destination)
        return replace(
            record,
            status="complete",
            transferred=actual_size,
            path=str(destination),
            updated_at=_now(),
        )

    async def _trusted_owner(self, source: str | None, destination: str) -> bool:
        if MessageBus is None:
            return False
        if self._system_bus is None or not self._system_bus.connected:
            self._system_bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        reply = await asyncio.wait_for(
            self._system_bus.call(
                Message(
                    destination=BLUEZ,
                    path="/",
                    interface=OBJECT_MANAGER,
                    member="GetManagedObjects",
                )
            ),
            timeout=self.timeout,
        )
        if reply.message_type is MessageType.ERROR:
            return False
        managed = reply.body[0]
        adapter_paths = {
            path
            for path, interfaces in managed.items()
            if source
            and str(_value((interfaces.get("org.bluez.Adapter1") or {}).get("Address"), "")).upper()
            == source
        }
        for path, interfaces in managed.items():
            props = interfaces.get("org.bluez.Device1") or {}
            if str(_value(props.get("Address"), "")).upper() != destination:
                continue
            if source and not any(path.startswith(f"{adapter}/") for adapter in adapter_paths):
                continue
            return bool(_value(props.get("Paired"), False) and _value(props.get("Trusted"), False))
        return False

    async def _connect(self):
        if MessageBus is None:
            raise RuntimeError("dbus-fast is not installed")
        if self._bus is None or not self._bus.connected:
            self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
        reply = await self._bus.call(
            Message(
                destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus",
                member="NameHasOwner",
                signature="s",
                body=[OBEX],
            )
        )
        if reply.message_type is MessageType.ERROR or not reply.body or not reply.body[0]:
            self._available = False
            self._last_error = "org.bluez.obex is unavailable; install and start bluez-obexd"
            raise RuntimeError(self._last_error)
        self._available = True
        self._last_error = None
        return self._bus

    async def _call(
        self,
        path: str,
        interface: str,
        member: str,
        *,
        signature: str = "",
        body: list[Any] | None = None,
    ):
        bus = await self._connect()
        reply = await asyncio.wait_for(
            bus.call(
                Message(
                    destination=OBEX,
                    path=path,
                    interface=interface,
                    member=member,
                    signature=signature,
                    body=body or [],
                )
            ),
            timeout=self.timeout,
        )
        if reply.message_type is MessageType.ERROR:
            raise RuntimeError(str(reply.body[0]) if reply.body else reply.error_name or "OBEX D-Bus error")
        return reply

    async def _get_all(self, path: str, interface: str) -> dict[str, Any]:
        reply = await self._call(
            path,
            PROPERTIES,
            "GetAll",
            signature="s",
            body=[interface],
        )
        return reply.body[0]

    async def _remove_session(self, session_path: str | None) -> None:
        if not session_path:
            return
        try:
            await self._call(
                OBEX_ROOT,
                OBEX_CLIENT,
                "RemoveSession",
                signature="o",
                body=[session_path],
            )
        except Exception:
            return

    def _get(self, transfer_id: str) -> ObexTransfer | None:
        with self._lock:
            return self._transfers.get(transfer_id)

    def _remember(self, record: ObexTransfer) -> None:
        with self._lock:
            self._transfers[record.id] = record
            while len(self._transfers) > self.history_limit:
                oldest = next(iter(self._transfers))
                self._transfers.pop(oldest, None)


if method is not None:
    class _ReceiveAgent(ServiceInterface):
        def __init__(self, manager: BlueZObexManager) -> None:
            super().__init__(OBEX_AGENT)
            self.manager = manager

        @method()
        async def AuthorizePush(
            self,
            transfer: _DBUS_OBJECT_PATH,  # type: ignore[valid-type]
        ) -> _DBUS_STRING:  # type: ignore[valid-type]
            return await self.manager.authorize_incoming(transfer)

        @method()
        def Cancel(self) -> _DBUS_NOTHING:  # type: ignore[valid-type]
            return None
else:  # pragma: no cover
    class _ReceiveAgent:  # type: ignore[no-redef]
        pass


def _value(value: Any, default: Any) -> Any:
    return getattr(value, "value", default) if value is not None else default


_MANAGER = BlueZObexManager()


def get_manager() -> BlueZObexManager:
    return _MANAGER


def set_manager_for_tests(manager: BlueZObexManager) -> None:
    global _MANAGER
    _MANAGER = manager
