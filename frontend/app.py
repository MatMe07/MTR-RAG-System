import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

import requests
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from frontend.agent_view import render_agent_result
from frontend.clarification_view import render_clarification
from frontend.demo_scenarios import DEMO_SCENARIOS
from frontend.expert_history_view import render_expert_history
from frontend.export_utils import candidate_export_rows, result_to_json, rows_to_csv
from frontend.quality_view import render_quality_view


DEMO_DATA_PATH = PROJECT_ROOT / "data" / "sample" / "ui_demo_case_q007.json"
QUESTIONS_PATH = (
    PROJECT_ROOT / "data" / "evaluation" / "complex_questions_40.jsonl"
)
STRESS_CASES_PATH = (
    PROJECT_ROOT / "data" / "evaluation" / "agent_stress_cases_50.jsonl"
)
BACKEND_URL = os.getenv("MTR_BACKEND_URL", "http://localhost:8000").rstrip("/")

SEARCH_MODES = {
    "Автоматически": "auto",
    "Гибридный поиск": "hybrid",
    "Точный поиск": "exact",
    "Семантический поиск": "vector",
    "Поиск по паспорту": "passport",
    "Проверка аналога": "filter",
    "Агентный запрос": "agent",
}

LEGACY_MODE_LABELS = {
    "автоматически": "Автоматически",
    "гибридный поиск": "Гибридный поиск",
    "точный поиск": "Точный поиск",
    "семантический поиск": "Семантический поиск",
    "поиск по паспорту": "Поиск по паспорту",
    "проверка аналога": "Проверка аналога",
    "агентный запрос": "Агентный запрос",
}

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

DECISION_CODES = {
    "Требует дополнительной проверки": "need_more_info",
    "Подтвердить": "approve",
    "Отклонить": "reject",
}

SOURCE_LABELS = {
    "passport": "Паспорт",
    "excel": "Excel",
    "lnd": "ЛНД",
    "catalog": "Каталог",
    "standard": "ГОСТ/ТУ",
    "user_query": "Запрос пользователя",
    "expert": "Эксперт",
}

ROUTE_LABELS = {
    "ordinary": "Обычный поиск",
    "clarification": "Нужно уточнение",
    "agent": "Агентный сценарий",
}

MODE_LABELS = {
    "exact": "Точный код",
    "hybrid": "Каталог и правила",
    "missing_parameters": "Уточнение параметров",
    "inventory_and_match": "Аналоги и склад",
    "inventory": "Складские остатки",
    "maintenance_plan": "План ТОиР",
    "object_configuration": "Связи объекта",
    "impact_analysis": "Влияние замены",
    "evidence_collection": "Сбор подтверждений",
}

TOOL_LABELS = {
    "catalog_search": "каталог",
    "stock_query": "складские остатки",
    "rules_engine": "правила сравнения",
    "regulation_lookup": "ГОСТ/ТУ и нормативы",
    "graph_search": "связи объекта",
    "maintenance_planner": "планирование ТОиР",
    "document_search": "паспорта и документы",
    "explanation_generator": "объяснение параметров",
    "object_builder": "состав объекта",
    "impact_analyzer": "влияние изменения",
    "duplicate_detector": "проверка дублей",
    "priority_ranker": "приоритизация рисков",
    "inventory_calculator": "расчёт запаса",
}

AGENT_SOURCE_LABELS = {
    "catalog": "Каталог",
    "stock": "Склад",
    "object_graph": "Граф объекта",
    "passport": "Паспорт",
    "tu": "ТУ",
    "lnd": "ЛНД",
    "standard": "ГОСТ/ТУ",
    "regulation": "Регуляторика",
    "expert_decisions": "Решения экспертов",
}

INTENT_LABELS = {
    "catalog_search": "Поиск по каталогу",
    "replacement": "Подбор замены",
    "inventory": "Склад и запас",
    "maintenance": "План ТОиР",
    "object_configuration": "Сборка участка",
    "document_search": "Поиск документов",
    "impact_analysis": "Анализ влияния",
    "equipment_guidance": "Справочная информация",
    "duplicates": "Проверка дублей",
}


class BackendAPIError(RuntimeError):
    pass


def normalize_mode_label(value: str | None) -> str:
    if value in SEARCH_MODES:
        return value
    if value in SEARCH_MODES.values():
        return next(
            label for label, code in SEARCH_MODES.items() if code == value
        )
    if isinstance(value, str):
        return LEGACY_MODE_LABELS.get(value.casefold(), "Гибридный поиск")
    return "Гибридный поиск"


def mode_code(mode_label: str) -> str:
    return SEARCH_MODES[normalize_mode_label(mode_label)]


def _response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, list):
        return "; ".join(
            str(item.get("msg", item)) if isinstance(item, dict) else str(item)
            for item in detail
        )
    return str(detail or payload)


def post_json(
    path: str,
    payload: dict[str, Any],
    timeout: int = 1000,
) -> dict[str, Any]:
    try:
        response = requests.post(
            f"{BACKEND_URL}{path}",
            json=payload,
            timeout=timeout,
        )
    except requests.exceptions.ConnectionError as exc:
        raise BackendAPIError(
            f"Backend недоступен по адресу {BACKEND_URL}."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise BackendAPIError(
            "Backend не ответил вовремя. Попробуйте повторить запрос."
        ) from exc
    except requests.RequestException as exc:
        raise BackendAPIError(f"Ошибка соединения с backend: {exc}") from exc

    if not response.ok:
        raise BackendAPIError(
            f"Backend вернул ошибку {response.status_code}: "
            f"{_response_error(response)}"
        )
    try:
        print(response.json())
        return response.json()
    except ValueError as exc:
        raise BackendAPIError("Backend вернул не JSON-ответ.") from exc


def get_json(
    path: str,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    try:
        response = requests.get(
            f"{BACKEND_URL}{path}",
            params=params,
            timeout=timeout,
        )
    except requests.exceptions.ConnectionError as exc:
        raise BackendAPIError(
            f"Backend недоступен по адресу {BACKEND_URL}."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise BackendAPIError("Backend не ответил вовремя.") from exc
    except requests.RequestException as exc:
        raise BackendAPIError(f"Ошибка соединения с backend: {exc}") from exc

    if not response.ok:
        raise BackendAPIError(
            f"Backend вернул ошибку {response.status_code}: {_response_error(response)}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise BackendAPIError("Backend вернул не JSON-ответ.") from exc


def upload_passport(uploaded_file: Any) -> dict[str, Any]:
    file_bytes = uploaded_file.getvalue()
    files = {
        "file": (
            uploaded_file.name,
            file_bytes,
            uploaded_file.type or "application/octet-stream",
        )
    }
    try:
        response = requests.post(
            f"{BACKEND_URL}/upload/passport",
            files=files,
            timeout=150,
        )
    except requests.exceptions.ConnectionError as exc:
        raise BackendAPIError(
            f"Backend недоступен по адресу {BACKEND_URL}."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise BackendAPIError(
            "Загрузка паспорта превысила допустимое время."
        ) from exc
    except requests.RequestException as exc:
        raise BackendAPIError(f"Ошибка загрузки паспорта: {exc}") from exc

    if not response.ok:
        raise BackendAPIError(
            f"Паспорт не загружен: {_response_error(response)}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise BackendAPIError(
            "Backend вернул некорректный ответ после загрузки."
        ) from exc


def search_backend(
    query: str,
    mode_label: str,
    uploaded_file: Any | None = None,
    top_k: int = 20,
) -> dict[str, Any]:
    selected_mode = mode_code(mode_label)

    if selected_mode == "auto":
        return auto_search_backend(query, top_k=top_k)

    if selected_mode == "agent":
        return agent_backend(query, mode_label)

    document_id = None

    if selected_mode == "passport":
        if uploaded_file is None:
            raise BackendAPIError(
                "Для режима «Поиск по паспорту» прикрепите файл."
            )
        upload_result = upload_passport(uploaded_file)
        document_id = upload_result.get("document_id")
        if document_id is None:
            raise BackendAPIError(
                "Backend загрузил файл, но не вернул document_id."
            )

    payload = {
        "query": query.strip(),
        "mode": selected_mode,
        "top_k": top_k,
        "document_id": document_id,
    }
    data = post_json("/search", payload)
    return transform_backend_response(data, query, mode_label)


def transform_agent_response(
    data: dict[str, Any],
    query: str,
    mode_label: str,
) -> dict[str, Any]:
    return {
        "search_id": str(uuid.uuid4()),
        "query": query,
        "mode": "Агентный запрос",
        "mode_code": "agent",
        "selected_mode_code": mode_code(mode_label),
        "query_card": {},
        "total_found": 0,
        "search_time_ms": None,
        "backend_connected": True,
        "error": None,
        "candidates": [],
        "agent": {
            "intent": data.get("intent"),
            "intent_label": data.get("intent_label"),
            "route": data.get("route"),
            "tools_used": data.get("tools_used") or [],
            "answer": data.get("answer") or "",
            "components": [
                {
                    "mtr_code": component.get("mtr_code"),
                    "ksm_code": component.get("ksm_code"),
                    "name": component.get("name"),
                    "item_type": component.get("item_type"),
                    "quantity": component.get("quantity"),
                    "status": component.get("status"),
                    "detail": component.get("detail"),
                    "source_id": component.get("source_id"),
                }
                for component in data.get("components") or []
                if isinstance(component, dict)
            ],
            "warnings": data.get("warnings") or [],
            "sources": [
                {
                    "kind": source.get("kind"),
                    "id": source.get("id"),
                    "fragment": source.get("fragment"),
                }
                for source in data.get("sources") or []
                if isinstance(source, dict)
            ],
            "missing_parameters": data.get("missing_parameters") or [],
            "human_review_required": bool(data.get("human_review_required")),
            "execution_mode": data.get("mode"),
            "parsed_confidence": data.get("parsed_confidence"),
            "review_verdict": data.get("review_verdict"),
            "review_issues": data.get("review_issues") or [],
            # Сохраняем разобранный запрос для показа карточки в агентном UI.
            "parsed_query": data.get("parsed_query"),
        },
    }


def agent_backend(
    query: str,
    mode_label: str,
) -> dict[str, Any]:
    if not query.strip():
        raise BackendAPIError("Введите запрос для агентного слоя.")
    data = post_json("/agent", {"query": query.strip()}, timeout=200)
    return transform_agent_response(data, query, mode_label)


def auto_search_backend(query: str, top_k: int = 20) -> dict[str, Any]:
    """Let /route choose ordinary search, clarification, or the agent."""
    clean_query = query.strip()
    if not clean_query:
        raise BackendAPIError("Введите запрос.")

    route = post_json("/route", {"query": clean_query}, timeout=30)
    route_name = route.get("route")
    print(f"[auto] /route -> {route_name} (mode={route.get('mode')})", flush=True)
    if route_name not in {"ordinary", "agent", "clarification"}:
        raise BackendAPIError("Маршрутизатор не вернул допустимый способ обработки.")

    if route_name == "clarification":
        print("[auto] путь=clarification -> показываем форму недостающих параметров", flush=True)
        parsed = route.get("parsed_query") or {}
        query_card = parsed.get("card") if isinstance(parsed, dict) else {}
        return {
            "search_id": str(uuid.uuid4()),
            "query": clean_query,
            "mode": "Автоматически",
            "mode_code": "clarification",
            "selected_mode_code": "auto",
            "query_card": query_card or {},
            "route_decision": route,
            "missing_parameters": route.get("missing_parameters") or [],
            "total_found": 0,
            "search_time_ms": None,
            "backend_connected": True,
            "error": None,
            "candidates": [],
        }

    if route_name == "agent":
        print("[auto] путь=agent -> POST /agent", flush=True)
        result = agent_backend(clean_query, "Автоматически")
        result["mode"] = "Автоматически"
        result["route_decision"] = route
        if not result["agent"].get("parsed_query"):
            result["agent"]["parsed_query"] = route.get("parsed_query")
        return result

    execution_mode = "exact" if route.get("mode") == "exact" else "hybrid"
    print(f"[auto] путь=ordinary -> POST /search (mode={execution_mode})", flush=True)
    data = post_json(
        "/search",
        {
            "query": clean_query,
            "mode": execution_mode,
            "top_k": top_k,
            "document_id": None,
        },
    )
    result = transform_backend_response(
        data,
        clean_query,
        normalize_mode_label(execution_mode),
    )
    result["mode"] = "Автоматически"
    result["selected_mode_code"] = "auto"
    result["execution_mode"] = execution_mode
    result["route_decision"] = route
    return result


def save_expert_review(
    search_id: str,
    candidate_ksm_code: str,
    decision_label: str,
    comment: str,
    reviewer: str,
) -> dict[str, Any]:
    if not reviewer.strip():
        raise BackendAPIError("Укажите имя эксперта.")
    if not candidate_ksm_code:
        raise BackendAPIError(
            "У кандидата нет кода КСМ, решение сохранить нельзя."
        )

    return post_json(
        "/expert-review",
        {
            "search_id": search_id,
            "candidate_ksm_code": candidate_ksm_code,
            "decision": DECISION_CODES[decision_label],
            "comment": comment.strip(),
            "reviewer": reviewer.strip(),
        },
        timeout=30,
    )


def transform_backend_response(
    data: dict[str, Any],
    query: str,
    mode_label: str,
) -> dict[str, Any]:
    return {
        "search_id": data.get("search_id") or str(uuid.uuid4()),
        "query": query,
        "mode": normalize_mode_label(mode_label),
        "mode_code": mode_code(mode_label),
        "query_card": data.get("requested_card") or {},
        "total_found": data.get("total_found", 0),
        "search_time_ms": data.get("search_time_ms"),
        "backend_connected": True,
        "error": None,
        "candidates": [
            {
                "rank": candidate.get("rank", index + 1),
                "mtr_code": candidate.get("mtr_code") or "",
                "ksm_code": candidate.get("ksm_code"),
                "candidate_name": candidate.get("candidate_name") or "",
                "match_percent": candidate.get("match_percent") or 0,
                "status": candidate.get("status", "нет данных"),
                "matched_params": candidate.get("matched_params") or [],
                "mismatched_params": candidate.get("mismatched_params") or [],
                "missing_params": candidate.get("missing_params") or [],
                "warnings": candidate.get("warnings") or [],
                "expert_comment": candidate.get("expert_comment"),
                "rule_trace": candidate.get("rule_trace") or [],
                "stock_quantity": candidate.get("stock_quantity"),
                "stock_cost": candidate.get("stock_cost"),
                "sources": [
                    {
                        "type": source.get("type", "unknown"),
                        "file": source.get("file")
                        or source.get("file_name"),
                        "page": source.get("page"),
                        "row": source.get("row"),
                        "fragment": source.get("fragment")
                        or (
                            source.get("source_fragment", {}).get("text")
                            if isinstance(source.get("source_fragment"), dict)
                            else None
                        ),
                        "fragment_id": (
                            source.get("source_fragment", {}).get("fragment_id")
                            if isinstance(source.get("source_fragment"), dict)
                            else None
                        ),
                    }
                    for source in candidate.get("sources", [])
                    if isinstance(source, dict)
                ],
            }
            for index, candidate in enumerate(data.get("candidates", []))
            if isinstance(candidate, dict)
        ],
    }


def load_demo_data() -> dict[str, Any]:
    with DEMO_DATA_PATH.open(encoding="utf-8") as demo_file:
        result = json.load(demo_file)
    result["search_id"] = f"demo-{uuid.uuid4()}"
    result["mode"] = normalize_mode_label(result.get("mode"))
    result["mode_code"] = mode_code(result["mode"])
    result["backend_connected"] = False
    result["error"] = None
    return result


def load_approved_questions() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _question_key(value: str) -> str:
    normalized = " ".join(value.casefold().split())
    return re.sub(r"[?.!,;:]+$", "", normalized).strip()


def find_approved_question(query: str) -> dict[str, Any] | None:
    query_key = _question_key(query)
    return next(
        (
            question
            for question in load_approved_questions()
            if _question_key(question["question"]) == query_key
        ),
        None,
    )


def card_missing_fields(card: dict[str, Any]) -> list[str]:
    extraction = card.get("extraction")
    if not isinstance(extraction, dict):
        return []
    missing = extraction.get("missing_fields")
    return list(missing) if isinstance(missing, list) else []


def build_query_review_context(
    query: str,
    card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from backend.app.services.routing.search_router import route_query_text
    
    decision = route_query_text(query, card or {})
    scenario = find_approved_question(query)
    if scenario:
        decision["route"] = scenario["expected_route"]
        decision["required_tools"] = scenario["required_tools"]
    decision["scenario"] = scenario
    decision["card_missing_fields"] = card_missing_fields(card or {})
    return decision


def render_query_processing(
    query: str,
    card: dict[str, Any],
) -> None:
    if not query.strip():
        return

    context = build_query_review_context(query, card)
    scenario = context["scenario"]
    with st.expander("Как система поняла запрос", expanded=True):
        if scenario:
            st.caption(
                f"Согласованный проверочный сценарий {scenario['case_id']}"
            )

        summary = st.columns(3)
        summary[0].metric("Задача", context["intent_label"])
        summary[1].metric(
            "Маршрут",
            ROUTE_LABELS.get(context["route"], context["route"]),
        )
        summary[2].metric(
            "Способ обработки",
            MODE_LABELS.get(context["mode"], context["mode"]),
        )

        for reason in context["reasons"]:
            st.markdown(f"- {reason}")

        aliases = [
            alias
            for alias in context["detected_aliases"]
            if alias["alias"] != alias["canonical"]
        ]
        if aliases:
            recognized = ", ".join(
                f"{alias['alias']} → {alias['canonical'].upper()}"
                for alias in aliases
            )
            st.caption(f"Распознаны формулировки: {recognized}")

        tools = [
            TOOL_LABELS.get(tool, tool)
            for tool in context["required_tools"]
        ]
        st.caption("Будут использованы: " + ", ".join(tools))

        missing = list(
            dict.fromkeys(
                context["missing_parameters"]
                + context["card_missing_fields"]
            )
        )
        if missing:
            st.warning(
                "Нужно уточнить или проверить: " + ", ".join(missing)
            )

    with st.expander("Критерии правильного ответа", expanded=bool(scenario)):
        if not scenario:
            st.markdown(
                "- показать найденных кандидатов и причину их попадания "
                "в выдачу\n"
                "- отделить совпадения от расхождений и неизвестных данных\n"
                "- привести доступные источники\n"
                "- оставить окончательное решение эксперту"
            )
            return

        st.markdown("**В ответе должны быть:**")
        for requirement in scenario["answer_must_include"]:
            st.markdown(f"- {requirement}")
        sources = ", ".join(
            SOURCE_LABELS.get(source, source)
            for source in scenario["required_sources"]
        )
        st.caption(f"Нужные источники: {sources}")
        st.warning(scenario["mandatory_warning"])


def card_value(
    card: dict[str, Any],
    property_name: str,
    *legacy_path: str,
) -> Any:
    properties = card.get("properties")
    if isinstance(properties, dict) and property_name in properties:
        characteristic = properties[property_name]
        if isinstance(characteristic, dict) and "value" in characteristic:
            return characteristic.get("value")
        return characteristic

    current: Any = card
    for part in legacy_path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return "Да"
    if value is False:
        return "Нет"
    return "Не указано"


def build_query_from_fields(fields: dict[str, Any]) -> str:
    parts = []
    text_fields = (
        ("item_type", ""),
        ("subtype", ""),
        ("steel_grade", "сталь "),
        ("strength_class", "класс прочности "),
        ("medium", "среда "),
        ("gost_tu", ""),
    )
    for field, prefix in text_fields:
        value = str(fields.get(field) or "").strip()
        if value:
            parts.append(f"{prefix}{value}".strip())

    numeric_fields = (
        ("dn", "DN"),
        ("angle", "угол"),
        ("wall_thickness", "стенка"),
        ("pn", "PN"),
    )
    for field, prefix in numeric_fields:
        value = fields.get(field)
        if value not in (None, 0, 0.0):
            parts.append(f"{prefix} {value:g}")

    if fields.get("h2s_confirmed") == "Да":
        parts.append("пригодность к H2S подтверждена")
    elif fields.get("h2s_confirmed") == "Нет":
        parts.append("для H2S не предназначено")

    for field, label in (
        ("inner_coating", "внутреннее покрытие"),
        ("outer_coating", "наружное покрытие"),
    ):
        if fields.get(field) == "Да":
            parts.append(label)
        elif fields.get(field) == "Нет":
            parts.append(f"{label} отсутствует")

    return ", ".join(parts)


def source_location(source: dict[str, Any]) -> str:
    details = []
    if source.get("file"):
        details.append(str(source["file"]))
    if source.get("page") is not None:
        details.append(f"стр. {source['page']}")
    if source.get("row") is not None:
        details.append(f"строка {source['row']}")
    return ", ".join(details) or "местоположение не указано"


def render_parameter_list(title: str, values: list[str], kind: str) -> None:
    st.markdown(f"#### {title}")
    if not values:
        st.caption("Нет")
        return
    marker = {"matched": "✓", "mismatched": "≠", "missing": "?"}[kind]
    css_class = f"param-{kind}"
    for value in values:
        st.markdown(
            f'<div class="param-row {css_class}"><span>{marker}</span>'
            f"{value}</div>",
            unsafe_allow_html=True,
        )


def render_query_card(card: dict[str, Any]) -> str | None:
    if not card:
        return None

    fields = {
        "item_type": card.get("item_type") or "",
        "subtype": card.get("subtype") or "",
        "dn": card_value(card, "dn", "geometry", "dn"),
        "angle": card_value(card, "angle", "geometry", "angle"),
        "wall_thickness": card_value(
            card,
            "wall_thickness",
            "geometry",
            "wall_thickness",
        ),
        "pn": card_value(card, "pn", "pressure", "pn"),
        "steel_grade": card_value(
            card,
            "steel_grade",
            "material",
            "steel_grade",
        ),
        "strength_class": card_value(
            card,
            "strength_class",
            "material",
            "strength_class",
        ),
        "medium": card_value(card, "medium", "environment", "medium"),
        "h2s_confirmed": card_value(
            card,
            "h2s_confirmed",
            "environment",
            "h2s_confirmed",
        ),
        "inner_coating": card_value(
            card,
            "inner_coating",
            "coating",
            "inner_coating",
        ),
        "outer_coating": card_value(
            card,
            "outer_coating",
            "coating",
            "outer_coating",
        ),
        "gost_tu": card_value(card, "gost_tu", "normative", "gost_tu"),
    }

    with st.expander("Карточка требуемого изделия", expanded=True):
        st.caption(
            "Исправьте распознанные параметры и повторите поиск. "
            "Пустое поле означает «не указано»."
        )
        with st.form("edit_query_card"):
            row_1 = st.columns(4)
            item_type = row_1[0].text_input(
                "Тип изделия",
                fields["item_type"],
            )
            subtype = row_1[1].text_input("Подтип", fields["subtype"])
            dn = row_1[2].number_input(
                "DN, мм",
                min_value=0.0,
                value=float(fields["dn"] or 0),
            )
            angle = row_1[3].number_input(
                "Угол, град.",
                min_value=0.0,
                max_value=360.0,
                value=float(fields["angle"] or 0),
            )

            row_2 = st.columns(4)
            wall_thickness = row_2[0].number_input(
                "Толщина стенки, мм",
                min_value=0.0,
                value=float(fields["wall_thickness"] or 0),
            )
            pn = row_2[1].number_input(
                "PN / Ру",
                min_value=0.0,
                value=float(fields["pn"] or 0),
            )
            steel_grade = row_2[2].text_input(
                "Марка стали",
                fields["steel_grade"] or "",
            )
            strength_class = row_2[3].text_input(
                "Класс прочности",
                fields["strength_class"] or "",
            )

            row_3 = st.columns(4)
            medium = row_3[0].text_input(
                "Рабочая среда",
                fields["medium"] or "",
            )
            h2s = row_3[1].selectbox(
                "Пригодность к H2S",
                ["Да", "Нет", "Не указано"],
                index=["Да", "Нет", "Не указано"].index(
                    yes_no_unknown(fields["h2s_confirmed"])
                ),
            )
            inner_coating = row_3[2].selectbox(
                "Внутреннее покрытие",
                ["Да", "Нет", "Не указано"],
                index=["Да", "Нет", "Не указано"].index(
                    yes_no_unknown(fields["inner_coating"])
                ),
            )
            outer_coating = row_3[3].selectbox(
                "Наружное покрытие",
                ["Да", "Нет", "Не указано"],
                index=["Да", "Нет", "Не указано"].index(
                    yes_no_unknown(fields["outer_coating"])
                ),
            )

            gost_tu = st.text_input(
                "ГОСТ / ТУ",
                fields["gost_tu"] or "",
            )
            submitted = st.form_submit_button(
                "Повторить поиск по исправленной карточке",
                type="primary",
            )

        if submitted:
            return build_query_from_fields(
                {
                    "item_type": item_type,
                    "subtype": subtype,
                    "dn": dn,
                    "angle": angle,
                    "wall_thickness": wall_thickness,
                    "pn": pn,
                    "steel_grade": steel_grade,
                    "strength_class": strength_class,
                    "medium": medium,
                    "h2s_confirmed": h2s,
                    "inner_coating": inner_coating,
                    "outer_coating": outer_coating,
                    "gost_tu": gost_tu,
                }
            )
    return None


def render_sources(sources: list[dict[str, Any]]) -> None:
    with st.expander("Источники", expanded=True):
        if not sources:
            st.caption(
                "Для этого кандидата backend не вернул источники. "
                "Результат требует дополнительной проверки."
            )
            return

        for number, source in enumerate(sources, start=1):
            source_type = SOURCE_LABELS.get(
                source.get("type"),
                source.get("type") or "Источник",
            )
            st.markdown(
                f"**{number}. {source_type}: {source_location(source)}**"
            )
            if source.get("fragment_id"):
                st.caption(f"Фрагмент: {source['fragment_id']}")
            fragment = source.get("fragment")
            if fragment:
                st.code(fragment, language=None)
            else:
                st.caption("OCR-фрагмент или выдержка не сохранены.")


def render_candidate_details(
    candidate: dict[str, Any],
    search_id: str,
    backend_connected: bool,
    reviewer: str,
) -> None:
    st.markdown("### Проверка кандидата")
    heading = st.columns([3, 1])
    heading[0].markdown(
        f"**{candidate['mtr_code']} · {candidate['candidate_name']}**"
    )
    heading[0].caption(
        f"КСМ: {candidate.get('ksm_code') or 'не указан'}"
    )
    heading[1].metric(
        "Близость",
        f"{candidate.get('match_percent', 0):.0f}%",
    )

    status = STATUS_LABELS.get(candidate["status"], candidate["status"])
    status_class = STATUS_CLASSES.get(candidate["status"], "status-empty")
    st.markdown(
        f'<div class="status {status_class}">{status}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Статус рекомендательный. Финальное решение принимает эксперт."
    )

    if candidate["warnings"]:
        st.markdown("#### Предупреждения")
        for warning in candidate["warnings"]:
            st.warning(warning)

    params = st.columns(3)
    with params[0]:
        render_parameter_list(
            "Совпало",
            candidate["matched_params"],
            "matched",
        )
    with params[1]:
        render_parameter_list(
            "Отличается",
            candidate.get("mismatched_params", []),
            "mismatched",
        )
    with params[2]:
        render_parameter_list(
            "Нет данных",
            candidate.get("missing_params", []),
            "missing",
        )

    st.info(candidate.get("expert_comment") or "Комментарий не указан.")

    with st.expander("Почему кандидат попал в выдачу"):
        traces = candidate.get("rule_trace", [])
        if not traces:
            st.caption("Правила не сработали или trace не был возвращён.")
        for trace in traces:
            st.markdown(
                f"**{trace.get('rule_id', 'правило')}** · "
                f"{trace.get('message', '')}"
            )
            st.caption(
                f"Реакция правила: {trace.get('reaction', 'unknown')}"
            )

    render_sources(candidate.get("sources", []))

    st.markdown("### Решение эксперта")
    candidate_key = (
        candidate.get("ksm_code")
        or candidate.get("mtr_code")
        or str(candidate.get("rank"))
    )
    with st.form(f"expert_review_{candidate_key}"):
        decision = st.radio(
            "Решение",
            list(DECISION_CODES),
            horizontal=True,
        )
        comment = st.text_area(
            "Комментарий",
            placeholder="Что проверено и почему кандидат принят или отклонён",
        )
        submitted = st.form_submit_button(
            "Сохранить решение",
            type="primary",
        )

    if submitted:
        if not backend_connected:
            st.warning(
                "Сейчас открыты демонстрационные данные. "
                "Выполните реальный поиск через backend."
            )
            return
        try:
            result = save_expert_review(
                search_id=search_id,
                candidate_ksm_code=candidate.get("ksm_code") or "",
                decision_label=decision,
                comment=comment,
                reviewer=reviewer,
            )
        except BackendAPIError as exc:
            st.error(str(exc))
            return

        if result.get("success"):
            st.success(
                result.get("message")
                or "Решение эксперта сохранено в базе данных."
            )
        else:
            st.error(
                result.get("message")
                or "Backend не смог сохранить решение."
            )


def render_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink: #17211b; --muted: #5f6b64; --line: #d8dfda; --accent: #176b45; }
        .stApp { background: #f7f9f7; color: var(--ink); }
        .block-container {
            box-sizing: border-box;
            max-width: 1200px;
            padding: 3.5rem 2rem 4rem;
        }
        h1, h2, h3, h4 { letter-spacing: 0 !important; color: var(--ink); }
        h1 { font-size: 2rem !important; }
        [data-testid="stExpander"], [data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 6px;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: .75rem 1rem;
        }
        .eyebrow {
            color: var(--accent);
            font-size: .78rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .lead {
            color: var(--muted);
            margin-top: -.6rem;
            max-width: 850px;
            overflow-wrap: anywhere;
        }
        .status {
            display: inline-block;
            border-radius: 4px;
            padding: .25rem .55rem;
            font-size: .82rem;
            font-weight: 700;
            margin-bottom: .2rem;
        }
        .status-ok { color: #0f5a38; background: #dff3e8; }
        .status-potential { color: #155b75; background: #e1f1f7; }
        .status-review { color: #7a4b00; background: #fff0c7; }
        .status-low, .status-empty { color: #6b3333; background: #f7e5e5; }
        .param-row {
            display: flex;
            gap: .5rem;
            padding: .42rem .55rem;
            margin-bottom: .35rem;
            border-left: 3px solid;
            background: #ffffff;
            font-size: .9rem;
        }
        .param-matched { border-color: #2d8b5d; }
        .param-mismatched { border-color: #c56b34; }
        .param-missing { border-color: #8b9090; }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 6px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_agent_answer(current: dict[str, Any]) -> None:
    agent = current.get("agent") or {}
    if not agent:
        st.caption("Агентный слой не вернул структурированный ответ.")
        return

    st.markdown("### Ответ агентного слоя")
    summary = st.columns(4)
    intent_label = agent.get("intent_label") or INTENT_LABELS.get(
        agent.get("intent") or "",
        agent.get("intent") or "не определен",
    )
    summary[0].metric("Задача", intent_label)
    tools = [TOOL_LABELS.get(tool, tool) for tool in agent.get("tools_used") or []]
    summary[1].metric("Тулы", ", ".join(tools) if tools else "—")
    summary[2].metric("Позиции", len(agent.get("components") or []))
    summary[3].metric(
        "Проверка эксперта",
        "нужна" if agent.get("human_review_required") else "не обязательна",
    )

    answer = (agent.get("answer") or "").strip()
    if answer:
        for paragraph in answer.splitlines():
            if paragraph.strip():
                st.markdown(paragraph)
    else:
        st.caption("Текстовый ответ не сформирован.")

    execution_mode = agent.get("execution_mode")
    if execution_mode:
        mode_hint = {
            "llm_augmented": "LLM-синтез",
            "offline_rules": "офлайн-правила",
        }.get(execution_mode, execution_mode)
        st.caption(f"Режим сборки ответа: {mode_hint}")

    if agent.get("human_review_required"):
        st.warning(
            "Ответ носит рекомендательный характер и требует проверки экспертом."
        )

    review_verdict = agent.get("review_verdict")
    review_issues = agent.get("review_issues") or []
    if review_verdict:
        if review_verdict == "pass":
            st.success("Авторевью: ответ проходит проверку.")
        elif review_verdict == "needs_review":
            st.warning("Авторевью: ответ требует проверки.")
        if review_issues:
            st.markdown("**Замечания авторевью:**")
            for issue in review_issues:
                st.markdown(f"- {issue}")

    for warning in agent.get("warnings") or []:
        st.warning(warning)

    missing = agent.get("missing_parameters") or []
    if missing:
        st.error(
            "Не хватает данных для полного ответа: " + ", ".join(missing)
        )

    components = agent.get("components") or []
    if components:
        st.markdown("#### Позиции ответа")
        table_rows = [
            {
                "Код КСМ": component.get("ksm_code") or "—",
                "Код МТР": component.get("mtr_code") or "—",
                "Наименование": component.get("name") or "—",
                "Тип": component.get("item_type") or "—",
                "Кол-во": component.get("quantity"),
                "Статус": component.get("status") or "—",
                "Детали": component.get("detail") or "",
            }
            for component in components
        ]
        st.dataframe(table_rows, hide_index=True, width="stretch")

    sources = agent.get("sources") or []
    if sources:
        with st.expander("Источники"):
            for number, source in enumerate(sources, start=1):
                label = AGENT_SOURCE_LABELS.get(
                    source.get("kind"),
                    source.get("kind") or "Источник",
                )
                location = source.get("id") or ""
                fragment = source.get("fragment")
                if fragment:
                    location = f"{location} · {fragment}".strip(" ·")
                st.markdown(f"**{number}. {label}**: {location or '—'}")


def render_app() -> None:
    st.set_page_config(page_title="Подбор аналогов МТР", layout="wide")
    render_styles()

    st.markdown(
        '<div class="eyebrow">Экспертная рекомендательная система</div>',
        unsafe_allow_html=True,
    )
    st.title("Подбор аналогов МТР")
    st.markdown(
        '<p class="lead">Система сокращает область поиска и объясняет '
        "результат. Она не заменяет инженерное заключение эксперта.</p>",
        unsafe_allow_html=True,
    )

    section = st.sidebar.radio(
        "Раздел",
        ["Поиск", "Проверка качества", "Решения экспертов"],
    )
    reviewer = st.sidebar.text_input(
        "Эксперт",
        value=st.session_state.get("reviewer", ""),
        placeholder="Имя или логин",
    )
    st.session_state["reviewer"] = reviewer
    st.sidebar.caption(f"Backend: {BACKEND_URL}")

    if section == "Проверка качества":
        render_quality_view(post_json, STRESS_CASES_PATH)
        return
    if section == "Решения экспертов":
        render_expert_history(get_json)
        return

    if "results" not in st.session_state:
        st.session_state["results"] = load_demo_data()

    current = st.session_state["results"]

    st.sidebar.markdown("#### Готовый сценарий")
    demo_titles = {item["title"]: item for item in DEMO_SCENARIOS}
    selected_demo_title = st.sidebar.selectbox(
        "Сценарий",
        list(demo_titles),
        label_visibility="collapsed",
    )
    selected_demo = demo_titles[selected_demo_title]
    st.sidebar.caption(selected_demo["expected"])
    if st.sidebar.button("Подставить запрос", width="stretch"):
        st.session_state["query_input"] = selected_demo["query"]
        st.session_state["mode_input"] = "Автоматически"
        st.rerun()

    if "mode_input" not in st.session_state:
        st.session_state["mode_input"] = "Автоматически"
    if "query_input" not in st.session_state:
        st.session_state["query_input"] = current.get("query", "")

    with st.form("search_form"):
        controls = st.columns([1.1, 2.8, 1.3])
        mode = controls[0].selectbox(
            "Режим поиска",
            list(SEARCH_MODES),
            key="mode_input",
        )
        query = controls[1].text_area(
            "Запрос",
            height=105,
            help="Опишите изделие и важные условия эксплуатации.",
            key="query_input",
        )
        uploaded_file = controls[2].file_uploader(
            "Паспорт изделия",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            help="Файл используется в режиме «Поиск по паспорту».",
        )
        submitted = st.form_submit_button(
            "Найти кандидатов",
            type="primary",
            width="stretch",
        )

    if submitted:
        with st.spinner("Формируем карточку и ранжируем кандидатов..."):
            try:
                st.session_state["results"] = search_backend(
                    query=query,
                    mode_label=mode,
                    uploaded_file=uploaded_file,
                )
            except BackendAPIError as exc:
                st.session_state["results"] = {
                    "search_id": str(uuid.uuid4()),
                    "query": query,
                    "mode": mode,
                    "mode_code": mode_code(mode),
                    "query_card": {},
                    "candidates": [],
                    "total_found": 0,
                    "search_time_ms": None,
                    "backend_connected": False,
                    "error": str(exc),
                }
        current = st.session_state["results"]

    if current.get("error"):
        st.error(current["error"])

    route_decision = current.get("route_decision") or {}
    if route_decision and current.get("mode_code") != "clarification":
        route_label = ROUTE_LABELS.get(
            route_decision.get("route"), route_decision.get("route") or "Не определён"
        )
        with st.expander("Как выбран способ обработки", expanded=False):
            st.markdown(f"**Маршрут:** {route_label}")
            if route_decision.get("mode"):
                st.markdown(
                    "**Режим выполнения:** "
                    + MODE_LABELS.get(
                        route_decision["mode"], route_decision["mode"]
                    )
                )
            for reason in route_decision.get("reasons") or []:
                st.markdown(f"- {reason}")

    if current.get("mode_code") == "clarification":
        clarified_query = render_clarification(current)
        if clarified_query:
            st.session_state["query_input"] = clarified_query
            with st.spinner("Проверяем уточнённый запрос..."):
                try:
                    st.session_state["results"] = search_backend(
                        query=clarified_query,
                        mode_label="Автоматически",
                    )
                except BackendAPIError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
        return

    if current.get("mode_code") == "agent":
        render_agent_result(
            current,
            reviewer=reviewer,
            save_review=save_expert_review,
        )
        return

    render_query_processing(
        current.get("query") or "",
        current.get("query_card") or {},
    )

    edited_query = render_query_card(current.get("query_card") or {})
    if edited_query:
        with st.spinner("Повторно ищем по исправленным параметрам..."):
            try:
                st.session_state["results"] = search_backend(
                    query=edited_query,
                    mode_label="Проверка аналога",
                )
            except BackendAPIError as exc:
                st.error(str(exc))
            else:
                st.rerun()

    candidates = sorted(
        current.get("candidates", []),
        key=lambda item: item.get("rank", 0),
    )
    
    if not candidates:
        if not current.get("error"):
            st.info(
                "Кандидаты не найдены. Уточните запрос, проверьте режим "
                "поиска или дождитесь OCR-обработки паспорта."
            )
        return

    st.markdown("### Кандидаты")
    total_found = current.get("total_found", len(candidates))
    search_time = current.get("search_time_ms")
    caption = (
        f"Показано {len(candidates)} кандидатов из {total_found}. "
        "Список отсортирован по близости."
    )
    if search_time is not None:
        caption += f" Время поиска: {search_time:.0f} мс."
    st.caption(caption)

    table_rows = [
        {
            "Место": item.get("rank", index + 1),
            "Код МТР": item.get("mtr_code", ""),
            "Код КСМ": item.get("ksm_code", ""),
            "Наименование": item.get("candidate_name", ""),
            "Близость, %": item.get("match_percent", 0),
            "Статус": STATUS_LABELS.get(
                item.get("status", ""),
                item.get("status", "нет данных"),
            ),
            "Предупреждения": len(item.get("warnings", [])),
        }
        for index, item in enumerate(candidates)
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
            "Близость, %": st.column_config.ProgressColumn(
                min_value=0,
                max_value=100,
                format="%d%%",
            ),
            "Предупреждения": st.column_config.NumberColumn(width="small"),
        },
    )

    export_columns = st.columns(2)
    export_columns[0].download_button(
        "Скачать результат JSON",
        data=result_to_json(current),
        file_name="mtr_search_result.json",
        mime="application/json",
        width="stretch",
    )
    export_columns[1].download_button(
        "Скачать кандидатов CSV",
        data=rows_to_csv(candidate_export_rows(current)),
        file_name="mtr_candidates.csv",
        mime="text/csv",
        width="stretch",
    )

    candidate_options = [
        (
            index,
            item,
            item.get("ksm_code")
            or item.get("mtr_code")
            or f"candidate-{index}",
        )
        for index, item in enumerate(candidates)
    ]
    selected_key = st.selectbox(
        "Открыть кандидата",
        [option[2] for option in candidate_options],
        format_func=lambda key: next(
            f"{item.get('rank', index + 1)}. "
            f"{item.get('mtr_code') or 'без МТР'} · "
            f"{item.get('candidate_name', '')}"
            for index, item, option_key in candidate_options
            if option_key == key
        ),
    )
    selected_candidate = next(
        item
        for _, item, option_key in candidate_options
        if option_key == selected_key
    )
    render_candidate_details(
        selected_candidate,
        search_id=current.get("search_id") or str(uuid.uuid4()),
        backend_connected=bool(current.get("backend_connected")),
        reviewer=reviewer,
    )


if __name__ == "__main__":
    render_app()
