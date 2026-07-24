"""API handlers module for RPi-TV Dashboard.

Implements request handlers for all API endpoints.
"""

from typing import Any, Dict
from ..services import audio, player, devices, cec, system, terminal
from ..services.bluetooth import service as bluetooth_service


def _get(q: dict, name: str, default: str = "") -> str:
    """Get single query parameter safely."""
    return (q.get(name) or [default])[0].strip()


# ─── Audio Handlers ──────────────────────────────────────────────────

def handle_audio_state(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get audio state."""
    force = _get(q, "force", "0") == "1"
    return audio.audio_state(force=force)


def handle_audio_default_sink(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set default audio sink."""
    name = _get(q, "name")
    if not name:
        return {"ok": False, "error": "name required"}
    return audio.audio_set_default(name)


def handle_audio_volume(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set audio volume."""
    kind = _get(q, "kind", "sink")
    name = _get(q, "name")
    volume = _get(q, "volume", "100")
    if not name:
        return {"ok": False, "error": "name required"}
    try:
        vol = int(volume)
    except ValueError:
        return {"ok": False, "error": "volume must be integer"}
    return audio.audio_set_volume(kind, name, vol)


def handle_audio_matrix(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get audio matrix."""
    return audio.get_audio_matrix()


def handle_audio_matrix_link(q: Dict[str, Any]) -> Dict[str, Any]:
    """Link/unlink audio nodes."""
    out_n = _get(q, "out")
    in_n = _get(q, "in")
    state = _get(q, "state", "1")
    if not out_n or not in_n:
        return {"ok": False, "error": "out and in required"}
    return audio.audio_matrix_link(out_n, in_n, state)


def handle_audio_latency(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set audio latency."""
    key = _get(q, "key")
    value = _get(q, "value", "0")
    if not key:
        return {"ok": False, "error": "key required"}
    try:
        val = int(value)
    except ValueError:
        return {"ok": False, "error": "value must be integer"}
    return audio.audio_set_latency(key, val)


def handle_audio_multi_output(q: Dict[str, Any]) -> Dict[str, Any]:
    """Manage the shared PipeWire Bluetooth multi-output route."""
    action = _get(q, "action", "status")
    sink_values = _get(q, "sinks")
    sinks = [name.strip() for name in sink_values.split(",") if name.strip()] or None
    return audio.audio_multi_output(action, sinks)


def handle_audio_bluetooth_profiles(q: Dict[str, Any]) -> Dict[str, Any]:
    """List or select negotiated PipeWire Bluetooth card profiles."""
    card = _get(q, "card")
    profile = _get(q, "profile")
    if not card and not profile:
        return audio.bluetooth_audio_profiles()
    if not card or not profile:
        return {"ok": False, "error": "card and profile are required"}
    return audio.audio_set_bluetooth_profile(card, profile)


def handle_audio_mute(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set explicit sink/source mute state."""
    kind = _get(q, "kind")
    name = _get(q, "name")
    muted = _get(q, "muted", "1") not in {"0", "false", "False", "off"}
    return audio.audio_set_mute(kind, name, muted)


# ─── Player Handlers ─────────────────────────────────────────────────

def handle_mpv_play(q: Dict[str, Any]) -> Dict[str, Any]:
    """Start mpv playback."""
    url = _get(q, "url")
    quality = _get(q, "q")
    resume = _get(q, "resume", "0") not in ("0", "", "false", "False")
    if not url:
        return {"ok": False, "error": "url required"}
    return player.mpv_start(url, quality or None, resume)


def handle_mpv_stop(q: Dict[str, Any]) -> Dict[str, Any]:
    """Stop mpv playback."""
    return player.mpv_stop()


def handle_mpv_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get mpv status."""
    return player.mpv_st()


def handle_mpv_seek(q: Dict[str, Any]) -> Dict[str, Any]:
    """Seek in mpv."""
    position = _get(q, "position", "0")
    try:
        pos = float(position)
    except ValueError:
        return {"ok": False, "error": "position must be number"}
    return player.mpv_seek(pos)


def handle_mpv_volume(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set mpv volume."""
    volume = _get(q, "volume", "100")
    try:
        vol = int(volume)
    except ValueError:
        return {"ok": False, "error": "volume must be integer"}
    return player.mpv_volume(vol)


# ─── Device Handlers ─────────────────────────────────────────────────

def handle_devices_state(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get devices state."""
    return devices.devices_state()


def handle_bt_scan(q: Dict[str, Any]) -> Dict[str, Any]:
    """Scan Bluetooth devices."""
    adapter_id = _get(q, "adapter_id")
    if adapter_id:
        return bluetooth_service.start_discovery(adapter_id)
    seconds = _get(q, "seconds", "5")
    try:
        sec = int(seconds)
    except ValueError:
        sec = 5
    return devices.bluetooth_scan_devices(sec)


def handle_bt_controller_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get Bluetooth controller readiness."""
    return {"ok": True, "controller": devices.bluetooth_controller_status()}


def handle_bt_state(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get adapter-aware Bluetooth state."""
    return bluetooth_service.bluetooth_state()


def handle_bt_discovery(q: Dict[str, Any]) -> Dict[str, Any]:
    """Start or stop adapter-aware discovery."""
    adapter_id = _get(q, "adapter_id")
    action = _get(q, "action", "start")
    if action == "start":
        return bluetooth_service.start_discovery(adapter_id or None)
    if action == "stop":
        return bluetooth_service.stop_discovery(adapter_id or None)
    return {"ok": False, "error": "action must be start or stop", "code": "unsupported"}


def handle_bt_adapter_power(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set adapter power."""
    adapter_id = _get(q, "adapter_id")
    powered = _get(q, "powered", "1").lower() not in {"0", "false", "off", "no"}
    return bluetooth_service.set_adapter_power(adapter_id or None, powered)


def handle_bt_discoverable(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set adapter discoverability."""
    adapter_id = _get(q, "adapter_id")
    discoverable = _get(q, "discoverable", "1").lower() not in {"0", "false", "off", "no"}
    raw_timeout = _get(q, "timeout", "")
    try:
        timeout = int(raw_timeout) if raw_timeout else None
    except ValueError:
        return {"ok": False, "error": "timeout must be an integer", "code": "unsupported"}
    return bluetooth_service.set_adapter_discoverable(
        adapter_id or None,
        discoverable,
        timeout,
    )


def handle_bt_settings(q: Dict[str, Any]) -> Dict[str, Any]:
    """Persist dashboard-owned Bluetooth settings."""
    raw_auto_connect = _get(q, "auto_connect", "")
    auto_connect = None
    if raw_auto_connect:
        auto_connect = raw_auto_connect.lower() not in {"0", "false", "off", "no"}
    raw_timeout = _get(q, "discoverable_timeout", "")
    try:
        timeout = int(raw_timeout) if raw_timeout else None
    except ValueError:
        return {
            "ok": False,
            "error": "discoverable_timeout must be an integer",
            "code": "unsupported",
        }
    return bluetooth_service.update_settings(
        auto_connect=auto_connect,
        discoverable_timeout=timeout,
        scan_mode=_get(q, "scan_mode", "") or None,
    )


def handle_bt_device_autoconnect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set the adapter-scoped reconnect policy for one paired device."""
    enabled = _get(q, "enabled", "1").lower() not in {"0", "false", "off", "no"}
    return bluetooth_service.set_device_auto_connect(
        _get(q, "adapter_id") or None,
        _get(q, "device_key") or None,
        enabled,
    )


def handle_bt_device_action(q: Dict[str, Any]) -> Dict[str, Any]:
    """Run an adapter-aware Bluetooth device action."""
    action = _get(q, "action")
    if not action:
        return {"ok": False, "error": "action required", "code": "unsupported"}
    return bluetooth_service.device_action(
        action,
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=_get(q, "mac") or None,
    )


def handle_bt_device_profile(q: Dict[str, Any]) -> Dict[str, Any]:
    """Connect or disconnect one profile advertised by a Bluetooth device."""
    return bluetooth_service.device_profile_action(
        _get(q, "action"),
        _get(q, "profile_uuid"),
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=_get(q, "mac") or None,
    )


def handle_bt_transfers(q: Dict[str, Any]) -> Dict[str, Any]:
    """Return OBEX availability and bounded transfer progress."""
    return bluetooth_service.obex_state()


def handle_bt_files(q: Dict[str, Any]) -> Dict[str, Any]:
    """List safe outbound candidates from the RPi Downloads directory."""
    return bluetooth_service.download_files()


def handle_bt_file_send(q: Dict[str, Any]) -> Dict[str, Any]:
    """Send one file from Downloads through adapter-scoped Object Push."""
    return bluetooth_service.send_file(
        _get(q, "path"),
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=_get(q, "mac") or None,
    )


def handle_bt_file_cancel(q: Dict[str, Any]) -> Dict[str, Any]:
    """Cancel one active OBEX transfer."""
    return bluetooth_service.cancel_file_transfer(_get(q, "transfer_id"))


def handle_bt_operation(q: Dict[str, Any]) -> Dict[str, Any]:
    """Look up or cancel one Bluetooth backend operation."""
    action = _get(q, "action", "status")
    operation_id = _get(q, "operation_id")
    if action == "status":
        return bluetooth_service.operation_status(operation_id)
    if action == "cancel":
        return bluetooth_service.cancel_operation(operation_id)
    return {"ok": False, "code": "unsupported", "error": "action must be status or cancel"}


def handle_bt_media(q: Dict[str, Any]) -> Dict[str, Any]:
    """Control an advertised BlueZ AVRCP player or transport volume."""
    value_text = _get(q, "value")
    try:
        value = int(value_text) if value_text else None
    except ValueError:
        return {"ok": False, "code": "unsupported", "error": "value must be an integer"}
    return bluetooth_service.media_action(
        _get(q, "action"),
        value=value,
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=_get(q, "mac") or None,
    )


def handle_bt_pair(q: Dict[str, Any]) -> Dict[str, Any]:
    """Pair Bluetooth device."""
    mac = _get(q, "mac")
    return bluetooth_service.device_action(
        "pair",
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=mac or None,
    )


def handle_bt_trust(q: Dict[str, Any]) -> Dict[str, Any]:
    """Trust Bluetooth device."""
    mac = _get(q, "mac")
    return bluetooth_service.device_action(
        "trust",
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=mac or None,
    )


def handle_bt_connect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Connect Bluetooth device."""
    mac = _get(q, "mac")
    return bluetooth_service.device_action(
        "connect",
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=mac or None,
    )


def handle_bt_disconnect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Disconnect Bluetooth device."""
    mac = _get(q, "mac")
    return bluetooth_service.device_action(
        "disconnect",
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=mac or None,
    )


def handle_bt_remove(q: Dict[str, Any]) -> Dict[str, Any]:
    """Remove Bluetooth device."""
    mac = _get(q, "mac")
    return bluetooth_service.device_action(
        "remove",
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=mac or None,
    )


def handle_wifi_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get WiFi status."""
    return devices.wifi_status()


def handle_wifi_scan(q: Dict[str, Any]) -> Dict[str, Any]:
    """Scan WiFi networks."""
    return devices.wifi_scan()


def handle_wifi_connect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Connect to WiFi."""
    ssid = _get(q, "ssid")
    password = _get(q, "password")
    if not ssid:
        return {"ok": False, "error": "ssid required"}
    return devices.wifi_connect(ssid, password)


# ─── CEC Handlers ────────────────────────────────────────────────────

def handle_cec_scan(q: Dict[str, Any]) -> Dict[str, Any]:
    """Scan CEC devices."""
    return cec.cec_scan()


def handle_cec_power(q: Dict[str, Any]) -> Dict[str, Any]:
    """CEC power control."""
    action = _get(q, "action", "on")
    if action == "on":
        return cec.cec_power_on()
    elif action == "off":
        return cec.cec_power_off()
    return {"ok": False, "error": "action must be on or off"}


def handle_cec_nav(q: Dict[str, Any]) -> Dict[str, Any]:
    """CEC navigation."""
    action = _get(q, "action")
    actions = {
        "up": cec.cec_up,
        "down": cec.cec_down,
        "left": cec.cec_left,
        "right": cec.cec_right,
        "select": cec.cec_select,
        "back": cec.cec_back,
        "menu": cec.cec_menu,
    }
    handler = actions.get(action)
    if handler:
        return handler()
    return {"ok": False, "error": f"unknown action: {action}"}


def handle_cec_vol(q: Dict[str, Any]) -> Dict[str, Any]:
    """CEC volume control."""
    action = _get(q, "action")
    if action == "up":
        return cec.cec_volume_up()
    elif action == "down":
        return cec.cec_volume_down()
    elif action == "mute":
        return cec.cec_mute()
    return {"ok": False, "error": "action must be up, down, or mute"}


def handle_cec_input(q: Dict[str, Any]) -> Dict[str, Any]:
    """CEC input switching."""
    input_num = _get(q, "input", "1")
    if input_num == "1":
        return cec.cec_input_hdmi1()
    elif input_num == "2":
        return cec.cec_input_hdmi2()
    elif input_num == "3":
        return cec.cec_input_hdmi3()
    return {"ok": False, "error": "input must be 1, 2, or 3"}


# ─── Terminal Handlers ───────────────────────────────────────────────

def handle_terminal_connect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Connect to terminal."""
    return terminal.terminal_connect()


def handle_terminal_disconnect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Disconnect from terminal."""
    return terminal.terminal_disconnect()


# ─── System Handlers ─────────────────────────────────────────────────

def handle_system_stats(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get system stats."""
    return system.get_system_stats()


def handle_restart_mpv(q: Dict[str, Any]) -> Dict[str, Any]:
    """Restart mpv."""
    return system.restart_mpv()


def handle_restart_dashboard(q: Dict[str, Any]) -> Dict[str, Any]:
    """Restart dashboard."""
    return system.restart_dashboard()


def handle_restart_rpi(q: Dict[str, Any]) -> Dict[str, Any]:
    """Restart RPi."""
    return system.restart_rpi()
