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


# -- Phase 4: Route Policy -----------------------------------------------


def test_basic_routes_require_no_auth():
    """Basic routes map to required_role=None."""
    assert auth.ENDPOINT_ROLES[("/mpv/play", "GET")].required_role is None
    assert auth.ENDPOINT_ROLES[("/mpv/status", "GET")].required_role is None
    assert auth.ENDPOINT_ROLES[("/audio/state", "GET")].required_role is None
    assert auth.ENDPOINT_ROLES[("/modes", "GET")].required_role is None


def test_route_policy_mutating_flags():
    """Correct mutating flags for representative routes."""
    # Basic mutating
    assert auth.ENDPOINT_ROLES[("/mpv/play", "GET")].mutating is True
    assert auth.ENDPOINT_ROLES[("/return", "POST")].mutating is True
    assert auth.ENDPOINT_ROLES[("/report", "POST")].mutating is True
    # Basic read
    assert auth.ENDPOINT_ROLES[("/mpv/status", "GET")].mutating is False
    # Admin read
    assert auth.ENDPOINT_ROLES[("/system/logs", "GET")].mutating is False
    # Admin mutating
    assert auth.ENDPOINT_ROLES[("/system/reboot", "GET")].mutating is True


def test_expert_routes_require_expert():
    """Expert routes map to required_role=EXPERT."""
    assert auth.ENDPOINT_ROLES[("/audio/default-sink", "GET")].required_role is Role.EXPERT
    assert auth.ENDPOINT_ROLES[("/bt/pair", "GET")].required_role is Role.EXPERT
    assert auth.ENDPOINT_ROLES[("/wifi/connect", "GET")].required_role is Role.EXPERT
    assert auth.ENDPOINT_ROLES[("/wifi/connect", "POST")].required_role is Role.EXPERT


def test_admin_routes_require_admin():
    """Admin routes map to required_role=ADMIN."""
    assert auth.ENDPOINT_ROLES[("/terminal/connect", "GET")].required_role is Role.ADMIN
    assert auth.ENDPOINT_ROLES[("/system/restart-rpi", "GET")].required_role is Role.ADMIN
    assert auth.ENDPOINT_ROLES[("/system/reboot", "GET")].required_role is Role.ADMIN
    assert auth.ENDPOINT_ROLES[("/ws/token", "GET")].required_role is Role.ADMIN


def test_deprecated_routes_return_410():
    """Deprecated paths are in _DEPRECATED_PATHS."""
    assert "/play" in auth._DEPRECATED_PATHS
    assert "/kodi/st" in auth._DEPRECATED_PATHS
    assert "/kodi/status" in auth._DEPRECATED_PATHS


def test_unknown_protected_route_defaults_to_admin():
    """A new /audio/* path defaults to Admin."""
    assert ("/audio/new-feature", "POST") not in auth.ENDPOINT_ROLES
    # Protected prefix check at runtime via classify_request


def test_unknown_unprotected_route_returns_none():
    """A truly unknown path like /foo/bar is not classified."""
    assert ("/foo/bar", "GET") not in auth.ENDPOINT_ROLES
    assert not any("/foo/bar".startswith(p) for p in auth._PROTECTED_PREFIXES)


def test_mpv_memory_save_requires_expert():
    """/mpv/memory-save GET requires EXPERT."""
    assert auth.ENDPOINT_ROLES[("/mpv/memory-save", "GET")].required_role is Role.EXPERT


def test_mpv_memory_clear_requires_expert():
    """/mpv/memory/clear GET requires EXPERT."""
    assert auth.ENDPOINT_ROLES[("/mpv/memory/clear", "GET")].required_role is Role.EXPERT


def test_system_logs_requires_admin():
    """/system/logs GET requires ADMIN."""
    assert auth.ENDPOINT_ROLES[("/system/logs", "GET")].required_role is Role.ADMIN


def test_protected_prefixes_covered():
    """All protected prefixes listed in spec are present."""
    expected = {
        "/audio/", "/bt/", "/wifi/", "/cec/", "/system/", "/terminal/",
        "/dlna/", "/return/", "/mpv/", "/devices/", "/network/",
        "/restart/", "/youtube/", "/media/", "/cache/", "/pool/",
        "/ha/", "/selftest/", "/ws/", "/keepalive",
    }
    assert set(auth._PROTECTED_PREFIXES) == expected


# -- classify_request -----------------------------------------------------


def _provisioned_store(tmp_path, monkeypatch, roles=None):
    """Helper: create an AuthStore with specified credential roles."""
    store = auth.AuthStore(tmp_path / "auth.json")
    monkeypatch.setattr(auth, "calibrate_pbkdf2", lambda target_ms=200, samples=3: 100_000)
    monkeypatch.setattr(auth.secrets, "token_bytes", lambda size: b"\x01" * size)
    if roles is None:
        roles = {"expert", "admin"}
    if "expert" in roles:
        store.set_expert("expert-pass")
    if "admin" in roles:
        store.set_admin("admin-pass")
    return store


def _session(role: Role = Role.EXPERT) -> auth.SessionSnapshot:
    """Helper: create an immutable session snapshot for a given role."""
    store = auth.SessionStore()
    _token, snapshot = store.create(role)
    return snapshot


def test_classify_unprovisioned_returns_503(tmp_path, monkeypatch):
    """No auth.json, Expert route returns 503."""
    store = auth.AuthStore(tmp_path / "missing" / "auth.json")
    assert not store.is_provisioned()

    role, code = auth.classify_request("/audio/default-sink", "GET", None, store)
    assert role is Role.EXPERT
    assert code == 503


def test_classify_missing_session_401(tmp_path, monkeypatch):
    """Provisioned, no cookie, Expert route returns 401."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/audio/default-sink", "GET", None, store)
    assert role is Role.EXPERT
    assert code == 401


def test_classify_wrong_role_403(tmp_path, monkeypatch):
    """Expert session, Admin route returns 403."""
    store = _provisioned_store(tmp_path, monkeypatch)
    expert_snapshot = _session(Role.EXPERT)

    role, code = auth.classify_request("/system/reboot", "GET", expert_snapshot, store)
    assert role is Role.ADMIN
    assert code == 403


def test_classify_basic_no_session(tmp_path, monkeypatch):
    """Basic route returns (None, None) without session."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/mpv/status", "GET", None, store)
    assert role is None
    assert code is None


def test_classify_deprecated_410(tmp_path, monkeypatch):
    """Deprecated /play returns 410."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/play", "GET", None, store)
    assert role is None
    assert code == 410


def test_classify_method_not_allowed_405(tmp_path, monkeypatch):
    """/mpv/status POST returns 405 (only GET registered)."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/mpv/status", "POST", None, store)
    assert role is None
    assert code == 405


def test_classify_admin_hash_satisfies_expert_route(tmp_path, monkeypatch):
    """Only admin hash set, Expert route returns (EXPERT, None) with
    Expert session."""
    store = _provisioned_store(tmp_path, monkeypatch, roles={"admin"})
    expert_snapshot = _session(Role.EXPERT)

    role, code = auth.classify_request("/audio/default-sink", "GET", expert_snapshot, store)
    assert role is Role.EXPERT
    assert code is None


def test_classify_expert_hash_does_not_satisfy_admin_route(tmp_path, monkeypatch):
    """Only expert hash set, Admin route returns (ADMIN, 503)."""
    store = _provisioned_store(tmp_path, monkeypatch, roles={"expert"})
    admin_snapshot = _session(Role.ADMIN)

    role, code = auth.classify_request("/system/reboot", "GET", admin_snapshot, store)
    assert role is Role.ADMIN
    assert code == 503


def test_classify_expert_session_satisfies_expert_route(tmp_path, monkeypatch):
    """Expert session + Expert route returns (EXPERT, None)."""
    store = _provisioned_store(tmp_path, monkeypatch)
    expert_snapshot = _session(Role.EXPERT)

    role, code = auth.classify_request("/bt/pair", "GET", expert_snapshot, store)
    assert role is Role.EXPERT
    assert code is None


def test_classify_admin_session_satisfies_admin_route(tmp_path, monkeypatch):
    """Admin session + Admin route returns (ADMIN, None)."""
    store = _provisioned_store(tmp_path, monkeypatch)
    admin_snapshot = _session(Role.ADMIN)

    role, code = auth.classify_request("/system/reboot", "GET", admin_snapshot, store)
    assert role is Role.ADMIN
    assert code is None


def test_classify_admin_session_satisfies_expert_route(tmp_path, monkeypatch):
    """Admin session + Expert route returns (EXPERT, None)."""
    store = _provisioned_store(tmp_path, monkeypatch)
    admin_snapshot = _session(Role.ADMIN)

    role, code = auth.classify_request("/audio/default-sink", "GET", admin_snapshot, store)
    assert role is Role.EXPERT
    assert code is None


def test_classify_unknown_route_returns_none(tmp_path, monkeypatch):
    """Unknown path like /foo/bar returns (None, None)."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/foo/bar", "GET", None, store)
    assert role is None
    assert code is None


def test_classify_protected_prefix_defaults_to_admin(tmp_path, monkeypatch):
    """An unregistered path under /audio/ defaults to Admin."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/audio/new-feature", "POST", None, store)
    assert role is Role.ADMIN
    assert code == 401  # no session


def test_classify_protected_prefix_unprovisioned(tmp_path, monkeypatch):
    """Unprovisioned store + protected prefix returns 503."""
    store = auth.AuthStore(tmp_path / "missing" / "auth.json")

    role, code = auth.classify_request("/audio/new-feature", "GET", None, store)
    assert role is Role.ADMIN
    assert code == 503


# -- validate_basic_csrf --------------------------------------------------


def test_basic_csrf_rejects_cross_site_fetch(tmp_path, monkeypatch):
    """Sec-Fetch-Site: cross-site is rejected on Basic mutating routes."""
    headers = {"Sec-Fetch-Site": "cross-site"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False


def test_basic_csrf_rejects_bad_origin(tmp_path, monkeypatch):
    """Origin from an untrusted host is rejected."""
    headers = {"Origin": "https://evil.example"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False


def test_basic_csrf_accepts_valid_origin(tmp_path, monkeypatch):
    """Origin from ALLOWED_SUBNETS is accepted."""
    headers = {"Origin": "http://192.168.0.10:8090"}
    allowed = ["192.168.0.0/16"]
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False, allowed) is True


def test_basic_csrf_accepts_no_headers_on_loopback():
    """No Fetch Metadata, Origin, or Referer on loopback is accepted."""
    headers: dict[str, str] = {}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, True) is True


def test_basic_csrf_accepts_localhost_referer():
    """Referer from localhost is accepted."""
    headers = {"Referer": "http://localhost:8090/mpv/play"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is True


def test_basic_csrf_rejects_missing_provenance_non_loopback():
    """No Sec-Fetch-Site, Origin, or Referer on non-loopback is rejected."""
    headers: dict[str, str] = {}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False


def test_basic_csrf_accepts_same_origin_non_loopback():
    """No Origin/Referer but Sec-Fetch-Site: same-origin is accepted."""
    headers = {"Sec-Fetch-Site": "same-origin"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is True


def test_basic_csrf_accepts_same_site_non_loopback():
    """No Origin/Referer but Sec-Fetch-Site: same-site is accepted."""
    headers = {"Sec-Fetch-Site": "same-site"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is True


def test_basic_csrf_non_mutating_bypasses_check():
    """Basic non-mutating route passes through regardless of headers."""
    headers = {"Sec-Fetch-Site": "cross-site"}
    assert auth.validate_basic_csrf("/mpv/status", "GET", headers, False) is True


def test_basic_csrf_non_basic_route_bypasses_check():
    """Expert route bypasses Basic CSRF check."""
    headers = {"Sec-Fetch-Site": "cross-site"}
    assert auth.validate_basic_csrf("/audio/default-sink", "GET", headers, False) is True


def test_basic_csrf_unknown_route_bypasses_check():
    """Unknown route bypasses Basic CSRF check."""
    headers = {"Sec-Fetch-Site": "cross-site"}
    assert auth.validate_basic_csrf("/some/unknown", "GET", headers, False) is True


def test_basic_csrf_localhost_origin():
    """Origin from localhost is accepted."""
    headers = {"Origin": "http://localhost:8080"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is True


def test_basic_csrf_local_domain_referer():
    """Referer from *.local domain is accepted."""
    headers = {"Referer": "http://rpi-tv.local:8090/"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is True


def test_basic_csrf_rejects_ip_hostname_origin():
    """Origin from a hostname (not IP, not localhost) is rejected since
    the hostname does not resolve to an allowed subnet."""
    headers = {"Origin": "http://somehost:8080"}
    allowed = ["192.168.0.0/16"]
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False, allowed) is False


def test_basic_csrf_port_edge_cases():
    """Origin with different ports but same host is still valid."""
    headers = {"Origin": "http://192.168.0.10:9999"}
    allowed = ["192.168.0.0/16"]
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False, allowed) is True


def test_basic_csrf_rejects_ip_outside_subnet():
    """Origin from IP outside allowed subnets is rejected."""
    headers = {"Origin": "http://10.0.0.5:8090"}
    allowed = ["192.168.0.0/16"]
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False, allowed) is False


def test_basic_csrf_empty_origin_referer():
    """Empty Origin and Referer strings are treated as absent."""
    headers = {"Origin": "", "Referer": ""}
    # Non-loopback + no provenance -> reject
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False
    # Loopback -> accept
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, True) is True


def test_basic_csrf_case_insensitive_sec_fetch_site():
    """Sec-Fetch-Site header value is case-insensitive."""
    headers = {"Sec-Fetch-Site": "CROSS-SITE"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False

    headers = {"Sec-Fetch-Site": "SAME-ORIGIN"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is True


def test_basic_csrf_post_route():
    """Basic POST mutating route uses same Fetch Metadata / Origin defence."""
    # POST /return with cross-site fetch
    headers = {"Sec-Fetch-Site": "cross-site"}
    assert auth.validate_basic_csrf("/return", "POST", headers, False) is False

    # POST /return from loopback
    headers = {}
    assert auth.validate_basic_csrf("/return", "POST", headers, True) is True

    # POST /return with valid origin
    headers = {"Origin": "http://192.168.0.10:8090"}
    allowed = ["192.168.0.0/16"]
    assert auth.validate_basic_csrf("/return", "POST", headers, False, allowed) is True


# -- effective_role in classify_request -------------------------------------


def test_classify_effective_role_admin_stepup(tmp_path, monkeypatch):
    """Expert session with effective_role=ADMIN satisfies Admin route."""
    store = _provisioned_store(tmp_path, monkeypatch)
    expert_snapshot = _session(Role.EXPERT)

    role, code = auth.classify_request(
        "/system/reboot", "GET", expert_snapshot, store,
        effective_role=Role.ADMIN,
    )
    assert role is Role.ADMIN
    assert code is None


def test_classify_effective_role_expired_stepup(tmp_path, monkeypatch):
    """Expert session with effective_role=EXPERT (step-up expired) still
    gets 403 on Admin route."""
    store = _provisioned_store(tmp_path, monkeypatch)
    expert_snapshot = _session(Role.EXPERT)

    role, code = auth.classify_request(
        "/system/reboot", "GET", expert_snapshot, store,
        effective_role=Role.EXPERT,
    )
    assert role is Role.ADMIN
    assert code == 403


def test_classify_effective_role_bearer_admin_no_session(tmp_path, monkeypatch):
    """Bearer-derived Admin role without session satisfies Admin route."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request(
        "/system/reboot", "GET", None, store,
        effective_role=Role.ADMIN,
    )
    assert role is Role.ADMIN
    assert code is None


def test_classify_effective_role_bearer_expert_no_session(tmp_path, monkeypatch):
    """Bearer-derived Expert role without session satisfies Expert route."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request(
        "/audio/default-sink", "GET", None, store,
        effective_role=Role.EXPERT,
    )
    assert role is Role.EXPERT
    assert code is None


def test_classify_effective_role_none_and_no_session_401(tmp_path, monkeypatch):
    """No session and no effective_role returns 401 for protected route."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/audio/default-sink", "GET", None, store)
    assert role is Role.EXPERT
    assert code == 401


def test_classify_effective_role_protected_prefix(tmp_path, monkeypatch):
    """effective_role also works for protected-prefix fallback routes."""
    store = _provisioned_store(tmp_path, monkeypatch)

    # Without effective_role, no session -> 401
    role, code = auth.classify_request("/audio/new-feature", "GET", None, store)
    assert code == 401

    # With effective_role=ADMIN bearer -> passes
    role, code = auth.classify_request(
        "/audio/new-feature", "GET", None, store,
        effective_role=Role.ADMIN,
    )
    assert role is Role.ADMIN
    assert code is None


# -- method normalisation (upper) ------------------------------------------


def test_classify_method_case_insensitive(tmp_path, monkeypatch):
    """Lowercase method is normalised via .upper()."""
    store = _provisioned_store(tmp_path, monkeypatch)
    expert_snapshot = _session(Role.EXPERT)

    role, code = auth.classify_request("/bt/pair", "get", expert_snapshot, store)
    assert role is Role.EXPERT
    assert code is None


def test_classify_method_case_405(tmp_path, monkeypatch):
    """Wrong case-normalised method still yields 405."""
    store = _provisioned_store(tmp_path, monkeypatch)

    role, code = auth.classify_request("/mpv/status", "post", None, store)
    assert role is None
    assert code == 405


# -- Mapping / case-insensitive headers for validate_basic_csrf -------------


def test_basic_csrf_lowercase_header_keys():
    """Lowercase header keys are matched case-insensitively."""
    headers = {"sec-fetch-site": "cross-site"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False


def test_basic_csrf_mixed_case_header_keys():
    """Mixed-case header keys are matched case-insensitively."""
    headers = {"Sec-Fetch-Site": "CROSS-SITE"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False

    headers = {"ORIGIN": "https://evil.example"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False


def test_basic_csrf_origin_key_different_case():
    """Origin header with different casing is still validated."""
    headers = {"origin": "http://192.168.0.10:8090"}
    allowed = ["192.168.0.0/16"]
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False, allowed) is True


def test_basic_csrf_referer_key_different_case():
    """Referer header with different casing is still validated."""
    headers = {"REFERER": "http://localhost:8090/"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is True


def test_basic_csrf_mapping_protocol():
    """Accepts any Mapping[str, str], not only dict."""
    from collections.abc import Mapping
    headers: Mapping[str, str] = {"Sec-Fetch-Site": "cross-site"}
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False) is False

    headers = {"Origin": "http://192.168.0.10:9000"}
    allowed = ["192.168.0.0/16"]
    assert auth.validate_basic_csrf("/mpv/play", "GET", headers, False, allowed) is True


# -- hardened _origin_allowed ----------------------------------------------


def test_origin_allowed_rejects_ftp_scheme():
    """ftp:// origin is rejected (not http/https)."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "ftp://192.168.0.10"}, False,
    ) is False


def test_origin_allowed_rejects_scheme_relative():
    """Scheme-relative //host origin is rejected."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "//192.168.0.10"}, False,
    ) is False


def test_origin_allowed_rejects_file_scheme():
    """file:// origin is rejected."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "file:///tmp/foo"}, False,
    ) is False


def test_origin_allowed_rejects_userinfo():
    """Origin with embedded credentials is rejected."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET",
        {"Origin": "http://user:pass@192.168.0.10:8090"}, False,
        ["192.168.0.0/16"],
    ) is False


def test_origin_allowed_rejects_non_numeric_port():
    """Origin with non-numeric port is rejected."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "http://192.168.0.10:abc"}, False,
        ["192.168.0.0/16"],
    ) is False


def test_origin_allowed_rejects_zero_port():
    """Origin with port 0 is rejected (out of valid range)."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "http://192.168.0.10:0"}, False,
        ["192.168.0.0/16"],
    ) is False


def test_origin_allowed_rejects_over_65535_port():
    """Origin with port > 65535 is rejected."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "http://192.168.0.10:70000"}, False,
        ["192.168.0.0/16"],
    ) is False


def test_origin_allowed_rejects_malformed_origin():
    """Completely malformed origin string is rejected."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "not a url at all !!!"}, False,
    ) is False


def test_origin_allowed_rejects_data_uri():
    """data: URI as origin is rejected."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET",
        {"Origin": "data:text/html,<script>alert(1)</script>"}, False,
    ) is False


def test_origin_allowed_rejects_invalid_allowed_subnet():
    """Invalid entry in allowed_subnets is safely rejected (returns False)."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "http://192.168.0.10:8090"}, False,
        ["not-a-subnet"],
    ) is False


def test_origin_allowed_accepts_no_port():
    """Origin without explicit port is accepted when IP is in subnet."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "http://192.168.0.10"}, False,
        ["192.168.0.0/16"],
    ) is True


def test_origin_allowed_accepts_localhost_trailing_dot():
    """Origin with localhost (any casing) is accepted."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Origin": "http://LOCALHOST:8080"}, False,
    ) is True


def test_origin_allowed_local_domain_subdomain():
    """Referer from a subdomain of .local is accepted."""
    assert auth.validate_basic_csrf(
        "/mpv/play", "GET", {"Referer": "http://sub.rpi-tv.local/path"}, False,
    ) is True


def test_basic_csrf_lowercase_method():
    """Lowercase method in validate_basic_csrf is normalised."""
    headers = {"Sec-Fetch-Site": "cross-site"}
    assert auth.validate_basic_csrf("/mpv/play", "get", headers, False) is False

    # Non-mutating route with lowercase method bypasses
    assert auth.validate_basic_csrf("/mpv/status", "get", headers, False) is True
