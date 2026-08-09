# query_parser/normative_parser.py

import re
from typing import Optional, Dict, Any


class NormativeParser:

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        text_upper = text.upper()
        
        # Ищем реальный ГОСТ или ТУ с номером
        # Форматы: 
        #   ГОСТ 12345-67, ГОСТ 12345, ГОСТ 12345-67-89
        #   ТУ 1234-567, ТУ 1234-567-89, ТУ 1234.567
        gost_match = re.search(
            r'\bГОСТ\s+[\d\-]+(?:\.[\d\-]+)?',
            text_upper
        )
        tu_match = re.search(
            r'\bТУ\s+[\d\-]+(?:\.[\d\-]+)?',
            text_upper
        )
        
        gost_tu = None
        if gost_match:
            gost_tu = gost_match.group(0)
        elif tu_match:
            gost_tu = tu_match.group(0)
        
        if gost_tu:
            return {"gost_tu": gost_tu, "lnd_sections": []}
        
        return None
