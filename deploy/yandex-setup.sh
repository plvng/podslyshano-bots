#!/usr/bin/env bash
# Bootstrap script for Yandex Compute Cloud VM (Ubuntu 22.04)
set -euo pipefail

echo "==> Installing Docker..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"

echo "==> Cloning repository..."
sudo mkdir -p /opt/podslyshano-bots
sudo chown "$USER:$USER" /opt/podslyshano-bots
if [ ! -d /opt/podslyshano-bots/.git ]; then
  git clone https://github.com/plvng/podslyshano-bots.git /opt/podslyshano-bots
fi

cd /opt/podslyshano-bots
echo "==> Create .env from .env.example and fill secrets before continuing"
echo "    Required: PROPOSAL_BOT_TOKEN, CHAT_BOT_TOKEN, TGK, ADMINS, ADMIN_WEB_URL=http://$(curl -s ifconfig.me):8080"

echo "==> Install systemd unit..."
sudo cp deploy/podslyshano-bots.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable podslyshano-bots.service

echo "Done. Next steps:"
echo "  1. cp .env.example .env && nano .env"
echo "  2. docker compose up -d --build"
echo "  3. sudo systemctl start podslyshano-bots"
echo "  4. Open Security Group ports: 22, 8080"
echo "  5. Send /panel to proposal bot -> open admin web"
