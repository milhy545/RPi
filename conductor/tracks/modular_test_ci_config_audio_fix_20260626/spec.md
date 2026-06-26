# Track: Modularization, Test Coverage, CI Enhancements, Config Refactor & Audio Mixer Fix

## Goal
Refactor the RPi‑TV Dashboard codebase to be **modular**, improve **test coverage**, extend **CI** pipelines, centralize **configuration constants**, enrich **API documentation**, and **fix the audio mixer** so that Bluetooth soundbars work correctly when selected.

## Tasks
| Area | Description | Acceptance Criteria |
|------|--------------|---------------------|
| **Modularization** | Split `webserver.py` into logical sub‑modules: `router.py`, `handlers.py`, `utils.py`, `audio.py`, `cec.py`, `mpv.py`, etc. | - Each endpoint lives in its own function inside `handlers.py`.<br>- Router maps `path -> handler`.
| **Test Coverage** | Add comprehensive tests covering: <br>• All HTTP GET/POST endpoints (`/mpv/*`, `/audio/*`, `/cec/*`, `/modes`, `/report`).<br>• WebSocket terminal flow using `pytest‑asyncio`.<br>• Unit tests for utility functions (`norm`, `yt_id`, audio routing helpers). | - Coverage reported by `pytest‑cov` ≥ 80 %.
| **CI / GitHub Actions** | Extend workflow `ci.yml` (or create `ci_extended.yml`): <br>• Run `mypy` for static typing.<br>• Run `ruff` for lint/formatting.<br>• Run `pytest‑cov` and fail if coverage < 80 %.
>• Add Docker build step and security scan with `trivy` or `snyk`.
| **Constants / Config** | Create `config.py` (or `.env`) that defines all tunables: ports, timeouts, rate‑limit, audio defaults, etc. Replace hard‑coded literals throughout the code. | - `webserver.py` imports from `config` only.
| **Documentation** | Generate OpenAPI/Swagger spec (can be manual JSON/YAML) describing all endpoints. Add link in `README.md`. | - `README.md` contains a badge/link to the API spec.
| **Audio Mixer Fix** | Investigate why audio output stays on HDMI even when a Bluetooth sink is selected via WebUI. Likely issues: default sink not being set, PulseAudio vs ALSA mismatch, missing `pactl set-default-sink` call. Implement robust sink switching and persist the choice. | - When user selects a Bluetooth sink in the UI, audio routes to the BT device (verified by `pactl list sinks`).<br>- UI reflects correct sink (HDMI ↔ BT).<br>- No regression for existing HDMI functionality.

## Acceptance Criteria
1. **Modular code** builds and passes `python -m py_compile`.
2. All new unit and integration tests pass on CI.
3. CI pipeline runs `mypy`, `ruff`, `pytest‑cov`, Docker build + scan without failures.
4. Configuration is externalized; changing a port in `config.py` updates server behavior without code changes.
5. API documentation is generated and accessible (`/api/docs` or a static file).
6. Audio routing works for both HDMI and Bluetooth soundbars; UI correctly indicates active sink.

## Implementation Sketch
- **router.py**: defines a `ROUTES` dict mapping path strings to handler callables.
- **handlers.py**: contains functions like `handle_mpvs_play`, `handle_audio_state`, etc.
- **audio.py**: wraps PulseAudio calls (`pactl set-default-sink`, `pactl list sinks`, volume, mute, latency). Ensure errors are caught and logged.
- **config.py**: central constants (ports, timeouts, rate‑limit seconds, etc.). Loaded at import time.
- **tests/**: new directory `tests/integration/` with HTTP client tests; `tests/websocket/` for terminal.
- **ci.yml**: add steps `- name: Type check` → `mypy .`; `- name: Lint` → `ruff .`; `- name: Coverage` → `pytest --cov=.`; `- name: Docker build` → `docker build .`; `- name: Scan` → `trivy image <image>`.
- **Audio fix**: In `audio.py` replace direct `pactl set-*-mute` calls with a higher‑level `set_default_sink(sink_name)` that updates `DEFAULT_SINK` variable and persists to a small JSON file (`~/.config/rpi-dashboard/audio_state.json`). Update UI code (`webui.js`) to call new endpoint `/audio/default-sink` which now invokes the helper.

## Next Steps
1. Create `config.py` and migrate existing constants.
2. Extract routing logic into `router.py` and move each endpoint implementation into `handlers.py`.
3. Write unit tests for each handler.
4. Add audio sink selection endpoint (`/audio/set-sink`).
5. Update CI workflow.
6. Generate OpenAPI spec (e.g., `openapi.yaml`).
7. Verify audio routing on a real RPi with a Bluetooth soundbar.

---
*Track created by Pi‑coding‑agent on 2026‑06‑26.*
