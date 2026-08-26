# agent/graph/router.py

from typing import Literal
from ..core.state import AgentState


def router(state: AgentState) -> Literal[
    "catalog", "stock", "graph", "impact", "rules", "regulation", "answer"
]:
    """Условный роутинг на основе интента"""
    parsed = state.get("parsed")
    if not parsed:
        return "catalog"
    
    operations = getattr(parsed, "operations", [])
    query = getattr(parsed, "original_query", "").lower()
    intent = state.get("context", {}).get("intent", "search")
    
    # Дубли → сразу каталог + детектор дублей
    if "дубл" in query:
        return "catalog"
    
    # Замена/ремонт → граф + каталог
    if intent in ["replacement", "maintenance"]:
        return "graph"
    
    # Анализ влияния → сразу анализ
    if intent == "impact_analysis":
        return "impact"
    
    # Склад/расчёт → каталог + склад
    if intent == "inventory":
        return "catalog"
    
    # Поиск документов → граф + документы
    if intent == "document_search":
        return "graph"
    
    return "catalog"


def graph_router(state: AgentState) -> Literal["impact", "catalog", "answer"]:
    """Роутинг после поиска в графе"""
    parsed = state.get("parsed")
    intent = state.get("context", {}).get("intent", "search")
    
    # Если есть изменения → анализ влияния
    if parsed and getattr(parsed, "proposed_changes", {}):
        return "impact"
    
    # Если замена → каталог
    if intent == "replacement":
        return "catalog"
    
    return "answer"


def catalog_router(state: AgentState) -> Literal["stock", "rules", "impact", "answer"]:
    """Роутинг после поиска в каталоге"""
    candidates = state.get("candidates", [])
    intent = state.get("context", {}).get("intent", "search")
    
    # Если есть кандидаты
    if candidates:
        # Проверка склада
        if intent in ["inventory", "replacement"]:
            return "stock"
        # Правила
        return "rules"
    
    # Нет кандидатов
    return "answer"


def stock_router(state: AgentState) -> Literal["rules", "impact", "answer"]:
    """Роутинг после проверки склада"""
    intent = state.get("context", {}).get("intent", "search")
    
    # Анализ влияния при замене
    if intent == "replacement":
        return "impact"
    
    # Правила
    return "rules"


def impact_router(state: AgentState) -> Literal["stock", "rules", "answer"]:
    """Роутинг после анализа влияния"""
    parsed = state.get("parsed")
    
    # Если есть изменения → проверяем склад
    if parsed and getattr(parsed, "proposed_changes", {}):
        return "stock"
    
    return "answer"


def rules_router(state: AgentState) -> Literal["regulation", "answer"]:
    """Роутинг после применения правил"""
    # Нормативы
    return "regulation"
