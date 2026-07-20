"""Тесты для хендлеров бота на уровне callback'ов.

Используем ``aiogram`` unittest-утилиты и ``respx`` для мока
HTTP. Не поднимаем реальный Telegram — это unit-тесты хендлеров.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx

from app.bot.api import ApiClient
from app.bot.handlers import _pagination_view
from app.bot.handlers.pagination import _on_pager
from app.bot.handlers.view import cmd_trades_id


def _make_callback(data: str) -> Any:
    cb = MagicMock()
    cb.data = data
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    return cb


def _make_message() -> Any:
    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.text = None
    return msg


async def test_build_trades_view_no_pager_for_single_page() -> None:
    trades = [{"id": i, "coin": "BTC", "buy_exchange": "A", "sell_exchange": "B",
               "amount": "0.1", "profit": "1.0", "roi": "1.0"}
              for i in range(1, 4)]
    text, kb = _pagination_view.build_trades_view(trades, page=0, page_size=5)
    assert "1/1" in text
    assert kb is None


async def test_build_trades_view_pager_for_multi_page() -> None:
    trades = [{"id": i, "coin": "BTC", "buy_exchange": "A", "sell_exchange": "B",
               "amount": "0.1", "profit": "1.0", "roi": "1.0"}
              for i in range(1, 12)]
    text, kb = _pagination_view.build_trades_view(trades, page=0, page_size=5)
    assert "1/3" in text
    assert kb is not None
    assert kb.inline_keyboard  # не пустой


async def test_pager_invalid_callback() -> None:
    cb = _make_callback("trades:page:abc")
    api = ApiClient(base_url="http://test")
    await _on_pager(cb, api)
    cb.answer.assert_awaited()


async def test_pager_calls_api_and_edits_message() -> None:
    cb = _make_callback("trades:page:0")
    api = ApiClient(base_url="http://test")
    with respx.mock(base_url="http://test", assert_all_mocked=False) as mock:
        mock.get("/trades/filter").respond(
            200,
            json=[
                {
                    "id": 1, "coin": "BTC", "buy_exchange": "Binance",
                    "sell_exchange": "Bybit", "amount": "0.1",
                    "profit": "10", "roi": "1.0",
                }
            ],
        )
        await _on_pager(cb, api)
    assert cb.message.edit_text.await_count == 1
    await api.aclose()


async def test_cmd_trades_id_calls_api() -> None:
    msg = _make_message()
    cmd = MagicMock()
    cmd.args = "5"
    api = ApiClient(base_url="http://test")
    with respx.mock(base_url="http://test") as mock:
        mock.get("/trades/5").respond(
            200,
            json={
                "id": 5, "coin": "BTC", "buy_exchange": "Binance",
                "sell_exchange": "Bybit", "amount": "0.1",
                "buy_price": "100", "sell_price": "110",
                "profit": "1", "roi": "1.0",
                "trade_type": "CEX_CEX", "status": "COMPLETED",
                "created_at": "2025-01-01T00:00:00",
            },
        )
        await cmd_trades_id(msg, cmd, api)
    assert msg.answer.await_count == 1
    args, _ = msg.answer.call_args
    assert "#5" in args[0]
    await api.aclose()


async def test_cmd_trades_id_404_message() -> None:
    msg = _make_message()
    cmd = MagicMock()
    cmd.args = "999"
    api = ApiClient(base_url="http://test")
    with respx.mock(base_url="http://test") as mock:
        mock.get("/trades/999").respond(404, json={"detail": "not found"})
        await cmd_trades_id(msg, cmd, api)
    args, _ = msg.answer.call_args
    assert "не найдена" in args[0]
    await api.aclose()


async def test_cmd_trades_id_missing_arg() -> None:
    msg = _make_message()
    cmd = MagicMock()
    cmd.args = None
    api = ApiClient(base_url="http://test")
    await cmd_trades_id(msg, cmd, api)
    args, _ = msg.answer.call_args
    assert "Использование" in args[0]
    await api.aclose()
