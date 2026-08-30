"""r3: industry semantic research objects (driver/transmission/narrative/position)

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols() -> list:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("object_key", sa.String(length=48), nullable=False),
        sa.Column("instrument_id", sa.String(length=32), nullable=True),
        sa.Column("industry_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "industry_semantic_objects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("object_type", sa.String(length=16), nullable=False),
        sa.Column("object_key", sa.String(length=48), nullable=False),
        sa.Column("instrument_id", sa.String(length=32), nullable=True),
        sa.Column("industry_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("mechanism", sa.String(length=2000), nullable=True),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("industry_semantic_objects", schema=None) as batch_op:
        batch_op.create_index("ix_industry_semantic_objects_object_type", ["object_type"], unique=False)
        batch_op.create_index("ix_industry_semantic_objects_object_key", ["object_key"], unique=False)
        batch_op.create_index("ix_industry_semantic_objects_industry_id", ["industry_id"], unique=False)
        batch_op.create_index("ix_industry_semantic_objects_as_of", ["as_of"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("industry_semantic_objects", schema=None) as batch_op:
        batch_op.drop_index("ix_industry_semantic_objects_as_of")
        batch_op.drop_index("ix_industry_semantic_objects_industry_id")
        batch_op.drop_index("ix_industry_semantic_objects_object_key")
        batch_op.drop_index("ix_industry_semantic_objects_object_type")
    op.drop_table("industry_semantic_objects")
