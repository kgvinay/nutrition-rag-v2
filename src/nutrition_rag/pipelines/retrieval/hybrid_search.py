from __future__ import annotations

import logging
from typing import Any

from qdrant_client import models
from qdrant_client import QdrantClient

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk, DataSource
from nutrition_rag.pipelines.embedding.registry import EmbeddingRegistry

logger = logging.getLogger(__name__)


class HybridSearcher:
    def __init__(self, settings: Settings, registry: EmbeddingRegistry, qdrant_client: QdrantClient | None = None):
        self.settings = settings
        self.registry = registry
        self.collection = settings.qdrant_collection
        self._client = qdrant_client

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

    async def search(
        self,
        query: str,
        top_k: int | None = None,
        vector_weight: float | None = None,
        keyword_weight: float | None = None,
        metadata_filters: dict[str, Any] | None = None,
        must_filters: list[models.FieldCondition] | None = None,
    ) -> list[Chunk]:
        top_k = top_k or self.settings.retrieval.top_k
        vector_weight = vector_weight or self.settings.retrieval.vector_weight
        keyword_weight = keyword_weight or self.settings.retrieval.keyword_weight

        provider = self.registry.get_active_provider()
        query_vector = await provider.embed_query(query)

        filter_conditions: list[models.Condition] = []
        if must_filters:
            filter_conditions.extend(must_filters)
        if metadata_filters:
            for key, value in metadata_filters.items():
                if isinstance(value, list):
                    filter_conditions.append(models.FieldCondition(key=key, match=models.MatchAny(any=value)))
                else:
                    filter_conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))

        search_filter = models.Filter(must=filter_conditions) if filter_conditions else None

        client = self._get_client()
        results = client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )

        chunks = []
        for result in results:
            payload = result.payload or {}
            chunk = Chunk(
                id=str(result.id),
                document_id=payload.get("document_id", ""),
                content=payload.get("content", ""),
                chunk_type=payload.get("chunk_type", "nutrient_fact"),
                metadata=payload.get("metadata", {}),
                confidence_score=payload.get("confidence_score", 0.5),
                has_disclaimer=payload.get("has_disclaimer", False),
                source=DataSource(payload.get("source", "usda")),
                source_url=payload.get("source_url", ""),
            )
            chunks.append(chunk)

        logger.info("Hybrid search: query='%s' → %d results", query[:50], len(chunks))
        return chunks
