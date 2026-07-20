"""Регистрация всех хендлеров в диспетчере aiogram.

Каждый подмодуль экспортирует ``register(dp, api, ...)`` — точка
входа, которая вешает все обработчики своей группы. ``bot.py``
просто вызывает ``register_all(dp, api)`` из этого файла.
"""
from __future__ import annotations

from aiogram import Dispatcher

from app.bot.api import ApiClient
from app.bot.handlers import (
    add_trade,
    analytics,
    common,
    export,
    pagination,
    view,
)


def register_all(dp: Dispatcher, api: ApiClient) -> None:
    """Подключает все группы хендлеров. Порядок не критичен."""
    common.register(dp)
    add_trade.register(dp, api)
    view.register(dp, api)
    analytics.register(dp, api)
    export.register(dp, api)
    # pagination должен идти ПОСЛЕ view, чтобы перехватывать callback'и
    # ``trades:page:...`` независимо от того, откуда они пришли.
    pagination.register(dp, api)
