from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.trade import Trade
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType
from app.infrastructure.mappers.trade_mapper import TradeMapper
from app.infrastructure.models.trade_model import TradeModel


class TradeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, trade: Trade) -> Trade:
        model = TradeMapper.to_model(trade)

        self.session.add(model)

        await self.session.commit()
        await self.session.refresh(model)

        return TradeMapper.to_entity(model)

    async def get_by_id(self, trade_id: int) -> Trade | None:
        result = await self.session.execute(
            select(TradeModel).where(
                TradeModel.id == trade_id
            )
        )

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return TradeMapper.to_entity(model)

    async def get_all(self) -> list[Trade]:
        result = await self.session.execute(
            select(TradeModel)
        )

        return [
            TradeMapper.to_entity(model)
            for model in result.scalars().all()
        ]

    async def filter(
        self,
        coin: str | None = None,
        exchange: str | None = None,
        status: TradeStatus | None = None,
        trade_type: TradeType | None = None,
    ) -> list[Trade]:

        query = select(TradeModel)

        if coin:
            query = query.where(
                TradeModel.coin.ilike(f"%{coin}%")
            )

        if exchange:
            query = query.where(
                or_(
                    TradeModel.buy_exchange.ilike(f"%{exchange}%"),
                    TradeModel.sell_exchange.ilike(f"%{exchange}%"),
                )
            )

        if status:
            query = query.where(
                TradeModel.status == status
            )

        if trade_type:
            query = query.where(
                TradeModel.trade_type == trade_type
            )

        result = await self.session.execute(query)

        return [
            TradeMapper.to_entity(model)
            for model in result.scalars().all()
        ]

    async def update(
        self,
        trade_id: int,
        trade: Trade,
    ) -> Trade | None:

        result = await self.session.execute(
            select(TradeModel).where(
                TradeModel.id == trade_id
            )
        )

        model = result.scalar_one_or_none()

        if model is None:
            return None

        model.coin = trade.coin
        model.buy_exchange = trade.buy_exchange
        model.sell_exchange = trade.sell_exchange

        model.amount = trade.amount

        model.buy_price = trade.buy_price
        model.sell_price = trade.sell_price

        model.buy_fee = trade.buy_fee
        model.sell_fee = trade.sell_fee
        model.withdrawal_fee = trade.withdrawal_fee
        model.gas_fee = trade.gas_fee
        model.slippage = trade.slippage

        model.trade_type = trade.trade_type
        model.status = trade.status

        model.strategy = trade.strategy
        model.note = trade.note

        model.profit = trade.profit
        model.roi = trade.roi

        await self.session.commit()
        await self.session.refresh(model)

        return TradeMapper.to_entity(model)

    async def delete(self, trade_id: int) -> None:
        result = await self.session.execute(
            select(TradeModel).where(
                TradeModel.id == trade_id
            )
        )

        model = result.scalar_one_or_none()

        if model is None:
            return

        await self.session.delete(model)
        await self.session.commit()