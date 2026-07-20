from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.get_coin_statistics import (
    GetCoinStatisticsUseCase,
)
from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


router = APIRouter(
    prefix="/statistics/coins",
    tags=["Statistics"],
)


async def get_session():
    async with async_session() as session:
        yield session


@router.get("/")
async def get_coin_statistics(
    session: AsyncSession = Depends(get_session),
):
    use_case = GetCoinStatisticsUseCase(
        UnitOfWork(session)
    )

    return await use_case.execute()