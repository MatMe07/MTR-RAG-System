"""Исполнитель агентского слоя: оркестрация пайплайна запроса.

Фаза 3 рефакторинга: run_agent/execute_agent_query сохраняют сигнатуры,
но делегируют:
  * планирование -> ToolPlanner.build_agent_plan;
  * исполнение тулов -> ToolExecutor.execute_plan;
  * сборка ответа -> AnswerBuilder.build_answer;
  * ревью/LLM-усиление остаются здесь (apply_review, apply_llm_synthesis,
    apply_llm_review).

Публичные имена (_to_components, _to_sources, _dedupe) сохранены как
re-export для обратной совместимости.
"""

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas import AgentAnswer, ParsedQuery

from .context import AgentContext
from .intent_resolver import INTENT_LABELS, resolve_intent
from .repository import JsonAgentRepository, get_agent_repository
from .reviewer import apply_review
from .tool_executor import execute_plan
from .tool_planner import build_agent_plan
from .tool_registry import build_workspace
from .answer_builder import (  # noqa: F401
    _dedupe,
    _to_components,
    _to_sources,
    build_answer,
)

log = get_logger("agent.executor")


def run_agent(parsed: ParsedQuery, context: AgentContext | None = None,
              expected: Optional[Dict[str, Any]] = None) -> AgentAnswer:
    """Запускает план тулов и собирает структурированный ответ.

    expected — критерии правильного ответа из complex_questions_40.jsonl
    (используется автопроверкой 40 вопросов), передаются в ревьюер.
    """
    # По умолчанию — репозиторий по AGENT_STORAGE (json|db|auto): агент работает
    # либо с демо-JSON, либо с PostgreSQL+Qdrant. Явный context (AgentContext)
    # используется тестами/вызовом извне и приоритетнее; тулы работают только
    # через интерфейс AgentRepository, поэтому AgentContext оборачивается.
    ctx = context or get_agent_repository()
    if isinstance(ctx, AgentContext):
        ctx = JsonAgentRepository(context=ctx)

    workspace = build_workspace()
    workspace["unit_ids"] = list(parsed.unit_ids or [])
    workspace["component_ids"] = list(parsed.component_ids or [])
    plan = build_agent_plan(parsed)
    log.info("[agent] ctx=%s (storage=%s)", type(ctx).__name__, getattr(ctx, "kind", "?"))
    log.info("[agent] план тулов: %s", plan)

    if settings.AGENT_LLM_MODE != "off":
        from ..llm_explainer import LlmExplainer
        ctx.llm_explainer = LlmExplainer()

    result = execute_plan(ctx, parsed, plan, workspace)
    log.info("[agent] готово: tools_used=%s ответов=%d компонентов=%d",
             result["tools_used"], len(result["answers"]), len(result["components"]))

    intent = resolve_intent(parsed.operations, parsed=parsed)
    answer = build_answer(parsed, intent, result)
    answer = apply_review(answer, expected=expected)

    # LLM-усиление (auto = всегда пытаться, при недоступности — офлайн-фолбэк):
    # 1) синтез связного answer; 2) LLM-ревьюер поверх детерминированного.
    if settings.AGENT_LLM_MODE != "off":
        from .llm_agent import apply_llm_synthesis
        from .llm_reviewer import apply_llm_review

        answer = apply_llm_synthesis(answer, tool_texts=result["answers"])
        answer = apply_llm_review(answer, expected=expected)
    return answer


def execute_agent_query(query: str, extractor: Optional[Any] = None,
                        context: AgentContext | None = None,
                        expected: Optional[Dict[str, Any]] = None) -> AgentAnswer:
    """Полный цикл агентного запроса: парсинг (rule-based + LLM-коррекция) -> run_agent.

    Позволяет подменять extractor в тестах, не трогая сетевые LLM-вызовы.
    expected — критерии ответа (см. run_agent), используются ревьюером.
    """
    from app.services.entity_extractor import EntityExtractor

    if extractor is None:
        extractor = EntityExtractor()
    parsed = extractor.extract(query)
    return run_agent(parsed, context=context, expected=expected)
