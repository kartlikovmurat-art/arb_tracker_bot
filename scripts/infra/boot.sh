#!/bin/bash
# boot.sh — автозапуск arb_tracker_bot.
# Запускается при @reboot через cron, или вручную.
# Сам себя восстанавливает (если упал, перезапустится).

CONF=/workspace/supervisor/supervisord.conf
WD=/workspace/scripts/outer-watchdog.sh
LOG=/workspace/logs/boot.log

mkdir -p /workspace/logs

while true; do
    # Запускаем outer-watchdog если не запущен.
    if ! pgrep -f "outer-watchdog.sh" > /dev/null; then
        echo "[$(date)] boot.sh: starting outer-watchdog" >> "$LOG"
        nohup "$WD" >> "$LOG" 2>&1 &
        disown
        sleep 5
    fi
    sleep 30
done
