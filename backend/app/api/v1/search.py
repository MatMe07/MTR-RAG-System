import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.pydantic.schemas import ClarifyRequest, ClarifyResponse, SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()
log = logging.getLogger("mtr.search")


@router.post("/clarify", response_model=ClarifyResponse)
def clarify(
    body: ClarifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Диалоговое уточнение (1G): до 3 циклов, затем REQUIRES_EXPERT."""
    from app.services.agent.intent.clarify import (
        RequireClarification,
        get_clarification_manager,
    )
    from app.services.agent.intent.detect import enrich_parsed
    from app.services.agent.parsing.hybrid_parser import HybridParser

    manager = get_clarification_manager()
    try:
        parsed = HybridParser().parse(body.query)
        enrich_parsed(parsed)
        decision = manager.process(body.session_id, parsed, body.query)
        if decision == "proceed":
            merged = manager.accumulated_text(body.session_id) or body.query
            turn = manager.turns(body.session_id)
            status = getattr(parsed, "status", "COMPLETE")
            manager.reset(body.session_id)
            svc = SearchService(db)
            answer = svc.execute_search(
                SearchRequest(query=merged, mode="deterministic"),
                user_id=str(current_user["id"]),
            )
            return ClarifyResponse(
                session_id=body.session_id,
                route="answer",
                turn=turn,
                status=status,
                answer=answer,
            )
        # 'expert' после max_turns (1G.4)
        turn = manager.turns(body.session_id)
        manager.reset(body.session_id)
        return ClarifyResponse(
            session_id=body.session_id,
            route="expert",
            turn=turn,
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log.info(
        "SEARCH REQUEST: query=%r mode=%s user=%s",
        body.query, body.mode, current_user["id"],
    )

    try:
        svc = SearchService(db)
        result = svc.execute_search(body, user_id=str(current_user["id"]))
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        from app.models.sqlalchemy.all_models import Log

        logs = (
            db.query(Log)
            .filter(Log.user_id == str(current_user["id"]), Log.action == "search")
            .order_by(Log.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items: list[SearchHistoryItem] = []
        for row in logs:
            data = row.data or {}
            results = data.get("results", [])
            items.append(
                SearchHistoryItem(
                    id=row.id,
                    request_id=str(row.request_id) if row.request_id else "",
                    query=data.get("query", ""),
                    mode=data.get("mode", "deterministic"),
                    status="ok",
                    results_count=len(results),
                    results=results,
                    warnings=data.get("warnings", []),
                    created_at=row.created_at.isoformat() if row.created_at else None,
                )
            )
        return items
    except AppException:
        raise
    except Exception:
        return []
