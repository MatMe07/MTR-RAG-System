from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session

from app.models import MatchingRule
from app.schemas import ItemCard,RuleTrace


class RulesEngine:
    def __init__(self, db: Session):
        self.db = db
        self._load_rules()

    def _load_rules(self) -> None:
        rules = self.db.query(MatchingRule).all()
        self.rules_by_parameter = {}
        for rule in rules:
            key = rule.parameter
            if key not in self.rules_by_parameter:
                self.rules_by_parameter[key] = []
            self.rules_by_parameter[key].append({
                'rule_type': rule.rule_type,
                'from_value': rule.from_value,
                'to_value': rule.to_value,
                'allowed': rule.allowed,
                'penalty': rule.penalty,
                'condition': rule.condition,
                'source': rule.source
            })

    def evaluate(self, requested: ItemCard, candidate: ItemCard) -> Dict[str, Any]:
        comparison = self._compare_fields(requested, candidate)
        rules_results = self._apply_rules(comparison)
        score = self._calculate_score(comparison, rules_results)
        status = self._determine_status(score, rules_results['hard_filter'], rules_results['warnings'])
        explanation, expert_comment = self._generate_explanation(comparison, rules_results, status)
        rule_trace = self._build_rule_trace(rules_results)

        return {
            'status': status,
            'match_percent': round(score, 1),
            'matched_params': comparison['matched'],
            'mismatched_params': comparison['mismatched'],
            'missing_params': comparison['missing'],
            'warnings': rules_results['warnings'],
            'expert_comment': expert_comment,
            'explanation': explanation,
            'rule_trace': rule_trace
        }

    def _compare_fields(self, requested: ItemCard, candidate: ItemCard) -> Dict[str, Any]:
        """
        Сравнивает все поля двух карточек.
        Возвращает: matched, mismatched, missing списки.
        """
        matched = []
        mismatched = []
        missing = []

        req_val = requested.item_type
        cand_val = candidate.item_type
        if req_val is None:
            missing.append('item_type')
        elif cand_val is None:
            missing.append('item_type')
        elif req_val.lower() == cand_val.lower():
            matched.append('item_type')
        else:
            mismatched.append('item_type')

        req_val = requested.subtype
        cand_val = candidate.subtype
        if req_val is None:
            missing.append('subtype')
        elif cand_val is None:
            missing.append('subtype')
        elif req_val.lower() == cand_val.lower():
            matched.append('subtype')
        else:
            mismatched.append('subtype')

        req_val = requested.geometry.dn if requested.geometry else None
        cand_val = candidate.geometry.dn if candidate.geometry else None
        if req_val is None:
            missing.append('dn')
        elif cand_val is None:
            missing.append('dn')
        elif abs(req_val - cand_val) <= 0.1:
            matched.append('dn')
        else:
            mismatched.append('dn')

        req_val = requested.geometry.wall_thickness if requested.geometry else None
        cand_val = candidate.geometry.wall_thickness if candidate.geometry else None
        if req_val is None:
            missing.append('wall_thickness')
        elif cand_val is None:
            missing.append('wall_thickness')
        elif abs(req_val - cand_val) <= 0.1:
            matched.append('wall_thickness')
        else:
            mismatched.append('wall_thickness')

        req_val = requested.geometry.angle if requested.geometry else None
        cand_val = candidate.geometry.angle if candidate.geometry else None
        if req_val is None:
            missing.append('angle')
        elif cand_val is None:
            missing.append('angle')
        elif abs(req_val - cand_val) <= 0.1:
            matched.append('angle')
        else:
            mismatched.append('angle')

        req_val = requested.pressure.pn if requested.pressure else None
        cand_val = candidate.pressure.pn if candidate.pressure else None
        if req_val is None:
            missing.append('pressure')
        elif cand_val is None:
            missing.append('pressure')
        elif abs(req_val - cand_val) <= 0.1:
            matched.append('pressure')
        else:
            mismatched.append('pressure')

        req_val = requested.material.strength_class if requested.material else None
        cand_val = candidate.material.strength_class if candidate.material else None
        if req_val is None:
            missing.append('strength_class')
        elif cand_val is None:
            missing.append('strength_class')
        elif req_val == cand_val:
            matched.append('strength_class')
        else:
            mismatched.append('strength_class')

        req_val = requested.material.steel_grade if requested.material else None
        cand_val = candidate.material.steel_grade if candidate.material else None
        if req_val is None:
            missing.append('steel_grade')
        elif cand_val is None:
            missing.append('steel_grade')
        elif req_val == cand_val:
            matched.append('steel_grade')
        else:
            mismatched.append('steel_grade')

        req_val = requested.environment.medium if requested.environment else None
        cand_val = candidate.environment.medium if candidate.environment else None
        if req_val is None:
            missing.append('medium')
        elif cand_val is None:
            missing.append('medium')
        elif req_val.lower() == cand_val.lower():
            matched.append('medium')
        else:
            mismatched.append('medium')

        req_val = requested.environment.h2s_confirmed if requested.environment else None
        cand_val = candidate.environment.h2s_confirmed if candidate.environment else None
        if req_val is None:
            missing.append('h2s_confirmed')
        elif cand_val is None:
            missing.append('h2s_confirmed')
        elif req_val == cand_val:
            matched.append('h2s_confirmed')
        else:
            mismatched.append('h2s_confirmed')

        req_val = requested.environment.co2_confirmed if requested.environment else None
        cand_val = candidate.environment.co2_confirmed if candidate.environment else None
        if req_val is None:
            missing.append('co2_confirmed')
        elif cand_val is None:
            missing.append('co2_confirmed')
        elif req_val == cand_val:
            matched.append('co2_confirmed')
        else:
            mismatched.append('co2_confirmed')

        req_val = requested.coating.inner_coating if requested.coating else None
        cand_val = candidate.coating.inner_coating if candidate.coating else None
        if req_val is None:
            missing.append('inner_coating')
        elif cand_val is None:
            missing.append('inner_coating')
        elif req_val == cand_val:
            matched.append('inner_coating')
        else:
            mismatched.append('inner_coating')

        req_val = requested.coating.outer_coating if requested.coating else None
        cand_val = candidate.coating.outer_coating if candidate.coating else None
        if req_val is None:
            missing.append('outer_coating')
        elif cand_val is None:
            missing.append('outer_coating')
        elif req_val == cand_val:
            matched.append('outer_coating')
        else:
            mismatched.append('outer_coating')

        req_val = requested.environment.climate_version if requested.environment else None
        cand_val = candidate.environment.climate_version if candidate.environment else None
        if req_val is None:
            missing.append('climate_version')
        elif cand_val is None:
            missing.append('climate_version')
        elif req_val == cand_val:
            matched.append('climate_version')
        else:
            mismatched.append('climate_version')

        req_val = requested.normative.gost_tu if requested.normative else None
        cand_val = candidate.normative.gost_tu if candidate.normative else None
        if req_val is None:
            missing.append('gost_or_tu')
        elif cand_val is None:
            missing.append('gost_or_tu')
        elif req_val == cand_val:
            matched.append('gost_or_tu')
        else:
            mismatched.append('gost_or_tu')

        return {
            'matched': matched,
            'mismatched': mismatched,
            'missing': missing
        }

    def _apply_rules(self, comparison: Dict[str, List[str]]) -> Dict[str, Any]:
        hard_filter = False
        warnings = []
        expert_comments = []
        penalties = []
        allowed_replacements = []

        for field in comparison['mismatched']:
            rules = self.rules_by_parameter.get(field, [])
            for rule in rules:
                if rule['rule_type'] == 'hard_filter':
                    hard_filter = True
                    warnings.append(rule['condition'])
                elif rule['rule_type'] == 'warning':
                    warnings.append(rule['condition'])
                elif rule['rule_type'] == 'expert_comment':
                    expert_comments.append(rule['condition'])
                elif rule['rule_type'] == 'penalty':
                    penalties.append(rule['penalty'])
                elif rule['rule_type'] == 'allowed_replacement':
                    allowed_replacements.append(rule['condition'])

        for field in comparison['missing']:
            rules = self.rules_by_parameter.get(field, [])
            for rule in rules:
                if rule['rule_type'] == 'warning' and not rule.get('to_value'):
                    warnings.append(f"Нет данных по полю {field}")
                elif rule['rule_type'] == 'expert_comment':
                    expert_comments.append(f"Нет данных по полю {field}")

        total_penalty = sum(penalties)

        return {
            'hard_filter': hard_filter,
            'warnings': warnings,
            'expert_comments': expert_comments,
            'penalty': total_penalty,
            'allowed_replacements': allowed_replacements
        }

    def _calculate_score(
        self,
        comparison: Dict[str, List[str]],
        rules_results: Dict[str, Any]
    ) -> float:
        weights = {
            'item_type': 15,
            'subtype': 10,
            'dn': 15,
            'wall_thickness': 15,
            'angle': 15,
            'pressure': 10,
            'strength_class': 10,
            'steel_grade': 10,
            'medium': 10,
            'h2s_confirmed': 5,
            'co2_confirmed': 5,
            'inner_coating': 5,
            'outer_coating': 5,
            'climate_version': 5,
            'gost_or_tu': 5
        }

        matched = comparison['matched']
        mismatched = comparison['mismatched']
        missing = comparison['missing']

        max_score = 0
        earned_score = 0

        for field, weight in weights.items():
            if field in missing:
                continue
            max_score += weight

            if field in matched:
                earned_score += weight
            elif field in mismatched:
                earned_score += weight * 0.2

        if max_score == 0:
            return 0.0

        raw_score = (earned_score / max_score) * 100

        penalty = rules_results.get('penalty', 0)
        final_score = max(0, raw_score - penalty)

        return min(100, final_score)

    def _determine_status(
        self,
        score: float,
        hard_filter: bool,
        warnings: List[str]
    ) -> str:
        if hard_filter:
            return 'низкая релевантность'

        if warnings:
            return 'требует проверки'

        if score >= 90:
            return 'соответствует'
        elif score >= 70:
            return 'потенциальный аналог'
        elif score >= 50:
            return 'требует проверки'
        else:
            return 'низкая релевантность'

    def _generate_explanation(
        self,
        comparison: Dict[str, List[str]],
        rules_results: Dict[str, Any],
        status: str
    ) -> Tuple[str, str]:
        parts = []

        if comparison['matched']:
            parts.append(f"Совпало: {', '.join(comparison['matched'])}")

        if comparison['mismatched']:
            parts.append(f"Расхождения: {', '.join(comparison['mismatched'])}")

        if comparison['missing']:
            parts.append(f"Нет данных: {', '.join(comparison['missing'])}")

        if rules_results['warnings']:
            parts.append(f"Предупреждения: {'; '.join(rules_results['warnings'])}")

        if rules_results['expert_comments']:
            parts.append(f"Комментарий эксперту: {'; '.join(rules_results['expert_comments'])}")

        if rules_results['allowed_replacements']:
            parts.append(f"Возможная составная замена: {'; '.join(rules_results['allowed_replacements'])}")

        explanation = '. '.join(parts)

        expert_comment = None
        if rules_results['expert_comments']:
            expert_comment = '; '.join(rules_results['expert_comments'])

        if rules_results['warnings']:
            expert_comment = f"Проверить: {'; '.join(rules_results['warnings'])}"

        return explanation, expert_comment

    def _build_rule_trace(self, rules_results: Dict[str, Any]) -> List[RuleTrace]:
        traces = []

        for warning in rules_results.get('warnings', []):
            traces.append(
                RuleTrace(
                    rule_id="WARNING",
                    reaction="warning",
                    message=warning
                )
            )

        for comment in rules_results.get('expert_comments', []):
            traces.append(
                RuleTrace(
                    rule_id="EXPERT",
                    reaction="expert_comment",
                    message=comment
                )
            )

        for replacement in rules_results.get('allowed_replacements', []):
            traces.append(
                RuleTrace(
                    rule_id="REPLACEMENT",
                    reaction="expert_comment",
                    message=replacement
                )
            )

        if rules_results.get('hard_filter'):
            traces.append(
                RuleTrace(
                    rule_id="HARD_FILTER",
                    reaction="hard_filter",
                    message="Кандидат отклонен по жесткому фильтру"
                )
            )

        return traces
