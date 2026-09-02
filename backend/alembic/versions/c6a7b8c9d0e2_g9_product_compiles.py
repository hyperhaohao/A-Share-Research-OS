"""G9 migration: research product compile versions (Artifact/PIT/Version)

Revision ID: c6a7b8c9d0e2
Revises: c5b6c7d8e9f1
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6a7b8c9d0e2'
down_revision: Union[str, Sequence[str], None] = 'c5b6c7d8e9f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'research_product_compiles',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('compile_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('product_type', sa.String(length=40), nullable=False, index=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('artifact_id', sa.String(length=32), nullable=True),
        sa.Column('provenance_status', sa.String(length=32), server_default='complete'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('research_product_compiles')
