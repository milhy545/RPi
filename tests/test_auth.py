"""Tests for auth role hierarchy and calibration."""

import sys
from pathlib import Path

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
