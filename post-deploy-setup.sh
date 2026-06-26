#!/bin/bash
# post-deploy-setup.sh — Run on RPi after first boot to configure services
# Execute: bash post-deploy-setup.sh
set -euo pipefail

echo "=== 1. Changing SSH port to 2222 ==="
if grep -q "^#Port 22" /etc/ssh/sshd_config; then
    sudo sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config
elif ! grep -q "^Port 2222" /etc/ssh/sshd_config; then
    echo "Port 2222" | sudo tee -a /etc/ssh/sshd_config
fi
sudo systemctl restart sshd
echo "SSH now on port 2222"

echo ""
echo "=== 2. Installing Tailscale ==="
if ! command -v tailscale &>/dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
    sudo tailscale up
else
    echo "Tailscale already installed"
fi

echo ""
echo "=== 3. Installing Node.js v24 ==="
if ! command -v node &>/dev/null || [[ "$(node -v)" != v24* ]]; then
    curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    echo "Node.js v24 already installed"
fi

echo ""
echo "=== 4. Deploying legacy webserver on port 8099 ==="
cp /home/milhy777/rpi-dashboard/webserver.py /home/milhy777/webserver.py

cat > /tmp/webserver-8099.service << 'EOF'
[Unit]
Description=RPi Legacy Webserver (Port 8099)
After=network.target

[Service]
Type=simple
User=milhy777
WorkingDirectory=/home/milhy777
ExecStart=/home/milhy777/rpi-dashboard/.venv/bin/python /home/milhy777/webserver.py
Restart=on-failure
RestartSec=5
Environment=PATH=/home/milhy777/.local/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/webserver-8099.service /etc/systemd/system/webserver-8099.service
sudo systemctl daemon-reload
sudo systemctl enable webserver-8099.service
sudo systemctl start webserver-8099.service

echo ""
echo "=== DONE ==="
echo "Webserver: http://$(hostname -I | awk '{print $1}'):8099/status"
echo "Dashboard service: sudo systemctl status dashboard@milhy777"
echo "SSH port: 2222"
