# repository/providers/norms_provider.py
"""Провайдер нормативов на Qdrant (векторный поиск по фрагментам).

Эмбеддинг — intfloat/multilingual-e5-small (384-мерный). Коллекция строится
лениво (фрагменты из матрицы нормативов + ЛНД). При недоступности Qdrant или
пустой коллекции поиск возвращает None, и вызывающий слой (ToolDAL) использует
полнотекстовый токен-матчер как fallback.
"""

import logging
import threading
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.repository.norms")

MODEL_NAME = "intfloat/multilingual-e5-small"
VECTOR_SIZE = 384
Q_PREFIX = "query: "
P_PREFIX = "passage: "

_embedder_singleton: Optional[Any] = None
_embedder_lock = threading.Lock()


def get_embedder() -> Optional[Any]:
    """Ленивый синглтон SentenceTransformer (модель грузится один раз)."""
    global _embedder_singleton
    if _embedder_singleton is None:
        with _embedder_lock:
            if _embedder_singleton is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    _embedder_singleton = SentenceTransformer(MODEL_NAME)
                except Exception as e:
                    log.warning("Embedder недоступен (%s): поиск по Qdrant отключён", e)
                    _embedder_singleton = False
    return _embedder_singleton or None


def embed_text(text: str, is_query: bool = False) -> Optional[List[float]]:
    model = get_embedder()
    if model is None:
        return None
    prefixed = (Q_PREFIX if is_query else P_PREFIX) + text
    try:
        vec = model.encode(prefixed, normalize_embeddings=True)
        return [float(x) for x in vec]
    except Exception as e:
        log.warning("embed_text failed: %s", e)
        return None


class NormsProvider:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection: Optional[str] = None,
        access_logger: Optional[Any] = None,
        auto_index: bool = True,
    ):
        from app.config import settings

        self._host = host or settings.QDRANT_HOST
        self._api_key = settings.QDRANT_API_KEY
        self._port = int(port or settings.QDRANT_PORT)
        self._collection = collection or settings.QDRANT_COLLECTION
        self._client: Optional[Any] = None
        self._unavailable = False
        self._index_lock = threading.Lock()
        self._indexed = False
        self._auto_index = auto_index
        self._access_logger = access_logger

    # ------------------------------------------------------------------ conn
    @property
    def _base_url(self) -> str:
        """Полный базовый URL Qdrant (локальный http://host:port или облачный)."""
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
                log.warning("NormsProvider: Qdrant недоступен: %s", e)
                self._client = None
                return None
        return self._client

    def _log(self, provider: str, fallback: bool, reason: Optional[str] = None) -> None:
        if self._access_logger is not None:
            try:
                self._access_logger.record(
                    method_name="search_norms",
                    provider_used=provider,
                    fallback_used=fallback,
                    fallback_reason=reason,
                )
            except Exception:
                pass

    # ---------------------------------------------------------------- index
    def ensure_index(self, fragments: Optional[List[Dict[str, Any]]] = None) -> bool:
        with self._index_lock:
            if self._indexed:
                return True
            client = self._get_client()
            if client is None:
                return False
            try:
                if fragments is None:
                    from .norms_fragments import build_norm_fragments

                    fragments = build_norm_fragments()

                if not fragments:
                    return False

                try:
                    client.get_collection(self._collection)
                    info = client.count(self._collection)
                    if info.count and info.count > 0:
                        self._indexed = True
                        return True
                except Exception:
                    pass

                client.recreate_collection(
                    collection_name=self._collection,
                    vectors_config={
                        "size": VECTOR_SIZE,
                        "distance": "Cosine",
                    },
                )
                points = []
                for i, frag in enumerate(fragments):
                    vec = embed_text(frag["text"], is_query=False)
                    if vec is None:
                        self._unavailable = True
                        return False
                    points.append(
                        {
                            "id": i + 1,
                            "vector": vec,
                            "payload": frag,
                        }
                    )
                client.upsert(collection_name=self._collection, points=points)
                self._indexed = True
                log.info("NormsProvider: проиндексировано %d фрагментов", len(points))
                return True
            except Exception as e:
                log.warning("NormsProvider: индексация не удалась: %s", e)
                self._unavailable = True
                return False

    # ------------------------------------------------------------------ api
    def search(
        self,
        query: str,
        limit: int = 5,
        document_type: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        client = self._get_client()
        if client is None:
            return None

        if self._auto_index:
            self.ensure_index()

        vec = embed_text(query, is_query=True)
        if vec is None:
            self._log("qdrant", fallback=True, reason="модель эмбеддингов недоступна")
            return None

        try:
            qfilter = None
            if document_type:
                qfilter = [{"key": "document_type", "match": {"value": document_type}}]

            # Сервер Qdrant v1.9 не поддерживает /points/query, а клиент 1.19
            # не имеет legacy search(): поиск выполняем напрямую по REST.
            import httpx

            headers = {"api-key": self._api_key} if self._api_key else {}
            resp = httpx.post(
                f"{self._base_url}/collections/{self._collection}/points/search",
                headers=headers,
                json={
                    "vector": vec,
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
            if not out:
                self._log("qdrant", fallback=True, reason="нет релевантных фрагментов")
                return []
            self._log("qdrant", fallback=False)
            return out
        except Exception as e:
            log.warning("NormsProvider: query failed: %s", e)
            self._unavailable = True
            return None

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
