from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import current_user_id
from app.application.use_cases.get_exchange_statistics import (
    GetExchangeStatisticsUseCase,
)
from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


router = APIRouter(prefix="/statistics/exchanges", tags=["Statistics"])


async def get_session():
    async with async_session() as session:
        yield session


@router.get("/")
async def get_exchange_statistics(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    use_case = GetExchangeStatisticsUseCase(UnitOfWork(session))
    return await use_case.execute(user_id=user_id)
