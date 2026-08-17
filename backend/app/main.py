# backend/app/main.py

import os
import shutil
import uuid
from typing import List, Optional

from app.core.logging import get_logger, setup_logging

setup_logging()
log = get_logger("main")
log.debug("start1")

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
log.debug("start2")


from app.database import get_db
from app.schemas import (
    SearchRequest, SearchResponse, MatchResult,
    ExpertReviewRequest, ItemCard, AgentRequest, AgentAnswer,
    RouteRequest, RouteResponse
)
log.debug("start3")

from app.services.search_service import SearchService
log.debug("start4")

from app.services.rules_engine import RulesEngine
log.debug("start5")

from app.services.llm_service import LLMService
log.debug("start6")

from app.services.embedding_service import EmbeddingService
from app.services.expert_service import ExpertService
log.debug("start7")
# from app.services.ocr_service import get_ocr_service
log.debug("start8")

from app.services.agent.executor import execute_agent_query
log.debug("start9")

from app.services.routing.llm_router import LlmRouter
# from app.services.routing.search_router import route_query_text
log.debug("start10")


app = FastAPI(
    title="MTR Search System",
    description="Система интеллектуального подбора МТР",
    version="0.1.0"
)

UPLOAD_DIR = "uploads/passports"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============================================================
# 🔥 ЛЕНИВАЯ ИНИЦИАЛИЗАЦИЯ (вместо глобальной)
# ============================================================

_llm = None
_embeddings = None
_ocr = None


def get_llm():
    global _llm
    if _llm is None:
        log.info("Инициализация LLMService...")
        _llm = LLMService()
        log.info("LLMService инициализирован")
    return _llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        log.info("Инициализация EmbeddingService...")
        _embeddings = EmbeddingService()
        log.info("EmbeddingService инициализирован")
    return _embeddings


def get_ocr():
    global _ocr
    if _ocr is None:
        log.info("Инициализация OCR...")
        # _ocr = get_ocr_service()
        log.info("OCR инициализирован")
    return _ocr


def get_search_service(db: Session = Depends(get_db)):
    rules = RulesEngine(db)
    return SearchService(db, rules, get_llm(), get_embeddings())


def get_expert_service(db: Session = Depends(get_db)):
    return ExpertService(db)


# ============================================================
# 🔥 ПРОВЕРКА ЗАГРУЗКИ (для отладки)
# ============================================================

log.info("main.py загружается")

# ============================================================
# ЭНДПОИНТЫ
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Выполняется при старте (но уже после загрузки main.py)"""
    log.info("FastAPI стартовал!")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service)
):
    log.info("[search] mode=%s top_k=%s | '%s'", request.mode, request.top_k, request.query[:80])
    try:
        return search_service.search(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent", response_model=AgentAnswer)
async def agent_query(request: AgentRequest):
    """Агентский слой: парсит запрос (rule-based + LLM-коррекция) и запускает план тулов."""
    log.info("[agent] старт: '%s'", request.query[:80])
    try:
        ag = execute_agent_query(request.query)
        log.info("[agent] ответ: %s", ag)
        return ag
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/route", response_model=RouteResponse)
async def route_query(request: RouteRequest):
    """Маршрутизация (L4): детерминированная + LLM-уточнение, если оно неоднозначно."""
    try:
        from app.services.entity_extractor import get_entity_extractor

        parsed = get_entity_extractor().extract(request.query)
        decision = LlmRouter().route(request.query)
        log.info("[route] '%s' -> %s (mode=%s, llm_refined=%s)",
                 request.query[:60], decision.get('route'),
                 decision.get('mode'), decision.get('llm_refined'))
        log.info("decision: %s", decision)
        decision["parsed_query"] = parsed
        return RouteResponse(**{
            key: decision.get(key)
            for key in RouteResponse.model_fields
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/passport")
async def upload_passport(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
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
        # Используем ленивый OCR
        ocr_service = get_ocr()
        pages = ocr_service.extract_text_from_pdf(file_path)
        
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
        doc.ocr_confidence = float(np.mean([p['confidence'] for p in pages])) if pages else 0.0

        full_text = "\n".join([p['text'] for p in pages if p['text']])
        if full_text.strip():
            try:
                # Используем ленивый LLM
                llm_service = get_llm()
                card = llm_service.extract_card_from_text(
                    full_text,
                    {"document_id": doc.id, "file_name": file.filename}
                )
                card_dict = card.model_dump() if hasattr(card, 'model_dump') else card
                
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
            except Exception as llm_err:
                log.warning("LLM извлечение не удалось: %s", llm_err)
                # Продолжаем, даже если LLM не сработала

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
