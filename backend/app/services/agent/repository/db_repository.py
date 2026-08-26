# agent/repository/db_repository.py

from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from sqlalchemy.orm import Session

from .interfaces import IRepository
from .json_repository import JsonRepository
from ..core.exceptions import RepositoryConnectionError


class DbRepository(IRepository):
    """DB-репозиторий (PostgreSQL) с fallback на JSON"""
    
    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._owns_db = db is None
        self._json_fallback = JsonRepository()
        self._catalog_cache: Optional[List[Dict[str, Any]]] = None
        self._by_ksm_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._by_id_cache: Optional[Dict[str, Dict[str, Any]]] = None
    
    @contextmanager
    def _session(self):
        """Контекстный менеджер для сессии БД"""
        if self._db is not None:
            yield self._db
            return
        
        try:
            from ....database import SessionLocal
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
        except Exception as e:
            raise RepositoryConnectionError("database") from e
    
    def get_catalog(self) -> List[Dict[str, Any]]:
        if self._catalog_cache is not None:
            return self._catalog_cache
        
        try:
            with self._session() as db:
                from ....models import MTRItem, KSMItem
                
                items = db.query(MTRItem).limit(500).all()
                ksm_map = {
                    k.ksm_code: k for k in db.query(KSMItem).all()
                }
                
                self._catalog_cache = []
                for mtr in items:
                    card = self._mtr_to_card(mtr, ksm_map)
                    self._catalog_cache.append(card)
                
                self._build_indexes()
                return self._catalog_cache
        except Exception:
            return self._json_fallback.get_catalog()
    
    def get_card_by_ksm(self, ksm: str) -> Optional[Dict[str, Any]]:
        if self._by_ksm_cache is None:
            self.get_catalog()
        return self._by_ksm_cache.get(ksm)
    
    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        if self._by_id_cache is None:
            self.get_catalog()
        return self._by_id_cache.get(card_id)
    
    def get_stock_quantity(self, ksm: str) -> Optional[float]:
        try:
            with self._session() as db:
                from ....models import KSMItem
                item = db.query(KSMItem).filter(KSMItem.ksm_code == ksm).first()
                return float(item.quantity) if item and item.quantity is not None else None
        except Exception:
            return self._json_fallback.get_stock_quantity(ksm)
    
    def get_stock_cost(self, ksm: str) -> Optional[float]:
        try:
            with self._session() as db:
                from ....models import KSMItem
                item = db.query(KSMItem).filter(KSMItem.ksm_code == ksm).first()
                return float(item.cost) if item and item.cost is not None else None
        except Exception:
            return None
    
    def get_graph(self) -> Dict[str, Any]:
        return self._json_fallback.get_graph()
    
    def get_components_by_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        return self._json_fallback.get_components_by_unit(unit_id)
    
    def get_regulation(self) -> Dict[str, Any]:
        return self._json_fallback.get_regulation()
    
    def search_candidates(self, parsed: Any, limit: int = 40) -> List[Dict[str, Any]]:
        try:
            with self._session() as db:
                from ....models import MTRItem
                from ..tools.core_tools import _matches_filters, _match_score
                
                items = db.query(MTRItem).limit(200).all()
                cards = [self._mtr_to_card(m, {}) for m in items]
                
                matches = []
                for card in cards:
                    if _matches_filters(card, parsed):
                        score = _match_score(card, parsed)
                        matches.append({"card": card, "score": score})
                
                matches.sort(key=lambda x: x["score"], reverse=True)
                return matches[:limit]
        except Exception:
            return self._json_fallback.search_candidates(parsed, limit)
    
    def close(self) -> None:
        if self._owns_db and self._db is not None:
            self._db.close()
    
    def _mtr_to_card(self, mtr, ksm_map: Dict) -> Dict[str, Any]:
        props = dict(mtr.properties or {})
        ksm = ksm_map.get(mtr.ksm_code) if mtr.ksm_code else None
        
        if ksm and ksm.quantity is not None:
            props["stock_qty"] = {"value": float(ksm.quantity), "unit": ksm.unit or "pcs"}
        
        return {
            "card_id": mtr.mtr_code,
            "card_version": 1,
            "lifecycle_status": "draft",
            "item_type": mtr.item_type,
            "subtype": mtr.subtype,
            "name": mtr.short_text or mtr.designation or mtr.mtr_code,
            "designation": mtr.designation or mtr.short_text,
            "codes": {"mtr_code": mtr.mtr_code, "ksm_code": mtr.ksm_code},
            "properties": props,
            "dcd": {},
            "db_id": mtr.id,
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
