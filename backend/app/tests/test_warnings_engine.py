import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import ParsedQuery
from app.services.agent.warnings import build_scenario_warnings


class BuildScenarioWarningsTest(unittest.TestCase):
    """Тексты предупреждений воспроизводятся правила-движком из JSON."""

    def test_h2s_base_warnings(self):
        parsed = ParsedQuery(
            original_query="нужен отвод 90",
            operations=["find"],
            item_types=["отвод"],
            technical_filters={"medium": "H2S"},
        )
        warnings = build_scenario_warnings(parsed, "catalog_search")
        self.assertIn(
            "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.",
            warnings,
        )

    def test_duplicates_warning(self):
        parsed = ParsedQuery(
            original_query="проверь дубли в каталоге по задвижкам",
            operations=["find"],
            item_types=["задвижка"],
        )
        warnings = build_scenario_warnings(parsed, "duplicates")
        self.assertIn(
            "Совпавшие параметры не доказывают, что корпоративные коды являются дублями.",
            warnings,
        )

    def test_all_warning_texts_come_from_json(self):
        json_path = (
            Path(__file__).parent.parent
            / "services"
            / "agents"
            / "scenario_warnings.json"
        )
        config = json.loads(json_path.read_text(encoding="utf-8"))
        texts = [
            rule["text"]
            for scenario in config["scenarios"]
            for rule in scenario["warnings"]
        ]
        self.assertGreater(len(texts), 20)
        # Внутри одного сценария тексты уникальны; между сценариями возможны
        # повторы (например, предупреждение о CO2 в средовых сценариях).
        for scenario in config["scenarios"]:
            local = [rule["text"] for rule in scenario["warnings"]]
            self.assertEqual(len(local), len(set(local)), scenario["id"])


if __name__ == "__main__":
    unittest.main()
