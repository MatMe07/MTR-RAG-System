# agent/parsing/llm_extractor.py

"""§1F: LLM-доизвлечение недостающих параметров (fallback к regex).

Вызывается из enrich_parsed ПОСЛЕ rule-парсеров, только если для
primary-интента остались непокрытые required-параметры.

Принципы:
- приоритет у regex/rule-парсеров: уже извлечённые значения НЕ перезаписываются;
- LLM возвращает только JSON-объект с заполненными полями, неизвестное пропускается;
- ошибки / нет ключа / невалидный JSON → пустой dict, пайплайн не падает;
- кеш (llm/cache.py), метрики extractor_* в LLMClient.
"""

import json
import logging
from typing import Any, Dict, Optional, Set

from ..core.exceptions import LLMError, LLMTimeoutError
from ..llm.cache import get_llm_cache
from ..llm.client import get_llm_client
from ..llm.response_parser import extract_json_object
from .normalizers import (
    normalize_climate,
    normalize_dn,
    normalize_item_type,
    normalize_material,
    normalize_medium,
)

logger = logging.getLogger(__name__)

# Поля, которые LLM может доизвлечь. Числовые и строковые группы.
NUMERIC_FIELDS: Set[str] = {
    "dn", "pn", "angle", "wall_thickness", "d1", "d2",
    "old_dn", "new_dn", "old_pn", "new_pn",
    "units_count", "quantity",
}
STRING_FIELDS: Set[str] = {
    "item_type", "material", "steel_grade", "medium", "climate",
    "strength_class", "gost_tu", "unit_id", "component_id",
    "old_material", "new_material",
}
# Значения этих полей прогоняются через нормализаторы §1E.
NORMALIZERS: Dict[str, Any] = {
    "dn": normalize_dn,
    "material": normalize_material,
    "steel_grade": normalize_material,
    "medium": normalize_medium,
    "climate": normalize_climate,
    "item_type": normalize_item_type,
}

ALL_FIELDS: Set[str] = NUMERIC_FIELDS | STRING_FIELDS

_TYPES_RU = {
    "dn": "диаметр DN (число)",
    "pn": "давление PN (число)",
    "angle": "угол отвода (число)",
    "wall_thickness": "толщина стенки (число)",
    "d1": "диаметр 1 перехода (число)",
    "d2": "диаметр 2 перехода (число)",
    "medium": "среда",
    "material": "материал/марка стали",
    "steel_grade": "марка стали",
    "strength_class": "класс прочности на разрыв",
    "climate": "климатическое исполнение (У/УХЛ/ХЛ/Т)",
    "gost_tu": "ГОСТ или ТУ",
    "item_type": "тип детали (отвод/задвижка/заглушка/переход/тройник/труба/кран)",
    "unit_id": "идентификатор участка",
    "component_id": "идентификатор компонента",
}


class LLMExtractor:
    """LLM-доизвлечение недостающих параметров с graceful-fallback."""

    def __init__(self, client: Optional[Any] = None, cache: Optional[Any] = None):
        self._client = client
        self._cache = cache if cache is not None else get_llm_cache()

    # ------------------------------------------------------ доступ
    @property
    def client(self) -> Optional[Any]:
        if self._client is None:
            self._client = get_llm_client()
        return self._client

    @property
    def enabled(self) -> bool:
        return self.client is not None

    # ------------------------------------------------------ метрики
    def _metrics(self) -> Optional[Dict[str, Any]]:
        m = getattr(self.client, "_metrics", None)
        return m if isinstance(m, dict) else None

    def _bump(self, suffix: str) -> None:
        m = self._metrics()
        if m:
            key = f"extractor_{suffix}"
            m[key] = m.get(key, 0) + 1

    # ------------------------------------------------------ точка входа
    def extract_missing(
        self,
        intent: str,
        query: str,
        missing: list,
        known: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Доизвлекает недостающие поля для интента. Никогда не бросает."""
        missing = [f for f in (missing or []) if f in ALL_FIELDS]
        if not missing:
            return {}
        client = self.client
        if client is None:
            return {}

        target = self._target_fields(intent, missing)
        prompt = self._build_prompt(intent, query, target, known)
        cache_key = f"extract:{intent}:{hash((query or '').strip().lower())}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            self._bump("hits")
            return {k: v for k, v in cached.items() if k in target}

        self._bump("calls")
        try:
            content = client.invoke(prompt)
            data = extract_json_object(content)
        except (LLMError, LLMTimeoutError, ValueError, json.JSONDecodeError) as e:
            self._bump("errors")
            logger.warning("LLM-экстрактор (§1F): %s", e)
            return {}

        result = self._validate(data, target, known)
        if result:
            self._cache.set(cache_key, dict(result))
        return result

    # ------------------------------------------------------ вспомогательное
    @staticmethod
    def _target_fields(intent: str, missing: list) -> list:
        """Недостающие поля + недостающие соседние поля из AND-групп интента."""
        from ..intent.matrix import INTENT_REQUIREMENTS

        target = list(dict.fromkeys(missing))
        req = INTENT_REQUIREMENTS.get(intent, {}).get("required", []) or []
        for group in req:
            if any(f in target for f in group):
                for f in group:
                    if f in ALL_FIELDS and f not in target:
                        target.append(f)
        return target

    @classmethod
    def _build_prompt(cls, intent: str, query: str, target: list, known: Dict[str, Any]) -> str:
        lines = [f"Интент: {intent}", f"Запрос: {query}", "", "Целевые поля (верни только их):"]
        for f in target:
            hint = _TYPES_RU.get(f, f)
            lines.append(f"- {f}: {hint}")
        if known:
            lines.append("")
            lines.append("Уже точно известно (НЕ переопределяй): " + ", ".join(
                f"{k}={v}" for k, v in known.items() if v is not None
            ))
        lines.extend([
            "",
            "Правила:",
            "1. Верни ТОЛЬКО JSON-объект вида {\"key\": value} без пояснений.",
            "2. Указывай только те целевые поля, которые можно уверенно извлечь из запроса.",
            "3. Не выдумывай значения. Нет данных — пропусти поле (или пустой объект {}).",
            "4. Не включай поля из «уже известно».",
            "5. Числа — числами (например \"dn\": 50), строки — строками как в запросе.",
            "Формат: json",
        ])
        return "\n".join(lines)

    @staticmethod
    def _validate(data: Any, target: list, known: Dict[str, Any]) -> Dict[str, Any]:
        """Отбирает валидные поля: только целевые, без известных, с проверкой типа."""
        if not isinstance(data, dict):
            return {}
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if key not in target or key in known or value is None:
                continue
            if key in NUMERIC_FIELDS:
                try:
                    value = float(str(value).replace(",", "."))
                except (TypeError, ValueError):
                    continue
                if key in ("units_count", "quantity"):
                    value = int(value)
            elif isinstance(value, str):
                value = str(value).strip()
                if not value:
                    continue
            else:
                continue
            norm = NORMALIZERS.get(key)
            if norm is not None:
                try:
                    nv = norm(value)
                except Exception:  # noqa: BLE001
                    continue
                if nv is None or nv == "":
                    continue
                value = nv
            result[key] = value
        return result


# ------------------------------------------------------------ фабрика
_extractor: Optional[LLMExtractor] = None


def get_llm_extractor() -> LLMExtractor:
    global _extractor
    if _extractor is None:
        _extractor = LLMExtractor()
    return _extractor


def reset_llm_extractor() -> None:
    global _extractor
    _extractor = None