"""G12 migration: background task heartbeat + dead-letter

Revision ID: c6b7c8d9e0f3
Revises: c6a7b8c9d0e2
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c6b7c8d9e0f3'
down_revision: Union[str, Sequence[str], None] = 'c6a7b8c9d0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('command_background_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('dead_letter', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('command_background_tasks', schema=None) as batch_op:
        batch_op.drop_column('dead_letter')
        batch_op.drop_column('heartbeat_at')
