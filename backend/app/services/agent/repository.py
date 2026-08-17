"""AgentRepository: единый доступ агента к данным.

Три режима (переменная AGENT_STORAGE):
  json — только демо-JSON (каталог, граф, регуляторика из data/);
  db   — PostgreSQL (mtr_items/ksm_items/documents) + Qdrant-семантика;
  auto — пробуем db, при недоступности БД падаем на json (без исключений).

Граф объекта и регуляторика остаются на JSON-файлах (в PG нет таблиц для них)
даже в db-режиме — это осознанное решение до появления object_contexts.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

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


class AgentRepository:
    """Интерфейс данных агента: карточки, склад, граф, регуляторика, документы."""

    kind = "json"

    # ===== Каталог (property-интерфейс как у AgentContext) =====
    @property
    def catalog(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @property
    def by_ksm(self) -> Dict[str, Dict[str, Any]]:
        raise NotImplementedError

    @property
    def by_card_id(self) -> Dict[str, Dict[str, Any]]:
        raise NotImplementedError

    def card_for_component(self, component: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @staticmethod
    def prop(card: Dict[str, Any], key: str, default=None) -> Any:
        p = (card.get("properties") or {}).get(key)
        if p is None:
            return default
        return p.get("value", default)

    def card_ksm(self, card: Dict[str, Any]) -> Optional[str]:
        return (card.get("codes") or {}).get("ksm_code")

    def card_mtr(self, card: Dict[str, Any]) -> Optional[str]:
        return (card.get("codes") or {}).get("mtr_code")

    def card_document(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """Документ карточки: JSON-режим читает dcd, db-режим — таблицы documents."""
        return (card.get("dcd") or {}).get("document") or {}

    # ===== Склад =====
    def stock_qty(self, card: Dict[str, Any]) -> Optional[float]:
        raise NotImplementedError

    def stock_cost(self, card: Dict[str, Any]) -> Optional[float]:
        return None

    # ===== Граф и регуляторика (JSON, общие для всех режимов) =====
    @property
    def graph(self) -> Dict[str, Any]:
        return _json_lite().graph

    @property
    def units_by_id(self) -> Dict[str, Dict[str, Any]]:
        return _json_lite().units_by_id

    @property
    def components_by_unit(self) -> Dict[str, List[Dict[str, Any]]]:
        return _json_lite().components_by_unit

    @property
    def components_by_id(self) -> Dict[str, Dict[str, Any]]:
        return _json_lite().components_by_id

    def components_of_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        return list(self.components_by_unit.get(unit_id, []))

    def installed_ksms(self) -> set:
        """Все КСМ, установленные на участках (для фильтра 'не установлены')."""
        return {comp.get("ksm_code") for comp in self.graph.get("components", [])}

    def unit_medium_code(self, unit_id: str) -> Optional[str]:
        unit = self.units_by_id.get(unit_id)
        return (unit or {}).get("medium_code")

    def medium_profile(self, unit_id: str) -> Optional[Dict[str, Any]]:
        return self.medium_profiles_by_code.get(self.unit_medium_code(unit_id) or "")

    def evidence_for_unit(self, unit_id: str) -> List[str]:
        profile = self.medium_profile(unit_id)
        return list((profile or {}).get("required_evidence", []))

    @property
    def regulation(self) -> Dict[str, Any]:
        return _json_lite().regulation

    @property
    def medium_profiles_by_code(self) -> Dict[str, Dict[str, Any]]:
        return _json_lite().medium_profiles_by_code

    # ===== Поиск (гибрид) и документы — расширяется db-режимом =====
    def search_candidates(self, parsed) -> Optional[List[Dict[str, Any]]]:
        return None

    def documents_for_ksm(self, ksm_code: str) -> Dict[str, Any]:
        return {}

    def close(self) -> None:
        pass


_JSON_LITE = None


def _json_lite():
    """Ленивый AgentContext для графа/регуляторики (общий для репозиториев)."""
    global _JSON_LITE
    if _JSON_LITE is None:
        from .context import AgentContext
        _JSON_LITE = AgentContext()
    return _JSON_LITE


class JsonAgentRepository(AgentRepository):
    """Данные из демо-JSON: текущее поведение AgentContext."""

    kind = "json"

    def __init__(self, context=None):
        self._ctx = context

    def _context(self):
        if self._ctx is None:
            from .context import AgentContext
            self._ctx = AgentContext()
        return self._ctx

    @property
    def catalog(self):
        return self._context().catalog

    @property
    def by_ksm(self):
        return self._context().by_ksm

    @property
    def by_card_id(self):
        return self._context().by_card_id

    def card_for_component(self, component):
        return self.by_card_id().get(component.get("installed_card_id"))

    def stock_qty(self, card):
        return self.prop(card, "stock_qty")


class DbAgentRepository(AgentRepository):
    """Данные из PostgreSQL + семантический поиск в Qdrant.

    Каталог читается из mtr_items/ksm_items (properties JSONB), остатки —
    из ksm_items.quantity/cost, документы — из documents/document_pages/
    extracted_characteristics. Граф и регуляторика — из JSON (см. выше).
    """

    kind = "db"

    def __init__(self, db=None, qdrant=None):
        self._db = db
        self._owns_db = db is None
        self._qdrant = qdrant
        self._catalog: Optional[List[Dict[str, Any]]] = None
        self._by_ksm_map: Optional[Dict[str, Dict[str, Any]]] = None
        self._by_card_map: Optional[Dict[str, Dict[str, Any]]] = None
        self._card_by_db_id: Optional[Dict[int, Dict[str, Any]]] = None
        self._ksm_by_code: Optional[Dict[str, Any]] = None
        self._mtr_by_code: Optional[Dict[str, Any]] = None
        self._mtr_by_ksm: Optional[Dict[str, Any]] = None
        self._json = _json_lite()

    def ping(self) -> bool:
        self._session().execute(__import__("sqlalchemy").text("SELECT 1"))
        return True

    def _session(self):
        if self._db is None:
            from app.database import SessionLocal
            self._db = SessionLocal()
            self._owns_db = True
        return self._db

    # ===== Загрузка каталога из PG =====
    def _mtr_items(self):
        from app.models import MTRItem
        db = self._session()
        return db.query(MTRItem).all()

    def _ksm_map(self):
        if self._ksm_by_code is None:
            from app.models import KSMItem
            self._ksm_by_code = {
                k.ksm_code: k for k in self._session().query(KSMItem).all()
            }
        return self._ksm_by_code

    def _mtr_maps(self):
        if self._mtr_by_code is None:
            self._mtr_by_code = {}
            self._mtr_by_ksm = {}
            for m in self._mtr_items():
                self._mtr_by_code[m.mtr_code] = m
                if m.ksm_code:
                    self._mtr_by_ksm[m.ksm_code] = m
        return self._mtr_by_code, self._mtr_by_ksm

    def _mtr_to_card(self, mtr) -> Dict[str, Any]:
        ksm_map = self._ksm_map()
        props = dict(mtr.properties or {})
        ksm = ksm_map.get(mtr.ksm_code) if mtr.ksm_code else None
        if ksm is not None and ksm.quantity is not None:
            props["stock_qty"] = {"value": ksm.quantity, "unit": ksm.unit or "pcs"}
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
            "sources": [],
            "db_id": mtr.id,
        }

    @property
    def catalog(self):
        if self._catalog is None:
            self._catalog = [self._mtr_to_card(m) for m in self._mtr_items()]
        return self._catalog

    @property
    def by_ksm(self):
        if self._by_ksm_map is None:
            self._by_ksm_map = {
                self.card_ksm(c): c for c in self.catalog if self.card_ksm(c)
            }
        return self._by_ksm_map

    @property
    def by_card_id(self):
        if self._by_card_map is None:
            self._by_card_map = {c["card_id"]: c for c in self.catalog}
        return self._by_card_map

    def card_for_component(self, component):
        return self.by_card_id().get(component.get("installed_card_id"))

    def _card_db_map(self):
        if self._card_by_db_id is None:
            self._card_by_db_id = {
                c.get("db_id"): c for c in self.catalog if c.get("db_id") is not None
            }
        return self._card_by_db_id

    # ===== Склад =====
    def stock_qty(self, card):
        qty = self.prop(card, "stock_qty")
        if qty is not None:
            return qty
        ksm = self.card_ksm(card)
        if not ksm:
            return None
        return getattr(self._ksm_map().get(ksm), "quantity", None)

    def stock_cost(self, card):
        ksm = self.card_ksm(card)
        if not ksm:
            return None
        return getattr(self._ksm_map().get(ksm), "cost", None)

    # ===== Документы из PG =====
    def documents_for_ksm(self, ksm_code):
        _, mtr_by_ksm = self._mtr_maps()
        mtr = mtr_by_ksm.get(ksm_code)
        if mtr is None or mtr.source_document_id is None:
            return {}
        from app.models import Document, DocumentPage, ExtractedCharacteristic
        db = self._session()
        doc = db.query(Document).filter(Document.id == mtr.source_document_id).first()
        if doc is None:
            return {}
        pages = db.query(DocumentPage).filter(
            DocumentPage.document_id == doc.id
        ).order_by(DocumentPage.page_number).all()
        chars = db.query(ExtractedCharacteristic).filter(
            ExtractedCharacteristic.document_id == doc.id
        ).all()
        return {
            "document": {
                "document_id": str(doc.id),
                "document_type": doc.file_type,
                "title": doc.file_name,
            },
            "pages": [{"page_number": p.page_number, "ocr_text": p.ocr_text} for p in pages],
            "characteristics": [
                {"field_name": ch.field_name, "normalized_value": ch.normalized_value}
                for ch in chars
            ],
        }

    def card_document(self, card):
        ksm = self.card_ksm(card)
        if not ksm:
            return {}
        info = self.documents_for_ksm(ksm)
        return info.get("document", {})

    # ===== Гибридный поиск кандидатов =====
    def search_candidates(self, parsed, limit: int = 40):
        from .core_tools import _matches_filters, _match_score
        matched = [c for c in self.catalog if _matches_filters(c, parsed)]
        scored = sorted(
            ((c, _match_score(c, parsed)) for c in matched),
            key=lambda x: x[1], reverse=True,
        )
        candidates = [{"card": c, "score": s} for c, s in scored[:limit]]
        try:
            semantic = self._semantic_candidates(parsed, limit=limit)
        except Exception:  # noqa: BLE001 — Qdrant недоступен — остаёмся на PG-фильтрах
            semantic = []
        if semantic:
            seen = {
                (c["card"].get("codes") or {}).get("ksm_code") or c["card"]["card_id"]
                for c in candidates
            }
            for c in semantic:
                key = (c["card"].get("codes") or {}).get("ksm_code") or c["card"]["card_id"]
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(c)
        return candidates[:limit]

    def _semantic_candidates(self, parsed, limit: int = 40):
        from .core_tools import _matches_filters
        text = (parsed.original_query or "").strip()
        if not text:
            return []
        hits = self.qdrant_search(text, k=50)
        out = []
        for hit in hits:
            card = self._card_db_map().get(hit.get("db_id"))
            if card is None or not _matches_filters(card, parsed):
                continue
            out.append({"card": card, "score": hit.get("score", 0.5),
                        "reason": "семантическое сходство"})
            if len(out) >= limit:
                break
        return out

    def qdrant_search(self, query: str, k: int = 50):
        if self._qdrant is None:
            from .qdrant_search import QdrantCatalogSearch
            self._qdrant = QdrantCatalogSearch()
        return self._qdrant.search(query, k=k)

    # ===== Граф и регуляторика — из JSON =====
    @property
    def graph(self):
        return self._json.graph

    @property
    def units_by_id(self):
        return self._json.units_by_id

    @property
    def components_by_unit(self):
        return self._json.components_by_unit

    @property
    def components_by_id(self):
        return self._json.components_by_id

    @property
    def regulation(self):
        return self._json.regulation

    @property
    def medium_profiles_by_code(self):
        return self._json.medium_profiles_by_code

    def close(self):
        if self._owns_db and self._db is not None:
            try:
                self._db.close()
            except Exception:  # noqa: BLE001
                pass
            self._db = None


def get_agent_repository() -> AgentRepository:
    """Фабрика репозитория по AGENT_STORAGE (json | db | auto)."""
    storage = (os.environ.get("AGENT_STORAGE") or getattr(settings, "AGENT_STORAGE", "auto") or "auto").strip().lower()
    if storage == "json":
        return JsonAgentRepository()
    if storage == "db":
        repo = DbAgentRepository()
        repo.ping()
        return repo
    # auto: пробуем БД, при любой ошибке — JSON.
    try:
        repo = DbAgentRepository()
        repo.ping()
        return repo
    except Exception:  # noqa: BLE001
        return JsonAgentRepository()
