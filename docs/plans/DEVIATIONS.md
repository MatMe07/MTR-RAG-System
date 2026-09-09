# Отклонения реализации от исходных планов (DEVIATIONS)

**Статус:** ведётся. Обновлять при появлении новых расхождений.
**Назначение:** фиксировать осознанные архитектурные решения, где код расходится с
`docs/plans/*.md`. Работающий код не переделываем ради имён из плана.

---

## Актуальные отклонения

### Оркестратор (Этап 4)

| План | Реализация | Решение |
|---|---|---|
| Классы `Planner` / `ExecutionPlan` / `ExecutionStep` / `StateManager` / `ContextBuilder` | **LangGraph** `StateGraph(AgentState)` с 12 узлами (parse, catalog, stock, rules, graph, impact, regulation, inventory, sufficiency, maintenance, duplicates, answer) | **Оставляем LangGraph** — работает и покрыт тестами. Планирование = граф маршрутизации `graph/router.py`, исполнение = `graph/nodes.py` + инструменты. `parallel_groups`/`estimated_duration_ms` не применимы. |
| `Executor` (класс-исполнитель плана) | `AgentExecutor` (`executor.py`) — точка входа оркестратора, запускает граф/LLM/auto | Эквивалент по сути. |
| `LLMExecutor` (класс) | функция `run_llm_executor` (`llm/llm_executor.py`) | Эквивалент, изменён способ оформления. |
| `AgentContext` (класс) | `AgentState(TypedDict)` (`core/state.py`) + `AgentAnswer` (`app/schemas.py`) | Поля покрыты множеством `AgentState`/`AgentAnswer`. |

### Доступ к данным (Этап 2)

| План | Реализация | Решение |
|---|---|---|
| `backend/app/providers/` + `DataAccessLayer` (async) | `backend/app/services/agent/repository/` (db/json/repository_factory) + `tools/tool_dal.py` (`ToolDAL`) | **`ToolDAL` и есть DAL-адаптер** над `IRepository` для инструментов ЭТАПА 3; провайдеры как классы добавлены (neo4j_/norms_/passport_, catalog_semantic_, documents_). |
| Асинхронность DAL (asyncpg vs run_in_executor) | Sync-драйвер БД (`ToolDAL`, `IRepository` — синхронные) | **Отложено**: контракт sync работает, async-обёртка не требуется для текущих нагрузок. |
| Репозитории по доменам (`MTRRepository`, `StockRepository`, …) | Единый агрегатный `IRepository` + `DbRepository`/`JsonRepository` | Оставляем агрегат — избавляет от дублирования. |

### Парсинг (Этап 1)

| План | Реализация | Решение |
|---|---|---|
| 1A.4/1A.5 ML-fallback классификатор (fastText/DistilBERT, 500+ размеченных запросов) | Rule-based `GroupClassifier` + LLM-fallback без обучения модели | **Сознательное упрощение** (решение пользователя). |
| `morph_normalizer` (морфонормализация) | Закомментирован в `hybrid_parser.py`; работает rule-based `normalizers.py` | Минорный остаток — подключение опционально. |

### Хранилища (Этап 1.1)

| План | Реализация | Решение |
|---|---|---|
| Qdrant-коллекция `queries` (кэш запросов) | Нет | Намеренно не нужна: LLM-кеш in-memory/Redis. |
| Qdrant: фактическая миграция данных норм в `norm_documents` | Коллекции настроены (`config.py`), загрузка данных требует проверки | Отложено (см. «Фактический остаток» чек-листа). |

### Прочее

| План | Реализация | Решение |
|---|---|---|
| LLM-доступ (живой OpenRouter) | Ключ в `.env` есть, но OpenRouter отдаёт **403 "Access denied by security policy"** (блок по региону/IP). Проверено на 3 моделях | **Ограничение окружения.** Код поддерживает graceful-fallback; живые прогоны — при доступе с разрешённой сети или альтернативном провайдере. |
| `purchase_order_preview` (заявка на закупку CSV/JSON для ERP/1С) | Нет | Отложено (`docs/plans/Потом.md`). |

---

## Закрытые (зафиксированы в истории, актуальному коду не противоречат)

| План | Статус |
|---|---|
| Лимит LLM-режима **60 секунд** (было 120с) | Приведено к плану — `MAX_TOTAL_SECONDS=60.0`. |
| Кеш: единый TTL 300с | Реализованы per-типные TTL (`redis_cache.DEFAULT_TTLS`: catalog 1ч / stock 5м / passport 1ч / словари 24ч). |
| Qdrant: одна коллекция `mtr_descriptions` с норм-фрагментами | Коллекции разведены: `mtr_descriptions`, `norm_documents`, `documents`. |
| Neo4j: только `Component`/`Unit`, 2 constraint'а | Добавлены `ComponentAlias` (constraint `comp_id`) + индексы `Component.item_type`/`dn`. |
| `workers/passport_worker.py` как заглушка | Реализован полноценный `workers/passport_worker.py` (OCR→параметры→связи KSM). |
| 1E нормализация (DN→R10, бар→МПа, материалы) | Подключены `normalizers` в парсеры (`geometry_parser`, `parser`, `llm_extractor`). |
| 1F LLM-доизвлечение параметров отсутствует | Реализован `parsing/llm_extractor.py`, вызывается при недобранных required-параметрах. |
| Интенты: 26/24 в маппингах | Доведено до 28, `INTENT_TOOLS` полный (`CHECK_SUFFICIENCY`, `ADD_COMPONENT`, `REPAIR_WITH_CHECKS`). |
| Конфиг `OCR_ENGINE` не читается (OCR захардкожен) | `OCR_ENGINE` читается в `ocr_service.py` и `passport_worker.py`. |
| Удаление справочников/правил — жёсткий DELETE | Поддерживается мягкое удаление (`is_active=False`) для правил валидации. |
| `POST /admin/dictionaries/update` (1J.3) | Заменён generic CRUD `/admin/dictionaries/{dict_name}[/{id}]` — оставлено как есть. |
| `POST /admin/validation-rules/reload` отсутствует | Реализован (`admin.py` + `admin_service.reload_validation_rules`). |
| Автопредложение правил при импорте MTR отсутствует | Реализовано (`import_service._suggest_validation_rules`, черновик `is_active=False`). |
| `docs/domain/dcd_taxonomy.json` удалён (bash «режим Авто») → падал тест манифеста | Файл восстановлен из git-истории; тест зелёный. |