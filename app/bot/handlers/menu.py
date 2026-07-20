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
from aiogram.types import BufferedInputFile, CallbackQuery

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
    BTN_ADD,
    BTN_ANALYTICS,
    BTN_BACKUP,
    BTN_CALC,
    BTN_EXPORT,
    BTN_GOAL,
    BTN_HELP,
    BTN_LAST,
    BTN_STATS,
    BTN_TODAY,
    BTN_TRADES,
    BTN_WEEK,
    add_trade_menu,
    analytics_menu,
    main_menu,
    trades_pager,
)
from app.bot.keyboards.reply import main_reply_keyboard

logger = logging.getLogger(__name__)


# Словарь «текст кнопки → имя действия». Используется в
# ``reply_menu_router`` ниже: когда пользователь жмёт reply-кнопку,
# Telegram отправляет боту message с текстом этой кнопки.
REPLY_MENU_ACTIONS: dict[str, str] = {
    BTN_ADD: "add",
    BTN_TRADES: "trades",
    BTN_LAST: "last",
    BTN_TODAY: "today",
    BTN_WEEK: "week",
    BTN_STATS: "stats",
    BTN_ANALYTICS: "analytics",
    BTN_GOAL: "goal",
    BTN_CALC: "calc",
    BTN_EXPORT: "export",
    BTN_BACKUP: "backup",
    BTN_HELP: "help",
}


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

    # Постоянная панель снизу экрана: ловим нажатия reply-кнопок
    # по тексту сообщения. Регистрируем ОДИН хендлер на все тексты
    # из REPLY_MENU_ACTIONS — внутри он роутит по словарю.
    dp.message.register(
        reply_menu_router,
        lambda m: (m.text or "") in REPLY_MENU_ACTIONS,
    )


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


# ── Reply-клавиатура (постоянная панель снизу) ─────────────────────
async def reply_menu_router(
    message: Message,
    state: FSMContext,
    api: ApiClient,  # type: ignore[assignment]
) -> None:
    """Ловит нажатия reply-кнопок и роутит их к нужному действию.

    Отличие от callback-handler'ов: reply-кнопка отправляет боту
    обычный message с текстом кнопки. Поэтому:
      * нельзя edit_text (сообщение новое) — используем answer()
      * клавиатура снизу остаётся (мы её и так уже показали)
      * inline-кнопки в сообщении используются для подменю
    """
    if message.text is None:
        return
    action = REPLY_MENU_ACTIONS.get(message.text)
    if action is None:
        return
    # После клика по reply-кнопке сразу очищаем чат-буфер —
    # чтобы старое сообщение с inline-кнопками не висело. Но
    # edit'ить reply-message нельзя, поэтому просто шлём новое.
    try:
        if action == "add":
            await message.answer(
                "➕  <b>Добавить сделку</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Выбери способ:\n"
                "  📝  <b>Пошаговый</b> — бот спросит всё по очереди.\n"
                "  ⚡  <b>JSON</b> — одной строкой (для интеграций).",
                reply_markup=add_trade_menu(),
            )
        elif action == "trades":
            try:
                trades = await api.list_trades()
            except ApiError as exc:
                await message.answer(f"❌ Не удалось получить сделки: {exc.detail or exc}")
                return
            text, keyboard = build_trades_view(trades, page=0)
            await message.answer(
                text,
                reply_markup=keyboard or main_menu(),
            )
        elif action == "stats":
            try:
                data = await api.overall_stats()
            except ApiError as exc:
                await message.answer(f"❌ Ошибка: {exc.detail or exc}")
                return
            await message.answer(
                format_overall_stats(data),
                reply_markup=main_menu(),
            )
        elif action == "analytics":
            await message.answer(
                "📈  <b>Аналитика</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Разрезы по твоей истории:",
                reply_markup=analytics_menu(),
            )
        elif action == "export":
            await message.answer("⏳ Готовлю Excel-выгрузку…")
            try:
                data = await api.export_excel()
            except ApiError as exc:
                await message.answer(f"❌ Не удалось выгрузить: {exc.detail or exc}")
                return
            if not data:
                await message.answer(
                    "ℹ️  Выгрузка пуста — сделок пока нет.\n"
                    "Добавь первую через ➕ в меню."
                )
                return
            filename = f"trades_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            document = BufferedInputFile(data, filename=filename)
            await message.answer_document(
                document=document,
                caption=(
                    f"📤  <b>Экспорт готов!</b>\n"
                    f"📎  {filename}\n"
                    f"📦  {len(data)} байт"
                ),
            )
        elif action == "help":
            from app.bot.handlers.help_text import HELP_TEXT
            await message.answer(HELP_TEXT, reply_markup=main_menu())
        elif action == "last":
            try:
                trades = await api.list_trades()
            except ApiError as exc:
                await message.answer(f"❌ {exc.detail or exc}")
                return
            if not trades:
                await message.answer("ℹ️ Сделок пока нет.")
                return
            from app.bot.formatters import format_trade
            last = max(trades, key=lambda t: t.get("created_at", ""))
            await message.answer(
                "🕐  <b>Последняя сделка</b>\n\n" + format_trade(last),
                reply_markup=main_menu(),
            )
        elif action == "today":
            from datetime import datetime, timedelta, timezone
            try:
                trades = await api.list_trades()
            except ApiError as exc:
                await message.answer(f"❌ {exc.detail or exc}")
                return
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            today = []
            for t in trades:
                try:
                    created = datetime.fromisoformat(
                        str(t.get("created_at", "")).replace("Z", "+00:00")
                    )
                    if created >= cutoff:
                        today.append(t)
                except Exception:  # noqa: BLE001
                    continue
            if not today:
                await message.answer("📅  Сегодня сделок не было.")
                return
            text, keyboard = build_trades_view(today, page=0)
            await message.answer(
                f"📅  <b>Сделки за сегодня</b> · {len(today)} шт.\n\n" + text,
                reply_markup=keyboard or main_menu(),
            )
        elif action == "week":
            from datetime import datetime, timedelta, timezone
            try:
                trades = await api.list_trades()
            except ApiError as exc:
                await message.answer(f"❌ {exc.detail or exc}")
                return
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            week = []
            for t in trades:
                try:
                    created = datetime.fromisoformat(
                        str(t.get("created_at", "")).replace("Z", "+00:00")
                    )
                    if created >= cutoff:
                        week.append(t)
                except Exception:  # noqa: BLE001
                    continue
            if not week:
                await message.answer("📆  За неделю сделок не было.")
                return
            text, keyboard = build_trades_view(week, page=0)
            await message.answer(
                f"📆  <b>Сделки за неделю</b> · {len(week)} шт.\n\n" + text,
                reply_markup=keyboard or main_menu(),
            )
        elif action == "goal":
            # Прогресс к цели — перенаправляем в extras.cmd_goal
            from app.bot.handlers.extras import cmd_goal as _goal_handler
            from aiogram.types import Message as _Msg
            fake = type("F", (), {"text": "/goal", "answer": message.answer})()
            await _goal_handler(fake, _CommandLike(args=""), api)
        elif action == "calc":
            await message.answer(
                "🧮  <b>Калькулятор</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Отправь <code>/calc</code> — бот попросит параметры по очереди."
            )
        elif action == "backup":
            await message.answer("⏳ Готовлю бэкап…")
            try:
                data = await api.backup_json()
            except ApiError as exc:
                await message.answer(f"❌ {exc.detail or exc}")
                return
            if not data:
                await message.answer("ℹ️ База пуста.")
                return
            from datetime import datetime
            from aiogram.types import BufferedInputFile
            filename = f"trades_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            document = BufferedInputFile(data, filename=filename)
            await message.answer_document(
                document=document,
                caption=f"💾  <b>Бэкап готов!</b>\n{len(data)} байт",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("reply_menu_router error")
        await message.answer(f"❌ Непредвиденная ошибка: {type(exc).__name__}: {exc}")


class _CommandLike:
    def __init__(self, args: str = "") -> None:
        self.args = args

