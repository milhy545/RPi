#!/bin/bash
# Build and install gmrender-resurrect on RPi
# Lightweight UPnP/DLNA MediaRenderer (~20 MB)
set -euo pipefail

RENDERER_NAME="${1:-RPi Renderer}"
BUILD_DIR="/tmp/gmrender-build"
INSTALL_PREFIX="/usr/local"
# shellcheck disable=SC2034
SERVICE_USER="milhy777"  # used by sourced provisioning scripts

echo "=== gmrender-resurrect build script ==="
echo "Renderer name: $RENDERER_NAME"

# 1. Install build dependencies
echo "[1/5] Installing build dependencies..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    build-essential \
    automake \
    autoconf \
    libtool \
    pkg-config \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libupnp-dev \
    libxml2-dev \
    libgirepository1.0-dev \
    gir1.2-gstreamer-1.0 \
    gir1.2-gupnp-1.6

# 2. Clone and build
echo "[2/5] Cloning gmrender-resurrect..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
git clone --depth 1 https://github.com/hzeller/gmrender-resurrect.git
cd gmrender-resurrect

echo "[3/5] Building..."
./autogen.sh
./configure --prefix="$INSTALL_PREFIX"
make -j"$(nproc)"

echo "[4/5] Installing..."
sudo make install

# 5. Verify installation
echo "[5/5] Verifying..."
if command -v gmediarender &>/dev/null; then
    echo "✅ gmediarender installed successfully"
    gmediarender --help 2>&1 | head -5 || true
else
    echo "❌ Installation failed - binary not found"
    exit 1
fi

# Cleanup
rm -rf "$BUILD_DIR"

echo ""
echo "=== Installation complete ==="
echo "Renderer name: $RENDERER_NAME"
echo "Binary: $(which gmrender-resurrect)"
echo ""
echo "To run manually:"
echo "  gmrender-resurrect -f \"$RENDERER_NAME\" -g 1"
echo ""
echo "Systemd service will be installed separately."
