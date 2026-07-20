from app.infrastructure.unit_of_work import UnitOfWork


class DeleteTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, trade_id: int, user_id: int = 0) -> bool:
        async with self.uow:
            return await self.uow.trades.delete(trade_id, user_id=user_id)
