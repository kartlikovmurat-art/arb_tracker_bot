from app.core.entities.trade import Trade
from app.infrastructure.unit_of_work import UnitOfWork


class GetAllTradesUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> list[Trade]:
        async with self.uow:
            return await self.uow.trades.get_all()