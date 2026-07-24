"""Tests for the central API route dispatch path."""

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import webserver
from rpi_dashboard.api import routes
from rpi_dashboard.services.bluetooth.fake import FakeBluetoothBackend
from rpi_dashboard.services.bluetooth.service import set_backend_for_tests


WEBUI_GET_ENDPOINTS = {
    "/audio/bt",
    "/audio/default-sink",
    "/audio/dlna",
    "/audio/hdmi",
    "/audio/latency",
    "/audio/matrix",
    "/audio/matrix/link",
    "/audio/multi-output",
    "/audio/bluetooth-profiles",
    "/audio/mute-state",
    "/bt/device-profile",
    "/bt/device-hid",
    "/bt/transfers",
    "/bt/files",
    "/bt/diagnostics",
    "/bt/file-send",
    "/bt/file-cancel",
    "/bt/operation",
    "/bt/media",
    "/bt/pairing",
    "/audio/mute",
    "/audio/route/alexa-bt",
    "/audio/route/alexa-retarget",
    "/audio/route/dlna-input/mode",
    "/audio/route/dlna-input/start",
    "/audio/route/dlna-input/status",
    "/audio/route/dlna-input/stop",
    "/audio/route/dlna-input/target",
    "/audio/state",
    "/audio/volume",
    "/bt/connect",
    "/bt/adapter-power",
    "/bt/discoverable",
    "/bt/controller",
    "/bt/device-action",
    "/bt/disconnect",
    "/bt/discovery",
    "/bt/pair",
    "/bt/remove",
    "/bt/scan",
    "/bt/state",
    "/bt/settings",
    "/bt/trust",
    "/cec/br/st",
    "/cec/br/start",
    "/cec/br/stop",
    "/cec/in",
    "/cec/key",
    "/cec/scan",
    "/cec/send",
    "/devices",
    "/devices/bt/scan",
    "/devices/state",
    "/dlna/connect",
    "/dlna/disconnect",
    "/dlna/renderer/start",
    "/dlna/renderer/status",
    "/dlna/renderer/stop",
    "/dlna/scan",
    "/dlna/select",
    "/keepalive",
    "/media/preview",
    "/mpv/memory",
    "/mpv/memory-save",
    "/mpv/memory/clear",
    "/mpv/play",
    "/mpv/seek",
    "/mpv/seekabs",
    "/mpv/status",
    "/mpv/stop",
    "/mpv/toggle",
    "/mpv/vol",
    "/system/https-info",
    "/system/hw-stats",
    "/system/restart-dashboard",
    "/system/restart-mpv",
    "/system/restart-rpi",
    "/system/status",
    "/youtube/age-check",
    "/youtube/cookies/status",
}


@pytest.fixture()
def server_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), webserver.H)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_webserver_delegates_registered_get_route(server_url):
    def handler(query):
        return {
            "ok": True,
            "name": query["name"][0],
            "default": query.get("missing", ["fallback"])[0],
        }

    routes.ROUTES["/__test/dispatch"] = handler
    try:
        with urllib.request.urlopen(
            server_url + "/__test/dispatch?name=central", timeout=5
        ) as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == "application/json"
            payload = json.loads(response.read().decode())

        assert payload == {"ok": True, "name": "central", "default": "fallback"}
    finally:
        routes.ROUTES.pop("/__test/dispatch", None)


def test_route_registry_covers_webui_get_endpoints():
    missing = WEBUI_GET_ENDPOINTS - set(routes.ROUTES)
    assert missing == set()


def test_legacy_bt_connect_uses_adapter_aware_resolver(server_url):
    set_backend_for_tests(FakeBluetoothBackend.with_overlapping_remote())
    try:
        with urllib.request.urlopen(
            server_url + "/bt/connect?mac=DD:EE:FF:00:00:09",
            timeout=5,
        ) as response:
            payload = json.loads(response.read().decode())
    finally:
        set_backend_for_tests(None)

    assert payload["ok"] is False
    assert payload["code"] == "ambiguous_device"
