# workers/celery_app.py
"""Celery-приложение (async-задачи: OCR-синк документов, переиндексация норм).

docker-compose поднимает celery-worker и celery-beat командой
`celery -A app.workers.celery_app ...`. Брокер/бэкенд — Redis (REDIS_URL).
"""

import os

from celery import Celery

from app.config import settings

REDIS_URL = settings.REDIS_URL or "redis://localhost:6379/0"

celery_app = Celery(
    "mtr_rag",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.tasks", "app.workers.passport_worker"],
)

celery_app.conf.update(
    timezone="UTC",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="mtr.tasks",
    task_track_started=True,
    worker_max_tasks_per_child=200,
)

# Тестовый режим (план B.8.2): CELERY_TASK_ALWAYS_EAGER=1 — задачи
# выполняются синхронно в вызывающем процессе, брокер не нужен.
_eager = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").strip().lower()
if _eager in ("1", "true", "yes"):
    celery_app.conf.update(task_always_eager=True)
    _propagate = os.environ.get("CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS", "1").strip().lower()
    if _propagate in ("1", "true", "yes"):
        celery_app.conf.update(task_eager_propagates=True)

# Периодические задачи — настраиваются отдельно (beat_schedule).
celery_app.conf.beat_schedule = {}
