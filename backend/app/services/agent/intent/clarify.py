# agent/intent/clarify.py

"""Диалоговое уточнение (Этап 1, §1G): до 3 циклов, статус REQUIRES_EXPERT.

Реализует 1G.1 (генератор вопроса), 1G.2 (состояние сессии), 1G.3 (слияние
текстов из прошлых итераций), 1G.4 (выход после 3 циклов → REQUIRES_EXPERT).
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from .detect import (
    determine_parsed_status,
    detect_intents,
    missing_required_for_intent,
)
from .matrix import INTENT_REQUIREMENTS

log = logging.getLogger("mtr.agent.intent.clarify")

MAX_CLARIFY_TURNS = 3

_MISSING_LABELS: Dict[str, str] = {
    "item_type": "тип изделия (труба, задвижка, отвод, фланец, ...)",
    "dn": "диаметр (DN)",
    "pn": "давление (PN)",
    "angle": "угол",
    "wall_thickness": "толщина стенки",
    "medium": "рабочую среду",
    "material": "материал / марку стали",
    "climate": "климатическое исполнение (У, ХЛ, УХЛ)",
    "component_id": "идентификатор компонента (COMP-SYN-XXX)",
    "unit_id": "идентификатор участка (UNIT-SYN-XXX)",
    "mtr_code": "код MTR",
    "ksm_code": "код KSM",
    "gost_tu": "ГОСТ/ТУ",
    "old_dn": "исходный диаметр (DN)",
    "new_dn": "новый диаметр (DN)",
    "old_medium": "текущую среду",
    "new_medium": "новую среду",
    "old_material": "текущий материал",
    "new_material": "новый материал",
    "old_pn": "текущее давление (PN)",
    "new_pn": "новое давление (PN)",
    "from_angle": "исходный угол",
    "to_angle": "новый угол",
    "term": "термин для объяснения",
    "term1": "первый термин",
    "term2": "второй термин",
    "from_value": "исходное значение",
    "to_value": "новое значение",
}


def _label(key: str) -> str:
    return _MISSING_LABELS.get(key, key)


def build_question(intent: str, missing: List[str]) -> str:
    """1G.1: вопрос по недостающим параметрам (специальные шаблоны + fallback)."""
    if not missing:
        return "Уточните, пожалуйста, что именно нужно найти или сделать."
    labels = [", ".join(_label(k) for k in missing)]
    text = " и " if len(missing) > 1 or True else " или "

    if "dn" in missing:
        return "Уточните, какой диаметр (DN) нужен?"
    if intent == "PLAN_REPAIR" and "component_id" in missing:
        return "Укажите идентификатор компонента (COMP-SYN-XXX) или участка (UNIT-SYN-XXX)."
    if "component_id" in missing and "unit_id" in missing:
        return "Укажите компонент (COMP-SYN-XXX) или участок (UNIT-SYN-XXX)."
    if "unit_id" in missing:
        return "Укажите участок, к которому относится запрос (UNIT-SYN-XXX)."
    if "new_medium" in missing or "old_medium" in missing:
        return "Укажите среду: текущую и новую (например, 'переведи участок с нефти на H2S')."
    if "item_type" in missing:
        return "Укажите тип изделия: труба, задвижка, отвод, переход, тройник, фланец, ..."
    return (
        "Недостаточно параметров для запроса: "
        + labels[0]
        + ". Уточните значения."
    )


class RequireClarification(Exception):
    """Исключение-сигнал: нужен ещё один цикл уточнения (1G)."""

    def __init__(
        self,
        session_id: str,
        turn: int,
        intent: str,
        missing: List[str],
        question: str,
        status: str = "",
    ):
        super().__init__(question)
        self.session_id = session_id
        self.turn = turn
        self.intent = intent
        self.missing = missing
        self.question = question
        self.status = status


class ClarificationManager:
    """Состояние диалога уточнения по сессиям (1G.2)."""

    def __init__(self, max_turns: int = MAX_CLARIFY_TURNS):
        self.max_turns = max_turns
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _session(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._sessions.setdefault(
                session_id,
                {"turns": 0, "text": "", "status": "", "missing": []},
            )

    def merged_text(self, session_id: str, query: str) -> str:
        """1G.3: объединить новый текст с накопленным (прошлые итерации)."""
        sess = self._session(session_id)
        prev = sess.get("text", "")
        return (prev + " " + query).strip() if prev else query

    def accumulated_text(self, session_id: str) -> str:
        """Накопленный текст диалога (включая ответы прошлых итераций)."""
        return self._session(session_id).get("text", "")

    def turns(self, session_id: str) -> int:
        return self._session(session_id).get("turns", 0)

    def process(
        self,
        session_id: str,
        parsed: Any,
        query: str,
    ) -> str:
        """Возвращает 'proceed' (нужно выполнить) или бросает RequireClarification.

        После max_turns циклов возвращает 'expert' (1G.4).
        """
        sess = self._session(session_id)
        intents = detect_intents(parsed)
        status = determine_parsed_status(parsed, intents)

        sess["status"] = status

        if status == "COMPLETE" and intents:
            sess["text"] = self.merged_text(session_id, query)
            return "proceed"

        primary = intents[0] if intents else ""
        missing = (
            missing_required_for_intent(parsed, primary)
            if intents
            else ["item_type", "unit_id"]
        )
        sess["missing"] = missing

        if sess["turns"] >= self.max_turns:
            return "expert"

        sess["turns"] += 1
        sess["text"] = self.merged_text(session_id, query)
        question = build_question(primary, missing)
        log.info(
            "[Clarify] turn=%d status=%s intent=%r missing=%s question=%r",
            sess["turns"], status, primary, missing, question,
        )
        raise RequireClarification(
            session_id=session_id,
            turn=sess["turns"],
            intent=primary,
            missing=missing,
            question=question,
            status=status,
        )

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


_manager: Optional[ClarificationManager] = None
_manager_lock = threading.Lock()


def get_clarification_manager() -> ClarificationManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ClarificationManager()
    return _manager