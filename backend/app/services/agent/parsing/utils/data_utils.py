# query_parser/utils/data_utils.py

from typing import Dict, Any, Optional
import copy


def safe_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Безопасное слияние словарей без мутации исходных.
    Только не-None значения из override заменяют base.
    """
    result = copy.deepcopy(base)
    
    for key, value in override.items():
        if value is not None:
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Рекурсивное слияние для вложенных словарей
                result[key] = safe_merge_dicts(result[key], value)
            else:
                result[key] = value
    
    return result


def clean_technical_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Удаляет мусорные значения из фильтров"""
    garbage_values = ["ТУ ДЛЯ", "ГОСТЫ", "ТУ для", "ГОСТы", "ТУ", "ГОСТ"]
    result = copy.deepcopy(filters)
    
    for key, value in list(result.items()):
        if value in garbage_values:
            del result[key]
    
    return result


def safe_update_card(card: Any, updates: Dict[str, Any]) -> Any:
    """
    Безопасное обновление карточки без мутации.
    Возвращает НОВЫЙ объект.
    """
    # Используем Pydantic's model_copy если доступно
    if hasattr(card, "model_copy"):
        new_card = card.model_copy(deep=True)
    else:
        # Fallback для обычных объектов
        import copy
        new_card = copy.deepcopy(card)
    
    for field, value in updates.items():
        if hasattr(new_card, field):
            setattr(new_card, field, value)
    
    return new_card
