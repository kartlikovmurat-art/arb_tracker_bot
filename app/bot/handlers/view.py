"""Просмотр сделок: /trades, /trades_id, /trades_coin, /trades_exchange."""
from __future__ import annotations

import logging
from typing import Any, Optional

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.api import ApiClient, ApiError
from app.bot.formatters import (
    format_trade,
    format_trades_page,
)
from app.bot.formatters.text import PAGE_SIZE
from app.bot.handlers._pagination_view import build_trades_view
from app.bot.keyboards import trade_actions_kb, trades_pager

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_trades, Command("trades"))
    dp.message.register(cmd_trades_id, Command("trades_id"))
    dp.message.register(cmd_trades_coin, Command("trades_coin"))
    dp.message.register(cmd_trades_exchange, Command("trades_exchange"))


async def _fetch_trades(
    api: ApiClient,
    user_id: int,
    *,
    coin: Optional[str] = None,
    exchange: Optional[str] = None,
) -> list[dict[str, Any]]:
    try:
        return await api.list_trades(user_id, coin=coin, exchange=exchange)
    except ApiError as exc:
        logger.warning("list_trades failed: %s", exc)
        raise


async def cmd_trades(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        uid = message.from_user.id if message.from_user else 0
        trades = await _fetch_trades(api, uid)
    except ApiError as exc:
        await message.answer(f"❌ Не удалось получить сделки: {exc.detail or exc}")
        return
    text, keyboard = build_trades_view(trades, page=0)
    await message.answer(text, reply_markup=keyboard)


async def cmd_trades_id(
    message: Message,
    command: Any,  # aiogram.CommandObject
    api: ApiClient,  # type: ignore[assignment]
) -> None:
    args = (command.args or "").strip() if command else ""
    if not args or not args.isdigit():
        await message.answer("Использование: <code>/trades_id 42</code>")
        return
    try:
        uid = message.from_user.id if message.from_user else 0
        trade = await api.get_trade(int(args), uid)
    except ApiError as exc:
        await message.answer(
            "❌ Сделка не найдена."
            if exc.status_code == 404
            else f"❌ Ошибка API: {exc.detail or exc}"
        )
        return
    await message.answer(format_trade(trade), reply_markup=trade_actions_kb(int(args)))


async def cmd_trades_coin(
    message: Message,
    command: Any,
    api: ApiClient,  # type: ignore[assignment]
) -> None:
    coin = (command.args or "").strip() if command else ""
    if not coin:
        await message.answer("Использование: <code>/trades_coin BTC</code>")
        return
    try:
        uid = message.from_user.id if message.from_user else 0
        trades = await _fetch_trades(api, uid, coin=coin.upper())
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    text, keyboard = build_trades_view(trades, page=0)
    await message.answer(text, reply_markup=keyboard)


async def cmd_trades_exchange(
    message: Message,
    command: Any,
    api: ApiClient,  # type: ignore[assignment]
) -> None:
    exchange = (command.args or "").strip() if command else ""
    if not exchange:
        await message.answer(
            "Использование: <code>/trades_exchange Binance</code>"
        )
        return
    try:
        uid = message.from_user.id if message.from_user else 0
        trades = await _fetch_trades(api, uid, exchange=exchange)
    except ApiError as exc:
        await message.answer(f"❌ Ошибка: {exc.detail or exc}")
        return
    text, keyboard = build_trades_view(trades, page=0)
    await message.answer(text, reply_markup=keyboard)
