# test_warning_cleanup.py

"""После редукции шума в предупреждениях: удаление мусорных disclaimer-ов,
дедупликация H2S (4→1), фильтрация ТОиР по intent."""

import unittest

from app.schemas import ParsedQuery
from app.services.agent.answer.warnings import (
    build_scenario_warnings,
    filter_by_intent,
)


def _parsed(**kw) -> ParsedQuery:
    base = {
        "original_query": "заменить трубу",
        "technical_filters": {},
        "operations": [],
        "item_types": [],
        "intents": [],
    }
    base.update(kw)
    return ParsedQuery(**base)


_TOIR = [
    "Среда с H2S: состав работ и материалы согласует служба ТОиР и эксперт по коррозии.",
    "Черновик: периодичность и состав работ утверждает служба ТОиР",
]

_REMOVED_SCENARIO = [
    "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.",
    "Синтетическая среда в карточке не является подтверждением пригодности изделия к H2S.",
    "Описание синтетической карточки нельзя выдавать за подтвержденный паспорт изделия.",
    "Примеры из синтетического каталога используются только для демонстрации.",
]

_REMOVED_REG = [
    "ГОСТ определяет область применения",
    "Публичные примеры КСМ",
    "synthetic=true",
]


class ScenarioCleanupTest(unittest.TestCase):
    """Удалённые мусорные строки не попадают в сценарные предупреждения."""

    def test_h2s_no_removed_strings(self):
        parsed = _parsed(
            original_query="заменить трубу DN200 H2S",
            technical_filters={"medium": "H2S"},
        )
        warnings = build_scenario_warnings(parsed, "replacement")
        for w in _REMOVED_SCENARIO:
            self.assertNotIn(w, warnings)

    def test_h2s_keeps_contextual(self):
        parsed = _parsed(
            original_query="сколько запасов на складе H2S",
            technical_filters={"medium": "H2S"},
            operations=["inventory"],
            intents=["inventory"],
        )
        warnings = build_scenario_warnings(parsed, "inventory")
        self.assertTrue(
            any("суммировать" in w.lower() or "склад" in w.lower() for w in warnings),
            "Ожидалось хотя бы одно контекстное H2S-предупреждение",
        )


class FilterByIntentTest(unittest.TestCase):
    """Только при intent=maintenance ТОиР-черновики остаются в ответе."""

    def test_non_maintenance_filters(self):
        result = filter_by_intent(_TOIR + ["Полезное"], "replacement")
        self.assertNotIn(_TOIR[0], result)
        self.assertNotIn(_TOIR[1], result)
        self.assertIn("Полезное", result)

    def test_maintenance_keeps(self):
        result = filter_by_intent(_TOIR, "maintenance")
        self.assertEqual(len(result), 2)

    def test_empty(self):
        self.assertEqual(filter_by_intent([], "maintenance"), [])


class RegulationCleanupTest(unittest.TestCase):
    """В important_limitations осталась только одна запись — H2S."""

    def test_single_limitation(self):
        from app.services.agent.repository.json_repository import JsonRepository

        reg = JsonRepository().get_regulation()
        lims = reg.get("important_limitations", [])
        self.assertEqual(len(lims), 1)
        text = lims[0].lower()
        self.assertIn("h2s", text)
        for forbidden in _REMOVED_REG:
            self.assertNotIn(forbidden.lower(), text)


if __name__ == "__main__":
    unittest.main()
