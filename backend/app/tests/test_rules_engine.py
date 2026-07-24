import unittest
from types import SimpleNamespace

from app.models import MatchingRule, ReplacementSet
from app.schemas import Geometry, ItemCard
from app.services.rules_engine import RulesEngine


class FakeQuery:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, rules=None, replacements=None):
        self.rules = rules or []
        self.replacements = replacements or []

    def query(self, model):
        if model is MatchingRule:
            return FakeQuery(self.rules)
        if model is ReplacementSet:
            return FakeQuery(self.replacements)
        raise AssertionError(f"Неожиданная модель: {model}")


def rule(
    rule_id,
    rule_type,
    parameter,
    from_value=None,
    to_value=None,
    allowed=False,
    penalty=0,
    condition="Тестовое правило",
):
    return SimpleNamespace(
        id=rule_id,
        rule_type=rule_type,
        parameter=parameter,
        from_value=from_value,
        to_value=to_value,
        allowed=allowed,
        penalty=penalty,
        condition=condition,
        source=f"R-{rule_id}",
    )


def replacement(
    replacement_id,
    target_angle,
    component_angle,
    quantity,
):
    return SimpleNamespace(
        id=replacement_id,
        target_item_type="отвод",
        target_angle=target_angle,
        target_dn=159,
        component_item_type="отвод",
        component_angle=component_angle,
        component_dn=159,
        quantity=quantity,
        condition=(
            f"{quantity} отвода по {component_angle}° "
            f"вместо одного отвода {target_angle}°"
        ),
        source=f"RS-{replacement_id}",
    )


def characteristic(value, value_type=None):
    if value_type is None:
        if isinstance(value, bool) or value is None:
            value_type = "boolean"
        elif isinstance(value, (int, float)):
            value_type = "number"
        else:
            value_type = "string"
    return {
        "value": value,
        "value_type": value_type,
        "raw_value": None,
        "unit": None,
        "status": "unknown" if value is None else "normalized",
        "confidence": None if value is None else 1,
        "source_fragment_ids": [],
    }


def card(item_type="отвод", **properties):
    return {
        "schema_version": "2.0",
        "card_id": None,
        "card_version": 1,
        "lifecycle_status": "normalized",
        "item_type": item_type,
        "subtype": None,
        "name": None,
        "designation": None,
        "codes": {
            "mtr_code": None,
            "ksm_code": None,
        },
        "dcd": {
            "domain": None,
            "collection": None,
            "document": None,
        },
        "properties": {
            name: characteristic(value)
            for name, value in properties.items()
        },
        "sources": [],
    }


class RulesEngineTest(unittest.TestCase):
    def test_full_match(self):
        engine = RulesEngine(FakeSession())
        requested = card(dn=159, angle=90, steel_grade="09Г2С")
        candidate = card(dn=159, angle=90, steel_grade="09Г2С")

        result = engine.evaluate(requested, candidate)

        self.assertEqual("соответствует", result["status"])
        self.assertEqual(100.0, result["match_percent"])
        self.assertEqual([], result["mismatched_params"])
        self.assertEqual([], result["missing_params"])
        self.assertEqual([], result["rule_trace"])

    def test_dn_mismatch_checks_from_to_allowed_and_penalty(self):
        rules = [
            rule(
                1,
                "hard_filter",
                "dn",
                from_value="159",
                to_value="219",
                allowed=False,
                penalty=40,
                condition="DN не допускает прямую замену",
            ),
            rule(
                2,
                "hard_filter",
                "dn",
                from_value="159",
                to_value="325",
                allowed=False,
                penalty=99,
                condition="Это правило не должно сработать",
            ),
        ]
        engine = RulesEngine(FakeSession(rules=rules))

        result = engine.evaluate(card(dn=159), card(dn=219))

        self.assertEqual("низкая релевантность", result["status"])
        self.assertEqual(["dn"], result["mismatched_params"])
        self.assertEqual(["R-1"], [trace.rule_id for trace in result["rule_trace"]])
        self.assertLess(result["match_percent"], 50)
        self.assertIn("159", result["rule_trace"][0].message)
        self.assertIn("219", result["rule_trace"][0].message)
        self.assertIn("не разрешено", result["rule_trace"][0].message)

    def test_unknown_coating_requires_expert_review(self):
        engine = RulesEngine(FakeSession())

        result = engine.evaluate(
            card(inner_coating=True),
            card(inner_coating=None),
        )

        self.assertEqual("требует проверки", result["status"])
        self.assertIn("inner_coating", result["missing_params"])
        self.assertTrue(
            any("Внутреннее покрытие" in warning for warning in result["warnings"])
        )
        self.assertTrue(
            any(
                trace.rule_id == "SYSTEM-INNER_COATING"
                for trace in result["rule_trace"]
            )
        )

    def test_unknown_h2s_requires_expert_review(self):
        engine = RulesEngine(FakeSession())

        result = engine.evaluate(
            card(medium="газ с H2S", h2s_confirmed=True),
            card(medium="газ с H2S", h2s_confirmed=None),
        )

        self.assertEqual("требует проверки", result["status"])
        self.assertIn("h2s_confirmed", result["missing_params"])
        self.assertTrue(any("H2S" in warning for warning in result["warnings"]))
        self.assertTrue(
            any(trace.rule_id == "SYSTEM-H2S" for trace in result["rule_trace"])
        )

    def test_composite_replacement_is_not_a_direct_analogue(self):
        engine = RulesEngine(
            FakeSession(
                replacements=[
                    replacement(
                        replacement_id=1,
                        target_angle=90,
                        component_angle=45,
                        quantity=2,
                    )
                ]
            )
        )

        result = engine.evaluate(
            card(dn=159, angle=90),
            card(dn=159, angle=45),
        )

        self.assertEqual("требует проверки", result["status"])
        self.assertIn("angle", result["mismatched_params"])
        self.assertTrue(
            any(
                trace.rule_id == "RS-1"
                and trace.reaction == "allowed_replacement"
                and "не прямой аналог" in trace.message
                for trace in result["rule_trace"]
            )
        )
        self.assertIn("2 отвода по 45°", result["expert_comment"])

    def test_legacy_item_card_remains_supported_during_migration(self):
        engine = RulesEngine(FakeSession())
        requested = ItemCard(
            item_type="отвод",
            geometry=Geometry(dn=159, angle=90),
            sources=[],
        )
        candidate = ItemCard(
            item_type="отвод",
            geometry=Geometry(dn=159, angle=90),
            sources=[],
        )

        result = engine.evaluate(requested, candidate)

        self.assertEqual("соответствует", result["status"])
        self.assertEqual(100.0, result["match_percent"])

if __name__ == "__main__":
    unittest.main()
