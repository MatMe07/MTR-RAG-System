"""Экран «Результаты поиска»."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import search_history  # noqa: E402
from components.auth import is_authenticated  # noqa: E402
from components.tables import render_table  # noqa: E402
from components.utils import fmt_date, search_rows  # noqa: E402

st.set_page_config(page_title="Результаты поиска", layout="wide")

if not is_authenticated():
    st.warning("Сначала войдите в систему.")
    st.page_link("app.py", label="Вернуться ко входу")
    st.stop()

st.markdown("## Результаты поиска")

results = st.session_state.get("results", [])
warnings = st.session_state.get("warnings", [])
request_id = st.session_state.get("request_id")
search_query = st.session_state.get("search_query", "")

if search_query:
    st.caption(f"Запрос: «{search_query}»  ·  ID: {request_id or '—'}  ·  Найдено: {len(results)}")

rows = search_rows(results)

if not results:
    for w in warnings:
        st.warning(w)
    st.info("Ничего не найдено. Попробуйте изменить запрос на странице «Поиск».")
else:
    for w in warnings:
        st.warning(w)

    col1, col2 = st.columns([3, 1])
    with col1:
        use_aggrid = st.toggle("Интерактивная таблица (AgGrid)", value=False)
    with col2:
        st.markdown("")
        st.download_button("Экспорт CSV", pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
                           file_name="results.csv", mime="text/csv")

    grid = render_table(rows, use_aggrid=use_aggrid, height=480, key="results_table")

    if use_aggrid and grid:
        sel = grid.get("selected_rows", [])
        if sel:
            selected_df = sel if isinstance(sel, pd.DataFrame) else pd.DataFrame(sel)
            if not selected_df.empty:
                row = selected_df.iloc[0].to_dict()
                ksm = row.get("Код КСМ")
                if ksm:
                    st.session_state.selected_ksm = ksm
                    st.page_link("pages/4_Component.py", label="Открыть карточку изделия")
    else:
        selected = st.selectbox("Выберите позицию для просмотра карточки:", options=range(len(rows)),
                                format_func=lambda i: f"{rows[i]['Код МТР']} / {rows[i]['Код КСМ']} — {rows[i]['Наименование']}")
        if selected is not None:
            st.session_state.selected_ksm = rows[selected]["Код КСМ"]
            st.page_link("pages/4_Component.py", label="Открыть карточку изделия")

    st.markdown("---")
    for i, comp in enumerate(results[:5], 1):
        with st.expander(f"{i}. {comp.get('name', '')} — {comp.get('status', '')}"):
            props = comp.get("properties") or {}
            detail = comp.get("detail")
            if detail:
                st.write(detail)
            for k, v in list(props.items())[:12]:
                if isinstance(v, dict):
                    st.markdown(f"**{k}**: {v.get('value', '')} {v.get('unit', '')}")
                else:
                    st.markdown(f"**{k}**: {v}")

st.markdown("---")
st.markdown("### История запросов")
hist = search_history(limit=10)
if hist.status_code == 200:
    items = hist.json()
    if items:
        st.caption("Нажмите на запрос, чтобы показать сохранённые результаты.")
        for idx, h in enumerate(items):
            label = f"{h.get('query', '')}  ·  {h.get('mode', '')}  ·  {fmt_date(h.get('created_at'))}  ·  результатов: {h.get('results_count', 0)}"
            if st.button(label, key=f"hist_{idx}"):
                saved = h.get("results") or []
                if saved:
                    st.session_state.results = saved
                    st.session_state.warnings = h.get("warnings") or []
                    st.session_state.request_id = h.get("request_id")
                    st.session_state.search_query = h.get("query", "")
                    st.session_state.search_mode = h.get("mode", "deterministic")
                    st.rerun()
                else:
                    st.info("Для этого запроса результаты не сохранены. Выполните его заново на странице «Поиск».")
    else:
        st.caption("История пуста. Выполните поиск — запросы появятся здесь.")
else:
    st.caption("История недоступна.")