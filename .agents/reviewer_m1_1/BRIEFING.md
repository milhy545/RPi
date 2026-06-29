# BRIEFING — 2026-06-28T10:59:00+01:00

## Mission
Review and verify Milestone 1 (Repo Cleanup & Hygiene) changes, ensuring test suite passes, files are clean, compilation succeeds, and tools run correctly.

## 🔒 My Identity
- Archetype: reviewer and adversarial critic
- Roles: reviewer, critic
- Working directory: /home/milhy777/rpi-dashboard/.agents/reviewer_m1_1
- Original parent: 1185aa9c-d2b0-48fc-8519-b811ce683f65
- Milestone: Milestone 1 (Repo Cleanup & Hygiene)
- Instance: 1 of 1

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code.
- Speak Czech to user; write ALL code/docs/commands/memories/rules in English. (Parent agent is English-speaking).
- RPi CI: MUST run tools/verify-done.sh before claiming done.
- Never dismiss failures — always full diagnostics.

## Current Parent
- Conversation ID: 1185aa9c-d2b0-48fc-8519-b811ce683f65
- Updated: not yet

## Review Scope
- **Files to review**:
  - `tests/test_webserver.py` (restored yt_id tests)
  - `webserver.py` (constant deduplication)
  - Removal of `webserver_8099.py.bak` and `provisioning/webserver-8099.service`
  - `tools/extract-webui-js.py` (fallback path fix)
- **Interface contracts**: `PROJECT.md`, `GEMINI.md`, `AGENTS.md`
- **Review criteria**: Correctness, completeness, robustness, compiling webserver.py, running tools/extract-webui-js.py, clean pytest run (55 passing).

## Review Checklist
- **Items reviewed**: [TBD]
- **Verdict**: pending
- **Unverified claims**: [TBD]

## Attack Surface
- **Hypotheses tested**: [TBD]
- **Vulnerabilities found**: [TBD]
- **Untested angles**: [TBD]

## Key Decisions Made
- Initial setup and briefing creation.

## Artifact Index
- `/home/milhy777/rpi-dashboard/.agents/reviewer_m1_1/handoff.md` — Handoff and Quality Review/Adversarial Report.
