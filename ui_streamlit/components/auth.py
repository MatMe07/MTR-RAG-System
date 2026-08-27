"""Проверка ролей и логин."""

import streamlit as st

ROLE_ORDER = ["admin", "expert", "auditor", "user"]


def is_authenticated() -> bool:
    return bool(st.session_state.get("token"))


def get_role() -> str:
    return st.session_state.get("role", "user")


def get_username() -> str:
    return st.session_state.get("username", "")


def check_role(required_roles: list) -> bool:
    """Возвращает True, если роль пользователя есть в required_roles."""
    role = get_role()
    if role not in required_roles:
        st.error(f"Доступ запрещён. Недостаточно прав (требуется: {', '.join(required_roles)}).")
        return False
    return True


def require_role(required_roles: list) -> None:
    """Прерывает выполнение сценария, если нет прав."""
    if not check_role(required_roles):
        st.stop()


def logout() -> None:
    st.session_state.pop("token", None)
    st.session_state.pop("role", None)
    st.session_state.pop("username", None)
    st.session_state.pop("results", None)
    st.session_state.pop("request_id", None)