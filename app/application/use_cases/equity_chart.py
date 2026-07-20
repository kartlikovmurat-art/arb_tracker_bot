"""Генерация PNG-графика equity curve.

Использует matplotlib. Возвращает байты PNG-файла.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

import matplotlib

# Используем non-interactive backend, чтобы не требовать дисплей.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.core.value_objects.trade_status import TradeStatus
from app.infrastructure.unit_of_work import UnitOfWork


def _to_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class GenerateEquityChartUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self) -> bytes:
        async with self.uow:
            trades = await self.uow.trades.get_all()
        completed = [t for t in trades if t.status == TradeStatus.COMPLETED]
        completed.sort(key=lambda t: _to_dt(t.created_at))

        if not completed:
            # Пустой график с подписью
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(
                0.5, 0.5,
                "No completed trades yet",
                ha="center", va="center",
                fontsize=14, color="#888",
            )
            ax.set_axis_off()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
            plt.close(fig)
            return buf.getvalue()

        dates = [_to_dt(t.created_at) for t in completed]
        cumulative = []
        running = Decimal("0")
        for t in completed:
            running += t.profit
            cumulative.append(float(running))

        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(dates, cumulative, marker="o", linewidth=2,
                color="#3b82f6", markerfacecolor="#fff",
                markeredgewidth=2, markersize=6)
        ax.fill_between(dates, cumulative, alpha=0.15, color="#3b82f6")
        ax.axhline(0, color="#94a3b8", linewidth=0.8, linestyle="--")
        ax.set_title("Equity Curve", fontsize=15, fontweight="bold",
                     color="#0f172a", pad=12)
        ax.set_xlabel("Date", color="#475569")
        ax.set_ylabel("Cumulative P/L", color="#475569")
        ax.grid(True, alpha=0.25, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.autofmt_xdate()
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
