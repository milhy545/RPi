# Implementation Plan for Modularization, Test Coverage, CI, Config & Audio Mixer Fix

## Sprint 1 (Days 1‑2) – Configuration & CI Foundations
1. **Create `config.py`** with all current constants (ports, timeouts, rate‑limit, audio defaults). Replace literals in existing code.
2. **Update CI workflow** (`.github/workflows/ci.yml`): add steps for `mypy`, `ruff`, `pytest‑cov`, Docker build, Trivy scan.
3. Verify that the repository passes the extended CI locally (`./tools/run-ci.sh` updated).

## Sprint 2 (Days 3‑5) – Modularize `webserver.py`
1. Add new modules:
   - `router.py` – registers routes.
   - `handlers.py` – each endpoint function.
   - `utils.py` – helpers (`norm`, `yt_id`, json response helpers).
   - `audio.py` – PulseAudio wrapper (default sink, volume, mute, latency).
   - `cec.py`, `mpv.py` – existing CEC/MPV logic.
2. Refactor `webserver.py` to import and start the server using the router.
3. Run `python -m py_compile` on all new modules.

## Sprint 3 (Days 6‑8) – Audio Mixer Fix
1. Diagnose current audio flow: identify why `audio_set_default` does not affect BT sink.
2. Implement `audio.set_default_sink(sink_name)` in `audio.py` using `pactl set-default-sink` and persist choice to `~/.config/rpi-dashboard/audio_state.json`.
3. Expose a new endpoint `POST /audio/set-sink` that calls the helper.
4. Update WebUI JavaScript to call this endpoint when the user selects a BT sink.
5. Manual test: connect HDMI and BT soundbar, switch via UI, verify audio output with `pactl info`.

## Sprint 4 (Days 9‑11) – Test Coverage Expansion
1. Write unit tests for all functions in `utils.py`, `audio.py`, `router.py`.
2. Write integration tests using `httpx` for HTTP endpoints (`/mpv/*`, `/audio/*`, `/cec/*`, `/modes`, `/report`).
3. Write websocket tests with `pytest‑asyncio` for terminal server.
4. Add `pytest‑cov` config (`coverage.xml`) and enforce ≥ 80 %.

## Sprint 5 (Days 12‑14) – Documentation & Final Polish
1. Draft OpenAPI spec (`openapi.yaml`) describing all endpoints, request/response schemas.
2. Add a static endpoint `/api/docs` that serves the spec or generate HTML via `redoc`.
3. Update `README.md` with badge for API docs and CI status.
4. Run full CI pipeline, fix any lint/type errors.
5. Tag a new release (e.g., `v4.3-modular`) and push.

## Verification
- All CI jobs (type‑check, lint, tests, coverage, Docker scan) pass.
- `git status` clean; `tools/verify-done.sh` returns `0`.
- Audio routing works: when BT sink is selected, `pactl get-default-sink` reflects it and audio output is audible on the BT soundbar.
- API docs are accessible and up‑to‑date.

---
*Prepared by Pi‑coding‑agent on 2026‑06‑26.*