# backend/app/main.py

import os
import shutil
import uuid
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

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
from app.services.ocr_service import get_ocr_service


app = FastAPI(
    title="MTR Search System",
    description="Система интеллектуального подбора МТР",
    version="0.1.0"
)

UPLOAD_DIR = "uploads/passports"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Глобальные сервисы (создаются один раз при старте)
llm = LLMService()
embeddings = EmbeddingService()
ocr = get_ocr_service()


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
        return search_service.search(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/passport")
async def upload_passport(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Загружает PDF-паспорт с OCR-обработкой.
    """
    from app.models import Document, DocumentPage, ExtractedCharacteristic
    import numpy as np
    
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = Document(
        file_name=file.filename,
        file_type="passport",
        page_count=0,
        ocr_status="pending"
    )
    db.add(doc)
    db.flush()

    try:
        pages = ocr.extract_text_from_pdf(file_path)
        
        for page in pages:
            page_record = DocumentPage(
                document_id=doc.id,
                page_number=page['page_number'],
                ocr_text=page['text'],
                ocr_confidence=page['confidence'],
                table_json=page['tables'] if page['tables'] else None
            )
            db.add(page_record)

        doc.page_count = len(pages)
        doc.ocr_status = "done"
        doc.ocr_confidence = np.mean([p['confidence'] for p in pages]) if pages else 0

        full_text = "\n".join([p['text'] for p in pages if p['text']])
        if full_text.strip():
            card = llm.extract_card_from_text(
                full_text,
                {"document_id": doc.id, "file_name": file.filename}
            )
            card_dict = card.dict() if hasattr(card, 'dict') else card
            
            for field, value in card_dict.items():
                if value is not None and field not in ['sources', 'card_id', 'mtr_code', 'ksm_code']:
                    if isinstance(value, (dict, list)):
                        continue
                    char = ExtractedCharacteristic(
                        document_id=doc.id,
                        field_name=field,
                        normalized_value=str(value)
                    )
                    db.add(char)

        db.commit()
        db.refresh(doc)

        return {
            "success": True,
            "document_id": doc.id,
            "message": f"Файл {file.filename} загружен и обработан",
            "pages": doc.page_count,
            "ocr_confidence": doc.ocr_confidence
        }

    except Exception as e:
        doc.ocr_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"OCR ошибка: {str(e)}")


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
    ksm_code: Optional[str] = None,
    limit: int = 50,
    expert_service: ExpertService = Depends(get_expert_service)
):
    return expert_service.get_review_history(ksm_code, limit)


@app.get("/expert-stats")
async def expert_stats(
    expert_service: ExpertService = Depends(get_expert_service)
):
    return expert_service.get_stats()
