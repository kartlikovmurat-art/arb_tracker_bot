from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import current_user_id
from app.application.use_cases.export_trades_to_excel import (
    ExportTradesToExcelUseCase,
)
from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


router = APIRouter(prefix="/export", tags=["Export"])


async def get_session():
    async with async_session() as session:
        yield session


@router.get("/excel")
async def export_excel(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    use_case = ExportTradesToExcelUseCase(UnitOfWork(session))
    stream = await use_case.execute(user_id=user_id)
    return StreamingResponse(
        stream,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": 'attachment; filename="trades.xlsx"'},
    )
