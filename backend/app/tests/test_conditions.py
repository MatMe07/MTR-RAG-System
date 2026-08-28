"""Юнит-тесты интерпретатора логических условий (conditions.py)."""

from app.services.agent.rules.conditions import (
    _compare,
    _match_when,
    evaluate_logical_conditions,
)


def test_compare_numeric_ops():
    assert _compare("eq", 500, 500)
    assert not _compare("eq", 500, 501)
    assert _compare("neq", 500, 501)
    assert _compare("gt", 501, "500")
    assert _compare("gte", 500, 500)
    assert _compare("lt", 499, "500")
    assert _compare("lte", 500, 500)
    assert _compare("gt", "501", 500)
    # не-числовые сравниваются как строки
    assert _compare("eq", "H2S", "h2s")
    assert _compare("in", "09Г2С", ["20", "09Г2С"])
    assert _compare("not_in", "09Г2С", ["20", "40Х"])


def test_match_when_single_and_list():
    tf = {"dn": 325, "medium": "H2S"}
    assert _match_when({"param": "dn", "op": "gte", "value": 300}, tf)
    assert not _match_when({"param": "dn", "op": "gte", "value": 400}, tf)
    assert _match_when(
        [
            {"param": "dn", "op": "gte", "value": 300},
            {"param": "medium", "op": "eq", "value": "h2s"},
        ],
        tf,
    )
    # одного из условий нет в параметрах → when ложно
    assert not _match_when({"param": "angle", "op": "eq", "value": 90}, tf)


def test_evaluate_require_and_forbid():
    labels = {"wall_thickness": "стенка", "angle": "угол"}
    conditions = [
        {
            "when": {"param": "dn", "op": "gte", "value": 500},
            "then_require": ["wall_thickness"],
            "then_forbid": ["angle"],
        }
    ]
    tf = {"dn": 500, "angle": 90}
    warnings = evaluate_logical_conditions("тройник", conditions, tf, labels)
    texts = " ".join(warnings)
    assert "стенка" in texts and "обязательно" in texts
    assert "угол" in texts and "недопустим" in texts

    tf = {"dn": 500, "wall_thickness": 8}
    assert evaluate_logical_conditions("тройник", conditions, tf, labels) == []


def test_evaluate_invalid_conditions():
    # не валидные структуры не роняют интерпретатор
    assert evaluate_logical_conditions("X", None, {}, {}) == []
    assert evaluate_logical_conditions("X", [{"bad": "rule"}], {}, {}) == []
    assert evaluate_logical_conditions("X", "string", {}, {}) == []