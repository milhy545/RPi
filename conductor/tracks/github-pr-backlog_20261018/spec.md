# Track Spec: GitHub Pull Request Backlog Resolution

## Context and Objective

The repository has a large set of open, overlapping pull requests. Several are queued for automatic merge without an explicit maintainer decision, and multiple PRs include stale generated reports or changes for unrelated repositories. Resolve the backlog from Milhy-PC, the sole GitHub push and merge gateway, while preserving user data and the local-only commits on the development checkout.

## Binding Decisions

1. Existing auto-merge requests are disabled while the backlog is reviewed.
2. Auto-merge is permitted only after a maintainer applies the `merge-approved` label. Removing that label revokes any queued auto-merge request.
3. PR #85 is split and verified; it is not merged as-is. Valid Conductor report records are preserved and reviewed for duplicates. Runtime report artifacts are excluded.
4. PRs for unrelated projects are closed with an explanation. Duplicate PRs are closed only after their unique changes are incorporated into a verified successor.
5. Every merged candidate must target current `main`, pass required checks and review, and be merged sequentially using the repository's linear-history policy.
6. Local-only commits on the development checkout are preserved and are not pushed as part of this work.
7. RPi candidate checks must use the isolated candidate worktree and the non-disruptive hardware guard. Never push from RPi or disturb playback, gaming, TUI, audio, Bluetooth, CEC, or system services.

## Acceptance Criteria

- The auto-merge workflow has an explicit label gate, least-required permissions, and a tested revoke path when the label is removed.
- Every PR in the initial open-backlog snapshot has a recorded final disposition: merged, closed as invalid, closed as superseded by a named successor, or left open with an exact blocker.
- Unique and valid changes from duplicate PRs are retained in a tested successor. Generated `reports/*.json` deletions or additions are not merged.
- PR #85 is split into focused successors; no unreviewed bundle of unrelated code and user reports is merged.
- Merges proceed one at a time, with the base rechecked and required GitHub checks green before each merge.
- The final report names every remaining blocker and includes exact PR numbers, commit SHAs, check evidence, and any resulting main-branch CI receipt.
