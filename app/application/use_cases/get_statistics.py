from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetStatisticsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self):
        async with self.uow:
            trades = await self.uow.trades.get_all()

        total = len(trades)

        completed = [
            trade
            for trade in trades
            if trade.status == TradeStatus.COMPLETED
        ]

        pending = [
            trade
            for trade in trades
            if trade.status == TradeStatus.PENDING
        ]

        cancelled = [
            trade
            for trade in trades
            if trade.status == TradeStatus.CANCELLED
        ]

        total_profit = sum(
            (trade.profit for trade in completed),
            Decimal("0"),
        )

        average_roi = Decimal("0")

        if completed:
            average_roi = (
                sum(
                    (trade.roi for trade in completed),
                    Decimal("0"),
                )
                / Decimal(len(completed))
            )

        profitable = [
            trade
            for trade in completed
            if trade.profit > 0
        ]

        losing = [
            trade
            for trade in completed
            if trade.profit < 0
        ]

        win_rate = Decimal("0")

        if completed:
            win_rate = (
                Decimal(len(profitable))
                / Decimal(len(completed))
            ) * Decimal("100")

        return {
            "total_trades": total,
            "completed_trades": len(completed),
            "pending_trades": len(pending),
            "cancelled_trades": len(cancelled),
            "profitable_trades": len(profitable),
            "losing_trades": len(losing),
            "total_profit": total_profit,
            "average_roi": average_roi.quantize(
                Decimal("0.01")
            ),
            "win_rate": win_rate.quantize(
                Decimal("0.01")
            ),
        }
    