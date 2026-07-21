#!/usr/bin/env bash
# Опционально: поднять SSH-туннель, если ваш провайдер блокирует
# api.telegram.org (часто бывает в РФ, BY, KZ).
#
# Это запускается на той же VPS, где крутится бот, и проксирует
# весь трафик к Telegram через зарубежный сервер. Скачивать
# дополнительный софт не нужно — SSH умеет SOCKS5 из коробки.
#
# Использование:
#   1. Скопируйте deploy/scripts/setup-tunnel.sh на сервер.
#   2. Замените JUMP_HOST на IP/порт вашего зарубежного сервера
#      (или купите любой VPS за 3-5$ в Германии/Нидерландах).
#   3. sudo bash setup-tunnel.sh
#   4. Допишите в /opt/arb-tracker/.env:
#        BOT_PROXY=socks5://127.0.0.1:1080
#   5. sudo systemctl restart arb-tracker-bot
#
# Бот автоматически пойдёт через SOCKS5-прокси, и Telegram снова
# будет отвечать.

set -euo pipefail

JUMP_HOST="${JUMP_HOST:-your.vps.example.com}"
JUMP_USER="${JUMP_USER:-root}"
LOCAL_PORT="${LOCAL_PORT:-1080}"
SERVICE_FILE="/etc/systemd/system/arb-tg-tunnel.service"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=SSH SOCKS5 tunnel to $JUMP_HOST (for Telegram API)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=nobody
ExecStart=/usr/bin/ssh -N -D 127.0.0.1:$LOCAL_PORT \\
    -o ServerAliveInterval=30 \\
    -o ServerAliveCountMax=3 \\
    -o StrictHostKeyChecking=accept-new \\
    -o ExitOnForwardFailure=yes \\
    -p 22 $JUMP_USER@$JUMP_HOST
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now arb-tg-tunnel

echo "Tunnel up: socks5://127.0.0.1:$LOCAL_PORT"
echo "Add to .env:  BOT_PROXY=socks5://127.0.0.1:$LOCAL_PORT"
echo "Test:         curl -x socks5h://127.0.0.1:$LOCAL_PORT https://api.telegram.org"
