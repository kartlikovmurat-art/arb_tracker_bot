import os

# Force tests to use a local SQLite database and a dummy bot token.
# This prevents external environment values like PostgreSQL URLs from leaking into test runs.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["BOT_TOKEN"] = "test_token"
os.environ["API_URL"] = "http://127.0.0.1:8000"
