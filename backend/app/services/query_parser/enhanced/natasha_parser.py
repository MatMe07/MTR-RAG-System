# query_parser/enhanced/natasha_parser.py

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
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
        }
        
        # 1. Извлечение типов деталей из NER
        item_type_keywords = ["отвод", "задвижка", "заглушка", "переход", "тройник", "труба"]
        
        for span in doc.spans:
            # Ищем по NER
            if span.type == "ORG":
                for keyword in item_type_keywords:
                    if keyword in span.text.lower():
                        result["item_types"].append(keyword)
                        break
            
            # Ищем по морфологии
            if span.text.lower() in item_type_keywords:
                result["item_types"].append(span.text.lower())
        
        # 2. Извлечение числовых параметров
        numbers = re.findall(r'(\d+(?:[.,]\d+)?)', text)
        
        # Ищем DN
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
        
        # Ищем толщину стенки
        wall_patterns = [
            r'стенк[аиой]\s*(\d+)',
            r'стенкой\s*(\d+)',
        ]
        for pattern in wall_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["parameters"]["wall_thickness"] = float(match.group(1))
                break
        
        # Ищем давление
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
        
        # 3. Материал
        steel_patterns = [
            r'(?:стал[иь])\s+(\d+)',
            r'\b(09Г2С|09ГСФ|13ХФА|12Х18Н10Т|10ХСНД)\b',
        ]
        for pattern in steel_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["parameters"]["steel_grade"] = match.group(1).upper()
                break
        
        # 4. Среда
        medium_patterns = [
            r'H2S',
            r'CO2',
            r'сероводород',
            r'углекислый газ',
        ]
        for pattern in medium_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result["parameters"]["medium"] = pattern.upper()
                break
        
        # 5. Операции
        operation_keywords = {
            "replace": ["замен", "аналог", "вместо", "подбери"],
            "repair": ["ремонт", "сломал", "поврежд", "утечк", "отказал"],
            "check": ["провер", "хвата", "подходит"],
            "explain": ["объясн", "расскаж", "означа"],
            "inventory": ["склад", "налич", "остат", "закуп"],
            "plan": ["план", "обслужив", "комплект"],
            "impact": ["изменится", "последств", "влияние"],
            "document": ["документ", "паспорт", "гост", "ту"],
            "search": ["найди", "покажи", "найти"],
        }
        
        for op, keywords in operation_keywords.items():
            for keyword in keywords:
                if re.search(keyword, text, re.IGNORECASE):
                    result["operations"].append(op)
                    break
        
        return result
