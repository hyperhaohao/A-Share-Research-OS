"""R1 migration: canonical production fields on strategy versions

Revision ID: c7b8c9d0e1f4
Revises: c6b7c8d9e0f3
Create Date: 2026-09-02

权威生产模型字段（任务书 §R1.2）：input_digest / source_version_ids /
confirmation_id / idempotency_key + ScreenRun 因果引用
（source_screen_definition_id / source_screen_run_id）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7b8c9d0e1f4'
down_revision: Union[str, Sequence[str], None] = 'c6b7c8d9e0f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('strategy_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_screen_definition_id', sa.String(length=24), nullable=True, index=True))
        batch_op.add_column(sa.Column('source_screen_run_id', sa.String(length=24), nullable=True, index=True))
        batch_op.add_column(sa.Column('input_digest', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('source_version_ids_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('confirmation_id', sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=120), nullable=True, index=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('strategy_versions', schema=None) as batch_op:
        batch_op.drop_column('idempotency_key')
        batch_op.drop_column('confirmation_id')
        batch_op.drop_column('source_version_ids_json')
        batch_op.drop_column('input_digest')
        batch_op.drop_column('source_screen_run_id')
        batch_op.drop_column('source_screen_definition_id')
