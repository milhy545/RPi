# Track Spec: Safe RPi / Milhy-PC / Jules Validation Pipeline

## Context & Objectives
This track defines and implements the safe, isolated multi-host validation pipeline for RPi-TV Dashboard across Raspberry Pi (RPi 3B), Milhy-PC (development workstation & sole GitHub push gateway), and Jules/cloud environments.

## Binding Requirements & Pipeline Rules

1. **Gateway & SHA Binding**:
   - Milhy-PC is the sole GitHub push and merge gateway. RPi never executes `git push`.
   - Exact commit SHA and Git tree hash bind all evidence. Any subsequent code change invalidates previous validation receipts.

2. **Pipeline Workflows by Origin**:
   - **RPi-origin**: Targeted debug & safe HW checks on RPi → handoff to Milhy-PC → Milhy-PC full pytest, backend stability, Ruff, mypy, security tools, and remote browser E2E → repeat RPi validation if code changed → Milhy-PC merge.
   - **Milhy-PC-origin**: Isolated worktree → full checks → stage exact candidate SHA outside live RPi checkout → Playwright/E2E from Milhy-PC against candidate → automatic safe RPi HW smoke → Milhy-PC merge.
   - **Jules/cloud**: Branch/PR → isolated Milhy-PC review & full checks → exact candidate staged on RPi → E2E + safe HW validation → Milhy-PC merge. VM tests are never hardware evidence.

3. **Automated RPi Hardware Guard**:
   - **Exact Process & Mode Detection**: Inspects running executables (`mpv`, `steamlink`, `moonlight`, TUI mode). Strictly excludes substring matches (e.g. `keys2mpv.py` must never be misidentified as `mpv`).
   - **Resource & CPU Attribution**: Sustained user workload CPU >20% triggers busy state. Self-CPU from CI runner/test PIDs is explicitly attributed and excluded to prevent self-deadlock.
   - **Resource Gates**: Gates RAM (<50 MB free), CPU temperature (>75°C), and active locks.
   - **Queueing & Backoff**: Defer execution with bounded exponential backoff when busy.
   - **Non-Disruptive Protection**: Never kill, signal, restart, or degrade active playback, gaming, TUI, audio, Bluetooth, CEC, or services. If playback starts mid-run, abort candidate/test processes immediately and requeue.
   - **RPi Host Limits**: RPi checks run serially with `flock`, low priority, bounded runtime. Browsers never run on RPi.

4. **Candidate Staging & Worktree Isolation**:
   - Candidate code is staged in an isolated worktree/directory (`/home/milhy777/rpi-dashboard-candidate-<sha>`).
   - Refuse sync/staging if live checkout or target directory has uncommitted dirty changes (`rsync --delete` forbidden over unknown dirty checkouts).
   - Health checks and clean rollback on failure.

5. **Explicit Execution Profiles**:
   - `rpi-focused`: Targeted debug and safe unit/smoke checks for RPi (no heavy pytest or browser tests).
   - `milhy-full`: Full pytest suite, backend stability, Ruff, mypy, security scans (ShellCheck, Gitleaks, Bandit, pip-audit), remote Playwright E2E.
   - `rpi-candidate`: Safe HW smoke on staged candidate worktree on RPi.
   - `github-safe`: Final CI gateway verification on Milhy-PC prior to GitHub push.

6. **Repository-Managed RPi Core Rules**:
   - Repository template `.agents/AGENTS.rpi.template.md` managed under git.
   - Idempotent installer `tools/install-rpi-core-rules.sh` with timestamped backups, destination validation, and symlink checks.
   - Preserves RPi 3B low-RAM rules and injects host routing, playback protection, Milhy-PC-only push, and receipt rules.

7. **Evidence & Receipt Contract**:
   - Pipeline evidence structured with host, SHA/tree, profile, timestamp, reports, RPi gate, E2E artifacts, Actions URL, and receipt path.
   - Requires `flock` file locking to prevent race conditions.
