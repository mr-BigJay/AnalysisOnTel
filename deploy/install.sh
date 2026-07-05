#!/bin/bash
# AnalysisOnTel v2 — Web dashboard install (Ubuntu 24.04)
set -euo pipefail

APP_DIR="/opt/analysisontel"
APP_USER="analysisontel"
REPO_URL="${REPO_URL:-https://github.com/mr-BigJay/AnalysisOnTel.git}"
BRANCH="${BRANCH:-cursor/web-dashboard-8654}"

echo "==> Installing packages..."
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip

echo "==> Creating user ${APP_USER}..."
id -u "${APP_USER}" &>/dev/null || useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"

echo "==> Cloning/updating repository..."
if [ -d "${APP_DIR}/.git" ]; then
  cd "${APP_DIR}"
  git fetch origin
  git checkout "${BRANCH}"
  git pull origin "${BRANCH}"
else
  git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${APP_DIR}"
  cd "${APP_DIR}"
fi

echo "==> Python venv..."
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt" -q

mkdir -p "${APP_DIR}/data"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

if [ ! -f /etc/analysisontel.env ]; then
  cp "${APP_DIR}/deploy/analysisontel.env.example" /etc/analysisontel.env
  chmod 600 /etc/analysisontel.env
  echo "!!! Set WEB_PASSWORD in /etc/analysisontel.env"
fi

cp "${APP_DIR}/deploy/analysisontel.service" /etc/systemd/system/analysisontel.service
systemctl daemon-reload

echo ""
echo "============================================"
echo "  Install complete!"
echo "  1. sudo nano /etc/analysisontel.env"
echo "  2. sudo systemctl enable --now analysisontel"
echo "  3. Open http://YOUR_SERVER:9443"
echo "  4. sudo journalctl -u analysisontel -f"
echo "============================================"
