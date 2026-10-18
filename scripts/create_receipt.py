#!/usr/bin/env python3
"""
Create CI receipt and report files for RPi Dashboard.
"""
import os
import subprocess
from datetime import datetime, timezone


def main():
    # Get git info
    SHA = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    TREE = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()

    RECEIPT_DIR = "conductor/ci/receipts"
    REPORT_DIR = "conductor/ci/reports"
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    ref = os.environ.get("GITHUB_REF", "")
    event_slug = event.replace("_", "-") or "manual"
    RECEIPT_FILE = f"{RECEIPT_DIR}/{SHA}-{timestamp}-{event_slug}.json"
    REPORT_FILE = f"{REPORT_DIR}/{SHA}-{timestamp}-{event_slug}.md"
    if event == "push" and ref == "refs/heads/main":
        source = "github-actions-main-push"
    elif event == "pull_request":
        source = "github-actions-pull-request"
    else:
        source = "github-actions-workflow"

    # Create report file
    with open(REPORT_FILE, "w") as f:
        f.write("PASS\n\n# RPi Dashboard CI Report\n\n")
        f.write(f"- Commit: {SHA}\n")
        f.write(f"- Host: {subprocess.check_output(['hostname'], text=True).strip()}\n")
        f.write(f"- Time: {now.isoformat()}\n")
        f.write("- Result: PASS\n")

    # Create receipt file
    receipt = {
        "status": "done",
        "commit_sha": SHA,
        "tree_hash": TREE,
        "source": source,
        "ci_report": REPORT_FILE,
        "actions_url": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'milhy545/RPi')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        "timestamp": now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    }

    with open(RECEIPT_FILE, "w") as f:
        import json
        json.dump(receipt, f, indent=2)

    # Note: REPORT_FILE is already written above
    # Output for GitHub Actions - write to GITHUB_OUTPUT file
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"receipt={RECEIPT_FILE}\n")
            f.write(f"report={REPORT_FILE}\n")
    else:
        # Fallback for local testing
        print(f"receipt={RECEIPT_FILE}")
        print(f"report={REPORT_FILE}")


if __name__ == "__main__":
    main()
