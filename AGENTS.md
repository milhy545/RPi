# Repository Guidelines

## Operating Context

This repository contains the RPi-TV Dashboard. The production checkout is `/home/milhy777/rpi-dashboard` on host `RPi`; the development and GitHub gateway mirror is `/home/milhy777/Develop/RPi` on `Milhy-PC`. Resolve the Git root and host before changing runtime state. Preserve user data, prefer reversible changes, and verify behaviour on the affected host.

## Project Structure & Module Organisation

- `webserver.py` is the WebUI/API compatibility entrypoint; HTTP routing lives in `rpi_dashboard/api/`.
- `rpi_dashboard/services/` contains audio, Bluetooth, player, devices, CEC, terminal, smart-home, and system logic.
- `rpi_dashboard/static/` contains the WebUI HTML, CSS, JavaScript, manifest, and service worker.
- `tui.py` is the production Textual dashboard. `rpi_dashboard/tui/modern.py` remains a non-production prototype.
- `tests/` contains pytest coverage; `tests/e2e/` contains the Playwright hardware smoke flow.
- `provisioning/` and `systemd/` contain deployment assets. `conductor/` is the intended product and track record; validate completion against its plan, CI, and receipt.
- `.agents/` and `.Jules/` contain agent-specific configuration and session state.

Do not edit caches, reports, receipts, logs, or runtime files unless the task explicitly targets them.

## Build, Test, and Development Commands

- `uv sync --extra dev` installs Python runtime and development dependencies.
- `uv run python tui.py` starts the TUI; `uv run python webserver.py` starts the WebUI/API.
- `uv run python -m pytest -q` runs Python tests.
- `uv run ruff check .` and `uv run mypy .` run lint and type checks.
- `cd tests/e2e && npm install` installs Playwright. Run hardware E2E from Milhy-PC with `TARGET_URL=http://192.168.0.205:8080 npm test`.
- `tools/run-ci.sh` runs the repository CI checks. `tools/verify-done.sh` is mandatory before any completion claim.

## Coding Style & Testing

Use Python 3.12, four-space indentation, type hints on public APIs, `snake_case` Python names, and `kebab-case` shell scripts. Keep service logic out of HTTP handlers. Write code and primary documentation in UK English and maintain matching `*.cz.md` documentation.

Add focused `test_<behaviour>.py` coverage near changed behaviour. Mock hardware commands such as `pactl`, `bluetoothctl`, `nmcli`, `cec-client`, and `mpv` unless explicitly performing live RPi validation. WebUI changes require Playwright or equivalent browser evidence; service changes require logs, process, port, and API/UI verification.

## Commits, Pull Requests, and Agent Safety

Use short imperative Conventional Commit subjects, for example `fix(webui): remove duplicate status bar`. Pull requests must describe intent, affected modules, verification, linked track or issue, screenshots for UI changes, and hardware impact.

Before editing, run `git status --short` and preserve unrelated changes. Follow `conductor/ci/SAFETY-RULES.md`: use `tools/finish-track.sh` for commits, never push directly from RPi, and report an exact blocker whenever `tools/verify-done.sh` fails.

## Safe Validation Pipeline & Host Routing

- **Sole Push Gateway**: Milhy-PC is the sole GitHub push and merge gateway. The RPi host MUST NEVER execute `git push` or push commits to GitHub.
- **Execution Profiles**:
  - `rpi-focused`: Lightweight unit & syntax checks for RPi (no full pytest or browser runs).
  - `milhy-full`: Full pytest suite, Ruff, mypy, security tools, and remote Playwright E2E.
  - `rpi-candidate`: Non-mutating hardware smoke on staged candidate worktree on RPi.
  - `github-safe`: Final CI gateway verification on Milhy-PC prior to GitHub push.
- **Playback & User Protection**: Candidate checks on RPi must NEVER disrupt active playback (`mpv`), gaming (`steamlink`/`moonlight`), TUI modes, audio, Bluetooth, CEC, or system services. If playback starts during candidate validation, candidate processes are terminated immediately and requeued.
- **Candidate Staging**: Candidate code is staged in isolated worktrees (`/home/milhy777/rpi-dashboard-candidate-<sha>`). Never overwrite or `rsync --delete` over dirty live checkouts.
- **Exact Receipt Requirement**: Agents MUST NOT claim completion without an atomic receipt (`conductor/ci/receipts/{sha}-{timestamp}.json`) matching the exact commit SHA or Git tree hash.

## 💻 Hardware & Performance (Critical)

This system runs on extremely constrained hardware. Every line of code must account for this:

- **Target HW:** Raspberry Pi 3 Model B (4× Cortex-A53, only **731 MB usable RAM**).
- **Limitations:** Shared L2 cache (only 512 KB) creates a memory throughput bottleneck. The CPU is prone to thermal throttling.
- **Coding Rule:** Backend and frontend must be extremely lightweight. Avoid CPU-intensive blocking operations. Aggressively use non-blocking asyncio architecture, conserve memory, and avoid creating unnecessary threads unless absolutely essential (e.g., isolating a crashing D-Bus call).

## 🌍 Globální pravidla (Global Rules)

- **Language (Critical):** Always communicate, explain steps, propose plans, and write code comments **exclusively in Czech**.
- **Conductor Standard:** All development follows Conductor tracks in `conductor/tracks/`. Always read the relevant `spec.md` and `plan.md` before starting a task.
- **Goat Principle:** Don't be unnecessarily verbose — be pragmatic. Before refactoring, ensure you have exact data and context.

## 🛠️ Architektura a Vývoj (Dev Guidelines)

- **Backend:** Written in Python using asyncio. Avoid blocking calls, especially with D-Bus.
- **BlueZ & D-Bus:** Any D-Bus crashes must be caught via custom exceptions (e.g. `BluetoothDBusError`). The system must never crash. Use isolated Threads or pure async approaches for D-Bus calls.
- **Frontend:** No React/Angular. UI changes are made in vanilla JS, HTML, and CSS (Tailwind).
- **Testing:** Every implementation must pass local tests. Pytest for backend, Playwright for E2E.

## 🤖 Conductor Workflow (Jules Instructions)

Since Jules operates primarily over the repository without complex external skills, follow this manual procedure for every task:

1. **Context:** Read this `AGENTS.md` at the start of every new session.
2. **Task (Spec):** Find your concrete task for the session. It will be stored in `spec.md` (e.g. `conductor/tracks/<track-name>/spec.md`).
3. **Plan & Architecture:** Along with the spec, also read `plan.md` in the same folder to understand the broader context and logic of the task.
4. **Execution:** Follow the spec step by step. Before creating a Pull Request, verify syntax and run local tests in your sandbox environment (using mocks where the real Raspberry Pi hardware is unavailable).
