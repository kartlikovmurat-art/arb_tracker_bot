"""Inline and reply keyboards for the bot."""

from app.bot.keyboards.inline import (
    add_trade_menu,
    analytics_menu,
    help_menu,
    main_menu,
    trades_pager,
)
from app.bot.keyboards.reply import (
    BTN_ADD,
    BTN_ANALYTICS,
    BTN_EXPORT,
    BTN_HELP,
    BTN_STATS,
    BTN_TRADES,
    main_reply_keyboard,
)

__all__ = [
    # inline
    "add_trade_menu",
    "analytics_menu",
    "help_menu",
    "main_menu",
    "trades_pager",
    # reply
    "BTN_ADD",
    "BTN_ANALYTICS",
    "BTN_EXPORT",
    "BTN_HELP",
    "BTN_STATS",
    "BTN_TRADES",
    "main_reply_keyboard",
]
