"""003 add audit

Revision ID: 003a3
Revises: 002a2
Create Date: 2025-01-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

revision: str = '003a3'
down_revision: Union[str, None] = '002a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_access_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', PG_UUID(as_uuid=True), nullable=False),
        sa.Column('method_name', sa.String(100), nullable=False),
        sa.Column('params', JSONB(), nullable=True),
        sa.Column('provider_used', sa.String(50), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), nullable=True),
        sa.Column('fallback_used', sa.Boolean(), nullable=True),
        sa.Column('fallback_reason', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_dal_request', 'data_access_logs', ['request_id'], unique=False)
    op.create_index('idx_dal_created', 'data_access_logs', ['created_at'], unique=False)

    op.create_table(
        'tool_execution_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', PG_UUID(as_uuid=True), nullable=False),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('input_data', JSONB(), nullable=True),
        sa.Column('output_data', JSONB(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_tel_request', 'tool_execution_logs', ['request_id'], unique=False)
    op.create_index('idx_tel_tool', 'tool_execution_logs', ['tool_name'], unique=False)
    op.create_index('idx_tel_created', 'tool_execution_logs', ['created_at'], unique=False)

    op.create_table(
        'llm_agent_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', PG_UUID(as_uuid=True), nullable=False),
        sa.Column('iteration', sa.Integer(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('response', JSONB(), nullable=True),
        sa.Column('tool_result', JSONB(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('llm_agent_logs')
    op.drop_table('tool_execution_logs')
    op.drop_table('data_access_logs')
