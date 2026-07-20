"""Отдаёт мини-приложение (HTML + JS) как статику.

Telegram Mini App требует публичный HTTPS URL — этот эндпоинт
отдаёт ``index.html`` из ``app/bot/webapp/`` для разработки.
Для production пробрось этот путь через ngrok / Cloudflare Tunnel
или захости HTML на GitHub Pages (тогда /api/* будет недоступен —
придётся проксировать через бота).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


_WEBAPP_DIR = Path(__file__).resolve().parent.parent / "bot" / "webapp"

router = APIRouter(tags=["WebApp"], prefix="/webapp")


@router.get("/", response_class=HTMLResponse)
async def webapp_index() -> FileResponse:
    """Главная страница мини-приложения."""
    return FileResponse(_WEBAPP_DIR / "index.html")


# Подключаем StaticFiles для /webapp/static/* если появятся ассеты
# (сейчас HTML inline, но это место для будущих CSS/JS).
# Регистрируется в main.py, не здесь, потому что StaticFiles —
# это ASGI-app, а не endpoint.
