"""Registration of all handlers in the aiogram dispatcher.

Each submodule exports ``register(dp, api, ...)`` which attaches its
own handlers. ``bot.py`` just calls ``register_all(dp, api)`` from
here.
"""
from __future__ import annotations

from aiogram import Dispatcher

from app.bot.api import ApiClient
from app.bot.handlers import (
    add_trade,
    analytics,
    common,
    export,
    menu,
    pagination,
    view,
)


def register_all(dp: Dispatcher, api: ApiClient) -> None:
    """Connect all handler groups. Order does not matter much, except
    pagination must be registered to catch ``trades:page:*`` callbacks
    even when they originate from the menu."""
    common.register(dp)
    add_trade.register(dp, api)
    view.register(dp, api)
    analytics.register(dp, api)
    export.register(dp, api)
    menu.register(dp, api)
    pagination.register(dp, api)
