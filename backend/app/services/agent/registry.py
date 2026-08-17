"""Фасад реестра агентских тулов (обратная совместимость).

Реализация разнесена по модулям (фаза 2 рефакторинга):
  * tool_registry.py — TOOLS, TOOL_ALIASES, resolve_tool, build_workspace;
  * tool_planner.py — INTENT_PLANS, AGENT_TO_TOOLS, plan_for_operations;
  * intent_resolver.py — INTENT_MAP, INTENT_LABELS, resolve_intent.

Здесь остаются re-export'ы, чтобы не ломать импорты
(from app.services.agents.registry import ...).
"""

from .tool_registry import (  # noqa: F401
    TOOLS,
    TOOL_ALIASES,
    build_workspace,
    resolve_tool,
)
from .tool_planner import (  # noqa: F401
    AGENT_TO_TOOLS,
    INTENT_PLANS,
    plan_for_operations,
)
