from app.application.dto import CreateTradeDTO
from app.application.factories import TradeFactory
from app.infrastructure.unit_of_work import UnitOfWork


class TradeService:
    """
    Legacy service.

    Оставлен только для совместимости.
    Новый код должен использовать Use Cases.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_trade(self, dto: CreateTradeDTO):
        trade = TradeFactory.create(dto)

        async with self.uow:
            return await self.uow.trades.add(trade)