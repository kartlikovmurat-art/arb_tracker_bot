#!/bin/bash
# ensure_venv.sh — переустанавливает /workspace/.venv если он пропал.
# Запускается из keepalive.sh каждый час (не чаще, чтобы не тратить CPU).
#
# venv находится в /workspace/.venv (persistent), но на всякий случай
# (disk corruption, manual delete) держим скрипт восстановления.
#
# Зависимости: requirements.txt из репо.

set -e

VENV=/workspace/.venv
REPO=/workspace/arb_tracker_bot1_full
REQ=$REPO/requirements.txt

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ensure_venv: $*" >> /workspace/logs/ensure_venv.log; }

# Проверка 1: venv существует и работает.
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import uvicorn, httpx, fastapi, aiogram, sqlalchemy, aiosqlite, alembic, matplotlib, openpyxl" 2>/dev/null; then
    log "venv OK"
    exit 0
fi

log "venv broken or missing, recreating..."

# Удаляем старый если есть
rm -rf "$VENV"
mkdir -p "$VENV"

# Создаём новый
python3 -m venv "$VENV" 2>&1 | head -5

# Устанавливаем зависимости
if [ -f "$REQ" ]; then
    "$VENV/bin/pip" install --no-cache-dir -r "$REQ" 2>&1 | tail -5
fi

# Доп. пакет
"$VENV/bin/pip" install --no-cache-dir openpyxl 2>&1 | tail -3

# Проверка
if "$VENV/bin/python" -c "import uvicorn, httpx, fastapi, aiogram, sqlalchemy, aiosqlite, alembic, matplotlib, openpyxl" 2>/dev/null; then
    log "venv RECREATED OK"
    exit 0
else
    log "venv RECREATE FAILED"
    exit 1
fi
