from __future__ import annotations

import logging

from nutrition_rag.core.config import Settings
from nutrition_rag.core.models import Chunk
from nutrition_rag.pipelines.embedding.registry import EmbeddingProvider, EmbeddingRegistry

logger = logging.getLogger(__name__)


def _detect_gpu() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


class BatchEmbedder:
    def __init__(self, settings: Settings, registry: EmbeddingRegistry):
        self.settings = settings
        self.registry = registry
        self.batch_size = settings.embedding.batch_size
        self.use_gpu = settings.embedding.use_gpu and _detect_gpu()
        if self.use_gpu:
            logger.info("BatchEmbedder: GPU acceleration enabled")
        else:
            logger.info("BatchEmbedder: Using CPU fallback")

    async def embed_chunks(self, chunks: list[Chunk], provider: EmbeddingProvider | None = None) -> list[Chunk]:
        if not chunks:
            return chunks
        provider = provider or self.registry.get_active_provider()
        total = len(chunks)
        embedded = 0
        for i in range(0, total, self.batch_size):
            batch = chunks[i : i + self.batch_size]
            texts = [c.content for c in batch]
            try:
                vectors = await provider.embed_texts(texts)
            except Exception as e:
                logger.error("Embedding batch %d-%d failed: %s", i, i + len(batch), e)
                raise
            for j, chunk in enumerate(batch):
                if j < len(vectors):
                    chunk.embedding = vectors[j]
            embedded += len(batch)
            logger.debug("Embedded batch %d-%d / %d", i, i + len(batch), total)
        logger.info("BatchEmbedder: embedded %d chunks", embedded)
        return chunks

    async def embed_query(self, query: str, provider: EmbeddingProvider | None = None) -> list[float]:
        provider = provider or self.registry.get_active_provider()
        return await provider.embed_query(query)
