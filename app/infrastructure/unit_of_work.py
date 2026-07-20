from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.trade_repository import TradeRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trades = TradeRepository(session)
        self._transaction = None

    async def __aenter__(self):
        # Use the session directly. Avoid starting an explicit transaction
        # which on some environments triggers a greenlet dependency.
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Commit on success, rollback on error, then close the session.
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