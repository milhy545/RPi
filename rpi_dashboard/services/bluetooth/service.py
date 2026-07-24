"""Synchronous service facade for the Bluetooth control center."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any
from uuid import uuid4

from .compat import legacy_state
from .bluez import BlueZDbusBackend
from .fake import FakeBluetoothBackend
from .fallback import BluetoothctlBackend
from .models import BluetoothError
from .models import BluetoothState
from .models import Operation
from .models import make_device_key

_BACKEND: Any | None = None
_RUNNER: "_AsyncRunner | None" = None
_RUNNER_LOCK = threading.Lock()
_SETTINGS_LOCK = threading.Lock()
_AUTO_CONNECT_LOCK = threading.Lock()
_STARTUP_RECOVERY_LOCK = threading.Lock()
_STARTUP_RECOVERY_STARTED = False
_PAIRING_LOCK = threading.Lock()
_PAIRING_OPERATIONS: dict[str, dict[str, Any]] = {}
_PAIRING_FUTURES: dict[str, Any] = {}
_AUDIO_RECONCILE_LOCK = threading.Lock()
_AUDIO_RECONCILE_NEXT = 0.0
_DISCOVERY_LOCK = threading.Lock()
_DISCOVERY_STOP_FUTURES: dict[str, tuple[str, Any]] = {}
_AUTO_CONNECT_LAST_ATTEMPT: dict[str, float] = {}
_AUTO_CONNECT_FAILURES: dict[str, int] = {}
_AUTO_CONNECT_NEXT_ATTEMPT: dict[str, float] = {}
_MANUAL_DISCONNECT_UNTIL: dict[str, float] = {}
_MANUAL_DISCONNECT_COOLDOWN = 60.0
_DEFAULT_SETTINGS: dict[str, Any] = {
    "auto_connect": True,
    "discoverable_timeout": 120,
    "scan_mode": "balanced",
    "device_auto_connect": {},
    "device_hid_control": {},
}


def get_backend() -> Any:
    """Return the configured Bluetooth backend singleton."""
    global _BACKEND
    if _BACKEND is None:
        if os.environ.get("RPI_BLUETOOTH_BACKEND") == "fake":
            _BACKEND = FakeBluetoothBackend.with_soundbar_and_controller()
        elif os.environ.get("RPI_BLUETOOTH_BACKEND") == "bluetoothctl":
            _BACKEND = BluetoothctlBackend()
        else:
            _BACKEND = BlueZDbusBackend(fallback=BluetoothctlBackend())
    return _BACKEND


def set_backend_for_tests(backend: Any | None) -> None:
    """Override the backend in tests."""
    global _BACKEND
    _BACKEND = backend


def start_startup_recovery(*, delay: float = 2.0) -> bool:
    """Start one bounded background recovery pass for a headless boot."""
    global _STARTUP_RECOVERY_STARTED
    with _STARTUP_RECOVERY_LOCK:
        if _STARTUP_RECOVERY_STARTED:
            return False
        _STARTUP_RECOVERY_STARTED = True

    thread = threading.Thread(
        target=_startup_recovery_worker,
        args=(max(0.0, delay),),
        name="bluetooth-startup-recovery",
        daemon=True,
    )
    thread.start()
    return True


def _startup_recovery_worker(delay: float) -> None:
    if delay:
        time.sleep(delay)
    try:
        _recover_startup_once()
        backend = get_backend()
        if _RUNNER is not None:
            _RUNNER.submit(_watch_reconnect_events(backend))
            _RUNNER.submit(_start_obex_agent_safely())
            _RUNNER.submit(_reconcile_audio_after_bluetooth_change(delay=1.5))
    except Exception:
        # Recovery is best-effort and must never take down the dashboard.
        return


def _recover_startup_once() -> BluetoothState:
    """Power present adapters and reconnect their paired trusted devices."""
    backend = get_backend()
    state = _run(backend.state())
    if not _load_settings().get("auto_connect"):
        return state

    for adapter in state.adapters:
        if adapter.present and not adapter.powered:
            _run(backend.set_adapter_power(adapter.id, True))

    state = _run(backend.state())
    return _apply_auto_connect(backend, state, force=True)


def bluetooth_state() -> dict[str, Any]:
    """Return the versioned Bluetooth state contract."""
    backend = get_backend()
    state_obj = _run(backend.state())
    state = state_obj.to_dict()
    _enrich_runtime_state(state)
    return state


def devices_compat_state() -> dict[str, Any]:
    """Return legacy-compatible Bluetooth state with embedded v2 data."""
    state = legacy_state(_run(get_backend().state()))
    _enrich_runtime_state(state["v2"])
    return state


def start_discovery(
    adapter_id: str | None = None,
    seconds: int | None = None,
) -> dict[str, Any]:
    """Start bounded discovery on a selected or uniquely resolved adapter."""
    state = _run(get_backend().state())
    adapter = _resolve_adapter(state, adapter_id)
    if isinstance(adapter, BluetoothError):
        return _error_response(adapter)
    operation = _run(get_backend().start_discovery(adapter.id))
    response = _operation_response(operation)
    if operation.state == "succeeded":
        settings = _load_settings()
        default_seconds = 30 if settings.get("scan_mode") == "aggressive" else 15
        duration = max(1, min(60, int(seconds if seconds is not None else default_seconds)))
        _schedule_discovery_stop(adapter.id, duration)
        response["discovery_timeout_seconds"] = duration
    return response


def stop_discovery(adapter_id: str | None = None) -> dict[str, Any]:
    """Stop discovery on a selected or uniquely resolved adapter."""
    state = _run(get_backend().state())
    adapter = _resolve_adapter(state, adapter_id)
    if isinstance(adapter, BluetoothError):
        return _error_response(adapter)
    _cancel_discovery_stop(adapter.id)
    operation = _run(get_backend().stop_discovery(adapter.id))
    return _operation_response(operation)


def _schedule_discovery_stop(adapter_id: str, seconds: int) -> None:
    """Replace one adapter's pending timer without blocking a request thread."""
    token = uuid4().hex
    backend = get_backend()
    assert _RUNNER is not None
    future = _RUNNER.submit(
        _stop_discovery_after(adapter_id, seconds, token, backend)
    )
    with _DISCOVERY_LOCK:
        previous = _DISCOVERY_STOP_FUTURES.pop(adapter_id, None)
        _DISCOVERY_STOP_FUTURES[adapter_id] = (token, future)
    if previous is not None:
        previous[1].cancel()


def _cancel_discovery_stop(adapter_id: str) -> None:
    with _DISCOVERY_LOCK:
        pending = _DISCOVERY_STOP_FUTURES.pop(adapter_id, None)
    if pending is not None:
        pending[1].cancel()


async def _stop_discovery_after(
    adapter_id: str,
    seconds: int,
    token: str,
    backend: Any,
) -> None:
    try:
        await asyncio.sleep(seconds)
        with _DISCOVERY_LOCK:
            current = _DISCOVERY_STOP_FUTURES.get(adapter_id)
            if current is None or current[0] != token:
                return
        await backend.stop_discovery(adapter_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        return
    finally:
        with _DISCOVERY_LOCK:
            current = _DISCOVERY_STOP_FUTURES.get(adapter_id)
            if current is not None and current[0] == token:
                _DISCOVERY_STOP_FUTURES.pop(adapter_id, None)


def set_adapter_power(adapter_id: str | None, powered: bool) -> dict[str, Any]:
    """Set adapter power through the active backend."""
    state = _run(get_backend().state())
    adapter = _resolve_adapter(state, adapter_id)
    if isinstance(adapter, BluetoothError):
        return _error_response(adapter)
    operation = _run(get_backend().set_adapter_power(adapter.id, powered))
    return _operation_response(operation)


def set_adapter_discoverable(
    adapter_id: str | None,
    discoverable: bool,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Set discoverability on a selected or uniquely resolved adapter."""
    state = _run(get_backend().state())
    adapter = _resolve_adapter(state, adapter_id)
    if isinstance(adapter, BluetoothError):
        return _error_response(adapter)
    settings = _load_settings()
    effective_timeout = max(0, int(timeout if timeout is not None else settings["discoverable_timeout"]))
    operation = _run(
        get_backend().set_adapter_discoverable(
            adapter.id,
            discoverable,
            effective_timeout,
        )
    )
    return _operation_response(operation)


def update_settings(
    *,
    auto_connect: bool | None = None,
    discoverable_timeout: int | None = None,
    scan_mode: str | None = None,
) -> dict[str, Any]:
    """Persist dashboard-owned Bluetooth behavior settings."""
    settings = _load_settings()
    if auto_connect is not None:
        settings["auto_connect"] = bool(auto_connect)
    if discoverable_timeout is not None:
        settings["discoverable_timeout"] = max(0, min(3600, int(discoverable_timeout)))
    if scan_mode is not None:
        normalized_mode = scan_mode.strip().lower()
        if normalized_mode not in {"balanced", "aggressive"}:
            return _error_response(
                BluetoothError("unsupported", "scan_mode must be balanced or aggressive")
            )
        settings["scan_mode"] = normalized_mode
    _save_settings(settings)
    if auto_connect:
        state = _run(get_backend().state())
        _apply_auto_connect(get_backend(), state, force=True)
    return {"ok": True, "settings": settings}


def set_device_auto_connect(
    adapter_id: str | None,
    device_key: str | None,
    enabled: bool,
) -> dict[str, Any]:
    """Persist a per-device override using its adapter-scoped identity."""
    if not adapter_id or not device_key:
        return _error_response(
            BluetoothError(
                "device_missing",
                "adapter_id and device_key are required",
            )
        )
    state = _run(get_backend().state())
    target = _resolve_device(
        state,
        adapter_id=adapter_id,
        device_key=device_key,
        mac=None,
    )
    if isinstance(target, BluetoothError):
        return _error_response(target)
    settings = _load_settings()
    policies = dict(settings.get("device_auto_connect") or {})
    policies[device_key] = bool(enabled)
    settings["device_auto_connect"] = policies
    _save_settings(settings)
    if enabled:
        _apply_auto_connect(get_backend(), state, force=True)
    return {
        "ok": True,
        "adapter_id": adapter_id,
        "device_key": device_key,
        "auto_connect": bool(enabled),
    }


def set_device_hid_control(
    adapter_id: str | None,
    device_key: str | None,
    enabled: bool,
) -> dict[str, Any]:
    """Persist opt-in HID control only when trusted transport prerequisites exist."""
    from .hid import hid_transport_status

    if not adapter_id or not device_key:
        return _error_response(BluetoothError("device_missing", "adapter_id and device_key are required"))
    state = _run(get_backend().state())
    target = _resolve_device(state, adapter_id=adapter_id, device_key=device_key, mac=None)
    if isinstance(target, BluetoothError):
        return _error_response(target)
    device = next(item for item in state.devices if item.key == device_key)
    if enabled and (not device.paired or not device.trusted):
        return _error_response(
            BluetoothError("permission_denied", "HID control requires a paired and trusted device")
        )
    transport = hid_transport_status()
    if enabled and not transport["available"]:
        return _error_response(
            BluetoothError(
                "profile_unavailable",
                "Outbound HID control is unavailable: " + "; ".join(transport["blockers"]),
            )
        )
    settings = _load_settings()
    policies = dict(settings.get("device_hid_control") or {})
    policies[device_key] = bool(enabled)
    settings["device_hid_control"] = policies
    _save_settings(settings)
    return {
        "ok": True,
        "adapter_id": adapter_id,
        "device_key": device_key,
        "hid_control": bool(enabled),
        "transport": transport,
    }


def device_action(
    action: str,
    *,
    adapter_id: str | None = None,
    device_key: str | None = None,
    mac: str | None = None,
) -> dict[str, Any]:
    """Run an adapter-aware device action or legacy MAC resolution."""
    state = _run(get_backend().state())
    target = _resolve_device(state, adapter_id=adapter_id, device_key=device_key, mac=mac)
    if isinstance(target, BluetoothError):
        return _error_response(target)
    resolved_adapter_id, resolved_device_key = target
    runner = getattr(get_backend(), action, None)
    if runner is None:
        return _error_response(BluetoothError("unsupported", f"Unsupported action: {action}"))
    operation = _run(runner(resolved_adapter_id, resolved_device_key))
    if action == "disconnect" and operation.state == "succeeded":
        with _AUTO_CONNECT_LOCK:
            _MANUAL_DISCONNECT_UNTIL[resolved_device_key] = (
                time.monotonic() + _MANUAL_DISCONNECT_COOLDOWN
            )
    return _operation_response(operation)


def device_profile_action(
    action: str,
    profile_uuid: str,
    *,
    adapter_id: str | None = None,
    device_key: str | None = None,
    mac: str | None = None,
) -> dict[str, Any]:
    """Connect or disconnect one advertised profile on an adapter-scoped device."""
    if action not in {"connect", "disconnect"}:
        return _error_response(
            BluetoothError("unsupported", "Profile action must be connect or disconnect")
        )
    normalized = profile_uuid.strip().lower()
    if not normalized:
        return _error_response(BluetoothError("profile_unavailable", "profile_uuid is required"))
    state = _run(get_backend().state())
    target = _resolve_device(state, adapter_id=adapter_id, device_key=device_key, mac=mac)
    if isinstance(target, BluetoothError):
        return _error_response(target)
    resolved_adapter_id, resolved_device_key = target
    runner = getattr(get_backend(), f"{action}_profile", None)
    if runner is None:
        return _error_response(BluetoothError("unsupported", "Profile operations are unavailable"))
    operation = _run(
        runner(resolved_adapter_id, resolved_device_key, normalized)
    )
    return _operation_response(operation)


def obex_state() -> dict[str, Any]:
    """Return bounded OBEX backend and transfer state."""
    from .obex import get_manager

    return _run(get_manager().state())


def bluetooth_diagnostics() -> dict[str, Any]:
    """Run explicit bounded read-only Bluetooth/audio diagnostics."""
    from .diagnostics import collect_diagnostics

    return collect_diagnostics()


def download_files() -> dict[str, Any]:
    """List bounded, regular outbound candidates from ~/Downloads only."""
    from .obex import downloads_directory, max_transfer_bytes

    directory = downloads_directory().resolve()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        entries = [
            path
            for path in directory.iterdir()
            if path.is_file() and not path.is_symlink() and path.stat().st_size <= max_transfer_bytes()
        ]
    except OSError as exc:
        return {"ok": False, "error": str(exc), "directory": str(directory), "files": []}
    entries.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return {
        "ok": True,
        "directory": str(directory),
        "files": [
            {
                "name": path.name,
                "path": str(path),
                "size": path.stat().st_size,
                "modified": path.stat().st_mtime,
            }
            for path in entries[:100]
        ],
    }


def send_file(
    file_path: str,
    *,
    adapter_id: str | None = None,
    device_key: str | None = None,
    mac: str | None = None,
) -> dict[str, Any]:
    """Start OPP send to one paired, trusted, adapter-scoped device."""
    from .obex import ObexError, downloads_directory, get_manager

    if not file_path:
        return _error_response(BluetoothError("file_missing", "path is required"))
    path = Path(file_path).expanduser().resolve()
    allowed_root = downloads_directory().resolve()
    if path.parent != allowed_root:
        return _error_response(
            BluetoothError(
                "permission_denied",
                "Outbound Bluetooth files must be selected from ~/Downloads",
            )
        )
    state = _run(get_backend().state())
    resolved = _resolve_device(state, adapter_id=adapter_id, device_key=device_key, mac=mac)
    if isinstance(resolved, BluetoothError):
        return _error_response(resolved)
    resolved_adapter, resolved_key = resolved
    device = next(item for item in state.devices if item.key == resolved_key)
    adapter = next(item for item in state.adapters if item.id == resolved_adapter)
    if not device.paired or not device.trusted:
        return _error_response(
            BluetoothError(
                "permission_denied",
                "Object Push requires a paired and trusted device",
                adapter_id=resolved_adapter,
                device_key=resolved_key,
            )
        )
    from .capabilities import capability_summary

    if not capability_summary(device.uuids)["file_transfer"]["object_push"]:
        return _error_response(
            BluetoothError(
                "profile_unavailable",
                "Device does not advertise Object Push",
                adapter_id=resolved_adapter,
                device_key=resolved_key,
            )
        )
    try:
        transfer = _run(
            get_manager().start_send(device.address, str(path), adapter.address)
        )
    except ObexError as exc:
        return _error_response(BluetoothError(exc.code, str(exc)))
    return {"ok": True, "transfer": transfer.to_dict()}


def cancel_file_transfer(transfer_id: str) -> dict[str, Any]:
    """Cancel one active OBEX transfer by its dashboard ID."""
    from .obex import ObexError, get_manager

    if not transfer_id:
        return _error_response(BluetoothError("transfer_missing", "transfer_id is required"))
    try:
        transfer = _run(get_manager().cancel(transfer_id))
    except ObexError as exc:
        return _error_response(BluetoothError(exc.code, str(exc)))
    return {"ok": True, "transfer": transfer.to_dict()}


def operation_status(operation_id: str) -> dict[str, Any]:
    """Look up one bounded backend operation record."""
    if not operation_id:
        return _error_response(BluetoothError("operation_missing", "operation_id is required"))
    state = _run(get_backend().state())
    operation = next((item for item in state.operations if item.id == operation_id), None)
    if operation is None:
        return _error_response(BluetoothError("operation_missing", "Bluetooth operation does not exist"))
    return {"ok": True, "operation": operation.to_dict()}


def media_action(
    action: str,
    *,
    value: int | None = None,
    adapter_id: str | None = None,
    device_key: str | None = None,
    mac: str | None = None,
) -> dict[str, Any]:
    """Run one capability-checked AVRCP action on an adapter-scoped device."""
    if action not in {"play", "pause", "stop", "next", "previous", "volume"}:
        return _error_response(BluetoothError("unsupported", "Unsupported media action"))
    state = _run(get_backend().state())
    target = _resolve_device(state, adapter_id=adapter_id, device_key=device_key, mac=mac)
    if isinstance(target, BluetoothError):
        return _error_response(target)
    resolved_adapter, resolved_key = target
    operation = _run(
        get_backend().media_control(resolved_adapter, resolved_key, action, value)
    )
    return _operation_response(operation)


def start_pairing(
    *,
    adapter_id: str | None = None,
    device_key: str | None = None,
    mac: str | None = None,
) -> dict[str, Any]:
    """Start one explicit pairing operation without blocking its UI request."""
    backend = get_backend()
    state = _run(backend.state())
    target = _resolve_device(state, adapter_id=adapter_id, device_key=device_key, mac=mac)
    if isinstance(target, BluetoothError):
        return _error_response(target)
    resolved_adapter, resolved_key = target
    with _PAIRING_LOCK:
        active = next(
            (
                item
                for item in _PAIRING_OPERATIONS.values()
                if item["state"] == "pending"
                and item["adapter_id"] == resolved_adapter
                and item["device_key"] == resolved_key
            ),
            None,
        )
        if active is not None:
            return {"ok": True, "pairing": dict(active), "deduplicated": True}
        operation_id = f"pair-{uuid4().hex}"
        record = {
            "id": operation_id,
            "state": "pending",
            "adapter_id": resolved_adapter,
            "device_key": resolved_key,
            "started_at": time.time(),
        }
        _PAIRING_OPERATIONS[operation_id] = record
        while len(_PAIRING_OPERATIONS) > 20:
            oldest = next(iter(_PAIRING_OPERATIONS))
            if oldest == operation_id:
                break
            _PAIRING_OPERATIONS.pop(oldest, None)
            _PAIRING_FUTURES.pop(oldest, None)
    assert _RUNNER is not None
    future = _RUNNER.submit(
        _pairing_worker(operation_id, resolved_adapter, resolved_key, backend)
    )
    with _PAIRING_LOCK:
        _PAIRING_FUTURES[operation_id] = future
    return {"ok": True, "pairing": dict(record)}


async def _pairing_worker(
    operation_id: str,
    adapter_id: str,
    device_key: str,
    backend: Any,
) -> None:
    try:
        operation = await backend.pair(adapter_id, device_key)
        update = {
            "state": "succeeded" if operation.state == "succeeded" else "failed",
            "operation": operation.to_dict(),
            "error": operation.error.message if operation.error else None,
            "code": operation.error.code if operation.error else None,
            "updated_at": time.time(),
        }
    except asyncio.CancelledError:
        update = {"state": "cancelled", "updated_at": time.time()}
    except Exception as exc:
        update = {
            "state": "failed",
            "error": str(exc),
            "code": "backend_unavailable",
            "updated_at": time.time(),
        }
    with _PAIRING_LOCK:
        if operation_id in _PAIRING_OPERATIONS:
            _PAIRING_OPERATIONS[operation_id].update(update)


def pairing_status(operation_id: str) -> dict[str, Any]:
    """Return one pairing lifecycle record and its current user challenge."""
    with _PAIRING_LOCK:
        record = dict(_PAIRING_OPERATIONS.get(operation_id) or {})
    if not record:
        return _error_response(BluetoothError("operation_missing", "Pairing operation does not exist"))
    challenge_getter = getattr(get_backend(), "pairing_challenge", None)
    challenge = challenge_getter() if challenge_getter is not None else None
    if challenge and (
        challenge.get("adapter_id") != record["adapter_id"]
        or challenge.get("device_key") != record["device_key"]
    ):
        challenge = None
    return {"ok": True, "pairing": record, "challenge": challenge}


def respond_pairing(
    operation_id: str,
    accepted: bool,
    value: str | int | None = None,
) -> dict[str, Any]:
    """Resolve a visible pairing challenge for its exact pending target."""
    status = pairing_status(operation_id)
    if not status.get("ok"):
        return status
    if status["pairing"]["state"] != "pending" or not status.get("challenge"):
        return _error_response(BluetoothError("operation_not_cancellable", "No pairing challenge is waiting"))
    responder = getattr(get_backend(), "respond_pairing", None)
    if responder is None or not responder(accepted, value):
        return _error_response(BluetoothError("operation_busy", "Pairing challenge already changed"))
    return {"ok": True, "accepted": accepted}


def cancel_pairing(operation_id: str) -> dict[str, Any]:
    """Cancel a pending pairing worker and Device1 pairing transaction."""
    status = pairing_status(operation_id)
    if not status.get("ok"):
        return status
    record = status["pairing"]
    if record["state"] != "pending":
        return _error_response(BluetoothError("operation_not_cancellable", "Pairing is already complete"))
    canceller = getattr(get_backend(), "cancel_pairing", None)
    operation = None
    if canceller is not None:
        operation = _run(canceller(record["adapter_id"], record["device_key"]))
    with _PAIRING_LOCK:
        future = _PAIRING_FUTURES.get(operation_id)
        if future is not None:
            future.cancel()
        _PAIRING_OPERATIONS[operation_id].update(
            {"state": "cancelled", "updated_at": time.time()}
        )
    response = {"ok": True, "pairing": dict(_PAIRING_OPERATIONS[operation_id])}
    if operation is not None:
        response["operation"] = operation.to_dict()
    return response


def cancel_operation(operation_id: str) -> dict[str, Any]:
    """Request cancellation through the active backend."""
    if not operation_id:
        return _error_response(BluetoothError("operation_missing", "operation_id is required"))
    operation = _run(get_backend().cancel(operation_id))
    return _operation_response(operation)


async def _start_obex_agent_safely() -> None:
    from .obex import get_manager

    try:
        await get_manager().start_receive_agent()
    except Exception:
        return


def _resolve_adapter(state: BluetoothState, adapter_id: str | None):
    present = [adapter for adapter in state.adapters if adapter.present]
    if adapter_id:
        adapter = next((candidate for candidate in present if candidate.id == adapter_id), None)
        if adapter is None:
            return BluetoothError(
                "adapter_missing",
                "Adapter is not present",
                retryable=True,
                adapter_id=adapter_id,
            )
        return adapter
    if len(present) == 1:
        return present[0]
    if not present:
        return BluetoothError("adapter_missing", "No Bluetooth adapter is present", retryable=True)
    return BluetoothError(
        "ambiguous_device",
        "Multiple Bluetooth adapters are present; adapter_id is required",
        retryable=False,
    )


def _resolve_device(
    state: BluetoothState,
    *,
    adapter_id: str | None,
    device_key: str | None,
    mac: str | None,
) -> tuple[str, str] | BluetoothError:
    if device_key and adapter_id:
        found = next(
            (
                device for device in state.devices
                if device.key == device_key and device.adapter_id == adapter_id and device.present
            ),
            None,
        )
        if found:
            return adapter_id, device_key
        return BluetoothError(
            "device_missing",
            "Device is not present on selected adapter",
            retryable=True,
            adapter_id=adapter_id,
            device_key=device_key,
        )
    if not mac:
        return BluetoothError("device_missing", "mac or adapter_id/device_key required")
    normalized = mac.strip().upper()
    matches = [
        device for device in state.devices
        if device.address == normalized
        and device.present
        and (not adapter_id or device.adapter_id == adapter_id)
    ]
    if not matches:
        present_adapters = [adapter for adapter in state.adapters if adapter.present]
        if adapter_id:
            adapter = next(
                (candidate for candidate in present_adapters if candidate.id == adapter_id),
                None,
            )
            if adapter is not None:
                return adapter.id, make_device_key(adapter.id, normalized)
        if len(present_adapters) == 1:
            adapter = present_adapters[0]
            return adapter.id, make_device_key(adapter.id, normalized)
        if len(present_adapters) > 1:
            return BluetoothError(
                "ambiguous_device",
                "Device is not uniquely known; adapter_id is required",
                retryable=False,
                detail=normalized,
            )
        return BluetoothError(
            "device_missing",
            "Device is not known",
            retryable=True,
            detail=normalized,
        )
    if len(matches) > 1:
        return BluetoothError(
            "ambiguous_device",
            "Device exists on multiple adapters; adapter_id and device_key are required",
            retryable=False,
            detail=normalized,
        )
    return matches[0].adapter_id, matches[0].key


def _operation_response(operation: Operation) -> dict[str, Any]:
    data = operation.to_dict()
    response = {
        "ok": operation.state == "succeeded",
        "operation": data,
    }
    if operation.error is not None:
        response["error"] = operation.error.message
        response["code"] = operation.error.code
    else:
        response["result"] = f"{operation.type} {operation.state}"
    return response


def _error_response(error: BluetoothError) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error.message,
        "code": error.code,
        "details": error.to_dict(),
    }


def _run(awaitable):
    global _RUNNER
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Bluetooth sync facade must run outside an event loop")
    if _RUNNER is None:
        with _RUNNER_LOCK:
            if _RUNNER is None:
                _RUNNER = _AsyncRunner()
    return _RUNNER.run(awaitable)


class _AsyncRunner:
    """Run all backend coroutines on one persistent event loop."""

    def __init__(self) -> None:
        self._ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="bluetooth-service-loop",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("Bluetooth service event loop did not start")

    def _run_loop(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.call_soon(self._ready.set)
        self.loop.run_forever()

    def run(self, awaitable: Any, timeout: float = 20.0) -> Any:
        future = asyncio.run_coroutine_threadsafe(awaitable, self.loop)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError(
                f"Bluetooth operation timed out after {timeout:g} seconds"
            ) from None

    def submit(self, awaitable: Any):
        """Schedule a long-lived coroutine without blocking its caller."""
        return asyncio.run_coroutine_threadsafe(awaitable, self.loop)

def _settings_path() -> Path:
    configured = os.environ.get("RPI_BLUETOOTH_SETTINGS_PATH")
    if configured:
        return Path(configured)
    return Path.home() / ".config" / "rpi-dashboard" / "bluetooth.json"


def _load_settings() -> dict[str, Any]:
    with _SETTINGS_LOCK:
        settings = dict(_DEFAULT_SETTINGS)
        try:
            data = json.loads(_settings_path().read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return settings
        if isinstance(data, dict):
            settings.update({key: data[key] for key in settings.keys() & data.keys()})
        return settings


def _save_settings(settings: dict[str, Any]) -> None:
    with _SETTINGS_LOCK:
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)


def _apply_auto_connect(
    backend: Any,
    state: BluetoothState,
    *,
    force: bool = False,
) -> BluetoothState:
    return _run(_apply_auto_connect_async(backend, state, force=force))


async def _apply_auto_connect_async(
    backend: Any,
    state: BluetoothState,
    *,
    force: bool = False,
) -> BluetoothState:
    settings = _load_settings()
    if not settings.get("auto_connect"):
        return state
    powered = {adapter.id for adapter in state.adapters if adapter.present and adapter.powered}
    device_policies = settings.get("device_auto_connect") or {}
    now = time.monotonic()
    attempted = False
    known_keys = {device.key for device in state.devices}
    with _AUTO_CONNECT_LOCK:
        for mapping in (
            _AUTO_CONNECT_LAST_ATTEMPT,
            _AUTO_CONNECT_FAILURES,
            _AUTO_CONNECT_NEXT_ATTEMPT,
            _MANUAL_DISCONNECT_UNTIL,
        ):
            for stale_key in set(mapping) - known_keys:
                mapping.pop(stale_key, None)
    for device in state.devices:
        if device_policies.get(device.key) is False:
            continue
        if not (
            device.present
            and device.adapter_id in powered
            and device.paired
            and device.trusted
            and not device.connected
        ):
            continue
        with _AUTO_CONNECT_LOCK:
            if not force and now < _MANUAL_DISCONNECT_UNTIL.get(device.key, 0.0):
                continue
            if not force and now < _AUTO_CONNECT_NEXT_ATTEMPT.get(device.key, 0.0):
                continue
            last_attempt = _AUTO_CONNECT_LAST_ATTEMPT.get(device.key, 0.0)
            if not force and now - last_attempt < 30.0:
                continue
            _AUTO_CONNECT_LAST_ATTEMPT[device.key] = now
        operation = await backend.connect(device.adapter_id, device.key)
        with _AUTO_CONNECT_LOCK:
            if operation.state == "succeeded":
                _AUTO_CONNECT_FAILURES.pop(device.key, None)
                _AUTO_CONNECT_NEXT_ATTEMPT.pop(device.key, None)
            else:
                failures = min(6, _AUTO_CONNECT_FAILURES.get(device.key, 0) + 1)
                _AUTO_CONNECT_FAILURES[device.key] = failures
                delay = min(300.0, 5.0 * (2 ** (failures - 1)))
                jitter = (sum(device.key.encode("utf-8")) % 1000) / 1000.0
                _AUTO_CONNECT_NEXT_ATTEMPT[device.key] = now + delay + jitter
        attempted = True
    return await backend.state() if attempted else state


async def _watch_reconnect_events(backend: Any) -> None:
    """Reconnect on bounded BlueZ presence/property events."""
    while True:
        try:
            async for event in backend.events():
                if event.type not in {
                    "adapter_added",
                    "adapter_changed",
                    "device_added",
                    "device_changed",
                }:
                    continue
                state = await backend.state()
                await _apply_auto_connect_async(backend, state)
                await _reconcile_audio_after_bluetooth_change(delay=0.5)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5.0)


async def _reconcile_audio_after_bluetooth_change(*, delay: float) -> None:
    """Debounce PipeWire route repair outside Bluetooth/UI request paths."""
    global _AUDIO_RECONCILE_NEXT
    now = time.monotonic()
    with _AUDIO_RECONCILE_LOCK:
        if now < _AUDIO_RECONCILE_NEXT:
            return
        _AUDIO_RECONCILE_NEXT = now + 5.0
    if delay:
        await asyncio.sleep(delay)
    try:
        from .. import audio

        await asyncio.to_thread(audio.audio_multi_output, "reconcile")
    except Exception:
        return


def _enrich_runtime_state(state: dict[str, Any]) -> None:
    settings = _load_settings()
    state["settings"] = settings
    policies = settings.get("device_auto_connect") or {}
    hid_policies = settings.get("device_hid_control") or {}
    for device in state.get("devices") or []:
        key = device.get("key")
        device["auto_connect"] = bool(
            policies.get(key, settings.get("auto_connect", True))
        )
        with _AUTO_CONNECT_LOCK:
            remaining = max(
                0.0,
                _MANUAL_DISCONNECT_UNTIL.get(str(key), 0.0) - time.monotonic(),
            )
        device["manual_disconnect_cooldown_seconds"] = round(remaining, 1)
        device["hid_control"] = bool(hid_policies.get(key, False))
    from .capabilities import pc_capability_matrix
    from .obex import get_manager
    from .hid import hid_transport_status

    state.setdefault("diagnostics", {})["pc_capability_matrix"] = pc_capability_matrix()
    state["obex"] = get_manager().snapshot()
    state.setdefault("diagnostics", {})["hid_control"] = hid_transport_status()
    _enrich_soundbar_audio_readiness(state)
    _enrich_controller_readiness(state)


def _enrich_controller_readiness(state: dict[str, Any]) -> None:
    try:
        from .. import devices

        evidence = devices.bluetooth_controller_status(state.get("devices") or [])
    except Exception as exc:
        evidence = {
            "ready": False,
            "controllers": [],
            "connected": [],
            "input_devices": [],
            "modules": {},
            "steamlink": {"available": False, "path": ""},
            "error": str(exc),
        }
    blockers = []
    if not evidence.get("connected"):
        blockers.append("No connected controller")
    if not evidence.get("input_devices"):
        blockers.append("No Linux input device detected")
    if not (evidence.get("steamlink") or {}).get("available"):
        blockers.append("Steam Link is unavailable")
    evidence["blockers"] = blockers
    diagnostics = state.setdefault("diagnostics", {})
    diagnostics["controllers"] = evidence
    diagnostics["steamlink"] = evidence.get("steamlink", {})


def _enrich_soundbar_audio_readiness(state: dict[str, Any]) -> None:
    diagnostics = state.get("diagnostics") or {}
    soundbar = diagnostics.get("soundbar")
    if not isinstance(soundbar, dict):
        return
    steps = soundbar.get("steps") or []
    by_id: dict[str, dict[str, Any]] = {}
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("id"), str):
            by_id[step["id"]] = step
    try:
        from .. import audio

        audio_state = audio.audio_state()
    except Exception as exc:
        _set_readiness_step(
            by_id,
            "pipewire_sink",
            None,
            f"Audio state unavailable: {exc}",
        )
        _set_readiness_step(
            by_id,
            "route",
            None,
            f"Audio state unavailable: {exc}",
        )
        return

    devices = audio_state.get("devices") or {}
    bt_soundbar = devices.get("bt_soundbar") or {}
    default_sink = audio_state.get("default_sink") or ""
    sink_name = bt_soundbar.get("name") or ""
    routes = audio_state.get("routes") or {}
    alexa_route = routes.get("alexa_to_bt") or {}
    sink_present = bool(bt_soundbar.get("present"))
    sink_default = bool(sink_name and default_sink == sink_name)
    route_active = bool(alexa_route.get("on"))
    _set_readiness_step(
        by_id,
        "pipewire_sink",
        sink_present,
        "PipeWire sink present" if sink_present else "PipeWire sink missing",
    )
    route_reason = "Audio route active" if route_active else (
        "Soundbar is default sink" if sink_default else "No active/default Audio route"
    )
    _set_readiness_step(by_id, "route", route_active or sink_default, route_reason)
    soundbar["ready"] = all(
        step.get("state") is True
        for step in steps
        if step.get("id") in {
            "adapter",
            "known",
            "paired",
            "trusted",
            "connected",
            "services",
            "pipewire_sink",
        }
    )


def _set_readiness_step(
    by_id: dict[str, dict[str, Any]],
    step_id: str,
    state: bool | None,
    reason: str,
) -> None:
    step = by_id.get(step_id)
    if step is None:
        return
    step["state"] = state
    step["reason"] = reason
