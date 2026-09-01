"""f9: background runway + session governance + session memory

Revision ID: a8b9c0d1e2f5
Revises: f6a7b8c9d0e1
Create Date: 2026-09-02

- command_background_tasks：帷幄后台任务跑道（§8.8：持久化 + 进度 + 重试 +
  lease 恢复 + 取消；不再依赖进程内 daemon thread）；
- command_sessions：会话治理（status=active|archived + last_activity_at，§8.9）；
- command_session_memory：双层记忆的会话记忆 + 长对话结构化压缩（§8.9）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f5'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'command_background_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('task_id', sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column('command_session_id', sa.String(length=32), nullable=True, index=True),
        sa.Column('tool_name', sa.String(length=64), nullable=False, index=True),
        sa.Column('arguments_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('arguments_digest', sa.String(length=256), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='queued', index=True),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=200), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('worker_id', sa.String(length=64), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Index('ix_cmd_bg_tasks_status_created', 'status', 'created_at'),
    )
    op.create_table(
        'command_session_memory',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('session_id', sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column('confirmed_params_json', sa.JSON(), nullable=True),
        sa.Column('key_conclusions_json', sa.JSON(), nullable=True),
        sa.Column('open_questions_json', sa.JSON(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('summary_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('compacted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        'command_sessions',
        sa.Column('status', sa.String(length=16), nullable=False, server_default='active'),
    )
    op.add_column(
        'command_sessions',
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('command_sessions', 'last_activity_at')
    op.drop_column('command_sessions', 'status')
    op.drop_table('command_session_memory')
    op.drop_table('command_background_tasks')
