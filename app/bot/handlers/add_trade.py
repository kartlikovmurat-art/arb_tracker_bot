"""FSM-диалог и JSON-ввод для команды /add_trade.

Пошаговый режим собирает сделку из 12 шагов. JSON-режим
(после команды сразу идёт валидный JSON) шлёт данные в API
без диалога — для интеграций и быстрого ввода.
"""
from __future__ import annotations

import json
import logging
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
# Любую другую можно ввести текстом (двойное нажатие "-" очищает).
COMMON_NETWORKS = [
    "ERC20", "TRC20", "BEP20", "Arbitrum", "Optimism",
    "Polygon", "Solana", "TON", "BTC", "Internal",
]


class TradeForm(StatesGroup):
    """Состояния пошагового ввода сделки."""

    coin = State()
    buy_exchange = State()
    sell_exchange = State()
    amount = State()
    buy_price = State()
    sell_price = State()
    buy_fee = State()
    sell_fee = State()
    withdrawal_fee = State()
    gas_fee = State()
    transfer_network = State()
    holding_time = State()
    strategy = State()
    note = State()


def _to_decimal(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _parse_holding_time(text: str) -> Optional[int]:
    """Парсит «5m», «2h», «3d», «1h30m», «90» (секунды) → секунды."""
    s = text.strip().lower().replace(" ", "")
    if not s or s == "-":
        return None
    # Чисто число — это секунды
    if s.isdigit():
        return int(s)
    # Парсим выражение типа «1d2h30m», «5m», «2h»
    total = 0
    num = ""
    for ch in s:
        if ch.isdigit() or ch == ".":
            num += ch
        elif ch == "d" and num:
            total += int(float(num) * 86400)
            num = ""
        elif ch == "h" and num:
            total += int(float(num) * 3600)
            num = ""
        elif ch == "m" and num:
            total += int(float(num) * 60)
            num = ""
        elif ch == "s" and num:
            total += int(float(num))
            num = ""
    if num:
        # Без суффикса — секунды
        try:
            total += int(num)
        except ValueError:
            return None
    return total if total > 0 else None


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
    # Шаги FSM.
    dp.message.register(step_coin, TradeForm.coin)
    dp.message.register(step_buy_exchange, TradeForm.buy_exchange)
    dp.message.register(step_sell_exchange, TradeForm.sell_exchange)
    dp.message.register(step_amount, TradeForm.amount)
    dp.message.register(step_buy_price, TradeForm.buy_price)
    dp.message.register(step_sell_price, TradeForm.sell_price)
    dp.message.register(step_buy_fee, TradeForm.buy_fee)
    dp.message.register(step_sell_fee, TradeForm.sell_fee)
    dp.message.register(step_withdrawal_fee, TradeForm.withdrawal_fee)
    dp.message.register(step_gas_fee, TradeForm.gas_fee)
    dp.message.register(step_transfer_network, TradeForm.transfer_network)
    dp.message.register(step_holding_time, TradeForm.holding_time)
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
    await state.set_state(TradeForm.buy_fee)
    await message.answer(
        "💸  Комиссия на покупку (buy_fee) в $:\n"
        "Введите число или '-' чтобы пропустить:"
    )


async def step_buy_fee(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        val = _to_decimal(text)
        if val is None or val < 0:
            await message.answer("Неверный формат. Введите число ≥ 0 или '-'.")
            return
        await state.update_data(buy_fee=str(val))
    await state.set_state(TradeForm.sell_fee)
    await message.answer(
        "💸  Комиссия на продажу (sell_fee) в $:\n"
        "Введите число или '-' чтобы пропустить:"
    )


async def step_sell_fee(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        val = _to_decimal(text)
        if val is None or val < 0:
            await message.answer("Неверный формат. Введите число ≥ 0 или '-'.")
            return
        await state.update_data(sell_fee=str(val))
    await state.set_state(TradeForm.withdrawal_fee)
    await message.answer(
        "💸  Комиссия за вывод (withdrawal_fee) в $:\n"
        "Введите число или '-' чтобы пропустить:"
    )


async def step_withdrawal_fee(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        val = _to_decimal(text)
        if val is None or val < 0:
            await message.answer("Неверный формат. Введите число ≥ 0 или '-'.")
            return
        await state.update_data(withdrawal_fee=str(val))
    await state.set_state(TradeForm.gas_fee)
    await message.answer(
        "⛽  Комиссия сети (gas_fee) в $:\n"
        "Введите число или '-' чтобы пропустить:"
    )


async def step_gas_fee(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        val = _to_decimal(text)
        if val is None or val < 0:
            await message.answer("Неверный формат. Введите число ≥ 0 или '-'.")
            return
        await state.update_data(gas_fee=str(val))
    await state.set_state(TradeForm.transfer_network)
    # Быстрые кнопки с популярными сетями
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = [
        [InlineKeyboardButton(text=n, callback_data=f"net:{n}")]
        for n in COMMON_NETWORKS[:5]
    ]
    buttons.append([InlineKeyboardButton(text="…другие", callback_data="net:more")])
    await message.answer(
        "🔗  Сеть перевода (transfer_network):\n"
        f"Популярные: {', '.join(COMMON_NETWORKS[:5])}.\n"
        "Можно нажать кнопку или ввести свою (ERC20, TRC20, TON, BTC, ...).\n"
        "'-' чтобы пропустить.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


async def step_transfer_network(
    message: Message, state: FSMContext
) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        await state.update_data(transfer_network=text)
    await state.set_state(TradeForm.holding_time)
    await message.answer(
        "⏱  Время от покупки до продажи (holding time):\n"
        "Формат: <code>5m</code> = 5 мин, <code>2h</code> = 2 ч, "
        "<code>1d3h</code> = 1 день 3 ч, или просто число секунд.\n"
        "'-' если ещё не закрыл сделку (PENDING)."
    )


async def step_holding_time(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text and text != "-":
        secs = _parse_holding_time(text)
        if secs is None or secs < 0:
            await message.answer(
                "Не понял формат. Примеры: <code>5m</code>, <code>2h</code>, "
                "<code>1d3h</code>, <code>90</code> (секунды), или '-'."
            )
            return
        await state.update_data(holding_time_seconds=secs)
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
