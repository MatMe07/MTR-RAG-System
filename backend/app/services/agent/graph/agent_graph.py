# agent/graph/agent_graph.py

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

try:  # optional: langgraph-checkpoint-redis (добавлен в pyproject)
    from langgraph.checkpoint.redis import RedisSaver

    _HAS_REDIS_SAVER = True
except Exception:  # pragma: no cover - зависимости нет (тесты/лёгкая установка)
    RedisSaver = None
    _HAS_REDIS_SAVER = False

from ..core.config import DEFAULT_CONFIG, AgentConfig
from ..core.state import AgentState
from .nodes import (
    answer_node,
    catalog_node,
    duplicates_node,
    graph_node,
    impact_node,
    inventory_node,
    maintenance_node,
    parse_node,
    regulation_node,
    rules_node,
    stock_node,
    sufficiency_node,
)
from .router import (
    catalog_router,
    graph_router,
    impact_router,
    maintenance_router,
    router,
    rules_router,
    stock_router,
)


def build_agent_graph(config: AgentConfig = None) -> StateGraph:
    """Сборка графа агента"""
    config = config or DEFAULT_CONFIG

    builder = StateGraph(AgentState)

    # ============================================================
    # ДОБАВЛЯЕМ УЗЛЫ
    # ============================================================
    builder.add_node("parse", parse_node)
    builder.add_node("catalog", catalog_node)
    builder.add_node("stock", stock_node)
    builder.add_node("rules", rules_node)
    builder.add_node("graph", graph_node)
    builder.add_node("impact", impact_node)
    builder.add_node("regulation", regulation_node)
    builder.add_node("inventory", inventory_node)
    builder.add_node("sufficiency", sufficiency_node)
    builder.add_node("maintenance", maintenance_node)
    builder.add_node("duplicates", duplicates_node)
    builder.add_node("answer", answer_node)

    # ============================================================
    # НАЧАЛЬНЫЙ УЗЕЛ
    # ============================================================
    builder.set_entry_point("parse")

    # ============================================================
    # УСЛОВНЫЙ РОУТИНГ ПОСЛЕ ПАРСИНГА
    # ============================================================
    builder.add_conditional_edges(
        "parse",
        router,
        {
            "catalog": "catalog",
            "stock": "stock",
            "graph": "graph",
            "impact": "impact",
            "rules": "rules",
            "regulation": "regulation",
            "duplicates": "duplicates",
            "inventory": "inventory",
            "maintenance": "maintenance",
            "answer": "answer",
        }
    )

    # ============================================================
    # РОУТИНГ ПОСЛЕ ГРАФА
    # ============================================================
    builder.add_conditional_edges(
        "graph",
        graph_router,
        {
            "impact": "impact",
            "catalog": "catalog",
            "maintenance": "maintenance",
            "answer": "answer",
        }
    )

    # ============================================================
    # РОУТИНГ ПОСЛЕ ПЛАНИРОВЩИКА ТОИР
    # ============================================================
    builder.add_conditional_edges(
        "maintenance",
        maintenance_router,
        {
            "catalog": "catalog",
            "rules": "rules",
            "answer": "answer",
        }
    )

    # ============================================================
    # РОУТИНГ ПОСЛЕ КАТАЛОГА
    # ============================================================
    builder.add_conditional_edges(
        "catalog",
        catalog_router,
        {
            "stock": "stock",
            "rules": "rules",
            "impact": "impact",
            "duplicates": "duplicates",
            "regulation": "regulation",
            "answer": "answer",
        }
    )

    # ============================================================
    # РОУТИНГ ПОСЛЕ СКЛАДА
    # ============================================================
    builder.add_conditional_edges(
        "stock",
        stock_router,
        {
            "sufficiency": "sufficiency",
            "rules": "rules",
            "impact": "impact",
            "inventory": "inventory",
            "answer": "answer",
        }
    )

    # ============================================================
    # РОУТИНГ ПОСЛЕ АНАЛИЗА ВЛИЯНИЯ
    # ============================================================
    builder.add_conditional_edges(
        "impact",
        impact_router,
        {
            "stock": "stock",
            "rules": "rules",
            "maintenance": "maintenance",
            "answer": "answer",
        }
    )

    # ============================================================
    # РОУТИНГ ПОСЛЕ ПРАВИЛ
    # ============================================================
    builder.add_conditional_edges(
        "rules",
        rules_router,
        {
            "regulation": "regulation",
            "answer": "answer",
        }
    )

    # ============================================================
    # ПРЯМЫЕ РЁБРА
    # ============================================================
    # Детектор дублей → склад
    builder.add_edge("duplicates", "stock")
    # Проверка достаточности → правила
    builder.add_edge("sufficiency", "rules")
    # Расчёт запаса → правила
    builder.add_edge("inventory", "rules")
    # После нормативов → ответ
    builder.add_edge("regulation", "answer")

    # Конец
    builder.add_edge("answer", END)

    return builder


def get_agent_graph(config: AgentConfig = None) -> StateGraph:
    """Получение скомпилированного графа с чекпоинтами.

    checkpoint_type: memory | sqlite | redis. Граф не кешируется глобально —
    каждый экземпляр AgentExecutor компилирует свой граф, чтобы конфиг
    одного экспзекутора не «протекал» в другой.
    """
    config = config or DEFAULT_CONFIG
    builder = build_agent_graph(config)

    # Выбор чекпоинтера
    checkpointer = MemorySaver()
    if config.checkpoint_type == "sqlite":
        import sqlite3
        conn = sqlite3.connect(config.checkpoint_sqlite_path)
        checkpointer = SqliteSaver(conn)
    elif config.checkpoint_type == "redis":
        if not _HAS_REDIS_SAVER:
            raise RuntimeError(
                "checkpoint_type='redis' требует пакет langgraph-checkpoint-redis "
                "(pip install langgraph-checkpoint-redis)."
            )
        checkpointer = RedisSaver(redis_url=config.checkpoint_redis_url)

    return builder.compile(checkpointer=checkpointer)


def get_graph(config: AgentConfig = None) -> StateGraph:
    """Свежескомпилированный граф (без глобального кеша — см. get_agent_graph)."""
    return get_agent_graph(config)
