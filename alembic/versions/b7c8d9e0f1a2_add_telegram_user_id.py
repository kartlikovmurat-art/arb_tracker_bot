"""add telegram_user_id to trades

Revision ID: b7c8d9e0f1a2
Revises: 2a682b9d2768
Create Date: 2026-07-21 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "b7c8d9e0f1a2"
down_revision = "2a682b9d2768"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем колонку владельца сделки (telegram user id).
    # Существующие строки получат 0 — легаси / анонимный владелец.
    # Их можно переназначить вручную после миграции.
    with op.batch_alter_table("trades") as batch_op:
        batch_op.add_column(
            sa.Column(
                "telegram_user_id",
                sa.BigInteger(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_index(
            "ix_trades_telegram_user_id",
            ["telegram_user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("trades") as batch_op:
        batch_op.drop_index("ix_trades_telegram_user_id")
        batch_op.drop_column("telegram_user_id")
