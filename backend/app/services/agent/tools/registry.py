# agent/tools/registry.py

from typing import Dict, Callable, Any, Optional


_TOOL_REGISTRY: Dict[str, Callable] = {}
_TOOL_DESCRIPTIONS: Dict[str, str] = {}


def register_tool(name: str, description: str = ""):
    """Декоратор для регистрации тула"""
    def decorator(func: Callable) -> Callable:
        _TOOL_REGISTRY[name] = func
        _TOOL_DESCRIPTIONS[name] = description or func.__doc__ or name
        return func
    return decorator


def get_tool(name: str) -> Optional[Callable]:
    return _TOOL_REGISTRY.get(name)


def list_tools() -> list[str]:
    return list(_TOOL_REGISTRY.keys())


def get_tool_descriptions() -> Dict[str, str]:
    return _TOOL_DESCRIPTIONS.copy()


def clear_registry() -> None:
    _TOOL_REGISTRY.clear()
    _TOOL_DESCRIPTIONS.clear()
