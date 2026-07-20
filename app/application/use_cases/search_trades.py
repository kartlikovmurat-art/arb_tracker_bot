"""Полнотекстовый поиск по сделкам.

Ищет подстроку в coin, buy_exchange, sell_exchange, strategy, note.
Возвращает все совпадения, отсортированные по дате (новые первые).
"""
from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.mappers.trade_mapper import TradeMapper
from app.infrastructure.models.trade_model import TradeModel
from app.infrastructure.unit_of_work import UnitOfWork


class SearchTradesUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, query: str, user_id: int = 0):
        if not query or not query.strip():
            return []
        pattern = f"%{query.strip()}%"
        async with self.uow:
            stmt = select(TradeModel).where(
                TradeModel.coin.ilike(pattern)
                | TradeModel.buy_exchange.ilike(pattern)
                | TradeModel.sell_exchange.ilike(pattern)
                | TradeModel.strategy.ilike(pattern)
                | TradeModel.note.ilike(pattern)
            )
            if user_id:
                stmt = stmt.where(TradeModel.telegram_user_id == user_id)
            stmt = stmt.order_by(TradeModel.created_at.desc())
            result = await self.uow.session.execute(stmt)
            return [
                TradeMapper.to_entity(model)
                for model in result.scalars().all()
            ]
