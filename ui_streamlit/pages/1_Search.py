"""Экран «Поиск»."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import search  # noqa: E402
from components.auth import is_authenticated  # noqa: E402
from components.tables import render_table  # noqa: E402
from components.utils import search_rows  # noqa: E402
from theme import SEARCH_MODES  # noqa: E402

st.set_page_config(page_title="Поиск", layout="wide")

if not is_authenticated():
    st.warning("Сначала войдите в систему.")
    st.page_link("app.py", label="Вернуться ко входу")
    st.stop()

st.markdown("## Поиск МТР")

with st.form("search_form"):
    query = st.text_area(
        "Запрос",
        height=100,
        placeholder="Например: найди замену задвижке DN150 PN40 для участка с H2S",
    )
    mode_label = st.radio("Режим поиска", list(SEARCH_MODES.keys()), index=0)
    mode = SEARCH_MODES[mode_label]
    submitted = st.form_submit_button("Найти", type="primary")

if submitted:
    if not query.strip():
        st.warning("Введите запрос для поиска.")
    else:
        with st.spinner("Выполняется поиск..."):
            resp = search(query=query, mode=mode)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.results = data.get("results", [])
                st.session_state.warnings = data.get("warnings", [])
                st.session_state.request_id = data.get("request_id")
                st.session_state.search_query = query
                st.session_state.search_mode = mode
                st.success(f"Найдено: {len(st.session_state.results)} позиций")
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                st.error(f"Ошибка поиска: {detail}")

results = st.session_state.get("results", [])
warnings = st.session_state.get("warnings", [])
search_query = st.session_state.get("search_query", "")

for w in warnings:
    st.warning(w)

if results:
    st.markdown("### Результаты текущего запроса")
    if search_query:
        st.caption(f"Запрос: «{search_query}»")
    rows = search_rows(results)
    render_table(rows, use_aggrid=False, height=480, key="search_results_table")
    st.markdown("")
    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
    st.download_button("Экспорт CSV", csv, file_name="results.csv", mime="text/csv")
elif search_query:
    st.info("Ничего не найдено. Попробуйте изменить запрос.")