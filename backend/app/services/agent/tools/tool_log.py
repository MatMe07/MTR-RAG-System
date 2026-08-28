# agent/tools/tool_log.py
"""Логирование вызовов инструментов (ЭТАП 3, секция 3F).

Записи пишутся в таблицу tool_execution_logs (PostgreSQL) при доступной БД,
иначе — в in-memory буфер. Индексы (request_id, tool_name, created_at)
определены моделью ToolExecutionLog и миграцией 003_add_audit.
"""

import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.agent.tool_log")


@dataclass
class ToolLogRecord:
    request_id: str
    tool_name: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]
    duration_ms: int
    user_id: Optional[str]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ToolExecutionLogger:
    """Логгер вызовов инструментов с fallback на память."""

    def __init__(self, max_memory: int = 2000):
        self._max_memory = max_memory
        self._memory: deque = deque(maxlen=max_memory)
        self._db_unavailable = False

    def _write_db(self, rec: ToolLogRecord) -> None:
        if self._db_unavailable:
            return
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import ToolExecutionLog as Model

            db = SessionLocal()
            try:
                db.add(Model(
                    request_id=rec.request_id,
                    tool_name=rec.tool_name,
                    input_data=rec.input_data,
                    output_data=rec.output_data,
                    duration_ms=rec.duration_ms,
                    user_id=rec.user_id,
                ))
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        except Exception as e:
            self._db_unavailable = True
            log.warning("ToolExecutionLogger: БД недоступна, лог в памяти: %s", e)

    def record(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        duration_ms: int,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ToolLogRecord:
        rec = ToolLogRecord(
            request_id=request_id or str(uuid.uuid4()),
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            error=error,
            duration_ms=int(duration_ms),
            user_id=user_id,
        )
        self._memory.append(rec)
        self._write_db(rec)
        return rec

    def get_logs(self, tool_name: Optional[str] = None, limit: int = 100) -> List[ToolLogRecord]:
        records = reversed(list(self._memory))
        if tool_name:
            records = (r for r in records if r.tool_name == tool_name)
        return list(records)[: max(0, limit)]

    def clear(self) -> None:
        self._memory.clear()


_logger: Optional[ToolExecutionLogger] = None


def get_tool_logger() -> ToolExecutionLogger:
    global _logger
    if _logger is None:
        _logger = ToolExecutionLogger()
    return _logger


def reset_tool_logger() -> None:
    global _logger
    _logger = None