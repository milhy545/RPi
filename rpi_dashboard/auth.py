"""Authentication primitives."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
import time
from enum import IntEnum
from statistics import median


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
