# query_parser/context_extractor.py

import re
from typing import Dict, Any, Optional


class ContextExtractor:
    """Извлечение контекстной информации из запроса"""
    
    # Словари для числительных
    NUM_WORDS = {
        'одна': 1, 'один': 1, 'одно': 1, 'одну': 1,
        'две': 2, 'два': 2, 'двух': 2,
        'три': 3, 'трёх': 3,
        'четыре': 4, 'четырёх': 4,
        'пять': 5, 'пяти': 5,
        'шесть': 6, 'шести': 6,
        'семь': 7, 'семи': 7,
        'восемь': 8, 'восьми': 8,
        'девять': 9, 'девяти': 9,
        'десять': 10, 'десяти': 10,
        'сто': 100, 'двести': 200, 'триста': 300,
        'четыреста': 400, 'пятьсот': 500,
        'шестьсот': 600, 'семьсот': 700,
        'восемьсот': 800, 'девятьсот': 900,
        'тысяча': 1000,
    }
    
    UNITS_COUNT_WORDS = {
        'одн': 1, 'дв': 2, 'трёх': 3, 'тр': 3,
        'четырёх': 4, 'четыр': 4,
        'пяти': 5, 'пят': 5,
        'шести': 6, 'шест': 6,
        'семи': 7, 'сем': 7,
        'восьми': 8, 'вос': 8,
        'девяти': 9, 'девят': 9,
        'десяти': 10, 'десят': 10,
    }
    
    def extract(self, text: str) -> Dict[str, Any]:
        """Извлечение всего контекста"""
        context = {}
        text_lower = text.lower()
        
        # Извлекаем все компоненты
        context['quantity'] = self._extract_quantity(text_lower)
        context['units_count'] = self._extract_units_count(text_lower)
        context['length_meters'] = self._extract_length(text_lower)
        context['timeframe'] = self._extract_timeframe(text_lower)
        context['urgency'] = self._extract_urgency(text_lower)
        context['limit'] = self._extract_limit(text_lower)
        context['sort_by'] = self._extract_sort_by(text_lower)
        
        # Удаляем None значения
        return {k: v for k, v in context.items() if v is not None}
    
    def _extract_quantity(self, text_lower: str) -> Optional[int]:
        """Извлечение количества штук"""
        # Цифры + штуки
        qty_match = re.search(r'(\d+)\s*(?:штук|шт|ед|штуки|штука)', text_lower)
        if qty_match:
            return int(qty_match.group(1))
        
        # Слова + штуки
        match = re.search(r'по\s+(' + '|'.join(self.NUM_WORDS.keys()) + r')\s+штук', text_lower)
        if match:
            return self.NUM_WORDS[match.group(1)]
        
        # Слова + деталь ("два отвода")
        match = re.search(r'(' + '|'.join(self.NUM_WORDS.keys()) + r')\s+(?:отвода|трубы|задвижки|перехода|заглушки|тройника)', text_lower)
        if match:
            return self.NUM_WORDS[match.group(1)]
        
        return None
    
    def _extract_units_count(self, text_lower: str) -> Optional[int]:
        """Извлечение количества участков"""
        # "трёх таких же участков" -> 3
        pattern = r'(' + '|'.join(self.UNITS_COUNT_WORDS.keys()) + r')\s*(?:таких же\s*)?участков'
        match = re.search(pattern, text_lower)
        if match:
            return self.UNITS_COUNT_WORDS[match.group(1)]
        
        # "три участка"
        match = re.search(r'(\d+)\s*(?:таких же\s*)?участков', text_lower)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_length(self, text_lower: str) -> Optional[float]:
        """Извлечение длины в метрах"""
        # Цифры + метры
        match = re.search(r'(\d+)\s*(?:м|метр|метров|метра)', text_lower)
        if match:
            return float(match.group(1))
        
        # Слова + метры (только полные единицы, чтобы не срабатывало на «одном» -> одн/о+м)
        for word, num in self.NUM_WORDS.items():
            if re.search(rf'\b{word}\b\s*(?:метров|метра|метр|метры)', text_lower):
                return float(num)
        
        return None
    
    def _extract_timeframe(self, text_lower: str) -> Optional[str]:
        """Извлечение временных рамок"""
        if re.search(r'следующ\w*\s*недел[ея]', text_lower):
            return 'next_week'
        elif re.search(r'следующ\w*\s*месяц\w*', text_lower):
            return 'next_month'
        elif re.search(r'следующ\w*\s*год\w*', text_lower):
            return 'next_year'
        elif re.search(r'прямо сейчас|сейчас же|немедленно|сегодня', text_lower):
            return 'immediate'
        return None
    
    def _extract_urgency(self, text_lower: str) -> Optional[str]:
        """Извлечение срочности"""
        # «по срочности закупки» — это сортировка, а не срочность
        if re.search(r'(?<!по\s)(?:срочн|критич|немедленн|безотлагательн)', text_lower):
            return 'high'
        return None
    
    def _extract_limit(self, text_lower: str) -> Optional[int]:
        """Извлечение лимита выдаваемых позиций ("выбери пять деталей" -> 5)"""
        pattern = (r'(?:выбери|отбери|возьми|покажи|найди|учитывай|ограничься|ограничь)'
                   r'\s+(?:топ\s*|лучших\s*|первых\s*)?(\d+|' + '|'.join(self.NUM_WORDS.keys()) + r')\s+детал\w*')
        match = re.search(pattern, text_lower)
        if match:
            token = match.group(1)
            if token.isdigit():
                return int(token)
            return self.NUM_WORDS.get(token)
        return None
    
    def _extract_sort_by(self, text_lower: str) -> Optional[str]:
        """Извлечение сортировки результатов"""
        if re.search(r'по\s+срочност\w*\s+закуп\w*', text_lower):
            return 'procurement_urgency'
        elif re.search(r'по\s+срочност\w*', text_lower):
            return 'urgency'
        elif re.search(r'(?:сам\w*\s+высок\w*|максимальн\w*|наибольш\w*)\s*риск\w*|по\s+риск\w*', text_lower):
            return 'risk'
        elif re.search(r'по\s+приоритет\w*', text_lower):
            return 'priority'
        return None
