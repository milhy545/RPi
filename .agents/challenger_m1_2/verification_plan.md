# Verification Plan - Challenger m1_2

This plan outlines the empirical steps to verify the correctness of Milestone 1 updates.

## Action Items
1. **Compilation Check**: Check that all python files compile successfully without errors or warnings.
   - Command: `python3 -m py_compile webserver.py config.py tests/test_webserver.py`
2. **Execute Full Test Suite**: Run all the tests using `pytest` inside the `uv` environment.
   - Command: `uv run pytest`
   - Expect: All 55 tests pass.
3. **Verify Restored yt_id Tests**: Inspect `tests/test_webserver.py` to ensure all 7 custom `yt_id` cases are defined.
4. **Verify Deduplicated Configuration**: Check that the duplication of `MAX_SOCKET_BUFFER`, `SOCKET_RECV_SIZE`, `TERMINAL_POLL_INTERVAL`, `DEFAULT_TIMEOUT`, `CEC_TIMEOUT`, and `MPV_CONNECT_TIMEOUT` between `webserver.py` and `config.py` has been resolved.
5. **Verify Stale Fallback Path in extract-webui-js.py**: Verify that `tools/extract-webui-js.py` has been updated to reference `webserver.py` instead of `webserver_8099.py`.
   - Run: `python3 tools/extract-webui-js.py`
6. **Verify Absense of Stale Files**: Confirm that `webserver_8099.py.bak` and `provisioning/webserver-8099.service` are deleted.
7. **Run Project CI Check**: Run the mandatory verification script `tools/verify-done.sh` to ensure it passes successfully.
   - Command: `tools/verify-done.sh`
