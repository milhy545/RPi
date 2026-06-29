"""Central configuration for RPi‑TV Dashboard.
All tunable values (ports, timeouts, rate limits, etc.) are defined here.
Modules should import from this file instead of using hard‑coded literals.
"""

# Server ports (environment variables can override)
# Additional: allowed IP subnets for API access (local LAN + Tailscale)
ALLOWED_SUBNETS = [
    "127.0.0.0/8",      # localhost
    "192.168.0.0/16",   # typical home LAN
    "100.64.0.0/10",    # Tailscale range (default)
]
import os

HOST = "0.0.0.0"
PORT = int(os.getenv("RPIDASHBOARD_PORT", "8080"))
HTTP_PORT = int(os.getenv("RPIDASHBOARD_HTTP_PORT", "80"))
HTTPS_PORT = int(os.getenv("RPIDASHBOARD_HTTPS_PORT", "8443"))
HTTPS_PORT_ALT = int(os.getenv("RPIDASHBOARD_HTTPS_PORT_ALT", "443"))

# Rate limiting (seconds per request per IP)
RATE_LIMIT_SECONDS = 1.0

# Misc constants
MAX_SOCKET_BUFFER = 65536
SOCKET_RECV_SIZE = 4096
TERMINAL_POLL_INTERVAL = 0.35
DEFAULT_TIMEOUT = 3
CEC_TIMEOUT = 5
MPV_CONNECT_TIMEOUT = 2

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Ensure reports directory exists at import time
os.makedirs(REPORTS_DIR, exist_ok=True)

# KODI config
KODI_HOST = "127.0.0.1"
KODI_PORT = 9090

# MPV config
MPV_SOCKET = "/tmp/rpi-mpv.sock"

# WS config
WS_PORT = 8098

# DLNA config
PA_DLNA_PORT = "8088"
AUDIO_STATE_CACHE_TTL = 0.75

# TUI intervals
TUI_STATS_INTERVAL = 2.0
TUI_SETTINGS_INTERVAL = 5.0
