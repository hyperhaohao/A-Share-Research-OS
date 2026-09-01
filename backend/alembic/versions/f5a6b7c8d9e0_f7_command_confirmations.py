"""f7: command confirmations (weiwo approval gate)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-09-02

审批确认状态机（第三轮整改任务书 §8.6）：
    pending → approved | rejected | expired | revoked → consumed
所有决定落库（审计）+ 帷幄事件（confirmation_requested/decided）；
参数 digest 绑定：批准后参数不可被替换（防 TOCTOU）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'command_confirmations',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('confirmation_id', sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column('command_session_id', sa.String(length=32), nullable=True, index=True),
        sa.Column('tool_name', sa.String(length=64), nullable=False, index=True),
        sa.Column('arguments_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('arguments_digest', sa.String(length=256), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='pending', index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_by', sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('command_confirmations')
