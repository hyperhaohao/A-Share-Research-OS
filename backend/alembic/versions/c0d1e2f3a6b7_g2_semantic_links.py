"""G2 migration: semantic chain/segment/edge links + contrary evidence

Revision ID: c0d1e2f3a6b7
Revises: b9c0d1e2f3a6
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0d1e2f3a6b7'
down_revision: Union[str, Sequence[str], None] = 'b9c0d1e2f3a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('industry_semantic_objects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('chain_id', sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column('segment_id', sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column('edge_id', sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column('contrary_evidence_refs_json', sa.JSON(), nullable=True))
        batch_op.create_index('ix_semantic_chain', ['chain_id'])
        batch_op.create_index('ix_semantic_edge', ['edge_id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('industry_semantic_objects', schema=None) as batch_op:
        batch_op.drop_index('ix_semantic_edge')
        batch_op.drop_index('ix_semantic_chain')
        batch_op.drop_column('contrary_evidence_refs_json')
        batch_op.drop_column('edge_id')
        batch_op.drop_column('segment_id')
        batch_op.drop_column('chain_id')
