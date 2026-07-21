#!/usr/bin/env bash
# 01-install-apt-deps.sh — Install system APT dependencies for Dumb TV Dashboard
# Idempotent: safe to run multiple times.
set -euo pipefail

echo "=== Installing APT dependencies ==="

# Core packages
APT_PACKAGES=(
    mpv
    cage
    cog
    python3
    python3-pip
    python3-venv
    git
    tmux
    fonts-terminus
    curl
    wget
    unzip
    build-essential
    libffi-dev
    libssl-dev
)

# Update package lists
sudo apt-get update -qq

# Install packages (apt-get install is idempotent)
sudo apt-get install -y --no-install-recommends "${APT_PACKAGES[@]}"

echo "=== APT dependencies installed successfully ==="
