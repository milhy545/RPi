"""Tests for CSRF enforcement on mutating API endpoints (Phase 5)."""

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import webserver
from rpi_dashboard.auth import AuthStore, SessionStore

def _patch_pbkdf2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rpi_dashboard.auth.calibrate_pbkdf2", lambda target_ms=200, samples=3: 100_000)
    monkeypatch.setattr("rpi_dashboard.auth.secrets.token_bytes", lambda size: b"\x01" * size)

@pytest.fixture
def test_server(tmp_path, monkeypatch):
    """Start a ThreadingHTTPServer with mocked stores and provisioned expert."""
    _patch_pbkdf2(monkeypatch)

    auth_path = tmp_path / "auth.json"
    auth_store = AuthStore(auth_path)
    session_store = SessionStore()

    # Provision both to satisfy is_provisioned()
    auth_store.set_expert("expertpass")
    auth_store.set_admin("adminpass")

    server = ThreadingHTTPServer(("127.0.0.1", 0), webserver.H)
    host, port = server.server_address

    with patch("webserver.auth_store", auth_store), \
         patch("webserver.session_store", session_store), \
         patch("webserver._check_rate_limit", lambda *args, **kwargs: True):
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://{host}:{port}"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def _login_expert(server_url):
    req = urllib.request.Request(f"{server_url}/auth/login", method="POST")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps({"password": "expertpass", "role": "expert"}).encode()
    with urllib.request.urlopen(req, timeout=5) as resp:
        set_cookie = resp.headers.get_all("Set-Cookie")
        set_cookie_header = "; ".join(set_cookie) if set_cookie else ""

        session_cookie = None
        csrf_cookie = None
        for part in set_cookie_header.split("; "):
            if part.startswith("rpi_session="):
                session_cookie = part.split("=")[1]
            elif part.startswith("rpi_csrf="):
                csrf_cookie = part.split("=")[1]

        return session_cookie, csrf_cookie


def _post(url, session_cookie=None, csrf_token=None, data=None):
    req = urllib.request.Request(url, method="POST")
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode()

    cookies = []
    if session_cookie:
        cookies.append(f"rpi_session={session_cookie}")
    if csrf_token:
        cookies.append(f"rpi_csrf={csrf_token}")
        req.add_header("X-CSRF-Token", csrf_token)

    if cookies:
        req.add_header("Cookie", "; ".join(cookies))

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_wifi_connect_requires_csrf(test_server):
    session, csrf = _login_expert(test_server)

    # Without CSRF
    status, body = _post(f"{test_server}/wifi/connect", session_cookie=session, csrf_token=None, data={"ssid": "test"})
    assert status == 403
    assert body == {"error": "CSRF validation failed"}

    # With wrong CSRF
    status, body = _post(f"{test_server}/wifi/connect", session_cookie=session, csrf_token="wrongtoken", data={"ssid": "test"})
    assert status == 403

    with patch("webserver.wifi_connect", return_value={"status": "connecting"}):
        status, body = _post(f"{test_server}/wifi/connect", session_cookie=session, csrf_token=csrf, data={"ssid": "test"})
        assert status == 200

def test_basic_csrf_origin_defense(test_server):
    # /report is a Basic mutating route, doesn't require session but enforces Origin defense
    req = urllib.request.Request(f"{test_server}/report", method="POST", data=json.dumps({"type": "bug", "description": "test"}).encode())
    req.add_header("Origin", "http://evil.com")
    try:
        urllib.request.urlopen(req, timeout=5)
        status = 200
    except urllib.error.HTTPError as e:
        status = e.code
    assert status == 403

    req = urllib.request.Request(f"{test_server}/report", method="POST", data=json.dumps({"type": "bug", "description": "test"}).encode())
    req.add_header("Origin", "http://192.168.0.100")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    assert status in (200, 201)

def _get(
    url: str,
    session_cookie: str | None = None,
    csrf_token: str | None = None,
) -> tuple[int, dict]:
    req = urllib.request.Request(url, method="GET")
    if session_cookie:
        req.add_header("Cookie", f"rpi_session={session_cookie}")
    if csrf_token is not None:
        req.add_header("X-CSRF-Token", csrf_token)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def test_mutating_get_requires_csrf(test_server):
    session, csrf = _login_expert(test_server)

    # /audio/volume is an Expert mutating route
    # Without CSRF header
    status, body = _get(f"{test_server}/audio/volume?sink=xxx&vol=50", session_cookie=session)
    assert status == 403
    assert body == {"error": "CSRF validation failed"}

    # With wrong CSRF header
    status, body = _get(f"{test_server}/audio/volume?sink=xxx&vol=50", session_cookie=session, csrf_token="wrong")
    assert status == 403

    with patch("webserver.audio_set_volume", return_value={"status": "ok"}):
        status, body = _get(f"{test_server}/audio/volume?sink=xxx&vol=50", session_cookie=session, csrf_token=csrf)
        assert status == 200
