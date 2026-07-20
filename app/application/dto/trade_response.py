from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType


class TradeResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda value: format(value.normalize(), 'f'),
            datetime: lambda value: value.isoformat(),
        },
    )

    id: Optional[int] = None
    coin: str
    buy_exchange: str
    sell_exchange: str
    amount: Decimal
    buy_price: Decimal
    sell_price: Decimal
    buy_fee: Decimal
    sell_fee: Decimal
    withdrawal_fee: Decimal
    gas_fee: Decimal
    slippage: Decimal
    profit: Decimal
    roi: Decimal
    trade_type: TradeType
    status: TradeStatus
    strategy: Optional[str] = None
    note: Optional[str] = None
    telegram_user_id: int = 0
    created_at: datetime
