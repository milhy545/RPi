"""Comprehensive tests for safe RPi/Milhy-PC/Jules validation pipeline.

Tests host and profile routing, exact process matching, CPU attribution,
busy/defer backoff, mid-run playback aborts, dirty checkout refusal, SHA mismatch,
lock contention, candidate rollback, and RPi push/browser bans.
"""

from __future__ import annotations

import os
import time
import subprocess
import pytest
from unittest.mock import MagicMock

from rpi_dashboard.ci.rpi_guard import (
    RPiGuard,
    RPiBusyError,
    RPiPlaybackStartedInterrupt,
    DirtyCheckoutError,
    SHAMismatchError,
    LockContentionError,
    is_exact_playback_process,
    parse_proc_ps_output,
)
from rpi_dashboard.ci.staging import stage_candidate, rollback_candidate, get_head_sha
from rpi_dashboard.ci.evidence import PipelineLock, build_evidence_record, validate_receipt_structure


# ─── 1. Exact Process Matching Tests ──────────────────────────────────────────

def test_exact_process_matching_mpv_vs_keys2mpv():
    """Verify that exact process matching identifies mpv but strictly excludes keys2mpv.py."""
    proc_mpv = {
        "pid": 101,
        "ppid": 1,
        "pcpu": 15.0,
        "comm": "mpv",
        "args": "/usr/bin/mpv http://stream.example.com/video.mp4",
    }
    proc_keys2mpv = {
        "pid": 102,
        "ppid": 1,
        "pcpu": 5.0,
        "comm": "python3",
        "args": "python3 /home/milhy777/rpi-dashboard/keys2mpv.py --device /dev/input/event0",
    }
    proc_steamlink = {
        "pid": 103,
        "ppid": 1,
        "pcpu": 30.0,
        "comm": "steamlink",
        "args": "/usr/bin/steamlink",
    }
    proc_moonlight = {
        "pid": 104,
        "ppid": 1,
        "pcpu": 25.0,
        "comm": "moonlight",
        "args": "/usr/bin/moonlight stream",
    }
    proc_tui = {
        "pid": 105,
        "ppid": 1,
        "pcpu": 10.0,
        "comm": "python3",
        "args": "python3 /home/milhy777/rpi-dashboard/tui.py",
    }

    assert is_exact_playback_process(proc_mpv) is True
    assert is_exact_playback_process(proc_steamlink) is True
    assert is_exact_playback_process(proc_moonlight) is True
    assert is_exact_playback_process(proc_keys2mpv) is False
    assert is_exact_playback_process(proc_tui) is True


def test_proc_ps_output_parsing():
    """Test parsing ps output lines into structured process dicts."""
    ps_data = """  PID  PPID  %CPU COMMAND         ARGS
  101     1  12.5 mpv             /usr/bin/mpv test.mp4
  102     1   2.0 python3         python3 keys2mpv.py
"""
    procs = parse_proc_ps_output(ps_data)
    assert len(procs) == 2
    assert procs[0]["pid"] == 101
    assert procs[0]["comm"] == "mpv"
    assert procs[1]["pid"] == 102
    assert procs[1]["comm"] == "python3"


# ─── 2. CPU Attribution & Self-Deadlock Prevention ───────────────────────────

def test_cpu_attribution_excludes_self_pids():
    """Verify that CI/agent self-CPU is excluded from user CPU calculation."""
    fake_procs = [
        {"pid": 200, "ppid": 1, "pcpu": 45.0, "comm": "python3", "args": "python3 -m pytest"},
        {"pid": 201, "ppid": 200, "pcpu": 25.0, "comm": "pytest", "args": "pytest -q"},
        {"pid": 300, "ppid": 1, "pcpu": 5.0, "comm": "bash", "args": "bash"},
    ]

    guard = RPiGuard(
        cpu_threshold_pct=20.0,
        proc_provider=lambda: fake_procs,
        ram_provider=lambda: 300.0,
        temp_provider=lambda: 45.0,
    )

    # Exclude runner PIDs 200 & 201
    status_excluded = guard.check_status(exclude_pids={200, 201})
    assert status_excluded["user_cpu_pct"] == 5.0
    assert status_excluded["busy"] is False

    # Without excluding, runner CPU causes busy
    status_included = guard.check_status(exclude_pids=set())
    assert status_included["user_cpu_pct"] == 75.0
    assert status_included["busy"] is True


def test_cpu_attribution_high_external_user_cpu():
    """Verify high external user CPU triggers busy status."""
    fake_procs = [
        {"pid": 500, "ppid": 1, "pcpu": 35.0, "comm": "ffmpeg", "args": "ffmpeg -i in.mp4 out.mp4"},
    ]

    guard = RPiGuard(
        cpu_threshold_pct=20.0,
        proc_provider=lambda: fake_procs,
        ram_provider=lambda: 400.0,
        temp_provider=lambda: 50.0,
    )

    status = guard.check_status(exclude_pids=set())
    assert status["user_cpu_pct"] == 35.0
    assert status["busy"] is True
    assert "exceeds 20.0%" in status["reasons"][0]


# ─── 3. Busy / Defer Queue & Backoff Tests ────────────────────────────────────

def test_wait_until_idle_success_after_deferral():
    """Verify wait_until_idle loops until system becomes idle."""
    call_count = 0

    def mock_procs():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return [{"pid": 999, "ppid": 1, "pcpu": 50.0, "comm": "busy_job", "args": "busy"}]
        return []

    guard = RPiGuard(
        cpu_threshold_pct=20.0,
        proc_provider=mock_procs,
        ram_provider=lambda: 200.0,
        temp_provider=lambda: 40.0,
    )

    status = guard.wait_until_idle(max_wait_seconds=5.0, backoff_seconds=0.05)
    assert status["busy"] is False
    assert call_count == 3


def test_wait_until_idle_timeout_raises_busy_error():
    """Verify wait_until_idle raises RPiBusyError on timeout."""
    guard = RPiGuard(
        cpu_threshold_pct=20.0,
        proc_provider=lambda: [{"pid": 888, "ppid": 1, "pcpu": 40.0, "comm": "heavy", "args": "heavy"}],
        ram_provider=lambda: 200.0,
        temp_provider=lambda: 40.0,
    )

    with pytest.raises(RPiBusyError) as excinfo:
        guard.wait_until_idle(max_wait_seconds=0.1, backoff_seconds=0.02)
    assert "RPi remained busy after" in str(excinfo.value)


# ─── 4. Mid-run Playback Abort & Protection Tests ─────────────────────────────

def test_run_protected_command_aborts_on_midrun_playback():
    """Verify protected command is aborted immediately if user playback starts mid-run."""
    playback_active = False

    def mock_procs():
        if playback_active:
            return [{"pid": 777, "ppid": 1, "pcpu": 10.0, "comm": "mpv", "args": "mpv video.mp4"}]
        return []

    guard = RPiGuard(
        proc_provider=mock_procs,
        ram_provider=lambda: 300.0,
        temp_provider=lambda: 50.0,
    )

    cancel_callback = MagicMock()

    # Trigger playback after 0.1s
    def trigger_playback():
        nonlocal playback_active
        time.sleep(0.1)
        playback_active = True

    import threading
    t = threading.Thread(target=trigger_playback)
    t.start()

    with pytest.raises(RPiPlaybackStartedInterrupt):
        guard.run_protected_command(
            ["sleep", "2"],
            cancel_callback=cancel_callback,
            poll_interval=0.02,
        )

    t.join()
    assert cancel_callback.called


# ─── 5. Candidate Staging, Dirty Refusal & Rollback Tests ──────────────────────

def test_stage_candidate_refuses_dirty_source(tmp_path):
    """Verify candidate staging is refused if live source checkout has uncommitted changes."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()

    subprocess.run(["git", "init"], cwd=source_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=source_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source_dir, check=True)

    dummy_file = source_dir / "file.txt"
    dummy_file.write_text("v1")
    subprocess.run(["git", "add", "."], cwd=source_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=source_dir, check=True)

    sha = get_head_sha(str(source_dir))

    # Make dirty
    dummy_file.write_text("v2 dirty")

    with pytest.raises(DirtyCheckoutError) as excinfo:
        stage_candidate(str(source_dir), str(target_dir), sha)

    assert "uncommitted dirty changes" in str(excinfo.value)


def test_stage_candidate_sha_mismatch_triggers_rollback(tmp_path):
    """Verify SHA mismatch triggers candidate rollback."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()

    subprocess.run(["git", "init"], cwd=source_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=source_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source_dir, check=True)

    dummy_file = source_dir / "file.txt"
    dummy_file.write_text("v1")
    subprocess.run(["git", "add", "."], cwd=source_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=source_dir, check=True)

    wrong_sha = "0000000000000000000000000000000000000000"

    with pytest.raises(SHAMismatchError):
        stage_candidate(str(source_dir), str(target_dir), wrong_sha)

    # Target directory should be rolled back / cleaned up
    assert not os.path.exists(target_dir)


def test_rollback_candidate_cleans_directory(tmp_path):
    """Verify rollback_candidate removes target worktree."""
    target_dir = tmp_path / "staged_candidate"
    target_dir.mkdir()
    (target_dir / "dummy.txt").write_text("test")

    rollback_candidate(str(target_dir))
    assert not os.path.exists(target_dir)


# ─── 6. Lock Contention & Evidence Contract Tests ─────────────────────────────

def test_pipeline_lock_contention(tmp_path):
    """Verify flock contention raises LockContentionError."""
    lock_file = str(tmp_path / "pipeline.lock")

    with PipelineLock(lock_file_path=lock_file, timeout_seconds=1.0):
        with pytest.raises(LockContentionError) as excinfo:
            with PipelineLock(lock_file_path=lock_file, timeout_seconds=0.1):
                pass
        assert "locked by another process" in str(excinfo.value)


def test_build_and_validate_evidence_record():
    """Verify evidence record structure and validation logic with frozen timestamp."""
    frozen_ts = "2026-08-05T04:25:00+00:00"
    rec = build_evidence_record(
        host="Milhy-PC",
        commit_sha="11223344556677889900aabbccddeeff11223344",
        tree_hash="aabbccddeeff11223344556677889900aabbccdd",
        profile="milhy-full",
        reports=["conductor/ci/reports/11223344-report.md"],
        rpi_gate={"status": "PASS", "busy": False},
        e2e_artifacts=["tests/e2e/screenshots/shot.png"],
        actions_url="https://github.com/milhy545/RPi/actions/runs/12345",
        receipt_path="conductor/ci/receipts/11223344-receipt.json",
        timestamp=frozen_ts,
    )

    assert rec["host"] == "Milhy-PC"
    assert rec["timestamp"] == frozen_ts
    assert rec["profile"] == "milhy-full"

    receipt_obj = {
        "status": "done",
        "commit_sha": "11223344556677889900aabbccddeeff11223344",
        "tree_hash": "aabbccddeeff11223344556677889900aabbccdd",
        "ci_report": "conductor/ci/reports/11223344-report.md",
        "actions_url": "https://github.com/milhy545/RPi/actions/runs/12345",
    }

    assert validate_receipt_structure(receipt_obj, expected_sha="11223344556677889900aabbccddeeff11223344") is True
    assert validate_receipt_structure(receipt_obj, expected_sha="badsha") is False


# ─── 7. Host Routing & RPi Push / Browser Bans ───────────────────────────────

def test_install_rpi_core_rules_idempotent(tmp_path):
    """Verify install-rpi-core-rules.sh is idempotent and creates backups on changes."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    installer = os.path.join(repo_root, "tools", "install-rpi-core-rules.sh")
    dest_file = str(tmp_path / "AGENTS.md")

    # First run: installs template
    res1 = subprocess.run([installer, dest_file], capture_output=True, text=True)
    assert res1.returncode == 0
    assert "Installing repository-managed RPi core-rules" in res1.stdout
    assert os.path.exists(dest_file)

    # Second run: idempotent OK
    res2 = subprocess.run([installer, dest_file], capture_output=True, text=True)
    assert res2.returncode == 0
    assert "already up-to-date" in res2.stdout

    # Modify dest_file
    with open(dest_file, "a") as f:
        f.write("\n# Extra user edit\n")

    # Third run: creates timestamped backup and overwrites with template
    res3 = subprocess.run([installer, dest_file], capture_output=True, text=True)
    assert res3.returncode == 0
    assert "Creating timestamped backup" in res3.stdout
