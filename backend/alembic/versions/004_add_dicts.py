"""004 add dicts

Revision ID: 004a4
Revises: 003a3
Create Date: 2025-01-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '004a4'
down_revision: Union[str, None] = '003a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'group_keywords',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_name', sa.String(50), nullable=False),
        sa.Column('keyword', sa.String(100), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_group_keywords_group', 'group_keywords', ['group_name'], unique=False)

    op.create_table(
        'contextual_overrides',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trigger_phrase', sa.String(255), nullable=False),
        sa.Column('target_group', sa.String(50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'synonyms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_name', sa.String(50), nullable=False),
        sa.Column('raw_value', sa.String(255), nullable=False),
        sa.Column('normalized_value', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_synonyms_group', 'synonyms', ['group_name'], unique=False)

    op.create_table(
        'validation_constants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('constant_name', sa.String(100), nullable=False),
        sa.Column('value', JSONB(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('constant_name'),
    )


def downgrade() -> None:
    op.drop_table('validation_constants')
    op.drop_table('synonyms')
    op.drop_table('contextual_overrides')
    op.drop_table('group_keywords')
