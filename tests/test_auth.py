"""Tests for auth role hierarchy and calibration."""

import sys
from collections.abc import Callable
from pathlib import Path

import base64

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rpi_dashboard.auth as auth
from rpi_dashboard.auth import Role


def test_role_hierarchy():
    assert Role.ADMIN >= Role.EXPERT >= Role.BASIC
    assert not (Role.BASIC >= Role.EXPERT)


def _mock_calibration_median(iterations: int, samples: int) -> float:
    if iterations == 400_000:
        return 200.0
    if iterations < 400_000:
        return 100.0
    return 350.0


def test_calibrate_pbkdf2_returns_positive_int(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth, "_median_pbkdf2_ms", _mock_calibration_median)

    result = auth.calibrate_pbkdf2()

    assert isinstance(result, int)
    assert result > 0


def test_calibrate_pbkdf2_target_range(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth, "_median_pbkdf2_ms", _mock_calibration_median)

    result = auth.calibrate_pbkdf2()

    assert 100_000 <= result <= 1_000_000


def test_calibrate_pbkdf2_verification_step(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[int, int]] = []

    def fake_median(iterations: int, samples: int) -> float:
        calls.append((iterations, samples))
        return _mock_calibration_median(iterations, samples)

    monkeypatch.setattr(auth, "_median_pbkdf2_ms", fake_median)

    result = auth.calibrate_pbkdf2()

    assert result == 400_000
    assert calls == [
        (100_000, 3),
        (200_000, 3),
        (400_000, 3),
        (600_000, 3),
        (800_000, 3),
        (1_000_000, 3),
        (400_000, 3),
    ]


def test_calibrate_pbkdf2_fails_when_no_candidate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth, "_median_pbkdf2_ms", lambda iterations, samples: 100.0)

    with pytest.raises(RuntimeError, match="retry provisioning"):
        auth.calibrate_pbkdf2()


def _patch_password_calibration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "calibrate_pbkdf2", lambda target_ms=200, samples=3: 100_000)
    monkeypatch.setattr(auth.secrets, "token_bytes", lambda size: b"\x01" * size)


def _make_valid_stored_password(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    _patch_password_calibration(monkeypatch)
    return auth.hash_password("correct horse battery staple")


def test_hash_and_verify_roundtrip(monkeypatch: pytest.MonkeyPatch):
    stored = _make_valid_stored_password(monkeypatch)

    assert auth.verify_password("correct horse battery staple", stored)


def test_verify_wrong_password_fails(monkeypatch: pytest.MonkeyPatch):
    stored = _make_valid_stored_password(monkeypatch)

    assert not auth.verify_password("wrong password", stored)


def test_stored_dict_contains_required_keys(monkeypatch: pytest.MonkeyPatch):
    stored = _make_valid_stored_password(monkeypatch)

    assert set(stored) == {"password_hash", "salt", "iterations"}
    assert isinstance(stored["password_hash"], str)
    assert isinstance(stored["salt"], str)
    assert isinstance(stored["iterations"], int)


Mutation = Callable[[dict[str, object]], dict[str, object]]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda valid_stored: {},
        lambda valid_stored: {**valid_stored, "iterations": True},
        lambda valid_stored: {**valid_stored, "iterations": 99_999},
        lambda valid_stored: {**valid_stored, "password_hash": "not-base64!"},
        lambda valid_stored: {
            **valid_stored,
            "salt": base64.b64encode(b"x" * 15).decode("ascii"),
        },
        lambda valid_stored: {
            **valid_stored,
            "password_hash": base64.b64encode(b"x" * 31).decode("ascii"),
        },
    ],
    ids=[
        "missing-keys",
        "iterations-bool",
        "iterations-too-low",
        "invalid-base64",
        "salt-wrong-length",
        "hash-wrong-length",
    ],
)
def test_verify_password_rejects_malformed_storage(
    monkeypatch: pytest.MonkeyPatch,
    mutation: Mutation,
):
    valid_stored = _make_valid_stored_password(monkeypatch)
    malformed = mutation(valid_stored)

    assert isinstance(malformed, dict)
    assert not auth.verify_password("correct horse battery staple", malformed)
