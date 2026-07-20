"""Бэкап и импорт данных.

* ``/backup`` — скачивает JSON со всеми сделками.
* ``/import`` — отправь JSON-файл боту в ответ на эту команду.
"""
from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.api import ApiClient, ApiError
from app.bot.keyboards import main_menu

logger = logging.getLogger(__name__)


def register(dp: Dispatcher, api: ApiClient) -> None:
    dp.message.register(cmd_backup, Command("backup"))
    dp.message.register(cmd_import, Command("import"))
    # Принимаем файл с расширением .json
    dp.message.register(handle_import_document, F.document)


async def cmd_backup(message: Message, api: ApiClient) -> None:  # type: ignore[assignment]
    await message.answer("⏳ Готовлю бэкап…")
    try:
        uid = message.from_user.id if message.from_user else 0
        data = await api.backup_json(uid)
    except ApiError as exc:
        await message.answer(f"❌ Не удалось: {exc.detail or exc}")
        return
    if not data:
        await message.answer("ℹ️ База пуста — бэкап нечего делать.")
        return
    filename = f"trades_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    from aiogram.types import BufferedInputFile
    document = BufferedInputFile(data, filename=filename)
    await message.answer_document(
        document=document,
        caption=(
            f"💾  <b>Бэкап готов!</b>\n"
            f"📎  {filename}\n"
            f"📦  {len(data)} байт\n\n"
            "💡  <i>Храни этот файл в безопасном месте.\n"
            "Чтобы восстановить: отправь его боту с командой /import</i>"
        ),
        reply_markup=main_menu(),
    )


async def cmd_import(message: Message) -> None:
    await message.answer(
        "📥  <b>Импорт сделок из бэкапа</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Отправь мне JSON-файл (формат /backup) reply-сообщением\n"
        "на это сообщение, или просто прикрепи его с подписью <code>/import</code>.\n\n"
        "💡  <i>Дубликаты (по id) будут пропущены.</i>"
    )


async def handle_import_document(
    message: Message, api: ApiClient  # type: ignore[assignment]
) -> None:
    if message.document is None or not message.document.file_name.endswith(".json"):
        return
    await message.answer("⏳ Импортирую…")
    from aiogram import Bot
    import httpx
    bot: Bot = message.bot  # type: ignore[assignment]
    try:
        # Скачиваем файл через Telegram Bot API
        file = await bot.get_file(message.document.file_id)
        if file.file_path is None:
            await message.answer("❌ Не удалось получить файл.")
            return
        # Скачиваем напрямую через api.telegram.org
        url = f"https://api.telegram.org/file/bot{api._client.__class__.__init__}" if False else None
        # Используем aiogram download
        import io
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        data = buf.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.exception("download failed")
        await message.answer(f"❌ Не удалось скачать файл: {exc}")
        return
    try:
        uid = message.from_user.id if message.from_user else 0
        result = await api.import_json(data, user_id=uid)
    except ApiError as exc:
        await message.answer(f"❌ Ошибка импорта: {exc.detail or exc}")
        return
    await message.answer(
        f"✅  <b>Импорт завершён!</b>\n\n"
        f"📥  Добавлено: <b>{result.get('inserted', 0)}</b>\n"
        f"⏭  Пропущено (дубликаты): <b>{result.get('skipped', 0)}</b>\n\n"
        f"💡  Проверь: /trades",
        reply_markup=main_menu(),
    )
