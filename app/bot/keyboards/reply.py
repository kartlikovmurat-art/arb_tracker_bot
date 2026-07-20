"""Reply keyboards — постоянная панель кнопок снизу экрана.

В отличие от ``InlineKeyboardMarkup`` (которые привязаны к сообщению
и уезжают вместе с ним), ``ReplyKeyboardMarkup`` заменяет системную
клавиатуру телефона и видна всегда, пока пользователь её не свернёт.

Текст нажатой кнопки Telegram отправляет боту как обычный message —
поэтому в ``handlers/menu.py`` есть ``REPLY_MENU_ACTIONS``, словарь
``текст кнопки -> действие``, и хендлер ``reply_menu_router``,
который их ловит.
"""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


# Текст кнопок — это ключи словаря REPLY_MENU_ACTIONS в handlers/menu.py.
# Меняй их здесь и там синхронно.
BTN_ADD = "➕  Добавить"
BTN_TRADES = "📋  Сделки"
BTN_STATS = "📊  Статистика"
BTN_ANALYTICS = "📈  Аналитика"
BTN_EXPORT = "📤  Экспорт"
BTN_HELP = "❓  Помощь"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная панель: 6 кнопок в 2 ряда, видна всегда внизу экрана."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_ADD),
                KeyboardButton(text=BTN_TRADES),
                KeyboardButton(text=BTN_STATS),
            ],
            [
                KeyboardButton(text=BTN_ANALYTICS),
                KeyboardButton(text=BTN_EXPORT),
                KeyboardButton(text=BTN_HELP),
            ],
        ],
        resize_keyboard=True,   # подгоняет размер под кнопки
        one_time_keyboard=False,  # НЕ скрывается после нажатия
        input_field_placeholder="Введи команду или нажми кнопку…",
        selective=False,
        is_persistent=True,     # aiogram 3.7+: остаётся видимой между сессиями
    )


def remove_reply_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с одной служебной кнопкой, по сути — способ её убрать.
    Используй ``ReplyKeyboardRemove`` из aiogram напрямую, если хочешь
    полностью убрать панель.
    """
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()  # type: ignore[return-value]
