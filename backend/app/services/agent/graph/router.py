# agent/graph/router.py

from typing import Literal
from ..core.state import AgentState


# Объектный контекст: запрос говорит про участок/схему/установленные детали,
# поэтому нужен граф объекта, а не только складской каталог.
_OBJECT_CONTEXT = (
    "участк", "газопровод", "трубопровод", "магистрал", "схем",
    "установлен", "стоит", "стоят", "перед ", "после ", "соседн",
    "рядом", "все детали", "всех деталей", "норматив",
)


def _has_object_context(query: str) -> bool:
    return any(token in query for token in _OBJECT_CONTEXT)


def router(state: AgentState) -> Literal[
    "catalog", "stock", "graph", "impact", "rules", "regulation",
    "duplicates", "inventory", "maintenance", "answer",
]:
    """Условный роутинг на основе интента"""
    parsed = state.get("parsed")
    if not parsed:
        return "catalog"
    
    operations = getattr(parsed, "operations", [])
    query = getattr(parsed, "original_query", "").lower()
    intent = state.get("context", {}).get("intent", "search")
    unit_ids = getattr(parsed, "unit_ids", [])
    component_ids = getattr(parsed, "component_ids", [])
    
    # Дубли → каталог (после поиска сработает детектор дублей)
    if "дубл" in query:
        return "catalog"
    
    # Замена/ремонт/ТОиР → граф + каталог + анализ + план + правила
    if intent in ["replacement", "maintenance", "repair", "plan"]:
        return "graph"
    
    # Анализ влияния → сначала граф и каталог, затем анализ
    if intent == "impact_analysis":
        return "graph"
    
    # Состав/документы → граф
    if intent in ["document_search", "object_configuration"]:
        return "graph"
    
    # Склад/расчёт → каталог (+ граф, если есть участки или объектный контекст)
    if intent in ["inventory", "calculate"]:
        return "graph" if (unit_ids or component_ids or _has_object_context(query)) else "catalog"
    
    # Рекомендации по оборудованию → каталог (+ граф, если есть объектный контекст)
    if intent == "equipment_guidance":
        return "graph" if (unit_ids or component_ids or _has_object_context(query)) else "catalog"
    
    # Есть явные участки/компоненты → граф
    if unit_ids or component_ids:
        return "graph"
    
    return "catalog"


def graph_router(state: AgentState) -> Literal[
    "impact", "catalog", "maintenance", "answer",
]:
    """Роутинг после поиска в графе"""
    parsed = state.get("parsed")
    intent = state.get("context", {}).get("intent", "search")
    
    # ТОиР/ремонт → планировщик работ по найденным в графе компонентам
    if intent in ["maintenance", "repair", "plan"]:
        return "maintenance"
    
    # Интенты, которым нужен и граф, и каталог
    if intent in [
        "replacement", "impact_analysis", "document_search",
        "object_configuration", "inventory", "equipment_guidance",
    ]:
        return "catalog"
    
    # Если есть изменения → анализ влияния
    if parsed and getattr(parsed, "proposed_changes", {}):
        return "impact"
    
    return "answer"


def catalog_router(state: AgentState) -> Literal[
    "stock", "rules", "impact", "duplicates", "answer",
]:
    """Роутинг после поиска в каталоге"""
    candidates = state.get("candidates", [])
    intent = state.get("context", {}).get("intent", "search")
    query = getattr(state.get("parsed"), "original_query", "").lower()
    
    # Дубли → детектор дублей
    if "дубл" in query:
        return "duplicates"
    
    # Если есть кандидаты
    if candidates:
        # Анализ влияния идёт сразу после каталога
        if intent == "impact_analysis":
            return "impact"
        # Проверка склада для запасов/замены/ТОиР/состава
        if intent in [
            "inventory", "calculate", "replacement",
            "maintenance", "repair", "plan",
            "object_configuration", "equipment_guidance",
        ]:
            return "stock"
        # Правила
        return "rules"
    
    # Нет кандидатов
    return "answer"


def stock_router(state: AgentState) -> Literal[
    "rules", "impact", "inventory", "answer",
]:
    """Роутинг после проверки склада"""
    intent = state.get("context", {}).get("intent", "search")
    
    # Расчёт запаса
    if intent in ["inventory", "calculate"]:
        return "inventory"
    
    # Анализ влияния при замене
    if intent == "replacement":
        return "impact"
    
    # Правила
    return "rules"


def impact_router(state: AgentState) -> Literal[
    "stock", "rules", "maintenance", "answer",
]:
    """Роутинг после анализа влияния"""
    parsed = state.get("parsed")
    intent = state.get("context", {}).get("intent", "search")
    
    # Замена: после влияния — план работ и правила
    if intent == "replacement":
        return "maintenance"
    
    # ТОиР/анализ влияния: сразу правила и нормативы
    if intent in ["maintenance", "impact_analysis"]:
        return "rules"
    
    # Если есть изменения → проверяем склад
    if parsed and getattr(parsed, "proposed_changes", {}):
        return "stock"
    
    return "answer"


def maintenance_router(state: AgentState) -> Literal["catalog", "rules", "answer"]:
    """Роутинг после планировщика ТОиР"""
    intent = state.get("context", {}).get("intent", "search")
    
    # Замена: планировщик завершает, дальше правила и нормативы
    if intent == "replacement":
        return "rules"
    
    # Обычный ТОиР: план по найденному составу, затем каталог и правила
    return "catalog"


def rules_router(state: AgentState) -> Literal["regulation", "answer"]:
    """Роутинг после применения правил"""
    # Нормативы
    return "regulation"