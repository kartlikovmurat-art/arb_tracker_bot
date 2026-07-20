"""Команда /export — выгрузка сделок в Excel через Telegram-документ."""
from __future__ import annotations

import io
import logging
from datetime import datetime

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.api import ApiClient, ApiError

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_export, Command("export"))


async def cmd_export(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    await message.answer("⏳ Готовлю Excel-выгрузку…")
    try:
        data = await api.export_excel()
    except ApiError as exc:
        await message.answer(f"❌ Не удалось выгрузить: {exc.detail or exc}")
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("export failed")
        await message.answer(
            f"❌ Непредвиденная ошибка: {type(exc).__name__}: {exc}"
        )
        return
    if not data:
        await message.answer("ℹ️ Выгрузка пуста — сделок пока нет.")
        return
    filename = f"trades_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    document = io.BytesIO(data)
    document.name = filename
    await message.answer_document(
        document=document,
        caption=f"📤 Экспорт сделок · {len(data)} байт",
    )
