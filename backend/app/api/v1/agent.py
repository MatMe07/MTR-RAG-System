import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.pydantic.schemas import ContinueRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()
log = logging.getLogger("mtr.agent_continue")


@router.post("/continue", response_model=SearchResponse)
def continue_search(
    body: ContinueRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Продолжение после offer_full_llm: полный LLM-анализ (proceed=true) либо
    остановка на достигнутом (proceed=false). Stateless — без промежуточного хранения."""
    try:
        svc = SearchService(db)
        result = svc.execute_continue(body, user_id=str(current_user["id"]))
        log.info(
            "AGENT CONTINUE RESPONSE: proceed=%s mode=%s status=%s offer_full_llm=%s",
            body.proceed, result.mode, result.status, result.offer_full_llm,
        )
        return result
    except AppException:
        raise
    except Exception as e:
        log.exception("AGENT CONTINUE FAILED: %s", e)
        from app.core.exceptions import InternalError
        raise InternalError(f"Continue failed: {e}")
