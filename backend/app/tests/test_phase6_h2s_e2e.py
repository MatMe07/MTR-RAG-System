# tests/test_phase6_h2s_e2e.py
"""Sub-этап 10: end-to-end кейсы H2S через полный граф (DoD п.3, п.5).

Запускает реальный детерминированный граф + sufficiency_check (без LLM) на
инвентарных H2S-кейсах и проверяет инварианты ответа:

1. AQ009 «проверь хватает ли ... по две штуки»:
   - у каждого из 6 запрошенных типов (труба/отвод/переход/задвижка/заглушка/
     тройник) есть sufficiency-вердикт («хватает» или «не хватает ... дефицит»);
   - для типов с остатком 0 посчитан дефицит = потребность − остаток;
   - потребность «по две штуки» отражена в вердикте;
   - ответ использует sufficiency_check и stock_query.

2. AQ008 «нет на складе / срочность»:
   - в компонентах только позиции с нулевым остатком (фильтр применён),
     утечки позиций в наличии нет.

3. Авто-режим поверх детерминированного прогона:
   - AQ009 (полные вердикты по всем типам) не эскалируется по quantity_unmet /
     scope_mismatch (verdict не обязан быть pass, но критичных гэпов нет);
   - AQ008 не даёт gэп zero_stock_missing (фильтр корректен).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.agent.core.config import AgentConfig  # noqa: E402
from app.services.agent.executor import AgentExecutor  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = _REPO_ROOT / "data" / "evaluation" / "complex_questions_40.jsonl"

SUFFICIENCY_TYPES = ["труба", "отвод", "переход", "задвижка", "заглушка", "тройник"]
SUFFICIENCY_KEY = ("хватает", "не хватает", "дефицит", "потребность")


def _load_case(case_id: str):
    with open(DATA_FILE, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            case = json.loads(line)
            if case.get("case_id") == case_id:
                return case
    raise KeyError(f"case {case_id} not found in {DATA_FILE.name}")


class H2SSufficiencyE2E(unittest.TestCase):
    """AQ009: «хватает ли ... по две штуки» через реальный граф."""

    @classmethod
    def setUpClass(cls):
        cls.case = _load_case("AQ009")
        ex = AgentExecutor(AgentConfig(use_llm=False, storage="json"))
        cls.answer = ex.execute(cls.case["question"], mode="auto")
        by_type: dict = {}
        for c in cls.answer.components:
            st = (c.status or "").lower()
            if any(k in st for k in SUFFICIENCY_KEY):
                by_type.setdefault(c.item_type, []).append(st)
        cls.verdicts_by_type = by_type

    def test_all_requested_types_have_a_verdict(self):
        missing = [t for t in SUFFICIENCY_TYPES if not self.verdicts_by_type.get(t)]
        self.assertEqual(missing, [],
                         f"нет sufficiency-вердикта по типам: {missing}")

    def test_types_with_zero_stock_report_deficit(self):
        # типы, по которым «не хватает», обязаны содержать дефицит
        for t in SUFFICIENCY_TYPES:
            for st in self.verdicts_by_type.get(t, []):
                if "не хватает" in st:
                    self.assertIn("дефицит", st, f"{t}: {st}")
                    self.assertIn("потребность", st, f"{t}: {st}")

    def test_satisfied_type_reports_sufficient(self):
        # труба в наборе имеет остаток — должен быть вердикт «хватает»
        satisfied = [st for st in self.verdicts_by_type.get("труба", []) if "хватает" in st]
        self.assertTrue(satisfied, "труба: ожидался вердикт «хватает»")

    def test_need_reflects_two_units(self):
        text = " ".join(" ".join(v) for v in self.verdicts_by_type.values())
        self.assertIn("2 шт.", text)

    def test_uses_sufficiency_tool(self):
        self.assertIn("sufficiency_check", self.answer.tools_used)
        self.assertIn("stock_query", self.answer.tools_used)

    def test_auto_gate_no_sufficiency_escalation(self):
        reasons = " ".join(self.answer.verification_reasons or [])
        self.assertNotIn("quantity_unmet", reasons, reasons)
        self.assertNotIn("scope_mismatch", reasons, reasons)


class H2SOutOfStockE2E(unittest.TestCase):
    """AQ008: «нет на складе / срочность» через реальный граф."""

    @classmethod
    def setUpClass(cls):
        cls.case = _load_case("AQ008")
        ex = AgentExecutor(AgentConfig(use_llm=False, storage="json"))
        cls.answer = ex.execute(cls.case["question"], mode="auto")
        cls.in_stock = [
            c for c in cls.answer.components
            if c.quantity is not None and c.quantity > 0
        ]

    def test_no_in_stock_leakage(self):
        # для LIST_OUT_OF_STOCK компоненты не должны содержать позиций в наличии
        self.assertEqual(self.in_stock, [],
                         "в ответ «нет на складе» утекли позиции с остатком")

    def test_all_components_zero_or_none_stock(self):
        for c in self.answer.components:
            self.assertTrue(c.quantity is None or c.quantity == 0,
                            f"{c.item_type}: остаток {c.quantity}")

    def test_auto_gate_no_zero_stock_escalation(self):
        reasons = " ".join(self.answer.verification_reasons or [])
        self.assertNotIn("zero_stock_missing", reasons, reasons)

    def test_required_tools_and_sources(self):
        req_tools = set(self.case.get("required_tools") or [])
        have_tools = set(self.answer.tools_used)
        req_sources = set(self.case.get("required_sources") or [])
        have_sources = {s.kind for s in self.answer.sources}
        missing_tools = req_tools - have_tools
        missing_sources = req_sources - have_sources
        self.assertEqual(
            sorted(missing_tools), [],
            f"отсутствуют инструменты: {sorted(missing_tools)}")
        self.assertEqual(
            sorted(missing_sources), [],
            f"отсутствуют источники: {sorted(missing_sources)}")


if __name__ == "__main__":
    unittest.main()