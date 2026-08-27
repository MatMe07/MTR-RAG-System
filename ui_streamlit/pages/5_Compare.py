"""Экран «Сравнение деталей»."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import compare  # noqa: E402
from components.auth import is_authenticated  # noqa: E402

st.set_page_config(page_title="Сравнение деталей", layout="wide")

if not is_authenticated():
    st.warning("Сначала войдите в систему.")
    st.page_link("app.py", label="Вернуться ко входу")
    st.stop()

st.markdown("## Сравнение деталей")

with st.form("compare_form"):
    c1, c2 = st.columns(2)
    with c1:
        ksm1 = st.text_input("Деталь 1 (КСМ)", value=st.session_state.get("compare_ksm1", ""))
    with c2:
        ksm2 = st.text_input("Деталь 2 (КСМ)", value=st.session_state.get("compare_ksm2", ""))
    submitted = st.form_submit_button("Сравнить", type="primary")

if submitted:
    st.session_state.compare_ksm1 = ksm1
    st.session_state.compare_ksm2 = ksm2
    if not ksm1 or not ksm2:
        st.warning("Укажите оба кода КСМ.")
    else:
        with st.spinner("Сравнение..."):
            resp = compare(ksm1, ksm2)
        if resp.status_code == 200:
            st.session_state.compare_result = resp.json()
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            st.error(f"Ошибка: {detail}")

result = st.session_state.get("compare_result")
if result is None:
    st.info("Введите коды двух деталей для сравнения.")
    st.stop()

st.markdown(f"### Сравнение: **{result.get('ksm1')}** и **{result.get('ksm2')}**")

matches = result.get("matches", [])
mismatches = result.get("mismatches", [])

rows = []
for m in matches:
    rows.append({"Параметр": m.get("field", ""), f"Деталь 1 ({result.get('ksm1')})": m.get("value_ksm1", ""),
                 f"Деталь 2 ({result.get('ksm2')})": m.get("value_ksm2", ""), "Статус": "совпадает"})
for m in mismatches:
    rows.append({"Параметр": m.get("field", ""), f"Деталь 1 ({result.get('ksm1')})": m.get("value_ksm1", ""),
                 f"Деталь 2 ({result.get('ksm2')})": m.get("value_ksm2", ""), "Статус": "не совпадает"})
only1 = result.get("only_in_first", [])
only2 = result.get("only_in_second", [])
for f in only1:
    rows.append({"Параметр": f, f"Деталь 1 ({result.get('ksm1')})": "есть", f"Деталь 2 ({result.get('ksm2')})": "—", "Статус": "только в детали 1"})
for f in only2:
    rows.append({"Параметр": f, f"Деталь 1 ({result.get('ksm1')})": "—", f"Деталь 2 ({result.get('ksm2')})": "есть", "Статус": "только в детали 2"})

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
else:
    st.info("Нет данных для сравнения.")

similarity = result.get("similarity", 0)
st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Совпало", result.get("match_count", 0))
c2.metric("Не совпало", result.get("mismatch_count", 0))
c3.metric("Схожесть", f"{similarity:.0%}" if similarity else "—")

if similarity >= 0.8:
    st.success("Детали очень похожи — можно рассматривать как аналог.")
elif similarity >= 0.5:
    st.warning("Детали частично совпадают. Требуется экспертная оценка.")
else:
    st.error("Детали существенно различаются. Замена не рекомендуется.")
