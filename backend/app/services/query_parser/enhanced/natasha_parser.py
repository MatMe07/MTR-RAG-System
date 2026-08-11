# query_parser/enhanced/natasha_parser.py

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsNERTagger,
    Doc
)
from typing import Dict, Any, List, Optional
import re


class NatashaParser:
    def __init__(self):
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.ner_tagger = NewsNERTagger(self.emb)
        self.morph_tagger = NewsMorphTagger(self.emb)

    def parse(self, text: str) -> Dict[str, Any]:
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_ner(self.ner_tagger)
        doc.tag_morph(self.morph_tagger)
        
        result = {
            "item_types": [],
            "parameters": {
                "dn": None,
                "wall_thickness": None,
                "pressure": None,
                "steel_grade": None,
                "medium": None,
            },
            "operations": [],
            "subtype": None,
        }
        
        # ---------------------------------------------------------
        # 1. Извлечение операций через морфологию
        # ---------------------------------------------------------
        operation_patterns = {
            "replace": [
                r'(?:подбер|найд|замен|аналог|вмест)',
                r'(?:замени|замену|замены)',
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
                r'(?:склад|налич|остат|закуп|пополн|сколько)',
            ],
            "plan": [
                r'(?:план|состав|обслужив|подготов|перечисл)',
            ],
            "impact": [
                r'(?:изменится|последств|влияние|риск)',
            ],
            "document": [
                r'(?:документ|паспорт|гост|ту|сертификат)',
            ],
            "search": [
                r'(?:найди|покажи|найти|показать|выбери)',
            ],
            "assemble": [
                r'(?:собер|комплект|сборка)',
            ],
            "calculate": [
                r'(?:посчитай|подсчитай|рассчитай|расчет)',
            ],
        }
        
        for op, patterns in operation_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    result["operations"].append(op)
                    break
        
        # ---------------------------------------------------------
        # 2. Уточнение операций через NER
        # ---------------------------------------------------------
        for span in doc.spans:
            span_text = span.text.lower()
            # Если NER определил как ORGANIZATION – возможно это код детали
            if span.type == "ORG":
                if re.search(r'(?:COMP|UNIT|KSM|MTR)', span_text, re.IGNORECASE):
                    if "search" not in result["operations"]:
                        result["operations"].append("search")
            
            # Если NER определил как LOCATION – возможно это про склад
            if span.type == "LOC":
                if "склад" in span_text:
                    if "inventory" not in result["operations"]:
                        result["operations"].append("inventory")
        
        # ---------------------------------------------------------
        # 3. Извлечение типов деталей
        # ---------------------------------------------------------
        item_type_keywords = ["отвод", "задвижка", "заглушка", "переход", "тройник", "труба", "кран"]
        
        for span in doc.spans:
            if span.type == "ORG":
                for keyword in item_type_keywords:
                    if keyword in span.text.lower():
                        result["item_types"].append(keyword)
                        break
            
            if span.text.lower() in item_type_keywords:
                result["item_types"].append(span.text.lower())
        
        # ---------------------------------------------------------
        # 4. Извлечение subtype
        # ---------------------------------------------------------
        result["subtype"] = self._parse_subtype(text)
        
        # ---------------------------------------------------------
        # 5. Извлечение параметров
        # ---------------------------------------------------------
        self._extract_parameters(text, result)
        
        return result

    def _parse_subtype(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        
        subtype_patterns = [
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
        
        for pattern, subtype in subtype_patterns:
            if re.search(pattern, text_lower):
                return subtype
        
        return None

    def _extract_parameters(self, text: str, result: Dict) -> None:
        """Извлечение параметров из текста"""
        # DN
        dn_patterns = [
            r'DN\s*(\d+)',
            r'Ду\s*(\d+)',
            r'диаметр(?:ом)?\s*(\d+)',
        ]
        for pattern in dn_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["parameters"]["dn"] = float(match.group(1))
                break
        
        # Толщина стенки
        wall_patterns = [
            r'стенк[аиой]\s*(\d+)',
            r'стенкой\s*(\d+)',
        ]
        for pattern in wall_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["parameters"]["wall_thickness"] = float(match.group(1))
                break
        
        # Давление
        pressure_patterns = [
            r'PN\s*(\d+)',
            r'давлени[ея]\s*(\d+)',
        ]
        for pattern in pressure_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = float(match.group(1))
                result["parameters"]["pressure"] = val / 10.0 if val >= 10 else val
                break
        
        # Материал
        steel_patterns = [
            r'(?:стал[иь])\s+(\d+)',
            r'\b(09Г2С|09ГСФ|13ХФА|12Х18Н10Т|10ХСНД)\b',
        ]
        for pattern in steel_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["parameters"]["steel_grade"] = match.group(1).upper()
                break
        
        # Среда – приоритет: нефть > газ > H2S > CO2
        medium_priority = ["нефть", "природный газ", "вода", "H2S", "CO2"]
        for medium in medium_priority:
            if re.search(rf'\b{medium}\b', text, re.IGNORECASE):
                result["parameters"]["medium"] = medium
                break
