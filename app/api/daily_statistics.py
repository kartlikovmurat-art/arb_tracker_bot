from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.get_daily_statistics import (
    GetDailyStatisticsUseCase,
)
from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


router = APIRouter(
    prefix="/statistics/daily",
    tags=["Statistics"],
)


async def get_session():
    async with async_session() as session:
        yield session


@router.get("/")
async def get_daily_statistics(
    session: AsyncSession = Depends(get_session),
):
    use_case = GetDailyStatisticsUseCase(
        UnitOfWork(session)
    )

    return await use_case.execute()
