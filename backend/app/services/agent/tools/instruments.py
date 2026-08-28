# agent/tools/instruments.py
"""Инструменты ЭТАПА 3 (13 штук): search_catalog, get_component,
search_by_passport, check_stock, get_low_stock_items, get_unused_stock,
get_unit_structure, get_neighbors, is_installed_anywhere,
check_compatibility, check_compatibility_batch, search_norms,
get_component_history.

Шаблон Instrument (секция 3B), валидация по JSON Schema (3C),
ошибки ToolError (3D), карта интентов (3E), логирование вызовов (3F).
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from .errors import ToolError, ToolErrorCode
from .registry import register_instrument, set_intent_tools
from .tool_dal import BATCH_LIMIT, DEFAULT_LIMIT, ToolDAL
from .tool_log import get_tool_logger

# ===========================================================================
# Константы
# ===========================================================================

PASSPORT_WEIGHTS = {
    "dn": 0.30,
    "pn": 0.25,
    "material": 0.20,
    "angle": 0.15,
    "medium": 0.10,
}

PASSPORT_FIELD_TO_SEARCH = {
    "dn": "dn",
    "pn": "pn",
    "material": "steel_grade",
    "angle": "angle",
    "medium": "medium",
    "wall_thickness": "wall_thickness",
}

DETAIL_LEVEL = {"type": "string", "enum": ["basic", "with_stock", "full"], "default": "basic"}

PAGINATION = {
    "limit": {"type": "integer", "minimum": 1, "maximum": DEFAULT_LIMIT, "default": 20},
    "offset": {"type": "integer", "minimum": 0, "default": 0},
}


def _paginated(items: List[Any], total: int, offset: int, limit: int) -> Dict[str, Any]:
    return {
        "items": items,
        "total_count": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(items) < total,
    }


def _enhanced(dal: ToolDAL, card: Dict[str, Any], detail_level: str, score: float = 0.0) -> Dict[str, Any]:
    component = dal.to_component(card)
    component["match_score"] = score
    if detail_level == "basic":
        return component
    ksm = component["ksm_code"]
    stock = dal.to_stock_item(ksm, card) if ksm else None
    entry: Dict[str, Any] = {
        "component": component,
        "match_score": score,
        "stock": stock,
        "compatibility": None,
        "neighbors": [],
        "extracted_params": None,
        "warnings": [],
    }
    if detail_level == "full" and ksm:
        entry["neighbors"] = dal.get_neighbors(ksm, depth=1, direction="both")
    return entry


# ===========================================================================
# 3A.1 search_catalog
# ===========================================================================
SEARCH_CATALOG_INPUT = {
    "type": "object",
    "properties": {
        "params": {
            "type": "object",
            "properties": {
                "item_type": {"type": "string"},
                "dn": {"type": "integer", "minimum": 10, "maximum": 2000},
                "pn": {"type": "number", "minimum": 0.1},
                "angle": {"type": "integer", "minimum": 0, "maximum": 180},
                "wall_thickness": {"type": "number", "minimum": 0},
                "steel_grade": {"type": "string"},
                "medium": {"type": "string"},
                "climate": {"type": "string"},
                "gost_tu": {"type": "string"},
                "mtr_code": {"type": "string"},
                "ksm_code": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": DEFAULT_LIMIT, "default": 20},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
            "required": [],
        },
        "detail_level": DETAIL_LEVEL,
    },
    "required": ["params"],
}

SEARCH_CATALOG_OUTPUT = {
    "type": "object",
    "properties": {
        "items": {"type": "array"},
        "total_count": {"type": "integer"},
        "offset": {"type": "integer"},
        "limit": {"type": "integer"},
        "has_more": {"type": "boolean"},
    },
}


def execute_search_catalog(input: Dict[str, Any], dal: ToolDAL) -> Dict[str, Any]:
    params = input["params"]
    detail_level = input.get("detail_level", "basic")
    limit = params.get("limit", 20)
    offset = params.get("offset", 0)

    matches = dal.search_catalog(params)
    total = len(matches)
    page = matches[offset: offset + limit]

    items: List[Any] = []
    for i, m in enumerate(page):
        is_full_slot = detail_level == "full" and i < 20
        if detail_level in ("with_stock", "full") or is_full_slot:
            items.append(_enhanced(dal, m["card"], "full" if is_full_slot else "with_stock", m["score"]))
        else:
            items.append(_enhanced(dal, m["card"], "basic", m["score"]))

    return _paginated(items, total, offset, limit)


# ===========================================================================
# 3A.2 get_component
# ===========================================================================
GET_COMPONENT_INPUT = {
    "type": "object",
    "properties": {
        "identifier": {"type": "string", "minLength": 1},
        "detail_level": DETAIL_LEVEL,
    },
    "required": ["identifier"],
}


def execute_get_component(input: Dict[str, Any], dal: ToolDAL) -> Dict[str, Any]:
    identifier = input["identifier"]
    detail_level = input.get("detail_level", "basic")
    card = dal.get_component(identifier)
    if card is None:
        raise ToolError(ToolErrorCode.NOT_FOUND, f"Деталь {identifier} не найдена", {"identifier": identifier})
    return _enhanced(dal, card, detail_level)


def _passport_weights() -> Dict[str, float]:
    """Веса полей паспорта из БД (БД > дефолт кода)."""
    try:
        from ..rules.dynamic_rules import get_dynamic_rules

        return get_dynamic_rules().passport_weights()
    except Exception:  # noqa: BLE001
        return dict(PASSPORT_WEIGHTS)


def _passport_confidence_threshold() -> float:
    """Порог достоверности параметров паспорта из БД (БД > 0.6)."""
    try:
        from ..rules.dynamic_rules import get_dynamic_rules

        return get_dynamic_rules().passport_confidence_threshold()
    except Exception:  # noqa: BLE001
        return 0.6


# ===========================================================================
# 3A.3 search_by_passport
# ===========================================================================
SEARCH_BY_PASSPORT_INPUT = {
    "type": "object",
    "properties": {
        "document_id": {"type": "string", "minLength": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
    },
    "required": ["document_id"],
}


def execute_search_by_passport(input: Dict[str, Any], dal: ToolDAL) -> List[Dict[str, Any]]:
    document_id = input["document_id"]
    limit = input.get("limit", 5)

    pp = dal.get_passport_params(document_id)
    params = pp.get("params", {})
    if not params:
        raise ToolError(
            ToolErrorCode.NOT_FOUND,
            f"Паспорт {document_id} не найден или параметры не извлечены",
            {"document_id": document_id},
        )

    extracted = {k: v for k, v in params.items() if v.get("confidence", 0) > _passport_confidence_threshold()}
    weights = _passport_weights()
    total_weight = sum(weights[k] for k in extracted if k in weights)

    agg: Dict[str, Dict[str, Any]] = {}
    for field, meta in extracted.items():
        search_field = PASSPORT_FIELD_TO_SEARCH.get(field)
        if not search_field:
            continue
        search_params: Dict[str, Any] = {"limit": 10, search_field: meta["value"]}
        for match in dal.search_catalog(search_params):
            card = match["card"]
            ksm_code = (card.get("codes") or {}).get("ksm_code")
            if not ksm_code:
                continue
            entry = agg.setdefault(ksm_code, {
                "ksm_code": ksm_code,
                "mtr_code": (card.get("codes") or {}).get("mtr_code"),
                "name": card.get("name") or card.get("designation"),
                "matched": set(),
            })
            entry["matched"].add(field)

    suggestions: List[Dict[str, Any]] = []
    weights = _passport_weights()
    for ksm_code, entry in agg.items():
        hit_weight = sum(weights[f] for f in entry["matched"] if f in weights)
        confidence = round(hit_weight / total_weight, 3) if total_weight else 0.0
        suggestions.append({
            "ksm_code": ksm_code,
            "mtr_code": entry["mtr_code"],
            "name": entry["name"],
            "confidence": confidence,
            "matched_params": sorted(entry["matched"]),
        })

    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    return suggestions[:limit]


# ===========================================================================
# 3A.4 check_stock
# ===========================================================================
CHECK_STOCK_INPUT = {
    "type": "object",
    "properties": {
        "ksm_codes": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
    "required": ["ksm_codes"],
}


def execute_check_stock(input: Dict[str, Any], dal: ToolDAL) -> Dict[str, Dict[str, Any]]:
    ksm_codes = input["ksm_codes"]
    if not ksm_codes:
        return {}
    return dal.get_stock_batch(ksm_codes)


# ===========================================================================
# 3A.5 get_low_stock_items
# ===========================================================================
GET_LOW_STOCK_INPUT = {
    "type": "object",
    "properties": {
        "threshold": {"type": "number", "minimum": 0, "default": 2.0},
        "unit_code": {"type": "string"},
    },
    "required": [],
}


def execute_get_low_stock_items(input: Dict[str, Any], dal: ToolDAL) -> List[Dict[str, Any]]:
    threshold = input.get("threshold", 2.0)
    unit_code = input.get("unit_code")
    if not unit_code:
        return dal.get_low_stock_items(threshold)

    inventory = dal.get_unit_inventory(unit_code)
    ksm_codes = [e["component"].get("ksm_code") for e in inventory if e["component"].get("ksm_code")]
    stock = dal.get_stock_batch(ksm_codes)
    return [
        item for item in stock.values()
        if item["quantity"] is not None and item["quantity"] < threshold
    ]


# ===========================================================================
# 3A.6 get_unused_stock
# ===========================================================================
GET_UNUSED_STOCK_INPUT = {
    "type": "object",
    "properties": {
        "min_qty": {"type": "number", "minimum": 0, "default": 50.0},
    },
    "required": [],
}


def execute_get_unused_stock(input: Dict[str, Any], dal: ToolDAL) -> List[Dict[str, Any]]:
    min_qty = input.get("min_qty", 50.0)
    uninstalled = dal.get_uninstalled_components()
    stock = dal.get_stock_batch(uninstalled)
    return [item for item in stock.values() if item["quantity"] is not None and item["quantity"] > min_qty]


# ===========================================================================
# 3A.7 get_unit_structure
# ===========================================================================
GET_UNIT_STRUCTURE_INPUT = {
    "type": "object",
    "properties": {
        "unit_code": {"type": "string", "minLength": 1},
        "limit": {"type": "integer", "minimum": 1, "default": 20},
        "offset": {"type": "integer", "minimum": 0, "default": 0},
    },
    "required": ["unit_code"],
}


def execute_get_unit_structure(input: Dict[str, Any], dal: ToolDAL) -> Dict[str, Any]:
    unit_code = input["unit_code"]
    limit = min(input.get("limit", 20), DEFAULT_LIMIT)
    offset = input.get("offset", 0)

    inventory = dal.get_unit_inventory(unit_code)
    total = len(inventory)
    page = inventory[offset: offset + limit]
    return _paginated(page, total, offset, limit)


# ===========================================================================
# 3A.8 get_neighbors
# ===========================================================================
GET_NEIGHBORS_INPUT = {
    "type": "object",
    "properties": {
        "ksm_code": {"type": "string", "minLength": 1},
        "depth": {"type": "integer", "minimum": 1, "maximum": 5, "default": 1},
        "direction": {"type": "string", "enum": ["upstream", "downstream", "both"], "default": "both"},
    },
    "required": ["ksm_code"],
}


def execute_get_neighbors(input: Dict[str, Any], dal: ToolDAL) -> List[Dict[str, Any]]:
    return dal.get_neighbors(
        input["ksm_code"],
        depth=input.get("depth", 1),
        direction=input.get("direction", "both"),
    )


# ===========================================================================
# 3A.9 is_installed_anywhere
# ===========================================================================
IS_INSTALLED_INPUT = {
    "type": "object",
    "properties": {
        "ksm_code": {"type": "string", "minLength": 1},
    },
    "required": ["ksm_code"],
}


def execute_is_installed_anywhere(input: Dict[str, Any], dal: ToolDAL) -> bool:
    return dal.is_installed_anywhere(input["ksm_code"])


# ===========================================================================
# 3A.10 check_compatibility
# ===========================================================================
COMPATIBILITY_CONTEXT = {
    "type": "object",
    "properties": {
        "medium": {"type": "string", "minLength": 1},
        "pn": {"type": "number", "minimum": 0},
        "temperature": {"type": "number"},
        "climate": {"type": "string"},
        "has_coating": {"type": "boolean"},
        "gost_tu": {"type": "string"},
    },
    "required": ["medium", "pn"],
}

CHECK_COMPATIBILITY_INPUT = {
    "type": "object",
    "properties": {
        "ksm_code": {"type": "string", "minLength": 1},
        "context": COMPATIBILITY_CONTEXT,
    },
    "required": ["ksm_code", "context"],
}


def execute_check_compatibility(input: Dict[str, Any], dal: ToolDAL) -> Dict[str, Any]:
    ksm_code = input["ksm_code"]
    card = dal.get_component(ksm_code)
    if card is None:
        raise ToolError(ToolErrorCode.NOT_FOUND, f"Деталь с KSM {ksm_code} не найдена", {"ksm_code": ksm_code})
    return dal.check_compatibility(card, input["context"])


# ===========================================================================
# 3A.11 check_compatibility_batch
# ===========================================================================
CHECK_COMPATIBILITY_BATCH_INPUT = {
    "type": "object",
    "properties": {
        "ksm_codes": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
        "context": COMPATIBILITY_CONTEXT,
    },
    "required": ["ksm_codes", "context"],
}


def execute_check_compatibility_batch(input: Dict[str, Any], dal: ToolDAL) -> Dict[str, Dict[str, Any]]:
    ksm_codes = input["ksm_codes"]
    if len(ksm_codes) > BATCH_LIMIT:
        raise ToolError(
            ToolErrorCode.BATCH_TOO_LARGE,
            f"Слишком много деталей. Максимум {BATCH_LIMIT}",
            {"received": len(ksm_codes), "max": BATCH_LIMIT},
        )
    return dal.check_compatibility_batch(ksm_codes, input["context"])


# ===========================================================================
# 3A.12 search_norms
# ===========================================================================
SEARCH_NORMS_INPUT = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
        "document_type": {"type": "string", "enum": ["ЛНД", "ГОСТ", "ТУ"]},
    },
    "required": ["query"],
}


def execute_search_norms(input: Dict[str, Any], dal: ToolDAL) -> List[Dict[str, Any]]:
    return dal.search_norms(
        input["query"],
        limit=input.get("limit", 5),
        document_type=input.get("document_type"),
    )


# ===========================================================================
# 3A.13 get_component_history
# ===========================================================================
GET_HISTORY_INPUT = {
    "type": "object",
    "properties": {
        "ksm_code": {"type": "string", "minLength": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
        "offset": {"type": "integer", "minimum": 0, "default": 0},
    },
    "required": ["ksm_code"],
}


def execute_get_component_history(input: Dict[str, Any], dal: ToolDAL) -> Dict[str, Any]:
    ksm_code = input["ksm_code"]
    limit = input.get("limit", 10)
    offset = input.get("offset", 0)
    history = dal.get_component_history(ksm_code, limit=limit, offset=offset)
    return _paginated(history, len(history), offset, limit)


# ===========================================================================
# Карта интентов → инструменты (ЭТАП 3, секция 3E)
# ===========================================================================
INTENT_TOOLS: Dict[str, List[str]] = {
    "FIND_BY_CODE": ["get_component"],
    "FIND_BY_COMPONENT": ["get_component", "get_neighbors", "get_unit_structure"],
    "FIND_BY_PARAMS": ["search_catalog"],
    "COMPARE_DUPLICATES": ["search_catalog", "check_stock"],
    "CHECK_STOCK": ["check_stock"],
    "CHECK_MINIMUM_STOCK": ["get_unit_structure", "get_low_stock_items"],
    "LIST_OUT_OF_STOCK": ["get_unit_structure", "check_stock"],
    "FIND_UNUSED_STOCK": ["get_unused_stock"],
    "PLAN_REPAIR": ["get_unit_structure", "check_stock", "check_compatibility_batch"],
    "BUILD_REPAIR_KIT": ["get_neighbors", "check_stock", "get_component"],
    "FIND_ALTERNATIVE": ["search_catalog", "check_compatibility"],
    "REPLACE_WITH_COMPOSITE": ["search_catalog", "check_stock", "get_neighbors"],
    "REPLACE_WITH_DIFFERENT_SIZE": ["search_catalog", "check_compatibility"],
    "COMPARE_ALTERNATIVES": ["search_catalog", "check_compatibility", "check_stock"],
    "IMPACT_MEDIUM_CHANGE": ["get_unit_structure", "check_compatibility_batch"],
    "IMPACT_DIAMETER_CHANGE": ["get_unit_structure", "get_neighbors", "check_compatibility"],
    "IMPACT_MATERIAL_CHANGE": ["get_component", "check_compatibility"],
    "IMPACT_PRESSURE_CHANGE": ["get_component", "check_compatibility"],
    "ANALYZE_RISK": ["get_unit_structure", "check_compatibility_batch", "check_stock"],
    "EXPLAIN_TERM": ["get_component", "search_norms"],
    "EXPLAIN_DIFFERENCE": ["get_component", "check_compatibility"],
    "FIND_DOCUMENTS": ["get_component", "search_by_passport"],
    "FIND_STANDARDS": ["search_norms"],
    "GET_UNIT_STRUCTURE": ["get_unit_structure"],
}

set_intent_tools(INTENT_TOOLS)


# ===========================================================================
# Регистрация инструментов
# ===========================================================================
def _register_all() -> None:
    register_instrument(
        "search_catalog",
        "Поиск деталей в каталоге по параметрам",
        SEARCH_CATALOG_INPUT,
        SEARCH_CATALOG_OUTPUT,
        execute_search_catalog,
        required_intents=["FIND_BY_PARAMS", "COMPARE_DUPLICATES", "FIND_ALTERNATIVE",
                          "REPLACE_WITH_COMPOSITE", "REPLACE_WITH_DIFFERENT_SIZE",
                          "COMPARE_ALTERNATIVES"],
    )
    register_instrument(
        "get_component",
        "Получение детали по идентификатору (KSM, MTR или COMP-код)",
        GET_COMPONENT_INPUT,
        {"type": "object"},
        execute_get_component,
        required_intents=["FIND_BY_CODE", "FIND_BY_COMPONENT", "BUILD_REPAIR_KIT",
                          "IMPACT_MATERIAL_CHANGE", "IMPACT_PRESSURE_CHANGE", "EXPLAIN_TERM",
                          "EXPLAIN_DIFFERENCE", "FIND_DOCUMENTS"],
    )
    register_instrument(
        "search_by_passport",
        "Поиск деталей по параметрам, извлечённым из паспорта",
        SEARCH_BY_PASSPORT_INPUT,
        {"type": "array"},
        execute_search_by_passport,
        required_intents=["FIND_DOCUMENTS"],
    )
    register_instrument(
        "check_stock",
        "Проверка остатка по одному или нескольким KSM",
        CHECK_STOCK_INPUT,
        {"type": "object"},
        execute_check_stock,
        required_intents=["CHECK_STOCK", "COMPARE_DUPLICATES", "PLAN_REPAIR",
                          "BUILD_REPAIR_KIT", "REPLACE_WITH_COMPOSITE", "COMPARE_ALTERNATIVES",
                          "ANALYZE_RISK", "CHECK_MINIMUM_STOCK", "LIST_OUT_OF_STOCK"],
    )
    register_instrument(
        "get_low_stock_items",
        "Получение деталей с остатком ниже порога",
        GET_LOW_STOCK_INPUT,
        {"type": "array"},
        execute_get_low_stock_items,
        required_intents=["CHECK_MINIMUM_STOCK"],
    )
    register_instrument(
        "get_unused_stock",
        "Получение деталей с большим остатком, не установленных на участках",
        GET_UNUSED_STOCK_INPUT,
        {"type": "array"},
        execute_get_unused_stock,
        required_intents=["FIND_UNUSED_STOCK"],
    )
    register_instrument(
        "get_unit_structure",
        "Получение структуры участка с пагинацией",
        GET_UNIT_STRUCTURE_INPUT,
        {"type": "object"},
        execute_get_unit_structure,
        required_intents=["FIND_BY_COMPONENT", "CHECK_MINIMUM_STOCK", "LIST_OUT_OF_STOCK",
                          "PLAN_REPAIR", "IMPACT_MEDIUM_CHANGE", "IMPACT_DIAMETER_CHANGE",
                          "ANALYZE_RISK", "GET_UNIT_STRUCTURE"],
    )
    register_instrument(
        "get_neighbors",
        "Получение соседних компонентов для заданной детали",
        GET_NEIGHBORS_INPUT,
        {"type": "array"},
        execute_get_neighbors,
        required_intents=["FIND_BY_COMPONENT", "BUILD_REPAIR_KIT", "REPLACE_WITH_COMPOSITE",
                          "IMPACT_DIAMETER_CHANGE"],
    )
    register_instrument(
        "is_installed_anywhere",
        "Проверка, установлена ли деталь на каком-либо участке",
        IS_INSTALLED_INPUT,
        {"type": "boolean"},
        execute_is_installed_anywhere,
        required_intents=["FIND_UNUSED_STOCK"],
    )
    register_instrument(
        "check_compatibility",
        "Проверка совместимости детали с условиями эксплуатации",
        CHECK_COMPATIBILITY_INPUT,
        {"type": "object"},
        execute_check_compatibility,
        required_intents=["FIND_ALTERNATIVE", "REPLACE_WITH_DIFFERENT_SIZE", "COMPARE_ALTERNATIVES",
                          "IMPACT_DIAMETER_CHANGE", "IMPACT_MATERIAL_CHANGE", "IMPACT_PRESSURE_CHANGE",
                          "EXPLAIN_DIFFERENCE"],
    )
    register_instrument(
        "check_compatibility_batch",
        "Проверка совместимости для списка деталей",
        CHECK_COMPATIBILITY_BATCH_INPUT,
        {"type": "object"},
        execute_check_compatibility_batch,
        required_intents=["PLAN_REPAIR", "IMPACT_MEDIUM_CHANGE", "ANALYZE_RISK"],
    )
    register_instrument(
        "search_norms",
        "Поиск в нормативной базе (ЛНД, ГОСТ, ТУ)",
        SEARCH_NORMS_INPUT,
        {"type": "array"},
        execute_search_norms,
        required_intents=["EXPLAIN_TERM", "FIND_STANDARDS"],
    )
    register_instrument(
        "get_component_history",
        "Получение истории изменений атрибутов детали",
        GET_HISTORY_INPUT,
        {"type": "object"},
        execute_get_component_history,
        required_intents=[],
    )


_register_all()


# ===========================================================================
# Исполнение инструмента (точка входа для оркестратора и LLM-режима)
# ===========================================================================
def run_instrument(
    name: str,
    input: Dict[str, Any],
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    dal: Optional[ToolDAL] = None,
) -> Dict[str, Any]:
    """Выполняет инструмент: валидация → исполнение → логирование.

    Возвращает {'tool': name, 'result': ..., 'error': None} либо
    {'tool': name, 'result': None, 'error': {'code': ..., 'message': ...}}.
    """
    from .registry import get_instrument

    instrument = get_instrument(name)
    if instrument is None:
        raise ToolError(ToolErrorCode.TOOL_NOT_FOUND, f"Инструмент {name} не найден", {"tool": name})

    start = time.time()
    request_id = request_id or str(uuid.uuid4())
    error: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None

    try:
        instrument["validate_input"](input or {})
        _dal = dal or _default_dal()
        result = instrument["execute"](input or {}, _dal)
        output = result if isinstance(result, dict) else {"value": result}
    except ToolError as e:
        error = e.to_dict()
    except Exception as e:  # noqa: BLE001
        error = ToolError(ToolErrorCode.DAL_ERROR, str(e), {"tool": name}).to_dict()

    duration_ms = int((time.time() - start) * 1000)
    logger = get_tool_logger()
    logger.record(
        tool_name=name,
        input_data=input or {},
        duration_ms=duration_ms,
        output_data=output,
        error=error,
        request_id=request_id,
        user_id=user_id,
    )

    if error:
        return {"tool": name, "result": None, "error": error, "duration_ms": duration_ms}
    return {"tool": name, "result": output, "error": None, "duration_ms": duration_ms}


_dal_singleton: Optional[ToolDAL] = None


def _default_dal() -> ToolDAL:
    global _dal_singleton
    if _dal_singleton is None:
        from app.services.agent.repository.repository_factory import get_repository

        _dal_singleton = ToolDAL(get_repository())
    return _dal_singleton


def reset_tool_dal() -> None:
    global _dal_singleton
    _dal_singleton = None