from collections import defaultdict
from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetDailyStatisticsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self):
        async with self.uow:
            trades = await self.uow.trades.get_all()

        statistics = defaultdict(
            lambda: {
                "trades": 0,
                "profit": Decimal("0"),
                "volume": Decimal("0"),
                "average_roi": Decimal("0"),
                "roi_sum": Decimal("0"),
            }
        )

        for trade in trades:

            if trade.status != TradeStatus.COMPLETED:
                continue

            day = trade.created_at.strftime("%Y-%m-%d")

            statistics[day]["trades"] += 1
            statistics[day]["profit"] += trade.profit
            statistics[day]["volume"] += trade.amount
            statistics[day]["roi_sum"] += trade.roi

        result = {}

        for day in sorted(statistics.keys()):

            data = statistics[day]

            if data["trades"] > 0:
                data["average_roi"] = (
                    data["roi_sum"] / data["trades"]
                ).quantize(
                    Decimal("0.01")
                )

            del data["roi_sum"]

            result[day] = data

        return result