# Implementation Plan: Safe RPi / Milhy-PC / Jules Validation Pipeline

## Tasks & Milestones

- [x] **Phase 1: Conductor Track Setup**
  - Create track metadata, specification, and implementation plan.
  - Register track in `conductor/tracks.md`.

- [x] **Phase 2: RPi Guard & Pipeline Engine Implementation**
  - Implement `rpi_dashboard.ci.rpi_guard` module with exact process matching, self-CPU attribution, resource gating, queueing/backoff, and mid-run playback detection.
  - Implement `rpi_dashboard.ci.staging` for isolated candidate staging, dirty checkout refusal, and rollback.
  - Implement `rpi_dashboard.ci.evidence` for `flock` lock ownership, evidence aggregation, and atomic receipt validation.

- [x] **Phase 3: Profiles & Script Integration**
  - Update `tools/run-ci.sh` to implement explicit profiles (`rpi-focused`, `milhy-full`, `rpi-candidate`, `github-safe`) and fix pytest drift.
  - Update `tools/ci-agent.sh` and `tools/finish-track.sh` to enforce profile evidence, RPi candidate gates, and Milhy-PC push restriction.
  - Note: `tools/verify-done.sh` was NOT modified in this implementation.

- [x] **Phase 4: RPi Core Rules Template & Idempotent Installer**
  - Add `.agents/core-rules/SKILL.rpi.template.md` with hardware constraints and injected pipeline rules for the actual CodeX skill system.
  - Create `tools/install-rpi-core-rules.sh` with timestamped backup, symlink resolution, boundary validation, atomic install, and rollback on failure.
  - Targets `~/.agents/skills/core-rules/SKILL.md` (not ~/AGENTS.md).

- [x] **Phase 5: Documentation Alignment**
  - Update `AGENTS.md` (UK English) and `AGENTS.cz.md` (Czech).
  - Update `conductor/ci/SAFETY-RULES.md`, `conductor/workflow.md`, and create matching `conductor/workflow.cz.md`.

- [x] **Phase 6: Comprehensive Test Suite & Verification**
  - Create `tests/test_rpi_safe_ci_pipeline.py` testing host/profile routing, exact process matching, CPU attribution, queueing, mid-run playback abort, dirty refusal, SHA mismatch, lock contention, rollback, and push/browser bans.
  - Run shell syntax checks, pytest suite, Ruff, mypy, Conductor validation, and `git diff --check`.
