import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import (
    Environment,
    ItemCard,
    Normative,
    Pressure,
)
from app.utils.jsonb_utils import (
    card_to_properties,
    get_property_value,
    normalize_properties,
    properties_to_card_dict,
)


class JsonbUtilsTest(unittest.TestCase):
    def test_normalizes_legacy_keys_and_preserves_metadata(self):
        properties = {
            "pressure": {
                "value": 40,
                "unit": "PN",
                "status": "expert_confirmed",
                "confidence": 1,
            },
            "gost_or_tu": {
                "value": "ГОСТ 5762-2002",
                "status": "normalized",
            },
            "stock_qty": {
                "value": 12,
                "unit": "pcs",
                "status": "inferred",
            },
        }

        normalized = normalize_properties(properties)

        self.assertNotIn("pressure", normalized)
        self.assertNotIn("gost_or_tu", normalized)
        self.assertEqual(normalized["pn"]["value"], 40)
        self.assertEqual(
            normalized["pn"]["status"],
            "expert_confirmed",
        )
        self.assertEqual(
            normalized["gost_tu"]["value"],
            "ГОСТ 5762-2002",
        )
        self.assertEqual(normalized["stock_qty"]["value"], 12)

    def test_derives_gost_tu_from_old_item_card_standard(self):
        normalized = normalize_properties(
            {
                "standard": {
                    "value": "ГОСТ 8731-2025",
                    "status": "normalized",
                }
            }
        )

        self.assertEqual(
            normalized["gost_tu"]["value"],
            "ГОСТ 8731-2025",
        )
        self.assertIn("standard", normalized)

    def test_read_supports_rows_written_with_previous_backend_keys(self):
        properties = {
            "pressure": {"value": 63},
            "gost_or_tu": {"value": "ТУ 001"},
        }

        self.assertEqual(get_property_value(properties, "pn"), 63)
        self.assertEqual(
            get_property_value(properties, "gost_tu"),
            "ТУ 001",
        )

    def test_item_card_round_trip_uses_canonical_keys(self):
        card = ItemCard(
            item_type="задвижка",
            pressure=Pressure(pn=40),
            environment=Environment(
                medium="газ с H2S",
                h2s_confirmed=None,
            ),
            normative=Normative(gost_tu="ГОСТ 5762-2002"),
            sources=[],
        )

        properties = card_to_properties(card)
        restored = properties_to_card_dict(properties)

        self.assertIn("pn", properties)
        self.assertIn("gost_tu", properties)
        self.assertNotIn("pressure", properties)
        self.assertNotIn("gost_or_tu", properties)
        self.assertEqual(restored["pressure"]["pn"], 40)
        self.assertEqual(
            restored["normative"]["gost_tu"],
            "ГОСТ 5762-2002",
        )


if __name__ == "__main__":
    unittest.main()
