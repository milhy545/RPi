# Milestone 1: Repo Cleanup & Hygiene Handoff Report

## 1. Observation

### Repository Status & Branch Configuration
- **Branch**: Currently on `main` (renamed from `master` in commit `1e29557`).
- **Stashes**: Two stashes exist in the repository:
  ```text
  stash@{0}: On main: pre-finish-track-20260628-022402
  stash@{1}: On main: ci.yml-stash
  ```
- **PR Management**: The repository only tracks standard remote branches via fetch refspec `+refs/heads/*:refs/remotes/origin/*`. PRs (#15 and #20) are managed remotely on GitHub.
- **PR #15 & PR #20 Integration**:
  - In commit `3051039` (`chore: apply Jules PRs manually + code review + system overhaul plan`), Milhy manually applied both PRs:
    * **PR #20**: Unused imports (`time`, `glob`) were removed from `keys2mpv.py`. This fix remains intact.
    * **PR #15**: `yt_id` unit tests were added to `tests/test_webserver.py`.
  - In commit `b567742` (`refactor: rename webserver_8099.py → webserver.py + standard ports`), the entire contents of `tests/test_webserver.py` were replaced with `test_norm` unit tests. Consequently, the `yt_id` tests from PR #15 were lost.
  - Verification of the lost PR #15 tests in `3051039` show the following deleted test definitions:
    ```python
    def test_yt_id_standard_url()
    def test_yt_id_short_url()
    def test_yt_id_shorts_url()
    def test_yt_id_embed_url()
    def test_yt_id_with_extra_params()
    def test_yt_id_invalid_urls()
    def test_yt_id_with_whitespace()
    ```

### Modified and Untracked Files
- **9 Modified files** in the working tree:
  1. `.github/workflows/ci.yml`
  2. `pyproject.toml`
  3. `router.py`
  4. `tools/ci-agent.sh`
  5. `tools/finish-track.sh`
  6. `tools/run-ci.sh`
  7. `tools/verify-done.sh`
  8. `uv.lock`
  9. `webserver.py`
- **1 Untracked test file**:
  * `tests/test_rate_limit_post_get.py`
- Note: `.agents/` is also untracked but contains only agent metadata.

### Legacy Files
- `webserver_8099.py.bak` (42,865 bytes) is located in the repository root.
- `provisioning/webserver-8099.service` (761 bytes) is located in the `provisioning/` directory.

### Stale Fallback Path
- In `/home/milhy777/rpi-dashboard/tools/extract-webui-js.py` line 10, the default fallback file is hardcoded as `webserver_8099.py`:
  ```python
  source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("webserver_8099.py")
  ```
  Since `webserver_8099.py` was renamed to `webserver.py`, this fallback path is stale and will fail if no arguments are provided.

### Duplicated Configuration Constants
- Six constants are defined in `config.py` (lines 25-30) and duplicated verbatim in `webserver.py` (lines 26-31):
  ```python
  MAX_SOCKET_BUFFER = 65536
  SOCKET_RECV_SIZE = 4096
  TERMINAL_POLL_INTERVAL = 0.35
  DEFAULT_TIMEOUT = 3
  CEC_TIMEOUT = 5
  MPV_CONNECT_TIMEOUT = 2
  ```

### Current CI and Test Status
- Running `uv run pytest` results in **48 tests passing** (duration: 42.06s).
- Running syntax compilation via `python3 -m py_compile webserver.py tui.py mode_switcher.py keys2mpv.py config.py router.py handlers.py` passes cleanly with no errors.

---

## 2. Logic Chain

1. **Working Tree Assessment**: A standard `git status` check confirms there are 9 modified files in the working tree and 1 untracked test file (`tests/test_rate_limit_post_get.py`).
2. **Branch & PR Analysis**:
   - `git branch -a` shows only local and remote `main`.
   - `git log` show commit `3051039` manually cherry-picked the code from PR #15 and PR #20.
   - Comparative log inspection on `tests/test_webserver.py` reveals that commit `b567742` replaced the `yt_id` tests with `test_norm`.
   - Therefore, PR #15's tests are currently missing from the codebase.
3. **Legacy Files Identification**: Listing the repository root and `provisioning/` directories confirms that `webserver_8099.py.bak` and `provisioning/webserver-8099.service` remain from before the webserver refactoring.
4. **Stale References**: Examining `tools/extract-webui-js.py` shows it references the renamed `webserver_8099.py` on line 10, which will cause runtime failures when running syntax checks without arguments.
5. **Configuration Duplication**: Line-by-line inspection of `config.py` (lines 25-30) and `webserver.py` (lines 26-31) shows identical variable names and values, indicating they are not dry-imported.
6. **Tests Execution**: Running `uv run pytest` directly proves that all existing unit tests are green, confirming current stability.

---

## 3. Caveats

- **Sandbox Restrictions**: Due to local sandbox constraints, the full `tools/run-ci.sh` could not be executed because it invokes shell environments (`bash -lc`) that touch files outside the workspace. However, all critical sub-steps (lint compile, unit testing) were individually verified.
- **GitHub Connection**: Because of the CODE_ONLY network configuration, the remote status of PR #15 and PR #20 on the GitHub origin server could not be queried directly. The analysis is based on git history and metadata files inside the repository.

---

## 4. Conclusion

The repository is functional and stable, but requires hygiene corrections:
1. **Restore PR #15 Tests**: Re-add the 7 missing `yt_id` tests to `tests/test_webserver.py`.
2. **Deduplicate Configuration**: Remove the duplicated constants from `webserver.py` (lines 26-31) and import them from `config.py` instead.
3. **Remove Stale Files**: Safely delete the legacy `webserver_8099.py.bak` and `provisioning/webserver-8099.service` files.
4. **Fix Stale Script Reference**: Update `tools/extract-webui-js.py` line 10 default fallback to `webserver.py`.

---

## 5. Verification Method

To verify that cleanup is completed successfully, the next agent should run:
1. **Test Suite**: Run `uv run pytest` to ensure all 48 tests (plus the restored `yt_id` tests) pass.
2. **Script Validation**: Run `python3 tools/extract-webui-js.py` without arguments and verify it successfully extracts JavaScript from `webserver.py` (and exit code is 0).
3. **Compilation Check**: Run `python3 -m py_compile webserver.py` to ensure import changes for the configuration constants are valid.
4. **File Check**: Run `ls webserver_8099.py.bak provisioning/webserver-8099.service` and verify that the files are no longer present.
