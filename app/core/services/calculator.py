from decimal import Decimal

from app.core.entities.trade import Trade


def calculate_profit(trade: Trade) -> Decimal:
    income = trade.sell_price * trade.amount

    expenses = (
        trade.buy_price * trade.amount
        + trade.buy_fee
        + trade.sell_fee
        + trade.withdrawal_fee
        + trade.gas_fee
        + trade.slippage
    )

    return income - expenses


def calculate_roi(trade: Trade) -> Decimal:
    invested = (
        trade.buy_price * trade.amount
        + trade.buy_fee
        + trade.withdrawal_fee
        + trade.gas_fee
        + trade.slippage
    )

    if invested == Decimal("0"):
        return Decimal("0")

    return (
        calculate_profit(trade) / invested
    ) * Decimal("100")


def update_trade_result(trade: Trade) -> Trade:
    trade.profit = calculate_profit(trade)
    trade.roi = calculate_roi(trade)

    return trade


class TradeCalculator:
    """Compatibility wrapper used by use-cases.

    Provides a `calculate(trade)` API expected elsewhere in the codebase.
    """

    @staticmethod
    def calculate(trade: Trade) -> Trade:
        return update_trade_result(trade)