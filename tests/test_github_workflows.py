from pathlib import Path

import yaml


WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"


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
        'gh pr merge "$PR_URL" --auto --squash --delete-branch'
    )
