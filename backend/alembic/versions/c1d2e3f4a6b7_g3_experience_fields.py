"""G3 migration: experience rule-component fields + validation verdict

Revision ID: c1d2e3f4a6b7
Revises: c0d1e2f3a6b7
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a6b7'
down_revision: Union[str, Sequence[str], None] = 'c0d1e2f3a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _card_cols() -> list[sa.Column]:
    return [
        sa.Column('signals_json', sa.JSON(), nullable=True),
        sa.Column('scope_json', sa.JSON(), nullable=True),
        sa.Column('usage_guidance', sa.Text(), nullable=True),
        sa.Column('counterexamples_json', sa.JSON(), nullable=True),
        sa.Column('validation_method', sa.String(length=32), nullable=True),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    for table in ('experience_cards', 'experience_card_versions'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            for col in _card_cols():
                batch_op.add_column(col.copy())
    with op.batch_alter_table('experience_validations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('verdict', sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('experience_validations', schema=None) as batch_op:
        batch_op.drop_column('verdict')
    for table in ('experience_card_versions', 'experience_cards'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column('validation_method')
            batch_op.drop_column('counterexamples_json')
            batch_op.drop_column('usage_guidance')
            batch_op.drop_column('scope_json')
            batch_op.drop_column('signals_json')
