"""phase f: strategy versions + backtest runs

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('strategy_versions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('version_id', sa.String(length=24), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('version_no', sa.Integer(), nullable=False),
    sa.Column('philosophy', sa.String(length=2000), nullable=False),
    sa.Column('source_card_id', sa.String(length=24), nullable=False),
    sa.Column('source_screening_run_id', sa.String(length=24), nullable=False),
    sa.Column('universe_json', sa.JSON(), nullable=False),
    sa.Column('entry_policy_json', sa.JSON(), nullable=False),
    sa.Column('exit_policy_json', sa.JSON(), nullable=False),
    sa.Column('risk_policy_json', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('verdict', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('strategy_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_strategy_versions_version_id'), ['version_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_strategy_versions_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_strategy_versions_source_card_id'), ['source_card_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_strategy_versions_status'), ['status'], unique=False)

    op.create_table('strategy_backtest_runs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('backtest_id', sa.String(length=24), nullable=False),
    sa.Column('version_id', sa.String(length=24), nullable=False),
    sa.Column('results_json', sa.JSON(), nullable=False),
    sa.Column('aggregate_json', sa.JSON(), nullable=False),
    sa.Column('failure_cases_json', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('strategy_backtest_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_strategy_backtest_runs_backtest_id'), ['backtest_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_strategy_backtest_runs_version_id'), ['version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_strategy_backtest_runs_status'), ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('strategy_backtest_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_strategy_backtest_runs_status'))
        batch_op.drop_index(batch_op.f('ix_strategy_backtest_runs_version_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_backtest_runs_backtest_id'))
    op.drop_table('strategy_backtest_runs')
    with op.batch_alter_table('strategy_versions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_strategy_versions_status'))
        batch_op.drop_index(batch_op.f('ix_strategy_versions_source_card_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_versions_name'))
        batch_op.drop_index(batch_op.f('ix_strategy_versions_version_id'))
    op.drop_table('strategy_versions')
