import logging

from app.core.entities.trade import Trade
from app.core.services.calculator import TradeCalculator
from app.infrastructure.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class CreateTradeUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, trade: Trade) -> Trade:
        logger.info("CREATE TRADE: calculation started")

        trade = TradeCalculator.calculate(trade)

        logger.info("CREATE TRADE: repository.add started")

        async with self.uow:
            created = await self.uow.trades.add(trade)

            logger.info("CREATE TRADE: repository.add finished")

            # Принудительно отправляем INSERT в PostgreSQL.
            # Если проблема именно в INSERT, теперь она будет
            # видна в логах FastAPI, а не превратится в Telegram timeout.
            await self.uow.session.flush()

            logger.info(
                "CREATE TRADE: flush finished, id=%s",
                getattr(created, "id", None),
            )

            return created
