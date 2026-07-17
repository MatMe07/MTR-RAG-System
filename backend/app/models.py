from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone


Base = declarative_base()


class ItemType(Base):
    __tablename__ = "item_types"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)


class Subtype(Base):
    __tablename__ = "subtypes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    item_type_code = Column(String(20), nullable=False, index=True)


class SteelGrade(Base):
    __tablename__ = "steel_grades"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)


class StrengthClass(Base):
    __tablename__ = "strength_classes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)


class ClimateVersion(Base):
    __tablename__ = "climate_versions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)


class Standard(Base):
    __tablename__ = "standards"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(String(20), nullable=False)  # ГОСТ, ТУ, ОСТ


class MediumType(Base):
    __tablename__ = "medium_types"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    is_corrosive = Column(Boolean, default=True)


class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)


class OntologyTerm(Base):
    __tablename__ = "ontology_terms"
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(100), unique=True, nullable=False, index=True)
    normalized_term = Column(String(100), nullable=False)
    definition = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)


class Synonym(Base):
    __tablename__ = "synonyms"
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(100), nullable=False, index=True)
    synonym = Column(String(100), nullable=False)
    normalized_value = Column(String(100), nullable=False)
    
    __table_args__ = (
        UniqueConstraint("term", "synonym", name="uq_synonym_term"),
    )


class DesignationPattern(Base):
    __tablename__ = "designation_patterns"
    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(50), nullable=False)
    pattern = Column(String(255), nullable=False)
    field_order = Column(JSON, nullable=False)
    example = Column(String(255), nullable=True)


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # excel, passport, lnd
    upload_date = Column(DateTime, default=datetime.utcnow)
    page_count = Column(Integer, nullable=True)
    ocr_status = Column(String(20), default="pending")
    ocr_confidence = Column(Float, nullable=True)
    
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    characteristics = relationship("ExtractedCharacteristic", back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "document_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    rotation_angle = Column(Float, default=0.0)
    table_json = Column(JSON, nullable=True)
    
    document = relationship("Document", back_populates="pages")
    
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_page"),
        Index("idx_document_pages_document_id", "document_id"),
    )


class ExtractedCharacteristic(Base):
    __tablename__ = "extracted_characteristics"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=True)
    field_name = Column(String(100), nullable=False)
    raw_value = Column(String(255), nullable=True)
    normalized_value = Column(String(255), nullable=True)
    unit_code = Column(String(20), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    source_fragment = Column(Text, nullable=True)
    
    document = relationship("Document", back_populates="characteristics")


class MTRItem(Base):
    __tablename__ = "mtr_items"
    
    id = Column(Integer, primary_key=True, index=True)
    mtr_code = Column(String(50), unique=True, nullable=False, index=True)
    ksm_code = Column(String(50), index=True, nullable=True)
    lot = Column(String(50), nullable=True)
    material_class = Column(String(100), nullable=True)
    short_text = Column(Text, nullable=True)
    
    # Денормализованные параметры
    item_type = Column(String(20), nullable=False, index=True)
    subtype = Column(String(20), nullable=True, index=True)
    designation = Column(String(255), nullable=True)
    
    dn = Column(Float, nullable=True, index=True)
    d1 = Column(Float, nullable=True) 
    d2 = Column(Float, nullable=True) 
    
    wall_thickness = Column(Float, nullable=True)
    angle = Column(Float, nullable=True, index=True)
    pressure = Column(Float, nullable=True, index=True)
    
    strength_class = Column(String(10), nullable=True, index=True)
    steel_grade = Column(String(20), nullable=True, index=True)
    medium = Column(String(20), nullable=True, index=True)
    
    inner_coating = Column(Boolean, default=False)
    outer_coating = Column(Boolean, default=False)
    climate_version = Column(String(10), nullable=True, index=True)
    gost_or_tu = Column(String(50), nullable=True)
    
    source_excel_row = Column(Integer, nullable=True)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    source_document = relationship("Document")
    
    __table_args__ = (
        Index("idx_mtr_items_type_dn", "item_type", "dn"),
        Index("idx_mtr_items_dn_angle", "dn", "angle"),
    )


class KSMItem(Base):
    __tablename__ = "ksm_items"
    
    id = Column(Integer, primary_key=True, index=True)
    ksm_code = Column(String(50), unique=True, nullable=False, index=True)
    short_text = Column(Text, nullable=True)
    
    quantity = Column(Float, nullable=True)
    unit = Column(String(20), nullable=True)
    cost = Column(Float, nullable=True)
    stock_category = Column(String(100), nullable=True)
    business_unit = Column(String(100), nullable=True)
    planned_involvement_date = Column(DateTime, nullable=True)
    forecast_involvement_date = Column(DateTime, nullable=True)
    
    # Денормализованные параметры
    item_type = Column(String(20), nullable=True, index=True)
    subtype = Column(String(20), nullable=True, index=True)
    designation = Column(String(255), nullable=True)
    dn = Column(Float, nullable=True, index=True)
    wall_thickness = Column(Float, nullable=True)
    angle = Column(Float, nullable=True, index=True)
    pressure = Column(Float, nullable=True, index=True)
    strength_class = Column(String(10), nullable=True, index=True)
    steel_grade = Column(String(20), nullable=True, index=True)
    medium = Column(String(20), nullable=True, index=True)
    inner_coating = Column(Boolean, default=False)
    outer_coating = Column(Boolean, default=False)
    climate_version = Column(String(10), nullable=True, index=True)
    gost_or_tu = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class ExpertMatch(Base):
    __tablename__ = "expert_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    lot = Column(String(50), nullable=True)
    requested_mtr_code = Column(String(50), ForeignKey("mtr_items.mtr_code", ondelete="CASCADE"), nullable=False, index=True)
    candidate_ksm_code = Column(String(50), ForeignKey("ksm_items.ksm_code", ondelete="CASCADE"), nullable=False, index=True)
    expert_status = Column(String(50), nullable=False)
    expert_reason = Column(Text, nullable=True)
    confirmed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    requested_item = relationship("MTRItem", foreign_keys=[requested_mtr_code])
    candidate_item = relationship("KSMItem", foreign_keys=[candidate_ksm_code])


class MatchingRule(Base):
    __tablename__ = "matching_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(20), nullable=False)  # blocker, penalty, allowed_replacement
    parameter = Column(String(50), nullable=False)
    from_value = Column(String(100), nullable=True)
    to_value = Column(String(100), nullable=True)
    allowed = Column(Boolean, default=True)
    condition = Column(Text, nullable=True)
    penalty = Column(Integer, default=0)
    source = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class ReplacementSet(Base):
    __tablename__ = "replacement_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    target_item_type = Column(String(20), nullable=False)
    target_angle = Column(Float, nullable=False)
    target_dn = Column(Float, nullable=True)
    component_item_type = Column(String(20), nullable=False)
    component_angle = Column(Float, nullable=False)
    component_dn = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    condition = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String(50), unique=True, nullable=False, index=True)
    input_type = Column(String(20), nullable=False)
    input_data = Column(JSON, nullable=False)
    expected_mtr_code = Column(String(50), nullable=True, index=True)
    expected_ksm_code = Column(String(50), nullable=True, index=True)
    expected_status = Column(String(50), nullable=True)
    expected_reason = Column(Text, nullable=True)
    actual_mtr_code = Column(String(50), nullable=True)
    actual_status = Column(String(50), nullable=True)
    passed = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    tested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class ExpertReviewLog(Base):
    __tablename__ = "expert_review_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(String(50), nullable=True, index=True)
    candidate_ksm_code = Column(String(50), nullable=False, index=True)
    user_comment = Column(Text, nullable=True)
    expert_decision = Column(String(50), nullable=False)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, default=datetime.now(timezone.utc))
    
class SearchLog(Base):
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(20), nullable=False)  # text, passport, excel
    result_count = Column(Integer, nullable=True)
    top_mtr_codes = Column(JSON, nullable=True)  
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_search_logs_user_id", "user_id"),
        Index("idx_search_logs_created_at", "created_at"),
    )
