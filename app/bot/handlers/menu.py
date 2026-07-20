"""Обработчики callback'ов от кнопок главного меню.

Один файл на все menu:* callback'и, чтобы:
  * не плодить кучу мелких модулей;
  * удобно тестировать (одна точка входа);
  * легко добавлять новые кнопки (просто +handler и +keyboard).
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.api import ApiClient, ApiError
from app.bot.formatters import (
    format_dict_stats,
    format_equity_curve,
    format_overall_stats,
    format_trades_page,
)
from app.bot.handlers._pagination_view import build_trades_view
from app.bot.handlers.add_trade import TradeForm
from app.bot.handlers.help_text import HELP_TEXT
from app.bot.keyboards import (
    add_trade_menu,
    analytics_menu,
    main_menu,
    trades_pager,
)

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api: ApiClient) -> None:
    """Подключает все callback'и menu:* к диспетчеру."""
    handlers: list[tuple[str, Callable[..., Awaitable[Any]]]] = [
        ("menu:add", _on_add),
        ("menu:trades", _on_trades),
        ("menu:stats", _on_stats),
        ("menu:analytics", _on_analytics),
        ("menu:export", _on_export),
        ("menu:month", _on_month),
        ("menu:daily", _on_daily),
        ("menu:coin", _on_coin),
        ("menu:exchange", _on_exchange),
        ("menu:strategy", _on_strategy),
        ("menu:equity", _on_equity),
        ("menu:add_step", _on_add_step),
        ("menu:add_json", _on_add_json),
    ]
    for data, handler in handlers:
        dp.callback_query.register(handler, lambda c, d=data: c.data == d)


# ── helpers ──────────────────────────────────────────────────────────
async def _safe_edit(
    callback: CallbackQuery,
    text: str,
    *,
    reply_markup: Any = None,
) -> None:
    """edit_text с запасом — если нельзя edit (старое сообщение), шлёт новое."""
    try:
        if callback.message is not None:
            await callback.message.edit_text(  # type: ignore[union-attr]
                text, reply_markup=reply_markup
            )
    except Exception:  # noqa: BLE001
        if callback.message is not None:
            await callback.message.answer(  # type: ignore[union-attr]
                text, reply_markup=reply_markup
            )
    await callback.answer()


async def _fetch(
    callback: CallbackQuery,
    coro_factory: Callable[[], Awaitable[Any]],
    *,
    on_error: str = "Ошибка",
) -> Any:
    """Запускает запрос к API; на ошибку показывает алерт и возвращает None."""
    try:
        return await coro_factory()
    except ApiError as exc:
        await callback.answer(f"❌ {on_error}: {exc.detail or exc}", show_alert=True)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("unexpected error in menu handler")
        await callback.answer(
            f"❌ Непредвиденная ошибка: {type(exc).__name__}",
            show_alert=True,
        )
        return None


# ── хендлеры ────────────────────────────────────────────────────────
async def _on_add(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    await _safe_edit(
        callback,
        "➕  <b>Добавить сделку</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выбери способ:\n"
        "  📝  <b>Пошаговый</b> — бот спросит всё по очереди.\n"
        "  ⚡  <b>JSON</b> — одной строкой (для интеграций).",
        reply_markup=add_trade_menu(),
    )


async def _on_add_step(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    await state.set_state(TradeForm.coin)
    if callback.message is not None:
        await callback.message.answer(  # type: ignore[union-attr]
            "📝  <b>Пошаговый ввод сделки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Шаг 1/8</b> · Введи монету (например, <code>BTC</code>):\n"
            "💡 /cancel — отмена в любой момент."
        )
    await callback.answer()


async def _on_add_json(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    if callback.message is not None:
        await callback.message.answer(  # type: ignore[union-attr]
            "⚡  <b>JSON-ввод сделки</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Отправь одной строкой:\n"
            "<code>/add_trade {\"coin\":\"BTC\",\"buy_exchange\":\"Binance\","
            "\"sell_exchange\":\"Bybit\",\"amount\":\"0.1\","
            "\"buy_price\":\"60000\",\"sell_price\":\"60500\","
            "\"trade_type\":\"CEX_CEX\",\"status\":\"COMPLETED\"}</code>"
        )
    await callback.answer()


async def _on_trades(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    trades = await _fetch(callback, api.list_trades, on_error="Не удалось получить сделки")
    if trades is None:
        return
    text, keyboard = build_trades_view(trades, page=0)
    await _safe_edit(callback, text, reply_markup=keyboard or main_menu())


async def _on_stats(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    data = await _fetch(callback, api.overall_stats, on_error="Ошибка статистики")
    if data is None:
        return
    await _safe_edit(
        callback,
        format_overall_stats(data),
        reply_markup=main_menu(),
    )


async def _on_analytics(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    await _safe_edit(
        callback,
        "📈  <b>Аналитика</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Разрезы по твоей истории:",
        reply_markup=analytics_menu(),
    )


async def _on_export(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    await callback.answer("⏳ Готовлю выгрузку…")
    data = await _fetch(callback, api.export_excel, on_error="Не удалось выгрузить")
    if data is None:
        return
    if not data:
        if callback.message is not None:
            await callback.message.answer(  # type: ignore[union-attr]
                "ℹ️  Выгрузка пуста — сделок пока нет.\n"
                "Добавь первую через ➕ в меню."
            )
        return
    filename = f"trades_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    document = io.BytesIO(data)
    document.name = filename
    if callback.message is not None:
        await callback.message.answer_document(  # type: ignore[union-attr]
            document=document,
            caption=(
                f"📤  <b>Экспорт готов!</b>\n"
                f"📎  {filename}\n"
                f"📦  {len(data)} байт"
            ),
        )
    await callback.answer("✅ Отправлено!")


async def _on_month(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    data = await _fetch(callback, api.monthly_stats, on_error="Ошибка")
    if data is None:
        return
    await _safe_edit(
        callback,
        format_dict_stats("По месяцам", data),
        reply_markup=analytics_menu(),
    )


async def _on_daily(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    data = await _fetch(callback, api.daily_stats, on_error="Ошибка")
    if data is None:
        return
    await _safe_edit(
        callback,
        format_dict_stats("По дням", data, top_n=20),
        reply_markup=analytics_menu(),
    )


async def _on_coin(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    data = await _fetch(callback, api.coin_stats, on_error="Ошибка")
    if data is None:
        return
    await _safe_edit(
        callback,
        format_dict_stats("По монетам", data),
        reply_markup=analytics_menu(),
    )


async def _on_exchange(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    data = await _fetch(callback, api.exchange_stats, on_error="Ошибка")
    if data is None:
        return
    await _safe_edit(
        callback,
        format_dict_stats("По биржам", data),
        reply_markup=analytics_menu(),
    )


async def _on_strategy(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    data = await _fetch(callback, api.strategy_stats, on_error="Ошибка")
    if data is None:
        return
    await _safe_edit(
        callback,
        format_dict_stats("По стратегиям", data),
        reply_markup=analytics_menu(),
    )


async def _on_equity(
    callback: CallbackQuery, state: FSMContext, api: ApiClient  # type: ignore[assignment]
) -> None:
    data = await _fetch(callback, api.equity_curve, on_error="Ошибка")
    if data is None:
        return
    await _safe_edit(
        callback,
        format_equity_curve(data),
        reply_markup=analytics_menu(),
    )
