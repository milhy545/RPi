"""Central configuration for RPi‑TV Dashboard.
All tunable values (ports, timeouts, rate limits, etc.) are defined here.
Modules should import from this file instead of using hard‑coded literals.
"""

# Server ports (environment variables can override)
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
