"""Исполнение плана тулов: цикл вызовов и агрегация результатов.

Выделено из executor.run_agent (фаза 3 рефакторинга). Executor остаётся
оркестратором: планирование -> ToolPlanner, исполнение -> сюда,
сборка ответа -> answer_builder.
"""

from typing import Any, Dict, List

from app.core.logging import get_logger
from app.schemas import ParsedQuery

from .tool_registry import resolve_tool

log = get_logger("agent.tool_executor")


def execute_plan(ctx: Any, parsed: ParsedQuery, plan: List[str],
                 workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Выполняет план тулов и агрегирует их результаты.

    Возвращает dict с полями: tools_used, answers, components, warnings,
    sources, missing, review. Ошибки отдельных тулов не роняют план —
    превращаются в предупреждение.
    """
    tools_used: List[str] = []
    answers: List[str] = []
    components: List[Dict[str, Any]] = []
    warnings: List[str] = []
    sources: List[Dict[str, Any]] = []
    missing: List[str] = []
    review = False

    cache = workspace.setdefault("cache", {})
    for tool_name in plan:
        cached = cache.get(("tool:" + tool_name))
        tool = cached if callable(cached) else resolve_tool(tool_name)
        if tool is None:
            continue
        cache["tool:" + tool_name] = tool
        tools_used.append(tool_name)
        try:
            result = tool(ctx, parsed, workspace)
        except Exception as exc:  # noqa: BLE001 — тул не должен ронять весь план
            warnings.append("Тул %s завершился с ошибкой: %s" % (tool_name, exc))
            continue
        if result.get("text"):
            answers.append(result["text"])
        components.extend(result.get("components") or [])
        warnings.extend(result.get("warnings") or [])
        sources.extend(result.get("sources") or [])
        for m in result.get("missing") or []:
            if m not in missing:
                missing.append(m)
        review = review or bool(result.get("review"))

    return {
        "tools_used": tools_used,
        "answers": answers,
        "components": components,
        "warnings": warnings,
        "sources": sources,
        "missing": missing,
        "review": review,
    }
