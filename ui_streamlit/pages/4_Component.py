"""Экран «Карточка изделия»."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import component  # noqa: E402
from components.auth import is_authenticated  # noqa: E402
from components.cards import component_card, attribute_table, stock_card, compatibility_card  # noqa: E402
from components.graphs import render_graph, graph_from_components  # noqa: E402

st.set_page_config(page_title="Карточка изделия", layout="wide")

if not is_authenticated():
    st.warning("Сначала войдите в систему.")
    st.page_link("app.py", label="Вернуться ко входу")
    st.stop()

st.markdown("## Карточка изделия")

default_ksm = st.session_state.get("selected_ksm", "")
col1, col2 = st.columns([2, 1])
with col1:
    ksm_code = st.text_input("Код КСМ (или МТР)", value=default_ksm)
with col2:
    load = st.button("Загрузить", type="primary")

if load and ksm_code:
    with st.spinner("Загрузка карточки..."):
        resp = component(ksm_code)
    if resp.status_code == 200:
        data = resp.json()
        st.session_state.current_component = data
    else:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"Ошибка: {detail}")

data = st.session_state.get("current_component")
if data is None:
    st.info("Введите код КСМ или МТР и нажмите «Загрузить».")
    st.stop()

component_card(data)
st.markdown("---")

attributes = data.get("attributes") or data.get("properties") or {}
attribute_table(attributes)

st.markdown("---")
st.markdown("### Склад")
stock_card(
    {
        "stock_qty": data.get("stock_qty"),
        "unit": data.get("unit", "шт"),
        "cost": data.get("cost"),
        "planned_involvement_date": data.get("planned_involvement_date"),
    }
)

st.markdown("---")
compat = data.get("compatibility") or {}
if compat:
    compatibility_card(compat)

st.markdown("### Топология (соседи)")
neighbors = data.get("neighbors") or data.get("graph") or {}
components_graph = neighbors.get("components") or [
    {"component_id": data.get("ksm_code"), "designation": data.get("name"), "ksm_code": data.get("ksm_code")}
]
nodes, edges_list = graph_from_components(components_graph)
render_graph(nodes, edges_list)

st.markdown("---")
if st.button("Очистить карточку"):
    st.session_state.pop("current_component", None)
    st.rerun()