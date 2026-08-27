"""005 add validation

Revision ID: 005a5
Revises: 004a4
Create Date: 2025-01-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision: str = '005a5'
down_revision: Union[str, None] = '004a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'validation_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('item_type', sa.String(50), nullable=False),
        sa.Column('required_params', ARRAY(sa.String()), nullable=False),
        sa.Column('forbidden_params', ARRAY(sa.String()), nullable=False),
        sa.Column('optional_params', ARRAY(sa.String()), nullable=False),
        sa.Column('logical_conditions', JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_type'),
    )


def downgrade() -> None:
    op.drop_table('validation_rules')
