"""Tests for auth role hierarchy and calibration."""

import hashlib
import json
import stat
import sys
import threading
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


def _patch_auth_store_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "calibrate_pbkdf2", lambda target_ms=200, samples=3: 100_000)


def _make_credential(monkeypatch: pytest.MonkeyPatch, password: str, salt: bytes) -> dict[str, object]:
    _patch_auth_store_password(monkeypatch)
    monkeypatch.setattr(auth.secrets, "token_bytes", lambda size: salt)
    return auth.hash_password(password)


def test_auth_store_is_provisioned_false_when_missing(tmp_path: Path):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)

    assert store.load() == {}
    assert not store.is_provisioned()


def test_auth_store_atomic_write_permissions(tmp_path: Path):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)
    data = {"expert": {"token": "alpha"}}

    store.save(data)

    assert store_path.exists()
    assert store_path.is_file()
    assert stat.S_IMODE(store_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store_path.parent.stat().st_mode) == 0o700
    assert json.loads(store_path.read_text(encoding="utf-8")) == data
    assert auth.AuthStore(store_path).load() == data

    external_data = {"admin": {"token": "bravo"}}
    store_path.write_text(json.dumps(external_data), encoding="utf-8")
    store_path.chmod(0o600)

    assert store.load() == external_data


def test_auth_store_set_and_get_expert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)

    _patch_auth_store_password(monkeypatch)
    store.set_expert("correct horse battery staple")

    assert store.is_provisioned()
    expert = store.get_expert_hash()
    assert expert is not None
    assert auth.verify_password("correct horse battery staple", expert)

    expert["iterations"] = 1
    assert store.get_expert_hash() != expert


def test_auth_store_backup_on_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)
    salts = iter([b"\x01" * 16, b"\x02" * 16])
    monkeypatch.setattr(auth, "calibrate_pbkdf2", lambda target_ms=200, samples=3: 100_000)
    monkeypatch.setattr(auth.secrets, "token_bytes", lambda size: next(salts))

    store.set_expert("correct horse battery staple")
    first_credential = store.get_expert_hash()
    assert first_credential is not None

    store.set_expert("correct horse battery staple")

    backup_path = store_path.with_name("auth.json.bak")
    assert backup_path.exists()
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    assert json.loads(backup_path.read_text(encoding="utf-8"))["expert"] == first_credential
    assert store.get_expert_hash() != first_credential


def test_is_role_provisioned_expert_by_admin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)
    monkeypatch.setattr(auth, "calibrate_pbkdf2", lambda target_ms=200, samples=3: 100_000)
    monkeypatch.setattr(auth.secrets, "token_bytes", lambda size: b"\x03" * 16)

    store.set_admin("admin password")

    credential = store.get_admin_hash()
    assert credential is not None
    assert auth.verify_password("admin password", credential)
    assert store.is_role_provisioned(Role.BASIC)
    assert store.is_role_provisioned(Role.EXPERT)
    assert store.is_role_provisioned(Role.ADMIN)


def test_api_key_create_and_lookup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = auth.AuthStore(tmp_path / "secure" / "auth.json")
    raw_token = "api-token-1"
    monkeypatch.setattr(auth.time, "time", lambda: 1_700_000_001)

    store.create_api_key(raw_token, Role.ADMIN, "first-label")

    assert store.get_api_key_role(raw_token) is Role.ADMIN


def test_api_key_not_stored_plaintext(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)
    raw_token = "plaintext-token"
    monkeypatch.setattr(auth.time, "time", lambda: 1_700_000_002)

    store.create_api_key(raw_token, Role.EXPERT, "no-plaintext")

    contents = store_path.read_text(encoding="utf-8")
    assert raw_token not in contents
    assert raw_token not in json.loads(contents)


def test_api_key_digest_only_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)
    raw_token = "digest-only-token"
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    monkeypatch.setattr(auth.time, "time", lambda: 1_700_000_003)

    store.create_api_key(raw_token, Role.BASIC, "digest-label")

    data = json.loads(store_path.read_text(encoding="utf-8"))
    assert set(data) == {"api_keys"}
    assert set(data["api_keys"]) == {digest}
    record = data["api_keys"][digest]
    assert record == {"role": "basic", "label": "digest-label", "created": 1_700_000_003}


def test_auth_store_concurrent_reads_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = auth.AuthStore(tmp_path / "secure" / "auth.json")
    monkeypatch.setattr(auth.time, "time", lambda: 1_700_000_004)

    barrier = threading.Barrier(10)
    errors: list[BaseException] = []
    error_lock = threading.Lock()
    specs = [
        (f"token-{index}", Role.ADMIN if index % 2 else Role.EXPERT, f"label-{index}")
        for index in range(10)
    ]

    def worker(raw_token: str, role: Role, label: str) -> None:
        try:
            barrier.wait()
            store.create_api_key(raw_token, role, label)
            assert store.load()
            assert store.get_api_key_role(raw_token) is role
        except BaseException as exc:  # pragma: no cover - exercised on failure
            with error_lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=spec) for spec in specs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not any(thread.is_alive() for thread in threads)
    assert not errors

    store_path = tmp_path / "secure" / "auth.json"
    data = json.loads(store_path.read_text(encoding="utf-8"))
    api_keys = data["api_keys"]
    assert len(api_keys) == 10

    for raw_token, role, _label in specs:
        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert digest in api_keys
        assert api_keys[digest]["role"] == role.name.lower()
        assert raw_token not in store_path.read_text(encoding="utf-8")



def test_is_role_provisioned_admin_requires_admin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store_path = tmp_path / "secure" / "auth.json"
    store = auth.AuthStore(store_path)
    credential = _make_credential(monkeypatch, "expert password", b"\x04" * 16)

    store.save({"expert": credential})

    assert store.is_role_provisioned(Role.BASIC)
    assert store.is_role_provisioned(Role.EXPERT)
    assert not store.is_role_provisioned(Role.ADMIN)
