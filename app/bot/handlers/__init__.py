"""Registration of all handlers in the aiogram dispatcher."""
from __future__ import annotations

from aiogram import Dispatcher

from app.bot.api import ApiClient
from app.bot.handlers import (
    add_trade,
    analytics,
    backup_io,
    calc,
    common,
    export,
    extras,
    manage,
    menu,
    pagination,
    view,
)


def register_all(dp: Dispatcher, api: ApiClient) -> None:
    """Connect all handler groups."""
    common.register(dp)
    add_trade.register(dp, api)
    calc.register(dp)
    view.register(dp, api)
    manage.register(dp, api)
    analytics.register(dp, api)
    export.register(dp, api)
    backup_io.register(dp, api)
    extras.register(dp, api)
    menu.register(dp, api)
    pagination.register(dp, api)
