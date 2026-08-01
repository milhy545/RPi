import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


from .common import _run, _pactl_lines, MULTI_OUTPUT_SINK, MULTI_OUTPUT_STATE_FILE, _multi_output_lock

from .matrix import _find_loopbacks, _find_loopback, _start_loopback, _stop_loopback, _find_multi_output_module

def _bluetooth_output_sinks() -> List[str]:
    """Return physical output sinks (Bluetooth, HDMI, USB) currently exposed by PipeWire."""
    valid_prefixes = ("bluez_output.", "alsa_output.platform-3f902000.hdmi", "alsa_output.platform-hdmi", "alsa_output.usb-")
    return [
        item["name"]
        for item in _pactl_lines("sinks")
        if item["name"] != MULTI_OUTPUT_SINK and any(item["name"].startswith(p) for p in valid_prefixes)
    ]

def _bluetooth_input_sources() -> List[str]:
    """Return active Bluetooth audio-input sources, excluding monitor nodes."""
    return [
        item["name"]
        for item in _pactl_lines("sources")
        if item["name"].startswith("bluez_input.") and not item["name"].endswith(".monitor")
    ]

def _multi_output_status() -> Dict[str, Any]:
    """Return the real PipeWire state of the dashboard Bluetooth combine sink."""
    from .state import _get_default_sink
    module = _find_multi_output_module()
    sink_names = [item["name"] for item in _pactl_lines("sinks")]
    available_sinks = _bluetooth_output_sinks()
    input_sources = _bluetooth_input_sources()
    routed_inputs = [
        str(loopback["source"])
        for loopback in _find_loopbacks()
        if loopback.get("sink") == MULTI_OUTPUT_SINK
        and str(loopback.get("source", "")).startswith("bluez_input.")
    ]
    active = bool(module and MULTI_OUTPUT_SINK in sink_names)
    slaves = module["slaves"] if module else []
    stale_slaves = [name for name in slaves if name not in available_sinks]
    healthy = active and len(slaves) >= 2 and not stale_slaves
    return {
        "ok": True,
        "active": active,
        "module_id": module["id"] if module else None,
        "sink": MULTI_OUTPUT_SINK,
        "slaves": slaves,
        "healthy": healthy,
        "stale_slaves": stale_slaves,
        "available_sinks": available_sinks,
        "input_sources": input_sources,
        "routed_inputs": routed_inputs,
        "unrouted_inputs": [source for source in input_sources if source not in routed_inputs],
        "input_pending": active and not input_sources,
        "default_sink": _get_default_sink(),
        "intent": _load_multi_output_intent(),
    }

def _load_multi_output_intent() -> Dict[str, Any]:
    """Load persisted user intent; infer legacy active module once for migration."""
    try:
        data = json.loads(Path(MULTI_OUTPUT_STATE_FILE).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                "enabled": bool(data.get("enabled")),
                "slaves": [str(name) for name in data.get("slaves") or []],
            }
    except (OSError, ValueError, TypeError):
        pass
    module = _find_multi_output_module()
    return {
        "enabled": bool(module),
        "slaves": list(module.get("slaves", [])) if module else [],
        "inferred": bool(module),
    }

def _save_multi_output_intent(enabled: bool, slaves: List[str]) -> None:
    path = Path(MULTI_OUTPUT_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"enabled": bool(enabled), "slaves": list(slaves)}, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)

def _physical_fallback_sink() -> Optional[str]:
    """Choose a real sink before unloading an unavailable virtual default."""
    return next(
        (
            item["name"]
            for item in _pactl_lines("sinks")
            if item["name"] != MULTI_OUTPUT_SINK and not item["name"].startswith("bluez_output.")
        ),
        None,
    )

def _attach_bluetooth_inputs() -> Tuple[List[str], List[str]]:
    """Attach active phone/PC A2DP input sources to the combine sink."""
    attached = []
    failed = []
    for source in _bluetooth_input_sources():
        if _find_loopback(source, MULTI_OUTPUT_SINK):
            attached.append(source)
            continue
        if _start_loopback(source, MULTI_OUTPUT_SINK) is None:
            failed.append(source)
        else:
            attached.append(source)
    return attached, failed

def audio_multi_output(action: str = "status", sinks: Optional[List[str]] = None) -> Dict[str, Any]:
    """Serialize reads and mutations of the dashboard-owned combine sink."""
    with _multi_output_lock:
        return _audio_multi_output(action, sinks)

def _audio_multi_output(action: str = "status", sinks: Optional[List[str]] = None) -> Dict[str, Any]:
    """Manage one combined sink for all selected Bluetooth output devices."""
    from .state import _get_default_sink
    action = (action or "status").strip().lower()
    if action == "status":
        return _multi_output_status()
    if action not in {"start", "sync", "stop", "reconcile"}:
        return {"ok": False, "error": "action must be status, start, sync, stop, or reconcile"}

    module = _find_multi_output_module()
    available = _bluetooth_output_sinks()

    if action == "reconcile":
        intent = _load_multi_output_intent()
        if not intent.get("enabled"):
            return {**_multi_output_status(), "reconciled": False, "reason": "multi-output disabled"}
        requested = [name for name in intent.get("slaves") or [] if name in available]
        if len(requested) >= 2:
            result = audio_multi_output("start", requested)
            result.update({"reconciled": True, "reason": "requested outputs available"})
            return result
        for loopback in _find_loopbacks():
            if loopback.get("sink") == MULTI_OUTPUT_SINK:
                _stop_loopback(str(loopback["id"]))
        fallback = available[0] if available else _physical_fallback_sink()
        if fallback and _get_default_sink() == MULTI_OUTPUT_SINK:
            _run(["pactl", "set-default-sink", fallback], t=5)
        if module:
            _run(["pactl", "unload-module", str(module["id"])], t=5)
        result = _multi_output_status()
        result.update(
            {
                "reconciled": True,
                "waiting_for_outputs": True,
                "fallback_sink": fallback,
                "reason": "fewer than two requested Bluetooth outputs are available",
                "intent": intent,
            }
        )
        return result

    if action == "stop":
        for loopback in _find_loopbacks():
            if loopback.get("sink") == MULTI_OUTPUT_SINK:
                _stop_loopback(str(loopback["id"]))
        fallback = next((name for name in available if name in (module or {}).get("slaves", [])), None)
        fallback = fallback or (available[0] if available else _physical_fallback_sink())
        if fallback:
            set_default = _run(["pactl", "set-default-sink", fallback], t=5)
            if set_default.returncode != 0:
                return {"ok": False, "error": (set_default.stderr or "failed to set fallback sink").strip()}
        if module:
            unloaded = _run(["pactl", "unload-module", str(module["id"])], t=5)
            if unloaded.returncode != 0:
                return {"ok": False, "error": (unloaded.stderr or "failed to unload combine sink").strip()}
        _save_multi_output_intent(False, [])
        result = _multi_output_status()
        result.update({"fallback_sink": fallback})
        return result

    requested = [name.strip() for name in (sinks or available) if name.strip()]
    requested = list(dict.fromkeys(requested))
    missing = [name for name in requested if name not in available]
    if missing:
        return {"ok": False, "error": "requested Bluetooth sinks are not available", "missing": missing}
    if len(requested) < 2:
        return {
            "ok": False,
            "error": "at least two connected Bluetooth output sinks are required",
            "available_sinks": available,
        }

    existing_matches = bool(module and set(module["slaves"]) == set(requested))
    if module and not existing_matches:
        for loopback in _find_loopbacks():
            if loopback.get("sink") == MULTI_OUTPUT_SINK:
                _stop_loopback(str(loopback["id"]))
        unloaded = _run(["pactl", "unload-module", str(module["id"])], t=5)
        if unloaded.returncode != 0:
            return {"ok": False, "error": (unloaded.stderr or "failed to replace combine sink").strip()}
        module = None

    created = False
    if not module:
        loaded = _run(
            [
                "pactl",
                "load-module",
                "module-combine-sink",
                f"sink_name={MULTI_OUTPUT_SINK}",
                f"slaves={','.join(requested)}",
                "adjust_time=1",
            ],
            t=10,
        )
        if loaded.returncode != 0:
            return {"ok": False, "error": (loaded.stderr or loaded.stdout or "failed to create combine sink").strip()}
        created = True

    set_default = _run(["pactl", "set-default-sink", MULTI_OUTPUT_SINK], t=5)
    if set_default.returncode != 0:
        if created:
            created_module = _find_multi_output_module()
            if created_module:
                _run(["pactl", "unload-module", str(created_module["id"])], t=5)
        return {"ok": False, "error": (set_default.stderr or "failed to select combine sink").strip()}

    attached, failed = _attach_bluetooth_inputs()
    result = _multi_output_status()
    if result.get("active"):
        _save_multi_output_intent(True, requested)
    result.update({"created": created, "attached_inputs": attached})
    if failed:
        result.update({"ok": False, "partial": True, "error": "failed to attach Bluetooth inputs", "failed_inputs": failed})
    return result

__all__ = [
    "_bluetooth_output_sinks",
    "_bluetooth_input_sources",
    "_multi_output_status",
    "_load_multi_output_intent",
    "_save_multi_output_intent",
    "_physical_fallback_sink",
    "_attach_bluetooth_inputs",
    "audio_multi_output",
    "_audio_multi_output"
]

