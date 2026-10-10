"""Tests for the package entrypoint."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import webserver
from rpi_dashboard import __main__ as package_main


def test_package_entrypoint_delegates_to_webserver_main(monkeypatch):
    calls = []

    def fake_main() -> None:
        calls.append("called")

    monkeypatch.setattr(webserver, "main", fake_main)

    package_main.main()

    assert calls == ["called"]
