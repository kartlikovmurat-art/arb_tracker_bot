"""Базовые команды: /start, /help, /cancel.

``/cancel`` общий для FSM-диалогов (добавление сделки).
"""
from __future__ import annotations

from aiogram import Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.help_text import HELP_TEXT
from app.bot.keyboards import help_menu


WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в Arbitrage Tracker Bot!</b>\n\n"
    "Это твоя личная CRM для учёта завершённых арбитражных сделок.\n"
    "Все данные хранятся локально и никуда не утекают.\n\n"
    "Открой /help, чтобы увидеть полный список команд."
)


def register(dp: Dispatcher) -> None:
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_cancel, Command("cancel"))
    dp.callback_query.register(help_callback, lambda c: c.data and c.data.startswith("help:"))


async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=help_menu())


async def help_callback(callback: CallbackQuery) -> None:
    """Показывает подсказку по выбранной из меню команде."""
    assert callback.data is not None
    section = callback.data.split(":", 1)[1]
    text = HELP_TEXT  # единый текст, секции уже есть
    await callback.message.answer(text)  # type: ignore[union-attr]
    await callback.answer(f"Раздел: {section}")


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Нет активного ввода.")
        return
    await state.clear()
    await message.answer("Ввод сделки отменён.")
