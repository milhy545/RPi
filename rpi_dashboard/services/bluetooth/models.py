"""Typed Bluetooth control center state models."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any


SCHEMA_VERSION = 2


def normalize_address(address: str) -> str:
    """Return a stable uppercase Bluetooth address representation."""
    return address.strip().upper()


def adapter_id_from_address(address: str) -> str:
    """Build a stable adapter id from a Bluetooth adapter address."""
    return f"adapter-{normalize_address(address).replace(':', '').lower()}"


@dataclass(frozen=True)
class BluetoothError:
    """Structured Bluetooth error safe for API/UI use."""

    code: str
    message: str
    retryable: bool = False
    adapter_id: str | None = None
    device_key: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error deterministically."""
        return _drop_none(asdict(self))


@dataclass(frozen=True)
class BackendHealth:
    """Backend availability and degradation state."""

    name: str
    degraded: bool = False
    available: bool = True
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize backend health."""
        return asdict(self)


@dataclass(frozen=True)
class Adapter:
    """Bluetooth adapter identity and runtime state."""

    id: str
    bluez_path: str
    index: int | None
    address: str
    address_type: str = "public"
    name: str = ""
    alias: str = ""
    modalias: str = ""
    powered: bool = False
    discoverable: bool = False
    pairable: bool = False
    discovering: bool = False
    present: bool = True
    backend: str = "fake"
    role: str | None = None
    hardware: dict[str, Any] = field(default_factory=dict)
    error: BluetoothError | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize adapter state."""
        data = asdict(self)
        if self.error is not None:
            data["error"] = self.error.to_dict()
        return _drop_none(data)


@dataclass(frozen=True)
class Device:
    """Bluetooth device scoped to one adapter relationship."""

    key: str
    adapter_id: str
    bluez_path: str
    address: str
    address_type: str = "public"
    name: str = ""
    alias: str = ""
    icon: str = ""
    appearance: int | None = None
    uuids: tuple[str, ...] = ()
    paired: bool = False
    bonded: bool | None = None
    trusted: bool = False
    blocked: bool = False
    connected: bool = False
    services_resolved: bool | None = None
    rssi: int | None = None
    tx_power: int | None = None
    battery_percentage: int | None = None
    kind: str = "unknown"
    kind_evidence: tuple[str, ...] = ()
    confidence: str = "unknown"
    first_seen: str | None = None
    last_seen: str | None = None
    present: bool = True
    known: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize device state without merging adapters."""
        data = asdict(self)
        data["uuids"] = list(self.uuids)
        data["kind_evidence"] = list(self.kind_evidence)
        return _drop_none(data)


@dataclass(frozen=True)
class Operation:
    """Bluetooth operation lifecycle record."""

    id: str
    type: str
    adapter_id: str | None = None
    device_key: str | None = None
    state: str = "pending"
    started_at: str = ""
    updated_at: str = ""
    cancellable: bool = False
    result: dict[str, Any] = field(default_factory=dict)
    error: BluetoothError | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize operation state."""
        data = asdict(self)
        if self.error is not None:
            data["error"] = self.error.to_dict()
        return _drop_none(data)


@dataclass(frozen=True)
class ReadinessStep:
    """Single evidence-backed readiness step."""

    id: str
    label: str
    state: bool | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize readiness step."""
        return asdict(self)


@dataclass(frozen=True)
class SoundbarReadiness:
    """Samsung soundbar readiness ladder."""

    device_key: str | None = None
    ready: bool = False
    steps: tuple[ReadinessStep, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize soundbar readiness."""
        return {
            "device_key": self.device_key,
            "ready": self.ready,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class ControllerReadiness:
    """Xbox/controller and Steam Link readiness evidence."""

    ready: bool = False
    controllers: tuple[str, ...] = ()
    input_devices: tuple[str, ...] = ()
    modules: dict[str, bool] = field(default_factory=dict)
    steamlink: dict[str, Any] = field(default_factory=dict)
    blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize controller readiness."""
        return {
            "ready": self.ready,
            "controllers": list(self.controllers),
            "input_devices": list(self.input_devices),
            "modules": dict(self.modules),
            "steamlink": dict(self.steamlink),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class Event:
    """Bounded diagnostic event for UI feedback."""

    id: str
    type: str
    message: str
    timestamp: str
    adapter_id: str | None = None
    device_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize event."""
        return _drop_none(asdict(self))


@dataclass(frozen=True)
class BluetoothState:
    """Versioned Bluetooth state contract shared by API, WebUI, and TUI."""

    backend: BackendHealth
    adapters: tuple[Adapter, ...] = ()
    devices: tuple[Device, ...] = ()
    operations: tuple[Operation, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)
    events: tuple[Event, ...] = ()
    ok: bool = True
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete Bluetooth state deterministically."""
        return {
            "ok": self.ok,
            "schema_version": self.schema_version,
            "backend": self.backend.to_dict(),
            "adapters": [adapter.to_dict() for adapter in self.adapters],
            "devices": [device.to_dict() for device in self.devices],
            "operations": [operation.to_dict() for operation in self.operations],
            "diagnostics": dict(self.diagnostics),
            "events": [event.to_dict() for event in self.events],
        }


def make_device_key(adapter_id: str, address: str) -> str:
    """Build a stable device key scoped to one adapter."""
    return f"{adapter_id}/{normalize_address(address)}"


def classify_device(
    name: str | None = "",
    icon: str | None = "",
    uuids: tuple[str | None, ...] | None = (),
    appearance: int | None = None,
) -> tuple[str, tuple[str, ...], str]:
    """Classify a Bluetooth device from evidence stronger than name alone."""
    evidence: list[str] = []
    uuid_text = " ".join((uuid or "").lower() for uuid in (uuids or ()))
    icon_lower = (icon or "").lower()
    name_lower = (name or "").lower()

    if "00001124" in uuid_text or "hid" in uuid_text:
        evidence.append("uuid:hid")
        return "gamepad", tuple(evidence), "medium"
    if icon_lower in {"input-gaming", "input-gamepad"}:
        evidence.append(f"icon:{icon}")
        return "gamepad", tuple(evidence), "medium"
    if "0000110b" in uuid_text or "0000110d" in uuid_text:
        evidence.append("uuid:audio")
        return "speaker", tuple(evidence), "high"
    if icon_lower in {"audio-card", "audio-headset", "audio-speakers"}:
        evidence.append(f"icon:{icon}")
        return "speaker", tuple(evidence), "medium"
    if appearance is not None:
        evidence.append(f"appearance:{appearance}")
    if any(token in name_lower for token in ("xbox", "gamepad", "controller")):
        evidence.append("name:controller")
        return "gamepad", tuple(evidence), "low"
    if any(token in name_lower for token in ("soundbar", "speaker", "audio")):
        evidence.append("name:audio")
        return "speaker", tuple(evidence), "low"
    return "unknown", tuple(evidence), "unknown"


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}
