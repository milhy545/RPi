#!/usr/bin/env bash
# 05-install-service.sh — Install, enable, and start the dashboard systemd service
# Idempotent: overwrites service file if exists, restarts if already running.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="dashboard"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}@.service"

echo "=== Installing systemd service ==="

# Copy service template
sudo cp "$SCRIPT_DIR/dashboard.service" "$SERVICE_FILE"

# Reload systemd
sudo systemctl daemon-reload

# Enable service for current user
CURRENT_USER="$(whoami)"
sudo systemctl enable "${SERVICE_NAME}@${CURRENT_USER}"

# Start or restart service
if sudo systemctl is-active --quiet "${SERVICE_NAME}@${CURRENT_USER}"; then
    echo "Service already running — restarting..."
    sudo systemctl restart "${SERVICE_NAME}@${CURRENT_USER}"
else
    echo "Starting service..."
    sudo systemctl start "${SERVICE_NAME}@${CURRENT_USER}"
fi

echo "=== Service installed and running ==="
echo "Check status: systemctl status ${SERVICE_NAME}@${CURRENT_USER}"
echo "View logs:    journalctl -u ${SERVICE_NAME}@${CURRENT_USER} -f"
