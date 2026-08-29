"""phase b: command sessions, turns, research plans

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('command_sessions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('session_id', sa.String(length=24), nullable=False),
    sa.Column('title', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('command_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_command_sessions_session_id'), ['session_id'], unique=True)

    op.create_table('command_turns',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('turn_id', sa.String(length=24), nullable=False),
    sa.Column('session_id', sa.String(length=24), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('text', sa.String(length=2000), nullable=False),
    sa.Column('plan_id', sa.String(length=24), nullable=True),
    sa.Column('artifact_ids_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('command_turns', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_command_turns_turn_id'), ['turn_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_command_turns_session_id'), ['session_id'], unique=False)

    op.create_table('research_plans',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('plan_id', sa.String(length=24), nullable=False),
    sa.Column('session_id', sa.String(length=24), nullable=True),
    sa.Column('instrument_id', sa.String(length=32), nullable=True),
    sa.Column('title', sa.String(length=256), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('steps_json', sa.JSON(), nullable=False),
    sa.Column('run_id', sa.String(length=64), nullable=True),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('research_plans', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_research_plans_plan_id'), ['plan_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_research_plans_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_research_plans_status'), ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('research_plans', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_research_plans_status'))
        batch_op.drop_index(batch_op.f('ix_research_plans_session_id'))
        batch_op.drop_index(batch_op.f('ix_research_plans_plan_id'))
    op.drop_table('research_plans')
    with op.batch_alter_table('command_turns', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_command_turns_session_id'))
        batch_op.drop_index(batch_op.f('ix_command_turns_turn_id'))
    op.drop_table('command_turns')
    with op.batch_alter_table('command_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_command_sessions_session_id'))
    op.drop_table('command_sessions')
