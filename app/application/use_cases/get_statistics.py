from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetStatisticsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, user_id: int = 0):
        async with self.uow:
            trades = await self.uow.trades.get_all(user_id=user_id)

        total = len(trades)

        completed = [t for t in trades if t.status == TradeStatus.COMPLETED]
        pending = [t for t in trades if t.status == TradeStatus.PENDING]
        cancelled = [t for t in trades if t.status == TradeStatus.CANCELLED]

        total_profit = sum((t.profit for t in completed), Decimal("0"))
        average_roi = Decimal("0")
        if completed:
            average_roi = (
                sum((t.roi for t in completed), Decimal("0"))
                / Decimal(len(completed))
            )
        profitable = [t for t in completed if t.profit > 0]
        losing = [t for t in completed if t.profit < 0]
        win_rate = Decimal("0")
        if completed:
            win_rate = (Decimal(len(profitable)) / Decimal(len(completed))) * Decimal("100")

        return {
            "total_trades": total,
            "completed_trades": len(completed),
            "pending_trades": len(pending),
            "cancelled_trades": len(cancelled),
            "profitable_trades": len(profitable),
            "losing_trades": len(losing),
            "total_profit": total_profit,
            "average_roi": average_roi.quantize(Decimal("0.01")),
            "win_rate": win_rate.quantize(Decimal("0.01")),
        }
