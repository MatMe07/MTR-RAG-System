# tests/test_answer_builder_cap.py
"""Тесты умного лимита компонентов ответа (AnswerBuilder._to_components)."""

import unittest

from app.schemas import ParsedQuery
from app.services.agent.answer.builder import AnswerBuilder

BUILDER = AnswerBuilder()


def _candidate(name: str, match_score: float, quantity=None) -> dict:
    row = {
        "mtr_code": f"MTR-{name}",
        "ksm_code": f"KSM-{name}",
        "name": name,
        "item_type": "задвижка",
        "quantity": quantity,
        "status": "совпадает по параметрам",
        "match_score": match_score,
        "match_percent": int(match_score * 100),
    }
    return row


def _verdict(name: str, detail: str = "дефицит по типу") -> dict:
    return {
        "mtr_code": f"MTR-V-{name}",
        "ksm_code": f"KSM-V-{name}",
        "name": name,
        "item_type": "труба",
        "status": "не хватает — потребность",
        "detail": detail,
    }


def _parsed(**overrides) -> ParsedQuery:
    base = {
        "original_query": "тест",
        "intents": [],
        "stock_filters": {},
        "on_stock": None,
    }
    base.update(overrides)
    return ParsedQuery(**base)


class CapComponentsTest(unittest.TestCase):
    def test_simple_query_caps_at_ten(self):
        """Без фильтров простой запрос не должен давать больше MAX_COMPONENTS."""
        rows = [_candidate(f"c{i}", 0.9 - i * 0.01) for i in range(30)]
        parsed = _parsed()
        comps = BUILDER._to_components(rows, parsed=parsed)
        self.assertLessEqual(len(comps), AnswerBuilder.MAX_COMPONENTS)

    def test_top_candidates_come_first(self):
        """При усечении впереди — кандидаты с максимальным скорингом."""
        rows = [_candidate(f"c{i}", 0.9 - i * 0.01) for i in range(30)]
        comps = BUILDER._to_components(rows, parsed=_parsed())
        scores = [c.match_score for c in comps]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_stock_filter_keeps_all_matching_positions(self):
        """Явный порог остатка: позиции, прошедшие фильтр, не срезаются."""
        rows = [_candidate(f"c{i}", 0.5, quantity=i + 1) for i in range(25)]
        parsed = _parsed(stock_filters={"quantity_min": 1})
        comps = BUILDER._to_components(rows, parsed=parsed)
        # все строки с quantity проходят порог и должны быть сохранены
        self.assertEqual(len(comps), 25)

    def test_verdicts_are_protected_from_cap(self):
        """Аналитические вердикты сохраняются даже при большом числе."""
        rows = [_candidate(f"c{i}", 0.8 - i * 0.01) for i in range(15)]
        rows += [_verdict(f"v{i}") for i in range(8)]
        comps = BUILDER._to_components(rows, parsed=_parsed())
        verdict_names = {c.name for c in comps if c.name.startswith("v")}
        self.assertEqual(len(verdict_names), 8)
        self.assertLessEqual(len(comps), AnswerBuilder.MAX_COMPONENTS + 8)

    def test_out_of_stock_protects_zero_stock_rows(self):
        """on_stock=False: позиции с нулевым остатком сохраняются."""
        rows = [_candidate(f"c{i}", 0.5, quantity=0) for i in range(20)]
        parsed = _parsed(on_stock=False)
        comps = BUILDER._to_components(rows, parsed=parsed)
        self.assertEqual(len(comps), 20)


if __name__ == "__main__":
    unittest.main()