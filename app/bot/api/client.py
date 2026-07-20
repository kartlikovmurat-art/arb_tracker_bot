"""Асинхронный клиент к FastAPI-эндпоинтам проекта.

Зачем он нужен: бот не должен знать про SQLAlchemy, репозитории
и DTO — только про HTTP-эндпоинты. Поэтому весь доступ к бизнес-
логике идёт через этот тонкий wrapper. Если API поменяется, чинить
надо только здесь.

Особенности:
    * Один ``httpx.AsyncClient`` создаётся один раз в ``start()`` и
      закрывается в ``aclose()``. Не плодим сокеты на каждый вызов.
    * Все методы возвращают распарсенный JSON (``dict`` / ``list``)
      либо бросают ``ApiError`` с человеко-читаемой причиной.
    * Таймаут умеренный (10 секунд) — если API висит, бот не должен
      зависать вместе с ним.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Mapping, Optional
from types import TracebackType

import httpx

logger = logging.getLogger(__name__)


class ApiError(RuntimeError):
    """Любая ошибка при общении с локальным API.

    Атрибуты:
        status_code: HTTP-статус, если ответ был получен (иначе ``None``).
        detail: текстовое описание от сервера или от httpx.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or message


class TradePayload(dict):
    """Словарь-сделка, отправляемая в ``POST /trades/``.

    Использовать как обычный ``dict`` — расширение нужно только
    ради type hint'а в IDE.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._normalise_enums()

    def _normalise_enums(self) -> None:
        # API ожидает enum-значения в верхнем регистре и с подчёркиваниями.
        # Пользователь может прислать «cex-cex» или «CEX CEX» — нормализуем.
        if "trade_type" in self and isinstance(self["trade_type"], str):
            self["trade_type"] = (
                self["trade_type"].replace("-", "_").replace(" ", "_").upper()
            )
        if "status" in self and isinstance(self["status"], str):
            self["status"] = self["status"].upper()

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "TradePayload":
        """Создаёт ``TradePayload`` из сырого dict, с конвертацией Decimal-строк."""
        data: dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, Decimal):
                data[key] = format(value.normalize(), "f")
            else:
                data[key] = value
        return cls(data)


class ApiClient:
    """Тонкая обёртка над ``httpx.AsyncClient`` с типизированными методами."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout)
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Ленивая инициализация HTTP-клиента."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                follow_redirects=True,
            )

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def __aenter__(self) -> "ApiClient":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    # ------------------------------------------------------------------ #
    # Внутренние хелперы
    # ------------------------------------------------------------------ #
    async def _get(self, path: str, **params: Any) -> Any:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise ApiError(
                f"Сеть: {type(exc).__name__}: {exc}"
            ) from exc
        return self._parse(response)

    async def _post(self, path: str, json: Mapping[str, Any]) -> Any:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.post(path, json=dict(json))
        except httpx.HTTPError as exc:
            raise ApiError(
                f"Сеть: {type(exc).__name__}: {exc}"
            ) from exc
        return self._parse(response)

    @staticmethod
    def _parse(response: httpx.Response) -> Any:
        if response.status_code >= 400:
            detail = response.text
            try:
                body = response.json()
                if isinstance(body, dict) and "detail" in body:
                    detail = str(body["detail"])
            except Exception:  # noqa: BLE001 — JSON может быть пустым
                pass
            raise ApiError(
                f"API {response.status_code}: {detail}",
                status_code=response.status_code,
                detail=detail,
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(
                f"API вернул невалидный JSON: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Trades
    # ------------------------------------------------------------------ #
    async def list_trades(
        self,
        *,
        coin: Optional[str] = None,
        exchange: Optional[str] = None,
        status: Optional[str] = None,
        trade_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Список сделок с опциональной фильтрацией."""
        params: dict[str, str] = {}
        if coin:
            params["coin"] = coin
        if exchange:
            params["exchange"] = exchange
        if status:
            params["status"] = status.upper()
        if trade_type:
            params["trade_type"] = (
                trade_type.replace("-", "_").replace(" ", "_").upper()
            )
        return await self._get("/trades/filter", **params)  # type: ignore[return-value]

    async def get_trade(self, trade_id: int) -> dict[str, Any]:
        return await self._get(f"/trades/{trade_id}")

    async def create_trade(
        self, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Создаёт сделку. На вход — dict, на выход — dict от API."""
        return await self._post("/trades/", dict(payload))  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #
    async def overall_stats(self) -> dict[str, Any]:
        return await self._get("/statistics/")  # type: ignore[return-value]

    async def coin_stats(self) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/coins/")  # type: ignore[return-value]

    async def monthly_stats(self) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/monthly/")  # type: ignore[return-value]

    async def daily_stats(self) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/daily/")  # type: ignore[return-value]

    async def exchange_stats(self) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/exchanges/")  # type: ignore[return-value]

    async def strategy_stats(self) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/strategies/")  # type: ignore[return-value]

    async def equity_curve(self) -> list[dict[str, Any]]:
        return await self._get("/statistics/equity/")  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    async def export_excel(self) -> bytes:
        """Скачивает Excel-отчёт. Возвращает сырые байты файла."""
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.get("/export/excel")
        except httpx.HTTPError as exc:
            raise ApiError(
                f"Сеть: {type(exc).__name__}: {exc}"
            ) from exc
        if response.status_code >= 400:
            raise ApiError(
                f"API {response.status_code}: {response.text}",
                status_code=response.status_code,
                detail=response.text,
            )
        return response.content


def create_api_client(base_url: str) -> ApiClient:
    """Фабрика для удобства. Создаёт и возвращает (не стартует)."""
    return ApiClient(base_url=base_url)
