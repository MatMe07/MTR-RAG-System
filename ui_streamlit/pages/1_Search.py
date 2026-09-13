"""Экран «Поиск»: выводит сырой JSON ответа агента (как app_console)."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import search  # noqa: E402
from components.auth import is_authenticated  # noqa: E402
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
                st.session_state.raw_response = data
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                st.error(f"Ошибка поиска: {detail}")

if st.session_state.get("raw_response"):
    st.json(st.session_state["raw_response"].get("raw_agent_answer") or st.session_state["raw_response"])