#!/bin/bash
# AnalysisOnTel — Ubuntu 24.04 install script
# Run as root: sudo bash deploy/install.sh

set -euo pipefail

APP_DIR="/opt/analysisontel"
APP_USER="analysisontel"
REPO_URL="${REPO_URL:-https://github.com/mr-BigJay/AnalysisOnTel.git}"
BRANCH="${BRANCH:-cursor/btc-notif-bot-8654}"

echo "==> Installing system packages..."
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip

echo "==> Creating user ${APP_USER}..."
id -u "${APP_USER}" &>/dev/null || useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"

echo "==> Cloning repository..."
if [ -d "${APP_DIR}/.git" ]; then
  cd "${APP_DIR}"
  git fetch origin
  git checkout "${BRANCH}"
  git pull origin "${BRANCH}"
else
  git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${APP_DIR}"
  cd "${APP_DIR}"
fi

echo "==> Setting up Python virtual environment..."
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt" -q

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
mkdir -p "${APP_DIR}/data"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}/data"

echo "==> Environment file..."
if [ ! -f /etc/analysisontel.env ]; then
  cp "${APP_DIR}/deploy/analysisontel.env.example" /etc/analysisontel.env
  chmod 600 /etc/analysisontel.env
  chown root:root /etc/analysisontel.env
  echo ""
  echo "!!! Edit /etc/analysisontel.env and set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS"
  echo "    nano /etc/analysisontel.env"
  echo ""
fi

echo "==> Installing systemd service..."
cp "${APP_DIR}/deploy/analysisontel.service" /etc/systemd/system/analysisontel.service
systemctl daemon-reload

echo ""
echo "============================================"
echo "  Install complete!"
echo "============================================"
echo ""
echo "  1. Edit config:  sudo nano /etc/analysisontel.env"
echo "  2. Start bot:    sudo systemctl enable --now analysisontel"
echo "  3. Check logs:   sudo journalctl -u analysisontel -f"
echo ""
echo "  NOTE: This bot uses Telegram POLLING."
echo "  No inbound ports needed (80/443/etc stay free)."
echo ""
