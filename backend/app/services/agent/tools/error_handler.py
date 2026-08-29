# agent/tools/error_handler.py
"""Обработчик ошибок выполнения инструментов (ЭТАП 4, секция 4B.1 ErrorHandler).

Таблица действий по типу ошибки (4B):

| Тип ошибки                  | Действие                                    |
|-----------------------------|---------------------------------------------|
| INVALID_PARAMS              | Остановка (STOP)                            |
| NOT_FOUND                   | Пропуск (SKIP), если инструмент не обязателен |
| BATCH_TOO_LARGE             | Повтор с уменьшенным размером батча          |
| DAL_ERROR / TIMEOUT         | Retry до 3 раз с экспоненциальной задержкой  |
| UNKNOWN                     | Остановка, логирование                       |

Обязательные инструменты: search_catalog, get_component, check_stock —
при их ошибке выполнение останавливается.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .errors import ToolErrorCode

log = logging.getLogger("mtr.agent.error_handler")

REQUIRED_TOOLS = {"search_catalog", "get_component", "check_stock"}

MAX_RETRIES = 3
# Экспоненциальная задержка: 0.2с, 0.4с, 0.8с.
RETRY_BACKOFF_BASE = 0.2

# Коды, которые можно повторить.
_RETRIABLE = {ToolErrorCode.DAL_ERROR, ToolErrorCode.TIMEOUT}
# Коды, предписывающие остановку.
_STOP = {ToolErrorCode.INVALID_PARAMS, ToolErrorCode.TOOL_NOT_FOUND}


class ErrorDecision:
    """Решения обработчика ошибок."""

    PROCEED = "proceed"  # результат есть, ошибок нет
    RETRY = "retry"      # повторить
    RETRY_BATCH = "retry_batch"  # повторить с уменьшенным батчем
    SKIP = "skip"        # пропустить инструмент
    STOP = "stop"        # остановить выполнение


class ErrorHandler:
    """Исполнение инструмента с ретраями и классификацией ошибок."""

    def __init__(
        self,
        max_retries: int = MAX_RETRIES,
        retry_backoff_base: float = RETRY_BACKOFF_BASE,
    ):
        self._max_retries = max_retries
        self._backoff = retry_backoff_base

    def decide(self, error: Optional[Dict[str, Any]], required: bool = False) -> str:
        """Классификация ошибки → действие."""
        if error is None:
            return ErrorDecision.PROCEED
        code = str(error.get("code", "UNKNOWN")).upper()

        if code in _STOP:
            return ErrorDecision.STOP
        if code == ToolErrorCode.NOT_FOUND:
            # Обязательные инструменты при NOT_FOUND останавливают,
            # необязательные — пропускаются (4B).
            return ErrorDecision.STOP if required else ErrorDecision.SKIP
        if code == ToolErrorCode.BATCH_TOO_LARGE:
            return ErrorDecision.RETRY_BATCH
        if code in _RETRIABLE:
            return ErrorDecision.RETRY
        return ErrorDecision.STOP

    def _retry_delay(self, attempt: int) -> float:
        # attempt начинается с 0: 0.2, 0.4, 0.8 экспоненциально.
        return self._backoff * (2 ** attempt)

    def run(
        self,
        execute: Any,
        tool_name: str = "",
        input_data: Optional[Dict[str, Any]] = None,
        required: bool = False,
    ) -> Dict[str, Any]:
        """Выполняет инструмент с обработкой ошибок.

        execute — вызываемая (input) -> {'result': ..., 'error': None|dict}
        (контракт run_instrument из instruments.py).

        Возвращает тот же контракт + поле 'decision'.
        """
        input_data = input_data or {}
        result = execute(input_data)
        decision = self.decide(result.get("error"), required=required)

        if decision == ErrorDecision.STOP:
            result["decision"] = ErrorDecision.STOP
            return result

        if decision in (ErrorDecision.SKIP, ErrorDecision.PROCEED):
            result["decision"] = decision
            return result

        # RETRY / RETRY_BATCH — ретраи с уменьшенным батчем, где применимо.
        for attempt in range(1, self._max_retries + 1):
            if decision == ErrorDecision.RETRY_BATCH:
                reduced = self._reduce_batch(input_data)
                if reduced is None:
                    result["decision"] = ErrorDecision.STOP
                    return result
                input_data = reduced
            # Последняя попытка не тратит время на ожидание.
            if attempt < self._max_retries:
                time.sleep(self._retry_delay(attempt - 1))
            result = execute(input_data)
            decision = self.decide(result.get("error"), required=required)
            if decision in (ErrorDecision.PROCEED, ErrorDecision.SKIP):
                result["decision"] = decision
                return result
            if decision == ErrorDecision.STOP:
                result["decision"] = ErrorDecision.STOP
                return result
            # RETRY / RETRY_BATCH — продолжаем цикл.

        result = result or execute(input_data)
        result["decision"] = ErrorDecision.STOP
        if not result.get("error"):
            result["decision"] = ErrorDecision.PROCEED
        return result

    @staticmethod
    def _reduce_batch(input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Уменьшает список ksm_codes вдвое для повторной попытки."""
        batch = input_data.get("ksm_codes")
        if isinstance(batch, list) and len(batch) > 1:
            reduced = dict(input_data)
            reduced["ksm_codes"] = batch[: max(1, len(batch) // 2)]
            return reduced
        return None