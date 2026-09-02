# tools/stock_filters.py
"""Применение складских порогов (stock_filters) к строкам с остатком.

Парсер кладёт quantity_min/quantity_max/stock_category/on_stock в
parsed.stock_filters (см. parser._extract_stock_filters). Ранее ни один
инструмент их не потреблял — пороговые запросы («больше 50», «меньше 3»)
возвращали случайные остатки. Этот модуль — единая точка применения.
"""

from typing import Any, Dict, List


def _thresholds(parsed: Any) -> dict:
    stock_filters = getattr(parsed, "stock_filters", None) or {}
    return {
        "quantity_min": stock_filters.get("quantity_min"),
        "quantity_max": stock_filters.get("quantity_max"),
        "min_strict": stock_filters.get("quantity_min_strict", False),
        "max_strict": stock_filters.get("quantity_max_strict", False),
    }


def passes_stock_filter(qty: Any, parsed: Any) -> bool:
    """True, если остаток проходит пороги quantity_min/quantity_max."""
    if parsed is None or qty is None:
        return True
    thr = _thresholds(parsed)
    qmin, qmax = thr["quantity_min"], thr["quantity_max"]
    if qmin is not None:
        if (thr["min_strict"] and qty <= qmin) or (not thr["min_strict"] and qty < qmin):
            return False
    if qmax is not None:
        if (thr["max_strict"] and qty >= qmax) or (not thr["max_strict"] and qty > qmax):
            return False
    return True


def apply_stock_filters(rows: List[Dict[str, Any]], parsed: Any) -> List[Dict[str, Any]]:
    """Фильтрует строки по порогам остатка из parsed.stock_filters/on_stock.

    Работает с реальным остатком (field "quantity"), а не с рекомендуемыми
    значениями. Если порог не задан — строка не отбрасывается.
    """
    if parsed is None:
        return list(rows)

    def passes(row: Dict[str, Any]) -> bool:
        qty = row.get("quantity")
        if qty is None:
            # Без указанного остатка порог количества применить нельзя —
            # считаем проходящей, чтобы не терять данные.
            return True
        return passes_stock_filter(qty, parsed)

    return [r for r in rows if passes(r)]


def describe_stock_filter(parsed: Any) -> str:
    """Человекочитаемое описание применённого порога (для текста ответа/лога)."""
    stock_filters = getattr(parsed, "stock_filters", None) or {}
    parts = []
    if stock_filters.get("quantity_min") is not None:
        parts.append(f"остаток ≥ {stock_filters['quantity_min']}")
    if stock_filters.get("quantity_max") is not None:
        parts.append(f"остаток ≤ {stock_filters['quantity_max']}")
    if not parts:
        return ""
    return " (" + ", ".join(parts) + ")"
