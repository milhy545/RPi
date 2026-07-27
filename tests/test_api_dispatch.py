"""Tests for the central API route dispatch path."""

import json
import sys
import threading
import time
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
    legacy_endpoints = set()

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

    migrated_system_endpoints = {
        "/system/hw-stats",
        "/system/https-info",
        "/system/status",
        "/system/restart-mpv",
        "/system/restart-dashboard",
        "/system/restart-rpi",
        "/youtube/cookies/status",
        "/youtube/age-check",
        "/media/preview",
        "/dlna/select",
        "/dlna/connect",
        "/dlna/disconnect",
        "/dlna/scan",
        "/dlna/renderer/status",
        "/dlna/renderer/start",
        "/dlna/renderer/stop",
        "/devices",
        "/devices/bt/scan",
        "/cec/send",
        "/cec/key",
        "/cec/in",
        "/cec/br/start",
        "/cec/br/stop",
        "/cec/br/st",
    }

    for endpoint in migrated_mpv_endpoints | migrated_system_endpoints:
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


def test_webserver_delegates_migrated_system_route(server_url):
    original = routes.ROUTES["/system/hw-stats"]
    routes.ROUTES["/system/hw-stats"] = lambda query: {"ok": True, "route": query["_route"][0], "cpu": [1.0]}
    try:
        with urllib.request.urlopen(server_url + "/system/hw-stats", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/system/hw-stats"] = original

    assert payload == {"ok": True, "route": "/system/hw-stats", "cpu": [1.0]}


def test_webserver_delegates_migrated_system_status_route(server_url):
    original = routes.ROUTES["/system/status"]
    routes.ROUTES["/system/status"] = lambda query: {"ok": True, "route": query["_route"][0], "mpv": {"mask": "1", "cores": "0"}}
    try:
        with urllib.request.urlopen(server_url + "/system/status", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/system/status"] = original

    assert payload == {"ok": True, "route": "/system/status", "mpv": {"mask": "1", "cores": "0"}}


def test_webserver_delegates_migrated_device_route(server_url):
    original = routes.ROUTES["/devices"]
    routes.ROUTES["/devices"] = lambda query: {"ok": True, "route": query["_route"][0], "bt": ["BT (11:22:33:44:55:66)"]}
    try:
        with urllib.request.urlopen(server_url + "/devices", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/devices"] = original

    assert payload == {"ok": True, "route": "/devices", "bt": ["BT (11:22:33:44:55:66)"]}


def test_webserver_delegates_migrated_cec_route(server_url):
    original = routes.ROUTES["/cec/send"]
    time.sleep(1.1)
    routes.ROUTES["/cec/send"] = lambda query: {"ok": True, "route": query["_route"][0], "cmd": query["c"][0]}
    try:
        with urllib.request.urlopen(server_url + "/cec/send?c=standby%200", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/cec/send"] = original

    assert payload == {"ok": True, "route": "/cec/send", "cmd": "standby 0"}


def test_webserver_delegates_migrated_media_route(server_url):
    time.sleep(1.1)
    original = routes.ROUTES["/media/preview"]
    routes.ROUTES["/media/preview"] = lambda query: {"ok": True, "route": query["_route"][0], "type": "direct"}
    try:
        with urllib.request.urlopen(server_url + "/media/preview?url=https%3A%2F%2Fexample.com%2Fvideo.mp4", timeout=5) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/media/preview"] = original

    assert payload == {"ok": True, "route": "/media/preview", "type": "direct"}


def test_webserver_delegates_migrated_dlna_routes(server_url):
    original_select = routes.ROUTES["/dlna/select"]
    original_scan = routes.ROUTES["/dlna/scan"]
    time.sleep(1.1)
    routes.ROUTES["/dlna/select"] = lambda query: {"ok": True, "route": query["_route"][0], "selected": query["name"][0]}
    routes.ROUTES["/dlna/scan"] = lambda query: {"ok": True, "route": query["_route"][0], "count": 1}
    try:
        with urllib.request.urlopen(server_url + "/dlna/select?name=Renderer&location=http%3A%2F%2Fexample", timeout=5) as response:
            assert response.status == 200
            select_payload = json.loads(response.read().decode())
        time.sleep(1.1)
        with urllib.request.urlopen(server_url + "/dlna/scan", timeout=5) as response:
            assert response.status == 200
            scan_payload = json.loads(response.read().decode())
    finally:
        routes.ROUTES["/dlna/select"] = original_select
        routes.ROUTES["/dlna/scan"] = original_scan

    assert select_payload == {"ok": True, "route": "/dlna/select", "selected": "Renderer"}
    assert scan_payload == {"ok": True, "route": "/dlna/scan", "count": 1}
