"""QdrantCatalogSearch: семантический поиск позиций каталога в Qdrant.

Лёгкая обёртка над EmbeddingService (raw qdrant-client): эмбеддинг запроса
строит та же модель, что используется при индексации, поиск идёт по точкам
коллекции с payload-фильтрами. Используется DbAgentRepository для гибридного
поиска кандидатов (PG-фильтры + семантика).
"""

from typing import Any, Dict, List, Optional


class QdrantCatalogSearch:
    """Поиск по коллекции каталога (mtr_items) в Qdrant."""

    def __init__(self, service=None, collection_name: Optional[str] = None):
        self._svc = service
        self._owns_service = service is None
        self._collection_name = collection_name

    def _service(self):
        if self._svc is None:
            from app.services.embedding_service import EmbeddingService
            self._svc = EmbeddingService(collection_name=self._collection_name)
            self._owns_service = True
        return self._svc

    def search(self, query: str, k: int = 50,
               must: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Семантический поиск позиций каталога.

        query — свободный текст запроса;
        k — число кандидатов;
        must — список условий qdrant_client.http.models.FieldCondition
        (например, по item_type/medium), ограничивающий поиск.

        Возвращает записи вида {db_id, mtr_code, ksm_code, item_type, score, ...}.
        """
        svc = self._service()
        if not svc.collection_exists():
            return []
        return svc.search_similar_filtered(query, k=k, must=must)
