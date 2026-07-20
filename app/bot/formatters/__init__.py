"""Преобразование ответов FastAPI в читабельный текст для Telegram."""

from app.bot.formatters.text import (
    format_overall_stats,
    format_trade,
    format_trade_compact,
    format_trades_page,
    format_dict_stats,
    format_equity_curve,
)

__all__ = [
    "format_overall_stats",
    "format_trade",
    "format_trade_compact",
    "format_trades_page",
    "format_dict_stats",
    "format_equity_curve",
]
