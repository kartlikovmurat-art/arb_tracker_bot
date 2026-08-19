import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.trades import router as trades_router
from app.api.statistics import router as statistics_router
from app.api.exchange_statistics import (
    router as exchange_statistics_router,
)
from app.api.coin_statistics import (
    router as coin_statistics_router,
)
from app.api.strategy_statistics import (
    router as strategy_statistics_router,
)
from app.api.monthly_statistics import (
    router as monthly_statistics_router,
)
from app.api.daily_statistics import (
    router as daily_statistics_router,
)
from app.api.equity_curve import (
    router as equity_curve_router,
)
from app.api.export import (
    router as export_router,
)
from app.api.extras import router as extras_router

from app.infrastructure.database import create_tables

# Ensure the DB schema exists when the application module is imported.
# This avoids failures in test environments where FastAPI lifespan events
# may not be triggered before the first request.



@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="Arbitrage Tracker API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://arb-tracker-miniapp.pages.dev",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-Telegram-User-Id",
        "X-Telegram-Init-Data",
    ],
)


# Mini App
WEB_DIR = Path(__file__).resolve().parent / "web"

app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR / "static"),
    name="static",
)


@app.get("/miniapp")
async def miniapp():
    return FileResponse(
        WEB_DIR / "templates" / "index.html"
    )

# Mini App размещена на Cloudflare Pages, поэтому доступ к API
# разрешён только для её production-origin.


# Регистрируем /trades/search и /trades/{id}/complete ДО /trades/{id},
# иначе FastAPI парсит "search" как trade_id.
app.include_router(extras_router)
app.include_router(trades_router)

app.include_router(statistics_router)
app.include_router(exchange_statistics_router)
app.include_router(coin_statistics_router)
app.include_router(strategy_statistics_router)
app.include_router(monthly_statistics_router)
app.include_router(daily_statistics_router)
app.include_router(equity_curve_router)

app.include_router(export_router)



@app.get("/")
async def root():
    return {
        "message": "Arbitrage Tracker API"
    }


@app.get("/health")
async def health():
    """Liveness/readiness для Render, Fly, k8s, мониторинга.

    Возвращает 200 всегда — даже если БД пустая. Если процесс
    отвечает, значит uvicorn жив и роутер загружен. Полноценный
    readiness-check с пингом БД добавим позже, если потребуется.
    """
    from datetime import datetime, timezone

    return {
        "status": "ok",
        "service": "arb-tracker-api",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
