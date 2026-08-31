# query_parser/parser.py

import re
from typing import Any, Dict, List, Optional

from .parsers.operation_parser import OperationParser
from .parsers.item_type_parser import ItemTypeParser
from .parsers.geometry_parser import GeometryParser
from .parsers.pressure_parser import PressureParser
from .parsers.material_parser import MaterialParser
from .parsers.environment_parser import EnvironmentParser
from .parsers.component_parser import ComponentParser
from .parsers.normative_parser import NormativeParser
from .parsers.context_parser import ContextParser
from .ambiguity_detector import AmbiguityDetector
from .context_extractor import ContextExtractor
from .confidence_calculator import ConfidenceCalculator
from .utils.data_utils import clean_technical_filters
from .dictionaries import refresh_dictionaries


from app.schemas import (
    ParsedQuery,
    ItemCard,
    Geometry,
    Pressure,
    Material,
    Environment,
    Normative,
    Source,
    Extraction,
)


class QueryParser:
    """Основной rule-based парсер инженерных запросов"""

    def __init__(self):
        # Инициализация всех парсеров
        self.operation_parser = OperationParser()
        self.item_type_parser = ItemTypeParser()
        self.geometry_parser = GeometryParser()
        self.pressure_parser = PressureParser()
        self.material_parser = MaterialParser()
        self.environment_parser = EnvironmentParser()
        self.component_parser = ComponentParser()
        self.normative_parser = NormativeParser()
        self.context_parser = ContextParser()
        self.ambiguity_detector = AmbiguityDetector()
        
        # Новые компоненты
        self.context_extractor = ContextExtractor()
        self.confidence_calculator = ConfidenceCalculator()

    def parse(self, text: str) -> ParsedQuery:
        """
        Основной метод парсинга запроса
        """
        # Валидация входных данных
        if not text or not text.strip():
            return self._empty_response(text or "")

        text = text.strip()

        # Обновляем алиасы из БД (не чаще раза в TTL, без перезапуска)
        refresh_dictionaries()

        # =========================================================
        # 1. Парсинг операций
        # =========================================================
        operations = self._safe_parse(self.operation_parser.parse_all, text)
        if not operations or operations == ["unknown"]:
            operations = ["search"]

        # =========================================================
        # 2. Парсинг сущностей
        # =========================================================
        item_types = self._safe_parse(self.item_type_parser.parse_multiple, text) or []
        geometry = self._safe_parse(self.geometry_parser.parse, text) or {}
        pressure = self._safe_parse(self.pressure_parser.parse, text) or {}
        material = self._safe_parse(self.material_parser.parse, text) or {}
        environment = self._safe_parse(self.environment_parser.parse, text) or {}
        normative = self._safe_parse(self.normative_parser.parse, text) or {}
        
        # Извлекаем component_ids и unit_ids из результатов
        ids_result = self._safe_parse(self.component_parser.parse_all, text) or {}
        comp_ids = ids_result.get('component_ids', []) if isinstance(ids_result, dict) else []
        unit_ids_list = ids_result.get('unit_ids', []) if isinstance(ids_result, dict) else []
        
        # Безопасная обработка material + normative
        material = self._clean_material_standard(material, normative)

        # =========================================================
        # 3. Контекст (используем новый ContextExtractor)
        # =========================================================
        context = self.context_extractor.extract(text) or {}

        # =========================================================
        # 4. Ссылки (references)
        # =========================================================
        references = self._extract_references(text, comp_ids, unit_ids_list)

        # =========================================================
        # 5. Изменения (changes)
        # =========================================================
        changes = self._extract_changes(text)

        # =========================================================
        # 6. Фильтры
        # =========================================================
        technical_filters = self._build_filters(
            geometry=geometry,
            pressure=pressure,
            material=material,
            environment=environment,
            item_types=item_types,
        )
        stock_filters = self._extract_stock_filters(text)

        # =========================================================
        # 7. Неоднозначности
        # =========================================================
        card_data_for_ambiguities = {
            "item_type": item_types[0] if item_types else None,
            "geometry": geometry,
            "pressure": pressure,
            "material": material,
            "environment": environment,
        }
        ambiguities = self._detect_ambiguities(
            text=text,
            card_data=card_data_for_ambiguities,
        )

        # =========================================================
        # 8. Построение карточек
        # =========================================================
        card, cards = self._build_cards(
            text=text,
            item_types=item_types,
            geometry=geometry,
            pressure=pressure,
            material=material,
            environment=environment,
            normative=normative,
        )

        # =========================================================
        # 9. Анализ влияния (impact analysis)
        # =========================================================
        impact_analysis = self._extract_impact_analysis(text, changes)

        # =========================================================
        # 10. Unit / Component контекст
        # =========================================================
        unit_context = self._extract_unit_context(text, unit_ids_list, environment)
        component_context = self._extract_component_context(text, comp_ids)

        # =========================================================
        # 11. Требуемые агенты
        # =========================================================
        required_agents = self._determine_required_agents(
            operations=operations,
            component_ids=comp_ids,
            unit_ids=unit_ids_list,
            references=references,
            ambiguities=ambiguities,
        )

        # =========================================================
        # 12. Возможности (capabilities)
        # =========================================================
        required_capabilities = self._detect_capabilities(
            operations=operations,
            text=text,
            references=references,
            changes=changes,
        )

        # =========================================================
        # 13. Уверенность (используем новый ConfidenceCalculator)
        # =========================================================
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

        # =========================================================
        # 14. Формирование результата
        # =========================================================
        return ParsedQuery(
            original_query=text,
            operations=operations,
            item_types=item_types,
            component_ids=comp_ids or [],
            unit_ids=unit_ids_list or [],
            card=card,
            cards=cards,
            technical_filters=technical_filters,
            stock_filters=stock_filters,
            units_count=context.get('units_count'),
            quantity=context.get('quantity'),
            length_m=context.get('length_meters'),
            limit=context.get('limit'),
            timeframe=context.get('timeframe'),
            urgency=context.get('urgency'),
            sort_by=context.get('sort_by'),
            on_stock=self._extract_on_stock(text),
            not_installed=self._extract_not_installed(text),
            proposed_changes=changes,
            impact_analysis=impact_analysis,
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
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _empty_response(self, text: str) -> ParsedQuery:
        """Ответ для пустого запроса"""
        return ParsedQuery(
            original_query=text,
            operations=[],
            confidence=0.0,
            ambiguities=["Пустой запрос"],
        )

    @staticmethod
    def _safe_parse(func, text):
        """Безопасный парсинг с обработкой ошибок"""
        try:
            return func(text)
        except Exception:
            return None

    def _clean_material_standard(self, material: Dict, normative: Dict) -> Dict:
        """
        Безопасная очистка стандарта материала
        Возвращает НОВЫЙ словарь без мутации
        """
        if not material or not normative:
            return material
        
        if not isinstance(material, dict) or not isinstance(normative, dict):
            return material

        material_standard = material.get("standard")
        normative_gost = normative.get("gost_tu")

        if material_standard and normative_gost and material_standard == normative_gost:
            # Создаём новый словарь вместо мутации
            return {**material, "standard": None}
        
        return material

    def _extract_references(self, text: str, component_ids=None, unit_ids=None) -> List[str]:
        """Извлечение ссылок на компоненты/участки"""
        references = []

        if component_ids:
            if isinstance(component_ids, str):
                references.append(component_ids)
            elif isinstance(component_ids, list):
                references.extend(component_ids)

        if unit_ids:
            if isinstance(unit_ids, str):
                references.append(unit_ids)
            elif isinstance(unit_ids, list):
                references.extend(unit_ids)

        patterns = [
            r"\bCOMP[-_][A-Z0-9-]+\b",
            r"\bUNIT[-_][A-Z0-9-]+\b",
            r"\bKSM[-_][A-Z0-9-]+\b",
            r"\bMTR[-_][A-Z0-9-]+\b",
        ]

        for pattern in patterns:
            references.extend(re.findall(pattern, text.upper()))

        return list(dict.fromkeys(references))

    def _extract_changes(self, text: str) -> Dict[str, Any]:
        """Извлечение предлагаемых изменений"""
        text_lower = text.lower()
        changes = {}

        # Смена среды на агрессивную (H2S/CO2 и синонимы): перевод/переход/смена/
        # замена/изменение среды В ДРУГУЮ не засчитывается без явной агрессивной цели.
        medium_change = re.search(
            r"(?:перевод\w*|переход\w*|смен\w*|замен\w*|измен\w*сред[аы])"
            r".{0,60}(?:на|для)\s+(h2s|сероводород\w*|co2|со2|углекисл\w+)",
            text_lower,
        )
        if medium_change:
            target = medium_change.group(1).lower()
            changes["medium"] = (
                "H2S" if target in ("h2s",) or target.startswith("сероводород") else "CO2"
            )

        # Диаметр: "DN200 вместо DN150"
        diameter_match = re.search(
            r"(?:dn|ду)\s*(\d+).{0,30}(?:вместо|на)\s+(?:dn|ду)?\s*(\d+)",
            text_lower,
        )
        if diameter_match:
            first = float(diameter_match.group(1))
            second = float(diameter_match.group(2))
            changes["dn_to"] = first
            changes["dn_from"] = second

        # Материал: "стали 20 на 09Г2С" -> from=20, to=09Г2С
        material_match = re.search(
            r"(?:из\s+)?стали?\s+([0-9а-яёa-z]+)\s+(?:на|в|вместо)\s+([0-9а-яёa-z]+)",
            text_lower,
            re.IGNORECASE
        )
        if material_match:
            material_from = material_match.group(1).upper()
            material_to = material_match.group(2).upper()
            garbage_words = ["УЧАСТКЕ", "СКЛАДЕ", "НЕТ", "ЕСТЬ"]
            if material_from not in garbage_words and material_to not in garbage_words:
                changes["material_from"] = material_from
                changes["material_to"] = material_to

        # Класс прочности: "К52 вместо К48"
        strength_match = re.search(r'(К\d+)\s+(?:вместо|на)\s+(К\d+)', text_lower)
        if strength_match:
            changes["strength_to"] = strength_match.group(1).upper()
            changes["strength_from"] = strength_match.group(2).upper()

        # Класс прочности (обратный порядок)
        strength_match_reverse = re.search(r'(?:вместо|на)\s+(К\d+)\s+(К\d+)', text_lower)
        if strength_match_reverse:
            changes["strength_from"] = strength_match_reverse.group(1).upper()
            changes["strength_to"] = strength_match_reverse.group(2).upper()

        return changes

    # Числительные для складских фильтров
    STOCK_NUMERALS = {
        "один": 1, "одну": 1, "одна": 1, "одного": 1, "одним": 1,
        "два": 2, "две": 2, "двух": 2, "двумя": 2,
        "три": 3, "трёх": 3, "трех": 3, "тремя": 3,
        "четыре": 4, "четырёх": 4, "четырех": 4,
        "пять": 5, "пяти": 5, "пятью": 5,
        "десять": 10, "десяти": 10,
        "двадцать": 20, "двадцати": 20,
        "тридцать": 30, "тридцати": 30,
        "сорок": 40, "сорока": 40,
        "пятьдесят": 50, "пятидесяти": 50,
        "шестьдесят": 60, "шестидесяти": 60,
        "семьдесят": 70, "семидесяти": 70,
        "восемьдесят": 80, "восьмидесяти": 80,
        "девяносто": 90, "девяноста": 90,
        "сто": 100, "ста": 100,
        "двести": 200, "двухсот": 200,
        "триста": 300, "пятьсот": 500,
        "тысяча": 1000, "тысячи": 1000,
    }

    def _parse_quantity_token(self, token: str) -> Optional[int]:
        """Преобразование числа или числительного в количество"""
        token = token.lower()
        if token.isdigit():
            return int(token)
        return self.STOCK_NUMERALS.get(token)

    def _extract_stock_filters(self, text: str) -> Dict[str, Any]:
        """Извлечение складских фильтров"""
        filters = {}
        text_lower = text.lower()

        # Количество: больше/более/свыше X
        match = re.search(r'(?:больше|более|свыше)\s+([а-яё]+|\d+)', text_lower)
        if match:
            qty = self._parse_quantity_token(match.group(1))
            if qty is not None:
                filters["quantity_min"] = qty

        # Количество: меньше/менее/не более X
        match = re.search(r'(?:меньше|менее|не более)\s+([а-яё]+|\d+)', text_lower)
        if match:
            qty = self._parse_quantity_token(match.group(1))
            if qty is not None:
                filters["quantity_max"] = qty

        # Safety stock: "один полный комплект должен оставаться на складе"
        match = re.search(r'(один|одну|одна|1|два|две|2|три|3)\s+(?:полный\s+)?комплект\b', text_lower)
        if match and re.search(r'оставаться|остается|остаётся', text_lower):
            qty = self._parse_quantity_token(match.group(1))
            if qty is not None:
                filters["quantity_min"] = qty

        # Категория склада
        if re.search(r'склад\w*', text_lower):
            filters["stock_category"] = "main"

        return filters

    @staticmethod
    def _extract_on_stock(text: str) -> Optional[bool]:
        """Есть ли товар на складе: «нет на складе» -> False, «есть/в наличии» -> True."""
        text_lower = text.lower()
        if re.search(r'(?:нет|нету|нет в наличии|отсутств\w+|не имеется|не хватает)[^.!?;]{0,40}(?:на складе|на склад|в наличии)', text_lower):
            return False
        if re.search(r'(?:есть|имеется|в наличии|есть на складе)', text_lower):
            return True
        return None

    @staticmethod
    def _extract_not_installed(text: str) -> Optional[bool]:
        """«не установлены ни на одном участке» -> True."""
        text_lower = text.lower()
        if re.search(r'не\s+установл\w+', text_lower):
            return True
        return None

    def _extract_impact_analysis(self, text: str, changes: Dict) -> Dict[str, Any]:
        """Извлечение анализа влияния изменений"""
        analysis = {}
        text_lower = text.lower()
        checks = []

        # Проверки
        if re.search(r'(?:проверить|проверь|убедиться|убедитесь)', text_lower):
            checks.append("проверить совместимость с соседними деталями")
        if re.search(r'\bдавлени[ея]\b', text_lower):
            checks.append("проверить давление в системе")
        if re.search(r'\bтемператур[аы]\b', text_lower):
            checks.append("проверить температуру")
        if re.search(r'\bсред[аы]|h2s|co2\b', text_lower):
            checks.append("проверить совместимость со средой")

        if checks:
            analysis["required_checks"] = checks

        # Затронутые компоненты
        if changes:
            if changes.get("dn_from") or changes.get("dn_to"):
                analysis["affected_components"] = ["фланцы", "прокладки", "болты"]
            if changes.get("medium"):
                affected = analysis.get("affected_components", [])
                analysis["affected_components"] = affected + ["уплотнения", "материал деталей"]

        return analysis

    def _extract_unit_context(self, text: str, unit_ids: List[str], environment: Dict) -> Dict[str, Any]:
        """Извлечение контекста участка"""
        context = {}
        text_lower = text.lower()

        if unit_ids:
            context["unit_id"] = unit_ids[0]

        if environment and environment.get("medium"):
            context["medium"] = environment["medium"]

        # Температура
        temp_match = re.search(r'температур[аы]?\s*[-+]?(\d+(?:[.,]\d+)?)', text_lower)
        if temp_match:
            context["temperature"] = float(temp_match.group(1).replace(',', '.'))

        # Давление
        press_match = re.search(r'давлени[ея]?\s*[-+]?(\d+(?:[.,]\d+)?)', text_lower)
        if press_match:
            context["pressure"] = float(press_match.group(1).replace(',', '.'))

        return context

    def _extract_component_context(self, text: str, component_ids: List[str]) -> Dict[str, Any]:
        """Извлечение контекста компонента"""
        context = {}
        text_lower = text.lower()

        if component_ids:
            context["component_id"] = component_ids[0]

        # Позиция
        pos_match = re.search(r'\b(до|после|перед|за|между)\s+(?:COMP-|компонент|деталь)', text_lower)
        if pos_match:
            context["position"] = pos_match.group(1)

        # Соседние детали
        if re.search(r'\bсоседн(?:ий|яя|ее|ие)\b', text_lower):
            context["connections"] = ["соседние детали"]

        return context

    # =========================================================
    # ТРЕБУЕМЫЕ АГЕНТЫ И ВОЗМОЖНОСТИ (ОБНОВЛЕНЫ)
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
        Обновлено с учётом новых операций
        """
        agents = set()

        # Обновлённый маппинг с новыми операциями
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
            "document": "knowledge",  # ✅ Добавлена новая операция
        }

        for op in operations:
            if op in mapping:
                agents.add(mapping[op])

        if component_ids or unit_ids:
            agents.add("topology")

        if references:
            agents.add("knowledge")

        if ambiguities:
            agents.add("human")  # ✅ Добавлен human агент

        return sorted(agents)

    def _detect_capabilities(
        self,
        operations: List[str],
        text: str,
        references: List[str],
        changes: Dict[str, Any]
    ) -> List[str]:
        """
        Определение требуемых возможностей
        Обновлено с учётом новых операций
        """
        capabilities = set()
        
        # Обновлённый маппинг
        mapping = {
            "search": "search",
            "replace": "replacement_matching",
            "repair": "repair_planning",
            "plan": "maintenance_planning",
            "check": "compatibility_check",
            "inventory": "inventory",
            "document": "document_search",
            "explain": "knowledge_search",
            "impact": "impact_analysis",
            "assemble": "assembly_planning",
            "calculate": "calculation",
        }
        
        for operation in operations:
            capability = mapping.get(operation)
            if capability:
                capabilities.add(capability)

        if references:
            capabilities.add("topology")
        if changes:
            capabilities.add("impact_analysis")
        if re.search(r"\b(?:склад|остаток|наличие|закуп|пополн)", text.lower()):
            capabilities.add("inventory")
        if re.search(r"\b(?:ГОСТ|ТУ)\s+[\d\-]+", text.upper()):
            capabilities.add("knowledge_search")
        if re.search(r"\b(?:паспорт|документ|ЛНД)\b", text.lower()):
            capabilities.add("document_search")

        return sorted(capabilities)

    # =========================================================
    # ПОСТРОЕНИЕ КАРТОЧЕК
    # =========================================================

    def _build_cards(
        self,
        text: str,
        item_types: List[str],
        geometry: Dict,
        pressure: Dict,
        material: Dict,
        environment: Dict,
        normative: Dict,
    ) -> tuple[Optional[ItemCard], List[ItemCard]]:
        """
        Построение карточек (одной или нескольких)
        Возвращает (main_card, cards_list)
        """
        # Проверка на участок без параметров
        if self._is_unit_without_params(text, item_types, geometry, pressure, material, environment):
            return None, []

        has_data = any(x is not None for x in [item_types, geometry, pressure, material, environment, normative])
        if not has_data:
            return None, []

        # Преобразование в Pydantic-модели
        geometry_obj = self._to_model(geometry, Geometry)
        pressure_obj = self._to_model(pressure, Pressure)
        material_obj = self._to_model(material, Material)
        environment_obj = self._to_model(environment, Environment)
        normative_obj = self._to_model(normative, Normative)

        # Определяем subtype
        subtype = self.item_type_parser.parse_subtype(text)

        # Если один тип — одна карточка
        if len(item_types) == 1:
            card = self._build_single_card(
                text=text,
                item_type=item_types[0],
                subtype=subtype,
                geometry=geometry_obj,
                pressure=pressure_obj,
                material=material_obj,
                environment=environment_obj,
                normative=normative_obj,
            )
            return card, [card] if card else []

        # Если несколько типов — несколько карточек
        elif len(item_types) > 1:
            cards = []
            for it_type in item_types:
                card = self._build_single_card(
                    text=text,
                    item_type=it_type,
                    subtype=subtype,
                    geometry=geometry_obj,
                    pressure=pressure_obj,
                    material=material_obj,
                    environment=environment_obj,
                    normative=normative_obj,
                )
                if card:
                    cards.append(card)
            return cards[0] if cards else None, cards

        # Если нет типа — пробуем без типа
        else:
            card = self._build_single_card(
                text=text,
                item_type=None,
                subtype=subtype,
                geometry=geometry_obj,
                pressure=pressure_obj,
                material=material_obj,
                environment=environment_obj,
                normative=normative_obj,
            )
            return card, [card] if card else []

    def _is_unit_without_params(self, text: str, item_types: List[str],
                                geometry: Dict, pressure: Dict, material: Dict,
                                environment: Dict) -> bool:
        """Проверка, что запрос про участок без параметров детали"""
        if not re.search(r'\b(?:участок|схема|состоит|участке)\b', text, re.IGNORECASE):
            return False

        if item_types:
            return False

        has_params = False
        if geometry and isinstance(geometry, dict):
            if any([geometry.get('dn'), geometry.get('d1'), geometry.get('wall_thickness')]):
                has_params = True
        if pressure and isinstance(pressure, dict):
            if pressure.get('pn'):
                has_params = True
        if material and isinstance(material, dict):
            if material.get('steel_grade'):
                has_params = True
        if environment and isinstance(environment, dict):
            if any([environment.get('medium'), environment.get('h2s_confirmed'),
                    environment.get('co2_confirmed'), environment.get('temperature_min_c')]):
                has_params = True

        return not has_params

    def _build_single_card(
        self,
        text: str,
        item_type: Optional[str],
        subtype: Optional[str],
        geometry: Optional[Geometry],
        pressure: Optional[Pressure],
        material: Optional[Material],
        environment: Optional[Environment],
        normative: Optional[Normative],
    ) -> Optional[ItemCard]:
        """Построение одной карточки"""
        # Определяем item_type и subtype
        if isinstance(item_type, dict):
            base_type = item_type.get("item_type")
            if not subtype:
                subtype = item_type.get("subtype")
        else:
            base_type = item_type

        # Проверяем, что есть хоть какие-то данные
        if not any([base_type, geometry, pressure, material, environment, normative]):
            return None

        # Создаём карточку
        card = ItemCard(
            card_id=None,
            item_type=base_type,
            subtype=subtype,
            designation=self._build_designation(geometry, pressure, material, environment),
            name=self._build_name(base_type, geometry, pressure),
            geometry=geometry,
            pressure=pressure,
            material=material,
            environment=environment,
            normative=normative,
            extraction=Extraction(
                confidence=0.0,
                method="user_query",
                missing_fields=[]
            ),
            sources=[Source(type="user_query", fragment=text)],
        )

        # Безопасная обработка материала с учётом изменений
        card = self._apply_material_changes(card, text)

        # Обновляем missing_fields
        missing = self._get_missing_fields(card)
        if card.extraction:
            card.extraction.missing_fields = missing

        return card

    def _apply_material_changes(self, card: ItemCard, text: str) -> ItemCard:
        """
        Применяет изменения материала к карточке
        Возвращает НОВУЮ карточку без мутации
        """
        if not card.material or not card.material.steel_grade:
            return card

        changes = self._extract_changes(text)
        if changes.get('material_from'):
            # Создаём новый объект Material с обновлённой сталью
            new_material = Material(
                steel_grade=changes['material_from'],
                strength_class=card.material.strength_class,
                standard=card.material.standard,
            )
            
            # Создаём новую карточку с обновлённым материалом
            new_card = ItemCard(
                card_id=card.card_id,
                item_type=card.item_type,
                subtype=card.subtype,
                designation=self._build_designation(
                    card.geometry, card.pressure, new_material, card.environment
                ),
                name=card.name,
                geometry=card.geometry,
                pressure=card.pressure,
                material=new_material,
                environment=card.environment,
                normative=card.normative,
                extraction=card.extraction,
                sources=card.sources,
            )
            return new_card

        return card

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ КАРТОЧЕК (ОБНОВЛЕНЫ)
    # =========================================================

    def _get_missing_fields(self, card: Optional[ItemCard]) -> List[str]:
        """Определение отсутствующих полей в карточке"""
        missing = []

        if card is None:
            return ["full_card"]

        if card.item_type is None:
            missing.append("item_type")

        transition_types = ["переход", "тройник"]
        angle_types = ["отвод", "кран"]
        
        if card.geometry:
            if card.item_type in transition_types:
                if card.geometry.d1 is None and card.geometry.d2 is None:
                    missing.append("geometry")
            else:
                if card.geometry.dn is None:
                    missing.append("dn")
                if card.geometry.wall_thickness is None and card.geometry.d1 is None:
                    missing.append("geometry")
                if card.item_type in angle_types and card.geometry.angle is None:
                    missing.append("angle")
        else:
            missing.append("geometry")

        # ✅ Проверяем PN - только если он должен быть (не для всех типов)
        # Для заглушек, задвижек, фланцев PN важен
        pn_required_types = ["задвижка", "заглушка", "фланец", "кран"]
        if card.item_type in pn_required_types:
            if card.pressure and card.pressure.pn is None:
                missing.append("pn")
            elif card.pressure is None:
                missing.append("pressure")
        else:
            # Для остальных типов PN не обязателен, но если нет pressure - отмечаем
            if card.pressure is None:
                missing.append("pressure")

        if card.material and card.material.steel_grade is None:
            missing.append("material")
        elif card.material is None:
            missing.append("material")

        if card.environment and card.environment.medium is None:
            missing.append("medium")
        elif card.environment is None:
            missing.append("environment")

        return missing

    @staticmethod
    def _to_model(value, model_class):
        """Преобразование словаря в Pydantic-модель"""
        if value is None:
            return None
        if isinstance(value, model_class):
            return value
        if isinstance(value, dict):
            try:
                return model_class(**value)
            except Exception:
                return None
        if hasattr(value, "model_dump"):
            try:
                return model_class(**value.model_dump())
            except Exception:
                return None
        return None

    @staticmethod
    def _build_designation(geometry, pressure, material, environment) -> Optional[str]:
        """Построение условного обозначения"""
        parts = []
        if geometry:
            if geometry.dn:
                parts.append(f"DN{geometry.dn:g}")
            if geometry.d1 and geometry.d2:
                parts.append(f"{geometry.d1:g}x{geometry.d2:g}")
            if geometry.wall_thickness:
                parts.append(f"δ{geometry.wall_thickness:g}")
            if geometry.angle:
                parts.append(f"{geometry.angle:g}°")
        # ✅ Добавляем PN только если он есть И был указан явно (есть raw_value)
        if pressure and pressure.pn is not None and pressure.raw_value:
            parts.append(f"PN{pressure.pn:g}")
        if material and material.steel_grade:
            parts.append(material.steel_grade)
        if material and material.strength_class:
            parts.append(material.strength_class)
        if environment and environment.medium:
            parts.append(environment.medium)
        return " ".join(parts) if parts else None

    @staticmethod
    def _build_name(item_type, geometry, pressure) -> Optional[str]:
        """Построение человекочитаемого имени"""
        if not item_type:
            return None
        name = str(item_type)
        if geometry:
            if geometry.angle:
                name += f" {geometry.angle:g}°"
            if geometry.dn:
                name += f" DN{geometry.dn:g}"
        # ✅ Добавляем PN только если он есть И был указан явно (есть raw_value)
        if pressure and pressure.pn is not None and pressure.raw_value:
            name += f" PN{pressure.pn:g}"
        return name

    # =========================================================
    # ФИЛЬТРЫ
    # =========================================================

    def _build_filters(self, geometry=None, pressure=None, material=None, environment=None, item_types=None) -> Dict[str, Any]:
        """Построение технических фильтров"""
        filters = {}

        # Тип детали
        if item_types and len(item_types) > 1:
            pass
        elif item_types and len(item_types) == 1:
            filters["item_type"] = item_types[0]

        # Геометрия
        if geometry and isinstance(geometry, dict):
            if geometry.get('d1') and geometry.get('d2'):
                filters["d1"] = geometry["d1"]
                filters["d2"] = geometry["d2"]
            if geometry.get('dn'):
                filters["dn"] = geometry["dn"]
            if geometry.get('wall_thickness') and not geometry.get('d1'):
                filters["wall_thickness"] = geometry["wall_thickness"]
            if geometry.get('angle'):
                filters["angle"] = geometry["angle"]

        # Остальные параметры
        for obj in [pressure, material, environment]:
            if obj:
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if v is not None and v != "":
                            filters[k] = v
                elif hasattr(obj, "model_dump"):
                    for k, v in obj.model_dump().items():
                        if v is not None and v != "":
                            filters[k] = v

        # Используем утилиту для очистки
        return clean_technical_filters(filters)

    # =========================================================
    # НЕОДНОЗНАЧНОСТИ
    # =========================================================

    def _detect_ambiguities(self, text: str, card_data: Optional[Dict[str, Any]] = None) -> List[str]:
        """Обнаружение неоднозначностей"""
        ambiguities = []

        # Используем AmbiguityDetector
        try:
            result = self.ambiguity_detector.detect(text, card_data or {})
            if result:
                if isinstance(result, list):
                    ambiguities.extend([amb.reason for amb in result if hasattr(amb, 'reason')])
                elif isinstance(result, dict):
                    ambiguities.extend(result.get("ambiguities", []))
        except Exception:
            pass

        # Дополнительные проверки
        dns = re.findall(r"\b(?:dn|ду)\s*(\d+(?:[.,]\d+)?)", text.lower())
        if len(set(dns)) > 1:
            ambiguities.append("В запросе указано несколько значений DN")

        pns = re.findall(r"\bpn\s*(\d+(?:[.,]\d+)?)", text.lower())
        if len(set(pns)) > 1:
            ambiguities.append("В запросе указано несколько значений PN")

        return list(dict.fromkeys(ambiguities))
