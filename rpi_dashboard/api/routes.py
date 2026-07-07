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

# Route registry: path -> handler function
ROUTES: Dict[str, Callable] = {
    # Audio routes
    "/audio/state": handle_audio_state,
    "/audio/default-sink": handle_audio_default_sink,
    "/audio/volume": handle_audio_volume,
    "/audio/matrix": handle_audio_matrix,
    "/audio/matrix/link": handle_audio_matrix_link,
    "/audio/latency": handle_audio_latency,
    
    # Player routes
    "/mpv/play": handle_mpv_play,
    "/mpv/stop": handle_mpv_stop,
    "/mpv/status": handle_mpv_status,
    "/mpv/seek": handle_mpv_seek,
    "/mpv/volume": handle_mpv_volume,
    
    # Device routes
    "/devices/state": handle_devices_state,
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
    "/cec/power": handle_cec_power,
    "/cec/nav": handle_cec_nav,
    "/cec/vol": handle_cec_vol,
    "/cec/input": handle_cec_input,
    
    # Terminal routes
    "/terminal/connect": handle_terminal_connect,
    "/terminal/disconnect": handle_terminal_disconnect,
    
    # System routes
    "/system/stats": handle_system_stats,
    "/restart/mpv": handle_restart_mpv,
    "/restart/dashboard": handle_restart_dashboard,
    "/restart/rpi": handle_restart_rpi,
}


def get_route(path: str) -> Optional[Callable]:
    """Get handler for a given path."""
    return ROUTES.get(path)


def list_routes() -> list:
    """List all registered routes."""
    return list(ROUTES.keys())
