from typing import Any, Dict

from .common import _run

__all__ = ["audio_set_mute", "audio_set_volume", "set_global_master_volume"]


def audio_set_mute(kind: str, name: str, muted: bool) -> Dict[str, Any]:
    """Set sink/source mute with strict target validation."""
    if kind not in {"sink", "source"}:
        return {"ok": False, "error": "kind must be sink or source"}
    if not name:
        return {"ok": False, "error": "name required"}
    result = _run(["pactl", f"set-{kind}-mute", name, "1" if muted else "0"], t=5)
    return {
        "ok": result.returncode == 0,
        "kind": kind,
        "name": name,
        "muted": muted,
        "error": (result.stderr or result.stdout).strip() if result.returncode else None,
    }


def audio_set_volume(kind: str, name: str, volume: int) -> Dict[str, Any]:
    """Set volume for sink or source and sync BT AVRCP if applicable."""
    vol = max(0, min(150, volume))
    cmd = ["pactl", "set-" + kind + "-volume", name, str(vol) + "%"]
    r = _run(cmd, t=5)

    # Propagate volume to sink inputs when adjusting sink volume
    if kind == "sink":
        try:
            sinks = _run(["pactl", "list", "short", "sinks"]).stdout.splitlines()
            sink_id = None
            for line in sinks:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == name:
                    sink_id = parts[0]
                    break
            if sink_id:
                inputs = _run(["pactl", "list", "short", "sink-inputs"]).stdout.splitlines()
                for line in inputs:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == sink_id:
                        input_id = parts[0]
                        _run(["pactl", "set-sink-input-volume", input_id, str(vol) + "%"], t=3)
        except Exception:
            pass

        # Sync AVRCP if the sink is a Bluetooth device
        if name.startswith("bluez_sink.") or name.startswith("bluez_output."):
            mac_part = name.split(".")[1].replace("_", ":").upper()
            scaled_volume = int((vol / 100.0) * 127)
            scaled_volume = max(0, min(127, scaled_volume))
            from rpi_dashboard.services.bluetooth import service as bt_service
            bt_state = bt_service.bluetooth_state()
            device = next((d for d in bt_state.get("devices", []) if d.get("address") == mac_part), None)
            if device:
                bt_service.media_action("volume", value=scaled_volume, adapter_id=device.get("adapter_id"), device_key=device.get("key"))

    return {"ok": r.returncode == 0, "volume": vol}


def set_global_master_volume(percentage: int) -> Dict[str, Any]:
    """Scale all active output sinks to percentage."""
    from .state import audio_state

    vol = max(0, min(150, percentage))
    state = audio_state()
    sinks = state.get("sinks", [])
    updated = []
    for s in sinks:
        s_name = s.get("name")
        if s_name:
            res = audio_set_volume("sink", s_name, vol)
            if res.get("ok"):
                updated.append(s_name)
    return {"ok": True, "volume": vol, "updated_sinks": updated}
