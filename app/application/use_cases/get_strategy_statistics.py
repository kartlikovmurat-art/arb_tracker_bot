from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetStrategyStatisticsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self):
        async with self.uow:
            trades = await self.uow.trades.get_all()

        statistics = {}

        for trade in trades:

            if trade.status != TradeStatus.COMPLETED:
                continue

            strategy = trade.strategy or "Unknown"

            if strategy not in statistics:
                statistics[strategy] = {
                    "trades": 0,
                    "profit": Decimal("0"),
                    "average_roi": Decimal("0"),
                    "roi_sum": Decimal("0"),
                    "volume": Decimal("0"),
                }

            statistics[strategy]["trades"] += 1
            statistics[strategy]["profit"] += trade.profit
            statistics[strategy]["roi_sum"] += trade.roi
            statistics[strategy]["volume"] += trade.amount

        for strategy in statistics.values():

            if strategy["trades"] > 0:
                strategy["average_roi"] = (
                    strategy["roi_sum"]
                    / strategy["trades"]
                ).quantize(
                    Decimal("0.01")
                )

            del strategy["roi_sum"]

        return statistics