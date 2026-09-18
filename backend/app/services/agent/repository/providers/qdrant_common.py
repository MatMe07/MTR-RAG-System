# repository/providers/qdrant_common.py
"""Общие примитивы Qdrant (коллекции каталога и документов).

Qdrant-сервер v1.9 не поддерживает /points/query, а клиент qdrant-client старше
сервера, поэтому поиск идёт напрямую по REST (паттерн из NormsProvider).
Эмбеддинг общий для всех коллекций — intfloat/multilingual-e5-small (384).
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

import httpx

from .norms_provider import VECTOR_SIZE, embed_text

log = logging.getLogger("mtr.repository.qdrant")


def qdrant_search(
    base_url: str,
    api_key: Optional[str],
    collection: str,
    vector: List[float],
    limit: int = 5,
    qfilter: Optional[List[Dict[str, Any]]] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Поиск по REST. None — ошибка/недоступность."""
    try:
        headers = {"api-key": api_key} if api_key else {}
        resp = httpx.post(
            f"{base_url.rstrip('/')}/collections/{collection}/points/search",
            headers=headers,
            json={
                "vector": vector,
                "limit": limit,
                "filter": {"must": qfilter} if qfilter else None,
                "with_payload": True,
            },
            timeout=5,
        )
        resp.raise_for_status()
        hits = (resp.json() or {}).get("result", []) or []
        out: List[Dict[str, Any]] = []
        for p in hits:
            payload = dict((p.get("payload") or {}))
            payload["score"] = round(float(p.get("score", 0.0)), 4)
            out.append(payload)
        return out
    except Exception as e:
        log.warning("Qdrant search failed (%s): %s", collection, e)
        return None


class QdrantCollectionIndex:
    """Ленивый read-through индекс коллекции Qdrant.

    Точки строятся из payload-словарей (build_points), эмбеддинг выполняется
    при upsert. Поведение при недоступности Qdrant — no-op:
    ensure_index -> False, search_payload -> None.
    """

    def __init__(
        self,
        collection: str,
        *,
        build_points: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        auto_index: bool = True,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        access_logger: Optional[Any] = None,
    ):
        from app.config import settings

        self._collection = collection
        self._build_points = build_points
        self._auto_index = auto_index
        self._host = host or settings.QDRANT_HOST
        self._port = int(port or settings.QDRANT_PORT)
        self._api_key = api_key if api_key is not None else settings.QDRANT_API_KEY
        self._access_logger = access_logger
        self._client: Optional[Any] = None
        self._unavailable = False
        self._indexed = False
        self._index_lock = threading.Lock()

    @property
    def collection(self) -> str:
        return self._collection

    # ---------------------------------------------------------------- conn
    @property
    def _base_url(self) -> str:
        if "://" in self._host:
            return self._host.rstrip("/")
        return f"http://{self._host}:{self._port}"

    def _get_client(self) -> Optional[Any]:
        if self._unavailable:
            return None
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self._base_url,
                    api_key=self._api_key or None,
                    timeout=3,
                    check_compatibility=False,
                )
                self._client.get_collections()
            except Exception as e:
                self._unavailable = True
                log.warning("QdrantCollectionIndex(%s): Qdrant недоступен: %s", self._collection, e)
                self._client = None
                return None
        return self._client

    # ---------------------------------------------------------------- index
    def ensure_index(self, points_payload: Optional[List[Dict[str, Any]]] = None) -> bool:
        with self._index_lock:
            if self._indexed:
                return True
            client = self._get_client()
            if client is None:
                return False
            try:
                payloads = (
                    points_payload
                    if points_payload is not None
                    else (self._build_points() if self._build_points is not None else [])
                )
                if not payloads:
                    return False

                try:
                    client.get_collection(self._collection)
                    info = client.count(self._collection)
                    if info.count and int(info.count) > 0:
                        self._indexed = True
                        return True
                except Exception:
                    pass

                client.recreate_collection(
                    collection_name=self._collection,
                    vectors_config={"size": VECTOR_SIZE, "distance": "Cosine"},
                )
                points = []
                for i, payload in enumerate(payloads):
                    vec = embed_text(payload.get("text", ""), is_query=False)
                    if vec is None:
                        self._unavailable = True
                        return False
                    points.append({"id": i + 1, "vector": vec, "payload": payload})
                client.upsert(collection_name=self._collection, points=points)
                self._indexed = True
                log.info("QdrantCollectionIndex(%s): проиндексировано %d точек", self._collection, len(points))
                return True
            except Exception as e:
                log.warning("QdrantCollectionIndex(%s): индексация не удалась: %s", self._collection, e)
                self._unavailable = True
                return False

    def upsert_payloads(
        self,
        points_payload: List[Dict[str, Any]],
        id_for: Optional[Callable[[Dict[str, Any]], int]] = None,
    ) -> bool:
        """Добавить/обновить точки в существующей коллекции без recreate.

        Если коллекции нет или она пуста — переиспользуется ensure_index
        (полное создание с этими же payloads). id_for возвращает стабильный
        целочисленный id точки (для идемпотентного обновления по ключу);
        по умолчанию id нумеруются от текущего count.
        """
        if not points_payload:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            info = client.count(self._collection)
            count = int(info.count) if info is not None else 0
        except Exception:
            count = 0
        if count == 0:
            return self.ensure_index(points_payload)
        with self._index_lock:
            points = []
            for i, payload in enumerate(points_payload):
                vec = embed_text(payload.get("text", ""), is_query=False)
                if vec is None:
                    self._unavailable = True
                    return False
                pid = id_for(payload) if id_for is not None else count + i + 1
                points.append({"id": pid, "vector": vec, "payload": payload})
            try:
                client.upsert(collection_name=self._collection, points=points)
                self._indexed = True
                log.info("QdrantCollectionIndex(%s): upsert %d точек", self._collection, len(points))
                return True
            except Exception as e:
                log.warning("QdrantCollectionIndex(%s): upsert не удался: %s", self._collection, e)
                return False

    # ---------------------------------------------------------------- search
    def search_payload(
        self,
        query: str,
        limit: int = 5,
        qfilter: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        client = self._get_client()
        if client is None:
            return None
        if self._auto_index:
            self.ensure_index()
        vec = embed_text(query, is_query=True)
        if vec is None:
            return None
        return qdrant_search(self._base_url, self._api_key, self._collection, vec, limit=limit, qfilter=qfilter)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
