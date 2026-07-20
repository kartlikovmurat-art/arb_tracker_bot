"""Частичное обновление сделки.

Принимает ``trade_id`` и dict с полями, которые нужно поменять
(только их, остальные не трогает). Пересчитывает P/L и ROI.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from app.core.services.calculator import TradeCalculator
from app.infrastructure.unit_of_work import UnitOfWork


class PatchTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(
        self,
        trade_id: int,
        updates: Mapping[str, Any],
        user_id: int = 0,
    ):
        async with self.uow:
            trade = await self.uow.trades.get_by_id(trade_id, user_id=user_id)
            if trade is None:
                return None

            for key, value in updates.items():
                if value is None:
                    continue
                if not hasattr(trade, key):
                    continue
                current = getattr(trade, key, None)
                if isinstance(current, Decimal) and not isinstance(value, Decimal):
                    try:
                        value = Decimal(str(value))
                    except Exception:  # noqa: BLE001
                        continue
                elif isinstance(current, datetime) and not isinstance(value, datetime):
                    # ISO-строка в datetime
                    if isinstance(value, str):
                        try:
                            value = datetime.fromisoformat(
                                value.replace("Z", "+00:00")
                            )
                        except ValueError:
                            continue
                setattr(trade, key, value)

            # Пересчёт fees и времени, profit, ROI.
            trade.recalculate()
            trade = TradeCalculator.calculate(trade)
            return await self.uow.trades.update(trade_id, trade, user_id=user_id)
