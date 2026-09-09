# repository/providers/documents_provider.py
"""Паспорта в Qdrant (коллекция documents) — поиск по тексту документов.

Payload (Этап 1.1, §3.2): document_id, page_number, text, ocr_confidence.
Инфраструктура для Фазы 3 (OCR-пайплайн); индекс строится из
data/sample/documents/passport_*.md. В агент-контур пока не подключён.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .qdrant_common import QdrantCollectionIndex


def _repo_root(depth: int) -> Path:
    return Path(__file__).parents[depth]


def _docs_dir() -> Path:
    for base in [_repo_root(6), Path.cwd()]:
        d = base / "data" / "sample" / "documents"
        if d.exists():
            return d
    return _repo_root(6) / "data" / "sample" / "documents"


def passport_md_paths(base: Optional[Path] = None) -> List[Path]:
    d = base or _docs_dir()
    if not d.exists():
        return []
    return sorted(d.glob("passport_*.md"))


def build_document_points(paths: List[Path]) -> List[Dict[str, Any]]:
    """Payload-точки паспортов (текст обрезается; вектор при upsert)."""
    points = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        points.append(
            {
                "document_id": path.stem,
                "page_number": 1,
                "text": text.strip()[:4000],
                "ocr_confidence": 1.0,
            }
        )
    return points


class DocumentsProvider:
    """Векторный поиск по текстам паспортов (коллекция documents)."""

    def __init__(
        self,
        collection: Optional[str] = None,
        *,
        auto_index: bool = True,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        from app.config import settings

        self._collection = collection or settings.QDRANT_DOCUMENTS_COLLECTION
        self._index = QdrantCollectionIndex(
            self._collection,
            build_points=lambda: build_document_points(passport_md_paths()),
            auto_index=auto_index,
            host=host,
            port=port,
            api_key=api_key,
        )

    def ensure_index(self, paths: Optional[List[Path]] = None) -> bool:
        payloads = build_document_points(paths) if paths is not None else None
        return self._index.ensure_index(payloads)

    def search(self, query: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Поиск по текстам паспортов. None — провайдер недоступен/пуст."""
        return self._index.search_payload(query, limit=limit)

    def close(self) -> None:
        self._index.close()