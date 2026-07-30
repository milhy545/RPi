"""Tests for LoginAttemptLimiter (Phase 5b)."""

import threading


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rpi_dashboard.auth import LoginAttemptLimiter


def test_login_limiter_allows_first_five():
    """Five attempts from the same IP succeed (all return True)."""
    limiter = LoginAttemptLimiter(clock=lambda: 1000.0)

    for _ in range(5):
        assert limiter.check_and_record("192.168.0.1") is True


def test_login_limiter_blocks_sixth():
    """Sixth attempt within 60s returns False."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    for _ in range(5):
        assert limiter.check_and_record("192.168.0.1") is True

    assert limiter.check_and_record("192.168.0.1") is False


def test_login_limiter_independent_ips():
    """Different IPs tracked separately."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    for _ in range(5):
        assert limiter.check_and_record("192.168.0.1") is True
    assert limiter.check_and_record("192.168.0.1") is False

    # Different IP still has full quota
    for _ in range(5):
        assert limiter.check_and_record("192.168.0.2") is True
    assert limiter.check_and_record("192.168.0.2") is False


def test_login_limiter_expiry():
    """After 60s window, count resets."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    for _ in range(5):
        assert limiter.check_and_record("192.168.0.1") is True
    assert limiter.check_and_record("192.168.0.1") is False

    # Advance past the window
    clock[0] += 61.0

    # Should be allowed again
    assert limiter.check_and_record("192.168.0.1") is True


def test_login_limiter_concurrent():
    """10 threads calling check_and_record in parallel for one IP."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    barrier = threading.Barrier(10)
    results: list[bool] = []
    results_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        result = limiter.check_and_record("192.168.0.1")
        with results_lock:
            results.append(result)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(results) == 10
    # Exactly 5 should succeed, 5 should fail
    assert results.count(True) == 5
    assert results.count(False) == 5


def test_login_limiter_storage_bounded():
    """Internal bucket count never exceeds 1024; oldest evicted."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    # Fill up to MAX_BUCKETS (1024)
    for i in range(1024):
        ip = f"10.0.{i // 256}.{i % 256}"
        assert limiter.check_and_record(ip) is True

    with limiter._lock:
        assert len(limiter._buckets) == 1024

    # Add one more unique IP - should evict oldest
    clock[0] += 1.0
    assert limiter.check_and_record("192.168.100.1") is True

    with limiter._lock:
        assert len(limiter._buckets) == 1024
        assert "10.0.0.0" not in limiter._buckets
        assert "192.168.100.1" in limiter._buckets


def test_login_limiter_boundary_at_60_seconds():
    """Attempt at exactly 60 seconds after oldest is expired."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    # 5 attempts
    for _ in range(5):
        assert limiter.check_and_record("192.168.0.1") is True

    # At exactly 60 seconds later, the first attempt should be expired
    clock[0] = 1060.0
    # Window is now (1000.0, 1060.0], so 1000.0 is expired
    # 4 remain in window, so 5th should succeed
    assert limiter.check_and_record("192.168.0.1") is True


def test_login_limiter_global_expired_bucket_purge_before_eviction():
    """Expired buckets purged globally at exact 60s boundary."""
    clock = [0.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    # Two old IPs at clock=0
    limiter.check_and_record("10.0.0.1")
    limiter.check_and_record("10.0.0.2")

    # One live IP at clock=1
    clock[0] = 1.0
    limiter.check_and_record("10.0.0.3")

    # Advance to exact boundary: 60 seconds after clock=0
    clock[0] = 60.0
    # New IP should trigger global purge
    assert limiter.check_and_record("192.168.1.1") is True

    with limiter._lock:
        # Both clock-0 buckets globally deleted at exact boundary
        assert "10.0.0.1" not in limiter._buckets
        assert "10.0.0.2" not in limiter._buckets
        # Clock-1 bucket remains
        assert "10.0.0.3" in limiter._buckets
        # New bucket exists
        assert "192.168.1.1" in limiter._buckets
        # Total count is 2
        assert len(limiter._buckets) == 2


def test_login_limiter_clock_called_once_per_invocation():
    """Injected clock is called exactly once per check_and_record."""
    call_count = [0]

    def clock() -> float:
        call_count[0] += 1
        return 1000.0

    limiter = LoginAttemptLimiter(clock=clock)
    limiter.check_and_record("1.2.3.4")
    limiter.check_and_record("1.2.3.4")

    assert call_count[0] == 2


def test_login_limiter_rejects_empty_ip():
    """Empty string IP is rejected."""
    limiter = LoginAttemptLimiter(clock=lambda: 1000.0)
    assert limiter.check_and_record("") is False


def test_login_limiter_rejects_non_string_ip():
    """Non-string IP is rejected."""
    limiter = LoginAttemptLimiter(clock=lambda: 1000.0)
    assert limiter.check_and_record(123) is False  # type: ignore[arg-type]
    assert limiter.check_and_record(None) is False  # type: ignore[arg-type]
    assert limiter.check_and_record(b"1.2.3.4") is False  # type: ignore[arg-type]


def test_login_limiter_eviction_deterministic_oldest_timestamp():
    """Eviction always removes bucket with oldest first timestamp."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    # Add 1024 IPs with strictly increasing timestamps
    for i in range(1024):
        clock[0] = float(i)
        limiter.check_and_record(f"10.0.{i // 256}.{i % 256}")

    # Oldest is "10.0.0.0" at timestamp 0.0
    clock[0] = 1024.0
    limiter.check_and_record("192.168.1.1")

    with limiter._lock:
        assert "10.0.0.0" not in limiter._buckets
        assert "192.168.1.1" in limiter._buckets


def test_login_limiter_eviction_tie_break_by_insertion_order():
    """When timestamps equal, dict insertion order breaks ties."""
    clock = [1000.0]
    limiter = LoginAttemptLimiter(clock=lambda: clock[0])

    # Add 1024 IPs all at same timestamp
    for i in range(1024):
        limiter.check_and_record(f"10.0.{i // 256}.{i % 256}")

    # All have timestamp 1000.0, first inserted is "10.0.0.0"
    clock[0] = 2000.0
    limiter.check_and_record("192.168.1.1")

    with limiter._lock:
        assert "10.0.0.0" not in limiter._buckets
        assert "192.168.1.1" in limiter._buckets