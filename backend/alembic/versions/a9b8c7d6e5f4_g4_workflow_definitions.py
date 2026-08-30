"""g4: workflow definitions + append-only versions

Revision ID: a9b8c7d6e5f4
Revises: c7d8e9f0a1b2
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('workflow_definitions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('def_id', sa.String(length=24), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=True),
    sa.Column('current_version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workflow_definitions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_definitions_def_id'), ['def_id'], unique=True)

    op.create_table('workflow_definition_versions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('def_id', sa.String(length=24), nullable=False),
    sa.Column('version_no', sa.Integer(), nullable=False),
    sa.Column('nodes_json', sa.JSON(), nullable=False),
    sa.Column('edges_json', sa.JSON(), nullable=False),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workflow_definition_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_definition_versions_def_id'), ['def_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('workflow_definition_versions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workflow_definition_versions_def_id'), ['def_id'])
    op.drop_table('workflow_definition_versions')
    with op.batch_alter_table('workflow_definitions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workflow_definitions_def_id'), ['def_id'])
    op.drop_table('workflow_definitions')
