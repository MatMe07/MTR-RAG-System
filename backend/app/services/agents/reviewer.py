"""Ревьюер агентского ответа (этап 6 плана).

Детерминированный чек-лист на черновике AgentAnswer по требованиям
docs/architecture/agent_system.md и docs/evaluation/query_routing_and_acceptance.md:
- у важных выводов есть источники;
- обязательное предупреждение сохранено (для вопросов из 40-критериев);
- используются требуемые источники;
- ответ не пустой и покрывает обязательные части;
- неизвестные данные перечислены (missing_parameters);
- финальное решение оставлено эксперту (human_review_required).

LLM-ревьюер (agents/llm_reviewer.py) работает поверх этого чек-листа.
"""

from typing import Any, Dict, List, Optional

from app.schemas import AgentAnswer


class ReviewResult:
    """Результат проверки: вердикт, замечания и по-критериальные флаги."""

    def __init__(self, verdict: str, issues: List[str], checks: Dict[str, bool]):
        self.verdict = verdict  # "pass" | "needs_review"
        self.issues = issues
        self.checks = checks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "issues": self.issues,
            "checks": self.checks,
        }


def _fragment_ok(text: str, fragment: str) -> bool:
    if not fragment:
        return True
    return fragment.lower() in (text or "").lower()


def review_answer(answer: AgentAnswer,
                  expected: Optional[Dict[str, Any]] = None) -> ReviewResult:
    """Проверяет черновик ответа агента.

    expected — критерии конкретного вопроса из complex_questions_40.jsonl:
    mandatory_warning, required_sources, answer_must_include. Без expected
    выполняется только общий чек-лист.
    """
    issues: List[str] = []
    checks: Dict[str, bool] = {}

    # 1. Источники для позиций
    if answer.components and not answer.sources:
        issues.append("Позиции ответа не имеют источников (sources пуст).")
        checks["sources_for_components"] = False
    else:
        checks["sources_for_components"] = True

    # 2. Ответ не пустой
    has_answer = bool(answer.answer and answer.answer.strip())
    checks["answer_present"] = has_answer
    if not has_answer:
        issues.append("Ответ пуст: не удалось собрать данные по запросу.")

    # 3. Рекомендация отделена от решения эксперта.
    # Для интентов, где итогом является решение о применимости, обязательно
    # должна быть запрошена проверка эксперта.
    expert_intents = {"replacement", "impact_analysis", "maintenance",
                      "object_configuration", "inventory"}
    if answer.intent in expert_intents and not answer.human_review_required:
        issues.append("Интент требует решения эксперта, но human_review_required=False.")
        checks["expert_decision"] = False
    else:
        checks["expert_decision"] = True

    # 5. Критерии конкретного вопроса (40 вопросов)
    if expected:
        mw = expected.get("mandatory_warning")
        if mw:
            # Предупреждение считается сохранённым, если оно есть в структурном
            # поле warnings или в тексте ответа (LLM-синтез добавляет его туда).
            in_warnings = _fragment_ok(" ".join(answer.warnings), mw)
            in_answer = _fragment_ok(answer.answer or "", mw)
            if in_warnings or in_answer:
                checks["mandatory_warning"] = True
            else:
                checks["mandatory_warning"] = False
                issues.append(f"Потеряно обязательное предупреждение: {mw}")

        req_sources = expected.get("required_sources") or []
        have_sources = {s.kind for s in answer.sources}
        missing_sources = [r for r in req_sources if r not in have_sources]
        if missing_sources:
            checks["required_sources"] = False
            issues.append(f"Не хватает источников: {', '.join(sorted(missing_sources))}")
        else:
            checks["required_sources"] = True

        must_include = expected.get("answer_must_include") or []
        text = answer.answer or ""
        missing_parts = [m for m in must_include if not _fragment_ok(text, m)]
        if missing_parts:
            checks["answer_must_include"] = False
            issues.append(f"Ответ не содержит обязательных частей: {', '.join(missing_parts)}")
        else:
            checks["answer_must_include"] = True

    verdict = "needs_review" if issues else "pass"
    return ReviewResult(verdict=verdict, issues=issues, checks=checks)


def apply_review(answer: AgentAnswer,
                 expected: Optional[Dict[str, Any]] = None) -> AgentAnswer:
    """Вызывает review_answer и применяет результат к черновику ответа."""
    result = review_answer(answer, expected=expected)
    if result.issues:
        answer.review_issues = result.issues
        answer.review_verdict = result.verdict
        answer.human_review_required = answer.human_review_required or result.verdict == "needs_review"
    return answer
