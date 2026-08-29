# agent/tools/core_tools.py

import logging
from typing import Any, Dict, List, Optional
import time

from .registry import register_tool
from ..core.state import AgentState
from ..answer.status import evaluate_candidate, candidate_tz_status

log = logging.getLogger("mtr.agent.tools")


def _matching_tolerances() -> Dict[str, float]:
    """Допуски матчинга из БД (БД > дефолт кода)."""
    try:
        from ..rules.dynamic_rules import get_dynamic_rules

        return get_dynamic_rules().matching_tolerances()
    except Exception:  # noqa: BLE001
        return {"dn": 0.1, "angle": 0.0, "wall_thickness": 0.15, "default": 0.1}


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


def _enrich_component(comp: Dict[str, Any], card: Dict, score: float, parsed: Any) -> Dict[str, Any]:
    """Добавляет ТЗ-метаданные кандидата (ЭТАП 5)."""
    matched, mismatched, missing = evaluate_candidate(card, parsed)
    percent = round(score * 100)
    comp["match_score"] = score
    comp["match_percent"] = percent
    comp["matched_params"] = matched
    comp["mismatched_params"] = mismatched
    comp["missing_params"] = missing
    comp["tz_status"] = candidate_tz_status(percent)
    return comp


def catalog_search(state: AgentState, ctx) -> Dict[str, Any]:
    """Поиск в каталоге"""
    start = time.time()
    result = _empty_result()

    if not ctx:
        result["text"] = "Репозиторий не доступен"
        result["error"] = {"code": "DAL_ERROR", "message": "Репозиторий не доступен"}
        log.warning("[catalog_search] Repository not available")
        return result

    parsed = state["parsed"]
    matches = []

    catalog = ctx.get_catalog()
    log.info("[catalog_search] Loaded %d cards from repository", len(catalog))

    for card in catalog:
        if _matches_filters(card, parsed):
            score = _match_score(card, parsed)
            matches.append({"card": card, "score": score})

    matches.sort(key=lambda x: x["score"], reverse=True)
    candidates = matches[:40]

    for m in candidates:
        card = m["card"]
        comp = _enrich_component(
            _card_component(card, m["score"], "совпадает по параметрам"),
            card, m["score"], parsed,
        )
        result["components"].append(comp)
        result["sources"].append(_source("catalog", card.get("card_id"), card.get("designation")))

    state["candidates"] = candidates
    result["text"] = f"Найдено {len(candidates)} позиций"
    result["duration_ms"] = (time.time() - start) * 1000
    log.info("[catalog_search] Found %d candidates (from %d cards) in %.0fms",
        len(candidates), len(catalog), result["duration_ms"])
    return result


def stock_query(state: AgentState, ctx) -> Dict[str, Any]:
    """Проверка остатков на складе"""
    start = time.time()
    result = _empty_result()

    if not ctx:
        result["text"] = "Репозиторий не доступен"
        result["error"] = {"code": "DAL_ERROR", "message": "Репозиторий не доступен"}
        log.warning("[stock_query] Repository not available")
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
    log.info("[stock_query] Checked %d items in %.0fms", len(candidates), result["duration_ms"])
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
        result["components"].append(
            _enrich_component(
                _card_component(card, score, "оценка правил"),
                card, score, state["parsed"],
            )
        )

    result["sources"].append(_source("matching_rules", "matching_rules.csv"))
    result["text"] = f"Оценено {len(candidates)} кандидатов"
    result["duration_ms"] = (time.time() - start) * 1000
    log.info("[rules_engine] Scored %d candidates in %.0fms", len(candidates), result["duration_ms"])
    return result


def graph_search(state: AgentState, ctx) -> Dict[str, Any]:
    """Поиск в графе объекта"""
    start = time.time()
    result = _empty_result()

    if not ctx:
        result["text"] = "Репозиторий не доступен"
        result["error"] = {"code": "DAL_ERROR", "message": "Репозиторий не доступен"}
        log.warning("[graph_search] Repository not available")
        return result

    parsed = state["parsed"]
    unit_ids = getattr(parsed, "unit_ids", [])
    component_ids = getattr(parsed, "component_ids", [])

    if not unit_ids and not component_ids:
        result["text"] = "Не указаны участки или компоненты"
        result["missing"] = ["unit_ids", "component_ids"]
        log.info("[graph_search] No unit_ids or component_ids provided")
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
    log.info("[graph_search] Found %d components, %d targets in %.0fms",
        len(components), len(targets), result["duration_ms"])
    return result


def regulation_lookup(state: AgentState, ctx) -> Dict[str, Any]:
    """Проверка нормативных требований"""
    start = time.time()
    result = _empty_result()

    if not ctx:
        result["text"] = "Репозиторий не доступен"
        result["error"] = {"code": "DAL_ERROR", "message": "Репозиторий не доступен"}
        log.warning("[regulation_lookup] Repository not available")
        return result

    reg = ctx.get_regulation()

    for limitation in reg.get("important_limitations", [])[:3]:
        result["warnings"].append(limitation)

    result["sources"].append(_source("regulation", "regulation_matrix.json"))
    result["text"] = f"Проверено {len(result['warnings'])} нормативов"
    result["duration_ms"] = (time.time() - start) * 1000
    log.info("[regulation_lookup] Checked %d regulations in %.0fms",
        len(result["warnings"]), result["duration_ms"])
    return result


def _matches_filters(card: Dict, parsed: Any) -> bool:
    props = card.get("properties", {})
    tf = getattr(parsed, "technical_filters", {}) or {}

    def num(key):
        v = (props.get(key) or {}).get("value")
        return v if isinstance(v, (int, float)) else None

    def tol(key: str) -> float:
        tolerances = _matching_tolerances()
        return tolerances.get(key, tolerances.get("default", 0.1))

    if tf.get("dn") and num("dn"):
        if abs(num("dn") - tf["dn"]) > abs(tf["dn"]) * tol("dn"):
            return False

    if tf.get("angle") and num("angle"):
        if abs(num("angle") - tf["angle"]) > abs(tf["angle"]) * tol("angle"):
            return False

    if tf.get("wall_thickness") and num("wall_thickness"):
        if abs(num("wall_thickness") - tf["wall_thickness"]) > abs(tf["wall_thickness"]) * tol("wall_thickness"):
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

    tolerances = _matching_tolerances()
    default_tol = tolerances.get("default", 0.1)

    for key in ["dn", "angle", "wall_thickness", "pn"]:
        want = tf.get(key)
        if want is not None:
            checks += 1
            got = num(key)
            tol = tolerances.get(key, default_tol)
            if got is not None and abs(got - want) <= max(abs(want), 1e-9) * tol:
                hits += 1

    item_types = getattr(parsed, "item_types", [])
    if item_types:
        checks += 1
        if card.get("item_type") in item_types:
            hits += 1

    return hits / checks if checks > 0 else 0.5
