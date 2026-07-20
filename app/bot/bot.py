"""
Arbitrage Tracker Bot — Telegram interface.

Полностью переписанная версия. Главное отличие от старой:
    * Полностью убран aiohttp (и AiohttpSession, и aiohttp.ClientSession).
    * HTTP-стек построен на httpx.AsyncClient через кастомный session-класс
      `HttpxSession`, который подменяет `AiohttpSession` в aiogram 3.
    * Все дикие хаки убраны: больше нет `connector_init["family"]`,
      нет `AiohttpSession(proxy=...)`, нет «оффлайн-демо через POST
      в свой же FastAPI» (это маскировало проблему, а не решало её).
    * Никакой логики про Telegram-подарки. Бот — это generic CRM
      для учёта завершённых крипто-арбитражных сделок.

Зачем уходить с aiohttp:
    На Windows + некоторых VPN-конфигурациях aiohttp падает на
    `ClientConnectorError WinError 121 — Cannot connect to api.telegram.org`,
    при этом `socket`, `requests` и Telegram Desktop работают нормально.
    Это сочетание aiohttp и сетевого стека Windows. httpx использует
    другую реализацию HTTP-клиента и на той же машине работает стабильно.

Как работает `HttpxSession`:
    Наследуется от `aiogram.client.session.base.BaseSession`. aiogram при
    каждом вызове метода (например, `bot.send_message(...)`) дёргает
    `session.make_request(bot, method)`. Мы реализуем ровно этот метод
    через httpx, а всю обвязку — URL, сериализацию, проверку ответа,
    маппинг ошибок — берём из базового класса (api.api_url, build_form_data,
    check_response). То есть это легитимный aiogram-session, просто
    на другом транспорте.

Зависимости:
    pip install aiogram httpx
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

# Позволяет запускать скрипт напрямую: `python app/bot/bot.py`
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx  # noqa: E402
from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.filters import Command, CommandStart  # noqa: E402
from aiogram.fsm.context import FSMContext  # noqa: E402
from aiogram.fsm.state import State, StatesGroup  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.methods import TelegramMethod  # noqa: E402
from aiogram.methods.base import TelegramType  # noqa: E402
from aiogram.types import Message  # noqa: E402

from app.config.settings import API_URL, BOT_TOKEN  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Кастомная сессия aiogram поверх httpx.AsyncClient
# ---------------------------------------------------------------------------
class HttpxSession(BaseSession):
    """aiogram-session на базе httpx. Полная замена AiohttpSession.

    aiogram внутри себя при вызове любого метода (`bot.send_message`,
    `bot.get_me`, `bot.get_updates` и т.д.) идёт в
    `session.make_request(bot, method)`. Мы реализуем этот метод
    через httpx, а всю обвязку (формирование URL, сериализация
    параметров, проверка статуса ответа, маппинг ошибок в
    `TelegramBadRequest` / `TelegramNetworkError` / и т.д.) берём
    из базового класса.
    """

    def __init__(
        self,
        proxy: Optional[str] = None,
        timeout: float = 35.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._proxy = proxy
        self._timeout = httpx.Timeout(timeout)
        self._client: Optional[httpx.AsyncClient] = None

    async def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            proxy=self._proxy,
            http2=False,
            follow_redirects=True,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        await super().close()

    async def create_session(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = await self._create_client()
        return self._client

    async def stream_content(
        self,
        url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ):
        """Стрим-чтение контента (нужно aiogram для скачивания файлов)."""
        client = await self.create_session()
        if headers is None:
            headers = {}
        try:
            async with client.stream(
                "GET",
                url,
                headers=headers,
                timeout=timeout,
            ) as response:
                if raise_for_status:
                    response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size):
                    yield chunk
        except httpx.HTTPError as exc:
            from aiogram.exceptions import TelegramNetworkError
            raise TelegramNetworkError(
                method=None, message=f"{type(exc).__name__}: {exc}"
            ) from exc

    async def make_request(
        self,
        bot: "Bot",
        method: TelegramMethod[TelegramType],
        timeout: Optional[int] = None,
    ) -> TelegramType:
        client = await self.create_session()

        # URL вида https://api.telegram.org/bot<TOKEN>/<METHOD>
        url = self.api.api_url(token=bot.token, method=method.__api_method__)

        # build_form_data умеет JSON-сериализацию и InputFile (multipart).
        # Для текстовых команд этого бота всегда хватает JSON-варианта,
        # но на будущее сохраняем полную совместимость с InputFile.
        form = self.build_form_data(bot=bot, method=method)

        effective_timeout = (
            self.timeout if timeout is None else timeout
        )
        try:
            response = await client.post(
                url,
                data=form,
                timeout=effective_timeout,
            )
        except httpx.TimeoutException as exc:
            from aiogram.exceptions import TelegramNetworkError
            raise TelegramNetworkError(
                method=method, message=f"Request timeout error: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            from aiogram.exceptions import TelegramNetworkError
            raise TelegramNetworkError(
                method=method, message=f"{type(exc).__name__}: {exc}"
            ) from exc

        raw_result = response.text
        # check_response сам парсит JSON и бросает правильные исключения
        checked = self.check_response(
            bot=bot,
            method=method,
            status_code=response.status_code,
            content=raw_result,
        )
        return checked.result  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# FSM: диалог добавления сделки
# ---------------------------------------------------------------------------
class TradeForm(StatesGroup):
    coin = State()
    buy_exchange = State()
    sell_exchange = State()
    amount = State()
    buy_price = State()
    sell_price = State()
    strategy = State()
    note = State()


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def _to_decimal(text: str) -> Optional[Decimal]:
    """Парсит число из пользовательского ввода. None при ошибке."""
    try:
        return Decimal(text.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _normalize_payload(payload: dict) -> dict:
    """Нормализация enum-полей перед отправкой в API."""
    if "trade_type" in payload and isinstance(payload["trade_type"], str):
        payload["trade_type"] = (
            payload["trade_type"].replace("-", "_").replace(" ", "_").upper()
        )
    if "status" in payload and isinstance(payload["status"], str):
        payload["status"] = payload["status"].upper()
    return payload


async def _post_to_api(data: dict) -> tuple[bool, str]:
    """POST сделки в локальный FastAPI. Возвращает (ok, info)."""
    payload = _normalize_payload(dict(data))
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.post(f"{API_URL}/trades/", json=payload)
    except httpx.HTTPError as exc:
        return False, f"Сеть: {type(exc).__name__}: {exc}"
    if response.status_code in (200, 201):
        return True, "ok"
    return False, f"API {response.status_code}: {response.text}"


# ---------------------------------------------------------------------------
# Хэндлеры
# ---------------------------------------------------------------------------
def register_handlers(dp: Dispatcher) -> None:
    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "👋 Добро пожаловать в Arbitrage Tracker Bot!\n\n"
            "Команды:\n"
            "/add_trade — добавить сделку пошагово\n"
            "/add_trade {\"coin\":\"BTC\",...} — добавить сделку JSON-ом\n"
            "/cancel — отменить текущий ввод"
        )

    @dp.message(Command("add_trade"))
    async def cmd_add_trade(message: Message, state: FSMContext) -> None:
        # Если после команды прислали JSON — сохраняем без диалога
        payload = message.text.removeprefix("/add_trade").strip() if message.text else ""
        if payload:
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                await message.answer("Невалидный JSON. Проверьте синтаксис.")
                return
            if not isinstance(data, dict):
                await message.answer("Ожидаю JSON-объект, не массив и не скаляр.")
                return
            ok, info = await _post_to_api(data)
            await message.answer(
                "✅ Сделка сохранена." if ok else f"❌ Не удалось сохранить: {info}"
            )
            return

        # Иначе запускаем пошаговый диалог
        await state.set_state(TradeForm.coin)
        await message.answer(
            "Ввод новой сделки. /cancel — отмена.\n"
            "Введите монету (например, BTC):"
        )

    @dp.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext) -> None:
        if (await state.get_state()) is None:
            await message.answer("Нет активного ввода.")
            return
        await state.clear()
        await message.answer("Ввод сделки отменён.")

    @dp.message(TradeForm.coin)
    async def step_coin(message: Message, state: FSMContext) -> None:
        await state.update_data(coin=(message.text or "").strip())
        await state.set_state(TradeForm.buy_exchange)
        await message.answer("Введите биржу покупки (buy_exchange):")

    @dp.message(TradeForm.buy_exchange)
    async def step_buy_exchange(message: Message, state: FSMContext) -> None:
        await state.update_data(buy_exchange=(message.text or "").strip())
        await state.set_state(TradeForm.sell_exchange)
        await message.answer("Введите биржу продажи (sell_exchange):")

    @dp.message(TradeForm.sell_exchange)
    async def step_sell_exchange(message: Message, state: FSMContext) -> None:
        await state.update_data(sell_exchange=(message.text or "").strip())
        await state.set_state(TradeForm.amount)
        await message.answer("Введите объём (amount), например 0.5:")

    @dp.message(TradeForm.amount)
    async def step_amount(message: Message, state: FSMContext) -> None:
        val = _to_decimal(message.text or "")
        if val is None or val <= 0:
            await message.answer(
                "Неверный формат числа для объёма. Введите число > 0 или /cancel."
            )
            return
        await state.update_data(amount=str(val))
        await state.set_state(TradeForm.buy_price)
        await message.answer("Введите цену покупки (buy_price):")

    @dp.message(TradeForm.buy_price)
    async def step_buy_price(message: Message, state: FSMContext) -> None:
        val = _to_decimal(message.text or "")
        if val is None or val <= 0:
            await message.answer(
                "Неверный формат числа для цены покупки. Введите число > 0 или /cancel."
            )
            return
        await state.update_data(buy_price=str(val))
        await state.set_state(TradeForm.sell_price)
        await message.answer("Введите цену продажи (sell_price):")

    @dp.message(TradeForm.sell_price)
    async def step_sell_price(message: Message, state: FSMContext) -> None:
        val = _to_decimal(message.text or "")
        if val is None or val <= 0:
            await message.answer(
                "Неверный формат числа для цены продажи. Введите число > 0 или /cancel."
            )
            return
        await state.update_data(sell_price=str(val))
        await state.set_state(TradeForm.strategy)
        await message.answer("Стратегия (опционально) или '-' чтобы пропустить:")

    @dp.message(TradeForm.strategy)
    async def step_strategy(message: Message, state: FSMContext) -> None:
        text = (message.text or "").strip()
        if text and text != "-":
            await state.update_data(strategy=text)
        await state.set_state(TradeForm.note)
        await message.answer("Комментарий (опционально) или '-' чтобы пропустить:")

    @dp.message(TradeForm.note)
    async def step_note(message: Message, state: FSMContext) -> None:
        text = (message.text or "").strip()
        if text and text != "-":
            await state.update_data(note=text)
        data = await state.get_data()
        ok, info = await _post_to_api(data)
        await message.answer(
            "✅ Сделка сохранена." if ok else f"❌ Не удалось сохранить: {info}"
        )
        await state.clear()


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------
def _pick_proxy() -> Optional[str]:
    return (
        os.getenv("BOT_PROXY")
        or os.getenv("TELEGRAM_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("HTTP_PROXY")
        or os.getenv("http_proxy")
    )


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN не задан. Получите новый токен у @BotFather и "
            "пропишите его в .env (см. .env.example)."
        )
        return

    proxy = _pick_proxy()
    if proxy:
        logger.info("Использую прокси для Telegram: %s", proxy)

    session = HttpxSession(proxy=proxy)
    try:
        bot = Bot(token=BOT_TOKEN, session=session)
        dp = Dispatcher(storage=MemoryStorage())
        register_handlers(dp)

        try:
            me = await bot.get_me()
            logger.info("Бот запущен: @%s (id=%s)", me.username, me.id)
            await dp.start_polling(bot)
        finally:
            await session.close()
    except Exception:
        # на холодную не получилось достучаться до Telegram — корректно
        # закрываем httpx-клиент, чтобы не сыпались warning'и
        await session.close()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
