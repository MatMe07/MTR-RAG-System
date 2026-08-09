# query_parser/component_parser.py

import re
from typing import Optional


class ComponentParser:

    PATTERN = re.compile(
        r"\bCOMP-[A-Z0-9-]+\b",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> Optional[str]:
        match = self.PATTERN.search(text)

        if not match:
            return None

        return match.group(0).upper()
