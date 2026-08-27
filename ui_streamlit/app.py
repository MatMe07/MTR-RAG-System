"""MTR RAG System — Streamlit UI. Главный файл (навигация + логин)."""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from components.api import login
from components.auth import logout, ROLE_ORDER  # noqa: E402
from components.utils import safe_text  # noqa: E402
from theme import ROLE_LABELS, inject_css  # noqa: E402

st.set_page_config(page_title="MTR RAG System", layout="wide")
inject_css()


def render_login() -> None:
    st.markdown("## Вход в систему")
    st.markdown("Система интеллектуального подбора МТР")

    with st.form("login_form"):
        username = st.text_input("Логин", value="admin")
        password = st.text_input("Пароль", type="password", value="admin123")
        submitted = st.form_submit_button("Войти", type="primary")

    if submitted:
        resp = login(username, password)
        print(resp)
        if resp.status_code == 200:
            data = resp.json()
            print(data)
            st.session_state.token = data.get("access_token", "")
            user = data.get("user") or {}
            if isinstance(user, dict):
                st.session_state.role = user.get("role", "user")
                st.session_state.username = user.get("username", username)
            else:
                st.session_state.role = "user"
                st.session_state.username = username
            st.success("Вход выполнен успешно!")
            st.rerun()
        else:
            try:
                detail = resp.json().get("detail", "Неверные учётные данные")
            except Exception:
                detail = "Неверные учётные данные"
            st.error(f"Ошибка входа: {detail}")

    st.markdown("---")
    st.caption("Демо-учётка: admin / admin123")


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## MTR RAG System")
        role = st.session_state.get("role", "user")
        username = st.session_state.get("username", "—")
        st.caption(f"Пользователь: **{username}**")
        st.caption(f"Роль: {ROLE_LABELS.get(role, role)}")

        st.markdown("### Страницы")
        st.page_link("pages/1_Search.py", label="Поиск")
        st.page_link("pages/2_Results.py", label="Результаты поиска")
        st.page_link("pages/3_Upload.py", label="Загрузка паспорта")

        if role in ("expert", "admin"):
            st.page_link("pages/6_Expert.py", label="Экспертная проверка")
        if role in ("auditor", "admin"):
            st.page_link("pages/7_Audit.py", label="Аудит")
        if role == "admin":
            st.page_link("pages/8_Admin.py", label="Справочники")

        st.markdown("---")
        if st.button("Выйти", use_container_width=True):
            logout()
            st.rerun()


def main() -> None:
    if not st.session_state.get("token"):
        render_login()
        return

    render_sidebar()
    st.markdown("## Добро пожаловать!")
    st.markdown(
        """
        Используйте навигацию слева для работы с системой:

        - **Поиск** — ввод запроса и выбор режима поиска
        - **Результаты** — результаты последнего поиска
        - **Загрузка паспорта** — загрузка PDF и извлечение параметров
        """
    )


if __name__ == "__main__":
    main()
