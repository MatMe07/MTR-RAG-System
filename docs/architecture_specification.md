# Архитектурная спецификация MTR-RAG v2.0

> Код: `backend/app/schemas.py` · Контракт для всех потребителей DTO.
> Поля, помеченные **«потерянные v2.0»**, — возвращены в спецификацию из актуального
> кода; ранее были задокументированы лишь частично.

---

## 1. ParsedQuery

Структурированный результат parse-уровня (1A/1B). Имена полей совпадают
с контрактом `ToolDAL.get_passport_params`.

| Поле | Тип | Описание |
|------|-----|----------|
| `original_query` | `str` | Исходный текст запроса |
| `operations` | `List[str]` | Операции: search, replace, check, plan, explain, inventory, impact, assemble, calculate, document, repair |
| `item_types` | `List[str]` | Типы изделий |
| `component_ids` | `List[str]` | ID компонентов COMP-XXX |
| `unit_ids` | `List[str]` | ID участков UNIT-XXX |
| `card` | `Optional[ItemCard]` | Одна карточка (простой запрос) |
| `cards` | `List[ItemCard]` | Несколько карточек (составной) |
| `technical_filters` | `Dict[str, Any]` | dn, pn, angle, wall_thickness, material, medium, steel_grade, strength_class |
| `stock_filters` | `Dict[str, Any]` | quantity_min/max, location, stock_category |
| `quantity` | `Optional[float]` | Потребность «N штук» |
| `units_count` | `Optional[int]` | Множитель участков («три участка» -> 3) |
| `length_m` | `Optional[float]` | Длина участка, м |
| `limit` | `Optional[int]` | Топ-N |
| `timeframe` | `Optional[str]` | next_week/next_month/... |
| `urgency` | `Optional[str]` | high |
| `sort_by` | `Optional[str]` | procurement_urgency/risk/priority |
| `on_stock` | `Optional[bool]` | Только складские |
| `not_installed` | `Optional[bool]` | Только не установленные |
| `proposed_changes` | `Dict[str, Any]` | Предлагаемые замены (DN→DN) |
| `impact_analysis` | `Dict[str, Any]` | Анализ влияния |
| `unit_context` | `Dict[str, Any]` | unit_id, medium, temperature, pressure |
| `component_context` | `Dict[str, Any]` | component_id, position, connections |
| `references` | `List[str]` | ГОСТы/ТУ/паспорта из запроса |
| `ambiguities` | `List[str]` | Требуют уточнения |
| `required_agents` | `List[str]` | Необходимые агенты |
| `required_capabilities` | `List[str]` | Свободное описание возможностей |
| `confidence` | `float` | Общая уверенность парсинга |
| `confidence_details` | `Dict[str, float]` | Уверенность по полям |
| `intents` | `List[str]` | Гранулярные интенты |
| `status` | `str` | COMPLETE/PARTIAL/REQUIRES_EXPERT |
| `missing_params` | `Dict[str, List[str]]` | Недостающие по интентам |
| `params` | `Dict[str, Any]` | Объединённые параметры фильтров |
| `primary_intent` | `Optional[str]` | Главный интент |
| `groups` | `List[Dict[str, Any]]` | Группы (Classifier)** |
| `parser_diagnostics` | `Optional[ParserDiagnostics]` | Как работал парсер (**потерянное v2.0**) |

---

## 2. ItemCard

Карточка изделия каталога.

| Поле | Тип | Описание |
|------|-----|----------|
| `card_id` | `Optional[str]` | Внутренний id |
| `mtr_code` | `Optional[str]` | Код МТР |
| `ksm_code` | `Optional[str]` | Код КСМ |
| `item_type` | `Optional[str]` | базовый тип |
| `subtype` | `Optional[str]` | подтип |
| `designation` | `Optional[str]` | условное обозначение |
| `name` | `Optional[str]` | наименование |
| `geometry` | `Optional[Geometry]` | DN, angle, wall_thickness |
| `pressure` | `Optional[Pressure]` | PN, рабочие/испытательные давления |
| `material` | `Optional[Material]` | сталь, класс прочности, ГОСТ |
| `environment` | `Optional[Environment]` | среда, H2S/CO2, температура, климат |
| `coating` | `Optional[Coating]` | покрытия |
| `normative` | `Optional[Normative]` | ГОСТ/ТУ, разделы ЛНД |
| `extraction` | `Optional[Extraction]` | метаданные извлечения (**потерянное v2.0**) |
| `sources` | `List[Source]` | Источники документа (**потерянное v2.0** — поле есть) |

---

## 3. AgentAnswer

Структурированный ответ агентского уровня.

| Поле | Тип | Описание |
|------|-----|----------|
| `query` | `str` | исходный запрос |
| `intent` | `Optional[str]` | класс интента |
| `intent_label` | `Optional[str]` | человекочитаемое имя |
| `route` | `Optional[str]` | ordinary/agent/clarification |
| `mode` | `Optional[str]` | **потерянное v2.0** — режим исполнения |
| `tools_used` | `List[str]` | запущенные тулы |
| `explanation` | `Optional[str]` | холistic объяснение |
| `components` | `List[AgentComponent]` | позиции ответа |
| `warnings` | `List[str]` | предупреждения |
| `warning_categories` | `Dict[str, List[str]]` | **потерянное v2.0** — группировка warnings |
| `purchase_recommendation` | `Optional[str]` | **потерянное v2.0** |
| `excluded_due_to_medium` | `List[Dict[str, Any]]` | **потерянное v2.0** — H2S/CO2 |
| `sources` | `List[AgentSource]` | источники |
| `recommendations` | `List[str]` | **потерянное v2.0** — рекомендации (ТЗ 11.2) |
| `expert_review_id` | `Optional[str]` | **потерянное v2.0** |
| `parsed_confidence` | `Optional[float]` | уверенность парсера |
| `parsed_query` | `Optional[ParsedQuery]` | структурированный запрос |
| `review_verdict` | `Optional[str]` | pass/needs_review |
| `review_issues` | `List[str]` | замечания ревьюера |
| `verification_verdict` | `Optional[str]` | pass/review |
| `verification_reasons` | `List[str]` | причины вердикта |
| `missing_parameters` | `List[str]` | чего не хватает |
| `human_review_required` | `bool` | требуется проверка |
| `human_review_reasons` | `List[str]` | **потерянное v2.0** |
| `human_review_reasons` | `List[str]` | обоснование проверки |
| `status` | `str` | ТЗ-статус |
| `llm` | `Optional[LLMDiagnostics]` | диагностика LLM |


---

## 4. LLMDiagnostics

Внутренняя диагностика вызовов LLM (для аудита и метрик).

| Поле | Тип | Описание |
|------|-----|----------|
| `available` | `bool` | LLM-клиент доступен |
| `used` | `bool` | были вызовы |
| `reason` | `Optional[str]` | почему used |
| `model` | `Optional[str]` | LLM_MODEL |
| `total_calls` | `int` | всего вызовов |
| `cache_hits` | `int` | кэш-хиты |
| `cache_misses` | `int` | до провайдера |
| `prompt_tokens` | `int` | токены промпта |
| `completion_tokens` | `int` | токены ответа |
| `total_tokens` | `int` | суммарно |
| `duration_ms` | `float` | время вызовов |
| `cost_estimate_usd` | `Optional[float]` | оценка стоимости |
| `refine_iterations` | `List[RefineIterationRecord]` | итерации C1+ |
| `calls` | `List[LLMCallRecord]` | поименные вызовы |
| `refine_iterations` — см. `RefineIterationRecord` |  | |
| `calls` — см. `LLMCallRecord` |  | |

---

## 5. Экстрагируемые поля паспорта

Поля из текста паспорта → `ExtractedCharacteristic`. Контракт `extract_passport_params`.

| Поле (DTO) | Тип | Поиск в каталоге |
|------------|-----|------------------|
| `dn` | `float` | `dn` |
| `pn` | `float` | `pn` |
| `angle` | `int` | `angle` |
| `wall_thickness` | `float` | `wall_thickness` |
| `material` | `str` | `steel_grade` |
| `medium` | `str` | `medium` |

Веса скоринга — зеркало `instruments.PASSPORT_WEIGHTS`, живые значения из
`validation_constants` (`passport_weights`).

---

## 6. Схемы БД (JSONB / таблицы)

- `Document.page_texts` — постраничный OCR (`page_number`, `text`).
- `ExtractedCharacteristic` — поля нового DTO (см. передачу в провайдеры).
- `DocumentLink.document_id → ksm_code` — связи паспорт→KSM.
- `auto_mode_escalations` — таблица эскалаций (P2-19).

---

## 7. Автопроверка

Прогон `pytest` — **555 passed, 12 skipped**. Поля всех DTO сверены с
`app/schemas.py` (см. `app/scripts/validate_schemas_doc.py`).

[→ Вернуться к чтению кода](backend/app/schemas.py)

