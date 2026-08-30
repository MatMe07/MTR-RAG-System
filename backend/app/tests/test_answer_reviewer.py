# tests/test_answer_reviewer.py
"""Авторевью структуры ответа: review_verdict pass|needs_review (5D)."""

from app.schemas import ParsedQuery
from app.services.agent.answer.builder import build_answer


def _parsed(query: str = "задвижка DN150 PN16") -> ParsedQuery:
    return ParsedQuery(original_query=query)


def _full_result():
    return {
        "components": [{
            "mtr_code": "MTR-TEST-1",
            "ksm_code": "KSM-TEST-1",
            "name": "Задвижка",
            "item_type": "задвижка",
        }],
        "sources": [{"kind": "catalog", "id": "card-1"}],
        "warnings": [],
        "missing": [],
        "answers": ["Найдена задвижка DN150 PN16"],
        "tools_used": ["catalog_search", "rules_engine"],
        "mode": "offline_rules",
    }


def test_complete_answer_reviewed_pass():
    answer = build_answer(_parsed(), "replacement", _full_result())
    assert answer.review_verdict == "pass"
    assert answer.review_issues == []


def test_empty_answer_needs_review():
    result = _full_result()
    result["answers"] = [""]
    answer = build_answer(_parsed(), "search", result)
    assert answer.review_verdict == "needs_review"
    assert any("не собран" in issue for issue in answer.review_issues)


def test_no_tools_needs_review():
    result = _full_result()
    result["tools_used"] = []
    answer = build_answer(_parsed(), "search", result)
    assert answer.review_verdict == "needs_review"
    assert any("инструмент" in issue for issue in answer.review_issues)


def test_no_sources_needs_review():
    result = _full_result()
    result["sources"] = []
    answer = build_answer(_parsed(), "search", result)
    assert answer.review_verdict == "needs_review"
    assert any("источников" in issue for issue in answer.review_issues)


def test_execution_error_needs_review():
    result = _full_result()
    result["errors"] = [{"code": "DAL_ERROR", "message": "нет данных"}]
    answer = build_answer(_parsed(), "search", result)
    assert answer.review_verdict == "needs_review"
    assert any("Ошибка исполнения" in issue for issue in answer.review_issues)


def test_pass_verdict_kept_with_human_review_flag():
    # Авторевью и ручная/экспертная проверка — независимые оси.
    result = _full_result()
    result["review"] = True
    answer = build_answer(_parsed(), "replacement", result)
    assert answer.review_verdict == "pass"
    assert answer.human_review_required is True