# agent/intent/detect.py

"""Детекция гранулярных интентов, фильтрация параметров и статуса запроса.

Реализация §1B (детекция/приоритеты), §1H.1 (filter_params_for_intent),
§1H.4 (статус), §1H.2 (несовместимость).
"""

import re
from typing import Any, Dict, List, Tuple

from .matrix import INTENT_ORDER, INTENT_REQUIREMENTS, INCOMPATIBLE_INTENTS
from ..parsing.utils.replacement_utils import has_explicit_dn_replacement

PARSED_STATUS_COMPLETE = "COMPLETE"
PARSED_STATUS_PARTIAL = "PARTIAL"
PARSED_STATUS_REQUIRES_EXPERT = "REQUIRES_EXPERT"
PARSED_STATUS_UNCLEAR = "UNCLEAR"

_CODE_RE = re.compile(r"\b(MTR|KSM)[-\w]*", re.IGNORECASE)
_PN_CHANGE_RE = re.compile(r"pn\s*(\d+)[\w\s]{0,25}(?:вместо|на)\s*(?:pn\s*)?(\d+)", re.IGNORECASE)
_STOP_WORDS = {
    "какой", "какая", "какие", "найди", "найти", "подбери", "подобрать",
    "замени", "заменить", "помоги", "нужно", "нужна", "для", "деталь",
    "изделия", "нужна", "выдать", "покажи", "дай", "и", "мне", "задвижку",
    "приемлемо", "пожалуйста", "расскажи", "объясни",
}


def _codes(parsed: Any) -> List[str]:
    return [m.group(0).upper() for m in _CODE_RE.finditer(parsed.original_query or "")]


def _has_op(parsed: Any, *ops: str) -> bool:
    return any(op in (getattr(parsed, "operations", []) or []) for op in ops)


def _q(parsed: Any) -> str:
    return (parsed.original_query or "").lower()


def _tf(parsed: Any, key: str) -> Any:
    return (getattr(parsed, "technical_filters", {}) or {}).get(key)


def _changes(parsed: Any) -> Dict[str, Any]:
    return getattr(parsed, "proposed_changes", {}) or {}


def _explain_terms(parsed: Any) -> Tuple[str, str]:
    q = parsed.original_query or ""
    # «чем отличается переход от отвода» и «чем переход отличается от отвода»
    m = re.search(
        r"чем\s+отличается\s+([а-яёa-z0-9-]+)\s+(?:от|и)\s+([а-яёa-z0-9-]+)"
        r"|чем\s+([а-яёa-z0-9-]+)\s+отличается\s+(?:от|и)\s+([а-яёa-z0-9-]+)",
        q, re.IGNORECASE,
    )
    if m:
        g = m.groups()
        return (g[0] or g[2]) or "", (g[1] or g[3]) or ""
    tokens = re.findall(r"[а-яёa-z0-9-]{3,}", _q(parsed), re.IGNORECASE)
    candidates = [t for t in tokens if t not in _STOP_WORDS]
    if candidates:
        return candidates[0], ""
    return "", ""


# ------------------------------------------------------------- детекция
def _det_FIND_BY_CODE(parsed):
    return bool(_codes(parsed) and not _has_op(parsed, "repair", "replace"))


def _det_FIND_BY_COMPONENT(parsed):
    return bool(getattr(parsed, "component_ids", None))


def _det_FIND_BY_PARAMS(parsed):
    return bool(getattr(parsed, "item_types", None)) and (
        _tf(parsed, "dn") is not None or _tf(parsed, "material")
    )


def _det_COMPARE_DUPLICATES(parsed):
    return "дубл" in _q(parsed) or "duplicates" in (getattr(parsed, "operations", []) or [])


def _det_FIND_ALTERNATIVE(parsed):
    if has_explicit_dn_replacement(parsed.original_query or ""):
        return False
    return _has_op(parsed, "replace") and bool(getattr(parsed, "item_types", None)) and (
        _tf(parsed, "dn") is not None or _tf(parsed, "pn") is not None
    )


def _det_REPLACE_WITH_DIFFERENT_SIZE(parsed):
    ch = _changes(parsed)
    return bool(ch.get("dn_from") is not None and ch.get("dn_to") is not None)


def _det_REPLACE_WITH_COMPOSITE(parsed):
    return any(w in _q(parsed) for w in ("составн", "композит", "составной"))


def _det_COMPARE_ALTERNATIVES(parsed):
    return any(w in _q(parsed) for w in ("сравни", "сравнить", "compare"))


def _det_CHECK_STOCK(parsed):
    kw = ("наличие", "остат", "проверь склад", "stock")
    return any(w in _q(parsed) for w in kw) or _has_op(parsed, "inventory", "check")


def _det_CHECK_MINIMUM_STOCK(parsed):
    return _det_CHECK_STOCK(parsed) and any(w in _q(parsed) for w in ("минимум", " мин ", "ниже"))


def _det_CHECK_SUFFICIENCY(parsed):
    uc = getattr(parsed, "units_count", None)
    if not uc:
        return False
    return any(w in _q(parsed) for w in (
        "хватит", "хватает", "достаточн", "по ", "штук",
        "sufficien", "enough",
    ))


def _det_LIST_OUT_OF_STOCK(parsed):
    if getattr(parsed, "on_stock", None) is False:
        return True
    return any(w in _q(parsed) for w in ("нет в наличии", "отсутств", "не в наличии"))


def _det_FIND_UNUSED_STOCK(parsed):
    return bool(getattr(parsed, "not_installed", None)) or any(
        w in _q(parsed) for w in ("не используется", "не установлен", "залежал", "unused")
    )


def _det_PLAN_REPAIR(parsed):
    return _has_op(parsed, "repair") or any(
        w in _q(parsed) for w in (
            "ремонт", "почини", "план", "обслужив",
            "порядок работ", "запчаст", "перечисли",
        )
    )


def _det_ADD_COMPONENT(parsed):
    # «добавь деталь/укомплектуй участок» — конфигурация объекта,
    # даже если параллельно указана «замена» текущей детали.
    if not _has_op(parsed, "assemble"):
        return False
    return any(w in _q(parsed) for w in ("добавь", "добавить", "дополни", "укомплектуй", "перекрыти"))


def _det_BUILD_REPAIR_KIT(parsed):
    return "ремкомплект" in _q(parsed)


def _det_REPAIR_WITH_CHECKS(parsed):
    # «Проверить ремонт/замену с учётом среды» (1B.3): контекст ремонта +
    # цель (component/unit) + известная среда (medium).
    if not _has_op(parsed, "repair"):
        return False
    has_target = bool(getattr(parsed, "component_ids", None)) or bool(getattr(parsed, "unit_ids", None))
    return has_target and _tf(parsed, "medium") is not None


def _det_IMPACT_MEDIUM_CHANGE(parsed):
    return bool(_changes(parsed).get("medium"))


def _det_IMPACT_DIAMETER_CHANGE(parsed):
    ch = _changes(parsed)
    return ch.get("dn_from") is not None or ch.get("dn_to") is not None


def _det_IMPACT_MATERIAL_CHANGE(parsed):
    ch = _changes(parsed)
    return bool(ch.get("material_from") or ch.get("material_to") or ch.get("strength_to"))


def _det_IMPACT_PRESSURE_CHANGE(parsed):
    return bool(_PN_CHANGE_RE.search(parsed.original_query or ""))


def _det_ANALYZE_RISK(parsed):
    return any(w in _q(parsed) for w in ("анализ", "риск", "оценка влияния", "оцени")) and (
        bool(getattr(parsed, "unit_ids", None)) or _tf(parsed, "medium")
    )


def _det_EXPLAIN_TERM(parsed):
    return any(w in _q(parsed) for w in ("что значит", "объясни", "расскажи про", "explain"))


def _det_EXPLAIN_DIFFERENCE(parsed):
    # «чем переход отличается от отвода» — подстрока «чем отличается» тут не
    # совпадает, поэтому срабатываем по «отличается от» / «отличаются».
    return any(w in _q(parsed) for w in ("чем отличается", "отличается от", "отличаются", "разница", "отличия"))


def _det_FIND_DOCUMENTS(parsed):
    return any(w in _q(parsed) for w in ("паспорт", "документ"))


def _det_FIND_STANDARDS(parsed):
    refs = [r for r in (getattr(parsed, "references", []) or [])
            if re.match(r"(ГОСТ|ТУ|ОСТ|НД|СТО|РД)[\s\d]", str(r), re.IGNORECASE)]
    if refs:
        return True
    return any(w in _q(parsed) for w in ("гост", " ту ", "норматив", "стандарт"))


def _det_GET_UNIT_STRUCTURE(parsed):
    return bool(getattr(parsed, "unit_ids", None)) and any(
        w in _q(parsed) for w in ("из чего состоит", "состав участка", "схема", "структур")
    )


def detect_intents(parsed: Any, max_intents: int = 5) -> List[str]:
    """Гранулярные интенты в порядке приоритета (§1B.8/1B.9).

    Первым — «главный»: явный глагол действия (replace/repair/impact/explain)
    поднимается выше «поисковых».
    """
    detected = []
    for name in INTENT_ORDER:
        fn = globals().get(f"_det_{name}")
        if fn and fn(parsed):
            detected.append(name)
    if not detected:
        return []

    primary_group = None
    if any(w in _q(parsed) for w in ("замени", "замен", "подбери замен")) and _has_op(parsed, "replace"):
        primary_group = "FIND_ALTERNATIVE"
    elif _has_op(parsed, "repair"):
        primary_group = "PLAN_REPAIR"
    elif any(w in _q(parsed) for w in ("чем отличается", "разница")):
        primary_group = "EXPLAIN_DIFFERENCE"

    if primary_group and primary_group in detected:
        detected.remove(primary_group)
        detected.insert(0, primary_group)

    return detected[: max_intents]


# ------------------------------------------------------- параметры (1D-объединение)
def params_from_parsed(parsed: Any) -> Dict[str, Any]:
    """Единый словарь параметров запроса (аналог 1H 'params')."""
    p: Dict[str, Any] = {}
    tf = getattr(parsed, "technical_filters", {}) or {}
    ch = _changes(parsed)

    if getattr(parsed, "item_types", None):
        p["item_type"] = parsed.item_types[0]
    for key in ("dn", "pn", "angle", "wall_thickness", "medium",
                "material", "climate", "gost_tu", "strength_class"):
        if tf.get(key) is not None:
            p[key] = tf[key]

    if getattr(parsed, "component_ids", None):
        p["component_id"] = parsed.component_ids[0]
    else:
        mtr_ksm = [c for c in _codes(parsed) if c.startswith("MTR") or c.startswith("KSM")]
        if mtr_ksm:
            p["mtr_code" if mtr_ksm[0].startswith("MTR") else "ksm_code"] = mtr_ksm[0]
    if getattr(parsed, "unit_ids", None):
        p["unit_id"] = parsed.unit_ids[0]

    # Изменения: old_x / new_x
    change_map = {
        "dn_from": "old_dn", "dn_to": "new_dn",
        "material_from": "old_material", "material_to": "new_material",
        "strength_from": "old_material", "strength_to": "new_material",
    }
    for src, dst in change_map.items():
        if ch.get(src) is not None:
            p[dst] = ch[src]
    if ch.get("medium"):
        p["new_medium"] = ch["medium"]

    if getattr(parsed, "units_count", None) is not None:
        p["units_count"] = parsed.units_count

    pn_m = _PN_CHANGE_RE.search(parsed.original_query or "")
    if pn_m:
        p["old_pn"] = float(pn_m.group(1))
        p["new_pn"] = float(pn_m.group(2))

    refs = getattr(parsed, "references", []) or []
    if refs and not p.get("gost_tu"):
        p["gost_tu"] = refs[0]

    # Значения по умолчанию из §1C
    p.setdefault("min_stock", 50)
    p.setdefault("quantity", 2)
    p.setdefault("top_n", getattr(parsed, "limit", None) or 5)

    if _det_EXPLAIN_TERM(parsed) or _det_EXPLAIN_DIFFERENCE(parsed):
        t1, t2 = _explain_terms(parsed)
        if t1:
            p["term"] = t1
        if t1 and t2:
            p["term1"], p["term2"] = t1, t2

    return p


def filter_params_for_intent(params: Dict[str, Any], intent: str) -> Dict[str, Any]:
    """§1H.1: оставляет только параметры required+optional для интента."""
    req = INTENT_REQUIREMENTS.get(intent, {})
    allowed = set(req.get("optional", []))
    for group in req.get("required", []):
        allowed.update(group)
    return {k: v for k, v in (params or {}).items() if k in allowed}


def missing_required_for_intent(parsed: Any, intent: str) -> List[str]:
    """Недостающие обязательные параметры интента (пустой список = выполним)."""
    params = params_from_parsed(parsed)
    groups = INTENT_REQUIREMENTS.get(intent, {}).get("required", [])
    for group in groups:
        absent = [k for k in group if params.get(k) is None]
        if not absent:
            return []
    if not groups:
        return []
    first = groups[0]
    return [k for k in first if params.get(k) is None]


def incompatible_detected(intents: List[str]) -> List[str]:
    """§1H.2: возвращает причины несовместимости (иначе пустой список)."""
    reasons = []
    intents = list(intents or [])
    for a, bs in INCOMPATIBLE_INTENTS.items():
        if a in intents:
            for b in bs:
                if b in intents:
                    reasons.append(f"{a} / {b}")
    return reasons


def determine_parsed_status(
    parsed: Any,
    intents: List[str],
) -> str:
    """§1H.4: COMPLETE / PARTIAL / REQUIRES_EXPERT / UNCLEAR."""
    if not intents:
        return PARSED_STATUS_UNCLEAR
    missing = {
        it: missing_required_for_intent(parsed, it) for it in intents
    }
    primary = intents[0]
    if not missing[primary]:
        return PARSED_STATUS_COMPLETE
    if any(not v for v in missing.values()):
        return PARSED_STATUS_PARTIAL
    return PARSED_STATUS_REQUIRES_EXPERT


def _apply_extracted(parsed: Any, data: Dict[str, Any]) -> None:
    """Применяет доизвлечённые LLM-параметры к ParsedQuery (§1F).

    Мутирует только незаполненные поля; существующие значения не трогает.
    """
    tf = dict(getattr(parsed, "technical_filters", None) or {})
    filter_keys = {"dn", "pn", "angle", "wall_thickness", "medium", "material",
                   "steel_grade", "climate", "gost_tu", "strength_class", "d1", "d2"}
    for key, value in data.items():
        if key in filter_keys:
            if tf.get(key) is None:
                tf[key] = value
        elif key == "item_type":
            items = list(getattr(parsed, "item_types", None) or [])
            if not items:
                items = [value]
            elif value not in items:
                items.insert(0, value)
            object.__setattr__(parsed, "item_types", items)
            if tf.get("item_type") is None:
                tf["item_type"] = items[0]
        elif key == "unit_id":
            ids = list(getattr(parsed, "unit_ids", None) or [])
            if value not in ids:
                ids.append(value)
                object.__setattr__(parsed, "unit_ids", ids)
        elif key == "component_id":
            ids = list(getattr(parsed, "component_ids", None) or [])
            if value not in ids:
                ids.append(value)
                object.__setattr__(parsed, "component_ids", ids)
        elif key in ("units_count", "quantity"):
            if getattr(parsed, key, None) is None:
                object.__setattr__(parsed, key, int(value))
    object.__setattr__(parsed, "technical_filters", tf)


def _llm_extract(parsed: Any, intents: List[str]) -> List[str]:
    """§1F: LLM-доизвлечение недостающих параметров после rule-парсеров.

    Выполняется один раз (флаг _llm_extracted). Работает в двух случаях:
    - интент определён, но есть непокрытые required-параметры;
    - интентов нет, но тип детали есть («отвод» без DN/давления) —
      доизвлекаем поисковые параметры под FIND_BY_PARAMS.

    parse_safe: не бросает исключений.
    Возвращает актуальный список интентов (мог измениться после дополнения).
    """
    if getattr(parsed, "_llm_extracted", False):
        return intents
    primary = intents[0] if intents else None
    if not primary:
        if not getattr(parsed, "item_types", None):
            return intents
        intent = "FIND_BY_PARAMS"
        missing = [f for f in ("dn", "pn", "material", "medium", "angle")]
    else:
        intent = primary
        missing = missing_required_for_intent(parsed, primary)
    if not missing:
        return intents
    try:
        from ..parsing.llm_extractor import get_llm_extractor

        extractor = get_llm_extractor()
        if not extractor.enabled:
            return intents
        object.__setattr__(parsed, "_llm_extracted", True)
        known = params_from_parsed(parsed)
        extracted = extractor.extract_missing(intent, parsed.original_query or "", missing, known)
    except Exception:  # noqa: BLE001 — graceful-fallback обязателен
        object.__setattr__(parsed, "_llm_extracted", True)
        return intents
    if not extracted:
        return intents
    _apply_extracted(parsed, extracted)
    return detect_intents(parsed)


def enrich_parsed(parsed: Any) -> Any:
    """Заполняет ParsedQuery.intents/status/missing_params (мутация).

    Этап 1, §1H + §1F:
    - project quantity → units_count (достаточность «по N штук»);
    - LLM-доизвлечение недостающих параметров после rule-парсеров (§1F);
    - несовместимая комбинация интентов (§1H.2) → status=UNCLEAR + ambiguity;
    - params фильтруются по главному интенту (§1H.1);
    - primary_intent — флаг is_primary для первого (главного) интента (§1B.8).
    """
    uc = getattr(parsed, "units_count", None)
    qty = getattr(parsed, "quantity", None)
    if not uc and qty:
        try:
            object.__setattr__(parsed, "units_count", int(qty))
        except (TypeError, ValueError):
            pass
    intents = detect_intents(parsed)

    # §1F: LLM-доизвлечение недостающих параметров (fallback к regex).
    intents = _llm_extract(parsed, intents)

    # Классификация по группам (§1A) — данные для диагностики и UI.
    try:
        from ..parsing.classifier import get_group_classifier

        groups = get_group_classifier().classify(parsed.original_query or "").get("groups", [])
    except Exception:  # noqa: BLE001
        groups = []
    object.__setattr__(parsed, "groups", groups)

    conflicts = incompatible_detected(intents)
    if conflicts:
        message = f"Конфликт интентов: {', '.join(conflicts)}. Уточните, что именно нужно."
        object.__setattr__(parsed, "intents", intents)
        object.__setattr__(parsed, "primary_intent", intents[0] if intents else None)
        object.__setattr__(parsed, "status", PARSED_STATUS_UNCLEAR)
        object.__setattr__(parsed, "missing_params", {})
        object.__setattr__(parsed, "params", params_from_parsed(parsed))
        amb = list(getattr(parsed, "ambiguities", []) or [])
        if message not in amb:
            amb.append(message)
            object.__setattr__(parsed, "ambiguities", amb)
        return parsed

    primary = intents[0] if intents else None
    params = params_from_parsed(parsed)
    if primary:
        params = filter_params_for_intent(params, primary)
    status = determine_parsed_status(parsed, intents)
    missing_params = {
        it: missing_required_for_intent(parsed, it) for it in intents
    }
    object.__setattr__(parsed, "intents", intents)
    object.__setattr__(parsed, "primary_intent", primary)
    object.__setattr__(parsed, "status", status)
    object.__setattr__(parsed, "missing_params", missing_params)
    object.__setattr__(parsed, "params", params)
    return parsed