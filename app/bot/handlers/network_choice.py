"""Обработчик inline-кнопок выбора сети в /add_trade."""
from __future__ import annotations

import logging

from aiogram import Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.handlers.add_trade import COMMON_NETWORKS, TradeForm

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api) -> None:  # noqa: ANN001
    """Регистрирует callback'и для выбора сети."""
    dp.callback_query.register(
        _on_network,
        F.data.startswith("net:"),
    )


async def _on_network(callback: CallbackQuery, state: FSMContext) -> None:
    assert callback.data is not None
    payload = callback.data.split(":", 1)[1]

    if payload == "more":
        # Показать остальные сети
        rest = COMMON_NETWORKS[5:]
        buttons = [
            [InlineKeyboardButton(text=n, callback_data=f"net:{n}")]
            for n in rest
        ]
        buttons.append([InlineKeyboardButton(text="↩ назад", callback_data="net:back")])
        if callback.message is not None:
            await callback.message.edit_reply_markup(  # type: ignore[union-attr]
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
        await callback.answer()
        return

    if payload == "back":
        # Назад к первым 5
        from app.bot.handlers.add_trade import COMMON_NETWORKS
        first = COMMON_NETWORKS[:5]
        buttons = [
            [InlineKeyboardButton(text=n, callback_data=f"net:{n}")]
            for n in first
        ]
        buttons.append([InlineKeyboardButton(text="…другие", callback_data="net:more")])
        if callback.message is not None:
            await callback.message.edit_reply_markup(  # type: ignore[union-attr]
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
        await callback.answer()
        return

    # Конкретная сеть выбрана
    await state.update_data(transfer_network=payload)
    await state.set_state(TradeForm.holding_time)
    if callback.message is not None:
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"🔗  Сеть: <b>{payload}</b> ✓\n\n"
            "⏱  Время от покупки до продажи (holding time):\n"
            "Формат: <code>5m</code> = 5 мин, <code>2h</code> = 2 ч, "
            "<code>1d3h</code> = 1 день 3 ч, или просто число секунд.\n"
            "'-' если ещё не закрыл сделку (PENDING)."
        )
    await callback.answer(f"Сеть: {payload}")
