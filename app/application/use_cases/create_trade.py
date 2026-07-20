from app.core.entities.trade import Trade
from app.core.services.calculator import TradeCalculator
from app.infrastructure.unit_of_work import UnitOfWork


class CreateTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, trade: Trade) -> Trade:
        trade = TradeCalculator.calculate(trade)

        async with self.uow:
            created = await self.uow.trades.add(trade)
            return created