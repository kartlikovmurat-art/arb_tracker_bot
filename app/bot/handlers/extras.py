"""Дополнительные команды: /equity_chart, /search, /goal, /last, /today, /week."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.api import ApiClient, ApiError
from app.bot.formatters import format_trade, format_trades_page
from app.bot.handlers._pagination_view import build_trades_view
from app.bot.keyboards import main_menu, trades_pager

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_equity_chart, Command("equity_chart"))
    dp.message.register(cmd_search, Command("search"))
    dp.message.register(cmd_goal, Command("goal"))
    dp.message.register(cmd_last, Command("last"))
    dp.message.register(cmd_today, Command("today"))
    dp.message.register(cmd_week, Command("week"))


# ── /equity_chart ───────────────────────────────────────────────
async def cmd_equity_chart(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    await message.answer("⏳ Рисую график…")
    try:
        blob = await api.equity_chart()
    except ApiError as exc:
        await message.answer(f"❌ Не удалось: {exc.detail or exc}")
        return
    if not blob:
        await message.answer("ℹ️ Сделок пока нет — график пустой.")
        return
    from aiogram.types import BufferedInputFile
    document = BufferedInputFile(blob, filename="equity_curve.png")
    await message.answer_photo(
        photo=document,
        caption=(
            "📈  <b>Equity Curve</b>\n"
            "Кумулятивный P/L по датам."
        ),
        reply_markup=main_menu(),
    )


# ── /search ──────────────────────────────────────────────────────
async def cmd_search(message: Message, command: Any, api: ApiClient) -> None:  # type: ignore[assignment]
    args = (command.args or "").strip() if command else ""
    if not args:
        await message.answer(
            "🔎  <b>Поиск сделок</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ищет по монете, бирже, стратегии, заметке.\n"
            "Формат: <code>/search BTC</code>"
        )
        return
    try:
        results = await api.search_trades(args)
    except ApiError as exc:
        await message.answer(f"❌ {exc.detail or exc}")
        return
    if not results:
        await message.answer(
            f"🔎  По запросу <b>{args!r}</b> ничего не нашлось."
        )
        return
    text, keyboard = build_trades_view(results, page=0)
    await message.answer(
        f"🔎  Найдено: <b>{len(results)}</b>\n\n" + text,
        reply_markup=keyboard or main_menu(),
    )


# ── /goal ────────────────────────────────────────────────────────
_GOAL_FILE = Path("/workspace/arb_tracker_bot1_full/.goal.json")


def _load_goal() -> dict:
    if _GOAL_FILE.exists():
        try:
            return json.loads(_GOAL_FILE.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save_goal(data: dict) -> None:
    _GOAL_FILE.write_text(json.dumps(data, indent=2))


async def cmd_goal(message: Message, command: Any, api: ApiClient) -> None:  # type: ignore[assignment]
    args = (command.args or "").strip() if command else ""
    goal = _load_goal()
    if not args:
        # Показать текущий прогресс
        target = goal.get("amount", 0)
        if target <= 0:
            await message.answer(
                "🎯  <b>Цель по прибыли</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Цель не установлена.\n"
                "Поставь: <code>/goal 1000</code>"
            )
            return
        try:
            stats = await api.overall_stats()
        except ApiError as exc:
            await message.answer(f"❌ {exc.detail or exc}")
            return
        current = float(stats.get("total_profit", 0))
        pct = min(100, current / target * 100) if target else 0
        bar_filled = int(pct // 5)
        bar_empty = 20 - bar_filled
        bar = "🟩" * bar_filled + "⬜" * bar_empty
        await message.answer(
            f"🎯  <b>Прогресс к цели</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯  Цель: <b>{target:.2f}</b>\n"
            f"💰  Текущая прибыль: <b>{current:.2f}</b>\n"
            f"📊  Прогресс: <b>{pct:.1f}%</b>\n\n"
            f"{bar}\n\n"
            f"{'✅ Цель достигнута!' if pct >= 100 else f'⏳  Осталось: {target - current:.2f}'}",
            reply_markup=main_menu(),
        )
        return
    # Поставить цель
    try:
        amount = float(args.replace(",", "."))
    except ValueError:
        await message.answer("Введи число: <code>/goal 1000</code>")
        return
    _save_goal({"amount": amount, "set_at": datetime.utcnow().isoformat() + "Z"})
    await message.answer(
        f"🎯  <b>Цель установлена!</b>\n"
        f"💰  Цель: <b>{amount:.2f}</b>\n\n"
        f"💡  Проверить прогресс: /goal"
    )


# ── /last ────────────────────────────────────────────────────────
async def cmd_last(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        trades = await api.list_trades()
    except ApiError as exc:
        await message.answer(f"❌ {exc.detail or exc}")
        return
    if not trades:
        await message.answer("ℹ️ Сделок пока нет.")
        return
    last = max(trades, key=lambda t: t.get("created_at", ""))
    await message.answer(
        "🕐  <b>Последняя сделка</b>\n\n" + format_trade(last),
        reply_markup=main_menu(),
    )


# ── /today и /week ───────────────────────────────────────────────
async def _filter_by_period(
    trades: list[dict], days: int
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for t in trades:
        try:
            created = datetime.fromisoformat(
                str(t.get("created_at", "")).replace("Z", "+00:00")
            )
        except Exception:  # noqa: BLE001
            continue
        if created >= cutoff:
            out.append(t)
    return out


async def cmd_today(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        trades = await api.list_trades()
    except ApiError as exc:
        await message.answer(f"❌ {exc.detail or exc}")
        return
    today = _filter_by_period(trades, 1)
    if not today:
        await message.answer("📅  Сегодня сделок не было.")
        return
    text, keyboard = build_trades_view(today, page=0)
    await message.answer(
        f"📅  <b>Сделки за сегодня</b> · {len(today)} шт.\n\n" + text,
        reply_markup=keyboard or main_menu(),
    )


async def cmd_week(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    try:
        trades = await api.list_trades()
    except ApiError as exc:
        await message.answer(f"❌ {exc.detail or exc}")
        return
    week = _filter_by_period(trades, 7)
    if not week:
        await message.answer("📅  За последние 7 дней сделок не было.")
        return
    text, keyboard = build_trades_view(week, page=0)
    await message.answer(
        f"📅  <b>Сделки за неделю</b> · {len(week)} шт.\n\n" + text,
        reply_markup=keyboard or main_menu(),
    )
