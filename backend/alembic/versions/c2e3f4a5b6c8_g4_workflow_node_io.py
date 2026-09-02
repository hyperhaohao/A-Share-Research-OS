"""G4 migration: typed workflow node I/O ledger

Revision ID: c2e3f4a5b6c8
Revises: c1d2e3f4a6b7
Create Date: 2026-09-02

Typed Dataflow Workflow（观澜语义迁移任务书 §G4）：
每次节点执行落不可变 NodeInput/NodeOutput（按 attempt 追加）——
Edge 承担有类型的数据传输，下游只消费指定上游端口的输出。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e3f4a5b6c8'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'workflow_node_io',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('io_id', sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column('run_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('node_id', sa.String(length=48), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=16), nullable=False, index=True),
        sa.Column('input_json', sa.JSON(), nullable=True),
        sa.Column('output_json', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('workflow_node_io')
