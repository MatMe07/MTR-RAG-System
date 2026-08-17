# backend/app/services/embedding_service.py

import sys
from typing import List, Optional, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http.exceptions import UnexpectedResponse

from app.models import MTRItem
from app.schemas import ItemCard
from app.database import SessionLocal
from app.core.config import settings
from app.core.logging import get_logger
from app.utils.jsonb_utils import get_property_value

log = get_logger("embedding_service")


class EmbeddingService:
    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: int = 1024
    ):
        self.qdrant_url = qdrant_url or settings.QDRANT_URL
        self.qdrant_api_key = qdrant_api_key or settings.QDRANT_API_KEY or None
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.vector_size = vector_size
        self._client = None
        self._embeddings = None
        self._vectorstore = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            try:
                self._client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key,
                    timeout=30.0,
                    check_compatibility=False
                )
                self._client.get_collections()
                log.info("Подключено к Qdrant: %s", self.qdrant_url)
                log.info("мы подключаемся к Qdrant")
            except UnexpectedResponse as e:
                log.warning("Ошибка подключения к Qdrant: %s", e)
                log.warning("Проверьте, что Qdrant запущен на %s", self.qdrant_url)
                raise
        return self._client

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={"device": self.device},
                encode_kwargs={"normalize_embeddings": True}
            )
            log.info("Модель эмбеддингов загружена: %s", self.model_name)
        return self._embeddings

    @property
    def vectorstore(self):
        if self._vectorstore is None:
            self._ensure_collection()
            self._vectorstore = QdrantVectorStore.from_existing_collection(
                embedding=self.embeddings,
                collection_name=self.collection_name,
                url=self.qdrant_url,
                api_key=self.qdrant_api_key
            )
            log.info("Подключено к коллекции: %s", self.collection_name)
        return self._vectorstore

    def _ensure_collection(self) -> None:
        try:
            collections = {c.name for c in self.client.get_collections().collections}
        except UnexpectedResponse as e:
            log.warning("Ошибка при проверке коллекций: %s", e)
            log.warning("Проверьте, что Qdrant запущен и доступен")
            raise

        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            log.info("Коллекция '%s' создана в Qdrant", self.collection_name)

    def collection_exists(self) -> bool:
        try:
            collections = {c.name for c in self.client.get_collections().collections}
            return self.collection_name in collections
        except UnexpectedResponse:
            return False

    def get_collection_count(self) -> int:
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count or 0
        except Exception:
            return 0

    def delete_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
            log.info("Коллекция '%s' удалена", self.collection_name)
            self._vectorstore = None
        except UnexpectedResponse as e:
            log.warning("Ошибка при удалении коллекции: %s", e)
            raise

    def recreate_collection(self) -> None:
        self.delete_collection()
        self._ensure_collection()
        self._vectorstore = None

    def embed_query(self, query: str) -> List[float]:
        return self.embeddings.embed_query(query)

    def embed_card(self, card: ItemCard) -> List[float]:
        text = self._card_to_text(card)
        return self.embeddings.embed_query(text)

    def index_all_mtr(self, force_recreate: bool = False) -> int:
        if self.collection_exists():
            count = self.get_collection_count()
            if count > 0:
                log.info("Коллекция '%s' уже существует и содержит %d точек.", self.collection_name, count)
                if not force_recreate:
                    log.info("Используйте force_recreate=True или аргумент --force для пересоздания.")
                    return count
                log.info("Пересоздание коллекции...")
                self.recreate_collection()
            else:
                log.info("Коллекция '%s' существует, но пуста. Заполняем...", self.collection_name)
        else:
            log.info("Коллекция '%s' не существует. Создаем...", self.collection_name)
            self._ensure_collection()

        db = SessionLocal()
        items = db.query(MTRItem).all()
        db.close()

        log.info("Найдено МТР в БД: %d", len(items))

        if not items:
            log.info("Нет данных для индексации")
            return 0

        documents = []
        for item in items:
            text = self._mtr_to_text(item)
            props = item.properties or {}
            metadata = {
                "mtr_code": item.mtr_code,
                "ksm_code": item.ksm_code,
                "item_type": item.item_type,
                "db_id": item.id,
                "designation": item.designation or item.short_text or "",
                "medium": get_property_value(props, 'medium') or "",
                "standard": get_property_value(props, 'standard')
                            or get_property_value(props, 'gost_tu') or "",
            }
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)

        self.vectorstore.add_documents(documents, batch_size=16)
        log.info("Индексировано %d документов в Qdrant", len(documents))
        return len(documents)

    def search_similar(self, query: str, k: int = 50) -> List[Dict[str, Any]]:
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        return [
            {
                "mtr_code": doc.metadata.get("mtr_code"),
                "ksm_code": doc.metadata.get("ksm_code"),
                "db_id": doc.metadata.get("db_id"),
                "score": score
            }
            for doc, score in results
        ]

    def search_similar_filtered(
        self,
        query: str,
        k: int = 50,
        must: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Семантический поиск по коллекции через raw qdrant-client.

        must — список условий (FieldCondition/FieldCondition) для фильтрации
        payload (item_type, medium и т.п.). Возвращает записи с db_id и
        расширенным payload (designation, medium, standard).
        """
        from qdrant_client.http.models import Filter

        query_vector = self.embed_query(query)
        query_filter = Filter(must=must) if must else None
        res = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=k,
            query_filter=query_filter,
            with_payload=True,
        )
        out = []
        for hit in res:
            p = hit.payload or {}
            out.append({
                "db_id": p.get("db_id"),
                "mtr_code": p.get("mtr_code"),
                "ksm_code": p.get("ksm_code"),
                "item_type": p.get("item_type"),
                "designation": p.get("designation"),
                "medium": p.get("medium"),
                "standard": p.get("standard"),
                "score": float(hit.score),
            })
        return out

    def _card_to_text(self, card: ItemCard) -> str:
        parts = []

        if card.item_type:
            parts.append(f"тип: {card.item_type}")
        if card.subtype:
            parts.append(f"подтип: {card.subtype}")
        if card.designation:
            parts.append(f"обозначение: {card.designation}")
        if card.name:
            parts.append(f"наименование: {card.name}")

        if card.geometry:
            if card.geometry.dn:
                parts.append(f"DN: {card.geometry.dn} мм")
            if card.geometry.wall_thickness:
                parts.append(f"стенка: {card.geometry.wall_thickness} мм")
            if card.geometry.angle:
                parts.append(f"угол: {card.geometry.angle} градусов")

        if card.pressure and card.pressure.pn:
            parts.append(f"номинальное давление: PN{card.pressure.pn}")

        if card.material:
            if card.material.steel_grade:
                parts.append(f"сталь: {card.material.steel_grade}")
            if card.material.strength_class:
                parts.append(f"класс: {card.material.strength_class}")

        if card.environment:
            if card.environment.medium:
                parts.append(f"среда: {card.environment.medium}")
            if card.environment.climate_version:
                parts.append(f"климат: {card.environment.climate_version}")

        if card.coating:
            if card.coating.inner_coating:
                parts.append("внутреннее покрытие")
            if card.coating.outer_coating:
                parts.append("наружное покрытие")

        if card.normative and card.normative.gost_tu:
            parts.append(f"ГОСТ/ТУ: {card.normative.gost_tu}")

        return " ".join(parts)

    def _mtr_to_text(self, mtr: MTRItem) -> str:
        parts = []
        props = mtr.properties or {}

        if mtr.item_type:
            parts.append(f"тип: {mtr.item_type}")
        if mtr.subtype:
            parts.append(f"подтип: {mtr.subtype}")
        if mtr.designation:
            parts.append(f"обозначение: {mtr.designation}")
        if mtr.short_text:
            parts.append(f"наименование: {mtr.short_text}")

        dn = get_property_value(props, 'dn')
        if dn:
            parts.append(f"DN: {dn} мм")
        
        wall = get_property_value(props, 'wall_thickness')
        if wall:
            parts.append(f"стенка: {wall} мм")
        
        angle = get_property_value(props, 'angle')
        if angle:
            parts.append(f"угол: {angle} градусов")
        
        pressure = get_property_value(props, 'pn')
        if pressure:
            parts.append(f"номинальное давление: PN{pressure}")
        
        steel_grade = get_property_value(props, 'steel_grade')
        if steel_grade:
            parts.append(f"сталь: {steel_grade}")
        
        strength_class = get_property_value(props, 'strength_class')
        if strength_class:
            parts.append(f"класс: {strength_class}")
        
        medium = get_property_value(props, 'medium')
        if medium:
            parts.append(f"среда: {medium}")
        
        climate = get_property_value(props, 'climate_version')
        if climate:
            parts.append(f"климат: {climate}")
        
        if get_property_value(props, 'inner_coating'):
            parts.append("внутреннее покрытие")
        if get_property_value(props, 'outer_coating'):
            parts.append("наружное покрытие")
        
        gost = get_property_value(props, 'gost_tu')
        if gost:
            parts.append(f"ГОСТ/ТУ: {gost}")

        return " ".join(parts)
