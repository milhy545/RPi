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
_AUTO_CONNECT_LAST_ATTEMPT: dict[str, float] = {}
_AUTO_CONNECT_FAILURES: dict[str, int] = {}
_AUTO_CONNECT_NEXT_ATTEMPT: dict[str, float] = {}
_MANUAL_DISCONNECT_UNTIL: dict[str, float] = {}
_MANUAL_DISCONNECT_COOLDOWN = 60.0
_DEFAULT_SETTINGS: dict[str, Any] = {
    "auto_connect": False,
    "discoverable_timeout": 120,
    "scan_mode": "balanced",
    "device_auto_connect": {},
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
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5.0)


def _enrich_runtime_state(state: dict[str, Any]) -> None:
    state["settings"] = _load_settings()
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
