from app.infrastructure.unit_of_work import UnitOfWork


class DeleteTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, trade_id: int) -> None:
        async with self.uow:
            await self.uow.trades.delete(trade_id)