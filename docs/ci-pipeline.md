# RPi Dashboard CI Pipeline

## 1. Work on a Conductor Track

Use a named feature branch or isolated worktree. Read the track specification and plan before editing, and preserve unrelated work. Milhy-PC is the only host allowed to push or merge on GitHub. The RPi production checkout must not push to GitHub.

## 2. Create a Commit with `tools/finish-track.sh`

```bash
tools/finish-track.sh "fix(webui): preserve accessible modal labels"
```

The script requires a commit message, a named branch, and pending changes. It creates a retained `pre-finish-track-*` stash snapshot, restores the exact staged and unstaged state, runs the selected `tools/run-ci.sh` profile, rejects runtime artifacts, and creates a new commit only after CI passes. It never amends the current commit, pushes a branch, or writes a completion receipt.

The default profile is `rpi-focused` on RPi and `milhy-full` on Milhy-PC. Set `CI_PROFILE=github-safe` for changes whose validation is fully covered by repository CI and that do not need staged-RPi or remote-browser evidence. This profile choice does not waive the required GitHub checks or final receipt.

If CI fails, no commit is created. The worktree and safety snapshot remain available for repair.

## 3. Validate and Merge a Pull Request

Push feature branches only from Milhy-PC. For changes that affect runtime behaviour, complete the staged-RPi hardware guard and remote E2E evidence required by the execution profile before the gateway push. Open or update a pull request and wait for the required `verify-done` and review checks. Merge one reviewed PR at a time using the repository's rebase policy.

The repository Actions policy allows local workflows only. CI fetches the tested ref with Git and runs repository scripts directly; it must not use marketplace actions.

Automatic rebase merging is allowed only when a maintainer applies the `merge-approved` label. Removing that label or converting the pull request to a draft revokes a queued auto-merge request.

## 4. Exact-SHA Completion Receipt

The GitHub Actions CI workflow creates an ephemeral receipt and report while it verifies each run. For completion, a successful `ci.yml` push run for the exact `main` commit is required. `tools/verify-done.sh` checks the current commit and tree, creates a local receipt and report from the matching successful `main` push run when needed, then checks the working tree and gateway state. The workflow does not upload artifacts.

Run the verifier from a clean checkout of the exact `main` commit:

```bash
tools/verify-done.sh
```

An absent or invalid receipt is a failure. A local commit or a green pull-request check alone is not a completion receipt for `main`.

## 5. Host Routing and Data Safety

- **RPi:** use `rpi-focused` for lightweight checks and `rpi-candidate` only for guarded, non-disruptive candidate evidence. Never run browser automation on RPi.
- **Milhy-PC:** use `milhy-full` for full local validation, or `github-safe` for code whose required checks run in GitHub Actions and that does not need hardware or remote-browser evidence.
- **GitHub:** use the required PR checks and merge queue; never bypass branch protection.
- **User data:** preserve report records and dirty work. Do not commit CI reports, receipts, caches, secrets, playback state, or generated E2E results.
- **Candidate safety:** stage candidate code in an isolated worktree. Do not overwrite a dirty production checkout, use `rsync --delete` over unknown state, or interrupt playback, gaming, TUI, audio, Bluetooth, CEC, or system services.

## 6. Failure Handling

| Failure | Commit | Push or merge | Required action |
|---|---|---|---|
| Local CI fails | Not created | No | Repair the change and rerun the selected profile. |
| Runtime artifact is staged | Not created | No | Remove it from the proposed commit without deleting user data. |
| RPi guard or remote E2E fails | May exist on a feature branch | No gateway push or merge | Preserve the candidate and report the exact failing evidence gate. |
| Required GitHub check or review fails | May exist on a feature branch | No merge | Resolve the finding and wait for new checks. |
| Exact-main receipt is missing or invalid | Existing main commit remains | No completion claim | Inspect the exact Actions run; rerun or import only a successful exact-SHA main push. |

## 7. File Reference

- `tools/finish-track.sh` — safety snapshot, local CI gate, artifact check, and non-amending commit.
- `tools/run-ci.sh` — profile-specific local validation.
- `tools/ci-agent.sh` — Milhy-PC gateway checks and evidence-gated push.
- `tools/trigger-ci-handoff.sh` — RPi-to-Milhy-PC handoff and exact-main receipt import.
- `tools/verify-done.sh` — mandatory exact-receipt and worktree check.
- `tools/receipt_lookup.py` and `tools/import_main_receipt.py` — receipt matching and exact-main run import.
- `.github/workflows/ci.yml` — pull-request and main-branch CI.
- `.github/workflows/auto-merge.yml` — explicit `merge-approved` auto-merge gate.
- `conductor/ci/SAFETY-RULES.md` — binding execution and evidence rules.
