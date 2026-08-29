"""deep a+b: global context indicators column

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('global_context_snapshots', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('indicators_json', sa.JSON(), nullable=False, server_default='[]')
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('global_context_snapshots', schema=None) as batch_op:
        batch_op.drop_column('indicators_json')
