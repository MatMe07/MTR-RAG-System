# Оценка бэкенда MTR-RAG-System против плана `docs/plans/*`

- Дата оценки: 2026-08-27
- Область оценки: **только бэкенд** (фронтенд намеренно исключён)
- Источники плана: `docs/plans/Этап 1.md`, `docs/plans/Этап 1.1.md`, `docs/plans/БЭКЕНД-АРХИТЕКТУРА.md`, `docs/plans/ЭТАП 2. ДОСТУП К ДАННЫМ.md`, `docs/plans/ЭТАП 3. ИНСТРУМЕНТЫ.md`, `docs/plans/ЭТАП 4. ОРКЕСТРАТОР И ПЛАНИРОВЩИК.md`, `docs/plans/ЭТАП 5. ФОРМИРОВАНИЕ ОТВЕТА.md`

## 1. Итоговый вердикт

**Статус: функциональный MVP-прототип, находящийся в середине незавершённого рефакторинга. Соответствие плану — частичное: отдельные слои реализованы на высоком уровне, но архитектура существенно разошлась со спецификацией.**

Что работает по-настоящему:

- Парсер запросов (regex + Natasha, confidence, ambiguity) — зрелый и функциональный.
- LangGraph-агент (8 узлов: parse → catalog → stock → rules → graph → impact → regulation → answer).
- Сборка ответа (AnswerBuilder + сценарные предупреждения из JSON-движка правил).
- API-слой: 9 роутеров, JWT + роли, AppException-иерархия + хендлер, structlog, health.
- ORM-модели и 5 миграций Alembic.
- Админ-CRUD для справочников.
- Генераторы данных: каталог 1000 позиций, граф 42 компонента / 126 связей, 40 eval-вопросов.

Что объявлено, но НЕ работает (live-путь фактически на JSON-файлах):

- PostgreSQL (задекларирован в `.env`, БД в базовой конфигурации не поднята/пустая).
- Neo4j — только разовый скрипт `generate_graph_neo4j.py`.
- Qdrant — скрипт индексации удалён (импортировал удалённый `embedding_service`); векторный поиск не входит в активный стек.
- Redis — ни одного импорта/использования в коде.
- Celery — `app/workers/` не существует, docker-compose ссылается на несуществующий `app.workers.celery_app`.
- LLM — клиент реализован, но в live-пути не вызывается (`AGENT_LLM_MODE=on` игнорируется).

## 2. Реальная архитектура (live-путь)

Документ `docs/pipeline_classes.md` описывает фактическую цепочку:

```
POST /api/v1/search/
 → SearchService.execute_search()          (app/services/search_service.py:23-78)
   → AgentExecutor.execute()               (app/services/agent/executor.py:46-99)
     → HybridParser.parse()                (парсится ДВАЖДЫ: executor + parse_node)
     → create_initial_state()
     → graph.invoke(state)                 (LangGraph, 8 узлов)
       parse → catalog → stock → rules → graph → impact → regulation → answer
     → AnswerBuilder.build() → SearchResponse
 — AuditService.log()                      (best-effort, try/except pass)
```

Ключевое расхождение с планом Этапа 4: вместо изолированных режимов
«Planner → ExecutionPlan → Executor (asyncio.gather) → StateManager → ErrorHandler»
стоит фиксированная LangGraph-топология с маршрутизаторами. Поле
`SearchRequest.mode` («deterministic»/«llm») принимается и логируется, но не влияет на выполнение.

## 3. Поэтапная сверка с планом

### 3.1 Этап 1 (парсинг, интенты, словари)

| Раздел плана | Статус | Комментарий |
|---|---|---|
| 1A Группы (ПОИСК/СКЛАД/РЕМОНТ/ЗАМЕНА/АНАЛИЗ/ОБЪЯСНЕНИЕ/ДОКУМЕНТЫ) | НЕ реализовано | Группы есть только как комментарии в `services/agent/parsing/dictionaries.py:172-259`. Правила переопределения, отрицание, дефолты — отсутствуют |
| 1B 28 атомарных интентов | НЕ реализовано | 11 операций (`OperationParser`), из них `_resolve_intent` даёт 8 интентов. `INTENT_REQUIREMENTS`, `FIND_BY_CODE`, `CHECK_STOCK` и пр. отсутствуют в коде |
| 1C Матрица параметров | НЕ реализовано | Отсутствует |
| 1D ParameterExtractor | Реализовано (иной способ) | Вместо одного класса — 10 специализированных парсеров: geometry, pressure, material, environment, component, normative, item_type, operation, context + Natasha. Качество высокое |
| 1E Нормализация | Частично | PN→МПа — полноценно (деление ≥10 на 10, таблица, бар/кгс·см²). DN→ряд R10 — не сделано (`STANDARD_DN` в `dictionaries.py:490` не применяется для округления). Сталь/среда/климат — частично |
| 1F LLM-доизвлечение | НЕ реализовано | LLM-клиент есть, но в live-пути не вызывается. Кеш LLM — in-memory LRU, не Redis |
| 1G Диалоговое уточнение | Частично | Есть механизм `missing_params`, но state-машины на 3 цикла и статуса REQUIRES_EXPERT нет |
| 1H Фильтрация/валидация/статус | Частично | `missing_params`, `confidence`, `ambiguities` есть. `filter_params_for_intent`, `INCOMPATIBLE_INTENTS`, `PARAMETER_VALIDATION_RULES` — нет. Вместо ParsedRequest используется ParsedQuery |
| 1I Логирование/аудит | Частично | `logs` + `AuditService` работают, `request_id` есть. Таблицы `data_access_logs`, `llm_agent_logs`, `tool_execution_logs` созданы, но записей нет |
| 1J/1K/1L Словари | Каркас, без интеграции | Таблицы + admin-API есть, но парсер их не читает. `POST /admin/dictionaries/reload` глушится битым импортом (`from services.agent...` без префикса `app.`) и несуществующей функцией `reload_dictionaries` | 

### 3.2 Этап 1.1 (модели и хранение)

| Пункт | Статус | Комментарий |
|---|---|---|
| `mtr_items` (JSONB attributes + GIN) | Есть | `models/sqlalchemy/all_models.py:40` |
| `candidate_items`, `documents`, `extracted_characteristics`, `golden_dataset`, `expert_matches`, `logs` | Есть | Совпадают с планом |
| Справочники (`group_keywords`, `contextual_overrides`, `synonyms`, `validation_constants`, `validation_rules`) | Есть | Таблицы + миграции 004/005 |
| Neo4j (модель данных) | НЕ интегрировано | Только скрипт `scripts/GEN/generate_graph_neo4j.py` с захардкоженными кредами; live читает JSON-граф |
| Qdrant (коллекции) | НЕ интегрировано | Скрипт индексации сломан |

### 3.3 ЭТАП 2 (доступ к данным)

| Пункт | Статус | Комментарий |
|---|---|---|
| 2A Pydantic-модели (Component, StockItem, GraphEdge, Unit, CompatibilityContext/Result, ExtractedParam, NeighborInfo, EnhancedSearchResult, SearchParams, PaginatedResult, UnitInventory, ComponentHistory, KsmSuggestion, DocumentMetadata) | Есть | `models/pydantic/schemas.py:14-249` |
| 2B Провайдеры (Catalog/Stock/Graph/Passport/Norms) | НЕ реализовано | Вместо них — `IRepository` (`services/agent/repository/interfaces.py`), реализация `JsonRepository` + `DbRepository` |
| 2C DAL (search_catalog с detail_level, get_unit_inventory, check_compatibility, extract_passport, история) | Частично | `IRepository` покрывает get_catalog/get_card/get_stock_quantity/get_graph/get_components_by_unit/get_regulation/search_candidates. Уровни детализации не реализованы |
| 2D Кеширование | НЕ реализовано | Redis не используется нигде |
| 2E Импорт | Частично | `load_data_v2.py` актуален; генераторы синтетики есть; импорта норм/графа в Neo4j нет |
| 2F Qdrant | НЕ интегрировано | Нет |
| 2G Fallback-механизмы | Работает | JSON-fallback — основной live-путь; `DbRepository` при пустом каталоге откатывается на JSON. Причина переключения не логируется |
| 2H Логирование DAL | НЕ реализовано | Таблица есть, записей нет |

### 3.4 ЭТАП 3 (инструменты)

| Пункт | Статус | Комментарий |
|---|---|---|
| 13 плановых инструментов | УДАЛЕНО | `services/tools/` — мёртвый пакет удалён целиком |
| Живой набор инструментов | 8 подключены к графу | `services/agent/tools/core_tools.py` (catalog_search, stock_query, rules_engine, graph_search, regulation_lookup) + `analytic_tools.py` (impact_analyzer, inventory_calculator, maintenance_planner, duplicate_detector) — все вызываются из узлов графа |
| Валидация входов (JSON-schema, лимиты depth/50/100) | НЕ реализовано | Лимиты не проверяются |
| ToolError (NOT_FOUND/INVALID_PARAMS/BATCH_TOO_LARGE) | НЕ реализовано | Инструменты возвращают `{"error": "..."}`-строки, которые никто не читает; `state["errors"]` не заполняется |
| 3F Логирование вызовов | НЕ реализовано | Таблица `tool_execution_logs` есть, записей нет |
| 3E Карта интенты → инструменты | Доработано | Маршрутизаторы графа покрывают все интенты; аналитические инструменты (inventory_calculator, maintenance_planner, duplicate_detector) подключены к узлам; замена/ТОиР проходят через правила и нормативы |

### 3.5 ЭТАП 4 (оркестратор) — наибольшее расхождение

| Требование плана | Статус |
|---|---|
| Два изолированных режима, переключатель | НЕ реализовано; `request.mode` игнорируется |
| Deterministic: Planner + ExecutionPlan + parallel_groups | Заменено фиксированным графом; параллельности нет |
| Executor с asyncio.gather | graph.invoke() |
| StateManager (completed_tools/results/errors/retry_counts) | `AgentState` минимальный; `errors` никогда не пишется |
| ErrorHandler (тип ошибки → действие, retry до 3) | Отсутствует; ошибки всплывают в HTTP 500 |
| LLM-режим (LLMAgent, ToolRegistry, ResponseParser, LLMExecutor, 10 итераций/60 сек) | НЕ реализован |
| Защита от зацикливания графа | Нет обхода: `replacement + proposed_changes` может зациклиться до GraphRecursionError (stock ↔ impact) |
| Время: deterministic < 10 сек | Не измеряется и не контролируется |

Найденные дефекты графа: `graph/edges.py` пустой (0 строк); `parse_node` повторно парсит запрос (дублирование с executor); `_resolve_intent` продублирован в `executor.py` и `nodes.py`, а модуль `agent/intent_resolver.py` (приведён в `docs/pipeline_classes.md:29`) удалён; `tools_used` никогда не заполняется; `rules_router` всегда ведёт в `regulation` (ветка `answer` недостижима).

### 3.6 ЭТАП 5 (формирование ответа)

| Пункт | Статус | Комментарий |
|---|---|---|
| 5A.1 ResponseBuilder | Есть | `AnswerBuilder` в `services/agent/answer/builder.py` |
| 5A.2 StatusDeterminator (95%/70%, блокеры) | Упрощено | Отдельного класса нет; `BLOCKER_FIELDS` в `core/constants.py` есть, но не участвует в статус-логике |
| 5A.3 ExplanationGenerator (шаблон/LLM) | Частично | Есть шаблонный текст; LLM-режим не работает |
| 5A.4 SourceFormatter | Есть | `_to_sources` (type/document_id/page) |
| 5B.1 JSON-ответ | Есть | `SearchResponse` совпадает по форме (status/results/warnings/recommendations/requires_expert/execution_time_ms) |
| 5B.3 expert_review_id | Частично | `requires_expert` есть (human_review_required), формат review_id — нет |

### 3.7 БЭКЕНД-АРХИТЕКТУРА

| Требование | Статус |
|---|---|
| Структура проекта | Удовлетворительно с оговорками: нет `app/repositories/`, `app/providers/`, `app/workers/`; момент соответствует `services/agent/repository/` |
| Celery + Redis, async-паспорта | НЕ реализовано: `app/workers/` отсутствует; docker-compose запускает несуществующий `celery -A app.workers.celery_app`. `/passport/upload` пишет строку `pending` и не запускает обработку (ocr_service не вызывается) |
| Alembic (5 миграций) | Есть; но БД фактически создавалась через `create_all` (в `mtr.db` нет `alembic_version`); миграции Postgres-only |
| Логирование (structlog JSON) | Есть |
| Обработка ошибок (AppException + handler) | Есть |
| JWT + роли + CORS | Есть; `passport`/`component`/`compare`/`norms` без аутентификации, `search` — опционально |
| Конфиг (env) | Полный |
| Тесты | 9 файлов; сломанные (test_query_parser, test_agent_endpoint, test_catalog_loader) удалены — импортирующие удалённые модули модули не остались; набор зелёный (27 passed, 1 skipped) |

## 4. Критические проблемы и риски (по убыванию важности)

1. **Параллельные стеки из-за незавершённого рефакторинга**
   - Модели: `app/models.py` (legacy) против `app/models/sqlalchemy/all_models.py` (актуальная) — совпадает только 5 имён таблиц, колонки различны.
   - Схемы: `app/schemas.py` против `app/models/pydantic/schemas.py` — дублирующиеся `SearchRequest/SearchResponse/ItemCard/AgentAnswer` с несовместимыми полями (старые скрипты ссылаются на несуществующие `operation/changes/context`).
   - Конфиги: `app/config.py` против `app/core/config.py` (разные defaults, разный DATABASE_URL).  *(legacy `core/config.py` удалён)*
   - Сессии БД: `app/db/session.py` (живой) против `app/database.py` (legacy).  *(legacy `database.py` удалён)*
   - Удалены модули при сохранившихся импортах/`.pyc`: `embedding_service`, `entity_extractor`, `query_parser`, `llm_service`, `rules_engine`, `card_extractor`, `jsonb_utils`, `query_normalizer`, `llm_prompts` → сломаны `index_qdrant.py`, `test_query_parser.py`, `eval_query_parser.py`, `test_agent_endpoint.py`.  *(сломанные скрипты и тесты удалены)*
2. **Инфраструктура «на бумаге»**: Neo4j/Qdrant/Redis/Celery/Postgres задекларированы, реальный live-путь — JSON-файлы. Celery-часть docker-compose не поднимется.
3. **Данные**: `data/regulation/regulation_matrix.json` отсутствует → `regulation_lookup` отдаёт mock; `rules_engine` ссылается на несуществующий `matching_rules.csv`.  *(`regulation_matrix.json` восстановлен из git-истории по состоянию на 2026-08-27)*
4. **Безопасность**: реальные `OPENROUTER_TOKEN` и `HF_TOKEN` в `.env` (файл в `.gitignore`, в git не попал — но секреты стоит ротировать); захардкоженные креды Neo4j в скрипте; `SECRET_KEY` по умолчанию.
5. **Роли**: половина роутеров без аутентификации (нарушение B.6.2).
6. **Качество (промежуточный отчёт `data/evaluation/results/40_questions_report.json`, 2026-08-17)**: 37/40 по «инструментам», `review_pass: 0/40` — экспертная проверка не выдаётся. Отчёт устарел относительно текущего кода. *(актуальный прогон 2026-08-27: tools 32/40, review_pass 0/40 — порог 20/40 пройден)*
7. **README устарел**; присутствуют два фронтенда (`frontend/`, `ui_streamlit/`).

## 5. Сильные стороны (база для развития)

- Парсинг: 10 специализированных парсеров, Natasha-fallback с порогом confidence 0.8 (enrich/merge), PN→МПа нормализация, полноценные ConfidenceCalculator и AmbiguityDetector (multiple/conflict/missing/contradiction + severity + suggestions).
- Агентный граф (LangGraph, 8 узлов): работает end-to-end, собирает кандидатов, источники и предупреждения.
- AnswerBuilder + scenario-warnings (JSON-движок): детерминированная логика предупреждений H2S/CO2/план/замена/дубликаты.
- API-каркас: 46 эндпоинтов, JWT/роли, иерархия исключений, structlog, миграции, admin-CRUD, health.
- Данные: генератор регламентированного каталога 1000 позиций, граф 42/126, 40 eval-вопросов.

## 6. Рекомендуемый план действий

1. **Завершить рефакторинг (устранить дубли)**: заморозить/удалить legacy-слои (`models.py`, `database.py`, `core/config.py`, `services/tools/`, 399-строчный `agent/analytic_tools.py`, мёртвые скрипты, `.pyc`); свести схемы к единому источнику (`models/pydantic/schemas.py` + достройка ParsedQuery).  *(legacy-слои удалены; остаётся сведение схем и достройка ParsedQuery)*
2. **Починить инфраструктурные заглушки**: либо поднять реальный Postgres (миграции + db_repository), либо зафиксировать JSON-режим и убрать вводящую в заблуждение конфигурацию Neo4j/Qdrant/Redis/Celery; починить `admin/reload`.
3. **Устранить опасные дефекты графа**: защита от зацикливания (`recursion_limit`), устранение двойного парсинга, подключение inventory_calculator/maintenance_planner/duplicate_detector, заполнение `tools_used`/`errors`.  *(инструменты подключены, `tools_used` заполняется; остаётся `recursion_limit` и двойной парсинг)*
4. **Восстановить функциональность плана, потерянную при рефакторинге**: LLM-доизвлечение и LLM-режим (клиент готов), ErrorHandler с retry, mode-switch, диалоговое уточнение, R10-нормализация DN, фильтрация параметров по интенту.
5. **Включить плановые механизмы**: Redis-кеш, Celery (`app/workers/` + обработка `/passport/upload`), реальные `norm_documents`/`compatibility_rules` + `data/regulation/regulation_matrix.json`, запись в `data_access_logs`/`tool_execution_logs`/`llm_agent_logs`.
6. **Безопасность/гигиена**: ротировать токены, аутентификация на passport/component/compare/norms, убрать хардкод кредов.
7. **Обновить документацию и тесты**: README, `docs/pipeline_classes.md` (intent_resolver), восстановить unit-тесты инструментов.

## 7. Обозначения статусов

- **Есть** — реализовано и работает.
- **Частично** — есть рабочая реализация, но отличается от плана или неполная.
- **НЕ реализовано** — отсутствует в коде (может существовать только в плане).
- **МЁРТВЫЙ КОД** — написано, но не вызывается нигде в live-пути.