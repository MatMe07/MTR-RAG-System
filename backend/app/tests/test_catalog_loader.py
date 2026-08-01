import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.scripts.load_data import catalog_card_to_payloads


class CatalogLoaderTest(unittest.TestCase):
    def test_builds_mtr_and_ksm_payloads_from_one_card(self):
        card = {
            "schema_version": "2.0",
            "item_type": "задвижка",
            "subtype": "клиновая",
            "name": "Задвижка клиновая DN150 PN40",
            "designation": "Задвижка клиновая DN150 PN40",
            "codes": {
                "mtr_code": "MTR-SYN-001",
                "ksm_code": "KSM-SYN-001",
            },
            "properties": {
                "pn": {"value": 40, "unit": "PN"},
                "standard": {"value": "ГОСТ 5762-2002"},
                "h2s_confirmed": {"value": None},
                "stock_qty": {"value": 7, "unit": "pcs"},
            },
        }

        mtr_payload, ksm_payload = catalog_card_to_payloads(card)

        self.assertEqual(mtr_payload["mtr_code"], "MTR-SYN-001")
        self.assertEqual(mtr_payload["schema_version"], 2)
        self.assertEqual(mtr_payload["properties"]["pn"]["value"], 40)
        self.assertEqual(
            mtr_payload["properties"]["gost_tu"]["value"],
            "ГОСТ 5762-2002",
        )
        self.assertIsNone(
            mtr_payload["properties"]["h2s_confirmed"]["value"]
        )
        self.assertEqual(ksm_payload["ksm_code"], "KSM-SYN-001")
        self.assertEqual(ksm_payload["quantity"], 7)
        self.assertEqual(ksm_payload["unit"], "pcs")

    def test_accepts_old_backend_property_names(self):
        card = {
            "item_type": "труба",
            "designation": "Труба 108x6",
            "codes": {"mtr_code": "MTR-OLD-001"},
            "properties": {
                "pressure": {"value": 63},
                "gost_or_tu": {"value": "ТУ 001"},
            },
        }

        mtr_payload, ksm_payload = catalog_card_to_payloads(card)

        self.assertIsNone(ksm_payload)
        self.assertEqual(mtr_payload["properties"]["pn"]["value"], 63)
        self.assertEqual(
            mtr_payload["properties"]["gost_tu"]["value"],
            "ТУ 001",
        )

    def test_rejects_card_without_mtr_code(self):
        with self.assertRaisesRegex(ValueError, "codes.mtr_code"):
            catalog_card_to_payloads(
                {
                    "item_type": "отвод",
                    "codes": {"ksm_code": "KSM-001"},
                    "properties": {},
                }
            )


if __name__ == "__main__":
    unittest.main()
