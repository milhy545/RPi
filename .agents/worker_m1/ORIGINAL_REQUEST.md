## 2026-06-28T09:52:36Z
You are the worker for Milestone 1 (Repo Cleanup & Hygiene).
Your working directory is: /home/milhy777/rpi-dashboard/.agents/worker_m1
Please perform the following implementation tasks:
1. Initialize your progress.md and BRIEFING.md in /home/milhy777/rpi-dashboard/.agents/worker_m1.
2. Recover the lost `yt_id` unit tests from PR #15 (you can find them in the git history of tests/test_webserver.py around commit 3051039, or use git show to extract them) and add them to tests/test_webserver.py.
3. Clean up the working tree: stash or commit the current modified files. (Wait, let's check which files are currently modified and see if they should be committed or kept. You can run git status to check).
4. Delete the legacy files: webserver_8099.py.bak and provisioning/webserver-8099.service.
5. Fix the stale fallback path in tools/extract-webui-js.py from webserver_8099.py to webserver.py.
6. Deduplicate the 6 constants in webserver.py (lines 26-31) and ensure they are imported from config.py.
7. Run the test suite using `uv run pytest` and verify that all tests (including the restored yt_id tests) pass.
8. Verify script validation: run `python3 tools/extract-webui-js.py` without arguments and verify it completes with exit code 0.
9. Verify compilation: run `python3 -m py_compile webserver.py` to ensure import changes are valid.
10. Update your progress.md and write a handoff.md in your working directory when complete.
11. Send a message to the orchestrator (conversation ID: 1185aa9c-d2b0-48fc-8519-b811ce683f65) with the path to your handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
