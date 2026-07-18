import json
from pathlib import Path
from typing import Any

import streamlit as st
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA_PATH = PROJECT_ROOT / "data" / "sample" / "ui_demo_case_q007.json"

SEARCH_MODES = [
    "гибридный поиск",
    "точный поиск",
    "семантический поиск",
    "поиск по паспорту",
    "проверка аналога",
]

STATUS_LABELS = {
    "соответствует": "Соответствует",
    "потенциальный аналог": "Потенциальный аналог",
    "требует проверки": "Требует проверки",
    "низкая релевантность": "Низкая релевантность",
    "нет данных": "Нет данных",
}

STATUS_CLASSES = {
    "соответствует": "status-ok",
    "потенциальный аналог": "status-potential",
    "требует проверки": "status-review",
    "низкая релевантность": "status-low",
    "нет данных": "status-empty",
}


def load_search_results(query: str, mode: str, uploaded_file: Any | None = None) -> dict[str, Any]:
    """Real backend call or demo fallback."""
    # Если передан файл — эмулируем загрузку
    if uploaded_file is not None:
        st.toast(f"Файл {uploaded_file.name} загружен")
    
    try:
        # Реальный запрос к бэкенду
        url = "http://localhost:8000/search"
        payload = {
            "query": query.strip() or "отвод ОКШ 90 DN159 стенка 10 К48 для газа с H2S",
            "mode": mode,
            "top_k": 20
        }
        response = requests.post(url, json=payload, timeout=150)
        print(response.status_code, response.text)
        if response.status_code == 200:
            data = response.json()
            # Преобразуем ответ бэкенда в формат фронтенда
            return transform_backend_response(data, query, mode)
        else:
            st.warning(f"Бэкенд вернул ошибку {response.status_code}. Использую демо-данные.")
    except requests.exceptions.ConnectionError:
        st.warning("Бэкенд не доступен. Использую демо-данные.")
    except Exception as e:
        st.warning(f"Ошибка: {e}. Использую демо-данные.")
    
    # Fallback на демо-данные
    with DEMO_DATA_PATH.open(encoding="utf-8") as demo_file:
        result = json.load(demo_file)
    result["query"] = query.strip() or result["query"]
    result["mode"] = mode
    return result


def transform_backend_response(data: dict, query: str, mode: str) -> dict:
    """Преобразует ответ бэкенда в формат фронтенда."""
    return {
        "query": query,
        "mode": mode,
        "query_card": data.get("requested_card", {}),
        "candidates": [
            {
                "rank": c.get("rank", idx + 1),
                "mtr_code": c.get("mtr_code", ""),
                "ksm_code": c.get("ksm_code"),
                "candidate_name": c.get("candidate_name", ""),
                "match_percent": c.get("match_percent", 0),
                "status": c.get("status", "нет данных"),
                "matched_params": c.get("matched_params", []),
                "mismatched_params": c.get("mismatched_params", []),
                "missing_params": c.get("missing_params", []),
                "warnings": c.get("warnings", []),
                "expert_comment": c.get("expert_comment"),
                "rule_trace": c.get("rule_trace", []),
                "sources": [
                    {
                        "type": s.get("type", "unknown"),
                        "file": s.get("file"),
                        "page": s.get("page"),
                        "row": s.get("row"),
                        "fragment": s.get("fragment")
                    }
                    for s in c.get("sources", [])
                ]
            }
            for idx, c in enumerate(data.get("candidates", []))
        ]
    }


def yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return "Да"
    if value is False:
        return "Нет"
    return "Не указано"


def source_location(source: dict[str, Any]) -> str:
    details = []
    if source.get("file"):
        details.append(source["file"])
    if source.get("page") is not None:
        details.append(f"стр. {source['page']}")
    if source.get("row") is not None:
        details.append(f"строка {source['row']}")
    return ", ".join(details) or "источник без номера"


def render_parameter_list(title: str, values: list[str], kind: str) -> None:
    st.markdown(f"#### {title}")
    if not values:
        st.caption("Нет")
        return
    marker = {"matched": "✓", "mismatched": "≠", "missing": "?"}[kind]
    css_class = f"param-{kind}"
    for value in values:
        st.markdown(
            f'<div class="param-row {css_class}"><span>{marker}</span>{value}</div>',
            unsafe_allow_html=True,
        )


def render_query_card(card: dict[str, Any]) -> None:
    geometry = card.get("geometry", {})
    pressure = card.get("pressure", {})
    material = card.get("material", {})
    environment = card.get("environment", {})
    coating = card.get("coating", {})
    normative = card.get("normative", {})

    with st.expander("Карточка требуемого изделия", expanded=True):
        st.caption("Поля можно исправить перед повторным поиском.")
        row_1 = st.columns(4)
        row_1[0].text_input("Тип изделия", card.get("item_type") or "", key="card_item_type")
        row_1[1].text_input("Подтип", card.get("subtype") or "", key="card_subtype")
        row_1[2].number_input("DN, мм", min_value=0.0, value=float(geometry.get("dn") or 0), key="card_dn")
        row_1[3].number_input("Угол, град.", min_value=0.0, max_value=360.0, value=float(geometry.get("angle") or 0), key="card_angle")

        row_2 = st.columns(4)
        row_2[0].number_input("Толщина стенки, мм", min_value=0.0, value=float(geometry.get("wall_thickness") or 0), key="card_wall")
        row_2[1].number_input("PN / Ру", min_value=0.0, value=float(pressure.get("pn") or 0), key="card_pn")
        row_2[2].text_input("Марка стали", material.get("steel_grade") or "", key="card_steel")
        row_2[3].text_input("Класс прочности", material.get("strength_class") or "", key="card_strength")

        row_3 = st.columns(4)
        row_3[0].text_input("Рабочая среда", environment.get("medium") or "", key="card_medium")
        row_3[1].selectbox(
            "Пригодность к H2S",
            ["Да", "Нет", "Не указано"],
            index=["Да", "Нет", "Не указано"].index(yes_no_unknown(environment.get("h2s_confirmed"))),
            key="card_h2s",
        )
        row_3[2].selectbox(
            "Внутреннее покрытие",
            ["Да", "Нет", "Не указано"],
            index=["Да", "Нет", "Не указано"].index(yes_no_unknown(coating.get("inner_coating"))),
            key="card_inner_coating",
        )
        row_3[3].text_input("ГОСТ / ТУ", normative.get("gost_tu") or "", key="card_standard")

        extraction = card.get("extraction", {})
        confidence = extraction.get("confidence")
        if confidence is not None:
            st.caption(f"Карточка извлечена из запроса. Уверенность распознавания: {confidence:.0%}.")


def render_candidate_details(candidate: dict[str, Any]) -> None:
    st.markdown("### Проверка кандидата")
    heading = st.columns([3, 1])
    heading[0].markdown(f"**{candidate['mtr_code']} · {candidate['candidate_name']}**")
    heading[0].caption(f"КСМ: {candidate.get('ksm_code') or 'не указан'}")
    heading[1].metric("Близость", f"{candidate.get('match_percent', 0):.0f}%")

    status = STATUS_LABELS.get(candidate["status"], candidate["status"])
    status_class = STATUS_CLASSES.get(candidate["status"], "status-empty")
    st.markdown(f'<div class="status {status_class}">{status}</div>', unsafe_allow_html=True)
    st.caption("Статус рекомендательный. Финальное решение принимает эксперт.")

    if candidate["warnings"]:
        st.markdown("#### Предупреждения")
        for warning in candidate["warnings"]:
            st.warning(warning)

    params = st.columns(3)
    with params[0]:
        render_parameter_list("Совпало", candidate["matched_params"], "matched")
    with params[1]:
        render_parameter_list("Отличается", candidate.get("mismatched_params", []), "mismatched")
    with params[2]:
        render_parameter_list("Нет данных", candidate.get("missing_params", []), "missing")

    st.info(candidate.get("expert_comment") or "Комментарий не указан.")

    with st.expander("Почему кандидат попал в выдачу"):
        for rule in candidate.get("rule_trace", []):
            st.markdown(f"**{rule.get('rule_id', 'правило')}** · {rule.get('message', '')}")
            st.caption(f"Реакция правила: {rule.get('reaction', 'unknown')}")

    with st.expander("Источники", expanded=True):
        for number, source in enumerate(candidate.get("sources", []), start=1):
            st.markdown(f"**{number}. {source_location(source)}**")
            st.caption(source.get("fragment") or "Фрагмент источника не сохранен.")

    st.markdown("### Решение эксперта")
    decision_key = f"decision_{candidate['mtr_code']}"
    comment_key = f"comment_{candidate['mtr_code']}"
    st.radio(
        "Решение",
        ["Требует проверки", "Подтвердить", "Отклонить"],
        horizontal=True,
        key=decision_key,
    )
    st.text_area(
        "Комментарий",
        placeholder="Что проверено, почему кандидат принят или отклонен",
        key=comment_key,
    )
    if st.button("Сохранить решение", type="primary", key=f"save_{candidate['mtr_code']}"):
        st.session_state["saved_decision"] = {
            "mtr_code": candidate["mtr_code"],
            "decision": st.session_state[decision_key],
            "comment": st.session_state[comment_key],
        }
        st.success(
            f"Решение по {candidate['mtr_code']} сохранено в текущей демонстрационной сессии."
        )


def render_app() -> None:
    st.set_page_config(page_title="Подбор аналогов МТР", layout="wide")
    st.markdown(
        """
        <style>
        :root { --ink: #17211b; --muted: #5f6b64; --line: #d8dfda; --accent: #176b45; }
        .stApp { background: #f7f9f7; color: var(--ink); }
        .block-container { max-width: 1440px; padding-top: 3.5rem; padding-bottom: 4rem; }
        h1, h2, h3, h4 { letter-spacing: 0 !important; color: var(--ink); }
        h1 { font-size: 2rem !important; }
        [data-testid="stExpander"], [data-testid="stForm"] { background: #ffffff; border: 1px solid var(--line); border-radius: 6px; }
        [data-testid="stMetric"] { background: #ffffff; border: 1px solid var(--line); border-radius: 6px; padding: .75rem 1rem; }
        .eyebrow { color: var(--accent); font-size: .78rem; font-weight: 700; text-transform: uppercase; }
        .lead { color: var(--muted); margin-top: -.6rem; max-width: 850px; }
        .status { display: inline-block; border-radius: 4px; padding: .25rem .55rem; font-size: .82rem; font-weight: 700; margin-bottom: .2rem; }
        .status-ok { color: #0f5a38; background: #dff3e8; }
        .status-potential { color: #155b75; background: #e1f1f7; }
        .status-review { color: #7a4b00; background: #fff0c7; }
        .status-low, .status-empty { color: #6b3333; background: #f7e5e5; }
        .param-row { display: flex; gap: .5rem; padding: .42rem .55rem; margin-bottom: .35rem; border-left: 3px solid; background: #ffffff; font-size: .9rem; }
        .param-matched { border-color: #2d8b5d; }
        .param-mismatched { border-color: #c56b34; }
        .param-missing { border-color: #8b9090; }
        div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="eyebrow">Экспертная система · демонстрация Q007</div>', unsafe_allow_html=True)
    st.title("Подбор аналогов МТР")
    st.markdown(
        '<p class="lead">Система сокращает область поиска и объясняет результат. '
        "Она не заменяет инженерное заключение эксперта.</p>",
        unsafe_allow_html=True,
    )

    if "results" not in st.session_state:
        st.session_state["results"] = load_search_results("", SEARCH_MODES[0])

    current = st.session_state["results"]
    with st.form("search_form"):
        controls = st.columns([1, 2.8, 1.3])
        mode = controls[0].selectbox(
            "Режим поиска",
            SEARCH_MODES,
            index=SEARCH_MODES.index(current.get("mode", SEARCH_MODES[0])),
        )
        query = controls[1].text_area(
            "Запрос",
            value=current.get("query", ""),
            height=105,
            help="Опишите изделие и важные условия эксплуатации.",
        )
        uploaded_file = controls[2].file_uploader(
            "Паспорт изделия",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            help="В демонстрации файл отображается, но выдача берется из подготовленного сценария Q007.",
        )
        submitted = st.form_submit_button("Найти кандидатов", type="primary", width="stretch")

    if submitted:
        with st.spinner("Формируем карточку и ранжируем кандидатов..."):
            st.session_state["results"] = load_search_results(query, mode, uploaded_file)
        current = st.session_state["results"]
        if uploaded_file is not None:
            st.toast(f"Файл {uploaded_file.name} принят для демонстрации.")

    if current.get("query_card"):
        render_query_card(current["query_card"])

    candidates = sorted(current.get("candidates", []), key=lambda item: item.get("rank", 0))
    
    if not candidates:
        st.info("Нет кандидатов. Попробуйте изменить запрос или режим поиска.")
        return

    st.markdown("### Кандидаты")
    st.caption(f"Показано {len(candidates)} кандидатов из возможного Top-20. Список отсортирован по близости.")
    
    table_rows = [
        {
            "Место": item.get("rank", idx + 1),
            "Код МТР": item.get("mtr_code", ""),
            "Код КСМ": item.get("ksm_code", ""),
            "Наименование": item.get("candidate_name", ""),
            "Близость, %": item.get("match_percent", 0),
            "Статус": STATUS_LABELS.get(item.get("status", ""), item.get("status", "нет данных")),
            "Предупреждения": len(item.get("warnings", [])),
        }
        for idx, item in enumerate(candidates)
    ]
    
    st.dataframe(
        table_rows,
        hide_index=True,
        width="stretch",
        column_config={
            "Место": st.column_config.NumberColumn(width="small"),
            "Код МТР": st.column_config.TextColumn(width="small"),
            "Код КСМ": st.column_config.TextColumn(width="small"),
            "Наименование": st.column_config.TextColumn(width="large"),
            "Близость, %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
            "Предупреждения": st.column_config.NumberColumn(width="small"),
        },
    )

    selected_code = st.selectbox(
        "Открыть кандидата",
        [item["mtr_code"] for item in candidates if item.get("mtr_code")],
        format_func=lambda code: next(
            f"{item.get('rank', 0)}. {code} · {item.get('candidate_name', '')}"
            for item in candidates
            if item.get("mtr_code") == code
        ),
    )
    selected_candidate = next(item for item in candidates if item.get("mtr_code") == selected_code)
    render_candidate_details(selected_candidate)

    if st.session_state.get("saved_decision"):
        saved = st.session_state["saved_decision"]
        st.caption(
            f"Последнее решение: {saved['mtr_code']} — {saved['decision'].lower()}. "
            "После подключения backend оно будет записываться в журнал экспертных решений."
        )


if __name__ == "__main__":
    render_app()
