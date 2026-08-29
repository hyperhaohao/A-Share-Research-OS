"""phase h: industry map + global context snapshots

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'b6c7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('industry_map_snapshots',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('map_id', sa.String(length=24), nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=False),
    sa.Column('industry_label', sa.String(length=64), nullable=False),
    sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
    sa.Column('industry_chain_json', sa.JSON(), nullable=False),
    sa.Column('main_business', sa.String(length=2000), nullable=True),
    sa.Column('related_instruments_json', sa.JSON(), nullable=False),
    sa.Column('evidence_ids_json', sa.JSON(), nullable=False),
    sa.Column('disclosures_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('industry_map_snapshots', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_industry_map_snapshots_map_id'), ['map_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_industry_map_snapshots_instrument_id'), ['instrument_id'], unique=False)

    op.create_table('global_context_snapshots',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('snapshot_id', sa.String(length=24), nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=False),
    sa.Column('topic', sa.String(length=64), nullable=False),
    sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
    sa.Column('themes_json', sa.JSON(), nullable=False),
    sa.Column('evidence_ids_json', sa.JSON(), nullable=False),
    sa.Column('disclosures_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('global_context_snapshots', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_global_context_snapshots_snapshot_id'), ['snapshot_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_global_context_snapshots_instrument_id'), ['instrument_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('global_context_snapshots', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_global_context_snapshots_instrument_id'))
        batch_op.drop_index(batch_op.f('ix_global_context_snapshots_snapshot_id'))
    op.drop_table('global_context_snapshots')
    with op.batch_alter_table('industry_map_snapshots', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_industry_map_snapshots_instrument_id'))
        batch_op.drop_index(batch_op.f('ix_industry_map_snapshots_map_id'))
    op.drop_table('industry_map_snapshots')
