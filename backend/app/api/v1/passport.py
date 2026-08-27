from typing import Any

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.exceptions import AppException
from app.models.pydantic.schemas import ExtractedParam, DocumentMetadata
from app.services.passport_service import PassportService

router = APIRouter()


class StatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    file_name: str
    ocr_status: str
    ocr_confidence: float | None = None
    page_count: int | None = None
    upload_date: str | None = None
    processed_date: str | None = None


class ExtractedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    params: list[ExtractedParam]


@router.post("/upload")
def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        svc = PassportService(db)
        document_id = svc.upload_document(file)
        return {"document_id": document_id, "status": "pending"}
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Upload failed: {e}")


@router.get("/status/{document_id}", response_model=StatusResponse)
def status(document_id: str, db: Session = Depends(get_db)):
    try:
        svc = PassportService(db)
        return svc.get_status(document_id)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to get status: {e}")


@router.get("/extracted/{document_id}")
def extracted(document_id: str, db: Session = Depends(get_db)):
    try:
        svc = PassportService(db)
        return svc.get_extracted_params(document_id)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to get extracted params: {e}")
