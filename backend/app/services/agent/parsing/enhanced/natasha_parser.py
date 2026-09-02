# query_parser/enhanced/natasha_parser.py

import re
from typing import Dict, Any, List, Optional, Set
from functools import lru_cache

from mawo_natasha import (
    Segmenter,
    MorphVocab,
    NewsMorphTagger,
    NewsNERTagger,
    Doc
)

from ..dictionaries import ITEM_TYPE_ALIASES, OPERATION_ALIASES
from ..utils.fuzzy_utils import FuzzyMatcher


class NatashaParser:
    """
    NLP-парсер на основе библиотеки Natasha.
    Извлекает сущности и параметры из текста с использованием NER и морфологии.
    """
    
    # Типы деталей для NER (используются для фильтрации)
    ITEM_TYPE_KEYWORDS = {"отвод", "задвижка", "заглушка", "переход", "тройник", "труба", "кран"}
    
    # Паттерны для извлечения subtype (централизовано)
    SUBTYPE_PATTERNS = [
        # Задвижки
        (r'клинов(?:ая|ой|ую)', "клиновая"),
        (r'параллельн(?:ая|ой|ую)', "параллельная"),
        (r'шиберн(?:ая|ой|ую)', "шиберная"),
        # Краны
        (r'шаров(?:ой|ая|ую)', "шаровой"),
        (r'пробков(?:ый|ая|ую)', "пробковый"),
        # Переходы
        (r'концентрическ(?:ий|ая|ое)', "концентрический"),
        (r'эксцентрическ(?:ий|ая|ое)', "эксцентрический"),
        # Отводы
        (r'крутоизогнут(?:ый|ая|ое)', "крутоизогнутый"),
        (r'гнут(?:ый|ая|ое)', "гнутый"),
        (r'штампованн(?:ый|ая|ое)', "штампованный"),
        # Трубы
        (r'сварн(?:ой|ая|ое|ую|ой)', "сварная"),
        (r'бесшовн(?:ый|ая|ое|ую|ой)', "бесшовная"),
        (r'электросварн(?:ой|ая|ое|ую|ой)', "электросварная"),
        # Тройники
        (r'равнопроходн(?:ый|ая|ое)', "равнопроходный"),
        (r'переходн(?:ой|ая|ое)', "переходной"),
    ]
    
    # ✅ Обновлены паттерны для извлечения операций
    OPERATION_PATTERNS = {
        "replace": [
            r'(?:подбер|найд|замен|аналог|вмест)',
            r'(?:замени|замену|замены)',
            r'(?:подбери|подобрать)',  # ✅ Добавлено
        ],
        "repair": [
            r'(?:ремонт|сломал|поврежд|утечк|отказал|почин)',
        ],
        "check": [
            r'(?:провер|хват|достаточ|подходит|соответств)',
        ],
        "explain": [
            r'(?:объясн|расскаж|означа|что значит|чем отличается)',
        ],
        "inventory": [
            r'(?:склад|налич|остат|закуп|пополн|сколько|запас)',
        ],
        "plan": [
            r'(?:план|состав|обслужив|подготов|перечисл)',
        ],
        "impact": [
            r'(?:изменится|последств|влияние|риск)',
            r'(?:прид[её]тся|затрон|соседн|заменят)',
            r'(?:какие соседние|что проверить)',
        ],
        "document": [
            r'(?:документ|паспорт|гост|ту|сертификат)',
        ],
        "search": [
            r'(?:найди|покажи|найти|показать|выбери)',
            # r'(?:подбери|подобрать)',  # ❌ Удаляем отсюда
        ],
        "assemble": [
            r'(?:собер|комплект|сборка)',
        ],
        "calculate": [
            r'(?:посчитай|подсчитай|рассчитай|расчет)',
        ],
    }
    
    def __init__(self):
        # Инициализация MAWO (Natasha) компонентов
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.ner_tagger = NewsNERTagger()
        self.morph_tagger = NewsMorphTagger()
        
        # Fuzzy matcher для улучшенного поиска
        self.fuzzy_matcher = FuzzyMatcher(threshold=75)
        
        # Кеш для результатов парсинга
        self._cache: Dict[str, Dict[str, Any]] = {}

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Основной метод парсинга с кешированием
        """
        # Кеширование результатов для одинаковых текстов
        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        # Основной парсинг
        result = self._parse_impl(text)
        
        # Сохраняем в кеш
        self._cache[cache_key] = result.copy()
        
        return result

    def _parse_impl(self, text: str) -> Dict[str, Any]:
        """
        Реализация парсинга без кеширования
        """
        # Создаём документ для Natasha
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_ner(self.ner_tagger)
        self._apply_morph_markup(doc)
        
        # Инициализация результата
        result = {
            "item_types": [],
            "subtype": None,
            "operations": [],
            "parameters": {
                "dn": None,
                "wall_thickness": None,
                "pressure": None,
                "steel_grade": None,
                "medium": None,
                "angle": None,
                "climate_version": None,
            },
            "component_ids": [],
            "unit_ids": [],
            "references": [],
            "ambiguities": [],
            "filters": {},
            "stock_filters": {},
            "changes": {},
            "unit_id": None,
            "component_id": None,
            "medium": None,
        }
        
        # 1. Извлечение операций
        result["operations"] = self._extract_operations(text)
        
        # 2. Извлечение типов деталей (через NER)
        result["item_types"] = self._extract_item_types(doc, text)
        
        # 3. Извлечение subtype
        result["subtype"] = self._extract_subtype(text)
        
        # 4. Извлечение параметров
        self._extract_parameters(text, result)
        
        # 5. Извлечение ID компонентов и участков
        result["component_ids"], result["unit_ids"] = self._extract_ids(text)
        
        # 6. Извлечение ссылок (ГОСТ, ТУ)
        result["references"] = self._extract_references(text)
        
        # 7. Извлечение неоднозначностей
        result["ambiguities"] = self._extract_ambiguities(text, result)
        
        return result

    def _apply_morph_markup(self, doc: Doc) -> None:
        """
        Морфологическая разметка токенов документа.

        Полноценный таггер SlovNet имеет метод .map (использует его Doc.tag_morph),
        но fallback-реализация mawo_slovnet (LocalSlovNetImplementation, когда
        модели недоступны) такого метода не имеет — поддерживает только __call__.
        """
        tagger = self.morph_tagger
        if hasattr(tagger, "map"):
            doc.tag_morph(tagger)
            return

        for sent in doc.sents:
            words = [token.text for token in sent.tokens]
            if not words:
                continue
            markup = tagger(words)
            sources = getattr(markup, "tokens", [])
            for token, source in zip(sent.tokens, sources):
                token.pos = getattr(source, "pos", None)
                token.feats = getattr(source, "feats", {})

    # =========================================================
    # ИЗВЛЕЧЕНИЕ ОПЕРАЦИЙ
    # =========================================================

    def _extract_operations(self, text: str) -> List[str]:
        """
        Извлечение операций через регулярные выражения
        """
        operations: Set[str] = set()
        text_lower = text.lower()
        
        # Проверяем по паттернам
        for op, patterns in self.OPERATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    operations.add(op)
                    break
        
        # Проверяем через алиасы (из dictionaries.py)
        for alias, op in OPERATION_ALIASES.items():
            if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", text_lower):
                operations.add(op)
        
        # ✅ Дополнительная проверка для impact через ключевые фразы
        if re.search(r'(?:какие соседние|прид[её]тся заменить|затронет|соседние детали)', text_lower):
            operations.add("impact")
        
        return sorted(operations)

    # =========================================================
    # ИЗВЛЕЧЕНИЕ ТИПОВ ДЕТАЛЕЙ
    # =========================================================

    def _extract_item_types(self, doc: Doc, text: str) -> List[str]:
        """
        Извлечение типов деталей через NER и регулярки
        """
        item_types: Set[str] = set()
        text_lower = text.lower()
        
        # 1. Через NER (ORGANIZATION часто содержит коды деталей)
        for span in doc.spans:
            if span.type == "ORG":
                span_lower = span.text.lower()
                for keyword in self.ITEM_TYPE_KEYWORDS:
                    if keyword in span_lower:
                        item_types.add(keyword)
                        break
        
        # 2. Через точное совпадение с алиасами
        for alias, normalized in ITEM_TYPE_ALIASES.items():
            if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", text_lower):
                item_types.add(normalized)
        
        # 3. Через fuzzy-поиск (для опечаток)
        words = re.findall(r"[а-яёa-z]+", text_lower)
        for word in words:
            if len(word) < 4:
                continue
            for alias, normalized in ITEM_TYPE_ALIASES.items():
                if len(alias) < 4:
                    continue
                if self.fuzzy_matcher.match(word, [alias]):
                    item_types.add(normalized)
                    break
        
        return list(item_types)

    # =========================================================
    # ИЗВЛЕЧЕНИЕ SUBTYPE
    # =========================================================

    def _extract_subtype(self, text: str) -> Optional[str]:
        """
        Извлечение подтипа из текста
        """
        text_lower = text.lower()
        
        for pattern, subtype in self.SUBTYPE_PATTERNS:
            if re.search(pattern, text_lower):
                return subtype
        
        return None

    # =========================================================
    # ИЗВЛЕЧЕНИЕ ПАРАМЕТРОВ
    # =========================================================

    def _extract_parameters(self, text: str, result: Dict) -> None:
        """
        Извлечение всех параметров из текста
        """
        params = result["parameters"]
        text_lower = text.lower()
        
        # DN
        dn_patterns = [
            r'DN\s*[:]?\s*(\d+)',
            r'Ду\s*[:]?\s*(\d+)',
            r'диаметр(?:ом)?\s*[:]?\s*(\d+)',
            r'\bна\s+(\d+)\b(?=.*(?:отвод|труба|задвижка|заглушка|переход|тройник))',
        ]
        for pattern in dn_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                params["dn"] = float(match.group(1))
                break
        
        # Толщина стенки
        wall_patterns = [
            r'стенк[аиой]\s*[:]?\s*(\d+(?:[.,]\d+)?)',
            r'стенкой\s*(\d+(?:[.,]\d+)?)',
            r'на\s+(\d+)\s*(?:мм|мл|миллиметр)',
        ]
        for pattern in wall_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                params["wall_thickness"] = float(match.group(1).replace(',', '.'))
                break
        
        # Давление (PN)
        pressure_patterns = [
            r'PN\s*[:]?\s*(\d+)',
            r'Ру\s*[:]?\s*(\d+)',
            r'давлени[ея]\s*[:]?\s*(\d+(?:[.,]\d+)?)',
        ]
        for pattern in pressure_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = float(match.group(1).replace(',', '.'))
                params["pressure"] = val / 10.0 if val >= 10 else val
                break
        
        # Угол
        angle_patterns = [
            r'\b(30|45|60|90)\s*°',
            r'угол(?:ом)?\s*[:]?\s*(\d+)',
        ]
        for pattern in angle_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                params["angle"] = float(match.group(1))
                break
        
        # Материал (марка стали)
        steel_patterns = [
            r'(?:стал[иь])\s+([0-9а-яёa-z]+)',
            r'\b(09Г2С|09ГСФ|13ХФА|12Х18Н10Т|10ХСНД|12ГС|17Г1С)\b',
        ]
        for pattern in steel_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                params["steel_grade"] = match.group(1).upper()
                break
        
        # Среда (приоритет: нефть > газ > вода > H2S > CO2)
        medium_priority = ["нефть", "природный газ", "вода", "H2S", "CO2"]
        for medium in medium_priority:
            if re.search(rf'\b{medium}\b', text, re.IGNORECASE):
                params["medium"] = medium
                break
        
        # Климатика (исполнение)
        climate_patterns = [
            (r'\bУХЛ1?\b', "УХЛ"),
            (r'\bХЛ1?\b', "ХЛ"),
            (r'\bТ\b', "Т"),
            (r'\bУ\b(?!\s+(?:меня|нас|него|нее|них|вас|тебя|себя))', "У"),
        ]
        for pattern, climate in climate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                params["climate_version"] = climate
                break

    # =========================================================
    # ИЗВЛЕЧЕНИЕ ID (COMPONENT и UNIT)
    # =========================================================

    def _extract_ids(self, text: str) -> tuple[List[str], List[str]]:
        """
        Извлечение ID компонентов и участков
        """
        component_ids = re.findall(r'\bCOMP[-_][A-Z0-9-]+\b', text, re.IGNORECASE)
        unit_ids = re.findall(r'\bUNIT[-_][A-Z0-9-]+\b', text, re.IGNORECASE)
        
        component_ids = [cid.upper() for cid in component_ids]
        unit_ids = [uid.upper() for uid in unit_ids]
        
        return component_ids, unit_ids

    # =========================================================
    # ИЗВЛЕЧЕНИЕ ССЫЛОК (ГОСТ, ТУ)
    # =========================================================

    def _extract_references(self, text: str) -> List[str]:
        """
        Извлечение ссылок на нормативную документацию
        """
        references = []
        text_upper = text.upper()
        
        gost_matches = re.findall(r'ГОСТ\s+[\d\-]+(?:\.[\d\-]+)?', text_upper)
        references.extend(gost_matches)
        
        tu_matches = re.findall(r'ТУ\s+[\d\-]+(?:\.[\d\-]+)?', text_upper)
        references.extend(tu_matches)
        
        return list(dict.fromkeys(references))

    # =========================================================
    # ИЗВЛЕЧЕНИЕ НЕОДНОЗНАЧНОСТЕЙ
    # =========================================================

    def _extract_ambiguities(self, text: str, result: Dict) -> List[str]:
        """
        Извлечение неоднозначностей
        """
        ambiguities = []
        text_lower = text.lower()
        
        dns = re.findall(r'\b(?:dn|ду)\s*[:]?\s*(\d+)', text_lower)
        if len(set(dns)) > 1:
            ambiguities.append("Обнаружено несколько значений DN")
        
        angles = re.findall(r'\b(30|45|60|90)\s*°?', text_lower)
        if len(set(angles)) > 1:
            ambiguities.append("Обнаружено несколько значений угла")
        
        if not result.get("item_types"):
            ambiguities.append("Не удалось определить тип детали")
        
        return ambiguities

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша результатов
        """
        self._cache.clear()
