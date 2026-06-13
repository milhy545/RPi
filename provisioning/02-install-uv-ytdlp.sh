#!/usr/bin/env bash
# 02-install-uv-ytdlp.sh — Install uv (Python package manager) and yt-dlp
# Idempotent: safe to run multiple times.
set -euo pipefail

echo "=== Installing uv and yt-dlp ==="

# Install uv (official installer)
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "uv already installed: $(uv --version)"
fi

# Install yt-dlp (standalone binary)
if ! command -v yt-dlp &>/dev/null; then
    echo "Installing yt-dlp..."
    sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
    sudo chmod a+rx /usr/local/bin/yt-dlp
else
    echo "yt-dlp already installed: $(yt-dlp --version)"
fi

echo "=== uv and yt-dlp installed successfully ==="
