# План: доработка проекта до состояния из docs/plans/* — фазы A–E, полный стек

Дата: 2026-08-28
Статус: утверждён (охват A–E; хранилище — полный стек PG/Neo4j/Qdrant/Redis с fallback на JSON; Celery и UI — вне итерации).

## Цель

Довести проект до состояния, описанного в `docs/plans/` (Этап 1, 1.1, 2, 3, 4, 5, БЭКЕНД-АРХИТЕКТУРА), за итерацию фаз A–E, развернув реальное хранилище с fallback на JSON.

## Сверка «план ⇄ код» (зафиксировано 2026-08-28)

- Этап 1 (парсинг): реализован HybridParser (9 парсеров + нормализаторы), ParsedQuery. НЕТ: матрицы 28 интентов (INTENT_REQUIREMENTS, INCOMPATIBLE_INTENTS, PARAMETER_VALIDATION_RULES, BLOCKER_FIELDS), filter_params_for_intent, статусов ParsedQuery, диалогового уточнения 1G в графе, DictionaryManager/БД-словарей (1J/1K/1L).
- Этап 1.1 (хранилище): миграции alembic 001–005 и models/sqlalchemy есть; PG не используется рантаймом; Neo4j/Qdrant в коде отсутствуют.
- Этап 2 (DAL): есть фасад IRepository; НЕТ async-DAL/провайдеров, detail_level, Redis-кеша, data_access_logs, процедур импорта.
- Этап 3 (инструменты): есть registry + 4 аналитических инструмента; НЕТ 13 инструментов-обёрток, JSON-schema валидации, ToolError, tool_execution_logs.
- Этап 4 (оркестратор): есть детерминированный langgraph; НЕТ изолированного LLM-цикла (call_tool/ask_user/finish, 10 итер/60с), ErrorHandler-retry, ветвления по request.mode.
- Этап 5 (ответ): есть AnswerBuilder → AgentAnswer; НЕТ структуры по ТЗ 11.2, StatusDeterminator-маппинга, рекомендаций, expert_review_id, lnd_section, LLM-объяснения.
- БЭКЕНД-АРХИТЕКТУРА: API-слои, JWT, CORS, логирование, исключения, Alembic, аудит — есть. НЕТ Celery/Redis (ocr sync), admin/reload сломан, compose-заглушки.
- UI-STREAMLIT: набор views вместо ролевой 8-экранной структуры — вне итерации.

## Порядок исполнения

### Шаг 0 — Фаза A «Стабилизация» (без зависимостей)
1. A1: parse_node переиспользует state["parsed"] (nodes.py) — фикс двойного парсинга.
2. A2: recursion_limit + guard GraphRecursionError в get_agent_graph (agent_graph.py).
3. A3: admin/reload — префикс app., реальная перезагрузка каталога, без try/except pass.
4. A4: сведение схем — удалены мёртвые дубликаты-близнецы из models/pydantic/schemas.py (AgentRequest, AgentAnswer, ExpertReviewRequest, ItemCard, MatchResult, RouteRequest, RouteResponse — не используются) и legacy SearchRequest/SearchResponse из app/schemas.py (живые — в models). Итог: каждое используемое имя определено один раз; runtime-схемы — в app/schemas.py, API-контрактные — в models/pydantic. Расходящиеся контрактные пары (ItemCard rich vs flat, AgentAnswer rich vs API-минимальный) осознанно отложены в Фазу B (там решаются по ТЗ 11.2), см. план Фазы B.
- DOD: полный pytest зелёный.

### Шаг 1 — Фаза B «Этап 5: ответ по ТЗ 11.2» — ВЫПОЛНЕНА
- StatusDeterminator (app/services/agent/answer/status.py): 6 ТЗ-статусов, последовательность 5A.2 (STOP→EXPERT, INVALID→UNCLEAR, ≥95/≥70/match-пороги, критические warning-фразы → EXPERT), не эскалируют обычные дисклеймеры.
- Оценка кандидата (evaluate_candidate): matched/mismatched/missing по BLOCKER_PARAMETERS (только пользовательские ключи, tol 10%), _match_score дополнен PN.
- Ответ по ТЗ 11.2 (tz_result.py -> SearchResponse): query, mode, status, results[{mtr_code,ksm_code,match_percent,status,matched_params,mismatched_params,missing_params,explanation,stock,sources}], warnings, recommendations, requires_expert, expert_review_id, execution_time_ms; format_sources -> {type,document_id,page,row,section,lnd_section,description}.
- AgentAnswer/AgentComponent расширены (status, recommendations, expert_review_id, match_score, match_percent, tz_status, matched/mismatched/missing); SearchResponse (models/pydantic) дополнен query/mode/expert_review_id.
- Explanation: шаблонный build_explanation (explanation.py); LLM-вариант — позже.
- DOD: test_answer_tz.py (23 теста 5D); E2E http POST /api/v1/search -> ТЗ-структура; полный pytest 53 passed / 1 skipped; UI-поля (status/labels) не сломаны.

### Шаг 2 — Фаза C «Этап 1: матрица интентов» — ВЫПОЛНЕНА
- Декларативная матрица в app/services/agent/intent/matrix.py: INTENT_ORDER/INTENT_REQUIREMENTS (24 интента, required = OR-AND-группы), INCOMPATIBLE_INTENTS, PARAMETER_VALIDATION_RULES, BLOCKER_FIELDS (единый источник; status.py импортирует из матрицы).
- detect.py: detect_intents (приоритеты 1B.8/1B.9, явный глагол — главный), params_from_parsed, filter_params_for_intent (1H.1), missing_required_for_intent, incompatible_detected (1H.2), determine_parsed_status (1H.4: COMPLETE/PARTIAL/REQUIRES_EXPERT/UNCLEAR), enrich_parsed (заполняет ParsedQuery.intents/status/missing_params/params; вызывается в executor и parse_node).
- Схема ParsedQuery расширена: intents, status, missing_params, params (аддитивно).
- clarify.py: ClarificationManager (1G.2 сессии), RequireClarification, build_question (1G.1), до 3 циклов → status REQUIRES_EXPERT (1G.4), слияние текстов (1G.3).
- API: POST /api/v1/search/clarify {session_id, query} -> {route: clarification|answer|expert, turn, question, missing, status, answer}.
- DOD: test_intent_matrix.py (19 тестов); E2E-диалог (уточнение → выполнение → expert); полный pytest 72 passed / 1 skipped; complex_questions_40 без регрессий.

### Шаг 3 — Инфраструктура «полный стек» — ВЫПОЛНЕНА (2026-08-29)
1. Поднять docker-compose (db/redis/neo4j/qdrant); .env.
2. alembic upgrade head на реальном PG.
3. Провайдеры: catalog(PG, fallback JSON), stock(PG), graph(Neo4j+pipeline_edges, fallback JSON), norms(PG+Qdrant, fallback полнотекст), passport(PG). DAL с detail_level, data_access_logs, Redis-кеш+инвалидация.
4. Импорт данных: каталог 1000 карточек (валиден по Ф7), граф, склад, нормативы.
5. repository_factory/db_repository основной, JSON — fallback, селектор по конфигу.
- DOD: /search и инструменты работают против PG; интеграционный тест.

### Шаг 4 — Фаза D «Этап 3: 13 инструментов» — ВЫПОЛНЕНА (коммит 975d92f)
- Обёртки над DAL: search_catalog, get_component, search_by_passport, check_stock, get_low_stock_items, get_unused_stock, get_unit_structure, get_neighbors, is_installed_anywhere, check_compatibility, check_compatibility_batch, search_norms, get_component_history.
- JSON-schema I/O, ToolError (INVALID_PARAMS/BATCH_TOO_LARGE/NOT_FOUND/DAL_ERROR), лимиты (depth≤5, limit≤100, batch≤50), tool_execution_logs (PG), карта intent→tools.
- DOD: тесты 3G.1–3G.2; реестр для LLM-режима.

### Шаг 5 — Фаза E «Этап 4: два изолированных режима» — ВЫПОЛНЕНА (2026-08-29)
- Детерминированный: langgraph + ErrorHandler (retry DAL_ERROR ≤3, skip NOT_FOUND, STOP на INVALID_PARAMS).
- LLM-режим: LLMAgent-цикл call_tool/ask_user/finish через ToolRegistry, лимиты 10 итер/60с/без повторов, llm_agent_logs.
- Ветвление по request.mode; рекомендация переключения при UNCLEAR/REQUIRES_EXPERT.
- DOD: 20 интеграционных запросов, оба режима; детерм < 10 с, LLM < 60 с.

## Финализация (Шаг 6, 2026-08-29)

- Секреты вычищены из config.py и scripts/GEN (дефолты — локальный compose-стек;
  облако/ключи — только через env/.env). Qdrant REST в NormsProvider теперь
  корректно работает и с https-облаком (api-key header).
- `llm_agent_logs` пишется в PG с самовосстановлением (как tool_execution_logs).
- Celery-каркас восстановлен: `app/workers/celery_app.py` + `tasks.py`
  (docker-compose celery-worker/beat снова валиден).
- Интеграционный тест `test_phase5_stack_integration.py` (11 тестов) авто-skip
  при недоступном стеке (в данной WSL-окружении Docker Desktop не поднят —
  skip ожидаем; ранее прогнан против живого стека: 11 passed).

## Риски

- Полный стек дороже всего: Qdrant требует эмбеддинг-модель, Neo4j — данные/память; проверить docker в начале Шага 3.
- Миграции 001–005 писались под план-схему — вероятны правки.
- Уточнение (Шаг 2) меняет ParsedQuery — BLOCKER_FIELDS закладывать заранее (Шаг 1).