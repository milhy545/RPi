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
    approval = workflow["jobs"]["agent-approval"]

    assert workflow["on"]["push"] == ""
    assert approval["needs"] == "verify-done"
    assert approval["permissions"] == {"pull-requests": "write"}
    command = approval["steps"][0]["run"]
    assert 'gh pr review "$PR_URL" --approve' in command


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
