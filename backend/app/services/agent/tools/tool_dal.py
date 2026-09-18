# agent/tools/tool_dal.py
"""адаптер DAL поверх IRepository (ЭТАП 3).

Инструменты ЭТАПА 3 работают только через этот слой. Сейчас источник —
репозиторий (JSON fallback / DB), позднее заменяется провайдерами
PostgreSQL/Neo4j/Qdrant без изменения инструментов.

Все методы возвращают JSON-безопасные dict.
"""

import logging
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from app.services.agent.repository.interfaces import IRepository
from app.services.agent.tools.core_tools import _match_score, _matches_filters

log = logging.getLogger("mtr.agent.tool_dal")

DEFAULT_LIMIT = 100
BATCH_LIMIT = 50
NEIGHBOR_DEPTH_MAX = 5


def _prop(card: Dict[str, Any], key: str, default: Any = None) -> Any:
    p = (card.get("properties") or {}).get(key)
    if p is None:
        return default
    return p.get("value", default)


def _contains(haystack: Any, needle: str) -> bool:
    if haystack is None:
        return False
    h = str(haystack).strip().lower()
    n = needle.strip().lower()
    return bool(h) and bool(n) and (n in h or h in n)


def _project_root(depth: int) -> Path:
    return Path(__file__).parents[depth]


def _sample_docs_dir() -> Path:
    for base in [_project_root(5), Path.cwd()]:
        d = base / "data" / "sample" / "documents"
        if d.exists():
            return d
    return _project_root(5) / "data" / "sample" / "documents"


def _sample_lnd_path() -> Path:
    d = _sample_docs_dir()
    for base in [d, d.parent]:
        p = base / "lnd_extract.md"
        if p.exists():
            return p
    return d / "lnd_extract.md"


_LND_SECTION_HEAD_NORM = {
    "раздел": "раздел", "раздела": "раздел", "разделу": "раздел", "разделы": "раздел",
    "глава": "глава", "главе": "глава", "главу": "глава", "главы": "глава",
    "пункт": "пункт", "пункта": "пункт", "пункте": "пункт", "пункты": "пункт",
    "параграф": "параграф", "параграфа": "параграф", "параграфе": "параграф",
    "часть": "часть", "части": "часть",
}


class ToolDAL:
    """Адаптер DAL над IRepository для инструментов ЭТАПА 3."""

    def __init__(self, repo: IRepository):
        self.repo = repo

    # =======================================================================
    # КАТАЛОГ
    # =======================================================================
    def search_catalog(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Поиск по параметрам. Возвращает [{'card': ..., 'score': ...}]."""
        tf: Dict[str, Any] = {}
        for key in ("dn", "pn", "angle", "wall_thickness"):
            if params.get(key) is not None:
                tf[key] = params[key]

        item_types: List[str] = []
        if params.get("item_type"):
            item_types = [params["item_type"]]

        parsed = SimpleNamespace(technical_filters=tf, item_types=item_types)
        matches: List[Dict[str, Any]] = []
        for card in self.repo.get_catalog():
            if not _matches_filters(card, parsed):
                continue
            if not self._extra_filters_ok(card, params):
                continue
            matches.append({"card": card, "score": _match_score(card, parsed)})
        if matches:
            matches.sort(
                key=lambda x: (x["score"] is not None, x["score"] if x["score"] is not None else 0.0),
                reverse=True,
            )
            return matches

        # Пустой детерминированный результат — семантический fallback по каталогу
        # (Qdrant mtr_descriptions), если репозиторий его поддерживает.
        semantic = getattr(self.repo, "search_catalog_semantic", None)
        if semantic is not None:
            try:
                hits = semantic(self._params_to_semantic_query(params), limit=5)
            except Exception:
                hits = None
            if hits:
                for hit in hits:
                    hit["source"] = "vector_fallback"
                    hit["card"] = self._ensure_full_card(hit.get("card"))
                return hits
        return []

    def _ensure_full_card(self, card: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Достроить карточку хита semantic-fallback через get_component.

        Репозиторий уже возвращает полноценные карточки (get_card_by_ksm);
        защитный довод на случай partial-payload от провайдера.
        """
        if not card or card.get("codes") or card.get("properties"):
            return card
        ksm = card.get("ksm_code") or (card.get("codes") or {}).get("ksm_code")
        if ksm:
            full = self.get_component(ksm)
            if full is not None:
                return full
        return card

    def get_component(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Карточка по KSM, card_id или MTR-коду."""
        card = self.repo.get_card_by_ksm(identifier)
        if card is None:
            card = self.repo.get_card_by_id(identifier)
        if card is None:
            for c in self.repo.get_catalog():
                if (c.get("codes") or {}).get("mtr_code") == identifier:
                    card = c
                    break
        return card

    def to_component(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """Карточка → JSON-представление Component."""
        codes = card.get("codes") or {}
        props = card.get("properties") or {}
        attributes = {
            k: v.get("value")
            for k, v in props.items()
            if k != "stock_qty" and v is not None
        }
        component = {
            "ksm_code": codes.get("ksm_code"),
            "mtr_code": codes.get("mtr_code"),
            "card_id": card.get("card_id"),
            "item_type": card.get("item_type"),
            "subtype": card.get("subtype"),
            "name": card.get("name"),
            "designation": card.get("designation") or card.get("name"),
            "attributes": attributes,
            "gost_tu": _prop(card, "gost_tu"),
            "standard": _prop(card, "standard"),
            "stock_qty": _prop(card, "stock_qty", 0.0),
            "unit": "pcs",
            "is_synthetic": bool(_prop(card, "synthetic", False)),
            "match_score": 0.0,
            "matched_fields": [],
            "sources": [],
        }
        return component

    def to_stock_item(self, ksm_code: str, card: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ksm_code": ksm_code,
            "quantity": _prop(card, "stock_qty", 0.0),
            "unit": "pcs",
            "business_unit": _prop(card, "business_unit"),
            "stock_category": _prop(card, "stock_category"),
            "cost": _prop(card, "cost", self.repo.get_stock_cost(ksm_code)),
            "planned_involvement_date": _prop(card, "planned_involvement_date"),
            "forecast_involvement_date": _prop(card, "forecast_involvement_date"),
            "stock_balance": _prop(card, "stock_balance"),
            "source": "repository",
        }

    @staticmethod
    def _params_to_semantic_query(params: Dict[str, Any]) -> str:
        parts: List[str] = []
        if params.get("item_type"):
            parts.append(str(params["item_type"]))
        if params.get("designation"):
            parts.append(str(params["designation"]))
        for key, label in (("dn", "DN"), ("pn", "PN"), ("angle", "угол")):
            if params.get(key) is not None:
                parts.append(f"{label} {params[key]}")
        if params.get("steel_grade"):
            parts.append(str(params["steel_grade"]))
        if params.get("medium"):
            parts.append(str(params["medium"]))
        if params.get("gost_tu"):
            parts.append(str(params["gost_tu"]))
        return " ".join(parts).strip()

    @staticmethod
    def _query_needs_safety_confirmation(params: Dict[str, Any], marker: str) -> bool:
        """Активна ли в запросе среда, требующая подтверждения пригодности.

        marker: h2s | co2. Признаки H2S/CO2 — флаг confirmed или ключевое
        слово в medium (кириллица и латиница).
        """
        if marker == "h2s" and params.get("h2s_confirmed"):
            return True
        if marker == "co2" and params.get("co2_confirmed"):
            return True
        med = str(params.get("medium") or "").lower()
        if marker == "h2s":
            return bool(med) and ("h2s" in med or "сероводород" in med)
        if marker == "co2":
            return bool(med) and ("co2" in med or "углекисл" in med)
        return False

    def _extra_filters_ok(self, card: Dict[str, Any], params: Dict[str, Any]) -> bool:
        for key, propkey in (
            ("steel_grade", "steel_grade"),
            ("medium", "medium"),
            ("climate", "climate_version"),
            ("gost_tu", "gost_tu"),
        ):
            want = params.get(key)
            if want:
                got = _prop(card, propkey)
                if not _contains(got, str(want)):
                    return False
        # P0 безопасность: из запроса с H2S/CO2-средой исключаем карточки с
        # ЯВНЫМ «не подтверждено» (h2s_confirmed=false / co2_confirmed=false).
        # unknown/null остаются в поиске — их помечает verifier (safety_unconfirmed).
        if self._query_needs_safety_confirmation(params, "h2s") and _prop(card, "h2s_confirmed") is False:
            return False
        if self._query_needs_safety_confirmation(params, "co2") and _prop(card, "co2_confirmed") is False:
            return False
        mtr = params.get("mtr_code")
        if mtr and (card.get("codes") or {}).get("mtr_code") != mtr:
            return False
        ks = params.get("ksm_code")
        if ks and (card.get("codes") or {}).get("ksm_code") != ks:
            return False
        return True

    # =======================================================================
    # ПАСПОРТА
    # =======================================================================
    def get_passport_params(self, document_id: str) -> Dict[str, Any]:
        """Извлечение параметров паспорта.

        Источник Шага 3 — провайдер паспортов (PG); если документ не загружен
        в БД — legacy регэкспы по тестовым файлам.
        """
        repo_method = getattr(self.repo, "get_passport_params", None)
        if repo_method is not None:
            try:
                result = repo_method(document_id)
            except Exception:
                result = None
            if result is not None and result.get("params"):
                return result

        path = self._find_passport(document_id)
        if path is None:
            return {"document_id": document_id, "params": {}}
        text = path.read_text(encoding="utf-8", errors="ignore")
        params: Dict[str, Any] = {}

        m = re.search(r"\bDN\s*(\d+)\b", text, re.IGNORECASE)
        if m:
            params["dn"] = {"value": int(m.group(1)), "confidence": 1.0}
        m = re.search(r"\bPN\s*([\d]+(?:[.,]\d+)?)\b", text, re.IGNORECASE)
        if m:
            val = float(m.group(1).replace(",", "."))
            params["pn"] = {"value": val, "confidence": 1.0}
        m = re.search(r"угол(?: наклона)?\s*(\d+)\s*град", text, re.IGNORECASE)
        if not m:
            m = re.search(r"(\d+)\s*градус", text, re.IGNORECASE)
        if m:
            params["angle"] = {"value": int(m.group(1)), "confidence": 1.0}
        m = re.search(r"толщин[ау]\s*стенки\s*(\d+(?:[.,]\d+)?)", text, re.IGNORECASE)
        if m:
            params["wall_thickness"] = {"value": float(m.group(1).replace(",", ".")), "confidence": 1.0}
        m = re.search(r"М(?:атериал|арка)\s*(?:сталь\s*)?[:\s]*([\wА-Яа-я0-9]+)", text, re.IGNORECASE)
        if m:
            params["material"] = {"value": m.group(1), "confidence": 1.0}
        m = re.search(r"Рабочая\s+среда:\s*([^\n\r\.]+)", text, re.IGNORECASE)
        if m:
            params["medium"] = {"value": m.group(1).strip(), "confidence": 0.8}

        return {"document_id": document_id, "params": params, "path": str(path)}

    def _find_passport(self, document_id: str) -> Optional[Path]:
        d = _sample_docs_dir()
        if not d.exists():
            return None
        if (d / f"{document_id}.md").exists():
            return d / f"{document_id}.md"
        for p in d.glob("*.md"):
            if document_id in p.stem:
                return p
        return None

    # =======================================================================
    # СКЛАД
    # =======================================================================
    def get_stock_batch(self, ksm_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for ksm in ksm_codes:
            card = self.repo.get_card_by_ksm(ksm)
            if card is not None:
                result[ksm] = self.to_stock_item(ksm, card)
        return result

    def get_low_stock_items(self, threshold: float) -> List[Dict[str, Any]]:
        return [
            item
            for item in self._all_stock_items()
            if item["quantity"] is not None and item["quantity"] < threshold
        ]

    def _all_stock_items(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for card in self.repo.get_catalog():
            ksm = (card.get("codes") or {}).get("ksm_code")
            if not ksm:
                continue
            items.append(self.to_stock_item(ksm, card))
        return items

    # =======================================================================
    # ГРАФ
    # =======================================================================
    def get_unit_inventory(self, unit_code: str) -> List[Dict[str, Any]]:
        """Компоненты участка, обогащённые карточкой и остатком."""
        comps = self.repo.get_components_by_unit(unit_code)
        return [self._enrich_component(comp) for comp in comps]

    def get_uninstalled_components(self) -> List[str]:
        installed = self._installed_ksm_set()
        return [
            (card.get("codes") or {}).get("ksm_code")
            for card in self.repo.get_catalog()
            if (card.get("codes") or {}).get("ksm_code") not in installed
        ]

    def is_installed_anywhere(self, ksm_code: str) -> bool:
        return ksm_code in self._installed_ksm_set()

    def get_neighbors(
        self, ksm_code: str, depth: int = 1, direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """Соседи по участку (BFS). Связи на основе графа объекта."""
        depth = max(1, min(int(depth), NEIGHBOR_DEPTH_MAX))
        if direction not in ("upstream", "downstream", "both"):
            direction = "both"

        cache = getattr(self.repo, "_cache", None)
        cache_key = f"neighbors:{ksm_code}:{depth}:{direction}"
        if cache is not None:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        by_ksm: Dict[str, Dict[str, Any]] = {}
        for comp in self.repo.get_graph().get("components", []):
            ksm = comp.get("ksm_code")
            if ksm:
                by_ksm.setdefault(ksm, comp)

        if ksm_code not in by_ksm:
            return []

        adjacency = self._build_adjacency(by_ksm)
        visited = {ksm_code}
        frontier = [ksm_code]
        result: List[Dict[str, Any]] = []
        for _ in range(depth):
            nxt: List[str] = []
            for node in frontier:
                for neighbor in adjacency.get(node, []):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    nxt.append(neighbor)
                    comp = by_ksm[neighbor]
                    result.append(self._neighbor_info(neighbor, comp, direction))
            frontier = nxt
        if cache is not None and result:
            cache.set(cache_key, result)
        return result

    def _build_adjacency(self, by_ksm: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        adjacency: Dict[str, List[str]] = {}
        units: Dict[str, List[str]] = {}
        for ksm, comp in by_ksm.items():
            unit = comp.get("unit_id")
            if unit:
                units.setdefault(unit, []).append(ksm)
        for comp in by_ksm.values():
            unit = comp.get("unit_id")
            key = comp.get("ksm_code")
            if not unit or not key:
                continue
            adjacency.setdefault(key, [])
            for other in units.get(unit, []):
                if other != key:
                    adjacency[key].append(other)
        return adjacency

    @staticmethod
    def _neighbor_info(ksm: str, comp: Dict[str, Any], direction: str) -> Dict[str, Any]:
        kind = comp.get("item_type", "")
        if direction == "upstream":
            conn = "upstream"
        elif direction == "downstream":
            conn = "downstream"
        else:
            conn = "pipeline"
        return {
            "ksm_code": ksm,
            "item_type": kind,
            "connection_type": conn,
            "distance_m": 0.0,
        }

    def _installed_ksm_set(self) -> set:
        return {
            comp.get("ksm_code")
            for comp in self.repo.get_graph().get("components", [])
            if comp.get("ksm_code")
        }

    def _enrich_component(self, comp: Dict[str, Any]) -> Dict[str, Any]:
        ksm = comp.get("ksm_code")
        card = self.repo.get_card_by_ksm(ksm) if ksm else None
        component = self.to_component(card) if card else self._comp_to_component(comp)
        stock = self.to_stock_item(ksm, card) if (card and ksm) else None
        return {
            "component": component,
            "match_score": 0.0,
            "stock": stock,
            "compatibility": None,
            "neighbors": [],
            "extracted_params": None,
            "warnings": [],
            "graph_component_id": comp.get("component_id"),
            "unit_id": comp.get("unit_id"),
            "operating_medium": comp.get("operating_medium"),
            "compatibility_status": comp.get("compatibility_status"),
        }

    @staticmethod
    def _comp_to_component(comp: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ksm_code": comp.get("ksm_code"),
            "mtr_code": None,
            "card_id": comp.get("installed_card_id"),
            "item_type": comp.get("item_type", ""),
            "subtype": None,
            "name": comp.get("designation") or comp.get("ksm_code"),
            "designation": comp.get("designation"),
            "attributes": {},
            "gost_tu": None,
            "standard": None,
            "stock_qty": 0.0,
            "unit": "pcs",
            "is_synthetic": False,
            "match_score": 0.0,
            "matched_fields": [],
            "sources": [],
        }

    # =======================================================================
    # СОВМЕСТИМОСТЬ
    # =======================================================================
    def check_compatibility(
        self, card: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        medium = (context.get("medium") or "").replace("h2s", "H2S")
        medium_l = medium.lower()
        warnings: List[str] = []
        actions: List[str] = []
        score = 1.0

        if "h2s" in medium_l:
            confirmed = bool(_prop(card, "h2s_confirmed", False))
            if not confirmed:
                warnings.append("Пригодность к H2S не подтверждена")
                actions.append("требуется паспорт изделия / ТУ / сертификат")
                score -= 0.4
        if "co2" in medium_l:
            confirmed = bool(_prop(card, "co2_confirmed", False))
            if not confirmed:
                warnings.append("Пригодность к CO2 не подтверждена")
                actions.append("требуется паспорт изделия / ТУ")
                score -= 0.3

        pn = _prop(card, "pn")
        ctx_pn = context.get("pn")
        if pn is not None and ctx_pn is not None and ctx_pn > pn:
            warnings.append(f"PN {ctx_pn} превышает PN изделия {pn}")
            actions.append("подобрать изделие с PN >= требуемого")
            score -= 0.5

        card_med = _prop(card, "medium") or _prop(card, "medium_code")
        if card_med and medium_l and not _contains(card_med, medium_l):
            warnings.append(f"Рабочая среда изделия ('{card_med}') не совпадает с контекстом")
            actions.append("уточнить пригодность материала к среде")
            score -= 0.2

        compatible = score >= 0.5
        if compatible and score < 1.0:
            warnings.append("Требуется экспертная проверка")
            actions.append("экспертная проверка")
        return {
            "compatible": compatible,
            "warnings": warnings,
            "required_actions": actions,
            "source": "compatibility_rules",
            "confidence": max(0.0, round(score, 2)),
        }

    def check_compatibility_batch(
        self, ksm_codes: List[str], context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for ksm in ksm_codes:
            card = self.repo.get_card_by_ksm(ksm)
            if card is None:
                result[ksm] = {
                    "compatible": False,
                    "warnings": [f"{ksm} не найден в каталоге"],
                    "required_actions": [],
                    "source": "compatibility_rules",
                    "confidence": 0.0,
                }
                continue
            result[ksm] = self.check_compatibility(card, context)
        return result

    # =======================================================================
    # НОРМАТИВЫ
    # =======================================================================
    def search_norms(self, query: str, limit: int = 5, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Поиск нормативов.

        Источник Шага 3 — Qdrant (векторный), при недоступности/пустой
        коллекции — полнотекстовый токен-матчер по фрагментам (legacy).
        """
        repo_method = getattr(self.repo, "search_norms", None)
        if repo_method is not None:
            try:
                result = repo_method(query, limit=limit, document_type=document_type)
            except Exception:
                result = None
            if result is not None:
                return self._decorate_lnd_fragments(list(result))

        tokens = self._tokens(query)
        scored: List[Dict[str, Any]] = []
        for frag in self._norm_fragments():
            if document_type and frag["document_type"] != document_type:
                continue
            text = f"{frag['title']} {frag['text']}".lower()
            hits = sum(1 for t in tokens if t in text)
            if hits:
                scored.append({**frag, "score": hits})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return self._decorate_lnd_fragments(scored[: limit])

    @staticmethod
    def _lnd_section_label(frag: Dict[str, Any]) -> str:
        """Метка раздела ЛНД: «раздел 4/глава 2/пункт 3» из текста фрагмента.

        P1-14: типизированный lnd_section для источников kind=lnd. Если
        в строке ЛНД раздела нет — запасной идентификатор фрагмента.
        """
        text = f"{frag.get('title') or ''} {frag.get('text') or ''}"
        m = re.search(
            r"\b(?:раздел\w*|главе?\w*|пункт\w*|параграф\w*|част\w*)\s+[\d\.\-]+",
            text,
            re.IGNORECASE,
        )
        if m:
            label = m.group(0).strip().lower()
            head, _, tail = label.partition(" ")
            norm = _LND_SECTION_HEAD_NORM.get(head, head)
            return f"{norm} {tail}".strip()
        return str(frag.get("fragment_id") or "")

    @classmethod
    def _decorate_lnd_fragments(cls, fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Проставляет lnd_section ЛНД-фрагментам (search_norms, P1-14)."""
        for frag in fragments:
            if frag.get("document_type") == "ЛНД" and "lnd_section" not in frag:
                frag["lnd_section"] = cls._lnd_section_label(frag)
        return fragments

    def _norm_fragments(self) -> List[Dict[str, Any]]:
        fragments: List[Dict[str, Any]] = []
        reg = self.repo.get_regulation()

        for i, lim in enumerate(reg.get("important_limitations", [])):
            fragments.append({
                "fragment_id": f"REG-LIM-{i + 1:03d}",
                "document_id": "regulation_matrix.json",
                "document_type": "ЛНД",
                "title": "Важное ограничение (матрица нормативов)",
                "text": lim,
                "source": "regulation_matrix.json",
            })
        for i, prof in enumerate(reg.get("medium_profiles", [])):
            fragments.append({
                "fragment_id": f"REG-MED-{i + 1:03d}",
                "document_id": "regulation_matrix.json",
                "document_type": "ЛНД",
                "title": f"Профиль среды: {prof.get('name')}",
                "text": "Требуемые подтверждения: " + ", ".join(prof.get("required_evidence", [])),
                "source": "regulation_matrix.json",
            })
        for i, std in enumerate(reg.get("replaced_standards", [])):
            fragments.append({
                "fragment_id": f"REG-STD-{i + 1:03d}",
                "document_id": "regulation_matrix.json",
                "document_type": "ГОСТ",
                "title": f"Замена стандарта {std.get('standard')}",
                "text": f"{std.get('standard')} → {std.get('replacement')} ({std.get('status')})",
                "source": "regulation_matrix.json",
            })

        lnd = self._load_lnd_lines()
        fragments.extend(lnd)
        return fragments

    def _load_lnd_lines(self) -> List[Dict[str, Any]]:
        path = _sample_lnd_path()
        result: List[Dict[str, Any]] = []
        if not path.exists():
            return result
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines()):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                doc_type = "ЛНД"
                if "ГОСТ" in line:
                    doc_type = "ГОСТ"
                elif "ТУ " in line or line.startswith("ТУ"):
                    doc_type = "ТУ"
                result.append({
                    "fragment_id": f"LND-{i + 1:04d}",
                    "document_id": "lnd_extract.md",
                    "document_type": doc_type,
                    "title": doc_type,
                    "text": line,
                    "source": str(path),
                })
        except OSError:
            log.warning("ToolDAL: не удалось прочитать %s", path)
        return result

    @staticmethod
    def _tokens(query: str) -> List[str]:
        words = re.findall(r"[\wА-Яа-яёЁ]+", query.lower())
        return [w for w in words if len(w) > 1]

    # =======================================================================
    # ИСТОРИЯ
    # =======================================================================
    def get_component_history(self, ksm_code: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """История изменений атрибутов.

        Источник Шага 3 — mtr_item_history (PostgreSQL). Если провайдер
        отсутствует/пусто — возвращается пустой список (как в JSON-режиме).
        """
        repo_method = getattr(self.repo, "get_component_history", None)
        if repo_method is not None:
            try:
                result = repo_method(ksm_code, limit=limit, offset=offset)
            except Exception:
                result = []
            if result:
                return result
        return []

    def close(self) -> None:
        self.repo.close()
