# Отклонения реализации от исходных планов (DEVIATIONS)

**Статус:** ведётся. Обновлять при появлении новых расхождений.
**Назначение:** фиксировать осознанные архитектурные решения, где код расходится с
`docs/plans/*.md`. Работающий код не переделываем ради имён из плана.

---

## Оркестратор (Этап 4)

| План | Реализация | Решение |
|---|---|---|
| Классы `Planner` / `ExecutionPlan` / `ExecutionStep` / `StateManager` / `ContextBuilder` | **LangGraph** `StateGraph(AgentState)` с 12 узлами (parse, catalog, stock, rules, graph, impact, regulation, inventory, sufficiency, maintenance, duplicates, answer) | **Оставляем LangGraph** — работает и покрыт тестами. Планирование = граф маршрутизации `graph/router.py`, исполнение = `graph/nodes.py` + инструменты. `parallel_groups`/`estimated_duration_ms` не применимы. |
| `Executor` (класс-исполнитель плана) | `AgentExecutor` (`executor.py`) — точка входа оркестратора, запускает граф/LLM/auto | Эквивалент по сути. |
| `LLMExecutor` (класс) | функция `run_llm_executor` (`llm/llm_executor.py`) | Эквивалент, изменён способ оформления. |
| `AgentContext` (класс) | `AgentState(TypedDict)` (`core/state.py`) + `AgentAnswer` (`app/schemas.py`) | Поля покрыты множеством `AgentState`/`AgentAnswer`. |
| Лимит LLM-режима **60 секунд** | Было 120с, **исправлено до 60с** (Фаза 0.2) | Уже приведено к плану. |

## Доступ к данным (Этап 2)

| План | Реализация | Решение |
|---|---|---|
| `backend/app/providers/` + `DataAccessLayer` (async) | `backend/app/services/agent/repository/` (db/json/repository_factory) + `tools/tool_dal.py` (`ToolDAL`, **sync**) | Реализация переехала в репо-слой. Провайдеры как классы частично добавлены (neo4j_/norms_/passport_provider). Контракт «все методы async» пока не выполняется (sync-драйвер БД); планируется async-обёртка. |
| Репозитории по доменам (`MTRRepository`, `StockRepository`, …) | Единый агрегатный `IRepository` + `DbRepository`/`JsonRepository` | Оставляем агрегат — избавляет от дублирования. |
| Кеш с per-типными TTL и группами `catalog:*`/`stock:*`… | RedisCache с **единым TTL 300с** / 3600с для словарей; инвалидация полным flush | Планируется переход на per-типные TTL. |
| Qdrant: `mtr_descriptions` (каталог), `norm_documents`, `documents`, `queries` | Одна коллекция `QDRANT_COLLECTION="mtr_descriptions"`, в ней **нормативные фрагменты** (не описания MTR) | Мисконфигурация. Планируется 3 коллекции по назначению + миграция данных норм. |

## Хранилища (Этап 1.1)

| План | Реализация | Решение |
|---|---|---|
| Neo4j: узел `ComponentAlias` (COMP-SYN-XXX→KSM), индексы по `item_type`/`dn` | Только `Component`/`Unit`, `CONNECTS_TO`/`BELONGS_TO`, 2 constraint'а | `ComponentAlias` и индексы **не созданы** — запланировано (Фаза 6). |
| Qdrant-коллекция `queries` (кэш запросов) | Нет | Намеренно не нужна: LLM-кеш in-memory/Redis. |

## Celery / паспорта (Бэкенд-архитектура B.3, Этап 2)

| План | Реализация | Решение |
|---|---|---|
| `workers/passport_worker.py`, задачи `process_passport`/`reprocess_passport` | `workers/celery_app.py` + `workers/tasks.py`; задача `documents.ingest` — **заглушка** («OCR-синк реализуется отдельной итерацией»), `passport_worker.py` нет | Запланировано (Фаза 3). |
| Прогресс-эндпоинт по состоянию Celery-задачи | `/api/v1/passport/status/{id}` читает `ocr_status` из БД | Планируется привязка к состоянию задачи. |

## Парсинг (Этап 1)

| План | Реализация | Решение |
|---|---|---|
| 1A.4/1A.5 ML-fallback классификатор (fastText/DistilBERT, 500+ размеченных запросов) | Отсутствует | **Сознательное упрощение**: rule-based + LLM-fallback без обучения модели (решение пользователя). |
| 1E нормализация (DN→R10, бар→МПа, материалы) | Парсеры держат простые cast (pressure_parser.py:295) | Запланировано (Фаза 1). |
| 1F LLM-доизвлечение параметров | Нет | Запланировано (Фаза 1). |
| Интенты: «28 штук» | 26 в `INTENT_ORDER`, 24 в `INTENT_TOOLS` | Приводим к 28 и полному маппингу (Фаза 1). |

## Прочее

| План | Реализация | Решение |
|---|---|---|
| Конфиг `OCR_ENGINE` | Поле есть в `.env`, но **не читается**: OCR захардкожен (Docling + EasyOCR) | Планируется в Фазе 3 (переключение движка). |
| Удаление справочников/правил — мягкое (`is_active=False`) | Админ-API делает жёсткий DELETE | Запланировано (Фаза 1). |
| `POST /admin/dictionaries/update` (1J.3) | Вместо него generic CRUD `/admin/dictionaries/{dict_name}[/{id}]` | Оставляем generic CRUD. |
| Асинхронность DAL | Sync `ToolDAL` | Планируется async-контракт (уточнить: asyncpg vs run_in_executor). |
| LLM-доступ (живой OpenRouter) | Ключ в `.env` есть, но OpenRouter отдаёт **403 "Access denied by security policy"** (блок по региону/IP). Проверено на 3 моделях | **Ограничение окружения.** Код поддерживает graceful-fallback; живые прогоны — при доступе с разрешённой сети или альтернативном провайдере. |