# agent/core/constants.py
"""
Глобальные константы агентной системы.
Все пороги, таймауты и лимиты вынесены сюда.
"""

from typing import Dict, List

# ============================================================
# ПОРОГИ УВЕРЕННОСТИ
# ============================================================

class ConfidenceThresholds:
    """Пороги уверенности для разных компонентов"""
    
    # Для маршрутизации
    ROUTER_MIN_CONFIDENCE: float = 0.55
    ROUTER_HIGH_CONFIDENCE: float = 0.85
    
    # Для парсинга
    PARSER_GOOD_CONFIDENCE: float = 0.8
    PARSER_MIN_CONFIDENCE: float = 0.5
    
    # Для ревью
    REVIEW_MIN_CONFIDENCE: float = 0.7
    
    # Для тулов
    TOOL_MIN_SCORE: float = 0.3
    TOOL_GOOD_SCORE: float = 0.7


# ============================================================
# ТАЙМАУТЫ
# ============================================================

class Timeouts:
    """Таймауты для разных операций"""
    
    LLM_TIMEOUT: float = 30.0           # секунд
    TOOL_TIMEOUT: float = 10.0          # секунд
    DB_TIMEOUT: float = 5.0             # секунд
    CACHE_TTL: int = 3600               # секунд (1 час)
    CACHE_TTL_LLM: int = 86400          # секунд (24 часа)


# ============================================================
# ЛИМИТЫ
# ============================================================

class Limits:
    """Лимиты на количество и размер"""
    
    MAX_CANDIDATES: int = 40            # кандидатов из каталога
    MAX_TOOLS: int = 20                 # тулов в плане
    MAX_RETRIES: int = 3                # попыток
    MAX_ANSWER_LENGTH: int = 5000       # символов
    MAX_COMPONENTS: int = 100           # компонентов в ответе


# ============================================================
# ТОЛЕРАНТНОСТИ
# ============================================================

class Tolerances:
    """Допуски для численных сравнений"""
    
    DN: float = 0.1                     # 10%
    WALL_THICKNESS: float = 0.15        # 15%
    ANGLE: float = 0.0                  # точное совпадение
    PN: float = 0.1                     # 10%
    PRESSURE_MPA: float = 0.01          # 0.01 МПа


# ============================================================
# ПРИОРИТЕТЫ ИНТЕНТОВ
# ============================================================

INTENT_PRIORITY: List[str] = [
    "impact_analysis",
    "replacement",
    "object_configuration",
    "document_search",
    "inventory",
    "maintenance",
    "equipment_guidance",
    "search",
]

# ============================================================
# МАППИНГ ОПЕРАЦИЙ → ИНТЕНТЫ
# ============================================================

OPERATION_TO_INTENT: Dict[str, str] = {
    "search": "search",
    "check": "search",
    "catalog_search": "catalog_search",
    "replace": "replacement",
    "replacement": "replacement",
    "inventory": "inventory",
    "calculate": "inventory",
    "plan": "maintenance",
    "repair": "maintenance",
    "maintain": "maintenance",
    "maintenance": "maintenance",
    "assemble": "object_configuration",
    "object_configuration": "object_configuration",
    "document": "document_search",
    "document_search": "document_search",
    "impact": "impact_analysis",
    "impact_analysis": "impact_analysis",
    "explain": "equipment_guidance",
    "explanation": "equipment_guidance",
}

# ============================================================
# МАППИНГ ИНТЕНТОВ → ПЛАНЫ ТУЛОВ
# ============================================================

INTENT_PLANS: Dict[str, List[str]] = {
    "search": ["catalog_search", "stock_query", "rules_engine", "regulation_lookup"],
    "replacement": ["graph_search", "catalog_search", "stock_query", "rules_engine", "impact_analyzer", "regulation_lookup"],
    "inventory": ["catalog_search", "stock_query", "inventory_calculator", "priority_ranker", "regulation_lookup"],
    "maintenance": ["graph_search", "maintenance_planner", "document_search", "regulation_lookup"],
    "object_configuration": ["object_builder", "catalog_search", "stock_query", "rules_engine"],
    "document_search": ["graph_search", "document_search", "regulation_lookup"],
    "impact_analysis": ["graph_search", "impact_analyzer", "rules_engine", "regulation_lookup"],
    "equipment_guidance": ["catalog_search", "rules_engine", "explanation_generator", "regulation_lookup"],
    "duplicates": ["catalog_search", "duplicate_detector", "regulation_lookup"],
}

# ============================================================
# МАРШРУТЫ
# ============================================================

ALLOWED_ROUTES: List[str] = ["ordinary", "agent", "clarification"]

# ============================================================
# СТАТУСЫ
# ============================================================

MATCH_STATUSES: List[str] = [
    "соответствует",
    "потенциальный аналог",
    "требует проверки",
    "низкая релевантность",
    "нет данных",
    "не соответствует",
]

REVIEW_VERDICTS: List[str] = ["pass", "needs_review"]

TOOL_STATUSES: List[str] = ["success", "warning", "error", "skipped"]

# ============================================================
# ИСТОЧНИКИ
# ============================================================

SOURCE_TYPES: List[str] = [
    "catalog",
    "stock",
    "object_graph",
    "regulation",
    "passport",
    "tu",
    "lnd",
    "standard",
    "expert_decisions",
    "project_documentation",
    "maintenance_policy",
    "maintenance_history",
]
