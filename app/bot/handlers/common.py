"""Common commands: /start, /help, /menu, /cancel.

The /start reply now carries a proper main-menu keyboard so the user
can drive the bot with buttons rather than typing commands. /menu
shows the same menu at any time. /cancel clears any in-progress FSM
dialog.
"""
from __future__ import annotations

from aiogram import Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.help_text import HELP_TEXT
from app.bot.keyboards import main_menu
from app.bot.keyboards.reply import main_reply_keyboard


WELCOME_TEXT = (
    "👋  <b>Добро пожаловать в Arbitrage Tracker Bot!</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "💼  Это твоя личная CRM для учёта\n"
    "    завершённых арбитражных сделок.\n\n"
    "🔐  Все данные хранятся локально\n"
    "    и никуда не утекают.\n\n"
    "📊  История — единственный источник истины.\n"
    "    Вся аналитика считается из неё.\n\n"
    "👇  <i>Выбирай действие в меню ниже — быстрее, чем команды.</i>\n"
)


MENU_TEXT = (
    "🏠  <b>Главное меню</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Что делаем?\n"
)


def register(dp: Dispatcher) -> None:
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_menu, Command("menu"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_cancel, Command("cancel"))
    # Callback'и от кнопок главного меню.
    dp.callback_query.register(
        menu_home,
        lambda c: c.data == "menu:home",
    )
    dp.callback_query.register(
        menu_help,
        lambda c: c.data == "menu:help",
    )


async def cmd_start(message: Message) -> None:
    # Показываем и inline-меню (кнопки под сообщением) и reply-меню
    # (постоянная панель снизу экрана). Оба не мешают друг другу.
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu(),
    )
    # Показываем панельку отдельным сообщением, чтобы Telegram принял её
    # без сюрпризов (некоторые клиенты игнорируют reply_markup после edit).
    await message.answer(
        "👇  <b>Панель быстрого доступа</b> — закреплена снизу.\n"
        "Можешь нажимать кнопки или писать команды.",
        reply_markup=main_reply_keyboard(),
    )


async def cmd_menu(message: Message) -> None:
    await message.answer(MENU_TEXT, reply_markup=main_menu())


async def cmd_help(message: Message) -> None:
    await message.answer(
        HELP_TEXT,
        reply_markup=main_menu(),
    )


async def menu_home(callback: CallbackQuery) -> None:
    """Callback: «В меню» / «Назад» — редактирует сообщение на главное меню."""
    if callback.message is None:
        await callback.answer()
        return
    await callback.message.edit_text(  # type: ignore[union-attr]
        MENU_TEXT, reply_markup=main_menu()
    )
    await callback.answer()


async def menu_help(callback: CallbackQuery) -> None:
    """Callback от кнопки «❓ Помощь»."""
    if callback.message is None:
        await callback.answer()
        return
    await callback.message.edit_text(  # type: ignore[union-attr]
        HELP_TEXT, reply_markup=main_menu()
    )
    await callback.answer()


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer(
            "🤷  Нет активного ввода.\n"
            "Можешь начать с /start или нажать кнопку в меню."
        )
        return
    await state.clear()
    await message.answer(
        "✖️  Ввод сделки отменён.\n"
        "Если хочешь начать заново — /add_trade или кнопка ➕ в меню."
    )
