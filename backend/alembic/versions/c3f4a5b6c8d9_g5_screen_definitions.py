"""G5 migration: screen definitions (experience-driven, versioned)

Revision ID: c3f4a5b6c8d9
Revises: c2e3f4a5b6c8
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f4a5b6c8d9'
down_revision: Union[str, Sequence[str], None] = 'c2e3f4a5b6c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'screen_definitions',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('def_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('source_card_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('source_card_version', sa.Integer(), nullable=False),
        sa.Column('universe_json', sa.JSON(), nullable=False),
        sa.Column('rules_json', sa.JSON(), nullable=False),
        sa.Column('ranking_json', sa.JSON(), nullable=False),
        sa.Column('missing_data_policy', sa.String(length=16), server_default='exclude'),
        sa.Column('as_of_policy', sa.String(length=16), server_default='now'),
        sa.Column('status', sa.String(length=16), server_default='draft', index=True),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('compiled_payload_json', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(length=64), server_default='screening'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        'screen_definition_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('run_id', sa.String(length=24), nullable=False, unique=True, index=True),
        sa.Column('def_id', sa.String(length=24), nullable=False, index=True),
        sa.Column('def_version', sa.Integer(), nullable=False),
        sa.Column('as_of', sa.DateTime(timezone=True), nullable=False),
        sa.Column('universe_json', sa.JSON(), nullable=False),
        sa.Column('candidates_json', sa.JSON(), nullable=False),
        sa.Column('exclusions_json', sa.JSON(), nullable=False),
        sa.Column('artifact_id', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('screen_definition_runs')
    op.drop_table('screen_definitions')
