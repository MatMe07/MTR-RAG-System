"""Экран «Аудит»."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import audit_logs  # noqa: E402
from components.auth import require_role  # noqa: E402
from components.utils import fmt_date  # noqa: E402

st.set_page_config(page_title="Аудит", layout="wide")

require_role(["auditor", "admin"])

st.markdown("## Журнал аудита")

with st.expander("Фильтры", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        request_id = st.text_input("request_id")
    with c2:
        user_id = st.text_input("user_id")
    with c3:
        action = st.selectbox("Действие", ["", "search", "login", "upload", "review", "compare", "admin"])
    with c4:
        limit = st.number_input("Лимит строк", min_value=1, max_value=1000, value=200)

if st.button("Применить фильтры", type="primary"):
    filters = {"request_id": request_id, "user_id": user_id, "action": action}
    resp = audit_logs(filters, limit=int(limit))
    if resp.status_code == 200:
        logs = resp.json()
        if not logs:
            st.info("Записей не найдено.")
            st.stop()
        st.session_state.audit_logs = logs
    else:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"Ошибка: {detail}")

logs = st.session_state.get("audit_logs", [])
if logs:
    rows = []
    for log in logs:
        rows.append(
            {
                "ID": log.get("id"),
                "Время": fmt_date(log.get("created_at")),
                "Пользователь": log.get("user_id", ""),
                "Действие": log.get("action", ""),
                "Данные": str(log.get("data", "")),
                "request_id": log.get("request_id", ""),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=500)

    with st.expander("Детали записи"):
        def _label(item_id):
            r = next((x for x in rows if x["ID"] == item_id), None)
            return f"#{item_id} — {r['Время']} · {r['Пользователь']} · {r['Действие']}" if r else str(item_id)

        selected_id = st.selectbox("Выберите запись:", options=[r["ID"] for r in rows if r["ID"] is not None],
                                   format_func=_label)
        log_row = next((r for r in rows if r["ID"] == selected_id), None)
        if log_row:
            st.json(log_row)
