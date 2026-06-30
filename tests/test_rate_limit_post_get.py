#!/usr/bin/env python3
"""Focused tests for rate‑limit behavior.

* GET requests should NOT be rate‑limited (frontend polls /audio/state etc.).
* POST requests should be rate‑limited (second quick POST returns 429).
"""

import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
import webserver


# Module‑scoped fixture to start server in daemon thread
@pytest.fixture(scope="module", autouse=True)
def start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), webserver.H)
    host, port = server.server_address
    url = f"http://{host}:{port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    os.environ["RPIDASHBOARD_WEBUI_URL"] = url
    yield
    server.shutdown()


# Autouse fixture to clear rate‑limit cache between tests
@pytest.fixture(autouse=True)
def clear_cache():
    webserver._rate_limit_cache.clear()
    yield
    webserver._rate_limit_cache.clear()


def get(path: str):
    base = os.getenv("RPIDASHBOARD_WEBUI_URL", "http://127.0.0.1:8099")
    try:
        resp = urllib.request.urlopen(base + path, timeout=5)
    except urllib.error.HTTPError as exc:
        resp = exc
    with resp:
        return resp.status


def post(path: str, payload: dict):
    base = os.getenv("RPIDASHBOARD_WEBUI_URL", "http://127.0.0.1:8099")
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        resp = exc
    with resp:
        return resp.status


# ── GET tests ──────────────────────────────────────────────────────

def test_get_root_not_rate_limited():
    """Rapid GET / requests should never be rate‑limited."""
    s1 = get("/")
    s2 = get("/")
    assert s1 == 200 and s2 == 200, f"GETs were rate‑limited: {s1}, {s2}"


def test_get_audio_state_not_rate_limited(monkeypatch):
    """Frontend polls /audio/state repeatedly — must never get 429."""
    # Mock audio_state to avoid pactl dependency in test env
    monkeypatch.setattr(webserver, "audio_state", lambda: {"ok": True})
    statuses = [get("/audio/state") for _ in range(5)]
    assert all(s == 200 for s in statuses), (
        f"/audio/state got rate‑limited: {statuses}"
    )


# ── POST tests ─────────────────────────────────────────────────────

def test_post_rate_limited(monkeypatch):
    """Second rapid POST /report within the rate window returns 429."""
    def fake_save_report(report: dict, client_ip: str) -> str:
        """Matches real _save_report(report, client_ip) signature."""
        return "fake_report.json"
    monkeypatch.setattr(webserver, "_save_report", fake_save_report)

    payload = {"type": "bug", "description": "rate‑limit test"}
    s1 = post("/report", payload)
    s2 = post("/report", payload)
    assert s1 == 201, f"First POST failed with {s1}"
    assert s2 == 429, f"Second POST not rate‑limited, got {s2}"
