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

    buy_fee: Decimal = Decimal("0")
    sell_fee: Decimal = Decimal("0")
    withdrawal_fee: Decimal = Decimal("0")
    gas_fee: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")

    trade_type: TradeType = TradeType.CEX_CEX
    status: TradeStatus = TradeStatus.PENDING

    strategy: Optional[str] = None
    note: Optional[str] = None