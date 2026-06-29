#!/usr/bin/env python3
"""Opt-in mutating checks for WebUI audio routes.

This test is disabled unless RPIDASHBOARD_MUTATING_AUDIO_TESTS=1 is set.
It may change default sinks, Bluetooth state, or DLNA state, so it must not run
as part of the safe E2E suite.
"""

import os
import urllib.request
import json

BASE_URL = os.getenv("RPIDASHBOARD_WEBUI_URL", "http://127.0.0.1:8099")


def get(path: str):
    with urllib.request.urlopen(BASE_URL + path, timeout=15) as response:
        return response.status, json.loads(response.read().decode("utf-8", "replace"))


def main() -> int:
    if os.getenv("RPIDASHBOARD_MUTATING_AUDIO_TESTS") != "1":
        print("SKIP - set RPIDASHBOARD_MUTATING_AUDIO_TESTS=1 to run mutating audio checks")
        return 0
    failures = 0
    for path in ("/audio/hdmi", "/audio/state"):
        status, body = get(path)
        ok = status == 200 and isinstance(body, dict)
        print(("PASS" if ok else "FAIL") + f" - {path} => {body}")
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
