from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import current_user_id
from app.application.dto.trade_request import TradeRequest
from app.application.dto.trade_response import TradeResponse
from app.application.factories.trade_factory import TradeFactory

from app.application.use_cases.create_trade import CreateTradeUseCase
from app.application.use_cases.delete_trade import DeleteTradeUseCase
from app.application.use_cases.filter_trades import FilterTradesUseCase
from app.application.use_cases.get_all_trades import GetAllTradesUseCase
from app.application.use_cases.get_trade import GetTradeUseCase
from app.application.use_cases.update_trade import UpdateTradeUseCase

from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType

from app.infrastructure.database import async_session
from app.infrastructure.unit_of_work import UnitOfWork


router = APIRouter(
    prefix="/trades",
    tags=["Trades"],
)


async def get_session():
    async with async_session() as session:
        yield session


@router.post("/", response_model=TradeResponse)
async def create_trade(
    request: TradeRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    # Если client не прислал telegram_user_id в body, берём из header.
    if not request.telegram_user_id and user_id:
        request = request.model_copy(update={"telegram_user_id": user_id})
    dto = request.to_dto()
    trade = TradeFactory.create(dto)

    use_case = CreateTradeUseCase(UnitOfWork(session))
    return await use_case.execute(trade)


@router.get("/", response_model=list[TradeResponse])
async def get_all_trades(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    use_case = GetAllTradesUseCase(UnitOfWork(session))
    return await use_case.execute(user_id=user_id)


@router.get("/filter", response_model=list[TradeResponse])
async def filter_trades(
    coin: str | None = None,
    exchange: str | None = None,
    status: TradeStatus | None = None,
    trade_type: TradeType | None = None,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    use_case = FilterTradesUseCase(UnitOfWork(session))
    return await use_case.execute(
        user_id=user_id,
        coin=coin,
        exchange=exchange,
        status=status,
        trade_type=trade_type,
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    use_case = GetTradeUseCase(UnitOfWork(session))
    trade = await use_case.execute(trade_id, user_id=user_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    request: TradeRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    if not request.telegram_user_id and user_id:
        request = request.model_copy(update={"telegram_user_id": user_id})
    dto = request.to_dto()
    trade = TradeFactory.create(dto)

    use_case = UpdateTradeUseCase(UnitOfWork(session))
    updated = await use_case.execute(trade_id, trade, user_id=user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return updated


@router.delete("/{trade_id}")
async def delete_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(current_user_id),
):
    use_case = DeleteTradeUseCase(UnitOfWork(session))
    deleted = await use_case.execute(trade_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"message": "Trade deleted"}
