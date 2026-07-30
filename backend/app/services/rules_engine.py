from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Union

from sqlalchemy.orm import Session

from app.models import MatchingRule, ReplacementSet, MTRItem
from app.schemas import ItemCard, RuleTrace


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

BLOCKER_FIELDS = {"item_type", "dn"}

HARD_FILTER_RULE_TYPES = {"hard_filter"}


class RulesEngine:

    def __init__(self, db: Session):
        self.db = db
        self.rules_by_parameter: Dict[str, List[Dict[str, Any]]] = {}
        self.replacement_sets: List[Dict[str, Any]] = []
        self.synonyms: Dict[str, List[str]] = {}
        self._load_rules()
        self._load_synonyms()

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

    def _load_synonyms(self) -> None:
        from app.models import Synonym
        for syn in self.db.query(Synonym).all():
            if syn.normalized_value not in self.synonyms:
                self.synonyms[syn.normalized_value] = []
            self.synonyms[syn.normalized_value].append(syn.synonym)

    def reload(self) -> None:
        self.rules_by_parameter.clear()
        self.replacement_sets.clear()
        self.synonyms.clear()
        self._load_rules()
        self._load_synonyms()

    def evaluate(self, requested: Union[ItemCard, Dict], candidate: Union[ItemCard, Dict, MTRItem]) -> Dict[str, Any]:
        requested_values = self._card_to_values(requested)
        candidate_values = self._card_to_values(candidate)
        comparison = self._compare_values(requested_values, candidate_values)
        rules_result = self._apply_rules(comparison, requested_values, candidate_values)
        score = self._calculate_score(comparison, rules_result["penalty"])
        status = self._determine_status(comparison, rules_result)

        return {
            "status": status,
            "match_percent": round(score, 1),
            "matched_params": comparison["matched"],
            "mismatched_params": comparison["mismatched"],
            "missing_params": comparison["missing"],
            "warnings": rules_result["warnings"],
            "expert_comment": rules_result["expert_comment"],
            "explanation": rules_result["explanation"],
            "rule_trace": rules_result["traces"],
        }

    def _card_to_values(self, card: Any) -> Dict[str, Any]:
        data = self._as_dict(card)
        values: Dict[str, Any] = {}

        for field in ("item_type", "subtype", "designation", "name"):
            if field in data:
                values[field] = data.get(field)

        if "mtr_code" in data:
            values["mtr_code"] = data.get("mtr_code")
        if "ksm_code" in data:
            values["ksm_code"] = data.get("ksm_code")

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
        extra_good: List[str] = []
        details: Dict[str, Dict[str, Any]] = {}

        all_params = set(requested.keys()) | set(candidate.keys())
        skip_params = {"mtr_code", "ksm_code", "designation", "name"}

        for parameter in all_params:
            if parameter in skip_params:
                continue

            requested_value = requested.get(parameter)
            candidate_value = candidate.get(parameter)
            details[parameter] = {
                "requested": requested_value,
                "candidate": candidate_value,
            }

            if parameter in {"h2s_confirmed", "co2_confirmed", "inner_coating", "outer_coating"}:
                result = self._compare_boolean(parameter, requested_value, candidate_value)
                if result == "match":
                    matched.append(parameter)
                elif result == "mismatch":
                    mismatched.append(parameter)
                elif result == "extra_good":
                    extra_good.append(parameter)
                elif result == "missing":
                    missing.append(parameter)
                continue

            if requested_value is None or requested_value == "":
                if candidate_value is not None and candidate_value != "":
                    extra_good.append(parameter)
                continue

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
            "extra_good": extra_good,
            "details": details,
        }

    def _compare_boolean(self, parameter: str, requested_value: Any, candidate_value: Any) -> str:
        if requested_value is None:
            if candidate_value is True:
                return "extra_good"
            return "missing"

        if candidate_value is None:
            return "missing"

        if requested_value == candidate_value:
            return "match"
        return "mismatch"

    def _values_equal(self, parameter: str, left: Any, right: Any) -> bool:
        if left is None or right is None:
            return left is right

        if isinstance(left, bool) or isinstance(right, bool):
            return self._normalize_value(left) == self._normalize_value(right)

        left_num = self._to_float(left)
        right_num = self._to_float(right)
        if left_num is not None and right_num is not None:
            if parameter == "dn":
                tolerance = max(abs(left_num), abs(right_num)) * 0.1
            else:
                tolerance = NUMERIC_TOLERANCES.get(parameter, 1e-9)
            return abs(left_num - right_num) <= tolerance

        left_str = str(left).strip().lower()
        right_str = str(right).strip().lower()

        if left_str == right_str:
            return True

        if left_str in right_str or right_str in left_str:
            return True

        if self._synonyms_match(parameter, left_str, right_str):
            return True

        return False

    def _synonyms_match(self, parameter: str, left: str, right: str) -> bool:
        for norm, synonyms in self.synonyms.items():
            if norm == left and right in synonyms:
                return True
            if norm == right and left in synonyms:
                return True
            if left in synonyms and right in synonyms:
                return True
        return False

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

        for parameter in comparison["mismatched"]:
            requested_value = requested.get(parameter)
            candidate_value = candidate.get(parameter)

            for rule in self.rules_by_parameter.get(parameter, []):
                if not self._rule_matches(rule, requested_value, candidate_value):
                    continue

                rule_type = rule["rule_type"]

                if rule_type == "hard_filter" and not rule["allowed"]:
                    hard_filter = True
                    penalty += min(rule["penalty"], 100)
                    traces.append(
                        RuleTrace(
                            rule_id=self._rule_id(rule),
                            reaction=rule_type,
                            message=self._rule_message(rule, parameter, requested_value, candidate_value),
                        )
                    )
                    break

                if rule_type == "warning":
                    message = self._rule_message(rule, parameter, requested_value, candidate_value)
                    if message not in warnings:
                        warnings.append(message)
                elif rule_type == "expert_comment":
                    message = self._rule_message(rule, parameter, requested_value, candidate_value)
                    if message not in expert_comments:
                        expert_comments.append(message)
                elif rule_type == "allowed_replacement" and rule["allowed"]:
                    message = self._rule_message(rule, parameter, requested_value, candidate_value)
                    if message not in allowed_replacements:
                        allowed_replacements.append(message)
                elif rule_type == "penalty":
                    penalty += min(rule["penalty"], 100)

                traces.append(
                    RuleTrace(
                        rule_id=self._rule_id(rule),
                        reaction=rule_type,
                        message=self._rule_message(rule, parameter, requested_value, candidate_value),
                    )
                )

            if hard_filter:
                break

        if not hard_filter:
            for parameter in comparison["missing"]:
                if parameter in {"dn"}:
                    warnings.append(f"Нет данных по параметру {parameter}. Без DN изделие неприменимо.")
                else:
                    warnings.append(f"Нет данных по параметру {parameter}. Требуется проверка.")

        special_result = self._apply_expert_review_policies(requested, candidate)
        for w in special_result["warnings"]:
            if w not in warnings:
                warnings.append(w)
        traces.extend(special_result["traces"])

        replacement_result = self._find_composite_replacements(requested, candidate)
        for msg in replacement_result["messages"]:
            if msg not in allowed_replacements:
                allowed_replacements.append(msg)
        traces.extend(replacement_result["traces"])

        explanation = self._build_explanation(comparison, warnings, expert_comments, allowed_replacements)
        expert_comment = self._build_expert_comment(warnings, expert_comments, allowed_replacements)

        return {
            "hard_filter": hard_filter,
            "warnings": warnings,
            "expert_comments": expert_comments,
            "allowed_replacements": allowed_replacements,
            "penalty": min(penalty, 100),
            "traces": traces,
            "explanation": explanation,
            "expert_comment": expert_comment,
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
                message = f"{label} требуется, но у кандидата оно {candidate_state}."
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
                    message = f"Применимость к {chemical} требуется, но у кандидата она {candidate_state}."
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

            condition = replacement["condition"] or (
                f"{replacement['quantity']} шт. {replacement['component_item_type']} "
                f"{self._display_value(replacement['component_angle'])}° "
                f"вместо {replacement['target_item_type']} "
                f"{self._display_value(replacement['target_angle'])}°"
            )
            message = f"Составная замена, не прямой аналог: {condition}."
            messages.append(message)
            traces.append(
                RuleTrace(
                    rule_id=str(replacement["source"] or f"REPLACEMENT-{replacement['id'] or 'SET'}"),
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
            self._values_equal("item_type", replacement["target_item_type"], requested.get("item_type")),
            self._values_equal("angle", replacement["target_angle"], requested.get("angle")),
            self._values_equal("item_type", replacement["component_item_type"], candidate.get("item_type")),
            self._values_equal("angle", replacement["component_angle"], candidate.get("angle")),
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
        matched = comparison["matched"]
        mismatched = comparison["mismatched"]
        missing = comparison["missing"]
        extra_good = comparison.get("extra_good", [])

        max_score = 0
        earned_score = 0

        all_fields = set(matched) | set(mismatched) | set(missing)

        for field in all_fields:
            weight = FIELD_WEIGHTS.get(field, 5)
            max_score += weight
            if field in matched:
                earned_score += weight
            elif field in mismatched:
                earned_score += weight * 0.2
            elif field in missing:
                earned_score += weight * 0.0

        for field in extra_good:
            weight = FIELD_WEIGHTS.get(field, 5)
            earned_score += weight * 0.1

        if max_score == 0:
            return 0.0

        raw_score = (earned_score / max_score) * 100
        return max(0.0, min(100.0, raw_score - penalty))

    def _determine_status(
        self,
        comparison: Dict[str, Any],
        rules_result: Dict[str, Any],
    ) -> str:
        if rules_result["hard_filter"]:
            return "низкая релевантность"

        has_blocker = False
        for field in comparison["mismatched"]:
            if field in BLOCKER_FIELDS:
                has_blocker = True
                break

        if has_blocker:
            return "не соответствует"

        has_important_missing = False
        for field in comparison["missing"]:
            if field in {"dn", "wall_thickness", "angle", "h2s_confirmed", "inner_coating"}:
                has_important_missing = True
                break

        if (
            has_important_missing
            or rules_result["warnings"]
            or rules_result["expert_comments"]
            or rules_result["allowed_replacements"]
        ):
            return "требует проверки"

        score = self._calculate_score(comparison, rules_result["penalty"])

        if comparison.get("extra_good") and score >= 70:
            return "потенциальный аналог"

        if score >= 90:
            return "соответствует"
        if score >= 70:
            return "потенциальный аналог"
        if score >= 50:
            return "требует проверки"
        return "низкая релевантность"

    def _build_explanation(
        self,
        comparison: Dict[str, Any],
        warnings: List[str],
        expert_comments: List[str],
        allowed_replacements: List[str],
    ) -> str:
        parts = []
        if comparison["matched"]:
            parts.append(f"Совпало: {', '.join(comparison['matched'])}")
        if comparison["mismatched"]:
            parts.append(f"Расхождения: {', '.join(comparison['mismatched'])}")
        if comparison["missing"]:
            parts.append(f"Нет данных: {', '.join(comparison['missing'])}")
        if comparison.get("extra_good"):
            parts.append(f"Дополнительные подтверждения: {', '.join(comparison['extra_good'])}")
        if warnings:
            parts.append(f"Предупреждения: {'; '.join(warnings)}")
        if expert_comments:
            parts.append(f"Комментарий эксперту: {'; '.join(expert_comments)}")
        if allowed_replacements:
            parts.append(f"Составная замена: {'; '.join(allowed_replacements)}")
        return ". ".join(parts) or "Нет данных для сравнения."

    @staticmethod
    def _build_expert_comment(
        warnings: List[str],
        expert_comments: List[str],
        allowed_replacements: List[str],
    ) -> Optional[str]:
        parts = warnings + expert_comments + allowed_replacements
        return "; ".join(parts) if parts else None

    def _rule_matches(
        self,
        rule: Dict[str, Any],
        requested_value: Any,
        candidate_value: Any,
    ) -> bool:
        from_value = rule["from_value"]
        to_value = rule["to_value"]

        from_matches = True
        if from_value is not None and from_value != "":
            from_matches = self._rule_value_matches(from_value, requested_value)

        to_matches = True
        if to_value is not None and to_value != "":
            to_matches = self._rule_value_matches(to_value, candidate_value)

        return from_matches and to_matches

    def _rule_value_matches(self, expected: Any, actual: Any) -> bool:
        if expected is None or expected == "":
            return True
        if actual is None:
            return False

        expected_normalized = self._normalize_value(expected)
        actual_normalized = self._normalize_value(actual)
        if expected_normalized == actual_normalized:
            return True

        if isinstance(expected_normalized, str) and isinstance(actual_normalized, str):
            if expected_normalized in {"гост", "ту"}:
                return actual_normalized.startswith(expected_normalized)
        return False

    @staticmethod
    def _as_dict(card: Any) -> Dict[str, Any]:
        if isinstance(card, dict):
            return card
        if hasattr(card, "model_dump"):
            return card.model_dump()
        if hasattr(card, "dict"):
            return card.dict()
        if hasattr(card, "__dict__"):
            return {k: v for k, v in card.__dict__.items() if not k.startswith("_")}
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
    def _medium_requires(values: Dict[str, Any], chemical: str, confirmation_parameter: str) -> bool:
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

    def _rule_message(self, rule: Dict[str, Any], parameter: str, requested_value: Any, candidate_value: Any) -> str:
        condition = rule["condition"] or "Сработало правило сопоставления."
        allowed_text = "разрешено правилом" if rule["allowed"] else "не разрешено правилом"
        return f"{condition} Параметр {parameter}: требуется {self._display_value(requested_value)}, у кандидата {self._display_value(candidate_value)}; {allowed_text}."

    @staticmethod
    def _rule_id(rule: Dict[str, Any]) -> str:
        return str(rule["source"] or rule["id"] or "RULE")


_MISSING = object()
