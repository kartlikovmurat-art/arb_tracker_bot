import asyncio
from decimal import Decimal
import pytest

try:
    import greenlet  # type: ignore
    _HAS_GREENLET = True
except Exception:
    _HAS_GREENLET = False

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine

from app.infrastructure.base import Base
from app.infrastructure.models.trade_model import TradeModel
from app.infrastructure.repositories.trade_repository import TradeRepository
from app.core.entities.trade import Trade
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType


async def setup_db(db_url: str):
    # Create tables synchronously first to avoid greenlet requirement during metadata.create_all
    sync_url = db_url.replace("+aiosqlite", "")
    sync_engine = create_engine(sync_url, echo=False)
    Base.metadata.create_all(bind=sync_engine)

    engine = create_async_engine(db_url, echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_maker


@pytest.mark.skipif(not _HAS_GREENLET, reason="greenlet not available in environment")
def test_repository_crud(tmp_path):
    db_file = tmp_path / "test_repo.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    async def run():
        engine, session_maker = await setup_db(db_url)

        async with session_maker() as session:
            repo = TradeRepository(session)

            trade = Trade(
                coin="ETH",
                buy_exchange="Binance",
                sell_exchange="Bybit",
                amount=Decimal("1"),
                buy_price=Decimal("2000"),
                sell_price=Decimal("2100"),
                trade_type=TradeType.CEX_CEX,
                status=TradeStatus.PENDING,
            )

            created = await repo.add(trade)
            assert created.id is not None

            found = await repo.get_by_id(created.id)
            assert found is not None
            assert found.coin == "ETH"

            all_trades = await repo.get_all()
            assert len(all_trades) >= 1

            # update
            trade.note = "test note"
            updated = await repo.update(created.id, trade)
            assert updated.note == "test note"

            # delete
            await repo.delete(created.id)
            after = await repo.get_by_id(created.id)
            assert after is None

    asyncio.run(run())
