from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.trade import Trade
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType
from app.infrastructure.mappers.trade_mapper import TradeMapper
from app.infrastructure.models.trade_model import TradeModel


class TradeRepository:
    """
    Репозиторий сделок.

    С версии user-scope все методы, кроме ``add``, принимают
    ``user_id`` — telegram user id владельца. ``0`` означает
    «любой пользователь» (используется для админских задач и
    для легаси-данных, где владелец неизвестен).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, trade: Trade) -> Trade:
        model = TradeMapper.to_model(trade)

        self.session.add(model)

        await self.session.commit()
        await self.session.refresh(model)

        return TradeMapper.to_entity(model)

    async def get_by_id(self, trade_id: int, user_id: int = 0) -> Trade | None:
        """
        Возвращает сделку, только если она принадлежит ``user_id``
        (или ``user_id == 0`` — админ/легаси).
        """
        query = select(TradeModel).where(TradeModel.id == trade_id)
        if user_id:
            query = query.where(TradeModel.telegram_user_id == user_id)

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return TradeMapper.to_entity(model)

    async def get_all(self, user_id: int = 0) -> list[Trade]:
        """Все сделки конкретного пользователя (или все при user_id=0)."""
        query = select(TradeModel)
        if user_id:
            query = query.where(TradeModel.telegram_user_id == user_id)

        result = await self.session.execute(query)
        return [TradeMapper.to_entity(m) for m in result.scalars().all()]

    async def filter(
        self,
        user_id: int = 0,
        coin: str | None = None,
        exchange: str | None = None,
        status: TradeStatus | None = None,
        trade_type: TradeType | None = None,
    ) -> list[Trade]:
        query = select(TradeModel)
        if user_id:
            query = query.where(TradeModel.telegram_user_id == user_id)
        if coin:
            query = query.where(TradeModel.coin.ilike(f"%{coin}%"))
        if exchange:
            query = query.where(
                or_(
                    TradeModel.buy_exchange.ilike(f"%{exchange}%"),
                    TradeModel.sell_exchange.ilike(f"%{exchange}%"),
                )
            )
        if status:
            query = query.where(TradeModel.status == status)
        if trade_type:
            query = query.where(TradeModel.trade_type == trade_type)

        result = await self.session.execute(query)
        return [TradeMapper.to_entity(m) for m in result.scalars().all()]

    async def update(
        self,
        trade_id: int,
        trade: Trade,
        user_id: int = 0,
    ) -> Trade | None:
        query = select(TradeModel).where(TradeModel.id == trade_id)
        if user_id:
            query = query.where(TradeModel.telegram_user_id == user_id)

        result = await self.session.execute(query)
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

    async def delete(self, trade_id: int, user_id: int = 0) -> bool:
        """Возвращает True, если удалили; False, если не нашли."""
        query = select(TradeModel).where(TradeModel.id == trade_id)
        if user_id:
            query = query.where(TradeModel.telegram_user_id == user_id)

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        await self.session.delete(model)
        await self.session.commit()
        return True
