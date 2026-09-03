# agent/llm/log.py
"""Логирование шагов LLM-режима (ЭТАП 4, секция 4C.4).

Для каждой итерации пишутся: номер, промпт, ответ LLM (включая выбранное
действие), результат инструмента (или вопрос пользователю), время шага.
Записи идут в таблицу llm_agent_logs при доступной БД, иначе — в память.
"""

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.agent.llm_log")


@dataclass
class LLMLogRecord:
    request_id: str
    iteration: Optional[int]
    prompt: str
    response: Dict[str, Any]
    tool_result: Optional[Dict[str, Any]]
    duration_ms: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LLMAgentLogger:
    """Логгер итераций LLM-агента с fallback на память."""

    def __init__(self, max_memory: int = 2000):
        self._max_memory = max_memory
        self._memory: deque = deque(maxlen=max_memory)
        self._fail_streak = 0
        self._retry_every = 100

    def _write_db(self, rec: LLMLogRecord) -> None:
        if self._fail_streak and self._fail_streak >= self._retry_every:
            # периодическое самовосстановление после падения БД
            self._fail_streak = 0
        if self._fail_streak:
            return
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import LlmAgentLog as Model

            db = SessionLocal()
            try:
                db.add(Model(
                    request_id=rec.request_id,
                    iteration=rec.iteration,
                    prompt=rec.prompt,
                    response=rec.response,
                    tool_result=rec.tool_result,
                    duration_ms=rec.duration_ms,
                ))
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        except Exception as e:
            self._fail_streak += 1
            log.warning("LLMAgentLogger: БД недоступна (%d), лог в памяти: %s", self._fail_streak, e)

    def record(
        self,
        prompt: str,
        response: Dict[str, Any],
        duration_ms: int,
        iteration: Optional[int] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> LLMLogRecord:
        rec = LLMLogRecord(
            request_id=request_id or str(uuid.uuid4()),
            iteration=iteration,
            prompt=prompt,
            response=response,
            tool_result=tool_result,
            duration_ms=int(duration_ms),
        )
        self._memory.append(rec)
        self._write_db(rec)
        return rec

    def get_logs(self, request_id: Optional[str] = None, limit: int = 100) -> List[LLMLogRecord]:
        records = reversed(list(self._memory))
        if request_id:
            records = (r for r in records if r.request_id == request_id)
        return list(records)[: max(0, limit)]

    def clear(self) -> None:
        self._memory.clear()


_logger: Optional[LLMAgentLogger] = None


def get_llm_logger() -> LLMAgentLogger:
    global _logger
    if _logger is None:
        _logger = LLMAgentLogger()
    return _logger


def reset_llm_logger() -> None:
    global _logger
    _logger = None