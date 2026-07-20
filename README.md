# Arbitrage Tracker Bot — Quick start

Steps to get the project running locally (Windows):

1) Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Create `.env` from the example and fill values

```powershell
copy .env.example .env
# then edit .env and set BOT_TOKEN and DATABASE_URL
```

4) Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

5) Run API (FastAPI)

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

6) Run Telegram bot

```powershell
.\.venv\Scripts\python.exe app\bot\bot.py
```

Notes:
- If you use Windows and encounter network issues with `aiohttp`, they are often environmental (VPN, OS socket stack). Tests use SQLite and are runnable locally.
- To change DB to PostgreSQL later, update `DATABASE_URL` in `.env`.

Applying migrations (Alembic)

```powershell
# create revision (autogenerate):
.\.venv\Scripts\alembic revision --autogenerate -m "create trades table"

# apply migrations to DB:
.\.venv\Scripts\alembic upgrade head
```

Note: Alembic uses `alembic.ini` for the `sqlalchemy.url` by default; set it there or export `DATABASE_URL` before running commands.
