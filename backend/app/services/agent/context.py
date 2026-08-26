"""AgentContext: внутренний JSON-загрузчик демонстрационных данных.

Фаза 4 рефакторинга: AgentContext — только ленивая загрузка и индексация
демо-JSON (каталог, граф, регуляторика). Хелперы карточек/склада/графа живут
в интерфейсе AgentRepository (repository.py) — тулы работают только через него.
Константы путей и доменные константы также переехали в repository.py.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.logging import get_logger
from ...schemas import CatalogCard

REPO_ROOT = Path(__file__).resolve().parents[4]

CATALOG_PATH = REPO_ROOT / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl"
GRAPH_PATH = REPO_ROOT / "data" / "graph" / "gas_pipeline_object.json"
REGULATION_PATH = REPO_ROOT / "data" / "regulation" / "regulation_matrix.json"

log = get_logger("agent_context")


def _load_catalog() -> List[Dict[str, Any]]:
    """Читает каталог из JSONL с Pydantic-валидацией каждой карточки.

    Невалидные карточки логируются и пропускаются, загрузка не падает.
    """
    cards: List[Dict[str, Any]] = []
    skipped = 0
    for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            card = json.loads(line)
            CatalogCard.model_validate(card)
            cards.append(card)
        except Exception as exc:
            skipped += 1
            cid = None
            try:
                cid = json.loads(line).get("card_id")
            except Exception:
                pass
            log.warning("Каталог: карточка %s пропущена (невалидна): %s", cid, exc)
    if skipped:
        log.warning("Каталог: загружено %d карточек, пропущено невалидных: %d", len(cards), skipped)
    return cards


class AgentContext:
    """Ленивая загрузка и индексация демонстрационных наборов."""

    def __init__(self):
        self._catalog: Optional[List[Dict[str, Any]]] = None
        self._by_card_id: Optional[Dict[str, Dict[str, Any]]] = None
        self._by_ksm: Optional[Dict[str, Dict[str, Any]]] = None
        self._graph: Optional[Dict[str, Any]] = None
        self._units_by_id: Optional[Dict[str, Dict[str, Any]]] = None
        self._components_by_unit: Optional[Dict[str, List[Dict[str, Any]]]] = None
        self._components_by_id: Optional[Dict[str, Dict[str, Any]]] = None
        self._regulation: Optional[Dict[str, Any]] = None
        self._medium_profiles_by_code: Optional[Dict[str, Dict[str, Any]]] = None

    # ===== Загрузка =====
    @property
    def catalog(self) -> List[Dict[str, Any]]:
        if self._catalog is None:
            self._catalog = _load_catalog()
        return self._catalog

    @property
    def by_card_id(self) -> Dict[str, Dict[str, Any]]:
        if self._by_card_id is None:
            self._by_card_id = {c["card_id"]: c for c in self.catalog}
        return self._by_card_id

    @property
    def by_ksm(self) -> Dict[str, Dict[str, Any]]:
        if self._by_ksm is None:
            self._by_ksm = {}
            for c in self.catalog:
                ksm = (c.get("codes") or {}).get("ksm_code")
                if ksm:
                    self._by_ksm[ksm] = c
        return self._by_ksm

    @property
    def graph(self) -> Dict[str, Any]:
        if self._graph is None:
            self._graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        return self._graph

    @property
    def units_by_id(self) -> Dict[str, Dict[str, Any]]:
        if self._units_by_id is None:
            self._units_by_id = {u["unit_id"]: u for u in self.graph.get("units", [])}
        return self._units_by_id

    @property
    def components_by_unit(self) -> Dict[str, List[Dict[str, Any]]]:
        if self._components_by_unit is None:
            self._components_by_unit = {}
            for comp in self.graph.get("components", []):
                self._components_by_unit.setdefault(comp["unit_id"], []).append(comp)
        return self._components_by_unit

    @property
    def components_by_id(self) -> Dict[str, Dict[str, Any]]:
        if self._components_by_id is None:
            self._components_by_id = {
                comp["component_id"]: comp
                for comp in self.graph.get("components", [])
            }
        return self._components_by_id

    @property
    def regulation(self) -> Dict[str, Any]:
        if self._regulation is None:
            self._regulation = json.loads(REGULATION_PATH.read_text(encoding="utf-8"))
        return self._regulation

    @property
    def medium_profiles_by_code(self) -> Dict[str, Dict[str, Any]]:
        if self._medium_profiles_by_code is None:
            self._medium_profiles_by_code = {
                m["code"]: m
                for m in self.regulation.get("medium_profiles", [])
            }
        return self._medium_profiles_by_code


def get_agent_context() -> AgentContext:
    return AgentContext()
