"""Полнотекстовый поиск по сделкам.

Ищет подстроку в coin, buy_exchange, sell_exchange, strategy, note.
Возвращает все совпадения, отсортированные по дате (новые первые).
"""
from __future__ import annotations

from sqlalchemy import or_, select

from app.infrastructure.models.trade_model import TradeModel
from app.infrastructure.unit_of_work import UnitOfWork


class SearchTradesUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, query: str):
        if not query or not query.strip():
            return []
        pattern = f"%{query.strip()}%"
        async with self.uow:
            stmt = select(TradeModel).where(
                or_(
                    TradeModel.coin.ilike(pattern),
                    TradeModel.buy_exchange.ilike(pattern),
                    TradeModel.sell_exchange.ilike(pattern),
                    TradeModel.strategy.ilike(pattern),
                    TradeModel.note.ilike(pattern),
                )
            ).order_by(TradeModel.created_at.desc())
            from app.infrastructure.mappers.trade_mapper import TradeMapper
            result = await self.uow.session.execute(stmt)
            return [
                TradeMapper.to_entity(model)
                for model in result.scalars().all()
            ]
