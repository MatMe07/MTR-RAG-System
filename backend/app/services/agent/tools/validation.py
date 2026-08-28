# agent/tools/validation.py
"""Валидация входных данных инструментов по JSON Schema (ЭТАП 3, секция 3C).

Реализовано подмножество JSON Schema, достаточное для схем инструментов:
type, required, properties, items, enum, minimum, maximum, maxItems, minItems.
"""

from typing import Any, Dict, List, Optional

from .errors import ToolError, ToolErrorCode

_TYPE_NAMES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}


def _type_matches(value: Any, type_name: str) -> bool:
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    target = _TYPE_NAMES.get(type_name)
    if target is None:
        return True
    return isinstance(value, target)


def _check(
    value: Any,
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str,
    errors: List[Dict[str, str]],
) -> None:
    """Рекурсивная проверка значения против схемы."""
    t = schema.get("type")
    if t and not _type_matches(value, t):
        expected = _TYPE_NAMES.get(t, t)
        if isinstance(expected, tuple):
            expected = " / ".join(c.__name__ for c in expected)
        errors.append({
            "path": path or "input",
            "message": f"ожидался тип {getattr(expected, '__name__', expected)}, получено {type(value).__name__}",
        })
        return

    if isinstance(value, list):
        if schema.get("minItems") is not None and len(value) < schema["minItems"]:
            errors.append({"path": path, "message": f"минимум {schema['minItems']} элементов"})
        if schema.get("maxItems") is not None and len(value) > schema["maxItems"]:
            errors.append({"path": path, "message": f"максимум {schema['maxItems']} элементов"})
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(value):
                _check(item, items_schema, root, f"{path}[{i}]", errors)
        return

    if isinstance(value, dict):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for k in required:
            if k not in value:
                errors.append({"path": path or "input", "message": f"обязательное поле '{k}' отсутствует"})
        for k, v in value.items():
            child = props.get(k)
            if child:
                _check(v, child, root, f"{path}.{k}" if path else k, errors)
        return

    if isinstance(value, bool):
        return

    if isinstance(value, (int, float)):
        if schema.get("minimum") is not None and value < schema["minimum"]:
            errors.append({
                "path": path,
                "message": f"значение {value} меньше минимума {schema['minimum']}",
            })
        if schema.get("maximum") is not None and value > schema["maximum"]:
            errors.append({
                "path": path,
                "message": f"значение {value} больше максимума {schema['maximum']}",
            })
        return

    if isinstance(value, str):
        if schema.get("enum") and value not in schema["enum"]:
            errors.append({
                "path": path,
                "message": f"значение '{value}' не входит в {schema['enum']}",
            })
        return


def validate_input(input_schema: Dict[str, Any], data: Dict[str, Any]) -> None:
    """Проверяет входные данные по JSON Schema.

    При ошибке выбрасывает ToolError с кодом INVALID_PARAMS.
    """
    errors: List[Dict[str, str]] = []
    _check(data, input_schema, input_schema, "input", errors)
    if errors:
        raise ToolError(
            ToolErrorCode.INVALID_PARAMS,
            "Неверные входные параметры",
            {"errors": errors},
        )