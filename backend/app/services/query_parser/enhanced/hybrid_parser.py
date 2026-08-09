# query_parser/enhanced/hybrid_parser.py

from typing import Dict, Any, Optional, List
from app.schemas import (
    ParsedQuery,
    ItemCard,
    Geometry,
    Pressure,
    Material,
    Environment,
    Normative,
    Extraction,
    Source,
)
from ..parser import QueryParser
from ..operation_parser import OperationParser
from .natasha_parser import NatashaParser
from ..normalizers.morph_normalizer import MorphNormalizer
import re


class HybridParser:
    def __init__(self):
        self.rule_parser = QueryParser()
        self.natasha_parser = NatashaParser()
        self.morph_normalizer = MorphNormalizer()
        self.operation_parser = OperationParser()

    def parse(self, text: str) -> ParsedQuery:
        # 1. Правилoвый парсер
        rule_result = self.rule_parser.parse(text)
        
        # 2. Natasha парсер
        natasha_result = self.natasha_parser.parse(text)
        
        # 3. Объединение результатов
        merged = self._merge_results(rule_result, natasha_result, text)
        
        return merged

    def _merge_results(self, rule: ParsedQuery, natasha: Dict, text: str) -> ParsedQuery:
        # Копируем rule как основу
        card = rule.card
        
        # Если карточки нет, создаём пустую
        if card is None:
            card = ItemCard(
                card_id=None,
                item_type=None,
                subtype=None,
                designation=None,
                name=None,
                geometry=None,
                pressure=None,
                material=None,
                environment=None,
                coating=None,
                normative=None,
                extraction=Extraction(
                    confidence=0.0,
                    method="hybrid",
                    missing_fields=[]
                ),
                sources=[Source(type="user_query", fragment=text)]
            )
        
        # Обновляем геометрию
        if card.geometry is None:
            card.geometry = Geometry()
        
        params = natasha.get("parameters", {})
        
        # DN
        if params.get("dn") and card.geometry.dn is None:
            card.geometry.dn = params["dn"]
        
        # Толщина стенки
        if params.get("wall_thickness") and card.geometry.wall_thickness is None:
            card.geometry.wall_thickness = params["wall_thickness"]
        
        # Давление
        if card.pressure is None:
            card.pressure = Pressure()
        if params.get("pressure") and card.pressure.pn is None:
            card.pressure.pn = params["pressure"]
        
        # Материал
        if card.material is None:
            card.material = Material()
        if params.get("steel_grade") and card.material.steel_grade is None:
            card.material.steel_grade = params["steel_grade"]
        
        # Среда
        if card.environment is None:
            card.environment = Environment()
        if params.get("medium") and card.environment.medium is None:
            card.environment.medium = params["medium"]
            if params["medium"] == "H2S":
                card.environment.h2s_confirmed = True
            elif params["medium"] == "CO2":
                card.environment.co2_confirmed = True
        
        # Тип детали (если не найден)
        if card.item_type is None and natasha.get("item_types"):
            card.item_type = natasha["item_types"][0]
        
        # Обновляем item_types
        item_types = rule.item_types or []
        if natasha.get("item_types"):
            item_types.extend([t for t in natasha["item_types"] if t not in item_types])
        
        # Обновляем операции (если rule вернул только search)
        operations = rule.operations.copy()
        if natasha["operations"]:
            for op in natasha["operations"]:
                if op not in operations:
                    operations.append(op)
            operations = sorted(
                operations,
                key=lambda x: self.operation_parser.OPERATION_PRIORITY.get(x, 0),
                reverse=True
            )
        
        # Основная операция – используем логику из parser.py
        operation = self.rule_parser._select_primary_operation(operations)
        
        # Пересчёт confidence
        confidence = self._recalculate_confidence(card, operations, rule.ambiguities, text)
        
        # Обновляем missing_fields
        if card.extraction:
            card.extraction.missing_fields = self.rule_parser._get_missing_fields(card)
            card.extraction.confidence = confidence
            card.extraction.method = "hybrid"
        
        # Создаём ParsedQuery
        return ParsedQuery(
            original_query=text,
            operation=operation,
            operations=operations,
            item_types=item_types,
            card=card,
            cards=rule.cards or ([card] if card else []),
            filters=rule.filters,
            changes=rule.changes,
            context=rule.context,
            references=rule.references,
            ambiguities=rule.ambiguities,
            required_capabilities=rule.required_capabilities,
            confidence=confidence,
        )

    # def _select_primary_operation(self, operations: List[str]) -> str:
    #     """Выбор основной операции (синхронизирован с parser.py)"""
    #     # Если есть explain – он всегда главный (объяснение)
    #     if "explain" in operations:
    #         return "explain"
        
    #     # Если есть impact – он важнее repair
    #     if "impact" in operations and "repair" in operations:
    #         return "impact"
        
    #     priority = {
    #         "repair": 100,
    #         "replace": 95,
    #         "impact": 90,
    #         "plan": 80,
    #         "check": 75,
    #         "inventory": 70,
    #         "document": 50,
    #         "explain": 45,
    #         "search": 30,
    #         "assemble": 20,
    #         "calculate": 10,
    #     }
    #     return max(operations, key=lambda x: priority.get(x, 0))

    def _recalculate_confidence(self, card: ItemCard, operations: List[str], ambiguities: List[str], text: str) -> float:
        """Пересчёт confidence (синхронизирован с parser.py)"""
        score = 1.0
        
        # 1. Операции
        if not operations or operations == ["unknown"]:
            score -= 0.3
        
        # 2. Карточка
        if card is None:
            score -= 0.25
            return max(0.0, min(1.0, score))
        
        # 3. Штраф за отсутствующие поля
        missing = self._get_missing_fields(card) if card.extraction else []
        if missing:
            penalty = 0.0
            
            # Критические поля
            critical_fields = ["item_type", "dn"]
            for field in critical_fields:
                if field in missing:
                    penalty += 0.15
            
            # Важные поля
            important_fields = ["wall_thickness", "pn", "steel_grade", "medium"]
            for field in important_fields:
                if field in missing:
                    penalty += 0.05
            
            # Остальные поля
            other_fields = ["geometry", "pressure", "material", "environment"]
            for field in other_fields:
                if field in missing:
                    penalty += 0.03
            
            score -= min(penalty, 0.5)
        
        # 4. Амбигвити
        if ambiguities:
            score -= min(0.15 * len(ambiguities), 0.3)
        
        # 5. Длина запроса
        word_count = len(text.split())
        if word_count < 3:
            score -= 0.15
        elif word_count < 5:
            score -= 0.05
        
        # 6. Бонус за references
        if re.search(r'COMP-|UNIT-|KSM-|MTR-', text):
            score += 0.05
        
        # 7. Неизвестные операции
        known_ops = set(self.operation_parser.OPERATION_PRIORITY.keys())
        unknown = [op for op in operations if op not in known_ops]
        if unknown:
            score -= 0.1 * len(unknown)
        
        return max(0.0, min(1.0, score))

    def _get_missing_fields(self, card: ItemCard) -> List[str]:
        """Определяет отсутствующие поля (синхронизирован с parser.py)"""
        missing = []
        
        if card is None:
            return ["full_card"]
        
        if card.item_type is None:
            missing.append("item_type")
        
        if card.geometry:
            # Для переходов достаточно d1 и d2
            if card.item_type == "переход":
                if card.geometry.d1 is None and card.geometry.d2 is None:
                    missing.append("geometry")
            else:
                if card.geometry.dn is None:
                    missing.append("dn")
                if card.geometry.wall_thickness is None and card.geometry.d1 is None:
                    missing.append("geometry")
        else:
            missing.append("geometry")
        
        if card.pressure and card.pressure.pn is None:
            missing.append("pressure")
        elif card.pressure is None:
            missing.append("pressure")
        
        if card.material and card.material.steel_grade is None:
            missing.append("material")
        elif card.material is None:
            missing.append("material")
        
        if card.environment and card.environment.medium is None:
            missing.append("environment")
        elif card.environment is None:
            missing.append("environment")
        
        return missing
