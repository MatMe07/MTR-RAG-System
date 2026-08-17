"""Core-тулы агента: поиск по каталогу, склад, граф объекта, регуляторика, правила, документы."""

from typing import Any, Dict, List

from app.core.logging import get_logger
from app.schemas import ParsedQuery

log = get_logger("agent.tools")


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


def _matches_filters(card: Dict[str, Any], parsed: ParsedQuery) -> bool:
    """Геометрическое/техническое совпадение карточки каталога с запросом."""
    ctx_prop = card["properties"]
    tf = parsed.technical_filters or {}

    def num(key, default=None):
        v = (ctx_prop.get(key) or {}).get("value")
        return v if isinstance(v, (int, float)) else default

    def within(got, want, tolerance_frac):
        if got is None or want is None:
            return True
        return abs(float(got) - float(want)) <= float(want) * tolerance_frac

    if not within(num("dn"), tf.get("dn"), 0.1):
        return False
    if not within(num("angle"), tf.get("angle"), 0.0):
        return False
    if not within(num("wall_thickness"), tf.get("wall_thickness"), 0.15):
        return False
    if not _pn_match(num("pn"), tf.get("pn")):
        return False

    item_types = parsed.item_types or []
    if item_types and card.get("item_type") not in item_types:
        return False

    medium = tf.get("medium")
    if medium:
        card_medium = (ctx_prop.get("medium") or {}).get("value")
        if card_medium and not _medium_equal(card_medium, medium):
            return False
    return True


def _card_has_data(card) -> bool:
    if not card:
        return False
    if card.item_type or card.designation or card.name:
        return True
    if card.geometry and (card.geometry.dn or card.geometry.d1 or card.geometry.d2
                          or card.geometry.wall_thickness or card.geometry.angle):
        return True
    if card.pressure and (card.pressure.pn or card.pressure.working_pressure_mpa):
        return True
    if card.material and (card.material.steel_grade or card.material.strength_class):
        return True
    if card.environment and (card.environment.medium or card.environment.h2s_confirmed
                             or card.environment.co2_confirmed):
        return True
    return False


def _pn_match(got, wanted) -> bool:
    """PN в каталоге хранится в барах, парсер отдаёт МПа: сравниваем с пересчётом."""
    if got is None or wanted is None:
        return True
    got, wanted = float(got), float(wanted)
    if abs(got - wanted) <= max(0.01, abs(wanted) * 0.1):
        return True
    if abs(got - wanted * 10) <= max(0.01, abs(wanted * 10) * 0.1):
        return True
    if abs(got - wanted / 10) <= max(0.01, abs(wanted / 10) * 0.1):
        return True
    return False


def _medium_equal(card_medium: str, wanted: str) -> bool:
    a = str(card_medium).lower()
    b = str(wanted).lower()
    if a == b:
        return True
    aliases = {"h2s": ("газ с h2s", "коррозионно-активная среда"),
               "co2": ("газ с co2",)}
    for key, variants in aliases.items():
        if key in (a, b) and any(v in (a, b) for v in variants):
            return True
    return False


def _card_component(card: Dict[str, Any], score: float, reason: str) -> Dict[str, Any]:
    codes = card.get("codes") or {}
    props = card.get("properties") or {}
    return {
        "mtr_code": codes.get("mtr_code"),
        "ksm_code": codes.get("ksm_code"),
        "name": card.get("name") or card.get("designation"),
        "item_type": card.get("item_type"),
        "quantity": (props.get("stock_qty") or {}).get("value"),
        "status": reason,
        "detail": "score=%.0f%%" % (score * 100),
        "source_id": card.get("card_id"),
    }


# =========================================================
# CATALOG_SEARCH
# =========================================================
def _catalog_matches(ctx, parsed: ParsedQuery) -> List[Dict[str, Any]]:
    """Кандидаты каталога: гибридный поиск репозитория или перебор по фильтрам.

    db-режим (AgentRepository) даёт гибрид PG-фильтры + Qdrant-семантика;
    json-режим и AgentContext семантики не имеют — классический перебор.
    """
    search = getattr(ctx, "search_candidates", None)
    if callable(search):
        try:
            found = search(parsed, limit=40)
        except Exception:  # noqa: BLE001 — Qdrant/БД недоступны — перебор
            found = None
        if found:
            log.info("[catalog_search] источник=репозиторий(гибрид) кандидатов=%d", len(found))
            return found
        log.info("[catalog_search] источник=перебор (репозиторий вернул пусто)")
    else:
        log.info("[catalog_search] источник=перебор (нет search_candidates)")
    matched: List[Dict[str, Any]] = []
    for card in ctx.catalog:
        if _matches_filters(card, parsed):
            matched.append({"card": card, "score": _match_score(card, parsed)})
    return matched


def catalog_search(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Поиск кандидатов в каталоге по карточке/фильтрам запроса."""
    result = _empty()

    tf = parsed.technical_filters or {}
    searchable_keys = ("dn", "angle", "wall_thickness", "pn", "medium",
                       "steel_grade", "strength_class", "d1", "d2")
    has_criteria = bool(parsed.item_types) or any(tf.get(k) for k in searchable_keys)
    if not has_criteria and not _card_has_data(parsed.card):
        result["text"] = "Каталог: не заданы параметры поиска."
        return result

    matched = _catalog_matches(ctx, parsed)
    matched.sort(key=lambda x: x["score"], reverse=True)
    candidates = []
    for m in matched[:40]:
        card = m["card"]
        reason = m.get("reason") or "совпадает по параметрам запроса"
        candidates.append({"card": card, "score": m["score"], "reason": reason})
        result["components"].append(
            _card_component(card, m["score"], reason)
        )
        result["sources"].append(_source("catalog", card["card_id"], card.get("designation")))

    workspace["candidates"] = candidates
    result["text"] = "Каталог: найдено %d подходящих позиций." % len(candidates)
    return result


def _match_score(card: Dict[str, Any], parsed: ParsedQuery) -> float:
    tf = parsed.technical_filters or {}
    props = card.get("properties") or {}
    hits = 0.0
    checks = 0.0

    def num(key):
        v = (props.get(key) or {}).get("value")
        return v if isinstance(v, (int, float)) else None

    for key, want in (("dn", tf.get("dn")), ("angle", tf.get("angle")),
                      ("wall_thickness", tf.get("wall_thickness"))):
        got = num(key)
        if want is not None:
            checks += 1
            if got is not None and abs(float(got) - float(want)) <= float(want) * 0.1:
                hits += 1

    if tf.get("pn") is not None:
        checks += 1
        if _pn_match(num("pn"), tf.get("pn")):
            hits += 1

    item_types = parsed.item_types or []
    if item_types:
        checks += 1
        if card.get("item_type") in item_types:
            hits += 1

    return hits / checks if checks else 0.5


# =========================================================
# STOCK_QUERY
# =========================================================
def stock_query(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Складские остатки: применяет on_stock/not_installed/quantity_min/max."""
    result = _empty()
    sf = parsed.stock_filters or {}

    items: List[Dict[str, Any]] = list(workspace.get("ksm_targets", []))
    for cand in workspace.get("candidates", []):
        items.append({"card": cand["card"], "ksm": ctx.card_ksm(cand["card"]),
                      "name": cand["card"].get("name")})

    seen = set()
    rows = []
    for item in items:
        card = item.get("card")
        if card is None:
            card = ctx.by_ksm.get(item.get("ksm"))
        if card is None:
            continue
        ksm = ctx.card_ksm(card)
        if not ksm or ksm in seen:
            continue
        seen.add(ksm)
        qty = ctx.stock_qty(card)
        component_id = item.get("component_id")
        unit_id = item.get("unit_id")
        rows.append({"card": card, "ksm": ksm, "qty": qty,
                     "component_id": component_id, "unit_id": unit_id})

    qty_min = sf.get("quantity_min")
    qty_max = sf.get("quantity_max")
    on_stock = parsed.on_stock
    not_installed = parsed.not_installed
    installed = ctx.installed_ksms()

    filtered = []
    for row in rows:
        qty = row["qty"]
        if qty_min is not None and (qty is None or qty < qty_min):
            continue
        if qty_max is not None and (qty is None or qty > qty_max):
            continue
        if on_stock is False and qty:
            continue
        if on_stock is True and not qty:
            continue
        if not_installed and row["ksm"] in installed:
            continue
        filtered.append(row)

    for row in filtered:
        qty = row["qty"]
        if qty:
            status = "на складе: %s" % qty
        else:
            status = "нет на складе (нулевой остаток)"
        result["components"].append({
            "ksm_code": row["ksm"],
            "mtr_code": ctx.card_mtr(row["card"]),
            "name": row["card"].get("name"),
            "item_type": row["card"].get("item_type"),
            "quantity": qty,
            "status": status,
            "detail": ("компонент %s" % row["component_id"]) if row.get("component_id") else None,
            "source_id": row["card"].get("card_id"),
        })
        result["sources"].append(_source("stock", row["ksm"], status))

    workspace["stock_rows"] = filtered
    result["text"] = "Склад: отобрано %d позиций." % len(filtered)
    return result


# =========================================================
# GRAPH_SEARCH
# =========================================================
def _units_for_medium(ctx, medium: str) -> List[str]:
    """Коды участков под среду запроса (без явного unit_id)."""
    med = str(medium).lower()
    codes: set = set()
    if "h2s" in med or "сероводород" in med:
        codes |= {"gas_h2s", "gas_h2s_co2"}
    if "co2" in med:
        codes |= {"gas_co2", "gas_h2s_co2"}
    if "коррози" in med:
        codes |= {"corrosive_medium"}
    if "природный газ" in med or "natural" in med:
        codes |= {"natural_gas"}
    for unit in ctx.graph.get("units", []):
        if (unit.get("medium_code") or "").lower() in {c.lower() for c in codes}:
            codes.add(unit.get("medium_code"))
    if not codes:
        return []
    return [
        u["unit_id"]
        for u in ctx.graph.get("units", [])
        if (u.get("medium_code") or "").lower() in {c.lower() for c in codes}
    ]


def _medium_from_query(ctx, parsed: ParsedQuery) -> str:
    tf = parsed.technical_filters or {}
    medium = tf.get("medium")
    if not medium and parsed.card and parsed.card.environment:
        medium = parsed.card.environment.medium
    return str(medium or "")


def graph_search(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Состав участков и компоненты: заполняет ksm_targets."""
    result = _empty()
    unit_ids = list(parsed.unit_ids or workspace.get("unit_ids", []))
    component_ids = list(parsed.component_ids or workspace.get("component_ids", []))

    # Нет явного участка, но запрос про объект/среду (H2S/CO2/коррозия):
    # выбираем участки по среде для «все детали для H2S»-запросов. Для
    # запросов с типами изделий (части + склад) состав не подмешиваем.
    medium = _medium_from_query(ctx, parsed)
    loaded_by_medium = False
    if not unit_ids and not component_ids and medium and not parsed.item_types:
        medium_units = _units_for_medium(ctx, medium)
        if medium_units:
            unit_ids = medium_units
            loaded_by_medium = True

    components: List[Dict[str, Any]] = []
    for uid in unit_ids:
        components.extend(ctx.components_of_unit(uid))
    for cid in component_ids:
        comp = ctx.components_by_id.get(cid)
        if comp:
            components.append(comp)

    if not components and parsed.unit_ids:
        for uid in parsed.unit_ids:
            result["missing"].append(
                "Не удалось загрузить состав участка %s." % uid
            )

    seen = set()
    targets = list(workspace.get("ksm_targets", []))
    for comp in components:
        ksm = comp.get("ksm_code")
        card = ctx.by_ksm.get(ksm)
        if card is None:
            card = ctx.card_for_component(comp)
        key = comp.get("component_id") or ksm
        if key in seen:
            continue
        seen.add(key)
        targets.append({
            "ksm": ksm,
            "component_id": comp.get("component_id"),
            "unit_id": comp.get("unit_id"),
            "card": card,
            "component": comp,
        })
        result["components"].append({
            "ksm_code": ksm,
            "mtr_code": ctx.card_mtr(card) if card else None,
            "name": (card or {}).get("name") or comp.get("designation"),
            "item_type": comp.get("item_type"),
            "status": "установлен на %s" % comp.get("unit_id"),
            "detail": "compatibility=%s" % comp.get("compatibility_status"),
            "source_id": comp.get("component_id"),
        })
        result["sources"].append(_source("object_graph", comp.get("component_id"),
                                         comp.get("unit_id")))

    # Граф контекстно задействован, даже если состав не разрешился по unit_id:
    # сверка установленных КСМ или выбор участков по среде запроса.
    if not components and (medium or parsed.not_installed):
        reason = []
        if medium:
            reason.append("контекст среды %s" % medium)
        if parsed.not_installed:
            reason.append("сверка установленных КСМ")
        result["sources"].append(_source(
            "object_graph", None,
            "; ".join(reason) or "граф объекта",
        ))
        if medium:
            result["text"] = "Граф объекта: участки по среде не найдены; сверен граф (%s)." % medium

    workspace["ksm_targets"] = targets
    workspace["graph_components"] = [t["component"] for t in targets if t.get("component")]
    result["text"] = result["text"] or "Граф объекта: %d компонентов (%d участков)." % (
        len(components), len(unit_ids))
    return result


# =========================================================
# REGULATION_LOOKUP
# =========================================================
_EVIDENCE_KIND = {
    "паспорт изделия": "passport_or_tu",
    "паспорт": "passport_or_tu",
    "ту": "TU",
    "внутренний лнд": "internal_lnd",
    "заключение эксперта": "expert_decisions",
    "проектная документация": "project_documentation",
}


def _medium_profile_for_medium(ctx, medium: str):
    med = str(medium or "").lower()
    if "h2s" in med and "co2" in med:
        code = "gas_h2s_co2"
    elif "h2s" in med or "сероводород" in med:
        code = "gas_h2s"
    elif "co2" in med:
        code = "gas_co2"
    elif "коррози" in med:
        code = "corrosive_medium"
    elif "природный" in med or "natural" in med:
        code = "natural_gas"
    else:
        return None
    for profile in ctx.regulation.get("medium_profiles", []):
        if profile.get("code") == code:
            return profile
    return None


def _evidence_sources(result, profile, unit_id: str = None) -> None:
    """Источники по требуемым доказательствам среды (паспорт, ТУ, ЛНД и т.п.)."""
    seen = set()
    for evidence in profile.get("required_evidence", []):
        kind = _EVIDENCE_KIND.get(str(evidence).strip().lower())
        if kind and kind not in seen:
            seen.add(kind)
            result["sources"].append(_source(kind, unit_id, evidence))


def regulation_lookup(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Нормативные предупреждения: среды H2S/CO2, заменённые ГОСТ, источники стандартов."""
    result = _empty()
    reg = ctx.regulation
    for limitation in reg.get("important_limitations", [])[:2]:
        result["warnings"].append(limitation)

    unit_ids = list(parsed.unit_ids or workspace.get("unit_ids", []))
    profiles = []
    for uid in unit_ids:
        profile = ctx.medium_profile(uid)
        if not profile:
            continue
        profiles.append(profile)
        code = profile.get("code", "")
        if code in ("gas_h2s", "gas_co2", "gas_h2s_co2", "corrosive_medium"):
            result["warnings"].append(
                "Среда %s требует %s; пригодность компонентов нельзя считать подтверждённой "
                "только по совпадению размеров." % (
                    profile.get("name", code),
                    ", ".join(profile.get("required_evidence", [])) or "документального подтверждения",
                )
            )
            result["sources"].append(_source("regulation", code, profile.get("name")))
            _evidence_sources(result, profile, uid)

    # Среда из самого запроса (без явного unit_id): профиль и его доказательства.
    medium = _medium_from_query(ctx, parsed)
    if not profiles and medium:
        profile = _medium_profile_for_medium(ctx, medium)
        if profile:
            code = profile.get("code", "")
            result["warnings"].append(
                "Среда %s требует %s; пригодность компонентов нельзя считать подтверждённой "
                "только по совпадению размеров." % (
                    profile.get("name", code),
                    ", ".join(profile.get("required_evidence", [])) or "документального подтверждения",
                )
            )
            result["sources"].append(_source("regulation", code, profile.get("name")))
            _evidence_sources(result, profile)

    # Источники стандартов по кандидатам каталога.
    cards = [t.get("card") for t in workspace.get("ksm_targets", [])]
    if not cards:
        cards = [c["card"] for c in workspace.get("candidates", [])]
    seen_std = set()
    for card in cards:
        if not card:
            continue
        standard = ctx.prop(card, "standard") or ctx.prop(card, "gost_tu")
        if standard:
            card_id = card.get("card_id")
            if card_id not in seen_std:
                seen_std.add(card_id)
                result["sources"].append(_source("standard", card_id, str(standard)))
            for rep in reg.get("replaced_standards", []):
                if str(standard).lower() == str(rep["standard"]).lower():
                    result["warnings"].append(
                        "ГОСТ %s заменён на %s (%s)." % (
                            rep["standard"], rep["replacement"], rep["status"]))
    return result


# =========================================================
# RULES_ENGINE (offline упрощённый матч-скоринг)
# =========================================================
def rules_engine(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Оценка соответствия кандидатов параметрам запроса."""
    result = _empty()
    candidates = workspace.get("candidates", [])
    for cand in candidates:
        card = cand["card"]
        score = _match_score(card, parsed)
        cand["score"] = score
        result["components"].append(_card_component(card, score, "оценка правил"))
    if candidates:
        result["sources"].append(_source(
            "matching_rules", "matching_rules.csv",
            "правила матчинга кандидатов по параметрам запроса",
        ))
    result["text"] = "Правила: оценено %d кандидатов." % len(candidates)
    return result


# =========================================================
# DOCUMENT_SEARCH
# =========================================================
def document_search(ctx, parsed: ParsedQuery, workspace: Dict[str, Any]) -> Dict[str, Any]:
    """Паспорта/ТУ для деталей участка: что есть, чего не хватает."""
    result = _empty()
    targets = workspace.get("ksm_targets", [])
    for target in targets:
        card = target.get("card")
        comp = target.get("component")
        if card is None:
            continue
        ksm = ctx.card_ksm(card)
        required = ctx.evidence_for_unit(target.get("unit_id") or "")
        doc = ctx.card_document(card) or {}
        doc_title = doc.get("title") or doc.get("document_type")
        found = [doc_title] if doc_title else []

        missing_evidence = [e for e in required if not _evidence_present(card, e)]
        status = []
        if missing_evidence:
            status.append("нет подтверждения: " + ", ".join(missing_evidence))
        result["components"].append({
            "ksm_code": ksm,
            "mtr_code": ctx.card_mtr(card),
            "name": card.get("name"),
            "item_type": card.get("item_type"),
            "status": "; ".join(status) or "документы на месте",
            "detail": ("компонент %s" % comp.get("component_id")) if comp else None,
            "source_id": card.get("card_id"),
        })
        for ev in required:
            kinds = [_EVIDENCE_KIND.get(ev.lower().strip(), "passport")]
            result["sources"].append(_source(kinds[0], ksm, ev))
        for card_target in targets:
            card = card_target.get("card")
            if card is None:
                continue
            standard = ctx.prop(card, "standard") or ctx.prop(card, "gost_tu")
            if standard:
                result["sources"].append(_source("standard", card.get("card_id"), str(standard)))
        if missing_evidence:
            result["missing"].extend(missing_evidence)
    result["text"] = "Документы: проверено %d карточек." % len(targets)
    return result


def _evidence_present(card: Dict[str, Any], evidence: str) -> bool:
    """Эвристика наличия подтверждающего документа по карточке."""
    present = (card.get("properties") or {}).get("required_evidence") or {}
    values = present.get("value") if isinstance(present, dict) else present
    if isinstance(values, list):
        return any(str(ev).lower() in str(v).lower() for v in values for ev in [evidence])
    return False
