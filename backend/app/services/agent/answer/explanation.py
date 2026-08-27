# agent/answer/explanation.py

"""ExplanationGenerator (ЭТАП 5, 5A.3): шаблонные объяснения для ТЗ-ответа.

Готовит поле `explanation` каждого результата ТЗ 11.2. Шаблоны строятся на
статусе кандидата и списках matched/mismatched/missing параметров. При наличии
генератора (LLM) можно подставить внешнее объяснение, иначе — шаблон.
"""

from typing import Callable, List, Optional

from .status import (
    STATUS_MATCH,
    STATUS_ANALOG,
    STATUS_MISMATCH,
    STATUS_NOT_FOUND,
    STATUS_UNCLEAR,
    STATUS_EXPERT,
)


def _join(items: List[str], prefix: str) -> str:
    return prefix + ", ".join(items) + "." if items else ""


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