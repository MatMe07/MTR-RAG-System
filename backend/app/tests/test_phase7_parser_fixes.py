# tests/test_phase7_parser_fixes.py

"""Шаг 7 (5.5): локальные дефекты парсера.

- AQ007: среда CORR вместо H2S для «коррозионного участка»;
- AQ002/AQ004: жёсткий отсев стали, не пригодной для H2S (сталь 20);
- AQ006: переход 219→159 фильтруется по обоим диаметрам d1/d2;
- AQ039/AQ040: regulation_lookup расшифровывает найденные/отсутствующие ГОСТ.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.agent.core.config import AgentConfig  # noqa: E402
from app.services.agent.executor import AgentExecutor  # noqa: E402
from app.services.agent.parsing.parsers.environment_parser import EnvironmentParser  # noqa: E402
from app.services.agent.tools.core_tools import _h2s_steel_rules  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = _REPO_ROOT / "data" / "evaluation" / "complex_questions_40.jsonl"


def _load_case(case_id: str):
    with open(DATA_FILE, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            case = json.loads(line)
            if case.get("case_id") == case_id:
                return case
    raise KeyError(f"case {case_id} not found")


class AQ007CorrMediumTest(unittest.TestCase):
    """«коррозионный участок» должен давать CORR, а не H2S."""

    def test_corrosive_medium_is_corr(self):
        env = EnvironmentParser().parse(
            "Найди замену заглушке для коррозионного участка")
        self.assertEqual(env["medium"], "CORR")
        self.assertIsNot(env["h2s_confirmed"], True)

    def test_h2s_medium_still_h2s(self):
        env = EnvironmentParser().parse("участок с H2S, нужен аналог")
        self.assertEqual(env["medium"], "H2S")
        self.assertTrue(env["h2s_confirmed"])

    def test_corr_alias_normalizes(self):
        from app.services.agent.parsing.normalizers.normalizers import normalize_medium

        self.assertEqual(normalize_medium("коррозионная среда"), "CORR")
        self.assertEqual(normalize_medium("агрессивная среда"), "CORR")


class AQ002_004_H2SSteelTest(unittest.TestCase):
    """H2S + сталь: сталь 20 отсекается, 13ХФА проходит."""

    @classmethod
    def setUpClass(cls):
        ex = AgentExecutor(AgentConfig(use_llm=False, storage="json"))
        cls.case = _load_case("AQ004")
        cls.answer = ex.execute(cls.case["question"], mode="auto")

    def test_steel_20_not_marked_corresponds(self):
        # AQ004: сталь 20 на H2S — не «соответствует».
        for c in self.answer.components:
            self.assertNotEqual(
                c.tz_status, "соответствует",
                f"{c.name}: сталь 20 не должна быть «соответствует» для H2S")

    def test_incompatible_steel_warning(self):
        warned = any("не пригодна для H2S" in w for w in self.answer.warnings)
        self.assertTrue(warned, "ожидалось предупреждение о непригодности стали 20")

    def test_h2s_steel_rules_loaded(self):
        rules = _h2s_steel_rules()
        self.assertEqual(rules.get("20"), "incompatible")
        self.assertEqual(rules.get("13ХФА"), "suitable")
        self.assertEqual(rules.get("09Г2С"), "requires_verification")


class AQ006TransitionDnTest(unittest.TestCase):
    """Переход 219→159: только переход с d1=219, d2=159."""

    @classmethod
    def setUpClass(cls):
        ex = AgentExecutor(AgentConfig(use_llm=False, storage="json"))
        cls.case = _load_case("AQ006")
        cls.answer = ex.execute(cls.case["question"], mode="auto")

    def test_no_wrong_diameter_transition(self):
        for c in self.answer.components:
            name = (c.name or "").lower()
            if "переход" in name:
                self.assertTrue(
                    ("219" in name and "159" in name),
                    f"переход с чужими диаметрами: {c.name}")

    def test_transition_counts_d1_d2(self):
        # хотя бы один переход должен быть «соответствует» с матчем по DN₁/DN₂
        trans = [c for c in self.answer.components if "переход" in (c.name or "").lower()]
        self.assertTrue(trans, "нет переходов в ответе")
        self.assertTrue(
            any(c.tz_status == "соответствует" for c in trans),
            "ожидался переход «соответствует» для 219→159")


class AQ039_040_RegulationDecodeTest(unittest.TestCase):
    """regulation_lookup: расшифровка найденных ГОСТ (а не «Проверено N»)."""

    @classmethod
    def setUpClass(cls):
        ex = AgentExecutor(AgentConfig(use_llm=False, storage="json"))
        cls.aq040 = ex.execute(
            "Покажи откуда взяты ГОСТы для отвода KSM-SYN-REG-000242 "
            "и что каждый из них подтверждает", mode="auto")

    def test_gost_decoded_not_just_count(self):
        text = self.aq040.explanation or ""
        self.assertNotIn("Проверено 3 нормативов", text)
        self.assertIn("ГОСТ", text)
        # декодированный ГОСТ несёт и номер, и краткое описание
        self.assertTrue(
            any("—" in line and "ГОСТ" in line
                for line in text.splitlines()),
            "ответ должен содержать расшифровку «ГОСТ N — описание»")


class AQ036ExplicitDnReplacementTest(unittest.TestCase):
    """«DN200 вместо DN150» — явная замена размера, а не неоднозначность."""

    @classmethod
    def setUpClass(cls):
        ex = AgentExecutor(AgentConfig(use_llm=False, storage="json"))
        cls.answer = ex.execute(
            "Хотим поставить задвижку DN200 вместо DN150, "
            "покажи какие соседние детали придется заменить или проверить",
            mode="auto")

    def test_no_multiple_dn_ambiguity(self):
        text = self.answer.explanation or ""
        for line in text.splitlines():
            self.assertNotIn(
                "несколько значений DN", line,
                "замена DN без неоднозначности, но эмитится DN-амбигуити")
            self.assertNotIn(
                "Конфликт интентов", line,
                "замена «X вместо Y» не должна давать конфликт FIND_ALTERNATIVE")
        pq = self.answer.parsed_query
        self.assertIsNotNone(pq, "нет parsed_query")
        self.assertNotEqual(pq.status, "UNCLEAR",
                            "явная замена DN не должна быть UNCLEAR")
        self.assertEqual(pq.ambiguities, [],
                         "явная замена DN не должна эмитить неоднозначности")

    def test_sources_include_geometry(self):
        self.assertTrue(self.answer.components,
                        "ожидался подбор деталей/влияние на соседние")


if __name__ == "__main__":
    unittest.main()
