"""Расширенные эндпоинты: edit, complete, search, backup, import, equity chart."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.backup_data import (
    ExportBackupUseCase,
    ImportTradesUseCase,
)
from app.application.use_cases.complete_trade import CompleteTradeUseCase
from app.application.use_cases.equity_chart import GenerateEquityChartUseCase
from app.application.use_cases.patch_trade import PatchTradeUseCase
from app.application.use_cases.search_trades import SearchTradesUseCase
from app.application.dto.trade_response import TradeResponse
from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


router = APIRouter(tags=["Extras"])


async def get_session():
    async with async_session() as session:
        yield session


# ── Частичное обновление ────────────────────────────────────────────
@router.patch("/trades/{trade_id}", response_model=TradeResponse)
async def patch_trade(
    trade_id: int,
    updates: dict[str, Any],
    session: AsyncSession = Depends(get_session),
):
    """Меняет только те поля, которые пришли в ``updates``. Пересчитывает P/L."""
    use_case = PatchTradeUseCase(UnitOfWork(session))
    trade = await use_case.execute(trade_id, updates)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


# ── Подтверждение PENDING → COMPLETED ──────────────────────────────
@router.post("/trades/{trade_id}/complete", response_model=TradeResponse)
async def complete_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Переводит сделку в COMPLETED, пересчитывает P/L и ROI."""
    use_case = CompleteTradeUseCase(UnitOfWork(session))
    trade = await use_case.execute(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


# ── Поиск ───────────────────────────────────────────────────────────
@router.get("/trades/search", response_model=list[TradeResponse])
async def search_trades(
    q: str = Query(..., min_length=1, description="поисковый запрос"),
    session: AsyncSession = Depends(get_session),
):
    """Полнотекстовый поиск по coin/exchange/strategy/note."""
    use_case = SearchTradesUseCase(UnitOfWork(session))
    return await use_case.execute(q)


# ── Бэкап ───────────────────────────────────────────────────────────
@router.get("/backup")
async def backup(session: AsyncSession = Depends(get_session)):
    """Возвращает JSON-файл со всеми сделками."""
    use_case = ExportBackupUseCase(UnitOfWork(session))
    payload = await use_case.execute()
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="trades_backup.json"'
        },
    )


# ── Импорт ──────────────────────────────────────────────────────────
@router.post("/import")
async def import_trades(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Принимает JSON-файл (формат /backup) и вставляет сделки,
    пропуская дубликаты по id."""
    content = await file.read()
    try:
        payload = content.decode("utf-8")
        json.loads(payload)  # валидация
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Bad JSON: {exc}")
    use_case = ImportTradesUseCase(UnitOfWork(session))
    inserted, skipped = await use_case.execute(payload)
    return {
        "status": "ok",
        "inserted": inserted,
        "skipped": skipped,
    }


# ── Equity curve график PNG ────────────────────────────────────────
@router.get("/statistics/equity/chart")
async def equity_chart(session: AsyncSession = Depends(get_session)):
    """PNG-картинка с кривой доходности по датам."""
    use_case = GenerateEquityChartUseCase(UnitOfWork(session))
    blob = await use_case.execute()
    return Response(
        content=blob,
        media_type="image/png",
        headers={
            "Content-Disposition": 'inline; filename="equity_curve.png"'
        },
    )
