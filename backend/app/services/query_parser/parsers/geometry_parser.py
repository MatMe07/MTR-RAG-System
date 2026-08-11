# query_parser/parsers/geometry_parser.py

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from functools import lru_cache

from ..normalizers.normalizers import normalize_decimal
from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class GeometryPattern:
    """Паттерн для извлечения геометрических параметров"""
    pattern: str
    fields: List[str]
    priority: int = 0
    description: str = ""


class GeometryParser:
    """
    Парсер геометрических параметров из запроса.
    Поддерживает:
    - DN / Ду (условный проход)
    - Диаметры для переходов и тройников (d1, d2)
    - Толщину стенки
    - Углы для отводов
    - Радиус
    - Различные форматы записи (219x159, 426 на 10, DN200)
    """
    
    # Паттерны для извлечения DN (условный проход)
    DN_PATTERNS = [
        # Приоритетные паттерны
        (r'\bDN\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['dn'], 100, "DN с пробелом/двоеточием"),
        (r'\bДу\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['dn'], 100, "Ду с пробелом/двоеточием"),
        (r'\bдиаметр(?:ом|е|а)?\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['dn'], 90, "диаметр с пробелом"),
        (r'\bD\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['dn'], 80, "D с пробелом"),
    ]
    
    # Паттерны для извлечения диаметров для переходов/тройников
    TRANSITION_PATTERNS = [
        (r'(\d+(?:[.,]\d+)?)\s*(?:x|х|×|на)\s*(\d+(?:[.,]\d+)?)', ['d1', 'd2'], 100, "диаметр x диаметр"),
        (r'(\d+(?:[.,]\d+)?)\s*(?:/-|/|—|-)\s*(\d+(?:[.,]\d+)?)', ['d1', 'd2'], 90, "диаметр - диаметр"),
        (r'с\s*(\d+(?:[.,]\d+)?)\s+(?:на|до)\s*(\d+(?:[.,]\d+)?)', ['d1', 'd2'], 80, "с X на Y"),
        (r'от\s*(\d+(?:[.,]\d+)?)\s+(?:до|на)\s*(\d+(?:[.,]\d+)?)', ['d1', 'd2'], 70, "от X до Y"),
    ]
    
    # Паттерны для извлечения толщины стенки
    WALL_PATTERNS = [
        (r'стенк(?:а|и|ой)\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['wall_thickness'], 100, "стенка X"),
        (r'стенкой\s*(\d+(?:[.,]\d+)?)', ['wall_thickness'], 100, "стенкой X"),
        (r'на\s+(\d+)\s*(?:мм|мл|миллиметр)', ['wall_thickness'], 90, "на X мм"),
        (r'толщин(?:а|ы|ой)\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['wall_thickness'], 90, "толщина X"),
        (r'δ\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['wall_thickness'], 80, "δ X"),
        (r'стенка\s+(\d+(?:[.,]\d+)?)', ['wall_thickness'], 80, "стенка X"),
        # ✅ Добавлен паттерн для "426 на 12" где второе число - стенка
        (r'\b(\d+)\s+на\s+(\d+)\b', ['dn', 'wall_thickness'], 70, "X на Y"),
    ]
    
    # Паттерны для извлечения углов
    ANGLE_PATTERNS = [
        # ✅ Исправлен паттерн для "отвод 90" - теперь правильно захватывает
        (r'\b(?:отвод|окш|ог)\s+(30|45|60|90)\b', ['angle'], 100, "отвод с углом"),
        (r'угол(?:ом)?\s*(?:поворота\s*)?[:]?\s*(\d+(?:[.,]\d+)?)', ['angle'], 100, "угол X"),
        (r'(\d+(?:[.,]\d+)?)\s*°', ['angle'], 100, "X°"),
        (r'\b(30|45|60|90)\s*(?:град|градус|°?)', ['angle'], 90, "X градус"),
        (r'\b(?:окш|ог)\s*(\d{1,3})\b', ['angle'], 80, "ОКШ/ОГ X"),
        (r'поворот(?:а|ом)?\s*[:]?\s*(\d+(?:[.,]\d+)?)', ['angle'], 80, "поворот X"),
    ]
    
    # Паттерны для извлечения радиуса
    RADIUS_PATTERNS = [
        (r'(?:радиус|R)\s*[:=]?\s*([0-9.,]+\s*[Dd]|[0-9.,]+)', ['radius'], 100, "радиус X"),
        (r'(?:R|r)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*[Dd]', ['radius'], 90, "R X D"),
        (r'(\d+(?:[.,]\d+)?)\s*[Dd]\s*(?:радиус)', ['radius'], 80, "X D радиус"),
    ]
    
    # Паттерны для специальных случаев (отводы с форматом "отвод 90 426 на 10")
    ELBOW_SPECIAL_PATTERNS = [
        (r'\b(?:отвод(?:а|у|ом|е|ов)?|окш|ог)\s+(30|45|60|90)\s+(\d+(?:[.,]\d+)?)\s+(?:на|x|х|×)\s+(\d+(?:[.,]\d+)?)',
         ['angle', 'dn', 'wall_thickness'], 100, "отвод угол DN на стенку"),
        (r'\b(?:отвод(?:а|у|ом|е|ов)?|окш|ог)\s+(\d+(?:[.,]\d+)?)\s+(?:на|x|х|×)\s+(\d+(?:[.,]\d+)?)',
         ['dn', 'wall_thickness'], 90, "отвод DN на стенку"),
    ]
    
    # Типы деталей для контекстного парсинга
    ITEM_TYPES = {
        'transition': ['переход', 'перехода', 'переходу', 'переходом', 'переходе'],
        'tee': ['тройник', 'тройника', 'тройнику', 'тройником', 'тройнике'],
        'elbow': ['отвод', 'отвода', 'отводу', 'отводом', 'отводе', 'окш', 'ог'],
        'pipe': ['труба', 'трубы', 'трубу', 'трубой', 'трубе', 'труб'],
        'cap': ['заглушка', 'заглушки', 'заглушку', 'заглушкой', 'заглушке'],
        'valve': ['задвижка', 'задвижки', 'задвижку', 'задвижкой', 'задвижке'],
    }
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=75)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Основной метод парсинга геометрических параметров
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
        
        # Определяем тип детали
        item_type = self._detect_item_type(normalized)
        is_transition = item_type in ['transition', 'tee']
        is_elbow = item_type == 'elbow'
        is_pipe = item_type == 'pipe'
        is_cap = item_type == 'cap'
        is_valve = item_type == 'valve'
        
        # 1. Специальные паттерны для отводов
        if is_elbow:
            self._apply_elbow_special_patterns(normalized, result)
        
        # 2. Паттерны для переходов/тройников (d1, d2)
        if is_transition:
            self._apply_transition_patterns(normalized, result)
        
        # 3. Паттерны для DN
        if result.get('dn') is None:
            self._apply_dn_patterns(normalized, result, is_transition)
        
        # 4. Паттерны для толщины стенки
        if is_pipe or is_elbow or is_cap or is_valve:
            self._apply_wall_patterns(normalized, result)
        
        # 5. Паттерны для углов
        if is_elbow or result.get('angle') is None:
            self._apply_angle_patterns(normalized, result)
        
        # 6. Паттерны для радиуса
        self._apply_radius_patterns(normalized, result)
        
        # 7. Если DN не найден, пробуем извлечь из контекста
        if result.get('dn') is None:
            self._extract_dn_from_context(normalized, result, is_transition)
        
        # 8. ✅ Если нет угла, но есть отвод - пробуем извлечь угол из контекста
        if is_elbow and result.get('angle') is None:
            self._extract_angle_from_context(normalized, result)
        
        return result

    # =========================================================
    # ПРИМЕНЕНИЕ ПАТТЕРНОВ
    # =========================================================

    def _apply_patterns(self, text: str, patterns: List[Tuple[str, List[str], int, str]], 
                        result: Dict[str, Any]) -> None:
        """
        Универсальное применение паттернов с приоритетами
        """
        # Сортируем по приоритету
        sorted_patterns = sorted(patterns, key=lambda x: x[2], reverse=True)
        
        for pattern, fields, priority, _ in sorted_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                for i, field in enumerate(fields):
                    if result.get(field) is None:
                        try:
                            value = match.group(i + 1)
                            if field in ['dn', 'd1', 'd2', 'wall_thickness', 'angle']:
                                result[field] = normalize_decimal(value)
                            else:
                                result[field] = value
                        except (IndexError, ValueError):
                            continue
                break

    def _apply_dn_patterns(self, text: str, result: Dict[str, Any], is_transition: bool = False) -> None:
        """Применение паттернов для DN"""
        self._apply_patterns(text, self.DN_PATTERNS, result)
        
        if is_transition and result.get('d1') is not None and result.get('dn') is None:
            result['dn'] = result['d1']

    def _apply_transition_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для переходов/тройников"""
        self._apply_patterns(text, self.TRANSITION_PATTERNS, result)

    def _apply_wall_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для толщины стенки"""
        self._apply_patterns(text, self.WALL_PATTERNS, result)

    def _apply_angle_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для углов"""
        self._apply_patterns(text, self.ANGLE_PATTERNS, result)
        
        if result.get('angle') is None and re.search(r'\bпрямой\s+угол\b', text):
            result['angle'] = 90.0

    def _apply_radius_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение паттернов для радиуса"""
        self._apply_patterns(text, self.RADIUS_PATTERNS, result)

    def _apply_elbow_special_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """Применение специальных паттернов для отводов"""
        self._apply_patterns(text, self.ELBOW_SPECIAL_PATTERNS, result)

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _detect_item_type(self, text: str) -> Optional[str]:
        """Определение типа детали по тексту"""
        for type_name, keywords in self.ITEM_TYPES.items():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", text):
                    return type_name
        return None

    def _extract_dn_from_context(self, text: str, result: Dict[str, Any], is_transition: bool = False) -> None:
        """Извлечение DN из контекста"""
        numbers = re.findall(r'\b(\d+)\b', text)
        
        # Для заглушек и труб: первое число = DN, второе = стенка
        if len(numbers) >= 2:
            if any(keyword in text for keyword in ['заглушка', 'труба', 'труб']):
                if result.get('dn') is None:
                    result['dn'] = normalize_decimal(numbers[0])
                if result.get('wall_thickness') is None:
                    result['wall_thickness'] = normalize_decimal(numbers[1])
                return
        
        if is_transition and result.get('d1') is not None and result.get('dn') is None:
            result['dn'] = result['d1']

    def _extract_angle_from_context(self, text: str, result: Dict[str, Any]) -> None:
        """✅ Извлечение угла из контекста для отводов"""
        # Ищем числа 30, 45, 60, 90 рядом с отводом
        angle_match = re.search(r'\b(30|45|60|90)\b', text)
        if angle_match:
            # Проверяем, что число не является DN или стенкой
            potential_angle = int(angle_match.group(1))
            dn = result.get('dn')
            wall = result.get('wall_thickness')
            
            # Если число не равно DN и не равно стенке, это угол
            if (dn is None or potential_angle != int(dn)) and \
               (wall is None or potential_angle != int(wall)):
                result['angle'] = float(potential_angle)

    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат"""
        return {
            "dn": None,
            "d1": None,
            "d2": None,
            "wall_thickness": None,
            "wall_thickness_2": None,
            "angle": None,
            "radius": None,
        }

    # =========================================================
    # МЕТОДЫ ДЛЯ ОТЛАДКИ
    # =========================================================

    def get_all_patterns(self) -> Dict[str, List[Tuple[str, List[str], int, str]]]:
        """Получить все паттерны для отладки"""
        return {
            "dn": self.DN_PATTERNS,
            "transition": self.TRANSITION_PATTERNS,
            "wall": self.WALL_PATTERNS,
            "angle": self.ANGLE_PATTERNS,
            "radius": self.RADIUS_PATTERNS,
            "elbow_special": self.ELBOW_SPECIAL_PATTERNS,
        }

    def get_item_types(self) -> Dict[str, List[str]]:
        """Получить все типы деталей"""
        return self.ITEM_TYPES

    def clear_cache(self):
        """Очистка кеша"""
        self._cache.clear()
