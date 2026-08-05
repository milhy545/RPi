# Repository Guidelines — Raspberry Pi Host (RPi 3B)

## Operating Context

This Raspberry Pi develops and runs RPi-TV. From the home directory (`~`), treat unrelated tasks as host administration: maintenance, diagnostics, recovery, configuration, and service management. Inspect state, preserve user data, prefer reversible actions, and verify changes. The application root is always `/home/milhy777/rpi-dashboard`. For any request involving RPi Dashboard, its code, components, or Conductor tracks, switch there before discovery, planning, Git operations, or writes—even when launched from `~`.

## Safe Validation Pipeline & Host Routing (CRITICAL)

- **Host Gateway Routing**: Milhy-PC is the sole GitHub push and merge gateway. The RPi host MUST NEVER execute `git push` or push code to remote repositories.
- **Playback & User Workload Protection**: Automated RPi candidate validation and hardware checks must NEVER kill, signal, restart, reroute, or disrupt active playback (`mpv`), gaming (`steamlink`, `moonlight`), TUI dashboard modes, audio, Bluetooth, CEC, or system services.
- **Process Abort & Requeue**: If user playback or active mode starts during a candidate validation run, candidate/test processes must be terminated immediately without touching user playback, and the job requeued.
- **Resource Constraints (RPi 3B)**: Target hardware has 4× Cortex-A53 CPU and only 731 MB usable RAM. Sustained user CPU >20%, low free RAM (<50 MB), or thermal limit (>75°C) gates candidate execution. Browsers (Playwright/Chrome/Firefox) are strictly forbidden on RPi.
- **Exact Receipt Requirement**: Agents MUST NOT claim completion ("done", "hotovo", "finished") without an atomic receipt (`conductor/ci/receipts/{sha}-{timestamp}.json`) matching the exact commit SHA or Git tree hash.

## Project Structure & Module Organization

The home directory is an operational workspace, not the source repository. User configuration lives under `~`; scripts belong in `~/bin/` or project tooling directories. Do not modify generated content such as `node_modules/`. For application code and conventions, inspect `~/rpi-dashboard`. Its only authoritative project context is `/home/milhy777/rpi-dashboard/conductor`; `~/conductor` is a compatibility link, never separate state.

## Build, Test, and Development Commands

- `cd ~/rpi-dashboard` enters the application repository before development work.
- `git status --short` checks for existing user changes before editing project files.
- `sudo apt update` refreshes package metadata; do not perform upgrades without reviewing the proposed changes.
- `systemctl --failed` identifies failed system services during diagnostics.
- `df -h` and `free -h` check storage and memory pressure before maintenance or builds.
- `tools/run-ci.sh --profile rpi-focused` runs safe, lightweight RPi unit and syntax checks.

Use the commands documented inside `~/rpi-dashboard` for building and testing. Do not assume that the root-level `package.json` represents the application.

## Coding Style & Naming Conventions

Follow the conventions and formatters configured in `~/rpi-dashboard`. For shell scripts, use `#!/usr/bin/env bash`, quote variable expansions, fail explicitly, and choose descriptive kebab-case filenames. Keep commands and documentation in English. Avoid embedding host-specific secrets or credentials.

## Testing Guidelines

Run the project-defined checks from `~/rpi-dashboard`. For system changes, verification must cover the affected service, relevant logs, resource usage, and expected behavior after the change. Never report success from a command exit code alone when runtime behavior can be checked.

## Commit & Pull Request Guidelines

Git work belongs in `~/rpi-dashboard`, not the home directory. Derive commit conventions from that repository's recent history. Keep commits focused and use short, imperative subjects. Pull requests should explain intent, list verification performed, link relevant issues, and include screenshots for visible RPi-TV changes. Never commit credentials, `.env` files, generated reports, or machine-specific state.
