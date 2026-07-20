"""create trades table

Revision ID: a1b2c3d4e5f1
Revises: 470457b7afe9
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.value_objects.trade_type import TradeType
from app.core.value_objects.trade_status import TradeStatus


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f1'
down_revision: Union[str, Sequence[str], None] = '470457b7afe9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # create enums as textual enums
    trade_type_enum = sa.Enum(TradeType, name="trade_type")
    status_enum = sa.Enum(TradeStatus, name="trade_status")
    trade_type_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('coin', sa.String(length=20), nullable=False),
        sa.Column('buy_exchange', sa.String(length=50), nullable=False),
        sa.Column('sell_exchange', sa.String(length=50), nullable=False),

        sa.Column('amount', sa.Numeric(28, 12), nullable=False),
        sa.Column('buy_price', sa.Numeric(28, 12), nullable=False),
        sa.Column('sell_price', sa.Numeric(28, 12), nullable=False),

        sa.Column('buy_fee', sa.Numeric(28, 12), nullable=False, server_default='0'),
        sa.Column('sell_fee', sa.Numeric(28, 12), nullable=False, server_default='0'),
        sa.Column('withdrawal_fee', sa.Numeric(28, 12), nullable=False, server_default='0'),
        sa.Column('gas_fee', sa.Numeric(28, 12), nullable=False, server_default='0'),
        sa.Column('slippage', sa.Numeric(28, 12), nullable=False, server_default='0'),

        sa.Column('profit', sa.Numeric(28, 12), nullable=False, server_default='0'),
        sa.Column('roi', sa.Numeric(10, 2), nullable=False, server_default='0'),

        sa.Column('trade_type', trade_type_enum, nullable=False),
        sa.Column('status', status_enum, nullable=False),

        sa.Column('strategy', sa.String(length=100), nullable=True),
        sa.Column('note', sa.String(length=255), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('trades')
    sa.Enum('trade_type', name='trade_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum('trade_status', name='trade_status').drop(op.get_bind(), checkfirst=True)
