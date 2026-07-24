# backend/app/main.py

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import shutil
import os

from app.database import get_db
from app.schemas import (
    SearchRequest, SearchResponse, MatchResult,
    ExpertReviewRequest, ItemCard
)
from app.services.search_service import SearchService
from app.services.rules_engine import RulesEngine
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.expert_service import ExpertService

app = FastAPI(
    title="MTR Search System",
    description="Система интеллектуального подбора МТР",
    version="0.1.0"
)

UPLOAD_DIR = "uploads/passports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
print("llm and embeddings")
llm = LLMService()
embeddings = EmbeddingService()

def get_search_service(db: Session = Depends(get_db)):
    rules = RulesEngine(db)
    return SearchService(db, rules, llm, embeddings)


def get_expert_service(db: Session = Depends(get_db)):
    return ExpertService(db)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service)
):
    try:
        # print('hello')
        return search_service.search(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/passport")
async def upload_passport(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Загружает PDF-паспорт.
    Для MVP: сохраняет файл, создает запись в БД, возвращает document_id.
    OCR пока заглушка.
    """
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    from app.models import Document
    doc = Document(
        file_name=file.filename,
        file_type="passport",
        page_count=1,
        ocr_status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "success": True,
        "document_id": doc.id,
        "message": f"Файл {file.filename} загружен",
        "file_path": file_path
    }


@app.post("/match", response_model=MatchResult)
async def match(
    requested_card: ItemCard,
    candidate_card: ItemCard,
    db: Session = Depends(get_db)
):
    """
    Сравнивает две карточки.
    """
    rules = RulesEngine(db)
    result = rules.evaluate(requested_card, candidate_card)
    return MatchResult(
        rank=1,
        mtr_code=candidate_card.mtr_code or "",
        ksm_code=candidate_card.ksm_code,
        candidate_name=candidate_card.name or candidate_card.designation or "",
        status=result["status"],
        match_percent=result["match_percent"],
        matched_params=result["matched_params"],
        mismatched_params=result["mismatched_params"],
        missing_params=result["missing_params"],
        warnings=result["warnings"],
        expert_comment=result["expert_comment"],
        rule_trace=result["rule_trace"],
        sources=[]
    )


@app.post("/expert-review")
async def expert_review(
    request: ExpertReviewRequest,
    expert_service: ExpertService = Depends(get_expert_service)
):
    return expert_service.save_review(request)


@app.get("/expert-history")
async def expert_history(
    ksm_code: str = None,
    limit: int = 50,
    expert_service: ExpertService = Depends(get_expert_service)
):
    return expert_service.get_review_history(ksm_code, limit)


@app.get("/expert-stats")
async def expert_stats(
    expert_service: ExpertService = Depends(get_expert_service)
):
    return expert_service.get_stats()
