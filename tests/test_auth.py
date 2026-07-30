"""Tests for auth role hierarchy and calibration."""

import hashlib
import json
import random
import stat
import statistics as _stats
import sys
import threading
import time
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


# ---- SessionStore -----------------------------------------------------------


def test_session_create_and_validate():
    """Create Expert session, validate returns Expert role and immutable snapshot."""
    store = auth.SessionStore()
    token_hex, snapshot = store.create(Role.EXPERT)

    assert len(token_hex) == 64  # 32 bytes -> 64 hex chars
    assert isinstance(snapshot, auth.SessionSnapshot)
    assert snapshot.role == Role.EXPERT
    assert snapshot.created > 0
    assert snapshot.last_seen > 0
    assert len(snapshot.csrf_token) == 32  # 16 bytes -> 32 hex chars
    assert snapshot.step_up_expires == 0.0

    role, result = store.validate(token_hex)
    assert role is Role.EXPERT
    assert result is not None
    assert result.role == Role.EXPERT
    # last_seen was refreshed by validate
    assert result.last_seen >= snapshot.last_seen
    assert result.csrf_token == snapshot.csrf_token


def test_session_validate_returns_none_for_bad_hex():
    """bytes.fromhex failure returns (None, None) without error."""
    store = auth.SessionStore()
    assert store.validate("not-hex") == (None, None)


def test_session_validate_returns_none_for_unknown_token():
    """Non-existent token returns (None, None)."""
    store = auth.SessionStore()
    assert store.validate("a" * 64) == (None, None)


def test_session_validate_empty_hex():
    """Empty hex string returns (None, None) -- 0 bytes after decode, not 32."""
    store = auth.SessionStore()
    assert store.validate("") == (None, None)


def test_session_validate_short_valid_hex():
    """Valid hex that decodes to fewer than 32 bytes returns (None, None)."""
    store = auth.SessionStore()
    short = "aa" * 16  # 16 bytes, valid hex, wrong length
    assert store.validate(short) == (None, None)


def test_session_validate_oversized_valid_hex():
    """Valid hex that decodes to more than 32 bytes returns (None, None)."""
    store = auth.SessionStore()
    oversized = "bb" * 64  # 64 bytes, valid hex, wrong length
    assert store.validate(oversized) == (None, None)


def test_session_expiry_injected_clock():
    """Advance injected clock past TTL, validate returns None."""
    store = auth.SessionStore()
    fake_time = [1_000_000.0]
    store._time_fn = lambda: fake_time[0]

    token_hex, _snapshot = store.create(Role.EXPERT)

    fake_time[0] += auth.SessionStore.EXPERT_TTL + 1.0

    assert store.validate(token_hex) == (None, None)


def test_session_validate_admin_ttl():
    """Admin session respects ADMIN_TTL (30 min)."""
    store = auth.SessionStore()
    fake_time = [1_000_000.0]
    store._time_fn = lambda: fake_time[0]

    token_hex, _snapshot = store.create(Role.ADMIN)

    fake_time[0] += auth.SessionStore.ADMIN_TTL + 1.0

    assert store.validate(token_hex) == (None, None)


def test_session_sliding_window():
    """Validate refreshes last_seen, keeping session alive past original TTL."""
    store = auth.SessionStore()
    fake_time = [1_000_000.0]
    store._time_fn = lambda: fake_time[0]

    token_hex, _snapshot = store.create(Role.EXPERT)

    # Advance most of the way through TTL
    fake_time[0] += auth.SessionStore.EXPERT_TTL - 10.0

    role, snapshot = store.validate(token_hex)
    assert role is Role.EXPERT
    assert snapshot is not None
    # last_seen was refreshed
    assert snapshot.last_seen == fake_time[0]

    # Now advance another chunk -- still valid because sliding window reset
    fake_time[0] += auth.SessionStore.EXPERT_TTL - 10.0

    role, snapshot = store.validate(token_hex)
    assert role is Role.EXPERT
    assert snapshot is not None

    # Advance past TTL from last refresh
    fake_time[0] += auth.SessionStore.EXPERT_TTL + 1.0

    assert store.validate(token_hex) == (None, None)


def test_session_step_up():
    """step_up on live Expert session makes effective_role return Admin."""
    store = auth.SessionStore()
    fake_time = [1_000_000.0]
    store._time_fn = lambda: fake_time[0]

    token_hex, _snapshot = store.create(Role.EXPERT)

    assert store.step_up(token_hex) is True

    # validate still returns the original role
    role, snapshot = store.validate(token_hex)
    assert role is Role.EXPERT
    assert snapshot is not None
    assert snapshot.step_up_expires == fake_time[0] + auth.SessionStore.STEPUP_TTL

    # effective_role reflects the step-up
    assert store.effective_role(token_hex) is Role.ADMIN


def test_session_step_up_expiry():
    """Advance past STEPUP_TTL, effective_role reverts to Expert."""
    store = auth.SessionStore()
    fake_time = [1_000_000.0]
    store._time_fn = lambda: fake_time[0]

    token_hex, _snapshot = store.create(Role.EXPERT)
    store.step_up(token_hex)

    fake_time[0] += auth.SessionStore.STEPUP_TTL + 1.0

    # Session itself is still alive (Expert TTL >> STEPUP_TTL)
    role, snapshot = store.validate(token_hex)
    assert role is Role.EXPERT
    assert snapshot is not None

    # But step-up has expired
    effective = store.effective_role(token_hex)
    assert effective is Role.EXPERT


def test_session_step_up_non_expert_fails():
    """step_up on Admin session returns False (only Expert can step up)."""
    store = auth.SessionStore()
    token_hex, _snapshot = store.create(Role.ADMIN)

    assert store.step_up(token_hex) is False


def test_session_step_up_on_expired_session():
    """step_up on expired Expert session returns False."""
    store = auth.SessionStore()
    fake_time = [1_000_000.0]
    store._time_fn = lambda: fake_time[0]

    token_hex, _snapshot = store.create(Role.EXPERT)

    fake_time[0] += auth.SessionStore.EXPERT_TTL + 1.0

    assert store.step_up(token_hex) is False


def test_session_destroy():
    """Validate after destroy returns None."""
    store = auth.SessionStore()

    token_hex, _snapshot = store.create(Role.EXPERT)
    store.destroy(token_hex)

    assert store.validate(token_hex) == (None, None)


def test_session_destroy_bad_hex():
    """destroy with bad hex does not raise."""
    store = auth.SessionStore()
    store.destroy("not-hex")  # must not raise


def test_session_cleanup():
    """cleanup removes expired sessions and returns count."""
    store = auth.SessionStore()
    fake_time = [1_000_000.0]
    store._time_fn = lambda: fake_time[0]

    # Create Expert sessions early
    exp_tokens = [store.create(Role.EXPERT)[0] for _ in range(3)]

    # Advance past most of Expert TTL, then create Admin sessions
    fake_time[0] += auth.SessionStore.EXPERT_TTL - 100.0
    adm_tokens = [store.create(Role.ADMIN)[0] for _ in range(2)]

    # None expired yet (Expert barely alive, Admin fresh)
    assert store.cleanup() == 0

    # Advance far enough that Expert expires but Admin stays within TTL
    fake_time[0] += 200.0  # Expert: (28800 - 100) + 200 = 28900 > 28800
    # Admin: 200 < 1800, still alive

    # 3 Expert sessions expired, 2 Admin still alive
    assert store.cleanup() == 3

    # Now validate the survivors
    for t in adm_tokens:
        role, _snap = store.validate(t)
        assert role is Role.ADMIN

    # Advance past Admin TTL
    fake_time[0] += auth.SessionStore.ADMIN_TTL + 1.0

    assert store.cleanup() == 2

    for t in exp_tokens:
        assert store.validate(t) == (None, None)


def test_session_create_admin():
    """Create Admin session, validate returns Admin."""
    store = auth.SessionStore()

    token_hex, snapshot = store.create(Role.ADMIN)
    assert snapshot.role == Role.ADMIN

    role, result = store.validate(token_hex)
    assert role is Role.ADMIN


def test_session_effective_role_nonexistent():
    """effective_role on unknown/bad token returns None."""
    store = auth.SessionStore()

    assert store.effective_role("a" * 64) is None
    assert store.effective_role("not-hex") is None


def test_session_snapshot_immutable():
    """Returned SessionSnapshot cannot be mutated (frozen dataclass)."""
    store = auth.SessionStore()
    _token, snapshot = store.create(Role.EXPERT)

    with pytest.raises(AttributeError):
        snapshot.role = Role.ADMIN  # type: ignore[misc]


def test_session_digest_only_storage():
    """Raw token is never stored server-side; only SHA-256 digest is kept."""
    store = auth.SessionStore()

    token_hex, _snapshot = store.create(Role.EXPERT)

    # The raw token bytes should not appear in _sessions
    raw_bytes = bytes.fromhex(token_hex)
    digest = hashlib.sha256(raw_bytes).hexdigest()

    with store._lock:
        assert digest in store._sessions
        # The raw token must NOT be a key
        assert raw_bytes.hex() not in store._sessions


def test_session_concurrent_create_validate_destroy():
    """20 threads performing random create/validate/destroy without corruption."""
    store = auth.SessionStore()
    barrier = threading.Barrier(20)
    errors: list[BaseException] = []
    error_lock = threading.Lock()

    def worker(seed: int) -> None:
        try:
            rng = random.Random(seed)
            my_tokens: list[str] = []
            barrier.wait()
            for _ in range(30):
                op = rng.randint(0, 2)
                if op == 0:
                    role = Role.ADMIN if rng.randint(0, 1) else Role.EXPERT
                    t, _s = store.create(role)
                    my_tokens.append(t)
                elif op == 1 and my_tokens:
                    store.validate(rng.choice(my_tokens))
                elif op == 2 and my_tokens:
                    idx = rng.randint(0, len(my_tokens) - 1)
                    store.destroy(my_tokens.pop(idx))
        except BaseException as exc:
            with error_lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert not errors, f"Errors: {errors}"
    assert not any(t.is_alive() for t in threads)


def test_session_benchmark_on_rpi(capsys: pytest.CaptureFixture[str]):
    """Run 1000 validate calls; report median/p95 for manual review.

    On target RPi hardware this should report median <= 1 ms, p95 <= 5 ms.
    On development hardware absolute values vary; this test prints results
    without asserting strict thresholds to avoid flakiness.
    """
    store = auth.SessionStore()
    token_hex, _snapshot = store.create(Role.EXPERT)

    # Warm-up
    store.validate(token_hex)

    timings: list[float] = []
    for _ in range(1000):
        start = time.perf_counter()
        store.validate(token_hex)
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    timings.sort()
    median_s = _stats.median(timings)
    p95_s = timings[int(len(timings) * 0.95)]

    print("\n  Session validation benchmark (1000 calls):")
    print(f"  median = {median_s * 1000:.3f} ms  p95 = {p95_s * 1000:.3f} ms")
    print("  RPi target: median <= 1 ms, p95 <= 5 ms")

    # Sanity guard -- even on slow development hardware, a single sha256
    # digest + locked dict lookup must never take > 500 ms per call.
    assert p95_s < 0.5, (
        f"p95={p95_s * 1000:.1f} ms exceeds 500 ms sanity ceiling -- "
        f"check for accidental PBKDF / I/O in hot path"
    )

    # Captured for separate evidence output
    captured = capsys.readouterr()
    assert "median" in captured.out
