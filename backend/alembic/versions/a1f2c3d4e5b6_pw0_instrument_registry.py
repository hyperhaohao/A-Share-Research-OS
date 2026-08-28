"""pw0: persistent instrument registry

Revision ID: a1f2c3d4e5b6
Revises: 530737648a35
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f2c3d4e5b6'
down_revision: Union[str, Sequence[str], None] = '530737648a35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('instrument_registry',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=False),
    sa.Column('code', sa.String(length=16), nullable=False),
    sa.Column('exchange', sa.String(length=8), nullable=False),
    sa.Column('board', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('aliases_json', sa.JSON(), nullable=False),
    sa.Column('listed_status', sa.String(length=16), nullable=False),
    sa.Column('sector', sa.String(length=64), nullable=True),
    sa.Column('industry', sa.String(length=64), nullable=True),
    sa.Column('origin', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('instrument_registry', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_instrument_registry_code'), ['code'], unique=False)
        batch_op.create_index(batch_op.f('ix_instrument_registry_instrument_id'), ['instrument_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('instrument_registry', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_instrument_registry_instrument_id'))
        batch_op.drop_index(batch_op.f('ix_instrument_registry_code'))
    op.drop_table('instrument_registry')
