"""Калькулятор арбитража: /calc.

Пошаговый ввод: монета, биржи, объём, цены, комиссии.
На выходе — расчёт прибыли и ROI до того, как сделка совершена.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.core.services.calculator import (
    calculate_profit,
    calculate_roi,
)
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType
from app.core.entities.trade import Trade

logger = logging.getLogger(__name__)


class CalcForm(StatesGroup):
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


def _to_decimal(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def register(dp: Dispatcher) -> None:
    dp.message.register(cmd_calc, Command("calc"))
    dp.message.register(step_coin, CalcForm.coin)
    dp.message.register(step_buy_exchange, CalcForm.buy_exchange)
    dp.message.register(step_sell_exchange, CalcForm.sell_exchange)
    dp.message.register(step_amount, CalcForm.amount)
    dp.message.register(step_buy_price, CalcForm.buy_price)
    dp.message.register(step_sell_price, CalcForm.sell_price)
    dp.message.register(step_buy_fee, CalcForm.buy_fee)
    dp.message.register(step_sell_fee, CalcForm.sell_fee)
    dp.message.register(step_withdrawal_fee, CalcForm.withdrawal_fee)
    dp.message.register(step_gas_fee, CalcForm.gas_fee)


async def cmd_calc(message: Message, state: FSMContext) -> None:
    await state.set_state(CalcForm.coin)
    await message.answer(
        "🧮  <b>Калькулятор арбитража</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Шаг 1/10</b> · Введи монету (например, BTC):\n"
        "💡 /cancel — выход в любой момент."
    )


async def step_coin(message: Message, state: FSMContext) -> None:
    await state.update_data(coin=(message.text or "").strip().upper())
    await state.set_state(CalcForm.buy_exchange)
    await message.answer(
        "<b>Шаг 2/10</b> · Биржа покупки (например, Binance):"
    )


async def step_buy_exchange(message: Message, state: FSMContext) -> None:
    await state.update_data(buy_exchange=(message.text or "").strip())
    await state.set_state(CalcForm.sell_exchange)
    await message.answer("<b>Шаг 3/10</b> · Биржа продажи:")


async def step_sell_exchange(message: Message, state: FSMContext) -> None:
    await state.update_data(sell_exchange=(message.text or "").strip())
    await state.set_state(CalcForm.amount)
    await message.answer(
        "<b>Шаг 4/10</b> · Объём (например, 0.5):"
    )


async def step_amount(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "")
    if val is None or val <= 0:
        await message.answer("Неверный формат. Введи число > 0:")
        return
    await state.update_data(amount=str(val))
    await state.set_state(CalcForm.buy_price)
    await message.answer("<b>Шаг 5/10</b> · Цена покупки:")


async def step_buy_price(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "")
    if val is None or val <= 0:
        await message.answer("Неверный формат. Введи число > 0:")
        return
    await state.update_data(buy_price=str(val))
    await state.set_state(CalcForm.sell_price)
    await message.answer("<b>Шаг 6/10</b> · Цена продажи:")


async def step_sell_price(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "")
    if val is None or val <= 0:
        await message.answer("Неверный формат. Введи число > 0:")
        return
    await state.update_data(sell_price=str(val))
    await state.set_state(CalcForm.buy_fee)
    await message.answer(
        "<b>Шаг 7/10</b> · Комиссия за покупку (или 0):"
    )


async def step_buy_fee(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "") or Decimal("0")
    await state.update_data(buy_fee=str(val))
    await state.set_state(CalcForm.sell_fee)
    await message.answer("<b>Шаг 8/10</b> · Комиссия за продажу (или 0):")


async def step_sell_fee(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "") or Decimal("0")
    await state.update_data(sell_fee=str(val))
    await state.set_state(CalcForm.withdrawal_fee)
    await message.answer(
        "<b>Шаг 9/10</b> · Комиссия за вывод (или 0):"
    )


async def step_withdrawal_fee(message: Message, state: FSMContext) -> None:
    val = _to_decimal(message.text or "") or Decimal("0")
    await state.update_data(withdrawal_fee=str(val))
    await state.set_state(CalcForm.gas_fee)
    await message.answer(
        "<b>Шаг 10/10</b> · Газ / сеть (или 0):"
    )


async def step_gas_fee(message: Message, state: FSMContext) -> None:
    gas_fee = _to_decimal(message.text or "") or Decimal("0")
    data = await state.get_data()
    data["gas_fee"] = str(gas_fee)
    # Считаем в уме, не сохраняя в БД
    try:
        trade = Trade(
            coin=data["coin"],
            buy_exchange=data["buy_exchange"],
            sell_exchange=data["sell_exchange"],
            amount=Decimal(data["amount"]),
            buy_price=Decimal(data["buy_price"]),
            sell_price=Decimal(data["sell_price"]),
            buy_fee=Decimal(data.get("buy_fee", "0")),
            sell_fee=Decimal(data.get("sell_fee", "0")),
            withdrawal_fee=Decimal(data.get("withdrawal_fee", "0")),
            gas_fee=gas_fee,
            trade_type=TradeType.CEX_CEX,
            status=TradeStatus.PENDING,
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"❌ Ошибка в расчёте: {exc}")
        await state.clear()
        return
    profit = calculate_profit(trade)
    roi = calculate_roi(trade)
    investment = trade.investment
    revenue = trade.revenue
    total_fees = trade.total_fees
    sign = "🟢" if profit > 0 else ("🔴" if profit < 0 else "⚪️")
    await message.answer(
        f"🧮  <b>Результат расчёта</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💼  <b>{trade.coin}</b> · {trade.buy_exchange} → {trade.sell_exchange}\n"
        f"📊  Объём: <b>{trade.amount.normalize():f}</b>\n"
        f"💵  Куплено по: <b>{trade.buy_price.normalize():f}</b>\n"
        f"💰  Продано по: <b>{trade.sell_price.normalize():f}</b>\n\n"
        f"📈  Инвестиция:  <b>{investment.quantize(Decimal('0.01'))}</b>\n"
        f"📈  Выручка:     <b>{revenue.quantize(Decimal('0.01'))}</b>\n"
        f"📉  Комиссии:    <b>{total_fees.quantize(Decimal('0.01'))}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{sign}  <b>Прибыль:  {profit.quantize(Decimal('0.01'))}</b>\n"
        f"{sign}  <b>ROI:      {roi.quantize(Decimal('0.01'))}%</b>\n"
        f"💵  Чистый P/L на единицу: <b>"
        f"{(trade.sell_price - trade.buy_price).quantize(Decimal('0.01'))}</b>\n\n"
        "💡 <i>Это только расчёт. Сделка в базу не добавлена.</i>"
    )
    await state.clear()
