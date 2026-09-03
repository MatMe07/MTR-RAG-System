# query_parser/parsers/pressure_parser.py

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from functools import lru_cache

from ..normalizers.normalizers import normalize_decimal
from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class PressurePattern:
    """Паттерн для извлечения параметров давления"""
    pattern: str
    field: str
    priority: int = 0
    description: str = ""
    normalize_func: Optional[callable] = None


class PressureParser:
    """
    Парсер параметров давления из запроса.
    Поддерживает:
    - PN / Ру (номинальное давление)
    - Рабочее давление в МПа
    - Испытательное давление
    - Различные форматы (PN40, Ру16, давление 4.0 МПа)
    - Канон PN = «PN-класс» (число): PN40 -> 40; рабочее давление = PN / 10.
    """
    
    # Паттерны для извлечения PN (номинальное давление)
    PN_PATTERNS = [
        # Приоритетные паттерны - только явные PN/Ру
        (r'\bPN\s*[:]?\s*(\d+(?:[.,]\d+)?)', 'pn', 100, "PN X", True),
        (r'\bРу\s*[:]?\s*(\d+(?:[.,]\d+)?)', 'pn', 100, "Ру X", True),
        (r'\bPн\s*[:]?\s*(\d+(?:[.,]\d+)?)', 'pn', 95, "Pн X", True),
        (r'\bРн\s*[:]?\s*(\d+(?:[.,]\d+)?)', 'pn', 95, "Рн X", True),
        
        # Давление с указанием PN
        (r'(?:давлени[ея]|nominal pressure)\s*(?:PN|Ру)?\s*[:]?\s*(\d+(?:[.,]\d+)?)',
         'pn', 85, "давление X", True),
        
        # Задвижки/краны в формате "ЗКЛ 150х16" (DN х PN, PN в барах)
        (r'\b(?:задвижк\w*|кран\w*)\s*(?:ЗКЛ\s*)?\d+(?:[.,]\d+)?\s*(?:x|х|×)\s*(\d+(?:[.,]\d+)?)',
         'pn', 75, "задвижка DNхPN", True),
        
        # ✅ Убираем опасный паттерн, который путал DN с PN
        # (r'\b(\d{2,3})\s*(?:МПа|MPa|кгс/см2)?\b', 'pn', 70, "число X как PN", True),
    ]
    
    # Паттерны для извлечения рабочего давления в МПа
    WORKING_PRESSURE_PATTERNS = [
        (r'(?:рабоче[ея]|working)\s*(?:давлени[ея]|pressure)\s*[:]?\s*(\d+(?:[.,]\d+)?)\s*(?:МПа|MPa|мегапаскал[ья])',
         'working_pressure_mpa', 100, "рабочее давление X МПа"),
        (r'(?:давлени[ея]|pressure)\s*(?:в системе|рабочее)\s*[:]?\s*(\d+(?:[.,]\d+)?)\s*(?:МПа|MPa)',
         'working_pressure_mpa', 90, "давление X МПа"),
        (r'(\d+(?:[.,]\d+)?)\s*(?:МПа|MPa|мегапаскал[ья])\s*(?:рабочее|в системе)',
         'working_pressure_mpa', 85, "X МПа рабочее"),
    ]
    
    # Паттерны для извлечения испытательного давления
    TEST_PRESSURE_PATTERNS = [
        (r'(?:испытательн[оа]е|test)\s*(?:давлени[ея]|pressure)\s*[:]?\s*(\d+(?:[.,]\d+)?)\s*(?:МПа|MPa)',
         'test_pressure_mpa', 100, "испытательное давление X МПа"),
        (r'(?:опрессовк[аи]|гидравлическ[ая])\s*(?:давлени[ея]|pressure)?\s*[:]?\s*(\d+(?:[.,]\d+)?)\s*(?:МПа|MPa)',
         'test_pressure_mpa', 90, "опрессовка X МПа"),
        (r'(\d+(?:[.,]\d+)?)\s*(?:МПа|MPa)\s*(?:испытательн[оа]е|опрессовк[аи])',
         'test_pressure_mpa', 85, "X МПа испытательное"),
    ]
    
    # Паттерны для извлечения давления в кгс/см2
    KGCM2_PATTERNS = [
        (r'(\d+(?:[.,]\d+)?)\s*(?:кгс/см2|кг/см2|атм)', 'working_pressure_mpa', 80, "X кгс/см2"),
    ]
    
    # Паттерны для извлечения давления в барах
    BAR_PATTERNS = [
        (r'(\d+(?:[.,]\d+)?)\s*(?:бар|bar|Бар)', 'working_pressure_mpa', 80, "X бар"),
    ]
    
    # Контекстные паттерны для определения давления
    CONTEXT_PATTERNS = {
        "pn": [
            (r'высокое\s+давлени[ея]', 100),
            (r'низкое\s+давлени[ея]', 16),
            (r'среднее\s+давлени[ея]', 40),
        ],
    }
    
    # Таблица соответствия PN и МПа
    PN_TO_MPA = {
        10: 1.0,
        16: 1.6,
        25: 2.5,
        40: 4.0,
        63: 6.3,
        100: 10.0,
        160: 16.0,
        250: 25.0,
        320: 32.0,
        400: 40.0,
    }
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=75)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Основной метод парсинга давления
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
        normalized = text.lower()
        
        # 1. Извлечение PN (номинальное давление)
        self._apply_pn_patterns(normalized, result)
        
        # 2. Извлечение рабочего давления в МПа
        self._apply_working_pressure_patterns(normalized, result)
        
        # 3. Извлечение испытательного давления
        self._apply_test_pressure_patterns(normalized, result)
        
        # 4. Извлечение давления в кгс/см2
        if result.get("working_pressure_mpa") is None:
            self._apply_kgcm2_patterns(normalized, result)
        
        # 5. Извлечение давления в барах
        if result.get("working_pressure_mpa") is None:
            self._apply_bar_patterns(normalized, result)
        
        # 6. Контекстный поиск (если не найдено)
        if result.get("pn") is None:
            self._apply_context_patterns(normalized, result)
        
        # 7. ✅ Проверяем, не является ли PN на самом деле DN
        result = self._filter_false_pn(text, result)
        
        # 8. Если есть PN, но нет рабочего давления - конвертируем
        if result.get("pn") is not None and result.get("working_pressure_mpa") is None:
            result["working_pressure_mpa"] = self._pn_to_mpa(result["pn"])
        
        # 9. Сохраняем raw_value
        if result.get("pn") is not None:
            # Проверяем, был ли PN указан явно
            if re.search(r'\b(?:PN|Ру)\s*' + str(int(result["pn"])), text, re.IGNORECASE):
                result["raw_value"] = f"PN{int(result['pn'])}"
            else:
                # Если PN был вычислен из контекста, не сохраняем raw_value
                result["raw_value"] = None
        
        return result

    # =========================================================
    # ПРИМЕНЕНИЕ ПАТТЕРНОВ
    # =========================================================

    def _apply_pn_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для PN
        """
        # Сортируем по приоритету
        sorted_patterns = sorted(self.PN_PATTERNS, key=lambda x: x[2], reverse=True)
        
        for pattern, field, priority, _, normalize in sorted_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                try:
                    num = float(value.replace(',', '.'))
                    if normalize:
                        result[field] = self._normalize_pn(num)
                    else:
                        result[field] = num
                    break
                except ValueError:
                    continue

    def _apply_working_pressure_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для рабочего давления"""
        for pattern, field, priority, _ in self.WORKING_PRESSURE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result[field] = float(match.group(1).replace(',', '.'))
                    break
                except ValueError:
                    continue

    def _apply_test_pressure_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для испытательного давления"""
        for pattern, field, priority, _ in self.TEST_PRESSURE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result[field] = float(match.group(1).replace(',', '.'))
                    break
                except ValueError:
                    continue

    def _apply_kgcm2_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для давления в кгс/см2"""
        for pattern, field, priority, _ in self.KGCM2_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(',', '.'))
                    result[field] = round(value * 0.098, 2)
                    break
                except ValueError:
                    continue

    def _apply_bar_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для давления в барах"""
        for pattern, field, priority, _ in self.BAR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(',', '.'))
                    result[field] = round(value * 0.1, 2)
                    break
                except ValueError:
                    continue

    def _apply_context_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение контекстных паттернов"""
        for pattern, default_value in self.CONTEXT_PATTERNS.get("pn", []):
            if re.search(pattern, text, re.IGNORECASE):
                result["pn"] = self._normalize_pn(default_value)
                break

    # =========================================================
    # ✅ НОВЫЙ МЕТОД: Фильтрация ложного PN
    # =========================================================

    def _filter_false_pn(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет, не является ли найденный PN на самом деле DN
        """
        pn = result.get("pn")
        if pn is None:
            return result
        
        # Проверяем, есть ли в тексте DN с таким же числом
        # PN хранится как PN-класс (число), поэтому сравниваем напрямую
        pn_number = int(round(pn))
        
        # Ищем DN с этим числом
        dn_patterns = [
            rf'\bDN\s*{pn_number}\b',
            rf'\bДу\s*{pn_number}\b',
            rf'\bдиаметр(?:ом|е|а)?\s*{pn_number}\b',
        ]
        
        for pattern in dn_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Это DN, а не PN - сбрасываем PN
                result["pn"] = None
                result["working_pressure_mpa"] = None
                result["raw_value"] = None
                break
        
        # Также проверяем: если в тексте есть "на X" и X равен PN, то это DN
        if re.search(rf'\bна\s+{pn_number}\b', text.lower()):
            result["pn"] = None
            result["working_pressure_mpa"] = None
            result["raw_value"] = None
        
        return result

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _normalize_pn(self, value: float) -> float:
        """PN40 -> 40, PN16 -> 16 (PN-класс). МПа храним отдельно."""
        return value

    def _pn_to_mpa(self, pn: float) -> Optional[float]:
        """Конвертация PN в МПа"""
        if pn < 10:
            return pn
        
        pn_int = int(pn)
        if pn_int in self.PN_TO_MPA:
            return self.PN_TO_MPA[pn_int]
        
        return pn / 10.0

    def _mpa_to_pn(self, mpa: float) -> float:
        """Конвертация МПа в PN"""
        if mpa < 10:
            return mpa
        
        for pn, value in self.PN_TO_MPA.items():
            if abs(value - mpa) < 0.1:
                return pn
        
        return mpa * 10.0

    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат"""
        return {
            "pn": None,
            "working_pressure_mpa": None,
            "test_pressure_mpa": None,
            "raw_value": None,
        }

    # =========================================================
    # МЕТОДЫ ДЛЯ ОТЛАДКИ
    # =========================================================

    def get_pn_to_mpa_mapping(self) -> Dict[int, float]:
        """Получить таблицу соответствия PN и МПа"""
        return self.PN_TO_MPA.copy()

    def is_valid_pn(self, pn: float) -> bool:
        """Проверка валидности PN"""
        standard_pns = [10, 16, 25, 40, 63, 100, 160, 250, 320, 400]
        return int(pn) in standard_pns or int(pn * 10) in standard_pns

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """Очистка кеша"""
        self._cache.clear()
