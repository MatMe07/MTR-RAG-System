"""Форматтеры и утилиты."""

from datetime import datetime, date
from typing import Any


def fmt_date(value) -> str:
    if not value:
        return "—"
    if isinstance(value, (datetime, date)):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return value
    return str(value)


def fmt_number(value, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
        if num == int(num):
            return f"{int(num)}{suffix}"
        return f"{num:.2f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def confidence_badge(confidence: float) -> str:
    if confidence is None:
        cls = "conf-low"
        label = "нет данных"
    elif confidence >= 0.8:
        cls = "conf-high"
        label = f"{confidence:.0%}"
    elif confidence >= 0.5:
        cls = "conf-mid"
        label = f"{confidence:.0%}"
    else:
        cls = "conf-low"
        label = f"{confidence:.0%}"
    return f'<span class="{cls}">{label}</span>'


def component_to_row(comp: dict, rank: int = None) -> dict:
    """Нормализует компонент из ответа агента в строку для таблицы."""
    props = comp.get("properties") or {}
    stock = comp.get("stock_qty") or comp.get("quantity") or (props.get("stock_qty") or {}).get("value")
    return {
        "Ранг": rank or comp.get("rank", ""),
        "Код МТР": comp.get("mtr_code", ""),
        "Код КСМ": comp.get("ksm_code", ""),
        "Тип": comp.get("item_type", ""),
        "DN": comp.get("dn", props.get("dn", {}).get("value", "")) if isinstance(props.get("dn", {}), dict) else props.get("dn", ""),
        "Статус": comp.get("status", ""),
        "Наличие": stock if stock is not None else "",
        "Источник": comp.get("source_id", ""),
    }


def safe_text(value) -> str:
    return value if value else ""


def search_rows(results: list, start_rank: int = 1) -> list[dict]:
    """Преобразует результаты поиска в строки для таблицы."""
    rows = []
    for idx, comp in enumerate(results, start_rank):
        props = comp.get("properties") or {}
        stock = comp.get("quantity")
        if stock is None:
            stock = comp.get("stock_qty")
        if stock is None and isinstance(props.get("stock_qty"), dict):
            stock = props["stock_qty"].get("value")
        rows.append(
            {
                "Ранг": idx,
                "Код МТР": comp.get("mtr_code", ""),
                "Код КСМ": comp.get("ksm_code", ""),
                "Тип": comp.get("item_type", ""),
                "Наименование": comp.get("name", ""),
                "Совпадение %": round((comp.get("score") or 0) * 100, 1),
                "Статус": comp.get("status", ""),
                "Наличие": fmt_number(stock) if stock is not None else "",
                "source_id": comp.get("source_id", ""),
            }
        )
    return rows


def parse_params(params: list) -> list[dict]:
    """Извлекает параметры из ответа component API в строки таблицы."""
    rows = []
    for p in params or []:
        rows.append(
            {
                "Параметр": p.get("field_name", ""),
                "Значение": p.get("normalized_value") or p.get("raw_value", ""),
                "Единица": p.get("unit", ""),
                "Уверенность": p.get("confidence", 0),
                "Статус": "проверено" if p.get("is_verified") else "не проверено",
            }
        )
    return rows