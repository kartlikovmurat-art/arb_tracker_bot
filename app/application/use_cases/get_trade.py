from app.core.entities.trade import Trade
from app.infrastructure.unit_of_work import UnitOfWork


class GetTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, trade_id: int, user_id: int = 0) -> Trade | None:
        async with self.uow:
            return await self.uow.trades.get_by_id(trade_id, user_id=user_id)
