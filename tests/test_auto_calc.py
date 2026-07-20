"""Тесты автоматического расчёта fees и holding time.

Проверяем, что:
1. buy_fee_percent / sell_fee_percent пересчитываются в money-значения.
2. network_fee объединяет withdrawal_fee + gas_fee (gas_fee=0).
3. holding_time_seconds вычисляется из bought_at и sold_at.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

try:
    import greenlet  # type: ignore
    _HAS_GREENLET = True
except Exception:
    _HAS_GREENLET = False

ALICE = 111111


@pytest.fixture(scope="module")
def isolated_app():
    tmpdir = tempfile.mkdtemp(prefix="arb_autotest_")
    db_path = os.path.join(tmpdir, "test_auto.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["BOT_TOKEN"] = "test_token"
    os.environ["API_URL"] = "http://127.0.0.1:8000"
    from app.main import app  # noqa: WPS433
    return TestClient(app), app


@pytest.fixture(autouse=True)
def _clean_db(isolated_app):
    from app.infrastructure.database import engine
    import asyncio
    async def _truncate():
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM trades"))
    asyncio.run(_truncate())
    yield


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_fees_auto_calculated_from_percent(isolated_app) -> None:
    """buy_fee_percent и sell_fee_percent дают money-значения."""
    client, _ = isolated_app
    payload = {
        "coin": "ETH",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": "1",  # 1 ETH
        "buy_price": "2000",
        "sell_price": "2010",
        "buy_fee_percent": "0.1",  # 0.1% от 2000*1 = 2 USDT
        "sell_fee_percent": "0.15",  # 0.15% от 2010*1 = 3.015 USDT
    }
    r = client.post(
        "/trades/", json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    t = r.json()
    # money-значения должны быть посчитаны
    assert float(t["buy_fee"]) == pytest.approx(2.0, rel=0.01)
    assert float(t["sell_fee"]) == pytest.approx(3.015, rel=0.01)


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_network_fee_combines_withdrawal_and_gas(isolated_app) -> None:
    """network_fee = withdrawal_fee, gas_fee=0."""
    client, _ = isolated_app
    payload = {
        "coin": "BTC",
        "buy_exchange": "Binance",
        "sell_exchange": "OKX",
        "amount": "0.1",
        "buy_price": "60000",
        "sell_price": "60100",
        "network_fee": "5.5",  # USDT
    }
    r = client.post(
        "/trades/", json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    t = r.json()
    assert float(t["network_fee"]) == 5.5
    assert float(t["withdrawal_fee"]) == 5.5
    assert float(t["gas_fee"]) == 0


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_holding_time_computed_from_bought_and_sold(isolated_app) -> None:
    """holding_time_seconds = sold_at - bought_at."""
    client, _ = isolated_app
    bought = "2025-07-20T10:00:00+00:00"
    sold = "2025-07-20T12:30:00+00:00"  # 2.5 часа = 9000 секунд
    payload = {
        "coin": "SOL",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": "10",
        "buy_price": "100",
        "sell_price": "105",
        "bought_at": bought,
        "sold_at": sold,
    }
    r = client.post(
        "/trades/", json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["holding_time_seconds"] == 9000
    assert t["bought_at"].startswith("2025-07-20T10:00")
    assert t["sold_at"].startswith("2025-07-20T12:30")


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_holding_time_not_set_when_only_bought(isolated_app) -> None:
    """Если только bought_at — holding_time_seconds = None (PENDING)."""
    client, _ = isolated_app
    payload = {
        "coin": "AVAX",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": "5",
        "buy_price": "30",
        "sell_price": "31",
        "bought_at": "2025-07-20T10:00:00+00:00",
    }
    r = client.post(
        "/trades/", json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["holding_time_seconds"] is None


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_patch_updates_fees(isolated_app) -> None:
    """Patch пересчитывает fees при изменении процентов."""
    client, _ = isolated_app
    payload = {
        "coin": "LINK",
        "buy_exchange": "Binance",
        "sell_exchange": "OKX",
        "amount": "10",
        "buy_price": "15",
        "sell_price": "15.5",
    }
    r = client.post(
        "/trades/", json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    t = r.json()
    r = client.patch(
        f"/trades/{t['id']}",
        json={"buy_fee_percent": "0.1", "sell_fee_percent": "0.15"},
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    # notional_buy = 10*15 = 150; 0.1% от 150 = 0.15
    assert float(updated["buy_fee"]) == pytest.approx(0.15, rel=0.01)
    # notional_sell = 10*15.5 = 155; 0.15% от 155 = 0.2325
    assert float(updated["sell_fee"]) == pytest.approx(0.2325, rel=0.01)


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_patch_updates_holding_time(isolated_app) -> None:
    """Patch с bought_at + sold_at пересчитывает holding_time_seconds."""
    client, _ = isolated_app
    payload = {
        "coin": "DOT",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": "100",
        "buy_price": "7",
        "sell_price": "7.1",
    }
    r = client.post(
        "/trades/", json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    t = r.json()
    r = client.patch(
        f"/trades/{t['id']}",
        json={
            "bought_at": "2025-07-20T08:00:00+00:00",
            "sold_at": "2025-07-21T08:00:00+00:00",  # сутки
        },
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    updated = r.json()
    assert updated["holding_time_seconds"] == 86400
