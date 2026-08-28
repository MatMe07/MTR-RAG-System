# agent/rules/conditions.py
"""Интерпретатор logical_conditions правил валидации (ValidationRule).

Схема условия (JSON в колонке validation_rules.logical_conditions):

    [
      {
        "when": [
          {"param": "dn", "op": "gte", "value": 300},
          {"param": "medium", "op": "eq", "value": "h2s"}
        ],
        "then_require": ["steel_grade", "wall_thickness"],
        "then_forbid": ["angle"]
      }
    ]

`when` — один объект или список объектов сравнения (все должны выполняться).
Поддерживаемые операции: eq, neq, gt, gte, lt, lte, in, not_in.
При сравнении числовые значения сравниваются как числа, иначе — строки (lower).
`then_require` — параметры, которые ОБЯЗАНЫ присутствовать, когда when истинно.
`then_forbid` — параметры, которые ЗАПРЕЩЕНЫ, когда when истинно.

Возвращаемые предупреждения — человекочитаемые строки на русском.
"""

from typing import Any, Dict, List, Optional

_LOGICAL_OPS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in"}


def _to_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", "."))
        except (ValueError, AttributeError):
            return None
    return None


def _clean(value: Any) -> str:
    return str(value).strip().lower()


def _compare(op: str, got: Any, want: Any) -> bool:
    got_num = _to_number(got)
    want_num = _to_number(want)
    if op in {"in", "not_in"}:
        wanted = want if isinstance(want, list) else [want]
        values = [_clean(v) for v in wanted]
        present = _clean(got) in values
        return not present if op == "not_in" else present
    if got_num is not None and want_num is not None:
        if op == "eq":
            return got_num == want_num
        if op == "neq":
            return got_num != want_num
        if op == "gt":
            return got_num > want_num
        if op == "gte":
            return got_num >= want_num
        if op == "lt":
            return got_num < want_num
        if op == "lte":
            return got_num <= want_num
        return False
    g, w = _clean(got), _clean(want)
    if op == "eq":
        return g == w
    if op == "neq":
        return g != w
    if op == "gt":
        return g > w
    if op == "gte":
        return g >= w
    if op == "lt":
        return g < w
    if op == "lte":
        return g <= w
    return False


def _conditions_list(conditions: Any) -> List[Dict[str, Any]]:
    if isinstance(conditions, dict):
        return [conditions]
    if isinstance(conditions, list):
        return conditions
    return []


def _match_when(when: Any, tf: Dict[str, Any]) -> bool:
    if not when:
        return True
    comparisons = when if isinstance(when, list) else [when]
    for cmp_ in comparisons:
        param = (cmp_.get("param") or "").strip()
        op = (cmp_.get("op") or "eq").strip().lower()
        if not param or op not in _LOGICAL_OPS:
            continue
        got = tf.get(param)
        if got is None:
            return False
        if not _compare(op, got, cmp_.get("value")):
            return False
    return True


def evaluate_logical_conditions(
    item_type: str,
    conditions: Any,
    tf: Dict[str, Any],
    labels: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Оценивает logical_conditions для типа детали относительно параметров запроса."""
    labels = labels or {}
    warnings: List[str] = []
    for cond in _conditions_list(conditions):
        if not isinstance(cond, dict):
            continue
        if not _match_when(cond.get("when"), tf):
            continue
        context = _context_text(cond.get("when"), tf)
        for param in cond.get("then_require", []) or []:
            if not tf.get(param):
                warnings.append(
                    f"Для типа «{item_type}»{context} обязательно указать параметр "
                    f"{labels.get(param, param)}."
                )
        for param in cond.get("then_forbid", []) or []:
            if tf.get(param):
                warnings.append(
                    f"Для типа «{item_type}»{context} параметр "
                    f"{labels.get(param, param)} недопустим."
                )
    return warnings


def _context_text(when: Any, tf: Dict[str, Any]) -> str:
    """Краткое пояснение условия «при …» для текста предупреждения."""
    if not when:
        return ""
    comparisons = when if isinstance(when, list) else [when]
    parts: List[str] = []
    for cmp_ in comparisons:
        param = (cmp_.get("param") or "").strip()
        if not param:
            continue
        got = tf.get(param)
        op = (cmp_.get("op") or "eq").strip().lower()
        want = cmp_.get("value")
        if op in {"eq", "in"} and got is not None:
            parts.append(f"при {param} = {_clean(got)}")
        elif op in {"neq", "not_in"} and got is not None:
            parts.append(f"при {param} ≠ {_clean(got)}")
        elif got is not None:
            parts.append(f"при {param} {op} {_clean(want)}")
    if not parts:
        return ""
    return " " + ", ".join(parts)