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
    assert list(jobs) == ["local-sync"]
    assert jobs["local-sync"]["uses"] == "./.github/workflows/ci-fast.yml"


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
