#!/workspace/.venv/bin/python
"""
Watchdog для arb_tracker_bot — МОЛЧАЛИВЫЙ режим.

Каждые 5 минут:
1. Пингует локальный API на :8000.
2. Проверяет, что Telegram Bot API доступен.
3. Проверяет, что все процессы в supervisor RUNNING.
4. Если что-то не так — перезапускает через supervisorctl.
5. Алерты в Telegram ТОЛЬКО в крайнем случае (после 3+ неудачных попыток
   восстановления подряд).

Запускается под supervisord — автоперезапуск при любом падении.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] watchdog: %(message)s",
)
log = logging.getLogger("watchdog")


# ── Конфигурация ────────────────────────────────────────────────────
API_LOCAL = "http://127.0.0.1:8000/"
SUPERVISOR_CONF = "/workspace/supervisor/supervisord.conf"
CHECK_INTERVAL = 300  # 5 минут
MAX_FAILS_BEFORE_ALERT = 3  # 3 рестарта подряд — последний шанс, потом алерт
ALERT_COOLDOWN = 24 * 3600  # один алерт в сутки на ту же проблему
BOT_TOKEN = os.environ.get(
    "WATCHDOG_BOT_TOKEN",
    "8889026369:AAH5g4izws1Q-r2uEzbVumQ9WnrbKzq-Rl8",
)
ADMIN_CHAT_ID = 6492055524

_failure_counts: dict[str, int] = {}
_last_alert: dict[str, float] = {}


def send_alert(text: str) -> None:
    """Шлёт сообщение админу. Используется только в крайнем случае."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = (
            f'{{"chat_id":{ADMIN_CHAT_ID},'
            f'"text":{repr(text)},'
            f'"parse_mode":"HTML",'
            f'"disable_web_page_preview":true}}'
        ).encode()
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10).read()
        log.info("alert sent: %s", text[:80])
    except Exception as exc:  # noqa: BLE001
        log.error("alert failed (network?): %s", exc)


def should_alert(key: str) -> bool:
    now = time.time()
    last = _last_alert.get(key, 0)
    if now - last < ALERT_COOLDOWN:
        return False
    _last_alert[key] = now
    return True


def check(name: str, url: str, timeout: int = 10) -> bool:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        log.warning("%s check failed: %s", name, exc)
        return False


def supervisor_restart(program: str) -> bool:
    try:
        result = subprocess.run(
            ["supervisorctl", "-c", SUPERVISOR_CONF, "restart", f"arb:{program}"],
            capture_output=True, text=True, timeout=30,
        )
        log.info("supervisor restart %s: %s", program, result.stdout.strip())
        return result.returncode == 0
    except Exception as exc:  # noqa: BLE001
        log.error("supervisor restart %s failed: %s", program, exc)
        return False


def supervisor_status() -> dict[str, str]:
    try:
        result = subprocess.run(
            ["supervisorctl", "-c", SUPERVISOR_CONF, "status", "arb:"],
            capture_output=True, text=True, timeout=10,
        )
        statuses: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if ":" in line:
                _, rest = line.split(":", 1)
                parts = rest.split()
                if parts:
                    name = parts[0]
                    state = parts[1] if len(parts) > 1 else "UNKNOWN"
                    statuses[name] = state
        return statuses
    except Exception as exc:  # noqa: BLE001
        log.error("supervisor status failed: %s", exc)
        return {}


def handle_failure(key: str, program: str, alert_msg: str) -> None:
    """Один рестарт, считаем попытки. Алерт только после N подряд."""
    _failure_counts[key] = _failure_counts.get(key, 0) + 1
    log.warning("%s: failure %d, restarting", key, _failure_counts[key])
    supervisor_restart(program)
    if _failure_counts[key] >= MAX_FAILS_BEFORE_ALERT and should_alert(key):
        send_alert(alert_msg)


def main() -> int:
    log.info("watchdog started (silent mode), interval=%ds", CHECK_INTERVAL)
    while True:
        try:
            statuses = supervisor_status()
            log.info("supervisor status: %s", statuses)

            # ── API ──────────────────────────────────────────────
            api_ok = check("api-local", API_LOCAL)
            if not api_ok and statuses.get("api") != "RUNNING":
                handle_failure(
                    "api_down",
                    "api",
                    f"🚨 <b>API не восстановился после {MAX_FAILS_BEFORE_ALERT} рестартов</b>\n"
                    "Нужна ручная проверка. Лог: /workspace/logs/api.err.log",
                )
            elif not api_ok:
                handle_failure(
                    "api_hung",
                    "api",
                    f"🚨 <b>API зависает, {MAX_FAILS_BEFORE_ALERT} рестартов не помогли</b>",
                )
            else:
                _failure_counts.pop("api_down", None)
                _failure_counts.pop("api_hung", None)

            # ── Bot ──────────────────────────────────────────────
            bot_ok = check(
                "telegram",
                f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
                timeout=15,
            )
            if statuses.get("bot") != "RUNNING":
                handle_failure(
                    "bot_down",
                    "bot",
                    f"🚨 <b>Бот не восстановился после {MAX_FAILS_BEFORE_ALERT} рестартов</b>",
                )
            elif not bot_ok:
                # Бот RUNNING но Telegram API не отвечает — скорее всего сеть
                _failure_counts["bot_down"] = _failure_counts.get("bot_down", 0) + 1
                if _failure_counts["bot_down"] >= MAX_FAILS_BEFORE_ALERT and should_alert("bot_no_tg"):
                    send_alert("🚨 <b>Telegram API недоступен 3+ циклов подряд</b>")
            else:
                _failure_counts.pop("bot_down", None)

        except Exception as exc:  # noqa: BLE001
            log.exception("watchdog loop error: %s", exc)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
