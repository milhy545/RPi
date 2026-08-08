#!/bin/bash
set -e

echo "Removing Tibo pairing..."
bluetoothctl remove FC:58:FA:29:BA:47 || true

echo "Configuring hci0 for Tibo..."
bluetoothctl select B8:27:EB:E1:1E:89
bluetoothctl power on
bluetoothctl agent on
# Try to pair, trust, and connect.
bluetoothctl pair FC:58:FA:29:BA:47 || true
bluetoothctl trust FC:58:FA:29:BA:47 || true
bluetoothctl connect FC:58:FA:29:BA:47 || true

echo "Configuring WirePlumber for Tibo codec (SBC/SBC-XQ)..."
mkdir -p ~/.config/wireplumber/bluetooth.lua.d
cat << 'EOF' > ~/.config/wireplumber/bluetooth.lua.d/52-tibo-codec.lua
bluez_monitor.rules = {
  {
    matches = {
      {
        { "device.name", "equals", "bluez_card.FC_58_FA_29_BA_47" },
      },
    },
    apply_properties = {
      ["bluez5.codecs"] = "[ sbc sbc_xq ]",
    },
  },
}
EOF

echo "Disabling SAP plugin in Bluetooth main.conf..."
# Ensure the line is in [General] section
# We use sudo for this operation, applying askpass rule
if ! grep -q "DisablePlugins = sap" /etc/bluetooth/main.conf; then
    SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A sed -i '/^\[General\]/a DisablePlugins = sap' /etc/bluetooth/main.conf
fi

echo "Restarting services..."
SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A systemctl restart bluetooth
systemctl --user restart wireplumber || true

echo "Fixes deployed."
