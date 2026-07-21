#!/workspace/.venv/bin/python
"""
cleanup_daemon — supervisor-managed фоновый процесс.
Раз в неделю чистит старые логи и бэкапы.

Заменяет Mavis cron. Не шлёт алертов, только логи.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] cleanup-daemon: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("cleanup-daemon")

LOG_DIR = Path("/workspace/logs")
BACKUP_DIR = Path("/workspace/backups")
LOG_TOTAL_MAX = 50 * 1024 * 1024  # 50 MB
MAX_BACKUPS = 30
WEEKLY = True  # запускаем раз в неделю


def cleanup_once() -> None:
    # Логи
    if LOG_DIR.exists():
        total = sum(p.stat().st_size for p in LOG_DIR.rglob("*") if p.is_file())
        log.info("log dir size: %d bytes (max %d)", total, LOG_TOTAL_MAX)
        if total > LOG_TOTAL_MAX:
            # Удаляем самые старые .log.* (ротированные)
            rotated = sorted(
                [p for p in LOG_DIR.rglob("*") if p.is_file() and (p.suffix == ".log" or ".log." in p.name)],
                key=lambda p: p.stat().st_mtime,
            )
            while total > LOG_TOTAL_MAX and rotated:
                victim = rotated.pop(0)
                try:
                    size = victim.stat().st_size
                    victim.unlink()
                    total -= size
                    log.info("removed old log: %s (%d bytes)", victim, size)
                except OSError:
                    log.exception("failed to remove: %s", victim)
    # Бэкапы
    if BACKUP_DIR.exists():
        backups = sorted(BACKUP_DIR.glob("db_*.sqlite3"))
        for old in backups[: max(0, len(backups) - MAX_BACKUPS)]:
            try:
                old.unlink()
                log.info("removed old backup: %s", old)
            except OSError:
                log.exception("failed to remove: %s", old)
        log.info("kept %d newest backups", min(len(backups), MAX_BACKUPS))


def main() -> int:
    log.info("cleanup-daemon started, weekly")
    while True:
        now = datetime.now()
        # Рандомный сдвиг (на случай если несколько контейнеров)
        # Первый запуск через 5 минут после старта.
        time.sleep(5 * 60)
        log.info("running cleanup")
        try:
            cleanup_once()
        except Exception:  # noqa: BLE001
            log.exception("cleanup error")
        # Следующий запуск через 7 дней.
        log.info("next cleanup in 7 days")
        time.sleep(7 * 24 * 60 * 60)


if __name__ == "__main__":
    main()
