"""phase a: artifacts, provenance_edges, run_events, handoffs

Revision ID: b7c8d9e0f1a2
Revises: a1f2c3d4e5b6
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a1f2c3d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('artifacts',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('artifact_id', sa.String(length=24), nullable=False),
    sa.Column('artifact_type', sa.String(length=32), nullable=False),
    sa.Column('domain_type', sa.String(length=32), nullable=False),
    sa.Column('domain_id', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=256), nullable=False),
    sa.Column('summary', sa.String(length=2000), nullable=True),
    sa.Column('instrument_ids_json', sa.JSON(), nullable=False),
    sa.Column('as_of_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('version', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_by', sa.String(length=32), nullable=False),
    sa.Column('route', sa.String(length=256), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('domain_type', 'domain_id', name='uq_artifact_domain')
    )
    with op.batch_alter_table('artifacts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_artifacts_artifact_id'), ['artifact_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_artifacts_artifact_type'), ['artifact_type'], unique=False)

    op.create_table('provenance_edges',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('edge_id', sa.String(length=24), nullable=False),
    sa.Column('from_artifact_id', sa.String(length=24), nullable=False),
    sa.Column('to_artifact_id', sa.String(length=24), nullable=False),
    sa.Column('relation_type', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('from_artifact_id', 'to_artifact_id', 'relation_type', name='uq_provenance_edge')
    )
    with op.batch_alter_table('provenance_edges', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_provenance_edges_edge_id'), ['edge_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_provenance_edges_from_artifact_id'), ['from_artifact_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_provenance_edges_relation_type'), ['relation_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_provenance_edges_to_artifact_id'), ['to_artifact_id'], unique=False)

    op.create_table('run_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('event_id', sa.String(length=24), nullable=False),
    sa.Column('run_id', sa.String(length=64), nullable=False),
    sa.Column('stage', sa.String(length=16), nullable=False),
    sa.Column('event_type', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=True),
    sa.Column('title', sa.String(length=64), nullable=True),
    sa.Column('summary', sa.String(length=500), nullable=True),
    sa.Column('payload_json', sa.JSON(), nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('run_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_run_events_event_id'), ['event_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_run_events_run_id'), ['run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_run_events_stage'), ['stage'], unique=False)

    op.create_table('handoffs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('handoff_id', sa.String(length=20), nullable=False),
    sa.Column('source_module', sa.String(length=32), nullable=False),
    sa.Column('target_module', sa.String(length=32), nullable=False),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('artifact_ids_json', sa.JSON(), nullable=False),
    sa.Column('context_json', sa.JSON(), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('handoffs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_handoffs_handoff_id'), ['handoff_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('handoffs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_handoffs_handoff_id'))
    op.drop_table('handoffs')
    with op.batch_alter_table('run_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_run_events_stage'))
        batch_op.drop_index(batch_op.f('ix_run_events_run_id'))
        batch_op.drop_index(batch_op.f('ix_run_events_event_id'))
    op.drop_table('run_events')
    with op.batch_alter_table('provenance_edges', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_provenance_edges_to_artifact_id'))
        batch_op.drop_index(batch_op.f('ix_provenance_edges_relation_type'))
        batch_op.drop_index(batch_op.f('ix_provenance_edges_from_artifact_id'))
        batch_op.drop_index(batch_op.f('ix_provenance_edges_edge_id'))
    op.drop_table('provenance_edges')
    with op.batch_alter_table('artifacts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_artifacts_artifact_type'))
        batch_op.drop_index(batch_op.f('ix_artifacts_artifact_id'))
    op.drop_table('artifacts')
