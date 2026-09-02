# agent/tools/analytic_tools.py

import logging
from typing import Any, Dict, List
from collections import defaultdict
import time

from .registry import register_tool
from .core_tools import _empty_result, _source, _card_component
from .stock_filters import passes_stock_filter
from ..core.state import AgentState

log = logging.getLogger("mtr.agent.tools")


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
    
    dn_to = changes.get("dn_to")
    dn_from = changes.get("dn_from")
    if dn_to or dn_from:
        checks.append("проверить фланцы, прокладки, болты на новый DN")
        affected.update(["фланцы", "прокладки", "болты"])
        if dn_to and dn_from:
            checks.append(f"подобрать переход DN{dn_from:.0f}→DN{dn_to:.0f} на границе участка")
        checks.append("проверить свободный проход (изменение прохода на стыке)")
        affected.update(["трубы", "переходы", "изменение прохода"])
        result["warnings"].append(
            "Изменение DN является изменением узла и не должно утверждаться автоматически."
        )
    
    if changes.get("medium"):
        checks.append(f"проверить совместимость материалов и уплотнений со средой {changes['medium']}")
        affected.update(["уплотнения", "материал деталей"])
    
    if changes.get("material_to") or changes.get("strength_to"):
        checks.append("проверить класс прочности и сварку по нормативной базе")
        affected.update(["сварные швы"])
    
    # Реальные соседние детали из графа (если известен участок/компонент).
    ctx = state.get("context", {}).get("repository")
    seen_units = set()
    for target in state.get("ksm_targets", [])[:20]:
        comp = target.get("component", {})
        unit = comp.get("unit_id")
        if not unit or unit in seen_units:
            continue
        seen_units.add(unit)
        if ctx is None:
            continue
        for n in ctx.get_components_by_unit(unit):
            ncid = n.get("component_id")
            if str(comp.get("component_id")) == str(ncid):
                continue
            nksm = n.get("ksm_code")
            ncard = ctx.get_card_by_ksm(nksm) if nksm else None
            result["components"].append({
                "ksm_code": nksm,
                "mtr_code": (ncard.get("codes") or {}).get("mtr_code") if ncard else None,
                "name": (ncard.get("name") if ncard else None) or n.get("designation"),
                "item_type": n.get("item_type"),
                "quantity": None,
                "status": "затронуто (соседний узел)",
                "detail": f"участок {unit}: проверить при замене",
                "source_id": ncid,
            })
            result["sources"].append(_source("object_graph", ncid, unit))
    
    for c in checks[:6]:
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
    
    for name in sorted(affected)[:6]:
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


_URGENCY_ITEM_TYPE = {
    "задвижка": 3, "арматура": 3, "кран": 3, "клапан": 3,
    "переход": 2, "отвод": 2, "тройник": 2, "штуцер": 2,
    "заглушка": 1, "фланец": 1, "прокладка": 1, "труба": 1,
}


_URGENCY_LABELS = {
    5: "критическая",
    4: "высокая",
    3: "средняя",
    2: "низкая",
    1: "минимальная",
}


def _urgency_label(score: int) -> str:
    return _URGENCY_LABELS.get(score, "минимальная")


def _urgency_status(qty, score: int) -> str:
    label = _urgency_label(score)
    if qty is None or qty == 0:
        return f"нет на складе — срочность закупки: {label}"
    if score >= 4:
        return f"на складе: {qty} — срочность пополнения: {label}"
    if score >= 2:
        return f"на складе: {qty} — срочность пополнения: {label}"
    return f"на складе: {qty}"


def _urgency_detail(card: Dict, qty, score: int) -> str:
    parts = []
    item_type = card.get("item_type") or ""
    label = _urgency_label(score)
    if score >= 4:
        parts.append(f"критично: {item_type} нужна срочно")
    elif score >= 2:
        parts.append(f"рекомендуется закупить: {item_type}")
    else:
        parts.append(f"пополнение: {item_type}")
    if qty is None or qty == 0:
        parts.append("нет остатков")
    elif qty < 5:
        parts.append(f"остаток {qty} — ниже нормы")
    return "; ".join(parts)


def _urgency_reason(card: Dict, qty, base: int, bump: int) -> str:
    """Человекочитаемая причина расчёта urgency (для логов)."""
    item_type = card.get("item_type") or "неизвестно"
    parts = [f"тип={item_type}(база={base})"]
    if qty is None or qty == 0:
        parts.append(f"нет на складе(+{bump})")
    elif bump:
        parts.append(f"остаток={qty}(+{bump})")
    else:
        parts.append(f"остаток={qty}(+0)")
    return ", ".join(parts)


def _build_purchase_recommendation(components: List[Dict]) -> str:
    """Итоговая сводка по закупке: группы по urgency."""
    critical, high, medium, low = [], [], [], []
    for c in components:
        s = c.get("_urgency_score", 1)
        if s >= 5:
            critical.append(c)
        elif s >= 4:
            high.append(c)
        elif s >= 2:
            medium.append(c)
        else:
            low.append(c)

    parts = []
    if critical:
        types = sorted(set(c.get("item_type", "?") for c in critical))
        parts.append(f"{', '.join(types)} — критически срочно ({len(critical)} шт.)")
    if high:
        types = sorted(set(c.get("item_type", "?") for c in high))
        parts.append(f"{', '.join(types)} — срочно ({len(high)} шт.)")
    if medium:
        types = sorted(set(c.get("item_type", "?") for c in medium))
        parts.append(f"{', '.join(types)} — рекомендуется ({len(medium)} шт.)")
    if low:
        types = sorted(set(c.get("item_type", "?") for c in low))
        parts.append(f"{', '.join(types)} — можно позже ({len(low)} шт.)")
    return "Рекомендация по закупке: " + "; ".join(parts) if parts else ""


@register_tool("inventory_calculator", "Расчёт рекомендуемого запаса")
def inventory_calculator(state: AgentState) -> Dict[str, Any]:
    """Расчёт рекомендуемого запаса с фильтрацией по наличию и ранжированием по срочности."""
    start = time.time()
    result = _empty_result()

    targets = state.get("ksm_targets", [])
    stock_rows = state.get("stock_rows", [])
    parsed = state.get("parsed")

    stock_by_ksm = {}
    for row in stock_rows:
        ksm = row.get("ksm_code")
        if ksm:
            stock_by_ksm[ksm] = row

    multiplier = getattr(parsed, "units_count", 1) or 1

    intents = getattr(parsed, "intents", []) or []
    on_stock = getattr(parsed, "on_stock", None)
    out_of_stock_only = (on_stock is False) or ("LIST_OUT_OF_STOCK" in intents)

    for target in targets[:20]:
        card = target.get("card")
        if not card:
            continue

        ksm = (card.get("codes") or {}).get("ksm_code")

        stock_info = stock_by_ksm.get(ksm) if ksm else None
        qty = stock_info.get("quantity") if stock_info else None

        # Если stock_query отфильтровал позицию по порогу остатка —
        # stock_rows её не содержит, qty=None; при наличии quantity_max
        # такие позиции тоже пропускаем (они не попали в filtered stock_rows).
        stock_filters = getattr(parsed, "stock_filters", None) or {}
        if qty is None and stock_filters.get("quantity_max") is not None:
            continue

        # Пороги остатка (quantity_min/quantity_max) применяются к ФАКТИЧЕСКОМУ
        # остатку, а не к рекомендуемому значению.
        if not passes_stock_filter(qty, parsed):
            continue

        if out_of_stock_only and qty is not None and qty > 0:
            continue

        if out_of_stock_only:
            recommended = 0
        else:
            recommended = max(1, qty or 0) * multiplier

        item_type = (card.get("item_type") or "").lower()
        base = _URGENCY_ITEM_TYPE.get(item_type, 1)
        if qty is None or qty == 0:
            bump = 2
        elif qty < 5:
            bump = 1
        else:
            bump = 0
        urgency = min(base + bump, 5)

        log.info(
            "[inventory_calculator] urgency=%d для %s: %s",
            urgency, ksm, _urgency_reason(card, qty, base, bump),
        )

        result["components"].append({
            "ksm_code": ksm,
            "mtr_code": (card.get("codes") or {}).get("mtr_code"),
            "name": card.get("name"),
            "item_type": card.get("item_type"),
            "quantity": recommended,
            "status": _urgency_status(qty, urgency),
            "detail": _urgency_detail(card, qty, urgency),
            "source_id": card.get("card_id"),
            "_urgency": urgency,
            "_urgency_score": urgency,
            "_tool": "inventory_calculator",
        })

    result["components"].sort(key=lambda c: c.get("_urgency", 0), reverse=True)
    for comp in result["components"]:
        comp.pop("_urgency", None)

    purchase_rec = _build_purchase_recommendation(result["components"])

    result["warnings"] = ["Расчёт — черновик: нормы запаса требуют утверждения"]
    result["review"] = True
    result["text"] = (
        f"Рассчитано {len(result['components'])} позиций"
        + (" (только отсутствующие на складе)" if out_of_stock_only else "")
    )
    result["purchase_recommendation"] = purchase_rec
    result["duration_ms"] = (time.time() - start) * 1000
    return result


def _aggregate_stock_by_type(targets: List[Dict], stock_rows: List[Dict]) -> Dict[str, Dict]:
    """Агрегирует остаток по типу детали (item_type) из stock_rows.

    Предпочитаем stock_rows, когда они несут item_type (не зависят от графа
    объекта). Если rows без типа (только ksm+quantity) — агрегируем через
    ksm_targets (карточка даёт item_type).
    """
    typed_rows = [r for r in stock_rows if r.get("item_type")]

    if typed_rows:
        by_type: Dict[str, Dict] = {}
        for row in typed_rows:
            item_type = row.get("item_type") or "неизвестно"
            qty = row.get("quantity") or 0
            bucket = by_type.setdefault(item_type, {"sum_stock": 0.0, "items": 0})
            bucket["sum_stock"] += float(qty)
            bucket["items"] += 1
        return by_type

    stock_by_ksm = {r.get("ksm_code"): r for r in stock_rows if r.get("ksm_code")}
    by_type = {}
    for target in targets:
        card = target.get("card")
        if not card:
            continue
        item_type = card.get("item_type") or "неизвестно"
        ksm = (card.get("codes") or {}).get("ksm_code")
        qty = (stock_by_ksm.get(ksm) or {}).get("quantity") or 0
        bucket = by_type.setdefault(item_type, {"sum_stock": 0.0, "items": 0})
        bucket["sum_stock"] += qty
        bucket["items"] += 1
    return by_type


@register_tool("sufficiency_check", "Проверка достаточности запаса «хватает ли по N штук»")
def sufficiency_check(state: AgentState) -> Dict[str, Any]:
    """Агрегирует остаток по типу и сравнивает с потребностью N (units_count).

    Результат — verdict «хватает» / «не хватает» по каждому типу детали.
    """
    start = time.time()
    result = _empty_result()

    targets = state.get("ksm_targets", [])
    stock_rows = state.get("stock_rows", [])
    parsed = state.get("parsed")

    needed = getattr(parsed, "units_count", None) or 1

    by_type = _aggregate_stock_by_type(targets, stock_rows)

    # Гарантируем verdict для КАЖДОГО запрошенного типа (в т.ч. нулевой остаток),
    # чтобы ответ явно говорил, каких типов не хватает (DoD п.3).
    requested_types = list(getattr(parsed, "item_types", []) or [])
    if not by_type and not requested_types:
        result["warnings"].append("Не определены типы деталей для проверки достаточности")
        result["text"] = "Нет данных для проверки достаточности"
        result["duration_ms"] = (time.time() - start) * 1000
        return result

    for it in requested_types:
        by_type.setdefault(it, {"sum_stock": 0.0, "items": 0})

    all_sufficient = True
    for item_type in sorted(by_type):
        bucket = by_type[item_type]
        sum_stock = bucket["sum_stock"]
        sufficient = sum_stock >= needed
        deficit = max(0, needed - sum_stock)
        if not sufficient:
            all_sufficient = False

        verdict = "хватает" if sufficient else "не хватает"
        status_parts = [f"потребность {needed} шт.", f"остаток {sum_stock:.0f} шт."]
        if not sufficient:
            status_parts.append(f"дефицит {deficit:.0f} шт.")

        result["components"].append({
            "item_type": item_type,
            "quantity": sum_stock,
            "needed": needed,
            "deficit": deficit,
            "status": f"{verdict}: {item_type} — {'; '.join(status_parts)}",
            "verdict": verdict,
            "detail": "хватает" if sufficient else f"не хватает {deficit:.0f} шт.",
        })

        result["sources"].append(_source("stock", f"type:{item_type}",
                                         f"суммарный остаток по типу: {sum_stock:.0f}"))

    if all_sufficient:
        result["text"] = "Все запрошенные типы в достаточном количестве"
        result["review"] = False
    else:
        result["text"] = "Есть типы, которых не хватает"
        result["review"] = True

    log.info(
        "[sufficiency_check] needed=%s types=%d all_sufficient=%s",
        needed, len(by_type), all_sufficient,
    )
    result["duration_ms"] = (time.time() - start) * 1000
    return result


@register_tool("maintenance_planner", "Черновик плана ТОиР")
def maintenance_planner(state: AgentState) -> Dict[str, Any]:
    """Черновик плана ТОиР: работы по целевым деталям + комплекс соседних узлов.

    Граф участка даёт соседние детали (стыки, через-компоненты: прокладки,
    фланцы, болты), которые при ТОиР проверяют/меняют комплектом.
    """
    start = time.time()
    result = _empty_result()

    ctx = state.get("context", {}).get("repository")
    targets = state.get("ksm_targets", [])

    planned_units: set = set()
    kit_rows = 0

    for target in targets[:10]:
        comp = target.get("component", {})
        card = target.get("card")
        unit = comp.get("unit_id")

        result["components"].append({
            "ksm_code": comp.get("ksm_code"),
            "mtr_code": (card.get("codes") or {}).get("mtr_code") if card else None,
            "name": card.get("name") if card else comp.get("designation"),
            "item_type": comp.get("item_type"),
            "status": "работа: обслуживание/проверка",
            "detail": f"участок {unit}",
            "source_id": comp.get("component_id"),
        })
        result["sources"].append(_source("object_graph", comp.get("component_id"), unit))

        # Комплект: соседние детали того же участка из графа.
        if ctx and unit and unit not in planned_units:
            planned_units.add(unit)
            for n in ctx.get_components_by_unit(unit):
                ncid = n.get("component_id")
                if str(comp.get("component_id")) == str(ncid):
                    continue
                ncard = ctx.get_card_by_ksm(n.get("ksm_code")) if n.get("ksm_code") else None
                result["components"].append({
                    "ksm_code": n.get("ksm_code"),
                    "mtr_code": (ncard.get("codes") or {}).get("mtr_code") if ncard else None,
                    "name": (ncard.get("name") if ncard else None) or n.get("designation"),
                    "item_type": n.get("item_type"),
                    "status": "комплект: проверить при ТОиР",
                    "detail": f"участок {unit}",
                    "source_id": ncid,
                })
                kit_rows += 1
                result["sources"].append(_source("object_graph", ncid, unit))

    # Расходники.
    result["components"].append({
        "ksm_code": None,
        "mtr_code": None,
        "name": "Расходные материалы",
        "item_type": None,
        "quantity": None,
        "status": "комплект",
        "detail": "прокладки, крепёж, материалы по регламенту ТОиР",
        "source_id": None,
    })

    # H2S-эскалация: состав работ при агрессивной среде согласует эксперт.
    tf = getattr(state["parsed"], "technical_filters", {}) or {}
    medium = str(tf.get("medium") or "").lower()
    if "h2s" in medium or "сероводород" in medium:
        result["warnings"].append(
            "Среда с H2S: состав работ и материалы согласует служба ТОиР и эксперт по коррозии."
        )

    result["warnings"].append("Черновик: периодичность и состав работ утверждает служба ТОиР")
    result["sources"].append(
        _source("maintenance_policy", "MTR-TOIR-POLICY-001", "регламент ТОиР (черновой)"))
    result["sources"].append(
        _source("maintenance_history", "MTR-TOIR-HISTORY-001",
                "история эксплуатации участка (МВП: расчётно)"))
    result["review"] = True
    result["text"] = f"Спланировано {len(result['components'])} позиций (комплект: {kit_rows})"
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
    result["sources"].append(
        _source("expert_decisions", "expert-review-001",
                "дубли/расхождения каталога решает эксперт"))
    result["review"] = True
    result["text"] = f"Найдено {len(dup_groups)} групп с одинаковыми параметрами"
    result["duration_ms"] = (time.time() - start) * 1000
    return result
