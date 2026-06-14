# RPi Dashboard — CI/CD Pipeline

Complete pipeline from Conductor track to GitHub repository.

## 1. Working on a Track

```text
Agent works on feature/bugfix in /home/milhy777/rpi-dashboard
```

- Creates/modifies files according to `conductor/tracks/<track>/plan.md`
- Commits via `tools/finish-track.sh "message"`
- **Never runs `git commit` directly** — everything through finish-track.sh

## 2. `tools/finish-track.sh` — Atomic Pipeline

When you call `tools/finish-track.sh "feat(webui): add player"`:

```text
Step 1: Safety snapshot
  └── git stash push -m "pre-finish-track-TIMESTAMP"
  └── immediately re-apply (stash stays as rollback point)

Step 2: Record pre-commit state
  └── stores SHA, tree hash, diff hash

Step 3: Local CI (tools/run-ci.sh)
  ├── whitespace check
  ├── Python compile (5 files)
  ├── JS syntax (extract → node --check)
  ├── WebUI audio tests (if server running)
  ├── ShellCheck (if installed)
  ├── Bandit high severity (if installed)
  └── forbidden regression strings

  ⚠️ If CI fails → ABORT, no commit, no receipt

Step 4: Forbidden patterns check
  └── grep for GFN-TV, killall mpv, pkill mpv

Step 5: Runtime artifact check
  └── *.pyc, __pycache__, .forensics/, cookies etc.

Step 6: git add -A && git commit -m "message"

Step 7: Post-commit verify
  └── compares SHA before and after commit

Step 8: rsync to Milhy-PC
  └── Milhy-PC:/home/milhy777/Develop/RPi
  └── verify: remote SHA == local SHA

Step 9: Trigger Milhy-PC CI agent
  └── ssh Milhy-PC "cd ... && tools/ci-agent.sh"

Step 10: Write atomic receipt
  └── conductor/ci/receipts/{SHA}-{TIMESTAMP}.json
  └── contains: status, SHA, tree, diff, timestamp, report
```

## 3. Milhy-PC CI Gateway

Persistent systemd service `rpi-ci-agent.service` runs on Milhy-PC.

```text
rpi-ci-agent.service
├── every 30 seconds checks: git log origin/master..HEAD
├── if new commit found:
│   ├── runs tools/run-ci.sh (including ShellCheck)
│   ├── if PASS → git push origin master
│   └── if FAIL → writes report, no push
└── then waits another 30 seconds
```

## 4. GitHub Actions

```text
.github/workflows/ci.yml
├── Python syntax
├── JS syntax (extract → node --check)
├── ShellCheck
├── Bandit high severity gate
├── pip-audit
├── forbidden strings
└── report upload as artifact
```

## 5. Auto-Start Chain (When You Forget)

```text
RPi systemd timer (rpi-git-handoff.timer)
├── every 2 minutes checks: git status + git log
├── if new commit and repo is clean:
│   └── rsync to Milhy-PC
└── Milhy-PC service notices new commit and runs CI

Both are persistent (Linger=yes) = survive reboot.
```

## 6. Safety Rules

```text
Rule 1: No receipt = agent MUST NOT say "done"
Rule 2: CI must PASS BEFORE commit is created
Rule 3: Receipt is created ONLY on full success
Rule 4: Any error = immediate abort
Rule 5: Runtime artifacts must not be in commits
Rule 6: RPi must NOT push directly to GitHub
Rule 7: Safety stash before every commit
```

Agent **MUST** run `tools/verify-done.sh` before claiming success.

## 7. Flow Summary

```text
Agent finishes work
  ↓
tools/finish-track.sh "message"
  ↓
  ├── CI pass? ──no──→ STOP (no commit)
  ├── commit created
  ├── rsync → Milhy-PC
  ├── Milhy-PC CI pass? ──no──→ STOP (no push)
  ├── git push → GitHub
  ├── GitHub Actions pass? ──no──→ commit on GH exists but red
  └── receipt written
  ↓
tools/verify-done.sh
  ├── receipt valid?
  ├── CI report PASS?
  ├── mirror synced?
  ├── no artifacts?
  └── no forbidden strings?
  ↓
EXIT 0 = "done" ✅
EXIT 1 = "MUST NOT claim done" 🛑
```

## 8. File Reference

```text
tools/finish-track.sh          — atomic pipeline
tools/run-ci.sh                — CI checks
tools/ci-agent.sh              — Milhy-PC persistent agent
tools/trigger-ci-handoff.sh    — RPi→Milhy-PC auto sync
tools/verify-done.sh           — agent self-check (MANDATORY)
tools/install-ci-gateway.sh    — systemd unit installer

systemd/user/rpi-git-handoff.timer   — RPi auto sync (2 min)
systemd/user/rpi-ci-agent.service    — Milhy-PC CI agent

conductor/ci/SAFETY-RULES.md   — rules for agents
conductor/ci/receipts/         — atomic receipts
conductor/ci/reports/          — CI reports
.github/workflows/ci.yml       — GitHub Actions
```

## 9. Failure Mode Matrix

| What fails | Receipt created? | Commit created? | GitHub push? | Agent action |
|---|---|---|---|---|
| Local CI fails | NO | NO | NO | Fix CI, retry |
| git commit fails | NO | NO | NO | Check staged files |
| rsync fails | NO | YES (local) | NO | Check network |
| Milhy-PC CI fails | NO | YES (local) | NO | Check Milhy-PC |
| Milhy-PC push fails | NO | YES (local) | NO | Check GitHub auth |
| GitHub Actions fails | YES | YES | YES (red) | Fix in next commit |
| Everything passes | YES | YES | YES (green) | Agent may say "done" |

## 10. Where Safety Rules Are Documented

| Location | Scope | Auto-injected? |
|---|---|---|
| `/home/milhy777/.agents/skills/core-rules/SKILL.md` | All agents | YES (description field) |
| `/home/milhy777/.pi/agent/skills/conductor/SKILL.md` | Pi agent | YES (skill file) |
| `/home/milhy777/rpi-dashboard/conductor/index.md` | Project agents | On read |
| `/home/milhy777/rpi-dashboard/conductor/ci/SAFETY-RULES.md` | Reference | On read |
