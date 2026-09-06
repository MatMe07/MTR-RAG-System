# agent/tools/core_tools.py

import logging
import re
from typing import Any, Dict, List, Optional
import time

from .registry import register_tool
from ..core.state import AgentState
from ..answer.status import evaluate_candidate, candidate_tz_status
from .stock_filters import apply_stock_filters, describe_stock_filter
from ..medium import (
    MEDIUM_UNIT_CODES,
    medium_match,
    medium_unit_codes,
    steel_h2s_status,
)

log = logging.getLogger("mtr.agent.tools")

_CODE_RE = re.compile(r"\b(MTR|KSM)-[A-Z0-9][A-Z0-9-]*", re.IGNORECASE)


def _parsed_codes(parsed: Any) -> List[str]:
    """MTR/KSM-коды, упомянутые в запросе (FIND_BY_CODE)."""
    if parsed is None:
        return []
    return [m.group(0).upper() for m in _CODE_RE.finditer(parsed.original_query or "")]


def _matching_tolerances() -> Dict[str, float]:
    """Допуски матчинга из БД (БД > дефолт кода)."""
    try:
        from ..rules.dynamic_rules import get_dynamic_rules

        return get_dynamic_rules().matching_tolerances()
    except Exception:  # noqa: BLE001
        return {"dn": 0.1, "angle": 0.0, "wall_thickness": 0.15, "default": 0.1}


def _query_medium(state: AgentState) -> str:
    """Среда из запроса: фильтры > id участка > текст вопроса."""
    parsed = state.get("parsed")
    tf = getattr(parsed, "technical_filters", {}) or {}
    medium = tf.get("medium")
    if medium:
        return str(medium)
    for uid in (getattr(parsed, "unit_ids", []) or []):
        u = str(uid).lower()
        for kw in MEDIUM_UNIT_CODES:
            if kw in u:
                return kw
    q = str(getattr(parsed, "original_query", None) or "").lower()
    for kw in MEDIUM_UNIT_CODES:
        if kw in q:
            return kw
    return ""


# Карта «марка стали → h2s_suitability» из regulation_matrix.json (кеш).
_H2S_STEEL_RULES: Optional[Dict[str, str]] = None


def _h2s_steel_rules() -> Dict[str, str]:
    """Карта пригодности сталей для H2S (лениво из regulation_matrix.json)."""
    global _H2S_STEEL_RULES
    if _H2S_STEEL_RULES is None:
        rules: Dict[str, str] = {}
        try:
            import json as _json
            from pathlib import Path

            grid: Dict[str, Any] = {}
            for base in (Path(__file__).resolve().parents[5], Path.cwd()):
                p = base / "data" / "regulation" / "regulation_matrix.json"
                if p.exists():
                    grid = _json.loads(p.read_text(encoding="utf-8"))
                    break
            for profile in grid.get("material_profiles", []):
                key = str(profile.get("steel_grade") or "").strip().upper()
                status = profile.get("h2s_suitability")
                if key and status:
                    rules[key] = status
        except Exception:  # noqa: BLE001
            rules = {}
        _H2S_STEEL_RULES = rules
    return _H2S_STEEL_RULES


def _h2s_medium(tf: Dict[str, Any]) -> bool:
    """Активна ли H2S-среда в фильтрах запроса (h2s_confirmed или среда H2S)."""
    if tf.get("h2s_confirmed"):
        return True
    medium = str(tf.get("medium") or "").lower()
    return bool(medium) and ("h2s" in medium or "сероводород" in medium)


def _h2s_steel_rejection(parsed: Any) -> Optional[str]:
    """Предупреждение, если запрос под H2S явно требует несовместимую сталь (AQ004)."""
    tf = getattr(parsed, "technical_filters", {}) or {}
    if not _h2s_medium(tf):
        return None
    steel = tf.get("steel_grade")
    if not steel:
        return None
    if steel_h2s_status(steel, _h2s_steel_rules()) == "incompatible":
        return (
            f"Марка стали «{steel}» не пригодна для H2S среды: такие позиции "
            "исключены из подбора. Подходящие марки/подтверждение применимости "
            "нужно проверять по паспорту, ТУ и внутреннему ЛНД."
        )
    return None


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
    if score is not None:
        percent = round(score * 100)
        comp["match_score"] = score
        comp["match_percent"] = percent
        comp["tz_status"] = candidate_tz_status(percent)
    comp["matched_params"] = matched
    comp["mismatched_params"] = mismatched
    comp["missing_params"] = missing
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

    # ADD_COMPONENT: перечисленные до «добавь/поставь/установи» типы — уже
    # существующие детали схемы, а не фильтр каталога. Сужаем до целевого типа.
    if "ADD_COMPONENT" in (getattr(parsed, "intents", None) or []):
        from ..parsing.parsers.item_type_parser import narrow_add_target_types

        narrowed = narrow_add_target_types(
            getattr(parsed, "original_query", "") or "",
            getattr(parsed, "item_types", []) or [],
        )
        if narrowed:
            parsed.item_types = narrowed
            log.info("[catalog_search] ADD_COMPONENT target types: %s", narrowed)

    # Точечный поиск по MTR/KSM-коду: код в запросе — фильтр по коду карточки,
    # а не по геометрическим параметрам (иначе FIND_BY_CODE возвращает весь тип).
    codes = _parsed_codes(parsed)

    catalog = ctx.get_catalog()
    log.info("[catalog_search] Loaded %d cards from repository", len(catalog))

    if codes:
        for card in catalog:
            c = (card.get("codes") or {})
            if any(code in (str(c.get("mtr_code") or ""), str(c.get("ksm_code") or "")) for code in codes):
                matches.append({"card": card, "score": 1.0})
    else:
        for card in catalog:
            if _matches_filters(card, parsed):
                score = _match_score(card, parsed)
                matches.append({"card": card, "score": score})

    matches.sort(
        key=lambda x: (x["score"] is not None, x["score"] if x["score"] is not None else 0.0),
        reverse=True,
    )
    candidates = matches[:40]

    for m in candidates:
        card = m["card"]
        comp = _enrich_component(
            _card_component(card, m["score"], "совпадает по параметрам"),
            card, m["score"], parsed,
        )
        result["components"].append(comp)
        result["sources"].append(_source("catalog", card.get("card_id"), card.get("designation")))

        # Нормативная привязка карточки (ГОСТ из card.sources).
        std_ids = set()
        for src in (card.get("sources") or []):
            if src.get("type") != "standard":
                continue
            doc_id = src.get("document_id") or src.get("source_id")
            if not doc_id or doc_id in std_ids:
                continue
            std_ids.add(doc_id)
            frag = (src.get("source_fragment") or {}).get("text") or src.get("file_name") or doc_id
            result["sources"].append(_source("standard", doc_id, frag))

        result["sources"].append(_source(
            "passport_or_tu",
            card.get("card_id"),
            "паспорт изделия/ТУ: подтверждение применимости (в МВП документы не хранятся)",
        ))

    state["candidates"] = candidates

    # AQ004: запрос под H2S с явно несовместимой сталью — предупреждение
    # вместо молчаливого «ничего не найдено» (кандидаты отсеяны фильтром).
    rejection = _h2s_steel_rejection(parsed)
    if rejection:
        result["warnings"].append(rejection)

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
    parsed = state.get("parsed")

    # Сначала считаем остаток по всем кандидатам, затем применяем пороги
    # (quantity_min/quantity_max/on_stock) — см. apply_stock_filters.
    rows = []
    skipped = 0
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

        rows.append({
            "ksm_code": ksm,
            "mtr_code": (card.get("codes") or {}).get("mtr_code"),
            "name": card.get("name"),
            "item_type": card.get("item_type"),
            "quantity": qty or 0,
            "status": status,
            "source_id": card.get("card_id"),
            "_tool": "stock_query",
        })

    filtered = apply_stock_filters(rows, parsed)
    if len(filtered) < len(rows):
        skipped = len(rows) - len(filtered)
        result["warnings"].append(
            f"По порогу остатка отфильтровано позиций: {skipped}"
        )

    for row in filtered:
        ksm = row.get("ksm_code")
        result["components"].append(row)
        result["sources"].append(_source("stock", ksm, f"остаток: {row.get('quantity')}"))

    state["stock_rows"] = result["components"]
    result["text"] = (
        f"Проверено {len(candidates)} позиций"
        + (f"{describe_stock_filter(parsed)}" if describe_stock_filter(parsed) else "")
    )
    result["duration_ms"] = (time.time() - start) * 1000
    log.info(
        "[stock_query] Checked %d items (kept %d) in %.0fms",
        len(candidates), len(result["components"]), result["duration_ms"],
    )
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
    graph = ctx.get_graph()
    object_id = graph.get("object_id") or "gas_pipeline_object.json"
    object_name = graph.get("name") or "демо-объект"

    # Граф объекта и его проектная схема — всегда релевантные источники.
    result["sources"].append(_source("object_graph", object_id, object_name))
    result["sources"].append(
        _source("project_documentation", object_id, "проектная схема объекта"))
    result["sources"].append(
        _source("maintenance_policy", "MTR-TOIR-POLICY-001", "регламент ТОиР (черновой)"))

    unit_ids = list(getattr(parsed, "unit_ids", []) or [])
    component_ids = list(getattr(parsed, "component_ids", []) or [])

    # Резолв участка по среде, если явных id нет (напр. «участок с H2S»).
    if not unit_ids and not component_ids:
        want_codes = medium_unit_codes(_query_medium(state))
        for unit in graph.get("units", []):
            if unit.get("medium_code") in want_codes:
                unit_ids.append(unit.get("unit_id"))

    if not unit_ids and not component_ids:
        result["text"] = f"Параметры участка/компонента не указаны; доступен граф: {object_name}"
        result["duration_ms"] = (time.time() - start) * 1000
        log.info("[graph_search] No unit_ids/component_ids provided; object sources only")
        return result

    components = []
    for uid in unit_ids:
        components.extend(ctx.get_components_by_unit(uid))
    for cid in component_ids:
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
                "unit_id": comp.get("unit_id"),
            })
            result["sources"].append(_source("object_graph", comp.get("component_id"), comp.get("unit_id")))

        # Статус применимости в графе требует паспорт изделия.
        status = comp.get("compatibility_status") or ""
        if "passport" in status:
            result["sources"].append(
                _source("passport", comp.get("component_id"),
                        "паспорт изделия (статус в графе требует паспорт)"))

    # История эксплуатации для рисковой зоны (агрессивная среда/коррозия).
    risk_medium = _query_medium(state).lower()
    risk_ctx = any(k in risk_medium for k in ("h2s", "co2", "коррозион", "риск", "важн"))
    risk_ctx = risk_ctx or any(
        k in str(u).lower() for u in unit_ids for k in ("h2s", "co2", "corr", "sour"))
    if risk_ctx:
        for uid in unit_ids:
            result["sources"].append(
                _source("maintenance_history", uid,
                        "риски по истории эксплуатации (МВП: расчётно)"))

    state["ksm_targets"] = targets
    result["text"] = f"Найдено {len(components)} компонентов"
    result["duration_ms"] = (time.time() - start) * 1000
    log.info("[graph_search] Found %d components, %d targets in %.0fms",
        len(components), len(targets), result["duration_ms"])
    return result


def _decode_docs(reg: Dict[str, Any], parsed: Any, cards: List[Dict]) -> Dict[str, Any]:
    """Расшифровка ГОСТ/ТУ по компонентам: найдено / отсутствует (AQ039/AQ040).

    Индексирует reg["sources"] по ГОСТ-обозначению («ГОСТ 8732-2025») и по
    source_id, затем для каждой карточки кандидата собирает:
      - docs_found:   ГОСТ/ТУ карточки, найденные в реестре (title + scope);
      - docs_missing: ГОСТ карточки, которых нет в реестре (без расшифровки).
    """
    sources_by_std: Dict[str, dict] = {}
    sources_by_id: Dict[str, dict] = {}
    for src in reg.get("sources", []):
        std = str(src.get("standard") or "").strip()
        if std:
            sources_by_std[std.lower()] = src
        sid = str(src.get("source_id") or "").strip()
        if sid:
            sources_by_id[sid.lower()] = src

    found: Dict[str, List[dict]] = {}
    missing: Dict[str, List[str]] = {}
    cards = list(cards or [])

    def prop(card: Dict[str, Any], key: str) -> Any:
        v = (card.get("properties") or {}).get(key)
        if isinstance(v, dict):
            return v.get("value")
        return v

    if not cards:
        norm = getattr(parsed, "normative", None) or {}
        gost = _norm_gost(norm)
        if gost:
            _classify_gost(gost, sources_by_std, sources_by_id, found, missing, "_query")
    else:
        for card in cards:
            name = card.get("name") or card.get("designation") or card.get("card_id")
            standards = set()
            for src in (card.get("sources") or []):
                doc_id = src.get("document_id") or src.get("source_id")
                if doc_id:
                    standards.add(doc_id)
            gost = prop(card, "gost_tu") or prop(card, "applicable_standards") or prop(card, "standard")
            if gost:
                standards.update(gost if isinstance(gost, list) else [gost])
            for std in standards:
                _classify_gost(std, sources_by_std, sources_by_id, found, missing, str(name))
    return {"docs_found": found, "docs_missing": missing}


def _norm_gost(norm: Any) -> Optional[str]:
    if not norm:
        return None
    if isinstance(norm, dict):
        return norm.get("gost_tu")
    try:
        return getattr(norm, "gost_tu", None)
    except Exception:  # noqa: BLE001
        return None


def _classify_gost(std, sources_by_std, sources_by_id, found, missing, label):
    raw = str(std or "").strip()
    if not raw:
        return
    key = raw.lower()
    src = sources_by_id.get(key) or sources_by_std.get(key)
    if src:
        entry = {
            "standard": src.get("standard") or raw,
            "source_id": src.get("source_id"),
            "title": src.get("title") or "",
            "scope": src.get("scope") or "",
            "status": src.get("status") or "",
        }
        found.setdefault(label, [])
        if entry not in found[label]:
            found[label].append(entry)
    else:
        missing.setdefault(label, [])
        if raw not in missing[label]:
            missing[label].append(raw)


def _fmt_docs(r: Dict[str, Any]) -> str:
    """Форматирует docs_found/docs_missing в текст для ответа."""
    found = r.get("docs_found") or {}
    missing = r.get("docs_missing") or {}
    lines = []
    found_labels = found or {}
    for label, docs in found_labels.items():
        for doc in docs:
            title = doc.get("title") or doc.get("standard") or ""
            scope = doc.get("scope") or ""
            line = f"• {doc.get('standard')} — {title}"
            if scope:
                line += f": {scope}"
            lines.append(line)
    missing_labels = {k: v for k, v in (missing or {}).items() if v}
    for label, docs in missing_labels.items():
        for doc in docs:
            lines.append(f"• {doc} — расшифровка отсутствует в реестре")
    return "\n".join(lines)


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
    parsed = state.get("parsed")

    for limitation in reg.get("important_limitations", [])[:3]:
        result["warnings"].append(limitation)

    # Профили среды: требования по документам/ЛНД для релевантной среды.
    medium = _query_medium(state).lower()
    want_codes = medium_unit_codes(medium) | ({medium} if medium else set())
    for profile in reg.get("medium_profiles", []):
        code = str(profile.get("code") or "").lower()
        if code not in want_codes and not (medium and medium in code):
            continue
        evidence = profile.get("required_evidence") or []
        if "ТУ" in evidence:
            result["sources"].append(_source("TU", code, "технические условия на изделие"))
        if "внутренний ЛНД" in evidence:
            result["sources"].append(
                _source("internal_lnd", code, "внутренний ЛНД по применимости к среде"))
        if "заключение эксперта" in evidence:
            result["sources"].append(_source("expert_decisions", code, "заключение эксперта по среде"))
        if "паспорт изделия" in evidence:
            result["sources"].append(
                _source("passport", code, "паспорт изделия (требование профиля среды)"))

    # Расшифровка ГОСТ/ТУ по компонентам (AQ039/AQ040): найденные/отсутствующие
    # нормативные документы по карточкам-кандидатам или явному ГОСТ из запроса.
    cards = [m.get("card") for m in (state.get("candidates") or []) if m and m.get("card")]
    docs = _decode_docs(reg, parsed, cards)
    result["docs_found"] = docs["docs_found"]
    result["docs_missing"] = docs["docs_missing"]

    result["sources"].append(_source("regulation", "regulation_matrix.json"))
    if docs["docs_found"] or docs["docs_missing"]:
        decode_text = _fmt_docs(docs)
        result["text"] = decode_text or result["text"]
        result["normative_detail"] = decode_text
    else:
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

    def text_val(key):
        v = props.get(key)
        if isinstance(v, dict):
            v = v.get("value")
        return v

    def num_alias(key):
        # Переход: карточка хранит диаметры в d1/d2, поля dn нет — для сравнения
        # запрошенный dn (равен большему диаметру) берём из d1.
        got = num(key)
        if got is None and key == "dn" and num("d1") is not None and num("d2") is not None:
            return num("d1")
        return got

    def tol(key: str) -> float:
        tolerances = _matching_tolerances()
        return tolerances.get(key, tolerances.get("default", 0.1))

    if tf.get("dn") and num_alias("dn"):
        if abs(num_alias("dn") - tf["dn"]) > abs(tf["dn"]) * tol("dn"):
            return False

    # Переходы (AQ006): проверяем ОБА диаметра. Карточка перехода хранит
    # наружные диаметры в d1/d2 (поле dn у перехода отсутствует), поэтому
    # без d1/d2-проверки фильтр DN для переходов не работал вовсе.
    if tf.get("d1") is not None or tf.get("d2") is not None:
        dn_tol = min(tol("dn"), 0.02)
        for key in ("d1", "d2"):
            want = tf.get(key)
            if want is None:
                continue
            got = num(key)
            if got is None or abs(got - want) > abs(want) * dn_tol:
                return False

    if tf.get("angle") and num("angle"):
        if abs(num("angle") - tf["angle"]) > abs(tf["angle"]) * tol("angle"):
            return False

    if tf.get("wall_thickness") and num("wall_thickness"):
        if abs(num("wall_thickness") - tf["wall_thickness"]) > abs(tf["wall_thickness"]) * tol("wall_thickness"):
            return False

    # PN: канон = PN-класс (число). Строгий фильтр: несовпадение PN отсекает карточку.
    if tf.get("pn") and num("pn"):
        if abs(num("pn") - tf["pn"]) > abs(tf["pn"]) * tol("pn"):
            return False

    # H2S (AQ002/AQ004): марки стали, не пригодные для H2S-среды, отсекаются
    # жёстко (сталь 20 и пр.) — иначе они проходили бы как «соответствует».
    if _h2s_medium(tf):
        card_steel = text_val("steel_grade")
        if card_steel is not None and steel_h2s_status(
            card_steel, _h2s_steel_rules()
        ) == "incompatible":
            return False

    item_types = getattr(parsed, "item_types", [])
    if item_types and card.get("item_type") not in item_types:
        return False

    return True


def _match_score(card: Dict, parsed: Any) -> Optional[float]:
    props = card.get("properties", {})
    tf = getattr(parsed, "technical_filters", {}) or {}

    def num(key):
        v = (props.get(key) or {}).get("value")
        return v if isinstance(v, (int, float)) else None

    def num_alias(key):
        # Переход (AQ006): карточка хранит диаметры в d1/d2; запрошенный dn
        # (равен большему диаметру) сравниваем с d1 карточки.
        got = num(key)
        if got is None and key == "dn" and num("d1") is not None and num("d2") is not None:
            return num("d1")
        return got

    def text_val(key):
        v = props.get(key)
        if isinstance(v, dict):
            v = v.get("value")
        return v

    hits = 0.0
    checks = 0.0

    tolerances = _matching_tolerances()
    default_tol = tolerances.get("default", 0.1)

    for key in ["dn", "angle", "wall_thickness", "pn", "d1", "d2"]:
        want = tf.get(key)
        if want is not None:
            checks += 1
            got = num_alias(key)
            tol = tolerances.get(key, default_tol)
            if key in ("d1", "d2"):
                # Переход (AQ006): оба диаметра строго (2%), иначе посторонние
                # переходы 76x57/133x89 давали бы высокий балл.
                tol = min(tol, 0.02)
            if got is not None and abs(got - want) <= max(abs(want), 1e-9) * tol:
                hits += 1

    # Текстовые параметры: среда и марка стали влияют на рейтинг (H2S-кандидаты выше).
    if tf.get("medium"):
        checks += 1
        got = text_val("medium")
        if got is not None and medium_match(tf["medium"], got):
            hits += 1

    if tf.get("steel_grade"):
        checks += 1
        got = text_val("steel_grade")
        if got is not None and str(got).strip().upper() == str(tf["steel_grade"]).strip().upper():
            hits += 1

    if tf.get("material"):
        checks += 1
        got = text_val("material")
        if got is not None and str(got).strip().lower() == str(tf["material"]).strip().lower():
            hits += 1

    # H2S-совместимость марки (AQ002): при активной H2S-среде пригодность стали
    # учитывается даже без явной марки в запросе (13ХФА выше 09ГСФ/09Г2С).
    if _h2s_medium(tf):
        checks += 1
        got = text_val("steel_grade")
        if got is not None and steel_h2s_status(
            got, _h2s_steel_rules()
        ) == "suitable":
            hits += 1

    item_types = getattr(parsed, "item_types", [])
    if item_types:
        checks += 1
        if card.get("item_type") in item_types:
            hits += 1

    # Нет ни одного параметрического фильтра (только тип, либо вообще ничего):
    # скоринг невозможен. Совпадение одного лишь типа не должно давать 100%
    # «соответствует» — иначе план/комплект без параметров светится матчем.
    param_checks = sum(
        1 for key in ("dn", "angle", "wall_thickness", "pn", "d1", "d2")
        if tf.get(key) is not None
    ) + sum(
        1 for key in ("medium", "steel_grade", "material")
        if tf.get(key)
    )
    if param_checks == 0:
        return None
    return hits / checks if checks > 0 else 0.5
