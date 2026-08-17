from dotenv import load_dotenv
import os
import warnings


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN:
    BOT_TOKEN = BOT_TOKEN.strip()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./db.sqlite3")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
if API_URL:
    API_URL = API_URL.strip()


# If DATABASE_URL is configured to use asyncpg but asyncpg cannot be
# imported/compiled in this environment, fall back to a local sqlite
# URL so the API can start for local development and tests.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )

if DATABASE_URL.startswith("postgresql+asyncpg://"):
    try:
        import asyncpg  # noqa: F401
    except Exception as exc:
        warnings.warn(
            f"DATABASE_URL uses asyncpg but asyncpg cannot be imported: {exc}.",
            RuntimeWarning,
        )

# Normalize local sqlite paths on Windows: ensure three slashes for relative
# and four for absolute drive paths (sqlite+aiosqlite:///C:/path)
if DATABASE_URL.startswith("sqlite+aiosqlite://"):
    # If user provided a Windows absolute path like sqlite+aiosqlite:///C:\...,
    # leave as-is. If somehow a single-slash form appears, convert to triple.
    if DATABASE_URL.count("/") < 3:
        DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite:/", "sqlite+aiosqlite:///")


# BOT_TOKEN is optional for running the API; warn if missing but don't
# raise so the app can start in environments without a bot token.
if not BOT_TOKEN:
    warnings.warn("BOT_TOKEN not set; bot will not start automatically.", RuntimeWarning)