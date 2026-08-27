"""Экран «Экспертная проверка»."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import (  # noqa: E402
    expert_reviews,
    expert_review_decision,
    expert_pending_passports,
    expert_link_passport,
)
from components.auth import require_role  # noqa: E402
from components.utils import fmt_date  # noqa: E402

st.set_page_config(page_title="Экспертная проверка", layout="wide")

require_role(["expert", "admin"])

st.markdown("## Экспертная проверка")

tab_requests, tab_passports = st.tabs(["Запросы на проверку", "Паспорта на проверку"])

with tab_requests:
    st.markdown("### Запросы")
    resp = expert_reviews()
    if resp.status_code != 200:
        st.error(f"Ошибка загрузки: {resp.text}")
        st.stop()
    reviews = resp.json()
    if not reviews:
        st.info("Нет запросов на проверку.")
    else:
        df = pd.DataFrame(reviews)
        display_cols = [c for c in ["id", "requested_mtr_code", "candidate_ksm_code", "expert_status", "created_at"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)

        selected_id = st.selectbox("Выберите запрос для проверки:", options=[r["id"] for r in reviews],
                                   format_func=lambda rid: next((f"#{r['id']} — {r.get('candidate_ksm_code', '')} ({r.get('expert_status', '')})" for r in reviews if r["id"] == rid), str(rid)))
        review = next((r for r in reviews if r["id"] == selected_id), None)

        if review:
            with st.form(f"review_form_{selected_id}"):
                st.markdown(f"**Запрашиваемый МТР:** {review.get('requested_mtr_code', '')}")
                st.markdown(f"**Кандидат КСМ:** {review.get('candidate_ksm_code', '')}")
                st.markdown(f"**Текущий статус:** {review.get('expert_status', '')} · **Создан:** {fmt_date(review.get('created_at'))}")
                comment = st.text_area("Комментарий эксперта", value=review.get("expert_reason") or "")
                c1, c2, c3 = st.columns(3)
                with c1:
                    confirm = st.form_submit_button("Подтвердить", type="primary")
                with c2:
                    reject = st.form_submit_button("Отклонить")
                with c3:
                    needs = st.form_submit_button("Требует информации")

            if confirm:
                r = expert_review_decision(selected_id, "confirmed", comment)
                if r.status_code == 200:
                    st.success("Решено: подтверждено")
                    st.rerun()
                else:
                    st.error(r.text)
            if reject:
                r = expert_review_decision(selected_id, "rejected", comment)
                if r.status_code == 200:
                    st.success("Решено: отклонено")
                    st.rerun()
                else:
                    st.error(r.text)
            if needs:
                r = expert_review_decision(selected_id, "needs_info", comment)
                if r.status_code == 200:
                    st.success("Запрошена дополнительная информация")
                    st.rerun()
                else:
                    st.error(r.text)

with tab_passports:
    st.markdown("### Паспорта на проверку")
    resp_pass = expert_pending_passports()
    if resp_pass.status_code != 200:
        st.error(f"Ошибка загрузки: {resp_pass.text}")
    else:
        passports = resp_pass.json()
        if not passports:
            st.info("Нет паспортов на проверку.")
        else:
            dfp = pd.DataFrame(passports)
            display_cols = [c for c in ["id", "requested_mtr_code", "candidate_ksm_code", "expert_status", "created_at"] if c in dfp.columns]
            st.dataframe(dfp[display_cols], use_container_width=True)

            doc_id = st.text_input("document_id для связывания (из паспорта)")
            ksm_code = st.text_input("КСМ код для связывания")
            if st.button("Связать паспорт с позицией", type="primary"):
                if doc_id and ksm_code:
                    r = expert_link_passport(doc_id, ksm_code)
                    if r.status_code == 200:
                        st.success("Паспорт связан с позицией.")
                        st.rerun()
                    else:
                        try:
                            detail = r.json().get("detail", r.text)
                        except Exception:
                            detail = r.text
                        st.error(f"Ошибка: {detail}")
                else:
                    st.warning("Укажите document_id и КСМ код.")
