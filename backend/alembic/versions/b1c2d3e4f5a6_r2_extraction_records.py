"""r2: extraction records (source-trust verified extraction staging)

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("extraction_records",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("extraction_id", sa.String(length=24), nullable=False),
    sa.Column("source_evidence_id", sa.String(length=32), nullable=False),
    sa.Column("statement", sa.String(length=500), nullable=False),
    sa.Column("support_span", sa.String(length=2000), nullable=False),
    sa.Column("fact_status", sa.String(length=32), nullable=False),
    sa.Column("claim_type", sa.String(length=32), nullable=True),
    sa.Column("confidence_basis", sa.String(length=300), nullable=True),
    sa.Column("extractor", sa.String(length=40), nullable=True),
    sa.Column("prompt_version", sa.String(length=24), nullable=True),
    sa.Column("verdict", sa.String(length=12), nullable=False),
    sa.Column("reject_reason", sa.String(length=60), nullable=True),
    sa.Column("verdict_basis", sa.String(length=24), nullable=True),
    sa.Column("trust_level", sa.String(length=32), nullable=False),
    sa.Column("evidence_authority", sa.String(length=4), nullable=False),
    sa.Column("instrument_id", sa.String(length=32), nullable=False),
    sa.Column("promoted_claim_id", sa.String(length=24), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id")
    )
    with op.batch_alter_table("extraction_records", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_extraction_records_extraction_id"), ["extraction_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_extraction_records_source_evidence_id"), ["source_evidence_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_extraction_records_verdict"), ["verdict"], unique=False)
        batch_op.create_index(batch_op.f("ix_extraction_records_instrument_id"), ["instrument_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("extraction_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_extraction_records_instrument_id"))
        batch_op.drop_index(batch_op.f("ix_extraction_records_verdict"))
        batch_op.drop_index(batch_op.f("ix_extraction_records_source_evidence_id"))
        batch_op.drop_index(batch_op.f("ix_extraction_records_extraction_id"))
    op.drop_table("extraction_records")
