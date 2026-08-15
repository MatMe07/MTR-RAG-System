"""Expert decision history and aggregate statistics."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st


GetJson = Callable[[str, dict[str, Any] | None, int], Any]

DECISION_LABELS = {
    "approve": "Подтверждено",
    "reject": "Отклонено",
    "need_more_info": "Нужны сведения",
}


def history_rows(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "Дата": row.get("reviewed_at") or "-",
            "Эксперт": row.get("reviewed_by") or "-",
            "КСМ": row.get("candidate_ksm_code") or "-",
            "Решение": DECISION_LABELS.get(
                row.get("decision"), row.get("decision") or "-"
            ),
            "Комментарий": row.get("comment") or "",
            "Поиск": row.get("search_id") or "-",
        }
        for row in history
        if isinstance(row, dict)
    ]


def render_expert_history(get_json: GetJson) -> None:
    st.markdown("## Решения экспертов")
    st.caption(
        "Здесь видны сохранённые подтверждения, отклонения и запросы дополнительных сведений."
    )

    controls = st.columns([2, 1])
    ksm_code = controls[0].text_input(
        "Фильтр по КСМ",
        placeholder="Например, KSM-SYN-REG-000242",
    )
    limit = controls[1].selectbox("Количество записей", [20, 50, 100], index=1)

    try:
        stats = get_json("/expert-stats", None, 30)
        history = get_json(
            "/expert-history",
            {"ksm_code": ksm_code.strip() or None, "limit": limit},
            30,
        )
    except Exception as exc:
        st.error(str(exc))
        return

    metrics = st.columns(4)
    metrics[0].metric("Всего решений", stats.get("total", 0))
    metrics[1].metric("Подтверждено", stats.get("approved", 0))
    metrics[2].metric("Отклонено", stats.get("rejected", 0))
    metrics[3].metric("Нужны сведения", stats.get("need_more_info", 0))

    rows = history_rows(history if isinstance(history, list) else [])
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("Сохранённых решений по этому фильтру пока нет.")
