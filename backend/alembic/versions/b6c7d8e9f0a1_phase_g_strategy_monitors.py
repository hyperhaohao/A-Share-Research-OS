"""phase g: strategy monitors, observations, signals, decisions

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c7d8e9f0a1'
down_revision: Union[str, Sequence[str], None] = 'a5b6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('strategy_monitors',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('monitor_id', sa.String(length=24), nullable=False),
    sa.Column('version_id', sa.String(length=24), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('universe_json', sa.JSON(), nullable=False),
    sa.Column('rules_json', sa.JSON(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('strategy_monitors', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_strategy_monitors_monitor_id'), ['monitor_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_strategy_monitors_version_id'), ['version_id'], unique=False)

    op.create_table('strategy_observations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('observation_id', sa.String(length=24), nullable=False),
    sa.Column('monitor_id', sa.String(length=24), nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('text', sa.String(length=1000), nullable=False),
    sa.Column('payload_json', sa.JSON(), nullable=False),
    sa.Column('evidence_ids_json', sa.JSON(), nullable=False),
    sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('strategy_observations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_strategy_observations_observation_id'), ['observation_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_strategy_observations_monitor_id'), ['monitor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_strategy_observations_instrument_id'), ['instrument_id'], unique=False)

    op.create_table('strategy_signals',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('signal_id', sa.String(length=24), nullable=False),
    sa.Column('monitor_id', sa.String(length=24), nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=False),
    sa.Column('rule_kind', sa.String(length=32), nullable=False),
    sa.Column('strength', sa.Float(), nullable=False),
    sa.Column('text', sa.String(length=1000), nullable=False),
    sa.Column('observation_ids_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('strategy_signals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_strategy_signals_signal_id'), ['signal_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_strategy_signals_monitor_id'), ['monitor_id'], unique=False)

    op.create_table('strategy_decisions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('decision_id', sa.String(length=24), nullable=False),
    sa.Column('monitor_id', sa.String(length=24), nullable=False),
    sa.Column('version_id', sa.String(length=24), nullable=False),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('rationale', sa.String(length=2000), nullable=False),
    sa.Column('observation_ids_json', sa.JSON(), nullable=False),
    sa.Column('signal_ids_json', sa.JSON(), nullable=False),
    sa.Column('evidence_ids_json', sa.JSON(), nullable=False),
    sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('strategy_decisions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_strategy_decisions_decision_id'), ['decision_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_strategy_decisions_monitor_id'), ['monitor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_strategy_decisions_version_id'), ['version_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('strategy_decisions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_strategy_decisions_version_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_decisions_monitor_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_decisions_decision_id'))
    op.drop_table('strategy_decisions')
    with op.batch_alter_table('strategy_signals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_strategy_signals_monitor_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_signals_signal_id'))
    op.drop_table('strategy_signals')
    with op.batch_alter_table('strategy_observations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_strategy_observations_instrument_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_observations_monitor_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_observations_observation_id'))
    op.drop_table('strategy_observations')
    with op.batch_alter_table('strategy_monitors', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_strategy_monitors_version_id'))
        batch_op.drop_index(batch_op.f('ix_strategy_monitors_monitor_id'))
    op.drop_table('strategy_monitors')
