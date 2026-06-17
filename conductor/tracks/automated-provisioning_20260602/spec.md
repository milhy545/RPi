# Specification: Automated Provisioning

## Overview
Create a set of automation scripts (Shell or Ansible) to bootstrap a fresh Raspberry Pi OS (or QEMU image) with all necessary dependencies for the Dumb TV Dashboard.

## Functional Requirements
- Install system dependencies: `mpv`, `python3`, `git`, `tmux`, etc.
- Install `uv` for Python package management.
- Install `yt-dlp` binary to a path accessible by `mpv`.
- Generate and enable a `systemd` service to auto-start the Dashboard on boot.

## Non-Functional Requirements
- Idempotent execution (running the script multiple times is safe).
- Minimal dependencies required for the provisioning script itself.

## Out of Scope
- Advanced network configuration (Tailscale) - manual setup is acceptable for now.
