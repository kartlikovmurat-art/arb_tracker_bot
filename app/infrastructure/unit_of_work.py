from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.trade_repository import TradeRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trades = TradeRepository(session)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
