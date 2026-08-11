# query_parser/parsers/material_parser.py

import re
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field
from functools import lru_cache

from ..dictionaries import STEEL_GRADES, STRENGTH_CLASSES
from ..normalizers.normalizers import normalize_steel, normalize_strength_class
from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class MaterialPattern:
    """Паттерн для извлечения материала"""
    pattern: str
    field: str
    priority: int = 0
    description: str = ""
    normalize_func: Optional[callable] = None


class MaterialParser:
    """
    Парсер материала из запроса.
    Поддерживает:
    - Марки стали (09Г2С, 20, 45, 12Х18Н10Т и др.)
    - Классы прочности (К48, К50, К52, К54, К56)
    - ГОСТ/ТУ на материал
    - Замены материалов ("стали 20 на 09Г2С")
    - Зарубежные марки (AISI 316L, ASTM A105)
    """
    
    # Расширенный список марок стали
    STEEL_GRADES_EXTENDED = {
        # Российские марки
        "09Г2С": "09Г2С",
        "09ГСФ": "09ГСФ",
        "13ХФА": "13ХФА",
        "12Х18Н10Т": "12Х18Н10Т",
        "10ХСНД": "10ХСНД",
        "12ГС": "12ГС",
        "17Г1С": "17Г1С",
        "20": "20",
        "45": "45",
        "40Х": "40Х",
        "30ХГСА": "30ХГСА",
        "08Х18Н10Т": "08Х18Н10Т",
        "03Х17Н14М3": "03Х17Н14М3",
        "06ХН28МДТ": "06ХН28МДТ",
        "15Х5М": "15Х5М",
        "12Х1МФ": "12Х1МФ",
        "15Х1М1Ф": "15Х1М1Ф",
        "20ХМФЛ": "20ХМФЛ",
        "20ГЛ": "20ГЛ",
        "35ГЛ": "35ГЛ",
        "45ГЛ": "45ГЛ",
        "08Г2С": "08Г2С",
        "10Г2": "10Г2",
        "14Г2": "14Г2",
        "16Г2АФ": "16Г2АФ",
        
        # Зарубежные марки
        "AISI 316L": "AISI 316L",
        "AISI 304": "AISI 304",
        "AISI 321": "AISI 321",
        "ASTM A105": "ASTM A105",
        "ASTM A106": "ASTM A106",
        "ASTM A234": "ASTM A234",
        "ASTM A420": "ASTM A420",
        "API 5L X42": "API 5L X42",
        "API 5L X52": "API 5L X52",
        "API 5L X60": "API 5L X60",
        "API 5L X65": "API 5L X65",
        "API 5L X70": "API 5L X70",
    }
    
    # Паттерны для извлечения марок стали
    STEEL_PATTERNS = [
        # Составные марки (приоритетные)
        (r'\b(09Г2С|09ГСФ|13ХФА|12Х18Н10Т|10ХСНД|12ГС|17Г1С|40Х|30ХГСА|08Х18Н10Т|03Х17Н14М3|06ХН28МДТ|15Х5М|12Х1МФ|15Х1М1Ф|20ХМФЛ|20ГЛ|35ГЛ|45ГЛ|08Г2С|10Г2|14Г2|16Г2АФ)\b',
         'steel_grade', 100, "составная марка"),
        
        # Простые марки (сталь 20, сталь 45)
        (r'(?:стал[иь]|марка|из)\s+(\d+)', 'steel_grade', 90, "сталь X"),
        (r'\b(\d+)\s*(?:сталь|марка)', 'steel_grade', 85, "X сталь"),
        
        # Зарубежные марки
        (r'\b(AISI\s+316L|AISI\s+304|AISI\s+321|ASTM\s+A105|ASTM\s+A106|ASTM\s+A234|ASTM\s+A420)\b',
         'steel_grade', 95, "зарубежная марка"),
        (r'\b(API\s+5L\s+X42|API\s+5L\s+X52|API\s+5L\s+X60|API\s+5L\s+X65|API\s+5L\s+X70)\b',
         'steel_grade', 95, "API марка"),
        
        # Сталь в составе
        (r'(?:из\s+)?стали?\s+([0-9а-яёa-z]+)', 'steel_grade', 80, "из стали X"),
    ]
    
    # Паттерны для извлечения классов прочности
    STRENGTH_PATTERNS = [
        (r'\b(К48|К50|К52|К54|К56|К60|К65|К70)\b', 'strength_class', 100, "класс прочности"),
        (r'(?:класс\s+прочности|класс)\s+(К\d+)', 'strength_class', 90, "класс прочности X"),
        (r'(?:прочность|категория)\s+(К\d+)', 'strength_class', 80, "прочность X"),
    ]
    
    # Паттерны для извлечения ГОСТ/ТУ на материал
    STANDARD_PATTERNS = [
        (r'\b(?:ГОСТ|ТУ)\s+[\d\-]+(?:\.[\d\-]+)?', 'standard', 100, "ГОСТ/ТУ"),
        (r'\b(?:стандарт|по\s+)\s*(ГОСТ|ТУ)\s+[\d\-]+', 'standard', 90, "стандарт ГОСТ/ТУ"),
    ]
    
    # Паттерны для замен материала
    REPLACEMENT_PATTERNS = [
        (r'(?:из\s+)?стали?\s+([0-9а-яёa-z]+)\s+(?:на|в|вместо)\s+([0-9а-яёa-z]+)',
         ['steel_grade_from', 'steel_grade_to'], 100, "замена стали X на Y"),
        (r'(?:замена|заменить)\s+стали?\s+([0-9а-яёa-z]+)\s+(?:на|вместо)\s+([0-9а-яёa-z]+)',
         ['steel_grade_from', 'steel_grade_to'], 90, "замена стали X на Y"),
    ]
    
    # Паттерны для контекстного поиска материала
    CONTEXT_PATTERNS = {
        "steel_grade": [
            (r'\bуглеродист(?:ая|ой|ую|ые|ых)', "20"),
            (r'\bлегирован(?:ая|ой|ую|ые|ых)', "09Г2С"),
            (r'\bнержавеющ(?:ая|ой|ую|ые|ых)', "12Х18Н10Т"),
            (r'\bжаропрочн(?:ая|ой|ую|ые|ых)', "15Х5М"),
            (r'\bхладостойк(?:ая|ой|ую|ые|ых)', "09Г2С"),
        ],
        "strength_class": [
            (r'\bвысокопрочн(?:ая|ой|ую|ые|ых)', "К52"),
            (r'\bповышенной\s+прочности', "К52"),
            (r'\bособовысокопрочн(?:ая|ой|ую|ые|ых)', "К60"),
        ],
    }
    
    # Стоп-слова для фильтрации
    STOP_WORDS = {"УЧАСТКЕ", "СКЛАДЕ", "НЕТ", "ЕСТЬ", "ТРУБА", "ОТВОД", "ЗАДВИЖКА"}
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=80)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Основной метод парсинга материала
        """
        if not text or not text.strip():
            return self._empty_result()
        
        # Проверка кеша
        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        result = self._parse_impl(text)
        
        # Сохраняем в кеш
        self._cache[cache_key] = result.copy()
        return result

    def _parse_impl(self, text: str) -> Dict[str, Any]:
        """
        Реализация парсинга без кеширования
        """
        result = self._empty_result()
        normalized = text.upper()
        
        # 1. Проверяем замену материала
        replacement = self._extract_replacement(normalized)
        if replacement:
            # Возвращаем исходную сталь (from)
            result["steel_grade"] = replacement.get("steel_grade_from")
            result["strength_class"] = replacement.get("strength_class_from")
            
            # Сохраняем информацию о замене
            result["_replacement"] = replacement
            return result
        
        # 2. Извлечение марки стали
        self._apply_steel_patterns(normalized, result)
        
        # 3. Извлечение класса прочности
        self._apply_strength_patterns(normalized, result)
        
        # 4. Извлечение ГОСТ/ТУ
        self._apply_standard_patterns(normalized, result)
        
        # 5. Контекстный поиск (если не найдено)
        if result.get("steel_grade") is None:
            self._apply_context_patterns(normalized, result)
        
        # 6. Fuzzy-поиск (для опечаток)
        if result.get("steel_grade") is None:
            self._apply_fuzzy_search(normalized, result)
        
        # 7. Нормализация
        if result.get("steel_grade"):
            result["steel_grade"] = normalize_steel(result["steel_grade"])
        if result.get("strength_class"):
            result["strength_class"] = normalize_strength_class(result["strength_class"])
        
        # 8. Очистка от мусора
        if result.get("steel_grade") in self.STOP_WORDS:
            result["steel_grade"] = None
        
        return result

    # =========================================================
    # ПРИМЕНЕНИЕ ПАТТЕРНОВ
    # =========================================================

    def _apply_steel_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для марок стали
        """
        for pattern, field, priority, _ in self.STEEL_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Проверяем, что это не стоп-слово
                if value.upper() not in self.STOP_WORDS:
                    result[field] = value
                    break

    def _apply_strength_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для классов прочности
        """
        for pattern, field, priority, _ in self.STRENGTH_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[field] = match.group(1)
                break

    def _apply_standard_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для ГОСТ/ТУ
        """
        for pattern, field, priority, _ in self.STANDARD_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[field] = match.group(0)
                break

    def _apply_context_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение контекстных паттернов
        """
        # Поиск по контексту для стали
        for pattern, default_value in self.CONTEXT_PATTERNS.get("steel_grade", []):
            if re.search(pattern, text, re.IGNORECASE):
                result["steel_grade"] = default_value
                break
        
        # Поиск по контексту для класса прочности
        if result.get("strength_class") is None:
            for pattern, default_value in self.CONTEXT_PATTERNS.get("strength_class", []):
                if re.search(pattern, text, re.IGNORECASE):
                    result["strength_class"] = default_value
                    break

    def _apply_fuzzy_search(self, text: str, result: Dict[str, Any]) -> None:
        """
        Fuzzy-поиск марок стали
        """
        words = re.findall(r"[а-яёa-z0-9]+", text.lower())
        
        # Собираем все марки стали для fuzzy-поиска
        all_grades = list(self.STEEL_GRADES_EXTENDED.keys())
        
        for word in words:
            if len(word) < 3:
                continue
            
            # Проверяем через fuzzy-матчер
            matches = self.fuzzy_matcher.match(word, all_grades)
            for matched_grade, score in matches:
                if score >= 80:  # Порог для fuzzy
                    result["steel_grade"] = self.STEEL_GRADES_EXTENDED[matched_grade]
                    return

    # =========================================================
    # ИЗВЛЕЧЕНИЕ ЗАМЕН
    # =========================================================

    def _extract_replacement(self, text: str) -> Optional[Dict[str, str]]:
        """
        Извлечение информации о замене материала
        """
        for pattern, fields, priority, _ in self.REPLACEMENT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                from_value = match.group(1).upper()
                to_value = match.group(2).upper()
                
                # Проверяем, что это не стоп-слова
                if from_value not in self.STOP_WORDS and to_value not in self.STOP_WORDS:
                    return {
                        "steel_grade_from": from_value,
                        "steel_grade_to": to_value,
                    }
        
        return None

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _empty_result(self) -> Dict[str, Any]:
        """
        Пустой результат
        """
        return {
            "steel_grade": None,
            "strength_class": None,
            "standard": None,
        }

    def is_valid_steel_grade(self, steel_grade: str) -> bool:
        """
        Проверка валидности марки стали
        """
        return steel_grade.upper() in self.STEEL_GRADES_EXTENDED

    def is_valid_strength_class(self, strength_class: str) -> bool:
        """
        Проверка валидности класса прочности
        """
        return strength_class.upper() in STRENGTH_CLASSES

    def get_all_steel_grades(self) -> List[str]:
        """
        Получить все марки стали
        """
        return list(self.STEEL_GRADES_EXTENDED.keys())

    def get_all_strength_classes(self) -> List[str]:
        """
        Получить все классы прочности
        """
        return STRENGTH_CLASSES.copy()

    def get_steel_grades_by_type(self, steel_type: str) -> List[str]:
        """
        Получить марки стали по типу
        """
        types = {
            "carbon": ["20", "45", "40Х"],
            "low_alloy": ["09Г2С", "09ГСФ", "13ХФА", "12ГС", "17Г1С"],
            "stainless": ["12Х18Н10Т", "08Х18Н10Т", "03Х17Н14М3"],
            "heat_resistant": ["15Х5М", "12Х1МФ", "15Х1М1Ф"],
            "foreign": ["AISI 316L", "AISI 304", "ASTM A105", "API 5L X52"],
        }
        return types.get(steel_type, [])

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша
        """
        self._cache.clear()
