# Agent Safety Rules — CI Gateway

## CRITICAL RULES

### Rule 1: Never claim "done" without a receipt
The agent MUST NOT say "done", "hotovo", "finished", or "completed"
until `tools/verify-done.sh` exits with code 0.

```bash
tools/verify-done.sh
# If exit code is 1, agent must NOT claim success.
```

### Rule 2: Never commit without CI passing
`tools/finish-track.sh` enforces the local commit gate:
- It retains a safety snapshot and runs the selected CI profile before staging a commit.
- If CI fails or runtime artifacts are staged, no commit is made.
- It creates a new commit; it never amends the current commit.
- The agent must not bypass this by running `git commit` directly.
- It does not push or create a completion receipt. Push and merge remain on the Milhy-PC gateway, and exact-main completion evidence comes from GitHub Actions.

### Rule 3: Never skip the receipt
An atomic completion receipt is written ONLY by successful GitHub Actions CI for the exact `main` push:
```
conductor/ci/receipts/{sha}-{timestamp}-github-main.json
```
No receipt for the exact commit SHA or identical Git tree = pipeline incomplete
= agent must not claim done. The tree identity fallback exists only because
GitHub rebase can rewrite commit metadata after the receipt is issued. An RPi
candidate receipt is hardware-gate evidence only and does not complete this
requirement.
If the base branch advanced and changed the tree, `verify-done.sh` may import a
new local receipt only from a successful GitHub Actions `push` run for the exact
`main` HEAD SHA and the repository `ci.yml` workflow. The workflow is local-only
and does not upload artifacts.
Local verification requires a `github-actions-main-push` receipt even when run
from a feature branch; a pull-request receipt is accepted only inside the
GitHub Actions `pull_request` checkout for its exact tested SHA.

### Rule 4: Never ignore error output
If ANY of these fail, the agent must STOP and report:
- `tools/run-ci.sh` exit code != 0
- `git commit` fails
- `rsync` to Milhy-PC fails
- Milhy-PC CI agent fails
- required GitHub Actions PR or main check fails
- `tools/verify-done.sh` exit code != 0

### Rule 5: Never commit runtime artifacts
Forbidden from commits:
- `*.pyc`, `__pycache__/`
- `.forensics/`
- `playback-memory.json`, `yt-cookies.txt`
- `conductor/ci/reports/`, `conductor/ci/receipts/`
- `.venv/`

### Rule 6: Never push directly from RPi
The RPi MUST NOT run `git push`. All pushes go through Milhy-PC CI gateway.

### Rule 7: Safety stash before every commit
`tools/finish-track.sh` creates a safety snapshot before any changes:
```
pre-finish-track-{timestamp}
```
If something goes wrong, this stash can be restored.

### Rule 8: Explicit execution profiles & host routing
- `rpi-focused`: RPi unit/syntax checks (no full pytest or browser runs).
- `milhy-full`: Milhy-PC full pytest, Ruff, mypy, security tools, and remote browser E2E.
- `rpi-candidate`: Non-mutating hardware smoke on staged SHA candidate on RPi.
- `github-safe`: Full local static and unit checks for changes validated by GitHub Actions that do not need hardware or remote-browser evidence.

### Rule 9: Non-disruptive RPi hardware guard
- Exact process matching for `mpv`, `steamlink`, `moonlight`, TUI mode (excludes substring scripts like `keys2mpv.py`).
- Sustained user CPU >20% gates candidate execution; self-CPU is excluded to prevent self-deadlock.
- If user playback starts mid-run, abort candidate processes immediately and requeue.
- Browsers (Playwright/Chrome/Firefox) are strictly forbidden on RPi.

### Rule 10: Candidate worktree isolation & flock ownership
- Candidate code is staged in an isolated worktree outside live checkout.
- Refuse `rsync --delete` if live checkout or target worktree has uncommitted dirty changes.
- Pipeline execution uses `flock` lock file (`/tmp/rpi-ci-pipeline.lock`) for exclusive ownership.

## VERIFICATION WORKFLOW

```
Agent completes work on a candidate branch
  ↓
tools/finish-track.sh "message"
  ↓
  ├── stash snapshot created
  ├── selected local CI runs (must PASS)
  ├── runtime artifact gate
  └── new commit created (no amend, push, or completion receipt)
  ↓
Milhy-PC gateway pushes the candidate branch after required candidate evidence
  ↓
GitHub PR checks and review pass; maintainer merges through branch protection
  ↓
GitHub Actions push CI for exact main SHA creates receipt/report artifacts
  ↓
tools/verify-done.sh
  ↓
  ├── receipt exists for HEAD SHA or identical Git tree?
  ├── receipt status == "done"?
  ├── CI report exists?
  ├── working tree clean?
  ├── Milhy-PC mirror matches?
  ├── HEAD pushed to origin?
  ├── no runtime artifacts?
  └── no forbidden strings?
  ↓
EXIT 0 = agent may say "done"
EXIT 1 = agent MUST NOT say "done"
```

## FAILURE MODE MATRIX

| What fails | Receipt created? | Agent action |
|---|---|---|
| Local CI or artifact gate fails | NO | Fix the change and retry; preserve the safety snapshot. |
| git commit fails | NO | Check staged files and preserve the working tree. |
| RPi candidate evidence or remote E2E fails | NO push | Report the exact gate; do not push the candidate. |
| GitHub PR check or review fails | NO merge | Resolve the finding and wait for checks to rerun. |
| Exact-main CI or receipt validation fails | NO completion | Inspect the exact SHA and Actions artifact; repair or rerun CI. |
| Everything passes and `verify-done.sh` exits 0 | YES | Agent may claim completion. |

## ANTI-LIABILITY CLAUSE

The agent MUST NOT:
- Say "CI passed" without showing the CI report path
- Say "committed" without showing the commit SHA
- Say "done" without `verify-done.sh` PASS
- Say "pushed to GitHub" without showing the GitHub Actions run URL
- Ignore stderr output from any tool
- Continue after a `set -e` failure
- Use `|| true` to suppress errors in critical paths
