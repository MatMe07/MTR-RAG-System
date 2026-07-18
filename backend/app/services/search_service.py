# backend/app/services/search_service.py

import time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import MTRItem, KSMItem, Document, DocumentPage
from app.schemas import (
    SearchRequest, SearchResponse, MatchResult, ItemCard,
    Geometry, Pressure, Material, Environment, Coating, Normative, Source
)
from app.services.rules_engine import RulesEngine
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService


class SearchService:
    def __init__(
        self,
        db: Session,
        rules_engine: RulesEngine,
        llm_service: LLMService,
        embedding_service: EmbeddingService
    ):
        self.db = db
        self.rules_engine = rules_engine
        self.llm = llm_service
        self.embeddings = embedding_service

    def search(self, request: SearchRequest) -> SearchResponse:
        start_time = time.time()
        
        requested_card = self._parse_query(request.query)
        print(request.mode)
        if request.mode == "exact":
            candidates = self._exact_search(requested_card)
        elif request.mode == "filter":
            candidates = self._filter_search(requested_card)
        elif request.mode == "vector":
            candidates = self._vector_search(request.query)
        elif request.mode == "passport":
            candidates = self._search_by_passport(request.document_id)
        else:
            candidates = self._hybrid_search(requested_card)

        scored = self._evaluate_candidates(requested_card, candidates)
        # print(scored)
        scored.sort(key=lambda x: x.match_percent, reverse=True)

        search_time_ms = (time.time() - start_time) * 1000

        searchresponse = SearchResponse(
            query=request.query,
            requested_card=requested_card,
            candidates=scored[:request.top_k],
            total_found=len(scored),
            search_time_ms=search_time_ms
        )
        print(searchresponse.candidates)
        return searchresponse

    def _parse_query(self, query: str) -> ItemCard:
        # print(self.llm)
        return self.llm.parse_query(query)

    def _exact_search(self, card: ItemCard) -> List[MTRItem]:
        results = []

        if card.mtr_code:
            results = self.db.query(MTRItem).filter(
                MTRItem.mtr_code == card.mtr_code
            ).all()
            if results:
                return results

        if card.ksm_code:
            results = self.db.query(MTRItem).filter(
                MTRItem.ksm_code == card.ksm_code
            ).all()
            if results:
                return results

        if card.designation:
            results = self.db.query(MTRItem).filter(
                MTRItem.designation.ilike(f"%{card.designation}%")
            ).limit(10).all()
            if results:
                return results

        return results

    def _filter_search(self, card: ItemCard) -> List[MTRItem]:
        query = self.db.query(MTRItem)

        if card.item_type:
            query = query.filter(MTRItem.item_type == card.item_type)

        if card.geometry and card.geometry.dn:
            tolerance = card.geometry.dn * 0.1
            query = query.filter(
                MTRItem.dn.between(
                    card.geometry.dn - tolerance,
                    card.geometry.dn + tolerance
                )
            )

        if card.geometry and card.geometry.angle:
            query = query.filter(
                MTRItem.angle.between(
                    card.geometry.angle - 5,
                    card.geometry.angle + 5
                )
            )

        if card.geometry and card.geometry.wall_thickness:
            tolerance = card.geometry.wall_thickness * 0.15
            query = query.filter(
                MTRItem.wall_thickness.between(
                    card.geometry.wall_thickness - tolerance,
                    card.geometry.wall_thickness + tolerance
                )
            )

        if card.pressure and card.pressure.pn:
            tolerance = card.pressure.pn * 0.1
            query = query.filter(
                MTRItem.pressure.between(
                    card.pressure.pn - tolerance,
                    card.pressure.pn + tolerance
                )
            )

        if card.material and card.material.strength_class:
            query = query.filter(MTRItem.strength_class == card.material.strength_class)

        if card.material and card.material.steel_grade:
            query = query.filter(MTRItem.steel_grade == card.material.steel_grade)

        if card.environment and card.environment.medium:
            query = query.filter(MTRItem.medium == card.environment.medium)

        return query.limit(100).all()

    def _vector_search(self, query: str) -> List[MTRItem]:
        results = self.embeddings.search_similar(query, k=50)
        if not results:
            return []
        ids = [r["db_id"] for r in results]
        return self.db.query(MTRItem).filter(MTRItem.id.in_(ids)).all()

    def _hybrid_search(self, card: ItemCard) -> List[MTRItem]:
        exact_results = self._exact_search(card)
        filter_results = self._filter_search(card)
        vector_results = self._vector_search(card.designation or card.name or "")

        combined = {}

        for item in exact_results:
            combined[item.id] = {"item": item, "score": 1.0}

        for item in filter_results:
            if item.id in combined:
                combined[item.id]["score"] = max(combined[item.id]["score"], 0.8)
            else:
                combined[item.id] = {"item": item, "score": 0.8}

        for item in vector_results:
            if item.id in combined:
                combined[item.id]["score"] = max(combined[item.id]["score"], 0.6)
            else:
                combined[item.id] = {"item": item, "score": 0.6}

        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        return [r["item"] for r in sorted_results[:100]]

    def _search_by_passport(self, document_id: int) -> List[MTRItem]:
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return []

        pages = self.db.query(DocumentPage).filter(
            DocumentPage.document_id == document_id
        ).all()

        full_text = "\n".join([p.ocr_text or "" for p in pages])
        if not full_text.strip():
            return []

        card = self.llm.extract_card_from_text(
            full_text,
            {"document_id": document_id, "file_name": doc.file_name}
        )

        return self._hybrid_search(card)

    def _evaluate_candidates(
        self,
        requested_card: ItemCard,
        candidates: List[MTRItem]
    ) -> List[MatchResult]:
        results = []

        for idx, mtr_item in enumerate(candidates):
            candidate_card = self._mtr_to_card(mtr_item)
            evaluation = self.rules_engine.evaluate(requested_card, candidate_card)

            results.append(
                MatchResult(
                    rank=idx + 1,
                    mtr_code=mtr_item.mtr_code,
                    ksm_code=mtr_item.ksm_code,
                    candidate_name=mtr_item.short_text or mtr_item.designation or "",
                    sources=self._get_sources(mtr_item),
                    stock_quantity=self._get_stock_quantity(mtr_item.ksm_code),
                    stock_cost=self._get_stock_cost(mtr_item.ksm_code),
                    status=evaluation["status"],
                    match_percent=evaluation["match_percent"],
                    matched_params=evaluation["matched_params"],
                    mismatched_params=evaluation["mismatched_params"],
                    missing_params=evaluation["missing_params"],
                    warnings=evaluation["warnings"],
                    expert_comment=evaluation["expert_comment"],
                    rule_trace=evaluation["rule_trace"]
                )
            )

        results.sort(key=lambda x: x.match_percent, reverse=True)

        for i, result in enumerate(results):
            result.rank = i + 1

        return results

    def _mtr_to_card(self, mtr: MTRItem) -> ItemCard:
        return ItemCard(
            card_id=str(mtr.id),
            mtr_code=mtr.mtr_code,
            ksm_code=mtr.ksm_code,
            item_type=mtr.item_type or "",
            subtype=mtr.subtype,
            designation=mtr.designation,
            name=mtr.short_text,
            geometry=Geometry(
                dn=mtr.dn,
                wall_thickness=mtr.wall_thickness,
                angle=mtr.angle
            ),
            pressure=Pressure(
                pn=mtr.pressure
            ),
            material=Material(
                steel_grade=mtr.steel_grade,
                strength_class=mtr.strength_class,
                standard=mtr.gost_or_tu
            ),
            environment=Environment(
                medium=mtr.medium,
                climate_version=mtr.climate_version
            ),
            coating=Coating(
                inner_coating=mtr.inner_coating,
                outer_coating=mtr.outer_coating
            ),
            normative=Normative(
                gost_tu=mtr.gost_or_tu
            ),
            sources=[]
        )

    def _get_sources(self, mtr: MTRItem) -> List[Source]:
        sources = []

        if mtr.source_excel_row:
            sources.append(
                Source(
                    type="excel",
                    row=mtr.source_excel_row
                )
            )

        if mtr.source_document_id:
            doc = self.db.query(Document).filter(
                Document.id == mtr.source_document_id
            ).first()
            if doc:
                sources.append(
                    Source(
                        type="passport",
                        file=doc.file_name
                    )
                )

        return sources

    def _get_stock_quantity(self, ksm_code: Optional[str]) -> Optional[float]:
        if not ksm_code:
            return None
        ksm = self.db.query(KSMItem).filter(KSMItem.ksm_code == ksm_code).first()
        return ksm.quantity if ksm else None

    def _get_stock_cost(self, ksm_code: Optional[str]) -> Optional[float]:
        if not ksm_code:
            return None
        ksm = self.db.query(KSMItem).filter(KSMItem.ksm_code == ksm_code).first()
        return ksm.cost if ksm else None
