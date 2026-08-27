"""001 initial

Revision ID: 001a1
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

revision: str = '001a1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    op.create_table(
        'mtr_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('mtr_code', sa.String(50), nullable=False),
        sa.Column('ksm_code', sa.String(50), nullable=True),
        sa.Column('card_id', sa.String(50), nullable=True),
        sa.Column('item_type', sa.String(50), nullable=False),
        sa.Column('subtype', sa.String(50), nullable=True),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('designation', sa.String(255), nullable=True),
        sa.Column('attributes', JSONB(), nullable=False),
        sa.Column('gost_tu', sa.String(255), nullable=True),
        sa.Column('standard', sa.String(255), nullable=True),
        sa.Column('stock_qty', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=True),
        sa.Column('attributes_schema_version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mtr_code'),
        sa.UniqueConstraint('ksm_code'),
    )
    op.create_index('idx_mtr_item_type', 'mtr_items', ['item_type'], unique=False)
    op.create_index('idx_mtr_mtr_code', 'mtr_items', ['mtr_code'], unique=False)
    op.create_index('idx_mtr_ksm_code', 'mtr_items', ['ksm_code'], unique=False)
    op.execute(
        'CREATE INDEX idx_mtr_attributes_gin ON mtr_items USING gin (attributes)'
    )

    op.create_table(
        'candidate_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('ksm_code', sa.String(50), nullable=False),
        sa.Column('short_text', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('stock_category', sa.String(100), nullable=True),
        sa.Column('business_unit', sa.String(100), nullable=True),
        sa.Column('stock_balance', sa.Float(), nullable=True),
        sa.Column('planned_involvement_date', sa.Date(), nullable=True),
        sa.Column('forecast_involvement_date', sa.Date(), nullable=True),
        sa.Column('source_excel_row', sa.Integer(), nullable=True),
        sa.Column('source_file', sa.String(255), nullable=True),
        sa.Column('loaded_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_candidate_items_ksm_code', 'candidate_items', ['ksm_code'], unique=False)

    op.create_table(
        'documents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(50), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('document_type', sa.String(20), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('ocr_status', sa.String(20), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('upload_date', sa.DateTime(), nullable=True),
        sa.Column('processed_date', sa.DateTime(), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id'),
    )

    op.create_table(
        'extracted_characteristics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(50), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=True),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('source_fragment', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(20), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verified_by', sa.String(100), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_extracted_characteristics_document_id', 'extracted_characteristics', ['document_id'], unique=False)

    op.create_table(
        'golden_dataset',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('case_id', sa.String(50), nullable=False),
        sa.Column('requested_mtr', sa.String(50), nullable=True),
        sa.Column('requested_description', sa.Text(), nullable=True),
        sa.Column('candidate_ksm', sa.String(50), nullable=True),
        sa.Column('candidate_description', sa.Text(), nullable=True),
        sa.Column('expected_status', sa.String(50), nullable=True),
        sa.Column('expected_reason', sa.Text(), nullable=True),
        sa.Column('has_passport', sa.Boolean(), nullable=True),
        sa.Column('expert_comment', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_id'),
    )

    op.create_table(
        'expert_matches',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('match_id', sa.String(50), nullable=True),
        sa.Column('lot', sa.String(50), nullable=True),
        sa.Column('requested_mtr_code', sa.String(50), nullable=False),
        sa.Column('candidate_ksm_code', sa.String(50), nullable=False),
        sa.Column('expert_status', sa.String(50), nullable=False),
        sa.Column('expert_reason', sa.Text(), nullable=True),
        sa.Column('confirmed_by', sa.String(100), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id'),
    )
    op.create_index('ix_expert_matches_requested_mtr_code', 'expert_matches', ['requested_mtr_code'], unique=False)
    op.create_index('ix_expert_matches_candidate_ksm_code', 'expert_matches', ['candidate_ksm_code'], unique=False)

    op.create_table(
        'logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', PG_UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_logs_request', 'logs', ['request_id'], unique=False)
    op.create_index('idx_logs_created', 'logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('logs')
    op.drop_table('expert_matches')
    op.drop_table('golden_dataset')
    op.drop_table('extracted_characteristics')
    op.drop_table('documents')
    op.drop_table('candidate_items')
    op.drop_table('mtr_items')
    op.drop_table('users')
