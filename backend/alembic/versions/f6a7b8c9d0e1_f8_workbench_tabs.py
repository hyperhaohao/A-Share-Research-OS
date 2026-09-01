"""f8: command workbench tabs (weiwo dynamic workbench)

Revision ID: f6a7b8c9d0e1
Revises: f5a6b7c8d9e0
Create Date: 2026-09-02

每会话独立 Workbench 状态（任务书 §8.7）：动态 Tab（page 来自注册表白名单、
payload 驱动真实页面、artifact 反查、刷新恢复）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'command_workbench_tabs',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('tab_id', sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column('session_id', sa.String(length=32), nullable=False, index=True),
        sa.Column('page', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('artifact_id', sa.String(length=32), nullable=True, index=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('session_id', 'artifact_id', name='uq_workbench_session_artifact'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('command_workbench_tabs')
