"""Асинхронный клиент к FastAPI-эндпоинтам проекта.

Зачем он нужен: бот не должен знать про SQLAlchemy, репозитории
и DTO — только про HTTP-эндпоинты. Поэтому весь доступ к бизнес-
логике идёт через этот тонкий wrapper. Если API поменяется, чинить
надо только здесь.

Изоляция пользователей:
    Каждый публичный метод принимает ``user_id`` — telegram user id
    пользователя, от имени которого делается запрос. Клиент добавляет
    его в ``X-Telegram-User-Id`` header, сервер использует для
    фильтрации данных. Без ``user_id`` (``0``) — режим legacy/админ.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Mapping, Optional
from types import TracebackType

import httpx

logger = logging.getLogger(__name__)


def _user_header(user_id: int) -> dict[str, str]:
    """Собирает заголовок с telegram user id для запроса к API."""
    if not user_id:
        return {}
    return {"X-Telegram-User-Id": str(int(user_id))}


class ApiError(RuntimeError):
    """Любая ошибка при общении с локальным API."""

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
    """Словарь-сделка, отправляемая в ``POST /trades/``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._normalise_enums()

    def _normalise_enums(self) -> None:
        if "trade_type" in self and isinstance(self["trade_type"], str):
            self["trade_type"] = (
                self["trade_type"].replace("-", "_").replace(" ", "_").upper()
            )
        if "status" in self and isinstance(self["status"], str):
            self["status"] = self["status"].upper()

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "TradePayload":
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
    async def _get(self, path: str, *, user_id: int = 0, **params: Any) -> Any:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.get(
                path, params=params, headers=_user_header(user_id)
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        return self._parse(response)

    async def _patch(
        self, path: str, json: Mapping[str, Any], *, user_id: int = 0
    ) -> Any:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.patch(
                path, json=dict(json), headers=_user_header(user_id)
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        return self._parse(response)

    async def _post(
        self, path: str, json: Mapping[str, Any], *, user_id: int = 0
    ) -> Any:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.post(
                path, json=dict(json), headers=_user_header(user_id)
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        return self._parse(response)

    async def _delete(self, path: str, *, user_id: int = 0) -> Any:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.delete(
                path, headers=_user_header(user_id)
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        if response.status_code >= 400:
            raise ApiError(
                f"API {response.status_code}",
                status_code=response.status_code,
                detail=response.text,
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    @staticmethod
    def _parse(response: httpx.Response) -> Any:
        if response.status_code >= 400:
            detail = response.text
            try:
                body = response.json()
                if isinstance(body, dict) and "detail" in body:
                    detail = str(body["detail"])
            except Exception:  # noqa: BLE001
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
            raise ApiError(f"API вернул невалидный JSON: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Trades
    # ------------------------------------------------------------------ #
    async def list_trades(
        self,
        user_id: int = 0,
        *,
        coin: Optional[str] = None,
        exchange: Optional[str] = None,
        status: Optional[str] = None,
        trade_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
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
        return await self._get("/trades/filter", user_id=user_id, **params)  # type: ignore[return-value]

    async def get_trade(self, trade_id: int, user_id: int = 0) -> dict[str, Any]:
        return await self._get(f"/trades/{trade_id}", user_id=user_id)

    async def create_trade(
        self, payload: Mapping[str, Any], user_id: int = 0
    ) -> dict[str, Any]:
        return await self._post("/trades/", dict(payload), user_id=user_id)  # type: ignore[return-value]

    async def patch_trade(
        self,
        trade_id: int,
        updates: Mapping[str, Any],
        user_id: int = 0,
    ) -> dict[str, Any]:
        return await self._patch(  # type: ignore[return-value]
            f"/trades/{trade_id}", dict(updates), user_id=user_id
        )

    async def delete_trade(self, trade_id: int, user_id: int = 0) -> None:
        await self._delete(f"/trades/{trade_id}", user_id=user_id)

    async def complete_trade(
        self, trade_id: int, user_id: int = 0
    ) -> dict[str, Any]:
        return await self._post(  # type: ignore[return-value]
            f"/trades/{trade_id}/complete", {}, user_id=user_id
        )

    async def search_trades(
        self, query: str, user_id: int = 0
    ) -> list[dict[str, Any]]:
        return await self._get("/trades/search", user_id=user_id, q=query)  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Backup & Import
    # ------------------------------------------------------------------ #
    async def backup_json(self, user_id: int = 0) -> bytes:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.get(
                "/backup", headers=_user_header(user_id)
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        if response.status_code >= 400:
            raise ApiError(
                f"API {response.status_code}",
                status_code=response.status_code,
                detail=response.text,
            )
        return response.content

    async def import_json(
        self, payload: bytes, user_id: int = 0
    ) -> dict[str, Any]:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.post(
                "/import",
                files={"file": ("backup.json", payload, "application/json")},
                headers=_user_header(user_id),
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        return self._parse(response)  # type: ignore[return-value]

    async def equity_chart(self, user_id: int = 0) -> bytes:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.get(
                "/statistics/equity/chart", headers=_user_header(user_id)
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        if response.status_code >= 400:
            raise ApiError(
                f"API {response.status_code}",
                status_code=response.status_code,
                detail=response.text,
            )
        return response.content

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #
    async def overall_stats(self, user_id: int = 0) -> dict[str, Any]:
        return await self._get("/statistics/", user_id=user_id)  # type: ignore[return-value]

    async def coin_stats(self, user_id: int = 0) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/coins/", user_id=user_id)  # type: ignore[return-value]

    async def monthly_stats(self, user_id: int = 0) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/monthly/", user_id=user_id)  # type: ignore[return-value]

    async def daily_stats(self, user_id: int = 0) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/daily/", user_id=user_id)  # type: ignore[return-value]

    async def exchange_stats(self, user_id: int = 0) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/exchanges/", user_id=user_id)  # type: ignore[return-value]

    async def strategy_stats(self, user_id: int = 0) -> dict[str, dict[str, Any]]:
        return await self._get("/statistics/strategies/", user_id=user_id)  # type: ignore[return-value]

    async def equity_curve(self, user_id: int = 0) -> list[dict[str, Any]]:
        return await self._get("/statistics/equity/", user_id=user_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    async def export_excel(self, user_id: int = 0) -> bytes:
        await self.start()
        assert self._client is not None
        try:
            response = await self._client.get(
                "/export/excel", headers=_user_header(user_id)
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"Сеть: {type(exc).__name__}: {exc}") from exc
        if response.status_code >= 400:
            raise ApiError(
                f"API {response.status_code}: {response.text}",
                status_code=response.status_code,
                detail=response.text,
            )
        return response.content


def create_api_client(base_url: str) -> ApiClient:
    return ApiClient(base_url=base_url)
