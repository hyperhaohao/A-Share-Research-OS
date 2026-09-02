"""G7 migration: strategy-aware monitor state machine + cursors

Revision ID: c4a5b6c7d8e0
Revises: c3f4a5b6c8d9
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a5b6c7d8e0'
down_revision: Union[str, Sequence[str], None] = 'c3f4a5b6c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('strategy_monitors', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'status', sa.String(length=16), nullable=False,
            server_default='ACTIVE', index=True))
        batch_op.add_column(sa.Column(
            'quote_cursor', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column(
            'evidence_cursor', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column(
            'last_error', sa.String(length=500), nullable=True))
    with op.batch_alter_table('strategy_signals', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'direction', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column(
            'idempotency_key', sa.String(length=120), nullable=True, index=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('strategy_signals', schema=None) as batch_op:
        batch_op.drop_column('idempotency_key')
        batch_op.drop_column('direction')
    with op.batch_alter_table('strategy_monitors', schema=None) as batch_op:
        batch_op.drop_column('last_error')
        batch_op.drop_column('evidence_cursor')
        batch_op.drop_column('quote_cursor')
        batch_op.drop_column('status')
