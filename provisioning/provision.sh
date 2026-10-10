#!/usr/bin/env bash
# provision.sh — Master provisioning script for Dumb TV Dashboard
# Runs all setup steps in order. Idempotent: safe to run multiple times.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "╔══════════════════════════════════════════════════╗"
echo "║   Dumb TV Dashboard — Automated Provisioning    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Step 1: Install APT dependencies
bash "$SCRIPT_DIR/01-install-apt-deps.sh"

# Step 2: Install uv and yt-dlp
bash "$SCRIPT_DIR/02-install-uv-ytdlp.sh"

# Step 3: Clone/sync repository
bash "$SCRIPT_DIR/03-clone-repo.sh"

# Step 4: Setup virtual environment
bash "$SCRIPT_DIR/04-setup-venv.sh"

# Step 5: Install systemd service
bash "$SCRIPT_DIR/05-install-service.sh"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Provisioning complete!                        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "The dashboard service is now running."
echo "Check status: systemctl status dashboard@$(whoami)"
echo "View logs:    journalctl -u dashboard@$(whoami) -f"
