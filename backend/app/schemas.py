
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class Geometry(BaseModel):
    dn: Optional[float] = Field(None, description="Условный проход или основной диаметр")
    d1: Optional[float] = Field(None, description="Первый/больший диаметр для переходов и тройников")
    d2: Optional[float] = Field(None, description="Второй/меньший диаметр для переходов и тройников")
    wall_thickness: Optional[float] = Field(None, description="Основная толщина стенки")
    wall_thickness_2: Optional[float] = Field(None, description="Дополнительная толщина стенки")
    angle: Optional[float] = Field(None, description="Угол для отводов: 30, 45, 60, 90")
    radius: Optional[str] = Field(None, description="Радиус или геометрический признак, например 1.5D или 5D")


class Pressure(BaseModel):
    pn: Optional[float] = Field(None, description="Номинальное давление PN/Ру")
    working_pressure_mpa: Optional[float] = Field(None, description="Рабочее давление в МПа")
    test_pressure_mpa: Optional[float] = Field(None, description="Испытательное давление в МПа")
    raw_value: Optional[str] = Field(None, description="Исходная запись давления из источника")


class Material(BaseModel):
    steel_grade: Optional[str] = Field(None, description="Марка стали, например 09Г2С")
    strength_class: Optional[str] = Field(None, description="Класс прочности, например К48")
    standard: Optional[str] = Field(None, description="ГОСТ/ТУ на материал")


class Environment(BaseModel):
    medium: Optional[str] = Field(None, description="Рабочая среда: газ, нефть, вода, H2S, CO2")
    h2s_confirmed: Optional[bool] = Field(None, description="Подтверждена ли пригодность для H2S")
    co2_confirmed: Optional[bool] = Field(None, description="Подтверждена ли пригодность для CO2")
    temperature_min_c: Optional[float] = Field(None, description="Минимальная температура эксплуатации")
    climate_version: Optional[str] = Field(None, description="Климатическое исполнение: У, ХЛ, УХЛ")


class Coating(BaseModel):
    inner_coating: Optional[bool] = Field(None, description="Есть ли внутреннее покрытие")
    outer_coating: Optional[bool] = Field(None, description="Есть ли наружное покрытие")
    coating_type: Optional[str] = Field(None, description="Тип покрытия")
    coating_standard: Optional[str] = Field(None, description="ГОСТ/ТУ на покрытие")


class Normative(BaseModel):
    gost_tu: Optional[str] = Field(None, description="ГОСТ или ТУ на изготовление изделия")
    lnd_sections: List[str] = Field(default_factory=list, description="Ссылки на разделы ЛНД")


class Extraction(BaseModel):
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Общая уверенность извлечения")
    method: Optional[str] = Field(None, description="Источник извлечения: user_query, excel, ocr, llm, expert_edit")
    missing_fields: List[str] = Field(default_factory=list, description="Поля, которые не удалось извлечь")


class Source(BaseModel):
    type: str = Field(..., description="Тип источника: passport, excel, lnd, user_query")
    file: Optional[str] = Field(None, description="Имя файла")
    page: Optional[int] = Field(None, description="Номер страницы")
    row: Optional[int] = Field(None, description="Номер строки Excel")
    fragment: Optional[str] = Field(None, description="Фрагмент текста-источника")


class ItemCard(BaseModel):
    card_id: Optional[str] = Field(None, description="Внутренний идентификатор карточки")
    mtr_code: Optional[str] = Field(None, description="Код МТР")
    ksm_code: Optional[str] = Field(None, description="Код КСМ")
    item_type: str = Field(..., description="Базовый тип изделия")
    subtype: Optional[str] = Field(None, description="Подтип или конструктивное исполнение")
    designation: Optional[str] = Field(None, description="Условное обозначение изделия")
    name: Optional[str] = Field(None, description="Человекочитаемое наименование изделия")
    
    geometry: Optional[Geometry] = Field(None, description="Геометрические параметры")
    pressure: Optional[Pressure] = Field(None, description="Параметры давления")
    material: Optional[Material] = Field(None, description="Материалы и классы прочности")
    environment: Optional[Environment] = Field(None, description="Условия эксплуатации")
    coating: Optional[Coating] = Field(None, description="Покрытия")
    normative: Optional[Normative] = Field(None, description="Нормативная документация")
    
    extraction: Optional[Extraction] = Field(None, description="Метаданные извлечения")
    sources: List[Source] = Field(..., description="Ссылки на источники данных")

    @field_validator("item_type")
    def validate_item_type(cls, v):
        allowed = ["отвод", "труба", "задвижка", "заглушка", "переход", "тройник"]
        if v.lower() not in allowed:
            raise ValueError(f"item_type должен быть одним из: {allowed}")
        return v.lower()



class SearchRequest(BaseModel):
    query: str = Field(..., description="Текстовый запрос пользователя")
    mode: str = Field("hybrid", description="Режим поиска: exact, filter, vector, hybrid, passport")
    filters: Optional[Dict[str, Any]] = Field(None, description="Фильтры: dn, angle, pressure, material")
    top_k: int = Field(20, description="Количество результатов", ge=1, le=100)
    document_id: Optional[int] = Field(None, description="ID документа для режима passport")


class RuleTrace(BaseModel):
    rule_id: str = Field(..., description="Идентификатор правила")
    reaction: str = Field(..., description="Тип реакции: hard_filter, warning, expert_comment, score_penalty")
    message: str = Field(..., description="Сообщение от правила")


class MatchResult(BaseModel):
    rank: int = Field(..., description="Позиция кандидата в выдаче")
    mtr_code: Optional[str] = Field(None, description="Код МТР кандидата")
    ksm_code: Optional[str] = Field(None, description="Код КСМ кандидата")
    candidate_name: Optional[str] = Field(None, description="Наименование кандидата")
    match_percent: Optional[float] = Field(None, ge=0, le=100, description="Оценка близости кандидата")
    status: str = Field(..., description="Рекомендательный статус")
    matched_params: List[str] = Field(default_factory=list, description="Совпавшие параметры")
    mismatched_params: List[str] = Field(default_factory=list, description="Расходящиеся параметры")
    missing_params: List[str] = Field(default_factory=list, description="Недостающие параметры")
    warnings: List[str] = Field(default_factory=list, description="Предупреждения для эксперта")
    expert_comment: Optional[str] = Field(None, description="Короткий комментарий для эксперта")
    rule_trace: List[RuleTrace] = Field(default_factory=list, description="Сработавшие правила")
    sources: List[Source] = Field(default_factory=list, description="Источники")

    rank: int
    mtr_code: str
    ksm_code: Optional[str]
    candidate_name: str
    sources: List[Source]
    stock_quantity: Optional[float]
    stock_cost: Optional[float]
    
    @field_validator("status")
    def validate_status(cls, v):
        allowed = ["соответствует", "потенциальный аналог", "требует проверки", "низкая релевантность", "нет данных"]
        if v not in allowed:
            raise ValueError(f"status должен быть одним из: {allowed}")
        return v


class SearchResponse(BaseModel):
    search_id: str = Field(..., description="Идентификатор поиска для экспертного решения")
    query: str = Field(..., description="Исходный запрос")
    requested_card: Any = Field(..., description="Карточка, извлечённая из запроса или паспорта")
    candidates: List[MatchResult] = Field(..., description="Список кандидатов")
    total_found: int = Field(..., description="Всего найдено")
    search_time_ms: float = Field(..., description="Время выполнения поиска, мс")


class UploadResponse(BaseModel):
    success: bool
    document_id: int
    message: str
    extracted_card: Optional[ItemCard] = None
    pages_processed: int = 0
    ocr_confidence: float = 0.0


class MatchRequest(BaseModel):
    requested_card: ItemCard = Field(..., description="Заявленная карточка")
    candidate_card: ItemCard = Field(..., description="Карточка кандидата")


class MatchResponse(BaseModel):
    status: str
    score: float
    matched_params: List[str] = Field(default_factory=list)
    mismatched_params: List[str] = Field(default_factory=list)
    missing_params: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    expert_comment: Optional[str] = None
    rule_trace: List[RuleTrace] = Field(default_factory=list)


class ExtractCardRequest(BaseModel):
    text: str = Field(..., description="Текст для извлечения")
    source: Source = Field(..., description="Источник")


class ExpertReviewRequest(BaseModel):
    search_id: str = Field(..., description="ID поискового запроса")
    candidate_ksm_code: str = Field(..., description="Код КСМ кандидата")
    decision: str = Field(..., description="Решение: approve, reject, need_more_info")
    comment: str = Field(..., description="Комментарий эксперта")
    reviewer: str = Field(..., description="Кто проверил")


class ExpertReviewResponse(BaseModel):
    success: bool
    message: str
    review_id: int



class ParsedQuery(BaseModel):
    original_query: str
    card: Optional[ItemCard] = None
    confidence: float = 1.0


class DocumentInfo(BaseModel):
    id: int
    file_name: str
    file_type: str
    page_count: int
    ocr_status: str
    ocr_confidence: Optional[float]
    upload_date: datetime


class PageInfo(BaseModel):
    page_number: int
    ocr_text: Optional[str]
    ocr_confidence: Optional[float]
    rotation_angle: float
    table_json: Optional[Dict[str, Any]]


class CharacteristicExtracted(BaseModel):
    field_name: str
    raw_value: Optional[str]
    normalized_value: Optional[str]
    unit_code: Optional[str]
    confidence: float
    source_fragment: Optional[str]


class HealthResponse(BaseModel):
    status: str = "ok"
    database: bool
    qdrant: bool
    version: str = "0.1.0"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
