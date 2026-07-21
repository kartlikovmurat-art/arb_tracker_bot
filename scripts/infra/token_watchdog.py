#!/workspace/.venv/bin/python
"""
Token-watchdog — МОЛЧАЛИВЫЙ режим.

Раз в 30 минут проверяет что Telegram-токен валиден.
Алертит ТОЛЬКО если 3+ проверок подряд показали проблему
(чтобы не спамить при кратковременных сбоях сети).

Запускается под supervisord (autorestart=true).
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] token-watchdog: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("token-watchdog")

BOT_TOKEN = os.environ.get(
    "WATCHDOG_BOT_TOKEN",
    "8889026369:AAH5g4izws1Q-r2uEzbVumQ9WnrbKzq-Rl8",
)
ADMIN_CHAT_ID = 6492055524
CHECK_INTERVAL = 1800  # 30 минут
ALERT_COOLDOWN = 24 * 3600  # один алерт в сутки
MAX_FAILS_BEFORE_ALERT = 3  # 3 цикла подряд = алерт
TIMEOUT = 15

_consecutive_failures = 0
_last_alert: dict[str, float] = {}


def send_alert(text: str) -> None:
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=json.dumps({
                "chat_id": ADMIN_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as exc:  # noqa: BLE001
        log.warning("alert failed: %s", exc)


def should_alert(key: str) -> bool:
    now = time.time()
    last = _last_alert.get(key, 0)
    if now - last < ALERT_COOLDOWN:
        return False
    _last_alert[key] = now
    return True


def check_token() -> bool:
    global _consecutive_failures
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getMe",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.loads(r.read())
        if not body.get("ok"):
            log.warning("getMe not ok: %s", body)
            _consecutive_failures += 1
            if _consecutive_failures >= MAX_FAILS_BEFORE_ALERT and should_alert("token_invalid"):
                send_alert(
                    f"🚨 <b>Telegram token INVALID</b>\n"
                    f"<code>{body.get('description', '?')}</code>\n"
                    "3+ проверок подряд. Нужен новый токен через @BotFather."
                )
            return False
        username = body.get("result", {}).get("username", "?")
        log.info("token OK, bot=@%s", username)
        _consecutive_failures = 0
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        log.warning("getMe network error: %s", exc)
        _consecutive_failures += 1
        if _consecutive_failures >= MAX_FAILS_BEFORE_ALERT and should_alert("telegram_unreachable"):
            send_alert(
                f"🚨 <b>Telegram API недоступен 3+ циклов</b>\n"
                f"<code>{exc}</code>"
            )
        return False


def main() -> int:
    log.info("token-watchdog started (silent mode), interval=%ds", CHECK_INTERVAL)
    while True:
        try:
            check_token()
        except Exception as exc:  # noqa: BLE001
            log.exception("loop error: %s", exc)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
