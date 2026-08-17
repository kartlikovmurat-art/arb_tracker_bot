"""Reply keyboards — постоянная панель кнопок снизу экрана."""
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


# Текст кнопок = ключи в handlers/menu.py:REPLY_MENU_ACTIONS.
BTN_ADD = "➕  Добавить"
BTN_TRADES = "📋  Сделки"
BTN_LAST = "🕐  Последняя"
BTN_TODAY = "📅  Сегодня"
BTN_WEEK = "📆  Неделя"
BTN_STATS = "📊  Статистика"
BTN_ANALYTICS = "📈  Аналитика"
BTN_GOAL = "🎯  Цель"
BTN_CALC = "🧮  Калькулятор"
BTN_EXPORT = "📤  Экспорт"
BTN_BACKUP = "💾  Бэкап"
BTN_HELP = "❓  Помощь"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная панель: 12 кнопок в 4 ряда, видна всегда внизу экрана."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_ADD),
                KeyboardButton(text=BTN_TRADES),
                KeyboardButton(text=BTN_LAST),
            ],
            [
                KeyboardButton(text=BTN_TODAY),
                KeyboardButton(text=BTN_WEEK),
                KeyboardButton(text=BTN_STATS),
            ],
            [
                KeyboardButton(text=BTN_ANALYTICS),
                KeyboardButton(text=BTN_GOAL),
                KeyboardButton(text=BTN_CALC),
            ],
            [
                KeyboardButton(text=BTN_EXPORT),
                KeyboardButton(text=BTN_BACKUP),
                KeyboardButton(text=BTN_HELP),
            ],
            [
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Введи команду или нажми кнопку…",
        selective=False,
        is_persistent=True,
    )
