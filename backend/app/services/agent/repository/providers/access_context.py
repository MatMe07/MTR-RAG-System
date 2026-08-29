# repository/providers/access_context.py
"""Контекст текущего запроса для журналов доступа к данным.

Значение проставляется исполнителем агента / API-слоем и читается
провайдерами при записи в data_access_logs.
"""

import contextvars
from typing import Any, Optional

_current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mtr_request_id", default="-"
)


def set_request_id(request_id: Optional[str]) -> None:
    _current_request_id.set(request_id or "-")


def get_request_id() -> str:
    return _current_request_id.get()


class request_scope:
    """Контекст-менеджер: задаёт request_id на время выполнения блока."""

    def __init__(self, request_id: Optional[str] = None):
        self._token: Any = None
        self._rid = request_id or "-"

    def __enter__(self) -> "request_scope":
        self._token = _current_request_id.set(self._rid)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _current_request_id.reset(self._token)