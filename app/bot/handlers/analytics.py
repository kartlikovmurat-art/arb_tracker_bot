"""Команды аналитики: /stats, /month, /daily, /coin, /exchange, /strategy, /equity."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.api import ApiClient, ApiError
from app.bot.formatters import (
    format_dict_stats,
    format_equity_curve,
    format_overall_stats,
)

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_month, Command("month"))
    dp.message.register(cmd_daily, Command("daily"))
    dp.message.register(cmd_coin, Command("coin"))
    dp.message.register(cmd_exchange, Command("exchange"))
    dp.message.register(cmd_strategy, Command("strategy"))
    dp.message.register(cmd_equity, Command("equity"))


async def _safe(
    message: Message,
    coro: Callable[[], Awaitable[Any]],
    *,
    on_error: str,
) -> None:
    """Запускает запрос к API и шлёт пользователю исключение, если что."""
    try:
        data = await coro()
    except ApiError as exc:
        await message.answer(f"❌ {on_error}: {exc.detail or exc}")
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("unexpected error in analytics handler")
        await message.answer(f"❌ Непредвиденная ошибка: {type(exc).__name__}: {exc}")
        return
    await message.answer(str(data))


async def cmd_stats(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        data = await api.overall_stats()
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    await message.answer(format_overall_stats(data))


async def cmd_month(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        data = await api.monthly_stats()
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    await message.answer(format_dict_stats("Статистика по месяцам", data))


async def cmd_daily(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        data = await api.daily_stats()
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    await message.answer(format_dict_stats("Статистика по дням", data, top_n=20))


async def cmd_coin(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        data = await api.coin_stats()
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    await message.answer(format_dict_stats("Статистика по монетам", data))


async def cmd_exchange(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        data = await api.exchange_stats()
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    await message.answer(format_dict_stats("Статистика по биржам", data))


async def cmd_strategy(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        data = await api.strategy_stats()
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    await message.answer(format_dict_stats("Статистика по стратегиям", data))


async def cmd_equity(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        points = await api.equity_curve()
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    await message.answer(format_equity_curve(points))
