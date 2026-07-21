#!/bin/bash
# arb-ctl.sh — управление arb_tracker_bot через supervisord.
# Использование:
#   ./arb-ctl.sh start    — запустить все процессы
#   ./arb-ctl.sh stop     — остановить
#   ./arb-ctl.sh restart  — перезапустить
#   ./arb-ctl.sh status   — статус
#   ./arb-ctl.sh logs     — последние 50 строк всех логов
#   ./arb-ctl.sh url      — показать текущий tunnel URL

CONF=/workspace/supervisor/supervisord.conf

cmd_status() {
    supervisorctl -c "$CONF" status arb:
}

cmd_start() {
    if pgrep -f "supervisord -c $CONF" > /dev/null; then
        echo "Supervisor already running. Issuing start..."
        supervisorctl -c "$CONF" start arb:*
    else
        echo "Starting supervisord..."
        supervisord -c "$CONF"
    fi
    sleep 3
    cmd_status
}

cmd_stop() {
    supervisorctl -c "$CONF" stop arb:*
    sleep 1
    cmd_status
}

cmd_restart() {
    supervisorctl -c "$CONF" restart arb:*
    sleep 2
    cmd_status
}

cmd_logs() {
    for f in /workspace/logs/api.out.log /workspace/logs/api.err.log \
             /workspace/logs/bot.out.log /workspace/logs/bot.err.log \
             /workspace/logs/cloudflared.out.log /workspace/logs/watchdog.out.log \
             /workspace/logs/watchdog.err.log /workspace/logs/tunnel-sync.out.log; do
        if [ -f "$f" ]; then
            echo "===== $f ====="
            tail -n 30 "$f"
            echo ""
        fi
    done
}

cmd_url() {
    if [ -f /workspace/logs/tunnel_url.txt ]; then
        cat /workspace/logs/tunnel_url.txt
    else
        echo "tunnel URL not found yet — wait a few seconds for cloudflared"
    fi
}

case "$1" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_restart ;;
    status) cmd_status ;;
    logs) cmd_logs ;;
    url) cmd_url ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|url}"
        exit 1
        ;;
esac
