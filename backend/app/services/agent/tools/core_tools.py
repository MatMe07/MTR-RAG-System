# agent/tools/core_tools.py

from typing import Any, Dict, List, Optional
import time

from .registry import register_tool
from ..core.state import AgentState


def _empty_result() -> Dict[str, Any]:
    return {
        "text": "",
        "components": [],
        "warnings": [],
        "sources": [],
        "missing": [],
        "review": False,
        "error": None,
    }


def _source(kind: str, id: str, fragment: str = None) -> Dict[str, Any]:
    return {"kind": kind, "id": id, "fragment": fragment}


def _card_component(card: Dict, score: float = 0.0, reason: str = "") -> Dict[str, Any]:
    codes = card.get("codes", {})
    props = card.get("properties", {})
    return {
        "mtr_code": codes.get("mtr_code"),
        "ksm_code": codes.get("ksm_code"),
        "name": card.get("name") or card.get("designation"),
        "item_type": card.get("item_type"),
        "quantity": (props.get("stock_qty") or {}).get("value"),
        "status": reason or f"score={score:.0%}",
        "detail": "",
        "source_id": card.get("card_id"),
    }


def catalog_search(state: AgentState, ctx) -> Dict[str, Any]:
    """Поиск в каталоге"""
    start = time.time()
    result = _empty_result()
    
    if not ctx:
        result["text"] = "Репозиторий не доступен"
        result["error"] = "repository_not_available"
        return result
    
    parsed = state["parsed"]
    matches = []
    
    for card in ctx.get_catalog():
        if _matches_filters(card, parsed):
            score = _match_score(card, parsed)
            matches.append({"card": card, "score": score})
    
    matches.sort(key=lambda x: x["score"], reverse=True)
    candidates = matches[:40]
    
    for m in candidates:
        card = m["card"]
        result["components"].append(_card_component(card, m["score"], "совпадает по параметрам"))
        result["sources"].append(_source("catalog", card.get("card_id"), card.get("designation")))
    
    state["candidates"] = candidates
    result["text"] = f"Найдено {len(candidates)} позиций"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


def stock_query(state: AgentState, ctx) -> Dict[str, Any]:
    """Проверка остатков на складе"""
    start = time.time()
    result = _empty_result()
    
    if not ctx:
        result["text"] = "Репозиторий не доступен"
        return result
    
    candidates = state.get("candidates", [])
    
    for item in candidates:
        card = item.get("card")
        if not card:
            continue
        
        ksm = (card.get("codes") or {}).get("ksm_code")
        qty = ctx.get_stock_quantity(ksm) if ksm else None
        
        if qty is not None and qty > 0:
            status = f"на складе: {qty}"
        else:
            status = "нет на складе"
            result["warnings"].append(f"Для {card.get('name')} нет остатков")
        
        result["components"].append({
            "ksm_code": ksm,
            "mtr_code": (card.get("codes") or {}).get("mtr_code"),
            "name": card.get("name"),
            "item_type": card.get("item_type"),
            "quantity": qty or 0,
            "status": status,
            "source_id": card.get("card_id"),
        })
        result["sources"].append(_source("stock", ksm, f"остаток: {qty or 0}"))
    
    state["stock_rows"] = result["components"]
    result["text"] = f"Проверено {len(candidates)} позиций"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


def rules_engine(state: AgentState) -> Dict[str, Any]:
    """Применение правил матчинга"""
    start = time.time()
    result = _empty_result()
    
    candidates = state.get("candidates", [])
    
    for item in candidates:
        card = item.get("card")
        if not card:
            continue
        
        score = _match_score(card, state["parsed"])
        item["score"] = score
        result["components"].append(_card_component(card, score, "оценка правил"))
    
    result["sources"].append(_source("matching_rules", "matching_rules.csv"))
    result["text"] = f"Оценено {len(candidates)} кандидатов"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


def graph_search(state: AgentState, ctx) -> Dict[str, Any]:
    """Поиск в графе объекта"""
    start = time.time()
    result = _empty_result()
    
    if not ctx:
        result["text"] = "Репозиторий не доступен"
        return result
    
    parsed = state["parsed"]
    unit_ids = getattr(parsed, "unit_ids", [])
    component_ids = getattr(parsed, "component_ids", [])
    
    if not unit_ids and not component_ids:
        result["text"] = "Не указаны участки или компоненты"
        result["missing"] = ["unit_ids", "component_ids"]
        return result
    
    components = []
    for uid in unit_ids:
        components.extend(ctx.get_components_by_unit(uid))
    for cid in component_ids:
        graph = ctx.get_graph()
        for comp in graph.get("components", []):
            if comp.get("component_id") == cid:
                components.append(comp)
                break
    
    targets = []
    for comp in components:
        ksm = comp.get("ksm_code")
        card = ctx.get_card_by_ksm(ksm) if ksm else None
        
        if card:
            targets.append({"ksm": ksm, "component": comp, "card": card})
            result["components"].append({
                "ksm_code": ksm,
                "mtr_code": (card.get("codes") or {}).get("mtr_code"),
                "name": card.get("name") or comp.get("designation"),
                "item_type": comp.get("item_type"),
                "status": f"установлен на {comp.get('unit_id')}",
                "source_id": comp.get("component_id"),
            })
            result["sources"].append(_source("object_graph", comp.get("component_id"), comp.get("unit_id")))
    
    state["ksm_targets"] = targets
    result["text"] = f"Найдено {len(components)} компонентов"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


def regulation_lookup(state: AgentState, ctx) -> Dict[str, Any]:
    """Проверка нормативных требований"""
    start = time.time()
    result = _empty_result()
    
    if not ctx:
        result["text"] = "Репозиторий не доступен"
        return result
    
    reg = ctx.get_regulation()
    
    for limitation in reg.get("important_limitations", [])[:3]:
        result["warnings"].append(limitation)
    
    result["sources"].append(_source("regulation", "regulation_matrix.json"))
    result["text"] = f"Проверено {len(result['warnings'])} нормативов"
    result["duration_ms"] = (time.time() - start) * 1000
    return result


def _matches_filters(card: Dict, parsed: Any) -> bool:
    props = card.get("properties", {})
    tf = getattr(parsed, "technical_filters", {}) or {}
    
    def num(key):
        v = (props.get(key) or {}).get("value")
        return v if isinstance(v, (int, float)) else None
    
    if tf.get("dn") and num("dn"):
        if abs(num("dn") - tf["dn"]) > tf["dn"] * 0.1:
            return False
    
    if tf.get("angle") and num("angle"):
        if abs(num("angle") - tf["angle"]) > 0:
            return False
    
    if tf.get("wall_thickness") and num("wall_thickness"):
        if abs(num("wall_thickness") - tf["wall_thickness"]) > tf["wall_thickness"] * 0.15:
            return False
    
    item_types = getattr(parsed, "item_types", [])
    if item_types and card.get("item_type") not in item_types:
        return False
    
    return True


def _match_score(card: Dict, parsed: Any) -> float:
    props = card.get("properties", {})
    tf = getattr(parsed, "technical_filters", {}) or {}
    
    def num(key):
        v = (props.get(key) or {}).get("value")
        return v if isinstance(v, (int, float)) else None
    
    hits = 0.0
    checks = 0.0
    
    for key in ["dn", "angle", "wall_thickness"]:
        want = tf.get(key)
        if want is not None:
            checks += 1
            got = num(key)
            if got is not None and abs(got - want) <= want * 0.1:
                hits += 1
    
    item_types = getattr(parsed, "item_types", [])
    if item_types:
        checks += 1
        if card.get("item_type") in item_types:
            hits += 1
    
    return hits / checks if checks > 0 else 0.5
