import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
from app.api.webapp import _WEBAPP_DIR, router as webapp_router

from app.infrastructure.database import create_tables

# Ensure the DB schema exists when the application module is imported.
# This avoids failures in test environments where FastAPI lifespan events
# may not be triggered before the first request.
asyncio.run(create_tables())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="Arbitrage Tracker API",
    version="1.0.0",
    lifespan=lifespan,
)


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
app.include_router(webapp_router)

# Статические файлы мини-приложения (CSS/JS, если появятся).
if _WEBAPP_DIR.exists():
    app.mount("/webapp/static", StaticFiles(directory=str(_WEBAPP_DIR)), name="webapp-static")


@app.get("/")
async def root():
    return {
        "message": "Arbitrage Tracker API"
    }