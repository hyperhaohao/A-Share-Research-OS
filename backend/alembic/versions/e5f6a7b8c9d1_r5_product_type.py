"""r5: reports.product_type (ResearchProduct typed contracts)

Revision ID: e5f6a7b8c9d1
Revises: d4e5f6a7b8c9
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("product_type", sa.String(length=32), nullable=False,
                      server_default="COMPANY_DEEP_DIVE")
        )
        batch_op.create_index("ix_reports_product_type", ["product_type"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.drop_index("ix_reports_product_type")
        batch_op.drop_column("product_type")
