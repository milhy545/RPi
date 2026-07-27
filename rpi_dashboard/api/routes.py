"""API routes module for RPi-TV Dashboard.

Maps URL paths to handler functions.
"""

import time
from typing import Callable, Dict, Optional
from .handlers import (
    handle_audio_state,
    handle_audio_default_sink,
    handle_audio_volume,
    handle_audio_matrix,
    handle_audio_matrix_link,
    handle_audio_latency,
    handle_audio_multi_output,
    handle_audio_bluetooth_profiles,
    handle_audio_mute_state,
    handle_audio_mute,
    handle_audio_bt,
    handle_audio_hdmi,
    handle_audio_dlna,
    handle_audio_route_alexa_bt,
    handle_audio_route_alexa_retarget,
    handle_audio_route_dlnain_status,
    handle_audio_route_dlnain_start,
    handle_audio_route_dlnain_stop,
    handle_audio_route_dlnain_mode,
    handle_audio_route_dlnain_target,
    handle_keepalive,
    handle_mpv_play,
    handle_mpv_stop,
    handle_mpv_status,
    handle_mpv_seek,
    handle_mpv_volume,
    handle_mpv_toggle,
    handle_mpv_seekabs,
    handle_mpv_vol,
    handle_mpv_memory,
    handle_mpv_memory_clear,
    handle_mpv_memory_save,
    handle_devices_state,
    handle_bt_scan,
    handle_bt_state,
    handle_bt_discovery,
    handle_bt_adapter_power,
    handle_bt_discoverable,
    handle_bt_settings,
    handle_bt_device_action,
    handle_bt_device_profile,
    handle_bt_transfers,
    handle_bt_files,
    handle_bt_diagnostics,
    handle_bt_file_send,
    handle_bt_file_cancel,
    handle_bt_operation,
    handle_bt_media,
    handle_bt_pairing,
    handle_bt_device_autoconnect,
    handle_bt_device_hid,
    handle_bt_controller_status,
    handle_bt_pair,
    handle_bt_trust,
    handle_bt_connect,
    handle_bt_disconnect,
    handle_bt_remove,
    handle_bt_reset,
    handle_bt_capabilities,
    handle_bt_phone_role,
    handle_wifi_status,
    handle_wifi_scan,
    handle_wifi_connect,
    handle_cec_scan,
    handle_cec_power,
    handle_cec_nav,
    handle_cec_vol,
    handle_cec_input,
    handle_terminal_connect,
    handle_terminal_disconnect,
    handle_system_stats,
    handle_restart_mpv,
    handle_restart_dashboard,
    handle_restart_rpi,
    handle_system_hw_stats,
    handle_system_https_info,
    handle_youtube_cookie_status,
    handle_youtube_age_check,
    handle_media_preview,
    handle_dlna_select,
    handle_dlna_connect,
    handle_dlna_disconnect,
    handle_dlna_scan,
    handle_dlna_renderer_status,
    handle_dlna_renderer_start,
    handle_dlna_renderer_stop,
)


LEGACY_ROUTE_HITS: Dict[str, int] = {}
LEGACY_ROUTE_LAST_HIT: Dict[str, float] = {}


def _legacy_route_name(q: dict) -> str:
    route = q.get("_route", "unknown")
    if isinstance(route, list):
        return str(route[0]) if route else "unknown"
    return str(route)


def legacy_webserver_endpoint(q: dict) -> dict:
    """Marker for endpoints still implemented by webserver.py legacy branches."""
    route = _legacy_route_name(q)
    LEGACY_ROUTE_HITS[route] = LEGACY_ROUTE_HITS.get(route, 0) + 1
    LEGACY_ROUTE_LAST_HIT[route] = time.time()
    return {
        "ok": False,
        "legacy": True,
        "route": route,
        "hits": LEGACY_ROUTE_HITS[route],
        "last_hit": LEGACY_ROUTE_LAST_HIT[route],
        "error": "endpoint remains implemented in webserver.py",
    }


# Route registry: path -> handler function
ROUTES: Dict[str, Callable] = {
    # Audio routes
    "/audio/state": handle_audio_state,
    "/audio/default-sink": handle_audio_default_sink,
    "/audio/volume": handle_audio_volume,
    "/audio/matrix": handle_audio_matrix,
    "/audio/matrix/link": handle_audio_matrix_link,
    "/audio/latency": handle_audio_latency,
    "/audio/multi-output": handle_audio_multi_output,
    "/audio/bluetooth-profiles": handle_audio_bluetooth_profiles,
    "/audio/mute-state": handle_audio_mute_state,
    "/audio/bt": handle_audio_bt,
    "/audio/hdmi": handle_audio_hdmi,
    "/audio/dlna": handle_audio_dlna,
    "/audio/mute": handle_audio_mute,
    "/audio/route/alexa-bt": handle_audio_route_alexa_bt,
    "/audio/route/alexa-retarget": handle_audio_route_alexa_retarget,
    "/audio/route/dlna-input/status": handle_audio_route_dlnain_status,
    "/audio/route/dlna-input/start": handle_audio_route_dlnain_start,
    "/audio/route/dlna-input/stop": handle_audio_route_dlnain_stop,
    "/audio/route/dlna-input/mode": handle_audio_route_dlnain_mode,
    "/audio/route/dlna-input/target": handle_audio_route_dlnain_target,
    "/dlna/select": handle_dlna_select,
    "/dlna/connect": handle_dlna_connect,
    "/dlna/disconnect": handle_dlna_disconnect,
    "/dlna/scan": handle_dlna_scan,
    "/dlna/renderer/status": handle_dlna_renderer_status,
    "/dlna/renderer/start": handle_dlna_renderer_start,
    "/dlna/renderer/stop": handle_dlna_renderer_stop,
    "/keepalive": handle_keepalive,
    
    # Player routes
    "/mpv/play": handle_mpv_play,
    "/mpv/stop": handle_mpv_stop,
    "/mpv/status": handle_mpv_status,
    "/mpv/seek": handle_mpv_seek,
    "/mpv/volume": handle_mpv_volume,
    "/mpv/toggle": handle_mpv_toggle,
    "/mpv/seekabs": handle_mpv_seekabs,
    "/mpv/vol": handle_mpv_vol,
    "/mpv/memory": handle_mpv_memory,
    "/mpv/memory/clear": handle_mpv_memory_clear,
    "/mpv/memory-save": handle_mpv_memory_save,
    
    # Device routes
    "/devices/state": handle_devices_state,
    "/devices": legacy_webserver_endpoint,
    "/devices/bt/scan": legacy_webserver_endpoint,
    "/bt/state": handle_bt_state,
    "/bt/discovery": handle_bt_discovery,
    "/bt/adapter-power": handle_bt_adapter_power,
    "/bt/discoverable": handle_bt_discoverable,
    "/bt/settings": handle_bt_settings,
    "/bt/device-action": handle_bt_device_action,
    "/bt/device-profile": handle_bt_device_profile,
    "/bt/transfers": handle_bt_transfers,
    "/bt/files": handle_bt_files,
    "/bt/diagnostics": handle_bt_diagnostics,
    "/bt/file-send": handle_bt_file_send,
    "/bt/file-cancel": handle_bt_file_cancel,
    "/bt/operation": handle_bt_operation,
    "/bt/media": handle_bt_media,
    "/bt/pairing": handle_bt_pairing,
    "/bt/device-autoconnect": handle_bt_device_autoconnect,
    "/bt/device-hid": handle_bt_device_hid,
    "/bt/scan": handle_bt_scan,
    "/bt/controller": handle_bt_controller_status,
    "/bt/pair": handle_bt_pair,
    "/bt/trust": handle_bt_trust,
    "/bt/connect": handle_bt_connect,
    "/bt/disconnect": handle_bt_disconnect,
    "/bt/remove": handle_bt_remove,
    "/bt/reset": handle_bt_reset,
    "/bt/capabilities": handle_bt_capabilities,
    "/bt/phone-role": handle_bt_phone_role,
    "/wifi/status": handle_wifi_status,
    "/wifi/scan": handle_wifi_scan,
    "/wifi/connect": handle_wifi_connect,
    
    # CEC routes
    "/cec/scan": handle_cec_scan,
    "/cec/send": legacy_webserver_endpoint,
    "/cec/key": legacy_webserver_endpoint,
    "/cec/in": legacy_webserver_endpoint,
    "/cec/br/start": legacy_webserver_endpoint,
    "/cec/br/stop": legacy_webserver_endpoint,
    "/cec/br/st": legacy_webserver_endpoint,
    "/cec/power": handle_cec_power,
    "/cec/nav": handle_cec_nav,
    "/cec/vol": handle_cec_vol,
    "/cec/input": handle_cec_input,
    
    # Terminal routes
    "/terminal/connect": handle_terminal_connect,
    "/terminal/disconnect": handle_terminal_disconnect,
    
    # System routes
    "/system/stats": handle_system_stats,
    "/system/hw-stats": handle_system_hw_stats,
    "/system/status": legacy_webserver_endpoint,
    "/system/https-info": handle_system_https_info,
    "/restart/mpv": handle_restart_mpv,
    "/restart/dashboard": handle_restart_dashboard,
    "/restart/rpi": handle_restart_rpi,
    "/system/restart-mpv": legacy_webserver_endpoint,
    "/system/restart-dashboard": legacy_webserver_endpoint,
    "/system/restart-rpi": legacy_webserver_endpoint,
    "/youtube/cookies/status": handle_youtube_cookie_status,
    "/youtube/age-check": handle_youtube_age_check,
    "/media/preview": handle_media_preview,
}


def get_route(path: str) -> Optional[Callable]:
    """Get handler for a given path."""
    return ROUTES.get(path)


def list_routes() -> list:
    """List all registered routes."""
    return list(ROUTES.keys())
