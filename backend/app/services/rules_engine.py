from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models import MatchingRule, ReplacementSet
from app.schemas import RuleTrace


FIELD_ALIASES = {
    "pressure": "pn",
    "gost_or_tu": "gost_tu",
}

LEGACY_PATHS = {
    "mtr_code": ("mtr_code",),
    "ksm_code": ("ksm_code",),
    "item_type": ("item_type",),
    "subtype": ("subtype",),
    "designation": ("designation",),
    "dn": ("geometry", "dn"),
    "d1": ("geometry", "d1"),
    "d2": ("geometry", "d2"),
    "wall_thickness": ("geometry", "wall_thickness"),
    "wall_thickness_2": ("geometry", "wall_thickness_2"),
    "angle": ("geometry", "angle"),
    "radius": ("geometry", "radius"),
    "pn": ("pressure", "pn"),
    "working_pressure_mpa": ("pressure", "working_pressure_mpa"),
    "test_pressure_mpa": ("pressure", "test_pressure_mpa"),
    "steel_grade": ("material", "steel_grade"),
    "strength_class": ("material", "strength_class"),
    "material_standard": ("material", "standard"),
    "medium": ("environment", "medium"),
    "h2s_confirmed": ("environment", "h2s_confirmed"),
    "co2_confirmed": ("environment", "co2_confirmed"),
    "temperature_min_c": ("environment", "temperature_min_c"),
    "climate_version": ("environment", "climate_version"),
    "inner_coating": ("coating", "inner_coating"),
    "outer_coating": ("coating", "outer_coating"),
    "coating_type": ("coating", "coating_type"),
    "coating_standard": ("coating", "coating_standard"),
    "gost_tu": ("normative", "gost_tu"),
}

FIELD_WEIGHTS = {
    "item_type": 15,
    "subtype": 8,
    "dn": 15,
    "d1": 12,
    "d2": 12,
    "wall_thickness": 12,
    "wall_thickness_2": 8,
    "angle": 12,
    "pn": 10,
    "steel_grade": 10,
    "strength_class": 10,
    "medium": 8,
    "h2s_confirmed": 8,
    "co2_confirmed": 8,
    "inner_coating": 5,
    "outer_coating": 5,
    "coating_type": 5,
    "climate_version": 5,
    "gost_tu": 5,
}

NUMERIC_TOLERANCES = {
    "dn": 0.1,
    "d1": 0.1,
    "d2": 0.1,
    "wall_thickness": 0.1,
    "wall_thickness_2": 0.1,
    "angle": 0.1,
    "pn": 0.1,
    "working_pressure_mpa": 0.01,
    "test_pressure_mpa": 0.01,
    "temperature_min_c": 0.1,
}


class RulesEngine:
    """Evaluates a requested item card against one candidate.

    ItemCard v2 dictionaries are the primary input. Legacy Pydantic cards are
    supported while the backend and stored test data are being migrated.
    """

    def __init__(self, db: Session):
        self.db = db
        self.rules_by_parameter: Dict[str, List[Dict[str, Any]]] = {}
        self.replacement_sets: List[Dict[str, Any]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        for rule in self.db.query(MatchingRule).all():
            parameter = self._canonical_parameter(rule.parameter)
            self.rules_by_parameter.setdefault(parameter, []).append(
                {
                    "id": getattr(rule, "id", None),
                    "rule_type": rule.rule_type,
                    "parameter": parameter,
                    "from_value": rule.from_value,
                    "to_value": rule.to_value,
                    "allowed": bool(rule.allowed),
                    "penalty": int(rule.penalty or 0),
                    "condition": rule.condition,
                    "source": rule.source,
                }
            )

        for replacement in self.db.query(ReplacementSet).all():
            self.replacement_sets.append(
                {
                    "id": getattr(replacement, "id", None),
                    "target_item_type": replacement.target_item_type,
                    "target_angle": replacement.target_angle,
                    "target_dn": replacement.target_dn,
                    "component_item_type": replacement.component_item_type,
                    "component_angle": replacement.component_angle,
                    "component_dn": replacement.component_dn,
                    "quantity": replacement.quantity,
                    "condition": replacement.condition,
                    "source": replacement.source,
                }
            )

    def evaluate(self, requested: Any, candidate: Any) -> Dict[str, Any]:
        requested_values = self._card_to_values(requested)
        candidate_values = self._card_to_values(candidate)
        comparison = self._compare_values(requested_values, candidate_values)
        rules_result = self._apply_rules(
            comparison,
            requested_values,
            candidate_values,
        )
        score = self._calculate_score(comparison, rules_result["penalty"])
        status = self._determine_status(score, comparison, rules_result)
        explanation, expert_comment = self._generate_explanation(
            comparison,
            rules_result,
        )

        return {
            "status": status,
            "match_percent": round(score, 1),
            "matched_params": comparison["matched"],
            "mismatched_params": comparison["mismatched"],
            "missing_params": comparison["missing"],
            "warnings": rules_result["warnings"],
            "expert_comment": expert_comment,
            "explanation": explanation,
            "rule_trace": rules_result["traces"],
        }

    def _card_to_values(self, card: Any) -> Dict[str, Any]:
        data = self._as_dict(card)
        values: Dict[str, Any] = {}

        for field in ("item_type", "subtype", "designation", "name"):
            if field in data:
                values[field] = data.get(field)

        codes = data.get("codes")
        if isinstance(codes, dict):
            values["mtr_code"] = codes.get("mtr_code")
            values["ksm_code"] = codes.get("ksm_code")

        properties = data.get("properties")
        if isinstance(properties, dict):
            for parameter, characteristic in properties.items():
                parameter = self._canonical_parameter(parameter)
                if isinstance(characteristic, dict) and "value" in characteristic:
                    values[parameter] = characteristic.get("value")
                else:
                    values[parameter] = characteristic
            return values

        for parameter, path in LEGACY_PATHS.items():
            value = self._read_path(data, path)
            if value is not _MISSING:
                values[parameter] = value

        return values

    def _compare_values(
        self,
        requested: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        matched: List[str] = []
        mismatched: List[str] = []
        missing: List[str] = []
        details: Dict[str, Dict[str, Any]] = {}

        for parameter, requested_value in requested.items():
            if parameter in {"mtr_code", "ksm_code", "designation", "name"}:
                continue
            if requested_value is None or requested_value == "":
                continue

            candidate_value = candidate.get(parameter)
            details[parameter] = {
                "requested": requested_value,
                "candidate": candidate_value,
            }

            if candidate_value is None or candidate_value == "":
                missing.append(parameter)
            elif self._values_equal(parameter, requested_value, candidate_value):
                matched.append(parameter)
            else:
                mismatched.append(parameter)

        return {
            "matched": matched,
            "mismatched": mismatched,
            "missing": missing,
            "details": details,
        }

    def _apply_rules(
        self,
        comparison: Dict[str, Any],
        requested: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        hard_filter = False
        warnings: List[str] = []
        expert_comments: List[str] = []
        allowed_replacements: List[str] = []
        traces: List[RuleTrace] = []
        penalty = 0

        for parameter in comparison["mismatched"] + comparison["missing"]:
            requested_value = requested.get(parameter)
            candidate_value = candidate.get(parameter)

            for rule in self.rules_by_parameter.get(parameter, []):
                if not self._rule_matches(
                    rule,
                    requested_value,
                    candidate_value,
                ):
                    continue

                rule_type = rule["rule_type"]
                message = self._rule_message(
                    rule,
                    parameter,
                    requested_value,
                    candidate_value,
                )
                penalty += max(0, rule["penalty"])

                if rule_type == "hard_filter" and not rule["allowed"]:
                    hard_filter = True
                elif rule_type == "warning":
                    warnings.append(message)
                elif rule_type == "expert_comment":
                    expert_comments.append(message)
                elif rule_type == "allowed_replacement" and rule["allowed"]:
                    allowed_replacements.append(message)

                traces.append(
                    RuleTrace(
                        rule_id=self._rule_id(rule),
                        reaction=rule_type,
                        message=message,
                    )
                )

        special_result = self._apply_expert_review_policies(
            requested,
            candidate,
        )
        warnings.extend(special_result["warnings"])
        traces.extend(special_result["traces"])

        replacement_result = self._find_composite_replacements(
            requested,
            candidate,
        )
        allowed_replacements.extend(replacement_result["messages"])
        traces.extend(replacement_result["traces"])

        return {
            "hard_filter": hard_filter,
            "warnings": self._unique(warnings),
            "expert_comments": self._unique(expert_comments),
            "allowed_replacements": self._unique(allowed_replacements),
            "penalty": penalty,
            "traces": self._unique_traces(traces),
        }

    def _apply_expert_review_policies(
        self,
        requested: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        traces: List[RuleTrace] = []

        for parameter, label in (
            ("inner_coating", "Внутреннее покрытие"),
            ("outer_coating", "Наружное покрытие"),
        ):
            if requested.get(parameter) is True and candidate.get(parameter) is not True:
                candidate_state = self._boolean_state(candidate.get(parameter))
                message = (
                    f"{label} требуется, но у кандидата оно {candidate_state}. "
                    "Кандидата оставить в выдаче и передать эксперту."
                )
                warnings.append(message)
                traces.append(
                    RuleTrace(
                        rule_id=f"SYSTEM-{parameter.upper()}",
                        reaction="warning",
                        message=message,
                    )
                )

        for chemical, parameter in (
            ("H2S", "h2s_confirmed"),
            ("CO2", "co2_confirmed"),
        ):
            if self._medium_requires(requested, chemical, parameter):
                if candidate.get(parameter) is not True:
                    candidate_state = self._boolean_state(candidate.get(parameter))
                    message = (
                        f"Применимость к {chemical} требуется, но у кандидата "
                        f"она {candidate_state}. Требуется экспертная проверка."
                    )
                    warnings.append(message)
                    traces.append(
                        RuleTrace(
                            rule_id=f"SYSTEM-{chemical}",
                            reaction="warning",
                            message=message,
                        )
                    )

        return {"warnings": warnings, "traces": traces}

    def _find_composite_replacements(
        self,
        requested: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        messages: List[str] = []
        traces: List[RuleTrace] = []

        for replacement in self.replacement_sets:
            if not self._replacement_matches(replacement, requested, candidate):
                continue

            quantity = replacement["quantity"] or 1
            condition = replacement["condition"] or (
                f"{quantity} шт. {replacement['component_item_type']} "
                f"{self._display_value(replacement['component_angle'])}° "
                f"вместо {replacement['target_item_type']} "
                f"{self._display_value(replacement['target_angle'])}°"
            )
            message = (
                f"Составная замена, не прямой аналог: {condition}. "
                "Окончательное решение принимает эксперт."
            )
            messages.append(message)
            traces.append(
                RuleTrace(
                    rule_id=str(
                        replacement["source"]
                        or f"REPLACEMENT-{replacement['id'] or 'SET'}"
                    ),
                    reaction="allowed_replacement",
                    message=message,
                )
            )

        return {"messages": messages, "traces": traces}

    def _replacement_matches(
        self,
        replacement: Dict[str, Any],
        requested: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> bool:
        checks = (
            self._values_equal(
                "item_type",
                replacement["target_item_type"],
                requested.get("item_type"),
            ),
            self._values_equal(
                "angle",
                replacement["target_angle"],
                requested.get("angle"),
            ),
            self._values_equal(
                "item_type",
                replacement["component_item_type"],
                candidate.get("item_type"),
            ),
            self._values_equal(
                "angle",
                replacement["component_angle"],
                candidate.get("angle"),
            ),
        )
        if not all(checks):
            return False

        for expected, actual in (
            (replacement["target_dn"], requested.get("dn")),
            (replacement["component_dn"], candidate.get("dn")),
        ):
            if expected is not None and not self._values_equal("dn", expected, actual):
                return False
        return True

    def _calculate_score(
        self,
        comparison: Dict[str, Any],
        penalty: int,
    ) -> float:
        considered = (
            comparison["matched"]
            + comparison["mismatched"]
            + comparison["missing"]
        )
        if not considered:
            return 0.0

        max_score = sum(FIELD_WEIGHTS.get(field, 5) for field in considered)
        earned_score = sum(
            FIELD_WEIGHTS.get(field, 5)
            for field in comparison["matched"]
        )
        raw_score = (earned_score / max_score) * 100
        return max(0.0, min(100.0, raw_score - penalty))

    @staticmethod
    def _determine_status(
        score: float,
        comparison: Dict[str, Any],
        rules_result: Dict[str, Any],
    ) -> str:
        if rules_result["hard_filter"]:
            return "низкая релевантность"
        if (
            comparison["missing"]
            or rules_result["warnings"]
            or rules_result["expert_comments"]
            or rules_result["allowed_replacements"]
        ):
            return "требует проверки"
        if score >= 90:
            return "соответствует"
        if score >= 70:
            return "потенциальный аналог"
        if score >= 50:
            return "требует проверки"
        return "низкая релевантность"

    def _generate_explanation(
        self,
        comparison: Dict[str, Any],
        rules_result: Dict[str, Any],
    ) -> tuple[str, Optional[str]]:
        parts = []
        if comparison["matched"]:
            parts.append(f"Совпало: {', '.join(comparison['matched'])}")
        if comparison["mismatched"]:
            parts.append(
                f"Расхождения: {', '.join(comparison['mismatched'])}"
            )
        if comparison["missing"]:
            parts.append(
                f"У кандидата нет данных: {', '.join(comparison['missing'])}"
            )
        if rules_result["warnings"]:
            parts.append(
                f"Предупреждения: {'; '.join(rules_result['warnings'])}"
            )
        if rules_result["expert_comments"]:
            parts.append(
                "Комментарий эксперту: "
                + "; ".join(rules_result["expert_comments"])
            )
        if rules_result["allowed_replacements"]:
            parts.append(
                "Составная замена: "
                + "; ".join(rules_result["allowed_replacements"])
            )

        expert_parts = (
            rules_result["warnings"]
            + rules_result["expert_comments"]
            + rules_result["allowed_replacements"]
        )
        expert_comment = "; ".join(self._unique(expert_parts)) or None
        return ". ".join(parts), expert_comment

    def _rule_matches(
        self,
        rule: Dict[str, Any],
        requested_value: Any,
        candidate_value: Any,
    ) -> bool:
        return self._rule_value_matches(
            rule["from_value"],
            requested_value,
        ) and self._rule_value_matches(
            rule["to_value"],
            candidate_value,
        )

    def _rule_value_matches(self, expected: Any, actual: Any) -> bool:
        if expected is None or expected == "":
            return True
        if actual is None:
            return False

        expected_normalized = self._normalize_value(expected)
        actual_normalized = self._normalize_value(actual)
        if expected_normalized == actual_normalized:
            return True

        if isinstance(expected_normalized, str) and isinstance(
            actual_normalized,
            str,
        ):
            if expected_normalized in {"гост", "ту"}:
                return actual_normalized.startswith(expected_normalized)
        return False

    def _values_equal(self, parameter: str, left: Any, right: Any) -> bool:
        if left is None or right is None:
            return left is right
        if isinstance(left, bool) or isinstance(right, bool):
            return self._normalize_value(left) is self._normalize_value(right)

        left_number = self._to_float(left)
        right_number = self._to_float(right)
        if left_number is not None and right_number is not None:
            tolerance = NUMERIC_TOLERANCES.get(parameter, 1e-9)
            return abs(left_number - right_number) <= tolerance

        return self._normalize_value(left) == self._normalize_value(right)

    @staticmethod
    def _as_dict(card: Any) -> Dict[str, Any]:
        if isinstance(card, dict):
            return card
        if hasattr(card, "model_dump"):
            return card.model_dump()
        if hasattr(card, "dict"):
            return card.dict()
        raise TypeError("Карточка должна быть словарём или Pydantic-моделью")

    @staticmethod
    def _read_path(data: Dict[str, Any], path: Iterable[str]) -> Any:
        current: Any = data
        for part in path:
            if not isinstance(current, dict) or part not in current:
                return _MISSING
            current = current[part]
        return current

    @staticmethod
    def _canonical_parameter(parameter: str) -> str:
        return FIELD_ALIASES.get(parameter, parameter)

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            normalized = value.strip().replace(",", ".")
            lowered = normalized.casefold()
            if lowered in {"true", "да", "yes"}:
                return True
            if lowered in {"false", "нет", "no"}:
                return False
            try:
                return float(normalized)
            except ValueError:
                return " ".join(lowered.split())
        return value

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip().replace(",", "."))
            except ValueError:
                return None
        return None

    @staticmethod
    def _medium_requires(
        values: Dict[str, Any],
        chemical: str,
        confirmation_parameter: str,
    ) -> bool:
        if values.get(confirmation_parameter) is True:
            return True
        medium = values.get("medium")
        return isinstance(medium, str) and chemical.casefold() in medium.casefold()

    @staticmethod
    def _boolean_state(value: Any) -> str:
        if value is True:
            return "подтверждено"
        if value is False:
            return "явно не подтверждено"
        return "не подтверждено по доступным источникам"

    @staticmethod
    def _display_value(value: Any) -> str:
        if value is None:
            return "нет данных"
        if value is True:
            return "да"
        if value is False:
            return "нет"
        return str(value)

    def _rule_message(
        self,
        rule: Dict[str, Any],
        parameter: str,
        requested_value: Any,
        candidate_value: Any,
    ) -> str:
        condition = rule["condition"] or "Сработало правило сопоставления."
        allowed_text = "разрешено правилом" if rule["allowed"] else "не разрешено правилом"
        return (
            f"{condition} Параметр {parameter}: требуется "
            f"{self._display_value(requested_value)}, у кандидата "
            f"{self._display_value(candidate_value)}; {allowed_text}."
        )

    @staticmethod
    def _rule_id(rule: Dict[str, Any]) -> str:
        return str(rule["source"] or rule["id"] or "RULE")

    @staticmethod
    def _unique(values: Iterable[str]) -> List[str]:
        return list(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _unique_traces(traces: Iterable[RuleTrace]) -> List[RuleTrace]:
        result = []
        seen = set()
        for trace in traces:
            key = (trace.rule_id, trace.reaction, trace.message)
            if key in seen:
                continue
            seen.add(key)
            result.append(trace)
        return result


_MISSING = object()
