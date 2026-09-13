# План исправлений MTR-RAG-System

Статус: в работе. Обновлять по мере выполнения. Фронт `frontend/` (legacy) НЕ трогаем.

---

## P1 — Критические баги и безопасность

### 1.1 Починить `/search/history` (backend/app/api/v1/search.py:127-164)
- Причина: в цикле `for log in logs` переменная `log` затирает логгер; строка 148 (`results = log.data...`) выполняется до цикла на логгере → `AttributeError` → пустой список.
- Фикс: переписать — удалить строку 148, внутри цикла `results`/`warnings` вычислять из элемента массива.
- Приёмка: тест `GET /api/v1/search/history` с авторизацией возвращает реальные записи.

### 1.2 Обязательный auth на `/search` и `/clarify` (search.py:18-77, 93-124)
- Заменить `Optional[str] Header(None)` на обязательный заголовок в обоих эндпоинтах.
- Вынести в FastAPI-зависимость на базе `get_current_user` (api/deps/auth.py).
- 401 без токена, `user_id` всегда не None при логировании.
- Приёмка: тесты — без токена 401, с валидным — 200. UI `ui_streamlit/components/api.py` уже шлёт Bearer.

### 1.3 Секреты
- Операционно: ротировать утёкшие OpenRouter/HF/Qdrant ключи (в открытом виде в `.env`/`.envMain`, gitignored).
- Код: в production-режиме c дефолтным `SECRET_KEY` — старт с ошибкой (config.py:44).
- Приёмка: `ENV=production` + дефолт `SECRET_KEY` → отказ старта.

---

## P2 — State management: Redis + конкуренция

### 2.1 ClarificationManager → Redis (clarify.py:126-221)
- Заменить `_sessions` dict + `threading.Lock` на Redis через `get_redis_cache()` (`repository/providers/redis_cache.py:159`): ключ `clarify:{session_id}` (JSON, TTL 1ч).
- Вызывать `reset(session_id)` в `search.py` при `proceed`/`expert`.
- Приёмка: параллельные `clarify` одним `session_id` не теряют turn; после завершения диалога ключ исчезает.

### 2.2 Executor: убрать общее мутируемое состояние (executor.py:161, 367-368)
- `self._auto_start` → передавать `start` параметром в `_log_escalation`.
- Приёмка: два параллельных `execute(auto)` не «перезаписывают» duration_ms.

### 2.3 Чекпоинты LangGraph (agent_graph.py:183-208, executor.py:104)
- Уникальный `thread_id` на запрос (uuid) вместо общего `"default"`.
- Опция `checkpoint_type == "redis"` (пакет `langgraph-checkpoint-redis`), TTL на чекпоинты.
- Убрать глобальный кеш графа `_agent_graph` (agent_graph.py:203-208).
- Приёмка: прогоны не растут в памяти; разные `checkpoint_type` у двух Executor не мешают.

### 2.4 Согласовать `use_llm` (executor.py:44-48 vs llm/agent.py:104-106)
- `LLMAgent` не создаёт сам `LLMClient` при `use_llm=False` — пробрасывать клиент из Executor; починить токен-аккаунтинг (executor.py:305-313).
- Приёмка: `mode="llm"` при `use_llm=False` → явная ошибка/откат к deterministic.

---

## P3 — Дед-код и хрупкость

### 3.1 Мелочи (выполнено)
- `clarify.py:73` — мёртвая строка `text = " и " if len(missing) > 1 or True else " или "` — уже не существует
- `executor.py:110-112` — закомментированный debug `print` — уже отсутствует
- `nodes.py:31-34` — `_set_repository` no-op: функция и все вызовы (nodes.py:148,156,170,177,184) удалены
- `agent.py:130,210-227` — `sources` никогда не заполняется: мёртвый параметр/переменная удалены
- `detect.py:15-18` + `intent/__init__.py:22-25` — дубль статусных констант: `__init__.py` re-export из detect.py
- `client.py:92-95` — мёртвый `except TimeoutError`: заменён на `except httpx.TimeoutException` (реальный таймаут)
- `constants.py:46` — дубль `BLOCKER_FIELDS`: удалён (канон в `intent/matrix.py:154`)

### 3.2 Ложные срабатывания substring (выполнено)
- `medium.py`: токен-логика + исключения префиксов; `"H2SO4"`/`"водород*"` больше не матчатся в `"h2s"`/`"вод"`.
- Приёмка: `test_medium.py` (15 тестов).

### 3.3 Greedy JSON-парсинг (выполнено)
- Общий утилит `extract_json_object` в `llm/json_utils.py`; `response_parser.py`/`refine.py` используют его.
- Доп.: `llm_extractor` фиксирует пустой JSON-ответ LLM как `extractor_errors`.

### 3.4 Остальные
- `detect.py` — `"по "` убран из `_det_CHECK_SUFFICIENCY` (слишком широкий); `_STOP_WORDS`: удалены дубль `"нужна"` и мёртвый `"и"` (токен-регекс `{3,}`)
- `SearchRequest.top_k`/`filters` — задокументированы как резерв (не влияют на пайплайн)

---

## P4 — Тесты и CI/CD

- 4.1 Починить падающий `test_normalizers.py:83`.
- 4.2 HTTP-тесты: `/search`, `/clarify`, `/history`, `/auth/login`, `/compare/`, `/norms/search`, `/expert/*`; юнит: `search_service`, `auth_service`, `compare_service`, `norms_service`, `expert_service`.
- 4.3 CI (GitHub Actions): `ruff` + `pytest` (unit/integration). Убрать `asyncio_mode="auto"` (pyproject.toml:67).
- 4.4 Поднять `MIN_TOOLS_COVERAGE` (test_40_questions.py:32).

---

## P5 — Консолидация и долг

- 5.1 Объединить `app/schemas.py` (550 LOC) и `app/models/pydantic/schemas.py` (300 LOC).
- 5.2 Удалить `REPtest_ocr.py` + `passport1.pdf`, пустой `backend/requirements.txt`; `.gitignore` + `MTR Local.session.sql`, `compose_check/`, `data/evaluation/results/`, `.envMain`; запушить 16 коммитов.
- 5.3 Env-дрейф: `OPENROUTER_TOKEN`/`OPENROUTER_API_KEY`, legacy `QDRANT_COLLECTION` (config.py:29), удалить `.envMain`; pandas-пины.
- 5.4 Дефолтные креды: `DEFAULT_USERS` (main.py:14-19), префил `admin123` (ui_streamlit/app.py:26) — за env `INITIAL_*_PASSWORD`.

---

## Порядок
P1 → P2 → P3 → P4 → P5. P2 частично блокирует P3 (общие файлы).