"""Текстовое форматирование ответов API.

Почему вынесено отдельно:
    * Хендлеры должны быть тонкими — получили данные, отдали текст.
    * Если завтра захочется рендерить в HTML или отдавать файл —
      меняется только этот модуль.
    * Тестировать форматирование удобнее без aiogram и httpx.

Все функции принимают распарсенный JSON (dict / list) и возвращают
обычный ``str``. Telegram умеет только ограниченную подсветку, поэтому
мы используем моноширинный ASCII-art и unicode-эмодзи как маркеры.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence


# ── утилиты ────────────────────────────────────────────────────────────
def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Any, *, signed: bool = True) -> str:
    """Форматирует число как «+12 345.67 USD» / «-8.50 USD»."""
    amount = _to_decimal(value)
    sign = ""
    if signed and amount > 0:
        sign = "+"
    # Разбиваем на группы по 3 для читаемости.
    quantized = amount.quantize(Decimal("0.01"))
    text = f"{quantized:,.2f}"
    # Python даёт «-12,345.67», нам нужно «-12 345.67» (ru-стиль).
    text = text.replace(",", " ")
    return f"{sign}{text}"


def _percent(value: Any) -> str:
    amount = _to_decimal(value)
    return f"{amount.quantize(Decimal('0.01'))}%"


def _format_holding_time(secs: int) -> str:
    """5 мин / 2 ч 15 мин / 3 д 4 ч."""
    if secs <= 0:
        return "—"
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days} д {hours} ч"
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    if minutes > 0:
        return f"{minutes} мин"
    return f"{secs} сек"


def _short(value: Any, limit: int = 32) -> str:
    text = str(value) if value is not None else ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


# ── одна сделка ────────────────────────────────────────────────────────
def format_trade(trade: Mapping[str, Any]) -> str:
    """Полная карточка сделки — для команды ``/trades_id``."""
    lines: list[str] = []
    trade_id = trade.get("id", "—")
    lines.append(f"🧾 <b>Сделка #{trade_id}</b>")
    lines.append(
        f"Монета: <b>{_short(trade.get('coin', '—'), 16)}</b>"
    )
    lines.append(
        f"{trade.get('buy_exchange', '—')} → {trade.get('sell_exchange', '—')}"
    )
    amount = _to_decimal(trade.get("amount"))
    lines.append(f"Объём: <b>{amount.normalize():f}</b>")
    buy = _to_decimal(trade.get("buy_price"))
    sell = _to_decimal(trade.get("sell_price"))
    lines.append(f"Цена: {buy.normalize():f} → {sell.normalize():f}")
    fees = _to_decimal(trade.get("buy_fee")) + _to_decimal(
        trade.get("sell_fee")
    ) + _to_decimal(trade.get("withdrawal_fee")) + _to_decimal(
        trade.get("gas_fee")
    ) + _to_decimal(trade.get("slippage"))
    if fees > 0:
        lines.append(f"💸 Комиссии: {fees.quantize(Decimal('0.01'))}")
    # Детали комиссий — если хоть одна ненулевая
    fee_parts = []
    for label, key in [
        ("покупка", "buy_fee"),
        ("продажа", "sell_fee"),
        ("вывод", "withdrawal_fee"),
        ("газ", "gas_fee"),
        ("проскальз.", "slippage"),
    ]:
        v = _to_decimal(trade.get(key))
        if v > 0:
            fee_parts.append(f"{label} {v.quantize(Decimal('0.01'))}")
    if fee_parts and len(fee_parts) > 1:
        lines.append(f"   └ {', '.join(fee_parts)}")
    # Сеть перевода
    network = trade.get("transfer_network")
    if network:
        lines.append(f"🔗 Сеть перевода: <b>{_short(network, 20)}</b>")
    # Время удержания
    holding = trade.get("holding_time_seconds")
    if holding is not None and int(holding) > 0:
        lines.append(f"⏱ Время удержания: <b>{_format_holding_time(int(holding))}</b>")
    profit = _to_decimal(trade.get("profit"))
    profit_emoji = "🟢" if profit > 0 else ("🔴" if profit < 0 else "⚪️")
    lines.append(
        f"{profit_emoji} Прибыль: <b>{_money(profit)}</b> "
        f"({_percent(trade.get('roi'))})"
    )
    lines.append(
        f"Тип: {trade.get('trade_type', '—')} · "
        f"Статус: {trade.get('status', '—')}"
    )
    if trade.get("strategy"):
        lines.append(f"Стратегия: <i>{_short(trade['strategy'], 48)}</i>")
    if trade.get("note"):
        lines.append(f"Заметка: <i>{_short(trade['note'], 96)}</i>")
    if trade.get("created_at"):
        lines.append(f"Создана: {trade['created_at']}")
    return "\n".join(lines)


def format_trade_compact(trade: Mapping[str, Any]) -> str:
    """Однострочное превью для пагинации."""
    profit = _to_decimal(trade.get("profit"))
    profit_emoji = "🟢" if profit > 0 else ("🔴" if profit < 0 else "⚪️")
    roi = _percent(trade.get("roi"))
    coin = _short(trade.get("coin", "—"), 8)
    buy = _short(trade.get("buy_exchange", "—"), 12)
    sell = _short(trade.get("sell_exchange", "—"), 12)
    # Дополнительные теги: сеть и время
    extras = []
    network = trade.get("transfer_network")
    if network:
        extras.append(_short(network, 8))
    holding = trade.get("holding_time_seconds")
    if holding is not None and int(holding) > 0:
        extras.append(_format_holding_time(int(holding)))
    extras_str = f" · {', '.join(extras)}" if extras else ""
    return (
        f"#{trade.get('id', '—')} · {coin} {buy}→{sell} · "
        f"{profit_emoji}{_money(profit)} ({roi}){extras_str}"
    )


# ── список сделок с пагинацией ─────────────────────────────────────────
PAGE_SIZE = 5


def format_trades_page(
    trades: Sequence[Mapping[str, Any]],
    *,
    page: int,
    page_size: int = PAGE_SIZE,
) -> str:
    """Форматирует страницу сделок.

    ``page`` — 0-based. Возвращает пустую строку, если список пуст.
    """
    if not trades:
        return "📭 Сделок пока нет. Добавьте первую через /add_trade."
    total = len(trades)
    start = page * page_size
    end = start + page_size
    slice_ = trades[start:end]
    if not slice_:
        return (
            f"ℹ️ Страница {page + 1} пуста. Всего сделок: {total}. "
            f"Вернитесь на /trades."
        )
    pages = (total + page_size - 1) // page_size
    lines = [f"📋 <b>Сделки</b> · стр. {page + 1}/{pages} (всего {total})"]
    lines.append("─" * 24)
    lines.extend(format_trade_compact(t) for t in slice_)
    return "\n".join(lines)


# ── общая статистика ──────────────────────────────────────────────────
def format_overall_stats(stats: Mapping[str, Any]) -> str:
    profit = _to_decimal(stats.get("total_profit"))
    profit_emoji = "🟢" if profit > 0 else ("🔴" if profit < 0 else "⚪️")
    lines = [
        "📊 <b>Общая статистика</b>",
        "─" * 24,
        f"Всего сделок: <b>{stats.get('total_trades', 0)}</b>",
        f"Завершённых: {stats.get('completed_trades', 0)}",
        f"В ожидании: {stats.get('pending_trades', 0)}",
        f"Отменено: {stats.get('cancelled_trades', 0)}",
        f"Прибыльных: {stats.get('profitable_trades', 0)}",
        f"Убыточных: {stats.get('losing_trades', 0)}",
        f"{profit_emoji} Суммарная прибыль: <b>{_money(profit)}</b>",
        f"📈 Средний ROI: {_percent(stats.get('average_roi'))}",
        f"🎯 Win-rate: {_percent(stats.get('win_rate'))}",
    ]
    return "\n".join(lines)


# ── словари статистики (по монетам / месяцам / …) ────────────────────
def format_dict_stats(
    title: str,
    stats: Mapping[str, Mapping[str, Any]],
    *,
    empty_text: str = "Нет данных.",
    top_n: int = 12,
) -> str:
    """Универсальный рендер словаря ``{ключ: {trades, profit, …}}``."""
    if not stats:
        return f"📊 <b>{title}</b>\n{empty_text}"
    # Сортируем по прибыли — самые интересные сверху.
    ordered = sorted(
        stats.items(),
        key=lambda item: _to_decimal(item[1].get("profit")),
        reverse=True,
    )
    lines = [f"📊 <b>{title}</b>", "─" * 24]
    for key, data in ordered[:top_n]:
        profit = _to_decimal(data.get("profit"))
        emoji = "🟢" if profit > 0 else ("🔴" if profit < 0 else "⚪️")
        trades = data.get("trades", 0)
        avg_roi = data.get("average_roi", "0")
        lines.append(
            f"{emoji} <b>{key}</b> · {trades} сд. · "
            f"{_money(profit)} · avgROI {_percent(avg_roi)}"
        )
    if len(ordered) > top_n:
        lines.append(
            f"<i>…и ещё {len(ordered) - top_n} "
            f"(всего {len(ordered)})</i>"
        )
    return "\n".join(lines)


# ── кривая доходности ─────────────────────────────────────────────────
def format_equity_curve(
    points: Sequence[Mapping[str, Any]],
    *,
    top_n: int = 12,
) -> str:
    if not points:
        return "📈 <b>Кривая доходности</b>\nНет данных."
    lines = ["📈 <b>Кривая доходности</b>", "─" * 24]
    tail = list(points)[-top_n:]
    for point in tail:
        date = point.get("date") or point.get("created_at") or "—"
        equity = _to_decimal(point.get("equity") or point.get("profit"))
        emoji = "🟢" if equity > 0 else ("🔴" if equity < 0 else "⚪️")
        lines.append(f"{emoji} {date} · {_money(equity)}")
    if len(points) > top_n:
        lines.append(
            f"<i>…всего точек: {len(points)}, "
            f"показаны последние {top_n}</i>"
        )
    return "\n".join(lines)
