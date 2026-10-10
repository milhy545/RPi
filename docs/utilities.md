# Utility Scripts

This project also contains helper scripts that are not part of the main runtime API.

## Shell helpers
- `qemu-start.sh` — starts the emulated Raspberry Pi OS environment
- `qemu-stop.sh` — stops the QEMU session
- `chroot-mount.sh` — mounts the image rootfs for offline work
- `chroot-umount.sh` — unmounts the rootfs after work
- `provisioning/*.sh` — provisioning and service-install helpers for fresh setups

## One-off Python helpers
- `fix_tui.py`
- `fix_tui_modes.py`
- `fix_provision.py`

These are maintenance/migration helpers rather than stable public APIs. They do not define a meaningful runtime function set that the dashboard depends on.

## Real usage examples
- Mount the image rootfs before editing a chroot-specific file.
- Boot QEMU to validate TUI behavior in an ARM-compatible environment.
- Use the provisioning scripts only when preparing a fresh image or service install.
