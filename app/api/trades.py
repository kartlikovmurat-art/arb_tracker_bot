from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
):
    dto = request.to_dto()
    trade = TradeFactory.create(dto)

    use_case = CreateTradeUseCase(UnitOfWork(session))

    return await use_case.execute(trade)


@router.get("/", response_model=list[TradeResponse])
async def get_all_trades(
    session: AsyncSession = Depends(get_session),
):
    use_case = GetAllTradesUseCase(UnitOfWork(session))
    return await use_case.execute()


@router.get("/filter", response_model=list[TradeResponse])
async def filter_trades(
    coin: str | None = None,
    exchange: str | None = None,
    status: TradeStatus | None = None,
    trade_type: TradeType | None = None,
    session: AsyncSession = Depends(get_session),
):
    use_case = FilterTradesUseCase(UnitOfWork(session))

    return await use_case.execute(
        coin=coin,
        exchange=exchange,
        status=status,
        trade_type=trade_type,
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_session),
):
    use_case = GetTradeUseCase(UnitOfWork(session))

    trade = await use_case.execute(trade_id)

    if trade is None:
        raise HTTPException(
            status_code=404,
            detail="Trade not found",
        )

    return trade


@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    request: TradeRequest,
    session: AsyncSession = Depends(get_session),
):
    dto = request.to_dto()
    trade = TradeFactory.create(dto)

    use_case = UpdateTradeUseCase(UnitOfWork(session))

    updated = await use_case.execute(
        trade_id,
        trade,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Trade not found",
        )

    return updated


@router.delete("/{trade_id}")
async def delete_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_session),
):
    use_case = DeleteTradeUseCase(UnitOfWork(session))

    await use_case.execute(trade_id)

    return {
        "message": "Trade deleted"
    }