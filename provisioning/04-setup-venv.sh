#!/usr/bin/env bash
# 04-setup-venv.sh — Initialize virtual environment and install dependencies with uv
# Idempotent: syncs if venv exists, creates if not.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/rpi-dashboard}"

echo "=== Setting up virtual environment ==="

cd "$INSTALL_DIR"

# Ensure uv is available
if ! command -v uv &>/dev/null; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Sync dependencies (creates venv if needed, installs deps from pyproject.toml)
uv sync

echo "=== Virtual environment ready ==="
echo "To activate: source .venv/bin/activate"
