"""Экран «Загрузка паспорта»."""

import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import upload_passport, passport_status, passport_extracted  # noqa: E402
from components.auth import is_authenticated  # noqa: E402
from components.utils import parse_params  # noqa: E402

st.set_page_config(page_title="Загрузка паспорта", layout="wide")

if not is_authenticated():
    st.warning("Сначала войдите в систему.")
    st.page_link("app.py", label="Вернуться ко входу")
    st.stop()

st.markdown("## Загрузка паспорта изделия")

with st.form("upload_form"):
    uploaded = st.file_uploader("Выберите PDF-файл", type=["pdf"], accept_multiple_files=False)
    submitted = st.form_submit_button("Загрузить", type="primary")

if submitted and uploaded is not None:
    file_bytes = uploaded.getvalue()
    with st.spinner("Загрузка файла..."):
        resp = upload_passport(file_bytes, uploaded.name)
    if resp.status_code == 200:
        data = resp.json()
        document_id = data.get("document_id")
        st.session_state.document_id = document_id
        st.success(f"Документ загружен. ID: {document_id}")

        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        for attempt in range(60):
            with progress_placeholder.container():
                status_placeholder.progress(min((attempt + 1) / 30, 1.0), text=f"Обработка документа... ({attempt}с)")
            poll = passport_status(document_id)
            if poll.status_code == 200:
                status = poll.json()
                ocr_status = status.get("ocr_status", "pending")
                status_placeholder.write(f"Статус OCR: **{ocr_status}**")
                if ocr_status == "completed":
                    progress_placeholder.empty()
                    st.success("Обработка завершена.")
                    extracted = passport_extracted(document_id)
                    if extracted.status_code == 200:
                        params = extracted.json().get("params", [])
                        rows = parse_params(params)
                        st.markdown("#### Извлечённые параметры")
                        if rows:
                            st.dataframe(pd.DataFrame(rows), use_container_width=True)
                        else:
                            st.info("Параметры не извлечены.")
                    st.session_state.last_passport_id = document_id
                    st.stop()
                elif ocr_status == "error":
                    progress_placeholder.empty()
                    st.error("Ошибка обработки документа.")
                    st.stop()
            time.sleep(2)
        progress_placeholder.empty()
        st.error("Превышено время ожидания обработки.")
    else:
        st.error(f"Ошибка загрузки: {resp.text}")

if st.session_state.get("last_passport_id"):
    st.info(f"Последний обработанный паспорт: **{st.session_state.last_passport_id}**")