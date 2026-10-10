#!/usr/bin/env bash
# install-moonlight.sh — One-click Moonlight client installer for Raspberry Pi 3B
# Configures required groups for hardware decoding and input takeover.

set -euo pipefail

echo "========================================================="
echo "   Moonlight Client Installer for Raspberry Pi 3B"
echo "========================================================="

# 1. Install Moonlight-QT via apt
echo "[*] Installing Moonlight-QT package..."
sudo apt-get update
sudo apt-get install -y moonlight-qt

# 2. Add user to required groups for direct input/hardware access
CURRENT_USER=$(whoami)
echo "[*] Adding user '$CURRENT_USER' to required groups (input, video, render, tty)..."
for grp in input video render tty; do
    if getent group "$grp" >/dev/null; then
        sudo usermod -aG "$grp" "$CURRENT_USER"
        echo "  -> Added to group: $grp"
    fi
done

# 3. Enable kernel configuration check for Raspberry Pi video driver
echo "[*] Verifying hardware decoding permissions..."
if [ -c /dev/vchiq ]; then
    sudo chmod a+rw /dev/vchiq || true
    echo "  -> Granted permissions to /dev/vchiq"
fi

echo ""
echo "========================================================="
echo "   INSTALLATION COMPLETE!"
echo "========================================================="
echo "1. Moonlight-QT is installed and ready."
echo "2. Group permissions configured. Please REBOOT or log out"
echo "   and back in to apply group changes."
echo "3. Run 'moonlight-qt' from the command line or use the"
echo "   TUI dashboard button to initiate scanning and pairing."
echo "========================================================="
