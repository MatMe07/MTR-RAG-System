"""LLM-синтез итогового ответа агента (этап L3).

Собирает связный ответ пользователю из структурированных результатов тулов.
Не меняет структуру AgentAnswer (components/warnings/sources/missing остаются
заполненными детерминированно) — только переписывает answer и переводит mode
в "llm_augmented". При недоступности LLM оставляет исходный answer.
"""

from typing import List, Optional

from app.schemas import AgentAnswer
from app.services.llm_service import LLMService


LLM_SYNTHESIS_PROMPT = """
Ты — инженерный ассистент по подбору МТР/КСМ. Составь связный ответ эксперту
на основе результатов инструментов. Ничего не выдумывай: используй только данные
из входных блоков.

Требования:
- Начни с короткого вывода по запросу.
- Перечисли кандидатов/позиции с ключевыми параметрами (DN, PN, материал, тип).
- Отдели совпадения, расхождения и неизвестные данные.
- Сохрани обязательные предупреждения дословно.
- Укажи, что именно нужно проверить эксперту перед решением.
- Перечисли неизвестные параметры (если есть).
- Не утверждай окончательную применимость изделия.
- Пиши по-русски, кратко и структурно (маркированный список).

Интент запроса: {intent}
Текст результатов инструментов:
{tool_texts}

Позиции (JSON):
{components}

Предупреждения:
{warnings}

Источники:
{sources}

Неизвестные параметры:
{missing}
"""


class AnswerSynthesizer:
    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or LLMService()

    def synthesize(self, answer: AgentAnswer, tool_texts: List[str]) -> Optional[str]:
        if not (answer.components or answer.warnings or tool_texts):
            return None
        prompt = LLM_SYNTHESIS_PROMPT.format(
            intent=answer.intent_label or answer.intent or "",
            tool_texts="\n".join(tool_texts) or "—",
            components=answer.model_dump_json() if hasattr(answer, "model_dump_json") else str(answer.components),
            warnings="; ".join(answer.warnings) or "—",
            sources="; ".join(f"{s.kind}:{s.id}" for s in answer.sources) or "—",
            missing="; ".join(answer.missing_parameters) or "—",
        )
        try:
            response = self.llm.invoke(prompt)
            text = getattr(response, "content", None)
            if isinstance(text, str) and text.strip():
                return text.strip()
        except Exception:
            return None
        return None


def apply_llm_synthesis(answer: AgentAnswer, tool_texts: List[str],
                        synthesizer: Optional[AnswerSynthesizer] = None) -> AgentAnswer:
    text = (synthesizer or AnswerSynthesizer()).synthesize(answer, tool_texts)
    if text:
        answer.answer = text
        answer.mode = "llm_augmented"
    return answer
