"""r7: research memories

Revision ID: a7b8c9d0e1f3
Revises: f7a8b9c0d1e2
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_memories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("memory_id", sa.String(length=24), nullable=False),
        sa.Column("memory_type", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.String(length=4000), nullable=False),
        sa.Column("instrument_id", sa.String(length=32), nullable=True),
        sa.Column("industry_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=True),
        sa.Column("intent", sa.String(length=24), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=True),
        sa.Column("source_artifacts_json", sa.JSON(), nullable=True),
        sa.Column("source_experiences_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("research_memories", schema=None) as batch_op:
        batch_op.create_index("ix_research_memories_memory_id", ["memory_id"], unique=True)
        batch_op.create_index("ix_research_memories_memory_type", ["memory_type"], unique=False)
        batch_op.create_index("ix_research_memories_status", ["status"], unique=False)
        batch_op.create_index("ix_research_memories_instrument_id", ["instrument_id"], unique=False)
        batch_op.create_index("ix_research_memories_industry_id", ["industry_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("research_memories", schema=None) as batch_op:
        batch_op.drop_index("ix_research_memories_industry_id")
        batch_op.drop_index("ix_research_memories_instrument_id")
        batch_op.drop_index("ix_research_memories_status")
        batch_op.drop_index("ix_research_memories_memory_type")
        batch_op.drop_index("ix_research_memories_memory_id")
    op.drop_table("research_memories")
