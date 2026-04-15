from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient, models

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: QdrantClient | None = None
        self.collection = settings.qdrant_collection

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            kwargs: dict[str, Any] = {
                "host": self.settings.qdrant_host,
                "port": self.settings.qdrant_port,
            }
            if self.settings.qdrant_api_key:
                kwargs["api_key"] = self.settings.qdrant_api_key
            self._client = QdrantClient(**kwargs)
        return self._client

    def ensure_collection(self, vector_size: int = 1536) -> None:
        client = self._get_client()
        collections = client.get_collections().collections
        exists = any(c.name == self.collection for c in collections)
        if not exists:
            client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
                sparse_vectors_config={"bm25": models.SparseVectorParams()},
            )
            logger.info("Created Qdrant collection '%s' (vector_size=%d)", self.collection, vector_size)

            client.create_payload_index(self.collection, "source", models.PayloadSchemaType.KEYWORD)
            client.create_payload_index(self.collection, "chunk_type", models.PayloadSchemaType.KEYWORD)
            client.create_payload_index(self.collection, "document_id", models.PayloadSchemaType.KEYWORD)
            client.create_payload_index(self.collection, "confidence_score", models.PayloadSchemaType.FLOAT)
            client.create_payload_index(self.collection, "has_disclaimer", models.PayloadSchemaType.BOOL)
        else:
            logger.debug("Collection '%s' already exists", self.collection)

    def _chunk_to_point(self, chunk: Chunk) -> models.PointStruct:
        return models.PointStruct(
            id=chunk.id,
            vector={"dense": chunk.embedding} if chunk.embedding else None,
            payload={
                "document_id": chunk.document_id,
                "content": chunk.content,
                "chunk_type": chunk.chunk_type.value,
                "source": chunk.source.value,
                "source_url": chunk.source_url,
                "confidence_score": chunk.confidence_score,
                "has_disclaimer": chunk.has_disclaimer,
                "metadata": chunk.metadata,
                "created_at": chunk.created_at.isoformat(),
            },
        )

    def upsert_chunks(self, chunks: list[Chunk], batch_size: int = 100) -> int:
        if not chunks:
            return 0
        client = self._get_client()
        self.ensure_collection(vector_size=len(chunks[0].embedding) if chunks[0].embedding else 1536)

        upserted = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            points = [self._chunk_to_point(c) for c in batch if c.embedding]
            if not points:
                continue
            client.upsert(collection_name=self.collection, points=points)
            upserted += len(points)
            logger.debug("Upserted batch %d-%d (%d points)", i, i + len(batch), len(points))

        logger.info("Vector store upsert: %d chunks written to '%s'", upserted, self.collection)
        return upserted

    def check_exists(self, document_id: str) -> set[str]:
        client = self._get_client()
        try:
            results, _ = client.scroll(
                collection_name=self.collection,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
                ),
                limit=10000,
                with_payload=False,
                with_vectors=False,
            )
            return {str(p.id) for p in results}
        except Exception:
            return set()

    def delete_by_document(self, document_id: str) -> None:
        client = self._get_client()
        client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
                )
            ),
        )
        logger.info("Deleted chunks for document %s", document_id)
