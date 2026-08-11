# query_parser/unit_parser.py

import re
from typing import Optional


class UnitParser:

    PATTERN = re.compile(
        r"\bUNIT-[A-Z0-9-]+\b",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> Optional[str]:
        match = self.PATTERN.search(text)

        if not match:
            return None

        return match.group(0).upper()
