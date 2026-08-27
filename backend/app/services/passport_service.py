import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.sqlalchemy.all_models import Document, ExtractedCharacteristic


class PassportService:
    def __init__(self, db: Session):
        self.db = db

    def upload_document(self, file: Any) -> str:
        document_id = str(uuid.uuid4())
        doc = Document(
            document_id=document_id,
            file_name=getattr(file, "filename", "unknown"),
            ocr_status="pending",
        )
        self.db.add(doc)
        self.db.commit()
        return document_id

    def get_status(self, document_id: str) -> dict[str, Any]:
        doc = self._get_document(document_id)
        return {
            "document_id": doc.document_id,
            "file_name": doc.file_name,
            "ocr_status": doc.ocr_status,
            "ocr_confidence": doc.ocr_confidence,
            "page_count": doc.page_count,
            "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
            "processed_date": doc.processed_date.isoformat() if doc.processed_date else None,
        }

    def get_extracted_params(self, document_id: str) -> dict[str, Any]:
        self._get_document(document_id)

        rows = (
            self.db.query(ExtractedCharacteristic)
            .filter(ExtractedCharacteristic.document_id == document_id)
            .all()
        )
        params = [
            {
                "field_name": r.field_name,
                "raw_value": r.raw_value,
                "normalized_value": r.normalized_value,
                "unit": r.unit,
                "confidence": r.confidence,
                "source_fragment": r.source_fragment,
                "source_type": r.source_type,
                "is_verified": r.is_verified,
            }
            for r in rows
        ]
        return {"document_id": document_id, "params": params}

    def _get_document(self, document_id: str) -> Document:
        doc = (
            self.db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )
        if not doc:
            raise NotFoundError(f"Document '{document_id}' not found")
        return doc
