"""add transfer_network and holding_time_seconds to trades

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-21 00:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("trades") as batch_op:
        batch_op.add_column(
            sa.Column("transfer_network", sa.String(length=20), nullable=True)
        )
        batch_op.add_column(
            sa.Column("holding_time_seconds", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("trades") as batch_op:
        batch_op.drop_column("holding_time_seconds")
        batch_op.drop_column("transfer_network")
