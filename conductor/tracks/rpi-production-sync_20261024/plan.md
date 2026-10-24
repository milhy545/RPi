# Implementation Plan: RPi Production Repository Synchronization

## Phase 1 — Verify and Preserve

- [x] Confirm the SSH alias reaches `rpi-tv` at `192.168.0.205`.
- [x] Correct the RPi address in `~/.gemini/GEMINI.md` and keep a timestamped backup.
- [x] Save a verified Git bundle, the dirty patch, report files, and local DLNA mode.
- [x] Compare the RPi branch with current GitHub main. The source fixes are already represented on current main; the closed PR #85 tree is stale and is not to be merged wholesale.

## Phase 2 — Reconcile on GitHub

- [x] Keep the RPi manual sink selection local.
- [x] Carry forward the two current uncommitted report entries at the user's explicit request.
- [ ] Run the required gateway CI, open a focused PR, and wait for required checks and Kilo review.
- [ ] Merge the reviewed PR and verify the exact main SHA and receipt.

## Phase 3 — Synchronize RPi

- [ ] Back up any remaining local-only state and move the production checkout to the exact GitHub main SHA without a direct push.
- [ ] Preserve the local DLNA mode and avoid service restarts or playback interruption.
- [ ] Verify the resulting SHA and report the exact local state.

## Phase 4 — User Verification and Branch Cleanup

- [ ] Notify the user that manual application testing can begin.
- [ ] Wait for the user's test result.
- [ ] Only after confirmation, inventory and remove non-main branches as a separate cleanup step.

## Progress Notes

- 2026-10-24: Host identity and mapping were verified. The production checkout is five commits ahead of its stale local `origin/main`, while GitHub main has advanced independently. The current worktree contains two placeholder report records and a tracked local DLNA mode. The full historical PR #85 snapshot is excluded because it would revert newer project state; its pre-sync objects and the dirty worktree were backed up.
