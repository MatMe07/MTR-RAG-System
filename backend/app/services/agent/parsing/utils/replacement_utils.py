"""Хелперы для явной замены с размерами («DN200 вместо DN150»).

Замена с явным сопоставлением размеров («X вместо Y») не является
неоднозначностью: оба значения DN заданы намеренно (старое → новое).
"""

import re

_DN_REPLACE_RE = re.compile(
    r"(?:dn|ду)\s*[:]?\s*(\d+).{0,40}(?:вместо|на)\s*(?:dn|ду)?\s*[:]?\s*(\d+)",
    re.IGNORECASE,
)


def has_explicit_dn_replacement(text) -> bool:
    """True, если текст содержит явное сопоставление «DN X вместо/на DN Y»
    (замена текущей детали на деталь другого размера)."""
    if not text:
        return False
    return bool(_DN_REPLACE_RE.search(str(text)))