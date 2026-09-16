# MTR-RAG-System

MVP рекомендательной системы для поиска аналогов МТР в документации газопровода. Система формирует карточку изделия, ранжирует кандидатов и показывает эксперту совпадения, расхождения, предупреждения и источники.

## Демонстрационный экран эксперта

Из корня проекта выполните:

```powershell
python -m pip install -r frontend/requirements.txt
python -m streamlit run frontend/app.py
```

Затем откройте адрес, который появится в терминале (обычно `http://localhost:8501`). Экран работает без backend на сценарии Q007 из `data/sample/ui_demo_case_q007.json`.

Это рекомендательная демонстрация: окончательное решение по кандидату принимает эксперт.

## Полный стек (PG + Redis + Neo4j + Qdrant)

Backend по умолчанию работает против PostgreSQL с fallback на JSON-данные.
Остальные источники подключаются as-available: Redis-кеш, Neo4j (граф объекта),
Qdrant (векторный поиск нормативов), PG `documents`/`extracted_characteristics`
(паспорта) и `mtr_item_history` (история).

Конфигурация — через переменные окружения (дефолты: локальный compose-стек
`docker-compose.yml`). Секреты/облако — только через `.env` (в .gitignore).

```powershell
docker compose up -d --build
cd backend
alembic upgrade head
python -m app.scripts.seed_stack --all   # каталог/PG, граф, нормы, паспорта, историю
```

Интеграционный тест: `app/tests/test_phase5_stack_integration.py` — запускается
только при доступном стеке (иначе авто-skip). Полный набор:
`python -m pytest app/tests -q`.

Теzlенисы: режимы `deterministic` (по умолчанию) и `llm` (экспериментальный), API `/api/v1/search` принимает `mode`. Async-задачи (OCR-синк, переиндексация
норм) — Celery (`app/workers/celery_app.py`), worker/beat в compose.

## Диагностика (answer.parser_diagnostics / answer.llm)

Каждый `AgentAnswer` теперь содержит два диагностических блока: один формируется
гибридным парсером (`parser_diagnostics`), другой — LLM/оркестратором (`answer.llm`).
Оба сериализуются в обычный JSON `answer.model_dump()` (пример транскрипта —
`compose_check/query.md`).

### parser_diagnostics (в `parsed`, переносится в answer)

| Поле | Тип | Описание |
|---|---|---|
| `parse_ms` | float | Суммарное время парсинга (мс). |
| `strategy` | str | Стратегия слияния: `rule` / `enrich` / `merge`. |
| `rule_confidence` | float | Лучшая rule-уверенность до слияния. |
| `natasha_used` | bool | Запускался ли NER-этап (Natasha). |
| `stages_ms` | dict | Время по этапам: `rule`, `natasha`, `merge`, опционально `llm`. |
| `llm_extractor` | dict | Мини-снимок LLM-экстрактора: `{enabled, calls, hits, errors, tokens}`. `enabled=true` означает, что экстрактор настроен, но мог не вызываться (calls=0, если rule-парсер уже покрыл все параметры). |

### answer.llm (диагностика LLM, по одному запросу)

| Поле | Тип | Описание |
|---|---|---|
| `available` | bool | LLMClient доступен и настроен для данного запроса. |
| `used` | bool | Хотя бы один LLM-вызов или итерация C1+ была выполнена. |
| `reason` | str\|null | Человекочитаемое пояснение (например, «LLM не вызывался: детерминированный auto-ответ прошёл quality gate»). |
| `model` | str\|null | Использованная модель (например, `inclusionai/ling-3.0-flash-vl:free`). |
| `total_calls` | int | Количество HTTP-вызовов к LLM-провайдеру. |
| `cache_hits` / `cache_misses` | int | Попадания/промахи кэша LLM для данного запроса. |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | int | Подсчёт токенов (0, если провайдер не возвращает usage). |
| `duration_ms` | float | Суммарное время HTTP-запросов (мс). |
| `cost_estimate_usd` | float\|null | Оценка стоимости в USD (`0.0` для `:free`-моделей, `null` если неизвестно). |
| `refine_iterations` | list[dict] | Шаги цикла C1+: `{n, action, tool_name, tool_input, error, verdict, gaps, duration_ms}`. Пустой список, если C1+ не запускался. |
| `calls` | list[dict] | Лог по каждому вызову: `{stage, mode, prompt_tokens, completion_tokens, total_tokens, duration_ms, cache_hit, error, ts}`. `stage` — `extract` / `refine` / `agent`. |

## Транскрипт

Пример сквозного транскрипта с реальным LLM сохранён в `compose_check/query.md`.
Генерация:

```
cd backend
printf '<запрос>\n2\n' | python3 app/app_console.py > ../compose_check/query.md
```

Отчёт детерминированной базовой проверки (40 вопросов) —
`data/evaluation/results/40_questions_report.{json,md}`, пересборка:

```
cd backend
python3 -m pytest app/tests/test_40_questions.py -q
```
