"""Аналитические тулы агента: дубли, расчёт запаса, план ТО, приоритеты, сборка, влияние, объяснения."""

from typing import Any, Dict, List, Optional

from app.schemas import ParsedQuery


def _source(kind: str, id_: str, fragment: str = None) -> Dict[str, Any]:
    return {"kind": kind, "id": id_, "fragment": fragment}


def _empty() -> Dict[str, Any]:
    return {
        "text": "",
        "components": [],
        "warnings": [],
        "sources": [],
        "missing": [],
        "review": False,
    }


def _card_component(card: Dict[str, Any], qty: Optional[float] = None,
                    status: str = None, detail: str = None) -> Dict[str, Any]:
    codes = card.get("codes") or {}
    props = card.get("properties") or {}
    return {
        "mtr_code": codes.get("mtr_code"),
        "ksm_code": codes.get("ksm_code"),
        "name": card.get("name"),
        "item_type": card.get("item_type"),
        "quantity": qty if qty is not None else (props.get("stock_qty") or {}).get("value"),
        "status": status,
        "detail": detail,
        "source_id": card.get("card_id"),
    }


def _pn_match(got, wanted) -> bool:
    """PN в каталоге в барах, парсер отдаёт МПа: сравниваем с пересчётом x10."""
    if got is None or wanted is None:
        return True
    got, wanted = float(got), float(wanted)
    if abs(got - wanted) <= max(0.01, abs(wanted) * 0.1):
        return True
    return abs(got - wanted * 10) <= max(0.01, abs(wanted * 10) * 0.1)


def _cards_from_targets(ctx, workspace: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Карточки из ksm_targets (граф/компоненты) или из кандидатов каталога."""
    cards: List[Dict[str, Any]] = []
    seen = set()
    for t in workspace.get("ksm_targets", []):
        card = t.get("card") or ctx.by_ksm.get(t.get("ksm"))
        if card and ctx.card_ksm(card) not in seen:
            seen.add(ctx.card_ksm(card))
            cards.append(card)
    if not cards:
        for c in workspace.get("candidates", []):
            card = c["card"]
            if ctx.card_ksm(card) not in seen:
                seen.add(ctx.card_ksm(card))
                cards.append(card)
    return cards


# =========================================================
# DUPLICATE_DETECTOR
# =========================================================
def duplicate_detector(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Группы карточек с одинаковыми параметрами, но разными КСМ (кандидаты в дубли)."""
    result = _empty()
    cards = _cards_from_targets(ctx, workspace) or ctx.catalog

    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for card in cards:
        key = (
            card.get("item_type"),
            ctx.prop(card, "dn"),
            ctx.prop(card, "pn"),
            ctx.prop(card, "steel_grade"),
            ctx.prop(card, "wall_thickness"),
        )
        if all(v is not None for v in key):
            groups.setdefault(key, []).append(card)

    dup_groups = []
    for key, items in groups.items():
        ksms = {ctx.card_ksm(c) for c in items}
        if len(ksms) > 1:
            dup_groups.append((key, items))

    for key, items in dup_groups[:10]:
        dn, pn, steel, wall = key[1], key[2], key[3], key[4]
        label = f"DN={dn}, PN={pn}, сталь={steel}, стенка={wall}"
        for card in items:
            result["components"].append(_card_component(
                card, status="кандидат в дубль",
                detail=label + "; код КСМ отличается при равных параметрах"))
            result["sources"].append(_source("catalog", card["card_id"], label))

    result["text"] = "Дубли: найдено %d групп с равными параметрами и разными КСМ." % len(dup_groups)
    result["warnings"] = ["Совпадение параметров не доказывает дубль — нужен аудит экспертом."]
    result["sources"].append(_source(
        "expert_decisions", None,
        "окончательное решение о дубле принимает эксперт после аудита"))
    result["review"] = True
    workspace["duplicate_groups"] = dup_groups
    return result


# =========================================================
# INVENTORY_CALCULATOR
# =========================================================
def inventory_calculator(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Рекомендуемый запас с учётом количества участков (units_count)."""
    result = _empty()
    cards = _cards_from_targets(ctx, workspace)
    if not cards:
        result["text"] = "Запас: нет целевых позиций (укажите участок или параметры)."
        result["missing"] = ["unit_ids", "item_type"]
        return result

    multiplier = parsed.units_count or 1
    for card in cards:
        ksm = ctx.card_ksm(card)
        qty = ctx.stock_qty(card) or 0
        recommended = max(1, qty) * multiplier
        detail = f"остаток={qty}; множитель участков x{multiplier} -> рекомендуемый запас {recommended}"
        result["components"].append(_card_component(
            card, qty=recommended, status="рекомендуемый запас", detail=detail))
        result["sources"].append(_source("stock", ksm, detail))

    result["text"] = "Запас: рассчитано %d позиций (x%d)." % (len(result["components"]), multiplier)
    result["warnings"] = ["Расчёт — черновик: нормы запаса требуют утверждения."]
    result["review"] = True
    return result


# =========================================================
# MAINTENANCE_PLANNER
# =========================================================
def maintenance_planner(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Черновик плана ТОиР: компоненты участков и их обслуживание."""
    result = _empty()
    unit_ids = list(parsed.unit_ids or workspace.get("unit_ids", []))
    if not unit_ids:
        result["text"] = "План ТО: не указан участок (unit_id)."
        result["missing"] = ["unit_ids"]
        return result

    works: List[Dict[str, Any]] = []
    for uid in unit_ids:
        profile = ctx.medium_profile(uid)
        status = (profile or {}).get("compatibility_status", "не определен")
        for comp in ctx.components_of_unit(uid):
            works.append({
                "unit_id": uid,
                "component_id": comp.get("component_id"),
                "ksm_code": comp.get("ksm_code"),
                "item_type": comp.get("item_type"),
                "designation": comp.get("designation"),
                "status": comp.get("compatibility_status") or status,
            })

    for w in works:
        result["components"].append({
            "ksm_code": w["ksm_code"],
            "mtr_code": None,
            "name": w["designation"],
            "item_type": w["item_type"],
            "status": "работа: обслуживание/проверка",
            "detail": "участок %s; статус %s" % (w["unit_id"], w["status"]),
            "source_id": w["component_id"],
        })
        result["sources"].append(_source("object_graph", w["component_id"], w["unit_id"]))

    result["sources"].append(_source(
        "maintenance_policy", "rego",
        "нормы и регламент ТОиР в MVP не наполнены; периодичность утверждает служба ТОиР"))
    result["sources"].append(_source(
        "maintenance_history", "rego",
        "история отказов в MVP отсутствует; план предварительный"))

    result["text"] = "План ТО: %d работ по %d участкам." % (len(works), len(unit_ids))
    result["warnings"] = ["Черновик: периодичность и состав работ утверждает служба ТОиР."]
    result["review"] = True
    return result


# =========================================================
# PRIORITY_RANKER
# =========================================================
def priority_ranker(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Ранжирование по срочности/риску: остаток, среда, покрытие, статус подтверждения."""
    result = _empty()
    cards = _cards_from_targets(ctx, workspace) or [c["card"] for c in workspace.get("candidates", [])]

    scored = []
    for card in cards:
        qty = ctx.stock_qty(card)
        score = 0
        reasons = []
        if qty is None or qty <= 0:
            score += 30
            reasons.append("нулевой остаток")
        elif qty < 3:
            score += 15
            reasons.append("малый остаток")
        medium = ctx.prop(card, "medium")
        if medium and str(medium).lower() in ("h2s", "co2", "газ с h2s", "газ с co2"):
            score += 25
            reasons.append("агрессивная среда")
        if not ctx.prop(card, "outer_coating"):
            score += 10
            reasons.append("без наружного покрытия")
        status = ctx.prop(card, "compatibility_status")
        if status and "requires" in str(status):
            score += 15
            reasons.append("требует подтверждения")
        scored.append({
            "card": card,
            "qty": qty,
            "score": score,
            "reasons": "; ".join(reasons) or "—",
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[: (parsed.limit or 10)]
    for item in top:
        result["components"].append(_card_component(
            item["card"], qty=item["qty"],
            status="риск %d" % item["score"],
            detail=item["reasons"]))
        result["sources"].append(_source("catalog", item["card"]["card_id"], item["reasons"]))

    result["text"] = "Приоритеты: отранжировано %d, показано top-%d." % (len(scored), len(top))
    result["warnings"] = ["Окончательный приоритет зависит от норм запаса и плана ремонта."]
    result["review"] = True
    return result


# =========================================================
# OBJECT_BUILDER
# =========================================================
def object_builder(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Формирование перечня деталей нового участка по параметрам (DN/PN/среда, длина)."""
    result = _empty()
    tf = parsed.technical_filters or {}
    dn = tf.get("dn") or (parsed.card.geometry.dn if parsed.card and parsed.card.geometry else None)
    pn = tf.get("pn") or (parsed.card.pressure.pn if parsed.card and parsed.card.pressure else None)
    medium = tf.get("medium") or (parsed.card.environment.medium if parsed.card and parsed.card.environment else None)
    length = parsed.length_m

    missing = []
    if not dn:
        missing.append("dn")
    if not pn:
        missing.append("pn")
    if not medium:
        missing.append("medium")
    if missing:
        result["text"] = "Сборка участка: не хватает параметров."
        result["missing"] = missing
        return result

    item_types = parsed.item_types or ["труба", "отвод", "переход", "задвижка", "заглушка", "тройник"]
    counts = {it: 1 for it in item_types}
    if "труба" in counts and length:
        counts["труба"] = max(1, int(length / 10))

    for it in item_types:
        best = None
        for card in ctx.catalog:
            if card.get("item_type") != it:
                continue
            if ctx.prop(card, "dn") != dn:
                continue
            if pn and ctx.prop(card, "pn") is not None and not _pn_match(ctx.prop(card, "pn"), pn):
                continue
            best = card
            break
        if best:
            result["components"].append(_card_component(
                best, qty=counts[it], status="подобрано по DN/PN",
                detail="среда %s; длина участка %s м" % (medium, length or "?")))
            result["sources"].append(_source("catalog", best["card_id"], "DN=%s PN=%s" % (dn, pn)))
        else:
            result["missing"].append("карточка: %s DN%s PN%s" % (it, dn, pn))

    result["text"] = "Сборка участка: составлено %d позиций (DN%s, %s)." % (
        len(result["components"]), dn, medium)
    result["warnings"] = ["Точное количество деталей зависит от проектной схемы."]
    result["sources"].append(_source(
        "project_documentation", None,
        "трасса и проектная схема в MVP отсутствуют; количество деталей расчётное"))
    result["review"] = True
    return result


# =========================================================
# IMPACT_ANALYZER
# =========================================================
def impact_analyzer(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Что проверить при замене/изменении: соседние детали и системные проверки."""
    result = _empty()
    changes = dict(parsed.proposed_changes or {})
    tf = parsed.technical_filters or {}

    # Парсер не всегда вычленяет изменение среды — выводим из фильтров запроса.
    if not changes.get("medium") and tf.get("medium"):
        medium = str(tf["medium"]).lower()
        if "h2s" in medium or "co2" in medium:
            changes["medium"] = str(tf["medium"])
    if not changes.get("dn_to") and tf.get("dn"):
        changes["dn_to"] = tf["dn"]

    checks = []
    if changes.get("dn_to") or changes.get("dn_from"):
        checks.append("проверить фланцы, прокладки, болты на новый DN")
    if changes.get("medium"):
        checks.append("проверить совместимость материалов и уплотнений со средой %s" % changes["medium"])
    if changes.get("material_to") or changes.get("strength_to"):
        checks.append("проверить класс прочности и сварку по нормативной базе")

    impact = parsed.impact_analysis or {}
    checks.extend(impact.get("required_checks", []))
    result["components"] = [{
        "ksm_code": None,
        "mtr_code": None,
        "name": "Проверка",
        "item_type": None,
        "quantity": None,
        "status": "required",
        "detail": c,
        "source_id": None,
    } for c in checks]

    affected = set(impact.get("affected_components", []))
    if changes.get("dn_to") or changes.get("dn_from"):
        affected.update(["фланцы", "прокладки", "болты"])
    if changes.get("medium"):
        affected.update(["уплотнения", "материал деталей"])
    for name in sorted(affected):
        result["components"].append({
            "ksm_code": None, "mtr_code": None, "name": name,
            "item_type": None, "quantity": None,
            "status": "затронуто", "detail": "соседний узел при замене", "source_id": None,
        })

    result["text"] = "Влияние: %d проверок, %d затронутых узлов." % (
        len(checks), len(affected))
    if changes.get("dn_to") or changes.get("dn_from"):
        result["sources"].append(_source(
            "project_documentation", None,
            "оценка влияния изменения DN требует проектной схемы участка"))
        result["sources"].append(_source(
            "object_graph", None, "граф объекта для проверки соседних узлов"))
    result["review"] = True
    return result


# =========================================================
# EXPLANATION_GENERATOR
# =========================================================
def explanation_generator(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Объяснение значимости позиций (почему деталь важна / почему в выдаче).

    L5: при наличии LLM-объяснителя (ctx.llm_explainer) для топ-кандидатов
    строится объяснение «почему кандидат в выдаче»; при недоступности LLM —
    правило-фолбэк по типу изделия.
    """
    result = _empty()
    cards = _cards_from_targets(ctx, workspace) or [c["card"] for c in workspace.get("candidates", [])]

    role_map = {
        "труба": "основной несущий элемент, определяет пропускную способность",
        "отвод": "обеспечивает поворот трассы, влияет на гидравлику и износ",
        "переход": "сопрягает разные диаметры, критичен для сварных швов",
        "задвижка": "запорная арматура, критична для отсечения участка",
        "заглушка": "герметизация тупиковых отводов и заглушек",
        "тройник": "точка ответвления, влияет на распределение потоков",
    }
    explainer = getattr(ctx, "llm_explainer", None)
    for index, card in enumerate(cards[:20]):
        item_type = card.get("item_type")
        role = role_map.get(item_type, "элемент трубопроводной обвязки")
        detail = "%s; %s" % (role, "без наружного покрытия — риск коррозии"
                             if not ctx.prop(card, "outer_coating") else "покрытие нанесено")
        if explainer is not None and index < 3:
            explanation = explainer.explain(parsed.original_query, card)
            if explanation.get("reasons"):
                detail = "%s; почему в выдаче: %s" % (
                    detail, "; ".join(explanation["reasons"])
                )
        result["components"].append(_card_component(card, status="значимость", detail=detail))

    result["text"] = "Объяснения: %d позиций." % len(result["components"])
    return result
