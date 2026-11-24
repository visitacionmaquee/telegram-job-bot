#!/bin/bash
# ==============================================================================
# JobRadar AI — Oracle Cloud Infrastructure (OCI) VM Bootstrap Script
# Supports: Ubuntu 22.04 / 24.04 LTS & Oracle Linux 8 / 9
# ==============================================================================

set -e

echo "🚀 [1/5] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release iptables-persistent ufw

echo "🔒 [2/5] Configuring OCI Firewall & iptables rules..."
# Critical for OCI: Oracle Cloud default images include restrictive OS-level iptables
# that drop incoming HTTP/HTTPS traffic before it reaches Docker.
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT || sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save || sudo service netfilter-persistent save || true

# Configure UFW
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "🐳 [3/5] Installing Docker Engine & Docker Compose Plugin..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm -f get-docker.sh
    sudo usermod -aG docker "$USER"
fi

sudo apt-get install -y docker-compose-plugin

echo "⚙️ [4/5] Setting up systemd auto-start service..."
WORK_DIR=$(pwd)
SERVICE_FILE="/etc/systemd/system/jobradar.service"

sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=JobRadar AI Production Stack (Docker Compose)
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$WORK_DIR
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable jobradar.service

echo "✅ [5/5] Setup complete! You are ready to configure .env and launch JobRadar AI."
echo "👉 Run: 'docker compose -f docker-compose.prod.yml up -d --build'"
