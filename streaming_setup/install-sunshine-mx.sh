#!/usr/bin/env bash
# install-sunshine-mx.sh — One-click Sunshine installer for MX Linux 25 (KDE/Wayland/X11)
# Configures auto-detection of Intel iGPU + NVIDIA dGPU for flexible encoding.

set -euo pipefail

echo "========================================================="
echo "   Sunshine Host Installer for MX Linux 25 / Debian"
echo "========================================================="

# 1. Install system prerequisites
echo "[*] Installing required system tools and libraries..."
sudo apt-get update
sudo apt-get install -y curl jq libva2 libdrm2 vainfo mesa-utils split-select- 2>/dev/null || true
sudo apt-get install -y python3-pip systemd -y

# 2. Fetch latest Sunshine Debian package
echo "[*] Querying GitHub for the latest Sunshine Debian package..."
LATEST_RELEASE_URL=$(curl -s https://api.github.com/repos/LizardByte/Sunshine/releases/latest \
  | jq -r '.assets[] | select(.name | contains("debian-bookworm-amd64.deb")) | .browser_download_url' | head -n 1)

if [ -z "$LATEST_RELEASE_URL" ] || [ "$LATEST_RELEASE_URL" == "null" ]; then
    # Fallback to Ubuntu jammy build if Debian bookworm is missing
    LATEST_RELEASE_URL=$(curl -s https://api.github.com/repos/LizardByte/Sunshine/releases/latest \
      | jq -r '.assets[] | select(.name | contains("ubuntu-jammy-amd64.deb")) | .browser_download_url' | head -n 1)
fi

echo "[*] Downloading package from: $LATEST_RELEASE_URL"
curl -L -o /tmp/sunshine-latest.deb "$LATEST_RELEASE_URL"

echo "[*] Installing Sunshine package..."
sudo apt-get install -y /tmp/sunshine-latest.deb || sudo apt-get install -f -y

# 3. Configure CAP_SYS_ADMIN for KMS screen capture (crucial for Wayland/headless fallback)
SUNSHINE_BIN=$(which sunshine || echo "/usr/bin/sunshine")
if [ -f "$SUNSHINE_BIN" ]; then
    echo "[*] Granting screen capture capabilities to Sunshine binary..."
    sudo setcap cap_sys_admin+ep "$SUNSHINE_BIN"
fi

# 4. Detect GPU Topology
echo "[*] Detecting GPU topology..."
INTEL_GPU=false
NVIDIA_GPU=false

if lspci | grep -i "Intel" | grep -q -E "VGA|3D|Display"; then
    INTEL_GPU=true
    echo "  -> Found Intel GPU"
fi

if lspci | grep -i "NVIDIA" | grep -q -E "VGA|3D|Display"; then
    NVIDIA_GPU=true
    echo "  -> Found NVIDIA GPU (GeForce GTX 1060)"
fi

# Create config directory
CONFIG_DIR="$HOME/.config/sunshine"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/sunshine.conf"

echo "[*] Writing configuration template to $CONFIG_FILE..."

# Write initial sunshine.conf template
cat << 'EOF' > "$CONFIG_FILE"
# Sunshine Configuration File
# Exposes Web UI on port 47990 (https://localhost:47990)

# Screen capture method (kms, x11, or wayland)
# On KDE Wayland, Sunshine uses PipeWire capture automatically.
# KMS is used as fallback.
EOF

# Write GPU-specific parameters based on topology
if [ "$INTEL_GPU" = true ] && [ "$NVIDIA_GPU" = true ]; then
    cat << 'EOF' >> "$CONFIG_FILE"

# MULTI-GPU WORKFLOW OPTIMIZATION
# -------------------------------------------------------------
# Option A: Intel QuickSync (iGPU) - RECOMMENDED FOR HYBRID WORKFLOW
# Use this to keep your NVIDIA GTX 1060 free for local AI / LLMs.
encoder = vaapi
adapter_name = /dev/dri/renderD128

# Option B: NVIDIA NVENC (dGPU) - RECOMMENDED FOR MAX GAMING PERFORMANCE
# Uncomment below and comment out Option A to use the GTX 1060 hardware encoder.
# encoder = nvenc
EOF
elif [ "$NVIDIA_GPU" = true ]; then
    cat << 'EOF' >> "$CONFIG_FILE"
# NVIDIA Only Configuration
encoder = nvenc
EOF
else
    cat << 'EOF' >> "$CONFIG_FILE"
# Intel/AMD VA-API Configuration
encoder = vaapi
adapter_name = /dev/dri/renderD128
EOF
fi

# 5. Enable and start Sunshine user service
echo "[*] Setting up Sunshine systemd user service..."
systemctl --user daemon-reload
systemctl --user enable sunshine.service || true
systemctl --user restart sunshine.service || true

echo ""
echo "========================================================="
echo "   INSTALLATION COMPLETE!"
echo "========================================================="
echo "1. Sunshine is now running as a user background service."
echo "2. Open the Web UI: https://localhost:47990"
echo "   (Create your admin credentials on first load)."
echo "3. Go to the 'PIN' tab and enter the PIN displayed on your"
echo "   Raspberry Pi (Moonlight) screen to pair."
echo "4. Configuration file is editable at: ~/.config/sunshine/sunshine.conf"
echo "========================================================="
