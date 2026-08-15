"""Clarification form for incomplete engineering queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class ClarificationField:
    key: str
    label: str
    kind: str = "text"


FIELD_SPECS = {
    "item_type": ClarificationField("item_type", "Тип изделия"),
    "subtype": ClarificationField("subtype", "Подтип изделия"),
    "dn": ClarificationField("dn", "DN / наружный диаметр", "number"),
    "d1": ClarificationField("d1", "Первый диаметр", "number"),
    "d2": ClarificationField("d2", "Второй диаметр", "number"),
    "dn_out": ClarificationField("dn_out", "Выходной DN", "number"),
    "angle": ClarificationField("angle", "Угол", "number"),
    "wall_thickness": ClarificationField(
        "wall_thickness", "Толщина стенки, мм", "number"
    ),
    "pn": ClarificationField("pn", "PN / Ру", "number"),
    "steel_grade": ClarificationField("steel_grade", "Марка стали"),
    "strength_class": ClarificationField("strength_class", "Класс прочности"),
    "medium": ClarificationField("medium", "Рабочая среда"),
    "inner_coating": ClarificationField(
        "inner_coating", "Внутреннее покрытие", "boolean"
    ),
    "outer_coating": ClarificationField(
        "outer_coating", "Наружное покрытие", "boolean"
    ),
    "gost_tu": ClarificationField("gost_tu", "ГОСТ / ТУ"),
}

FIELD_ALIASES = {
    "type": "item_type",
    "product_type": "item_type",
    "diameter": "dn",
    "dn_or_diameter": "dn",
    "geometry.dn": "dn",
    "geometry.dn_out": "dn_out",
    "geometry.angle": "angle",
    "geometry.wall_thickness": "wall_thickness",
    "pressure": "pn",
    "pressure.pn": "pn",
    "material": "steel_grade",
    "material.steel_grade": "steel_grade",
    "material.strength_class": "strength_class",
    "environment.medium": "medium",
    "coating.inner_coating": "inner_coating",
    "coating.outer_coating": "outer_coating",
    "standard": "gost_tu",
    "references": "gost_tu",
}

EXPANDED_FIELDS = {
    "d1_d2": ("d1", "d2"),
    "geometry": ("dn", "wall_thickness"),
    "full_card": ("item_type", "dn", "wall_thickness"),
}


def normalize_missing_fields(missing: list[str]) -> list[ClarificationField]:
    """Map backend field names to a stable, de-duplicated UI contract."""
    fields: list[ClarificationField] = []
    seen: set[str] = set()
    for raw_name in missing:
        name = str(raw_name).strip().casefold()
        keys = EXPANDED_FIELDS.get(name)
        if keys is None:
            keys = (FIELD_ALIASES.get(name, name.split(".")[-1]),)
        for key in keys:
            if key in FIELD_SPECS and key not in seen:
                fields.append(FIELD_SPECS[key])
                seen.add(key)
    return fields


def build_clarified_query(original_query: str, values: dict[str, Any]) -> str:
    """Append only explicitly supplied values to the original user query."""
    parts: list[str] = []
    text_prefixes = {
        "item_type": "тип изделия",
        "subtype": "подтип",
        "steel_grade": "марка стали",
        "strength_class": "класс прочности",
        "medium": "среда",
        "gost_tu": "норматив",
    }
    numeric_prefixes = {
        "dn": "DN",
        "d1": "первый диаметр",
        "d2": "второй диаметр",
        "dn_out": "выходной DN",
        "angle": "угол",
        "wall_thickness": "толщина стенки",
        "pn": "PN",
    }

    for key, prefix in text_prefixes.items():
        value = values.get(key)
        if value is not None and str(value).strip():
            parts.append(f"{prefix} {str(value).strip()}")

    for key, prefix in numeric_prefixes.items():
        value = values.get(key)
        if value not in (None, "", 0, 0.0):
            suffix = " мм" if key == "wall_thickness" else ""
            number = int(value) if isinstance(value, float) and value.is_integer() else value
            parts.append(f"{prefix} {number}{suffix}")

    coating_labels = {
        True: "есть",
        False: "нет",
        "Да": "есть",
        "Нет": "нет",
    }
    for key, label in (
        ("inner_coating", "внутреннее покрытие"),
        ("outer_coating", "наружное покрытие"),
    ):
        value = values.get(key)
        if value in coating_labels:
            parts.append(f"{label} {coating_labels[value]}")

    base = original_query.strip().rstrip("?.!,;:")
    if not parts:
        return base
    return f"{base}; " + ", ".join(parts)


def render_clarification(current: dict[str, Any]) -> str | None:
    """Render missing fields and return a clarified query after submission."""
    route = current.get("route_decision") or {}
    missing = route.get("missing_parameters") or current.get("missing_parameters") or []
    fields = normalize_missing_fields([str(item) for item in missing])

    st.markdown("### Уточните запрос")
    st.info(
        "Система поняла общую задачу, но для надёжного поиска не хватает "
        "нескольких параметров. Заполните то, что вам известно."
    )

    if route.get("reasons"):
        with st.expander("Почему система задала вопрос"):
            for reason in route["reasons"]:
                st.markdown(f"- {reason}")

    values: dict[str, Any] = {}
    with st.form("clarification_form"):
        if fields:
            columns = st.columns(2)
            for index, field in enumerate(fields):
                container = columns[index % 2]
                key = f"clarify_{field.key}"
                if field.kind == "number":
                    values[field.key] = container.number_input(
                        field.label,
                        min_value=0.0,
                        value=None,
                        step=1.0,
                        key=key,
                    )
                elif field.kind == "boolean":
                    values[field.key] = container.selectbox(
                        field.label,
                        ["Не указано", "Да", "Нет"],
                        key=key,
                    )
                else:
                    values[field.key] = container.text_input(field.label, key=key)
        else:
            values["details"] = st.text_area(
                "Дополнительные сведения",
                placeholder="Например: DN 159, PN 40, среда H2S",
            )

        submitted = st.form_submit_button("Продолжить поиск", type="primary")

    if not submitted:
        return None
    if values.get("details"):
        details = str(values["details"]).strip()
        return f"{current.get('query', '').strip().rstrip('?')}; {details}".strip("; ")
    return build_clarified_query(current.get("query") or "", values)
