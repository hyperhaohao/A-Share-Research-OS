"""G1 迁移：industry graph 六表

Revision ID: b9c0d1e2f3a6
Revises: a8b9c0d1e2f5
Create Date: 2026-09-02

真实产业图谱（观澜语义迁移任务书 §G1）：产业链/环节/传导边/产物/
边证据链接/公司链上位置 —— 与行业分类分表（分类树保留但不再冒充产业链）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c0d1e2f3a6'
down_revision: Union[str, Sequence[str], None] = 'a8b9c0d1e2f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'industry_chains',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('chain_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(length=128), nullable=False, index=True),
        sa.Column('description', sa.Text()),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('name', 'version', name='uq_industry_chain_name_version'),
    )
    op.create_table(
        'industry_segments',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('segment_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('chain_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('stage_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'industry_products',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('product_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(length=128), nullable=False, index=True),
        sa.Column('unit', sa.String(length=32)),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'industry_edges',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('edge_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('chain_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('source_segment_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('target_segment_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('relation_type', sa.String(length=32), nullable=False, index=True),
        sa.Column('input_product_ids_json', sa.JSON()),
        sa.Column('output_product_ids_json', sa.JSON()),
        sa.Column('transmission_metric', sa.String(length=200)),
        sa.Column('direction', sa.String(length=16), server_default='positive'),
        sa.Column('lag_min_days', sa.Integer(), server_default='0'),
        sa.Column('lag_max_days', sa.Integer(), server_default='0'),
        sa.Column('strength', sa.Float(), server_default='0'),
        sa.Column('confidence_level', sa.String(length=16), server_default='insufficient'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='insufficient', index=True),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('snapshot_id', sa.String(length=32), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'industry_edge_evidence',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('link_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('edge_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('evidence_id', sa.String(length=32), nullable=False, index=True),
        sa.Column('stance', sa.String(length=16), server_default='support'),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('added_by', sa.String(length=64), server_default='industry_graph'),
        sa.UniqueConstraint('edge_id', 'evidence_id', 'stance', name='uq_edge_evidence'),
    )
    op.create_table(
        'company_industry_positions',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('position_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('instrument_id', sa.String(length=32), nullable=False, index=True),
        sa.Column('chain_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('segment_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('role', sa.String(length=24), server_default='producer'),
        sa.Column('revenue_exposure_pct', sa.Float(), nullable=True),
        sa.Column('profit_exposure_pct', sa.Float(), nullable=True),
        sa.Column('capacity_note', sa.Text()),
        sa.Column('evidence_ids_json', sa.JSON()),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('snapshot_id', sa.String(length=32), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('company_industry_positions')
    op.drop_table('industry_edge_evidence')
    op.drop_table('industry_edges')
    op.drop_table('industry_products')
    op.drop_table('industry_segments')
    op.drop_table('industry_chains')
