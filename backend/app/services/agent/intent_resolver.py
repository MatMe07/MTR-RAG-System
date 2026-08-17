"""Единый источник правды по интентам запроса.

INTENT_MAP — операция/действие -> канонический интент. Объединяет словари,
которые раньше были продублированы в registry.plan_for_operations,
executor._guess_intent и search_router.route_query_text.

INTENT_LABELS — метки всех интентов. execоutor'ные метки (капитализированные)
используются в AgentAnswer и проверяются фронтендом; catalog_search добавлен
из search_router.

resolve_intent — единая функция разрешения интента из операций ParsedQuery
(с учётом специальных случаев: сборка участка по геометрии, proposed_changes,
«дубли»). Комбинированным операциям присваивается интент по INTENT_PRIORITY.
"""

from typing import Any, Dict, List, Optional

INTENT_LABELS: Dict[str, str] = {
    "search": "Поиск по каталогу",
    "catalog_search": "поиск по каталогу",
    "replacement": "Подбор замены",
    "inventory": "Склад и запас",
    "maintenance": "План ТОиР",
    "object_configuration": "Сборка участка",
    "document_search": "Поиск документов",
    "impact_analysis": "Анализ влияния",
    "equipment_guidance": "Справочная информация",
    "duplicates": "Проверка дублей",
}

# Операция/действие (query_parser, query_normalizer aliases) -> канонический интент.
INTENT_MAP: Dict[str, str] = {
    "search": "search",
    "check": "search",
    "catalog_search": "catalog_search",
    "replace": "replacement",
    "replacement": "replacement",
    "inventory": "inventory",
    "calculate": "inventory",
    "plan": "maintenance",
    "repair": "maintenance",
    "maintain": "maintenance",
    "maintenance": "maintenance",
    "assemble": "object_configuration",
    "object_configuration": "object_configuration",
    "document": "document_search",
    "document_search": "document_search",
    "impact": "impact_analysis",
    "impact_analysis": "impact_analysis",
    "explain": "equipment_guidance",
    "explanation": "equipment_guidance",
}

# Приоритет интентов для комбинированных операций: более специфичный побеждает.
INTENT_PRIORITY: List[str] = [
    "impact_analysis",
    "replacement",
    "object_configuration",
    "document_search",
    "inventory",
    "maintenance",
    "equipment_guidance",
    "search",
]


def intent_from_operation(op: Optional[str]) -> Optional[str]:
    """Интент для одной операции/действия (без фолбэков)."""
    return INTENT_MAP.get((op or "").strip().lower())


def resolve_intent(operations: Optional[List[str]],
                   parsed: Any = None) -> str:
    """Единое разрешение интента из операций ParsedQuery.

    parsed (ParsedQuery | None) нужен для специальных случаев:
      * «дубли» в тексте -> duplicates;
      * plan + геометрия без unit_ids -> object_configuration (сборка участка);
      * proposed_changes без специфичной операции -> impact_analysis.
    """
    ops = [op for op in (operations or []) if op]

    if parsed is not None:
        if "дубл" in (getattr(parsed, "original_query", "") or "").lower():
            return "duplicates"
        if "plan" in ops and not parsed.unit_ids:
            card = getattr(parsed, "card", None)
            geometry = getattr(card, "geometry", None) if card else None
            pressure = getattr(card, "pressure", None) if card else None
            has_geometry = bool(geometry and (geometry.dn or geometry.wall_thickness
                                               or geometry.angle))
            has_pressure = bool(pressure and pressure.pn)
            if has_geometry or has_pressure:
                return "object_configuration"
        if getattr(parsed, "proposed_changes", None):
            # generic ops (search/check) не считаем специфичной операцией:
            # изменение узла без явного интента -> impact_analysis.
            has_explicit_intent = any(
                (intent_from_operation(op) or "search") not in ("search", "catalog_search")
                for op in ops
            )
            if not has_explicit_intent:
                return "impact_analysis"

    for intent in INTENT_PRIORITY:
        for op in ops:
            if intent_from_operation(op) == intent:
                return intent
    return "search"


def intent_label(intent: Optional[str]) -> Optional[str]:
    """Метка интента (без падения для неизвестных значений)."""
    return INTENT_LABELS.get(intent or "")