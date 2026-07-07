"""API routes module for RPi-TV Dashboard.

Maps URL paths to handler functions.
"""

from typing import Callable, Dict, Optional
from .handlers import (
    handle_audio_state,
    handle_audio_default_sink,
    handle_audio_volume,
    handle_audio_matrix,
    handle_audio_matrix_link,
    handle_audio_latency,
    handle_mpv_play,
    handle_mpv_stop,
    handle_mpv_status,
    handle_mpv_seek,
    handle_mpv_volume,
    handle_devices_state,
    handle_bt_scan,
    handle_bt_pair,
    handle_bt_trust,
    handle_bt_connect,
    handle_bt_disconnect,
    handle_bt_remove,
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
)


def legacy_webserver_endpoint(q: dict) -> dict:
    """Marker for endpoints still implemented by webserver.py legacy branches."""
    return {
        "ok": False,
        "legacy": True,
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
    "/audio/bt": legacy_webserver_endpoint,
    "/audio/hdmi": legacy_webserver_endpoint,
    "/audio/dlna": legacy_webserver_endpoint,
    "/audio/mute": legacy_webserver_endpoint,
    "/audio/route/alexa-bt": legacy_webserver_endpoint,
    "/audio/route/alexa-retarget": legacy_webserver_endpoint,
    "/audio/route/dlna-input/status": legacy_webserver_endpoint,
    "/audio/route/dlna-input/start": legacy_webserver_endpoint,
    "/audio/route/dlna-input/stop": legacy_webserver_endpoint,
    "/audio/route/dlna-input/mode": legacy_webserver_endpoint,
    "/audio/route/dlna-input/target": legacy_webserver_endpoint,
    "/dlna/select": legacy_webserver_endpoint,
    "/dlna/connect": legacy_webserver_endpoint,
    "/dlna/disconnect": legacy_webserver_endpoint,
    "/dlna/scan": legacy_webserver_endpoint,
    "/dlna/renderer/status": legacy_webserver_endpoint,
    "/dlna/renderer/start": legacy_webserver_endpoint,
    "/dlna/renderer/stop": legacy_webserver_endpoint,
    "/keepalive": legacy_webserver_endpoint,
    
    # Player routes
    "/mpv/play": handle_mpv_play,
    "/mpv/stop": handle_mpv_stop,
    "/mpv/status": handle_mpv_status,
    "/mpv/seek": handle_mpv_seek,
    "/mpv/volume": handle_mpv_volume,
    "/mpv/toggle": legacy_webserver_endpoint,
    "/mpv/seekabs": legacy_webserver_endpoint,
    "/mpv/vol": legacy_webserver_endpoint,
    "/mpv/memory": legacy_webserver_endpoint,
    "/mpv/memory/clear": legacy_webserver_endpoint,
    "/mpv/memory-save": legacy_webserver_endpoint,
    
    # Device routes
    "/devices/state": handle_devices_state,
    "/devices": legacy_webserver_endpoint,
    "/devices/bt/scan": legacy_webserver_endpoint,
    "/bt/scan": handle_bt_scan,
    "/bt/pair": handle_bt_pair,
    "/bt/trust": handle_bt_trust,
    "/bt/connect": handle_bt_connect,
    "/bt/disconnect": handle_bt_disconnect,
    "/bt/remove": handle_bt_remove,
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
    "/system/hw-stats": legacy_webserver_endpoint,
    "/system/status": legacy_webserver_endpoint,
    "/system/https-info": legacy_webserver_endpoint,
    "/restart/mpv": handle_restart_mpv,
    "/restart/dashboard": handle_restart_dashboard,
    "/restart/rpi": handle_restart_rpi,
    "/system/restart-mpv": legacy_webserver_endpoint,
    "/system/restart-dashboard": legacy_webserver_endpoint,
    "/system/restart-rpi": legacy_webserver_endpoint,
    "/youtube/cookies/status": legacy_webserver_endpoint,
    "/youtube/age-check": legacy_webserver_endpoint,
    "/media/preview": legacy_webserver_endpoint,
}


def get_route(path: str) -> Optional[Callable]:
    """Get handler for a given path."""
    return ROUTES.get(path)


def list_routes() -> list:
    """List all registered routes."""
    return list(ROUTES.keys())
