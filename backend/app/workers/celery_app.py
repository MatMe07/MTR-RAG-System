# workers/celery_app.py
"""Celery-приложение (async-задачи: OCR-синк документов, переиндексация норм).

docker-compose поднимает celery-worker и celery-beat командой
`celery -A app.workers.celery_app ...`. Брокер/бэкенд — Redis (REDIS_URL).
"""

from celery import Celery

from app.config import settings

REDIS_URL = settings.REDIS_URL or "redis://localhost:6379/0"

celery_app = Celery(
    "mtr_rag",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.tasks"],
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

# Периодические задачи — настраиваются отдельно (beat_schedule).
celery_app.conf.beat_schedule = {}