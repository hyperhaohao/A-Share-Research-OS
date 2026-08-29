"""phase e: screening runs

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('screening_runs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('run_id', sa.String(length=24), nullable=False),
    sa.Column('card_id', sa.String(length=24), nullable=True),
    sa.Column('universe_size', sa.Integer(), nullable=False),
    sa.Column('rules_json', sa.JSON(), nullable=False),
    sa.Column('candidates_json', sa.JSON(), nullable=False),
    sa.Column('excluded_summary_json', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('screening_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_screening_runs_run_id'), ['run_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_screening_runs_card_id'), ['card_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_screening_runs_status'), ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('screening_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_screening_runs_status'))
        batch_op.drop_index(batch_op.f('ix_screening_runs_card_id'))
        batch_op.drop_index(batch_op.f('ix_screening_runs_run_id'))
    op.drop_table('screening_runs')
