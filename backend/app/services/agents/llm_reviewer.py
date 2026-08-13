"""LLM-ревьюер поверх детерминированного чек-листа (этап 6b).

Проверяет черновик AgentAnswer по чек-листу из docs/architecture/agent_system.md
и docs/evaluation/query_routing_and_acceptance.md. Сначала выполняется
детерминированный ревьюер, затем LLM добавляет содержательные замечания
(выдуманные документы, смешивание false/null, непроверяемые утверждения).

При недоступности LLM результат детерминированного ревьюера возвращается как есть.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas import AgentAnswer
from app.services.llm_service import LLMService
from .reviewer import ReviewResult, review_answer


class ReviewVerdict(BaseModel):
    """Структурный ответ LLM-ревьюера."""
    verdict: str = Field(..., description="pass | needs_review")
    issues: List[str] = Field(default_factory=list, description="Замечания к ответу")


LLM_REVIEW_PROMPT = """
Ты — ревьюер ответов инженерного ассистента по подбору МТР/КСМ.
Проверь ответ по чек-листу. Не исправляй сам ответ, только найди замечания.

Чек-лист:
1. У каждого важного вывода есть источник (каталог, склад, граф, паспорт, ТУ, ГОСТ, ЛНД).
2. Обязательные предупреждения сохранены (пригодность к H2S/CO2 нельзя
   подтверждать только по совпадению DN/PN).
3. Не придуманы карточки, документы или позиции, которых нет в источниках.
4. Не смешаны «не подтверждено» (null) и «подтверждено как отсутствующее» (false).
5. Рекомендация отделена от решения эксперта: ассистент не утверждает аналог сам.
6. Неизвестные данные перечислены (missing_parameters).
7. Нет предложений деталей, отсутствующих в каталоге/на складе, как найденных.

Ответ ассистента (JSON):
{answer_json}

Замечания детерминированного ревьюера (могут быть пустыми):
{deterministic_issues}

Верни строго JSON: {{"verdict": "pass" | "needs_review", "issues": [строка, ...]}}.
Если замечаний нет — verdict "pass", issues [].
"""


class LLMReviewer:
    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or LLMService()

    def review(self, answer: AgentAnswer,
               expected: Optional[Dict[str, Any]] = None) -> ReviewResult:
        det = review_answer(answer, expected=expected)
        try:
            prompt = LLM_REVIEW_PROMPT.format(
                answer_json=answer.model_dump_json(exclude_none=True),
                deterministic_issues=det.issues,
            )
            verdict = self.llm.structured_invoke(prompt, ReviewVerdict)
        except Exception:
            return det

        issues = list(det.issues)
        for item in getattr(verdict, "issues", []) or []:
            if item and item not in issues:
                issues.append(item)
        final_verdict = "needs_review" if (issues or verdict.verdict == "needs_review") else "pass"
        checks = dict(det.checks)
        checks["llm_review"] = True
        return ReviewResult(verdict=final_verdict, issues=issues, checks=checks)


def apply_llm_review(answer: AgentAnswer,
                     expected: Optional[Dict[str, Any]] = None,
                     reviewer: Optional[LLMReviewer] = None) -> AgentAnswer:
    result = (reviewer or LLMReviewer()).review(answer, expected=expected)
    if result.issues:
        answer.review_issues = result.issues
        answer.review_verdict = result.verdict
        answer.human_review_required = answer.human_review_required or result.verdict == "needs_review"
    return answer
