"""Экран «Управление справочниками»."""

import json as _json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.api import (  # noqa: E402
    admin_dict_get,
    admin_dict_post,
    admin_dict_put,
    admin_dict_delete,
    admin_dict_reload,
)
from components.auth import require_role  # noqa: E402
from theme import DICT_NAMES  # noqa: E402

st.set_page_config(page_title="Справочники", layout="wide")

require_role(["admin"])

st.markdown("## Управление справочниками")

names = list(DICT_NAMES.keys())
tab_labels = [DICT_NAMES[n] for n in names]
tabs = st.tabs(tab_labels)

for tab, name in zip(tabs, names):
    with tab:
        st.markdown(f"### {DICT_NAMES[name]}")

        resp = admin_dict_get(name)
        if resp.status_code != 200:
            st.error(f"Ошибка загрузки: {resp.text}")
            st.stop()
        entries = resp.json()

        if isinstance(entries, list) and entries:
            df = pd.DataFrame(entries)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Справочник пуст.")

        with st.form(f"add_{name}"):
            st.markdown("#### Добавить запись")
            json_input = st.text_area("Данные (JSON)", height=100,
                                      placeholder='{"group_name": "...", "keyword": "...", "priority": 10}')
            add_submit = st.form_submit_button("Добавить", type="primary")

        if add_submit:
            try:
                payload = _json.loads(json_input) if json_input.strip() else {}
                r = admin_dict_post(name, payload)
                if r.status_code in (200, 201):
                    st.success("Запись добавлена.")
                    st.rerun()
                else:
                    st.error(r.text)
            except ValueError:
                st.error("Некорректный JSON.")

        if isinstance(entries, list) and entries:
            with st.expander("Редактирование / удаление"):
                col_id, col_key = st.columns(2)
                with col_id:
                    item_id = st.selectbox("Выберите ID записи:", options=[e.get("id") for e in entries if "id" in e])
                with col_key:
                    field_key = st.text_input("Поле JSON в виде {'ключ': 'значение'}",
                                              value='{"priority": 0}')
                c_edit, c_del = st.columns(2)
                if c_edit.button("Сохранить изменения"):
                    try:
                        payload = _json.loads(field_key) if field_key.strip() else {}
                        r = admin_dict_put(name, item_id, payload)
                        if r.status_code == 200:
                            st.success("Запись обновлена.")
                            st.rerun()
                        else:
                            st.error(r.text)
                    except ValueError:
                        st.error("Некорректный JSON.")
                if c_del.button("Удалить"):
                    r = admin_dict_delete(name, item_id)
                    if r.status_code == 200:
                        st.success("Запись удалена.")
                        st.rerun()
                    else:
                        st.error(r.text)

st.markdown("---")
if st.button("Пересоздать кэш справочников", type="secondary"):
    r = admin_dict_reload()
    if r.status_code == 200:
        st.success("Кэш пересоздан.")
    else:
        st.error(f"Ошибка: {r.text}")
