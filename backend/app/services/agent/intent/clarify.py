# agent/intent/clarify.py

"""Диалоговое уточнение (Этап 1, §1G): до 3 циклов, статус REQUIRES_EXPERT.

Реализует 1G.1 (генератор вопроса), 1G.2 (состояние сессии), 1G.3 (слияние
текстов из прошлых итераций), 1G.4 (выход после 3 циклов → REQUIRES_EXPERT).
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from .detect import (
    detect_intents,
    determine_parsed_status,
    missing_required_for_intent,
)

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

# Тексты уточнений для несовместимых комбинаций (§1H.2 → маршрут clarify).
_CONFLICT_QUESTIONS = {
    "FIND_ALTERNATIVE / REPLACE_WITH_COMPOSITE": "Запрос содержит подбор аналога и замену на составную. Что нужно: аналог или составная замена?",
    "FIND_ALTERNATIVE / REPLACE_WITH_DIFFERENT_SIZE": "Запрос содержит подбор аналога и замену на другой DN. Что нужно: аналог или смена DN?",
    "CHECK_STOCK / LIST_OUT_OF_STOCK": "Запрос про наличие и про отсутствие одновременно. Проверить наличие или найти отсутствующие позиции?",
    "PLAN_REPAIR / FIND_BY_PARAMS": "Запрос содержит и план ремонта, и подбор по параметрам. Составить план или найти деталь?",
}


def _label(key: str) -> str:
    return _MISSING_LABELS.get(key, key)


def build_question(intent: str, missing: List[str]) -> str:
    """1G.1: вопрос по недостающим параметрам (специальные шаблоны + fallback)."""
    if not missing:
        return "Уточните, пожалуйста, что именно нужно найти или сделать."
    labels = [", ".join(_label(k) for k in missing)]

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


def _conflict_question(parsed: Any, primary: str) -> str:
    """Вопрос для несовместимых интентов (по ambiguity из enrich_parsed)."""
    for amb in getattr(parsed, "ambiguities", []) or []:
        if not isinstance(amb, str) or "Конфликт интентов" not in amb:
            continue
        for key, q in _CONFLICT_QUESTIONS.items():
            if key in amb:
                return q
    return "Запрос содержит противоречащие действия. Уточните, что именно нужно."


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


# Срок жизни сессии диалога уточнения (Redis TTL).
CLARIFY_SESSION_TTL = 3600


class ClarificationManager:
    """Состояние диалога уточнения по сессиям (1G.2).

    Хранилище — Redis (ключ `clarify:{session_id}`, TTL 1 час): атомарные
    read-modify-write (WATCH/MULTI) не теряют обновления при параллельных
    запросах. При недоступности Redis — in-memory fallback с блокировкой
    (офлайн-тесты, локальный запуск без стека).
    """

    DEFAULT_STATE: Dict[str, Any] = {
        "turns": 0,
        "text": "",
        "status": "",
        "missing": [],
    }

    def __init__(self, max_turns: int = MAX_CLARIFY_TURNS):
        self.max_turns = max_turns
        self._fallback: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(session_id: str) -> str:
        return f"clarify:{session_id}"

    @staticmethod
    def _parse_state(data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return dict(ClarificationManager.DEFAULT_STATE)
        return {
            "turns": int(data.get("turns", 0) or 0),
            "text": data.get("text") or "",
            "status": data.get("status") or "",
            "missing": data.get("missing") or [],
        }

    @staticmethod
    def _redis_cache():
        from ..repository.providers.redis_cache import get_redis_cache

        return get_redis_cache()

    def _load(self, session_id: str) -> Dict[str, Any]:
        cache = self._redis_cache()
        if cache.available:
            return self._parse_state(cache.get(self._key(session_id)))
        with self._lock:
            return self._fallback.setdefault(
                session_id, dict(self.DEFAULT_STATE)
            )

    def _tick(
        self, session_id: str, parsed: Any, query: str
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Применяет один «ход» диалога к состоянию сессии атомарно
        (Redis WATCH) или в fallback.

        Возвращает (decision, state, payload), где decision: proceed |
        clarify | expert, а payload описывает уточняющий вопрос
        (turn/intent/missing/question/status), когда decision == "clarify".
        """
        intents = detect_intents(parsed)
        status = determine_parsed_status(parsed, intents)
        primary = intents[0] if intents else ""
        outcome: Dict[str, Any] = {"decision": "", "turn": 0, "intent": primary,
                                   "missing": [], "question": "", "status": status}

        def _apply(sess: Any) -> Dict[str, Any]:
            state = self._parse_state(sess)
            state["status"] = status

            conflict = getattr(parsed, "status", "") == "UNCLEAR"
            if conflict:
                if state["turns"] >= self.max_turns:
                    outcome["decision"] = "expert"
                    return state
                state["turns"] += 1
                state["text"] = self._merge_state_text(state["text"], query)
                outcome.update(
                    decision="clarify",
                    status="UNCLEAR",
                    turn=state["turns"],
                    missing=[],
                    question=_conflict_question(parsed, primary),
                )
                return state

            if status == "COMPLETE" and intents:
                state["text"] = self._merge_state_text(state["text"], query)
                outcome["decision"] = "proceed"
                return state

            missing = (
                missing_required_for_intent(parsed, primary)
                if intents
                else ["item_type", "unit_id"]
            )
            if state["turns"] >= self.max_turns:
                outcome["decision"] = "expert"
                return state
            state["turns"] += 1
            state["text"] = self._merge_state_text(state["text"], query)
            state["missing"] = missing
            outcome.update(
                decision="clarify",
                status=status,
                turn=state["turns"],
                missing=missing,
                question=build_question(primary, missing),
            )
            return state

        cache = self._redis_cache()
        if cache.available:
            updated = cache.update(self._key(session_id), _apply, ttl=CLARIFY_SESSION_TTL)
            if updated is not None:
                return outcome["decision"], updated, outcome
        with self._lock:
            current = self._fallback.setdefault(session_id, dict(self.DEFAULT_STATE))
            updated = _apply(current)
            self._fallback[session_id] = updated
            return outcome["decision"], updated, outcome

    @staticmethod
    def _merge_state_text(prev: str, query: str) -> str:
        return (prev + " " + query).strip() if prev else query

    def merged_text(self, session_id: str, query: str) -> str:
        """1G.3: объединить новый текст с накопленным (прошлые итерации)."""
        return self._merge_state_text(self._load(session_id)["text"], query)

    def accumulated_text(self, session_id: str) -> str:
        """Накопленный текст диалога (включая ответы прошлых итераций)."""
        return self._load(session_id)["text"]

    def turns(self, session_id: str) -> int:
        return self._load(session_id)["turns"]

    def process(
        self,
        session_id: str,
        parsed: Any,
        query: str,
    ) -> str:
        """Вернёт 'proceed' (выполнить), 'expert' (1G.4) или бросит
        RequireClarification с вопросом."""
        decision, state, payload = self._tick(session_id, parsed, query)
        log.info(
            "[Clarify] session=%s decision=%s turn=%d status=%s",
            session_id, decision, state["turns"], state["status"],
        )
        if decision == "clarify":
            raise RequireClarification(
                session_id=session_id,
                turn=payload["turn"],
                intent=payload["intent"],
                missing=payload["missing"],
                question=payload["question"],
                status=payload["status"],
            )
        return decision

    def reset(self, session_id: str) -> None:
        cache = self._redis_cache()
        if cache.available:
            cache.delete(self._key(session_id))
        with self._lock:
            self._fallback.pop(session_id, None)


_manager: Optional[ClarificationManager] = None
_manager_lock = threading.Lock()


def get_clarification_manager() -> ClarificationManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ClarificationManager()
    return _manager
