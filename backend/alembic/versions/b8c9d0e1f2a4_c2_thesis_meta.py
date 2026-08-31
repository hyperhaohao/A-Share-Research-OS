"""c2: theses meta_json (thesis revision model / current thesis)

Revision ID: b8c9d0e1f2a4
Revises: a7b8c9d0e1f3
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a4"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("theses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("meta_json", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("theses", schema=None) as batch_op:
        batch_op.drop_column("meta_json")
