"""Минимальная консольная версия pipeline поиска (без HTTP).

Запуск:  python app.py   (из каталога backend)
Логика:  запрос → режим (0=deterministic, 1=llm) → полный проход агента
         с выводом всех логов, в конце — ответ в исходном виде.
"""

import logging
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s | %(name)-32s | %(message)s",
    stream=sys.stdout,
)

for _name in ("pymorphy2", "pymorphy2.opencorpora_dict", "natasha", "hnswlib"):
    logging.getLogger(_name).setLevel(logging.WARNING)

from app.models.pydantic.schemas import SearchResponse  # noqa: E402
from app.services.agent.core.config import AgentConfig  # noqa: E402
from app.services.agent.executor import AgentExecutor  # noqa: E402


def run_search(query: str, mode: str) -> SearchResponse:
    config = AgentConfig(use_llm=(mode == "llm"))
    executor = AgentExecutor(config)

    start = time.time()
    answer = executor.execute(query, mode=mode)
    elapsed = (time.time() - start) * 1000

    response = SearchResponse(
        request_id=str(uuid.uuid4()),
        query=query,
        mode=mode,
        status=answer.status or ("ok" if not answer.human_review_required else "requires_expert"),
        results=answer.components or [],
        warnings=answer.warnings or [],
        recommendations=answer.recommendations or [],
        requires_expert=answer.human_review_required,
        expert_review_id=answer.expert_review_id,
        execution_time_ms=elapsed,
    )

    try:
        from app.db.session import SessionLocal
        from app.services.audit_service import AuditService

        db = SessionLocal()
        try:
            AuditService(db=db).log(
                request_id=response.request_id,
                user_id=None,
                action="search",
                data={"query": query, "mode": mode},
            )
        finally:
            db.close()
    except Exception:
        pass

    return response


def main() -> None:
    query = input("Запрос: ").strip()
    while not query:
        query = input("Запрос (не может быть пустым): ").strip()

    mode_raw = input("Метод поиска (0 - deterministic, 1 - llm): ").strip()
    mode = "llm" if mode_raw in ("1", "llm") else "deterministic"
    print(f"\n>>> Режим: {mode}\n")

    response = run_search(query, mode)

    print("\n" + "=" * 72)
    print(">>> ОТВЕТ (как возвращается):")
    print(response)
    print("=" * 72)


if __name__ == "__main__":
    main()
