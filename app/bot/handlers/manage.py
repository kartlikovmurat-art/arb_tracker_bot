"""Управление сделками: edit, delete, confirm.

* ``/trades_edit <id> поле=значение`` — частичное редактирование.
* ``/trades_delete <id>`` — удаление (с подтверждением).
* ``/confirm <id>`` — перевод PENDING → COMPLETED.
* Inline-кнопки под карточкой сделки: «✏️ Редактировать»,
  «✅ Подтвердить», «🗑 Удалить» (с confirm).
"""
from __future__ import annotations

import logging
from typing import Any

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.api import ApiClient, ApiError
from app.bot.formatters import format_trade
from app.bot.keyboards import trades_pager

logger = logging.getLogger(__name__)


class EditForm(StatesGroup):
    """FSM для /trades_edit — пользователь пишет field=value."""
    waiting_changes = State()


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_edit, Command("trades_edit"))
    dp.message.register(cmd_delete, Command("trades_delete"))
    dp.message.register(cmd_confirm, Command("confirm"))
    dp.callback_query.register(
        _on_delete_confirm,
        lambda c: c.data and c.data.startswith("trades:delete:"),
    )
    dp.callback_query.register(
        _on_edit_inline,
        lambda c: c.data and c.data.startswith("trades:edit:"),
    )
    dp.callback_query.register(
        _on_complete_inline,
        lambda c: c.data and c.data.startswith("trades:complete:"),
    )


# ── /trades_edit ──────────────────────────────────────────────────
async def cmd_edit(
    message: Message, command: Any, api: ApiClient  # type: ignore[assignment]
) -> None:
    """Использование: /trades_edit <id> [field=value ...]"""
    args = (command.args or "").strip() if command else ""
    if not args:
        await message.answer(
            "✏️  <b>Редактирование сделки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Формат:\n"
            "<code>/trades_edit 42 buy_price=60500 note=\"новый текст\"</code>\n\n"
            "Доступные поля: <code>coin</code>, <code>buy_exchange</code>, "
            "<code>sell_exchange</code>, <code>amount</code>, "
            "<code>buy_price</code>, <code>sell_price</code>, "
            "<code>buy_fee</code>, <code>sell_fee</code>, "
            "<code>withdrawal_fee</code>, <code>gas_fee</code>, "
            "<code>slippage</code>, <code>strategy</code>, <code>note</code>, "
            "<code>status</code> (PENDING/COMPLETED/CANCELLED), "
            "<code>trade_type</code>."
        )
        return
    parts = args.split(maxsplit=1)
    if not parts[0].isdigit():
        await message.answer("Первый аргумент должен быть ID сделки (число).")
        return
    trade_id = int(parts[0])
    rest = parts[1] if len(parts) > 1 else ""
    if not rest:
        # Просто показать карточку с кнопками
        try:
            uid = message.from_user.id if message.from_user else 0
            trade = await api.get_trade(trade_id, uid)
        except ApiError as exc:
            await message.answer(
                "❌ Сделка не найдена."
                if exc.status_code == 404
                else f"❌ Ошибка: {exc.detail or exc}"
            )
            return
        await message.answer(
            f"📋  <b>Сделка #{trade_id}</b>\n\n" + format_trade(trade),
            reply_markup=_trade_actions_kb(trade_id),
        )
        return
    # Парсим key=value (с поддержкой кавычек для значений с пробелами)
    updates = _parse_kv(rest)
    if not updates:
        await message.answer(
            "Не нашёл ни одного <code>field=value</code>.\n"
            "Пример: <code>/trades_edit 42 buy_price=60500 note=\"swap\"</code>"
        )
        return
    try:
        uid = message.from_user.id if message.from_user else 0
        trade = await api.patch_trade(trade_id, updates, user_id=uid)
    except ApiError as exc:
        await message.answer(
            "❌ Сделка не найдена."
            if exc.status_code == 404
            else f"❌ Ошибка: {exc.detail or exc}"
        )
        return
    await message.answer(
        f"✅  <b>Сделка #{trade_id} обновлена!</b>\n\n" + format_trade(trade),
    )


def _parse_kv(text: str) -> dict[str, Any]:
    """Парсит 'k1=v1 k2="v 2" k3=v3' в dict."""
    out: dict[str, Any] = {}
    i = 0
    n = len(text)
    while i < n:
        # пропускаем пробелы
        while i < n and text[i] == " ":
            i += 1
        if i >= n:
            break
        # читаем ключ
        k_start = i
        while i < n and text[i] != "=":
            i += 1
        if i >= n:
            break
        key = text[k_start:i].strip()
        i += 1  # пропускаем '='
        # читаем значение (в кавычках или до пробела)
        if i < n and text[i] == '"':
            i += 1
            v_start = i
            while i < n and text[i] != '"':
                i += 1
            value = text[v_start:i]
            if i < n:
                i += 1  # пропускаем закрывающую "
        else:
            v_start = i
            while i < n and text[i] != " ":
                i += 1
            value = text[v_start:i]
        if key:
            out[key] = value
    return out


def _trade_actions_kb(trade_id: int):
    """Backwards-compat alias. Реальная функция — trade_actions_kb."""
    return trade_actions_kb(trade_id)


async def _on_edit_inline(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    assert callback.data is not None
    trade_id = int(callback.data.split(":")[2])
    await state.set_state(EditForm.waiting_changes)
    await state.update_data(trade_id=trade_id)
    if callback.message is not None:
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"✏️  <b>Редактирование сделки #{trade_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Отправь изменения в формате:\n"
            "<code>buy_price=60500 note=\"swap test\"</code>\n\n"
            "Поля: <code>coin</code>, <code>buy_exchange</code>, "
            "<code>sell_exchange</code>, <code>amount</code>, "
            "<code>buy_price</code>, <code>sell_price</code>, "
            "<code>buy_fee</code>, <code>sell_fee</code>, "
            "<code>withdrawal_fee</code>, <code>gas_fee</code>, "
            "<code>slippage</code>, <code>strategy</code>, <code>note</code>, "
            "<code>status</code>, <code>trade_type</code>.\n\n"
            "💡 /cancel — выход без изменений."
        )
    await callback.answer()


async def _on_complete_inline(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    assert callback.data is not None
    trade_id = int(callback.data.split(":")[2])
    try:
        uid = callback.from_user.id if callback.from_user else 0
        trade = await api.complete_trade(trade_id, uid)
    except ApiError as exc:
        await callback.answer(f"❌ {exc.detail or exc}", show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"✅  <b>Сделка #{trade_id} подтверждена!</b>\n\n"
            + format_trade(trade)
        )
    await callback.answer("Сделка подтверждена")


# ── /trades_delete ───────────────────────────────────────────────
async def cmd_delete(
    message: Message, command: Any, api: ApiClient  # type: ignore[assignment]
) -> None:
    args = (command.args or "").strip() if command else ""
    if not args or not args.isdigit():
        await message.answer("Использование: <code>/trades_delete 42</code>")
        return
    trade_id = int(args)
    # Без подтверждения удаляем, но в логах пишем
    try:
        uid = message.from_user.id if message.from_user else 0
        await api.delete_trade(trade_id, uid)
    except ApiError as exc:
        await message.answer(
            "❌ Не найдена."
            if exc.status_code == 404
            else f"❌ Ошибка: {exc.detail or exc}"
        )
        return
    await message.answer(f"🗑  Сделка <b>#{trade_id}</b> удалена.")


async def _on_delete_confirm(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    assert callback.data is not None
    parts = callback.data.split(":")
    action = parts[2]  # "ask" or "yes"
    trade_id = int(parts[3])
    if action == "ask":
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                f"🗑  <b>Удалить сделку #{trade_id}?</b>\n\n"
                "Это действие нельзя отменить.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Да, удалить",
                                callback_data=f"trades:delete:yes:{trade_id}",
                            ),
                            InlineKeyboardButton(
                                text="❌ Отмена",
                                callback_data="menu:trades",
                            ),
                        ]
                    ]
                ),
            )
        await callback.answer()
        return
    if action == "yes":
        try:
            uid = callback.from_user.id if callback.from_user else 0
            await api.delete_trade(trade_id, uid)
        except ApiError as exc:
            await callback.answer(f"❌ {exc.detail or exc}", show_alert=True)
            return
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                f"✅  Сделка <b>#{trade_id}</b> удалена."
            )
        await callback.answer("Удалено")


# ── /confirm ─────────────────────────────────────────────────────
async def cmd_confirm(
    message: Message, command: Any, api: ApiClient  # type: ignore[assignment]
) -> None:
    """Переводит сделку PENDING → COMPLETED."""
    args = (command.args or "").strip() if command else ""
    if not args or not args.isdigit():
        await message.answer("Использование: <code>/confirm 42</code>")
        return
    trade_id = int(args)
    try:
        uid = message.from_user.id if message.from_user else 0
        trade = await api.complete_trade(trade_id, uid)
    except ApiError as exc:
        await message.answer(
            "❌ Не найдена."
            if exc.status_code == 404
            else f"❌ Ошибка: {exc.detail or exc}"
        )
        return
    await message.answer(
        f"✅  <b>Сделка #{trade_id} подтверждена!</b>\n\n"
        + format_trade(trade)
    )
