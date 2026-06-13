#!/usr/bin/env python3
"""Safe live checks for the WebUI Test Audio tab.

This test intentionally avoids mutating audio routes, default sinks, mpv state,
or Bluetooth state. It validates markup, JSON schemas, error handling, and the
built-in `/selftest/testaudio` endpoint against a running webserver.
"""

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("RPIDASHBOARD_WEBUI_URL", "http://127.0.0.1:8099")


def get(path: str):
    with urllib.request.urlopen(BASE_URL + path, timeout=8) as response:
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
    failures += check("stable Audio tab exists", 'data-t="audio"' in html)
    failures += check("Test Audio tab exists", 'data-t="testaudio"' in html)
    failures += check("Test Audio panel exists", 'id="p-testaudio"' in html)
    failures += check("Test Audio refresh hook exists", "sw('testaudio');taRefresh()" in html)
    failures += check("outputs/inputs layout markers exist", "Output Sinks" in html and "Input Sources" in html)
    failures += check("DLNA latency range is aligned", 'min="-5000" max="5000"' in html)

    status, state = get("/audio/state")
    failures += check("GET /audio/state", status == 200 and isinstance(state, dict), state)
    for key in ("default_sink", "default_source", "sinks", "sources", "devices", "routes", "latency", "sink_inputs"):
        failures += check(f"/audio/state has {key}", key in state)
    failures += check(
        "sink schema",
        all({"id", "name", "type", "present", "volume", "state"} <= set(item) for item in state.get("sinks", [])),
        state.get("sinks"),
    )
    failures += check(
        "source schema",
        all({"id", "name", "type", "present", "volume", "state"} <= set(item) for item in state.get("sources", [])),
        state.get("sources"),
    )

    status, selftest = get("/selftest/testaudio")
    failures += check("GET /selftest/testaudio", status == 200 and selftest.get("ok") is True, selftest)

    status, bad_volume = get("/audio/volume?kind=sink&name=__missing__&volume=abc")
    failures += check("bad volume returns JSON error", status == 200 and bad_volume.get("ok") is False, bad_volume)

    status, bad_latency = get("/audio/latency?key=dlna_output_offset_ms&value=abc")
    failures += check("bad latency returns JSON error", status == 200 and bad_latency.get("ok") is False, bad_latency)

    status, keepalive = get("/keepalive?action=status")
    failures += check("keepalive status returns JSON", status == 200 and keepalive.get("ok") is True, keepalive)

    print(f"FAILED={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        print(f"FAIL - WebUI is not reachable at {BASE_URL}: {exc}")
        raise SystemExit(2)
