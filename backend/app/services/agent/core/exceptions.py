# agent/core/exceptions.py

from typing import Optional, List


class AgentError(Exception):
    """Базовое исключение агентной системы"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ============================================================
# РЕПОЗИТОРИЙ
# ============================================================

class RepositoryError(AgentError):
    """Ошибка репозитория"""
    pass


class RepositoryConnectionError(RepositoryError):
    """Ошибка подключения к репозиторию"""
    def __init__(self, source: str):
        super().__init__(f"Не удалось подключиться к {source}")


class DataNotFoundError(RepositoryError):
    """Данные не найдены"""
    def __init__(self, entity: str, id: str):
        super().__init__(f"{entity} не найден: {id}")


# ============================================================
# ТУЛЫ
# ============================================================

class ToolError(AgentError):
    """Ошибка выполнения тула"""
    def __init__(self, tool_name: str, message: str, details: Optional[dict] = None):
        self.tool_name = tool_name
        super().__init__(f"{tool_name}: {message}", details)


class ToolNotFoundError(ToolError):
    """Тул не найден"""
    def __init__(self, tool_name: str):
        super().__init__(tool_name, f"Тул не найден: {tool_name}")


class ToolTimeoutError(ToolError):
    """Таймаут выполнения тула"""
    def __init__(self, tool_name: str, timeout: float):
        super().__init__(tool_name, f"Таймаут {timeout}с")


# ============================================================
# LLM
# ============================================================

class LLMError(AgentError):
    """Ошибка LLM"""
    pass


class LLMTimeoutError(LLMError):
    """Таймаут LLM"""
    def __init__(self, timeout: float):
        super().__init__(f"Таймаут LLM: {timeout}с")


class LLMResponseError(LLMError):
    """Ошибка ответа LLM"""
    def __init__(self, message: str, response: str = ""):
        self.response = response
        super().__init__(f"Ошибка ответа LLM: {message}")


# ============================================================
# ГРАФ
# ============================================================

class GraphError(AgentError):
    """Ошибка графа"""
    pass


class NodeError(GraphError):
    """Ошибка узла графа"""
    def __init__(self, node_name: str, message: str):
        self.node_name = node_name
        super().__init__(f"Узел {node_name}: {message}")


# ============================================================
# ИСПОЛНЕНИЕ
# ============================================================

class ExecutionError(AgentError):
    """Ошибка исполнения"""
    pass


class PlanExecutionError(ExecutionError):
    """Ошибка выполнения плана"""
    def __init__(self, errors: List[str]):
        super().__init__(f"Ошибка выполнения плана: {', '.join(errors)}")


# ============================================================
# ПАРСИНГ
# ============================================================

class ParsingError(AgentError):
    """Ошибка парсинга"""
    pass


class ValidationError(AgentError):
    """Ошибка валидации"""
    pass
