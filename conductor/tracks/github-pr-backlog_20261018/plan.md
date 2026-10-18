# Implementation Plan: GitHub Pull Request Backlog Resolution

## Phase 1 — Stop Unreviewed Automation

- [x] Disable the repository's unconditional auto-merge workflow.
- [x] Disable all auto-merge requests active in the open PR snapshot.
- [x] Add `merge-approved` label gating, a label-removal revoke path, and focused workflow tests.
- [ ] Re-enable the workflow only after the gated version is on `main`.
- [x] Repair the commit and receipt gates: prevent amend commits, reject runtime artifacts, and make missing receipts fail explicitly.
- [x] Adapt GitHub CI to the repository's local-only Actions policy using direct Git fetch and repository scripts; keep the required `verify-done` context and import exact-main receipts from successful run metadata.

## Phase 2 — Record and Triage the Backlog

- [x] Capture the initial open PR set and current GitHub `main` SHA.
- [x] Preserve the four local-only commits and create a clean isolated worktree from GitHub `main`.
- [ ] Record one disposition for every initial PR and recheck each PR before any close or merge.
- [ ] Close unrelated-project PRs with `invalid` and a clear explanation.
- [ ] Mark duplicates as `duplicate` only after naming the verified successor.

## Phase 3 — Consolidate and Verify Candidates

- [ ] Split PR #85 into focused code and report changes; retain valid user report records and exclude runtime artifacts.
- [ ] Consolidate accessibility changes, including translated accessible names and the feedback modal close control.
- [ ] Consolidate TUI network information changes while retaining DHCP leases and the `RPi-service` fallback.
- [ ] Consolidate network information service changes behind one implementation and test address, route, interface, and fallback behaviour.
- [ ] Consolidate the TUI command helper and procfs process detection; do not include generated report files.
- [x] Audit the locked project environment and prepare fixed versions for the vulnerable `multidict`, `pip`, and `urllib3` packages represented in PR #62.
- [ ] Merge the tested lockfile candidate, then close PR #62 as superseded by that candidate.
- [ ] Review standalone process, service-status, Kodi-port, and DLNA updates individually.
- [ ] Reject security or workflow changes with invalid YAML, broad permissions, unpinned third-party actions, or unresolved review findings.

## Phase 4 — Merge Sequentially

- [ ] Update each selected PR against the latest `main` and inspect its exact diff.
- [ ] Run the required local checks and candidate-specific tests on Milhy-PC; run safe RPi candidate checks where runtime behaviour is affected.
- [ ] Wait for required GitHub checks and review to pass, then merge one PR at a time using rebase.
- [ ] Recheck and refresh the next candidate after each merge advances `main`.
- [ ] Close replaced duplicates only after the successor merge is confirmed.

## Phase 5 — Verify and Close the Track

- [ ] Confirm the disposition of every PR from the initial snapshot and recheck the live open-PR list.
- [ ] Confirm GitHub `main`, required checks, CI receipt, local worktree state, and the four preserved local-only commits.
- [ ] Run `tools/verify-done.sh`; keep the track active and report exact blockers if any required evidence is unavailable.

## Initial PR Inventory and Intended Direction

| PRs | Topic | Planned handling |
|---|---|---|
| #93 | Unrelated application/repository files | Close as invalid after final diff check. |
| #85 | Large sync bundle, app changes, and Conductor reports | Split; inspect failing Ruff and review findings; preserve valid reports. |
| #92, #94–#95, #97–#102 | Accessibility | Consolidate into a bilingual, tested successor; include the active feedback modal template fix. |
| #42–#43 | TUI Bluetooth event rendering | Keep valid DHCP and Wi-Fi details with a non-empty service fallback; consolidate. |
| #45–#46, #48–#49 | TUI network information | Retain subnet mask and settings/Tailscale semantics in one tested successor. |
| #47, #60–#61, #64, #67 | TUI subprocess helper | Select a safe implementation, test argument handling and timeouts, and exclude reports. |
| #54–#55, #65, #71–#73, #78–#91 excluding #85 | Backend network information | Consolidate behind the service API, preserve compatibility, and test fallback behaviour. |
| #77, #81 | RPi process enumeration | Keep exact procfs matching and focused tests; do not delete report data. |
| #56 | Service state detection | Close unless semantics are shown equivalent to `systemctl is-active`. |
| #58 | DLNA process lookup | Review and test procfs behaviour. |
| #62 | Dependency update | Preserve the pip bump in the corrected lockfile candidate; close as superseded only after that candidate merges. |
| #66 | MPV process signalling | Verify exact process matching and safe signal target. |
| #68 | Kodi port detection | Verify IPv4/IPv6 procfs parsing and call site. |
| #96 | PR-agent workflow | Validate YAML, action pinning, token scope, and secret use; prefer the hardened replacement or close as superseded. |

## Change Log

- 2026-10-18: Recorded the 48-PR snapshot, disabled unreviewed auto-merge, and created this isolated worktree from GitHub `main` at `4b7caeed68c2378507d81bba7136fe51e5f64faa`.
- 2026-10-18: Implemented the explicit-label workflow gate and began repairing the local commit/receipt contract; tests and CI are pending.
- 2026-10-18: Added regression coverage for the commit helper, missing/valid receipts, and workflow approval/revocation; 21 targeted tests, ShellCheck, shell syntax, and YAML parsing pass. Full local CI remains pending.
- 2026-10-18: The first full run exposed a host-global `pip-audit` fallback. CI now syncs the locked project environment before auditing it. The project lock had 6 findings across `multidict 6.7.1`, `pip 26.1.2`, and `urllib3 2.7.0`; updated them to `6.9.1`, `26.2.1`, and `2.8.0`. Project-venv `pip-audit` reports no known vulnerabilities. Fixed two host-dependent Bluetooth tests and updated the receipt-contract test. Full CI is rerunning.
- 2026-10-18: GitHub API reports that the repository permits local workflows/actions only; the existing CI invoked prohibited marketplace actions and failed before creating jobs. Replaced those steps with direct Git ref fetching and the locked local CI script, preserved the required `verify-done` check, removed artifact-action dependencies, and changed the RPi handoff to import a receipt from a successful exact-main run. Protected local receipt/report directories from handoff deletion.
- 2026-10-18: First remote CI run confirmed checkout and full tests passed but exposed generated report files in two API integration tests and a detached-checkout assumption in `verify-done.sh`. Redirected test report output to `tmp_path`, kept clean-tree and receipt checks, and made branch tracking checks skip only on detached CI refs after the workflow verifies `GITHUB_SHA`.
