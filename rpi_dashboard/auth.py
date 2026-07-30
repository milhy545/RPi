"""Authentication primitives."""

from __future__ import annotations

import base64
import binascii
import copy
import dataclasses
import hashlib
import hmac
import json
import os
import secrets
import shutil
import tempfile
import threading
import time
from collections.abc import Mapping
from enum import IntEnum
from ipaddress import ip_address, ip_network
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

from config import ALLOWED_SUBNETS


class AuthStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._data: dict[str, object] = {}
        with self._lock:
            self._data = self._load_unlocked()

    def _load_unlocked(self) -> dict[str, object]:
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return {}

        if not isinstance(data, dict):
            raise ValueError("auth store must contain a top-level JSON object")
        return data

    def load(self) -> dict[str, object]:
        with self._lock:
            self._data = self._load_unlocked()
            return copy.deepcopy(self._data)

    def _get_hash_unlocked(self, key: str) -> dict[str, object] | None:
        value = self._data.get(key)
        if isinstance(value, dict):
            return copy.deepcopy(value)
        return None

    def get_expert_hash(self) -> dict[str, object] | None:
        with self._lock:
            return self._get_hash_unlocked("expert")

    def get_admin_hash(self) -> dict[str, object] | None:
        with self._lock:
            return self._get_hash_unlocked("admin")

    def is_role_provisioned(self, role: Role) -> bool:
        with self._lock:
            expert = self._data.get("expert")
            admin = self._data.get("admin")
            if role is Role.BASIC:
                return True
            if role is Role.EXPERT:
                return isinstance(expert, dict) or isinstance(admin, dict)
            if role is Role.ADMIN:
                return isinstance(admin, dict)
            raise ValueError("unknown role")

    def _backup_unlocked(self) -> None:
        if not self._path.exists():
            return

        backup_path = self._path.with_name(f"{self._path.name}.bak")
        shutil.copyfile(self._path, backup_path)
        os.chmod(backup_path, 0o600)
        backup_fd = os.open(backup_path, os.O_RDONLY)
        try:
            os.fsync(backup_fd)
        finally:
            os.close(backup_fd)

    def create_api_key(self, raw_token: str, role: Role, label: str) -> None:
        if not raw_token:
            raise ValueError("raw_token must not be empty")
        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        record = {"role": role.name.lower(), "label": label, "created": int(time.time())}

        with self._lock:
            self._data = self._load_unlocked()
            if self._path.exists():
                self._backup_unlocked()
            payload = copy.deepcopy(self._data)
            api_keys = payload.get("api_keys")
            if not isinstance(api_keys, dict):
                api_keys = {}
                payload["api_keys"] = api_keys
            api_keys[digest] = record
            self._save_unlocked(payload)
            self._data = payload

    def get_api_key_role(self, raw_token: str) -> Role | None:
        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        with self._lock:
            self._data = self._load_unlocked()
            api_keys = self._data.get("api_keys")
            if not isinstance(api_keys, dict):
                return None
            record = api_keys.get(digest)
            if not isinstance(record, dict):
                return None
            role = record.get("role")
            if not isinstance(role, str):
                return None
            try:
                return Role[role.upper()]
            except KeyError:
                return None

    def _save_unlocked(self, data: dict[str, object]) -> None:
        parent = self._path.parent
        created_parent = not parent.exists()
        if created_parent:
            parent.mkdir(parents=True, mode=0o700)
            os.chmod(parent, 0o700)

        temp_fd, temp_name = tempfile.mkstemp(dir=str(parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as handle:
                os.fchmod(handle.fileno(), 0o600)
                json.dump(data, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self._path)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

    def save(self, data: Mapping[str, object]) -> None:
        with self._lock:
            payload = copy.deepcopy(dict(data))
            self._save_unlocked(payload)
            self._data = payload

    def _set_password(self, key: str, password: str) -> None:
        credential = hash_password(password)
        with self._lock:
            self._data = self._load_unlocked()
            if self._path.exists():
                self._backup_unlocked()
            payload = copy.deepcopy(self._data)
            payload[key] = credential
            self._save_unlocked(payload)
            self._data = payload

    def set_expert(self, password: str) -> None:
        self._set_password("expert", password)

    def set_admin(self, password: str) -> None:
        self._set_password("admin", password)

    def is_provisioned(self) -> bool:
        with self._lock:
            expert = self._data.get("expert")
            admin = self._data.get("admin")
            return isinstance(expert, dict) or isinstance(admin, dict)


class Role(IntEnum):
    BASIC = 0
    EXPERT = 1
    ADMIN = 2

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Role):
            return int(self) >= int(other)
        return NotImplemented


_PBKDF2_CANDIDATES = (100_000, 200_000, 400_000, 600_000, 800_000, 1_000_000)
_PBKDF2_MIN_MS = 150.0
_PBKDF2_MAX_MS = 300.0


def _measure_pbkdf2_ms(iterations: int) -> float:
    started = time.perf_counter()
    hashlib.pbkdf2_hmac(
        "sha256",
        b"rpi-dashboard-calibration-password",
        b"rpi-dashboard-calibration-salt",
        iterations,
    )
    return (time.perf_counter() - started) * 1_000


def _median_pbkdf2_ms(iterations: int, samples: int) -> float:
    return float(median(_measure_pbkdf2_ms(iterations) for _ in range(samples)))


def calibrate_pbkdf2(target_ms: int = 200, samples: int = 3) -> int:
    if not _PBKDF2_MIN_MS <= target_ms <= _PBKDF2_MAX_MS:
        raise ValueError("target_ms must be between 150 and 300 milliseconds")
    if samples < 1:
        raise ValueError("samples must be at least 1")

    qualifying = []
    for iterations in _PBKDF2_CANDIDATES:
        measured_ms = _median_pbkdf2_ms(iterations, samples)
        if _PBKDF2_MIN_MS <= measured_ms <= _PBKDF2_MAX_MS:
            qualifying.append((iterations, measured_ms))

    if not qualifying:
        raise RuntimeError(
            "PBKDF2 calibration could not find a safe iteration count; "
            "check target hardware load and retry provisioning"
        )

    selected = min(qualifying, key=lambda result: (abs(result[1] - target_ms), result[0]))[0]
    verified_ms = _median_pbkdf2_ms(selected, samples)
    if not _PBKDF2_MIN_MS <= verified_ms <= _PBKDF2_MAX_MS:
        raise RuntimeError(
            "PBKDF2 calibration verification was unstable; "
            "check target hardware load and retry provisioning"
        )
    return selected


def hash_password(password: str) -> dict[str, object]:
    iterations = calibrate_pbkdf2()
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return {
        "password_hash": base64.b64encode(password_hash).decode("ascii"),
        "salt": base64.b64encode(salt).decode("ascii"),
        "iterations": iterations,
    }


def verify_password(password: str, stored: dict) -> bool:
    try:
        password_hash_b64 = stored["password_hash"]
        salt_b64 = stored["salt"]
        iterations = stored["iterations"]
    except (KeyError, TypeError):
        return False

    if not isinstance(password_hash_b64, str) or not isinstance(salt_b64, str):
        return False
    if type(iterations) is not int or not 100_000 <= iterations <= 1_000_000:
        return False

    try:
        expected_password_hash = base64.b64decode(password_hash_b64, validate=True)
        salt = base64.b64decode(salt_b64, validate=True)
    except (binascii.Error, ValueError):
        return False

    if len(salt) != 16 or len(expected_password_hash) != hashlib.sha256().digest_size:
        return False

    derived_password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(derived_password_hash, expected_password_hash)


@dataclasses.dataclass(frozen=True)
class SessionSnapshot:
    """Immutable snapshot of a session -- never mutated after creation."""
    role: Role
    created: float
    last_seen: float
    csrf_token: str
    step_up_expires: float = 0.0


class _Session:
    """Mutable internal session -- never exposed outside the lock."""

    def __init__(self, role: Role, csrf_token: str, now: float) -> None:
        self.role = role
        self.created = now
        self.last_seen = now
        self.csrf_token = csrf_token
        self.step_up_expires = 0.0

    def to_snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            role=self.role,
            created=self.created,
            last_seen=self.last_seen,
            csrf_token=self.csrf_token,
            step_up_expires=self.step_up_expires,
        )


class SessionStore:
    """In-memory session store with threading.Lock and non-nested acquisition.

    Only the SHA-256 digest of each token is stored server-side; the raw
    token is never persisted.  Public methods acquire the lock once and
    call private ``_unlocked`` helpers only while the caller holds it.
    """

    EXPERT_TTL: int = 28800   # 8 hours sliding window
    ADMIN_TTL: int = 1800     # 30 minutes sliding window
    STEPUP_TTL: int = 300     # 5 minutes fixed window

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, _Session] = {}
        self._time_fn = time.time

    # -- injected clock hook for deterministic tests ---------------------------

    @property
    def _now(self) -> float:
        return self._time_fn()

    # -- private unlocked helpers (caller must hold _lock) ---------------------

    def _session_key(self, cookie_hex: str) -> str | None:
        """Return the storage key, or None if the hex is invalid."""
        try:
            token_bytes = bytes.fromhex(cookie_hex)
        except ValueError:
            return None
        if len(token_bytes) != 32:
            return None
        return hashlib.sha256(token_bytes).hexdigest()

    def _expired_unlocked(self, session: _Session, now: float) -> bool:
        ttl = self.ADMIN_TTL if session.role is Role.ADMIN else self.EXPERT_TTL
        return (now - session.last_seen) > ttl

    def _lookup_unlocked(
        self, cookie_hex: str, now: float
    ) -> tuple[str, _Session] | None:
        """Lookup and expiry check under lock.  Returns (key, session) or None.

        Does NOT refresh last_seen; callers must do that when appropriate.
        """
        key = self._session_key(cookie_hex)
        if key is None:
            return None
        session = self._sessions.get(key)
        if session is None:
            return None
        if self._expired_unlocked(session, now):
            del self._sessions[key]
            return None
        return (key, session)

    # -- public API ------------------------------------------------------------

    def create(self, role: Role) -> tuple[str, SessionSnapshot]:
        """Create a new session and return (cookie_hex, snapshot)."""
        token = secrets.token_bytes(32)
        cookie_hex = token.hex()
        key = hashlib.sha256(token).hexdigest()
        csrf_token = generate_csrf_token().hex()
        now = self._now
        session = _Session(role, csrf_token, now)
        with self._lock:
            self._sessions[key] = session
        return (cookie_hex, session.to_snapshot())

    def validate(
        self, cookie_hex: str
    ) -> tuple[Role | None, SessionSnapshot | None]:
        """Validate a session cookie.

        Returns (role, snapshot) on success, (None, None) if the session
        is missing, expired, or the hex is malformed.  Refreshes the
        sliding-window ``last_seen`` timestamp under the lock.
        """
        now = self._now
        with self._lock:
            result = self._lookup_unlocked(cookie_hex, now)
            if result is None:
                return (None, None)
            _key, session = result
            session.last_seen = now  # sliding window refresh
            return (session.role, session.to_snapshot())

    def step_up(self, cookie_hex: str) -> bool:
        """Elevate an Expert session to Admin for STEPUP_TTL seconds.

        Returns True on success.  The caller must have already verified
        the admin password.
        """
        now = self._now
        with self._lock:
            result = self._lookup_unlocked(cookie_hex, now)
            if result is None:
                return False
            _key, session = result
            if session.role is not Role.EXPERT:
                return False
            session.step_up_expires = now + self.STEPUP_TTL
            session.last_seen = now
            return True

    def effective_role(self, cookie_hex: str) -> Role | None:
        """Return the effective role, considering any active step-up.

        Returns ``ADMIN`` if the session is live and ``step_up_expires``
        has not been reached, otherwise returns the session's original role.
        Returns ``None`` for missing or expired sessions.
        """
        now = self._now
        with self._lock:
            result = self._lookup_unlocked(cookie_hex, now)
            if result is None:
                return None
            _key, session = result
            if session.step_up_expires > 0 and now < session.step_up_expires:
                return Role.ADMIN
            return session.role

    def destroy(self, cookie_hex: str) -> None:
        """Remove a session from the store."""
        key = self._session_key(cookie_hex)
        if key is None:
            return
        with self._lock:
            self._sessions.pop(key, None)

    def cleanup(self) -> int:
        """Remove all expired sessions.  Returns the number removed."""
        now = self._now
        removed = 0
        with self._lock:
            expired = [
                key
                for key, session in self._sessions.items()
                if self._expired_unlocked(session, now)
            ]
            for key in expired:
                del self._sessions[key]
                removed += 1
        return removed


@dataclasses.dataclass(frozen=True)
class RoutePolicy:
    """Policy for a single (path, method) endpoint."""
    required_role: Role | None = None
    mutating: bool = False


# -- Known API routes mapped to (path, method) -> RoutePolicy ---------------

_DEPRECATED_PATHS: frozenset[str] = frozenset({
    "/play",
    "/kodi/st",
    "/kodi/status",
})

_PROTECTED_PREFIXES: tuple[str, ...] = (
    "/audio/", "/bt/", "/wifi/", "/cec/", "/system/", "/terminal/",
    "/dlna/", "/return/", "/mpv/", "/devices/", "/network/",
    "/restart/", "/youtube/", "/media/", "/cache/", "/pool/",
    "/ha/", "/selftest/", "/ws/", "/keepalive",
)

ENDPOINT_ROLES: dict[tuple[str, str], RoutePolicy] = {
    # -- Basic reads (no login, not mutating) --
    ("/modes", "GET"): RoutePolicy(None, False),
    ("/mpv/status", "GET"): RoutePolicy(None, False),
    ("/mpv/memory", "GET"): RoutePolicy(None, False),
    ("/audio/state", "GET"): RoutePolicy(None, False),
    ("/audio/matrix", "GET"): RoutePolicy(None, False),
    ("/audio/bluetooth-profiles", "GET"): RoutePolicy(None, False),
    ("/audio/mute-state", "GET"): RoutePolicy(None, False),
    ("/audio/route/dlna-input/status", "GET"): RoutePolicy(None, False),
    ("/devices/state", "GET"): RoutePolicy(None, False),
    ("/devices", "GET"): RoutePolicy(None, False),
    ("/bt/state", "GET"): RoutePolicy(None, False),
    ("/bt/scan", "GET"): RoutePolicy(None, False),
    ("/bt/controller", "GET"): RoutePolicy(None, False),
    ("/bt/transfers", "GET"): RoutePolicy(None, False),
    ("/bt/files", "GET"): RoutePolicy(None, False),
    ("/bt/diagnostics", "GET"): RoutePolicy(None, False),
    ("/bt/media", "GET"): RoutePolicy(None, False),
    ("/bt/pairing", "GET"): RoutePolicy(None, False),
    ("/bt/capabilities", "GET"): RoutePolicy(None, False),
    ("/bt/phone-role", "GET"): RoutePolicy(None, False),
    ("/wifi/status", "GET"): RoutePolicy(None, False),
    ("/cec/scan", "GET"): RoutePolicy(None, False),
    ("/cec/br/st", "GET"): RoutePolicy(None, False),
    ("/system/stats", "GET"): RoutePolicy(None, False),
    ("/system/hw-stats", "GET"): RoutePolicy(None, False),
    ("/system/status", "GET"): RoutePolicy(None, False),
    ("/system/https-info", "GET"): RoutePolicy(None, False),
    ("/network/info", "GET"): RoutePolicy(None, False),
    ("/network/tailscale", "GET"): RoutePolicy(None, False),
    ("/youtube/cookies/status", "GET"): RoutePolicy(None, False),
    ("/media/preview", "GET"): RoutePolicy(None, False),
    ("/dlna/scan", "GET"): RoutePolicy(None, False),
    ("/dlna/renderer/status", "GET"): RoutePolicy(None, False),
    ("/return/config", "GET"): RoutePolicy(None, False),
    ("/return/last", "GET"): RoutePolicy(None, False),
    ("/cache/stats", "GET"): RoutePolicy(None, False),
    ("/pool/stats", "GET"): RoutePolicy(None, False),
    # -- Basic mutating (no login, but Fetch Metadata / Origin defence) --
    ("/mpv/play", "GET"): RoutePolicy(None, True),
    ("/mpv/stop", "GET"): RoutePolicy(None, True),
    ("/mpv/toggle", "GET"): RoutePolicy(None, True),
    ("/mpv/seek", "GET"): RoutePolicy(None, True),
    ("/mpv/seekabs", "GET"): RoutePolicy(None, True),
    ("/mpv/vol", "GET"): RoutePolicy(None, True),
    ("/mpv/volume", "GET"): RoutePolicy(None, True),
    ("/audio/mute", "GET"): RoutePolicy(None, True),
    ("/return", "POST"): RoutePolicy(None, True),
    ("/report", "POST"): RoutePolicy(None, True),
    # -- Expert mutating --
    ("/mpv/memory-save", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/mpv/memory/clear", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/default-sink", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/volume", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/volume/global", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/matrix/link", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/latency", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/multi-output", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/bt", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/hdmi", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/dlna", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/test", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/route/alexa-bt", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/route/alexa-retarget", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/route/dlna-input/start", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/route/dlna-input/stop", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/route/dlna-input/mode", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/audio/route/dlna-input/target", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/keepalive", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/dlna/select", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/dlna/connect", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/dlna/disconnect", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/dlna/renderer/start", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/dlna/renderer/stop", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/discovery", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/adapter-power", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/discoverable", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/settings", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/device-action", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/device-profile", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/device-autoconnect", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/device-hid", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/operation", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/pair", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/trust", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/connect", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/bt/disconnect", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/wifi/scan", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/wifi/connect", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/wifi/connect", "POST"): RoutePolicy(Role.EXPERT, True),
    ("/cec/send", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/key", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/in", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/br/start", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/br/stop", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/power", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/nav", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/vol", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cec/input", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/devices/bt/scan", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/youtube/age-check", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/cache/clear", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/pool/clear", "GET"): RoutePolicy(Role.EXPERT, True),
    ("/return/config/set", "GET"): RoutePolicy(Role.EXPERT, True),
    # -- Expert read --
    ("/ha/config", "GET"): RoutePolicy(Role.EXPERT, False),
    # -- Admin mutating --
    ("/terminal/connect", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/terminal/disconnect", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/bt/file-send", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/bt/file-cancel", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/bt/remove", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/bt/reset", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/system/restart-mpv", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/system/restart-dashboard", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/system/restart-rpi", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/restart/mpv", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/restart/dashboard", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/restart/rpi", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/system/reboot", "GET"): RoutePolicy(Role.ADMIN, True),
    ("/selftest/testaudio", "GET"): RoutePolicy(Role.ADMIN, True),
    # -- Admin read --
    ("/system/logs", "GET"): RoutePolicy(Role.ADMIN, False),
    ("/ws/token", "GET"): RoutePolicy(Role.ADMIN, False),
}

# -- Helpers ----------------------------------------------------------------


def _is_deprecated(path: str) -> bool:
    """Return True if the path is a known deprecated endpoint."""
    return path in _DEPRECATED_PATHS


def _get_header(headers: Mapping[str, str], name: str) -> str:
    """Case-insensitive header lookup.  Returns empty string when missing."""
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return ""


def classify_request(
    path: str,
    method: str,
    session: SessionSnapshot | None,
    auth_store: AuthStore,
    *,
    effective_role: Role | None = None,
) -> tuple[Role | None, int | None]:
    """Classify a request and return (required_role, error_code).

    Returns ``(required_role, None)`` when the request can proceed
    (subject to further CSRF / transport checks by the gate).
    Returns ``(None, error_code)`` for 405/410, or
    ``(required_role, error_code)`` for 401/403/503.

    Unknown routes that are not in a protected prefix return
    ``(None, None)`` -- the dispatcher should serve 404 normally.

    ``effective_role``
        When supplied (e.g. from ``SessionStore.effective_role()`` or a
        Bearer-derived role), use it for the role-hierarchy check instead
        of ``session.role``.  This allows Expert sessions with active
        Admin step-up, or a bearer credential without any session, to
        satisfy Admin routes.  Pass ``session=None`` together with
        ``effective_role=Role.ADMIN`` for bearer-only Admin access.
        When ``effective_role`` is omitted, ``session.role`` is used.
        If both are absent/missing the request returns 401.
    """
    normalised_method = method.upper()

    # 1. Deprecated check
    if _is_deprecated(path):
        return (None, 410)

    # 2. Lookup exact (path, method)
    policy = ENDPOINT_ROLES.get((path, normalised_method))

    # 3. If not found by exact (path, method), check if path exists
    #    with a different method -> 405
    if policy is None:
        for stored_path, stored_method in ENDPOINT_ROLES:
            if stored_path == path:
                return (None, 405)
        # 4. Check protected prefixes -> default to Admin
        for prefix in _PROTECTED_PREFIXES:
            if path.startswith(prefix):
                required = Role.ADMIN
                if not auth_store.is_role_provisioned(required):
                    return (required, 503)
                role = effective_role if effective_role is not None else (
                    session.role if session is not None else None
                )
                if role is None:
                    return (required, 401)
                if role < required:
                    return (required, 403)
                return (required, None)
        # 5. Unknown route -- return None for normal 404
        return (None, None)

    required_role = policy.required_role

    # Basic route -- always passes
    if required_role is None:
        return (None, None)

    # Role-based route: check provisioning
    if not auth_store.is_role_provisioned(required_role):
        return (required_role, 503)

    # Determine the effective role for the access check
    role = effective_role if effective_role is not None else (
        session.role if session is not None else None
    )
    if role is None:
        return (required_role, 401)

    if role < required_role:
        return (required_role, 403)

    return (required_role, None)


def validate_basic_csrf(
    path: str,
    method: str,
    headers: Mapping[str, str],
    is_loopback: bool,
    allowed_subnets: list[str] | None = None,
) -> bool:
    """Fetch Metadata / Origin defence for Basic mutating routes.

    Only applies when the endpoint is Basic with ``mutating=True``.
    Returns ``True`` if the request passes the defence, ``False`` if it
    should be rejected with 403.
    """
    normalised_method = method.upper()
    policy = ENDPOINT_ROLES.get((path, normalised_method))
    if policy is None or policy.required_role is not None or not policy.mutating:
        return True  # not a Basic mutating route, skip

    if allowed_subnets is None:
        allowed_subnets = list(ALLOWED_SUBNETS)

    sec_fetch_site = _get_header(headers, "Sec-Fetch-Site")
    origin = _get_header(headers, "Origin")
    referer = _get_header(headers, "Referer")

    # Sec-Fetch-Site: cross-site -> reject
    if sec_fetch_site and sec_fetch_site.lower() == "cross-site":
        return False

    # Origin or Referer present -> validate strictly
    if origin or referer:
        source = origin if origin else referer
        return _origin_allowed(source, allowed_subnets)

    # Neither Origin nor Referer
    if is_loopback:
        return True
    # Accept same-origin / same-site via Sec-Fetch-Site if present
    if sec_fetch_site and sec_fetch_site.lower() in ("same-origin", "same-site"):
        return True
    return False


def generate_csrf_token() -> bytes:
    """Generate a CSRF synchroniser token using secrets.token_bytes(16)."""
    return secrets.token_bytes(16)


def validate_csrf(
    session: SessionSnapshot,
    x_csrf_header: str | None,
    rpi_csrf_cookie: str | None,
    origin: str | None,
    referer: str | None,
    sec_fetch_site: str | None,
    is_loopback: bool,
    allowed_subnets: list[str] | None = None,
) -> bool:
    """Validate CSRF token and provenance for Expert/Admin routes.

    Returns True if the request passes CSRF protection.

    Strict absence semantics:
    - ``None`` means absent for cookie, origin, referer, sec_fetch_site.
    - ``None`` is rejected for session, x_csrf_header, is_loopback.
    - Empty or non-string values for any parameter are rejected.
    - ``session`` must be a ``SessionSnapshot`` whose ``csrf_token`` is
      a non-empty 32-character lowercase hexadecimal string.
    - ``allowed_subnets`` after defaulting must be a list of valid
      networks; malformed type/entries reject before any provenance
      check (including loopback).
    - ``is_loopback`` must be an exact ``bool``.
    - All comparisons use ``hmac.compare_digest``.
    """
    # 0. Validate allowed_subnets early (before any provenance logic)
    if allowed_subnets is None:
        allowed_subnets = list(ALLOWED_SUBNETS)
    if not isinstance(allowed_subnets, list):
        return False
    for net in allowed_subnets:
        if not isinstance(net, str) or not net:
            return False
        try:
            ip_network(net)
        except ValueError:
            return False

    # 1. Validate session is a SessionSnapshot with valid csrf_token
    if not isinstance(session, SessionSnapshot):
        return False
    csrf = session.csrf_token
    if not isinstance(csrf, str) or len(csrf) != 32:
        return False
    # Explicit exact character-set check: only 0-9 and a-f allowed
    if not all(ch in "0123456789abcdef" for ch in csrf):
        return False

    # 2. Require non-empty string X-CSRF-Token header
    if not isinstance(x_csrf_header, str) or not x_csrf_header:
        return False

    # 3. Constant-time compare header against session's csrf_token
    if not hmac.compare_digest(x_csrf_header, csrf):
        return False

    # 4. Validate and check rpi_csrf cookie
    #    None = absent; any other value must be non-empty str matching header
    if rpi_csrf_cookie is not None:
        if not isinstance(rpi_csrf_cookie, str) or not rpi_csrf_cookie:
            return False
        if not hmac.compare_digest(x_csrf_header, rpi_csrf_cookie):
            return False

    # 5. Validate sec_fetch_site (None or str)
    if sec_fetch_site is not None and not isinstance(sec_fetch_site, str):
        return False

    # 6. Validate is_loopback (exact bool)
    if not isinstance(is_loopback, bool):
        return False

    # 7. Reject cross-site Sec-Fetch-Site (case-insensitive)
    if isinstance(sec_fetch_site, str) and sec_fetch_site.lower() == "cross-site":
        return False

    # 8. Validate Origin and Referer
    #    None = absent; any other value must be non-empty str and pass _origin_allowed
    if origin is not None:
        if not isinstance(origin, str) or not origin:
            return False
        if not _origin_allowed(origin, allowed_subnets):
            return False

    if referer is not None:
        if not isinstance(referer, str) or not referer:
            return False
        if not _origin_allowed(referer, allowed_subnets):
            return False

    if origin is not None or referer is not None:
        return True

    # 9. Neither Origin nor Referer present
    if is_loopback:
        return True
    if isinstance(sec_fetch_site, str) and sec_fetch_site.lower() in (
        "same-origin",
        "same-site",
    ):
        return True
    return False


def _origin_allowed(source: str, allowed_subnets: list[str]) -> bool:
    """Validate an Origin or Referer URL against allowed subnets.

    Rules (fail-closed):
    - Requires http or https scheme; rejects scheme-relative, ftp, file, data, etc.
    - Rejects URLs containing userinfo (credentials).
    - Parses and validates port: must be absent, empty, or an integer 1-65535.
    - Rejects invalid hostname / IP formats.
    - Accepts ``localhost``, ``* .local``, and any IP within ``allowed_subnets``.
    """
    try:
        parsed = urlparse(source)
    except Exception:
        return False

    # Reject missing or empty hostname
    host = parsed.hostname
    if not host:
        return False

    # Scheme must be http or https; reject scheme-relative (//host), ftp, file, etc.
    scheme = parsed.scheme
    if scheme not in ("http", "https"):
        return False

    # Reject URLs with userinfo (e.g. http://user:pass@host/)
    if parsed.username is not None or parsed.password is not None:
        return False

    # Validate port if present (urlparse.port raises ValueError for
    # non-numeric port strings)
    try:
        port = parsed.port
    except ValueError:
        return False
    # Reject port 0 and out-of-range (port property already ensures 0-65535)
    if port is not None and port == 0:
        return False

    # localhost and *.local are always trusted
    if host == "localhost" or host.endswith(".local"):
        return True

    # IP-based check
    try:
        ip = ip_address(host)
    except ValueError:
        return False
    try:
        return any(ip in ip_network(net) for net in allowed_subnets)
    except ValueError:
        return False
