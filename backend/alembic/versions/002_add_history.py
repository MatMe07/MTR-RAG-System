"""002 add history

Revision ID: 002a2
Revises: 001a1
Create Date: 2025-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '002a2'
down_revision: Union[str, None] = '001a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mtr_item_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('mtr_code', sa.String(50), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.Column('changed_by', sa.String(100), nullable=True),
        sa.Column('old_attributes', JSONB(), nullable=True),
        sa.Column('new_attributes', JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mtr_item_history_mtr_code', 'mtr_item_history', ['mtr_code'], unique=False)

    op.create_table(
        'pipeline_edges',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('from_ksm', sa.String(50), nullable=False),
        sa.Column('to_ksm', sa.String(50), nullable=False),
        sa.Column('connection_type', sa.String(30), nullable=True),
        sa.Column('distance_m', sa.Float(), nullable=True),
        sa.Column('unit_code', sa.String(50), nullable=True),
        sa.Column('template', sa.String(255), nullable=True),
        sa.Column('instance', sa.Integer(), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_pe_from', 'pipeline_edges', ['from_ksm'], unique=False)
    op.create_index('idx_pe_to', 'pipeline_edges', ['to_ksm'], unique=False)


def downgrade() -> None:
    op.drop_table('pipeline_edges')
    op.drop_table('mtr_item_history')
