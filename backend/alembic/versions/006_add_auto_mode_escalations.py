"""006 add auto_mode_escalations

Revision ID: 006a6
Revises: 005a5
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '006a6'
down_revision: Union[str, None] = '005a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auto_mode_escalations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.String(64), nullable=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('mode_used', sa.String(32), nullable=True),
        sa.Column('gaps', JSONB(), nullable=True),
        sa.Column('verdict', sa.String(16), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('llm_tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('auto_mode_escalations')
