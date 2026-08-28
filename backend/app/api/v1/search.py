import logging

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.api.deps.auth import get_current_user
from app.core.exceptions import AppException
from app.models.pydantic.schemas import SearchRequest, SearchResponse, ClarifyRequest, ClarifyResponse
from app.services.search_service import SearchService

router = APIRouter()
log = logging.getLogger("mtr.search")


@router.post("/clarify", response_model=ClarifyResponse)
def clarify(
    body: ClarifyRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Диалоговое уточнение (1G): до 3 циклов, затем REQUIRES_EXPERT."""
    from app.services.agent.parsing.hybrid_parser import HybridParser
    from app.services.agent.intent.clarify import (
        RequireClarification,
        get_clarification_manager,
    )
    from app.services.agent.intent.detect import enrich_parsed

    manager = get_clarification_manager()
    try:
        parsed = HybridParser().parse(body.query)
        enrich_parsed(parsed)
        decision = manager.process(body.session_id, parsed, body.query)
        if decision == "proceed":
            merged = manager.accumulated_text(body.session_id) or body.query
            svc = SearchService(db)
            answer = svc.execute_search(
                SearchRequest(query=merged, mode="deterministic"),
                user_id=None,
            )
            return ClarifyResponse(
                session_id=body.session_id,
                route="answer",
                turn=manager.turns(body.session_id),
                status=getattr(parsed, "status", "COMPLETE"),
                answer=answer,
            )
        # 'expert' после max_turns (1G.4)
        return ClarifyResponse(
            session_id=body.session_id,
            route="expert",
            turn=manager.turns(body.session_id),
            status="REQUIRES_EXPERT",
            message=(
                "Недостаточно данных для выполнения запроса. "
                "Обратитесь к эксперту."
            ),
        )
    except RequireClarification as rc:
        return ClarifyResponse(
            session_id=rc.session_id,
            route="clarification",
            turn=rc.turn,
            question=rc.question,
            missing=rc.missing,
            status=rc.status,
        )
    except AppException:
        raise
    except Exception as e:
        log.exception("CLARIFY FAILED: %s", e)
        from app.core.exceptions import InternalError
        raise InternalError(f"Clarify failed: {e}")


class SearchHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    request_id: str
    query: str
    mode: str
    status: str
    results_count: int = 0
    results: list | None = None
    warnings: list | None = None
    created_at: str | None = None


@router.post("/", response_model=SearchResponse)
def search(
    body: SearchRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    log.info("SEARCH REQUEST: query=%r mode=%s", body.query, body.mode)
    user_id = None
    if authorization:
        try:
            user = get_current_user(authorization=authorization, db=db)
            user_id = str(user["id"])
        except Exception:
            log.warning("Search without valid auth; history will be anonymous")

    try:
        svc = SearchService(db)
        result = svc.execute_search(body, user_id=user_id)
        log.info(
            "SEARCH RESPONSE: status=%s results=%d warnings=%d requires_expert=%s",
            result.status,
            len(result.results or []),
            len(result.warnings or []),
            result.requires_expert,
        )
        return result
    except AppException:
        raise
    except Exception as e:
        log.exception("SEARCH FAILED: %s", e)
        from app.core.exceptions import InternalError
        raise InternalError(f"Search failed: {e}")


@router.get("/history", response_model=list[SearchHistoryItem])
def search_history(
    limit: int = 20,
    offset: int = 0,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        return []
    try:
        from app.models.sqlalchemy.all_models import Log

        user = get_current_user(authorization=authorization, db=db)
        logs = (
            db.query(Log)
            .filter(Log.user_id == str(user["id"]), Log.action == "search")
            .order_by(Log.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        results = log.data.get("results", []) if log.data else []
        return [
            SearchHistoryItem(
                id=log.id,
                request_id=str(log.request_id) if log.request_id else "",
                query=log.data.get("query", "") if log.data else "",
                mode=log.data.get("mode", "deterministic") if log.data else "deterministic",
                status="ok",
                results_count=len(results),
                results=results,
                warnings=log.data.get("warnings", []) if log.data else [],
                created_at=log.created_at.isoformat() if log.created_at else None,
            )
            for log in logs
        ]
    except Exception:
        return []
