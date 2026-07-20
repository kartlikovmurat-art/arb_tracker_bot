import importlib
import sys
import pytest

try:
    import greenlet  # type: ignore
    _HAS_GREENLET = True
except Exception:
    _HAS_GREENLET = False

from fastapi.testclient import TestClient


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available in environment")
def test_trade_api_crud(tmp_path, monkeypatch):
    db_file = tmp_path / "test_api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("BOT_TOKEN", "test_token")
    monkeypatch.setenv("API_URL", "http://127.0.0.1:8000")

    for module in [
        "app.config.settings",
        "app.infrastructure.database",
        "app.main",
    ]:
        if module in sys.modules:
            del sys.modules[module]

    import app.main as app_main  # noqa: E402

    client = TestClient(app_main.app)

    payload = {
        "coin": "BTC",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": 0.5,
        "buy_price": 60000,
        "sell_price": 61000,
    }

    response = client.post("/trades/", json=payload)
    assert response.status_code == 200

    created = response.json()
    assert created["coin"] == payload["coin"]
    assert created["buy_exchange"] == payload["buy_exchange"]
    assert created["sell_exchange"] == payload["sell_exchange"]
    assert created["amount"] == "0.5"
    assert created["buy_price"] == "60000"
    assert created["sell_price"] == "61000"
    assert created["id"] is not None
    assert created["created_at"] is not None

    trade_id = created["id"]

    get_response = client.get(f"/trades/{trade_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == trade_id

    list_response = client.get("/trades/")
    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == trade_id
