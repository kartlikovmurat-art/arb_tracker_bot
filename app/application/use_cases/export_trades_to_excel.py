from io import BytesIO

from app.core.services.excel_export_service import (
    ExcelExportService,
)
from app.infrastructure.unit_of_work import UnitOfWork


class ExportTradesToExcelUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, user_id: int = 0) -> BytesIO:
        async with self.uow:
            trades = await self.uow.trades.get_all(user_id=user_id)
        return ExcelExportService.export(trades)
