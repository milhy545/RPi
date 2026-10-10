# Implementation Plan: Git Live Development Workflow

## Phase 1: Safety and Audit
- [x] Check mpv is not running before setup.
- [x] Verify RPi tree is not currently a Git repo.
- [x] Verify Milhy-PC repo path and status.

## Phase 2: Preserve History on RPi
- [x] Copy `.git` directory from Milhy-PC repo into RPi live tree.
- [x] Configure `.gitignore` for RPi runtime/secrets.
- [x] Verify RPi Git status.

## Phase 3: Commit Live RPi State
- [x] Add source/docs/conductor/tests/scripts only.
- [x] Verify `yt-cookies.txt` and runtime dirs are not staged.
- [x] Create atomic commit (`4594298`).

## Phase 4: Configure Milhy-PC Gateway
- [x] Add/update `rpi` remote on Milhy-PC.
- [x] Verify `git fetch rpi` works.
- [x] Leave push to GitHub as explicit user-approved action.

## Phase 5: Validation
- [x] Confirm RPi repo is clean or only expected local runtime changes remain.
- [x] Confirm Milhy-PC can fetch RPi branch.
- [x] Conductor - User Manual Verification 'git-live-dev-workflow'.
