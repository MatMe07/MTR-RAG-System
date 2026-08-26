# query_parser/parsers/normative_parser.py

import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from functools import lru_cache

from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class NormativePattern:
    """Паттерн для извлечения нормативной документации"""
    pattern: str
    field: str
    priority: int = 0
    description: str = ""
    normalize_func: Optional[callable] = None


class NormativeParser:
    """
    Парсер нормативной документации из запроса.
    Поддерживает:
    - ГОСТ (государственные стандарты)
    - ТУ (технические условия)
    - ЛНД (локальные нормативные документы)
    - СТО (стандарты организаций)
    - Различные форматы номеров
    - Паспорта и сертификаты
    """
    
    # Паттерны для извлечения ГОСТ
    GOST_PATTERNS = [
        # Полный формат: ГОСТ 12345-67
        (r'\bГОСТ\s+(\d+)\s*[-—–]\s*(\d+)(?:\s*[-—–]\s*(\d+))?\b',
         'gost_tu', 100, "ГОСТ XXXX-XX"),
        
        # ГОСТ с точкой: ГОСТ 12345-67-89
        (r'\bГОСТ\s+(\d+)\s*[-—–]\s*(\d+)\s*[-—–]\s*(\d+)\b',
         'gost_tu', 95, "ГОСТ XXXX-XX-XX"),
        
        # ГОСТ без дефиса: ГОСТ 1234567
        (r'\bГОСТ\s+(\d+)\b',
         'gost_tu', 85, "ГОСТ XXXXXXX"),
        
        # ГОСТ с годом в скобках: ГОСТ 12345 (2005)
        (r'\bГОСТ\s+(\d+)\s*[\(（]\s*(\d+)\s*[\)）]',
         'gost_tu', 90, "ГОСТ XXXX (год)"),
        
        # ГОСТ с указанием "по ГОСТ": по ГОСТ 12345-67
        (r'(?:по|согласно|согл|в соотв)\s+ГОСТ\s+(\d+)\s*[-—–]\s*(\d+)',
         'gost_tu', 90, "по ГОСТ XXXX-XX"),
    ]
    
    # Паттерны для извлечения ТУ
    TU_PATTERNS = [
        # ✅ Исправлен паттерн для ТУ с точкой: ТУ 1234.567-89
        (r'\bТУ\s+(\d+)\.(\d+)\s*[-—–]\s*(\d+)\b',
         'gost_tu', 100, "ТУ XXXX.XXX-XX"),
        
        # Полный формат: ТУ 1234-567-89
        (r'\bТУ\s+(\d+)\s*[-—–]\s*(\d+)\s*[-—–]\s*(\d+)\b',
         'gost_tu', 95, "ТУ XXXX-XXX-XX"),
        
        # ТУ с дефисом: ТУ 1234-567
        (r'\bТУ\s+(\d+)\s*[-—–]\s*(\d+)\b',
         'gost_tu', 90, "ТУ XXXX-XXX"),
        
        # ТУ простой: ТУ 1234567
        (r'\bТУ\s+(\d+)\b',
         'gost_tu', 80, "ТУ XXXXXXX"),
    ]
    
    # Паттерны для извлечения СТО (стандарты организаций)
    STO_PATTERNS = [
        (r'\bСТО\s+(\d+)\s*[-—–]\s*(\d+)\b',
         'gost_tu', 85, "СТО XXXX-XX"),
        (r'\bСТО\s+(\d+)\b',
         'gost_tu', 75, "СТО XXXXX"),
    ]
    
    # ✅ Исправлены паттерны для ЛНД - сохраняем префикс
    LND_PATTERNS = [
        (r'\bЛНД\s+[\d\.\-]+', 'lnd_sections', 100, "ЛНД"),
        (r'\b(?:раздел|пункт|параграф)\s+[\d\.\-]+', 'lnd_sections', 80, "раздел X"),
        (r'\b(?:глава|часть)\s+[\d\.\-]+', 'lnd_sections', 75, "глава X"),
    ]
    
    # ✅ Паттерны для паспортов и сертификатов
    PASSPORT_PATTERNS = [
        (r'\bпаспорт\s+[\d\-]+(?:\.[\d\-]+)?', 'passport', 100, "паспорт"),
        (r'\bсертификат\s+[\d\-]+(?:\.[\d\-]+)?', 'certificate', 100, "сертификат"),
        (r'\b(?:свидетельство|серт)\s+[\d\-]+', 'certificate', 90, "свидетельство"),
    ]
    
    # Паттерны для контекстного поиска
    CONTEXT_PATTERNS = {
        "gost_tu": [
            (r'\bстандарт\b', "ГОСТ"),
            (r'\bнормативн(?:ый|ая|ое)\b', "ГОСТ"),
            (r'\bтехническ(?:ий|ая|ое)\s+услови[ея]', "ТУ"),
        ],
        "lnd_sections": [
            (r'\bлнд\b', "ЛНД"),
            (r'\bнормативн(?:ый|ая|ое)\s+документ', "ЛНД"),
        ],
    }
    
    # Валидные префиксы нормативных документов
    VALID_PREFIXES = ["ГОСТ", "ТУ", "СТО", "ЛНД", "ОСТ", "РД", "СНиП", "СП"]
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=75)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Основной метод парсинга нормативной документации
        """
        if not text or not text.strip():
            return None
        
        # Проверка кеша
        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        result = self._parse_impl(text)
        
        # Сохраняем в кеш
        if result:
            self._cache[cache_key] = result.copy()
        return result

    def _parse_impl(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Реализация парсинга без кеширования
        """
        result = {
            "gost_tu": None,
            "lnd_sections": [],
            "passport": None,
            "certificate": None,
            "sto": None,
            "other_normatives": [],
        }
        
        text_upper = text.upper()
        
        # 1. Извлечение ГОСТ
        self._apply_gost_patterns(text_upper, result)
        
        # 2. Извлечение ТУ
        if result.get("gost_tu") is None:
            self._apply_tu_patterns(text_upper, result)
        
        # 3. Извлечение СТО
        if result.get("gost_tu") is None:
            self._apply_sto_patterns(text_upper, result)
        
        # 4. Извлечение ЛНД
        self._apply_lnd_patterns(text, result)
        
        # 5. Извлечение паспортов и сертификатов
        self._apply_passport_patterns(text, result)
        
        # 6. Контекстный поиск
        if result.get("gost_tu") is None:
            self._apply_context_patterns(text_upper, result)
        
        # 7. Если ничего не найдено - возвращаем None
        if not self._has_any_data(result):
            return None
        
        # 8. Нормализация
        result = self._normalize_result(result)
        
        return result

    # =========================================================
    # ПРИМЕНЕНИЕ ПАТТЕРНОВ
    # =========================================================

    def _apply_gost_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для ГОСТ"""
        for pattern, field, priority, _ in self.GOST_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3 and groups[2]:
                    value = f"ГОСТ {groups[0]}-{groups[1]}-{groups[2]}"
                elif len(groups) >= 2:
                    value = f"ГОСТ {groups[0]}-{groups[1]}"
                else:
                    value = f"ГОСТ {groups[0]}"
                result[field] = value
                break

    def _apply_tu_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для ТУ"""
        for pattern, field, priority, _ in self.TU_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                # ✅ Проверяем, был ли это паттерн с точкой
                if '.' in match.group(0):
                    # Сохраняем оригинальный формат с точкой
                    value = match.group(0).strip()
                elif len(groups) == 3:
                    value = f"ТУ {groups[0]}-{groups[1]}-{groups[2]}"
                elif len(groups) == 2:
                    value = f"ТУ {groups[0]}-{groups[1]}"
                else:
                    value = f"ТУ {groups[0]}"
                result[field] = value
                break

    def _apply_sto_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для СТО"""
        for pattern, field, priority, _ in self.STO_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    value = f"СТО {groups[0]}-{groups[1]}"
                else:
                    value = f"СТО {groups[0]}"
                result["sto"] = value
                result[field] = value
                break

    def _apply_lnd_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для ЛНД"""
        for pattern, field, priority, _ in self.LND_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, str):
                        # ✅ Сохраняем оригинальный текст с префиксом
                        if 'ЛНД' in text.upper() and 'раздел' in match:
                            result[field].append(f"ЛНД {match}")
                        else:
                            result[field].append(match)
                    elif isinstance(match, tuple):
                        result[field].append(match[0])
                break

    def _apply_passport_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для паспортов и сертификатов"""
        for pattern, field, priority, _ in self.PASSPORT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(0).strip()
                if field == 'passport':
                    result['passport'] = value
                elif field == 'certificate':
                    result['certificate'] = value

    def _apply_context_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение контекстных паттернов"""
        for pattern, default_value in self.CONTEXT_PATTERNS.get("gost_tu", []):
            if re.search(pattern, text, re.IGNORECASE):
                result["other_normatives"].append(default_value)
                break

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _has_any_data(self, result: Dict[str, Any]) -> bool:
        """Проверка, есть ли какие-либо данные в результате"""
        return any([
            result.get("gost_tu") is not None,
            result.get("lnd_sections"),
            result.get("passport") is not None,
            result.get("certificate") is not None,
            result.get("sto") is not None,
            result.get("other_normatives"),
        ])

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация результата"""
        # Очищаем пустые списки
        if not result.get("lnd_sections"):
            result["lnd_sections"] = []
        
        # Удаляем дубликаты в lnd_sections
        if result.get("lnd_sections"):
            result["lnd_sections"] = list(dict.fromkeys(result["lnd_sections"]))
        
        # Удаляем дубликаты в other_normatives
        if result.get("other_normatives"):
            result["other_normatives"] = list(dict.fromkeys(result["other_normatives"]))
        
        return result

    def is_valid_gost_tu(self, gost_tu: str) -> bool:
        """Проверка валидности ГОСТ/ТУ"""
        patterns = [
            r'^ГОСТ\s+\d+[-–—]\d+$',
            r'^ГОСТ\s+\d+[-–—]\d+[-–—]\d+$',
            r'^ГОСТ\s+\d+$',
            r'^ТУ\s+\d+\.\d+[-–—]\d+$',
            r'^ТУ\s+\d+[-–—]\d+[-–—]\d+$',
            r'^ТУ\s+\d+[-–—]\d+$',
            r'^ТУ\s+\d+$',
            r'^СТО\s+\d+[-–—]\d+$',
        ]
        return any(re.match(pattern, gost_tu) for pattern in patterns)

    def extract_gost_number(self, gost_tu: str) -> Optional[Dict[str, str]]:
        """Извлечение номера ГОСТ/ТУ в структурированном виде"""
        patterns = [
            (r'^(ГОСТ|ТУ|СТО)\s+(\d+)[-–—](\d+)[-–—](\d+)$', 3),
            (r'^(ГОСТ|ТУ|СТО)\s+(\d+)[-–—](\d+)$', 2),
            (r'^(ГОСТ|ТУ|СТО)\s+(\d+)$', 1),
        ]
        
        for pattern, count in patterns:
            match = re.match(pattern, gost_tu)
            if match:
                result = {
                    "prefix": match.group(1),
                    "number": match.group(2),
                }
                if count >= 2:
                    result["year"] = match.group(3)
                if count >= 3:
                    result["additional"] = match.group(4)
                return result
        return None

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """Очистка кеша"""
        self._cache.clear()
