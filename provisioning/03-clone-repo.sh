#!/usr/bin/env bash
# 03-clone-repo.sh — Clone or sync the Dumb TV Dashboard repository
# Idempotent: pulls if repo exists, clones if not.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/milhy777/RPi.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/rpi-dashboard}"

echo "=== Cloning/syncing repository ==="

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Repository exists at $INSTALL_DIR — pulling latest..."
    cd "$INSTALL_DIR"
    git pull --ff-only
else
    echo "Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo "=== Repository synced to $INSTALL_DIR ==="
