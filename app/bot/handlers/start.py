"""Приветственное сообщение для /start и любого первого контакта.

Показывает что умеет бот, даёт быстрый доступ к основным действиям
через inline-кнопки. Можно привязать к командам ``/start``,
``/help`` и ``startapp=open`` (deep link из Mini App).
"""
from __future__ import annotations

import logging

from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.bot.api import ApiClient, ApiError
from app.bot.keyboards import main_menu

logger = logging.getLogger(__name__)


# Текст приветствия. Достаточно подробный, чтобы новый пользователь
# сразу понял что к чему, и не терялся в первый запуск.
WELCOME_TEXT = (
    "💼  <b>Arb Tracker</b> — твой личный CRM для арбитража\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    "📊  Учёт каждой сделки: покупка/продажа, объём, цены, "
    "все комиссии (buy, sell, withdrawal, gas), проскальзывание.\n\n"

    "🔗  Сеть перевода (ERC20, TRC20, BEP20, BTC, TON, …) — "
    "видно сколько съел газ и какая сеть была между биржами.\n\n"

    "⏱  Время удержания сделки — сколько пролежала монета "
    "от покупки до продажи. Полезно для оценки стратегий.\n\n"

    "📈  Аналитика: P/L, ROI, win-rate, статистика по монетам, "
    "биржам, стратегиям, equity curve.\n\n"

    "🔒  Каждый пользователь видит <b>только свои</b> сделки — "
    "изоляция по telegram user id.\n\n"

    "💾  Бэкап/импорт JSON, Excel-выгрузка.\n"
    "🔍  Поиск, фильтры, калькулятор P/L.\n"
    "🌐  Mini App (веб-интерфейс) — кнопкой ниже.\n\n"

    "<i>Нажми /help, чтобы увидеть все команды.</i>"
)


WELCOME_PIC_URL = (
    "https://raw.githubusercontent.com/kartlikovmurat-art/"
    "arb_tracker_bot/main/assets/welcome.png"
)


def welcome_keyboard() -> InlineKeyboardMarkup:
    """Главное меню приветствия — 4 inline-кнопки на старт."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕  Добавить сделку",
                    callback_data="welcome:add",
                ),
                InlineKeyboardButton(
                    text="📋  Мои сделки",
                    callback_data="welcome:trades",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊  Статистика",
                    callback_data="welcome:stats",
                ),
                InlineKeyboardButton(
                    text="🧮  Калькулятор",
                    callback_data="welcome:calc",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌐  Открыть Mini App",
                    url="https://t.me/arb_tracker_cex_bot?startapp=open",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❓  Все команды",
                    callback_data="welcome:help",
                ),
            ],
        ]
    )


def register(dp: Dispatcher, api: ApiClient) -> None:  # noqa: ARG001
    """Подключает /start, /help и callback'и кнопок приветствия."""
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_start, Command("start"))
    # Deep link от Mini App / WebApp
    dp.message.register(cmd_start, Command("startapp"))
    # Колбэки
    dp.callback_query.register(
        _on_welcome,
        F.data.startswith("welcome:"),
    )


async def cmd_start(
    message: Message,
    command: "CommandStart | None" = None,  # type: ignore[name-defined]
) -> None:
    """Приветствие с картинкой (если доступна) и клавиатурой."""
    name = ""
    if message.from_user:
        name = message.from_user.first_name or message.from_user.username or ""
    greeting = (
        f"👋 Привет, <b>{name}</b>!\n\n" if name else "👋 Привет!\n\n"
    )
    text = greeting + WELCOME_TEXT

    # Пробуем отправить картинку + текст, fallback — просто текст
    try:
        await message.answer_photo(
            photo=WELCOME_PIC_URL,
            caption=text,
            reply_markup=welcome_keyboard(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("welcome pic not available: %s", exc)
        await message.answer(
            text,
            reply_markup=welcome_keyboard(),
        )


async def _on_welcome(callback: CallbackQuery, api: ApiClient) -> None:  # noqa: ARG001
    """Обрабатывает inline-кнопки приветствия."""
    assert callback.data is not None
    action = callback.data.split(":", 1)[1]
    if callback.message is None:
        await callback.answer()
        return

    if action == "add":
        await callback.message.edit_text(  # type: ignore[union-attr]
            "➕  <b>Добавление сделки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Доступно три способа:\n\n"
            "📝  <b>Пошаговый ввод</b> — нажми <code>/add_trade</code> "
            "и бот спросит всё по очереди (монета, биржи, цены, "
            "все комиссии, сеть, время удержания, стратегия).\n\n"
            "⚡  <b>JSON-режим</b> — <code>/add_trade {JSON}</code> одной строкой.\n\n"
            "🌐  <b>Mini App</b> — кнопка ниже с красивой формой.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🌐  Открыть Mini App",
                            url="https://t.me/arb_tracker_cex_bot?startapp=open",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="↩ Назад", callback_data="welcome:back"
                        )
                    ],
                ]
            ),
        )
    elif action == "trades":
        # Перенаправляем в view.py:cmd_trades
        from app.bot.handlers.view import cmd_trades
        # Создаём фейковый объект message через переиспользование api
        from app.bot.api import ApiError
        user_id = callback.from_user.id if callback.from_user else 0
        try:
            trades = await api.list_trades(user_id)
        except ApiError as exc:
            await callback.answer(f"Ошибка: {exc.detail or exc}", show_alert=True)
            return
        from app.bot.handlers._pagination_view import build_trades_view
        text, keyboard = build_trades_view(trades, page=0)
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                text, reply_markup=keyboard or main_menu()
            )
    elif action == "stats":
        from app.bot.api import ApiError
        user_id = callback.from_user.id if callback.from_user else 0
        try:
            data = await api.overall_stats(user_id)
        except ApiError as exc:
            await callback.answer(f"Ошибка: {exc.detail or exc}", show_alert=True)
            return
        from app.bot.formatters import format_overall_stats
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                format_overall_stats(data), reply_markup=main_menu()
            )
    elif action == "calc":
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                "🧮  <b>Калькулятор P/L</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Нажми <code>/calc</code> — бот попросит параметры по очереди:\n"
                "объём, цена покупки, цена продажи, все комиссии.\n"
                "Посчитает прибыль и ROI без сохранения в базу.\n\n"
                "💡  Удобно прикинуть сделку ДО её совершения.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="↩ Назад", callback_data="welcome:back"
                            )
                        ],
                    ]
                ),
            )
    elif action == "help":
        from app.bot.handlers.help_text import HELP_TEXT
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                HELP_TEXT, reply_markup=main_menu()
            )
    elif action == "back":
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                WELCOME_TEXT, reply_markup=welcome_keyboard()
            )

    await callback.answer()
