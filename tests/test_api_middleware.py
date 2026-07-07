"""Tests for shared API middleware helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rpi_dashboard.api import middleware


def test_allowed_ip_accepts_configured_subnet():
    assert middleware.is_allowed_ip("127.0.0.1", ["127.0.0.0/8"])


def test_allowed_ip_rejects_invalid_or_outside_subnet():
    assert not middleware.is_allowed_ip("not-an-ip", ["127.0.0.0/8"])
    assert not middleware.is_allowed_ip("10.0.0.10", ["127.0.0.0/8"])


def test_cors_origin_allows_localhost_local_and_allowed_ip():
    allowed = ["192.168.0.0/24"]

    assert middleware.allowed_cors_origin("http://localhost:8080", allowed) == "http://localhost:8080"
    assert middleware.allowed_cors_origin("http://rpi-tv.local", allowed) == "http://rpi-tv.local"
    assert middleware.allowed_cors_origin("http://192.168.0.50:8080", allowed) == "http://192.168.0.50:8080"


def test_cors_origin_falls_back_for_untrusted_or_malformed_origin():
    allowed = ["192.168.0.0/24"]

    assert middleware.allowed_cors_origin("http://203.0.113.10", allowed) == "http://localhost"
    assert middleware.allowed_cors_origin("not a url", allowed) == "http://localhost"
    assert middleware.allowed_cors_origin(None, allowed) == "http://localhost"


def test_rate_limiter_blocks_until_window_elapses():
    cache = {}

    assert middleware.check_rate_limit("127.0.0.1", cache, now=10.0, window_seconds=1.0)
    assert not middleware.check_rate_limit("127.0.0.1", cache, now=10.5, window_seconds=1.0)
    assert middleware.check_rate_limit("127.0.0.1", cache, now=11.1, window_seconds=1.0)
