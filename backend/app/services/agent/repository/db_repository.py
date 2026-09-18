# agent/repository/db_repository.py

import logging
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.sqlalchemy.all_models import CandidateItem, MtrItem, MtrItemHistory
from app.services.agent.tools.core_tools import _match_score, _matches_filters

from .interfaces import IRepository
from .json_repository import JsonRepository

log = logging.getLogger("mtr.repository")


def _safe_prop(card: Dict[str, Any], key: str, default: Any = None) -> Any:
    p = (card.get("properties") or {}).get(key)
    if p is None:
        return default
    return p.get("value", default)


def _contains(haystack: Any, needle: str) -> bool:
    if haystack is None:
        return False
    h = str(haystack).strip().lower()
    n = str(needle).strip().lower()
    return bool(h) and bool(n) and (n in h or h in n)


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
        catalog_provider: Optional[Any] = None,
        documents_provider: Optional[Any] = None,
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
        from .providers.catalog_semantic_provider import CatalogSemanticProvider
        from .providers.documents_provider import DocumentsProvider
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
        # Семантический индекс каталога (Qdrant mtr_descriptions) — ленивый
        # fallback поиска; подключается только когда детерминированный поиск пуст.
        # Семантический индекс каталога (Qdrant mtr_descriptions) — ленивый
        # fallback поиска; подключается только когда детерминированный поиск пуст.
        self._catalog_provider = (
            catalog_provider if catalog_provider is not None else CatalogSemanticProvider()
        )

        # Векторный индекс паспортов (Qdrant documents) — для поиска по текстам
        # документов (P2-16). Ленивый провайдер; None/недоступность не роняют конвейер.
        self._documents_provider = (
            documents_provider if documents_provider is not None else DocumentsProvider()
        )

        # Векторный индекс паспортов (Qdrant documents) — для search_documents
        # (P2-16). Ленивый: клиент поднимается при первом поиске; None-провайдер
        # не должен ломать конвейер.
        self._documents_provider = (
            documents_provider if documents_provider is not None else DocumentsProvider()
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

        cached = self._cache.get("catalog:all")
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
            self._cache.set("catalog:all", cards)
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
        cached = self._cache.get("graph:object")
        if cached is not None:
            self._log("get_graph", "redis", cache_hit=True)
            return cached
        if self._graph_provider is not None:
            result = self._graph_provider.graph()
            if result is not None:
                self._cache.set("graph:object", result)
                return result
        return self._json_fallback.get_graph()

    def get_components_by_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        cached = self._cache.get(f"graph:unit:{unit_id}")
        if cached is not None:
            self._log("get_components_by_unit", "redis", cache_hit=True)
            return cached
        if self._graph_provider is not None:
            result = self._graph_provider.components_by_unit(unit_id)
            if result:
                self._cache.set(f"graph:unit:{unit_id}", result)
                return result
        return self._json_fallback.get_components_by_unit(unit_id)

    def get_regulation(self) -> Dict[str, Any]:
        return self._json_fallback.get_regulation()

    # ==================================================================== НОРМАТИВЫ (Qdrant-провайдер; fallback прост)
    def search_norms(
        self, query: str, limit: int = 5, document_type: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Векторный поиск по Qdrant. None — провайдер недоступен/пуст.

        Кешируются только непустые результаты (иначе теряется
        полнотекстовый token-matcher fallback в ToolDAL).
        """
        cache_key = f"norms:{document_type or 'all'}:{query.strip()[:120]}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._log("search_norms", "redis", cache_hit=True)
            return cached
        if self._norms_provider is not None:
            result = self._norms_provider.search(
                query=query, limit=limit, document_type=document_type
            )
            if result:
                self._cache.set(cache_key, result)
            return result
        return None

    def search_documents(self, query: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Векторный поиск по текстам паспортов (Qdrant documents).

        Кеш только непустых результатов, иначе теряется полнотекстовый
        token-matcher fallback в ToolDAL. None — провайдер недоступен/пуст.
        """
        cache_key = f"documents:{query.strip()[:140]}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._log("search_documents", "qdrant_documents", cache_hit=True)
            return cached
        if self._documents_provider is not None:
            result = self._documents_provider.search(query, limit=limit)
            if result:
                self._cache.set(cache_key, result)
            return result
        return None

    # ==================================================================== ПАСПОРТА (PG)
    def get_passport_params(self, document_id: str) -> Optional[Dict[str, Any]]:
        if not document_id:
            return None
        cache_key = f"passport:{document_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._log("get_passport_params", "redis", cache_hit=True)
            return cached
        if self._passport_provider is not None:
            result = self._passport_provider.get_passport_params(document_id)
            if result is not None:
                self._cache.set(cache_key, result)
            return result
        return None

    # ==================================================================== СЕМАНТИКА КАТАЛОГА (Qdrant mtr_descriptions)
    def search_catalog_semantic(
        self, query: str, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """Семантический поиск по описаниям каталога.

        Возвращает [{'card': ..., 'score': ...}] по образцу search_candidates;
        None — провайдер недоступен/пуст/нет карточек.
        """
        if self._catalog_provider is None:
            return None
        hits = self._catalog_provider.search(query, limit=limit)
        if not hits:
            return None
        out: List[Dict[str, Any]] = []
        for h in hits:
            ksm = h.get("ksm_code")
            card = self.get_card_by_ksm(ksm) if ksm else None
            if card is None:
                continue
            out.append({"card": card, "score": h.get("score", 0.0), "source": "vector_fallback"})
        return out or None

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

    # ==================================================================== ПАСПОРТА: связи KSM (Фаза 3)
    def _search_catalog_for_passport(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Поиск в каталоге по одному полю для скоринга паспортных связей."""
        numeric = ("dn", "pn", "angle", "wall_thickness")
        tf = {k: v for k, v in search_params.items() if k in numeric and v is not None}
        parsed = SimpleNamespace(technical_filters=tf, item_types=[])

        out: List[Dict[str, Any]] = []
        for card in self.get_catalog():
            if not _matches_filters(card, parsed):
                continue
            if not self._passport_extra_ok(card, search_params):
                continue
            score = _match_score(card, parsed) or 0.0
            out.append({"card": card, "score": score})
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[: int(search_params.get("limit", 10))]

    def _passport_extra_ok(self, card: Dict[str, Any], search_params: Dict[str, Any]) -> bool:
        """Текстовые поля паспорта (марка стали/среда) — подстрока (аналог
        ToolDAL._extra_filters_ok)."""
        for key, propkey in (("steel_grade", "steel_grade"), ("medium", "medium")):
            want = search_params.get(key)
            if not want:
                continue
            got = (card.get("properties") or {}).get(propkey)
            if isinstance(got, dict):
                got = got.get("value")
            if not _contains(got, str(want)):
                return False
        return True

    def suggest_ksm_links(self, document_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Кандидаты KSM по параметрам паспорта (2B.4 suggest_ksm_links)."""
        if self._passport_provider is None:
            return []
        return self._passport_provider.suggest_ksm_links(
            document_id, limit=limit, catalog_search=self._search_catalog_for_passport
        )

    def link_passport_to_ksm(
        self,
        document_id: str,
        ksm_code: str,
        confidence: float,
        method: str = "semantic",
        needs_review: bool = False,
        reviewed_by: Optional[str] = None,
    ) -> bool:
        """Запись связи паспорт→KSM в document_links."""
        if self._passport_provider is None:
            return False
        return self._passport_provider.link_passport_to_ksm(
            document_id, ksm_code, confidence,
            method=method, needs_review=needs_review, reviewed_by=reviewed_by,
        )

    def get_passport_text(self, document_id: str, page: Optional[int] = None):
        if self._passport_provider is None:
            return None
        return self._passport_provider.get_passport_text(document_id, page=page)

    def get_passport_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Статус обработки паспорта (2C: get_passport_status)."""
        if self._passport_provider is None:
            return None
        return self._passport_provider.get_processing_status(document_id)

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
        if self._catalog_provider is not None:
            self._catalog_provider.close()
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
