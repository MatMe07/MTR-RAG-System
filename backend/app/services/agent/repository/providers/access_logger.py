# repository/providers/access_logger.py
"""Журнал доступа к данным (data_access_logs).

Каждый вызов провайдера фиксирует: метод, провайдера, попадание в кеш,
использование fallback и длительность. Запись — в PostgreSQL; при недоступности
БД журнал работает как no-op с периодическим повтором (самовосстановление).
"""

import logging
import time
from typing import Any, Dict, Optional

from .access_context import get_request_id

log = logging.getLogger("mtr.repository.access_logger")


class DataAccessLogger:
    """Синхронная запись в data_access_logs c самовосстановлением."""

    def __init__(self, retry_every: int = 100):
        self._retry_every = max(1, int(retry_every))
        self._fail_streak = 0

    def record(
        self,
        method_name: str,
        params: Optional[Dict[str, Any]] = None,
        provider_used: Optional[str] = None,
        duration_ms: Optional[float] = None,
        cache_hit: Optional[bool] = None,
        fallback_used: Optional[bool] = None,
        fallback_reason: Optional[str] = None,
        error: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if not method_name:
            return
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import DataAccessLog as Model

            db = SessionLocal()
            try:
                db.add(
                    Model(
                        request_id=request_id or get_request_id(),
                        method_name=method_name,
                        params=params,
                        provider_used=provider_used,
                        duration_ms=int(duration_ms or 0),
                        cache_hit=bool(cache_hit) if cache_hit is not None else None,
                        fallback_used=bool(fallback_used) if fallback_used is not None else None,
                        fallback_reason=fallback_reason,
                        error=error,
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
            self._fail_streak = 0
        except Exception as e:
            self._fail_streak += 1
            if self._fail_streak % self._retry_every == 0:
                log.warning("DataAccessLogger: БД недоступна (%d подряд), пропуск: %s", self._fail_streak, e)


_logger: Optional[DataAccessLogger] = None


def get_data_access_logger() -> DataAccessLogger:
    global _logger
    if _logger is None:
        _logger = DataAccessLogger()
    return _logger


def record_access(**kwargs: Any) -> None:
    get_data_access_logger().record(**kwargs)


class timed_access:
    """Таймер доступа: измеряет длительность и пишет запись даже при ошибке."""

    def __init__(
        self,
        method_name: str,
        provider_used: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        self._method_name = method_name
        self._provider_used = provider_used
        self._params = params
        self._request_id = request_id
        self._started: float = 0.0

    def __enter__(self) -> "timed_access":
        self._started = time.monotonic()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        duration = (time.monotonic() - self._started) * 1000.0
        get_data_access_logger().record(
            method_name=self._method_name,
            provider_used=self._provider_used,
            params=self._params,
            duration_ms=duration,
            error=str(exc) if exc else None,
            request_id=self._request_id,
        )