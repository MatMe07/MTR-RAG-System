# query_parser/operation_parser.py

import re
from typing import List, Optional, Dict, Tuple

from rapidfuzz import fuzz

from .dictionaries import OPERATION_ALIASES


class OperationParser:

    OPERATION_PRIORITY = {
    "repair": 100,
    "inventory": 100,    
    "replace": 95,
    "check": 95,      
    "impact": 85,        
    "plan": 80,     
    "explain": 70,       
    "search": 50,        
    "document": 40,      
    "assemble": 35,       
    "calculate": 30,
    }

    KEYWORD_MAP = {
        "repair": [
            "сломался",
            "сломалась",
            "сломалось",
            "сломаны",
            "сломанный",
            "поврежден",
            "повреждена",
            "повреждено",
            "повреждены",
            "утечка",
            "ремонт",
        ],

        "replace": [
            "замена",
            "заменить",
            "замену",
            "замены",
            "аналог",
            "аналога",
            "аналогом",
            "вместо",
            "подбери замену",
            "подобрать замену",
        ],

        "plan": [
            "план",
            "плановой",
            "плановое",
            "обслуживание",
            "комплект",
            "список деталей",
            "порядок работ",
        ],

        "check": [
            "проверить",
            "проверь",
            "проверка",
            "хватает",
            "достаточно",
            "подходит",
            "подойдут",
            "что проверить",
        ],

        "explain": [
            "объясни",
            "объяснить",
            "расскажи",
            "рассказать",
            "что значит",
            "означает",
            "чем отличается",
        ],

        "inventory": [
            "сколько",
            "наличие",
            "остаток",
            "остатки",
            "на складе",
            "складе",
            "пополнение",
            "закупки",
            "закупку",
        ],

        "search": [
            "найди",
            "найти",
            "покажи",
            "показать",
        ],

        "impact": [
            "что изменится",
            "последствия",
            "влияние",
        ],

        "document": [
            "паспорта",
            "паспорт",
            "документы",
            "документацию",
            "госты",
            "гост",
        ],

        "assemble": [
            "собери",
            "собрать",
            "комплект",
            "сборка",
            "полный комплект",
        ],

        "calculate": [
            "посчитай",
            "подсчитай",
            "рассчитай",
            "расчет",
        ],
    }

    PHRASE_MAP = [
        ("план замены", "plan"),
        ("план обслуживания", "plan"),
        ("комплект замены", "plan"),
        ("комплект ремонта", "plan"),
        ("полный комплект", "plan"),

        ("порядок ремонта", "repair"),

        ("что проверить", "check"),

        ("что изменится", "impact"),
        ("откуда взяты госты", "document"),
        ("паспорта и ту", "document"),

        ("найди замену", "replace"),
        ("подбери замену", "replace"),
        ("подобрать замену", "replace"),
        ("найди аналог", "replace"),
        ("подбери аналог", "replace"),

        ("собери комплект", "assemble"),
        ("собрать комплект", "assemble"),
    ]

    FUZZY_WORDS = {
        "replace": [
            "замена",
            "заменить",
            "замену",
            "замены",
            "аналог",
            "аналога",
            "вместо",
        ],

        "repair": [
            "ремонт",
            "сломался",
            "сломалась",
            "сломалось",
            "поврежден",
            "повреждена",
            "утечка",
        ],

        "plan": [
            "план",
            "обслуживание",
            "комплект",
        ],

        "check": [
            "проверить",
            "проверь",
            "проверка",
            "хватает",
            "подходит",
        ],

        "explain": [
            "объясни",
            "объяснить",
            "расскажи",
            "рассказать",
            "означает",
        ],

        "inventory": [
            "сколько",
            "наличие",
            "остаток",
        ],

        "search": [
            "найди",
            "найти",
            "покажи",
            "показать",
        ],

        "assemble": [
            "собери",
            "собрать",
            "комплект",
        ],

        "calculate": [
            "посчитай",
            "подсчитай",
        ],
    }

    FUZZY_THRESHOLD = 75
    FUZZY_STRONG_THRESHOLD = 85

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[а-яёa-z]+", text.lower())

    def _fuzzy_operations(self, text: str) -> List[Tuple[str, float]]:
        words = self._tokenize(text)
        scores: Dict[str, float] = {}

        for word in words:
            for operation, targets in self.FUZZY_WORDS.items():
                for target in targets:
                    score = fuzz.ratio(word, target)
                    if score >= self.FUZZY_THRESHOLD:
                        scores[operation] = max(scores.get(operation, 0), score)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        pattern = (
            rf"(?<![а-яёА-ЯЁa-zA-Z])"
            rf"{re.escape(keyword.lower())}"
            rf"(?![а-яёА-ЯЁa-zA-Z])"
        )
        return bool(re.search(pattern, text))

    def parse_all(self, text: str) -> List[str]:
        if not text or not text.strip():
            return ["unknown"]

        text_lower = text.lower()
        found = set()

        # 1. Фразы
        for phrase, operation in self.PHRASE_MAP:
            if phrase in text_lower:
                found.add(operation)

        # 2. Точные ключевые слова
        for operation, keywords in self.KEYWORD_MAP.items():
            for keyword in keywords:
                if self._contains_keyword(text_lower, keyword):
                    found.add(operation)
                    break

        # 3. Алиасы
        for alias, operation in OPERATION_ALIASES.items():
            if self._contains_keyword(text_lower, alias):
                found.add(operation)

        # 4. Fuzzy
        fuzzy_results = self._fuzzy_operations(text)
        for operation, score in fuzzy_results:
            if score >= self.FUZZY_STRONG_THRESHOLD:
                found.add(operation)
            elif score >= self.FUZZY_THRESHOLD:
                found.add(operation)

        # 5. Контекстные признаки (ИСПРАВЛЕНО)
        
        # inventory – только если явные слова
        if any(word in text_lower for word in ["складе", "остат", "наличи", "пополн", "закуп"]):
            # Проверяем что не "установлены ни на одном" (false positive)
            if not re.search(r'установлены?\s+ни\s+на\s+одном', text_lower):
                found.add("inventory")

        # repair – только при явных признаках поломки
        if any(word in text_lower for word in ["сломал", "поврежд", "утечк", "отказал"]):
            found.add("repair")

        if any(word in text_lower for word in ["план", "обслужив", "комплект"]):
            found.add("plan")

        if any(word in text_lower for word in ["провер", "хвата", "достаточ", "подход"]):
            found.add("check")

        if any(word in text_lower for word in ["объясн", "расскаж", "что значит", "означа"]):
            found.add("explain")

        # document – ТОЛЬКО если есть явные слова или ГОСТ/ТУ с номером
        if any(word in text_lower for word in ["паспорт", "документ", "лнд"]):
            found.add("document")
        elif re.search(r"(?:гост|ту)\s+[\d\-]+", text_lower):
            found.add("document")

        if any(word in text_lower for word in ["изменится", "последств", "влияние"]):
            found.add("impact")

        if any(word in text_lower for word in ["собер", "комплект"]):
            found.add("assemble")

        if any(word in text_lower for word in ["посчита", "подсчита", "рассчита"]):
            found.add("calculate")

        if not found:
            return ["unknown"]

        return sorted(
            found,
            key=lambda operation: self.OPERATION_PRIORITY.get(operation, 0),
            reverse=True,
        )

    def parse(self, text: str) -> Optional[str]:
        operations = self.parse_all(text)
        if not operations:
            return "unknown"
        return operations[0]

    def parse_primary(self, text: str) -> str:
        return self.parse(text)
