#!/usr/bin/env python3
"""Safe live checks for the WebUI Test Audio tab.

This test intentionally avoids mutating audio routes, default sinks, mpv state,
or Bluetooth state. It validates markup, JSON schemas, error handling, and the
built-in `/selftest/testaudio` endpoint against a running webserver.
"""

import json
import os
import urllib.error
import urllib.request


BASE_URL = os.getenv("RPIDASHBOARD_WEBUI_URL", "http://127.0.0.1:8099")


def get(path: str):
    try:
        response = urllib.request.urlopen(BASE_URL + path, timeout=8)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        body = response.read().decode("utf-8", "replace")
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.status, json.loads(body)
        return response.status, body


def check(name: str, ok: bool, detail=None) -> int:
    status = "PASS" if ok else "FAIL"
    suffix = "" if detail is None else f" => {detail!r}"[:500]
    print(f"{status} - {name}{suffix}")
    return 0 if ok else 1


def main() -> int:
    failures = 0

    status, html = get("/")
    failures += check("GET /", status == 200, status)
    failures += check(
        "header language switch exists",
        'id="lang-switch"' in html
        and 'data-lang-btn="en"' in html
        and 'data-lang-btn="cz"' in html,
    )
    failures += check(
        "security banner exists",
        'id="security-banner"' in html
        and "function updateSecurityBanner" in html
        and "Open HTTPS" in html,
    )
    failures += check("primary Audio tab exists", 'data-t="audio"' in html)
    failures += check("old Test Audio tab removed", 'data-t="testaudio"' not in html)
    failures += check("primary Audio panel exists", 'id="p-audio"' in html)
    failures += check("Audio refresh hook exists", "sw('audio');taRefresh()" in html)
    failures += check(
        "Player tab initializes automatic clipboard/preview flow",
        "onclick=\"sw('player')\"" in html
        and "function playerEnter" in html
        and "function tryClipboardUrl" in html,
    )
    failures += check(
        "Player clipboard autoload retries on browser/user events",
        "function autoClipboardUrl" in html
        and "visibilitychange" in html
        and "window.addEventListener('focus'" in html,
    )
    failures += check(
        "Player has paste button inside URL input wrapper",
        'class="url-wrap"' in html
        and 'class="url-paste"' in html
        and 'onclick="pasteClipboardUrl()"' in html
        and "function pasteClipboardUrl" in html,
    )
    failures += check(
        "Player paste button has no duplicate icon/text and no manual preview button",
        "📋 Paste" not in html
        and 'data-icon="📋"' not in html
        and "🖼 Preview" not in html,
    )
    failures += check(
        "Player default quality is 720p",
        '<option value="720p" selected>720p</option>' in html,
    )
    failures += check(
        "language apply helper exists",
        "function applyLang()" in html and "const I18N=" in html,
    )
    failures += check(
        "Devices tab exists", 'data-t="devices"' in html and 'id="p-devices"' in html
    )
    failures += check(
        "outputs/inputs layout markers exist",
        "Output Sinks" in html and "Input Sources" in html,
    )
    failures += check("DLNA latency range is aligned", 'min="-5000" max="5000"' in html)
    failures += check("latency label matches audio-delay", "Audio delay (ms)" in html)
    failures += check(
        "input devices use source volume API",
        "includes('input')?'source':'sink'" in html,
    )
    failures += check(
        "connected badges use existing ok style", 'class="badge ok"' in html
    )
    failures += check(
        "DLNA keepalive badge is sink-specific", "hasDlnaKeepalive" in html
    )
    failures += check("volume slider is debounced", "taSetVolDebounced" in html)
    failures += check(
        "YouTube cookie diagnostics exist",
        "/youtube/cookies/status" in html and "/youtube/age-check" in html,
    )
    failures += check(
        "YouTube diagnostics moved to Player tab",
        'id="p-player"' in html
        and 'id="yt-cookie-status"' in html
        and "function playerEnter" in html,
    )
    failures += check(
        "Kodi tab removed from WebUI",
        'data-t="kodi"' not in html
        and 'id="p-kodi"' not in html
        and "function kDiag" not in html,
    )

    status, state = get("/audio/state")
    failures += check(
        "GET /audio/state", status == 200 and isinstance(state, dict), state
    )
    for key in (
        "default_sink",
        "default_source",
        "sinks",
        "sources",
        "devices",
        "routes",
        "latency",
        "sink_inputs",
    ):
        failures += check(f"/audio/state has {key}", key in state)
    failures += check(
        "sink schema",
        all(
            {"id", "name", "type", "present", "volume", "state"} <= set(item)
            for item in state.get("sinks", [])
        ),
        state.get("sinks"),
    )
    failures += check(
        "source schema",
        all(
            {"id", "name", "type", "present", "volume", "state"} <= set(item)
            for item in state.get("sources", [])
        ),
        state.get("sources"),
    )

    status, selftest = get("/selftest/testaudio")
    failures += check(
        "GET /selftest/testaudio",
        status == 200 and selftest.get("ok") is True,
        selftest,
    )

    status, bad_volume = get("/audio/volume?kind=sink&name=__missing__&volume=abc")
    failures += check(
        "bad volume returns JSON error",
        status == 200 and bad_volume.get("ok") is False,
        bad_volume,
    )

    status, bad_latency = get("/audio/latency?key=dlna_output_offset_ms&value=abc")
    failures += check(
        "bad latency returns JSON error",
        status == 200 and bad_latency.get("ok") is False,
        bad_latency,
    )

    status, keepalive = get("/keepalive?action=status")
    failures += check(
        "keepalive status returns JSON",
        status == 200 and keepalive.get("ok") is True,
        keepalive,
    )

    status, devices = get("/devices/state")
    failures += check(
        "devices state returns JSON",
        status == 200 and devices.get("ok") is True and "bluetooth" in devices,
        devices,
    )

    status, wifi = get("/wifi/status")
    failures += check(
        "wifi status returns JSON", status == 200 and wifi.get("ok") is True, wifi
    )

    status, cookies = get("/youtube/cookies/status")
    failures += check(
        "youtube cookie status returns JSON",
        status == 200 and "exists" in cookies and "cookie_count" in cookies,
        cookies,
    )

    status, preview = get("/media/preview?url=https%3A%2F%2Fexample.com%2Fvideo.mp4")
    failures += check(
        "direct media preview returns JSON",
        status == 200 and preview.get("ok") is True and preview.get("type") == "direct",
        preview,
    )

    status, generic_preview = get(
        "/media/preview?url=https%3A%2F%2Fexample.com%2Fwatch%3Fid%3D1"
    )
    failures += check(
        "generic http URL preview returns JSON",
        status == 200
        and generic_preview.get("ok") is True
        and generic_preview.get("type") == "direct",
        generic_preview,
    )

    status, https_info = get("/system/https-info")
    failures += check(
        "https info endpoint returns configured ports",
        status == 200
        and https_info.get("ok") is True
        and https_info.get("https_port") == 8443
        and https_info.get("friendly_https_port") == 443
        and https_info.get("friendly_http_port") == 80,
        https_info,
    )

    status, kodi = get("/kodi/status")
    failures += check(
        "kodi status route is deprecated",
        status == 410 and kodi.get("deprecated") is True,
        kodi,
    )

    print(f"FAILED={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"FAIL - WebUI is not reachable at {BASE_URL}: {exc}")
        raise SystemExit(2)
