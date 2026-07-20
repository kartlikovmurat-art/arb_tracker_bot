"""FSM-диалог и JSON-ввод для команды /add_trade.

Пошаговый режим собирает сделку из 14 шагов. JSON-режим
(после команды сразу идёт валидный JSON) шлёт данные в API
без диалога — для интеграций и быстрого ввода.

Новая модель ввода (v2):
  - Комиссии — в процентах: buy_fee_percent, sell_fee_percent.
  - Сеть перевода + газ — одно поле network_fee в USDT.
  - Время удержания вычисляется из bought_at / sold_at.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.bot.api import ApiClient, ApiError, TradePayload

logger = logging.getLogger(__name__)


# Популярные сети — пользователю проще выбрать, чем печатать.
COMMON_NETWORKS = [
    "ERC20", "TRC20", "BEP20", "Arbitrum", "Optimism",
    "Polygon", "Solana", "TON", "BTC", "Internal",
]


class TradeForm(StatesGroup):
    """Состояния пошагового ввода сделки (v2 — проценты + datetime)."""

    coin = State()
    buy_exchange = State()
    sell_exchange = State()
    amount = State()
    buy_price = State()
    sell_price = State()
    buy_fee_percent = State()
    sell_fee_percent = State()
    network_fee = State()
    transfer_network = State()
    bought_at = State()
    sold_at = State()
    strategy = State()
    note = State()


def _to_decimal(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _parse_datetime(text: str) -> Optional[datetime]:
    """
    Парсит 'YYYY-MM-DD HH:MM' или ISO 'YYYY-MM-DDTHH:MM:SS'.
    Возвращает naive datetime (UTC интерпретируется).
    Пусто / '-' → None.
    """
    s = text.strip()
    if not s or s == "-":
        return None
    s = s.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


async def _send_trade(api: ApiClient, message: Message, data: dict[str, Any]) -> None:
    """Отправляет сделку в API и отвечает пользователю."""
    try:
        user_id = message.from_user.id if message.from_user else 0
        await api.create_trade(TradePayload.from_raw(data), user_id=user_id)
    except ApiError as exc:
        logger.warning("create_trade failed: %s", exc)
        await message.answer(f"❌ Не удалось сохранить: {exc.detail or exc}")
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("unexpected error in create_trade")
        await message.answer(f"❌ Непредвиденная ошибка: {type(exc).__name__}: {exc}")
        return
    await message.answer("✅ Сделка сохранена.")


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_add_trade, Command("add_trade"))
    dp.message.register(step_coin, TradeForm.coin)
    dp.message.register(step_buy_exchange, TradeForm.buy_exchange)
    dp.message.register(step_sell_exchange, TradeForm.sell_exchange)
    dp.message.register(step_amount, TradeForm.amount)
    dp.message.register(step_buy_price, TradeForm.buy_price)
    dp.message.register(step_sell_price, TradeForm.sell_price)
    dp.message.register(step_buy_fee_percent, TradeForm.buy_fee_percent)
    dp.message.register(step_sell_fee_percent, TradeForm.sell_fee_percent)
    dp.message.register(step_network_fee, TradeForm.network_fee)
    dp.message.register(step_transfer_network, TradeForm.transfer_network)
    dp.message.register(step_bought_at, TradeForm.bought_at)
    dp.message.register(step_sold_at, TradeForm.sold_at)
    dp.message.register(step_strategy, TradeForm.strategy)
    dp.message.register(step_note, TradeForm.note)

    dp.workflow_data.update(api=api)


# ── хендлеры ──────────────────────────────────────────────────────────
async def cmd_add_trade(message: Message, state: FSMContext) -> None:
    """Точка входа: если после команды JSON — шлём напрямую, иначе FSM."""
    payload = (
        message.text.removeprefix("/add_trade").strip()
        if message.text
        else ""
    )
    if payload:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            await message.answer("Невалидный JSON. Проверьте синтаксис.")
            return
        if not isinstance(data, dict):
            await message.answer("Ожидаю JSON-объект, не массив и не скаляр.")
            return
        api: ApiClient = message.bot.get("api")  # type: ignore[arg-type]
        await _send_trade(api, message, data)
        return

    await state.set_state(TradeForm.coin)
    await message.answer(
        "Ввод новой сделки. /cancel — отмена.\n"
        "Введите монету (например, BTC):"
    )


async def step_coin(message: Message, state: FSMContext) -> None:
    await state.update_data(coin=(message.text or "").strip().upper())
    await state.set_state(TradeForm.buy_exchange)
    await message.answer("Введите биржу покупки (buy_exchange):")


async def step_buy_exchange(message: Message, state: FSMContext) -> None:
    await state.update_data(buy_exchange=(message.text or "").strip())
    await state.set_state(TradeForm.sell_exchange)
    await message.answer("Введите биржу продажи (sell_exchange):")


async def step_sell_exchange(message: Message, state: FSMContext) -> None:
    await state.update_data(sell_exchange=(message.text or "").strip())
    await state.set_state(TradeForm.amount)
    await message.answer("Введите объём (amount), например 0.5:")


async def step_amount(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "")
    if val is None or val <= 0:
        await message.answer(
            "Неверный формат числа для объёма. Введите число > 0 или /cancel."
        )
        return
    await state.update_data(amount=str(val))
    await state.set_state(TradeForm.buy_price)
    await message.answer("Введите цену покупки (buy_price):")


async def step_buy_price(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "")
    if val is None or val <= 0:
        await message.answer(
            "Неверный формат числа для цены покупки. Введите число > 0 или /cancel."
        )
        return
    await state.update_data(buy_price=str(val))
    await state.set_state(TradeForm.sell_price)
    await message.answer("Введите цену продажи (sell_price):")


async def step_sell_price(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "")
    if val is None or val <= 0:
        await message.answer(
            "Неверный формат числа для цены продажи. Введите число > 0 или /cancel."
        )
        return
    await state.update_data(sell_price=str(val))
    await state.set_state(TradeForm.buy_fee_percent)
    await message.answer(
        "💸  <b>Комиссия за покупку (в %)</b>\n"
        "Например: <code>0.1</code> = 0.1% (как у Binance).\n"
        "Введите число или '-' чтобы пропустить:"
    )


async def step_buy_fee_percent(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        val = _to_decimal(text)
        if val is None or val < 0:
            await message.answer("Неверный формат. Введите число ≥ 0 или '-'.")
            return
        await state.update_data(buy_fee_percent=str(val))
    await state.set_state(TradeForm.sell_fee_percent)
    await message.answer(
        "💸  <b>Комиссия за продажу (в %)</b>\n"
        "Например: <code>0.15</code> = 0.15% (как у Bybit).\n"
        "Введите число или '-' чтобы пропустить:"
    )


async def step_sell_fee_percent(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        val = _to_decimal(text)
        if val is None or val < 0:
            await message.answer("Неверный формат. Введите число ≥ 0 или '-'.")
            return
        await state.update_data(sell_fee_percent=str(val))
    await state.set_state(TradeForm.network_fee)
    await message.answer(
        "🌐  <b>Комиссия за вывод + сеть (в USDT)</b>\n"
        "Одно число: сумма комиссии за вывод монеты + gas сети.\n"
        "Например: <code>2.5</code> (USDT).\n"
        "Введите число или '-' чтобы пропустить:"
    )


async def step_network_fee(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        val = _to_decimal(text)
        if val is None or val < 0:
            await message.answer("Неверный формат. Введите число ≥ 0 или '-'.")
            return
        await state.update_data(network_fee=str(val))
    await state.set_state(TradeForm.transfer_network)
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = [
        [InlineKeyboardButton(text=n, callback_data=f"net:{n}")]
        for n in COMMON_NETWORKS[:5]
    ]
    buttons.append([InlineKeyboardButton(text="…другие", callback_data="net:more")])
    await message.answer(
        "🔗  <b>Сеть перевода</b> (ERC20, TRC20, ...):\n"
        "Нажми кнопку или введи текстом. '-' чтобы пропустить.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


async def step_transfer_network(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        await state.update_data(transfer_network=text)
    await state.set_state(TradeForm.bought_at)
    await message.answer(
        "🕐  <b>Время покупки (bought_at)</b>\n"
        "Формат: <code>2025-07-21 14:30</code> или <code>2025-07-21T14:30</code>.\n"
        "'-' если ещё не купил (PENDING)."
    )


async def step_bought_at(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        dt = _parse_datetime(text)
        if dt is None:
            await message.answer(
                "Не понял дату. Пример: <code>2025-07-21 14:30</code> или '-'."
            )
            return
        await state.update_data(bought_at=dt.replace(tzinfo=timezone.utc).isoformat())
    await state.set_state(TradeForm.sold_at)
    await message.answer(
        "🕐  <b>Время продажи (sold_at)</b>\n"
        "Такой же формат. '-' если ещё держишь.\n"
        "💡  Я сам посчитаю время удержания сделки."
    )


async def step_sold_at(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        dt = _parse_datetime(text)
        if dt is None:
            await message.answer(
                "Не понял дату. Пример: <code>2025-07-21 16:45</code> или '-'."
            )
            return
        await state.update_data(sold_at=dt.replace(tzinfo=timezone.utc).isoformat())
    await state.set_state(TradeForm.strategy)
    await message.answer("Стратегия (опционально) или '-' чтобы пропустить:")


async def step_strategy(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        await state.update_data(strategy=text)
    await state.set_state(TradeForm.note)
    await message.answer("Комментарий (опционально) или '-' чтобы пропустить:")


async def step_note(
    message: Message,
    state: FSMContext,
    api: ApiClient,  # type: ignore[assignment]
) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    if text and text != "-":
        data["note"] = text
    await _send_trade(api, message, data)
    await state.clear()
