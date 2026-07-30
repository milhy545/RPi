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
from pathlib import Path
from statistics import median


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
        csrf_token = secrets.token_bytes(16).hex()
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
