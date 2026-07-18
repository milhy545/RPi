"""Synchronous service facade for the Bluetooth control center."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from .compat import legacy_state
from .bluez import BlueZDbusBackend
from .fake import FakeBluetoothBackend
from .fallback import BluetoothctlBackend
from .models import BluetoothError
from .models import BluetoothState
from .models import Operation
from .models import make_device_key

_BACKEND: Any | None = None


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


def bluetooth_state() -> dict[str, Any]:
    """Return the versioned Bluetooth state contract."""
    state = _run(get_backend().state()).to_dict()
    _enrich_soundbar_audio_readiness(state)
    return state


def devices_compat_state() -> dict[str, Any]:
    """Return legacy-compatible Bluetooth state with embedded v2 data."""
    state = legacy_state(_run(get_backend().state()))
    _enrich_soundbar_audio_readiness(state["v2"])
    return state


def start_discovery(adapter_id: str | None = None) -> dict[str, Any]:
    """Start discovery on a selected or uniquely resolved adapter."""
    state = _run(get_backend().state())
    adapter = _resolve_adapter(state, adapter_id)
    if isinstance(adapter, BluetoothError):
        return _error_response(adapter)
    operation = _run(get_backend().start_discovery(adapter.id))
    return _operation_response(operation)


def stop_discovery(adapter_id: str | None = None) -> dict[str, Any]:
    """Stop discovery on a selected or uniquely resolved adapter."""
    state = _run(get_backend().state())
    adapter = _resolve_adapter(state, adapter_id)
    if isinstance(adapter, BluetoothError):
        return _error_response(adapter)
    operation = _run(get_backend().stop_discovery(adapter.id))
    return _operation_response(operation)


def set_adapter_power(adapter_id: str | None, powered: bool) -> dict[str, Any]:
    """Set adapter power through the active backend."""
    state = _run(get_backend().state())
    adapter = _resolve_adapter(state, adapter_id)
    if isinstance(adapter, BluetoothError):
        return _error_response(adapter)
    operation = _run(get_backend().set_adapter_power(adapter.id, powered))
    return _operation_response(operation)


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
    return _operation_response(operation)


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
        if device.address == normalized and device.present
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
        output = operation.result.get("output") if operation.result else ""
        response["result"] = output or f"{operation.type} {operation.state}"
    return response


def _error_response(error: BluetoothError) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error.message,
        "code": error.code,
        "details": error.to_dict(),
    }


def _run(awaitable):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("Bluetooth sync facade must run outside an event loop")


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
