# agent/llm/json_utils.py
"""Извлечение JSON-объекта из прозаического вывода LLM.

Строки LLM часто содержат пояснения вокруг JSON и ```-фенсы. Вместо жадного
regex `\\{.*\\}` (ломается на `}` внутри текста) сканируем токен `{` по всему
тексту и пробуем `json.JSONDecoder.raw_decode` от этой позиции — берём первый
валидный JSON-объект, не трогая обвязку.
"""

import json
import re
from typing import Any, Dict, Optional

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*")
_FENCE_END_RE = re.compile(r"\s*```\s*$")


def strip_code_fences(text: str) -> str:
    """Срезает markdown-фенсы ```json ... ```, если они есть."""
    out = _FENCE_RE.sub("", (text or "").lstrip())
    return _FENCE_END_RE.sub("", out.rstrip())


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Первый корректный JSON-объект в тексте или None, если его нет."""
    raw = strip_code_fences(text or "")
    decoder = json.JSONDecoder()
    idx = raw.find("{")
    while idx != -1:
        try:
            data, _ = decoder.raw_decode(raw, idx)
        except json.JSONDecodeError:
            idx = raw.find("{", idx + 1)
            continue
        if isinstance(data, dict):
            return data
        idx = raw.find("{", idx + 1)
    return None
