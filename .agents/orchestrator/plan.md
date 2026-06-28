# Overhaul Plan

This plan details the steps to execute the system overhaul for the RPi Dumb TV Dashboard.

## Steps
1. **Milestone 1: Repository Cleanup & Hygiene**
   - Dispatch Explorer to inspect git status, branches, PRs (#15, #20), and config duplication.
   - Dispatch Worker to clean working tree, merge/close PRs, delete merged branches, remove legacy files, unify config, verify with CI.
   - Dispatch Reviewer/Challenger/Auditor to verify hygiene.
2. **Milestone 2: Critical Safety Fixes**
   - Dispatch Explorer to locate all `except Exception: pass`, bare excepts in `keys2mpv.py`, resource leak in `webserver.py:879`, and WebSocket terminal code.
   - Dispatch Worker to fix bare excepts, add context manager, log swallowed exceptions, and add IP allowlist auth to WebSocket terminal.
   - Dispatch Reviewer/Challenger/Auditor to verify fixes.
3. **Milestone 3: Code Quality & Testing**
   - Dispatch Explorer/Worker to add type annotations, docstrings, move legacy test files, configure mypy and ruff in `pyproject.toml`, and expand pytests to ≥60% coverage.
   - Verify with Reviewer/Challenger/Auditor.
4. **Milestone 4: Security Hardening**
   - Dispatch Worker to update WiFi connection API to POST, prevent command line password exposure, add GET action rate limiting, and update CORS to allow LAN subnet/Tailscale.
   - Verify with Reviewer/Challenger/Auditor.
5. **Milestone 5: Feature Tracks Completion**
   - Dispatch Worker to complete Czech i18n, report modal, and TUI mode/terminal menu additions.
   - Verify with Reviewer/Challenger/Auditor.
6. **Final Verification & Handoff**
   - Run full CI and `tools/verify-done.sh` to get the success receipt.
   - Deliver completion report to the Sentinel.
