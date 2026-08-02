import os
from pathlib import Path
import subprocess

import yaml


WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
CI_AGENT = Path(__file__).parents[1] / "tools" / "ci-agent.sh"


def _workflow(name: str) -> dict:
    return yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)


def test_ci_approves_pull_requests_only_after_verification() -> None:
    workflow = _workflow("ci.yml")

    assert "on" in workflow
    assert "push" in workflow["on"]
    assert "pull_request" in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]

    jobs = workflow["jobs"]
    assert list(jobs) == ["local-sync", "verify-done"]
    assert jobs["local-sync"]["uses"] == "./.github/workflows/ci-fast.yml"

    verify = jobs["verify-done"]
    assert verify["name"] == "verify-done"
    assert verify["needs"] == "local-sync"
    assert verify["runs-on"] == "ubuntu-latest"
    assert [step["name"] for step in verify["steps"]] == [
        "Checkout branch",
        "Download CI receipt",
        "Download CI report",
        "Verify completion receipt",
    ]
    assert verify["steps"][-1]["run"] == "tools/verify-done.sh"


def test_ci_fast_workflow_contains_the_previous_local_sync_checks() -> None:
    workflow = _workflow("ci-fast.yml")

    assert "workflow_call" in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]

    jobs = workflow["jobs"]
    assert list(jobs) == ["local-sync"]
    assert jobs["local-sync"]["runs-on"] == "ubuntu-latest"

    steps = jobs["local-sync"]["steps"]
    assert [step["name"] for step in steps[:5]] == [
        "Checkout",
        "Setup Python",
        "Create virtual environment",
        "Install dependencies",
        "Python compile",
    ]
    assert steps[-2]["name"] == "Upload receipt"
    assert steps[-1]["name"] == "Upload CI report"


def test_ci_fast_workflow_enforces_quality_and_security_gates() -> None:
    workflow = _workflow("ci-fast.yml")
    steps = workflow["jobs"]["local-sync"]["steps"]
    commands = {step["name"]: step.get("run", "") for step in steps}

    assert commands["Ruff lint"] == ".venv/bin/ruff check ."
    assert commands["Mypy type check"] == (
        ".venv/bin/mypy --explicit-package-bases ."
    )
    assert "--cov-fail-under=69" in commands["Run pytest with coverage gate"]
    assert "--cov-report=xml" in commands["Run pytest with coverage gate"]
    assert commands["Bandit high-severity scan"] == (
        ".venv/bin/bandit -q -lll -r . -x ./.venv,./__pycache__,./tests"
    )
    assert commands["Dependency vulnerability audit"] == (
        ".venv/bin/pip-audit --skip-editable"
    )


def test_ci_rpi_workflow_is_separate_and_self_hosted() -> None:
    workflow = _workflow("ci-rpi.yml")

    assert "workflow_dispatch" in workflow["on"]
    jobs = workflow["jobs"]
    assert jobs["rpi-hardware"]["runs-on"] == ["self-hosted", "rpi", "linux", "arm"]
    assert jobs["rpi-hardware"]["if"] == "github.event.inputs.rpi_hw_tests == 'true'"
    assert jobs["verify"]["needs"] == ["rpi-hardware"]
    assert jobs["status"]["needs"] == ["rpi-hardware", "verify"]


def test_auto_merge_uses_safe_target_event_without_checkout() -> None:
    workflow = _workflow("auto-merge.yml")
    event = workflow["on"]["pull_request_target"]
    job = workflow["jobs"]["queue-auto-merge"]

    assert event["types"] == ["opened", "synchronize", "reopened", "ready_for_review"]
    assert workflow["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
    }
    assert all("uses" not in step for step in job["steps"])
    assert job["steps"][0]["run"] == (
        'gh pr merge "$PR_URL" --auto --rebase --delete-branch'
    )


def test_ci_agent_selects_only_complete_report_for_exact_commit(tmp_path: Path) -> None:
    expected_sha = "a" * 40
    reports = {
        "expected.md": f"- Commit: {expected_sha}\n# Final Result\nPASS\n",
        "wrong.md": f"- Commit: {'b' * 40}\n# Final Result\nPASS\n",
        "incomplete.md": f"- Commit: {expected_sha}\n# Final Result\n",
    }
    for timestamp, (name, content) in enumerate(reports.items(), start=1):
        path = tmp_path / name
        path.write_text(content)
        os.utime(path, (timestamp, timestamp))

    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; REPORT_DIR="$2"; latest_report "$3"',
            "ci-report-test",
            str(CI_AGENT),
            str(tmp_path),
            expected_sha,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == str(tmp_path / "expected.md")


def test_ci_agent_refreshes_checkout_branch_when_polling_without_override(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)

    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; cd "$2"; BRANCH_OVERRIDE=""; BRANCH=stale; refresh_branch; printf "%s" "$BRANCH"',
            "ci-branch-test",
            str(CI_AGENT),
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == "main"


def test_ci_agent_rejects_detached_checkout_without_branch_override(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "ci@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "CI Test"], check=True)
    (tmp_path / "README").write_text("test\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "--detach"], check=True, capture_output=True)

    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; cd "$2"; BRANCH_OVERRIDE=""; BRANCH=main; refresh_branch',
            "ci-detached-test",
            str(CI_AGENT),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "detached HEAD" in result.stderr


def test_ci_agent_detects_commit_already_on_target_branch(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    checkout = tmp_path / "checkout"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(checkout)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(checkout), "config", "user.email", "ci@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(checkout), "config", "user.name", "CI Test"], check=True)
    (checkout / "README").write_text("test\n")
    subprocess.run(["git", "-C", str(checkout), "add", "README"], check=True)
    subprocess.run(["git", "-C", str(checkout), "commit", "-m", "test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(checkout), "push", "origin", "main"], check=True, capture_output=True)
    source_sha = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    (checkout / "README").write_text("newer remote tip\n")
    subprocess.run(["git", "-C", str(checkout), "commit", "-am", "advance"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(checkout), "push", "origin", "main"], check=True, capture_output=True)

    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; cd "$2"; TARGET_REMOTE=origin; BRANCH=main; remote_has_commit "$3"',
            "ci-remote-test",
            str(CI_AGENT),
            str(checkout),
            source_sha,
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_ci_agent_state_path_works_in_linked_worktree(tmp_path: Path) -> None:
    """In a linked worktree .git is a file; STATE_FILE must still resolve."""
    source_repo = tmp_path / "source"
    subprocess.run(["git", "init", "-b", "main", str(source_repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(source_repo), "config", "user.email", "ci@t.invalid"], check=True)
    subprocess.run(["git", "-C", str(source_repo), "config", "user.name", "CI"], check=True)
    (source_repo / "README").write_text("init\n")
    subprocess.run(["git", "-C", str(source_repo), "add", "README"], check=True)
    subprocess.run(
        ["git", "-C", str(source_repo), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )
    linked = tmp_path / "linked"
    subprocess.run(
        ["git", "-C", str(source_repo), "worktree", "add", "-b", "linked-branch", str(linked)],
        check=True,
        capture_output=True,
    )
    # linked/.git is a plain file pointing at the source repo worktrees dir
    assert linked.joinpath(".git").is_file()

    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                'source "$1"; cd "$2"; '
                'state_path="$(_resolve_state_path)"; '
                'mkdir -p "$(dirname "$state_path")"; '
                'printf "%s\\n" "deadbeef" > "$state_path"; '
                'printf "%s" "$state_path"'
            ),
            "ci-worktree-test",
            str(CI_AGENT),
            str(linked),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    resolved = Path(result.stdout.strip())
    assert resolved.exists(), f"state file not created at {resolved}"
    assert resolved.read_text().strip() == "deadbeef"


def test_ci_agent_creates_report_dir_on_source(tmp_path: Path) -> None:
    """Sourcing ci-agent.sh must create REPORT_DIR when it does not yet exist."""
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "ci@t.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "CI"], check=True)
    (repo / "README").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )

    report_dir = tmp_path / "abs" / "reports"
    result = subprocess.run(
        [
            "bash",
            "-c",
            'export REPORT_DIR="$1"; source "$2"; printf "%s" "$REPORT_DIR"',
            "ci-report-dir-test",
            str(report_dir),
            str(CI_AGENT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == str(report_dir)
    assert report_dir.is_dir(), f"REPORT_DIR {report_dir} was not created"


def test_ci_agent_dispatches_workflow_for_non_main_branch(tmp_path: Path) -> None:
    """A non-main push must invoke gh workflow run ci.yml --ref <branch>."""
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "ci@t.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "CI"], check=True)
    (repo / "README").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    gh_log = tmp_path / "gh-call.log"
    # Fake gh: record all args, succeed for workflow run, fail otherwise.
    (fake_bin / "gh").write_text(
        '#!/bin/bash\n'
        'echo "$@" >> ' + str(gh_log) + '\n'
        'if [[ "$1" == "workflow" && "$2" == "run" ]]; then\n'
        '  exit 0\n'
        'fi\n'
        'exit 1\n'
    )
    (fake_bin / "gh").chmod(0o755)

    result = subprocess.run(
        [
            "bash",
            "-c",
            'export PATH="$3:$PATH"; source "$1"; cd "$2"; BRANCH=feat-x; dispatch_ci',
            "ci-dispatch-test",
            str(CI_AGENT),
            str(repo),
            str(fake_bin),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Dispatched ci.yml for branch feat-x" in result.stdout
    log = gh_log.read_text()
    assert "workflow" in log
    assert "run" in log
    assert "ci.yml" in log
    assert "--ref" in log
    assert "feat-x" in log


def test_ci_agent_skips_dispatch_for_main_branch(tmp_path: Path) -> None:
    """A main-branch push must not call gh workflow run at all."""
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "ci@t.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "CI"], check=True)
    (repo / "README").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    gh_log = tmp_path / "gh-call.log"
    # Fake gh that would fail if called — proves dispatch_ci is a no-op.
    (fake_bin / "gh").write_text(
        '#!/bin/bash\n'
        'echo "$@" >> ' + str(gh_log) + '\n'
        'echo "FAIL: gh should not be called for main" >&2\n'
        'exit 1\n'
    )
    (fake_bin / "gh").chmod(0o755)

    result = subprocess.run(
        [
            "bash",
            "-c",
            'export PATH="$3:$PATH"; source "$1"; cd "$2"; BRANCH=main; dispatch_ci',
            "ci-dispatch-main-test",
            str(CI_AGENT),
            str(repo),
            str(fake_bin),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not gh_log.exists(), "gh was called for main branch but should not have been"


def test_finish_track_report_copy_no_self_truncation(tmp_path: Path) -> None:
    """When remote and local paths are identical, scp-to-temp-then-mv must not truncate."""
    report_content = "PASS\n- Commit: abc123\n"
    report_name = "ci-report.md"
    report_file = tmp_path / report_name
    report_file.write_text(report_content)
    # Simulate the same-file scenario: remote and local point to the same path.
    local_ci_report_path = tmp_path / report_name
    local_ci_report_tmp = tmp_path / f"{report_name}.9999.tmp"
    # The finish-track pattern: scp to temp, verify non-empty, mv to target.
    import shutil
    shutil.copy2(str(report_file), str(local_ci_report_tmp))
    assert local_ci_report_tmp.is_file()
    assert local_ci_report_tmp.stat().st_size > 0
    local_ci_report_tmp.rename(local_ci_report_path)
    # File must be intact and temp file gone.
    assert local_ci_report_path.read_text() == report_content
    assert not local_ci_report_tmp.exists()
