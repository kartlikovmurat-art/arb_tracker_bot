from collections import defaultdict
from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetMonthlyStatisticsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, user_id: int = 0):
        async with self.uow:
            trades = await self.uow.trades.get_all(user_id=user_id)

        statistics = defaultdict(lambda: {
            "trades": 0,
            "profit": Decimal("0"),
            "volume": Decimal("0"),
            "average_roi": Decimal("0"),
            "roi_sum": Decimal("0"),
        })

        for trade in trades:
            if trade.status != TradeStatus.COMPLETED:
                continue
            month = trade.created_at.strftime("%Y-%m")
            statistics[month]["trades"] += 1
            statistics[month]["profit"] += trade.profit
            statistics[month]["volume"] += trade.amount
            statistics[month]["roi_sum"] += trade.roi

        result = {}
        for month in sorted(statistics.keys()):
            data = statistics[month]
            if data["trades"] > 0:
                data["average_roi"] = (
                    data["roi_sum"] / data["trades"]
                ).quantize(Decimal("0.01"))
            del data["roi_sum"]
            result[month] = data
        return result
