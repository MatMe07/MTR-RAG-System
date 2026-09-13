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

    def execute_continue(self, request, user_id: str | None = None) -> SearchResponse:
        """Stateless продолжение после offer_full_llm (вариант a).

        proceed=True  → повтор запроса в mode="llm" (полный C2-анализ, свежий парсинг);
        proceed=False → остановиться на достигнутом: повтор детерминированного ответа.
        """
        mode = "llm" if request.proceed else "deterministic"
        log.info("[SearchService] Continue: session_id=%r query=%r proceed=%s mode=%s",
                 request.session_id, request.query, request.proceed, mode)
        req = SearchRequest(query=request.query, mode=mode)
        return self.execute_search(req, user_id=user_id)

    def execute_search(self, request: SearchRequest, user_id: str | None = None) -> SearchResponse:
        from app.services.agent.executor import AgentExecutor
        from app.services.audit_service import AuditService

        start = time.time()
        request_id = str(uuid.uuid4())
        log.info("[SearchService] Starting search: query=%r mode=%s request_id=%s",
                 request.query, request.mode, request_id)

        try:
            executor = AgentExecutor()
            log.info("[SearchService] AgentExecutor created")

            answer = executor.execute(
                request.query,
                mode=getattr(request, "mode", "deterministic") or "deterministic",
                request_id=request_id,
            )
            elapsed = (time.time() - start) * 1000

            log.info(
                "[SearchService] Agent finished: intent=%s mode=%s tools=%s components=%d warnings=%d",
                getattr(answer, "intent", "?"),
                getattr(answer, "mode", "?"),
                getattr(answer, "tools_used", []),
                len(getattr(answer, "components", []) or []),
                len(getattr(answer, "warnings", []) or []),
            )

            from app.services.agent.answer.status import STATUS_NOT_FOUND, STATUS_UNCLEAR
            from app.services.agent.answer.tz_result import build_tz_result_items

            answer_status = (
                getattr(answer, "status", "") or STATUS_UNCLEAR
            )
            response = SearchResponse(
                request_id=request_id,
                query=request.query,
                mode=getattr(answer, "mode", None) or "deterministic",
                status=answer_status if answer_status else STATUS_NOT_FOUND,
                results=build_tz_result_items(answer),
                explanation=getattr(answer, "explanation", None),
                warnings=answer.warnings or [],
                recommendations=getattr(answer, "recommendations", None) or [],
                requires_expert=answer.human_review_required,
                expert_review_id=getattr(answer, "expert_review_id", None),
                offer_full_llm=getattr(answer, "offer_full_llm", False),
                offer_question=getattr(answer, "offer_question", "") or "",
                offer_endpoint=getattr(answer, "offer_endpoint", None),
                execution_time_ms=elapsed,
                raw_agent_answer=_to_json_safe(answer.model_dump(mode="json")),
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
