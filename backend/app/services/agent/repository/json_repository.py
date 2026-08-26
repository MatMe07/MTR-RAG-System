# agent/repository/json_repository.py

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import IRepository
from ..core.exceptions import RepositoryError


class JsonRepository(IRepository):
    """JSON-репозиторий (демо-данные)"""
    
    def __init__(self):
        self._catalog_cache: Optional[List[Dict[str, Any]]] = None
        self._by_ksm_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._by_id_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._graph_cache: Optional[Dict[str, Any]] = None
        self._regulation_cache: Optional[Dict[str, Any]] = None
        self._components_by_unit: Optional[Dict[str, List[Dict]]] = None
        
        self._catalog_path = self._get_path("data/catalog/regulated_mtr_catalog_1000.jsonl")
        self._graph_path = self._get_path("data/graph/gas_pipeline_object.json")
        self._regulation_path = self._get_path("data/regulation/regulation_matrix.json")
    
    def _get_path(self, relative_path: str) -> Path:
        """Получение пути к файлу"""
        # Ищем от корня проекта
        for base in [Path(__file__).parents[5], Path.cwd()]:
            path = base / relative_path
            if path.exists():
                return path
        
        # Если не найдено — создаём fallback
        fallback = Path.cwd() / relative_path
        return fallback
    
    def get_catalog(self) -> List[Dict[str, Any]]:
        if self._catalog_cache is None:
            self._catalog_cache = self._load_catalog()
            self._build_indexes()
        return self._catalog_cache
    
    def get_card_by_ksm(self, ksm: str) -> Optional[Dict[str, Any]]:
        if not ksm:
            return None
        if self._by_ksm_cache is None:
            self.get_catalog()
        return self._by_ksm_cache.get(ksm)
    
    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        if not card_id:
            return None
        if self._by_id_cache is None:
            self.get_catalog()
        return self._by_id_cache.get(card_id)
    
    def get_stock_quantity(self, ksm: str) -> Optional[float]:
        card = self.get_card_by_ksm(ksm)
        if not card:
            return None
        return self._prop(card, "stock_qty")
    
    def get_stock_cost(self, ksm: str) -> Optional[float]:
        return None
    
    def get_graph(self) -> Dict[str, Any]:
        if self._graph_cache is None:
            self._graph_cache = self._load_graph()
            self._build_graph_indexes()
        return self._graph_cache
    
    def get_components_by_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        if self._components_by_unit is None:
            self.get_graph()
        return self._components_by_unit.get(unit_id, [])
    
    def get_regulation(self) -> Dict[str, Any]:
        if self._regulation_cache is None:
            self._regulation_cache = self._load_regulation()
        return self._regulation_cache
    
    def search_candidates(self, parsed: Any, limit: int = 40) -> List[Dict[str, Any]]:
        from ..tools.core_tools import _matches_filters, _match_score
        
        matches = []
        for card in self.get_catalog():
            if _matches_filters(card, parsed):
                score = _match_score(card, parsed)
                matches.append({"card": card, "score": score})
        
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]
    
    def close(self) -> None:
        pass
    
    def _load_catalog(self) -> List[Dict[str, Any]]:
        cards = []
        try:
            if not self._catalog_path.exists():
                return self._load_sample_catalog()
            
            with open(self._catalog_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        cards.append(json.loads(line))
        except Exception as e:
            return self._load_sample_catalog()
        return cards
    
    def _load_sample_catalog(self) -> List[Dict[str, Any]]:
        """Загрузка демо-каталога для тестирования"""
        return [
            {
                "card_id": "MTR-TEST-001",
                "item_type": "отвод",
                "name": "Отвод 90 426x10",
                "designation": "ОКШ90-426x10-К52-09Г2С-УХЛ",
                "codes": {"mtr_code": "MTR-TEST-001", "ksm_code": "KSM-TEST-001"},
                "properties": {
                    "dn": {"value": 426.0},
                    "wall_thickness": {"value": 10.0},
                    "angle": {"value": 90.0},
                    "steel_grade": {"value": "09Г2С"},
                    "strength_class": {"value": "К52"},
                    "stock_qty": {"value": 5.0},
                },
                "dcd": {}
            },
            {
                "card_id": "MTR-TEST-002",
                "item_type": "задвижка",
                "name": "Задвижка DN150 PN16",
                "designation": "ЗД-150-16-УХЛ",
                "codes": {"mtr_code": "MTR-TEST-002", "ksm_code": "KSM-TEST-002"},
                "properties": {
                    "dn": {"value": 150.0},
                    "pn": {"value": 16.0},
                    "steel_grade": {"value": "20"},
                    "stock_qty": {"value": 0.0},
                },
                "dcd": {}
            },
            {
                "card_id": "MTR-TEST-003",
                "item_type": "труба",
                "name": "Труба 108x6",
                "designation": "Труба 108x6-20-УХЛ",
                "codes": {"mtr_code": "MTR-TEST-003", "ksm_code": "KSM-TEST-003"},
                "properties": {
                    "dn": {"value": 108.0},
                    "wall_thickness": {"value": 6.0},
                    "steel_grade": {"value": "20"},
                    "stock_qty": {"value": 12.0},
                },
                "dcd": {}
            }
        ]
    
    def _load_graph(self) -> Dict[str, Any]:
        try:
            if not self._graph_path.exists():
                return self._load_sample_graph()
            with open(self._graph_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self._load_sample_graph()
    
    def _load_sample_graph(self) -> Dict[str, Any]:
        return {
            "units": [
                {"unit_id": "UNIT-SYN-H2S-001", "medium_code": "gas_h2s"},
                {"unit_id": "UNIT-SYN-GAS-001", "medium_code": "natural_gas"},
            ],
            "components": [
                {
                    "component_id": "COMP-SYN-010",
                    "unit_id": "UNIT-SYN-H2S-001",
                    "ksm_code": "KSM-TEST-001",
                    "item_type": "отвод",
                    "designation": "ОКШ90-426x10",
                    "compatibility_status": "confirmed"
                },
                {
                    "component_id": "COMP-SYN-011",
                    "unit_id": "UNIT-SYN-H2S-001",
                    "ksm_code": "KSM-TEST-002",
                    "item_type": "задвижка",
                    "designation": "ЗД-150-16",
                    "compatibility_status": "requires_review"
                }
            ]
        }
    
    def _load_regulation(self) -> Dict[str, Any]:
        try:
            if not self._regulation_path.exists():
                return self._load_sample_regulation()
            with open(self._regulation_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self._load_sample_regulation()
    
    def _load_sample_regulation(self) -> Dict[str, Any]:
        return {
            "important_limitations": [
                "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.",
                "Синтетическая среда в карточке не является подтверждением пригодности изделия к H2S.",
                "Наличие позиции на складе не подтверждает ее пригодность для H2S.",
            ],
            "medium_profiles": [
                {
                    "code": "gas_h2s",
                    "name": "Газ с H2S",
                    "required_evidence": ["паспорт изделия", "ТУ", "сертификат"],
                },
                {
                    "code": "gas_co2",
                    "name": "Газ с CO2",
                    "required_evidence": ["паспорт изделия", "ТУ"],
                }
            ],
            "replaced_standards": [
                {"standard": "ГОСТ 12345-67", "replacement": "ГОСТ 67890-12", "status": "заменён"}
            ]
        }
    
    def _build_indexes(self) -> None:
        self._by_ksm_cache = {}
        self._by_id_cache = {}
        
        for card in self._catalog_cache:
            card_id = card.get("card_id")
            if card_id:
                self._by_id_cache[card_id] = card
            
            ksm = (card.get("codes") or {}).get("ksm_code")
            if ksm:
                self._by_ksm_cache[ksm] = card
    
    def _build_graph_indexes(self) -> None:
        graph = self._graph_cache or {}
        components = graph.get("components", [])
        
        self._components_by_unit = {}
        for comp in components:
            unit_id = comp.get("unit_id")
            if unit_id:
                self._components_by_unit.setdefault(unit_id, []).append(comp)
    
    @staticmethod
    def _prop(card: Dict[str, Any], key: str, default: Any = None) -> Any:
        p = (card.get("properties") or {}).get(key)
        if p is None:
            return default
        return p.get("value", default)
