"""Подтверждение сделки: переводит PENDING → COMPLETED с пересчётом P/L."""
from __future__ import annotations

from app.core.services.calculator import TradeCalculator
from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class CompleteTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, trade_id: int, user_id: int = 0):
        async with self.uow:
            trade = await self.uow.trades.get_by_id(trade_id, user_id=user_id)
            if trade is None:
                return None
            trade.status = TradeStatus.COMPLETED
            trade = TradeCalculator.calculate(trade)
            return await self.uow.trades.update(trade_id, trade, user_id=user_id)
