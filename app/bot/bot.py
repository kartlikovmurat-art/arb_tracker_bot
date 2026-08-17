"""Arbitrage Tracker Bot — точка входа.

Запускает Telegram-бота, который общается с локальным FastAPI
(``app.main``) через ``httpx.AsyncClient``. Вся бизнес-логика
лежит в ``app/api`` и доменном слое — бот только маршрутизирует
команды пользователя.

Главное отличие от старой версии:
    * Полностью убран ``aiohttp`` (и ``AiohttpSession``, и
      ``aiohttp.ClientSession``).
    * HTTP-стек построен на ``httpx.AsyncClient`` через кастомный
      session-класс ``HttpxSession``, который подменяет
      ``AiohttpSession`` в aiogram 3.
    * Все хаки убраны: ``connector_init["family"]``,
      ``AiohttpSession(proxy=...)``, оффлайн-демо через POST
      в свой же FastAPI.
    * Никакой логики про Telegram-подарки. Бот — это generic
      CRM для учёта завершённых крипто-арбитражных сделок.

Зачем уходить с aiohttp:
    На Windows + некоторых VPN-конфигурациях aiohttp падает на
    ``ClientConnectorError WinError 121 — Cannot connect to
    api.telegram.org``, при этом ``socket``, ``requests`` и
    Telegram Desktop работают нормально. Это сочетание aiohttp
    и сетевого стека Windows. ``httpx`` использует другую
    реализацию HTTP-клиента и на той же машине работает стабильно.

Как работает ``HttpxSession``:
    Наследуется от ``aiogram.client.session.base.BaseSession``.
    aiogram при каждом вызове метода (например, ``bot.send_message``)
    дёргает ``session.make_request(bot, method)``. Мы реализуем
    ровно этот метод через httpx, а всю обвязку — URL,
    сериализацию, проверку ответа, маппинг ошибок — берём из
    базового класса.

Зависимости:
    pip install aiogram httpx
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Позволяет запускать скрипт напрямую: ``python app/bot/bot.py``
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx  # noqa: E402
from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.methods import TelegramMethod  # noqa: E402
from aiogram.methods.base import TelegramType  # noqa: E402

from app.bot.api import ApiClient, create_api_client  # noqa: E402
from app.bot.handlers import register_all  # noqa: E402
from app.config.settings import API_URL, BOT_TOKEN  # noqa: E402

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Кастомная сессия aiogram поверх httpx.AsyncClient
# ──────────────────────────────────────────────────────────────────────
class HttpxSession(BaseSession):
    """aiogram-session на базе httpx. Полная замена ``AiohttpSession``.

    aiogram внутри себя при вызове любого метода (``bot.send_message``,
    ``bot.get_me``, ``bot.get_updates`` и т.д.) идёт в
    ``session.make_request(bot, method)``. Мы реализуем этот метод
    через httpx, а всю обвязку (формирование URL, сериализация
    параметров, проверка статуса ответа, маппинг ошибок в
    ``TelegramBadRequest`` / ``TelegramNetworkError`` / и т.д.)
    берём из базового класса.
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
        url = self.api.api_url(token=bot.token, method=method.__api_method__)

        # Собираем форму вручную, потому что в aiogram 3.30 метод
        # ``build_form_data`` переехал в ``AiohttpSession`` и возвращает
        # специфичный для aiohttp ``FormData``. В ``BaseSession`` остался
        # ``prepare_value``, на котором мы и собираем данные.
        form: dict[str, Any] = {}
        files: dict[str, Any] = {}
        for key, value in method.model_dump(warnings=False).items():
            prepared = self.prepare_value(value, bot=bot, files=files)
            if prepared in (None, ""):
                continue
            form[key] = prepared

        effective_timeout = self.timeout if timeout is None else timeout
        try:
            if files:
                # multipart: в httpx файлы передаются как кортежи
                # (filename, content, content_type). aiogram 3.30
                # ``BufferedInputFile``/``InputFile`` не предоставляют
                # ``content_type`` явно — выводим mime из имени файла,
                # а если не получается, ставим application/octet-stream.
                import mimetypes

                async def _file_bytes(f: Any) -> bytes:
                    if hasattr(f, "data") and isinstance(f.data, (bytes, bytearray)):
                        return bytes(f.data)
                    chunks = []
                    async for chunk in f.read(bot):
                        chunks.append(chunk)
                    return b"".join(chunks)

                multipart_files: dict[str, tuple[str, bytes, str]] = {}
                for key, f in files.items():
                    name = f.filename or key
                    mime, _ = mimetypes.guess_type(name)
                    multipart_files[key] = (name, await _file_bytes(f), mime or "application/octet-stream")
                response = await client.post(
                    url,
                    data=form,
                    files=multipart_files,
                    timeout=effective_timeout,
                )
            else:
                # Без файлов: посылаем JSON, как делает современный
                # клиент Telegram Bot API.
                response = await client.post(
                    url,
                    json=form,
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
        checked = self.check_response(
            bot=bot,
            method=method,
            status_code=response.status_code,
            content=raw_result,
        )
        return checked.result  # type: ignore[return-value]


# ──────────────────────────────────────────────────────────────────────
# Запуск
# ──────────────────────────────────────────────────────────────────────
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
    api = create_api_client(API_URL)
    await api.start()

    try:
        from aiogram.client.default import DefaultBotProperties

        bot = Bot(
            token=BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode="HTML"),
        )
        dp = Dispatcher(storage=MemoryStorage())
        # Прокидываем api в workflow_data, чтобы хендлеры
        # могли его получить через аргумент ``api: ApiClient``.
        dp.workflow_data.update(api=api)
        register_all(dp, api)

        # Глобальный обработчик ошибок: чтобы одно битое сообщение
        # не убило диспетчер. Пользователь всегда получит внятный
        # ответ, а в логах будет полный traceback.
        @dp.error()
        async def _on_error(event, exception):  # type: ignore[no-untyped-def]
            logger.exception(
                "Unhandled exception in handler: %s",
                exception,
                exc_info=exception,
            )
            # Пытаемся ответить пользователю там, где это возможно.
            try:
                if getattr(event, "message", None):
                    await event.message.answer(  # type: ignore[union-attr]
                        "❌  Произошла внутренняя ошибка.\n"
                        "Попробуй ещё раз или напиши /start."
                    )
                elif getattr(event, "callback_query", None) and event.callback_query.message:
                    await event.callback_query.message.answer(  # type: ignore[union-attr]
                        "❌  Внутренняя ошибка. Попробуй ещё раз."
                    )
                    await event.callback_query.answer()  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                # Не даём ошибке из error-handler'а выйти наружу.
                logger.exception("Failed to send error message to user")
            return True  # Говорим aiogram, что ошибка обработана.

        try:
            me = await bot.get_me()
            logger.info("Бот запущен: @%s (id=%s)", me.username, me.id)
            
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🚀 Mini App",
            web_app=WebAppInfo(
                url="https://arb-tracker-miniapp.pages.dev/"
            ),
        )
    )

    await dp.start_polling(bot)
        finally:
            await api.aclose()
            await session.close()
    except Exception:
        # на холодную не получилось достучаться — закрываем оба клиента
        # корректно, чтобы не сыпались warning'и о незакрытых сокетах.
        await api.aclose()
        await session.close()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
