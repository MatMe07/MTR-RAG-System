import json
import logging
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.pydantic.schemas import SearchRequest, SearchResponse

log = logging.getLogger("mtr.search.service")


def _to_json_safe(obj: Any) -> Any:
    """Рекурсивно приводит объект к JSON-безопасному виду."""
    return json.loads(json.dumps(obj, ensure_ascii=False, default=str))


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def execute_search(self, request: SearchRequest, user_id: str | None = None) -> SearchResponse:
        from app.services.agent.executor import AgentExecutor
        from app.services.audit_service import AuditService

        start = time.time()
        log.info("[SearchService] Starting search: query=%r mode=%s", request.query, request.mode)

        try:
            executor = AgentExecutor()
            log.info("[SearchService] AgentExecutor created")

            answer = executor.execute(request.query)
            elapsed = (time.time() - start) * 1000

            log.info(
                "[SearchService] Agent finished: intent=%s mode=%s tools=%s components=%d warnings=%d",
                getattr(answer, "intent", "?"),
                getattr(answer, "mode", "?"),
                getattr(answer, "tools_used", []),
                len(getattr(answer, "components", []) or []),
                len(getattr(answer, "warnings", []) or []),
            )

            request_id = str(uuid.uuid4())

            from app.services.agent.answer.tz_result import build_tz_result_items
            from app.services.agent.answer.status import STATUS_NOT_FOUND, STATUS_UNCLEAR

            answer_status = (
                getattr(answer, "status", "") or STATUS_UNCLEAR
            )
            response = SearchResponse(
                request_id=request_id,
                query=request.query,
                mode=getattr(answer, "mode", None) or "deterministic",
                status=answer_status if answer_status else STATUS_NOT_FOUND,
                results=build_tz_result_items(answer),
                warnings=answer.warnings or [],
                recommendations=getattr(answer, "recommendations", None) or [],
                requires_expert=answer.human_review_required,
                expert_review_id=getattr(answer, "expert_review_id", None),
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            log.exception("[SearchService] Agent FAILED after %.0fms: %s", elapsed, e)
            raise

        try:
            audit = AuditService(db=self.db)
            audit.log(
                request_id=response.request_id,
                user_id=user_id,
                action="search",
                data={
                    "query": request.query,
                    "mode": getattr(request, "mode", "default"),
                    "results": _to_json_safe(response.results or []),
                    "warnings": _to_json_safe(response.warnings or []),
                },
            )
        except Exception:
            pass

        return response
