"""Тесты для текстовых форматтеров.

Покрывают самые важные сценарии:
    * положительная / отрицательная / нулевая прибыль;
    * пустые данные;
    * большое число (группировка разрядов);
    * отсутствие полей в trade.
"""
from __future__ import annotations

from app.bot.formatters import (
    format_dict_stats,
    format_equity_curve,
    format_overall_stats,
    format_trade,
    format_trade_compact,
    format_trades_page,
)
from app.bot.formatters.text import PAGE_SIZE


def _sample_trade(**overrides):
    base = {
        "id": 7,
        "coin": "ETH",
        "buy_exchange": "Binance",
        "sell_exchange": "OKX",
        "amount": "1.25",
        "buy_price": "3000",
        "sell_price": "3050",
        "profit": "62.5",
        "roi": "2.08",
        "trade_type": "CEX_CEX",
        "status": "COMPLETED",
        "created_at": "2025-01-15T10:00:00",
        "strategy": "spread-hunter",
        "note": "first deal of the year",
    }
    base.update(overrides)
    return base


def test_format_trade_profit_positive() -> None:
    text = format_trade(_sample_trade(profit="100.50"))
    assert "#7" in text
    assert "ETH" in text
    assert "Binance" in text
    assert "OKX" in text
    assert "+100.50" in text
    assert "🟢" in text


def test_format_trade_profit_negative() -> None:
    text = format_trade(_sample_trade(profit="-12.34"))
    assert "🔴" in text
    assert "-12.34" in text


def test_format_trade_profit_zero() -> None:
    text = format_trade(_sample_trade(profit="0"))
    assert "⚪️" in text
    assert "+0.00" not in text
    assert "0.00" in text


def test_format_trade_missing_optional_fields() -> None:
    trade = _sample_trade()
    trade.pop("strategy")
    trade.pop("note")
    text = format_trade(trade)
    assert "Стратегия" not in text
    assert "Заметка" not in text


def test_format_trade_compact_short() -> None:
    text = format_trade_compact(_sample_trade())
    assert text.startswith("#7")
    assert "ETH" in text


def test_format_trades_page_empty() -> None:
    text = format_trades_page([], page=0)
    assert "Сделок пока нет" in text


def test_format_trades_page_paginates() -> None:
    trades = [_sample_trade(id=i) for i in range(1, 13)]
    page1 = format_trades_page(trades, page=0, page_size=PAGE_SIZE)
    page3 = format_trades_page(trades, page=2, page_size=PAGE_SIZE)
    assert "1/3" in page1
    assert "3/3" in page3
    # На странице 5 строк-сделок плюс шапка с «📋 …». Считаем сделки
    # по количеству символов # в строках превью (5 штук на странице).
    preview_lines = [
        line for line in page1.splitlines()
        if line.startswith("#") and " · " in line
    ]
    assert len(preview_lines) == PAGE_SIZE
    assert "пуста" in format_trades_page(trades, page=99, page_size=PAGE_SIZE)


def test_format_overall_stats_currency_grouping() -> None:
    text = format_overall_stats(
        {
            "total_trades": 1000,
            "completed_trades": 900,
            "pending_trades": 50,
            "cancelled_trades": 50,
            "profitable_trades": 700,
            "losing_trades": 200,
            "total_profit": "1234567.89",
            "average_roi": "2.5",
            "win_rate": "77.77",
        }
    )
    # ru-style группировка: пробел, а не запятая.
    assert "1 234 567.89" in text
    assert "1000" in text


def test_format_dict_stats_orders_by_profit() -> None:
    stats = {
        "BTC": {"trades": 5, "profit": "-10", "average_roi": "-0.5"},
        "ETH": {"trades": 8, "profit": "500", "average_roi": "3.0"},
        "SOL": {"trades": 3, "profit": "100", "average_roi": "1.0"},
    }
    text = format_dict_stats("Top", stats)
    # ETH идёт первой (profit 500), потом SOL (100), потом BTC (-10).
    eth_pos = text.find("ETH")
    sol_pos = text.find("SOL")
    btc_pos = text.find("BTC")
    assert eth_pos < sol_pos < btc_pos


def test_format_dict_stats_empty() -> None:
    text = format_dict_stats("Empty", {})
    assert "Нет данных" in text


def test_format_equity_curve_empty() -> None:
    text = format_equity_curve([])
    assert "Нет данных" in text


def test_format_equity_curve_truncates_to_top_n() -> None:
    points = [
        {"date": f"2025-01-{i:02d}", "equity": str(i * 10)} for i in range(1, 30)
    ]
    text = format_equity_curve(points, top_n=5)
    assert "всего точек: 29" in text
    assert "2025-01-29" in text
    assert "2025-01-01" not in text
