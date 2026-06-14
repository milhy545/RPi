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
`tools/finish-track.sh` enforces this automatically:
- CI runs BEFORE commit is created
- If CI fails, no commit is made
- The agent must not bypass this by running `git commit` directly

### Rule 3: Never skip the receipt
An atomic receipt is written ONLY on full pipeline success:
```
conductor/ci/receipts/{sha}-{timestamp}.json
```
No receipt = pipeline incomplete = agent must not claim done.

### Rule 4: Never ignore error output
If ANY of these fail, the agent must STOP and report:
- `tools/run-ci.sh` exit code != 0
- `git commit` fails
- `rsync` to Milhy-PC fails
- Milhy-PC CI agent fails
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

## VERIFICATION WORKFLOW

```
Agent completes work
  ↓
tools/finish-track.sh "message"
  ↓
  ├── stash snapshot created
  ├── CI runs (must PASS)
  ├── commit created
  ├── rsync to Milhy-PC
  ├── Milhy-PC CI runs
  ├── Milhy-PC pushes to GitHub
  └── atomic receipt written
  ↓
tools/verify-done.sh
  ↓
  ├── receipt exists for HEAD?
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
| CI fails | NO | Fix CI, retry |
| git commit fails | NO | Check staged files, retry |
| rsync fails | NO | Check network, retry |
| Milhy-PC CI fails | NO | Check Milhy-PC, fix, retry |
| verify-done.sh fails | NO | Check which check failed, fix |
| Everything passes | YES | Agent may say "done" |

## ANTI-LIABILITY CLAUSE

The agent MUST NOT:
- Say "CI passed" without showing the CI report path
- Say "committed" without showing the commit SHA
- Say "done" without `verify-done.sh` PASS
- Say "pushed to GitHub" without showing the GitHub Actions run URL
- Ignore stderr output from any tool
- Continue after a `set -e` failure
- Use `|| true` to suppress errors in critical paths
