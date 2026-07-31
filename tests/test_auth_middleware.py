"""Focused tests for Phase 7 middleware transport helpers."""

from __future__ import annotations

import ssl
import sys
from unittest.mock import MagicMock


sys.path.insert(0, str(__file__).replace("tests/test_auth_middleware.py", ""))

from rpi_dashboard.api import middleware as mw


# ─── is_https ─────────────────────────────────────────────────────────────


def test_is_https_true_on_connection_ssl():
    """is_https returns True when handler.connection is an SSLSocket."""
    handler = MagicMock()
    handler.connection = MagicMock(spec=ssl.SSLSocket)
    assert mw.is_https(handler) is True


def test_is_https_true_on_request_ssl():
    """is_https returns True when handler.request is an SSLSocket."""
    handler = MagicMock()
    handler.connection = MagicMock()  # plain
    handler.request = MagicMock(spec=ssl.SSLSocket)
    assert mw.is_https(handler) is True


def test_is_https_false_on_plain_socket():
    """is_https returns False for plain socket."""
    handler = MagicMock()
    handler.connection = MagicMock()  # not SSLSocket
    handler.request = MagicMock()  # not SSLSocket
    assert mw.is_https(handler) is False


def test_is_https_false_when_no_connection():
    """is_https returns False when handler has no connection/request."""
    handler = MagicMock()
    handler.connection = None
    handler.request = None
    assert mw.is_https(handler) is False


def test_is_https_rejects_x_forwarded_proto():
    """is_https never reads X-Forwarded-Proto header."""
    handler = MagicMock()
    handler.connection = MagicMock()  # plain
    handler.request = MagicMock()
    handler.headers = {"X-Forwarded-Proto": "https", "X-Forwarded-Ssl": "on"}
    assert mw.is_https(handler) is False


def test_is_https_rejects_forwarded_header():
    """is_https never reads Forwarded header."""
    handler = MagicMock()
    handler.connection = MagicMock()
    handler.headers = {"Forwarded": "for=192.0.2.1; proto=https; by=10.0.0.1"}
    assert mw.is_https(handler) is False


# ─── is_loopback ──────────────────────────────────────────────────────────


def test_is_loopback_ipv4():
    """is_loopback returns True for 127.0.0.1."""
    handler = MagicMock()
    handler.client_address = ("127.0.0.1", 54321)
    assert mw.is_loopback(handler) is True


def test_is_loopback_ipv4_full_range():
    """is_loopback returns True for all 127.0.0.0/8 addresses."""
    for ip in ("127.0.0.1", "127.255.255.255", "127.0.0.100"):
        handler = MagicMock()
        handler.client_address = (ip, 1234)
        assert mw.is_loopback(handler) is True, f"failed for {ip}"


def test_is_loopback_ipv6():
    """is_loopback returns True for ::1."""
    handler = MagicMock()
    handler.client_address = ("::1", 54321)
    assert mw.is_loopback(handler) is True


def test_is_loopback_false_for_lan():
    """is_loopback returns False for LAN addresses."""
    for ip in ("192.168.0.10", "10.0.0.5", "172.16.0.1"):
        handler = MagicMock()
        handler.client_address = (ip, 1234)
        assert mw.is_loopback(handler) is False, f"failed for {ip}"


def test_is_loopback_false_for_public():
    """is_loopback returns False for public addresses."""
    handler = MagicMock()
    handler.client_address = ("8.8.8.8", 1234)
    assert mw.is_loopback(handler) is False


def test_is_loopback_rejects_x_forwarded_for():
    """is_loopback never reads X-Forwarded-For header."""
    handler = MagicMock()
    handler.client_address = ("192.168.0.10", 1234)
    handler.headers = {"X-Forwarded-For": "127.0.0.1"}
    assert mw.is_loopback(handler) is False


def test_is_loopback_false_when_no_client_address():
    """is_loopback returns False when client_address is missing."""
    handler = MagicMock()
    handler.client_address = None
    assert mw.is_loopback(handler) is False


# ─── credential_transport_allowed ─────────────────────────────────────────


def test_credential_transport_allowed_tls():
    """TLS transport allows credentials regardless of loopback."""
    assert mw.credential_transport_allowed(is_tls=True, is_loopback=False) is True


def test_credential_transport_allowed_loopback():
    """Loopback transport allows credentials without TLS."""
    assert mw.credential_transport_allowed(is_tls=False, is_loopback=True) is True


def test_credential_transport_allowed_tls_and_loopback():
    """Both TLS and loopback allows credentials."""
    assert mw.credential_transport_allowed(is_tls=True, is_loopback=True) is True


def test_credential_transport_denied_plain_lan():
    """Plain LAN transport denies credentials."""
    assert mw.credential_transport_allowed(is_tls=False, is_loopback=False) is False


# ─── extract_session_cookie ───────────────────────────────────────────────


def test_extract_session_cookie_present():
    """rpi_session cookie is extracted from Cookie header."""
    request = MagicMock()
    request.headers = {"Cookie": "rpi_session=abc123; other=xyz"}
    assert mw.extract_session_cookie(request) == "abc123"


def test_extract_session_cookie_rejects_unrelated_session():
    """Cookie named 'session' is ignored; only 'rpi_session' is accepted."""
    request = MagicMock()
    request.headers = {"Cookie": "session=unrelated; other=xyz"}
    assert mw.extract_session_cookie(request) is None


def test_extract_session_cookie_missing():
    """Missing rpi_session cookie returns None."""
    request = MagicMock()
    request.headers = {"Cookie": "other=xyz"}
    assert mw.extract_session_cookie(request) is None


def test_extract_session_cookie_no_cookie_header():
    """Missing Cookie header returns None."""
    request = MagicMock()
    request.headers = {}
    assert mw.extract_session_cookie(request) is None


def test_extract_session_cookie_malformed():
    """Malformed Cookie header returns None."""
    request = MagicMock()
    request.headers = {"Cookie": "not a valid cookie"}
    assert mw.extract_session_cookie(request) is None


def test_extract_session_cookie_empty_value():
    """Empty rpi_session cookie value returns empty string."""
    request = MagicMock()
    request.headers = {"Cookie": "rpi_session=; other=xyz"}
    assert mw.extract_session_cookie(request) == ""


# ─── extract_bearer_role ──────────────────────────────────────────────────


def test_extract_bearer_role_valid():
    """Valid Bearer token returns Role from auth_store."""
    from rpi_dashboard.auth import Role
    auth_store = MagicMock()
    auth_store.get_api_key_role.return_value = Role.ADMIN
    request = MagicMock()
    request.headers = {"Authorization": "Bearer abc123"}
    assert mw.extract_bearer_role(request, auth_store) is Role.ADMIN
    auth_store.get_api_key_role.assert_called_once_with("abc123")


def test_extract_bearer_role_case_insensitive():
    """Bearer scheme is case-insensitive."""
    from rpi_dashboard.auth import Role
    auth_store = MagicMock()
    auth_store.get_api_key_role.return_value = Role.EXPERT
    for hdr in ("Bearer token", "bearer token", "BEARER token", "BeArEr token"):
        request = MagicMock()
        request.headers = {"Authorization": hdr}
        assert mw.extract_bearer_role(request, auth_store) is Role.EXPERT


def test_extract_bearer_role_missing_header():
    """Missing Authorization header returns None."""
    auth_store = MagicMock()
    request = MagicMock()
    request.headers = {}
    assert mw.extract_bearer_role(request, auth_store) is None


def test_extract_bearer_role_not_bearer():
    """Non-Bearer scheme returns None."""
    auth_store = MagicMock()
    for hdr in ("Basic dXNlcjpwYXNz", "Token abc123", "ApiKey xyz"):
        request = MagicMock()
        request.headers = {"Authorization": hdr}
        assert mw.extract_bearer_role(request, auth_store) is None


def test_extract_bearer_role_malformed():
    """Malformed Bearer header returns None."""
    auth_store = MagicMock()
    for hdr in ("Bearer", "Bearer  ", "Bearer token extra"):
        request = MagicMock()
        request.headers = {"Authorization": hdr}
        assert mw.extract_bearer_role(request, auth_store) is None


def test_extract_bearer_role_empty_token():
    """Empty token returns None."""
    auth_store = MagicMock()
    request = MagicMock()
    request.headers = {"Authorization": "Bearer"}
    assert mw.extract_bearer_role(request, auth_store) is None


# ─── set_session_cookie ───────────────────────────────────────────────────


def test_set_session_cookie_attributes_tls():
    """Session cookie has HttpOnly, SameSite=Lax, Path=/, Secure on TLS."""
    handler = MagicMock()
    mw.set_session_cookie(handler, "a" * 64, 3600, is_tls=True)

    handler.send_header.assert_called_once()
    cookie = handler.send_header.call_args[0][1]
    assert cookie.startswith("rpi_session=")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Path=/" in cookie
    assert "Max-Age=3600" in cookie
    assert "Secure" in cookie


def test_set_session_cookie_attributes_no_tls():
    """Session cookie omits Secure on plain HTTP."""
    handler = MagicMock()
    mw.set_session_cookie(handler, "b" * 64, 7200, is_tls=False)

    cookie = handler.send_header.call_args[0][1]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Path=/" in cookie
    assert "Max-Age=7200" in cookie
    assert "Secure" not in cookie


def test_set_session_cookie_token_preserved():
    """Exact token hex is used in cookie value."""
    handler = MagicMock()
    token = "deadbeef" * 8
    mw.set_session_cookie(handler, token, 1800, is_tls=True)

    cookie = handler.send_header.call_args[0][1]
    assert f"rpi_session={token}" in cookie


# ─── set_csrf_cookie ──────────────────────────────────────────────────────


def test_set_csrf_cookie_attributes_tls():
    """CSRF cookie has SameSite=Strict, Path=/, Secure on TLS, NO HttpOnly."""
    handler = MagicMock()
    mw.set_csrf_cookie(handler, "c" * 32, is_tls=True)

    handler.send_header.assert_called_once()
    cookie = handler.send_header.call_args[0][1]
    assert cookie.startswith("rpi_csrf=")
    assert "HttpOnly" not in cookie
    assert "SameSite=Strict" in cookie
    assert "Path=/" in cookie
    assert "Secure" in cookie
    assert "Max-Age" not in cookie


def test_set_csrf_cookie_attributes_no_tls():
    """CSRF cookie omits Secure on plain HTTP."""
    handler = MagicMock()
    mw.set_csrf_cookie(handler, "d" * 32, is_tls=False)

    cookie = handler.send_header.call_args[0][1]
    assert "HttpOnly" not in cookie
    assert "SameSite=Strict" in cookie
    assert "Path=/" in cookie
    assert "Secure" not in cookie


def test_set_csrf_cookie_token_preserved():
    """Exact CSRF token hex is used in cookie value."""
    handler = MagicMock()
    token = "feedface" * 4
    mw.set_csrf_cookie(handler, token, is_tls=True)

    cookie = handler.send_header.call_args[0][1]
    assert f"rpi_csrf={token}" in cookie


# ─── Integration: X-Forwarded-Proto spoof rejection ───────────────────────


def test_x_forwarded_proto_spoof_rejected_e2e():
    """Full chain: proxy claims HTTPS but plain socket -> credentials denied."""
    handler = MagicMock()
    handler.connection = MagicMock()  # plain
    handler.request = MagicMock()
    handler.client_address = ("192.168.0.10", 1234)
    handler.headers = {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Ssl": "on",
        "Forwarded": "proto=https",
    }

    is_tls = mw.is_https(handler)
    is_loopback = mw.is_loopback(handler)
    allowed = mw.credential_transport_allowed(is_tls, is_loopback)

    assert is_tls is False
    assert is_loopback is False
    assert allowed is False


def test_loopback_plain_allows_credentials():
    """Loopback plain HTTP allows credentials (local development)."""
    handler = MagicMock()
    handler.connection = MagicMock()
    handler.client_address = ("127.0.0.1", 1234)

    is_tls = mw.is_https(handler)
    is_loopback = mw.is_loopback(handler)
    allowed = mw.credential_transport_allowed(is_tls, is_loopback)

    assert is_tls is False
    assert is_loopback is True
    assert allowed is True


def test_tls_lan_allows_credentials():
    """Real TLS on LAN allows credentials."""
    handler = MagicMock()
    handler.connection = MagicMock(spec=ssl.SSLSocket)
    handler.client_address = ("192.168.0.10", 1234)

    is_tls = mw.is_https(handler)
    is_loopback = mw.is_loopback(handler)
    allowed = mw.credential_transport_allowed(is_tls, is_loopback)

    assert is_tls is True
    assert is_loopback is False
    assert allowed is True


def test_loopback_with_proxy_headers_still_allowed():
    """Loopback with misleading proxy headers still allows credentials."""
    handler = MagicMock()
    handler.connection = MagicMock()
    handler.client_address = ("127.0.0.1", 1234)
    handler.headers = {"X-Forwarded-For": "192.168.0.100", "X-Forwarded-Proto": "http"}

    is_tls = mw.is_https(handler)
    is_loopback = mw.is_loopback(handler)
    allowed = mw.credential_transport_allowed(is_tls, is_loopback)

    assert is_tls is False
    assert is_loopback is True
    assert allowed is True