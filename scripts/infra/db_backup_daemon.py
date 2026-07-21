#!/workspace/.venv/bin/python
"""
db_backup_daemon — supervisor-managed фоновый процесс.
Раз в сутки делает backup БД, ротирует старые.

Заменяет Mavis cron полностью. Не шлёт алертов в Telegram
(только логи). Работает под supervisord с autorestart=true.

Зачем: бот не зависит от Mavis, не тратит кредиты на сессии.
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] db-backup-daemon: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("db-backup-daemon")

DB_PATH = Path(os.environ.get("ARBOT_DB_PATH", "/workspace/arb_tracker_bot1_full/db.sqlite3"))
BACKUP_DIR = Path("/workspace/backups")
MAX_BACKUPS = 30
BACKUP_HOUR = 3  # ежедневно в 03:00 (по локальному времени контейнера)
MAX_FAILS_BEFORE_ALERT = 7  # неделя без единого успешного backup — пора шлёпать


def _next_run_seconds(now: datetime) -> float:
    """Сколько секунд до следующего 03:00."""
    target = now.replace(hour=BACKUP_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target.replace(day=target.day + 1)
    return (target - now).total_seconds()


def backup_once() -> bool:
    if not DB_PATH.exists():
        log.error("DB not found: %s", DB_PATH)
        return False
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"db_{ts}.sqlite3"
    try:
        shutil.copy2(DB_PATH, dest)
        size = dest.stat().st_size
        log.info("backup OK: %s (%d bytes)", dest, size)
    except Exception:  # noqa: BLE001
        log.exception("backup FAILED")
        return False
    # Ротация
    backups = sorted(BACKUP_DIR.glob("db_*.sqlite3"))
    for old in backups[: max(0, len(backups) - MAX_BACKUPS)]:
        try:
            old.unlink()
            log.info("old backup removed: %s", old)
        except OSError:
            log.exception("failed to remove old backup: %s", old)
    log.info("kept %d newest backups", min(len(backups), MAX_BACKUPS))
    return True


def main() -> int:
    log.info("db-backup-daemon started, daily at %02d:00 UTC", BACKUP_HOUR)
    consecutive_failures = 0
    while True:
        now = datetime.now()
        sleep_s = _next_run_seconds(now)
        log.info("next backup in %.0f s (at %s)", sleep_s, now.fromtimestamp(now.timestamp() + sleep_s))
        time.sleep(sleep_s)
        ok = backup_once()
        if ok:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            log.warning("consecutive failures: %d", consecutive_failures)
            if consecutive_failures >= MAX_FAILS_BEFORE_ALERT:
                # Если неделя без backup — пишем в лог, супервизор заметит.
                # В Telegram НЕ шлём, чтобы не спамить.
                log.error("TOO MANY FAILURES — manual intervention needed")
                # Сбрасываем счётчик, чтобы не зацикливаться в ERROR.
                consecutive_failures = MAX_FAILS_BEFORE_ALERT - 1


if __name__ == "__main__":
    main()
