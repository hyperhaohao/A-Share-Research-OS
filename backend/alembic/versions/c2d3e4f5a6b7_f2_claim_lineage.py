"""f2: claim version lineage columns

Revision ID: c2d3e4f5a6b7
Revises: b8c9d0e1f2a4
Create Date: 2026-09-01

Claim Version lineage（第三轮整改任务书 §5.3.4）：
  - parent_claim_id      版本链父 Claim（supersedes/updates/carried_forward）
  - revision_kind        版本类型：carried_forward | supersedes | updated
  - revision_reason      修订原因（可审计）
  - source_impact_relation  驱动本次修订的 ClaimImpact relation
  - carried_forward      是否为上一版本快照的沿用
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('claims', schema=None) as batch_op:
        batch_op.add_column(sa.Column('parent_claim_id', sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column('revision_kind', sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column('revision_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source_impact_relation', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('carried_forward', sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.create_index('ix_claims_parent_claim_id', ['parent_claim_id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('claims', schema=None) as batch_op:
        batch_op.drop_index('ix_claims_parent_claim_id')
        batch_op.drop_column('carried_forward')
        batch_op.drop_column('source_impact_relation')
        batch_op.drop_column('revision_reason')
        batch_op.drop_column('revision_kind')
        batch_op.drop_column('parent_claim_id')
