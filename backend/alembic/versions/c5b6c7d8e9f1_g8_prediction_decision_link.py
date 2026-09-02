"""G8 migration: prediction decision causal link

Revision ID: c5b6c7d8e9f1
Revises: c4a5b6c7d8e0
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5b6c7d8e9f1'
down_revision: Union[str, Sequence[str], None] = 'c4a5b6c7d8e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('decision_id', sa.String(length=24), nullable=True, index=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.drop_column('decision_id')
