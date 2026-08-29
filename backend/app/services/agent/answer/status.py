# agent/answer/status.py

"""ТЗ-статусы и детерминация финального статуса ответа.

Реализация ЭТАПА 5 (5A.2 StatusDeterminator, 5B структура JSON-ответа).
ТЗ раздел 9: соответств. / потенциальный аналог / не соответствует / нет данных /
требует проверки / требует экспертной проверки.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import AgentAnswer, AgentComponent, AgentSource
from app.services.agent.intent.matrix import BLOCKER_FIELDS

STATUS_MATCH = "соответствует"
STATUS_ANALOG = "потенциальный аналог"
STATUS_MISMATCH = "не соответствует"
STATUS_NOT_FOUND = "нет данных"
STATUS_UNCLEAR = "требует проверки"
STATUS_EXPERT = "требует экспертной проверки"

# Критические предупреждения: только фразы, сигнализирующие о блокирующем
# дефекте данных/подтверждения. Обычные дисклеймеры (ГОСТ не присваивает КСМ,
# соответствие H2S нельзя подтверждать только ГОСТом) НЕ эскалируют.
_CRITICAL_WARNING_MARKERS = (
    "противореч",
    "недостаточно данных",
    "не подтвержд",
    "не удалось подтвердить",
    "критич",
    "требуется эксперт",
    "блокиру",
    "приостанов",
)

PARAM_LABELS = {
    "item_type": "тип изделия",
    "dn": "DN",
    "pn": "PN",
    "angle": "угол",
    "wall_thickness": "стенка",
    "strength_class": "класс прочности",
    "steel_grade": "марка стали",
    "medium": "среда",
    "material": "материал",
    "standard": "стандарт",
    "gost_tu": "ТУ/ГОСТ",
}

_NUMERIC_TOLERANCE = 0.1


def _param_labels() -> Dict[str, str]:
    """Лейблы параметров: БД (param_labels) поверх дефолта кода."""
    try:
        from ..rules.dynamic_rules import get_dynamic_rules

        labels = get_dynamic_rules().param_labels()
        merged = dict(PARAM_LABELS)
        if isinstance(labels, dict):
            merged.update(labels)
        return merged
    except Exception:  # noqa: BLE001
        return dict(PARAM_LABELS)


def _numeric_tolerance() -> float:
    """Числовой допуск сравнения (База данных > дефолт кода)."""
    try:
        from ..rules.dynamic_rules import get_dynamic_rules

        return get_dynamic_rules().numeric_tolerance()
    except Exception:  # noqa: BLE001
        return _NUMERIC_TOLERANCE


def candidate_tz_status(match_percent: Optional[float]) -> str:
    """ТЗ-статус отдельного кандидата по проценту совпадения."""
    percent = match_percent or 0.0
    if percent >= 95:
        return STATUS_MATCH
    if percent >= 70:
        return STATUS_ANALOG
    return STATUS_MISMATCH


def evaluate_candidate(
    card: Dict[str, Any],
    parsed: Any,
) -> Tuple[List[str], List[str], List[str]]:
    """Сравнивает запрошенные параметры с карточкой.

    Возвращает (matched, mismatched, missing) — человекочитаемые имена
    параметров. Числовые значения сравниваются с допуском 10%.
    """
    matched: List[str] = []
    mismatched: List[str] = []
    missing: List[str] = []

    props = card.get("properties", {}) or {}
    tf = getattr(parsed, "technical_filters", {}) or {}
    labels = _param_labels()
    # Только пользовательские параметры: служебные ключи парсера
    # (raw_value, h2s_confirmed и т.п.) не участвуют в сравнении.
    tf = {k: v for k, v in tf.items() if k in labels}
    item_types = getattr(parsed, "item_types", []) or []

    def prop_val(key: str) -> Any:
        v = props.get(key)
        if isinstance(v, dict):
            val = v.get("value")
            if val is None:
                val = v.get("normalized")
            return val
        return v

    checks: List[tuple] = []
    seen_keys: set = set()
    if item_types:
        checks.append(("item_type", item_types[0], card.get("item_type")))
        seen_keys.add("item_type")
    for key, want in tf.items():
        if key in seen_keys:
            continue
        seen_keys.add(key)
        checks.append((key, want, prop_val(key)))

    for key, want, got in checks:
        label = labels.get(key, key)
        if got is None or (isinstance(got, str) and not got.strip()):
            missing.append(label)
            continue

        if key == "item_type":
            ok = str(got).strip().lower() == str(want).strip().lower()
        elif isinstance(got, (int, float)):
            if isinstance(want, (int, float)):
                tol = _numeric_tolerance()
                ok = abs(got - want) <= abs(want) * tol
            else:
                ok = str(got).strip().lower() == str(want).strip().lower()
        else:
            ok = str(got).strip().lower() == str(want).strip().lower()

        (matched if ok else mismatched).append(label)

    return matched, mismatched, missing


def _is_critical_warning(warning: str) -> bool:
    low = str(warning).lower()
    return any(marker in low for marker in _CRITICAL_WARNING_MARKERS)


def determine_status(
    components: List[AgentComponent],
    warnings: List[str],
    errors: Optional[List[Any]] = None,
    has_request: bool = True,
) -> str:
    """Последовательность проверок по 5A.2."""
    for error in errors or []:
        code = str(
            error.get("code") if isinstance(error, dict) else error
        ).upper()
        if "STOP" in code:
            return STATUS_EXPERT
        if "INVALID" in code:
            return STATUS_UNCLEAR

    if not components:
        return STATUS_NOT_FOUND if has_request else STATUS_UNCLEAR

    best = max((c.match_score or 0.0) for c in components)
    status = candidate_tz_status(best * 100)

    if any(_is_critical_warning(w) for w in warnings):
        return STATUS_EXPERT

    return status


def _request_present(parsed: Any) -> bool:
    if parsed is None:
        return False
    return bool(
        getattr(parsed, "component_ids", None)
        or getattr(parsed, "unit_ids", None)
        or getattr(parsed, "item_types", None)
        or getattr(parsed, "technical_filters", None)
    )


def build_recommendations(
    status: str,
    warnings: List[str],
    missing: List[str],
) -> List[str]:
    """Рекомендации для ТЗ-ответа (поле recommendations)."""
    recs: List[str] = []
    missing = list(dict.fromkeys(missing))
    if status == STATUS_MATCH and warnings:
        recs.append("Проверьте предупреждения перед принятием решения.")
    if status == STATUS_ANALOG:
        recs.append(
            "Проверьте взаимозаменяемость аналога: геометрия, давление и среда."
        )
    if status == STATUS_MISMATCH:
        recs.append(
            "Существенные расхождения параметров: уточните требования к детали "
            "или обратитесь к эксперту."
        )
    if status == STATUS_NOT_FOUND:
        recs.append("В каталоге нет подходящих позиций: измените параметры запроса.")
    if status == STATUS_UNCLEAR:
        recs.append("Уточните параметры запроса: тип изделия, DN, PN, среда.")
    if status == STATUS_EXPERT:
        recs.append("Требуется экспертная проверка: критические параметры не подтверждены.")
    if missing:
        recs.append("Уточните недостающие параметры: " + ", ".join(missing) + ".")
    return recs


def expert_review_id() -> str:
    """Формирует идентификатор запроса на экспертную проверку."""
    import uuid

    return f"req-{date.today().isoformat()}-{uuid.uuid4().hex[:4]}"


SOURCE_TYPE_MAP = {
    "catalog": "excel",
    "stock": "excel",
    "excel": "excel",
    "passport": "passport",
    "lnd": "lnd",
    "object_graph": "excel",
    "regulation": "standard",
    "standard": "standard",
    "tu": "document",
    "expert_decisions": "expert",
}


def format_sources(sources: List[AgentSource]) -> List[Dict[str, Any]]:
    """SourceFormatter: сырые источники → ТЗ-структура sources.

    {type, document_id, page, row, section, lnd_section, description}
    """
    items: List[Dict[str, Any]] = []
    seen: set = set()
    for s in sources or []:
        if isinstance(s, dict):
            kind = s.get("kind")
            sid = s.get("id")
            frag = s.get("fragment")
        else:
            kind = getattr(s, "kind", None)
            sid = getattr(s, "id", None)
            frag = getattr(s, "fragment", None)
        if kind is None:
            continue
        t = SOURCE_TYPE_MAP.get(kind, kind)
        key = (t, sid)
        if key in seen:
            continue
        seen.add(key)
        item: Dict[str, Any] = {"type": t}
        if t == "passport":
            item["document_id"] = sid
        elif t == "lnd":
            item["lnd_section"] = sid
        elif t in ("excel", "object_graph"):
            item["row"] = sid
        elif t == "standard":
            item["document_id"] = sid
        else:
            item["document_id"] = sid
        if frag:
            item["description"] = frag
        items.append(item)
    return items