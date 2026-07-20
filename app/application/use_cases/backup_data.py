"""Бэкап базы в JSON и импорт обратно."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.infrastructure.models.trade_model import TradeModel
from app.infrastructure.unit_of_work import UnitOfWork


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return format(obj.normalize(), "f")
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    val = getattr(obj, "value", None)
    if val is not None:
        return str(val)
    raise TypeError(f"Cannot serialize {type(obj)}")


class ExportBackupUseCase:
    """Возвращает JSON-строку со всеми сделками."""
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, user_id: int = 0) -> str:
        async with self.uow:
            stmt = select(TradeModel).order_by(TradeModel.created_at)
            if user_id:
                stmt = stmt.where(TradeModel.telegram_user_id == user_id)
            result = await self.uow.session.execute(stmt)
            models = list(result.scalars().all())
            data = {
                "version": 1,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "count": len(models),
                "trades": [
                    {
                        col.name: _to_jsonable(getattr(m, col.name))
                        for col in TradeModel.__table__.columns
                    }
                    for m in models
                ],
            }
        return json.dumps(data, ensure_ascii=False, indent=2)


class ImportTradesUseCase:
    """Импортирует сделки из JSON-строки (формат ExportBackupUseCase).
    Возвращает (inserted: int, skipped: int)."""
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, payload: str, user_id: int = 0) -> tuple[int, int]:
        data = json.loads(payload)
        trades = data.get("trades", [])
        inserted = 0
        skipped = 0
        async with self.uow:
            for raw in trades:
                existing_id = raw.get("id")
                if existing_id is not None:
                    stmt = select(TradeModel).where(TradeModel.id == existing_id)
                    found = (await self.uow.session.execute(stmt)).scalar_one_or_none()
                    if found is not None:
                        skipped += 1
                        continue
                obj = TradeModel()
                for col in TradeModel.__table__.columns:
                    val = raw.get(col.name)
                    if val is None and col.nullable:
                        setattr(obj, col.name, None)
                    elif val is not None:
                        setattr(obj, col.name, val)
                # При импорте ставим владельцем текущего пользователя.
                obj.telegram_user_id = user_id
                self.uow.session.add(obj)
                inserted += 1
            await self.uow.session.commit()
        return inserted, skipped
