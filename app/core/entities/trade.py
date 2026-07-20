from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType


@dataclass
class Trade:
    """
    Доменная сущность арбитражной сделки.
    """

    coin: str

    buy_exchange: str
    sell_exchange: str

    amount: Decimal

    buy_price: Decimal
    sell_price: Decimal

    trade_type: TradeType = TradeType.CEX_CEX
    status: TradeStatus = TradeStatus.PENDING

    buy_fee: Decimal = Decimal("0")
    sell_fee: Decimal = Decimal("0")
    withdrawal_fee: Decimal = Decimal("0")
    gas_fee: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")

    # Сеть перевода между биржами: ERC20, TRC20, BEP20, BTC,
    # Arbitrum, TON, Internal (внутри одной биржи) и т.д.
    transfer_network: Optional[str] = None

    # Сколько секунд между покупкой и продажей. Если сделка ещё
    # PENDING — None; заполняется при complete().
    holding_time_seconds: Optional[int] = None

    strategy: Optional[str] = None
    note: Optional[str] = None

    id: Optional[int] = None

    # Telegram user id владельца сделки. 0 — анонимный / legacy.
    telegram_user_id: int = 0

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    profit: Decimal = Decimal("0")
    roi: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Количество должно быть больше 0.")

        if self.buy_price <= 0:
            raise ValueError("Цена покупки должна быть больше 0.")

        if self.sell_price <= 0:
            raise ValueError("Цена продажи должна быть больше 0.")

        if self.telegram_user_id < 0:
            raise ValueError("telegram_user_id не может быть отрицательным.")

    @property
    def investment(self) -> Decimal:
        return self.amount * self.buy_price

    @property
    def revenue(self) -> Decimal:
        return self.amount * self.sell_price

    @property
    def total_fees(self) -> Decimal:
        return (
            self.buy_fee
            + self.sell_fee
            + self.withdrawal_fee
            + self.gas_fee
            + self.slippage
        )

    @property
    def holding_time_human(self) -> str:
        """Красиво отформатированное время удержания сделки.

        Возвращает «5 мин», «2 ч 15 мин», «3 д 4 ч» или «—»,
        если время неизвестно.
        """
        secs = self.holding_time_seconds
        if secs is None or secs <= 0:
            return "—"
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days > 0:
            return f"{days} д {hours} ч"
        if hours > 0:
            return f"{hours} ч {minutes} мин"
        if minutes > 0:
            return f"{minutes} мин"
        return f"{secs} сек"

    def complete(self) -> None:
        self.status = TradeStatus.COMPLETED

    def cancel(self) -> None:
        self.status = TradeStatus.CANCELLED

    def is_profitable(self) -> bool:
        return self.profit > Decimal("0")