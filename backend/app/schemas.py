
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
    item_type: Optional[str] = Field(None, description="Базовый тип изделия")
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

    # @field_validator("item_type")
    # def validate_item_type(cls, v):
    #     allowed = ["отвод", "труба", "задвижка", "заглушка", "переход", "тройник"]
    #     if v.lower() not in allowed:
    #         raise ValueError(f"item_type должен быть одним из: {allowed}")
    #     return v.lower()

class QueryIntent(BaseModel):
    """Интент запроса"""
    operation: Optional[str] = None
    workflow: Optional[str] = None

    unit_id: Optional[str] = None
    component_id: Optional[str] = None

    stock_required: bool = False
    stock_missing: bool = False
    stock_present_only: bool = False

    quantity: Optional[float] = None
    units_count: Optional[int] = None

    comparison_required: bool = False
    explanation_required: bool = False
    plan_required: bool = False
    documents_required: bool = False
    normative_required: bool = False


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
    explanation: Optional[str] = Field(None, description="Объяснение результата")
    
    stock_quantity: Optional[float]
    stock_cost: Optional[float]
    
    @field_validator("status")
    def validate_status(cls, v):
        allowed = ["соответствует", "потенциальный аналог", "требует проверки", "низкая релевантность", "нет данных", "не соответствует"]
        if v not in allowed:
            raise ValueError(f"status должен быть одним из: {allowed}")
        return v


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
    """Результат парсинга пользовательского запроса для инженерной системы."""
    
    # ===== Исходный запрос =====
    original_query: str = Field(..., description="Исходный текст запроса")

    # ===== Интентный слой (1D): заполняется detect.enrich_parsed() =====
    intents: List[str] = Field(
        default_factory=list,
        description="Определённые интенты (см. intent.matrix, до 24)",
    )
    status: str = Field(
        default="",
        description="Статус разбора: COMPLETE / PARTIAL / UNCLEAR / REQUIRES_EXPERT",
    )
    missing_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Интент → недостающие обязательные параметры",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Плоские извлечённые параметры (для filter_params_for_intent)",
    )
    
    # ===== Операции (что нужно сделать) =====
    operations: List[str] = Field(
        default_factory=list,
        description="Список операций: search, replace, check, plan, explain, inventory, impact, assemble, calculate, document, repair"
    )
    
    # ===== Целевые объекты =====
    item_types: List[str] = Field(
        default_factory=list,
        description="Типы изделий: отвод, труба, задвижка, заглушка, переход, тройник, кран, фланец, прокладка, болт"
    )
    component_ids: List[str] = Field(
        default_factory=list,
        description="ID компонентов: COMP-XXX"
    )
    unit_ids: List[str] = Field(
        default_factory=list,
        description="ID участков: UNIT-XXX"
    )
    
    # ===== Карточки =====
    card: Optional[ItemCard] = Field(
        None,
        description="Одна основная карточка (для простых запросов)"
    )
    cards: List[ItemCard] = Field(
        default_factory=list,
        description="Несколько карточек (для составных запросов)"
    )
    
    # ===== Фильтры для поиска =====
    technical_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Технические фильтры: dn, angle, wall_thickness, pressure, steel_grade, strength_class, medium"
    )
    stock_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Складские фильтры: quantity_min, quantity_max, location, stock_category"
    )
    
    # ===== Параметры количества, сроков и сортировки =====
    units_count: Optional[int] = Field(None, description="Количество участков (множитель), например трёх таких же участков -> 3")
    length_m: Optional[float] = Field(None, description="Длина нового участка в метрах, например длиной сто метров -> 100")
    limit: Optional[int] = Field(None, description="Лимит выдаваемых позиций (топ-N), например выбери пять деталей -> 5")
    timeframe: Optional[str] = Field(None, description="Временные рамки: next_week, next_month, next_year, immediate")
    urgency: Optional[str] = Field(None, description="Срочность: high")
    sort_by: Optional[str] = Field(None, description="Сортировка результатов: procurement_urgency, risk, priority")
    on_stock: Optional[bool] = Field(None, description="True=только в наличии, False=только отсутствующие на складе")
    not_installed: Optional[bool] = Field(None, description="True=не установлены ни на одном участке")
    
    # ===== Изменения и их анализ =====
    proposed_changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Предлагаемые изменения: from_value → to_value (например, DN150 → DN200)"
    )
    impact_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Анализ влияния: что проверить при замене, какие детали затронуты"
    )
    
    # ===== Контекст =====
    unit_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Контекст участка: unit_id, medium, temperature, pressure"
    )
    component_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Контекст компонента: component_id, position, connections"
    )
    
    # ===== Ссылки на нормативную базу =====
    references: List[str] = Field(
        default_factory=list,
        description="Упомянутые ГОСТы, ТУ, паспорта"
    )
    
    # ===== Неоднозначности =====
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Что нужно уточнить у пользователя"
    )
    
    # ===== Требуемые возможности =====
    required_agents: List[str] = Field(
        default_factory=list,
        description="Какие агенты нужны: search, inventory, rules, knowledge, topology, impact, plan, human"
    )
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="Свободное описание требуемых возможностей"
    )
    
    # ===== Уверенность =====
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Общая уверенность в парсинге"
    )
    confidence_details: Dict[str, float] = Field(
        default_factory=dict,
        description="Детали уверенности по каждому полю"
    )
    
    # ===== Интентный слой (Этап 1, §1B–1H) =====
    intents: List[str] = Field(
        default_factory=list,
        description="Гранулярные интенты в порядке приоритета (FIND_BY_PARAMS, CHECK_STOCK, ...)"
    )
    status: str = Field(
        default="",
        description="Статус полноты запроса: COMPLETE | PARTIAL | REQUIRES_EXPERT | UNCLEAR"
    )
    missing_params: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Недостающие обязательные параметры по каждому интенту"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Объединённые параметры запроса (filter_params_for_intent)"
    )


class AgentRequest(BaseModel):
    """Запрос к агентскому слою."""
    query: str = Field(..., description="Пользовательский запрос")


class RouteRequest(BaseModel):
    """Запрос маршрутизации (L4)."""
    query: str = Field(..., description="Пользовательский запрос")


class RouteResponse(BaseModel):
    """Решение маршрутизатора: ordinary | agent | clarification."""
    route: str = Field(..., description="ordinary | agent | clarification")
    intent: str = Field("", description="Интент запроса")
    intent_label: str = Field("", description="Человекочитаемое имя интента")
    mode: str = Field("", description="Режим исполнения")
    reasons: List[str] = Field(default_factory=list, description="Причины решения")
    required_tools: List[str] = Field(default_factory=list, description="Тулы для агентного пути")
    exact_codes: List[str] = Field(default_factory=list, description="Точные коды из запроса")
    missing_parameters: List[str] = Field(default_factory=list, description="Чего не хватает")
    llm_refined: bool = Field(False, description="Уточнял ли решение LLM")
    router_confidence: Optional[float] = Field(None, description="Уверенность LLM-маршрутизатора")
    parsed_query: Optional[ParsedQuery] = Field(
        None,
        description="Структурированный запрос, сформированный парсером",
    )


class AgentSource(BaseModel):
    """Источник факта в ответе агента."""
    kind: str = Field(..., description="catalog, stock, object_graph, passport, tu, lnd, standard, regulation, expert_decisions")
    id: Optional[str] = Field(None, description="Идентификатор источника (card_id, unit_id, source_id и т.п.)")
    fragment: Optional[str] = Field(None, description="Фрагмент/краткое описание источника")


class AgentComponent(BaseModel):
    """Одна позиция в ответе агента."""
    mtr_code: Optional[str] = None
    ksm_code: Optional[str] = None
    name: Optional[str] = Field(None, description="Наименование детали")
    item_type: Optional[str] = None
    quantity: Optional[float] = Field(None, description="Остаток или рекомендуемое количество")
    status: Optional[str] = Field(None, description="Статус/причина включения в ответ")
    detail: Optional[str] = Field(None, description="Дополнительное объяснение")
    source_id: Optional[str] = Field(None, description="card_id или component_id источника")
    match_score: Optional[float] = Field(None, description="Оценка совпадения 0..1")
    match_percent: Optional[int] = Field(None, description="Оценка совпадения в процентах 0..100")
    tz_status: Optional[str] = Field(None, description="ТЗ-статус кандидата: соответствует | потенциальный аналог | не соответствует")
    matched_params: List[str] = Field(default_factory=list, description="Совпавшие параметры (ТЗ 11.2)")
    mismatched_params: List[str] = Field(default_factory=list, description="Расходящиеся параметры (ТЗ 11.2)")
    missing_params: List[str] = Field(default_factory=list, description="Параметры без данных в карточке (ТЗ 11.2)")


class AgentAnswer(BaseModel):
    """Структурированный ответ агентского слоя."""
    query: str = Field(..., description="Исходный запрос")
    intent: Optional[str] = Field(None, description="Класс интента: catalog_search, replacement, inventory, maintenance, object_configuration, document_search, impact_analysis, equipment_guidance")
    intent_label: Optional[str] = Field(None, description="Человекочитаемое имя интента")
    route: Optional[str] = Field(None, description="ordinary | agent | clarification")
    mode: Optional[str] = Field(None, description="Режим исполнения")
    tools_used: List[str] = Field(default_factory=list, description="Запущенные тулы")
    answer: str = Field(default="", description="Текстовый ответ пользователю")
    explanation: Optional[str] = Field(
        None,
        description="Холистическое объяснение ответа (5A.3): LLM-генеративное для UNCLEAR/EXPERT/«объясни»",
    )
    components: List[AgentComponent] = Field(default_factory=list, description="Позиции ответа")
    warnings: List[str] = Field(default_factory=list, description="Предупреждения")
    warning_categories: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Предупреждения, сгруппированные по категориям (вместо единого плоского списка)",
    )
    purchase_recommendation: Optional[str] = Field(
        None,
        description="Итоговая рекомендация по закупке (для инвентаризации: что срочно, что можно позже)",
    )
    sources: List[AgentSource] = Field(default_factory=list, description="Источники")
    missing_parameters: List[str] = Field(default_factory=list, description="Чего не хватает для полного ответа")
    human_review_required: bool = Field(False, description="Требуется ли проверка экспертом")
    status: str = Field("", description="ТЗ-статус ответа (ЭТАП 5): соответствует | потенциальный аналог | не соответствует | нет данных | требует проверки | требует экспертной проверки")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации по ответу (ТЗ 11.2)")
    expert_review_id: Optional[str] = Field(None, description="Идентификатор запроса на экспертную проверку")
    parsed_confidence: Optional[float] = Field(None, description="Уверенность парсера")
    parsed_query: Optional[ParsedQuery] = Field(
        None,
        description="Структурированный запрос, использованный агентом",
    )
    review_verdict: Optional[str] = Field(None, description="Вердикт ревьюера: pass | needs_review")
    review_issues: List[str] = Field(default_factory=list, description="Замечания ревьюера")
    verification_verdict: Optional[str] = Field(
        None, description="Вердикт quality gate (auto-режим): pass | review"
    )
    verification_reasons: List[str] = Field(
        default_factory=list, description="Причины вердикта quality gate"
    )
    mode_refined: Optional[str] = Field(
        None, description="Фактический подрежим auto: auto | auto_llm_refine | None"
    )
    llm_refine_failed: Optional[bool] = Field(
        None, description="True если LLM-doоформление не помогло (still_unclear)"
    )


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


class CatalogProperty(BaseModel):
    """Одно свойство карточки каталога (элемент properties.*)."""

    value: Any = Field(None, description="Значение свойства (число/строка/список/булево)")
    value_type: Optional[str] = Field(None, description="Тип значения: number/string/boolean/list")
    unit: Optional[str] = Field(None, description="Единица измерения (mm, MPa и т.п.)")
    status: Optional[str] = Field(None, description="Статус: normalized/inferred/confirmed")
    confidence: Optional[float] = Field(None, description="Уверенность 0..1")
    source_fragment_ids: List[str] = Field(default_factory=list, description="Источники фрагментов")


class CatalogCodes(BaseModel):
    """Коды карточки каталога."""

    mtr_code: Optional[str] = Field(None, description="Код МТР")
    ksm_code: Optional[str] = Field(None, description="Код КСМ")


class CatalogDcd(BaseModel):
    """DCD-контейнер карточки каталога."""

    domain: Dict[str, Any] = Field(default_factory=dict, description="Домен")
    collection: Dict[str, Any] = Field(default_factory=dict, description="Коллекция")
    document: Dict[str, Any] = Field(default_factory=dict, description="Документ")


class CatalogCard(BaseModel):
    """Карточка каталога МТР/КСМ (из regulated_mtr_catalog_1000.jsonl).

    Схема мягкая (extra="ignore", поля опциональны), чтобы валидировать
    реальные карточки репозитория без их нормализации.
    """

    schema_version: Optional[str] = Field(None, description="Версия схемы, например 2.0")
    card_id: str = Field(..., description="Идентификатор карточки")
    card_version: Optional[int] = Field(None, description="Версия карточки")
    lifecycle_status: Optional[str] = Field(None, description="Статус жизненного цикла")
    item_type: Optional[str] = Field(None, description="Тип изделия: отвод, труба и т.п.")
    subtype: Optional[str] = Field(None, description="Подтип изделия")
    name: Optional[str] = Field(None, description="Наименование")
    designation: Optional[str] = Field(None, description="Условное обозначение")
    codes: Optional[CatalogCodes] = Field(None, description="Коды МТР/КСМ")
    properties: Dict[str, CatalogProperty] = Field(
        default_factory=dict,
        description="Свойства карточки (ключ -> параметр со value/value_type и т.п.)",
    )
    dcd: Optional[CatalogDcd] = Field(None, description="DCD-контейнер")


class RouterDecision(BaseModel):
    """Решение детерминированного роутера (result route_query_text).

    Ключи совпадают с возвращаемым словарём. Дополнительные ключи
    (например, parsed_query) при валидации через extra="ignore" сохраняются.
    """

    route: str = Field(..., description="ordinary | agent | clarification")
    mode: str = Field(..., description="Режим исполнения")
    intent: str = Field(..., description="Интент запроса")
    intent_label: str = Field(..., description="Человекочитаемое имя интента")
    reasons: List[str] = Field(default_factory=list, description="Причины решения")
    required_tools: List[str] = Field(default_factory=list, description="Тулы для пути")
    missing_parameters: List[str] = Field(default_factory=list, description="Чего не хватает")
    exact_codes: List[str] = Field(default_factory=list, description="Точные коды из запроса")
    collections: List[str] = Field(default_factory=list, description="Затронутые DCD-коллекции")
    normalized_query: str = Field(default="", description="Нормализованный запрос")
    detected_aliases: List[Dict[str, Any]] = Field(default_factory=list, description="Распознанные алиасы")

    model_config = {"extra": "ignore"}
