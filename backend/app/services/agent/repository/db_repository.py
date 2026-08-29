# agent/repository/db_repository.py

import logging
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.sqlalchemy.all_models import MtrItem, CandidateItem, MtrItemHistory
from app.services.agent.tools.core_tools import _matches_filters, _match_score

from .interfaces import IRepository
from .json_repository import JsonRepository

log = logging.getLogger("mtr.repository")


def _safe_prop(card: Dict[str, Any], key: str, default: Any = None) -> Any:
    p = (card.get("properties") or {}).get(key)
    if p is None:
        return default
    return p.get("value", default)


class DbRepository(IRepository):
    """DB-репозиторий (PostgreSQL) с fallback на JSON.

    Шаг 3 «полный стек»: каталог/склад — PG (Redis-кеш), граф — Neo4j с
    fallback на pipeline_edges/JSON, нормативы — Qdrant, паспорта — PG,
    история — mtr_item_history. Каждый источник недоступный по отдельности
    безопасно откатывается на предыдущий.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        *,
        neo4j_provider: Optional[Any] = None,
        norms_provider: Optional[Any] = None,
        passport_provider: Optional[Any] = None,
        redis_cache: Optional[Any] = None,
        access_logger: Optional[Any] = None,
    ):
        self._db = db
        self._owns_db = db is None
        self._json_fallback = JsonRepository()
        self._catalog_cache: Optional[List[Dict[str, Any]]] = None
        self._by_ksm_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._by_id_cache: Optional[Dict[str, Dict[str, Any]]] = None

        from .providers.access_logger import get_data_access_logger
        from .providers.neo4j_provider import Neo4jGraphProvider
        from .providers.norms_provider import NormsProvider
        from .providers.passport_provider import PassportProvider
        from .providers.redis_cache import get_redis_cache

        self._access_logger = access_logger or get_data_access_logger()
        self._cache = redis_cache if redis_cache is not None else get_redis_cache()
        self._graph_provider = neo4j_provider or Neo4jGraphProvider(
            card_lookup=self.get_card_by_ksm, access_logger=self._access_logger
        )
        self._norms_provider = norms_provider if norms_provider is not None else NormsProvider(
            access_logger=self._access_logger
        )
        self._passport_provider = passport_provider or PassportProvider(
            access_logger=self._access_logger
        )

    @contextmanager
    def _session(self):
        if self._db is not None:
            yield self._db
            return

        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _log(self, method: str, provider: str, cache_hit: bool = False, fallback: bool = False, reason: Optional[str] = None) -> None:
        try:
            self._access_logger.record(
                method_name=method,
                provider_used=provider,
                cache_hit=cache_hit,
                fallback_used=fallback,
                fallback_reason=reason,
            )
        except Exception:
            pass

    # ==================================================================== КАТАЛОГ
    def get_catalog(self) -> List[Dict[str, Any]]:
        if self._catalog_cache is not None:
            return self._catalog_cache

        cached = self._cache.get("catalog.json")
        if cached is not None:
            self._catalog_cache = cached
            self._build_indexes()
            self._log("get_catalog", "redis", cache_hit=True)
            return self._catalog_cache

        try:
            with self._session() as db:
                items = db.query(MtrItem).all()
                log.info("DbRepository: loaded %d MTR items from DB", len(items))

                if len(items) == 0:
                    log.warning("DbRepository: mtr_items table is empty, using JSON fallback")
                    raise ValueError("empty DB")

                ksm_map = {}
                for k in db.query(CandidateItem).all():
                    ksm_map[k.ksm_code] = k
                log.info("DbRepository: loaded %d CandidateItems for stock lookup", len(ksm_map))

                cards = []
                for mtr in items:
                    card = self._mtr_to_card(mtr, ksm_map)
                    cards.append(card)

            self._catalog_cache = cards
            self._build_indexes()
            self._cache.set("catalog.json", cards)
            self._log("get_catalog", "postgresql")
            log.info("DbRepository: catalog built with %d cards", len(self._catalog_cache))
            return self._catalog_cache
        except Exception as e:
            log.warning("DbRepository.get_catalog failed: %s, using JSON fallback", e)
            result = self._json_fallback.get_catalog()
            self._catalog_cache = result
            self._build_indexes()
            self._log("get_catalog", "json", fallback=True, reason=str(e))
            log.info("JsonRepository fallback loaded %d cards", len(result))
            return result

    def get_card_by_ksm(self, ksm: str) -> Optional[Dict[str, Any]]:
        if not ksm:
            return None
        if self._by_ksm_cache is None:
            self.get_catalog()
        return self._by_ksm_cache.get(ksm) if self._by_ksm_cache else None

    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        if not card_id:
            return None
        if self._by_id_cache is None:
            self.get_catalog()
        return self._by_id_cache.get(card_id) if self._by_id_cache else None

    # ==================================================================== СКЛАД
    def get_stock_quantity(self, ksm: str) -> Optional[float]:
        cached = self._cache.get(f"stock:qty:{ksm}")
        if cached is not None:
            self._log("get_stock_quantity", "redis", cache_hit=True)
            return cached
        try:
            with self._session() as db:
                item = db.query(CandidateItem).filter(CandidateItem.ksm_code == ksm).first()
                value = float(item.quantity) if item and item.quantity is not None else None
            if value is not None:
                self._cache.set(f"stock:qty:{ksm}", value)
            self._log("get_stock_quantity", "postgresql")
            return value
        except Exception as e:
            self._log("get_stock_quantity", "json", fallback=True, reason=str(e))
            return self._json_fallback.get_stock_quantity(ksm)

    def get_stock_cost(self, ksm: str) -> Optional[float]:
        cached = self._cache.get(f"stock:cost:{ksm}")
        if cached is not None:
            self._log("get_stock_cost", "redis", cache_hit=True)
            return cached
        try:
            with self._session() as db:
                item = db.query(CandidateItem).filter(CandidateItem.ksm_code == ksm).first()
                value = float(item.cost) if item and item.cost is not None else None
            if value is not None:
                self._cache.set(f"stock:cost:{ksm}", value)
            self._log("get_stock_cost", "postgresql")
            return value
        except Exception as e:
            self._log("get_stock_cost", "json", fallback=True, reason=str(e))
            return self._json_fallback.get_stock_cost(ksm)

    # ==================================================================== ГРАФ
    def get_graph(self) -> Dict[str, Any]:
        if self._graph_provider is not None:
            result = self._graph_provider.graph()
            if result is not None:
                return result
        return self._json_fallback.get_graph()

    def get_components_by_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        if self._graph_provider is not None:
            result = self._graph_provider.components_by_unit(unit_id)
            if result:
                return result
        return self._json_fallback.get_components_by_unit(unit_id)

    def get_regulation(self) -> Dict[str, Any]:
        return self._json_fallback.get_regulation()

    # ==================================================================== НОРМАТИВЫ (Qdrant-провайдер; fallback прост)
    def search_norms(
        self, query: str, limit: int = 5, document_type: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Векторный поиск по Qdrant. None — провайдер недоступен/пуст."""
        if self._norms_provider is not None:
            return self._norms_provider.search(query=query, limit=limit, document_type=document_type)
        return None

    # ==================================================================== ПАСПОРТА (PG)
    def get_passport_params(self, document_id: str) -> Optional[Dict[str, Any]]:
        if self._passport_provider is not None:
            return self._passport_provider.get_passport_params(document_id)
        return None

    # ==================================================================== ИСТОРИЯ (PG)
    def get_component_history(
        self, ksm_code: str, limit: int = 10, offset: int = 0
    ) -> List[Dict[str, Any]]:
        card = self.get_card_by_ksm(ksm_code)
        if card is None:
            return []
        mtr_code = (card.get("codes") or {}).get("mtr_code")
        if not mtr_code:
            return []
        try:
            with self._session() as db:
                rows = (
                    db.query(MtrItemHistory)
                    .filter(MtrItemHistory.mtr_code == mtr_code)
                    .order_by(MtrItemHistory.changed_at.desc())
                    .offset(max(0, int(offset)))
                    .limit(max(1, int(limit)))
                    .all()
                )
            self._log("get_component_history", "postgresql")
            result = [
                {
                    "mtr_code": r.mtr_code,
                    "changed_at": r.changed_at.isoformat() if r.changed_at else None,
                    "changed_by": r.changed_by,
                    "old_attributes": r.old_attributes or {},
                    "new_attributes": r.new_attributes or {},
                }
                for r in rows
            ]
            return result
        except Exception as e:
            self._log("get_component_history", "json", fallback=True, reason=str(e))
            return []

    # ==================================================================== ПОИСК
    def search_candidates(self, parsed: Any, limit: int = 40) -> List[Dict[str, Any]]:
        try:
            with self._session() as db:
                items = db.query(MtrItem).all()
                cards = [self._mtr_to_card(m, {}) for m in items]

                matches = []
                for card in cards:
                    if _matches_filters(card, parsed):
                        score = _match_score(card, parsed)
                        matches.append({"card": card, "score": score})

                matches.sort(key=lambda x: x["score"], reverse=True)
            return matches[:limit]
        except Exception as e:
            log.warning("DbRepository.search_candidates failed: %s", e)
            return self._json_fallback.search_candidates(parsed, limit)

    def close(self) -> None:
        if self._graph_provider is not None:
            self._graph_provider.close()
        if self._norms_provider is not None:
            self._norms_provider.close()
        if self._owns_db and self._db is not None:
            self._db.close()

    # ==================================================================== helpers
    def _mtr_to_card(self, mtr, ksm_map: Dict) -> Dict[str, Any]:
        raw = mtr.attributes or {}
        props = {}
        for k, v in raw.items():
            if isinstance(v, dict) and "value" in v:
                props[k] = v
            elif isinstance(v, (int, float, str, bool)):
                props[k] = {"value": v}
            else:
                props[k] = v

        ksm = ksm_map.get(mtr.ksm_code) if mtr.ksm_code else None

        if ksm and ksm.quantity is not None:
            props["stock_qty"] = {"value": float(ksm.quantity), "unit": mtr.unit or "pcs"}
        if ksm and ksm.cost is not None:
            props["cost"] = {"value": float(ksm.cost)}
        if ksm:
            if ksm.stock_category:
                props["stock_category"] = {"value": ksm.stock_category}
            if ksm.business_unit:
                props["business_unit"] = {"value": ksm.business_unit}
            if ksm.planned_involvement_date:
                props["planned_involvement_date"] = {"value": ksm.planned_involvement_date}
            if ksm.forecast_involvement_date:
                props["forecast_involvement_date"] = {"value": ksm.forecast_involvement_date}
            if ksm.stock_balance is not None:
                props["stock_balance"] = {"value": float(ksm.stock_balance)}

        return {
            "card_id": mtr.mtr_code,
            "card_version": 1,
            "lifecycle_status": "draft",
            "item_type": mtr.item_type,
            "subtype": mtr.subtype,
            "name": mtr.name or mtr.designation or mtr.mtr_code,
            "designation": mtr.designation or mtr.name,
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