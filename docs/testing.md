# Tests and Verification

## Safe tests

### `test_testaudio_webui.py`
Validates the live WebUI without mutating audio routing.

#### `get(path)`
Fetches a live endpoint and decodes JSON when possible.

#### `check(name, ok, detail=None)`
Prints PASS/FAIL lines and returns a failure count contribution.

#### `main()`
Runs the safe end-to-end audio and WebUI validation suite.

Checks:
- main tabs exist
- Audio layout markers are present
- Audio state endpoint returns the expected schema
- invalid audio inputs return JSON errors
- safe self-test endpoint works
- device, Wi‑Fi, and YouTube cookie diagnostics are present

**Run**
```bash
python3 test_testaudio_webui.py
```

### `test_audio_mutating_webui.py`
Opt-in mutating smoke test.

#### `get(path)`
Fetches a live endpoint and decodes JSON when possible.

#### `main()`
Runs the opt-in mutating smoke test when the enabling environment variable is set.

It is disabled by default. Enable it only when you explicitly want to test real routing changes.

**Run**
```bash
RPIDASHBOARD_MUTATING_AUDIO_TESTS=1 python3 test_audio_mutating_webui.py
```

## Legacy / broader tests

### `test_dashboard.py`
Exercises dashboard state switching, watchdog handling, crash recovery, and signal teardown.

#### `run_tests()`
Runs the asynchronous Textual dashboard behavior suite.

#### `test_mode_switcher_suite()`
Pytest entry point for the dashboard suite.

### `test_production_api.py`
Historical integration test for the older API surface.

#### `make_request(path, method="GET", payload=None, headers=None)`
Helper for making JSON API requests.

#### `main()`
Runs the historical integration flow.

#### `test_production_api_suite()`
Pytest entry point for the historical integration test.

## What the safe audio test proves
- The WebUI is reachable
- The Audio tab is present
- The new Devices tab is present
- The Player tab hosts the YouTube cookie/age diagnostics
- `/selftest/testaudio` returns `ok: true`
- `/audio/state` is safe under concurrent access

## Real verification examples
- After editing WebUI HTML, run `python3 test_testaudio_webui.py`
- After editing JS strings in `webserver_8099.py`, run `node --check` on the extracted script
- After changing audio logic, hit `/audio/state` several times in parallel to verify it stays responsive
