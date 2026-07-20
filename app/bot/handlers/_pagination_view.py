"""Общая логика рендера страницы сделок.

Вынесено, чтобы её мог дёргать и обычный хендлер, и callback
пагинации — без дублирования расчёта страниц и текста.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence, Tuple

from aiogram.types import InlineKeyboardMarkup

from app.bot.formatters import format_trades_page
from app.bot.formatters.text import PAGE_SIZE
from app.bot.keyboards import trades_pager


def build_trades_view(
    trades: Sequence[Mapping[str, Any]],
    *,
    page: int,
    page_size: int = PAGE_SIZE,
) -> Tuple[str, InlineKeyboardMarkup | None]:
    """Возвращает (текст, клавиатура). Клавиатуры нет, если страница одна."""
    if not trades:
        return format_trades_page(trades, page=page, page_size=page_size), None
    total_pages = max(1, (len(trades) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    text = format_trades_page(trades, page=page, page_size=page_size)
    if total_pages == 1:
        return text, None
    return text, trades_pager(page=page, total_pages=total_pages)
