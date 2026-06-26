"""Handler functions for the RPi‑TV Dashboard.
Each function receives the request handler instance ``self`` and the parsed
query dict ``q``.  They delegate to the existing implementation in
``webserver.py``.
"""

from typing import Callable, Dict
import webserver

# Helper to extract single query parameter safely
def _get(q: dict, name: str, default: str = "") -> str:
    return (q.get(name) or [default])[0].strip()

# Example handler implementations

def handle_audio_default_sink(self, q):
    name = _get(q, "name")
    return self.sj(200, webserver.audio_set_default(name))

def handle_audio_state(self, q):
    return self.sj(200, webserver.audio_state())

def handle_mpv_play(self, q):
    url = _get(q, "url")
    q_param = q.get("q") or [None]
    resume = _get(q, "resume", "0") not in ("0", "", "false", "False")
    if not url:
        return self.sj(400, {"error": "no url"})
    return self.sj(200, webserver.mpv_start(url, q_param[0], resume))

# Route table mapping URL path -> handler callable
route_table: Dict[str, Callable] = {
    "/audio/default-sink": handle_audio_default_sink,
    "/audio/state": handle_audio_state,
    "/mpv/play": handle_mpv_play,
    # Additional endpoints can be added here following the same pattern
}
