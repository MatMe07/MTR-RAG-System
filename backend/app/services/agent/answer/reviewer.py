# agent/answer/reviewer.py

from typing import Any, Dict, List, Tuple

_FALLBACK_ANSWER = "Не удалось собрать ответ: недостаточно данных."


def auto_review(
    result: Dict[str, Any],
    tools_used: List[str],
    sources: List[Any],
    answer_text: str,
) -> Tuple[str, List[str]]:
    """Детерминированное авторевью структурной корректности ответа.

    Вердикт "pass" означает: агент собрал структурированный ответ (текст,
    инструменты, источники) без фатальных ошибок исполнения. Это не отмена
    ручной/экспертной проверки решения (см. human_review_required) — ось
    авторевью проверяет полноту сборки, а не корректность доменного решения.
    """
    issues: List[str] = []

    if not answer_text or not answer_text.strip() or answer_text.strip() == _FALLBACK_ANSWER:
        issues.append("Ответ не собран")

    if not (tools_used or (result.get("tools_used") or [])):
        issues.append("Не выполнен ни один инструмент")

    if not sources:
        issues.append("Ответ не содержит источников")

    for err in result.get("errors") or []:
        issues.append(f"Ошибка исполнения: {err}")

    verdict = "pass" if not issues else "needs_review"
    return verdict, issues