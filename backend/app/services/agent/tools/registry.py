# agent/tools/registry.py

from typing import Any, Callable, Dict, List, Optional

from .validation import validate_input


_TOOL_REGISTRY: Dict[str, Callable] = {}
_TOOL_DESCRIPTIONS: Dict[str, str] = {}

# Инструменты ЭТАПА 3 (шаблон Instrument: ЭТАП 3, секция 3B).
_INSTRUMENTS: Dict[str, Dict[str, Any]] = {}
_INTENT_TOOLS: Dict[str, List[str]] = {}


def register_tool(name: str, description: str = ""):
    """Декоратор для регистрации тула"""
    def decorator(func: Callable) -> Callable:
        _TOOL_REGISTRY[name] = func
        _TOOL_DESCRIPTIONS[name] = description or func.__doc__ or name
        return func
    return decorator


def register_instrument(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    output_schema: Dict[str, Any],
    execute: Callable,
    required_intents: Optional[List[str]] = None,
) -> None:
    """Регистрация инструмента (Instrument) с JSON-schema валидацией."""
    _INSTRUMENTS[name] = {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "execute": execute,
        "validate_input": lambda data: validate_input(input_schema, data),
        "required_intents": required_intents or [],
    }


def set_intent_tools(mapping: Dict[str, List[str]]) -> None:
    """Карта интент → список инструментов (ЭТАП 3, секция 3E)."""
    _INTENT_TOOLS.update(mapping)


def get_tool(name: str) -> Optional[Callable]:
    return _TOOL_REGISTRY.get(name)


def get_instrument(name: str) -> Optional[Dict[str, Any]]:
    return _INSTRUMENTS.get(name)


def list_tools() -> list[str]:
    return list(_TOOL_REGISTRY.keys())


def list_instruments() -> List[str]:
    return sorted(_INSTRUMENTS.keys())


def get_tool_descriptions() -> Dict[str, str]:
    return _TOOL_DESCRIPTIONS.copy()


def get_instruments_for_llm() -> List[Dict[str, Any]]:
    """Реестр инструментов для LLM-режима (Фаза E): имена, описания, схемы."""
    return [
        {
            "name": inst["name"],
            "description": inst["description"],
            "input_schema": inst["input_schema"],
            "output_schema": inst["output_schema"],
            "required_intents": inst["required_intents"],
        }
        for inst in _INSTRUMENTS.values()
    ]


def get_intent_tools(intent: str) -> List[str]:
    return list(_INTENT_TOOLS.get(intent, []))
