"""f5: command events (weiwo event protocol)

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-02

帷幄 Commander Event Protocol（第三轮整改任务书 §8.3）：
append-only、per-session 单调 sequence、correlation 关联、
版本化 payload schema、artifact 反查。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'command_events',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('event_id', sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column('session_id', sa.String(length=32), nullable=False, index=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=40), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', sa.String(length=48), nullable=True, index=True),
        sa.Column('plan_id', sa.String(length=32), nullable=True, index=True),
        sa.Column('task_id', sa.String(length=32), nullable=True, index=True),
        sa.Column('status', sa.String(length=24), nullable=True),
        sa.Column('payload_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('artifact_ids_json', sa.JSON(), nullable=True),
        sa.Column('provenance_json', sa.JSON(), nullable=True),
        sa.UniqueConstraint('session_id', 'sequence', name='uq_command_events_session_sequence'),
    )
    op.create_index(
        'ix_command_events_session_created',
        'command_events',
        ['session_id', 'created_at'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_command_events_session_created', table_name='command_events')
    op.drop_table('command_events')
