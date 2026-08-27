# query_parser/hybrid_parser.py

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
# from .normalizers.morph_normalizer import MorphNormalizer
from .dictionaries import get_operations
from .confidence_calculator import ConfidenceCalculator


class HybridParser:
    """
    Гибридный парсер, объединяющий rule-based и NLP подходы.
    
    Стратегия:
    1. Сначала запускается rule-based парсер (быстрый и точный)
    2. Если confidence >= 0.8 - результат считается хорошим, Natasha только дополняет
    3. Если confidence < 0.8 - запускается Natasha и результаты объединяются
    """
    
    # Порог, выше которого rule-based результат считается достаточным
    RULE_CONFIDENCE_THRESHOLD = 0.8
    
    def __init__(self):
        self.rule_parser = QueryParser()
        self.natasha_parser = NatashaParser()
        # self.morph_normalizer = MorphNormalizer()
        self.operation_parser = OperationParser()
        self.confidence_calculator = ConfidenceCalculator()

    def parse(self, text: str) -> ParsedQuery:
        """
        Основной метод парсинга с гибридным подходом
        """
        # 1. Rule-based парсинг
        rule_result = self.rule_parser.parse(text)
        
        # 2. Natasha парсинг (всегда запускаем, но используем по-разному)
        natasha_result = self.natasha_parser.parse(text)
        
        # 3. Если rule уже хороший - только дополняем
        if rule_result.confidence >= self.RULE_CONFIDENCE_THRESHOLD:
            return self._enrich_result(rule_result, natasha_result, text)
        
        # 4. Иначе - полноценное объединение
        return self._merge_results(rule_result, natasha_result, text)

    # =========================================================
    # СТРАТЕГИИ ОБЪЕДИНЕНИЯ
    # =========================================================

    def _enrich_result(self, rule: ParsedQuery, natasha: Dict, text: str) -> ParsedQuery:
        """
        Дополняет rule-результат данными из Natasha (без изменения структуры)
        """
        card = rule.card
        
        # 1. Добавляем subtype
        if card and card.subtype is None and natasha.get("subtype"):
            card.subtype = natasha["subtype"]
        
        # 2. Операции: rule-based результат авторитетен (natasha добавляет шум).
        #    Natasha используется только как fallback, если rule не нашёл ничего.
        rule.operations = self._merge_operations(rule.operations, natasha.get("operations", []), text)
        
        # 3. Добавляем ID компонентов и участков (из Natasha)
        if natasha.get("component_ids"):
            for cid in natasha["component_ids"]:
                if cid not in rule.component_ids:
                    rule.component_ids.append(cid)
        
        if natasha.get("unit_ids"):
            for uid in natasha["unit_ids"]:
                if uid not in rule.unit_ids:
                    rule.unit_ids.append(uid)
        
        # 4. Обновляем фильтры
        if natasha.get("filters"):
            for k, v in natasha["filters"].items():
                if k not in rule.technical_filters or rule.technical_filters.get(k) is None:
                    rule.technical_filters[k] = v
        
        # 5. Обновляем references
        if natasha.get("references"):
            for ref in natasha["references"]:
                if ref not in rule.references:
                    rule.references.append(ref)
        
        # 6. Обновляем ambiguities
        if natasha.get("ambiguities"):
            for amb in natasha["ambiguities"]:
                if amb not in rule.ambiguities:
                    rule.ambiguities.append(amb)
        
        # 7. Обновляем карточку из Natasha (если есть пропуски)
        if card and natasha.get("parameters"):
            card = self._enrich_card(card, natasha)
            rule.card = card
        
        # 8. Пересчитываем confidence (с учётом дополнений)
        rule.confidence = self.confidence_calculator.calculate(
            text=text,
            operations=rule.operations,
            card=card,
            ambiguities=rule.ambiguities,
            references=rule.references,
        )
        rule.confidence_details = self.confidence_calculator.build_details(
            operations=rule.operations,
            card=card,
            ambiguities=rule.ambiguities,
        )
        
        return rule

    def _merge_results(self, rule: ParsedQuery, natasha: Dict, text: str) -> ParsedQuery:
        """
        Полноценное объединение rule и Natasha результатов
        """
        # 1. Создаём или обновляем карточку
        card = self._merge_card(rule.card, natasha, text)
        
        # 2. Объединяем все списки
        item_types = self._merge_unique_lists(rule.item_types, natasha.get("item_types", []))
        component_ids = self._merge_unique_lists(rule.component_ids, natasha.get("component_ids", []))
        unit_ids = self._merge_unique_lists(rule.unit_ids, natasha.get("unit_ids", []))
        references = self._merge_unique_lists(rule.references, natasha.get("references", []))
        ambiguities = self._merge_unique_lists(rule.ambiguities, natasha.get("ambiguities", []))
        
        # ✅ 3. Объединяем операции (rule авторитетен; natasha только как fallback)
        operations = self._merge_operations(rule.operations, natasha.get("operations", []), text)
        
        # 4. Объединяем фильтры (Natasha дополняет rule)
        technical_filters = self._merge_filters(rule.technical_filters, natasha.get("filters", {}))
        stock_filters = self._merge_filters(rule.stock_filters, natasha.get("stock_filters", {}))
        
        # 5. Объединяем контексты
        unit_context = self._merge_contexts(rule.unit_context, natasha)
        component_context = self._merge_contexts(rule.component_context, natasha)
        
        # 6. Объединяем изменения
        proposed_changes = self._merge_dicts(rule.proposed_changes, natasha.get("changes", {}))
        
        # 7. Обновляем missing_fields
        if card and card.extraction:
            card.extraction.missing_fields = self.rule_parser._get_missing_fields(card)
            card.extraction.method = "hybrid"
        
        # 8. Пересчитываем confidence
        confidence = self.confidence_calculator.calculate(
            text=text,
            operations=operations,
            card=card,
            ambiguities=ambiguities,
            references=references,
        )
        confidence_details = self.confidence_calculator.build_details(
            operations=operations,
            card=card,
            ambiguities=ambiguities,
        )
        
        # 9. Определяем требуемых агентов
        required_agents = self._determine_required_agents(
            operations=operations,
            component_ids=component_ids,
            unit_ids=unit_ids,
            references=references,
            ambiguities=ambiguities,
        )
        
        # 10. Определяем capabilities
        required_capabilities = self.rule_parser._detect_capabilities(
            operations=operations,
            text=text,
            references=references,
            changes=proposed_changes,
        )
        
        # 11. Формируем результат
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
            units_count=rule.units_count,
            length_m=rule.length_m,
            limit=rule.limit,
            timeframe=rule.timeframe,
            urgency=rule.urgency,
            sort_by=rule.sort_by,
            on_stock=rule.on_stock,
            not_installed=rule.not_installed,
            proposed_changes=proposed_changes,
            impact_analysis=rule.impact_analysis or {},
            unit_context=unit_context,
            component_context=component_context,
            references=references,
            ambiguities=ambiguities,
            required_agents=required_agents,
            required_capabilities=required_capabilities,
            confidence=confidence,
            confidence_details=confidence_details,
        )

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ СЛИЯНИЯ
    # =========================================================

    def _merge_card(self, rule_card: Optional[ItemCard], natasha: Dict, text: str) -> Optional[ItemCard]:
        """
        Слияние карточки из rule и Natasha
        """
        if rule_card is None:
            return self._create_card_from_natasha(natasha, text)
        return self._enrich_card(rule_card, natasha)

    def _create_card_from_natasha(self, natasha: Dict, text: str) -> Optional[ItemCard]:
        """
        Создание карточки из Natasha данных
        """
        params = natasha.get("parameters", {})
        item_types = natasha.get("item_types", [])
        
        if not item_types and not params:
            return None
        
        card = ItemCard(
            card_id=None,
            item_type=item_types[0] if item_types else None,
            subtype=natasha.get("subtype"),
            designation=None,
            name=None,
            geometry=Geometry(
                dn=params.get("dn"),
                wall_thickness=params.get("wall_thickness"),
                angle=params.get("angle"),
            ),
            pressure=Pressure(
                pn=params.get("pressure"),
            ),
            material=Material(
                steel_grade=params.get("steel_grade"),
                strength_class=params.get("strength_class"),
            ),
            environment=Environment(
                medium=params.get("medium"),
                h2s_confirmed=params.get("medium") == "H2S",
                co2_confirmed=params.get("medium") == "CO2",
                climate_version=params.get("climate_version"),
            ),
            normative=Normative(),
            extraction=Extraction(
                confidence=0.0,
                method="natasha",
                missing_fields=[]
            ),
            sources=[Source(type="user_query", fragment=text)],
        )
        
        card.designation = self.rule_parser._build_designation(
            card.geometry, card.pressure, card.material, card.environment
        )
        card.name = self.rule_parser._build_name(
            card.item_type, card.geometry, card.pressure
        )
        card.extraction.missing_fields = self.rule_parser._get_missing_fields(card)
        
        return card

    def _enrich_card(self, card: ItemCard, natasha: Dict) -> ItemCard:
        """
        Дополнение существующей карточки данными из Natasha
        """
        params = natasha.get("parameters", {})
        
        if card.geometry is None:
            card.geometry = Geometry()
        if params.get("dn") and card.geometry.dn is None:
            card.geometry.dn = params["dn"]
        if params.get("wall_thickness") and card.geometry.wall_thickness is None:
            card.geometry.wall_thickness = params["wall_thickness"]
        if params.get("angle") and card.geometry.angle is None:
            card.geometry.angle = params["angle"]
        
        if card.pressure is None:
            card.pressure = Pressure()
        if params.get("pressure") and card.pressure.pn is None:
            card.pressure.pn = params["pressure"]
        
        if card.material is None:
            card.material = Material()
        if params.get("steel_grade") and card.material.steel_grade is None:
            card.material.steel_grade = params["steel_grade"]
        if params.get("strength_class") and card.material.strength_class is None:
            card.material.strength_class = params["strength_class"]
        
        if card.environment is None:
            card.environment = Environment()
        if params.get("medium") and card.environment.medium is None:
            card.environment.medium = params["medium"]
            if params["medium"] == "H2S":
                card.environment.h2s_confirmed = True
            elif params["medium"] == "CO2":
                card.environment.co2_confirmed = True
        
        if params.get("climate_version") and card.environment.climate_version is None:
            card.environment.climate_version = params["climate_version"]
        
        if card.item_type is None and natasha.get("item_types"):
            card.item_type = natasha["item_types"][0]
        
        if card.subtype is None and natasha.get("subtype"):
            card.subtype = natasha["subtype"]
        
        card.designation = self.rule_parser._build_designation(
            card.geometry, card.pressure, card.material, card.environment
        )
        card.name = self.rule_parser._build_name(
            card.item_type, card.geometry, card.pressure
        )
        
        return card

    def _merge_unique_lists(self, list1: List, list2: List) -> List:
        """
        Объединение списков с сохранением уникальности
        """
        result = list1.copy() if list1 else []
        for item in list2:
            if item not in result:
                result.append(item)
        return result

    def _merge_operations(self, rule_ops: List[str], natasha_ops: List[str], text: str) -> List[str]:
        """
        Объединение операций: rule-based результат авторитетен,
        natasha используется только как fallback при пустом rule-результате.
        """
        rule_ops = [op for op in (rule_ops or []) if op != "unknown"]
        if rule_ops:
            return self._sort_operations(rule_ops)

        valid_operations = get_operations()
        natasha_ops = [op for op in (natasha_ops or []) if op in valid_operations]
        if natasha_ops:
            return self._sort_operations(natasha_ops)

        return ["search"]

    def _merge_filters(self, base: Dict, override: Dict) -> Dict:
        """
        Объединение фильтров (override дополняет base)
        """
        result = base.copy() if base else {}
        for k, v in override.items():
            if v is not None and (k not in result or result.get(k) is None):
                result[k] = v
        return result

    def _merge_dicts(self, base: Dict, override: Dict) -> Dict:
        """
        Объединение словарей (override дополняет base)
        """
        result = base.copy() if base else {}
        for k, v in override.items():
            if v is not None and (k not in result or result.get(k) is None):
                result[k] = v
        return result

    def _merge_contexts(self, base_context: Dict, natasha: Dict) -> Dict:
        """
        Объединение контекстов
        """
        context = base_context.copy() if base_context else {}
        
        if natasha.get("unit_id"):
            context["unit_id"] = natasha["unit_id"]
        if natasha.get("component_id"):
            context["component_id"] = natasha["component_id"]
        if natasha.get("medium"):
            context["medium"] = natasha["medium"]
        
        return context

    def _sort_operations(self, operations: List[str]) -> List[str]:
        """
        Сортировка операций по приоритету
        """
        return sorted(
            operations,
            key=lambda x: self.operation_parser.OPERATION_PRIORITY.get(x, 0),
            reverse=True
        )

    # =========================================================
    # ОПРЕДЕЛЕНИЕ АГЕНТОВ
    # =========================================================

    def _determine_required_agents(
        self,
        operations: List[str],
        component_ids: List[str],
        unit_ids: List[str],
        references: List[str],
        ambiguities: List[str]
    ) -> List[str]:
        """
        Определение требуемых агентов
        """
        return self.rule_parser._determine_required_agents(
            operations=operations,
            component_ids=component_ids,
            unit_ids=unit_ids,
            references=references,
            ambiguities=ambiguities,
        )
