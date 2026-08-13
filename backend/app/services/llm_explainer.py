"""L5: LLM-объяснение кандидатов «почему кандидат в выдаче» (этап 7).

Для каждого кандидата из каталога LLM объясняет, почему он подходит под
запрос эксперта, сравнивая только фактически указанные свойства карточки.
При недоступности LLM или пустых причинах — правило-фолбэк по типу изделия.
"""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm_service import LLMService


class CandidateExplanation(BaseModel):
    """Структурный ответ LLM-объяснения кандидата."""
    mtr_code: str = Field("", description="Код МТР объясняемого кандидата")
    reasons: List[str] = Field(default_factory=list, description="Почему кандидат подходит")
    confidence: float = Field(0.0, description="Уверенность в объяснении 0..1")


EXPLAIN_CANDIDATE_PROMPT = """
Ты — инженерный ассистент по подбору аналогов МТР/КСМ.
Объясни, почему кандидат попал в выдачу под запрос эксперта.
Сравнивай только фактически указанные в карточке кандидата свойства;
не выдумывай и не додумывай отсутствующие параметры.
Если какое-то требование запроса карточкой не подтверждается — так и скажи
(«в карточке не указано»).

Запрос эксперта:
{query}

Карточка кандидата (JSON):
{candidate_json}

Верни строго JSON:
{{"mtr_code": "<код из карточки>", "reasons": [строка, ...], "confidence": 0.0}}
"""


_ROLE_FALLBACK: Dict[str, str] = {
    "труба": "совпадение по типу «труба»; уточни DN, толщину стенки и материал",
    "отвод": "совпадение по типу «отвод»; уточни угол, DN и материал",
    "переход": "совпадение по типу «переход»; уточни диаметры d1/d2",
    "задвижка": "совпадение по типу «задвижка»; уточни DN, PN и исполнение",
    "заглушка": "совпадение по типу «заглушка»; уточни DN, PN и материал",
    "тройник": "совпадение по типу «тройник»; уточни DN и материал",
}


def rule_fallback(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Детерминированное объяснение по типу изделия (не требует LLM)."""
    item_type = candidate.get("item_type") or ""
    role = _ROLE_FALLBACK.get(item_type, "совпадение по категории изделия")
    reasons = [role]
    mtr = (candidate.get("codes") or {}).get("mtr_code") or candidate.get("mtr_code")
    if not mtr:
        mtr = (candidate.get("codes") or {}).get("ksm_code") or candidate.get("ksm_code")
    return {
        "mtr_code": mtr or "",
        "reasons": reasons,
        "confidence": 0.0,
        "llm": False,
    }


class LlmExplainer:
    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or LLMService()

    def explain(self, query: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
        if settings.AGENT_LLM_MODE == "off":
            return rule_fallback(candidate)
        card = {
            "mtr_code": (candidate.get("codes") or {}).get("mtr_code")
            or candidate.get("mtr_code"),
            "ksm_code": (candidate.get("codes") or {}).get("ksm_code")
            or candidate.get("ksm_code"),
            "name": candidate.get("name"),
            "item_type": candidate.get("item_type"),
            "properties": candidate.get("properties"),
        }
        try:
            prompt = EXPLAIN_CANDIDATE_PROMPT.format(
                query=query,
                candidate_json=json.dumps(card, ensure_ascii=False, default=str),
            )
            result = self.llm.structured_invoke(prompt, CandidateExplanation)
        except Exception:
            return rule_fallback(candidate)

        reasons = [r for r in (result.reasons or []) if str(r).strip()]
        if not reasons:
            return rule_fallback(candidate)
        return {
            "mtr_code": (result.mtr_code or "").strip() or card["mtr_code"] or "",
            "reasons": reasons,
            "confidence": getattr(result, "confidence", 0.0),
            "llm": True,
        }
