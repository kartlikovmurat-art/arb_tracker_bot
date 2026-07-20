from app.core.entities.trade import Trade
from app.core.services.calculator import TradeCalculator
from app.infrastructure.unit_of_work import UnitOfWork


class UpdateTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(
        self,
        trade_id: int,
        trade: Trade,
        user_id: int = 0,
    ) -> Trade | None:
        trade = TradeCalculator.calculate(trade)

        async with self.uow:
            updated = await self.uow.trades.update(
                trade_id,
                trade,
                user_id=user_id,
            )
            return updated
