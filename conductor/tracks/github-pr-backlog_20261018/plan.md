# Implementation Plan: GitHub Pull Request Backlog Resolution

## Phase 1 — Stop Unreviewed Automation

- [x] Disable the repository's unconditional auto-merge workflow.
- [x] Disable all auto-merge requests active in the open PR snapshot.
- [x] Add `merge-approved` label gating, reconcile current label/draft state on every PR event, and test revocation.
- [ ] Re-enable the workflow only after the gated version is on `main`.
- [x] Repair the commit and receipt gates: prevent amend commits, reject runtime artifacts, and make missing receipts fail explicitly.
- [x] Adapt GitHub CI to the repository's local-only Actions policy using direct Git fetch and repository scripts; keep the required `verify-done` context and import exact-main receipts from successful run metadata.
- [x] Configure GitHub CodeQL default setup for Actions, JavaScript/TypeScript, and Python after the active `main` ruleset blocked merging while CodeQL was unconfigured; verify analysis on the exact PR revision before merging.

## Phase 2 — Record and Triage the Backlog

- [x] Capture the initial open PR set and current GitHub `main` SHA.
- [x] Preserve the four local-only commits and create a clean isolated worktree from GitHub `main`.
- [ ] Record one disposition for every initial PR and recheck each PR before any close or merge.
- [x] Close unrelated-project PRs #93 and #96 with `invalid` and a clear explanation.
- [ ] Mark duplicates as `duplicate` only after naming the verified successor.

## Phase 3 — Consolidate and Verify Candidates

- [x] Re-audit PR #85: its current diff contains only placeholder report tracks, a runtime mode file, and generated-report deletions; it was closed as invalid because no application change or valid report record remained to preserve.
- [x] Consolidate accessibility changes, including translated accessible names and the feedback modal close control.
- [x] Consolidate TUI network information changes while retaining DHCP leases and the RPi-service fallback.
- [x] Consolidate network information service changes behind one implementation and test address, route, interface, and fallback behaviour.
- [x] Consolidate the TUI command helper and procfs process detection; add focused tests for PID ancestry, sustained CPU attribution, and candidate termination; exclude generated reports and duplicated tests.
- [x] Audit the locked project environment and prepare fixed versions for the vulnerable `multidict`, `pip`, and `urllib3` packages represented in PR #62.
- [x] Prepare a focused dependency successor for #62, #111, and #113: require patched aiohttp and certifi minimums and pip 26.2.2 in the development extra; keep merging and closing the source PRs gated on the successor.
- [ ] Merge the tested lockfile candidate, then close PR #62 as superseded by that candidate.
- [ ] Review remaining standalone service-status, Kodi-port, and DLNA updates individually.
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
| #93 | Unrelated application/repository files | Closed as invalid after final diff check. |
| #85 | Large sync bundle, app changes, and Conductor reports | Closed as invalid after current-diff audit: only placeholders, runtime state, and generated-report deletions remained; no valid code or report record needed splitting. |
| #92, #94–#95, #97–#102 | Accessibility | Consolidate into a bilingual, tested successor; include the active feedback modal template fix. |
| #42–#43 | TUI Bluetooth event rendering | Keep valid DHCP and Wi-Fi details with a non-empty service fallback; consolidate. |
| #45–#46, #48–#49 | TUI network information | Retain subnet mask and settings/Tailscale semantics in one tested successor. |
| #47, #60–#61, #64, #67 | TUI subprocess helper | Select a safe implementation, test argument handling and timeouts, and exclude reports. |
| #54–#55, #65, #71–#73, #78–#91 excluding #85 | Backend network information | Consolidate behind the service API, preserve compatibility, and test fallback behaviour. |
| #77, #81 | RPi process enumeration | Implementation is present in main; focused unique regressions merged in #116 with an exact-main receipt. #77 closed automatically after #116 merged; #81 closed as superseded. No report deletions were carried over. |
| #56 | Service state detection | Close unless semantics are shown equivalent to `systemctl is-active`. |
| #58 | DLNA process lookup | Review and test procfs behaviour. |
| #62 | Dependency update | #117 carries the current pip floor and patched aiohttp/certifi minima; close as superseded only after that candidate merges. |
| #66 | MPV process signalling | Verify exact process matching and safe signal target; close only after the existing safe implementation in #108 is confirmed. |
| #68 | Kodi port detection | Verify IPv4/IPv6 procfs parsing and call site. |
| #96 | PR-agent workflow | Closed as invalid: duplicate `runs-on`, unpinned third-party action, broad write permissions, and secret exposure. |
| #111, #113 | Modal-close ARIA labels and dependency floors | UI is superseded by #106; preserve the security minimums in #117, then close after the focused successor merges. |

## Change Log

- 2026-10-18: Recorded the 48-PR snapshot, disabled unreviewed auto-merge, and created this isolated worktree from GitHub `main` at `4b7caeed68c2378507d81bba7136fe51e5f64faa`.
- 2026-10-18: Implemented the explicit-label workflow gate and began repairing the local commit/receipt contract; tests and CI are pending.
- 2026-10-18: Added regression coverage for the commit helper, missing/valid receipts, and workflow approval/revocation; 21 targeted tests, ShellCheck, shell syntax, and YAML parsing pass. Full local CI remains pending.
- 2026-10-18: The first full run exposed a host-global `pip-audit` fallback. CI now syncs the locked project environment before auditing it. The project lock had 6 findings across `multidict 6.7.1`, `pip 26.1.2`, and `urllib3 2.7.0`; updated them to `6.9.1`, `26.2.1`, and `2.8.0`. Project-venv `pip-audit` reports no known vulnerabilities. Fixed two host-dependent Bluetooth tests and updated the receipt-contract test. Full CI is rerunning.
- 2026-10-18: GitHub API reports that the repository permits local workflows/actions only; the existing CI invoked prohibited marketplace actions and failed before creating jobs. Replaced those steps with direct Git ref fetching and the locked local CI script, preserved the required `verify-done` check, removed artifact-action dependencies, and changed the RPi handoff to import a receipt from a successful exact-main run. Protected local receipt/report directories from handoff deletion.
- 2026-10-18: First remote CI run confirmed checkout and full tests passed but exposed generated report files in two API integration tests and a detached-checkout assumption in `verify-done.sh`. Redirected test report output to `tmp_path`, kept clean-tree and receipt checks, and made branch tracking checks skip only on detached CI refs after the workflow verifies `GITHUB_SHA`.
- 2026-10-18: Closed unrelated PRs #93 and #96 with the `invalid` label and an explanation after verifying their current diffs.
- 2026-10-18: Current #103 review identified receipt provenance, PR-wide runtime-artifact scanning, missing hosted coverage enforcement, profile validation, and handoff idempotency issues. Fixed these locally, including exact-main receipt lookup, selective transfer of the exact RPi candidate receipt, required project-local quality/security tools, logged failure reports, and isolated report-path tests. The focused regression set passes (44 tests); the new remote CI and Kilo review are pending before merge.
- 2026-10-18: Follow-up review found that detached local checkouts could skip the pushed-state check and that a failed `git status` could look like a clean tree. Detached verification now passes only for a GitHub Actions checkout whose `GITHUB_SHA` and `GITHUB_REF` match; status and runtime-diff inspection errors fail closed. Focused verifier/workflow tests pass (22 tests), and the full local profile and remote review must be rerun on the updated commit.
- 2026-10-18: The next hosted CI run exposed that the runner's PR-wide `VERIFY_BASE_SHA` leaked into synthetic verifier-test repositories, which intentionally have no such base commit. The fixture now clears that CI-only variable unless a test explicitly supplies it; all 7 verifier tests pass locally. Full local CI and updated hosted review are pending.
- 2026-10-18: Required-conversation review exposed two remaining verifier/handoff gaps: local feature branches could accept a PR receipt as completion proof, and rsync could include or delete unrelated receipt files. Verification now requires main-push receipt provenance locally, while PR receipts are exact-SHA-only inside the PR Actions run. Handoff filters include only the exact RPi candidate receipt and protect all other receipts/reports from `--delete`; regression tests cover both. The 28 focused verifier, handoff, and workflow tests pass; full CI and review are pending.
- 2026-10-18: Follow-up review found that `github-safe` could not pass the Milhy-PC gateway without a hardware receipt and that Actions checked out a moving event ref before comparing it with immutable `GITHUB_SHA`. The gateway now requires E2E/RPi evidence only for `milhy-full`, and both CI workflows fetch and check out the event SHA directly. Regression coverage exercises the real no-push gateway path without hardware artifacts. Full CI and hosted reviews are pending.
- 2026-10-18: The focused gateway, workflow, verifier, and handoff set passes (69 tests) after setting the repository `PYTHONPATH`; full `github-safe` and fresh hosted reviews remain required.
- 2026-10-18: The gateway's feature-branch CI dispatch uses `workflow_dispatch`, whose receipt source is distinct from both PR and main-push receipts. `verify-done.sh` now accepts that receipt only for the exact SHA inside the matching Actions event; local completion still requires main-push provenance. A dedicated regression test is added; focused and full CI are pending.
- 2026-10-18: GitHub's active `main` ruleset blocked #103 because the required CodeQL tool was not configured. Enabled GitHub default CodeQL setup for Actions, JavaScript/TypeScript, and Python without weakening branch rules; the initial scan is running, and PR-revision analysis must pass before merge.

- 2026-10-24: Re-audited closed PR #85 against its current diff. It contains only placeholder report tracks, a runtime mode file, and generated-report deletions; no valid application change or user report needs preservation. Added focused procfs guard tests for PID ancestry, sustained CPU averaging, and graceful/forced candidate termination without importing PR report deletions or repeated cases.

- 2026-10-24: PR #116 merged as c0193130ede0aff820c85ea9608b7e8851ac4630 with tree 55ba040e8ea67ef1300fc30062d1a7205ed114b3; main push run 40069464037 passed and wrote conductor/ci/receipts/c0193130ede0aff820c85ea9608b7e8851ac4630-20261024-061627-push.json, with VERIFY-DONE: PASS. The successor adds five focused guard regressions; #77 closed on merge and #81 was closed as superseded.
- 2026-10-24: Audited dependency payloads in #62, #111, and #113. The merged lock already has newer aiohttp and certifi versions, but the declared floors allow affected versions; the lock also has pip 26.2.1. A focused successor now raises the floors to aiohttp>=3.14.4, certifi>=2026.10.19, and pip>=26.2.2 in the development extra.
