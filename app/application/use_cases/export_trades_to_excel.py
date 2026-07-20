from io import BytesIO
# Fixed import path to core.services.ExcelExportService

from app.core.services.excel_export_service import (
    ExcelExportService,
)
from app.infrastructure.unit_of_work import UnitOfWork


class ExportTradesToExcelUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> BytesIO:
        async with self.uow:
            trades = await self.uow.trades.get_all()

        return ExcelExportService.export(trades)