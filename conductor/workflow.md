# Workflow: RPi Dumb TV Dashboard

## 0. Repository Routing & Host Roles

- All RPi Dashboard work uses this Git repository's top-level directory as the project root.
- `<repository>/conductor` is the authoritative Conductor state.
- **Milhy-PC**: Development workstation, sole GitHub push/merge gateway, full pytest runner, security auditor, and Playwright E2E runner.
- **RPi**: Target hardware execution host (RPi 3B, 731 MB RAM). Runs lightweight unit checks, candidate hardware smoke, and playback guard. RPi NEVER executes `git push`.
- **Jules / Cloud**: Cloud agent environment. Candidate code is reviewed and staged on Milhy-PC before hardware validation. VM tests are never hardware evidence.

## 1. Safe Multi-Host Validation Pipeline

### 1.1 Pipeline Flow by Origin
- **RPi-Origin**: Targeted debug + `rpi-focused` HW checks on RPi → handoff sync to Milhy-PC → Milhy-PC `milhy-full` pytest, Ruff, mypy, security, and remote E2E → repeat RPi validation if code changed → Milhy-PC merge.
- **Milhy-PC-Origin**: Isolated worktree → `milhy-full` checks → stage exact SHA outside live RPi checkout → remote Playwright E2E against candidate → automatic safe RPi `rpi-candidate` HW smoke → Milhy-PC merge.
- **Jules/Cloud-Origin**: Branch/PR → isolated Milhy-PC review & full checks → stage candidate on RPi → E2E + safe HW validation → Milhy-PC merge.

### 1.2 Execution Profiles
- `rpi-focused`: Lightweight unit & syntax checks for RPi (no heavy pytest or browser runs).
- `milhy-full`: Full pytest suite, Ruff, mypy, security scans (ShellCheck, Gitleaks, Bandit, pip-audit), remote Playwright E2E.
- `rpi-candidate`: Safe HW smoke on staged candidate worktree on RPi.
- `github-safe`: Final CI gateway verification on Milhy-PC prior to GitHub push.

### 1.3 Automated RPi Hardware Guard
- **Exact Process Matching**: Checks executables (`mpv`, `steamlink`, `moonlight`, TUI modes). Excludes helper scripts like `keys2mpv.py`.
- **Resource Attribution & Queueing**: User CPU >20%, low free RAM (<50 MB), or thermal limit (>75°C) queues execution with bounded backoff. Self-CPU from CI runner is excluded to prevent self-deadlock.
- **Playback Protection**: Candidate checks on RPi NEVER disrupt active playback, gaming, TUI modes, audio, Bluetooth, CEC, or services. If playback starts mid-run, candidate processes terminate immediately and requeue.
- **RPi Environment Limits**: RPi runs serially with `flock`. Browsers (Playwright/Chrome/Firefox) are strictly forbidden on RPi.

## 2. Branching & Commit Guidelines

- **Branches**: `main` (stable/deployable), `feat/*` or `fix/*` feature branches.
- **Commit Format**: Conventional Commits (`type(scope): message`).
- **Safety Gates**: `tools/finish-track.sh` creates safety snapshot `pre-finish-track-{timestamp}`, runs CI, commits, syncs mirror, and generates atomic receipt. `tools/verify-done.sh` verifies receipt and exact SHA binding before any completion claim.
