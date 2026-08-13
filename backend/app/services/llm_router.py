"""L4: LLM-маршрутизация поверх детерминированного search_router (этап 7).

Детерминированный `route_query_text` даёт baseline-решение. LLM уточняет
маршрут (ordinary/agent/clarification), интент и режим, когда baseline
неоднозначен: нет точного кода, нет нехватки параметров.

Детерминированные факты LLM не переопределяет: точный код МТР/КСМ всегда
ведёт в ordinary-режим exact, а нехватка параметров — в clarification.
При недоступности LLM, низкой уверенности или невалидном ответе
возвращается детерминированное решение.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.llm_service import LLMService
from .search_router import INTENT_LABELS, route_query_text


ALLOWED_ROUTES = {"ordinary", "agent", "clarification"}


class RoutingDecision(BaseModel):
    """Структурный ответ LLM-маршрутизатора."""
    route: str = Field(..., description="ordinary | agent | clarification")
    intent: str = Field("", description="Интент запроса")
    mode: str = Field("", description="Режим исполнения")
    reasons: List[str] = Field(default_factory=list, description="Причины решения")
    confidence: float = Field(0.0, description="Уверенность в решении 0..1")


ROUTE_PROMPT = """
Ты — маршрутизатор инженерной системы подбора МТР/КСМ.
Детерминированный модуль уже дал решение по запросу эксперта. Уточни его,
если эвристика неоднозначна, но не переопределяй очевидные факты
(точный код = ordinary, нехватка параметров = clarification).

Выбери один из маршрутов:
- ordinary: одиночный поиск по каталогу, точный код, простой фильтр;
- agent: нужно связать каталог, склад, объект, нормативы и документы
  (подбор замены, остатки, ТОиР, анализ влияния, сборка участка);
- clarification: не хватает параметров для поиска.

Возможные интенты: {intents}

Запрос эксперта:
{query}

Детерминированное решение:
{deterministic_json}

Верни строго JSON:
{{"route": "ordinary|agent|clarification", "intent": "<интент>",
  "mode": "<короткий режим>", "reasons": [строка, ...], "confidence": 0.0}}
"""


class LlmRouter:
    def __init__(self, llm: Optional[LLMService] = None,
                 min_confidence: float = 0.55):
        self.llm = llm or LLMService()
        self.min_confidence = min_confidence

    def route(self, query: str,
              deterministic: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        decision = dict(deterministic or route_query_text(query))
        decision["llm_refined"] = False

        if settings.AGENT_LLM_MODE == "off":
            return decision
        if decision.get("exact_codes") or decision.get("missing_parameters"):
            return decision

        try:
            prompt = ROUTE_PROMPT.format(
                intents=", ".join(sorted(INTENT_LABELS)),
                query=query,
                deterministic_json=dict(
                    route=decision["route"],
                    intent=decision["intent"],
                    mode=decision["mode"],
                    reasons=decision.get("reasons") or [],
                ),
            )
            result = self.llm.structured_invoke(prompt, RoutingDecision)
        except Exception:
            return decision

        if (
            getattr(result, "route", "") not in ALLOWED_ROUTES
            or getattr(result, "confidence", 0.0) < self.min_confidence
        ):
            return decision

        merged = dict(decision)
        merged["route"] = result.route
        intent = (result.intent or "").strip()
        if intent in INTENT_LABELS:
            merged["intent"] = intent
            merged["intent_label"] = INTENT_LABELS[intent]
        if (result.mode or "").strip():
            merged["mode"] = result.mode.strip()
        reasons = list(decision.get("reasons") or [])
        for item in result.reasons or []:
            text = f"LLM: {item}"
            if text not in reasons:
                reasons.append(text)
        merged["reasons"] = reasons
        merged["llm_refined"] = True
        merged["router_confidence"] = getattr(result, "confidence", 0.0)
        return merged
