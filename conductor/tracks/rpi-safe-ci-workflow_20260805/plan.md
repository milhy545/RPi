# Implementation Plan: Safe RPi / Milhy-PC / Jules Validation Pipeline

## Tasks & Milestones

- [x] **Phase 1: Conductor Track Setup**
  - Create track metadata, specification, and implementation plan.
  - Register track in `conductor/tracks.md`.

- [x] **Phase 2: RPi Guard & Pipeline Engine Implementation**
  - Implement `rpi_dashboard.ci.rpi_guard` module with exact process matching, self-CPU attribution, resource gating, queueing/backoff, and mid-run playback detection.
  - Implement `rpi_dashboard.ci.staging` for isolated candidate staging, dirty checkout refusal, and rollback.
  - Implement `rpi_dashboard.ci.evidence` for `flock` lock ownership, evidence aggregation, and atomic receipt validation.

- [ ] **Phase 3: Profiles & Script Integration**
  - [x] Update `tools/run-ci.sh` to implement explicit profiles (`rpi-focused`, `milhy-full`, `rpi-candidate`, `github-safe`) and fix pytest drift.
  - [x] Update `tools/ci-agent.sh` default profile to `milhy-full` (was `github-safe`).
  - [x] Add E2E/evidence gates in `ci-agent.sh` requiring Playwright artifacts and exact-SHA RPi receipt before push.
  - [x] Fix `prepare_candidate` to fail-loud on dirty worktree (removed silent git-stash).
  - [x] Update `tools/finish-track.sh` to use `milhy-full` profile.
  - [ ] **PENDING**: Live E2E/HW/receipt rollout evidence must exist before marking complete.
  - Note: `tools/verify-done.sh` was NOT modified in this implementation.

- [x] **Phase 4: RPi Core Rules Template & Idempotent Installer**
  - Add `.agents/core-rules/SKILL.rpi.template.md` with hardware constraints and injected pipeline rules for the actual CodeX skill system.
  - Create `tools/install-rpi-core-rules.sh` with timestamped backup, symlink resolution, boundary validation, atomic install, and rollback on failure.
  - Targets `~/.agents/skills/core-rules/SKILL.md` (not ~/AGENTS.md).

- [x] **Phase 5: Documentation Alignment**
  - Update `AGENTS.md` (UK English) and `AGENTS.cz.md` (Czech).
  - Update `conductor/ci/SAFETY-RULES.md`, `conductor/workflow.md`, and create matching `conductor/workflow.cz.md`.

- [ ] **Phase 6: Comprehensive Test Suite & Verification**
  - [x] Create `tests/test_rpi_safe_ci_pipeline.py` testing host/profile routing, exact process matching, CPU attribution, queueing, mid-run playback abort, dirty refusal, SHA mismatch, lock contention, rollback, and push/browser bans.
  - [ ] **PENDING**: Add deterministic tests proving push is impossible when E2E or exact-SHA RPi evidence is absent/stale.
  - [ ] **PENDING**: Add tests proving dirty state is untouched.
  - [ ] **PENDING**: Live E2E/HW/receipt rollout evidence must exist before marking complete.
  - Run shell syntax checks, pytest suite, Ruff, mypy, Conductor validation, and `git diff --check`.
