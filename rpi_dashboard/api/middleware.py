"""Shared API middleware helpers for RPi-TV Dashboard."""

from __future__ import annotations

import http.cookies
import ssl
from ipaddress import ip_address, ip_network
from time import monotonic
from typing import TYPE_CHECKING, Mapping, MutableMapping, Optional, Protocol, Sequence
from urllib.parse import urlparse

if TYPE_CHECKING:
    from rpi_dashboard.auth import AuthStore, Role


class _Request(Protocol):
    """Minimal request protocol: headers is a mapping with get()."""
    headers: Mapping[str, str]


def is_allowed_ip(client_ip: str, allowed_subnets: Sequence[str]) -> bool:
    """Return True when client_ip belongs to one of allowed_subnets."""
    try:
        ip = ip_address(client_ip)
    except ValueError:
        return False
    return any(ip in ip_network(net) for net in allowed_subnets)


def allowed_cors_origin(
    origin: Optional[str],
    allowed_subnets: Sequence[str],
    fallback: str = "http://localhost",
) -> str:
    """Return the origin to emit for CORS headers."""
    if not origin:
        return fallback
    try:
        parsed = urlparse(origin)
        host = parsed.hostname
    except Exception:
        return fallback
    if not host:
        return fallback
    if host == "localhost" or host.endswith(".local") or is_allowed_ip(host, allowed_subnets):
        return origin
    return fallback


def check_rate_limit(
    client_ip: str,
    cache: MutableMapping[str, float],
    *,
    now: Optional[float] = None,
    window_seconds: float,
) -> bool:
    """Return True when the request is allowed and update cache."""
    current = monotonic() if now is None else now
    last = cache.get(client_ip, 0)
    if current - last < window_seconds:
        return False
    cache[client_ip] = current
    return True


def is_https(handler) -> bool:
    """Return True iff the connection is a real TLS socket.

    Checks handler.connection and handler.request directly; both may be the
    socket in BaseHTTPRequestHandler. Never trusts proxy headers.
    """
    conn = getattr(handler, "connection", None)
    if isinstance(conn, ssl.SSLSocket):
        return True
    req = getattr(handler, "request", None)
    if isinstance(req, ssl.SSLSocket):
        return True
    return False


def is_loopback(handler) -> bool:
    """Return True when the request originates from loopback (127.0.0.0/8, ::1)."""
    addr = getattr(handler, "client_address", None)
    if not addr:
        return False
    client_ip = addr[0] if isinstance(addr, (list, tuple)) and addr else str(addr)
    try:
        return ip_address(client_ip).is_loopback
    except ValueError:
        return False


def credential_transport_allowed(is_tls: bool, is_loopback: bool) -> bool:
    """Return True when credentials may be accepted (TLS or loopback)."""
    return is_tls or is_loopback


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract token from 'Bearer <token>' header (case-insensitive scheme)."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1] if parts[1] else None


def extract_session_cookie(request: _Request) -> Optional[str]:
    """Return the 'rpi_session' cookie value from request headers, or None."""
    cookie_header = request.headers.get("Cookie")
    if not cookie_header:
        return None
    try:
        cookie = http.cookies.SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get("rpi_session")
        return morsel.value if morsel else None
    except Exception:
        return None


def extract_bearer_role(request: _Request, auth_store: "AuthStore") -> "Role | None":
    """Return Role from API key in Authorization header, or None."""
    auth = request.headers.get("Authorization")
    token = _extract_bearer_token(auth)
    if not token:
        return None
    return auth_store.get_api_key_role(token)


def set_session_cookie(
    handler,
    token_hex: str,
    max_age: int,
    is_tls: bool,
) -> None:
    """Set session cookie: HttpOnly, SameSite=Lax, Path=/, Secure only on TLS."""
    cookie = (
        f"rpi_session={token_hex}; HttpOnly; SameSite=Lax; Path=/; Max-Age={max_age}"
    )
    if is_tls:
        cookie += "; Secure"
    handler.send_header("Set-Cookie", cookie)


def set_csrf_cookie(
    handler,
    csrf_hex: str,
    is_tls: bool,
) -> None:
    """Set CSRF cookie: non-HttpOnly, SameSite=Strict, Path=/, Secure only on TLS."""
    cookie = f"rpi_csrf={csrf_hex}; SameSite=Strict; Path=/"
    if is_tls:
        cookie += "; Secure"
    handler.send_header("Set-Cookie", cookie)