from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


async def get_session():
    async with async_session() as session:
        yield session


def get_uow(session: AsyncSession) -> UnitOfWork:
    return UnitOfWork(session)