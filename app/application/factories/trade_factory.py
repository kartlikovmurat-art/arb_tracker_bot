from datetime import datetime, timezone

from app.application.dto import CreateTradeDTO
from app.core.entities.trade import Trade


class TradeFactory:

    @staticmethod
    def create(dto: CreateTradeDTO) -> Trade:
        return Trade(
            coin=dto.coin,
            buy_exchange=dto.buy_exchange,
            sell_exchange=dto.sell_exchange,
            amount=dto.amount,
            buy_price=dto.buy_price,
            sell_price=dto.sell_price,
            buy_fee=dto.buy_fee,
            sell_fee=dto.sell_fee,
            withdrawal_fee=dto.withdrawal_fee,
            gas_fee=dto.gas_fee,
            slippage=dto.slippage,
            trade_type=dto.trade_type,
            status=dto.status,
            strategy=dto.strategy,
            note=dto.note,
            created_at=datetime.now(timezone.utc),
        )