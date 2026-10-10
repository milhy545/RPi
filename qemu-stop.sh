#!/bin/bash

# Configuration
MONITOR_SOCK="/tmp/qemu-monitor.sock"

if [ ! -S "$MONITOR_SOCK" ]; then
    echo "Error: QEMU monitor socket not found at $MONITOR_SOCK"
    echo "Is QEMU running?"
    exit 1
fi

echo "Sending system shutdown command to QEMU..."
echo "system_powerdown" | nc -U "$MONITOR_SOCK"

# Wait a few seconds for shutdown, then force quit if it's still alive
sleep 3
if [ -S "$MONITOR_SOCK" ]; then
    echo "QEMU still running. Forcing quit..."
    echo "quit" | nc -U "$MONITOR_SOCK"
fi

echo "QEMU stopped."
