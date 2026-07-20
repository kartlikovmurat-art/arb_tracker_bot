from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Optional

from app.core.value_objects.trade_status import TradeStatus
from app.core.value_objects.trade_type import TradeType


@dataclass
class Trade:
    """
    Доменная сущность арбитражной сделки.

    Поля ввода (что задаёт пользователь):
        * buy_fee_percent, sell_fee_percent — комиссии в % от notional.
        * network_fee — комиссия за вывод + газ, одним числом в USDT.
        * bought_at, sold_at — время покупки/продажи (datetime).
        * slippage — проскальзывание (опц.).

    Поля результата (вычисляются автоматически в recalculate()):
        * buy_fee, sell_fee, withdrawal_fee, gas_fee, holding_time_seconds.
        * profit, roi.

    Связь: ``withdrawal_fee = network_fee``, ``gas_fee = 0`` (объединено).
    """

    coin: str

    buy_exchange: str
    sell_exchange: str

    amount: Decimal

    buy_price: Decimal
    sell_price: Decimal

    trade_type: TradeType = TradeType.CEX_CEX
    status: TradeStatus = TradeStatus.PENDING

    # ── Комиссии (входные) ────────────────────────────────────────
    # Проценты от notional: 0.10 = 0.10 % (как у Binance/Bybit).
    buy_fee_percent: Decimal = Decimal("0")
    sell_fee_percent: Decimal = Decimal("0")
    # Сеть перевода (ERC20/TRC20/...) — выбирается отдельно как строка.
    transfer_network: Optional[str] = None
    # Комиссия за вывод + газ, в USDT (пользователь вводит как удобно).
    network_fee: Decimal = Decimal("0")
    # Проскальзывание (опц.) — в USDT.
    slippage: Decimal = Decimal("0")

    # ── Время ─────────────────────────────────────────────────────
    # Когда купил / продал. Если оба — вычислим holding_time_seconds.
    bought_at: Optional[datetime] = None
    sold_at: Optional[datetime] = None

    # ── Комиссии (вычисляемые) ────────────────────────────────────
    # Для обратной совместимости с TradeMapper/Repository/старыми
    # сделками храним как Decimal в БД.
    buy_fee: Decimal = Decimal("0")
    sell_fee: Decimal = Decimal("0")
    withdrawal_fee: Decimal = Decimal("0")
    gas_fee: Decimal = Decimal("0")
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
        # Один вызов — все производные поля консистентны.
        self.recalculate()

    # ── Производные свойства ──────────────────────────────────────
    @property
    def investment(self) -> Decimal:
        return self.amount * self.buy_price

    @property
    def revenue(self) -> Decimal:
        return self.amount * self.sell_price

    @property
    def total_fees(self) -> Decimal:
        """Сумма всех комиссий, как они сказываются на P/L.

        Сейчас ``gas_fee = 0`` (legacy) — сеть перевода учтена в
        ``network_fee`` → ``withdrawal_fee``.
        """
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

    # ── Методы состояния ─────────────────────────────────────────
    def complete(self) -> None:
        self.status = TradeStatus.COMPLETED

    def cancel(self) -> None:
        self.status = TradeStatus.CANCELLED

    def is_profitable(self) -> bool:
        return self.profit > Decimal("0")

    # ── Главный метод — пересчёт всех производных полей ──────────
    def recalculate(self) -> None:
        """Пересчитывает комиссии (из процентов) и время удержания.

        Вызывается автоматически в ``__post_init__`` и вручную
        после patch / изменения полей.
        """
        notional_buy = self.amount * self.buy_price
        notional_sell = self.amount * self.sell_price

        # Если указан процент и при этом money-value = 0, считаем из процента.
        if self.buy_fee_percent and not self.buy_fee:
            self.buy_fee = (notional_buy * self.buy_fee_percent / Decimal("100"))
        if self.sell_fee_percent and not self.sell_fee:
            self.sell_fee = (notional_sell * self.sell_fee_percent / Decimal("100"))

        # Объединяем вывод + сеть в одно число.
        self.withdrawal_fee = self.network_fee
        self.gas_fee = Decimal("0")

        # Время удержания — из bought_at / sold_at.
        # bought_at / sold_at могут прийти как ISO-строки (из API/patch).
        bought = self._coerce_dt(self.bought_at)
        sold = self._coerce_dt(self.sold_at)
        if bought and sold:
            delta = sold - bought
            self.holding_time_seconds = max(0, int(delta.total_seconds()))
        else:
            self.holding_time_seconds = None
        # Нормализуем к datetime (чтобы SQLAlchemy/DB не падали).
        self.bought_at = bought
        self.sold_at = sold

    @staticmethod
    def _coerce_dt(value: Any) -> Optional[datetime]:
        """Принимает datetime, ISO-строку или None. Возвращает datetime или None."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            try:
                s = value.replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except ValueError:
                return None
        return None
