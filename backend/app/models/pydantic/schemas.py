import uuid
from datetime import date, datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


# ---------------------------------------------------------------------------
# 2A.1 Component
# ---------------------------------------------------------------------------
class Component(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm_code: str = Field(..., description="Уникальный код KSM")
    mtr_code: Optional[str] = Field(None, description="Код MTR")
    card_id: Optional[str] = Field(None, description="ID карточки")
    item_type: str = Field(..., description="Тип изделия")
    subtype: Optional[str] = Field(None, description="Подтип")
    name: str = Field(..., description="Полное наименование")
    designation: Optional[str] = Field(None, description="Условное обозначение")
    attributes: dict = Field(default_factory=dict, description="Атрибуты изделия (JSONB)")
    gost_tu: Optional[str] = Field(None, description="ГОСТ / ТУ")
    standard: Optional[str] = Field(None, description="Стандарт")
    stock_qty: float = Field(0.0, description="Количество на складе")
    unit: str = Field("", description="Код участка")
    is_synthetic: bool = Field(False, description="Синтетическая запись")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    match_score: float = Field(0.0, description="Результат поисковой оценки")
    matched_fields: List[str] = Field(default_factory=list)
    sources: List[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2A.2 StockItem
# ---------------------------------------------------------------------------
class StockItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm_code: str
    quantity: float
    unit: str
    business_unit: Optional[str] = None
    stock_category: Optional[str] = None
    cost: Optional[float] = None
    planned_involvement_date: Optional[date] = None
    forecast_involvement_date: Optional[date] = None
    source: str = ""


# ---------------------------------------------------------------------------
# 2A.3 GraphEdge
# ---------------------------------------------------------------------------
class GraphEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_ksm: str
    to_ksm: str
    connection_type: str
    distance_m: float = 0.0
    unit_code: Optional[str] = None
    template: Optional[str] = None
    is_synthetic: bool = False


# ---------------------------------------------------------------------------
# 2A.4 Unit
# ---------------------------------------------------------------------------
class Unit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_code: str
    name: Optional[str] = None
    medium: Optional[str] = None
    components: List[str] = Field(default_factory=list)
    is_synthetic: bool = False


# ---------------------------------------------------------------------------
# 2A.5 CompatibilityContext
# ---------------------------------------------------------------------------
class CompatibilityContext(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medium: str
    pn: float
    temperature: Optional[float] = None
    climate: Optional[str] = None
    has_coating: bool = False
    gost_tu: Optional[str] = None


# ---------------------------------------------------------------------------
# 2A.6 CompatibilityResult
# ---------------------------------------------------------------------------
class CompatibilityResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    compatible: bool
    warnings: List[str] = Field(default_factory=list)
    required_actions: List[str] = Field(default_factory=list)
    source: str = ""
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# 2A.7 ExtractedParam
# ---------------------------------------------------------------------------
class ExtractedParam(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_name: str
    raw_value: str
    normalized_value: str
    unit: Optional[str] = None
    confidence: float = 0.0
    source_fragment: str = ""
    source_type: str = ""
    is_verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# 2A.8 NeighborInfo
# ---------------------------------------------------------------------------
class NeighborInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm_code: str
    item_type: str
    connection_type: str
    distance_m: float = 0.0


# ---------------------------------------------------------------------------
# 2A.9 EnhancedSearchResult
# ---------------------------------------------------------------------------
class EnhancedSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component: Component
    match_score: float = 0.0
    stock: Optional[StockItem] = None
    compatibility: Optional[CompatibilityResult] = None
    neighbors: List[NeighborInfo] = Field(default_factory=list)
    extracted_params: Optional[List[ExtractedParam]] = None
    warnings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2A.10 SearchParams
# ---------------------------------------------------------------------------
class SearchParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_type: Optional[str] = None
    dn: Optional[int] = None
    pn: Optional[float] = None
    steel_grade: Optional[str] = None
    medium: Optional[str] = None
    angle: Optional[int] = None
    climate: Optional[str] = None
    gost_tu: Optional[str] = None
    mtr_code: Optional[str] = None
    ksm_code: Optional[str] = None
    limit: int = 20
    offset: int = 0


# ---------------------------------------------------------------------------
# 2A.11 PaginatedResult
# ---------------------------------------------------------------------------
class PaginatedResult(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    items: List[T] = Field(default_factory=list)
    total_count: int = 0
    offset: int = 0
    limit: int = 20
    has_more: bool = False


# ---------------------------------------------------------------------------
# 2A.12 UnitInventory
# ---------------------------------------------------------------------------
class UnitInventory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit: Unit
    components: List[EnhancedSearchResult] = Field(default_factory=list)
    summary: dict = Field(
        default_factory=lambda: {
            "total_components": 0,
            "h2s_compatible": 0,
            "out_of_stock": 0,
            "low_stock": 0,
        }
    )


# ---------------------------------------------------------------------------
# 2A.13 ComponentHistory
# ---------------------------------------------------------------------------
class ComponentHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm_code: str
    changed_at: datetime
    changed_by: Optional[str] = None
    old_attributes: dict = Field(default_factory=dict)
    new_attributes: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 2A.14 KsmSuggestion
# ---------------------------------------------------------------------------
class KsmSuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm_code: str
    mtr_code: Optional[str] = None
    name: str
    confidence: float = 0.0
    matched_params: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2A.15 DocumentMetadata
# ---------------------------------------------------------------------------
class DocumentMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    file_name: str
    status: str = "pending"
    error_message: Optional[str] = None
    ocr_confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ===========================================================================
# Request / Response schemas
# ===========================================================================

class SearchRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str
    mode: str = "deterministic"
    top_k: int = 20
    filters: Optional[dict] = None


class SearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = Field("", description="Исходный запрос (ТЗ 11.2)")
    mode: str = Field("deterministic", description="Режим исполнения (ТЗ 11.2)")
    status: str = Field("", description="ТЗ-статус ответа: соответствует | потенциальный аналог | не соответствует | нет данных | требует проверки | требует экспертной проверки")
    results: list = Field(default_factory=list, description="Список результатов (ТЗ 11.2)")
    warnings: list = Field(default_factory=list)
    recommendations: list = Field(default_factory=list)
    requires_expert: bool = False
    expert_review_id: Optional[str] = Field(None, description="Идентификатор запроса на экспертную проверку")
    execution_time_ms: float = 0.0
