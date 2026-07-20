"""HTTP-клиент к локальному FastAPI-сервису ``app.main``."""

from app.bot.api.client import (
    ApiClient,
    ApiError,
    TradePayload,
    create_api_client,
)

__all__ = ["ApiClient", "ApiError", "TradePayload", "create_api_client"]
