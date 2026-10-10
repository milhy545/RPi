# Implementation Plan: Automated Provisioning

## Phase 1: Dependency Bootstrapping
- [x] Task: Write shell script to install APT dependencies (`mpv`, etc.).
- [x] Task: Add installation routine for `uv` and `yt-dlp`.

## Phase 2: Application Deployment
- [x] Task: Script the cloning/syncing of the repository.
- [x] Task: Use `uv` to initialize the virtual environment and install dependencies.

## Phase 3: Systemd Service
- [x] Task: Create a `dashboard.service` template.
- [x] Task: Script the installation, enabling, and starting of the service.
- [x] Task: Conductor - User Manual Verification 'Systemd Service' (Protocol in workflow.md)

## Completion Notes
- Idempotent provisioning scripts (01-05) implemented and verified.
- `dashboard.service` template created using `%i` instance identifier for multi-user/dynamic deployment.
- Systemd service installation verified (template targets `/dev/tty1` with TTY takeover).
- Current live stack has outgrown this bootstrap scope; treat this as the historical baseline for provisioning.

