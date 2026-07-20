from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class FilterTradesUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(
        self,
        coin: str | None = None,
        exchange: str |None = None,
        status: TradeStatus | None = None,
    ):
        async with self.uow:
            return await self.uow.trades.filter(
                coin=coin,
                exchange=exchange,
                status=status,
            )