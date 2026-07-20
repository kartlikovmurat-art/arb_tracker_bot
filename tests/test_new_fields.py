"""Тесты для новых полей transfer_network и holding_time_seconds."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

try:
    import greenlet  # type: ignore
    _HAS_GREENLET = True
except Exception:
    _HAS_GREENLET = False

ALICE = 111111


@pytest.fixture
def isolated_app():
    import os
    import tempfile
    from sqlalchemy import text
    import asyncio
    tmpdir = tempfile.mkdtemp(prefix="arb_test_fields_")
    db_path = os.path.join(tmpdir, "test_fields.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["BOT_TOKEN"] = "test_token"
    os.environ["API_URL"] = "http://127.0.0.1:8000"

    from app.main import app  # noqa: WPS433
    from app.infrastructure.database import engine

    async def _truncate():
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM trades"))
    asyncio.run(_truncate())
    return TestClient(app), app


@pytest.fixture(autouse=True)
def _clean_db(isolated_app):
    from sqlalchemy import text
    import asyncio
    from app.infrastructure.database import engine

    async def _truncate():
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM trades"))
    asyncio.run(_truncate())
    yield


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_create_trade_with_network_and_holding(isolated_app) -> None:
    client, _ = isolated_app
    payload = {
        "coin": "ETH",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": "0.5",
        "buy_price": "3000",
        "sell_price": "3010",
        "transfer_network": "ERC20",
        "holding_time_seconds": 3600,
    }
    r = client.post(
        "/trades/",
        json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    trade = r.json()
    assert trade["transfer_network"] == "ERC20"
    assert trade["holding_time_seconds"] == 3600


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_create_trade_without_new_fields(isolated_app) -> None:
    """Обратная совместимость: новые поля опциональны."""
    client, _ = isolated_app
    payload = {
        "coin": "BTC",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": "0.1",
        "buy_price": "60000",
        "sell_price": "60100",
    }
    r = client.post(
        "/trades/",
        json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    trade = r.json()
    assert trade["transfer_network"] is None
    assert trade["holding_time_seconds"] is None


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_patch_network_and_holding(isolated_app) -> None:
    client, _ = isolated_app
    payload = {
        "coin": "SOL",
        "buy_exchange": "Binance",
        "sell_exchange": "OKX",
        "amount": "10",
        "buy_price": "100",
        "sell_price": "105",
    }
    r = client.post(
        "/trades/", json=payload,
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    trade = r.json()
    r = client.patch(
        f"/trades/{trade['id']}",
        json={"transfer_network": "Solana", "holding_time_seconds": 180},
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["transfer_network"] == "Solana"
    assert updated["holding_time_seconds"] == 180
