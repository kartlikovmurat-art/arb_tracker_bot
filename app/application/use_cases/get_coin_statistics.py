from decimal import Decimal

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


class GetCoinStatisticsUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, user_id: int = 0):
        async with self.uow:
            trades = await self.uow.trades.get_all(user_id=user_id)

        statistics = {}
        for trade in trades:
            if trade.status != TradeStatus.COMPLETED:
                continue
            coin = trade.coin.upper()
            if coin not in statistics:
                statistics[coin] = {
                    "trades": 0,
                    "profit": Decimal("0"),
                    "average_roi": Decimal("0"),
                    "roi_sum": Decimal("0"),
                    "volume": Decimal("0"),
                }
            statistics[coin]["trades"] += 1
            statistics[coin]["profit"] += trade.profit
            statistics[coin]["roi_sum"] += trade.roi
            statistics[coin]["volume"] += trade.amount

        for coin in statistics.values():
            if coin["trades"] > 0:
                coin["average_roi"] = (
                    coin["roi_sum"] / coin["trades"]
                ).quantize(Decimal("0.01"))
            del coin["roi_sum"]
        return statistics
