# query_parser/parsers/environment_parser.py

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from functools import lru_cache

from ..dictionaries import MEDIUM_ALIASES, CLIMATE_ALIASES
from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class EnvironmentPattern:
    """Паттерн для извлечения параметров среды"""
    pattern: str
    field: str
    priority: int = 0
    description: str = ""
    normalize_func: Optional[callable] = None


class EnvironmentParser:
    """
    Парсер параметров среды эксплуатации из запроса.
    Поддерживает:
    - Рабочую среду (нефть, газ, вода, H2S, CO2)
    - Климатическое исполнение (У, ХЛ, УХЛ, Т)
    - Температуру эксплуатации
    - Подтверждение H2S/CO2 стойкости
    """
    
    # Паттерны для извлечения среды с приоритетами
    MEDIUM_PATTERNS = [
        # Специфические среды с высоким приоритетом
        (r'\bH2S\b', 'medium', 100, "H2S", lambda x: "H2S"),
        (r'\bCO2\b', 'medium', 100, "CO2", lambda x: "CO2"),
        (r'\bсероводород(?:ная среда)?\b', 'medium', 95, "сероводород", lambda x: "H2S"),
        (r'\bуглекислый газ\b', 'medium', 95, "углекислый газ", lambda x: "CO2"),
        
        # Основные среды
        (r'\bнефть\b', 'medium', 90, "нефть", lambda x: "нефть"),
        (r'\bнефтян(?:ая|ой|ую|ые|ых)\s+сред[аы]?\b', 'medium', 90, "нефтяная среда", lambda x: "нефть"), 
        (r'\bприродный газ\b', 'medium', 90, "природный газ", lambda x: "природный газ"),
        (r'\bгаз\b', 'medium', 85, "газ", lambda x: "газ"),
        (r'\bвода\b', 'medium', 85, "вода", lambda x: "вода"),
        
        # Среда через предлоги
        (r'(?:для|с|на)\s+(?:H2S|сероводород)', 'medium', 80, "для H2S", lambda x: "H2S"),
        (r'(?:для|с|на)\s+(?:CO2|углекислый газ)', 'medium', 80, "для CO2", lambda x: "CO2"),
        
        # Среда в составе слова
        (r'UNIT[-_\s]*(?:H2S|CO2)', 'medium', 75, "UNIT с H2S/CO2", lambda x: x.upper()),
    ]
    
    # Паттерны для климатического исполнения
    CLIMATE_PATTERNS = [
        # Точные совпадения (высший приоритет)
        (r'\bУХЛ1?\b', 'climate_version', 100, "УХЛ", lambda x: "УХЛ"),
        (r'\bХЛ1?\b', 'climate_version', 100, "ХЛ", lambda x: "ХЛ"),
        (r'\bТ\b', 'climate_version', 95, "Т", lambda x: "Т"),
        
        # Климатика через слова
        (r'\bсевер(?:ный|ное)?\b', 'climate_version', 90, "север", lambda x: "ХЛ"),
        (r'\bтропик(?:и|еский|еская|еское)?\b', 'climate_version', 90, "тропики", lambda x: "Т"), 
        (r'\bтропическ(?:ий|ая|ое|ие|их)\s+исполнени[ея]?\b', 'climate_version', 90, "тропическое исполнение", lambda x: "Т"),
        (r'\bумеренн(?:ый|ая|ое)?\b', 'climate_version', 85, "умеренный", lambda x: "У"),
        
        # Климатика с пояснениями
        (r'(?:климат|исполнение)\s+(?:УХЛ|ХЛ|Т|У)', 'climate_version', 80, "климат X", lambda x: x.upper()),
    ]
    
    # Паттерны для температуры
    TEMPERATURE_PATTERNS = [
        (r'(?:температур[аы]|град)\s*[:]?\s*([-+]?\d+(?:[.,]\d+)?)\s*(?:°?C|°|градус[а]?)?',
         'temperature_min_c', 100, "температура X°C"),
        (r'(?:до|от|при)\s*([-+]?\d+(?:[.,]\d+)?)\s*(?:°?C|°|градус[а]?)?',
         'temperature_min_c', 90, "до X°C"),
        (r'([-+]?\d+(?:[.,]\d+)?)\s*(?:°?C|°|градус[а]?)\s*(?:температур[аы])',
         'temperature_min_c', 85, "X°C температура"),
    ]
    
    # Контекстные паттерны для определения среды
    CONTEXT_PATTERNS = {
        "h2s_confirmed": [
            (r'сероводород(?:ная среда)?', True),
            (r'H2S\s*(?:среда|стойк)', True),
            (r'кислотн(?:ый|ая|ое)', True),
        ],
        "co2_confirmed": [
            (r'CO2\s*(?:среда|стойк)', True),
            (r'углекисл(?:ый|ая|ое)', True),
        ],
        "medium": [
            (r'агрессивн(?:ая|ой|ую)', "H2S"),
            (r'коррозионн(?:ая|ой|ую)', "H2S"),
            (r'нейтральн(?:ая|ой|ую)', "вода"),
            (r'горюч(?:ая|ой|ую)', "нефть"),
        ],
    }
    
    # Список климатических исполнений для валидации
    VALID_CLIMATE_VERSIONS = ["У", "ХЛ", "УХЛ", "Т", "УХЛ1", "ХЛ1"]
    
    # Список валидных сред
    VALID_MEDIUMS = ["нефть", "природный газ", "газ", "вода", "H2S", "CO2"]
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=80)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Основной метод парсинга среды
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
        
        # Проверяем наличие UNIT с указанием среды
        has_unit_h2s = bool(re.search(r'unit[\-_\s]*h2s', normalized))
        has_unit_co2 = bool(re.search(r'unit[\-_\s]*co2', normalized))
        
        if has_unit_h2s or has_unit_co2:
            if has_unit_h2s:
                result["medium"] = "H2S"
                result["h2s_confirmed"] = True
            if has_unit_co2:
                result["medium"] = "CO2"
                result["co2_confirmed"] = True
        else:
            # 1. Извлечение среды
            self._apply_medium_patterns(normalized, result)
            
            # 2. Контекстный поиск среды
            if result.get("medium") is None:
                self._apply_context_medium_patterns(normalized, result)
            
            # 3. Извлечение климатики
            self._apply_climate_patterns(normalized, result)
            
            # 4. Извлечение температуры
            self._apply_temperature_patterns(normalized, result)
            
            # 5. Подтверждение H2S/CO2 стойкости
            self._apply_h2s_co2_confirmation(normalized, result)
            
            # 6. Fuzzy-поиск для среды
            if result.get("medium") is None:
                self._apply_fuzzy_medium_search(normalized, result)
        
        # 7. Нормализация климатики
        if result.get("climate_version"):
            result["climate_version"] = self._normalize_climate(result["climate_version"])
        
        # 8. Если есть h2s_confirmed, но нет medium - заполняем
        if result.get("h2s_confirmed") and result.get("medium") is None:
            result["medium"] = "H2S"
        if result.get("co2_confirmed") and result.get("medium") is None:
            result["medium"] = "CO2"
        
        return result

    # =========================================================
    # ПРИМЕНЕНИЕ ПАТТЕРНОВ
    # =========================================================

    def _apply_medium_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для среды
        """
        # Сортируем по приоритету
        sorted_patterns = sorted(self.MEDIUM_PATTERNS, key=lambda x: x[2], reverse=True)
        
        for pattern, field, priority, _, normalize_func in sorted_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(0) if isinstance(match.group(0), str) else match.group(1)
                if normalize_func:
                    result[field] = normalize_func(value)
                else:
                    result[field] = value
                
                if result.get("medium") == "H2S":
                    result["h2s_confirmed"] = True
                elif result.get("medium") == "CO2":
                    result["co2_confirmed"] = True
                
                break

    def _apply_climate_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для климатики
        """
        # Сортируем по приоритету
        sorted_patterns = sorted(self.CLIMATE_PATTERNS, key=lambda x: x[2], reverse=True)
        
        for pattern, field, priority, _, normalize_func in sorted_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(0)
                if normalize_func:
                    result[field] = normalize_func(value)
                else:
                    result[field] = value
                break
        
        # Специальная обработка для "У" (отличаем от предлога)
        if result.get("climate_version") is None:
            self._extract_climate_u(text, result)

    def _apply_temperature_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для температуры
        """
        for pattern, field, priority, _ in self.TEMPERATURE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = match.group(1).replace(',', '.')
                    result[field] = float(value)
                    break
                except (ValueError, IndexError):
                    continue

    def _apply_context_medium_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение контекстных паттернов для среды
        """
        for pattern, default_value in self.CONTEXT_PATTERNS.get("medium", []):
            if re.search(pattern, text, re.IGNORECASE):
                result["medium"] = default_value
                # ✅ Если нашли H2S, устанавливаем флаг
                if default_value == "H2S":
                    result["h2s_confirmed"] = True
                break

    def _apply_h2s_co2_confirmation(self, text: str, result: Dict[str, Any]) -> None:
        """
        Подтверждение H2S/CO2 стойкости
        """
        # Проверяем H2S
        for pattern, value in self.CONTEXT_PATTERNS.get("h2s_confirmed", []):
            if re.search(pattern, text, re.IGNORECASE):
                result["h2s_confirmed"] = value
                if result.get("medium") is None:
                    result["medium"] = "H2S"
                break
        
        # Проверяем CO2
        for pattern, value in self.CONTEXT_PATTERNS.get("co2_confirmed", []):
            if re.search(pattern, text, re.IGNORECASE):
                result["co2_confirmed"] = value
                if result.get("medium") is None:
                    result["medium"] = "CO2"
                break

    def _apply_fuzzy_medium_search(self, text: str, result: Dict[str, Any]) -> None:
        """
        Fuzzy-поиск среды
        """
        words = re.findall(r"[а-яёa-z0-9]+", text.lower())
        
        # Собираем все алиасы сред
        all_aliases = list(MEDIUM_ALIASES.keys())
        
        for word in words:
            if len(word) < 3:
                continue
            
            matches = self.fuzzy_matcher.match(word, all_aliases)
            for matched_alias, score in matches:
                if score >= 80:
                    medium = MEDIUM_ALIASES[matched_alias]
                    result["medium"] = medium
                    if medium == "H2S":
                        result["h2s_confirmed"] = True
                    elif medium == "CO2":
                        result["co2_confirmed"] = True
                    return

    # =========================================================
    # СПЕЦИАЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _extract_climate_u(self, text: str, result: Dict[str, Any]) -> None:
        """
        Специальное извлечение климатики "У" (отличаем от предлога)
        """
        text_lower = text.lower()
        
        # Проверяем, что "у" не является предлогом
        # Ищем "У" в конце строки, после запятой, после тире, или в скобках
        climate_u_patterns = [
            r',\s*у\b',           # ", у" после запятой
            r'\s+у\b',            # " у" отдельно
            r'\(у\)',             # "(у)" в скобках
            r'исполнени[ея]\s+у\b',  # "исполнение У"
            r'климат\s+у\b',      # "климат У"
            r'\bу\s*[,;]',        # "у," или "у;"
            r'-\s*у\b',           # "- у" после тире
        ]
        
        for pattern in climate_u_patterns:
            if re.search(pattern, text_lower):
                result["climate_version"] = "У"
                return
        
        # Проверяем, что "у" не является предлогом "у меня", "у нас" и т.д.
        words = re.findall(r'\b\w+\b', text_lower)
        for i, word in enumerate(words):
            if word == 'у' and i > 0:
                next_word = words[i + 1] if i + 1 < len(words) else ''
                if next_word in ['меня', 'нас', 'него', 'нее', 'них', 'вас', 'тебя', 'себя']:
                    continue  # это предлог
                # Проверяем, что перед "у" не стоит точка или начало предложения
                prev_word = words[i - 1] if i - 1 >= 0 else ''
                if prev_word and prev_word not in [',', ';', 'и', 'а', 'но', 'или']:
                    result["climate_version"] = "У"
                    return

    def _normalize_climate(self, climate: str) -> str:
        """
        Нормализация климатического исполнения
        """
        climate_upper = climate.upper()
        
        # Проверяем по алиасам
        for alias, normalized in CLIMATE_ALIASES.items():
            if alias.upper() == climate_upper:
                return normalized
        
        return climate_upper

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _empty_result(self) -> Dict[str, Any]:
        """
        Пустой результат
        """
        return {
            "medium": None,
            "h2s_confirmed": None,
            "co2_confirmed": None,
            "temperature_min_c": None,
            "climate_version": None,
        }

    def is_valid_medium(self, medium: str) -> bool:
        """
        Проверка валидности среды
        """
        return medium in self.VALID_MEDIUMS

    def is_valid_climate(self, climate: str) -> bool:
        """
        Проверка валидности климатики
        """
        return climate in self.VALID_CLIMATE_VERSIONS

    def get_all_mediums(self) -> List[str]:
        """
        Получить все среды
        """
        return self.VALID_MEDIUMS.copy()

    def get_all_climates(self) -> List[str]:
        """
        Получить все климатики
        """
        return self.VALID_CLIMATE_VERSIONS.copy()

    def get_medium_aliases(self, medium: str) -> List[str]:
        """
        Получить алиасы для среды
        """
        return [alias for alias, value in MEDIUM_ALIASES.items() if value == medium]

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша
        """
        self._cache.clear()
