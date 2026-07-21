#!/bin/bash
# Внешний «супервизор над супервизором».
# Если supervisord упал — поднимает его заново.
# Запускается через nohup отдельным процессом.
#
# При перезапуске supervisord чистит осиротевших чайлдов
# (uvicorn, bot.py), которые supervisord не успел убить при exit.

set -e

CONF=/workspace/supervisor/supervisord.conf
LOG=/workspace/logs/outer-watchdog.log
PIDFILE=/workspace/supervisor/supervisord.pid
SOCK=/workspace/supervisor/supervisor.sock
mkdir -p /workspace/logs

cleanup_orphans() {
    # Убиваем всё, что могло пережить supervisord.
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -9 -f "app/bot/bot.py"       2>/dev/null || true
    pkill -9 -f "watchdog.py"          2>/dev/null || true
    pkill -9 -f "token_watchdog.py"    2>/dev/null || true
    sleep 1
    # Удаляем stale pid и socket, иначе supervisord не стартанёт.
    rm -f "$PIDFILE" "$SOCK"
}

start_supervisor() {
    echo "[$(date)] supervisord not running, starting..." >> "$LOG"
    cleanup_orphans
    /usr/bin/supervisord -c "$CONF" >> "$LOG" 2>&1 || true
    sleep 5
}

while true; do
    if ! pgrep -f "supervisord -c $CONF" > /dev/null; then
        start_supervisor
    fi
    sleep 30
done
