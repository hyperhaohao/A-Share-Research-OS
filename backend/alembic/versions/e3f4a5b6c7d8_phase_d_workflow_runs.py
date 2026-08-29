"""phase d: workflow runs

Revision ID: e3f4a5b6c7d8
Revises: d1e2f3a4b5c6
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('workflow_runs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('run_id', sa.String(length=24), nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=False),
    sa.Column('card_id', sa.String(length=24), nullable=True),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('params_json', sa.JSON(), nullable=False),
    sa.Column('nodes_json', sa.JSON(), nullable=False),
    sa.Column('metrics_json', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workflow_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_runs_run_id'), ['run_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_workflow_runs_instrument_id'), ['instrument_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workflow_runs_card_id'), ['card_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workflow_runs_status'), ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('workflow_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workflow_runs_status'))
        batch_op.drop_index(batch_op.f('ix_workflow_runs_card_id'))
        batch_op.drop_index(batch_op.f('ix_workflow_runs_instrument_id'))
        batch_op.drop_index(batch_op.f('ix_workflow_runs_run_id'))
    op.drop_table('workflow_runs')
