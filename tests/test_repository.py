import asyncio
from decimal import Decimal

from app.core.entities.trade import Trade
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType
from app.infrastructure.database import async_session
from app.infrastructure.repositories.trade_repository import TradeRepository


async def main():
    async with async_session() as session:
        repository = TradeRepository(session)

        trade = Trade(
            coin="BTC",
            buy_exchange="Binance",
            sell_exchange="Bybit",
            amount=Decimal("0.5"),
            buy_price=Decimal("60000"),
            sell_price=Decimal("62000"),
            trade_type=TradeType.CEX_CEX,
            status=TradeStatus.PENDING,
        )

        created = await repository.add(trade)

        print(created)

        trades = await repository.get_all()

        print(trades)


if __name__ == "__main__":
    asyncio.run(main())