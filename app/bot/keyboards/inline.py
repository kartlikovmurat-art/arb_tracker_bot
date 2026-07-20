"""Инлайн-клавиатуры aiogram.

Callback-data — короткие строки с разделителем ``|``:
    trades:page:<n>     — открыть страницу сделок.
    help:<command>      — подсказка по конкретной команде.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def trades_pager(
    *,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Кнопки ‹/›/обновить для пагинации по сделкам."""
    buttons: list[list[InlineKeyboardButton]] = []

    nav: list[InlineKeyboardButton] = []
    nav.append(
        InlineKeyboardButton(
            text="⏮ 1",
            callback_data=f"trades:page:0",
        )
    )
    nav.append(
        InlineKeyboardButton(
            text="‹ Назад",
            callback_data=f"trades:page:{max(0, page - 1)}",
        )
    )
    nav.append(
        InlineKeyboardButton(
            text=f"· {page + 1}/{total_pages} ·",
            callback_data="trades:noop",
        )
    )
    nav.append(
        InlineKeyboardButton(
            text="Вперёд ›",
            callback_data=f"trades:page:{min(total_pages - 1, page + 1)}",
        )
    )
    nav.append(
        InlineKeyboardButton(
            text="⏭ ⠀",
            callback_data=f"trades:page:{max(0, total_pages - 1)}",
        )
    )
    buttons.append(nav)

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data=f"trades:page:{page}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def help_menu() -> InlineKeyboardMarkup:
    """Кнопки-подсказки для /help."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить сделку",
                    callback_data="help:add_trade",
                ),
                InlineKeyboardButton(
                    text="📋 Сделки",
                    callback_data="help:trades",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="help:stats",
                ),
                InlineKeyboardButton(
                    text="📈 Аналитика",
                    callback_data="help:analytics",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📤 Экспорт",
                    callback_data="help:export",
                )
            ],
        ]
    )
