"""Health-endpoint должен отвечать 200, даже если БД пустая."""
import importlib
import sys

import pytest

try:
    import greenlet  # type: ignore
    _HAS_GREENLET = True
except Exception:
    _HAS_GREENLET = False


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available in environment")
def test_health_endpoint(tmp_path, monkeypatch):
    db_file = tmp_path / "test_health.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("BOT_TOKEN", "test_token")
    monkeypatch.setenv("API_URL", "http://127.0.0.1:8000")

    for module in ["app.config.settings", "app.infrastructure.database", "app.main"]:
        if module in sys.modules:
            del sys.modules[module]

    import app.main as app_main  # noqa: E402
    from fastapi.testclient import TestClient  # noqa: E402

    with TestClient(app_main.app) as client:
        r = client.get("/health")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ok"
        assert body["service"] == "arb-tracker-api"
        assert "ts" in body
