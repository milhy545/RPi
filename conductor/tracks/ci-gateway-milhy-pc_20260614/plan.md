# Implementation Plan: Milhy-PC CI Gateway

## Phase 1: Local CI Foundation
- [x] Task: Add embedded WebUI JavaScript extractor.
- [x] Task: Add `tools/run-ci.sh` with Python syntax checks.
- [x] Task: Add Node.js syntax check for embedded WebUI JavaScript when available.
- [x] Task: Add optional security tools: ShellCheck, Gitleaks, Bandit, pip-audit.
- [x] Task: Store Markdown reports under `conductor/ci/reports/`.

## Phase 2: RPi Handoff Workflow
- [x] Task: Add `tools/finish-track.sh`.
- [x] Task: Create safety stash checkpoint before committing.
- [x] Task: Run local CI before commit.
- [x] Task: Push to Milhy-PC remote only, not GitHub.

## Phase 3: Milhy-PC Gateway Agent
- [x] Task: Add `tools/ci-agent.sh`.
- [x] Task: Fetch candidate commits from RPi remote.
- [x] Task: Run CI on Milhy-PC.
- [x] Task: Push to GitHub only after CI success.
- [x] Task: Produce report and desktop notification on failure.

## Phase 4: GitHub Actions
- [x] Task: Add `.github/workflows/ci.yml`.
- [x] Task: Run project CI on GitHub.
- [x] Task: Upload CI reports as artifacts.

## Phase 5: Verification
- [x] Task: Run local CI on RPi.
- [x] Task: Sync current RPi state to Milhy-PC.
- [x] Task: Start persistent Milhy-PC tmux CI agent.
- [x] Task: Perform first full RPi → Milhy-PC → GitHub handoff.

## Completion Notes

The tooling is implemented and the first full RPi → Milhy-PC → GitHub handoff has completed successfully.
