from sqlalchemy import (
    Integer, String, Float, Boolean, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid

from app.db.session import Base
from app.models.sqlalchemy.compat import (
    JSONBCompat, PKColType,
)


JSONCol = JSONBCompat


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class MtrItem(Base):
    __tablename__ = "mtr_items"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    mtr_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    ksm_code: Mapped[str | None] = mapped_column(String(50), unique=True)
    card_id: Mapped[str | None] = mapped_column(String(50))
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subtype: Mapped[str | None] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(255))
    attributes: Mapped[dict] = mapped_column(JSONCol(), nullable=False, default=dict)
    gost_tu: Mapped[str | None] = mapped_column(String(255))
    standard: Mapped[str | None] = mapped_column(String(255))
    stock_qty: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(20), default="pcs")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    attributes_schema_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_mtr_item_type", "item_type"),
        Index("idx_mtr_mtr_code", "mtr_code"),
        Index("idx_mtr_ksm_code", "ksm_code"),
    )


class MtrItemHistory(Base):
    __tablename__ = "mtr_item_history"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    mtr_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    changed_by: Mapped[str | None] = mapped_column(String(100))
    old_attributes: Mapped[dict] = mapped_column(JSONCol(), default=dict)
    new_attributes: Mapped[dict] = mapped_column(JSONCol(), default=dict)


class CandidateItem(Base):
    __tablename__ = "candidate_items"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    ksm_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    short_text: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float | None] = mapped_column(Float)
    stock_category: Mapped[str | None] = mapped_column(String(100))
    business_unit: Mapped[str | None] = mapped_column(String(100))
    stock_balance: Mapped[float] = mapped_column(Float, default=0)
    planned_involvement_date: Mapped[datetime | None] = mapped_column(Date)
    forecast_involvement_date: Mapped[datetime | None] = mapped_column(Date)
    source_excel_row: Mapped[int | None] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255))
    loaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500))
    document_type: Mapped[str | None] = mapped_column(String(20))
    page_count: Mapped[int | None] = mapped_column(Integer)
    ocr_status: Mapped[str] = mapped_column(String(20), default="pending")
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_date: Mapped[datetime | None] = mapped_column(DateTime)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class ExtractedCharacteristic(Base):
    __tablename__ = "extracted_characteristics"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    page_number: Mapped[int | None] = mapped_column(Integer)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_fragment: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(20))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(100))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class GoldenDataset(Base):
    __tablename__ = "golden_dataset"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    requested_mtr: Mapped[str | None] = mapped_column(String(50))
    requested_description: Mapped[str | None] = mapped_column(Text)
    candidate_ksm: Mapped[str | None] = mapped_column(String(50))
    candidate_description: Mapped[str | None] = mapped_column(Text)
    expected_status: Mapped[str | None] = mapped_column(String(50))
    expected_reason: Mapped[str | None] = mapped_column(Text)
    has_passport: Mapped[bool] = mapped_column(Boolean, default=False)
    expert_comment: Mapped[str | None] = mapped_column(Text)


class ExpertMatch(Base):
    __tablename__ = "expert_matches"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    match_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    lot: Mapped[str | None] = mapped_column(String(50))
    requested_mtr_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    candidate_ksm_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    expert_status: Mapped[str] = mapped_column(String(50), nullable=False)
    expert_reason: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[str | None] = mapped_column(String(100))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str | None] = mapped_column(String(50))
    data: Mapped[dict] = mapped_column(JSONCol(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_logs_request", "request_id"),
        Index("idx_logs_created", "created_at"),
    )


class GroupKeyword(Base):
    __tablename__ = "group_keywords"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_group_keywords_group", "group_name"),)


class ContextualOverride(Base):
    __tablename__ = "contextual_overrides"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    trigger_phrase: Mapped[str] = mapped_column(String(255), nullable=False)
    target_group: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SynonymRecord(Base):
    __tablename__ = "synonyms"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_synonyms_group", "group_name"),)


class ValidationConstant(Base):
    __tablename__ = "validation_constants"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    constant_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSONCol(), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ValidationRule(Base):
    __tablename__ = "validation_rules"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    required_params: Mapped[list] = mapped_column(Text, nullable=False, default="[]")
    forbidden_params: Mapped[list] = mapped_column(Text, nullable=False, default="[]")
    optional_params: Mapped[list] = mapped_column(Text, nullable=False, default="[]")
    logical_conditions: Mapped[dict | None] = mapped_column(JSONCol())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DataAccessLog(Base):
    __tablename__ = "data_access_logs"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    method_name: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[dict | None] = mapped_column(JSONCol())
    provider_used: Mapped[str | None] = mapped_column(String(50))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    cache_hit: Mapped[bool | None] = mapped_column(Boolean)
    fallback_used: Mapped[bool | None] = mapped_column(Boolean)
    fallback_reason: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_dal_request", "request_id"),
        Index("idx_dal_created", "created_at"),
    )


class ToolExecutionLog(Base):
    __tablename__ = "tool_execution_logs"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict | None] = mapped_column(JSONCol())
    output_data: Mapped[dict | None] = mapped_column(JSONCol())
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    user_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_tel_request", "request_id"),
        Index("idx_tel_tool", "tool_name"),
        Index("idx_tel_created", "created_at"),
    )


class LlmAgentLog(Base):
    __tablename__ = "llm_agent_logs"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    iteration: Mapped[int | None] = mapped_column(Integer)
    prompt: Mapped[str | None] = mapped_column(Text)
    response: Mapped[dict | None] = mapped_column(JSONCol())
    tool_result: Mapped[dict | None] = mapped_column(JSONCol())
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class PipelineEdge(Base):
    __tablename__ = "pipeline_edges"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    from_ksm: Mapped[str] = mapped_column(String(50), nullable=False)
    to_ksm: Mapped[str] = mapped_column(String(50), nullable=False)
    connection_type: Mapped[str | None] = mapped_column(String(30))
    distance_m: Mapped[float | None] = mapped_column(Float)
    unit_code: Mapped[str | None] = mapped_column(String(50))
    template: Mapped[str | None] = mapped_column(String(255))
    instance: Mapped[int] = mapped_column(Integer, default=0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_pe_from", "from_ksm"),
        Index("idx_pe_to", "to_ksm"),
    )


class AutoModeEscalation(Base):
    __tablename__ = "auto_mode_escalations"

    id: Mapped[int] = mapped_column(PKColType(), primary_key=True, autoincrement=True)
    request_id: Mapped[str | None] = mapped_column(String(64))
    query: Mapped[str | None] = mapped_column(Text)
    mode_used: Mapped[str | None] = mapped_column(String(32))
    gaps: Mapped[dict | None] = mapped_column(JSONCol())
    verdict: Mapped[str | None] = mapped_column(String(16))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    llm_tokens_used: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
