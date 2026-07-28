#!/usr/bin/env python3
"""
Create CI receipt and report files for RPi Dashboard.
"""
import os
import subprocess
from datetime import datetime


def main():
    # Get git info
    SHA = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    TREE = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()

    RECEIPT_DIR = "conductor/ci/receipts"
    REPORT_DIR = "conductor/ci/reports"
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    RECEIPT_FILE = f"{RECEIPT_DIR}/{SHA}-{timestamp}-github-main.json"
    REPORT_FILE = f"conductor/ci/reports/{SHA}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-github-main.md"

    # Create report file
    with open(REPORT_FILE, "w") as f:
        f.write("# RPi Dashboard CI Report\n\n")
        f.write(f"- Commit: {SHA}\n")
        f.write(f"- Host: {subprocess.check_output(['hostname'], text=True).strip()}\n")
        f.write(f"- Time: {datetime.utcnow().isoformat()}Z\n")
        f.write("- Result: PASS\n")

    # Create receipt file
    receipt = {
        "status": "done",
        "commit_sha": SHA,
        "tree_hash": TREE,
        "source": "github-actions-main-push",
        "ci_report": REPORT_FILE,
        "actions_url": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'milhy545/RPi')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
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
            f.write(f"report=conductor/ci/reports/{SHA}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-github-main.md\n")
    else:
        # Fallback for local testing
        print(f"receipt={RECEIPT_FILE}")
        print(f"report=conductor/ci/reports/{SHA}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-github-main.md")


if __name__ == "__main__":
    main()