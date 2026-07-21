"""Запуск Telegram-бота с автоматическим перезапуском.

Использование:
    python run_bot.py

Зачем нужен:
    Бот может упасть по самым разным причинам: пропала сеть,
    упал FastAPI, Telegram вернул 5xx, прилетело неожиданное
    исключение в хендлере. По умолчанию после этого процесс
    просто умирает и ждёт ручного перезапуска.

    Этот wrapper ловит падения и перезапускает бота с экспоненциальным
    backoff (1с → 2с → 4с → … → 60с). После успешного старта счётчик
    сбрасывается, и при следующем падении backoff начинается заново.

    Остановка: Ctrl+C один раз. Двойной Ctrl+C — принудительный выход.

Env:
    BOT_MAX_BACKOFF_SEC  — потолок backoff (по умолчанию 60).
    BOT_RESTART_DELAY    — фиксированная задержка вместо backoff (опц.).
    LOG_LEVEL            — INFO/DEBUG/WARNING/ERROR.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
import traceback
from pathlib import Path

# Поднимаем корень проекта в sys.path, чтобы import работал и при
# запуске ``python run_bot.py`` из любой директории.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logger = logging.getLogger("run_bot")


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


async def _run_once(stop_event: asyncio.Event) -> int:
    """Запускает main() из app.bot.bot. Возвращает exit code."""
    from app.bot.bot import main as bot_main
    task = asyncio.create_task(bot_main())
    stop_waiter = asyncio.create_task(stop_event.wait())
    done, _ = await asyncio.wait(
        {task, stop_waiter},
        return_when=asyncio.FIRST_COMPLETED,
    )
    if stop_waiter in done and not task.done():
        # Пришёл сигнал остановки. Говорим диспетчеру остановиться
        # (aiogram ловит SIGINT/SIGTERM сам, но инициируем принудительно).
        logger.info("Получен сигнал остановки, прерываю main()…")
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
            pass
        return 0
    # main() сам завершился — бот упал.
    if task.cancelled():
        logger.warning("main() был отменён")
        return 1
    exc = task.exception()
    if exc is not None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logger.error("Бот упал с исключением:\n%s", tb)
        return 1
    return 0


async def _supervisor() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    force_stop = {"v": False}

    def _on_signal(signame: str) -> None:
        if force_stop["v"]:
            logger.warning("Повторный %s — принудительный выход", signame)
            os._exit(1)
        logger.info("Поймал %s, останавливаю бота…", signame)
        force_stop["v"] = True
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal, sig.name)
        except NotImplementedError:  # pragma: no cover (Windows)
            # На Windows add_signal_handler не работает — полагаемся на Ctrl+C.
            pass

    max_backoff = float(os.getenv("BOT_MAX_BACKOFF_SEC", "60"))
    fixed_delay = os.getenv("BOT_RESTART_DELAY")
    attempt = 0
    started_at = 0.0

    while not stop_event.is_set():
        exit_code = await _run_once(stop_event)
        if stop_event.is_set():
            break
        attempt += 1
        if fixed_delay is not None:
            delay = float(fixed_delay)
        else:
            delay = min(max_backoff, 2 ** min(attempt, 6))
        logger.warning(
            "Бот завершился с кодом %s. Перезапуск через %.1fs (попытка %d)…",
            exit_code, delay, attempt,
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
    logger.info("run_bot завершил работу.")


def main() -> None:
    _setup_logging()
    try:
        asyncio.run(_supervisor())
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем.")


if __name__ == "__main__":
    main()
