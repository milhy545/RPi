# RPi (Raspberry Pi) Development & Monitoring Platform

This repository manages automation scripts, environment configurations, and monitoring utilities for the Raspberry Pi (`KODI-TV` running Debian 13/Trixie) and its associated build/chroot environments.

## Architecture & Environments

1. **Local Workspace (`Milhy-PC`)**: This repository acts as the single source of truth for all tools and configurations.
2. **Build Server (`LLMS`)**: Contains the active `qemu-arm-static` chroot environment under `/home/milhy777/Develop/RPi/rootfs/` where target packages and agent components are built/configured.
3. **Target Device (`KODI-TV / RPi`)**: The actual hardware node (`192.168.0.205`) hosting services, media players, and remote AI agents.

## Repository Contents

* `chroot-mount.sh`: Mounts proc, sysfs, dev, and copies `qemu-arm-static` to initialize the ARM chroot on the build host.
* `chroot-umount.sh`: Safely unmounts chroot filesystems.
* `bin/agy`: Real-time monitoring wrapper script for the Pibot CLI (`pi`). Writes execution state to RAM (`/dev/shm/agy_status`).
* `bin/agy-hud`: Terminal dashboard display tracking running agent sheep.

## Getting Started

### Initializing the Chroot on LLMS
```bash
./chroot-mount.sh
sudo chroot rootfs /bin/bash
```

### Exiting and Cleaning Up Chroot
```bash
exit
./chroot-umount.sh
```
