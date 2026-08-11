# hybrid_parser_v2.py
# Гибридный парсер: FastRegex + Spacy (опционально)
# Использует схемы из schemas.py
import json
import re
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime

from app.schemas import (
    ParsedQuery,
    ItemCard,
    Geometry,
    Pressure,
    Material,
    Environment,
    Coating,
    Normative,
    Extraction,
    Source,
)


# ============================================================
# 1. FAST REGEX PARSER (основной)
# ============================================================

class FastRegexParser:
    """Быстрый парсер на регулярных выражениях"""
    
    # Словари
    ITEM_TYPES = {
        "труб": "труба",
        "отвод": "отвод",
        "задвижк": "задвижка",
        "заглушк": "заглушка",
        "переход": "переход",
        "тройник": "тройник",
        "кран": "кран",
    }
    
    SUBTYPES = {
        "свар": "сварная",
        "бесшовн": "бесшовная",
        "электросвар": "электросварная",
        "клинов": "клиновая",
        "параллельн": "параллельная",
        "шиберн": "шиберная",
        "шаров": "шаровой",
        "пробков": "пробковый",
        "концентрическ": "концентрический",
        "эксцентрическ": "эксцентрический",
        "крутоизогнут": "крутоизогнутый",
        "гнут": "гнутый",
        "штампован": "штампованный",
    }
    
    OPERATIONS = {
        "repair": ["сломал", "поврежд", "утечк", "ремонт", "почин"],
        "replace": ["замен", "аналог", "вмест", "подбер", "подобрат"],
        "plan": ["план", "обслужив", "комплект", "состав"],
        "check": ["провер", "хват", "достаточ", "подход"],
        "explain": ["объясн", "расскаж", "означа", "отлича"],
        "inventory": ["скольк", "налич", "остат", "закуп", "пополн"],
        "search": ["найд", "покаж"],
        "impact": ["изменит", "последств", "влиян"],
        "document": ["паспорт", "документ", "гост", "ту"],
        "assemble": ["собер", "сборк"],
        "calculate": ["посчита", "рассчита", "расчет"],
    }
    
    MEDIUMS = {
        "h2s": "H2S",
        "сероводород": "H2S",
        "co2": "CO2",
        "углекислый": "CO2",
        "нефт": "нефть",
        "газ": "газ",
        "вод": "вода",
    }
    
    CLIMATE = {
        "север": "ХЛ",
        "хл": "ХЛ",
        "ухл": "УХЛ",
        "у": "У",
        "т": "Т",
    }
    
    STEEL_GRADES = {
        "09г2с": "09Г2С",
        "09гсф": "09ГСФ",
        "13хфа": "13ХФА",
        "12х18н10т": "12Х18Н10Т",
        "10хснд": "10ХСНД",
        "12гс": "12ГС",
        "17г1с": "17Г1С",
        "20": "20",
    }
    
    STRENGTH_CLASSES = ["К48", "К50", "К52", "К54", "К56"]
    
    def parse(self, text: str) -> ParsedQuery:
        """Основной метод парсинга"""
        text_clean = text.strip()
        
        # 1. Парсим базовые сущности
        operations = self._parse_operations(text_clean)
        item_types = self._parse_item_types(text_clean)
        subtype = self._parse_subtype(text_clean)
        geometry = self._parse_geometry(text_clean)
        environment = self._parse_environment(text_clean)
        material = self._parse_material(text_clean)
        pressure = self._parse_pressure(text_clean)
        context = self._parse_context(text_clean)
        references = self._parse_references(text_clean)
        changes = self._parse_changes(text_clean)
        ambiguities = self._parse_ambiguities(text_clean)
        
        # 2. Собираем карточку
        card = self._build_card(
            text=text_clean,
            item_types=item_types,
            subtype=subtype,
            geometry=geometry,
            environment=environment,
            material=material,
            pressure=pressure,
        )
        
        # 3. Собираем фильтры
        filters = self._build_filters(geometry, material, environment, item_types)
        
        # 4. Определяем основную операцию
        primary_op = operations[0] if operations else "search"
        
        # 5. Считаем confidence
        confidence = self._calculate_confidence(
            text_clean, operations, card, ambiguities
        )
        
        # 6. Capabilities
        capabilities = self._detect_capabilities(operations, context)
        
        return ParsedQuery(
            original_query=text_clean,
            operation=primary_op,
            operations=operations,
            item_types=item_types,
            card=card,
            cards=[card] if card else [],
            filters=filters,
            changes=changes,
            context=context,
            references=references,
            ambiguities=ambiguities,
            required_capabilities=capabilities,
            confidence=confidence
        )
    
    # =========================================================
    # ПАРСЕРЫ
    # =========================================================
    
    def _parse_operations(self, text: str) -> List[str]:
        """Извлечение операций"""
        text_lower = text.lower()
        found = set()
        
        for op, keywords in self.OPERATIONS.items():
            for kw in keywords:
                if kw in text_lower:
                    found.add(op)
                    break
        
        # Спец. случаи
        if "подбер" in text_lower and re.search(r'\d+[хx]\d+|стал', text_lower):
            found.add("search")
        
        return sorted(found, key=lambda x: self._op_priority(x), reverse=True)
    
    def _op_priority(self, op: str) -> int:
        priorities = {
            "repair": 100, "replace": 95, "impact": 90, "plan": 80,
            "check": 75, "inventory": 70, "document": 50, "explain": 45,
            "search": 30, "assemble": 20, "calculate": 10
        }
        return priorities.get(op, 0)
    
    def _parse_item_types(self, text: str) -> List[str]:
        """Извлечение типов деталей"""
        text_lower = text.lower()
        found = set()
        
        for alias, item_type in self.ITEM_TYPES.items():
            if alias in text_lower:
                found.add(item_type)
        
        return list(found)
    
    def _parse_subtype(self, text: str) -> Optional[str]:
        """Извлечение подтипа"""
        text_lower = text.lower()
        
        for alias, subtype in self.SUBTYPES.items():
            if alias in text_lower:
                return subtype
        
        return None
    
    def _parse_geometry(self, text: str) -> Optional[Geometry]:
        """Извлечение геометрии"""
        result = {}
        text_lower = text.lower()
        
        # 1. Парсим "159х10" или "159x10"
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*[хx]\s*(\d+(?:[.,]\d+)?)', text)
        if match:
            result["dn"] = float(match.group(1).replace(',', '.'))
            result["wall_thickness"] = float(match.group(2).replace(',', '.'))
            return Geometry(**result)
        
        # 2. Парсим DN/Ду
        match = re.search(r'(?:DN|Ду|диаметр(?:ом)?)\s*(\d+)', text, re.IGNORECASE)
        if match:
            result["dn"] = float(match.group(1))
        
        # 3. Парсим толщину стенки
        match = re.search(r'(?:стенк[аиой]|стенкой)\s*(\d+)', text, re.IGNORECASE)
        if match:
            result["wall_thickness"] = float(match.group(1))
        
        # 4. Парсим угол
        match = re.search(r'(\d+)[°\s]*град', text, re.IGNORECASE)
        if match:
            result["angle"] = float(match.group(1))
        
        # 5. Парсим d1 и d2 для переходов
        match = re.search(r'(\d+)[хx]\s*(\d+)\s*(?:мм)?', text)
        if match:
            result["d1"] = float(match.group(1))
            result["d2"] = float(match.group(2))
        
        # Если ничего не нашли
        if not result:
            return None
        
        return Geometry(**result)
    
    def _parse_environment(self, text: str) -> Optional[Environment]:
        """Извлечение среды и климата"""
        result = {}
        text_lower = text.lower()
        
        # 1. Среда
        mediums = []
        h2s_confirmed = False
        co2_confirmed = False
        
        for alias, medium in self.MEDIUMS.items():
            if alias in text_lower:
                mediums.append(medium)
                if medium == "H2S":
                    h2s_confirmed = True
                elif medium == "CO2":
                    co2_confirmed = True
        
        # Приоритет: H2S > CO2 > нефть > газ > вода
        priority = {"H2S": 5, "CO2": 4, "нефть": 3, "газ": 2, "вода": 1}
        if mediums:
            result["medium"] = max(mediums, key=lambda x: priority.get(x, 0))
            result["h2s_confirmed"] = h2s_confirmed
            result["co2_confirmed"] = co2_confirmed
        
        # 2. Климат
        for alias, climate in self.CLIMATE.items():
            if alias in text_lower:
                result["climate_version"] = climate
                break
        
        # 3. Температура
        match = re.search(r'(?:температур[аы]|град|до\s*|от\s*)([-+]?\d+(?:[.,]\d+)?)', text_lower)
        if match:
            result["temperature_min_c"] = float(match.group(1).replace(',', '.'))
        
        # Если ничего не нашли
        if not result:
            return None
        
        return Environment(**result)
    
    def _parse_material(self, text: str) -> Optional[Material]:
        """Извлечение материала"""
        text_lower = text.lower()
        result = {}
        
        # 1. Сталь
        for alias, grade in self.STEEL_GRADES.items():
            if alias in text_lower:
                result["steel_grade"] = grade
                break
        
        # 2. Класс прочности
        for cls in self.STRENGTH_CLASSES:
            if cls.lower() in text_lower:
                result["strength_class"] = cls
                break
        
        if not result:
            return None
        
        return Material(**result)
    
    def _parse_pressure(self, text: str) -> Optional[Pressure]:
        """Извлечение давления"""
        text_upper = text.upper()
        
        # PN40 → 4.0 МПа
        match = re.search(r'(?:PN|Ру|РУ)\s*(\d+)', text_upper)
        if match:
            val = float(match.group(1))
            pn = val / 10.0 if val >= 10 else val
            return Pressure(pn=pn)
        
        # Просто число > 10
        match = re.search(r'давлени[ея]\s*(\d+)', text_upper)
        if match:
            val = float(match.group(1))
            pn = val / 10.0 if val >= 10 else val
            return Pressure(pn=pn)
        
        return None
    
    def _parse_context(self, text: str) -> Dict[str, Any]:
        """Извлечение контекстной информации"""
        context = {}
        text_lower = text.lower()
        
        # 1. Условия "под что-то"
        match = re.search(r'под\s+([А-Яа-яёЁ\s]+?)(?:\s|$|,)', text_lower)
        if match:
            condition = match.group(1).strip()
            if "север" in condition:
                context["climate"] = "ХЛ"
            if "свар" in condition:
                context["fabrication"] = "сварная"
            if any(m in condition for m in ["h2s", "сероводород"]):
                context["medium_h2s"] = True
        
        # 2. Количество
        match = re.search(r'(\d+)\s*(?:штук|шт|ед|штуки)', text_lower)
        if match:
            context["quantity"] = int(match.group(1))
        
        # 3. Длина
        match = re.search(r'(\d+)\s*(?:м|метр|метров|метра)', text_lower)
        if match:
            context["length_meters"] = float(match.group(1))
        
        # 4. Срочность
        if re.search(r'срочн|важн|критич', text_lower):
            context["urgency"] = "high"
        
        return context
    
    def _parse_references(self, text: str) -> List[str]:
        """Извлечение ссылок на коды"""
        text_upper = text.upper()
        references = []
        
        patterns = [
            r'\bCOMP[-_][A-Z0-9-]+\b',
            r'\bUNIT[-_][A-Z0-9-]+\b',
            r'\bKSM[-_][A-Z0-9-]+\b',
            r'\bMTR[-_][A-Z0-9-]+\b',
        ]
        
        for pattern in patterns:
            references.extend(re.findall(pattern, text_upper))
        
        return list(dict.fromkeys(references))
    
    def _parse_changes(self, text: str) -> Dict[str, Any]:
        """Извлечение изменений"""
        changes = {}
        text_lower = text.lower()
        
        # Диаметр: "DN200 вместо DN150"
        match = re.search(r'(?:DN|Ду)\s*(\d+).{0,30}(?:вместо|на)\s+(?:DN|Ду)?\s*(\d+)', text_lower)
        if match:
            changes["dn_to"] = float(match.group(1))
            changes["dn_from"] = float(match.group(2))
        
        # Материал: "стали 20 на 09Г2С"
        match = re.search(r'стали?\s+([0-9а-яёa-z]+)\s+(?:на|в|вместо)\s+([0-9а-яёa-z]+)', text_lower, re.IGNORECASE)
        if match:
            changes["material_from"] = match.group(1).upper()
            changes["material_to"] = match.group(2).upper()
        
        return changes
    
    def _parse_ambiguities(self, text: str) -> List[str]:
        """Обнаружение неоднозначностей"""
        ambiguities = []
        text_lower = text.lower()
        
        # Несколько DN
        dns = re.findall(r'(?:DN|Ду)\s*(\d+)', text_lower)
        if len(set(dns)) > 1:
            ambiguities.append("Указано несколько значений DN")
        
        # Несколько материалов
        materials = re.findall(r'\b(09Г2С|09ГСФ|13ХФА|12Х18Н10Т|10ХСНД)\b', text_lower)
        if len(set(materials)) > 1:
            ambiguities.append("Указано несколько марок стали")
        
        return ambiguities
    
    def _detect_capabilities(self, operations: List[str], context: Dict) -> List[str]:
        """Определение необходимых возможностей"""
        caps = set()
        
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
        
        for op in operations:
            if op in mapping:
                caps.add(mapping[op])
        
        if context.get("climate"):
            caps.add("climate_analysis")
        if context.get("fabrication"):
            caps.add("fabrication_check")
        
        return sorted(caps)
    
    def _calculate_confidence(self, text: str, operations: List[str], card: Optional[ItemCard], ambiguities: List[str]) -> float:
        """Расчёт уверенности"""
        score = 1.0
        
        # Операции
        if not operations or operations == ["unknown"]:
            score -= 0.3
        
        # Карточка
        if card is None:
            score -= 0.25
        else:
            missing = self._get_missing_fields(card)
            if missing:
                penalty = 0.0
                critical = ["item_type", "dn"]
                for field in critical:
                    if field in missing:
                        penalty += 0.15
                important = ["wall_thickness", "steel_grade", "medium"]
                for field in important:
                    if field in missing:
                        penalty += 0.05
                score -= min(penalty, 0.5)
        
        # Амбигвити
        if ambiguities:
            score -= min(0.15 * len(ambiguities), 0.3)
        
        # Длина запроса
        word_count = len(text.split())
        if word_count < 3:
            score -= 0.15
        elif word_count < 5:
            score -= 0.05
        
        return max(0.0, min(1.0, score))
    
    def _get_missing_fields(self, card: ItemCard) -> List[str]:
        """Определяет какие поля отсутствуют в карточке"""
        missing = []
        
        if card.item_type is None:
            missing.append("item_type")
        
        if card.geometry:
            if card.geometry.dn is None:
                missing.append("dn")
            if card.geometry.wall_thickness is None:
                missing.append("wall_thickness")
        else:
            missing.append("geometry")
        
        if card.pressure is None or card.pressure.pn is None:
            missing.append("pressure")
        
        if card.material is None or card.material.steel_grade is None:
            missing.append("material")
        
        if card.environment is None or card.environment.medium is None:
            missing.append("environment")
        
        return missing
    
    def _build_card(
        self,
        text: str,
        item_types: List[str],
        subtype: Optional[str],
        geometry: Optional[Geometry],
        environment: Optional[Environment],
        material: Optional[Material],
        pressure: Optional[Pressure],
    ) -> Optional[ItemCard]:
        """Сборка карточки"""
        has_data = any([
            item_types,
            geometry,
            environment,
            material,
            pressure,
            subtype,
        ])
        
        if not has_data:
            return None
        
        item_type = item_types[0] if item_types else None
        
        # Строим designation
        designation_parts = []
        if geometry:
            if geometry.dn:
                designation_parts.append(f"DN{geometry.dn:g}")
            if geometry.wall_thickness:
                designation_parts.append(f"δ{geometry.wall_thickness:g}")
        if material and material.steel_grade:
            designation_parts.append(material.steel_grade)
        if environment and environment.medium:
            designation_parts.append(environment.medium)
        
        designation = " ".join(designation_parts) if designation_parts else None
        
        # Строим name
        name_parts = []
        if item_type:
            name_parts.append(item_type)
        if geometry and geometry.dn:
            name_parts.append(f"DN{geometry.dn:g}")
        if geometry and geometry.wall_thickness:
            name_parts.append(f"δ{geometry.wall_thickness:g}")
        name = " ".join(name_parts) if name_parts else None
        
        # Extraction
        extraction = Extraction(
            confidence=0.0,
            method="user_query",
            missing_fields=[]
        )
        
        # Source
        source = Source(
            type="user_query",
            fragment=text
        )
        
        card = ItemCard(
            card_id=None,
            mtr_code=None,
            ksm_code=None,
            item_type=item_type,
            subtype=subtype,
            designation=designation,
            name=name,
            geometry=geometry,
            pressure=pressure,
            material=material,
            environment=environment,
            coating=None,
            normative=None,
            extraction=extraction,
            sources=[source]
        )
        
        # Обновляем missing_fields
        extraction.missing_fields = self._get_missing_fields(card)
        
        return card
    
    def _build_filters(
        self,
        geometry: Optional[Geometry],
        material: Optional[Material],
        environment: Optional[Environment],
        item_types: List[str],
    ) -> Dict[str, Any]:
        """Сборка фильтров"""
        filters = {}
        
        if item_types:
            filters["item_type"] = item_types[0]
        
        if geometry:
            if geometry.dn:
                filters["dn"] = geometry.dn
            if geometry.wall_thickness:
                filters["wall_thickness"] = geometry.wall_thickness
            if geometry.angle:
                filters["angle"] = geometry.angle
            if geometry.d1 and geometry.d2:
                filters["d1"] = geometry.d1
                filters["d2"] = geometry.d2
        
        if material:
            if material.steel_grade:
                filters["steel_grade"] = material.steel_grade
            if material.strength_class:
                filters["strength_class"] = material.strength_class
        
        if environment:
            if environment.medium:
                filters["medium"] = environment.medium
            if environment.climate_version:
                filters["climate"] = environment.climate_version
        
        return filters


# ============================================================
# 2. SPACY PARSER (опционально, для сложных случаев)
# ============================================================

class SpacyParser:
    """Парсер на основе SpaCy для сложных конструкций"""
    
    def __init__(self):
        self.nlp = None
        self._init_spacy()
    
    def _init_spacy(self):
        try:
            import spacy
            from spacy.matcher import Matcher
            
            # Загружаем модель
            try:
                self.nlp = spacy.load("ru_core_news_sm")
            except:
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "ru_core_news_sm"])
                self.nlp = spacy.load("ru_core_news_sm")
            
            # Создаём матчер
            self.matcher = Matcher(self.nlp.vocab)
            
            # Паттерн для размеров: 159х10
            size_pattern = [
                {"LIKE_NUM": True},
                {"TEXT": {"IN": ["х", "x", "Х", "X"]}},
                {"LIKE_NUM": True}
            ]
            self.matcher.add("SIZE", [size_pattern])
            
            # Паттерн для среды: "для нефти с H2S"
            medium_pattern = [
                {"LOWER": "для"},
                {"POS": "NOUN"},
                {"LOWER": {"IN": ["с", "со"]}},
                {"TEXT": {"REGEX": r"(?i)^(h2s|co2|сероводород|углекислый)$"}}
            ]
            self.matcher.add("MEDIUM", [medium_pattern])
            
            # Паттерн для климата: "под Север"
            climate_pattern = [
                {"LOWER": "под"},
                {"TEXT": {"REGEX": r"(?i)^(север|севера|хл|ухл)$"}}
            ]
            self.matcher.add("CLIMATE", [climate_pattern])
            
        except Exception as e:
            print(f"Spacy не загружен: {e}")
            self.nlp = None
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Парсинг с помощью SpaCy"""
        if self.nlp is None:
            return {}
        
        doc = self.nlp(text)
        result = {
            "subtype": None,
            "mediums": [],
            "climate": None,
            "fabrication": None,
        }
        
        # 1. Матчинг паттернов
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            match_name = self.nlp.vocab.strings[match_id]
            
            if match_name == "SIZE":
                # Размеры уже распаршены regex
                pass
            elif match_name == "MEDIUM":
                # Извлекаем среду
                for token in span:
                    if token.text.upper() in ["H2S", "CO2"]:
                        result["mediums"].append(token.text.upper())
                    elif "сероводород" in token.text.lower():
                        result["mediums"].append("H2S")
                    elif "углекислый" in token.text.lower():
                        result["mediums"].append("CO2")
            elif match_name == "CLIMATE":
                for token in span:
                    if token.text.lower() in ["север", "севера"]:
                        result["climate"] = "ХЛ"
                    elif token.text.lower() in ["хл"]:
                        result["climate"] = "ХЛ"
                    elif token.text.lower() in ["ухл"]:
                        result["climate"] = "УХЛ"
        
        # 2. Морфологический анализ для извлечения subtype
        for token in doc:
            if token.lemma_ in ["сварка", "сварной", "сварить"]:
                result["fabrication"] = "сварная"
            elif token.lemma_ in ["бесшовный"]:
                result["subtype"] = "бесшовная"
        
        # 3. NER для извлечения организаций/продуктов
        for ent in doc.ents:
            if ent.label_ == "ORG" and any(c in ent.text.upper() for c in ["COMP", "UNIT", "KSM", "MTR"]):
                result["reference"] = ent.text
        
        return result


# ============================================================
# 3. ГИБРИДНЫЙ ПАРСЕР
# ============================================================

class HybridParserV2:
    """Гибридный парсер: FastRegex + Spacy"""
    
    def __init__(self, use_spacy: bool = True):
        self.fast_parser = FastRegexParser()
        self.spacy_parser = SpacyParser() if use_spacy else None
        self.use_spacy = use_spacy
    
    def parse(self, text: str) -> ParsedQuery:
        """Основной метод парсинга"""
        # 1. Быстрый проход
        result = self.fast_parser.parse(text)
        
        # 2. Если уверенность низкая или есть сложные конструкции
        if self.use_spacy and self._needs_spacy(text, result):
            spacy_data = self.spacy_parser.parse(text)
            if spacy_data:
                result = self._merge_spacy(result, spacy_data)
        
        return result
    
    def _needs_spacy(self, text: str, result: ParsedQuery) -> bool:
        """Определяем, нужен ли Spacy"""
        # Если уверенность низкая
        if result.confidence < 0.7:
            return True
        
        # Если есть конструкции с предлогами (под, для, с)
        if re.search(r'\b(под|для|с|со)\s+[А-Яа-яёЁ]', text):
            return True
        
        # Если есть неоднозначности
        if result.ambiguities:
            return True
        
        return False
    
    def _merge_spacy(self, result: ParsedQuery, spacy_data: Dict) -> ParsedQuery:
        """Объединение результатов"""
        card = result.card
        
        if card is None:
            card = ItemCard(
                card_id=None,
                mtr_code=None,
                ksm_code=None,
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
                sources=[]
            )
        
        # 1. Subtype
        if spacy_data.get("subtype") and card.subtype is None:
            card.subtype = spacy_data["subtype"]
        
        # 2. Fabrication (добавляем в контекст и subtype)
        if spacy_data.get("fabrication"):
            result.context["fabrication"] = spacy_data["fabrication"]
            if card.subtype is None:
                card.subtype = spacy_data["fabrication"]
        
        # 3. Климат
        if spacy_data.get("climate"):
            if card.environment is None:
                card.environment = Environment()
            card.environment.climate_version = spacy_data["climate"]
            result.context["climate"] = spacy_data["climate"]
        
        # 4. Среды (если несколько)
        if spacy_data.get("mediums"):
            if card.environment is None:
                card.environment = Environment()
            
            # Берём первую
            card.environment.medium = spacy_data["mediums"][0]
            if "H2S" in spacy_data["mediums"]:
                card.environment.h2s_confirmed = True
            if "CO2" in spacy_data["mediums"]:
                card.environment.co2_confirmed = True
            
            # Обновляем фильтры
            if result.filters:
                result.filters["medium"] = card.environment.medium
        
        # 5. References
        if spacy_data.get("reference"):
            if result.references is None:
                result.references = []
            result.references.append(spacy_data["reference"])
        
        # Обновляем карточку
        result.card = card
        
        # Если карточки нет в списке, добавляем
        if card not in result.cards:
            result.cards.append(card)
        
        # Обновляем extraction
        if card.extraction:
            card.extraction.method = "hybrid"
            card.extraction.missing_fields = self.fast_parser._get_missing_fields(card)
        
        # Пересчёт уверенности (добавляем бонус)
        if spacy_data:
            result.confidence = min(result.confidence + 0.05, 1.0)
        
        return result



def test_parser():
    """Тестирование парсера"""
    parser = HybridParserV2(use_spacy=True)
    
    questions = [
        "Найди заглушку 426 на 12 из стали 09ГСФ",
        "найди отвод 90 426 на 10 для H2S",
        "Найди замину задвижке DN150 PN40 для участка с H2S, исходной задвижки на складе нет?",
        "Какой аналог отвода 90 426 на 10 подойдёт для H2S, покажи сначала то, что есть на складе?",
        "У меня сломался отвод 90 426 на 10 на участке с H2S, предложи план замены и список деталей для ремонта?",
        "Нужна замена бесшовной трубы 108 на 6 из стали 20 на участке с H2S, подбери варианты и скажи, что проверить?",
    ]
    
    results = []

    for i, query in enumerate(questions, start=1):
        try:
            # if i != 22: continue
            result = parser.parse(query)
            # results.append(result)
            
            results.append({
                "id": i,
                "query": query,
                "operation": result.operation,
                "operations": result.operations,
                "confidence": result.confidence,
                "card": result.card.model_dump() if result.card else None,
                "cards": [c.model_dump() for c in result.cards] if result.cards else [],
                "filters": result.filters,
                "changes": result.changes,
                "context": result.context,
                "references": result.references,
                "ambiguities": result.ambiguities,
                "required_capabilities": result.required_capabilities,
                "error": None
            })
        
        except Exception as e:
            results.append({
                "id": i,
                "query": query,
                "operation": None,
                "confidence": 0.0,
                "card": None,
                "cards": [],
                "filters": {},
                "changes": {},
                "context": {},
                "references": [],
                "ambiguities": [],
                "required_capabilities": [],
                "error": str(e)
            })

    print(json.dumps(results, ensure_ascii=False, indent=2))
    

if __name__ == "__main__":
    test_parser()
