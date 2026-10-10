#!/bin/bash

# Configuration
QEMU_DIR="/media/Backup/RPi/qemu"
IMAGE="/home/milhy777/rpios_new.img"
KERNEL="$QEMU_DIR/Image"
DTB="$QEMU_DIR/bcm2710-rpi-3-b.dtb"
MONITOR_SOCK="/tmp/qemu-monitor.sock"

# Check if image exists
if [ ! -f "$IMAGE" ]; then
    echo "Error: QEMU image not found at $IMAGE"
    exit 1
fi

echo "Starting QEMU Raspberry Pi 3B emulation..."
echo "To exit QEMU manually, press Ctrl-A then x"
echo "Or use ./qemu-stop.sh from another terminal"

# QEMU Command
# Using raspi3b machine
# Memory is fixed to 1G for raspi3b
# Port 2225 forwarded to 22 for SSH
# console=ttyAMA0 for serial output
# -monitor unix socket for controlled shutdown
qemu-system-aarch64 \
    -M raspi3b \
    -cpu cortex-a53 \
    -m 1G \
    -kernel "$KERNEL" \
    -dtb "$DTB" \
    -drive file="$IMAGE",format=raw,if=sd \
    -append "rw earlyprintk loglevel=8 console=ttyAMA0,115200 root=/dev/mmcblk0p2 rootdelay=1" \
    -netdev user,id=net0,hostfwd=tcp::2225-:22,hostfwd=tcp::8091-:8090 \
    -device usb-net,netdev=net0 \
    -monitor unix:"$MONITOR_SOCK",server,nowait \
    -nographic

