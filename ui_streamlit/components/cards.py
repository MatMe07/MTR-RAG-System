"""Карточки (MUI-подобные) для отображения деталей."""

import streamlit as st

from .utils import fmt_date, fmt_number, confidence_badge


def component_card(data: dict) -> None:
    """Заголовок детали: KSM, MTR, тип, наименование."""
    st.markdown(
        f'<div class="card-title">{data.get("name") or data.get("designation") or data.get("ksm_code", "?")}</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Код КСМ", data.get("ksm_code", "—"))
    col2.metric("Код МТР", data.get("mtr_code", "—"))
    col3.metric("Тип", data.get("item_type", "—"))
    if data.get("designation"):
        st.caption(f"Обозначение: {data['designation']}")
    if data.get("gost_tu"):
        st.caption(f"ГОСТ/ТУ: {data['gost_tu']}")


def attribute_table(attributes: dict) -> None:
    """Таблица параметров со значением и единицей."""
    if not attributes:
        st.info("Параметры не найдены.")
        return
    rows = []
    for key, value in attributes.items():
        if isinstance(value, dict):
            val = value.get("value")
            unit = value.get("unit", "")
            conf = value.get("confidence")
        else:
            val = value
            unit = ""
            conf = None
        rows.append(
            {
                "Параметр": key,
                "Значение": fmt_number(val) if isinstance(val, (int, float)) else (val or "—"),
                "Единица": unit or "—",
                "Уверенность": confidence_badge(conf) if conf is not None else "—",
            }
        )
    st.markdown("### Параметры")
    st.markdown('<table><tr><th>Параметр</th><th>Значение</th><th>Единица</th><th>Уверенность</th></tr>' + "".join(
        f"<tr><td>{r['Параметр']}</td><td>{r['Значение']}</td><td>{r['Единица']}</td><td>{r['Уверенность']}</td></tr>"
        for r in rows
    ) + "</table>", unsafe_allow_html=True)


def stock_card(stock: dict) -> None:
    """Остатки, цена, сроки."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Остаток", f"{fmt_number(stock.get('stock_qty'))} {stock.get('unit', 'шт')}")
    c2.metric("Цена", f"{fmt_number(stock.get('cost'))} ₽" if stock.get("cost") else "—")
    c3.metric("Планируемая дата", fmt_date(stock.get("planned_involvement_date")))


def compatibility_card(compat: dict) -> None:
    """Результаты проверки совместимости."""
    status = compat.get("status", "")
    warnings = compat.get("warnings", [])
    recommendations = compat.get("recommendations", [])
    if status == "compatible":
        st.success("Совместимо")
    elif status == "requires_review":
        st.warning("Требует проверки")
    elif status == "incompatible":
        st.error("Несовместимо")
    else:
        st.info(f"Статус совместимости: {status or 'нет данных'}")
    for w in warnings:
        st.caption(f"Предупреждение: {w}")
    for r in recommendations:
        st.caption(f"Рекомендация: {r}")


def match_score(percent: float) -> None:
    """Индикатор процента совпадения."""
    pct = percent if percent is not None else 0
    color = "match-high" if pct >= 80 else "match-mid" if pct >= 50 else "match-low"
    st.progress(min(pct / 100, 1.0))
    st.markdown(f'<div class="{color}">{pct:.0f}%</div>', unsafe_allow_html=True)