"""Shared API middleware helpers for RPi-TV Dashboard."""

from ipaddress import ip_address, ip_network
from time import monotonic
from typing import MutableMapping, Optional, Sequence
from urllib.parse import urlparse


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
