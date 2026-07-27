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


def test_legacy_routes_are_explicitly_marked():
    legacy_endpoints = {
        "/cec/send",
        "/system/hw-stats",
        "/youtube/age-check",
    }

    for endpoint in legacy_endpoints:
        assert routes.ROUTES[endpoint] is routes.legacy_webserver_endpoint

    migrated_audio_endpoints = {
        "/audio/bt",
        "/audio/hdmi",
        "/audio/dlna",
        "/audio/mute",
        "/audio/route/alexa-bt",
        "/audio/route/alexa-retarget",
        "/audio/route/dlna-input/status",
        "/audio/route/dlna-input/start",
        "/audio/route/dlna-input/stop",
        "/audio/route/dlna-input/mode",
        "/audio/route/dlna-input/target",
        "/keepalive",
    }

    migrated_mpv_endpoints = {
        "/mpv/toggle",
        "/mpv/seekabs",
        "/mpv/vol",
        "/mpv/memory",
        "/mpv/memory/clear",
        "/mpv/memory-save",
    }

    for endpoint in migrated_mpv_endpoints:
        assert routes.ROUTES[endpoint] is not routes.legacy_webserver_endpoint

    for endpoint in migrated_audio_endpoints:
        assert routes.ROUTES[endpoint] is not routes.legacy_webserver_endpoint


def test_legacy_route_telemetry_records_hits():
    routes.LEGACY_ROUTE_HITS.clear()
    routes.LEGACY_ROUTE_LAST_HIT.clear()

    payload = routes.legacy_webserver_endpoint({"_route": ["/cec/send"]})
    assert payload["legacy"] is True
    assert payload["route"] == "/cec/send"
    assert payload["hits"] == 1
    assert routes.LEGACY_ROUTE_HITS["/cec/send"] == 1

    payload = routes.legacy_webserver_endpoint({"_route": ["/cec/send"]})
    assert payload["hits"] == 2
    assert routes.LEGACY_ROUTE_HITS["/cec/send"] == 2


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


def test_webserver_delegates_migrated_audio_route(server_url):
    def handler(query):
        return {"ok": True, "route": query["_route"][0], "target": "bt"}

    original = routes.ROUTES["/audio/bt"]
    routes.ROUTES["/audio/bt"] = handler
    try:
        with urllib.request.urlopen(server_url + "/audio/bt", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/audio/bt"] = original

    assert payload == {"ok": True, "route": "/audio/bt", "target": "bt"}


def test_webserver_delegates_migrated_mpv_route(server_url):
    def handler(query):
        return {"ok": True, "route": query["_route"][0], "position": float(query["pos"][0])}

    original = routes.ROUTES["/mpv/seekabs"]
    routes.ROUTES["/mpv/seekabs"] = handler
    try:
        with urllib.request.urlopen(server_url + "/mpv/seekabs?pos=12.5", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/mpv/seekabs"] = original

    assert payload == {"ok": True, "route": "/mpv/seekabs", "position": 12.5}
