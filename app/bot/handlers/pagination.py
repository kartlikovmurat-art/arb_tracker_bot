"""Callback-хендлер для пагинации сделок (inline-кнопки)."""
from __future__ import annotations

import logging
from typing import Any

from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from app.bot.api import ApiClient, ApiError
from app.bot.handlers._pagination_view import build_trades_view

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.callback_query.register(
        _on_pager,
        lambda c: c.data is not None and c.data.startswith("trades:page:"),
    )
    dp.callback_query.register(
        _on_noop,
        lambda c: c.data == "trades:noop",
    )
    dp.workflow_data.update(api=api)


async def _on_pager(
    callback: CallbackQuery,
    api: ApiClient,  # type: ignore[assignment]
) -> None:
    assert callback.data is not None
    parts = callback.data.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer("Некорректный callback.")
        return
    page = int(parts[2])
    try:
        uid = callback.from_user.id if callback.from_user else 0
        trades = await api.list_trades(uid)
    except ApiError as exc:
        await callback.answer(f"Ошибка: {exc.detail or exc}", show_alert=True)
        return
    text, keyboard = build_trades_view(trades, page=page)
    if callback.message is None:
        await callback.answer()
        return
    # Если пагинация отключилась (total_pages == 1) — редактируем без клавиатуры.
    await callback.message.edit_text(  # type: ignore[union-attr]
        text, reply_markup=keyboard
    )
    await callback.answer()


async def _on_noop(callback: CallbackQuery) -> None:
    # Просто гасим «часики» на кнопке с номером страницы.
    await callback.answer()
