from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACK_ROOT = PROJECT_ROOT / "conductor" / "tracks" / "verification-coverage-hardening_20260723"
SYSTEMD_ROOT = PROJECT_ROOT / "systemd"
SOAK_TEST = PROJECT_ROOT / "tools" / "soak_test.py"
RUN_CHECKS = PROJECT_ROOT / "run_checks.py"


def test_report_worker_units_are_aligned_with_project_interpreter() -> None:
    user_service = (SYSTEMD_ROOT / "user" / "report-processor.service").read_text()
    user_timer = (SYSTEMD_ROOT / "user" / "report-processor.timer").read_text()
    root_service = (SYSTEMD_ROOT / "report-processor.service").read_text()

    assert "Type=oneshot" in user_service
    assert "ExecStart=/home/milhy777/rpi-dashboard/tools/process_reports.py" in user_service
    assert "User=" not in user_service
    assert "OnBootSec=1min" in user_timer
    assert "OnUnitActiveSec=1min" in user_timer
    assert "ExecStart=/usr/bin/python3 /home/milhy777/rpi-dashboard/tools/process_reports.py" in root_service


def test_tmux_restore_disposition_is_explicit_in_soak_and_audit() -> None:
    soak = SOAK_TEST.read_text()
    audit = (TRACK_ROOT / "log-audit.md").read_text()
    plan = (TRACK_ROOT / "plan.md").read_text()

    assert '"tmux-restore"' in soak
    assert "tmux-restore.service" in audit
    assert "fix or intentionally retire" in audit.lower()
    assert "tmux restore" in plan.lower()


def test_production_tools_do_not_execute_commands_through_a_shell() -> None:
    assert "shell=True" not in SOAK_TEST.read_text()
    assert "shell=True" not in RUN_CHECKS.read_text()


def test_logrotate_regression_remains_documented_in_the_ledger() -> None:
    baseline = (TRACK_ROOT / "baseline_reconciliation.md").read_text()

    assert "/tmp/tui_fresh.log" in baseline
    assert "Preserve fix with config validation + regression check" in baseline
    assert "regression risk" in baseline
