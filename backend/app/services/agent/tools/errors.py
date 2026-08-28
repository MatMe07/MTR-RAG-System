# agent/tools/errors.py
"""Стандартизированные ошибки инструментов (ЭТАП 3, секция 3D)."""

from typing import Any, Dict, Optional


class ToolErrorCode:
    """Коды ошибок инструментов."""

    NOT_FOUND = "NOT_FOUND"
    INVALID_PARAMS = "INVALID_PARAMS"
    DAL_ERROR = "DAL_ERROR"
    TIMEOUT = "TIMEOUT"
    BATCH_TOO_LARGE = "BATCH_TOO_LARGE"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"


class ToolError(Exception):
    """Структурированная ошибка инструмента."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }