# query_parser/parser.py

import re
from typing import Any, Dict, List, Optional

from .operation_parser import OperationParser
from .item_type_parser import ItemTypeParser
from .geometry_parser import GeometryParser
from .pressure_parser import PressureParser
from .material_parser import MaterialParser
from .environment_parser import EnvironmentParser
from .component_parser import ComponentParser
from .unit_parser import UnitParser
from .normative_parser import NormativeParser
from .context_parser import ContextParser
from .ambiguity_detector import AmbiguityDetector

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

    def __init__(self):
        self.operation_parser = OperationParser()
        self.item_type_parser = ItemTypeParser()
        self.geometry_parser = GeometryParser()
        self.pressure_parser = PressureParser()
        self.material_parser = MaterialParser()
        self.environment_parser = EnvironmentParser()
        self.component_parser = ComponentParser()
        self.unit_parser = UnitParser()
        self.normative_parser = NormativeParser()
        self.context_parser = ContextParser()
        self.ambiguity_detector = AmbiguityDetector()

    def parse(self, text: str) -> ParsedQuery:
        if not text or not text.strip():
            return ParsedQuery(
                original_query=text or "",
                operation="unknown",
                operations=[],
                confidence=0.0,
                ambiguities=["Пустой запрос"],
            )

        text = text.strip()

        # -----------------------------------------------------
        # 1. Операции
        # -----------------------------------------------------

        operations = self._safe_parse(
            self.operation_parser.parse_all,
            text
        )

        if not operations or operations == ["unknown"]:
            operations = ["search"]

        primary_operation = self._select_primary_operation(operations)
        # if (2<=operations.__len__()< 3):
        #     print(text)
        #     print(operations)
        #     print(primary_operation)
        #     print("---------")
        # if "explain" in operations and "replace" in operations:
        #     if re.search(r'^(?:объясни|расскажи|что означает|чем отличается)', text, re.IGNORECASE):
        #         primary_operation = "explain"
        #     else:
        #         primary_operation = "replace"
        
        # # 2. Если есть replace и assemble – replace важнее
        # if "replace" in operations and "assemble" in operations:
        #     primary_operation = "replace"
        
        # # 3. Если есть inventory и repair, но нет признаков поломки – inventory
        # if "inventory" in operations and "repair" in operations:
        #     if not re.search(r'(?:сломал|поврежд|утечк|отказал)', text, re.IGNORECASE):
        #         primary_operation = "inventory"
        
        # # 4. Если есть check и repair, но нет признаков поломки – check
        # if "check" in operations and "repair" in operations:
        #     if not re.search(r'(?:сломал|поврежд|утечк|отказал)', text, re.IGNORECASE):
        #         primary_operation = "check"
        
        # # 5. Если есть impact и repair – impact важнее
        # if "impact" in operations and "repair" in operations:
        #     primary_operation = "impact"
        
        # if "repair" in operations and "replace" in operations:
        #     if re.search(r'(?:сломал|поврежд|утечк|отказал)', text, re.IGNORECASE):
        #         primary_operation = "repair"
        #     else:
        #         # нет признаков поломки – replace важнее
        #         primary_operation = "replace"
        # -----------------------------------------------------
        # 2. Извлечение сущностей
        # -----------------------------------------------------

        item_type = self._safe_parse(
            self.item_type_parser.parse,
            text
        )
        
        item_types = self._safe_parse(self.item_type_parser.parse_multiple, text)
        if not item_types:
            item_types = []

        geometry = self._safe_parse(
            self.geometry_parser.parse,
            text
        )

        pressure = self._safe_parse(
            self.pressure_parser.parse,
            text
        )

        material = self._safe_parse(
            self.material_parser.parse,
            text
        )

        environment = self._safe_parse(
            self.environment_parser.parse,
            text
        )

        component_ids = self._safe_parse(
            self.component_parser.parse,
            text
        )

        unit_ids = self._safe_parse(
            self.unit_parser.parse,
            text
        )

        normative = self._safe_parse(
            self.normative_parser.parse,
            text
        )
        if material and isinstance(material, dict) and normative:
            material_standard = material.get("standard")
            normative_gost = normative.get("gost_tu") if isinstance(normative, dict) else None
            if material_standard and normative_gost and material_standard == normative_gost:
                material["standard"] = None

        # -----------------------------------------------------
        # 3. Контекст
        # -----------------------------------------------------

        context = self._extract_context(text)

        if context is None:
            context = {}

        if not isinstance(context, dict):
            context = {}

        # -----------------------------------------------------
        # 4. References
        # -----------------------------------------------------

        references = self._extract_references(
            text,
            component_ids,
            unit_ids
        )

        # -----------------------------------------------------
        # 5. Changes
        # -----------------------------------------------------

        changes = self._extract_changes(text)

        # -----------------------------------------------------
        # 6. Filters
        # -----------------------------------------------------

        filters = self._build_filters(
            geometry=geometry,
            pressure=pressure,
            material=material,
            environment=environment,
            item_type=item_type,
            item_types=item_types,
        )

        # -----------------------------------------------------
        # 7. Ambiguities
        # -----------------------------------------------------

        ambiguities = self._detect_ambiguities(
            text=text,
            geometry=geometry,
            pressure=pressure,
            material=material,
            operations=operations,
        )

        # -----------------------------------------------------
        # 8. ItemCards
        # -----------------------------------------------------

        # Основная карточка – только если один тип детали
        card = None
        cards = []
        
        if len(item_types) == 1:
            card = self._build_card(
                text=text,
                item_type=item_types[0],
                geometry=geometry,
                pressure=pressure,
                material=material,
                environment=environment,
                normative=normative,
            )
            if card:
                cards = [card]
        elif len(item_types) > 1:
            # Не создаём основную карточку при множественных типах
            # Но создаём отдельные карточки для каждого типа
            for it_type in item_types:
                type_card = self._build_card(
                    text=text,
                    item_type=it_type,
                    geometry=geometry,
                    pressure=pressure,
                    material=material,
                    environment=environment,
                    normative=normative,
                )
                if type_card:
                    cards.append(type_card)
        else:
            # Нет item_type – пробуем создать карточку без типа
            card = self._build_card(
                text=text,
                item_type=None,
                geometry=geometry,
                pressure=pressure,
                material=material,
                environment=environment,
                normative=normative,
            )
            if card:
                cards = [card]

        # -----------------------------------------------------
        # 9. Capabilities
        # -----------------------------------------------------

        required_capabilities = self._detect_capabilities(
            operations=operations,
            text=text,
            references=references,
            changes=changes,
        )

        # -----------------------------------------------------
        # 10. Confidence
        # -----------------------------------------------------

        confidence = self._calculate_confidence(
            text=text,
            operations=operations,
            card=card,
            ambiguities=ambiguities,
        )

        # -----------------------------------------------------
        # 11. Итог
        # -----------------------------------------------------
        
        parsed = ParsedQuery(
            original_query=text,
            operation=primary_operation,
            operations=operations,
            item_types=item_types,
            card=card,
            cards=cards,
            filters=filters,
            changes=changes,
            context=context,
            references=references,
            ambiguities=ambiguities,
            required_capabilities=required_capabilities,
            confidence=confidence,
        )
        # print(parsed.operation)
        return parsed
        
        
    def _get_missing_fields(self, card: Optional[ItemCard]) -> List[str]:
        """Определяет какие поля отсутствуют в карточке"""
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
                # DN не критичен для перехода
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

    # =========================================================
    # PRIMARY OPERATION
    # =========================================================

    def _select_primary_operation(self, operations: List[str]) -> str:
        # Если есть explain – он всегда главный (объяснение)
        if "explain" in operations:
            return "explain"
        
        # Если есть impact – он важнее repair
        if "impact" in operations and "repair" in operations:
            return "impact"
        
        priority = {
            "repair": 100,
            "replace": 95,
            "impact": 90,
            "plan": 80,
            "check": 75,
            "inventory": 70,
            "document": 50,
            "explain": 45,
            "search": 30,
            "assemble": 20,
            "calculate": 10,
        }
        return max(operations, key=lambda x: priority.get(x, 0))

    # =========================================================
    # SAFE PARSER
    # =========================================================

    @staticmethod
    def _safe_parse(func, text):
        try:
            result = func(text)
            return result
        except Exception:
            return None

    # =========================================================
    # REFERENCES
    # =========================================================

    def _extract_references(self, text: str, component_ids=None, unit_ids=None) -> List[str]:
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

    # =========================================================
    # CHANGES
    # =========================================================

    def _extract_changes(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        changes = {}

        # Среда
        if re.search(r"(?:перевод|переводят|сменить|смена|заменить).{0,50}(?:на|для)\s+h2s", text_lower):
            changes["medium"] = "H2S"

        if re.search(r"(?:перевод|переводят|сменить|смена).{0,50}(?:на|для)\s+co2", text_lower):
            changes["medium"] = "CO2"

        # Диаметр: "DN200 вместо DN150" -> from=150, to=200
        diameter_match = re.search(
            r"(?:dn|ду)\s*(\d+).{0,30}(?:вместо|на)\s+(?:dn|ду)?\s*(\d+)",
            text_lower,
        )
        if diameter_match:
            first = float(diameter_match.group(1))
            second = float(diameter_match.group(2))
            # from – то что было, to – то что ставим
            # Если первое число = новое, второе = старое
            # По умолчанию: первое = to, второе = from
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
# ---------------------------------------------------------
        # Класс прочности: "К52 вместо К48" -> from=К48, to=К52  (НОВОЕ)
        # ---------------------------------------------------------
        strength_match = re.search(
            r'(К\d+)\s+(?:вместо|на)\s+(К\d+)',
            text_lower,
        )
        if strength_match:
            changes["strength_to"] = strength_match.group(1).upper()
            changes["strength_from"] = strength_match.group(2).upper()

        # ---------------------------------------------------------
        # Класс прочности: "К52 вместо К48" (обратный порядок)
        # ---------------------------------------------------------
        strength_match_reverse = re.search(
            r'(?:вместо|на)\s+(К\d+)\s+(К\d+)',
            text_lower,
        )
        if strength_match_reverse:
            changes["strength_from"] = strength_match_reverse.group(1).upper()
            changes["strength_to"] = strength_match_reverse.group(2).upper()
        
        return changes

    def _extract_context(self, text: str) -> Dict[str, Any]:
        context = {}
        text_lower = text.lower()
        
        # ---------------------------------------------------------
        # 1. Количество штук
        # ---------------------------------------------------------
        quantity = None
        
        # Цифры + штуки
        qty_match = re.search(r'(\d+)\s*(?:штук|шт|ед|штуки|штука)', text_lower)
        if qty_match:
            quantity = int(qty_match.group(1))
        
        # Слова + штуки ("по две штуки")
        if quantity is None:
            num_words = {'одна':1,'один':1,'одно':1,'одну':1,'две':2,'два':2,'двух':2,
                        'три':3,'трёх':3,'четыре':4,'четырёх':4,'пять':5,'пяти':5,
                        'шесть':6,'шести':6,'семь':7,'семи':7,'восемь':8,'восьми':8,
                        'девять':9,'девяти':9,'десять':10,'десяти':10}
            match = re.search(r'по\s+(' + '|'.join(num_words.keys()) + r')\s+штук', text_lower)
            if match:
                quantity = num_words[match.group(1)]
        
        # Слова + деталь ("два отвода")
        if quantity is None:
            num_words = {'два':2,'две':2,'три':3,'четыре':4,'пять':5,'шесть':6,
                        'семь':7,'восемь':8,'девять':9,'десять':10}
            match = re.search(r'(' + '|'.join(num_words.keys()) + r')\s+(?:отвода|трубы|задвижки|перехода|заглушки|тройника)', text_lower)
            if match:
                quantity = num_words[match.group(1)]
        
        if quantity:
            context['quantity'] = quantity
            
        units_count = None
        
        # "трёх таких же участков" -> 3
        units_match = re.search(
            r'(' + '|'.join(['одн','дв','трёх','тр','четырёх','четыр','пяти','пят','шести','шест','семи','сем','восьми','вос','девяти','девят','десяти','десят']) + r')\s*(?:таких же\s*)?участков',
            text_lower
        )
        if units_match:
            units_words = {
                'одн':1,'дв':2,'трёх':3,'тр':3,'четырёх':4,'четыр':4,
                'пяти':5,'пят':5,'шести':6,'шест':6,'семи':7,'сем':7,
                'восьми':8,'вос':8,'девяти':9,'девят':9,'десяти':10,'десят':10
            }
            units_count = units_words.get(units_match.group(1))
        
        # "три участка"
        if units_count is None:
            units_match = re.search(r'(\d+)\s*(?:таких же\s*)?участков', text_lower)
            if units_match:
                units_count = int(units_match.group(1))
        
        if units_count:
            context['units_count'] = units_count
        # ---------------------------------------------------------
        # 2. Длина в метрах
        # ---------------------------------------------------------
        length_match = re.search(r'(\d+)\s*(?:м|метр|метров|метра)', text_lower)
        if length_match:
            context['length_meters'] = float(length_match.group(1))
        else:
            num_words = {
                'сто':100,'двести':200,'триста':300,'четыреста':400,'пятьсот':500,
                'шестьсот':600,'семьсот':700,'восемьсот':800,'девятьсот':900,
                'тысяча':1000,'один':1,'одну':1,'одна':1,'одно':1,'две':2,'два':2,
                'три':3,'четыре':4,'пять':5,'шесть':6,'семь':7,'восемь':8,'девять':9,
                'десять':10,'одиннадцать':11,'двенадцать':12,'тринадцать':13,
                'четырнадцать':14,'пятнадцать':15,'шестнадцать':16,'семнадцать':17,
                'восемнадцать':18,'девятнадцать':19,'двадцать':20,'тридцать':30,
                'сорок':40,'пятьдесят':50,'шестьдесят':60,'семьдесят':70,
                'восемьдесят':80,'девяносто':90
            }
            for word, num in num_words.items():
                if re.search(rf'{word}\s*(?:м|метр|метров|метра)', text_lower):
                    context['length_meters'] = float(num)
                    break
        
        # ---------------------------------------------------------
        # 3. Время
        # ---------------------------------------------------------
        if re.search(r'следующ(?:ая|ей|ую)?\s*недел[ея]', text_lower):
            context['timeframe'] = 'next_week'
        elif re.search(r'сегодня|сейчас', text_lower):
            context['timeframe'] = 'immediate'
        
        # ---------------------------------------------------------
        # 4. Срочность
        # ---------------------------------------------------------
        if re.search(r'срочн|важн|критич', text_lower):
            context['urgency'] = 'high'
        
        return context
    
    # =========================================================
    # FILTERS
    # =========================================================

    def _build_filters(self, geometry=None, pressure=None, material=None, environment=None, item_type=None, item_types=None) -> Dict[str, Any]:
        filters = {}

        if item_types and len(item_types) > 1:
            pass
        elif item_type:
            if isinstance(item_type, str):
                filters["item_type"] = item_type
            elif isinstance(item_type, dict):
                filters.update(item_type)

        # Добавляем параметры
        if geometry and isinstance(geometry, dict):
            # Для переходов и тройников используем d1 и d2, а не wall_thickness
            if geometry.get('d1') and geometry.get('d2'):
                filters["d1"] = geometry["d1"]
                filters["d2"] = geometry["d2"]
            if geometry.get('dn'):
                filters["dn"] = geometry["dn"]
            if geometry.get('wall_thickness') and not geometry.get('d1'):
                filters["wall_thickness"] = geometry["wall_thickness"]
            if geometry.get('angle'):
                filters["angle"] = geometry["angle"]

        # Добавляем остальное
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

        garbage_values = ["ТУ ДЛЯ", "ГОСТЫ", "ТУ для", "ГОСТы", "ТУ", "ГОСТ"]
        for key in list(filters.keys()):
            if filters[key] in garbage_values:
                del filters[key]

        return filters

    # =========================================================
    # CARD
    # =========================================================

    def _build_card(self, text: str, item_type=None, geometry=None, pressure=None,
                    material=None, environment=None, normative=None) -> Optional[ItemCard]:
        if re.search(r'\b(?:участок|схема|состоит|участке)\b', text, re.IGNORECASE):
            # Проверяем, есть ли явные параметры детали
            has_params = False
            
            # Проверяем геометрию
            if geometry and isinstance(geometry, dict):
                if any([geometry.get('dn'), geometry.get('d1'), geometry.get('wall_thickness')]):
                    has_params = True
            
            # Проверяем давление
            if pressure and isinstance(pressure, dict):
                if pressure.get('pn'):
                    has_params = True
            
            # Проверяем материал
            if material and isinstance(material, dict):
                if material.get('steel_grade'):
                    has_params = True
            
            # Если нет параметров – не создаём карточку
            if not has_params:
                return None

        has_data = any(x is not None for x in [item_type, geometry, pressure, material, environment, normative])
        if not has_data:
            return None

        geometry_obj = self._to_model(geometry, Geometry)
        pressure_obj = self._to_model(pressure, Pressure)
        material_obj = self._to_model(material, Material)
        environment_obj = self._to_model(environment, Environment)
        
        normative_obj = None
        if normative and isinstance(normative, dict):
            gost_tu = normative.get("gost_tu")
            if gost_tu and re.match(r'^(?:ГОСТ|ТУ)\s+[\d\-]+', gost_tu.upper()):
                normative_obj = self._to_model(normative, Normative)

        if isinstance(item_type, dict):
            base_type = item_type.get("item_type")
            subtype = item_type.get("subtype")            
        else:
            base_type = item_type
            subtype = self.item_type_parser.parse_subtype(text)
            
        temp_card = ItemCard(
            card_id=None,
            item_type=base_type,
            subtype=subtype,
            designation=self._build_designation(geometry_obj, pressure_obj, material_obj, environment_obj),
            name=self._build_name(base_type, geometry_obj, pressure_obj),
            geometry=geometry_obj,
            pressure=pressure_obj,
            material=material_obj,
            environment=environment_obj,
            normative=normative_obj,
            extraction=Extraction(confidence=0.0, method="user_query", missing_fields=[]),
            sources=[Source(type="user_query", fragment=text)],
        )
        if temp_card.material and temp_card.material.steel_grade:
            # Проверяем изменения в тексте
            changes = self._extract_changes(text)
            if changes.get('material_from'):
                temp_card.material.steel_grade = changes['material_from']
                # Перестраиваем designation с новым материалом
                temp_card.designation = self._build_designation(
                    geometry_obj, pressure_obj, temp_card.material, environment_obj
                )
        
        missing = self._get_missing_fields(temp_card)
        temp_card.extraction.missing_fields = missing
        
        return temp_card

    # =========================================================
    # MODEL CONVERSION
    # =========================================================

    @staticmethod
    def _to_model(value, model_class):
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

    # =========================================================
    # DESIGNATION
    # =========================================================

    @staticmethod
    def _build_designation(geometry, pressure, material, environment) -> Optional[str]:
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
        if pressure and pressure.pn:
            parts.append(f"PN{pressure.pn:g}")
        if material and material.steel_grade:
            parts.append(material.steel_grade)
        if material and material.strength_class:
            parts.append(material.strength_class)
        if environment and environment.medium:
            parts.append(environment.medium)
        return " ".join(parts) if parts else None

    # =========================================================
    # NAME
    # =========================================================

    @staticmethod
    def _build_name(item_type, geometry, pressure) -> Optional[str]:
        if not item_type:
            return None
        name = str(item_type)
        if geometry:
            if geometry.angle:
                name += f" {geometry.angle:g}°"
            if geometry.dn:
                name += f" DN{geometry.dn:g}"
        if pressure and pressure.pn:
            name += f" PN{pressure.pn:g}"
        return name

    # =========================================================
    # AMBIGUITIES
    # =========================================================

    def _detect_ambiguities(self, text: str, geometry=None, pressure=None, material=None, operations=None) -> List[str]:
        ambiguities = []

        try:
            result = self.ambiguity_detector.detect(text)
            if result:
                if isinstance(result, list):
                    ambiguities.extend(result)
                elif isinstance(result, dict):
                    ambiguities.extend(result.get("ambiguities", []))
        except Exception:
            pass

        dns = re.findall(r"\b(?:dn|ду)\s*(\d+(?:[.,]\d+)?)", text.lower())
        if len(set(dns)) > 1:
            ambiguities.append("В запросе указано несколько значений DN")

        pns = re.findall(r"\bpn\s*(\d+(?:[.,]\d+)?)", text.lower())
        if len(set(pns)) > 1:
            ambiguities.append("В запросе указано несколько значений PN")

        return list(dict.fromkeys(ambiguities))

    # =========================================================
    # CAPABILITIES
    # =========================================================

    def _detect_capabilities(self, operations: List[str], text: str, references: List[str], changes: Dict[str, Any]) -> List[str]:
        capabilities = set()
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
        
        # Только если есть реальный ГОСТ/ТУ с номером
        if re.search(r"\b(?:ГОСТ|ТУ)\s+[\d\-]+", text.upper()):
            capabilities.add("knowledge_search")
        
        # Только если есть слово "паспорт" или "документ"
        if re.search(r"\b(?:паспорт|документ|ЛНД)\b", text.lower()):
            capabilities.add("document_search")

        return sorted(capabilities)

    # =========================================================
    # CONFIDENCE
    # =========================================================

    def _calculate_confidence(self, text: str, operations: List[str], card: Optional[ItemCard], ambiguities: List[str]) -> float:
        score = 1.0
        
        # ---------------------------------------------------------
        # 1. Операции
        # ---------------------------------------------------------
        if not operations or operations == ["unknown"]:
            score -= 0.3
        
        # ---------------------------------------------------------
        # 2. Карточка
        # ---------------------------------------------------------
        if card is None:
            score -= 0.25
        else:
            # Штраф за отсутствующие поля в карточке
            missing = card.extraction.missing_fields if card.extraction else []
            if missing:
                # Штраф зависит от количества пропущенных полей
                # Но не все поля одинаково важны
                penalty = 0.0
                
                # Критические поля (без них карточка бесполезна)
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
                
                # Но не больше 0.5 за пропущенные поля
                score -= min(penalty, 0.5)
        
        # ---------------------------------------------------------
        # 3. Амбигвити
        # ---------------------------------------------------------
        if ambiguities:
            score -= min(0.15 * len(ambiguities), 0.3)
        
        # ---------------------------------------------------------
        # 4. Длина запроса
        # ---------------------------------------------------------
        word_count = len(text.split())
        if word_count < 3:
            score -= 0.15
        elif word_count < 5:
            score -= 0.05
        
        # ---------------------------------------------------------
        # 5. Бонус за references (уточняет запрос)
        # ---------------------------------------------------------
        if re.search(r'COMP-|UNIT-|KSM-|MTR-', text):
            score += 0.05
        
        # ---------------------------------------------------------
        # 6. Неизвестные операции
        # ---------------------------------------------------------
        known_ops = set(self.operation_parser.OPERATION_PRIORITY.keys())
        unknown = [op for op in operations if op not in known_ops]
        if unknown:
            score -= 0.1 * len(unknown)
        
        # ---------------------------------------------------------
        # 7. Ограничения
        # ---------------------------------------------------------
        return max(0.0, min(1.0, score))
