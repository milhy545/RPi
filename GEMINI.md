# GEMINI.md - RPi Dumb TV Dashboard

## Project Overview
The **RPi Dumb TV Dashboard** is a lightweight, TUI-based (Terminal User Interface) controller designed for low-RAM (1GB) Raspberry Pi devices connected to a living room TV. It serves as a minimal, high-performance replacement for heavy media centers like Kodi, following the "Goat Principle" (Functionality > Aesthetics).

### Core Features
- **Mode Switching:** Zero-overhead switching between the dashboard and full-screen modes:
  - **Game Streaming:** `steamlink` or `moonlight`.
  - **Media Player:** `mpv` with `yt-dlp` integration for ad-free YouTube.
  - **Spotify Kiosk:** `WPE WebKit` for Spotify playback.
- **System Telemetry:** Real-time monitoring of CPU, RAM, and Temperature.
- **Network Casting:** An integrated `aiohttp` API server (port 8090) to receive playback commands from other devices.
- **Screensaver:** A "Matrix Rain" animated screensaver that triggers during inactivity.

## Tech Stack
- **Language:** Python 3.12 (managed via `uv`)
- **TUI Framework:** [Textual](https://textual.textualize.io/)
- **API Server:** `aiohttp`
- **Provisioning:** Shell scripts and `systemd` services.
- **External Tools:** `steamlink`, `moonlight`, `mpv`, `yt-dlp`, `wpe-webkit`.

## Directory Structure
- `main.py`: Minimal CLI entry point.
- `tui.py`: The core Textual dashboard implementation.
- `mode_switcher.py`: Logic for suspending the TUI and launching external modes.
- `conductor/`: Project planning, specs, tech stack, and workflow documentation.
- `provisioning/`: System setup scripts and systemd service files.
- `qemu/` & `rootfs/`: Assets and tools for managing the RPi OS image/chroot.
- `boot_mnt/` & `mnt_root/`: Mount points for image manipulation.

## Development & Usage Commands

### Python Environment
- **Install Dependencies:** `uv sync`
- **Run Dashboard:** `uv run python tui.py`
- **Run Headless API Server:** `uv run python tui.py --headless`
- **Run CLI Entry Point:** `uv run python main.py`

### System Provisioning
- **Full Setup:** `bash provisioning/provision.sh` (installs deps and service).

### Chroot Management
- **Mount rootfs:** `bash chroot-mount.sh`
- **Unmount rootfs:** `bash chroot-umount.sh`

## Development Conventions
- **Indentation:** 4-space indentation for Python.
- **Naming:** 
  - `snake_case` for functions and variables.
  - `PascalCase` for classes.
  - `ALL_CAPS` for constants.
- **Type Annotations:** Strongly preferred for public APIs.
- **Imports:** Grouped by Standard Library, Third-Party, then Local Modules.
- **Shell Scripts:** Quote variables and use explicit commands.

## Testing Guidelines
- **Preferred Framework:** `pytest` (though not yet fully integrated).
- **Manual Verification:** Use `uv run python tui.py` and verify via the dashboard logs or CLI output.
- **Reproduction:** For bug fixes, implement a reproduction script or test case before applying the fix.

## Security
- **Secrets:** Do not commit credentials or secrets. Use `.env` or environment variables.
- **Permissions:** Use `SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A` for privileged operations where necessary.
