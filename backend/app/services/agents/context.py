"""AgentContext: единый доступ к демонстрационным данным (каталог, граф, регуляторика)."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[4]

CATALOG_PATH = REPO_ROOT / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl"
GRAPH_PATH = REPO_ROOT / "data" / "graph" / "gas_pipeline_object.json"
REGULATION_PATH = REPO_ROOT / "data" / "regulation" / "regulation_matrix.json"

ITEM_TYPE_COLLECTION = {
    "труба": "pipes",
    "отвод": "elbows",
    "переход": "reducers",
    "задвижка": "valves",
    "заглушка": "plugs",
    "тройник": "tees",
}

COLLECTION_ITEM_TYPE = {v: k for k, v in ITEM_TYPE_COLLECTION.items()}

DEFAULT_TARGET_STOCK = 5.0


class AgentContext:
    """Ленивая загрузка и хелперы поверх демонстрационных наборов."""

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
            self._catalog = [
                json.loads(line)
                for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
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

    # ===== Хелперы =====
    @staticmethod
    def prop(card: Dict[str, Any], key: str, default=None) -> Any:
        """Значение свойства карточки: properties[key].value."""
        p = (card.get("properties") or {}).get(key)
        if p is None:
            return default
        return p.get("value", default)

    def card_for_component(self, component: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.by_card_id.get(component.get("installed_card_id"))

    def card_ksm(self, card: Dict[str, Any]) -> Optional[str]:
        return (card.get("codes") or {}).get("ksm_code")

    def card_mtr(self, card: Dict[str, Any]) -> Optional[str]:
        return (card.get("codes") or {}).get("mtr_code")

    def card_document(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """Документ карточки (dcd-режим): паспорт/ТУ по умолчанию из JSON."""
        return (card.get("dcd") or {}).get("document") or {}

    def unit_medium_code(self, unit_id: str) -> Optional[str]:
        unit = self.units_by_id.get(unit_id)
        return (unit or {}).get("medium_code")

    def medium_profile(self, unit_id: str) -> Optional[Dict[str, Any]]:
        return self.medium_profiles_by_code.get(self.unit_medium_code(unit_id) or "")

    def components_of_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        return list(self.components_by_unit.get(unit_id, []))

    def installed_ksms(self) -> set:
        """Все КСМ, установленные на участках (для фильтра 'не установлены')."""
        return {comp.get("ksm_code") for comp in self.graph.get("components", [])}

    def stock_qty(self, card: Dict[str, Any]) -> Optional[float]:
        return self.prop(card, "stock_qty")

    def evidence_for_unit(self, unit_id: str) -> List[str]:
        profile = self.medium_profile(unit_id)
        return list((profile or {}).get("required_evidence", []))


def get_agent_context() -> AgentContext:
    return AgentContext()
