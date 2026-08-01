"""Route inventory regression test.

Ensures every API route is classified in ENDPOINT_ROLES or explicitly exempt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# --- Data extraction from source files ---

def _get_registered_routes() -> set[tuple[str, str]]:
    """Extract (path, method) from rpi_dashboard/api/routes.py ROUTES dict."""
    content = Path("rpi_dashboard/api/routes.py").read_text()
    routes = set()
    for match in re.finditer(r'"(/[^"]+)"\s*:\s*handle_\w+', Path("rpi_dashboard/api/routes.py").read_text()):
        path = match.group(1)
        routes.add((path, "GET"))
    return routes


def _get_legacy_get_routes() -> set[tuple[str, str]]:
    """Extract legacy GET routes from webserver.py do_GET branches."""
    content = Path("webserver.py").read_text()
    routes = set()
    for match in re.finditer(r'elif path=="/([^"]+)"', Path("webserver.py").read_text()):
        path = "/" + match.group(1)
        if path.startswith("/static/"):
            continue
        routes.add((path, "GET"))
    return routes


def _get_legacy_post_routes() -> set[tuple[str, str]]:
    """Extract legacy POST routes from webserver.py do_POST branches."""
    content = Path("webserver.py").read_text()
    routes = set()
    for match in re.finditer(r'if self\.path == "([^"]+)"', Path("webserver.py").read_text()):
        path = match.group(1)
        routes.add((path, "POST"))
    return routes


def _get_endpoint_roles() -> dict[tuple[str, str], str]:
    """Parse ENDPOINT_ROLES from auth.py."""
    content = Path("rpi_dashboard/auth.py").read_text()
    endpoint_roles = {}
    match = re.search(r"ENDPOINT_ROLES:.*?=.*?{([^}]+)}", Path("rpi_dashboard/auth.py").read_text(), re.DOTALL)
    if match:
        dict_str = match.group(1)
        for match in re.finditer(r'\("(/[^"]+)",\s*"([A-Z]+)"\)\s*:\s*RoutePolicy\(([^,]+)', dict_str):
            path = match.group(1)
            method = match.group(2)
            endpoint_roles[(path, method)] = match.group(3).strip()
    return endpoint_roles


def _get_deprecated_paths() -> set[str]:
    """Extract _DEPRECATED_PATHS from auth.py."""
    content = Path("rpi_dashboard/auth.py").read_text()
    match = re.search(r'_DEPRECATED_PATHS.*?frozenset\(\{([^}]+)\}', content, re.DOTALL)
    if match:
        return set(re.findall(r'"/([^"]+)"', match.group(1)))
    return set()


def _get_protected_prefixes() -> set[str]:
    """Extract _PROTECTED_PREFIXES from auth.py."""
    content = Path("rpi_dashboard/auth.py").read_text()
    match = re.search(r'_PROTECTED_PREFIXES.*?=.*?\(([^)]+)\)', Path("rpi_dashboard/auth.py").read_text(), re.DOTALL)
    if match:
        return set(re.findall(r'"/([^"]+)/"', match.group(1)))
    return set()


# --- The test ---

def test_all_registered_routes_have_role_classification():
    """Ensure every API route is classified in ENDPOINT_ROLES or explicitly exempt."""

    registered = _get_registered_routes()
    legacy_get = _get_legacy_get_routes()
    legacy_post = _get_legacy_post_routes()

    all_routes = registered | legacy_get | legacy_post

    deprecated = _get_deprecated_paths()
    deprecated_with_slash = {f"/{p}" for p in deprecated}
    protected_prefixes = _get_protected_prefixes()

    EXEMPT_PATHS = {
        "/",
        "/index.html",
        "/favicon.ico",
        "/manifest.json",
    }
    EXEMPT_PREFIXES = {"/static/"}

    endpoint_roles = _get_endpoint_roles()

    missing = []
    for path, method in sorted(all_routes):
        if path in EXEMPT_PATHS or any(path.startswith(p) for p in EXEMPT_PREFIXES):
            continue
        if path in deprecated_with_slash:
            continue
        if (path, method) in endpoint_roles:
            continue

        under_prefix = any(path.startswith("/" + p + "/") for p in protected_prefixes)
        if not under_prefix:
            missing.append(f"{method} {path} (no prefix, no explicit role)")

    assert ("/modes", "GET") in endpoint_roles, "/modes GET missing from ENDPOINT_ROLES"
    assert endpoint_roles[("/modes", "GET")] == "None", f"/modes GET expected None, got {endpoint_roles[('/modes', 'GET')]}"

    assert ("/return", "POST") in endpoint_roles, "/return POST missing from ENDPOINT_ROLES"
    assert endpoint_roles[("/return", "POST")] == "None", f"/return POST expected None, got {endpoint_roles[('/return', 'POST')]}"

    assert ("/system/reboot", "GET") in endpoint_roles, "/system/reboot GET missing from ENDPOINT_ROLES"
    assert endpoint_roles[("/system/reboot", "GET")] == "Role.ADMIN", f"/system/reboot GET expected Role.ADMIN, got {endpoint_roles[('/system/reboot', 'GET')]}"

    assert ("/audio/route/dlna-input/status", "GET") in endpoint_roles, "/audio/route/dlna-input/status GET missing from ENDPOINT_ROLES"
    assert endpoint_roles[("/audio/route/dlna-input/status", "GET")] == "None", f"/audio/route/dlna-input/status GET expected None, got {endpoint_roles[('/audio/route/dlna-input/status', 'GET')]}"

    assert ("/bt/discovery", "GET") in endpoint_roles, "/bt/discovery GET missing from ENDPOINT_ROLES"
    assert endpoint_roles[("/bt/discovery", "GET")] == "Role.EXPERT", f"/bt/discovery GET expected Role.EXPERT, got {endpoint_roles[('/bt/discovery', 'GET')]}"

    print(f"Total routes checked: {len(all_routes)}")
    print(f"Explicit ENDPOINT_ROLES entries: {len(_get_endpoint_roles())}")
    print(f"Deprecated paths exempted: {_get_deprecated_paths()}")
    print(f"Protected prefixes: {sorted(_get_protected_prefixes())}")
