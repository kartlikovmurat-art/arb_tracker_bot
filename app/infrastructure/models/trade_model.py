from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType
from app.infrastructure.base import Base


class TradeModel(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)

    coin: Mapped[str] = mapped_column(String(20))

    buy_exchange: Mapped[str] = mapped_column(String(50))
    sell_exchange: Mapped[str] = mapped_column(String(50))

    amount: Mapped[Decimal] = mapped_column(Numeric(28, 12))

    buy_price: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    sell_price: Mapped[Decimal] = mapped_column(Numeric(28, 12))

    buy_fee: Mapped[Decimal] = mapped_column(Numeric(28, 12), default=0)
    sell_fee: Mapped[Decimal] = mapped_column(Numeric(28, 12), default=0)
    withdrawal_fee: Mapped[Decimal] = mapped_column(Numeric(28, 12), default=0)
    gas_fee: Mapped[Decimal] = mapped_column(Numeric(28, 12), default=0)
    slippage: Mapped[Decimal] = mapped_column(Numeric(28, 12), default=0)

    profit: Mapped[Decimal] = mapped_column(Numeric(28, 12), default=0)
    roi: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    trade_type: Mapped[TradeType] = mapped_column(Enum(TradeType))
    status: Mapped[TradeStatus] = mapped_column(Enum(TradeStatus))

    strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())