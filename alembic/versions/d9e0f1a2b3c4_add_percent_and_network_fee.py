"""add buy_fee_percent, sell_fee_percent, network_fee, bought_at, sold_at to trades

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-21 00:45:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "d9e0f1a2b3c4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("trades") as batch_op:
        batch_op.add_column(
            sa.Column("buy_fee_percent", sa.Numeric(10, 4), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("sell_fee_percent", sa.Numeric(10, 4), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("network_fee", sa.Numeric(28, 12), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("bought_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("trades") as batch_op:
        batch_op.drop_column("sold_at")
        batch_op.drop_column("bought_at")
        batch_op.drop_column("network_fee")
        batch_op.drop_column("sell_fee_percent")
        batch_op.drop_column("buy_fee_percent")
