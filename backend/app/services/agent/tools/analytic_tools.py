# agent/tools/analytic_tools.py

from typing import Any, Dict, List
from collections import defaultdict
import time

from .registry import register_tool
from .core_tools import _empty_result, _source, _card_component
from ..core.state import AgentState


@register_tool("impact_analyzer", "Анализ влияния изменений на соседние детали")
def impact_analyzer(state: AgentState) -> Dict[str, Any]:
    """Анализ влияния изменений"""
    start = time.time()
    result = _empty_result()
    
    parsed = state["parsed"]
    changes = getattr(parsed, "proposed_changes", {}) or {}
    tf = getattr(parsed, "technical_filters", {}) or {}
    
    # Определяем изменения из контекста
    if not changes.get("medium") and tf.get("medium"):
        medium = str(tf["medium"]).lower()
        if "h2s" in medium or "co2" in medium:
            changes["medium"] = str(tf["medium"])
    
    checks = []
    affected = set()
    
    if changes.get("dn_to") or changes.get("dn_from"):
        checks.append("проверить фланцы, прокладки, болты на новый DN")
        affected.update(["фланцы", "прокладки", "болты"])
    
    if changes.get("medium"):
        checks.append(f"проверить совместимость материалов и уплотнений со средой {changes['medium']}")
        affected.update(["уплотнения", "материал деталей"])
    
    if changes.get("material_to") or changes.get("strength_to"):
        checks.append("проверить класс прочности и сварку по нормативной базе")
        affected.update(["сварные швы"])
    
    for c in checks[:5]:
        result["components"].append({
            "ksm_code": None,
            "mtr_code": None,
            "name": "Проверка",
            "item_type": None,
            "quantity": None,
            "status": "required",
            "detail": c,
            "source_id": None,
        })
    
    for name in sorted(affected)[:5]:
        result["components"].append({
            "ksm_code": None,
            "mtr_code": None,
            "name": name,
            "item_type": None,
            "quantity": None,
            "status": "затронуто",
            "detail": "соседний узел при замене",
            "source_id": None,
        })
    
    result["sources"].append(_source("project_documentation", None, "оценка влияния требует проектной схемы"))
    result["review"] = True
    result["text"] = f"Анализ влияния: {len(checks)} проверок, {len(affected)} затронутых узлов"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


@register_tool("inventory_calculator", "Расчёт рекомендуемого запаса")
def inventory_calculator(state: AgentState) -> Dict[str, Any]:
    """Расчёт рекомендуемого запаса"""
    start = time.time()
    result = _empty_result()
    
    targets = state.get("ksm_targets", [])
    ctx = state.get("context", {}).get("repository")
    
    multiplier = getattr(state["parsed"], "units_count", 1) or 1
    
    for target in targets[:20]:
        card = target.get("card")
        if not card:
            continue
        
        ksm = (card.get("codes") or {}).get("ksm_code")
        qty = ctx.get_stock_quantity(ksm) if ctx else 0
        recommended = max(1, qty or 0) * multiplier
        
        result["components"].append({
            "ksm_code": ksm,
            "mtr_code": (card.get("codes") or {}).get("mtr_code"),
            "name": card.get("name"),
            "item_type": card.get("item_type"),
            "quantity": recommended,
            "status": f"рекомендуемый запас (x{multiplier})",
            "source_id": card.get("card_id"),
        })
    
    result["warnings"] = ["Расчёт — черновик: нормы запаса требуют утверждения"]
    result["review"] = True
    result["text"] = f"Рассчитано {len(result['components'])} позиций"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


@register_tool("maintenance_planner", "Черновик плана ТОиР")
def maintenance_planner(state: AgentState) -> Dict[str, Any]:
    """Черновик плана ТОиР"""
    start = time.time()
    result = _empty_result()
    
    targets = state.get("ksm_targets", [])
    
    for target in targets[:20]:
        comp = target.get("component", {})
        card = target.get("card")
        
        result["components"].append({
            "ksm_code": comp.get("ksm_code"),
            "mtr_code": (card.get("codes") or {}).get("mtr_code") if card else None,
            "name": card.get("name") if card else comp.get("designation"),
            "item_type": comp.get("item_type"),
            "status": "работа: обслуживание/проверка",
            "detail": f"участок {comp.get('unit_id')}",
            "source_id": comp.get("component_id"),
        })
        result["sources"].append(_source("object_graph", comp.get("component_id"), comp.get("unit_id")))
    
    result["warnings"] = ["Черновик: периодичность и состав работ утверждает служба ТОиР"]
    result["review"] = True
    result["text"] = f"Спланировано {len(result['components'])} работ"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


@register_tool("duplicate_detector", "Обнаружение дублей в каталоге")
def duplicate_detector(state: AgentState) -> Dict[str, Any]:
    """Обнаружение дублей в каталоге"""
    start = time.time()
    result = _empty_result()
    
    ctx = state.get("context", {}).get("repository")
    if not ctx:
        result["text"] = "Репозиторий не доступен"
        return result
    
    cards = ctx.get_catalog()
    groups = defaultdict(list)
    
    for card in cards:
        key = (
            card.get("item_type"),
            (card.get("properties", {}).get("dn") or {}).get("value"),
            (card.get("properties", {}).get("pn") or {}).get("value"),
            (card.get("properties", {}).get("wall_thickness") or {}).get("value"),
        )
        if all(k is not None for k in key):
            groups[key].append(card)
    
    dup_groups = [(k, v) for k, v in groups.items() if len(v) > 1]
    
    for key, items in dup_groups[:10]:
        dn, pn, wall = key[1], key[2], key[3]
        label = f"DN={dn}, PN={pn}, стенка={wall}"
        for card in items:
            result["components"].append({
                "ksm_code": (card.get("codes") or {}).get("ksm_code"),
                "mtr_code": (card.get("codes") or {}).get("mtr_code"),
                "name": card.get("name"),
                "item_type": card.get("item_type"),
                "status": "кандидат в дубль",
                "detail": label,
                "source_id": card.get("card_id"),
            })
    
    result["warnings"] = ["Совпадение параметров не доказывает дубль — нужен аудит экспертом"]
    result["review"] = True
    result["text"] = f"Найдено {len(dup_groups)} групп с одинаковыми параметрами"
    result["duration_ms"] = (time.time() - start) * 1000
    return result
