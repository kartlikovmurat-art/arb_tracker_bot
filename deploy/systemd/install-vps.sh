#!/usr/bin/env bash
# Развёртывание Arbitrage Tracker на чистом Ubuntu 22.04/24.04.
# Запускать от root или через sudo.
#
#   curl -fsSL https://raw.githubusercontent.com/.../deploy/systemd/install-vps.sh | sudo bash
# или
#   sudo bash deploy/systemd/install-vps.sh
#
# Что делает:
#   1. Создаёт пользователя arb.
#   2. Ставит python3.11, git, sqlite3.
#   3. Клонирует репозиторий в /opt/arb-tracker.
#   4. Создаёт venv и ставит зависимости.
#   5. Копирует .env.example → .env (вам нужно дописать BOT_TOKEN).
#   6. Регистрирует systemd-сервисы и запускает их.
#   7. Создаёт /var/log/arb-tracker и ротацию логов.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/kartlikovmurat-art/arb_tracker_bot.git}"
APP_USER="arb"
APP_DIR="/opt/arb-tracker"

echo "▶ Создаю пользователя $APP_USER..."
id "$APP_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$APP_USER"

echo "▶ Ставлю системные пакеты..."
apt-get update
apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip \
    git sqlite3 ca-certificates curl logrotate

echo "▶ Клонирую репозиторий в $APP_DIR..."
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" && git pull --ff-only
else
    git clone "$REPO_URL" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

cd "$APP_DIR"
sudo -u "$APP_USER" python3.11 -m venv .venv
sudo -u "$APP_USER" .venv/bin/pip install --upgrade pip
sudo -u "$APP_USER" .venv/bin/pip install -r requirements.txt openpyxl

if [ ! -f .env ]; then
    sudo -u "$APP_USER" cp .env.example .env
    echo "============================================================"
    echo "  ⚠  Не забудьте отредактировать .env и вписать BOT_TOKEN!"
    echo "     sudo -u arb nano $APP_DIR/.env"
    echo "     sudo systemctl restart arb-tracker-api arb-tracker-bot"
    echo "============================================================"
fi

mkdir -p /var/log/arb-tracker
chown "$APP_USER:$APP_USER" /var/log/arb-tracker

echo "▶ Регистрирую systemd-сервисы..."
cp deploy/systemd/arb-tracker-api.service /etc/systemd/system/
cp deploy/systemd/arb-tracker-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now arb-tracker-api arb-tracker-bot

cat > /etc/logrotate.d/arb-tracker <<'EOF'
/var/log/arb-tracker/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 arb arb
    sharedscripts
    postrotate
        systemctl kill -s HUP arb-tracker-api.service 2>/dev/null || true
        systemctl kill -s HUP arb-tracker-bot.service 2>/dev/null || true
    endscript
}
EOF

echo "▶ Готово. Проверяю статус..."
sleep 2
systemctl --no-pager status arb-tracker-api arb-tracker-bot || true
echo
echo "Логи:  sudo journalctl -u arb-tracker-bot -f"
