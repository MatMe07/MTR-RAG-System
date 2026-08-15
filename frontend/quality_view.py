"""Streamlit dashboard for the 50 black-box agent checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from frontend.agent_quality import CaseResult, build_report, load_cases, run_case


PostJson = Callable[[str, dict[str, Any], int], dict[str, Any]]


def _failed_result(case: dict[str, Any], exc: Exception) -> CaseResult:
    return CaseResult(
        case_id=str(case["case_id"]),
        query=str(case["query"]),
        passed=False,
        route_ok=False,
        intent_ok=False,
        tools_ok=False,
        sources_ok=False,
        warning_ok=False,
        review_ok=False,
        latency_ok=False,
        extraction_checked=False,
        extraction_ok=False,
        latency_ms=0.0,
        issues=[f"API недоступен или вернул ошибку: {exc}"],
    )


def _report_rows(
    report: dict[str, Any], cases: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    groups = {case["case_id"]: case.get("group") or "без группы" for case in cases}
    return [
        {
            "Кейс": row["case_id"],
            "Группа": groups.get(row["case_id"], "без группы"),
            "Результат": "Пройден" if row["passed"] else "Ошибка",
            "Время, мс": row["latency_ms"],
            "Проблемы": "; ".join(row["issues"]),
        }
        for row in report.get("cases") or []
    ]


def render_quality_view(post_json: PostJson, cases_path: str | Path) -> None:
    st.markdown("## Проверка качества")
    st.caption(
        "Набор проверяет маршрутизацию, понимание параметров, выбор инструментов, "
        "источники, предупреждения и время ответа."
    )

    try:
        cases = load_cases(cases_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Не удалось прочитать проверочный набор: {exc}")
        return

    amount = st.select_slider(
        "Сколько запросов прогнать",
        options=[5, 10, 20, len(cases)],
        value=min(10, len(cases)),
    )
    selected_cases = cases[:amount]

    if st.button("Запустить проверку", type="primary"):
        progress = st.progress(0, text="Подготовка")
        results: list[CaseResult] = []
        for index, case in enumerate(selected_cases, start=1):
            progress.progress(
                index / len(selected_cases),
                text=f"{case['case_id']}: {index} из {len(selected_cases)}",
            )
            try:
                results.append(run_case(post_json, case))
            except Exception as exc:  # Keep the report useful when one request fails.
                results.append(_failed_result(case, exc))
        progress.empty()
        st.session_state["quality_report"] = build_report(results)
        st.session_state["quality_cases"] = selected_cases

    report = st.session_state.get("quality_report")
    report_cases = st.session_state.get("quality_cases") or selected_cases
    if not report:
        st.info("Нажмите кнопку, чтобы проверить текущий backend на тестовых запросах.")
        return

    summary = report["summary"]
    metrics = st.columns(4)
    metrics[0].metric("Пройдено", f"{summary['passed']} из {summary['total']}")
    metrics[1].metric("Доля успеха", f"{summary['pass_rate'] * 100:.1f}%")
    metrics[2].metric("Среднее время", f"{summary['mean_latency_ms']:.0f} мс")
    metrics[3].metric("p95", f"{summary['p95_latency_ms']:.0f} мс")

    rows = _report_rows(report, report_cases)
    failed_only = st.toggle("Показать только ошибки", value=False)
    if failed_only:
        rows = [row for row in rows if row["Результат"] == "Ошибка"]
    st.dataframe(rows, hide_index=True, width="stretch")

    st.download_button(
        "Скачать отчёт JSON",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name="agent_quality_report.json",
        mime="application/json",
    )
