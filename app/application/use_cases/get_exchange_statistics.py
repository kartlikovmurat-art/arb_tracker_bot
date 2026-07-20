from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetExchangeStatisticsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self):
        async with self.uow:
            trades = await self.uow.trades.get_all()

        statistics = {}

        for trade in trades:

            if trade.status != TradeStatus.COMPLETED:
                continue

            for exchange in (
                trade.buy_exchange,
                trade.sell_exchange,
            ):

                if exchange not in statistics:
                    statistics[exchange] = {
                        "trades": 0,
                        "profit": Decimal("0"),
                        "average_roi": Decimal("0"),
                        "roi_sum": Decimal("0"),
                    }

                statistics[exchange]["trades"] += 1
                statistics[exchange]["profit"] += trade.profit
                statistics[exchange]["roi_sum"] += trade.roi

        for exchange in statistics.values():
            if exchange["trades"] > 0:
                exchange["average_roi"] = (
                    exchange["roi_sum"]
                    / exchange["trades"]
                ).quantize(
                    Decimal("0.01")
                )

            del exchange["roi_sum"]

        return statistics