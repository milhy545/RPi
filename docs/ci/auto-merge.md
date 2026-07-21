# Automated Pull Request Merge

Pull requests targeting `main` are queued for native GitHub auto-merge when
they are opened, updated, reopened, or marked ready for review. Draft pull
requests are excluded.

The repository keeps a required approving review. After the `verify-done` CI
job succeeds, `github-actions[bot]` submits that approval through the existing
GitHub Actions permission to create and approve pull requests. A new commit
dismisses the stale approval and reruns the gate.

Branch protection also requires these checks:

- `verify-done`
- `Kilo Code Review`

All review conversations must be resolved. The merge method is rebase, which
keeps `main` linear. Because GitHub can rewrite commit metadata and SHA during
rebase, `verify-done.sh` accepts the original Conductor receipt only when its
Git tree hash exactly matches the rebased commit. GitHub performs the merge only
after every required review, conversation, and status check is satisfied, and
then deletes the source branch.

Copilot and Codex reviews remain advisory. GitHub Copilot code review submits
comments rather than approvals, so it cannot satisfy the required approval by
itself.
