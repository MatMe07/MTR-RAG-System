"""007 add document_links and passport columns

Revision ID: 007a7
Revises: 006a6
Create Date: 2026-09-07 00:00:00.000000

Фаза 3 — Паспорта/Celery:
- таблица document_links (связи паспорт→KSM с порогами).
- колонки documents: task_id, processing_progress, error_message,
  needs_review, page_texts — для состояния Celery-задачи, прогресса и
  постраничного OCR-текста.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '007a7'
down_revision: Union[str, None] = '006a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_links',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(50), nullable=False),
        sa.Column('ksm_code', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('method', sa.String(20), nullable=True),
        sa.Column('needs_review', sa.Boolean(), nullable=True),
        sa.Column('linked', sa.Boolean(), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'ksm_code', name='uq_document_links_doc_ksm'),
    )
    op.create_index('ix_document_links_document_id', 'document_links', ['document_id'], unique=False)
    op.create_index('ix_document_links_ksm_code', 'document_links', ['ksm_code'], unique=False)

    op.add_column('documents', sa.Column('task_id', sa.String(64), nullable=True))
    op.add_column('documents', sa.Column('processing_progress', sa.Float(), nullable=True, server_default='0'))
    op.add_column('documents', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('needs_review', sa.Boolean(), nullable=True, server_default=sa.false()))
    op.add_column('documents', sa.Column('page_texts', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'page_texts')
    op.drop_column('documents', 'needs_review')
    op.drop_column('documents', 'error_message')
    op.drop_column('documents', 'processing_progress')
    op.drop_column('documents', 'task_id')
    op.drop_index('ix_document_links_ksm_code', table_name='document_links')
    op.drop_index('ix_document_links_document_id', table_name='document_links')
    op.drop_table('document_links')