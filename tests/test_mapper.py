from decimal import Decimal

from app.core.entities.trade import Trade
from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType
from app.infrastructure.mappers.trade_mapper import TradeMapper


def test_trade_mapper_entity_to_model_and_back():
    trade = Trade(
        coin="BTC",
        buy_exchange="Binance",
        sell_exchange="Bybit",
        amount=Decimal("0.5"),
        buy_price=Decimal("60000"),
        sell_price=Decimal("62000"),
        trade_type=TradeType.CEX_CEX,
        status=TradeStatus.PENDING,
    )

    model = TradeMapper.to_model(trade)

    # ensure model fields exist and are Decimal-like via str()
    assert str(model.amount).startswith("0.5")
    assert str(model.buy_price).startswith("60000")

    entity = TradeMapper.to_entity(model)

    assert entity.coin == trade.coin
    assert entity.buy_exchange == trade.buy_exchange
    assert entity.sell_exchange == trade.sell_exchange
    assert entity.amount == trade.amount
    assert entity.buy_price == trade.buy_price
