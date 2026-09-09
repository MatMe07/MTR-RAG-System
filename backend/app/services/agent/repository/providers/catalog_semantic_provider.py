# repository/providers/catalog_semantic_provider.py
"""Семантический индекс каталога MTR в Qdrant (коллекция mtr_descriptions).

Payload по 2F.1 (docs/plans/ЭТАП 2. ДОСТУП К ДАННЫМ.md): ksm_code, mtr_code,
item_type, dn, pn, material (steel_grade), medium, text (designation), gost_tu.
Источник — регламентированный CSV-каталог. Поиск — по REST (см. qdrant_common).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .qdrant_common import QdrantCollectionIndex


def _repo_root(depth: int) -> Path:
    return Path(__file__).parents[depth]


def _catalog_csv_path() -> Path:
    for base in [_repo_root(6), Path.cwd()]:
        p = base / "data" / "catalog" / "regulated_mtr_catalog_1000.csv"
        if p.exists():
            return p
    return _repo_root(6) / "data" / "catalog" / "regulated_mtr_catalog_1000.csv"


def load_catalog_rows(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    import pandas as pd

    p = path or _catalog_csv_path()
    df = pd.read_csv(p, delimiter=';')
    return df.to_dict(orient="records")


def build_catalog_points(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Плоские payload-точки каталога (вектор добавляется при upsert)."""
    points = []
    for r in rows:
        text = r.get("designation") or r.get("name") or ""
        points.append(
            {
                "ksm_code": r.get("ksm_code"),
                "mtr_code": r.get("mtr_code"),
                "item_type": r.get("item_type") or "",
                "dn": r.get("dn"),
                "pn": r.get("pn"),
                "material": r.get("steel_grade") or "",
                "medium": r.get("medium") or "",
                "text": str(text),
                "gost_tu": r.get("gost_tu") or "",
            }
        )
    return points


class CatalogSemanticProvider:
    """Векторный поиск по описаниям каталога (коллекция mtr_descriptions)."""

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

        self._collection = collection or settings.QDRANT_CATALOG_COLLECTION
        self._index = QdrantCollectionIndex(
            self._collection,
            build_points=lambda: build_catalog_points(load_catalog_rows()),
            auto_index=auto_index,
            host=host,
            port=port,
            api_key=api_key,
        )

    def ensure_index(self, rows: Optional[List[Dict[str, Any]]] = None) -> bool:
        payloads = build_catalog_points(rows) if rows is not None else None
        return self._index.ensure_index(payloads)

    def search(self, query: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Поиск по каталогу. None — провайдер недоступен/пуст."""
        return self._index.search_payload(query, limit=limit)

    def close(self) -> None:
        self._index.close()