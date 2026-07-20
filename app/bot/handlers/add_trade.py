"""FSM-диалог и JSON-ввод для команды /add_trade.

Пошаговый режим собирает сделку из 8 шагов. JSON-режим
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


class TradeForm(StatesGroup):
    """Состояния пошагового ввода сделки."""

    coin = State()
    buy_exchange = State()
    sell_exchange = State()
    amount = State()
    buy_price = State()
    sell_price = State()
    strategy = State()
    note = State()


# ── утилиты ────────────────────────────────────────────────────────────
def _to_decimal(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


async def _send_trade(api: ApiClient, message: Message, data: dict[str, Any]) -> None:
    """Отправляет сделку в API и отвечает пользователю."""
    try:
        await api.create_trade(TradePayload.from_raw(data))
    except ApiError as exc:
        logger.warning("create_trade failed: %s", exc)
        await message.answer(f"❌ Не удалось сохранить: {exc.detail or exc}")
        return
    except Exception as exc:  # noqa: BLE001 — ловим всё на границе с внешним миром
        logger.exception("unexpected error in create_trade")
        await message.answer(f"❌ Непредвиденная ошибка: {type(exc).__name__}: {exc}")
        return
    await message.answer("✅ Сделка сохранена.")


# ── регистрация ────────────────────────────────────────────────────────
def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_add_trade, Command("add_trade"))
    # Шаги FSM. Регистрируем по state-фильтру.
    dp.message.register(step_coin, TradeForm.coin)
    dp.message.register(step_buy_exchange, TradeForm.buy_exchange)
    dp.message.register(step_sell_exchange, TradeForm.sell_exchange)
    dp.message.register(step_amount, TradeForm.amount)
    dp.message.register(step_buy_price, TradeForm.buy_price)
    dp.message.register(step_sell_price, TradeForm.sell_price)
    dp.message.register(step_strategy, TradeForm.strategy)
    dp.message.register(step_note, TradeForm.note)

    # Передаём api через ``dp.workflow_data`` — этот dict aiogram
    # прокидывает во все хендлеры. Заполняется в bot.py.
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
        # JSON-режим
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

    # Пошаговый режим
    await state.set_state(TradeForm.coin)
    await message.answer(
        "Ввод новой сделки. /cancel — отмена.\n"
        "Введите монету (например, BTC):"
    )


async def step_coin(message: Message, state: FSMContext) -> None:
    await state.update_data(coin=(message.text or "").strip())
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
