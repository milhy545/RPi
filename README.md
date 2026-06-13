# Raspberry Pi Dumb TV Dashboard

Lightweight, TUI-based dashboard and controller for a low-RAM (1GB) Raspberry Pi connected to a living room TV.

## Project Structure
* `main.py` - Minimal CLI entry point.
* `tui.py` - Interactive dashboard prototype (Textual).
* `qemu-start.sh` - Script to boot the emulated Raspberry Pi OS in QEMU.
* `qemu-stop.sh` - Script to cleanly shut down QEMU.
* `chroot-mount.sh` - Script to mount the rootfs for local chroot environments.
* `chroot-umount.sh` - Script to unmount the rootfs.
* `conductor/` - Framework planning, architecture notes, style guides, and tracks registry.

## Local QEMU & Chroot Development

The project environment is emulated on x86_64 host using `qemu-system-aarch64` and `qemu-aarch64-static` for chroot.

### 1. Booting QEMU VM
To boot the full RPi OS Lite image in QEMU:
```bash
./qemu-start.sh
```
This boots the system in headless mode, mapping the serial console to your terminal. To stop it, run the shutdown script from another terminal:
```bash
./qemu-stop.sh
```
Or exit manually inside the console by pressing `Ctrl-A` then `x`.

### 2. Mounting Chroot for Validation
Alternatively, you can work inside the image's filesystem directly via `chroot` with QEMU static binary interpreter:
```bash
# Mount rootfs and map system virtual directories:
./chroot-mount.sh

# Enter the chroot:
sudo chroot rootfs /bin/bash

# Work inside the image...
# Once done, exit the chroot and unmount the virtual directories:
./chroot-umount.sh
```

## Running the Dashboard
All dependencies are managed via `uv`.
```bash
# Sync dependencies
uv sync

# Run the TUI
uv run python tui.py
```
