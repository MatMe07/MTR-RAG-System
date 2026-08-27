# query_parser/confidence_calculator.py
import sys
import os
from pathlib import Path

# sys.path.insert(0, str(Path(__file__).parent.parent))
# print(str(Path(__file__).parent.parent))
from typing import List, Optional, Dict, Any
from app.schemas import ItemCard
import re

class ConfidenceCalculator:
    """Расчёт уверенности парсинга"""
    
    # Конфигурация штрафов
    PENALTIES = {
        'critical_field': 0.15,   # item_type, dn
        'important_field': 0.05,  # wall_thickness, pn, steel_grade, medium
        'other_field': 0.03,      # geometry, pressure, material, environment
        'no_operations': 0.3,
        'no_card': 0.25,
        'per_ambiguity': 0.15,
        'short_query_3words': 0.15,
        'short_query_5words': 0.05,
        'unknown_operation': 0.1,
    }
    
    # Максимальные штрафы
    MAX_PENALTIES = {
        'missing_fields': 0.5,
        'ambiguities': 0.3,
        'unknown_operations': 0.3,
    }
    
    @classmethod
    def calculate(
        cls,
        text: str,
        operations: List[str],
        card: Optional[ItemCard],
        ambiguities: List[str],
        references: List[str] = None
    ) -> float:
        """Основной метод расчёта confidence"""
        score = 1.0
        
        # 1. Операции
        score -= cls._penalty_operations(operations)
        
        # 2. Карточка
        score -= cls._penalty_card(card)
        
        # 3. Амбигвити
        score -= cls._penalty_ambiguities(ambiguities)
        
        # 4. Длина запроса
        score -= cls._penalty_query_length(text)
        
        # 5. Бонусы
        score += cls._bonus_references(text, references or [])
        
        # 6. Неизвестные операции
        score -= cls._penalty_unknown_operations(operations)
        
        return max(0.0, min(1.0, score))
    
    @classmethod
    def _penalty_operations(cls, operations: List[str]) -> float:
        if not operations or operations == ["unknown"]:
            return cls.PENALTIES['no_operations']
        return 0.0
    
    @classmethod
    def _penalty_card(cls, card: Optional[ItemCard]) -> float:
        if card is None:
            return cls.PENALTIES['no_card']
        
        if not hasattr(card, 'extraction') or not card.extraction:
            return 0.0
        
        missing = card.extraction.missing_fields or []
        if not missing:
            return 0.0
        
        penalty = 0.0
        critical_fields = ["item_type", "dn"]
        important_fields = ["wall_thickness", "pn", "steel_grade", "medium"]
        other_fields = ["geometry", "pressure", "material", "environment"]
        
        for field in missing:
            if field in critical_fields:
                penalty += cls.PENALTIES['critical_field']
            elif field in important_fields:
                penalty += cls.PENALTIES['important_field']
            elif field in other_fields:
                penalty += cls.PENALTIES['other_field']
        
        return min(penalty, cls.MAX_PENALTIES['missing_fields'])
    
    @classmethod
    def _penalty_ambiguities(cls, ambiguities: List[str]) -> float:
        if not ambiguities:
            return 0.0
        return min(cls.PENALTIES['per_ambiguity'] * len(ambiguities), cls.MAX_PENALTIES['ambiguities'])
    
    @classmethod
    def _penalty_query_length(cls, text: str) -> float:
        word_count = len(text.split())
        if word_count < 3:
            return cls.PENALTIES['short_query_3words']
        elif word_count < 5:
            return cls.PENALTIES['short_query_5words']
        return 0.0
    
    @classmethod
    def _bonus_references(cls, text: str, references: List[str]) -> float:
        if references:
            return 0.05
        if re.search(r'COMP-|UNIT-|KSM-|MTR-', text):
            return 0.05
        return 0.0
    
    @classmethod
    def _penalty_unknown_operations(cls, operations: List[str]) -> float:
        # Предполагаем, что есть список известных операций
        # В реальном коде нужно передавать или использовать глобальный список
        known_ops = {"search", "replace", "repair", "plan", "check", 
                     "inventory", "explain", "impact", "assemble", "calculate"}
        unknown = [op for op in operations if op not in known_ops]
        if unknown:
            return min(cls.PENALTIES['unknown_operation'] * len(unknown), cls.MAX_PENALTIES['unknown_operations'])
        return 0.0
    
    @classmethod
    def build_details(
        cls,
        operations: List[str],
        card: Optional[ItemCard],
        ambiguities: List[str]
    ) -> Dict[str, float]:
        """Построение детализированного отчёта по confidence"""
        details = {}
        
        # Операции
        if operations:
            details["operations"] = min(1.0, len(operations) * 0.2 + 0.2)
        else:
            details["operations"] = 0.0
        
        # Карточка
        if card:
            missing = card.extraction.missing_fields if card.extraction else []
            if missing:
                details["card"] = max(0.0, 1.0 - len(missing) * 0.1)
            else:
                details["card"] = 1.0
        else:
            details["card"] = 0.0
        
        # Амбигвити
        if ambiguities:
            details["ambiguities"] = max(0.0, 1.0 - len(ambiguities) * 0.2)
        else:
            details["ambiguities"] = 1.0
        
        return details
