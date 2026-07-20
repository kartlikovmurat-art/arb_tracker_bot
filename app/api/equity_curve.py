from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.get_equity_curve import (
    GetEquityCurveUseCase,
)
from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


router = APIRouter(
    prefix="/statistics/equity",
    tags=["Statistics"],
)


async def get_session():
    async with async_session() as session:
        yield session


@router.get("/")
async def get_equity_curve(
    session: AsyncSession = Depends(get_session),
):
    use_case = GetEquityCurveUseCase(
        UnitOfWork(session)
    )

    return await use_case.execute()