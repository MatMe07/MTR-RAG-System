"""Streamlit presentation for a structured agent response."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st


INTENT_LABELS = {
    "catalog_search": "Поиск по каталогу",
    "search": "Поиск по каталогу",
    "replacement": "Подбор замены",
    "inventory": "Склад и запас",
    "maintenance": "План ТОиР",
    "object_configuration": "Состав объекта",
    "document_search": "Поиск документов",
    "impact_analysis": "Анализ влияния",
    "equipment_guidance": "Справка по оборудованию",
    "duplicates": "Проверка дублей",
}

TOOL_LABELS = {
    "catalog_search": "каталог",
    "stock_query": "склад",
    "rules_engine": "правила сравнения",
    "regulation_lookup": "ГОСТ, ТУ и нормативы",
    "graph_search": "связи объекта",
    "maintenance_planner": "планирование ТОиР",
    "document_search": "паспорта и документы",
    "explanation_generator": "объяснение параметров",
    "object_builder": "состав объекта",
    "impact_analyzer": "влияние изменения",
    "duplicate_detector": "проверка дублей",
    "priority_ranker": "приоритет рисков",
    "inventory_calculator": "расчёт запаса",
}

SOURCE_LABELS = {
    "catalog": "Каталог",
    "stock": "Склад",
    "object_graph": "Граф объекта",
    "passport": "Паспорт",
    "tu": "ТУ",
    "lnd": "ЛНД",
    "standard": "ГОСТ/ТУ",
    "regulation": "Регламент",
    "expert_decisions": "Решения экспертов",
}

FIELD_LABELS = {
    "item_type": "Тип изделия",
    "subtype": "Подтип",
    "dn": "DN",
    "d1": "Первый диаметр",
    "d2": "Второй диаметр",
    "angle": "Угол",
    "wall_thickness": "Толщина стенки",
    "pn": "PN",
    "steel_grade": "Марка стали",
    "strength_class": "Класс прочности",
    "medium": "Среда",
    "h2s_confirmed": "H2S подтверждён",
    "co2_confirmed": "CO2 подтверждён",
    "inner": "Внутреннее покрытие",
    "outer": "Наружное покрытие",
    "inner_coating": "Внутреннее покрытие",
    "outer_coating": "Наружное покрытие",
}


def _property_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def _display_value(value: Any) -> str:
    value = _property_value(value)
    if value is True:
        return "Да"
    if value is False:
        return "Нет"
    if value is None:
        return "Не указано"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "Не указано"
    return str(value)


def parsed_query_rows(parsed_query: dict[str, Any] | None) -> list[dict[str, str]]:
    """Convert both nested ParsedQuery and a flat card into UI rows."""
    if not isinstance(parsed_query, dict):
        return []
    card = parsed_query.get("card") or parsed_query.get("requested_card") or {}
    if not isinstance(card, dict):
        return []

    sections = [
        card,
        card.get("geometry") or {},
        card.get("pressure") or {},
        card.get("material") or {},
        card.get("environment") or {},
        card.get("coating") or {},
        card.get("properties") or {},
    ]
    values: dict[str, Any] = {}
    for section in sections:
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if key in FIELD_LABELS and key not in values:
                values[key] = value

    return [
        {"Параметр": FIELD_LABELS[key], "Значение": _display_value(value)}
        for key, value in values.items()
    ]


def component_rows(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "Код КСМ": component.get("ksm_code") or "-",
            "Код МТР": component.get("mtr_code") or "-",
            "Наименование": component.get("name") or "-",
            "Тип": component.get("item_type") or "-",
            "Количество": component.get("quantity"),
            "Статус": component.get("status") or "-",
            "Комментарий": component.get("detail") or "",
        }
        for component in components
        if isinstance(component, dict)
    ]


def agent_quality_notes(agent: dict[str, Any]) -> list[str]:
    notes = []
    if not (agent.get("answer") or "").strip():
        notes.append("Агент не сформировал текстовый ответ")
    if not agent.get("sources"):
        notes.append("В ответе нет источников")
    if agent.get("components") and not any(
        component.get("source_id") for component in agent.get("components") or []
    ):
        notes.append("Найденные позиции не связаны с исходными карточками")
    if agent.get("human_review_required") and not agent.get("warnings"):
        notes.append("Требуется эксперт, но причина не указана в предупреждениях")
    return notes


def render_agent_result(
    current: dict[str, Any],
    reviewer: str = "",
    save_review: Callable[..., dict[str, Any]] | None = None,
) -> None:
    agent = current.get("agent") or {}
    if not agent:
        st.info("Агент не вернул структурированный ответ.")
        return

    st.markdown("### Ответ агента")
    metrics = st.columns(4)
    intent = agent.get("intent") or ""
    metrics[0].metric(
        "Задача",
        agent.get("intent_label") or INTENT_LABELS.get(intent, intent or "Не определена"),
    )
    tools = [TOOL_LABELS.get(tool, tool) for tool in agent.get("tools_used") or []]
    metrics[1].metric("Инструменты", ", ".join(tools) if tools else "-")
    metrics[2].metric("Позиций", len(agent.get("components") or []))
    metrics[3].metric(
        "Проверка эксперта",
        "Нужна" if agent.get("human_review_required") else "Не обязательна",
    )

    parsed_rows = parsed_query_rows(agent.get("parsed_query"))
    if parsed_rows:
        with st.expander("Как система поняла запрос", expanded=True):
            st.dataframe(parsed_rows, hide_index=True, width="stretch")
            confidence = agent.get("parsed_confidence")
            if confidence is not None:
                st.caption(f"Уверенность парсера: {float(confidence) * 100:.0f}%")

    with st.expander("Ход выполнения", expanded=False):
        if tools:
            for number, tool in enumerate(tools, start=1):
                st.markdown(f"{number}. {tool}")
        else:
            st.caption("Агент не указал использованные инструменты.")

    answer = (agent.get("answer") or "").strip()
    if answer:
        st.markdown(answer)
    else:
        st.info("Текстовый ответ пока не сформирован.")

    if agent.get("human_review_required"):
        st.warning(
            "Это рекомендация системы. Окончательное решение принимает эксперт."
        )

    for warning in agent.get("warnings") or []:
        st.warning(warning)

    missing = agent.get("missing_parameters") or []
    if missing:
        st.error("Не хватает данных: " + ", ".join(str(item) for item in missing))

    review_issues = agent.get("review_issues") or []
    if review_issues:
        with st.expander("Что не прошло автоматическую проверку", expanded=True):
            for issue in review_issues:
                st.markdown(f"- {issue}")

    quality_notes = agent_quality_notes(agent)
    if quality_notes:
        with st.expander("Техническая полнота ответа", expanded=False):
            for note in quality_notes:
                st.markdown(f"- {note}")

    components = agent.get("components") or []
    if components:
        st.markdown("#### Найденные позиции")
        st.dataframe(component_rows(components), hide_index=True, width="stretch")

    sources = agent.get("sources") or []
    with st.expander("Источники", expanded=not bool(sources)):
        if not sources:
            st.caption("Источники пока не приложены к ответу.")
        for number, source in enumerate(sources, start=1):
            label = SOURCE_LABELS.get(
                source.get("kind"), source.get("kind") or "Источник"
            )
            location = source.get("id") or "-"
            fragment = source.get("fragment")
            st.markdown(f"**{number}. {label}:** {location}")
            if fragment:
                st.caption(str(fragment))

    reviewable = [
        component for component in components if component.get("ksm_code")
    ]
    if save_review is not None and reviewable:
        st.markdown("#### Решение эксперта")
        options = {
            f"{item.get('ksm_code')} - {item.get('name') or item.get('item_type') or 'позиция'}": item
            for item in reviewable
        }
        selected_label = st.selectbox(
            "Позиция",
            list(options),
            key="agent_review_component",
        )
        decision = st.radio(
            "Решение",
            ["Требует дополнительной проверки", "Подтвердить", "Отклонить"],
            horizontal=True,
            key="agent_review_decision",
        )
        comment = st.text_area(
            "Комментарий",
            key="agent_review_comment",
            placeholder="Что проверено и почему принято такое решение",
        )
        if st.button("Сохранить решение", key="agent_review_submit"):
            selected = options[selected_label]
            try:
                result = save_review(
                    search_id=current.get("search_id") or "agent-search",
                    candidate_ksm_code=selected["ksm_code"],
                    decision_label=decision,
                    comment=comment,
                    reviewer=reviewer,
                )
            except Exception as exc:  # UI must show an API failure without losing the answer.
                st.error(str(exc))
            else:
                st.success(result.get("message") or "Решение сохранено")
