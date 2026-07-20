from decimal import Decimal

from app.core.entities.trade import Trade
from app.core.services.calculator import update_trade_result


def test_trade_calculation():

    trade = Trade(
        coin="BTC",

        buy_exchange="Binance",
        sell_exchange="Bybit",

        amount=Decimal("0.5"),

        buy_price=Decimal("60000"),
        sell_price=Decimal("62000"),

        buy_fee=Decimal("10"),
        sell_fee=Decimal("10"),
        withdrawal_fee=Decimal("20"),
        gas_fee=Decimal("5"),
        slippage=Decimal("5"),
    )

    update_trade_result(trade)

    print("Profit:", trade.profit)
    print("ROI:", trade.roi)


if __name__ == "__main__":
    test_trade_calculation()