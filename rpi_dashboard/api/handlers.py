"""API handlers module for RPi-TV Dashboard.

Implements request handlers for all API endpoints.
"""

from pathlib import Path
from typing import Any, Dict
from ..services import audio, audio_dlna, audio_routing as audio_routing_service, media, player, devices, cec, system, terminal
from ..services.bluetooth import service as bluetooth_service
from ..services import return_service


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


def handle_audio_volume_global(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set global master volume for all sinks."""
    volume = _get(q, "volume", "100")
    try:
        vol = int(volume)
    except ValueError:
        return {"ok": False, "error": "volume must be integer"}
    return audio.set_global_master_volume(vol)


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


def handle_audio_mute_state(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set exact sink/source mute state."""
    kind = _get(q, "kind")
    name = _get(q, "name")
    muted = _get(q, "muted", "1") not in {"0", "false", "False", "off"}
    return audio.audio_set_mute(kind, name, muted)


def handle_audio_mute(q: Dict[str, Any]) -> Dict[str, Any]:
    """Toggle sink/source mute state."""
    kind = _get(q, "kind")
    name = _get(q, "name")
    return audio_routing_service.audio_toggle_mute(kind, name)


def handle_audio_bt(q: Dict[str, Any]) -> Dict[str, Any]:
    """Route audio to Bluetooth output."""
    return audio_routing_service.audio_route_output("bt")


def handle_audio_hdmi(q: Dict[str, Any]) -> Dict[str, Any]:
    """Route audio to HDMI output."""
    return audio_routing_service.audio_route_output("hdmi")


def handle_audio_dlna(q: Dict[str, Any]) -> Dict[str, Any]:
    """Route audio to DLNA output."""
    return audio_routing_service.audio_route_output("dlna")


def handle_audio_route_alexa_bt(q: Dict[str, Any]) -> Dict[str, Any]:
    """Control Alexa→BT routing."""
    return audio_routing_service.audio_route_alexa_bt(_get(q, "action", "status"))


def handle_audio_route_alexa_retarget(q: Dict[str, Any]) -> Dict[str, Any]:
    """Retarget Alexa routing to the current default output."""
    return audio_routing_service._retarget_alexa()


def handle_audio_route_dlnain_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Return DLNA input routing status."""
    return audio_routing_service.dlnain_status()


def handle_audio_route_dlnain_start(q: Dict[str, Any]) -> Dict[str, Any]:
    """Start DLNA input routing."""
    return audio_routing_service._dlnain_start()


def handle_audio_route_dlnain_stop(q: Dict[str, Any]) -> Dict[str, Any]:
    """Stop DLNA input routing."""
    return audio_routing_service._dlnain_stop()


def handle_audio_route_dlnain_mode(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set DLNA input routing mode."""
    return audio_routing_service.dlnain_set_mode(_get(q, "mode", "follow"))


def handle_audio_route_dlnain_target(q: Dict[str, Any]) -> Dict[str, Any]:
    """Set DLNA input routing target."""
    return audio_routing_service.dlnain_set_target(_get(q, "sink"))


def handle_keepalive(q: Dict[str, Any]) -> Dict[str, Any]:
    """Control keepalive audio streams."""
    return audio_routing_service.audio_keepalive(_get(q, "action", "status"), _get(q, "sink") or None)


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


def handle_mpv_toggle(q: Dict[str, Any]) -> Dict[str, Any]:
    """Toggle mpv pause state."""
    return player.mpv_toggle()


def handle_mpv_seekabs(q: Dict[str, Any]) -> Dict[str, Any]:
    """Seek mpv to an absolute position."""
    pos = _get(q, "pos", "0")
    try:
        position = float(pos)
    except ValueError:
        return {"ok": False, "error": "pos must be number"}
    return player.mpv_seek_absolute(position)


def handle_mpv_vol(q: Dict[str, Any]) -> Dict[str, Any]:
    """Adjust mpv volume by a relative delta."""
    delta = _get(q, "d", "0")
    try:
        amount = int(delta)
    except ValueError:
        return {"ok": False, "error": "d must be integer"}
    return player.mpv_volume_delta(amount)


def handle_mpv_memory(q: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch stored mpv resume memory for a URL."""
    url = _get(q, "url")
    if not url:
        return {"ok": False, "error": "url required"}
    return {"ok": True, "memory": player.mpv_memory_for_url(url)}


def handle_mpv_memory_clear(q: Dict[str, Any]) -> Dict[str, Any]:
    """Clear stored mpv resume memory for a URL."""
    url = _get(q, "url")
    if not url:
        return {"ok": False, "error": "url required"}
    return {"ok": True, "cleared": player.mpv_memory_clear_for_url(url)}


def handle_mpv_memory_save(q: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the current mpv resume state."""
    if not player.mpv_ipc_socket_live():
        return {"ok": True, "memory": "mpv not running"}
    memory = player.save_mpv_resume_memory()
    return {"ok": True, "memory": memory}


# ─── Device Handlers ─────────────────────────────────────────────────

def handle_devices_state(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get devices state."""
    return devices.devices_state()


def handle_devices_legacy(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get the legacy device summary."""
    return devices.devices_legacy_summary()


def handle_devices_bt_scan(q: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy Bluetooth scan for the Devices tab."""
    seconds = _get(q, "seconds", "5")
    try:
        sec = int(seconds)
    except ValueError:
        sec = 5
    return devices.bluetooth_scan_devices(sec)


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
    raw_seconds = _get(q, "seconds", "")
    try:
        seconds = int(raw_seconds) if raw_seconds else None
    except ValueError:
        return {"ok": False, "error": "seconds must be an integer", "code": "unsupported"}
    if action == "start":
        return bluetooth_service.start_discovery(adapter_id or None, seconds)
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


def handle_bt_device_hid(q: Dict[str, Any]) -> Dict[str, Any]:
    """Enable or immediately disable optional trusted-device HID control."""
    enabled = _get(q, "enabled", "0").lower() in {"1", "true", "on", "yes"}
    return bluetooth_service.set_device_hid_control(
        _get(q, "adapter_id") or None,
        _get(q, "device_key") or None,
        enabled,
    )


def handle_bt_reset(q: Dict[str, Any]) -> Dict[str, Any]:
    """Unpair all devices and reset local Bluetooth state."""
    return bluetooth_service.reset_all_devices()


def handle_bt_capabilities(q: Dict[str, Any]) -> Dict[str, Any]:
    """Return adapter hardware recommendations and topology capabilities."""
    return bluetooth_service.get_adapter_recommendations()


def handle_bt_phone_role(q: Dict[str, Any]) -> Dict[str, Any]:
    """Configure a phone device as an A2DP audio source or sink."""
    role = _get(q, "role", "source").lower()
    return bluetooth_service.set_phone_role(
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=_get(q, "mac") or None,
        role=role,
    )


def handle_bt_device_action(q: Dict[str, Any]) -> Dict[str, Any]:
    """Run an adapter-aware Bluetooth device action."""
    action = _get(q, "action")
    if not action:
        return {"ok": False, "error": "action required", "code": "unsupported"}
    if action == "pair":
        return bluetooth_service.start_pairing(
            adapter_id=_get(q, "adapter_id") or None,
            device_key=_get(q, "device_key") or None,
            mac=_get(q, "mac") or None,
        )
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


def handle_bt_diagnostics(q: Dict[str, Any]) -> Dict[str, Any]:
    """Collect bounded read-only Bluetooth failure and resource diagnostics."""
    return bluetooth_service.bluetooth_diagnostics()


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

    action = _get(q, "action")
    result = bluetooth_service.media_action(
        action,
        value=value,
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=_get(q, "mac") or None,
    )

    # Sync PipeWire volume if AVRCP volume changes
    if action == "volume" and value is not None and result.get("ok"):
        mac = _get(q, "mac")
        if not mac:
            device_key = _get(q, "device_key")
            if device_key and "/" in device_key:
                mac = device_key.split("/")[1]
        if mac:
            sink_name = f"bluez_output.{mac.replace(':', '_')}.a2dp_sink"
            pw_vol = int((value / 127.0) * 100)
            pw_vol = max(0, min(150, pw_vol))
            audio.audio_set_volume("sink", sink_name, pw_vol)

    return result


def handle_bt_pairing(q: Dict[str, Any]) -> Dict[str, Any]:
    """Start, inspect, answer, or cancel one explicit pairing lifecycle."""
    action = _get(q, "action", "status")
    operation_id = _get(q, "operation_id")
    if action == "start":
        return bluetooth_service.start_pairing(
            adapter_id=_get(q, "adapter_id") or None,
            device_key=_get(q, "device_key") or None,
            mac=_get(q, "mac") or None,
        )
    if action == "status":
        return bluetooth_service.pairing_status(operation_id)
    if action == "respond":
        accepted = _get(q, "accepted", "0").lower() in {"1", "true", "yes", "on"}
        return bluetooth_service.respond_pairing(
            operation_id,
            accepted,
            _get(q, "value") or None,
        )
    if action == "cancel":
        return bluetooth_service.cancel_pairing(operation_id)
    return {"ok": False, "code": "unsupported", "error": "unsupported pairing action"}


def handle_bt_pair(q: Dict[str, Any]) -> Dict[str, Any]:
    """Start the non-blocking pairing lifecycle for legacy callers."""
    return bluetooth_service.start_pairing(
        adapter_id=_get(q, "adapter_id") or None,
        device_key=_get(q, "device_key") or None,
        mac=_get(q, "mac") or None,
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


def handle_cec_send(q: Dict[str, Any]) -> Dict[str, Any]:
    """Send a raw CEC command."""
    cmd = _get(q, "c")
    if not cmd:
        return {"ok": False, "error": "no cmd"}
    return cec.cec_send(cmd)


def handle_cec_key(q: Dict[str, Any]) -> Dict[str, Any]:
    """Send a CEC key command."""
    key = _get(q, "k")
    if not key:
        return {"ok": False, "error": "no key"}
    return cec.cec_key(key)


def handle_cec_in(q: Dict[str, Any]) -> Dict[str, Any]:
    """Switch the CEC input."""
    return cec.cec_input(_get(q, "n", "1"))


def handle_cec_bridge_start(q: Dict[str, Any]) -> Dict[str, Any]:
    """Start the legacy CEC bridge."""
    return cec.cec_bridge_start()


def handle_cec_bridge_stop(q: Dict[str, Any]) -> Dict[str, Any]:
    """Stop the legacy CEC bridge."""
    return cec.cec_bridge_stop()


def handle_cec_bridge_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get the legacy CEC bridge status."""
    return cec.cec_bridge_status()


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


def handle_system_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get system service affinity status."""
    return system.get_system_status()


def handle_restart_mpv(q: Dict[str, Any]) -> Dict[str, Any]:
    """Restart mpv."""
    result = system.restart_mpv()
    return {**result, "out": result.get("message", "mpv stopped")}


def handle_restart_dashboard(q: Dict[str, Any]) -> Dict[str, Any]:
    """Restart dashboard."""
    result = system.restart_dashboard()
    return {**result, "out": result.get("message", "Dashboard restarting...")}


def handle_restart_rpi(q: Dict[str, Any]) -> Dict[str, Any]:
    """Restart RPi."""
    result = system.restart_rpi()
    return {**result, "out": result.get("message", "Rebooting...")}


def handle_system_hw_stats(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get hardware stats."""
    return system.get_hw_stats()


def handle_system_https_info(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get HTTPS info."""
    return system.get_https_info()


def handle_network_info(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get network information."""
    return system.get_network_info()


def handle_network_tailscale(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get Tailscale status."""
    return system.get_tailscale_status()


def handle_system_logs(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get system logs from journalctl."""
    lines = int(_get(q, "lines", "100"))
    service = _get(q, "service", "")
    return system.get_service_logs(service, lines)


def handle_youtube_cookie_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get YouTube cookie status."""
    return media.youtube_cookie_status()


def handle_youtube_age_check(q: Dict[str, Any]) -> Dict[str, Any]:
    """Check YouTube age/cookie status for a URL."""
    return media.youtube_age_check(_get(q, "url"))


def handle_media_preview(q: Dict[str, Any]) -> Dict[str, Any]:
    """Preview a media URL."""
    from ..services.media import media_preview

    return media_preview(_get(q, "url"))


def handle_dlna_select(q: Dict[str, Any]) -> Dict[str, Any]:
    """Select a DLNA renderer."""
    return audio_dlna.audio_select_dlna_renderer(_get(q, "name"), _get(q, "location"), _get(q, "usn"))


def handle_dlna_connect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Connect DLNA audio."""
    return audio_dlna.audio_connect_dlna()


def handle_dlna_disconnect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Disconnect DLNA audio."""
    return audio_dlna.audio_disconnect_dlna()


def handle_dlna_scan(q: Dict[str, Any]) -> Dict[str, Any]:
    """Scan for DLNA renderers."""
    return audio_dlna.dlna_scan()


def handle_dlna_renderer_status(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get DLNA renderer status."""
    return audio_dlna.dlna_renderer_status()


def handle_dlna_renderer_start(q: Dict[str, Any]) -> Dict[str, Any]:
    """Start DLNA renderer."""
    return audio_dlna.dlna_renderer_start()


def handle_dlna_renderer_stop(q: Dict[str, Any]) -> Dict[str, Any]:
    """Stop DLNA renderer."""
    return audio_dlna.dlna_renderer_stop()


# ─── Return Service Handlers ─────────────────────────────────────────

def handle_return_config_get(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get return service configuration."""
    return {"ok": True, "config": return_service.get_config()}


def handle_return_config_set(q: Dict[str, Any]) -> Dict[str, Any]:
    """Update return service configuration."""
    try:
        # Support both form data and JSON body
        if hasattr(q, 'get'):
            updates = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
        else:
            updates = q
        config = return_service.update_config(updates)
        return {"ok": True, "config": config}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_return_last(q: Dict[str, Any]) -> Dict[str, Any]:
    """Get last return event."""
    return {"ok": True, "last_return": return_service.get_last_return()}


def handle_ha_config(q: Dict[str, Any]) -> Dict[str, Any]:
    """Return Home Assistant YAML integration configuration."""
    yaml_path = Path(__file__).resolve().parents[1] / "ha_configuration.yaml"
    if yaml_path.exists():
        return {"ok": True, "yaml": yaml_path.read_text()}
    return {"ok": False, "error": "ha_configuration.yaml not found"}


# ─── POST Handlers ─────────────────────────────────────────────────

def handle_post_report(q: Dict[str, Any]) -> Dict[str, Any]:
    """Handle bug/feature report submission via POST /report."""
    import time as _time

    report = q.get("_body", {})
    if not isinstance(report, dict):
        return {"ok": False, "error": "Invalid JSON"}
    if report.get("type") not in ("bug", "feature"):
        return {"ok": False, "error": "type must be 'bug' or 'feature'"}
    desc = report.get("description", "")
    if not isinstance(desc, str) or not desc.strip():
        return {"ok": False, "error": "description must be non-empty"}

    from pathlib import Path as _Path
    import json as _json

    reports_dir = _Path(__file__).resolve().parents[2] / "reports"
    reports_dir.mkdir(exist_ok=True)
    ts = int(_time.time())
    filename = f"report_{ts}_{report['type']}.json"
    filepath = reports_dir / filename
    filepath.write_text(_json.dumps({**report, "timestamp": ts}, indent=2))
    return {"ok": True, "file": filename}


def handle_post_return(q: Dict[str, Any]) -> Dict[str, Any]:
    """Handle return to dashboard via POST /return."""
    body = q.get("_body", {})
    reason = body.get("reason", "unknown") if isinstance(body, dict) else "unknown"
    source = body.get("source", "webapi") if isinstance(body, dict) else "webapi"
    ok = return_service.return_to_dashboard(reason, source)
    return {"ok": ok}


def handle_post_wifi_connect(q: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Wi-Fi connection via POST /wifi/connect."""
    import webserver as _ws
    body = q.get("_body", {})
    if isinstance(body, dict):
        ssid = body.get("ssid", "").strip()
        password = body.get("password", "")
    else:
        ssid = ""
        password = ""
    if not ssid:
        return {"ok": False, "error": "ssid required"}
    return _ws.wifi_connect(ssid, password)

