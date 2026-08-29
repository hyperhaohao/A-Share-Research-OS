"""phase c: experience cards, versions, validations

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('experience_cards',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('card_id', sa.String(length=24), nullable=False),
    sa.Column('instrument_id', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=256), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('statement', sa.String(length=2000), nullable=False),
    sa.Column('mechanism', sa.String(length=4000), nullable=False),
    sa.Column('applicable_conditions_json', sa.JSON(), nullable=False),
    sa.Column('invalid_conditions_json', sa.JSON(), nullable=False),
    sa.Column('source_report_id', sa.String(length=32), nullable=False),
    sa.Column('source_report_version_id', sa.String(length=32), nullable=False),
    sa.Column('source_snapshot_id', sa.String(length=32), nullable=False),
    sa.Column('source_claim_ids_json', sa.JSON(), nullable=False),
    sa.Column('source_evidence_ids_json', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('verdict', sa.String(length=500), nullable=True),
    sa.Column('current_version', sa.Integer(), nullable=False),
    sa.Column('refine_method', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('experience_cards', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_experience_cards_card_id'), ['card_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_experience_cards_instrument_id'), ['instrument_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_experience_cards_source_report_id'), ['source_report_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_experience_cards_status'), ['status'], unique=False)

    op.create_table('experience_card_versions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('card_id', sa.String(length=24), nullable=False),
    sa.Column('version_no', sa.Integer(), nullable=False),
    sa.Column('statement', sa.String(length=2000), nullable=False),
    sa.Column('mechanism', sa.String(length=4000), nullable=False),
    sa.Column('applicable_conditions_json', sa.JSON(), nullable=False),
    sa.Column('invalid_conditions_json', sa.JSON(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('method', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('experience_card_versions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_experience_card_versions_card_id'), ['card_id'], unique=False)

    op.create_table('experience_validations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('validation_id', sa.String(length=24), nullable=False),
    sa.Column('card_id', sa.String(length=24), nullable=False),
    sa.Column('method', sa.String(length=16), nullable=False),
    sa.Column('cases_json', sa.JSON(), nullable=False),
    sa.Column('summary', sa.String(length=1000), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('experience_validations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_experience_validations_validation_id'), ['validation_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_experience_validations_card_id'), ['card_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('experience_validations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_experience_validations_card_id'))
        batch_op.drop_index(batch_op.f('ix_experience_validations_validation_id'))
    op.drop_table('experience_validations')
    with op.batch_alter_table('experience_card_versions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_experience_card_versions_card_id'))
    op.drop_table('experience_card_versions')
    with op.batch_alter_table('experience_cards', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_experience_cards_status'))
        batch_op.drop_index(batch_op.f('ix_experience_cards_source_report_id'))
        batch_op.drop_index(batch_op.f('ix_experience_cards_instrument_id'))
        batch_op.drop_index(batch_op.f('ix_experience_cards_card_id'))
    op.drop_table('experience_cards')
