from decimal import Decimal

from app.core.entities.trade import Trade
from app.infrastructure.models.trade_model import TradeModel


class TradeMapper:

    @staticmethod
    def to_model(trade: Trade) -> TradeModel:
        return TradeModel(
            coin=trade.coin,
            buy_exchange=trade.buy_exchange,
            sell_exchange=trade.sell_exchange,
            amount=Decimal(trade.amount),
            buy_price=Decimal(trade.buy_price),
            sell_price=Decimal(trade.sell_price),
            buy_fee=Decimal(trade.buy_fee),
            sell_fee=Decimal(trade.sell_fee),
            withdrawal_fee=Decimal(trade.withdrawal_fee),
            gas_fee=Decimal(trade.gas_fee),
            slippage=Decimal(trade.slippage),
            profit=Decimal(trade.profit),
            roi=Decimal(trade.roi),
            trade_type=trade.trade_type,
            status=trade.status,
            strategy=trade.strategy,
            note=trade.note,
            created_at=trade.created_at,
            telegram_user_id=trade.telegram_user_id,
            transfer_network=trade.transfer_network,
            holding_time_seconds=trade.holding_time_seconds,
        )

    @staticmethod
    def to_entity(model: TradeModel) -> Trade:
        return Trade(
            coin=model.coin,
            buy_exchange=model.buy_exchange,
            sell_exchange=model.sell_exchange,
            amount=Decimal(model.amount),
            buy_price=Decimal(model.buy_price),
            sell_price=Decimal(model.sell_price),
            buy_fee=Decimal(model.buy_fee),
            sell_fee=Decimal(model.sell_fee),
            withdrawal_fee=Decimal(model.withdrawal_fee),
            gas_fee=Decimal(model.gas_fee),
            slippage=Decimal(model.slippage),
            profit=Decimal(model.profit),
            roi=Decimal(model.roi),
            trade_type=model.trade_type,
            status=model.status,
            strategy=model.strategy,
            note=model.note,
            id=model.id,
            created_at=model.created_at,
            telegram_user_id=model.telegram_user_id or 0,
            transfer_network=model.transfer_network,
            holding_time_seconds=model.holding_time_seconds,
        )