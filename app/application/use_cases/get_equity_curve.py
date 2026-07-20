from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetEquityCurveUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, user_id: int = 0):
        async with self.uow:
            trades = await self.uow.trades.get_all(user_id=user_id)

        completed = sorted(
            (t for t in trades if t.status == TradeStatus.COMPLETED),
            key=lambda t: t.created_at,
        )

        equity = Decimal("0")
        result = []
        for trade in completed:
            equity += trade.profit
            result.append({
                "date": trade.created_at.isoformat(),
                "trade_id": trade.id,
                "coin": trade.coin,
                "profit": trade.profit,
                "equity": equity,
            })
        return result
