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
from .parser import QueryParser
from .parsers.operation_parser import OperationParser
from .enhanced.natasha_parser import NatashaParser
from .normalizers.morph_normalizer import MorphNormalizer
import re


class HybridParser:
    def __init__(self):
        self.rule_parser = QueryParser()
        self.natasha_parser = NatashaParser()
        self.morph_normalizer = MorphNormalizer()
        self.operation_parser = OperationParser()

    def parse(self, text: str) -> ParsedQuery:
        # 1. Rule-based парсер
        rule_result = self.rule_parser.parse(text)
        
        # 2. Natasha парсер
        natasha_result = self.natasha_parser.parse(text)
        
        # 3. Если rule уже хороший – используем его
        if rule_result.confidence >= 0.8:
            return self._enrich_result(rule_result, natasha_result, text)
        
        # 4. Иначе объединяем
        return self._merge_results(rule_result, natasha_result, text)

    def _enrich_result(self, rule: ParsedQuery, natasha: Dict, text: str) -> ParsedQuery:
        """Дополняет rule-результат данными из Natasha"""
        card = rule.card
        
        # Добавляем subtype
        if card and card.subtype is None and natasha.get("subtype"):
            card.subtype = natasha["subtype"]
        
        # Добавляем отсутствующие операции
        if natasha.get("operations"):
            for op in natasha["operations"]:
                if op not in rule.operations:
                    rule.operations.append(op)
            rule.operations = sorted(
                rule.operations,
                key=lambda x: self.operation_parser.OPERATION_PRIORITY.get(x, 0),
                reverse=True
            )
        
        # Добавляем component_ids
        if natasha.get("component_ids"):
            for cid in natasha["component_ids"]:
                if cid not in rule.component_ids:
                    rule.component_ids.append(cid)
        
        # Добавляем unit_ids
        if natasha.get("unit_ids"):
            for uid in natasha["unit_ids"]:
                if uid not in rule.unit_ids:
                    rule.unit_ids.append(uid)
        
        # Обновляем technical_filters
        if natasha.get("filters"):
            for k, v in natasha["filters"].items():
                if k not in rule.technical_filters or rule.technical_filters.get(k) is None:
                    rule.technical_filters[k] = v
        
        # Обновляем references
        if natasha.get("references"):
            for ref in natasha["references"]:
                if ref not in rule.references:
                    rule.references.append(ref)
        
        return rule

    def _merge_results(self, rule: ParsedQuery, natasha: Dict, text: str) -> ParsedQuery:
        # Берем карточку из rule или создаем новую
        card = rule.card
        
        if card is None:
            card = ItemCard(
                card_id=None,
                item_type=None,
                subtype=None,
                designation=None,
                name=None,
                geometry=Geometry(),
                pressure=Pressure(),
                material=Material(),
                environment=Environment(),
                normative=Normative(),
                extraction=Extraction(
                    confidence=0.0,
                    method="hybrid",
                    missing_fields=[]
                ),
                sources=[Source(type="user_query", fragment=text)]
            )
        
        # Обновляем геометрию (только если нет в rule)
        if card.geometry is None:
            card.geometry = Geometry()
        
        params = natasha.get("parameters", {})
        
        # DN
        if params.get("dn") and card.geometry.dn is None:
            card.geometry.dn = params["dn"]
        
        # Толщина стенки
        if params.get("wall_thickness") and card.geometry.wall_thickness is None:
            card.geometry.wall_thickness = params["wall_thickness"]
        
        # Угол
        if params.get("angle") and card.geometry.angle is None:
            card.geometry.angle = params["angle"]
        
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
        if params.get("strength_class") and card.material.strength_class is None:
            card.material.strength_class = params["strength_class"]
        
        # Среда
        if card.environment is None:
            card.environment = Environment()
        if params.get("medium") and card.environment.medium is None:
            card.environment.medium = params["medium"]
            if params["medium"] == "H2S":
                card.environment.h2s_confirmed = True
            elif params["medium"] == "CO2":
                card.environment.co2_confirmed = True
        
        # Климатика
        if params.get("climate_version") and card.environment.climate_version is None:
            card.environment.climate_version = params["climate_version"]
        
        # Тип детали – если rule не нашёл
        if card.item_type is None and natasha.get("item_types"):
            card.item_type = natasha["item_types"][0]
        
        # Subtype
        if card.subtype is None and natasha.get("subtype"):
            card.subtype = natasha["subtype"]
        
        # Обновляем item_types
        item_types = rule.item_types or []
        if natasha.get("item_types"):
            for t in natasha["item_types"]:
                if t not in item_types:
                    item_types.append(t)
        
        # Обновляем component_ids
        component_ids = rule.component_ids or []
        if natasha.get("component_ids"):
            for cid in natasha["component_ids"]:
                if cid not in component_ids:
                    component_ids.append(cid)
        
        # Обновляем unit_ids
        unit_ids = rule.unit_ids or []
        if natasha.get("unit_ids"):
            for uid in natasha["unit_ids"]:
                if uid not in unit_ids:
                    unit_ids.append(uid)
        
        # Обновляем technical_filters
        technical_filters = rule.technical_filters.copy()
        if natasha.get("filters"):
            for k, v in natasha["filters"].items():
                if k not in technical_filters or technical_filters.get(k) is None:
                    technical_filters[k] = v
        
        # Обновляем references
        references = rule.references or []
        if natasha.get("references"):
            for ref in natasha["references"]:
                if ref not in references:
                    references.append(ref)
        
        # Обновляем stock_filters
        stock_filters = rule.stock_filters.copy()
        if natasha.get("stock_filters"):
            for k, v in natasha["stock_filters"].items():
                if k not in stock_filters or stock_filters.get(k) is None:
                    stock_filters[k] = v
        
        # Обновляем proposed_changes
        proposed_changes = rule.proposed_changes.copy()
        if natasha.get("changes"):
            for k, v in natasha["changes"].items():
                if k not in proposed_changes or proposed_changes.get(k) is None:
                    proposed_changes[k] = v
        
        # Обновляем unit_context и component_context
        unit_context = rule.unit_context.copy()
        component_context = rule.component_context.copy()
        
        if natasha.get("unit_id"):
            unit_context["unit_id"] = natasha["unit_id"]
        if natasha.get("component_id"):
            component_context["component_id"] = natasha["component_id"]
        if natasha.get("medium"):
            unit_context["medium"] = natasha["medium"]
        
        # Операции – дополняем Natasha
        operations = rule.operations.copy()
        if natasha.get("operations"):
            for op in natasha["operations"]:
                if op not in operations:
                    operations.append(op)
            operations = sorted(
                operations,
                key=lambda x: self.operation_parser.OPERATION_PRIORITY.get(x, 0),
                reverse=True
            )
        
        # Ambiguities
        ambiguities = rule.ambiguities or []
        if natasha.get("ambiguities"):
            for amb in natasha["ambiguities"]:
                if amb not in ambiguities:
                    ambiguities.append(amb)
        
        # Обновляем missing_fields
        if card.extraction:
            card.extraction.missing_fields = self.rule_parser._get_missing_fields(card)
            card.extraction.method = "hybrid"
        
        # Пересчёт confidence
        confidence = self._recalculate_confidence(card, operations, ambiguities, text)
        confidence_details = self._build_confidence_details(operations, card, ambiguities)
        
        # Required agents
        required_agents = self._determine_required_agents(
            operations=operations,
            component_ids=component_ids,
            unit_ids=unit_ids,
            references=references,
            ambiguities=ambiguities,
        )
        
        return ParsedQuery(
            original_query=text,
            operations=operations,
            item_types=item_types,
            component_ids=component_ids,
            unit_ids=unit_ids,
            card=card,
            cards=rule.cards or ([card] if card and card.item_type else []),
            technical_filters=technical_filters,
            stock_filters=stock_filters,
            proposed_changes=proposed_changes,
            impact_analysis=rule.impact_analysis or {},
            unit_context=unit_context,
            component_context=component_context,
            references=references,
            ambiguities=ambiguities,
            required_agents=required_agents,
            required_capabilities=rule.required_capabilities or [],
            confidence=confidence,
            confidence_details=confidence_details,
        )

    def _recalculate_confidence(
        self,
        card: ItemCard,
        operations: List[str],
        ambiguities: List[str],
        text: str
    ) -> float:
        score = 1.0
        
        if not operations or operations == ["unknown"]:
            score -= 0.3
        
        if card is None:
            score -= 0.25
            return max(0.0, min(1.0, score))
        
        missing = self.rule_parser._get_missing_fields(card)
        if missing:
            penalty = 0.0
            critical_fields = ["item_type", "dn"]
            for field in critical_fields:
                if field in missing:
                    penalty += 0.15
            
            important_fields = ["wall_thickness", "pn", "steel_grade", "medium"]
            for field in important_fields:
                if field in missing:
                    penalty += 0.05
            
            other_fields = ["geometry", "pressure", "material", "environment"]
            for field in other_fields:
                if field in missing:
                    penalty += 0.03
            
            score -= min(penalty, 0.5)
        
        if ambiguities:
            score -= min(0.15 * len(ambiguities), 0.3)
        
        word_count = len(text.split())
        if word_count < 3:
            score -= 0.15
        elif word_count < 5:
            score -= 0.05
        
        if re.search(r'COMP-|UNIT-|KSM-|MTR-', text):
            score += 0.05
        
        return max(0.0, min(1.0, score))

    def _build_confidence_details(
        self,
        operations: List[str],
        card: Optional[ItemCard],
        ambiguities: List[str]
    ) -> Dict[str, float]:
        details = {}
        
        if operations:
            details["operations"] = min(1.0, len(operations) * 0.2 + 0.2)
        else:
            details["operations"] = 0.0
        
        if card:
            missing = card.extraction.missing_fields if card.extraction else []
            if missing:
                details["card"] = max(0.0, 1.0 - len(missing) * 0.1)
            else:
                details["card"] = 1.0
        else:
            details["card"] = 0.0
        
        if ambiguities:
            details["ambiguities"] = max(0.0, 1.0 - len(ambiguities) * 0.2)
        else:
            details["ambiguities"] = 1.0
        
        return details

    def _determine_required_agents(
        self,
        operations: List[str],
        component_ids: List[str],
        unit_ids: List[str],
        references: List[str],
        ambiguities: List[str]
    ) -> List[str]:
        agents = set()
        
        mapping = {
            "search": "search",
            "replace": "search",
            "repair": "search",
            "plan": "plan",
            "check": "rules",
            "inventory": "inventory",
            "explain": "knowledge",
            "impact": "impact",
            "assemble": "plan",
            "calculate": "rules",
        }
        
        for op in operations:
            if op in mapping:
                agents.add(mapping[op])
        
        if component_ids or unit_ids:
            agents.add("topology")
        
        if references:
            agents.add("knowledge")
        
        if ambiguities:
            agents.add("human")
        
        return sorted(agents)
