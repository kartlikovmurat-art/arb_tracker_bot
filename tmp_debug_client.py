import os
import json
import traceback
from pathlib import Path

# Ensure tests-like env
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./tmp_test.db')
os.environ['BOT_TOKEN'] = os.environ.get('BOT_TOKEN', 'test_token')
os.environ['API_URL'] = os.environ.get('API_URL', 'http://127.0.0.1:8000')

# Remove old DB for clean state
try:
    p = Path('./tmp_test.db')
    if p.exists():
        p.unlink()
except Exception as e:
    print('failed to remove old db', e)

try:
    import importlib
    import app.main as m
    print('imported app.main')
    from fastapi.testclient import TestClient
    client = TestClient(m.app)
    print('TestClient created')

    payload = {
        "coin": "BTC",
        "buy_exchange": "Binance",
        "sell_exchange": "Bybit",
        "amount": 0.5,
        "buy_price": 60000,
        "sell_price": 61000,
    }

    r = client.post('/trades/', json=payload)
    print('POST /trades/ status', r.status_code)
    try:
        print('response json:', r.json())
    except Exception:
        print('response text:', r.text)

except Exception:
    traceback.print_exc()
