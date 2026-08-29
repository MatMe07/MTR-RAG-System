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
