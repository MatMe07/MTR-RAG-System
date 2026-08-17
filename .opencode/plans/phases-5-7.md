# План: фазы 5–7 (разделение LLM-слоя, JSON-предупреждения, Pydantic-схемы)

## Контекст

Текущее состояние (сверено с источником):

- `app/services/llm_service.py` — 556 строк: 5 промптов модульного уровня
  (QUERY_TO_CARD, PASSPORT_TO_CARD, EXPLAIN_MATCH, ENTITY_EXTRACTION,
  QUERY_VALIDATION) + один класс `LLMService` (транспорт + извлечение +
  парсинг запроса).
- `test_llm_agent_integration.py` патчит `LLMService._make_client` и
  проверяет свойства `llm` / `fallback_llm` — этот контракт обязателен к
  сохранению.
- `app/services/agents/warnings.py` — 23 каноничных текста предупреждений,
  совпадающих с `complex_questions_40.jsonl` — приёмочные формулировки.
  Вызов из `answer_builder.build_scenario_warnings(parsed, intent)`.
- `AgentContext.catalog` (context.py) читает `regulated_mtr_catalog_1000.jsonl`
  как сырые dict — это точка валидации.
- `search_router.route_query_text` возвращает dict решения без схемы.

## Фаза 5 — Разделение LLM-слоя

Новые модули:

1. `app/services/llm_prompts.py`
   - Перенести 5 модульных промптов дословно (схема и текст ответа LLM).
   - Объявить их как именованные константы.

2. `app/services/llm_client.py` — класс `LLMClient`
   - Транспорт: `_make_client`, свойства `llm`/`fallback_llm`, `invoke`,
     `structured_invoke`.
   - Логика таймаутов/ретраев: использовать `settings.LLM_TIMEOUT`
     (default 120), `settings.LLM_MAX_RETRIES` (default 2).
   - Режим JSON: json_mode для Ollama-клиентов из `settings.LLM_JSON_MODE`
     (default true) — то же поведение, что в текущей реализации.

3. `app/services/card_extractor.py` — класс `CardExtractor`
   - Методы: `extract_card_from_text`, `generate_explanation`,
     `_extract_card_from_response`, `_parse_explanation_response`,
     `_empty_card`. Текстовые блоки и обвязка — без изменений поведения.

4. `app/services/query_parser_llm.py` — класс `QueryParserLLM`
   - Методы: `parse_query`, `parse_engineering_query`,
     `validate_and_correct_query`, `_apply_llm_corrections`.
   - Сохранить сигнатуры и fallback-логику.

5. `app/services/llm_service.py` — фасад
   - `class LLMService(LLMClient)`, публичный API не меняется.
   - Оставить `_make_client` и свойства `llm`/`fallback_llm`, чтобы патчи
     тестов продолжали работать.
   - Методы `parse_query`/`parse_engineering_query`/`validate_and_correct_query`/
     `extract_card_from_text`/`generate_explanation` делегируют в
     `CardExtractor` и `QueryParserLLM` (композиция), либо остаются тонкой
     обёрткой.

Проверка: `pytest app/tests/test_llm_agent_integration.py
app/tests/test_llm_explainer.py app/tests/test_llm_reviewer.py
app/tests/test_llm_router.py app/tests/test_search_router.py`.
Импорт `LLMService` в `main.py`, `search_service.py`, `entity_extractor.py`
не менять.

## Фаза 6 — Предупреждения на JSON-правилах

1. Новый `app/services/agents/scenario_warnings.json`
   - Полный датасет предупреждений: 23 каноничных текста.
   - Схема:
     ```json
     {
       "scenario": "h2s",
       "trigger": {"medium_kind": ["h2s"]},
       "warnings": [
         {"text": "...", "condition": {"ops": ["inventory"], "text_contains": ["на складе"]}}
       ]
     }
     ```
   - Поле `condition` опционально: для базовых предупреждений сценария
     отсутствует (безусловные для сценария).

2. `app/services/agents/warnings.py` — движок правил
   - Загружает JSON, вычисляет признаки ({medium_kind, ops, text,
     planned, replacement, duplicates, intent}), фильтрует по trigger,
     применяет condition, дедуплицирует.
   - Сохранить сигнатуру `build_scenario_warnings(parsed, intent)`.
   - `_medium`, `_medium_kind`, `_planned` — оставить как вспомогательные
     или перенести внутрь движка (поведение то же).

3. Байт-эквивалентность:
   - Прогнать 40 вопросов + тестовые запросы (корпус из 49 кейсов), сверить
     списки предупреждений «до/после».

## Фаза 7 — Pydantic-схемы

1. `app/schemas.py`:
   - `CatalogProperty` (properties[].*), `CatalogCodes`, `CatalogCard`
     (карточка каталога: schema_version, card_id, card_version,
     lifecycle_status, item_type, subtype, name, designation, codes,
     properties, dcd). Строгие типы для ключевых полей, `extra="ignore"`,
     мягкие дефолты для остальных.
   - `RouterDecision` (route, mode, intent, intent_label, reasons,
     required_tools, missing_parameters, exact_codes, collections,
     normalized_query, detected_aliases).

2. `AgentContext.catalog` (context.py):
   - При загрузке JSONL валидировать каждую карточку через `CatalogCard`.
   - Невалидные карточки: лог-варнинг + пропуск (режим утверждён). Считать
     пропущенные и логировать сводку один раз.

3. `search_router.route_query_text`:
   - Собирать dict, затем валидировать через `RouterDecision.model_validate`
     и возвращать `model_dump()`. Ключи словаря не меняются.

Проверка: `python app/scripts/validate_catalog.py` (все 1000 карточек проходят),
`pytest app/tests/test_search_router.py`, `test_catalog_loader.py`,
`test_regulated_dataset.py`.

## Риски и решения

- Патч `LLMService._make_client` в тестах: класс наследует `LLMClient`, патч
  ставится на тот же класс.
- Артефакты отображения больших файлов: работать маленькими кусками с
  префиксом номера строки (проверено рабочее решение).
- 40 обязательных предупреждений остаются в JSON как есть (это и есть
  каноничные тексты приёмки).

## Порядок исполнения

1. Ф5: config -> промпты -> клиент -> извлечение -> парсер -> фасад -> тесты.
2. Ф6: JSON -> движок -> байт-сверка.
3. Ф7: схемы -> валидация каталога -> роутер -> скрипт-проверка.
4. Полный прогон тестов бэкенда.