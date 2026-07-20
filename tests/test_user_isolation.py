"""Тесты изоляции данных по telegram_user_id.

Критично: пользователь A не должен видеть/менять/удалять сделки
пользователя B. Все методы API фильтруют данные по
``X-Telegram-User-Id`` header.

Все тесты используют одну и ту же временную БД (создаётся в
фикстуре ``isolated_app``) — это проще и быстрее, чем переимпорт
``app.main`` на каждый тест. Перед каждым тестом таблица trades
очищается.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

try:
    import greenlet  # type: ignore
    _HAS_GREENLET = True
except Exception:
    _HAS_GREENLET = False

ALICE = 111111
BOB = 222222


@pytest.fixture(scope="module")
def isolated_app():
    """Создаёт чистое FastAPI-приложение с временной БД один раз на модуль.

    Сбрасывает таблицу trades перед каждым тестом через фикстуру
    ``_clean_db`` ниже.
    """
    import os
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="arb_test_")
    db_path = os.path.join(tmpdir, "test_isolation.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["BOT_TOKEN"] = "test_token"
    os.environ["API_URL"] = "http://127.0.0.1:8000"

    from app.main import app  # noqa: WPS433
    return TestClient(app), app


@pytest.fixture(autouse=True)
def _clean_db(isolated_app):
    """Очищает таблицу trades перед каждым тестом в модуле."""
    _client, app = isolated_app
    from app.infrastructure.database import engine
    import asyncio
    async def _truncate():
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM trades"))
    asyncio.run(_truncate())
    yield


def _create_trade(client: TestClient, user_id: int, coin: str = "BTC") -> dict:
    payload = {
        "coin": coin,
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": "0.5",
        "buy_price": "60000",
        "sell_price": "60200",
    }
    r = client.post(
        "/trades/",
        json=payload,
        headers={"X-Telegram-User-Id": str(user_id)},
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_alice_and_bob_have_separate_trades(isolated_app) -> None:
    client, _ = isolated_app
    a1 = _create_trade(client, ALICE, "BTC")
    a2 = _create_trade(client, ALICE, "ETH")
    b1 = _create_trade(client, BOB, "SOL")

    ra = client.get("/trades/", headers={"X-Telegram-User-Id": str(ALICE)})
    rb = client.get("/trades/", headers={"X-Telegram-User-Id": str(BOB)})
    assert ra.status_code == 200
    assert rb.status_code == 200

    alice_ids = {t["id"] for t in ra.json()}
    bob_ids = {t["id"] for t in rb.json()}

    assert a1["id"] in alice_ids
    assert a2["id"] in alice_ids
    assert b1["id"] not in alice_ids

    assert b1["id"] in bob_ids
    assert a1["id"] not in bob_ids
    assert a2["id"] not in bob_ids


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_cannot_get_other_users_trade_by_id(isolated_app) -> None:
    client, _ = isolated_app
    bob_trade = _create_trade(client, BOB, "XRP")
    r = client.get(
        f"/trades/{bob_trade['id']}",
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 404


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_cannot_patch_other_users_trade(isolated_app) -> None:
    client, _ = isolated_app
    bob_trade = _create_trade(client, BOB, "ADA")
    r = client.patch(
        f"/trades/{bob_trade['id']}",
        json={"buy_price": "99999"},
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 404
    r = client.get(
        f"/trades/{bob_trade['id']}",
        headers={"X-Telegram-User-Id": str(BOB)},
    )
    assert r.json()["buy_price"] != "99999"


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_cannot_delete_other_users_trade(isolated_app) -> None:
    client, _ = isolated_app
    bob_trade = _create_trade(client, BOB, "DOGE")
    r = client.delete(
        f"/trades/{bob_trade['id']}",
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 404
    r = client.get(
        f"/trades/{bob_trade['id']}",
        headers={"X-Telegram-User-Id": str(BOB)},
    )
    assert r.status_code == 200


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_statistics_are_user_scoped(isolated_app) -> None:
    client, _ = isolated_app
    _create_trade(client, ALICE, "AVAX")
    _create_trade(client, ALICE, "AVAX")
    _create_trade(client, BOB, "DOT")

    stats_a = client.get(
        "/statistics/", headers={"X-Telegram-User-Id": str(ALICE)}
    ).json()
    stats_b = client.get(
        "/statistics/", headers={"X-Telegram-User-Id": str(BOB)}
    ).json()

    # total_trades учитывает все (включая PENDING).
    assert stats_a["total_trades"] == 2
    assert stats_b["total_trades"] == 1
    assert stats_a["pending_trades"] == 2
    assert stats_b["pending_trades"] == 1


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_search_filters_by_user(isolated_app) -> None:
    client, _ = isolated_app
    _create_trade(client, ALICE, "UNI")
    _create_trade(client, BOB, "UNI")

    r = client.get(
        "/trades/search",
        params={"q": "UNI"},
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 200, r.text
    results = r.json()
    assert isinstance(results, list)
    for t in results:
        assert t["telegram_user_id"] == ALICE


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_x_user_id_alternative_header(isolated_app) -> None:
    client, _ = isolated_app
    _create_trade(client, ALICE, "VIAALT")
    r = client.get("/trades/", headers={"X-User-Id": str(ALICE)})
    coins = {t["coin"] for t in r.json()}
    assert "VIAALT" in coins


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_backup_is_user_scoped(isolated_app) -> None:
    client, _ = isolated_app
    _create_trade(client, ALICE, "ALICECOIN")
    _create_trade(client, BOB, "BOBCOIN")
    r = client.get("/backup", headers={"X-Telegram-User-Id": str(ALICE)})
    assert r.status_code == 200
    body = r.text
    assert "ALICECOIN" in body
    assert "BOBCOIN" not in body


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available")
def test_complete_only_own_trade(isolated_app) -> None:
    """Завершить чужую сделку нельзя."""
    client, _ = isolated_app
    bob_trade = _create_trade(client, BOB, "MATIC")
    r = client.post(
        f"/trades/{bob_trade['id']}/complete",
        headers={"X-Telegram-User-Id": str(ALICE)},
    )
    assert r.status_code == 404
    # У Боба сделка осталась PENDING
    r = client.get(
        f"/trades/{bob_trade['id']}",
        headers={"X-Telegram-User-Id": str(BOB)},
    )
    assert r.json()["status"] == "PENDING"
