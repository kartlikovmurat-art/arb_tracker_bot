from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.application.dto.create_trade_dto import CreateTradeDTO
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType


class TradeRequest(BaseModel):
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

    transfer_network: Optional[str] = None
    holding_time_seconds: Optional[int] = None

    trade_type: TradeType = TradeType.CEX_CEX
    status: TradeStatus = TradeStatus.PENDING

    strategy: Optional[str] = None
    note: Optional[str] = None

    # Telegram user id. Если не указан — берётся из X-Telegram-User-Id
    # header в API, либо 0 (legacy).
    telegram_user_id: int = 0

    def to_dto(self) -> CreateTradeDTO:
        return CreateTradeDTO(
            coin=self.coin,
            buy_exchange=self.buy_exchange,
            sell_exchange=self.sell_exchange,
            amount=self.amount,
            buy_price=self.buy_price,
            sell_price=self.sell_price,
            buy_fee=self.buy_fee,
            sell_fee=self.sell_fee,
            withdrawal_fee=self.withdrawal_fee,
            gas_fee=self.gas_fee,
            slippage=self.slippage,
            transfer_network=self.transfer_network,
            holding_time_seconds=self.holding_time_seconds,
            trade_type=self.trade_type,
            status=self.status,
            strategy=self.strategy,
            note=self.note,
            telegram_user_id=self.telegram_user_id,
        )