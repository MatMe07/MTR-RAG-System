"""Исполнитель агентского слоя: планирует тулы по ParsedQuery и собирает AgentAnswer."""

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.schemas import AgentAnswer, AgentComponent, AgentSource, ParsedQuery

from .context import AgentContext
from .registry import build_workspace, plan_for_operations, resolve_tool
from .repository import get_agent_repository
from .reviewer import apply_review


def _to_components(rows: List[Dict[str, Any]]) -> List[AgentComponent]:
    components = []
    for row in rows:
        if not row:
            continue
        components.append(AgentComponent(
            mtr_code=row.get("mtr_code"),
            ksm_code=row.get("ksm_code"),
            name=row.get("name"),
            item_type=row.get("item_type"),
            quantity=row.get("quantity"),
            status=row.get("status"),
            detail=row.get("detail"),
            source_id=row.get("source_id"),
        ))
    return components


def _to_sources(rows: List[Dict[str, Any]]) -> List[AgentSource]:
    sources = []
    for row in rows:
        if not row:
            continue
        sources.append(AgentSource(
            kind=row.get("kind"),
            id=row.get("id"),
            fragment=row.get("fragment"),
        ))
    return sources


def run_agent(parsed: ParsedQuery, context: AgentContext | None = None,
              expected: Optional[Dict[str, Any]] = None) -> AgentAnswer:
    """Запускает план тулов и собирает структурированный ответ.

    expected — критерии правильного ответа из complex_questions_40.jsonl
    (используется автопроверкой 40 вопросов), передаются в ревьюер.
    """
    # По умолчанию — репозиторий по AGENT_STORAGE (json|db|auto): агент работает
    # либо с демо-JSON, либо с PostgreSQL+Qdrant. Явный context (AgentContext)
    # используется тестами/вызовом извне и приоритетнее.
    ctx = context or get_agent_repository()
    workspace = build_workspace()
    workspace["unit_ids"] = list(parsed.unit_ids or [])
    workspace["component_ids"] = list(parsed.component_ids or [])

    if settings.AGENT_LLM_MODE != "off":
        from ..llm_explainer import LlmExplainer
        ctx.llm_explainer = LlmExplainer()

    plan = plan_for_operations(parsed.operations, parsed.required_agents,
                               parsed.ambiguities, parsed=parsed)
    print(f"[agent] ctx={type(ctx).__name__} (storage={getattr(ctx, 'kind', '?')})", flush=True)
    print(f"[agent] план тулов: {plan}", flush=True)

    # Если запрос явно про участки/компоненты — сначала загружаем состав объекта,
    # чтобы stock_query/document_search работали по установленным позициям.
    if parsed.unit_ids or parsed.component_ids:
        plan = [t for t in plan if t != "graph_search"]
        plan.insert(0, "graph_search")

    # Ключевое слово «дубли» не выделяется парсером как операция — подключаем тул.
    if "дубл" in (parsed.original_query or "").lower():
        for t in ("duplicate_detector", "catalog_search"):
            if t not in plan:
                plan.append(t)

    # Если парсер вычленил изменение (DN150->DN200, среда H2S) — обязательно
    # нужен анализ влияния даже без явной операции impact.
    if parsed.proposed_changes:
        for t in ("impact_analyzer", "graph_search", "regulation_lookup"):
            if t not in plan:
                plan.append(t)
    tools_used: List[str] = []
    answers: List[str] = []
    all_components: List[Dict[str, Any]] = []
    all_warnings: List[str] = []
    all_sources: List[Dict[str, Any]] = []
    missing: List[str] = []
    review = False

    for tool_name in plan:
        tool = resolve_tool(tool_name)
        if tool is None:
            continue
        tools_used.append(tool_name)
        try:
            result = tool(ctx, parsed, workspace)
        except Exception as exc:  # noqa: BLE001 — тул не должен ронять весь план
            all_warnings.append("Тул %s завершился с ошибкой: %s" % (tool_name, exc))
            continue
        if result.get("text"):
            answers.append(result["text"])
        all_components.extend(result.get("components") or [])
        all_warnings.extend(result.get("warnings") or [])
        all_sources.extend(result.get("sources") or [])
        for m in result.get("missing") or []:
            if m not in missing:
                missing.append(m)
        review = review or bool(result.get("review"))

    if not answers:
        answers.append("Не удалось собрать ответ: недостаточно данных по запросу.")

    print(f"[agent] готово: tools_used={tools_used} ответов={len(answers)} "
          f"компонентов={len(all_components)}", flush=True)
    answer_text = "\n".join(answers)

    intent = _guess_intent(parsed)

    from .warnings import build_scenario_warnings
    scenario_warnings = build_scenario_warnings(parsed, intent)

    answer = AgentAnswer(
        query=parsed.original_query,
        intent=intent,
        intent_label=_INTENT_LABELS.get(intent),
        route="agent",
        mode="offline_rules",
        tools_used=tools_used,
        answer=answer_text,
        components=_to_components(all_components),
        warnings=_dedupe(all_warnings + scenario_warnings),
        sources=_to_sources(all_sources),
        missing_parameters=_dedupe(missing),
        human_review_required=review,
        parsed_confidence=parsed.confidence,
        parsed_query=parsed,
    )
    answer = apply_review(answer, expected=expected)

    # LLM-усиление (auto = всегда пытаться, при недоступности — офлайн-фолбэк):
    # 1) синтез связного answer; 2) LLM-ревьюер поверх детерминированного.
    if settings.AGENT_LLM_MODE != "off":
        from .llm_agent import apply_llm_synthesis
        from .llm_reviewer import apply_llm_review

        answer = apply_llm_synthesis(answer, tool_texts=answers)
        answer = apply_llm_review(answer, expected=expected)
    return answer


_INTENT_LABELS = {
    "search": "Поиск по каталогу",
    "replacement": "Подбор замены",
    "inventory": "Склад и запас",
    "maintenance": "План ТОиР",
    "object_configuration": "Сборка участка",
    "document_search": "Поиск документов",
    "impact_analysis": "Анализ влияния",
    "equipment_guidance": "Справочная информация",
    "duplicates": "Проверка дублей",
}


def _guess_intent(parsed: ParsedQuery) -> str:
    ops = parsed.operations or ["search"]
    if "plan" in ops and not parsed.unit_ids and parsed.card and (parsed.card.geometry or parsed.card.pressure):
        return "object_configuration"
    mapping = {
        "replace": "replacement",
        "inventory": "inventory",
        "calculate": "inventory",
        "plan": "maintenance",
        "assemble": "object_configuration",
        "document": "document_search",
        "impact": "impact_analysis",
        "explain": "equipment_guidance",
    }
    for op in ops:
        if op in mapping:
            return mapping[op]
    if parsed.proposed_changes:
        return "impact_analysis"
    return "search"


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


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
