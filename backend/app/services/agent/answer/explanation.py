# agent/answer/explanation.py

"""ExplanationGenerator (ЭТАП 5, 5A.3): объяснения для ТЗ-ответа.

Два режима:
- Шаблонный (build_explanation): пер-компонентное поле `explanation`
  результатов ТЗ 11.2 по статусу кандидата и спискам параметров.
- LLM-генеративный (ExplanationGenerator / default_generator): холистическое
  топ-уровневое объяснение по RawResponse (запрос, критические параметры,
  кандидаты, проверки, предупреждения, ошибки). Активируется для статусов
  UNCLEAR / REQUIRES_EXPERT или при явном запросе «объясни».
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from app.services.agent.intent.matrix import BLOCKER_FIELDS

from .status import (
    STATUS_MATCH,
    STATUS_ANALOG,
    STATUS_MISMATCH,
    STATUS_NOT_FOUND,
    STATUS_UNCLEAR,
    STATUS_EXPERT,
    PARAM_LABELS,
)

log = logging.getLogger("mtr.agent.answer.explanation")

# Маркеры явного запроса на объяснение (в т.ч. опечатки из eval-наборов).
EXPLAIN_MARKERS = (
    "объясни", "объясн", "обисни",
    "почему", "расскажи", "что значит",
    "чем отличается", "чем отличаются", "в чем разница", "разница",
    "explain",
)


def _join(items: List[str], prefix: str) -> str:
    return prefix + ", ".join(items) + "." if items else ""


def should_use_llm(status: str, query: str) -> bool:
    """Критерий 5A.3: статусы UNCLEAR / REQUIRES_EXPERT или явное «объясни»."""
    if status in (STATUS_UNCLEAR, STATUS_EXPERT):
        return True
    q = str(query or "").lower()
    return any(marker in q for marker in EXPLAIN_MARKERS)


def _comp_get(comp: Any, key: str, default: Any = None) -> Any:
    if isinstance(comp, dict):
        return comp.get(key, default)
    return getattr(comp, key, default)


def _critical_param_labels(
    components: List[Any],
    warnings: List[str],
) -> List[str]:
    """Критические параметры (BLOCKER_FIELDS) из расхождений/недостатка данных."""
    labels = {PARAM_LABELS.get(k) for k in BLOCKER_FIELDS if k in PARAM_LABELS}
    blocked = set()
    for comp in components or []:
        for key in ("mismatched_params", "missing_params"):
            blocked |= set(_comp_get(comp, key) or [])
    for warning in warnings or []:
        for label in labels:
            if label and label.lower() in str(warning).lower():
                blocked.add(label)
    ordered = [l for l in labels if l and l in blocked]
    return ordered or [l for l in labels if l]


def _components_for_prompt(components: List[Any]) -> str:
    lines = []
    for c in (components or [])[:5]:
        name = _comp_get(c, "name") or _comp_get(c, "ksm_code") or _comp_get(c, "mtr_code")
        pct = _comp_get(c, "match_percent")
        state = _comp_get(c, "tz_status") or _comp_get(c, "status")
        if pct is not None:
            lines.append(f"- {name or '?'}: {pct}% ({state or ''})".strip())
        else:
            lines.append(f"- {name or '?'}: {state or ''}".strip())
    return "\n".join(lines) or "—"


def _compat_for_prompt(components: List[Any]) -> str:
    scored = [c for c in (components or []) if _comp_get(c, "match_percent") is not None]
    scored.sort(key=lambda c: _comp_get(c, "match_percent") or 0, reverse=True)
    c = scored[0] if scored else ((components or [None])[0] if components else None)
    if c is None:
        return "—"
    parts = []
    if _comp_get(c, "matched_params"):
        parts.append("Совпало: " + ", ".join(_comp_get(c, "matched_params")))
    if _comp_get(c, "mismatched_params"):
        parts.append("Расхождение: " + ", ".join(_comp_get(c, "mismatched_params")))
    if _comp_get(c, "missing_params"):
        parts.append("Нет данных: " + ", ".join(_comp_get(c, "missing_params")))
    return "; ".join(parts) if parts else "—"


def build_explanation_prompt(context: Dict[str, Any]) -> str:
    """Промпт LLM-режима 5A.3 (адаптация под структуру AgentAnswer)."""
    return (
        "Ты — технический эксперт по МТР. На основе следующих данных составь "
        "понятное объяснение для инженера.\n\n"
        f"Критические параметры (нельзя менять, они должны совпадать): "
        f"{context.get('critical_params') or '—'}\n"
        f"Запрос: {context.get('query') or ''}\n"
        f"Найденные детали:\n{context.get('candidates') or '—'}\n"
        f"Результаты проверок: {context.get('compatibility') or '—'}\n"
        f"Предупреждения: {context.get('warnings') or '—'}\n"
        f"Ошибки: {context.get('errors') or '—'}\n\n"
        "Твой ответ должен быть:\n"
        "1. Кратким (3–5 предложений).\n"
        "2. Содержать рекомендацию (какую деталь выбрать, что проверить).\n"
        "3. Если есть риски — указать их.\n"
        "4. Не повторять сухие технические данные — переформулировать их.\n"
        "5. Если хотя бы один критический параметр не совпал — явно указать это.\n\n"
        "Ответ:"
    )


def build_llm_context(
    *,
    status: str,
    query: str,
    parsed: Any,
    components: List[Any],
    warnings: List[str],
    errors: Optional[List[Any]],
    recommendations: List[str],
) -> Dict[str, Any]:
    """Контекст RawResponse для генератора объяснения (5A.3)."""
    return {
        "status": status,
        "query": query,
        "critical_params": _critical_param_labels(components, warnings),
        "candidates": _components_for_prompt(components),
        "compatibility": _compat_for_prompt(components),
        "warnings": [str(w) for w in (warnings or [])],
        "errors": [str(e) for e in (errors or [])],
        "recommendations": [str(r) for r in (recommendations or [])],
        "parsed": parsed,
    }


def default_generator(context: Dict[str, Any]) -> Optional[str]:
    """LLM-генератор по умолчанию через LLMClient (только при конфигурации).

    Безопасный путь: без AGENT_LLM_MODE=on, без ключа API или при ошибке LLM
    возвращает None — вызов не ломает детерминированный контур.
    """
    from ..core.config import DEFAULT_CONFIG

    if not DEFAULT_CONFIG.use_llm:
        return None
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")):
        return None
    try:
        from ..llm.client import get_llm_client

        client = get_llm_client(DEFAULT_CONFIG)
        if client is None:
            return None
        text = client.invoke(build_explanation_prompt(context))
        return (text or "").strip() or None
    except Exception as e:  # noqa: BLE001
        log.warning("[explanation] LLM explanation failed, fallback to template: %s", e)
        return None


class ExplanationGenerator:
    """Генератор холистического объяснения (5A.3, LLM-режим).

    generator — инжектируемая функция контекста в текст (по умолчанию —
    default_generator поверх LLMClient). Возвращает None, если LLM-режим не
    применим (нет триггера/генератора, ошибка) — шаблоны сохраняются.
    """

    def __init__(self, generator: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None):
        self._generator = generator or default_generator

    def available(self, status: str, query: str) -> bool:
        return should_use_llm(status, query)

    def generate(
        self,
        *,
        status: str,
        query: str,
        mode: str = "offline_rules",
        parsed: Any = None,
        components: Optional[List[Any]] = None,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[Any]] = None,
        recommendations: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Только при триггере; любой сбой → None (fallback на шаблоны)."""
        if mode == "llm" or not self.available(status, query):
            return None
        context = build_llm_context(
            status=status,
            query=query,
            parsed=parsed,
            components=components or [],
            warnings=warnings or [],
            errors=errors,
            recommendations=recommendations or [],
        )
        try:
            return self._generator(context) or None
        except Exception as e:  # noqa: BLE001
            log.warning("[explanation] generator failed, fallback to template: %s", e)
            return None


def build_explanation(
    status: str,
    matched: Optional[List[str]] = None,
    mismatched: Optional[List[str]] = None,
    missing: Optional[List[str]] = None,
) -> str:
    matched = matched or []
    mismatched = mismatched or []
    missing = missing or []

    if status == STATUS_MATCH:
        parts = ["Совпали все критические параметры."]
        parts.append(_join(matched, "Совпало: "))
        return " ".join(p for p in parts if p)
    if status == STATUS_ANALOG:
        parts = ["Найден потенциальный аналог."]
        parts.append(_join(matched, "Совпало: "))
        parts.append(_join(mismatched, "Расхождение: "))
        parts.append(_join(missing, "Нет данных по: "))
        return " ".join(p for p in parts if p)
    if status == STATUS_MISMATCH:
        parts = ["Существенные расхождения параметров с запросом."]
        parts.append(_join(mismatched, "Расхождение: "))
        parts.append(_join(missing, "Нет данных по: "))
        return " ".join(p for p in parts if p)
    if status == STATUS_NOT_FOUND:
        return "В каталоге нет подходящих позиций по запросу."
    if status == STATUS_UNCLEAR:
        return "Запрос не удалось однозначно интерпретировать: уточните параметры."
    if status == STATUS_EXPERT:
        return "Требуется экспертная проверка: критические параметры не подтверждены."
    return ""