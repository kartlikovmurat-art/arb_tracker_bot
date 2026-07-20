from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType


class CreateTradeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coin: str

    buy_exchange: str
    sell_exchange: str

    amount: Decimal

    buy_price: Decimal
    sell_price: Decimal

    # Старые поля (deprecated) — оставлены для обратной совместимости.
    # Если указаны buy_fee/sell_fee — используются как есть.
    buy_fee: Decimal = Decimal("0")
    sell_fee: Decimal = Decimal("0")
    withdrawal_fee: Decimal = Decimal("0")
    gas_fee: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")

    # Новые входные поля.
    buy_fee_percent: Decimal = Decimal("0")
    sell_fee_percent: Decimal = Decimal("0")
    network_fee: Decimal = Decimal("0")
    transfer_network: Optional[str] = None
    bought_at: Optional[datetime] = None
    sold_at: Optional[datetime] = None

    # Legacy: явное время удержания (если оба времени не заданы).
    holding_time_seconds: Optional[int] = None

    trade_type: TradeType = TradeType.CEX_CEX
    status: TradeStatus = TradeStatus.PENDING

    strategy: Optional[str] = None
    note: Optional[str] = None

    # Telegram user id владельца. По умолчанию 0 (legacy).
    telegram_user_id: int = 0