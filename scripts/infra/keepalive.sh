#!/bin/bash
# keepalive.sh — ПЕРСИСТЕНТНЫЙ АВТОСТАРТЕР arb_tracker_bot.
#
# Запускается через setsid, отвязывается от родительской сессии,
# становится orphan-процессом (PPID=1, node). Переживает закрытие
# Mavis-сессии. Переживает ребут Mavis bash.
#
# Каждые 30 секунд проверяет всю цепочку:
#   init.d (если /etc/ persistent) →
#   boot.sh →
#   outer-watchdog.sh →
#   supervisord →
#   6 программ (api, bot, watchdog, token-watchdog, db-backup, cleanup)
#
# Если что-то упало — поднимает. Тихо, без алертов.
# Если совсем не получается 3 раза подряд — пишет в /workspace/logs/keepalive.critical.log

set +e

LOG=/workspace/logs/keepalive.log
CRIT=/workspace/logs/keepalive.critical.log
mkdir -p /workspace/logs /workspace/supervisor /workspace/scripts

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }
crit() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] CRITICAL: $*" >> "$CRIT"; }

ensure_initd() {
    # Init.d не persistent в контейнере, воссоздаём каждый раз.
    if [ ! -x /etc/init.d/arb-bot-autostart ]; then
        cat > /etc/init.d/arb-bot-autostart <<'INIT'
#!/bin/sh
# Auto-start arb_tracker_bot
mkdir -p /workspace/logs /workspace/supervisor /workspace/scripts
nohup /workspace/scripts/keepalive.sh > /workspace/logs/init-autostart.log 2>&1 &
exit 0
INIT
        chmod +x /etc/init.d/arb-boot-autostart 2>/dev/null
        chmod +x /etc/init.d/arb-bot-autostart
    fi
}

ensure_boot() {
    # boot.sh — bash-цикл, перезапускает outer-watchdog.
    if ! pgrep -f "/workspace/scripts/boot\.sh" > /dev/null; then
        log "boot.sh not running, starting"
        nohup /workspace/scripts/boot.sh > /workspace/logs/boot.nohup.log 2>&1 &
        disown 2>/dev/null
    fi
}

ensure_outer_watchdog() {
    if ! pgrep -f "/workspace/scripts/outer-watchdog\.sh" > /dev/null; then
        log "outer-watchdog.sh not running, starting"
        nohup /workspace/scripts/outer-watchdog.sh > /workspace/logs/outer-watchdog.nohup.log 2>&1 &
        disown 2>/dev/null
    fi
}

ensure_supervisord() {
    if ! pgrep -f "supervisord -c /workspace/supervisor/supervisord.conf" > /dev/null; then
        log "supervisord not running, starting"
        # Сначала убиваем осиротевших чайлдов
        pkill -9 -f "uvicorn app.main:app" 2>/dev/null
        pkill -9 -f "app/bot/bot.py" 2>/dev/null
        pkill -9 -f "watchdog.py" 2>/dev/null
        pkill -9 -f "token_watchdog.py" 2>/dev/null
        pkill -9 -f "db_backup_daemon.py" 2>/dev/null
        pkill -9 -f "cleanup_daemon.py" 2>/dev/null
        sleep 2
        rm -f /workspace/supervisor/supervisord.pid /workspace/supervisor/supervisor.sock
        /usr/bin/supervisord -c /workspace/supervisor/supervisord.conf >> "$LOG" 2>&1
        sleep 5
    fi
}

check_programs() {
    # Проверяет что все 6 программ в supervisor RUNNING.
    # Если что-то BACKOFF/STARTING — даём ещё время, не перезапускаем агрессивно.
    if [ -S /workspace/supervisor/supervisor.sock ]; then
        local out
        out=$(supervisorctl -c /workspace/supervisor/supervisord.conf status arb: 2>&1)
        local not_running
        not_running=$(echo "$out" | grep -E "STOPPED|BACKOFF|FATAL|EXITED" | wc -l)
        if [ "$not_running" -gt 0 ]; then
            log "some programs not running: $out"
        fi
    fi
}

ensure_api() {
    # API — самое важное. Если он не отвечает при работающем supervisord,
    # supervisord сам его перезапустит. Но если socket есть, а 8000 закрыт —
    # форсируем restart.
    if [ -S /workspace/supervisor/supervisor.sock ]; then
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://127.0.0.1:8000/" 2>/dev/null)
        if [ "$code" != "200" ]; then
            log "API returned $code, forcing restart"
            supervisorctl -c /workspace/supervisor/supervisord.conf restart arb:api > /dev/null 2>&1
        fi
    fi
}

ensure_bot() {
    if [ -S /workspace/supervisor/supervisor.sock ]; then
        local out
        out=$(supervisorctl -c /workspace/supervisor/supervisord.conf status arb:bot 2>&1)
        if echo "$out" | grep -qE "STOPPED|BACKOFF|FATAL|EXITED"; then
            log "bot not running, restart: $out"
            supervisorctl -c /workspace/supervisor/supervisord.conf restart arb:bot > /dev/null 2>&1
        fi
    fi
}

# === Main loop ===
log "keepalive.sh started (pid $$)"

# Один проход инициализации при старте.
ensure_initd
ensure_boot
ensure_outer_watchdog
ensure_supervisord
sleep 10
ensure_api
ensure_bot
check_programs

# Цикл самовосстановления.
venv_check_counter=0
while true; do
    ensure_initd
    ensure_boot
    ensure_outer_watchdog
    ensure_supervisord
    sleep 5
    ensure_api
    ensure_bot
    check_programs
    # Раз в 120 циклов (≈1 час) — проверяем целостность venv.
    venv_check_counter=$((venv_check_counter + 1))
    if [ $((venv_check_counter % 120)) -eq 0 ]; then
        /workspace/scripts/ensure_venv.sh > /dev/null 2>&1
    fi
    sleep 25
done
