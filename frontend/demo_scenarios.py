"""Prepared user scenarios for a reproducible project demonstration."""

from __future__ import annotations

from typing import Any


DEMO_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "replacement",
        "title": "Подбор замены",
        "query": (
            "Какой аналог отвода 90 426 на 10 подойдет для H2S, "
            "покажи сначала то, что есть на складе"
        ),
        "expected": "Агент объединит каталог, правила, склад и нормативные источники.",
    },
    {
        "id": "inventory",
        "title": "Складские остатки",
        "query": (
            "На следующей неделе ремонт участка с H2S, проверь хватает ли труб, "
            "отводов, переходов, задвижек, заглушек и тройников по две штуки"
        ),
        "expected": "Агент сопоставит состав участка с остатками и покажет дефицит.",
    },
    {
        "id": "maintenance",
        "title": "План ТОиР",
        "query": (
            "Составь план обслуживания участка UNIT-SYN-H2S-001 на следующий месяц "
            "и перечисли нужные запчасти"
        ),
        "expected": "Агент соберёт предварительный план, запчасти и недостающие данные.",
    },
    {
        "id": "documents",
        "title": "Проверка документов",
        "query": (
            "Найди документы, которые подтверждают материал, покрытие и пригодность "
            "отвода 90 426 на 10 для H2S"
        ),
        "expected": "Агент должен вернуть паспорт или ТУ и указать, чего не хватает.",
    },
]


def scenario_by_id(scenario_id: str) -> dict[str, Any]:
    return next(item for item in DEMO_SCENARIOS if item["id"] == scenario_id)
