"""Inline keyboards aiogram.

Callback-data convention (short strings, ``:``-separated):
    trades:page:<n>      open trade-list page n
    trades:noop          no-op (close the spinner on a static button)
    menu:add              open add-trade menu
    menu:trades           show trades
    menu:stats            show overall stats
    menu:analytics        show analytics menu
    menu:export           export to xlsx
    menu:help             show /help
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# ── Главное меню (стартовый экран) ────────────────────────────────────
def main_menu() -> InlineKeyboardMarkup:
    """Красивое главное меню: 6 кнопок в две колонки + статус."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕  Добавить сделку",
                    callback_data="menu:add",
                ),
                InlineKeyboardButton(
                    text="📋  Мои сделки",
                    callback_data="menu:trades",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊  Статистика",
                    callback_data="menu:stats",
                ),
                InlineKeyboardButton(
                    text="📈  Аналитика",
                    callback_data="menu:analytics",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📤  Экспорт в Excel",
                    callback_data="menu:export",
                ),
                InlineKeyboardButton(
                    text="❓  Помощь",
                    callback_data="menu:help",
                ),
            ],
        ]
    )


def analytics_menu() -> InlineKeyboardMarkup:
    """Подменю аналитики."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅  По месяцам",
                    callback_data="menu:month",
                ),
                InlineKeyboardButton(
                    text="🗓  По дням",
                    callback_data="menu:daily",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🪙  По монетам",
                    callback_data="menu:coin",
                ),
                InlineKeyboardButton(
                    text="🏦  По биржам",
                    callback_data="menu:exchange",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎯  По стратегиям",
                    callback_data="menu:strategy",
                ),
                InlineKeyboardButton(
                    text="📈  Кривая доходности",
                    callback_data="menu:equity",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️  Назад в меню",
                    callback_data="menu:home",
                ),
            ],
        ]
    )


def add_trade_menu() -> InlineKeyboardMarkup:
    """Меню добавления сделки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝  Пошаговый ввод",
                    callback_data="menu:add_step",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚡  JSON-ввод",
                    callback_data="menu:add_json",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️  Назад в меню",
                    callback_data="menu:home",
                ),
            ],
        ]
    )


# ── Пагинация по сделкам ──────────────────────────────────────────────
def trades_pager(
    *,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    nav: list[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text="⏮",
            callback_data=f"trades:page:0",
        ),
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"trades:page:{max(0, page - 1)}",
        ),
        InlineKeyboardButton(
            text=f"· {page + 1}/{total_pages} ·",
            callback_data="trades:noop",
        ),
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"trades:page:{min(total_pages - 1, page + 1)}",
        ),
        InlineKeyboardButton(
            text="⏭",
            callback_data=f"trades:page:{max(0, total_pages - 1)}",
        ),
    ]
    buttons.append(nav)
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔄  Обновить",
                callback_data=f"trades:page:{page}",
            ),
            InlineKeyboardButton(
                text="⬅️  В меню",
                callback_data="menu:home",
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Меню help (используется внутри /help) ────────────────────────────
def help_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕  Добавить сделку",
                    callback_data="menu:add",
                ),
                InlineKeyboardButton(
                    text="📋  Мои сделки",
                    callback_data="menu:trades",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊  Статистика",
                    callback_data="menu:stats",
                ),
                InlineKeyboardButton(
                    text="📈  Аналитика",
                    callback_data="menu:analytics",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📤  Экспорт",
                    callback_data="menu:export",
                ),
                InlineKeyboardButton(
                    text="⬅️  В меню",
                    callback_data="menu:home",
                ),
            ],
        ]
    )
