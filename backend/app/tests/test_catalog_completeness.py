import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.scripts.GEN.audit_catalog_completeness import (
    audit_catalog,
    load_cards,
)


class CatalogCompletenessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit_catalog(load_cards())

    def test_core_mvp_classes_are_complete(self):
        self.assertEqual(self.report["catalog_count"], 1000)
        self.assertTrue(self.report["core_mvp"]["complete"])
        self.assertEqual(self.report["core_mvp"]["missing"], [])

    def test_repair_kit_gaps_are_explicit(self):
        self.assertFalse(self.report["repair_kits"]["complete"])
        self.assertEqual(
            set(self.report["repair_kits"]["missing"]),
            {
                "фланец",
                "прокладка",
                "крепеж",
                "сварочный материал",
                "материал восстановления покрытия",
            },
        )

    def test_search_contract_properties_exist_in_every_card(self):
        for count in self.report["property_presence"].values():
            self.assertEqual(count, 1000)

    def test_unverified_medium_is_not_changed_to_false(self):
        self.assertEqual(
            self.report["unknown_values"]["h2s_confirmed"],
            1000,
        )
        self.assertEqual(
            self.report["unknown_values"]["co2_confirmed"],
            1000,
        )


if __name__ == "__main__":
    unittest.main()
