"""Common commands: /start, /help, /menu, /cancel."""
from __future__ import annotations

from aiogram import Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.bot.handlers.help_text import HELP_TEXT
from app.bot.keyboards import main_menu
from app.bot.keyboards.reply import main_reply_keyboard

MINIAPP_URL = "https://arb-tracker-miniapp.pages.dev/"


def miniapp_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀  Открыть Mini App", web_app=WebAppInfo(url=MINIAPP_URL))]
    ])


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
    # /start регистрируем ТОЛЬКО здесь.

    dp.message.register(cmd_menu, Command("menu"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_cancel, Command("cancel"))

    dp.callback_query.register(
        menu_home,
        lambda c: c.data == "menu:home",
    )

    dp.callback_query.register(
        menu_help,
        lambda c: c.data == "menu:help",
    )


async def cmd_start(message: Message) -> None:
    # INLINE-МЕНЮ под сообщением
    await message.answer(
        WELCOME_TEXT,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🚀  Открыть Mini App",
                    web_app=WebAppInfo(url=MINIAPP_URL),
                )
            ]]
        ),
    )

    # НИЖНЯЯ ПОСТОЯННАЯ КЛАВИАТУРА
    await message.answer(
        "👇  <b>Панель быстрого доступа</b> — закреплена снизу.\n"
        "Можешь нажимать кнопки или писать команды.",
        reply_markup=main_reply_keyboard(),
    )


async def cmd_menu(message: Message) -> None:
    await message.answer(
        MENU_TEXT,
        reply_markup=main_menu(),
    )


async def cmd_help(message: Message) -> None:
    await message.answer(
        HELP_TEXT,
        reply_markup=main_menu(),
    )


async def menu_home(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    await callback.message.edit_text(
        MENU_TEXT,
        reply_markup=main_menu(),
    )

    await callback.answer()


async def menu_help(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    await callback.message.edit_text(
        HELP_TEXT,
        reply_markup=main_menu(),
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
