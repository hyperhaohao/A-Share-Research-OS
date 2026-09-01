"""f4: source independence + confidence basis

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-09-02

来源独立性字段（第三轮整改任务书 §7.2，evidence 表）：
  publisher / origin_url / canonical_url / source_group / original_source /
  published_at（content_hash 已存在）。

可解释置信度（§7.1，claims 表）：
  confidence_basis_json（因素分解）/ confidence_level（high|medium|low|insufficient）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('publisher', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('origin_url', sa.String(length=2048), nullable=True))
        batch_op.add_column(sa.Column('canonical_url', sa.String(length=2048), nullable=True))
        batch_op.add_column(sa.Column('source_group', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('original_source', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table('claims', schema=None) as batch_op:
        batch_op.add_column(sa.Column('confidence_basis_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('confidence_level', sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('claims', schema=None) as batch_op:
        batch_op.drop_column('confidence_level')
        batch_op.drop_column('confidence_basis_json')
    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.drop_column('published_at')
        batch_op.drop_column('original_source')
        batch_op.drop_column('source_group')
        batch_op.drop_column('canonical_url')
        batch_op.drop_column('origin_url')
        batch_op.drop_column('publisher')
