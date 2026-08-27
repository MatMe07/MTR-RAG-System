"""Цветовая схема и константы статусов."""

import streamlit as st

STATUS_COLORS = {
    "Соответствует": "#2e7d32",
    "Потенциальный аналог": "#ed6c02",
    "Требует проверки": "#d32f2f",
    "Низкая релевантность": "#9e9e9e",
    "Нет данных": "#9e9e9e",
    "Не соответствует": "#d32f2f",
}

ROLE_LABELS = {
    "user": "Пользователь",
    "expert": "Эксперт",
    "auditor": "Аудитор",
    "admin": "Администратор",
}

SEARCH_MODES = {
    "Детерминированный": "deterministic",
    "LLM-поиск": "llm",
}

DICT_NAMES = {
    "group_keywords": "Ключевые слова",
    "contextual_overrides": "Контекстные правила",
    "synonyms": "Синонимы",
    "validation_constants": "Константы",
}


def badge(status: str) -> str:
    """Строка HTML для цветного бейджа статуса."""
    color = STATUS_COLORS.get(status, "#1976d2")
    return f'<span style="color:{color};font-weight:bold">{status}</span>'


def inject_css() -> None:
    """Инжектит кастомный CSS в приложение."""
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 12px;
        }
        .match-high { color: #2e7d32; }
        .match-mid { color: #ed6c02; }
        .match-low { color: #d32f2f; }
        .card-title { font-size: 1.3rem; font-weight: 600; color: #1976d2; }
        .conf-high { background-color: #e8f5e9; color: #2e7d32; border-radius: 4px; padding: 2px 8px; }
        .conf-mid { background-color: #fff8e1; color: #ed6c02; border-radius: 4px; padding: 2px 8px; }
        .conf-low { background-color: #ffebee; color: #d32f2f; border-radius: 4px; padding: 2px 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )