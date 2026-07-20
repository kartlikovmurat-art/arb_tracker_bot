"""Тесты для HTTP-клиента бота.

Используем ``respx`` — он перехватывает все httpx-запросы
и позволяет мокать ответы без поднятия настоящего FastAPI.
"""
from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
import respx

from app.bot.api import ApiClient, ApiError, TradePayload


@pytest.fixture
async def api() -> ApiClient:
    client = ApiClient(base_url="http://test", timeout=2.0)
    yield client
    await client.aclose()


async def test_overall_stats_ok(api: ApiClient) -> None:
    with respx.mock(base_url="http://test") as mock:
        route = mock.get("/statistics/").respond(
            200,
            json={
                "total_trades": 3,
                "completed_trades": 3,
                "pending_trades": 0,
                "cancelled_trades": 0,
                "profitable_trades": 2,
                "losing_trades": 1,
                "total_profit": "150.50",
                "average_roi": "2.5",
                "win_rate": "66.66",
            },
        )
        data = await api.overall_stats()
    assert data["total_trades"] == 3
    assert Decimal(data["total_profit"]) == Decimal("150.50")
    assert route.called


async def test_overall_stats_api_error(api: ApiClient) -> None:
    with respx.mock(base_url="http://test") as mock:
        mock.get("/statistics/").respond(500, text="boom")
        with pytest.raises(ApiError) as exc_info:
            await api.overall_stats()
    assert exc_info.value.status_code == 500
    assert "boom" in str(exc_info.value)


async def test_list_trades_coin_filter(api: ApiClient) -> None:
    with respx.mock(base_url="http://test") as mock:
        route = mock.get("/trades/filter", params={"coin": "BTC"}).respond(
            200,
            json=[{"id": 1, "coin": "BTC"}],
        )
        trades = await api.list_trades(coin="BTC")
    assert trades[0]["coin"] == "BTC"
    assert route.called


async def test_list_trades_empty(api: ApiClient) -> None:
    with respx.mock(base_url="http://test", assert_all_mocked=False) as mock:
        # list_trades всегда ходит в /trades/filter (даже без фильтров).
        mock.get("/trades/filter").respond(200, json=[])
        trades = await api.list_trades()
    assert trades == []


async def test_create_trade_normalises_enums() -> None:
    payload = TradePayload(
        {
            "coin": "BTC",
            "buy_exchange": "Binance",
            "sell_exchange": "Bybit",
            "amount": "0.5",
            "buy_price": "60000",
            "sell_price": "60500",
            "trade_type": "cex-cex",
            "status": "completed",
        }
    )
    assert payload["trade_type"] == "CEX_CEX"
    assert payload["status"] == "COMPLETED"


async def test_create_trade_decimal_serialisation(api: ApiClient) -> None:
    captured: dict = {}

    def callback(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": 1, **captured["body"]})

    with respx.mock(base_url="http://test") as mock:
        mock.post("/trades/").mock(side_effect=callback)
        payload = TradePayload.from_raw(
            {
                "coin": "BTC",
                "buy_exchange": "Binance",
                "sell_exchange": "Bybit",
                "amount": Decimal("0.5"),
                "buy_price": Decimal("60000"),
                "sell_price": Decimal("60500"),
            }
        )
        await api.create_trade(payload)
    assert captured["body"]["amount"] == "0.5"
    assert captured["body"]["buy_price"] == "60000"


async def test_get_trade_not_found(api: ApiClient) -> None:
    with respx.mock(base_url="http://test") as mock:
        mock.get("/trades/42").respond(404, json={"detail": "Trade not found"})
        with pytest.raises(ApiError) as exc_info:
            await api.get_trade(42)
    assert exc_info.value.status_code == 404
    assert "Trade not found" in str(exc_info.value)


async def test_export_excel_returns_bytes(api: ApiClient) -> None:
    blob = b"\x50\x4b\x03\x04fakexlsx"
    with respx.mock(base_url="http://test") as mock:
        mock.get("/export/excel").respond(
            200,
            content=blob,
            headers={"content-type": "application/octet-stream"},
        )
        result = await api.export_excel()
    assert result == blob


async def test_network_error_wrapped(api: ApiClient) -> None:
    with respx.mock(base_url="http://test") as mock:
        mock.get("/statistics/").mock(
            side_effect=httpx.ConnectError("dns down")
        )
        with pytest.raises(ApiError) as exc_info:
            await api.overall_stats()
    assert "Сеть" in str(exc_info.value)
    assert "dns down" in str(exc_info.value)
