# Implementation Plan: Git Live Development Workflow

## Phase 1: Safety and Audit
- [x] Check mpv is not running before setup.
- [x] Verify RPi tree is not currently a Git repo.
- [x] Verify Milhy-PC repo path and status.

## Phase 2: Preserve History on RPi
- [ ] Copy `.git` directory from Milhy-PC repo into RPi live tree.
- [ ] Configure `.gitignore` for RPi runtime/secrets.
- [ ] Verify RPi Git status.

## Phase 3: Commit Live RPi State
- [ ] Add source/docs/conductor/tests/scripts only.
- [ ] Verify `yt-cookies.txt` and runtime dirs are not staged.
- [ ] Create atomic commit.

## Phase 4: Configure Milhy-PC Gateway
- [ ] Add/update `rpi` remote on Milhy-PC.
- [ ] Verify `git fetch rpi` works.
- [ ] Leave push to GitHub as explicit user-approved action.

## Phase 5: Validation
- [ ] Confirm RPi repo is clean or only expected local runtime changes remain.
- [ ] Confirm Milhy-PC can fetch RPi branch.
- [ ] Conductor - User Manual Verification 'git-live-dev-workflow'.
