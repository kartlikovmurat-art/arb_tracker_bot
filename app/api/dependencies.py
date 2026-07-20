"""Общие зависимости для FastAPI эндпоинтов."""
from __future__ import annotations

from fastapi import Header


async def current_user_id(
    x_telegram_user_id: int | None = Header(
        default=None,
        alias="X-Telegram-User-Id",
        description="Telegram user id владельца сделок. "
        "Бот прокидывает его автоматически из message.from_user.id.",
    ),
    x_user_id: int | None = Header(
        default=None,
        alias="X-User-Id",
        description="Альтернативный заголовок (используется веб-приложением).",
    ),
) -> int:
    """
    Возвращает telegram user id из заголовка.

    Любой из двух заголовков принимается; если оба отсутствуют —
    возвращает ``0`` (режим legacy / анонимный).
    """
    uid = x_telegram_user_id or x_user_id or 0
    return int(uid)
